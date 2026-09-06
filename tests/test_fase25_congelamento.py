"""O congelamento da Fase 25 continua valendo — ou este arquivo cai.

Nao e um teste do codigo da Fase 25: e um teste do ARTEFATO congelado. Ele le o
manifesto e o snapshot que foram commitados e verifica que ninguem os moveu sem
subir a versao. Se alguem editar um caso, trocar um split ou encostar no TEST, o
sha256 do manifesto deixa de bater com o do snapshot e este arquivo acusa.

  python tests/test_fase25_congelamento.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase25 import split as sp  # noqa: E402

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"

N = 16
N_TRAIN = 10
N_VALIDATION = 6


def _carregar():
    import json
    ent = man.carregar(MANIFESTO)
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return ent, snap


def test_01_o_manifesto_congelado_existe():
    assert MANIFESTO.exists(), "manifesto congelado desapareceu"
    assert SNAPSHOT.exists(), "snapshot desapareceu"


def test_02_tem_os_16_casos():
    ent, _ = _carregar()
    assert len(ent) == N, "esperava %d entradas, ha %d" % (N, len(ent))


def test_03_o_hash_bate_com_o_snapshot():
    """A trava inteira. Mudou o manifesto sem subir versao? Cai aqui."""
    ent, snap = _carregar()
    r = man.verificar_congelamento(ent, snap)
    assert r["intacto"], "manifesto divergiu do snapshot: %s" % r["mudancas"]


def test_04_a_composicao_e_a_congelada():
    ent, snap = _carregar()
    por = {p: sum(1 for e in ent if e["split"] == p) for p in man.PARTICOES}
    assert por == {"train": N_TRAIN, "validation": N_VALIDATION, "test": 0}, por
    assert snap["por_split"] == por, "snapshot e manifesto discordam da composicao"


def test_05_o_test_esta_vazio():
    ent, _ = _carregar()
    assert [e for e in ent if e["split"] == "test"] == [], "apareceu caso em TEST"


def test_06_treino_nao_alcanca_o_test():
    """Nao e convencao de nome: e excecao levantada de verdade."""
    ent, _ = _carregar()
    for contexto in ("treino", "validacao"):
        try:
            man.carregar_particao(ent, "test", contexto)
        except man.AcessoIndevido:
            continue
        raise AssertionError("contexto %r leu o TEST — a protecao caiu" % contexto)


def test_07_controle_negativo_o_guarda_nao_proibe_tudo():
    """Se treino tambem nao lesse train, o teste 06 passaria sem provar nada."""
    ent, _ = _carregar()
    assert len(man.carregar_particao(ent, "train", "treino")) == N_TRAIN


def test_08_o_manifesto_e_valido_pelo_esquema():
    ent, _ = _carregar()
    v = man.validar_manifesto(ent)
    assert v["valido"], v["erros"][:5]


def test_09_nenhum_sujeito_em_dois_splits():
    ent, _ = _carregar()
    por = {}
    for e in ent:
        por.setdefault(e["source_case_id"], set()).add(e["split"])
    maus = sorted(s for s, v in por.items() if len(v) > 1)
    assert not maus, "sujeito nos dois lados: %s" % maus


def test_10_o_split_gravado_e_o_que_a_regra_produz():
    """O manifesto nao pode ter split editado a mao depois do congelamento."""
    ent, _ = _carregar()
    divergentes = [e["case_id"] for e in ent if e["split"] != sp.atribuir(e["case_id"])]
    assert not divergentes, "split gravado diverge da regra: %s" % divergentes


def test_11_a_ontologia_do_snapshot_e_a_congelada():
    from scripts.validation.tier2 import ontologia_esofago as onto
    _, snap = _carregar()
    assert snap["ontologia"] == onto.VERSAO, "snapshot aponta outra ontologia"


def main() -> int:
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    falhas = []
    for nome, f in testes:
        try:
            f()
            print("  ok   %s" % nome)
        except Exception as exc:  # noqa: BLE001
            falhas.append((nome, exc))
            print("  FALHA %s: %s" % (nome, exc))
    print("\n%d/%d passaram" % (len(testes) - len(falhas), len(testes)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
