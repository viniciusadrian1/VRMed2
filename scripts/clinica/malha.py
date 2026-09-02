"""
Etapa 3a — máscara → malha → cor do próprio exame.

Decisões (docs/CLINICA-FIDELIDADE.md, itens 2, 3, 4, 7 e 8):
- Suavização proporcional ao spacing: σ = max(0,6 mm, 0,5 × maior voxel). Os 1,3 mm fixos de
  antes (pensados para fatias de 2,5 mm) apagavam 17 % da área e 5× o relevo do coração.
- Pad de 1 voxel antes do marching cubes: estrutura cortada pelo campo de visão ganha tampa
  plana em vez de rasgo.
- Nível 0,5 (sem erosão) + afastamento de 0,15 mm para dentro pela normal: preserva paredes
  finas e evita z-fighting entre vizinhas que compartilham fronteira (o nível 0,56 antigo
  erodia até 16 % do volume dos vasos).
- Ilhas < 30 mm³ removidas e buracos fechados ANTES do marching cubes (eram as cascas soltas),
  exceto nas classes que são vários vasos por natureza (veias pulmonares).
- Vasos que entram no coração são dilatados 1 voxel para dentro dele (contato garantido).
- Cor por vértice = cor didática LINEARIZADA (glTF lê COLOR_0 como linear; gravar sRGB deixava
  tudo dessaturado) modulada pelo HU real logo abaixo/acima da superfície, mais oclusão pela
  ocupação da vizinhança. Nada é inventado: toda variação vem do exame ou de regra geométrica.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

from .cores import cor_para

# Rotação RAS→glTF: (x, y, z) → (x, z, -y). Determinante +1 (rotação pura, sem
# espelhar — espelhar trocaria esquerda/direita do paciente).
RAS_PARA_GLTF = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
MM_PARA_M = 0.001

OCRE = (0.83, 0.62, 0.35)  # gordura epicárdica nos sulcos (sRGB)
VERMELHO_CLARO = (0.95, 0.55, 0.50)  # vaso opacificado encostado na superfície (sRGB)

# Rampa de cor por densidade para o parênquima pulmonar (sRGB): ar → rosa
# claro, tecido denso (vasos, opacidades) → vinho escuro.
RAMPA_HU_PONTOS = np.array([-950.0, -800.0, -600.0, -300.0, 100.0])
RAMPA_HU_CORES = np.array(
    [[0.93, 0.72, 0.70], [0.86, 0.57, 0.55], [0.74, 0.42, 0.43], [0.55, 0.26, 0.29], [0.40, 0.18, 0.20]]
)

# Classes em que vários componentes conexos são anatomia, não sujeira.
CLASSES_MULTIPLAS = {"pulmonary_vein"}
# Vasos que terminam no coração: dilatados 1 voxel para dentro do rótulo `heart`.
ENCOSTAM_NO_CORACAO = ("pulmonary_vein", "superior_vena_cava", "inferior_vena_cava", "atrial_appendage_left")
PREFIXOS_SANGUE = (
    "heart_atrium", "heart_ventricle", "aorta", "pulmonary_artery", "pulmonary_vein",
    "superior_vena_cava", "inferior_vena_cava", "brachiocephalic", "subclavian", "common_carotid",
    "atrial_appendage", "iliac", "portal_vein",
)
CAMARAS = (
    "heart_atrium_left", "heart_atrium_right", "heart_ventricle_left", "heart_ventricle_right",
    "heart_myocardium", "pulmonary_artery",
)


def afastamento_de(nome: str) -> float:
    """0,15 mm só nas câmaras/miocárdio (superfícies opacas coincidentes:
    cavidade do VE × face interna do miocárdio). Num vaso de 3 mm o mesmo
    afastamento custava até metade do volume, sem z-fighting a evitar."""
    return 0.15 if nome.startswith("heart_") else 0.0


def papel_de(nome: str, com_camaras: bool) -> str:
    """Como a superfície é pintada: sangue (câmaras/vasos), músculo, pulmão,
    envelope (coração inteiro por cima das câmaras) ou órgão genérico."""
    if nome == "heart":
        return "envelope" if com_camaras else "orgao"
    if nome == "heart_myocardium":
        return "musculo"
    if nome.startswith(PREFIXOS_SANGUE):
        return "sangue"
    if nome.startswith("lung"):
        return "pulmao"
    return "orgao"


def zooms_de(affine: np.ndarray) -> np.ndarray:
    return np.linalg.norm(affine[:3, :3], axis=0)


def limpar(mask: np.ndarray, zooms: np.ndarray, min_mm3: float = 30.0, manter_todos: bool = False) -> np.ndarray:
    """Remove ilhas menores que min_mm3 (a menos que a classe seja multi-componente)
    e fecha buracos internos. Feito na máscara, antes do marching cubes."""
    from scipy import ndimage

    if not manter_todos:
        rotulos, n = ndimage.label(mask)
        if n > 1:
            tamanhos = np.bincount(rotulos.ravel())
            tamanhos[0] = 0
            manter = tamanhos >= min_mm3 / float(np.prod(zooms))
            if not manter.any():
                manter[tamanhos.argmax()] = True
            mask = manter[rotulos]
    return ndimage.binary_fill_holes(mask)


def encostar(mask: np.ndarray, alvo: np.ndarray) -> np.ndarray:
    """Dilata 1 voxel só onde entra no alvo — a veia passa a tocar o coração."""
    from scipy import ndimage

    return mask | (ndimage.binary_dilation(mask) & alvo)


def toca_borda(mask: np.ndarray) -> list[str]:
    faces = []
    if mask[:, :, -1].any():
        faces.append("topo")
    if mask[:, :, 0].any():
        faces.append("base")
    if mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any():
        faces.append("lateral")
    return faces


def malha_de_volume(
    mask: np.ndarray,
    affine: np.ndarray,
    sigma_mm: float | None = None,
    level: float = 0.5,
    afastamento_mm: float = 0.15,
    taubin: int = 3,
) -> tuple[trimesh.Trimesh, int] | None:
    """Máscara binária → malha em metros (eixos glTF), ainda sem decimação."""
    from scipy import ndimage
    from skimage import measure

    if mask.sum() < 50:  # estrutura ausente ou ruído
        return None
    zooms = zooms_de(affine)
    if sigma_mm is None:
        sigma_mm = max(0.6, 0.5 * float(zooms.max()))
    # Pad: a superfície fecha com uma tampa plana onde o exame termina.
    campo = ndimage.gaussian_filter(np.pad(mask.astype(np.float32), 1), sigma=sigma_mm / zooms)
    verts, faces, _normais, _valores = measure.marching_cubes(campo, level=level)
    verts -= 1.0  # desfaz o pad
    verts_mm = verts @ affine[:3, :3].T + affine[:3, 3]
    malha = trimesh.Trimesh(vertices=(verts_mm @ RAS_PARA_GLTF.T) * MM_PARA_M, faces=faces, process=True)
    tris_brutos = len(malha.faces)
    trimesh.smoothing.filter_taubin(malha, lamb=0.5, nu=-0.53, iterations=taubin)
    # O marching cubes sai com normais para DENTRO; corrige por corpo antes de
    # usar as normais para o afastamento e para a amostragem de HU.
    malha.fix_normals(multibody=True)
    if afastamento_mm > 0:
        malha.vertices = malha.vertices - malha.vertex_normals * (afastamento_mm * MM_PARA_M)
    return malha, tris_brutos


def decimar(malha: trimesh.Trimesh, orcamento_tris: int) -> trimesh.Trimesh:
    """Decimação controlada por estrutura (nunca o --simplify do gltf-transform)."""
    if len(malha.faces) <= orcamento_tris:
        return malha
    import fast_simplification

    verts_d, faces_d = fast_simplification.simplify(
        malha.vertices.astype(np.float32), malha.faces.astype(np.int64), target_count=orcamento_tris
    )
    saida = trimesh.Trimesh(vertices=verts_d, faces=faces_d, process=True)
    saida.fix_normals(multibody=True)
    return saida


@dataclass
class ContextoCT:
    """CT levemente suavizada + campos de ocupação para pintar as malhas."""

    vol: np.ndarray
    inv_affine: np.ndarray
    ocupacao_fora: np.ndarray | None  # estruturas externas (envelope, vasos, vias aéreas…)
    ocupacao_dentro: np.ndarray | None  # câmaras + miocárdio (dentro do envelope)


def preparar_ct(
    caminho_ct,
    uniao_fora: np.ndarray | None = None,
    uniao_dentro: np.ndarray | None = None,
    raio_oclusao_mm: float = 8.0,
) -> ContextoCT:
    import nibabel as nib
    from scipy import ndimage

    img = nib.load(str(caminho_ct))
    zooms = zooms_de(img.affine)
    vol = ndimage.gaussian_filter(np.asarray(img.dataobj, dtype=np.float32), sigma=0.7 / zooms)

    def ocupacao(uniao):
        if uniao is None:
            return None
        tamanho = (np.maximum(1, np.round(raio_oclusao_mm / zooms)).astype(int) * 2 + 1).tolist()
        return ndimage.uniform_filter(uniao.astype(np.float32), size=tamanho)

    return ContextoCT(vol, np.linalg.inv(img.affine), ocupacao(uniao_fora), ocupacao(uniao_dentro))


def _amostrar(campo: np.ndarray, inv_affine: np.ndarray, pontos_gltf: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    mm = (pontos_gltf / MM_PARA_M) @ RAS_PARA_GLTF  # inversa da rotação = transposta
    vox = mm @ inv_affine[:3, :3].T + inv_affine[:3, 3]
    return ndimage.map_coordinates(campo, vox.T, order=1, mode="nearest")


def amostrar_hu(malha: trimesh.Trimesh, ct: ContextoCT, profundidade_mm: float) -> np.ndarray:
    """HU a `profundidade_mm` da superfície (positivo = para dentro)."""
    pontos = malha.vertices - malha.vertex_normals * (profundidade_mm * MM_PARA_M)
    return _amostrar(ct.vol, ct.inv_affine, pontos)


def srgb_para_linear(cor) -> np.ndarray:
    c = np.asarray(cor, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _banda(x: np.ndarray, centro: float, meia_largura: float) -> np.ndarray:
    """1 no centro, 0 fora de ±meia_largura (rampa linear)."""
    return np.clip(1.0 - np.abs(x - centro) / meia_largura, 0.0, 1.0)


def pintar(malha: trimesh.Trimesh, nome: str, papel: str, ct: ContextoCT | None) -> None:
    """Cor por vértice a partir do exame. Sem CT, só a cor didática linearizada."""
    base = srgb_para_linear(cor_para(nome))
    n = len(malha.vertices)
    cor = np.tile(base, (n, 1))

    if ct is not None:
        hu_in = amostrar_hu(malha, ct, 1.0)[:, None]
        hu_out = amostrar_hu(malha, ct, -2.0)[:, None]
        if papel == "sangue":
            # Sangue com contraste (≥ 300 HU) vivo; cava sem contraste (~130 HU) escura.
            t = np.clip((hu_in - 100.0) / 250.0, 0.0, 1.0)
            cor = base * 0.55 * (1 - t) + np.minimum(base * 1.25, 1.0) * t
        elif papel == "musculo":
            t = np.clip((hu_in - 30.0) / 150.0, 0.0, 1.0)
            cor = base * 0.6 * (1 - t) + base * t
        elif papel == "pulmao":
            hu = hu_in[:, 0]
            srgb = np.stack([np.interp(hu, RAMPA_HU_PONTOS, RAMPA_HU_CORES[:, c]) for c in range(3)], axis=1)
            cor = srgb_para_linear(srgb)
        else:
            # Superfície externa: gordura (−190..−30 HU) nos sulcos vira ocre; vaso
            # opacificado encostado (> 250 HU) clareia. Pulmão (−800) não entra.
            gordura = _banda(hu_out, -110.0, 80.0)
            cor = cor * (1 - 0.4 * gordura) + srgb_para_linear(OCRE) * 0.4 * gordura
            vaso = np.clip((hu_out - 250.0) / 200.0, 0.0, 1.0)
            cor = cor * (1 - 0.35 * vaso) + srgb_para_linear(VERMELHO_CLARO) * 0.35 * vaso

        ocupacao = ct.ocupacao_dentro if papel in ("sangue", "musculo") and nome.startswith("heart_") else ct.ocupacao_fora
        if ocupacao is not None:
            # Fora da superfície: quanto mais vizinhança ocupada (fenda entre
            # estruturas), menos luz — oclusão cozida no vértice, custo zero no Quest.
            oc = _amostrar(ocupacao, ct.inv_affine, malha.vertices + malha.vertex_normals * (1.0 * MM_PARA_M))
            ao = 1.0 - np.clip((oc - 0.5) / 0.4, 0.0, 1.0)
            cor = cor * (0.55 + 0.45 * ao)[:, None]

    rgba = np.hstack([np.clip(cor, 0.0, 1.0), np.ones((n, 1))])
    malha.visual = trimesh.visual.ColorVisuals(malha, vertex_colors=(rgba * 255).astype(np.uint8))


def volume_ml(malha: trimesh.Trimesh) -> float:
    return abs(float(malha.volume)) * 1e6  # m³ → mL
