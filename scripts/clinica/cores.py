"""Cores didáticas por estrutura (RGB 0–1) — usadas no GLB e nos PNGs de QA."""

from __future__ import annotations

# Aproximação didática, não convenção clínica. Os lobos pulmonares têm tons
# DISTINTOS de propósito: as fissuras entre eles são anatomia real, e com uma
# cor só pareciam rachadura de defeito.
CORES: list[tuple[str, tuple[float, float, float]]] = [
    ("lung_upper_lobe_left", (0.89, 0.58, 0.58)),
    ("lung_lower_lobe_left", (0.78, 0.47, 0.50)),
    ("lung_upper_lobe_right", (0.91, 0.64, 0.55)),
    ("lung_middle_lobe_right", (0.83, 0.52, 0.44)),
    ("lung_lower_lobe_right", (0.74, 0.42, 0.44)),
    ("lung", (0.85, 0.55, 0.55)),
    # heartchambers_highres: câmaras esquerdas em vermelhos, direitas em azuis —
    # antes do prefixo "heart", senão as cinco saem iguais e o QA vira monocromático.
    ("heart_myocardium", (0.60, 0.20, 0.18)),
    ("heart_atrium_left", (0.90, 0.45, 0.40)),
    ("heart_ventricle_left", (0.78, 0.30, 0.26)),
    ("heart_atrium_right", (0.55, 0.40, 0.72)),
    ("heart_ventricle_right", (0.40, 0.35, 0.68)),
    ("heart", (0.72, 0.25, 0.22)),
    ("atrial_appendage", (0.85, 0.35, 0.30)),
    ("aorta", (0.80, 0.20, 0.20)),
    ("pulmonary_vein", (0.45, 0.35, 0.70)),
    ("pulmonary_artery", (0.35, 0.40, 0.75)),
    ("pulmonary", (0.55, 0.30, 0.55)),
    ("brachiocephalic", (0.75, 0.45, 0.30)),
    ("superior_vena_cava", (0.30, 0.40, 0.70)),
    ("trachea", (0.85, 0.83, 0.75)),
    ("esophagus", (0.76, 0.60, 0.48)),
    ("liver", (0.55, 0.27, 0.17)),
    ("spleen", (0.45, 0.18, 0.25)),
    ("kidney", (0.58, 0.32, 0.28)),
    ("gallbladder", (0.35, 0.52, 0.30)),
    ("pancreas", (0.85, 0.72, 0.50)),
    ("stomach", (0.83, 0.65, 0.58)),
    ("inferior_vena_cava", (0.25, 0.35, 0.65)),
]
COR_PADRAO = (0.75, 0.72, 0.68)


def cor_para(nome: str) -> tuple[float, float, float]:
    for prefixo, cor in CORES:
        if nome.startswith(prefixo):
            return cor
    return COR_PADRAO
