"""
Fase 7 — Partes 9 e 17: definicao anatomica do esofago (medida) + BASELINE OFICIAL.

Este modulo faz DUAS coisas e nada mais:

PARTE A — aprofunda a secao 1.2 de docs/VRMED-ANATOMICAL-ONTOLOGY.md com MEDIDA.
    Quatro perguntas que a prosa nao responde e a grade responde:
      1. o GT do esofago encosta na traqueia / na aorta?  -> fronteira ambigua POR
         ADJACENCIA, o que muda o que se pode exigir de um modelo naquela borda;
      2. o GT inclui o lumen?  -> se o contorno fosse so parede, fill_holes 2D por
         fatia preencheria volume; se preenche ~0, o GT e macico;
      3. parede e lumen sao distinguiveis NESTA resolucao?  -> espessura
         caracteristica (2 x EDT no esqueleto) contra o spacing;
      4. ha campos de interrupcao?  -> fatias vazias DENTRO do suporte do GT.

PARTE B — mede o TotalSegmentator congelado (A_BASELINE_V1) contra o GT do esofago,
    POR CASO, no DEVELOPMENT. Vira o baseline oficial do experimento do esofago.

REGRA DE FASE, IMPOSTA EM CODIGO: so `development` do fase5/split.json. Os conjuntos
`validation` e `test` estao reservados para a hipotese heart->pericardium; `_casos()`
levanta RuntimeError se qualquer caso pedido nao estiver no development.

NAO TREINA NADA. A unica inferencia que este modulo pode disparar (`--aux`) e o
MESMO TotalSegmentator 2.18.0 congelado, apenas com outro `roi_subset`, para obter
traqueia e aorta — que NAO estao no roi_subset de 8 estruturas do baseline e por isso
nao existem em pred_masks/. Essa corrida traz `esophagus` junto DE PROPOSITO: e o
controle que prova que trocar o roi_subset nao mexeu na predicao do esofago.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from scipy import ndimage

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.espessura import calibre_mm  # noqa: E402
from scripts.validation.segmentation_metrics import compare_masks  # noqa: E402
from scripts.validation.tier2 import fase5, geometria  # noqa: E402
from scripts.validation.tier2 import rtstruct as rtst  # noqa: E402
from scripts.validation.tier2.benchmark_tier2 import recall_containment  # noqa: E402

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase7" / "esofago" / "baseline"
AUX_PADRAO = RAIZ_PADRAO / "fase7" / "esofago" / "aux_masks"

ROI_GT = "Esophagus"          # nome REAL da ROI no RTSTRUCT do LCTSC
PRED_ESOFAGO = "esophagus"    # nome de saida do TotalSegmentator
AUX_ROIS = ("trachea", "aorta", "esophagus")  # esophagus vai junto como CONTROLE
VIZINHOS = ("trachea", "aorta")

NM = "nao medido"
NA = "nao aplicavel"

# Conectividade 1 = vizinhanca de FACE (6 em 3D). "1 voxel" aqui e UM PASSO DA GRADE,
# nao 1 mm: a grade do LCTSC e anisotropica (~0,98 x 0,98 x 2,5-3,0 mm), entao um passo
# vale coisas diferentes em cada eixo. Por isso as fracoes em mm saem junto.
_FACE = ndimage.generate_binary_structure(3, 1)


# --------------------------------------------------------------------- utilidades


def _ml(m: np.ndarray, spacing) -> float:
    """Volume em mililitros a partir do spacing em mm por eixo."""
    return float(int(np.count_nonzero(m)) * float(np.prod(np.asarray(spacing, float))) / 1000.0)


def _fatias_com_voxel(m: np.ndarray) -> np.ndarray:
    """Indices Z (eixo 2) em que a mascara tem ao menos um voxel."""
    return np.flatnonzero(m.any(axis=(0, 1)))


def _superficie(m: np.ndarray) -> np.ndarray:
    """MESMA definicao de segmentation_metrics: camada interna de voxels de face.

    Reimplementada aqui em uma linha em vez de importada porque a funcao la e
    privada; o autoteste compara as duas para garantir que nao divergiram.
    """
    if not m.any():
        return np.zeros_like(m, dtype=bool)
    return m & ~ndimage.binary_erosion(m, structure=None, border_value=0)


def _dist(valores: list[float]) -> dict[str, Any]:
    """n / mediana / media / desvio / P5 / P25 / P75 / P95 / min / max.

    O pedido e explicito: nao publicar so a mediana. Quem vai treinar precisa da
    cauda, nao do centro.
    """
    v = np.asarray([x for x in valores if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"n": 0, "mediana": NM, "media": NM, "desvio": NM,
                "p5": NM, "p25": NM, "p75": NM, "p95": NM, "min": NM, "max": NM}
    return {
        "n": int(v.size),
        "mediana": float(np.median(v)),
        "media": float(v.mean()),
        "desvio": float(v.std(ddof=1)) if v.size > 1 else NA,
        "p5": float(np.percentile(v, 5)),
        "p25": float(np.percentile(v, 25)),
        "p75": float(np.percentile(v, 75)),
        "p95": float(np.percentile(v, 95)),
        "min": float(v.min()),
        "max": float(v.max()),
    }


def _casos(raiz: Path) -> list[str]:
    """SOMENTE o development. Qualquer outro conjunto e recusado aqui, nao adiante."""
    split = fase5.carregar_split(raiz)
    dev = sorted(split["development"])
    reservados = set(split["validation"]) | set(split["test"])
    if set(dev) & reservados:
        raise RuntimeError("split corrompido: caso em development e tambem em validation/test")
    return dev


def _guarda_development(casos: list[str], raiz: Path) -> None:
    dev = set(_casos(raiz))
    fora = sorted(set(casos) - dev)
    if fora:
        raise RuntimeError(
            f"caso(s) fora do development: {fora}. validation/test estao RESERVADOS "
            "nesta fase para a hipotese heart->pericardium — nem para conferir spacing."
        )


# ------------------------------------------------------- PARTE A — instrumentos


def frac_superficie_adjacente(gt: np.ndarray, outra: np.ndarray, spacing) -> dict:
    """Quanto da SUPERFICIE do GT esta encostada em `outra`.

    Duas leituras, porque a grade e anisotropica e uma so mentiria:
      - `frac_1passo_grade`: fracao da superficie do GT que cai na dilatacao de
        `outra` por UM passo de face. E o "<= 1 voxel" literal, na grade.
      - `frac_le_*mm`: fracao com distancia euclidiana (sampling=spacing) abaixo
        de um limiar em mm — comparavel entre casos com spacing diferente.

    `outra` vazia => tudo "nao aplicavel", nunca um zero que parece medida.
    """
    sup = _superficie(gt)
    n_sup = int(sup.sum())
    if n_sup == 0:
        return {"veredito": "invalido: GT vazio"}
    if not outra.any():
        return {"veredito": "nao aplicavel: mascara vizinha vazia", "n_superficie_gt": n_sup}

    passo = ndimage.binary_dilation(outra, structure=_FACE, iterations=1)
    edt = ndimage.distance_transform_edt(~outra, sampling=np.asarray(spacing, float))
    d = edt[sup]

    # ZONA DE COEXISTENCIA. A traqueia acaba na carina e o esofago segue ate o
    # diafragma: medir contato sobre a superficie INTEIRA do esofago dilui o
    # numero com fatias onde o vizinho nem existe. `_na_zona` usa como
    # denominador so a superficie do GT nas fatias Z em que o vizinho tem voxel.
    z_outra = _fatias_com_voxel(outra)
    zona = np.zeros(gt.shape[2], dtype=bool)
    zona[z_outra] = True
    sup_zona = sup & zona[None, None, :]
    n_zona = int(sup_zona.sum())

    return {
        "n_superficie_gt": n_sup,
        "frac_1passo_grade": float(np.count_nonzero(passo[sup]) / n_sup),
        "frac_le_1mm": float(np.count_nonzero(d <= 1.0) / n_sup),
        "frac_le_2mm": float(np.count_nonzero(d <= 2.0) / n_sup),
        "frac_le_5mm": float(np.count_nonzero(d <= 5.0) / n_sup),
        "d_mediana_mm": float(np.median(d)),
        "d_min_mm": float(d.min()),
        "sobreposicao_ml": _ml(gt & outra, spacing),
        "n_fatias_do_vizinho": int(z_outra.size),
        "n_superficie_gt_na_zona": n_zona,
        "frac_superficie_gt_na_zona": float(n_zona / n_sup),
        "frac_1passo_na_zona": (float(np.count_nonzero(passo[sup_zona]) / n_zona)
                                if n_zona else NA),
        "frac_le_2mm_na_zona": (float(np.count_nonzero(edt[sup_zona] <= 2.0) / n_zona)
                                if n_zona else NA),
        "veredito": "medido",
    }


def preenchimento_2d(m: np.ndarray) -> np.ndarray:
    """binary_fill_holes por FATIA AXIAL (eixo 2) — o que foi preenchido, so isso.

    Por fatia e nao em 3D de proposito: em 3D um tubo aberto nas duas pontas nao
    tem buraco topologico, entao um lumen vazado passaria despercebido. Na fatia,
    um anel vira buraco.
    """
    out = np.zeros_like(m, dtype=bool)
    for k in range(m.shape[2]):
        fatia = m[:, :, k]
        if fatia.any():
            out[:, :, k] = ndimage.binary_fill_holes(fatia) & ~fatia
    return out


# Faixas de HU. Sao convencao de leitura de TC, nao medida deste projeto — servem
# so para dizer DE QUE e feito o que esta dentro de cada mascara. A faixa de gordura
# (-190 a -30) e a usada em composicao corporal por TC; "ar" abaixo de -200 cobre gas
# no lumen sem invadir a faixa de gordura.
FAIXAS_HU: dict[str, tuple[float, float]] = {
    "ar": (-2000.0, -200.0),
    "gordura": (-190.0, -30.0),
    "tecido_mole": (-30.0, 100.0),
    "denso": (100.0, 4000.0),
}


def composicao_hu(mask: np.ndarray, imagem: np.ndarray, prefixo: str) -> dict:
    """De que e feito o que esta dentro da mascara: percentis de HU + fracoes por faixa.

    E daqui que sai a resposta mensuravel para "o GT inclui gordura periesofagica?"
    e "o lumen tem gas?" — perguntas que fill_holes nao responde quando o contorno e
    macico. Mascara vazia devolve 'nao aplicavel', nunca zero.
    """
    if not mask.any():
        return {f"{prefixo}_n_voxels": 0, f"{prefixo}_hu_mediana": NA}
    hu = imagem[mask].astype(np.float32)
    out = {
        f"{prefixo}_n_voxels": int(mask.sum()),
        f"{prefixo}_hu_p5": float(np.percentile(hu, 5)),
        f"{prefixo}_hu_mediana": float(np.median(hu)),
        f"{prefixo}_hu_p95": float(np.percentile(hu, 95)),
    }
    for nome, (lo, hi) in FAIXAS_HU.items():
        out[f"{prefixo}_frac_{nome}"] = float(np.count_nonzero((hu >= lo) & (hu < hi)) / hu.size)
    return out


def fatias_vazias_internas(m: np.ndarray) -> list[int]:
    """Indices Z sem nenhum voxel ENTRE a primeira e a ultima fatia com voxel."""
    z = _fatias_com_voxel(m)
    if z.size == 0:
        return []
    return sorted(set(range(int(z.min()), int(z.max()) + 1)) - set(int(k) for k in z))


def medir_definicao(caso: str, raiz: Path, aux_dir: Path) -> dict:
    """Parte A de UM caso. Vizinhos ausentes => 'nao medido', nunca zero."""
    dir_gt = raiz / caso / "gt"
    caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{ROI_GT}.nii.gz"
    spacing = tuple(geometria.descrever_nifti(dir_gt / rtst.NOME_IMAGEM)["zooms_mm"])
    geometria.verificar_alinhamento(caminho_gt, dir_gt / rtst.NOME_IMAGEM,
                                    rotulos=("gt_esofago", "imagem"))
    gt = rtst.carregar_mascara(caminho_gt)

    z = _fatias_com_voxel(gt)
    vazias = fatias_vazias_internas(gt)
    buracos = preenchimento_2d(gt)
    fatias_com_buraco = int(np.count_nonzero(buracos.any(axis=(0, 1))))
    cal = calibre_mm(gt, np.asarray(spacing, float))
    esp = cal["espessura_mediana_no_esqueleto_mm"]

    linha: dict[str, Any] = {
        "case_id": caso,
        "instituicao": fase5.instituicao_de(caso),
        "spacing_mm": [round(float(s), 6) for s in spacing],
        "volume_gt_ml": _ml(gt, spacing),
        "n_voxels_gt": int(gt.sum()),
        "z_primeira_fatia": int(z.min()), "z_ultima_fatia": int(z.max()),
        "n_fatias_gt": int(z.size),
        "n_fatias_no_intervalo": int(z.max() - z.min() + 1),
        # 4. campos de interrupcao
        "n_fatias_vazias_internas": len(vazias),
        "fatias_vazias_internas": vazias,
        # 2. lumen
        "lumen_voxels_preenchidos_2d": int(buracos.sum()),
        "lumen_volume_preenchido_ml": _ml(buracos, spacing),
        "lumen_frac_do_volume_gt": float(buracos.sum() / gt.sum()) if gt.any() else NA,
        "lumen_n_fatias_com_buraco": fatias_com_buraco,
        "lumen_frac_fatias_com_buraco": float(fatias_com_buraco / z.size) if z.size else NA,
        # 3. espessura
        "espessura_esqueleto_mm": esp,
        "calibre_mediano_mm": cal["calibre_mediano_mm"],
        "calibre_p90_mm": cal["calibre_p90_mm"],
        "calibre_max_mm": cal["calibre_max_mm"],
        "espessura_em_voxels_no_plano": float(esp / min(spacing[0], spacing[1])),
        "espessura_em_voxels_em_z": float(esp / spacing[2]),
    }

    # --- do que e feito o GT, e do que e feita a discordancia (parede/lumen/gordura)
    imagem = np.asarray(nib.load(str(dir_gt / rtst.NOME_IMAGEM)).dataobj)
    canto = imagem[:16, :16, :]  # controle: fora do corpo tem que ser ar (~ -1000 HU)
    linha["hu_controle_ar_fora_do_corpo"] = float(np.median(canto))
    linha["hu_controle_ok"] = bool(np.median(canto) < -800)
    pred_path = raiz / caso / "pred_masks" / f"{PRED_ESOFAGO}.nii.gz"
    pred = np.asarray(nib.load(str(pred_path)).dataobj) > 0.5
    linha.update(composicao_hu(gt, imagem, "hu_gt"))
    # INTERIOR do GT (erosao de 1 passo): separa "o contorno inclui gas do lumen" de
    # "o voxel da borda misturou esofago com pulmao vizinho". Se o ar sumir na erosao,
    # era volume parcial de borda; se persistir, e lumen dentro do contorno.
    linha.update(composicao_hu(ndimage.binary_erosion(gt, structure=_FACE, border_value=0),
                               imagem, "hu_gt_interior"))
    linha.update(composicao_hu(pred & ~gt, imagem, "hu_fp"))
    linha.update(composicao_hu(gt & ~pred, imagem, "hu_fn"))

    # --- extensao em Z. Orientacao LPS com affine[2,2] > 0 nos 30 casos: indice de Z
    #     maior = mais CRANIAL. Sinal positivo = a predicao passa do GT naquela ponta.
    z_pred = _fatias_com_voxel(pred)
    dz = float(spacing[2])
    linha.update({
        "z_pred_primeira": int(z_pred.min()), "z_pred_ultima": int(z_pred.max()),
        "n_fatias_predicao": int(z_pred.size),
        "erro_cranial_mm": float((int(z_pred.max()) - int(z.max())) * dz),
        "erro_distal_mm": float((int(z.min()) - int(z_pred.min())) * dz),
        "delta_comprimento_mm": float(
            ((int(z_pred.max()) - int(z_pred.min())) - (int(z.max()) - int(z.min()))) * dz),
        "frac_campo_gt": float(z.size / gt.shape[2]),
        "frac_campo_pred": float(z_pred.size / gt.shape[2]),
    })

    # 1. adjacencia — precisa das mascaras auxiliares (rodar `--aux` antes)
    for nome in VIZINHOS:
        p = aux_dir / caso / f"{nome}.nii.gz"
        if not p.exists():
            linha[f"adj_{nome}"] = {"veredito": f"{NM}: {p} ausente — rode --aux"}
            linha[f"adj_{nome}_frac_1passo"] = None
            continue
        geometria.verificar_alinhamento(p, caminho_gt, rotulos=(nome, "gt_esofago"))
        outra = np.asarray(nib.load(str(p)).dataobj) > 0.5
        r = frac_superficie_adjacente(gt, outra, spacing)
        linha[f"adj_{nome}"] = r
        linha[f"adj_{nome}_frac_1passo"] = r.get("frac_1passo_grade")
        linha[f"adj_{nome}_frac_le_2mm"] = r.get("frac_le_2mm")
        linha[f"adj_{nome}_frac_1passo_na_zona"] = r.get("frac_1passo_na_zona")
        linha[f"adj_{nome}_frac_le_2mm_na_zona"] = r.get("frac_le_2mm_na_zona")
        linha[f"adj_{nome}_frac_superficie_na_zona"] = r.get("frac_superficie_gt_na_zona")
        linha[f"adj_{nome}_volume_ml"] = _ml(outra, spacing)
    return linha


# ------------------------------------------------------- PARTE B — baseline oficial


def medir_baseline(caso: str, raiz: Path) -> dict:
    """Parte B de UM caso: predicao CRUA do A_BASELINE_V1 contra o GT do esofago.

    Variante B (campo completo) e a oficial — toda a extensao da predicao, sem
    recorte. A variante A (predicao limitada ao suporte do GT em Z) sai junto
    APENAS como conferencia contra os numeros ja publicados da coorte n=60; ela
    e circular por construcao (a janela vem do proprio GT) e nao e o baseline.
    """
    dir_gt, dir_pred = raiz / caso / "gt", raiz / caso / "pred_masks"
    caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{ROI_GT}.nii.gz"
    caminho_pred = dir_pred / f"{PRED_ESOFAGO}.nii.gz"

    # Parte K ANTES de qualquer medida: sem mesma grade, o Dice e mentira.
    geometria.verificar_alinhamento(caminho_pred, caminho_gt)
    spacing = tuple(geometria.descrever_nifti(dir_gt / rtst.NOME_IMAGEM)["zooms_mm"])

    gt = rtst.carregar_mascara(caminho_gt)
    pred = np.asarray(nib.load(str(caminho_pred)).dataobj) > 0.5

    m = compare_masks(pred, gt, spacing)
    rc = recall_containment(pred, gt)
    fp = pred & ~gt
    fn = gt & ~pred

    z_gt = _fatias_com_voxel(gt)
    z0, z1 = int(z_gt.min()), int(z_gt.max())
    no_suporte = pred.copy()
    no_suporte[:, :, :z0] = False
    no_suporte[:, :, z1 + 1:] = False
    mA = compare_masks(no_suporte, gt, spacing)

    fp_ml, fn_ml = _ml(fp, spacing), _ml(fn, spacing)
    vol_gt, vol_pred = _ml(gt, spacing), _ml(pred, spacing)
    return {
        "case_id": caso,
        "instituicao": fase5.instituicao_de(caso),
        "spacing_mm": [round(float(s), 6) for s in spacing],
        "dice": m["dice"],
        "iou": m["iou"],
        "hd95_mm": m["hd95_mm"],
        "assd_mm": m["assd_mm"],
        "hd_mm": m["hd_mm"],
        "nsd_1vox": m["nsd_1vox"],
        "precision": rc["precision_pred"],
        "recall": rc["recall_gt"],
        "volume_error_pct": m["volume_error_pct"],
        "volume_pred_ml": vol_pred,
        "volume_gt_ml": vol_gt,
        "erro_liquido_ml": round(vol_pred - vol_gt, 6),
        "fp_ml": fp_ml,
        "fn_ml": fn_ml,
        "erro_absoluto_ml": round(fp_ml + fn_ml, 6),
        "erro_absoluto_pct_do_gt": round(100.0 * (fp_ml + fn_ml) / vol_gt, 4) if vol_gt else NA,
        "fp_fora_do_suporte_gt_ml": _ml(pred & ~no_suporte, spacing),
        "fp_dentro_do_suporte_gt_ml": _ml(no_suporte & ~gt, spacing),
        "dice_variante_A_suporte_gt": mA["dice"],
        "hd95_variante_A_mm": mA["hd95_mm"],
    }


METRICAS_B = ("dice", "hd95_mm", "assd_mm", "precision", "recall", "volume_error_pct",
              "fp_ml", "fn_ml", "erro_absoluto_ml", "nsd_1vox", "iou",
              "volume_pred_ml", "volume_gt_ml", "erro_liquido_ml",
              "dice_variante_A_suporte_gt")


def agregar(linhas: list[dict], metricas=METRICAS_B) -> dict:
    """Distribuicao geral + estratificada por instituicao."""
    saida = {"geral": {mt: _dist([l[mt] for l in linhas]) for mt in metricas},
             "por_instituicao": {}}
    for inst in sorted({l["instituicao"] for l in linhas}):
        sub = [l for l in linhas if l["instituicao"] == inst]
        saida["por_instituicao"][inst] = {
            "n_casos": len(sub),
            "spacing_z_mm": sorted({round(l["spacing_mm"][2], 3) for l in sub}),
            **{mt: _dist([l[mt] for l in sub]) for mt in metricas},
        }
    return saida


# ------------------------------------------------------------------ inferencia aux


def rodar_aux(casos: list[str], raiz: Path, destino: Path, log=print) -> dict:
    """Traqueia + aorta (+ esofago como controle) pelo MESMO modelo congelado.

    Nao e treino, nao e modelo novo, nao e pos-processamento: e o TotalSegmentator
    2.18.0 tarefa `total`, com os MESMOS parametros de inferencia do A_BASELINE_V1,
    mudando UMA coisa — o roi_subset. E isso e declarado como ressalva: com
    robust_crop=True o recorte depende das ROIs pedidas, entao a corrida auxiliar
    nao e bit-a-bit a mesma. O `esophagus` vai junto exatamente para MEDIR se essa
    diferenca de recorte mexeu na predicao (ver conferir_aux).
    """
    from scripts.clinica.segmentacao import rodar_segmentacao

    _guarda_development(casos, raiz)
    destino.mkdir(parents=True, exist_ok=True)
    feitos = []
    for i, caso in enumerate(casos, 1):
        saida = destino / caso
        if all((saida / f"{n}.nii.gz").exists() for n in AUX_ROIS):
            log(f"[{i}/{len(casos)}] {caso}: ja existe — pulado")
            continue
        log(f"[{i}/{len(casos)}] {caso}: segmentando traqueia/aorta/esofago…")
        rodar_segmentacao(raiz / caso / "gt" / rtst.NOME_IMAGEM, saida,
                          estruturas=list(AUX_ROIS), fast=False, task="total", log=log)
        feitos.append(caso)
    return {"casos_rodados": feitos, "destino": str(destino)}


def conferir_aux(casos: list[str], raiz: Path, aux_dir: Path) -> dict:
    """CONTROLE: o esofago da corrida auxiliar reproduz o do baseline congelado?

    Se o Dice for 1,0 em todos os casos, trocar o roi_subset nao mexeu na predicao
    e as mascaras de traqueia/aorta valem como contexto anatomico do MESMO estado
    do modelo. Se nao for, o numero sai publicado assim mesmo — a divergencia e
    informacao sobre o instrumento, nao coisa para esconder.
    """
    def _dice(x, y):
        s = int(x.sum()) + int(y.sum())
        return 1.0 if s == 0 else float(2 * np.count_nonzero(x & y) / s)

    dices = []
    for caso in casos:
        p_aux = aux_dir / caso / f"{PRED_ESOFAGO}.nii.gz"
        p_base = raiz / caso / "pred_masks" / f"{PRED_ESOFAGO}.nii.gz"
        if not p_aux.exists():
            continue
        a = np.asarray(nib.load(str(p_aux)).dataobj) > 0.5
        b = np.asarray(nib.load(str(p_base)).dataobj) > 0.5
        gt = rtst.carregar_mascara(raiz / caso / "gt" / f"{rtst.PREFIXO_MASCARA}{ROI_GT}.nii.gz")
        d_aux, d_base = _dice(a, gt), _dice(b, gt)
        dices.append({"case_id": caso,
                      "dice_aux_vs_baseline": _dice(a, b),
                      "voxels_diferentes": int(np.count_nonzero(a ^ b)),
                      # o que interessa nao e so "as mascaras diferem": e QUANTO O PLACAR
                      # anda quando a unica coisa trocada e o roi_subset.
                      "dice_vs_gt_baseline": d_base,
                      "dice_vs_gt_aux": d_aux,
                      "delta_dice_vs_gt": d_aux - d_base})
    if not dices:
        return {"veredito": f"{NM}: nenhuma mascara auxiliar encontrada"}
    d = [x["dice_aux_vs_baseline"] for x in dices]
    delta = [x["delta_dice_vs_gt"] for x in dices]
    identicos = sum(1 for x in dices if x["voxels_diferentes"] == 0)
    return {
        "n": len(dices),
        "n_identicos_voxel_a_voxel": identicos,
        "dice_aux_vs_baseline": {"mediana": float(np.median(d)), "min": float(min(d)),
                                 "max": float(max(d))},
        "delta_dice_vs_gt": {"mediana": float(np.median(delta)), "min": float(min(delta)),
                             "max": float(max(delta)),
                             "media_abs": float(np.mean(np.abs(delta))),
                             "n_pioraram": sum(1 for x in delta if x < 0),
                             "n_melhoraram": sum(1 for x in delta if x > 0)},
        "por_caso": dices,
        "veredito": (
            "corrida auxiliar reproduz o esofago do baseline voxel a voxel"
            if identicos == len(dices) else
            f"SENSIBILIDADE AO roi_subset: trocar so a lista de ROIs muda a predicao do "
            f"esofago (Dice entre as duas predicoes: mediana {float(np.median(d)):.4f}, "
            f"min {min(d):.4f}) e desloca o placar contra o GT em "
            f"{float(np.mean(np.abs(delta))):.4f} de Dice em media absoluta. Com "
            f"robust_crop=True o recorte depende das ROIs pedidas — o baseline e "
            f"reprodutivel COM a mesma lista, nao independente dela."),
    }


# ------------------------------------------------------------------------ relatorio


def _f(v, casas=4):
    if v is None:
        return NM
    if isinstance(v, str):
        return v
    return f"{float(v):.{casas}f}".replace(".", ",")


def _tabela_dist(titulo: str, dists: dict, metricas, casas=4) -> str:
    t = f"\n### {titulo}\n\n| metrica | n | P5 | P25 | mediana | P75 | P95 | media | desvio |\n"
    t += "|---|---|---|---|---|---|---|---|---|\n"
    for mt in metricas:
        d = dists.get(mt)
        if not d:
            continue
        t += (f"| {mt} | {d['n']} | {_f(d['p5'], casas)} | {_f(d['p25'], casas)} | "
              f"**{_f(d['mediana'], casas)}** | {_f(d['p75'], casas)} | {_f(d['p95'], casas)} | "
              f"{_f(d['media'], casas)} | {_f(d['desvio'], casas)} |\n")
    return t


def escrever_summary(res: dict, destino: Path) -> Path:
    ag = res["baseline"]["agregado"]
    linhas_b = res["baseline"]["por_caso"]
    defs = res["definicao"]["agregado"]
    md = [
        "# Fase 7 — esofago: baseline oficial e definicao medida",
        "",
        f"Gerado em {res['gerado_em']}. Conjunto: **development, n={len(linhas_b)}** "
        "(validation/test reservados para a hipotese heart->pericardium).",
        "",
        f"Modelo: **{res['baseline']['modelo']}** — saida CRUA, zero pos-processamento.",
        "",
        "## Parte B — BASELINE OFICIAL (variante B, campo completo)",
        "",
        "Qualquer modelo novo do esofago tem de superar esta distribuicao. A mediana nao",
        "e o criterio sozinha: o desvio e as caudas estao aqui porque e a cauda que",
        "quebra treino.",
        _tabela_dist("Geral (n=%d)" % len(linhas_b), ag["geral"], METRICAS_B),
        "",
        "### Estratificado por instituicao",
        "",
        "| instituicao | n | dz (mm) | dice mediana | dice P5 | dice P95 | hd95 mediana | "
        "assd mediana | recall mediana | precision mediana | erro_abs mediana (mL) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for inst, d in ag["por_instituicao"].items():
        md.append(
            f"| {inst} | {d['n_casos']} | {'; '.join(str(x).replace('.', ',') for x in d['spacing_z_mm'])} | "
            f"**{_f(d['dice']['mediana'])}** | {_f(d['dice']['p5'])} | {_f(d['dice']['p95'])} | "
            f"{_f(d['hd95_mm']['mediana'], 3)} | {_f(d['assd_mm']['mediana'], 3)} | "
            f"{_f(d['recall']['mediana'])} | {_f(d['precision']['mediana'])} | "
            f"{_f(d['erro_absoluto_ml']['mediana'], 2)} |"
        )
    md += ["", "### Conferencia contra a coorte publicada (n=60, variante B)", "",
           "| metrica | coorte n=60 | development n=%d | delta |" % len(linhas_b),
           "|---|---|---|---|"]
    for mt, publicado in res["conferencia"]["coorte_n60_variante_B"].items():
        obtido = ag["geral"].get(mt, {}).get("mediana")
        delta = (obtido - publicado) if isinstance(obtido, float) else None
        md.append(f"| {mt} | {_f(publicado)} | {_f(obtido)} | {_f(delta)} |")
    md += ["", res["conferencia"]["veredito"], ""]

    md += ["", "## Parte A — a definicao, medida", ""]
    md.append(_tabela_dist("Distribuicoes (n=%d)" % len(res["definicao"]["por_caso"]),
                           defs, list(defs.keys())))
    md += ["", "### Adjacencia (fracao da superficie do GT encostada no vizinho)", "",
           res["definicao"]["adjacencia_nota"], ""]
    ctrl = res["definicao"].get("controle_aux", {})
    md.append(f"Controle da corrida auxiliar: {ctrl.get('veredito', NM)}")
    caminho = destino / "summary.md"
    caminho.write_text("\n".join(md) + "\n", encoding="utf-8")
    return caminho


# ------------------------------------------------------------------------ execucao


def rodar(raiz: Path = RAIZ_PADRAO, destino: Path = SAIDA_PADRAO,
          aux_dir: Path = AUX_PADRAO, log=print) -> dict:
    casos = _casos(raiz)
    _guarda_development(casos, raiz)
    destino.mkdir(parents=True, exist_ok=True)

    log(f"development: {len(casos)} casos")
    linhas_b, linhas_a = [], []
    for i, caso in enumerate(casos, 1):
        b = medir_baseline(caso, raiz)
        linhas_b.append(b)
        log(f"[{i}/{len(casos)}] {caso}: dice={b['dice']:.4f} hd95={b['hd95_mm']:.2f} "
            f"recall={b['recall']:.4f} prec={b['precision']:.4f} "
            f"erro_abs={b['erro_absoluto_ml']:.1f} mL")
        a = medir_definicao(caso, raiz, aux_dir)
        linhas_a.append(a)
        log(f"          lumen={a['lumen_volume_preenchido_ml']:.4f} mL "
            f"esp={a['espessura_esqueleto_mm']:.2f} mm "
            f"vazias={a['n_fatias_vazias_internas']} "
            f"adj_traq={a.get('adj_trachea_frac_1passo')}")

    # ---- conferencia contra a coorte publicada (medianas, variante B, n=60)
    publicado = {"dice": 0.8003, "hd95_mm": 5.3916, "assd_mm": 1.2727,
                 "recall": 0.7851, "precision": 0.8098, "volume_error_pct": -0.3626,
                 "nsd_1vox": 0.8786, "erro_absoluto_ml": 16.098, "volume_gt_ml": 40.6396}
    ag = agregar(linhas_b)
    delta_dice = ag["geral"]["dice"]["mediana"] - publicado["dice"]

    metricas_a = ("volume_gt_ml", "espessura_esqueleto_mm", "espessura_em_voxels_no_plano",
                  "espessura_em_voxels_em_z", "calibre_mediano_mm", "calibre_p90_mm",
                  "calibre_max_mm", "lumen_volume_preenchido_ml", "lumen_frac_do_volume_gt",
                  "lumen_n_fatias_com_buraco", "lumen_frac_fatias_com_buraco",
                  "n_fatias_gt", "n_fatias_vazias_internas",
                  "erro_cranial_mm", "erro_distal_mm", "delta_comprimento_mm",
                  "frac_campo_gt", "frac_campo_pred",
                  "hu_gt_interior_frac_ar", "hu_gt_interior_frac_gordura",
                  "hu_gt_interior_frac_tecido_mole", "hu_gt_interior_hu_mediana",
                  "adj_trachea_frac_1passo", "adj_trachea_frac_le_2mm",
                  "adj_trachea_frac_1passo_na_zona", "adj_trachea_frac_le_2mm_na_zona",
                  "adj_trachea_frac_superficie_na_zona",
                  "adj_aorta_frac_1passo", "adj_aorta_frac_le_2mm",
                  "adj_aorta_frac_1passo_na_zona", "adj_aorta_frac_le_2mm_na_zona",
                  "adj_aorta_frac_superficie_na_zona",
                  "hu_gt_hu_mediana", "hu_gt_hu_p5", "hu_gt_hu_p95",
                  "hu_gt_frac_ar", "hu_gt_frac_gordura", "hu_gt_frac_tecido_mole",
                  "hu_gt_frac_denso",
                  "hu_fp_hu_mediana", "hu_fp_frac_ar", "hu_fp_frac_gordura",
                  "hu_fp_frac_tecido_mole",
                  "hu_fn_hu_mediana", "hu_fn_frac_ar", "hu_fn_frac_gordura",
                  "hu_fn_frac_tecido_mole")
    ag_a = {mt: _dist([l.get(mt) for l in linhas_a]) for mt in metricas_a}

    res = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conjunto": "development",
        "n_casos": len(casos),
        "casos": casos,
        "ressalva_de_fase": ("validation e test NAO foram lidos: reservados para a hipotese "
                             "heart->pericardium"),
        "baseline": {
            "id": "BASELINE_ESOFAGO_V1",
            "modelo": (f"TotalSegmentator {fase5.A_BASELINE_V1['modelo']['TotalSegmentator']} "
                       f"task={fase5.A_BASELINE_V1['modelo']['task']}"),
            "parametros_de_inferencia": fase5.A_BASELINE_V1["parametros_de_inferencia"],
            "postprocessing": fase5.A_BASELINE_V1["postprocessing"],
            "variante_oficial": ("B_campo_completo — toda a extensao da predicao, sem recorte. "
                                 "A variante A (suporte do GT em Z) sai junto so como "
                                 "conferencia; e circular por construcao."),
            "por_caso": linhas_b,
            "agregado": ag,
        },
        "definicao": {
            "por_caso": linhas_a,
            "agregado": ag_a,
            "adjacencia_nota": (
                "`frac_1passo_grade` = fracao dos voxels de superficie do GT que caem na "
                "dilatacao do vizinho por UM passo de face. Na grade do LCTSC um passo vale "
                "~0,98 mm no plano e 2,5-3,0 mm em Z — por isso as fracoes em mm saem junto."
            ),
            "controle_aux": conferir_aux(casos, raiz, aux_dir),
        },
        "conferencia": {
            "coorte_n60_variante_B": publicado,
            "delta_dice_mediana": float(delta_dice),
            "veredito": (
                f"Dice mediano do development {ag['geral']['dice']['mediana']:.4f} contra "
                f"{publicado['dice']:.4f} da coorte n=60 (delta {delta_dice:+.4f}); "
                + ("compativel — o subconjunto reproduz o instrumento."
                   if abs(delta_dice) <= 0.02 else
                   "DIVERGENTE acima de 0,02 — investigar o instrumento antes de usar.")
            ),
        },
    }

    (destino / "baseline_esofago.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    cols_b = [c for c in linhas_b[0] if c != "spacing_mm"] + ["spacing_mm"]
    with (destino / "baseline_esofago.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols_b)
        w.writeheader()
        for l in linhas_b:
            w.writerow({**l, "spacing_mm": ";".join(str(s) for s in l["spacing_mm"])})

    cols_a = ["case_id", "instituicao", "volume_gt_ml", "n_fatias_gt",
              "erro_cranial_mm", "erro_distal_mm", "delta_comprimento_mm",
              "frac_campo_gt", "frac_campo_pred",
              "hu_gt_interior_frac_ar", "hu_gt_interior_frac_gordura",
              "n_fatias_vazias_internas", "lumen_voxels_preenchidos_2d",
              "lumen_volume_preenchido_ml", "lumen_frac_do_volume_gt",
              "lumen_n_fatias_com_buraco", "espessura_esqueleto_mm",
              "espessura_em_voxels_no_plano", "espessura_em_voxels_em_z",
              "calibre_mediano_mm", "calibre_p90_mm", "calibre_max_mm",
              "adj_trachea_frac_1passo", "adj_trachea_frac_le_2mm",
              "adj_trachea_frac_1passo_na_zona", "adj_trachea_frac_superficie_na_zona",
              "adj_aorta_frac_1passo", "adj_aorta_frac_le_2mm",
              "adj_aorta_frac_1passo_na_zona", "adj_aorta_frac_superficie_na_zona",
              "hu_gt_hu_mediana", "hu_gt_frac_ar", "hu_gt_frac_gordura",
              "hu_gt_frac_tecido_mole", "hu_gt_frac_denso",
              "hu_fp_hu_mediana", "hu_fp_frac_gordura", "hu_fp_frac_tecido_mole",
              "hu_fn_hu_mediana", "hu_fn_frac_gordura", "hu_fn_frac_tecido_mole",
              "hu_controle_ok", "spacing_mm"]
    with (destino / "definicao_esofago.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols_a, extrasaction="ignore")
        w.writeheader()
        for l in linhas_a:
            w.writerow({**{k: l.get(k) for k in cols_a},
                        "spacing_mm": ";".join(str(s) for s in l["spacing_mm"])})

    caminho_md = escrever_summary(res, destino)
    log(f"gravado: {destino}/baseline_esofago.csv, .json, definicao_esofago.csv, {caminho_md.name}")
    log(res["conferencia"]["veredito"])
    return res


# ------------------------------------------------------------------------ autoteste


def _autoteste() -> None:
    """Cada instrumento com CONTROLE POSITIVO: tem que FALHAR quando deveria falhar."""
    spacing = (0.977, 0.977, 3.0)

    # --- _superficie: identica a de segmentation_metrics (nao pode ter divergido)
    from scripts.validation.segmentation_metrics import _superficie as _sup_ref
    tubo = np.zeros((40, 40, 20), dtype=bool)
    tubo[18:24, 18:24, 3:17] = True
    assert np.array_equal(_superficie(tubo), _sup_ref(tubo)), "fronteira divergiu de segmentation_metrics"

    # --- adjacencia: encostado -> alto; longe -> ZERO (se der > 0, o instrumento mente)
    colado = np.zeros_like(tubo)
    colado[24:30, 18:24, 3:17] = True          # face a face com o tubo
    r_perto = frac_superficie_adjacente(tubo, colado, spacing)
    assert r_perto["frac_1passo_grade"] > 0.10, r_perto
    longe = np.zeros_like(tubo)
    longe[0:4, 0:4, 3:17] = True
    r_longe = frac_superficie_adjacente(tubo, longe, spacing)
    assert r_longe["frac_1passo_grade"] == 0.0, r_longe
    assert r_longe["frac_le_2mm"] == 0.0 and r_longe["d_mediana_mm"] > 5.0, r_longe
    assert r_perto["d_mediana_mm"] < r_longe["d_mediana_mm"]
    vazia = frac_superficie_adjacente(tubo, np.zeros_like(tubo), spacing)
    assert vazia["veredito"].startswith(NA), vazia   # vizinho vazio nao vira zero

    # zona de coexistencia: vizinho em METADE das fatias tem que DILUIR a fracao
    # global e NAO a da zona (e exatamente o vies que o numero global sofreria com
    # a traqueia acabando na carina). Se as duas caissem juntas, a correcao e falsa.
    meio = colado.copy()
    meio[:, :, 10:] = False
    r_meio = frac_superficie_adjacente(tubo, meio, spacing)
    assert r_meio["frac_1passo_grade"] < r_perto["frac_1passo_grade"], r_meio
    assert r_meio["frac_1passo_na_zona"] > r_meio["frac_1passo_grade"], r_meio
    assert 0.3 < r_meio["frac_superficie_gt_na_zona"] < 0.8, r_meio

    # --- lumen: anel 2D TEM que ser preenchido; macico NAO pode ser
    anel = np.zeros((40, 40, 20), dtype=bool)
    yy, xx = np.mgrid[0:40, 0:40]
    rad = np.hypot(yy - 20, xx - 20)
    anel[..., 3:17] = ((rad >= 4) & (rad <= 7))[..., None]
    preenchido = preenchimento_2d(anel)
    esperado = int(np.count_nonzero(rad < 4)) * 14
    assert abs(int(preenchido.sum()) - esperado) <= esperado * 0.05, (int(preenchido.sum()), esperado)
    assert int(preenchimento_2d(tubo).sum()) == 0, "fill_holes preencheu massa macica"

    # --- interrupcao: buraco TEM que ser detectado; continuo nao pode acusar
    assert fatias_vazias_internas(tubo) == []
    furado = tubo.copy()
    furado[:, :, 8:10] = False
    assert fatias_vazias_internas(furado) == [8, 9], fatias_vazias_internas(furado)
    # e o buraco nao pode ser confundido com o fim da estrutura
    cortado = tubo.copy()
    cortado[:, :, 12:] = False
    assert fatias_vazias_internas(cortado) == []

    # --- espessura: fantoma de calibre conhecido (6 voxels x 0,977 = 5,86 mm)
    cal = calibre_mm(tubo, np.asarray(spacing, float))
    assert 4.0 < cal["espessura_mediana_no_esqueleto_mm"] < 8.0, cal

    # --- metricas: perfeito=1; EROSAO (controle positivo do regime) tem que cair
    m_id = compare_masks(tubo, tubo, spacing)
    assert m_id["dice"] == 1.0 and m_id["hd95_mm"] == 0.0, m_id
    erodido = ndimage.binary_erosion(tubo, structure=_FACE, border_value=0)
    m_er = compare_masks(erodido, tubo, spacing)
    rc_er = recall_containment(erodido, tubo)
    assert m_er["dice"] < 0.95 and rc_er["recall_gt"] < 1.0 and rc_er["precision_pred"] == 1.0, (m_er, rc_er)
    assert _ml(erodido & ~tubo, spacing) == 0.0 and _ml(tubo & ~erodido, spacing) > 0.0

    # --- HU: fantoma com composicao CONHECIDA tem que sair na faixa certa, e a
    #     faixa errada tem que sair ZERO (senao o classificador de faixa e decorativo)
    img = np.full(tubo.shape, -1000.0, dtype=np.float32)   # ar em todo lugar
    img[tubo] = 40.0                                       # tecido mole dentro do tubo
    gordura_falsa = np.zeros_like(tubo)
    gordura_falsa[24:30, 18:24, 3:17] = True
    img[gordura_falsa] = -100.0                            # gordura ao lado
    c_gt = composicao_hu(tubo, img, "x")
    assert c_gt["x_frac_tecido_mole"] == 1.0 and c_gt["x_frac_gordura"] == 0.0, c_gt
    assert c_gt["x_hu_mediana"] == 40.0, c_gt
    c_fat = composicao_hu(gordura_falsa, img, "x")
    assert c_fat["x_frac_gordura"] == 1.0 and c_fat["x_frac_tecido_mole"] == 0.0, c_fat
    c_ar = composicao_hu(~(tubo | gordura_falsa), img, "x")
    assert c_ar["x_frac_ar"] == 1.0, c_ar
    assert composicao_hu(np.zeros_like(tubo), img, "x")["x_hu_mediana"] == NA

    # --- _dist: nao pode inventar numero em lista vazia
    assert _dist([])["mediana"] == NM and _dist([1.0, 2.0, 3.0])["mediana"] == 2.0

    print("baseline_esofago.py: autoteste OK (6 instrumentos com controle positivo)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    p.add_argument("--aux-dir", type=Path, default=AUX_PADRAO)
    p.add_argument("--aux", action="store_true",
                   help="roda o TotalSegmentator congelado para traqueia/aorta/esofago")
    p.add_argument("--autoteste", action="store_true")
    a = p.parse_args(argv)
    if a.autoteste:
        _autoteste()
        return 0
    if a.aux:
        rodar_aux(_casos(a.raiz), a.raiz, a.aux_dir)
        print(json.dumps(conferir_aux(_casos(a.raiz), a.raiz, a.aux_dir)["veredito"],
                         ensure_ascii=False))
        return 0
    rodar(a.raiz, a.saida, a.aux_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
