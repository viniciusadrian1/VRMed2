"""Fase 23 — o funil da Fase 21 rodando sobre DICOM clinico de verdade.

A DIFERENCA PARA A FASE 21
La as fixtures eram escritas por nos: sabiamos o que estava dentro. Aqui o dado vem
de fora, e o funil so pode confiar no que o arquivo declara.

O QUE ESTE MODULO EXIGE DE CADA CASO (criterio 23.18), e nada e opcional:
  imagem legivel · mascara legivel · VINCULO CONFIRMADO POR UID · case_id ·
  image_sha256 · mask_sha256 · licenca classificada · source_dataset ·
  source_case_id · annotation_source · ontologia aprovada · mascara nao vazia.
  E, por ser DICOM: study_id e series_id tambem.

O VINCULO E O PONTO (23.8)
A mascara so entra se o RTSTRUCT apontar para a serie de CT por
`ReferencedSeriesInstanceUID` E essa serie for a que temos em disco. Par por nome de
arquivo, por ordem ou por pasta e RECUSADO — sao as tres formas classicas de casar
a mascara de um caso com a imagem de outro.

DADO DERIVADO (23.16)
A mascara voxelizada NAO e o artefato original: o original e o contorno poligonal do
RTSTRUCT. A conversao e feita por `tier2/rtstruct.py` (dcmrtstruct2nii), e cada caso
sai marcado `mascara_origem = "derivada: RTSTRUCT poligonal -> voxel"`. Chamar isso
de "original" seria apagar uma transformacao que muda a fronteira.

  python -m scripts.validation.fase23.ingerir_real --autoteste
  python -m scripts.validation.fase23.ingerir_real
"""

from __future__ import annotations

import argparse
import glob
import json
import shutil
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.baseline_v1 import plano as bplano  # noqa: E402
from scripts.validation.fase21 import funil  # noqa: E402
from scripts.validation.tier2 import geometria  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402
from scripts.validation.tier2 import rtstruct as rtst  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / ".clinica-dados" / "fase23" / "4dlung"
TRAB = RAIZ / ".clinica-dados" / "fase23" / "convertido"
SAIDA = RAIZ / "docs" / "overnight" / "phase23"

U = man.DESCONHECIDO

# Procedencia da colecao, apurada na Fase 20 e no artigo do 4D-Lung. Escrita aqui
# uma vez, viaja com todo caso — e o que o manifesto grava, nao a memoria de quem leu.
ORIGEM_4DLUNG = {
    "source_dataset": "4D-Lung (TCIA)",
    "source_doi": "10.7937/K9/TCIA.2016.ELN8YGLE",
    "institution": U,
    "acquisition": "TC 4D de planejamento de radioterapia, NSCLC adulto",
    "annotation_source": (
        "contorno clinico de radioterapia; ROIGenerationAlgorithm declarado "
        "SEMIAUTOMATIC no proprio RTSTRUCT"
    ),
    "annotation_protocol": U,
    "annotation_date_known": False,
    "license": "CC BY 3.0 (declarada POR SERIE no indice do IDC)",
    "license_class": "ABERTA_ATRIBUICAO",
}


def _uid_da_serie_ct(dir_ct: Path) -> str:
    import pydicom
    for f in sorted(dir_ct.glob("*.dcm")):
        ds = pydicom.dcmread(str(f), stop_before_pixels=True, force=True)
        return str(ds.SeriesInstanceUID)
    return ""


def _rtstruct_do_caso(dir_rt: Path):
    import pydicom
    for f in sorted(dir_rt.glob("*.dcm")):
        ds = pydicom.dcmread(str(f), stop_before_pixels=True, force=True)
        if str(getattr(ds, "Modality", "")) == "RTSTRUCT":
            return f, ds
    return None, None


def vinculo(ds_rt, uid_ct: str) -> dict:
    """23.8 — o RTSTRUCT aponta, POR UID, para a serie de CT que temos em disco?"""
    ref = ""
    try:
        s = (ds_rt.ReferencedFrameOfReferenceSequence[0]
             .RTReferencedStudySequence[0].RTReferencedSeriesSequence[0])
        ref = str(s.SeriesInstanceUID)
    except Exception:  # noqa: BLE001
        pass
    return {
        "referenced_series_uid": ref,
        "ct_em_disco_uid": uid_ct,
        "confirmado": bool(ref) and ref == uid_ct,
        "metodo": "ReferencedSeriesInstanceUID",
        "nao_aceito": "nome de arquivo, ordem ou pasta",
    }


def processar(caso_dir: Path) -> dict:
    dir_ct, dir_rt = caso_dir / "ct", caso_dir / "rtstruct"
    reg = {"case_id": caso_dir.name, "erros": [], "bloqueios": []}

    if not dir_ct.exists() or not dir_rt.exists():
        reg["bloqueios"].append("diretorio de CT ou RTSTRUCT ausente")
        return reg

    uid_ct = _uid_da_serie_ct(dir_ct)
    f_rt, ds_rt = _rtstruct_do_caso(dir_rt)
    if ds_rt is None:
        reg["bloqueios"].append("nenhum RTSTRUCT no diretorio")
        return reg

    v = vinculo(ds_rt, uid_ct)
    reg["vinculo"] = v
    if not v["confirmado"]:
        reg["bloqueios"].append(
            "VINCULO NAO CONFIRMADO: RTSTRUCT referencia %r e a CT em disco e %r"
            % (v["referenced_series_uid"][:24], uid_ct[:24]))
        return reg

    # identidade DICOM (23.7) — as tres do arquivo, mais SOP como extra
    ident = funil.identidade_dicom(dir_ct)
    reg["identidade"] = ident

    # ROI de esofago e o algoritmo DECLARADO no arquivo, nao no indice
    rois = [(str(r.ROIName), str(getattr(r, "ROIGenerationAlgorithm", "") or ""))
            for r in getattr(ds_rt, "StructureSetROISequence", [])]
    from scripts.validation.tier2 import idc_esofago as ie
    eso = ie._nomes_de_esofago([n for n, _ in rois])
    if not eso:
        reg["bloqueios"].append("RTSTRUCT sem ROI de esofago: " + str([n for n, _ in rois]))
        return reg
    nome_eso = eso[0]
    algo = next((a for n, a in rois if n == nome_eso), "")
    reg["roi_esofago"] = {"nome": nome_eso, "algoritmo_declarado": algo or "VAZIO",
                          "n_rois": len(rois), "todas": [n for n, _ in rois]}

    # conversao RTSTRUCT -> voxel. DADO DERIVADO, e sai marcado como tal.
    destino = TRAB / caso_dir.name
    destino.mkdir(parents=True, exist_ok=True)
    try:
        conv = rtst.converter(f_rt, dir_ct, destino, estruturas=[nome_eso])
    except Exception as e:  # noqa: BLE001
        reg["bloqueios"].append("conversao RTSTRUCT->voxel falhou: " + str(e)[:160])
        return reg
    img = Path(conv["imagem"])
    msk = conv["mascaras"].get(nome_eso)
    if msk is None:
        reg["bloqueios"].append("conversao nao produziu mascara para " + nome_eso)
        return reg
    msk = Path(msk)

    # ONTOLOGIA (23.11) — a mesma funcao que julgou LyNoS e LCTSC
    alvo = bplano.validar_alvo(msk)
    reg["ontologia"] = {"aprovado": alvo["aprovado"], "problemas": alvo["problemas"],
                        "medidas": {k: alvo["medidas"][k] for k in
                                    ("binaria", "valor_de_foreground", "volume_ml",
                                     "extensao_axial_mm", "n_componentes_3d",
                                     "buracos_2d_pct", "spacing_mm", "orientacao",
                                     "shape", "dtype", "mascara_vazia")}}
    if not alvo["aprovado"]:
        reg["bloqueios"].append("ontologia reprovou: " + str(alvo["problemas"]))
        return reg

    # GRADE — nunca reamostra
    try:
        geometria.verificar_alinhamento(msk, img, rotulos=("mascara", "imagem"))
    except Exception as e:  # noqa: BLE001
        reg["bloqueios"].append("grade: " + type(e).__name__ + ": " + str(e)[:140])
        return reg

    entrada = {
        "case_id": "4DLUNG-" + caso_dir.name,
        "study_id": ident["study_id"],
        "series_id": ident["series_id"],
        "image_path": str(img), "mask_path": str(msk),
        "image_sha256": man.sha256_arquivo(img),
        "mask_sha256": man.sha256_arquivo(msk),
        "spacing": [round(float(x), 6) for x in alvo["medidas"]["spacing_mm"]],
        "orientation": alvo["medidas"]["orientacao"],
        "shape": list(alvo["medidas"]["shape"]),
        "source_case_id": caso_dir.name,
        "split": "train",
        "notes": ("mascara DERIVADA: contorno poligonal do RTSTRUCT voxelizado por "
                  "dcmrtstruct2nii. ROIGenerationAlgorithm declarado no arquivo: %s. "
                  "Vinculo mascara-imagem confirmado por ReferencedSeriesInstanceUID. "
                  "SOPInstanceUID presentes: %d." % (algo or "VAZIO", ident["n_instancias"])),
        **{k: v for k, v in ORIGEM_4DLUNG.items()},
    }
    erros = man.validar_entrada(entrada) + man.validar_licenca(entrada)
    if erros:
        reg["bloqueios"].append("esquema: " + "; ".join(erros[:3]))
        return reg

    reg["entrada"] = entrada
    reg["mascara_origem"] = "derivada: RTSTRUCT poligonal -> voxel (dcmrtstruct2nii)"
    reg["elegivel"] = True
    return reg


def autoteste() -> int:
    falhas = []

    # vinculo: so confirma quando os UIDs BATEM
    class _S:
        def __init__(self, u):
            self.SeriesInstanceUID = u
    class _RT:
        def __init__(self, u):
            class A:
                pass
            a = A(); a.SeriesInstanceUID = u
            class B:
                pass
            b = B(); b.RTReferencedSeriesSequence = [a]
            class C:
                pass
            c = C(); c.RTReferencedStudySequence = [b]
            self.ReferencedFrameOfReferenceSequence = [c]

    if not vinculo(_RT("1.2.3"), "1.2.3")["confirmado"]:
        falhas.append("vinculo com UIDs iguais nao foi confirmado")
    if vinculo(_RT("1.2.3"), "9.9.9")["confirmado"]:
        falhas.append("VINCULO ACEITOU UIDs DIFERENTES — casaria mascara de um caso "
                      "com imagem de outro")
    class _Vazio:
        pass
    if vinculo(_Vazio(), "1.2.3")["confirmado"]:
        falhas.append("vinculo confirmado sem ReferencedSeriesInstanceUID")
    if vinculo(_RT(""), "")["confirmado"]:
        falhas.append("dois UIDs vazios foram tratados como vinculo valido")

    # a origem declarada tem de ter licenca classificada e nao pode mentir
    if ORIGEM_4DLUNG["license_class"] not in man.LICENCAS:
        falhas.append("license_class da origem e invalida")
    if ORIGEM_4DLUNG["annotation_date_known"] is not False:
        falhas.append("annotation_date_known deveria ser False explicito")
    if "SEMIAUTOMATIC" not in ORIGEM_4DLUNG["annotation_source"]:
        falhas.append("a origem deixou de registrar o algoritmo declarado — e o ponto "
                      "da fase: o caso nao pode virar 'referencia humana pura'")
    # e a ontologia usada e a congelada
    if onto.VERSAO != "ESOPHAGUS_ONTOLOGY_V1":
        falhas.append("ontologia divergente: " + onto.VERSAO)

    for f in falhas:
        print("FALHA:", f)
    print("autoteste ingerir_real: %d verificacoes, %d falhas" % (8, len(falhas)))
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

    casos = sorted([Path(p) for p in glob.glob(str(DADOS / "*")) if Path(p).is_dir()
                    and not Path(p).name.startswith("_")])
    if not casos:
        print("nenhum caso baixado em", DADOS)
        return 1

    regs = []
    for c in casos:
        r = processar(c)
        regs.append(r)
        estado = ("ELEGIVEL" if r.get("elegivel") else
                  "BLOQUEADO: " + (r["bloqueios"][0][:70] if r["bloqueios"] else "?"))
        print("%-16s %s" % (c.name, estado))

    elegiveis = [r for r in regs if r.get("elegivel")]
    print()
    print("ELEGIVEIS: %d de %d" % (len(elegiveis), len(regs)))
    if elegiveis:
        print()
        print("%-22s %-9s %-9s %8s %9s %s"
              % ("case_id", "algoritmo", "orient", "vol mL", "ext mm", "buracos 2D"))
        for r in elegiveis:
            m = r["ontologia"]["medidas"]
            print("%-22s %-9s %-9s %8.2f %9.1f %.4f%%"
                  % (r["entrada"]["case_id"], r["roi_esofago"]["algoritmo_declarado"],
                     m["orientacao"], m["volume_ml"], m["extensao_axial_mm"],
                     m["buracos_2d_pct"]))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "ingestao_real.json").write_text(json.dumps({
        "fase": 23, "colecao": "4D-Lung",
        "n_casos": len(regs), "n_elegiveis": len(elegiveis),
        "criterio_23_18": [
            "imagem legivel", "mascara legivel", "vinculo por UID confirmado",
            "case_id", "image_sha256", "mask_sha256", "licenca classificada",
            "source_dataset", "source_case_id", "annotation_source",
            "ontologia aprovada", "mascara nao vazia", "study_id", "series_id",
        ],
        "casos": regs,
    }, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nescrito:", SAIDA / "ingestao_real.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
