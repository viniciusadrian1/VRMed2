"""
Cadeia A -> B: o que o erro de segmentacao e o de reconstrucao fazem JUNTOS.

    ground truth  --(A)-->  mascara prevista  --(B)-->  malha MASTER
         |                                                   ^
         +---------------------(A+B)-------------------------+

TRES MEDIDAS, TRES SIGNIFICADOS DIFERENTES — e a razao deste modulo existir e
impedir que sejam confundidas:

  A = GT x mascara prevista      -> erro de SEGMENTACAO (Tier2)
  B = mascara prevista x malha   -> erro de RECONSTRUCAO (Tier1)
  C = GT x malha rasterizada     -> CONSEQUENCIA CONJUNTA

A regra que o modulo aplica em toda saida: **o erro GT->malha NAO pode ser
atribuido ao algoritmo de reconstrucao**. Ele contem A inteiro. Se a mascara ja
esta 15 % menor que o GT, a malha herda isso mesmo com reconstrucao perfeita.

E por isso que `A + B != C`: as duas etapas nao somam. Elas podem ate se
CANCELAR — uma mascara inflada pela segmentacao mais uma reconstrucao que encolhe
produz um C melhor que A, e isso nao significa que a reconstrucao consertou nada.
O modulo mede o residual `C - A` e o rotula explicitamente como "o que a
reconstrucao acrescentou", nunca como "o erro da reconstrucao".

MASTER congelada: marching_cubes, sigma=0, Taubin=4, level=0.5, offset=0, sem
decimacao. Este modulo NAO altera nada do pipeline — so mede.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.geometry.reconstruction import reconstruct_surface  # noqa: E402
from scripts.validation.mesh_metrics import voxelizar_malha  # noqa: E402
from scripts.validation.segmentation_metrics import compare_masks  # noqa: E402
from scripts.validation.tier2 import geometria, mapeamento, rtstruct as rtst  # noqa: E402

RAIZ = Path(".clinica-dados/tier2/lctsc")
NA = "nao aplicavel"
NM = "nao medido"

# Configuracao da MASTER. Espelhada aqui so para ir no relatorio; nao e um ponto
# de ajuste. Qualquer mudanca aqui invalida a comparacao com o Tier1 publicado.
MASTER = {"method": "marching_cubes", "sigma_mm": 0.0, "taubin_iters": 4,
          "level": 0.5, "offset_mm": 0.0}

# Estruturas com divergencia de DEFINICAO conhecida entre GT e predicao. O
# residual C-A delas nao e interpretavel como efeito da reconstrucao, porque o
# proprio A ja mistura erro de modelo com desacordo de contorno.
DEFINICAO_DIVERGENTE = {
    "Heart": "GT inclui saco pericardico (atlas RTOG 1106); a predicao nao",
    "Esophagus": "GT contornado so do cricoide a juncao gastroesofagica",
    "Lung_L": "uniao de lobos apaga fissuras; atlas exclui vasos hilares > ~5 mm",
    "Lung_R": "uniao de lobos apaga fissuras; atlas exclui vasos hilares > ~5 mm",
}


def _dif(depois: dict, antes: dict, chaves) -> dict:
    """Residual chave a chave. String de um dos lados propaga, nunca vira 0."""
    out = {}
    for k in chaves:
        a, d = antes.get(k), depois.get(k)
        if isinstance(a, (int, float)) and isinstance(d, (int, float)) \
                and np.isfinite(float(a)) and np.isfinite(float(d)):
            out[f"residual_{k}"] = round(float(d) - float(a), 4)
        else:
            out[f"residual_{k}"] = NM
    return out


def medir_cadeia(gt: np.ndarray, pred: np.ndarray, affine: np.ndarray,
                 spacing) -> dict[str, Any]:
    """As tres medidas da cadeia para uma estrutura, na mesma grade."""
    gt = np.asarray(gt) > 0.5
    pred = np.asarray(pred) > 0.5

    # A — segmentacao: GT x mascara prevista. E Tier2.
    a = compare_masks(pred, gt, spacing)

    # reconstroi a MASTER a partir da mascara PREVISTA (nunca a partir do GT:
    # o pipeline de producao nunca ve o GT)
    r = reconstruct_surface(pred, affine, **MASTER)
    if r is None:
        return {"erro": "ausente: reconstruct_surface devolveu None (< 50 voxels ou dissolvida)",
                "A_segmentacao": a, "B_reconstrucao": NM, "C_conjunto": NM}
    malha = r.mesh
    rasterizada = voxelizar_malha(malha, gt.shape, affine) > 0.5

    # B — reconstrucao: mascara prevista x malha rasterizada de volta. E Tier1.
    #
    # ATENCAO — COM A MASTER (sigma=0) ESTA MEDIDA E DEGENERADA. Sem borramento, a
    # malha rasterizada de volta reproduz a mascara EXATAMENTE: dice 1,0 / hd95 0 /
    # assd 0 / volume 0 %, por construcao e nao por qualidade. Medido: com esfera de
    # 20 mm e GT == predicao, as TRES etapas devolvem 1,0 / 0 / 0 / 0.
    # O erro da reconstrucao com sigma=0 e SUB-VOXEL e a rasterizacao o quantiza para
    # fora. Quem mede B sem degenerar e o volume da MALHA contra o volume de voxel da
    # mascara — a malha corta o voxel pela metade no level=0,5 e nao e multipla dele.
    b = compare_masks(rasterizada, pred, spacing)
    vox_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    vol_mascara_mm3 = float(pred.sum()) * vox_mm3
    vol_malha_mm3 = abs(float(malha.volume)) * 1e9  # m3 -> mm3
    b["volume_malha_vs_mascara_pct"] = (
        round((vol_malha_mm3 - vol_mascara_mm3) / vol_mascara_mm3 * 100.0, 4)
        if vol_mascara_mm3 else NM)
    b["nota_degenerada"] = (
        "dice/hd95/assd/volume_error_pct desta etapa sao TAUTOLOGICOS com sigma=0: a "
        "rasterizacao reproduz a mascara por construcao. Leia "
        "volume_malha_vs_mascara_pct, que compara a malha (sub-voxel) com o volume de "
        "voxel da mascara sem passar pela rasterizacao."
    )
    # C — consequencia conjunta: GT x malha rasterizada. NAO e erro da reconstrucao.
    c = compare_masks(rasterizada, gt, spacing)

    chaves = ("dice", "iou", "hd95_mm", "assd_mm", "volume_error_pct")
    return {
        "erro": "",
        "A_segmentacao": {k: a[k] for k in a},
        "B_reconstrucao": {k: b[k] for k in b},
        "C_conjunto": {k: c[k] for k in c},
        # residual = quanto a reconstrucao ACRESCENTOU sobre o erro que ja existia.
        # Nao e "o erro da reconstrucao": B e que mede isso, contra a mascara.
        **_dif(c, a, chaves),
        "tris": int(len(malha.faces)),
        "watertight": bool(malha.is_watertight),
        "config_master": dict(MASTER),
    }


def rodar(caso: str, raiz: Path = RAIZ, log=print) -> dict:
    """Roda a cadeia nas estruturas do caso ja ingerido."""
    dir_caso = raiz / caso
    dir_gt, dir_pred = dir_caso / "gt", dir_caso / "pred_masks"
    manifesto = json.loads((dir_caso / "manifesto.json").read_text(encoding="utf-8"))

    import nibabel as nib

    linhas = []
    for gt_roi in manifesto["rois_encontradas"]:
        canonica = mapeamento.canonizar(gt_roi)
        if canonica is None:
            continue
        alvos = mapeamento.MAPA_LCTSC[canonica]
        caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{gt_roi}.nii.gz"
        caminhos_pred = [dir_pred / f"{n}.nii.gz" for n in alvos]

        # geometria ANTES de qualquer medida; desalinhamento aborta, nao vira Dice ruim
        try:
            for cp in caminhos_pred:
                geometria.verificar_alinhamento(cp, caminho_gt)
        except geometria.DesalinhamentoGeometrico as e:
            linhas.append({"case_id": caso, "gt_roi_name": gt_roi,
                           "structure": "+".join(alvos), "erro": f"ABORTADA: {e}"})
            log(f"  {gt_roi}: ABORTADA — {e}")
            continue

        img = nib.load(str(caminho_gt))
        affine = img.affine
        spacing = tuple(float(z) for z in img.header.get_zooms()[:3])
        gt = rtst.carregar_mascara(caminho_gt)
        pred, _ = mapeamento.unir_predicao(dir_pred, alvos)

        r = medir_cadeia(gt, pred, affine, spacing)
        linha = {
            "case_id": caso, "gt_roi_name": gt_roi, "structure": "+".join(alvos),
            "spacing_mm": list(spacing),
            "divergencia_de_definicao": DEFINICAO_DIVERGENTE.get(gt_roi, ""),
            **r,
        }
        linhas.append(linha)
        if not r["erro"]:
            log(f"  {gt_roi}: A dice={r['A_segmentacao']['dice']:.4f} | "
                f"B dice={r['B_reconstrucao']['dice']:.4f} | "
                f"C dice={r['C_conjunto']['dice']:.4f} | "
                f"residual_dice={r['residual_dice']:+.4f}")
    return {"caso": caso, "linhas": linhas}


def gravar(resultados: list[dict], destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    linhas = [l for r in resultados for l in r["linhas"]]
    (destino / "cadeia_ab.json").write_text(
        json.dumps({
            "leitura": (
                "A = GT x mascara prevista (SEGMENTACAO, Tier2). "
                "B = mascara prevista x malha (RECONSTRUCAO, Tier1). "
                "C = GT x malha (CONSEQUENCIA CONJUNTA). "
                "C NAO e erro de reconstrucao: contem A inteiro. "
                "A + B != C, e as duas etapas podem ate se cancelar."
            ),
            "config_master": dict(MASTER),
            "linhas": linhas,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    planas = []
    for l in linhas:
        base = {k: l[k] for k in ("case_id", "gt_roi_name", "structure",
                                  "divergencia_de_definicao", "erro") if k in l}
        for etapa in ("A_segmentacao", "B_reconstrucao", "C_conjunto"):
            m = l.get(etapa)
            if isinstance(m, dict):
                base.update({f"{etapa[0]}_{k}": v for k, v in m.items()})
        base.update({k: v for k, v in l.items() if k.startswith("residual_")})
        planas.append(base)
    if planas:
        campos = sorted({k for p in planas for k in p})
        with (destino / "cadeia_ab.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(planas)


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cadeia A->B (segmentacao -> reconstrucao)")
    ap.add_argument("--casos", nargs="+", required=True)
    ap.add_argument("--raiz", type=Path, default=RAIZ)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    res = []
    for c in a.casos:
        print(f"== {c}")
        res.append(rodar(c, a.raiz))
    gravar(res, a.out or (a.raiz / "resultados" / "cadeia_ab"))
    return 0


def _autoteste() -> None:
    """Controles que provam que as tres medidas sao MESMO diferentes."""
    from scripts.validation.phantom import esfera

    mask, affine = esfera(20.0, spacing=(1.0, 1.0, 1.0))
    spacing = (1.0, 1.0, 1.0)

    # (1) GT == predicao: A e perfeito, mas B e C NAO sao — a reconstrucao tem
    # erro proprio. Se C viesse igual a A aqui, as medidas estariam coladas.
    r = medir_cadeia(mask, mask, affine, spacing)
    assert r["erro"] == "", r
    assert r["A_segmentacao"]["dice"] == 1.0, r["A_segmentacao"]
    # A TAUTOLOGIA DA §4.2 codificada como FATO, nao como expectativa: com sigma=0
    # a rasterizacao de volta reproduz a mascara, entao as tres etapas colapsam em
    # 1,0. Este assert FALHA se alguem mudar a MASTER para uma config que borra a
    # mascara — e nesse dia a leitura de B tem que mudar junto.
    assert r["B_reconstrucao"]["dice"] == 1.0, (
        "B deixou de ser tautologico: a MASTER ainda tem sigma=0? "
        f"dice={r['B_reconstrucao']['dice']}")
    bv = r["B_reconstrucao"]["volume_malha_vs_mascara_pct"]
    assert isinstance(bv, float) and bv != 0.0, (
        f"volume_malha_vs_mascara_pct={bv}: a unica medida NAO-degenerada de B "
        "tambem colapsou — B ficou sem instrumento")
    assert abs(r["C_conjunto"]["dice"] - r["B_reconstrucao"]["dice"]) < 1e-9, \
        "com GT == pred, C tem que coincidir com B"

    # (2) predicao ERODIDA: A piora, e C herda esse erro. O residual C-A isola o
    # que a reconstrucao acrescentou por cima.
    from scipy import ndimage
    pred = ndimage.binary_erosion(mask, iterations=1)
    r2 = medir_cadeia(mask, pred, affine, spacing)
    assert r2["A_segmentacao"]["dice"] < 1.0
    assert r2["C_conjunto"]["dice"] < r["C_conjunto"]["dice"], \
        "C nao piorou com segmentacao pior: C nao esta herdando A"
    # o volume de C tem que ficar do lado do de A, nao do de B
    va = r2["A_segmentacao"]["volume_error_pct"]
    vc = r2["C_conjunto"]["volume_error_pct"]
    assert abs(vc - va) < abs(vc - r2["B_reconstrucao"]["volume_error_pct"]) or va * vc > 0, \
        f"C ({vc:+.2f}%) nao acompanha A ({va:+.2f}%): a cadeia nao esta encadeada"

    # (3) string nunca vira 0 no residual
    assert _dif({"x": "nao medido"}, {"x": 1.0}, ("x",))["residual_x"] == NM

    print("cadeia_ab.py: autoteste OK")
    print(f"  GT==pred  : A={r['A_segmentacao']['dice']:.4f} B={r['B_reconstrucao']['dice']:.4f} "
          f"C={r['C_conjunto']['dice']:.4f}  (as tres colapsam: tautologia de sigma=0)")
    print(f"              B nao-degenerado (volume malha x mascara) = "
          f"{r['B_reconstrucao']['volume_malha_vs_mascara_pct']:+.4f} %")
    print(f"  pred erodida: A={r2['A_segmentacao']['dice']:.4f} B={r2['B_reconstrucao']['dice']:.4f} "
          f"C={r2['C_conjunto']['dice']:.4f} residual={r2['residual_dice']:+.4f}")


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(_main())
