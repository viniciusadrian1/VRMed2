"""
Fase 8 — o que o rotulo `pericardium` SIGNIFICA, usando o SAROS como referencia.

Este arquivo e a parte de AQUISICAO. A medicao entra depois, aqui mesmo.

A pergunta nao e "o Dice melhora?". E: a geometria que o TotalSegmentator chama
de `pericardium` corresponde ao objeto que o SAROS chama de `pericardium`?

RESSALVA QUE VALE PARA TUDO O QUE SAIR DAQUI
--------------------------------------------
As quatro classes da tarefa `trunk_cavities` do TotalSegmentator
(abdominal_cavity, thoracic_cavity, pericardium, mediastinum) sao exatamente o
subconjunto toracico/abdominal dos rotulos de regiao do SAROS, e a proveniencia
de treino dessa tarefa e INDOCUMENTADA. Logo a INDEPENDENCIA do SAROS como
referencia e INCERTA: se o `trunk_cavities` foi treinado no SAROS, um Dice alto
mede memorizacao, nao identidade anatomica. Toda afirmacao que dependa da
independencia tem que dizer isso.

A saida que sobrevive a essa incerteza e a medida da geometria do PROPRIO GT do
SAROS: se o `pericardium` do SAROS for ele mesmo um solido preenchido, entao
"pericardium" neste ecossistema significa REGIAO, nao SACO — e essa medida nao
envolve predicao nenhuma, logo nao e circular.

PROVENIENCIA (lida da fonte, nao de memoria)
--------------------------------------------
DOI do dado: 10.25737/SZ96-ZG60 -> https://www.cancerimagingarchive.net/analysis-result/saros/
E um "analysis result" do TCIA, NAO uma colecao NBIA: `getCollectionValues` da
API do NBIA nao lista "SAROS" (verificado: 156 colecoes, zero match). Por isso as
mascaras nao saem da API — saem de um zip direto, publico, sem cadastro.

LICENCA — as duas licencas sao coisas diferentes e divergem de proposito:
  - MASCARAS + planilha (o DADO que este modulo usa): CC BY 4.0, campo
    "License" da tabela de download da pagina do TCIA (URL_PAGINA abaixo).
  - Codigo em github.com/UMEssen/saros-dataset: MIT (arquivo LICENSE do repo).
  - Imagens de origem: variam por colecao do TCIA. Este modulo le a licenca de
    cada serie da PROPRIA API do NBIA (`tcia.licenca`) e grava no manifesto —
    nunca digitada a mao. As colecoes sob "NIH Controlled Data Access Policy"
    (COLECOES_RESTRITAS) exigem login e ficam FORA do subconjunto.

ROTULO — `pericardium` = 7. Nao adivinhado pelo nome nem pela ordem alfabetica:
sai do enum `BodyRegions` de training/util.py do repositorio dos proprios
autores, que e o mesmo enum usado por training/move_data.py para escrever o
`dataset.json` destes exatos arquivos body-regions.nii.gz.

ANOTACAO ESPARSA — 255 = ignore. O criterio de "fatia anotada" tambem e dos
autores (move_data.py): uma fatia esta anotada se NENHUM voxel dela vale 255,
`np.all(label != 255, axis=(0, 1))`. Toda comparacao posterior tem que ser
restrita a essas fatias.

GRADE — as anotacoes foram feitas em 5 mm. A imagem original do DICOM NAO
compartilha a grade da mascara; a imagem que compartilha e a reamostrada para
5 mm exatamente como em download.py dos autores (`_resample_image_to_thickness`:
mesmo origin, mesma direcao, mesmo spacing no plano, z = 5 mm, tamanho em z
arredondado). Este modulo reproduz isso e ABORTA o caso se a grade nao bater —
nunca reamostra a mascara em silencio.
"""

from __future__ import annotations

import csv
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

import nibabel as nib
import numpy as np

from .tier2 import tcia
from .tier2.geometria import DesalinhamentoGeometrico, descrever_nifti, verificar_alinhamento

# --------------------------------------------------------------- proveniencia

URL_PAGINA = "https://www.cancerimagingarchive.net/analysis-result/saros/"
DOI_DADO = "10.25737/SZ96-ZG60"
URL_ZIP = "https://www.cancerimagingarchive.net/wp-content/uploads/SAROS-Collection-NIfTI-files-v2_03-70-2024.zip"
URL_CSV = "https://www.cancerimagingarchive.net/wp-content/uploads/Segmentation-Info_09-29-2023.csv"
LICENCA_MASCARAS = "CC BY 4.0"  # campo "License" da tabela de download em URL_PAGINA
URL_CODIGO = "https://github.com/UMEssen/saros-dataset"
LICENCA_CODIGO = "MIT"  # LICENSE do repositorio — NAO e a licenca do dado

# Colecoes de origem sob "NIH Controlled Data Access Policy" na pagina do TCIA:
# exigem login, logo nao sao reproduziveis sem cadastro. Ficam fora.
COLECOES_RESTRITAS = frozenset({
    "ACRIN-HNSCC-FDG-PET-CT", "Anti-PD-1_MELANOMA", "HNSCC",
    "Head-Neck Cetuximab", "QIN-HEADNECK", "TCGA-HNSC",
})

# BodyRegions de training/util.py (UMEssen/saros-dataset). Copiado inteiro para
# que o indice 7 possa ser conferido no contexto, nao isolado.
BODY_REGIONS = {
    0: "background", 1: "subcutaneous_tissue", 2: "muscle", 3: "abdominal_cavity",
    4: "thoracic_cavity", 5: "bone", 6: "parotid_glands", 7: "pericardium",
    8: "breast_implant", 9: "mediastinum", 10: "brain", 11: "spinal_cord",
    12: "thyroid_glands", 13: "submandibular_glands",
}
ROTULO_PERICARDIUM = 7
IGNORE = 255
ESPESSURA_ANOTACAO_MM = 5.0

# ------------------------------------------------------ subconjunto declarado

# Declarado ANTES de qualquer medida. A regra e hash do identificador — nao
# depende de desempenho, de metrica, nem da ordem de iteracao.
SEMENTE = "saros-pericardio-fase8"
N_CASOS = 15
SPLIT_USADO = "test"  # o test set pre-definido pelos proprios autores
REGIOES = ("thorax", "wholebody")  # as duas que cobrem o torax

RAIZ = Path(".clinica-dados/saros")
DIR_BRUTO = RAIZ / "bruto"
DIR_MASCARAS = RAIZ / "mascaras"
PASTA_ZIP = "SAROS-Collection-NIfTI-files-v2_03-70-2024"
ARQ_SUBCONJUNTO = RAIZ / "subconjunto.json"
ARQ_MANIFESTO = RAIZ / "manifesto.json"


class AquisicaoInvalida(AssertionError):
    """Base: o caso nao pode ser usado, e seguir seria produzir numero falso."""


class GTAusente(AquisicaoInvalida):
    """Caso sem body-regions.nii.gz."""


class MascaraVazia(AquisicaoInvalida):
    """Mascara sem nenhum voxel do rotulo pedido."""


class SpacingInvalido(AquisicaoInvalida):
    """Zoom zerado / nao finito — volume em mm3 seria lixo."""


class PareamentoInvalido(AquisicaoInvalida):
    """Imagem e mascara de casos diferentes — o erro silencioso mais caro."""


class GradeDivergente(AquisicaoInvalida):
    """Imagem e mascara nao compartilham a grade. O caso sai da fase, com diagnostico."""


# --------------------------------------------------------------- 1. aquisicao


def _baixar(url: str, destino: Path) -> Path:
    """GET simples com cache por existencia. Sem token: estes dois sao publicos."""
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "vrmed/validacao"})
    with urllib.request.urlopen(req, timeout=900) as r:  # noqa: S310 (host fixo, https)
        bruto = r.read()
    destino.write_bytes(bruto)
    return destino


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def baixar_mascaras_e_planilha() -> dict:
    """Zip das mascaras + planilha de informacao. Devolve proveniencia com hash."""
    csv_path = _baixar(URL_CSV, DIR_BRUTO / Path(URL_CSV).name)
    zip_path = _baixar(URL_ZIP, DIR_BRUTO / Path(URL_ZIP).name)

    if not (DIR_MASCARAS / PASTA_ZIP).exists():
        with zipfile.ZipFile(zip_path) as z:
            membros = [
                n for n in z.namelist()
                if n.endswith(".nii.gz") and not n.startswith("__MACOSX")
            ]
            z.extractall(DIR_MASCARAS, members=membros)  # ZipFile remove ".."

    return {
        "doi": DOI_DADO,
        "pagina": URL_PAGINA,
        "licenca_mascaras": LICENCA_MASCARAS,
        "licenca_codigo": {"repo": URL_CODIGO, "licenca": LICENCA_CODIGO},
        "csv": {"url": URL_CSV, "sha256": _sha256(csv_path)},
        "zip": {"url": URL_ZIP, "sha256": _sha256(zip_path)},
    }


def ler_planilha() -> list[dict]:
    return list(csv.DictReader(
        (DIR_BRUTO / Path(URL_CSV).name).read_text(encoding="utf-8-sig").splitlines()
    ))


def _ordem_deterministica(case_id: str) -> str:
    """sha256(semente|id). Nao usa random: a ordem nao pode depender da iteracao."""
    return hashlib.sha256(f"{SEMENTE}|{case_id}".encode()).hexdigest()


def selecionar_subconjunto(linhas: list[dict], n: int = N_CASOS) -> list[dict]:
    """Elegibilidade declarada + ordem por hash. Nenhum criterio de desempenho."""
    elegiveis = [
        r for r in linhas
        if r["split"] == SPLIT_USADO
        and r["anatomic_region"] in REGIOES
        and r["tcia_collection"] not in COLECOES_RESTRITAS
    ]
    return sorted(elegiveis, key=lambda r: _ordem_deterministica(r["id"]))[:n]


def declarar_subconjunto(proveniencia: dict, selecao: list[dict]) -> dict:
    """Grava a lista em disco ANTES de qualquer medicao. Nao sobrescreve."""
    decl = {
        "proveniencia": proveniencia,
        "regra": {
            "semente": SEMENTE,
            "ordem": "sha256(semente|id), crescente",
            "split": SPLIT_USADO,
            "split_origem": "pre-definido pelos autores, coluna `split` da planilha",
            "anatomic_region": list(REGIOES),
            "colecoes_excluidas": sorted(COLECOES_RESTRITAS),
            "motivo_exclusao": "NIH Controlled Data Access Policy — exige login",
            "n": len(selecao),
        },
        "rotulo": {"pericardium": ROTULO_PERICARDIUM, "body_regions": BODY_REGIONS,
                   "fonte": f"{URL_CODIGO} training/util.py, enum BodyRegions"},
        "casos": [
            {k: r[k] for k in ("id", "tcia_collection", "tcia_case_id",
                               "anatomic_region", "orientation_code",
                               "tcia_series_instance_uid", "split")}
            for r in selecao
        ],
    }
    if ARQ_SUBCONJUNTO.exists():
        antigo = json.loads(ARQ_SUBCONJUNTO.read_text(encoding="utf-8"))
        ids_antigos = [c["id"] for c in antigo["casos"]]
        if ids_antigos != [c["id"] for c in decl["casos"]]:
            raise AquisicaoInvalida(
                f"subconjunto ja declarado em {ARQ_SUBCONJUNTO} com outra lista — "
                "trocar de casos depois de declarar invalida a fase"
            )
        return antigo
    ARQ_SUBCONJUNTO.parent.mkdir(parents=True, exist_ok=True)
    ARQ_SUBCONJUNTO.write_text(json.dumps(decl, indent=2, ensure_ascii=False), encoding="utf-8")
    return decl


# ------------------------------------------------- 2. imagem na grade da mascara


def caminho_mascara(caso: str) -> Path:
    return DIR_MASCARAS / PASTA_ZIP / caso / "body-regions.nii.gz"


def preparar_imagem(caso: dict) -> Path:
    """Baixa a serie do NBIA e reamostra para 5 mm como download.py dos autores.

    Reproduz `_resample_image_to_thickness`: mesmo origin, mesma direcao, mesmo
    spacing no plano, z = 5 mm, tamanho em z ARREDONDADO (o round e deles: a
    imagem foi exportada para anotacao com arredondamento de fatia).
    """
    import SimpleITK as sitk

    cid, uid = caso["id"], caso["tcia_series_instance_uid"]
    destino = RAIZ / "imagens" / cid
    saida = destino / "image.nii.gz"
    if saida.exists():
        return saida

    dicom_dir = RAIZ / "dicom" / cid
    if not (dicom_dir / tcia.MARCADOR).exists():
        series = [
            s for s in tcia.listar_series(caso["tcia_collection"], patient_id=caso["tcia_case_id"])
            if s["SeriesInstanceUID"] == uid
        ]
        if not series:
            raise AquisicaoInvalida(f"{cid}: serie {uid} nao encontrada na API do NBIA")
        tcia.baixar_serie(series[0], dicom_dir)

    leitor = sitk.ImageSeriesReader()
    arquivos = leitor.GetGDCMSeriesFileNames(str(dicom_dir), uid)
    if not arquivos:
        raise AquisicaoInvalida(f"{cid}: nenhum DICOM da serie {uid} em {dicom_dir}")
    leitor.SetFileNames(arquivos)
    img = leitor.Execute()

    sp, tam = img.GetSpacing(), img.GetSize()
    res = sitk.Resample(
        img,
        (tam[0], tam[1], round(tam[2] * sp[2] / ESPESSURA_ANOTACAO_MM)),
        sitk.Transform(), sitk.sitkLinear,
        img.GetOrigin(), (sp[0], sp[1], ESPESSURA_ANOTACAO_MM), img.GetDirection(),
    )
    destino.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(res, str(saida), True)
    return saida


# ------------------------------------------------------------- 3. verificacoes


def conferir_pareamento(caso_id: str, imagem: Path, mascara: Path) -> None:
    """Imagem e mascara tem que ser do MESMO caso — pelo caminho E pelo UID baixado.

    O caminho sozinho nao basta: dois casos podem ter grade identica por acaso e
    o alinhamento passaria. O UID vem do `_tcia_serie.json` que a propria API
    gravou, entao nao e um valor digitado por este codigo.
    """
    for papel, p in (("imagem", imagem), ("mascara", mascara)):
        if caso_id not in Path(p).parts:
            raise PareamentoInvalido(f"{papel} {p} nao pertence ao caso {caso_id}")

    marcador = RAIZ / "dicom" / caso_id / tcia.MARCADOR
    if not marcador.exists():
        return  # sem marcador nao ha o que cruzar; o caminho ja foi conferido
    uid_baixado = json.loads(marcador.read_text(encoding="utf-8"))["SeriesInstanceUID"]
    declarado = {c["id"]: c["tcia_series_instance_uid"]
                 for c in json.loads(ARQ_SUBCONJUNTO.read_text(encoding="utf-8"))["casos"]}
    if declarado.get(caso_id) and uid_baixado != declarado[caso_id]:
        raise PareamentoInvalido(
            f"{caso_id}: serie baixada {uid_baixado} != declarada {declarado[caso_id]}"
        )


def conferir_spacing(descricao: dict) -> None:
    z = np.asarray(descricao["zooms_mm"], dtype=float)
    if z.size != 3 or not np.all(np.isfinite(z)) or np.any(z <= 0):
        raise SpacingInvalido(f"{descricao['caminho']}: zooms_mm invalidos {descricao['zooms_mm']}")


def conferir_rotulo_presente(mascara: np.ndarray, caso_id: str, rotulo: int = ROTULO_PERICARDIUM) -> int:
    """Conta os voxels do rotulo e ABORTA se nao houver nenhum.

    Um caso sem o rotulo nao e "Dice 0": e um caso que nao pode entrar na medida.
    Sai como MascaraVazia para nao virar zero no denominador de uma mediana.
    """
    n = int((mascara == rotulo).sum())
    if n == 0:
        raise MascaraVazia(
            f"{caso_id}: rotulo {rotulo} ({BODY_REGIONS.get(rotulo)}) ausente na mascara"
        )
    return n


def diagnosticar_desalinhamento(imagem: Path, mascara: Path) -> dict:
    """Grade divergente: os ARRAYS discordam, ou so o affine discorda?

    Distingue as duas causas por MEDIDA, nao por leitura do header. Se os arrays
    ja estao pareados voxel a voxel, os rotulos caem sobre o HU que lhes cabe:
    `thoracic_cavity` (pulmao) fica muito negativo e `bone` fica muito positivo.
    Se for preciso inverter Z para conseguir isso, o desencontro esta no array.

    Nao corrige nada — so nomeia a causa, para o caso nao sair como "dado ruim"
    quando o problema e o affine, nem o contrario.
    """
    img = np.asarray(nib.load(str(imagem)).dataobj)
    msk = np.asarray(nib.load(str(mascara)).dataobj)
    if img.shape != msk.shape:
        return {"causa": "shapes diferentes — arrays nem sao comparaveis",
                "shape_imagem": list(img.shape), "shape_mascara": list(msk.shape)}

    anotada = np.all(msk != IGNORE, axis=(0, 1))
    def _hu(arr):
        return {
            BODY_REGIONS[r]: (float(arr[sel].mean()) if (sel := (msk == r) & anotada).any() else None)
            for r in (4, 5)  # thoracic_cavity (pulmao, muito negativo) e bone (positivo)
        }
    como_lido, invertido = _hu(img), _hu(img[:, :, ::-1])
    coerente = (como_lido["thoracic_cavity"] is not None
                and como_lido["thoracic_cavity"] < invertido["thoracic_cavity"]
                and como_lido["bone"] > invertido["bone"])
    return {
        "hu_medio_como_lido": como_lido,
        "hu_medio_com_z_invertido": invertido,
        "arrays_pareados_voxel_a_voxel": bool(coerente),
        "causa": ("so o affine diverge — os arrays ja estao pareados"
                  if coerente else "os arrays tambem divergem"),
    }


def esparsidade(mascara: np.ndarray) -> dict:
    """Fatias anotadas x fatias ignore, medidas NO DADO.

    Criterio dos autores (move_data.py): anotada = nenhum voxel 255 na fatia.
    Reporta tambem o passo entre fatias anotadas, para checar o "1 em 5" do paper
    contra o que o arquivo realmente tem.
    """
    anotada = np.all(mascara != IGNORE, axis=(0, 1))
    idx = np.flatnonzero(anotada)
    passos = np.diff(idx)
    unicos, contagens = np.unique(passos, return_counts=True) if passos.size else ([], [])
    return {
        "n_fatias": int(mascara.shape[2]),
        "n_anotadas": int(idx.size),
        "n_ignore": int(mascara.shape[2] - idx.size),
        "fracao_anotada": float(idx.size / mascara.shape[2]),
        "indices_anotados": idx.tolist(),
        "passos": {int(u): int(c) for u, c in zip(unicos, contagens)},
        "passo_modal": int(unicos[int(np.argmax(contagens))]) if len(unicos) else None,
        "padrao_1_em_5": bool(len(unicos) == 1 and unicos[0] == 5),
    }


def inspecionar_caso(caso: dict) -> dict:
    """Um caso: geometria, grade compartilhada, esparsidade, rotulo 7 presente."""
    cid = caso["id"]
    mascara = caminho_mascara(cid)
    if not mascara.exists():
        raise GTAusente(f"{cid}: {mascara} nao existe")

    imagem = preparar_imagem(caso)
    conferir_pareamento(cid, imagem, mascara)

    d_img, d_msk = descrever_nifti(imagem), descrever_nifti(mascara)
    conferir_spacing(d_img)
    conferir_spacing(d_msk)
    # ponytail: grade divergente = caso FORA da fase, com diagnostico anexado.
    # Nao corrijo o affine aqui: seria reescrever geometria depois de ver o dado.
    try:
        alinhamento = verificar_alinhamento(imagem, mascara, ("imagem", "mascara"))
    except DesalinhamentoGeometrico as e:
        raise GradeDivergente(
            f"{cid}: {e} | diagnostico={json.dumps(diagnosticar_desalinhamento(imagem, mascara))}"
        ) from e

    arr = np.asarray(nib.load(str(mascara)).dataobj)
    valores, contagens = np.unique(arr, return_counts=True)
    n_peri = conferir_rotulo_presente(arr, cid)

    voxel_mm3 = float(np.prod(d_msk["zooms_mm"]))
    marcador = RAIZ / "dicom" / cid / tcia.MARCADOR
    serie = json.loads(marcador.read_text(encoding="utf-8")) if marcador.exists() else {}

    return {
        "id": cid,
        "colecao": caso["tcia_collection"],
        "anatomic_region": caso["anatomic_region"],
        "licenca_imagem_api": tcia.licenca(serie) if serie else None,
        "geometria": {"imagem": d_img, "mascara": d_msk,
                      "grade_compartilhada": alinhamento["alinhado"]},
        "rotulos_presentes": {BODY_REGIONS.get(int(v), f"desconhecido_{int(v)}"): int(c)
                              for v, c in zip(valores, contagens) if v != IGNORE},
        "pericardium": {
            "rotulo": ROTULO_PERICARDIUM,
            "n_voxels": n_peri,
            "volume_mm3": n_peri * voxel_mm3,
            "volume_ml": n_peri * voxel_mm3 / 1000.0,
            "n_fatias_com_pericardium": int((arr == ROTULO_PERICARDIUM).any(axis=(0, 1)).sum()),
        },
        "esparsidade": esparsidade(arr),
    }


def adquirir(n: int = N_CASOS) -> dict:
    """Aquisicao completa. Grava subconjunto ANTES, manifesto DEPOIS."""
    proveniencia = baixar_mascaras_e_planilha()
    selecao = selecionar_subconjunto(ler_planilha(), n)
    decl = declarar_subconjunto(proveniencia, selecao)

    casos, falhas = [], []
    for caso in decl["casos"]:
        try:
            casos.append(inspecionar_caso(caso))
        except AquisicaoInvalida as e:
            falhas.append({"id": caso["id"], "erro": type(e).__name__, "mensagem": str(e)})

    manifesto = {"declaracao": decl, "casos": casos, "falhas": falhas}
    ARQ_MANIFESTO.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifesto


# ------------------------------------------------------------------ autoteste


def _autoteste() -> None:
    """Controles POSITIVOS: cada verificacao tem que FALHAR quando deveria."""
    import tempfile

    rng = np.random.default_rng(0)
    base = np.full((16, 16, 10), IGNORE, dtype=np.uint8)
    base[..., ::5] = 0                      # 1 fatia anotada a cada 5
    base[4:12, 4:12, ::5] = ROTULO_PERICARDIUM
    aff = np.diag([1.0, 1.0, 5.0, 1.0])

    # --- esparsidade mede o que esta no dado
    e = esparsidade(base)
    assert e["n_anotadas"] == 2 and e["passo_modal"] == 5 and e["padrao_1_em_5"], e
    denso = np.zeros((16, 16, 10), dtype=np.uint8)
    assert esparsidade(denso)["fracao_anotada"] == 1.0
    assert not esparsidade(denso)["padrao_1_em_5"], "denso nao pode passar por 1-em-5"

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        img_p, msk_p = td / "case_A" / "image.nii.gz", td / "case_A" / "body-regions.nii.gz"
        img_p.parent.mkdir(parents=True)
        nib.save(nib.Nifti1Image(rng.random((16, 16, 10)).astype(np.float32), aff), str(img_p))
        nib.save(nib.Nifti1Image(base, aff), str(msk_p))

        # controle NEGATIVO: o caso correto passa
        verificar_alinhamento(img_p, msk_p, ("imagem", "mascara"))
        conferir_spacing(descrever_nifti(msk_p))
        conferir_pareamento("case_A", img_p, msk_p)

        # 1. mascara deslocada da imagem
        desl = aff.copy()
        desl[2, 3] += 5.0
        p = td / "case_A" / "deslocada.nii.gz"
        nib.save(nib.Nifti1Image(base, desl), str(p))
        try:
            verificar_alinhamento(img_p, p, ("imagem", "mascara"))
        except DesalinhamentoGeometrico as ex:
            assert "affine" in str(ex), ex
        else:
            raise AssertionError("CONTROLE POSITIVO FALHOU: mascara deslocada passou")

        # 2. affine incompativel (shape diferente = outra grade)
        p = td / "case_A" / "outra_grade.nii.gz"
        nib.save(nib.Nifti1Image(base[:8], aff), str(p))
        try:
            verificar_alinhamento(img_p, p, ("imagem", "mascara"))
        except DesalinhamentoGeometrico as ex:
            assert "shape" in str(ex), ex
        else:
            raise AssertionError("CONTROLE POSITIVO FALHOU: grade diferente passou")

        # 3. caso sem GT
        try:
            inspecionar_caso({"id": "case_inexistente_999", "tcia_collection": "x",
                              "tcia_case_id": "x", "anatomic_region": "thorax",
                              "tcia_series_instance_uid": "x"})
        except GTAusente:
            pass
        else:
            raise AssertionError("CONTROLE POSITIVO FALHOU: caso sem GT passou")

        # 4. mascara vazia (sem o rotulo 7)
        assert conferir_rotulo_presente(base, "case_A") == int((base == ROTULO_PERICARDIUM).sum())
        vazia = base.copy()
        vazia[vazia == ROTULO_PERICARDIUM] = 0
        try:
            conferir_rotulo_presente(vazia, "case_A")
        except MascaraVazia as ex:
            assert "case_A" in str(ex) and "pericardium" in str(ex), ex
        else:
            raise AssertionError("CONTROLE POSITIVO FALHOU: mascara sem rotulo 7 passou")

        # 5. spacing ausente / zerado
        for zooms in ([0.0, 1.0, 5.0], [np.nan, 1.0, 5.0]):
            try:
                conferir_spacing({"caminho": "sintetico", "zooms_mm": zooms})
            except SpacingInvalido:
                pass
            else:
                raise AssertionError(f"CONTROLE POSITIVO FALHOU: spacing {zooms} passou")

        # 6. pareamento cruzado — mascara de OUTRO caso, com a MESMA grade.
        #    E o que o alinhamento sozinho nao pega: aqui ele passaria.
        outro = td / "case_B" / "body-regions.nii.gz"
        outro.parent.mkdir(parents=True)
        nib.save(nib.Nifti1Image(base, aff), str(outro))
        verificar_alinhamento(img_p, outro, ("imagem", "mascara"))  # passa — por isso o teste existe
        try:
            conferir_pareamento("case_A", img_p, outro)
        except PareamentoInvalido as ex:
            assert "case_A" in str(ex), ex
        else:
            raise AssertionError("CONTROLE POSITIVO FALHOU: mascara de outro caso passou")

    # 7. subconjunto e deterministico e nao depende da ordem de entrada
    linhas = [{"id": f"case_{i:03d}", "split": SPLIT_USADO, "anatomic_region": "thorax",
               "tcia_collection": "LIDC-IDRI"} for i in range(60)]
    a = [r["id"] for r in selecionar_subconjunto(linhas, 15)]
    b = [r["id"] for r in selecionar_subconjunto(list(reversed(linhas)), 15)]
    assert a == b, "selecao depende da ordem de entrada"
    fora = [{"id": "case_900", "split": "fold-1", "anatomic_region": "thorax",
             "tcia_collection": "LIDC-IDRI"},
            {"id": "case_901", "split": SPLIT_USADO, "anatomic_region": "abdomen",
             "tcia_collection": "LIDC-IDRI"},
            {"id": "case_902", "split": SPLIT_USADO, "anatomic_region": "thorax",
             "tcia_collection": "QIN-HEADNECK"}]
    assert not selecionar_subconjunto(fora, 15), "criterio de elegibilidade nao filtrou"

    print("saros_pericardium.py: autoteste OK (7 controles positivos falharam como deviam)")


# =============================================================== 4. MEDICAO
#
# PARTE 1 e a unica medida IMUNE A CIRCULARIDADE: mede a geometria do PROPRIO GT
# do SAROS, sem tocar em predicao nenhuma. Se o `pericardium` humano-revisado do
# SAROS for ele mesmo um solido preenchido, entao "pericardium" neste ecossistema
# significa REGIAO e nao SACO — e nenhum Dice muda isso.
#
# PARTES 2 e 3 dependem da predicao e por isso herdam a incerteza de
# independencia declarada no topo do modulo. Cada linha de resultado carrega
# `independencia_incerta`.
#
# RESTRICAO AS FATIAS ANOTADAS — obrigatoria em TUDO o que sai daqui.
# 4 de cada 5 fatias valem 255 (ignore). Uma metrica calculada sobre fatia de
# ignore compara predicao com AUSENCIA DE ROTULO e produz numero que parece
# valido. Toda funcao abaixo recebe a mascara booleana `anotadas` e a aplica.

DIR_PRED = RAIZ / "predicoes"
DIR_RESULTADOS = RAIZ / "resultados"

TAREFA_CAVIDADES = "trunk_cavities"  # task 343 do TotalSegmentator 2.18.0

# class_map["trunk_cavities"] do TotalSegmentator 2.18.0 (map_to_binary.py) ->
# rotulo homonimo do enum BodyRegions do SAROS. A correspondencia e POR NOME:
# e exatamente isso que esta fase poe a prova.
EQUIV_TS_SAROS = {
    "abdominal_cavity": 3,
    "thoracic_cavity": 4,
    "pericardium": 7,
    "mediastinum": 9,
}
CLASSE_ALVO = "pericardium"
NA = "nao aplicavel"
NM = "nao medido"

RESSALVA_INDEPENDENCIA = (
    "independencia INCERTA: a proveniencia de treino do trunk_cavities e "
    "indocumentada e suas 4 classes sao exatamente os rotulos de regiao "
    "toracica/abdominal do SAROS. Se a tarefa foi treinada no SAROS, este numero "
    "mede memorizacao, nao identidade anatomica."
)


def fatias_anotadas(mascara: np.ndarray) -> np.ndarray:
    """Criterio dos autores (move_data.py): fatia anotada = NENHUM voxel 255."""
    return np.all(mascara != IGNORE, axis=(0, 1))


def _zerar_fora(m: np.ndarray, anotadas: np.ndarray) -> np.ndarray:
    """Restringe uma mascara binaria as fatias anotadas. Tudo passa por aqui."""
    saida = np.zeros_like(m, dtype=bool)
    saida[:, :, anotadas] = np.asarray(m)[:, :, anotadas] > 0.5
    return saida


# ------------------------------------------------ PARTE 1 — geometria do GT


def forma_esparsa(m: np.ndarray, spacing, anotadas: np.ndarray) -> dict:
    """Casca ou solido, medido FATIA A FATIA nas fatias anotadas.

    POR QUE NAO FILL 3D: com 4 de cada 5 fatias em ignore, o objeto anotado e um
    empilhamento de lajes ISOLADAS de 1 voxel de espessura separadas por vazio.
    `binary_fill_holes` em 3D nao tem o que fechar entre lajes que nao se tocam:
    ele devolveria ~a propria mascara e diria "solido" para QUALQUER coisa,
    inclusive para uma casca. O fill 3D aqui nao e conservador, e cego.
    O fill 2D no plano de cada fatia anotada e a leitura valida: um saco fibroso
    corta cada fatia axial como um ANEL FECHADO, e o fill 2D detecta o anel.

    Reusa `pericardio.forma()` sem reimplementar: aplicada a uma laje (X, Y, 1),
    a conectividade de face nao tem vizinho em z, entao razao_3d == razao_2d ==
    razao no plano, a EDT nao recebe contribuicao de z, e n_componentes vira a
    contagem 2D de componentes daquela fatia. O criterio de casca (0,5) e o
    mesmo da fase 6, declarado antes desta fase.
    """
    from .tier2.pericardio import LIMIAR_CASCA, forma

    m = np.asarray(m) > 0.5
    spacing = tuple(float(s) for s in spacing)
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    idx = [int(k) for k in np.flatnonzero(anotadas) if m[:, :, k].any()]
    if not idx:
        return {"veredito_forma": "invalido: mascara vazia nas fatias anotadas"}

    por_fatia = []
    espessuras, razoes, componentes = [], [], []
    for k in idx:
        f = forma(m[:, :, k : k + 1], spacing)
        por_fatia.append({
            "z": k,
            "n_voxels": f["n_voxels"],
            "razao_preenchimento_2d": f["razao_preenchimento_2d_por_fatia"],
            "n_componentes_2d": f["n_componentes"],
            "meia_espessura_mediana_mm": f["meia_espessura_mm"]["mediana"],
        })
        razoes.append(f["razao_preenchimento_2d_por_fatia"])
        componentes.append(f["n_componentes"])
        espessuras.append(f["meia_espessura_mm"]["mediana"])

    # razao agregada = voxels / voxels apos preencher, somado sobre as fatias:
    # ponderada pelo tamanho, nao media de razoes (fatia de 3 voxels nao pesa
    # igual a fatia de 20 mil).
    from scipy.ndimage import binary_fill_holes

    n = sum(f["n_voxels"] for f in por_fatia)
    n_cheio = sum(int(binary_fill_holes(m[:, :, k]).sum()) for k in idx)
    razao = n / n_cheio

    # espessura radial de TODOS os voxels juntos, no plano (EDT 2D por fatia)
    from scipy.ndimage import distance_transform_edt

    todas = np.concatenate([
        distance_transform_edt(m[:, :, k], sampling=spacing[:2])[m[:, :, k]] for k in idx
    ])
    return {
        "n_fatias_anotadas_com_rotulo": len(idx),
        "n_voxels": n,
        "volume_ml_nas_fatias_anotadas": n * voxel_mm3 / 1000.0,
        "razao_preenchimento_2d_agregada": razao,
        "razao_preenchimento_2d_por_fatia": {
            "mediana": float(np.median(razoes)), "min": float(np.min(razoes)),
            "max": float(np.max(razoes)),
        },
        "razao_preenchimento_3d": NA + ": fill 3D e cego com anotacao esparsa "
                                      "(lajes isoladas, nada a fechar entre elas)",
        "meia_espessura_no_plano_mm": {
            "definicao": "EDT 2D (sampling = spacing no plano) de cada voxel ate o fundo "
                         "da propria mascara, na propria fatia; ~metade da espessura local",
            "mediana": float(np.median(todas)), "p95": float(np.percentile(todas, 95)),
            "max": float(todas.max()),
        },
        "n_componentes_2d_por_fatia": {
            "mediana": float(np.median(componentes)), "min": int(np.min(componentes)),
            "max": int(np.max(componentes)),
            "contagem": {int(u): int(c) for u, c in zip(*np.unique(componentes, return_counts=True))},
        },
        "veredito_forma": "casca" if razao < LIMIAR_CASCA else "solido preenchido",
        "criterio": f"razao_preenchimento_2d < {LIMIAR_CASCA} => casca "
                    "(limiar da fase 6, declarado antes desta fase)",
        "por_fatia": por_fatia,
    }


def contencao_coracao(peri: np.ndarray, heart: np.ndarray, spacing, anotadas) -> dict:
    """O objeto contem o coracao? O coracao aqui e PREDICAO, nao GT.

    O SAROS nao anota coracao. A unica referencia geometrica disponivel e o
    `heart` da tarefa `total` do TotalSegmentator — que e o objeto sob suspeita
    do outro lado da comparacao. Logo esta linha NAO e evidencia independente:
    e uma descricao de onde uma predicao cai dentro de outra mascara.
    """
    from .tier2.pericardio import relacao

    p, h = _zerar_fora(peri, anotadas), _zerar_fora(heart, anotadas)
    r = relacao(p, h, spacing)
    # as chaves de uniao dependem de conectividade/preenchimento em 3D — invalidas
    # com lajes isoladas. Substituidas por NA em vez de sairem plausiveis.
    for k in ("uniao_n_componentes", "uniao_vazio_encapsulado_ml", "uniao_frac_vazio"):
        r[k] = NA + ": depende de 3D contiguo; a anotacao esparsa nao o e"
    r["coracao_e_predicao"] = (
        "SIM — `heart` da tarefa `total` do TotalSegmentator. O SAROS nao anota "
        "coracao. Isto descreve duas mascaras, nao valida nenhuma das duas."
    )
    r["restrito_a_fatias_anotadas"] = int(anotadas.sum())
    return r


# ------------------------------- PARTE 2 — comparacao restrita as fatias anotadas


def distancias_no_plano(pred: np.ndarray, gt: np.ndarray, spacing, anotadas) -> dict:
    """HD95/ASSD medidos SO NO PLANO, fatia anotada a fatia anotada.

    ESCOLHA E CUSTO, declarados: distancia de superficie em 3D exige vizinhanca
    em z. Com 4 de cada 5 fatias em ignore, o voxel "vizinho em z" de uma fatia
    anotada esta a 25 mm e nao foi anotado — a superficie 3D do objeto anotado e
    a superficie das lajes, nao a do objeto. Um HD95 3D calculado assim mediria
    principalmente as tampas artificiais das lajes.
    O que sobra valido e a distancia NO PLANO de cada fatia anotada, com o
    spacing no plano. O custo: esta metrica NAO diz nada sobre concordancia em z
    — nem a favor, nem contra. HD95/ASSD em 3D saem como "nao aplicavel".
    Fatia em que um dos lados esta vazio nao entra (distancia indefinida) e e
    contada a parte.
    """
    from .segmentation_metrics import surface_distances

    p, g = np.asarray(pred) > 0.5, np.asarray(gt) > 0.5
    sp2 = (float(spacing[0]), float(spacing[1]))
    linhas, vazias = [], []
    for k in np.flatnonzero(anotadas):
        a, b = p[:, :, k], g[:, :, k]
        if not a.any() or not b.any():
            if a.any() or b.any():
                vazias.append({"z": int(k), "pred_vazia": not a.any(), "gt_vazia": not b.any()})
            continue
        d = surface_distances(a, b, sp2)
        linhas.append({"z": int(k), "hd95_mm": d["hd95_mm"], "assd_mm": d["assd_mm"],
                       "hd_mm": d["hd_mm"], "nsd_1mm": d["nsd_1mm"]})
    if not linhas:
        return {"veredito": "invalido: nenhuma fatia anotada com os dois lados nao vazios",
                "n_fatias_pareadas": 0, "fatias_com_um_lado_vazio": vazias}
    hd95 = np.array([l["hd95_mm"] for l in linhas])
    assd = np.array([l["assd_mm"] for l in linhas])
    return {
        "escolha": "2D no plano, por fatia anotada; 3D nao aplicavel (ver docstring)",
        "hd95_3d_mm": NA + ": superficie em z e artefato das lajes da anotacao esparsa",
        "assd_3d_mm": NA + ": mesma razao",
        "n_fatias_pareadas": len(linhas),
        "fatias_com_um_lado_vazio": vazias,
        "hd95_no_plano_mm": {"mediana": float(np.median(hd95)), "p95": float(np.percentile(hd95, 95)),
                             "max": float(hd95.max())},
        "assd_no_plano_mm": {"mediana": float(np.median(assd)), "p95": float(np.percentile(assd, 95)),
                             "max": float(assd.max())},
        "por_fatia": linhas,
    }


def metricas_esparsas(pred: np.ndarray, gt: np.ndarray, spacing, anotadas) -> dict:
    """Dice/IoU/precision/recall/volume — todos restritos as fatias anotadas.

    Estas quatro sao CONTAGENS DE VOXEL: restringir o dominio as fatias anotadas
    e exato, nao aproximado (o Dice restrito e 2|P∩G∩A|/(|P∩A|+|G∩A|)).
    O volume tambem: e volume da mascara, em mm3/mL — nao de malha.
    Mas NAO e volume anatomico: cobre ~1/5 da extensao em z.
    """
    from .segmentation_metrics import dice, iou
    from .tier2.benchmark_tier2 import recall_containment
    from scipy.ndimage import label

    p, g = _zerar_fora(pred, anotadas), _zerar_fora(gt, anotadas)
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    v_p, v_g = int(p.sum()) * voxel_mm3 / 1000.0, int(g.sum()) * voxel_mm3 / 1000.0
    rc = recall_containment(p, g)
    comps = [int(label(p[:, :, k])[1]) for k in np.flatnonzero(anotadas) if p[:, :, k].any()]
    return {
        "n_fatias_anotadas": int(anotadas.sum()),
        "n_fatias_totais": int(gt.shape[2]),
        "dice": dice(p, g),
        "iou": iou(p, g),
        "recall_gt": rc["recall_gt"],
        "precision_pred": rc["precision_pred"],
        "volume_gt_ml": v_g,
        "volume_pred_ml": v_p,
        "erro_volume_ml": v_p - v_g,
        "erro_volume_abs_ml": abs(v_p - v_g),
        "erro_volume_abs_pct": (abs(v_p - v_g) / v_g * 100.0) if v_g > 0 else NA,
        "n_componentes_2d_pred_por_fatia": {
            "mediana": float(np.median(comps)) if comps else NA,
            "max": int(max(comps)) if comps else NA,
        },
        "volume_e_amostra": "volume da MASCARA nas fatias anotadas (~1/5 da extensao em z). "
                            "Nao e volume anatomico e nao se compara a volume denso.",
        "topologia_malha": NA + ": qualidade_topologica exige malha; malha de lajes isoladas "
                                "de 1 voxel separadas por 20 mm de ignore nao descreve o objeto",
        "independencia_incerta": RESSALVA_INDEPENDENCIA,
    }


# ---------------------------------------- PARTE 3 — discriminar entre hipoteses


def composicao(pred: np.ndarray, gt_rotulos: np.ndarray, anotadas) -> dict:
    """De que o `pericardium` predito e FEITO, em rotulos do SAROS.

    Esta e a medida que discrimina sem depender de limiar de Dice: cada voxel da
    predicao cai sobre exatamente um rotulo do SAROS, e a distribuicao diz se a
    predicao e a regiao pericardica, o mediastino, a cavidade toracica, ou uma
    mistura. Soma 1 por construcao.
    """
    p = _zerar_fora(pred, anotadas)
    n = int(p.sum())
    if not n:
        return {"veredito": "invalido: predicao vazia nas fatias anotadas"}
    vals, cont = np.unique(np.asarray(gt_rotulos)[p], return_counts=True)
    return {
        "n_voxels_pred": n,
        "fracao_por_rotulo_saros": {
            BODY_REGIONS.get(int(v), f"desconhecido_{int(v)}"): float(c / n)
            for v, c in sorted(zip(vals, cont), key=lambda t: -t[1])
        },
    }


def cobertura_inversa(gt_alvo: np.ndarray, preds: dict, anotadas) -> dict:
    """O caminho contrario: o `pericardium` do SAROS e coberto por qual classe predita?"""
    g = _zerar_fora(gt_alvo, anotadas)
    n = int(g.sum())
    if not n:
        return {"veredito": "invalido: GT vazio nas fatias anotadas"}
    return {
        "n_voxels_gt": n,
        "fracao_coberta_por_classe_predita": {
            nome: float(int((_zerar_fora(m, anotadas) & g).sum()) / n)
            for nome, m in sorted(preds.items())
        },
    }


def contra_todas_classes(pred_peri, gt_rotulos, spacing, anotadas) -> dict:
    """O `pericardium` predito casa melhor com QUAL rotulo do SAROS?

    Se casar melhor com `mediastinum` do que com `pericardium`, isso e achado de
    primeira ordem e muda a ontologia — por isso a comparacao inclui as outras
    classes e as unioes que fazem sentido anatomico.
    """
    from .segmentation_metrics import dice
    from .tier2.benchmark_tier2 import recall_containment

    p = _zerar_fora(pred_peri, anotadas)
    alvos = {nome: (np.asarray(gt_rotulos) == rot) for nome, rot in EQUIV_TS_SAROS.items()}
    alvos["pericardium_U_mediastinum"] = alvos["pericardium"] | alvos["mediastinum"]
    alvos["thoracic_cavity_U_pericardium_U_mediastinum"] = (
        alvos["thoracic_cavity"] | alvos["pericardium"] | alvos["mediastinum"])
    saida = {}
    for nome, alvo in alvos.items():
        a = _zerar_fora(alvo, anotadas)
        rc = recall_containment(p, a)
        saida[nome] = {"dice": dice(p, a), "recall_gt": rc["recall_gt"],
                       "precision_pred": rc["precision_pred"]}
    melhor = max(saida, key=lambda k: saida[k]["dice"])
    return {"por_rotulo_saros": saida, "melhor_dice": melhor,
            "melhor_e_pericardium": melhor == CLASSE_ALVO,
            "independencia_incerta": RESSALVA_INDEPENDENCIA}


# ------------------------------------------------------------------- execucao


def segmentar_caso(caso: dict, log=print) -> dict:
    """`trunk_cavities` + `heart` da tarefa `total`, em diretorio proprio.

    Nao toca em nada do baseline. A entrada e a imagem reamostrada para 5 mm que
    COMPARTILHA a grade da mascara — assim a predicao sai na grade do GT e nao
    ha reamostragem de mascara em lugar nenhum da comparacao.
    """
    from scripts.clinica.segmentacao import rodar_segmentacao

    cid = caso["id"]
    entrada = RAIZ / "imagens" / cid / "image.nii.gz"
    if not entrada.exists():
        raise AquisicaoInvalida(f"{cid}: imagem ausente ({entrada})")

    info = {}
    alvos = ((TAREFA_CAVIDADES, None, f"{CLASSE_ALVO}.nii.gz"),
             ("total", ["heart"], "heart.nii.gz"))
    for tarefa, estruturas, marcador in alvos:
        destino = DIR_PRED / cid / tarefa
        if (destino / marcador).exists():
            log(f"{cid}/{tarefa}: ja segmentado — reusando")
            info[tarefa] = json.loads((destino / "segmentacao.json").read_text(encoding="utf-8"))
            continue
        info[tarefa] = rodar_segmentacao(entrada, destino, estruturas=estruturas,
                                         task=tarefa, log=log)
    return info


def _mascara_pred(cid: str, tarefa: str, classe: str) -> np.ndarray:
    caminho = DIR_PRED / cid / tarefa / f"{classe}.nii.gz"
    if not caminho.exists():
        raise AquisicaoInvalida(f"{cid}: predicao ausente ({caminho})")
    # grade: a predicao TEM que estar na grade do GT. Aborta se nao estiver.
    verificar_alinhamento(caminho, caminho_mascara(cid), (f"pred_{classe}", "gt_saros"))
    return np.asarray(nib.load(str(caminho)).dataobj) > 0.5


def medir_caso(caso: dict, log=print) -> dict:
    """Um caso inteiro: parte 1 (so GT), parte 2 (comparacao), parte 3 (hipoteses)."""
    cid = caso["id"]
    gt = np.asarray(nib.load(str(caminho_mascara(cid))).dataobj)
    d = descrever_nifti(caminho_mascara(cid))
    spacing = tuple(d["zooms_mm"])
    anotadas = fatias_anotadas(gt)
    gt_peri = gt == ROTULO_PERICARDIUM

    segmentar_caso(caso, log=log)
    preds = {nome: _mascara_pred(cid, TAREFA_CAVIDADES, nome) for nome in EQUIV_TS_SAROS}
    heart = _mascara_pred(cid, "total", "heart")
    pred_peri = preds[CLASSE_ALVO]

    return {
        "id": cid,
        "colecao": caso["tcia_collection"],
        "anatomic_region": caso["anatomic_region"],
        "spacing_mm": list(spacing),
        "orientacao": d["orientacao"],
        "n_fatias": int(gt.shape[2]),
        "n_fatias_anotadas": int(anotadas.sum()),
        "fracao_anotada": float(anotadas.sum() / gt.shape[2]),
        # PARTE 1 — so GT, imune a circularidade
        "parte1_forma_gt": forma_esparsa(gt_peri, spacing, anotadas),
        "parte1_contencao_coracao_predito": contencao_coracao(gt_peri, heart, spacing, anotadas),
        # PARTE 2 — comparacao
        "parte2_metricas": metricas_esparsas(pred_peri, gt_peri, spacing, anotadas),
        "parte2_distancias": distancias_no_plano(pred_peri, gt_peri, spacing, anotadas),
        # PARTE 3 — hipoteses
        "parte3_forma_pred": forma_esparsa(pred_peri, spacing, anotadas),
        "parte3_composicao_pred_em_saros": composicao(pred_peri, gt, anotadas),
        "parte3_cobertura_gt_por_pred": cobertura_inversa(gt_peri, preds, anotadas),
        "parte3_contra_todas_classes": contra_todas_classes(pred_peri, gt, spacing, anotadas),
        "parte3_contencao_coracao_na_pred": contencao_coracao(pred_peri, heart, spacing, anotadas),
    }


# -------------------------------------------------------- PARTE 4 — estatistica


def distribuicao(valores) -> dict:
    """n, mediana, P5, P25, P75, P95, min, max. Nunca so a mediana."""
    v = np.asarray([x for x in valores if isinstance(x, (int, float)) and np.isfinite(x)], float)
    if not v.size:
        return {"n": 0, "veredito": "invalido: nenhum valor finito"}
    return {"n": int(v.size), "mediana": float(np.median(v)),
            "p5": float(np.percentile(v, 5)), "p25": float(np.percentile(v, 25)),
            "p75": float(np.percentile(v, 75)), "p95": float(np.percentile(v, 95)),
            "min": float(v.min()), "max": float(v.max())}


def _cava(d: dict, caminho: str):
    for k in caminho.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def pareado(casos: list[dict], a: str, b: str) -> dict:
    """Diferenca PAREADA por caso entre duas variantes. Nao compara medianas."""
    pares = [(_cava(c, a), _cava(c, b)) for c in casos]
    pares = [(x, y) for x, y in pares if isinstance(x, (int, float)) and isinstance(y, (int, float))]
    if not pares:
        return {"n": 0, "veredito": "invalido: sem pares"}
    dif = np.array([y - x for x, y in pares], float)
    return {"n": len(pares), "n_b_maior": int((dif > 0).sum()), "n_a_maior": int((dif < 0).sum()),
            "n_empate": int((dif == 0).sum()), "diferenca_b_menos_a": distribuicao(dif)}


# ------------------------------------------------- PARTE 5 — figuras (depois)


def figura_caso(caso_medido: dict, destino: Path, n_fatias: int = 3) -> str:
    """CT + GT do SAROS + predicao, em fatias ANOTADAS. Escolhida DEPOIS de medir.

    Figura investiga anatomia; nao substitui metrica nenhuma.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cid = caso_medido["id"]
    gt = np.asarray(nib.load(str(caminho_mascara(cid))).dataobj)
    img = np.asarray(nib.load(str(RAIZ / "imagens" / cid / "image.nii.gz")).dataobj)
    pred = _mascara_pred(cid, TAREFA_CAVIDADES, CLASSE_ALVO)
    anotadas = fatias_anotadas(gt)
    gt_peri = gt == ROTULO_PERICARDIUM

    zs = [k for k in np.flatnonzero(anotadas) if gt_peri[:, :, k].any()]
    if not zs:
        return NA + ": nenhuma fatia anotada com pericardium"
    escolhidas = [zs[i] for i in np.linspace(0, len(zs) - 1, min(n_fatias, len(zs))).astype(int)]

    fig, eixos = plt.subplots(1, len(escolhidas), figsize=(5 * len(escolhidas), 5.6))
    eixos = np.atleast_1d(eixos)
    for ax, k in zip(eixos, escolhidas):
        ax.imshow(np.rot90(img[:, :, k]), cmap="gray", vmin=-200, vmax=400)
        ax.contour(np.rot90(gt_peri[:, :, k]), levels=[0.5], colors="#00d0ff", linewidths=1.6)
        ax.contour(np.rot90(pred[:, :, k]), levels=[0.5], colors="#ff5c00", linewidths=1.2)
        ax.set_title(f"z={k} (fatia anotada)", fontsize=9)
        ax.axis("off")
    d = caso_medido["parte2_metricas"]["dice"]
    fig.suptitle(f"{cid} — ciano: pericardium GT SAROS · laranja: pericardium predito "
                 f"(trunk_cavities) — dice nas fatias anotadas = {d:.4f}", fontsize=10)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(destino, dpi=130)
    plt.close(fig)
    return str(destino)


# ---------------------------------------------------------------- orquestracao


def medir(log=print) -> dict:
    """Roda as partes 1-5 sobre o manifesto ja adquirido. Grava em resultados/."""
    manifesto = json.loads(ARQ_MANIFESTO.read_text(encoding="utf-8"))
    por_id = {c["id"]: c for c in manifesto["declaracao"]["casos"]}

    casos, falhas = [], []
    for c in manifesto["casos"]:
        try:
            casos.append(medir_caso(por_id[c["id"]], log=log))
            log(f"{c['id']}: medido")
        except (AquisicaoInvalida, DesalinhamentoGeometrico) as e:
            falhas.append({"id": c["id"], "erro": type(e).__name__, "mensagem": str(e)})
            log(f"{c['id']}: ABORTADO — {e}")

    def col(caminho):
        return [_cava(c, caminho) for c in casos]

    resumo = {
        "parte1_gt": {
            "razao_preenchimento_2d_agregada": distribuicao(
                col("parte1_forma_gt.razao_preenchimento_2d_agregada")),
            "meia_espessura_no_plano_mediana_mm": distribuicao(
                col("parte1_forma_gt.meia_espessura_no_plano_mm.mediana")),
            "meia_espessura_no_plano_p95_mm": distribuicao(
                col("parte1_forma_gt.meia_espessura_no_plano_mm.p95")),
            "volume_ml_nas_fatias_anotadas": distribuicao(
                col("parte1_forma_gt.volume_ml_nas_fatias_anotadas")),
            "n_componentes_2d_mediana": distribuicao(
                col("parte1_forma_gt.n_componentes_2d_por_fatia.mediana")),
            "frac_heart_predito_dentro_do_gt": distribuicao(
                col("parte1_contencao_coracao_predito.frac_heart_dentro_de_pericardium")),
            "veredito_forma": {c["id"]: _cava(c, "parte1_forma_gt.veredito_forma") for c in casos},
        },
        "parte2_comparacao": {
            k: distribuicao(col(f"parte2_metricas.{k}"))
            for k in ("dice", "iou", "recall_gt", "precision_pred", "volume_gt_ml",
                      "volume_pred_ml", "erro_volume_abs_ml", "erro_volume_abs_pct")
        } | {
            "hd95_no_plano_mediana_mm": distribuicao(
                col("parte2_distancias.hd95_no_plano_mm.mediana")),
            "assd_no_plano_mediana_mm": distribuicao(
                col("parte2_distancias.assd_no_plano_mm.mediana")),
            "independencia_incerta": RESSALVA_INDEPENDENCIA,
        },
        "parte3_hipoteses": {
            "dice_pred_peri_contra": {
                nome: distribuicao(col(f"parte3_contra_todas_classes.por_rotulo_saros.{nome}.dice"))
                for nome in list(EQUIV_TS_SAROS) + ["pericardium_U_mediastinum",
                                                    "thoracic_cavity_U_pericardium_U_mediastinum"]
            },
            "melhor_alvo_por_caso": {c["id"]: _cava(c, "parte3_contra_todas_classes.melhor_dice")
                                     for c in casos},
            "pareado_dice_pericardium_x_mediastinum": pareado(
                casos, "parte3_contra_todas_classes.por_rotulo_saros.pericardium.dice",
                "parte3_contra_todas_classes.por_rotulo_saros.mediastinum.dice"),
            "forma_pred_razao_preenchimento_2d": distribuicao(
                col("parte3_forma_pred.razao_preenchimento_2d_agregada")),
            "forma_pred_meia_espessura_mediana_mm": distribuicao(
                col("parte3_forma_pred.meia_espessura_no_plano_mm.mediana")),
            "frac_heart_predito_dentro_da_pred": distribuicao(
                col("parte3_contencao_coracao_na_pred.frac_heart_dentro_de_pericardium")),
            "composicao_media_pred_em_saros": {
                r: distribuicao([_cava(c, f"parte3_composicao_pred_em_saros."
                                          f"fracao_por_rotulo_saros.{r}") or 0.0 for c in casos])
                for r in sorted({k for c in casos
                                 for k in (_cava(c, "parte3_composicao_pred_em_saros."
                                                    "fracao_por_rotulo_saros") or {})})
            },
        },
    }

    # PARTE 5 — representativos escolhidos DEPOIS de medir, pelo dice medido.
    figuras = {}
    if casos:
        ordenados = sorted(casos, key=lambda c: _cava(c, "parte2_metricas.dice"))
        escolha = {"pior": ordenados[0], "mediana": ordenados[len(ordenados) // 2],
                   "melhor": ordenados[-1]}
        for papel, c in escolha.items():
            figuras[papel] = {
                "id": c["id"], "dice": _cava(c, "parte2_metricas.dice"),
                "png": figura_caso(c, DIR_RESULTADOS / "figuras" / f"{papel}_{c['id']}.png"),
            }

    saida = {
        "ressalva_independencia": RESSALVA_INDEPENDENCIA,
        "definicao_do_gt": "o paper do SAROS descreve `pericardium` como rotulo de REGIAO "
                           "CORPORAL, listado ao lado das cavidades e do mediastino — nao como "
                           "o saco fibroso. Nenhum Dice muda essa definicao.",
        "restricao": "TODA metrica restrita as fatias anotadas (nenhum voxel 255), "
                     "selecionadas pelo teste != 255 e nunca por [::5].",
        "n_casos": len(casos), "falhas": falhas,
        "resumo": resumo, "figuras": figuras, "casos": casos,
    }
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    (DIR_RESULTADOS / "medicao.json").write_text(
        json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")
    return saida


# ------------------------------------------------------ autoteste da medicao


def _autoteste_medicao() -> None:
    """Controles POSITIVOS das metricas novas: cada uma FALHA quando deveria."""
    from .segmentation_metrics import dice

    sp = (1.0, 1.0, 5.0)
    nz = 20
    anot = np.zeros(nz, bool)
    anot[::5] = True

    # anel (casca) x disco (solido) — controle da forma
    yy, xx = np.mgrid[0:64, 0:64]
    r = np.sqrt((yy - 32.0) ** 2 + (xx - 32.0) ** 2)
    anel2d, disco2d = (r > 18) & (r < 20), r < 20
    anel = np.zeros((64, 64, nz), bool)
    disco = np.zeros((64, 64, nz), bool)
    anel[:, :, anot] = anel2d[:, :, None]
    disco[:, :, anot] = disco2d[:, :, None]

    fa = forma_esparsa(anel, sp, anot)
    fd = forma_esparsa(disco, sp, anot)
    assert fa["veredito_forma"] == "casca", fa["razao_preenchimento_2d_agregada"]
    assert fd["veredito_forma"] == "solido preenchido", fd["razao_preenchimento_2d_agregada"]
    # CONTROLE POSITIVO da escolha 2D: o fill 3D NAO distingue os dois com anotacao
    # esparsa — se um dia alguem trocar 2D por 3D aqui, isto documenta o custo.
    from scipy.ndimage import binary_fill_holes
    assert int(binary_fill_holes(anel).sum()) == int(anel.sum()), \
        "fill 3D deixaria de ser cego — revisar a justificativa de forma_esparsa"
    # espessura: o anel tem ~1 voxel de meia-espessura, o disco ~10
    assert fa["meia_espessura_no_plano_mm"]["mediana"] < 2.0, fa
    assert fd["meia_espessura_no_plano_mm"]["mediana"] > 5.0, fd

    # CALIBRACAO — um SACO FIBROSO com a geometria que a anatomia descreve
    # (parede de 2 mm, raio de 55 mm), na resolucao real destes casos. E o
    # controle que da sentido ao veredito "solido preenchido": prova que a
    # medida SABE dizer "casca" quando o objeto e um saco de verdade.
    sp_real = (0.73, 0.73, 5.0)
    yy2, xx2 = np.mgrid[0:256, 0:256]
    r2 = np.hypot(yy2 - 128.0, xx2 - 128.0)
    raio, parede = 55 / sp_real[0], 2.0 / sp_real[0]
    saco = np.zeros((256, 256, nz), bool)
    saco[:, :, anot] = ((r2 > raio - parede) & (r2 < raio))[:, :, None]
    fs = forma_esparsa(saco, sp_real, anot)
    assert fs["veredito_forma"] == "casca", fs["razao_preenchimento_2d_agregada"]
    assert fs["razao_preenchimento_2d_agregada"] < 0.10, fs
    assert fs["meia_espessura_no_plano_mm"]["p95"] < 2.0, fs

    # restricao as fatias anotadas: lixo nas fatias de IGNORE nao pode entrar
    gt, pred = disco.copy(), disco.copy()
    lixo = np.zeros_like(pred)
    lixo[:, :, ~anot] = True                      # falso positivo gigantesco, so em ignore
    pred_com_lixo = pred | lixo
    m_limpo = metricas_esparsas(pred, gt, sp, anot)
    m_lixo = metricas_esparsas(pred_com_lixo, gt, sp, anot)
    assert m_limpo["dice"] == 1.0 and m_lixo["dice"] == 1.0, (m_limpo["dice"], m_lixo["dice"])
    assert m_lixo["volume_pred_ml"] == m_limpo["volume_pred_ml"], m_lixo
    # CONTROLE POSITIVO: sem a restricao o mesmo lixo destruiria o dice.
    assert dice(pred_com_lixo, gt) < 0.4, "o lixo nao era grande o bastante para o controle"

    # e o inverso: erro DENTRO da fatia anotada TEM que aparecer
    errado = np.zeros_like(gt)
    errado[0:8, 0:8, anot] = True  # blob disjunto do disco central
    assert metricas_esparsas(errado, gt, sp, anot)["dice"] == 0.0, "metrica cega a erro real"

    # distancias no plano: fatia com um lado vazio nao entra, e e contada
    meio = np.zeros_like(gt)
    z0 = int(np.flatnonzero(anot)[0])
    meio[:, :, z0] = disco2d
    dd = distancias_no_plano(meio, gt, sp, anot)
    assert dd["n_fatias_pareadas"] == 1, dd["n_fatias_pareadas"]
    assert len(dd["fatias_com_um_lado_vazio"]) == int(anot.sum()) - 1, dd
    assert dd["hd95_no_plano_mm"]["mediana"] == 0.0, dd
    assert dd["hd95_3d_mm"].startswith(NA), dd

    # composicao: soma 1 e aponta o rotulo certo
    rot = np.zeros((64, 64, nz), np.uint8) + IGNORE
    rot[:, :, anot] = 0
    rot[disco] = ROTULO_PERICARDIUM
    comp = composicao(disco, rot, anot)
    assert abs(sum(comp["fracao_por_rotulo_saros"].values()) - 1.0) < 1e-9, comp
    assert comp["fracao_por_rotulo_saros"]["pericardium"] == 1.0, comp
    # CONTROLE POSITIVO: predicao deslocada para o mediastinum tem que ACUSAR isso
    rot2 = rot.copy()
    rot2[disco] = 9  # mediastinum
    comp2 = composicao(disco, rot2, anot)
    assert comp2["fracao_por_rotulo_saros"].get("pericardium", 0.0) == 0.0, comp2
    assert comp2["fracao_por_rotulo_saros"]["mediastinum"] == 1.0, comp2
    melhor = contra_todas_classes(disco, rot2, sp, anot)
    assert melhor["melhor_dice"] == "mediastinum" and not melhor["melhor_e_pericardium"], melhor

    # distribuicao nao inventa numero
    assert distribuicao([])["n"] == 0 and distribuicao([1.0, 2.0, 3.0])["mediana"] == 2.0
    assert pareado([], "a", "b")["n"] == 0

    print("saros_pericardium.py: autoteste da MEDICAO OK "
          "(forma, restricao esparsa, distancias, composicao, discriminacao)")


if __name__ == "__main__":
    import sys

    if "--autoteste" in sys.argv:
        _autoteste()
        _autoteste_medicao()
    elif "--medir" in sys.argv:
        r = medir()
        print(json.dumps({"n_casos": r["n_casos"], "falhas": r["falhas"],
                          "resumo": r["resumo"], "figuras": r["figuras"]},
                         indent=2, ensure_ascii=False))
    else:
        m = adquirir()
        print(json.dumps({
            "casos_ok": len(m["casos"]),
            "falhas": m["falhas"],
            "licenca_mascaras": m["declaracao"]["proveniencia"]["licenca_mascaras"],
        }, indent=2, ensure_ascii=False))
