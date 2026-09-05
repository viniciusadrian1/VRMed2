"""Partes 5 e 6 — o erro da medula e do esofago e de LIMITE ou de EXTENSAO?

A pergunta que decide o remedio: o modelo desenha a estrutura ERRADA (fronteira
deslocada / mais estreita) ou a estrutura CERTA por uma EXTENSAO maior em Z?
Sao remedios opostos — regra de terminacao contra operacao morfologica — e
escolher um antes de medir e adivinhar.

Este modulo so MEDE. Ele nao propoe regra, nao altera predicao, nao grava
mascara nenhuma.

------------------------------------------------------------------------------
USO DO GROUND TRUTH — a distincao que este arquivo respeita

Aqui o GT entra em TODA medida: FP_extensao e definido por "fatia onde o GT nao
tem voxel", o comprimento comparado e o do GT, a razao de area e contra a area
do GT. Isso e PERMITIDO e e o proposito do arquivo: o GT esta AVALIANDO.

O que seria proibido, e que este arquivo nao faz em lugar nenhum: usar o GT para
CONSTRUIR a predicao — cortar a predicao no alcance do GT, calcular `pred & gt`,
ou tirar do GT o valor de uma constante que depois iria para uma regra de
pos-processamento. Nenhuma medida daqui pode virar regra por copia: se a
resposta for "e extensao", a regra de terminacao que vier depois tera que
derivar o ponto de corte de algo observavel SEM GT (a imagem, a anatomia, a
propria predicao), e essa derivacao sera declarada no experimento dela, nao
aqui.

As unicas constantes deste modulo (CAMADA_FINA_VOX e os tres limiares de
ROTULAGEM) vem da grade de voxel e de convencao de redacao, nunca do GT.
------------------------------------------------------------------------------

O QUE E MEDIDO, por caso do `development` e por estrutura alvo:

  FP_total_mL / FN_total_mL
  FP_extensao_mL   FP em fatias Z onde o GT nao tem voxel nenhum
  FP_lateral_mL    FP em fatias Z onde o GT TEM voxel (fronteira, nao extensao)
                   FP_extensao + FP_lateral == FP_total, por construcao
  FP_extensao_{distal,proximal,interna}_mL — a extensao repartida entre as duas
                   pontas do suporte do GT e os buracos internos dele
  FN_fino_mL       FN a <= CAMADA_FINA_VOX voxel da superficie da predicao
  FN_bloco_mL      FN mais fundo que isso
  erro_distal_mm / erro_proximal_mm — o que SOBRA da predicao em cada ponta,
                   com sinal: positivo = a predicao passa alem do GT
  comprimento_{gt,pred}_mm e a diferenca
  area transversal por fatia (mm2) de GT e predicao, a razao pred/GT
                   (mediana, P5, P95) e a fracao de fatias em que a predicao e
                   MAIS ESTREITA que o GT

DISTAL / PROXIMAL nao sao presumidos: saem do codigo de eixo do NIfTI
(`nib.aff2axcodes`). Com eixo 2 = S, o indice cresce em direcao cranial, entao a
ponta z_max e a PROXIMAL (cranial — origem da medula e do esofago) e a z_min e a
DISTAL (caudal). Com eixo 2 = I, invertido. Com qualquer outro codigo os nomes
anatomicos NAO sao aplicados e as pontas saem como z_min / z_max.

COMPRIMENTO aqui e extensao do SUPORTE em Z ((z_max - z_min + 1) * dz), nao
comprimento de arco de uma estrutura curva. Declarado porque uma medula com
inclinacao lateral tem arco maior que a extensao em Z.

TIER: diagnostico do bloco A (segmentacao). Uso educacional/experimental —
"caso" e "estrutura", nunca "paciente".

  python -m scripts.validation.tier2.diagnostico_longitudinal --autoteste
  python -m scripts.validation.tier2.diagnostico_longitudinal
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_cdt

from . import fase5, geometria, mapeamento
from . import rtstruct as rtst
from .mapa_erro import _frac, _ml, _p, _recorte, _suporte_z

RAIZ_PADRAO = fase5.RAIZ
SAIDA_PADRAO = RAIZ_PADRAO / "fase5" / "diagnostico"
SPLIT_USADO = "development"  # o `test` e intocavel nesta fase; o `validation` so na confirmacao

NA = "nao aplicavel"

# --------------------------------------------------------------------- constantes
# Nenhuma delas vem do GT. Origem declarada em cada linha.

# Espessura de "casca". Vem da GRADE: camada 1 (chessboard) = voxel que encosta
# na predicao. Em grade anisotropica (0,98 x 0,98 x 3,0 mm) um limiar unico em
# mm chamaria o mesmo primeiro anel de fino num eixo e espesso no outro — por
# isso a contagem e em VOXELS, igual ao `mapa_erro`.
CAMADA_FINA_VOX = 1

# Limiares de ROTULAGEM do texto do summary. Nao decidem intervencao nenhuma e
# nao entram em nenhuma regra: existem so para a frase do relatorio nao ser
# escrita depois de olhar o numero. Declarados antes da primeira execucao.
LIMIAR_CONCENTRACAO = 2.0        # uma ponta com >= 2x o volume da outra = "concentrada"
LIMIAR_SISTEMATICO_FRAC = 0.90   # >= 90 % das fatias mais estreitas = "sistematico"
LIMIAR_AMPLITUDE_INSTITUICAO = 0.10  # amplitude de fracao entre S1/S2/S3 = "muda"

COLUNAS = (
    "dataset", "case_id", "instituicao", "structure", "gt_roi_name",
    "spacing_mm", "orientacao", "eixo_z", "pontas_anatomicas",
    "volume_gt_mL", "volume_pred_mL",
    "FP_total_mL", "FN_total_mL",
    "FP_extensao_mL", "FP_lateral_mL", "frac_FP_extensao",
    "FP_extensao_distal_mL", "FP_extensao_proximal_mL", "FP_extensao_interna_mL",
    "FN_fino_mL", "FN_bloco_mL", "frac_FN_fino",
    "erro_distal_mm", "erro_proximal_mm",
    "comprimento_gt_mm", "comprimento_pred_mm", "diferenca_comprimento_mm",
    "campo_z_mm", "frac_campo_gt", "frac_campo_pred",
    "n_fatias_gt", "n_fatias_pred", "n_fatias_sobrepostas",
    "area_gt_mediana_mm2", "area_pred_mediana_mm2",
    "razao_area_mediana", "razao_area_p5", "razao_area_p95",
    "frac_fatias_mais_estreita",
    "alinhamento", "erro",
)

COLUNAS_FATIA = (
    "case_id", "instituicao", "structure", "z", "z_relativo_ao_gt",
    "area_gt_mm2", "area_pred_mm2", "razao_pred_gt", "categoria",
)


# ------------------------------------------------------------------------ nucleo


def _nomes_das_pontas(orientacao: str) -> tuple[str, str, bool]:
    """(nome da ponta z_min, nome da ponta z_max, nomes sao anatomicos?).

    Derivado do codigo de eixo do NIfTI, nunca presumido.
    """
    eixo = orientacao[2] if len(orientacao) >= 3 else "?"
    if eixo == "S":       # indice cresce para cranial
        return ("distal", "proximal", True)
    if eixo == "I":       # indice cresce para caudal
        return ("proximal", "distal", True)
    return ("ponta_z_min", "ponta_z_max", False)


def medir(pred: np.ndarray, gt: np.ndarray, spacing, orientacao: str = "???") -> dict:
    """Todas as medidas de UM par (predicao, GT) ja alinhado. Nucleo puro, sem IO.

    E esta funcao que o autoteste exercita com controles positivos.
    """
    pred = np.asarray(pred) > 0.5
    gt = np.asarray(gt) > 0.5
    spacing = tuple(float(s) for s in spacing)
    dz = spacing[2]
    area_voxel_mm2 = spacing[0] * spacing[1]
    voxel_mm3 = area_voxel_mm2 * dz

    # Recorte de custo: contem GT + predicao + 2 voxels de fundo. Como ele contem
    # TODA a predicao, a distancia ate a predicao calculada dentro dele e exata.
    cortes, offset = _recorte(pred, gt)
    p, g = pred[cortes], gt[cortes]
    fp = p & ~g
    fn = g & ~p

    # ---------------- FN: casca fina contra bloco
    # distance_transform_cdt(~p) = para cada voxel FORA da predicao, a distancia
    # de chessboard ate o voxel de predicao mais proximo. FN esta sempre fora da
    # predicao, entao camada >= 1; camada == 1 e o FN que ENCOSTA na predicao.
    n_fn = int(np.count_nonzero(fn))
    if p.any():
        camada_ate_pred = distance_transform_cdt(~p, metric="chessboard")
        n_fn_fino = int(np.count_nonzero(fn & (camada_ate_pred <= CAMADA_FINA_VOX)))
    else:
        # sem predicao nao existe superficie de predicao para medir distancia
        camada_ate_pred = None
        n_fn_fino = 0
    n_fn_bloco = n_fn - n_fn_fino

    # ---------------- FP: extensao contra fronteira, por fatia Z
    gt_por_fatia = np.count_nonzero(g, axis=(0, 1))
    pred_por_fatia = np.count_nonzero(p, axis=(0, 1))
    fp_por_fatia = np.count_nonzero(fp, axis=(0, 1))
    z_orig = np.arange(gt_por_fatia.size) + int(offset[2])

    z0g, z1g, n_fatias_gt = _suporte_z(gt)
    z0p, z1p, n_fatias_pred = _suporte_z(pred)

    sem_gt = gt_por_fatia == 0
    n_fp = int(np.count_nonzero(fp))
    n_fp_extensao = int(fp_por_fatia[sem_gt].sum())
    n_fp_lateral = n_fp - n_fp_extensao

    if n_fatias_gt:
        antes = sem_gt & (z_orig < z0g)      # ponta z_min
        depois = sem_gt & (z_orig > z1g)     # ponta z_max
        n_fp_zmin = int(fp_por_fatia[antes].sum())
        n_fp_zmax = int(fp_por_fatia[depois].sum())
        n_fp_interna = n_fp_extensao - n_fp_zmin - n_fp_zmax
    else:
        n_fp_zmin = n_fp_zmax = n_fp_interna = None

    # ---------------- pontas em mm (sinal: positivo = a predicao passa alem do GT)
    nome_zmin, nome_zmax, anatomico = _nomes_das_pontas(orientacao)
    if n_fatias_gt and n_fatias_pred:
        sobra_zmin_mm = float((z0g - z0p) * dz)
        sobra_zmax_mm = float((z1p - z1g) * dz)
        pontas = {nome_zmin: sobra_zmin_mm, nome_zmax: sobra_zmax_mm}
        vol_ponta = {nome_zmin: _ml(n_fp_zmin, voxel_mm3),
                     nome_zmax: _ml(n_fp_zmax, voxel_mm3)}
    else:
        pontas = {nome_zmin: f"invalido: {'GT' if not n_fatias_gt else 'predicao'} vazia em Z",
                  nome_zmax: f"invalido: {'GT' if not n_fatias_gt else 'predicao'} vazia em Z"}
        vol_ponta = {nome_zmin: "invalido: GT vazio em Z", nome_zmax: "invalido: GT vazio em Z"}

    comp_gt = float((z1g - z0g + 1) * dz) if n_fatias_gt else "invalido: GT vazio em Z"
    comp_pred = float((z1p - z0p + 1) * dz) if n_fatias_pred else "invalido: predicao vazia em Z"
    dif_comp = (comp_pred - comp_gt if isinstance(comp_gt, float) and isinstance(comp_pred, float)
                else "invalido: suporte em Z vazio")

    # CONTROLE DE CONFUSAO — sem ele a resposta (d) e lida ao contrario.
    # "extensao indevida" (E1) e "o contornador parou antes" (E6) produzem o MESMO
    # FP_extensao. O que as separa e o campo de visao: se a predicao vai de ponta a
    # ponta do volume, ela nao escolheu onde terminar — ela preencheu o campo, e o
    # que sobra e a fracao do campo que o GT cobre. O campo sai do SHAPE do array,
    # nao do GT.
    campo_z_mm = float(gt.shape[2] * dz)

    # ---------------- area transversal por fatia
    ambos = (gt_por_fatia > 0) & (pred_por_fatia > 0)
    razoes = (pred_por_fatia[ambos] / gt_por_fatia[ambos]) if ambos.any() else np.array([])
    mais_estreita = (pred_por_fatia[ambos] < gt_por_fatia[ambos]) if ambos.any() else np.array([])

    fatias = []
    for i, z in enumerate(z_orig):
        a_gt = float(gt_por_fatia[i]) * area_voxel_mm2
        a_pred = float(pred_por_fatia[i]) * area_voxel_mm2
        if a_gt == 0 and a_pred == 0:
            continue
        if a_gt > 0 and a_pred > 0:
            categoria = "sobreposta"
        elif a_gt > 0:
            categoria = "so_gt"
        else:
            categoria = "so_predicao"
        if n_fatias_gt:
            rel = "dentro" if z0g <= z <= z1g else (nome_zmin if z < z0g else nome_zmax)
        else:
            rel = NA
        fatias.append({
            "z": int(z), "z_relativo_ao_gt": rel,
            "area_gt_mm2": a_gt, "area_pred_mm2": a_pred,
            "razao_pred_gt": (a_pred / a_gt) if a_gt > 0 else "invalido: GT vazio na fatia",
            "categoria": categoria,
        })

    return {
        "spacing_mm": list(spacing),
        "voxel_mm3": voxel_mm3,
        "orientacao": orientacao,
        "eixo_z": orientacao[2] if len(orientacao) >= 3 else "?",
        "pontas_anatomicas": anatomico,
        "nome_ponta_z_min": nome_zmin,
        "nome_ponta_z_max": nome_zmax,
        "volume_gt_mL": _ml(int(g.sum()), voxel_mm3),
        "volume_pred_mL": _ml(int(p.sum()), voxel_mm3),
        "FP_total_mL": _ml(n_fp, voxel_mm3),
        "FN_total_mL": _ml(n_fn, voxel_mm3),
        "FP_extensao_mL": _ml(n_fp_extensao, voxel_mm3),
        "FP_lateral_mL": _ml(n_fp_lateral, voxel_mm3),
        "frac_FP_extensao": _frac(n_fp_extensao, n_fp, "FP vazio"),
        "FP_extensao_por_ponta_mL": vol_ponta,
        "FP_extensao_interna_mL": (_ml(n_fp_interna, voxel_mm3) if n_fp_interna is not None
                                   else "invalido: GT vazio em Z"),
        "FN_fino_mL": _ml(n_fn_fino, voxel_mm3),
        "FN_bloco_mL": _ml(n_fn_bloco, voxel_mm3),
        "frac_FN_fino": _frac(n_fn_fino, n_fn, "FN vazio"),
        "camada_fina_vox": CAMADA_FINA_VOX,
        "sobra_por_ponta_mm": pontas,
        "comprimento_gt_mm": comp_gt,
        "comprimento_pred_mm": comp_pred,
        "diferenca_comprimento_mm": dif_comp,
        "campo_z_mm": campo_z_mm,
        "frac_campo_gt": _frac(comp_gt, campo_z_mm, "campo vazio") if isinstance(comp_gt, float)
                         else comp_gt,
        "frac_campo_pred": _frac(comp_pred, campo_z_mm, "campo vazio")
                           if isinstance(comp_pred, float) else comp_pred,
        "extensao_z_gt": {"z_min": z0g, "z_max": z1g, "n_fatias": n_fatias_gt},
        "extensao_z_pred": {"z_min": z0p, "z_max": z1p, "n_fatias": n_fatias_pred},
        "n_fatias_sobrepostas": int(np.count_nonzero(ambos)),
        "area_gt_mediana_mm2": _p(gt_por_fatia[gt_por_fatia > 0] * area_voxel_mm2, 50),
        "area_pred_mediana_mm2": _p(pred_por_fatia[pred_por_fatia > 0] * area_voxel_mm2, 50),
        "razao_area_mediana": _p(razoes, 50),
        "razao_area_p5": _p(razoes, 5),
        "razao_area_p95": _p(razoes, 95),
        "frac_fatias_mais_estreita": (float(mais_estreita.mean()) if mais_estreita.size
                                      else "invalido: nenhuma fatia sobreposta"),
        "fatias": fatias,
    }


# ---------------------------------------------------------------------- execucao


def rodar_caso(caso: str, raiz: Path = RAIZ_PADRAO, alvos=fase5.ALVOS, log=print) -> list[dict]:
    """Mede as estruturas alvo de UM caso. Uma linha por estrutura."""
    destino = Path(raiz) / caso
    manifesto = json.loads((destino / "manifesto.json").read_text(encoding="utf-8"))
    dir_gt, dir_pred = destino / "gt", destino / "pred_masks"
    rois = list(manifesto["rois_encontradas"])
    linhas = []

    for alvo in alvos:
        gt_roi = next((r for r in rois if mapeamento.canonizar(r) == alvo), None)
        base = {c: None for c in COLUNAS}
        base.update(dataset=manifesto["dataset"], case_id=manifesto["case_id"],
                    instituicao=fase5.instituicao_de(caso), structure=alvo,
                    gt_roi_name=gt_roi, erro="")
        if gt_roi is None:
            base["erro"] = f"ABORTADA: {alvo} ausente das ROIs do caso"
            linhas.append({**base, "_fatias": []})
            log(f"  {caso}/{alvo}: ausente")
            continue

        estruturas = mapeamento.MAPA_LCTSC[alvo]
        caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{gt_roi}.nii.gz"
        caminhos_pred = [dir_pred / f"{n}.nii.gz" for n in estruturas]

        # Parte K ANTES de qualquer medida: grade divergente aborta a estrutura.
        try:
            alinhamento = [geometria.verificar_alinhamento(c, caminho_gt) for c in caminhos_pred]
        except geometria.DesalinhamentoGeometrico as e:
            base["erro"] = f"ABORTADA: {e}"
            linhas.append({**base, "_fatias": []})
            log(f"  {caso}/{alvo}: ABORTADA — {e}")
            continue

        geo_gt = geometria.descrever_nifti(caminho_gt)
        gt = rtst.carregar_mascara(caminho_gt)
        pred, _ = mapeamento.unir_predicao(dir_pred, estruturas)
        m = medir(pred, gt, tuple(geo_gt["zooms_mm"]), geo_gt["orientacao"])

        nzmin, nzmax = m["nome_ponta_z_min"], m["nome_ponta_z_max"]
        base.update(
            spacing_mm=[round(s, 6) for s in m["spacing_mm"]],
            orientacao=m["orientacao"], eixo_z=m["eixo_z"],
            pontas_anatomicas=m["pontas_anatomicas"],
            alinhamento="; ".join(a["veredito"] for a in alinhamento),
        )
        for c in ("volume_gt_mL", "volume_pred_mL", "FP_total_mL", "FN_total_mL",
                  "FP_extensao_mL", "FP_lateral_mL", "frac_FP_extensao",
                  "FP_extensao_interna_mL", "FN_fino_mL", "FN_bloco_mL", "frac_FN_fino",
                  "comprimento_gt_mm", "comprimento_pred_mm", "diferenca_comprimento_mm",
                  "campo_z_mm", "frac_campo_gt", "frac_campo_pred",
                  "n_fatias_sobrepostas", "area_gt_mediana_mm2", "area_pred_mediana_mm2",
                  "razao_area_mediana", "razao_area_p5", "razao_area_p95",
                  "frac_fatias_mais_estreita"):
            base[c] = m[c]
        base["n_fatias_gt"] = m["extensao_z_gt"]["n_fatias"]
        base["n_fatias_pred"] = m["extensao_z_pred"]["n_fatias"]
        # distal/proximal saem com o nome que a orientacao determinou; se a
        # orientacao nao permitir nome anatomico, as colunas ficam vazias e as
        # pontas saem como erro_ponta_z_min/max — nunca rotuladas por presuncao.
        for nome in (nzmin, nzmax):
            base[f"erro_{nome}_mm"] = m["sobra_por_ponta_mm"][nome]
            base[f"FP_extensao_{nome}_mL"] = m["FP_extensao_por_ponta_mL"][nome]

        linhas.append({**base, "_fatias": m["fatias"], "_medida": m})
        log(f"  {caso}/{alvo}: FP {m['FP_total_mL']:.3f} mL "
            f"(extensao {m['frac_FP_extensao'] if isinstance(m['frac_FP_extensao'], str) else format(m['frac_FP_extensao'], '.3f')}) / "
            f"FN {m['FN_total_mL']:.3f} mL")
    return linhas


def _numeros(linhas, chave):
    """Valores float de `chave`, descartando invalidos — e contando quantos caiu."""
    vals = [l[chave] for l in linhas if isinstance(l.get(chave), (int, float))
            and not isinstance(l.get(chave), bool)]
    descartados = len(linhas) - len(vals)
    return np.asarray(vals, dtype=float), descartados


def _resumo(linhas, chave) -> dict:
    v, desc = _numeros(linhas, chave)
    return {
        "n": int(v.size), "descartados_invalidos": desc,
        "mediana": _p(v, 50), "p5": _p(v, 5), "p95": _p(v, 95),
        "min": float(v.min()) if v.size else NA, "max": float(v.max()) if v.size else NA,
    }


CHAVES_RESUMO = (
    "FP_total_mL", "FN_total_mL", "FP_extensao_mL", "FP_lateral_mL", "frac_FP_extensao",
    "FP_extensao_distal_mL", "FP_extensao_proximal_mL", "FP_extensao_interna_mL",
    "FN_fino_mL", "FN_bloco_mL", "frac_FN_fino",
    "erro_distal_mm", "erro_proximal_mm",
    "comprimento_gt_mm", "comprimento_pred_mm", "diferenca_comprimento_mm",
    "campo_z_mm", "frac_campo_gt", "frac_campo_pred",
    "razao_area_mediana", "razao_area_p5", "razao_area_p95", "frac_fatias_mais_estreita",
    "area_gt_mediana_mm2", "area_pred_mediana_mm2",
)


def agregar(linhas: list[dict]) -> dict:
    """Agregados por estrutura, global e estratificado por instituicao."""
    out = {}
    for estrutura in sorted({l["structure"] for l in linhas}):
        das = [l for l in linhas if l["structure"] == estrutura and not l["erro"]]
        bloco = {
            "n_casos": len(das),
            "global": {k: _resumo(das, k) for k in CHAVES_RESUMO},
            # agregado POOLED: soma de volumes, nao media de fracoes. As duas
            # respostas sao diferentes e as duas sao publicadas de proposito.
            "pooled": {
                "FP_total_mL": float(sum(l["FP_total_mL"] for l in das)),
                "FP_extensao_mL": float(sum(l["FP_extensao_mL"] for l in das)),
                "FP_lateral_mL": float(sum(l["FP_lateral_mL"] for l in das)),
                "FN_total_mL": float(sum(l["FN_total_mL"] for l in das)),
                "FN_fino_mL": float(sum(l["FN_fino_mL"] for l in das)),
                "FN_bloco_mL": float(sum(l["FN_bloco_mL"] for l in das)),
            },
            "por_instituicao": {},
        }
        b = bloco["pooled"]
        b["frac_FP_extensao"] = _frac(b["FP_extensao_mL"], b["FP_total_mL"], "FP vazio")
        b["frac_FN_fino"] = _frac(b["FN_fino_mL"], b["FN_total_mL"], "FN vazio")
        for inst in sorted({l["instituicao"] for l in das}):
            do_inst = [l for l in das if l["instituicao"] == inst]
            bloco["por_instituicao"][inst] = {
                "n_casos": len(do_inst),
                **{k: _resumo(do_inst, k) for k in CHAVES_RESUMO},
            }
        out[estrutura] = bloco
    return out


def responder(agregados: dict) -> dict:
    """(a)-(d) por estrutura, cada uma com o numero e a regra que a rotulou."""
    respostas = {}
    for estrutura, bloco in agregados.items():
        g, pooled = bloco["global"], bloco["pooled"]

        fa = g["frac_FP_extensao"]["mediana"]
        a = {
            "pergunta": "que fracao do FP total e extensao (fatia sem GT) contra fronteira?",
            "frac_FP_extensao_mediana_por_caso": fa,
            "frac_FP_extensao_pooled": pooled["frac_FP_extensao"],
            "FP_extensao_mL_mediana": g["FP_extensao_mL"]["mediana"],
            "FP_lateral_mL_mediana": g["FP_lateral_mL"]["mediana"],
        }

        d_, p_ = g["FP_extensao_distal_mL"]["mediana"], g["FP_extensao_proximal_mL"]["mediana"]
        if isinstance(d_, float) and isinstance(p_, float):
            maior, menor = max(d_, p_), min(d_, p_)
            razao = maior / menor if menor > 0 else float("inf")
            rotulo = ("concentrada em " + ("distal" if d_ > p_ else "proximal")
                      if razao >= LIMIAR_CONCENTRACAO else "simetrica entre as pontas")
        else:
            razao, rotulo = NA, "invalido: ponta sem valor"
        b = {
            "pergunta": "a extensao e simetrica ou concentrada numa ponta?",
            "FP_extensao_distal_mL_mediana": d_,
            "FP_extensao_proximal_mL_mediana": p_,
            "erro_distal_mm_mediana": g["erro_distal_mm"]["mediana"],
            "erro_proximal_mm_mediana": g["erro_proximal_mm"]["mediana"],
            "razao_entre_pontas": razao,
            "rotulo": rotulo,
            "regra": f"razao entre as pontas >= {LIMIAR_CONCENTRACAO} = concentrada",
            # controle de confusao: E1 (o modelo passa do ponto) e E6 (o
            # contornador parou antes) dao o MESMO FP_extensao. Uma predicao que
            # ocupa o campo inteiro nao escolheu onde terminar.
            "frac_campo_pred_mediana": g["frac_campo_pred"]["mediana"],
            "frac_campo_gt_mediana": g["frac_campo_gt"]["mediana"],
        }

        fe = g["frac_fatias_mais_estreita"]["mediana"]
        if isinstance(fe, float):
            if fe >= LIMIAR_SISTEMATICO_FRAC:
                rot_c = "sistematicamente mais estreita"
            elif fe <= 1.0 - LIMIAR_SISTEMATICO_FRAC:
                rot_c = "sistematicamente mais larga"
            else:
                rot_c = "so em parte das fatias"
        else:
            rot_c = "invalido: sem fatia sobreposta"
        c = {
            "pergunta": "a predicao e sistematicamente mais estreita ou so em algumas fatias?",
            "frac_fatias_mais_estreita_mediana": fe,
            "razao_area_mediana_das_medianas": g["razao_area_mediana"]["mediana"],
            "razao_area_p5_mediana": g["razao_area_p5"]["mediana"],
            "razao_area_p95_mediana": g["razao_area_p95"]["mediana"],
            "rotulo": rot_c,
            "regra": (f"fracao de fatias mais estreitas >= {LIMIAR_SISTEMATICO_FRAC} = "
                      f"sistematicamente mais estreita; <= {1 - LIMIAR_SISTEMATICO_FRAC:.2f} = "
                      "sistematicamente mais larga; entre as duas = so em parte das fatias"),
        }

        d = {"pergunta": "o comportamento e o mesmo nas tres instituicoes?", "por_instituicao": {},
             "amplitudes": {}, "regra": (f"amplitude de fracao entre instituicoes > "
                                         f"{LIMIAR_AMPLITUDE_INSTITUICAO} = muda")}
        for chave in ("frac_FP_extensao", "frac_FN_fino", "frac_fatias_mais_estreita"):
            vals = {i: v[chave]["mediana"] for i, v in bloco["por_instituicao"].items()}
            d["por_instituicao"][chave] = vals
            nums = [v for v in vals.values() if isinstance(v, float)]
            amp = (max(nums) - min(nums)) if len(nums) > 1 else NA
            d["amplitudes"][chave] = {
                "amplitude": amp,
                "rotulo": (("muda entre instituicoes" if amp > LIMIAR_AMPLITUDE_INSTITUICAO
                            else "estavel entre instituicoes") if isinstance(amp, float) else NA),
            }
        for chave in ("FP_extensao_mL", "erro_distal_mm", "erro_proximal_mm",
                      "razao_area_mediana", "frac_campo_gt", "frac_campo_pred"):
            d["por_instituicao"][chave] = {
                i: v[chave]["mediana"] for i, v in bloco["por_instituicao"].items()}

        respostas[estrutura] = {"a": a, "b": b, "c": c, "d": d}
    return respostas


def rodar(raiz: Path = RAIZ_PADRAO, casos=None, log=print) -> dict:
    """Roda o diagnostico no `development` inteiro (ou na lista dada)."""
    if casos is None:
        casos = fase5.carregar_split(raiz)[SPLIT_USADO]
    linhas, fatias = [], []
    for caso in casos:
        log(f"{caso}")
        for linha in rodar_caso(caso, raiz=raiz, log=log):
            das_fatias = linha.pop("_fatias", [])
            linha.pop("_medida", None)
            for f in das_fatias:
                fatias.append({"case_id": linha["case_id"], "instituicao": linha["instituicao"],
                               "structure": linha["structure"], **f})
            linhas.append(linha)
    agregados = agregar(linhas)
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split_usado": SPLIT_USADO,
        "casos": list(casos),
        "constantes": {
            "camada_fina_vox": CAMADA_FINA_VOX,
            "limiar_concentracao": LIMIAR_CONCENTRACAO,
            "limiar_sistematico_frac": LIMIAR_SISTEMATICO_FRAC,
            "limiar_amplitude_instituicao": LIMIAR_AMPLITUDE_INSTITUICAO,
            "origem": ("camada_fina_vox vem da grade de voxel; os tres limiares sao "
                       "convencao de redacao do summary. NENHUMA constante vem do GT."),
        },
        "uso_do_gt": ("o GT AVALIA todas as medidas deste arquivo e nao CONSTROI nenhuma "
                      "predicao. Nenhuma constante daqui pode ser copiada para uma regra."),
        "linhas": linhas, "fatias": fatias,
        "agregados": agregados, "respostas": responder(agregados),
    }


# ----------------------------------------------------------------------- saida


def _f(v, casas=4) -> str:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    if v is None:
        return "—"
    return str(v)


def _summary_md(r: dict) -> str:
    md = [
        "# Partes 5 e 6 — diagnostico longitudinal (SpinalCord, Esophagus)",
        "",
        f"- gerado em: {r['gerado_em']}",
        f"- split: `{r['split_usado']}` ({len(r['casos'])} casos)",
        f"- casca fina: camada <= {CAMADA_FINA_VOX} voxel (chessboard) da superficie da predicao",
        "- o GT foi usado para MEDIR. Nenhuma constante deste relatorio veio do GT e nenhuma",
        "  medida daqui e regra: uma regra de terminacao tera que derivar seu ponto de corte",
        "  de algo observavel sem GT, e isso sera declarado no experimento dela.",
        "- comprimento = extensao do suporte em Z ((z_max - z_min + 1) x dz), nao arco.",
        "- `frac_campo_pred` = quanto do campo de visao em Z a predicao ocupa. E o controle",
        "  de confusao entre E1 (a predicao passa do ponto) e E6 (o contornador parou antes):",
        "  os dois produzem o MESMO FP_extensao, e so a fracao do campo os separa. O campo",
        "  sai do shape do array, nao do GT.",
        "",
    ]
    for estrutura, bloco in r["agregados"].items():
        g = bloco["global"]
        md += [f"## {estrutura} (n = {bloco['n_casos']})", "",
               "| medida | mediana | P5 | P95 | min | max | n |",
               "|---|---|---|---|---|---|---|"]
        for k in CHAVES_RESUMO:
            s = g[k]
            md.append(f"| {k} | {_f(s['mediana'])} | {_f(s['p5'])} | {_f(s['p95'])} | "
                      f"{_f(s['min'])} | {_f(s['max'])} | {s['n']} |")
        p = bloco["pooled"]
        md += ["", "Agregado pooled (soma dos volumes da coorte, nao media de fracoes):", "",
               "| medida | mL |", "|---|---|"]
        for k in ("FP_total_mL", "FP_extensao_mL", "FP_lateral_mL",
                  "FN_total_mL", "FN_fino_mL", "FN_bloco_mL"):
            md.append(f"| {k} | {_f(p[k])} |")
        md += [f"| frac_FP_extensao (pooled) | {_f(p['frac_FP_extensao'])} |",
               f"| frac_FN_fino (pooled) | {_f(p['frac_FN_fino'])} |", ""]

        md += ["### Estratificado por instituicao (medianas)", "",
               "| medida | " + " | ".join(sorted(bloco["por_instituicao"])) + " |",
               "|---|" + "---|" * len(bloco["por_instituicao"])]
        for k in ("FP_total_mL", "FP_extensao_mL", "FP_lateral_mL", "frac_FP_extensao",
                  "FP_extensao_distal_mL", "FP_extensao_proximal_mL",
                  "erro_distal_mm", "erro_proximal_mm", "FN_total_mL", "frac_FN_fino",
                  "razao_area_mediana", "frac_fatias_mais_estreita",
                  "comprimento_gt_mm", "comprimento_pred_mm",
                  "campo_z_mm", "frac_campo_gt", "frac_campo_pred"):
            linha = [k] + [_f(bloco["por_instituicao"][i][k]["mediana"])
                           for i in sorted(bloco["por_instituicao"])]
            md.append("| " + " | ".join(linha) + " |")
        md.append("")

        resp = r["respostas"][estrutura]
        md += ["### Respostas", ""]
        for letra in ("a", "b", "c", "d"):
            x = resp[letra]
            md.append(f"**({letra})** {x['pergunta']}")
            md.append("")
            for k, v in x.items():
                if k == "pergunta":
                    continue
                md.append(f"- `{k}`: {json.dumps(v, ensure_ascii=False, default=_f)}"
                          if isinstance(v, dict) else f"- `{k}`: {_f(v)}")
            md.append("")
    md += ["## Limites deste instrumento", "",
           "- FP_extensao usa a fatia INTEIRA como criterio: um FP na altura certa mas em outra",
           "  regiao do torax conta como lateral, nao como extensao.",
           "- a distancia usada em FN_fino e ate a rede de VOXELS da predicao, nao ate uma",
           "  superficie interpolada.",
           "- razao de area so e calculada em fatias onde as DUAS mascaras existem; as fatias",
           "  so_gt e so_predicao aparecem no CSV por fatia e nao entram na razao.",
           "- comprimento e extensao em Z do suporte, nao comprimento de arco.",
           "- as medidas descrevem a coorte de avaliacao sob estas condicoes; nada aqui e",
           "  afirmacao sobre outra coorte, outro dataset ou outra instituicao.", ""]
    return "\n".join(md)


def gravar(r: dict, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)

    p_csv = saida / "diagnostico_longitudinal.csv"
    with p_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(r["linhas"])

    p_fatias = saida / "area_por_fatia.csv"
    with p_fatias.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_FATIA, extrasaction="ignore")
        w.writeheader()
        w.writerows(r["fatias"])

    p_json = saida / "diagnostico_longitudinal.json"
    p_json.write_text(json.dumps(
        {k: v for k, v in r.items() if k != "fatias"}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    p_md = saida / "summary.md"
    p_md.write_text(_summary_md(r), encoding="utf-8")

    for p in (p_csv, p_fatias, p_json, p_md):
        log(f"gravado: {p}")
    return {"csv": p_csv, "csv_fatias": p_fatias, "json": p_json, "summary": p_md}


# -------------------------------------------------------------------- autoteste


def _tubo(shape=(40, 40, 60), z=(10, 50), raio=4) -> np.ndarray:
    """Tubo cilindrico centrado, do tipo medula/esofago. GT sintetico do autoteste."""
    m = np.zeros(shape, dtype=bool)
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    disco = (yy - shape[0] // 2) ** 2 + (xx - shape[1] // 2) ** 2 <= raio ** 2
    m[:, :, z[0]:z[1]] = disco[:, :, None]
    return m


def _autoteste() -> None:
    """Controle POSITIVO: o instrumento tem que SEPARAR extensao de fronteira.

    Se estes asserts passassem com qualquer entrada, o instrumento nao serviria.
    Por isso cada caso sintetico afirma o que TEM que dar alto E o que TEM que
    dar ~zero — e no fim se exige que os dois casos sejam distinguiveis.
    """
    from scipy.ndimage import binary_dilation, binary_erosion

    spacing = (0.98, 0.98, 3.0)
    dz = spacing[2]
    gt = _tubo()

    # 1) predicao ESTENDIDA em 10 fatias na ponta z_max: so extensao, zero fronteira
    est = gt.copy()
    est[:, :, 50:60] = gt[:, :, 49][:, :, None]
    m = medir(est, gt, spacing, "LPS")
    assert m["FP_lateral_mL"] == 0.0, m["FP_lateral_mL"]
    assert m["frac_FP_extensao"] == 1.0, m["frac_FP_extensao"]
    assert m["FP_extensao_mL"] > 0.0, m
    assert m["FN_total_mL"] == 0.0, m["FN_total_mL"]
    # a ponta certa, com o nome certo: LPS -> eixo 2 = S -> z_max = proximal
    assert m["nome_ponta_z_max"] == "proximal" and m["nome_ponta_z_min"] == "distal", m
    assert m["FP_extensao_por_ponta_mL"]["distal"] == 0.0, m["FP_extensao_por_ponta_mL"]
    assert m["FP_extensao_por_ponta_mL"]["proximal"] == m["FP_extensao_mL"], m
    assert abs(m["sobra_por_ponta_mm"]["proximal"] - 10 * dz) < 1e-6, m["sobra_por_ponta_mm"]
    assert m["sobra_por_ponta_mm"]["distal"] == 0.0, m["sobra_por_ponta_mm"]
    assert abs(m["diferenca_comprimento_mm"] - 10 * dz) < 1e-6, m["diferenca_comprimento_mm"]
    assert m["frac_fatias_mais_estreita"] == 0.0, m["frac_fatias_mais_estreita"]
    estendida = m

    # 2) predicao ERODIDA no plano: so casca fina de FN, zero extensao
    ero = binary_erosion(gt, structure=np.ones((3, 3, 1), bool))
    m = medir(ero, gt, spacing, "LPS")
    assert m["FP_total_mL"] == 0.0, m["FP_total_mL"]
    assert m["FP_extensao_mL"] == 0.0, m["FP_extensao_mL"]
    # nao e 1,00 e nao deveria ser: num disco discretizado de raio 4 uma parte do
    # anel (medido: 14 %) fica a 2 voxels do nucleo erodido, porque a borda
    # discreta e mais grossa que 1 voxel nas quinas. Isso e geometria da grade, e
    # o limiar de casca esta certo em nao mentir sobre ela.
    assert m["FN_fino_mL"] > 0.0 and m["frac_FN_fino"] > 0.80, m["frac_FN_fino"]
    assert m["FN_bloco_mL"] < m["FN_fino_mL"], (m["FN_bloco_mL"], m["FN_fino_mL"])
    assert m["frac_fatias_mais_estreita"] == 1.0, m["frac_fatias_mais_estreita"]
    assert m["razao_area_mediana"] < 1.0, m["razao_area_mediana"]
    assert m["diferenca_comprimento_mm"] == 0.0, m["diferenca_comprimento_mm"]
    erodida = m

    # 3) o instrumento SEPARA os dois? (se nao separar, ele nao serve)
    # sem FP nenhum, a fracao tem que sair INVALIDA e nunca 0,0 — 0,0 seria lido
    # como "nada e extensao" quando o certo e "nao ha FP para repartir"
    assert isinstance(erodida["frac_FP_extensao"], str), erodida["frac_FP_extensao"]
    assert estendida["frac_FP_extensao"] == 1.0, "nao separa FP"
    assert erodida["FN_fino_mL"] > 0.0 and estendida["FN_total_mL"] == 0.0, "nao separa FN"

    # 4) controle NEGATIVO: predicao identica ao GT nao pode gerar erro nenhum
    m = medir(gt, gt, spacing, "LPS")
    assert m["FP_total_mL"] == m["FN_total_mL"] == 0.0, m
    assert m["razao_area_mediana"] == 1.0 and m["frac_fatias_mais_estreita"] == 0.0, m

    # 5) FN em BLOCO tem que sair como bloco, nao como casca — senao o limiar de
    #    camada esta frouxo e "casca fina" viraria rotulo de qualquer FN.
    grosso = _tubo(raio=8)
    m = medir(_tubo(raio=2), grosso, spacing, "LPS")
    assert m["FN_bloco_mL"] > 0.0, "FN profundo saiu classificado como casca fina"
    assert m["frac_FN_fino"] < 0.20, m["frac_FN_fino"]
    # e a separacao tem que ser LARGA: casca 0,86 contra bloco 0,13 no mesmo teste
    assert erodida["frac_FN_fino"] - m["frac_FN_fino"] > 0.5, "nao separa casca de bloco"

    # 6) FP LATERAL (predicao dilatada no plano) nao pode virar extensao
    m = medir(binary_dilation(gt, structure=np.ones((3, 3, 1), bool)), gt, spacing, "LPS")
    assert m["FP_extensao_mL"] == 0.0, m["FP_extensao_mL"]
    assert m["frac_FP_extensao"] == 0.0, m["frac_FP_extensao"]
    assert m["frac_fatias_mais_estreita"] == 0.0, m["frac_fatias_mais_estreita"]
    assert m["razao_area_mediana"] > 1.0, m["razao_area_mediana"]

    # 7) DESLOCAMENTO no plano (mesmo volume, mesma extensao): FP e FN existem,
    #    e os dois sao laterais/finos. Um instrumento que chamasse isso de
    #    extensao confundiria os dois remedios.
    deslocado = np.roll(gt, 3, axis=0)
    m = medir(deslocado, gt, spacing, "LPS")
    assert m["FP_extensao_mL"] == 0.0 and m["FP_lateral_mL"] > 0.0, m
    assert m["diferenca_comprimento_mm"] == 0.0, m["diferenca_comprimento_mm"]
    assert abs(m["razao_area_mediana"] - 1.0) < 1e-9, m["razao_area_mediana"]

    # 8) a orientacao INVERTE os nomes das pontas (senao o codigo de eixo e decorativo)
    m = medir(est, gt, spacing, "LPI")
    assert m["nome_ponta_z_max"] == "distal", m["nome_ponta_z_max"]
    assert m["FP_extensao_por_ponta_mL"]["distal"] > 0.0, m["FP_extensao_por_ponta_mL"]
    m = medir(est, gt, spacing, "RAL")
    assert m["pontas_anatomicas"] is False and m["nome_ponta_z_max"] == "ponta_z_max", m

    # 9) extensao na ponta z_min tambem tem que ser detectada (nao so na z_max)
    baixo = gt.copy()
    baixo[:, :, 0:10] = gt[:, :, 10][:, :, None]
    m = medir(baixo, gt, spacing, "LPS")
    assert m["FP_extensao_por_ponta_mL"]["distal"] == m["FP_extensao_mL"] > 0.0, m
    assert abs(m["sobra_por_ponta_mm"]["distal"] - 10 * dz) < 1e-6, m["sobra_por_ponta_mm"]

    # 10) buraco em Z no meio do GT vira extensao INTERNA, nao ponta
    gt_furado = gt.copy()
    gt_furado[:, :, 28:32] = False
    m = medir(gt, gt_furado, spacing, "LPS")
    assert m["FP_extensao_interna_mL"] == m["FP_extensao_mL"] > 0.0, m
    assert m["FP_extensao_por_ponta_mL"]["distal"] == 0.0, m["FP_extensao_por_ponta_mL"]

    # 11) mascara vazia nao pode devolver float plausivel
    m = medir(np.zeros_like(gt), gt, spacing, "LPS")
    assert isinstance(m["comprimento_pred_mm"], str), m["comprimento_pred_mm"]
    assert isinstance(m["frac_fatias_mais_estreita"], str), m["frac_fatias_mais_estreita"]
    assert m["FN_fino_mL"] == 0.0 and m["FN_bloco_mL"] == m["FN_total_mL"] > 0.0, m

    # 12) controle de CONFUSAO: o campo de visao separa "passou do ponto" de
    #     "o contornador parou antes". Uma predicao que ocupa o volume inteiro
    #     tem frac_campo_pred == 1 e nao escolheu onde terminar; se esta medida
    #     nao existisse, os dois casos sairiam com o mesmo FP_extensao.
    campo_mm = gt.shape[2] * dz
    m = medir(gt, gt, spacing, "LPS")
    assert m["campo_z_mm"] == campo_mm, m["campo_z_mm"]
    assert abs(m["frac_campo_gt"] - 40 * dz / campo_mm) < 1e-9, m["frac_campo_gt"]
    cheia = np.zeros_like(gt)
    cheia[:, :, :] = gt[:, :, 30][:, :, None]
    m_cheia = medir(cheia, gt, spacing, "LPS")
    assert m_cheia["frac_campo_pred"] == 1.0, m_cheia["frac_campo_pred"]
    assert estendida["frac_campo_pred"] < 1.0, estendida["frac_campo_pred"]
    # mesmo rotulo de erro (extensao), leitura diferente — e por isso que a
    # fracao do campo vai no CSV ao lado do FP_extensao
    assert m_cheia["frac_FP_extensao"] == estendida["frac_FP_extensao"] == 1.0, (
        m_cheia["frac_FP_extensao"], estendida["frac_FP_extensao"])

    print("diagnostico_longitudinal.py: autoteste OK (12 controles)")


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    ap.add_argument("--caso", action="append", help="limita a estes casos (default: development)")
    a = ap.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0
    r = rodar(raiz=a.raiz, casos=a.caso)
    gravar(r, saida=a.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
