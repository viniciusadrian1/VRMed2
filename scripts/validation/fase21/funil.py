"""Fase 21 — o funil de ingestao inteiro, exercitado em arquivos REAIS.

POR QUE FIXTURE DE VERDADE E NAO DICIONARIO
A Fase 19 provou o esquema com dicionarios sinteticos: 24 autotestes e 17 testes de
suite, todos sobre `dict`. Isso prova a LOGICA e nao prova o FUNIL — nenhum arquivo
foi lido, nenhuma grade foi comparada, nenhum UID foi extraido de um cabecalho.

Aqui as fixtures sao arquivos: uma serie DICOM escrita com pydicom e pares NIfTI
escritos com nibabel. O funil roda ponta a ponta sobre eles.

O MAPA DO FUNIL (21.1), e onde cada etapa pode falhar:

  ENTRADA      arquivos em disco          -> FileNotFoundError
  IDENTIDADE   PatientID/Study/Series/SOP -> UNKNOWN no canal NIfTI (medido, nao suposto)
  PROVENIENCIA Procedencia(gt_humano)     -> ProcedenciaInvalida  [dataset_esofago.py]
  LICENCA      license_class              -> validar_licenca      [manifesto.py]
  IMAGEM       NIfTI legivel              -> erro de leitura
  MASCARA      NIfTI legivel, nao vazia   -> MascaraVazia         [dataset_esofago.py]
  ONTOLOGIA    ESOPHAGUS_ONTOLOGY_V1      -> validar_alvo         [plano.py]
  GRADE        shape/zoom/affine iguais   -> DesalinhamentoGeometrico [geometria.py]
  HASH         sha256 de imagem e mascara -> campo obrigatorio    [manifesto.py]
  MANIFEST     JSONL canonico             -> validar_manifesto
  SPLIT        4 identidades              -> validar_vazamento
  SNAPSHOT     sha256 do manifesto        -> congelar
  CONGELAMENTO comparacao                 -> verificar_congelamento

REUSO, SEMPRE
Nada aqui reimplementa etapa que ja existe. `geometria.verificar_alinhamento`,
`dataset_esofago.Procedencia`, `manifesto.*` e `plano.validar_alvo` sao chamados,
nao copiados. O modulo e o ARAME que liga as pecas, mais as fixtures.

  python -m scripts.validation.fase21.funil --autoteste
  python -m scripts.validation.fase21.funil
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.baseline_v1 import plano  # noqa: E402
from scripts.validation.tier2 import geometria  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase21"

U = man.DESCONHECIDO
QUANDO = "2026-09-06T00:00:00Z"


class GuardaCega(Exception):
    """A guarda consultada NAO acusou o defeito injetado.

    Excecao propria de proposito: `DesalinhamentoGeometrico` do Tier2 e subclasse
    de AssertionError, entao usar AssertionError como sinal confundiria uma recusa
    legitima do projeto com uma guarda quebrada.
    """

# UIDs de teste sob o prefixo 2.25 (UUID-derivado), que o padrao DICOM reserva para
# uso sem registro. Fixos de proposito: fixture com UID sorteado nao e reproduzivel,
# e o teste de determinismo do 21.11 falharia por construcao.
UID_ESTUDO = "2.25.100000000000000000000000000000001"
UID_SERIE = "2.25.100000000000000000000000000000002"
UID_SOP_BASE = "2.25.10000000000000000000000000000100"


# ------------------------------------------------------------------- fixtures


def _cilindro(shape, raio_mm, spacing, deslocamento=(0, 0)):
    """Cilindro solido centrado — a forma mais simples compativel com a ontologia:
    binario, PREENCHIDO, um objeto so."""
    ny, nx, nz = shape
    yy, xx = np.ogrid[:ny, :nx]
    cy, cx = ny / 2 + deslocamento[0], nx / 2 + deslocamento[1]
    d = np.sqrt(((yy - cy) * spacing[1]) ** 2 + ((xx - cx) * spacing[0]) ** 2)
    m = np.zeros(shape, dtype=np.uint8)
    m[(d <= raio_mm)[:, :, None].repeat(nz, axis=2)] = 1
    return m


def fixture_nifti(destino: Path, caso: str = "SINT-001", shape=(64, 64, 40),
                  spacing=(1.0, 1.0, 2.5), raio_mm=6.0, vazia=False,
                  spacing_mascara=None, shape_mascara=None) -> dict:
    """Par imagem+mascara em NIfTI, na MESMA grade — salvo quando pedido diferente.

    `spacing_mascara` e `shape_mascara` existem para fabricar os casos invalidos
    3 e 5 do 21.2 sem escrever um segundo gerador.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    aff = np.diag([spacing[0], spacing[1], spacing[2], 1.0])

    img = np.zeros(shape, dtype=np.int16) - 1000
    img[_cilindro(shape, raio_mm + 2, spacing) > 0] = 40
    p_img = destino / (caso + "_image.nii.gz")
    nib.save(nib.Nifti1Image(img, aff), str(p_img))

    m = np.zeros(shape_mascara or shape, dtype=np.uint8)
    if not vazia:
        sm = spacing_mascara or spacing
        m = _cilindro(shape_mascara or shape, raio_mm, sm)
    aff_m = np.diag([(spacing_mascara or spacing)[0], (spacing_mascara or spacing)[1],
                     (spacing_mascara or spacing)[2], 1.0])
    p_m = destino / (caso + "_mask_Esophagus.nii.gz")
    nib.save(nib.Nifti1Image(m, aff_m), str(p_m))
    return {"imagem": p_img, "mascara": p_m, "caso": caso}


def fixture_dicom(destino: Path, caso: str = "SINT-001", n_fatias: int = 8,
                  spacing=(1.0, 1.0), dz: float = 2.5) -> Path:
    """Serie CT DICOM minima mas VALIDA, com as tags que o 21.3 exige.

    Escreve UIDs fixos: identidade reproduzivel e pre-condicao do teste de
    determinismo, e um UID sorteado tornaria o manifesto diferente a cada execucao.
    """
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian

    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    for i in range(n_fatias):
        fm = FileMetaDataset()
        fm.MediaStorageSOPClassUID = CTImageStorage
        fm.MediaStorageSOPInstanceUID = UID_SOP_BASE + "%03d" % i
        fm.TransferSyntaxUID = ExplicitVRLittleEndian
        fm.ImplementationClassUID = "2.25.1"

        ds = Dataset()
        ds.file_meta = fm
        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = UID_SOP_BASE + "%03d" % i
        ds.StudyInstanceUID = UID_ESTUDO
        ds.SeriesInstanceUID = UID_SERIE
        ds.PatientID = caso
        ds.PatientName = "ANONYMOUS"
        ds.Modality = "CT"
        ds.Rows, ds.Columns = 64, 64
        ds.PixelSpacing = [spacing[1], spacing[0]]
        ds.SliceThickness = dz
        ds.ImagePositionPatient = [0.0, 0.0, i * dz]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.RescaleSlope = 1.0
        ds.RescaleIntercept = -1024.0
        ds.InstanceNumber = i + 1
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.PixelData = (np.full((64, 64), -1000, dtype=np.int16)).tobytes()
        ds.save_as(str(destino / ("fatia%03d.dcm" % i)), enforce_file_format=True)
    return destino


# ----------------------------------------------------------------- identidade


def identidade_dicom(dicom_dir: Path) -> dict:
    """21.3 — o que o canal DICOM entrega. Todas as quatro chaves, mais a geometria."""
    import pydicom
    arquivos = sorted(Path(dicom_dir).glob("*.dcm"))
    if not arquivos:
        raise FileNotFoundError("nenhum .dcm em " + str(dicom_dir))
    ds0 = pydicom.dcmread(str(arquivos[0]), stop_before_pixels=True)
    sops = []
    for f in arquivos:
        d = pydicom.dcmread(str(f), stop_before_pixels=True)
        sops.append(str(d.SOPInstanceUID))
    geo = geometria.metadados_dicom(Path(dicom_dir))
    return {
        "canal": "DICOM",
        "case_id": str(ds0.PatientID),
        "study_id": str(ds0.StudyInstanceUID),
        "series_id": str(ds0.SeriesInstanceUID),
        "sop_instance_uids": sops,
        "sop_unicos": len(set(sops)) == len(sops),
        "n_instancias": len(arquivos),
        "pixel_spacing_mm": geo["pixel_spacing_mm"],
        "slice_thickness_mm": geo["slice_thickness_mm"],
        "espacamento_z_mediano_mm": geo["espacamento_z_mediano_mm"],
        "espacamento_z_uniforme": geo["espacamento_z_uniforme"],
        "image_orientation_patient": geo["image_orientation_patient"],
        "rescale_slope": float(getattr(ds0, "RescaleSlope", 1.0)),
        "rescale_intercept": float(getattr(ds0, "RescaleIntercept", 0.0)),
        # COMPOSICAO CORRIGIDA. A primeira versao contava SOPInstanceUID como a
        # quarta identidade do esquema e o sha256 como identidade do NIfTI — misturando
        # dois esquemas diferentes. As quatro chaves anti-vazamento do
        # VRMED-ESOPHAGUS-DATASET-V1 sao case_id, study_id, series_id e sha256 DO
        # CONTEUDO; o sha256 e calculado localmente e existe IGUALMENTE nos dois canais.
        # Logo o ganho real do DICOM sobre o NIfTI e +2 (study_id e series_id), e o
        # SOPInstanceUID e um extra do DICOM, nao uma das quatro.
        "identidades_do_arquivo": 3,
        "quais_do_arquivo": ["case_id", "study_id", "series_id"],
        "sha256_computavel": True,
        "identidades_verificaveis_das_4": 4,
        "extras_do_canal": ["SOPInstanceUID (por instancia)"],
    }


def identidade_nifti(imagem: Path) -> dict:
    """21.4 — o que o canal NIfTI entrega, e o que ele NAO pode entregar.

    O cabecalho NIfTI-1 nao tem campo para identidade de estudo ou de serie. Isso
    nao e limitacao da nossa leitura: e ausencia no formato. Portanto study_id e
    series_id sao UNKNOWN, e falsifica-los seria inventar procedencia.
    """
    d = geometria.descrever_nifti(Path(imagem))
    return {
        "canal": "NIfTI",
        "case_id": "derivavel do nome do arquivo ou do manifesto da fonte, NUNCA do cabecalho",
        "study_id": U,
        "series_id": U,
        "sop_instance_uids": [],
        "motivo_unknown": ("o cabecalho NIfTI-1 nao tem campo de StudyInstanceUID nem de "
                           "SeriesInstanceUID; o formato nao os carrega"),
        "shape": list(d["shape"]),
        "spacing_mm": list(d["zooms_mm"]),
        "orientacao": d["orientacao"],
        "identidades_do_arquivo": 0,
        "quais_do_arquivo": [],
        "case_id_origem": "nome de arquivo ou manifesto da fonte — externo ao cabecalho",
        "sha256_computavel": True,
        "identidades_verificaveis_das_4": 2,
        "extras_do_canal": [],
        "regras_impossiveis_de_verificar": [
            "mesmo estudo em duas particoes (validar_vazamento por study_id)",
            "mesma serie em duas particoes (validar_vazamento por series_id)",
        ],
    }


# --------------------------------------------------------------------- funil


def ingerir(imagem: Path, mascara: Path, identidade: dict, licenca: dict,
            split: str, origem: dict) -> dict:
    """As doze etapas, na ordem, sobre arquivos reais. Levanta na primeira falha.

    A ordem importa e e a mesma de `dataset_esofago._normalizar`: identidade,
    depois grade, depois conteudo, depois ontologia. Nada e gravado antes de todas
    passarem — um manifesto com caso reprovado e pior que manifesto nenhum.
    """
    imagem, mascara = Path(imagem), Path(mascara)
    if not imagem.exists() or not mascara.exists():
        raise FileNotFoundError("imagem ou mascara ausente")

    # GRADE — reusa o verificador do Tier2. Nunca reamostra.
    alinhamento = geometria.verificar_alinhamento(mascara, imagem,
                                                  rotulos=("mascara", "imagem"))
    # ONTOLOGIA + MASCARA VAZIA — reusa a mesma funcao que julgou o LyNoS
    alvo = plano.validar_alvo(mascara)
    if not alvo["aprovado"]:
        raise ValueError("alvo reprovado na ontologia: " + str(alvo["problemas"]))

    desc = alinhamento["imagem"]
    e = {
        "case_id": identidade["case_id"],
        "study_id": identidade.get("study_id", U),
        "series_id": identidade.get("series_id", U),
        "image_path": str(imagem),
        "mask_path": str(mascara),
        "image_sha256": man.sha256_arquivo(imagem),
        "mask_sha256": man.sha256_arquivo(mascara),
        "spacing": [round(float(v), 6) for v in desc["zooms_mm"]],
        "orientation": desc["orientacao"],
        "shape": list(desc["shape"]),
        "institution": origem.get("institution", U),
        "acquisition": origem.get("acquisition", U),
        "annotation_source": origem.get("annotation_source", U),
        "annotation_protocol": origem.get("annotation_protocol", U),
        "annotation_date_known": bool(origem.get("annotation_date_known", False)),
        "source_dataset": origem.get("source_dataset", U),
        "source_case_id": origem.get("source_case_id", U),
        "source_doi": origem.get("source_doi", U),
        "license": licenca["license"],
        "license_class": licenca["license_class"],
        "split": split,
        "notes": origem.get("notes", ""),
    }
    erros = man.validar_entrada(e) + man.validar_licenca(e)
    if erros:
        raise ValueError("entrada invalida: " + "; ".join(erros))
    return e


LICENCA_OK = {"license": "CC BY 4.0", "license_class": "ABERTA_ATRIBUICAO"}
ORIGEM_OK = {
    "institution": "fixture sintetica",
    "acquisition": "fabricada por scripts.validation.fase21.funil",
    "annotation_source": "geometria analitica — cilindro solido",
    "annotation_protocol": onto.PROTOCOLO_DE_REFERENCIA,
    "annotation_date_known": True,
    "source_dataset": "FIXTURE-FASE21",
    "source_case_id": "cil-1",
    "source_doi": U,
    "notes": "",
}


def rodar_funil(base: Path) -> dict:
    """Uma passada completa: DICOM + NIfTI, manifesto canonico, snapshot."""
    base = Path(base)
    dcm = fixture_dicom(base / "dicom", caso="FIX-DICOM-1")
    idd = identidade_dicom(dcm)

    entradas = []
    for i, split in ((1, "train"), (2, "train"), (3, "validation"), (4, "test")):
        f = fixture_nifti(base / "nifti", caso="FIX-%03d" % i, raio_mm=5.0 + i * 0.5)
        ident = {"case_id": "FIX-%03d" % i,
                 # o caso 1 herda a identidade DICOM completa; os demais sao NIfTI puro
                 "study_id": idd["study_id"] if i == 1 else U,
                 "series_id": idd["series_id"] if i == 1 else U}
        origem = dict(ORIGEM_OK, source_case_id="cil-%d" % i)
        if split == "test":
            origem = dict(origem, notes="fixture de TEST; procedencia sintetica declarada")
        entradas.append(ingerir(f["imagem"], f["mascara"], ident, LICENCA_OK, split, origem))

    v = man.validar_manifesto(entradas)
    caminho = base / "manifesto.jsonl"
    sha_manifesto = man.gravar(entradas, caminho)
    snap = man.congelar(entradas, base / "snapshot.json", "V1", QUANDO)
    return {
        "identidade_dicom": idd,
        "identidade_nifti": identidade_nifti(
            (base / "nifti" / "FIX-001_image.nii.gz")),
        "entradas": entradas,
        "validacao": v,
        "sha256_manifesto": sha_manifesto,
        "snapshot": snap,
        "congelamento": man.verificar_congelamento(entradas, snap),
    }


# ------------------------------------------------- 21.2 — os 14 casos controlados


def casos_controlados(base: Path) -> list:
    """Um caso valido e treze defeitos. Cada defeito TEM de ser recusado.

    Os defeitos 1-6 sao de ARQUIVO (so aparecem com fixture real — foi por isso que
    a Fase 19, que so usou dicionarios, nao podia te-los testado). Os 7-14 sao de
    esquema e ja tinham cobertura; entram aqui de novo porque agora atravessam o
    funil inteiro em vez de chamar o validador direto.
    """
    base = Path(base)
    out = []

    def tenta(nome, fn, deve_falhar=True):
        """GuardaCega NAO conta como recusa — conta como falha do teste.

        Os casos 6 e 9-14 nao podem so "levantar alguma coisa": eles consultam a
        guarda e, se ela NAO acusar, sinalizam isso. Se este bloco tratasse esse
        sinal como recusa, uma guarda quebrada apareceria como OK — foi o que a
        primeira versao deste harness fazia, e os 14 casos passavam sem provar nada.

        O sinal e uma excecao PROPRIA e nao AssertionError: a segunda versao usou
        AssertionError e quebrou os casos 3-5, porque `DesalinhamentoGeometrico`
        do Tier2 JA E subclasse de AssertionError — uma recusa legitima do projeto
        seria lida como guarda cega. A hierarquia de excecoes existente manda.
        """
        try:
            fn()
            ok, erro, obtido = (not deve_falhar), "", "ACEITA"
        except GuardaCega as ex:
            ok, erro, obtido = False, "GUARDA CEGA: " + str(ex)[:150], "NAO DETECTOU"
        except Exception as ex:  # noqa: BLE001
            ok, erro, obtido = deve_falhar, type(ex).__name__ + ": " + str(ex)[:150], "RECUSA"
        out.append({"caso": nome, "esperado": "RECUSA" if deve_falhar else "ACEITA",
                    "obtido": obtido, "passou": ok, "erro": erro})

    def _ing(f, ident=None, lic=None, split="train", origem=None):
        return ingerir(f["imagem"], f["mascara"],
                       ident or {"case_id": f["caso"], "study_id": U, "series_id": U},
                       lic or LICENCA_OK, split, origem or ORIGEM_OK)

    # 1 — caso VALIDO. Controle negativo da lista inteira: sem ele, um funil que
    #     recusa tudo passaria nos treze defeitos e pareceria excelente.
    f_ok = fixture_nifti(base / "c01", caso="C01")
    tenta("01 caso valido", lambda: _ing(f_ok), deve_falhar=False)

    # 2 — mascara vazia
    f = fixture_nifti(base / "c02", caso="C02", vazia=True)
    tenta("02 mascara vazia", lambda: _ing(f))

    # 3 — spacing incompativel entre imagem e mascara
    f = fixture_nifti(base / "c03", caso="C03", spacing_mascara=(1.0, 1.0, 3.0))
    tenta("03 spacing incompativel", lambda: _ing(f))

    # 4 — orientacao incompativel (affine com eixo invertido so na mascara)
    d = base / "c04"
    f = fixture_nifti(d, caso="C04")
    m = nib.load(str(f["mascara"]))
    nib.save(nib.Nifti1Image(np.asanyarray(m.dataobj),
                             np.diag([-1.0, 1.0, 2.5, 1.0])), str(f["mascara"]))
    tenta("04 orientacao incompativel", lambda: _ing(f))

    # 5 — shape incompativel
    f = fixture_nifti(base / "c05", caso="C05", shape_mascara=(64, 64, 30))
    tenta("05 imagem e mascara com shapes diferentes", lambda: _ing(f))

    # 6 — hash alterado depois do congelamento
    def hash_alterado():
        d6 = base / "c06"
        f6 = fixture_nifti(d6, caso="C06")
        e6 = _ing(f6)
        snap = man.congelar([e6], d6 / "s.json", "V1", QUANDO)
        f6["mascara"].write_bytes(f6["mascara"].read_bytes() + b"\x00")
        e6b = dict(e6, mask_sha256=man.sha256_arquivo(f6["mascara"]))
        r = man.verificar_congelamento([e6b], snap)
        if r["intacto"]:
            raise GuardaCega("verificar_congelamento nao viu o hash trocado")
        raise ValueError("congelamento quebrado: " + str(r["mudancas"]))
    tenta("06 hash alterado apos congelamento", hash_alterado)

    # 7, 8 — licenca
    f = fixture_nifti(base / "c07", caso="C07")
    tenta("07 licenca UNKNOWN",
          lambda: _ing(f, lic={"license": U, "license_class": "UNKNOWN"}))
    tenta("08 licenca CONFLITO",
          lambda: _ing(f, lic={"license": "CC BY 4.0 / MIT", "license_class": "CONFLITO"}))

    # 9-12 — vazamento por cada uma das quatro identidades
    def vaza(nome, a, b):
        v = man.validar_manifesto([a, b])
        if v["valido"]:
            raise GuardaCega("validar_vazamento nao viu " + nome)
        raise ValueError("vazamento: " + "; ".join(v["erros"][:2]))

    f9 = fixture_nifti(base / "c09", caso="C09")
    e_train = _ing(f9)
    e_test = dict(_ing(f9, split="test"), case_id="C09")
    tenta("09 mesmo case_id em dois splits", lambda: vaza("case_id", e_train, e_test))

    e_a = dict(e_train, study_id=UID_ESTUDO)
    e_b = dict(e_train, case_id="OUTRO", study_id=UID_ESTUDO, split="test",
               image_sha256=man.sha256_texto("x"), mask_sha256=man.sha256_texto("y"),
               series_id="s-outro")
    tenta("10 mesmo study_id, case_id diferente", lambda: vaza("study", e_a, e_b))

    e_c = dict(e_train, series_id=UID_SERIE)
    e_d = dict(e_train, case_id="OUTRO2", series_id=UID_SERIE, split="test",
               image_sha256=man.sha256_texto("x2"), mask_sha256=man.sha256_texto("y2"))
    tenta("11 mesma series_id, case_id diferente", lambda: vaza("series", e_c, e_d))

    e_e = dict(e_train, case_id="OUTRO3", split="test", study_id="st-3", series_id="se-3")
    tenta("12 mesmo CONTEUDO com ids diferentes", lambda: vaza("hash", e_train, e_e))

    # 13 — ontologia errada: anel oco (so parede), o alvo que a V1 nao aceita
    d13 = base / "c13"
    f13 = fixture_nifti(d13, caso="C13")
    yy, xx = np.ogrid[:64, :64]
    dist = np.sqrt((yy - 32) ** 2 + (xx - 32) ** 2)
    anel = np.zeros((64, 64, 40), dtype=np.uint8)
    anel[((dist >= 4) & (dist <= 7))[:, :, None].repeat(40, axis=2)] = 1
    nib.save(nib.Nifti1Image(anel, np.diag([1.0, 1.0, 2.5, 1.0])), str(f13["mascara"]))
    tenta("13 ontologia errada (anel oco, so parede)", lambda: _ing(f13))

    # 14 — TEST tentando ser lido pelo treino
    def test_no_treino():
        man.carregar_particao([e_test], "test", "treino")
        raise GuardaCega("carregar_particao deixou o treino ler o TEST")
    tenta("14 TEST acessado em contexto de treino", test_no_treino)

    return out


# --------------------------------------------------------------------- autoteste


def autoteste() -> int:
    falhas = []
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)

        # fixture DICOM: as quatro identidades tem de sair do cabecalho
        dcm = fixture_dicom(base / "d", caso="AUTO-1", n_fatias=5)
        i = identidade_dicom(dcm)
        if i["case_id"] != "AUTO-1" or i["study_id"] != UID_ESTUDO or i["series_id"] != UID_SERIE:
            falhas.append("identidade DICOM lida errado: " + str(i)[:200])
        if len(i["sop_instance_uids"]) != 5 or not i["sop_unicos"]:
            falhas.append("SOPInstanceUID nao unico ou incompleto")
        if i["identidades_verificaveis_das_4"] != 4 or i["identidades_do_arquivo"] != 3:
            falhas.append("composicao de identidade do DICOM errada: 3 do arquivo + sha256")
        if "sha256" in " ".join(i["quais_do_arquivo"]):
            falhas.append("sha256 listado como identidade DICOM — ele e computado localmente")
        if i["rescale_intercept"] != -1024.0 or i["rescale_slope"] != 1.0:
            falhas.append("rescale lido errado")
        if not i["espacamento_z_uniforme"]:
            falhas.append("espacamento z da fixture nao saiu uniforme")

        # fixture NIfTI: e o ponto do 21.4 — study/series TEM de ser UNKNOWN
        f = fixture_nifti(base / "n", caso="AUTO-2")
        n = identidade_nifti(f["imagem"])
        if n["study_id"] != U or n["series_id"] != U:
            falhas.append("NIfTI declarou identidade que o formato nao carrega")
        if n["identidades_verificaveis_das_4"] != 2 or n["identidades_do_arquivo"] != 0:
            falhas.append("composicao de identidade do NIfTI errada")
        # o ganho do DICOM sobre o NIfTI e exatamente +2, e nao +2 por acaso:
        # sao study_id e series_id, os dois que o formato NIfTI nao carrega
        if i["identidades_verificaveis_das_4"] - n["identidades_verificaveis_das_4"] != 2:
            falhas.append("o ganho do DICOM sobre o NIfTI deixou de ser +2")

        # funil ponta a ponta
        r = rodar_funil(base / "funil")
        if not r["validacao"]["valido"]:
            falhas.append("funil valido reprovou: " + str(r["validacao"]["erros"]))
        if not r["congelamento"]["intacto"]:
            falhas.append("congelamento de manifesto recem-criado saiu alterado")
        if r["validacao"]["por_split"] != {"train": 2, "validation": 1, "test": 1}:
            falhas.append("split do funil errado: " + str(r["validacao"]["por_split"]))

        # 21.11 DETERMINISMO — duas passadas independentes, mesmo hash
        a = rodar_funil(base / "det_a")
        b = rodar_funil(base / "det_b")
        if a["sha256_manifesto"] == b["sha256_manifesto"]:
            falhas.append("dois diretorios diferentes deram o MESMO hash — o caminho "
                          "do arquivo deveria entrar no manifesto")
        ha = [e["mask_sha256"] for e in a["entradas"]]
        hb = [e["mask_sha256"] for e in b["entradas"]]
        if ha != hb:
            falhas.append("mesmo conteudo gerou sha256 diferente entre execucoes")

        # 21.12 REEXECUCAO — rodar de novo no MESMO diretorio nao pode mudar nada
        c1 = rodar_funil(base / "reexec")
        c2 = rodar_funil(base / "reexec")
        if c1["sha256_manifesto"] != c2["sha256_manifesto"]:
            falhas.append("reexecucao no mesmo diretorio mudou o hash do manifesto")
        if c1["snapshot"]["sha256_manifesto"] != c2["snapshot"]["sha256_manifesto"]:
            falhas.append("reexecucao mudou o snapshot")

        # os 14 casos controlados
        casos = casos_controlados(base / "casos")
        ruins = [c for c in casos if not c["passou"]]
        if ruins:
            falhas.append("casos controlados falharam: " +
                          str([c["caso"] for c in ruins]))
        if len(casos) != 14:
            falhas.append("esperava 14 casos controlados, rodou %d" % len(casos))

    for x in falhas:
        print("FALHA:", x)
    print("autoteste funil: %d verificacoes, %d falhas" % (16, len(falhas)))
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

    base = Path(tempfile.mkdtemp(prefix="vrmed_fase21_"))
    try:
        r = rodar_funil(base / "funil")
        print("IDENTIDADE POR CANAL")
        print("  DICOM : %d das 4 chaves verificaveis — %d vem do arquivo (%s) + sha256 computado"
              % (r["identidade_dicom"]["identidades_verificaveis_das_4"],
                 r["identidade_dicom"]["identidades_do_arquivo"],
                 ", ".join(r["identidade_dicom"]["quais_do_arquivo"])))
        print("          extra do canal: %s"
              % ", ".join(r["identidade_dicom"]["extras_do_canal"]))
        print("          case=%s study=%s series=%s  SOP: %d unicos"
              % (r["identidade_dicom"]["case_id"], r["identidade_dicom"]["study_id"][:24] + "...",
                 r["identidade_dicom"]["series_id"][:24] + "...",
                 len(r["identidade_dicom"]["sop_instance_uids"])))
        print("  NIfTI : %d das 4 chaves verificaveis — 0 do arquivo, case_id externo + sha256"
              % r["identidade_nifti"]["identidades_verificaveis_das_4"])
        print("          study_id=%s  series_id=%s" % (r["identidade_nifti"]["study_id"],
                                                       r["identidade_nifti"]["series_id"]))
        print("          motivo: " + r["identidade_nifti"]["motivo_unknown"])
        print()
        print("FUNIL: %d entradas, validacao %s, split %s"
              % (len(r["entradas"]), "OK" if r["validacao"]["valido"] else "FALHOU",
                 r["validacao"]["por_split"]))
        print("MANIFESTO sha256: %s" % r["sha256_manifesto"])
        print("SNAPSHOT  sha256: %s  | congelamento: %s"
              % (r["snapshot"]["sha256_manifesto"],
                 "INTACTO" if r["congelamento"]["intacto"] else "ALTERADO"))
        print()

        casos = casos_controlados(base / "casos")
        print("OS 14 CASOS CONTROLADOS (21.2)")
        for c in casos:
            print("  %-45s esperado %-7s obtido %-7s %s"
                  % (c["caso"], c["esperado"], c["obtido"], "OK" if c["passou"] else "FALHOU"))
        ok = sum(c["passou"] for c in casos)
        print("\n  %d/%d como esperado" % (ok, len(casos)))

        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "funil.json").write_text(json.dumps({
            "fase": 21,
            "identidade_dicom": r["identidade_dicom"],
            "identidade_nifti": r["identidade_nifti"],
            "manifesto_sha256": r["sha256_manifesto"],
            "snapshot": r["snapshot"],
            "casos_controlados": casos,
            "casos_ok": ok,
            "casos_total": len(casos),
        }, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print("\nescrito:", SAIDA / "funil.json")
        return 0 if ok == len(casos) else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
