"""Pos-processamento de mascara binaria com regras por estrutura anatomica.

Por que regra por classe (e nao um pipeline unico):
  - "vaso" e "via_aerea": o lumen e uma cavidade REAL. Fechar buracos aqui
    transforma um tubo oco em um cilindro macico e destroi a anatomia. Alem
    disso a segmentacao de vaso/arvore bronquica se fragmenta naturalmente em
    ramos finos; manter multiplos componentes e o comportamento correto e o
    limiar de ilha e minusculo (2 mm3) so para varrer ruido de 1 voxel.
  - "lesao": NUNCA remove componente pequeno (nodulo de 3 mm e o achado, nao
    ruido) e nunca fecha buraco (necrose/cavitacao central e real).
  - "orgao": corpo solido e unico. Pode fechar cavidade interna (buraco ali
    quase sempre e falha do modelo em regiao heterogenea) e pode remover ilha
    de ate 30 mm3, mantendo apenas o maior componente.
  - "camara": intermediario. Volume de sangue e solido o bastante para manter
    componente unico e remover ilha de 10 mm3, mas NAO fecha buraco (musculo
    papilar e trabecula aparecem como buraco e sao reais).

Toda operacao destrutiva vai no dict de retorno (chave "operacoes") junto com
o delta de volume. Nada e aplicado silenciosamente. Volumes sempre em mm3
usando o spacing fisico (zooms), nunca contagem de voxel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage as ndi

# 26-conectividade: vaso/bronquio fino encosta na diagonal entre fatias;
# usar face-conectividade fragmentaria a estrutura artificialmente.
_CONECTIVIDADE = ndi.generate_binary_structure(3, 3)


@dataclass(frozen=True)
class RegraMascara:
    """Politica de limpeza de uma classe anatomica."""

    min_componente_mm3: float
    fechar_buracos: bool
    manter_multiplos: bool


REGRAS: dict[str, RegraMascara] = {
    "orgao": RegraMascara(min_componente_mm3=30.0, fechar_buracos=True, manter_multiplos=False),
    "vaso": RegraMascara(min_componente_mm3=2.0, fechar_buracos=False, manter_multiplos=True),
    "via_aerea": RegraMascara(min_componente_mm3=2.0, fechar_buracos=False, manter_multiplos=True),
    "camara": RegraMascara(min_componente_mm3=10.0, fechar_buracos=False, manter_multiplos=False),
    "lesao": RegraMascara(min_componente_mm3=0.0, fechar_buracos=False, manter_multiplos=True),
}


def classe_de(nome: str) -> str:
    """Classifica pelo nome de saida do TotalSegmentator (heuristica)."""
    n = nome.lower().removesuffix(".gz").removesuffix(".nii")
    if any(t in n for t in ("lesion", "tumor", "nodule", "nodulo", "lesao")):
        return "lesao"
    if n.startswith("lung") or "trachea" in n or "bronch" in n or "airway" in n:
        return "via_aerea"
    if any(
        t in n
        for t in ("aorta", "vein", "artery", "vena_cava", "iliac", "portal", "atrial_appendage")
    ):
        return "vaso"
    if n.startswith("heart_"):
        return "camara"
    return "orgao"


def processar_mascara(
    mask: np.ndarray,
    zooms: np.ndarray,
    nome: str,
    regra: RegraMascara | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Limpa a mascara segundo a regra da classe de `nome`.

    Args:
        mask: array 3D booleano (ou convertivel) da mascara.
        zooms: spacing fisico (mm) por eixo, ex. np.linalg.norm(affine[:3,:3], axis=0).
        nome: nome da estrutura (define a classe se `regra` nao for passada).
        regra: sobrescreve a regra da classe.

    Returns:
        (mascara_limpa, relatorio). O relatorio lista toda operacao aplicada.
    """
    m = np.asarray(mask).astype(bool)
    if m.ndim != 3:
        raise ValueError(f"mask deve ser 3D, recebido ndim={m.ndim}")
    vox_mm3 = float(np.prod(np.asarray(zooms, dtype=float)))
    classe = classe_de(nome)
    r = regra if regra is not None else REGRAS[classe]

    rot: list[str] = []
    vol_antes = float(m.sum()) * vox_mm3
    _, comp_antes = ndi.label(m, structure=_CONECTIVIDADE)

    buracos_mm3 = 0.0
    if r.fechar_buracos:
        preenchida = ndi.binary_fill_holes(m, structure=_CONECTIVIDADE)
        buracos_mm3 = float((preenchida & ~m).sum()) * vox_mm3
        if buracos_mm3 > 0.0:
            m = preenchida
            rot.append(f"fechar_buracos: +{buracos_mm3:.1f} mm3")
        else:
            rot.append("fechar_buracos: nenhum buraco interno")
    else:
        rot.append(f"fechar_buracos: pulado (classe '{classe}' — cavidade e real)")

    rotulos, n = ndi.label(m, structure=_CONECTIVIDADE)
    if n > 1 or r.min_componente_mm3 > 0.0:
        tamanhos = np.bincount(rotulos.ravel())
        tamanhos[0] = 0
        vols = tamanhos.astype(float) * vox_mm3

        if r.min_componente_mm3 > 0.0:
            pequenos = np.flatnonzero((vols > 0) & (vols < r.min_componente_mm3))
            if pequenos.size:
                removido = float(vols[pequenos].sum())
                m &= ~np.isin(rotulos, pequenos)
                vols[pequenos] = 0.0
                rot.append(
                    f"remover_ilhas < {r.min_componente_mm3:g} mm3: "
                    f"{pequenos.size} componente(s), -{removido:.1f} mm3"
                )
        else:
            rot.append(f"remover_ilhas: pulado (classe '{classe}' — lesao pode ser minuscula)")

        restantes = int(np.count_nonzero(vols))
        if not r.manter_multiplos and restantes > 1:
            maior = int(np.argmax(vols))
            removido = float(vols.sum() - vols[maior])
            m &= rotulos == maior
            rot.append(
                f"manter_maior_componente: descartados {restantes - 1}, -{removido:.1f} mm3"
            )
        elif r.manter_multiplos and restantes > 1:
            rot.append(f"manter_multiplos: {restantes} componentes preservados")

    vol_depois = float(m.sum()) * vox_mm3
    _, comp_depois = ndi.label(m, structure=_CONECTIVIDADE)

    relatorio: dict[str, Any] = {
        "nome": nome,
        "classe": classe,
        "regra": {
            "min_componente_mm3": r.min_componente_mm3,
            "fechar_buracos": r.fechar_buracos,
            "manter_multiplos": r.manter_multiplos,
        },
        "voxel_mm3": round(vox_mm3, 6),
        "volume_antes_mm3": round(vol_antes, 2),
        "volume_depois_mm3": round(vol_depois, 2),
        "delta_volume_pct": round(
            100.0 * (vol_depois - vol_antes) / vol_antes if vol_antes else 0.0, 4
        ),
        "componentes_antes": int(comp_antes),
        "componentes_depois": int(comp_depois),
        "buracos_fechados_mm3": round(buracos_mm3, 2),
        "operacoes": rot,
    }
    return m, relatorio


if __name__ == "__main__":  # autoteste com dados reais
    import json
    import sys
    from pathlib import Path

    import nibabel as nib

    base = Path(__file__).resolve().parents[2] / ".clinica-dados" / "torax-alta_masks"
    for arq in ("aorta.nii.gz", "heart.nii.gz", "trachea.nii.gz"):
        img = nib.load(str(base / arq))
        mask = np.asarray(img.dataobj) > 0.5
        zooms = np.linalg.norm(img.affine[:3, :3], axis=0)
        _, rel = processar_mascara(mask, zooms, arq)
        print(json.dumps(rel, indent=2, ensure_ascii=False))

    # contraste na MESMA mascara real: aorta tratada como 'orgao' fecha o lumen.
    img = nib.load(str(base / "aorta.nii.gz"))
    _, rel = processar_mascara(
        np.asarray(img.dataobj) > 0.5,
        np.linalg.norm(img.affine[:3, :3], axis=0),
        "aorta.nii.gz",
        regra=REGRAS["orgao"],
    )
    print("# aorta FORCADA com a regra de orgao (contraste):")
    print(json.dumps(rel, indent=2, ensure_ascii=False))
    print(
        "# nota: nenhuma mascara de torax-alta tem cavidade 3D TOTALMENTE fechada,"
        " entao buracos_fechados_mm3 = 0 mesmo com fechar_buracos=True."
        " O contraste vaso vs orgao vai no caso sintetico abaixo.",
        file=sys.stderr,
    )

    # checagem: cubo oco com casca -> orgao fecha o buraco, vaso nao.
    cubo = np.zeros((20, 20, 20), bool)
    cubo[5:15, 5:15, 5:15] = True
    cubo[8:12, 8:12, 8:12] = False
    cubo[0, 0, 0] = True  # ilha de 1 mm3
    z = np.ones(3)
    _, ro = processar_mascara(cubo, z, "liver")
    _, rv = processar_mascara(cubo, z, "aorta")
    print("# sintetico (casca oca + 1 ilha) — orgao vs vaso:")
    print(json.dumps({"orgao": ro, "vaso": rv}, indent=2, ensure_ascii=False))
    assert ro["buracos_fechados_mm3"] == 64.0 and rv["buracos_fechados_mm3"] == 0.0
    assert ro["componentes_depois"] == 1  # ilha removida + maior componente
    assert rv["componentes_depois"] == 1  # ilha de 1 mm3 < 2 mm3 tambem sai no vaso
    assert rv["volume_depois_mm3"] == 936.0  # casca do cubo intacta, lumen preservado
    print("autoteste sintetico OK", file=sys.stderr)
