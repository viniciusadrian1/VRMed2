"""ESOPHAGUS_ONTOLOGY_V1 — a definicao congelada do alvo `esophagus` do VRmed.

Este modulo e a FONTE DA VERDADE legivel por maquina. O documento
`docs/ESOPHAGUS-ONTOLOGY-V1.md` e a versao humana da MESMA especificacao, e
`tests/test_ontologia_esofago.py` falha se os dois divergirem.

POR QUE ELE EXISTE
A Fase 12 mediu que o criterio K4 ("definicao do alvo congelada") estava em NAO, e
que era o unico dos quatro criterios de prontidao inteiramente nas maos do projeto —
nao depende de dado novo, de acesso nem de permissao. Sem alvo congelado, comparar
qualquer Dice entre dois mundos mede desacordo de DEFINICAO, nao desempenho.

O QUE ESTA CONGELADO AQUI
 - o alvo e uma MASCARA BINARIA PREENCHIDA: parede + lumen sao UM objeto;
 - a extensao longitudinal e HERDADA DO GT e NAO AVALIAVEL anatomicamente;
 - as oito metricas de segmentacao;
 - as afirmacoes que o projeto NAO pode fazer sobre marcos anatomicos.

A REGRA DE MUDANCA: qualquer alteracao aqui e uma NOVA VERSAO (V2), com data e
motivo, nunca uma edicao silenciosa de V1. `test_ontologia_esofago.py` existe
justamente para tornar a edicao silenciosa impossivel.
"""

from __future__ import annotations

import re
from pathlib import Path

VERSAO = "ESOPHAGUS_ONTOLOGY_V1"
CONGELADA_EM = "2026-09-06"
PROTOCOLO_DE_REFERENCIA = "RTOG 1106"

# --------------------------------------------------------------------------- alvo

ALVO = {
    "nome_vrmed": "esophagus",
    "rotulo_totalsegmentator": "esophagus",
    "rotulo_gt_lctsc": "Esophagus",
    "representacao": "mascara binaria PREENCHIDA (solida)",
    "parede_e_lumen": "NAO SEPARADOS — um unico alvo",
}

INCLUI = (
    "parede esofagica",
    "lumen esofagico (preenchido, nao vazado)",
    "o envelope tecidual definido pelo protocolo " + PROTOCOLO_DE_REFERENCIA,
)

EXCLUI = (
    "conteudo (alimentar, liquido, gasoso) como CLASSE INDEPENDENTE",
    "tecido adiposo periesofagico",
    "estruturas vizinhas (traqueia, aorta, veia azigos, corpo vertebral)",
    "qualquer limite anatomico NAO OBSERVAVEL no exame",
)

# O ponto que mais confunde e por isso esta explicito: o lumen NAO e excluido do
# alvo — ele e preenchido. O que e excluido e o CONTEUDO como classe separada.
NAO_CONFUNDIR = (
    "lumen PREENCHIDO (dentro do alvo) x conteudo como CLASSE (fora do alvo)",
    "excluir gordura periesofagica (fora) x excluir a parede (a parede ESTA dentro)",
)

# ------------------------------------------------------- extensao longitudinal

EXTENSAO_LONGITUDINAL = "HERDADA DO GT / NAO AVALIAVEL ANATOMICAMENTE"

EXTENSAO_JUSTIFICATIVA = (
    "Medido na Fase 9 sobre 30 casos do development: as pontas do GT NAO estao a "
    "deslocamento fixo da carina (IQR 23,5 mm cranial e 13,6 mm caudal, ambos acima "
    "do HD95 de 6,27 mm que se quer medir); as duas pontas sao CORTES e nao "
    "terminacoes (a fatia terminal caudal tem 2,2447x a area mediana do proprio "
    "caso, e em 30/30 fica acima de 1,00x — uma estrutura que acaba anatomicamente "
    "AFINA, esta acaba na largura cheia); e o corte nao vem do campo de visao "
    "(caudal no limite em 0/30, cranial em 1/30)."
)

# Marcos que o projeto NAO demonstra localizar. Afirmar o contrario e regressao.
MARCOS_NAO_LOCALIZAVEIS = ("cricoide", "juncao gastroesofagica")

# Marco que o projeto DEMONSTRA localizar, com o numero que o sustenta.
MARCOS_LOCALIZAVEIS = {
    "carina": "extremo caudal da mascara `trachea` predita; 30/30 casos, estavel em "
              "29/30; desvio mediano 0,00 mm e maximo 3,0 mm sob tres variantes do "
              "detector (medido na Fase 10). NAO e usado como ancora do alvo."
}

# --------------------------------------------------------- limites observaveis

LIMITES_OBSERVAVEIS = (
    "fronteira lateral parede-x-gordura: observavel na janela de mediastino",
    "fronteira com traqueia e aorta: observavel quando ha contraste de densidade",
)

LIMITES_NAO_OBSERVAVEIS = (
    "extremidade cranial (nivel do cricoide)",
    "extremidade caudal (juncao gastroesofagica)",
)

RESOLUCAO = (
    "Grade do LCTSC: 0,977-1,270 mm no plano, dz 2,5-3,0 mm. O piso de resolucao no "
    "plano e 1,953 mm (um voxel de ida e volta).",
    "A parede esofagica tem 3-4 mm e ocupa 1,0-1,6 voxel em Z. Exigir que um modelo "
    "separe parede de lumen nesta grade e exigir o impossivel — e uma das razoes "
    "pelas quais o alvo e preenchido.",
    "Diferencas de largura abaixo de 1,953 mm NAO sao representaveis nesta grade: "
    "medidas ou nao, elas nao existiriam no dado (medido na Fase 10).",
)

# --------------------------------------------------------- metricas congeladas

METRICAS_CONGELADAS = (
    "dice", "iou", "precision", "recall", "hd95", "assd",
    "erro_volume_absoluto", "erro_volume_percentual",
)

METRICAS_REGRA = (
    "Nenhuma metrica pode ser acrescentada como CRITERIO DE APROVACAO sem registrar "
    "a mudanca numa nova versao desta ontologia. Metricas exploratorias podem ser "
    "medidas e publicadas — desde que declaradas exploratorias e fora do criterio."
)

# Toda distancia em MILIMETROS FISICOS. Indice de voxel nunca e medida final.
UNIDADE_DE_DISTANCIA = "mm"

# --------------------------------------------------- relacao com o mundo externo

RELACAO_LCTSC = (
    "O GT do LCTSC declara o esofago pelo atlas " + PROTOCOLO_DE_REFERENCIA + ", "
    "'do nivel abaixo do cricoide a juncao gastroesofagica'. Isso e descricao do "
    "PROTOCOLO DE CONTORNAGEM do GT, nao capacidade do VRmed. O alvo do VRmed "
    "coincide com o do GT em EXTENSAO TOTAL — diferenca de comprimento mediana "
    "0,000 mm, medida — mas por HERANCA, nao por localizacao de marco."
)

RELACAO_BASELINE = (
    "BASELINE_ESOFAGO_V1: TotalSegmentator 2.18.0, task `total`, saida crua, campo "
    "completo, zero pos-processamento. Dice mediano 0,7880 no LCTSC development "
    "(n=30). O baseline NAO e alterado por esta ontologia; ela apenas escreve contra "
    "o que ele e medido."
)

RELACAO_REFERENCIA_HUMANA = (
    "A banda humana publicada (iCurveE, Fase 12) tem vDSC mediano 0,7555 (n=493) "
    "contra uma referencia humana curada, sob o mesmo atlas " + PROTOCOLO_DE_REFERENCIA
    + ". E TETO OTIMISTA, nao piso, e vem de OUTRA coorte, com OUTRO padrao-ouro e "
    "OUTRA grade. A comparacao com o 0,7880 do baseline e de ORDEM DE GRANDEZA e "
    "jamais de contabilidade."
)

# Frases que NENHUM documento do projeto pode conter. O teste de regressao varre
# os .md em busca delas. Cada uma ja foi escrita por engano em alguma fase e
# corrigida — a lista e historico de erro, nao precaucao teorica.
FRASES_PROIBIDAS = (
    "o modelo esta dentro da variabilidade humana",
    "o modelo e melhor que humano",
    "0,7880 supera 0,7555",
    "0.7880 supera 0.7555",
    "o modelo atingiu nivel humano",
    "nivel humano",
    "validado clinicamente",
)

# TERMO CANONICO. "digital twin" NAO e proibido — e proibido como DESCRICAO TECNICA
# ATUAL, porque o VRmed nao modela estado fisiologico nem simulacao. Usar o termo
# para CONTRASTAR ("patient-specific model vs digital twin", "requisitos minimos de
# um digital twin mapeados no VRmed real") e exatamente o uso correto e tem que
# passar. Por isso a regra e de COMPANHIA, nao de ausencia: um documento que fala em
# digital twin precisa tambem falar em patient-specific, senao esta usando o termo
# como se fosse o que o projeto e.
TERMO_CANONICO = "patient-specific 3D model"
TERMO_VIGIADO = "digital twin"
TERMO_ACOMPANHANTE = "patient-specific"

# Afirmacoes de capacidade que o projeto NAO tem. Regex, aplicado ao texto
# normalizado (sem acento, minusculo).
PADROES_DE_REGRESSAO = (
    (r"pipeline\s+localiza\s+(?:o\s+|a\s+)?cricoide",
     "afirma que o pipeline localiza o cricoide — ele nao localiza"),
    (r"pipeline\s+localiza\s+(?:a\s+)?juncao\s+gastroesofagica",
     "afirma que o pipeline localiza a juncao gastroesofagica — ele nao localiza"),
    (r"vrmed\s+adota:?\s*cricoide",
     "readota o cricoide como limite do VRmed — removido na Fase 9 por nao ser observavel"),
    (r"limite\s+superior\s*\|?\s*\*{0,2}(?:o\s+)?cricoide",
     "reintroduz 'limite superior = cricoide' como criterio do VRmed"),
    # Conjugacao livre de proposito: a primeira versao usava apenas "separar" e o
    # controle positivo do teste 12 flagrou que "separamos parede e lumen" passava
    # limpo. O verbo aqui aparece em qualquer forma.
    (r"separa\w*\s+(?:a\s+)?parede\s+e\s+(?:o\s+)?lumen"
     r"|parede\s+e\s+(?:o\s+)?lumen\s+(?:em\s+)?(?:duas\s+)?(?:class|separad)",
     "propoe separar parede e lumen — o alvo V1 e preenchido e unico"),
)


def _normalizar(texto: str) -> str:
    """Minusculas sem acento — para o crivo nao depender de grafia."""
    import unicodedata
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def varrer_documento(caminho: Path) -> list[str]:
    """Devolve as violacoes encontradas num .md. Lista vazia = documento limpo.

    IMPORTANTE — o que NAO e violacao: citar a frase proibida para PROIBI-LA.
    Todo relatorio desta serie tem uma secao "frases proibidas", e ela precisa
    escrever a frase para bani-la. A heuristica: uma linha que contenha marca de
    negacao (NAO, NUNCA, proibid, ~~) esta banindo, nao afirmando.
    """
    bruto = caminho.read_text(encoding="utf-8", errors="replace")
    achados = []
    for i, linha in enumerate(bruto.splitlines(), 1):
        n = _normalizar(linha)
        # Uma linha que BANE a frase precisa escreve-la. Marcadores de negacao —
        # inclusive "**nao**" com enfase markdown e o proprio X vermelho das listas
        # de frases proibidas, que eram os dois falsos positivos da primeira versao.
        sem_enfase = n.replace("*", "").replace("_", "").replace("`", "")
        negando = ("❌" in linha) or any(
            m in sem_enfase for m in ("nao ", "nunca", "proibid", "~~", "jamais",
                                      "evite", "nao e", "nao pode", "nao dizer",
                                      "sem sugerir", "frases proibidas"))
        for frase in FRASES_PROIBIDAS:
            if _normalizar(frase) in n and not negando:
                achados.append(f"{caminho.name}:{i} frase proibida: '{frase}'")
        for padrao, motivo in PADROES_DE_REGRESSAO:
            if re.search(padrao, n) and not negando:
                achados.append(f"{caminho.name}:{i} regressao: {motivo}")
    return achados


def checar_termo(caminho: Path) -> list[str]:
    """Higiene de termo: `digital twin` so passa acompanhado de `patient-specific`."""
    n = _normalizar(caminho.read_text(encoding="utf-8", errors="replace"))
    if TERMO_VIGIADO in n and TERMO_ACOMPANHANTE not in n:
        return [f"{caminho.name}: usa '{TERMO_VIGIADO}' sem nenhuma mencao a "
                f"'{TERMO_ACOMPANHANTE}' — o termo canonico atual e "
                f"'{TERMO_CANONICO}'; o VRmed nao modela estado fisiologico"]
    return []


def varrer_docs(raiz: Path = Path("docs")) -> dict:
    """Varre todos os .md de docs/ e devolve o mapa de violacoes."""
    violacoes = {}
    for md in sorted(raiz.rglob("*.md")):
        v = varrer_documento(md) + checar_termo(md)
        if v:
            violacoes[str(md)] = v
    return {"n_documentos": len(list(raiz.rglob("*.md"))),
            "n_com_violacao": len(violacoes), "violacoes": violacoes}


def resumo() -> dict:
    """A especificacao inteira, serializavel — para o documento e para os testes."""
    return {
        "versao": VERSAO, "congelada_em": CONGELADA_EM,
        "protocolo": PROTOCOLO_DE_REFERENCIA, "alvo": ALVO,
        "inclui": list(INCLUI), "exclui": list(EXCLUI),
        "extensao_longitudinal": EXTENSAO_LONGITUDINAL,
        "marcos_nao_localizaveis": list(MARCOS_NAO_LOCALIZAVEIS),
        "marcos_localizaveis": MARCOS_LOCALIZAVEIS,
        "limites_observaveis": list(LIMITES_OBSERVAVEIS),
        "limites_nao_observaveis": list(LIMITES_NAO_OBSERVAVEIS),
        "resolucao": list(RESOLUCAO),
        "metricas_congeladas": list(METRICAS_CONGELADAS),
        "unidade_de_distancia": UNIDADE_DE_DISTANCIA,
        "relacao_lctsc": RELACAO_LCTSC, "relacao_baseline": RELACAO_BASELINE,
        "relacao_referencia_humana": RELACAO_REFERENCIA_HUMANA,
    }


if __name__ == "__main__":
    import json
    import sys

    if "--varrer" in sys.argv:
        r = varrer_docs()
        print(f"documentos varridos: {r['n_documentos']} · com violacao: {r['n_com_violacao']}")
        for arq, vs in r["violacoes"].items():
            print(f"\n{arq}")
            for v in vs:
                print("   ", v)
        raise SystemExit(1 if r["n_com_violacao"] else 0)
    print(json.dumps(resumo(), indent=2, ensure_ascii=False))
