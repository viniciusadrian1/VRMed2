"""Grava as tres medidas de cada candidato da Fase 11-B em fichas/_medida/.

  censo   — agregado da API do TCIA (getSeries da colecao inteira)
  idc     — cruzamento com o indice do IDC v24.2.2 (cobertura de nome de ROI)
  rotulos — SegmentLabel/ROIName LIDOS DOS ARQUIVOS ja baixados

A ficha JSON cita estes arquivos; os numeros nao sao digitados a mao.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.validation.tier2 import fichas_fase11b as M
from scripts.validation.tier2 import fichas_fase11b_idc as I
from scripts.validation.tier2 import fichas_fase11b_rotulos as R

RAIZ = Path(__file__).resolve().parents[3]
OUT = RAIZ / ".clinica-dados/fase11/fichas/_medida"
VAR = RAIZ / ".clinica-dados/fase11/varredura"

# colecao -> diretorio ja baixado onde estao os arquivos de contorno
ARVORES = {
    "Pediatric-CT-SEG": RAIZ / ".clinica-dados/fase11/fichas/_dl/Pediatric-CT-SEG",
    "Mediastinal-Lymph-Node-SEG": VAR / "dl/Mediastinal-Lymph-Node-SEG",
    "CT4Harmonization-Multicentric": VAR / "dl/CT4Harmonization-Multicentric",
    "NSCLC Radiogenomics": VAR / "dl/NSCLC_Radiogenomics",
    "Spine-Mets-CT-SEG": VAR / "Spine-Mets-CT-SEG",
    "QIBA CT-1C": VAR / "dl/QIBA_CT-1C",
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for col, arvore in ARVORES.items():
        slug = col.replace(" ", "_")
        for nome, fn in (("censo", lambda: M.censo(col)),
                         ("idc", lambda: I.cruzar(col)),
                         ("rotulos", lambda: R.varrer(arvore))):
            destino = OUT / f"{slug}_{nome}.json"
            if destino.exists():
                continue
            destino.write_text(json.dumps(fn(), ensure_ascii=False, indent=1), encoding="utf-8")
            print("gravado", destino.name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
