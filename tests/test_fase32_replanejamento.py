"""Fase 32 — planejou-se um treino sem treinar, e nada do passado pode ter mudado.

Quatro metades:

  [NADA MUDOU]   V1, V2, checkpoints, predições e árvores de treino anteriores,
                 comparados com a impressão digital tirada ANTES da fase.

  [NADA RODOU]   nenhuma época nova, nenhuma predição nova, nenhum dataset além dos
                 dois esperados, nenhum resultado escrito na árvore da Fase 32.

  [PLANO]        o dataset V2 do nnU-Net, o plano do planner, os 5 folds, e a coerência
                 entre o que o protocolo declara e o que está em disco.

  [PROTOCOLO]    o documento existe, fixa os campos exigidos, e não altera o
                 pré-registro em silêncio.

  python tests/test_fase32_replanejamento.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase32 import integridade as integ  # noqa: E402
from scripts.validation.fase32 import planejar as pl  # noqa: E402

MAN_V1 = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAP_V1 = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
MAN_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl"
SNAP_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-SNAPSHOT-V2.json"
PRE_V1 = RAIZ / "docs" / "BASELINE-ESOPHAGUS-VRMED-V1.md"
PRE_V2 = RAIZ / "docs" / "BASELINE-ESOPHAGUS-VRMED-V2.md"

ANTES = RAIZ / "docs" / "overnight" / "phase32" / "integridade_antes.json"
DEPOIS = RAIZ / "docs" / "overnight" / "phase32" / "integridade_depois.json"
PROTOCOLO = RAIZ / "docs" / "FASE32-PROTOCOLO-TREINO-V2.json"

F32 = RAIZ / ".clinica-dados" / "fase32"
DS = F32 / "nnUNet_raw" / "Dataset502_VRmedEsofagoV2"
PRE = F32 / "nnUNet_preprocessed" / "Dataset502_VRmedEsofagoV2"

SHA_V1 = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"
SHA_V2 = "f4bd480e8f8046923a8990096d40832145fb405f1a84ca85e8f3be6e6d20f60b"
V1 = {"train": 10, "validation": 6, "test": 0}
V2 = {"train": 32, "validation": 14, "test": 0}

# Os dois únicos identificadores de dataset que o projeto tem. Um terceiro aparecendo
# significa que alguém montou um dataset alternativo, que é o que 32E proíbe.
DATASETS_ESPERADOS = {"Dataset501_VRmedEsofago", "Dataset502_VRmedEsofagoV2"}


class Pulado(Exception):
    """Artefato ausente. NÃO é passar."""


def _v1():
    return man.carregar(MAN_V1)


def _v2():
    return man.carregar(MAN_V2)


def _protocolo():
    if not PROTOCOLO.exists():
        raise Pulado("protocolo ausente")
    return json.loads(PROTOCOLO.read_text(encoding="utf-8"))


def _plano():
    if not (PRE / "nnUNetPlans.json").exists():
        raise Pulado("plano do nnU-Net ausente")
    return json.loads((PRE / "nnUNetPlans.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------- [NADA MUDOU]


def test_01_manifesto_v1_intacto():
    r = man.verificar_congelamento(_v1(), json.loads(SNAP_V1.read_text(encoding="utf-8")))
    assert r["intacto"], "manifesto V1 divergiu: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_V1, "sha256 canônico da V1 mudou"
    por = {p: sum(1 for e in _v1() if e["split"] == p) for p in man.PARTICOES}
    assert por == V1, por


def test_02_manifesto_v2_intacto():
    r = man.verificar_congelamento(_v2(), json.loads(SNAP_V2.read_text(encoding="utf-8")))
    assert r["intacto"], "manifesto V2 divergiu: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_V2, "sha256 canônico da V2 mudou"


def test_03_test_continua_zero_e_inalcancavel():
    for ent in (_v1(), _v2()):
        assert sum(1 for e in ent if e["split"] == "test") == 0
        try:
            man.carregar_particao(ent, "test", "treino")
            raise AssertionError("o contexto de treino alcançou TEST")
        except man.AcessoIndevido:
            pass


def test_04_train_v2_tem_32():
    assert sum(1 for e in _v2() if e["split"] == "train") == 32


def test_05_validation_v2_tem_14():
    por = {p: sum(1 for e in _v2() if e["split"] == "validation") for p in ("validation",)}
    assert por["validation"] == 14
    assert {p: sum(1 for e in _v2() if e["split"] == p) for p in man.PARTICOES} == V2


def test_06_hash_do_manifesto_confere_com_o_declarado():
    assert man.sha256_texto(man._canonico(_v2())) == SHA_V2
    p = _protocolo()
    assert p["manifesto_sha256"] == SHA_V2, "o protocolo aponta outro manifesto"


def test_07_nada_historico_mudou_entre_antes_e_depois():
    if not (ANTES.exists() and DEPOIS.exists()):
        raise Pulado("impressão digital antes/depois ausente")
    a = json.loads(ANTES.read_text(encoding="utf-8"))
    b = json.loads(DEPOIS.read_text(encoding="utf-8"))
    r = integ.comparar(a, b)
    assert r["intacto"], "divergências: %s" % r["divergencias"][:8]


def test_08_nenhum_checkpoint_alterado():
    if not ANTES.exists():
        raise Pulado("impressão digital ausente")
    a = json.loads(ANTES.read_text(encoding="utf-8"))
    difs = []
    for rotulo in ("f26_results", "f26b_results"):
        alvo = a["alvos"][rotulo]
        base = RAIZ / alvo["caminho"]
        for rel, sha in alvo["arquivos"].items():
            if not rel.endswith(".pth"):
                continue
            p = base / rel
            if not p.exists():
                difs.append("sumiu: %s" % rel)
            elif man.sha256_arquivo(p) != sha:
                difs.append("alterado: %s" % rel)
    assert not difs, difs
    n = sum(1 for rotulo in ("f26_results", "f26b_results")
            for rel in a["alvos"][rotulo]["arquivos"] if rel.endswith(".pth"))
    assert n == 12, "esperados 12 checkpoints históricos, achados %d" % n


def test_09_nenhuma_predicao_nova():
    if not ANTES.exists():
        raise Pulado("impressão digital ausente")
    a = json.loads(ANTES.read_text(encoding="utf-8"))["alvos"]["f26b_predicoes"]
    base = RAIZ / a["caminho"]
    agora = sorted(str(p.relative_to(base)).replace("\\", "/")
                   for p in base.rglob("*") if p.is_file())
    assert agora == sorted(a["arquivos"]), "o conjunto de predições mudou"


# --------------------------------------------------------------- [NADA RODOU]


def test_10_nenhuma_epoca_nova_em_lugar_nenhum():
    """Conta `Epoch time:` em TODO log de treino do projeto. 1250 e só 1250."""
    logs = list((RAIZ / ".clinica-dados").rglob("training_log_*.txt"))
    total = {}
    for p in logs:
        n = len(re.findall(r"Epoch time:", p.read_text(encoding="utf-8", errors="replace")))
        total[str(p.relative_to(RAIZ)).replace("\\", "/")] = n
    soma = sum(total.values())
    # 26B: 5 folds x 250 = 1250. Fase 26: fold 0 pausado, mais os logs preservados do
    # incidente de treino duplicado. O número exato é o que a Fase 31 já registrava.
    assert soma == 1250 + sum(v for k, v in total.items() if "/fase26/" in k), \
        "apareceram épocas fora do 26B: %s" % total
    assert not any("/fase32/" in k for k in total), \
        "há log de TREINO na árvore da Fase 32: %s" % [k for k in total if "/fase32/" in k]


def test_11_a_arvore_de_resultados_da_fase32_esta_vazia():
    res = F32 / "nnUNet_results"
    arquivos = [p for p in res.rglob("*") if p.is_file()] if res.exists() else []
    assert not arquivos, "a Fase 32 escreveu resultado de treino: %s" % arquivos[:5]


def test_12_nenhum_dataset_novo_alem_dos_dois():
    achados = set()
    for d in (RAIZ / ".clinica-dados").glob("fase*/nnUNet_*/Dataset*"):
        if d.is_dir():
            achados.add(d.name)
    assert achados <= DATASETS_ESPERADOS, "dataset inesperado: %s" % (achados - DATASETS_ESPERADOS)
    assert "Dataset502_VRmedEsofagoV2" in achados, "o dataset da Fase 32 não existe"


# ------------------------------------------------------------------- [PLANO]


def test_13_imagesTr_tem_os_32_de_train_e_nenhum_de_validation():
    if not DS.exists():
        raise Pulado("dataset V2 do nnU-Net ausente")
    imgs = sorted(p.name[:-len("_0000.nii.gz")] for p in (DS / "imagesTr").glob("*_0000.nii.gz"))
    lbls = sorted(p.name[:-len(".nii.gz")] for p in (DS / "labelsTr").glob("*.nii.gz"))
    treino = sorted(e["case_id"] for e in _v2() if e["split"] == "train")
    holdout = {e["case_id"] for e in _v2() if e["split"] == "validation"}
    assert imgs == treino, "imagesTr não é exatamente a partição train"
    assert lbls == treino, "labelsTr não pareia com imagesTr"
    assert not (set(imgs) & holdout), "um caso de VALIDATION entrou em imagesTr"


def test_14_holdout_fora_da_arvore_do_nnunet():
    ho = F32 / "validation_holdout"
    if not ho.exists():
        raise Pulado("holdout ausente")
    n = len(list((ho / "images").glob("*_0000.nii.gz")))
    assert n == 14, "holdout com %d casos" % n
    assert not (DS / "imagesTs").exists(), "não deve haver imagesTs: TEST = 0"


def test_15_dataset_json_carimba_procedencia_e_ontologia():
    if not (DS / "dataset.json").exists():
        raise Pulado("dataset.json ausente")
    d = json.loads((DS / "dataset.json").read_text(encoding="utf-8"))
    assert d["numTraining"] == 32
    assert d["labels"] == {"background": 0, "esophagus": 1}
    assert d["vrmed_dataset_version"] == "VRMED-ESOPHAGUS-POOL46-V2"
    assert d["vrmed_split_rule"] == "VRMED-SPLIT-RULE-V2"
    assert d["vrmed_sha256_manifesto"] == SHA_V2
    # a nota do seed tem de existir: sem ela `vrmed_seed` seria lido como controle de treino
    assert "vrmed_seed_nota" in d, "falta a nota que declara o que o seed NÃO faz"
    assert "12345" in d["vrmed_seed_nota"], "a nota não diz qual é o seed que de fato age"


def test_16_o_plano_veio_do_planner_e_bate_com_o_protocolo():
    p = _plano()["configurations"]["3d_fullres"]
    prot = _protocolo()["planner"]
    assert _plano()["experiment_planner_used"] == prot["experiment_planner"]
    for k in ("patch_size", "batch_size"):
        assert list(p[k]) == list(prot[k]) if isinstance(p[k], list) else p[k] == prot[k], \
            "%s divergiu entre plano e protocolo" % k
    assert [round(x, 6) for x in p["spacing"]] == [round(x, 6) for x in prot["target_spacing"]]
    a = p["architecture"]["arch_kwargs"]
    assert a["n_stages"] == prot["n_stages"]
    assert a["features_per_stage"] == prot["features_per_stage"]
    assert a["kernel_sizes"] == prot["kernel_sizes"]
    assert a["strides"] == prot["strides"]


def test_17_o_plano_em_disco_e_o_que_o_protocolo_carimbou():
    """sha256 do arquivo. Se o plano for reeditado à mão, este teste cai."""
    prot = _protocolo()
    for rel, chave in (("nnUNetPlans.json", "plans_sha256"),
                       ("dataset_fingerprint.json", "fingerprint_sha256"),
                       ("splits_final.json", "splits_sha256")):
        p = PRE / rel
        if not p.exists():
            raise Pulado("%s ausente" % rel)
        assert hashlib.sha256(p.read_bytes()).hexdigest() == prot["planner"][chave], \
            "%s mudou depois de congelado" % rel


def test_18_cinco_folds_validos_e_so_com_casos_de_train():
    p = PRE / "splits_final.json"
    if not p.exists():
        raise Pulado("splits_final.json ausente")
    splits = json.loads(p.read_text(encoding="utf-8"))
    assert len(splits) == 5
    r = pl.auditar_folds(splits)
    assert r["ok"], r["problemas"]
    assert r["n_casos_cobertos"] == 32


def test_19_os_folds_sao_os_que_a_funcao_do_framework_produz():
    """Reimplementar o split seria fazer dele um artefato nosso. Ele é do framework."""
    p = PRE / "splits_final.json"
    if not p.exists():
        raise Pulado("splits_final.json ausente")
    esperado = pl.gerar_folds(escrever=False)["splits"]
    assert json.loads(p.read_text(encoding="utf-8")) == esperado, \
        "o splits_final.json em disco não é o que generate_crossval_split(seed=12345) dá"


def test_20_a_fingerprint_viu_apenas_os_32_de_train():
    f = PRE / "dataset_fingerprint.json"
    if not f.exists():
        raise Pulado("fingerprint ausente")
    d = json.loads(f.read_text(encoding="utf-8"))
    assert len(d["shapes_after_crop"]) == 32, \
        "a fingerprint viu %d casos, não 32" % len(d["shapes_after_crop"])
    assert len(d["spacings"]) == 32


def test_21_os_6_do_holdout_da_v1_seguem_no_holdout_da_v2():
    """O instrumento de comparabilidade da Fase 33. Se cair, a comparação com o 26B morre."""
    v1 = {e["case_id"] for e in _v1() if e["split"] == "validation"}
    v2v = {e["case_id"] for e in _v2() if e["split"] == "validation"}
    v2t = {e["case_id"] for e in _v2() if e["split"] == "train"}
    assert len(v1) == 6 and v1 <= v2v, "os 6 do holdout da V1 saíram do holdout da V2"
    assert not (v1 & v2t), "um caso do holdout da V1 foi parar no TRAIN da V2"


# --------------------------------------------------------------- [PROTOCOLO]


def test_22_o_protocolo_fixa_todos_os_campos_exigidos():
    p = _protocolo()
    for k in ("fase", "dataset", "train", "validation", "test", "planner", "folds",
              "trainer", "epochs", "checkpoint_primary", "checkpoint_secondary",
              "decision", "protocol_locked"):
        assert k in p, "falta o campo %s" % k
    assert (p["train"], p["validation"], p["test"]) == (32, 14, 0)
    assert p["protocol_locked"] is True
    for k in ("learning_rate", "optimizer", "scheduler", "loss", "deep_supervision",
              "seed_behavior", "stopping", "hardware", "expected_runtime_h"):
        assert k in p["treinamento"], "falta %s no bloco de treinamento" % k


def test_23_checkpoint_primary_e_secondary_sao_os_da_fase_26b():
    p = _protocolo()
    assert p["checkpoint_primary"] == "checkpoint_final"
    assert p["checkpoint_secondary"] == "checkpoint_best"
    assert p["treinamento"]["stopping"].lower().startswith("sem"), \
        "o protocolo tem de declarar que não há parada antecipada"


def test_24_o_protocolo_nao_promete_seed_que_o_framework_nao_tem():
    s = _protocolo()["treinamento"]["seed_behavior"]
    assert "12345" in s, "o seed real do split não está declarado"
    assert "cudnn" in s.lower(), "o comportamento não determinístico do cuDNN não está declarado"


def test_25_o_preregistro_anterior_nao_foi_editado():
    """Nenhuma mudança silenciosa: V1 e V2 têm de estar byte a byte como estavam."""
    if not ANTES.exists():
        raise Pulado("impressão digital ausente")
    a = json.loads(ANTES.read_text(encoding="utf-8"))["alvos"]
    for rotulo, caminho in (("v1_prerregistro", PRE_V1), ("prerregistro_v2", PRE_V2)):
        assert man.sha256_arquivo(caminho) == a[rotulo]["sha256"], \
            "%s foi editado nesta fase" % caminho.name


def test_26_se_houve_emenda_ela_e_um_arquivo_novo_e_esta_declarada():
    p = _protocolo()
    v3 = RAIZ / "docs" / "BASELINE-ESOPHAGUS-VRMED-V3.md"
    if p.get("preregistro_emendado"):
        assert v3.exists(), "o protocolo diz que emendou, mas não há V3"
        t = v3.read_text(encoding="utf-8")
        assert "LCTSC" in t, "a V3 não trata do ponto que a motivou"
        assert "V1" in t and "V2" in t, "a V3 não declara o que preserva"
    else:
        assert not v3.exists(), "existe uma V3 que o protocolo não declara"


def test_27_o_protocolo_nao_usa_linguagem_proibida():
    proibidas = ("variabilidade humana", "melhor que humano", "nível humano",
                 "nivel humano", "validado clinicamente", "paciente")
    alvos = [PROTOCOLO, RAIZ / "docs" / "FASE32-PROTOCOLO-TREINO-V2.md",
             RAIZ / "docs" / "RELATORIO-FASE32-REPLANEJAMENTO-TREINO.md",
             RAIZ / "docs" / "BASELINE-ESOPHAGUS-VRMED-V3.md"]
    achados = []
    for p in alvos:
        if not p.exists():
            continue
        linhas = p.read_text(encoding="utf-8").lower().splitlines()
        for i, linha in enumerate(linhas, 1):
            for f in proibidas:
                if f in linha:
                    achados.append("%s:%d %r" % (p.name, i, f))
            # Negar a frase é permitido e necessário; AFIRMÁ-LA é que não. A regra é de
            # companhia: "LCTSC" e "independente" juntos só passam se houver negação por
            # perto. A janela é de duas linhas porque o texto é quebrado em 90 colunas e a
            # negação cai na linha seguinte com frequência.
            if "independente" in linha and "lctsc" in linha:
                janela = linha + " " + (linhas[i] if i < len(linhas) else "")
                if not any(n in janela for n in ("não", "nao", "nunca", "jamais", "sem ",
                                                 "proibid", "vedado")):
                    achados.append("%s:%d chama o LCTSC de independente" % (p.name, i))
    assert not achados, achados


def test_28_a_regra_de_fontes_saiu_da_prosa_e_virou_teste():
    """Quatro vezes uma regra que só existia em prosa caiu. Esta não pode ser a quinta.

    A lista vem do protocolo vigente, não daqui: se a regra mudar, muda num lugar só, e
    este teste passa a cobrar a regra nova.
    """
    p = _protocolo()
    permitidas = set(p["fontes_permitidas_no_pool"])
    proibidas_test = set(p["fontes_proibidas_como_test"])
    assert permitidas and proibidas_test, "as listas de fontes não estão no protocolo"

    for rotulo, ent in (("V1", _v1()), ("V2", _v2())):
        fora = sorted({e["source_dataset"] for e in ent} - permitidas)
        assert not fora, "%s tem fonte fora da lista permitida: %s" % (rotulo, fora)
        no_test = sorted({e["source_dataset"] for e in ent if e["split"] == "test"}
                         & proibidas_test)
        assert not no_test, "%s tem fonte proibida na partição test: %s" % (rotulo, no_test)

    # a regra "fonte usada vira proibida como TEST" tem de valer para o que já foi usado
    if p.get("regra_fonte_usada_vira_proibida_como_test"):
        usadas = {e["source_dataset"] for e in _v2() if e["split"] in ("train", "validation")}
        faltando = sorted(usadas - proibidas_test)
        assert not faltando, ("fontes já usadas em train/validation que o protocolo não "
                              "declarou proibidas como TEST: %s" % faltando)


def test_29_o_preregistro_vigente_e_o_que_o_protocolo_carimbou():
    p = _protocolo()
    v3 = RAIZ / p["preregistro_vigente"]
    assert v3.exists(), "o pré-registro vigente não existe"
    assert man.sha256_arquivo(v3) == p["preregistro_vigente_sha256"], \
        "o pré-registro vigente foi editado depois de congelado no protocolo"


def test_30_o_protocolo_nao_chama_o_artefato_futuro_de_baseline():
    """O nome importa: a Fase 26A separou 'experimento' de 'baseline' e a separação vale."""
    p = _protocolo()
    assert "MODELO INTERNO EXPERIMENTAL V2" in " ".join(p["proibido"]), \
        "o protocolo não fixa o nome do artefato"
    d = p["decision"].lower()
    assert "nao e o baseline" in d or "não é o baseline" in d, \
        "a decisão não declara que o resultado não é o baseline"
    assert "pendente" in d, "a decisão não declara a dívida do baseline canônico"


def main() -> int:
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    falhas, pulados = [], []
    for nome, f in testes:
        try:
            f()
            print("  ok     %s" % nome)
        except Pulado as p:
            pulados.append(nome)
            print("  PULADO %s: %s" % (nome, p))
        except Exception as exc:  # noqa: BLE001
            falhas.append(nome)
            print("  FALHA  %s: %s" % (nome, exc))
    print("\n%d/%d passaram | %d pulados | %d falharam"
          % (len(testes) - len(falhas) - len(pulados), len(testes), len(pulados), len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
