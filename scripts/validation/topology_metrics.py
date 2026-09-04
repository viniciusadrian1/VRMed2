"""Qualidade TOPOLOGICA da malha e CONTINUIDADE de estruturas tubulares.

Duas perguntas que Dice/HD95 nao respondem:
  1. a malha e utilizavel (fechada, um corpo so, sem aresta nao-manifold)?
     -> `qualidade_topologica` — nao mede fidelidade, mede sanidade.
  2. o vaso continuou INTEIRO ao virar malha, ou fragmentou/sumiu?
     -> `continuidade_vaso` (na mascara) e `comparar_continuidade` (mascara x
        malha rasterizada). Um vaso que quebra em 3 pedacos pode ter Dice alto
        e ainda assim ser inutil para navegacao/planejamento.

Uma terceira, para A/B de variantes:
  3. o que a variante ESTRAGOU ou CONSERTOU na topologia?
     -> `comparar_topologia(antes, depois)` — deltas nomeados entre dois
        retornos de `qualidade_topologica`.

Convencao de valor ausente (nao negociavel neste modulo): nenhuma chave devolve
um numero que parece valido quando a medida nao aconteceu.
  - "nao medido"    -> a medida e definida, mas nao foi possivel executa-la aqui
                       (dependencia ausente, malha grande demais, chave ausente).
  - "nao aplicavel" -> a medida nao e matematicamente definida para esta malha.
  - "invalido"      -> idem, mas para grandeza que so existe em malha fechada.
`0` significa sempre "medi e nao encontrei".

Nada aqui e claim clinico: e controle de qualidade geometrico sobre a MESMA
grade de voxel (referencia = a propria mascara, tipo "benchmark_interno").
"""

from __future__ import annotations

import operator

import numpy as np
import trimesh
from scipy import ndimage
from skimage.morphology import skeletonize

from ..geometry.coordinates import zooms_de
from .mesh_metrics import voxelizar_malha, volume_ml

# 26-conexo: dois voxels que se tocam so pelo vertice ainda sao o mesmo vaso.
# Com 6-conexo uma escada diagonal de 1 voxel ja contaria como fragmentacao.
CONECTIVIDADE = np.ones((3, 3, 3), dtype=bool)

# Acima disso a busca de pares candidatos deixa de caber no orcamento do
# benchmark; devolvemos "nao medido" em vez de travar. Custo medido nesta
# maquina: ~2,4 s para 82 k faces, crescimento aproximadamente linear.
LIMITE_FACES_SELF_INTERSECTION = 300_000
# Lote de pares no teste exato, para nao estourar RAM em malha grande.
_LOTE_PARES = 250_000
# a = e1 . (d x e2) tem dimensao de comprimento^3: numa malha em METROS um
# limiar absoluto reprovaria tudo. Este e RELATIVO a |e1||e2||d|.
_EPS_PARALELO = 1e-9


def _e_numero(x: object) -> bool:
    """int/float de verdade — bool NAO conta (True == 1 estragaria os deltas)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _faltante(antes: object, depois: object) -> str | None:
    """String a propagar quando algum dos dois lados nao e valor medido.

    Prioriza a string do lado `depois` (o estado mais recente e o que descreve
    a malha que se quer julgar). Devolve None quando os dois lados sao valores.
    """
    for v in (depois, antes):
        if isinstance(v, str):
            return v
    return None


def _segmento_corta_triangulo(
    p0: np.ndarray, p1: np.ndarray, t0: np.ndarray, t1: np.ndarray, t2: np.ndarray
) -> np.ndarray:
    """Moller-Trumbore vetorizado: o segmento p0->p1 corta o triangulo t0t1t2?

    Interseccao PROPRIA (transversal). Caso degenerado — segmento paralelo ao
    plano do triangulo, ou toque exato vertice-com-vertice — sai False: nao e
    auto-interseccao, e malha compartilhando geometria.
    """
    d = p1 - p0
    e1 = t1 - t0
    e2 = t2 - t0
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    escala = np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1) * np.linalg.norm(d, axis=1)
    ok = np.abs(a) > _EPS_PARALELO * np.maximum(escala, np.finfo(float).tiny)

    f = 1.0 / np.where(ok, a, 1.0)  # evita divisao por zero no ramo descartado
    s = p0 - t0
    u = f * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    v = f * np.einsum("ij,ij->i", d, q)
    t = f * np.einsum("ij,ij->i", e2, q)
    return ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)


def _auto_interseccoes(mesh: trimesh.Trimesh) -> int | str:
    """Numero de PARES de faces que se auto-intersectam, ou "nao medido".

    Caminho: broadphase por AABB no R-tree que o proprio trimesh ja mantem
    (`mesh.triangles_tree`, exige rtree) + teste exato aresta-x-triangulo nos
    candidatos. Dois triangulos que se cruzam sempre o fazem ao longo de um
    segmento cujos extremos sao cortes de ARESTA de um contra a FACE do outro,
    entao testar as 6 arestas dos dois cobre toda interseccao propria.

    Pares que compartilham vertice sao descartados: sao vizinhos legitimos.

    Por que NAO usamos `vtkIntersectionPolyDataFilter` (tentativa (a)): rodar a
    malha contra ela mesma marca CADA aresta compartilhada como interseccao —
    numa icosfera limpa de 1280 faces ele devolve 480 linhas, exatamente o
    numero de arestas. E `vtkOBBTree.IntersectWithLine` foi conferido contra
    forca bruta em duas esferas sobrepostas (640 faces) e achou 0 dos 127 pares
    reais. Nenhum dos dois e confiavel aqui, entao nao entram como fonte.

    Calibragem: conferido contra forca bruta O(n^2) exata em duas esferas
    sobrepostas; concorda em 123/127 pares, e os 4 restantes sao toques exatos
    vertice-com-vertice (u=1, v=0), que por definicao nao contam.
    """
    n_faces = len(mesh.faces)
    if n_faces == 0:
        return 0
    if n_faces > LIMITE_FACES_SELF_INTERSECTION:
        return "nao medido"

    tris = np.asarray(mesh.triangles, dtype=float)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    caixas = np.hstack([tris.min(axis=1), tris.max(axis=1)])
    try:
        arvore = mesh.triangles_tree  # rtree; ausente => ImportError
    except (ImportError, AttributeError):
        return "nao medido"

    esq: list[int] = []
    dir_: list[int] = []
    for i, caixa in enumerate(caixas):
        for j in arvore.intersection(caixa):
            if j > i:
                esq.append(i)
                dir_.append(j)
    if not esq:
        return 0

    a_idx = np.asarray(esq, dtype=np.int64)
    b_idx = np.asarray(dir_, dtype=np.int64)
    total = 0
    for ini in range(0, len(a_idx), _LOTE_PARES):
        ia = a_idx[ini : ini + _LOTE_PARES]
        ib = b_idx[ini : ini + _LOTE_PARES]
        # descarta vizinhos: qualquer vertice em comum
        compartilha = (faces[ia][:, :, None] == faces[ib][:, None, :]).any(axis=(1, 2))
        ia, ib = ia[~compartilha], ib[~compartilha]
        if not len(ia):
            continue
        ta, tb = tris[ia], tris[ib]
        bate = np.zeros(len(ia), dtype=bool)
        for k in range(3):
            bate |= _segmento_corta_triangulo(ta[:, k], ta[:, (k + 1) % 3], tb[:, 0], tb[:, 1], tb[:, 2])
            bate |= _segmento_corta_triangulo(tb[:, k], tb[:, (k + 1) % 3], ta[:, 0], ta[:, 1], ta[:, 2])
        total += int(bate.sum())
    return total


def qualidade_topologica(mesh: trimesh.Trimesh) -> dict:
    """Sanidade topologica da malha (nao mede fidelidade geometrica).

    Sobre as tres chaves de aresta — uma aresta sa aparece em EXATAMENTE 2 faces:
      - `n_arestas_nao_manifold`: chave HISTORICA, contagem != 2. Mistura buraco
        (contagem 1) e nao-manifold de verdade (contagem >= 3) num numero so.
        Mantida com o significado original para nao quebrar consumidor existente.
      - `n_boundary_edges`: contagem == 1. Borda aberta/buraco.
      - `n_arestas_nao_manifold_estrito`: contagem >= 3. Aresta com 3+ faces,
        que e o defeito que impede booleanas e offsets.
    Vale sempre `n_arestas_nao_manifold == n_boundary_edges +
    n_arestas_nao_manifold_estrito`.

    `volume_ml_se_watertight` sai "invalido" em malha aberta: volume de
    superficie nao fechada nao e definido — o teorema da divergencia exige
    fronteira fechada, e o numero que sairia depende de onde o buraco esta.

    `genus` = (2*n_componentes - euler)/2, so em malha fechada e manifold
    (sem borda e sem aresta 3+). Fora disso o numero de Euler nao descreve uma
    superficie fechada e o genero nao existe: sai "nao aplicavel".
    CUIDADO com malha de varios corpos: o valor e a SOMA dos generos das
    componentes, nao o genero de uma superficie. `genus=2` com
    `n_componentes=3` pode ser uma componente com 2 alcas ou duas com 1 cada —
    este numero nao distingue. Para localizar, separe os corpos antes.
    """
    arestas = np.sort(mesh.edges, axis=1)
    _unicas, contagem = np.unique(arestas, axis=0, return_counts=True)
    n_nao_manifold = int((contagem != 2).sum())  # chave historica: 1 e >=3 juntos
    n_boundary = int((contagem == 1).sum())
    n_nao_manifold_estrito = int((contagem >= 3).sum())

    areas = np.asarray(mesh.area_faces, dtype=float)
    # degenerada = area desprezivel FRENTE A ESCALA DA MALHA (limiar absoluto em
    # metros classificaria tudo como degenerado numa malha de 5 mm).
    mediana = float(np.median(areas)) if len(areas) else 0.0
    n_degeneradas = int((areas <= 1e-8 * mediana).sum()) if mediana > 0 else len(areas)

    n_isolados = int(len(mesh.vertices) - len(np.unique(mesh.faces)))
    watertight = bool(mesh.is_watertight)
    n_componentes = int(mesh.body_count)
    euler = int(mesh.euler_number)

    manifold = n_boundary == 0 and n_nao_manifold_estrito == 0
    genus: int | str = "nao aplicavel"
    if watertight and manifold:
        dobro = 2 * n_componentes - euler
        # genero fracionario significa que a caracteristica de Euler nao fecha:
        # nao arredondamos para fingir um inteiro.
        genus = dobro // 2 if dobro % 2 == 0 else "invalido"

    return {
        "watertight": watertight,
        "n_componentes": n_componentes,
        "euler_number": euler,
        "n_arestas_nao_manifold": n_nao_manifold,
        "n_boundary_edges": n_boundary,
        "n_arestas_nao_manifold_estrito": n_nao_manifold_estrito,
        "n_self_intersections": _auto_interseccoes(mesh),
        "genus": genus,
        "n_faces_degeneradas": n_degeneradas,
        "n_vertices_isolados": n_isolados,
        "normais_consistentes": bool(mesh.is_winding_consistent),
        "area_mm2": round(float(mesh.area) * 1e6, 3),  # m2 -> mm2
        "volume_ml_se_watertight": round(volume_ml(mesh), 4) if watertight else "invalido",
    }


def _delta(antes: dict, depois: dict, chave: str) -> float | int | str:
    """depois - antes, ou a string do lado que nao foi medido."""
    a, d = antes.get(chave, "nao medido"), depois.get(chave, "nao medido")
    falta = _faltante(a, d)
    if falta is not None:
        return falta
    if not _e_numero(a) or not _e_numero(d):
        return "nao medido"
    bruto = d - a
    return round(float(bruto), 4) if isinstance(bruto, float) else int(bruto)


def _compara(antes: dict, depois: dict, chave: str, op) -> bool | str:
    """`op(antes, depois)` como bool, ou a string do lado que nao foi medido."""
    a, d = antes.get(chave, "nao medido"), depois.get(chave, "nao medido")
    falta = _faltante(a, d)
    if falta is not None:
        return falta
    if a is None or d is None:
        return "nao medido"
    return bool(op(a, d))


def comparar_topologia(antes: dict, depois: dict) -> dict:
    """Deltas nomeados entre dois retornos de `qualidade_topologica`.

    Responde "o que a variante estragou/consertou", nao "qual e melhor" — sinal
    de topologia nao e criterio de promocao sozinho.

    Todo campo cujo insumo saiu "nao medido"/"nao aplicavel"/"invalido" PROPAGA
    a string. Nenhum vira False silenciosamente: nao conseguir medir nao e o
    mesmo que medir e nao encontrar defeito.
    """
    return {
        "fundiu_componentes": _compara(antes, depois, "n_componentes", operator.gt),
        "fragmentou": _compara(antes, depois, "n_componentes", operator.lt),
        # era fechada e deixou de ser
        "abriu_malha": _compara(antes, depois, "watertight", lambda a, d: bool(a) and not bool(d)),
        # genero caindo = alca/tunel a menos, i.e. cavidade ou furo fechado
        "fechou_cavidade": _compara(antes, depois, "genus", operator.gt),
        "criou_nao_manifold": _compara(antes, depois, "n_arestas_nao_manifold_estrito", operator.lt),
        "delta_componentes": _delta(antes, depois, "n_componentes"),
        "delta_euler": _delta(antes, depois, "euler_number"),
        "delta_boundary_edges": _delta(antes, depois, "n_boundary_edges"),
        "delta_nao_manifold_edges": _delta(antes, depois, "n_arestas_nao_manifold_estrito"),
        "delta_self_intersections": _delta(antes, depois, "n_self_intersections"),
        "delta_genus": _delta(antes, depois, "genus"),
        "delta_faces_degeneradas": _delta(antes, depois, "n_faces_degeneradas"),
        "delta_vertices_isolados": _delta(antes, depois, "n_vertices_isolados"),
        "delta_area_mm2": _delta(antes, depois, "area_mm2"),
        "delta_volume_ml": _delta(antes, depois, "volume_ml_se_watertight"),
    }


def continuidade_vaso(mask: np.ndarray, zooms: np.ndarray) -> dict:
    """Continuidade de estrutura tubular: quantos pedacos e qual o comprimento.

    `comprimento_esqueleto_mm` e APROXIMADO: soma dos voxels do esqueleto x
    spacing medio. Subestima trecho diagonal (passo real ate sqrt(3)x maior) e
    so serve para COMPARAR duas versoes da mesma estrutura na mesma grade.
    skimage >= 0.26 removeu `skeletonize_3d`; `skeletonize` trata 3D nativamente.
    """
    mask = np.asarray(mask) > 0.5
    zooms = np.asarray(zooms, dtype=float)
    total = int(mask.sum())
    if total == 0:
        return {"n_componentes": 0, "fracao_maior_componente": 0.0, "comprimento_esqueleto_mm": 0.0}

    rotulos, n = ndimage.label(mask, structure=CONECTIVIDADE)
    tamanhos = np.bincount(rotulos.ravel())[1:]
    esqueleto = skeletonize(mask)
    passo_mm = float(np.mean(zooms))

    return {
        "n_componentes": int(n),
        "fracao_maior_componente": round(float(tamanhos.max()) / total, 5),
        "comprimento_esqueleto_mm": round(float(esqueleto.sum()) * passo_mm, 2),
    }


def comparar_continuidade(mask_ref: np.ndarray, mesh: trimesh.Trimesh, affine: np.ndarray) -> dict:
    """Detecta vaso que FRAGMENTOU ou sumiu ao virar malha.

    Rasteriza a malha na mesma grade da mascara e compara a continuidade das
    duas. `delta_componentes > 0` = fragmentou; `fracao_maior_componente` caindo
    = perdeu um ramo; comprimento de esqueleto caindo = encurtou/afinou.
    """
    mask_ref = np.asarray(mask_ref) > 0.5
    zooms = zooms_de(affine)
    rasterizada = voxelizar_malha(mesh, mask_ref.shape, affine)

    ref = continuidade_vaso(mask_ref, zooms)
    mal = continuidade_vaso(rasterizada, zooms)
    comp_ref = ref["comprimento_esqueleto_mm"]
    return {
        "mascara": ref,
        "malha": mal,
        "delta_componentes": mal["n_componentes"] - ref["n_componentes"],
        "delta_comprimento_pct": (
            round((mal["comprimento_esqueleto_mm"] - comp_ref) / comp_ref * 100.0, 2) if comp_ref else float("nan")
        ),
        "fragmentou": mal["n_componentes"] > ref["n_componentes"],
        "sumiu": mal["n_componentes"] == 0,
        "referencia": "benchmark_interno",  # a mascara nao e ground truth clinico
    }


def _demo() -> None:
    import json
    from pathlib import Path

    import nibabel as nib

    from ..geometry.reconstruction import reconstruct_surface
    from .phantom import tubo_fino

    raiz = Path(__file__).resolve().parents[2] / ".clinica-dados" / "torax-alta_masks"
    casos: list[tuple[str, np.ndarray, np.ndarray]] = []
    for nome in ("aorta", "trachea"):
        img = nib.load(str(raiz / f"{nome}.nii.gz"))
        casos.append((nome, np.asarray(img.dataobj) > 0.5, img.affine))
    mask_tubo, aff_tubo = tubo_fino(3.0, 40.0, spacing=(0.7, 0.7, 0.7))
    casos.append(("fantoma_tubo_3mm", mask_tubo, aff_tubo))

    for nome, mask, affine in casos:
        zooms = zooms_de(affine)
        base = continuidade_vaso(mask, zooms)
        print(f"\n=== {nome} shape={mask.shape} voxels={int(mask.sum())} zooms={np.round(zooms, 3).tolist()}")
        print("  mascara:", json.dumps(base))
        for metodo in ("marching_cubes", "surface_nets"):
            r = reconstruct_surface(mask, affine, method=metodo)
            if r is None:
                print(f"  [{metodo}] AUSENTE (estrutura nao sobreviveu)")
                continue
            print(f"  [{metodo}] topologia:", json.dumps(qualidade_topologica(r.mesh)))
            c = comparar_continuidade(mask, r.mesh, affine)
            print(f"  [{metodo}] continuidade:", json.dumps({k: v for k, v in c.items() if k != "mascara"}))

    # check minimo: esfera de trimesh e sa; um tubo inteiro nao tem 2 componentes
    q = qualidade_topologica(trimesh.creation.icosphere(subdivisions=2, radius=0.01))
    assert q["watertight"] and q["n_componentes"] == 1 and q["n_arestas_nao_manifold"] == 0, q
    assert continuidade_vaso(mask_tubo, zooms_de(aff_tubo))["n_componentes"] == 1
    print("\nOK: checks minimos passaram")


def _autoteste() -> None:
    """Metricas de falha topologica em malha de referencia, sem dado real.

        python -m scripts.validation.topology_metrics --autoteste
    """
    import json

    # 1. Esfera: fechada, um corpo, sem borda, sem nao-manifold, genero 0.
    esfera = trimesh.creation.icosphere(subdivisions=3, radius=0.01)
    q = qualidade_topologica(esfera)
    print(f"1) icosfera r=10 mm  faces={len(esfera.faces)}")
    print("   ", json.dumps(q))
    assert q["watertight"] is True, q
    assert q["n_componentes"] == 1, q
    assert q["n_boundary_edges"] == 0, q
    assert q["n_arestas_nao_manifold_estrito"] == 0, q
    assert q["genus"] == 0, q
    assert q["n_self_intersections"] == 0, q
    assert q["n_arestas_nao_manifold"] == q["n_boundary_edges"] + q["n_arestas_nao_manifold_estrito"], q
    assert _e_numero(q["volume_ml_se_watertight"]), q
    print("   OK: watertight, 1 componente, 0 borda, 0 nao-manifold, genus 0, 0 auto-interseccao")

    # 2. Toro: uma alca => genero 1. euler = 0 numa superficie fechada.
    toro = trimesh.creation.torus(major_radius=0.02, minor_radius=0.005)
    qt = qualidade_topologica(toro)
    print(f"\n2) toro R=20 mm r=5 mm  faces={len(toro.faces)}")
    print("   ", json.dumps(qt))
    assert qt["watertight"] is True, qt
    assert qt["genus"] == 1, qt
    print(f"   OK: genus=1 (euler={qt['euler_number']}, componentes={qt['n_componentes']})")

    # 3. Malha aberta: buraco => borda aberta, nao fechada, volume sem sentido.
    aberta = trimesh.Trimesh(vertices=esfera.vertices.copy(), faces=esfera.faces[:-10].copy(), process=False)
    qa = qualidade_topologica(aberta)
    print(f"\n3) icosfera com 10 faces removidas  faces={len(aberta.faces)}")
    print("   ", json.dumps(qa))
    assert qa["n_boundary_edges"] > 0, qa
    assert qa["watertight"] is False, qa
    assert qa["volume_ml_se_watertight"] == "invalido", qa
    assert qa["genus"] == "nao aplicavel", qa
    print(f"   OK: {qa['n_boundary_edges']} boundary edges, watertight=False, volume='invalido', genus='nao aplicavel'")

    # 4. comparar_topologia: 3 componentes viraram 1 => fusao.
    c = comparar_topologia({"n_componentes": 3}, {"n_componentes": 1})
    print("\n4) comparar_topologia({n_componentes:3} -> {n_componentes:1})")
    print("   ", json.dumps(c))
    assert c["fundiu_componentes"] is True, c
    assert c["fragmentou"] is False, c
    assert c["delta_componentes"] == -2, c
    # chaves ausentes nao viram False: propagam a string
    assert c["abriu_malha"] == "nao medido", c
    assert c["fechou_cavidade"] == "nao medido", c
    assert c["delta_volume_ml"] == "nao medido", c
    print("   OK: fundiu_componentes=True, delta=-2, campos sem insumo propagam 'nao medido'")

    # 5. comparar_topologia esfera -> aberta: propagacao com valores reais.
    ca = comparar_topologia(q, qa)
    print("\n5) comparar_topologia(icosfera -> icosfera aberta)")
    print("   ", json.dumps(ca))
    assert ca["abriu_malha"] is True, ca
    assert ca["delta_boundary_edges"] == qa["n_boundary_edges"], ca
    assert ca["fechou_cavidade"] == "nao aplicavel", ca  # genus do 'depois' nao existe
    assert ca["delta_volume_ml"] == "invalido", ca
    assert ca["fundiu_componentes"] is False, ca
    print("   OK: abriu_malha=True; genus/volume ausentes propagam a string, nao viram False")

    # 6. Auto-interseccao com sinal: duas esferas sobrepostas na mesma malha.
    a = trimesh.creation.icosphere(subdivisions=2, radius=0.01)
    b = trimesh.creation.icosphere(subdivisions=2, radius=0.01)
    b.apply_translation([0.01, 0.0, 0.0])
    suja = trimesh.util.concatenate([a, b])
    qs = qualidade_topologica(suja)
    print(f"\n6) duas icosferas sobrepostas  faces={len(suja.faces)}")
    print("   ", json.dumps(qs))
    assert isinstance(qs["n_self_intersections"], int) and qs["n_self_intersections"] > 0, qs
    assert qs["n_componentes"] == 2, qs
    print(f"   OK: {qs['n_self_intersections']} pares auto-intersectados (0 na esfera limpa do check 1)")

    print("\nOK: autoteste de topologia passou")


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Qualidade topologica de malha e continuidade de estrutura tubular.")
    p.add_argument("--autoteste", action="store_true", help="checks em malha de referencia, sem dado real")
    args = p.parse_args()
    _autoteste() if args.autoteste else _demo()


if __name__ == "__main__":
    main()
