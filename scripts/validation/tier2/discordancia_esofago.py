"""Fase 6 (Partes 3 e 4) — mapa de DISCORDANCIA ANATOMICA do esofago.

A fase 5 fechou duas coisas sobre o esofago: o erro e de FRONTEIRA (frac_FP_extensao
0,177; diferenca de comprimento mediana exatamente 0,000 mm) e NENHUMA das 8 variantes
de morfologia testadas mexeu no dice (teto de +0,0004, 25x abaixo do limiar de 0,01).

A pergunta desta fase e ANTERIOR a "que operacao conserta": parte desse erro e
DEFINICAO e nao erro? Tres regimes, mutuamente exclusivos por construcao:

  LOCALIZACAO — a predicao esta em OUTRO LUGAR do plano. Assinatura: centroide por
                fatia distante, e uma TRANSLACAO por fatia remove o erro.
  EXTENSAO    — as duas mascaras cobrem intervalos diferentes em Z. Assinatura: erro
                em fatias onde a outra mascara nao tem voxel nenhum.
  DEFINICAO   — a predicao esta no lugar certo, no intervalo certo, com espessura ou
                limite lateral diferente. Assinatura: o que SOBRA depois de descontar
                as duas anteriores — E que seja SISTEMATICO E NO MESMO SENTIDO dentro
                de cada instituicao.

------------------------------------------------------------------------------
A DECOMPOSICAO, declarada antes de rodar

Sobre o volume de erro (FP + FN, em mL), por caso:

  erro_total = extensao + lateral

  extensao = FP em fatias Z sem voxel de GT  +  FN em fatias Z sem voxel de predicao
             (as duas mascaras nem se encontram naquela fatia — nao ha fronteira ali)

  lateral  = o resto: erro em fatias onde AS DUAS existem. Ele e reparticionado por
             uma TRANSLACAO POR FATIA, do centroide da predicao para o centroide do
             GT, arredondada para voxel inteiro:

    localizacao = reducao do erro lateral produzida por essa translacao (>= 0)
    definicao_residual = o erro lateral que SOBRA depois dela

CEILING DECLARADO desta decomposicao: a translacao pelo centroide NAO e a translacao
otima para o erro — e a translacao que a propria medida de centroide indica. Ela
SUBESTIMA `localizacao` e portanto SUPERESTIMA `definicao_residual`. Trocar por busca
exaustiva do deslocamento otimo mudaria o numero na direcao de mais localizacao; nao
foi feito porque a pergunta e se o centroide esta alinhado, e nao qual o melhor
alinhamento possivel.

E `definicao_residual` NAO E "definicao" por si so. Um erro de fronteira do modelo
tambem cai ali. O que separa os dois e o SEGUNDO teste, o de consistencia
INTRA-instituicao (`_consistencia`): se dentro de uma instituicao a razao de area
aponta para o MESMO lado em >= LIMIAR_CONSISTENCIA_CASOS dos casos E o centroide esta
alinhado, o residuo e COMPATIVEL COM convencao de contorno. Se o sentido oscila dentro
da mesma instituicao, e erro de fronteira do modelo. Por isso o campo se chama
`frac_compativel_com_definicao` e nao `frac_definicao`: nenhuma medida aqui PROVA
definicao — ela so e ou nao e compativel com definicao.
------------------------------------------------------------------------------

USO DO GT: o GT AVALIA. Ele entra em toda medida como referencia (centroide alvo,
area alvo, suporte em Z alvo) e em NENHUMA como construtor: nada aqui recorta a
predicao no alcance do GT, nem grava mascara, nem extrai constante do GT para uma
regra futura. As unicas constantes do modulo vem da grade de voxel e de combinatoria
declarada — origem escrita em cada uma.

TIER: diagnostico do bloco A (segmentacao). Uso educacional/experimental — "caso" e
"estrutura", nunca "paciente". Somente o split `development`; `validation` e `test`
nao sao lidos.

  python -m scripts.validation.tier2.discordancia_esofago --autoteste
  python -m scripts.validation.tier2.discordancia_esofago
  python -m scripts.validation.tier2.discordancia_esofago --estrutura Esophagus --estrutura SpinalCord
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, shift as _shift

from . import diagnostico_longitudinal as diag
from . import fase5, geometria, mapeamento
from . import rtstruct as rtst
from .mapa_erro import _frac, _ml, _p, _recorte

RAIZ_PADRAO = fase5.RAIZ
SAIDA_PADRAO = RAIZ_PADRAO / "fase6" / "esofago"
SPLIT_USADO = "development"  # `validation` e `test` nao sao lidos nesta fase

NA = "nao aplicavel"
NM = "nao medido"

# --------------------------------------------------------------------- constantes
# Nenhuma vem do GT nem de resultado observado. Origem declarada em cada linha.

# Centroide "alinhado". Vem da GRADE: 2 voxels no plano a 0,98 mm = 1,95 mm. Abaixo
# disso o deslocamento do centroide de uma estrutura de ~10 mm de diametro esta na
# ordem do proprio erro de rasterizacao do contorno.
#
# DEFEITO CONHECIDO deste limiar, achado pelo CONTRASTE e nao pelo alvo (ver
# `contraste_instrumento/`): 2,0 mm e calibrado para uma estrutura de ~10 mm de
# diametro. No `Heart` — ~100 mm, GT superconjunto por envelope assimetrico — o
# deslocamento do centroide da 4,79 mm e este limiar rotularia LOCALIZACAO, enquanto a
# propria decomposicao mede frac_localizacao = 0,0094. Envelope assimetrico desloca o
# centroide sem ser deslocamento. Por isso o limiar em mm NAO decide mais nada: ele
# continua reportado como diagnostico, e quem decide o regime e `LIMIAR_DOMINANCIA`
# aplicado a `frac_localizacao`, que e adimensional e ja estava declarado.
# A correcao e NEUTRA sobre o esofago: la o deslocamento mediano por instituicao e
# 1,04-1,49 mm, abaixo de 2,0 nos dois criterios. Verificado reexecutando.
LIMIAR_CENTROIDE_ALINHADO_MM = 2.0

# Consistencia INTRA-instituicao. Vem de COMBINATORIA, nao de resultado: com 10 casos
# por instituicao no development, a probabilidade de >= 9 caírem do mesmo lado sob
# moeda honesta e 2*(C(10,9)+C(10,10))/2^10 = 22/1024 = 0,0215. 0,90 e o menor limiar
# que derruba a explicacao "e so acaso" abaixo de 5 % com este n.
LIMIAR_CONSISTENCIA_CASOS = 0.90

# Um regime "domina" o erro quando leva mais da metade dele. Convencao de redacao do
# relatorio; nao decide intervencao nenhuma.
LIMIAR_DOMINANCIA = 0.50

# Autoteste: quanto o regime certo tem que levar, e quanto os outros dois podem levar.
# Se estes nao separarem, o instrumento nao serve.
AUTOTESTE_MIN_DOMINANTE = 0.80
AUTOTESTE_MAX_OUTROS = 0.20

COLUNAS = (
    "case_id", "instituicao", "structure", "dz_mm", "spacing_mm", "orientacao",
    "volume_gt_mL", "volume_pred_mL",
    "erro_total_mL", "FP_total_mL", "FN_total_mL",
    "extensao_mL", "FP_longitudinal_mL", "FN_longitudinal_mL",
    "lateral_mL", "FP_lateral_mL", "FN_lateral_mL",
    "localizacao_mL", "definicao_residual_mL",
    "frac_extensao", "frac_localizacao", "frac_definicao_residual",
    "desloc_centroide_mm_mediana", "desloc_centroide_mm_p95", "desloc_centroide_mm_max",
    "dist_radial_FP_mm_mediana", "dist_radial_FP_mm_p95",
    "dist_radial_FN_mm_mediana", "dist_radial_FN_mm_p95",
    "espessura_erro_mm_mediana", "espessura_erro_mm_p95",
    "razao_area_mediana", "razao_area_p5", "razao_area_p95",
    "frac_fatias_mais_estreita", "frac_fatias_mais_larga", "frac_fatias_igual",
    "sentido_do_caso",
    "n_fatias_gt", "n_fatias_pred", "n_fatias_sobrepostas",
    "comprimento_gt_mm", "comprimento_pred_mm", "diferenca_comprimento_mm",
    "frac_campo_gt", "frac_campo_pred",
    "conferencia_FP_extensao_delta_mL",
    "alinhamento", "erro",
)

COLUNAS_FATIA = (
    "case_id", "instituicao", "structure", "z",
    "area_gt_mm2", "area_pred_mm2", "razao_pred_gt",
    "desloc_centroide_mm", "d_eixo0_mm", "d_eixo1_mm",
    "erro_lateral_antes_mL", "erro_lateral_apos_translacao_mL",
    "shift_voxels_eixo0", "shift_voxels_eixo1",
)


# ------------------------------------------------------------------------ nucleo


def _centroide(m2d: np.ndarray) -> tuple[float, float] | None:
    """Centroide (eixo0, eixo1) em INDICE de voxel de uma fatia booleana, ou None."""
    idx = np.flatnonzero(m2d.ravel())
    if not idx.size:
        return None
    linhas, colunas = np.unravel_index(idx, m2d.shape)
    return float(linhas.mean()), float(colunas.mean())


def decompor(pred: np.ndarray, gt: np.ndarray, spacing, orientacao: str = "???") -> dict:
    """Decompoe o erro de UM par (predicao, GT) ja alinhado em extensao/localizacao/definicao.

    Nucleo puro: nao le arquivo, nao escreve nada. E o que o autoteste exercita com
    controles positivos.
    """
    pred = np.asarray(pred) > 0.5
    gt = np.asarray(gt) > 0.5
    spacing = tuple(float(s) for s in spacing)
    area_voxel_mm2 = spacing[0] * spacing[1]
    voxel_mm3 = area_voxel_mm2 * spacing[2]

    # Recorte de custo: contem GT + predicao + 2 voxels de fundo em volta, entao a
    # EDT calculada dentro dele e exata (o vizinho procurado nunca cai fora).
    cortes, offset = _recorte(pred, gt)
    p, g = pred[cortes], gt[cortes]
    fp, fn = p & ~g, g & ~p

    gt_por_fatia = np.count_nonzero(g, axis=(0, 1))
    pred_por_fatia = np.count_nonzero(p, axis=(0, 1))
    ambas = (gt_por_fatia > 0) & (pred_por_fatia > 0)

    # ---------------- EXTENSAO: erro em fatia onde a OUTRA mascara nao existe
    fp_por_fatia = np.count_nonzero(fp, axis=(0, 1))
    fn_por_fatia = np.count_nonzero(fn, axis=(0, 1))
    n_fp_long = int(fp_por_fatia[gt_por_fatia == 0].sum())
    n_fn_long = int(fn_por_fatia[pred_por_fatia == 0].sum())
    n_fp_lat = int(fp_por_fatia.sum()) - n_fp_long
    n_fn_lat = int(fn_por_fatia.sum()) - n_fn_long

    # ---------------- distancia radial ate a superficie da OUTRA mascara
    # FP -> voxel de GT mais proximo; FN -> voxel de predicao mais proximo. E a rede
    # de voxels, nao uma superficie interpolada: declarado, igual ao mapa_erro.
    if g.any():
        d_fp = distance_transform_edt(~g, sampling=spacing)[fp]
    else:
        d_fp = None
    if p.any():
        d_fn = distance_transform_edt(~p, sampling=spacing)[fn]
    else:
        d_fn = None
    partes = [x for x in (d_fp, d_fn) if x is not None and x.size]
    erro_mm = np.concatenate(partes) if partes else np.array([])

    # ---------------- LOCALIZACAO x DEFINICAO, fatia a fatia
    fatias: list[dict] = []
    deslocs: list[float] = []
    n_antes_total = n_apos_total = 0
    n_mais_estreita = n_mais_larga = n_igual = 0

    for i in np.flatnonzero(ambas):
        gi, pi = g[:, :, i], p[:, :, i]
        cg, cp = _centroide(gi), _centroide(pi)
        d0 = (cg[0] - cp[0]) * spacing[0]
        d1 = (cg[1] - cp[1]) * spacing[1]
        desloc = float(np.hypot(d0, d1))
        deslocs.append(desloc)

        s0, s1 = int(round(cg[0] - cp[0])), int(round(cg[1] - cp[1]))
        antes = int(np.count_nonzero(pi ^ gi))
        if s0 or s1:
            movida = _shift(pi.astype(np.uint8), (s0, s1), order=0,
                            mode="constant", cval=0) > 0
            apos = int(np.count_nonzero(movida ^ gi))
        else:
            apos = antes
        # a translacao nunca pode PIORAR a conta: se piorar, ela nao explica nada e a
        # localizacao daquela fatia e zero. Declarado, nao um max() escondido.
        apos = min(apos, antes)

        n_antes_total += antes
        n_apos_total += apos

        a_gt = float(gt_por_fatia[i]) * area_voxel_mm2
        a_pred = float(pred_por_fatia[i]) * area_voxel_mm2
        if pred_por_fatia[i] < gt_por_fatia[i]:
            n_mais_estreita += 1
        elif pred_por_fatia[i] > gt_por_fatia[i]:
            n_mais_larga += 1
        else:
            n_igual += 1

        fatias.append({
            "z": int(i) + int(offset[2]),
            "area_gt_mm2": a_gt, "area_pred_mm2": a_pred,
            "razao_pred_gt": a_pred / a_gt,
            "desloc_centroide_mm": desloc,
            "d_eixo0_mm": float(d0), "d_eixo1_mm": float(d1),
            "erro_lateral_antes_mL": _ml(antes, voxel_mm3),
            "erro_lateral_apos_translacao_mL": _ml(apos, voxel_mm3),
            "shift_voxels_eixo0": s0, "shift_voxels_eixo1": s1,
        })

    n_sobrep = int(np.count_nonzero(ambas))
    n_erro_total = int(np.count_nonzero(fp)) + int(np.count_nonzero(fn))
    n_extensao = n_fp_long + n_fn_long
    n_lateral = n_fp_lat + n_fn_lat
    n_local = max(n_antes_total - n_apos_total, 0)
    n_defin = n_apos_total

    # Prova interna: a soma por fatia do erro lateral TEM que fechar com o total
    # lateral contado por voxel. Sao dois caminhos independentes ate o mesmo numero.
    assert n_antes_total == n_lateral, (
        f"erro lateral por fatia ({n_antes_total}) != por voxel ({n_lateral}) — "
        "instrumento inconsistente")

    return {
        "spacing_mm": list(spacing),
        "voxel_mm3": voxel_mm3,
        "orientacao": orientacao,
        "volume_gt_mL": _ml(int(g.sum()), voxel_mm3),
        "volume_pred_mL": _ml(int(p.sum()), voxel_mm3),
        "erro_total_mL": _ml(n_erro_total, voxel_mm3),
        "FP_total_mL": _ml(int(np.count_nonzero(fp)), voxel_mm3),
        "FN_total_mL": _ml(int(np.count_nonzero(fn)), voxel_mm3),
        "extensao_mL": _ml(n_extensao, voxel_mm3),
        "FP_longitudinal_mL": _ml(n_fp_long, voxel_mm3),
        "FN_longitudinal_mL": _ml(n_fn_long, voxel_mm3),
        "lateral_mL": _ml(n_lateral, voxel_mm3),
        "FP_lateral_mL": _ml(n_fp_lat, voxel_mm3),
        "FN_lateral_mL": _ml(n_fn_lat, voxel_mm3),
        "localizacao_mL": _ml(n_local, voxel_mm3),
        "definicao_residual_mL": _ml(n_defin, voxel_mm3),
        "frac_extensao": _frac(n_extensao, n_erro_total, "erro vazio"),
        "frac_localizacao": _frac(n_local, n_erro_total, "erro vazio"),
        "frac_definicao_residual": _frac(n_defin, n_erro_total, "erro vazio"),
        "desloc_centroide_mm_mediana": _p(deslocs, 50),
        "desloc_centroide_mm_p95": _p(deslocs, 95),
        "desloc_centroide_mm_max": float(max(deslocs)) if deslocs else "invalido: sem fatia sobreposta",
        "dist_radial_FP_mm_mediana": _p(d_fp if d_fp is not None else [], 50),
        "dist_radial_FP_mm_p95": _p(d_fp if d_fp is not None else [], 95),
        "dist_radial_FN_mm_mediana": _p(d_fn if d_fn is not None else [], 50),
        "dist_radial_FN_mm_p95": _p(d_fn if d_fn is not None else [], 95),
        "espessura_erro_mm_mediana": _p(erro_mm, 50),
        "espessura_erro_mm_p95": _p(erro_mm, 95),
        "n_fatias_sobrepostas": n_sobrep,
        "frac_fatias_mais_estreita": _frac(n_mais_estreita, n_sobrep, "sem fatia sobreposta"),
        "frac_fatias_mais_larga": _frac(n_mais_larga, n_sobrep, "sem fatia sobreposta"),
        "frac_fatias_igual": _frac(n_igual, n_sobrep, "sem fatia sobreposta"),
        "fatias": fatias,
    }


# ---------------------------------------------------------------------- execucao


def rodar_caso(caso: str, raiz: Path = RAIZ_PADRAO, estruturas=("Esophagus",),
               log=print) -> list[dict]:
    """Decompoe o erro das estruturas pedidas de UM caso. Uma linha por estrutura."""
    destino = Path(raiz) / caso
    manifesto = json.loads((destino / "manifesto.json").read_text(encoding="utf-8"))
    dir_gt, dir_pred = destino / "gt", destino / "pred_masks"
    rois = list(manifesto["rois_encontradas"])
    dz = float(manifesto["spacing_mm"][2])
    linhas = []

    for alvo in estruturas:
        gt_roi = next((r for r in rois if mapeamento.canonizar(r) == alvo), None)
        base = {c: None for c in COLUNAS}
        base.update(case_id=manifesto["case_id"], instituicao=fase5.instituicao_de(caso),
                    structure=alvo, dz_mm=dz, erro="")
        if gt_roi is None:
            base["erro"] = f"ABORTADA: {alvo} ausente das ROIs do caso"
            linhas.append({**base, "_fatias": []})
            log(f"  {caso}/{alvo}: ausente")
            continue

        alvos_ts = mapeamento.MAPA_LCTSC[alvo]
        caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{gt_roi}.nii.gz"
        caminhos_pred = [dir_pred / f"{n}.nii.gz" for n in alvos_ts]

        # Parte K ANTES de qualquer medida: grade divergente aborta a estrutura.
        try:
            alinhamento = [geometria.verificar_alinhamento(c, caminho_gt) for c in caminhos_pred]
        except geometria.DesalinhamentoGeometrico as e:
            base["erro"] = f"ABORTADA: {e}"
            linhas.append({**base, "_fatias": []})
            log(f"  {caso}/{alvo}: ABORTADA — {e}")
            continue

        geo_gt = geometria.descrever_nifti(caminho_gt)
        spacing = tuple(geo_gt["zooms_mm"])
        gt = rtst.carregar_mascara(caminho_gt)
        pred, _ = mapeamento.unir_predicao(dir_pred, alvos_ts)

        d = decompor(pred, gt, spacing, geo_gt["orientacao"])
        # Contexto ja estabelecido na fase 5, reaproveitado em vez de reimplementado.
        m = diag.medir(pred, gt, spacing, geo_gt["orientacao"])

        base.update({k: d[k] for k in (
            "volume_gt_mL", "volume_pred_mL", "erro_total_mL", "FP_total_mL", "FN_total_mL",
            "extensao_mL", "FP_longitudinal_mL", "FN_longitudinal_mL",
            "lateral_mL", "FP_lateral_mL", "FN_lateral_mL",
            "localizacao_mL", "definicao_residual_mL",
            "frac_extensao", "frac_localizacao", "frac_definicao_residual",
            "desloc_centroide_mm_mediana", "desloc_centroide_mm_p95", "desloc_centroide_mm_max",
            "dist_radial_FP_mm_mediana", "dist_radial_FP_mm_p95",
            "dist_radial_FN_mm_mediana", "dist_radial_FN_mm_p95",
            "espessura_erro_mm_mediana", "espessura_erro_mm_p95",
            "n_fatias_sobrepostas",
            "frac_fatias_mais_estreita", "frac_fatias_mais_larga", "frac_fatias_igual")})
        base.update(
            spacing_mm=[round(s, 6) for s in spacing], orientacao=geo_gt["orientacao"],
            razao_area_mediana=m["razao_area_mediana"],
            razao_area_p5=m["razao_area_p5"], razao_area_p95=m["razao_area_p95"],
            comprimento_gt_mm=m["comprimento_gt_mm"],
            comprimento_pred_mm=m["comprimento_pred_mm"],
            diferenca_comprimento_mm=m["diferenca_comprimento_mm"],
            frac_campo_gt=m["frac_campo_gt"], frac_campo_pred=m["frac_campo_pred"],
            n_fatias_gt=m["extensao_z_gt"]["n_fatias"],
            n_fatias_pred=m["extensao_z_pred"]["n_fatias"],
            alinhamento="; ".join(a["veredito"] for a in alinhamento),
        )
        # Duas implementacoes independentes do MESMO numero (FP fora do suporte do
        # GT): a da fase 5 e a daqui. Divergencia != 0 e defeito de instrumento.
        base["conferencia_FP_extensao_delta_mL"] = round(
            d["FP_longitudinal_mL"] - m["FP_extensao_mL"], 9)
        r = base["razao_area_mediana"]
        base["sentido_do_caso"] = (
            "pred_mais_larga" if isinstance(r, float) and r > 1
            else "pred_mais_estreita" if isinstance(r, float) and r < 1
            else NA)

        for f in d["fatias"]:
            f.update(case_id=base["case_id"], instituicao=base["instituicao"],
                     structure=alvo)
        linhas.append({**base, "_fatias": d["fatias"]})
        log(f"  {caso}/{alvo}: erro {d['erro_total_mL']:.3f} mL -> "
            f"ext {d['frac_extensao']:.3f} / loc {d['frac_localizacao']:.3f} / "
            f"def {d['frac_definicao_residual']:.3f}")
    return linhas


def _validas(linhas, estrutura):
    return [l for l in linhas if l["structure"] == estrutura and not l["erro"]
            and isinstance(l["erro_total_mL"], float) and l["erro_total_mL"] > 0]


def _num(linhas, chave):
    return [l[chave] for l in linhas if isinstance(l.get(chave), (int, float))]


def _resumo(v):
    a = np.asarray(v, dtype=float)
    if not a.size:
        return {"n": 0, "mediana": NM, "p5": NM, "p95": NM, "min": NM, "max": NM}
    return {"n": int(a.size), "mediana": float(np.median(a)),
            "p5": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95)),
            "min": float(a.min()), "max": float(a.max())}


def _consistencia(linhas: list[dict]) -> dict:
    """O TESTE QUE SEPARA DEFINICAO DE ERRO, aplicado INTRA-instituicao.

    Regra declarada (limiares no topo do modulo, nenhum escolhido apos ver o resultado
    do ALVO): a razao de area de cada caso aponta para um lado; se >= 90 % dos casos da
    instituicao apontam para o MESMO lado e a translacao NAO explica o erro, o residuo
    e COMPATIVEL COM convencao de contorno. Se o sentido oscila, e erro de fronteira do
    modelo. Se a translacao explica o erro (frac_localizacao mediana > 0,50), o teste
    nao se aplica — ali o regime e localizacao.

    O gate e `frac_localizacao`, adimensional, e NAO o deslocamento do centroide em mm:
    ver o DEFEITO CONHECIDO documentado em LIMIAR_CENTROIDE_ALINHADO_MM. O criterio em
    mm continua calculado e reportado, para que a divergencia entre os dois fique
    visivel em vez de escondida.
    """
    saida = {}
    for inst in sorted({l["instituicao"] for l in linhas}):
        do_inst = [l for l in linhas if l["instituicao"] == inst]
        largas = sum(1 for l in do_inst if l["sentido_do_caso"] == "pred_mais_larga")
        estreitas = sum(1 for l in do_inst if l["sentido_do_caso"] == "pred_mais_estreita")
        empates = len(do_inst) - largas - estreitas
        n = largas + estreitas
        frac_mesmo = _frac(max(largas, estreitas), n, "nenhum caso com sentido definido")
        # Empate (razao de area exatamente 1) nao aponta lado nenhum. Reportado nos dois
        # denominadores para o veredito nao depender dessa convencao sem que se veja.
        frac_mesmo_com_empate = _frac(max(largas, estreitas), len(do_inst), "instituicao vazia")
        desloc = _num(do_inst, "desloc_centroide_mm_mediana")
        desloc_med = float(np.median(desloc)) if desloc else None
        alinhado = desloc_med is not None and desloc_med <= LIMIAR_CENTROIDE_ALINHADO_MM
        loc = _num(do_inst, "frac_localizacao")
        loc_med = float(np.median(loc)) if loc else None
        translacao_explica = loc_med is not None and loc_med > LIMIAR_DOMINANCIA
        consistente = isinstance(frac_mesmo, float) and frac_mesmo >= LIMIAR_CONSISTENCIA_CASOS

        if translacao_explica:
            assinatura = ("a translacao explica o erro — regime de LOCALIZACAO, "
                          "teste de convencao nao aplicavel")
        elif consistente:
            assinatura = ("centroide nao explica o erro e o sentido e consistente — "
                          "COMPATIVEL COM convencao de contorno")
        else:
            assinatura = ("centroide nao explica o erro e o sentido OSCILA — compativel "
                          "com erro de fronteira do modelo, nao com convencao")

        saida[inst] = {
            "n_casos": len(do_inst),
            "n_pred_mais_larga": largas, "n_pred_mais_estreita": estreitas,
            "n_empate_razao_area_1": empates,
            "frac_casos_mesmo_sentido": frac_mesmo,
            "frac_casos_mesmo_sentido_com_empate_no_denominador": frac_mesmo_com_empate,
            "sentido_dominante": ("pred_mais_larga" if largas > estreitas
                                  else "pred_mais_estreita" if estreitas > largas else "empate"),
            "razao_area_mediana": _resumo(_num(do_inst, "razao_area_mediana")),
            "frac_fatias_mais_estreita": _resumo(_num(do_inst, "frac_fatias_mais_estreita")),
            "desloc_centroide_mm_mediana_dos_casos": desloc_med if desloc_med is not None else NM,
            "frac_localizacao_mediana_dos_casos": loc_med if loc_med is not None else NM,
            "centroide_alinhado_criterio_mm": alinhado,
            "translacao_explica_o_erro": translacao_explica,
            "criterios_mm_e_translacao_divergem": bool(alinhado == translacao_explica),
            "sentido_consistente": consistente,
            "assinatura": assinatura,
            "fracoes": {k: _resumo(_num(do_inst, k)) for k in
                        ("frac_extensao", "frac_localizacao", "frac_definicao_residual")},
        }
    return saida


def agregar(linhas: list[dict], estrutura: str) -> dict:
    v = _validas(linhas, estrutura)
    if not v:
        return {"estrutura": estrutura, "n_casos": 0, "erro": "nenhum caso valido"}

    total = sum(l["erro_total_mL"] for l in v)
    pooled = {k: _frac(sum(l[m] for l in v), total, "erro total zero")
              for k, m in (("extensao", "extensao_mL"),
                           ("localizacao", "localizacao_mL"),
                           ("definicao_residual", "definicao_residual_mL"))}

    por_dz: dict[str, dict] = {}
    for dz in sorted({round(l["dz_mm"], 3) for l in v}):
        do_dz = [l for l in v if round(l["dz_mm"], 3) == dz]
        t = sum(l["erro_total_mL"] for l in do_dz)
        por_dz[f"{dz:g}"] = {
            "n_casos": len(do_dz),
            "instituicoes": sorted({l["instituicao"] for l in do_dz}),
            "erro_total_mL": t,
            "frac_extensao": _frac(sum(l["extensao_mL"] for l in do_dz), t, "erro zero"),
            "frac_localizacao": _frac(sum(l["localizacao_mL"] for l in do_dz), t, "erro zero"),
            "frac_definicao_residual": _frac(
                sum(l["definicao_residual_mL"] for l in do_dz), t, "erro zero"),
            "desloc_centroide_mm_mediana": _resumo(_num(do_dz, "desloc_centroide_mm_mediana")),
            "razao_area_mediana": _resumo(_num(do_dz, "razao_area_mediana")),
        }

    conf = _num(v, "conferencia_FP_extensao_delta_mL")
    return {
        "estrutura": estrutura,
        "n_casos": len(v),
        "erro_total_somado_mL": total,
        "fracao_do_erro_pooled": pooled,
        "fracao_do_erro_por_caso": {
            k: _resumo(_num(v, f"frac_{k}"))
            for k in ("extensao", "localizacao", "definicao_residual")},
        "distribuicoes": {k: _resumo(_num(v, k)) for k in (
            "erro_total_mL", "desloc_centroide_mm_mediana", "desloc_centroide_mm_p95",
            "dist_radial_FP_mm_mediana", "dist_radial_FP_mm_p95",
            "dist_radial_FN_mm_mediana", "dist_radial_FN_mm_p95",
            "espessura_erro_mm_mediana", "espessura_erro_mm_p95",
            "razao_area_mediana", "razao_area_p5", "razao_area_p95",
            "frac_fatias_mais_estreita", "frac_fatias_mais_larga",
            "diferenca_comprimento_mm", "frac_campo_gt", "frac_campo_pred")},
        "por_instituicao": _consistencia(v),
        "por_dz": por_dz,
        "conferencia_FP_extensao_delta_mL_max": (float(np.abs(conf).max()) if conf else NM),
    }


def rodar(raiz: Path = RAIZ_PADRAO, casos=None, estruturas=("Esophagus",), log=print) -> dict:
    split = fase5.carregar_split(raiz)
    alvos = list(casos) if casos else list(split[SPLIT_USADO])
    if not casos:
        proibidos = set(split["validation"]) | set(split["test"])
        assert not (set(alvos) & proibidos), "caso de validation/test entrou na lista"

    linhas, fatias = [], []
    for caso in alvos:
        log(caso)
        for l in rodar_caso(caso, raiz=raiz, estruturas=estruturas, log=log):
            fatias.extend(l.pop("_fatias"))
            linhas.append(l)

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split_usado": SPLIT_USADO,
        "n_casos": len(alvos),
        "casos": alvos,
        "estruturas": list(estruturas),
        "limiares": {
            "centroide_alinhado_mm": LIMIAR_CENTROIDE_ALINHADO_MM,
            "consistencia_casos": LIMIAR_CONSISTENCIA_CASOS,
            "dominancia": LIMIAR_DOMINANCIA,
            "declarados_antes_da_execucao": True,
        },
        "ceiling_declarado": (
            "a translacao e pelo CENTROIDE, nao a otima: subestima localizacao e "
            "superestima definicao_residual"
        ),
        "agregados": {e: agregar(linhas, e) for e in estruturas},
        "linhas": linhas,
        "fatias": fatias,
    }


# ----------------------------------------------------------------------- saida


def _f(v, casas=4) -> str:
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    if isinstance(v, int):
        return str(v)
    return str(v)


def _summary_md(r: dict) -> str:
    L = [
        "# Fase 6 — discordancia anatomica do esofago (Partes 3 e 4)",
        "",
        f"Gerado em {r['gerado_em']}. Split `{r['split_usado']}`, n={r['n_casos']} casos. "
        f"`validation` e `test` nao foram lidos.",
        "",
        "Decomposicao do volume de erro (FP+FN) em tres regimes mutuamente exclusivos: "
        "**extensao** (erro em fatia onde a outra mascara nao existe), **localizacao** "
        "(erro lateral removido por uma translacao por fatia, do centroide da predicao "
        "para o do GT) e **definicao_residual** (o erro lateral que sobra).",
        "",
        f"> Ceiling declarado: {r['ceiling_declarado']}.",
        "",
        "> `definicao_residual` nao PROVA definicao. So o teste de consistencia "
        "INTRA-instituicao decide se ela e compativel com convencao de contorno ou com "
        "erro de fronteira do modelo.",
        "",
    ]
    for est, a in r["agregados"].items():
        L += [f"## {est}", ""]
        if a.get("erro"):
            L += [f"{a['erro']}", ""]
            continue
        p = a["fracao_do_erro_pooled"]
        L += [
            f"n={a['n_casos']} casos com erro > 0. Erro somado "
            f"{_f(a['erro_total_somado_mL'], 3)} mL.",
            "",
            "### Fracao do erro, agregada (pooled: mL somado / mL somado)",
            "",
            "| regime | fracao pooled | mediana por caso | P5 | P95 |",
            "|---|---|---|---|---|",
        ]
        for k, rot in (("extensao", "extensao"), ("localizacao", "localizacao"),
                       ("definicao_residual", "definicao_residual")):
            c = a["fracao_do_erro_por_caso"][k]
            L.append(f"| {rot} | {_f(p[k])} | {_f(c['mediana'])} | {_f(c['p5'])} "
                     f"| {_f(c['p95'])} |")
        L += ["", "### Distribuicoes por caso", "",
              "| medida | mediana | P5 | P95 | min | max |", "|---|---|---|---|---|---|"]
        for k, d in a["distribuicoes"].items():
            L.append(f"| {k} | {_f(d['mediana'])} | {_f(d['p5'])} | {_f(d['p95'])} "
                     f"| {_f(d['min'])} | {_f(d['max'])} |")
        L += ["", "### Consistencia INTRA-instituicao (o teste que separa)", "",
              "| inst | n | larga | estreita | empate | frac mesmo sentido | idem com "
              "empate no denominador | razao area (mediana) | desloc centroide mm "
              "| frac localizacao | assinatura |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for inst, c in a["por_instituicao"].items():
            L.append(
                f"| {inst} | {c['n_casos']} | {c['n_pred_mais_larga']} "
                f"| {c['n_pred_mais_estreita']} | {c['n_empate_razao_area_1']} "
                f"| {_f(c['frac_casos_mesmo_sentido'])} "
                f"| {_f(c['frac_casos_mesmo_sentido_com_empate_no_denominador'])} "
                f"| {_f(c['razao_area_mediana']['mediana'])} "
                f"| {_f(c['desloc_centroide_mm_mediana_dos_casos'], 3)} "
                f"| {_f(c['frac_localizacao_mediana_dos_casos'])} "
                f"| {c['assinatura']} |")
        divergem = [i for i, c in a["por_instituicao"].items()
                    if c["criterios_mm_e_translacao_divergem"]]
        if divergem:
            L += ["", f"> Criterio em mm e criterio de translacao DIVERGEM em: "
                      f"{', '.join(divergem)}. Quem decide e a translacao (adimensional); "
                      f"o mm fica reportado. Ver LIMIAR_CENTROIDE_ALINHADO_MM no modulo."]
        L += ["", "### Estratificacao por spacing em Z", "",
              "| dz (mm) | n | instituicoes | frac extensao | frac localizacao "
              "| frac definicao_residual | desloc centroide mm (mediana) |",
              "|---|---|---|---|---|---|---|"]
        for dz, d in a["por_dz"].items():
            L.append(f"| {dz} | {d['n_casos']} | {', '.join(d['instituicoes'])} "
                     f"| {_f(d['frac_extensao'])} | {_f(d['frac_localizacao'])} "
                     f"| {_f(d['frac_definicao_residual'])} "
                     f"| {_f(d['desloc_centroide_mm_mediana']['mediana'], 3)} |")
        L += ["",
              f"Conferencia interna FP_extensao (esta medida contra a da fase 5), maior "
              f"divergencia absoluta: {_f(a['conferencia_FP_extensao_delta_mL_max'], 9)} mL.",
              ""]
    return "\n".join(L) + "\n"


def gravar(r: dict, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)

    p_csv = saida / "discordancia_esofago.csv"
    with p_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(r["linhas"])

    p_fatias = saida / "fatias.csv"
    with p_fatias.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_FATIA, extrasaction="ignore")
        w.writeheader()
        w.writerows(r["fatias"])

    p_json = saida / "discordancia_esofago.json"
    p_json.write_text(json.dumps({k: v for k, v in r.items() if k != "fatias"},
                                 indent=2, ensure_ascii=False), encoding="utf-8")
    p_md = saida / "summary.md"
    p_md.write_text(_summary_md(r), encoding="utf-8")

    for p in (p_csv, p_fatias, p_json, p_md):
        log(f"gravado: {p}")
    return {"csv": p_csv, "csv_fatias": p_fatias, "json": p_json, "summary": p_md}


# -------------------------------------------------------------------- autoteste


def _autoteste() -> None:
    """Controle POSITIVO: o instrumento tem que SEPARAR os tres regimes.

    Tres predicoes sinteticas construidas a partir do MESMO GT, cada uma com um unico
    defeito conhecido. Cada assert diz o que TEM que dar alto E o que TEM que dar
    ~zero — um instrumento que devolvesse sempre o mesmo rotulo passaria numa
    verificacao so de "deu alto", entao a exigencia e de SEPARACAO.
    """
    from scipy.ndimage import binary_erosion

    spacing = (0.98, 0.98, 3.0)
    gt = diag._tubo()  # tubo de raio 4, fatias 10..49

    # 0) controle NEGATIVO: predicao identica ao GT nao tem erro para repartir
    igual = decompor(gt, gt, spacing, "LPS")
    assert igual["erro_total_mL"] == 0.0, igual["erro_total_mL"]
    assert isinstance(igual["frac_extensao"], str), igual["frac_extensao"]

    # 1) DESLOCADA no plano: 3 voxels no eixo 0 = 2,94 mm. Mesmo Z, mesma area.
    deslocada = np.roll(gt, 3, axis=0)
    d = decompor(deslocada, gt, spacing, "LPS")
    assert d["frac_localizacao"] > AUTOTESTE_MIN_DOMINANTE, d["frac_localizacao"]
    assert d["frac_extensao"] < AUTOTESTE_MAX_OUTROS, d["frac_extensao"]
    assert d["frac_definicao_residual"] < AUTOTESTE_MAX_OUTROS, d["frac_definicao_residual"]
    assert abs(d["desloc_centroide_mm_mediana"] - 3 * 0.98) < 1e-6, d["desloc_centroide_mm_mediana"]
    assert d["desloc_centroide_mm_mediana"] > LIMIAR_CENTROIDE_ALINHADO_MM, d

    # 2) ERODIDA no plano (elemento 3x3x1: nao encurta em Z): so espessura muda.
    erodida = binary_erosion(gt, structure=np.ones((3, 3, 1), dtype=bool))
    e = decompor(erodida, gt, spacing, "LPS")
    assert e["frac_definicao_residual"] > AUTOTESTE_MIN_DOMINANTE, e["frac_definicao_residual"]
    assert e["frac_extensao"] < AUTOTESTE_MAX_OUTROS, e["frac_extensao"]
    assert e["frac_localizacao"] < AUTOTESTE_MAX_OUTROS, e["frac_localizacao"]
    assert e["desloc_centroide_mm_mediana"] <= LIMIAR_CENTROIDE_ALINHADO_MM, e
    assert e["frac_fatias_mais_estreita"] == 1.0, e["frac_fatias_mais_estreita"]

    # 3) ESTENDIDA em Z: 10 fatias copiadas alem da ponta z_max do GT.
    estendida = gt.copy()
    estendida[:, :, 50:60] = gt[:, :, 49][:, :, None]
    x = decompor(estendida, gt, spacing, "LPS")
    assert x["frac_extensao"] > AUTOTESTE_MIN_DOMINANTE, x["frac_extensao"]
    assert x["frac_localizacao"] < AUTOTESTE_MAX_OUTROS, x["frac_localizacao"]
    assert x["frac_definicao_residual"] < AUTOTESTE_MAX_OUTROS, x["frac_definicao_residual"]
    assert x["FP_longitudinal_mL"] > 0 and x["FP_lateral_mL"] == 0.0, x

    # SEPARACAO: cada controle tem que eleger um regime DIFERENTE.
    eleito = {nome: max(("extensao", "localizacao", "definicao_residual"),
                        key=lambda k: m[f"frac_{k}"])
              for nome, m in (("deslocada", d), ("erodida", e), ("estendida", x))}
    assert eleito == {"deslocada": "localizacao", "erodida": "definicao_residual",
                      "estendida": "extensao"}, eleito

    # 4) o teste de consistencia tem que ver o SENTIDO, nao so a mediana: uma
    #    instituicao com sentido oscilante NAO pode sair como convencao.
    def _linha(inst, razao, desloc, floc=0.0):
        return {"instituicao": inst, "structure": "X", "erro": "", "erro_total_mL": 1.0,
                "razao_area_mediana": razao, "desloc_centroide_mm_mediana": desloc,
                "frac_fatias_mais_estreita": 1.0 if razao < 1 else 0.0,
                "sentido_do_caso": "pred_mais_estreita" if razao < 1 else "pred_mais_larga",
                "frac_extensao": 0.0, "frac_localizacao": floc,
                "frac_definicao_residual": 1.0 - floc}

    coerente = [_linha("SA", 0.9, 0.5) for _ in range(10)]
    oscilante = [_linha("SB", 0.9 if i % 2 else 1.1, 0.5) for i in range(10)]
    transladada = [_linha("SC", 0.9, 9.0, floc=0.9) for _ in range(10)]
    # REGRESSAO do defeito achado pelo contraste `Heart`: centroide LONGE em mm mas a
    # translacao nao explica nada. Nao pode sair como localizacao.
    envelope = [_linha("SD", 0.74, 4.8, floc=0.01) for _ in range(10)]
    c = _consistencia(coerente + oscilante + transladada + envelope)
    assert "COMPATIVEL COM convencao" in c["SA"]["assinatura"], c["SA"]
    assert "OSCILA" in c["SB"]["assinatura"], c["SB"]
    assert "LOCALIZACAO" in c["SC"]["assinatura"], c["SC"]
    assert "LOCALIZACAO" not in c["SD"]["assinatura"], c["SD"]
    assert "COMPATIVEL COM convencao" in c["SD"]["assinatura"], c["SD"]
    assert c["SD"]["criterios_mm_e_translacao_divergem"], c["SD"]
    # ambos com mediana ~0,9-1,0: se o teste olhasse so a mediana, SA e SB sairiam iguais
    assert c["SA"]["sentido_consistente"] and not c["SB"]["sentido_consistente"], c

    print("discordancia_esofago.py: autoteste OK — os tres regimes se separam")


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    ap.add_argument("--caso", action="append", help="limita a estes casos (default: development)")
    ap.add_argument("--estrutura", action="append",
                    help="default: Esophagus. Outras servem de CONTRASTE do instrumento.")
    a = ap.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0
    r = rodar(raiz=a.raiz, casos=a.caso, estruturas=tuple(a.estrutura or ("Esophagus",)))
    gravar(r, saida=a.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
