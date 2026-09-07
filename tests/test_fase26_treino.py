"""Os controles anti-vazamento do treino da Fase 26 continuam valendo — ou este arquivo cai.

Ele nao testa se o modelo e bom. Testa se o modelo foi treinado no que dizemos que foi.

Cai se alguem:
  - preencher o TEST;
  - colocar um caso de VALIDATION dentro de imagesTr;
  - alterar o manifesto congelado ou o snapshot;
  - alterar a composicao do split;
  - trocar os folds por outros que nao cubram exatamente os 10 de TRAIN;
  - tirar o carimbo da ontologia do dataset.json.

Os artefatos do nnU-Net vivem em `.clinica-dados/` (fora do git). Quando eles nao existem,
os testes que dependem deles sao PULADOS de forma explicita e contada — nunca silenciosa,
porque "pulou" e "passou" nao sao a mesma coisa.

  python tests/test_fase26_treino.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
SHA_CONGELADO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"

BASE = RAIZ / ".clinica-dados" / "fase26"
DS = BASE / "nnUNet_raw" / "Dataset501_VRmedEsofago"
IMAGES_TR = DS / "imagesTr"
DATASET_JSON = DS / "dataset.json"
SPLITS = BASE / "nnUNet_preprocessed" / "Dataset501_VRmedEsofago" / "splits_final.json"
# Copia versionada: sobrevive mesmo quando .clinica-dados e limpo
SPLITS_COPIA = RAIZ / "docs" / "overnight" / "phase26" / "splits_final.json"

N_TRAIN, N_VALIDATION, N_TEST = 10, 6, 0


class Pulado(Exception):
    """O artefato nao existe nesta maquina. Nao e falha, e ausencia — e e contada."""


def _ent():
    return man.carregar(MANIFESTO)


def _ids(split):
    return sorted(e["case_id"] for e in _ent() if e["split"] == split)


def _ids_em_imagesTr():
    if not IMAGES_TR.exists():
        raise Pulado("imagesTr ausente (%s)" % IMAGES_TR)
    return sorted(p.name.replace("_0000.nii.gz", "")
                  for p in IMAGES_TR.glob("*_0000.nii.gz"))


def _splits():
    p = SPLITS if SPLITS.exists() else SPLITS_COPIA
    if not p.exists():
        raise Pulado("splits_final.json ausente")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------- o congelamento nao se mexeu


def test_01_manifesto_bate_com_o_snapshot():
    ent = _ent()
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    r = man.verificar_congelamento(ent, snap)
    assert r["intacto"], "manifesto divergiu do snapshot: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_CONGELADO, "sha256 do manifesto mudou"


def test_02_a_composicao_do_split_e_a_congelada():
    por = {p: sum(1 for e in _ent() if e["split"] == p) for p in man.PARTICOES}
    assert por == {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST}, por


def test_03_o_test_continua_vazio():
    assert [e for e in _ent() if e["split"] == "test"] == [], "apareceu caso em TEST"


def test_04_o_treino_nao_alcanca_test_nem_validation():
    """A trava que o dataset da Fase 26 usa como unica porta de entrada."""
    ent = _ent()
    for particao in ("test", "validation"):
        try:
            man.carregar_particao(ent, particao, "treino")
        except man.AcessoIndevido:
            continue
        raise AssertionError("o contexto de treino alcancou a particao %r" % particao)


def test_05_controle_negativo_o_treino_ainda_le_train():
    """Sem isto, uma tabela que proibisse tudo passaria no teste 04 sem provar nada."""
    assert len(man.carregar_particao(_ent(), "train", "treino")) == N_TRAIN


# --------------------------------------- o que foi realmente para dentro do treino


def test_06_imagesTr_contem_exatamente_os_10_de_train():
    try:
        em_disco = _ids_em_imagesTr()
    except Pulado as p:
        raise Pulado(p)
    assert em_disco == _ids("train"), (
        "imagesTr nao e a particao train.\n  em disco: %s\n  esperado: %s"
        % (em_disco, _ids("train")))


def test_07_nenhum_caso_de_validation_entrou_em_imagesTr():
    """O teste que o usuario pediu por nome. Falha se a protecao for removida."""
    try:
        em_disco = set(_ids_em_imagesTr())
    except Pulado as p:
        raise Pulado(p)
    invasores = sorted(em_disco & set(_ids("validation")))
    assert not invasores, "caso de VALIDATION dentro de imagesTr: %s" % invasores


def test_08_nenhum_caso_externo_entrou():
    try:
        em_disco = set(_ids_em_imagesTr())
    except Pulado as p:
        raise Pulado(p)
    conhecidos = {e["case_id"] for e in _ent()}
    estranhos = sorted(em_disco - conhecidos)
    assert not estranhos, "caso fora do manifesto congelado em imagesTr: %s" % estranhos


def test_09_nenhum_caso_duplicado_em_imagesTr():
    try:
        _ids_em_imagesTr()
    except Pulado as p:
        raise Pulado(p)
    nomes = [p.name for p in IMAGES_TR.glob("*_0000.nii.gz")]
    assert len(nomes) == len(set(nomes)) == N_TRAIN, "imagesTr tem %d arquivos" % len(nomes)


# ------------------------------------------------------------------ os folds


def test_10_os_folds_cobrem_exatamente_os_10_de_train():
    try:
        folds = _splits()
    except Pulado as p:
        raise Pulado(p)
    assert len(folds) == 5, "esperava 5 folds, ha %d" % len(folds)
    treino = set(_ids("train"))
    val6 = set(_ids("validation"))
    for i, f in enumerate(folds):
        universo = set(f["train"]) | set(f["val"])
        assert universo == treino, "fold %d nao cobre a particao train: %s" % (i, universo ^ treino)
        assert not (universo & val6), "fold %d contem caso de VALIDATION" % i
        assert not (set(f["train"]) & set(f["val"])), "fold %d tem caso nos dois lados" % i


def test_11_cada_caso_de_train_valida_em_exatamente_um_fold():
    try:
        folds = _splits()
    except Pulado as p:
        raise Pulado(p)
    contagem = {c: 0 for c in _ids("train")}
    for f in folds:
        for c in f["val"]:
            contagem[c] += 1
    ruins = {c: n for c, n in contagem.items() if n != 1}
    assert not ruins, "casos que nao validam em exatamente um fold: %s" % ruins


# ------------------------------------------------------------ o dataset.json


def test_12_dataset_json_carimba_a_ontologia_e_o_manifesto():
    if not DATASET_JSON.exists():
        raise Pulado("dataset.json ausente")
    d = json.loads(DATASET_JSON.read_text(encoding="utf-8"))
    assert d["vrmed_ontology"] == onto.VERSAO, "dataset.json aponta outra ontologia"
    assert d["vrmed_sha256_manifesto"] == SHA_CONGELADO, "dataset.json aponta outro manifesto"
    assert d["numTraining"] == N_TRAIN, "numTraining != %d" % N_TRAIN
    assert d["labels"] == {"background": 0, "esophagus": 1}, "rotulos divergiram"


def main() -> int:
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    falhas, pulados = [], []
    for nome, f in testes:
        try:
            f()
            print("  ok    %s" % nome)
        except Pulado as p:
            pulados.append((nome, p))
            print("  PULADO %s: %s" % (nome, p))
        except Exception as exc:  # noqa: BLE001
            falhas.append((nome, exc))
            print("  FALHA %s: %s" % (nome, exc))
    print("\n%d/%d passaram | %d pulados (artefato ausente) | %d falharam"
          % (len(testes) - len(falhas) - len(pulados), len(testes), len(pulados), len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
