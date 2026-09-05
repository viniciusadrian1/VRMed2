"""Fase 9, Partes F/G/H/I — protocolo de treino, tabela pre-treino, criterios e
controles anti-vazamento do esofago.

NAO TREINA. NAO BAIXA. NAO LE validation nem test. Roda seco: a Parte H le o CSV
do baseline JA MEDIDO e o autoteste usa dado sintetico.

------------------------------------------------------------------------------
PARTE F — protocolo (registro, nao otimizacao)

`PROTOCOLO` fixa input, target, spacing, patch, batch, loss, augmentation,
folds, semente, criterio de selecao, early stopping, hardware e tempo. Cada item
tem VALOR e JUSTIFICATIVA, e a justificativa cita numero JA MEDIDO (fase 5, 6, 7
e 9) ou declara `nao medido`. Nada aqui foi escolhido depois de ver desempenho —
nao ha desempenho para ver: o modelo nao existe.

O protocolo e CANDIDATO e CONDICIONAL. Ele descreve o que seria feito SE a
Parte I autorizasse. Ela nao autoriza (ver DECISAO no fim do arquivo).

------------------------------------------------------------------------------
PARTE H — tabela pre-treino

Linhas do baseline preenchidas a partir de
`fase7/esofago/baseline/baseline_esofago.csv` — LIDAS do disco, nunca
redigitadas. Linhas do modelo em branco (`nao medido`), porque nao existe
modelo. Metricas de distancia em mm fisicos; volume em mL e em % do GT.

------------------------------------------------------------------------------
PARTE G — as DUAS perguntas, que nao sao a mesma

  (i)  o novo modelo SUPERA o baseline?
  (ii) o resultado GENERALIZA, ou e efeito de dominio?

Podem ter respostas opostas, e a fase 6 mediu exatamente o mecanismo que faz
isso acontecer: instituicao explica ESTILO de contorno (ICC1 0,5098 e 0,4719,
p 0,0005) e NAO explica anatomia (0,0788 / 0,0275 / -0,0762). Um modelo treinado
em contorno RTOG 1106 pode ganhar em (i) por ter aprendido a CONVENCAO, e perder
em (ii) por nao ter aprendido a estrutura. Os limiares de (i) sao os congelados
da fase 5, importados daqui — nao reescritos.

------------------------------------------------------------------------------
PARTE I — controles anti-vazamento, como CODIGO

Dez guardas. Cada uma:
  - recusa levantando uma excecao propria (duas sao REUSO: `ProcedenciaInvalida`
    do dataset_esofago e `DesalinhamentoGeometrico` da geometria);
  - tem no autoteste um caso legitimo que PASSA e um CONTROLE POSITIVO que
    DERRUBA;
  - pode ser desligada por nome, e `verificar_por_mutacao` desliga uma por uma e
    exige que o autoteste CAIA. Guarda que nao derruba o teste quando desligada
    nao esta guardando nada — isso ja aconteceu sete vezes nesta base, sempre
    com a metrica e nunca com o pipeline.

O caminho desligado devolve `recusou: False` com a mesma chave do caminho
legitimo, de proposito: assim o unico assert que pode cair sob mutacao e o do
controle positivo, e nao um KeyError no caminho feliz. Um teste que cai pelo
motivo errado nao prova nada.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.protocolo_esofago --autoteste
    python -m scripts.validation.tier2.protocolo_esofago --mutacao
    python -m scripts.validation.tier2.protocolo_esofago
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import fase5, geometria  # noqa: E402
from scripts.validation.tier2.dataset_esofago import (  # noqa: E402
    PLANO_SUPERAJUSTE,
    Procedencia,
    ProcedenciaInvalida,
)

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase9" / "protocolo"
BASELINE_CSV = RAIZ_PADRAO / "fase7" / "esofago" / "baseline" / "baseline_esofago.csv"

NM = "nao medido"
NA = "nao aplicavel"

IGNORE = 255          # rotulo de "nao anotado" do SAROS; convencao herdada da fase 8
FOREGROUND = 255      # convencao do dcmrtstruct2nii para mascara binaria gravada


# ====================================================== PARTE F — o protocolo


# Medidos e citados, nao remedidos aqui. Fonte de cada um no campo `fonte`.
MEDIDOS = {
    "voxels_positivos_development": (488_710, "fase 6, 30 casos"),
    "volume_gt_mediano_ml": (40.64, "fase 6"),
    "parametros_da_rede_de_hoje": (31_214_109, "fase 6, dois caminhos independentes"),
    "voxel_por_parametro": (0.0157, "fase 6"),
    "fracao_positiva_em_patch_128": (0.0072, "fase 6, esofago inteiro num patch 128^3"),
    "espessura_caracteristica_mm": (9.33, "fase 9, representabilidade"),
    "dz_mediano_mm": (2.5, "fase 9, development"),
    "dx_mm": (0.976562, "fase 7/9, in-plane em 30/30"),
    "erro_cranial_mm": (-3.0, "fase 7: em 18/30 a predicao para ANTES do GT"),
    "erro_distal_mm": (6.0, "fase 7: em 23/30 a predicao PASSA do GT"),
    "decomposicao_do_erro": (
        {"extensao": 0.2119, "localizacao": 0.1355, "residual_de_fronteira": 0.6526},
        "fase 7",
    ),
    "icc1_estilo": ((0.5098, 0.4719), "fase 6, p 0,0005 — instituicao explica estilo"),
    "icc1_anatomia": ((0.0788, 0.0275, -0.0762), "fase 6 — instituicao NAO explica anatomia"),
    "custo_do_passo_s": (0.453, "fase 6, patch 128^3 batch 2 AMP fp16"),
    "memoria_do_passo_mib": (4811, "fase 6, alocados; 6.730 reservados"),
    "vram_total_mib": (16_380, "fase 6, RTX 4060 Ti"),
    "horas_por_fold": (31.5, "fase 6, limite INFERIOR: so o passo da rede"),
    "horas_5_folds": (157.5, "fase 6, 6,6 dias"),
}


def _item(valor: Any, justificativa: str, fonte: str = "esta fase") -> dict[str, Any]:
    return {"valor": valor, "justificativa": justificativa, "fonte": fonte}


PROTOCOLO: dict[str, Any] = {
    "id": "PROTOCOLO_ESOFAGO_CANDIDATO_V1",
    "estado": "CANDIDATO E CONDICIONAL — registrado antes de existir treino, e nao autorizado",
    "candidato": "nnU-Net v2 (nnunetv2 2.8.1), configuracao 3d_fullres",
    "porque_nnunet": _item(
        "nnunetv2 2.8.1",
        "ja instalado como dependencia do TotalSegmentator; MONAI ausente. Escolher nnU-Net "
        "custa ZERO dependencia nova. E o comparador (TotalSegmentator) e ele proprio nnU-Net, "
        "entao a diferenca medida seria de DADO e de especializacao, nao de arquitetura — "
        "trocar a arquitetura junto confundiria as duas causas num experimento so.",
        "fase 6 secao 8",
    ),
    "input": _item(
        "TC de campo completo, 1 canal, HU cruas, sem recorte nosso",
        "e exatamente o que o BASELINE_ESOFAGO_V1 recebe (saida CRUA, campo completo). "
        "Qualquer recorte nosso na entrada tornaria a comparacao com o baseline uma "
        "comparacao entre dois pre-processamentos, nao entre dois modelos. A normalizacao de "
        "intensidade fica a cargo do fingerprint do nnU-Net (CT: clip nos percentis do "
        "foreground + z-score global), que e parte da configuracao e nao escolha nossa.",
    ),
    "target": _item(
        "binario, 1 classe: Esophagus, corpo MACICO (parede + lumen juntos)",
        "o GT e macico — `fill_holes` 2D preencheu 0,0000 mL em 30/30 — e a parede de 3-4 mm "
        "ocupa 1,0-1,6 voxel em Z, entao a distincao parede/lumen NAO e representavel nesta "
        "grade. Um target de 2 classes pediria uma fronteira que nem o GT nem a grade tem.",
        "fase 7 e fase 9",
    ),
    "extensao_longitudinal_do_target": _item(
        "HERDADA do GT e declarada NAO AVALIAVEL",
        "fase 9 mediu: as duas pontas do GT sao CORTES na largura cheia (fatia terminal caudal "
        "com 2,2447x a area mediana do proprio caso, 30/30 acima de 1,00x) e nao vem da "
        "aquisicao (0/30 caudal no limite do campo). Nao ha deslocamento fixo em relacao a "
        "carina (IQR 23,5 mm cranial, 13,6 mm caudal, contra HD95 mediano de 6,27 mm). "
        "Consequencia direta para o treino: 0,2119 do erro decomposto e EXTENSAO, e essa "
        "parcela NAO deve ser otimizada nem citada como fidelidade.",
        "fase 9 Parte A + fase 7",
    ),
    "spacing": _item(
        "definido pelo fingerprint do nnU-Net sobre o conjunto de TREINO; nesta coorte a "
        "mediana e 0,9766 x 0,9766 x 2,5 mm",
        "NAO reamostrar para isotropico. Com a espessura caracteristica em 9,33 mm e a parede "
        "presumida em 3-4 mm ocupando 1,0-1,6 voxel em Z, subir a resolucao em Z INVENTA "
        "fronteira que o anotador nao desenhou; descer destroi o pouco que existe. O spacing "
        "esta confundido com instituicao (S1 dz 3,0; S2 dz 2,5), entao ele tambem e uma "
        "variavel do experimento e nao so um parametro.",
        "fase 9 + fase 6",
    ),
    "patch": _item(
        "128 x 128 x 128 voxels",
        "e o unico patch com CUSTO MEDIDO nesta maquina (0,453 s/passo, 4.811 MiB). Em "
        "2,5 mm cobre 320 mm em Z — o esofago inteiro cabe. Consequencia medida e desagradavel: "
        "mesmo com o esofago inteiro dentro, so 0,72 % do patch e positivo.",
        "fase 6",
    ),
    "amostragem_de_patch": _item(
        "fracao forcada de patches centrados em voxel positivo (o oversample do nnU-Net)",
        "0,72 % de positivo por patch. Amostragem uniforme entrega quase so fundo e o modelo "
        "aprende a prever vazio — que e o otimo local mais barato que existe para esta razao.",
        "fase 6; reuso de PLANO_SUPERAJUSTE",
    ),
    "batch": _item(
        2,
        "medido cabendo em 4.811 MiB alocados de 16.380 disponiveis. Nao aumentado sem medir: "
        "trocar batch muda o ruido do gradiente e a normalizacao, e viraria uma segunda "
        "variavel no mesmo experimento.",
        "fase 6",
    ),
    "loss": _item(
        "Dice + CrossEntropy com deep supervision (padrao do nnU-Net)",
        "o padrao NAO foi trocado de proposito: nao ha nenhuma medida nesta base que aponte "
        "uma loss melhor para este alvo, e trocar sem medida e escolher antes de saber. O "
        "termo Dice e o que segura o desequilibrio de 0,72 %; um ajuste de loss so entra "
        "depois que a curva de aprendizado mostrar QUE tipo de erro sobrou.",
    ),
    "augmentation": _item(
        PLANO_SUPERAJUSTE["augmentation"],
        "REUSO integral do plano ja escrito em dataset_esofago.PLANO_SUPERAJUSTE. Os dois "
        "vetos que importam sao medidos: espelhamento E-D ensina uma anatomia que nao existe "
        "(o mediastino nao e simetrico), e recorte agressivo da ponta treina o modelo a errar "
        "onde ele JA erra (erro cranial -3,0 mm em 18/30, distal +6,0 mm em 23/30).",
        "dataset_esofago.PLANO_SUPERAJUSTE",
    ),
    "folds": _item(
        "5-fold CV por CASO no conjunto de treino + 3 dobras leave-one-institution-out",
        "cinco dobras respondem (i); as tres dobras por instituicao respondem (ii), e so elas. "
        "Divisao por CASO, nunca por fatia: sao 86,5 fatias por caso na mediana e fatias "
        "vizinhas a 2,5-3,0 mm sao quase a mesma imagem. Com 3 instituicoes as dobras de (ii) "
        "sao 3 — reportar as tres, nunca a media.",
        "PLANO_SUPERAJUSTE + fase 9 Parte C (S1=MAASTRO, S2=MDACC, S3=MSKCC)",
    ),
    "seed": _item(
        "uma semente fixa, declarada e gravada por rodada",
        "e obrigatoria para reproduzir, e NAO e suficiente para concluir: uma semente so nao "
        "mede a variacao entre execucoes. Consequencia declarada antes: uma margem menor que "
        "a dispersao entre sementes nao e resultado. Quantas sementes serao rodadas e o custo "
        "que decide, e o custo esta medido em 31,5 h por fold.",
    ),
    "criterio_de_selecao": _item(
        "Dice de validacao agregado por CASO; checkpoint do melhor valor, nunca o da ultima epoca",
        "REUSO de PLANO_SUPERAJUSTE.monitorar. HD95 de validacao e obrigatorio ao lado, porque "
        "o modo de erro conhecido do esofago e de extensao e fronteira (0,2119 + 0,6526 da "
        "decomposicao) e o Dice de um tubo fino se move pouco com erro que o HD95 enxerga.",
        "PLANO_SUPERAJUSTE + fase 7",
    ),
    "early_stopping": _item(
        PLANO_SUPERAJUSTE["early_stopping"],
        "REUSO integral. A paciencia de 0,005 e metade do LIMIAR_MELHORIA_DICE=0,01 da fase 5, "
        "que veio da meia-largura medida dos IC 95 % da coorte (0,005 a 0,031).",
        "dataset_esofago.PLANO_SUPERAJUSTE + fase5",
    ),
    "hardware": _item(
        "RTX 4060 Ti, 16.380 MiB; i5-12400F; 31,8 GiB RAM",
        "medido, nao estimado. O passo de 128^3 batch 2 AMP ocupa 4.811 MiB alocados / "
        "6.730 reservados — cabe com folga.",
        "fase 6 secao 8",
    ),
    "tempo_estimado": _item(
        {"por_fold_h": 31.5, "cinco_folds_h": 157.5, "cinco_folds_dias": 6.6,
         "mais_3_dobras_por_instituicao_h": 94.5, "total_se_tudo_rodar_h": 252.0},
        "0,453 s/passo x schedule padrao. Sao LIMITES INFERIORES: medem so o passo da rede, "
        "sem dataloader e sem augmentation. As 3 dobras leave-one-institution-out custam mais "
        "94,5 h, e sao elas que respondem a pergunta (ii) — o orcamento de (ii) e maior que "
        "metade do de (i), o que e a forma financeira de dizer que (ii) e a pergunta cara.",
        "fase 6 + aritmetica desta fase",
    ),
    "o_que_o_protocolo_NAO_define": [
        "o conjunto de TREINO — nao existe fonte aprovada (Parte D)",
        "o conjunto de TESTE — nao existe fonte independente aprovada (Parte D e guarda 1)",
        "numero de epocas do schedule — depende do treino que nao foi autorizado",
        "quantas sementes — depende do orcamento, que depende da autorizacao",
    ],
}


# ================================================= PARTE G — as duas perguntas


CRITERIOS: dict[str, Any] = {
    "congelados_da_fase5_importados_nao_reescritos": {
        "limiar_melhoria_dice": fase5.LIMIAR_MELHORIA_DICE,
        "limiar_regressao_dice": fase5.LIMIAR_REGRESSAO_DICE,
        "limiar_regressao_hd95_mm": fase5.LIMIAR_REGRESSAO_HD95_MM,
        "limiar_regressao_volume_pct": fase5.LIMIAR_REGRESSAO_VOLUME_PCT,
        "controles_de_nao_regressao": list(fase5.CONTROLES),
        "de_onde_vem_o_0_01": (
            "meia-largura medida dos IC 95 % da mediana na coorte publicada: 0,005 (Lung_R) a "
            "0,031 (SpinalCord). Efeito abaixo de 0,01 esta dentro do IC de metade das "
            "estruturas e nao e discriminavel com n desta ordem."
        ),
    },
    "pergunta_i": {
        "enunciado": "o novo modelo supera o BASELINE_ESOFAGO_V1?",
        "e_uma_pergunta_sobre": "casos — este modelo e melhor que aquele NESTE dominio?",
        "como_seria_respondida": [
            "comparacao PAREADA por caso: mesmo caso, mesma grade, mesma metrica, os dois "
            "modelos. Pareada porque a variacao entre casos (dice 0,4849 a 0,8761) e muito "
            "maior que o efeito procurado (0,01) — nao pareado, o ruido entre casos engole tudo.",
            "delta de Dice mediano > +0,01 (LIMIAR_MELHORIA_DICE) E delta de HD95 que nao piore "
            "mais que 1,0 mm. As DUAS, porque 0,2119 + 0,6526 do erro decomposto vive em "
            "extensao e fronteira, que o Dice de um tubo fino quase nao ve.",
            "sem regressao nos controles Lung_R e Lung_L alem dos limiares congelados.",
            "reportar a distribuicao inteira, nao so a mediana: a cauda do baseline vai de "
            "dice 0,4849 e hd95 38,62 mm, e um modelo que so melhora a mediana e um modelo que "
            "nao mexeu na cauda que importa.",
        ],
        "com_que_dado": (
            "um conjunto que NUNCA escolheu nada: nem checkpoint, nem early stopping, nem "
            "augmentation, nem hiperparametro. No LCTSC esse conjunto era o `test` (15 casos) "
            "e ele esta GASTO — foi lido na fase 7 pela hipotese heart->pericardium. Uma "
            "leitura agora seria a SEGUNDA, e a segunda leitura de um holdout nao e um holdout."
        ),
        "estado_hoje": "NAO RESPONDIVEL — nao ha conjunto que satisfaca 'nunca escolheu nada'",
    },
    "pergunta_ii": {
        "enunciado": "o resultado generaliza, ou e efeito de dominio?",
        "e_uma_pergunta_sobre": "convencoes — o modelo aprendeu a estrutura ou aprendeu o estilo?",
        "porque_pode_dar_o_OPOSTO_de_i": (
            "a fase 6 mediu que instituicao explica ESTILO de contorno (ICC1 0,5098 e 0,4719, "
            "p 0,0005) e NAO explica anatomia (0,0788 / 0,0275 / -0,0762, p 0,16-0,74). Um "
            "modelo treinado em contorno RTOG 1106 pode subir em (i) por ter decorado a "
            "CONVENCAO do atlas — inclusive as pontas, que a fase 9 mostrou serem CORTES e nao "
            "anatomia — e cair em (ii) por nao ter aprendido a estrutura. (i) alto com (ii) "
            "baixo NAO e um modelo bom com um teste ruim: e um modelo que aprendeu a coisa errada."
        ),
        "como_seria_respondida": [
            "leave-one-institution-out: treinar sem S1, avaliar em S1; idem S2 e S3. Reportar "
            "as tres dobras separadas, nunca a media — a media esconde a dobra que caiu.",
            "avaliacao numa fonte com outra CONVENCAO de contorno e outra instituicao. E este "
            "o teste que responde (ii); o leave-one-institution-out sozinho nao responde, "
            "porque as tres instituicoes compartilham o mesmo atlas RTOG 1106 declarado pelo "
            "TCIA — sao tres maos, uma convencao.",
            "queda maior que o LIMIAR_MELHORIA_DICE entre a dobra vista e a nao vista ja "
            "responde 'efeito de dominio', com o mesmo 0,01 dos dois lados por simetria.",
        ],
        "confundimento_declarado_antes": (
            "instituicao e spacing estao confundidos: S1 dz 3,0 mm em 20/20, S2 dz 2,5 mm em "
            "20/20, so S3 varia. Uma dobra que caia mede instituicao OU spacing e esta coorte "
            "NAO separa os dois. Isso e parte do resultado, nao uma ressalva de rodape."
        ),
        "com_que_dado": (
            "fonte externa com GT humano, licenca confirmada, contorno de outra convencao e "
            "independencia do treino do comparador. A Parte D varreu 156 colecoes do TCIA e "
            "nao achou uma que passe nos quatro filtros ao mesmo tempo."
        ),
        "estado_hoje": "NAO RESPONDIVEL — nao ha fonte externa aprovada",
    },
    "porque_as_duas_precisam_estar_separadas": (
        "sao perguntas com sujeitos diferentes: (i) e sobre casos e (ii) e sobre convencoes. "
        "Responder (i) e anunciar (ii) e o erro classico desta area, e nesta base ele teria "
        "suporte numerico para acontecer — 0,6526 do erro e residual de fronteira, e a "
        "atribuicao desse residual a 'convencao de contorno' JA FOI REFUTADA uma vez pelo "
        "controle positivo (o regime e uma EROSAO uniforme, assinatura de erro de modelo). "
        "Um instrumento que ja errou uma vez nesse ponto nao ganha o beneficio da duvida."
    ),
}


# ======================================== PARTE I — guardas (codigo, nao prosa)


class RecusaDeProtocolo(RuntimeError):
    """Base de todas as recusas desta fase — permite `except RecusaDeProtocolo`."""


class TestNaoDefinido(RecusaDeProtocolo):
    """Nao ha conjunto de teste declarado antes do treino."""


class TestGasto(RecusaDeProtocolo):
    """O conjunto de teste do LCTSC ja foi lido — uma leitura agora seria a segunda."""


class VazamentoEntreConjuntos(RecusaDeProtocolo):
    """O mesmo caso aparece em dois conjuntos."""


class CasoRepetido(RecusaDeProtocolo):
    """O mesmo case_id aparece duas vezes na mesma lista."""


class LicencaNaoConfirmada(RecusaDeProtocolo):
    """A licenca do dataset nao foi lida na fonte, ou e conflitante, ou proibe o uso."""


class MascaraForaDaGrade(RecusaDeProtocolo):
    """A mascara nao esta na grade declarada — comparar seria comparar outra coisa."""


class AvaliacaoSobreIgnore(RecusaDeProtocolo):
    """A metrica esta sendo calculada sobre voxels que o anotador NAO anotou."""


class DefinicoesIncompativeis(RecusaDeProtocolo):
    """As duas definicoes anatomicas nao descrevem o mesmo objeto."""


# Excecoes REUSADAS, nao reimplementadas:
#   ProcedenciaInvalida      — dataset_esofago (gt_humano)
#   DesalinhamentoGeometrico — geometria (affine/zooms/shape/orientacao)
DesalinhamentoGeometrico = geometria.DesalinhamentoGeometrico

GUARDAS = (
    "test_definido",
    "test_intocado",
    "gt_humano",
    "conjuntos_disjuntos",
    "sem_repeticao",
    "licenca_confirmada",
    "affine_compativel",
    "mascara_na_grade",
    "fora_de_ignore",
    "definicao_compativel",
)

# Mecanismo de MUTACAO. Vazio em operacao normal; `verificar_por_mutacao` mexe
# aqui e devolve ao estado anterior num `finally`.
_DESLIGADAS: set[str] = set()


def _desligada(nome: str) -> dict[str, Any] | None:
    """Devolve o resultado neutro se a guarda estiver desligada, senao None.

    O resultado neutro tem a MESMA chave `recusou` do caminho legitimo para que,
    sob mutacao, o unico assert capaz de cair seja o do controle positivo.
    """
    if nome in _DESLIGADAS:
        return {"guarda": nome, "estado": "DESLIGADA", "recusou": False}
    return None


def _ok(nome: str, **extra: Any) -> dict[str, Any]:
    return {"guarda": nome, "estado": "ativa", "recusou": False, **extra}


# ------------------------------------------------------------------ guarda 1

CONJUNTOS_OBRIGATORIOS = ("development", "validation", "test")


def exigir_test_definido(split: dict[str, list[str]]) -> dict[str, Any]:
    """Guarda 1 — treino sem TEST definido ANTES: recusa.

    Um teste definido depois do treino nao e teste, e escolha. Exige as tres
    chaves presentes e nao vazias.
    """
    if (r := _desligada("test_definido")) is not None:
        return r
    faltando = [k for k in CONJUNTOS_OBRIGATORIOS if not split.get(k)]
    if faltando:
        raise TestNaoDefinido(
            f"conjunto(s) ausente(s) ou vazio(s): {faltando}. Treinar sem TEST declarado antes "
            "significa escolher o teste depois de ver o resultado — o holdout nao existe."
        )
    return _ok("test_definido", n={k: len(split[k]) for k in CONJUNTOS_OBRIGATORIOS})


# ------------------------------------------------------------------ guarda 2

# Registro de conjuntos JA LIDOS. Ler de novo nao e ler pela primeira vez.
CONJUNTOS_GASTOS: dict[str, str] = {
    "LCTSC/test": (
        "lido na fase 7 pela hipotese heart->pericardium. Uma leitura para o esofago agora "
        "seria a SEGUNDA leitura do mesmo holdout, e a segunda leitura nao e holdout."
    ),
}


def exigir_test_intocado(
    casos: list[str],
    papel: str,
    split: dict[str, list[str]],
    rotulo: str = "LCTSC/test",
) -> dict[str, Any]:
    """Guarda 2 — treino (ou reteste) usando o LCTSC test: recusa.

    Duas recusas pelo mesmo motivo, em direcoes opostas:
      - papel de treino/validacao tocando o `test`  -> vazamento;
      - papel de teste apontando para um conjunto JA GASTO -> segunda leitura.
    """
    if (r := _desligada("test_intocado")) is not None:
        return r
    contaminados = sorted(set(casos) & set(split.get("test", [])))
    if papel in ("treino", "validacao") and contaminados:
        raise TestGasto(
            f"{len(contaminados)} caso(s) do conjunto `test` em papel de {papel}: "
            f"{contaminados[:5]}{'...' if len(contaminados) > 5 else ''}. "
            "Um caso usado para ajustar qualquer coisa nao pode medir nada depois."
        )
    if papel == "teste" and rotulo in CONJUNTOS_GASTOS and contaminados:
        raise TestGasto(f"{rotulo} esta GASTO: {CONJUNTOS_GASTOS[rotulo]}")
    return _ok("test_intocado", papel=papel, n_casos=len(casos))


# ------------------------------------------------------------------ guarda 3


def exigir_gt_humano(procedencias: list[dict[str, Any]]) -> dict[str, Any]:
    """Guarda 3 — GT nao humano: recusa. REUSO de dataset_esofago.Procedencia.

    Nao reimplementa a regra: constroi a `Procedencia`, cujo `__post_init__` ja
    levanta `ProcedenciaInvalida` quando `gt_humano` nao e exatamente True.
    Reimplementar aqui criaria uma segunda porta com outra tranca.
    """
    if (r := _desligada("gt_humano")) is not None:
        return r
    for p in procedencias:
        Procedencia(**p)          # levanta ProcedenciaInvalida
    return _ok("gt_humano", n=len(procedencias))


# ------------------------------------------------------------------ guarda 4


def exigir_conjuntos_disjuntos(conjuntos: dict[str, list[str]]) -> dict[str, Any]:
    """Guarda 4 — caso presente em treino E teste: recusa."""
    if (r := _desligada("conjuntos_disjuntos")) is not None:
        return r
    nomes = sorted(conjuntos)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            comum = sorted(set(conjuntos[a]) & set(conjuntos[b]))
            if comum:
                raise VazamentoEntreConjuntos(
                    f"{len(comum)} caso(s) em `{a}` E `{b}`: "
                    f"{comum[:5]}{'...' if len(comum) > 5 else ''}. "
                    "Medir num caso ja visto mede memorizacao, nao generalizacao."
                )
    return _ok("conjuntos_disjuntos", pares_verificados=len(nomes) * (len(nomes) - 1) // 2)


# ------------------------------------------------------------------ guarda 5


def exigir_sem_repeticao(casos: list[str], rotulo: str = "conjunto") -> dict[str, Any]:
    """Guarda 5 — caso repetido: recusa.

    LIMITE DECLARADO: pega repeticao de IDENTIFICADOR. NAO pega o mesmo corpo
    sob dois identificadores diferentes — a fase 9 Parte C mostrou que UID e
    PatientID zerados entre colecoes sao artefato de reanonimizacao e NAO
    evidencia de independencia. Essa deteccao nao existe neste pipeline.
    """
    if (r := _desligada("sem_repeticao")) is not None:
        return r
    vistos: set[str] = set()
    repetidos = sorted({c for c in casos if c in vistos or vistos.add(c)})  # type: ignore[func-returns-value]
    if repetidos:
        raise CasoRepetido(
            f"case_id repetido em `{rotulo}`: {repetidos}. Caso duplicado pesa dobrado na "
            "media e desbalanceia o split sem aparecer em lugar nenhum."
        )
    return _ok("sem_repeticao", n=len(casos), rotulo=rotulo)


# ------------------------------------------------------------------ guarda 6

# LIDAS NA FONTE por esta base (fase 6, fase 8 e fase 9 Parte D). Ausencia do
# dataset neste registro E recusa: nao ha padrao permissivo.
LICENCAS: dict[str, dict[str, Any]] = {
    "LCTSC": {"licenca": "CC BY 3.0", "confirmada": True, "onde": "API do TCIA",
              "restricao": None},
    "NSCLC-Radiomics": {"licenca": "CC BY-NC 3.0", "confirmada": True, "onde": "pagina do TCIA",
                        "restricao": "NC — uso nao comercial"},
    "TotalSegmentator (Zenodo 6802613)": {"licenca": "CC BY 4.0", "confirmada": True,
                                          "onde": "Zenodo", "restricao": None},
    "SAROS": {"licenca": "CC BY 4.0", "confirmada": True, "onde": "pagina do TCIA",
              "restricao": "anotacao esparsa: ~21 % das fatias, resto e ignore (255)"},
    "Pediatric-CT-SEG": {"licenca": "CC BY 4.0", "confirmada": True, "onde": "pagina do TCIA",
                         "restricao": None},
    "HaN-Seg": {"licenca": "CC BY-NC-ND 4.0", "confirmada": True, "onde": "Zenodo 7442914",
                "restricao": "clausula ND; leitura nossa da licenca, nao parecer juridico"},
    "4D-Lung": {"licenca": "CC BY 3.0", "confirmada": True, "onde": "pagina do TCIA",
                "restricao": None},
    "AMOS22": {"licenca": "conflitante: CC BY 4.0 no Zenodo x CC BY-NC-SA no artigo",
               "confirmada": False, "onde": "Zenodo e artigo", "restricao": "conflito nao resolvido"},
    "SegTHOR": {"licenca": "DUA proibe redistribuicao", "confirmada": True, "onde": "DUA",
                "restricao": "PROIBE — cadastro, termo assinado e aprovacao humana"},
    "StructSeg2019": {"licenca": None, "confirmada": False, "onde": "grand-challenge",
                      "restricao": "nenhuma licenca publicada"},
    "SegRap2023": {"licenca": None, "confirmada": False, "onde": "pagina do desafio",
                   "restricao": "End User Agreement assinada + senha por e-mail; sem licenca publicada"},
    "WORD": {"licenca": "conflitante: GPLv3 no repo x 'not for second-development'",
             "confirmada": False, "onde": "repositorio e README",
             "restricao": "acesso humano-dependente (e-mail + senha do autor)"},
    "BTCV": {"licenca": None, "confirmada": False, "onde": "Synapse",
             "restricao": "licenca NAO lida na fonte por esta base"},
    "RAOS": {"licenca": None, "confirmada": False, "onde": NM,
             "restricao": "licenca NAO lida na fonte por esta base"},
    "Ensaios cooperativos NCI (S0819, EAY131, RTOG-0617, ...)": {
        "licenca": "NIH Controlled Data Access Policy", "confirmada": True, "onde": "TCIA",
        "restricao": "PROIBE — download com login nao disponivel via TCIA hoje"},
}


def exigir_licenca_confirmada(dataset: str) -> dict[str, Any]:
    """Guarda 6 — dataset sem licenca confirmada: recusa.

    Ausencia do registro tambem recusa. Um dataset que ninguem leu a licenca nao
    e um dataset permitido, e um dataset nao verificado.
    """
    if (r := _desligada("licenca_confirmada")) is not None:
        return r
    reg = LICENCAS.get(dataset)
    if reg is None:
        raise LicencaNaoConfirmada(
            f"{dataset!r} nao esta em LICENCAS. Ausencia nao e permissao: a licenca precisa "
            "ter sido LIDA na fonte e registrada antes do dataset entrar."
        )
    if not reg["confirmada"] or reg["licenca"] is None:
        raise LicencaNaoConfirmada(
            f"{dataset}: licenca nao confirmada ({reg['licenca']!r}; {reg['restricao']})."
        )
    if reg["restricao"] and str(reg["restricao"]).startswith("PROIBE"):
        raise LicencaNaoConfirmada(f"{dataset}: {reg['restricao']}")
    return _ok("licenca_confirmada", dataset=dataset, licenca=reg["licenca"],
               ressalva=reg["restricao"])


# ------------------------------------------------------------------ guarda 7


def exigir_affine_compativel(caminho_pred: Path, caminho_gt: Path) -> dict[str, Any]:
    """Guarda 7 — avaliacao com affine incompativel: recusa.

    REUSO de geometria.verificar_alinhamento (shape, zooms do header, affine,
    orientacao). Nivel de ARQUIVO. NAO reamostra: reamostrar para "consertar"
    inventa fronteira que ninguem desenhou.
    """
    if (r := _desligada("affine_compativel")) is not None:
        return r
    al = geometria.verificar_alinhamento(caminho_pred, caminho_gt)   # levanta Desalinhamento...
    return _ok("affine_compativel", delta_affine_max=al["delta_affine_max"],
               veredito=al["veredito"])


# ------------------------------------------------------------------ guarda 8


def exigir_mascara_na_grade(
    mascara: np.ndarray,
    shape_referencia: tuple[int, ...],
    rotulo: str = "mascara",
    valores_permitidos: tuple[int, ...] = (0, 1, FOREGROUND),
) -> dict[str, Any]:
    """Guarda 8 — mascara fora da grade: recusa. Nivel de ARRAY.

    Existe alem da guarda 7 porque uma predicao produzida EM MEMORIA nao tem
    affine proprio para comparar: o que se pode exigir dela e que esteja no
    shape da referencia, com rotulos conhecidos e nao vazia. Vazia recusa junto:
    um caso vazio nao e um caso facil, e um caso quebrado que atravessa o
    pipeline inteiro sem erro e envenena a media.
    """
    if (r := _desligada("mascara_na_grade")) is not None:
        return r
    m = np.asarray(mascara)
    if tuple(m.shape) != tuple(shape_referencia):
        raise MascaraForaDaGrade(
            f"{rotulo}: shape {tuple(m.shape)} != grade de referencia {tuple(shape_referencia)}. "
            "Sem reamostragem: fonte fora da grade e problema da FONTE."
        )
    fora = sorted(set(np.unique(m).tolist()) - set(valores_permitidos))
    if fora:
        raise MascaraForaDaGrade(
            f"{rotulo}: valores fora de {valores_permitidos}: {fora[:8]}. Rotulo desconhecido "
            "vira foreground silencioso com `> 0.5` e ninguem ve."
        )
    n = int((m > 0.5).sum())
    if n == 0:
        raise MascaraForaDaGrade(f"{rotulo}: zero voxel acima de 0.5 — caso quebrado, nao facil.")
    return _ok("mascara_na_grade", n_voxels=n, shape=tuple(int(s) for s in m.shape))


# ------------------------------------------------------------------ guarda 9


def exigir_fora_de_ignore(
    gt_rotulado: np.ndarray,
    avaliados: np.ndarray,
    metricas_3d: bool = False,
    ignore: int = IGNORE,
) -> dict[str, Any]:
    """Guarda 9 — avaliacao sobre fatias `ignore`: recusa. Licao da fase 8 (SAROS).

    Duas recusas, um objeto:
      - qualquer voxel avaliado que esteja em `ignore` -> recusa. Medido na fase 8:
        um falso positivo macico posto SO nas fatias de ignore nao muda nada com a
        restricao (Dice restrito 1,0) e derruba o Dice abaixo de 0,4 sem ela.
      - metrica de superficie 3D com anotacao esparsa -> recusa. Com 4 de cada 5
        fatias em ignore, o vizinho em z de uma fatia anotada esta a 25 mm e nao
        foi anotado: a "superficie 3D" e a superficie de lajes e o HD95 mediria as
        tampas artificiais delas.

    Selecao por `!= ignore`, NUNCA por passo fixo: na fase 8, `[::5]` errou em
    11 de 14 casos porque o passo modal 5 so era puro em 3/14.
    """
    if (r := _desligada("fora_de_ignore")) is not None:
        return r
    gt = np.asarray(gt_rotulado)
    av = np.asarray(avaliados, dtype=bool)
    if gt.shape != av.shape:
        raise AvaliacaoSobreIgnore(f"shapes divergentes: {gt.shape} != {av.shape}")
    anotado = gt != ignore
    vazando = int((av & ~anotado).sum())
    if vazando:
        raise AvaliacaoSobreIgnore(
            f"{vazando} voxel(s) avaliado(s) em regiao `ignore` ({ignore}). A metrica estaria "
            "cobrando do modelo uma regiao que o anotador declarou nao ter anotado."
        )
    frac = float(anotado.mean())
    if metricas_3d and frac < 1.0:
        raise AvaliacaoSobreIgnore(
            f"metrica de superficie 3D com anotacao esparsa (fracao anotada {frac:.4f}). "
            "HD95/ASSD 3D sao NAO APLICAVEIS aqui: mediriam as tampas artificiais das lajes. "
            "So distancia NO PLANO, por fatia anotada, e interpretavel."
        )
    return _ok("fora_de_ignore", fracao_anotada=frac, n_avaliados=int(av.sum()),
               metricas_3d_aplicaveis=bool(frac >= 1.0))


# ----------------------------------------------------------------- guarda 10

# Definicoes DECLARADAS. `nao medido` e ausencia de declaracao, nao concordancia.
DEFINICOES: dict[str, dict[str, Any]] = {
    "LCTSC/Esophagus": {
        "estrutura": "Esophagus", "segmento": "toracico", "populacao": "adulto",
        "inclui": ("parede", "lumen"),
        "exclui": ("conteudo alimentar", "gordura periesofagica", "traqueia"),
        "corpo": "macico", "convencao": "atlas RTOG 1106", "contornos_por_caso": 1,
        "extensao": "HERDADA do GT, declarada NAO AVALIAVEL (fase 9 Parte A)",
    },
    "TS/esophagus": {
        "estrutura": "Esophagus", "segmento": "toracico", "populacao": "adulto",
        "inclui": NM, "exclui": NM, "corpo": NM,
        "convencao": f"{NM} — 27 % do treino da v2 tem procedencia nao publicada",
        "extensao": "campo completo (a predicao preenche o campo de visao)",
    },
    "LCTSC/Heart": {
        "estrutura": "Heart", "segmento": "toracico", "populacao": "adulto",
        "inclui": ("miocardio", "camaras", "saco pericardico", "gordura pericardica"),
        "exclui": ("grandes vasos alem da raiz",),
        "corpo": "macico", "convencao": "atlas RTOG 1106", "contornos_por_caso": 1,
        "extensao": "herdada do GT",
    },
    "TS/heart": {
        "estrutura": "Heart", "segmento": "toracico", "populacao": "adulto",
        "inclui": ("miocardio", "camaras"),
        "exclui": ("saco pericardico", "gordura pericardica"),
        "corpo": NM, "convencao": NM, "extensao": "campo completo",
    },
    "HaN-Seg/cervical_esophagus": {
        "estrutura": "Esophagus", "segmento": "cervical", "populacao": "adulto",
        "inclui": NM, "exclui": NM, "corpo": NM,
        "convencao": "1 de 30 OAR, curado por especialista", "extensao": NM,
    },
    "Pediatric-CT-SEG/Esophagus": {
        "estrutura": "Esophagus", "segmento": "toracico", "populacao": "pediatrico 5 dias-16 anos",
        "inclui": NM, "exclui": NM, "corpo": NM,
        "convencao": f"{NM} — definicao de contorno nao publicada", "extensao": NM,
    },
}

# Comparadas SEMPRE. Divergencia aqui e divergencia de OBJETO.
CHAVES_DE_IDENTIDADE = ("estrutura", "segmento", "populacao")
# Comparadas so quando as DUAS lados declaram. `nao medido` nao vira acordo.
CHAVES_DE_CONTEUDO = ("inclui", "exclui")


def exigir_definicao_compativel(a: str, b: str) -> dict[str, Any]:
    """Guarda 10 — comparacao entre definicoes anatomicas incompativeis: recusa.

    Regra, declarada antes: recusa se divergirem em estrutura, segmento ou
    populacao; recusa se AMBAS declararem inclusoes/exclusoes e elas diferirem.
    `nao medido` de um lado NAO e concordancia — devolve `ressalva`, porque
    recusar por desconhecimento invalidaria o proprio BASELINE_ESOFAGO_V1, que e
    LCTSC/Esophagus contra TS/esophagus com o lado do TS nao declarado. A
    ressalva e o preco honesto de manter o baseline valido.
    """
    if (r := _desligada("definicao_compativel")) is not None:
        return r
    da, db = DEFINICOES.get(a), DEFINICOES.get(b)
    if da is None or db is None:
        raise DefinicoesIncompativeis(
            f"definicao nao registrada: {a if da is None else b!r}. Comparar contra uma "
            "definicao que ninguem escreveu e comparar contra a suposicao de quem lê."
        )
    for k in CHAVES_DE_IDENTIDADE:
        if da[k] != db[k]:
            raise DefinicoesIncompativeis(
                f"{a} x {b}: {k} divergente ({da[k]!r} x {db[k]!r}). Nao sao o mesmo objeto; "
                "o numero que sair mede a diferenca de definicao, nao a de modelo."
            )
    ressalvas = []
    for k in CHAVES_DE_CONTEUDO:
        va, vb = da[k], db[k]
        if va == NM or vb == NM:
            ressalvas.append(f"{k} nao declarado em {a if va == NM else b}")
            continue
        if set(va) != set(vb):
            raise DefinicoesIncompativeis(
                f"{a} x {b}: {k} divergente. So em {a}: {sorted(set(va) - set(vb))}; "
                f"so em {b}: {sorted(set(vb) - set(va))}. Ver fase5.NAO_OTIMIZAR."
            )
    return _ok("definicao_compativel", par=(a, b), ressalvas=ressalvas)


# ------------------------------------------------- a decisao, como uma funcao


def decidir(raiz: Path = RAIZ_PADRAO) -> dict[str, Any]:
    """TREINO AUTORIZADO ou TREINO BLOQUEADO. Duas saidas, nunca uma terceira.

    A decisao NAO e opiniao: ela roda as guardas contra o estado real. Se
    qualquer uma recusar, e BLOQUEADO — inclusive por duvida material sobre a
    independencia do TEST, que e o criterio mais estrito do enunciado.
    """
    split = fase5.carregar_split(raiz)
    recusas: list[dict[str, str]] = []

    def _tenta(nome: str, fn, *a, **kw) -> None:
        try:
            fn(*a, **kw)
        except RecusaDeProtocolo as e:
            recusas.append({"guarda": nome, "excecao": type(e).__name__, "motivo": str(e)})
        except ProcedenciaInvalida as e:
            recusas.append({"guarda": nome, "excecao": "ProcedenciaInvalida", "motivo": str(e)})

    # O `test` do LCTSC existe no split, mas esta GASTO. Perguntar a guarda 2 se
    # ele pode ser o TESTE de uma pergunta nova e a pergunta que decide a fase.
    _tenta("test_intocado(LCTSC/test)", exigir_test_intocado,
           split["test"], "teste", split, "LCTSC/test")
    # Nenhum candidato da Parte D passa a licenca+procedencia+definicao ao mesmo tempo.
    for ds in ("SegRap2023", "WORD", "BTCV", "StructSeg2019", "SegTHOR", "AMOS22"):
        _tenta(f"licenca_confirmada({ds})", exigir_licenca_confirmada, ds)
    for outro in ("HaN-Seg/cervical_esophagus", "Pediatric-CT-SEG/Esophagus"):
        _tenta(f"definicao_compativel({outro})", exigir_definicao_compativel,
               "LCTSC/Esophagus", outro)

    autorizado = not recusas
    return {
        "decisao": "TREINO AUTORIZADO" if autorizado else "TREINO BLOQUEADO",
        "n_recusas": len(recusas),
        "recusas": recusas,
        "criterio_aplicado": (
            "duas saidas apenas. Qualquer duvida material sobre a independencia do TEST "
            "resulta em BLOQUEADO."
        ),
        "porque": [
            "1. NAO HA TESTE. O `test` do LCTSC (15 casos) esta gasto — lido na fase 7 pela "
            "hipotese heart->pericardium. Uma leitura agora seria a segunda.",
            "2. NENHUM CANDIDATO EXTERNO PASSA. Pediatric-CT-SEG tem licenca e GT humano mas e "
            "populacao pediatrica (5 dias-16 anos) — a guarda 10 recusa. HaN-Seg cobre o "
            "esofago CERVICAL — a guarda 10 recusa. SegRap2023, WORD, BTCV e StructSeg2019 nao "
            "tem licenca confirmada — a guarda 6 recusa. Os 10 ensaios do NCI estao sob NIH "
            "Controlled Data Access e o download nao esta disponivel hoje.",
            "3. INDEPENDENCIA NAO DEMONSTRAVEL. O comparador e TotalSegmentator 2.18.0 e o "
            "proprio repositorio declara que 420 das 1.559 imagens de treino da v2 (26,9 %) "
            "vieram de 'other institutions' e NAO foram publicadas. Nenhum dataset publico — "
            "o LCTSC incluido — pode hoje ser PROVADO independente do treino do comparador. "
            "Isso e duvida material por definicao.",
            "4. PARTE DO ALVO NAO E AVALIAVEL. A extensao longitudinal e herdada do GT e foi "
            "declarada nao avaliavel; ela responde por 0,2119 da decomposicao do erro. Um "
            "quinto do erro medido esta num eixo onde nao existe arbitro.",
        ],
        "o_que_desbloquearia": [
            "uma fonte com GT humano, licenca lida na fonte, esofago TORACICO de populacao "
            "adulta, instituicao fora de MAASTRO/MDACC/MSKCC, e nunca usada nesta base;",
            "ou uma declaracao de procedencia completa do treino do TotalSegmentator v2, que "
            "hoje nao existe publicamente e nao depende de nos;",
            "ou uma reformulacao da pergunta que nao precise de teste causal — por exemplo "
            "medir concordancia entre anotadores em vez de desempenho contra um GT unico. "
            "Isso e outra fase, nao esta.",
        ],
        "o_que_este_bloqueio_NAO_diz": (
            "nao diz que o modelo especializado seria ruim, nem que nnU-Net seria a escolha "
            "errada. Diz que o resultado nao seria INTERPRETAVEL: sem teste independente, "
            "(i) e (ii) ficam indistinguiveis e um ganho de Dice nao teria como ser separado "
            "de aprendizado de convencao."
        ),
    }


# =============================================== PARTE H — tabela pre-treino


METRICAS_TABELA = (
    ("dice", "adimensional", "sobreposicao; cego para erro de extensao num tubo fino"),
    ("hd95_mm", "mm fisicos", "fronteira; e a que enxerga o modo de erro conhecido"),
    ("assd_mm", "mm fisicos", "distancia media de superficie"),
    ("precision", "adimensional", "quanto da predicao esta no GT"),
    ("recall", "adimensional", "quanto do GT foi encontrado"),
    ("erro_absoluto_ml", "mL", "|FP| + |FN| em volume — nao cancela sinal"),
    ("erro_absoluto_pct_do_gt", "% do GT", "o mesmo, normalizado pelo volume do proprio caso"),
)


def _dist(v: list[float]) -> dict[str, float]:
    a = np.asarray(v, dtype=float)
    return {
        "n": int(a.size),
        "mediana": float(np.median(a)),
        "p25": float(np.percentile(a, 25)),
        "p75": float(np.percentile(a, 75)),
        "min": float(a.min()),
        "max": float(a.max()),
        "media": float(a.mean()),
    }


def tabela_pre_treino(csv_baseline: Path = BASELINE_CSV) -> dict[str, Any]:
    """Linhas do baseline LIDAS do CSV; linhas do modelo em branco.

    Nenhum numero do baseline e redigitado: se o CSV mudar, a tabela muda junto,
    e se ele sumir a funcao falha em vez de inventar.
    """
    linhas = list(csv.DictReader(Path(csv_baseline).open(encoding="utf-8")))
    if not linhas:
        raise FileNotFoundError(f"{csv_baseline} vazio — a tabela nao pode ser preenchida")
    tabela = []
    for nome, unidade, papel in METRICAS_TABELA:
        d = _dist([float(l[nome]) for l in linhas])
        tabela.append({
            "metrica": nome, "unidade": unidade, "papel": papel,
            "baseline_mediana": d["mediana"], "baseline_p25": d["p25"], "baseline_p75": d["p75"],
            "baseline_min": d["min"], "baseline_max": d["max"],
            "modelo_mediana": NM, "modelo_p25": NM, "modelo_p75": NM,
            "modelo_min": NM, "modelo_max": NM,
            "delta_mediana": NM,
        })
    return {
        "baseline": "BASELINE_ESOFAGO_V1 — TotalSegmentator 2.18.0 task=total, saida CRUA, "
                    "campo completo",
        "conjunto": "LCTSC development, n=30",
        "fonte_dos_numeros": str(csv_baseline),
        "modelo": "NAO EXISTE — todas as celulas do modelo sao `nao medido`, e continuam "
                  "assim enquanto a decisao for TREINO BLOQUEADO",
        "n_casos": len(linhas),
        "linhas": tabela,
    }


# ================================================================ orquestracao


def _md(res: dict[str, Any]) -> str:
    t, dec, pro = res["tabela_pre_treino"], res["decisao"], res["protocolo"]
    L = [
        "# Fase 9 — Partes F/G/H/I: protocolo, criterios e controles do esofago", "",
        f"Gerado em {res['gerado_em']}. **Nada foi treinado.** Conjunto lido: "
        f"development (n={t['n_casos']}); validation e test NAO foram lidos.", "",
        f"## DECISAO: **{dec['decisao']}**", "",
        f"{dec['criterio_aplicado']}", "",
    ]
    for p in dec["porque"]:
        L.append(f"- {p}")
    L += ["", f"Guardas que recusaram ao rodar contra o estado real: **{dec['n_recusas']}**.", "",
          "| guarda | excecao | motivo |", "|---|---|---|"]
    for r in dec["recusas"]:
        L.append(f"| `{r['guarda']}` | `{r['excecao']}` | {r['motivo'].split('.')[0][:120]} |")

    L += ["", "## Parte F — protocolo candidato (registro, nao otimizacao)", "",
          f"Candidato: **{pro['candidato']}**. Estado: {pro['estado']}.", "",
          "| item | valor | justificativa (resumo) |", "|---|---|---|"]
    for k, v in pro.items():
        if isinstance(v, dict) and "valor" in v:
            valor = v["valor"]
            if isinstance(valor, dict):
                valor = "; ".join(f"{a}={b}" for a, b in list(valor.items())[:3]) + " ..."
            valor = str(valor).replace("\n", " ")[:90]
            just = v["justificativa"].split(".")[0][:150]
            L.append(f"| `{k}` | {valor} | {just} |")
    L += ["", "**O que o protocolo NAO define:**"]
    for s in pro["o_que_o_protocolo_NAO_define"]:
        L.append(f"- {s}")

    L += ["", "## Parte H — tabela pre-treino", "",
          f"Baseline: {t['baseline']}, {t['conjunto']}. Modelo: {t['modelo']}", "",
          "| metrica | unidade | baseline mediana | baseline IQR | baseline min-max | "
          "modelo mediana | delta |", "|---|---|---|---|---|---|---|"]
    for r in t["linhas"]:
        L.append(
            f"| `{r['metrica']}` | {r['unidade']} | {r['baseline_mediana']:.4f} | "
            f"{r['baseline_p25']:.4f}-{r['baseline_p75']:.4f} | "
            f"{r['baseline_min']:.4f}-{r['baseline_max']:.4f} | {r['modelo_mediana']} | "
            f"{r['delta_mediana']} |"
        )

    c = res["criterios"]
    L += ["", "## Parte G — as duas perguntas", "",
          "| | (i) supera o baseline? | (ii) generaliza? |", "|---|---|---|",
          f"| sujeito | {c['pergunta_i']['e_uma_pergunta_sobre']} | "
          f"{c['pergunta_ii']['e_uma_pergunta_sobre']} |",
          f"| dado exigido | {c['pergunta_i']['com_que_dado'][:120]}... | "
          f"{c['pergunta_ii']['com_que_dado'][:120]}... |",
          f"| estado hoje | **{c['pergunta_i']['estado_hoje']}** | "
          f"**{c['pergunta_ii']['estado_hoje']}** |", "",
          c["pergunta_ii"]["porque_pode_dar_o_OPOSTO_de_i"], ""]

    L += ["## Parte I — guardas verificadas por mutacao", "",
          "| guarda | excecao | autoteste caiu com a guarda desligada |", "|---|---|---|"]
    for m in res["mutacao"]:
        L.append(f"| `{m['guarda']}` | `{m['excecao_da_guarda']}` | "
                 f"**{'sim' if m['autoteste_caiu'] else 'NAO — guarda inutil'}** |")
    L += ["", "## O que este bloqueio nao diz", "", dec["o_que_este_bloqueio_NAO_diz"], "",
          "## O que desbloquearia", ""]
    for s in dec["o_que_desbloquearia"]:
        L.append(f"- {s}")
    return "\n".join(L) + "\n"


def executar(raiz: Path = RAIZ_PADRAO, destino: Path = SAIDA_PADRAO) -> dict[str, Any]:
    res = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conjunto_lido": "development (via fase7/baseline_esofago.csv)",
        "ressalva_de_fase": "validation e test NAO foram lidos; nada foi treinado nem baixado",
        "protocolo": PROTOCOLO,
        "medidos_citados": {k: {"valor": v, "fonte": f} for k, (v, f) in MEDIDOS.items()},
        "tabela_pre_treino": tabela_pre_treino(raiz / BASELINE_CSV.relative_to(RAIZ_PADRAO)),
        "criterios": CRITERIOS,
        "guardas": {
            "test_definido": "TestNaoDefinido", "test_intocado": "TestGasto",
            "gt_humano": "ProcedenciaInvalida (REUSO de dataset_esofago)",
            "conjuntos_disjuntos": "VazamentoEntreConjuntos", "sem_repeticao": "CasoRepetido",
            "licenca_confirmada": "LicencaNaoConfirmada",
            "affine_compativel": "DesalinhamentoGeometrico (REUSO de geometria)",
            "mascara_na_grade": "MascaraForaDaGrade", "fora_de_ignore": "AvaliacaoSobreIgnore",
            "definicao_compativel": "DefinicoesIncompativeis",
        },
        "mutacao": verificar_por_mutacao(),
        "decisao": decidir(raiz),
    }
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "protocolo.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with (destino / "tabela_pre_treino.csv").open("w", newline="", encoding="utf-8") as fh:
        linhas = res["tabela_pre_treino"]["linhas"]
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    (destino / "summary.md").write_text(_md(res), encoding="utf-8")
    print(f"\nDECISAO: {res['decisao']['decisao']} "
          f"({res['decisao']['n_recusas']} guardas recusaram)")
    print(f"escrito em {destino}")
    return res


# ================================================================== autoteste


def _autoteste() -> None:
    """Dez blocos. Cada um: caso legitimo PASSA, controle positivo DERRUBA.

    O caso legitimo so verifica `recusou is False`, para que desligar a guarda
    NAO o quebre — assim, sob mutacao, o unico assert capaz de cair e o do
    controle positivo, que e o que prova que a guarda guarda.
    """
    def _derruba(exc, fn, *a, **kw) -> None:
        try:
            fn(*a, **kw)
        except exc:
            return
        raise AssertionError(f"CONTROLE POSITIVO nao derrubou: {fn.__name__} deveria "
                             f"levantar {exc.__name__} com {a!r}")

    split_ok = {"development": ["a", "b"], "validation": ["c"], "test": ["d"]}

    # --- 1. test definido
    assert exigir_test_definido(split_ok)["recusou"] is False
    _derruba(TestNaoDefinido, exigir_test_definido, {"development": ["a"], "validation": ["c"]})
    _derruba(TestNaoDefinido, exigir_test_definido, {**split_ok, "test": []})

    # --- 2. LCTSC test intocado
    assert exigir_test_intocado(["a", "b"], "treino", split_ok)["recusou"] is False
    _derruba(TestGasto, exigir_test_intocado, ["a", "d"], "treino", split_ok)
    _derruba(TestGasto, exigir_test_intocado, ["d"], "teste", split_ok, "LCTSC/test")

    # --- 3. GT humano (REUSO)
    humano = {"case_id": "c1", "dataset": "s", "licenca": "NA", "gt_humano": True}
    assert exigir_gt_humano([humano])["recusou"] is False
    _derruba(ProcedenciaInvalida, exigir_gt_humano, [{**humano, "gt_humano": False}])
    _derruba(ProcedenciaInvalida, exigir_gt_humano, [{**humano, "gt_humano": 1}])

    # --- 4. conjuntos disjuntos
    assert exigir_conjuntos_disjuntos(split_ok)["recusou"] is False
    _derruba(VazamentoEntreConjuntos, exigir_conjuntos_disjuntos,
             {"treino": ["a", "b"], "teste": ["b", "c"]})

    # --- 5. sem repeticao
    assert exigir_sem_repeticao(["a", "b", "c"])["recusou"] is False
    _derruba(CasoRepetido, exigir_sem_repeticao, ["a", "b", "a"])

    # --- 6. licenca confirmada
    assert exigir_licenca_confirmada("LCTSC")["recusou"] is False
    _derruba(LicencaNaoConfirmada, exigir_licenca_confirmada, "StructSeg2019")   # sem licenca
    _derruba(LicencaNaoConfirmada, exigir_licenca_confirmada, "AMOS22")          # conflitante
    _derruba(LicencaNaoConfirmada, exigir_licenca_confirmada, "SegTHOR")         # PROIBE
    _derruba(LicencaNaoConfirmada, exigir_licenca_confirmada, "Dataset-Novo-X")  # ausente

    # --- 7. affine compativel (REUSO); arquivos reais em diretorio temporario
    import tempfile

    import nibabel as nib
    cubo = np.zeros((16, 16, 16), dtype=np.uint8)
    cubo[4:12, 4:12, 4:12] = 1
    aff = np.diag([0.98, 0.98, 2.5, 1.0])
    with tempfile.TemporaryDirectory() as td:
        pa, pb, pc = (Path(td) / n for n in ("a.nii.gz", "b.nii.gz", "c.nii.gz"))
        nib.save(nib.Nifti1Image(cubo, aff), str(pa))
        nib.save(nib.Nifti1Image(cubo, aff), str(pb))
        desloc = aff.copy()
        desloc[2, 3] += 2.5                      # uma fatia de deslocamento
        nib.save(nib.Nifti1Image(cubo, desloc), str(pc))
        assert exigir_affine_compativel(pa, pb)["recusou"] is False
        _derruba(DesalinhamentoGeometrico, exigir_affine_compativel, pa, pc)

    # --- 8. mascara na grade
    m = np.zeros((8, 8, 8), np.uint8)
    m[2:6, 2:6, 2:6] = FOREGROUND
    assert exigir_mascara_na_grade(m, (8, 8, 8))["recusou"] is False
    _derruba(MascaraForaDaGrade, exigir_mascara_na_grade, m, (8, 8, 9))        # shape
    _derruba(MascaraForaDaGrade, exigir_mascara_na_grade, np.zeros((8, 8, 8)), (8, 8, 8))  # vazia
    ruim = m.copy()
    ruim[0, 0, 0] = 7                                                          # rotulo estranho
    _derruba(MascaraForaDaGrade, exigir_mascara_na_grade, ruim, (8, 8, 8))

    # --- 9. fora de ignore. Reproduz o controle da fase 8: 4 de 5 fatias em
    #        ignore e um FP macico posto SO nas fatias nao anotadas.
    gt = np.zeros((10, 10, 10), np.uint8)
    gt[:, :, :] = IGNORE
    gt[:, :, ::5] = 0                    # so 2 de 10 fatias anotadas (fracao 0,2)
    gt[3:7, 3:7, 0] = 1
    anotado = gt != IGNORE
    assert exigir_fora_de_ignore(gt, anotado)["recusou"] is False
    fp_no_ignore = np.zeros_like(anotado)
    fp_no_ignore[:, :, 2] = True         # bloco inteiro numa fatia de ignore
    _derruba(AvaliacaoSobreIgnore, exigir_fora_de_ignore, gt, anotado | fp_no_ignore)
    _derruba(AvaliacaoSobreIgnore, exigir_fora_de_ignore, gt, anotado, True)  # HD95 3D esparso
    r9 = exigir_fora_de_ignore(gt, anotado)
    assert r9["metricas_3d_aplicaveis"] is False, r9
    denso = np.zeros((6, 6, 6), np.uint8)
    denso[2:4, 2:4, 2:4] = 1
    assert exigir_fora_de_ignore(denso, np.ones_like(denso, bool), True)["recusou"] is False

    # --- 10. definicoes compativeis
    assert exigir_definicao_compativel("LCTSC/Esophagus", "TS/esophagus")["recusou"] is False
    _derruba(DefinicoesIncompativeis, exigir_definicao_compativel,
             "LCTSC/Heart", "TS/heart")                     # pericardio: conteudo declarado difere
    _derruba(DefinicoesIncompativeis, exigir_definicao_compativel,
             "LCTSC/Esophagus", "HaN-Seg/cervical_esophagus")          # segmento
    _derruba(DefinicoesIncompativeis, exigir_definicao_compativel,
             "LCTSC/Esophagus", "Pediatric-CT-SEG/Esophagus")          # populacao
    _derruba(DefinicoesIncompativeis, exigir_definicao_compativel,
             "LCTSC/Esophagus", "Dataset-Novo-X")                      # nao registrada

    print(f"autoteste OK — {len(GUARDAS)} guardas, todas com controle positivo")


def verificar_por_mutacao(guardas: tuple[str, ...] = GUARDAS) -> list[dict[str, Any]]:
    """Desliga UMA guarda por vez e exige que o autoteste CAIA.

    Guarda que nao derruba o teste quando desligada nao esta guardando nada.
    Levanta se alguma sobreviver a propria ausencia.
    """
    relatorio = []
    excecoes = {
        "test_definido": "TestNaoDefinido", "test_intocado": "TestGasto",
        "gt_humano": "ProcedenciaInvalida", "conjuntos_disjuntos": "VazamentoEntreConjuntos",
        "sem_repeticao": "CasoRepetido", "licenca_confirmada": "LicencaNaoConfirmada",
        "affine_compativel": "DesalinhamentoGeometrico", "mascara_na_grade": "MascaraForaDaGrade",
        "fora_de_ignore": "AvaliacaoSobreIgnore", "definicao_compativel": "DefinicoesIncompativeis",
    }
    for nome in guardas:
        _DESLIGADAS.add(nome)
        try:
            _autoteste()
            caiu, motivo = False, "o autoteste PASSOU sem a guarda"
        except AssertionError as e:
            caiu, motivo = True, str(e).splitlines()[0][:160]
        finally:
            _DESLIGADAS.discard(nome)
        relatorio.append({
            "guarda": nome, "excecao_da_guarda": excecoes[nome],
            "autoteste_caiu": caiu, "motivo": motivo,
        })
    sobreviventes = [r["guarda"] for r in relatorio if not r["autoteste_caiu"]]
    if sobreviventes:
        raise AssertionError(
            f"guardas que NAO derrubam o autoteste quando desligadas: {sobreviventes}. "
            "Elas nao estao guardando nada."
        )
    return relatorio


def _main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--autoteste" in argv:
        _autoteste()
        return 0
    if "--mutacao" in argv:
        for r in verificar_por_mutacao():
            print(f"  {r['guarda']:22s} desligada -> autoteste "
                  f"{'CAIU' if r['autoteste_caiu'] else 'PASSOU (INUTIL)'}: {r['motivo']}")
        print(f"mutacao OK — {len(GUARDAS)}/{len(GUARDAS)} guardas derrubam o autoteste")
        return 0
    executar()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
