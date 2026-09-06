"""Fase 10 — o par MAASTRO: mesma instituicao, outra convencao.

PERGUNTA DA FASE: quanto do erro do esofago no LCTSC e explicavel por CONVENCAO
DE CONTORNO, e nao por anatomia nem por instituicao?

O par LCTSC-S1 x NSCLC-Radiomics e a unica celula publica em que a instituicao
(MAASTRO, recuperada na fase 9 por quatro canais independentes) fica FIXA e so a
convencao de contorno muda. Esta fase adquire o lado B do par e mede se essa
fixacao SOBREVIVE ao protocolo de aquisicao — porque "mesma instituicao" so
significa "mesmo protocolo" se o DICOM disser que sim.

Este arquivo NAO treina, NAO mede Dice e NAO decide modelo. Ele faz tres coisas:

  Parte 0 — DECLARA o subconjunto do NSCLC ANTES de qualquer medida, por regra
            deterministica (sha256 da semente + PatientID, como a fase 5), e
            grava a declaracao em disco antes do primeiro byte de CT baixado.
            Elegibilidade e a UNICA condicao, e ela e lida do arquivo: o
            RTSTRUCT tem que conter uma ROI de esofago. O nome real vem do
            `dcmrtstruct2nii ls`, nunca da literatura.

  Parte 1 — TABELA DE COMPARABILIDADE. 14 campos de protocolo lidos do DICOM
            dos dois lados. Campo ausente ou vazio = "nao disponivel". Se os
            protocolos divergirem, o par MAASTRO deixa de isolar estilo — e isso
            e achado de primeira ordem, nao detalhe.

  Parte 2 — DEFINICAO do GT, das FONTES. O que cada dataset DIZ que mandou
            contornar, verbatim e com URL. Ausencia de documentacao e resultado,
            nao lacuna a preencher por analogia.

  Parte 3 — MORFOLOGIA do GT, sem modelo nenhum. Volume, extensao, area
            transversal, largura efetiva (2 x EDT no eixo medial), variacao de
            calibre em Z, posicao relativa a carina e folga ate traqueia e
            aorta, para os quatro grupos: LCTSC-S1, S2, S3 e o subconjunto do
            NSCLC. O GT e MACICO (fase 9): "espessura de parede" e proibido.

  Parte 4 — os QUATRO GRUPOS, com Kruskal-Wallis. Cada medida sai marcada como
            ABSOLUTA (carrega tamanho anatomico junto com estilo) ou
            NORMALIZADA por caso (divide o tamanho fora e deixa o estilo).

  Parte 5 — o par S1 x NSCLC: Mann-Whitney, permutacao, Cliff delta, IC por
            bootstrap, efeito minimo detectavel por simulacao e correcao de
            multiplicidade. Nada e concluido por p. E a traducao da diferenca de
            estilo para a unidade do baseline: qual Dice dois contornos
            perfeitos de estilos diferentes teriam entre si.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.estilo_esofago --autoteste
    python -m scripts.validation.tier2.estilo_esofago --mutacao
    python -m scripts.validation.tier2.estilo_esofago --declarar
    python -m scripts.validation.tier2.estilo_esofago --adquirir
    python -m scripts.validation.tier2.estilo_esofago --tabela
    python -m scripts.validation.tier2.estilo_esofago --aux
    python -m scripts.validation.tier2.estilo_esofago --morfologia
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage, stats
from skimage.morphology import skeletonize

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation import segmentation_metrics as sm  # noqa: E402
from scripts.validation.espessura import calibre_mm  # noqa: E402
from scripts.validation.tier2 import fase5, geometria, tcia  # noqa: E402
from scripts.validation.tier2 import protocolo_esofago as prot  # noqa: E402
from scripts.validation.tier2 import representabilidade_esofago as rep  # noqa: E402
from scripts.validation.tier2 import rtstruct as rtst  # noqa: E402

ND = "nao disponivel"   # o campo nao existe no DICOM, ou existe vazio
NM = "nao medido"
NA = "nao aplicavel"

COLECAO_B = "NSCLC-Radiomics"
RAIZ_LCTSC = Path(".clinica-dados/tier2/lctsc")
RAIZ_NSCLC = Path(".clinica-dados/nsclc-radiomics")
SAIDA_FASE10 = RAIZ_LCTSC / "fase10"

# --------------------------------------------------------- Parte 0: a regra

# Fixa. Trocar isto refaz o sorteio — e refazer sorteio depois de medir e
# escolher caso por resultado, que e exatamente o que esta proibido.
SEMENTE_SUBCONJUNTO = "vrmed-fase10-estilo-2026-09-05"
N_ALVO = 25              # dentro da faixa declarada pela fase (20 a 30)
BLOCO_CENSO = 12         # quantos casos o censo examina por rodada
MAX_WORKERS = 6          # cortesia com a API publica do TCIA

# O nome da ROI NAO e presumido. Esta regex e um CRIVO sobre o nome real lido do
# arquivo; o censo grava a distribuicao completa dos nomes encontrados, e e ela
# — nao a regex — que responde "os nomes variam entre casos?".
CRIVO_ESOFAGO = re.compile(r"o?esoph")

# Datasets que ESTA fase pode tocar. Qualquer outro e recusa, nao aviso.
DATASETS_PERMITIDOS = {
    "LCTSC": "somente o conjunto `development` (30 casos), instituicao S1 = MAASTRO",
    COLECAO_B: "subconjunto declarado por sha256(semente|PatientID) antes de medir",
}

# Os 14 campos que a Parte 1 le. Ausente = ND, nunca inferido de outro campo.
CAMPOS_PROTOCOLO = (
    "InstitutionName", "Manufacturer", "ManufacturerModelName", "StationName",
    "SliceThickness", "PixelSpacing", "SpacingBetweenSlices", "ConvolutionKernel",
    "KVP", "ContrastBolusAgent", "SeriesDescription", "StudyDescription",
    "ProtocolName", "ReconstructionDiameter",
)


def ordem_deterministica(patient_id: str) -> str:
    """sha256(semente|PatientID) — mesma construcao da fase 5, mesmo motivo.

    Nao usa `random` com semente porque a ordem do `random` depende da ordem de
    iteracao da entrada; o hash depende so do identificador.
    """
    return hashlib.sha256(f"{SEMENTE_SUBCONJUNTO}|{patient_id}".encode()).hexdigest()


def listar_pacientes(colecao: str = COLECAO_B, timeout: int = 120) -> list[str]:
    """getPatient — a lista de PatientID da colecao, direto da API do TCIA."""
    url = (f"{tcia.BASE}/getPatient?"
           + urllib.parse.urlencode({"Collection": colecao}))
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (host fixo, https)
        return sorted(p["PatientId"] for p in json.load(r))


# ============================================== guardas (codigo, nao prosa)


class MisturaDeInstituicoes(prot.RecusaDeProtocolo):
    """O lado LCTSC do par tem caso de outra instituicao — o par deixa de ser par."""


class DatasetNaoPermitido(prot.RecusaDeProtocolo):
    """GT vindo de dataset que esta fase nao declarou — comparacao fora do escopo."""


class ConjuntoProibido(prot.RecusaDeProtocolo):
    """Caso do LCTSC fora do `development`. O `validation` nao escolhe nada aqui."""


class SpacingAusente(prot.RecusaDeProtocolo):
    """Sem spacing nao ha milimetro — toda distancia viraria contagem de voxel."""


# Excecoes e guardas REUSADAS (nao reimplementadas):
#   prot.TestGasto / exigir_sem_repeticao / exigir_mascara_na_grade
#   prot.exigir_affine_compativel  -> geometria.DesalinhamentoGeometrico
TestGasto = prot.TestGasto

GUARDAS = (
    "instituicao_unica",   # mistura de instituicoes
    "sem_repeticao",       # caso duplicado                     (REUSO)
    "apenas_development",  # uso inadvertido do LCTSC test      (parcial REUSO: TestGasto)
    "dataset_permitido",   # GT fora do dataset permitido
    "mascara_na_grade",    # grades incompativeis               (REUSO)
    "spacing_presente",    # spacing ausente
    "affine_compativel",   # affine incompativel                (REUSO)
)

# Mecanismo de MUTACAO. Guarda reusada e desligada NO MODULO DELA, senao a
# mutacao testaria um wrapper e nao a tranca.
_DESLIGADAS: set[str] = set()
_ONDE_DESLIGAR = {
    "sem_repeticao": prot._DESLIGADAS,
    "mascara_na_grade": prot._DESLIGADAS,
    "affine_compativel": prot._DESLIGADAS,
}


def _desligada(nome: str) -> dict[str, Any] | None:
    """Resultado neutro com a MESMA chave `recusou` do caminho legitimo.

    Assim, sob mutacao, o unico assert que pode cair e o do controle positivo —
    nunca um KeyError no caminho feliz. Um teste que cai pelo motivo errado nao
    prova nada.
    """
    if nome in _DESLIGADAS:
        return {"guarda": nome, "estado": "DESLIGADA", "recusou": False}
    return None


def _ok(nome: str, **extra: Any) -> dict[str, Any]:
    return {"guarda": nome, "estado": "ativa", "recusou": False, **extra}


def exigir_instituicao_unica(casos: list[str], esperada: str = "S1") -> dict[str, Any]:
    """Guarda 1 — o lado LCTSC do par tem que ser de UMA instituicao so.

    O par MAASTRO existe porque S1 = MAASTRO. Um caso S2 ou S3 dentro dele
    reintroduz a variavel que o par foi construido para eliminar, e o resultado
    passaria a medir instituicao vestida de convencao.
    """
    if (r := _desligada("instituicao_unica")) is not None:
        return r
    achadas = {c: fase5.instituicao_de(c) for c in casos}
    fora = sorted(c for c, i in achadas.items() if i != esperada)
    if fora:
        raise MisturaDeInstituicoes(
            f"{len(fora)} caso(s) fora de {esperada}: {fora[:5]}"
            f"{'...' if len(fora) > 5 else ''} (instituicoes {sorted(set(achadas.values()))}). "
            "O par so isola convencao enquanto a instituicao fica fixa."
        )
    return _ok("instituicao_unica", instituicao=esperada, n=len(casos))


def exigir_apenas_development(casos: list[str], split: dict[str, list[str]]) -> dict[str, Any]:
    """Guarda 3 — caso do LCTSC fora do `development`: recusa.

    Duas recusas, de gravidade diferente e por isso com excecoes diferentes:
      - `test`       -> `TestGasto` (REUSO). Foi gasto na fase 7 e esta fora
                        desta fase por completo;
      - `validation` -> `ConjuntoProibido`. Esta fase nao escolhe parametro
                        nenhum, entao nao tem nada que ler o validation.
    """
    if (r := _desligada("apenas_development")) is not None:
        return r
    em_test = sorted(set(casos) & set(split.get("test", [])))
    if em_test:
        raise TestGasto(
            f"{len(em_test)} caso(s) do LCTSC `test` nesta fase: {em_test[:5]}"
            f"{'...' if len(em_test) > 5 else ''}. O test foi gasto na fase 7; "
            "uma leitura agora seria a segunda e nao mede mais nada."
        )
    em_val = sorted(set(casos) & set(split.get("validation", [])))
    if em_val:
        raise ConjuntoProibido(
            f"{len(em_val)} caso(s) do LCTSC `validation` nesta fase: {em_val[:5]}"
            f"{'...' if len(em_val) > 5 else ''}. Esta fase MEDE, nao escolhe."
        )
    faltantes = sorted(set(casos) - set(split.get("development", [])))
    if faltantes:
        raise ConjuntoProibido(
            f"{len(faltantes)} caso(s) do LCTSC fora dos tres conjuntos declarados: "
            f"{faltantes[:5]}. Caso que nao esta no split nao tem procedencia."
        )
    return _ok("apenas_development", n=len(casos))


def exigir_dataset_permitido(dataset: str, casos: list[str] | None = None,
                             declarados: list[str] | None = None) -> dict[str, Any]:
    """Guarda 4 — GT fora do dataset permitido: recusa.

    Cobre os dois jeitos de o GT escorregar para fora do escopo: um dataset que
    esta fase nunca declarou, e um caso do NSCLC que nao estava na lista gravada
    ANTES de medir (que seria escolher caso depois de ver o dado).
    """
    if (r := _desligada("dataset_permitido")) is not None:
        return r
    if dataset not in DATASETS_PERMITIDOS:
        raise DatasetNaoPermitido(
            f"dataset `{dataset}` nao esta em {sorted(DATASETS_PERMITIDOS)}. "
            "Esta fase compara DUAS convencoes; uma terceira nao e comparacao, e mistura."
        )
    if declarados is not None and casos is not None:
        intrusos = sorted(set(casos) - set(declarados))
        if intrusos:
            raise DatasetNaoPermitido(
                f"{len(intrusos)} caso(s) de `{dataset}` fora do subconjunto declarado: "
                f"{intrusos[:5]}. A lista foi gravada antes da primeira medida de proposito."
            )
    return _ok("dataset_permitido", dataset=dataset, n=len(casos or []))


def exigir_spacing_presente(geo: dict[str, Any], rotulo: str = "serie") -> dict[str, Any]:
    """Guarda 6 — spacing ausente, zero ou nao finito: recusa.

    Sem spacing em mm, HD95 e ASSD viram contagem de voxel e ficam
    incomparaveis entre casos com grades diferentes — que e exatamente o caso
    aqui: o S1 tem dz 3,0 mm e o NSCLC ainda nao foi medido.
    """
    if (r := _desligada("spacing_presente")) is not None:
        return r
    xy = geo.get("pixel_spacing_mm")
    dz = geo.get("espacamento_z_mediano_mm")
    valores = list(xy or []) + ([dz] if dz is not None else [])
    if not xy or len(xy) < 2 or dz is None:
        raise SpacingAusente(
            f"{rotulo}: spacing incompleto (PixelSpacing={xy!r}, dz={dz!r}). "
            "Sem milimetro nao ha distancia, so contagem de voxel."
        )
    ruins = [v for v in valores if not np.isfinite(v) or v <= 0]
    if ruins:
        raise SpacingAusente(f"{rotulo}: spacing invalido {ruins} — zero ou nao finito.")
    return _ok("spacing_presente", pixel_spacing_mm=[float(v) for v in xy],
               dz_mm=float(dz), z_uniforme=bool(geo.get("espacamento_z_uniforme")))


def exigir_sem_repeticao(casos: list[str], rotulo: str = "subconjunto") -> dict[str, Any]:
    """Guarda 2 — caso duplicado. REUSO integral de protocolo_esofago."""
    return prot.exigir_sem_repeticao(casos, rotulo)


def exigir_mascara_na_grade(mascara, shape_referencia, rotulo: str = "mascara") -> dict[str, Any]:
    """Guarda 5 — grades incompativeis no nivel do ARRAY. REUSO de protocolo_esofago."""
    return prot.exigir_mascara_na_grade(mascara, shape_referencia, rotulo)


def exigir_affine_compativel(caminho_a: Path, caminho_b: Path) -> dict[str, Any]:
    """Guarda 7 — affine incompativel. REUSO (leva a geometria.verificar_alinhamento)."""
    return prot.exigir_affine_compativel(caminho_a, caminho_b)


# ================================================ Parte 0 — censo + declaracao


def _rois_do_caso(patient_id: str, raiz: Path) -> dict[str, Any]:
    """Baixa SO o RTSTRUCT (≈1,5 MB) e le os nomes REAIS das ROIs."""
    registro: dict[str, Any] = {"patient_id": patient_id}
    try:
        series = tcia.listar_series(COLECAO_B, patient_id=patient_id)
        rts = [s for s in series if s.get("Modality") == "RTSTRUCT"]
        cts = [s for s in series if s.get("Modality") == "CT"]
        if len(rts) != 1 or len(cts) != 1:
            registro["erro"] = f"{len(cts)} CT e {len(rts)} RTSTRUCT (esperava 1 e 1)"
            return registro
        destino = tcia.baixar_serie(rts[0], raiz / patient_id / "rtstruct")
        arquivos = sorted(destino.glob("*.dcm"))
        if len(arquivos) != 1:
            registro["erro"] = f"{len(arquivos)} arquivos no RTSTRUCT"
            return registro
        rois = rtst.listar_rois(arquivos[0])
        registro.update({
            "rois": rois,
            "rois_esofago": [r for r in rois if CRIVO_ESOFAGO.search(r.lower())],
            "licenca": tcia.licenca(rts[0]),
            "software_rtstruct": rts[0].get("SoftwareVersions"),
            "fabricante_rtstruct": rts[0].get("Manufacturer"),
            "n_imagens_ct": cts[0].get("ImageCount"),
        })
        registro["elegivel"] = len(registro["rois_esofago"]) == 1
        if len(registro["rois_esofago"]) > 1:
            registro["erro"] = f"{len(registro['rois_esofago'])} ROIs de esofago — ambiguo"
    except Exception as e:  # noqa: BLE001 — um caso quebrado nao pode derrubar o censo
        registro["erro"] = f"{type(e).__name__}: {e}"
        registro["elegivel"] = False
    registro.setdefault("elegivel", False)
    return registro


def censo_e_declaracao(raiz: Path = RAIZ_NSCLC, n_alvo: int = N_ALVO, log=print) -> dict[str, Any]:
    """Caminha a ordem deterministica ate juntar `n_alvo` elegiveis e DECLARA.

    Caminhar em vez de fixar um prefixo evita a unica constante que eu teria de
    escolher depois de olhar o dado. O criterio de parada e o numero de
    elegiveis, nunca uma propriedade do caso.
    """
    raiz = Path(raiz)
    p_decl = raiz / "subconjunto.json"

    pacientes = listar_pacientes()
    ordem = sorted(pacientes, key=ordem_deterministica)
    log(f"{COLECAO_B}: {len(pacientes)} casos na colecao; caminhando a ordem deterministica")

    examinados: list[dict[str, Any]] = []
    elegiveis: list[str] = []
    i = 0
    while len(elegiveis) < n_alvo and i < len(ordem):
        bloco = ordem[i:i + BLOCO_CENSO]
        i += len(bloco)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            registros = list(ex.map(lambda p: _rois_do_caso(p, raiz), bloco))
        # a ordem do bloco e restaurada: o resultado nao depende do escalonamento
        por_id = {r["patient_id"]: r for r in registros}
        for pid in bloco:
            r = por_id[pid]
            examinados.append(r)
            if r["elegivel"] and len(elegiveis) < n_alvo:
                elegiveis.append(pid)
        log(f"  examinados {len(examinados)}, elegiveis {len(elegiveis)}/{n_alvo}")

    if len(elegiveis) < n_alvo:
        raise RuntimeError(
            f"a colecao inteira ({len(ordem)}) rendeu {len(elegiveis)} elegiveis < {n_alvo}"
        )

    # distribuicao de nomes: e ela que responde "os nomes variam entre casos?"
    dist_nomes: dict[str, int] = {}
    dist_esofago: dict[str, int] = {}
    for r in examinados:
        for nome in r.get("rois", []):
            dist_nomes[nome] = dist_nomes.get(nome, 0) + 1
        for nome in r.get("rois_esofago", []):
            dist_esofago[nome] = dist_esofago.get(nome, 0) + 1

    com_rois = [r for r in examinados if "rois" in r]
    licencas = sorted({json.dumps(r["licenca"], sort_keys=True) for r in com_rois})
    censo = {
        "colecao": COLECAO_B,
        "n_na_colecao": len(ordem),
        "n_examinados": len(examinados),
        "n_com_rtstruct_lido": len(com_rois),
        "n_elegiveis_entre_examinados": sum(1 for r in examinados if r["elegivel"]),
        "criterio_elegibilidade": (
            f"exatamente 1 ROI cujo nome casa com /{CRIVO_ESOFAGO.pattern}/ (minusculas), "
            "lida do proprio RTSTRUCT via dcmrtstruct2nii"
        ),
        "distribuicao_de_nomes_de_roi": dict(sorted(dist_nomes.items(), key=lambda kv: -kv[1])),
        "distribuicao_de_nomes_de_esofago": dist_esofago,
        "casos_sem_roi_de_esofago": [r["patient_id"] for r in examinados if not r["elegivel"]],
        "licencas_distintas_lidas_da_api": [json.loads(x) for x in licencas],
        "software_rtstruct_distinto": sorted({str(r.get("software_rtstruct")) for r in com_rois}),
        "fabricante_rtstruct_distinto": sorted({str(r.get("fabricante_rtstruct")) for r in com_rois}),
        "examinados": examinados,
    }
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "censo_rois.json").write_text(
        json.dumps(censo, indent=2, ensure_ascii=False), encoding="utf-8")

    declaracao = {
        "declarado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "colecao": COLECAO_B,
        "semente": SEMENTE_SUBCONJUNTO,
        "metodo": (
            "ordem = sha256(semente|PatientID); caminha essa ordem e aceita os primeiros "
            f"{n_alvo} casos ELEGIVEIS. Elegibilidade e a unica condicao e nao depende de "
            "nenhuma medida do caso — nem imagem, nem volume, nem desempenho."
        ),
        "n_alvo": n_alvo,
        "n_examinados_ate_completar": len(examinados),
        "criterio_elegibilidade": censo["criterio_elegibilidade"],
        "gravado_antes_de": "qualquer download de CT e qualquer medida",
        "casos": elegiveis,
        "roi_de_esofago_por_caso": {
            r["patient_id"]: r["rois_esofago"][0] for r in examinados
            if r["patient_id"] in set(elegiveis)
        },
    }

    if p_decl.exists():
        antigo = json.loads(p_decl.read_text(encoding="utf-8"))
        if antigo.get("casos") != declaracao["casos"]:
            raise RuntimeError(
                f"{p_decl} ja existe e DIFERE do que seria gerado agora. Redeclarar o "
                "subconjunto depois de medir e escolher caso por resultado. Apague o "
                "arquivo de proposito se souber o que esta fazendo."
            )
        log("subconjunto.json ja existe e confere — nao reescrito")
        return {"declaracao": antigo, "censo": censo}

    p_decl.write_text(json.dumps(declaracao, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"subconjunto DECLARADO ({len(elegiveis)} casos) -> {p_decl}")
    return {"declaracao": declaracao, "censo": censo}


def carregar_declaracao(raiz: Path = RAIZ_NSCLC) -> dict[str, Any]:
    return json.loads((Path(raiz) / "subconjunto.json").read_text(encoding="utf-8"))


# ==================================================== Parte 0b — aquisicao


def adquirir_caso(patient_id: str, roi: str, raiz: Path = RAIZ_NSCLC, log=print) -> dict[str, Any]:
    """Baixa CT + RTSTRUCT, converte e PROVA a grade. Aborta o caso se nao provar.

    Aborta em vez de reamostrar: reamostrar para "consertar" a grade inventa
    fronteira que nenhum anotador desenhou.
    """
    destino = Path(raiz) / patient_id
    series = tcia.listar_series(COLECAO_B, patient_id=patient_id)
    ct = [s for s in series if s.get("Modality") == "CT"]
    rt = [s for s in series if s.get("Modality") == "RTSTRUCT"]
    if len(ct) != 1 or len(rt) != 1:
        raise RuntimeError(f"{patient_id}: {len(ct)} CT e {len(rt)} RTSTRUCT")
    if ct[0]["StudyInstanceUID"] != rt[0]["StudyInstanceUID"]:
        raise RuntimeError(f"{patient_id}: CT e RTSTRUCT em estudos diferentes")

    dir_ct = tcia.baixar_serie(ct[0], destino / "ct")
    dir_rt = tcia.baixar_serie(rt[0], destino / "rtstruct")
    arquivo_rt = sorted(dir_rt.glob("*.dcm"))[0]

    dir_gt = destino / "gt"
    imagem = dir_gt / rtst.NOME_IMAGEM
    mascara = dir_gt / f"{rtst.PREFIXO_MASCARA}{roi}.nii.gz"
    if not (imagem.exists() and mascara.exists()):
        rtst.converter(arquivo_rt, dir_ct, dir_gt, estruturas=[roi])
    if not mascara.exists():
        raise FileNotFoundError(f"{patient_id}: dcmrtstruct2nii nao gravou {mascara.name}")

    geo_dicom = geometria.metadados_dicom(dir_ct)
    g_spacing = exigir_spacing_presente(geo_dicom, f"{patient_id}/CT")
    g_affine = exigir_affine_compativel(imagem, mascara)     # mesma grade, nivel arquivo
    ref = geometria.descrever_nifti(imagem)
    bruto = np.asarray(__import__("nibabel").load(str(mascara)).dataobj)
    g_grade = exigir_mascara_na_grade(bruto, ref["shape"], f"{patient_id}/{roi}")

    # O dz do NIfTI e o dz do DICOM podem NAO ser o mesmo numero: quando as fatias
    # nao sao equidistantes, o dcmrtstruct2nii regulariza a grade e a diferenca
    # some sem aviso. Nao e recusa (imagem e mascara continuam na MESMA grade, que
    # e o que a comparacao exige), mas fica REGISTRADA — uma esticada de meio por
    # cento em z contamina qualquer metrica em mm depois.
    dz_nii = float(ref["zooms_mm"][2])
    dz_dcm = geo_dicom["espacamento_z_mediano_mm"]
    dz_reg = {
        "dz_nifti_mm": dz_nii,
        "dz_dicom_mediano_mm": dz_dcm,
        "delta_mm": abs(dz_nii - dz_dcm),
        "z_uniforme_no_dicom": bool(geo_dicom["espacamento_z_uniforme"]),
        "grade_regularizada": bool(abs(dz_nii - dz_dcm) > TOL_MM),
    }
    if dz_reg["grade_regularizada"]:
        log(f"  {patient_id}: AVISO — dz do NIfTI {dz_nii:.4f} mm != dz do DICOM "
            f"{dz_dcm:.4f} mm (fatias nao equidistantes); grade regularizada na conversao")

    registro = {
        "patient_id": patient_id,
        "roi_esofago": roi,
        "status": "ok",
        "dz_nifti_vs_dicom": dz_reg,
        "licenca": tcia.licenca(ct[0]),
        "study_instance_uid": ct[0]["StudyInstanceUID"],
        "series_instance_uid": {"ct": ct[0]["SeriesInstanceUID"],
                                "rtstruct": rt[0]["SeriesInstanceUID"]},
        "fabricante_rtstruct": rt[0].get("Manufacturer"),
        "software_rtstruct": rt[0].get("SoftwareVersions"),
        "n_imagens_ct": ct[0].get("ImageCount"),
        "geometria_nifti": ref,
        "geometria_dicom": geo_dicom,
        "guardas": {"spacing_presente": g_spacing, "affine_compativel": g_affine,
                    "mascara_na_grade": g_grade},
        "caminhos": {"ct": str(dir_ct), "rtstruct": str(arquivo_rt),
                     "imagem": str(imagem), "mascara": str(mascara)},
    }
    log(f"  {patient_id}: {ref['shape']} {tuple(round(z, 4) for z in ref['zooms_mm'])} mm "
        f"{ref['orientacao']} · {g_grade['n_voxels']} voxels de esofago")
    return registro


def adquirir(raiz: Path = RAIZ_NSCLC, log=print) -> dict[str, Any]:
    """Adquire TODO o subconjunto declarado. Caso que falha vira `abortado`.

    Um caso abortado NAO e substituido por outro: substituir seria escolher caso
    por sucesso de conversao, que e uma propriedade medida do caso.
    """
    decl = carregar_declaracao(raiz)
    casos = decl["casos"]
    exigir_dataset_permitido(COLECAO_B, casos, decl["casos"])
    exigir_sem_repeticao(casos, f"{COLECAO_B}/subconjunto")

    registros = []
    for pid in casos:
        roi = decl["roi_de_esofago_por_caso"][pid]
        try:
            registros.append(adquirir_caso(pid, roi, raiz, log))
        except Exception as e:  # noqa: BLE001 — aborta o CASO, com motivo explicito
            log(f"  {pid}: ABORTADO — {type(e).__name__}: {e}")
            registros.append({"patient_id": pid, "roi_esofago": roi, "status": "abortado",
                              "motivo": f"{type(e).__name__}: {e}"})

    ok = [r for r in registros if r["status"] == "ok"]
    resumo = {
        "colecao": COLECAO_B,
        "n_declarados": len(casos),
        "n_adquiridos": len(ok),
        "n_abortados": len(registros) - len(ok),
        "abortados": [{"patient_id": r["patient_id"], "motivo": r["motivo"]}
                      for r in registros if r["status"] != "ok"],
        "grades_regularizadas": [
            {"patient_id": r["patient_id"], **r["dz_nifti_vs_dicom"]}
            for r in ok if r["dz_nifti_vs_dicom"]["grade_regularizada"]],
        "casos": registros,
    }
    (Path(raiz) / "aquisicao.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"aquisicao: {len(ok)}/{len(casos)} ok, {resumo['n_abortados']} abortados")
    return resumo


# ============================================ Parte 1 — tabela de comparabilidade


def _valor(ds, campo: str) -> Any:
    """Valor JSON-safe de um campo, ou ND. Vazio conta como ausente — nao como ''."""
    if campo not in ds:
        return ND
    v = ds[campo].value
    if v is None or (isinstance(v, str) and not v.strip()):
        return ND
    if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
        lista = [float(x) if isinstance(x, (int, float)) or hasattr(x, "real") else str(x)
                 for x in v]
        return lista if lista else ND
    if isinstance(v, (int, float)) or hasattr(v, "real"):
        return float(v)
    return str(v).strip()


def metadados_protocolo(dicom_dir: Path) -> dict[str, Any]:
    """Le os 14 campos em TODAS as fatias da serie e reporta o que variar.

    Le todas porque uma serie com dois protocolos nao aparece na primeira fatia,
    e um campo que varia dentro da serie nao e um valor — e uma distribuicao.
    """
    import pydicom

    arquivos = sorted(Path(dicom_dir).glob("*.dcm"))
    if not arquivos:
        raise FileNotFoundError(f"nenhum .dcm em {dicom_dir}")
    vistos: dict[str, list[Any]] = {c: [] for c in CAMPOS_PROTOCOLO}
    for f in arquivos:
        ds = pydicom.dcmread(str(f), stop_before_pixels=True,
                             specific_tags=list(CAMPOS_PROTOCOLO))
        for c in CAMPOS_PROTOCOLO:
            vistos[c].append(_valor(ds, c))

    saida: dict[str, Any] = {"n_fatias_lidas": len(arquivos)}
    for c, valores in vistos.items():
        distintos = sorted({json.dumps(v, ensure_ascii=False) for v in valores})
        if len(distintos) == 1:
            saida[c] = json.loads(distintos[0])
        else:
            saida[c] = {"VARIA_NA_SERIE": [json.loads(d) for d in distintos]}
    return saida


def _lado_lctsc(raiz: Path = RAIZ_LCTSC) -> list[dict[str, Any]]:
    """Os 10 casos S1 do `development`. Passa pelas guardas antes de ser lido."""
    split = fase5.carregar_split(raiz)
    casos = sorted(c for c in split["development"] if fase5.instituicao_de(c) == "S1")
    exigir_dataset_permitido("LCTSC", casos)
    exigir_apenas_development(casos, split)
    exigir_instituicao_unica(casos, "S1")
    exigir_sem_repeticao(casos, "LCTSC/S1/development")

    linhas = []
    for caso in casos:
        dir_ct = Path(raiz) / caso / "ct"
        geo = geometria.metadados_dicom(dir_ct)
        exigir_spacing_presente(geo, f"{caso}/CT")
        linhas.append({
            "lado": "A", "dataset": "LCTSC", "instituicao": "S1 = MAASTRO",
            "caso": caso, "n_fatias": geo["n_fatias"],
            "dz_mediano_mm": geo["espacamento_z_mediano_mm"],
            "dz_uniforme": geo["espacamento_z_uniforme"],
            **metadados_protocolo(dir_ct),
        })
    return linhas


def _lado_nsclc(raiz: Path = RAIZ_NSCLC) -> list[dict[str, Any]]:
    """Os casos do NSCLC que a aquisicao marcou como `ok`."""
    aq = json.loads((Path(raiz) / "aquisicao.json").read_text(encoding="utf-8"))
    decl = carregar_declaracao(raiz)
    ok = [r for r in aq["casos"] if r["status"] == "ok"]
    exigir_dataset_permitido(COLECAO_B, [r["patient_id"] for r in ok], decl["casos"])
    exigir_sem_repeticao([r["patient_id"] for r in ok], f"{COLECAO_B}/adquiridos")

    linhas = []
    for r in ok:
        dir_ct = Path(r["caminhos"]["ct"])
        geo = r["geometria_dicom"]
        linhas.append({
            "lado": "B", "dataset": COLECAO_B, "instituicao": "MAASTRO (declarada na fonte)",
            "caso": r["patient_id"], "n_fatias": geo["n_fatias"],
            "dz_mediano_mm": geo["espacamento_z_mediano_mm"],
            "dz_uniforme": geo["espacamento_z_uniforme"],
            **metadados_protocolo(dir_ct),
        })
    return linhas


# Tolerancia para comparar campos NUMERICOS de geometria entre os dois lados.
#
# DECLARADA DEPOIS de ver a tabela, e por que: o lado B grava PixelSpacing com 3
# casas (0,977) e o lado A com precisao cheia (0,9765625). A diferenca e 4,4e-4 mm
# — vinte vezes menor que o menor voxel e mil vezes menor que o HD95 de 6,27 mm.
# Sem tolerancia, a comparacao por string diria "DIVERGE" para dois valores
# fisicamente iguais, e o veredito seria do INSTRUMENTO, nao do dado. Isto e
# correcao de instrumento, nao ajuste de resultado: nenhuma medida de acuracia
# depende deste numero, e o valor bruto dos dois lados continua na tabela.
TOL_MM = 1e-3
CAMPOS_NUMERICOS = ("dz_mediano_mm", "SliceThickness", "PixelSpacing",
                    "SpacingBetweenSlices", "KVP", "ReconstructionDiameter")


def _numeros(chave_json: str) -> list[float] | None:
    """Le uma chave da distribuicao como vetor de numeros, ou None se nao for."""
    v = json.loads(chave_json)
    v = v if isinstance(v, list) else [v]
    if not v or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        return None
    return [float(x) for x in v]


def _iguais_com_tolerancia(a: dict[str, int], b: dict[str, int]) -> bool | None:
    """True/False se os dois lados forem comparaveis como numeros; None se nao forem."""
    va = [_numeros(k) for k in a]
    vb = [_numeros(k) for k in b]
    if any(x is None for x in va + vb) or not va or not vb:
        return None
    return all(
        any(len(x) == len(y) and np.allclose(x, y, atol=TOL_MM, rtol=0) for y in vb)
        for x in va
    ) and all(
        any(len(y) == len(x) and np.allclose(y, x, atol=TOL_MM, rtol=0) for x in va)
        for y in vb
    )


def _resumo_campo(linhas: list[dict[str, Any]], campo: str) -> dict[str, Any]:
    """Distribuicao de UM campo num lado. Sem media: sao categorias, nao numeros."""
    cont: dict[str, int] = {}
    for l in linhas:
        chave = json.dumps(l.get(campo, ND), ensure_ascii=False, sort_keys=True)
        cont[chave] = cont.get(chave, 0) + 1
    return {
        "valores": dict(sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))),
        "n_distintos": len(cont),
        "todos_nao_disponiveis": set(cont) == {json.dumps(ND)},
    }


def _token_de_protocolo(valor: Any) -> str | None:
    """Extrai o nome do protocolo de um campo livre do DICOM, ou None.

    Os dois lados guardam o nome do protocolo em TAGS DIFERENTES (o lado A em
    StudyDescription, o lado B em ProtocolName) e com enfeites diferentes
    ("RT^...", "Specials^...", " (Adult)"). Isto tira os enfeites para que a
    comparacao seja entre nomes de protocolo, nao entre formatos de tag.
    """
    if not isinstance(valor, str) or valor == ND:
        return None
    t = valor.split("^")[-1].split(" (")[0].strip().upper()
    return t or None


def cruzar_nomes_de_protocolo(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    """O mesmo NOME de protocolo aparece nos dois lados?

    Um nome de protocolo e uma string interna da instituicao — ela nao viaja
    entre servicos. Um casamento exato e assinatura institucional; a ausencia de
    casamento NAO e prova de instituicao diferente, so falta de evidencia.
    """
    lado_a = {c: t for l in a
              if (t := _token_de_protocolo(l.get("StudyDescription"))) and (c := l["caso"])}
    lado_b = {c: t for l in b
              if (t := _token_de_protocolo(l.get("ProtocolName"))) and (c := l["caso"])}
    sa, sb = set(lado_a.values()), set(lado_b.values())
    exatos = sorted(sa & sb)
    # familia = primeiros dois campos separados por "_" (ex.: RCCTPET_THORAX)
    fam = lambda s: "_".join(s.split("_")[:2])  # noqa: E731
    familias = sorted({fam(x) for x in sa} & {fam(x) for x in sb})
    return {
        "tag_lida_no_lado_A": "StudyDescription",
        "tag_lida_no_lado_B": "ProtocolName",
        "n_com_nome_lado_A": len(lado_a), "n_lado_A": len(a),
        "n_com_nome_lado_B": len(lado_b), "n_lado_B": len(b),
        "nomes_lado_A": sorted(sa), "nomes_lado_B": sorted(sb),
        "casamentos_exatos": exatos,
        "casos_do_casamento_exato": {
            "lado_A": sorted(c for c, t in lado_a.items() if t in set(exatos)),
            "lado_B": sorted(c for c, t in lado_b.items() if t in set(exatos)),
        },
        "familias_em_comum": familias,
        "mencao_literal_a_instituicao": {
            "lado_A": sorted(c for c, t in lado_a.items() if "MAASTRO" in t),
            "lado_B": sorted(c for c, t in lado_b.items() if "MAASTRO" in t),
        },
        "leitura": (
            "casamento exato de nome de protocolo e assinatura INSTITUCIONAL, nao prova "
            "de mesmo protocolo de aquisicao: o nome pode ser o mesmo e os parametros "
            "diferentes. A ausencia de casamento tambem nao prova nada — os dois lados "
            "guardam o nome em tags diferentes e um deles pode ter sido anonimizado."
        ),
    }


def tabela_comparabilidade(raiz_a: Path = RAIZ_LCTSC, raiz_b: Path = RAIZ_NSCLC,
                           saida: Path = SAIDA_FASE10, log=print) -> dict[str, Any]:
    """Parte 1 — a tabela e o veredito sobre 'mesma instituicao = mesmo protocolo?'."""
    a, b = _lado_lctsc(raiz_a), _lado_nsclc(raiz_b)
    campos = ("dz_mediano_mm", *CAMPOS_PROTOCOLO)

    comparacao = {}
    for campo in campos:
        ra, rb = _resumo_campo(a, campo), _resumo_campo(b, campo)
        numerico = (_iguais_com_tolerancia(ra["valores"], rb["valores"])
                    if campo in CAMPOS_NUMERICOS else None)
        if ra["todos_nao_disponiveis"] and rb["todos_nao_disponiveis"]:
            veredito = "nao aplicavel — campo ausente nos dois lados"
        elif ra["todos_nao_disponiveis"] or rb["todos_nao_disponiveis"]:
            veredito = "NAO COMPARAVEL — um dos lados nao tem o campo"
        elif numerico is True:
            veredito = f"mesmos valores nos dois lados (numerico, atol {TOL_MM} mm)"
        elif numerico is False:
            veredito = f"DIVERGE — numerico, acima de atol {TOL_MM} mm"
        elif set(ra["valores"]) == set(rb["valores"]):
            veredito = "mesmos valores nos dois lados"
        elif set(ra["valores"]) & set(rb["valores"]):
            veredito = "sobreposicao parcial"
        else:
            veredito = "DIVERGE — nenhum valor em comum"
        comparacao[campo] = {"lado_A_LCTSC_S1": ra, "lado_B_NSCLC": rb,
                             "comparado_como": "numero" if numerico is not None else "texto",
                             "veredito": veredito}

    divergentes = [c for c, v in comparacao.items() if v["veredito"].startswith("DIVERGE")]
    incomparaveis = [c for c, v in comparacao.items() if v["veredito"].startswith("NAO COMPARAVEL")]
    ausentes = [c for c, v in comparacao.items() if v["veredito"].startswith("nao aplicavel")]

    resultado = {
        "pergunta": "'mesma instituicao' significa 'mesmo protocolo'? Medido, nao presumido.",
        "n_lado_A": len(a), "n_lado_B": len(b),
        "campos_divergentes": divergentes,
        "campos_nao_comparaveis": incomparaveis,
        "campos_ausentes_nos_dois": ausentes,
        # startswith, e nao igualdade: o veredito numerico carrega o sufixo da
        # tolerancia ("... (numerico, atol 0.001 mm)") e uma comparacao exata aqui
        # deixaria de fora justamente os tres campos de geometria.
        "campos_concordantes": [c for c, v in comparacao.items()
                                if v["veredito"].startswith("mesmos valores")],
        "campos_com_sobreposicao_parcial": [c for c, v in comparacao.items()
                                            if v["veredito"].startswith("sobreposicao")],
        "comparacao": comparacao,
        # heterogeneidade INTERNA de cada lado: "quantos valores distintos, sem contar
        # o `nao disponivel`". E o numero que separa "os dois lados diferem" de "um dos
        # lados nao e homogeneo nem consigo mesmo".
        "n_valores_distintos_sem_ND": {
            campo: {
                "lado_A": sum(1 for k in comparacao[campo]["lado_A_LCTSC_S1"]["valores"]
                              if json.loads(k) != ND),
                "lado_B": sum(1 for k in comparacao[campo]["lado_B_NSCLC"]["valores"]
                              if json.loads(k) != ND),
            } for campo in campos
        },
        "nomes_de_protocolo": cruzar_nomes_de_protocolo(a, b),
        "linhas": a + b,
        "limite_declarado": (
            "InstitutionName ausente nao PROVA mesma instituicao nem outra: o campo foi "
            "removido na anonimizacao dos dois lados. A atribuicao MAASTRO vem da fase 9 "
            "(quatro canais independentes) e continua sendo HIPOTESE, nao resultado."
        ),
    }

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "comparabilidade.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    colunas = ["lado", "dataset", "instituicao", "caso", "n_fatias", "dz_mediano_mm",
               "dz_uniforme", *CAMPOS_PROTOCOLO]
    with (saida / "comparabilidade.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for linha in a + b:
            w.writerow({k: (json.dumps(v, ensure_ascii=False)
                            if isinstance(v, (list, dict)) else v)
                        for k, v in linha.items()})
    log(f"tabela: {len(a)} + {len(b)} linhas -> {saida}")
    log(f"  divergem: {divergentes}")
    log(f"  nao comparaveis: {incomparaveis}")
    return resultado


# ============================================== Parte 2 — as duas definicoes


# Citacoes VERBATIM, com URL. O que nao foi achado na fonte fica como ausencia
# declarada — ausencia de documentacao e RESULTADO, nao lacuna a preencher por
# analogia com o outro dataset.
EIXOS = (
    "extensao longitudinal", "inclusao do lumen", "relacao com a parede",
    "proximidade de traqueia e aorta", "inclusao de gordura",
    "comportamento em bifurcacoes", "limite superior", "limite inferior",
    "regra explicita de atlas",
)

DEFINICOES = {
    "preenchido_em": "2026-09-05",
    "metodo": (
        "leitura das paginas de descricao dos dois datasets no TCIA e da publicacao "
        "de referencia de cada um. Verbatim entre aspas, com URL. Nada aqui foi "
        "parafraseado a partir do outro dataset: o que nao esta escrito na fonte de um "
        "lado fica como AUSENTE, nunca preenchido por analogia com o outro."
    ),
    "eixos_comparados": list(EIXOS),

    # ------------------------------------------------------------------ lado A
    "LCTSC": {
        "status": "DOCUMENTADA — atlas nomeado, com limites e janela explicitos",
        "atlas": "RTOG 1106",
        "fontes": [
            {"url": "https://www.cancerimagingarchive.net/collection/lctsc/",
             "doi": "10.7937/K9/TCIA.2017.3r3fvz08",
             "verbatim": {
                 "esofago": (
                     "The esophagus should be contoured from the beginning at the level "
                     "just below the cricoid to its entrance to the stomach at GE junction. "
                     "The esophagus will be contoured using mediastinal window/level on CT "
                     "to correspond to the mucosal, submucosa, and all muscular layers out "
                     "to the fatty adventitia."),
                 "limite_superior": (
                     "The superior-most slice of the esophagus is the slice below the first "
                     "slice where the lamina of the cricoid cartilage is visible (+/- 1 slice)."),
                 "limite_inferior": (
                     "The inferior-most slice of the esophagus is the first slice (+/- 1 slice) "
                     "where the esophagus and stomach are joined, and at least 10 square cm of "
                     "stomach cross section is visible."),
                 "instituicoes": "Data were acquired from 3 institutions (20 each).",
                 "procedencia_do_gt": (
                     "The manual contours that were used in clinic for treatment planning "
                     "were used as ground 'truth.'"),
                 "harmonizacao": (
                     "All contours were reviewed (and edited if necessary) to ensure "
                     "consistency across the 60 patients using the RTOG 1106 contouring atlas."),
             }},
            {"url": "https://doi.org/10.1002/mp.13141",
             "referencia": ("Yang J. et al., Autosegmentation for thoracic radiation treatment "
                            "planning: A grand challenge at AAPM 2017. Med Phys 45:4568-4581, 2018"),
             "texto_integral": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6714977/",
             "verbatim": {
                 "instituicoes": (
                     "Datasets for the grand challenge were made available from three different "
                     "institutions: MD Anderson Cancer Center (MDACC), Memorial Sloan-Kettering "
                     "Cancer Center (MSKCC), and the MAASTRO clinic, with 20 cases from each "
                     "institution."),
                 "limite_da_harmonizacao": (
                     "extensive editing of contouring was undesirable, because interobserver "
                     "variability present in the original contours would be lost"),
             }},
        ],
        "por_eixo": {
            "extensao longitudinal": "cricoide -> juncao gastroesofagica (declarada no atlas)",
            "inclusao do lumen": (
                "implicita: 'mucosal, submucosa, and all muscular layers out to the fatty "
                "adventitia' descreve a PAREDE de fora a fora, o que na pratica de contorno "
                "produz um envelope preenchido. A fase 9 mediu que o GT do LCTSC e MACICO "
                "(fill_holes 2D preencheu 0,0000 mL em 30/30) — medido, nao lido"),
            "relacao com a parede": "camadas mucosa/submucosa/muscular ate a adventicia gordurosa",
            "proximidade de traqueia e aorta": ND,
            "inclusao de gordura": "ate a adventicia gordurosa (o texto para NA adventicia)",
            "comportamento em bifurcacoes": ND,
            "limite superior": "fatia abaixo da primeira em que a lamina da cricoide aparece (+/- 1)",
            "limite inferior": "juncao com o estomago, com >= 10 cm2 de secao gastrica (+/- 1)",
            "regra explicita de atlas": "RTOG 1106, nomeado na fonte",
        },
    },

    # ------------------------------------------------------------------ lado B
    COLECAO_B: {
        "status": (
            "NAO DOCUMENTADA — a fonte declara QUEM contornou e O QUE, e nao declara "
            "NENHUMA regra de como. Isto e resultado desta fase, nao lacuna de busca."
        ),
        "atlas": ND,
        "fontes": [
            {"url": "https://www.cancerimagingarchive.net/collection/nsclc-radiomics/",
             "doi": "10.7937/K9/TCIA.2015.PF0M9REI",
             "verbatim": {
                 "unica_frase_sobre_contorno": (
                     "manual delineation by a radiation oncologist of the 3D volume of the "
                     "primary gross tumor volume (\"GTV-1\") and selected anatomical "
                     "structures (i.e., lung, heart and esophagus)"),
                 "nota_de_versao_3": (
                     "Re-checked and updated the RTSTRUCT files to amend issues in the previous "
                     "submission due to missing RTSTRUCTS or regions of interest that were not "
                     "vertically aligned with the patient image."),
             },
             "ausente_na_fonte": [
                 "atlas ou guideline nomeado", "janela/nivel de visualizacao",
                 "limite superior", "limite inferior", "inclusao ou nao do lumen",
                 "tratamento da gordura periesofagica", "conduta perto de traqueia e aorta",
                 "conduta em bifurcacoes", "numero e formacao dos anotadores",
                 "qualquer procedimento de revisao ou harmonizacao entre casos",
             ]},
            {"url": "https://www.cancerimagingarchive.net/collection/nsclc-radiomics-interobserver1/",
             "papel": ("colecao irma, consultada porque documenta variabilidade entre "
                       "observadores. Documenta a delineacao do GTV-1; NAO documenta orgao "
                       "de risco nem esofago.")},
            {"url": "https://doi.org/10.1038/ncomms5006",
             "referencia": ("Aerts H.J.W.L. et al., Decoding tumour phenotype by noninvasive "
                            "imaging using a quantitative radiomics approach. Nat Commun 5:4006, 2014"),
             "papel": (
                 "publicacao de referencia da colecao. LIMITE DECLARADO: nao foi possivel ler o "
                 "texto integral por esta rota (Nature exige autenticacao; PMC devolveu CAPTCHA), "
                 "entao o conteudo dela sobre contorno fica `nao medido`. Mas ela nao poderia "
                 "documentar os orgaos de risco de qualquer forma: os RTSTRUCT com OAR "
                 "entraram na colecao na versao 3, em 2019/10/23, cinco anos depois do artigo."),
             "status": NM},
        ],
        "por_eixo": {eixo: ND for eixo in EIXOS},
    },

    # ------------------------------------------------------------------ leitura
    "veredito": (
        "A comparacao e ASSIMETRICA por construcao. O lado A tem definicao escrita, com "
        "atlas nomeado, janela e dois limites anatomicos. O lado B tem apenas a existencia "
        "da estrutura. Consequencia direta para a fase inteira: uma diferenca medida entre "
        "os dois lados NAO pode ser atribuida a uma regra de contorno especifica, porque a "
        "regra do lado B nao e conhecida. O par mede DIFERENCA ENTRE DUAS PRATICAS, uma "
        "delas nao especificada — nao mede o efeito de uma convencao nomeada."
    ),
    "ressalva_sobre_o_lado_A": (
        "'Documentada' nao e 'cumprida'. A propria fonte do LCTSC diz que a edicao foi "
        "deliberadamente parcial para nao apagar a variabilidade entre observadores, e a "
        "fase 6 mediu que descritores de ESTILO ainda separam as tres instituicoes "
        "(ICC1 0,5098 e 0,4719, p 0,0005). O atlas foi aplicado como revisao, nao como "
        "redesenho."
    ),
}


def gravar_definicoes(saida: Path = SAIDA_FASE10, log=print) -> dict[str, Any]:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "definicoes.json").write_text(
        json.dumps(DEFINICOES, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"definicoes -> {saida / 'definicoes.json'}")
    return DEFINICOES


# ======================================= Parte 3 — morfologia do GT (sem modelo)

SAIDA_MORFO = SAIDA_FASE10 / "morfologia"

# Traqueia e aorta do LADO A: JA existem, da fase 7, para os MESMOS 30 casos do
# development. Nao sao remedidas aqui — sao lidas.
AUX_LCTSC = RAIZ_LCTSC / "fase7" / "esofago" / "aux_masks"
AUX_NSCLC = RAIZ_NSCLC / "aux_masks"
AUX_ESTRUTURAS = ["trachea", "aorta", "esophagus"]   # a MESMA lista da fase 7

ROI_GT_LCTSC = "Esophagus"
GRUPOS = ("LCTSC-S1", "LCTSC-S2", "LCTSC-S3", "NSCLC")


def gerar_aux(raiz: Path = RAIZ_NSCLC, saida: Path = AUX_NSCLC, log=print) -> dict[str, Any]:
    """Traqueia e aorta do LADO B, pela MESMA chamada que produziu as do lado A.

    Nao e treino: e inferencia do TotalSegmentator 2.18.0 congelado, tarefa
    `total`, sobre o `image.nii.gz` que o dcmrtstruct2nii gravou — a MESMA grade
    do GT, por construcao. Nenhum default do BASELINE_ESOFAGO_V1 e tocado: a
    predicao de esofago que sai aqui NAO entra em metrica nenhuma desta fase,
    ela vem junto so porque estava na lista da fase 7 e trocar a lista trocaria
    o recorte do modelo e, com ele, a traqueia.

    A traqueia e a aorta so servem de REGUA (carina, distancia). Se sairem
    erradas, o caso perde a regua — nao vira caso errado.
    """
    from scripts.clinica.segmentacao import info_segmentacao, rodar_segmentacao

    decl = carregar_declaracao(raiz)
    aq = json.loads((Path(raiz) / "aquisicao.json").read_text(encoding="utf-8"))
    ok = [r for r in aq["casos"] if r["status"] == "ok"]
    exigir_dataset_permitido(COLECAO_B, [r["patient_id"] for r in ok], decl["casos"])

    registros = []
    for r in ok:
        pid = r["patient_id"]
        destino = Path(saida) / pid
        if (destino / "trachea.nii.gz").exists() and (destino / "aorta.nii.gz").exists():
            registros.append({"patient_id": pid, "status": "reusado",
                              "info": info_segmentacao(destino)})
            continue
        try:
            info = rodar_segmentacao(Path(r["caminhos"]["imagem"]), destino,
                                     estruturas=AUX_ESTRUTURAS, log=log)
            registros.append({"patient_id": pid, "status": "ok", "info": info})
        except Exception as e:  # noqa: BLE001 — um caso sem regua nao derruba os 24 outros
            log(f"  {pid}: aux ABORTADO — {type(e).__name__}: {e}")
            registros.append({"patient_id": pid, "status": "abortado",
                              "motivo": f"{type(e).__name__}: {e}"})

    resumo = {"colecao": COLECAO_B, "estruturas": AUX_ESTRUTURAS,
              "n": len(registros),
              "n_ok": sum(1 for x in registros if x["status"] in ("ok", "reusado")),
              "casos": registros}
    Path(saida).mkdir(parents=True, exist_ok=True)
    (Path(saida) / "aux.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"aux: {resumo['n_ok']}/{resumo['n']} com traqueia e aorta -> {saida}")
    return resumo


# --------------------------------------------------- instrumentos de forma
#
# Todos operam SO sobre o GT. Nenhuma predicao entra em nenhum numero desta
# parte — traqueia e aorta entram apenas como REGUA (onde esta a carina, quanto
# de folga o contorno deixou), nunca como referencia de acerto.
#
# VOCABULARIO (fase 9): o GT e MACICO, nao separa parede de lumen. Por isso aqui
# so existem `largura efetiva`, `raio caracteristico`, `meia-espessura do
# envelope preenchido` e `area transversal`. "Espessura de parede" e proibido.


def _largura_efetiva_vetor(m: np.ndarray, zooms) -> tuple[np.ndarray, bool, float]:
    """(vetor de LARGURA EFETIVA em mm, usou_esqueleto, valor de referencia).

    Mesma construcao de espessura.calibre_mm — inclusive o galho de excecao dele
    (esqueleto vazio -> p90 sobre o interior inteiro). O vetor inteiro e preciso
    aqui porque esta fase compara DISTRIBUICOES, e uma mediana nao distingue
    "mais largo em tudo" de "mais largo so nas pontas".

    Nao chama calibre_mm porque as duas contas sao a MESMA EDT + o MESMO
    esqueleto sobre volumes de 512x512x161, e rodar duas vezes dobrava o tempo
    da fase inteira sem mudar um digito. Em vez de confiar nisso, o autoteste
    exige a igualdade numerica com calibre_mm nos DOIS galhos — com esqueleto e
    sem. Se as definicoes se separarem, o teste cai.
    """
    m = np.asarray(m) > 0
    if not m.any():
        return np.empty(0, dtype=float), False, 0.0
    edt = ndimage.distance_transform_edt(m, sampling=np.asarray(zooms, dtype=float))
    esq = skeletonize(m)
    if esq.any():
        v = np.asarray(edt[esq] * 2.0, dtype=float)
        return v, True, float(np.median(v))
    v = np.asarray(edt[m] * 2.0, dtype=float)
    return v, False, float(np.percentile(v, 90))


def largura_por_fatia_mm(m: np.ndarray, zooms) -> tuple[np.ndarray, np.ndarray]:
    """(indices das fatias com GT, diametro do maior disco inscrito em cada uma).

    E a largura efetiva LOCAL, medida no plano da fatia — 2 x max(EDT 2D). Serve
    para "variacao de calibre ao longo de Z", que o vetor 3D nao da porque nele
    a coordenada longitudinal se perde.
    """
    m = np.asarray(m) > 0
    s = np.asarray(zooms[:2], dtype=float)
    z = np.flatnonzero(m.any(axis=(0, 1)))
    larg = np.array([2.0 * float(ndimage.distance_transform_edt(m[:, :, k], sampling=s).max())
                     for k in z], dtype=float)
    return z, larg


def distancia_no_plano_mm(gt: np.ndarray, alvo: np.ndarray, zooms) -> dict[str, Any]:
    """Menor distancia NO PLANO entre o GT e `alvo`, fatia a fatia, em mm.

    No plano, e nao em 3D, por dois motivos: a folga que uma convencao de
    contorno decide e transversal (o anotador decide se encosta na traqueia
    NAQUELA fatia), e a distancia 3D seria dominada pela extensao longitudinal
    da traqueia, que acaba na carina e nao diz nada sobre estilo.

    `folga zero` = a distancia cabe em um voxel do plano (dx): abaixo disso as
    duas mascaras sao vizinhas na grade e a "folga" seria ruido de rasterizacao.
    """
    gt = np.asarray(gt) > 0
    alvo = np.asarray(alvo) > 0
    s = np.asarray(zooms[:2], dtype=float)
    limiar = float(zooms[0])
    dists = []
    for k in np.flatnonzero(gt.any(axis=(0, 1))):
        fa = alvo[:, :, k]
        if not fa.any():
            continue
        d = ndimage.distance_transform_edt(~fa, sampling=s)
        dists.append(float(d[gt[:, :, k]].min()))
    if not dists:
        return {"n_fatias_com_os_dois": 0, "mediana_mm": None, "p25_mm": None,
                "p75_mm": None, "min_mm": None, "frac_fatias_sem_folga": None}
    v = np.asarray(dists, dtype=float)
    return {
        "n_fatias_com_os_dois": int(v.size),
        "mediana_mm": float(np.median(v)),
        "p25_mm": float(np.percentile(v, 25)),
        "p75_mm": float(np.percentile(v, 75)),
        "min_mm": float(v.min()),
        "frac_fatias_sem_folga": float(np.mean(v <= limiar)),
    }


def _recorte_no_plano(m: np.ndarray, margem: int = 16) -> tuple[np.ndarray, tuple]:
    """Recorta a caixa da mascara no plano, com margem. So velocidade, sem efeito.

    A EDT DENTRO da mascara mede a distancia ao fundo mais proximo, que esta na
    propria caixa + 1 voxel; qualquer margem >= 1 devolve valores identicos. A
    margem de 16 voxels (~16 mm) cobre com folga o unico uso que precisa de mais:
    a dilatacao do teto, de poucos milimetros. O autoteste compara recortado
    contra inteiro e exige igualdade.
    """
    m = np.asarray(m) > 0
    if not m.any():
        return m, (slice(None), slice(None), slice(None))
    xs, ys = np.flatnonzero(m.any(axis=(1, 2))), np.flatnonzero(m.any(axis=(0, 2)))
    fat = (slice(max(0, int(xs[0]) - margem), min(m.shape[0], int(xs[-1]) + margem + 1)),
           slice(max(0, int(ys[0]) - margem), min(m.shape[1], int(ys[-1]) + margem + 1)),
           slice(None))
    return m[fat], fat


def offset_no_plano(m: np.ndarray, zooms, t_mm: float) -> np.ndarray:
    """Empurra a fronteira `t_mm` para fora (t>0) ou para dentro (t<0), NO PLANO.

    Conjunto de nivel da EDT, nao dilatacao por elemento estruturante: um
    elemento estruturante em grade anisotropica (0,98 x 0,98 x 3,0 mm) empurraria
    distancias diferentes em cada eixo, e o "1 mm" do resultado nao seria 1 mm.

    So no plano: a diferenca de largura medida e transversal. Empurrar tambem em
    z misturaria convencao de calibre com convencao de extensao — que esta fase
    mede em separado, justamente para nao somar as duas sem perceber.
    """
    m = np.asarray(m) > 0
    if t_mm == 0.0 or not m.any():
        return m.copy()
    s = np.asarray(zooms[:2], dtype=float)
    out = np.zeros_like(m)
    for k in np.flatnonzero(m.any(axis=(0, 1))):
        f = m[:, :, k]
        if t_mm > 0:
            out[:, :, k] = ndimage.distance_transform_edt(~f, sampling=s) <= t_mm
        else:
            out[:, :, k] = ndimage.distance_transform_edt(f, sampling=s) > -t_mm
    return out


def morfologia_do_caso(gt: np.ndarray, zooms, affine: np.ndarray,
                       traqueia: np.ndarray | None = None,
                       aorta: np.ndarray | None = None) -> dict[str, Any]:
    """Todas as medidas da Parte 3 para UM caso, so a partir do GT.

    Cada chave sai marcada como absoluta ou normalizada em MEDIDAS (abaixo). A
    separacao nao e cosmetica: medida absoluta carrega tamanho anatomico junto
    com estilo, medida normalizada por caso divide o tamanho fora.
    """
    gt = np.asarray(gt) > 0
    if not gt.any():
        raise ValueError("GT vazio — caso quebrado, nao caso facil")
    zooms = np.asarray(zooms, dtype=float)
    dx, dy, dz = (float(v) for v in zooms[:3])
    area_voxel = dx * dy
    sinal = rep._sinal_z(affine)

    conta = gt.sum(axis=(0, 1))
    z = np.flatnonzero(conta)
    areas = conta[z] * area_voxel
    area_med = float(np.median(areas))
    volume_mm3 = float(gt.sum()) * dx * dy * dz
    comprimento = float(z.size) * dz

    largura, usou_esq, raio = _largura_efetiva_vetor(gt, zooms)
    _, lfat = largura_por_fatia_mm(gt, zooms)
    l_med_fatia = float(np.median(lfat)) if lfat.size else None

    d: dict[str, Any] = {
        # ---------------- absolutas
        "volume_mL": volume_mm3 / 1000.0,
        "comprimento_z_mm": comprimento,
        "n_fatias_gt": int(z.size),
        "area_mediana_mm2": area_med,
        "area_p5_mm2": float(np.percentile(areas, 5)),
        "area_p95_mm2": float(np.percentile(areas, 95)),
        # O enunciado chama "raio caracteristico" o 2 x EDT no esqueleto. Ele e,
        # geometricamente, a LARGURA EFETIVA cheia; a meia-espessura do envelope
        # preenchido e a metade dele. Sao o MESMO instrumento a menos de um fator
        # 2 — nao duas medidas independentes, e esta linha existe para que
        # ninguem some as duas achando que somou informacao.
        "raio_caracteristico_mm": raio,
        "meia_espessura_envelope_mm": raio / 2.0,
        "volume_por_comprimento_mm2": volume_mm3 / comprimento,
        "largura_efetiva_p5_mm": float(np.percentile(largura, 5)) if largura.size else None,
        "largura_efetiva_p50_mm": float(np.median(largura)) if largura.size else None,
        "largura_efetiva_p95_mm": float(np.percentile(largura, 95)) if largura.size else None,
        "largura_fatia_mediana_mm": l_med_fatia,
        "largura_fatia_iqr_mm": (float(np.percentile(lfat, 75) - np.percentile(lfat, 25))
                                 if lfat.size else None),
        # ---------------- normalizadas pelo proprio caso
        "razao_area_p5": float(np.percentile(areas, 5) / area_med),
        "razao_area_p95": float(np.percentile(areas, 95) / area_med),
        "razao_largura_p5": (float(np.percentile(largura, 5) / np.median(largura))
                             if largura.size else None),
        "razao_largura_p95": (float(np.percentile(largura, 95) / np.median(largura))
                              if largura.size else None),
        "cv_largura_em_z": (float(lfat.std(ddof=1) / l_med_fatia)
                            if lfat.size > 1 and l_med_fatia else None),
        # ---------------- diagnostico do instrumento, nao medida
        "eixo_medial_pelo_esqueleto": bool(usou_esq),
        "n_amostras_eixo_medial": int(largura.size),
    }
    # pontas: JA existe na fase 9, normalizada por caso. Nao remedida aqui.
    d.update(rep.abrupticidade_das_pontas(gt, zooms, sinal))

    # ---------------- regua: carina, traqueia, aorta
    d["carina_disponivel"] = False
    for chave in ("carina_mm_ate_gt_cranial", "carina_mm_ate_gt_caudal",
                  "carina_desvio_mm_max", "dist_traqueia_mediana_mm",
                  "dist_aorta_mediana_mm", "frac_fatias_sem_folga_traqueia",
                  "frac_fatias_sem_folga_aorta"):
        d[chave] = None

    if traqueia is not None and np.asarray(traqueia).any():
        traq = np.asarray(traqueia) > 0
        carina = rep.indice_carina(traq, sinal)
        est = rep.estabilidade_carina(traq, sinal, dz)
        cran, caud = rep._pontas(gt, sinal)
        dt = distancia_no_plano_mm(gt, traq, zooms)
        d.update({
            "carina_disponivel": True,
            "carina_desvio_mm_max": est["desvio_mm_max"],
            "carina_n_componentes_traqueia": est["n_componentes_conexos"],
            "carina_mm_ate_gt_cranial": float((cran - carina) * dz * sinal),
            "carina_mm_ate_gt_caudal": float((caud - carina) * dz * sinal),
            "dist_traqueia_mediana_mm": dt["mediana_mm"],
            "frac_fatias_sem_folga_traqueia": dt["frac_fatias_sem_folga"],
            "_dist_traqueia": dt,
        })
    if aorta is not None and np.asarray(aorta).any():
        da = distancia_no_plano_mm(gt, np.asarray(aorta) > 0, zooms)
        d.update({"dist_aorta_mediana_mm": da["mediana_mm"],
                  "frac_fatias_sem_folga_aorta": da["frac_fatias_sem_folga"],
                  "_dist_aorta": da})

    d["_largura_efetiva"] = largura            # distribuicao inteira, para a Parte 5
    d["_largura_por_fatia"] = lfat
    d["_areas_por_fatia"] = areas
    return d


# (chave, unidade, escala). `escala` decide a leitura: absoluta carrega tamanho
# anatomico + estilo; normalizada por caso divide o tamanho fora e deixa o
# estilo. A tabela e a fonte da marcacao — nenhuma linha de relatorio inventa a
# sua.
MEDIDAS: tuple[tuple[str, str, str], ...] = (
    ("volume_mL", "mL", "absoluta"),
    ("comprimento_z_mm", "mm", "absoluta"),
    # em VOXELS: mistura extensao com dz. Entre S1 e NSCLC (dz 3,0 mm nos dois) e
    # comparavel; contra o S2 (dz 2,5 mm) NAO e, e uma diferenca ai pode ser so a
    # grade. `comprimento_z_mm` e a versao fisica da mesma coisa.
    ("n_fatias_gt", "fatias (depende do dz)", "absoluta"),
    ("area_mediana_mm2", "mm2", "absoluta"),
    ("area_p5_mm2", "mm2", "absoluta"),
    ("area_p95_mm2", "mm2", "absoluta"),
    ("raio_caracteristico_mm", "mm", "absoluta"),
    ("meia_espessura_envelope_mm", "mm", "absoluta"),
    ("volume_por_comprimento_mm2", "mm2", "absoluta"),
    ("largura_efetiva_p5_mm", "mm", "absoluta"),
    ("largura_efetiva_p50_mm", "mm", "absoluta"),
    ("largura_efetiva_p95_mm", "mm", "absoluta"),
    ("largura_fatia_mediana_mm", "mm", "absoluta"),
    ("largura_fatia_iqr_mm", "mm", "absoluta"),
    ("area_ponta_cranial_mm2", "mm2", "absoluta"),
    ("area_ponta_caudal_mm2", "mm2", "absoluta"),
    ("carina_mm_ate_gt_cranial", "mm", "absoluta"),
    ("carina_mm_ate_gt_caudal", "mm", "absoluta"),
    ("dist_traqueia_mediana_mm", "mm", "absoluta"),
    ("dist_aorta_mediana_mm", "mm", "absoluta"),
    ("razao_area_p5", "adimensional", "normalizada"),
    ("razao_area_p95", "adimensional", "normalizada"),
    ("razao_largura_p5", "adimensional", "normalizada"),
    ("razao_largura_p95", "adimensional", "normalizada"),
    ("cv_largura_em_z", "adimensional", "normalizada"),
    ("razao_ponta_cranial", "adimensional", "normalizada"),
    ("razao_ponta_caudal", "adimensional", "normalizada"),
    ("frac_fatias_sem_folga_traqueia", "fracao", "normalizada"),
    ("frac_fatias_sem_folga_aorta", "fracao", "normalizada"),
)
ESCALA_DA_MEDIDA = {k: e for k, _, e in MEDIDAS}
UNIDADE_DA_MEDIDA = {k: u for k, u, _ in MEDIDAS}


def _grupo_de(caso: str, dataset: str) -> str:
    return "NSCLC" if dataset == COLECAO_B else f"LCTSC-{fase5.instituicao_de(caso)}"


def medir_grupos(raiz_a: Path = RAIZ_LCTSC, raiz_b: Path = RAIZ_NSCLC,
                 aux_a: Path = AUX_LCTSC, aux_b: Path = AUX_NSCLC,
                 log=print) -> list[dict[str, Any]]:
    """Parte 3 — uma linha por caso, nos quatro grupos. Passa pelas guardas."""
    import nibabel as nib

    split = fase5.carregar_split(raiz_a)
    casos_a = sorted(split["development"])
    exigir_dataset_permitido("LCTSC", casos_a)
    exigir_apenas_development(casos_a, split)          # test e validation ficam fora
    exigir_sem_repeticao(casos_a, "LCTSC/development")

    decl = carregar_declaracao(raiz_b)
    aq = json.loads((Path(raiz_b) / "aquisicao.json").read_text(encoding="utf-8"))
    casos_b = [r["patient_id"] for r in aq["casos"] if r["status"] == "ok"]
    exigir_dataset_permitido(COLECAO_B, casos_b, decl["casos"])
    exigir_sem_repeticao(casos_b, f"{COLECAO_B}/adquiridos")

    alvos: list[tuple[str, str, Path, Path, Path]] = [
        *((c, "LCTSC", Path(raiz_a) / c / "gt" / f"mask_{ROI_GT_LCTSC}.nii.gz",
           Path(raiz_a) / c / "gt" / rtst.NOME_IMAGEM, Path(aux_a) / c) for c in casos_a),
        *((r["patient_id"], COLECAO_B, Path(r["caminhos"]["mascara"]),
           Path(r["caminhos"]["imagem"]), Path(aux_b) / r["patient_id"])
          for r in aq["casos"] if r["status"] == "ok"),
    ]

    linhas = []
    for caso, dataset, p_gt, p_img, p_aux in alvos:
        img = nib.load(str(p_gt))
        gt = np.asarray(img.dataobj) > 0.5
        zooms = np.asarray(img.header.get_zooms()[:3], dtype=float)
        # `z_uniforme` aqui e do NIfTI, que e regular por construcao; a
        # irregularidade que houver esta no DICOM e ja foi registrada em
        # aquisicao.json/grades_regularizadas (LUNG1-021, 0,51% em z).
        exigir_spacing_presente({"pixel_spacing_mm": [zooms[0], zooms[1]],
                                 "espacamento_z_mediano_mm": float(zooms[2]),
                                 "espacamento_z_uniforme": True}, f"{caso}/GT")
        exigir_affine_compativel(p_img, p_gt)
        # contra a grade da IMAGEM, nao contra a propria: tambem recusa GT vazio
        exigir_mascara_na_grade(gt, nib.load(str(p_img)).shape, f"{caso}/GT")

        aux = {}
        for nome in ("trachea", "aorta"):
            p = p_aux / f"{nome}.nii.gz"
            if not p.exists():
                aux[nome] = None
                continue
            exigir_affine_compativel(p_gt, p)     # a regua tem que estar NA MESMA grade
            aux[nome] = np.asarray(nib.load(str(p)).dataobj) > 0.5

        linha = {"caso": caso, "dataset": dataset, "grupo": _grupo_de(caso, dataset)}
        linha.update(morfologia_do_caso(gt, zooms, img.affine, aux["trachea"], aux["aorta"]))
        linha["traqueia_disponivel"] = aux["trachea"] is not None
        linha["aorta_disponivel"] = aux["aorta"] is not None
        linhas.append(linha)
        log(f"  {linha['grupo']:9s} {caso:20s} vol {linha['volume_mL']:6.2f} mL · "
            f"largura {linha['raio_caracteristico_mm']:5.2f} mm · "
            f"comp {linha['comprimento_z_mm']:6.1f} mm")
    return linhas


# ============================================ Parte 4 — os quatro grupos

def _valores(linhas, grupo: str, chave: str) -> np.ndarray:
    v = [l.get(chave) for l in linhas if l["grupo"] == grupo]
    return np.asarray([x for x in v if x is not None and np.isfinite(x)], dtype=float)


def comparar_quatro_grupos(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """Parte 4 — distribuicao por grupo e Kruskal-Wallis (nao-parametrico) entre os quatro.

    Kruskal-Wallis e nao a ANOVA porque n=10 por grupo do LCTSC nao permite
    verificar normalidade nem confiar no TLC. E ele responde so "algum grupo
    difere?"; QUAL par difere e a Parte 5, e so para o par que a fase declarou
    antes de medir (S1 x NSCLC).
    """
    saida = {}
    for chave, unidade, escala in MEDIDAS:
        por_grupo = {g: _valores(linhas, g, chave) for g in GRUPOS}
        cheios = [v for v in por_grupo.values() if v.size >= 2]
        if len(cheios) >= 2:
            h, p = stats.kruskal(*cheios)
            kw = {"H": float(h), "p": float(p), "n_grupos_usados": len(cheios)}
        else:
            kw = {"H": NA, "p": NA, "n_grupos_usados": len(cheios),
                  "motivo": "menos de dois grupos com n>=2"}
        saida[chave] = {
            "unidade": unidade,
            "escala": escala,
            "por_grupo": {g: rep._dist(v) for g, v in por_grupo.items()},
            "kruskal_wallis": kw,
        }
    # Esta parte roda ~30 Kruskal-Wallis na MESMA amostra e publicava so {H, p}.
    # As Partes 5, 6 e 7 corrigem multiplicidade; nao corrigir aqui era rigor
    # assimetrico — e a assimetria pesava a favor de achar diferenca de estilo.
    saida["multiplicidade"] = _bh_kruskal(saida)
    return saida


# ==================================== Parte 5 — o experimento central (S1 x B)

# Semente fixa para bootstrap, permutacao e simulacao de poder. Declarada aqui
# para que o intervalo de confianca publicado seja reproduzivel numero a numero.
SEMENTE_ESTATISTICA = 20260905
N_BOOTSTRAP = 10000
N_PERMUTACAO = 20000
N_SIM_PODER = 2000
ALFA = 0.05
PODER_ALVO = 0.80


def cliff_delta(a, b) -> float:
    """Tamanho de efeito nao-parametrico: P(A>B) - P(A<B), em [-1, +1].

    Nao e o p: nao depende de n. |delta| 0,147 / 0,33 / 0,474 sao os cortes
    usuais de pequeno/medio/grande, e estao citados como convencao de leitura,
    nao como lei.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return float("nan")
    dif = a[:, None] - b[None, :]
    return float((np.count_nonzero(dif > 0) - np.count_nonzero(dif < 0)) / dif.size)


def _rotulo_cliff(d: float) -> str:
    m = abs(d)
    if not np.isfinite(m):
        return NA
    return ("desprezivel" if m < 0.147 else "pequeno" if m < 0.33
            else "medio" if m < 0.474 else "grande")


def _ic_bootstrap(a, b, estat, n=N_BOOTSTRAP, alfa=ALFA,
                  semente=SEMENTE_ESTATISTICA) -> dict[str, Any]:
    """IC percentil por reamostragem independente dos dois grupos.

    Percentil, e nao BCa: com n=10 de um lado, a correcao de vies do BCa se apoia
    em jackknife de 10 pontos e nao e mais confiavel que o percentil. A escolha
    esta declarada, e alarga o intervalo em vez de estreitar.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 2 or b.size < 2:
        return {"ic95": NA, "motivo": "n < 2 em um dos grupos"}
    rng = np.random.default_rng(semente)
    ia = rng.integers(0, a.size, size=(n, a.size))
    ib = rng.integers(0, b.size, size=(n, b.size))
    vals = np.array([estat(a[ia[i]], b[ib[i]]) for i in range(n)], dtype=float)
    vals = vals[np.isfinite(vals)]
    return {"ic95": [float(np.percentile(vals, 100 * alfa / 2)),
                     float(np.percentile(vals, 100 * (1 - alfa / 2)))],
            "n_reamostragens": int(vals.size)}


def _p_permutacao(a, b, n=N_PERMUTACAO, semente=SEMENTE_ESTATISTICA) -> float:
    """p bilateral por permutacao da diferenca de MEDIANAS.

    (k+1)/(n+1) e nao k/n: um p exatamente zero seria uma afirmacao que 20000
    permutacoes nao sustentam.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 2 or b.size < 2:
        return float("nan")
    obs = abs(float(np.median(a) - np.median(b)))
    junto = np.concatenate([a, b])
    rng = np.random.default_rng(semente)
    idx = np.argsort(rng.random((n, junto.size)), axis=1)
    emb = junto[idx]
    dif = np.abs(np.median(emb[:, :a.size], axis=1) - np.median(emb[:, a.size:], axis=1))
    return float((np.count_nonzero(dif >= obs - 1e-12) + 1) / (n + 1))


def efeito_minimo_detectavel(a, b, n_a: int, n_b: int, n_sim=N_SIM_PODER,
                             alfa=ALFA, poder=PODER_ALVO,
                             semente=SEMENTE_ESTATISTICA) -> dict[str, Any]:
    """Menor deslocamento, na unidade da medida, que ESTE n consegue detectar.

    Monte Carlo sobre a distribuicao empirica COMBINADA (a hipotese nula usa a
    forma que o dado tem, sem supor normalidade nem variancia igual): sorteia
    n_a de H0 e n_b de H0 + s, roda Mann-Whitney bilateral, conta rejeicoes.
    Varre s ate o poder passar de `poder`.

    Existe para que "p alto" nunca seja lido como "nao ha diferenca": com 10
    contra 25, o que o desenho NAO enxerga tem tamanho, e o tamanho esta aqui.
    """
    pool = np.concatenate([np.asarray(a, float), np.asarray(b, float)])
    if pool.size < 4:
        return {"mde": NA, "motivo": "amostra combinada menor que 4"}
    escala = float(np.percentile(pool, 75) - np.percentile(pool, 25)) or float(pool.std())
    if not np.isfinite(escala) or escala <= 0:
        return {"mde": NA, "motivo": "dispersao nula na amostra combinada"}
    rng = np.random.default_rng(semente)
    curva = []
    for k in range(1, 41):
        s = escala * k * 0.1
        xa = rng.choice(pool, size=(n_sim, n_a), replace=True)
        xb = rng.choice(pool, size=(n_sim, n_b), replace=True) + s
        p = stats.mannwhitneyu(xa, xb, axis=1, alternative="two-sided").pvalue
        pot = float(np.mean(p < alfa))
        # magnitude: o sinal aqui so diria "o grupo deslocado esta acima", que e
        # como a simulacao foi montada, e nao um achado
        d = abs(cliff_delta(pool, pool + s))
        curva.append({"deslocamento": float(s), "poder": pot, "cliff_delta_implicado": d})
        if pot >= poder:
            return {"mde": float(s), "poder_no_mde": pot, "cliff_delta_no_mde": d,
                    "alfa": alfa, "poder_alvo": poder, "n_a": n_a, "n_b": n_b,
                    "escala_usada_iqr": escala, "curva": curva}
    return {"mde": NM, "motivo": f"poder {poder} nao alcancado ate 4x o IQR combinado",
            "alfa": alfa, "n_a": n_a, "n_b": n_b, "curva": curva}


def corrigir_multiplicidade(por_medida: dict[str, Any], alfa=ALFA) -> dict[str, Any]:
    """Benjamini-Hochberg sobre TODAS as medidas testadas de uma vez.

    Existe porque a Parte 5 roda ~30 testes na mesma amostra: a alfa 0,05,
    um ou dois p abaixo de 0,05 sao o que se espera do ACASO, e publicar o menor
    deles como achado seria escolher o vencedor de uma loteria que a propria
    fase montou. BH controla a taxa de falsa descoberta e nao a familiar, que e
    a escolha certa para uma bateria exploratoria — mas a escolha esta declarada.

    As medidas nao sao independentes (largura efetiva p50 e raio caracteristico
    sao a mesma coisa, area e volume andam juntos), e BH sob dependencia positiva
    continua valido; sob dependencia arbitraria, seria preciso o BY, mais
    conservador. Fica registrado como premissa, nao como fato.
    """
    chaves = [k for k, v in por_medida.items() if isinstance(v.get("p_mann_whitney"), float)]
    if not chaves:
        return {"veredito": NA, "motivo": "nenhum p valido"}
    ps = np.array([por_medida[k]["p_mann_whitney"] for k in chaves], dtype=float)
    ajust = stats.false_discovery_control(ps, method="bh")
    for k, pa in zip(chaves, ajust):
        por_medida[k]["p_mann_whitney_bh"] = float(pa)
        por_medida[k]["sobrevive_a_bh"] = bool(pa < alfa)
    brutos = [k for k, p in zip(chaves, ps) if p < alfa]
    return {
        "metodo": "Benjamini-Hochberg (FDR), sobre os p bilaterais de Mann-Whitney",
        "n_medidas_testadas": len(chaves),
        "alfa": alfa,
        "n_p_brutos_abaixo_de_alfa": len(brutos),
        "medidas_com_p_bruto_abaixo_de_alfa": brutos,
        "esperado_por_acaso": float(alfa * len(chaves)),
        "n_sobreviventes_bh": int(np.count_nonzero(ajust < alfa)),
        "medidas_sobreviventes_bh": [k for k, pa in zip(chaves, ajust) if pa < alfa],
        "premissa": ("BH assume independencia ou dependencia positiva; varias medidas aqui "
                     "sao redundantes por construcao (largura_efetiva_p50 e "
                     "raio_caracteristico_mm sao o MESMO numero; meia_espessura e a metade "
                     "dele). Isso torna o teste efetivo menor que a contagem, e a correcao, "
                     "conservadora."),
    }


def _bh_kruskal(saida: dict[str, Any], alfa=ALFA) -> dict[str, Any]:
    """Benjamini-Hochberg sobre os p de Kruskal-Wallis da Parte 4.

    Separado de `corrigir_multiplicidade` so porque a chave do p e outra
    (`kruskal_wallis.p` contra `p_mann_whitney`); a familia e a mesma ideia e
    as mesmas premissas de dependencia valem — ver o docstring de la.
    """
    chaves = [k for k, v in saida.items()
              if isinstance(v, dict) and isinstance(v.get("kruskal_wallis", {}).get("p"), float)]
    if not chaves:
        return {"veredito": NA, "motivo": "nenhum p de KW valido"}
    ps = np.array([saida[k]["kruskal_wallis"]["p"] for k in chaves], dtype=float)
    ajust = stats.false_discovery_control(ps, method="bh")
    for k, pa in zip(chaves, ajust):
        saida[k]["kruskal_wallis"]["p_bh"] = float(pa)
        saida[k]["kruskal_wallis"]["sobrevive_a_bh"] = bool(pa < alfa)
    return {
        "metodo": "Benjamini-Hochberg (FDR) sobre os p bilaterais de Kruskal-Wallis",
        "n_medidas_testadas": len(chaves),
        "alfa": alfa,
        "esperado_por_acaso": float(alfa * len(chaves)),
        "n_p_brutos_abaixo_de_alfa": int(np.count_nonzero(ps < alfa)),
        "n_sobreviventes_bh": int(np.count_nonzero(ajust < alfa)),
        "medidas_sobreviventes_bh": [k for k, pa in zip(chaves, ajust) if pa < alfa],
        "leitura": ("KW responde 'algum grupo difere', nao QUAL. Sobreviver ao BH aqui NAO "
                    "identifica o par, e uma medida em VOXELS (n_fatias_gt) ou em escala "
                    "ABSOLUTA sobrevive por grade e por tamanho, nao por estilo — conferir "
                    "a coluna `escala` antes de ler qualquer sobrevivente como achado."),
    }



def comparar_par(a, b, n_a_rotulo="LCTSC-S1", n_b_rotulo="NSCLC") -> dict[str, Any]:
    """Um par de distribuicoes, com tudo que a fase exige — e sem concluir por p."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 2 or b.size < 2:
        return {"veredito": NA, "motivo": f"n insuficiente ({a.size} x {b.size})"}
    ma, mb = float(np.median(a)), float(np.median(b))
    dif = mb - ma
    u, p_mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    d = cliff_delta(b, a)     # positivo = lado B (NSCLC) acima do lado A (S1)
    poder = efeito_minimo_detectavel(a, b, int(a.size), int(b.size))
    # Efeito observado MENOR que o minimo detectavel e p abaixo de alfa e o
    # regime classico de erro de MAGNITUDE: o desenho so enxerga essa diferenca
    # quando a amostra cai do lado sortudo, entao a magnitude publicada esta
    # provavelmente inflada. Nao invalida o sinal — obriga a le-lo como direcao,
    # nao como tamanho.
    abaixo = (isinstance(poder.get("mde"), float) and abs(dif) < poder["mde"])
    return {
        "grupo_A": n_a_rotulo, "grupo_B": n_b_rotulo,
        "n_A": int(a.size), "n_B": int(b.size),
        "mediana_A": ma, "mediana_B": mb,
        "diferenca_de_mediana_B_menos_A": dif,
        "diferenca_pct_sobre_A": (float(100.0 * dif / ma) if ma else NA),
        "ic95_diferenca_de_mediana": _ic_bootstrap(
            b, a, lambda x, y: float(np.median(x) - np.median(y)))["ic95"],
        "mann_whitney_U": float(u), "p_mann_whitney": float(p_mw),
        "p_permutacao_da_mediana": _p_permutacao(a, b),
        "cliff_delta_B_vs_A": d,
        "cliff_delta_rotulo": _rotulo_cliff(d),
        "ic95_cliff_delta": _ic_bootstrap(b, a, cliff_delta)["ic95"],
        "poder": poder,
        "efeito_observado_abaixo_do_mde": bool(abaixo),
        "ressalva_de_magnitude": (
            "diferenca observada MENOR que o efeito minimo detectavel deste desenho: "
            "se ela ainda assim passar em alfa, a magnitude publicada tende a estar "
            "inflada — leia como direcao, nao como tamanho." if abaixo else NA),
        "distribuicao_A": [float(x) for x in np.sort(a)],
        "distribuicao_B": [float(x) for x in np.sort(b)],
    }


# ------------------- a traducao para a unidade do erro do baseline

def teto_de_dice_por_largura(gt: np.ndarray, zooms, delta_largura_mm: float) -> dict[str, Any]:
    """Dice do MESMO GT contra ele mesmo com a largura mudada em `delta` mm.

    E a unica traducao honesta de "X mm de estilo" para a unidade do baseline
    SEM par de casos: os dois lados sao estruturas de casos diferentes, entao
    nao existe "o mesmo esofago contornado nos dois estilos". O que existe e:
    pegar a anatomia REAL de um lado e aplicar nela, e so nela, a diferenca
    MEDIDA de largura. O numero responde "se dois anotadores concordassem em
    tudo menos na largura, e divergissem exatamente o que os dois datasets
    divergem, que Dice eles teriam entre si?".

    O offset e radial (dois lados), entao a largura muda 2t — mas o `delta`
    ALCANCADO e MEDIDO na saida, nunca suposto: em grade de 0,98 mm, uma
    estrutura de 3 fatias nao aceita meio milimetro sem quantizar.
    """
    gt, _ = _recorte_no_plano(np.asarray(gt) > 0)   # so velocidade; ver docstring
    t = float(delta_largura_mm) / 2.0
    m2 = offset_no_plano(gt, zooms, t)
    l0 = _largura_efetiva_vetor(gt, zooms)[2]
    l1 = _largura_efetiva_vetor(m2, zooms)[2] if m2.any() else 0.0
    voxel = float(np.prod(np.asarray(zooms[:3], dtype=float)))
    return {
        "delta_largura_alvo_mm": float(delta_largura_mm),
        "offset_radial_mm": t,
        "delta_largura_alcancado_mm": l1 - l0,
        "largura_original_mm": l0, "largura_deslocada_mm": l1,
        "dice": sm.dice(m2, gt),
        "volume_original_mL": float(gt.sum()) * voxel / 1000.0,
        "volume_deslocado_mL": float(m2.sum()) * voxel / 1000.0,
    }


def teto_de_dice_por_extensao(gt: np.ndarray, zooms, affine, corte_cranial_mm: float,
                              corte_caudal_mm: float) -> dict[str, Any]:
    """Dice do MESMO GT contra ele mesmo aparado nas pontas pelos mm medidos.

    Apara so o que da para aparar: um corte NEGATIVO significaria ESTENDER o
    contorno para fora do que alguem desenhou, e isso seria inventar fronteira.
    Esse lado sai como `nao aplicavel`, com o valor pedido registrado.
    """
    gt = np.asarray(gt) > 0
    dz = float(np.asarray(zooms)[2])
    sinal = rep._sinal_z(np.asarray(affine))
    cran, caud = rep._pontas(gt, sinal)
    nc = int(round(max(0.0, corte_cranial_mm) / dz))
    nd = int(round(max(0.0, corte_caudal_mm) / dz))
    m2 = gt.copy()
    for i in range(nc):
        k = cran - i * int(sinal)
        if 0 <= k < gt.shape[2]:
            m2[:, :, k] = False
    for i in range(nd):
        k = caud + i * int(sinal)
        if 0 <= k < gt.shape[2]:
            m2[:, :, k] = False
    return {
        "corte_cranial_pedido_mm": float(corte_cranial_mm),
        "corte_caudal_pedido_mm": float(corte_caudal_mm),
        "corte_cranial_aplicado_mm": nc * dz,
        "corte_caudal_aplicado_mm": nd * dz,
        "cranial_nao_aplicavel": corte_cranial_mm < 0,
        "caudal_nao_aplicavel": corte_caudal_mm < 0,
        "dice": sm.dice(m2, gt),
        "n_fatias_removidas": int(nc + nd),
    }

# O numero congelado do BASELINE_ESOFAGO_V1 no LCTSC development (n=30). Esta
# aqui SO como regua de comparacao — nada nesta fase o recalcula ou o altera.
BASELINE_DICE_MEDIANO = 0.7880
BASELINE_HD95_MEDIANO_MM = 6.27

# A medida que vira "mm de estilo". Declarada aqui, antes de rodar: e a largura
# efetiva mediana (2 x EDT no eixo medial), porque e a unica medida absoluta que
# (a) esta em mm, (b) e transversal e (c) tem um caminho geometrico direto para
# Dice via deslocamento de fronteira.
MEDIDA_DO_TETO = "raio_caracteristico_mm"


def teto_do_estilo(linhas: list[dict[str, Any]], par: dict[str, Any],
                   raiz_a: Path = RAIZ_LCTSC, raiz_b: Path = RAIZ_NSCLC,
                   log=print) -> dict[str, Any]:
    """Traduz a diferenca de estilo medida para a MESMA unidade do erro do baseline.

    NAO HA PAR DIRETO. Os 10 casos do lado A e os 25 do lado B sao estruturas de
    casos diferentes: ninguem contornou a mesma estrutura nos dois estilos, e
    nenhum registro (rigido ou nao) criaria esse par sem inventar
    correspondencia anatomica que o dado nao tem. Entao o Dice do teto NAO e
    medido entre os dois lados — ele e CONSTRUIDO, caso a caso, aplicando a
    diferenca MEDIDA sobre a anatomia REAL de cada caso e comparando o caso
    consigo mesmo.

    O que isso responde: "se dois anotadores concordassem em tudo menos na
    largura (e na extensao), e divergissem exatamente o que os dois datasets
    divergem, que Dice teriam entre si?". Isso e um TETO: acima dele nenhum
    modelo pode chegar contra o outro estilo, por mais perfeito que seja.

    O que isso NAO responde: quanto do erro do baseline VEM de estilo. Teto e
    limite superior de concordancia, nao decomposicao de erro — e a comparacao
    com 0,7880 e de ordem de grandeza, nao de contabilidade.
    """
    import nibabel as nib

    p_larg = par["por_medida"].get(MEDIDA_DO_TETO, {})
    if not isinstance(p_larg.get("diferenca_de_mediana_B_menos_A"), float):
        return {"veredito": NA, "motivo": f"{MEDIDA_DO_TETO} sem comparacao valida"}
    delta_larg = float(p_larg["diferenca_de_mediana_B_menos_A"])
    ic_larg = p_larg.get("ic95_diferenca_de_mediana")

    # TRES deltas, e nao um. O pontual sozinho responderia so "o teto da diferenca
    # que medimos"; se essa diferenca sair abaixo do voxel, o teto vira 1,0000 por
    # construcao e nao informa nada. Os outros dois respondem a pergunta que
    # sobra: "qual e o teto da MAIOR diferenca que este dado ainda permite?".
    #   ic95_superior — a borda do intervalo de confianca da propria diferenca;
    #   mde           — o menor efeito que 10 x 25 casos conseguiriam detectar:
    #                   acima dele, o desenho teria visto.
    deltas = {"pontual": delta_larg}
    if isinstance(ic_larg, list) and len(ic_larg) == 2:
        deltas["ic95_superior"] = float(max(abs(ic_larg[0]), abs(ic_larg[1])))
    mde = p_larg.get("poder", {}).get("mde")
    if isinstance(mde, float):
        deltas["mde"] = float(mde)
    # Quarto cenario, por caso: o MENOR deslocamento que a grade consegue
    # DESENHAR — um voxel no plano de cada lado, ou seja 2 x dx de largura.
    # Abaixo disso o conjunto de nivel nao encosta em nenhum voxel novo e o Dice
    # volta 1,0000 nao porque os estilos concordem, mas porque a grade nao sabe
    # escrever a diferenca. Ele e o TETO CONSERVADOR: se a diferenca real e menor
    # que um voxel, o custo dela em Dice e menor que este.
    DELTA_UM_VOXEL = "um_voxel_no_plano"

    p_cran = par["por_medida"].get("carina_mm_ate_gt_cranial", {})
    p_caud = par["por_medida"].get("carina_mm_ate_gt_caudal", {})
    d_cran = p_cran.get("diferenca_de_mediana_B_menos_A")
    d_caud = p_caud.get("diferenca_de_mediana_B_menos_A")

    aq = json.loads((Path(raiz_b) / "aquisicao.json").read_text(encoding="utf-8"))
    caminho_b = {r["patient_id"]: Path(r["caminhos"]["mascara"])
                 for r in aq["casos"] if r["status"] == "ok"}

    por_caso = []
    for l in linhas:
        if l["grupo"] not in ("LCTSC-S1", "NSCLC"):
            continue
        p_gt = (caminho_b[l["caso"]] if l["grupo"] == "NSCLC"
                else Path(raiz_a) / l["caso"] / "gt" / f"mask_{ROI_GT_LCTSC}.nii.gz")
        img = nib.load(str(p_gt))
        gt = np.asarray(img.dataobj) > 0.5
        zooms = np.asarray(img.header.get_zooms()[:3], dtype=float)
        # Sinal: no lado A, o contorno teria que ficar MAIS LARGO em `delta` para
        # virar estilo B; no lado B, mais estreito na mesma medida. Os dois lados
        # entram para que o teto nao dependa de qual anatomia foi escolhida.
        sinal = +1.0 if l["grupo"] == "LCTSC-S1" else -1.0
        deltas_caso = {**deltas, DELTA_UM_VOXEL: 2.0 * float(zooms[0])}
        r = {"caso": l["caso"], "grupo": l["grupo"],
             "largura": {nome: teto_de_dice_por_largura(gt, zooms, sinal * dl)
                         for nome, dl in deltas_caso.items()}}
        if isinstance(d_cran, float) and isinstance(d_caud, float):
            # Aparar so quem esta SOBRANDO. Estender e impossivel: nao existe
            # contorno alem do que alguem desenhou.
            if l["grupo"] == "NSCLC":
                cc, cd = max(0.0, d_cran), max(0.0, -d_caud)
            else:
                cc, cd = max(0.0, -d_cran), max(0.0, d_caud)
            r["extensao"] = teto_de_dice_por_extensao(gt, zooms, img.affine, cc, cd)
            # combinado: as DUAS diferencas na mesma estrutura, de uma vez. Em
            # dois cenarios — o delta PONTUAL, que e o que o dado mediu, e o de
            # UM VOXEL, que e o pior caso ainda compativel com o dado (a
            # diferenca real de largura e menor que um voxel).
            r["combinado_dice"] = {
                nome: sm.dice(_aparar(offset_no_plano(gt, zooms, sinal * dl / 2.0),
                                      zooms, img.affine, cc, cd), gt)
                for nome, dl in (("pontual", delta_larg),
                                 (DELTA_UM_VOXEL, 2.0 * float(zooms[0])))}
        por_caso.append(r)
        log(f"  teto {l['grupo']:9s} {l['caso']:20s} dice_largura " + " · ".join(
            f"{n} {r['largura'][n]['dice']:.4f}" for n in deltas_caso))

    def _res(sel):
        v = [x for x in sel if x is not None and np.isfinite(x)]
        return rep._dist(v) if v else {"n": 0, "mediana": NA}

    def _por_grupo(f):
        return {g: _res([f(r) for r in por_caso if r["grupo"] == g])
                for g in ("LCTSC-S1", "NSCLC")}

    # A extensao so e simulavel no lado que SOBRA: no outro, virar o estilo do
    # vizinho exigiria ESTENDER o contorno, e nenhum Dice honesto sai disso. Os
    # casos sem apara ficam de fora da agregacao em vez de entrar como 1,0000 —
    # entrariam como concordancia perfeita que ninguem mediu.
    aparados = [r for r in por_caso if r.get("extensao", {}).get("n_fatias_removidas", 0) > 0]
    dices_ext = [r["extensao"]["dice"] for r in aparados]
    nomes = list(por_caso[0]["largura"]) if por_caso else list(deltas)
    med_larg = {n: _res([r["largura"][n]["dice"] for r in por_caso]) for n in nomes}
    # MAGNITUDE nos pedidos: o sinal so diz de que lado do par o caso veio (o S1
    # e alargado, o NSCLC estreitado, para chegar no estilo do outro).
    alcancado = {n: rep._dist([abs(r["largura"][n]["delta_largura_alcancado_mm"])
                               for r in por_caso]) for n in nomes}
    pedido = {n: rep._dist([abs(r["largura"][n]["delta_largura_alvo_mm"]) for r in por_caso])
              for n in nomes}
    piso = pedido[DELTA_UM_VOXEL]
    dice_piso = med_larg[DELTA_UM_VOXEL]
    nomes_comb = list(aparados[0]["combinado_dice"]) if aparados else []
    dices_comb = {n: _res([r["combinado_dice"][n] for r in aparados]) for n in nomes_comb}
    return {
        "pergunta": ("qual Dice um contorno PERFEITO de um estilo teria contra o outro, "
                     "dada a diferenca MEDIDA entre os dois?"),
        "medida_traduzida": MEDIDA_DO_TETO,
        "delta_largura_mm": delta_larg,
        "delta_largura_ic95_mm": ic_larg,
        "delta_largura_pct": p_larg.get("diferenca_pct_sobre_A"),
        "delta_extensao_cranial_mm": d_cran,
        "delta_extensao_caudal_mm": d_caud,
        "deltas_de_largura_simulados_mm": deltas,
        "delta_largura_pedido_mm": pedido,
        "delta_largura_alcancado_mm": alcancado,
        "piso_de_resolucao_do_deslocamento_mm": piso,
        "dice_teto_por_largura": med_larg,
        "dice_teto_por_largura_por_grupo": {
            n: _por_grupo(lambda r, n=n: r["largura"][n]["dice"]) for n in nomes},
        "leitura_do_teto_por_largura": (
            "a diferenca de largura entre os dois estilos e MENOR que um voxel no plano: "
            f"pontual {delta_larg:.4f} mm, borda do IC95 "
            f"{deltas.get('ic95_superior', float('nan')):.4f} mm e MDE "
            f"{deltas.get('mde', float('nan')):.4f} mm, todos abaixo do piso de "
            f"{piso.get('mediana', float('nan')):.4f} mm que a grade consegue desenhar. "
            "Nesses tres cenarios o Dice volta 1,0000 porque o deslocamento nao encosta em "
            "voxel novo — e resolucao da grade, NAO concordancia dos estilos. O numero que "
            "responde e o cenario `um_voxel_no_plano`: o menor deslocamento desenhavel custa "
            f"Dice {dice_piso.get('mediana', float('nan')):.4f}, e como a diferenca real e "
            "menor que ele, o custo real em Dice e MENOR que esse."),
        "dice_teto_por_extensao": _res(dices_ext),
        "dice_teto_por_extensao_n_casos_aparados": len(aparados),
        "dice_teto_por_extensao_grupo_aparado": sorted({r["grupo"] for r in aparados}),
        "dice_teto_combinado": dices_comb,
        "baseline_dice_mediano": BASELINE_DICE_MEDIANO,
        "comparacao_com_o_baseline": (
            "o teto e a concordancia MAXIMA entre os dois estilos; o baseline e a "
            "concordancia OBTIDA por um modelo contra UM dos estilos. Teto abaixo de "
            f"{BASELINE_DICE_MEDIANO} significaria que o estilo sozinho ja explica todo o "
            "erro. Teto ACIMA nao permite a leitura simetrica: a premissa 2 deste mesmo "
            "bloco diz que deslocamento nao uniforme deixa o teto REAL menor que este, "
            "entao 'sobra erro para outras causas' NAO se deduz. O que se pode dizer e que "
            "o teto limita o estilo apenas NA PORCAO modelada como deslocamento uniforme. "
            "E a diferenca entre os dois numeros NAO e a fracao de erro atribuivel a "
            "estilo: sao quantidades diferentes, a comparacao e de ordem de grandeza e "
            "nunca de contabilidade. Ressalva de regua: este teto sai de casos S1, cujo "
            f"baseline proprio e 0,7995, e nao dos {BASELINE_DICE_MEDIANO} do development "
            "inteiro (n=30, tres instituicoes)."),
        "premissas_do_calculo": [
            "os dois lados sao casos DIFERENTES: nao ha par, e o Dice do teto e "
            "construido caso-contra-si-mesmo, nunca medido entre os dois datasets",
            "a diferenca de estilo e modelada como deslocamento UNIFORME da fronteira "
            "no plano; se o estilo diferir mais em umas regioes que em outras, o teto "
            "real e MENOR que este",
            "o deslocamento e no plano; nada e empurrado em z",
            "a diferenca de extensao entra so como APARA de quem sobra — estender "
            "contorno seria inventar fronteira",
            "o teto por largura so informa quando o deslocamento pedido passa de UM VOXEL "
            "no plano; abaixo disso o conjunto de nivel nao encosta em voxel novo e o Dice "
            "volta 1,0000 por resolucao de grade, nao por concordancia. O cenario "
            "`um_voxel_no_plano` existe justamente para dar o limite superior computavel",
            "largura e extensao sao aplicadas juntas no `combinado`, mas as duas "
            "diferencas foram medidas em amostras diferentes do mesmo par, e o "
            "combinado herda o erro das duas",
            "toda diferenca medida carrega o confundimento da Parte 1: kernel, kVp e "
            "estrategia respiratoria nao batem entre os lados",
        ],
        "por_caso": por_caso,
    }


def _aparar(m: np.ndarray, zooms, affine, cranial_mm: float, caudal_mm: float) -> np.ndarray:
    """Remove `cranial_mm` da ponta cranial e `caudal_mm` da caudal. So apara."""
    m = np.asarray(m) > 0
    if not m.any():
        return m.copy()
    dz = float(np.asarray(zooms)[2])
    sinal = rep._sinal_z(np.asarray(affine))
    cran, caud = rep._pontas(m, sinal)
    out = m.copy()
    for i in range(int(round(max(0.0, cranial_mm) / dz))):
        k = cran - i * int(sinal)
        if 0 <= k < m.shape[2]:
            out[:, :, k] = False
    for i in range(int(round(max(0.0, caudal_mm) / dz))):
        k = caud + i * int(sinal)
        if 0 <= k < m.shape[2]:
            out[:, :, k] = False
    return out


def executar(raiz_a: Path = RAIZ_LCTSC, raiz_b: Path = RAIZ_NSCLC,
             saida: Path = SAIDA_MORFO, log=print) -> dict[str, Any]:
    """Partes 3, 4 e 5, ponta a ponta. Grava JSON + CSV + resumo."""
    log("Parte 3 — morfologia do GT (sem modelo):")
    linhas = medir_grupos(raiz_a, raiz_b, log=log)

    s1 = [l["caso"] for l in linhas if l["grupo"] == "LCTSC-S1"]
    exigir_instituicao_unica(s1, "S1")     # o par so e par enquanto S1 for so S1

    log("Parte 4 — os quatro grupos:")
    quatro = comparar_quatro_grupos(linhas)

    log("Parte 5 — LCTSC-S1 x NSCLC:")
    par = {"pergunta": ("as distribuicoes de contorno diferem o bastante para que o "
                        "estilo explique parte substancial do erro do baseline?"),
           "por_medida": {}}
    for chave, unidade, escala in MEDIDAS:
        a = _valores(linhas, "LCTSC-S1", chave)
        b = _valores(linhas, "NSCLC", chave)
        r = comparar_par(a, b)
        r["unidade"], r["escala"] = unidade, escala
        par["por_medida"][chave] = r
        if isinstance(r.get("cliff_delta_B_vs_A"), float):
            log(f"  {chave:34s} {escala:12s} dif {r['diferenca_de_mediana_B_menos_A']:+8.3f} "
                f"{unidade:12s} delta {r['cliff_delta_B_vs_A']:+.3f} "
                f"({r['cliff_delta_rotulo']}) p {r['p_mann_whitney']:.4f}")

    par["multiplicidade"] = corrigir_multiplicidade(par["por_medida"])
    log(f"  multiplicidade: {par['multiplicidade']['n_p_brutos_abaixo_de_alfa']} p brutos < "
        f"{ALFA} em {par['multiplicidade']['n_medidas_testadas']} medidas "
        f"({par['multiplicidade']['esperado_por_acaso']:.2f} esperados por acaso); "
        f"sobrevivem a BH: {par['multiplicidade']['medidas_sobreviventes_bh']}")

    log("Parte 5 — teto de Dice imposto pelo estilo:")
    teto = teto_do_estilo(linhas, par, raiz_a, raiz_b, log=log)

    resultado = {
        "fase": "10, partes 3 a 5",
        "nao_treinou_nada": True,
        "baseline_intocado": BASELINE_DICE_MEDIANO,
        "grupos": {g: int(sum(1 for l in linhas if l["grupo"] == g)) for g in GRUPOS},
        "parte3_medidas": {k: {"unidade": u, "escala": e} for k, u, e in MEDIDAS},
        "parte4_quatro_grupos": quatro,
        "parte5_par_maastro": par,
        "parte5_teto": teto,
        "limitacoes": _LIMITACOES,
    }

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "morfologia.json").write_text(
        json.dumps(_json_safe(resultado), indent=2, ensure_ascii=False), encoding="utf-8")
    colunas = ["caso", "dataset", "grupo", "traqueia_disponivel", "aorta_disponivel",
               "carina_disponivel", "eixo_medial_pelo_esqueleto", *[k for k, _, _ in MEDIDAS]]
    with (saida / "morfologia_por_caso.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({k: l.get(k) for k in colunas})
    (saida / "resumo.md").write_text(_resumo_md(resultado), encoding="utf-8")
    log(f"gravado -> {saida}")
    return resultado


def _json_safe(o):
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return _json_safe(o.tolist())
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


_LIMITACOES = [
    "ASSOCIACAO, nunca causalidade: nada aqui mostra que a convencao de contorno CAUSA "
    "erro de segmentacao. O par MAASTRO fixa instituicao e geometria de voxel e deixa "
    "variar convencao E protocolo de reconstrucao juntos (Parte 1).",
    "n de 10 contra 25. p alto NAO e ausencia de efeito — por isso cada medida traz "
    "tamanho de efeito, IC por bootstrap e o efeito minimo detectavel por simulacao.",
    "A atribuicao LCTSC-S1 = MAASTRO segue HIPOTESE da fase 9; InstitutionName esta "
    "ausente nos dois lados.",
    "A traqueia e a aorta sao PREDICOES do TotalSegmentator 2.18.0, nao marcacoes. "
    "Servem de regua; se a regua errar, o caso perde a regua, mas o erro dela nao entra "
    "nas medidas que so dependem do GT.",
    "A carina e o extremo caudal da mascara `trachea` predita — aproximacao declarada na "
    "fase 9, nunca verificada contra anatomia marcada.",
    "O teto de Dice e CONSTRUIDO sob premissa de deslocamento uniforme de fronteira, nao "
    "medido entre os dois datasets: os casos sao de estruturas diferentes e nao ha par.",
    "LUNG1-021 teve a grade regularizada na conversao (0,51% em z); toda medida em mm "
    "desse caso herda a esticada.",
    "O lado B nao e homogeneo consigo mesmo (4 familias de protocolo, 2 kVp, 4 kernels): "
    "compara-lo como bloco unico mede a media de uma mistura.",
    "O eixo medial vem de skeletonize 3D; em estrutura tubular fina ele pode gerar ramos "
    "espurios. A coluna eixo_medial_pelo_esqueleto registra quando o esqueleto saiu vazio "
    "e o vetor caiu para o interior inteiro.",
    "Varias medidas sao QUANTIZADAS pela grade (dz 3,0 mm; dx 0,977 mm), e S1 e NSCLC tem a "
    "MESMA grade (Parte 1). Por isso medianas identicas — comprimento, distancia a traqueia, "
    "posicao da carina — sao coincidencia de grade, nao prova de igualdade. Quem responde "
    "'quanto poderiam diferir' e o IC95 e o MDE, nao a diferenca de mediana.",
    "n_fatias_gt esta em voxels: entre S1 e NSCLC e comparavel (mesmo dz), mas contra o S2 "
    "(dz 2,5 mm) uma diferenca pode ser so a grade. A versao fisica e comprimento_z_mm.",
    "MULTIPLICIDADE: a Parte 5 roda ~30 testes na mesma amostra. O bloco `multiplicidade` "
    "traz o p corrigido por Benjamini-Hochberg e quantos p abaixo de alfa eram esperados "
    "por acaso. Nenhum p BRUTO deve ser lido como achado sem olhar essa linha.",
    "Medida com `efeito_observado_abaixo_do_mde` verdadeiro e que ainda assim passa em alfa "
    "esta no regime de erro de MAGNITUDE: a direcao pode estar certa e o tamanho, inflado.",
    "As ~30 medidas nao sao independentes: raio_caracteristico_mm e largura_efetiva_p50_mm "
    "sao o MESMO numero, e meia_espessura_envelope_mm e a metade dele. A contagem de testes "
    "e maior que o numero de perguntas distintas, e a correcao BH sai conservadora.",
]


def _f(v, casas=4) -> str:
    if isinstance(v, bool) or v is None:
        return NM if v is None else str(v)
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return NM if not np.isfinite(v) else f"{float(v):.{casas}f}".replace(".", ",")
    return str(v)


def _resumo_md(r: dict[str, Any]) -> str:
    L = ["# Fase 10, partes 3 a 5 — morfologia do GT e o teste do par MAASTRO", "",
         f"Grupos: " + " · ".join(f"{g} n={n}" for g, n in r["grupos"].items()),
         f"Nada foi treinado. Baseline intocado (dice mediano {_f(BASELINE_DICE_MEDIANO)}).", ""]

    L += ["## Parte 4 — os quatro grupos", "",
          "| medida | escala | unidade | " + " | ".join(GRUPOS) + " | KW p | p BH |",
          "|---|---|---|" + "---|" * (len(GRUPOS) + 2)]
    for k, u, e in MEDIDAS:
        c = r["parte4_quatro_grupos"][k]
        cel = [_f(c["por_grupo"][g].get("mediana"), 3) for g in GRUPOS]
        L.append(f"| {k} | {e} | {u} | " + " | ".join(cel) + " | "
                 + _f(c["kruskal_wallis"].get("p")) + " | "
                 + _f(c["kruskal_wallis"].get("p_bh")) + " |")
    m4 = r["parte4_quatro_grupos"].get("multiplicidade", {})
    L += ["", f"{m4.get('n_medidas_testadas', NM)} testes na mesma amostra, "
              f"{_f(m4.get('esperado_por_acaso'), 2)} p abaixo de alfa esperados por acaso, "
              f"{m4.get('n_p_brutos_abaixo_de_alfa', NM)} observados, "
              f"{m4.get('n_sobreviventes_bh', NM)} sobrevivem ao BH: "
              f"{m4.get('medidas_sobreviventes_bh', NM)}. {m4.get('leitura', '')}"]

    m = r["parte5_par_maastro"].get("multiplicidade", {})
    L += ["", "## Parte 5 — LCTSC-S1 (n=10) x NSCLC (n=25)", "",
          f"{m.get('n_medidas_testadas', NM)} medidas testadas na MESMA amostra. "
          f"p brutos abaixo de {_f(m.get('alfa'), 2)}: {m.get('n_p_brutos_abaixo_de_alfa', NM)} "
          f"({_f(m.get('esperado_por_acaso'), 2)} esperados por acaso). "
          f"Sobrevivem a Benjamini-Hochberg: {m.get('medidas_sobreviventes_bh', NM)}.", "",
          "| medida | escala | mediana S1 | mediana NSCLC | dif | % | Cliff delta | IC95 delta | "
          "p MW | p BH | p perm | MDE | dif < MDE |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, u, e in MEDIDAS:
        c = r["parte5_par_maastro"]["por_medida"][k]
        if "mediana_A" not in c:
            L.append(f"| {k} | {e} | {NA} | | | | | | | | | | |")
            continue
        icd = c.get("ic95_cliff_delta") or [None, None]
        L.append(
            f"| {k} | {e} | {_f(c['mediana_A'], 3)} | {_f(c['mediana_B'], 3)} | "
            f"{_f(c['diferenca_de_mediana_B_menos_A'], 3)} | "
            f"{_f(c.get('diferenca_pct_sobre_A'), 1)} | "
            f"{_f(c['cliff_delta_B_vs_A'], 3)} ({c['cliff_delta_rotulo']}) | "
            + (f"{_f(icd[0], 3)} a {_f(icd[1], 3)}" if isinstance(icd, list) else NA) + " | "
            f"{_f(c['p_mann_whitney'])} | {_f(c.get('p_mann_whitney_bh'))} | "
            f"{_f(c['p_permutacao_da_mediana'])} | "
            f"{_f(c['poder'].get('mde'), 3)} | "
            f"{'SIM' if c.get('efeito_observado_abaixo_do_mde') else 'nao'} |")

    t = r["parte5_teto"]
    L += ["", "## Parte 5 — o teto que o estilo impoe", ""]
    if t.get("veredito") == NA:
        L.append(f"{NA}: {t.get('motivo')}")
    else:
        L += [f"- diferenca de largura efetiva: {_f(t['delta_largura_mm'], 3)} mm "
              f"({_f(t.get('delta_largura_pct'), 1)} %), IC95 "
              + " a ".join(_f(x, 3) for x in (t.get('delta_largura_ic95_mm') or [None, None])),
              "", "| cenario de largura | delta pedido, mediana (mm) | delta alcancado, "
              "mediana (mm) | teto de Dice, mediana | n |", "|---|---|---|---|---|"]
        for nome in t["dice_teto_por_largura"]:
            m = t["dice_teto_por_largura"][nome]
            L.append(f"| {nome} | {_f(t['delta_largura_pedido_mm'][nome].get('mediana'), 3)} | "
                     f"{_f(t['delta_largura_alcancado_mm'][nome].get('mediana'), 3)} | "
                     f"{_f(m.get('mediana'))} | {m.get('n')} |")
        L += ["", t["leitura_do_teto_por_largura"], "",
              f"- teto de Dice so por extensao: mediana {_f(t['dice_teto_por_extensao'].get('mediana'))}"
              f" — so os {t['dice_teto_por_extensao_n_casos_aparados']} casos aparaveis "
              f"({t['dice_teto_por_extensao_grupo_aparado']}); no outro lado, estender seria "
              "inventar fronteira",
              *[f"- teto de Dice combinado (largura {n} + extensao): mediana "
                f"{_f(v.get('mediana'))} (n={v.get('n')})"
                for n, v in t["dice_teto_combinado"].items()],
              f"- baseline (congelado, para comparacao): {_f(BASELINE_DICE_MEDIANO)}", "",
              "Premissas do teto:"] + [f"  - {p}" for p in t["premissas_do_calculo"]]
    L += ["", "## Limitacoes", ""] + [f"- {x}" for x in r["limitacoes"]]
    return "\n".join(L) + "\n"


# ===================================================================== testes


def _derruba(excecao, funcao, *args, **kwargs) -> None:
    """CONTROLE POSITIVO: a chamada TEM que levantar `excecao`."""
    try:
        funcao(*args, **kwargs)
    except excecao:
        return
    raise AssertionError(
        f"CONTROLE POSITIVO FALHOU: {funcao.__name__} nao levantou {excecao.__name__} "
        f"para {args[:2]}"
    )


def _cilindro(shape=(48, 48, 22), zooms=(1.0, 1.0, 3.0), raio_mm=5.0,
              z=(4, 18), deriva=0.5) -> np.ndarray:
    """Fantoma de calibre CONHECIDO: largura efetiva = 2 x raio_mm.

    `deriva` inclina o eixo do tubo meio voxel por fatia, e nao e enfeite:
    MEDIDO aqui, o skeletonize 3D do skimage 0.26 devolve esqueleto VAZIO para um
    cilindro perfeitamente reto e centrado (e para um cubo solido), e nao vazio
    assim que o eixo deixa de ser exatamente paralelo a Z. Um fantoma reto
    testaria o galho de excecao de calibre_mm em vez do caminho que os dados
    reais usam — medido: o esqueleto sai NAO vazio em 30/30 do LCTSC development
    e em 25/25 do subconjunto do NSCLC.
    """
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    c = shape[0] / 2.0 - 0.5
    m = np.zeros(shape, dtype=bool)
    for i, k in enumerate(range(z[0], z[1])):
        m[:, :, k] = np.hypot((xx - c - deriva * i) * zooms[0],
                              (yy - c) * zooms[1]) <= raio_mm
    return m


def _autoteste_forma() -> None:
    """Partes 3 a 5: cada instrumento novo com fantoma de resposta conhecida.

    Todo assert aqui e um CONTROLE POSITIVO no sentido do PRINCIPIO: existe uma
    forma de o instrumento estar errado que faz este assert cair.
    """
    zooms = np.array([1.0, 1.0, 3.0])

    # --- largura efetiva: o numero e 2 x raio, nao o raio (fator 2 esquecido cai aqui)
    cil = _cilindro(raio_mm=5.0)
    v, usou, ref = _largura_efetiva_vetor(cil, zooms)
    assert usou and v.size > 0, "esqueleto vazio num cilindro de 10 mm"
    assert abs(ref - 10.0) < 2.0, f"largura efetiva {ref} != ~10 mm"
    # a MESMA definicao de espessura.calibre_mm, nos DOIS galhos. Se elas se
    # separarem, esta fase estaria publicando um numero que a fase 9 nao publicou.
    assert abs(ref - calibre_mm(cil, zooms)["espessura_mediana_no_esqueleto_mm"]) < 1e-9, (
        "galho COM esqueleto: a referencia daqui nao bate com calibre_mm")
    reto = _cilindro(raio_mm=5.0, deriva=0.0)     # esqueleto vazio: galho de excecao
    v0, usou0, ref0 = _largura_efetiva_vetor(reto, zooms)
    assert not usou0, "o cilindro reto deixou de cair no galho sem esqueleto"
    assert abs(ref0 - calibre_mm(reto, zooms)["espessura_mediana_no_esqueleto_mm"]) < 1e-9, (
        "galho SEM esqueleto: a referencia daqui nao bate com o p90 de calibre_mm")
    # CONTROLE POSITIVO: um cilindro mais grosso TEM que dar numero maior
    _, _, ref2 = _largura_efetiva_vetor(_cilindro(raio_mm=8.0), zooms)
    assert ref2 > ref + 3.0, (
        "a largura efetiva nao subiu com o calibre — o instrumento e cego a calibre")

    # --- largura por fatia: acompanha o afinamento, nao devolve constante
    afinando = np.zeros((48, 48, 22), bool)
    for k, r in zip(range(4, 18), np.linspace(9.0, 3.0, 14)):
        afinando[:, :, k] = _cilindro(raio_mm=float(r), z=(k, k + 1), deriva=0.0)[:, :, k]
    zf, lf = largura_por_fatia_mm(afinando, zooms)
    assert zf.size == 14 and lf.size == 14, (zf.size, lf.size)
    assert lf[0] > lf[-1] + 5.0, f"largura por fatia nao viu o afinamento: {lf[0]} -> {lf[-1]}"
    assert float(lf.std(ddof=1)) > 1.0, "variacao de calibre em Z saiu ~0 num tubo que afina"
    # CONTROLE POSITIVO: num tubo de calibre CONSTANTE a variacao tem que sumir
    _, lc = largura_por_fatia_mm(cil, zooms)
    assert float(lc.std(ddof=1)) < 1.0, "variacao de calibre acusou variacao num tubo reto"

    # --- distancia no plano: mede a folga que existe, e ve quando nao ha folga
    # ultimo voxel de `a` em x=19, primeiro de `b` em x=26: 7 mm entre centros
    a = np.zeros((48, 48, 6), bool); a[10:20, 20:28, 1:5] = True
    b = np.zeros((48, 48, 6), bool); b[26:36, 20:28, 1:5] = True
    d = distancia_no_plano_mm(a, b, zooms)
    assert d["n_fatias_com_os_dois"] == 4, d
    assert abs(d["mediana_mm"] - 7.0) < 1e-6, f"folga medida {d['mediana_mm']} != 7,0 mm"
    assert d["frac_fatias_sem_folga"] == 0.0, d
    # CONTROLE POSITIVO: encostado tem que cair no balde "sem folga"; sobreposto, em zero
    colado = np.zeros((48, 48, 6), bool); colado[20:30, 20:28, 1:5] = True
    dc = distancia_no_plano_mm(a, colado, zooms)
    assert dc["mediana_mm"] == 1.0 and dc["frac_fatias_sem_folga"] == 1.0, dc
    dsobre = distancia_no_plano_mm(a, a, zooms)
    assert dsobre["mediana_mm"] == 0.0 and dsobre["frac_fatias_sem_folga"] == 1.0, dsobre

    # --- offset no plano: empurra 2t de largura e NAO mexe em z
    m2 = offset_no_plano(cil, zooms, 2.0)
    l0 = calibre_mm(cil, zooms)["espessura_mediana_no_esqueleto_mm"]
    l1 = calibre_mm(m2, zooms)["espessura_mediana_no_esqueleto_mm"]
    # 2 mm de offset radial pedem 4 mm de largura; a grade de 1 mm entrega menos.
    # A faixa e larga de proposito: quem publica o numero e o `alcancado`, medido,
    # nunca o alvo. Estreitar isto seria fingir que a grade nao quantiza.
    assert 2.0 <= (l1 - l0) <= 5.0, f"offset de 2 mm mudou a largura em {l1 - l0} mm"
    assert (np.flatnonzero(m2.any(axis=(0, 1))).tolist()
            == np.flatnonzero(cil.any(axis=(0, 1))).tolist()), (
        "o offset vazou para z — ele misturaria calibre com extensao")
    assert (offset_no_plano(cil, zooms, 0.0) == cil).all(), "offset de 0 mm mexeu na mascara"
    # recorte: aceleracao que NAO pode mudar numero nenhum
    cor, _fat = _recorte_no_plano(cil)
    assert cor.shape != cil.shape, "o recorte nao recortou — o teste abaixo seria vazio"
    assert abs(_largura_efetiva_vetor(cor, zooms)[2]
               - _largura_efetiva_vetor(cil, zooms)[2]) < 1e-9, (
        "o recorte mudou a largura efetiva — deixou de ser so velocidade")
    assert sm.dice(offset_no_plano(cor, zooms, 1.0), cor) == sm.dice(
        offset_no_plano(cil, zooms, 1.0), cil), "o recorte mudou o Dice do deslocamento"
    # CONTROLE POSITIVO: erodir TEM que estreitar, nao so mudar de tamanho
    l_ero = calibre_mm(offset_no_plano(cil, zooms, -1.5), zooms)[
        "espessura_mediana_no_esqueleto_mm"]
    assert l_ero < l0 - 1.0, f"erosao de 1,5 mm nao estreitou ({l_ero} vs {l0})"

    # --- teto por largura: 0 mm da Dice 1, e mais mm da MENOS Dice
    t0 = teto_de_dice_por_largura(cil, zooms, 0.0)
    t2 = teto_de_dice_por_largura(cil, zooms, 2.0)
    t4 = teto_de_dice_por_largura(cil, zooms, 4.0)
    assert t0["dice"] == 1.0, t0
    assert t4["dice"] < t2["dice"] < 1.0, (t2["dice"], t4["dice"])
    assert 2.0 <= t4["delta_largura_alcancado_mm"] <= 5.0, t4
    # PISO DE RESOLUCAO — foi isto que apareceu no dado real: um deslocamento
    # menor que meio voxel nao encosta em voxel novo, o Dice volta 1,0000 e isso
    # NAO e concordancia, e cegueira da grade. O teste fixa as duas metades:
    # (a) sub-voxel devolve Dice 1 com alcancado 0 — e nunca copia o alvo pedido;
    # (b) um voxel inteiro de deslocamento radial JA custa Dice.
    sub = teto_de_dice_por_largura(cil, zooms, 0.5)      # 0,25 mm de raio, grade de 1 mm
    assert sub["dice"] == 1.0 and sub["delta_largura_alcancado_mm"] == 0.0, sub
    assert sub["delta_largura_alcancado_mm"] != sub["delta_largura_alvo_mm"], (
        "o alcancado esta copiando o alvo em vez de medir a mascara deslocada")
    piso = teto_de_dice_por_largura(cil, zooms, 2.0 * float(zooms[0]))
    assert piso["dice"] < 0.95, (
        f"um voxel de deslocamento radial nao custou Dice ({piso['dice']}) — sem esse "
        "custo nao existe limite superior computavel para a diferenca sub-voxel")
    # CONTROLE POSITIVO: o Dice do teto tem que ser sensivel a MILIMETRO, senao
    # traduzir "mm de estilo" para Dice nao mede nada
    assert t2["dice"] - t4["dice"] > 0.05, (
        "2 mm de diferenca de largura mudam o Dice em menos de 0,05 — a traducao e cega")

    # --- teto por extensao: apara o que da, recusa o que nao da
    aff = np.diag([1.0, 1.0, 3.0, 1.0])
    e0 = teto_de_dice_por_extensao(cil, zooms, aff, 0.0, 0.0)
    e9 = teto_de_dice_por_extensao(cil, zooms, aff, 9.0, 0.0)
    assert e0["dice"] == 1.0 and e0["n_fatias_removidas"] == 0, e0
    assert e9["n_fatias_removidas"] == 3 and e9["dice"] < 1.0, e9
    neg = teto_de_dice_por_extensao(cil, zooms, aff, -9.0, 0.0)
    assert neg["cranial_nao_aplicavel"] and neg["n_fatias_removidas"] == 0, neg
    assert (_aparar(cil, zooms, aff, 0.0, 0.0) == cil).all()

    # --- Cliff delta: sinal, extremos e insensibilidade a n
    assert cliff_delta([1, 2, 3], [1, 2, 3]) == 0.0
    assert cliff_delta([10, 11, 12], [1, 2, 3]) == 1.0
    assert cliff_delta([1, 2, 3], [10, 11, 12]) == -1.0
    assert _rotulo_cliff(0.05) == "desprezivel" and _rotulo_cliff(0.9) == "grande"
    # CONTROLE POSITIVO: nao pode virar p disfarcado — repetir a amostra 10 vezes
    # muda o p, mas NAO pode mudar o tamanho de efeito
    assert abs(cliff_delta([1, 2, 3] * 10, [2, 3, 4] * 10)
               - cliff_delta([1, 2, 3], [2, 3, 4])) < 1e-12, (
        "Cliff delta mudou com o n — entao e p, nao tamanho de efeito")

    # --- permutacao e bootstrap: separam o que e separado, e nao inventam separacao
    rng = np.random.default_rng(7)
    x = rng.normal(0.0, 1.0, 40)
    y = rng.normal(0.0, 1.0, 40)
    assert _p_permutacao(x, y, n=2000) > 0.05, "permutacao acusou diferenca em ruido puro"
    # CONTROLE POSITIVO: com as duas amostras separadas, o p tem que ir ao chao
    assert _p_permutacao(x, y + 5.0, n=2000) < 0.01, "permutacao nao viu 5 sigma de diferenca"
    ic = _ic_bootstrap(y + 5.0, x, lambda u, w: float(np.median(u) - np.median(w)), n=800)
    assert ic["ic95"][0] > 0.0, f"IC do bootstrap incluiu zero com 5 sigma de diferenca: {ic}"
    ic0 = _ic_bootstrap(y, x, lambda u, w: float(np.median(u) - np.median(w)), n=800)
    assert ic0["ic95"][0] < 0.0 < ic0["ic95"][1], f"IC excluiu zero em ruido puro: {ic0}"

    # --- multiplicidade: BH tem que ENGOLIR o vencedor de loteria e POUPAR o real
    loteria = {f"m{i}": {"p_mann_whitney": p} for i, p in
               enumerate([0.02, *[0.2 + 0.02 * i for i in range(29)]])}
    mult = corrigir_multiplicidade(loteria)
    assert mult["n_p_brutos_abaixo_de_alfa"] == 1 and mult["n_sobreviventes_bh"] == 0, mult
    assert loteria["m0"]["sobrevive_a_bh"] is False, "p 0,02 entre 30 testes sobreviveu ao BH"
    # CONTROLE POSITIVO: um efeito forte de verdade nao pode ser apagado pela correcao
    real = {f"m{i}": {"p_mann_whitney": p} for i, p in
            enumerate([1e-6, *[0.2 + 0.02 * i for i in range(29)]])}
    mr = corrigir_multiplicidade(real)
    assert mr["n_sobreviventes_bh"] == 1 and real["m0"]["sobrevive_a_bh"], (
        "o BH apagou um p de 1e-6 — a correcao esta cega a efeito real")

    # --- BH da Parte 4: mesmo par de controles, sobre p de Kruskal-Wallis
    lot4 = {f"m{i}": {"kruskal_wallis": {"p": pv}} for i, pv in
            enumerate([0.02, *[0.2 + 0.02 * i for i in range(29)]])}
    m4 = _bh_kruskal(lot4)
    assert m4["n_p_brutos_abaixo_de_alfa"] == 1 and m4["n_sobreviventes_bh"] == 0, m4
    assert lot4["m0"]["kruskal_wallis"]["sobrevive_a_bh"] is False, (
        "p 0,02 de KW entre 30 testes sobreviveu ao BH")
    real4 = {f"m{i}": {"kruskal_wallis": {"p": pv}} for i, pv in
             enumerate([1e-6, *[0.2 + 0.02 * i for i in range(29)]])}
    mr4 = _bh_kruskal(real4)
    assert mr4["n_sobreviventes_bh"] == 1 and real4["m0"]["kruskal_wallis"]["sobrevive_a_bh"], (
        "o BH da Parte 4 apagou um p de 1e-6")
    # a chave `multiplicidade` nao pode se passar por medida e reentrar na familia
    lot5 = {"multiplicidade": {"n_medidas_testadas": 3}, "m": {"kruskal_wallis": {"p": 0.01}}}
    assert _bh_kruskal(lot5)["n_medidas_testadas"] == 1, (
        "o bloco de multiplicidade entrou na propria familia que ele corrige")

    # --- efeito minimo detectavel: mais casos TEM que enxergar menos
    p_pouco = efeito_minimo_detectavel(x[:10], y[:25], 10, 25, n_sim=300)
    p_muito = efeito_minimo_detectavel(x, y, 200, 500, n_sim=300)
    assert isinstance(p_pouco["mde"], float) and p_pouco["mde"] > 0, p_pouco
    assert p_muito["mde"] < p_pouco["mde"], (
        f"o MDE nao caiu com o n ({p_pouco['mde']} -> {p_muito['mde']}) — "
        "entao ele nao mede poder")

    # --- rotulagem de grupo e serializacao
    assert _grupo_de("LCTSC-Train-S1-002", "LCTSC") == "LCTSC-S1"
    assert _grupo_de("LUNG1-021", COLECAO_B) == "NSCLC"
    assert set(ESCALA_DA_MEDIDA.values()) == {"absoluta", "normalizada"}
    js = _json_safe({"_privado": 1, "x": np.float64("nan"), "y": np.int64(3),
                     "z": np.array([1.0, 2.0])})
    assert js == {"x": None, "y": 3, "z": [1.0, 2.0]}, js


def _autoteste() -> None:
    """Cada guarda: um caso legitimo que PASSA e um controle positivo que DERRUBA."""
    import tempfile

    import nibabel as nib

    split = {"development": ["LCTSC-Train-S1-002", "LCTSC-Train-S1-003"],
             "validation": ["LCTSC-Train-S1-010"],
             "test": ["LCTSC-Train-S1-001"]}
    s1 = ["LCTSC-Train-S1-002", "LCTSC-Train-S1-003"]

    # --- ordem deterministica: mesma entrada, mesma saida; outra semente, outra ordem
    pids = [f"LUNG1-{i:03d}" for i in range(1, 60)]
    assert sorted(pids, key=ordem_deterministica) == sorted(reversed(pids),
                                                            key=ordem_deterministica)
    global SEMENTE_SUBCONJUNTO
    orig = SEMENTE_SUBCONJUNTO
    try:
        SEMENTE_SUBCONJUNTO = "outra-semente"
        assert sorted(pids, key=ordem_deterministica)[:5] != sorted(
            pids, key=lambda p: hashlib.sha256(f"{orig}|{p}".encode()).hexdigest())[:5], (
            "a semente nao afeta a ordem")
    finally:
        SEMENTE_SUBCONJUNTO = orig

    # --- crivo de nome: nao presume "Esophagus"
    assert CRIVO_ESOFAGO.search("esophagus") and CRIVO_ESOFAGO.search("oesophagus")
    assert CRIVO_ESOFAGO.search("esophagus_ce") and not CRIVO_ESOFAGO.search("spinal-cord")

    # --- 1. instituicao unica
    assert exigir_instituicao_unica(s1, "S1")["recusou"] is False
    _derruba(MisturaDeInstituicoes, exigir_instituicao_unica,
             [*s1, "LCTSC-Train-S2-002"], "S1")                 # mistura de instituicoes

    # --- 2. sem repeticao (REUSO)
    assert exigir_sem_repeticao(s1)["recusou"] is False
    _derruba(prot.CasoRepetido, exigir_sem_repeticao, [*s1, s1[0]])          # duplicado

    # --- 3. apenas development
    assert exigir_apenas_development(s1, split)["recusou"] is False
    _derruba(TestGasto, exigir_apenas_development,
             [*s1, "LCTSC-Train-S1-001"], split)                 # LCTSC test
    _derruba(ConjuntoProibido, exigir_apenas_development,
             [*s1, "LCTSC-Train-S1-010"], split)                 # LCTSC validation
    _derruba(ConjuntoProibido, exigir_apenas_development, ["LCTSC-Train-S1-999"], split)

    # --- 4. dataset permitido
    assert exigir_dataset_permitido("LCTSC", s1)["recusou"] is False
    assert exigir_dataset_permitido(COLECAO_B, ["LUNG1-031"], ["LUNG1-031"])["recusou"] is False
    _derruba(DatasetNaoPermitido, exigir_dataset_permitido, "SAROS", ["x"])  # fora do escopo
    _derruba(DatasetNaoPermitido, exigir_dataset_permitido,
             COLECAO_B, ["LUNG1-999"], ["LUNG1-031"])            # fora do subconjunto declarado

    # --- 5. mascara na grade (REUSO)
    m = np.zeros((8, 8, 8), np.uint8)
    m[3:5, 3:5, 3:5] = 255
    assert exigir_mascara_na_grade(m, (8, 8, 8))["recusou"] is False
    _derruba(prot.MascaraForaDaGrade, exigir_mascara_na_grade, m, (8, 8, 9))  # grade errada
    _derruba(prot.MascaraForaDaGrade, exigir_mascara_na_grade,
             np.zeros((8, 8, 8), np.uint8), (8, 8, 8))                        # vazia

    # --- 6. spacing presente
    bom = {"pixel_spacing_mm": [0.9765625, 0.9765625], "espacamento_z_mediano_mm": 3.0,
           "espacamento_z_uniforme": True}
    assert exigir_spacing_presente(bom)["recusou"] is False
    _derruba(SpacingAusente, exigir_spacing_presente, {**bom, "pixel_spacing_mm": None})
    _derruba(SpacingAusente, exigir_spacing_presente, {**bom, "espacamento_z_mediano_mm": None})
    _derruba(SpacingAusente, exigir_spacing_presente, {**bom, "espacamento_z_mediano_mm": 0.0})

    # --- 7. affine compativel (REUSO)
    with tempfile.TemporaryDirectory() as td:
        cubo = np.zeros((12, 12, 12), np.uint8)
        cubo[4:8, 4:8, 4:8] = 255
        aff = np.diag([0.9765625, 0.9765625, 3.0, 1.0])
        pa, pb, pc = (Path(td) / f"{n}.nii.gz" for n in "abc")
        nib.save(nib.Nifti1Image(cubo, aff), str(pa))
        nib.save(nib.Nifti1Image(cubo, aff), str(pb))
        deslocado = aff.copy()
        deslocado[2, 3] += 1.5
        nib.save(nib.Nifti1Image(cubo, deslocado), str(pc))
        assert exigir_affine_compativel(pa, pb)["recusou"] is False
        _derruba(geometria.DesalinhamentoGeometrico, exigir_affine_compativel, pa, pc)

        # --- _valor / metadados_protocolo: ausente e vazio viram ND, nao ""
        import pydicom
        from pydicom.dataset import Dataset, FileMetaDataset

        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        ds.file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
        ds.file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        ds.SeriesDescription = ""          # presente porem VAZIO
        ds.Manufacturer = "SIEMENS"
        ds.PixelSpacing = [0.9765625, 0.9765625]
        p = Path(td) / "fatia.dcm"
        ds.save_as(str(p), enforce_file_format=True)
        meta = metadados_protocolo(Path(td))
        assert meta["SeriesDescription"] == ND, meta["SeriesDescription"]
        assert meta["InstitutionName"] == ND, meta["InstitutionName"]
        assert meta["Manufacturer"] == "SIEMENS" and meta["PixelSpacing"] == [0.9765625] * 2

    # --- resumo de campo: nao inventa concordancia onde os dois lados estao vazios
    r = _resumo_campo([{"X": ND}, {"X": ND}], "X")
    assert r["todos_nao_disponiveis"] and r["n_distintos"] == 1, r
    r2 = _resumo_campo([{"X": "a"}, {"X": "b"}], "X")
    assert r2["n_distintos"] == 2 and not r2["todos_nao_disponiveis"], r2

    # --- tolerancia numerica: engole o arredondamento do re-export, NAO engole 0,5 mm
    a_cheio = _resumo_campo([{"P": [0.9765625, 0.9765625]}], "P")["valores"]
    b_3casas = _resumo_campo([{"P": [0.977, 0.977]}], "P")["valores"]
    assert _iguais_com_tolerancia(a_cheio, b_3casas) is True, "tolerancia nao cobre 4,4e-4 mm"
    # CONTROLE POSITIVO: uma diferenca REAL de spacing tem que continuar aparecendo
    assert _iguais_com_tolerancia(_resumo_campo([{"P": 3.0}], "P")["valores"],
                                  _resumo_campo([{"P": 2.5}], "P")["valores"]) is False, (
        "a tolerancia engoliu 0,5 mm — ela apagaria a diferenca de dz entre S1 e S2")
    assert _iguais_com_tolerancia(_resumo_campo([{"P": "SIEMENS"}], "P")["valores"],
                                  _resumo_campo([{"P": "CMS, Inc."}], "P")["valores"]) is None, (
        "texto entrou no caminho numerico")
    assert _iguais_com_tolerancia(_resumo_campo([{"P": ND}], "P")["valores"],
                                  _resumo_campo([{"P": 3.0}], "P")["valores"]) is None

    # --- cruzamento de nomes de protocolo: tira o enfeite da tag, nao inventa casamento
    assert _token_de_protocolo("Specials^RCCTPET_THORAX_8F (Adult)") == "RCCTPET_THORAX_8F"
    assert _token_de_protocolo(ND) is None and _token_de_protocolo(3.0) is None
    cr = cruzar_nomes_de_protocolo(
        [{"caso": "A1", "StudyDescription": "Specials^RCCTPET_THORAX_8F (Adult)"}],
        [{"caso": "B1", "ProtocolName": "RCCTPET_THORAX_8F"}])
    assert cr["casamentos_exatos"] == ["RCCTPET_THORAX_8F"], cr
    # CONTROLE POSITIVO: dois nomes sem relacao NAO podem casar, nem por familia
    cr2 = cruzar_nomes_de_protocolo(
        [{"caso": "A1", "StudyDescription": "RT^RCCT_THORAX_8F (Adult)"}],
        [{"caso": "B1", "ProtocolName": "HEAD_ANGIO_FAST"}])
    assert cr2["casamentos_exatos"] == [] and cr2["familias_em_comum"] == [], cr2

    _autoteste_forma()

    print(f"estilo_esofago.py: autoteste OK — {len(GUARDAS)} guardas com controle positivo "
          "+ instrumentos das partes 3 a 5 com fantoma de resposta conhecida")


def verificar_por_mutacao(guardas: tuple[str, ...] = GUARDAS) -> list[dict[str, Any]]:
    """Desliga UMA guarda por vez e exige que o autoteste CAIA.

    Guarda que nao derruba o teste quando desligada nao esta guardando nada.
    Guarda reusada e desligada no modulo DELA, senao a mutacao testaria o
    wrapper daqui em vez da tranca de la.
    """
    relatorio = []
    for nome in guardas:
        alvo = _ONDE_DESLIGAR.get(nome, _DESLIGADAS)
        alvo.add(nome)
        try:
            _autoteste()
            caiu, motivo = False, "o autoteste PASSOU sem a guarda"
        except AssertionError as e:
            caiu, motivo = True, str(e).splitlines()[0][:160]
        finally:
            alvo.discard(nome)
        relatorio.append({"guarda": nome, "autoteste_caiu": caiu, "motivo": motivo})
    sobreviventes = [r["guarda"] for r in relatorio if not r["autoteste_caiu"]]
    if sobreviventes:
        raise AssertionError(
            f"guardas que NAO derrubam o autoteste quando desligadas: {sobreviventes}. "
            "Elas nao estao guardando nada."
        )
    return relatorio


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fase 10 — aquisicao do par MAASTRO e comparabilidade.")
    p.add_argument("--autoteste", action="store_true")
    p.add_argument("--mutacao", action="store_true")
    p.add_argument("--declarar", action="store_true", help="censo de ROIs + declaracao (sem CT)")
    p.add_argument("--adquirir", action="store_true", help="baixa e converte o subconjunto")
    p.add_argument("--tabela", action="store_true", help="Parte 1 + Parte 2")
    p.add_argument("--aux", action="store_true",
                   help="traqueia e aorta do lado B (inferencia; o lado A ja tem, da fase 7)")
    p.add_argument("--morfologia", action="store_true", help="Partes 3, 4 e 5")
    p.add_argument("--raiz-lctsc", type=Path, default=RAIZ_LCTSC)
    p.add_argument("--raiz-nsclc", type=Path, default=RAIZ_NSCLC)
    a = p.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0
    if a.mutacao:
        for r in verificar_por_mutacao():
            print(f"  {r['guarda']:20s} desligada -> autoteste "
                  f"{'CAIU' if r['autoteste_caiu'] else 'PASSOU (INUTIL)'}: {r['motivo']}")
        print(f"mutacao OK — {len(GUARDAS)}/{len(GUARDAS)} guardas derrubam o autoteste")
        return 0
    if a.declarar:
        censo_e_declaracao(a.raiz_nsclc)
        return 0
    if a.adquirir:
        adquirir(a.raiz_nsclc)
        return 0
    if a.tabela:
        tabela_comparabilidade(a.raiz_lctsc, a.raiz_nsclc)
        gravar_definicoes()
        return 0
    if a.aux:
        gerar_aux(a.raiz_nsclc)
        return 0
    if a.morfologia:
        executar(a.raiz_lctsc, a.raiz_nsclc)
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
