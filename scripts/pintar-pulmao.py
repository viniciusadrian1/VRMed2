# -*- coding: utf-8 -*-
"""
pintar-pulmao.py — gera o GLB PERSONALIZADO do paciente: pega o modelo
ilustrativo de pulmão (bonito, do modo Estudo) e pinta a TEXTURA dele com os
achados medidos na TC (saída do achados-pulmao.py).

O que pinta (tudo determinístico, dirigido pelos números do exame):
  * Manchas escuras nas posições das opacidades encontradas, com o diâmetro
    real convertido para a escala do modelo (multiplicação sobre a textura,
    preservando o detalhe por baixo — parece tecido, não adesivo).
  * Escurecimento global + mosqueado (antracose) proporcional ao %% de
    enfisema medido (LAA-950). Pulmão sadio quase não muda; DPOC grave
    escurece visivelmente.

Nada é inventado: sem exame, sem mancha. IA generativa segue proibida.

Uso (o modelo precisa estar SEM Draco — gere uma vez com:
  npx gltf-transform copy public/models/healthy/pulmao.glb .clinica-dados/pulmao-sem-draco.glb):

  python scripts/pintar-pulmao.py \
      --achados public/pacientes/torax-alta-achados.json \
      --modelo .clinica-dados/pulmao-sem-draco.glb \
      --output .clinica-dados/torax-alta-mapa.glb
Depois: npx gltf-transform draco <saida> public/pacientes/<slug>-mapa.glb
"""

import argparse
import json

import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage

# Mesma convenção do MapaAchados.tsx: paciente -X = esquerda, -Z = anterior;
# modelo ilustrativo de frente para +Z em posição anatômica → inverte X e Z.
FLIP_X = True
FLIP_Z = True

COR_MANCHA = np.array([0.38, 0.27, 0.28])   # multiplicador: marrom-acinzentado
FORCA_MANCHA = 0.85
COR_FUMO = np.array([0.45, 0.42, 0.44])     # antracose: cinza-escuro


def achar_malha_pulmoes(cena: trimesh.Scene) -> tuple[str, trimesh.Trimesh]:
    """A malha dos pulmões é a mais larga em X (a outra é traqueia/tireoide)."""
    return max(
        cena.geometry.items(),
        key=lambda item: item[1].bounds[1][0] - item[1].bounds[0][0],
    )


def uv_e_escala_das_lesoes(
    malha: trimesh.Trimesh, lesoes: list[dict], escala_por_mm: float
) -> list[tuple[np.ndarray, float]]:
    """Para cada lesão: (uv do ponto mais próximo na superfície, raio em fração de UV)."""
    bb_min, bb_max = malha.bounds
    tam = bb_max - bb_min
    pontos = []
    for lesao in lesoes:
        px, py, pz = lesao["posNorm"]
        pontos.append([
            bb_min[0] + ((1 - px) if FLIP_X else px) * tam[0],
            bb_min[1] + py * tam[1],
            bb_min[2] + ((1 - pz) if FLIP_Z else pz) * tam[2],
        ])
    pontos = np.array(pontos)
    perto, _, tri_ids = trimesh.proximity.closest_point(malha, pontos)
    bary = trimesh.triangles.points_to_barycentric(
        malha.triangles[tri_ids], perto
    )
    uvs_verts = malha.visual.uv[malha.faces[tri_ids]]          # (n, 3, 2)
    uvs = np.einsum("nij,ni->nj", uvs_verts, bary)

    saida = []
    for i, lesao in enumerate(lesoes):
        # Densidade local de texels: relação entre áreas UV e 3D do triângulo.
        tri3d = malha.triangles[tri_ids[i]]
        area3d = trimesh.triangles.area(tri3d[None, :, :])[0]
        uv_tri = uvs_verts[i]
        e1, e2 = uv_tri[1] - uv_tri[0], uv_tri[2] - uv_tri[0]
        area_uv = 0.5 * abs(e1[0] * e2[1] - e1[1] * e2[0])
        uv_por_unidade = np.sqrt(max(area_uv, 1e-12) / max(area3d, 1e-12))
        raio_uv = (lesao["diametroMm"] / 2) * escala_por_mm * uv_por_unidade
        saida.append((uvs[i] % 1.0, float(raio_uv)))
    return saida


def pintar(textura: Image.Image, manchas, enfisema_pct: float,
           semente: int) -> Image.Image:
    img = np.asarray(textura.convert("RGB"), dtype=np.float32) / 255.0
    alt, larg = img.shape[:2]
    rng = np.random.default_rng(semente)

    # --- Fumante: escurecimento global + mosqueado, proporcional ao enfisema.
    grav = min(enfisema_pct, 30.0) / 30.0
    if grav > 0.003:
        ruido = rng.random((alt // 8, larg // 8)).astype(np.float32)
        ruido = ndimage.zoom(ndimage.gaussian_filter(ruido, 3), 8, order=1)
        ruido = (ruido - ruido.min()) / max(np.ptp(ruido), 1e-6)
        a = (0.25 + 0.75 * ruido[:alt, :larg]) * grav * 0.9
        img *= 1 - a[..., None] * (1 - COR_FUMO)

    # --- Manchas focais (opacidades medidas na TC).
    for (u, v), raio_uv in manchas:
        raio_px = max(int(raio_uv * larg), 6)
        # trimesh usa V com origem embaixo; a linha da imagem é (1 - v).
        cx, cy = int(u * larg), int((1 - v) * alt)
        r2 = raio_px * 2
        y0, y1 = max(cy - r2, 0), min(cy + r2, alt)
        x0, x1 = max(cx - r2, 0), min(cx + r2, larg)
        if y0 >= y1 or x0 >= x1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (raio_px ** 2)
        queda = np.exp(-d2 * 1.8).astype(np.float32)
        # Borda irregular: modula a queda com ruído suave (mancha, não círculo).
        irr = rng.random((y1 - y0, x1 - x0)).astype(np.float32)
        irr = ndimage.gaussian_filter(irr, raio_px / 3 + 1)
        irr = (irr - irr.min()) / max(np.ptp(irr), 1e-6)
        a = np.clip(queda * (0.55 + 0.65 * irr) * FORCA_MANCHA, 0, 1)
        img[y0:y1, x0:x1] *= 1 - a[..., None] * (1 - COR_MANCHA)

    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--achados", required=True)
    ap.add_argument("--modelo", required=True, help="GLB ilustrativo SEM Draco")
    ap.add_argument("--output", required=True)
    ap.add_argument("--semente", type=int, default=7,
                    help="semente do ruído (reprodutível)")
    args = ap.parse_args()

    achados = json.loads(open(args.achados, encoding="utf-8").read())
    cena = trimesh.load(args.modelo)
    nome, pulmoes = achar_malha_pulmoes(cena)

    tam_y = pulmoes.bounds[1][1] - pulmoes.bounds[0][1]
    escala_por_mm = tam_y / achados["bboxMm"][1]

    manchas = uv_e_escala_das_lesoes(pulmoes, achados["lesoes"], escala_por_mm)
    textura = pulmoes.visual.material.baseColorTexture
    pulmoes.visual.material.baseColorTexture = pintar(
        textura, manchas, achados["enfisemaPctTotal"], args.semente
    )

    cena.export(args.output)
    print(f"[pintar-pulmao] {len(manchas)} manchas + enfisema "
          f"{achados['enfisemaPctTotal']}% pintados em '{nome[-30:]}' -> {args.output}")
    print("[pintar-pulmao] agora: npx gltf-transform draco "
          f"{args.output} public/pacientes/<slug>-mapa.glb")


if __name__ == "__main__":
    main()
