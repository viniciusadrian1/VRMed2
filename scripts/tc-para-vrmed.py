#!/usr/bin/env python
"""
tc-para-vrmed — transforma uma tomografia (DICOM ou NIfTI) num GLB de malhas
NOMEADAS pronto para o VRmed Clínica.

Pipeline (PROMPT-CLINICA.md, Fase 1):
  TC → TotalSegmentator (inferência, nunca treino) → máscaras por estrutura
     → marching cubes → suavização → decimação até o orçamento → GLB nomeado

Uso:
  python scripts/tc-para-vrmed.py --input exame.nii.gz --output paciente.glb \
      --structures torax --max-tris 120000 --report paciente.json [--fast]

O GLB sai em metros, eixo Y para cima (rotação RAS→glTF sem espelhamento —
espelhar trocaria esquerda/direita do paciente, erro médico inaceitável).
Depois rode: npx gltf-transform draco paciente.glb paciente.min.glb
(APENAS Draco; --simplify destrói anatomia — regra do projeto.)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import trimesh
from skimage import measure

# ---------------------------------------------------------------------------
# Presets de estruturas (nomes do TotalSegmentator, tarefa "total").
# Uma malha POR estrutura, com o nome preservado — é o contrato do VRmed
# (detectStructures/identifyStructure identificam pelo nome do nó).
# ---------------------------------------------------------------------------
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

# Rotação RAS→glTF: (x, y, z) → (x, z, -y). Determinante +1 (rotação pura,
# sem espelhar) — anterior do paciente aponta para -Z, superior para +Y.
RAS_PARA_GLTF = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
    ]
)
MM_PARA_M = 0.001

# Cores anatômicas (RGB 0–1) por prefixo de estrutura — aproximação didática,
# não convenção clínica. Sem isso o GLB sai cinza uniforme.
CORES: list[tuple[str, tuple[float, float, float]]] = [
    ("lung", (0.87, 0.62, 0.62)),
    ("heart", (0.72, 0.25, 0.22)),
    ("aorta", (0.80, 0.20, 0.20)),
    ("pulmonary", (0.55, 0.30, 0.55)),
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


def log(msg: str) -> None:
    print(f"[tc-para-vrmed] {msg}", flush=True)


def rodar_segmentacao(
    entrada: Path, saida_masks: Path, estruturas: list[str] | None, fast: bool
) -> float:
    """Roda o TotalSegmentator (inferência) e devolve o tempo gasto."""
    from totalsegmentator.python_api import totalsegmentator

    inicio = time.time()
    log(
        f"segmentando {entrada.name} "
        f"({'todas as estruturas' if estruturas is None else f'{len(estruturas)} estruturas'}"
        f"{', modo rápido' if fast else ''})…"
    )
    totalsegmentator(
        str(entrada),
        str(saida_masks),
        roi_subset=estruturas,
        fast=fast,
        quiet=False,
    )
    return time.time() - inicio


def mascara_para_malha(
    caminho_mask: Path, orcamento_tris: int
) -> tuple[trimesh.Trimesh, dict] | None:
    """Converte uma máscara NIfTI numa malha suavizada e decimada."""
    img = nib.load(str(caminho_mask))
    volume = np.asarray(img.dataobj) > 0.5
    if volume.sum() < 50:  # estrutura ausente ou ruído
        return None

    # Marching cubes no espaço de voxels; o affine leva para mm em RAS.
    verts, faces, _normals, _values = measure.marching_cubes(
        volume.astype(np.uint8), level=0.5
    )
    affine = img.affine
    verts_mm = verts @ affine[:3, :3].T + affine[:3, 3]
    verts_gltf = (verts_mm @ RAS_PARA_GLTF.T) * MM_PARA_M

    malha = trimesh.Trimesh(vertices=verts_gltf, faces=faces, process=True)
    tris_brutos = len(malha.faces)

    # Suavização leve tira o "degrau" de voxel sem derreter o detalhe.
    trimesh.smoothing.filter_taubin(malha, lamb=0.5, nu=-0.53, iterations=8)

    # Decimação controlada (regra do projeto: NUNCA o --simplify do
    # gltf-transform em anatomia — aqui controlamos o alvo por estrutura).
    if len(malha.faces) > orcamento_tris:
        import fast_simplification

        verts_d, faces_d = fast_simplification.simplify(
            malha.vertices.astype(np.float32),
            malha.faces.astype(np.int64),
            target_count=orcamento_tris,
        )
        malha = trimesh.Trimesh(vertices=verts_d, faces=faces_d, process=True)

    info = {
        "triangulos_brutos": int(tris_brutos),
        "triangulos_finais": int(len(malha.faces)),
        "componentes": int(len(malha.split(only_watertight=False))),
    }
    return malha, info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="pasta DICOM ou arquivo .nii/.nii.gz")
    parser.add_argument("--output", required=True, help="GLB de saída")
    parser.add_argument("--structures", default="torax", choices=list(PRESETS))
    parser.add_argument("--max-tris", type=int, default=120_000)
    parser.add_argument("--report", default=None, help="JSON de relatório")
    parser.add_argument("--fast", action="store_true", help="modo rápido (3mm) — bom para CPU")
    parser.add_argument(
        "--masks-dir",
        default=None,
        help="reusa máscaras já segmentadas (pula o TotalSegmentator)",
    )
    args = parser.parse_args()

    entrada = Path(args.input)
    saida = Path(args.output)
    if not entrada.exists():
        log(f"ERRO: entrada não existe: {entrada}")
        return 1

    estruturas = PRESETS[args.structures]
    relatorio: dict = {
        "entrada": str(entrada),
        "preset": args.structures,
        "fast": args.fast,
        "etapas_s": {},
        "estruturas": {},
    }

    # ----- 1. Segmentação (ou reuso) -----
    if args.masks_dir:
        masks_dir = Path(args.masks_dir)
        log(f"reusando máscaras de {masks_dir}")
    else:
        # Máscaras são intermediário volumoso: ficam FORA de public/ (nunca
        # devem ir para o site nem para o git).
        masks_dir = Path(".clinica-dados") / (saida.stem + "_masks")
        masks_dir.mkdir(parents=True, exist_ok=True)
        relatorio["etapas_s"]["segmentacao"] = round(
            rodar_segmentacao(entrada, masks_dir, estruturas, args.fast), 1
        )
        try:
            import totalsegmentator

            relatorio["totalsegmentator_versao"] = totalsegmentator.__version__
        except Exception:
            pass

    mascaras = sorted(masks_dir.glob("*.nii.gz"))
    if estruturas is not None:
        mascaras = [m for m in mascaras if m.name.removesuffix(".nii.gz") in estruturas]
    if not mascaras:
        log(f"ERRO: nenhuma máscara encontrada em {masks_dir}")
        return 1
    log(f"{len(mascaras)} máscaras para converter")

    # ----- 2. Máscaras → malhas -----
    inicio = time.time()
    # Orçamento por estrutura: proporcional, com piso para não pulverizar
    # estruturas pequenas (mínimo 2k triângulos cada).
    por_estrutura = max(2_000, args.max_tris // max(1, len(mascaras)))

    cena = trimesh.Scene()
    total_tris = 0
    for caminho in mascaras:
        nome = caminho.name.removesuffix(".nii.gz")
        resultado = mascara_para_malha(caminho, por_estrutura)
        if resultado is None:
            log(f"  - {nome}: vazia no exame, pulando")
            relatorio["estruturas"][nome] = {"presente": False}
            continue
        malha, info = resultado
        r, g, b = cor_para(nome)
        malha.visual = trimesh.visual.texture.TextureVisuals(
            material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=(r, g, b, 1.0),
                metallicFactor=0.05,
                roughnessFactor=0.65,
            )
        )
        cena.add_geometry(malha, node_name=nome, geom_name=nome)
        total_tris += info["triangulos_finais"]
        relatorio["estruturas"][nome] = {"presente": True, **info}
        log(f"  + {nome}: {info['triangulos_finais']} tris")

    relatorio["etapas_s"]["malhas"] = round(time.time() - inicio, 1)
    relatorio["triangulos_total"] = total_tris

    if total_tris == 0:
        log("ERRO: nenhuma estrutura gerou malha — o exame cobre a região do preset?")
        return 1
    if total_tris > 150_000:
        log(f"AVISO: {total_tris} tris > orçamento VR (150k). Reduza --max-tris.")

    # ----- 3. Exporta GLB -----
    saida.parent.mkdir(parents=True, exist_ok=True)
    cena.export(str(saida))
    tamanho_mb = saida.stat().st_size / 1_048_576
    relatorio["glb"] = {"arquivo": str(saida), "mb": round(tamanho_mb, 2)}
    log(f"GLB: {saida} ({tamanho_mb:.1f} MB, {total_tris} tris)")
    log("Agora comprima: npx gltf-transform draco "
        f"{saida} {saida.with_suffix('')}.min.glb  (SEM --simplify!)")

    # ----- 4. Relatório -----
    if args.report:
        Path(args.report).write_text(
            json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log(f"relatório: {args.report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
