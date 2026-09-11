"""Fase 32 — escreve `docs/FASE32-PROTOCOLO-TREINO-V2.json` a partir do plano real.

POR QUE O PROTOCOLO E GERADO, E NAO DIGITADO

Metade do protocolo sao decisoes (o trainer, as epocas, o checkpoint primario, o que fica
proibido) e metade sao valores que ja existem em disco (patch, batch, spacing, kernels,
os tres `sha256`). Digitar a segunda metade a mao seria abrir a porta para um protocolo
que descreve um plano diferente do que sera executado — e o erro so apareceria depois.

Aqui as decisoes estao escritas neste arquivo e os valores sao LIDOS do plano. O teste
`test_fase32_replanejamento.py` confere as duas metades contra o disco de novo, para que
regenerar sem querer com outro plano tambem caia.

  python -m scripts.validation.fase32.gerar_protocolo
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.fase32 import planejar as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
DESTINO = RAIZ / "docs" / "FASE32-PROTOCOLO-TREINO-V2.json"
V3 = RAIZ / "docs" / "BASELINE-ESOPHAGUS-VRMED-V3.md"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def montar() -> dict:
    pre = pl.PRE_V2
    plano = pl.ler_plano(pre)
    cfg = pl.config_do_plano(plano)
    ark = cfg["architecture"]["arch_kwargs"]
    splits = json.loads((pre / "splits_final.json").read_text(encoding="utf-8"))
    cp = pl.custo_por_patch()["v2"]

    return {
        "fase": 32,
        "documento": "FASE32-PROTOCOLO-TREINO-V2",
        "congelado_em": "2026-09-11",
        "natureza": ("protocolo de treinamento congelado ANTES da execucao. A Fase 32 nao "
                     "treinou, nao inferiu e nao produziu metrica de modelo."),

        "dataset": "VRMED-ESOPHAGUS-POOL46-V2",
        "dataset_nnunet": "Dataset502_VRmedEsofagoV2",
        "dataset_id": 502,
        "manifesto": "docs/VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl",
        "manifesto_sha256":
            "f4bd480e8f8046923a8990096d40832145fb405f1a84ca85e8f3be6e6d20f60b",
        "split_rule": "VRMED-SPLIT-RULE-V2",
        "train": 32, "validation": 14, "test": 0,

        "preregistro_vigente": "docs/BASELINE-ESOPHAGUS-VRMED-V3.md",
        "preregistro_vigente_sha256": sha(V3),
        "preregistro_emendado": True,
        "preregistro_anteriores_intactos": ["docs/BASELINE-ESOPHAGUS-VRMED-V1.md",
                                            "docs/BASELINE-ESOPHAGUS-VRMED-V2.md"],

        # As duas listas que a V3 tirou da prosa e pos em codigo. O teste le daqui.
        "fontes_permitidas_no_pool": ["4D-Lung (TCIA)", "LCTSC (TCIA)"],
        # O 4D-Lung entra nesta lista pela regra abaixo, nao por proibicao herdada: os 16
        # casos eleigiveis dele estao todos em train ou validation, entao ele nunca podera
        # ser TEST deste projeto. O teste 28 falha se a lista deixar de refletir a regra.
        "fontes_proibidas_como_test": ["4D-Lung (TCIA)", "LCTSC (TCIA)", "LyNoS",
                                       "NSCLC-Radiomics", "SegTHOR"],
        "regra_fonte_usada_vira_proibida_como_test": True,

        "planner": {
            "experiment_planner": plano["experiment_planner_used"],
            "configuration": pl.CONFIG,
            "patch_size": [int(x) for x in cfg["patch_size"]],
            "batch_size": int(cfg["batch_size"]),
            "target_spacing": [float(x) for x in cfg["spacing"]],
            "median_image_size_in_voxels": [float(x) for x in cfg["median_image_size_in_voxels"]],
            "normalization": cfg["normalization_schemes"],
            "batch_dice": bool(cfg["batch_dice"]),
            "network_class": cfg["architecture"]["network_class_name"],
            "n_stages": ark["n_stages"],
            "features_per_stage": ark["features_per_stage"],
            "kernel_sizes": ark["kernel_sizes"],
            "strides": ark["strides"],
            "n_conv_per_stage": ark["n_conv_per_stage"],
            "n_conv_per_stage_decoder": ark["n_conv_per_stage_decoder"],
            "parametros": cp["parametros"],
            "voxels_por_patch": cp["voxels_por_patch"],
            "macs_por_patch": cp["macs_por_patch"],
            "plans_sha256": sha(pre / "nnUNetPlans.json"),
            "fingerprint_sha256": sha(pre / "dataset_fingerprint.json"),
            "splits_sha256": sha(pre / "splits_final.json"),
            "plano_reproduzido_em_duas_execucoes_independentes": True,
            "plano_editado_a_mao": False,
        },

        "folds": {
            "n": pl.N_FOLDS,
            "origem": ("nnunetv2.utilities.crossval_split.generate_crossval_split, "
                       "seed=%d — a mesma funcao que o nnUNetTrainer.do_split chama"
                       % pl.SEED_SPLIT),
            "estratificados": False,
            "motivo_nao_estratificar": ("estratificar faria do split um artefato de desenho "
                                        "nosso; o pre-registro vincula os defaults do "
                                        "framework, e estratificar nao compra poder"),
            "congelado_antes_do_treino": True,
            "arquivo": ("clinica-dados/fase32/nnUNet_preprocessed/"
                        "Dataset502_VRmedEsofagoV2/splits_final.json"),
            "tamanhos": [{"fold": i, "train": len(s["train"]), "val": len(s["val"])}
                         for i, s in enumerate(splits)],
            "limitacao_declarada": ("os folds 2 e 3 tem validacao interna composta so de "
                                    "LCTSC; a dispersao entre folds mistura fonte e "
                                    "amostragem, e por isso nao e endpoint"),
        },

        "trainer": "nnUNetTrainer_250epochs",
        "epochs": 250,
        "checkpoint_primary": "checkpoint_final",
        "checkpoint_secondary": "checkpoint_best",

        "treinamento": {
            "comando": ("nnUNetv2_train 502 3d_fullres FOLD "
                        "-tr nnUNetTrainer_250epochs --npz"),
            "folds_a_rodar": [0, 1, 2, 3, 4],
            "learning_rate": "1e-2 inicial",
            "optimizer": "SGD, momentum 0.99, nesterov, weight_decay 3e-5",
            "scheduler": "PolyLRScheduler(initial_lr, max_steps=num_epochs=250, exponent=0.9)",
            "loss": ("DC_and_CE_loss (Dice + CrossEntropy, weight_ce=1, weight_dice=1, "
                     "do_bg=False, batch_dice=True)"),
            "deep_supervision": True,
            "iteracoes_por_epoca": pl.ITERACOES_POR_EPOCA,
            "iteracoes_de_validacao_por_epoca": pl.ITERACOES_VALIDACAO,
            "oversample_foreground_percent": 0.33,
            "seed_behavior": (
                "o nnUNetTrainer 2.8.1 NAO semeia torch, numpy nem random, e roda com "
                "cudnn.deterministic=False e cudnn.benchmark=True. O unico passo semeado e "
                "a divisao em 5 folds (seed=12345 fixo no framework), e ela esta congelada "
                "por sha256 em splits_final.json antes do treino. vrmed_seed=20260906 e "
                "identificador de experimento, nao controle de treinamento."),
            "stopping": (
                "sem parada antecipada. O trainer roda as 250 epocas inteiras; a Fase 26A "
                "recusou early stopping por cinco motivos, o decisivo sendo a "
                "incompatibilidade estrutural com o PolyLR de horizonte fixo."),
            "selecao_por_holdout": (
                "proibida. Nenhuma epoca, checkpoint, pos-processamento ou limiar e "
                "escolhido a partir dos 14 casos da particao validation."),
            "find_best_configuration": (
                "NAO roda. Nao rodou no 26B (nenhum artefato em disco) e nao roda aqui, "
                "para manter a comparacao e para nao escolher pos-processamento a partir "
                "de 32 predicoes out-of-fold."),
            "validation": (
                "dois niveis, homonimos que nao se misturam: (a) validacao INTERNA do "
                "nnU-Net, out-of-fold sobre os 32 de train; (b) particao validation do "
                "manifesto, 14 casos, holdout pos-treino, lida UMA vez ao fim, com as oito "
                "metricas congeladas, pelo ensemble dos 5 folds — como foi no 26B."),
            "hardware": (
                "NVIDIA GeForce RTX 4060 Ti, 16379 MiB de VRAM; 34,2 GB de RAM; 12 CPUs "
                "logicas; Windows 11; python 3.13.11, torch 2.6.0+cu124, CUDA 12.4, "
                "nnunetv2 2.8.1, driver 591.86"),
            "expected_runtime_h": {
                "central": 49, "banda": [47, 52],
                "base": ("138 +- 3 s por epoca: 137,56 s medidos nas 1250 epocas do 26B e "
                         "140,42 s medidos nas 64 epocas da Fase 26, mesma configuracao, "
                         "sessao diferente. Mais 0,5 a 1,5 h fora das epocas."),
                "custo_por_iteracao_identico_ao_26b": True},
            "armazenamento_previsto_gb": {"raw": 1.08, "preprocessed": 1.24,
                                          "resultados": [3.0, 3.5], "disco_livre": 103.7},
            "passo_zero_obrigatorio": (
                "antes dos 5 folds, rodar nnUNetTrainerBenchmark_5epochs no fold 0 com "
                "nvidia-smi em paralelo (~15 min) para MEDIR s/epoca e pico de VRAM no "
                "Dataset502. A Fase 32 esta proibida de treinar e nao o rodou; as duas "
                "grandezas seguem sendo inferencia ate la. Ele grava em arvore propria e "
                "nao produz checkpoint."),
        },

        "endpoints_pre_declarados": {
            "primario": ("Dice out-of-fold por caso, n=32, com quebra por source_dataset. "
                         "E o unico endpoint com n suficiente para dizer alguma coisa."),
            "secundarios": [
                "taxa de colapso out-of-fold (Dice < 0,50) com intervalo de Wilson",
                ("as oito metricas congeladas nos 14 casos do holdout, em tres recortes "
                 "declarados agora: os 6 comuns a V1, os 8 do LCTSC, e os 14"),
                ("os 6 casos comuns a V1 e V2 comparados com o 26B — descritivo, poder "
                 "baixo com n=6, e confundido por dominio: os 6 sao 100% 4D-Lung enquanto "
                 "o TRAIN da V2 e 69% LCTSC"),
            ],
            "retirado": (
                "'o dp entre folds cai com TRAIN=32?' foi RETIRADO como objetivo. No 26B a "
                "analise de variancia sobre os 10 Dice out-of-fold da F(4,5)=0,774, "
                "p=0,586: nao ha efeito de fold detectavel acima do efeito de caso. E o dp "
                "cairia so por a validacao interna passar de 2 para 6-7 casos."),
            "banda_nula_do_dp": (
                "se o dp entre folds for reportado, e descritivo: sob 'nada mudou exceto o "
                "n', o esperado so por amostragem fica em torno de 0,054 a 0,059."),
            "os_8_do_lctsc_no_holdout": (
                "sao a unica primeira leitura disponivel no projeto. Ficam declarados AGORA "
                "como parte da leitura unica do holdout, reportados em recorte proprio, e "
                "NAO como conjunto de teste — a fonte deles ja esta no TRAIN."),
        },

        "limitacoes_declaradas_antes": [
            ("a comparacao 26B x Fase 33 e de pipeline inteiro contra pipeline inteiro: "
             "mudam n, composicao de fonte, protocolo de anotacao, spacing-alvo em z, "
             "patch_size e as estatisticas de normalizacao. NAO e 'uma variavel so'."),
            ("250 epocas sao 125.000 patches com 10 ou com 32 casos: a exposicao media por "
             "voxel cai de ~966x para ~227x. Um resultado fraco fica AMBIGUO entre 'mais "
             "casos nao ajudaram' e 'o orcamento de passos nao acompanhou a diversidade'."),
            ("250 epocas sao um cronograma PolyLR completo, nao um prefixo de 1000. Cobrar "
             "o canonico depois custa o valor cheio a mais, nao a diferenca."),
            ("institution e UNKNOWN em 46 de 46 registros; a diversidade institucional e da "
             "colecao, nao do caso, e nao pode ser afirmada por caso."),
            "os folds 2 e 3 tem validacao interna composta so de LCTSC.",
            ("o criterio de sucesso 4 da V1 (TEST lido uma vez) e insatisfazivel com "
             "TEST=0: nenhum modelo pode ser descrito como aceito pelos cinco criterios."),
            ("o teto de Dice imposto so pela troca de grade nos 6 casos comuns foi MEDIDO: "
             "0,9989 em media, 1,0 em 5 de 6. Pequeno, mas nao e 1,0 como era no 26B."),
        ],

        "proibido": [
            ("chamar o artefato da Fase 33 de baseline, baseline V2 ou baseline ampliado. "
             "O nome e MODELO INTERNO EXPERIMENTAL V2."),
            ("reportar qualquer numero dos 14 como desempenho externo, independencia ou "
             "generalizacao."),
            "nunca descrever o LCTSC como avaliacao independente deste projeto.",
            "preencher o TEST.",
            "usar desempenho para editar dataset, remover caso ou reescolher fold.",
            "as frases congeladas em ontologia_esofago.FRASES_PROIBIDAS.",
        ],

        "decision": (
            "PROTOCOLO A — nnUNetTrainer_250epochs, 5 folds, Dataset502_VRmedEsofagoV2, "
            "3d_fullres, checkpoint_final primario e checkpoint_best secundario, sem parada "
            "antecipada e sem qualquer selecao pela particao validation. Fundamento: a Fase "
            "26A, secao 7, autorizou nominalmente esta linha experimental separada, que NAO "
            "e o baseline, e a Fase 33 continua com 5 folds a linha que a 26B abriu com 10 "
            "casos. O baseline canonico de 1000 epocas permanece PENDENTE e declarado como "
            "divida. O custo e fato registrado, nao e o fundamento da escolha."),
        "protocol_locked": True,
        "proxima_fase": "Fase 33 — TREINO",
    }


def main(argv=None) -> int:
    p = montar()
    DESTINO.write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
    print("escrito:", DESTINO)
    print("   pre-registro vigente:", p["preregistro_vigente_sha256"][:16])
    print("   plano               :", p["planner"]["plans_sha256"][:16])
    print("   folds               :", p["planner"]["splits_sha256"][:16])
    print("   decisao             :", p["decision"][:60], "...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
