"""Varredura shard 3 — lado NBIA: o que o indice do IDC nao da.

Duas coisas so existem abrindo o arquivo:
  (a) colecao AUSENTE do IDC (ARAR0331, CALGB50303, FDG-PET-CT-Lesions);
  (b) SegmentLabel dos SEG — o indice do IDC guarda o CodeMeaning, nao o rotulo
      livre, e e no rotulo livre que moraria 'Obs1'/'Obs2'.

Cada colecao vira um JSON proprio; cobertura declarada em todas.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from scripts.validation.tier2 import interobservador as I  # noqa: E402

DL = RAIZ / ".clinica-dados/fase11/varredura/dl"
OUT = RAIZ / ".clinica-dados/fase11/varredura/nbia"

# (colecao, k) — k=None significa UNIAO COMPLETA
PLANO = [
    # prioridade do critico / ausentes do IDC
    ("QIBA CT-1C", None),
    ("CT4Harmonization-Multicentric", 120),
    ("ARAR0331", 400),
    ("CALGB50303", 400),
    ("FDG-PET-CT-Lesions", 200),
    # RTSTRUCT (IDC ja deu 100% dos ROIName; aqui e conferencia + referencias)
    ("CC-Radiomics-Phantom", None),
    ("Soft-tissue-Sarcoma", 60),
    ("CPTAC-PDA", 60),
    ("CPTAC-CCRCC", 60),
    ("Prostate-Anatomical-Edge-Cases", 40),
    # SEG — SegmentLabel so sai do arquivo
    ("Adrenal-ACC-Ki67-Seg", None),
    ("Lung Phantom", None),
    ("CT-Phantom4Radiomics", 60),
    ("RIDER Lung CT", 100),
    ("NLST", 80),
    ("PSMA-PET-CT-Lesions", 60),
    ("PROSTATEx", 40),
    ("Duke-Breast-Cancer-MRI", 40),
    ("ACRIN-6698", 60),
    ("ISPY1", 60),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for nome, k in PLANO:
        destino = OUT / (I._slug(nome) + ".json")
        if destino.exists():
            print("ja existe, pulando:", nome, flush=True)
            continue
        t = time.time()
        try:
            reg = I.censo_colecao(
                nome, k=k or I.K_CONTORNOS, raiz=DL, completo=(k is None))
        except Exception as e:  # noqa: BLE001 — colecao quebrada nao derruba o lote
            reg = {"colecao": nome, "erro": f"{type(e).__name__}: {e}"}
        reg["segundos"] = round(time.time() - t, 1)
        destino.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
        cob = reg.get("cobertura", {})
        print(f"{nome:34s} {reg['segundos']:7.1f}s lidos={cob.get('lidos')}/"
              f"{cob.get('total_de_contornos_na_colecao')} "
              f"ok={cob.get('lidos_com_sucesso')} -> {reg.get('veredito_instrumento')}",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
