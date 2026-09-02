"""
Etapa 2 — TotalSegmentator (nnU-Net pré-treinado; inferência, NUNCA treino).

- Tarefa `total` (v2): rotula 117 estruturas; o coração vem como UM rótulo
  (`heart`) + aorta, veia pulmonar, tronco braquiocefálico, cava superior,
  aurícula esquerda. Câmaras/miocárdio só na tarefa `heartchambers_highres`,
  que exige licença acadêmica gratuita (totalseg_set_license).
- `roi_subset` só vale para `total` (python_api 2.18): tarefas extras rodam
  em chamada própria, numa subpasta.
- Grava masks/segmentacao.json (versão, tarefa, tempo) — rastreabilidade
  exigida pelo PROMPT-CLINICA, mesmo quando as máscaras são reusadas depois.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# Presets de estruturas (nomes do TotalSegmentator, tarefa "total"). Uma malha
# POR estrutura, nome preservado — contrato do VRmed (detectStructures).
PRESETS: dict[str, list[str] | None] = {
    "torax": [
        "lung_upper_lobe_left",
        "lung_lower_lobe_left",
        "lung_upper_lobe_right",
        "lung_middle_lobe_right",
        "lung_lower_lobe_right",
        "heart",
        "aorta",
        "trachea",
        "esophagus",
    ],
    # Angiotomografia cardíaca: coração inteiro + grandes vasos que a tarefa
    # `total` entrega sem licença; pulmões/traqueia/esôfago dão contexto.
    "cardiaco": [
        "heart",
        "atrial_appendage_left",
        "aorta",
        "pulmonary_vein",
        "brachiocephalic_trunk",
        "superior_vena_cava",
        "inferior_vena_cava",
        "lung_upper_lobe_left",
        "lung_lower_lobe_left",
        "lung_upper_lobe_right",
        "lung_middle_lobe_right",
        "lung_lower_lobe_right",
        "trachea",
        "esophagus",
    ],
    "abdomen": [
        "liver",
        "spleen",
        "kidney_left",
        "kidney_right",
        "gallbladder",
        "pancreas",
        "stomach",
        "aorta",
        "inferior_vena_cava",
    ],
    # None = todas as estruturas da tarefa "total" (pesado; use com cuidado)
    "completo": None,
}

class LicencaAusente(RuntimeError):
    """Tarefa comercial do TotalSegmentator sem licença acadêmica configurada."""


def rodar_segmentacao(
    entrada: Path,
    saida_masks: Path,
    estruturas: list[str] | None = None,
    fast: bool = False,
    task: str = "total",
    log=print,
) -> dict:
    """Roda o TotalSegmentator e devolve {tarefa, tempo_s, versão…} (também
    gravado em saida_masks/segmentacao.json)."""
    from importlib.metadata import version

    from totalsegmentator.config import has_valid_license_offline
    from totalsegmentator.python_api import totalsegmentator as segmentar
    from totalsegmentator.registry import requires_license

    # A MESMA checagem que a lib faz em get_task_config (18 tarefas comerciais,
    # config em TOTALSEG_HOME_DIR) — só que lá ela termina em sys.exit(1) no
    # meio do run; aqui vira exceção que o CLI trata como "tarefa pulada".
    if requires_license(task) and has_valid_license_offline()[0] != "yes":
        raise LicencaAusente(
            f"a tarefa {task} exige licença acadêmica do TotalSegmentator "
            "(gratuita: https://backend.totalsegmentator.com/license-academic/ → "
            "totalseg_set_license -l aca_…)"
        )
    if task != "total":
        estruturas = None  # roi_subset só existe na tarefa total
        if fast:
            # Toda tarefa extra do 2.18 (exceto lung_vessels/body) tem
            # disallow_fast — a API levantaria ValueError depois do run total.
            log(f"AVISO: --fast só vale para a tarefa total; {task} roda em resolução cheia")
            fast = False

    log(
        f"segmentando {entrada.name} — tarefa {task}, "
        f"{'todas as estruturas' if estruturas is None else f'{len(estruturas)} estruturas'}"
        f"{', modo rápido 3 mm' if fast else ''}…"
    )
    inicio = time.time()
    saida_masks.mkdir(parents=True, exist_ok=True)
    segmentar(
        str(entrada),
        str(saida_masks),
        task=task,
        roi_subset=estruturas,
        fast=fast,
        quiet=False,
    )
    info = {
        "tarefa": task,
        "estruturas": estruturas,
        "fast": fast,
        "tempo_s": round(time.time() - inicio, 1),
        # O pacote não expõe __version__; a metadata da distribuição sim.
        "totalsegmentator_versao": version("TotalSegmentator"),
    }
    (saida_masks / "segmentacao.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return info


def info_segmentacao(masks_dir: Path) -> dict | None:
    """Lê o segmentacao.json de máscaras reusadas (para o relatório)."""
    try:
        return json.loads((masks_dir / "segmentacao.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
