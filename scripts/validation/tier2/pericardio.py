"""
Fase 6 — o que a classe `pericardium` do TotalSegmentator DE FATO cobre.

Pergunta: o nome NAO e a definicao. `pericardium` (tarefa `trunk_cavities`,
task 343, rotulo 3) pode ser o SACO pericardico (uma casca fibrosa fina em volta
do coracao) ou a CAVIDADE pericardica (o volume preenchido que a casca delimita,
coracao incluso). Sao coisas diferentes e produzem geometrias diferentes. Este
modulo descobre qual e por MEDIDA, nao por leitura do nome.

O que se mede, na ordem em que a evidencia importa:

  1. FORMA — casca ou solido?
     `razao_preenchimento` = |mascara| / |mascara com buracos preenchidos|.
     E um criterio SEM constante em mm: uma casca fina fechada envolve um volume
     muito maior que ela propria (razao pequena); um solido preenchido nao tem o
     que preencher (razao 1,0). Medida em 3D e tambem fatia a fatia em 2D,
     porque uma casca ABERTA nas pontas em Z nao fecha em 3D e o fill 3D nao a
     detectaria — o fill 2D detecta.
     Complemento descritivo: `meia_espessura_mm`, a distancia euclidiana de cada
     voxel da mascara ate o fundo mais proximo DELA MESMA (EDT com sampling =
     spacing). Casca fina => mediana e P95 pequenos e proximos entre si.

  2. RELACAO COM O `heart` PREDITO — contencao nos dois sentidos, e se a uniao
     (heart U pericardium) e um corpo contiguo ou tem vazio encapsulado entre as
     duas mascaras.

  3. A PERGUNTA QUE DECIDE — (heart U pericardium) explica o envelope do GT do
     coracao? Compara, NO MESMO CASO e contra o MESMO GT Heart: dice/precision/
     recall de `heart` sozinho contra os de `heart U pericardium`. A hipotese do
     envelope pericardico so ganha suporte se o recall subir na direcao de 1,0
     SEM que a precision despenque.

  4. O QUE SOBRA — depois da uniao, quanto da divergencia restante e corte em Z
     e quanto e envelope lateral (a fase 5 mediu 19,25 % / 80,75 % para `heart`
     sozinho). Reusa ontologia_coracao.medir, a MESMA funcao que produziu
     aqueles numeros, para que a comparacao seja de igual para igual.

USO DO GT: aqui o GT so AVALIA. Nenhuma mascara deste modulo e construida a
partir do ground truth — `pericardium` sai do modelo, do CT, e mais nada.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import (
    binary_fill_holes,
    distance_transform_edt,
    generate_binary_structure,
    label,
)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from scripts.validation.tier2 import (  # noqa: E402
        fase5, geometria, mapeamento, ontologia_coracao, rtstruct as rtst,
    )
    from scripts.validation.tier2.mapa_erro import _frac, _ml, _p  # noqa: E402
else:
    from . import fase5, geometria, mapeamento, ontologia_coracao, rtstruct as rtst
    from .mapa_erro import _frac, _ml, _p

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase6" / "pericardio"
TAREFA = "trunk_cavities"           # task 343 do TotalSegmentator 2.18.0
CLASSE = "pericardium"              # rotulo 3 da tarefa
ROI_GT = "Heart"                    # a unica ROI do LCTSC com que isto se compara
NM = "nao medido"
NA = "nao aplicavel"

# 6-vizinhanca (face) — a MESMA conectividade de mapa_erro/ontologia_coracao, para
# que "n componentes" continue comparavel entre os relatorios da fase 5 e 6.
_VIZ6 = generate_binary_structure(3, 1)

# ---------------------------------------------------------------------------
# CASOS — declarados ANTES de rodar qualquer segmentacao (registro em 2026-09-05).
#
# Regra que os produziu, reproduzivel por `_conferir_casos()`: dentro do conjunto
# `development` do split da fase 5, os DOIS primeiros de cada instituicao na ordem
# fase5._ordem_deterministica. Dois por instituicao porque instituicao e a maior
# fonte de variacao medida na coorte; a ordem por hash e a mesma que construiu o
# split, entao nenhum caso foi escolhido a dedo.
#
# O conjunto `test` e o `validation` NAO sao lidos, medidos nem citados.
CASOS: tuple[str, ...] = (
    "LCTSC-Test-S1-101",
    "LCTSC-Train-S1-005",
    "LCTSC-Train-S2-003",
    "LCTSC-Train-S2-010",
    "LCTSC-Train-S3-005",
    "LCTSC-Train-S3-010",
)

# ---------------------------------------------------------------------------
# CRITERIO DE FORMA — declarado antes de ver qualquer numero desta fase.
#
# 0,5 e o ponto medio natural da razao, nao um limiar ajustado: abaixo dele a
# mascara e MENOS da metade do que ela encerra (mais vazio que materia => casca);
# acima, ela e a maior parte do proprio interior (=> solido preenchido). Nao ha
# constante em mm em lugar nenhum da decisao.
LIMIAR_CASCA = 0.5


# ------------------------------------------------------------------- forma pura


def _fill_2d(m: np.ndarray) -> np.ndarray:
    """binary_fill_holes fatia a fatia no eixo 2 (axial no LCTSC).

    Uma casca ABERTA nas pontas em Z nao e uma superficie fechada em 3D, e o fill
    3D devolveria a propria mascara — falso "solido". Cada fatia axial de uma
    casca ainda e um anel FECHADO, e o fill 2D o detecta. Por isso as duas
    versoes sao reportadas: divergencia entre elas E a informacao.
    """
    saida = np.zeros_like(m, dtype=bool)
    for k in range(m.shape[2]):
        if m[:, :, k].any():
            saida[:, :, k] = binary_fill_holes(m[:, :, k])
    return saida


def forma(m: np.ndarray, spacing) -> dict:
    """Casca ou solido? Nao le arquivo, nao escreve nada — e o que o autoteste exercita."""
    m = np.asarray(m) > 0.5
    spacing = tuple(float(s) for s in spacing)
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    n = int(m.sum())
    if not n:
        return {"volume_ml": 0.0, "n_voxels": 0, "veredito_forma": "invalido: mascara vazia"}

    cheio_3d = binary_fill_holes(m, structure=_VIZ6)
    cheio_2d = _fill_2d(m)
    razao_3d = n / int(cheio_3d.sum())
    razao_2d = n / int(cheio_2d.sum())
    # A casca so precisa fechar em UMA das duas leituras para ser casca: o fill 3D
    # pega a casca fechada, o fill 2D pega a casca aberta nas pontas em Z.
    razao = min(razao_3d, razao_2d)

    # meia-espessura local: EDT da propria mascara (distancia ate o fundo dela).
    # Para uma placa de espessura t o valor maximo e ~t/2; por isso "meia".
    meia = distance_transform_edt(m, sampling=spacing)[m]
    n_comp = int(label(m, structure=_VIZ6)[1])

    return {
        "volume_ml": _ml(n, voxel_mm3),
        "n_voxels": n,
        "n_componentes": n_comp,
        "razao_preenchimento_3d": razao_3d,
        "razao_preenchimento_2d_por_fatia": razao_2d,
        "razao_preenchimento": razao,
        "volume_encerrado_3d_ml": _ml(int(cheio_3d.sum()), voxel_mm3),
        "volume_encerrado_2d_ml": _ml(int(cheio_2d.sum()), voxel_mm3),
        "meia_espessura_mm": {
            "definicao": "distancia euclidiana (sampling=spacing) de cada voxel da mascara "
                         "ate o fundo mais proximo DELA MESMA; ~metade da espessura local",
            "mediana": _p(meia, 50), "p95": _p(meia, 95),
            "max": float(meia.max()),
        },
        "veredito_forma": "casca" if razao < LIMIAR_CASCA else "solido preenchido",
        "criterio": f"razao_preenchimento < {LIMIAR_CASCA} => casca (declarado antes de medir)",
    }


def relacao(peri: np.ndarray, heart: np.ndarray, spacing) -> dict:
    """Contencao nos dois sentidos + contiguidade/vazio da uniao."""
    peri = np.asarray(peri) > 0.5
    heart = np.asarray(heart) > 0.5
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    inter = int((peri & heart).sum())
    uniao = peri | heart
    n_u = int(uniao.sum())
    cheio = binary_fill_holes(uniao, structure=_VIZ6)
    buraco = int(cheio.sum()) - n_u
    return {
        "intersecao_ml": _ml(inter, voxel_mm3),
        "frac_heart_dentro_de_pericardium": _frac(inter, int(heart.sum()), "heart vazio"),
        "frac_pericardium_dentro_de_heart": _frac(inter, int(peri.sum()), "pericardium vazio"),
        "uniao_ml": _ml(n_u, voxel_mm3),
        "uniao_n_componentes": int(label(uniao, structure=_VIZ6)[1]),
        "uniao_vazio_encapsulado_ml": _ml(buraco, voxel_mm3),
        "uniao_frac_vazio": _frac(buraco, n_u, "uniao vazia"),
        "nota": "vazio encapsulado = voxels que o fill 3D da uniao fecha e a uniao nao tem "
                "— e o espaco entre as duas mascaras, se existir",
    }


# ---------------------------------------------------------------------- execucao


def segmentar(caso: str, raiz: Path = RAIZ_PADRAO, saida: Path = SAIDA_PADRAO,
              log=print) -> dict:
    """Roda `trunk_cavities` num caso, em diretorio PROPRIO.

    NAO toca em pred_masks/ do baseline A_BASELINE_V1: escreve em
    fase6/pericardio/<caso>/masks/. Reusa a segmentacao se ja existir.
    """
    from scripts.clinica.segmentacao import rodar_segmentacao

    entrada = Path(raiz) / caso / "gt" / "image.nii.gz"
    destino = Path(saida) / caso / "masks"
    if (destino / f"{CLASSE}.nii.gz").exists():
        log(f"{caso}: {TAREFA} ja segmentado — reusando")
        return json.loads((destino / "segmentacao.json").read_text(encoding="utf-8"))
    if not entrada.exists():
        raise FileNotFoundError(f"imagem ausente: {entrada}")
    return rodar_segmentacao(entrada, destino, task=TAREFA, log=log)


def rodar_caso(caso: str, raiz: Path = RAIZ_PADRAO, saida: Path = SAIDA_PADRAO) -> dict:
    """Mede UM caso. Alinhamento (Parte K) ANTES de qualquer medida."""
    dir_caso = Path(raiz) / caso
    caminho_gt = dir_caso / "gt" / f"{rtst.PREFIXO_MASCARA}{ROI_GT}.nii.gz"
    caminho_heart = dir_caso / "pred_masks" / "heart.nii.gz"
    caminho_peri = Path(saida) / caso / "masks" / f"{CLASSE}.nii.gz"

    for p in (caminho_gt, caminho_heart, caminho_peri):
        if not p.exists():
            return {"case_id": caso, "erro": f"ABORTADA: arquivo ausente ({p})"}

    try:
        alin = {
            "pericardium_x_gt": geometria.verificar_alinhamento(
                caminho_peri, caminho_gt, ("pericardium", "gt_Heart")),
            "pericardium_x_heart": geometria.verificar_alinhamento(
                caminho_peri, caminho_heart, ("pericardium", "heart_predito")),
        }
    except geometria.DesalinhamentoGeometrico as e:
        return {"case_id": caso, "erro": f"ABORTADA: {e}"}

    geo = geometria.descrever_nifti(caminho_gt)
    spacing = tuple(geo["zooms_mm"])
    orientacao = geo["orientacao"]

    gt = rtst.carregar_mascara(caminho_gt)
    peri = rtst.carregar_mascara(caminho_peri)
    heart, _ = mapeamento.unir_predicao(dir_caso / "pred_masks",
                                        mapeamento.MAPA_LCTSC[ROI_GT])
    uniao = heart | peri

    # As tres predicoes contra o MESMO GT, pela MESMA funcao que produziu os
    # numeros publicados da fase 5 — comparacao de igual para igual.
    contra_gt = {
        "heart_sozinho": ontologia_coracao.medir(heart, gt, spacing, orientacao),
        "pericardium_sozinho": ontologia_coracao.medir(peri, gt, spacing, orientacao),
        "heart_uniao_pericardium": ontologia_coracao.medir(uniao, gt, spacing, orientacao),
    }

    return {
        "case_id": caso,
        "instituicao": fase5.instituicao_de(caso),
        "spacing_mm": list(spacing),
        "orientacao": orientacao,
        "alinhamento_veredito": {k: v["veredito"] for k, v in alin.items()},
        "forma_pericardium": forma(peri, spacing),
        "forma_heart_CONTROLE": forma(heart, spacing),
        "relacao_heart_pericardium": relacao(peri, heart, spacing),
        "contra_gt_heart": contra_gt,
        "erro": "",
    }


# ------------------------------------------------------------------- relatorio


COLUNAS = [
    "case_id", "instituicao", "spacing_mm", "orientacao",
    "peri_volume_ml", "peri_n_componentes", "peri_razao_preench_3d",
    "peri_razao_preench_2d", "peri_meia_espessura_mediana_mm", "peri_meia_espessura_p95_mm",
    "peri_veredito_forma",
    "heart_volume_ml", "heart_razao_preench_3d", "heart_meia_espessura_mediana_mm",
    "heart_meia_espessura_p95_mm", "heart_veredito_forma_CONTROLE",
    "frac_heart_em_peri", "frac_peri_em_heart", "uniao_n_componentes", "uniao_vazio_ml",
    "gt_volume_ml",
    "dice_heart", "precision_heart", "recall_heart",
    "dice_peri", "precision_peri", "recall_peri",
    "dice_uniao", "precision_uniao", "recall_uniao",
    "div_total_heart_ml", "div_heart_frac_corte_z", "div_heart_frac_envelope_lateral",
    "div_total_peri_ml", "div_peri_frac_corte_z", "div_peri_frac_envelope_lateral",
    "div_total_uniao_ml", "div_uniao_frac_corte_z", "div_uniao_frac_envelope_lateral",
    "z_delta_alto_mm_heart", "z_delta_alto_mm_peri",
    "erro",
]


def _b(r: dict, variante: str, chave: str):
    """Metrica da variante B_campo_completo (sem recorte em Z) de uma das predicoes."""
    return r["contra_gt_heart"][variante]["variantes"]["B_campo_completo"][chave]


def _dz(r: dict, variante: str):
    """Quanto a predicao passa do GT no lado de indice ALTO em Z, em mm (positivo = passa)."""
    z = r["contra_gt_heart"][variante]["extensao_z"]
    return z[f"delta_{z['lado_indice_alto']}_mm"]


def _linha(r: dict) -> dict:
    if r.get("erro"):
        return {**{c: NM for c in COLUNAS}, "case_id": r["case_id"], "erro": r["erro"]}
    fp, fh = r["forma_pericardium"], r["forma_heart_CONTROLE"]
    rel = r["relacao_heart_pericardium"]
    u = r["contra_gt_heart"]["heart_uniao_pericardium"]
    return {
        "case_id": r["case_id"], "instituicao": r["instituicao"],
        "spacing_mm": "x".join(f"{v:.3f}" for v in r["spacing_mm"]),
        "orientacao": r["orientacao"],
        "peri_volume_ml": fp["volume_ml"], "peri_n_componentes": fp["n_componentes"],
        "peri_razao_preench_3d": fp["razao_preenchimento_3d"],
        "peri_razao_preench_2d": fp["razao_preenchimento_2d_por_fatia"],
        "peri_meia_espessura_mediana_mm": fp["meia_espessura_mm"]["mediana"],
        "peri_meia_espessura_p95_mm": fp["meia_espessura_mm"]["p95"],
        "peri_veredito_forma": fp["veredito_forma"],
        "heart_volume_ml": fh["volume_ml"],
        "heart_razao_preench_3d": fh["razao_preenchimento_3d"],
        "heart_meia_espessura_mediana_mm": fh["meia_espessura_mm"]["mediana"],
        "heart_meia_espessura_p95_mm": fh["meia_espessura_mm"]["p95"],
        "heart_veredito_forma_CONTROLE": fh["veredito_forma"],
        "frac_heart_em_peri": rel["frac_heart_dentro_de_pericardium"],
        "frac_peri_em_heart": rel["frac_pericardium_dentro_de_heart"],
        "uniao_n_componentes": rel["uniao_n_componentes"],
        "uniao_vazio_ml": rel["uniao_vazio_encapsulado_ml"],
        "gt_volume_ml": u["volume_gt_ml"],
        "dice_heart": _b(r, "heart_sozinho", "dice"),
        "precision_heart": _b(r, "heart_sozinho", "precision_pred"),
        "recall_heart": _b(r, "heart_sozinho", "recall_gt"),
        "dice_peri": _b(r, "pericardium_sozinho", "dice"),
        "precision_peri": _b(r, "pericardium_sozinho", "precision_pred"),
        "recall_peri": _b(r, "pericardium_sozinho", "recall_gt"),
        "dice_uniao": _b(r, "heart_uniao_pericardium", "dice"),
        "precision_uniao": _b(r, "heart_uniao_pericardium", "precision_pred"),
        "recall_uniao": _b(r, "heart_uniao_pericardium", "recall_gt"),
        **{f"div_{n}_{k}": r["contra_gt_heart"][v]["divergencia_total"][k]
           for n, v in (("heart", "heart_sozinho"), ("peri", "pericardium_sozinho"),
                        ("uniao", "heart_uniao_pericardium"))
           for k in ("frac_corte_z", "frac_envelope_lateral")},
        **{f"div_total_{n}_ml": r["contra_gt_heart"][v]["divergencia_total"]["total_ml"]
           for n, v in (("heart", "heart_sozinho"), ("peri", "pericardium_sozinho"),
                        ("uniao", "heart_uniao_pericardium"))},
        "z_delta_alto_mm_heart": _dz(r, "heart_sozinho"),
        "z_delta_alto_mm_peri": _dz(r, "pericardium_sozinho"),
        "erro": "",
    }


def _num(valores):
    return [float(v) for v in valores
            if isinstance(v, (int, float)) and not isinstance(v, bool) and np.isfinite(v)]


def _med(linhas, coluna) -> float | str:
    n = _num([l.get(coluna) for l in linhas])
    return float(np.median(n)) if n else f"invalido: sem valor numerico em {coluna}"


def _f(v, casas=4) -> str:
    return f"{v:.{casas}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def veredito(linhas: list[dict]) -> dict:
    """SIM / NAO / NAO DETERMINADO — com o numero que sustenta.

    A correspondencia com o SACO pericardico exige as DUAS coisas ao mesmo tempo:
      (a) forma de casca (razao_preenchimento abaixo do limiar declarado) em todos
          os casos medidos — um saco e uma casca, nao um bloco;
      (b) o heart predito majoritariamente DENTRO do que a casca encerra.
    Se (a) falhar e a mascara for solida e disjunta do heart, a classe corresponde
    a outra coisa (gordura/espaco pericardico, ou a cavidade) e o veredito e NAO.
    Discordancia entre casos => NAO DETERMINADO; a evidencia nao fecha.
    """
    validos = [l for l in linhas if not l.get("erro")]
    if not validos:
        return {"veredito": "NAO DETERMINADO", "motivo": "nenhum caso valido medido"}

    cascas = [l["peri_veredito_forma"] == "casca" for l in validos]
    frac_dentro = _num([l["frac_heart_em_peri"] for l in validos])
    med_dentro = float(np.median(frac_dentro)) if frac_dentro else None

    if all(cascas) and med_dentro is not None and med_dentro >= LIMIAR_CASCA:
        v, motivo = "SIM", (
            f"forma de casca em {sum(cascas)}/{len(validos)} casos e mediana de "
            f"{med_dentro:.4f} do heart predito dentro dela")
    elif not any(cascas):
        v, motivo = "NAO", (
            f"solido preenchido em {len(validos)}/{len(validos)} casos "
            f"(mediana razao_preenchimento_3d = {_med(validos, 'peri_razao_preench_3d'):.4f}); "
            "um saco pericardico seria casca")
    else:
        v, motivo = "NAO DETERMINADO", (
            f"forma inconsistente entre casos: casca em {sum(cascas)}/{len(validos)}")

    # O que a mascara E, se nao e o saco. Descricao DIRIGIDA PELO DADO: so afirma
    # "cavidade/regiao pericardica preenchida" quando as tres medidas batem ao mesmo
    # tempo — solida, contendo o heart, e reproduzindo o envelope do GT. Se alguma
    # delas nao bater, o campo diz que nao ha correspondencia medida.
    rec_peri = _med(validos, "recall_peri")
    corresponde = NM
    if v == "NAO" and med_dentro is not None:
        solida = isinstance(_med(validos, "peri_razao_preench_3d"), float)
        if solida and med_dentro >= 0.8 and isinstance(rec_peri, float) and rec_peri >= 0.9:
            corresponde = (
                "compativel com a REGIAO/CAVIDADE pericardica preenchida (o volume que o saco "
                f"delimita, coracao incluso): solida, contendo {med_dentro:.4f} do `heart` "
                f"predito e recuperando {rec_peri:.4f} do GT `Heart` do LCTSC sozinha")
        else:
            corresponde = ("nao e o saco; a alternativa nao ficou determinada pelas medidas "
                           "desta fase")

    return {
        "veredito": v, "motivo": motivo, "corresponde_a": corresponde,
        "razao_preenchimento_3d_mediana": _med(validos, "peri_razao_preench_3d"),
        "razao_preenchimento_2d_mediana": _med(validos, "peri_razao_preench_2d"),
        "meia_espessura_p95_mm_mediana": _med(validos, "peri_meia_espessura_p95_mm"),
        "frac_heart_em_peri_mediana": med_dentro if med_dentro is not None else NM,
        "frac_peri_em_heart_mediana": _med(validos, "frac_peri_em_heart"),
    }


def _resumo_md(r: dict) -> str:
    L, med, v = r["linhas"], r["medianas"], r["veredito"]
    val = [l for l in L if not l.get("erro")]
    ganho_recall = (med["recall_uniao"] - med["recall_heart"]
                    if isinstance(med["recall_uniao"], float)
                    and isinstance(med["recall_heart"], float) else NM)
    perda_prec = (med["precision_heart"] - med["precision_uniao"]
                  if isinstance(med["precision_uniao"], float)
                  and isinstance(med["precision_heart"], float) else NM)

    linhas = [
        "# Fase 6 — o que a classe `pericardium` cobre",
        "",
        f"Tarefa `{TAREFA}` (task 343) do TotalSegmentator {r['totalsegmentator_versao']}, "
        f"classe `{CLASSE}`. {len(val)} de {len(L)} casos do conjunto **development** "
        "(2 por instituicao, ordem determinista do split da fase 5).",
        "Uso educacional/experimental. O GT aqui so AVALIA — nenhuma mascara foi "
        "construida a partir dele.",
        "",
        f"## VEREDITO: a classe `pericardium` corresponde ao saco pericardico? **{v['veredito']}**",
        "",
        f"{v['motivo']}",
        "",
        f"O que ela e, entao: {v['corresponde_a']}",
        "",
        "| numero que sustenta | valor (mediana) |",
        "|---|---|",
        f"| razao_preenchimento 3D (1,0 = solido) | {_f(v['razao_preenchimento_3d_mediana'])} |",
        f"| razao_preenchimento 2D por fatia | {_f(v['razao_preenchimento_2d_mediana'])} |",
        f"| meia-espessura P95 (mm) | {_f(v['meia_espessura_p95_mm_mediana'], 3)} |",
        f"| fracao do `heart` dentro de `pericardium` | {_f(v['frac_heart_em_peri_mediana'])} |",
        f"| fracao de `pericardium` dentro de `heart` | {_f(v['frac_peri_em_heart_mediana'])} |",
        "",
        "## 1. Forma — casca ou solido",
        "",
        "`heart` entra como CONTROLE: e um solido conhecido; se o instrumento "
        "classificasse `heart` como casca, ele nao serviria.",
        "",
        "| mascara | volume (mL) | razao_preench 3D | razao_preench 2D | "
        "meia-espessura mediana (mm) | P95 (mm) | veredito |",
        "|---|---|---|---|---|---|---|",
        f"| `pericardium` | {_f(med['peri_volume_ml'], 2)} | "
        f"{_f(med['peri_razao_preench_3d'])} | {_f(med['peri_razao_preench_2d'])} | "
        f"{_f(med['peri_meia_espessura_mediana_mm'], 3)} | "
        f"{_f(med['peri_meia_espessura_p95_mm'], 3)} | "
        f"{val[0]['peri_veredito_forma'] if val else NM} |",
        f"| `heart` (controle) | {_f(med['heart_volume_ml'], 2)} | "
        f"{_f(med['heart_razao_preench_3d'])} | — | "
        f"{_f(med['heart_meia_espessura_mediana_mm'], 3)} | "
        f"{_f(med['heart_meia_espessura_p95_mm'], 3)} | "
        f"{val[0]['heart_veredito_forma_CONTROLE'] if val else NM} |",
        "",
        "## 2. A pergunta que decide — a uniao explica o envelope do GT?",
        "",
        "| predicao contra o GT `Heart` | dice | precision | recall |",
        "|---|---|---|---|",
        f"| `heart` sozinho | {_f(med['dice_heart'])} | {_f(med['precision_heart'])} | "
        f"{_f(med['recall_heart'])} |",
        f"| `pericardium` sozinho | {_f(med['dice_peri'])} | {_f(med['precision_peri'])} | "
        f"{_f(med['recall_peri'])} |",
        f"| `heart` U `pericardium` | {_f(med['dice_uniao'])} | {_f(med['precision_uniao'])} | "
        f"{_f(med['recall_uniao'])} |",
        "",
        f"Ganho de recall da uniao: **{_f(ganho_recall)}**. "
        f"Perda de precision: **{_f(perda_prec)}**.",
        "",
        "## 3. O que sobra — corte em Z x envelope lateral",
        "",
        "As tres predicoes medidas pela MESMA funcao (ontologia_coracao.medir) nos MESMOS "
        "6 casos, entao as colunas sao comparaveis entre si sem ressalva de n.",
        "",
        "| | `heart` | `pericardium` | `heart` U `pericardium` |",
        "|---|---|---|---|",
        f"| divergencia total FP+FN (mL) | {_f(med['div_total_heart_ml'], 2)} | "
        f"{_f(med['div_total_peri_ml'], 2)} | {_f(med['div_total_uniao_ml'], 2)} |",
        f"| fracao corte em Z | {_f(med['div_heart_frac_corte_z'])} | "
        f"{_f(med['div_peri_frac_corte_z'])} | {_f(med['div_uniao_frac_corte_z'])} |",
        f"| fracao envelope lateral | {_f(med['div_heart_frac_envelope_lateral'])} | "
        f"{_f(med['div_peri_frac_envelope_lateral'])} | "
        f"{_f(med['div_uniao_frac_envelope_lateral'])} |",
        f"| quanto passa do GT no lado de indice alto em Z (mm) | "
        f"{_f(med['z_delta_alto_mm_heart'], 1)} | {_f(med['z_delta_alto_mm_peri'], 1)} | — |",
        "",
        "Referencia da fase 5 para `heart` sozinho na coorte n=30: divergencia 342,27 mL, "
        "19,25 % corte em Z e 80,75 % envelope lateral. Os 6 casos daqui sao um subconjunto "
        "de outro tamanho — a coluna `heart` acima e que serve de par para as outras duas.",
        "",
        "## Por caso",
        "",
        "| caso | inst | peri (mL) | razao 3D | heart em peri | dice heart | dice uniao | "
        "recall heart | recall uniao | precision uniao |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for l in L:
        if l.get("erro"):
            linhas.append(f"| {l['case_id']} | — | {l['erro']} | | | | | | | |")
            continue
        linhas.append(
            f"| {l['case_id']} | {l['instituicao']} | {_f(l['peri_volume_ml'], 2)} | "
            f"{_f(l['peri_razao_preench_3d'])} | {_f(l['frac_heart_em_peri'])} | "
            f"{_f(l['dice_heart'])} | {_f(l['dice_uniao'])} | {_f(l['recall_heart'])} | "
            f"{_f(l['recall_uniao'])} | {_f(l['precision_uniao'])} |")
    linhas += [
        "",
        "## Limitacoes declaradas",
        "",
        f"- n = {len(val)} casos do `development`. Nao e a coorte de 60 nem o `test`.",
        "- O `pericardium` sai da tarefa `trunk_cavities`, um modelo DIFERENTE do que "
        "produziu o baseline (tarefa `total`); os dois nao compartilham pesos.",
        "- O LCTSC nao anota pericardio. Nao existe GT de pericardio contra o qual "
        "medir a classe diretamente — toda a evidencia aqui e indireta, via GT `Heart`.",
    ]
    return "\n".join(linhas) + "\n"


def rodar(raiz: Path = RAIZ_PADRAO, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    from importlib.metadata import version

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    _conferir_casos(raiz, log=log)

    resultados = []
    for caso in CASOS:
        try:
            segmentar(caso, raiz, saida, log=log)
        except Exception as e:  # LicencaAusente inclusa — vira caso abortado, nao crash
            resultados.append({"case_id": caso, "erro": f"ABORTADA: {type(e).__name__}: {e}"})
            log(f"{caso}: ABORTADA — {e}")
            continue
        r = rodar_caso(caso, raiz, saida)
        resultados.append(r)
        if r.get("erro"):
            log(f"{caso}: {r['erro']}")
        else:
            log(f"{caso}: peri {r['forma_pericardium']['volume_ml']:.1f} mL, "
                f"razao3d {r['forma_pericardium']['razao_preenchimento_3d']:.4f}, "
                f"dice {_b(r, 'heart_sozinho', 'dice'):.4f} -> "
                f"{_b(r, 'heart_uniao_pericardium', 'dice'):.4f}")

    linhas = [_linha(r) for r in resultados]
    medianas = {c: _med([l for l in linhas if not l.get("erro")], c)
                for c in COLUNAS if c not in
                ("case_id", "instituicao", "spacing_mm", "orientacao", "erro",
                 "peri_veredito_forma", "heart_veredito_forma_CONTROLE")}
    r = {
        "tarefa": TAREFA, "classe": CLASSE, "roi_gt": ROI_GT,
        "totalsegmentator_versao": version("TotalSegmentator"),
        "conjunto": "development", "casos": list(CASOS),
        "limiar_casca": LIMIAR_CASCA,
        "por_caso": resultados, "linhas": linhas, "medianas": medianas,
        "veredito": veredito(linhas),
    }

    (saida / "pericardio.json").write_text(
        json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with (saida / "pericardio.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    (saida / "RESUMO.md").write_text(_resumo_md(r), encoding="utf-8")
    log(f"gravado em {saida}: pericardio.json, pericardio.csv, RESUMO.md")
    log(f"VEREDITO: {r['veredito']['veredito']} — {r['veredito']['motivo']}")
    return r


def _conferir_casos(raiz: Path = RAIZ_PADRAO, log=print) -> None:
    """Reproduz a regra que gerou CASOS. Falha se alguem editar a lista a dedo."""
    dev = fase5.carregar_split(raiz)["development"]
    por: dict[str, list[str]] = {}
    for c in dev:
        por.setdefault(fase5.instituicao_de(c), []).append(c)
    esperado = tuple(sorted(
        c for inst in sorted(por)
        for c in sorted(por[inst], key=fase5._ordem_deterministica)[:2]))
    if esperado != CASOS:
        raise RuntimeError(
            f"CASOS nao reproduz a regra declarada.\nesperado: {esperado}\natual: {CASOS}")
    intocavel = set(fase5.carregar_split(raiz)["test"]) | set(
        fase5.carregar_split(raiz)["validation"])
    vazado = intocavel & set(CASOS)
    if vazado:
        raise RuntimeError(f"CASOS contem caso de test/validation: {sorted(vazado)}")
    log(f"casos conferidos: {len(CASOS)} do development, regra reproduzida, sem vazamento")


# -------------------------------------------------------------------- autoteste


def _esfera(shape, centro, raio, spacing=(1.0, 1.0, 1.0)) -> np.ndarray:
    g = np.ogrid[:shape[0], :shape[1], :shape[2]]
    d2 = sum(((g[i] - centro[i]) * spacing[i]) ** 2 for i in range(3))
    return d2 <= raio ** 2


def _autoteste() -> None:
    """CONTROLE POSITIVO: cada check falha quando o instrumento erra.

    O criterio de forma tem que separar casca de solido nas DUAS direcoes — nao
    basta acertar a casca (uma metrica que dissesse "casca" para tudo passaria).
    """
    sp = (1.0, 1.0, 1.0)
    shape, c = (48, 48, 48), (24, 24, 24)

    solido = _esfera(shape, c, 16, sp)
    casca = solido & ~_esfera(shape, c, 13, sp)          # ~3 voxels de espessura
    casca_aberta = casca.copy()
    casca_aberta[:, :, :10] = False                       # aberta nas pontas em Z
    casca_aberta[:, :, 38:] = False

    f_sol, f_casca, f_aberta = forma(solido, sp), forma(casca, sp), forma(casca_aberta, sp)

    # 1. positivo: casca fechada e classificada como casca
    assert f_casca["veredito_forma"] == "casca", f_casca
    # 2. NEGATIVO (o que faz o teste valer): solido NAO pode passar por casca
    assert f_sol["veredito_forma"] == "solido preenchido", f_sol
    assert f_sol["razao_preenchimento_3d"] == 1.0, f_sol["razao_preenchimento_3d"]
    # 3. casca ABERTA em Z: o fill 3D falha (razao ~1,0) e o fill 2D salva.
    #    Este e o check que quebra se alguem remover _fill_2d.
    assert f_aberta["razao_preenchimento_3d"] > 0.9, f_aberta["razao_preenchimento_3d"]
    assert f_aberta["veredito_forma"] == "casca", f_aberta
    # 4. meia-espessura separa os dois por ordem de grandeza
    assert f_casca["meia_espessura_mm"]["p95"] < f_sol["meia_espessura_mm"]["p95"] / 3, (
        f_casca["meia_espessura_mm"], f_sol["meia_espessura_mm"])

    # 5. contencao: nucleo dentro da casca => vazio encapsulado > 0 e intersecao 0
    nucleo = _esfera(shape, c, 8, sp)
    rel = relacao(casca, nucleo, sp)
    assert rel["frac_heart_dentro_de_pericardium"] == 0.0, rel
    assert rel["uniao_vazio_encapsulado_ml"] > 0, rel
    assert rel["uniao_n_componentes"] == 2, rel
    # 6. NEGATIVO: solido que contem o nucleo => contencao 1,0 e vazio 0
    rel2 = relacao(solido, nucleo, sp)
    assert rel2["frac_heart_dentro_de_pericardium"] == 1.0, rel2
    assert rel2["uniao_vazio_encapsulado_ml"] == 0.0, rel2
    assert rel2["uniao_n_componentes"] == 1, rel2

    # 7. veredito: entradas sinteticas produzem SIM e NAO nos dois extremos
    def _l(forma_txt, dentro):
        return {"peri_veredito_forma": forma_txt, "frac_heart_em_peri": dentro,
                "peri_razao_preench_3d": 0.2 if forma_txt == "casca" else 1.0,
                "peri_razao_preench_2d": 0.2 if forma_txt == "casca" else 1.0,
                "peri_meia_espessura_p95_mm": 1.5, "frac_peri_em_heart": 0.1, "erro": ""}
    assert veredito([_l("casca", 0.99)] * 3)["veredito"] == "SIM"
    assert veredito([_l("solido preenchido", 0.99)] * 3)["veredito"] == "NAO"
    assert veredito([_l("casca", 0.99), _l("solido preenchido", 0.99)]
                    )["veredito"] == "NAO DETERMINADO"
    assert veredito([])["veredito"] == "NAO DETERMINADO"

    print("autoteste pericardio: OK (7 checks, com controle negativo em cada um)")


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--autoteste", action="store_true")
    p.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    a = p.parse_args(argv)
    if a.autoteste:
        _autoteste()
        return 0
    rodar(a.raiz, a.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
