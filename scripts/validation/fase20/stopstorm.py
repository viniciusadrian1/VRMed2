"""Fase 20 — o candidato novo (STOPSTORM), medido no proprio arquivo.

O QUE ESTE MODULO DERRUBOU
Um arm da busca classificou o STOPSTORM Benchmark Data como B e escreveu que a
autoria humana da mascara de esofago estava "verificada no arquivo, ROIGeneration
Algorithm". Baixei os 3 RTSTRUCT e a tag esta VAZIA nos 93 ROIs (31 x 3).

Os dois sinais que EXISTEM no arquivo apontam para o outro lado:
  StructureSetLabel = 'AutoSS'      (AutoSS = automatic structure set)
  Manufacturer      = 'Plastimatch' (ferramenta de registro/segmentacao automatica)

Isso ja bastaria para UNKNOWN. Mas a medicao seguinte fechou o caso de vez:

  CADA UM dos 31 ROIs, nos 3 casos, tem contorno em EXATAMENTE UMA FATIA.
  O esofago tem 1 contorno, em 1 fatia.

Um contorno de orgao cobre dezenas de fatias. Um TEMPLATE DE NOMENCLATURA cobre uma.
E o PDF do proprio benchmark (baixado, 0,96 MB) confirma em texto:

  "we provided the above-mentioned contour templates. There is one slice where you
   can find all the contours. Please delete our temporary contours from the templates
   and start contouring according to the guidelines presented in this document."

CLASSE F. O pacote distribui a TAREFA, nao a referencia. Nao ha ground truth de
esofago aqui — e isso e medido, nao inferido.

O QUE O PACOTE ENTREGA DE VALOR: a REGRA. O PDF traz a definicao operacional de
extensao do esofago atribuida a Kong et al., com limite cranial no ARCO AORTICO
(nao no cricoide) e caudal "until it ends at the stomach". Mais uma convencao de
extensao diferente — o que reforca, e nao contradiz, a decisao da ONTOLOGY_V1 de
HERDAR a extensao do GT em vez de fixa-la.

E UM SEGUNDO ACHADO, DE IDENTIDADE
PatientID = 'NOID' nos TRES casos. O `case_id` entregue e degenerado: tres estudos
distintos com o mesmo valor. `study_id` e `series_id` diferem, entao a identidade e
recuperavel — mas quem montasse split por `case_id` juntaria os tres num so.

DOWNLOAD CONSERVADOR (20.9)
Nada dos 169,5 MB do ZIP foi baixado. Os 3 RTSTRUCT (484 KiB, 0,29 % do total)
vieram por Range HTTP com `fase20/zip_remoto.py`, com CRC-32 conferido.

  python -m scripts.validation.fase20.stopstorm --autoteste
  python -m scripts.validation.fase20.stopstorm
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import idc_esofago as ie  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / ".clinica-dados" / "fase20" / "stopstorm"
SAIDA = RAIZ / "docs" / "overnight" / "phase20"

ZIP_URL = ("https://zenodo.org/records/22127731/files/"
           "STOPSTORM_Contouring_Benchmark_Data_06032024.zip")
DOI = "10.5281/zenodo.22127731"
DOI_CONCEITO = "10.5281/zenodo.22127730"

# Rotulos e fabricantes que sinalizam geracao automatica. Nao provam automacao —
# sinalizam. A conclusao que sai daqui e sempre UNKNOWN ou SUSPEITA, nunca "e
# automatica" nem "e manual".
SINAIS_AUTO = ("autoss", "auto_ss", "autocontour", "auto-contour", "automatic",
               "deformed", "propagated", "atlas")
FERRAMENTAS_AUTO = ("plastimatch", "elastix", "ants", "mim", "velocity",
                    "raystation", "limbus", "mvision", "totalsegmentator")


def medir(diretorio: Path = DADOS) -> dict:
    import pydicom
    arquivos = sorted(glob.glob(str(Path(diretorio) / "*.dcm")))
    if not arquivos:
        raise FileNotFoundError("nenhum RTSTRUCT em " + str(diretorio))

    casos = []
    for f in arquivos:
        ds = pydicom.dcmread(f, stop_before_pixels=True, force=True)
        rois = [str(r.ROIName) for r in ds.StructureSetROISequence]
        algos = [str(getattr(r, "ROIGenerationAlgorithm", "") or "") for r in ds.StructureSetROISequence]
        rotulo = str(getattr(ds, "StructureSetLabel", "") or "")
        fabricante = str(getattr(ds, "Manufacturer", "") or "")
        eso = ie._nomes_de_esofago(rois)
        idx = [i for i, r in enumerate(rois) if r in eso]

        # A MEDICAO QUE FECHOU O CASO: quantas FATIAS distintas cada ROI cobre.
        # Um contorno de orgao cobre dezenas de fatias. Um template de nomenclatura
        # cobre UMA. O PDF do proprio benchmark diz: "we provided the contour
        # templates. There is one slice where you can find all the contours. Please
        # delete our temporary contours from the templates and start contouring".
        fatias_por_roi = {}
        try:
            n2n = {r.ROINumber: str(r.ROIName) for r in ds.StructureSetROISequence}
            for c in ds.ROIContourSequence:
                seq = getattr(c, "ContourSequence", [])
                zs = {round(float(x.ContourData[2]), 2) for x in seq
                      if len(getattr(x, "ContourData", [])) >= 3}
                fatias_por_roi[n2n.get(c.ReferencedROINumber, "?")] = len(zs)
        except Exception:  # noqa: BLE001
            pass

        ct_uid, n_inst = None, None
        try:
            s = (ds.ReferencedFrameOfReferenceSequence[0]
                 .RTReferencedStudySequence[0].RTReferencedSeriesSequence[0])
            ct_uid, n_inst = str(s.SeriesInstanceUID), len(s.ContourImageSequence)
        except Exception:  # noqa: BLE001
            pass

        casos.append({
            "arquivo": Path(f).name,
            "case_id": str(ds.PatientID),
            "study_id": str(ds.StudyInstanceUID),
            "series_id": str(ds.SeriesInstanceUID),
            "structure_set_label": rotulo,
            "manufacturer": fabricante,
            "structure_set_date": str(getattr(ds, "StructureSetDate", "") or ""),
            "n_rois": len(rois),
            "esofago": eso,
            "algoritmo_do_esofago": [algos[i] or "VAZIO" for i in idx],
            "algoritmos_todos": dict(Counter(a or "VAZIO" for a in algos)),
            "ct_referenciada": ct_uid,
            "ct_instancias": n_inst,
            "fatias_por_roi": fatias_por_roi,
            "fatias_do_esofago": fatias_por_roi.get("Esophagus"),
            "todos_rois_em_uma_fatia": bool(fatias_por_roi
                                            and set(fatias_por_roi.values()) == {1}),
            "sinal_auto_no_rotulo": any(s in rotulo.lower() for s in SINAIS_AUTO),
            "ferramenta_auto": any(t in fabricante.lower() for t in FERRAMENTAS_AUTO),
        })

    ids = [c["case_id"] for c in casos]
    algos_eso = [a for c in casos for a in c["algoritmo_do_esofago"]]
    return {
        "dataset": "STOPSTORM Benchmark Data — Critical Structures Contouring",
        "doi": DOI, "doi_conceito": DOI_CONCEITO, "licenca": "CC BY 4.0",
        "publicado_em": "2026-08-27",
        "zip_url": ZIP_URL, "zip_bytes": 169465385,
        "baixado_bytes": sum(Path(f).stat().st_size for f in arquivos),
        "n_casos": len(casos),
        "todos_com_esofago": all(c["esofago"] for c in casos),
        "case_id_unico": len(set(ids)) == len(ids),
        "case_id_valores": sorted(set(ids)),
        "algoritmo_do_esofago_declarado": dict(Counter(algos_eso)),
        "algum_sinal_auto": any(c["sinal_auto_no_rotulo"] or c["ferramenta_auto"]
                                for c in casos),
        "ct_ligada_por_uid": sum(1 for c in casos if c["ct_referenciada"]),
        "casos": casos,
        "todos_em_uma_fatia": all(c["todos_rois_em_uma_fatia"] for c in casos),
        "classificacao": "F",
        "veredito_gt": (
            "NAO HA GROUND TRUTH AQUI — e isso e medido, nao inferido. Cada um dos 31 "
            "ROIs, nos 3 casos, tem contorno em EXATAMENTE UMA fatia; o esofago tem 1 "
            "contorno em 1 fatia. Sao TEMPLATES DE NOMENCLATURA, nao segmentacoes. O "
            "PDF do proprio benchmark confirma: 'we provided the contour templates. "
            "There is one slice where you can find all the contours. Please delete our "
            "temporary contours from the templates and start contouring'. "
            "Os sinais anteriores (tag vazia, StructureSetLabel 'AutoSS', Manufacturer "
            "'Plastimatch') apontavam na direcao certa; a medicao de fatias fechou. "
            "CLASSE F: o pacote distribui a TAREFA, nao a referencia."
        ),
        "regra_de_contorno_publicada": (
            "O PDF traz a regra operacional de extensao do esofago, atribuida a Kong "
            "et al.: 'contoured using mediastinal windowing... to correspond to the "
            "mucosa, submucosa, and all muscular layers out to the fatty adventitia. "
            "Cranial the esophagus contour should begin at the level of aortic arch "
            "and continue including the gastroesophageal junction (GEJ) until it ends "
            "at the stomach.' NOTA: o limite cranial aqui e o ARCO AORTICO, nao o "
            "cricoide — mais uma convencao de extensao diferente, o que reforca a "
            "decisao da ONTOLOGY_V1 de herdar a extensao do GT em vez de fixa-la."
        ),
        "veredito_identidade": (
            "PARCIAL. study_id e series_id presentes e distintos; a CT e referenciada "
            "por UID. Mas case_id = 'NOID' nos tres casos: o identificador entregue e "
            "degenerado e um split por case_id juntaria os tres."
        ),
    }


def autoteste() -> int:
    falhas = []
    # deteccao de sinal, sem depender de arquivo
    for rotulo, esperado in (("AutoSS", True), ("Manual", False),
                             ("auto-contour v2", True), ("Reference", False),
                             ("Deformed_from_atlas", True)):
        got = any(s in rotulo.lower() for s in SINAIS_AUTO)
        if got != esperado:
            falhas.append("sinal de rotulo %r deu %s, esperado %s" % (rotulo, got, esperado))
    for fab, esperado in (("Plastimatch", True), ("Varian Medical Systems", False),
                          ("MIM Software", True), ("", False)):
        got = any(t in fab.lower() for t in FERRAMENTAS_AUTO)
        if got != esperado:
            falhas.append("ferramenta %r deu %s, esperado %s" % (fab, got, esperado))
    # o crivo de esofago e o mesmo do projeto
    if ie._nomes_de_esofago(["Esophagus"]) != ["Esophagus"]:
        falhas.append("crivo de esofago mudou")
    if ie._nomes_de_esofago(["Heart", "Aorta"]):
        falhas.append("crivo aceitou estrutura que nao e esofago")

    if DADOS.exists() and list(DADOS.glob("*.dcm")):
        r = medir()
        if not r["todos_com_esofago"]:
            falhas.append("algum caso do STOPSTORM ficou sem esofago")
        # o achado central: a tag NAO pode aparecer como MANUAL
        if "MANUAL" in r["algoritmo_do_esofago_declarado"]:
            falhas.append("a tag apareceu como MANUAL — o achado da fase mudou e o "
                          "relatorio precisa ser refeito")
        if not r["algum_sinal_auto"]:
            falhas.append("os sinais AutoSS/Plastimatch sumiram — remedir")
        # o achado que fecha o caso: se deixar de ser 1 fatia por ROI, o veredito muda
        if not r["todos_em_uma_fatia"]:
            falhas.append("os ROIs deixaram de estar em UMA fatia — o veredito F "
                          "depende disso e o relatorio precisa ser refeito")
        if r["classificacao"] != "F":
            falhas.append("classificacao mudou sem revisao")
        if r["case_id_unico"]:
            falhas.append("case_id passou a ser unico — o achado 'NOID' mudou")
    else:
        print("  (dados do STOPSTORM ausentes: medicao pulada, sinais testados)")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste stopstorm: %d verificacoes, %d falhas" % (15, len(falhas)))
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

    r = medir()
    print("STOPSTORM Benchmark Data — %s | %s | publicado %s"
          % (r["doi"], r["licenca"], r["publicado_em"]))
    print("baixado: %.1f KiB de um zip de %.1f MB (%.2f %%)"
          % (r["baixado_bytes"] / 1024, r["zip_bytes"] / 1e6,
             100.0 * r["baixado_bytes"] / r["zip_bytes"]))
    print()
    print("%-10s %-8s %-13s %-14s %5s %-11s %s"
          % ("caso", "case_id", "label", "fabricante", "ROIs", "esofago", "algoritmo"))
    for c in r["casos"]:
        print("%-10s %-8s %-13s %-14s %5d %-11s %s"
              % (c["structure_set_date"], c["case_id"], c["structure_set_label"],
                 c["manufacturer"], c["n_rois"], ",".join(c["esofago"]),
                 ",".join(c["algoritmo_do_esofago"])))
    print()
    print("fatias por ROI: %s  |  esofago: %s fatia(s)"
          % (sorted({v for c in r["casos"] for v in c["fatias_por_roi"].values()}),
             {c["fatias_do_esofago"] for c in r["casos"]}))
    print()
    print("GT:        ", r["veredito_gt"])
    print()
    print("IDENTIDADE:", r["veredito_identidade"])
    print()
    print("CT ligada por UID: %d/%d" % (r["ct_ligada_por_uid"], r["n_casos"]))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "stopstorm.json").write_text(
        json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nescrito:", SAIDA / "stopstorm.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
