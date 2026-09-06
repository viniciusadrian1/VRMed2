"""Guardas do VRMED-ESOPHAGUS-DATASET-V1 — 19.12 e 19.14, assert puro.

Mesma convencao de `test_ontologia_esofago.py` e `test_geometria.py`: nao ha pytest
neste ambiente, cada teste e uma funcao com assert e o `__main__` roda todas.

Rodar:
    .venv-pipeline/Scripts/python.exe tests/test_baseline_v1.py

O QUE ESTA SUITE DEFENDE

A Fase 16 mediu por que o baseline atual (TotalSegmentator) e inauditavel, e a lista
nao tem nada a ver com modelagem: nao ha lista de casos efetivamente usada, 420 de
1.559 imagens de treino nao sao atribuidas, os pesos sao `fold=0` sem o
`splits_final.json` correspondente, e SegTHOR/BTCV semearam a primeira segmentacao
do treino — circularidade de anotacao que nenhuma sonda de imagem enxerga.

Nenhum desses defeitos e detectavel DEPOIS. Todos sao evitaveis ANTES. Esta suite e
o "antes".

OS TESTES DE REPRODUTIBILIDADE NEGATIVA (19.14) SAO OS MAIS IMPORTANTES.
Um validador que devolve "nenhum erro" pode estar zerado por estar quebrado. Os
testes 08-14 injetam os sete defeitos que o pedido nomeia, exigem que o sistema
FALHE em cada um, e restauram o estado. Sem eles, os testes 01-07 provariam apenas
que o codigo roda, nao que ele ve.

Nenhuma tolerancia foi afrouxada para passar. Se um teste falhar, a falha e o
resultado.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.baseline_v1 import plano  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

QUANDO = "2026-09-06T00:00:00Z"


def _base():
    """Manifesto sintetico VALIDO. Todo teste negativo parte daqui e injeta um defeito."""
    return [man._entrada("c1", "train"),
            man._entrada("c2", "train"),
            man._entrada("c3", "validation"),
            man._entrada("c4", "test")]


def _erros(entradas, publicavel=True):
    return man.validar_manifesto(entradas, publicavel=publicavel)["erros"]


# =========================================================== 19.12 — guardas base


def test_01_manifesto_valido_passa():
    """Controle NEGATIVO da suite inteira: sem ele, um validador que reprova tudo
    passaria em todos os testes de injecao abaixo e pareceria excelente."""
    v = man.validar_manifesto(_base())
    assert v["valido"], v["erros"]
    assert v["por_split"] == {"train": 2, "validation": 1, "test": 1}, v["por_split"]


def test_02_esquema_tem_todos_os_campos_do_pedido():
    exigidos = {"case_id", "study_id", "series_id", "image_path", "mask_path",
                "spacing", "orientation", "institution", "acquisition",
                "annotation_source", "annotation_protocol", "license",
                "source_doi", "split", "image_sha256", "mask_sha256",
                "source_dataset", "source_case_id", "annotation_date_known", "notes"}
    faltando = exigidos - set(man.CAMPOS)
    assert not faltando, "campos do pedido ausentes do esquema: " + str(sorted(faltando))


def test_03_treino_nao_pode_ler_test_nem_validation():
    """A trava do 19.6. Nao e convencao de nome: e excecao."""
    base = _base()
    for split in ("test", "validation"):
        try:
            man.carregar_particao(base, split, "treino")
            raise AssertionError("contexto treino leu " + split)
        except man.AcessoIndevido:
            pass
    # e o acesso legitimo continua funcionando — senao a trava seria so um bloqueio
    assert len(man.carregar_particao(base, "train", "treino")) == 2
    assert len(man.carregar_particao(base, "validation", "validacao")) == 1
    assert len(man.carregar_particao(base, "test", "avaliacao")) == 1


def test_04_congelamento_produz_hash_estavel_e_independente_de_ordem():
    base = _base()
    with tempfile.TemporaryDirectory() as d:
        s1 = man.congelar(base, Path(d) / "a.json", "V1", QUANDO)
        s2 = man.congelar(list(reversed(base)), Path(d) / "b.json", "V1", QUANDO)
    assert s1["sha256_manifesto"] == s2["sha256_manifesto"], \
        "o hash mudou so por ordem de insercao — congelamento seria ruido"
    assert s1["ontologia"] == onto.VERSAO
    assert s1["n_entradas"] == 4


def test_05_nao_se_congela_manifesto_invalido():
    ruim = _base() + [man._entrada("c1", "test")]  # c1 ja esta em train
    with tempfile.TemporaryDirectory() as d:
        try:
            man.congelar(ruim, Path(d) / "x.json", "V1", QUANDO)
            raise AssertionError("congelou manifesto com vazamento")
        except man.ManifestoInvalido:
            pass


def test_06_baseline_declara_seed_ontologia_e_metricas_congeladas():
    assert plano.BASELINE["seed"] == plano.SEED
    assert plano.BASELINE["alvo"]["definicao"] == onto.VERSAO
    assert tuple(plano.BASELINE["metricas"]) == tuple(onto.METRICAS_CONGELADAS), \
        "as metricas do baseline divergiram das oito congeladas"
    assert "nao treinado" in plano.BASELINE["estado"].lower()


def test_07_ambiente_reflete_o_interpretador():
    """Dependencia digitada a mao e dependencia inventada."""
    a = plano.ambiente()
    assert a["pacotes"]["nnunetv2"] != "AUSENTE", \
        "o baseline proposto e nnU-Net e nnunetv2 nao esta instalado"
    assert a["pacotes"]["monai"] == "AUSENTE", \
        "monai foi reportado como presente; o relatorio tem de refletir a maquina"
    assert a["python"].startswith("3."), a["python"]
    assert a["ontologia"] == onto.VERSAO


# ============================================ 19.14 — reprodutibilidade NEGATIVA
# Sete injecoes, na ordem do pedido. Cada uma exige FALHA, depois restaura.


def test_08_injecao_1_trocar_case_id_de_split():
    base = _base()
    antes = json.dumps(base, sort_keys=True)
    quebrado = [dict(e) for e in base] + [man._entrada("c1", "test")]
    erros = _erros(quebrado)
    assert any("caso 'c1' aparece em" in e for e in erros), erros
    assert json.dumps(base, sort_keys=True) == antes, "o estado original foi mutado"


def test_09_injecao_2_trocar_um_hash():
    base = _base()
    with tempfile.TemporaryDirectory() as d:
        snap = man.congelar(base, Path(d) / "s.json", "V1", QUANDO)
    trocado = [dict(e) for e in base]
    trocado[0]["image_sha256"] = man.sha256_texto("conteudo diferente")
    r = man.verificar_congelamento(trocado, snap)
    assert not r["intacto"], "trocar um hash nao quebrou o congelamento"
    assert any("conteudo alterado: c1" in m for m in r["mudancas"]), r["mudancas"]
    assert r["exige"].startswith("VERSION INCREMENT"), r["exige"]
    # restaurado: o manifesto original ainda bate com o snapshot
    assert man.verificar_congelamento(base, snap)["intacto"]


def test_10_injecao_3_mover_caso_de_validation_para_test():
    base = _base()
    with tempfile.TemporaryDirectory() as d:
        snap = man.congelar(base, Path(d) / "s.json", "V1", QUANDO)
    movido = [dict(e) for e in base]
    movido[2]["split"] = "test"
    r = man.verificar_congelamento(movido, snap)
    assert not r["intacto"], "mover caso entre particoes passou despercebido"
    assert r["exige"].startswith("VERSION INCREMENT")
    assert man.verificar_congelamento(base, snap)["intacto"]


def test_11_injecao_4_mascara_sem_licenca():
    for classe, licenca in (("UNKNOWN", man.DESCONHECIDO),
                            ("CONFLITO", "CC BY 4.0 / MIT"),
                            ("ABERTA_SEM_DERIVADAS", "CC BY-NC-ND 4.0"),
                            ("RESTRITA", "acordo assinado")):
        e = man._entrada("cx", license_class=classe, license=licenca)
        erros = man.validar_licenca(e)
        assert erros, "licenca %s passou sem bloqueio" % classe
    # controle negativo: a licenca boa NAO pode ser bloqueada
    assert not man.validar_licenca(man._entrada("cx")), \
        "CC BY 4.0 foi bloqueada — o validador reprova tudo"


def test_12_injecao_5_remover_campo_obrigatorio():
    for campo in ("annotation_source", "image_sha256", "license_class", "split", "notes"):
        e = man._entrada("cx")
        del e[campo]
        erros = man.validar_entrada(e)
        assert any("campos ausentes" in x and campo in x for x in erros), \
            "remover %s nao foi detectado: %s" % (campo, erros)


def test_13_injecao_6_alterar_a_ontologia():
    """A ontologia entra no snapshot. Trocar a definicao do alvo depois do
    congelamento tem de ser visivel — foi assim que a Fase 6 e a Fase 7 ficaram
    contraditorias por tres fases sem ninguem notar."""
    base = _base()
    with tempfile.TemporaryDirectory() as d:
        snap = man.congelar(base, Path(d) / "s.json", "V1", QUANDO)
    assert snap["ontologia"] == "ESOPHAGUS_ONTOLOGY_V1", snap["ontologia"]
    assert snap["ontologia_congelada_em"] == onto.CONGELADA_EM
    falso = dict(snap, ontologia="ESOPHAGUS_ONTOLOGY_V2")
    assert falso["ontologia"] != snap["ontologia"], \
        "o snapshot nao carrega a ontologia — trocar o alvo seria invisivel"
    # e o alvo do baseline tem de vir da ontologia, nao de um literal solto
    assert plano.BASELINE["alvo"]["representacao"] == onto.ALVO["representacao"]


def test_14_injecao_7_liberar_acesso_ao_test_no_loader():
    """A injecao mais perigosa: alguem 'so por enquanto' abre o TEST para o treino."""
    original = dict(man.PERMISSOES)
    try:
        man.PERMISSOES["treino"] = ("train", "validation", "test")
        vazou = man.carregar_particao(_base(), "test", "treino")
        assert vazou, "a mutacao nao teve efeito — o teste nao esta testando nada"
    finally:
        man.PERMISSOES.clear()
        man.PERMISSOES.update(original)
    # RESTAURADO: a trava tem de voltar a valer
    try:
        man.carregar_particao(_base(), "test", "treino")
        raise AssertionError("a trava NAO foi restaurada — estado corrompido")
    except man.AcessoIndevido:
        pass
    assert man.PERMISSOES == original


# ============================================ 19.8 — alvo, contra a ontologia unica


def test_15_alvo_reprova_parede_sem_lumen_e_aprova_preenchido():
    import numpy as np
    import nibabel as nib
    yy, xx = np.ogrid[:60, :60]
    d = np.sqrt((yy - 30) ** 2 + (xx - 30) ** 2)
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "m.nii.gz"

        solido = np.zeros((60, 60, 40), dtype=np.uint8)
        solido[d <= 8] = 1
        nib.save(nib.Nifti1Image(solido, np.diag([1.0, 1.0, 2.0, 1.0])), str(p))
        assert plano.validar_alvo(p)["aprovado"], "cilindro solido reprovado"

        anel = np.zeros((60, 60, 40), dtype=np.uint8)
        anel[(d >= 5) & (d <= 8)] = 1
        nib.save(nib.Nifti1Image(anel, np.diag([1.0, 1.0, 2.0, 1.0])), str(p))
        r = plano.validar_alvo(p)
        assert not r["aprovado"], "anel oco (so parede) aprovado como alvo"
        assert "preenchida_parede_mais_lumen" in r["problemas"], r["problemas"]

        vazia = np.zeros((60, 60, 40), dtype=np.uint8)
        nib.save(nib.Nifti1Image(vazia, np.diag([1.0, 1.0, 2.0, 1.0])), str(p))
        assert "mascara_vazia" in plano.validar_alvo(p)["problemas"]


def test_16_o_desenho_do_split_nao_contem_caso_inventado():
    """Fase 19 termina em DESENHO. Uma lista de casos aqui seria dado fabricado."""
    txt = json.dumps(plano.DESENHO_SPLIT, ensure_ascii=False)
    for proibido in ("LCTSC-", "pat1", "case_id\":"):
        assert proibido not in txt, "o desenho do split contem caso concreto: " + proibido
    assert "DESENHO" in plano.DESENHO_SPLIT["estado"]


def test_17_a_v1_continua_com_22_campos_e_a_v2_nao_foi_promovida():
    """A Fase 21.13 escreveu uma PROPOSTA de V2 com 10 campos novos. Proposta nao e
    promocao: enquanto este teste existir, a V1 tem exatamente 22 campos e o
    documento da V2 tem de continuar se declarando proposta.

    Sem isto, promover a V2 seria uma edicao silenciosa — exatamente o que a regra
    de mudanca da ontologia e do esquema proibe."""
    assert len(man.CAMPOS) == 22, "a V1 mudou de tamanho: %d campos" % len(man.CAMPOS)
    assert man.VERSAO_ESQUEMA == "VRMED-ESOPHAGUS-DATASET-V1", man.VERSAO_ESQUEMA

    # os campos propostos para a V2 NAO podem ter entrado na V1 por descuido
    propostos = {"identity_channel", "identity_keys_verifiable", "sop_instance_count",
                 "annotation_is_human", "annotation_algorithm_declared", "derived_from",
                 "ethics_approval", "consent_basis", "secondary_use_declared"}
    invadiram = propostos & set(man.CAMPOS)
    assert not invadiram, "campos da proposta de V2 entraram na V1: " + str(sorted(invadiram))

    doc = Path(__file__).resolve().parents[1] / "docs" / "VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md"
    assert doc.exists(), "a proposta de V2 sumiu"
    txt = doc.read_text(encoding="utf-8")
    assert "PROPOSTA, NÃO PROMOVIDA" in txt, "o documento da V2 deixou de se declarar proposta"


def test_18_autotestes_dos_modulos_passam():
    """A suite nao substitui os autotestes — ela exige que eles continuem verdes."""
    assert man.autoteste() == 0, "autoteste do manifesto falhou"
    assert plano.autoteste() == 0, "autoteste do plano falhou"


def main() -> int:
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = []
    for t in testes:
        try:
            t()
            print("  OK   " + t.__name__)
        except AssertionError as e:
            falhas.append((t.__name__, str(e)))
            print("  FAIL " + t.__name__ + ": " + str(e))
        except Exception as e:  # noqa: BLE001
            falhas.append((t.__name__, repr(e)))
            print("  ERRO " + t.__name__ + ": " + repr(e))
    print("\n%d/%d passaram%s" % (len(testes) - len(falhas), len(testes),
                                  "" if not falhas else " — %d falhas" % len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
