"""Cliente minimo da API publica do TCIA (NBIA), com cache em disco.

Colecao aberta (LCTSC) = sem token e sem cadastro; so GET + urllib da stdlib.
O cache e o proprio diretorio de destino: uma serie ja baixada tem
`_tcia_serie.json` gravado DEPOIS da extracao completa, entao um download
interrompido no meio nao passa por baixado.

Esse mesmo `_tcia_serie.json` e a prova de licenca: e o registro da API, com
LicenseName / LicenseURI / CollectionURI, nao um valor digitado a mao.
"""

from __future__ import annotations

import io
import json
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
MARCADOR = "_tcia_serie.json"


def listar_series(
    collection: str,
    patient_id: str | None = None,
    modality: str | None = None,
    timeout: int = 120,
) -> list[dict]:
    """getSeries — metadados de serie (inclui licenca, contagem de imagens, fabricante)."""
    params = {"Collection": collection}
    if patient_id:
        params["PatientID"] = patient_id
    if modality:
        params["Modality"] = modality
    url = f"{BASE}/getSeries?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (host fixo, https)
        return json.load(r)


def baixar_serie(serie: dict, destino: Path, timeout: int = 900) -> Path:
    """getImage — baixa e extrai a serie em `destino`. Nao rebaixa o que ja esta la.

    `serie` e o dict devolvido por `listar_series` (precisa de SeriesInstanceUID);
    ele inteiro e gravado como marcador de cache e prova de licenca.
    """
    destino = Path(destino)
    marcador = destino / MARCADOR
    if marcador.exists():
        return destino

    uid = serie["SeriesInstanceUID"]
    url = f"{BASE}/getImage?{urllib.parse.urlencode({'SeriesInstanceUID': uid})}"
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (host fixo, https)
        bruto = r.read()

    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(bruto)) as z:
        z.extractall(destino)  # ZipFile remove componentes ".." dos nomes
    marcador.write_text(json.dumps(serie, indent=2, ensure_ascii=False), encoding="utf-8")
    return destino


def licenca(serie: dict) -> dict:
    """Bloco de licenca LIDO da API (nunca digitado a mao)."""
    return {
        "nome": serie.get("LicenseName"),
        "uri": serie.get("LicenseURI"),
        "collection_uri": serie.get("CollectionURI"),
    }
