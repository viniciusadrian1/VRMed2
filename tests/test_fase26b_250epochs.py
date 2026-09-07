"""Fase 26B — o experimento de 250 epocas e o que dizemos que e, ou este arquivo cai.

DUAS CLASSES DE TESTE, E ELAS NAO SE MISTURAM

  [PRE]  valem antes do treino. Se falharem, o treino nao deveria ter comecado.
  [POS]  dependem de artefato que so existe DEPOIS de um fold terminar.

Um teste [POS] cujo artefato ainda nao existe e reportado como **PENDENTE**, nunca como
PASS. "Ainda nao rodou" e "passou" sao coisas diferentes, e confundi-las e como um
relatorio de fase mente sem que ninguem perceba.

  python tests/test_fase26b_250epochs.py
"""

from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
SHA_CONGELADO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"

DS = "Dataset501_VRmedEsofago"
BASE_26B = RAIZ / ".clinica-dados" / "fase26b"
BASE_26 = RAIZ / ".clinica-dados" / "fase26"
RAW_26B = BASE_26B / "nnUNet_raw" / DS
PRE_26B = BASE_26B / "nnUNet_preprocessed" / DS
RES_26B = BASE_26B / "nnUNet_results" / DS / "nnUNetTrainer_250epochs__nnUNetPlans__3d_fullres"
RES_26 = BASE_26 / "nnUNet_results" / DS / "nnUNetTrainer__nnUNetPlans__3d_fullres"

TRAINER = "nnUNetTrainer_250epochs"
EPOCAS = 250
N_TRAIN, N_VALIDATION = 10, 6
TERMOS_DE_PARADA = ("early_stop", "earlystop", "EarlyStopping", "patience",
                    "no_improvement", "should_stop", "stop_training")


class Pendente(Exception):
    """O artefato ainda nao existe. NAO e passar."""


class Pulado(Exception):
    """A arvore da 26B nao existe nesta maquina."""


def _ent():
    return man.carregar(MANIFESTO)


def _ids(split):
    return sorted(e["case_id"] for e in _ent() if e["split"] == split)


def _folds_no_disco():
    return sorted(p for p in RES_26B.glob("fold_*") if p.is_dir()) if RES_26B.exists() else []


# ------------------------------------------------------------------ [PRE]


def test_PRE_01_trainer_correto():
    from nnunetv2.utilities.find_class_by_name import recursive_find_python_class
    import nnunetv2
    cls = recursive_find_python_class(
        str(Path(nnunetv2.__file__).parent / "training" / "nnUNetTrainer"),
        TRAINER, "nnunetv2.training.nnUNetTrainer")
    assert cls is not None and cls.__name__ == TRAINER, "trainer nao resolveu para %s" % TRAINER


def test_PRE_02_250_epocas():
    from nnunetv2.utilities.find_class_by_name import recursive_find_python_class
    import nnunetv2
    cls = recursive_find_python_class(
        str(Path(nnunetv2.__file__).parent / "training" / "nnUNetTrainer"),
        TRAINER, "nnunetv2.training.nnUNetTrainer")
    src = inspect.getsource(cls)
    m = re.search(r"self\.num_epochs\s*=\s*(\d+)", src)
    assert m and int(m.group(1)) == EPOCAS, "num_epochs != %d" % EPOCAS
    # e SO num_epochs: se a variante mexer em outra coisa, deixa de ser o mesmo experimento
    assert re.findall(r"self\.(\w+)\s*=", src) == ["num_epochs"], (
        "a variante altera mais que num_epochs")


def test_PRE_03_saida_separada_da_fase26():
    assert RES_26B.resolve() != RES_26.resolve(), "26B escreveria por cima da 26"
    assert "nnUNetTrainer_250epochs__" in RES_26B.name, "a pasta nao carrega o trainer no nome"


def test_PRE_04_dataset_e_a_particao_train():
    if not RAW_26B.exists():
        raise Pulado("arvore da 26B ausente")
    imgs = sorted(p.name.replace("_0000.nii.gz", "")
                  for p in (RAW_26B / "imagesTr").glob("*_0000.nii.gz"))
    lbls = sorted(p.name.replace(".nii.gz", "") for p in (RAW_26B / "labelsTr").glob("*.nii.gz"))
    assert imgs == _ids("train") == lbls, "imagesTr/labelsTr nao sao a particao train"


def test_PRE_05_holdout_ausente_de_tudo():
    if not RAW_26B.exists():
        raise Pulado("arvore da 26B ausente")
    hold = set(_ids("validation"))
    for d in (RAW_26B / "imagesTr", RAW_26B / "labelsTr",
              PRE_26B / "nnUNetPlans_3d_fullres", PRE_26B / "gt_segmentations"):
        if not d.exists():
            continue
        nomes = [p.name for p in d.iterdir()]
        inv = sorted(h for h in hold if any(h in n for n in nomes))
        assert not inv, "caso de holdout em %s: %s" % (d.name, inv)


def test_PRE_06_test_vazio_e_inalcancavel():
    ent = _ent()
    assert [e for e in ent if e["split"] == "test"] == [], "apareceu caso em TEST"
    for particao in ("test", "validation"):
        try:
            man.carregar_particao(ent, particao, "treino")
        except man.AcessoIndevido:
            continue
        raise AssertionError("o contexto de treino alcancou %r" % particao)
    assert len(man.carregar_particao(ent, "train", "treino")) == N_TRAIN  # controle negativo


def test_PRE_07_folds_corretos_e_iguais_aos_da_fase26():
    p = PRE_26B / "splits_final.json"
    if not p.exists():
        raise Pulado("splits_final.json da 26B ausente")
    folds = json.loads(p.read_text(encoding="utf-8"))
    treino, hold = set(_ids("train")), set(_ids("validation"))
    assert len(folds) == 5, "esperava 5 folds, ha %d" % len(folds)
    universo = set()
    for i, f in enumerate(folds):
        u = set(f["train"]) | set(f["val"])
        assert not (u & hold), "fold %d contem holdout" % i
        assert not (set(f["train"]) & set(f["val"])), "fold %d tem caso nos dois lados" % i
        universo |= u
    assert universo == treino, "os folds nao cobrem exatamente a particao train"
    # e sao LITERALMENTE os mesmos da Fase 26 — nao apenas equivalentes
    p26 = BASE_26 / "nnUNet_preprocessed" / DS / "splits_final.json"
    if p26.exists():
        assert p.read_bytes() == p26.read_bytes(), (
            "os folds da 26B divergem dos da 26 — o experimento deixaria de ser comparavel")


def test_PRE_08_manifesto_intacto():
    r = man.verificar_congelamento(_ent(), json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    assert r["intacto"] and r["sha256_atual"] == SHA_CONGELADO, "manifesto mudou: %s" % r["mudancas"]


def test_PRE_09_snapshot_intacto():
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snap["sha256_manifesto"] == SHA_CONGELADO
    assert snap["por_split"] == {"train": N_TRAIN, "validation": N_VALIDATION, "test": 0}


def test_PRE_10_nenhuma_heranca_de_checkpoint_do_experimento_1000():
    """A 26B nao pode conter peso vindo da execucao de 1000 epocas."""
    if not BASE_26B.exists():
        raise Pulado("arvore da 26B ausente")
    for pth in BASE_26B.rglob("*.pth"):
        assert "nnUNetTrainer_250epochs__" in str(pth), (
            "checkpoint fora da pasta do trainer de 250 epocas: %s" % pth)
    # e a execucao de 1000 continua intacta, no lugar dela
    if RES_26.exists():
        assert (RES_26 / "fold_0").exists(), "o run parcial de 1000 epocas sumiu"


def test_PRE_12_nenhuma_rotina_de_parada_customizada():
    """Nem no pacote instalado, nem escrita por nos."""
    import nnunetv2
    pkg = Path(nnunetv2.__file__).parent
    achados = []
    for py in pkg.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        txt = py.read_text(encoding="utf-8", errors="replace")
        achados += ["%s:%s" % (py.relative_to(pkg), t) for t in TERMOS_DE_PARADA if t in txt]
    assert not achados, "parada antecipada no pacote: %s" % achados[:5]
    nossos = [p for p in (RAIZ / "scripts").rglob("*.py")
              if "__pycache__" not in str(p)
              and re.search(r"class\s+\w*Trainer\w*\s*\(",
                            p.read_text(encoding="utf-8", errors="replace"))]
    assert not nossos, "trainer customizado no repositorio: %s" % nossos


# ------------------------------------------------------------------ [POS]


def test_POS_11_checkpoints_presentes_apos_o_treino():
    """Exige fold concluido. PENDENTE enquanto o treino nao terminar."""
    folds = _folds_no_disco()
    if not folds:
        raise Pendente("nenhum fold iniciado ainda em %s" % RES_26B)
    concluidos, faltando = [], []
    for f in folds:
        tem_final = (f / "checkpoint_final.pth").exists()
        tem_best = (f / "checkpoint_best.pth").exists()
        if tem_final and tem_best:
            concluidos.append(f.name)
        else:
            faltando.append("%s(final=%s,best=%s)" % (f.name, tem_final, tem_best))
    if len(concluidos) < 5:
        raise Pendente("%d de 5 folds com final+best; em andamento: %s"
                       % (len(concluidos), faltando))
    assert len(concluidos) == 5


def test_POS_13_todos_os_folds_rodaram_250_epocas():
    """Nenhum fold pode ter parado antes: 250 e o orcamento completo."""
    folds = _folds_no_disco()
    if not folds:
        raise Pendente("nenhum fold iniciado ainda")
    problemas, ok = [], 0
    for f in folds:
        logs = sorted(f.glob("training_log_*.txt"))
        if not logs:
            problemas.append("%s sem log" % f.name)
            continue
        txt = "".join(p.read_text(encoding="utf-8", errors="replace") for p in logs)
        n = len(re.findall(r"Epoch time: [0-9.]+ s", txt))
        if not (f / "checkpoint_final.pth").exists():
            problemas.append("%s em andamento (%d epocas)" % (f.name, n))
        elif n != EPOCAS:
            raise AssertionError("%s concluiu com %d epocas, esperado %d" % (f.name, n, EPOCAS))
        else:
            ok += 1
    if ok < 5:
        raise Pendente("%d de 5 folds concluiram as %d epocas; %s" % (ok, EPOCAS, problemas))
    assert ok == 5


def main() -> int:
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    falhas, pendentes, pulados = [], [], []
    for nome, f in testes:
        marca = "PRE" if "_PRE_" in nome else "POS"
        try:
            f()
            print("  ok       [%s] %s" % (marca, nome))
        except Pendente as p:
            pendentes.append(nome)
            print("  PENDENTE [%s] %s: %s" % (marca, nome, p))
        except Pulado as p:
            pulados.append(nome)
            print("  PULADO   [%s] %s: %s" % (marca, nome, p))
        except Exception as exc:  # noqa: BLE001
            falhas.append(nome)
            print("  FALHA    [%s] %s: %s" % (marca, nome, exc))
    passou = len(testes) - len(falhas) - len(pendentes) - len(pulados)
    print("\n%d/%d passaram | %d PENDENTES (aguardam treino) | %d pulados | %d falharam"
          % (passou, len(testes), len(pendentes), len(pulados), len(falhas)))
    if pendentes:
        print("PENDENTE nao e PASS: %s" % ", ".join(pendentes))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
