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

# 'commercial': True no map_tasks_config do TotalSegmentator → licença
# acadêmica gratuita em https://backend.totalsegmentator.com/license-academic/
TAREFAS_COM_LICENCA = {"heartchambers_highres", "coronary_arteries"}


class LicencaAusente(RuntimeError):
    pass


def licenca_configurada() -> bool:
    config = Path.home() / ".totalsegmentator" / "config.json"
    try:
        return bool(json.loads(config.read_text(encoding="utf-8")).get("license_number"))
    except (OSError, ValueError):
        return False


def validar_estruturas(nomes: list[str]) -> tuple[list[str], list[str]]:
    """Separa nomes válidos na tarefa `total` instalada dos desconhecidos."""
    from totalsegmentator.map_to_binary import class_map

    validos = set(class_map["total"].values())
    ok = [n for n in nomes if n in validos]
    return ok, [n for n in nomes if n not in validos]


def rodar_segmentacao(
    entrada: Path,
    saida_masks: Path,
    estruturas: list[str] | None = None,
    fast: bool = False,
    task: str = "total",
    device: str = "gpu",
    log=print,
) -> dict:
    """Roda o TotalSegmentator e devolve {tarefa, tempo_s, versão…} (também
    gravado em saida_masks/segmentacao.json)."""
    from importlib.metadata import version

    from totalsegmentator.python_api import totalsegmentator as segmentar

    if task in TAREFAS_COM_LICENCA and not licenca_configurada():
        raise LicencaAusente(
            f"a tarefa {task} exige licença acadêmica do TotalSegmentator "
            "(gratuita: https://backend.totalsegmentator.com/license-academic/ → "
            "totalseg_set_license -l aca_…)"
        )
    if task != "total":
        estruturas = None  # roi_subset só existe na tarefa total
    elif estruturas is not None:
        estruturas, desconhecidas = validar_estruturas(estruturas)
        if desconhecidas:
            log(f"AVISO: estruturas fora da tarefa total, ignoradas: {', '.join(desconhecidas)}")

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
        device=device,
        quiet=False,
    )
    info = {
        "tarefa": task,
        "estruturas": estruturas,
        "fast": fast,
        "device": device,
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
