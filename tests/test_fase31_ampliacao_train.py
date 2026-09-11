"""Fase 31 — a V1 não pode ter mudado, e a V2 tem de se sustentar sozinha.

Três metades:

  [V1 INTACTA]   manifesto, snapshot, split e pool16 da V1, mais os artefatos de treino
                 e as predições, comparados com a impressão digital tirada ANTES.

  [V2 VÁLIDA]    esquema, hashes, split determinístico, bandas, isolamento, licença,
                 procedência, e reprodutibilidade do manifesto a partir da regra.

  [ANTI-LEAKAGE] os 30 casos novos contra os 16 da V1 nas cinco identidades, contra as
                 coleções históricas, e o registro explícito do que é NOT_AVAILABLE.

  python tests/test_fase31_ampliacao_train.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase31 import pool_v2 as p2  # noqa: E402

MAN_V1 = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAP_V1 = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
POOL16 = RAIZ / "docs" / "FASE24-POOL-16.json"
MAN_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl"
SNAP_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-SNAPSHOT-V2.json"
POOL_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-POOL-V2.json"
ANTES = RAIZ / "docs" / "overnight" / "phase31" / "integridade_antes.json"
INGEST = RAIZ / "docs" / "overnight" / "phase31" / "ingestao_real.json"
PROV = RAIZ / "docs" / "overnight" / "phase20" / "proveniencia_roi.csv"

SHA_V1 = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"
V1 = {"train": 10, "validation": 6, "test": 0}
V2 = {"train": 32, "validation": 14, "test": 0}
N_V1, N_NOVOS, N_V2 = 16, 30, 46


class Pulado(Exception):
    """Artefato ausente. NÃO é passar."""


def _v1():
    return man.carregar(MAN_V1)


def _v2():
    if not MAN_V2.exists():
        raise Pulado("manifesto V2 ausente")
    return man.carregar(MAN_V2)


# ------------------------------------------------------------ [V1 INTACTA]


def test_01_manifesto_v1_nao_alterado():
    r = man.verificar_congelamento(_v1(), json.loads(SNAP_V1.read_text(encoding="utf-8")))
    assert r["intacto"], "manifesto V1 divergiu: %s" % r["mudancas"]
    assert r["sha256_atual"] == SHA_V1, "sha256 da V1 mudou"


def test_02_split_v1_nao_alterado():
    por = {p: sum(1 for e in _v1() if e["split"] == p) for p in man.PARTICOES}
    assert por == V1, por
    assert len(_v1()) == N_V1


def test_03_snapshot_e_pool16_nao_alterados():
    if not ANTES.exists():
        raise Pulado("impressão digital ausente")
    a = json.loads(ANTES.read_text(encoding="utf-8"))
    assert hashlib.sha256(SNAP_V1.read_bytes()).hexdigest() == a["VRMED-ESOFAGO-SNAPSHOT-V1.json"]
    assert hashlib.sha256(POOL16.read_bytes()).hexdigest() == a["FASE24-POOL-16.json"]


def test_04_nenhum_checkpoint_alterado_e_nenhum_treino_novo():
    if not ANTES.exists():
        raise Pulado("impressão digital ausente")
    antes = json.loads(ANTES.read_text(encoding="utf-8"))["treino"]
    bases = {
        "26b": RAIZ / ".clinica-dados/fase26b/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer_250epochs__nnUNetPlans__3d_fullres",
        "26": RAIZ / ".clinica-dados/fase26/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer__nnUNetPlans__3d_fullres",
    }
    difs = []
    for chave, esp in antes.items():
        rot, fold = chave.split("/")
        d = bases[rot] / fold
        txt = "".join(p.read_text(encoding="utf-8", errors="replace")
                      for p in sorted(d.glob("training_log_*.txt"))) if d.exists() else ""
        n = len(re.findall(r"Epoch time:", txt))
        if n != esp["epocas"]:
            difs.append("%s: %d épocas, era %d — TREINO NOVO" % (chave, n, esp["epocas"]))
        pth = {p.name: [p.stat().st_size, int(p.stat().st_mtime)] for p in sorted(d.glob("*.pth"))}
        if pth != esp["pth"]:
            difs.append("%s: checkpoint alterado" % chave)
    assert not difs, "\n  ".join(difs)


def test_05_nenhuma_inferencia_nova():
    if not ANTES.exists():
        raise Pulado("impressão digital ausente")
    a = json.loads(ANTES.read_text(encoding="utf-8"))["predicoes"]
    base = RAIZ / ".clinica-dados" / "fase26b" / "predicoes_holdout"
    agora = {d.name: len(list(d.glob("*.nii.gz"))) for d in sorted(base.iterdir()) if d.is_dir()}
    assert agora == a, "contagem de predições mudou: %s vs %s" % (agora, a)


def test_06_artefatos_historicos_de_fase_anterior_intactos():
    """A Fase 31 escreveu por engano em phase23 e foi restaurado. Isto trava."""
    p = RAIZ / "docs" / "overnight" / "phase23" / "ingestao_real.json"
    if not p.exists():
        raise Pulado("artefato da Fase 23 ausente")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert len(d["casos"]) == 5, "phase23/ingestao_real.json deveria ter os 5 da Fase 23, tem %d" % len(d["casos"])
    ids = {c["case_id"] for c in d["casos"]}
    assert all("HM10395" in i for i in ids), "apareceu caso não-4D-Lung no artefato da Fase 23: %s" % ids


# -------------------------------------------------------------- [V2 VÁLIDA]


def test_07_manifesto_v2_valido_pelo_esquema():
    v = man.validar_manifesto(_v2())
    assert v["valido"], v["erros"][:5]
    assert len(_v2()) == N_V2


def test_08_manifesto_v2_bate_com_o_snapshot():
    snap = json.loads(SNAP_V2.read_text(encoding="utf-8"))
    r = man.verificar_congelamento(_v2(), snap)
    assert r["intacto"], "V2 divergiu do snapshot: %s" % r["mudancas"]
    assert snap["ontologia"] == "ESOPHAGUS_ONTOLOGY_V1", "V2 aponta outra ontologia"
    assert snap["por_split"] == V2


def test_09_todo_caso_v2_tem_hash_de_imagem_e_mascara():
    for e in _v2():
        for campo in ("image_sha256", "mask_sha256"):
            v = e[campo]
            assert isinstance(v, str) and len(v) == 64, "%s sem sha256: %s" % (e["case_id"], campo)
            assert all(c in "0123456789abcdef" for c in v.lower())


def test_10_split_v2_e_deterministico_e_reproduzivel():
    """O split gravado tem de ser o que a regra produz — não editado à mão."""
    div = [e["case_id"] for e in _v2() if e["split"] != p2.atribuir(e["case_id"])]
    assert not div, "split gravado diverge da regra: %s" % div
    por = {p: sum(1 for e in _v2() if e["split"] == p) for p in man.PARTICOES}
    assert por == V2, por


def test_11_bandas_declaradas_respeitadas_por_estrato():
    aud = p2.auditar(_v2())
    for fonte, s in aud["estratos"].items():
        assert s["dentro_da_banda"], "%s fora da banda: %d em %s" % (fonte, s["validation"], s["banda"])
    assert aud["dentro_da_banda_global"], "global fora da banda"
    # e as duas fontes aparecem nos DOIS lados — é para isso que a estratificação existe
    for fonte, s in aud["estratos"].items():
        assert s["train"] > 0 and s["validation"] > 0, "%s não aparece nos dois lados" % fonte


def test_12_train_e_validation_sem_overlap():
    tr = {e["case_id"] for e in _v2() if e["split"] == "train"}
    va = {e["case_id"] for e in _v2() if e["split"] == "validation"}
    assert not (tr & va), "caso em train E validation: %s" % sorted(tr & va)
    aud = p2.auditar(_v2())
    assert not aud["identidade"]["sujeitos_em_dois_splits"], (
        "sujeito nos dois lados: %s" % aud["identidade"]["sujeitos_em_dois_splits"])


def test_13_test_zero_e_protegido():
    ent = _v2()
    assert [e for e in ent if e["split"] == "test"] == [], "apareceu caso em TEST na V2"
    for ctx in ("treino", "validacao"):
        try:
            man.carregar_particao(ent, "test", ctx)
        except man.AcessoIndevido:
            continue
        raise AssertionError("contexto %r alcançou o TEST" % ctx)
    try:
        man.carregar_particao(ent, "validation", "treino")
        raise AssertionError("o contexto de treino alcançou VALIDATION")
    except man.AcessoIndevido:
        pass
    assert len(man.carregar_particao(ent, "train", "treino")) == V2["train"]  # controle negativo


def test_14_licenca_unknown_nao_passa_como_elegivel():
    lic = {e["license_class"] for e in _v2()}
    bloq = lic & set(man.LICENCAS_BLOQUEANTES)
    assert not bloq, "licença bloqueante no pool V2: %s" % bloq
    assert lic == {"ABERTA_ATRIBUICAO"}, lic
    # e o detector funciona: injetar UNKNOWN tem de acusar
    ruim = [dict(_v2()[0], license_class="UNKNOWN")]
    assert p2.auditar(ruim)["licencas_bloqueantes"], "o detector de licença está cego"


def test_15_ontologia_unknown_nao_passa_como_elegivel():
    """Todo caso do V2 passou por `validar_alvo`; os rejeitados ficam no registro.

    O que a ontologia congelada EXIGE: aprovação nos critérios, máscara não vazia,
    volume na faixa e dtype inteiro. Ela **não** exige componente conexo único — mede
    e reporta, mas não bloqueia. O teste afirma a regra real, não uma mais estrita
    inventada aqui.
    """
    if not INGEST.exists():
        raise Pulado("registro de ingestão ausente")
    d = json.loads(INGEST.read_text(encoding="utf-8"))
    for c in d["casos"]:
        if c.get("elegivel"):
            assert c["ontologia"]["aprovado"] is True, "%s elegível sem aprovação ontológica" % c["case_id"]
            m = c["ontologia"]["medidas"]
            assert m["binaria"] is True and m["mascara_vazia"] is False
            assert m["dtype"] not in ("float32", "float64")


def test_15b_a_excecao_de_multiplos_componentes_fica_exposta():
    """Um caso do LCTSC tem 2 componentes. A ontologia aceita; o projeto não esconde.

    Este teste existe para que a exceção seja CONTADA. Se amanhã aparecerem cinco
    casos fragmentados, ele cai e obriga alguém a olhar — em vez de o número crescer
    em silêncio dentro de um pool aprovado.
    """
    if not INGEST.exists():
        raise Pulado("registro de ingestão ausente")
    d = json.loads(INGEST.read_text(encoding="utf-8"))
    multi = [(c["case_id"], c["ontologia"]["medidas"]["n_componentes_3d"])
             for c in d["casos"] if c.get("elegivel")
             and c["ontologia"]["medidas"]["n_componentes_3d"] > 1]
    assert multi == [("LCTSC-Train-S3-002", 2)], (
        "o conjunto de casos com múltiplos componentes mudou: %s" % multi)


def test_16_todo_caso_v2_tem_procedencia():
    for e in _v2():
        for campo in ("source_dataset", "source_doi", "source_case_id",
                      "annotation_source", "license", "license_class"):
            assert e[campo] and e[campo] != man.DESCONHECIDO, (
                "%s sem %s" % (e["case_id"], campo))
        assert e["source_dataset"] in ("4D-Lung (TCIA)", "LCTSC (TCIA)")


# ---------------------------------------------------------- [ANTI-LEAKAGE]


def test_17_novos_nao_colidem_com_a_v1_em_nenhuma_das_cinco_identidades():
    v1, v2 = _v1(), _v2()
    ids_v1 = {e["case_id"] for e in v1}
    novos = [e for e in v2 if e["case_id"] not in ids_v1]
    assert len(novos) == N_NOVOS, "esperava %d casos novos, há %d" % (N_NOVOS, len(novos))
    for chave in ("case_id", "study_id", "series_id", "image_sha256", "mask_sha256"):
        inter = {e[chave] for e in novos} & {e[chave] for e in v1}
        assert not inter, "colisão em %s: %s" % (chave, sorted(inter)[:3])
    # e por sujeito
    inter = {e["source_case_id"] for e in novos} & {e["source_case_id"] for e in v1}
    assert not inter, "sujeito repetido entre V1 e novos: %s" % sorted(inter)


def test_18_cross_format_nao_vira_falso_independente():
    """A lição do LyNoS: hash não detecta o mesmo exame em outro formato.

    O registro da fase tem de declarar NOT_AVAILABLE para as fontes sem UID, em vez
    de dizer 'sem overlap'.
    """
    p = RAIZ / "docs" / "overnight" / "phase31" / "antileakage.json"
    if not p.exists():
        raise Pulado("registro de anti-leakage ausente")
    d = json.loads(p.read_text(encoding="utf-8"))
    ly = d.get("lynos", {})
    assert ly.get("estado") == "NOT_AVAILABLE", "LyNoS deveria ser NOT_AVAILABLE, é %r" % ly.get("estado")
    txt = json.dumps(d).lower()
    assert "sem overlap" not in txt, "o registro afirma 'sem overlap' onde a checagem é impossível"
    for fonte in ("4d_lung", "nsclc_radiomics", "pediatric_ct_seg", "eay131"):
        assert fonte in d["colecoes_historicas"], "coleção histórica não checada: %s" % fonte


def test_19_nenhum_caso_rejeitado_desaparece_sem_motivo():
    if not INGEST.exists():
        raise Pulado("registro de ingestão ausente")
    d = json.loads(INGEST.read_text(encoding="utf-8"))
    for c in d["casos"]:
        if not c.get("elegivel"):
            assert c.get("bloqueios"), "%s rejeitado sem motivo registrado" % c["case_id"]
    n_ok = sum(1 for c in d["casos"] if c.get("elegivel"))
    assert n_ok + sum(1 for c in d["casos"] if not c.get("elegivel")) == len(d["casos"])


def test_20_pool_v2_publicado_bate_com_o_manifesto():
    if not POOL_V2.exists():
        raise Pulado("pool V2 ausente")
    d = json.loads(POOL_V2.read_text(encoding="utf-8"))
    v2 = {e["case_id"]: e for e in _v2()}
    assert len(d["casos"]) == N_V2
    assert d["sha256_manifesto"] == man.sha256_texto(man._canonico(_v2()))
    for c in d["casos"]:
        e = v2[c["case_id"]]
        assert c["split"] == e["split"] and c["image_sha256"] == e["image_sha256"]
        assert c["bucket"] == p2.bucket(c["case_id"])


def test_21_a_fonte_nova_respeita_o_split_congelado_do_lctsc():
    """Só o `development` 30. `validation` 15 e `test` 15 do LCTSC ficam de fora."""
    f5 = RAIZ / ".clinica-dados" / "tier2" / "lctsc" / "fase5" / "split.json"
    if not f5.exists():
        raise Pulado("split congelado do LCTSC ausente")
    s = json.loads(f5.read_text(encoding="utf-8"))["split"]
    usados = {e["source_case_id"] for e in _v2() if e["source_dataset"] == "LCTSC (TCIA)"}
    assert usados == set(s["development"]), "os casos usados não são o development do LCTSC"
    for part in ("validation", "test"):
        inter = usados & set(s[part])
        assert not inter, "usou caso do %s do LCTSC: %s" % (part, sorted(inter))


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
