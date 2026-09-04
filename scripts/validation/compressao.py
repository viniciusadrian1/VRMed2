"""Bloco D da decomposicao de erro: quanto a compressao Draco desloca a geometria.

PERGUNTA: o KHR_draco_mesh_compression e lossy (quantiza posicao). Quanto ele
move a superficie, e o que ele faz com a topologia?

POR QUE ISSO ESTAVA BLOQUEADO ATE AGORA
    `trimesh` NAO decodifica Draco. Ele avisa
        "`KHR_draco_mesh_compression` GLTF extension has no handler,
         values are placeholder zeros"
    e devolve a malha com a contagem certa de vertices e faces mas TODAS as
    posicoes em zero (area 0.0, extents [0,0,0]). Qualquer metrica calculada em
    cima disso e numero falso com cara de numero bom — foi por isso que
    `error_decomposition.erro_compressao` sempre devolveu
    `desvio_geometrico.verificavel = False`.

DECODER USADO AQUI: DracoPy (binding do decoder oficial do Google). Roda o mesmo
codigo que o navegador roda no DRACOLoader, entao o que medimos e o que o
usuario final ve. Alternativa conferida e funcional, mas NAO usada: ver
`ALTERNATIVAS_CONFERIDAS` no fim deste modulo.

COMO COMPARAMOS (importa, porque muda o significado do numero)
    Draco quantiza as posicoes e re-solda vertices; a contagem de vertices e de
    faces MUDA (medido: lung_left 21539 -> 21546 vertices, 43080 -> 43078 faces).
    Logo NAO existe correspondencia indice-a-indice e comparar `v[i]` com `v[i]`
    seria comparar vertices diferentes. Usamos duas medidas, com significados
    distintos, nenhuma delas agregada com a outra:

    1. DESLOCAMENTO DE VERTICE (`erro_vertice_*_mm`) — de cada vertice decodificado
       ate o vertice ORIGINAL mais proximo (KD-tree). E a medida direta da
       quantizacao. So e interpretavel enquanto o deslocamento for muito menor
       que o espacamento entre vertices; acima de 1/4 da aresta mediana o vizinho
       mais proximo deixa de ser "o mesmo vertice" e a chave sai como string.
    2. DISTANCIA PONTO-SUPERFICIE (`hausdorff_amostrado_mm`, `rms_mm`) —
       reaproveita `mesh_metrics.comparar_malhas`, simetrica, por amostragem da
       superficie. Nao exige correspondencia nenhuma.

O INSTRUMENTO 2 TEM PISO DE RUIDO — LEIA ANTES DE CITAR O NUMERO
    `comparar_malhas` chamada com a MESMA malha nos dois lados NAO devolve zero.
    Medido em lung_left (43 080 faces, 20 000 amostras por lado):
        comparar_malhas(m, m) -> hausdorff 0,1721 mm | rms 0,0063 mm
        comparar_malhas(antes, depois_draco) -> hausdorff 0,1871 mm | rms 0,0072 mm
    A resposta verdadeira do primeiro caso e exatamente 0. A causa e o
    `trimesh.proximity.closest_point`: o candidato vem de `nearby_faces`, que
    parte do VERTICE mais proximo e testa so as faces incidentes — quando o pe
    da perpendicular cai num triangulo que nao toca esse vertice, a funcao
    devolve uma distancia MAIOR que a real. E superestimacao, nao ruido aleatorio.
    Consequencia direta: para o bloco D o sinal do Draco (~0,01 mm) esta uma
    ordem de grandeza ABAIXO do piso do instrumento (~0,17 mm de Hausdorff), e
    as duas chaves de superficie sao INCONCLUSIVAS aqui. Por isso cada malha
    carrega seu proprio `piso_ruido_instrumento` (a mesma funcao, mesma malha nos
    dois lados, mesma semente) e um `veredito_superficie` explicito. O numero
    fica no relatorio, mas nunca sozinho.
    O deslocamento de vertice (instrumento 1, KD-tree exata da scipy) nao tem
    esse problema — controle de identidade da 0,0 cravado — e e a medida em que
    o bloco D se apoia.

CONVENCAO DE VALOR AUSENTE (a mesma de topology_metrics, nao negociavel):
    "nao medido" / "nao aplicavel" / "invalido". Volume de malha aberta sai
    "invalido" — nao existe volume sem fronteira fechada.

Nao ha claim clinico aqui: e controle de qualidade geometrico.

Uso:
    python -m scripts.validation.compressao --autoteste
    python -m scripts.validation.compressao \
        --antes .clinica-dados/cta-cardio/cta-cardio-sem-draco.glb \
        --depois .clinica-dados/cta-cardio/cta-cardio.glb
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from .mesh_metrics import AMOSTRAS_PADRAO, comparar_malhas
from .topology_metrics import comparar_topologia, qualidade_topologica

# componentType do glTF -> dtype numpy
_DTYPE_GLTF = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NCOMP_GLTF = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

# Acima disso o vizinho mais proximo deixa de identificar "o mesmo vertice":
# o deslocamento passa a poder trocar de vertice de destino e a media vira lixo.
FRACAO_ARESTA_CONFIAVEL = 0.25

# Padrao do `gltf-transform draco` para POSITION. Nao esta gravado no GLB de
# forma que o DracoPy exponha, entao entra como PREVISAO a refutar, nunca como
# medida: se o deslocamento medido nao couber nesse passo, o instrumento (ou a
# hipotese sobre o encoder) esta errado.
BITS_QUANTIZACAO_PREVISTOS = 14


class DecoderIndisponivel(RuntimeError):
    """DracoPy ausente/quebrado: bloco D vira 'bloqueado', nunca um numero."""


def _decodificar_draco(blob: bytes) -> tuple[np.ndarray, np.ndarray]:
    try:
        import DracoPy
    except ImportError as e:  # pragma: no cover - depende do ambiente
        raise DecoderIndisponivel(
            f"DracoPy nao importavel ({e}). Instale com: pip install DracoPy"
        ) from e
    malha = DracoPy.decode(blob)
    return np.asarray(malha.points, dtype=np.float64), np.asarray(malha.faces, dtype=np.int64).reshape(-1, 3)


# --------------------------------------------------------------- leitura do GLB


def _ler_glb(caminho: Path) -> tuple[dict, bytes]:
    """Devolve (json do glTF, chunk BIN). Um leitor so para os dois lados.

    Deliberadamente NAO usamos `trimesh.load` no lado sem Draco: o loader do
    trimesh processa a malha (funde vertices, reordena) e isso introduziria uma
    diferenca ANTES x DEPOIS que nao veio do Draco. Mesmo leitor dos dois lados,
    mesmo tratamento, `process=False`.
    """
    b = caminho.read_bytes()
    if b[:4] != b"glTF":
        raise ValueError(f"{caminho} nao e um GLB binario (magic ausente)")
    tam_json = struct.unpack("<I", b[12:16])[0]
    gltf = json.loads(b[20 : 20 + tam_json])
    inicio_bin = 20 + tam_json
    tam_bin = struct.unpack("<I", b[inicio_bin : inicio_bin + 4])[0]
    return gltf, b[inicio_bin + 8 : inicio_bin + 8 + tam_bin]


def _ler_acessor(gltf: dict, binario: bytes, idx: int) -> np.ndarray:
    a = gltf["accessors"][idx]
    if "sparse" in a:
        raise ValueError("acessor sparse nao suportado neste leitor")
    dt = np.dtype(_DTYPE_GLTF[a["componentType"]])
    ncomp = _NCOMP_GLTF[a["type"]]
    bv = gltf["bufferViews"][a["bufferView"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    passo = bv.get("byteStride") or dt.itemsize * ncomp
    if passo == dt.itemsize * ncomp:  # compacto
        return np.frombuffer(binario, dtype=dt, count=a["count"] * ncomp, offset=base).reshape(a["count"], ncomp)
    linhas = np.frombuffer(binario, dtype=np.uint8, count=a["count"] * passo, offset=base).reshape(a["count"], passo)
    return linhas[:, : dt.itemsize * ncomp].copy().view(dt).reshape(a["count"], ncomp)


def _escala_de_no(no: dict) -> np.ndarray:
    """Escala do node (TRS ou matriz). Rotacao/translacao nao mudam distancia."""
    if "matrix" in no:
        m = np.asarray(no["matrix"], dtype=float).reshape(4, 4).T
        return np.linalg.norm(m[:3, :3], axis=0)
    return np.asarray(no.get("scale", [1.0, 1.0, 1.0]), dtype=float)


def ler_primitivas(caminho: str | Path) -> list[dict[str, Any]]:
    """Uma entrada por primitiva do GLB, com a malha ja em trimesh.

    Cada entrada: nome, mesh (trimesh, metros), bytes_geometria, fonte
    ("draco" | "accessor"), escala_nao_unitaria (bool).
    """
    caminho = Path(caminho)
    gltf, binario = _ler_glb(caminho)

    # escala por indice de mesh: distancia local so vale em mm se a escala for 1
    escala_por_mesh: dict[int, np.ndarray] = {}
    for no in gltf.get("nodes", []):
        if "mesh" in no:
            escala_por_mesh[no["mesh"]] = _escala_de_no(no)

    saida: list[dict[str, Any]] = []
    for i_mesh, m in enumerate(gltf.get("meshes", [])):
        for k, prim in enumerate(m["primitives"]):
            ext = prim.get("extensions", {}).get("KHR_draco_mesh_compression")
            if ext is not None:
                bv = gltf["bufferViews"][ext["bufferView"]]
                ini = bv.get("byteOffset", 0)
                verts, faces = _decodificar_draco(binario[ini : ini + bv["byteLength"]])
                n_bytes = int(bv["byteLength"])
                fonte = "draco"
            else:
                verts = _ler_acessor(gltf, binario, prim["attributes"]["POSITION"]).astype(np.float64)
                faces = _ler_acessor(gltf, binario, prim["indices"]).astype(np.int64).reshape(-1, 3)
                vistos = {gltf["accessors"][a]["bufferView"] for a in prim["attributes"].values()}
                vistos.add(gltf["accessors"][prim["indices"]]["bufferView"])
                n_bytes = int(sum(gltf["bufferViews"][b]["byteLength"] for b in vistos))
                fonte = "accessor"

            escala = escala_por_mesh.get(i_mesh, np.ones(3))
            nome = m.get("name") or f"mesh{i_mesh}"
            saida.append(
                {
                    "nome": nome if len(m["primitives"]) == 1 else f"{nome}#{k}",
                    "mesh": trimesh.Trimesh(vertices=verts, faces=faces, process=False),
                    "bytes_geometria": n_bytes,
                    "fonte": fonte,
                    "escala_nao_unitaria": bool(np.any(np.abs(escala - 1.0) > 1e-9)),
                }
            )
    return saida


# ------------------------------------------------------------------- metricas


def _aresta_mediana_mm(mesh: trimesh.Trimesh) -> float:
    v = mesh.vertices
    f = mesh.faces
    comp = np.concatenate(
        [
            np.linalg.norm(v[f[:, 0]] - v[f[:, 1]], axis=1),
            np.linalg.norm(v[f[:, 1]] - v[f[:, 2]], axis=1),
            np.linalg.norm(v[f[:, 2]] - v[f[:, 0]], axis=1),
        ]
    )
    return float(np.median(comp)) * 1000.0


def _deslocamento_vertices(antes: trimesh.Trimesh, depois: trimesh.Trimesh) -> dict[str, Any]:
    """Cada vertice decodificado ate o vertice ORIGINAL mais proximo, em mm.

    Mede a quantizacao em si, nao a aproximacao de superficie. Vale enquanto o
    deslocamento for << espacamento entre vertices; acima disso o pareamento por
    vizinho mais proximo e ambiguo e as chaves saem como string em vez de float.
    """
    d = cKDTree(antes.vertices).query(depois.vertices, k=1)[0] * 1000.0
    aresta = _aresta_mediana_mm(antes)
    limite = FRACAO_ARESTA_CONFIAVEL * aresta
    d_max = float(d.max())
    if aresta > 0 and d_max > limite:
        aviso = (
            f"nao confiavel (deslocamento maximo {d_max:.4f} mm >= "
            f"{FRACAO_ARESTA_CONFIAVEL} x aresta mediana {aresta:.4f} mm: "
            "vizinho mais proximo deixa de identificar o mesmo vertice)"
        )
        return {"erro_vertice_max_mm": aviso, "erro_vertice_rms_mm": aviso, "aresta_mediana_mm": round(aresta, 5)}
    return {
        "erro_vertice_max_mm": round(d_max, 6),
        "erro_vertice_rms_mm": round(float(np.sqrt(np.mean(d**2))), 6),
        "aresta_mediana_mm": round(aresta, 5),
    }


def _passo_quantizacao_previsto_mm(mesh: trimesh.Trimesh) -> float:
    """Passo da grade Draco previsto: maior extensao / (2^bits - 1), em mm.

    Draco quantiza numa grade CUBICA cobrindo a maior extensao da malha. Serve
    de teste de refutacao: o deslocamento medido tem de caber em ~metade disso.
    """
    return float(np.max(mesh.extents)) * 1000.0 / (2**BITS_QUANTIZACAO_PREVISTOS - 1)


def _veredito_superficie(medido: dict, piso: dict) -> str:
    """As chaves de superficie separam o Draco do proprio erro do instrumento?

    Exigimos o dobro do piso para chamar de sinal. Abaixo disso o numero existe
    mas nao mede o Draco — devolvemos "inconclusivo", nunca um float sozinho.
    """
    partes = []
    for chave in ("hausdorff_mm", "rms_mm"):
        p = float(piso[chave])
        m = float(medido[chave])
        ok = p > 0 and m >= 2.0 * p
        partes.append(f"{chave}={m} vs piso {p} -> {'sinal' if ok else 'inconclusivo'}")
    return "; ".join(partes)


def medir_par(
    antes: trimesh.Trimesh,
    depois: trimesh.Trimesh,
    *,
    amostras: int = AMOSTRAS_PADRAO,
    semente: int = 0,
) -> dict[str, Any]:
    """Erro geometrico e topologico de UMA malha antes x depois do Draco."""
    superficie = comparar_malhas(antes, depois, amostras=amostras, semente=semente)
    # controle obrigatorio: a MESMA funcao com a MESMA malha dos dois lados.
    # A resposta verdadeira e 0; o que sair daqui e o piso do instrumento.
    piso = comparar_malhas(antes, antes, amostras=amostras, semente=semente)
    topo_antes = qualidade_topologica(antes)
    topo_depois = qualidade_topologica(depois)

    # volume so existe em malha fechada — nos DOIS lados, senao a diferenca nao
    # e uma diferenca de volume. `comparar_malhas` calcula sempre; sobrescrevemos.
    volume_pct: float | str = superficie["volume_error_pct"]
    if not (topo_antes["watertight"] and topo_depois["watertight"]):
        volume_pct = "invalido"

    area_antes, area_depois = float(antes.area), float(depois.area)
    return {
        "n_vertices_antes": int(len(antes.vertices)),
        "n_vertices_depois": int(len(depois.vertices)),
        "n_faces_antes": int(len(antes.faces)),
        "n_faces_depois": int(len(depois.faces)),
        **_deslocamento_vertices(antes, depois),
        "passo_quantizacao_previsto_mm": round(_passo_quantizacao_previsto_mm(antes), 6),
        "hausdorff_amostrado_mm": superficie["hausdorff_mm"],
        "rms_mm": superficie["rms_mm"],
        "piso_ruido_instrumento": {
            "hausdorff_mm": piso["hausdorff_mm"],
            "rms_mm": piso["rms_mm"],
            "o_que_e": "comparar_malhas(antes, antes) — resposta verdadeira 0; o resto e o instrumento",
        },
        "veredito_superficie": _veredito_superficie(superficie, piso),
        "amostras_por_lado": int(amostras),
        "area_antes_m2": round(area_antes, 9),
        "area_depois_m2": round(area_depois, 9),
        "area_erro_pct": round((area_depois - area_antes) / area_antes * 100.0, 5) if area_antes else "invalido",
        "volume_erro_pct": volume_pct,
        "topologia_antes": topo_antes,
        "topologia_depois": topo_depois,
        "delta_topologia": comparar_topologia(topo_antes, topo_depois),
    }


def medir_compressao(
    caminho_antes: str | Path,
    caminho_depois: str | Path,
    *,
    amostras: int = AMOSTRAS_PADRAO,
    semente: int = 0,
) -> dict[str, Any]:
    """Bloco D sobre um par de GLB (mesma malha, um sem Draco e um com).

    Nunca agrega as malhas num numero so: cada estrutura tem sua propria linha.
    """
    caminho_antes, caminho_depois = Path(caminho_antes), Path(caminho_depois)
    try:
        prims_antes = ler_primitivas(caminho_antes)
        prims_depois = ler_primitivas(caminho_depois)
    except (DecoderIndisponivel, ValueError) as e:
        return {
            "disponivel": False,
            "classe": "bloqueado",
            "motivo": str(e),
            "arquivo_antes": str(caminho_antes),
            "arquivo_depois": str(caminho_depois),
        }

    if not any(p["fonte"] == "draco" for p in prims_depois):
        return {
            "disponivel": False,
            "classe": "bloqueado",
            "motivo": f"{caminho_depois.name} nao usa KHR_draco_mesh_compression: nao ha compressao a medir",
            "arquivo_antes": str(caminho_antes),
            "arquivo_depois": str(caminho_depois),
        }

    bytes_antes = caminho_antes.stat().st_size
    bytes_depois = caminho_depois.stat().st_size
    por_nome = {p["nome"]: p for p in prims_depois}

    malhas: list[dict[str, Any]] = []
    for pa in prims_antes:
        pd = por_nome.get(pa["nome"])
        linha: dict[str, Any] = {
            "nome": pa["nome"],
            "bytes_geometria_antes": pa["bytes_geometria"],
            "bytes_geometria_depois": pd["bytes_geometria"] if pd else "nao medido",
        }
        if pd is None:
            linha["erro"] = "nao medido: malha ausente no arquivo comprimido"
        elif pa["escala_nao_unitaria"] or pd["escala_nao_unitaria"]:
            # a malha esta em espaco local; com escala != 1 no node, mm sairia errado
            linha["erro"] = "nao medido: node com escala nao unitaria (distancia local nao e mm)"
        else:
            linha["ratio_compressao"] = round(pa["bytes_geometria"] / pd["bytes_geometria"], 3)
            linha.update(medir_par(pa["mesh"], pd["mesh"], amostras=amostras, semente=semente))
        malhas.append(linha)

    return {
        "disponivel": True,
        "classe": "medido",
        "tipo_referencia": "benchmark_interno",
        "referencia": "GLB sem Draco (mesma malha, mesmo pipeline)",
        "decoder": "DracoPy (decoder oficial do Google) — o mesmo que o DRACOLoader roda no navegador",
        "arquivo_antes": str(caminho_antes),
        "arquivo_depois": str(caminho_depois),
        "bytes_arquivo_antes": int(bytes_antes),
        "bytes_arquivo_depois": int(bytes_depois),
        "ratio_compressao_arquivo": round(bytes_antes / bytes_depois, 3),
        "reducao_bytes_pct": round((1.0 - bytes_depois / bytes_antes) * 100.0, 2),
        "malhas": malhas,
    }


# ------------------------------------------------------------------- autoteste

ALTERNATIVAS_CONFERIDAS = {
    "trimesh 5.0.0": (
        "NAO decodifica. Avisa '`KHR_draco_mesh_compression` GLTF extension has no handler, "
        "values are placeholder zeros' e devolve contagem correta de vertices/faces com TODAS "
        "as posicoes em zero (area=0.0, extents=[0,0,0]). Fonte de numero falso — bloqueio original."
    ),
    "pygltflib 1.16.5": "le a estrutura do glTF, nao decodifica geometria Draco. Nao serve sozinho.",
    "npx @gltf-transform/cli@latest copy <draco.glb> <saida.glb>": (
        "FUNCIONA: descomprime ('warn: Decoded KHR_draco_mesh_compression', 598 KB -> 2,92 MB). "
        "Nao usado aqui porque o round-trip passa a malha pelo WRITER do gltf-transform, que "
        "re-indexa por conta propria — a diferenca medida deixaria de ser so do Draco."
    ),
    "DracoPy 2.0.0": "USADO. Wheel pronta cp313 win_amd64, sem compilar. decode() no blob do bufferView.",
}


def _autoteste() -> int:
    """Valida o INSTRUMENTO antes de acreditar em qualquer numero que ele der.

    Cinco controles, cada um capaz de reprovar o decoder:
      1. round-trip sintetico com passo de quantizacao CONHECIDO -> o
         deslocamento medido tem de caber em meio passo;
      2. controle de identidade: malha contra ela mesma da erro exatamente 0;
      3. controle negativo: as posicoes decodificadas NAO sao zeros (o modo de
         falha exato do trimesh);
      4. contagem decodificada bate com o `count` do acessor no glTF;
      5. o deslocamento real cabe no passo previsto de 14 bits.
    """
    import DracoPy

    falhas: list[str] = []

    def checa(nome: str, ok: bool, detalhe: str) -> None:
        print(f"  [{'ok ' if ok else 'FALHA'}] {nome}: {detalhe}")
        if not ok:
            falhas.append(nome)

    print("autoteste do decoder Draco")
    print(f"  DracoPy importado de {DracoPy.__file__}")

    # 1) round-trip sintetico: passo de quantizacao conhecido, erro previsto
    esfera = trimesh.creation.icosphere(subdivisions=3, radius=0.05)
    bits = 12
    blob = DracoPy.encode(esfera.vertices.astype(np.float32), esfera.faces, quantization_bits=bits)
    v, f = _decodificar_draco(blob)
    passo_mm = float(np.max(esfera.extents)) * 1000.0 / (2**bits - 1)
    d_max = float(cKDTree(esfera.vertices).query(v, k=1)[0].max()) * 1000.0
    checa(
        "round-trip sintetico dentro do passo",
        d_max <= 0.87 * passo_mm,  # sqrt(3)/2 = 0.866: pior caso no canto da celula cubica
        f"erro max {d_max:.6f} mm, passo {bits} bits = {passo_mm:.6f} mm",
    )
    checa("round-trip preserva faces", len(f) == len(esfera.faces), f"{len(esfera.faces)} -> {len(f)}")

    # 2) identidade: nenhuma diferenca inventada quando nao ha diferenca
    ident = _deslocamento_vertices(esfera, esfera)
    checa("controle de identidade", ident["erro_vertice_max_mm"] == 0.0, f"erro max {ident['erro_vertice_max_mm']}")

    # 3/4/5) arquivo real do repositorio
    raiz = Path(__file__).resolve().parents[2]
    antes_p = raiz / ".clinica-dados" / "cta-cardio" / "cta-cardio-sem-draco.glb"
    depois_p = raiz / ".clinica-dados" / "cta-cardio" / "cta-cardio.glb"
    if not (antes_p.exists() and depois_p.exists()):
        checa("par real disponivel", False, f"nao medido: ausente {antes_p} ou {depois_p}")
        return 1 if falhas else 0

    gltf, _ = _ler_glb(depois_p)
    prims = ler_primitivas(depois_p)
    checa("arquivo alvo usa Draco", all(p["fonte"] == "draco" for p in prims), f"{len(prims)} primitivas")

    m0 = prims[0]["mesh"]
    checa(
        "posicoes NAO sao zeros (modo de falha do trimesh)",
        float(m0.area) > 0.0 and bool(np.any(np.asarray(m0.extents) > 1e-9)),
        f"area {float(m0.area):.6f} m2, extents {np.round(m0.extents, 5).tolist()}",
    )

    esperado = gltf["accessors"][gltf["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]["count"]
    checa("contagem decodificada = count do acessor", len(m0.vertices) == esperado, f"{len(m0.vertices)} vs {esperado}")

    orig = ler_primitivas(antes_p)[0]["mesh"]
    desloc = _deslocamento_vertices(orig, m0)
    passo = _passo_quantizacao_previsto_mm(orig)
    ok_passo = isinstance(desloc["erro_vertice_max_mm"], float) and desloc["erro_vertice_max_mm"] <= 0.87 * passo
    checa(
        "deslocamento real cabe no passo previsto de 14 bits",
        ok_passo,
        f"erro max {desloc['erro_vertice_max_mm']} mm, passo previsto {passo:.6f} mm",
    )

    # informativo, sem pass/fail: piso de ruido do instrumento 2 na malha real.
    # Nao entra como falha porque nao e defeito deste modulo — e limitacao
    # conhecida do closest_point do trimesh, e o que importa e ficar VISIVEL.
    piso = comparar_malhas(orig, orig, amostras=4000, semente=0)
    par = comparar_malhas(orig, m0, amostras=4000, semente=0)
    print(
        "  [info] piso de ruido de comparar_malhas (mesma malha dos dois lados, "
        f"resposta verdadeira 0): hausdorff {piso['hausdorff_mm']} mm, rms {piso['rms_mm']} mm"
    )
    print(f"  [info] antes x depois pela mesma funcao: hausdorff {par['hausdorff_mm']} mm, rms {par['rms_mm']} mm")
    print(f"  [info] veredito: {_veredito_superficie(par, piso)}")

    print(f"\n{'AUTOTESTE OK' if not falhas else 'AUTOTESTE REPROVOU: ' + ', '.join(falhas)}")
    return 0 if not falhas else 1


def main() -> int:
    import argparse

    raiz = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description="Bloco D: erro geometrico introduzido pela compressao Draco.")
    ap.add_argument("--antes", default=str(raiz / ".clinica-dados/cta-cardio/cta-cardio-sem-draco.glb"))
    ap.add_argument("--depois", default=str(raiz / ".clinica-dados/cta-cardio/cta-cardio.glb"))
    ap.add_argument("--amostras", type=int, default=AMOSTRAS_PADRAO)
    ap.add_argument("--semente", type=int, default=0)
    ap.add_argument("--json", default=None, help="grava o relatorio completo neste caminho")
    ap.add_argument("--autoteste", action="store_true", help="valida o decoder e sai")
    args = ap.parse_args()

    if args.autoteste:
        try:
            return _autoteste()
        except DecoderIndisponivel as e:
            print(f"BLOQUEADO: {e}")
            for nome, nota in ALTERNATIVAS_CONFERIDAS.items():
                print(f"  - {nome}: {nota}")
            return 2

    rel = medir_compressao(args.antes, args.depois, amostras=args.amostras, semente=args.semente)
    if not rel["disponivel"]:
        print(f"BLOQUEADO: {rel['motivo']}")
        return 2

    print(f"{Path(rel['arquivo_antes']).name} -> {Path(rel['arquivo_depois']).name}")
    print(
        f"  arquivo: {rel['bytes_arquivo_antes']} -> {rel['bytes_arquivo_depois']} bytes "
        f"(ratio {rel['ratio_compressao_arquivo']}x, -{rel['reducao_bytes_pct']}%)"
    )
    print("  deslocamento de vertice = medida do bloco D. haus/rms de superficie vem com o PISO do")
    print("  instrumento ao lado (comparar_malhas contra a propria malha); sem sinal acima do piso,")
    print("  a coluna de superficie e inconclusiva.")
    print(
        f"  {'malha':24s} {'vmax_mm':>9s} {'rms_v_mm':>9s} {'haus_mm':>9s} {'haus_piso':>9s} "
        f"{'rms_s_mm':>9s} {'rms_piso':>9s} {'area_%':>9s} {'vol_%':>10s} {'ratio':>7s}"
    )
    for m in rel["malhas"]:
        if "erro" in m:
            print(f"  {m['nome']:24s} {m['erro']}")
            continue
        piso = m["piso_ruido_instrumento"]
        print(
            f"  {m['nome']:24s} {m['erro_vertice_max_mm']:>9} {m['erro_vertice_rms_mm']:>9} "
            f"{m['hausdorff_amostrado_mm']:>9} {piso['hausdorff_mm']:>9} "
            f"{m['rms_mm']:>9} {piso['rms_mm']:>9} {m['area_erro_pct']:>9} "
            f"{m['volume_erro_pct']:>10} {m['ratio_compressao']:>7}"
        )
    if args.json:
        Path(args.json).write_text(json.dumps(rel, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  relatorio -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
