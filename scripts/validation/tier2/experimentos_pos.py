"""
Fase 5 / Parte 3 — experimentos de POS-PROCESSAMENTO, uma alteracao por vez.

O baseline congelado (A_BASELINE_V1) NAO tem pos-processamento nenhum: a predicao
avaliada e a saida crua do TotalSegmentator. Entao cada variante aqui e ADITIVA e
ISOLADA — aplica UMA operacao sobre a mascara predita e mede tudo de novo.

Nada fora deste arquivo foi criado ou editado. Nenhum modulo da lista congelada foi
tocado. Metricas, uniao de lobos, leitura de GT e checagem de grade sao reuso:
  segmentation_metrics.compare_masks · benchmark_tier2.recall_containment ·
  mapeamento.unir_predicao · rtstruct.carregar_mascara · geometria.verificar_alinhamento ·
  mapa_erro._recorte/_ml/_suporte_z · fase5.carregar_split/instituicao_de/ALVOS/CONTROLES

==============================================================================
TUDO QUE E CONSTANTE ESTA DECLARADO ABAIXO, ANTES DE QUALQUER EXECUCAO
==============================================================================

Nenhuma constante vem do ground truth. Nenhuma vem de "o que maximizou o Dice".
Cada uma tem a derivacao escrita ao lado. Toda operacao recebe SOMENTE mascaras
PREDITAS (assinatura sem parametro de GT) — `_autoteste` prova isso rodando as
quatro familias em arrays sinteticos, sem GT nenhum no processo.

O GT entra uma unica vez, no fim, como AVALIADOR.

------------------------------------------------------------------------------
CORTE DE CUSTO (declarado, e verificado por controle)

O custo publicado de `compare_masks` e 11,6 s por estrutura em volume cheio
(512x512x130). Aqui as duas mascaras sao recortadas na caixa que contem as duas,
com margem de 2 voxels de fundo (`mapa_erro._recorte`, MARGEM_RECORTE = 2), ANTES
de medir. Isso nao e aproximacao: dice, iou e volume dependem so de contagens, e
as distancias de superficie dependem so dos voxels de superficie, que o recorte
preserva integralmente (a margem garante fundo em volta; onde a mascara ja toca a
borda do array, o recorte tambem toca, entao a face exposta continua exposta).

Medido em LCTSC-Test-S1-101: 9,94 s -> 0,06 s (SpinalCord) e 10,06 s -> 0,53 s
(Lung_R), com TODAS as chaves de `compare_masks` identicas ate 1e-12. O controle
esta em `_autoteste` (item 6), inclusive para mascara que ENCOSTA na borda — o
caso em que um recorte ingenuo mudaria a superficie.

Consequencia: NENHUM experimento e NENHUM caso foi cortado por custo. Rodam as 10
variantes x 30 casos x 4 estruturas.
------------------------------------------------------------------------------

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_closing, binary_dilation, binary_opening, label

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.segmentation_metrics import compare_masks
from scripts.validation.tier2 import fase5, geometria, mapa_erro, mapeamento
from scripts.validation.tier2 import rtstruct as rtst
from scripts.validation.tier2.benchmark_tier2 import recall_containment

RAIZ = Path(".clinica-dados/tier2/lctsc")
SAIDA = RAIZ / "fase5" / "experimentos"
NM = "nao medido"

# Eixo de fatia. Toda a base Tier2 usa o eixo 2 (benchmark_tier2 recorta em
# `pred[:, :, :z0]`, mapa_erro._suporte_z olha `axis=(0,1)`). Nao e presumido:
# `medir_caso` ABORTA o caso se spacing[2] nao for o maior spacing.
EIXO_Z = 2


# =============================================================================
# EXP-A "component_cleanup" — ataca E4 (falso positivo localizado)
# =============================================================================
#
# DE ONDE VEM O NUMERO (nao veio do Dice, nao veio do GT):
#
# As cinco estruturas do LCTSC sao corpos anatomicamente CONTINUOS: esofago e
# medula sao tubos unicos, e cada pulmao e uma uniao de lobos que se tocam. Logo
# um componente conexo pequeno e solto nao pode ser continuacao de nenhuma delas.
#
# A escala fisica que define "pequeno" e uma fatia axial da MENOR estrutura alvo:
# o esofago toracico tem diametro externo da ordem de 2 cm (anatomia de livro,
# nao medida deste dataset), logo area ~pi*(10 mm)^2 = 314 mm^2; uma fatia de
# 3,0 mm de espessura (o spacing em Z de S1/S3) vale ~0,94 mL.
#
#   PRINCIPAL = 0,5 mL  — metade de UMA fatia da menor estrutura alvo. Abaixo
#                         disso o componente nao chega a ser um corte da menor
#                         estrutura que existe aqui. Escolha conservadora: remove
#                         so o que nao pode ser orgao.
#   sensibilidade 0,1 mL — ~35 voxels de 2,86 mm^3; um cubo de ~3 voxels de lado.
#                          Piso da grade: quase nada e removido.
#   sensibilidade 2,0 mL — ~duas fatias inteiras do esofago. Agressivo de
#                          proposito, para mostrar onde a regra comeca a doer.
#
# O limiar e ABSOLUTO em mL, e nao "% do maior componente", por um motivo
# concreto: Lung_R e uniao de 3 lobos. Se as fissuras separarem os lobos, uma
# regra percentual apagaria um lobo inteiro. Um limiar absoluto de 0,5 mL nao
# ameaca um lobo (dezenas a centenas de mL).
LIMIARES_COMPONENTE_ML = (0.1, 0.5, 2.0)
LIMIAR_COMPONENTE_PRINCIPAL_ML = 0.5

# Conectividade 26 (np.ones((3,3,3))), nao 6. Declarada: 26 e a mais PERMISSIVA —
# junta o que se toca so por quina, entao produz componentes maiores e remove
# MENOS. Escolha conservadora, coerente com o limiar conservador.
CONECTIVIDADE_26 = np.ones((3, 3, 3), dtype=bool)


# =============================================================================
# EXP-B "terminacao_longitudinal" — ataca E1 (extensao indevida)
# =============================================================================
#
# A REGRA NAO VE O GT. A referencia e outra estrutura PREDITA: a uniao dos 5 lobos
# pulmonares que o proprio TotalSegmentator produziu no mesmo caso. Os pulmoes
# definem a extensao do torax sem tocar em contorno de referencia nenhum. Um caso
# sem GT nenhum roda esta regra sem alteracao — a assinatura de
# `terminacao_torax` nao tem parametro de GT (provado em `_autoteste`, item 2).
#
# MARGEM = 0,0 mm. Declarada antes de rodar, nao ajustada.
#
# PREVISAO REGISTRADA ANTES DA EXECUCAO (isto e o que torna o experimento util
# em qualquer direcao): espera-se que a regra AJUDE pouco o esofago — cujo FP de
# extensao e distal (1,48 mL, caudal, abaixo do diafragma) — e que ATRAPALHE
# muito a medula, porque a medula real continua acima do apice pulmonar e abaixo
# da base. Se a medula piorar, isso e evidencia de que a extensao da medula alem
# do GT e E6 (o contornador parou) e nao E1 (o modelo passou do ponto) — que e
# exatamente a duvida que o Diagnostico 1 deixou em aberto ao medir
# frac_campo_pred = 1,000 nas tres instituicoes.
MARGEM_TORAX_MM = 0.0

# Estruturas preditas que definem o torax. Vem de mapeamento.MAPA_LCTSC, nao de
# lista propria — se o mapeamento mudar, isto acompanha.
LOBOS_PULMONARES = tuple(sorted(set(mapeamento.MAPA_LCTSC["Lung_L"] + mapeamento.MAPA_LCTSC["Lung_R"])))


# =============================================================================
# EXP-C "preservacao_fina" — ataca E2/E3
# =============================================================================
#
# CONVENCAO UNICA, COMPARTILHADA PELAS QUATRO VARIANTES (declarada uma vez, nao e
# ajuste por variante): o elemento estruturante e AXIAL, conecta so no plano.
#
# Motivo, que e de grade e nao de resultado: o voxel do LCTSC e ~0,977 x 0,977 x
# 3,0 mm. Um elemento 6-vizinhos "isotropico em indice" desloca a fronteira 1 mm
# no plano e 3 mm em Z ao mesmo tempo — sao dois deslocamentos fisicos diferentes
# chamados de "um voxel". Alem disso, dilatar em Z ACRESCENTA extensao
# longitudinal, que e o erro do EXP-B; misturar os dois num experimento seria
# combinar duas alteracoes, o que esta proibido.
#
# O deficit de calibre medido pelo Diagnostico 1 e in-plane (razao de AREA por
# fatia: 0,907 mediana na medula), entao a operacao correspondente e in-plane.
def _elemento_axial() -> np.ndarray:
    """4-vizinhanca dentro da fatia; nenhuma conexao entre fatias."""
    e = np.zeros((3, 3, 3), dtype=bool)
    e[1, 1, 1] = True
    e[0, 1, 1] = e[2, 1, 1] = True
    e[1, 0, 1] = e[1, 2, 1] = True
    return e


ELEMENTO_AXIAL = _elemento_axial()

# FRACAO_CALIBRE — a unica constante da variante condicionada ao calibre local.
#
# DE ONDE VEM: da resolucao, nao do GT e nao do Dice. Um passo de dilatacao no
# plano muda a area de um disco de raio r voxels por (2r+1)/r^2. A medula tem
# ~15 mm de diametro (anatomia de livro), o que da r ~ 7,5 voxels de ~1 mm, logo
# um unico passo vale ~+28 % de area. Corrigir um deficit menor que METADE de um
# passo (~14 %) e garantir overshoot: a grade nao consegue expressar a correcao.
# Logo so vale dilatar a fatia cujo deficit ja passa disso — area abaixo de 0,85
# da area mediana da PROPRIA predicao naquele caso.
#
# A mediana e da predicao, por caso. Nao ha nada do GT nela.
FRACAO_CALIBRE = 0.85


# =============================================================================
# operacoes — todas recebem SOMENTE mascara(s) predita(s)
# =============================================================================


def component_cleanup(pred: np.ndarray, spacing, limiar_ml: float) -> np.ndarray:
    """Remove componentes conexos com volume abaixo de `limiar_ml`. EXP-A / E4."""
    if not pred.any():
        return pred
    voxel_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    rot, n = label(pred, structure=CONECTIVIDADE_26)
    if n <= 1:
        return pred
    # bincount[0] e o fundo; indice i+1 e o componente i+1
    tamanhos = np.bincount(rot.ravel())
    # mesma conta de mapa_erro._ml, vetorizada (aquela e escalar-only)
    manter = (tamanhos * voxel_mm3 / 1000.0) >= limiar_ml
    manter[0] = False
    return manter[rot]


def extensao_z_torax(pulmoes: np.ndarray, spacing, margem_mm: float = MARGEM_TORAX_MM):
    """(z0, z1) da janela toracica, derivada SO da predicao dos lobos pulmonares.

    Devolve None se nao houver pulmao predito — nesse caso a regra se declara
    inaplicavel em vez de inventar uma janela.
    """
    z0, z1, n = mapa_erro._suporte_z(pulmoes)
    if n == 0:
        return None
    passo = float(np.asarray(spacing, dtype=float)[EIXO_Z])
    folga = int(np.floor(margem_mm / passo)) if passo > 0 else 0
    return (max(z0 - folga, 0), min(z1 + folga, pulmoes.shape[EIXO_Z] - 1))


def terminacao_torax(pred: np.ndarray, pulmoes: np.ndarray, spacing,
                     margem_mm: float = MARGEM_TORAX_MM) -> np.ndarray:
    """Zera a predicao fora da extensao em Z dos PULMOES PREDITOS. EXP-B / E1.

    Sem parametro de GT, de proposito: a regra roda num caso que nao tem GT nenhum.
    """
    janela = extensao_z_torax(pulmoes, spacing, margem_mm)
    if janela is None:
        return pred
    z0, z1 = janela
    fora = np.zeros(pred.shape[EIXO_Z], dtype=bool)
    fora[:z0] = True
    fora[z1 + 1:] = True
    saida = pred.copy()
    saida[:, :, fora] = False
    return saida


def dilatacao_axial(pred: np.ndarray) -> np.ndarray:
    """Dilatacao de 1 voxel NO PLANO. EXP-C variante 1 / E2."""
    return binary_dilation(pred, structure=ELEMENTO_AXIAL, border_value=0)


def fechamento_axial(pred: np.ndarray) -> np.ndarray:
    """Fechamento morfologico no plano (dilata, depois erode). EXP-C variante 2 / E3."""
    return binary_closing(pred, structure=ELEMENTO_AXIAL, border_value=0)


def abertura_axial(pred: np.ndarray) -> np.ndarray:
    """Abertura morfologica no plano (erode, depois dilata). EXP-C variante 3 / E3."""
    return binary_opening(pred, structure=ELEMENTO_AXIAL, border_value=0)


def dilatacao_por_calibre(pred: np.ndarray, fracao: float = FRACAO_CALIBRE) -> np.ndarray:
    """Dilata no plano SO as fatias cuja area esta abaixo de `fracao` x mediana propria.

    A mediana e a das fatias NAO VAZIAS da propria predicao. EXP-C variante 4 / E2.
    """
    areas = pred.sum(axis=(0, 1))
    nao_vazias = areas[areas > 0]
    if nao_vazias.size == 0:
        return pred
    limiar = float(np.median(nao_vazias)) * fracao
    estreitas = (areas > 0) & (areas < limiar)
    if not estreitas.any():
        return pred
    saida = pred.copy()
    saida[:, :, estreitas] = binary_dilation(
        pred[:, :, estreitas], structure=ELEMENTO_AXIAL, border_value=0
    )
    return saida


# ---------------------------------------------------------------------- catalogo


# (nome, experimento, tipo_de_erro, funcao(pred, ctx) -> pred). `ctx` traz spacing
# e a uniao de lobos PREDITA. Nada mais. Nenhuma funcao recebe GT.
VARIANTES: list[tuple[str, str, str, object]] = [
    ("baseline", "—", "—", lambda p, c: p),
    *[
        (f"A_comp_{lim:g}mL", "EXP-A component_cleanup", "E4",
         (lambda lim: (lambda p, c: component_cleanup(p, c["spacing"], lim)))(lim))
        for lim in LIMIARES_COMPONENTE_ML
    ],
    ("B_terminacao_torax", "EXP-B terminacao_longitudinal", "E1",
     lambda p, c: terminacao_torax(p, c["pulmoes"], c["spacing"])),
    ("C_dilatacao", "EXP-C preservacao_fina", "E2", lambda p, c: dilatacao_axial(p)),
    ("C_fechamento", "EXP-C preservacao_fina", "E3", lambda p, c: fechamento_axial(p)),
    ("C_abertura", "EXP-C preservacao_fina", "E3", lambda p, c: abertura_axial(p)),
    ("C_calibre", "EXP-C preservacao_fina", "E2", lambda p, c: dilatacao_por_calibre(p)),
]

VARIANTE_PRINCIPAL_A = f"A_comp_{LIMIAR_COMPONENTE_PRINCIPAL_ML:g}mL"


# =============================================================================
# medida
# =============================================================================


def _metricas(pred: np.ndarray, gt: np.ndarray, spacing) -> dict:
    """compare_masks + recall_containment + FP/FN em mL, no recorte comum."""
    voxel_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    cortes, _ = mapa_erro._recorte(pred, gt)
    p, g = pred[cortes], gt[cortes]
    m = compare_masks(p, g, spacing)
    rc = recall_containment(p, g)
    fp = int(np.count_nonzero(p & ~g))
    fn = int(np.count_nonzero(~p & g))
    return {
        "dice": m["dice"], "iou": m["iou"],
        "hd95_mm": m["hd95_mm"], "assd_mm": m["assd_mm"],
        "nsd_1vox": m["nsd_1vox"], "volume_error_pct": m["volume_error_pct"],
        "fp_ml": mapa_erro._ml(fp, voxel_mm3), "fn_ml": mapa_erro._ml(fn, voxel_mm3),
        "precision": rc["precision_pred"], "recall": rc["recall_gt"],
        "voxels_pred": int(p.sum()), "voxels_gt": int(g.sum()),
    }


def medir_caso(caso: str, raiz: Path = RAIZ, log=print) -> list[dict]:
    """Todas as variantes x todas as estruturas de UM caso."""
    d = Path(raiz) / caso
    dir_gt, dir_pred = d / "gt", d / "pred_masks"
    spacing = tuple(geometria.descrever_nifti(dir_gt / rtst.NOME_IMAGEM)["zooms_mm"])

    # o eixo de fatia nao e presumido: se o eixo 2 nao for o mais grosso, aborta.
    if abs(spacing[EIXO_Z] - max(spacing)) > 1e-6:
        raise RuntimeError(
            f"{caso}: spacing {spacing} — o eixo {EIXO_Z} nao e o de fatia; "
            "as regras longitudinais e o elemento axial seriam invalidos"
        )

    pulmoes, _ = mapeamento.unir_predicao(dir_pred, LOBOS_PULMONARES)
    ctx = {"spacing": spacing, "pulmoes": pulmoes}

    estruturas = list(fase5.ALVOS) + list(fase5.CONTROLES)
    linhas: list[dict] = []
    for roi in estruturas:
        alvos = mapeamento.MAPA_LCTSC[roi]
        caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{roi}.nii.gz"
        # OBRIGATORIO antes de medir (a grade e verificada, nao presumida)
        for n in alvos:
            geometria.verificar_alinhamento(dir_pred / f"{n}.nii.gz", caminho_gt)

        gt = rtst.carregar_mascara(caminho_gt)
        base, _ = mapeamento.unir_predicao(dir_pred, alvos)

        cache: dict[bytes, dict] = {}
        for nome, exp, erro, fn in VARIANTES:
            pred = np.asarray(fn(base, ctx), dtype=bool)
            # mascaras identicas produzem metricas identicas por construcao; a
            # chave e o conteudo (hash de 256 bits do buffer), entao isto nao e
            # aproximacao nenhuma — so evita recalcular a mesma medida.
            chave = hashlib.blake2b(pred.tobytes(), digest_size=32).digest()
            if chave not in cache:
                cache[chave] = _metricas(pred, gt, spacing)
            linhas.append({
                "case_id": caso, "instituicao": fase5.instituicao_de(caso),
                "estrutura": roi,
                "papel": "alvo" if roi in fase5.ALVOS else "controle",
                "variante": nome, "experimento": exp, "tipo_de_erro": erro,
                "identica_ao_baseline": bool(np.array_equal(pred, base)),
                "spacing_mm": list(spacing),
                **cache[chave],
            })
        log(f"  {caso}/{roi}: {len(VARIANTES)} variantes")
    return linhas


# =============================================================================
# agregacao
# =============================================================================


def _med(vals) -> float | str:
    v = [x for x in vals if isinstance(x, (int, float)) and np.isfinite(x)]
    return float(np.median(v)) if v else "invalido: nenhum valor finito"


def _delta_pareado(linhas: list[dict], variante: str, estrutura: str, campo: str,
                   subset: list[str] | None = None) -> float | str:
    """Mediana das diferencas POR CASO (variante - baseline). Pareado, nao entre medianas."""
    base = {l["case_id"]: l[campo] for l in linhas
            if l["variante"] == "baseline" and l["estrutura"] == estrutura}
    d = []
    for l in linhas:
        if l["variante"] != variante or l["estrutura"] != estrutura:
            continue
        if subset is not None and l["case_id"] not in subset:
            continue
        b = base.get(l["case_id"])
        if isinstance(b, (int, float)) and isinstance(l[campo], (int, float)) \
                and np.isfinite(b) and np.isfinite(l[campo]):
            d.append(l[campo] - b)
    return float(np.median(d)) if d else "invalido: nenhum par valido"


def _max_abs_delta(linhas: list[dict], variante: str, estrutura: str, campo: str) -> float | str:
    """Maior |diferenca| POR CASO. Mostra o efeito que a mediana esconde."""
    base = {l["case_id"]: l[campo] for l in linhas
            if l["variante"] == "baseline" and l["estrutura"] == estrutura}
    d = [abs(l[campo] - base[l["case_id"]]) for l in linhas
         if l["variante"] == variante and l["estrutura"] == estrutura
         and l["case_id"] in base
         and isinstance(base[l["case_id"]], (int, float)) and isinstance(l[campo], (int, float))
         and np.isfinite(base[l["case_id"]]) and np.isfinite(l[campo])]
    return float(max(d)) if d else "invalido: nenhum par valido"


def _delta_volume_abs(linhas: list[dict], variante: str, estrutura: str,
                      subset: list[str] | None = None) -> float | str:
    """Mediana de (|erro_vol variante| - |erro_vol baseline|) por caso, em pontos %."""
    base = {l["case_id"]: l["volume_error_pct"] for l in linhas
            if l["variante"] == "baseline" and l["estrutura"] == estrutura}
    d = []
    for l in linhas:
        if l["variante"] != variante or l["estrutura"] != estrutura:
            continue
        if subset is not None and l["case_id"] not in subset:
            continue
        b = base.get(l["case_id"])
        if isinstance(b, (int, float)) and np.isfinite(b) and np.isfinite(l["volume_error_pct"]):
            d.append(abs(l["volume_error_pct"]) - abs(b))
    return float(np.median(d)) if d else "invalido: nenhum par valido"


def _regride(dd, dh, dv) -> list[str]:
    """Flags de regressao pelos criterios de fase5.py, sem limiar novo."""
    f = []
    if isinstance(dd, float) and dd <= -fase5.LIMIAR_REGRESSAO_DICE:
        f.append("dice")
    if isinstance(dh, float) and dh >= fase5.LIMIAR_REGRESSAO_HD95_MM:
        f.append("hd95")
    if isinstance(dv, float) and dv >= fase5.LIMIAR_REGRESSAO_VOLUME_PCT:
        f.append("volume")
    return f


def classificar(linhas: list[dict], variante: str) -> dict:
    """ADOTAVEL / PROMISSORA / SEM EVIDENCIA / REJEITADA — pelos criterios declarados.

    ADOTAVEL EXIGE HOLDOUT, que NAO roda nesta tarefa. O teto emitido aqui e
    PROMISSORA, sempre — nenhuma variante pode sair ADOTAVEL deste modulo.
    """
    alvo_ganha, alvo_regride, controle_regride = [], [], []
    for roi in fase5.ALVOS:
        dd = _delta_pareado(linhas, variante, roi, "dice")
        dh = _delta_pareado(linhas, variante, roi, "hd95_mm")
        dv = _delta_volume_abs(linhas, variante, roi)
        if isinstance(dd, float) and dd >= fase5.LIMIAR_MELHORIA_DICE:
            alvo_ganha.append(roi)
        if _regride(dd, dh, dv):
            alvo_regride.append(f"{roi}:{'+'.join(_regride(dd, dh, dv))}")
    for roi in fase5.CONTROLES:
        dd = _delta_pareado(linhas, variante, roi, "dice")
        dh = _delta_pareado(linhas, variante, roi, "hd95_mm")
        dv = _delta_volume_abs(linhas, variante, roi)
        if _regride(dd, dh, dv):
            controle_regride.append(f"{roi}:{'+'.join(_regride(dd, dh, dv))}")

    suspeita = bool(alvo_ganha and controle_regride)
    if alvo_regride:
        v = "REJEITADA"
    elif suspeita:
        v = "REJEITADA"
    elif controle_regride:
        v = "REJEITADA"
    elif alvo_ganha:
        v = "PROMISSORA"
    else:
        v = "SEM EVIDENCIA"
    return {
        "variante": variante, "classificacao": v,
        "teto_desta_tarefa": "PROMISSORA (ADOTAVEL exige holdout, que nao roda aqui)",
        "alvos_com_ganho": alvo_ganha,
        "alvos_com_regressao": alvo_regride,
        "controles_com_regressao": controle_regride,
        "SUSPEITA_ganho_no_alvo_com_regressao_no_controle": suspeita,
    }


def resumir(linhas: list[dict]) -> dict:
    casos = sorted({l["case_id"] for l in linhas})
    insts = sorted({l["instituicao"] for l in linhas})
    campos = ("dice", "hd95_mm", "assd_mm", "assd_mm", "volume_error_pct",
              "fp_ml", "fn_ml", "iou", "precision", "recall", "nsd_1vox")
    matriz = []
    for nome, exp, erro, _ in VARIANTES:
        for roi in list(fase5.ALVOS) + list(fase5.CONTROLES):
            sel = [l for l in linhas if l["variante"] == nome and l["estrutura"] == roi]
            b = [l for l in linhas if l["variante"] == "baseline" and l["estrutura"] == roi]
            matriz.append({
                "variante": nome, "experimento": exp, "tipo_de_erro": erro,
                "estrutura": roi,
                "papel": "alvo" if roi in fase5.ALVOS else "controle",
                "n": len(sel),
                "n_identicas_ao_baseline": sum(1 for l in sel if l["identica_ao_baseline"]),
                # A mediana de 30 casos e 0,0000 sempre que a operacao mexeu em
                # menos de metade deles. Estas duas colunas impedem que "delta
                # mediano zero" seja lido como "a operacao nao fez nada".
                "n_casos_alterados": len(sel) - sum(1 for l in sel if l["identica_ao_baseline"]),
                "max_abs_delta_dice_por_caso": _max_abs_delta(linhas, nome, roi, "dice"),
                **{f"base_{c}": _med([l[c] for l in b]) for c in dict.fromkeys(campos)},
                **{f"var_{c}": _med([l[c] for l in sel]) for c in dict.fromkeys(campos)},
                "delta_dice_pareado": _delta_pareado(linhas, nome, roi, "dice"),
                "delta_hd95_pareado": _delta_pareado(linhas, nome, roi, "hd95_mm"),
                "delta_assd_pareado": _delta_pareado(linhas, nome, roi, "assd_mm"),
                "delta_fp_ml_pareado": _delta_pareado(linhas, nome, roi, "fp_ml"),
                "delta_fn_ml_pareado": _delta_pareado(linhas, nome, roi, "fn_ml"),
                "delta_volume_abs_pp": _delta_volume_abs(linhas, nome, roi),
                "regressao": _regride(
                    _delta_pareado(linhas, nome, roi, "dice"),
                    _delta_pareado(linhas, nome, roi, "hd95_mm"),
                    _delta_volume_abs(linhas, nome, roi),
                ),
                "por_instituicao": {
                    i: {
                        "n": sum(1 for l in sel if l["instituicao"] == i),
                        "dice": _med([l["dice"] for l in sel if l["instituicao"] == i]),
                        "delta_dice_pareado": _delta_pareado(
                            linhas, nome, roi, "dice",
                            subset=[c for c in casos if fase5.instituicao_de(c) == i]),
                    } for i in insts
                },
            })
    return {
        "n_casos": len(casos), "casos": casos, "instituicoes": insts,
        "conjunto": "development (holdout validation/test NAO lido)",
        "constantes_declaradas": {
            "limiares_componente_ml": list(LIMIARES_COMPONENTE_ML),
            "limiar_componente_principal_ml": LIMIAR_COMPONENTE_PRINCIPAL_ML,
            "conectividade": "26 (np.ones((3,3,3)))",
            "margem_torax_mm": MARGEM_TORAX_MM,
            "fracao_calibre": FRACAO_CALIBRE,
            "elemento_estruturante": "axial (4-vizinhanca no plano, sem conexao em Z)",
            "criterios_de_fase5": {
                "melhoria_dice": fase5.LIMIAR_MELHORIA_DICE,
                "regressao_dice": fase5.LIMIAR_REGRESSAO_DICE,
                "regressao_hd95_mm": fase5.LIMIAR_REGRESSAO_HD95_MM,
                "regressao_volume_pct": fase5.LIMIAR_REGRESSAO_VOLUME_PCT,
            },
        },
        "matriz": matriz,
        "classificacao": [classificar(linhas, n) for n, _, _, _ in VARIANTES if n != "baseline"],
    }


# =============================================================================
# saida
# =============================================================================


def _f(v, casas=4) -> str:
    if isinstance(v, bool):
        return "sim" if v else "nao"
    if isinstance(v, (int, float)) and np.isfinite(v):
        return f"{v:.{casas}f}".replace(".", ",")
    return str(v)


def _summary_md(r: dict) -> str:
    L = [
        "# Fase 5 / Parte 3 — pos-processamento (development, n = %d)" % r["n_casos"],
        "",
        "Conjunto: **development**. `validation` e `test` nao foram lidos.",
        "Toda constante esta declarada no topo de `experimentos_pos.py`, com a derivacao,",
        "e nenhuma vem do GT nem do resultado. **Teto desta tarefa: PROMISSORA** —",
        "ADOTAVEL exige holdout, que nao roda aqui.",
        "",
        "## Matriz (Parte 19) — cada linha traz o baseline ao lado",
        "",
        "Δ e sempre PAREADO: mediana das diferencas caso a caso (variante - baseline),",
        "nao diferenca entre medianas. `casos alterados` e quantos dos 30 a operacao",
        "de fato mudou; onde ele e pequeno, o Δ mediano e 0,0000 **por construcao** e a",
        "coluna `max\\|Δdice\\|` e a unica que mostra o tamanho real do efeito.",
        "",
        "| experimento | variante | estrutura | papel | casos alterados | dice base | dice var | Δdice | max\\|Δdice\\| | Δhd95 mm | Δassd mm | ΔFP mL | ΔFN mL | Δ\\|vol\\| pp | regressao |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m in r["matriz"]:
        if m["variante"] == "baseline":
            continue
        L.append("| {} | {} | {} | {} | {}/{} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            m["experimento"], m["variante"], m["estrutura"], m["papel"],
            m["n_casos_alterados"], m["n"],
            _f(m["base_dice"]), _f(m["var_dice"]), _f(m["delta_dice_pareado"]),
            _f(m["max_abs_delta_dice_por_caso"], 5),
            _f(m["delta_hd95_pareado"], 3), _f(m["delta_assd_pareado"], 3),
            _f(m["delta_fp_ml_pareado"], 3), _f(m["delta_fn_ml_pareado"], 3),
            _f(m["delta_volume_abs_pp"], 2),
            "+".join(m["regressao"]) if m["regressao"] else "—"))

    L += ["", "## Baseline medido aqui (referencia das linhas acima)", "",
          "| estrutura | papel | dice | hd95 mm | assd mm | FP mL | FN mL | vol % | iou | precision | recall | nsd_1vox |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in r["matriz"]:
        if m["variante"] != "baseline":
            continue
        L.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            m["estrutura"], m["papel"], _f(m["base_dice"]), _f(m["base_hd95_mm"], 3),
            _f(m["base_assd_mm"], 3), _f(m["base_fp_ml"], 3), _f(m["base_fn_ml"], 3),
            _f(m["base_volume_error_pct"], 2), _f(m["base_iou"]),
            _f(m["base_precision"]), _f(m["base_recall"]), _f(m["base_nsd_1vox"])))

    L += ["", "## Classificacao", "",
          "| variante | classificacao | alvos com ganho | alvos com regressao | controles com regressao | SUSPEITA |",
          "|---|---|---|---|---|---|"]
    for c in r["classificacao"]:
        L.append("| {} | **{}** | {} | {} | {} | {} |".format(
            c["variante"], c["classificacao"],
            ", ".join(c["alvos_com_ganho"]) or "—",
            ", ".join(c["alvos_com_regressao"]) or "—",
            ", ".join(c["controles_com_regressao"]) or "—",
            "SIM" if c["SUSPEITA_ganho_no_alvo_com_regressao_no_controle"] else "nao"))

    L += ["", "## Δdice pareado por instituicao (Parte 9)", "",
          "| variante | estrutura | " + " | ".join(r["instituicoes"]) + " | amplitude |",
          "|---|---|" + "---|" * (len(r["instituicoes"]) + 1)]
    for m in r["matriz"]:
        if m["variante"] == "baseline":
            continue
        vals = [m["por_instituicao"][i]["delta_dice_pareado"] for i in r["instituicoes"]]
        fin = [v for v in vals if isinstance(v, float)]
        amp = _f(max(fin) - min(fin)) if len(fin) > 1 else NM
        L.append("| {} | {} | {} | {} |".format(
            m["variante"], m["estrutura"], " | ".join(_f(v) for v in vals), amp))
    return "\n".join(L) + "\n"


def gravar(linhas: list[dict], resumo: dict, saida: Path = SAIDA, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    campos = list(linhas[0].keys())
    with (saida / "experimentos_pos.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for l in linhas:
            w.writerow({k: (json.dumps(v) if isinstance(v, list) else v) for k, v in l.items()})
    (saida / "experimentos_pos.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (saida / "RESUMO.md").write_text(_summary_md(resumo), encoding="utf-8")
    log(f"gravado em {saida}")
    return {"csv": saida / "experimentos_pos.csv", "json": saida / "experimentos_pos.json"}


# =============================================================================
# autoteste — CONTROLE POSITIVO: cada check TEM que falhar quando deveria falhar
# =============================================================================


def _autoteste() -> None:
    sp = (1.0, 1.0, 3.0)
    voxel_mm3 = float(np.prod(sp))

    # ---- 1. component_cleanup remove o pequeno e mantem o grande
    a = np.zeros((40, 40, 20), dtype=bool)
    a[5:15, 5:15, 5:15] = True          # 1000 voxels = 3,0 mL
    a[30:32, 30:32, 2:4] = True         # 8 voxels = 0,024 mL
    grande = mapa_erro._ml(1000, voxel_mm3)
    pequeno = mapa_erro._ml(8, voxel_mm3)
    assert pequeno < 0.1 < 0.5 < grande, (pequeno, grande)
    r = component_cleanup(a, sp, 0.5)
    assert r.sum() == 1000, r.sum()
    # CONTROLE POSITIVO: com limiar acima do componente grande, some TUDO
    assert component_cleanup(a, sp, grande + 1.0).sum() == 0, "limiar alto nao removeu nada"
    # CONTROLE POSITIVO: com limiar abaixo do pequeno, NADA e removido
    assert component_cleanup(a, sp, 0.001).sum() == 1008, "limiar baixo removeu algo"
    # conectividade 26: dois cubos que so se tocam por quina sao UM componente
    q = np.zeros((10, 10, 10), dtype=bool)
    q[2:4, 2:4, 2:4] = True
    q[4:6, 4:6, 4:6] = True
    assert label(q, structure=CONECTIVIDADE_26)[1] == 1, "26-conectividade nao juntou a quina"
    assert label(q)[1] == 2, "6-conectividade deveria separar — controle do controle"

    # ---- 2. terminacao_torax: so ve predicao, e trunca o que esta fora
    pulm = np.zeros((20, 20, 30), dtype=bool)
    pulm[5:15, 5:15, 10:20] = True                  # torax = fatias 10..19
    tubo = np.zeros((20, 20, 30), dtype=bool)
    tubo[9:11, 9:11, 0:30] = True                   # atravessa o volume inteiro
    t = terminacao_torax(tubo, pulm, sp)
    assert mapa_erro._suporte_z(t) == (10, 19, 10), mapa_erro._suporte_z(t)
    # CONTROLE POSITIVO: quem ja esta dentro da janela nao muda
    dentro = np.zeros_like(tubo); dentro[9:11, 9:11, 12:16] = True
    assert np.array_equal(terminacao_torax(dentro, pulm, sp), dentro), "truncou o que estava dentro"
    # CONTROLE POSITIVO: sem pulmao predito a regra se declara inaplicavel, nao zera
    assert np.array_equal(terminacao_torax(tubo, np.zeros_like(pulm), sp), tubo)
    # a regra roda SEM GT: nenhuma das chamadas acima recebeu ground truth
    import inspect
    for f in (component_cleanup, terminacao_torax, dilatacao_axial, fechamento_axial,
              abertura_axial, dilatacao_por_calibre, extensao_z_torax):
        ps = set(inspect.signature(f).parameters)
        assert not (ps & {"gt", "ground_truth", "referencia"}), f"{f.__name__} recebe GT"

    # ---- 3. elemento axial nao mexe em Z
    fatia = np.zeros((20, 20, 10), dtype=bool)
    fatia[9:11, 9:11, 4:6] = True
    d = dilatacao_axial(fatia)
    assert d.sum() > fatia.sum(), "dilatacao nao dilatou"
    assert mapa_erro._suporte_z(d) == mapa_erro._suporte_z(fatia), "dilatacao axial vazou em Z"
    # CONTROLE POSITIVO: com elemento 3D a extensao em Z MUDA — prova que o check pega
    d3 = binary_dilation(fatia, structure=None, border_value=0)
    assert mapa_erro._suporte_z(d3) != mapa_erro._suporte_z(fatia), "o check de Z nao detecta nada"

    # ---- 4. fechamento fecha buraco no plano; abertura remove espicula fina
    c = np.zeros((20, 20, 5), dtype=bool)
    c[5:12, 5:12, 2] = True
    c[8, 8, 2] = False                              # buraco de 1 voxel
    assert fechamento_axial(c)[8, 8, 2], "fechamento nao fechou o buraco"
    o = np.zeros((20, 20, 5), dtype=bool)
    o[5:12, 5:12, 2] = True
    o[13:16, 8, 2] = True                           # espicula de 1 voxel de largura
    ab = abertura_axial(o)
    assert not ab[14, 8, 2], "abertura nao removeu a espicula"
    assert ab[8, 8, 2], "abertura comeu o corpo"
    # CONTROLE POSITIVO: abertura NAO deve remover corpo espesso
    assert abertura_axial(c).sum() >= c.sum() - 12, "abertura destruiu bloco espesso"

    # ---- 5. calibre: dilata so as fatias estreitas
    k = np.zeros((30, 30, 6), dtype=bool)
    for z in range(6):
        k[13:17, 13:17, z] = True                   # 16 voxels: fatias "normais"
    k[14:16, 14:16, 3] = True
    k[13:17, 13:17, 3] = False
    k[14:16, 14:16, 3] = True                       # 4 voxels: fatia estreita (25 % da mediana)
    areas0 = k.sum(axis=(0, 1))
    kc = dilatacao_por_calibre(k)
    areas1 = kc.sum(axis=(0, 1))
    assert areas1[3] > areas0[3], "fatia estreita nao foi dilatada"
    assert all(areas1[z] == areas0[z] for z in (0, 1, 2, 4, 5)), "dilatou fatia que nao era estreita"
    # CONTROLE POSITIVO: tubo de calibre CONSTANTE nao pode ser tocado
    u = np.zeros((30, 30, 6), dtype=bool)
    u[13:17, 13:17, :] = True
    assert np.array_equal(dilatacao_por_calibre(u), u), "dilatou tubo de calibre constante"

    # ---- 6. o recorte usado por _metricas nao muda metrica nenhuma
    rng = np.random.default_rng(0)
    for encosta in (False, True):
        g = np.zeros((24, 24, 12), dtype=bool)
        g[6:16, 6:16, 3:9] = True
        p = np.zeros_like(g)
        p[7:18, 5:15, 2:8] = True
        if encosta:                                  # mascara TOCANDO a borda do array
            g[0:4, 0:4, 0:3] = True
            p[0:4, 0:4, 0:3] = True
        p ^= (rng.random(p.shape) < 0.01)            # ruido, para nao medir so blocos
        cheio = compare_masks(p, g, sp)
        cortes, _ = mapa_erro._recorte(p, g)
        rec = compare_masks(p[cortes], g[cortes], sp)
        for kk in cheio:
            if isinstance(cheio[kk], float):
                assert abs(cheio[kk] - rec[kk]) < 1e-9, (encosta, kk, cheio[kk], rec[kk])

    # ---- 7. a classificacao nao emite ADOTAVEL nem com ganho enorme
    falso = []
    for cid in [f"C{i}" for i in range(10)]:
        for roi in list(fase5.ALVOS) + list(fase5.CONTROLES):
            for nome, d in (("baseline", 0.50), ("C_dilatacao", 0.90)):
                falso.append({"case_id": cid, "instituicao": "S1", "estrutura": roi,
                              "variante": nome, "dice": d, "hd95_mm": 1.0,
                              "assd_mm": 1.0, "volume_error_pct": 0.0})
    c = classificar(falso, "C_dilatacao")
    assert c["classificacao"] == "PROMISSORA", c
    assert "ADOTAVEL" not in json.dumps(c["classificacao"]), c
    # CONTROLE POSITIVO: ganho no alvo + queda no controle => REJEITADA e SUSPEITA
    for l in falso:
        if l["estrutura"] in fase5.CONTROLES and l["variante"] == "C_dilatacao":
            l["dice"] = 0.40
    c2 = classificar(falso, "C_dilatacao")
    assert c2["classificacao"] == "REJEITADA", c2
    assert c2["SUSPEITA_ganho_no_alvo_com_regressao_no_controle"], c2

    print("experimentos_pos.py: autoteste OK (7 blocos, com controle positivo em cada)")


# =============================================================================


def rodar(raiz: Path = RAIZ, saida: Path = SAIDA, log=print) -> dict:
    split = fase5.carregar_split(raiz)
    casos = split["development"]          # SO development. validation/test intocados.
    log(f"development: {len(casos)} casos · {len(VARIANTES)} variantes · "
        f"{len(fase5.ALVOS) + len(fase5.CONTROLES)} estruturas")
    t0 = time.time()
    linhas: list[dict] = []
    for i, caso in enumerate(casos, 1):
        t = time.time()
        linhas.extend(medir_caso(caso, raiz, log=lambda *_: None))
        log(f"[{i}/{len(casos)}] {caso}: {time.time() - t:.1f}s")
    resumo = resumir(linhas)
    resumo["custo_s"] = round(time.time() - t0, 1)
    resumo["n_medidas"] = len(linhas)
    gravar(linhas, resumo, saida, log)
    return resumo


def reagregar(saida: Path = SAIDA, log=print) -> dict:
    """Reconstroi JSON + RESUMO.md a partir do CSV ja medido. NAO remede nada.

    Existe para que mudar a APRESENTACAO nao custe outra passagem de 45 min e,
    principalmente, para que nao haja tentacao de remedir depois de ver o
    resultado. Os numeros sao os mesmos bytes gravados na primeira execucao.
    """
    numericos = ("dice", "iou", "hd95_mm", "assd_mm", "nsd_1vox", "volume_error_pct",
                 "fp_ml", "fn_ml", "precision", "recall")
    linhas = []
    with (Path(saida) / "experimentos_pos.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            l = dict(row)
            l["identica_ao_baseline"] = row["identica_ao_baseline"] == "True"
            for c in numericos:
                try:
                    l[c] = float(row[c])
                except ValueError:
                    pass  # "invalido: ..." fica string, de proposito
            linhas.append(l)
    resumo = resumir(linhas)
    resumo["reagregado_de"] = "experimentos_pos.csv (sem remedir)"
    gravar(linhas, resumo, saida, log)
    return resumo


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    elif "--reagregar" in sys.argv:
        _autoteste()
        reagregar()
    else:
        _autoteste()
        rodar()
