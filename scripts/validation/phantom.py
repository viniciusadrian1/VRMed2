"""
Fantomas sintéticos com dimensão CONHECIDA — detector de regressão geométrica.

A ideia: a única forma de saber se o pipeline (suavização + marching cubes +
Taubin + afastamento + decimação) está comendo volume é medí-lo contra algo cuja
resposta analítica já se sabe. Esfera de 10 mm = 523,60 mm³, sempre.

Todas as máscaras saem numa grade com affine DIAGONAL de spacing dado (aceita
anisotropia, ex.: 0,7 × 0,7 × 2,5 mm, para simular fatia grossa) e origem tal
que o centro do fantoma cai em (0, 0, 0) mm RAS.
"""

from __future__ import annotations

import numpy as np

Spacing = tuple[float, float, float]


def _grade(extent_mm: tuple[float, float, float], spacing: Spacing) -> tuple[np.ndarray, np.ndarray]:
    """Grade centrada na origem. Devolve (pontos_mm com shape (nx,ny,nz,3), affine)."""
    sp = np.asarray(spacing, dtype=float)
    n = np.maximum(2, np.ceil(np.asarray(extent_mm, dtype=float) / sp).astype(int) + 1)
    # n ÍMPAR em todos os eixos: garante um centro de voxel exatamente na origem,
    # então a rede de amostragem é a MESMA para qualquer diâmetro. Com n variando
    # entre par e ímpar, a rede deslocava meio voxel e o volume discretizado
    # deixava de crescer com o diâmetro (d=2,0 mm dava menos que d=1,5 mm) —
    # um fantoma não-monotônico não detecta regressão.
    n = n + (n % 2 == 0)
    affine = np.eye(4)
    affine[:3, :3] = np.diag(sp)
    affine[:3, 3] = -(n - 1) / 2.0 * sp  # centro do volume na origem
    eixos = [np.arange(n[i]) * sp[i] + affine[i, 3] for i in range(3)]
    pts = np.stack(np.meshgrid(*eixos, indexing="ij"), axis=-1)
    return pts, affine


def _ocupacao(pts_mm: np.ndarray, spacing: Spacing, dentro, supersample: int = 3) -> np.ndarray:
    """Fração de cada voxel que cai dentro da forma, por supersampling.

    Amostrar só o centro do voxel torna a discretização NÃO-MONOTÔNICA: como
    `_grade` gera n par ou ímpar conforme o diâmetro, a rede de amostragem
    desloca meio voxel e, por exemplo, d=1,0 mm e d=2,0 mm em spacing 0,7 mm
    caíam ambos em 4 voxels de seção. Um fantoma que não cresce com o diâmetro
    não serve como detector de regressão — daí o supersampling.
    """
    sp = np.asarray(spacing, dtype=float)
    passos = (np.arange(supersample) + 0.5) / supersample - 0.5  # simétrico em torno de 0
    desl = np.stack(np.meshgrid(passos * sp[0], passos * sp[1], passos * sp[2], indexing="ij"), axis=-1)
    desl = desl.reshape(-1, 3)
    acumulado = np.zeros(pts_mm.shape[:3], dtype=np.float32)
    for d in desl:
        acumulado += dentro(pts_mm + d).astype(np.float32)
    return acumulado / float(len(desl))


def esfera(
    diametro_mm: float, spacing: Spacing = (1.0, 1.0, 1.0), margem_mm: float = 5.0
) -> tuple[np.ndarray, np.ndarray]:
    """Esfera sólida centrada na origem. Volume analítico = π/6 · d³."""
    lado = diametro_mm + 2 * margem_mm
    pts, affine = _grade((lado, lado, lado), spacing)
    raio = diametro_mm / 2.0
    mask = _ocupacao(pts, spacing, lambda p: np.linalg.norm(p, axis=-1) <= raio) >= 0.5
    return mask, affine


def cilindro(
    diametro_mm: float,
    altura_mm: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    eixo: int = 2,
    margem_mm: float = 5.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Cilindro sólido alinhado ao eixo dado (0=x, 1=y, 2=z). V = π/4 · d² · h."""
    extent = [diametro_mm + 2 * margem_mm] * 3
    extent[eixo] = altura_mm + 2 * margem_mm
    pts, affine = _grade(tuple(extent), spacing)
    radiais = [i for i in range(3) if i != eixo]
    raio = diametro_mm / 2.0
    meia_altura = altura_mm / 2.0

    def dentro(p: np.ndarray) -> np.ndarray:
        r = np.linalg.norm(p[..., radiais], axis=-1)
        return (r <= raio) & (np.abs(p[..., eixo]) <= meia_altura)

    mask = _ocupacao(pts, spacing, dentro) >= 0.5
    return mask, affine


def tubo_fino(
    diametro_mm: float, comprimento_mm: float, spacing: Spacing = (1.0, 1.0, 1.0)
) -> tuple[np.ndarray, np.ndarray]:
    """Vaso fino (ex.: 2 mm) ao longo de z — o caso que suavização e erosão apagam."""
    return cilindro(diametro_mm, comprimento_mm, spacing=spacing, eixo=2, margem_mm=4.0)


def duas_estruturas_adjacentes(
    gap_mm: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    diametro_mm: float = 10.0,
    margem_mm: float = 5.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Duas esferas iguais separadas por `gap_mm` de vão em x (borda a borda).
    Se a malha sair como um corpo só, houve fusão indevida (σ grande demais)."""
    centro = (diametro_mm + gap_mm) / 2.0
    lx = 2 * centro + diametro_mm + 2 * margem_mm
    ly = diametro_mm + 2 * margem_mm
    pts, affine = _grade((lx, ly, ly), spacing)
    r = diametro_mm / 2.0
    d1 = np.linalg.norm(pts - np.array([-centro, 0.0, 0.0]), axis=-1)
    d2 = np.linalg.norm(pts - np.array([centro, 0.0, 0.0]), axis=-1)
    return (d1 <= r) | (d2 <= r), affine


def esfera_com_cavidade(
    diametro_mm: float,
    diametro_cavidade_mm: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    margem_mm: float = 5.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Casca esférica: cavidade interna vazia. Se o volume medido vier igual ao da
    esfera cheia, algum `binary_fill_holes` engoliu a cavidade."""
    mask, affine = esfera(diametro_mm, spacing=spacing, margem_mm=margem_mm)
    cavidade, _ = esfera(diametro_cavidade_mm, spacing=spacing, margem_mm=margem_mm)
    # mesma grade só se as extensões coincidirem; recorta pela distância direto:
    pts, affine = _grade((diametro_mm + 2 * margem_mm,) * 3, spacing)
    r = np.linalg.norm(pts, axis=-1)
    return (r <= diametro_mm / 2.0) & (r > diametro_cavidade_mm / 2.0), affine


def medir_esfera(mesh) -> dict:
    """Mede uma malha esférica em METROS (saída do pipeline) e devolve mm.

    diametro_medido_mm = 2 × raio médio dos vértices em torno do centroide
    (menos sensível a um único vértice fora do lugar que a bounding box).
    """
    v = np.asarray(mesh.vertices, dtype=float)
    centro = v.mean(axis=0)
    raios_mm = np.linalg.norm(v - centro, axis=1) * 1000.0
    bbox_mm = (v.max(axis=0) - v.min(axis=0)) * 1000.0
    volume_mm3 = abs(float(mesh.volume)) * 1e9
    return {
        "diametro_medido_mm": float(2.0 * raios_mm.mean()),
        "volume_medido_mm3": volume_mm3,
        "diametro_bbox_mm": float(bbox_mm.mean()),
        "desvio_raio_mm": float(raios_mm.std()),
        "diametro_equivalente_mm": float((6.0 * volume_mm3 / np.pi) ** (1.0 / 3.0)),
        "n_vertices": int(len(v)),
        "estanque": bool(mesh.is_watertight),
    }


def volume_da_mascara_mm3(mask: np.ndarray, affine: np.ndarray) -> float:
    """Volume por contagem de voxels × volume do voxel (referência de discretização)."""
    zooms = np.linalg.norm(affine[:3, :3], axis=0)
    return float(mask.sum()) * float(np.prod(zooms))


def _demo() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from clinica.malha import malha_de_volume  # baseline do pipeline

    def caso(rotulo: str, spacing: Spacing, d: float = 10.0) -> None:
        esperado_v = np.pi / 6.0 * d**3
        mask, affine = esfera(d, spacing=spacing)
        v_vox = volume_da_mascara_mm3(mask, affine)
        malha, _tris = malha_de_volume(mask, affine, afastamento_mm=0.0)
        m = medir_esfera(malha)
        err_d = 100.0 * (m["diametro_medido_mm"] - d) / d
        err_v = 100.0 * (m["volume_medido_mm3"] - esperado_v) / esperado_v
        err_vox = 100.0 * (v_vox - esperado_v) / esperado_v
        print(f"\n[{rotulo}] spacing={spacing}  grade={mask.shape}  voxels={int(mask.sum())}")
        print(f"  esperado        : d={d:.2f} mm   V={esperado_v:.1f} mm3")
        print(f"  contagem voxels : V={v_vox:.1f} mm3   erro={err_vox:+.1f} %")
        print(f"  malha (MC)      : d={m['diametro_medido_mm']:.2f} mm  erro={err_d:+.1f} %")
        print(f"                    V={m['volume_medido_mm3']:.1f} mm3  erro={err_v:+.1f} %")
        print(f"                    d_equiv={m['diametro_equivalente_mm']:.2f} mm  "
              f"bbox={m['diametro_bbox_mm']:.2f} mm  desvio_raio={m['desvio_raio_mm']:.2f} mm  "
              f"estanque={m['estanque']}")
        assert abs(err_v) < 60.0, f"regressao grosseira em {rotulo}: {err_v:+.1f} %"

    caso("isotropico", (1.0, 1.0, 1.0))
    caso("anisotropico (fatia grossa)", (0.7, 0.7, 2.5))

    # Fantomas restantes: só o sanity check de que a geometria bate com a fórmula.
    m, a = tubo_fino(2.0, 30.0, spacing=(0.5, 0.5, 0.5))
    print(f"\n[tubo 2x30 mm] voxels={int(m.sum())}  V={volume_da_mascara_mm3(m, a):.1f} mm3 "
          f"(analitico {np.pi/4*2.0**2*30.0:.1f})")

    from scipy import ndimage

    for gap in (3.0, 1.0):
        m, a = duas_estruturas_adjacentes(gap, spacing=(1.0, 1.0, 1.0))
        n_mask = ndimage.label(m)[1]
        malha, _ = malha_de_volume(m, a, afastamento_mm=0.0)
        print(f"[gap {gap} mm] componentes na mascara={n_mask}  corpos na malha={malha.body_count}")

    m, a = esfera_com_cavidade(20.0, 10.0, spacing=(0.5, 0.5, 0.5))
    v = volume_da_mascara_mm3(m, a)
    print(f"\n[casca 20/10 mm] V_mascara={v:.1f} mm3 (analitico "
          f"{np.pi/6*(20.0**3 - 10.0**3):.1f})")
    malha, _ = malha_de_volume(m, a, afastamento_mm=0.0)
    print(f"  malha: V={abs(malha.volume)*1e9:.1f} mm3  corpos={malha.body_count} "
          f"(1 corpo => cavidade foi preenchida)")


if __name__ == "__main__":
    _demo()
