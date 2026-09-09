"""Fase 26B — figuras de diagnostico: GT x predicao, em cortes 2D.

REGRA DE HONESTIDADE VISUAL

Nada aqui pode sugerir precisao maior do que a medida. Por isso:

  - os cortes NAO sao escolhidos a dedo. Sao 3 cortes axiais em posicoes fixas
    (25 %, 50 %, 75 % da extensao do GT) mais um corte coronal no centroide;
  - o Dice do caso aparece impresso NA figura, entao nenhuma imagem circula sem
    o numero que a qualifica;
  - GT e predicao usam contorno, nao preenchimento opaco, para que a discordancia
    fique visivel em vez de escondida sob a cor de cima;
  - a escala de cinza da CT e fixa em janela de mediastino (nivel 40, largura 400),
    a mesma para todos os casos — janela ajustada por caso deixaria um caso ruim
    parecer melhor.

Os casos sao escolhidos pela regra ja declarada na Fase 27 (melhor, mediano, pior
por Dice), nunca por serem visualmente interessantes.

  python -m scripts.validation.fase26b.figuras --autoteste
  python -m scripts.validation.fase26b.figuras --avaliacao <json> --saida <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]

# Janela de mediastino, fixa. Mudar por caso seria maquiar.
NIVEL, LARGURA = 40.0, 400.0
FRACOES = (0.25, 0.50, 0.75)


def _janela(a):
    import numpy as np
    lo, hi = NIVEL - LARGURA / 2, NIVEL + LARGURA / 2
    return np.clip((np.asarray(a, dtype=float) - lo) / (hi - lo), 0, 1)


def cortes_do_caso(gt):
    """Indices axiais em 25/50/75 % da extensao do GT. Posicao fixa, nao escolhida."""
    import numpy as np
    z = np.where(gt.any(axis=(0, 1)))[0]
    if z.size == 0:
        return []
    z0, z1 = int(z.min()), int(z.max())
    return [int(round(z0 + f * (z1 - z0))) for f in FRACOES]


def figura(case_id, img, gt, pred, dice, destino: Path, rotulo: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    zs = cortes_do_caso(gt)
    if not zs:
        return None
    fig, axes = plt.subplots(1, len(zs) + 1, figsize=(4 * (len(zs) + 1), 4.4))

    for ax, z in zip(axes[:len(zs)], zs):
        ax.imshow(_janela(img[:, :, z]).T, cmap="gray", origin="lower")
        if gt[:, :, z].any():
            ax.contour(gt[:, :, z].T.astype(float), levels=[0.5], colors="#22c55e", linewidths=1.4)
        if pred[:, :, z].any():
            ax.contour(pred[:, :, z].T.astype(float), levels=[0.5], colors="#ef4444",
                       linewidths=1.4, linestyles="--")
        ax.set_title("axial z=%d" % z, fontsize=9)
        ax.axis("off")

    # coronal no centroide do GT, para mostrar a extensao longitudinal
    ys = np.where(gt.any(axis=(0, 2)))[0]
    y = int(round(float(ys.mean()))) if ys.size else gt.shape[1] // 2
    ax = axes[-1]
    ax.imshow(_janela(img[:, y, :]).T, cmap="gray", origin="lower", aspect="auto")
    if gt[:, y, :].any():
        ax.contour(gt[:, y, :].T.astype(float), levels=[0.5], colors="#22c55e", linewidths=1.2)
    if pred[:, y, :].any():
        ax.contour(pred[:, y, :].T.astype(float), levels=[0.5], colors="#ef4444",
                   linewidths=1.2, linestyles="--")
    ax.set_title("coronal y=%d" % y, fontsize=9)
    ax.axis("off")

    fig.suptitle("%s  —  %s  —  Dice %.4f   (verde = GT, vermelho tracejado = predicao)"
                 % (case_id, rotulo, dice), fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=110)
    plt.close(fig)
    return destino


def selecionar(casos):
    """Melhor, mediano e pior por Dice. Regra fixa, nunca 'o mais interessante'."""
    ordenados = sorted(casos, key=lambda c: c["dice"])
    return [(ordenados[0], "PIOR"),
            (ordenados[len(ordenados) // 2], "MEDIANO"),
            (ordenados[-1], "MELHOR")]


def autoteste() -> int:
    import numpy as np
    falhas = []

    # 1. os cortes ficam DENTRO da extensao do GT e sao os das fracoes declaradas
    gt = np.zeros((20, 20, 40), bool)
    gt[8:12, 8:12, 10:30] = True
    # GT ocupa z de 10 a 29 (extensao 19): 25 % -> 14,75 -> 15; 50 % -> 19,5 -> 20;
    # 75 % -> 24,25 -> 24. Os valores vem da conta, nao de expectativa aproximada.
    zs = cortes_do_caso(gt)
    if zs != [15, 20, 24]:
        falhas.append("cortes fora das fracoes declaradas: %s" % zs)

    # 2. GT vazio nao quebra, devolve lista vazia
    if cortes_do_caso(np.zeros((5, 5, 5), bool)) != []:
        falhas.append("GT vazio nao devolveu lista vazia")

    # 3. a janela e FIXA e nao depende do conteudo: mesma entrada -> mesma saida,
    #    e um caso com HU altos nao remapeia a escala
    a = _janela(np.array([-160.0, 40.0, 240.0]))
    if not (abs(a[0]) < 1e-9 and abs(a[1] - 0.5) < 1e-9 and abs(a[2] - 1.0) < 1e-9):
        falhas.append("janela nao esta em nivel 40 largura 400: %s" % a)
    b = _janela(np.array([-160.0, 40.0, 240.0, 3000.0]))
    if not np.allclose(a, b[:3]):
        falhas.append("a janela mudou por causa de um voxel extremo — escala nao e fixa")

    # 4. a selecao pega pior/mediano/melhor, e nao o mais vistoso
    casos = [{"case_id": "c%d" % i, "dice": d} for i, d in enumerate([0.9, 0.1, 0.5, 0.7, 0.3])]
    sel = selecionar(casos)
    if [s[0]["dice"] for s in sel] != [0.1, 0.5, 0.9]:
        falhas.append("selecao errada: %s" % [s[0]["dice"] for s in sel])
    if [s[1] for s in sel] != ["PIOR", "MEDIANO", "MELHOR"]:
        falhas.append("rotulos trocados")

    # 5. a figura sai mesmo, com o Dice no titulo
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        img = np.random.RandomState(0).normal(0, 200, (20, 20, 40))
        p = figura("TESTE", img, gt, gt, 0.9999, Path(d) / "f.png", "MELHOR")
        if p is None or not p.exists() or p.stat().st_size < 5000:
            falhas.append("a figura nao foi gerada")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste figuras: %d verificacoes, %d falhas" % (5, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--avaliacao")
    ap.add_argument("--predicoes")
    ap.add_argument("--saida", default=str(RAIZ / "docs" / "overnight" / "phase26b" / "figuras"))
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    if not (a.avaliacao and a.predicoes):
        print("faltou --avaliacao e --predicoes")
        return 1

    import numpy as np
    import nibabel as nib

    r = json.loads(Path(a.avaliacao).read_text(encoding="utf-8"))
    feitas = []
    for caso, rotulo in selecionar(r["casos"]):
        cid = caso["case_id"]
        gt = np.asanyarray(nib.load(str(RAIZ / caso["mask_path"])).dataobj) > 0
        img_p = RAIZ / ".clinica-dados" / "fase26" / "validation_holdout" / "images" / ("%s_0000.nii.gz" % cid)
        img = np.asanyarray(nib.load(str(img_p)).dataobj)
        pred = np.asanyarray(nib.load(str(Path(a.predicoes) / ("%s.nii.gz" % cid))).dataobj) > 0
        d = figura(cid, img, gt, pred, caso["dice"],
                   Path(a.saida) / ("%s_%s.png" % (rotulo.lower(), cid)), rotulo)
        if d:
            feitas.append(str(d))
            print("  %-8s %-24s dice %.4f -> %s" % (rotulo, cid, caso["dice"], d.name))
    print("\n%d figuras em %s" % (len(feitas), a.saida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
