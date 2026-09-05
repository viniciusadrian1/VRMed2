"""Parte 8 — experimento de RESOLUCAO. Ataca E7 (artefato de aquisicao/spacing).

A coorte tem spacing em Z heterogeneo (S1 = 3,0 mm; S2 = 2,5 mm; S3 = misto de
1,25 / 2,0 / 2,5 / 3,0 mm). A pergunta: a heterogeneidade contribui para o erro?

Este modulo NAO altera o baseline, NAO grava em pred_masks/ e NAO treina nada.
Ele roda UMA configuracao alternativa de inferencia e mede a diferenca contra o
baseline congelado, caso a caso, nas mesmas quatro estruturas.

==============================================================================
QUAL COMPARACAO E LEGITIMA — e por que a outra nao e
==============================================================================

O TotalSegmentator ja reamostra a entrada internamente antes de segmentar. Lido
do proprio pacote (`totalsegmentator/map_tasks_config.py`, tarefa `total`):

    modo default : resample 1,5 mm · task_id [291..295] · nnUNetTrainerNoMirroring
    modo fast    : resample 3,0 mm · task_id 297        · nnUNetTrainer_4000epochs_NoMirroring

(a) ESCOLHIDA — `fast=True` contra o baseline `fast=False`.
    A entrada nao e tocada: continua sendo o mesmo `gt/image.nii.gz` na grade
    original. Quem reamostra e o proprio TotalSegmentator, na ida e na volta,
    pelo mesmo caminho de codigo que ja produziu o baseline. A predicao volta
    para a grade original por construcao — e isso e VERIFICADO caso a caso com
    `geometria.verificar_alinhamento` antes de qualquer medida.

    O que (a) NAO e: uma alteracao unica. A flag troca resolucao interna E
    modelo E trainer de uma vez so (1,5 mm / ensemble de 5 partes / trainer
    padrao  ->  3,0 mm / modelo unico / trainer de 4000 epocas). O confundimento
    esta DENTRO da ferramenta, nao no desenho do experimento: nao existe, na
    configuracao congelada, um botao que mude so a resolucao. Por isso o
    resultado responde "trocar para o caminho de 3 mm muda o erro?" e NAO
    "resolucao maior e melhor?". Declarado antes de rodar.

(b) RECUSADA — reamostrar a entrada para isotropico antes de segmentar.
    E dupla reamostragem, e ela e indevida aqui por tres motivos, em ordem de
    forca:

    1. Ela nao substitui a reamostragem do TotalSegmentator, se soma a ela. A
       entrada iria 0,98 x 0,98 x 3,0 -> 1,5 iso (nossa, interpolando CINZA) e
       de la o TotalSegmentator faria a dele. Duas interpolacoes encadeadas do
       sinal, e a segunda nao e nossa para controlar.
    2. Para comparar com o GT a predicao teria que VOLTAR para a grade original
       — uma terceira reamostragem, agora de MASCARA. Esse retorno tem custo
       medido: `custo_ida_e_volta()` neste modulo mede o Dice de uma mascara
       consigo mesma depois de ir para 1,5 mm isotropico e voltar, sem GT
       nenhum. E um LIMITE INFERIOR do artefato de (b) — cobre so a volta da
       mascara, nao a ida do sinal. Se ja esse limite inferior custar mais que
       LIMIAR_MELHORIA_DICE, o artefato do caminho domina o efeito procurado e
       a comparacao nao e interpretavel. O numero sai no relatorio.
    3. A investigacao de confianca (Parte 7, ja registrada) mediu o mesmo tipo
       de retorno num caso e achou teto de Dice ~0,955 contra a mascara
       entregue, com 2.131 voxels em desacordo contra os ~239 que valem 0,01 de
       Dice — razao ruido/efeito de 8,9x.

    Entao (b) NAO e executada. O que este modulo faz por (b) e medir o custo do
    caminho e publicar o numero, para a recusa ser uma medida e nao uma opiniao.

==============================================================================
SUBCONJUNTO — criterio declarado ANTES de rodar (`--selecao` imprime e sai)
==============================================================================

Universo: SOMENTE o `development` do split.json (30 casos). O `test` nao e lido
e o `validation` nao e usado nesta fase.

    estrato    = (instituicao, dx_mm, dz_mm) — geometria de voxel da AQUISICAO,
                 lida de `gt/image.nii.gz` (header). Nenhum dado do GT entra na
                 escolha: a regra rodaria igual num caso sem GT nenhum.
    ordem      = fase5._ordem_deterministica = sha256(semente|case_id)
    passo 1    = o primeiro caso de CADA estrato  -> cobre toda a geometria de
                 voxel presente no development e as tres instituicoes
    passo 2    = enquanto n < N_CASOS, o proximo caso nao usado do MAIOR estrato
                 restante (empate resolvido pela chave do estrato ordenada)
    N_CASOS    = 11

==============================================================================
O QUE E REGISTRADO e como se decide
==============================================================================

Por caso e por estrutura (SpinalCord, Esophagus = alvos; Lung_R, Lung_L =
controles de nao regressao): spacing original, task_id/resample/trainer de cada
configuracao, tempo, pico de VRAM, dice, hd95_mm, assd_mm, volume_error_pct,
FP_mL, FN_mL — para as DUAS configuracoes, medidos pelo MESMO codigo na mesma
execucao (o baseline e remedido a partir de `pred_masks/`, nao copiado de
tabela publicada).

Metrica primaria, declarada antes: MEDIANA do delta PAREADO por caso
(fast - baseline) do Dice. Pareado porque as duas configuracoes veem o mesmo
caso: a variancia entre casos, que e a maior desta coorte, sai da conta.
Classificacao pelos limiares congelados em fase5.py:

    delta_dice mediano >= +0,01  -> melhoria
    delta_dice mediano <= -0,01  -> regressao
    entre os dois              -> nenhum efeito discriminavel (NAO "igual")

Regressoes independentes (valem tambem quando o Dice melhora):
    delta_hd95 mediano >= +1,0 mm                              -> regressao HD95
    |volume_error_pct| mediano cresce >= 2,0 pontos percentuais -> regressao volume

Nenhum limiar, metrica ou caso foi escolhido depois de ver resultado.

TIER: bloco A (segmentacao). Uso educacional/experimental — "caso" e
"estrutura", nunca "paciente".

  python -m scripts.validation.tier2.experimento_spacing --autoteste
  python -m scripts.validation.tier2.experimento_spacing --selecao
  python -m scripts.validation.tier2.experimento_spacing
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import nibabel as nib
import numpy as np

from ..segmentation_metrics import compare_masks, dice as _dice
from . import fase5, geometria, mapeamento
from . import rtstruct as rtst
from .mapa_erro import _ml

RAIZ_PADRAO = fase5.RAIZ
SAIDA_PADRAO = RAIZ_PADRAO / "fase5" / "spacing"
SPLIT_USADO = "development"

NM = "nao medido"
NA = "nao aplicavel"

# ---------------------------------------------------------------- constantes
# Nenhuma vem do GT nem de resultado observado. Origem declarada em cada linha.

N_CASOS = 11              # entre 10 e 12, como pedido; 9 estratos + 2 de reforco
MM_ISOTROPICO = 1.5       # a grade interna do proprio TotalSegmentator (modo default)
ORDEM_MASCARA = 0         # vizinho mais proximo: mascara binaria nao interpola rotulo

ESTRUTURAS = tuple(fase5.ALVOS) + tuple(fase5.CONTROLES)

COLUNAS = (
    "dataset", "case_id", "instituicao", "structure", "gt_roi_name",
    "spacing_mm", "dx_mm", "dz_mm", "shape",
    "modelo_baseline", "modelo_fast",
    "tempo_baseline_s", "tempo_fast_s",
    "vram_pico_MiB", "vram_reservada_MiB", "vram_livre_antes_MiB",
    "volume_gt_mL", "volume_pred_baseline_mL", "volume_pred_fast_mL",
    "dice_baseline", "dice_fast", "delta_dice",
    "hd95_baseline_mm", "hd95_fast_mm", "delta_hd95_mm",
    "assd_baseline_mm", "assd_fast_mm", "delta_assd_mm",
    "volume_error_pct_baseline", "volume_error_pct_fast", "delta_abs_volume_pct",
    "FP_baseline_mL", "FP_fast_mL", "FN_baseline_mL", "FN_fast_mL",
    "dice_ida_e_volta_15mm", "alinhamento_baseline", "alinhamento_fast", "erro",
)


# ------------------------------------------------------------------ selecao


def _geometria_do_caso(raiz: Path, caso: str) -> dict:
    """Geometria da AQUISICAO, do header da imagem. Nao toca em mascara nenhuma."""
    d = geometria.descrever_nifti(raiz / caso / "gt" / rtst.NOME_IMAGEM)
    zooms = [round(float(z), 4) for z in d["zooms_mm"]]
    return {
        "case_id": caso,
        "instituicao": fase5.instituicao_de(caso),
        "spacing_mm": zooms,
        "dx_mm": zooms[0],
        "dz_mm": zooms[2],
        "shape": list(d["shape"]),
        "orientacao": d["orientacao"],
    }


def selecionar(geometrias: list[dict], n_casos: int = N_CASOS) -> dict:
    """Subconjunto declarado: 1 por estrato (instituicao, dx, dz) + reforco ate n.

    Deterministico e independente da ordem de entrada. Levanta se n_casos nao
    couber ao menos um caso por estrato — reduzir a cobertura em silencio seria
    escolher caso depois do fato.
    """
    estratos: dict[tuple, list[str]] = {}
    for g in geometrias:
        estratos.setdefault((g["instituicao"], g["dx_mm"], g["dz_mm"]), []).append(g["case_id"])
    for k in estratos:
        estratos[k].sort(key=fase5._ordem_deterministica)

    if n_casos < len(estratos):
        raise ValueError(
            f"n_casos={n_casos} nao cobre os {len(estratos)} estratos de aquisicao do "
            f"{SPLIT_USADO}; o criterio declarado exige ao menos um caso por estrato"
        )

    chaves = sorted(estratos)
    escolhidos = [estratos[k][0] for k in chaves]           # passo 1
    usados = {c: 1 for c in chaves}
    while len(escolhidos) < n_casos:                        # passo 2
        # maior estrato com caso sobrando; empate pela chave ordenada
        cand = [k for k in chaves if usados[k] < len(estratos[k])]
        if not cand:
            break
        k = max(cand, key=lambda k: (len(estratos[k]) - usados[k], [str(v) for v in k]))
        escolhidos.append(estratos[k][usados[k]])
        usados[k] += 1

    return {
        "criterio": (
            "1 caso por estrato (instituicao, dx_mm, dz_mm) na ordem "
            "sha256(semente|case_id); reforco pelo maior estrato ate n_casos"
        ),
        "n_casos": n_casos,
        "estratos": {
            "|".join(str(v) for v in k): {"n_disponivel": len(v), "n_usado": usados[k],
                                          "casos": v}
            for k, v in ((k, estratos[k]) for k in chaves)
        },
        "casos": sorted(escolhidos),
    }


# --------------------------------------------------------------- inferencia


def _config_ts(fast: bool) -> dict:
    """task_id / resample / trainer LIDOS do pacote instalado, nao digitados."""
    try:
        from totalsegmentator.map_tasks_config import TASK_CONFIGS
        sub = TASK_CONFIGS["total"]["sub_modes"]["fast" if fast else "default"]
        return {"fast": fast, "task_id": sub["task_id"],
                "resample_mm": sub["resample"], "trainer": sub["trainer"]}
    except Exception as e:  # pacote ausente num ambiente so de analise
        return {"fast": fast, "erro": f"{type(e).__name__}: {e}"}


def _vram():
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        return torch
    except Exception:
        return None


def segmentar_fast(raiz: Path, caso: str, saida: Path, log=print) -> dict:
    """Roda o TotalSegmentator com fast=True. Reusa a saida se ja estiver completa.

    Chama `scripts/clinica/segmentacao.py::rodar_segmentacao` — o MESMO codigo do
    baseline, com a unica diferenca sendo o argumento `fast`.
    """
    from scripts.clinica.segmentacao import rodar_segmentacao

    dir_pred = saida / "pred_fast" / caso
    alvos = mapeamento.roi_subset()
    completo = (dir_pred / "segmentacao.json").exists() and all(
        (dir_pred / f"{n}.nii.gz").exists() for n in alvos
    )
    if completo:
        info = json.loads((dir_pred / "segmentacao.json").read_text(encoding="utf-8"))
        log(f"  {caso}: predicao fast ja existe — reusada ({info.get('tempo_s')} s)")
        return {"dir": dir_pred, "reusado": True, **info,
                "vram_pico_MiB": info.get("vram_pico_MiB", NM),
                "vram_reservada_MiB": info.get("vram_reservada_MiB", NM),
                "vram_livre_antes_MiB": info.get("vram_livre_antes_MiB", NM)}

    torch = _vram()
    livre_antes = NM
    if torch is not None:
        torch.cuda.reset_peak_memory_stats()
        livre_antes = round(torch.cuda.mem_get_info()[0] / 2**20, 1)

    t0 = time.perf_counter()
    info = rodar_segmentacao(
        entrada=raiz / caso / "gt" / rtst.NOME_IMAGEM,
        saida_masks=dir_pred,
        estruturas=alvos,
        fast=True,
        log=log,
    )
    info["tempo_medido_s"] = round(time.perf_counter() - t0, 1)
    if torch is not None:
        info["vram_pico_MiB"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
        info["vram_reservada_MiB"] = round(torch.cuda.max_memory_reserved() / 2**20, 1)
        info["vram_livre_antes_MiB"] = livre_antes
    else:
        info["vram_pico_MiB"] = info["vram_reservada_MiB"] = NM
        info["vram_livre_antes_MiB"] = NM
    # regrava com VRAM junto, para o reuso nao perder a medida
    (dir_pred / "segmentacao.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"dir": dir_pred, "reusado": False, **info}


# ------------------------------------------------------------------ medidas


def _medidas(pred: np.ndarray, gt: np.ndarray, spacing) -> dict:
    """compare_masks + FP/FN em mL. Nao reimplementa metrica nenhuma."""
    m = compare_masks(pred, gt, spacing)
    voxel = float(np.prod(np.asarray(spacing, dtype=float)))
    return {
        "dice": m["dice"], "hd95_mm": m["hd95_mm"], "assd_mm": m["assd_mm"],
        "volume_error_pct": m["volume_error_pct"],
        "FP_mL": _ml(int(np.count_nonzero(pred & ~gt)), voxel),
        "FN_mL": _ml(int(np.count_nonzero(gt & ~pred)), voxel),
        "volume_pred_mL": _ml(int(np.count_nonzero(pred)), voxel),
    }


def custo_ida_e_volta(mascara: np.ndarray, affine: np.ndarray,
                      mm: float = MM_ISOTROPICO) -> float:
    """Dice de uma mascara consigo mesma depois de ir para `mm` isotropico e voltar.

    Sem GT: mede o CAMINHO, nao a predicao. E o limite inferior do artefato da
    alternativa (b) — cobre so o retorno da mascara, nao a ida do sinal.
    """
    from nibabel.processing import resample_from_to, resample_to_output

    orig = nib.Nifti1Image(np.asarray(mascara, dtype=np.uint8), affine)
    iso = resample_to_output(orig, voxel_sizes=mm, order=ORDEM_MASCARA)
    volta = resample_from_to(iso, orig, order=ORDEM_MASCARA)
    return _dice(np.asarray(volta.dataobj) > 0.5, np.asarray(mascara) > 0.5)


def _rois_do_gt(dir_gt: Path) -> dict[str, Path]:
    """Nome canonico -> arquivo. Os nomes vem do ARQUIVO, nunca da literatura."""
    achados: dict[str, Path] = {}
    for p in sorted(dir_gt.glob(f"{rtst.PREFIXO_MASCARA}*.nii.gz")):
        canon = mapeamento.canonizar(p.name[len(rtst.PREFIXO_MASCARA):].removesuffix(".nii.gz"))
        if canon:
            achados[canon] = p
    return achados


def medir_caso(raiz: Path, caso: str, dir_fast: Path, geo: dict,
               info_fast: dict, log=print) -> list[dict]:
    """Uma linha por estrutura, com as duas configuracoes medidas lado a lado."""
    dir_gt = raiz / caso / "gt"
    dir_base = raiz / caso / "pred_masks"
    spacing = tuple(geo["spacing_mm"])
    voxel = float(np.prod(np.asarray(spacing, dtype=float)))
    rois = _rois_do_gt(dir_gt)

    try:
        info_base = json.loads((dir_base / "segmentacao.json").read_text(encoding="utf-8"))
        tempo_base = info_base.get("tempo_s", NM)
    except (OSError, ValueError):
        tempo_base = NM

    linhas = []
    for estrutura in ESTRUTURAS:
        linha = {c: NM for c in COLUNAS}
        linha.update(
            dataset="LCTSC", case_id=caso, instituicao=geo["instituicao"],
            structure=estrutura, gt_roi_name=NM,
            spacing_mm=[round(float(s), 6) for s in spacing],
            dx_mm=geo["dx_mm"], dz_mm=geo["dz_mm"], shape=geo["shape"],
            modelo_baseline=_rotulo_modelo(_config_ts(False)),
            modelo_fast=_rotulo_modelo(_config_ts(True)),
            tempo_baseline_s=tempo_base,
            tempo_fast_s=info_fast.get("tempo_medido_s", info_fast.get("tempo_s", NM)),
            vram_pico_MiB=info_fast.get("vram_pico_MiB", NM),
            vram_reservada_MiB=info_fast.get("vram_reservada_MiB", NM),
            vram_livre_antes_MiB=info_fast.get("vram_livre_antes_MiB", NM),
            erro="",
        )
        try:
            if estrutura not in rois:
                raise FileNotFoundError(f"ROI {estrutura} ausente do GT deste caso")
            gt = rtst.carregar_mascara(rois[estrutura])
            alvos = mapeamento.MAPA_LCTSC[estrutura]
            pred_b, ref_b = mapeamento.unir_predicao(dir_base, alvos)
            pred_f, ref_f = mapeamento.unir_predicao(dir_fast, alvos)

            # Parte K: sem mesma grade, o numero seria mentira. Falha alto.
            geometria.verificar_alinhamento(ref_b, rois[estrutura], ("baseline", "gt"))
            geometria.verificar_alinhamento(ref_f, rois[estrutura], ("fast", "gt"))

            mb = _medidas(pred_b, gt, spacing)
            mf = _medidas(pred_f, gt, spacing)
            linha.update(
                gt_roi_name=rois[estrutura].name,
                volume_gt_mL=_ml(int(np.count_nonzero(gt)), voxel),
                volume_pred_baseline_mL=mb["volume_pred_mL"],
                volume_pred_fast_mL=mf["volume_pred_mL"],
                dice_baseline=mb["dice"], dice_fast=mf["dice"],
                delta_dice=mf["dice"] - mb["dice"],
                hd95_baseline_mm=mb["hd95_mm"], hd95_fast_mm=mf["hd95_mm"],
                delta_hd95_mm=mf["hd95_mm"] - mb["hd95_mm"],
                assd_baseline_mm=mb["assd_mm"], assd_fast_mm=mf["assd_mm"],
                delta_assd_mm=mf["assd_mm"] - mb["assd_mm"],
                volume_error_pct_baseline=mb["volume_error_pct"],
                volume_error_pct_fast=mf["volume_error_pct"],
                delta_abs_volume_pct=abs(mf["volume_error_pct"]) - abs(mb["volume_error_pct"]),
                FP_baseline_mL=mb["FP_mL"], FP_fast_mL=mf["FP_mL"],
                FN_baseline_mL=mb["FN_mL"], FN_fast_mL=mf["FN_mL"],
                dice_ida_e_volta_15mm=custo_ida_e_volta(
                    pred_b, nib.load(str(ref_b)).affine),
                alinhamento_baseline="mesma grade", alinhamento_fast="mesma grade",
            )
            log(f"  {caso} {estrutura}: dice {mb['dice']:.4f} -> {mf['dice']:.4f} "
                f"(delta {linha['delta_dice']:+.4f})")
        except Exception as e:
            linha["erro"] = f"{type(e).__name__}: {e}"
            log(f"  {caso} {estrutura}: ERRO {linha['erro']}")
        linhas.append(linha)
    return linhas


def _rotulo_modelo(cfg: dict) -> str:
    if "erro" in cfg:
        return NM
    return f"resample {cfg['resample_mm']} mm · task {cfg['task_id']} · {cfg['trainer']}"


# ---------------------------------------------------------------- agregacao


def _num(linhas, coluna) -> list[float]:
    v = [l[coluna] for l in linhas if isinstance(l.get(coluna), (int, float))]
    return [float(x) for x in v if np.isfinite(x)]


def _mediana(v: list[float]):
    return float(np.median(v)) if v else NM


def veredito(delta_dice_mediano, delta_hd95_mediano, delta_abs_vol_mediano) -> dict:
    """Classificacao pelos limiares congelados em fase5.py. Nada e escolhido aqui."""
    def _cmp(v, alvo):
        return isinstance(v, (int, float)) and np.isfinite(v) and v >= alvo

    if not isinstance(delta_dice_mediano, (int, float)):
        return {"dice": NM, "hd95": NM, "volume": NM}
    d = float(delta_dice_mediano)
    if d >= fase5.LIMIAR_MELHORIA_DICE:
        efeito = f"melhoria (>= +{fase5.LIMIAR_MELHORIA_DICE})"
    elif d <= -fase5.LIMIAR_REGRESSAO_DICE:
        efeito = f"regressao (<= -{fase5.LIMIAR_REGRESSAO_DICE})"
    else:
        efeito = "nenhum efeito discriminavel pelos limiares declarados"
    return {
        "dice": efeito,
        "hd95": ("regressao HD95" if _cmp(delta_hd95_mediano, fase5.LIMIAR_REGRESSAO_HD95_MM)
                 else "sem regressao HD95"),
        "volume": ("regressao de volume"
                   if _cmp(delta_abs_vol_mediano, fase5.LIMIAR_REGRESSAO_VOLUME_PCT)
                   else "sem regressao de volume"),
    }


def agregar(linhas: list[dict]) -> dict:
    validas = [l for l in linhas if not l["erro"]]
    por_estrutura = {}
    for e in ESTRUTURAS:
        sub = [l for l in validas if l["structure"] == e]
        dd = _num(sub, "delta_dice")
        agg = {
            "n": len(sub),
            "dice_baseline_mediana": _mediana(_num(sub, "dice_baseline")),
            "dice_fast_mediana": _mediana(_num(sub, "dice_fast")),
            "delta_dice_mediano": _mediana(dd),
            "delta_dice_p5": float(np.percentile(dd, 5)) if dd else NM,
            "delta_dice_p95": float(np.percentile(dd, 95)) if dd else NM,
            "n_casos_delta_positivo": int(sum(1 for x in dd if x > 0)),
            "n_casos_delta_acima_do_limiar": int(
                sum(1 for x in dd if abs(x) >= fase5.LIMIAR_MELHORIA_DICE)),
            "hd95_baseline_mediana": _mediana(_num(sub, "hd95_baseline_mm")),
            "hd95_fast_mediana": _mediana(_num(sub, "hd95_fast_mm")),
            "delta_hd95_mediano": _mediana(_num(sub, "delta_hd95_mm")),
            "assd_baseline_mediana": _mediana(_num(sub, "assd_baseline_mm")),
            "assd_fast_mediana": _mediana(_num(sub, "assd_fast_mm")),
            "delta_assd_mediano": _mediana(_num(sub, "delta_assd_mm")),
            "volume_error_pct_baseline_mediano": _mediana(_num(sub, "volume_error_pct_baseline")),
            "volume_error_pct_fast_mediano": _mediana(_num(sub, "volume_error_pct_fast")),
            "delta_abs_volume_pct_mediano": _mediana(_num(sub, "delta_abs_volume_pct")),
            "FP_baseline_mediana_mL": _mediana(_num(sub, "FP_baseline_mL")),
            "FP_fast_mediana_mL": _mediana(_num(sub, "FP_fast_mL")),
            "FN_baseline_mediana_mL": _mediana(_num(sub, "FN_baseline_mL")),
            "FN_fast_mediana_mL": _mediana(_num(sub, "FN_fast_mL")),
        }
        agg["veredito"] = veredito(agg["delta_dice_mediano"], agg["delta_hd95_mediano"],
                                   agg["delta_abs_volume_pct_mediano"])
        agg["papel"] = "alvo" if e in fase5.ALVOS else "controle de nao regressao"
        por_estrutura[e] = agg

    # estratificado por dz — a heterogeneidade que motivou o experimento
    por_dz = {}
    for dz in sorted({l["dz_mm"] for l in validas}):
        bloco = {}
        for e in ESTRUTURAS:
            sub = [l for l in validas if l["structure"] == e and l["dz_mm"] == dz]
            bloco[e] = {
                "n": len(sub),
                "dice_baseline_mediana": _mediana(_num(sub, "dice_baseline")),
                "dice_fast_mediana": _mediana(_num(sub, "dice_fast")),
                "delta_dice_mediano": _mediana(_num(sub, "delta_dice")),
            }
        por_dz[str(dz)] = bloco

    custos = _num(validas, "dice_ida_e_volta_15mm")
    custo_por_estrutura = {
        e: _mediana(_num([l for l in validas if l["structure"] == e], "dice_ida_e_volta_15mm"))
        for e in ESTRUTURAS
    }
    tempos_b = _num(validas, "tempo_baseline_s")
    tempos_f = _num(validas, "tempo_fast_s")
    return {
        "por_estrutura": por_estrutura,
        "por_dz": por_dz,
        "custo_ida_e_volta": {
            "n_medidas": len(custos),
            "dice_mediano": _mediana(custos),
            "dice_minimo": float(min(custos)) if custos else NM,
            "dice_mediano_por_estrutura": custo_por_estrutura,
            "perda_mediana_de_dice": (1.0 - _mediana(custos)) if custos else NM,
            "limiar_de_melhoria": fase5.LIMIAR_MELHORIA_DICE,
            "veredito": (
                "o retorno de grade sozinho custa MAIS que o menor efeito declarado "
                "como melhoria — a alternativa (b) nao seria interpretavel"
                if custos and (1.0 - _mediana(custos)) >= fase5.LIMIAR_MELHORIA_DICE
                else "o retorno de grade custa menos que o limiar de melhoria (ver ressalvas)"
            ),
        },
        "custo_computacional": {
            "tempo_baseline_mediano_s": _mediana(tempos_b),
            "tempo_fast_mediano_s": _mediana(tempos_f),
            "vram_pico_mediano_MiB": _mediana(_num(validas, "vram_pico_MiB")),
            "vram_reservada_mediana_MiB": _mediana(_num(validas, "vram_reservada_MiB")),
            "ressalva_tempo": (
                "o tempo do baseline vem do segmentacao.json do run congelado (outra "
                "execucao, outra carga de GPU); o do fast foi medido agora. A comparacao "
                "de tempo e indicativa, nao um benchmark pareado."
            ),
        },
    }


# ------------------------------------------------------------------ execucao


def rodar(raiz: Path = RAIZ_PADRAO, saida: Path = SAIDA_PADRAO,
          casos: list[str] | None = None, n_casos: int = N_CASOS, log=print) -> dict:
    dev = fase5.carregar_split(raiz)[SPLIT_USADO]
    geos = [_geometria_do_caso(raiz, c) for c in dev]
    sel = selecionar(geos, n_casos)
    escolhidos = casos or sel["casos"]
    por_caso = {g["case_id"]: g for g in geos}

    log(f"{SPLIT_USADO}: {len(dev)} casos · {len(sel['estratos'])} estratos de aquisicao")
    log(f"selecionados ({len(escolhidos)}): {escolhidos}")

    (saida / "casos").mkdir(parents=True, exist_ok=True)
    linhas: list[dict] = []
    for i, caso in enumerate(escolhidos, 1):
        log(f"[{i}/{len(escolhidos)}] {caso} · spacing {por_caso[caso]['spacing_mm']}")
        try:
            info = segmentar_fast(raiz, caso, saida, log=log)
            l = medir_caso(raiz, caso, info["dir"], por_caso[caso], info, log=log)
        except Exception as e:  # um caso que falha nao derruba a coorte
            log(f"  {caso}: FALHOU — {type(e).__name__}: {e}")
            l = [{**{c: NM for c in COLUNAS}, "case_id": caso, "structure": e_,
                  "erro": f"{type(e).__name__}: {e}"} for e_ in ESTRUTURAS]
        linhas.extend(l)
        (saida / "casos" / f"{caso}.json").write_text(
            json.dumps(l, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pergunta": "a heterogeneidade de spacing contribui para o erro?",
        "erro_atacado": {"E7": fase5.TAXONOMIA["E7"]},
        "split_usado": SPLIT_USADO,
        "selecao": sel,
        "casos_rodados": escolhidos,
        "comparacao": {
            "escolhida": "(a) fast=True contra o baseline fast=False — a entrada nao e tocada",
            "recusada": "(b) reamostrar a entrada para isotropico — dupla reamostragem",
            "baseline": _config_ts(False),
            "experimental": _config_ts(True),
            "confundimento_declarado": (
                "fast troca resolucao interna, modelo e trainer de uma vez; o "
                "confundimento esta na ferramenta, nao no desenho"
            ),
        },
        "criterios": {
            "metrica_primaria": "mediana do delta pareado por caso do Dice (fast - baseline)",
            "limiar_melhoria_dice": fase5.LIMIAR_MELHORIA_DICE,
            "limiar_regressao_dice": fase5.LIMIAR_REGRESSAO_DICE,
            "limiar_regressao_hd95_mm": fase5.LIMIAR_REGRESSAO_HD95_MM,
            "limiar_regressao_volume_pct": fase5.LIMIAR_REGRESSAO_VOLUME_PCT,
            "declarados_antes": True,
        },
        "resumo": agregar(linhas),
        "linhas": linhas,
    }


# ------------------------------------------------------------------ relatorio


def _f(v, casas=4) -> str:
    if isinstance(v, (int, float)) and np.isfinite(v):
        return f"{v:.{casas}f}".replace(".", ",")
    return str(v)


def _summary_md(r: dict) -> str:
    res = r["resumo"]
    L = [
        "# Parte 8 — experimento de RESOLUCAO (E7)",
        "",
        f"Gerado em {r['gerado_em']} · split `{r['split_usado']}` · "
        f"n = {len(r['casos_rodados'])} casos.",
        "",
        "## Comparacao",
        "",
        f"- ESCOLHIDA: {r['comparacao']['escolhida']}",
        f"- RECUSADA: {r['comparacao']['recusada']}",
        f"- baseline: `{_rotulo_modelo(r['comparacao']['baseline'])}`",
        f"- experimental: `{_rotulo_modelo(r['comparacao']['experimental'])}`",
        f"- confundimento declarado: {r['comparacao']['confundimento_declarado']}",
        "",
        "## Selecao (criterio declarado ANTES de rodar)",
        "",
        f"`{r['selecao']['criterio']}`",
        "",
        "| estrato (instituicao · dx · dz) | disponiveis | usados |",
        "|---|---|---|",
    ]
    for k, v in r["selecao"]["estratos"].items():
        L.append(f"| {k.replace('|', ' · ')} | {v['n_disponivel']} | {v['n_usado']} |")

    L += ["", "## Por estrutura — delta PAREADO (fast - baseline)", "",
          "`delta mediano` = mediana do delta POR CASO, nao a diferenca das medianas — "
          "as duas colunas ao lado sao medianas independentes e nao subtraem uma da outra.",
          "",
          "| estrutura | papel | n | dice base | dice fast | delta mediano | "
          "P5 | P95 | casos com abs(delta) >= 0,01 | veredito |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for e, a in res["por_estrutura"].items():
        L.append(
            f"| {e} | {a['papel']} | {a['n']} | {_f(a['dice_baseline_mediana'])} | "
            f"{_f(a['dice_fast_mediana'])} | {_f(a['delta_dice_mediano'])} | "
            f"{_f(a['delta_dice_p5'])} | {_f(a['delta_dice_p95'])} | "
            f"{a['n_casos_delta_acima_do_limiar']}/{a['n']} | {a['veredito']['dice']} |")

    L += ["", "### Regressoes independentes", "",
          "| estrutura | HD95 base | HD95 fast | delta | ASSD base | ASSD fast | "
          "delta | vol% base | vol% fast | delta abs | veredito HD95 | veredito volume |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e, a in res["por_estrutura"].items():
        L.append(
            f"| {e} | {_f(a['hd95_baseline_mediana'],3)} | {_f(a['hd95_fast_mediana'],3)} | "
            f"{_f(a['delta_hd95_mediano'],3)} | {_f(a['assd_baseline_mediana'],3)} | "
            f"{_f(a['assd_fast_mediana'],3)} | {_f(a['delta_assd_mediano'],3)} | "
            f"{_f(a['volume_error_pct_baseline_mediano'],2)} | "
            f"{_f(a['volume_error_pct_fast_mediano'],2)} | "
            f"{_f(a['delta_abs_volume_pct_mediano'],2)} | {a['veredito']['hd95']} | "
            f"{a['veredito']['volume']} |")

    L += ["", "### FP / FN medianos (mL)", "",
          "| estrutura | FP base | FP fast | FN base | FN fast |", "|---|---|---|---|---|"]
    for e, a in res["por_estrutura"].items():
        L.append(f"| {e} | {_f(a['FP_baseline_mediana_mL'],3)} | {_f(a['FP_fast_mediana_mL'],3)} | "
                 f"{_f(a['FN_baseline_mediana_mL'],3)} | {_f(a['FN_fast_mediana_mL'],3)} |")

    L += ["", "## Estratificado por dz (a heterogeneidade que motivou o experimento)", "",
          "| dz (mm) | estrutura | n | dice base | dice fast | delta mediano |",
          "|---|---|---|---|---|---|"]
    for dz, bloco in res["por_dz"].items():
        for e, a in bloco.items():
            L.append(f"| {dz} | {e} | {a['n']} | {_f(a['dice_baseline_mediana'])} | "
                     f"{_f(a['dice_fast_mediana'])} | {_f(a['delta_dice_mediano'])} |")

    c = res["custo_ida_e_volta"]
    cc = res["custo_computacional"]
    L += ["", "## Por que (b) nao foi executada — custo medido do retorno de grade", "",
          f"- medidas: {c['n_medidas']} (mascara do baseline -> {MM_ISOTROPICO} mm "
          f"isotropico -> grade original, sem GT)",
          f"- Dice mediano da mascara consigo mesma: {_f(c['dice_mediano'])} "
          f"(minimo {_f(c['dice_minimo'])})",
          f"- perda mediana de Dice so no retorno: {_f(c['perda_mediana_de_dice'])} "
          f"contra limiar de melhoria de {c['limiar_de_melhoria']}",
          f"- veredito: {c['veredito']}",
          "- e um LIMITE INFERIOR: cobre so o retorno da mascara, nao a interpolacao "
          "do sinal na ida.",
          "",
          "| estrutura | Dice mediano da mascara consigo mesma | perda |",
          "|---|---|---|",
          *[f"| {e} | {_f(v)} | {_f(1.0 - v) if isinstance(v, float) else v} |"
            for e, v in c["dice_mediano_por_estrutura"].items()],
          "", "## Custo computacional", "",
          f"- tempo mediano baseline: {_f(cc['tempo_baseline_mediano_s'],1)} s",
          f"- tempo mediano fast: {_f(cc['tempo_fast_mediano_s'],1)} s",
          f"- pico de VRAM (torch, processo) mediano: {_f(cc['vram_pico_mediano_MiB'],1)} MiB "
          f"· reservada {_f(cc['vram_reservada_mediana_MiB'],1)} MiB",
          f"- ressalva: {cc['ressalva_tempo']}", ""]
    return "\n".join(L)


def gravar(r: dict, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    p_json = saida / "experimento_spacing.json"
    p_csv = saida / "experimento_spacing.csv"
    p_md = saida / "RESUMO.md"

    p_json.write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str),
                      encoding="utf-8")
    with p_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(COLUNAS))
        w.writeheader()
        for l in r["linhas"]:
            w.writerow({c: l.get(c, NM) for c in COLUNAS})
    p_md.write_text(_summary_md(r), encoding="utf-8")
    log(f"gravado: {p_json} · {p_csv} · {p_md}")
    return {"json": p_json, "csv": p_csv, "md": p_md}


# ------------------------------------------------------------------ autoteste


def _autoteste() -> None:
    """Controles POSITIVOS: cada instrumento tem que FALHAR quando deveria falhar."""
    # (1) selecao: cobre todo estrato, e deterministica e independente da ordem
    geos = [
        {"case_id": f"LCTSC-Train-S1-{i:03d}", "instituicao": "S1", "dx_mm": 0.9766,
         "dz_mm": 3.0} for i in range(1, 6)
    ] + [
        {"case_id": f"LCTSC-Train-S2-{i:03d}", "instituicao": "S2", "dx_mm": 0.9766,
         "dz_mm": 2.5} for i in range(1, 5)
    ] + [
        {"case_id": "LCTSC-Train-S3-001", "instituicao": "S3", "dx_mm": 1.1719, "dz_mm": 2.0},
        {"case_id": "LCTSC-Train-S3-002", "instituicao": "S3", "dx_mm": 0.9766, "dz_mm": 1.25},
    ]
    s = selecionar(geos, 6)
    assert len(s["casos"]) == 6, s["casos"]
    assert len(s["estratos"]) == 4, s["estratos"]
    # todo estrato representado — a propriedade que o criterio promete
    inst_dz = {(g["instituicao"], g["dz_mm"]) for g in geos
               if g["case_id"] in s["casos"]}
    assert len(inst_dz) == 4, inst_dz
    assert selecionar(list(reversed(geos)), 6)["casos"] == s["casos"], "selecao depende da ordem"
    # CONTROLE POSITIVO: pedir menos casos que estratos tem que FALHAR
    try:
        selecionar(geos, 3)
    except ValueError as e:
        assert "estratos" in str(e), e
    else:
        raise AssertionError("selecao aceitou n menor que o numero de estratos")

    # (2) veredito: os tres desfechos e a regressao que sobrevive a um Dice melhor
    assert veredito(0.02, 0.0, 0.0)["dice"].startswith("melhoria"), veredito(0.02, 0.0, 0.0)
    assert veredito(-0.02, 0.0, 0.0)["dice"].startswith("regressao")
    assert "nenhum efeito" in veredito(0.005, 0.0, 0.0)["dice"]
    assert "nenhum efeito" in veredito(-0.009, 0.0, 0.0)["dice"]
    # CONTROLE POSITIVO: Dice melhor NAO pode apagar regressao de HD95 nem de volume
    v = veredito(0.05, 1.5, 3.0)
    assert v["dice"].startswith("melhoria") and v["hd95"] == "regressao HD95" \
        and v["volume"] == "regressao de volume", v
    assert veredito(0.05, 0.9, 1.9)["hd95"] == "sem regressao HD95"

    # (3) custo_ida_e_volta: no-op da 1,0; grade anisotropica com estrutura fina NAO da
    cubo = np.zeros((40, 40, 40), dtype=bool)
    cubo[12:28, 12:28, 12:28] = True
    iso = np.diag([MM_ISOTROPICO, MM_ISOTROPICO, MM_ISOTROPICO, 1.0])
    d_noop = custo_ida_e_volta(cubo, iso)
    assert d_noop == 1.0, f"round trip numa grade que ja e {MM_ISOTROPICO} mm mudou a mascara: {d_noop}"
    fina = np.zeros((40, 40, 60), dtype=bool)
    fina[18:22, 18:22, 5:55] = True          # medula sintetica: 4 x 4 voxels de secao
    d_aniso = custo_ida_e_volta(fina, np.diag([0.9766, 0.9766, 3.0, 1.0]))
    assert d_aniso < 1.0, "o instrumento nao viu artefato nenhum numa grade anisotropica"
    assert 1.0 - d_aniso >= fase5.LIMIAR_MELHORIA_DICE, (
        f"perda {1.0 - d_aniso} — controle esperava artefato acima do limiar")

    # (4) _medidas: FP/FN tem sinal certo e o Dice cai quando deve
    from scipy.ndimage import binary_dilation
    sp = (0.9766, 0.9766, 3.0)
    m_id = _medidas(cubo, cubo, sp)
    assert m_id["dice"] == 1.0 and m_id["FP_mL"] == 0.0 and m_id["FN_mL"] == 0.0, m_id
    m_dil = _medidas(binary_dilation(cubo), cubo, sp)
    assert m_dil["FN_mL"] == 0.0 and m_dil["FP_mL"] > 0.0 and m_dil["dice"] < 1.0, m_dil
    m_ero = _medidas(cubo & ~binary_dilation(~cubo), cubo, sp)
    assert m_ero["FP_mL"] == 0.0 and m_ero["FN_mL"] > 0.0, m_ero

    # (5) agregacao: uma regressao plantada tem que sair como regressao
    base = {c: NM for c in COLUNAS}
    linhas = []
    for i in range(5):
        linhas.append({**base, "structure": "SpinalCord", "dz_mm": 3.0, "erro": "",
                       "dice_baseline": 0.80, "dice_fast": 0.75, "delta_dice": -0.05,
                       "delta_hd95_mm": 2.0, "delta_abs_volume_pct": 5.0,
                       "case_id": f"c{i}"})
    for e in ESTRUTURAS[1:]:
        linhas.append({**base, "structure": e, "dz_mm": 3.0, "erro": "",
                       "dice_baseline": 0.9, "dice_fast": 0.9, "delta_dice": 0.0,
                       "delta_hd95_mm": 0.0, "delta_abs_volume_pct": 0.0, "case_id": "c0"})
    a = agregar(linhas)["por_estrutura"]["SpinalCord"]
    assert a["veredito"]["dice"].startswith("regressao"), a["veredito"]
    assert a["veredito"]["hd95"] == "regressao HD95" and a["veredito"]["volume"] == "regressao de volume"
    assert a["n_casos_delta_acima_do_limiar"] == 5, a
    # linha com erro nao pode entrar na conta
    a2 = agregar(linhas + [{**base, "structure": "SpinalCord", "dz_mm": 3.0,
                            "erro": "boom", "delta_dice": 99.0}])["por_estrutura"]["SpinalCord"]
    assert a2["n"] == 5 and a2["delta_dice_mediano"] == a["delta_dice_mediano"], a2

    print("experimento_spacing.py: autoteste OK (5 blocos de controle)")


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--selecao", action="store_true",
                    help="imprime o subconjunto declarado e sai, sem tocar na GPU")
    ap.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    ap.add_argument("--n-casos", type=int, default=N_CASOS)
    ap.add_argument("--caso", action="append", help="limita a estes casos (debug)")
    a = ap.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0
    if a.selecao:
        dev = fase5.carregar_split(a.raiz)[SPLIT_USADO]
        sel = selecionar([_geometria_do_caso(a.raiz, c) for c in dev], a.n_casos)
        print(json.dumps(sel, indent=2, ensure_ascii=False))
        return 0

    r = rodar(raiz=a.raiz, saida=a.saida, casos=a.caso, n_casos=a.n_casos)
    gravar(r, saida=a.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
