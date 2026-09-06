"""Fase 21.5 — auditoria de anonimizacao DICOM, e o que ela NAO pode afirmar.

A REGRA QUE ESTE MODULO EXISTE PARA IMPOR
O pedido e explicito: nao afirmar que um dado esta anonimizado so porque
`PatientName` foi removido. Este modulo verifica 4 eixos, e o nome do paciente e
apenas um item do primeiro.

  EIXO 1  TAGS IDENTIFICADORAS   — o conjunto do PS3.15 Anexo E (Basic Application
                                   Level Confidentiality Profile), nao uma lista
                                   de tres tags escolhidas por conveniencia.
  EIXO 2  UIDs                   — UID nao e identificador direto, mas e LIGACAO:
                                   um UID original permite reencontrar o exame no
                                   PACS de origem. O padrao manda remapear.
  EIXO 3  TAGS PRIVADAS          — grupo impar. Fabricantes gravam ali o que quiserem,
                                   inclusive nome e prontuario. Sao o buraco classico.
  EIXO 4  CAMINHO E NOME         — o arquivo pode estar limpo e a pasta chamar-se
                                   com o nome do caso. Metadado tambem mora fora
                                   do arquivo.

O QUE ESTE MODULO NAO PODE FAZER, E DIZ
  - NAO le pixel. Texto queimado na imagem (burned-in annotation) e invisivel aqui.
  - NAO julga reidentificacao por combinacao (data + instituicao + diagnostico raro).
  - NAO substitui parecer juridico nem aprovacao etica. CC BY 4.0 nao e consentimento.

Um resultado "sem achado" deste modulo significa "as 4 varreduras nao acharam",
nunca "o dado esta anonimizado".

  python -m scripts.validation.fase21.anonimizacao --autoteste
  python -m scripts.validation.fase21.anonimizacao --dir <pasta com .dcm>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase21"

# Subconjunto do PS3.15 Anexo E aplicavel a TC. Cada entrada e (tag, nome, acao
# esperada). REMOVER = a tag nao deve existir ou deve estar vazia; SUBSTITUIR = deve
# existir mas com valor nao identificador; MANTER = pode e deve ficar.
TAGS = [
    ("PatientName", "0010,0010", "REMOVER_OU_SUBSTITUIR"),
    ("PatientID", "0010,0020", "SUBSTITUIR"),
    ("PatientBirthDate", "0010,0030", "REMOVER"),
    ("PatientSex", "0010,0040", "MANTER"),
    ("PatientAge", "0010,1010", "MANTER"),
    ("PatientAddress", "0010,1040", "REMOVER"),
    ("PatientTelephoneNumbers", "0010,2154", "REMOVER"),
    ("OtherPatientIDs", "0010,1000", "REMOVER"),
    ("OtherPatientNames", "0010,1001", "REMOVER"),
    ("EthnicGroup", "0010,2160", "REMOVER"),
    ("PatientComments", "0010,4000", "REMOVER"),
    ("ReferringPhysicianName", "0008,0090", "REMOVER"),
    ("PerformingPhysicianName", "0008,1050", "REMOVER"),
    ("OperatorsName", "0008,1070", "REMOVER"),
    ("PhysiciansOfRecord", "0008,1048", "REMOVER"),
    ("InstitutionName", "0008,0080", "REMOVER_OU_SUBSTITUIR"),
    ("InstitutionAddress", "0008,0081", "REMOVER"),
    ("InstitutionalDepartmentName", "0008,1040", "REMOVER"),
    ("StationName", "0008,1010", "REMOVER_OU_SUBSTITUIR"),
    ("AccessionNumber", "0008,0050", "REMOVER_OU_SUBSTITUIR"),
    ("StudyID", "0020,0010", "REMOVER_OU_SUBSTITUIR"),
    ("DeviceSerialNumber", "0018,1000", "REMOVER"),
    ("RequestingPhysician", "0032,1032", "REMOVER"),
    ("ContentCreatorName", "0070,0084", "REMOVER_OU_SUBSTITUIR"),
]

UIDS = ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
        "FrameOfReferenceUID"]

# Valores que o TCIA e outros usam como marcador de anonimizacao. A lista existe
# para NAO acusar um dado corretamente pseudonimizado como identificado.
VAZIO_OU_ANONIMO = {"", "ANONYMOUS", "ANONYMIZED", "ANON", "NONE", "UNKNOWN",
                    "REMOVED", "NA", "N/A", "0", "PATIENT"}

# Nome ou caminho com cara de identificador humano. Heuristica declarada: acusa
# demais de proposito — um falso positivo custa uma conferencia, um falso negativo
# custa um vazamento.
#
# NAO usa \b nas partes numericas, e a razao e um defeito que o controle positivo
# pegou: `_` E caractere de palavra, entao \b nao casa entre "04" e "_" nem entre
# "_" e "123456789". Como underscore e justamente o separador mais comum em nome
# de arquivo medico ("1957-03-04_prontuario_123456789"), o \b tornava a varredura
# cega exatamente no caso mais provavel. Lookaround de digito faz o que se queria.
SUSPEITO_CAMINHO = re.compile(
    r"(?<!\d)(19|20)\d{2}[-_/.]?\d{2}[-_/.]?\d{2}(?!\d)"   # data completa
    r"|(?<!\d)\d{9,}(?!\d)"                                 # numero longo (prontuario)
    r"|(nome|name|paciente|patient|prontuario|mrn|cpf|\brg\b|birth|nasc|dob)",
    re.IGNORECASE)


def _valor(ds, nome):
    v = getattr(ds, nome, None)
    if v is None:
        return None
    return str(v).strip()


def auditar_dicom(diretorio: Path, amostra: int = 50) -> dict:
    """As quatro varreduras sobre uma serie DICOM."""
    import pydicom

    diretorio = Path(diretorio)
    arquivos = sorted(diretorio.rglob("*.dcm"))
    if not arquivos:
        raise FileNotFoundError("nenhum .dcm em " + str(diretorio))
    lidos = arquivos[:amostra]

    # EIXO 1 — tags identificadoras
    eixo1 = []
    for nome, tag, acao in TAGS:
        presentes, valores = 0, set()
        for f in lidos:
            ds = pydicom.dcmread(str(f), stop_before_pixels=True, force=True)
            v = _valor(ds, nome)
            if v is not None and v.upper() not in VAZIO_OU_ANONIMO:
                presentes += 1
                valores.add(v[:40])
        if acao == "MANTER":
            estado = "OK"
        elif presentes == 0:
            estado = "OK"
        elif acao == "SUBSTITUIR":
            # presente e nao vazio e o ESPERADO; o que nao da para saber e se o
            # valor e um pseudonimo ou o identificador de verdade.
            estado = "INDETERMINADO"
        else:
            estado = "ACHADO"
        eixo1.append({"tag": tag, "nome": nome, "acao_esperada": acao,
                      "presente_em": presentes, "de": len(lidos),
                      "estado": estado,
                      "exemplos": sorted(valores)[:2] if estado == "ACHADO" else []})

    # EIXO 2 — UIDs
    ds0 = pydicom.dcmread(str(lidos[0]), stop_before_pixels=True, force=True)
    eixo2 = []
    for u in UIDS:
        v = _valor(ds0, u)
        eixo2.append({
            "uid": u, "presente": v is not None,
            "prefixo": (v.rsplit(".", 1)[0][:32] if v else None),
            "estado": "INDETERMINADO" if v else "AUSENTE",
            "nota": ("UID presente e ESPERADO — e a identidade que o esquema exige. "
                     "O que nao se verifica daqui e se ele foi REMAPEADO na origem; "
                     "um UID original permite reencontrar o exame no PACS de origem."),
        })

    # EIXO 3 — tags privadas (grupo impar)
    privadas = {}
    for f in lidos:
        ds = pydicom.dcmread(str(f), stop_before_pixels=True, force=True)
        for el in ds:
            if el.tag.group % 2 == 1:
                privadas[str(el.tag)] = privadas.get(str(el.tag), 0) + 1
    eixo3 = {"n_tags_privadas_distintas": len(privadas),
             "tags": sorted(privadas)[:20],
             "estado": "ACHADO" if privadas else "OK",
             "nota": ("grupo impar e espaco livre do fabricante; ja se encontrou nome "
                      "e prontuario ali. Presenca nao prova vazamento, mas exige "
                      "inspecao caso a caso.")}

    # EIXO 4 — caminho e nome de arquivo
    achados_caminho = []
    for f in arquivos:
        rel = str(f.relative_to(diretorio.parent))
        if SUSPEITO_CAMINHO.search(rel):
            achados_caminho.append(rel)
    eixo4 = {"arquivos": len(arquivos),
             "suspeitos": achados_caminho[:10],
             "n_suspeitos": len(achados_caminho),
             "estado": "ACHADO" if achados_caminho else "OK"}

    achados = ([e for e in eixo1 if e["estado"] == "ACHADO"]
               + ([eixo3] if eixo3["estado"] == "ACHADO" else [])
               + ([eixo4] if eixo4["estado"] == "ACHADO" else []))
    return {
        "diretorio": str(diretorio),
        "arquivos": len(arquivos), "lidos": len(lidos),
        "eixo1_tags_identificadoras": eixo1,
        "eixo2_uids": eixo2,
        "eixo3_tags_privadas": eixo3,
        "eixo4_caminho": eixo4,
        "n_achados": len(achados),
        "veredito": ("SEM ACHADO NAS 4 VARREDURAS" if not achados
                     else "ACHADOS: %d" % len(achados)),
        "o_que_este_veredito_NAO_significa": [
            "nao significa 'anonimizado' — significa que estas quatro varreduras nao acharam",
            "pixel nao foi lido: texto queimado na imagem e invisivel aqui",
            "reidentificacao por combinacao (data + instituicao + diagnostico raro) nao e avaliada",
            "nao substitui parecer juridico nem aprovacao etica; licenca aberta nao e consentimento",
        ],
    }


def autoteste() -> int:
    import tempfile
    import numpy as np
    import pydicom
    from scripts.validation.fase21.funil import fixture_dicom

    falhas = []
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)

        # A fixture do funil ja nasce pseudonimizada (PatientName = ANONYMOUS).
        d = fixture_dicom(base / "limpo", caso="AUTO-1", n_fatias=3)
        r = auditar_dicom(d)
        if r["n_achados"] != 0:
            falhas.append("fixture limpa acusada: " + str(r["veredito"]))
        # PatientID presente e ESPERADO — nunca pode virar ACHADO
        pid = [e for e in r["eixo1_tags_identificadoras"] if e["nome"] == "PatientID"][0]
        if pid["estado"] != "INDETERMINADO":
            falhas.append("PatientID deveria ser INDETERMINADO, veio " + pid["estado"])
        # e o modulo NAO pode dizer 'anonimizado'
        if "anonimizado" in r["veredito"].lower():
            falhas.append("o veredito afirmou anonimizacao")

        # CONTROLE POSITIVO 1: nome de paciente real tem de ser achado
        d2 = fixture_dicom(base / "sujo", caso="AUTO-2", n_fatias=2)
        for f in sorted(d2.glob("*.dcm")):
            ds = pydicom.dcmread(str(f))
            ds.PatientName = "SILVA^JOAO"
            ds.PatientBirthDate = "19570304"
            ds.InstitutionName = "Hospital das Clinicas"
            ds.save_as(str(f), enforce_file_format=True)
        r2 = auditar_dicom(d2)
        achados = {e["nome"] for e in r2["eixo1_tags_identificadoras"]
                   if e["estado"] == "ACHADO"}
        for esperado in ("PatientName", "PatientBirthDate", "InstitutionName"):
            if esperado not in achados:
                falhas.append("controle positivo falhou: " + esperado + " nao foi achado")

        # CONTROLE POSITIVO 2: tag privada tem de ser achada
        d3 = fixture_dicom(base / "privada", caso="AUTO-3", n_fatias=1)
        f3 = sorted(d3.glob("*.dcm"))[0]
        ds = pydicom.dcmread(str(f3))
        ds.add_new(0x00090010, "LO", "FABRICANTE X")
        ds.save_as(str(f3), enforce_file_format=True)
        r3 = auditar_dicom(d3)
        if r3["eixo3_tags_privadas"]["estado"] != "ACHADO":
            falhas.append("controle positivo falhou: tag privada nao detectada")

        # CONTROLE POSITIVO 3: caminho com data/prontuario tem de ser achado
        d4 = base / "1957-03-04_prontuario_123456789"
        fixture_dicom(d4, caso="AUTO-4", n_fatias=1)
        if auditar_dicom(d4)["eixo4_caminho"]["estado"] != "ACHADO":
            falhas.append("controle positivo falhou: caminho identificador nao detectado")

        # CONTROLE NEGATIVO: caminho neutro NAO pode ser acusado
        d5 = base / "caso_0001"
        fixture_dicom(d5, caso="AUTO-5", n_fatias=1)
        if auditar_dicom(d5)["eixo4_caminho"]["estado"] != "OK":
            falhas.append("controle negativo falhou: caminho neutro acusado")

        # diretorio sem dcm tem de levantar, nao devolver zero em silencio
        try:
            auditar_dicom(base / "vazio_inexistente")
            falhas.append("diretorio sem dcm nao levantou")
        except FileNotFoundError:
            pass

    for f in falhas:
        print("FALHA:", f)
    print("autoteste anonimizacao: %d verificacoes, %d falhas" % (11, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--dir", default=None)
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    import tempfile
    from scripts.validation.fase21.funil import fixture_dicom
    alvo = Path(a.dir) if a.dir else None
    tmp = None
    if alvo is None:
        tmp = Path(tempfile.mkdtemp(prefix="vrmed_anon_"))
        alvo = fixture_dicom(tmp / "fixture", caso="FIX-ANON-1", n_fatias=4)
        print("sem --dir: auditando a fixture sintetica do funil\n")

    try:
        r = auditar_dicom(alvo)
        print("EIXO 1 — tags identificadoras (%d verificadas)"
              % len(r["eixo1_tags_identificadoras"]))
        for e in r["eixo1_tags_identificadoras"]:
            if e["estado"] != "OK":
                print("   %-28s %-22s %-14s %d/%d %s"
                      % (e["nome"], e["tag"], e["estado"], e["presente_em"], e["de"],
                         e["exemplos"]))
        print("   (as demais: OK)")
        print()
        print("EIXO 2 — UIDs: %s" % ", ".join(
            "%s=%s" % (u["uid"], u["estado"]) for u in r["eixo2_uids"]))
        print("EIXO 3 — tags privadas: %d distintas -> %s"
              % (r["eixo3_tags_privadas"]["n_tags_privadas_distintas"],
                 r["eixo3_tags_privadas"]["estado"]))
        print("EIXO 4 — caminho: %d suspeitos de %d arquivos -> %s"
              % (r["eixo4_caminho"]["n_suspeitos"], r["eixo4_caminho"]["arquivos"],
                 r["eixo4_caminho"]["estado"]))
        print()
        print("VEREDITO:", r["veredito"])
        print("E O QUE ELE NAO SIGNIFICA:")
        for n in r["o_que_este_veredito_NAO_significa"]:
            print("   -", n)

        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "anonimizacao.json").write_text(
            json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nescrito:", SAIDA / "anonimizacao.json")
        return 0
    finally:
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
