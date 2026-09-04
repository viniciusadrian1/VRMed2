"""
Teste de FALHA TOPOLÓGICA da suavização de malha (fantoma analítico, Tier3).

Pergunta única: aumentar a suavização QUEBRA a topologia da estrutura? Não é
uma pergunta de milímetro (isso é o benchmark de calibre) — é de contagem:
cavidade que some, dois corpos que viram um, conexão fina que arrebenta,
malha que abre, face que atravessa face.

Variantes (todas marching_cubes + sigma_mm=0.0, para isolar o filtro de MALHA):
  V0_taubin4   — BASELINE CONGELADO (default vigente da MASTER)
  V1_taubin8
  V2_taubin12
  V3_taubin20
  V4_wsinc     — mesh_smoothing="windowed_sinc", ws_iters=20, ws_pass_band=0.1

Tier: TUDO aqui é Tier3 (fantoma com topologia declarada pela geometria) mais
sanidade topológica da malha isolada. NÃO há Tier1 (nenhuma métrica de
fidelidade à máscara é calculada aqui) e NÃO há Tier2 (acurácia de segmentação
contra ground truth independente continua AUSENTE no repositório).

Convenção de valor ausente (herdada de topology_metrics, não negociável):
  "sim"/"nao"      -> mediu e concluiu
  "nao aplicavel"  -> o modo de falha não existe para esta geometria
  "nao medido"     -> a métrica de origem não pôde ser calculada (string propagada)
  "sumiu"          -> reconstruct_surface devolveu None: a estrutura não sobreviveu
                      à variante. Perda total — não é "nao" nem 0.

O que este arquivo NÃO responde:
  - se a variante é melhor: topologia intacta não é qualidade geométrica.
  - qualquer coisa sobre dado real: são 8 fantomas sintéticos.

Uso:
  python scripts/validation/benchmark_topologia.py --out .clinica-dados/benchmark-topologia
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy import ndimage

if __package__ in (None, ""):  # rodado como script: a raiz do repo não está no path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.geometry.reconstruction import reconstruct_surface  # noqa: E402
from scripts.validation import phantom  # noqa: E402
from scripts.validation.phantom import CASOS_TOPOLOGIA, volume_da_mascara_mm3  # noqa: E402
from scripts.validation.topology_metrics import (  # noqa: E402
    CONECTIVIDADE,
    comparar_topologia,
    qualidade_topologica,
)

TIER = "Tier3"

# Todas com marching_cubes e sigma_mm=0.0: o que varia é SÓ o filtro de malha.
VARIANTES: dict[str, dict[str, Any]] = {
    "V0_taubin4": {"mesh_smoothing": "taubin", "taubin_iters": 4},
    "V1_taubin8": {"mesh_smoothing": "taubin", "taubin_iters": 8},
    "V2_taubin12": {"mesh_smoothing": "taubin", "taubin_iters": 12},
    "V3_taubin20": {"mesh_smoothing": "taubin", "taubin_iters": 20},
    "V4_wsinc": {"mesh_smoothing": "windowed_sinc", "ws_iters": 20, "ws_pass_band": 0.1},
}
BASELINE = "V0_taubin4"

MODOS = (
    "fechou_cavidade",
    "fundiu_componentes",
    "criou_ponte",
    "removeu_conexao_fina",
    "gerou_self_intersection",
    "abriu_malha",
)


@dataclass(frozen=True)
class Caso:
    """Um fantoma + a topologia que a GEOMETRIA declara para a MALHA dele.

    `n_comp_malha` e `genus_malha` são DECLARAÇÕES derivadas da forma, não
    medidas. Elas são a referência dos modos de falha; se o próprio baseline
    já as violar, isso é registrado como "baseline ja viola" e não é atribuído
    às variantes.

    Atenção à diferença entre componente da MÁSCARA e da MALHA: a casca
    esférica é 1 componente conexo de voxels mas 2 superfícies fechadas
    (externa + da cavidade). Por isso a referência aqui é a da malha.
    """

    nome: str
    construtor: Callable[..., tuple[np.ndarray, np.ndarray]]
    kwargs: dict[str, Any]
    n_comp_malha: int          # superfícies fechadas esperadas
    genus_malha: int           # soma dos gêneros das componentes
    tem_cavidade: bool         # cavidade interna OU lúmen passante
    conexao_fina: bool         # a estrutura depende de uma junção estreita
    contato: bool              # dois corpos separados por ~1 voxel
    volume_analitico_mm3: float | None
    nota: str


def _casos() -> list[Caso]:
    """Os 8 casos. Os 5 de CASOS_TOPOLOGIA vêm da tabela (kwargs e volume
    analítico não são recopiados, para não sair de sincronia); os 3 restantes
    usam fantomas que já existiam em phantom.py."""
    t = CASOS_TOPOLOGIA
    return [
        Caso(
            "esfera_com_cavidade", phantom.esfera_com_cavidade,
            {"diametro_mm": 20.0, "diametro_cavidade_mm": 10.0, "spacing": (0.5, 0.5, 0.5)},
            n_comp_malha=2, genus_malha=0, tem_cavidade=True, conexao_fina=False, contato=False,
            volume_analitico_mm3=np.pi / 6.0 * (20.0**3 - 10.0**3),
            nota="cavidade interna fechada: aparece como SUPERFICIE extra, nao como genero",
        ),
        Caso(
            "duas_estruturas_adjacentes", phantom.duas_estruturas_adjacentes,
            {"gap_mm": 1.0, "diametro_mm": 10.0, "spacing": (0.5, 0.5, 0.5)},
            n_comp_malha=2, genus_malha=0, tem_cavidade=False, conexao_fina=False, contato=False,
            volume_analitico_mm3=2.0 * np.pi / 6.0 * 10.0**3,
            nota="vao de 1,0 mm = 2 voxels",
        ),
        Caso(
            "dois_cilindros_em_contato", t["dois_cilindros_em_contato"][0],
            dict(t["dois_cilindros_em_contato"][1]),
            n_comp_malha=2, genus_malha=0, tem_cavidade=False, conexao_fina=False, contato=True,
            volume_analitico_mm3=t["dois_cilindros_em_contato"][4],
            nota="vao de exatamente 1 voxel (0,5 mm)",
        ),
        Caso(
            "tubo_fino", phantom.tubo_fino,
            {"diametro_mm": 2.0, "comprimento_mm": 20.0, "spacing": (0.5, 0.5, 0.5)},
            n_comp_malha=1, genus_malha=0, tem_cavidade=False, conexao_fina=False, contato=False,
            volume_analitico_mm3=np.pi / 4.0 * 2.0**2 * 20.0,
            nota="4 voxels de secao: candidato a dissolver",
        ),
        Caso(
            "bifurcacao", t["bifurcacao"][0], dict(t["bifurcacao"][1]),
            n_comp_malha=1, genus_malha=0, tem_cavidade=False, conexao_fina=True, contato=False,
            volume_analitico_mm3=t["bifurcacao"][4],
            nota="a juncao em Y e a conexao que pode ser apagada",
        ),
        Caso(
            "tubo_oco", t["tubo_oco"][0], dict(t["tubo_oco"][1]),
            n_comp_malha=1, genus_malha=1, tem_cavidade=True, conexao_fina=False, contato=False,
            volume_analitico_mm3=t["tubo_oco"][4],
            nota="lumen PASSANTE: e uma alca (genus 1), nao uma cavidade fechada",
        ),
        Caso(
            "estrutura_parcialmente_cortada", t["estrutura_parcialmente_cortada"][0],
            dict(t["estrutura_parcialmente_cortada"][1]),
            n_comp_malha=1, genus_malha=0, tem_cavidade=False, conexao_fina=False, contato=False,
            volume_analitico_mm3=t["estrutura_parcialmente_cortada"][4],
            nota="o pad de 1 voxel de _campo_suavizado FECHA a tampa: watertight esperado",
        ),
        Caso(
            "ponte_fina", t["ponte_fina"][0], dict(t["ponte_fina"][1]),
            n_comp_malha=1, genus_malha=0, tem_cavidade=False, conexao_fina=True, contato=False,
            volume_analitico_mm3=t["ponte_fina"][4],
            nota="ponte de 2 mm: 1 componente virando 2 = conexao removida",
        ),
    ]


def _inteiro(x: object) -> int | None:
    """int de verdade (bool não conta). None se for string de ausência."""
    return int(x) if isinstance(x, int) and not isinstance(x, bool) else None


def _sim_nao(v: bool | str) -> str:
    return v if isinstance(v, str) else ("sim" if v else "nao")


def _modos_de_falha(caso: Caso, q: dict) -> dict[str, str]:
    """Os 6 modos, respondidos contra a topologia DECLARADA do caso.

    Cada modo que não existe para a geometria sai "nao aplicavel" — não "nao".
    Toda string vinda de `qualidade_topologica` é propagada intacta.
    """
    n = _inteiro(q["n_componentes"])
    g = q["genus"]

    # cavidade some de duas formas diferentes conforme o tipo de vazio:
    #   lúmen passante  -> gênero cai (alça a menos)
    #   cavidade fechada-> superfície interna some (componente a menos)
    if not caso.tem_cavidade:
        fechou = "nao aplicavel"
    elif caso.genus_malha > 0:
        gi = _inteiro(g)
        fechou = _sim_nao(gi < caso.genus_malha) if gi is not None else str(g)
    else:
        fechou = _sim_nao(n < caso.n_comp_malha) if n is not None else "nao medido"

    fundiu = (
        "nao aplicavel" if caso.n_comp_malha < 2
        else (_sim_nao(n < caso.n_comp_malha) if n is not None else "nao medido")
    )
    # "criou ponte" é a especialização de fundiu para o caso de contato de 1 voxel.
    ponte = fundiu if caso.contato else "nao aplicavel"
    # "removeu conexão fina" = o corpo único fragmentou. Só faz sentido onde há
    # uma junção estreita sustentando a peça (ponte_fina, bifurcacao).
    removeu = (
        _sim_nao(n > caso.n_comp_malha) if (caso.conexao_fina and n is not None)
        else ("nao medido" if caso.conexao_fina else "nao aplicavel")
    )

    si = q["n_self_intersections"]
    si_i = _inteiro(si)
    auto_int = _sim_nao(si_i > 0) if si_i is not None else str(si)

    nb = _inteiro(q["n_boundary_edges"])
    abriu = _sim_nao((nb is not None and nb > 0) or not q["watertight"])

    return {
        "fechou_cavidade": fechou,
        "fundiu_componentes": fundiu,
        "criou_ponte": ponte,
        "removeu_conexao_fina": removeu,
        "gerou_self_intersection": auto_int,
        "abriu_malha": abriu,
    }


def _linha_sumiu(caso: Caso, variante: str) -> dict[str, Any]:
    """Variante que dissolveu a estrutura: nenhum modo é "nao" — todos "sumiu"."""
    linha: dict[str, Any] = {
        "tier": TIER, "caso": caso.nome, "variante": variante, "malha": "ausente",
    }
    linha.update({m: "sumiu" for m in MODOS})
    return linha


def rodar(casos: list[Caso]) -> list[dict[str, Any]]:
    linhas: list[dict[str, Any]] = []
    for caso in casos:
        mask, affine = caso.construtor(**caso.kwargs)
        n_comp_mask = int(ndimage.label(mask, structure=CONECTIVIDADE)[1])
        v_mask = volume_da_mascara_mm3(mask, affine)
        base_q: dict | None = None

        for variante, extra in VARIANTES.items():
            res = reconstruct_surface(
                mask, affine, method="marching_cubes", sigma_mm=0.0, offset_mm=0.0, **extra
            )
            if res is None:
                linhas.append(_linha_sumiu(caso, variante))
                continue

            q = qualidade_topologica(res.mesh)
            if variante == BASELINE:
                base_q = q

            linha: dict[str, Any] = {
                "tier": TIER,
                "caso": caso.nome,
                "variante": variante,
                "malha": "presente",
                # referências declaradas (geometria), não medidas
                "n_comp_malha_esperado": caso.n_comp_malha,
                "genus_esperado": caso.genus_malha,
                "n_comp_mascara_medido": n_comp_mask,
                "volume_mascara_mm3": round(v_mask, 2),
                "volume_analitico_mm3": (
                    round(caso.volume_analitico_mm3, 2)
                    if caso.volume_analitico_mm3 is not None else "nao aplicavel"
                ),
                # métricas numéricas da malha
                "n_componentes": q["n_componentes"],
                "euler_number": q["euler_number"],
                "genus": q["genus"],
                "n_boundary_edges": q["n_boundary_edges"],
                "n_nao_manifold_estrito": q["n_arestas_nao_manifold_estrito"],
                "n_self_intersections": q["n_self_intersections"],
                "n_faces_degeneradas": q["n_faces_degeneradas"],
                "n_vertices_isolados": q["n_vertices_isolados"],
                "watertight": q["watertight"],
                "area_mm2": q["area_mm2"],
                "volume_ml_se_watertight": q["volume_ml_se_watertight"],
                "n_faces": int(len(res.mesh.faces)),
                "nota": caso.nota,
            }
            linha.update(_modos_de_falha(caso, q))
            # deltas contra o baseline congelado (antes = V0, depois = variante).
            # PREFIXADOS: `comparar_topologia` devolve chaves com os mesmos nomes de
            # quatro modos de falha (fundiu_componentes, abriu_malha, ...) e sem o
            # prefixo elas sobrescreveriam a resposta do caso pelo delta contra V0.
            if base_q is not None:
                linha.update({f"vsV0_{k}": v for k, v in comparar_topologia(base_q, q).items()})
            linhas.append(linha)
    return linhas


def _matriz(linhas: list[dict], modo: str, casos: list[Caso]) -> list[list[str]]:
    idx = {(l["caso"], l["variante"]): l.get(modo, "nao medido") for l in linhas}
    tabela = [["caso", *VARIANTES]]
    for c in casos:
        tabela.append([c.nome, *[str(idx.get((c.nome, v), "nao medido")) for v in VARIANTES]])
    return tabela


def _md_tabela(tabela: list[list[str]]) -> str:
    cab, *corpo = tabela
    linhas = ["| " + " | ".join(cab) + " |", "|" + "|".join(["---"] * len(cab)) + "|"]
    linhas += ["| " + " | ".join(l) + " |" for l in corpo]
    return "\n".join(linhas)


def _resumo_md(linhas: list[dict], casos: list[Caso]) -> str:
    p: list[str] = [
        "# Falha topológica da suavização — fantoma analítico (Tier3)",
        "",
        "Todas as variantes: `marching_cubes`, `sigma_mm=0.0`, `offset_mm=0.0`. "
        "O que varia é só o filtro de MALHA.",
        "",
        "Legenda: `sim` = o modo de falha ocorreu · `nao` = medido e não ocorreu · "
        "`nao aplicavel` = o modo não existe para esta geometria · "
        "`nao medido` = a métrica de origem não pôde ser calculada · "
        "`sumiu` = a estrutura não sobreviveu (reconstrução devolveu None).",
        "",
        "**Isto não é validação clínica nem prova de qualidade geométrica.** "
        "Topologia intacta não significa malha fiel; e Tier1 (fidelidade à máscara) "
        "e Tier2 (acurácia de segmentação) não são medidos aqui.",
        "",
        "## Leia isto antes de usar as matrizes",
        "",
        "Em `_finalizar`, a fusão de vértices (`process=True`) acontece ANTES do filtro, "
        "e nem Taubin nem windowed_sinc alteram o array de faces — só deslocam vértices. "
        "Logo `n_componentes`, `euler_number`, `genus`, `n_boundary_edges` e "
        "`n_arestas_nao_manifold_estrito` são **invariantes por construção** entre estas "
        "cinco variantes: a extração (marching_cubes) já decidiu a topologia. Isso é medido "
        "aqui, não suposto — ver `--autoteste`, que compara os arrays de faces de V0 e V3.",
        "",
        "Consequência: `nao` nas matrizes de **fechou_cavidade, fundiu_componentes, "
        "criou_ponte, removeu_conexao_fina e abriu_malha** é TAUTOLÓGICO para estas cinco "
        "variantes — da mesma família da armadilha de sigma=0 no Tier1. Não é evidência de "
        "que suavizar mais seja seguro. O único modo com poder de discriminação real é "
        "`gerou_self_intersection`, que depende da posição dos vértices; é lá que uma fusão "
        "geométrica (duas paredes se atravessando sem mudar a conectividade) apareceria.",
        "",
        "Estas matrizes DETECTAM falha topológica introduzida antes da malha — outro "
        "extrator, outro sigma, decimação, fill_holes. Para as cinco variantes de "
        "suavização de malha, elas são um controle negativo, não uma aprovação.",
        "",
    ]
    for modo in MODOS:
        p += [f"## {modo}", "", _md_tabela(_matriz(linhas, modo, casos)), ""]

    p += ["## Métricas numéricas por caso × variante", ""]
    cols = [
        "caso", "variante", "n_componentes", "euler_number", "genus", "n_boundary_edges",
        "n_nao_manifold_estrito", "n_self_intersections", "watertight", "area_mm2",
        "volume_ml_se_watertight", "n_faces",
    ]
    tab = [cols] + [[str(l.get(c, "sumiu")) for c in cols] for l in linhas]
    p += [_md_tabela(tab), ""]

    p += ["## Referência declarada de cada caso (geometria, não medida)", ""]
    ref = [["caso", "n_comp_malha_esperado", "genus_esperado", "n_comp_mascara_medido", "nota"]]
    idx = {l["caso"]: l for l in linhas if l.get("malha") == "presente"}
    for c in casos:
        l = idx.get(c.nome, {})
        ref.append([
            c.nome, str(c.n_comp_malha), str(c.genus_malha),
            str(l.get("n_comp_mascara_medido", "nao medido")), c.nota,
        ])
    p += [_md_tabela(ref), ""]
    return "\n".join(p)


def _caso_falso(**over: Any) -> Caso:
    base = dict(
        nome="controle", construtor=phantom.esfera, kwargs={}, n_comp_malha=1, genus_malha=0,
        tem_cavidade=False, conexao_fina=False, contato=False, volume_analitico_mm3=None, nota="",
    )
    return Caso(**{**base, **over})


def _autoteste() -> None:
    """CONTROLE POSITIVO: prova que cada modo de falha sabe dizer "sim".

    Uma matriz inteira de "nao" é ambígua — pode ser "nada quebrou" ou "o detector
    está morto". Aqui cada modo recebe uma malha deliberadamente defeituosa e tem
    de acusar. Isto NÃO mede o pipeline nem valida variante nenhuma.
    """
    import trimesh

    # 1. self-intersection: duas esferas sobrepostas num corpo só.
    a, b = trimesh.creation.icosphere(subdivisions=2), trimesh.creation.icosphere(subdivisions=2)
    b.apply_translation([0.7, 0.0, 0.0])
    m = _modos_de_falha(_caso_falso(), qualidade_topologica(trimesh.util.concatenate([a, b])))
    assert m["gerou_self_intersection"] == "sim", m

    # 2. abriu_malha: esfera com uma face removida.
    aberta = trimesh.creation.icosphere(subdivisions=2)
    aberta.update_faces(np.arange(len(aberta.faces)) != 0)
    m = _modos_de_falha(_caso_falso(), qualidade_topologica(aberta))
    assert m["abriu_malha"] == "sim", m

    # 3. fechou_cavidade por GÊNERO: um toro (genus 1) virando esfera (genus 0).
    m = _modos_de_falha(
        _caso_falso(tem_cavidade=True, genus_malha=1),
        qualidade_topologica(trimesh.creation.icosphere(subdivisions=2)),
    )
    assert m["fechou_cavidade"] == "sim", m

    # 4. fechou_cavidade por COMPONENTE: casca (2 superfícies) virando 1.
    m = _modos_de_falha(
        _caso_falso(tem_cavidade=True, n_comp_malha=2),
        qualidade_topologica(trimesh.creation.icosphere(subdivisions=2)),
    )
    assert m["fechou_cavidade"] == "sim", m

    # 5. fundiu_componentes e criou_ponte: esperava 2 corpos, veio 1.
    q1 = qualidade_topologica(trimesh.creation.icosphere(subdivisions=2))
    assert _modos_de_falha(_caso_falso(n_comp_malha=2), q1)["fundiu_componentes"] == "sim"
    assert _modos_de_falha(_caso_falso(n_comp_malha=2, contato=True), q1)["criou_ponte"] == "sim"

    # 6. removeu_conexao_fina: esperava 1 corpo, veio 2 soltos.
    c, d = trimesh.creation.icosphere(subdivisions=2), trimesh.creation.icosphere(subdivisions=2)
    d.apply_translation([5.0, 0.0, 0.0])
    q2 = qualidade_topologica(trimesh.util.concatenate([c, d]))
    assert _modos_de_falha(_caso_falso(conexao_fina=True), q2)["removeu_conexao_fina"] == "sim"

    # 7. a invariância declarada no summary, MEDIDA: Taubin e windowed_sinc só
    # deslocam vértices; o array de faces de V0, V3 e V4 tem de ser idêntico.
    mask, affine = phantom.tubo_oco(**CASOS_TOPOLOGIA["tubo_oco"][1])
    faces = {
        v: reconstruct_surface(mask, affine, method="marching_cubes", sigma_mm=0.0, **extra).mesh.faces
        for v, extra in VARIANTES.items()
    }
    for v in ("V3_taubin20", "V4_wsinc"):
        assert np.array_equal(faces[BASELINE], faces[v]), f"{v}: faces mudaram (invariancia falsa)"
    # e os vértices TÊM de mudar, senão a variante não fez nada:
    v0 = reconstruct_surface(mask, affine, method="marching_cubes", sigma_mm=0.0, **VARIANTES[BASELINE])
    v3 = reconstruct_surface(mask, affine, method="marching_cubes", sigma_mm=0.0, **VARIANTES["V3_taubin20"])
    assert not np.allclose(v0.mesh.vertices, v3.mesh.vertices), "V3 nao mexeu em vertice nenhum"

    print("autoteste OK: os 6 modos acusam falha quando ela existe;")
    print("              faces identicas entre V0/V3/V4 (topologia invariante, medido);")
    print("              vertices diferentes entre V0 e V3 (a variante de fato roda).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".clinica-dados/benchmark-topologia", type=Path)
    ap.add_argument("--autoteste", action="store_true", help="controle positivo dos 6 modos de falha")
    args = ap.parse_args()

    if args.autoteste:
        _autoteste()
        return

    casos = _casos()
    linhas = rodar(casos)

    args.out.mkdir(parents=True, exist_ok=True)
    campos: list[str] = []
    for l in linhas:  # união preservando ordem de aparição
        campos += [k for k in l if k not in campos]
    with (args.out / "resultados.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, restval="")
        w.writeheader()
        w.writerows(linhas)
    (args.out / "resultados.json").write_text(
        json.dumps({"variantes": VARIANTES, "linhas": linhas}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    md = _resumo_md(linhas, casos)
    (args.out / "summary_topologia.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
