"""A regra de parada do baseline e a que esta documentada — ou este arquivo cai.

Metade destes testes NAO olha o VRmed: olha o `nnunetv2` INSTALADO. Isso e deliberado.
A Fase 26A concluiu coisas sobre o comportamento do framework (nao ha early stopping; o
laco e fixo; o melhor checkpoint sai de uma EMA da validacao interna). Se alguem atualizar
o pacote, trocar o trainer ou instalar uma variante com parada propria, essas conclusoes
deixam de valer em silencio — e o relatorio da fase passa a descrever um software que nao
esta mais ali. Estes testes sao o alarme.

A outra metade prova, em disco, que os 6 casos do holdout congelado nao alcancam nenhuma
decisao de treino.

  python tests/test_fase26a_regra_de_parada.py
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

BASE = RAIZ / ".clinica-dados" / "fase26"
RAW = BASE / "nnUNet_raw" / "Dataset501_VRmedEsofago"
PRE = BASE / "nnUNet_preprocessed" / "Dataset501_VRmedEsofago"
SPLITS_COPIA = RAIZ / "docs" / "overnight" / "phase26" / "splits_final.json"

# Termos que denunciariam um mecanismo de parada antecipada. Se QUALQUER um aparecer no
# pacote instalado, a conclusao da Fase 26A precisa ser reexaminada.
TERMOS_DE_PARADA = ("early_stop", "earlystop", "EarlyStopping", "patience",
                    "no_improvement", "should_stop", "stop_training")

N_TRAIN, N_VALIDATION = 10, 6


class Pulado(Exception):
    """Artefato ausente nesta maquina. Nao e falha, e ausencia — e e contada."""


def _ent():
    return man.carregar(MANIFESTO)


def _ids(split):
    return sorted(e["case_id"] for e in _ent() if e["split"] == split)


def _trainer():
    try:
        from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
        return nnUNetTrainer
    except ImportError as exc:
        raise Pulado("nnunetv2 nao importavel: %s" % exc)


# ------------------------------------------------- o framework realmente instalado


def test_01_o_pacote_instalado_nao_tem_early_stopping():
    """A conclusao central da Fase 26A. Se cair, a fase precisa ser refeita."""
    try:
        import nnunetv2
    except ImportError as exc:
        raise Pulado("nnunetv2 ausente: %s" % exc)
    raiz = Path(nnunetv2.__file__).parent
    achados = []
    for py in raiz.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        txt = py.read_text(encoding="utf-8", errors="replace")
        for termo in TERMOS_DE_PARADA:
            if termo in txt:
                achados.append("%s: %s" % (py.relative_to(raiz), termo))
    assert not achados, (
        "apareceu mecanismo de parada antecipada no nnunetv2 instalado — a Fase 26A "
        "concluiu que nao havia nenhum:\n  " + "\n  ".join(achados[:10]))


def test_02_o_laco_de_treino_e_fixo_sobre_num_epochs():
    """Sem `break`, sem saida antecipada: o treino roda o orcamento inteiro."""
    src = inspect.getsource(_trainer().run_training)
    assert "for epoch in range(self.current_epoch, self.num_epochs)" in src, (
        "o laco de treino mudou de forma: %s" % src[:400])
    corpo = src.split("for epoch in range(self.current_epoch, self.num_epochs)", 1)[1]
    assert "break" not in corpo, "apareceu um `break` no laco de treino"


def test_03_o_orcamento_default_e_1000_epocas():
    src = inspect.getsource(_trainer().__init__)
    m = re.search(r"self\.num_epochs\s*=\s*(\d+)", src)
    assert m, "num_epochs nao encontrado no __init__ do trainer"
    assert m.group(1) == "1000", "o default do trainer deixou de ser 1000: %s" % m.group(1)
    m2 = re.search(r"self\.num_iterations_per_epoch\s*=\s*(\d+)", src)
    assert m2 and m2.group(1) == "250", "iteracoes por epoca mudaram"


def test_04_o_melhor_checkpoint_sai_de_uma_ema_da_validacao_interna():
    """O mecanismo que JA faz selecao de modelo — e a razao de early stopping ser dispensavel."""
    src = inspect.getsource(_trainer().on_epoch_end)
    assert "ema_fg_dice" in src, "checkpoint_best deixou de usar ema_fg_dice"
    assert "checkpoint_best.pth" in src, "checkpoint_best.pth nao e mais escrito em on_epoch_end"
    assert "self._best_ema" in src, "a comparacao com _best_ema sumiu"


def test_05_a_ema_e_deterministica_e_com_coeficiente_fixo():
    """Nenhum sorteio, nenhum parametro escondido: 0.9 do anterior + 0.1 do novo."""
    # A EMA vive no MetaLogger, que e quem intercepta `mean_fg_dice`. O nome da classe
    # e verificado aqui de proposito: se a instalacao renomear, o teste avisa em vez de
    # passar por engano sobre outra classe.
    from nnunetv2.training.logging.nnunet_logger import MetaLogger
    src = inspect.getsource(MetaLogger.log)
    assert "ema_fg_dice" in src and "0.9" in src and "0.1" in src, (
        "a formula da EMA mudou: %s" % src[-500:])
    assert "random" not in src.lower(), "apareceu aleatoriedade no logger da EMA"


def test_06_nenhum_criterio_de_parada_aleatorio():
    """Um criterio de parada que sorteia nao e reproduzivel. Nao pode existir."""
    for metodo in (_trainer().run_training, _trainer().on_epoch_end):
        src = inspect.getsource(metodo)
        for proibido in ("random.", "np.random", "torch.rand", "shuffle("):
            assert proibido not in src, (
                "%s usa %s — parada/checkpoint nao pode depender de sorteio"
                % (metodo.__name__, proibido))


def test_07_a_variante_de_epocas_muda_somente_num_epochs():
    """Se ela mexer em outra coisa, um orcamento menor deixa de ser comparavel."""
    try:
        from nnunetv2.training.nnUNetTrainer.variants.training_length import (
            nnUNetTrainer_Xepochs as mod)
    except ImportError as exc:
        raise Pulado("variantes de duracao ausentes: %s" % exc)
    cls = getattr(mod, "nnUNetTrainer_250epochs", None)
    assert cls is not None, "nnUNetTrainer_250epochs nao existe nesta instalacao"
    src = inspect.getsource(cls)
    atribuicoes = re.findall(r"self\.(\w+)\s*=", src)
    assert atribuicoes == ["num_epochs"], (
        "a variante mexe em mais que num_epochs: %s" % atribuicoes)


def test_08_o_agendador_de_lr_recoze_dentro_do_orcamento():
    """Orcamento menor tem de ser run RECOZIDO, nao run de 1000 truncado."""
    src = inspect.getsource(_trainer().configure_optimizers)
    assert "PolyLRScheduler" in src and "self.num_epochs" in src, (
        "o agendador deixou de ser construido sobre num_epochs: %s" % src)


# --------------------------------------- os 6 do holdout nao alcancam decisao alguma


def test_09_o_holdout_nao_esta_em_imagesTr_nem_labelsTr():
    if not RAW.exists():
        raise Pulado("nnUNet_raw ausente")
    hold = set(_ids("validation"))
    for sub in ("imagesTr", "labelsTr"):
        nomes = [p.name for p in (RAW / sub).iterdir()]
        invasores = sorted(h for h in hold if any(h in n for n in nomes))
        assert not invasores, "caso do holdout em %s: %s" % (sub, invasores)
        assert len(nomes) == N_TRAIN, "%s tem %d arquivos, esperado %d" % (sub, len(nomes), N_TRAIN)


def test_10_o_holdout_nao_esta_no_preprocessado():
    """imagesTr limpo nao basta: o sinal de validacao interna le o PRE-PROCESSADO."""
    if not PRE.exists():
        raise Pulado("nnUNet_preprocessed ausente")
    hold = set(_ids("validation"))
    for sub in ("nnUNetPlans_3d_fullres", "gt_segmentations"):
        d = PRE / sub
        if not d.exists():
            continue
        nomes = [p.name for p in d.iterdir()]
        invasores = sorted(h for h in hold if any(h in n for n in nomes))
        assert not invasores, "caso do holdout em %s: %s" % (sub, invasores)


def test_11_nenhum_fold_contem_caso_do_holdout():
    p = (PRE / "splits_final.json") if (PRE / "splits_final.json").exists() else SPLITS_COPIA
    if not p.exists():
        raise Pulado("splits_final.json ausente")
    folds = json.loads(p.read_text(encoding="utf-8"))
    hold, treino = set(_ids("validation")), set(_ids("train"))
    universo = set()
    for i, f in enumerate(folds):
        u = set(f["train"]) | set(f["val"])
        assert not (u & hold), "fold %d contem caso do holdout: %s" % (i, sorted(u & hold))
        universo |= u
    assert universo == treino, "os folds nao cobrem exatamente a particao train"


def test_12_o_sinal_de_checkpoint_so_pode_vir_do_fold_interno():
    """`ema_fg_dice` vem de mean_fg_dice, que vem do dataloader de validacao do fold.

    A prova em disco e a dos testes 9-11: se o holdout nao existe em lugar nenhum da
    arvore que o dataloader enxerga, nenhum sinal derivado dele pode existir.
    """
    if not PRE.exists():
        raise Pulado("nnUNet_preprocessed ausente")
    src = inspect.getsource(_trainer().on_validation_epoch_end)
    assert "mean_fg_dice" in src, "on_validation_epoch_end deixou de logar mean_fg_dice"
    ids_pre = {p.name.split(".")[0] for p in (PRE / "gt_segmentations").glob("*.nii.gz")}
    assert ids_pre == set(_ids("train")), (
        "o universo pre-processado deixou de ser exatamente a particao train: %s"
        % sorted(ids_pre ^ set(_ids("train"))))


# ------------------------------------------------- o congelamento nao se mexeu


def test_13_manifesto_e_snapshot_inalterados():
    ent = _ent()
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    r = man.verificar_congelamento(ent, snap)
    assert r["intacto"], "manifesto divergiu do snapshot: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_CONGELADO, "sha256 do manifesto mudou"


def test_14_split_inalterado_e_test_inacessivel():
    ent = _ent()
    por = {p: sum(1 for e in ent if e["split"] == p) for p in man.PARTICOES}
    assert por == {"train": N_TRAIN, "validation": N_VALIDATION, "test": 0}, por
    for particao in ("test", "validation"):
        try:
            man.carregar_particao(ent, particao, "treino")
        except man.AcessoIndevido:
            continue
        raise AssertionError("o contexto de treino alcancou %r" % particao)
    # controle negativo: o guarda nao proibe tudo
    assert len(man.carregar_particao(ent, "train", "treino")) == N_TRAIN


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
