"""Fase 10, Partes 6 a 9 — o baseline no lado B e a ASSOCIACAO erro x estilo.

PERGUNTA DESTA ETAPA: quando o GT e mais largo, mais estreito, mais curto ou de
area transversal maior, o erro do BASELINE_ESOFAGO_V1 acompanha? Se acompanhar,
parte do erro segue a CONVENCAO DE CONTORNO e nao a capacidade do modelo.

Este arquivo NAO treina, NAO altera o BASELINE_ESOFAGO_V1 e NAO escolhe modelo,
hiperparametro nem limiar. Ele faz quatro coisas:

  Parte 6 — RODA o baseline congelado nos 25 casos ja adquiridos do
            NSCLC-Radiomics. E analise EXPLORATORIA previamente autorizada: o
            numero que sai aqui NAO pode escolher nada, e isso vai gravado no
            proprio JSON de saida. Os 30 casos do LCTSC `development` sao
            REUSADOS de fase7/esofago/baseline/ — nao sao remedidos.

            A predicao e produzida com o roi_subset DE 8 ESTRUTURAS do baseline,
            nao com o de 3 do `aux_masks`: a fase 7 mediu que trocar o
            roi_subset MUDA a predicao do esofago (Dice mediano 0,9382 entre as
            duas, deslocamento de 0,0084 de Dice contra o GT). Usar o aux seria
            comparar o lado B com outro modelo.

  Parte 7 — ASSOCIACAO por correlacao de posto (Spearman), com o n de cada uma,
            dentro de cada grupo e no conjunto todo. Quatro pares DECLARADOS
            antes de olhar: erro de volume x largura efetiva; erro lateral x
            area transversal; dice x calibre; hd95 x comprimento.

            A palavra CAUSA nao aparece neste arquivo e nao pode aparecer na
            leitura: correlacao de posto entre duas descricoes do mesmo caso e
            ASSOCIACAO, e o desenho e observacional.

  Parte 8 — MODELO NULO GEOMETRICO, e so na parte em que ele nao vaza. O nulo
            ESPACIAL (envelope mediano, perfil longitudinal) NAO foi construido,
            e o motivo esta em `parte8.nulo_espacial`: ele precisa de uma
            POSICAO, e toda fonte de posicao disponivel aqui e o proprio GT
            (circular) ou uma rede (deixa de ser nulo). O nulo ESCALAR — prever
            volume e calibre pela mediana do OUTRO grupo — nao precisa de
            posicao, e por isso e o unico que foi feito.

  Parte 9 — CLASSIFICACAO (A/B/C/D), com o numero que a sustenta.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.associacao_esofago --autoteste
    python -m scripts.validation.tier2.associacao_esofago --baseline-b
    python -m scripts.validation.tier2.associacao_esofago --associacao
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
from scipy import ndimage, stats

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import baseline_esofago as bl  # noqa: E402
from scripts.validation.tier2 import estilo_esofago as est  # noqa: E402
from scripts.validation.tier2 import fase5, geometria, mapeamento  # noqa: E402
from scripts.validation.tier2 import rtstruct as rtst  # noqa: E402

ND = "nao disponivel"
NM = "nao medido"
NA = "nao aplicavel"

RAIZ_LCTSC = est.RAIZ_LCTSC
RAIZ_NSCLC = est.RAIZ_NSCLC
SAIDA = est.SAIDA_FASE10 / "associacao"
BASELINE_A = RAIZ_LCTSC / "fase7" / "esofago" / "baseline" / "baseline_esofago.json"
MORFOLOGIA = est.SAIDA_FASE10 / "morfologia" / "morfologia_por_caso.csv"

# Declarado aqui, no codigo, e repetido na saida: nenhum numero desta fase pode
# virar criterio de escolha. Se algum dia virar, esta linha e a evidencia de que
# a escolha foi feita fora do protocolo.
ESCOPO = ("EXPLORATORIO previamente autorizado. Os numeros desta etapa NAO podem "
          "escolher modelo, hiperparametro nem limiar. Esta fase MEDE.")

ALFA = 0.05


# ======================================================= Parte 6 — o baseline

def _pred_do_baseline(pid: str, raiz: Path, log=print) -> dict[str, Any]:
    """Predicao CRUA do BASELINE_ESOFAGO_V1 para UM caso, reusada se ja existe.

    Mesma chamada da fase 7: TotalSegmentator 2.18.0, tarefa `total`, o
    roi_subset de 8 estruturas de mapeamento.roi_subset(), fast=False,
    higher_order_resampling_LEGACY=True, robust_crop=True. Nenhum default do
    baseline e tocado aqui — este modulo so CHAMA.
    """
    destino = Path(raiz) / pid / "pred_masks"
    alvo = destino / f"{bl.PRED_ESOFAGO}.nii.gz"
    if alvo.exists():
        info = json.loads((destino / "segmentacao.json").read_text(encoding="utf-8"))
        return {"status": "reusado", "info": info}

    from scripts.clinica.segmentacao import rodar_segmentacao

    imagem = Path(raiz) / pid / "gt" / rtst.NOME_IMAGEM
    info = rodar_segmentacao(imagem, destino, estruturas=mapeamento.roi_subset(),
                             fast=False, task="total", log=log)
    return {"status": "ok", "info": info}


def _conferir_roi_subset(info: dict[str, Any]) -> None:
    """O roi_subset gravado tem que ser o do baseline. Se nao for, a medida cai.

    Isto e uma tranca contra o erro mais provavel desta etapa: reaproveitar por
    engano as mascaras do `aux_masks`, que sairam de um roi_subset de 3 e por
    isso sao de OUTRA predicao (fase 7, controle_aux).
    """
    esperado = sorted(mapeamento.roi_subset())
    achado = sorted(info.get("estruturas") or [])
    if achado != esperado:
        raise est.DatasetNaoPermitido(
            f"roi_subset divergente do BASELINE_ESOFAGO_V1: achado {achado}, "
            f"esperado {esperado}. A fase 7 mediu que trocar o roi_subset muda a "
            "predicao do esofago — isto seria outro modelo, nao o baseline."
        )
    if info.get("tarefa") != "total" or info.get("fast") is not False:
        raise est.DatasetNaoPermitido(
            f"parametros de inferencia divergentes: tarefa={info.get('tarefa')!r}, "
            f"fast={info.get('fast')!r}. O baseline e task=total, fast=False."
        )


def rodar_baseline_nsclc(raiz: Path = RAIZ_NSCLC, log=print) -> dict[str, Any]:
    """Parte 6 — BASELINE_ESOFAGO_V1 nos 25 casos declarados do NSCLC.

    As metricas saem de baseline_esofago.medir_baseline: mesma funcao, mesma
    variante oficial (B, campo completo), mesmas unidades fisicas, mesma Parte K
    (verificar_alinhamento antes de qualquer numero).
    """
    decl = est.carregar_declaracao(raiz)
    aq = json.loads((Path(raiz) / "aquisicao.json").read_text(encoding="utf-8"))
    casos = [r["patient_id"] for r in aq["casos"] if r["status"] == "ok"]

    guardas = [
        est.exigir_dataset_permitido(est.COLECAO_B, casos, decl["casos"]),
        est.exigir_sem_repeticao(casos, "NSCLC"),
    ]

    linhas, falhas = [], []
    for i, pid in enumerate(casos, 1):
        log(f"[{i}/{len(casos)}] {pid}")
        try:
            r = _pred_do_baseline(pid, raiz, log=log)
            _conferir_roi_subset(r["info"])
            geo = geometria.descrever_nifti(Path(raiz) / pid / "gt" / rtst.NOME_IMAGEM)
            zooms = geo["zooms_mm"]
            est.exigir_spacing_presente(
                {"pixel_spacing_mm": list(zooms[:2]),
                 "espacamento_z_mediano_mm": zooms[2],
                 "espacamento_z_uniforme": True}, rotulo=pid)
            linha = bl.medir_baseline(pid, Path(raiz))
            linha["instituicao"] = "NSCLC"
            linha["predicao"] = r["status"]
            linhas.append(linha)
        except Exception as e:  # noqa: BLE001 — um caso perdido nao derruba os outros
            log(f"  {pid}: ABORTADO — {type(e).__name__}: {e}")
            falhas.append({"patient_id": pid, "motivo": f"{type(e).__name__}: {e}"})

    return {"colecao": est.COLECAO_B, "escopo": ESCOPO, "n": len(casos),
            "n_ok": len(linhas), "guardas": guardas, "falhas": falhas,
            "baseline_id": "BASELINE_ESOFAGO_V1",
            "roi_subset": mapeamento.roi_subset(),
            "por_caso": linhas}


# ================================== instrumento NOVO: deslocamento lateral

def deslocamento_lateral_mm(gt: np.ndarray, pred: np.ndarray, zooms) -> dict[str, Any]:
    """ERRO LATERAL: distancia NO PLANO entre os centroides do GT e da predicao.

    Fatia a fatia, so nas fatias em que as DUAS mascaras tem voxel — uma fatia
    em que so uma existe e erro de EXTENSAO, nao lateral, e ja e medida pelo
    HD95 e pelo recall. Misturar as duas coisas num numero so faria o "erro
    lateral" subir por um motivo longitudinal.

    Em mm, com o pixel spacing do proprio caso: sem isso, casos com grades
    diferentes ficariam incomparaveis (o NSCLC e o S1 tem 0,9765625 mm no plano,
    o S3 tem 1,269531 — a comparacao entre grupos exige milimetro).

    Sem nenhuma fatia em comum, devolve `nao aplicavel`, nunca 0,0: zero seria a
    leitura de "perfeitamente alinhado", que e o oposto do que aconteceu.
    """
    gt = np.asarray(gt) > 0
    pred = np.asarray(pred) > 0
    sx, sy = float(zooms[0]), float(zooms[1])
    ambos = np.flatnonzero(gt.any(axis=(0, 1)) & pred.any(axis=(0, 1)))
    if ambos.size == 0:
        return {"n_fatias_com_os_dois": 0, "mediana_mm": NA, "p90_mm": NA,
                "max_mm": NA, "frac_fatias_do_gt": 0.0}
    d = []
    for k in ambos:
        cg = ndimage.center_of_mass(gt[:, :, k])
        cp = ndimage.center_of_mass(pred[:, :, k])
        d.append(float(np.hypot((cg[0] - cp[0]) * sx, (cg[1] - cp[1]) * sy)))
    v = np.asarray(d, dtype=float)
    n_gt = int(gt.any(axis=(0, 1)).sum())
    return {"n_fatias_com_os_dois": int(v.size),
            "mediana_mm": float(np.median(v)),
            "p90_mm": float(np.percentile(v, 90)),
            "max_mm": float(v.max()),
            "frac_fatias_do_gt": float(v.size / n_gt) if n_gt else NA}


def medir_predicao_congelada(caso: str, raiz: Path) -> dict[str, Any]:
    """Erro lateral e calibre PREDITO de UM caso, sobre a predicao ja em disco.

    Nao roda modelo. Le `pred_masks/esophagus.nii.gz`, que e a saida crua do
    baseline — na fase 7 para o LCTSC, na Parte 6 para o NSCLC.

    O calibre da PREDICAO sai daqui (mesmo instrumento do GT na Parte 3, o
    `_largura_efetiva_vetor` da fase 10) porque a Parte 8 precisa comparar o
    calibre que a rede entregou com o que uma constante do outro grupo entregaria.
    """
    dir_gt = Path(raiz) / caso / "gt"
    caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{bl.ROI_GT}.nii.gz"
    caminho_pred = Path(raiz) / caso / "pred_masks" / f"{bl.PRED_ESOFAGO}.nii.gz"
    geometria.verificar_alinhamento(caminho_pred, caminho_gt)
    zooms = geometria.descrever_nifti(dir_gt / rtst.NOME_IMAGEM)["zooms_mm"]
    gt = rtst.carregar_mascara(caminho_gt)
    pred = np.asarray(nib.load(str(caminho_pred)).dataobj) > 0.5
    est.exigir_mascara_na_grade(pred, gt.shape, rotulo=f"{caso}/pred")
    r = deslocamento_lateral_mm(gt, pred, zooms)
    _, _, calibre_pred = est._largura_efetiva_vetor(pred, zooms)
    return {"caso": caso, "raio_caracteristico_pred_mm": float(calibre_pred),
            **{f"lateral_{k}": v for k, v in r.items()}}


# ============================ o baseline no par MAASTRO, na unidade do erro

METRICAS_DO_ERRO = ("dice", "hd95_mm", "assd_mm", "precision", "recall",
                    "volume_error_pct", "erro_absoluto_pct_do_gt", "lateral_mediana_mm")


def baseline_no_par(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """O baseline congelado no LCTSC-S1 (n=10) contra o NSCLC (n=25).

    Mesma maquinaria da Parte 5, REUSADA (Mann-Whitney, permutacao, Cliff delta,
    IC por bootstrap, efeito minimo detectavel por simulacao, BH) — porque a
    pergunta e a mesma, so trocou o que esta na distribuicao: la era forma do GT,
    aqui e erro do modelo.

    Se o baseline errar mais de um lado que do outro com a instituicao fixa, isso
    e ASSOCIACAO entre erro e o lado do par. Nao prova convencao: a Parte 1 mostrou
    que o par tambem nao fixa kernel, kVp nem estrategia respiratoria.
    """
    a = [l for l in linhas if l["grupo"] == "LCTSC-S1"]
    b = [l for l in linhas if l["grupo"] == "NSCLC"]
    por_medida = {mt: est.comparar_par([l[mt] for l in a if l.get(mt) is not None],
                                       [l[mt] for l in b if l.get(mt) is not None])
                  for mt in METRICAS_DO_ERRO}
    for v in por_medida.values():
        v.pop("distribuicao_A", None)
        v.pop("distribuicao_B", None)
    return {"pergunta": ("com instituicao e geometria de voxel fixas, o baseline "
                         "congelado erra diferente nos dois lados do par?"),
            "por_medida": por_medida,
            "multiplicidade": est.corrigir_multiplicidade(por_medida)}


# ================================================ Parte 7 — a associacao

# Os quatro pares DO ENUNCIADO, declarados antes de calcular. A quinta linha e o
# mesmo par 1 com sinal: a pergunta "quando o GT e mais largo, o erro muda
# PROPORCIONALMENTE?" e sobre direcao, e o valor absoluto apaga a direcao.
PARES = (
    ("erro_de_volume_x_largura_efetiva",
     "erro_absoluto_pct_do_gt", "largura_efetiva_p50_mm"),
    ("erro_de_volume_com_sinal_x_largura_efetiva",
     "volume_error_pct", "largura_efetiva_p50_mm"),
    ("erro_lateral_x_area_transversal",
     "lateral_mediana_mm", "area_mediana_mm2"),
    ("dice_x_calibre",
     "dice", "raio_caracteristico_mm"),
    ("hd95_x_comprimento",
     "hd95_mm", "comprimento_z_mm"),
)

GRUPOS = ("LCTSC-S1", "LCTSC-S2", "LCTSC-S3", "NSCLC", "TODOS")


def spearman(x, y) -> dict[str, Any]:
    """Correlacao de POSTO, com o n. ASSOCIACAO — nunca causalidade.

    Posto, e nao Pearson, por dois motivos medidos nesta base: as distribuicoes
    tem cauda (dice 0,4849-0,8761, hd95 2,62-38,62 mm) e a relacao entre estilo
    e erro nao tem forma declarada. Spearman nao exige linearidade nem
    normalidade — so monotonicidade.

    n < 3 devolve `nao aplicavel`: com dois pontos o rho e sempre +-1 e nao
    significa nada.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    bons = np.isfinite(x) & np.isfinite(y)
    x, y = x[bons], y[bons]
    n = int(x.size)
    if n < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return {"n": n, "rho": NA, "p": NA,
                "motivo": "n < 3 ou variavel constante — rho indefinido ou trivial"}
    r = stats.spearmanr(x, y)
    return {"n": n, "rho": float(r.statistic), "p": float(r.pvalue)}


def _bh(ps: list[float]) -> list[float]:
    """Benjamini-Hochberg, na ordem da entrada. Mesma escolha da Parte 5.

    FDR e nao familiar porque isto e bateria exploratoria; e a scipy faz a conta,
    que nao precisa de implementacao propria para ser auditada.
    """
    return [float(v) for v in stats.false_discovery_control(np.asarray(ps, dtype=float),
                                                            method="bh")]


def associar(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """Parte 7 — os cinco pares, em cada grupo e no conjunto todo."""
    por_par: dict[str, Any] = {}
    familia: list[tuple[str, str, float]] = []
    for nome, ce, cf in PARES:
        por_grupo = {}
        for g in GRUPOS:
            sub = linhas if g == "TODOS" else [l for l in linhas if l["grupo"] == g]
            r = spearman([l.get(ce) for l in sub], [l.get(cf) for l in sub])
            por_grupo[g] = r
            if isinstance(r.get("p"), float):
                familia.append((nome, g, r["p"]))
        por_par[nome] = {"erro": ce, "estilo": cf, "por_grupo": por_grupo}

    qs = _bh([p for _, _, p in familia])
    for (nome, g, _), q in zip(familia, qs):
        por_par[nome]["por_grupo"][g]["p_bh"] = q

    # CONTROLE DE ESCALA — nao entra na familia testada, e diagnostico do
    # instrumento. `erro_absoluto_pct_do_gt` divide pelo volume do GT, e o volume
    # do GT anda com a largura. Se o SINAL da associacao inverter entre a versao
    # normalizada e a versao em mL, a associacao mede a NORMALIZACAO, nao estilo.
    controle = {}
    for g in GRUPOS:
        sub = linhas if g == "TODOS" else [l for l in linhas if l["grupo"] == g]
        larg = [l.get("largura_efetiva_p50_mm") for l in sub]
        controle[g] = {
            "erro_pct_do_gt_x_largura": spearman([l.get("erro_absoluto_pct_do_gt")
                                                  for l in sub], larg),
            "erro_em_mL_x_largura": spearman([l.get("erro_absoluto_ml") for l in sub], larg),
            "volume_gt_x_largura": spearman([l.get("volume_gt_ml") for l in sub], larg),
        }
        r1 = controle[g]["erro_pct_do_gt_x_largura"].get("rho")
        r2 = controle[g]["erro_em_mL_x_largura"].get("rho")
        controle[g]["sinal_inverte"] = (isinstance(r1, float) and isinstance(r2, float)
                                        and r1 * r2 < 0)

    n_brutos = sum(1 for _, _, p in familia if p < ALFA)
    sobreviventes = [f"{n}/{g}" for (n, g, _), q in zip(familia, qs) if q < ALFA]
    return {
        "leitura": ("ASSOCIACAO, nao causalidade. Correlacao de posto entre duas "
                    "descricoes do MESMO caso num desenho observacional nao separa "
                    "estilo de anatomia: um caso de estrutura maior tem, ao mesmo "
                    "tempo, GT mais largo e mais volume para o modelo errar."),
        "redundancia_declarada": ("`largura_efetiva_p50_mm` e `raio_caracteristico_mm` "
                                  "sao o MESMO numero (verificado: iguais em 55/55). Os "
                                  "cinco pares usam TRES descritores de estilo distintos, "
                                  "nao cinco — e `area_mediana_mm2` tambem anda com a "
                                  "largura. A familia de testes e menor do que a contagem, "
                                  "o que torna o BH conservador aqui."),
        "pares": por_par,
        "controle_de_escala": {
            "por_que": ("o erro de volume normalizado pelo GT e o proprio GT compartilham "
                        "o denominador. Este controle roda a MESMA associacao com o erro "
                        "em mL e mostra o volume do GT contra a largura. Ele NAO entra na "
                        "familia de testes corrigida: e diagnostico do instrumento, nao "
                        "hipotese."),
            "leitura": ("`sinal_inverte` verdadeiro significa que a associacao publicada "
                        "para aquele grupo mede a NORMALIZACAO e o TAMANHO, nao estilo."),
            "por_grupo": controle,
        },
        "multiplicidade": {
            "n_testes": len(familia),
            "esperado_por_acaso": round(ALFA * len(familia), 2),
            "n_p_brutos_abaixo_de_alfa": n_brutos,
            "n_sobreviventes_bh": len(sobreviventes),
            "sobreviventes_bh": sobreviventes,
        },
    }


# ============================================== Parte 8 — o modelo nulo

MOTIVO_NULO_ESPACIAL = (
    "NAO FEITO, de proposito. Um nulo ESPACIAL (envelope mediano, calibre "
    "mediano normalizado, perfil longitudinal mediano) so vira Dice depois de ser "
    "COLOCADO em algum lugar do volume, e nesta base existem exatamente tres "
    "fontes de posicao: (1) o eixo medial do proprio GT do caso avaliado — "
    "circular, o nulo passaria a conhecer a resposta que esta sendo cobrada dele; "
    "(2) a predicao do TotalSegmentator (esofago, traqueia ou aorta) — deixa de "
    "ser `sem rede nenhuma` e vira ablacao de calibre sobre uma rede; (3) uma "
    "posicao fixa em coordenada de imagem — nao e estatistica de forma do "
    "dataset, e um chute que a anatomia de cada caso desmente. Nenhuma das tres "
    "responde a pergunta que o nulo espacial existiria para responder. Trocar o "
    "grupo de construcao pelo grupo de avaliacao resolve o vazamento do PARAMETRO "
    "de forma, e nao o da POSICAO — e e o da posicao que domina o Dice de uma "
    "estrutura fina. Por isso a Parte 8 se limita ao nulo ESCALAR, que nao "
    "precisa de posicao."
)

# Alvos escalares que o nulo consegue prever sem posicao nenhuma. Cada um tem um
# par direto no erro do baseline, senao o nulo nao seria comparavel a nada.
ALVOS_NULO = (
    ("volume_mL", "volume_gt_ml", "volume_pred_ml"),
    ("raio_caracteristico_mm", "raio_caracteristico_mm", "raio_caracteristico_pred_mm"),
)


def nulo_escalar(linhas: list[dict[str, Any]], grupo_fonte: str,
                 grupo_alvo: str) -> dict[str, Any]:
    """Nulo CONSTANTE: a mediana do grupo FONTE prevendo cada caso do grupo ALVO.

    Sem vazamento por construcao: o parametro vem de casos que nao estao entre os
    avaliados, e a checagem `fonte != alvo` e uma tranca, nao um comentario.

    O que ele responde: quanto do erro de VOLUME do baseline ja e dado por uma
    constante tirada do outro dataset. Se a constante errar menos que a rede, o
    erro de volume da rede nao vem de anatomia especifica do caso.
    """
    if grupo_fonte == grupo_alvo:
        raise ValueError(
            f"nulo construido e avaliado no mesmo grupo ({grupo_fonte}) — isso e "
            "vazamento: a mediana do grupo ja viu todos os casos que ela vai prever."
        )
    fonte = [l for l in linhas if l["grupo"] == grupo_fonte]
    alvo = [l for l in linhas if l["grupo"] == grupo_alvo]
    if not fonte or not alvo:
        return {"grupo_fonte": grupo_fonte, "grupo_alvo": grupo_alvo, "status": NA}

    saida = {"grupo_fonte": grupo_fonte, "grupo_alvo": grupo_alvo,
             "n_fonte": len(fonte), "n_alvo": len(alvo), "alvos": {}}
    for nome, col_gt, col_pred in ALVOS_NULO:
        if any(l.get(c) is None for l in fonte + alvo for c in (col_gt, col_pred)):
            saida["alvos"][nome] = {"status": NM,
                                    "motivo": f"coluna ausente ou vazia ({col_gt}/{col_pred})"}
            continue
        const = float(np.median([l[col_gt] for l in fonte]))
        gt = np.asarray([l[col_gt] for l in alvo], dtype=float)
        pred = np.asarray([l[col_pred] for l in alvo], dtype=float)
        e_nulo = np.abs(const - gt) / gt * 100.0
        e_base = np.abs(pred - gt) / gt * 100.0
        saida["alvos"][nome] = {
            "constante_do_nulo": const,
            "erro_abs_pct_nulo_mediana": float(np.median(e_nulo)),
            "erro_abs_pct_baseline_mediana": float(np.median(e_base)),
            "n_casos_em_que_o_nulo_erra_menos": int(np.sum(e_nulo < e_base)),
            "p_wilcoxon": float(stats.wilcoxon(e_nulo, e_base).pvalue)
            if len(gt) >= 6 else NA,
        }
    return saida


def parte8(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """Parte 8 — o nulo escalar cruzado nas duas direcoes, e o espacial recusado."""
    pares = [("NSCLC", "LCTSC-S1"), ("LCTSC-S1", "NSCLC"),
             ("NSCLC", "LCTSC-S2"), ("NSCLC", "LCTSC-S3")]
    return {
        "nulo_espacial": {"feito": False, "motivo": MOTIVO_NULO_ESPACIAL},
        "nulo_escalar": {
            "construcao": ("constante = mediana do alvo no grupo FONTE, avaliada nos "
                           "casos do grupo ALVO. Fonte e alvo sao disjuntos por "
                           "construcao e a funcao recusa fonte == alvo."),
            "cruzamentos": [nulo_escalar(linhas, f, a) for f, a in pares],
        },
    }


# ============================================== Parte 9 — a classificacao

CLASSES = {
    "A": "ESTILO PEQUENO — diferenca pequena frente ao erro do baseline",
    "B": "ESTILO RELEVANTE — diferenca mensuravel, mas sobra erro nao explicado",
    "C": "ESTILO DOMINANTE — a diferenca de convencao e comparavel ou maior que a "
         "melhoria que um modelo novo precisaria produzir",
    "D": "INCONCLUSIVO — os datasets nao sao comparaveis o bastante para separar as causas",
}


def classificar(res: dict[str, Any], saida_fase: Path = est.SAIDA_FASE10) -> dict[str, Any]:
    """Parte 9 — A/B/C/D, com os numeros de disco que sustentam a escolha.

    A regra do enunciado e explicita e vale mais que a tentacao de concluir:
    se a comparabilidade institucional da Parte 1 falhou, a resposta e D. Os
    criterios sao lidos dos arquivos das partes anteriores, nao redigitados.
    """
    comp = json.loads((saida_fase / "comparabilidade.json").read_text(encoding="utf-8"))
    defi = json.loads((saida_fase / "definicoes.json").read_text(encoding="utf-8"))
    morf = json.loads((saida_fase / "morfologia" / "morfologia.json").read_text(
        encoding="utf-8"))
    teto = morf["parte5_teto"]
    par = morf["parte5_par_maastro"]

    # A Parte 2 gravou o veredito em texto, com a palavra NAO na frente quando o
    # lado nao tem regra. Ler a string e o que existe — inventar um campo booleano
    # agora seria reescrever a Parte 2 para caber nesta.
    status_b = str(defi["NSCLC-Radiomics"]["status"])
    lado_b_documentado = not status_b.upper().startswith("NAO DOCUMENTADA")

    bloqueios = []
    if comp["campos_com_sobreposicao_parcial"]:
        bloqueios.append({
            "de": "Parte 1",
            "fato": (f"{len(comp['campos_concordantes'])} campos concordantes (todos de "
                     f"geometria) contra {len(comp['campos_com_sobreposicao_parcial'])} "
                     f"com sobreposicao parcial (todos de aquisicao/reconstrucao): "
                     f"{comp['campos_com_sobreposicao_parcial']}"),
            "consequencia": ("o par fixa instituicao e geometria de voxel, NAO fixa "
                             "protocolo de aquisicao — logo nao isola convencao sozinha"),
        })
    if comp["campos_nao_comparaveis"]:
        bloqueios.append({
            "de": "Parte 1",
            "fato": f"{len(comp['campos_nao_comparaveis'])} campos nao comparaveis por "
                    f"anonimizacao oposta: {comp['campos_nao_comparaveis']}",
            "consequencia": "a procedencia institucional do lado B continua hipotese",
        })
    if not lado_b_documentado:
        bloqueios.append({
            "de": "Parte 2",
            "fato": f"a convencao de contorno do lado B (NSCLC-Radiomics): {status_b}",
            "consequencia": ("uma diferenca medida entre os lados nao pode ser atribuida a "
                             "uma REGRA de contorno — a regra do lado B e desconhecida"),
        })
    mult5 = par.get("multiplicidade", {})
    pm = par["por_medida"]
    sob_mde = sum(1 for v in pm.values() if v.get("efeito_observado_abaixo_do_mde"))
    if mult5.get("n_sobreviventes_bh", 0) == 0:
        bloqueios.append({
            "de": "Parte 5",
            "fato": f"{mult5.get('n_medidas_testadas')} medidas de forma testadas, "
                    f"{mult5.get('n_p_brutos_abaixo_de_alfa')} p bruto abaixo de {ALFA}, "
                    f"{mult5.get('n_sobreviventes_bh')} sobrevivem ao BH; e o efeito "
                    f"observado fica abaixo do MDE em {sob_mde}/{len(pm)}",
            "consequencia": "nenhuma diferenca de forma esta estabelecida neste desenho",
        })
    mult7 = res["parte7_associacao"]["multiplicidade"]
    if mult7["n_sobreviventes_bh"] == 0:
        bloqueios.append({
            "de": "Parte 7",
            "fato": f"{mult7['n_testes']} associacoes testadas, "
                    f"{mult7['n_p_brutos_abaixo_de_alfa']} p brutos abaixo de {ALFA} "
                    f"({mult7['esperado_por_acaso']} esperados por acaso), "
                    f"{mult7['n_sobreviventes_bh']} sobrevivem ao BH",
            "consequencia": "nenhuma associacao erro x estilo sobrevive a multiplicidade",
        })
    inverte = [g for g, v in res["parte7_associacao"]["controle_de_escala"][
        "por_grupo"].items() if v["sinal_inverte"]]
    if inverte:
        bloqueios.append({
            "de": "Parte 7 (controle de escala)",
            "fato": f"o sinal da associacao erro-de-volume x largura INVERTE entre a versao "
                    f"normalizada pelo GT e a versao em mL, em {len(inverte)} de "
                    f"{len(GRUPOS)} recortes: {inverte}",
            "consequencia": ("a associacao mais forte desta parte segue TAMANHO e a escolha "
                             "de normalizacao, nao convencao de contorno"),
        })

    pior = teto["dice_teto_combinado"]["um_voxel_no_plano"]
    base = teto["baseline_dice_mediano"]
    return {
        "classe": "D" if bloqueios else "B",
        "rotulo": CLASSES["D" if bloqueios else "B"],
        "regra_aplicada": ("o enunciado manda D quando a comparabilidade institucional da "
                           "Parte 1 falha. Ela falhou parcialmente, e as Partes 2, 5 e 7 "
                           "adicionam bloqueios independentes. D nao e o resultado mais "
                           "interessante; e o unico que o dado sustenta."),
        "bloqueios": bloqueios,
        "numero_que_teria_sustentado_B": {
            "teto_de_dice_no_pior_cenario": pior.get("mediana"),
            "faixa": [pior.get("min"), pior.get("max")],
            "baseline_dice_mediano": base,
            "sobra": (pior.get("mediana") - base)
            if isinstance(pior.get("mediana"), float) else NA,
            "leitura": ("no cenario mais pessimista compativel com este dado — "
                        "deslocamento de UM voxel de largura mais os 10,5 mm de extensao "
                        "caudal — dois contornos perfeitos dos dois estilos concordariam "
                        "a Dice mediana acima do baseline. Isso APONTA para B (estilo "
                        "relevante, com erro sobrando), e nao pode ser publicado como B "
                        "porque os bloqueios acima impedem atribuir a diferenca a "
                        "convencao em vez de a protocolo de aquisicao ou a acaso."),
        },
        "o_que_mudaria_a_classe": [
            "documentacao de contorno do lado B (removeria o bloqueio da Parte 2)",
            "um par com o MESMO kernel, kVp e estrategia respiratoria nos dois lados",
            "n por grupo suficiente para o efeito observado passar do MDE",
            "o MESMO caso contornado nos dois estilos (elimina anatomia por pareamento)",
        ],
    }


# ================================================== juntar tudo e gravar

def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def montar_linhas(raiz_a: Path = RAIZ_LCTSC, raiz_b: Path = RAIZ_NSCLC,
                  log=print) -> list[dict[str, Any]]:
    """Uma linha por caso: metricas do baseline + morfologia do GT + erro lateral.

    O lado A vem PRONTO de fase7/esofago/baseline/baseline_esofago.json — nao e
    remedido. O lado B vem da Parte 6. A morfologia vem da Parte 3/4, tambem
    pronta. O unico numero novo por caso e o erro lateral, que le as predicoes
    ja congeladas em disco.
    """
    a = json.loads(BASELINE_A.read_text(encoding="utf-8"))
    linhas_a = a["baseline"]["por_caso"]
    split = json.loads((raiz_a / "fase5" / "split.json").read_text(encoding="utf-8"))["split"]
    est.exigir_apenas_development([l["case_id"] for l in linhas_a], split)

    b = json.loads((SAIDA / "baseline_nsclc.json").read_text(encoding="utf-8"))
    linhas_b = b["por_caso"]

    morf = {r["caso"]: r for r in csv.DictReader(MORFOLOGIA.open(encoding="utf-8"))}

    linhas = []
    for l, raiz in [(x, raiz_a) for x in linhas_a] + [(x, raiz_b) for x in linhas_b]:
        caso = l["case_id"]
        m = morf.get(caso)
        if m is None:
            log(f"  {caso}: sem morfologia — fora da associacao")
            continue
        lat = medir_predicao_congelada(caso, raiz)
        linha = {"caso": caso, "grupo": m["grupo"], "dataset": m["dataset"]}
        for k in ("dice", "hd95_mm", "assd_mm", "precision", "recall",
                  "volume_error_pct", "volume_pred_ml", "volume_gt_ml",
                  "erro_absoluto_ml", "erro_absoluto_pct_do_gt"):
            linha[k] = _num(l.get(k))
        for k in ("volume_mL", "comprimento_z_mm", "area_mediana_mm2",
                  "raio_caracteristico_mm", "largura_efetiva_p50_mm",
                  "largura_fatia_mediana_mm", "razao_ponta_caudal",
                  "cv_largura_em_z"):
            linha[k] = _num(m.get(k))
        linha["lateral_mediana_mm"] = _num(lat.get("lateral_mediana_mm"))
        linha["lateral_p90_mm"] = _num(lat.get("lateral_p90_mm"))
        linha["lateral_n_fatias"] = lat.get("lateral_n_fatias_com_os_dois")
        linha["raio_caracteristico_pred_mm"] = _num(lat.get("raio_caracteristico_pred_mm"))
        linhas.append(linha)

    est.exigir_sem_repeticao([l["caso"] for l in linhas], "associacao")
    return linhas


def executar(raiz_a: Path = RAIZ_LCTSC, raiz_b: Path = RAIZ_NSCLC,
             saida: Path = SAIDA, log=print) -> dict[str, Any]:
    """Partes 7, 8 e 9 sobre a Parte 6 ja gravada."""
    Path(saida).mkdir(parents=True, exist_ok=True)
    linhas = montar_linhas(raiz_a, raiz_b, log=log)
    log(f"associacao: {len(linhas)} casos")

    # Distribuicoes lado a lado. O lado A e REUSO da fase 7 — as mesmas 30 linhas
    # que produziram o BASELINE_ESOFAGO_V1 publicado, sem remedir.
    metricas = ("dice", "hd95_mm", "assd_mm", "precision", "recall",
                "volume_error_pct", "erro_absoluto_pct_do_gt", "lateral_mediana_mm")
    lado = {"A": [l for l in linhas if l["dataset"] == "LCTSC"],
            "B": [l for l in linhas if l["dataset"] != "LCTSC"]}
    b6 = {
        "n_ok": len(lado["B"]),
        "reuso_lado_A": str(BASELINE_A),
        "agregado": {k: {mt: bl._dist([l.get(mt) for l in v]) for mt in metricas}
                     for k, v in lado.items()},
        "por_grupo": {g: {mt: bl._dist([l.get(mt) for l in linhas if l["grupo"] == g])
                          for mt in metricas}
                      for g in GRUPOS if g != "TODOS"},
        "par_maastro": baseline_no_par(linhas),
    }

    res = {
        "parte6_baseline": b6,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "escopo": ESCOPO,
        "n_casos": len(linhas),
        "por_grupo": {g: sum(1 for l in linhas if l["grupo"] == g)
                      for g in GRUPOS if g != "TODOS"},
        "parte7_associacao": associar(linhas),
        "parte8_nulo": parte8(linhas),
        "por_caso": linhas,
    }
    res["parte9_classificacao"] = classificar(res)
    (Path(saida) / "associacao.json").write_text(
        json.dumps(_json_safe(res), indent=2, ensure_ascii=False), encoding="utf-8")
    (Path(saida) / "resumo.md").write_text(_resumo_md(res, b6), encoding="utf-8")

    cols = list(linhas[0])
    with (Path(saida) / "associacao_por_caso.csv").open("w", newline="",
                                                        encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(linhas)
    log(f"gravado em {saida}")
    return res


def _f(v, casas=4) -> str:
    if isinstance(v, (int, float)) and np.isfinite(v):
        return f"{v:.{casas}f}".replace(".", ",")
    return NA if v is None else str(v)


def _resumo_md(r: dict[str, Any], b6: dict[str, Any]) -> str:
    """Tabelas com os numeros REAIS. Nada aqui e escrito a mao."""
    L = ["# Fase 10, Partes 6 a 9 — o baseline no lado B e a associacao erro x estilo",
         "", f"ESCOPO: {ESCOPO}", "",
         "## Parte 6 — BASELINE_ESOFAGO_V1, sem alteracao, nos dois lados", ""]

    ag = b6.get("agregado", {})
    L += ["| metrica | LCTSC development (n=30, fase 7, REUSADO) | NSCLC (n=%d, medido aqui) |"
          % b6["n_ok"], "|---|---|---|"]
    for mt in ("dice", "hd95_mm", "assd_mm", "precision", "recall", "volume_error_pct",
               "erro_absoluto_pct_do_gt"):
        a_ = ag.get("A", {}).get(mt, {})
        b_ = ag.get("B", {}).get(mt, {})
        L.append(f"| {mt} | {_f(a_.get('mediana'))} [{_f(a_.get('p25'))}–"
                 f"{_f(a_.get('p75'))}] | {_f(b_.get('mediana'))} "
                 f"[{_f(b_.get('p25'))}–{_f(b_.get('p75'))}] |")

    L += ["", "### Por grupo", "",
          "| grupo | n | dice | hd95 mm | assd mm | precision | recall | "
          "erro de volume % | erro lateral mm |", "|---|---|---|---|---|---|---|---|---|"]
    for g, v in b6["por_grupo"].items():
        L.append(f"| {g} | {v['dice']['n']} | " + " | ".join(
            _f(v[mt]["mediana"]) for mt in
            ("dice", "hd95_mm", "assd_mm", "precision", "recall",
             "volume_error_pct", "lateral_mediana_mm")) + " |")

    pm = b6["par_maastro"]["por_medida"]
    L += ["", "### O par MAASTRO na unidade do erro — LCTSC-S1 (n=10) x NSCLC (n=25)", "",
          "| metrica | S1 | NSCLC | dif | Cliff | IC95 do Cliff | p MW | p BH | p perm "
          "| MDE | dif < MDE |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for mt, v in pm.items():
        ic = v.get("ic95_cliff_delta") or [None, None]
        L.append(f"| {mt} | {_f(v['mediana_A'])} | {_f(v['mediana_B'])} | "
                 f"{_f(v['diferenca_de_mediana_B_menos_A'])} | "
                 f"{_f(v['cliff_delta_B_vs_A'])} ({v['cliff_delta_rotulo']}) | "
                 f"[{_f(ic[0])}; {_f(ic[1])}] | {_f(v['p_mann_whitney'])} | "
                 f"{_f(v.get('p_mann_whitney_bh'))} | {_f(v['p_permutacao_da_mediana'])} | "
                 f"{_f(v['poder'].get('mde'))} | "
                 f"{'SIM' if v['efeito_observado_abaixo_do_mde'] else 'nao'} |")
    mp = b6["par_maastro"]["multiplicidade"]
    L += ["", f"{mp['n_medidas_testadas']} metricas, {mp['n_p_brutos_abaixo_de_alfa']} p "
              f"brutos abaixo de {ALFA} ({_f(mp['esperado_por_acaso'], 2)} esperados por "
              f"acaso), {mp['n_sobreviventes_bh']} sobrevivem ao BH: "
              f"{mp['medidas_sobreviventes_bh']}.", ""]

    L += ["", "## Parte 7 — associacao (Spearman). ASSOCIACAO, nunca causalidade.", ""]
    p7 = r["parte7_associacao"]
    L += ["| par | grupo | n | rho | p | p BH |", "|---|---|---|---|---|---|"]
    for nome, d in p7["pares"].items():
        for g, v in d["por_grupo"].items():
            L.append(f"| {nome} | {g} | {v['n']} | {_f(v.get('rho'))} | "
                     f"{_f(v.get('p'))} | {_f(v.get('p_bh'))} |")
    ce = p7["controle_de_escala"]
    L += ["", "### Controle de escala (diagnostico do instrumento, fora da familia testada)",
          "", "| grupo | erro % do GT x largura | erro em mL x largura | volume GT x largura "
          "| sinal inverte |", "|---|---|---|---|---|"]
    for g, v in ce["por_grupo"].items():
        L.append(f"| {g} | {_f(v['erro_pct_do_gt_x_largura'].get('rho'))} "
                 f"(p {_f(v['erro_pct_do_gt_x_largura'].get('p'))}) | "
                 f"{_f(v['erro_em_mL_x_largura'].get('rho'))} "
                 f"(p {_f(v['erro_em_mL_x_largura'].get('p'))}) | "
                 f"{_f(v['volume_gt_x_largura'].get('rho'))} "
                 f"(p {_f(v['volume_gt_x_largura'].get('p'))}) | "
                 f"{'SIM' if v['sinal_inverte'] else 'nao'} |")
    L += ["", ce["leitura"], ""]

    m = p7["multiplicidade"]
    L += ["", f"{m['n_testes']} testes, {m['esperado_por_acaso']} esperados por acaso, "
              f"{m['n_p_brutos_abaixo_de_alfa']} p brutos abaixo de {ALFA}, "
              f"{m['n_sobreviventes_bh']} sobrevivem ao BH: {m['sobreviventes_bh']}.", ""]

    L += ["## Parte 8 — modelo nulo", "",
          "Nulo espacial: " + MOTIVO_NULO_ESPACIAL, "",
          "| alvo | fonte | avaliado em | n fonte | n alvo | constante | erro nulo % | "
          "erro baseline % | nulo erra menos em | p Wilcoxon |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for c in r["parte8_nulo"]["nulo_escalar"]["cruzamentos"]:
        for nome, v in c.get("alvos", {}).items():
            L.append(f"| {nome} | {c['grupo_fonte']} | {c['grupo_alvo']} | "
                     f"{c['n_fonte']} | {c['n_alvo']} | {_f(v['constante_do_nulo'], 3)} | "
                     f"{_f(v['erro_abs_pct_nulo_mediana'], 2)} | "
                     f"{_f(v['erro_abs_pct_baseline_mediana'], 2)} | "
                     f"{v['n_casos_em_que_o_nulo_erra_menos']}/{c['n_alvo']} | "
                     f"{_f(v['p_wilcoxon'])} |")

    p9 = r["parte9_classificacao"]
    L += ["", f"## Parte 9 — classe **{p9['classe']}**: {p9['rotulo']}", "",
          p9["regra_aplicada"], "", "| bloqueio | fato | consequencia |",
          "|---|---|---|"]
    for b in p9["bloqueios"]:
        L.append(f"| {b['de']} | {b['fato']} | {b['consequencia']} |")
    n9 = p9["numero_que_teria_sustentado_B"]
    L += ["", f"Teto de Dice no pior cenario: {_f(n9['teto_de_dice_no_pior_cenario'])} "
              f"[{_f(n9['faixa'][0])}–{_f(n9['faixa'][1])}] contra baseline "
              f"{_f(n9['baseline_dice_mediano'])} (sobra {_f(n9['sobra'])}). "
              + n9["leitura"], ""]
    return "\n".join(L) + "\n"


def _json_safe(o):
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return _json_safe(o.tolist())
    if isinstance(o, Path):
        return str(o)
    return o


# ============================================================== autoteste

def _cilindro(shape=(64, 64, 30), zooms=(1.0, 1.0, 3.0), raio_mm=5.0,
              centro=None) -> np.ndarray:
    """Cilindro solido em Z — mesma construcao do autoteste da fase 10."""
    cx, cy = centro if centro else (shape[0] / 2.0, shape[1] / 2.0)
    xx, yy = np.mgrid[0:shape[0], 0:shape[1]]
    d = np.hypot((xx - cx) * zooms[0], (yy - cy) * zooms[1])
    disco = d <= raio_mm
    m = np.zeros(shape, dtype=bool)
    m[:, :, 4:shape[2] - 4] = disco[:, :, None]
    return m


def _autoteste() -> None:
    """Controle POSITIVO em cada instrumento novo: tem que FALHAR quando deve."""
    print("== deslocamento lateral ==")
    zooms = (0.9765625, 0.9765625, 3.0)
    a = _cilindro(zooms=zooms, centro=(32.0, 32.0))

    # 1. mascaras identicas -> deslocamento ZERO.
    r = deslocamento_lateral_mm(a, a, zooms)
    assert abs(r["mediana_mm"]) < 1e-9, r
    print(f"  identicas: mediana {r['mediana_mm']:.2e} mm — ok")

    # 2. CONTROLE POSITIVO: deslocar 4 voxels em x tem que dar 4*dx, nao zero.
    b = np.roll(a, 4, axis=0)
    r = deslocamento_lateral_mm(a, b, zooms)
    esperado = 4 * zooms[0]
    assert abs(r["mediana_mm"] - esperado) < 1e-6, (r, esperado)
    assert r["mediana_mm"] > 1e-6, "instrumento cego a deslocamento — controle positivo"
    print(f"  deslocado 4 voxels: {r['mediana_mm']:.6f} mm (esperado {esperado:.6f}) — ok")

    # 3. CONTROLE POSITIVO da unidade: a MESMA geometria com outro spacing tem
    #    que dar OUTRO numero. Se der o mesmo, o instrumento esta em voxel.
    zooms2 = (1.269531, 1.269531, 3.0)
    r2 = deslocamento_lateral_mm(a, b, zooms2)
    assert abs(r2["mediana_mm"] - 4 * zooms2[0]) < 1e-6, r2
    assert abs(r2["mediana_mm"] - r["mediana_mm"]) > 1e-3, "instrumento em voxel, nao em mm"
    print(f"  outro spacing: {r2['mediana_mm']:.6f} mm — ok (nao e contagem de voxel)")

    # 4. CONTROLE POSITIVO: sem fatia em comum devolve `nao aplicavel`, nao 0,0.
    c = np.zeros_like(a)
    c[:, :, :3] = a[:, :, 10:13]
    r3 = deslocamento_lateral_mm(a, c, zooms)
    assert r3["mediana_mm"] == NA and r3["n_fatias_com_os_dois"] == 0, r3
    print("  sem sobreposicao em Z: `nao aplicavel` (e nao 0,0) — ok")

    # 5. CONTROLE POSITIVO: fatias so-do-GT nao podem contaminar o lateral.
    d = b.copy()
    d[:, :, 4:8] = False           # a predicao perde 4 fatias caudais
    r4 = deslocamento_lateral_mm(a, d, zooms)
    assert abs(r4["mediana_mm"] - esperado) < 1e-6, r4
    assert r4["frac_fatias_do_gt"] < 1.0, r4
    print(f"  4 fatias sem predicao: lateral igual ({r4['mediana_mm']:.4f} mm), "
          f"frac {r4['frac_fatias_do_gt']:.4f} — ok")

    print("== spearman ==")
    x = list(range(10))
    assert abs(spearman(x, [v ** 3 for v in x])["rho"] - 1.0) < 1e-12
    assert abs(spearman(x, [-v for v in x])["rho"] + 1.0) < 1e-12
    assert spearman([1, 2], [1, 2])["rho"] == NA, "n<3 tinha que ser nao aplicavel"
    assert spearman(x, [7] * 10)["rho"] == NA, "constante tinha que ser nao aplicavel"
    # CONTROLE POSITIVO: monotonico NAO-linear tem que dar rho 1 (Pearson daria < 1)
    assert stats.pearsonr(x, [v ** 3 for v in x]).statistic < 0.99
    print("  monotonico nao-linear: rho 1,0 e Pearson < 0,99 — e posto mesmo — ok")

    print("== BH ==")
    q = _bh([0.001, 0.02, 0.5, 0.9])
    assert q[0] < ALFA and q == sorted(q), q
    # CONTROLE POSITIVO: um p que passa sozinho tem que MORRER numa familia de 20.
    solto = _bh([0.03])
    numa_familia = _bh([0.03] + [0.6] * 19)
    assert solto[0] < ALFA <= numa_familia[0], (solto, numa_familia)
    print(f"  {[round(v, 4) for v in q]} — monotonico; p 0,03 vira "
          f"{numa_familia[0]:.4f} em familia de 20 — ok")

    print("== nulo escalar ==")
    rng = np.random.default_rng(20260905)
    linhas = []
    for i in range(20):
        v = float(30 + rng.normal(0, 5))
        linhas.append({"grupo": "A" if i < 10 else "B", "volume_gt_ml": v,
                       "volume_pred_ml": v * 1.3,        # baseline erra 30% sempre
                       "raio_caracteristico_mm": 9.0 + rng.normal(0, 0.5),
                       "raio_caracteristico_pred_mm": 9.0})
    alvos = nulo_escalar(linhas, "A", "B")["alvos"]
    r = alvos["volume_mL"]
    assert r["erro_abs_pct_nulo_mediana"] < r["erro_abs_pct_baseline_mediana"], r
    print(f"  volume: nulo {r['erro_abs_pct_nulo_mediana']:.2f}% x baseline "
          f"{r['erro_abs_pct_baseline_mediana']:.2f}% — ok")
    assert isinstance(alvos["raio_caracteristico_mm"]["constante_do_nulo"], float)

    # CONTROLE POSITIVO: coluna ausente vira `nao medido`, nao um numero inventado.
    sem = [{k: v for k, v in l.items() if k != "raio_caracteristico_pred_mm"}
           for l in linhas]
    assert nulo_escalar(sem, "A", "B")["alvos"]["raio_caracteristico_mm"]["status"] == NM
    print("  coluna ausente: `nao medido` (e nao um numero) — ok")

    # CONTROLE POSITIVO do VAZAMENTO: a tranca tem que recusar fonte == alvo.
    caiu = False
    try:
        nulo_escalar(linhas, "B", "B")
    except ValueError:
        caiu = True
    assert caiu, "a tranca contra vazamento nao disparou — controle positivo"
    print("  fonte == alvo: RECUSADO — ok")

    print("== roi_subset do baseline ==")
    _conferir_roi_subset({"tarefa": "total", "fast": False,
                          "estruturas": mapeamento.roi_subset()})
    for ruim in ({"tarefa": "total", "fast": False,
                  "estruturas": ["trachea", "aorta", "esophagus"]},
                 {"tarefa": "total", "fast": True,
                  "estruturas": mapeamento.roi_subset()}):
        caiu = False
        try:
            _conferir_roi_subset(ruim)
        except est.DatasetNaoPermitido:
            caiu = True
        assert caiu, f"aceitou predicao fora do baseline: {ruim}"
    print("  aceita as 8 do baseline, RECUSA as 3 do aux e o fast — ok")

    print("\nautoteste OK")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fase 10, Partes 6-9")
    p.add_argument("--autoteste", action="store_true")
    p.add_argument("--baseline-b", action="store_true",
                   help="Parte 6: baseline congelado nos 25 casos do NSCLC")
    p.add_argument("--associacao", action="store_true",
                   help="Partes 7 e 8 sobre a Parte 6 ja gravada")
    a = p.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0
    if a.baseline_b:
        SAIDA.mkdir(parents=True, exist_ok=True)
        r = rodar_baseline_nsclc()
        (SAIDA / "baseline_nsclc.json").write_text(
            json.dumps(_json_safe(r), indent=2, ensure_ascii=False), encoding="utf-8")
        if r["por_caso"]:
            cols = [c for c in r["por_caso"][0] if c != "spacing_mm"] + ["spacing_mm"]
            with (SAIDA / "baseline_nsclc.csv").open("w", newline="",
                                                     encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for l in r["por_caso"]:
                    w.writerow({**l, "spacing_mm": ";".join(
                        str(s) for s in l["spacing_mm"])})
        print(f"parte 6: {r['n_ok']}/{r['n']} casos -> {SAIDA}")
        return 0
    if a.associacao:
        executar()
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
