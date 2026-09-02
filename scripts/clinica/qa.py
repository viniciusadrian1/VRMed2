"""
QA visual — máscaras coloridas sobre a TC em 3 cortes × 3 planos, mais um
mosaico. É a prova intermediária pedida pelo plano ("me mostre as máscaras
sobrepostas ao CT antes da malha"): confere segmentação, orientação
(convenção radiológica: direita do paciente à ESQUERDA da imagem) e escala
(aspecto corrigido pelo spacing real). Só nibabel + Pillow, já no venv.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .cores import cor_para

JANELAS: dict[str, tuple[int, int]] = {
    "torax": (-1000, 400),
    "cardiaco": (-200, 600),  # contraste iodado no sangue fica claro sem estourar
    "abdome": (-150, 250),
}
PLANOS = {"axial": 2, "coronal": 1, "sagital": 0}
FRACOES = (0.25, 0.5, 0.75)
ALFA = 0.45
FUNDO = (16, 20, 24)
TEXTO = (235, 235, 235)


def _fonte(tamanho: int = 16) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:  # Pillow antigo
        return ImageFont.load_default()


def _canonico(caminho: Path) -> nib.Nifti1Image:
    """Reorienta para RAS: índice [x, y, z] = [direita, anterior, superior]."""
    return nib.as_closest_canonical(nib.load(str(caminho)))


def _corte(vol: np.ndarray, eixo: int, k: int) -> np.ndarray:
    """Corte 2D já na convenção radiológica: linhas = eixo maior decrescente
    (anterior/superior em cima), colunas = eixo menor decrescente (direita do
    paciente à esquerda; no sagital, anterior à esquerda)."""
    return np.flip(np.take(vol, k, axis=eixo).T, (0, 1))


def _bbox(rotulos: np.ndarray) -> list[tuple[int, int]]:
    caixa = []
    for eixo in range(3):
        outros = tuple(i for i in range(3) if i != eixo)
        onde = np.flatnonzero(np.any(rotulos, axis=outros))
        caixa.append((int(onde[0]), int(onde[-1])) if len(onde) else (0, rotulos.shape[eixo] - 1))
    return caixa


def _mosaico(tiles: dict, nomes: list[str], cores: dict, fonte, altura: int = 330) -> Image.Image:
    planos = list(PLANOS)
    escalados = {
        k: v.resize((round(v.width * altura / v.height), altura), Image.BILINEAR)
        for k, v in tiles.items()
    }
    larguras = [max(escalados[(p, f)].width for p in planos) for f in FRACOES]
    linhas_legenda = (len(nomes) + 3) // 4
    largura = sum(larguras) + 8 * (len(FRACOES) + 1)
    alt = altura * len(planos) + 8 * (len(planos) + 1) + 26 * linhas_legenda + 12
    canvas = Image.new("RGB", (largura, alt), FUNDO)
    draw = ImageDraw.Draw(canvas)
    y = 8
    for plano in planos:
        x = 8
        for frac, larg in zip(FRACOES, larguras):
            canvas.paste(escalados[(plano, frac)], (x, y))
            x += larg + 8
        y += altura + 8
    x, passo = 8, (largura - 16) // 4
    for i, nome in enumerate(nomes):
        if i and i % 4 == 0:
            x, y = 8, y + 26
        draw.rectangle([x, y + 4, x + 16, y + 20], fill=cores[i + 1])
        draw.text((x + 22, y + 3), nome, fill=TEXTO, font=fonte)
        x += passo
    return canvas


def sobrepor(
    ct_path: Path,
    masks_dir: Path,
    saida_dir: Path,
    janela: tuple[int, int] = JANELAS["torax"],
    estruturas: list[str] | None = None,
    log=print,
) -> dict:
    """Gera saida_dir/<plano>_<25|50|75>.png e saida_dir/mosaico.png."""
    ct = _canonico(ct_path)
    vol = np.asarray(ct.dataobj).astype(np.float32)
    zooms = np.array(ct.header.get_zooms()[:3], dtype=float)

    # Um volume de rótulos (uint8) em vez de uma máscara bool por estrutura:
    # 13 máscaras de 512×512×321 seriam >1 GB em RAM.
    rotulos = np.zeros(vol.shape, dtype=np.uint8)
    nomes: list[str] = []
    for caminho in sorted(masks_dir.glob("*.nii.gz")):
        nome = caminho.name.removesuffix(".nii.gz")
        if estruturas is not None and nome not in estruturas:
            continue
        mask = np.asarray(_canonico(caminho).dataobj) > 0.5
        if mask.shape != vol.shape:
            log(f"AVISO: {nome} tem shape {mask.shape} ≠ TC {vol.shape}; pulando no QA")
            continue
        if not mask.any() or len(nomes) >= 255:
            continue
        nomes.append(nome)
        rotulos[mask] = len(nomes)
    cores = {i + 1: tuple(int(c * 255) for c in cor_para(n)) for i, n in enumerate(nomes)}
    caixa = _bbox(rotulos)
    lo_hu, hi_hu = janela
    fonte = _fonte(16)
    saida_dir.mkdir(parents=True, exist_ok=True)

    arquivos: list[Path] = []
    tiles: dict = {}
    for plano, eixo in PLANOS.items():
        a, b = [i for i in range(3) if i != eixo]
        zoom_rc = (zooms[b], zooms[a])  # linhas = eixo b, colunas = eixo a
        lado = ("R", "L") if plano != "sagital" else ("A", "P")
        lo, hi = caixa[eixo]
        for frac in FRACOES:
            k = int(round(lo + frac * (hi - lo)))
            ct2d = _corte(vol, eixo, k)
            rot2d = _corte(rotulos, eixo, k)
            cinza = np.clip((ct2d - lo_hu) / (hi_hu - lo_hu), 0.0, 1.0) * 255.0
            rgb = np.repeat(cinza[..., None], 3, axis=2)
            for rid, cor in cores.items():
                sel = rot2d == rid
                if sel.any():
                    rgb[sel] = rgb[sel] * (1 - ALFA) + np.array(cor, dtype=np.float32) * ALFA
            img = Image.fromarray(rgb.astype(np.uint8))
            menor = min(zoom_rc)
            img = img.resize(
                (round(img.width * zoom_rc[1] / menor), round(img.height * zoom_rc[0] / menor)),
                Image.BILINEAR,
            )
            titulo = f"{plano} #{k} · {int(frac * 100)}% do bbox · janela {lo_hu}..{hi_hu} HU"
            canvas = Image.new("RGB", (img.width, img.height + 26), FUNDO)
            canvas.paste(img, (0, 26))
            draw = ImageDraw.Draw(canvas)
            draw.text((6, 5), titulo, fill=TEXTO, font=fonte)
            meio = 26 + img.height // 2
            draw.text((6, meio), lado[0], fill=(255, 220, 80), font=fonte)
            draw.text((img.width - 16, meio), lado[1], fill=(255, 220, 80), font=fonte)
            destino = saida_dir / f"{plano}_{int(frac * 100)}.png"
            canvas.save(destino)
            arquivos.append(destino)
            tiles[(plano, frac)] = canvas

    mosaico = saida_dir / "mosaico.png"
    _mosaico(tiles, nomes, cores, fonte).save(mosaico)
    return {
        "arquivos": [str(p) for p in arquivos],
        "mosaico": str(mosaico),
        "estruturas": nomes,
        "janela_hu": list(janela),
    }
