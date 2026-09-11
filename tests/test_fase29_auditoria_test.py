"""Fase 29 — a regra de aprovacao A e os invariantes que a fase nao podia tocar.

Tres metades:

  [REGRA]        os sete cenarios que o pedido exige, mais o controle positivo. A regra
                 vive em `fase29/decisao.py` e aqui ela e REAPLICADA — se as duas
                 divergirem, isto cai.

  [CONGELAMENTO] manifesto, snapshot, split, pool16 e TEST=0 inalterados.

  [TREINO]       nenhum checkpoint alterado e nenhum treino novo. Provado por
                 impressao digital: contagem de epocas por fold e tamanho/mtime de
                 cada .pth, comparados com o que a fase registrou ao comecar.

  python tests/test_fase29_auditoria_test.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase29.decisao import (  # noqa: E402
    EIXOS_INDEPENDENCIA, pode_ser_A,
)

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
POOL16 = RAIZ / "docs" / "FASE24-POOL-16.json"
DECISAO = RAIZ / "docs" / "FASE29-DECISAO-TEST.json"
IMPRESSAO = RAIZ / "docs" / "overnight" / "phase29" / "impressao_digital_treino.json"

SHA_CONGELADO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"
SHA_POOL16 = "1a013531ad65b89275e8878ac6180cdbe0e376cb3d4d88c4433897fb519b11b9"
N_TRAIN, N_VALIDATION, N_TEST = 10, 6, 0


class Pulado(Exception):
    """Artefato ainda nao existe. NAO e passar."""


def _ent():
    return man.carregar(MANIFESTO)


def _perfeito(**kw):
    base = {
        "nome": "SINTETICO",
        "independencia": {e: "DEMONSTRADA" for e in EIXOS_INDEPENDENCIA},
        "ontologia": "COMPATIVEL", "anotacao_tipo": "HUMANA_MANUAL",
        "acesso": "ABERTO", "licenca_classe": "ABERTA_ATRIBUICAO",
        "overlap": "NAO DETECTADO",
    }
    base.update(kw)
    return base


# ----------------------------------------------------------------- [REGRA]


def test_01_candidato_perfeito_vira_A():
    """Controle positivo. Sem ele, a regra poderia estar reprovando tudo."""
    pode, imp = pode_ser_A(_perfeito())
    assert pode, "candidato perfeito reprovado: %s" % imp


def test_02_sem_licenca_nao_e_A():
    for lic in ("UNKNOWN", "CONFLITO", "RESTRITA", "ABERTA_SEM_DERIVADAS"):
        assert not pode_ser_A(_perfeito(licenca_classe=lic))[0], "aceitou licenca %s" % lic


def test_03_ontologia_desconhecida_nao_e_A():
    for o in ("UNKNOWN", "PARCIAL", "INCOMPATIVEL"):
        assert not pode_ser_A(_perfeito(ontologia=o))[0], "aceitou ontologia %s" % o


def test_04_anotacao_desconhecida_nao_e_A():
    for a in ("UNKNOWN", "AUTOMATICA", "SEMIAUTOMATICA", "DERIVADA_DE_MODELO"):
        assert not pode_ser_A(_perfeito(anotacao_tipo=a))[0], "aceitou anotacao %s" % a


def test_05_independencia_inconclusiva_nao_e_A_em_nenhum_dos_cinco_eixos():
    """O teste central da fase.

    Basta UM dos cinco eixos nao estar demonstrado para impedir o A. E o eixo
    `linhagem_anotacao` e o que a Fase 28 descobriu estar aberto para todo mundo.
    """
    for eixo in EIXOS_INDEPENDENCIA:
        for v in ("INCONCLUSIVO", "PLAUSIVEL", "NAO DEMONSTRADA", "NAO VERIFICAVEL", ""):
            ind = {e: "DEMONSTRADA" for e in EIXOS_INDEPENDENCIA}
            ind[eixo] = v
            assert not pode_ser_A(_perfeito(independencia=ind))[0], (
                "aceitou A com independencia.%s=%r" % (eixo, v))


def test_06_overlap_confirmado_nao_e_A():
    for ov in ("DETECTADO", "CONFIRMADO", "IDENTIDADE"):
        assert not pode_ser_A(_perfeito(overlap=ov))[0], "aceitou overlap %s" % ov


def test_07_acesso_inviavel_nao_e_A():
    for ac in ("EULA", "DUA", "RESTRITO", "INDISPONIVEL", "UNKNOWN"):
        assert not pode_ser_A(_perfeito(acesso=ac))[0], "aceitou acesso %s" % ac


def test_08_proibidos_nunca_viram_A():
    for p in ("LCTSC", "LyNoS", "NSCLC-Radiomics", "SegTHOR"):
        assert not pode_ser_A(_perfeito(nome="%s 2019" % p))[0], "aceitou proibido %s" % p


def test_09_a_decisao_publicada_respeita_a_regra():
    """Reaplica a regra sobre o JSON que a fase publicou."""
    if not DECISAO.exists():
        raise Pulado("FASE29-DECISAO-TEST.json ausente")
    d = json.loads(DECISAO.read_text(encoding="utf-8"))
    maus = [c["nome"] for c in d["candidatos"]
            if c["status"] == "A" and c.get("impedimentos_para_A")]
    assert not maus, "status A publicado com impedimentos: %s" % maus
    assert d["test_atual"]["n"] == N_TEST, "o JSON declara TEST != 0"
    assert d["test_atual"]["estado"] == "PROTEGIDO"
    # coerencia: aprovados_A tem de bater com os status A
    a_por_status = sorted(c["nome"] for c in d["candidatos"] if c["status"] == "A")
    assert sorted(d["aprovados_A"]) == a_por_status, (
        "aprovados_A diverge dos candidatos com status A")


# ---------------------------------------------------------- [CONGELAMENTO]


def test_10_manifesto_e_snapshot_inalterados():
    r = man.verificar_congelamento(_ent(), json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    assert r["intacto"], "manifesto divergiu: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_CONGELADO


def test_11_split_inalterado_e_test_zero():
    por = {p: sum(1 for e in _ent() if e["split"] == p) for p in man.PARTICOES}
    assert por == {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST}, por
    for contexto in ("treino", "validacao"):
        try:
            man.carregar_particao(_ent(), "test", contexto)
        except man.AcessoIndevido:
            continue
        raise AssertionError("contexto %r alcancou o TEST" % contexto)
    assert len(man.carregar_particao(_ent(), "train", "treino")) == N_TRAIN


def test_12_pool16_inalterado():
    import hashlib
    if not POOL16.exists():
        raise Pulado("FASE24-POOL-16.json ausente")
    h = hashlib.sha256(POOL16.read_bytes()).hexdigest()
    assert h == SHA_POOL16, "o pool de 16 mudou: %s" % h
    doc = json.loads(POOL16.read_text(encoding="utf-8"))
    assert len(doc["casos"]) == 16


def test_13_nenhuma_fonte_nova_entrou_no_manifesto():
    fontes = {e["source_dataset"] for e in _ent()}
    assert fontes == {"4D-Lung (TCIA)"}, "source_dataset novo: %s" % sorted(fontes)


# --------------------------------------------------------------- [TREINO]


def test_14_nenhum_treino_novo_e_nenhum_checkpoint_alterado():
    """Compara a arvore de treino com a impressao digital tirada no inicio da fase."""
    if not IMPRESSAO.exists():
        raise Pulado("impressao digital ausente")
    fp = json.loads(IMPRESSAO.read_text(encoding="utf-8"))["folds"]
    bases = {
        "26b": RAIZ / ".clinica-dados/fase26b/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer_250epochs__nnUNetPlans__3d_fullres",
        "26": RAIZ / ".clinica-dados/fase26/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer__nnUNetPlans__3d_fullres",
    }
    divergencias = []
    for chave, esperado in fp.items():
        rot, fold = chave.split("/")
        d = bases[rot] / fold
        if not d.exists():
            divergencias.append("%s sumiu" % chave)
            continue
        txt = "".join(p.read_text(encoding="utf-8", errors="replace")
                      for p in sorted(d.glob("training_log_*.txt")))
        ep = len(re.findall(r"Epoch time: [0-9.]+ s", txt))
        if ep != esperado["epocas"]:
            divergencias.append("%s: %d epocas, esperado %d — TREINO NOVO?"
                                % (chave, ep, esperado["epocas"]))
        for nome, meta in esperado["checkpoints"].items():
            p = d / nome
            if not p.exists():
                divergencias.append("%s/%s sumiu" % (chave, nome))
            elif p.stat().st_size != meta["bytes"]:
                divergencias.append("%s/%s mudou de tamanho" % (chave, nome))
            elif int(p.stat().st_mtime) != meta["mtime"]:
                divergencias.append("%s/%s foi reescrito" % (chave, nome))
    assert not divergencias, "a fase mexeu em treino:\n  " + "\n  ".join(divergencias)


def test_15_a_fase29_nao_produziu_predicao_nova():
    """Fase de auditoria: nenhuma pasta de predicao nova pode ter aparecido."""
    base = RAIZ / ".clinica-dados" / "fase26b" / "predicoes_holdout"
    if not base.exists():
        raise Pulado("predicoes_holdout ausente")
    subs = sorted(p.name for p in base.iterdir() if p.is_dir())
    assert subs == ["checkpoint_best", "checkpoint_final"], (
        "apareceu pasta de predicao nova: %s" % subs)


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
