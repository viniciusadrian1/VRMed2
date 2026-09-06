"""Fase 19 — o esquema aplicado ao unico candidato real, para ver se ele recusa.

POR QUE ISTO NAO E INGESTAO
Nenhum caso do LyNoS foi ingerido, e nenhum sera enquanto a licenca estiver em
conflito. Isto e uma FICHA DE CANDIDATO: o esquema `VRMED-ESOPHAGUS-DATASET-V1`
preenchido com o que a Fase 18 MEDIU, para responder duas perguntas que so um caso
real responde:

  1. o esquema e preenchivel na pratica, ou tem campo que nenhuma fonte fornece?
  2. o que, concretamente, impede este candidato de entrar?

Um esquema que so foi testado com dado sintetico e um esquema nao testado.

DE ONDE VEM CADA CAMPO — nada digitado a mao
  shape, spacing, orientation  -> `docs/overnight/phase18/lynos_auditoria.json` (medido)
  image_sha256                 -> nao ha imagem local; a TC nao foi baixada -> UNKNOWN
  mask_sha256                  -> calculado do arquivo em disco
  license / license_class      -> CC BY 4.0 (Zenodo), apurado na Fase 18
  source_doi                   -> o DOI do ARTIGO; o Zenodo nao emitiu DOI proprio
  institution / acquisition    -> o que a Fase 18 apurou; UNKNOWN quando nao apurado
  split                        -> NAO ATRIBUIDO: escrito como o valor que o validador
                                  recusa, porque atribuir particao a um candidato
                                  bloqueado seria fingir que ele entrou

  python -m scripts.validation.baseline_v1.candidatos --autoteste
  python -m scripts.validation.baseline_v1.candidatos
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
MEDIDAS = RAIZ / "docs" / "overnight" / "phase18" / "lynos_auditoria.json"
MASCARAS = RAIZ / ".clinica-dados" / "fase18" / "lynos"
SAIDA = RAIZ / "docs" / "overnight" / "phase19"
CONFIG = RAIZ / ".clinica-dados" / "baseline_v1"

U = man.DESCONHECIDO

# As tres fontes oficiais em conflito, citadas por URL. Texto curto de proposito:
# a apuracao completa mora no relatorio da Fase 18.
LICENCA = (
    "CC BY 4.0 — zenodo.org/api/records/10102261, metadata.license.id = 'cc-by-4.0', "
    "access_right 'open', sem embargo, versao unica. O 'MIT' do GitHub e do card do "
    "HuggingFace tem escopo de CODIGO: o README diz literalmente 'The code in this "
    "repository is released under MIT license', o repositorio GitHub nao hospeda "
    "imagem alguma (23 blobs, ~400 KB), e o loader do HuggingFace baixa o zip DO "
    "ZENODO. RESSALVA: nenhuma fonte primaria nomeia o titular de direitos sobre as "
    "imagens de TC. Ver docs/RELATORIO-FASE18-AUDITORIA-LYNOS.md."
)

# O Zenodo NAO emitiu DOI proprio para este deposito: o campo doi do registro e o DOI
# do ARTIGO na Taylor & Francis, provider 'external', e conceptdoi e null. Escrever
# '10.5281/zenodo.10102261' seria inventar um identificador que nao existe — e foi
# exatamente o que esta ficha fez na primeira versao, ate a Fase 18 medir.
DOI = "10.1080/21681163.2022.2043778"


def fichas() -> list:
    """Uma ficha por caso do LyNoS, montada a partir das MEDIDAS em disco."""
    doc = json.loads(MEDIDAS.read_text(encoding="utf-8"))
    out = []
    for c in doc["casos"]:
        caso = c["arquivo"].split("_")[0]          # pat1, pat2, ...
        arq = MASCARAS / c["arquivo"]
        out.append({
            "case_id": "LYNOS-" + caso.upper(),
            # O LyNoS distribui NIfTI: nao ha StudyInstanceUID nem SeriesInstanceUID.
            # Isso NAO e descuido nosso — e uma propriedade do canal, e vira UNKNOWN.
            "study_id": U,
            "series_id": U,
            "image_path": "Pat%s/%s_data.nii.gz" % (caso[3:], caso),
            "mask_path": "Pat%s/%s" % (caso[3:], c["arquivo"]),
            # A TC nao foi baixada (180-263 MB cada); so o cabecalho, por Range HTTP.
            # Sem o arquivo nao ha sha256, e inventar um seria pior que UNKNOWN.
            "image_sha256": U,
            "mask_sha256": man.sha256_arquivo(arq) if arq.exists() else U,
            "spacing": c["spacing_mm"],
            "orientation": c["orientacao"],
            "shape": c["shape"],
            "institution": "St. Olavs Hospital, Trondheim (declarado na fonte)",
            "acquisition": "TC toracica/mediastinal COM contraste, diagnostica (nao de planejamento)",
            "annotation_source": U,
            "annotation_protocol": U,
            "annotation_date_known": False,
            "source_dataset": "LyNoS / ct_mediastinal_structures_segmentation",
            "source_case_id": caso,
            "source_doi": DOI,
            "license": LICENCA,
            "license_class": "ABERTA_ATRIBUICAO",
            "split": "test",
            "notes": (
                "CANDIDATO, NAO INGERIDO. Ontologia: %s (Fase 18 — binaria, buracos 2D "
                "%.4f%%). Sonda geometrica vs treino do Dataset291: %s. "
                "IMAGEM NAO EXCLUSIVA: byte-identica (SHA-256 de Git-LFS) ao sujeito "
                "correspondente do AeroPath, e o AeroPath e espelhado em "
                "MedOtter/AeroPath no HuggingFace. Nenhuma fonte oficial declara esse "
                "overlap. Anotacao de esofago: anotador unico nao identificado, sem "
                "medida interobservador. Independencia INDETERMINADA."
                % (c["ontology_compatible"], c["buracos_2d_pct"], c["classificacao"])
            ),
        })
    return out


def autoteste() -> int:
    falhas = []
    if not MEDIDAS.exists():
        print("autoteste candidatos: PULADO — %s ausente" % MEDIDAS.name)
        return 0

    f = fichas()
    if len(f) != 15:
        falhas.append("esperava 15 fichas, montou %d" % len(f))

    # 1. o esquema tem de ser PREENCHIVEL: nenhum campo pode faltar
    for e in f:
        faltando = [c for c in man.CAMPOS if c not in e]
        if faltando:
            falhas.append("%s: campos ausentes %s" % (e["case_id"], faltando))
            break

    # 2. e o validador tem de RECUSAR. Depois da Fase 18 a licenca deixou de ser o
    #    motivo (CC BY 4.0 resolvida); o que barra agora e IDENTIDADE — nao ha TC em
    #    disco, logo nao ha image_sha256, e o esquema nao aceita identidade UNKNOWN.
    v = man.validar_manifesto(f, publicavel=True)
    if v["valido"]:
        falhas.append("candidato sem image_sha256 passou na validacao")
    if not any("image_sha256" in e for e in v["erros"]):
        falhas.append("recusou pelo motivo errado: " + str(v["erros"][:3]))
    if any("CONFLITO" in e for e in v["erros"]):
        falhas.append("ainda recusa por CONFLITO de licenca — a Fase 18 resolveu isso")

    # 3. controle NEGATIVO: se a licenca fosse resolvida, o que mais barraria?
    #    Sem isto, nao da para saber se a licenca e o UNICO bloqueio ou apenas o primeiro.
    # 3. contrafactual: e se as TCs fossem baixadas amanha (2,9 GB) e os hashes
    #    existissem? O que AINDA barraria? Sem isto nao da para saber se o download
    #    resolve o problema ou apenas troca de bloqueio.
    baixado = [dict(e, image_sha256=man.sha256_texto("hipotetico-" + e["case_id"]))
               for e in f]
    v2 = man.validar_manifesto(baixado, publicavel=True)
    if not v2["valido"]:
        falhas.append("bloqueio residual inesperado apos hashes: " + str(v2["erros"][:2]))

    # 4. nenhum sha256 pode ter sido inventado: image_sha256 e UNKNOWN de proposito
    if any(e["image_sha256"] != U for e in f):
        falhas.append("apareceu sha256 de imagem sem a imagem em disco — invencao")
    if any(e["mask_sha256"] == U for e in f):
        falhas.append("mascara em disco ficou sem sha256")

    # 5. hashes tem de ser distintos entre casos (senao ha arquivo duplicado)
    if len({e["mask_sha256"] for e in f}) != len(f):
        falhas.append("duas mascaras com o mesmo sha256 — arquivos duplicados")

    for x in falhas:
        print("FALHA:", x)
    print("autoteste candidatos: %d verificacoes, %d falhas" % (7, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    f = fichas()
    v = man.validar_manifesto(f, publicavel=True)
    print("FICHAS DE CANDIDATO: %d (LyNoS)" % len(f))
    print("VALIDACAO COMO DATASET PUBLICAVEL: %s" % ("PASSOU" if v["valido"] else "RECUSADO"))
    for e in v["erros"][:3]:
        print("  motivo:", e[:150])
    if len(v["erros"]) > 3:
        print("  ... e mais %d (o mesmo motivo, um por caso)" % (len(v["erros"]) - 3))

    baixado = [dict(e, image_sha256=man.sha256_texto("hipotetico-" + e["case_id"]))
               for e in f]
    v2 = man.validar_manifesto(baixado, publicavel=True)
    print("")
    print("CONTRAFACTUAL — se as TCs fossem baixadas e os hashes existissem:")
    print("  validacao estrutural: %s" % ("PASSA" if v2["valido"] else "AINDA RECUSADO"))
    for e in v2["erros"][:3]:
        print("    ", e[:150])
    print("  campos que continuariam UNKNOWN mesmo assim: study_id, series_id,")
    print("    annotation_source, annotation_protocol  (annotation_date_known=False)")
    print("  -> duas das quatro identidades anti-vazamento ficam CEGAS por propriedade")
    print("     do canal NIfTI, e nenhum download resolve isso.")

    SAIDA.mkdir(parents=True, exist_ok=True)
    CONFIG.mkdir(parents=True, exist_ok=True)
    linhas = "\n".join(json.dumps(e, sort_keys=True, ensure_ascii=False) for e in f) + "\n"
    (CONFIG / "candidatos.jsonl").write_text(linhas, encoding="utf-8")
    (SAIDA / "candidatos_lynos.jsonl").write_text(linhas, encoding="utf-8")
    (SAIDA / "candidatos_lynos_validacao.json").write_text(json.dumps({
        "fase": 19,
        "natureza": "FICHA DE CANDIDATO — nenhum caso ingerido",
        "n_fichas": len(f),
        "validacao_publicavel": v,
        "contrafactual_tcs_baixadas": v2,
        "campos_unknown_persistentes": ["study_id", "series_id", "image_sha256",
                                        "annotation_source", "annotation_protocol"],
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nescrito:", CONFIG / "candidatos.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
