"""Fase 19 — VRMED-ESOPHAGUS-DATASET-V1: manifesto, split, hashes e travas.

POR QUE ESTE MODULO EXISTE
A Fase 16 mediu o que torna o baseline atual inauditavel, e a lista e curta:
nao ha lista de casos efetivamente usada; 420 de 1.559 imagens de treino nao sao
atribuidas; os pesos publicados sao `fold=0` e o arquivo que diz QUAIS 80 % foram
vistos nunca saiu; e SegTHOR/BTCV semearam a primeira segmentacao do treino, o que
cria circularidade de anotacao para o esofago.

Nenhum desses defeitos e de modelagem. Todos sao de PROCEDENCIA NAO REGISTRADA.
Este modulo e a resposta: torna impossivel um caso entrar sem que a pergunta
"de onde veio este caso?" tenha resposta gravada em disco.

O QUE ELE NAO FAZ
Nao treina, nao baixa, nao avalia, nao preenche split com dado inventado. Ele e
esquema, hash e recusa. `--autoteste` roda inteiro com dado sintetico.

REUSO, NAO SEGUNDA IMPLEMENTACAO
A ingestao de caso ja existe em `scripts/validation/tier2/dataset_esofago.py`, com
as tres recusas (procedencia, grade, mascara vazia). Este modulo NAO a reescreve:
ele adiciona a camada que faltava — identidade, licenca, split e congelamento.

  python -m scripts.validation.baseline_v1.manifesto --autoteste
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
PADRAO = RAIZ / ".clinica-dados" / "baseline_v1"

VERSAO_ESQUEMA = "VRMED-ESOPHAGUS-DATASET-V1"
DESCONHECIDO = "UNKNOWN"
PARTICOES = ("train", "validation", "test")

# Campos exigidos em TODA entrada. Um campo ausente e erro; um campo que o projeto
# nao sabe e DESCONHECIDO explicito. Os dois nao sao a mesma coisa: o primeiro e
# descuido, o segundo e conhecimento sobre o proprio limite.
CAMPOS = (
    "case_id", "study_id", "series_id",
    "image_path", "mask_path", "image_sha256", "mask_sha256",
    "spacing", "orientation", "shape",
    "institution", "acquisition",
    "annotation_source", "annotation_protocol", "annotation_date_known",
    "source_dataset", "source_case_id", "source_doi",
    "license", "license_class",
    "split", "notes",
)

# Classes de licenca. `UNKNOWN` e `CONFLITO` NAO sao a mesma coisa: desconhecida e
# ausencia de informacao; conflitante e presenca de informacao contraditoria, que e
# um estado pior porque parece resolvido. O LyNoS e exatamente o segundo caso.
LICENCAS = {
    "ABERTA_ATRIBUICAO": "permite uso e redistribuicao com atribuicao (CC BY, MIT, BSD, Apache)",
    "ABERTA_NAO_COMERCIAL": "permite uso nao comercial (CC BY-NC e variantes)",
    "ABERTA_SEM_DERIVADAS": "proibe obra derivada (CC BY-ND, CC BY-NC-ND)",
    "RESTRITA": "exige acordo, cadastro ou aprovacao para uso",
    "CONFLITO": "fontes oficiais do MESMO dado declaram licencas diferentes",
    "UNKNOWN": "nenhuma licenca localizada em fonte primaria",
}

# Licencas que NAO podem sustentar um caso num dataset publicavel. Sem derivadas
# reprova porque uma mascara reamostrada ou um recorte JA E obra derivada.
LICENCAS_BLOQUEANTES = ("CONFLITO", "UNKNOWN", "ABERTA_SEM_DERIVADAS", "RESTRITA")


class ManifestoInvalido(ValueError):
    """O manifesto viola uma regra estrutural. Nunca e aviso: e recusa."""


class VazamentoDetectado(ValueError):
    """Um mesmo objeto aparece em duas particoes. Sempre erro, nunca tolerado."""


class AcessoIndevido(PermissionError):
    """Alguem tentou ler uma particao que o contexto atual nao pode ver."""


# ----------------------------------------------------------------------- hashes


def sha256_arquivo(caminho: Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(caminho).open("rb") as fh:
        for pedaco in iter(lambda: fh.read(bloco), b""):
            h.update(pedaco)
    return h.hexdigest()


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _canonico(entradas) -> str:
    """Serializacao estavel do manifesto. Ordem de caso e ordem de chave fixas.

    Sem isto, dois manifestos com o MESMO conteudo teriam hashes diferentes so por
    ordem de insercao, e o congelamento viraria ruido em vez de trava.
    """
    linhas = []
    for e in sorted(entradas, key=lambda x: x["case_id"]):
        linhas.append(json.dumps({k: e[k] for k in CAMPOS}, sort_keys=True, ensure_ascii=False))
    return "\n".join(linhas) + "\n"


# -------------------------------------------------------------------- validacao


def validar_entrada(e: dict) -> list:
    """Erros estruturais de UMA entrada. Lista vazia = entrada valida."""
    erros = []
    faltando = [c for c in CAMPOS if c not in e]
    if faltando:
        erros.append("campos ausentes: " + ", ".join(sorted(faltando)))
        return erros  # sem os campos, o resto nao e verificavel

    sobrando = [c for c in e if c not in CAMPOS]
    if sobrando:
        erros.append("campos nao previstos no esquema: " + ", ".join(sorted(sobrando)))

    if e["split"] not in PARTICOES:
        erros.append("split invalido: %r (esperado um de %s)" % (e["split"], list(PARTICOES)))

    if e["license_class"] not in LICENCAS:
        erros.append("license_class invalida: %r" % (e["license_class"],))

    for campo in ("case_id", "image_sha256", "mask_sha256"):
        if not e[campo] or e[campo] == DESCONHECIDO:
            erros.append("%s nao pode ser vazio nem %s — e identidade, nao metadado"
                         % (campo, DESCONHECIDO))

    for campo in ("image_sha256", "mask_sha256"):
        v = e[campo]
        if isinstance(v, str) and v != DESCONHECIDO:
            if len(v) != 64 or any(c not in "0123456789abcdef" for c in v.lower()):
                erros.append("%s nao e um sha256 hexadecimal de 64 digitos" % campo)

    if e["annotation_date_known"] not in (True, False):
        erros.append("annotation_date_known tem de ser booleano explicito")

    # A regra 19.4 do pedido, virando codigo: procedencia desconhecida NAO entra em
    # TEST sem justificativa registrada. O campo notes e onde a justificativa mora;
    # exigi-la nao vazia impede que a excecao vire silencio.
    if e["split"] == "test":
        indefinidos = [c for c in ("source_dataset", "annotation_source", "institution")
                       if e[c] == DESCONHECIDO]
        if indefinidos and not str(e["notes"]).strip():
            erros.append("caso em TEST com procedencia %s e sem justificativa em notes"
                         % ", ".join(indefinidos))
    return erros


def validar_licenca(e: dict) -> list:
    """19.7 — nenhum caso entra em dataset publicavel sem classificacao de licenca."""
    erros = []
    if e.get("license_class") not in LICENCAS:
        return ["license_class ausente ou invalida"]
    if e["license_class"] in LICENCAS_BLOQUEANTES:
        erros.append("licenca %s bloqueia publicacao (%s); declarado: %r"
                     % (e["license_class"], LICENCAS[e["license_class"]], e.get("license")))
    if e["license_class"] != "UNKNOWN" and e.get("license", DESCONHECIDO) == DESCONHECIDO:
        erros.append("license_class diz %s mas o texto da licenca e %s — classificacao "
                     "sem fonte" % (e["license_class"], DESCONHECIDO))
    return erros


def validar_vazamento(entradas) -> list:
    """19.6 — nenhum objeto pode existir em duas particoes.

    Quatro identidades verificadas, e nao uma: caso, estudo, serie e conteudo. As
    tres primeiras podem ser renomeadas por engano; o sha256 nao pode. Verificar so
    o case_id e o modo classico de deixar a mesma serie entrar duas vezes com nomes
    diferentes.
    """
    erros = []
    for chave, rotulo in (("case_id", "caso"), ("study_id", "estudo"),
                          ("series_id", "serie"), ("image_sha256", "conteudo de imagem"),
                          ("mask_sha256", "conteudo de mascara")):
        onde = {}
        for e in entradas:
            v = e.get(chave)
            if v in (None, "", DESCONHECIDO):
                continue  # desconhecido nao acusa vazamento; ele ja e acusado alhures
            onde.setdefault(v, set()).add(e["split"])
        for v, splits in onde.items():
            if len(splits) > 1:
                erros.append("%s %r aparece em %s" % (rotulo, v, sorted(splits)))
    # duplicata DENTRO da mesma particao tambem e defeito: o mesmo caso contado duas
    # vezes infla n e estreita IC sem que nada tenha sido medido a mais.
    vistos = {}
    for e in entradas:
        vistos.setdefault(e["case_id"], 0)
        vistos[e["case_id"]] += 1
    for c, n in vistos.items():
        if n > 1:
            erros.append("case_id %r repetido %d vezes no manifesto" % (c, n))
    return erros


def validar_manifesto(entradas, publicavel: bool = True) -> dict:
    erros = []
    for e in entradas:
        for msg in validar_entrada(e):
            erros.append("%s: %s" % (e.get("case_id", "<sem case_id>"), msg))
        if publicavel:
            for msg in validar_licenca(e):
                erros.append("%s: %s" % (e.get("case_id", "<sem case_id>"), msg))
    erros.extend(validar_vazamento(entradas))
    return {
        "valido": not erros,
        "n_entradas": len(entradas),
        "erros": erros,
        "por_split": {p: sum(1 for e in entradas if e.get("split") == p) for p in PARTICOES},
    }


# ------------------------------------------------------------- io e congelamento


def carregar(caminho: Path) -> list:
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def gravar(entradas, caminho: Path) -> str:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = _canonico(entradas)
    caminho.write_text(texto, encoding="utf-8")
    return sha256_texto(texto)


def congelar(entradas, destino: Path, versao: str, quando: str) -> dict:
    """19.5 — snapshot com hash do conteudo. Depois disto, mudar exige nova versao.

    `quando` entra por parametro de proposito: um congelamento que carimba a si
    mesmo com o relogio da maquina nao e reproduzivel.
    """
    v = validar_manifesto(entradas)
    if not v["valido"]:
        raise ManifestoInvalido("nao se congela manifesto invalido:\n  " + "\n  ".join(v["erros"]))
    texto = _canonico(entradas)
    snap = {
        "esquema": VERSAO_ESQUEMA,
        "versao": versao,
        "congelado_em": quando,
        "ontologia": onto.VERSAO,
        "ontologia_congelada_em": onto.CONGELADA_EM,
        "n_entradas": len(entradas),
        "por_split": v["por_split"],
        "sha256_manifesto": sha256_texto(texto),
        "sha256_por_caso": {e["case_id"]: {"imagem": e["image_sha256"], "mascara": e["mask_sha256"]}
                            for e in sorted(entradas, key=lambda x: x["case_id"])},
    }
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
    return snap


def verificar_congelamento(entradas, snapshot: dict) -> dict:
    """Falha se o manifesto mudou sem que a versao subisse. Esta e a trava inteira."""
    atual = sha256_texto(_canonico(entradas))
    igual = atual == snapshot["sha256_manifesto"]
    mudancas = []
    if not igual:
        antes = snapshot.get("sha256_por_caso", {})
        agora = {e["case_id"]: {"imagem": e["image_sha256"], "mascara": e["mask_sha256"]}
                 for e in entradas}
        for c in sorted(set(antes) | set(agora)):
            if c not in agora:
                mudancas.append("caso removido: " + c)
            elif c not in antes:
                mudancas.append("caso acrescentado: " + c)
            elif antes[c] != agora[c]:
                mudancas.append("conteudo alterado: " + c)
        if not mudancas:
            mudancas.append("metadado alterado sem mudanca de conteudo (split, licenca, notes...)")
    return {
        "intacto": igual,
        "sha256_congelado": snapshot["sha256_manifesto"],
        "sha256_atual": atual,
        "versao_congelada": snapshot.get("versao"),
        "mudancas": mudancas,
        "exige": None if igual else "VERSION INCREMENT — nova versao, nunca edicao de V1",
    }


# ------------------------------------------------------------------- o carregador


# Quem pode ler o que. A tabela existe para que a resposta nao dependa de alguem
# lembrar da regra na hora de escrever o loop de treino.
PERMISSOES = {
    "treino":    ("train",),
    "validacao": ("train", "validation"),
    "avaliacao": ("test",),
}


def carregar_particao(entradas, split: str, contexto: str) -> list:
    """19.6 — o TEST e inalcancavel a partir do contexto de treino, por construcao.

    Nao e convencao de nome nem comentario: e `AcessoIndevido`. A unica forma de ler
    o TEST e declarar contexto 'avaliacao', que e uma frase que ninguem escreve por
    acidente dentro de um laco de treino.
    """
    if contexto not in PERMISSOES:
        raise AcessoIndevido("contexto desconhecido: %r (esperado %s)"
                             % (contexto, list(PERMISSOES)))
    if split not in PARTICOES:
        raise AcessoIndevido("particao desconhecida: %r" % (split,))
    if split not in PERMISSOES[contexto]:
        raise AcessoIndevido(
            "contexto %r nao pode ler a particao %r (pode ler: %s). "
            "Se isto apareceu durante treino, o vazamento estava prestes a acontecer."
            % (contexto, split, list(PERMISSOES[contexto]))
        )
    return [e for e in entradas if e["split"] == split]


# --------------------------------------------------------------------- autoteste


def _entrada(case_id, split="train", **kw):
    """Entrada sintetica valida. Base dos controles: parte-se do valido e injeta-se erro."""
    e = {
        "case_id": case_id,
        "study_id": "study-" + case_id,
        "series_id": "series-" + case_id,
        "image_path": "casos/%s/gt/image.nii.gz" % case_id,
        "mask_path": "casos/%s/gt/mask_Esophagus.nii.gz" % case_id,
        "image_sha256": sha256_texto("imagem-" + case_id),
        "mask_sha256": sha256_texto("mascara-" + case_id),
        "spacing": [1.0, 1.0, 3.0],
        "orientation": "LPS",
        "shape": [512, 512, 200],
        "institution": "instituicao-" + case_id,
        "acquisition": "TC de planejamento, sem contraste",
        "annotation_source": "contorno manual clinico",
        "annotation_protocol": onto.PROTOCOLO_DE_REFERENCIA,
        "annotation_date_known": True,
        "source_dataset": "SINTETICO",
        "source_case_id": case_id,
        "source_doi": DESCONHECIDO,
        "license": "CC BY 4.0",
        "license_class": "ABERTA_ATRIBUICAO",
        "split": split,
        "notes": "",
    }
    e.update(kw)
    return e


def autoteste() -> int:
    falhas = []

    def exige_erro(nome, entradas, agulha=None, publicavel=True):
        """Controle POSITIVO: o defeito injetado TEM de derrubar a validacao."""
        v = validar_manifesto(entradas, publicavel=publicavel)
        if v["valido"]:
            falhas.append("NAO DETECTOU: " + nome)
        elif agulha and not any(agulha in x for x in v["erros"]):
            falhas.append("detectou pelo motivo errado (%s): %s" % (nome, v["erros"]))

    base = [_entrada("c1", "train"), _entrada("c2", "validation"), _entrada("c3", "test")]

    # controle NEGATIVO: o manifesto saudavel tem de passar. Sem ele, um validador
    # que reprova tudo passaria em todos os controles positivos acima.
    v = validar_manifesto(base)
    if not v["valido"]:
        falhas.append("manifesto valido foi reprovado: " + str(v["erros"]))

    # 19.14.1 — mesmo case_id em dois splits
    exige_erro("case_id em dois splits",
               base + [_entrada("c1", "test")], "aparece em")

    # 19.14.2 — hash trocado: mesmo conteudo em duas particoes
    dup = _entrada("c9", "test", image_sha256=base[0]["image_sha256"])
    exige_erro("mesmo conteudo de imagem em dois splits", base + [dup], "conteudo de imagem")

    # mesma serie sob outro case_id — o vazamento que o case_id sozinho nao pega
    serie = _entrada("c8", "test", series_id=base[0]["series_id"])
    exige_erro("mesma serie em dois splits", base + [serie], "serie")

    # 19.14.4 — mascara sem licenca
    exige_erro("licenca UNKNOWN",
               [_entrada("c1", license_class="UNKNOWN", license=DESCONHECIDO)], "bloqueia publicacao")
    exige_erro("licenca em CONFLITO",
               [_entrada("c1", license_class="CONFLITO", license="CC BY 4.0 / MIT")], "CONFLITO")
    exige_erro("licenca sem derivadas",
               [_entrada("c1", license_class="ABERTA_SEM_DERIVADAS", license="CC BY-NC-ND 4.0")],
               "bloqueia publicacao")

    # 19.14.5 — campo obrigatorio removido
    sem = _entrada("c1")
    del sem["annotation_source"]
    exige_erro("campo obrigatorio ausente", [sem], "campos ausentes")

    # campo NAO previsto tambem e erro: esquema aberto e esquema que nao protege
    exige_erro("campo fora do esquema", [_entrada("c1", extra_inventado="x")],
               "nao previstos")

    # procedencia desconhecida entrando em TEST sem justificativa
    exige_erro("procedencia UNKNOWN em TEST",
               [_entrada("c1", split="test", source_dataset=DESCONHECIDO, notes="")],
               "sem justificativa")
    # ...e COM justificativa tem de passar (senao a regra viraria proibicao total)
    if not validar_manifesto([_entrada("c1", split="test", source_dataset=DESCONHECIDO,
                                       notes="origem sob apuracao na Fase 18")])["valido"]:
        falhas.append("justificativa em notes nao liberou o caso de TEST")

    # sha256 malformado
    exige_erro("sha256 invalido", [_entrada("c1", image_sha256="abc")], "sha256")

    # split invalido
    exige_erro("split invalido", [_entrada("c1", split="treino")], "split invalido")

    # 19.14.7 — o TEST tem de ser inalcancavel do contexto de treino
    for ctx, split in (("treino", "test"), ("treino", "validation"), ("validacao", "test")):
        try:
            carregar_particao(base, split, ctx)
            falhas.append("AcessoIndevido nao levantado: contexto %s leu %s" % (ctx, split))
        except AcessoIndevido:
            pass
    # e o acesso legitimo tem de funcionar (controle negativo do guarda)
    try:
        if len(carregar_particao(base, "train", "treino")) != 1:
            falhas.append("acesso legitimo devolveu numero errado de casos")
        if len(carregar_particao(base, "test", "avaliacao")) != 1:
            falhas.append("avaliacao nao conseguiu ler o test")
    except AcessoIndevido as ex:
        falhas.append("acesso legitimo foi bloqueado: " + str(ex))

    # 19.14.3 e 19.5 — mover caso de validation para test tem de quebrar o congelamento
    snap = congelar(base, PADRAO / "_autoteste_snapshot.json", "V1", "2026-09-06T00:00:00Z")
    intacto = verificar_congelamento(base, snap)
    if not intacto["intacto"]:
        falhas.append("manifesto inalterado foi acusado de mudanca")

    movido = [dict(e) for e in base]
    movido[1]["split"] = "test"
    r = verificar_congelamento(movido, snap)
    if r["intacto"]:
        falhas.append("mover caso de validation para test NAO quebrou o congelamento")
    if r["exige"] != "VERSION INCREMENT — nova versao, nunca edicao de V1":
        falhas.append("congelamento quebrado sem exigir version increment")

    trocado = [dict(e) for e in base]
    trocado[0]["image_sha256"] = sha256_texto("outro conteudo")
    r2 = verificar_congelamento(trocado, snap)
    if r2["intacto"] or not any("conteudo alterado" in m for m in r2["mudancas"]):
        falhas.append("troca de hash nao foi detectada como conteudo alterado")

    # 19.14.6 — alterar a ontologia tem de aparecer no snapshot
    if snap["ontologia"] != "ESOPHAGUS_ONTOLOGY_V1":
        falhas.append("snapshot nao carimbou a ontologia congelada")

    # congelar manifesto invalido tem de ser impossivel
    try:
        congelar(base + [_entrada("c1", "test")], PADRAO / "_autoteste_ruim.json",
                 "V1", "2026-09-06T00:00:00Z")
        falhas.append("congelou um manifesto com vazamento")
    except ManifestoInvalido:
        pass

    # o hash canonico tem de ignorar ordem de insercao
    if sha256_texto(_canonico(base)) != sha256_texto(_canonico(list(reversed(base)))):
        falhas.append("hash canonico depende da ordem de insercao")

    for p in (PADRAO / "_autoteste_snapshot.json", PADRAO / "_autoteste_ruim.json"):
        p.unlink(missing_ok=True)

    for f in falhas:
        print("FALHA:", f)
    print("autoteste manifesto: %d verificacoes, %d falhas" % (24, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    print(VERSAO_ESQUEMA, "— esquema, sem dado.")
    print("campos obrigatorios (%d):" % len(CAMPOS))
    for c in CAMPOS:
        print("   ", c)
    print("\nclasses de licenca:")
    for k, v in LICENCAS.items():
        print("    %-22s %s%s" % (k, v, "   [BLOQUEIA]" if k in LICENCAS_BLOQUEANTES else ""))
    print("\npermissoes de leitura por contexto:")
    for k, v in PERMISSOES.items():
        print("    %-11s -> %s" % (k, list(v)))
    print("\nmanifesto atual:", PADRAO / "manifesto.jsonl")
    ent = carregar(PADRAO / "manifesto.jsonl")
    print("entradas:", len(ent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
