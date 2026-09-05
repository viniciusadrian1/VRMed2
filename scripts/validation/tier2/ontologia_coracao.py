"""Parte 14 — o coracao como problema de ONTOLOGIA, nao de otimizacao.

Este modulo NAO altera o modelo, NAO gera predicao, NAO otimiza nada. Ele mede o
TAMANHO da divergencia de DEFINICAO entre duas coisas que tem o mesmo nome e nao
sao a mesma estrutura, para que ninguem leia o Dice de 0,7552 como acuracia.

    heart_model_definition — o que o TotalSegmentator (tarefa `total`, classe
        `heart`) se propoe a delimitar: o coracao SEM saco pericardico.
    heart_gt_definition    — o que o contornador do LCTSC desenhou: o coracao
        COM saco pericardico e gordura, atlas RTOG 1106, com corte superior no
        nivel inferior da arteria pulmonar.

Duas definicoes diferentes produzem UM Dice. O Dice nao sabe qual das duas ele
esta medindo — e por isso ele nao pode ser lido como erro do modelo. As duas
avaliacoes saem SEPARADAS e ROTULADAS, e o objetivo explicito NAO e faze-las
convergir.

O QUE E MEDIDO (so no `development`, so a ROI Heart):

  1. As duas metades assimetricas que o Dice funde:
       precision_pred = |P inter G| / |P|  — quanto da predicao cai dentro do GT.
         E a pergunta da definicao do MODELO: se o GT for um envelope que contem
         o orgao, uma predicao correta sob a definicao do modelo esta quase toda
         dentro dele. Valor alto NAO prova a hipotese do envelope; e a medida
         compativel com ela.
       recall_gt = |P inter G| / |G|  — quanto do GT a predicao cobriu.
         E a pergunta da definicao do GT. O que falta aqui e, por hipotese, o
         que o modelo nunca se propos a segmentar.
     Nas duas variantes ja existentes (A_suporte_gt e B_campo_completo), com a
     ressalva de circularidade de A herdada do benchmark.

  2. O FN (GT fora da predicao) separado em ADJACENTE x LONGE. Aqui houve
     CORRECAO DE INSTRUMENTO, registrada em vez de escondida:

       PRIMEIRA VERSAO (topologica, mantida no relatorio como NEGATIVA): um
         componente conexo de FN e "contiguo" se encosta na predicao
         (6-vizinhanca). Zero constante. MEDIDO: da 1,0000 em 30/30 casos do
         coracao — e tambem 1,0000 em Esophagus, SpinalCord e Lung_R nos casos
         do controle de instrumento. Um criterio que nao muda de valor entre um
         envelope e um deslocamento de fronteira NAO separa nada. Continua
         publicado como resultado negativo; nenhuma conclusao se apoia nele.

       VERSAO QUE SEPARA: o PERFIL DE DISTANCIA. Para cada voxel de FN, a
         distancia euclidiana (`sampling=spacing`) ate o voxel de PREDICAO mais
         proximo, e a fracao acumulada do FN abaixo de cada distancia de uma
         grade FIXA de reporte (`DISTANCIAS_MM`). E a funcao de distribuicao
         empirica; nenhum limiar classifica coisa nenhuma, nada e escolhido
         depois de ver o resultado. Casca fina de fronteira e camada espessa
         aparecem como curvas diferentes, nao como um rotulo.

       TESTE DE ENVELOPE, tambem sem constante: `frac_anel_externo_em_gt` — a
         fracao do anel de 1 voxel imediatamente FORA da predicao que cai
         dentro do GT. Um envelope que envolve cobre o anel inteiro; um
         deslocamento de fronteira cobre so o lado para onde deslocou.
         Publicado global e restrito as fatias em que o GT existe (o corte em Z
         do atlas dilui a versao global).

  3. A espessura dessa camada, em mm: mediana, P95 e maximo da mesma distancia
     radial ate a predicao. O numero e uma DISTANCIA MEDIDA; dizer que ela "e"
     gordura pericardica seria hipotese, e este modulo nao a afirma.

  4. A extensao em Z dos dois lados e a divisao da divergencia entre:
       corte em Z — FN em fatias onde a predicao nao existe (e FP em fatias onde
         o GT nao existe). A direcao (superior/inferior) vem do codigo de eixo
         do NIfTI, nunca presumida.
       envelope lateral — FN dentro da faixa em Z que os dois compartilham.

  5. Estabilidade entre S1/S2/S3: uma divergencia de DEFINICAO deve reaparecer
     em toda instituicao. Se so aparecesse numa, seria outro fenomeno.

O QUE NAO E MEDIDO: nada de HD95/ASSD aqui — ja publicados na coorte e caros
(11,6 s por estrutura); esta parte e sobre volume, topologia e extensao.

PERICARDIO NO TOTALSEGMENTATOR: a tarefa `trunk_cavities` tem uma classe
`pericardium` (registrada em `pericardio_disponivel()`). Ela NAO e rodada aqui e
NAO deve ser rodada para "consertar" o coracao — trocar a saida do modelo para
casar com outra definicao e exatamente a otimizacao contra alvo alheio que esta
parte existe para impedir. O que seria preciso para uma comparacao
ontologicamente correta esta registrado no JSON de saida.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.ontologia_coracao
    python -m scripts.validation.tier2.ontologia_coracao --autoteste
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, generate_binary_structure, label

from ..segmentation_metrics import dice as _dice
from . import fase5, geometria, mapeamento, rtstruct as rtst
from .benchmark_tier2 import recall_containment
from .mapa_erro import _frac, _ml, _p, _recorte, _suporte_z

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase5" / "coracao"
ROI = "Heart"
CONJUNTO = "development"  # o `test` e intocavel nesta fase; `validation` so na confirmacao
NA = "nao aplicavel"
NM = "nao medido"

# 6-vizinhanca (face), a mesma conectividade de mapa_erro e benchmark_tier2, para
# que "n componentes" continue comparavel entre os relatorios.
CONECTIVIDADE = "face (6-vizinhanca, structure padrao do scipy.ndimage.label)"
_VIZ6 = generate_binary_structure(3, 1)

# Grade FIXA de reporte do perfil de distancia. E eixo de grafico, nao limiar de
# decisao: nenhuma classificacao, escolha ou conclusao deste modulo depende de um
# valor desta lista. Publicar a distribuicao inteira e o que dispensa escolher um
# corte depois de ver o resultado.
DISTANCIAS_MM = (1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 20.0, 30.0)

# ROIs usadas so como CONTROLE DE INSTRUMENTO. Nao sao resultado sobre elas.
ROIS_CONTROLE = ("Esophagus", "SpinalCord", "Lung_R", "Lung_L")

COLUNAS = [
    "case_id", "instituicao", "spacing_mm", "orientacao",
    "volume_gt_ml", "volume_pred_ml", "razao_volume_gt_sobre_pred",
    "dice_A", "precision_A", "recall_A",
    "dice_B", "precision_B", "recall_B",
    "fn_total_ml", "fn_frac_do_gt",
    "anel_externo_em_gt", "anel_externo_em_gt_fatias_com_gt",
    "casca_mm_mediana", "casca_mm_p95", "casca_mm_max",
    *[f"fn_frac_ate_{d:g}mm" for d in DISTANCIAS_MM],
    "fn_frac_contiguo_DEGENERADO", "fn_frac_distante_DEGENERADO", "fn_n_componentes",
    "fn_frac_corte_z", "fn_frac_envelope_lateral",
    "fn_ml_corte_superior", "fn_ml_corte_inferior",
    "fp_total_ml", "fp_frac_da_pred", "fp_frac_corte_z",
    "fp_ml_corte_superior", "fp_ml_corte_inferior",
    "divergencia_total_ml", "divergencia_frac_corte_z", "divergencia_frac_envelope_lateral",
    "z_gt_min", "z_gt_max", "z_gt_n_fatias", "z_pred_min", "z_pred_max", "z_pred_n_fatias",
    "z_delta_superior_mm", "z_delta_inferior_mm",
    "alinhamento_veredito", "erro",
]


# ------------------------------------------------------------------- utilitarios


def _direcoes_z(orientacao: str) -> tuple[str, str]:
    """(nome do indice ALTO, nome do indice BAIXO) no eixo 2, do codigo do NIfTI.

    Nao presume craniocaudal: se o eixo 2 nao for S nem I, os lados saem
    nomeados por indice e o relatorio diz isso.
    """
    eixo = orientacao[2] if len(orientacao) >= 3 else "?"
    if eixo == "S":
        return ("superior", "inferior")
    if eixo == "I":
        return ("inferior", "superior")
    return ("indice_alto", "indice_baixo")


def _mediana(valores) -> float | str:
    """Mediana dos valores NUMERICOS; string invalida entra como ausente, nao como 0."""
    nums = [float(v) for v in valores if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return float(np.median(nums)) if nums else "invalido: nenhum valor numerico"


def _recorte_z(pred: np.ndarray, z0: int, z1: int) -> np.ndarray:
    """Predicao limitada a faixa [z0, z1] — a variante A do benchmark, mesma construcao.

    CIRCULAR por construcao: a janela vem do alcance do GT DESTE caso. Reproduzida
    aqui so para que os numeros de A sejam comparaveis com os ja publicados.
    """
    fora = pred.copy()
    fora[:, :, :z0] = False
    fora[:, :, z1 + 1:] = False
    return fora


# --------------------------------------------------------------- nucleo da medida


def perfil_distancia(dist_mm: np.ndarray) -> dict:
    """Fracao acumulada do conjunto abaixo de cada distancia de `DISTANCIAS_MM`.

    Distribuicao empirica, nao classificacao: a grade e eixo de reporte e nenhuma
    decisao deste modulo depende dela.
    """
    if not dist_mm.size:
        return {f"frac_ate_{d:g}mm": "invalido: conjunto vazio" for d in DISTANCIAS_MM}
    return {f"frac_ate_{d:g}mm": float((dist_mm <= d).mean()) for d in DISTANCIAS_MM}


def anel_externo(pred: np.ndarray, gt: np.ndarray) -> dict:
    """Teste de ENVELOPE sem constante nenhuma.

    O anel e a casca de 1 voxel imediatamente fora da predicao (6-vizinhanca).
    Se o GT for um envelope que ENVOLVE a predicao, o anel inteiro cai dentro do
    GT. Se a discordancia for deslocamento de fronteira, so o lado para onde
    deslocou cai dentro. A versao `nas_fatias_com_gt` remove a diluicao causada
    por fatias onde o GT simplesmente nao existe (o corte em Z do atlas).
    """
    anel = binary_dilation(pred, structure=_VIZ6) & ~pred
    com_gt = gt.any(axis=(0, 1))
    anel_z = anel & com_gt[None, None, :]
    return {
        "definicao": "anel de 1 voxel imediatamente fora da predicao (6-vizinhanca)",
        "frac_anel_externo_em_gt": _frac(int((anel & gt).sum()), int(anel.sum()), "anel vazio"),
        "frac_anel_externo_em_gt_nas_fatias_com_gt": _frac(
            int((anel_z & gt).sum()), int(anel_z.sum()), "anel vazio nas fatias com GT"),
        "n_voxels_anel": int(anel.sum()),
    }


def separar_fn(fn: np.ndarray, pred: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """FN contiguo a predicao x FN distante — criterio TOPOLOGICO.

    MEDIDO E DEGENERADO: da frac_contiguo = 1,0000 em 30/30 casos do coracao e
    tambem em Esophagus, SpinalCord e Lung_R (ver `controle_instrumento`). Fica
    no relatorio como RESULTADO NEGATIVO — um criterio que nao muda entre um
    envelope e um deslocamento de fronteira nao separa os dois. Quem separa e o
    perfil de distancia + o anel externo.

    REGRA: nenhuma constante. Um componente conexo de FN e "contiguo" se pelo
    menos um voxel seu e vizinho de face de um voxel de PREDICAO. Nada vem do GT
    e nada vem de limiar. Roda identica num caso sem GT (FN vazio -> "invalido").
    """
    rot, n = label(fn)  # structure=None => 6-vizinhanca em 3D
    if n == 0:
        vazio = np.zeros_like(fn)
        return vazio, vazio, {"n_componentes": 0, "n_componentes_distantes": 0,
                              "maior_distante_n_voxels": 0}
    encosta = binary_dilation(pred, structure=_VIZ6) & fn
    rotulos_contiguos = np.unique(rot[encosta])
    rotulos_contiguos = rotulos_contiguos[rotulos_contiguos > 0]
    contiguo = np.isin(rot, rotulos_contiguos) & fn
    distante = fn & ~contiguo

    tamanhos = np.bincount(rot.ravel())[1:]
    distantes = [int(t) for i, t in enumerate(tamanhos, start=1)
                 if i not in set(rotulos_contiguos.tolist())]
    return contiguo, distante, {
        "n_componentes": int(n),
        "n_componentes_distantes": len(distantes),
        "maior_distante_n_voxels": max(distantes) if distantes else 0,
    }


def medir(pred: np.ndarray, gt: np.ndarray, spacing, orientacao: str = "???") -> dict:
    """Nucleo puro: nao le arquivo, nao escreve nada. E o que o autoteste exercita."""
    pred = np.asarray(pred) > 0.5
    gt = np.asarray(gt) > 0.5
    spacing = tuple(float(s) for s in spacing)
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    alto, baixo = _direcoes_z(orientacao)

    z_gt_full, z_pred_full = _suporte_z(gt), _suporte_z(pred)
    cortes, offset = _recorte(pred, gt)
    p, g = pred[cortes], gt[cortes]
    fp, fn = p & ~g, g & ~p

    vol_gt = _ml(int(g.sum()), voxel_mm3)
    vol_pred = _ml(int(p.sum()), voxel_mm3)

    # --- as duas metades assimetricas, nas duas variantes ja publicadas
    zg0, zg1 = z_gt_full[0], z_gt_full[1]
    pred_A = _recorte_z(pred, zg0, zg1) if z_gt_full[2] else np.zeros_like(pred)
    variantes = {
        "A_suporte_gt": {**recall_containment(pred_A, gt), "dice": _dice(pred_A, gt),
                         "ressalva": ("predicao limitada ao suporte do GT em Z "
                                      f"[{zg0}, {zg1}] — janela vinda do proprio GT, "
                                      "CIRCULAR por construcao")},
        "B_campo_completo": {**recall_containment(pred, gt), "dice": _dice(pred, gt),
                             "ressalva": "toda a extensao da predicao, sem recorte"},
    }

    # --- FN: casca contigua x ilha distante
    contiguo, distante, comps = separar_fn(fn, p)
    dist_ate_pred = distance_transform_edt(~p, sampling=spacing)
    mm_fn = dist_ate_pred[fn]
    mm_ilha = dist_ate_pred[distante]
    n_fn = int(fn.sum())

    # --- extensao em Z: corte nas pontas x envelope lateral
    zp0, zp1 = _suporte_z(p)[0], _suporte_z(p)[1]
    zc0, zc1 = _suporte_z(g)[0], _suporte_z(g)[1]
    fn_por_z = np.count_nonzero(fn, axis=(0, 1))
    fp_por_z = np.count_nonzero(fp, axis=(0, 1))
    sem_pred = ~p.any(axis=(0, 1))
    sem_gt = ~g.any(axis=(0, 1))
    idx_z = np.arange(fn_por_z.size)

    fn_alto = int(fn_por_z[sem_pred & (idx_z > zp1)].sum()) if zp1 >= 0 else int(fn_por_z.sum())
    fn_baixo = int(fn_por_z[sem_pred & (idx_z < zp0)].sum()) if zp0 >= 0 else 0
    fp_alto = int(fp_por_z[sem_gt & (idx_z > zc1)].sum()) if zc1 >= 0 else int(fp_por_z.sum())
    fp_baixo = int(fp_por_z[sem_gt & (idx_z < zc0)].sum()) if zc0 >= 0 else 0
    n_fp = int(fp.sum())

    return {
        "spacing_mm": list(spacing), "voxel_mm3": voxel_mm3, "orientacao": orientacao,
        "conectividade": CONECTIVIDADE,
        "volume_gt_ml": vol_gt, "volume_pred_ml": vol_pred,
        "razao_volume_gt_sobre_pred": _frac(vol_gt, vol_pred, "predicao vazia"),
        "variantes": variantes,
        "heart_gt_definition": {
            "pergunta": "quanto do que o GT contornou a predicao cobriu, e o que falta tem "
                        "a FORMA de um envelope em volta",
            "fn_total_ml": _ml(n_fn, voxel_mm3),
            "fn_frac_do_gt": _frac(n_fn, int(g.sum()), "GT vazio"),
            "envelope_anel_externo": anel_externo(p, g),
            "distancia_radial_mm": {
                "definicao": "distancia euclidiana (sampling=spacing) de cada voxel de FN ate "
                             "o voxel de PREDICAO mais proximo",
                "mediana": _p(mm_fn, 50), "p95": _p(mm_fn, 95),
                "max": float(mm_fn.max()) if mm_fn.size else "invalido: FN vazio",
                "perfil_acumulado": perfil_distancia(mm_fn),
            },
            "separacao_topologica_DEGENERADA": {
                "aviso": "criterio medido e NAO discriminante (1,0 para toda estrutura "
                         "testada) — publicado como resultado negativo, nao sustenta conclusao",
                "contiguo_ml": _ml(int(contiguo.sum()), voxel_mm3),
                "frac_contiguo": _frac(int(contiguo.sum()), n_fn, "FN vazio"),
                "distante_ml": _ml(int(distante.sum()), voxel_mm3),
                "frac_distante": _frac(int(distante.sum()), n_fn, "FN vazio"),
                "n_componentes": comps["n_componentes"],
                "n_componentes_distantes": comps["n_componentes_distantes"],
                "maior_distante_ml": _ml(comps["maior_distante_n_voxels"], voxel_mm3),
                "distancia_radial_mm_das_ilhas": {"mediana": _p(mm_ilha, 50),
                                                  "p95": _p(mm_ilha, 95)},
            },
            "corte_z": {
                f"ml_{alto}": _ml(fn_alto, voxel_mm3), f"ml_{baixo}": _ml(fn_baixo, voxel_mm3),
                "frac_corte_z": _frac(fn_alto + fn_baixo, n_fn, "FN vazio"),
                "frac_envelope_lateral": _frac(n_fn - fn_alto - fn_baixo, n_fn, "FN vazio"),
                "nota": "corte_z = FN em fatias onde a predicao nao existe; envelope lateral = "
                        "FN dentro da faixa em Z compartilhada",
            },
        },
        "heart_model_definition": {
            "pergunta": "a predicao esta contida no que o GT chamou de coracao, como estaria "
                        "um orgao dentro de um envelope que o contem",
            "fp_total_ml": _ml(n_fp, voxel_mm3),
            "fp_frac_da_pred": _frac(n_fp, int(p.sum()), "predicao vazia"),
            "corte_z": {
                f"ml_{alto}": _ml(fp_alto, voxel_mm3), f"ml_{baixo}": _ml(fp_baixo, voxel_mm3),
                "frac_corte_z": _frac(fp_alto + fp_baixo, n_fp, "FP vazio"),
                "nota": "FP em fatias onde o GT nao existe — e aqui que um corte superior do "
                        "contorno aparece, se houver",
            },
        },
        # A pergunta direta: da divergencia TOTAL (FP + FN, os dois lados somados,
        # sem cancelamento), quanto e corte em Z e quanto e envelope lateral.
        "divergencia_total": {
            "definicao": "FP + FN em voxels, sem cancelamento de sinal",
            "total_ml": _ml(n_fp + n_fn, voxel_mm3),
            "frac_do_volume_gt": _frac(n_fp + n_fn, int(g.sum()), "GT vazio"),
            "corte_z_ml": _ml(fn_alto + fn_baixo + fp_alto + fp_baixo, voxel_mm3),
            "frac_corte_z": _frac(fn_alto + fn_baixo + fp_alto + fp_baixo, n_fp + n_fn,
                                  "sem divergencia"),
            "envelope_lateral_ml": _ml(n_fp + n_fn - fn_alto - fn_baixo - fp_alto - fp_baixo,
                                       voxel_mm3),
            "frac_envelope_lateral": _frac(
                n_fp + n_fn - fn_alto - fn_baixo - fp_alto - fp_baixo, n_fp + n_fn,
                "sem divergencia"),
        },
        "extensao_z": {
            "gt": {"z_min": z_gt_full[0], "z_max": z_gt_full[1], "n_fatias": z_gt_full[2],
                   "mm": z_gt_full[2] * spacing[2]},
            "predicao": {"z_min": z_pred_full[0], "z_max": z_pred_full[1],
                         "n_fatias": z_pred_full[2], "mm": z_pred_full[2] * spacing[2]},
            "lado_indice_alto": alto, "lado_indice_baixo": baixo,
            f"delta_{alto}_mm": (z_pred_full[1] - z_gt_full[1]) * spacing[2],
            f"delta_{baixo}_mm": (z_gt_full[0] - z_pred_full[0]) * spacing[2],
            "convencao_delta": "positivo = a predicao vai ALEM do GT daquele lado",
        },
        "recorte_index": [[int(c.start), int(c.stop)] for c in cortes],
        "offset": [int(v) for v in offset],
    }


# ---------------------------------------------------------------------- execucao


def rodar_caso(caso: str, raiz: Path = RAIZ_PADRAO) -> dict:
    """Mede UM caso. Parte K (alinhamento) ANTES de qualquer medida."""
    destino = Path(raiz) / caso
    dir_gt, dir_pred = destino / "gt", destino / "pred_masks"
    caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{ROI}.nii.gz"
    alvos = mapeamento.MAPA_LCTSC[ROI]
    caminhos_pred = [dir_pred / f"{n}.nii.gz" for n in alvos]

    if not caminho_gt.exists():
        return {"case_id": caso, "erro": f"ABORTADA: GT ausente ({caminho_gt})"}

    try:
        alinhamento = [geometria.verificar_alinhamento(p, caminho_gt) for p in caminhos_pred]
    except geometria.DesalinhamentoGeometrico as e:
        return {"case_id": caso, "erro": f"ABORTADA: {e}"}

    geo_gt = geometria.descrever_nifti(caminho_gt)
    gt = rtst.carregar_mascara(caminho_gt)
    pred, _ = mapeamento.unir_predicao(dir_pred, alvos)
    r = medir(pred, gt, tuple(geo_gt["zooms_mm"]), geo_gt["orientacao"])
    r.update(case_id=caso, instituicao=fase5.instituicao_de(caso),
             estruturas_totalsegmentator=list(alvos),
             alinhamento_veredito=[a["veredito"] for a in alinhamento],
             delta_affine_max=[a["delta_affine_max"] for a in alinhamento], erro="")
    return r


def _linha(r: dict) -> dict:
    """Uma linha de CSV a partir do dicionario de um caso."""
    linha = {c: None for c in COLUNAS}
    linha["case_id"] = r["case_id"]
    if r.get("erro"):
        linha["erro"] = r["erro"]
        return linha
    g, m, z = r["heart_gt_definition"], r["heart_model_definition"], r["extensao_z"]
    alto, baixo = z["lado_indice_alto"], z["lado_indice_baixo"]
    linha.update(
        instituicao=r["instituicao"], spacing_mm=[round(s, 6) for s in r["spacing_mm"]],
        orientacao=r["orientacao"],
        volume_gt_ml=r["volume_gt_ml"], volume_pred_ml=r["volume_pred_ml"],
        razao_volume_gt_sobre_pred=r["razao_volume_gt_sobre_pred"],
        dice_A=r["variantes"]["A_suporte_gt"]["dice"],
        precision_A=r["variantes"]["A_suporte_gt"]["precision_pred"],
        recall_A=r["variantes"]["A_suporte_gt"]["recall_gt"],
        dice_B=r["variantes"]["B_campo_completo"]["dice"],
        precision_B=r["variantes"]["B_campo_completo"]["precision_pred"],
        recall_B=r["variantes"]["B_campo_completo"]["recall_gt"],
        fn_total_ml=g["fn_total_ml"], fn_frac_do_gt=g["fn_frac_do_gt"],
        anel_externo_em_gt=g["envelope_anel_externo"]["frac_anel_externo_em_gt"],
        anel_externo_em_gt_fatias_com_gt=(
            g["envelope_anel_externo"]["frac_anel_externo_em_gt_nas_fatias_com_gt"]),
        casca_mm_mediana=g["distancia_radial_mm"]["mediana"],
        casca_mm_p95=g["distancia_radial_mm"]["p95"],
        casca_mm_max=g["distancia_radial_mm"]["max"],
        **{f"fn_frac_ate_{d:g}mm": g["distancia_radial_mm"]["perfil_acumulado"][
            f"frac_ate_{d:g}mm"] for d in DISTANCIAS_MM},
        fn_frac_contiguo_DEGENERADO=g["separacao_topologica_DEGENERADA"]["frac_contiguo"],
        fn_frac_distante_DEGENERADO=g["separacao_topologica_DEGENERADA"]["frac_distante"],
        fn_n_componentes=g["separacao_topologica_DEGENERADA"]["n_componentes"],
        fn_frac_corte_z=g["corte_z"]["frac_corte_z"],
        fn_frac_envelope_lateral=g["corte_z"]["frac_envelope_lateral"],
        fn_ml_corte_superior=g["corte_z"].get("ml_superior", NA),
        fn_ml_corte_inferior=g["corte_z"].get("ml_inferior", NA),
        fp_total_ml=m["fp_total_ml"], fp_frac_da_pred=m["fp_frac_da_pred"],
        fp_frac_corte_z=m["corte_z"]["frac_corte_z"],
        fp_ml_corte_superior=m["corte_z"].get("ml_superior", NA),
        fp_ml_corte_inferior=m["corte_z"].get("ml_inferior", NA),
        divergencia_total_ml=r["divergencia_total"]["total_ml"],
        divergencia_frac_corte_z=r["divergencia_total"]["frac_corte_z"],
        divergencia_frac_envelope_lateral=r["divergencia_total"]["frac_envelope_lateral"],
        z_gt_min=z["gt"]["z_min"], z_gt_max=z["gt"]["z_max"], z_gt_n_fatias=z["gt"]["n_fatias"],
        z_pred_min=z["predicao"]["z_min"], z_pred_max=z["predicao"]["z_max"],
        z_pred_n_fatias=z["predicao"]["n_fatias"],
        z_delta_superior_mm=z.get(f"delta_{alto}_mm") if alto == "superior"
        else z.get(f"delta_{baixo}_mm"),
        z_delta_inferior_mm=z.get(f"delta_{baixo}_mm") if alto == "superior"
        else z.get(f"delta_{alto}_mm"),
        alinhamento_veredito=";".join(r["alinhamento_veredito"]), erro="",
    )
    return linha


_AGREGAR = [
    "volume_gt_ml", "volume_pred_ml", "razao_volume_gt_sobre_pred",
    "dice_A", "precision_A", "recall_A", "dice_B", "precision_B", "recall_B",
    "fn_total_ml", "fn_frac_do_gt",
    "anel_externo_em_gt", "anel_externo_em_gt_fatias_com_gt",
    "fn_frac_contiguo_DEGENERADO", "fn_frac_distante_DEGENERADO",
    *[f"fn_frac_ate_{d:g}mm" for d in DISTANCIAS_MM],
    "casca_mm_mediana", "casca_mm_p95", "casca_mm_max",
    "fn_frac_corte_z", "fn_frac_envelope_lateral",
    "fn_ml_corte_superior", "fn_ml_corte_inferior",
    "fp_total_ml", "fp_frac_da_pred", "fp_frac_corte_z",
    "fp_ml_corte_superior", "fp_ml_corte_inferior",
    "divergencia_total_ml", "divergencia_frac_corte_z", "divergencia_frac_envelope_lateral",
    "z_gt_n_fatias", "z_pred_n_fatias", "z_delta_superior_mm", "z_delta_inferior_mm",
]


def controle_instrumento(casos: list[str], raiz: Path = RAIZ_PADRAO, log=print) -> dict:
    """Os MESMOS discriminadores nas outras ROIs — controle, nao resultado sobre elas.

    Existe porque a primeira versao do separador deu 1,0000 em 30/30 casos do
    coracao, e um numero constante pode ser um achado ou um instrumento cego. Se
    o criterio topologico tambem der 1,0 em estruturas cujo erro JA se sabe ser
    outro (medula: casca fina; esofago: deslocamento), ele esta cego. Se o anel
    externo e o perfil de distancia mudarem entre elas, esses separam.

    NAO e avaliacao do esofago, da medula nem do pulmao: e checagem de que o
    instrumento aplicado ao coracao consegue devolver outro valor.
    """
    saida: dict = {}
    for roi in (ROI, *ROIS_CONTROLE):
        alvos = mapeamento.MAPA_LCTSC[roi]
        linhas = []
        for caso in casos:
            cg = Path(raiz) / caso / "gt" / f"{rtst.PREFIXO_MASCARA}{roi}.nii.gz"
            if not cg.exists():
                continue
            geo = geometria.descrever_nifti(cg)
            gt = rtst.carregar_mascara(cg)
            pred, _ = mapeamento.unir_predicao(Path(raiz) / caso / "pred_masks", alvos)
            g = medir(pred, gt, tuple(geo["zooms_mm"]), geo["orientacao"])["heart_gt_definition"]
            linhas.append({
                "frac_contiguo_DEGENERADO": g["separacao_topologica_DEGENERADA"]["frac_contiguo"],
                "anel_externo_em_gt": g["envelope_anel_externo"]["frac_anel_externo_em_gt"],
                "anel_externo_em_gt_fatias_com_gt": (
                    g["envelope_anel_externo"]["frac_anel_externo_em_gt_nas_fatias_com_gt"]),
                "fn_frac_ate_2mm": g["distancia_radial_mm"]["perfil_acumulado"]["frac_ate_2mm"],
                "fn_frac_ate_10mm": g["distancia_radial_mm"]["perfil_acumulado"]["frac_ate_10mm"],
                "casca_mm_mediana": g["distancia_radial_mm"]["mediana"],
                "casca_mm_p95": g["distancia_radial_mm"]["p95"],
            })
        saida[roi] = {"n": len(linhas),
                      **{k: _mediana([l[k] for l in linhas]) for k in linhas[0]}} if linhas \
            else {"n": 0, "nota": "nenhum caso com esta ROI"}
        log(f"  controle {roi}: {saida[roi]}")
    saida["leitura"] = ("se `frac_contiguo_DEGENERADO` for igual em todas as ROIs, esse criterio "
                        "esta cego; os que variam entre ROIs sao os que separam. Numeros das "
                        "ROIs de controle NAO sao avaliacao dessas estruturas.")
    return saida


def pericardio_disponivel() -> dict:
    """Existe pericardio no TotalSegmentator instalado? REGISTRO, nao execucao.

    Nao roda a tarefa e nao propoe roda-la para "consertar" o coracao.
    """
    reg = {"consultado_em": "totalsegmentator.map_to_binary / map_tasks_config",
           "executado": False,
           "por_que_nao_executar": (
               "trocar a saida do modelo para casar com a definicao do GT e otimizar contra "
               "um alvo que nao e o dele. A comparacao so faz sentido depois de harmonizar "
               "a ontologia, nao antes."),
           "o_que_faltaria_para_uma_comparacao_ontologicamente_correta": [
               "1. declarar a ontologia: heart_model = miocardio+cavidades; heart_gt = "
               "heart_model + saco pericardico + gordura, truncado em Z pelo atlas RTOG 1106",
               "2. construir a predicao COMPARAVEL a partir das classes do modelo "
               "(p. ex. heart uniao pericardium), com a regra declarada ANTES de medir",
               "3. verificar que `pericardium` da trunk_cavities e mesmo o SACO e nao a "
               "cavidade pericardica — o nome nao e a definicao",
               "4. reproduzir o corte superior do atlas a partir de referencia ANATOMICA "
               "(nivel inferior da arteria pulmonar), nunca do alcance em Z do proprio GT",
               "5. so entao medir; e reportar como estrutura NOVA, nunca como 'melhoria' "
               "do Dice do heart",
           ]}
    try:
        from totalsegmentator.map_to_binary import class_map
        from totalsegmentator.map_tasks_config import TASK_CONFIGS
    except Exception as e:  # noqa: BLE001 — registro, nao dependencia dura
        reg.update(disponivel=NM, motivo=f"import falhou: {e}")
        return reg
    tarefas = {t: [n for n in m.values() if "pericard" in n.lower()]
               for t, m in class_map.items()
               if any("pericard" in n.lower() for n in m.values())}
    reg.update(
        disponivel=bool(tarefas),
        tarefas_com_classe_pericardio=tarefas,
        trunk_cavities_classes=class_map.get("trunk_cavities", NM),
        trunk_cavities_config=TASK_CONFIGS.get("trunk_cavities", NM),
    )
    return reg


def rodar(raiz: Path = RAIZ_PADRAO, conjunto: str = CONJUNTO, log=print) -> dict:
    casos = fase5.carregar_split(Path(raiz))[conjunto]
    log(f"{conjunto}: {len(casos)} casos, ROI {ROI}")

    resultados, linhas = {}, []
    for caso in casos:
        r = rodar_caso(caso, raiz)
        resultados[caso] = r
        linhas.append(_linha(r))
        if r.get("erro"):
            log(f"  {caso}: {r['erro']}")
            continue
        v, g = r["variantes"], r["heart_gt_definition"]
        log(f"  {caso}: dice_B {v['B_campo_completo']['dice']:.4f} | "
            f"prec_A {v['A_suporte_gt']['precision_pred']:.4f} "
            f"rec_A {v['A_suporte_gt']['recall_gt']:.4f} | "
            f"anel {g['envelope_anel_externo']['frac_anel_externo_em_gt']:.4f} | "
            f"FN<=2mm {g['distancia_radial_mm']['perfil_acumulado']['frac_ate_2mm']:.3f}")

    log("controle de instrumento (as mesmas medidas nas outras ROIs):")
    controle = controle_instrumento(casos, raiz, log)

    validas = [l for l in linhas if not l["erro"]]
    # Checagem do instrumento, nao resultado: recortar a predicao no suporte do GT
    # so remove voxels de fatias onde o GT nao existe, e la nao ha intersecao — entao
    # o recall TEM que ser identico em A e B. Se algum dia diferir, o recorte comeu
    # voxel que intersecta o GT e a variante A esta errada.
    dif_recall = [(l["case_id"], l["recall_A"], l["recall_B"]) for l in validas
                  if abs(float(l["recall_A"]) - float(l["recall_B"])) > 1e-12]

    agregado = {"n_casos": len(linhas), "n_validos": len(validas),
                "checagem_recall_A_igual_B": {
                    "esperado": "identicos por construcao — o recorte em Z so tira FP",
                    "casos_divergentes": dif_recall,
                    "passou": not dif_recall},
                "mediana": {c: _mediana([l[c] for l in validas]) for c in _AGREGAR}}
    por_inst = {}
    for inst in sorted({l["instituicao"] for l in validas}):
        sel = [l for l in validas if l["instituicao"] == inst]
        por_inst[inst] = {"n": len(sel),
                          **{c: _mediana([l[c] for l in sel]) for c in
                             ("dice_B", "precision_A", "recall_A", "precision_B", "recall_B",
                              "anel_externo_em_gt", "casca_mm_p95",
                              "razao_volume_gt_sobre_pred")}}
    agregado["por_instituicao"] = por_inst

    return {"conjunto": conjunto, "roi": ROI, "casos": casos,
            "agregado": agregado, "por_caso": resultados, "linhas": linhas,
            "controle_instrumento": controle,
            "pericardio_no_totalsegmentator": pericardio_disponivel(),
            "declaracao": DECLARACAO}


DECLARACAO = {
    "titulo": "o coracao NAO e alvo de otimizacao nesta fase",
    "motivo": ("predicao e GT nomeiam estruturas DIFERENTES: `heart` do TotalSegmentator nao "
               "inclui saco pericardico; o GT do LCTSC inclui (atlas RTOG 1106) e ainda trunca "
               "em Z. Um Dice entre definicoes diferentes nao mede acuracia de segmentacao."),
    "consequencia": ("qualquer ganho de Dice obtido dilatando/engordando a predicao seria "
                     "ajuste a outra definicao, nao reducao de erro — e nao transferiria para "
                     "nenhum uso que dependa da definicao do modelo."),
    "condicao_para_reabrir": ("harmonizar a ontologia primeiro (ver "
                              "pericardio_no_totalsegmentator.o_que_faltaria...), e reportar o "
                              "resultado como estrutura NOVA, nunca como melhoria do heart."),
}


# ------------------------------------------------------------------------ relatorio


def _f(v, casas=4) -> str:
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    if v is None:
        return "—"
    return str(v)


def _resumo_md(r: dict) -> str:
    a, med = r["agregado"], r["agregado"]["mediana"]
    chk = a["checagem_recall_A_igual_B"]
    md = [f"# Ontologia do coracao — {r['roi']}, conjunto `{r['conjunto']}`\n",
          f"n = {a['n_validos']}/{a['n_casos']} casos validos. "
          f"Mediana entre casos. Uso educacional/experimental.\n",
          f"Checagem de instrumento — recall identico entre as variantes A e B "
          f"(esperado por construcao): **{'passou' if chk['passou'] else 'FALHOU'}** "
          f"({len(chk['casos_divergentes'])} caso(s) divergente(s)).\n",
          "\n## Declaracao\n",
          f"**{DECLARACAO['titulo']}** — {DECLARACAO['motivo']}\n",
          "\n## As duas avaliacoes, rotuladas\n",
          "| avaliacao | pergunta | metrica | mediana (A_suporte_gt) | mediana (B_campo_completo) |",
          "|---|---|---|---|---|",
          f"| `heart_model_definition` | a predicao esta contida no GT? | precision_pred | "
          f"{_f(med['precision_A'])} | {_f(med['precision_B'])} |",
          f"| `heart_gt_definition` | quanto do GT foi coberto? | recall_gt | "
          f"{_f(med['recall_A'])} | {_f(med['recall_B'])} |",
          f"| (fusao das duas) | — | Dice | {_f(med['dice_A'])} | {_f(med['dice_B'])} |",
          "\nO Dice e a fusao. Ele nao distingue as duas perguntas — e por isso que ele nao "
          "pode ser lido como acuracia.\n",
          "\n## Tamanho da divergencia\n",
          "| medida | mediana |", "|---|---|",
          f"| volume GT (mL) | {_f(med['volume_gt_ml'], 2)} |",
          f"| volume predicao (mL) | {_f(med['volume_pred_ml'], 2)} |",
          f"| razao volume GT / predicao | {_f(med['razao_volume_gt_sobre_pred'])} |",
          f"| GT nao coberto (mL) | {_f(med['fn_total_ml'], 2)} |",
          f"| GT nao coberto (fracao do GT) | {_f(med['fn_frac_do_gt'])} |",
          f"| anel de 1 voxel fora da predicao que cai no GT | "
          f"{_f(med['anel_externo_em_gt'])} |",
          f"| idem, so nas fatias em que o GT existe | "
          f"{_f(med['anel_externo_em_gt_fatias_com_gt'])} |",
          f"| distancia radial do FN — mediana (mm) | {_f(med['casca_mm_mediana'], 3)} |",
          f"| distancia radial do FN — P95 (mm) | {_f(med['casca_mm_p95'], 3)} |",
          f"| distancia radial do FN — max (mm) | {_f(med['casca_mm_max'], 3)} |",
          "\nA distancia radial e uma MEDIDA. Dizer que ela e gordura pericardica seria "
          "hipotese — nao afirmada aqui.\n",
          "\n### Perfil de distancia do FN (fracao acumulada, mediana entre casos)\n",
          "| ate (mm) | " + " | ".join(f"{d:g}" for d in DISTANCIAS_MM) + " |",
          "|---|" + "---|" * len(DISTANCIAS_MM),
          "| fracao do FN | " + " | ".join(
              _f(med[f"fn_frac_ate_{d:g}mm"], 3) for d in DISTANCIAS_MM) + " |",
          "\nGrade fixa de reporte, nao limiar de decisao: nada e classificado por ela.\n",
          "\n### Criterio topologico — resultado NEGATIVO\n",
          "| medida | mediana |", "|---|---|",
          f"| fracao do FN contigua a predicao | {_f(med['fn_frac_contiguo_DEGENERADO'])} |",
          f"| fracao do FN distante (ilha) | {_f(med['fn_frac_distante_DEGENERADO'])} |",
          "\nEste criterio da o mesmo valor para toda estrutura testada (ver controle de "
          "instrumento) — esta cego e nao sustenta nenhuma conclusao. Fica publicado.\n",
          "\n## Corte em Z x envelope lateral\n",
          "| medida | mediana |", "|---|---|",
          f"| FN em fatias sem predicao (fracao do FN) | {_f(med['fn_frac_corte_z'])} |",
          f"| FN dentro da faixa Z comum — envelope lateral | "
          f"{_f(med['fn_frac_envelope_lateral'])} |",
          f"| **divergencia TOTAL (FP+FN, sem cancelar) — mL** | "
          f"{_f(med['divergencia_total_ml'], 2)} |",
          f"| **dela, fracao que e CORTE EM Z** | {_f(med['divergencia_frac_corte_z'])} |",
          f"| **dela, fracao que e ENVELOPE LATERAL** | "
          f"{_f(med['divergencia_frac_envelope_lateral'])} |",
          f"| FP em fatias sem GT (fracao do FP) | {_f(med['fp_frac_corte_z'])} |",
          f"| FP superior (mL) | {_f(med['fp_ml_corte_superior'], 3)} |",
          f"| FP inferior (mL) | {_f(med['fp_ml_corte_inferior'], 3)} |",
          f"| fatias em Z do GT | {_f(med['z_gt_n_fatias'], 1)} |",
          f"| fatias em Z da predicao | {_f(med['z_pred_n_fatias'], 1)} |",
          f"| delta superior (mm, + = predicao alem do GT) | "
          f"{_f(med['z_delta_superior_mm'], 2)} |",
          f"| delta inferior (mm, + = predicao alem do GT) | "
          f"{_f(med['z_delta_inferior_mm'], 2)} |",
          "\n## Estabilidade entre instituicoes\n",
          "| instituicao | n | Dice B | precision A | recall A | precision B | recall B | "
          "anel externo | FN P95 (mm) |", "|---|---|---|---|---|---|---|---|---|"]
    for inst, v in a["por_instituicao"].items():
        md.append(f"| {inst} | {v['n']} | {_f(v['dice_B'])} | {_f(v['precision_A'])} | "
                  f"{_f(v['recall_A'])} | {_f(v['precision_B'])} | {_f(v['recall_B'])} | "
                  f"{_f(v['anel_externo_em_gt'])} | {_f(v['casca_mm_p95'], 3)} |")

    ctrl = r["controle_instrumento"]
    md += ["\n## Controle de instrumento (NAO e avaliacao dessas estruturas)\n",
           "As mesmas medidas nas outras ROIs, para checar se o instrumento consegue "
           "devolver outro valor. Mediana entre casos.\n",
           "| ROI | n | contiguo (degenerado) | anel externo | anel (fatias com GT) | "
           "FN<=2mm | FN<=10mm | FN mediana (mm) | FN P95 (mm) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for roi in (ROI, *ROIS_CONTROLE):
        v = ctrl.get(roi, {})
        if not v.get("n"):
            continue
        md.append(f"| {roi} | {v['n']} | {_f(v['frac_contiguo_DEGENERADO'])} | "
                  f"{_f(v['anel_externo_em_gt'])} | "
                  f"{_f(v['anel_externo_em_gt_fatias_com_gt'])} | "
                  f"{_f(v['fn_frac_ate_2mm'], 3)} | {_f(v['fn_frac_ate_10mm'], 3)} | "
                  f"{_f(v['casca_mm_mediana'], 3)} | {_f(v['casca_mm_p95'], 3)} |")
    md.append(f"\n{ctrl['leitura']}\n")
    per = r["pericardio_no_totalsegmentator"]
    md += ["\n## Pericardio no TotalSegmentator (registro, NAO executado)\n",
           f"- disponivel: `{per.get('disponivel')}`",
           f"- classes de `trunk_cavities`: `{per.get('trunk_cavities_classes')}`",
           f"- executado: `{per['executado']}` — {per['por_que_nao_executar']}",
           "\nO que faltaria para uma comparacao ontologicamente correta:"]
    md += [f"  {s}" for s in per["o_que_faltaria_para_uma_comparacao_ontologicamente_correta"]]
    md += ["\n## Nao medido\n",
           "- HD95/ASSD/NSD do coracao nesta parte (ja publicados na coorte; caros e nao "
           "necessarios para a pergunta de ontologia)",
           "- se a casca medida E pericardio: nao ha GT de pericardio neste dataset — "
           f"`{NM}`, e hipotese",
           "- `validation` e `test`: intocados nesta fase\n"]
    return "\n".join(md) + "\n"


def gravar(r: dict, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    p_json = saida / "ontologia_coracao.json"
    p_csv = saida / "ontologia_coracao.csv"
    p_md = saida / "RESUMO.md"

    p_json.write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with p_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(r["linhas"])
    p_md.write_text(_resumo_md(r), encoding="utf-8")
    log(f"gravado: {p_json}\n          {p_csv}\n          {p_md}")
    return {"json": p_json, "csv": p_csv, "md": p_md}


# -------------------------------------------------------------------------- autoteste


def _cubo(shape=(40, 40, 40), c=20, r=5) -> np.ndarray:
    m = np.zeros(shape, dtype=bool)
    m[c - r:c + r, c - r:c + r, c - r:c + r] = True
    return m


def _autoteste() -> None:
    """Autoteste com CONTROLE POSITIVO: a medida tem que FALHAR quando deveria.

    (B) e o controle que a PRIMEIRA versao do instrumento nao tinha e por isso
    nao pegou nada: um envelope e um deslocamento de fronteira precisam sair com
    NUMEROS DIFERENTES. O criterio topologico da 1,0 nos dois — o assert de (B)
    exige que o anel externo e o perfil de distancia os separem.
    """
    sp = (1.0, 1.0, 1.0)
    LPS = "LPS"  # eixo 2 = S, indice cresce em direcao superior

    # (A) envelope puro: GT = predicao engordada 2 voxels SO no plano, mesma faixa em Z.
    pred = _cubo()
    gt = binary_dilation(pred, structure=np.ones((5, 5, 1), dtype=bool))
    a = medir(pred, gt, sp, LPS)["heart_gt_definition"]
    assert a["separacao_topologica_DEGENERADA"]["frac_contiguo"] == 1.0, a
    assert a["corte_z"]["frac_corte_z"] == 0.0, a["corte_z"]
    assert a["corte_z"]["frac_envelope_lateral"] == 1.0, a["corte_z"]
    assert 1.0 <= a["distancia_radial_mm"]["p95"] <= 2.5, a["distancia_radial_mm"]
    # envelope que envolve: o anel externo esta quase todo dentro do GT
    anel_env = a["envelope_anel_externo"]["frac_anel_externo_em_gt_nas_fatias_com_gt"]
    assert anel_env > 0.9, anel_env
    print(f"(A) envelope: anel_externo={anel_env:.4f}, corte_z={a['corte_z']['frac_corte_z']}, "
          f"FN P95={a['distancia_radial_mm']['p95']:.3f} mm")

    # (B) CONTROLE POSITIVO: deslocamento de fronteira, NAO envelope. GT = a mesma
    #     predicao deslocada 3 voxels em X. Se o instrumento nao separar isto do
    #     caso (A), ele esta cego — foi exatamente o que aconteceu com a versao
    #     topologica, que da 1,0 nos dois.
    gt_b = np.roll(pred, 1, axis=0)
    b = medir(pred, gt_b, sp, LPS)["heart_gt_definition"]
    anel_desl = b["envelope_anel_externo"]["frac_anel_externo_em_gt_nas_fatias_com_gt"]
    assert b["separacao_topologica_DEGENERADA"]["frac_contiguo"] == 1.0, (
        "o criterio topologico deveria continuar cego aqui — se mudou, revise o registro")
    # o teste de envelope separa: envolver cobre o anel inteiro, deslocar cobre um lado
    assert anel_desl < 0.5 < anel_env, (anel_desl, anel_env)
    # o perfil separa CAMADA FINA de CAMADA ESPESSA: o deslocamento de 1 voxel poe todo o
    # FN a 1 mm; o envelope de 2 voxels nao. E este o contraste que aparece no dado real.
    p1_desl = b["distancia_radial_mm"]["perfil_acumulado"]["frac_ate_1mm"]
    p1_env = a["distancia_radial_mm"]["perfil_acumulado"]["frac_ate_1mm"]
    assert p1_desl == 1.0 and p1_env < 0.9, (p1_desl, p1_env)
    print(f"(B) controle positivo deslocamento: anel_externo={anel_desl:.4f} < "
          f"{anel_env:.4f} do envelope; FN<=1mm {p1_desl:.3f} vs {p1_env:.3f}; topologico "
          f"continua {b['separacao_topologica_DEGENERADA']['frac_contiguo']} nos dois (cego)")

    # (C) CONTROLE POSITIVO do eixo Z: GT so estendido 5 fatias ACIMA da predicao.
    #     Se a extensao em Z fosse ignorada, isto viria como envelope lateral.
    gt_c = pred.copy()
    gt_c[15:25, 15:25, 25:30] = True
    c = medir(pred, gt_c, sp, LPS)["heart_gt_definition"]
    assert c["corte_z"]["frac_corte_z"] == 1.0, c["corte_z"]
    assert c["corte_z"]["frac_envelope_lateral"] == 0.0, c["corte_z"]
    assert c["corte_z"]["ml_superior"] > 0 and c["corte_z"]["ml_inferior"] == 0.0, c["corte_z"]
    # o mesmo volume com o codigo de eixo invertido tem que trocar o NOME do lado
    c_i = medir(pred, gt_c, sp, "LPI")["heart_gt_definition"]["corte_z"]
    assert c_i["ml_inferior"] > 0 and c_i["ml_superior"] == 0.0, c_i
    print(f"(C) controle positivo Z: corte_z={c['corte_z']['frac_corte_z']}, "
          f"superior={c['corte_z']['ml_superior']:.3f} mL; com eixo I vira "
          f"inferior={c_i['ml_inferior']:.3f} mL")

    # (D) identidade: sem FN nenhum, as fracoes tem que sair INVALIDAS, nunca 0,0 plausivel.
    d = medir(pred, pred, sp, LPS)
    g = d["heart_gt_definition"]
    assert isinstance(g["separacao_topologica_DEGENERADA"]["frac_contiguo"], str), g
    assert isinstance(g["distancia_radial_mm"]["mediana"], str), g
    assert isinstance(g["distancia_radial_mm"]["perfil_acumulado"]["frac_ate_2mm"], str), g
    assert d["variantes"]["B_campo_completo"]["dice"] == 1.0
    assert d["variantes"]["B_campo_completo"]["recall_gt"] == 1.0
    print(f"(D) identidade: dice=1.0, frac_contiguo="
          f"{g['separacao_topologica_DEGENERADA']['frac_contiguo']!r}")

    # (E) predicao vazia: nada pode virar float plausivel.
    e = medir(np.zeros_like(pred), gt, sp, LPS)["heart_gt_definition"]
    ev = medir(np.zeros_like(pred), gt, sp, LPS)["variantes"]["B_campo_completo"]
    assert isinstance(ev["precision_pred"], str), ev
    assert isinstance(e["envelope_anel_externo"]["frac_anel_externo_em_gt"], str), e
    print(f"(E) predicao vazia: precision={ev['precision_pred']!r}, "
          f"anel={e['envelope_anel_externo']['frac_anel_externo_em_gt']!r}")

    print("ontologia_coracao.py: autoteste OK")


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Parte 14 — divergencia de DEFINICAO do coracao (Tier2). Mede, nao otimiza.")
    p.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    p.add_argument("--conjunto", default=CONJUNTO, choices=["development"],
                   help="so development: validation e test sao intocaveis nesta fase")
    p.add_argument("--saida", type=Path, default=None)
    p.add_argument("--autoteste", action="store_true")
    a = p.parse_args(argv)
    if a.autoteste:
        _autoteste()
        return 0
    r = rodar(a.raiz, a.conjunto)
    gravar(r, a.saida or SAIDA_PADRAO)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
