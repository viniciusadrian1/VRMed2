"""Fase 32 — o que o planner produziu para o V2, e o que isso custa.

O QUE ESTE MODULO NAO FAZ

Nao treina, nao infere, nao escolhe hiperparametro, nao edita plano. O plano vem do
`nnUNetv2_plan_experiment`, ja executado; aqui ele e LIDO, comparado com o da Fase 26B e
convertido em custo. Editar o plano a mao para caber na placa seria trocar a pergunta
"cabe?" pela pergunta "o que eu fiz caber?".

OS FOLDS

O nnU-Net gera `splits_final.json` na PRIMEIRA vez que se treina. Isso significa que, sem
uma fase de planejamento, os folds so seriam conhecidos depois de comecar. Este modulo
chama a MESMA funcao do framework — `generate_crossval_split(sorted(ids), seed=12345,
n_splits=5)`, o codigo que o `nnUNetTrainer.do_split` chama — e congela o arquivo antes.
Nao ha reimplementacao: se o framework mudar de algoritmo, isto muda junto.

O CUSTO, E POR QUE NAO E 3,2x

Uma epoca do nnU-Net e `num_iterations_per_epoch` iteracoes de `batch_size` patches.
As duas sao CONSTANTES do trainer (250 e o plano), e nao dependem de quantos casos
existem. Trinta e dois casos nao custam 3,2x dez casos: custam o mesmo por epoca, com o
mesmo numero de patches vistos. O que MUDA o custo por epoca e o patch e a arquitetura —
e por isso o custo aqui e derivado do plano real, e ancorado no tempo MEDIDO na Fase 26B.

  python -m scripts.validation.fase32.planejar --autoteste
  python -m scripts.validation.fase32.planejar --gravar docs/overnight/phase32/plano.json
  python -m scripts.validation.fase32.planejar --escrever-folds
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
CONFIG = "3d_fullres"

F26B = RAIZ / ".clinica-dados" / "fase26b"
F32 = RAIZ / ".clinica-dados" / "fase32"
PRE_26B = F26B / "nnUNet_preprocessed" / "Dataset501_VRmedEsofago"
PRE_V2 = F32 / "nnUNet_preprocessed" / "Dataset502_VRmedEsofagoV2"
RES_26B = (F26B / "nnUNet_results" / "Dataset501_VRmedEsofago"
           / "nnUNetTrainer_250epochs__nnUNetPlans__3d_fullres")
MANIFESTO_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl"

# Constantes do trainer, conferidas de primeira mao no 2.8.1 instalado. Nao sao
# escolha desta fase: sao o que o codigo faz.
ITERACOES_POR_EPOCA = 250
ITERACOES_VALIDACAO = 50
N_FOLDS = 5
SEED_SPLIT = 12345           # nnUNetTrainer.do_split -> generate_crossval_split

# Campos do plano que a Fase 32 compara. A lista e explicita: um campo novo no plano
# que nao esteja aqui aparece como "campo so em um dos planos", nao some.
CAMPOS = ("data_identifier", "preprocessor_name", "batch_size", "patch_size",
          "median_image_size_in_voxels", "spacing", "normalization_schemes",
          "use_mask_for_norm", "batch_dice")
CAMPOS_ARQ = ("n_stages", "features_per_stage", "conv_op", "kernel_sizes", "strides",
              "n_conv_per_stage", "n_conv_per_stage_decoder", "norm_op", "nonlin")


def ler_plano(pasta: Path) -> dict:
    return json.loads((pasta / "nnUNetPlans.json").read_text(encoding="utf-8"))


def config_do_plano(p: dict) -> dict:
    return p["configurations"][CONFIG]


def comparar_planos() -> list:
    """CAMPO | 26B | V2 | MUDOU? — sem interpretacao; a consequencia fica no relatorio."""
    a, b = ler_plano(PRE_26B), ler_plano(PRE_V2)
    ca, cb = config_do_plano(a), config_do_plano(b)
    linhas = []

    def add(campo, va, vb):
        linhas.append({"campo": campo, "f26b": va, "v2": vb, "mudou": va != vb})

    add("dataset_name", a["dataset_name"], b["dataset_name"])
    add("experiment_planner", a["experiment_planner_used"], b["experiment_planner_used"])
    add("mediana_spacing_original", a["original_median_spacing_after_transp"],
        b["original_median_spacing_after_transp"])
    add("mediana_shape_original", a["original_median_shape_after_transp"],
        b["original_median_shape_after_transp"])
    for k in CAMPOS:
        add(k, ca.get(k), cb.get(k))
    aa = ca["architecture"]["arch_kwargs"]
    ab = cb["architecture"]["arch_kwargs"]
    add("network_class", ca["architecture"]["network_class_name"],
        cb["architecture"]["network_class_name"])
    for k in CAMPOS_ARQ:
        add("arch." + k, aa.get(k), ab.get(k))
    # campos que existem num plano e nao no outro nao podem sumir da comparacao
    so_a = sorted(set(ca) - set(cb) - set(CAMPOS))
    so_b = sorted(set(cb) - set(ca) - set(CAMPOS))
    if so_a or so_b:
        add("campos_exclusivos", so_a, so_b)
    return linhas


def custo_por_patch() -> dict:
    """MACs e tamanho de mapa de ativacao por patch, para os dois planos.

    Nao e estimativa de VRAM em GB: e a MESMA grandeza que o planner usa como
    orcamento (`compute_conv_feature_map_size`) mais uma contagem de multiplicacoes
    obtida percorrendo a rede real em `meta` device (nenhum tensor e alocado, nenhum
    calculo e feito — so as formas sao propagadas).
    """
    import numpy as np
    import torch
    from nnunetv2.utilities.get_network_from_plans import get_network_from_plans
    from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

    out = {}
    for rot, pre, raw in (("f26b", PRE_26B, F26B / "nnUNet_raw" / "Dataset501_VRmedEsofago"),
                          ("v2", PRE_V2, F32 / "nnUNet_raw" / "Dataset502_VRmedEsofagoV2")):
        pm = PlansManager(pre / "nnUNetPlans.json")
        cfg = pm.get_configuration(CONFIG)
        lm = pm.get_label_manager(json.loads((raw / "dataset.json").read_text(encoding="utf-8")))
        rede = get_network_from_plans(cfg.network_arch_class_name,
                                      cfg.network_arch_init_kwargs,
                                      cfg.network_arch_init_kwargs_req_import,
                                      1, lm.num_segmentation_heads,
                                      allow_init=False, deep_supervision=True)
        macs = [0]

        def gancho(m, i, o):
            if isinstance(m, (torch.nn.Conv3d, torch.nn.ConvTranspose3d)):
                s = (o[0] if isinstance(o, (list, tuple)) else o).shape[2:]
                macs[0] += (int(np.prod(s)) * m.out_channels
                            * (m.in_channels // m.groups) * int(np.prod(m.kernel_size)))

        ganchos = [m.register_forward_hook(gancho) for m in rede.modules()]
        with torch.no_grad():
            rede.to("meta")(torch.empty(1, 1, *cfg.patch_size, device="meta"))
        for g in ganchos:
            g.remove()
        out[rot] = {
            "patch_size": list(int(x) for x in cfg.patch_size),
            "voxels_por_patch": int(np.prod(cfg.patch_size)),
            "batch_size": int(cfg.batch_size),
            "parametros": int(sum(p.numel() for p in rede.parameters())),
            "mapa_ativacao": float(rede.compute_conv_feature_map_size(cfg.patch_size)),
            "macs_por_patch": int(macs[0]),
        }
    a, b = out["f26b"], out["v2"]
    out["identico_por_iteracao"] = bool(
        a["macs_por_patch"] == b["macs_por_patch"]
        and a["mapa_ativacao"] == b["mapa_ativacao"]
        and a["parametros"] == b["parametros"]
        and a["batch_size"] == b["batch_size"])
    out["razao_macs_v2_sobre_26b"] = round(b["macs_por_patch"] / a["macs_por_patch"], 6)
    return out


def tempo_medido_26b() -> dict:
    """Tempo por epoca REALMENTE medido nos 5 folds da Fase 26B, lido dos logs."""
    por_fold = {}
    for f in range(N_FOLDS):
        logs = sorted((RES_26B / ("fold_%d" % f)).glob("training_log_*.txt"))
        if not logs:
            continue
        txt = logs[-1].read_text(encoding="utf-8", errors="replace")
        ep = [float(m) for m in re.findall(r"Epoch time: ([0-9.]+) s", txt)]
        carimbos = re.findall(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", txt, re.M)
        parede = None
        if len(carimbos) >= 2:
            from datetime import datetime
            fmt = "%Y-%m-%d %H:%M:%S"
            parede = (datetime.strptime(carimbos[-1], fmt)
                      - datetime.strptime(carimbos[0], fmt)).total_seconds()
        por_fold["fold_%d" % f] = {
            "n_epocas": len(ep),
            "media_s": round(statistics.fmean(ep), 2) if ep else None,
            "soma_h": round(sum(ep) / 3600, 3) if ep else None,
            "parede_h": round(parede / 3600, 3) if parede else None,
            "fora_das_epocas_s": round(parede - sum(ep), 1) if parede and ep else None,
        }
    medias = [v["media_s"] for v in por_fold.values() if v["media_s"]]
    return {
        "por_fold": por_fold,
        "media_s_por_epoca": round(statistics.fmean(medias), 2) if medias else None,
        "min_s": round(min(medias), 2) if medias else None,
        "max_s": round(max(medias), 2) if medias else None,
        "soma_h_5_folds": round(sum(v["soma_h"] for v in por_fold.values()), 2),
    }


def custo(epocas: int, seg_por_epoca: float, razao: float = 1.0) -> dict:
    s = seg_por_epoca * razao
    por_fold_h = s * epocas / 3600
    return {
        "epocas": epocas,
        "s_por_epoca_estimado": round(s, 2),
        "h_por_fold": round(por_fold_h, 2),
        "h_5_folds": round(por_fold_h * N_FOLDS, 2),
        "dias_5_folds": round(por_fold_h * N_FOLDS / 24, 2),
        "patches_vistos_por_fold": epocas * ITERACOES_POR_EPOCA * 2,
    }


def gerar_folds(escrever: bool = False) -> dict:
    """Chama a funcao do proprio nnU-Net sobre os identificadores ja preprocessados."""
    from nnunetv2.utilities.crossval_split import generate_crossval_split
    import numpy as np

    ids = sorted(p.name[:-len(".b2nd")]
                 for p in (PRE_V2 / ("nnUNetPlans_" + CONFIG)).glob("*.b2nd")
                 if not p.name.endswith("_seg.b2nd"))
    ordenados = list(np.sort(ids))
    splits = generate_crossval_split(ordenados, seed=SEED_SPLIT, n_splits=N_FOLDS)
    splits = [{"train": [str(x) for x in s["train"]], "val": [str(x) for x in s["val"]]}
              for s in splits]
    destino = PRE_V2 / "splits_final.json"
    if escrever:
        destino.write_text(json.dumps(splits, indent=4, ensure_ascii=False), encoding="utf-8")
    return {"n_identificadores": len(ordenados), "splits": splits,
            "arquivo": str(destino), "escrito": escrever, "ja_existia": destino.exists()}


def auditar_folds(splits: list) -> dict:
    """32K — cada fold e legivel, disjunto, e cobre os 32 exatamente uma vez como val."""
    ent = {e["case_id"]: e for e in man.carregar(MANIFESTO_V2)}
    treino = sorted(k for k, v in ent.items() if v["split"] == "train")
    linhas, problemas = [], []
    vistos_val = Counter()

    for i, s in enumerate(splits):
        tr, va = list(s["train"]), list(s["val"])
        vistos_val.update(va)
        desconhecidos = [c for c in tr + va if c not in ent]
        if desconhecidos:
            problemas.append("fold %d cita caso fora do manifesto: %s" % (i, desconhecidos))
        fora_do_train = [c for c in tr + va if c in ent and ent[c]["split"] != "train"]
        if fora_do_train:
            problemas.append("fold %d usa caso que NAO e da particao train: %s"
                             % (i, fora_do_train))
        if set(tr) & set(va):
            problemas.append("fold %d tem caso nos dois lados: %s" % (i, sorted(set(tr) & set(va))))
        if sorted(tr + va) != treino:
            problemas.append("fold %d nao cobre exatamente os %d de train" % (i, len(treino)))
        # sujeito nos dois lados — a checagem que case_id sozinho nao faz
        suj = lambda c: (ent[c]["source_dataset"], ent[c]["source_case_id"])  # noqa: E731
        st, sv = set(map(suj, tr)), set(map(suj, va))
        if st & sv:
            problemas.append("fold %d tem o mesmo SUJEITO nos dois lados: %s" % (i, st & sv))
        linhas.append({
            "fold": i,
            "n_train": len(tr), "n_val": len(va),
            "fontes_train": dict(Counter(ent[c]["source_dataset"] for c in tr)),
            "fontes_val": dict(Counter(ent[c]["source_dataset"] for c in va)),
            "institution_val": dict(Counter(ent[c]["institution"] for c in va)),
            "spacing_z_val": dict(Counter(round(float(ent[c]["spacing"][2]), 4) for c in va)),
            "val": sorted(va),
        })

    faltando = [c for c in treino if vistos_val[c] != 1]
    if faltando:
        problemas.append("casos que nao aparecem exatamente uma vez como val: %s" % faltando)

    duas_fontes = [l["fold"] for l in linhas if len(l["fontes_val"]) < 2]
    return {
        "linhas": linhas,
        "problemas": problemas,
        "todos_os_folds_com_duas_fontes_na_val": not duas_fontes,
        "folds_com_uma_fonte_so_na_val": duas_fontes,
        "n_casos_cobertos": len(vistos_val),
        "ok": not problemas,
    }


def decomposicao_dispersao() -> dict:
    """32O — o dp de 0,0898 entre folds do 26B mede fold ou mede caso?

    A Fase 30 usou `dp entre folds = 0,0898` como sinal de que o treino era instavel.
    Cada fold, porem, foi medido em DOIS casos. A dispersao de uma media de dois casos
    ja e grande so por amostragem, e as duas coisas nunca foram separadas.

    Aqui elas sao: analise de variancia de uma via sobre os 10 Dice out-of-fold, cinco
    grupos de dois. `F` compara a variacao ENTRE folds com a variacao DENTRO deles.
    `F < 1` significa que a estimativa do componente de variancia entre folds e nao
    positiva — nao ha efeito de fold detectavel acima do efeito de caso.

    Isto NAO diz que o treino e estavel. Diz que estes dados nao distinguem as duas
    coisas, e que comparar 0,0898 com um dp futuro medido sobre 6 ou 7 casos por fold
    compararia numeros que diferem pelo `n` antes de diferirem pelo modelo.
    """
    from scipy import stats

    grupos = []
    for f in range(N_FOLDS):
        q = RES_26B / ("fold_%d" % f) / "validation" / "summary.json"
        if not q.exists():
            return {"disponivel": False, "motivo": "summary.json do fold %d ausente" % f}
        d = json.loads(q.read_text(encoding="utf-8"))
        grupos.append([m["metrics"]["1"]["Dice"] for m in d["metric_per_case"]])
    if len(set(len(g) for g in grupos)) != 1:
        return {"disponivel": False, "motivo": "folds com numero diferente de casos"}

    todos = [x for g in grupos for x in g]
    k, n = len(grupos), len(grupos[0])
    grande = statistics.fmean(todos)
    ms_entre = (n * sum((statistics.fmean(g) - grande) ** 2 for g in grupos)) / (k - 1)
    ms_dentro = (sum((x - statistics.fmean(g)) ** 2 for g in grupos for x in g)
                 / (k * (n - 1)))
    f_stat = ms_entre / ms_dentro
    componente = (ms_entre - ms_dentro) / n
    medias = [statistics.fmean(g) for g in grupos]
    return {
        "disponivel": True,
        "n_folds": k, "casos_por_fold": n,
        "dice_por_fold": [round(x, 4) for x in medias],
        "dp_entre_folds": round(statistics.stdev(medias), 4),
        "dp_caso_a_caso_dentro": round(ms_dentro ** 0.5, 4),
        "F": round(f_stat, 3),
        "p": round(float(1 - stats.f.cdf(f_stat, k - 1, k * (n - 1))), 4),
        "componente_entre_folds": round(componente, 6),
        "efeito_de_fold_detectavel": bool(componente > 0),
        "dp_esperado_so_por_amostragem": {
            "com_2_casos": round((ms_dentro / 2) ** 0.5, 4),
            "com_6_casos": round((ms_dentro / 6) ** 0.5, 4),
            "com_7_casos": round((ms_dentro / 7) ** 0.5, 4),
        },
    }


def viabilidade(cp: dict) -> dict:
    """32J — o plano cabe no hardware que existe? Sem tocar no plano."""
    import shutil
    import torch
    import psutil

    total, _, livre = shutil.disk_usage(str(RAIZ))
    p = torch.cuda.get_device_properties(0) if torch.cuda.is_available() else None
    vm = psutil.virtual_memory()

    # o 26B rodou nesta MESMA placa com este MESMO orcamento de mapa de ativacao.
    # Nao ha estimativa de VRAM aqui: ha um precedente medido e a prova de que o
    # orcamento nao subiu.
    return {
        "gpu": p.name if p else None,
        "vram_mib": (p.total_memory // 1024 // 1024) if p else None,
        "vram_livre_mib_agora": (torch.cuda.mem_get_info()[0] // 1024 // 1024
                                 if torch.cuda.is_available() else None),
        "ram_gb": round(vm.total / 1e9, 1),
        "ram_livre_gb": round(vm.available / 1e9, 1),
        "disco_livre_gb": round(livre / 1e9, 1),
        "mapa_ativacao_igual_ao_26b": cp["identico_por_iteracao"],
        "precedente": ("o mesmo orcamento de patch, batch e arquitetura ja treinou 5 folds "
                       "nesta placa na Fase 26B"),
    }


def teto_por_reamostragem() -> dict:
    """O quanto do Dice ja se perde so por trocar de grade, antes de qualquer modelo.

    POR QUE ISTO PRECISA SER MEDIDO NESTA FASE

    No 26B o spacing-alvo era 3,0 mm em z, que e o spacing NATIVO dos 6 casos do holdout.
    A ida e a volta eram identidade e o teto de Dice era 1,0. No plano V2 o alvo caiu para
    2,5 mm: a predicao nasce numa grade que nenhum dos 6 tem e volta reamostrada. Comparar
    o Dice do 26B com o da Fase 33 nesses mesmos 6 casos sem saber esse teto seria atribuir
    ao modelo uma diferenca que pode ser da grade.

    O que e medido: mascara de referencia na grade nativa -> grade-alvo do plano (kwargs de
    `resampling_fn_seg` do proprio plano) -> volta a grade nativa pelo caminho das
    probabilidades (one-hot, kwargs de `resampling_fn_probabilities`, argmax), que e como a
    predicao de fato retorna. Nenhum modelo entra nisto.
    """
    import numpy as np
    import nibabel as nib
    from nnunetv2.preprocessing.resampling.default_resampling import (
        resample_data_or_seg_to_shape)

    sys.path.insert(0, str(RAIZ))
    from scripts.validation import segmentation_metrics as sm

    cfg = config_do_plano(ler_plano(PRE_V2))
    alvo = [float(x) for x in cfg["spacing"]]                 # (z, y, x) apos transpose
    kw_seg = dict(cfg["resampling_fn_seg_kwargs"])
    kw_prob = dict(cfg["resampling_fn_probabilities_kwargs"])

    v1 = [e for e in man.carregar(RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl")
          if e["split"] == "validation"]
    linhas = []
    for e in sorted(v1, key=lambda x: x["case_id"]):
        cam = RAIZ / e["mask_path"]
        if not cam.exists():
            return {"disponivel": False, "motivo": "mascara ausente: %s" % cam}
        im = nib.load(str(cam))
        a = (np.asanyarray(im.dataobj) > 0).astype(np.uint8)
        # o manifesto guarda spacing como (x, y, z); o nnU-Net trabalha em (z, y, x)
        sx, sy, sz = (float(v) for v in e["spacing"])
        orig = a.transpose(2, 1, 0)[None]                     # (1, z, y, x)
        esp_orig = np.array([sz, sy, sx])
        forma_alvo = [int(round(orig.shape[i + 1] * esp_orig[i] / alvo[i])) for i in range(3)]

        ida = resample_data_or_seg_to_shape(orig, forma_alvo, esp_orig, np.array(alvo), **kw_seg)
        # a volta e pelo caminho das PROBABILIDADES, que e o caminho real da predicao
        onehot = np.concatenate([(ida[0] == 0)[None], (ida[0] == 1)[None]]).astype(np.float32)
        volta = resample_data_or_seg_to_shape(onehot, list(orig.shape[1:]),
                                              np.array(alvo), esp_orig, **kw_prob)
        rec = (np.argmax(volta, axis=0) == 1).astype(np.uint8)

        linhas.append({
            "case_id": e["case_id"],
            "spacing_nativo_z": round(sz, 4),
            "forma_nativa": list(int(x) for x in orig.shape[1:]),
            "forma_no_alvo": forma_alvo,
            "dice_teto": round(sm.dice(rec, a.transpose(2, 1, 0)), 4),
            "voxels_fg_original": int(a.sum()),
            "voxels_fg_ida_e_volta": int(rec.sum()),
        })
    tetos = [l["dice_teto"] for l in linhas]
    return {
        "disponivel": True,
        "spacing_alvo": alvo,
        "linhas": linhas,
        "dice_teto_media": round(statistics.fmean(tetos), 4),
        "dice_teto_min": round(min(tetos), 4),
        "dice_teto_max": round(max(tetos), 4),
        "teto_no_26b": 1.0,
        "motivo_teto_1_no_26b": "o spacing-alvo do 26B (3,0 mm em z) e o nativo dos 6 casos",
    }


def uso_de_disco() -> dict:
    def tam(d: Path):
        return round(sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) / 1e9, 3) \
            if d.exists() else None
    return {
        "v2_raw_gb": tam(F32 / "nnUNet_raw"),
        "v2_preprocessed_gb": tam(F32 / "nnUNet_preprocessed"),
        "f26b_results_gb": tam(F26B / "nnUNet_results"),
        "f26b_preprocessed_gb": tam(F26B / "nnUNet_preprocessed"),
    }


def rodar() -> dict:
    cp = custo_por_patch()
    med = tempo_medido_26b()
    razao = cp["razao_macs_v2_sobre_26b"]
    folds = gerar_folds(escrever=False)
    aud = auditar_folds(folds["splits"])
    disco = uso_de_disco()
    # o resultado de 5 folds cabe em quanto? o checkpoint tem o mesmo numero de
    # parametros, entao o tamanho por fold e o mesmo medido no 26B.
    return {
        "fase": 32,
        "config": CONFIG,
        "plano_v2": config_do_plano(ler_plano(PRE_V2)),
        "comparacao": comparar_planos(),
        "custo_por_patch": cp,
        "tempo_medido_26b": med,
        "custo_250": custo(250, med["media_s_por_epoca"], razao),
        "custo_1000": custo(1000, med["media_s_por_epoca"], razao),
        "folds": folds["splits"],
        "auditoria_folds": aud,
        "viabilidade": viabilidade(cp),
        "decomposicao_dispersao": decomposicao_dispersao(),
        "teto_por_reamostragem": teto_por_reamostragem(),
        "disco": disco,
        "armazenamento_previsto_gb": {
            "resultados_5_folds": disco["f26b_results_gb"],
            "motivo": "mesmo numero de parametros, mesmos 2 checkpoints por fold",
        },
        "constantes_do_trainer": {
            "num_iterations_per_epoch": ITERACOES_POR_EPOCA,
            "num_val_iterations_per_epoch": ITERACOES_VALIDACAO,
            "n_folds": N_FOLDS,
            "seed_do_split": SEED_SPLIT,
            "semeia_torch_numpy_random": False,
            "cudnn_deterministic": False,
            "cudnn_benchmark": True,
        },
    }


def autoteste() -> int:
    falhas = []

    # 1. os dois planos existem e tem a configuracao que a fase compara
    for pre in (PRE_26B, PRE_V2):
        if not (pre / "nnUNetPlans.json").exists():
            falhas.append("plano ausente: %s" % pre)
    if falhas:
        print("FALHA:", falhas[0])
        print("autoteste planejar: 10 verificacoes, %d falhas" % len(falhas))
        return 1

    # 2. a comparacao inclui os campos que a fase promete mostrar
    linhas = comparar_planos()
    campos = set(l["campo"] for l in linhas)
    for k in ("patch_size", "batch_size", "spacing", "arch.n_stages", "arch.strides"):
        if k not in campos:
            falhas.append("a comparacao nao inclui %s" % k)

    # 3. CONTROLE POSITIVO da comparacao: dois valores diferentes tem de dar mudou=True,
    #    e dois iguais tem de dar False. Uma tabela que sempre diz "mudou" nao informa.
    if not any(l["mudou"] for l in linhas):
        falhas.append("a comparacao nao viu nenhuma diferenca entre planos diferentes")
    if not any(not l["mudou"] for l in linhas):
        falhas.append("a comparacao marcou tudo como mudado")

    # 4. o custo por patch e derivado da rede real, e os dois planos tem o mesmo batch
    cp = custo_por_patch()
    if cp["f26b"]["batch_size"] != cp["v2"]["batch_size"]:
        falhas.append("batch_size mudou; o modelo de custo desta fase assume o mesmo")
    if cp["v2"]["macs_por_patch"] <= 0:
        falhas.append("contagem de MACs nao percorreu a rede")

    # 5. os folds vem da funcao do framework, e ela e deterministica
    a = gerar_folds(escrever=False)["splits"]
    b = gerar_folds(escrever=False)["splits"]
    if a != b:
        falhas.append("gerar_folds nao e deterministico")
    if len(a) != N_FOLDS:
        falhas.append("nao sairam %d folds: %d" % (N_FOLDS, len(a)))

    # 6. a auditoria aprova os folds reais
    aud = auditar_folds(a)
    if not aud["ok"]:
        falhas.append("auditoria de folds reprovou: %s" % aud["problemas"][:2])
    if aud["n_casos_cobertos"] != 32:
        falhas.append("os folds nao cobrem os 32 de train: %d" % aud["n_casos_cobertos"])

    # 7. CONTROLE POSITIVO da auditoria — um fold com caso nos dois lados TEM de
    #    reprovar. Sem isto, uma auditoria que sempre aprova passaria em 6.
    import copy
    ruim = copy.deepcopy(a)
    ruim[0]["train"] = list(ruim[0]["train"]) + [ruim[0]["val"][0]]
    if auditar_folds(ruim)["ok"]:
        falhas.append("a auditoria aprovou um fold com o mesmo caso nos dois lados")

    # 8. e um fold que usasse um caso de VALIDATION tambem TEM de reprovar.
    #    Este e o vazamento que a fase inteira existe para impedir.
    ent = man.carregar(MANIFESTO_V2)
    externo = next(e["case_id"] for e in ent if e["split"] == "validation")
    ruim = copy.deepcopy(a)
    ruim[1]["train"] = list(ruim[1]["train"]) + [externo]
    r = auditar_folds(ruim)
    if r["ok"] or not any("NAO e da particao train" in p for p in r["problemas"]):
        falhas.append("a auditoria aceitou um caso de VALIDATION dentro de um fold")

    # 9. o tempo medido vem dos logs, nao de constante escrita a mao
    med = tempo_medido_26b()
    if med["media_s_por_epoca"] is None or not (60 < med["media_s_por_epoca"] < 600):
        falhas.append("tempo por epoca lido dos logs fora do plausivel: %s" % med)
    if sum(v["n_epocas"] for v in med["por_fold"].values()) != 1250:
        falhas.append("nao foram lidas 1250 epocas dos logs do 26B")

    # 10. o custo escala com epocas e NAO com numero de casos
    c250, c1000 = custo(250, 100.0), custo(1000, 100.0)
    if round(c1000["h_5_folds"] / c250["h_5_folds"], 3) != 4.0:
        falhas.append("o custo nao escalou linearmente com as epocas")

    for f in falhas:
        print("FALHA:", f)
    # 11. a decomposicao de variancia usa os 10 casos reais e reproduz o dp publicado
    dd = decomposicao_dispersao()
    if not dd.get("disponivel"):
        falhas.append("decomposicao de dispersao indisponivel: %s" % dd.get("motivo"))
    else:
        if dd["dp_entre_folds"] != 0.0898:
            falhas.append("o dp entre folds nao reproduz o publicado na Fase 30: %s"
                          % dd["dp_entre_folds"])
        if dd["n_folds"] * dd["casos_por_fold"] != 10:
            falhas.append("a decomposicao nao usou os 10 casos out-of-fold")
        # controle POSITIVO: com grupos obviamente separados, F tem de ficar alto.
        # Sem isto, um F baixo poderia ser da conta, e nao do dado.
        g = [[0.1, 0.11], [0.5, 0.51], [0.9, 0.91]]
        gr = statistics.fmean([x for gg in g for x in gg])
        mse = (2 * sum((statistics.fmean(x) - gr) ** 2 for x in g)) / 2
        msd = sum((x - statistics.fmean(gg)) ** 2 for gg in g for x in gg) / 3
        if mse / msd < 100:
            falhas.append("a conta de F nao separa grupos obviamente distintos")

    # 12. o teto por reamostragem e medido, nao assumido, e o instrumento acusa perda
    tr = teto_por_reamostragem()
    if not tr.get("disponivel"):
        falhas.append("teto por reamostragem indisponivel: %s" % tr.get("motivo"))
    else:
        if len(tr["linhas"]) != 6:
            falhas.append("o teto nao foi medido nos 6 casos do holdout da V1")
        if not (0.5 < tr["dice_teto_min"] <= 1.0):
            falhas.append("teto fora do plausivel: %s" % tr["dice_teto_min"])
        # controle POSITIVO: ida e volta para a MESMA grade tem de dar Dice 1,0.
        # Se der menos, o instrumento esta medindo o proprio ruido, nao a grade.
        import numpy as np
        from nnunetv2.preprocessing.resampling.default_resampling import (
            resample_data_or_seg_to_shape)
        cfg = config_do_plano(ler_plano(PRE_V2))
        a = np.zeros((1, 20, 40, 40), np.uint8)
        a[0, 5:15, 10:30, 10:30] = 1
        esp = np.array([3.0, 1.0, 1.0])
        ida = resample_data_or_seg_to_shape(a, [20, 40, 40], esp, esp,
                                            **cfg["resampling_fn_seg_kwargs"])
        if not np.array_equal(ida, a):
            falhas.append("reamostrar para a MESMA grade mudou a mascara")

    print("autoteste planejar: %d verificacoes, %d falhas" % (12, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--gravar")
    ap.add_argument("--escrever-folds", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    r = rodar()
    print("32F  PLANO V2 (%s), planner %s"
          % (CONFIG, ler_plano(PRE_V2)["experiment_planner_used"]))
    p = r["plano_v2"]
    for k in ("patch_size", "batch_size", "spacing", "median_image_size_in_voxels",
              "batch_dice", "normalization_schemes"):
        print("   %-28s %s" % (k, p[k]))
    ar = p["architecture"]["arch_kwargs"]
    for k in ("n_stages", "features_per_stage", "kernel_sizes", "strides",
              "n_conv_per_stage", "n_conv_per_stage_decoder"):
        print("   arch.%-23s %s" % (k, ar[k]))

    print("\n32G  CAMPO | 26B | V2 | MUDOU?")
    for l in r["comparacao"]:
        print("   %-28s %-30s %-30s %s"
              % (l["campo"], str(l["f26b"])[:30], str(l["v2"])[:30],
                 "MUDOU" if l["mudou"] else "="))

    cp = r["custo_por_patch"]
    print("\n     custo por iteracao: MACs 26B %.5e | V2 %.5e | razao %s"
          % (cp["f26b"]["macs_por_patch"], cp["v2"]["macs_por_patch"],
             cp["razao_macs_v2_sobre_26b"]))
    print("     mapa de ativacao   : %.4e | %.4e | parametros %d | %d"
          % (cp["f26b"]["mapa_ativacao"], cp["v2"]["mapa_ativacao"],
             cp["f26b"]["parametros"], cp["v2"]["parametros"]))

    m = r["tempo_medido_26b"]
    print("\n32I  CUSTO (ancorado no MEDIDO: %.2f s/epoca, %s..%s entre folds)"
          % (m["media_s_por_epoca"], m["min_s"], m["max_s"]))
    for rot in ("custo_250", "custo_1000"):
        c = r[rot]
        print("   %4d epocas -> %.2f h por fold, %.2f h nos 5 folds (%.2f dias)"
              % (c["epocas"], c["h_por_fold"], c["h_5_folds"], c["dias_5_folds"]))
    d = r["disco"]
    print("   disco: raw %.2f GB, preprocessed %.2f GB, resultados previstos ~%.2f GB"
          % (d["v2_raw_gb"], d["v2_preprocessed_gb"], d["f26b_results_gb"]))

    v = r["viabilidade"]
    print("\n32J  VIABILIDADE  %s, %d MiB VRAM (%d livres), RAM %.1f GB, disco livre %.1f GB"
          % (v["gpu"], v["vram_mib"], v["vram_livre_mib_agora"], v["ram_gb"],
             v["disco_livre_gb"]))
    print("   orcamento de ativacao igual ao do 26B: %s" % v["mapa_ativacao_igual_ao_26b"])

    tr = r["teto_por_reamostragem"]
    if tr.get("disponivel"):
        print()
        print("32O  TETO DE DICE IMPOSTO SO PELA GRADE (alvo z = %s mm)" % tr["spacing_alvo"][0])
        for l in tr["linhas"]:
            print("   %-24s nativo z %s  %s -> %s  teto %s"
                  % (l["case_id"], l["spacing_nativo_z"], l["forma_nativa"],
                     l["forma_no_alvo"], l["dice_teto"]))
        print("   media %s  (no 26B o teto era %s: alvo = nativo)"
              % (tr["dice_teto_media"], tr["teto_no_26b"]))

    dd = r["decomposicao_dispersao"]
    if dd.get("disponivel"):
        print()
        print("32O  DE ONDE VEM O dp DE %s ENTRE OS FOLDS DO 26B" % dd["dp_entre_folds"])
        print("   dp caso a caso dentro dos folds : %s" % dd["dp_caso_a_caso_dentro"])
        print("   F(%d,%d) = %s   p = %s"
              % (dd["n_folds"] - 1, dd["n_folds"] * (dd["casos_por_fold"] - 1),
                 dd["F"], dd["p"]))
        print("   efeito de fold detectavel       : %s (componente %s)"
              % (dd["efeito_de_fold_detectavel"], dd["componente_entre_folds"]))
        print("   dp esperado so por amostragem   : %s" % dd["dp_esperado_so_por_amostragem"])

    aud = r["auditoria_folds"]
    print("\n32K  FOLDS (seed %d, funcao do proprio nnU-Net)" % SEED_SPLIT)
    print("   %-6s %-8s %-7s %-34s %s" % ("fold", "train", "val", "fontes na val", "spacing z na val"))
    for l in aud["linhas"]:
        print("   %-6d %-8d %-7d %-34s %s"
              % (l["fold"], l["n_train"], l["n_val"], l["fontes_val"], l["spacing_z_val"]))
    print("   problemas: %s" % (aud["problemas"] or "nenhum"))
    print("   toda val tem as duas fontes: %s" % aud["todos_os_folds_com_duas_fontes_na_val"])

    if a.escrever_folds:
        g = gerar_folds(escrever=True)
        print("\nfolds congelados em %s" % g["arquivo"])

    if a.gravar:
        q = Path(a.gravar)
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str),
                     encoding="utf-8")
        print("escrito:", q)
    return 0 if aud["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
