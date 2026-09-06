"""Fase 11 — INSTRUMENTO do censo de datasets com anotacao INTEROBSERVADOR.

Pergunta da fase (e so ela):

    existe dataset publico, acessivel e legalmente utilizavel com >= 2 anotacoes
    HUMANAS INDEPENDENTES do ESOFAGO sobre os MESMOS exames de TC toracica?

Este arquivo NAO responde a pergunta. Ele constroi o instrumento que procura, e
prova o instrumento em controles. O censo em si roda em shards, por fora.

------------------------------------------------------------------------------
A LICAO QUE DEFINE O DESENHO DESTE ARQUIVO

Medido na fonte primaria (API NBIA + pydicom), na colecao
`NSCLC-Radiomics-Interobserver1`: 64 series (22 CT, 21 RTSTRUCT, 21 SEG),
22 casos, UM RTSTRUCT por estudo — e, dentro desse unico RTSTRUCT, 20 a 24 ROIs
cujos NOMES revelam cinco observadores (GTV-1vis-1 .. GTV-1vis-5, e o mesmo para
GTV-2, mais as familias `auto` e os limiares).

Consequencia direta: um censo que conte SERIES de structure set por estudo daria
falso negativo exatamente nos datasets procurados. Os observadores moram DENTRO
de um arquivo, como sufixo do ROIName. Por isso `censo_colecao` conta series
(porque e barato e informa), mas quem DECIDE e `classificar_rois`, que le nome
de ROI. A contagem por estudo esta marcada no JSON como `nao_e_criterio`.

------------------------------------------------------------------------------
O QUE A SEGUNDA ONDA CONSERTOU (D1..D6) — e por que cada conserto existe

D1 DETECTOR DE OBSERVADOR CEGO A camelCase. `_norm` minusculizava ANTES de
   marcar fronteira, e a base do token tinha que terminar em '-' ou digito. O
   dado REAL escreve colado: `BowelSmObs1` (Pancreatic-CT-CBCT-SEG). O token
   'Obs' esta literalmente no nome e o detector nao via. Conserto: `_sep_camel`
   marca a fronteira ANTES de minusculizar — o que preserva a defesa original
   ('amd-2' nao tem fronteira, entao 'md' continua sendo parte de 'amd') — e
   `_familia` passou a cobrir PREFIXO (Obs1_, Rater1_, A_), iniciais (JD/MK),
   romanos (I/II), letras (a/b) e numero puro. 21 convencoes testadas.

D2 AMOSTRA DE 2 ARQUIVOS POR COLECAO, SEM ESTRATIFICAR. `rts[:2]` sobre lista
   ordenada por SeriesInstanceUID perde por construcao a colecao onde SO UM
   SUBCONJUNTO dos casos tem dupla anotacao — foi exatamente o que aconteceu com
   Pancreatic-CT-CBCT-SEG na 1a onda (abriu dois planCT e gravou "nem esofago
   nem indicio de multiplos observadores", falso nas duas metades). Conserto:
   `--completo` le a UNIAO de todos os structure sets, e a amostra passou a ser
   estratificada por ESTUDO com prioridade para estudos com >= 2 structure sets.
   A cobertura (lidos/total e por qual regra) e sempre gravada.

D3 OBSERVADOR EM ARQUIVOS SEPARADOS (padrao S0819). A licao "observadores moram
   DENTRO do arquivo" so foi aplicada numa direcao; o caso simetrico — dois
   structure sets apontando para a MESMA serie de CT — nao era coberto, porque
   cada arquivo era classificado ISOLADAMENTE e agregado com any().
   Conserto: `detectar_entre_arquivos` agrupa por StudyInstanceUID + serie de CT
   referenciada (ou FrameOfReferenceUID) e procura o MESMO ROIName em >= 2
   arquivos do mesmo grupo.

D4 'Esophagus' + 'Esophagus_2' saia como NEGATIVO. A base NUA nao formava
   familia, a familia ficava com um sufixo so e morria em len(sufixos) < 2.
   Conserto: a base sem sufixo e MEMBRO da familia. O par sai AMBIGUO,
   registrado e reportado — nunca negativo.

D5 SO RTSTRUCT ERA LIDO. 30 colecoes que so tem SEG receberam "INCONCLUSIVO"
   com resumo tem_esofago:false — lacuna gravada como negativa. Conserto:
   `ler_segmentos` le SegmentLabel/SegmentDescription/SegmentAlgorithmType e os
   codigos de propriedade. SegmentAlgorithmType e evidencia direta de F2
   (MANUAL x AUTOMATIC) e SegmentedPropertyCategoryCodeSequence e evidencia
   direta de F5 (Anatomical Structure x Morphologically Abnormal Structure).

D6 BOOLEANO QUE SIGNIFICAVA DUAS COISAS. `tem_esofago: false` queria dizer ora
   "medido e ausente", ora "nao medido". Conserto: tri-estado true/false/null,
   com null = NAO MEDIDO, e a guarda g11 que RECUSA agregar null como false.

------------------------------------------------------------------------------
OS 7 FILTROS — e o que este instrumento consegue medir de cada um

  F1 mesmo exame com >= 2 contornos de esofago .... mede (nome de ROI no mesmo
                                                    arquivo, D1; e entre arquivos
                                                    da mesma serie de CT, D3)
  F2 contornos HUMANOS ............................ mede parcialmente (g2/g3: recusa
                                                    consenso e recusa automatico pelo nome;
                                                    SegmentAlgorithmType do SEG, D5;
                                                    NAO prova humanidade — so a fonte prova)
  F3 numero de anotadores verificavel ............. levanta HIPOTESE, a confirmar na fonte
  F4 licenca/acesso verificavel ................... mede (g8, licenca LIDA da API)
  F5 anatomia comparavel .......................... mede (esofago OAR x tumor esofagico;
                                                    codigo de propriedade do SEG, D5)
  F6 contornos recuperaveis INDIVIDUALMENTE ....... mede parcialmente (g2 recusa consenso)
  F7 comparacao em mm possivel .................... mede (g6/g9, spacing e affine)

------------------------------------------------------------------------------
TRES COISAS QUE ESTE ARQUIVO SE RECUSA A CONFUNDIR (Parte C)

  interobservador  x  interinstituicao  x  intraobservador

Dois datasets nao sao dois observadores (g1). Dois hospitais nao sao dois
observadores. Dois algoritmos nao sao dois observadores (g3). Uma mascara de
consenso nao substitui os contornos individuais (g2). O alvo e INTEROBSERVADOR.

------------------------------------------------------------------------------
LIMITE DECLARADO DO INSTRUMENTO

Ele le NOME. Nome e indicio, nunca prova. `padrao_observador` sai sempre marcado
como HIPOTESE: quem confirma e a fonte primaria (artigo, README, DOI, o proprio
DICOM). Um dataset com dois observadores e nomes ruins ("Esophagus" e
"Esophagus_2") sai daqui como AMBIGUO REGISTRADO, nunca como negativo — e por
isso o censo grava a distribuicao COMPLETA dos nomes, nao so o veredito.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.interobservador --autoteste
    python -m scripts.validation.tier2.interobservador --mutacao
    python -m scripts.validation.tier2.interobservador --colecoes LCTSC --completo
    python -m scripts.validation.tier2.interobservador --censo --shard 0/8
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import fase5  # noqa: E402
from scripts.validation.tier2 import protocolo_esofago as prot  # noqa: E402
from scripts.validation.tier2 import rtstruct as rtst  # noqa: E402
from scripts.validation.tier2 import tcia  # noqa: E402

RAIZ_CENSO = Path(".clinica-dados/tier2/censo")
SAIDA_PADRAO = RAIZ_CENSO / "censo_interobservador.json"

# D2: quantos structure sets abrir por colecao quando NAO se pede --completo.
# Era 2 e sem estratificacao — o defeito que perdeu Pancreatic-CT-CBCT-SEG.
# Continua sendo AMOSTRA: quem quer resposta usa --completo.
K_CONTORNOS = 6

MODALIDADES_DE_CONTORNO = ("RTSTRUCT", "SEG")


# ============================================================ 1. API de colecao


def colecoes(timeout: int = 120) -> list[str]:
    """getCollectionValues — os nomes de colecao, direto da API NBIA.

    Fica aqui e nao no tcia.py porque o tcia.py e o cliente da INGESTAO (serie,
    imagem, licenca) e ja esta congelado sob o baseline; um endpoint novo la
    mudaria um arquivo do caminho de producao para servir uma fase de busca.
    """
    url = f"{tcia.BASE}/getCollectionValues"
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (host fixo, https)
        return sorted(c["Collection"] for c in json.load(r))


# ================================================== 2. crivos de nome (o motor)

# Mecanismo de MUTACAO (mesmo desenho de protocolo_esofago). Vazio em operacao
# normal; `verificar_por_mutacao` desliga UMA regra por vez e exige que o
# autoteste caia. Regra que sobrevive a propria ausencia nao esta guardando nada.
_DESLIGADAS: set[str] = set()


def _desligada(nome: str) -> dict[str, Any] | None:
    """Resultado NEUTRO se a guarda estiver desligada, senao None.

    Mesma chave `recusou` do caminho legitimo: assim, sob mutacao, o unico
    assert capaz de cair e o do controle positivo.
    """
    if nome in _DESLIGADAS:
        return {"guarda": nome, "estado": "DESLIGADA", "recusou": False}
    return None


def _sep_camel(nome: str) -> str:
    """D1 — marca a fronteira que a minusculizacao apagaria.

    `BowelSmObs1` -> `Bowel-Sm-Obs-1`. Sem isto o token 'Obs' desaparece dentro
    da palavra e o detector fica cego na convencao que o dado REAL usa.

    A defesa original continua de pe justamente porque a fronteira e de CASO, e
    nao de posicao: `amd-2` nao tem transicao minuscula->maiuscula nenhuma,
    entao 'md' continua sendo parte de 'amd' e nao vira observador.
    """
    if "fronteira_camelcase" in _DESLIGADAS:
        return str(nome)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", "-", str(nome))   # BowelSm  -> Bowel-Sm
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "-", s)      # GTVObs   -> GTV-Obs
    return re.sub(r"(?<=[A-Za-z])(?=\d)", "-", s)        # Obs1     -> Obs-1


def _norm(nome: str) -> str:
    """minusculas, sem acento, separadores colapsados em '-'.

    `-` sobrevive de proposito: e ele que separa sufixo de base em `-a`/`-b`.
    A fronteira camelCase e marcada ANTES (D1), senao ela se perde para sempre.
    """
    s = unicodedata.normalize("NFKD", _sep_camel(nome)).encode("ascii", "ignore").decode()
    s = re.sub(r"[\s_.,;:+/\\()\[\]]+", "-", s.lower())
    return re.sub(r"-{2,}", "-", s).strip("-")


# --- esofago (F5). Superset de estilo_esofago.CRIVO_ESOFAGO (`o?esoph`), com
# --- pt/latim e a forma abreviada `eso` isolada (que exige fronteira, senao
# --- "mesotelioma" entraria).
CRIVO_ESOFAGO = re.compile(
    r"(?:o?esoph\w*|o?esofag\w*|o?esofag|(?:^|(?<=[^a-z]))eso(?:$|(?=[^a-z])))"
)

# --- alvo de tratamento: se o nome tem isto, o objeto e TUMOR, nao o orgao.
CRIVO_TUMOR = re.compile(
    r"(?:^|(?<=[^a-z]))(?:gtv\w*|ctv\w*|ptv\w*|itv\w*|igtv\w*|tumou?r\w*|tu|lesa[oe]\w*|"
    r"lesion\w*|nodul\w*|mass|ln|lymph\w*|linfonod\w*|met\w*|boost|nidus)(?:$|(?=[^a-z]))"
)

# --- g2: consenso NAO e observador independente.
CRIVO_CONSENSO = re.compile(
    r"(?:^|(?<=[^a-z]))(?:consensus\w*|consens\w*|consenso\w*|staple\w*|fus[ae]?d?\w*|"
    r"fusion\w*|majority\w*|maioria\w*|union\w*|uniao\w*|intersect\w*|agreement\w*|"
    r"combined\w*|averaged?\w*|mediana?\w*|simultaneous\w*|gold\w*)(?:$|(?=[^a-z]))"
)

# --- g3: saida de MODELO (duas saidas do mesmo modelo nao sao dois observadores).
# --- `t?res?hold` de proposito: o interobs11 real grava "treshold0,34", com erro
# --- de grafia. Crivo que so aceita a grafia correta perde o dado que existe.
CRIVO_AUTOMATICO = re.compile(
    r"(?:^|(?<=[^a-z]))(?:auto\w*|automat\w*|t?h?res?hold\w*|limiar\w*|suv\w*|nnunet\w*|"
    r"nn-?unet\w*|unet\w*|totalseg\w*|ts|cnn\w*|dl|ai|deep\w*|model\w*|modelo\w*|"
    r"pred\w*|algo\w*|segmentador\w*|machine\w*|net\w*)(?:$|(?=[^a-z]))"
)

# --- tokens que declaram IDENTIDADE de observador no proprio nome (g4, F3).
TOKENS_OBSERVADOR = (
    "observador", "observateur", "observer", "observ", "obs",
    "annotator", "anotador", "annot",
    "radiologista", "radiologist", "clinician", "physician", "especialista", "expert",
    "rater", "reader", "leitor", "delineator", "contourer",
    "user", "usuario", "vis", "doc", "dr", "md",
)
_ALT_OBS = "|".join(sorted(TOKENS_OBSERVADOR, key=len, reverse=True))

# SUFIXO: base termina em '-' ou digito (ou e vazia) => o token nao pode estar no
# meio de uma palavra. Com a fronteira camelCase marcada, 'BowelSmObs1' vira
# 'bowel-sm-obs-1' e PASSA; 'amd-2' continua sem passar.
_RE_FAM_TOKEN = re.compile(rf"^(?P<base>|.*?[-\d])(?P<tipo>{_ALT_OBS})-?(?P<num>\d+)$")
# PREFIXO (D1): Obs1_Esophagus, Rater1_Esophagus, Reader-2-Eso
_RE_FAM_TOKEN_PRE = re.compile(rf"^(?P<tipo>{_ALT_OBS})-?(?P<num>\d+)-(?P<base>.+)$")
# romanos: EsophagusI / EsophagusII (depois de _sep_camel: esophagus-i / -ii)
_RE_FAM_ROMANO = re.compile(r"^(?P<base>.*[a-z0-9])-(?P<num>i{1,3}|iv|vi{0,3}|ix|x)$")
# iniciais de pessoa: Esophagus_JD / Esophagus_MK. Exatamente DUAS letras —
# ponytail: 3+ letras sao qualificador anatomico ('ant', 'inf', 'sup') com muito
# mais frequencia do que iniciais; se aparecer dataset com 'Esophagus_JDS',
# ampliar aqui e ampliar INICIAIS_NAO_OBSERVADOR junto.
_RE_FAM_INICIAIS = re.compile(r"^(?P<base>.*[a-z0-9])-(?P<num>[a-z]{2})$")
_RE_FAM_LETRA = re.compile(r"^(?P<base>.*[a-z0-9])-(?P<num>[a-z])$")
_RE_FAM_LETRA_PRE = re.compile(r"^(?P<num>[a-z])-(?P<base>.+)$")
_RE_FAM_NUM = re.compile(r"^(?P<base>.*?[a-z])-?(?P<num>\d+)$")
_RE_FAM_NUM_PRE = re.compile(r"^(?P<num>\d+)-(?P<base>.+)$")


def _familia(norm: str) -> tuple[str, str, str] | None:
    """(base, tipo, sufixo) do nome normalizado, ou None se nao houver sufixo.

    tipo: nome do token ("obs", "vis", ...) = indicio FORTE;
          "iniciais"                        = indicio FORTE (fora da blocklist);
          "romano"                          = indicio FORTE a partir de 'ii';
          "letra"                           = indicio MEDIO, so a partir de '-a';
          "numero"                          = indicio FRACO (GTV-1/GTV-2 cai aqui).
    """
    sem_token = "familia_por_token" in _DESLIGADAS
    sem_prefixo = "familia_por_prefixo" in _DESLIGADAS

    if not sem_token and (m := _RE_FAM_TOKEN.match(norm)) is not None:
        return m["base"].rstrip("-"), m["tipo"], m["num"]
    if not sem_token and not sem_prefixo and (m := _RE_FAM_TOKEN_PRE.match(norm)) is not None:
        return m["base"].strip("-"), m["tipo"], m["num"]
    if (m := _RE_FAM_ROMANO.match(norm)) is not None:
        return m["base"].rstrip("-"), "romano", m["num"]
    if (m := _RE_FAM_INICIAIS.match(norm)) is not None:
        return m["base"].rstrip("-"), "iniciais", m["num"]
    if (m := _RE_FAM_LETRA.match(norm)) is not None:
        return m["base"].rstrip("-"), "letra", m["num"]
    if not sem_prefixo and (m := _RE_FAM_LETRA_PRE.match(norm)) is not None:
        return m["base"].strip("-"), "letra", m["num"]
    if (m := _RE_FAM_NUM.match(norm)) is not None:
        return m["base"].rstrip("-"), "numero", m["num"]
    if not sem_prefixo and (m := _RE_FAM_NUM_PRE.match(norm)) is not None:
        return m["base"].strip("-"), "numero", m["num"]
    return None


# Lateralidade, nao observador: Lung_L/Lung_R, rim-D/rim-E. Uma familia cujas
# letras so tem estas e DESCARTADA — e registrada em `familias_descartadas`,
# porque nada aqui pode sumir em silencio.
LETRAS_LATERALIDADE = frozenset("lrde")

# Duas letras que sao abreviacao tecnica, nao iniciais de pessoa.
INICIAIS_NAO_OBSERVADOR = frozenset({
    "ce", "ct", "pt", "ap", "pa", "lt", "rt", "ll", "rl", "lr", "np", "po", "sd", "hu", "gy",
})

ROMANOS_COMPOSTOS = frozenset({"ii", "iii", "iv", "vi", "vii", "viii", "ix"})


def _letras_de_observador(sufixos: set[str]) -> bool:
    """Familia de letras so vale se comecar em 'a' e for contigua.

    Observador rotulado por letra comeca no 'a' (-a/-b/-c). Sem esta regra,
    `Lung_L` + `Lung_R` viraria "duas letras da base lung".
    """
    if not sufixos:
        return False
    ords = sorted(ord(s) for s in sufixos)
    return ords[0] == ord("a") and ords == list(range(ords[0], ords[0] + len(ords)))


def classificar_rois(nomes: list[str]) -> dict[str, Any]:
    """Duas deteccoes SEPARADAS sobre uma lista de ROIName: esofago e observador.

    Nao decide nada sozinha: devolve o retrato. `padrao_observador` e sempre
    HIPOTESE — nome nao prova quem contornou.
    """
    nomes = [str(n) for n in nomes]
    norm = {n: _norm(n) for n in nomes}

    esofago = [n for n in nomes if CRIVO_ESOFAGO.search(norm[n])]
    esofago_tumor = [n for n in esofago if CRIVO_TUMOR.search(norm[n])]
    esofago_oar = [n for n in esofago if n not in esofago_tumor]

    consenso = [n for n in nomes if CRIVO_CONSENSO.search(norm[n])]
    automaticos = [n for n in nomes if n not in consenso and CRIVO_AUTOMATICO.search(norm[n])]

    # so nome que sobreviveu a g2 e g3 pode entrar numa familia de observador
    elegiveis = [n for n in nomes if n not in consenso and n not in automaticos]

    familias: dict[tuple[str, str], dict[str, Any]] = {}
    for n in elegiveis:
        if (f := _familia(norm[n])) is None:
            continue
        base, tipo, sufixo = f
        d = familias.setdefault((base, tipo), {"membros": [], "sufixos": set(), "base_nua": None})
        d["membros"].append(n)
        d["sufixos"].add(sufixo)

    # D4 — a base NUA e MEMBRO da familia: 'Esophagus' + 'Esophagus_2' sao dois
    # contornos do mesmo objeto, com o primeiro sem sufixo. Sem isto o par saia
    # como negativo, que e o pior erro possivel neste censo.
    if "base_implicita" not in _DESLIGADAS:
        nus = {norm[n]: n for n in elegiveis}
        for (base, _tipo), d in familias.items():
            if base in nus and nus[base] not in d["membros"]:
                d["base_nua"] = nus[base]
                d["membros"].append(nus[base])

    fortes, ambiguas, descartadas = [], [], []
    for (base, tipo), d in sorted(familias.items()):
        sufs = set(d["sufixos"])
        n_membros_efetivos = len(sufs) + (1 if d["base_nua"] else 0)
        if n_membros_efetivos < 2:  # uma familia de um so nao e familia
            continue
        reg = {
            "base": base, "tipo": tipo,
            "n_membros": len(d["membros"]),
            "membros": sorted(d["membros"]),
            "sufixos": sorted(sufs),
            "base_sem_sufixo": d["base_nua"],
        }
        if tipo == "letra" and sufs <= LETRAS_LATERALIDADE and "lateralidade" not in _DESLIGADAS:
            reg["por_que_descartada"] = "lateralidade (L/R, D/E), nao observador"
            descartadas.append(reg)
        elif tipo == "iniciais" and sufs <= INICIAIS_NAO_OBSERVADOR:
            reg["por_que_descartada"] = "abreviacao tecnica conhecida, nao iniciais de pessoa"
            descartadas.append(reg)
        elif tipo == "numero" and "numero_nunca_forte" not in _DESLIGADAS:
            reg["por_que_ambigua"] = (
                "sufixo numerico sozinho NAO prova observador: GTV-1 e GTV-2 sao alvos "
                "diferentes, nao dois contornos do mesmo objeto"
            )
            ambiguas.append(reg)
        elif tipo == "letra" and not _letras_de_observador(sufs):
            reg["por_que_ambigua"] = "letras nao comecam em 'a' e nao sao lateralidade conhecida"
            ambiguas.append(reg)
        elif tipo == "romano" and not (sufs & ROMANOS_COMPOSTOS):
            reg["por_que_ambigua"] = "romano de uma letra so ('i', 'v', 'x') e indistinguivel de letra"
            ambiguas.append(reg)
        else:
            fortes.append(reg)

    # familias que existem SO no lado automatico (interobs11: GTV-1auto-1..5)
    fam_auto: dict[str, int] = Counter(
        _familia(norm[n])[0] for n in automaticos if _familia(norm[n]) is not None
    )

    n_obs = max((len(f["sufixos"]) + (1 if f["base_sem_sufixo"] else 0) for f in fortes),
                default=None)
    return {
        "n_rois": len(nomes),
        "tem_esofago": bool(esofago_oar),
        "esofago_oar": sorted(esofago_oar),
        "esofago_tumor": sorted(esofago_tumor),
        "padrao_observador": fortes,
        "familias_ambiguas": ambiguas,
        "familias_descartadas": descartadas,
        "n_observadores_hipotese": n_obs,
        "consenso": sorted(consenso),
        "automaticos": sorted(automaticos),
        "familias_automaticas": dict(sorted(fam_auto.items())),
        "status": "HIPOTESE" if fortes else ("AMBIGUO" if ambiguas else "sem indicio"),
        "ressalva": (
            "classificacao por NOME. Indicio, nunca prova: confirmar numero e independencia "
            "dos anotadores na fonte primaria antes de contar como interobservador."
        ),
    }


# ================================================================= 3. guardas


class RecusaDeCenso(prot.RecusaDeProtocolo):
    """Base das recusas desta fase (herda de RecusaDeProtocolo de proposito)."""


class DoisDatasets(RecusaDeCenso):
    """g1 — mascaras de colecoes diferentes. Dois datasets nao sao dois observadores."""


class ConsensoComoObservador(RecusaDeCenso):
    """g2 — consenso/STAPLE/fused nao e observador independente."""


class MesmoModelo(RecusaDeCenso):
    """g3 — duas saidas do mesmo modelo (auto/threshold/suv/nnU-Net/TS) nao sao observadores."""


class SemIdentidadeDeObservador(RecusaDeCenso):
    """g4 — mascara sem identidade de quem contornou."""


class CasosDiferentes(RecusaDeCenso):
    """g5 — case_id diferente entre os lados. Nao e o mesmo exame."""


class DistanciaEmVoxel(RecusaDeCenso):
    """g9 — distancia em indice de voxel. So milimetro compara grade diferente."""


class FatiaFaltante(RecusaDeCenso):
    """g10 — fatia ausente virando background: inventa concordancia que ninguem anotou."""


class NullComoFalse(RecusaDeCenso):
    """g11 — NAO MEDIDO (null) sendo agregado como False. Lacuna nao e ausencia."""


# Excecoes e guardas REUSADAS, nao reimplementadas:
#   g6 -> prot.exigir_affine_compativel  (leva a geometria.DesalinhamentoGeometrico)
#   g7 -> prot.TestGasto                 (mesma tranca do holdout da fase 5)
#   g8 -> prot.LicencaNaoConfirmada
DesalinhamentoGeometrico = prot.DesalinhamentoGeometrico
TestGasto = prot.TestGasto
LicencaNaoConfirmada = prot.LicencaNaoConfirmada

GUARDAS = ("mesma_colecao", "nao_consenso", "nao_automatico", "identidade_de_observador",
           "mesmo_caso", "grade_compativel", "fora_do_holdout_lctsc", "licenca_da_api",
           "distancia_em_mm", "sem_fatia_faltante", "nao_agregar_null_como_false")

# Regras do DETECTOR que tambem sao mutadas (nao sao guardas: sao o motor).
REGRAS_MUTAVEIS = ("crivo_esofago", "crivo_tumor", "crivo_consenso", "crivo_automatico",
                   "fronteira_camelcase", "familia_por_token", "familia_por_prefixo",
                   "base_implicita", "numero_nunca_forte", "lateralidade")


def _ok(guarda: str, **extra: Any) -> dict[str, Any]:
    return {"guarda": guarda, "recusou": False, **extra}


def exigir_mesma_colecao(a: str, b: str) -> dict[str, Any]:
    """g1 — comparar mascara de colecoes diferentes: recusa.

    Duas colecoes sao dois exames de corpos diferentes. A diferenca medida seria
    diferenca de CASO, e ela seria reportada como desacordo entre observadores.
    """
    if (r := _desligada("mesma_colecao")) is not None:
        return r
    if _norm(a) != _norm(b):
        raise DoisDatasets(
            f"colecoes diferentes: {a!r} x {b!r}. Dois DATASETS nao sao dois observadores — "
            "isto mediria variacao entre coortes, nao entre quem contornou."
        )
    return _ok("mesma_colecao", colecao=a)


def exigir_nao_consenso(nome: str) -> dict[str, Any]:
    """g2 — nome de consenso: recusa. Consenso ja e funcao dos observadores."""
    if (r := _desligada("nao_consenso")) is not None:
        return r
    if CRIVO_CONSENSO.search(_norm(nome)):
        raise ConsensoComoObservador(
            f"{nome!r} e consenso/fusao. Um consenso e FUNCAO dos contornos individuais: "
            "compara-lo com um deles mede o proprio observador contra si mesmo (F6)."
        )
    return _ok("nao_consenso", nome=nome)


def exigir_nao_automatico(nome: str) -> dict[str, Any]:
    """g3 — nome de saida de modelo/limiar: recusa (F2)."""
    if (r := _desligada("nao_automatico")) is not None:
        return r
    if CRIVO_AUTOMATICO.search(_norm(nome)):
        raise MesmoModelo(
            f"{nome!r} e saida automatica (modelo/limiar). Duas saidas do mesmo modelo tem "
            "erro CORRELACIONADO: a concordancia entre elas nao e variabilidade humana."
        )
    return _ok("nao_automatico", nome=nome)


def exigir_identidade_de_observador(nome: str, observador: str | None = None) -> dict[str, Any]:
    """g4 — mascara sem identidade de observador: recusa (F3).

    Aceita identidade EXPLICITA (`observador=`, vinda da fonte) ou um token de
    observador no proprio nome. Sufixo numerico puro nao serve: `GTV-1` nao diz
    quem contornou, diz qual alvo.
    """
    if (r := _desligada("identidade_de_observador")) is not None:
        return r
    if observador:
        return _ok("identidade_de_observador", nome=nome, observador=observador, origem="explicita")
    f = _familia(_norm(nome))
    if f is None or f[1] in ("numero", "letra", "romano"):
        raise SemIdentidadeDeObservador(
            f"{nome!r} nao carrega identidade de observador. Sem saber QUEM contornou, a "
            "diferenca medida nao pode ser atribuida a ninguem — nao e interobservador."
        )
    return _ok("identidade_de_observador", nome=nome, observador=f"{f[1]}{f[2]}", origem="nome")


def exigir_mesmo_caso(case_id_a: str, case_id_b: str) -> dict[str, Any]:
    """g5 — case_id diferente: recusa (F1). O par tem que ser o MESMO exame."""
    if (r := _desligada("mesmo_caso")) is not None:
        return r
    if str(case_id_a) != str(case_id_b):
        raise CasosDiferentes(
            f"case_id {case_id_a!r} != {case_id_b!r}. Contornos de exames diferentes medem "
            "anatomia diferente; o desacordo seria do corpo, nao do observador."
        )
    return _ok("mesmo_caso", case_id=case_id_a)


def exigir_grade_compativel(caminho_a: Path, caminho_b: Path) -> dict[str, Any]:
    """g6 — shape/zooms/affine/orientacao divergentes: recusa. REUSO de prot (F7).

    Nao reamostra: reamostrar para "consertar" inventa fronteira que observador
    nenhum desenhou, e a fronteira e exatamente o que se quer medir.
    """
    if (r := _desligada("grade_compativel")) is not None:
        return r
    r = prot.exigir_affine_compativel(Path(caminho_a), Path(caminho_b))
    return _ok("grade_compativel", **{k: v for k, v in r.items() if k not in ("guarda", "recusou")})


def exigir_fora_do_holdout_lctsc(case_ids: list[str], raiz: Path = fase5.RAIZ) -> dict[str, Any]:
    """g7 — case_id do LCTSC `test` ou `validation`: recusa. Split lido da fase 5.

    O `test` esta declarado GASTO e o `validation` e o unico conjunto que ainda
    escolhe algo. Um censo e leitura, mas leitura tambem gasta: split.json e a
    fonte, nunca uma lista digitada aqui.
    """
    if (r := _desligada("fora_do_holdout_lctsc")) is not None:
        return r
    split = fase5.carregar_split(Path(raiz))  # ausente => FileNotFoundError, e recusa tambem
    proibidos = set(split.get("test", [])) | set(split.get("validation", []))
    tocados = sorted(set(map(str, case_ids)) & proibidos)
    if tocados:
        raise TestGasto(
            f"{len(tocados)} caso(s) do LCTSC test/validation: {tocados[:5]}"
            f"{'...' if len(tocados) > 5 else ''}. Estes conjuntos NAO podem ser lidos."
        )
    return _ok("fora_do_holdout_lctsc", n_verificados=len(case_ids))


def exigir_licenca_da_api(serie: dict[str, Any]) -> dict[str, Any]:
    """g8 — licenca ausente no registro da API: recusa (F4). REUSO de tcia.licenca.

    A licenca vem do dict da serie devolvido pela API. Nome digitado a mao nao
    passa: o que este projeto pode alegar e o que a API respondeu.
    """
    if (r := _desligada("licenca_da_api")) is not None:
        return r
    lic = tcia.licenca(serie)
    if not lic.get("nome") or not lic.get("uri"):
        raise LicencaNaoConfirmada(
            f"serie sem licenca na resposta da API (nome={lic.get('nome')!r}, "
            f"uri={lic.get('uri')!r}). Ausencia de licenca nao e permissao."
        )
    return _ok("licenca_da_api", **lic)


def exigir_distancia_em_mm(unidade: str, spacing_mm: tuple[float, ...] | None) -> dict[str, Any]:
    """g9 — distancia em indice de voxel: recusa (F7).

    Um voxel de 1x1x3 mm faz "3 voxels" valer 3 mm no plano e 9 mm em z. Dois
    datasets com spacing diferente comparados em indice comparam grade, nao
    anatomia.
    """
    if (r := _desligada("distancia_em_mm")) is not None:
        return r
    if _norm(unidade) not in ("mm", "milimetro", "milimetros"):
        raise DistanciaEmVoxel(
            f"unidade {unidade!r}: distancia so vale em mm. Indice de voxel nao e distancia — "
            "ele muda de significado quando o spacing muda."
        )
    if not spacing_mm or not all(isinstance(v, (int, float)) and v > 0 for v in spacing_mm):
        raise DistanciaEmVoxel(
            f"spacing invalido ({spacing_mm!r}): sem spacing positivo nos tres eixos nao ha "
            "como converter nada para mm."
        )
    return _ok("distancia_em_mm", spacing_mm=[float(v) for v in spacing_mm])


def exigir_sem_fatia_faltante(
    fatias_esperadas: list[int], fatias_presentes: list[int], rotulo: str = "mascara",
) -> dict[str, Any]:
    """g10 — fatia ausente tratada como background: recusa.

    Fatia que o observador NAO anotou nao e fatia vazia. Preenchida com zero, ela
    entra na metrica como concordancia (dois vazios batem) ou como falso negativo
    do outro lado — dois erros de sinais opostos, nenhum deles medido.
    """
    if (r := _desligada("sem_fatia_faltante")) is not None:
        return r
    faltando = sorted(set(map(int, fatias_esperadas)) - set(map(int, fatias_presentes)))
    if faltando:
        raise FatiaFaltante(
            f"{rotulo}: {len(faltando)} fatia(s) sem anotacao ({faltando[:8]}"
            f"{'...' if len(faltando) > 8 else ''}). Fatia faltante tem que virar `ignore`, "
            "nunca background."
        )
    return _ok("sem_fatia_faltante", n_fatias=len(set(fatias_esperadas)), rotulo=rotulo)


def exigir_tri_estado(valor: bool | None, rotulo: str = "medida") -> dict[str, Any]:
    """g11 — None (NAO MEDIDO) sendo lido como booleano: recusa (D6).

    Este e o defeito que a 1a onda gravou 30 vezes: colecao sem nenhum structure
    set aberto saiu com `tem_esofago: false`. Falso significa MEDIDO E AUSENTE;
    nao medido e `null`. Quem quiser um booleano tem que passar por aqui.
    """
    if (r := _desligada("nao_agregar_null_como_false")) is not None:
        return r
    if valor is None:
        raise NullComoFalse(
            f"{rotulo}=None significa NAO MEDIDO e nao pode ser agregado como False. "
            "Colecao sem structure set lido nao e colecao sem esofago — e colecao nao medida; "
            "o veredito dela e INCONCLUSIVO, nunca negativo."
        )
    return _ok("nao_agregar_null_como_false", rotulo=rotulo, valor=bool(valor))


def agregar_tri(valores: list[bool | None]) -> bool | None:
    """D6 — agrega tri-estado sem transformar NAO MEDIDO em negativo.

    True se algum lido deu True; False so se algo foi lido e nada deu True;
    None se NADA foi lido.
    """
    medidos = [v for v in valores if v is not None]
    if any(medidos):
        return True
    return False if medidos else None


# ==================================================== 4. leitura do DICOM (D5)


def _codigo(seq: Any) -> dict[str, str] | None:
    """CodeValue/CodingSchemeDesignator/CodeMeaning do primeiro item da sequencia."""
    if not seq:
        return None
    it = seq[0]
    return {
        "codigo": str(getattr(it, "CodeValue", "") or ""),
        "esquema": str(getattr(it, "CodingSchemeDesignator", "") or ""),
        "significado": str(getattr(it, "CodeMeaning", "") or ""),
    }


# F5 — o codigo de propriedade distingue ORGAO de ACHADO. 'Morphologically
# Abnormal Structure' e 'Neoplasm' nao sao o objeto do VRmed.
CRIVO_CATEGORIA_ANORMAL = re.compile(r"abnormal|neoplas|tumou?r|lesion|nodule", re.I)


def ler_segmentos(ds: Any) -> list[dict[str, Any]]:
    """D5 — SegmentSequence de um DICOM SEG.

    SegmentAlgorithmType e a evidencia mais direta de F2 que existe no proprio
    arquivo: MANUAL, SEMIAUTOMATIC ou AUTOMATIC, escrito por quem gerou o SEG.
    O codigo de propriedade e a evidencia mais direta de F5.
    """
    saida = []
    for s in getattr(ds, "SegmentSequence", None) or []:
        saida.append({
            "numero": getattr(s, "SegmentNumber", None),
            "label": str(getattr(s, "SegmentLabel", "") or ""),
            "descricao": str(getattr(s, "SegmentDescription", "") or ""),
            "algoritmo": str(getattr(s, "SegmentAlgorithmType", "") or "") or None,
            "nome_do_algoritmo": str(getattr(s, "SegmentAlgorithmName", "") or "") or None,
            "categoria": _codigo(getattr(s, "SegmentedPropertyCategoryCodeSequence", None)),
            "tipo_propriedade": _codigo(getattr(s, "SegmentedPropertyTypeCodeSequence", None)),
        })
    return saida


def nomes_de_segmentos(segmentos: list[dict[str, Any]]) -> list[str]:
    """SegmentLabel, com SegmentDescription como reserva (label vazio existe)."""
    return [s["label"] or s["descricao"] or f"segmento-{s['numero']}" for s in segmentos]


def resumo_seg(segmentos: list[dict[str, Any]]) -> dict[str, Any]:
    """Evidencia de F2 e F5 lida do SEG, sem inferir nada do nome."""
    algos = Counter((s["algoritmo"] or "AUSENTE").upper() for s in segmentos)
    anormais = [
        s["label"] or s["descricao"] for s in segmentos
        if CRIVO_CATEGORIA_ANORMAL.search(
            f"{(s['categoria'] or {}).get('significado', '')} "
            f"{(s['tipo_propriedade'] or {}).get('significado', '')}")
    ]
    tem_manual = None if not segmentos else ("MANUAL" in algos)
    return {
        "n_segmentos": len(segmentos),
        "algoritmos": dict(sorted(algos.items())),
        "tem_manual_f2": tem_manual,
        "todos_automaticos_f2": None if not segmentos else set(algos) <= {"AUTOMATIC"},
        "categorias": sorted({(s["categoria"] or {}).get("significado", "") for s in segmentos} - {""}),
        "tipos_de_propriedade": sorted(
            {(s["tipo_propriedade"] or {}).get("significado", "") for s in segmentos} - {""}),
        "segmentos_de_estrutura_anormal_f5": sorted(set(anormais)),
    }


def _referencias(ds: Any) -> dict[str, Any]:
    """D3 — a QUAL serie de CT este structure set aponta.

    Sem isto nao da para dizer que dois arquivos anotam o MESMO exame, e o
    padrao S0819 (observadores em arquivos separados) fica invisivel.
    """
    for_uid = str(getattr(ds, "FrameOfReferenceUID", "") or "")
    ref = ""
    try:
        rf = ds.ReferencedFrameOfReferenceSequence[0]
        for_uid = for_uid or str(getattr(rf, "FrameOfReferenceUID", "") or "")
        ref = str(rf.RTReferencedStudySequence[0].RTReferencedSeriesSequence[0].SeriesInstanceUID)
    except Exception:  # noqa: BLE001 — sequencia opcional; ausencia nao e erro
        pass
    if not ref:
        try:
            ref = str(ds.ReferencedSeriesSequence[0].SeriesInstanceUID)
        except Exception:  # noqa: BLE001
            pass
    return {"frame_of_reference_uid": for_uid or None, "serie_referenciada": ref or None}


def detectar_entre_arquivos(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """D3 — padrao S0819: o MESMO ROIName em >= 2 arquivos da MESMA serie de CT.

    Isto e candidato a interobservador tanto quanto o sufixo dentro do arquivo.
    O agrupamento exige StudyInstanceUID E (serie de CT referenciada ou
    FrameOfReferenceUID): dois structure sets do mesmo estudo que apontam para
    CTs diferentes (planCT x CBCT) nao anotam o mesmo exame e nao entram.

    Nomes de consenso e de saida automatica sao removidos antes da intersecao
    (g2/g3): repetir 'auto' em dois arquivos nao e dois observadores.
    """
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in registros:
        if "classificacao" not in r:
            continue
        estudo = r.get("study_uid")
        alvo = r.get("serie_referenciada") or r.get("frame_of_reference_uid")
        if not estudo or not alvo:
            continue  # sem ancora nao da para afirmar "mesmo exame"
        grupos.setdefault((str(estudo), str(alvo)), []).append(r)

    achados = []
    for (estudo, alvo), rs in sorted(grupos.items()):
        if len(rs) < 2:
            continue
        conj = []
        for r in rs:
            c = r["classificacao"]
            fora = set(c["consenso"]) | set(c["automaticos"])
            conj.append({_norm(n): n for n in r.get("rois", []) if n not in fora})
        comuns = set.intersection(*(set(d) for d in conj)) if conj else set()
        if not comuns:
            continue
        esof = sorted(n for n in comuns
                      if CRIVO_ESOFAGO.search(n) and not CRIVO_TUMOR.search(n))
        achados.append({
            "study_uid": estudo,
            "alvo_referenciado": alvo,
            "n_arquivos": len(rs),
            "series_de_contorno": sorted(str(r.get("series_uid")) for r in rs),
            "casos": sorted({str(r.get("case_id")) for r in rs}),
            "roinames_repetidos": sorted(comuns),
            "esofago_repetido": esof,
            "por_que_candidato": (
                "mesmo ROIName em arquivos DIFERENTES que referenciam a MESMA serie de CT: "
                "e o padrao 'segundo grupo re-anota o mesmo exame' (S0819). HIPOTESE — pode "
                "ser tambem re-exportacao do mesmo contorno; so a fonte primaria decide."
            ),
        })
    return achados


# ============================================================== 5. censo de UMA


def _slug(nome: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nome)


def _contorno_de_serie(serie: dict[str, Any], raiz: Path) -> dict[str, Any]:
    """Baixa SO o structure set (nunca a CT) e le nomes, referencias e SEG."""
    reg = {
        "case_id": serie.get("PatientID"),
        "modality": serie.get("Modality"),
        "series_uid": serie.get("SeriesInstanceUID"),
        "study_uid": serie.get("StudyInstanceUID"),
    }
    try:
        import pydicom

        destino = tcia.baixar_serie(serie, raiz / _slug(serie["SeriesInstanceUID"]))
        arquivos = sorted(destino.glob("*.dcm"))
        if not arquivos:
            reg["erro"] = "nenhum .dcm extraido"
            return reg
        ds = pydicom.dcmread(str(arquivos[0]), stop_before_pixels=True)
        reg.update(_referencias(ds))
        if getattr(ds, "SegmentSequence", None):  # D5 — SEG
            segmentos = ler_segmentos(ds)
            reg["segmentos"] = segmentos
            reg["resumo_seg"] = resumo_seg(segmentos)
            reg["rois"] = nomes_de_segmentos(segmentos)
        else:
            reg["rois"] = rtst.listar_rois(arquivos[0])
        reg["classificacao"] = classificar_rois(reg["rois"])
    except Exception as e:  # noqa: BLE001 — uma serie quebrada nao derruba o censo
        reg["erro"] = f"{type(e).__name__}: {e}"
    return reg


def _amostra_estratificada(
    contornos: list[dict[str, Any]], k: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """D2 — amostra por ESTUDO, com prioridade para estudo com >= 2 structure sets.

    `rts[:2]` sobre lista ordenada por SeriesInstanceUID perde por construcao a
    colecao onde so um SUBCONJUNTO dos casos tem dupla anotacao. Quando um estudo
    entra, ele entra INTEIRO (ate o limite), porque e a comparacao entre os
    arquivos do mesmo estudo que responde D3.
    """
    por_estudo: dict[str, list[dict[str, Any]]] = {}
    for s in sorted(contornos, key=lambda s: str(s.get("SeriesInstanceUID"))):
        por_estudo.setdefault(str(s.get("StudyInstanceUID")), []).append(s)
    ordem = sorted(por_estudo.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    escolhidos: list[dict[str, Any]] = []
    for _uid, ss in ordem:
        if len(escolhidos) >= k:
            break
        escolhidos.extend(ss[: max(0, k - len(escolhidos))])
    cobertura = {
        "regra": f"amostra estratificada por estudo (k={k}); estudos com >=2 structure sets "
                 "entram primeiro e inteiros",
        "n_estudos_com_contorno": len(ordem),
        "n_estudos_com_multiplos_contornos": sum(1 for _u, ss in ordem if len(ss) >= 2),
        "n_estudos_lidos": len({str(s.get("StudyInstanceUID")) for s in escolhidos}),
    }
    return escolhidos, cobertura


def resumir(lidos: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    """(resumo tri-estado, veredito). Pura de proposito: testavel sem rede (D6).

    Nenhuma lacuna vira negativo aqui. Se nada foi lido, esofago e
    multiplos_observadores saem `null` e o veredito e INCONCLUSIVO.
    """
    entre = detectar_entre_arquivos(lidos)
    fortes = [f for r in lidos for f in r["classificacao"]["padrao_observador"]]
    ambiguas = [f for r in lidos for f in r["classificacao"]["familias_ambiguas"]]
    descartadas = [f for r in lidos for f in r["classificacao"]["familias_descartadas"]]

    tem_esofago = agregar_tri([r["classificacao"]["tem_esofago"] for r in lidos])
    multiplos = None if not lidos else bool(fortes or entre)
    n_obs = max((r["classificacao"]["n_observadores_hipotese"] or 0 for r in lidos), default=0)

    resumo = {
        "n_contornos_lidos": len(lidos),
        "tem_esofago": tem_esofago,
        "multiplos_observadores": multiplos,
        "tri_estado": "true/false/null — null e NAO MEDIDO, nunca ausencia (D6)",
        "tem_esofago_tumor": agregar_tri([bool(r["classificacao"]["esofago_tumor"]) for r in lidos]),
        "n_observadores_hipotese": n_obs or None,
        "familias_de_observador": fortes,
        "familias_ambiguas": ambiguas,
        "familias_descartadas": descartadas,
        "entre_arquivos": entre,
        "algoritmos_seg_f2": dict(sorted(Counter(
            a for r in lidos for a, n in (r.get("resumo_seg") or {}).get("algoritmos", {}).items()
            for _ in range(n)).items())),
    }

    if tem_esofago is None or multiplos is None:
        return resumo, ("INCONCLUSIVO — nenhum structure set lido (esofago=null, "
                        "multiplos_observadores=null; NAO MEDIDO nao e negativo)")

    exigir_tri_estado(tem_esofago, "tem_esofago")           # g11
    exigir_tri_estado(multiplos, "multiplos_observadores")  # g11
    veredito = {
        (True, True): "CANDIDATO — esofago E familia de observador (confirmar na fonte)",
        (True, False): "esofago SEM indicio de multiplos observadores (F1 nao satisfeito)",
        (False, True): "multiplos observadores SEM esofago (falha F5)",
        (False, False): "nem esofago nem indicio de multiplos observadores",
    }[(tem_esofago, multiplos)]
    if ambiguas and not multiplos:
        veredito += (" — MAS ha familia AMBIGUA registrada (sufixo sem identidade): "
                     "ambiguo NAO e negativo, verificar na fonte")
    return resumo, veredito


def censo_colecao(
    nome: str,
    k: int = K_CONTORNOS,
    raiz: Path = RAIZ_CENSO,
    timeout: int = 300,
    completo: bool = False,
) -> dict[str, Any]:
    """Retrato de UMA colecao, sem baixar nenhuma imagem de CT.

    O que sai daqui e material para decidir os 7 filtros — nao o veredito. O
    veredito de uma colecao promissora exige a fonte primaria.
    """
    raiz = Path(raiz) / _slug(nome)
    reg: dict[str, Any] = {
        "colecao": nome,
        "lido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        series = tcia.listar_series(nome, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        reg["erro"] = f"getSeries: {type(e).__name__}: {e}"
        return reg

    reg["n_series"] = len(series)
    reg["series_por_modalidade"] = dict(sorted(Counter(
        str(s.get("Modality")) for s in series).items()))
    reg["n_casos"] = len({s.get("PatientID") for s in series})
    reg["n_estudos"] = len({s.get("StudyInstanceUID") for s in series})

    # contagem POR ESTUDO: informa, mas NAO decide (ver docstring do modulo)
    por_estudo: Counter[str] = Counter()
    for s in series:
        if s.get("Modality") in MODALIDADES_DE_CONTORNO:
            por_estudo[str(s.get("StudyInstanceUID"))] += 1
    reg["contornos_por_estudo"] = {
        "distribuicao": dict(sorted(Counter(por_estudo.values()).items())),
        "nao_e_criterio": (
            "os observadores costumam morar DENTRO de um unico RTSTRUCT, como sufixo do "
            "ROIName (medido no NSCLC-Radiomics-Interobserver1). Contar arquivos daria "
            "falso negativo exatamente nos datasets procurados — mas >=2 arquivos por estudo "
            "PRIORIZA a amostra (D2) e habilita a deteccao entre arquivos (D3)."
        ),
    }

    # F4 — licenca lida da API, nunca digitada
    licencas = sorted({json.dumps(tcia.licenca(s), sort_keys=True) for s in series})
    reg["licencas_lidas_da_api"] = [json.loads(x) for x in licencas]
    try:
        reg["guarda_licenca"] = exigir_licenca_da_api(series[0]) if series else None
    except LicencaNaoConfirmada as e:
        reg["guarda_licenca"] = {"guarda": "licenca_da_api", "recusou": True, "motivo": str(e)}
        reg["contornos_lidos"] = []
        reg["cobertura"] = {"lidos": 0, "regra": "nao lido: g8 recusou antes"}
        reg["resumo"], _ = resumir([])
        reg["veredito_instrumento"] = "RECUSADO por g8 (licenca nao confirmada pela API)"
        return reg

    # F1/F2/F3/F5/F6 — os NOMES, que e onde a resposta mora (RTSTRUCT e SEG, D5)
    contornos = [s for s in series if s.get("Modality") in MODALIDADES_DE_CONTORNO]
    if _norm(nome) == "lctsc":  # g7: o holdout nao pode ser lido nem para censo
        split = fase5.carregar_split()
        proibidos = set(split.get("test", [])) | set(split.get("validation", []))
        contornos = [s for s in contornos if str(s.get("PatientID")) not in proibidos]
        reg["g7_aplicada"] = "LCTSC test/validation excluidos do censo (split da fase 5)"

    if completo:
        escolhidos = sorted(contornos, key=lambda s: str(s.get("SeriesInstanceUID")))
        cobertura = {"regra": "completo — UNIAO de todos os structure sets da colecao",
                     "n_estudos_com_contorno": len({str(s.get("StudyInstanceUID"))
                                                    for s in contornos})}
        cobertura["n_estudos_com_multiplos_contornos"] = sum(
            1 for v in por_estudo.values() if v >= 2)
        cobertura["n_estudos_lidos"] = cobertura["n_estudos_com_contorno"]
    else:
        escolhidos, cobertura = _amostra_estratificada(contornos, k)

    cobertura |= {
        "lidos": len(escolhidos),
        "total_de_contornos_na_colecao": len(contornos),
        "fracao_lida": round(len(escolhidos) / len(contornos), 4) if contornos else None,
        "modalidades_lidas": dict(sorted(Counter(str(s.get("Modality")) for s in escolhidos).items())),
    }
    reg["cobertura"] = cobertura

    if escolhidos and _norm(nome) == "lctsc":
        # o filtro acima ja tirou; isto e a TRANCA — se ela levantar, o filtro furou
        exigir_fora_do_holdout_lctsc([str(s.get("PatientID")) for s in escolhidos])
    reg["contornos_lidos"] = [_contorno_de_serie(s, raiz) for s in escolhidos]

    lidos = [r for r in reg["contornos_lidos"] if "classificacao" in r]
    cobertura["lidos_com_sucesso"] = len(lidos)
    reg["resumo"], reg["veredito_instrumento"] = resumir(lidos)
    return reg


def rodar_censo(
    nomes: list[str] | None = None,
    shard: tuple[int, int] | None = None,
    saida: Path = SAIDA_PADRAO,
    k: int = K_CONTORNOS,
    raiz: Path = RAIZ_CENSO,
    completo: bool = False,
    log=print,
) -> dict[str, Any]:
    """Censo de N colecoes -> JSON. `shard=(i, n)` fica com as colecoes j%n == i."""
    todas = nomes if nomes else colecoes()
    alvo = [c for j, c in enumerate(todas) if shard is None or j % shard[1] == shard[0]]
    log(f"censo: {len(alvo)} de {len(todas)} colecoes"
        + (f" (shard {shard[0]}/{shard[1]})" if shard else ""))

    registros = []
    for i, c in enumerate(alvo, 1):
        registros.append(censo_colecao(c, k=k, raiz=raiz, completo=completo))
        log(f"  [{i}/{len(alvo)}] {c}: "
            f"{registros[-1].get('veredito_instrumento', registros[-1].get('erro'))}")

    fora = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": f"{tcia.BASE} (getCollectionValues + getSeries), ROIName dos RTSTRUCT e "
                 "SegmentSequence dos SEG",
        "shard": {"i": shard[0], "n": shard[1]} if shard else None,
        "n_colecoes_na_api": len(todas),
        "n_colecoes_neste_shard": len(alvo),
        "modo": "completo" if completo else f"amostra estratificada k={k}",
        "limite_declarado": (
            "le NOME de ROI (RTSTRUCT) e SegmentSequence (SEG). Em modo amostra le ate K "
            "structure sets por colecao, priorizando estudos com >=2; em modo completo le "
            "todos. Nao abre CT e nao confirma nada na fonte primaria: o que sai aqui e "
            "indicio para triagem. tem_esofago/multiplos_observadores sao TRI-ESTADO — "
            "null significa NAO MEDIDO."
        ),
        "colecoes": registros,
    }
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(fora, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"gravado: {saida}")
    return fora


# ================================================================ 6. autoteste


# ROIName REAIS, medidos na fonte (API NBIA + pydicom).
ROIS_INTEROBS11 = (
    [f"GTV-1vis-{i}" for i in range(1, 6)] + [f"GTV-1auto-{i}" for i in range(1, 6)]
    + [f"GTV-2vis-{i}" for i in range(1, 6)] + [f"GTV-2auto-{i}" for i in range(1, 6)]
    + ["treshold0,34", "suv2,5", "treshold-pr", "treshold-ln"]
)
ROIS_INTEROBS05 = [  # lidos do proprio RTSTRUCT em 2026-09-05
    "treshold0,34", "suv2,5", "GTV-1auto-2", "GTV-1auto-4", "GTV-1auto-5", "GTV-1vis-2",
    "GTV-1vis-4", "GTV-1vis-5", "GTV-1vis-1", "GTV-1vis-3", "treshold-pr",
    "GTV-1auto-1", "GTV-1auto-3",
]
ROIS_LCTSC = ["Esophagus", "Heart", "Lung_L", "Lung_R", "SpinalCord"]

# O CASO QUE A 1a ONDA ERROU. ROIName reais de Pancreatic-CT-CBCT-SEG, lidos do
# DICOM em disco: interobservador REAL, escrito colado em camelCase.
ROIS_PANCREATIC = ["BowelSmObs1", "BowelSmObs2", "StomachDuoObs1", "StomachDuoObs2",
                   "LUNG_L", "LUNG_R"]

# D1 — as convencoes que o detector TEM que cobrir. (rotulo, nomes, tipo, status)
CONVENCOES = [
    ("sufixo colado camelCase", ["BowelSmObs1", "BowelSmObs2"], "obs", "HIPOTESE"),
    ("prefixo obs", ["Obs1_Esophagus", "Obs2_Esophagus"], "obs", "HIPOTESE"),
    ("prefixo rater", ["Rater1_Esophagus", "Rater2_Esophagus"], "rater", "HIPOTESE"),
    ("prefixo letra", ["A_Esophagus", "B_Esophagus"], "letra", "HIPOTESE"),
    ("separador hifen", ["Esophagus-obs1", "Esophagus-obs2"], "obs", "HIPOTESE"),
    ("separador underscore", ["Esophagus_obs1", "Esophagus_obs2"], "obs", "HIPOTESE"),
    ("separador espaco", ["Esophagus obs 1", "Esophagus obs 2"], "obs", "HIPOTESE"),
    ("separador ponto", ["Esophagus.obs.1", "Esophagus.obs.2"], "obs", "HIPOTESE"),
    ("iniciais", ["Esophagus_JD", "Esophagus_MK"], "iniciais", "HIPOTESE"),
    ("romanos", ["EsophagusI", "EsophagusII"], "romano", "HIPOTESE"),
    ("letras a/b", ["Esophagus_a", "Esophagus_b"], "letra", "HIPOTESE"),
    ("token observer", ["Esophagus_observer1", "Esophagus_observer2"], "observer", "HIPOTESE"),
    ("token reader", ["Eso_reader1", "Eso_reader2"], "reader", "HIPOTESE"),
    ("token annotator", ["Esophagus_annotator1", "Esophagus_annotator2"], "annotator", "HIPOTESE"),
    ("token expert", ["Esophagus_expert1", "Esophagus_expert2"], "expert", "HIPOTESE"),
    ("token vis", ["Esophagus_vis1", "Esophagus_vis2"], "vis", "HIPOTESE"),
    ("token md", ["EsophagusMD1", "EsophagusMD2"], "md", "HIPOTESE"),
    ("token dr", ["Esophagus_dr1", "Esophagus_dr2"], "dr", "HIPOTESE"),
    ("numeros puros", ["Esophagus_1", "Esophagus_2"], "numero", "AMBIGUO"),
    ("base nua + sufixo", ["Esophagus", "Esophagus_2"], "numero", "AMBIGUO"),
    ("armadilha alvo", ["GTV-1", "GTV-2"], "numero", "AMBIGUO"),
]


def _recusa(excecao, fn, *args, **kwargs) -> None:
    """Controle POSITIVO: a guarda TEM que levantar. Silencio aqui e guarda morta."""
    try:
        fn(*args, **kwargs)
    except excecao:
        return
    raise AssertionError(f"{fn.__name__} NAO recusou {args!r} — a guarda nao esta guardando")


def _seg_falso(label: str, algoritmo: str, categoria: str, tipo: str, numero: int = 1):
    """SEG sintetico para o controle de D5 (sem rede, sem arquivo)."""
    from pydicom.dataset import Dataset

    def _cod(sig: str) -> Dataset:
        c = Dataset()
        c.CodeValue = "000000"
        c.CodingSchemeDesignator = "SCT"
        c.CodeMeaning = sig
        return c

    s = Dataset()
    s.SegmentNumber = numero
    s.SegmentLabel = label
    s.SegmentDescription = label
    s.SegmentAlgorithmType = algoritmo
    s.SegmentedPropertyCategoryCodeSequence = [_cod(categoria)]
    s.SegmentedPropertyTypeCodeSequence = [_cod(tipo)]
    return s


def _autoteste() -> None:  # noqa: C901 — e uma lista de checks, nao um algoritmo
    import tempfile

    import nibabel as nib
    import numpy as np
    from pydicom.dataset import Dataset

    # ---------------------------------------- CONTROLE POSITIVO: interobs11
    c = classificar_rois(ROIS_INTEROBS11)
    assert not c["tem_esofago"], f"interobs11 nao tem esofago; achou {c['esofago_oar']}"
    fam = c["padrao_observador"]
    assert len(fam) == 2, f"esperava 2 familias `vis` (GTV-1 e GTV-2), veio {fam}"
    assert all(f["n_membros"] == 5 for f in fam), f"familias sem 5 membros: {fam}"
    assert all(f["tipo"] == "vis" for f in fam), fam
    assert sorted(f["base"] for f in fam) == ["gtv-1", "gtv-2"], fam
    assert len(c["automaticos"]) == 14, c["automaticos"]  # 10 auto + 4 limiar
    assert c["status"] == "HIPOTESE", c["status"]
    assert c["n_observadores_hipotese"] == 5, c["n_observadores_hipotese"]

    # o MESMO controle no caso real de 13 ROIs (sem GTV-2): 1 familia de 5
    c5 = classificar_rois(ROIS_INTEROBS05)
    assert not c5["tem_esofago"] and c5["status"] == "HIPOTESE", c5
    assert [(f["base"], f["tipo"], f["n_membros"]) for f in c5["padrao_observador"]] \
        == [("gtv-1", "vis", 5)], c5["padrao_observador"]
    assert len(c5["automaticos"]) == 8, c5["automaticos"]  # 5 auto + 3 limiar

    # ------------------------- CONTROLE POSITIVO NOVO: Pancreatic-CT-CBCT-SEG
    # O caso que a 1a onda errou. Se este assert nao existir, o conserto de D1
    # nao aconteceu: 'Obs' esta literalmente no nome e o detector antigo nao via.
    pa = classificar_rois(ROIS_PANCREATIC)
    assert pa["status"] == "HIPOTESE", f"Pancreatic saiu {pa['status']}: {pa}"
    bases = sorted((f["base"], f["tipo"], f["n_membros"]) for f in pa["padrao_observador"])
    assert bases == [("bowel-sm", "obs", 2), ("stomach-duo", "obs", 2)], bases
    assert pa["n_observadores_hipotese"] == 2, pa["n_observadores_hipotese"]
    assert pa["familias_ambiguas"] == [], pa["familias_ambiguas"]
    assert [f["base"] for f in pa["familias_descartadas"]] == ["lung"], pa["familias_descartadas"]
    # e o mesmo pelo caminho do censo: multiplos_observadores TEM que ser True
    r_pa, v_pa = resumir([{"study_uid": "s", "series_uid": "u", "rois": ROIS_PANCREATIC,
                           "classificacao": pa}])
    assert r_pa["multiplos_observadores"] is True, r_pa
    assert r_pa["n_observadores_hipotese"] == 2, r_pa
    assert v_pa.startswith("multiplos observadores SEM esofago"), v_pa

    # ---------------------------------------- CONTROLE NEGATIVO: LCTSC
    n = classificar_rois(ROIS_LCTSC)
    assert n["tem_esofago"] and n["esofago_oar"] == ["Esophagus"], n
    assert n["padrao_observador"] == [], f"LCTSC nao tem observador multiplo: {n}"
    assert n["familias_ambiguas"] == [], f"Lung_L/Lung_R viraram familia: {n['familias_ambiguas']}"

    # ---------------------------------------- CONTROLE DE ARMADILHA
    t = classificar_rois(["GTV-1", "GTV-2"])
    assert t["padrao_observador"] == [], f"GTV-1/GTV-2 lidos como observadores: {t}"
    assert len(t["familias_ambiguas"]) == 1 and t["status"] == "AMBIGUO", t

    # ------------------- CONTROLE DE AMBIGUIDADE (D4): ambiguo NAO e negativo
    a = classificar_rois(["Esophagus", "Esophagus_2"])
    assert a["status"] == "AMBIGUO", f"'Esophagus'+'Esophagus_2' saiu {a['status']}: {a}"
    assert len(a["familias_ambiguas"]) == 1, a["familias_ambiguas"]
    assert a["familias_ambiguas"][0]["base_sem_sufixo"] == "Esophagus", a["familias_ambiguas"][0]
    assert a["padrao_observador"] == [], a
    _r, _v = resumir([{"study_uid": "s", "series_uid": "u", "rois": ["Esophagus", "Esophagus_2"],
                       "classificacao": a}])
    assert "AMBIGUA" in _v and "nao e negativo" in _v.lower(), _v

    # ---------------------------------------- D1: as 21 convencoes, uma a uma
    for rotulo, nomes, tipo, status in CONVENCOES:
        cc = classificar_rois(nomes)
        assert cc["status"] == status, f"{rotulo}: status {cc['status']} != {status} ({cc})"
        fams = cc["padrao_observador"] if status == "HIPOTESE" else cc["familias_ambiguas"]
        assert len(fams) == 1, f"{rotulo}: esperava 1 familia, veio {fams}"
        assert fams[0]["tipo"] == tipo, f"{rotulo}: tipo {fams[0]['tipo']} != {tipo}"
        assert fams[0]["n_membros"] == 2, f"{rotulo}: {fams[0]}"

    # a defesa original continua de pe: token no MEIO de palavra nao e observador
    assert classificar_rois(["amd-1", "amd-2"])["padrao_observador"] == [], "amd-N virou 'md'"
    assert classificar_rois(["amd-1", "amd-2"])["status"] == "AMBIGUO"

    # esofago: idioma, grafia e a separacao OAR x tumor
    e = classificar_rois(["Esophagus", "esofago", "Oesophagus", "Esoph", "eso",
                          "Esophagus tumor", "GTV eso", "Musculus_esophagus",
                          "SpinalCord", "Mesothelioma"])
    assert set(e["esofago_oar"]) == {"Esophagus", "esofago", "Oesophagus", "Esoph", "eso",
                                     "Musculus_esophagus"}, e["esofago_oar"]
    assert set(e["esofago_tumor"]) == {"Esophagus tumor", "GTV eso"}, e["esofago_tumor"]

    # o crivo desta fase e SUPERSET do crivo ja em producao (estilo_esofago)
    from scripts.validation.tier2.estilo_esofago import CRIVO_ESOFAGO as CRIVO_ANTIGO
    for nome in ["esophagus", "oesophagus", "esophagus_ce", "Esophagus"]:
        assert CRIVO_ANTIGO.search(nome.lower()) and CRIVO_ESOFAGO.search(_norm(nome)), nome

    # familia por token de observador, com esofago (o caso que a fase PROCURA)
    p = classificar_rois(["Esophagus_obs1", "Esophagus_obs2", "Heart_obs1", "Heart_obs2"])
    assert p["tem_esofago"] and len(p["padrao_observador"]) == 2, p
    assert all(f["n_membros"] == 2 for f in p["padrao_observador"]), p["padrao_observador"]

    # ------------------------------- D3: observadores em ARQUIVOS SEPARADOS
    def _arq(uid, rois, estudo="ESTUDO-1", ref="CT-1", caso="caso-1"):
        return {"case_id": caso, "series_uid": uid, "study_uid": estudo,
                "serie_referenciada": ref, "frame_of_reference_uid": "FOR-1",
                "rois": rois, "classificacao": classificar_rois(rois)}

    s0819 = detectar_entre_arquivos([_arq("A", ["Esophagus", "Heart"]),
                                     _arq("B", ["Esophagus", "Lung_L"])])
    assert len(s0819) == 1 and s0819[0]["esofago_repetido"] == ["esophagus"], s0819
    assert s0819[0]["n_arquivos"] == 2, s0819
    # CT diferente no mesmo estudo (planCT x CBCT) NAO e o mesmo exame
    assert detectar_entre_arquivos([_arq("A", ["Esophagus"], ref="CT-1"),
                                    _arq("B", ["Esophagus"], ref="CT-2")]) == []
    # sem ancora de serie/frame nao se afirma "mesmo exame"
    sem_ancora = [_arq("A", ["Esophagus"]), _arq("B", ["Esophagus"])]
    for r in sem_ancora:
        r["serie_referenciada"] = r["frame_of_reference_uid"] = None
    assert detectar_entre_arquivos(sem_ancora) == []
    # repetir nome AUTOMATICO em dois arquivos nao e dois observadores (g3)
    assert detectar_entre_arquivos([_arq("A", ["Esophagus_auto"]),
                                    _arq("B", ["Esophagus_auto"])]) == []
    # e o veredito enxerga o achado entre arquivos
    _r3, _v3 = resumir([_arq("A", ["Esophagus", "Heart"]), _arq("B", ["Esophagus", "Lung_L"])])
    assert _r3["multiplos_observadores"] is True and _v3.startswith("CANDIDATO"), (_r3, _v3)

    # ------------------------------------------------- D5: leitor de SEG
    ds = Dataset()
    ds.SegmentSequence = [
        _seg_falso("Esophagus", "MANUAL", "Anatomical Structure", "Esophagus", 1),
        _seg_falso("Nodule 1 - Annotation 1", "SEMIAUTOMATIC",
                   "Morphologically Abnormal Structure", "Nodule", 2),
    ]
    segs = ler_segmentos(ds)
    assert [s["algoritmo"] for s in segs] == ["MANUAL", "SEMIAUTOMATIC"], segs
    assert nomes_de_segmentos(segs) == ["Esophagus", "Nodule 1 - Annotation 1"], segs
    rs = resumo_seg(segs)
    assert rs["tem_manual_f2"] is True and rs["todos_automaticos_f2"] is False, rs
    assert rs["segmentos_de_estrutura_anormal_f5"] == ["Nodule 1 - Annotation 1"], rs
    assert "Anatomical Structure" in rs["categorias"], rs
    assert classificar_rois(nomes_de_segmentos(segs))["tem_esofago"], "SEG com esofago perdido"
    assert resumo_seg([])["n_segmentos"] == 0 and resumo_seg([])["tem_manual_f2"] is None
    assert ler_segmentos(Dataset()) == [], "SEG sem SegmentSequence tinha que sair vazio"

    # ---------------------------- D6: tri-estado — lacuna NAO pode virar false
    vazio, vered = resumir([])
    assert vazio["tem_esofago"] is None, vazio
    assert vazio["multiplos_observadores"] is None, vazio
    assert vered.startswith("INCONCLUSIVO"), vered
    assert agregar_tri([None, None]) is None
    assert agregar_tri([None, False]) is False
    assert agregar_tri([None, False, True]) is True
    assert agregar_tri([]) is None

    # ---------------------------------------- guardas: positivo e negativo
    # g1
    _ok_ = exigir_mesma_colecao("LCTSC", "lctsc")            # negativo (nao recusa)
    assert not _ok_["recusou"]
    _recusa(DoisDatasets, exigir_mesma_colecao, "LCTSC", "NSCLC-Radiomics")

    # g2
    assert not exigir_nao_consenso("Esophagus_obs1")["recusou"]
    for mau in ("Esophagus_consensus", "esofago-consenso", "GTV_STAPLE", "Eso_fused",
                "Esophagus_majority"):
        _recusa(ConsensoComoObservador, exigir_nao_consenso, mau)

    # g3
    assert not exigir_nao_automatico("Esophagus_obs1")["recusou"]
    for mau in ("GTV-1auto-1", "treshold0,34", "suv2,5", "Esophagus_nnUNet",
                "esophagus_TS", "Eso_pred"):
        _recusa(MesmoModelo, exigir_nao_automatico, mau)

    # g4
    assert not exigir_identidade_de_observador("Esophagus_obs2")["recusou"]
    assert not exigir_identidade_de_observador("BowelSmObs1")["recusou"]  # D1
    assert not exigir_identidade_de_observador("mask.nii.gz", observador="rater-B")["recusou"]
    for mau in ("Esophagus", "GTV-1", "mask_2"):
        _recusa(SemIdentidadeDeObservador, exigir_identidade_de_observador, mau)

    # g5
    assert not exigir_mesmo_caso("LCTSC-Train-S1-001", "LCTSC-Train-S1-001")["recusou"]
    _recusa(CasosDiferentes, exigir_mesmo_caso, "LCTSC-Train-S1-001", "LCTSC-Train-S1-002")

    # g6 — arquivos de verdade: a guarda reusada le NIfTI, nao dicionario
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        dado = np.zeros((4, 4, 4), dtype=np.uint8)
        dado[1:3, 1:3, 1:3] = 1
        nib.save(nib.Nifti1Image(dado, np.diag([1.0, 1.0, 3.0, 1.0])), d / "a.nii.gz")
        nib.save(nib.Nifti1Image(dado, np.diag([1.0, 1.0, 3.0, 1.0])), d / "b.nii.gz")
        nib.save(nib.Nifti1Image(dado, np.diag([1.0, 1.0, 5.0, 1.0])), d / "c.nii.gz")
        nib.save(nib.Nifti1Image(np.zeros((4, 4, 8), np.uint8),
                                 np.diag([1.0, 1.0, 3.0, 1.0])), d / "d.nii.gz")
        assert not exigir_grade_compativel(d / "a.nii.gz", d / "b.nii.gz")["recusou"]
        _recusa(DesalinhamentoGeometrico, exigir_grade_compativel, d / "a.nii.gz", d / "c.nii.gz")
        _recusa(DesalinhamentoGeometrico, exigir_grade_compativel, d / "a.nii.gz", d / "d.nii.gz")

    # g7 — split REAL da fase 5 (se ausente, a propria ausencia recusa)
    split = fase5.carregar_split()
    assert not exigir_fora_do_holdout_lctsc(split["development"][:3])["recusou"]
    _recusa(TestGasto, exigir_fora_do_holdout_lctsc, [split["test"][0]])
    _recusa(TestGasto, exigir_fora_do_holdout_lctsc, [split["validation"][0]])
    _recusa(TestGasto, exigir_fora_do_holdout_lctsc,
            [split["development"][0], split["test"][-1]])

    # g8 — o dict e o da API; nome digitado a mao nao entra
    boa = {"LicenseName": "Creative Commons Attribution 3.0 Unported License",
           "LicenseURI": "http://creativecommons.org/licenses/by/3.0/"}
    assert exigir_licenca_da_api(boa)["nome"].startswith("Creative Commons")
    for ma in ({}, {"LicenseName": "CC BY 3.0"}, {"LicenseURI": "http://x"},
               {"LicenseName": "", "LicenseURI": ""}):
        _recusa(LicencaNaoConfirmada, exigir_licenca_da_api, ma)

    # g9
    assert not exigir_distancia_em_mm("mm", (0.98, 0.98, 3.0))["recusou"]
    _recusa(DistanciaEmVoxel, exigir_distancia_em_mm, "voxel", (0.98, 0.98, 3.0))
    _recusa(DistanciaEmVoxel, exigir_distancia_em_mm, "indice", None)
    _recusa(DistanciaEmVoxel, exigir_distancia_em_mm, "mm", None)
    _recusa(DistanciaEmVoxel, exigir_distancia_em_mm, "mm", (1.0, 1.0, 0.0))

    # g10
    assert not exigir_sem_fatia_faltante([10, 11, 12], [10, 11, 12])["recusou"]
    _recusa(FatiaFaltante, exigir_sem_fatia_faltante, [10, 11, 12], [10, 12])

    # g11 — null NAO pode ser agregado como false
    assert not exigir_tri_estado(False, "tem_esofago")["recusou"]
    assert not exigir_tri_estado(True, "tem_esofago")["recusou"]
    _recusa(NullComoFalse, exigir_tri_estado, None, "tem_esofago")

    # ------------------------------------------------- D2: amostra estratificada
    def _serie(uid, estudo):
        return {"SeriesInstanceUID": uid, "StudyInstanceUID": estudo, "Modality": "RTSTRUCT"}

    universo = ([_serie(f"u{i}", f"e{i}") for i in range(5)]      # 5 estudos com 1
                + [_serie("z1", "e9"), _serie("z2", "e9")])       # 1 estudo com 2
    esc, cob = _amostra_estratificada(universo, 2)
    assert [s["SeriesInstanceUID"] for s in esc] == ["z1", "z2"], esc
    assert cob["n_estudos_com_multiplos_contornos"] == 1, cob
    assert _amostra_estratificada(universo, 99)[1]["n_estudos_lidos"] == 6
    assert _amostra_estratificada([], 2)[0] == []

    print(f"interobservador.py: autoteste OK — {len(GUARDAS)} guardas com controle positivo e "
          f"negativo; {len(CONVENCOES)} convencoes de nome; controles D1 (Pancreatic Obs1/Obs2), "
          "D3 (entre arquivos), D4 (ambiguo), D5 (SEG) e D6 (tri-estado)")


# ======================================================= 7. mutacao das regras


_REGEX_NUNCA = re.compile(r"(?!x)x")  # nao casa com nada


def verificar_por_mutacao(
    guardas: tuple[str, ...] = GUARDAS, regras: tuple[str, ...] = REGRAS_MUTAVEIS,
) -> list[dict[str, Any]]:
    """Desliga UMA regra por vez e exige que o autoteste CAIA.

    Guarda que nao derruba o teste quando desligada nao esta guardando nada; o
    mesmo vale para as regras do detector (os crivos e as fronteiras de nome).
    Levanta se alguma sobreviver a propria ausencia.
    """
    crivos = {"crivo_esofago": "CRIVO_ESOFAGO", "crivo_tumor": "CRIVO_TUMOR",
              "crivo_consenso": "CRIVO_CONSENSO", "crivo_automatico": "CRIVO_AUTOMATICO"}
    relatorio = []
    for nome in list(guardas) + list(regras):
        alvo = crivos.get(nome)
        original = globals().get(alvo) if alvo else None
        if alvo:
            globals()[alvo] = _REGEX_NUNCA
        else:
            _DESLIGADAS.add(nome)
        try:
            _autoteste()
            caiu, motivo = False, "o autoteste PASSOU sem a regra"
        except AssertionError as e:
            caiu, motivo = True, str(e).splitlines()[0][:150]
        except Exception as e:  # noqa: BLE001 — quebrar tambem e morrer
            caiu, motivo = True, f"{type(e).__name__}: {str(e).splitlines()[0][:120]}"
        finally:
            if alvo:
                globals()[alvo] = original
            else:
                _DESLIGADAS.discard(nome)
        relatorio.append({
            "regra": nome,
            "especie": "guarda" if nome in guardas else "detector",
            "autoteste_caiu": caiu,
            "motivo": motivo,
        })
    return relatorio


# ===================================================================== 8. CLI


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fase 11 — instrumento do censo interobservador")
    p.add_argument("--autoteste", action="store_true", help="guardas + controles, sem rede")
    p.add_argument("--mutacao", action="store_true", help="desliga cada regra e exige que o teste caia")
    p.add_argument("--censo", action="store_true", help="roda o censo e grava JSON")
    p.add_argument("--colecoes", help="lista separada por virgula (em vez da API inteira)")
    p.add_argument("--shard", help="k/n — a colecao i vai para o shard i%%n")
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    p.add_argument("--raiz", type=Path, default=RAIZ_CENSO, help="onde os structure sets caem")
    p.add_argument("--k", type=int, default=K_CONTORNOS, help="structure sets por colecao (amostra)")
    p.add_argument("--completo", action="store_true",
                   help="le a UNIAO de TODOS os structure sets da colecao (ignora --k)")
    a = p.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0
    if a.mutacao:
        rel = verificar_por_mutacao()
        for r in rel:
            print(f"  {r['especie']:8s} {r['regra']:28s} desligada -> autoteste "
                  f"{'CAIU' if r['autoteste_caiu'] else 'PASSOU (INUTIL)'}: {r['motivo']}")
        mortas = sum(1 for r in rel if r["autoteste_caiu"])
        print(f"mutacao: {mortas}/{len(rel)} regras derrubam o autoteste")
        sobreviventes = [r["regra"] for r in rel if not r["autoteste_caiu"]]
        if sobreviventes:
            print(f"SOBREVIVENTES (nao guardam nada): {sobreviventes}")
            return 1
        return 0
    if not (a.censo or a.colecoes):
        p.print_help()
        return 2

    shard = None
    if a.shard:
        i, n = (int(x) for x in a.shard.split("/"))
        if not 0 <= i < n:
            raise SystemExit(f"--shard {a.shard}: precisa de 0 <= k < n")
        shard = (i, n)
    nomes = [c.strip() for c in a.colecoes.split(",")] if a.colecoes else None
    saida = a.saida if not shard else a.saida.with_name(
        f"{a.saida.stem}_shard{shard[0]}de{shard[1]}{a.saida.suffix}")
    rodar_censo(nomes=nomes, shard=shard, saida=saida, k=a.k, raiz=a.raiz, completo=a.completo)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
