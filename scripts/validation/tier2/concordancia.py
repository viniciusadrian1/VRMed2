"""Comissionamento do instrumento de concordancia contra DESACORDO HUMANO REAL.

    OBJETO = GTV, NAO ESOFAGO; ELIMINADO POR F5

Leia a linha acima antes de qualquer numero deste modulo. Ela e o rotulo que o
modulo carrega no proprio nome interno (`ROTULO_F5`), em TODO registro gravado e
em TODA linha impressa, e que a guarda g12 faz cumprir mecanicamente.

O QUE ISTO E
------------
NSCLC-Radiomics-Interobserver1 (TCIA, DOI 10.7937/tcia.2019.cwvlpd26,
CC BY-NC 3.0) e o unico desacordo humano real, sobre o MESMO exame de TC
toracica, disponivel em disco: 5 observadores humanos desenharam GTV-1vis-1..5
no mesmo structure set de cada caso. O candidato ja foi ELIMINADO POR F5 na 1a
onda — o objeto anotado e o TUMOR (GTV), nao o esofago.

O valor deste modulo e triplo e NENHUM dos tres e sobre o esofago:
  (a) exercita as guardas g5/g6/g9/g10 em dado REAL (ate aqui elas so tinham
      controle sintetico, e o F7 nunca havia sido exercido em candidato nenhum);
  (b) prova que o instrumento de concordancia produz numero quando existe
      desacordo de verdade — um instrumento que so foi testado contra copias
      identicas nao foi testado;
  (c) da uma REGUA DE ESCALA medida, nao citada de artigo: quanto humanos
      discordam entre si ao contornar uma estrutura de tecido mole em TC
      toracica com fatia de 5 mm.

O QUE ISTO NAO E
----------------
Nao e medida do esofago. Nao e limiar de aceitacao. Nao e validacao clinica.
As tres frases que este resultado NAO autoriza estao em `FRASES_PROIBIDAS` e
sao reimpressas no fim de toda execucao.

GEOMETRIA (guarda g9)
---------------------
ContourData do RTSTRUCT ja vem em coordenadas de PACIENTE, em MILIMETROS.
Nada aqui converte para indice de voxel. A grade de rasterizacao e construida
em mm (`Grade.unidade == "mm"`), o passo em z e o proprio passo das fatias lido
do arquivo, e toda distancia sai em mm. `mesh_metrics.py` NAO e usado: ele teve
um bug de escala (trimesh.constants.tol.zero e absoluto, 1e-13) e este modulo
nao precisa de malha — a rasterizacao + `segmentation_metrics.py` bastam.

CONVENCOES DECLARADAS (para que ninguem tenha que adivinhar depois)
-------------------------------------------------------------------
  - Pares NAO sao ordenados: 5 observadores dao C(5,2) = 10 pares por caso, e
    toda diferenca e reportada em MODULO. Nao existe "predicao" nem "referencia"
    aqui; nenhum dos 5 e ground truth do outro.
  - `comprimento_mm` = (numero de planos ocupados) x dz. E extensao ocupada,
    nao (z_max - z_min).
  - `area_transversal_mm2` = media da area por plano OCUPADO (planos vazios nao
    entram na media).
  - `raio_caracteristico_mm` = sqrt(area_transversal_media / pi).
  - Diferenca percentual de volume e SIMETRICA: |Va-Vb| / ((Va+Vb)/2) x 100.
  - Apenas GTV-1vis-1..5 entra. GTV-2vis-* (segunda lesao, presente em parte dos
    casos) e visto e DELIBERADAMENTE nao agregado, para nao contar duas vezes o
    mesmo caso (guarda g5, espirito).
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import segmentation_metrics as SM

# ---------------------------------------------------------------- o rotulo

ROTULO_F5 = "OBJETO = GTV, NAO ESOFAGO; ELIMINADO POR F5"

COLECAO = "NSCLC-Radiomics-Interobserver1"
DOI = "10.7937/tcia.2019.cwvlpd26"
LICENCA = "CC BY-NC 3.0 Unported"
PREFIXO_OBS = "GTV-1vis-"

FRASES_PROIBIDAS = (
    "1. NAO autoriza: 'a concordancia interobservador do esofago e X'. "
    "O objeto medido aqui e GTV (tumor). Nenhum contorno de esofago foi lido.",
    "2. NAO autoriza: 'existe dataset publico com >=2 anotacoes humanas "
    "independentes do esofago'. Este candidato foi eliminado por F5; medi-lo "
    "nao o promove.",
    "3. NAO autoriza: 'o modelo esta dentro da variabilidade humana'. Isto e "
    "concordancia humano-humano em OUTRO objeto, nao um limiar de aceitacao, e "
    "nada aqui compara modelo com humano.",
)

RAIZ = Path(__file__).resolve().parents[3]
ENTRADA = RAIZ / ".clinica-dados/tier2/censo" / COLECAO
SAIDA = RAIZ / ".clinica-dados/fase11/concordancia_gtv_nao_esofago"

TOL_MM = 1e-3  # tolerancia de casamento de plano em z


class RecusaDeGuarda(Exception):
    """Uma guarda recusou a operacao. `guarda` diz qual."""

    def __init__(self, guarda: str, msg: str):
        super().__init__(f"[{guarda}] {msg}")
        self.guarda = guarda


# ---------------------------------------------------------------- g12


_RE_ESOFAGO = re.compile(r"esofag|esophag|oesofag|oesophag", re.IGNORECASE)

# As UNICAS strings em que o termo pode aparecer: elas negam, nao afirmam.
_G12_PERMITIDO = frozenset(FRASES_PROIBIDAS) | {
    ROTULO_F5,
    "nenhuma afirmacao sobre esofago pode ser derivada destes dados",
}


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def guarda_g12(payload) -> None:
    """g12 — RECUSA qualquer afirmacao sobre esofago derivada destes dados.

    Varre recursivamente chaves e valores de texto. Se o termo aparecer fora da
    lista fechada de frases que o NEGAM, levanta. E a guarda que impede que um
    numero de GTV vire, por descuido de copiar-e-colar, um numero de esofago.
    """

    def visitar(no, caminho: str) -> None:
        if isinstance(no, str):
            if _RE_ESOFAGO.search(_sem_acento(no)) and no not in _G12_PERMITIDO:
                raise RecusaDeGuarda(
                    "g12",
                    f"tentativa de escrever afirmacao sobre esofago em {caminho!r}: {no[:120]!r}. "
                    f"{ROTULO_F5}",
                )
        elif isinstance(no, dict):
            for k, v in no.items():
                visitar(k, f"{caminho}.{k}")
                visitar(v, f"{caminho}.{k}")
        elif isinstance(no, (list, tuple)):
            for i, v in enumerate(no):
                visitar(v, f"{caminho}[{i}]")

    visitar(payload, "$")


# ---------------------------------------------------------------- grade em mm


@dataclass(frozen=True)
class Grade:
    """Grade de rasterizacao em COORDENADAS DE PACIENTE, milimetros.

    `unidade` existe para ser conferida (g9): nenhuma metrica de distancia deste
    modulo aceita grade que nao seja "mm".
    """

    x0_mm: float
    y0_mm: float
    passo_xy_mm: float
    nx: int
    ny: int
    z_mm: np.ndarray  # centros dos planos, crescente, passo constante
    dz_mm: float
    unidade: str = "mm"
    caso: str = ""

    @property
    def spacing(self) -> tuple[float, float, float]:
        """Spacing na ordem dos eixos do array (z, y, x)."""
        return (self.dz_mm, self.passo_xy_mm, self.passo_xy_mm)

    @property
    def shape(self) -> tuple[int, int, int]:
        return (len(self.z_mm), self.ny, self.nx)

    @property
    def voxel_mm3(self) -> float:
        return float(self.dz_mm * self.passo_xy_mm * self.passo_xy_mm)


def guarda_g9(grade: Grade) -> None:
    """g9 — distancia SO em mm. Recusa grade em indice de voxel ou com passo invalido."""
    if grade.unidade != "mm":
        raise RecusaDeGuarda(
            "g9", f"grade em unidade {grade.unidade!r}; distancia so pode ser medida em mm"
        )
    for nome, v in (("passo_xy_mm", grade.passo_xy_mm), ("dz_mm", grade.dz_mm)):
        if not np.isfinite(v) or v <= 0:
            raise RecusaDeGuarda("g9", f"{nome}={v!r} nao e um passo fisico valido em mm")


def guarda_g5(a: str, b: str) -> None:
    """g5 — nao misturar casos. Um par so existe dentro do MESMO caso."""
    if a != b:
        raise RecusaDeGuarda("g5", f"par entre casos diferentes: {a!r} vs {b!r}")


# ---------------------------------------------------------------- leitura


def carregar_contornos(rtstruct: Path, prefixo: str = PREFIXO_OBS) -> dict:
    """Le os contornos dos observadores de UM structure set.

    Devolve {caso, frame_uid, arquivo, observadores: {nome: [(z_mm, poly Nx2)]}}.
    Os pontos saem exatamente como estao no arquivo: coordenadas de paciente, mm.
    """
    import pydicom

    ds = pydicom.dcmread(str(rtstruct), stop_before_pixels=True)
    if ds.Modality != "RTSTRUCT":
        raise ValueError(f"{rtstruct} nao e RTSTRUCT (Modality={ds.Modality})")

    num2nome = {r.ROINumber: r.ROIName for r in ds.StructureSetROISequence}
    observadores: dict[str, list] = {}
    for c in getattr(ds, "ROIContourSequence", []):
        nome = num2nome.get(c.ReferencedROINumber)
        if not nome or not nome.startswith(prefixo):
            continue
        fatias = []
        for ct in getattr(c, "ContourSequence", []):
            if ct.ContourGeometricType != "CLOSED_PLANAR":
                raise RecusaDeGuarda(
                    "g6", f"{nome}: ContourGeometricType={ct.ContourGeometricType!r} nao planar"
                )
            pts = np.asarray(ct.ContourData, dtype=float).reshape(-1, 3)
            z = float(pts[0, 2])
            if not np.allclose(pts[:, 2], z, atol=TOL_MM):
                raise RecusaDeGuarda("g6", f"{nome}: contorno nao coplanar em z={z}")
            fatias.append((z, pts[:, :2]))
        if fatias:
            observadores[nome] = fatias

    frames = {
        getattr(f, "FrameOfReferenceUID", "") for f in getattr(ds, "ReferencedFrameOfReferenceSequence", [])
    }
    return {
        "caso": str(ds.PatientID),
        "frame_uid": sorted(frames)[0] if len(frames) == 1 else "",
        "n_frames": len(frames),
        "arquivo": str(rtstruct),
        "observadores": dict(sorted(observadores.items())),
        "objeto": ROTULO_F5,
    }


# ---------------------------------------------------------------- grade + raster


def montar_grade(reg: dict, passo_xy_mm: float = 1.0, margem_mm: float = 5.0) -> Grade:
    """Constroi a grade comum do caso. Aplica g6 (grades incompativeis recusadas).

    g6 aqui e concreto: os 5 observadores tem que viver na MESMA rede de planos
    em z. Se os z de um observador nao caem na rede dos outros (passo diferente,
    ou deslocamento de meia fatia), a comparacao seria entre grades diferentes e
    e recusada em vez de reamostrada em silencio.
    """
    obs = reg["observadores"]
    if len(obs) < 2:
        raise RecusaDeGuarda("g6", f"{reg['caso']}: {len(obs)} observador(es), par impossivel")
    if reg["n_frames"] != 1:
        raise RecusaDeGuarda(
            "g6", f"{reg['caso']}: {reg['n_frames']} FrameOfReferenceUID; grade nao e unica"
        )

    zs = np.array(sorted({round(z, 6) for fatias in obs.values() for z, _ in fatias}))
    if len(zs) < 2:
        raise RecusaDeGuarda("g6", f"{reg['caso']}: {len(zs)} plano(s) em z; sem extensao medivel")
    gaps = np.diff(zs)
    dz = float(gaps.min())
    if dz <= 0:
        raise RecusaDeGuarda("g6", f"{reg['caso']}: passo em z nao positivo ({dz})")
    k = gaps / dz
    if np.any(np.abs(k - np.round(k)) > 1e-3):
        raise RecusaDeGuarda(
            "g6",
            f"{reg['caso']}: planos em z fora de uma rede comum "
            f"(passos observados: {sorted(set(np.round(gaps, 3).tolist()))})",
        )

    z0 = float(zs[0])
    nz = int(round((float(zs[-1]) - z0) / dz)) + 1
    z_mm = z0 + dz * np.arange(nz, dtype=float)

    pts = np.concatenate([p for fatias in obs.values() for _, p in fatias], axis=0)
    x0 = float(pts[:, 0].min()) - margem_mm
    y0 = float(pts[:, 1].min()) - margem_mm
    nx = int(np.ceil((float(pts[:, 0].max()) + margem_mm - x0) / passo_xy_mm)) + 1
    ny = int(np.ceil((float(pts[:, 1].max()) + margem_mm - y0) / passo_xy_mm)) + 1

    grade = Grade(x0, y0, float(passo_xy_mm), nx, ny, z_mm, dz, "mm", reg["caso"])
    guarda_g9(grade)
    return grade


def rasterizar(fatias: list, grade: Grade) -> tuple[np.ndarray, int]:
    """Contornos (z_mm, poly_mm) -> mascara booleana (nz, ny, nx). Aplica g10.

    g10: um contorno cujo z NAO cai em nenhum plano da grade seria descartado e
    viraria fundo. Isso e recusado. Poligonos coplanares sao combinados por XOR
    (regra par-impar: poligono dentro de poligono e buraco), que e a convencao
    do RTSTRUCT.

    Devolve tambem quantos planos INTERNOS ao proprio observador ficaram vazios
    (buraco de contorno no meio da estrutura) — nao e recusa, mas nunca some:
    e reportado por caso e por observador.
    """
    from matplotlib.path import Path as MplPath

    guarda_g9(grade)
    nz, ny, nx = grade.shape
    m = np.zeros((nz, ny, nx), dtype=bool)

    xs = grade.x0_mm + grade.passo_xy_mm * np.arange(nx, dtype=float)
    ys = grade.y0_mm + grade.passo_xy_mm * np.arange(ny, dtype=float)
    gx, gy = np.meshgrid(xs, ys)
    pontos = np.column_stack([gx.ravel(), gy.ravel()])

    ocupados = set()
    for z, poly in fatias:
        idx = (z - grade.z_mm[0]) / grade.dz_mm
        i = int(round(idx))
        if not (0 <= i < nz) or abs(idx - i) > 1e-3:
            raise RecusaDeGuarda(
                "g10",
                f"contorno em z={z:.3f} mm nao cai em plano da grade "
                f"[{grade.z_mm[0]:.3f}..{grade.z_mm[-1]:.3f}] passo {grade.dz_mm:.3f} mm; "
                "descarta-lo o transformaria em fundo",
            )
        dentro = MplPath(poly).contains_points(pontos).reshape(ny, nx)
        m[i] ^= dentro  # XOR: par-impar, buracos saem de graca
        ocupados.add(i)

    if ocupados:
        lo, hi = min(ocupados), max(ocupados)
        vazios_internos = (hi - lo + 1) - len(ocupados)
    else:
        vazios_internos = 0
    return m, int(vazios_internos)


# ---------------------------------------------------------------- descritores


def descritores(m: np.ndarray, grade: Grade) -> dict:
    """Descritores de forma de UMA mascara, todos em mm / mm2 / mm3."""
    guarda_g9(grade)
    if not m.any():
        raise ValueError("mascara vazia: sem descritor de forma")

    area_vox = grade.passo_xy_mm**2
    por_plano = m.reshape(m.shape[0], -1).sum(axis=1)
    ocupados = np.flatnonzero(por_plano)
    areas = por_plano[ocupados] * area_vox

    zc, yc, xc = (np.asarray(a, dtype=float) for a in np.nonzero(m))
    cx = grade.x0_mm + grade.passo_xy_mm * xc.mean()
    cy = grade.y0_mm + grade.passo_xy_mm * yc.mean()
    cz = float(np.interp(zc.mean(), np.arange(len(grade.z_mm)), grade.z_mm))

    area_media = float(areas.mean())
    return {
        "volume_mm3": float(m.sum()) * grade.voxel_mm3,
        "comprimento_mm": float(len(ocupados) * grade.dz_mm),
        "area_transversal_media_mm2": area_media,
        "area_transversal_max_mm2": float(areas.max()),
        "raio_caracteristico_mm": float(np.sqrt(area_media / np.pi)),
        "z_inf_mm": float(grade.z_mm[ocupados[0]]),
        "z_sup_mm": float(grade.z_mm[ocupados[-1]]),
        "centroide_mm": [float(cx), float(cy), cz],
        "n_planos_ocupados": int(len(ocupados)),
    }


def metricas_par(ma: np.ndarray, mb: np.ndarray, grade: Grade, caso_a: str, caso_b: str) -> dict:
    """Parte E (todas as metricas do par) + Parte F (decomposicao A/B/C/D).

    Aplica g5 (mesmo caso) e g9 (grade em mm) antes de qualquer numero.
    """
    guarda_g5(caso_a, caso_b)
    guarda_g9(grade)
    if ma.shape != mb.shape:
        raise RecusaDeGuarda("g6", f"formas incompativeis: {ma.shape} vs {mb.shape}")

    sob = SM.compare_masks(ma, mb, grade.spacing)  # dice, iou, assd, hd95, hd, nsd
    da, db = descritores(ma, grade), descritores(mb, grade)

    vol_a, vol_b = da["volume_mm3"], db["volume_mm3"]
    d_vol = abs(vol_a - vol_b)
    d_vol_pct = d_vol / ((vol_a + vol_b) / 2.0) * 100.0

    ca, cb = np.array(da["centroide_mm"]), np.array(db["centroide_mm"])
    lateral = float(np.hypot(*(ca[:2] - cb[:2])))

    return {
        "objeto": ROTULO_F5,
        # -------- Parte E
        "dice": sob["dice"],
        "iou": sob["iou"],
        "hd95_mm": sob["hd95_mm"],
        "assd_mm": sob["assd_mm"],
        "hd_mm": sob["hd_mm"],
        "dif_volume_mm3": d_vol,
        "dif_volume_pct": d_vol_pct,
        "dif_comprimento_mm": abs(da["comprimento_mm"] - db["comprimento_mm"]),
        "dif_area_transversal_mm2": abs(
            da["area_transversal_media_mm2"] - db["area_transversal_media_mm2"]
        ),
        "dif_raio_caracteristico_mm": abs(
            da["raio_caracteristico_mm"] - db["raio_caracteristico_mm"]
        ),
        "dif_z_sup_mm": abs(da["z_sup_mm"] - db["z_sup_mm"]),
        "dif_z_inf_mm": abs(da["z_inf_mm"] - db["z_inf_mm"]),
        # -------- Parte F (decomposicao da variabilidade)
        "F_A_extensao_mm": abs(da["comprimento_mm"] - db["comprimento_mm"]),
        "F_B_largura_mm": abs(da["raio_caracteristico_mm"] - db["raio_caracteristico_mm"]),
        "F_C_lateral_mm": lateral,
        "F_D_longitudinal_mm": abs(ca[2] - cb[2]),
        # -------- rastro
        "spacing_mm": list(grade.spacing),
        "descritores": {"a": da, "b": db},
    }


# ---------------------------------------------------------------- por caso


def comparar_caso(rtstruct: Path, passo_xy_mm: float = 1.0) -> dict:
    """Todos os C(n,2) pares de observadores de UM caso."""
    reg = carregar_contornos(rtstruct)
    grade = montar_grade(reg, passo_xy_mm=passo_xy_mm)

    mascaras, vazios = {}, {}
    for nome, fatias in reg["observadores"].items():
        mascaras[nome], vazios[nome] = rasterizar(fatias, grade)

    pares = []
    for a, b in itertools.combinations(sorted(mascaras), 2):
        r = metricas_par(mascaras[a], mascaras[b], grade, reg["caso"], reg["caso"])
        r.update({"caso": reg["caso"], "obs_a": a, "obs_b": b})
        pares.append(r)

    return {
        "objeto": ROTULO_F5,
        "colecao": COLECAO,
        "caso": reg["caso"],
        "arquivo": reg["arquivo"],
        "frame_uid": reg["frame_uid"],
        "observadores": sorted(mascaras),
        "grade_mm": {
            "passo_xy_mm": grade.passo_xy_mm,
            "dz_mm": grade.dz_mm,
            "shape_zyx": list(grade.shape),
            "unidade": grade.unidade,
        },
        "planos_internos_vazios_por_observador": vazios,
        "pares": pares,
    }


# ---------------------------------------------------------------- estatistica


def _dist(valores: list) -> dict:
    v = np.asarray([x for x in valores if np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"n": 0}
    q1, med, q3 = (float(x) for x in np.percentile(v, [25, 50, 75]))
    return {
        "n": int(v.size),
        "mediana": med,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "min": float(v.min()),
        "max": float(v.max()),
    }


METRICAS = (
    "dice",
    "iou",
    "hd95_mm",
    "assd_mm",
    "hd_mm",
    "dif_volume_mm3",
    "dif_volume_pct",
    "dif_comprimento_mm",
    "dif_area_transversal_mm2",
    "dif_raio_caracteristico_mm",
    "dif_z_sup_mm",
    "dif_z_inf_mm",
    "F_A_extensao_mm",
    "F_B_largura_mm",
    "F_C_lateral_mm",
    "F_D_longitudinal_mm",
)


def resumir(casos: list) -> dict:
    pares = [p for c in casos for p in c["pares"]]
    return {
        "objeto": ROTULO_F5,
        "colecao": COLECAO,
        "doi": DOI,
        "licenca": LICENCA,
        "roi_prefixo": PREFIXO_OBS,
        "n_casos": len(casos),
        "n_pares": len(pares),
        "n_observadores_por_caso": sorted({len(c["observadores"]) for c in casos}),
        "distribuicoes": {m: _dist([p[m] for p in pares]) for m in METRICAS},
        "planos_internos_vazios": {
            c["caso"]: c["planos_internos_vazios_por_observador"]
            for c in casos
            if any(c["planos_internos_vazios_por_observador"].values())
        },
        "nao_autoriza": list(FRASES_PROIBIDAS),
        "aviso": "nenhuma afirmacao sobre esofago pode ser derivada destes dados",
    }


# ---------------------------------------------------------------- fantoma


def _contornos_esfera(centro, raio_mm: float, z_mm: np.ndarray, n_pts: int = 256) -> list:
    """Esfera como contornos planares em mm — mesma forma que o RTSTRUCT entrega."""
    cx, cy, cz = centro
    t = np.linspace(0.0, 2 * np.pi, n_pts, endpoint=False)
    fatias = []
    for z in z_mm:
        dz = z - cz
        if abs(dz) >= raio_mm:
            continue
        r = float(np.sqrt(raio_mm**2 - dz**2))
        fatias.append((float(z), np.column_stack([cx + r * np.cos(t), cy + r * np.sin(t)])))
    return fatias


def _grade_fantoma(raio_mm: float, extra_mm: float, passo_mm: float, caso: str = "fantoma") -> Grade:
    lim = raio_mm + extra_mm
    n = int(np.ceil(2 * lim / passo_mm)) + 1
    z = -lim + passo_mm * np.arange(n, dtype=float)
    return Grade(-lim, -lim, passo_mm, n, n, z, passo_mm, "mm", caso)


# ---------------------------------------------------------------- autoteste


def _autoteste(verboso: bool = True) -> None:
    """Fantoma de resposta conhecida + controle positivo de cada guarda.

    Duas esferas IGUAIS de raio R deslocadas de d (0 < d <= R) tem resposta
    fechada. Com t = cos(angulo em relacao ao eixo do deslocamento) uniforme na
    superficie, a distancia de um ponto da superficie de A ate a superficie de B
    vale |sqrt(R^2+d^2-2Rdt) - R|; como s^2 = R^2+d^2-2Rdt e uniforme em
    [(R-d)^2, (R+d)^2], sai P(dist <= x) = 4Rx / 4Rd = x/d. Ou seja a distancia
    e UNIFORME em [0, d]. Logo, exatamente:
        HD = d ; HD95 = 0.95 d ; ASSD = d/2
        Dice = (4R+d)(2R-d)^2 / (16 R^3) ; IoU = Dice/(2-Dice)
        deslocamento lateral de centroide = d ; dif. de comprimento = 0
    """

    def diz(*a):
        if verboso:
            print(*a, flush=True)

    R, d, passo = 15.0, 5.0, 1.0
    grade = _grade_fantoma(R, d + 4.0, passo)
    ma, _ = rasterizar(_contornos_esfera((0.0, 0.0, 0.0), R, grade.z_mm), grade)
    mb, _ = rasterizar(_contornos_esfera((d, 0.0, 0.0), R, grade.z_mm), grade)
    r = metricas_par(ma, mb, grade, "fantoma", "fantoma")

    dice_ok = (4 * R + d) * (2 * R - d) ** 2 / (16 * R**3)
    esperado = {
        "dice": dice_ok,
        "iou": dice_ok / (2 - dice_ok),
        "hd_mm": d,
        "hd95_mm": 0.95 * d,
        "assd_mm": d / 2,
        "F_C_lateral_mm": d,
        "F_A_extensao_mm": 0.0,
        "F_D_longitudinal_mm": 0.0,
        "dif_volume_pct": 0.0,
    }
    tol = {  # tolerancia = erro de rasterizacao/quantizacao, ~1 voxel
        "dice": 0.02,
        "iou": 0.03,
        "hd_mm": 1.5 * passo,
        "hd95_mm": 1.5 * passo,
        "assd_mm": 1.0 * passo,
        "F_C_lateral_mm": 0.5 * passo,
        "F_A_extensao_mm": 1.0 * passo,
        "F_D_longitudinal_mm": 0.5 * passo,
        "dif_volume_pct": 2.0,
    }
    for k, esp in esperado.items():
        assert abs(r[k] - esp) <= tol[k], (k, r[k], esp, tol[k])
    diz(
        f"fantoma esferas R={R} d={d} passo={passo}mm: "
        + " ".join(f"{k}={r[k]:.3f}(esp {esperado[k]:.3f})" for k in esperado)
    )

    # fantoma 2: esferas CONCENTRICAS R e R+delta -> so a largura muda
    delta = 3.0
    g2 = _grade_fantoma(R + delta, 4.0, passo)
    m1, _ = rasterizar(_contornos_esfera((0.0, 0.0, 0.0), R, g2.z_mm), g2)
    m2, _ = rasterizar(_contornos_esfera((0.0, 0.0, 0.0), R + delta, g2.z_mm), g2)
    r2 = metricas_par(m1, m2, g2, "fantoma", "fantoma")
    assert abs(r2["F_C_lateral_mm"]) <= 0.5 * passo, r2["F_C_lateral_mm"]
    assert abs(r2["F_D_longitudinal_mm"]) <= 0.5 * passo, r2["F_D_longitudinal_mm"]
    assert abs(r2["F_A_extensao_mm"] - 2 * delta) <= 2.0 * passo, r2["F_A_extensao_mm"]
    assert abs(r2["hd_mm"] - delta) <= 1.5 * passo, r2["hd_mm"]
    assert r2["F_B_largura_mm"] > passo, r2["F_B_largura_mm"]
    diz(
        f"fantoma concentrico delta={delta}mm: F_A={r2['F_A_extensao_mm']:.2f} "
        f"F_B={r2['F_B_largura_mm']:.2f} F_C={r2['F_C_lateral_mm']:.2f} "
        f"F_D={r2['F_D_longitudinal_mm']:.2f} hd={r2['hd_mm']:.2f}"
    )

    # ---- g9 (controle positivo 1/2): grade declarada em indice de voxel
    try:
        metricas_par(ma, mb, Grade(0, 0, 1.0, grade.nx, grade.ny, grade.z_mm, 1.0, "voxel"), "f", "f")
    except RecusaDeGuarda as e:
        assert e.guarda == "g9", e
        diz("g9 controle positivo (unidade='voxel'):", e)
    else:
        raise AssertionError("g9 NAO recusou grade em indice de voxel")

    # ---- g9 (controle positivo 2/2): a mesma forma em escala 2x tem que dobrar
    # a distancia. Um numero medido em INDICE de voxel nao dobraria.
    g_2x = _grade_fantoma(2 * R, 2 * (d + 4.0), 2 * passo)
    a2, _ = rasterizar(_contornos_esfera((0.0, 0.0, 0.0), 2 * R, g_2x.z_mm), g_2x)
    b2, _ = rasterizar(_contornos_esfera((2 * d, 0.0, 0.0), 2 * R, g_2x.z_mm), g_2x)
    r3 = metricas_par(a2, b2, g_2x, "f", "f")
    assert abs(r3["hd95_mm"] - 2 * r["hd95_mm"]) <= 2.0 * passo, (r3["hd95_mm"], r["hd95_mm"])
    assert abs(r3["dice"] - r["dice"]) <= 0.02, (r3["dice"], r["dice"])
    diz(f"g9 escala 2x: hd95 {r['hd95_mm']:.2f} -> {r3['hd95_mm']:.2f} mm (dice preservado)")

    # ---- g5 (controle positivo): par entre casos diferentes
    try:
        metricas_par(ma, mb, grade, "interobs05", "interobs06")
    except RecusaDeGuarda as e:
        assert e.guarda == "g5", e
        diz("g5 controle positivo (casos diferentes):", e)
    else:
        raise AssertionError("g5 NAO recusou par entre casos diferentes")

    # ---- g6 (controle positivo): observadores em redes de z incompativeis
    reg_ruim = {
        "caso": "sintetico",
        "n_frames": 1,
        "observadores": {
            "A": [(0.0, np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])),
                  (5.0, np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]))],
            "B": [(2.5, np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])),
                  (5.7, np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]))],
        },
    }
    try:
        montar_grade(reg_ruim)
    except RecusaDeGuarda as e:
        assert e.guarda == "g6", e
        diz("g6 controle positivo (redes de z incompativeis):", e)
    else:
        raise AssertionError("g6 NAO recusou grades incompativeis")

    # ---- g10 (controle positivo): contorno num plano que a grade nao tem
    g_furada = Grade(-20, -20, 1.0, 40, 40, np.array([0.0, 5.0, 10.0]), 5.0, "mm", "f")
    try:
        rasterizar([(7.5, np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 3.0]]))], g_furada)
    except RecusaDeGuarda as e:
        assert e.guarda == "g10", e
        diz("g10 controle positivo (fatia fora da grade):", e)
    else:
        raise AssertionError("g10 NAO recusou contorno fora da grade")

    # ---- g12 (controle positivo): tentativa de escrever afirmacao sobre esofago
    for payload in (
        {"conclusao": "a concordancia do esofago e 0.72"},
        {"esophagus": {"dice": 0.7}},
        ["ok", ["nested", "Esofago torácico medido"]],
    ):
        try:
            guarda_g12(payload)
        except RecusaDeGuarda as e:
            assert e.guarda == "g12", e
        else:
            raise AssertionError(f"g12 NAO recusou {payload!r}")
    guarda_g12({"objeto": ROTULO_F5, "nao_autoriza": list(FRASES_PROIBIDAS)})  # tem que passar
    diz("g12 controle positivo: 3 payloads recusados, rotulo/negativas liberados")

    diz("AUTOTESTE OK —", ROTULO_F5)


# ---------------------------------------------------------------- CLI


def _fmt(d: dict) -> str:
    if not d.get("n"):
        return "sem dado"
    return (
        f"mediana {d['mediana']:.3f} | IQR {d['q1']:.3f}-{d['q3']:.3f} ({d['iqr']:.3f}) | "
        f"min {d['min']:.3f} | max {d['max']:.3f} | n {d['n']}"
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=f"Concordancia interobservador. {ROTULO_F5}")
    p.add_argument("--entrada", type=Path, default=ENTRADA, help="arvore com os RTSTRUCT")
    p.add_argument("--saida", type=Path, default=SAIDA)
    # ponytail: passo-xy 1.0 mm por padrao (a TC da colecao tem ~0,98 mm no plano).
    # Sensibilidade JA medida: rodando tudo com --passo-xy 0.5 as medianas nao se
    # movem (dice 0.840 -> 0.840, hd95 5.099 -> 5.099, assd 1.471 -> 1.378 mm).
    # Ou seja, os numeros nao sao artefato de rasterizacao. Refazer so se o passo
    # em z mudar — ele, sim, e o eixo que quantiza (5 mm).
    p.add_argument("--passo-xy", type=float, default=1.0, help="passo da grade no plano, mm")
    p.add_argument("--autoteste", action="store_true")
    a = p.parse_args(argv)

    if a.autoteste:
        _autoteste()
        return 0

    print(f"### {ROTULO_F5}", flush=True)
    print(f"colecao {COLECAO} · DOI {DOI} · licenca {LICENCA} · ROI {PREFIXO_OBS}1..5\n", flush=True)

    import pydicom

    # uma serie = um diretorio; so RTSTRUCT e candidato (o resto da colecao e CT
    # e SEG do tumor, que nao carregam contorno de observador nomeado).
    series = sorted({p.parent for p in a.entrada.rglob("*.dcm")})
    casos, recusas, ignorados = [], [], {}
    for d in series:
        dcm = sorted(d.glob("*.dcm"))[0]
        mod = str(getattr(pydicom.dcmread(str(dcm), stop_before_pixels=True), "Modality", "?"))
        if mod != "RTSTRUCT":
            ignorados[mod] = ignorados.get(mod, 0) + 1
            continue
        try:
            casos.append(comparar_caso(dcm, passo_xy_mm=a.passo_xy))
        except RecusaDeGuarda as e:
            recusas.append({"arquivo": str(dcm), "guarda": e.guarda, "motivo": str(e)})
        except (ValueError, AttributeError) as e:
            recusas.append({"arquivo": str(dcm), "guarda": "leitura", "motivo": str(e)})
        else:
            c = casos[-1]
            print(f"{c['caso']}: {len(c['observadores'])} obs, {len(c['pares'])} pares", flush=True)
    print(f"series ignoradas por modalidade: {ignorados or 'nenhuma'}", flush=True)

    if not casos:
        print("nenhum caso lido")
        return 1

    resumo = resumir(casos)
    resumo["recusas"] = recusas
    resumo["series_ignoradas_por_modalidade"] = ignorados

    guarda_g12(resumo)  # g12 antes de gravar
    guarda_g12(casos)

    a.saida.mkdir(parents=True, exist_ok=True)
    (a.saida / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (a.saida / "pares.json").write_text(
        json.dumps(casos, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"\n--- distribuicao par-a-par ({resumo['n_pares']} pares, {resumo['n_casos']} casos) ---")
    for m in METRICAS:
        print(f"  {m:<28} {_fmt(resumo['distribuicoes'][m])}")
    print(f"\nrecusas de guarda: {len(recusas)}")
    for r in recusas:
        print(f"  [{r['guarda']}] {Path(r['arquivo']).parent.name}: {r['motivo'][:140]}")
    print(f"\n### {ROTULO_F5}")
    for f in FRASES_PROIBIDAS:
        print("  " + f)
    print(f"\ngravado em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
