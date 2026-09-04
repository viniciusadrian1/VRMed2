"""
Benchmark A/B de SIGMA da gaussiana, agrupado por FAIXA DE CALIBRE (mm).

Pergunta: o sigma automático (`max(0.6, 0.5·zoom_max)`) custa quanto de fidelidade,
e esse custo depende da espessura característica da estrutura?

Variantes comparadas (todas as três primeiras com marching_cubes, o BASELINE OFICIAL):
  sigma_auto   — sigma_mm=None (comportamento atual do pipeline)
  sigma_zero   — sigma_mm=0.0 (sem borrar a ocupação)
  sigma_meio   — sigma_mm = 0.5 × sigma automático
  surface_nets — candidato EXPERIMENTAL, nunca baseline (guardrail 8)

Tiers (declarados em toda linha, guardrail 3):
  Tier1 — fidelidade da RECONSTRUÇÃO à máscara de entrada. Não diz nada sobre a
          qualidade da segmentação.
  Tier3 — validação contra FANTOMA analítico: área e volume têm resposta fechada.
  Tier2 (acurácia da segmentação vs ground truth independente) NÃO EXISTE neste
          repositório e não é estimado aqui.

Referências de área/volume (guardrail: nunca chamar proxy de verdade):
  Tier3 — área e volume ANALÍTICOS do fantoma (erro real).
  Tier1 — volume da máscara (voxels × spacing); área é PROXY: a área da malha
          gerada com sigma=0 e taubin=0, a que mais adere à máscara. Não existe
          área verdadeira para uma máscara de voxel — a coluna diz isso.

Cada erro fica na sua coluna; nada é agregado numa nota só (guardrail 4).

Uso:
  python scripts/validation/benchmark_sigma.py --out .clinica-dados/benchmark-sigma
  python scripts/validation/benchmark_sigma.py --out ... --so-fantomas
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

if __package__ in (None, ""):  # rodado como script: a raiz do repo não está no path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.geometry.reconstruction import (  # noqa: E402
    _sigma_padrao,  # importado (e não recopiado) para não sair de sincronia com o pipeline
    reconstruct_surface,
    zooms_de,
)
from scripts.validation.mesh_metrics import comparar_mascara_malha  # noqa: E402
from scripts.validation.phantom import cilindro, esfera, tubo_fino  # noqa: E402
from scripts.validation.topology_metrics import (  # noqa: E402
    comparar_continuidade,
    qualidade_topologica,
)

TIER1 = "Tier1"  # fidelidade da reconstrução à máscara
TIER3 = "Tier3"  # fantoma analítico

# Faixas de CALIBRE (espessura característica em mm), não de volume.
FAIXAS: tuple[tuple[str, float, float], ...] = (
    ("<3mm", 0.0, 3.0),
    ("3-10mm", 3.0, 10.0),
    ("10-30mm", 10.0, 30.0),
    (">30mm", 30.0, float("inf")),
)
ORDEM_FAIXAS = tuple(f[0] for f in FAIXAS)

# sigma_mm: None = automático; "meio" é resolvido por alvo (0.5 × automático).
VARIANTES: dict[str, dict[str, Any]] = {
    "sigma_auto": {"method": "marching_cubes", "sigma_mm": None},
    "sigma_zero": {"method": "marching_cubes", "sigma_mm": 0.0},
    "sigma_meio": {"method": "marching_cubes", "sigma_mm": "meio"},
    "surface_nets": {"method": "surface_nets", "sigma_mm": None},
}
BASELINE = "sigma_auto"
EXPERIMENTAL = ("surface_nets",)

SPACINGS_FANTOMA: tuple[tuple[str, tuple[float, float, float]], ...] = (
    ("aniso", (0.7, 0.7, 1.25)),
    ("iso", (0.7, 0.7, 0.7)),
)

# (nome, calibre_mm, construtor -> (mask, affine), área analítica, volume analítico)
_FANTOMAS: tuple[tuple[str, float, str, dict[str, float]], ...] = (
    ("tubo_2mm", 2.0, "tubo", {"d": 2.0, "h": 30.0}),
    ("tubo_5mm", 5.0, "tubo", {"d": 5.0, "h": 30.0}),
    ("tubo_8mm", 8.0, "tubo", {"d": 8.0, "h": 30.0}),
    ("tubo_20mm", 20.0, "cilindro", {"d": 20.0, "h": 40.0}),
    ("esfera_20mm", 20.0, "esfera", {"d": 20.0}),
    ("esfera_40mm", 40.0, "esfera", {"d": 40.0}),
    ("cilindro_40mm", 40.0, "cilindro", {"d": 40.0, "h": 40.0}),
)

REAIS_TORAX = ("aorta", "trachea", "esophagus", "heart")
REAIS_CTA = ("pulmonary_vein", "brachiocephalic_trunk", "common_carotid_artery_left")

COLUNAS = (
    "alvo", "tier", "faixa_calibre", "calibre_mm", "spacing_mm", "variante", "metodo",
    "sigma_mm_usado", "estrutura_preservada", "dice_reconstrucao", "assd_mm", "hd95_mm",
    "volume_error_pct", "volume_ref_mm3", "volume_ref_tipo",
    "area_error_pct", "area_mm2", "area_ref_mm2", "area_ref_tipo",
    "watertight", "n_componentes", "delta_componentes", "fracao_maior_componente",
    "tris", "vertices", "tempo_s", "erro",
)

METRICAS_AGREGADAS = (
    "dice_reconstrucao", "assd_mm", "hd95_mm", "volume_error_pct", "area_error_pct",
    "n_componentes", "delta_componentes", "fracao_maior_componente", "tris", "vertices", "tempo_s",
)


# ------------------------------------------------------------------ alvos


@dataclass
class Alvo:
    """Uma estrutura (real ou fantoma) com suas referências declaradas."""

    nome: str
    tier: str
    mask: np.ndarray
    affine: np.ndarray
    calibre_mm: float
    volume_ref_mm3: float
    volume_ref_tipo: str
    area_ref_mm2: float | None = None
    area_ref_tipo: str = ""
    rotulo_spacing: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def faixa(self) -> str:
        for nome, lo, hi in FAIXAS:
            if lo <= self.calibre_mm < hi:
                return nome
        return ORDEM_FAIXAS[-1]


def calibre_de(mask: np.ndarray, zooms: np.ndarray) -> float:
    """Espessura característica em mm: 2 × mediana da distância ao fundo no esqueleto.

    O esqueleto é a linha central; a EDT nele é o raio local. A mediana ignora as
    pontas afiladas, então o número é o calibre TÍPICO da estrutura, não o máximo.
    Aproximado por natureza: serve para AGRUPAR em faixas, não como medida.
    """
    from scipy import ndimage
    from skimage.morphology import skeletonize

    mask = np.asarray(mask) > 0.5
    if not mask.any():
        return 0.0
    raio = ndimage.distance_transform_edt(mask, sampling=zooms)
    esqueleto = skeletonize(mask)
    amostras = raio[esqueleto] if esqueleto.any() else raio[mask]
    return float(2.0 * np.median(amostras))


def recortar(mask: np.ndarray, affine: np.ndarray, margem_vox: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Recorta a máscara na sua bounding box + margem, corrigindo a origem do affine.

    Não muda geometria nenhuma: as coordenadas físicas (mm RAS) de cada voxel
    continuam idênticas, só o FOV vazio some. É o que torna as estruturas reais
    mensuráveis em minutos em vez de horas — a EDT e o esqueleto das métricas
    varrem o array inteiro, e num 512×512×261 quase tudo é fundo.

    A margem não "abre" estrutura cortada pelo FOV: se ela já encostava na borda
    original, o recorte é limitado pela borda e ela continua encostando.
    """
    idx = np.nonzero(mask)
    inicio = [max(0, int(i.min()) - margem_vox) for i in idx]
    fim = [min(s, int(i.max()) + margem_vox + 1) for i, s in zip(idx, mask.shape)]
    fatia = tuple(slice(a, b) for a, b in zip(inicio, fim))
    novo = np.asarray(affine, dtype=float).copy()
    novo[:3, 3] = affine[:3, :3] @ np.array(inicio, dtype=float) + affine[:3, 3]
    return np.ascontiguousarray(mask[fatia]), novo


def _construir_fantoma(tipo: str, dims: dict[str, float], spacing: tuple[float, float, float]):
    """Devolve (mask, affine, area_analitica_mm2, volume_analitico_mm3)."""
    r = dims["d"] / 2.0
    if tipo == "esfera":
        mask, affine = esfera(dims["d"], spacing=spacing)
        return mask, affine, 4.0 * np.pi * r**2, np.pi / 6.0 * dims["d"] ** 3
    h = dims["h"]
    if tipo == "tubo":
        mask, affine = tubo_fino(dims["d"], h, spacing=spacing)
    else:
        mask, affine = cilindro(dims["d"], h, spacing=spacing, eixo=2)
    # cilindro FECHADO: lateral + as duas tampas
    return mask, affine, 2.0 * np.pi * r * h + 2.0 * np.pi * r**2, np.pi / 4.0 * dims["d"] ** 2 * h


def alvos_fantoma() -> list[Alvo]:
    alvos: list[Alvo] = []
    for rotulo, spacing in SPACINGS_FANTOMA:
        for nome, calibre, tipo, dims in _FANTOMAS:
            mask, affine, area, volume = _construir_fantoma(tipo, dims, spacing)
            alvos.append(
                Alvo(
                    nome=f"{nome}[{rotulo}]",
                    tier=TIER3,
                    mask=mask,
                    affine=affine,
                    calibre_mm=calibre,  # calibre NOMINAL: no fantoma ele é conhecido
                    volume_ref_mm3=volume,
                    volume_ref_tipo="analitico",
                    area_ref_mm2=area,
                    area_ref_tipo="analitico",
                    rotulo_spacing=rotulo,
                    extra={"voxels": int(mask.sum()), "shape": list(mask.shape)},
                )
            )
    return alvos


def alvos_reais(raiz: Path) -> list[Alvo]:
    """Estruturas reais: calibre MEDIDO, volume de referência = volume da máscara."""
    import nibabel as nib

    fontes = [(raiz / ".clinica-dados" / "torax-alta_masks", n) for n in REAIS_TORAX]
    fontes += [(raiz / ".clinica-dados" / "cta-cardio" / "masks", n) for n in REAIS_CTA]

    alvos: list[Alvo] = []
    for pasta, nome in fontes:
        caminho = pasta / f"{nome}.nii.gz"
        if not caminho.exists():
            print(f"  [pulado] {caminho} não existe", file=sys.stderr)
            continue
        img = nib.load(str(caminho))
        mask = np.asarray(img.dataobj) > 0.5
        if not mask.any():
            print(f"  [pulado] {nome}: máscara vazia", file=sys.stderr)
            continue
        shape_original = list(mask.shape)
        mask, affine = recortar(mask, img.affine)
        zooms = zooms_de(affine)
        alvos.append(
            Alvo(
                nome=f"{nome}[{pasta.parent.name if pasta.name == 'masks' else pasta.name}]",
                tier=TIER1,
                mask=mask,
                affine=affine,
                calibre_mm=round(calibre_de(mask, zooms), 3),
                volume_ref_mm3=float(mask.sum()) * float(np.prod(zooms)),
                volume_ref_tipo="mascara_voxels",
                area_ref_mm2=None,  # preenchido pelo proxy sigma=0/taubin=0
                area_ref_tipo="proxy_sigma0_taubin0",
                extra={
                    "voxels": int(mask.sum()),
                    "shape": list(mask.shape),
                    "shape_original": shape_original,
                },
            )
        )
    return alvos


def area_proxy_mm2(alvo: Alvo) -> float | None:
    """Área da malha sigma=0 / taubin=0 — a que mais adere à máscara.

    NÃO é a área verdadeira da estrutura (que não existe para uma máscara de
    voxel): é o piso de comparação para medir quanto cada sigma encolhe a
    superfície. Fica rotulado como proxy em toda saída.
    """
    r = reconstruct_surface(alvo.mask, alvo.affine, method="marching_cubes", sigma_mm=0.0, taubin_iters=0)
    return None if r is None else float(r.mesh.area) * 1e6  # m² -> mm²


# ------------------------------------------------------------------ medição


def _erro_pct(medido: float, referencia: float | None) -> float | None:
    if referencia is None or referencia == 0:
        return None
    return (medido - referencia) / referencia * 100.0


def _finito(v: Any) -> float | None:
    if v is None:
        return None
    v = float(v)
    return v if np.isfinite(v) else None


def medir(alvo: Alvo, variante: str) -> dict[str, Any]:
    """Uma linha (alvo × variante). Falha vira linha com `erro`, sem derrubar a matriz."""
    cfg = VARIANTES[variante]
    zooms = zooms_de(alvo.affine)
    sigma = cfg["sigma_mm"]
    if sigma == "meio":
        sigma = 0.5 * _sigma_padrao(zooms)

    linha: dict[str, Any] = {c: None for c in COLUNAS}
    linha.update(
        alvo=alvo.nome,
        tier=alvo.tier,
        faixa_calibre=alvo.faixa,
        calibre_mm=alvo.calibre_mm,
        spacing_mm=[round(float(z), 4) for z in zooms],
        variante=variante,
        metodo=cfg["method"],
        # o surface_nets não usa gaussiana: registrar "-" é mais honesto que registrar um sigma
        sigma_mm_usado=None if cfg["method"] == "surface_nets" else (
            round(float(sigma), 4) if sigma is not None else round(float(_sigma_padrao(zooms)), 4)
        ),
        volume_ref_mm3=round(alvo.volume_ref_mm3, 4),
        volume_ref_tipo=alvo.volume_ref_tipo,
        area_ref_mm2=None if alvo.area_ref_mm2 is None else round(alvo.area_ref_mm2, 3),
        area_ref_tipo=alvo.area_ref_tipo,
        estrutura_preservada=False,
    )

    try:
        r = reconstruct_surface(alvo.mask, alvo.affine, method=cfg["method"], sigma_mm=sigma)
        if r is None:
            # perda TOTAL: a estrutura não sobreviveu à suavização. É resultado, não erro.
            linha["erro"] = "ausente: reconstruct_surface devolveu None"
            return linha
        malha = r.mesh
        linha["tempo_s"] = round(r.tempo_s, 4)
        linha["tris"] = int(len(malha.faces))
        linha["vertices"] = int(len(malha.vertices))
        linha["estrutura_preservada"] = bool(len(malha.faces) > 0 and abs(float(malha.volume)) > 0.0)

        topo = qualidade_topologica(malha)
        linha["watertight"] = topo["watertight"]
        linha["n_componentes"] = topo["n_componentes"]
        area_mm2 = topo["area_mm2"]
        linha["area_mm2"] = area_mm2
        linha["area_error_pct"] = _finito_arred(_erro_pct(area_mm2, alvo.area_ref_mm2))

        met = comparar_mascara_malha(alvo.mask, malha, alvo.affine)
        linha["dice_reconstrucao"] = _finito_arred(met["dice"], 4)
        linha["assd_mm"] = _finito_arred(met["assd_mm"], 4)
        linha["hd95_mm"] = _finito_arred(met["hd95_mm"], 4)
        # Tier3 tem volume analítico; Tier1 só tem o volume da máscara.
        volume_mm3 = abs(float(malha.volume)) * 1e9
        linha["volume_error_pct"] = _finito_arred(_erro_pct(volume_mm3, alvo.volume_ref_mm3))

        cont = comparar_continuidade(alvo.mask, malha, alvo.affine)
        linha["delta_componentes"] = cont["delta_componentes"]
        linha["fracao_maior_componente"] = cont["malha"]["fracao_maior_componente"]
    except Exception as exc:  # uma variante que quebra não derruba as outras
        linha["erro"] = f"{type(exc).__name__}: {exc}"
        print(f"  [erro] {alvo.nome} x {variante}: {linha['erro']}", file=sys.stderr)
    return linha


def _finito_arred(v: Any, casas: int = 3) -> float | None:
    v = _finito(v)
    return None if v is None else round(v, casas)


def rodar(alvos: list[Alvo]) -> list[dict[str, Any]]:
    linhas: list[dict[str, Any]] = []
    for alvo in alvos:
        if alvo.tier == TIER1 and alvo.area_ref_mm2 is None:
            alvo.area_ref_mm2 = area_proxy_mm2(alvo)
        print(
            f"\n=== {alvo.nome}  {alvo.tier}  calibre={alvo.calibre_mm:g} mm ({alvo.faixa})  "
            f"voxels={alvo.extra.get('voxels')}  shape={alvo.extra.get('shape')}"
        )
        for variante in VARIANTES:
            linha = medir(alvo, variante)
            linhas.append(linha)
            print(
                f"  {variante:13s} sigma={_fmt(linha['sigma_mm_usado'], 2):>5s} "
                f"preservada={str(linha['estrutura_preservada']):5s} "
                f"dice={_fmt(linha['dice_reconstrucao'], 4)} assd={_fmt(linha['assd_mm'])} "
                f"hd95={_fmt(linha['hd95_mm'], 2)} dV%={_fmt(linha['volume_error_pct'], 2)} "
                f"dA%={_fmt(linha['area_error_pct'], 2)} comp={_fmt(linha['n_componentes'])} "
                f"tris={_fmt(linha['tris'])} t={_fmt(linha['tempo_s'], 2)}s"
                + (f"  !! {linha['erro']}" if linha["erro"] else "")
            )
    return linhas


# ------------------------------------------------------------------ saída


def _fmt(v: Any, casas: int = 3) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    return f"{v:.{casas}f}" if isinstance(v, float) else str(v)


def _mediana(valores: list[Any]) -> float | None:
    limpos = [v for v in valores if v is not None]
    return statistics.median(limpos) if limpos else None


def _bloco_tier(linhas: list[dict[str, Any]], tier: str) -> list[str]:
    do_tier = [l for l in linhas if l["tier"] == tier]
    if not do_tier:
        return []
    out: list[str] = []
    for faixa in ORDEM_FAIXAS:
        da_faixa = [l for l in do_tier if l["faixa_calibre"] == faixa]
        if not da_faixa:
            continue
        alvos = sorted({l["alvo"] for l in da_faixa})
        out += [
            f"### calibre {faixa}", "",
            f"Alvos ({len(alvos)}): {', '.join(alvos)}", "",
            "| variante | n_ok | preservada | dice | assd_mm | hd95_mm | volume_err_% | area_err_% |"
            " watertight | n_comp | d_comp | frac_maior | tris | verts | tempo_s |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for variante in VARIANTES:
            do_par = [l for l in da_faixa if l["variante"] == variante]
            if not do_par:
                continue
            ok = [l for l in do_par if l["erro"] is None]
            med = {m: _mediana([l[m] for l in ok]) for m in METRICAS_AGREGADAS}
            n_pres = sum(1 for l in do_par if l["estrutura_preservada"])
            n_wt = sum(1 for l in ok if l["watertight"])
            marca = " *" if variante in EXPERIMENTAL else ""
            out.append(
                f"| {variante}{marca} | {len(ok)}/{len(do_par)} | {n_pres}/{len(do_par)} | "
                f"{_fmt(med['dice_reconstrucao'], 4)} | {_fmt(med['assd_mm'])} | "
                f"{_fmt(med['hd95_mm'], 2)} | {_fmt(med['volume_error_pct'], 2)} | "
                f"{_fmt(med['area_error_pct'], 2)} | {n_wt}/{len(ok)} | "
                f"{_fmt(med['n_componentes'], 0)} | {_fmt(med['delta_componentes'], 0)} | "
                f"{_fmt(med['fracao_maior_componente'], 4)} | {_fmt(med['tris'], 0)} | "
                f"{_fmt(med['vertices'], 0)} | {_fmt(med['tempo_s'], 2)} |"
            )
        out.append("")
    return out


def montar_summary(linhas: list[dict[str, Any]]) -> str:
    n_alvos = len({l["alvo"] for l in linhas})
    out = [
        "# Benchmark de sigma por faixa de calibre", "",
        f"{n_alvos} alvos × {len(VARIANTES)} variantes = {len(linhas)} linhas. "
        f"Baseline oficial: `{BASELINE}` (marching_cubes). Variante marcada com `*` é "
        "candidato EXPERIMENTAL, não baseline.", "",
        "Faixas são de CALIBRE (espessura característica em mm), não de volume. No Tier3 o "
        "calibre é o diâmetro nominal do fantoma; no Tier1 é `2 × mediana(EDT no esqueleto)` — "
        "aproximado, serve para agrupar, não como medida.", "",
        "Agregação = MEDIANA por (tier, faixa, variante). Cada erro na sua coluna; nada é "
        "somado numa nota única. Linhas com `erro` (inclusive estrutura ausente) ficam fora "
        "das medianas, mas contam em `n_ok` e `preservada`.", "",
        "## Tiers", "",
        "- **Tier1** — fidelidade da RECONSTRUÇÃO à máscara de entrada. Dice/ASSD/HD95 medem "
        "a malha rasterizada de volta contra a máscara: uma máscara errada com reconstrução "
        "perfeita dá dice ~1 aqui.",
        "- **Tier2** — acurácia da segmentação contra ground truth independente. **AUSENTE "
        "neste repositório**; nenhuma linha abaixo é Tier2 e nada aqui estima Tier2.",
        "- **Tier3** — fantoma analítico: área e volume têm resposta fechada, então "
        "`area_error_%` e `volume_error_%` são erro REAL.", "",
        "## Referências de área e volume", "",
        "| tier | volume de referência | área de referência |",
        "|---|---|---|",
        "| Tier3 | analítico (esfera π/6·d³; cilindro π/4·d²·h) | analítica (esfera 4πr²; "
        "cilindro 2πrh + 2πr²) |",
        "| Tier1 | volume da máscara (voxels × spacing) | **PROXY**: área da malha com "
        "sigma=0 e taubin=0 |", "",
        "> No Tier1 **não existe área verdadeira** para uma máscara de voxel. A área de "
        "referência é a da malha que mais adere à máscara (sigma=0, taubin=0) — um piso de "
        "comparação entre variantes, **não** a área da estrutura. Ler `area_err_%` do Tier1 "
        "como \"quanto esta variante encolhe a superfície em relação à malha mais aderente\", "
        "nunca como erro absoluto.", "",
        "Colunas: `preservada` = a malha existe e tem volume > 0. `d_comp` = componentes da "
        "malha rasterizada menos os da máscara (>0 = fragmentou). `frac_maior` = fração de "
        "voxels no maior componente da malha rasterizada.", "",
    ]

    bloco3 = _bloco_tier(linhas, TIER3)
    if bloco3:
        out += ["## Tier3 — fantomas analíticos", ""] + bloco3
    bloco1 = _bloco_tier(linhas, TIER1)
    if bloco1:
        out += ["## Tier1 — estruturas reais (fidelidade à máscara)", ""] + bloco1
    out += ["## Tier2 — ausente", "",
            "Não há ground truth de segmentação independente neste repositório. "
            "Nenhum número acima pode ser lido como acurácia de segmentação.", ""]
    return "\n".join(out)


def gravar(linhas: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "benchmark_sigma.json").write_text(
        json.dumps(
            {
                "variantes": {k: {**v, "experimental": k in EXPERIMENTAL} for k, v in VARIANTES.items()},
                "baseline": BASELINE,
                "faixas_calibre_mm": [{"faixa": n, "min": lo, "max": hi} for n, lo, hi in FAIXAS],
                "tier2": "ausente: sem ground truth de segmentação independente no repositório",
                "resultados": linhas,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with (out_dir / "benchmark_sigma.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for l in linhas:
            w.writerow({**l, "spacing_mm": "x".join(f"{z:g}" for z in l["spacing_mm"])})
    (out_dir / "summary_sigma.md").write_text(montar_summary(linhas), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark A/B de sigma por faixa de calibre")
    ap.add_argument("--out", required=True, type=Path, help="diretório de saída")
    ap.add_argument("--so-fantomas", action="store_true", help="pula as estruturas reais (Tier3 apenas)")
    args = ap.parse_args(argv)

    raiz = Path(__file__).resolve().parents[2]
    alvos = alvos_fantoma()
    if not args.so_fantomas:
        alvos += alvos_reais(raiz)

    linhas = rodar(alvos)
    if not linhas:
        print("erro: nenhum alvo utilizável", file=sys.stderr)
        return 2

    gravar(linhas, args.out)
    print()
    print(montar_summary(linhas))
    print(f"gravado em: {args.out.resolve()}")
    return 0


def _autoteste() -> None:
    """Checks mínimos: faixa de calibre, referências analíticas e medição de uma variante."""
    mask, affine = tubo_fino(5.0, 30.0, spacing=(0.7, 0.7, 0.7))
    c = calibre_de(mask, zooms_de(affine))
    assert 3.0 <= c <= 7.0, f"calibre medido {c:.2f} mm fora do esperado para tubo de 5 mm"

    a = alvos_fantoma()[0]
    assert a.tier == TIER3 and a.faixa == "<3mm", (a.tier, a.faixa, a.calibre_mm)

    _m, _aff, area, vol = _construir_fantoma("esfera", {"d": 20.0}, (0.7, 0.7, 0.7))
    assert abs(area - 4 * np.pi * 100.0) < 1e-9 and abs(vol - np.pi / 6 * 8000.0) < 1e-9

    # recorte não pode mover nada: mesmo nº de voxels e mesma posição física do 1º voxel
    grande = np.zeros((60, 70, 80), dtype=bool)
    grande[20:30, 31:44, 55:60] = True
    aff = np.diag([0.7, 0.7, 1.25, 1.0])
    aff[:3, 3] = [-11.0, 22.0, -333.0]
    cortada, aff_c = recortar(grande, aff)
    assert int(cortada.sum()) == int(grande.sum()) and cortada.shape < grande.shape
    p0 = np.array(np.nonzero(grande))[:, 0].astype(float)
    p0c = np.array(np.nonzero(cortada))[:, 0].astype(float)
    mm, mm_c = aff[:3, :3] @ p0 + aff[:3, 3], aff_c[:3, :3] @ p0c + aff_c[:3, 3]
    assert np.allclose(mm, mm_c), f"recorte moveu a estrutura: {mm} vs {mm_c}"

    linha = medir(a, "sigma_zero")
    assert linha["tier"] == TIER3 and linha["volume_ref_tipo"] == "analitico", linha
    assert linha["erro"] is None and linha["estrutura_preservada"], linha
    print("autoteste OK:", json.dumps({k: linha[k] for k in ("alvo", "faixa_calibre", "dice_reconstrucao",
                                                             "volume_error_pct", "area_error_pct")}))


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(main())
