"""
Benchmark da SUAVIZAÇÃO NO DOMÍNIO DA MALHA, agrupado por faixa de calibre (mm).

Pergunta: mais iterações de Taubin — ou trocar Taubin por windowed_sinc — melhoram
a superfície sem custar volume, e isso depende da espessura da estrutura?

Todas as variantes rodam com `marching_cubes` e `sigma_mm=0.0` (o extrator e o
borramento ficam FIXOS): a única coisa que muda entre elas é o filtro de malha.

  V0_taubin4  — taubin_iters=4   ← BASELINE CONGELADO (default vigente da MASTER)
  V1_taubin8  — taubin_iters=8
  V2_taubin12 — taubin_iters=12
  V3_taubin20 — taubin_iters=20
  V4_wsinc    — mesh_smoothing="windowed_sinc", ws_iters=20, ws_pass_band=0.1

Tiers (declarados em toda linha):
  Tier1 — fidelidade da RECONSTRUÇÃO à máscara. Não diz nada sobre a segmentação.
  Tier3 — fantoma analítico: volume, área e dimensão têm resposta fechada, então
          o erro é ABSOLUTO. É o único tier onde "erro" quer dizer erro.
  Tier2 — acurácia da segmentação contra ground truth independente: AUSENTE neste
          repositório. Nada aqui estima Tier2.

ARMADILHA do Tier1 (repetida na tabela): com `sigma_mm=0.0` a malha rasterizada de
volta reproduz a máscara por construção, então `dice`, `assd` e `hd95` saem
tautologicamente perfeitos. Essas três colunas NÃO são critério de promoção.

Este arquivo não altera nenhum default do pipeline: ele só chama
`reconstruct_surface` com kwargs explícitos.

Uso:
  python scripts/validation/benchmark_smoothing.py --out .clinica-dados/benchmark-smoothing
  python scripts/validation/benchmark_smoothing.py --out ... --so-fantomas
  python scripts/validation/benchmark_smoothing.py --autoteste
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

if __package__ in (None, ""):  # rodado como script: a raiz do repo não está no path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.geometry.coordinates import MM_PARA_M, M_PARA_MM, gltf_m_para_ras_mm  # noqa: E402
from scripts.geometry.reconstruction import reconstruct_surface, zooms_de  # noqa: E402
from scripts.validation.benchmark_sigma import (  # noqa: E402  (reaproveitado, não recopiado)
    _FANTOMAS,
    ORDEM_FAIXAS,
    TIER1,
    TIER3,
    Alvo,
    _bloco_tier,
    _erro_pct,
    _finito_arred,
    _fmt,
    _mediana,
    alvos_fantoma,
    alvos_reais,
    area_proxy_mm2,
    gravar,
)
from scripts.validation.mesh_metrics import comparar_mascara_malha  # noqa: E402
from scripts.validation.phantom import medir_esfera  # noqa: E402
from scripts.validation.topology_metrics import (  # noqa: E402
    comparar_continuidade,
    comparar_topologia,
    qualidade_topologica,
)

# --------------------------------------------------------------- variantes

VARIANTES: dict[str, dict[str, Any]] = {
    "V0_taubin4": {"method": "marching_cubes", "sigma_mm": 0.0, "taubin_iters": 4,
                   "mesh_smoothing": "taubin"},
    "V1_taubin8": {"method": "marching_cubes", "sigma_mm": 0.0, "taubin_iters": 8,
                   "mesh_smoothing": "taubin"},
    "V2_taubin12": {"method": "marching_cubes", "sigma_mm": 0.0, "taubin_iters": 12,
                    "mesh_smoothing": "taubin"},
    "V3_taubin20": {"method": "marching_cubes", "sigma_mm": 0.0, "taubin_iters": 20,
                    "mesh_smoothing": "taubin"},
    "V4_wsinc": {"method": "marching_cubes", "sigma_mm": 0.0, "taubin_iters": 4,
                 "mesh_smoothing": "windowed_sinc", "ws_iters": 20, "ws_pass_band": 0.1},
}
BASELINE = "V0_taubin4"  # CONGELADO: não pode ser alterado durante o experimento
EXPERIMENTAL: tuple[str, ...] = ()  # nenhuma variante aqui é candidato experimental de MÉTODO

# Limiar declarado de "relevante": mudança de pelo menos este número de PONTOS
# PERCENTUAIS no módulo do erro mediano da faixa. Não é intervalo de confiança
# nem resultado de teste estatístico — é um corte escolhido e declarado, abaixo
# do qual o benchmark se recusa a chamar duas variantes de diferentes.
LIMIAR_RELEVANTE_PP = 1.0

AMOSTRAS_SDF = 20_000  # pontos amostrados na malha para distância à superfície analítica

# --------------------------------------------------------------- fantomas

# Acrescenta ao conjunto do benchmark de sigma um fantoma COM CAVIDADE (lúmen
# passante): sem ele não há como testar "a suavização fecha o lúmen?".
# Parede de 2 mm -> cai na faixa <3mm, que é onde o risco é maior.
FANTOMAS = _FANTOMAS + (
    ("tubo_oco_10_6mm", 2.0, "tubo_oco", {"de": 10.0, "di": 6.0, "h": 20.0}),
)
# genus esperado da malha fechada, por tipo de fantoma. Sólido simples = 0;
# tubo com lúmen passante = 1 (toro sólido). Serve para dizer se a cavidade
# sobreviveu — não localiza nada, ver limitações de `qualidade_topologica`.
GENUS_ESPERADO = {"tubo_oco": 1}

# --------------------------------------------------------------- colunas

REPRODUTIBILIDADE = (
    "dataset", "case_id", "structure", "pipeline_version", "segmentation_model",
    "reconstruction_method", "sigma", "taubin_iterations", "mesh_smoothing",
    "ws_iters", "ws_pass_band", "spacing_mm",
)

# as 18 primeiras são as que `_bloco_tier` (de benchmark_sigma) consome
COLUNAS = (
    "alvo", "tier", "faixa_calibre", "calibre_mm", "variante", "estrutura_preservada",
    "dice_reconstrucao", "assd_mm", "hd95_mm", "volume_error_pct", "area_error_pct",
    "watertight", "n_componentes", "delta_componentes", "fracao_maior_componente",
    "tris", "vertices", "tempo_s",
    # Tier3: verdade analítica
    "hausdorff_analitico_mm", "rms_analitico_mm",
    "dimensao_error_pct", "dimensao_medida_mm", "dimensao_ref_mm", "dimensao_tipo", "dimensao_bbox_mm",
    "cavidade_preservada", "genus", "n_self_intersections", "n_boundary_edges",
    # continuidade tubular
    "continuidade_delta_comprimento_pct", "fragmentou", "sumiu",
    # referências e reprodutibilidade
    "volume_ref_mm3", "volume_ref_tipo", "area_mm2", "area_ref_mm2", "area_ref_tipo",
) + REPRODUTIBILIDADE + ("erro",)

NA = "nao aplicavel"
NM = "nao medido"


# --------------------------------------------------------------- verdade analítica


def _sdf_cilindro(rxy: np.ndarray, z: np.ndarray, r: float, meia_altura: float) -> np.ndarray:
    """SDF exata de um cilindro fechado alinhado a z (fórmula padrão do capped cylinder)."""
    dr = rxy - r
    dz = np.abs(z) - meia_altura
    fora = np.hypot(np.maximum(dr, 0.0), np.maximum(dz, 0.0))
    return fora + np.minimum(np.maximum(dr, dz), 0.0)


def sdf_analitica(tipo: str, dims: dict[str, float]) -> Callable[[np.ndarray], np.ndarray] | None:
    """Distância COM SINAL (mm) à superfície analítica do fantoma, em RAS mm.

    Só existe para os fantomas de forma fechada. Devolve None para o resto — e aí
    hausdorff/RMS saem "nao aplicavel", nunca um número inventado.

    No `tubo_oco` a combinação por `max` (interseção com o complemento do lúmen)
    é exata na região de interesse (pontos SOBRE a superfície) e pode subestimar
    a distância de pontos afastados perto da junção côncava — o que este
    benchmark mede é justamente a primeira.
    """
    if tipo == "esfera":
        raio = dims["d"] / 2.0
        return lambda p: np.linalg.norm(p, axis=-1) - raio
    if tipo == "tubo_oco":
        re_, ri = dims["de"] / 2.0, dims["di"] / 2.0
        meia = dims["h"] / 2.0

        def _anel(p: np.ndarray) -> np.ndarray:
            rxy = np.linalg.norm(p[..., :2], axis=-1)
            return np.maximum(_sdf_cilindro(rxy, p[..., 2], re_, meia), ri - rxy)

        return _anel
    if tipo in ("tubo", "cilindro"):
        raio, meia = dims["d"] / 2.0, dims["h"] / 2.0
        return lambda p: _sdf_cilindro(np.linalg.norm(p[..., :2], axis=-1), p[..., 2], raio, meia)
    return None


def distancia_a_verdade(mesh, tipo: str, dims: dict[str, float], semente: int = 0) -> dict[str, Any]:
    """Hausdorff e RMS (mm) da malha até a superfície analítica.

    UNILATERAL, por construção: amostra pontos NA MALHA e mede a distância deles
    à superfície analítica. Detecta a malha encolhendo, inchando ou ondulando;
    NÃO detecta um pedaço da verdade que a malha simplesmente não cobre (para
    isso seria preciso o sentido inverso, que exigiria amostrar a superfície
    analítica — não implementado). Ler como "quanto a malha se afasta da
    verdade", não como distância de Hausdorff simétrica.
    """
    import trimesh

    f = sdf_analitica(tipo, dims)
    if f is None:
        return {"hausdorff_analitico_mm": NA, "rms_analitico_mm": NA}
    pts, _ = trimesh.sample.sample_surface(mesh, AMOSTRAS_SDF, seed=semente)
    d = np.abs(f(gltf_m_para_ras_mm(np.asarray(pts))))
    return {
        "hausdorff_analitico_mm": round(float(d.max()), 4),
        "rms_analitico_mm": round(float(np.sqrt(np.mean(d**2))), 4),
    }


def calibre_mediano_mm(mesh, comprimento_mm: float) -> float:
    """Calibre de estrutura tubular: 2 × MEDIANA do raio dos vértices numa faixa central.

    Por que MEDIANA e não bounding box: a bbox é uma estatística de MÁXIMO sobre os
    vértices extremos da escada do marching cubes, então ela mede o quanto o filtro
    raspa a ponta da escada, NÃO o calibre. Medido no tubo de 2 mm (spacing
    0,7×0,7×1,25), a bbox e o volume andam em sentidos OPOSTOS com mais Taubin — a
    bbox diz que afinou de +5,000 % (taubin=0) para -4,904 % (taubin=20) enquanto o
    volume sobe de -27,755 % para -25,343 %. Com a mediana o sinal é coerente: o
    calibre sobe de -21,738 % para -14,465 %, na mesma direção do volume.

    Faixa central (metade do comprimento em torno do meio): as tampas do cilindro
    não têm calibre e contaminariam o raio.
    """
    v = np.asarray(mesh.vertices, dtype=float)
    # RAS_PARA_GLTF leva o eixo z do RAS para o eixo y do glTF: o eixo do tubo é v[:,1].
    eixo = v[:, 1]
    centro = 0.5 * (float(eixo.max()) + float(eixo.min()))
    meia = (comprimento_mm * MM_PARA_M) / 4.0  # metade da metade central
    faixa = np.abs(eixo - centro) < meia
    if faixa.sum() < 8:  # faixa vazia demais para uma mediana significar algo
        faixa = np.ones(len(v), dtype=bool)
    secao = v[faixa][:, [0, 2]]
    raios = np.linalg.norm(secao - secao.mean(axis=0), axis=1)
    return 2.0 * float(np.median(raios)) * M_PARA_MM


def medir_dimensao(mesh, tipo: str, dims: dict[str, float]) -> dict[str, Any]:
    """Erro da DIMENSÃO característica contra o valor nominal do fantoma.

    Esfera: `phantom.medir_esfera` (2 × raio médio dos vértices ao centroide).
    Cilindro/tubo/tubo_oco: 2 × mediana do raio na faixa central (`calibre_mediano_mm`).

    A versão anterior usava bounding box em x/y; ela foi trocada porque é um MÁXIMO
    e mede a escada, não o calibre — e por isso reprovava a porta de estrutura fina
    até para a malha SEM filtro nenhum. A bbox continua gravada em
    `dimensao_bbox_mm` para auditoria, rotulada como o que é.
    """
    v = gltf_m_para_ras_mm(np.asarray(mesh.vertices))
    bbox = v.max(axis=0) - v.min(axis=0)
    bbox_xy = round(float((bbox[0] + bbox[1]) / 2.0), 4)
    if tipo == "esfera":
        return {"dimensao_medida_mm": round(medir_esfera(mesh)["diametro_medido_mm"], 4),
                "dimensao_ref_mm": dims["d"], "dimensao_tipo": "diametro_medio_vertices",
                "dimensao_bbox_mm": bbox_xy}
    ref = dims.get("de", dims.get("d"))
    if ref is None:
        return {"dimensao_medida_mm": NA, "dimensao_ref_mm": NA, "dimensao_tipo": NA,
                "dimensao_bbox_mm": bbox_xy}
    return {"dimensao_medida_mm": round(calibre_mediano_mm(mesh, float(dims.get("h", 30.0))), 4),
            "dimensao_ref_mm": float(ref), "dimensao_tipo": "calibre_mediano_secao",
            "dimensao_bbox_mm": bbox_xy}


# --------------------------------------------------------------- medição


def _pipeline_version() -> str:
    """Não existe versão declarada no repositório: usamos o hash do arquivo que produz a malha."""
    caminho = Path(__file__).resolve().parents[1] / "geometry" / "reconstruction.py"
    h = hashlib.sha256(caminho.read_bytes()).hexdigest()[:12]
    return f"reconstruction.py@sha256:{h} (repositorio sem versao de pipeline declarada)"


def _segmentation_model(raiz: Path, dataset: str) -> str:
    """Lê a versão do TotalSegmentator do relatório do dataset; não inventa se não estiver lá."""
    for p in (raiz / ".clinica-dados" / dataset / "relatorio.json",
              raiz / ".clinica-dados" / f"{dataset}.json"):
        if not p.exists():
            continue
        seg = json.loads(p.read_text(encoding="utf-8")).get("segmentacao") or {}
        versao = seg.get("totalsegmentator_versao")
        if versao:
            return f"TotalSegmentator {versao} (tarefa={seg.get('tarefa', NM)})"
        return f"{NM}: {p.name} nao registra o modelo de segmentacao"
    return f"{NM}: sem relatorio para o dataset {dataset}"


def _identidade(alvo: Alvo, raiz: Path) -> dict[str, str]:
    """dataset / case_id / structure / segmentation_model do alvo."""
    if alvo.tier == TIER3:
        return {"dataset": "fantoma-sintetico", "case_id": alvo.nome,
                "structure": str(alvo.extra.get("tipo", NM)), "segmentation_model": NA}
    estrutura, _, resto = alvo.nome.partition("[")
    dataset = resto.rstrip("]").removesuffix("_masks")
    return {"dataset": dataset, "case_id": dataset, "structure": estrutura,
            "segmentation_model": _segmentation_model(raiz, dataset)}


def medir(alvo: Alvo, variante: str, raiz: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Uma linha (alvo × variante) + o dict de `qualidade_topologica` para comparar com o baseline."""
    cfg = VARIANTES[variante]
    zooms = zooms_de(alvo.affine)
    tipo = str(alvo.extra.get("tipo", ""))
    dims = dict(alvo.extra.get("dims", {}))
    usa_wsinc = cfg["mesh_smoothing"] == "windowed_sinc"

    linha: dict[str, Any] = {c: None for c in COLUNAS}
    linha.update(
        alvo=alvo.nome, tier=alvo.tier, faixa_calibre=alvo.faixa, calibre_mm=alvo.calibre_mm,
        variante=variante, estrutura_preservada=False,
        volume_ref_mm3=round(alvo.volume_ref_mm3, 4), volume_ref_tipo=alvo.volume_ref_tipo,
        area_ref_mm2=None if alvo.area_ref_mm2 is None else round(alvo.area_ref_mm2, 3),
        area_ref_tipo=alvo.area_ref_tipo,
        reconstruction_method=cfg["method"], sigma=cfg["sigma_mm"],
        # o filtro que NÃO roda não tem parâmetro: registrar um número ali seria mentira
        taubin_iterations=NA if usa_wsinc else cfg["taubin_iters"],
        mesh_smoothing=cfg["mesh_smoothing"],
        ws_iters=cfg.get("ws_iters", NA) if usa_wsinc else NA,
        ws_pass_band=cfg.get("ws_pass_band", NA) if usa_wsinc else NA,
        spacing_mm=[round(float(z), 4) for z in zooms],
        pipeline_version=_pipeline_version(),
        **_identidade(alvo, raiz),
    )

    try:
        r = reconstruct_surface(
            alvo.mask, alvo.affine, method=cfg["method"], sigma_mm=cfg["sigma_mm"],
            taubin_iters=cfg["taubin_iters"], mesh_smoothing=cfg["mesh_smoothing"],
            ws_iters=cfg.get("ws_iters", 20), ws_pass_band=cfg.get("ws_pass_band", 0.1),
        )
        if r is None:
            # perda TOTAL: a estrutura não sobreviveu ao filtro. É resultado, não erro.
            linha["erro"] = "ausente: reconstruct_surface devolveu None"
            return linha, None
        malha = r.mesh
        linha.update(tempo_s=round(r.tempo_s, 4), tris=int(len(malha.faces)),
                     vertices=int(len(malha.vertices)),
                     estrutura_preservada=bool(len(malha.faces) > 0 and abs(float(malha.volume)) > 0.0))

        topo = qualidade_topologica(malha)
        linha.update(
            watertight=topo["watertight"], n_componentes=topo["n_componentes"],
            genus=topo["genus"], n_self_intersections=topo["n_self_intersections"],
            n_boundary_edges=topo["n_boundary_edges"], area_mm2=topo["area_mm2"],
        )
        linha["area_error_pct"] = _finito_arred(_erro_pct(topo["area_mm2"], alvo.area_ref_mm2))
        linha["volume_error_pct"] = _finito_arred(
            _erro_pct(abs(float(malha.volume)) * 1e9, alvo.volume_ref_mm3)
        )

        met = comparar_mascara_malha(alvo.mask, malha, alvo.affine)
        linha.update(dice_reconstrucao=_finito_arred(met["dice"], 4),
                     assd_mm=_finito_arred(met["assd_mm"], 4),
                     hd95_mm=_finito_arred(met["hd95_mm"], 4))

        cont = comparar_continuidade(alvo.mask, malha, alvo.affine)
        linha.update(delta_componentes=cont["delta_componentes"],
                     fracao_maior_componente=cont["malha"]["fracao_maior_componente"],
                     continuidade_delta_comprimento_pct=_finito_arred(cont["delta_comprimento_pct"], 2),
                     fragmentou=cont["fragmentou"], sumiu=cont["sumiu"])

        if alvo.tier == TIER3:
            linha.update(distancia_a_verdade(malha, tipo, dims))
            linha.update(medir_dimensao(malha, tipo, dims))
            linha["dimensao_error_pct"] = _finito_arred(
                _erro_pct(linha["dimensao_medida_mm"], linha["dimensao_ref_mm"])
                if isinstance(linha["dimensao_medida_mm"], float) else None
            )
            esperado = GENUS_ESPERADO.get(tipo)
            linha["cavidade_preservada"] = (
                NA if esperado is None
                else (topo["genus"] == esperado if isinstance(topo["genus"], int) else NM)
            )
        else:
            # estrutura real não tem verdade analítica de superfície nem de cavidade
            linha.update(hausdorff_analitico_mm=NA, rms_analitico_mm=NA,
                         dimensao_medida_mm=NA, dimensao_ref_mm=NA, dimensao_tipo=NA,
                         dimensao_error_pct=NA, cavidade_preservada=NA)
    except Exception as exc:  # uma variante que quebra não derruba as outras
        linha["erro"] = f"{type(exc).__name__}: {exc}"
        print(f"  [erro] {alvo.nome} x {variante}: {linha['erro']}", file=sys.stderr)
        return linha, None
    return linha, topo


def rodar(alvos: list[Alvo], raiz: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict]]:
    linhas: list[dict[str, Any]] = []
    topos: dict[tuple[str, str], dict] = {}
    for alvo in alvos:
        if alvo.tier == TIER1 and alvo.area_ref_mm2 is None:
            alvo.area_ref_mm2 = area_proxy_mm2(alvo)
        print(f"\n=== {alvo.nome}  {alvo.tier}  calibre={alvo.calibre_mm:g} mm ({alvo.faixa})  "
              f"voxels={alvo.extra.get('voxels')}  shape={alvo.extra.get('shape')}")
        for variante in VARIANTES:
            linha, topo = medir(alvo, variante, raiz)
            linhas.append(linha)
            if topo is not None:
                topos[(alvo.nome, variante)] = topo
            print(f"  {variante:12s} preservada={str(linha['estrutura_preservada']):5s} "
                  f"dV%={_fmt(linha['volume_error_pct'], 2)} dA%={_fmt(linha['area_error_pct'], 2)} "
                  f"dDim%={_fmt(linha['dimensao_error_pct'], 2)} "
                  f"hd={_fmt(linha['hausdorff_analitico_mm'], 3)} rms={_fmt(linha['rms_analitico_mm'], 3)} "
                  f"wt={_fmt(linha['watertight'])} comp={_fmt(linha['n_componentes'])} "
                  f"genus={_fmt(linha['genus'])} cav={_fmt(linha['cavidade_preservada'])} "
                  f"tris={_fmt(linha['tris'])} t={_fmt(linha['tempo_s'], 2)}s"
                  + (f"  !! {linha['erro']}" if linha["erro"] else ""))
    return linhas, topos


# --------------------------------------------------------------- veredito


def _classificar(delta_pp: float | None) -> str:
    """melhorou/piorou/empate a partir da variação do MÓDULO do erro, em pontos percentuais."""
    if delta_pp is None:
        return NM
    if delta_pp <= -LIMIAR_RELEVANTE_PP:
        return "melhorou"
    if delta_pp >= LIMIAR_RELEVANTE_PP:
        return "piorou"
    return "empate"


def _mediana_abs(linhas: list[dict[str, Any]], metrica: str) -> float | None:
    return _mediana([abs(l[metrica]) for l in linhas
                     if l["erro"] is None and isinstance(l[metrica], (int, float))])


def veredito(linhas: list[dict[str, Any]], topos: dict[tuple[str, str], dict],
             variante: str) -> dict[str, Any]:
    """Veredito de UMA variante contra o baseline congelado. Só olha o Tier3.

    Motivo: no Tier1 a área de referência é um PROXY (a malha sigma=0/taubin=0) e
    dice/ASSD/HD95 são tautológicos com sigma=0. Erro absoluto de área e volume
    só existe contra fantoma analítico. As portas de topologia, cavidade e
    continuidade, essas sim, varrem Tier1 e Tier3.
    """
    if variante == BASELINE:
        return {"variante": variante, "veredito": "baseline congelado", "por_faixa": {},
                "portas": {}, "limiar_relevante_pp": LIMIAR_RELEVANTE_PP}

    por_faixa: dict[str, dict[str, Any]] = {}
    for faixa in ORDEM_FAIXAS:
        base = [l for l in linhas if l["tier"] == TIER3 and l["faixa_calibre"] == faixa
                and l["variante"] == BASELINE]
        alt = [l for l in linhas if l["tier"] == TIER3 and l["faixa_calibre"] == faixa
               and l["variante"] == variante]
        if not base or not alt:
            continue
        celula: dict[str, Any] = {}
        for rotulo, metrica in (("area", "area_error_pct"), ("volume", "volume_error_pct"),
                                ("dimensao", "dimensao_error_pct")):
            b, a = _mediana_abs(base, metrica), _mediana_abs(alt, metrica)
            delta = None if (b is None or a is None) else round(a - b, 4)
            celula[f"abs_{rotulo}_baseline_pct"] = b
            celula[f"abs_{rotulo}_variante_pct"] = a
            celula[f"delta_abs_{rotulo}_pp"] = delta
            celula[rotulo] = _classificar(delta)
        por_faixa[faixa] = celula

    # portas de topologia/cavidade/continuidade: por ALVO, Tier1 e Tier3
    falhas_topologia, cavidades_fechadas, finas_degradadas = [], [], []
    for (nome, var), topo in topos.items():
        if var != variante:
            continue
        base_topo = topos.get((nome, BASELINE))
        if base_topo is None:
            continue
        cmp_ = comparar_topologia(base_topo, topo)
        motivos = [k for k in ("abriu_malha", "fragmentou", "criou_nao_manifold") if cmp_[k] is True]
        if motivos:
            falhas_topologia.append(f"{nome}: {'+'.join(motivos)}")
        if cmp_["fechou_cavidade"] is True:
            cavidades_fechadas.append(nome)

    por_alvo = {(l["alvo"], l["variante"]): l for l in linhas}
    for (nome, var) in list(por_alvo):
        if var != variante:
            continue
        l, b = por_alvo[(nome, variante)], por_alvo.get((nome, BASELINE))
        if b is None or l["faixa_calibre"] != ORDEM_FAIXAS[0]:  # "<3mm"
            continue
        if b["estrutura_preservada"] and not l["estrutura_preservada"]:
            finas_degradadas.append(f"{nome}: estrutura sumiu")
        elif l["fragmentou"] and not b["fragmentou"]:
            finas_degradadas.append(f"{nome}: fragmentou")
        elif l["cavidade_preservada"] is False and b["cavidade_preservada"] is True:
            finas_degradadas.append(f"{nome}: cavidade fechada")

    # degradar estrutura fina não é só sumir: a DIMENSÃO da faixa <3mm encolhendo
    # de forma relevante já é perda de calibre, e é o defeito clássico do filtro.
    fina = por_faixa.get(ORDEM_FAIXAS[0], {})
    for metrica in ("dimensao", "volume", "area"):
        if fina.get(metrica) == "piorou":
            finas_degradadas.append(
                f"faixa {ORDEM_FAIXAS[0]}: |erro de {metrica}| piorou "
                f"{fina[f'delta_abs_{metrica}_pp']:+.2f} pp"
            )

    # faixas MENORES = todas menos a última; regressão ali pesa mais (estrutura fina)
    menores = ORDEM_FAIXAS[:-1]
    regressao_menores = [
        f"{f}: {m} piorou {por_faixa[f][f'delta_abs_{m}_pp']:+.2f} pp"
        for f in menores if f in por_faixa
        for m in ("area", "volume") if por_faixa[f][m] == "piorou"
    ]

    classes_area = [c["area"] for c in por_faixa.values()]
    classes_vol = [c["volume"] for c in por_faixa.values()]
    area_todas = bool(classes_area) and all(c == "melhorou" for c in classes_area)
    vol_todas = bool(classes_vol) and all(c == "melhorou" for c in classes_vol)
    area_alguma = "melhorou" in classes_area
    vol_alguma = "melhorou" in classes_vol
    area_piorou = "piorou" in classes_area
    vol_piorou = "piorou" in classes_vol

    portas = {
        "1_reduziu_area": area_alguma and not area_piorou,
        "2_nao_aumentou_volume": not vol_piorou,
        "3_sem_falha_topologica_nova": not falhas_topologia,
        "4_sem_cavidade_fechada": not cavidades_fechadas,
        "5_estrutura_fina_intacta": not finas_degradadas,
        "6_sem_regressao_em_faixa_menor": not regressao_menores,
        "detalhes": {"falhas_topologia": falhas_topologia, "cavidades_fechadas": cavidades_fechadas,
                     "estrutura_fina": finas_degradadas, "regressao_faixas_menores": regressao_menores},
    }
    bloqueios = [k for k in list(portas)[2:6] if portas[k] is False]

    if bloqueios:
        parecer = f"nao adotar: porta(s) reprovada(s) {', '.join(bloqueios)}"
    elif area_todas and vol_todas:
        parecer = "forte candidato"
    elif vol_alguma and not vol_piorou and area_piorou:
        parecer = "inconclusivo / trade-off (volume melhora, area piora)"
    elif area_alguma and vol_piorou:
        parecer = "nao adotar automaticamente (area melhora as custas de volume)"
    elif area_piorou or vol_piorou:
        parecer = "nao adotar: piorou sem compensacao"
    elif area_alguma or vol_alguma:
        # melhora real, mas não em todas as faixas: NÃO é forte candidato e também
        # não é "sem diferença" — dizer qualquer uma das duas coisas seria falso.
        parecer = (
            f"melhora parcial (area melhorou em {classes_area.count('melhorou')}/"
            f"{len(classes_area)} faixas, volume em {classes_vol.count('melhorou')}/"
            f"{len(classes_vol)}); nao e forte candidato"
        )
    else:
        parecer = f"sem diferenca relevante (limiar {LIMIAR_RELEVANTE_PP:g} pp)"

    return {"variante": variante, "veredito": parecer, "por_faixa": por_faixa, "portas": portas,
            "limiar_relevante_pp": LIMIAR_RELEVANTE_PP,
            "base_do_veredito": "Tier3 (fantoma analitico); Tier1 nao entra por ser proxy/tautologico"}


# --------------------------------------------------------------- markdown


_ANALITICAS = ("volume_error_pct", "area_error_pct", "dimensao_error_pct",
               "hausdorff_analitico_mm", "rms_analitico_mm",
               "continuidade_delta_comprimento_pct")


def _bloco_tier3_analitico(linhas: list[dict[str, Any]]) -> list[str]:
    """Segunda tabela do Tier3: as colunas que só existem contra verdade analítica."""
    out: list[str] = []
    do_tier = [l for l in linhas if l["tier"] == TIER3]
    for faixa in ORDEM_FAIXAS:
        da_faixa = [l for l in do_tier if l["faixa_calibre"] == faixa]
        if not da_faixa:
            continue
        out += [
            f"### calibre {faixa} — verdade analítica", "",
            "`dim_err_%` é a mediana do erro COM SINAL (diz a direção: negativo = encolheu);"
            " `\\|dim_err\\|_%` é a mediana do MÓDULO — esta última é a que o veredito compara."
            " Numa faixa que mistura alvos com sinais opostos as duas se movem em direções"
            " diferentes, e isso não é contradição.", "",
            "| variante | volume_err_% | area_err_% | dim_err_% | \\|dim_err\\|_% | hausdorff_mm |"
            " rms_mm | watertight | n_comp | genus | self_int | cavidade preservada | frag |"
            " d_compr_% |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for variante in VARIANTES:
            do_par = [l for l in da_faixa if l["variante"] == variante and l["erro"] is None]
            if not do_par:
                continue
            med = {m: _mediana([l[m] for l in do_par if isinstance(l[m], (int, float))])
                   for m in _ANALITICAS}
            cav = [l["cavidade_preservada"] for l in do_par if l["cavidade_preservada"] is not NA]
            n_si = [l["n_self_intersections"] for l in do_par
                    if isinstance(l["n_self_intersections"], int)]
            generos = {str(l["genus"]) for l in do_par}
            out.append(
                f"| {variante} | {_fmt(med['volume_error_pct'], 2)} | {_fmt(med['area_error_pct'], 2)} | "
                f"{_fmt(med['dimensao_error_pct'], 2)} | "
                f"{_fmt(_mediana_abs(do_par, 'dimensao_error_pct'), 2)} | "
                f"{_fmt(med['hausdorff_analitico_mm'], 3)} | "
                f"{_fmt(med['rms_analitico_mm'], 3)} | "
                f"{sum(1 for l in do_par if l['watertight'])}/{len(do_par)} | "
                f"{_fmt(_mediana([l['n_componentes'] for l in do_par]), 0)} | "
                f"{', '.join(sorted(generos))} | "
                f"{(f'{max(n_si)} (max)' if n_si else NM)} | "
                f"{(f'{sum(1 for c in cav if c is True)}/{len(cav)}' if cav else NA)} | "
                f"{sum(1 for l in do_par if l['fragmentou'])}/{len(do_par)} | "
                f"{_fmt(med['continuidade_delta_comprimento_pct'], 2)} |"
            )
        out.append("")
    return out


def _bloco_tier1_com_lacunas(linhas: list[dict[str, Any]]) -> list[str]:
    """Tier1 faixa a faixa; faixa sem estrutura real vira a lacuna declarada, não uma linha vazia."""
    out: list[str] = []
    for faixa in ORDEM_FAIXAS:
        da_faixa = [l for l in linhas if l["tier"] == TIER1 and l["faixa_calibre"] == faixa]
        if da_faixa:
            out += _bloco_tier(da_faixa, TIER1, VARIANTES, EXPERIMENTAL)
        else:
            out += [f"### calibre {faixa}", "",
                    "nao medido: sem estrutura real nesta faixa", ""]
    return out


def montar_summary(linhas: list[dict[str, Any]], vereditos: list[dict[str, Any]]) -> str:
    n_alvos = len({l["alvo"] for l in linhas})
    param = {
        v: (f"marching_cubes, sigma=0.0, mesh_smoothing={c['mesh_smoothing']}, "
            + (f"ws_iters={c['ws_iters']}, ws_pass_band={c['ws_pass_band']}"
               if c["mesh_smoothing"] == "windowed_sinc" else f"taubin_iters={c['taubin_iters']}"))
        for v, c in VARIANTES.items()
    }
    out = [
        "# Benchmark de suavização de MALHA por faixa de calibre", "",
        f"{n_alvos} alvos × {len(VARIANTES)} variantes = {len(linhas)} linhas. "
        f"Baseline CONGELADO: `{BASELINE}` (o default vigente da MASTER).", "",
        "## Variantes (parâmetros exatos)", "",
        "| variante | parâmetros |", "|---|---|",
    ]
    out += [f"| `{v}` | {p} |" for v, p in param.items()]
    out += [
        "", f"Extrator e borramento ficam FIXOS em todas: `marching_cubes` + `sigma_mm=0.0`. "
        "A única coisa que varia é o filtro no domínio da malha. Nada aqui altera o default "
        "do pipeline — as variantes são kwargs explícitos de `reconstruct_surface`.", "",
        "Faixas são de CALIBRE (espessura característica em mm), não de volume. No Tier3 o "
        "calibre é a dimensão nominal do fantoma; no Tier1 é `2 × mediana(EDT no esqueleto)` — "
        "aproximado, serve para agrupar, não como medida.", "",
        "Agregação = MEDIANA por (tier, faixa, variante). Linhas com `erro` (inclusive estrutura "
        "ausente) ficam fora das medianas mas contam em `n_ok` e `preservada`.", "",
        "## Tiers", "",
        "- **Tier1** — fidelidade da RECONSTRUÇÃO à máscara. Área de referência é PROXY (malha "
        "sigma=0/taubin=0); não existe área verdadeira para uma máscara de voxel.",
        "- **Tier2** — acurácia da segmentação contra ground truth independente: **AUSENTE neste "
        "repositório**. Nenhuma linha abaixo é Tier2.",
        "- **Tier3** — fantoma analítico: volume, área e dimensão têm resposta fechada, então o "
        "erro é ABSOLUTO. É o único tier onde o veredito é decidido.", "",
        "`hausdorff_mm` e `rms_mm` são distâncias da MALHA até a superfície analítica, "
        "**unilaterais** (amostra na malha, mede até a verdade). Detectam encolher/inchar/ondular; "
        "não detectam pedaço da verdade que a malha não cobre.", "",
        "## Critério de aprovação (calculado, não julgado no olho)", "",
        f"**Limiar de relevância declarado: {LIMIAR_RELEVANTE_PP:g} ponto percentual** de variação no "
        "MÓDULO do erro mediano da faixa. Abaixo disso, `empate` — o benchmark se recusa a "
        "chamar duas variantes de diferentes. É um corte escolhido e declarado, não intervalo "
        "de confiança: as medianas vêm de n=2 a 4 alvos por faixa, sem estatística por trás.", "",
        "Portas (todas contra o baseline congelado): (1) reduziu |erro de área| de forma "
        "relevante; (2) não aumentou |erro de volume|; (3) não criou falha topológica nova "
        "(abriu malha, fragmentou, criou aresta não-manifold); (4) não fechou cavidade "
        "(queda de genus); (5) não degradou estrutura fina — a estrutura sumir, fragmentar ou "
        "perder a cavidade, **e também** |erro de dimensão, volume ou área| piorando de forma "
        "relevante na faixa `<3mm`; (6) não regrediu em faixa menor.", "",
        "Desfechos: `forte candidato` = volume E área melhoram em TODAS as faixas e nenhuma "
        "porta reprova. `inconclusivo / trade-off` = volume melhora e área piora. "
        "`nao adotar automaticamente` = área melhora às custas de volume. "
        "`nao adotar: porta(s) reprovada(s)` = qualquer porta 3–6 reprovada. "
        "`melhora parcial` = melhora relevante em algumas faixas e não em todas — "
        "não é forte candidato, e também não é \"sem diferença\".", "",
        "### Veredito por variante", "",
        "| variante | veredito | portas reprovadas |", "|---|---|---|",
    ]
    for v in vereditos:
        reprovadas = [k for k, val in v["portas"].items() if val is False] or ["-"]
        out.append(f"| `{v['variante']}` | {v['veredito']} | {', '.join(reprovadas)} |")
    out += ["", "Detalhe por faixa (Δ do módulo do erro mediano, em pontos percentuais; "
            "negativo = melhorou):", "",
            "| variante | faixa | Δ\\|área\\| pp | classe | Δ\\|volume\\| pp | classe | "
            "Δ\\|dimensão\\| pp | classe |", "|---|---|---|---|---|---|---|---|"]
    for v in vereditos:
        for faixa, c in v["por_faixa"].items():
            out.append(
                f"| `{v['variante']}` | {faixa} | {_fmt(c['delta_abs_area_pp'], 2)} | {c['area']} | "
                f"{_fmt(c['delta_abs_volume_pp'], 2)} | {c['volume']} | "
                f"{_fmt(c['delta_abs_dimensao_pp'], 2)} | {c['dimensao']} |")
    out += ["", "## Tier3 — fantomas analíticos", ""]
    out += _bloco_tier(linhas, TIER3, VARIANTES, EXPERIMENTAL)
    out += _bloco_tier3_analitico(linhas)
    out += [
        "## Tier1 — estruturas reais (fidelidade à máscara)", "",
        "> **NÃO use `dice`, `assd` e `hd95` desta seção como critério.** Todas as variantes "
        "rodam com `sigma_mm=0.0`; a malha rasterizada de volta reproduz a máscara por "
        "construção e essas três colunas saem tautologicamente perfeitas. Elas estão aqui "
        "como checagem de sanidade da conversão de coordenadas, nada mais.", "",
        "> `area_err_%` do Tier1 é contra um **PROXY** (área da malha sigma=0/taubin=0, a que "
        "mais adere à máscara), não contra área verdadeira. Ler como \"quanto esta variante "
        "encolhe a superfície em relação à malha mais aderente\".", "",
    ]
    out += _bloco_tier1_com_lacunas(linhas)
    out += ["## Tier2 — ausente", "",
            "Não há ground truth de segmentação independente neste repositório. Nenhum número "
            "acima pode ser lido como acurácia de segmentação.", "",
            "## Limitações declaradas", "",
            "- Hausdorff/RMS analíticos são UNILATERAIS (malha → verdade).",
            "- `dimensao_error_%` mistura duas grandezas: raio médio dos vértices (esfera) e "
            "bounding box em x/y (cilindro/tubo). A coluna `dimensao_tipo` do CSV diz qual.",
            "- `n_self_intersections` conta PARES DE FACES e não é comparável entre malhas de "
            "resolução diferente; acima de 300 k faces sai `nao medido`.",
            "- `genus`/cavidade só existem em malha fechada e manifold; em malha aberta a "
            "métrica está cega justamente onde o defeito é mais provável.",
            "- Tier1 não cobre `<3mm` nem `>30mm`: não há estrutura real nessas faixas neste "
            "repositório (a mais fina medida tem 5,60 mm; a mais grossa, 23,18 mm).",
            "- Nada aqui é validação clínica: é sanidade geométrica.", ""]
    return "\n".join(out)


# --------------------------------------------------------------- saída


def _linhas_json(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cada linha do JSON: campos de reprodutibilidade no topo, métricas em `metrics`."""
    ignorar = set(REPRODUTIBILIDADE)
    chaves = ("alvo", "tier", "faixa_calibre", "calibre_mm", "variante", "erro")
    return [
        {**{k: l[k] for k in REPRODUTIBILIDADE}, **{k: l[k] for k in chaves},
         "metrics": {k: v for k, v in l.items() if k not in ignorar and k not in chaves}}
        for l in linhas
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark da suavização de malha por faixa de calibre")
    ap.add_argument("--out", required=True, type=Path, help="diretório de saída")
    ap.add_argument("--so-fantomas", action="store_true", help="pula as estruturas reais (Tier3 apenas)")
    args = ap.parse_args(argv)

    raiz = Path(__file__).resolve().parents[2]
    alvos = alvos_fantoma(FANTOMAS)
    if not args.so_fantomas:
        alvos += alvos_reais(raiz)

    linhas, topos = rodar(alvos, raiz)
    if not linhas:
        print("erro: nenhum alvo utilizável", file=sys.stderr)
        return 2

    vereditos = [veredito(linhas, topos, v) for v in VARIANTES]
    summary = montar_summary(linhas, vereditos)
    gravar(
        linhas, args.out, prefixo="smoothing", colunas=COLUNAS, summary=summary,
        linhas_json=_linhas_json(linhas),
        cabecalho={
            "variantes": VARIANTES,
            "baseline": BASELINE,
            "baseline_congelado": True,
            "limiar_relevante_pp": LIMIAR_RELEVANTE_PP,
            "faixas_calibre_mm": [{"faixa": n} for n in ORDEM_FAIXAS],
            "tier2": "ausente: sem ground truth de segmentação independente no repositório",
            "tier1_faixas_sem_cobertura": {
                f: "nao medido: sem estrutura real nesta faixa"
                for f in ORDEM_FAIXAS
                if not any(l["tier"] == TIER1 and l["faixa_calibre"] == f for l in linhas)
            },
            "vereditos": vereditos,
        },
    )
    print()
    print(summary)
    print(f"gravado em: {args.out.resolve()}")
    return 0


def _autoteste() -> None:
    """Checks mínimos: SDF analítica, veredito e uma linha medida de ponta a ponta."""
    # SDF exata: pontos sobre a superfície analítica dão distância ~0
    f = sdf_analitica("esfera", {"d": 20.0})
    p = np.array([[10.0, 0.0, 0.0], [0.0, 0.0, 10.0], [0.0, 0.0, 0.0]])
    assert np.allclose(f(p), [0.0, 0.0, -10.0]), f(p)
    g = sdf_analitica("cilindro", {"d": 10.0, "h": 20.0})
    assert np.allclose(g(np.array([[5.0, 0.0, 0.0], [0.0, 0.0, 10.0], [0.0, 0.0, 15.0]])),
                       [0.0, 0.0, 5.0]), g(np.array([[5.0, 0.0, 0.0]]))
    h = sdf_analitica("tubo_oco", {"de": 10.0, "di": 6.0, "h": 20.0})
    # parede entre r=3 e r=5: o meio (r=4) está a 1 mm das duas superfícies
    assert np.allclose(h(np.array([[4.0, 0.0, 0.0], [3.0, 0.0, 0.0], [5.0, 0.0, 0.0]])),
                       [-1.0, 0.0, 0.0]), h(np.array([[4.0, 0.0, 0.0]]))
    assert sdf_analitica("bifurcacao", {}) is None

    assert _classificar(-2.0) == "melhorou" and _classificar(2.0) == "piorou"
    assert _classificar(0.5) == "empate" and _classificar(None) == NM

    raiz = Path(__file__).resolve().parents[2]
    alvos = [a for a in alvos_fantoma(FANTOMAS) if a.nome.startswith("tubo_oco")]
    assert alvos, "fantoma de cavidade sumiu do conjunto"
    alvo = alvos[0]
    assert alvo.faixa == "<3mm", (alvo.faixa, alvo.calibre_mm)

    linhas, topos = [], {}
    for variante in (BASELINE, "V3_taubin20", "V4_wsinc"):
        linha, topo = medir(alvo, variante, raiz)
        assert linha["erro"] is None and linha["estrutura_preservada"], linha
        assert linha["tier"] == TIER3 and linha["volume_ref_tipo"] == "analitico"
        assert isinstance(linha["hausdorff_analitico_mm"], float), linha
        assert linha["dimensao_tipo"] == "calibre_mediano_secao"
        assert set(REPRODUTIBILIDADE) <= set(linha), "faltou campo de reprodutibilidade"
        linhas.append(linha)
        if topo is not None:
            topos[(alvo.nome, variante)] = topo

    # COERÊNCIA DE SINAL — o assert que a bounding box não passava.
    # Calibre e volume de um tubo são a mesma grandeza vista de dois jeitos
    # (V ~ d²·h): se uma variante engorda o tubo, as duas têm que subir juntas.
    # A bbox falhava aqui — dizia que o tubo afinou 4,9 % enquanto o volume
    # subia 1,7 pp. Este assert falha se alguém voltar a usar um estimador de
    # MÁXIMO (bbox, extensão, raio máximo) no lugar de um estimador robusto.
    base, longo = linhas[0], linhas[1]  # V0_taubin4 e V3_taubin20
    d_cal = longo["dimensao_error_pct"] - base["dimensao_error_pct"]
    d_vol = longo["volume_error_pct"] - base["volume_error_pct"]
    assert d_cal * d_vol > 0, (
        f"calibre e volume discordam de sinal (dcal={d_cal:+.3f} pp, dvol={d_vol:+.3f} pp): "
        "o estimador de dimensão está medindo a escada, não a estrutura"
    )

    # o baseline nunca é julgado contra si mesmo
    assert veredito(linhas, topos, BASELINE)["veredito"] == "baseline congelado"
    v = veredito(linhas, topos, "V3_taubin20")
    assert v["veredito"], v
    assert set(v["portas"]) >= {"1_reduziu_area", "6_sem_regressao_em_faixa_menor"}
    # o JSON precisa carregar reprodutibilidade fora de `metrics`
    j = _linhas_json(linhas)[0]
    assert j["mesh_smoothing"] == "taubin" and "volume_error_pct" in j["metrics"]

    print("autoteste OK:", json.dumps(
        {k: linhas[0][k] for k in ("alvo", "faixa_calibre", "volume_error_pct", "area_error_pct",
                                   "dimensao_error_pct", "hausdorff_analitico_mm",
                                   "cavidade_preservada", "genus")}, ensure_ascii=False))


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(main())
