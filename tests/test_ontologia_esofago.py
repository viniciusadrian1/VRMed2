"""Suite de regressao da ESOPHAGUS_ONTOLOGY_V1 — 13 testes, assert puro.

Mesma convencao de `test_geometria.py`: nao ha pytest neste ambiente, entao cada
teste e uma funcao com assert e o `__main__` roda todas.

Rodar:
    .venv-pipeline/Scripts/python.exe tests/test_ontologia_esofago.py

O QUE ESTA SUITE DEFENDE

A Fase 13 congelou a definicao do alvo `esophagus` para fechar o criterio K4. Uma
definicao congelada que ninguem verifica volta a derreter: a Fase 6 escreveu
"limite superior = cricoide", a Fase 7 mediu que o cricoide nao e localizavel, e a
contradicao ficou de pe entre as duas fases ate a Fase 9 remove-la. Esta suite
existe para que isso nao aconteca de novo em silencio.

O TESTE MAIS IMPORTANTE E O 13. Um varredor que devolve "zero violacoes" pode
estar zerado por estar quebrado. O teste 13 injeta violacoes conhecidas num
arquivo temporario e exige que o varredor as encontre — sem ele, os testes 9-11
provariam apenas que o codigo roda, nao que ele ve.
O teste 12 fecha o outro laco: uma metrica congelada que some de um CSV
publicado tem que quebrar a suite, e nao passar em silencio.

Nenhuma tolerancia aqui foi afrouxada para passar. Se um teste falhar, a falha e
o resultado.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validation.tier2 import ontologia_esofago as ont  # noqa: E402

DOCS = Path(__file__).resolve().parents[1] / "docs"
ESPEC = DOCS / "ESOPHAGUS-ONTOLOGY-V1.md"


# ------------------------------------------------------- 1-4: o alvo congelado

def test_01_alvo_e_mascara_preenchida():
    """Parede + lumen sao UM alvo. Separa-los seria outra ontologia, nao esta."""
    assert "PREENCHIDA" in ont.ALVO["representacao"].upper()
    assert "NAO SEPARADOS" in ont.ALVO["parede_e_lumen"].upper()
    assert any("parede" in i for i in ont.INCLUI)
    assert any("lumen" in i for i in ont.INCLUI), "o lumen ESTA dentro do alvo"


def test_02_exclusoes_completas():
    """As quatro exclusoes do enunciado da Fase 13, nenhuma a menos."""
    txt = " ".join(ont.EXCLUI).lower()
    for termo in ("conteudo", "adiposo", "vizinha", "nao observavel"):
        assert termo in txt, f"exclusao ausente: {termo}"
    # O conteudo e excluido como CLASSE, nao como regiao — o lumen segue preenchido.
    assert "classe independente" in txt


def test_03_extensao_herdada_e_nao_avaliavel():
    e = ont.EXTENSAO_LONGITUDINAL.upper()
    assert "HERDADA" in e and "NAO AVALIAVEL" in e
    assert len(ont.EXTENSAO_JUSTIFICATIVA) > 200, "a decisao precisa vir com a medida"


def test_04_marcos_separados_por_capacidade():
    """Cricoide e JGE fora; carina dentro — e a carina NAO ancora o alvo."""
    assert set(ont.MARCOS_NAO_LOCALIZAVEIS) == {"cricoide", "juncao gastroesofagica"}
    assert "carina" in ont.MARCOS_LOCALIZAVEIS
    assert "NAO e usado como ancora" in ont.MARCOS_LOCALIZAVEIS["carina"]
    for m in ont.MARCOS_NAO_LOCALIZAVEIS:
        assert m not in ont.MARCOS_LOCALIZAVEIS


# --------------------------------------------------- 5-7: metricas e unidades

def test_05_metricas_congeladas_sao_as_oito():
    esperadas = {"dice", "iou", "precision", "recall", "hd95", "assd",
                 "erro_volume_absoluto", "erro_volume_percentual"}
    assert set(ont.METRICAS_CONGELADAS) == esperadas, (
        "a lista de metricas mudou — isso exige uma NOVA VERSAO da ontologia, "
        f"nao uma edicao: {set(ont.METRICAS_CONGELADAS) ^ esperadas}")
    assert len(ont.METRICAS_CONGELADAS) == 8


def test_06_distancia_em_milimetros():
    assert ont.UNIDADE_DE_DISTANCIA == "mm"


def test_07_versao_e_protocolo_declarados():
    assert ont.VERSAO == "ESOPHAGUS_ONTOLOGY_V1"
    assert ont.PROTOCOLO_DE_REFERENCIA == "RTOG 1106"
    assert ont.CONGELADA_EM


# ------------------------------------------- 8: a comparacao que nao pode virar nota

def test_08_referencia_humana_declara_teto_e_mundos_diferentes():
    """0,7555 e teto otimista, de outra coorte. Sem isso, vira nota de aprovacao."""
    t = ont.RELACAO_REFERENCIA_HUMANA.upper()
    assert "TETO OTIMISTA" in t
    assert "ORDEM DE GRANDEZA" in t
    assert "OUTRA COORTE" in t or "OUTRA GRADE" in t


# ---------------------------------------------- 9-11: os documentos publicados

def test_09_documentos_sem_frase_proibida():
    r = ont.varrer_docs(DOCS)
    assert r["n_documentos"] > 10, "varredura nao encontrou documentos — caminho errado?"
    assert r["n_com_violacao"] == 0, (
        "documento(s) com frase proibida ou regressao de ontologia:\n"
        + "\n".join(f"  {a}: {v}" for a, v in r["violacoes"].items()))


def test_10_espec_humana_existe_e_bate_com_o_modulo():
    """O .md e o .py sao a MESMA especificacao. Divergir e o modo de falha classico."""
    assert ESPEC.exists(), f"documento da especificacao ausente: {ESPEC}"
    txt = ont._normalizar(ESPEC.read_text(encoding="utf-8"))
    assert ont._normalizar(ont.VERSAO) in txt
    assert ont._normalizar(ont.PROTOCOLO_DE_REFERENCIA) in txt
    assert "herdada" in txt and "nao avaliavel" in txt
    assert "nao separados" in txt
    for m in ont.METRICAS_CONGELADAS:
        alvo = m.replace("_", " ").replace("erro volume", "volume")
        assert alvo.split()[0] in txt, f"metrica congelada ausente do documento: {m}"


def test_11_ontologia_geral_marca_o_cricoide_como_do_GT():
    """A linha do GT no VRMED-ANATOMICAL-ONTOLOGY pode citar o cricoide — desde que
    deixe explicito que e descricao do protocolo do GT, nao capacidade do VRmed."""
    doc = DOCS / "VRMED-ANATOMICAL-ONTOLOGY.md"
    assert doc.exists()
    linhas = doc.read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(linhas):
        n = ont._normalizar(ln)
        if "cricoide" in n and "gt lctsc" in n:
            janela = ont._normalizar(" ".join(linhas[i:i + 3]))
            assert "protocolo" in janela or "gt" in janela, (
                f"linha {i+1} cita o cricoide sem marcar que e do protocolo do GT")


# ------------------------------- 12: as metricas congeladas nos CSV publicados

def test_12_csv_publicado_traz_as_metricas_congeladas():
    """A Fase 17 provou que congelar a lista num documento nao basta.

    O benchmark daquela fase foi escrito DEPOIS da ontologia e mesmo assim
    entregou 6 das 8 metricas: pediu ao modulo chaves que nao existem, `dict.get`
    devolveu None em silencio, e o CSV saiu completo sem erro nenhum. Este teste
    fecha o laco pelo lado do artefato publicado.

    Regra: um CSV de benchmark em docs/ precisa trazer, por nome de coluna, cada
    metrica congelada — ou declarar no proprio arquivo por que ela nao se aplica.
    """
    import csv as _csv

    # nome congelado -> nomes de coluna aceitos no CSV
    EQUIV = {
        "dice": ("dice",), "iou": ("iou",),
        "precision": ("precision", "precisao"), "recall": ("recall", "sensibilidade"),
        "hd95": ("hd95", "hd95_mm"), "assd": ("assd", "assd_mm"),
        "erro_volume_absoluto": ("volume_error_abs", "erro_volume_ml", "volume_ml"),
        "erro_volume_percentual": ("volume_error_pct", "erro_volume_pct"),
    }
    # Benchmarks de RECONSTRUCAO nao medem precision/recall: eles comparam malha
    # contra a mascara que a gerou, e nao ha classificador. A dispensa e nominal
    # e declarada aqui, nao inferida em silencio pelo teste.
    DISPENSADAS_EM_RECONSTRUCAO = {"precision", "recall"}

    csvs = sorted(DOCS.rglob("*benchmark*.csv"))
    assert csvs, "nenhum CSV de benchmark encontrado em docs/ — caminho errado?"
    for arq in csvs:
        with arq.open(encoding="utf-8", newline="") as f:
            colunas = {c.strip().lower() for c in (next(_csv.reader(f), []) or [])}
        assert colunas, f"{arq.name}: sem cabecalho"
        eh_reconstrucao = "reconstruction" in arq.name or "variant" in colunas
        for metrica, aceitos in EQUIV.items():
            if eh_reconstrucao and metrica in DISPENSADAS_EM_RECONSTRUCAO:
                continue
            assert colunas & set(aceitos), (
                f"{arq.name}: metrica congelada '{metrica}' ausente "
                f"(aceitos: {aceitos}); colunas presentes: {sorted(colunas)}")


# -------------------------------------------------- 13: CONTROLE POSITIVO

def test_13_o_varredor_realmente_ve():
    """Sem este teste, 'zero violacoes' nao prova nada.

    Injeta uma violacao de cada tipo num arquivo temporario e exige que o
    varredor ache TODAS. E depois injeta o caso que deve PASSAR (a mesma frase
    sendo banida) e exige que ele NAO acuse — um varredor que acusa a propria
    lista de proibicoes seria inutilizavel.
    """
    with tempfile.TemporaryDirectory() as d:
        raiz = Path(d)

        (raiz / "violador.md").write_text(
            "# doc de teste\n"
            "O modelo esta dentro da variabilidade humana.\n"
            "O pipeline localiza o cricoide em todos os casos.\n"
            "Aqui separamos parede e lumen em duas classes.\n"
            "Este trabalho foi validado clinicamente.\n",
            encoding="utf-8")
        achados = ont.varrer_documento(raiz / "violador.md")
        assert len(achados) >= 4, f"varredor cego — achou so {len(achados)}: {achados}"
        juntos = " ".join(achados).lower()
        assert "variabilidade humana" in juntos
        assert "cricoide" in juntos
        assert "lumen" in juntos
        assert "clinicamente" in juntos

        # CONTROLE NEGATIVO: banir a frase nao pode contar como comete-la.
        (raiz / "banidor.md").write_text(
            "# frases proibidas\n"
            "1. NAO escrever \"o modelo esta dentro da variabilidade humana\".\n"
            "2. ❌ \"validado clinicamente\"\n"
            "3. O pipeline **nao** localiza o cricoide.\n",
            encoding="utf-8")
        falsos = ont.varrer_documento(raiz / "banidor.md")
        assert not falsos, f"varredor acusou uma lista de proibicoes: {falsos}"

        # A ISENCAO META NAO PODE VIRAR PORTA DE FUGA. Ela exige DUAS coisas:
        # vocabulario de instrumento E a frase entre aspas. Vocabulario sozinho,
        # com a afirmacao solta, tem que continuar sendo acusado — senao bastaria
        # escrever "varredor" numa linha para afirmar qualquer coisa nela.
        (raiz / "meta_legitimo.md").write_text(
            'O varredor acusou a linha que dizia "o modelo esta dentro da '
            'variabilidade humana", e esse foi um falso positivo.\n',
            encoding="utf-8")
        assert not ont.varrer_documento(raiz / "meta_legitimo.md"), (
            "citacao entre aspas num texto sobre o varredor foi acusada")

        (raiz / "meta_fuga.md").write_text(
            "Segundo o varredor, o modelo esta dentro da variabilidade humana.\n",
            encoding="utf-8")
        assert ont.varrer_documento(raiz / "meta_fuga.md"), (
            "PORTA DE FUGA: bastou a palavra 'varredor' para a afirmacao passar")

        # CONTROLE DE TERMO: digital twin sozinho acusa; acompanhado passa.
        (raiz / "twin_sozinho.md").write_text("O VRmed e um digital twin.\n", encoding="utf-8")
        assert ont.checar_termo(raiz / "twin_sozinho.md")
        (raiz / "twin_contraste.md").write_text(
            "patient-specific model vs digital twin: o VRmed e o primeiro.\n", encoding="utf-8")
        assert not ont.checar_termo(raiz / "twin_contraste.md")


TESTES = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    print(f"VRmed — regressao da ESOPHAGUS_ONTOLOGY_V1 ({len(TESTES)} testes, assert puro)\n")
    falhas = []
    for t in TESTES:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            falhas.append((t.__name__, str(e)))
            print(f"  FALHA {t.__name__}: {str(e)[:300]}")
    print()
    if falhas:
        print(f"{len(falhas)} de {len(TESTES)} falharam.")
        raise SystemExit(1)
    print(f"{len(TESTES)}/{len(TESTES)} OK — ontologia congelada e sem regressao.")
