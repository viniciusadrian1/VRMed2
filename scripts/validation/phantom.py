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


# ---------------------------------------------------------------------------
# Fantomas de TOPOLOGIA
#
# Os fantomas acima medem QUANTO volume some. Os abaixo medem se a suavização
# muda a TOPOLOGIA: apaga uma junção, fecha um lúmen, cria uma ponte entre duas
# estruturas ou arrebenta uma conexão fina. São perguntas de contagem
# (componentes, cavidades, borda aberta), não de milímetro.
# ---------------------------------------------------------------------------


def _dist_a_segmento(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distância de cada ponto ao segmento [a, b]. Comparada a um raio, dá uma cápsula."""
    ab = b - a
    ap = p - a
    t = np.clip((ap @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(ap - t[..., None] * ab, axis=-1)


def bifurcacao(
    diametro_mm: float,
    comprimento_mm: float,
    angulo_graus: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    margem_mm: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Tronco em Y: um cilindro sobe em −z e se divide em dois ramos de mesmo diâmetro.

    Detecta se a suavização APAGA a junção (os ramos se soltam do tronco: 1 → 2 ou 3
    componentes) ou FUNDE os dois ramos num bloco só (o vão entre eles some).

    VOLUME ANALÍTICO: **não aplicável**. Os três cilindros se interceptam na junção e
    a interseção não tem forma fechada simples. A referência deste caso é o volume da
    MÁSCARA (`volume_da_mascara_mm3`), que já é uma discretização — não é verdade
    analítica. Só serve para comparar duas versões do pipeline na MESMA grade.
    """
    raio = diametro_mm / 2.0
    comp = float(comprimento_mm)
    meia = np.radians(angulo_graus) / 2.0
    ramo_x = comp * np.sin(meia)
    ramo_z = comp * np.cos(meia)
    extent = (
        2 * (ramo_x + raio + margem_mm),
        2 * (raio + margem_mm),
        2 * (comp + raio + margem_mm),  # o tronco desce até −comp
    )
    pts, affine = _grade(extent, spacing)

    origem = np.zeros(3)
    segmentos = (
        (np.array([0.0, 0.0, -comp]), origem),          # tronco
        (origem, np.array([ramo_x, 0.0, ramo_z])),      # ramo +x
        (origem, np.array([-ramo_x, 0.0, ramo_z])),     # ramo −x
    )

    def dentro(p: np.ndarray) -> np.ndarray:
        d = np.full(p.shape[:-1], np.inf)
        for a, b in segmentos:
            d = np.minimum(d, _dist_a_segmento(p, a, b))
        return d <= raio

    return _ocupacao(pts, spacing, dentro) >= 0.5, affine


def tubo_oco(
    diametro_externo_mm: float,
    diametro_interno_mm: float,
    comprimento_mm: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    margem_mm: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Cilindro com lúmen vazio ao longo de z (parede anular).

    Detecta se a suavização FECHA o lúmen: se o volume medido subir para
    π/4 · de² · h, o vazio foi engolido.

    Volume analítico = π/4 · (de² − di²) · h.
    """
    re = diametro_externo_mm / 2.0
    ri = diametro_interno_mm / 2.0
    meia_altura = comprimento_mm / 2.0
    lado = diametro_externo_mm + 2 * margem_mm
    pts, affine = _grade((lado, lado, comprimento_mm + 2 * margem_mm), spacing)

    def dentro(p: np.ndarray) -> np.ndarray:
        r = np.linalg.norm(p[..., :2], axis=-1)
        return (r <= re) & (r > ri) & (np.abs(p[..., 2]) <= meia_altura)

    return _ocupacao(pts, spacing, dentro) >= 0.5, affine


def dois_cilindros_em_contato(
    diametro_mm: float,
    comprimento_mm: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    margem_mm: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Dois cilindros paralelos a z separados por EXATAMENTE 1 voxel de vão em x.

    Detecta se a suavização cria uma PONTE e funde 2 componentes em 1.

    Por que 1 voxel e não tangência real (vão 0): em 26-conexo dois cilindros
    tangentes já saem da PRÓPRIA MÁSCARA como 1 componente — não haveria como
    distinguir a ponte criada pelo pipeline da geometria original, e o fantoma não
    detectaria nada. Com vão de um voxel a máscara tem 2 componentes (verificado no
    autoteste) e qualquer fusão posterior é atribuível ao pipeline. O vão em mm
    depende do spacing: é `spacing[0]`, o menor vão representável nessa grade.

    Volume analítico = 2 · π/4 · d² · h (exato: os cilindros não se interceptam).
    Componentes esperados na máscara: 2.
    """
    passo_x = float(spacing[0])
    centro = (diametro_mm + passo_x) / 2.0  # vão borda a borda = passo_x
    raio = diametro_mm / 2.0
    meia_altura = comprimento_mm / 2.0
    extent = (
        2 * centro + diametro_mm + 2 * margem_mm,
        diametro_mm + 2 * margem_mm,
        comprimento_mm + 2 * margem_mm,
    )
    pts, affine = _grade(extent, spacing)

    def dentro(p: np.ndarray) -> np.ndarray:
        dy = p[..., 1]
        r1 = np.hypot(p[..., 0] + centro, dy)
        r2 = np.hypot(p[..., 0] - centro, dy)
        return ((r1 <= raio) | (r2 <= raio)) & (np.abs(p[..., 2]) <= meia_altura)

    return _ocupacao(pts, spacing, dentro) >= 0.5, affine


def estrutura_parcialmente_cortada(
    diametro_mm: float, spacing: Spacing = (1.0, 1.0, 1.0), margem_mm: float = 4.0
) -> tuple[np.ndarray, np.ndarray]:
    """Esfera cujo topo é cortado pela borda do volume — o FOV acaba no meio dela.

    É o caso real de pulmão/aorta cortados pelo campo de visão. Detecta se o
    pipeline ABRE a malha na borda (não-watertight, volume inválido) ou INVENTA uma
    tampa plana (malha fechada com volume que ninguém mediu).

    Geometria: a calota de altura h = r/2 fica FORA da grade; a esfera é deslocada em
    +z para que só o topo seja cortado (o fundo continua com margem).

    Volume analítico remanescente = 4/3·π·r³ − π·h²·(3r − h)/3, com h = r/2 (fórmula
    da calota esférica). ATENÇÃO: o plano de corte efetivo tem ambiguidade de meio
    voxel (a máscara guarda centros de voxel, o plano está na face externa do
    último), o que em fatia grossa vale vários por cento — por isso o autoteste
    verifica o CORTE (a máscara toca a borda), não esse volume.
    """
    raio = diametro_mm / 2.0
    lado = diametro_mm + 2 * margem_mm
    pts, affine = _grade((lado, lado, diametro_mm), spacing)
    passo_z = float(spacing[2])
    z_face = float(pts[0, 0, -1, 2]) + passo_z / 2.0  # face externa do último voxel
    z_centro = z_face - raio / 2.0  # sobra do lado de fora uma calota de altura r/2
    centro = np.array([0.0, 0.0, z_centro])
    mask = _ocupacao(pts, spacing, lambda p: np.linalg.norm(p - centro, axis=-1) <= raio) >= 0.5
    return mask, affine


def ponte_fina(
    diametro_mm: float,
    gap_mm: float,
    spacing: Spacing = (1.0, 1.0, 1.0),
    diametro_ponte_mm: float = 2.0,
    margem_mm: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Duas esferas ligadas por um cilindro fino (a ponte) ao longo de x.

    Detecta se a suavização REMOVE a conexão fina: 1 componente na máscara virando 2
    na malha significa que a ponte foi apagada — a estrutura continua "bonita" e o
    Dice quase não cai, mas a conectividade morreu.

    `gap_mm` é o vão entre as esferas (borda a borda), preenchido pela ponte de
    `diametro_ponte_mm`.

    VOLUME ANALÍTICO: **não aplicável**. A ponte penetra as duas esferas e a
    interseção não tem forma fechada simples aqui. Referência = volume da máscara.
    Componentes esperados na máscara: 1.
    """
    raio = diametro_mm / 2.0
    raio_ponte = diametro_ponte_mm / 2.0
    centro = (diametro_mm + gap_mm) / 2.0
    lado = diametro_mm + 2 * margem_mm
    pts, affine = _grade((2 * centro + lado, lado, lado), spacing)

    def dentro(p: np.ndarray) -> np.ndarray:
        d1 = np.linalg.norm(p - np.array([-centro, 0.0, 0.0]), axis=-1)
        d2 = np.linalg.norm(p - np.array([centro, 0.0, 0.0]), axis=-1)
        r_ponte = np.linalg.norm(p[..., 1:], axis=-1)
        # a ponte vai de centro a centro: entra nas duas esferas, sem junta aberta
        ponte = (r_ponte <= raio_ponte) & (np.abs(p[..., 0]) <= centro)
        return (d1 <= raio) | (d2 <= raio) | ponte

    return _ocupacao(pts, spacing, dentro) >= 0.5, affine


# nome -> (construtor, kwargs, n_componentes_esperado, tem_cavidade, volume_analitico_mm3)
# volume_analitico_mm3 = None significa "não aplicável": a geometria não tem forma
# fechada simples e a referência é o volume da MÁSCARA, que não é verdade analítica.
# `n_componentes_esperado` é contado em 26-conexo (`np.ones((3, 3, 3))`), a mesma
# conectividade de `topology_metrics.CONECTIVIDADE`.
CASOS_TOPOLOGIA: dict[str, tuple] = {
    "bifurcacao": (
        bifurcacao,
        {"diametro_mm": 6.0, "comprimento_mm": 20.0, "angulo_graus": 60.0, "spacing": (0.5, 0.5, 0.5)},
        1,
        False,
        None,  # interseção dos três cilindros: sem forma fechada
    ),
    "tubo_oco": (
        tubo_oco,
        {
            "diametro_externo_mm": 10.0,
            "diametro_interno_mm": 6.0,
            "comprimento_mm": 20.0,
            "spacing": (0.5, 0.5, 0.5),
        },
        1,
        True,
        np.pi / 4.0 * (10.0**2 - 6.0**2) * 20.0,
    ),
    "dois_cilindros_em_contato": (
        dois_cilindros_em_contato,
        {"diametro_mm": 8.0, "comprimento_mm": 20.0, "spacing": (0.5, 0.5, 0.5)},
        2,
        False,
        2.0 * np.pi / 4.0 * 8.0**2 * 20.0,
    ),
    "estrutura_parcialmente_cortada": (
        estrutura_parcialmente_cortada,
        {"diametro_mm": 20.0, "spacing": (0.5, 0.5, 0.5)},
        1,
        False,
        # esfera r=10 menos a calota de altura h=5 que ficou fora do FOV
        4.0 / 3.0 * np.pi * 10.0**3 - np.pi * 5.0**2 * (3 * 10.0 - 5.0) / 3.0,
    ),
    "ponte_fina": (
        ponte_fina,
        {"diametro_mm": 10.0, "gap_mm": 6.0, "spacing": (0.5, 0.5, 0.5), "diametro_ponte_mm": 2.0},
        1,
        False,
        None,  # a ponte penetra as esferas: sem forma fechada
    ),
}


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


def _autoteste_topologia() -> None:
    """Sanidade da GEOMETRIA dos fantomas de topologia (não mede pipeline nenhum).

    Se um destes falhar, o fantoma está errado e qualquer conclusão tirada dele
    também estaria. Nada aqui prova que o pipeline preserva topologia — prova só
    que a máscara de entrada tem a topologia que a tabela declara.
    """
    from scipy import ndimage

    conectividade = np.ones((3, 3, 3), dtype=bool)

    for nome, (construtor, kwargs, n_esperado, tem_cavidade, v_analitico) in CASOS_TOPOLOGIA.items():
        mask, affine = construtor(**kwargs)
        n_obtido = int(ndimage.label(mask, structure=conectividade)[1])
        v_mask = volume_da_mascara_mm3(mask, affine)
        ref = f"{v_analitico:.1f}" if v_analitico is not None else "nao aplicavel"
        print(
            f"[{nome}] grade={tuple(mask.shape)} voxels={int(mask.sum())} "
            f"componentes={n_obtido} (esperado {n_esperado}) cavidade={tem_cavidade} "
            f"V_mascara={v_mask:.1f} mm3  V_analitico={ref}"
        )
        assert n_obtido == n_esperado, f"{nome}: {n_obtido} componentes, esperado {n_esperado}"

    # tubo_oco: a máscara tem de bater com o anel analítico. Lúmen preenchido daria
    # +56% (π/4·de²·h em vez de π/4·(de²−di²)·h), muito acima dos 15%.
    mask, affine = tubo_oco(**CASOS_TOPOLOGIA["tubo_oco"][1])
    v_ana = CASOS_TOPOLOGIA["tubo_oco"][4]
    erro = 100.0 * (volume_da_mascara_mm3(mask, affine) - v_ana) / v_ana
    print(f"[tubo_oco] erro de volume da mascara = {erro:+.1f} % (limite +-15 %)")
    assert abs(erro) <= 15.0, f"tubo_oco fora de 15%: {erro:+.1f} %"

    # estrutura_parcialmente_cortada: prova de que o corte existe — a máscara toca a
    # última fatia em z. Se não tocar, a esfera coube inteira e o fantoma é inútil.
    mask, _ = estrutura_parcialmente_cortada(**CASOS_TOPOLOGIA["estrutura_parcialmente_cortada"][1])
    print(f"[estrutura_parcialmente_cortada] voxels na ultima fatia z = {int(mask[:, :, -1].sum())}")
    assert mask[:, :, -1].any(), "a esfera nao encosta na borda: nao ha corte"
    assert not mask[:, :, 0].any(), "cortou tambem no fundo: era para ser so o topo"

    # ponte_fina: a ponte tem de existir NA MÁSCARA (1 componente), senão o teste do
    # pipeline mediria a discretização, não a suavização.
    mask, _ = ponte_fina(**CASOS_TOPOLOGIA["ponte_fina"][1])
    n = int(ndimage.label(mask, structure=conectividade)[1])
    assert n == 1, f"ponte_fina: mascara ja sai com {n} componentes"

    print("autoteste OK")


if __name__ == "__main__":
    import sys

    if "--topologia" in sys.argv:
        _autoteste_topologia()
    else:
        _demo()
