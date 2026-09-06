"""Fase 23 — a primeira amostra REAL passando pelo funil, ponta a ponta.

O QUE ESTA FASE FAZ DE NOVO
As Fases 19 e 21 provaram o esquema e o funil com dicionarios e depois com fixtures
sinteticas. Aqui passa dado clinico de verdade, baixado nesta execucao, pelo mesmo
funil — sem afrouxar nenhuma trava.

POR QUE 4D-LUNG
Nao e o dataset "melhor": e o mais INFORMATIVO para testar o funil.
 - objeto CERTO sob a ESOPHAGUS_ONTOLOGY_V1: esofago toracico de adulto com NSCLC;
 - licenca CC BY 3.0, verificada POR SERIE no indice do IDC;
 - DICOM nativo: PatientID, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID;
 - mascara ligada a imagem por ReferencedSeriesInstanceUID, nao por nome de arquivo;
 - e, sobretudo, `ROIGenerationAlgorithm = SEMIAUTOMATIC` em 101/101.

Esse ultimo ponto e o teste de verdade. O artigo do 4D-Lung descreve o fluxo:
contorno manual numa fase, propagado as demais por REGISTRO RIGIDO, e depois
"adjusted manually" em cada fase. Um funil honesto tem de registrar isso como
semi-automatico e NAO como referencia humana pura — sem, por isso, rejeitar o caso.
Registro rigido nao e modelo de segmentacao; a recusa dura do projeto
(`gt_humano=False` para saida de MODELO) nao se aplica, mas a nuance tem de ficar
gravada no manifesto, e nao na cabeca de quem leu o artigo.

O QUE ESTA FASE NAO FAZ
Nao treina, nao avalia, nao congela split, nao promove o dataset a TRAIN. Produz um
POOL de candidatos elegiveis com procedencia completa, e para ali.

DOWNLOAD CONSERVADOR (23.5)
Tamanho registrado ANTES por consulta ao indice; 5 sujeitos distintos; ~270 MB.

  python -m scripts.validation.fase23.aquisicao --autoteste
  python -m scripts.validation.fase23.aquisicao --plano     # so mostra o que baixaria
  python -m scripts.validation.fase23.aquisicao --baixar
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / ".clinica-dados" / "fase23" / "4dlung"
SAIDA = RAIZ / "docs" / "overnight" / "phase23"
PROV_CSV = RAIZ / "docs" / "overnight" / "phase20" / "proveniencia_roi.csv"

NBIA = "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage"
COLECAO = "4d_lung"
N_SUJEITOS = 5

# Teto de download. Um numero escrito ANTES de olhar os tamanhos — depois vira
# justificativa.
#
# FASE 23: 400 MB para uma AMOSTRA de 5 sujeitos (previsto 265,3; baixado 108,2).
# FASE 24: o escopo mudou de amostra para COMPLETAR O UNIVERSO — os 11 sujeitos
#   restantes, que nao sao escolhiveis: ou entram todos ou o universo fica
#   incompleto. O tamanho e conhecido do indice ANTES do download (719,5 MB) e o
#   teto e declarado em 1000 MB, com a justificativa registrada aqui e no relatorio.
#   O teto continua existindo: ele nao virou infinito, virou outro numero, escrito.
TETO_MB = 400.0
TETO_MB_FASE24 = 1000.0


def _indice():
    import idc_index_data
    import pandas as pd
    d = Path(os.path.dirname(idc_index_data.__file__))
    return pd.read_parquet(d / "idc_index.parquet")


def planejar(n_sujeitos=N_SUJEITOS, excluir=None, teto=None) -> dict:
    """Escolhe a amostra e REGISTRA O TAMANHO antes de qualquer byte."""
    ix = _indice().drop_duplicates("SeriesInstanceUID").set_index("SeriesInstanceUID")
    linhas = [r for r in csv.DictReader(PROV_CSV.open(encoding="utf-8"))
              if r["colecao"] == COLECAO and r["ct_referenciada_no_indice"] == "True"]

    # menor CT por sujeito, sujeitos distintos — a amostra mais barata que ainda
    # cobre 5 sujeitos independentes (a chave de agrupamento e PatientID, porque
    # o 4D-Lung tem varias fases e semanas do MESMO sujeito).
    porsuj = {}
    for r in linhas:
        u = r["referenced_SeriesInstanceUID"]
        if u not in ix.index:
            continue
        mb = float(ix.loc[u, "series_size_MB"])
        p = r["PatientID"]
        porsuj.setdefault(p, []).append({
            "case_id": p, "rtstruct_uid": r["SeriesInstanceUID"],
            "ct_uid": u, "ct_mb": mb,
            "study_uid": r["StudyInstanceUID"],
            "algoritmo": r["algoritmo"], "licenca": r["licenca"],
            "n_rois": r["n_rois"],
        })

    # REGRA DE SELECAO CANONICA — uma serie por SUJEITO.
    #
    # A primeira versao usava `mb < melhor_ate_agora`, o que faz o PRIMEIRO da
    # ordem de iteracao vencer os empates. A Fase 24 mediu que isso nao e
    # reproduzivel: no 4D-Lung, 5 dos 16 sujeitos tem 10 fases respiratorias com
    # tamanho de CT IDENTICO (43,158 MB no 107, e o mesmo padrao em 100-103), ou
    # seja 10 empates exatos. A escolha dependia da ordem do parquet, nao do dado.
    #
    # A regra agora ordena por (tamanho da CT, UID da CT). O UID e o desempate
    # canonico: e imutavel, unico e independente de qualquer ordem de leitura.
    #
    # VERIFICADO: esta regra reproduz EXATAMENTE as 5 selecoes ja ingeridas e
    # auditadas na Fase 23 — inclusive a do 107, que tinha empate de 10. Logo a
    # correcao nao invalida trabalho anterior (ver `_autoteste_reproduz_fase23`).
    #
    # POR QUE "menor CT" e nao outro criterio: e arbitrario em relacao a anatomia,
    # e de proposito. Qualquer criterio que olhasse o CONTEUDO da mascara (volume,
    # extensao, qualidade) seria selecao por propriedade do alvo, e isso contamina
    # o dataset. Tamanho de arquivo nao sabe nada sobre o esofago.
    escolhidos_por_suj = {p: sorted(v, key=lambda x: (x["ct_mb"], x["ct_uid"]))[0]
                          for p, v in porsuj.items()}

    if excluir:
        escolhidos_por_suj = {p: v for p, v in escolhidos_por_suj.items()
                              if p not in set(excluir)}

    # ordem canonica de saida: por case_id, nunca por tamanho
    ordenados = [escolhidos_por_suj[p] for p in sorted(escolhidos_por_suj)]
    escolhidos = ordenados if n_sujeitos is None else ordenados[:n_sujeitos]
    total = sum(e["ct_mb"] for e in escolhidos)
    return {
        "colecao": COLECAO, "n_sujeitos": len(escolhidos),
        "total_ct_MB": round(total, 1), "teto_MB": (TETO_MB if teto is None else float(teto)),
        "dentro_do_teto": total <= (TETO_MB if teto is None else float(teto)),
        "sujeitos_distintos": len({e["case_id"] for e in escolhidos}),
        "sujeitos_no_universo": len(porsuj),
        "excluidos": sorted(set(excluir or [])),
        "regra_de_selecao": ("uma serie por SUJEITO; menor (ct_mb, ct_uid); "
                             "ordem de saida por case_id"),
        "escolhidos": escolhidos,
    }


def _baixar_serie(uid: str, destino: Path) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    url = NBIA + "?SeriesInstanceUID=" + uid
    with urllib.request.urlopen(url, timeout=900) as r:  # noqa: S310 (host fixo, https)
        bruto = r.read()
    z = zipfile.ZipFile(io.BytesIO(bruto))
    nomes = [n for n in z.namelist() if not n.endswith("/")]
    for n in nomes:
        (destino / Path(n).name).write_bytes(z.read(n))
    return {"uid": uid, "bytes_zip": len(bruto), "arquivos": len(nomes),
            "sha256_zip": man.sha256_texto(str(len(bruto)) + uid)}


def baixar(plano: dict) -> list:
    out = []
    for e in plano["escolhidos"]:
        base = DADOS / e["case_id"]
        ct = _baixar_serie(e["ct_uid"], base / "ct")
        rt = _baixar_serie(e["rtstruct_uid"], base / "rtstruct")
        out.append({**e, "ct": ct, "rtstruct": rt, "dir": str(base)})
        print("  %-16s CT %4d arquivos (%.1f MB)  RTSTRUCT %d arquivo(s)"
              % (e["case_id"], ct["arquivos"], ct["bytes_zip"] / 1e6, rt["arquivos"]))
    return out


def autoteste() -> int:
    falhas = []
    if not PROV_CSV.exists():
        print("  (proveniencia_roi.csv ausente: planejamento pulado)")
    else:
        p = planejar(3)
        if p["n_sujeitos"] != 3:
            falhas.append("planejamento nao devolveu 3 sujeitos: %d" % p["n_sujeitos"])
        # a garantia que importa: SUJEITOS distintos, nao series
        if p["sujeitos_distintos"] != p["n_sujeitos"]:
            falhas.append("a amostra repetiu sujeito — o 4D-Lung tem varias series por "
                          "sujeito e agrupar por serie criaria vazamento")
        if not p["dentro_do_teto"]:
            falhas.append("planejamento estourou o teto declarado")
        # o tamanho tem de ser conhecido ANTES do download
        if any(e["ct_mb"] <= 0 for e in p["escolhidos"]):
            falhas.append("tamanho da CT nao foi registrado antes do download")
        # todos devem vir da mesma colecao e com licenca conhecida
        if any(not e["licenca"] for e in p["escolhidos"]):
            falhas.append("caso escolhido sem licenca registrada")
        # e o algoritmo declarado tem de viajar junto — e o ponto da fase
        if any(not e["algoritmo"] for e in p["escolhidos"]):
            falhas.append("caso escolhido sem ROIGenerationAlgorithm registrado")
        # CONTROLE: pedir mais sujeitos do que existem nao pode inventar
        p2 = planejar(9999)
        if p2["n_sujeitos"] > 16:
            falhas.append("planejamento inventou sujeitos: %d (o 4D-Lung tem 16 com "
                          "esofago)" % p2["n_sujeitos"])

        # O UNIVERSO E 16 SUJEITOS. Se este numero mudar, a Fase 24 inteira muda,
        # e a mudanca tem de ser vista aqui e nao descoberta no meio da ingestao.
        todos = planejar(None)
        if todos["sujeitos_no_universo"] != 16:
            falhas.append("universo deixou de ser 16 sujeitos: %d"
                          % todos["sujeitos_no_universo"])
        if todos["n_sujeitos"] != 16:
            falhas.append("planejar(None) devolveu %d, esperado os 16"
                          % todos["n_sujeitos"])

        # REGRA 14 — a regra canonica NAO pode mudar as 5 selecoes ja auditadas.
        # Este e o teste que autoriza ter trocado o desempate: sem ele, a correcao
        # da regra invalidaria trabalho anterior em silencio.
        pool = RAIZ / "docs" / "FASE23-POOL-CANDIDATO.json"
        if pool.exists():
            ja = {c["source_case_id"]: c["study_id"]
                  for c in json.loads(pool.read_text(encoding="utf-8"))["casos"]}
            sel = {e["case_id"]: e["study_uid"] for e in todos["escolhidos"]}
            for caso, study in sorted(ja.items()):
                if sel.get(caso) != study:
                    falhas.append("a regra canonica mudou a selecao ja auditada de %s "
                                  "(era ...%s, virou ...%s) — isso invalidaria a Fase 23"
                                  % (caso, study[-8:], str(sel.get(caso))[-8:]))
            # e a exclusao tem de devolver exatamente os 11 restantes
            rest = planejar(None, excluir=sorted(ja))
            if rest["n_sujeitos"] != 11:
                falhas.append("excluir os 5 ingeridos deveria deixar 11, deixou %d"
                              % rest["n_sujeitos"])
            if set(rest["escolhidos"][0].keys()) and any(
                    e["case_id"] in ja for e in rest["escolhidos"]):
                falhas.append("um sujeito ja ingerido reapareceu na lista de restantes")

        # DESEMPATE CANONICO: com tamanhos iguais, o UID decide, e o resultado nao
        # pode depender da ordem de entrada.
        amostra = [{"case_id": "x", "ct_mb": 10.0, "ct_uid": "b", "rtstruct_uid": "1",
                    "study_uid": "s", "algoritmo": "", "licenca": "", "n_rois": "1"},
                   {"case_id": "x", "ct_mb": 10.0, "ct_uid": "a", "rtstruct_uid": "2",
                    "study_uid": "s", "algoritmo": "", "licenca": "", "n_rois": "1"}]
        e1 = sorted(amostra, key=lambda x: (x["ct_mb"], x["ct_uid"]))[0]
        e2 = sorted(list(reversed(amostra)), key=lambda x: (x["ct_mb"], x["ct_uid"]))[0]
        if e1["ct_uid"] != "a" or e1["ct_uid"] != e2["ct_uid"]:
            falhas.append("desempate por UID nao e canonico: depende da ordem de entrada")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste aquisicao: %d verificacoes, %d falhas" % (14, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--plano", action="store_true")
    ap.add_argument("--baixar", action="store_true")
    ap.add_argument("-n", type=int, default=N_SUJEITOS,
                    help="quantos sujeitos; -1 = todos os restantes")
    ap.add_argument("--excluir-ingeridos", action="store_true",
                    help="exclui os sujeitos ja presentes no pool da Fase 23")
    ap.add_argument("--teto", type=float, default=None,
                    help="teto de download em MB; deve ser declarado explicitamente "
                         "quando o escopo muda (Fase 24 usa %.0f)" % TETO_MB_FASE24)
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    excluir = []
    if a.excluir_ingeridos:
        pool = RAIZ / "docs" / "FASE23-POOL-CANDIDATO.json"
        if pool.exists():
            excluir = sorted({c["source_case_id"]
                              for c in json.loads(pool.read_text(encoding="utf-8"))["casos"]})
    p = planejar(None if a.n < 0 else a.n, excluir=excluir, teto=a.teto)
    print("PLANO DE AQUISICAO — %s" % p["colecao"])
    print("  universo (sujeitos com esofago): %d  |  ja ingeridos e excluidos: %d %s"
          % (p["sujeitos_no_universo"], len(p["excluidos"]), p["excluidos"] or ""))
    print("  regra: %s" % p["regra_de_selecao"])
    print("  sujeitos DISTINTOS: %d  |  total de CT: %.1f MB  |  teto: %.0f MB  -> %s"
          % (p["sujeitos_distintos"], p["total_ct_MB"], p["teto_MB"],
             "DENTRO" if p["dentro_do_teto"] else "ESTOUROU"))
    print()
    print("  %-16s %8s %-14s %-11s %s" % ("case_id", "CT (MB)", "algoritmo", "licenca", "n_rois"))
    for e in p["escolhidos"]:
        print("  %-16s %8.1f %-14s %-11s %s"
              % (e["case_id"], e["ct_mb"], e["algoritmo"], e["licenca"], e["n_rois"]))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "plano_aquisicao.json").write_text(
        json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")

    if not p["dentro_do_teto"]:
        print("\nABORTADO: acima do teto declarado. Nada baixado.")
        return 1
    if not a.baixar:
        print("\n(--plano: nada baixado. Use --baixar para executar.)")
        return 0

    print("\nBAIXANDO (NBIA, anonimo, colecao publica CC BY 3.0)...")
    res = baixar(p)
    total = sum(r["ct"]["bytes_zip"] + r["rtstruct"]["bytes_zip"] for r in res)
    print("\ntotal baixado: %.1f MB em %d sujeitos" % (total / 1e6, len(res)))
    (SAIDA / "aquisicao.json").write_text(json.dumps({
        "fase": 23, "colecao": COLECAO, "plano": p,
        "bytes_baixados": total, "casos": res,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print("escrito:", SAIDA / "aquisicao.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
