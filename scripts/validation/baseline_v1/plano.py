"""Fase 19 — desenho do split, validacao do alvo, config do baseline e ambiente.

TUDO AQUI E PLANO. Nada treina, nada baixa, nada avalia. O modulo produz quatro
coisas que precisam existir ANTES de qualquer treino, e cuja utilidade depende
inteiramente de terem sido escritas antes:

  19.4  DESENHO do split — as regras, nao a lista. A lista nao existe porque os
        casos nao existem: preencher split com dado inventado seria a fraude que
        este projeto passou 18 fases documentando nos outros.
  19.8  VALIDACAO DO ALVO contra a ESOPHAGUS_ONTOLOGY_V1, sem segunda definicao.
  19.9  CONFIG do nnU-Net 3d_fullres — dataset.json, comandos, seed.
  19.10 RELATORIO DE AMBIENTE — so versoes realmente instaladas, lidas do
        interpretador. Uma dependencia digitada a mao e uma dependencia inventada.

REUSO
A medicao de mascara contra a ontologia ja existe em `lynos/auditoria.py`
(`medir_mascara`, `classificar_ontologia`). Ela nasceu na pasta do LyNoS mas e
generica, e escrever uma segunda copia aqui criaria exatamente o problema que a
Fase 13 fechou: duas definicoes do mesmo alvo, livres para divergir.

  python -m scripts.validation.baseline_v1.plano --autoteste
  python -m scripts.validation.baseline_v1.plano --ambiente
  python -m scripts.validation.baseline_v1.plano --escrever
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.lynos.auditoria import (  # noqa: E402
    classificar_ontologia, medir_mascara,
)
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase19"
CONFIG = RAIZ / ".clinica-dados" / "baseline_v1"

SEED = 20260906  # unico, fixo, declarado antes de existir treino

# ------------------------------------------------------------ 19.4 desenho do split

DESENHO_SPLIT = {
    "particoes": {
        "train": "dados proprios auditaveis — proveniencia completa obrigatoria",
        "validation": "dados proprios auditaveis — mesma exigencia do train",
        "test": "conjunto externo, congelado ANTES do treino, lido so em contexto 'avaliacao'",
    },
    "regras": [
        "um mesmo caso NUNCA aparece em duas particoes (verificado por case_id)",
        "um mesmo estudo NUNCA aparece em duas particoes (verificado por study_id)",
        "uma mesma serie NUNCA aparece em duas particoes (verificado por series_id)",
        "um mesmo CONTEUDO nunca aparece em duas particoes (verificado por sha256 de "
        "imagem e de mascara) — as tres chaves acima podem ser renomeadas por engano; "
        "o hash nao pode",
        "a fonte de cada caso e rastreavel ate source_dataset + source_case_id + source_doi",
        "a instituicao e rastreavel quando disponivel; quando nao, UNKNOWN explicito",
        "caso com proveniencia UNKNOWN NAO entra em TEST sem justificativa gravada em notes",
        "o TEST e congelado antes do treino e qualquer alteracao exige VERSION INCREMENT",
        "o TEST nunca participa de selecao de modelo, de hiperparametro nem de epoca",
    ],
    "proporcao_alvo": {
        "nota": (
            "NAO fixada aqui. Fixar proporcao antes de saber quantos casos existem "
            "seria numero inventado. A proporcao entra na V2 do desenho, junto com a "
            "primeira lista real de casos."
        ),
        "restricao_ja_conhecida": (
            "o TEST precisa de n suficiente para um IC util. Medido na Fase 18.5 com a "
            "dispersao do proprio projeto: n=15 da IC95 de largura 0,077 de Dice e poder "
            "0,485 para separar uma diferenca de 0,05. Qualquer TEST de n=15 herda isso."
        ),
    },
    "estado": "DESENHO — nenhuma lista de casos existe, e nenhuma sera inventada",
}

# ------------------------------------------------------------ 19.9 baseline proposto

BASELINE = {
    "id": "BASELINE_ESOFAGO_VRMED_V1",
    "estado": "PRE-REGISTRO — nao treinado",
    "arquitetura": "nnU-Net v2, configuracao 3d_fullres",
    "por_que": [
        "e a arquitetura mais simples que a stack ja instalada suporta sem codigo novo "
        "(nnunetv2 2.8.1 ja presente, e o proprio TotalSegmentator roda sobre ela)",
        "o planner do nnU-Net deriva patch size, spacing e normalizacao DO DADO, o que "
        "remove um canal inteiro de escolha humana — e portanto de vazamento por escolha",
        "torna o baseline comparavel com o TotalSegmentator sem replicar a opacidade "
        "dele: a diferenca sera a proveniencia, nao a arquitetura",
    ],
    "o_que_nao_e": (
        "nao e proposta de arquitetura melhor. A Fase 19 nao tem dado para escolher "
        "arquitetura, e escolher por resultado de LCTSC seria usar TEST para desenho."
    ),
    "seed": SEED,
    "folds": {
        "plano": "treinar os 5 folds, nao apenas fold=0",
        "motivo": (
            "a Fase 16 mediu que os pesos publicos do TotalSegmentator sao fold=0 e que "
            "o splits_final.json nunca foi publicado — logo nem as imagens declaradas sao "
            "atribuiveis ao treino efetivo. Publicar splits_final.json e os 5 folds e "
            "exatamente o que fecha esse buraco no nosso lado."
        ),
    },
    "hiperparametros": (
        "os padroes do nnU-Net, sem ajuste. Ajustar exigiria um sinal, e o unico sinal "
        "disponivel viria de VALIDATION ou TEST — o primeiro so apos o treino existir, "
        "o segundo nunca."
    ),
    "alvo": {
        "definicao": onto.VERSAO,
        "rotulos": {"0": "background", "1": "esophagus"},
        "representacao": onto.ALVO["representacao"],
        "parede_e_lumen": onto.ALVO["parede_e_lumen"],
    },
    "metricas": list(onto.METRICAS_CONGELADAS),
    "criterio_de_sucesso": (
        "NAO DEFINIDO como limiar numerico. Um limiar escolhido agora, sem dado, seria "
        "chute; escolhido depois, seria ajuste ao resultado. O criterio da V1 e "
        "procedimental: o modelo e aceito se for REPRODUZIVEL a partir do manifesto "
        "congelado, do seed e do commit — nao se atingir um Dice."
    ),
    "criterio_de_regressao": (
        "qualquer execucao que nao reproduza o sha256 do manifesto congelado, ou que "
        "leia TEST em contexto de treino, e regressao — independentemente do Dice."
    ),
}


def dataset_json(n_train: int) -> dict:
    """dataset.json do nnU-Net v2. Formato do proprio nnU-Net, nao invencao nossa."""
    return {
        "channel_names": {"0": "CT"},
        "labels": {"background": 0, "esophagus": 1},
        "numTraining": n_train,
        "file_ending": ".nii.gz",
        "overwrite_image_reader_writer": "SimpleITKIO",
        "_vrmed": {
            "ontologia": onto.VERSAO,
            "congelada_em": onto.CONGELADA_EM,
            "protocolo": onto.PROTOCOLO_DE_REFERENCIA,
            "aviso": ("o alvo e mascara binaria PREENCHIDA: parede e lumen sao UM objeto. "
                      "Separa-los seria outra tarefa, e exigiria uma V2 da ontologia."),
        },
    }


def comandos(dataset_id: int = 501) -> list:
    d = str(dataset_id)
    return [
        {"passo": "planejar e pre-processar",
         "cmd": "nnUNetv2_plan_and_preprocess -d " + d + " --verify_dataset_integrity",
         "le": "train + validation", "nunca_le": "test"},
        {"passo": "treinar os 5 folds",
         "cmd": "nnUNetv2_train " + d + " 3d_fullres FOLD --npz   (FOLD em 0..4)",
         "le": "train + validation", "nunca_le": "test"},
        {"passo": "escolher pos-processamento",
         "cmd": "nnUNetv2_find_best_configuration " + d + " -c 3d_fullres",
         "le": "validation", "nunca_le": "test"},
        {"passo": "congelar e publicar o split efetivo",
         "cmd": "copiar splits_final.json para o snapshot do dataset",
         "le": "-", "nunca_le": "-",
         "nota": "e o arquivo cuja ausencia torna o baseline atual inauditavel"},
        {"passo": "avaliar UMA vez, no fim",
         "cmd": "nnUNetv2_predict ... (contexto 'avaliacao')",
         "le": "test", "nunca_le": "-",
         "nota": "uma unica execucao, sem retorno para desenho"},
    ]


# ------------------------------------------------------- 19.8 validacao do alvo

# Faixa de volume plausivel para esofago toracico inteiro, em mL. Origem declarada:
# a propria coorte medida pelo projeto (LyNoS 26,5-62,7 mL na Fase 18) mais folga.
# NAO e criterio anatomico: e detector de outlier grosseiro, e esta escrito assim.
VOLUME_ML_MIN = 5.0
VOLUME_ML_MAX = 150.0


def validar_alvo(caminho: Path) -> dict:
    """19.8 — um caso contra a ontologia congelada, mais os testes de sanidade.

    A parte ontologica NAO e reimplementada: vem de `lynos.auditoria`, que e a mesma
    funcao que julgou o LyNoS na Fase 18. Duas copias divergiriam, e a divergencia
    apareceria como diferenca de desempenho.
    """
    m = medir_mascara(Path(caminho))
    v = classificar_ontologia(m)
    problemas = [k for k, c in v["criterios"].items() if not c["passou"]]

    if m["mascara_vazia"]:
        problemas.append("mascara_vazia")
    if not (VOLUME_ML_MIN <= m["volume_ml"] <= VOLUME_ML_MAX):
        problemas.append("volume_fora_da_faixa (%.2f mL)" % m["volume_ml"])
    if m["dtype"] not in ("uint8", "int8", "uint16", "int16", "int32", "int64", "bool"):
        problemas.append("dtype de ponto flutuante em mascara: " + m["dtype"])

    return {"medidas": m, "ontologia": v, "problemas": problemas, "aprovado": not problemas}


# --------------------------------------------------------- 19.10 reprodutibilidade

PACOTES = ("nnunetv2", "torch", "numpy", "scipy", "scikit-image", "SimpleITK",
           "pydicom", "nibabel", "TotalSegmentator", "dcmrtstruct2nii",
           "batchgenerators", "acvl_utils", "dynamic_network_architectures",
           "monai", "trimesh", "vtk", "scikit-learn")


def ambiente() -> dict:
    """So versoes REALMENTE instaladas, lidas do interpretador. Ausente vira AUSENTE."""
    pk = {}
    for p in PACOTES:
        try:
            pk[p] = version(p)
        except PackageNotFoundError:
            pk[p] = "AUSENTE"
    try:
        import torch
        gpu = {
            "cuda_compilada": torch.version.cuda,
            "disponivel": bool(torch.cuda.is_available()),
            "dispositivo": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "memoria_MiB": (round(torch.cuda.get_device_properties(0).total_memory / 2 ** 20)
                            if torch.cuda.is_available() else None),
        }
    except Exception as e:  # noqa: BLE001
        gpu = {"erro": str(e)}
    return {
        "python": sys.version.split()[0],
        "plataforma": platform.platform(),
        "processador": platform.processor(),
        "pacotes": pk,
        "gpu": gpu,
        "seed": SEED,
        "ontologia": onto.VERSAO,
        "esquema_dataset": man.VERSAO_ESQUEMA,
    }


# --------------------------------------------------------------------- autoteste


def autoteste() -> int:
    import numpy as np
    import nibabel as nib
    falhas = []

    # o ambiente tem de refletir o interpretador, nao uma lista digitada
    a = ambiente()
    if a["pacotes"]["nnunetv2"] == "AUSENTE":
        falhas.append("nnunetv2 ausente — o baseline proposto nao e executavel nesta stack")
    if a["pacotes"]["monai"] != "AUSENTE":
        falhas.append("monai apareceu como instalado; o relatorio precisa refletir a realidade")
    if a["seed"] != SEED:
        falhas.append("seed do relatorio divergiu da constante")

    # dataset.json tem de carregar o alvo da ontologia congelada, nao um literal
    dj = dataset_json(42)
    if dj["labels"] != {"background": 0, "esophagus": 1}:
        falhas.append("rotulos do dataset.json mudaram")
    if dj["numTraining"] != 42:
        falhas.append("numTraining nao propagou")
    if dj["_vrmed"]["ontologia"] != onto.VERSAO:
        falhas.append("dataset.json nao carimba a ontologia congelada")

    # Nenhum passo pode ler TEST sem declarar o contexto 'avaliacao'. A declaracao
    # pode estar no comando ou na nota, entao a busca e na entrada inteira — checar
    # so um campo foi o primeiro jeito de escrever isto, e o autoteste derrubou.
    for c in comandos():
        if c["le"] == "test" and "avaliacao" not in json.dumps(c, ensure_ascii=False):
            falhas.append("passo le TEST sem declarar contexto avaliacao: " + c["passo"])
    # e nenhum passo de TREINO pode listar test em 'le'
    for c in comandos():
        if "train" in c["le"] and "test" in c["le"]:
            falhas.append("passo mistura train e test na mesma leitura: " + c["passo"])

    # 19.8 — controle POSITIVO: cilindro solido aprovado, anel oco reprovado
    tmp = Path(__file__).parent / "_autoteste_alvo.nii.gz"
    yy, xx = np.ogrid[:60, :60]
    d = np.sqrt((yy - 30) ** 2 + (xx - 30) ** 2)

    solido = np.zeros((60, 60, 40), dtype=np.uint8)
    solido[d <= 8] = 1
    nib.save(nib.Nifti1Image(solido, np.diag([1.0, 1.0, 2.0, 1.0])), str(tmp))
    r = validar_alvo(tmp)
    if not r["aprovado"]:
        falhas.append("cilindro solido reprovado: " + str(r["problemas"]))

    anel = np.zeros((60, 60, 40), dtype=np.uint8)
    anel[(d >= 5) & (d <= 8)] = 1
    nib.save(nib.Nifti1Image(anel, np.diag([1.0, 1.0, 2.0, 1.0])), str(tmp))
    if validar_alvo(tmp)["aprovado"]:
        falhas.append("anel oco (so parede) foi aprovado como alvo")

    vazia = np.zeros((60, 60, 40), dtype=np.uint8)
    nib.save(nib.Nifti1Image(vazia, np.diag([1.0, 1.0, 2.0, 1.0])), str(tmp))
    rv = validar_alvo(tmp)
    if rv["aprovado"] or "mascara_vazia" not in rv["problemas"]:
        falhas.append("mascara vazia nao foi recusada: " + str(rv["problemas"]))

    # volume absurdo tem de cair no detector de outlier
    enorme = np.ones((200, 200, 200), dtype=np.uint8)
    nib.save(nib.Nifti1Image(enorme, np.diag([1.0, 1.0, 1.0, 1.0])), str(tmp))
    re_ = validar_alvo(tmp)
    if re_["aprovado"] or not any("volume_fora" in p for p in re_["problemas"]):
        falhas.append("volume de 8000 mL foi aceito: " + str(re_["problemas"]))

    # dtype float tem de ser recusado em mascara
    flt = np.zeros((60, 60, 40), dtype=np.float32)
    flt[d <= 8] = 1.0
    nib.save(nib.Nifti1Image(flt, np.diag([1.0, 1.0, 2.0, 1.0])), str(tmp))
    rf = validar_alvo(tmp)
    if not any("dtype" in p for p in rf["problemas"]):
        falhas.append("mascara float32 passou sem reclamacao de dtype")

    tmp.unlink(missing_ok=True)

    # o desenho do split nao pode conter lista de casos
    txt = json.dumps(DESENHO_SPLIT)
    if any(k in txt for k in ("case_id\":", "LCTSC-", "pat1")):
        falhas.append("o DESENHO do split contem caso concreto — isso seria inventar dado")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste plano: %d verificacoes, %d falhas" % (14, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--ambiente", action="store_true")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args(argv)

    if a.autoteste:
        return autoteste()
    if a.ambiente:
        print(json.dumps(ambiente(), indent=1, ensure_ascii=False))
        return 0
    if autoteste() != 0:
        return 1
    print()

    SAIDA.mkdir(parents=True, exist_ok=True)
    CONFIG.mkdir(parents=True, exist_ok=True)
    amb = ambiente()
    doc = {
        "fase": 19,
        "estado": "PRE-REGISTRO — nada treinado",
        "esquema_dataset": man.VERSAO_ESQUEMA,
        "ontologia": onto.VERSAO,
        "desenho_split": DESENHO_SPLIT,
        "baseline": BASELINE,
        "dataset_json_modelo": dataset_json(0),
        "comandos": comandos(),
        "validacao_do_alvo": {
            "fonte": "scripts.validation.lynos.auditoria (mesma funcao que julgou o LyNoS)",
            "volume_ml_min": VOLUME_ML_MIN,
            "volume_ml_max": VOLUME_ML_MAX,
            "criterios": ["binaria", "nao_vazia", "preenchida_parede_mais_lumen",
                          "objeto_unico_dominante", "calibre_compativel_com_esofago",
                          "dtype inteiro", "volume dentro da faixa"],
        },
        "ambiente": amb,
    }
    (SAIDA / "plano_baseline_v1.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    (CONFIG / "dataset.json.modelo").write_text(
        json.dumps(dataset_json(0), indent=1, ensure_ascii=False), encoding="utf-8")
    (CONFIG / "ambiente.json").write_text(
        json.dumps(amb, indent=1, ensure_ascii=False), encoding="utf-8")

    print("AMBIENTE (so o que esta instalado)")
    for k, v in amb["pacotes"].items():
        print("  %-32s %s" % (k, v))
    print("  GPU:", amb["gpu"].get("dispositivo"), amb["gpu"].get("memoria_MiB"), "MiB",
          "| CUDA", amb["gpu"].get("cuda_compilada"))
    print("  seed:", amb["seed"])
    print()
    print("SPLIT: %s" % DESENHO_SPLIT["estado"])
    print("BASELINE: %s — %s" % (BASELINE["id"], BASELINE["estado"]))
    print("\nescrito:", SAIDA / "plano_baseline_v1.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
