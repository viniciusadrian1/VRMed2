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

# Etapas 1–2 e cores vivem no pacote scripts/clinica (também usado por
# preparar-caso.py e, na Fase 3, pelo worker). O hífen no nome deste
# arquivo impede importá-lo, por isso o pacote.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clinica.cores import cor_para  # noqa: E402
from clinica.segmentacao import PRESETS, info_segmentacao, rodar_segmentacao  # noqa: E402

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

def log(msg: str) -> None:
    print(f"[tc-para-vrmed] {msg}", flush=True)


def malha_de_volume(
    volume: np.ndarray, affine: np.ndarray
) -> tuple[trimesh.Trimesh, int] | None:
    """Volume binário → malha suavizada (ainda sem decimação)."""
    from scipy import ndimage

    if volume.sum() < 50:  # estrutura ausente ou ruído
        return None

    # Suaviza a MÁSCARA antes do marching cubes. As fatias de TC costumam ser
    # grossas (ex.: 2,5mm contra 0,76mm no plano) e a superfície sai em
    # "degraus" — o filtro gaussiano em mm (anisotrópico por eixo) remove o
    # serrilhado na origem, o que nenhuma suavização de malha alcança depois.
    espacamento = np.abs(np.diag(affine)[:3])
    sigma_voxels = 1.3 / np.maximum(espacamento, 1e-6)  # ~1,3mm de sigma
    campo = ndimage.gaussian_filter(volume.astype(np.float32), sigma=sigma_voxels)

    # Nível ACIMA de 0,5 de propósito: encolhe cada superfície uma fração de
    # milímetro. Estruturas vizinhas (coração e aorta; os lobos, quando não
    # unidos) compartilham a fronteira exata — extraídas em 0,5 elas saem
    # coplanares e uma FURA a outra, aparecendo como linhas finas claras.
    verts, faces, _normals, _values = measure.marching_cubes(campo, level=0.56)
    verts_mm = verts @ affine[:3, :3].T + affine[:3, 3]
    verts_gltf = (verts_mm @ RAS_PARA_GLTF.T) * MM_PARA_M

    malha = trimesh.Trimesh(vertices=verts_gltf, faces=faces, process=True)
    tris_brutos = len(malha.faces)

    # Retoque leve pós-marching (o grosso do serrilhado já saiu na máscara).
    trimesh.smoothing.filter_taubin(malha, lamb=0.5, nu=-0.53, iterations=5)
    return malha, tris_brutos


def extrair_malha_bruta(caminho_mask: Path) -> tuple[trimesh.Trimesh, int] | None:
    """Máscara NIfTI → malha suavizada (ainda sem decimação)."""
    img = nib.load(str(caminho_mask))
    return malha_de_volume(np.asarray(img.dataobj) > 0.5, img.affine)


# Rampa de cor por densidade (HU) para o parênquima pulmonar: ar → rosa claro,
# tecido denso (vasos, opacidades) → vinho escuro. A "textura" da superfície
# vem do PRÓPRIO exame do paciente — nada é inventado.
RAMPA_HU_PONTOS = np.array([-950.0, -800.0, -600.0, -300.0, 100.0])
RAMPA_HU_CORES = np.array(
    [
        [0.93, 0.72, 0.70],
        [0.86, 0.57, 0.55],
        [0.74, 0.42, 0.43],
        [0.55, 0.26, 0.29],
        [0.40, 0.18, 0.20],
    ]
)


def preparar_ct(caminho_ct: Path) -> tuple[np.ndarray, np.ndarray]:
    """CT suavizada + inversa do affine, para amostrar HU nos vértices."""
    from scipy import ndimage

    img = nib.load(str(caminho_ct))
    vol = ndimage.gaussian_filter(np.asarray(img.dataobj, dtype=np.float32), 1.2)
    return vol, np.linalg.inv(img.affine)


def amostrar_hu(
    malha: trimesh.Trimesh, vol: np.ndarray, inv_affine: np.ndarray
) -> np.ndarray:
    """HU médio ~2mm PARA DENTRO da superfície em cada vértice (subsuperfície)."""
    from scipy import ndimage

    pontos = malha.vertices - malha.vertex_normals * 0.003
    mm = (pontos / MM_PARA_M) @ RAS_PARA_GLTF  # inversa da rotação = transposta
    vox = mm @ inv_affine[:3, :3].T + inv_affine[:3, 3]
    hu = ndimage.map_coordinates(vol, vox.T, order=1, mode="nearest")
    if np.median(hu) > -500:
        log("AVISO: HU subsuperficial alto — normais invertidas? (fix_normals)")
    return hu


def pintar_vertices(
    malha: trimesh.Trimesh,
    nome: str,
    ct: tuple[np.ndarray, np.ndarray] | None,
) -> None:
    """Cor por vértice: densidade real (pulmões) ou cor didática, ambas
    moduladas por oclusão de cavidade — vincos escuros dão leitura orgânica,
    matando o aspecto de plástico chapado."""
    lap = trimesh.smoothing.laplacian_calculation(malha, equal_weight=True)
    delta = lap.dot(malha.vertices) - malha.vertices
    concavidade = np.einsum("ij,ij->i", delta, malha.vertex_normals)
    escala = np.percentile(np.abs(concavidade), 90) + 1e-12
    cavidade = 1.0 - 0.5 * np.clip(concavidade / (1.5 * escala), 0.0, 1.0)

    if ct is not None and nome.startswith("lung"):
        hu = amostrar_hu(malha, *ct)
        cor = np.stack(
            [np.interp(hu, RAMPA_HU_PONTOS, RAMPA_HU_CORES[:, c]) for c in range(3)],
            axis=1,
        )
    else:
        cor = np.tile(cor_para(nome), (len(malha.vertices), 1))

    rgb = np.clip(cor * cavidade[:, None], 0.0, 1.0)
    rgba = np.hstack([rgb, np.ones((len(rgb), 1))])
    malha.visual = trimesh.visual.ColorVisuals(
        malha, vertex_colors=(rgba * 255).astype(np.uint8)
    )


def decimar(malha: trimesh.Trimesh, orcamento_tris: int) -> trimesh.Trimesh:
    """Decimação controlada (regra do projeto: nunca o --simplify do
    gltf-transform em anatomia — o alvo é decidido por estrutura, aqui)."""
    if len(malha.faces) <= orcamento_tris:
        return malha
    import fast_simplification

    verts_d, faces_d = fast_simplification.simplify(
        malha.vertices.astype(np.float32),
        malha.faces.astype(np.int64),
        target_count=orcamento_tris,
    )
    return trimesh.Trimesh(vertices=verts_d, faces=faces_d, process=True)


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
    parser.add_argument(
        "--pulmoes-inteiros",
        action="store_true",
        help="une os lobos em pulmão esquerdo/direito (sem linhas de fissura)",
    )
    parser.add_argument(
        "--cores-tc",
        default=None,
        help="CT (.nii.gz) para colorir os pulmões pela densidade real (HU)",
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
        # Rastreabilidade: a versão do TotalSegmentator não pode sumir do
        # relatório só porque as máscaras foram reusadas.
        seg = info_segmentacao(masks_dir)
        if seg:
            relatorio["totalsegmentator_versao"] = seg.get("totalsegmentator_versao")
    else:
        # Máscaras são intermediário volumoso: ficam FORA de public/ (nunca
        # devem ir para o site nem para o git).
        masks_dir = Path(".clinica-dados") / (saida.stem + "_masks")
        masks_dir.mkdir(parents=True, exist_ok=True)
        seg = rodar_segmentacao(entrada, masks_dir, estruturas, args.fast, log=log)
        relatorio["etapas_s"]["segmentacao"] = seg["tempo_s"]
        relatorio["totalsegmentator_versao"] = seg["totalsegmentator_versao"]

    mascaras = sorted(masks_dir.glob("*.nii.gz"))
    if estruturas is not None:
        mascaras = [m for m in mascaras if m.name.removesuffix(".nii.gz") in estruturas]
    if not mascaras:
        log(f"ERRO: nenhuma máscara encontrada em {masks_dir}")
        return 1
    log(f"{len(mascaras)} máscaras para converter")

    # ----- 2. Máscaras → malhas (duas passadas) -----
    inicio = time.time()

    # Passada 1: extrai todas as malhas brutas para conhecer os tamanhos.
    brutas: list[tuple[str, trimesh.Trimesh, int]] = []

    # Pulmões inteiros: une os lobos de cada lado ANTES do marching cubes.
    # As fissuras entre lobos, mesmo com folga, liam-se como defeito ("linhas
    # soltas"); a superfície externa contínua é o que um render clínico mostra.
    if args.pulmoes_inteiros:
        lados = {"lung_left": "_left.nii.gz", "lung_right": "_right.nii.gz"}
        for nome_lado, sufixo in lados.items():
            lobos = [
                m for m in mascaras
                if m.name.startswith("lung_") and m.name.endswith(sufixo)
            ]
            if not lobos:
                continue
            img0 = nib.load(str(lobos[0]))
            uniao = np.zeros(img0.shape, dtype=bool)
            for caminho in lobos:
                uniao |= np.asarray(nib.load(str(caminho)).dataobj) > 0.5
            resultado = malha_de_volume(uniao, img0.affine)
            if resultado is None:
                relatorio["estruturas"][nome_lado] = {"presente": False}
                continue
            brutas.append((nome_lado, *resultado))
        mascaras = [m for m in mascaras if not m.name.startswith("lung_")]

    for caminho in mascaras:
        nome = caminho.name.removesuffix(".nii.gz")
        resultado = extrair_malha_bruta(caminho)
        if resultado is None:
            log(f"  - {nome}: vazia no exame, pulando")
            relatorio["estruturas"][nome] = {"presente": False}
            continue
        brutas.append((nome, *resultado))

    # Passada 2: orçamento PROPORCIONAL ao tamanho real de cada estrutura
    # (um pulmão merece dezenas de vezes mais triângulos que um esôfago;
    # dividir por igual deixava os órgãos grandes facetados), com piso para
    # as pequenas não virarem poliedros.
    total_bruto = sum(tris for _, _, tris in brutas) or 1
    ct = preparar_ct(Path(args.cores_tc)) if args.cores_tc else None
    cena = trimesh.Scene()
    total_tris = 0
    for nome, malha_bruta, tris_brutos in brutas:
        orcamento = max(3_000, round(args.max_tris * tris_brutos / total_bruto))
        malha = decimar(malha_bruta, orcamento)
        # O marching cubes sai com winding/normais para DENTRO — isso inverte
        # a iluminação no three.js e a amostragem de HU. Corrige aqui, na raiz.
        malha.fix_normals(multibody=True)
        pintar_vertices(malha, nome, ct)
        cena.add_geometry(malha, node_name=nome, geom_name=nome)
        info = {
            "triangulos_brutos": int(tris_brutos),
            "triangulos_finais": int(len(malha.faces)),
        }
        total_tris += info["triangulos_finais"]
        relatorio["estruturas"][nome] = {"presente": True, **info}
        log(f"  + {nome}: {info['triangulos_finais']} tris (bruto {tris_brutos})")

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
