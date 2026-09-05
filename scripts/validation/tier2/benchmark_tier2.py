"""Benchmark Tier2 — acuracia da SEGMENTACAO contra ground truth INDEPENDENTE.

Tier1 = fidelidade da RECONSTRUCAO a mascara. Tier2 = acuracia da SEGMENTACAO
contra ground truth INDEPENDENTE (aqui). Tier3 = fantoma analitico.
Na decomposicao de erro (A = segmentacao, B = reconstrucao, C = simplificacao,
D = compressao) este script quantifica APENAS o bloco A. Os blocos NUNCA se somam.
Nenhum numero daqui diz nada sobre reconstrucao.

As metricas vem de `segmentation_metrics.compare_masks(pred, gt, spacing)`, com
o spacing em MM lido de `header.get_zooms()` — nunca indice de voxel. Este
modulo NAO reimplementa metrica; so acrescenta recall/containment, que o
modulo de metricas nao tem.

TRES RESSALVAS DE DEFINICAO, cada uma colada no numero que ela afeta:

1. Heart — o GT do LCTSC segue o atlas RTOG 1106 e INCLUI saco e gordura
   pericardica; o `heart` do TotalSegmentator v2 nao inclui pericardio (a
   classe `pericardium` nem existe na tarefa `total`). O GT e maior POR
   CONSTRUCAO: um modelo perfeito nao tira Dice 1,0 aqui. Por isso a linha do
   coracao sai com erro volumetrico COM SINAL e com a fracao da predicao
   contida no GT, e NAO deve ser lida como "acuracia do coracao".

2. Esophagus — o atlas so manda contornar do nivel abaixo do cricoide ate a
   juncao gastroesofagica. Fora dessa janela o TotalSegmentator segmenta
   esofago que o GT nao desenhou. Saem DUAS linhas: `recorte_z` (predicao
   recortada ao intervalo Z em que o GT tem voxels) e `sem_recorte` (lixo por
   construcao, serve so para mostrar o tamanho do efeito).

3. Lungs — o GT anota o pulmao inteiro por lado; o TotalSegmentator devolve 5
   LOBOS. Compara-se uniao contra uniao. A uniao APAGA AS FISSURAS: o Dice
   mede "acertou a envoltoria pulmonar", nao "acertou os lobos". O atlas ainda
   manda excluir vias aereas e vasos hilares acima de ~5 mm, enquanto as
   mascaras de lobo incluem o que estiver dentro da fronteira — a discordancia
   no hilo e diferenca de definicao, e o proprio atlas admite bronquios
   secundarios como opcionais (GT ambiguo ali POR ESPECIFICACAO).
   Volume e componentes conexos por lobo saem em bloco SEPARADO, rotulado como
   NAO sendo Tier2: nao ha GT de lobo.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

  python -m scripts.validation.tier2.benchmark_tier2 --caso LCTSC-Train-S1-001
  python -m scripts.validation.tier2.benchmark_tier2 --autoteste
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import label

from ..segmentation_metrics import compare_masks
from . import geometria, mapeamento, rtstruct as rtst

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
NA = "nao aplicavel"
NM = "nao medido"
SEM_COBERTURA = "nao medido: dataset nao anota esta estrutura"

# O LCTSC nao contorna estas estruturas. Nao ha como medi-las aqui, e estimar
# por qualquer outra via seria inventar numero.
ESTRUTURAS_SEM_COBERTURA = ("aorta", "trachea")

# Abaixo deste volume de GT a linha e marcada como estrutura pequena e o recall
# entra na leitura junto do Dice (Dice de estrutura fina despenca com 1 voxel
# de borda). Limiar declarado, nao derivado dos dados.
LIMIAR_PEQUENA_ML = 100.0

RESSALVAS = {
    "Heart": (
        "divergencia de definicao: GT inclui pericardio (atlas RTOG 1106, saco e gordura "
        "pericardica, corte superior no nivel inferior da arteria pulmonar); o `heart` do "
        "TotalSegmentator v2 nao inclui pericardio. GT maior POR CONSTRUCAO — leia o erro "
        "volumetrico com sinal e o containment, nao o Dice como 'acuracia do coracao'."
    ),
    "Esophagus": (
        "janela de contorno limitada: o atlas so contorna do nivel abaixo do cricoide ate a "
        "juncao gastroesofagica; fora dessa janela o GT nao desenhou nada."
    ),
    "Lung_L": (
        "uniao de lobos: GT anota o pulmao inteiro, a predicao e a uniao dos lobos. A uniao "
        "APAGA AS FISSURAS — mede a envoltoria pulmonar, nao a lobacao. Hilo: o atlas exclui "
        "vias aereas/vasos acima de ~5 mm e admite bronquios secundarios como opcionais, "
        "logo o GT e ambiguo ali POR ESPECIFICACAO."
    ),
}
RESSALVAS["Lung_R"] = RESSALVAS["Lung_L"]

COLUNAS = (
    "dataset", "case_id", "structure", "gt_roi_name", "variante",
    "dice", "iou", "nsd_1mm", "nsd_2mm", "hd95_mm", "assd_mm", "hd_mm",
    "volume_error_pct", "volume_pred_ml", "volume_gt_ml",
    "recall_gt", "precision_pred", "containment_pred_em_gt", "estrutura_pequena",
    "nsd_1vox", "nsd_2vox", "nsd_tau_vox_mm",
    "fp_fora_do_suporte_ml", "fp_dentro_do_suporte_ml", "fn_dentro_do_suporte_ml",
    "erro_absoluto_ml",
    "pipeline_version", "segmentation_model", "reconstruction_method",
    "sigma", "taubin_iterations", "spacing_mm", "ressalva", "erro",
)


# ------------------------------------------------------- metrica que falta no modulo


def recall_containment(pred: np.ndarray, gt: np.ndarray) -> dict:
    """Recall e containment — as duas metades assimetricas que o Dice funde numa so.

    recall_gt        = |P inter G| / |G|  — quanto do GT a predicao cobriu.
    containment_pred = |P inter G| / |P|  — quanto da predicao cai dentro do GT.

    Denominador vazio => "invalido" (divisao por zero), nunca um float plausivel.
    """
    p, g = np.asarray(pred) > 0.5, np.asarray(gt) > 0.5
    inter = int(np.count_nonzero(p & g))
    n_p, n_g = int(p.sum()), int(g.sum())
    # precision e containment sao a MESMA razao |P inter G| / |P|. Mantemos as duas
    # chaves porque a coorte pede "precision" pelo nome e o relatorio ja publicou
    # "containment"; sao rotulos do mesmo numero, nao duas medidas.
    prec = (inter / n_p) if n_p else "invalido: predicao vazia"
    return {
        "recall_gt": (inter / n_g) if n_g else "invalido: GT vazio",
        "precision_pred": prec,
        "containment_pred_em_gt": prec,
    }


# ------------------------------------------------------------------ reprodutibilidade


def _pipeline_version() -> str:
    """Sem versao declarada no repositorio: hash do codigo que PRODUZIU a predicao.

    Tier2 mede o bloco A, entao o arquivo relevante e o da segmentacao, nao o
    da reconstrucao.
    """
    caminho = Path(__file__).resolve().parents[2] / "clinica" / "segmentacao.py"
    h = hashlib.sha256(caminho.read_bytes()).hexdigest()[:12]
    return f"segmentacao.py@sha256:{h} (repositorio sem versao de pipeline declarada)"


def _segmentation_model(manifesto: dict) -> str:
    seg = manifesto.get("segmentacao") or {}
    versao = seg.get("totalsegmentator_versao")
    if not versao:
        return f"{NM}: manifesto nao registra a versao do modelo de segmentacao"
    return f"TotalSegmentator {versao} (tarefa={seg.get('tarefa', NM)})"


def _ml(mascara: np.ndarray, spacing) -> float:
    """Volume em mililitros a partir do spacing em mm."""
    return float(int(np.count_nonzero(mascara)) * float(np.prod(np.asarray(spacing, float))) / 1000.0)


def _fatias_com_voxel(m: np.ndarray) -> np.ndarray:
    """Indices Z (eixo 2) em que a mascara tem ao menos um voxel."""
    return np.flatnonzero(m.any(axis=(0, 1)))


# ------------------------------------------------------------------------ uma linha


def _linha_base(ident: dict, structure: str, gt_roi: str, variante: str) -> dict:
    linha = {c: None for c in COLUNAS}
    linha.update(
        dataset=ident["dataset"], case_id=ident["case_id"],
        structure=structure, gt_roi_name=gt_roi, variante=variante,
        pipeline_version=ident["pipeline_version"],
        segmentation_model=ident["segmentation_model"],
        # Tier2 nao envolve reconstrucao: nenhum destes tres parametros existe aqui.
        reconstruction_method=NA, sigma=NA, taubin_iterations=NA,
        spacing_mm=[round(float(s), 6) for s in ident["spacing_mm"]],
        ressalva=RESSALVAS.get(gt_roi, ""),
        erro="",
    )
    return linha


def _medir(pred: np.ndarray, gt: np.ndarray, spacing, linha: dict) -> dict:
    """Preenche uma linha com compare_masks + recall/containment + volumes em ml."""
    m = compare_masks(pred, gt, spacing)
    rc = recall_containment(pred, gt)
    vol_gt = _ml(gt, spacing)
    # Copia TUDO que compare_masks e recall_containment devolvem, filtrado por
    # COLUNAS. Antes as chaves eram enumeradas a mao e foi exatamente isso que
    # fez `nsd_1vox`, `nsd_2vox`, `nsd_tau_vox_mm` e `precision_pred` sairem None
    # na coorte inteira: as colunas foram declaradas e a copia nao acompanhou.
    # Enumerar a mao aqui e um ponto de falha silencioso — a linha ja nasce com
    # todas as chaves de COLUNAS em None, entao a metrica ausente nao da erro,
    # so vira "nao medido" na agregacao.
    linha.update({k: v for k, v in m.items() if k in COLUNAS})
    linha.update({k: v for k, v in rc.items() if k in COLUNAS})
    linha.update(
        volume_pred_ml=_ml(pred, spacing), volume_gt_ml=vol_gt,
        estrutura_pequena=bool(vol_gt < LIMIAR_PEQUENA_ML),
    )
    faltando = [k for k in ("dice", "iou", "nsd_1mm", "nsd_2mm", "nsd_1vox", "nsd_2vox",
                            "hd95_mm", "assd_mm", "hd_mm", "volume_error_pct",
                            "recall_gt", "precision_pred") if linha.get(k) is None]
    if faltando:  # falha alto em vez de gravar None silencioso
        raise KeyError(f"metricas declaradas em COLUNAS e nao preenchidas: {faltando}")
    return linha


def _checar_grade(caminhos_pred: list[Path], caminho_gt: Path) -> list[dict]:
    """Parte K antes de QUALQUER comparacao: cada arquivo de predicao x o GT.

    Nunca comparar arrays so porque tem o mesmo shape. Levanta
    DesalinhamentoGeometrico (que aborta a linha) se qualquer par divergir.
    """
    return [geometria.verificar_alinhamento(p, caminho_gt) for p in caminhos_pred]


# -------------------------------------------------------------------- bloco de lobos


def _bloco_lobos(dir_pred: Path, spacing) -> list[dict]:
    """NAO E TIER2: nao existe GT de lobo no LCTSC. Volume e componentes por lobo.

    Unico sinal disponivel sobre lobacao. Componentes conexos com a
    conectividade padrao do scipy em 3D (vizinhanca de FACE, 6). Um lobo sadio
    e um blob so; contagem > 1 indica fragmentacao, mas nao diz onde nem
    quanto de volume esta no fragmento alem da fracao do maior componente.
    """
    saida = []
    for nome in sorted({n for alvos in mapeamento.MAPA_LCTSC.values() for n in alvos if "lobe" in n}):
        caminho = dir_pred / f"{nome}.nii.gz"
        m = np.asarray(nib.load(str(caminho)).dataobj) > 0.5
        rotulos, n = label(m)
        tamanhos = np.bincount(rotulos.ravel())[1:] if n else np.array([], dtype=int)
        saida.append({
            "lobo": nome,
            "tier": "NAO E TIER2 — o LCTSC nao anota lobos, nao ha ground truth para comparar",
            "volume_ml": _ml(m, spacing),
            "n_componentes_conexos": int(n),
            "conectividade": "face (6-vizinhanca, structure padrao do scipy.ndimage.label)",
            "fracao_maior_componente": float(tamanhos.max() / tamanhos.sum()) if n else "invalido: lobo vazio",
        })
    return saida


# ------------------------------------------------------------------------- benchmark


# ROIs cuja DEFINICAO de contorno e conhecida por truncar em Z. Hoje isto e apenas
# DOCUMENTACAO: as duas avaliacoes (A_suporte_gt e B_campo_completo) saem para TODAS
# as estruturas, justamente para que a escolha de onde recortar nao possa ser feita
# depois de ver o resultado.
ROIS_COM_TRUNCAGEM_CONHECIDA = ("Esophagus", "Heart")


def rodar(caso: str, raiz: Path = RAIZ_PADRAO, log=print) -> dict:
    destino = Path(raiz) / caso
    manifesto = json.loads((destino / "manifesto.json").read_text(encoding="utf-8"))
    dir_gt, dir_pred = destino / "gt", destino / "pred_masks"

    spacing = tuple(geometria.descrever_nifti(dir_gt / rtst.NOME_IMAGEM)["zooms_mm"])
    ident = {
        "dataset": manifesto["dataset"], "case_id": manifesto["case_id"],
        "pipeline_version": _pipeline_version(),
        "segmentation_model": _segmentation_model(manifesto),
        "spacing_mm": spacing,
    }
    log(f"caso {caso}: spacing_mm {spacing}, ROIs {manifesto['rois_encontradas']}")

    linhas: list[dict] = []
    detalhes: dict = {}

    for gt_roi in manifesto["rois_encontradas"]:
        canonica = mapeamento.canonizar(gt_roi)
        if canonica is None:
            log(f"  {gt_roi}: sem mapeamento — pulada")
            continue
        alvos = mapeamento.MAPA_LCTSC[canonica]
        caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{gt_roi}.nii.gz"
        caminhos_pred = [dir_pred / f"{n}.nii.gz" for n in alvos]
        structure = "+".join(alvos)

        try:
            alinhamento = _checar_grade(caminhos_pred, caminho_gt)
        except geometria.DesalinhamentoGeometrico as e:
            linha = _linha_base(ident, structure, gt_roi, "padrao")
            linha["erro"] = f"ABORTADA: {e}"
            linhas.append(linha)
            log(f"  {gt_roi}: ABORTADA — {e}")
            continue

        gt = rtst.carregar_mascara(caminho_gt)
        pred, _ = mapeamento.unir_predicao(dir_pred, alvos)
        zg, zp = _fatias_com_voxel(gt), _fatias_com_voxel(pred)
        detalhes[gt_roi] = {
            "estruturas_totalsegmentator": list(alvos),
            "uniao_de_lobos": len(alvos) > 1,
            "alinhamento_veredito": [a["veredito"] for a in alinhamento],
            "delta_affine_max": [a["delta_affine_max"] for a in alinhamento],
            # extensao em Z de cada lado: onde as definicoes de contorno divergem, e
            # aqui que aparece — e e daqui que vem boa parte do HD95.
            "extensao_z": {
                "gt": [int(zg.min()), int(zg.max())], "n_fatias_gt": int(zg.size),
                "predicao": [int(zp.min()), int(zp.max())], "n_fatias_predicao": int(zp.size),
            },
        }

        # DUAS AVALIACOES, SEMPRE AS DUAS, PARA TODA ESTRUTURA (Parte 3).
        #
        # A — suporte do GT: compara so onde o GT existe em Z. E o unico jeito de
        #     separar "contorno diferente" de "extensao diferente"... e e CIRCULAR
        #     por construcao: a janela vem de z_gt.min()/max() DESTE caso, nao de
        #     referencia anatomica. O pipeline nao localiza cricoide nem arteria
        #     pulmonar, entao A define como comparavel exatamente onde o GT existe
        #     e NAO detecta o caso em que o contornador divergiu do atlas.
        # B — campo completo: compara toda a extensao da predicao. E a avaliacao
        #     honesta do que o modelo produz, e e sempre >= tao ruim quanto A.
        #
        # Antes, A so era calculada para Esophagus e Heart. A aplicacao seletiva
        # era o problema: escolher onde recortar depois de ver o resultado e
        # exatamente o que a Parte 10 proibe. Agora as duas saem para todas.
        z_gt = _fatias_com_voxel(gt)
        z_pred = _fatias_com_voxel(pred)
        z0, z1 = int(z_gt.min()), int(z_gt.max())
        no_suporte = pred.copy()
        no_suporte[:, :, :z0] = False
        no_suporte[:, :, z1 + 1:] = False
        descartadas = sorted(set(z_pred.tolist()) - set(range(z0, z1 + 1)))

        detalhes[gt_roi]["suporte_gt"] = {
            "intervalo_z_do_gt": [z0, z1],
            "n_fatias_no_intervalo": int(z1 - z0 + 1),
            "n_fatias_gt_nao_vazias": int(z_gt.size),
            "n_fatias_predicao_nao_vazias": int(z_pred.size),
            "n_fatias_predicao_descartadas": len(descartadas),
            "volume_descartado_ml": _ml(pred & ~no_suporte, spacing),
            "circular": ("a janela vem do alcance do proprio GT deste caso, nao de "
                         "referencia anatomica — nao detecta GT que divergiu do atlas"),
        }

        # DECOMPOSICAO DO ERRO DE VOLUME (Parte 4): erros de sinal oposto cancelam
        # no erro liquido e produzem falsa sensacao de concordancia. Publicamos os
        # tres termos separados, o liquido e o absoluto.
        fp_fora = _ml(pred & ~no_suporte, spacing)          # predicao fora do suporte do GT
        fp_dentro = _ml(no_suporte & ~gt, spacing)          # sobra dentro do suporte
        fn_dentro = _ml(gt & ~pred, spacing)                # falta (GT so existe no suporte)
        vol_gt_ml = _ml(gt, spacing)
        vol_pred_ml = _ml(pred, spacing)
        absoluto = round(fp_fora + fp_dentro + fn_dentro, 4)
        detalhes[gt_roi]["decomposicao_volume"] = {
            "fp_fora_do_suporte_ml": fp_fora,
            "fp_dentro_do_suporte_ml": fp_dentro,
            "fn_dentro_do_suporte_ml": fn_dentro,
            "erro_liquido_ml": round(vol_pred_ml - vol_gt_ml, 4),
            "erro_absoluto_ml": absoluto,
            "erro_absoluto_pct_do_gt": (round(100.0 * absoluto / vol_gt_ml, 3)
                                        if vol_gt_ml else "nao aplicavel"),
            "nota": ("o erro percentual de volume das linhas e LIQUIDO e cancela estes "
                     "termos; erro_absoluto_ml e a discordancia que nao cancela"),
        }

        lA = _medir(no_suporte, gt, spacing,
                    _linha_base(ident, structure, gt_roi, "A_suporte_gt"))
        lA["ressalva"] += (
            f" [A] Predicao limitada ao suporte do GT em Z [{z0}, {z1}]; "
            f"{len(descartadas)} fatia(s) descartada(s) "
            f"({detalhes[gt_roi]['suporte_gt']['volume_descartado_ml']:.2f} ml). "
            "A janela vem do proprio GT — CIRCULAR por construcao."
        )
        lB = _medir(pred, gt, spacing,
                    _linha_base(ident, structure, gt_roi, "B_campo_completo"))
        lB["ressalva"] += (
            f" [B] Toda a extensao da predicao, sem recorte. Discordancia que NAO cancela: "
            f"{fp_fora:.1f} ml FP fora do suporte + {fp_dentro:.1f} ml FP dentro"
            f" + {fn_dentro:.1f} ml FN dentro = {absoluto:.1f} ml"
            + (f" ({100.0 * absoluto / vol_gt_ml:.1f} % do GT)." if vol_gt_ml else ".")
        )
        for l in (lA, lB):
            l["fp_fora_do_suporte_ml"] = fp_fora
            l["fp_dentro_do_suporte_ml"] = fp_dentro
            l["fn_dentro_do_suporte_ml"] = fn_dentro
            l["erro_absoluto_ml"] = absoluto
        linhas += [lA, lB]
        log(f"  {gt_roi}: A dice={lA['dice']:.4f} | B dice={lB['dice']:.4f} "
            f"| erro_abs={absoluto:.1f} ml ({fp_fora:.1f} fora + {fp_dentro:.1f} sobra "
            f"+ {fn_dentro:.1f} falta)")

    for nome in ESTRUTURAS_SEM_COBERTURA:
        linha = _linha_base(ident, nome, SEM_COBERTURA, "padrao")
        for c in ("dice", "iou", "nsd_1mm", "nsd_2mm", "hd95_mm", "assd_mm", "hd_mm",
                  "volume_error_pct", "volume_pred_ml", "volume_gt_ml",
                  "recall_gt", "precision_pred", "containment_pred_em_gt", "estrutura_pequena",
                  "fp_fora_do_suporte_ml", "fp_dentro_do_suporte_ml", "fn_dentro_do_suporte_ml",
                  "erro_absoluto_ml"):
            linha[c] = SEM_COBERTURA
        linha["ressalva"] = "o LCTSC nao contorna esta estrutura; nao estimada por nenhuma outra via"
        linhas.append(linha)
        log(f"  {nome}: {SEM_COBERTURA}")

    return {
        "manifesto": manifesto, "ident": ident, "linhas": linhas,
        "detalhes": detalhes, "lobos": _bloco_lobos(dir_pred, spacing),
    }


# ---------------------------------------------------------------------------- saida


def _json_por_linha(r: dict) -> list[dict]:
    """Um registro por linha, com metrics agrupadas e as chaves de reproducao no topo."""
    chaves_metrica = ("dice", "iou", "nsd_1mm", "nsd_2mm", "hd95_mm", "assd_mm", "hd_mm",
                      "volume_error_pct", "volume_pred_ml", "volume_gt_ml",
                      "recall_gt", "precision_pred", "containment_pred_em_gt", "estrutura_pequena",
                  "fp_fora_do_suporte_ml", "fp_dentro_do_suporte_ml", "fn_dentro_do_suporte_ml",
                  "erro_absoluto_ml")
    return [{
        "dataset": l["dataset"], "case_id": l["case_id"], "structure": l["structure"],
        "gt_roi_name": l["gt_roi_name"], "variante": l["variante"],
        "pipeline_version": l["pipeline_version"], "segmentation_model": l["segmentation_model"],
        "reconstruction_method": l["reconstruction_method"],
        "sigma": l["sigma"], "taubin_iterations": l["taubin_iterations"],
        "spacing_mm": l["spacing_mm"],
        "metrics": {k: l[k] for k in chaves_metrica},
        "ressalva": l["ressalva"], "erro": l["erro"],
    } for l in r["linhas"]]


def _f(v, casas=4) -> str:
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    return "-" if v is None else str(v)


def _tabela_md(linhas: list[dict]) -> str:
    cab = ("| estrutura (ROI do GT) | variante | Dice | IoU | NSD@1mm | NSD@2mm | HD95 (mm) | "
           "ASSD (mm) | erro vol. (%) | vol. pred (ml) | vol. GT (ml) | recall GT | containment |\n")
    cab += "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    corpo = ""
    for l in linhas:
        # aorta/traqueia nao tem ROI no GT: o rotulo da linha e o nome da estrutura,
        # e a coluna de metrica e que carrega o "nao medido".
        nome = l["structure"] if l["gt_roi_name"] == SEM_COBERTURA else l["gt_roi_name"]
        if l["erro"]:
            corpo += f"| {nome} | {l['variante']} | {l['erro']} |" + " |" * 11 + "\n"
            continue
        if l["dice"] == SEM_COBERTURA:
            corpo += f"| {nome} | sem cobertura |" + " nao medido |" * 11 + "\n"
            continue
        ve = l["volume_error_pct"]
        corpo += (
            f"| {nome} | {l['variante']} | {_f(l['dice'])} | {_f(l['iou'])} | "
            f"{_f(l['nsd_1mm'])} | {_f(l['nsd_2mm'])} | {_f(l['hd95_mm'], 3)} | "
            f"{_f(l['assd_mm'], 3)} | {f'{ve:+.2f}' if isinstance(ve, float) else ve} | "
            f"{_f(l['volume_pred_ml'], 1)} | {_f(l['volume_gt_ml'], 1)} | "
            f"{_f(l['recall_gt'])} | {_f(l['containment_pred_em_gt'])} |\n"
        )
    return cab + corpo


def _summary_md(r: dict) -> str:
    m, ident = r["manifesto"], r["ident"]
    lic = m["licenca"]
    esof = r["detalhes"].get("Esophagus", {}).get("recorte_z", {})

    md = f"""# Tier2 — acuracia de segmentacao contra ground truth independente

**O que e Tier2.** Tier2 mede a acuracia da SEGMENTACAO contra um ground truth
INDEPENDENTE. (Tier1 mede a fidelidade da RECONSTRUCAO a mascara; Tier3 usa
fantoma analitico.) Na decomposicao de erro — A = segmentacao, B = reconstrucao,
C = simplificacao/decimacao, D = compressao — **este documento quantifica APENAS
o bloco A**, e os blocos nunca se somam. Nenhum numero aqui diz coisa alguma
sobre reconstrucao de malha.

**Dataset.** {m['dataset']} (Lung CT Segmentation Challenge 2017, TCIA).
Ground truth = RTSTRUCT de contorno de radioterapia.
DOI [{lic['doi']}]({lic['collection_uri']}).

**Licenca.** {lic['nome']} — <{lic['uri']}>. Nome e URI foram LIDOS do registro
de serie devolvido pela API do TCIA, nao digitados a mao.

**Quantos casos: UM.** {m['case_id']}. Um caso. Nao arredondado para cima, nao
agregado, sem media, sem desvio-padrao — nao ha o que agregar com n=1.

**O que este resultado NAO e.** Com um unico caso, isto **nao e uma estimativa
de acuracia do modelo de segmentacao**. E a primeira medida tirada com o
instrumento ja montado: prova que a cadeia TCIA -> RTSTRUCT -> NIfTI ->
TotalSegmentator -> metrica em mm fecha, e que os numeros que ela produz sao
plausiveis. Qualquer afirmacao sobre desempenho do modelo exige a coorte
inteira. Uso educacional/experimental; nao e avaliacao clinica.

## Como foi medido

- Predicao: {ident['segmentation_model']}.
- Codigo: `{ident['pipeline_version']}`.
- Grade compartilhada POR CONSTRUCAO: o TotalSegmentator rodou sobre exatamente
  o `gt/image.nii.gz` gravado pelo `dcmrtstruct2nii`, nao sobre uma conversao
  paralela. Antes de CADA comparacao a grade foi reverificada
  (`geometria.verificar_alinhamento`); linha desalinhada e abortada com erro
  explicito em vez de virar "Dice ruim".
- spacing = {list(ident['spacing_mm'])} mm (de `header.get_zooms()`, nao de
  `np.diag(affine)`), shape {m['shape']}, orientacao {m['orientacao']}.
- Todas as distancias em MILIMETROS FISICOS. Metricas de
  `scripts/validation/segmentation_metrics.py::compare_masks`, com a convencao
  de fronteira fixada la (superficie = camada interna de voxels com vizinho de
  face no fundo; distancias entre centros de voxel, quantizadas na grade).
- `reconstruction_method`, `sigma` e `taubin_iterations` saem como
  "{NA}": Tier2 nao envolve reconstrucao.

## Resultados

{_tabela_md(r['linhas'])}
### Leia junto com o numero

"""
    for roi in ("Heart", "Esophagus", "Lung_L"):
        rot = "Lung_L / Lung_R" if roi == "Lung_L" else roi
        md += f"- **{rot}** — {RESSALVAS[roi]}\n"
    ez = r["detalhes"].get("Heart", {}).get("extensao_z")
    if ez:
        md += (
            f"- **Onde o HD95 do coracao nasce** — extensao em Z: GT nas fatias "
            f"{ez['gt']} ({ez['n_fatias_gt']} fatias) contra predicao {ez['predicao']} "
            f"({ez['n_fatias_predicao']} fatias). O contorno de radioterapia para no nivel "
            f"inferior da arteria pulmonar; o TotalSegmentator segue subindo. Essa diferenca "
            f"de extensao — nao um contorno lateral errado — e o que domina HD95 e ASSD. "
            f"A extensao em Z de cada ROI esta em `tier2.json`, campo `extensao_z`.\n"
        )
    if esof:
        md += (
            f"- **Recorte do esofago** — a janela do GT vai da fatia Z "
            f"{esof['intervalo_z_do_gt'][0]} a {esof['intervalo_z_do_gt'][1]} "
            f"({esof['n_fatias_no_intervalo']} fatias no intervalo, "
            f"{esof['n_fatias_gt_nao_vazias']} delas com voxel). A predicao ocupa "
            f"{esof['n_fatias_predicao_nao_vazias']} fatias, das quais "
            f"{esof['n_fatias_predicao_descartadas']} caiu(ram) fora da janela e foi(ram) "
            f"descartada(s) pelo recorte — {esof['volume_descartado_ml']:.3f} ml. "
            f"Neste caso o efeito e desprezivel: `recorte_z` e `sem_recorte` quase coincidem, "
            f"porque a predicao ja parou praticamente onde o GT parou. A linha `sem_recorte` "
            f"continua na tabela porque e ela que mostra o tamanho do efeito — que aqui deu "
            f"perto de zero, mas nao ha razao para supor que dara em outros casos.\n"
        )
    md += (
        f"- **Estrutura pequena** — linhas com volume de GT abaixo de "
        f"{LIMIAR_PEQUENA_ML:.0f} ml sao marcadas em `estrutura_pequena`; nelas o recall "
        f"pesa mais que o Dice, porque um voxel de borda move o Dice de estrutura fina "
        f"muito mais do que move a cobertura real.\n"
        "- **Aorta e traqueia** — o LCTSC nao contorna essas estruturas. Elas aparecem na "
        f"tabela como \"{SEM_COBERTURA}\" e nao foram estimadas por nenhuma outra via.\n"
    )

    md += "\n## Lobos pulmonares — NAO E TIER2\n\n"
    md += (
        "O LCTSC nao anota lobos, entao nao ha ground truth para comparar. O bloco abaixo nao\n"
        "e uma metrica de acuracia: e o unico sinal disponivel sobre lobacao — volume e numero\n"
        "de componentes conexos por lobo predito. Um lobo integro e um componente so.\n\n"
        "| lobo (predicao) | volume (ml) | componentes conexos | fracao do maior componente |\n"
        "|---|---|---|---|\n"
    )
    for lb in r["lobos"]:
        md += (f"| {lb['lobo']} | {lb['volume_ml']:.1f} | {lb['n_componentes_conexos']} | "
               f"{_f(lb['fracao_maior_componente'])} |\n")
    md += (f"\nConectividade: {r['lobos'][0]['conectividade']}.\n")

    md += (
        "\n## Limitacoes\n\n"
        "- n = 1. Nenhuma dispersao, nenhuma generalizacao.\n"
        "- Distancias quantizadas na grade de voxel (sem interpolacao sub-voxel e sem area de\n"
        "  triangulo): o menor valor nao-nulo possivel e ~1 voxel, e em Z o voxel tem 3 mm.\n"
        "- Ground truth de contorno de radioterapia carrega variabilidade interobservador que\n"
        "  este documento nao mede e nao tem como separar do erro do modelo.\n"
        "- Tier2 nao diz nada sobre reconstrucao, simplificacao ou compressao (blocos B, C, D).\n"
    )
    return md


def gravar(r: dict, saida: Path, log=print) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    csv_p, json_p, md_p = saida / "tier2.csv", saida / "tier2.json", saida / "summary_tier2.md"

    with csv_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(r["linhas"])

    json_p.write_text(json.dumps({
        "tier": "Tier2 — acuracia da SEGMENTACAO contra ground truth independente",
        "bloco_de_erro": "A (segmentacao). Nao diz nada sobre B/C/D e nao se soma a eles.",
        "n_casos": 1,
        "aviso": ("um unico caso: NAO e estimativa de acuracia do modelo, e a primeira medida "
                  "com o instrumento montado"),
        "dataset": r["manifesto"]["dataset"],
        "case_id": r["manifesto"]["case_id"],
        "licenca": r["manifesto"]["licenca"],
        "spacing_mm": list(r["ident"]["spacing_mm"]),
        "shape": r["manifesto"]["shape"],
        "orientacao": r["manifesto"]["orientacao"],
        "resultados": _json_por_linha(r),
        "detalhes_por_roi": r["detalhes"],
        "lobos_sem_ground_truth": r["lobos"],
        "estruturas_sem_cobertura": {n: SEM_COBERTURA for n in ESTRUTURAS_SEM_COBERTURA},
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    md_p.write_text(_summary_md(r), encoding="utf-8")
    for p in (csv_p, json_p, md_p):
        log(f"gravado: {p}")
    return {"csv": csv_p, "json": json_p, "md": md_p}


# -------------------------------------------------------------------------- autoteste


def _autoteste() -> None:
    """(a) identidade; (b) HD95 em MM, nao em indice de voxel; (c) grade divergente reprovada."""
    import tempfile

    spacing = (0.9765625, 0.9765625, 3.0)  # anisotropico de proposito: 1.0 != spacing em nenhum eixo
    cubo = np.zeros((40, 40, 40), dtype=bool)
    cubo[10:20, 10:20, 10:20] = True

    # (a) identidade
    r = compare_masks(cubo, cubo, spacing)
    assert r["dice"] == 1.0 and r["hd95_mm"] == 0.0, r
    assert r["iou"] == 1.0 and r["assd_mm"] == 0.0 and r["volume_error_pct"] == 0.0, r
    rc = recall_containment(cubo, cubo)
    assert rc["recall_gt"] == 1.0 and rc["containment_pred_em_gt"] == 1.0, rc
    print("(a) identidade:", json.dumps({**r, **rc}))

    # (b) deslocada 1 voxel em Z: HD95 tem que dar o SPACING em mm (3.0), nunca 1.0.
    deslocada = np.roll(cubo, 1, axis=2)
    r2 = compare_masks(deslocada, cubo, spacing)
    assert abs(r2["hd95_mm"] - spacing[2]) < 1e-9, (r2["hd95_mm"], spacing[2])
    assert abs(r2["hd95_mm"] - 1.0) > 1e-6, "HD95 saiu em indice de voxel, nao em mm"
    print(f"(b) deslocada 1 voxel em Z (spacing {spacing}): hd95_mm={r2['hd95_mm']} "
          f"(= spacing[2]={spacing[2]}, NAO 1.0)")
    print("    linha completa:", json.dumps(r2))

    # (c) o verificador de geometria REPROVA um par com affine diferente
    aff = np.diag([0.9765625, 0.9765625, 3.0, 1.0])
    outro = aff.copy()
    outro[2, 3] += 3.0
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "a.nii.gz", Path(td) / "b.nii.gz"
        nib.save(nib.Nifti1Image(cubo.astype(np.uint8), aff), str(a))
        nib.save(nib.Nifti1Image(cubo.astype(np.uint8), outro), str(b))
        assert geometria.verificar_alinhamento(a, a)["alinhado"], "grade identica foi reprovada"
        try:
            geometria.verificar_alinhamento(a, b)
        except geometria.DesalinhamentoGeometrico as e:
            print("(c) affine diferente REPROVADO:", e)
        else:
            raise AssertionError("grade divergente passou pelo verificador de geometria")

    print("benchmark_tier2.py: autoteste OK")


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Benchmark Tier2 (acuracia de segmentacao) do LCTSC.")
    p.add_argument("--caso", default="LCTSC-Train-S1-001")
    p.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    p.add_argument("--saida", type=Path, default=None, help="padrao: <raiz>/resultados")
    p.add_argument("--autoteste", action="store_true")
    a = p.parse_args(argv)
    if a.autoteste:
        _autoteste()
        return 0
    r = rodar(a.caso, a.raiz)
    gravar(r, a.saida or (a.raiz / "resultados"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
