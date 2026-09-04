"""
Ablacao A/B de cada etapa do pipeline (guardrail 8: nada sai sem experimento).

Uma etapa por vez, o resto identico. As quatro perguntas:

  1. gaussiana na mascara : sigma automatico x sigma 0 (marching cubes no campo binario)
  2. Taubin               : taubin_iters=4 x taubin_iters=0
  3. fill_holes           : processar_mascara com fechar_buracos=True x False (a
                            comparacao e feita na MASCARA, antes de malhar)
  4. encostar (dilatacao) : pulmonary_vein sozinha x dilatada para dentro de `heart`
                            — mede o volume INVENTADO pela dilatacao (guardrail 7)

Cada etapa roda em ESCALAS diferentes (grande: heart/lobo; media: trachea/esophagus;
fina: tubo de 2 e 3 mm). O efeito e de sinal oposto por escala — a media global
mentiria, entao nao existe media global aqui: a tabela e sempre por alvo.

`tipo_referencia` vai em toda linha: "benchmark_interno" nos 4 casos de
.clinica-dados (que NAO sao ground truth clinico) e "phantom_sintetico" nos
fantomas (verdade analitica). Nenhuma metrica mistura os dois.

Rodar: .venv-pipeline/Scripts/python.exe scripts/validation/ablation.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import trimesh

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:  # roda como script ou como -m, tanto faz
    sys.path.insert(0, str(RAIZ))

from scripts.clinica.malha import decimar, encostar  # noqa: E402
from scripts.geometry.mask_processing import REGRAS, RegraMascara, classe_de, processar_mascara  # noqa: E402
from scripts.geometry.reconstruction import reconstruct_surface  # noqa: E402
from scripts.validation.benchmark import volume_mascara_ml, zooms_de  # noqa: E402
from scripts.validation.mesh_metrics import comparar_malhas  # noqa: E402
from scripts.validation.phantom import esfera_com_cavidade, tubo_fino  # noqa: E402
from scripts.validation.topology_metrics import qualidade_topologica  # noqa: E402

DADOS = RAIZ / ".clinica-dados"
SAIDA = DADOS / "ablation"

INTERNO = "benchmark_interno"
FANTOMA = "phantom_sintetico"

# Alvos reais por faixa de escala (grande / media). Nome -> (dir_masks, arquivo).
ALVOS_REAIS = (
    ("heart", DADOS / "torax-alta_masks" / "heart.nii.gz"),
    ("lung_upper_lobe_left", DADOS / "torax-alta_masks" / "lung_upper_lobe_left.nii.gz"),
    ("trachea", DADOS / "torax-alta_masks" / "trachea.nii.gz"),
    ("esophagus", DADOS / "torax-alta_masks" / "esophagus.nii.gz"),
)
CTA = DADOS / "cta-cardio" / "masks"


def _carregar(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    img = nib.load(str(caminho))
    return np.asarray(img.dataobj) > 0.5, img.affine


def _alvos() -> list[tuple[str, str, np.ndarray, np.ndarray]]:
    """(nome, tipo_referencia, mask, affine) — reais + fantomas finos de 2 e 3 mm."""
    alvos = [(nome, INTERNO, *_carregar(p)) for nome, p in ALVOS_REAIS]
    for d in (2.0, 3.0):
        mask, affine = tubo_fino(d, 30.0, spacing=(0.5, 0.5, 0.5))
        alvos.append((f"tubo_{d:g}mm", FANTOMA, mask, affine))
    return alvos


def _medir(mask: np.ndarray, affine: np.ndarray, malha: trimesh.Trimesh, tempo_s: float) -> dict[str, Any]:
    """As metricas de UMA variante. volume_error_pct e malha x mascara, nada agregado."""
    v_masc = volume_mascara_ml(mask, affine)
    v_malha = abs(float(malha.volume)) * 1e6  # m3 -> mL
    return {
        "volume_malha_ml": round(v_malha, 4),
        "volume_mascara_ml": round(v_masc, 4),
        "volume_error_pct": round((v_malha - v_masc) / v_masc * 100.0, 3) if v_masc else None,
        "area_mm2": round(float(malha.area) * 1e6, 2),  # m2 -> mm2
        "tris": int(len(malha.faces)),
        "vertices": int(len(malha.vertices)),
        "watertight": bool(malha.is_watertight),
        "n_componentes": int(malha.body_count),
        "tempo_s": round(tempo_s, 3),
    }


def _variante(mask: np.ndarray, affine: np.ndarray, **kw: Any) -> dict[str, Any]:
    """Reconstroi e mede. Estrutura que nao sobrevive a receita vira erro explicito."""
    t0 = time.perf_counter()
    try:
        r = reconstruct_surface(mask, affine, **kw)
    except Exception as exc:  # uma variante que quebra nao derruba a matriz
        return {"erro": f"{type(exc).__name__}: {exc}", "tempo_s": round(time.perf_counter() - t0, 3)}
    dt = time.perf_counter() - t0
    if r is None:
        return {"erro": "reconstruct_surface devolveu None (dissolvida ou < 50 voxels)", "tempo_s": round(dt, 3)}
    return _medir(mask, affine, r.mesh, dt)


# ---------------------------------------------------------------- ablacoes


def ablacao_gaussiana() -> dict[str, Any]:
    """sigma = max(0,6 mm; 0,5 x maior voxel) x sigma = 0. Taubin fixo em 4 nos dois."""
    linhas = []
    for nome, tipo, mask, affine in _alvos():
        for rotulo, sigma in (("com_gaussiana", None), ("sem_gaussiana", 0.0)):
            linhas.append({
                "alvo": nome, "tipo_referencia": tipo, "variante": rotulo,
                "sigma_mm": round(max(0.6, 0.5 * float(zooms_de(affine).max())), 3) if sigma is None else 0.0,
                **_variante(mask, affine, sigma_mm=sigma, taubin_iters=4),
            })
    return {
        "etapa": "gaussiana_na_mascara",
        "pergunta": "borrar a ocupacao antes do marching cubes muda o que?",
        "controle": "taubin_iters=4, level=0.5, offset_mm=0 nas duas variantes",
        "tipos_referencia": [INTERNO, FANTOMA],
        "linhas": linhas,
    }


def ablacao_taubin() -> dict[str, Any]:
    """taubin_iters=4 x 0, com a gaussiana automatica ligada nos dois."""
    linhas = []
    for nome, tipo, mask, affine in _alvos():
        for rotulo, iters in (("com_taubin_4", 4), ("sem_taubin", 0)):
            linhas.append({
                "alvo": nome, "tipo_referencia": tipo, "variante": rotulo, "taubin_iters": iters,
                **_variante(mask, affine, taubin_iters=iters),
            })
    return {
        "etapa": "taubin",
        "pergunta": "as 4 iteracoes de Taubin custam volume/area em que escala?",
        "controle": "sigma automatico, level=0.5, offset_mm=0 nas duas variantes",
        "tipos_referencia": [INTERNO, FANTOMA],
        "linhas": linhas,
    }


def ablacao_fill_holes() -> dict[str, Any]:
    """fechar_buracos True x False na MASCARA (mesma regra no resto), depois malha.

    Os fantomas entram porque nenhuma mascara de torax-alta tem cavidade 3D
    fechada: sem a casca esferica o experimento so mostraria zero.
    """
    casos: list[tuple[str, str, np.ndarray, np.ndarray]] = [
        (nome, INTERNO, *_carregar(p)) for nome, p in ALVOS_REAIS if nome in ("heart", "trachea")
    ]
    casos.append(("casca_esferica_20_10mm", FANTOMA, *esfera_com_cavidade(20.0, 10.0, spacing=(0.5, 0.5, 0.5))))

    linhas = []
    for nome, tipo, mask, affine in casos:
        zooms = zooms_de(affine)
        base = REGRAS[classe_de(nome)]
        for rotulo, fechar in (("com_fill_holes", True), ("sem_fill_holes", False)):
            regra = RegraMascara(base.min_componente_mm3, fechar, base.manter_multiplos)
            limpa, rel = processar_mascara(mask, zooms, nome, regra=regra)
            linhas.append({
                "alvo": nome, "tipo_referencia": tipo, "variante": rotulo,
                "classe": rel["classe"],
                "buracos_fechados_mm3": rel["buracos_fechados_mm3"],
                "mascara_delta_volume_pct": rel["delta_volume_pct"],
                "componentes_mascara": rel["componentes_depois"],
                "operacoes_mascara": rel["operacoes"],
                **_variante(limpa, affine, taubin_iters=4),
            })
    return {
        "etapa": "fill_holes",
        "pergunta": "fechar cavidade interna some com anatomia real?",
        "controle": "mesma regra de ilhas/componentes; so fechar_buracos muda. Malha: sigma auto, taubin 4",
        "tipos_referencia": [INTERNO, FANTOMA],
        "linhas": linhas,
    }


def ablacao_encostar() -> dict[str, Any]:
    """Dilatacao de 1 voxel da veia para dentro do coracao: quanto volume e INVENTADO."""
    veia, affine = _carregar(CTA / "pulmonary_vein.nii.gz")
    coracao, affine_h = _carregar(CTA / "heart.nii.gz")
    if veia.shape != coracao.shape or not np.allclose(affine, affine_h):
        raise RuntimeError("pulmonary_vein e heart nao estao na mesma grade")

    encostada = encostar(veia, coracao)
    v_antes = volume_mascara_ml(veia, affine)
    v_depois = volume_mascara_ml(encostada, affine)

    linhas = []
    for rotulo, m in (("sem_encostar", veia), ("com_encostar", encostada)):
        linhas.append({
            "alvo": "pulmonary_vein+heart", "caso": "cta-cardio", "tipo_referencia": INTERNO, "variante": rotulo,
            "volume_inventado_ml": round(v_depois - v_antes, 4) if rotulo == "com_encostar" else 0.0,
            "volume_inventado_pct": round((v_depois - v_antes) / v_antes * 100.0, 3) if rotulo == "com_encostar" else 0.0,
            **_variante(m, affine, taubin_iters=4),
        })
    return {
        "etapa": "encostar",
        "pergunta": "quanto volume a dilatacao de contato inventa na veia?",
        "controle": "mesma veia, mesmo alvo; so a dilatacao 1 voxel dentro de heart muda",
        "tipos_referencia": [INTERNO],
        "aviso": "o volume ganho NAO existe no exame: e cola geometrica para o vaso tocar o coracao",
        "linhas": linhas,
    }


def ablacao_decimacao() -> dict[str, Any]:
    """MASTER (marching cubes, sigma auto, sem afastamento) x niveis de decimacao.

    Alvos escolhidos por CALIBRE (espessura caracteristica), nao por volume:
    tubo de 2 e 5 mm (fantoma), esophagus e trachea (~10-30 mm), aorta e heart (>30 mm).
    A pergunta e se a decimacao machuca mais o fino — e o que o piso de 3000 tris
    do pipeline faz com uma estrutura que ja nasce com poucos triangulos.
    """
    casos: list[tuple[str, str, str, np.ndarray, np.ndarray]] = []
    for d in (2.0, 5.0):
        mask, affine = tubo_fino(d, 30.0, spacing=(0.5, 0.5, 0.5))
        casos.append((f"tubo_{d:g}mm", FANTOMA, f"{d:g}mm", mask, affine))
    for nome, faixa in (("esophagus", "10-30mm"), ("trachea", "10-30mm"),
                        ("aorta", ">30mm"), ("heart", ">30mm")):
        casos.append((nome, INTERNO, faixa, *_carregar(DADOS / "torax-alta_masks" / f"{nome}.nii.gz")))

    linhas = []
    for nome, tipo, faixa, mask, affine in casos:
        r = reconstruct_surface(mask, affine, method="marching_cubes", taubin_iters=4, offset_mm=0.0)
        if r is None:
            linhas.append({"alvo": nome, "tipo_referencia": tipo, "faixa_calibre_mm": faixa,
                           "variante": "master", "erro": "reconstruct_surface devolveu None"})
            continue
        master = r.mesh
        top_master = qualidade_topologica(master)
        tris_master = int(len(master.faces))
        area_master = float(master.area)

        alvos_tris = [(f"{int(p * 100)}%", max(4, int(tris_master * p))) for p in (0.7, 0.5, 0.3, 0.1)]
        alvos_tris.append(("piso_3000", 3000))
        for rotulo, orcamento in alvos_tris:
            t0 = time.perf_counter()
            try:
                derivado = decimar(master, orcamento)
            except Exception as exc:
                linhas.append({"alvo": nome, "tipo_referencia": tipo, "faixa_calibre_mm": faixa,
                               "variante": rotulo, "erro": f"{type(exc).__name__}: {exc}",
                               "tempo_s": round(time.perf_counter() - t0, 3)})
                continue
            dt = time.perf_counter() - t0
            cmp_ = comparar_malhas(master, derivado)
            top = qualidade_topologica(derivado)
            linhas.append({
                "alvo": nome, "tipo_referencia": tipo, "faixa_calibre_mm": faixa,
                "variante": rotulo, "orcamento_tris": orcamento,
                "tris_antes": tris_master,
                "tris_depois": int(len(derivado.faces)),
                "reducao_pct": cmp_["reducao_tris_pct"],
                "hausdorff_mm": cmp_["hausdorff_mm"],
                "rms_mm": cmp_["rms_mm"],
                "volume_error_pct": cmp_["volume_error_pct"],
                "area_error_pct": round((float(derivado.area) - area_master) / area_master * 100.0, 3)
                                  if area_master else None,
                "watertight_antes": top_master["watertight"],
                "watertight_depois": top["watertight"],
                "n_componentes_antes": top_master["n_componentes"],
                "n_componentes_depois": top["n_componentes"],
                "tempo_s": round(dt, 3),
            })
    return {
        "etapa": "decimacao",
        "pergunta": "a decimacao machuca mais o calibre fino? e o piso de 3000 tris destroi o fino?",
        "controle": "mesma MASTER por alvo (marching_cubes, sigma auto, taubin 4, offset 0); "
                    "so o orcamento de triangulos muda. Tier1: erro medido contra a MASTER, nao contra a mascara",
        "tipos_referencia": [INTERNO, FANTOMA],
        "aviso": "piso_3000 aplicado a alvo que ja tem <=3000 tris e no-op (reducao 0) — "
                 "o piso nao protege o fino, so nao o corta mais",
        "campos": _CAMPOS_DECIMACAO,
        "linhas": linhas,
    }


# ---------------------------------------------------------------- saida


_CAMPOS = ("volume_malha_ml", "volume_mascara_ml", "volume_error_pct", "area_mm2",
           "tris", "vertices", "watertight", "n_componentes", "tempo_s")

_CAMPOS_DECIMACAO = ("tris_antes", "tris_depois", "reducao_pct", "hausdorff_mm", "rms_mm",
                     "volume_error_pct", "area_error_pct", "watertight_antes", "watertight_depois",
                     "n_componentes_antes", "n_componentes_depois", "tempo_s")


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "sim" if v else "nao"
    return f"{v:,.2f}".replace(",", " ") if isinstance(v, float) else str(v)


def imprimir(bloco: dict[str, Any]) -> None:
    print(f"\n=== ablacao: {bloco['etapa']} — {bloco['pergunta']}")
    print(f"    controle: {bloco['controle']}")
    if "aviso" in bloco:
        print(f"    AVISO: {bloco['aviso']}")
    campos = bloco.get("campos", _CAMPOS)
    cab = f"{'alvo':<26}{'variante':<16}{'ref':<20}" + "".join(f"{c[:12]:>13}" for c in campos)
    print(cab)
    anterior: dict[str, Any] | None = None
    alvo_ant = None
    for l in bloco["linhas"]:
        if l["alvo"] != alvo_ant:
            anterior, alvo_ant = None, l["alvo"]
        if "erro" in l:
            print(f"{l['alvo']:<26}{l['variante']:<16}{l['tipo_referencia']:<20}ERRO: {l['erro']}")
            anterior = None
            continue
        print(f"{l['alvo']:<26}{l['variante']:<16}{l['tipo_referencia']:<20}"
              + "".join(f"{_fmt(l[c]):>13}" for c in campos))
        if anterior is not None and "volume_malha_ml" in l:
            d = {c: l[c] - anterior[c] for c in ("volume_malha_ml", "area_mm2", "tris") if not isinstance(l[c], bool)}
            pct = d["volume_malha_ml"] / anterior["volume_malha_ml"] * 100.0 if anterior["volume_malha_ml"] else float("nan")
            print(f"{'':<26}{'  ^ delta':<36}"
                  f"volume {d['volume_malha_ml']:+.3f} mL ({pct:+.2f} %)   "
                  f"area {d['area_mm2']:+.1f} mm2   tris {d['tris']:+d}")
        anterior = l
        if "volume_inventado_ml" in l and l["volume_inventado_ml"]:
            print(f"{'':<26}  volume INVENTADO pela dilatacao: {l['volume_inventado_ml']:+.3f} mL "
                  f"({l['volume_inventado_pct']:+.2f} % da mascara original)")
        if "buracos_fechados_mm3" in l:
            print(f"{'':<26}  mascara: buracos_fechados={l['buracos_fechados_mm3']:.1f} mm3  "
                  f"delta={l['mascara_delta_volume_pct']:+.3f} %  componentes={l['componentes_mascara']}")


def main() -> int:
    blocos = [ablacao_gaussiana(), ablacao_taubin(), ablacao_fill_holes(), ablacao_encostar(),
              ablacao_decimacao()]
    for b in blocos:
        imprimir(b)

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "ablation.json"
    destino.write_text(
        json.dumps(
            {
                "nota": "A/B por etapa. Sem media global: o efeito troca de sinal com a escala.",
                "guardrail": "os casos de .clinica-dados nao sao ground truth clinico "
                             "(tipo_referencia=benchmark_interno); so o fantoma tem verdade analitica.",
                "ablacoes": blocos,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\ngravado: {destino}")

    # Autoteste: as duas variantes de cada par tem que ser DIFERENTES em pelo menos
    # um alvo, senao a ablacao nao ablacionou nada e a tabela e decorativa.
    for b in blocos:
        chave = "tris_depois" if b["etapa"] == "decimacao" else "volume_malha_ml"
        vols = [l.get(chave) for l in b["linhas"] if "erro" not in l]
        assert len(set(vols)) > 1, f"ablacao {b['etapa']} nao produziu diferenca alguma"
    print(f"autoteste: as {len(blocos)} ablacoes produziram diferenca mensuravel OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
