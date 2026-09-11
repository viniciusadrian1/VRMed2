"""Fase 28 — a descoberta de candidatos a TEST nao pode ter mexido em nada, e o
status A nao pode ser dado sem evidencia.

Duas metades:

  [CONGELAMENTO]  a fase e de pesquisa. Se ela tocou no manifesto, no snapshot, no
                  split ou no TEST, e falha, por mais interessante que seja o achado.

  [CLASSIFICACAO] a regra do status A vira CODIGO. Um candidato so pode ser A se
                  houver evidencia POSITIVA em quatro eixos. Sem isso o maximo e B.
                  Escrever a regra em prosa no relatorio nao impede ninguem de
                  promover um candidato duvidoso amanha; um teste impede.

  python tests/test_fase28_test_discovery.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
CANDIDATOS = RAIZ / "docs" / "overnight" / "phase28" / "candidatos.json"

SHA_CONGELADO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"
N_TRAIN, N_VALIDATION, N_TEST = 10, 6, 0

# Os quatro eixos que o pedido exige para o status A. Cada um precisa de evidencia
# POSITIVA — ausencia de evidencia contraria nao serve.
EXIGENCIAS_A = {
    "independencia": ("DEMONSTRAVEL",),
    "ontologia": ("COMPATIVEL",),
    "anotacao_tipo": ("HUMANA_MANUAL", "HUMANA_REVISADA"),
    "acesso": ("ABERTO", "CADASTRO"),
}
LICENCAS_PROIBIDAS_PARA_A = set(man.LICENCAS_BLOQUEANTES)

STATUS_VALIDOS = ("A", "B", "C", "D", "E")


class Pulado(Exception):
    """O artefato ainda nao existe."""


def _ent():
    return man.carregar(MANIFESTO)


def _candidatos():
    if not CANDIDATOS.exists():
        raise Pulado("candidatos.json ausente (%s)" % CANDIDATOS)
    return json.loads(CANDIDATOS.read_text(encoding="utf-8"))


def pode_ser_A(c: dict) -> tuple:
    """A regra, em codigo. Devolve (pode, motivos_que_impedem)."""
    impedimentos = []
    for campo, aceitos in EXIGENCIAS_A.items():
        v = c.get(campo, "UNKNOWN")
        if v not in aceitos:
            impedimentos.append("%s=%r (exigido um de %s)" % (campo, v, list(aceitos)))
    lic = c.get("licenca_classe", "UNKNOWN")
    if lic in LICENCAS_PROIBIDAS_PARA_A:
        impedimentos.append("licenca_classe=%r e bloqueante" % lic)
    if c.get("overlap") == "DETECTADO":
        impedimentos.append("overlap DETECTADO")
    return (not impedimentos, impedimentos)


# ------------------------------------------------------- [CONGELAMENTO]


def test_01_manifesto_nao_mudou():
    ent = _ent()
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    r = man.verificar_congelamento(ent, snap)
    assert r["intacto"], "manifesto divergiu do snapshot: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_CONGELADO, (
        "sha256 do manifesto mudou: %s" % r["sha256_atual"])


def test_02_snapshot_nao_mudou():
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snap["sha256_manifesto"] == SHA_CONGELADO
    assert snap["versao"] == "VRMED-ESOPHAGUS-POOL16-V1"
    assert snap["por_split"] == {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST}


def test_03_split_nao_mudou():
    por = {p: sum(1 for e in _ent() if e["split"] == p) for p in man.PARTICOES}
    assert por == {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST}, por


def test_04_test_continua_zero_e_inalcancavel():
    ent = _ent()
    assert [e for e in ent if e["split"] == "test"] == [], "apareceu caso em TEST"
    for contexto in ("treino", "validacao"):
        try:
            man.carregar_particao(ent, "test", contexto)
        except man.AcessoIndevido:
            continue
        raise AssertionError("contexto %r alcancou o TEST" % contexto)
    # controle negativo: o guarda nao proibe tudo
    assert len(man.carregar_particao(ent, "train", "treino")) == N_TRAIN


def test_05_nenhum_candidato_entrou_no_manifesto():
    """A fase e de pesquisa. Nenhuma fonte nova pode ter virado caso."""
    fontes = {e["source_dataset"] for e in _ent()}
    assert fontes == {"4D-Lung (TCIA)"}, (
        "apareceu source_dataset novo no manifesto congelado: %s" % sorted(fontes))
    try:
        cands = _candidatos()
    except Pulado:
        return
    nomes_no_manifesto = {e["case_id"] for e in _ent()}
    for c in cands["candidatos"]:
        # nenhum nome de candidato pode ter virado case_id
        assert not any(c["nome"].lower() in n.lower() for n in nomes_no_manifesto), (
            "candidato %r aparece como caso do manifesto" % c["nome"])


# ------------------------------------------------------- [CLASSIFICACAO]


def test_06_todo_candidato_tem_status_valido():
    cands = _candidatos()
    for c in cands["candidatos"]:
        assert c.get("status") in STATUS_VALIDOS, (
            "%s tem status invalido: %r" % (c.get("nome"), c.get("status")))


def test_07_status_A_exige_evidencia_positiva_nos_quatro_eixos():
    """A regra central da fase, em codigo.

    Sem isto, 'A exige evidencia' e so uma frase no relatorio — e frases nao impedem
    ninguem de promover um candidato duvidoso na proxima fase.
    """
    cands = _candidatos()
    indevidos = []
    for c in cands["candidatos"]:
        if c.get("status") != "A":
            continue
        pode, impedimentos = pode_ser_A(c)
        if not pode:
            indevidos.append("%s: %s" % (c["nome"], "; ".join(impedimentos)))
    assert not indevidos, (
        "candidato(s) com status A sem evidencia suficiente:\n  " + "\n  ".join(indevidos))


def test_08_controle_positivo_a_regra_nao_proibe_tudo():
    """Um candidato sintetico que cumpre TUDO tem de poder ser A.

    Sem este controle, a regra do teste 07 poderia estar simplesmente reprovando
    qualquer coisa, e passaria sem provar nada.
    """
    perfeito = {
        "nome": "SINTETICO",
        "independencia": "DEMONSTRAVEL",
        "ontologia": "COMPATIVEL",
        "anotacao_tipo": "HUMANA_MANUAL",
        "acesso": "ABERTO",
        "licenca_classe": "ABERTA_ATRIBUICAO",
        "overlap": "NAO DETECTADO",
    }
    pode, imp = pode_ser_A(perfeito)
    assert pode, "a regra reprovou um candidato que cumpre todos os eixos: %s" % imp


def test_09_controle_positivo_a_regra_realmente_reprova():
    """E o espelho: cada eixo, quebrado sozinho, tem de impedir o A."""
    base = {
        "nome": "S", "independencia": "DEMONSTRAVEL", "ontologia": "COMPATIVEL",
        "anotacao_tipo": "HUMANA_MANUAL", "acesso": "ABERTO",
        "licenca_classe": "ABERTA_ATRIBUICAO", "overlap": "NAO DETECTADO",
    }
    quebras = [
        ("independencia", "INCONCLUSIVA"),
        ("ontologia", "PARCIAL"),
        ("anotacao_tipo", "AUTOMATICA"),
        ("anotacao_tipo", "UNKNOWN"),
        ("acesso", "EULA"),
        ("licenca_classe", "UNKNOWN"),
        ("licenca_classe", "CONFLITO"),
        ("overlap", "DETECTADO"),
    ]
    for campo, valor in quebras:
        pode, _ = pode_ser_A({**base, campo: valor})
        assert not pode, "a regra aceitou A com %s=%r — detector cego" % (campo, valor)


def test_10_independencia_inconclusiva_nunca_vira_demonstravel():
    """A regra que o projeto repete desde a Fase 18.

    'Nao detectado' e resultado de instrumento; 'independencia demonstrada' e
    afirmacao sobre o mundo. Um candidato cuja relacao com o TotalSegmentator seja
    INCONCLUSIVA nao pode ter independencia DEMONSTRAVEL.
    """
    cands = _candidatos()
    maus = []
    for c in cands["candidatos"]:
        rel = str(c.get("relacao_totalsegmentator", "")).upper()
        if "INCONCLUSIV" in rel and c.get("independencia") == "DEMONSTRAVEL":
            maus.append(c["nome"])
    assert not maus, (
        "candidato(s) com relacao INCONCLUSIVA ao TotalSegmentator marcados como "
        "independencia DEMONSTRAVEL: %s" % maus)


def test_11_os_quatro_proibidos_nao_viraram_A():
    """LCTSC, LyNoS, NSCLC-Radiomics e SegTHOR estao proibidos como TEST."""
    proibidos = ("lctsc", "lynos", "nsclc-radiomics", "segthor")
    cands = _candidatos()
    maus = [c["nome"] for c in cands["candidatos"]
            if c.get("status") == "A" and any(p in c["nome"].lower() for p in proibidos)]
    assert not maus, "dataset proibido promovido a A: %s" % maus


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
