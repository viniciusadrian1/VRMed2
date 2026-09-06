"""Fase 20 — o candidato novo (STOPSTORM), medido no proprio arquivo.

O QUE ESTE MODULO DERRUBOU
Um arm da busca classificou o STOPSTORM Benchmark Data como B e escreveu que a
autoria humana da mascara de esofago estava "verificada no arquivo, ROIGeneration
Algorithm". Baixei os 3 RTSTRUCT e a tag esta VAZIA nos 93 ROIs (31 x 3).

Os dois sinais que EXISTEM no arquivo apontam para o outro lado:
  StructureSetLabel = 'AutoSS'      (AutoSS = automatic structure set)
  Manufacturer      = 'Plastimatch' (ferramenta de registro/segmentacao automatica)

Pela regra do projeto — ausencia da tag e UNKNOWN, nunca MANUAL por omissao — a
autoria e UNKNOWN, e o rotulo AutoSS a empurra para "provavelmente automatica ou
semi-automatica". Isso NAO prova que a mascara e ruim: num benchmark de contorno,
o structure set distribuido costuma ser o PONTO DE PARTIDA dado aos centros, nao a
referencia. Prova que ela nao pode entrar como ground truth humano sem apuracao.

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
        "veredito_gt": (
            "UNKNOWN, com sinal de automacao. A tag ROIGenerationAlgorithm esta VAZIA "
            "em todos os ROIs; StructureSetLabel e 'AutoSS' e Manufacturer e "
            "'Plastimatch'. Ausencia da tag e UNKNOWN, nunca MANUAL por omissao — e "
            "os dois sinais existentes apontam para geracao automatica. Nao entra como "
            "ground truth humano sem apuracao documental."
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
