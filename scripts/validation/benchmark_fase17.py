"""Fase 17 — benchmark profundo de reconstrucao de superficie.

REGRA QUE GOVERNA ESTE MODULO
O MASTER (marching_cubes · sigma=0 · Taubin=4 · level=0.5 · offset=0 · sem decimacao)
NAO E SUBSTITUIDO POR NADA QUE ESTE ARQUIVO MEDIR. Variante que superar o MASTER sai
como CANDIDATA e nada mais. A promocao e decisao humana, com fase propria.

POR QUE FANTOMA E NAO CASO REAL
Aqui a resposta certa e conhecida em forma fechada: a esfera tem pi/6*d^3, o cilindro
pi/4*d^2*h, o tubo oco tem cavidade que existe ou nao. Num caso real o "erro" de
reconstrucao se confunde com o erro de segmentacao, e a Fase 10 mostrou o quanto isso
custa. Aqui a unica fonte de erro e a reconstrucao — que e exatamente o objeto da fase.

O QUE A COMPARACAO MASCARA-x-MALHA MEDE, E O QUE ELA NAO MEDE
Dice/ASSD/HD95 de malha contra a mascara que a gerou sao TAUTOLOGICOS quando sigma=0:
a malha rasterizada de volta reproduz a mascara por construcao. Eles entram como
controle de sanidade e como detector de dano (decimacao, suavizacao agressiva), NUNCA
como prova de acuracia anatomica. O numero que informa de verdade nos fantomas e o
erro contra a FORMULA.

CHECKPOINT
Cada linha e gravada assim que sai. Interromper a execucao perde a linha em curso, nunca
o que ja foi medido. Rodar de novo com --retomar pula o que ja esta no CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import traceback
from pathlib import Path

import numpy as np
import trimesh

from scripts.geometry import reconstruction as R
from scripts.validation import mesh_metrics as MM
from scripts.validation import phantom as P
from scripts.validation import topology_metrics as TM

SAIDA = Path("docs/overnight/reconstruction_benchmark.csv")
BRUTO = Path(".clinica-dados/overnight/fase17")

COLUNAS = [
    "variant", "structure", "volume_ml", "surface_area_mm2", "dice", "iou",
    "assd_mm", "hd95_mm", "components", "watertight", "boundary_edges",
    "nonmanifold_edges", "triangles", "vertices", "processing_time_s",
    "glb_size_mb", "notes",
]

# ------------------------------------------------------------------ variantes
# `derivada` marca o que so pode ser aplicado SOBRE o MASTER, nunca no lugar dele.
VARIANTES = [
    # A — o MASTER congelado. Primeira linha de proposito: e a referencia.
    ("MASTER_mc_taubin4", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=4,
                              level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    # B — sem suavizacao nenhuma na malha
    ("mc_taubin0", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=0,
                        level=0.5, offset_mm=0.0, mesh_smoothing="none")),
    # C — varredura de Taubin
    ("mc_taubin2", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=2,
                        level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    ("mc_taubin8", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=8,
                        level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    ("mc_taubin12", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=12,
                         level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    ("mc_taubin20", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=20,
                         level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    # D — Surface Nets (EXPERIMENTAL; o MASTER continua Marching Cubes)
    # SURFACE NETS — EXPERIMENTAL. Uma variante so, de proposito: `reconstruction.py`
    # fixa `suavizar_malha=False` para este metodo (linha 315), entao ele usa a
    # suavizacao interna do vtkSurfaceNets3D e IGNORA taubin_iters/mesh_smoothing.
    # A primeira versao deste benchmark listava duas variantes e mediu a mesma coisa
    # duas vezes — verificado: os vertices sao byte a byte identicos entre
    # taubin=4 e taubin=0, enquanto em marching_cubes eles diferem.
    ("surface_nets", dict(method="surface_nets", sigma_mm=0.0, taubin_iters=4,
                          level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    # E — outras extracoes do VTK/skimage disponiveis
    ("flying_edges", dict(method="flying_edges", sigma_mm=0.0, taubin_iters=4,
                          level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    ("sdf", dict(method="sdf", sigma_mm=0.0, taubin_iters=4,
                 level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
    # F — outro filtro de malha, mesmo extrator
    ("mc_windowed_sinc", dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=4,
                              level=0.5, offset_mm=0.0, mesh_smoothing="windowed_sinc")),
    # sigma>0 borra a OCUPACAO antes de extrair — e a alavanca mais destrutiva que
    # existe aqui, e por isso e medida em vez de suposta.
    ("mc_sigma1_taubin4", dict(method="marching_cubes", sigma_mm=1.0, taubin_iters=4,
                               level=0.5, offset_mm=0.0, mesh_smoothing="taubin")),
]

# G/H — derivadas: aplicadas SOBRE a malha do MASTER, nunca no lugar dela.
DERIVADAS = [("LOD_decim50", 0.50), ("LOD_decim25", 0.25), ("LOD_decim10", 0.10)]

# ------------------------------------------------------------------- fantomas
# Cada um existe para estressar uma coisa. `analitico` e o volume em mm3 quando ha
# formula fechada; None quando a referencia e a propria mascara.
def _fantomas() -> list[tuple[str, tuple, float | None, str]]:
    iso = (1.0, 1.0, 1.0)
    aniso = (0.977, 0.977, 3.0)  # a grade real do LCTSC — anisotropia de 3x
    d = 20.0
    return [
        ("esfera_d20_iso", P.esfera(d, iso), np.pi / 6 * d ** 3, "curvatura alta, formula fechada"),
        ("esfera_d20_aniso", P.esfera(d, aniso), np.pi / 6 * d ** 3, "mesma esfera na grade do LCTSC"),
        ("esfera_d6_iso", P.esfera(6.0, iso), np.pi / 6 * 6.0 ** 3, "estrutura PEQUENA"),
        ("cilindro_d10_h40", P.cilindro(10.0, 40.0, iso), np.pi / 4 * 100.0 * 40.0, "formula fechada"),
        ("tubo_fino_d3", P.tubo_fino(3.0, 40.0, iso), np.pi / 4 * 9.0 * 40.0, "estrutura FINA (3 mm)"),
        ("tubo_fino_d2_aniso", P.tubo_fino(2.0, 40.0, aniso), np.pi / 4 * 4.0 * 40.0, "fina + anisotropia"),
        ("tubo_oco_20_12", P.tubo_oco(20.0, 12.0, 40.0, iso), None, "CAVIDADE que nao pode fechar"),
        ("esfera_cavidade_20_10", P.esfera_com_cavidade(20.0, 10.0, iso), None, "cavidade interna"),
        ("bifurcacao_d8", P.bifurcacao(8.0, 30.0, 45.0, iso), None, "juncao, alta curvatura"),
        ("dois_cilindros_contato", P.dois_cilindros_em_contato(10.0, 30.0, iso), None, "FUSAO de estruturas"),
        ("duas_estruturas_gap2", P.duas_estruturas_adjacentes(2.0, iso), None, "2 componentes, gap 2 mm"),
        ("ponte_fina_gap4", P.ponte_fina(10.0, 4.0, iso), None, "ponte fina: preservar ou romper"),
        ("cortada_d20", P.estrutura_parcialmente_cortada(20.0, iso), None, "superficie ABERTA no corte"),
    ]


def _tamanho_glb_mb(mesh: trimesh.Trimesh) -> float | None:
    try:
        return len(trimesh.Scene(mesh).export(file_type="glb")) / 1e6
    except Exception:
        return None


def _linha(variante: str, estrutura: str, mesh, mask, affine, dt: float,
           nota: str) -> dict:
    """Uma linha do CSV. Falha de metrica vira campo vazio + nota, nunca excecao."""
    L = {c: "" for c in COLUNAS}
    L["variant"], L["structure"] = variante, estrutura
    L["processing_time_s"] = round(dt, 4)
    notas = [nota] if nota else []

    if mesh is None:
        L["notes"] = "; ".join(notas + ["SUPERFICIE VAZIA — extracao nao produziu geometria"])
        return L

    L["triangles"] = int(len(mesh.faces))
    L["vertices"] = int(len(mesh.vertices))
    # A malha sai em METROS (convencao glTF do projeto). Area em mm2 exige 1e6.
    L["surface_area_mm2"] = round(float(mesh.area) * 1e6, 3)
    L["glb_size_mb"] = round(v, 6) if (v := _tamanho_glb_mb(mesh)) is not None else ""

    try:
        topo = TM.qualidade_topologica(mesh)
        # Os nomes reais de `qualidade_topologica` — a primeira versao deste
        # arquivo usou chaves inventadas e gravou tres colunas VAZIAS sem erro
        # nenhum. `.get` com default silencioso e o modo classico de perder dado.
        L["components"] = topo.get("n_componentes", "")
        L["watertight"] = topo.get("watertight", "")
        L["boundary_edges"] = topo.get("n_boundary_edges", "")
        L["nonmanifold_edges"] = topo.get("n_arestas_nao_manifold", "")
        for chave, valor in (("n_componentes", L["components"]),
                             ("n_boundary_edges", L["boundary_edges"])):
            if valor == "":
                notas.append(f"topologia sem a chave {chave}")
    except Exception as e:
        notas.append(f"topologia falhou: {type(e).__name__}")

    try:
        cmp_ = MM.comparar_mascara_malha(mask, mesh, affine)
        for csv_key, m_key in (("dice", "dice"), ("iou", "iou"),
                               ("assd_mm", "assd_mm"), ("hd95_mm", "hd95_mm"),
                               ("volume_ml", "volume_malha_ml")):
            v2 = cmp_.get(m_key)
            L[csv_key] = round(v2, 6) if isinstance(v2, (int, float)) else ""
        if not L["volume_ml"]:
            L["volume_ml"] = round(MM.volume_ml(mesh), 6)
    except Exception as e:
        notas.append(f"fidelidade falhou: {type(e).__name__}")
        try:
            L["volume_ml"] = round(MM.volume_ml(mesh), 6)
        except Exception:
            pass

    L["notes"] = "; ".join(notas)
    return L


def _erro_analitico(L: dict, analitico_mm3: float | None) -> str:
    """Erro percentual contra a formula fechada — o unico numero nao tautologico."""
    if analitico_mm3 is None or not L.get("volume_ml"):
        return ""
    medido_mm3 = float(L["volume_ml"]) * 1000.0
    return f"{100.0 * (medido_mm3 - analitico_mm3) / analitico_mm3:+.2f}%"


def rodar(retomar: bool = True) -> None:
    BRUTO.mkdir(parents=True, exist_ok=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)

    feitas: set[tuple[str, str]] = set()
    if retomar and SAIDA.exists():
        with SAIDA.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                feitas.add((r["variant"], r["structure"]))
        print(f"retomando: {len(feitas)} linhas ja no CSV")

    novo = not SAIDA.exists()
    fh = SAIDA.open("a", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=COLUNAS)
    if novo:
        w.writeheader()

    fantomas = _fantomas()
    total = len(fantomas) * (len(VARIANTES) + len(DERIVADAS))
    feito = 0
    t0 = time.time()
    analiticos = {}

    for nome_f, (mask, affine), analitico, descr in fantomas:
        master_mesh = None
        for nome_v, kw in VARIANTES:
            feito += 1
            if (nome_v, nome_f) in feitas:
                continue
            t = time.time()
            try:
                res = R.reconstruct_surface(mask, affine, **kw)
                mesh = res.mesh if res is not None else None
            except R.SuperficieVazia:
                mesh, res = None, None
            except Exception as e:
                mesh, res = None, None
                print(f"  ERRO {nome_v}/{nome_f}: {type(e).__name__}: {e}")
                (BRUTO / "erros.log").open("a", encoding="utf-8").write(
                    f"{nome_v}/{nome_f}\n{traceback.format_exc()}\n")
            dt = time.time() - t
            L = _linha(nome_v, nome_f, mesh, mask, affine, dt, descr)
            err = _erro_analitico(L, analitico)
            if err:
                L["notes"] = (L["notes"] + f"; erro_vs_formula={err}").strip("; ")
                analiticos[(nome_v, nome_f)] = err
            w.writerow(L); fh.flush()
            if nome_v.startswith("MASTER") and mesh is not None:
                master_mesh = mesh
            print(f"[{feito}/{total}] {nome_v:26} {nome_f:24} "
                  f"tri={L['triangles'] or '-':>7} dice={L['dice'] or '-':>8} "
                  f"wt={L['watertight']} {err}")

        # DERIVADAS: so sobre o MASTER, nunca substituindo.
        for nome_d, frac in DERIVADAS:
            feito += 1
            if (nome_d, nome_f) in feitas or master_mesh is None:
                continue
            t = time.time()
            try:
                alvo = max(4, int(len(master_mesh.faces) * frac))
                der = master_mesh.simplify_quadric_decimation(face_count=alvo)
            except Exception as e:
                der = None
                print(f"  ERRO {nome_d}/{nome_f}: {type(e).__name__}")
            dt = time.time() - t
            L = _linha(nome_d, nome_f, der, mask, affine, dt,
                       f"DERIVADA do MASTER ({int(frac*100)}% das faces) — nao substitui")
            w.writerow(L); fh.flush()
            print(f"[{feito}/{total}] {nome_d:26} {nome_f:24} "
                  f"tri={L['triangles'] or '-':>7} dice={L['dice'] or '-':>8} wt={L['watertight']}")

    fh.close()
    (BRUTO / "erro_analitico.json").write_text(
        json.dumps({f"{k[0]}|{k[1]}": v for k, v in analiticos.items()},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nconcluido em {time.time()-t0:.1f}s · CSV: {SAIDA}")


def _autoteste() -> None:
    """Fantoma com resposta fechada: o MASTER tem que acertar a esfera."""
    mask, affine = P.esfera(20.0, (1.0, 1.0, 1.0))
    res = R.reconstruct_surface(mask, affine, method="marching_cubes", sigma_mm=0.0,
                                taubin_iters=4, level=0.5, offset_mm=0.0)
    assert res is not None and res.mesh is not None, "MASTER nao produziu malha na esfera"
    vol_mm3 = MM.volume_ml(res.mesh) * 1000.0
    esperado = np.pi / 6 * 20.0 ** 3
    err = abs(vol_mm3 - esperado) / esperado
    assert err < 0.10, f"MASTER erra {err:.1%} o volume analitico da esfera d=20"
    # A cavidade do tubo oco NAO pode desaparecer no MASTER.
    m2, a2 = P.tubo_oco(20.0, 12.0, 40.0, (1.0, 1.0, 1.0))
    r2 = R.reconstruct_surface(m2, a2, method="marching_cubes", sigma_mm=0.0,
                               taubin_iters=4, level=0.5, offset_mm=0.0)
    assert r2 is not None and len(r2.mesh.faces) > 100
    # CONTROLE DAS CHAVES DE TOPOLOGIA: um `.get` com nome errado devolve "" em
    # silencio e a coluna sai vazia sem ninguem notar. Foi o que aconteceu.
    L = _linha("teste", "esfera", res.mesh, mask, affine, 0.0, "")
    for c in ("components", "boundary_edges", "watertight"):
        assert L[c] != "", f"coluna {c} saiu vazia — chave de topologia errada?"
    # CONTROLE DO SURFACE NETS: ele ignora o filtro de malha; se um dia passar a
    # respeitar, este assert cai e o benchmark precisa de duas variantes de novo.
    s1 = R.reconstruct_surface(mask, affine, method="surface_nets", sigma_mm=0.0,
                               taubin_iters=4, level=0.5, offset_mm=0.0, mesh_smoothing="taubin")
    s2 = R.reconstruct_surface(mask, affine, method="surface_nets", sigma_mm=0.0,
                               taubin_iters=0, level=0.5, offset_mm=0.0, mesh_smoothing="none")
    assert np.allclose(np.asarray(s1.mesh.vertices), np.asarray(s2.mesh.vertices)), (
        "surface_nets passou a respeitar o filtro de malha — o benchmark precisa "
        "voltar a ter duas variantes")
    print(f"benchmark_fase17: autoteste OK (esfera err={err:.2%}, tubo oco reconstruido, "
          "4 controles)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--do-zero", action="store_true", help="ignora o CSV existente")
    a = ap.parse_args()
    _autoteste()
    if not a.autoteste:
        rodar(retomar=not a.do_zero)
