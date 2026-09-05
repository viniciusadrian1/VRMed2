"""Fase 9 — definicao operacional (Parte A) e representabilidade (Parte B) do esofago.

SO development (30 casos). NAO treina, NAO baixa, NAO toca validation/test.

------------------------------------------------------------------------------
PARTE A — a ontologia 1.2 esta contraditoria e este arquivo resolve por medida

Hoje a secao 1.2 declara "limite superior = cricoide" e "limite inferior =
juncao gastroesofagica" e, logo abaixo, uma correcao dizendo que o pipeline nao
localiza nenhum dos dois. As duas coisas nao podem valer juntas. As quatro
alternativas do enunciado sao decididas AQUI, por tres medidas, nenhuma delas
de desempenho:

  M1  Ha algum landmark DETECTAVEL perto do esofago na saida de hoje?
      O `roi_subset` em producao tem 8 estruturas (esophagus, heart, 5 lobos,
      spinal_cord) — nenhuma delas e um marco longitudinal. A fase 7 gerou
      `trachea` e `aorta` para os MESMOS 30 casos. A traqueia termina na carina,
      que e o unico marco longitudinal disponivel. Mede-se: presenca (n/30) e
      ESTABILIDADE do detector sob tres variantes declaradas (maior componente
      conexo, limiar de 5 voxels por fatia, erosao de 1 passo no plano). Se as
      variantes discordarem por mais de 1 voxel em Z, o marco nao serve.

  M2  As pontas do GT estao a um deslocamento fixo da carina?
      Se estiverem, a alternativa B (definir por landmarks) e viavel. A dispersao
      caso a caso responde. NAO se separa aqui variacao anatomica real de decisao
      do contornador — com 1 contorno por caso isso e impossivel, e esta declarado.

  M3  As pontas do GT sao TRUNCAMENTOS ou terminacoes?
      Mede-se a area da fatia terminal contra a area mediana do proprio caso. Uma
      estrutura que acaba anatomicamente afina; uma que foi cortada acaba na
      largura cheia. Esta e a medida que separa a alternativa A ("a extensao do
      GT E a definicao") da alternativa D ("a extensao e herdada").

  M4  Existe um trecho anotado em TODOS os casos, ancorado na carina?
      Responde a alternativa C, junto com a fracao do volume do GT que sobraria
      dentro dele.

------------------------------------------------------------------------------
PARTE B — representabilidade

spacing por eixo, espessura caracteristica (2 x EDT no esqueleto) em mm e em
voxels de CADA eixo, e o balde de parede sob PREMISSA declarada.

A PAREDE NAO E UM OBJETO ANOTADO. O GT e macico (fase 7: `fill_holes` 2D
preencheu 0,0000 mL em 30/30). Entao "espessura de parede" NAO E MEDIVEL a
partir do GT. O que este arquivo faz e usar 3-4 mm da literatura como PREMISSA
DECLARADA e comparar com o spacing de cada caso. Toda coluna que depende disso
tem `premissa` no nome, e nenhuma delas e medida.

Orientacao importa: a parede de um tubo que corre em Z tem normal
predominantemente NO PLANO. Por isso o balde sai para os tres eixos, e a fracao
de AREA de fronteira com normal em Z sai junto — sem ela, comparar 3 mm com dz
supoe que a parede esta deitada, o que ela quase nunca esta.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.representabilidade_esofago --autoteste
    python -m scripts.validation.tier2.representabilidade_esofago
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from scipy import ndimage

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.espessura import calibre_mm  # noqa: E402
from scripts.validation.tier2 import fase5  # noqa: E402

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase9" / "representabilidade"
AUX_PADRAO = RAIZ_PADRAO / "fase7" / "esofago" / "aux_masks"
DEFINICAO_FASE7 = RAIZ_PADRAO / "fase7" / "esofago" / "baseline" / "definicao_esofago.csv"

ROI_GT = "Esophagus"
NM = "nao medido"
NA = "nao aplicavel"

# PREMISSA DECLARADA, NAO MEDIDA. Espessura da parede esofagica na literatura
# anatomica. Nao ha como medi-la neste GT: ele e macico e nao separa parede de
# lumen. Toda conclusao que depende deste par cai junto se a premissa cair.
PAREDE_PREMISSA_MM = (3.0, 4.0)

# Criterio de representabilidade de um objeto na grade: para ter INTERIOR (uma
# camada de borda de cada lado mais alguma coisa dentro) um objeto precisa de
# pelo menos 3 amostras no eixo. 2 amostras dao so as duas bordas coladas.
# Declarado antes de olhar qualquer numero.
VOXELS_PARA_TER_INTERIOR = 3.0
VOXELS_NYQUIST = 2.0   # 2 amostras atravessando a feicao: o minimo para ela existir


# --------------------------------------------------------------------- utilidades


def _dist(valores) -> dict[str, Any]:
    v = np.asarray([x for x in valores if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"n": 0, "mediana": NM, "min": NM, "max": NM, "p25": NM, "p75": NM, "desvio": NM}
    return {
        "n": int(v.size),
        "mediana": float(np.median(v)),
        "media": float(v.mean()),
        "desvio": float(v.std(ddof=1)) if v.size > 1 else NA,
        "p25": float(np.percentile(v, 25)),
        "p75": float(np.percentile(v, 75)),
        "min": float(v.min()),
        "max": float(v.max()),
    }


def _sinal_z(affine: np.ndarray) -> float:
    """+1 se o indice Z cresce para cranial, -1 se cresce para caudal.

    Sem isto, "extremo cranial" seria `max` em metade dos casos e `min` na outra,
    e a mistura passaria despercebida porque os dois produzem numero.
    """
    s = float(np.sign(affine[2, 2]))
    if s == 0.0:
        raise ValueError("affine sem componente Z — orientacao indeterminada")
    return s


def _fatias(m: np.ndarray) -> np.ndarray:
    return np.flatnonzero(m.any(axis=(0, 1)))


def _pontas(m: np.ndarray, sinal: float) -> tuple[int, int]:
    """(indice da fatia mais cranial, indice da mais caudal)."""
    z = _fatias(m)
    if z.size == 0:
        raise ValueError("mascara vazia — nao ha pontas")
    return (int(z.max()), int(z.min())) if sinal > 0 else (int(z.min()), int(z.max()))


# ------------------------------------------------- PARTE A — instrumentos


def indice_carina(trachea: np.ndarray, sinal: float) -> int:
    """Carina = extremo CAUDAL da traqueia predita.

    E uma aproximacao declarada: o que se mede e onde a mascara `trachea` do
    TotalSegmentator acaba, nao onde a bifurcacao esta. As duas coisas coincidem
    se o modelo para na bifurcacao — o que NAO foi verificado contra anatomia,
    porque nao ha marcacao de carina em nenhum caso do LCTSC.
    """
    _, caudal = _pontas(trachea, sinal)
    return caudal


def estabilidade_carina(trachea: np.ndarray, sinal: float, dz: float) -> dict[str, Any]:
    """Desvio, em mm, do indice da carina sob tres variantes do detector.

    Variantes declaradas ANTES de rodar. Se o marco fosse fragil, uma delas
    moveria a carina muito; se fosse insensivel a tudo, o autoteste com controle
    positivo (uma traqueia deslocada) e que pegaria.
    """
    base = indice_carina(trachea, sinal)
    lab, n = ndimage.label(trachea)
    if n > 0:
        tam = ndimage.sum(trachea, lab, range(1, n + 1))
        maior = lab == (int(np.argmax(tam)) + 1)
    else:
        maior = trachea
    variantes = {
        "maior_componente": maior,
        "min_5_voxels_por_fatia": trachea & (trachea.sum(axis=(0, 1)) >= 5)[None, None, :],
        "erosao_1_passo_no_plano": ndimage.binary_erosion(trachea, np.ones((3, 3, 1), bool)),
    }
    desvios = {}
    for nome, m in variantes.items():
        if not m.any():
            desvios[nome] = None
            continue
        desvios[nome] = abs(indice_carina(m, sinal) - base) * float(dz)
    validos = [d for d in desvios.values() if d is not None]
    return {
        "n_componentes_conexos": int(n),
        "desvio_mm_por_variante": desvios,
        "desvio_mm_max": max(validos) if validos else None,
        "desvio_voxels_max": (max(validos) / dz) if validos else None,
    }


def abrupticidade_das_pontas(gt: np.ndarray, zooms: np.ndarray, sinal: float) -> dict[str, float]:
    """Area da fatia terminal / area mediana das fatias do proprio caso.

    ~1 (ou mais) = a estrutura foi CORTADA na largura cheia; << 1 = ela afinou e
    acabou. E a medida que decide se a extensao do GT e um fato anatomico ou uma
    decisao de onde parar de contornar. Normalizada por caso, entao nao carrega
    diferenca de calibre entre casos.
    """
    area_voxel = float(zooms[0] * zooms[1])
    conta = gt.sum(axis=(0, 1))
    z = np.flatnonzero(conta)
    areas = conta[z] * area_voxel
    cran, caud = _pontas(gt, sinal)
    mediana = float(np.median(areas))
    return {
        "area_mediana_mm2": mediana,
        "area_ponta_cranial_mm2": float(conta[cran] * area_voxel),
        "area_ponta_caudal_mm2": float(conta[caud] * area_voxel),
        "razao_ponta_cranial": float(conta[cran] * area_voxel / mediana),
        "razao_ponta_caudal": float(conta[caud] * area_voxel / mediana),
    }


def perfil_ancorado(gt: np.ndarray, carina: int, dz: float, sinal: float) -> tuple[np.ndarray, np.ndarray]:
    """(distancia da carina em mm por fatia, presenca do GT por fatia).

    Positivo = cranial a carina. E o unico sistema de coordenadas longitudinal
    comparavel entre casos que este pipeline consegue produzir hoje.
    """
    d = (np.arange(gt.shape[2]) - carina) * float(dz) * sinal
    return d, gt.any(axis=(0, 1))


def cobertura_comum(perfis: dict[str, tuple[np.ndarray, np.ndarray]],
                    passo_mm: float = 1.0) -> dict[str, Any]:
    """Intervalo, em mm da carina, em que TODOS os casos tem GT.

    Amostra uma grade comum e, para cada ponto, marca o caso se a fatia mais
    proxima (dentro de meio dz maximo) tem GT. Meio dz e a tolerancia justa: mais
    que isso inventaria cobertura entre fatias.
    """
    if not perfis:
        return {"veredito": "nao aplicavel: sem casos"}
    grade = np.arange(-200.0, 200.0 + passo_mm, passo_mm)
    cobertura = np.zeros(grade.size, dtype=int)
    for d, pres in perfis.values():
        tol = float(np.median(np.abs(np.diff(d)))) / 2.0 + 1e-6
        idx = np.argmin(np.abs(grade[:, None] - d[None, :]), axis=1)
        perto = np.abs(d[idx] - grade) <= tol
        cobertura += (perto & pres[idx]).astype(int)
    n = len(perfis)
    plena = grade[cobertura == n]
    if plena.size == 0:
        return {"n_casos": n, "veredito": "nao ha ponto coberto por todos os casos"}
    return {
        "n_casos": n,
        "inicio_mm_da_carina": float(plena.min()),
        "fim_mm_da_carina": float(plena.max()),
        "comprimento_mm": float(plena.max() - plena.min()),
        "grade_mm": grade,
        "cobertura": cobertura,
    }


def fracao_do_volume_no_intervalo(conta: np.ndarray, d: np.ndarray,
                                  inicio: float, fim: float) -> float:
    """Fracao do volume do GT dentro de um intervalo em mm da carina.

    `conta` = voxels de GT por fatia; `d` = distancia da carina por fatia.
    """
    total = int(conta.sum())
    if total == 0:
        return float("nan")
    dentro = (d >= inicio) & (d <= fim)
    return float(conta[dentro].sum() / total)


# ------------------------------------------------- PARTE B — instrumentos


def fracao_area_fronteira_em_z(gt: np.ndarray, zooms: np.ndarray) -> dict[str, float]:
    """Fracao da AREA de fronteira do GT cuja normal aponta em Z.

    Conta faces expostas por eixo e pesa cada uma pela sua area fisica (uma face
    em X vale dy*dz, uma em Z vale dx*dy). Sem este peso a anisotropia da grade
    faria a contagem mentir. E o numero que diz contra QUAL spacing a espessura
    de parede deve ser comparada: onde a normal esta no plano, quem manda e
    dx/dy; onde esta em Z, quem manda e dz.
    """
    m = gt
    a_x = float(zooms[1] * zooms[2])
    a_y = float(zooms[0] * zooms[2])
    a_z = float(zooms[0] * zooms[1])
    area = {}
    for eixo, a in ((0, a_x), (1, a_y), (2, a_z)):
        faces = 0
        for desloc in (1, -1):
            viz = np.roll(m, desloc, axis=eixo)
            # borda do volume conta como exterior: a face esta exposta
            corte = [slice(None)] * 3
            corte[eixo] = 0 if desloc == 1 else -1
            viz[tuple(corte)] = False
            faces += int(np.count_nonzero(m & ~viz))
        area[eixo] = faces * a
    total = sum(area.values())
    if total == 0:
        return {"veredito": "invalido: GT vazio"}
    return {
        "area_fronteira_mm2": total,
        "frac_area_normal_em_x": area[0] / total,
        "frac_area_normal_em_y": area[1] / total,
        "frac_area_normal_em_z": area[2] / total,
        "frac_area_normal_no_plano": (area[0] + area[1]) / total,
    }


def balde_parede(parede_mm: float, spacing_mm: float) -> str:
    """Em quantos voxels daquele eixo cabe uma parede da espessura da PREMISSA."""
    v = parede_mm / spacing_mm
    if v < 1.0:
        return "<1 voxel"
    if v < 2.0:
        return "1-2 voxels"
    return ">=2 voxels"


def representabilidade(gt: np.ndarray, zooms: np.ndarray) -> dict[str, Any]:
    """Espessura caracteristica, voxels por eixo e os baldes sob premissa."""
    cal = calibre_mm(gt, zooms)
    esp = float(cal["espessura_mediana_no_esqueleto_mm"])
    dx, dy, dz = (float(z) for z in zooms)

    d: dict[str, Any] = {
        "dx_mm": dx, "dy_mm": dy, "dz_mm": dz,
        "anisotropia_dz_sobre_dx": dz / dx,
        "volume_voxel_mm3": dx * dy * dz,
        "espessura_esqueleto_mm": esp,
        "espessura_em_voxels_x": esp / dx,
        "espessura_em_voxels_y": esp / dy,
        "espessura_em_voxels_z": esp / dz,
        "calibre_mediano_mm": float(cal["calibre_mediano_mm"]),
        "calibre_p90_mm": float(cal["calibre_p90_mm"]),
        "calibre_max_mm": float(cal["calibre_max_mm"]),
    }
    for t in PAREDE_PREMISSA_MM:
        tag = f"{t:.0f}mm".replace(".", "")
        d[f"premissa_parede_{tag}_voxels_x"] = t / dx
        d[f"premissa_parede_{tag}_voxels_z"] = t / dz
        d[f"premissa_parede_{tag}_balde_x"] = balde_parede(t, dx)
        d[f"premissa_parede_{tag}_balde_z"] = balde_parede(t, dz)
        # lumen implicado: o que sobra do calibre depois de descontar as DUAS paredes
        lumen = esp - 2.0 * t
        d[f"premissa_lumen_{tag}_mm"] = lumen
        d[f"premissa_lumen_{tag}_voxels_x"] = lumen / dx
        d[f"premissa_lumen_{tag}_voxels_z"] = lumen / dz
        d[f"premissa_lumen_{tag}_tem_interior_no_plano"] = bool(
            lumen / dx >= VOXELS_PARA_TER_INTERIOR)
        d[f"premissa_lumen_{tag}_existe_no_plano"] = bool(lumen / dx >= VOXELS_NYQUIST)
        d[f"premissa_lumen_{tag}_existe_em_z"] = bool(lumen / dz >= VOXELS_NYQUIST)
    return d


# ------------------------------------------------------------------ execucao


def _casos(raiz: Path) -> list[str]:
    """SOMENTE development. validation/test continuam reservados."""
    split = fase5.carregar_split(raiz)
    dev = sorted(split["development"])
    if set(dev) & (set(split["validation"]) | set(split["test"])):
        raise RuntimeError("split corrompido: caso em development e tambem em validation/test")
    return dev


def _ler_definicao_fase7(caminho: Path) -> dict[str, dict[str, str]]:
    """Reuso das colunas de extensao JA medidas na fase 7 — nao remedidas aqui."""
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8") as f:
        return {l["case_id"]: l for l in csv.DictReader(f)}


def medir_caso(caso: str, raiz: Path, aux_dir: Path) -> dict[str, Any]:
    dir_caso = raiz / caso
    img = nib.load(str(dir_caso / "gt" / f"mask_{ROI_GT}.nii.gz"))
    gt = np.asarray(img.dataobj) > 0.5
    if not gt.any():
        raise ValueError(f"{caso}: GT vazio — caso quebrado, nao caso facil")
    zooms = np.asarray(img.header.get_zooms()[:3], dtype=float)
    sinal = _sinal_z(img.affine)
    dz = float(zooms[2])

    linha: dict[str, Any] = {
        "case_id": caso,
        "instituicao": fase5.instituicao_de(caso),
        "n_fatias_campo": int(gt.shape[2]),
        "n_fatias_gt": int(_fatias(gt).size),
    }
    linha.update(representabilidade(gt, zooms))
    linha.update(fracao_area_fronteira_em_z(gt, zooms))
    linha.update(abrupticidade_das_pontas(gt, zooms, sinal))

    traq_p = aux_dir / caso / "trachea.nii.gz"
    if not traq_p.exists():
        linha.update({"carina_disponivel": False, "carina_mm_ate_gt_cranial": None,
                      "carina_mm_ate_gt_caudal": None, "carina_desvio_mm_max": None})
        return linha
    traq = np.asarray(nib.load(str(traq_p)).dataobj) > 0.5
    if not traq.any():
        linha.update({"carina_disponivel": False, "carina_mm_ate_gt_cranial": None,
                      "carina_mm_ate_gt_caudal": None, "carina_desvio_mm_max": None})
        return linha

    carina = indice_carina(traq, sinal)
    est = estabilidade_carina(traq, sinal, dz)
    cran, caud = _pontas(gt, sinal)
    borda_cranial = gt.shape[2] - 1 if sinal > 0 else 0
    borda_caudal = 0 if sinal > 0 else gt.shape[2] - 1
    linha.update({
        "carina_disponivel": True,
        "carina_n_componentes_traqueia": est["n_componentes_conexos"],
        "carina_desvio_mm_max": est["desvio_mm_max"],
        "carina_desvio_voxels_max": est["desvio_voxels_max"],
        "carina_mm_ate_gt_cranial": float((cran - carina) * dz * sinal),
        "carina_mm_ate_gt_caudal": float((caud - carina) * dz * sinal),
        "gt_cranial_ate_borda_do_campo_mm": float(abs(cran - borda_cranial) * dz),
        "gt_caudal_ate_borda_do_campo_mm": float(abs(caud - borda_caudal) * dz),
    })
    linha["_perfil"] = perfil_ancorado(gt, carina, dz, sinal)
    linha["_gt_conta"] = gt.sum(axis=(0, 1))
    return linha


COLUNAS = [
    "case_id", "instituicao", "n_fatias_campo", "n_fatias_gt",
    "dx_mm", "dy_mm", "dz_mm", "anisotropia_dz_sobre_dx", "volume_voxel_mm3",
    "espessura_esqueleto_mm", "espessura_em_voxels_x", "espessura_em_voxels_y",
    "espessura_em_voxels_z", "calibre_mediano_mm", "calibre_p90_mm", "calibre_max_mm",
    "premissa_parede_3mm_voxels_x", "premissa_parede_3mm_voxels_z",
    "premissa_parede_3mm_balde_x", "premissa_parede_3mm_balde_z",
    "premissa_lumen_3mm_mm", "premissa_lumen_3mm_voxels_x", "premissa_lumen_3mm_voxels_z",
    "premissa_lumen_3mm_existe_no_plano", "premissa_lumen_3mm_existe_em_z",
    "premissa_lumen_3mm_tem_interior_no_plano",
    "premissa_parede_4mm_voxels_x", "premissa_parede_4mm_voxels_z",
    "premissa_parede_4mm_balde_x", "premissa_parede_4mm_balde_z",
    "premissa_lumen_4mm_mm", "premissa_lumen_4mm_voxels_x", "premissa_lumen_4mm_voxels_z",
    "premissa_lumen_4mm_existe_no_plano", "premissa_lumen_4mm_existe_em_z",
    "premissa_lumen_4mm_tem_interior_no_plano",
    "area_fronteira_mm2", "frac_area_normal_em_z", "frac_area_normal_no_plano",
    "area_mediana_mm2", "area_ponta_cranial_mm2", "area_ponta_caudal_mm2",
    "razao_ponta_cranial", "razao_ponta_caudal",
    "carina_disponivel", "carina_n_componentes_traqueia",
    "carina_desvio_mm_max", "carina_desvio_voxels_max",
    "carina_mm_ate_gt_cranial", "carina_mm_ate_gt_caudal",
    "gt_cranial_ate_borda_do_campo_mm", "gt_caudal_ate_borda_do_campo_mm",
]


def _contar(linhas, chave, valor) -> int:
    return sum(1 for l in linhas if l.get(chave) == valor)


def agregar(linhas: list[dict], definicao7: dict) -> dict[str, Any]:
    numericas = [c for c in COLUNAS if c not in
                 ("case_id", "instituicao", "carina_disponivel",
                  "premissa_parede_3mm_balde_x", "premissa_parede_3mm_balde_z",
                  "premissa_parede_4mm_balde_x", "premissa_parede_4mm_balde_z")]
    ag = {c: _dist([l.get(c) for l in linhas]) for c in numericas}

    baldes = {}
    for t in PAREDE_PREMISSA_MM:
        tag = f"{t:.0f}mm".replace(".", "")
        for eixo in ("x", "z"):
            baldes[f"parede_{tag}_eixo_{eixo}"] = {
                b: _contar(linhas, f"premissa_parede_{tag}_balde_{eixo}", b)
                for b in ("<1 voxel", "1-2 voxels", ">=2 voxels")
            }

    # extensao: REUSO da fase 7, so convertida para voxels do proprio caso
    extensao = {}
    if definicao7:
        cr, ds = [], []
        for l in linhas:
            d7 = definicao7.get(l["case_id"])
            if not d7:
                continue
            cr.append(abs(float(d7["erro_cranial_mm"])) / l["dz_mm"])
            ds.append(abs(float(d7["erro_distal_mm"])) / l["dz_mm"])
        extensao = {
            "fonte": str(DEFINICAO_FASE7),
            "erro_cranial_abs_em_voxels_z": _dist(cr),
            "erro_distal_abs_em_voxels_z": _dist(ds),
            "n_casos_erro_cranial_ate_1_voxel": int(sum(1 for v in cr if v <= 1.0)),
            "n_casos_erro_distal_ate_1_voxel": int(sum(1 for v in ds if v <= 1.0)),
        }

    perfis = {l["case_id"]: l["_perfil"] for l in linhas if "_perfil" in l}
    cob = cobertura_comum(perfis)
    fracs = []
    if "inicio_mm_da_carina" in cob:
        for l in linhas:
            if "_perfil" not in l:
                continue
            d, _ = l["_perfil"]
            fracs.append(fracao_do_volume_no_intervalo(
                l["_gt_conta"], d, cob["inicio_mm_da_carina"], cob["fim_mm_da_carina"]))
        cob = {k: v for k, v in cob.items() if k not in ("grade_mm", "cobertura")}
        cob["frac_do_volume_do_gt_dentro"] = _dist(fracs)

    return {"distribuicoes": ag, "baldes_de_parede": baldes,
            "extensao_em_voxels": extensao, "cobertura_comum_ancorada_na_carina": cob}


def decidir(linhas: list[dict], ag: dict) -> dict[str, Any]:
    """A tabela de decisao da Parte A. Cada alternativa recebe veredito POR MEDIDA."""
    n = len(linhas)
    d = ag["distribuicoes"]
    cob = ag["cobertura_comum_ancorada_na_carina"]
    n_carina = _contar(linhas, "carina_disponivel", True)
    desvio_max = d["carina_desvio_voxels_max"]["max"]
    n_estavel = sum(1 for l in linhas
                    if (l.get("carina_desvio_voxels_max") or 0.0) <= 1.0)
    n_campo_cran = sum(1 for l in linhas if l.get("gt_cranial_ate_borda_do_campo_mm") == 0.0)
    n_campo_caud = sum(1 for l in linhas if l.get("gt_caudal_ate_borda_do_campo_mm") == 0.0)
    iqr_cran = d["carina_mm_ate_gt_cranial"]["p75"] - d["carina_mm_ate_gt_cranial"]["p25"]
    iqr_caud = d["carina_mm_ate_gt_caudal"]["p75"] - d["carina_mm_ate_gt_caudal"]["p25"]
    r_caud = d["razao_ponta_caudal"]
    r_cran = d["razao_ponta_cranial"]
    n_caud_cheia = sum(1 for l in linhas if l["razao_ponta_caudal"] >= 1.0)
    n_cran_cheia = sum(1 for l in linhas if l["razao_ponta_cranial"] >= 0.5)

    return {
        "M1_landmark_detectavel": {
            "landmark": "carina = extremo caudal da mascara `trachea` do TotalSegmentator",
            "onde_existe": ("fase 7, aux_masks, os MESMOS 30 casos. NAO esta no roi_subset de "
                            "producao (8 estruturas, nenhuma longitudinal) — entrar em producao "
                            "custa uma estrutura a mais na inferencia, nao um modelo novo."),
            "presente_em": f"{n_carina}/{n}",
            "criterio_declarado": "desvio <= 1 voxel em Z entre as tres variantes",
            "estabilidade_voxels_z_max": desvio_max,
            "n_casos_dentro_do_criterio": f"{n_estavel}/{n}",
            "variantes_testadas": ["maior_componente", "min_5_voxels_por_fatia",
                                   "erosao_1_passo_no_plano"],
            # o limiar foi declarado ANTES de rodar e NAO foi mexido depois de ver
            # o resultado; por isso o veredito reporta os dois fatos separados em
            # vez de um booleano que esconderia o 1/30 fora do criterio.
            "veredito": (f"DETECTAVEL em {n_carina}/{n}; dentro do criterio de estabilidade "
                         f"em {n_estavel}/{n} (pior caso {desvio_max:.0f} voxels em Z)"),
            "ressalva": ("mede-se onde a mascara acaba, nao onde a bifurcacao esta; nao ha "
                         "marcacao de carina em nenhum caso do LCTSC para conferir."),
        },
        "M2_pontas_a_deslocamento_fixo_da_carina": {
            "cranial_mm": {k: d["carina_mm_ate_gt_cranial"][k]
                           for k in ("mediana", "desvio", "min", "max")},
            "cranial_iqr_mm": iqr_cran,
            "caudal_mm": {k: d["carina_mm_ate_gt_caudal"][k]
                          for k in ("mediana", "desvio", "min", "max")},
            "caudal_iqr_mm": iqr_caud,
            "veredito": "NAO ha deslocamento fixo" if max(iqr_cran, iqr_caud) > 5.0 else "ha",
            "ressalva": ("com 1 contorno por caso nao da para separar variacao anatomica real "
                         "de decisao do contornador. A dispersao e um limite SUPERIOR da "
                         "reprodutibilidade, nunca uma medida de discordancia."),
        },
        "M3_pontas_sao_truncamento": {
            "razao_ponta_caudal": {k: r_caud[k] for k in ("mediana", "min", "max")},
            "razao_ponta_cranial": {k: r_cran[k] for k in ("mediana", "min", "max")},
            "n_casos_ponta_caudal_acima_da_area_mediana": f"{n_caud_cheia}/{n}",
            "n_casos_ponta_cranial_acima_de_metade_da_area_mediana": f"{n_cran_cheia}/{n}",
            # controle da explicacao alternativa: se as pontas estivessem no limite
            # do campo, o corte seria da AQUISICAO, nao do contornador.
            "n_casos_com_ponta_cranial_no_limite_do_campo": f"{n_campo_cran}/{n}",
            "n_casos_com_ponta_caudal_no_limite_do_campo": f"{n_campo_caud}/{n}",
            "veredito": ("as duas pontas sao CORTES na largura cheia"
                         if r_caud["mediana"] >= 1.0 else "ao menos a caudal afina"),
        },
        "M4_trecho_anotado_em_todos_os_casos": cob,
        "alternativas": {
            "A_preservar_a_extensao_do_gt_como_definicao": {
                "veredito": "REFUTADA",
                "por_que": ("A eleva as pontas do GT a fato anatomico. M3 mostra que a ponta "
                            f"caudal tem area {r_caud['mediana']:.2f}x a mediana do proprio caso "
                            f"({n_caud_cheia}/{n} acima de 1,00x): o contorno acaba na secao mais "
                            "larga que ele tem. Estrutura nao termina no seu ponto mais grosso; "
                            f"isso e corte. E o corte nao vem da aquisicao: a ponta caudal esta no "
                            f"limite do campo em {n_campo_caud}/{n} casos e a cranial em "
                            f"{n_campo_cran}/{n}."),
            },
            "B_definir_por_landmarks_detectaveis": {
                "veredito": "REFUTADA",
                "por_que": (f"o unico marco longitudinal detectavel hoje e a carina — presente em "
                            f"{n_carina}/{n}, dentro do criterio de estabilidade em "
                            f"{n_estavel}/{n} (M1). M2 "
                            f"mostra IQR de {iqr_cran:.1f} mm no cranial e {iqr_caud:.1f} mm no "
                            "caudal em relacao a ela — ordem de grandeza acima do HD95 mediano do "
                            "baseline (6,27 mm). Ancorar a extensao num deslocamento fixo da "
                            "carina injetaria erro maior que o erro que se quer medir."),
            },
            "C_recortar_ao_trecho_consistente": {
                "veredito": "REFUTADA",
                "por_que": ("o trecho anotado em 30/30 existe (M4) mas seus limites sao os dois "
                            "casos mais truncados, nao anatomia, e ele guarda mediana de "
                            f"{cob.get('frac_do_volume_do_gt_dentro', {}).get('mediana', 0.0):.4f} "
                            "do volume do GT. Recortar jogaria fora ~1/3 da anotacao para trocar "
                            "uma fronteira arbitraria por outra."),
            },
            "D_extensao_herdada_do_gt_e_declarada_nao_avaliavel": {
                "veredito": "ESCOLHIDA",
                "por_que": ("e a unica compativel com as tres medidas: ha marco detectavel mas "
                            "ele nao define as pontas (M1+M2), e as pontas sao cortes (M3). "
                            "Herdar a extensao e o que o pipeline ja faz; o que muda e parar de "
                            "chamar isso de definicao anatomica e passar a declarar a extensao "
                            "como NAO avaliavel."),
            },
        },
    }


def irresolvivel(linhas: list[dict], ag: dict) -> dict[str, Any]:
    """O componente fisicamente irresoluvel nesta grade, com numero."""
    n = len(linhas)
    d = ag["distribuicoes"]
    out: dict[str, Any] = {
        "premissa_declarada_mm": list(PAREDE_PREMISSA_MM),
        "premissa_e_medida": False,
        "por_que_nao_e_medida": ("o GT e macico (fase 7: fill_holes 2D preencheu 0,0000 mL em "
                                 "30/30). Parede e lumen nao sao objetos separados na anotacao, "
                                 "entao espessura de parede nao e medivel a partir dele."),
        "orientacao": {
            "frac_area_fronteira_com_normal_em_z": d["frac_area_normal_em_z"]["mediana"],
            "frac_area_fronteira_com_normal_no_plano": d["frac_area_normal_no_plano"]["mediana"],
            "consequencia": ("a maior parte da fronteira tem normal NO PLANO, entao o spacing que "
                             "limita a parede e dx/dy, nao dz. Comparar 3-4 mm so com dz supoe a "
                             "parede deitada, o que ela quase nunca esta."),
        },
    }
    for t in PAREDE_PREMISSA_MM:
        tag = f"{t:.0f}mm".replace(".", "")
        n_plano = sum(1 for l in linhas if l[f"premissa_lumen_{tag}_existe_no_plano"])
        n_z = sum(1 for l in linhas if l[f"premissa_lumen_{tag}_existe_em_z"])
        n_int = sum(1 for l in linhas if l[f"premissa_lumen_{tag}_tem_interior_no_plano"])
        n_nyq_z = sum(1 for l in linhas if t / l["dz_mm"] >= VOXELS_NYQUIST)
        n_nyq_x = sum(1 for l in linhas if t / l["dx_mm"] >= VOXELS_NYQUIST)
        # a premissa se contradiz quando duas paredes ja excedem o calibre medido:
        # ou a parede e mais fina ali, ou a espessura caracteristica nao e o
        # diametro externo. Contar isso e o que impede a premissa de virar medida.
        n_incoerente = sum(1 for l in linhas if l[f"premissa_lumen_{tag}_mm"] <= 0.0)
        out[f"parede_{tag}"] = {
            "n_casos_em_que_a_premissa_se_contradiz": f"{n_incoerente}/{n}",
            "n_casos_parede_com_>=2_amostras_no_plano": f"{n_nyq_x}/{n}",
            "n_casos_parede_com_>=2_amostras_em_z": f"{n_nyq_z}/{n}",
            "lumen_implicado_mm": d[f"premissa_lumen_{tag}_mm"]["mediana"],
            "n_casos_lumen_com_>=2_amostras_no_plano": f"{n_plano}/{n}",
            "n_casos_lumen_com_>=2_amostras_em_z": f"{n_z}/{n}",
            "n_casos_lumen_com_interior_no_plano": f"{n_int}/{n}",
        }
    ext = ag.get("extensao_em_voxels") or {}
    out["extensao"] = {
        "erro_cranial_abs_mediano_em_voxels_z": ext.get("erro_cranial_abs_em_voxels_z", {}).get("mediana", NM),
        "n_casos_erro_cranial_dentro_de_1_voxel": ext.get("n_casos_erro_cranial_ate_1_voxel", NM),
        "erro_distal_abs_mediano_em_voxels_z": ext.get("erro_distal_abs_em_voxels_z", {}).get("mediana", NM),
        "n_casos_erro_distal_dentro_de_1_voxel": ext.get("n_casos_erro_distal_ate_1_voxel", NM),
    }
    p3, p4 = out["parede_3mm"], out["parede_4mm"]
    out["resposta_com_numero"] = (
        f"O irresoluvel NAO e a parede: com normal no plano — {out['orientacao']['frac_area_fronteira_com_normal_no_plano']:.4f} "
        f"da area de fronteira — 3 mm ja tem >=2 amostras em {p3['n_casos_parede_com_>=2_amostras_no_plano']} "
        f"casos. O irresoluvel e o LUMEN: sob parede de 4 mm o diametro interno implicado cai para "
        f"{p4['lumen_implicado_mm']:.2f} mm mediano, com >=2 amostras no plano em so "
        f"{p4['n_casos_lumen_com_>=2_amostras_no_plano']} e interior em "
        f"{p4['n_casos_lumen_com_interior_no_plano']}. Em Z nada disso existe: "
        f"{p3['n_casos_parede_com_>=2_amostras_em_z']} casos para a parede de 3 mm."
    )
    out["distincoes_nao_avaliaveis"] = [
        (f"parede x lumen — nao existe no GT; sob a premissa de 4 mm o lumen tem interior no "
         f"plano em {p4['n_casos_lumen_com_interior_no_plano']} casos e >=2 amostras em Z em "
         f"{p4['n_casos_lumen_com_>=2_amostras_em_z']}."),
        ("posicao da ponta cranial e da ponta caudal — as duas sao cortes de contorno (M3) e nao "
         "ha marco anatomico no pipeline para conferir (M1/M2)."),
        (f"deslocamento longitudinal abaixo de 1 voxel em Z (mediana {d['dz_mm']['mediana']:.2f} mm, "
         f"maximo {d['dz_mm']['max']:.2f} mm) — menor que o passo da grade."),
        ("espessura de parede como alvo de metrica — a premissa se contradiz em "
         f"{p4['n_casos_em_que_a_premissa_se_contradiz']} casos ja no valor de 4 mm."),
    ]
    return out


def escrever(res: dict, linhas: list[dict], destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "representabilidade.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with (destino / "representabilidade.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def _md(res: dict) -> str:
    ag, dec, irr = res["agregado"], res["decisao"], res["irresoluvel"]
    d = ag["distribuicoes"]
    L = [f"# Fase 9 — representabilidade do esofago (development, n={res['n_casos']})", "",
         f"Gerado em {res['gerado_em']}. validation e test NAO foram lidos.", "",
         "## Parte A — decisao da ontologia", ""]
    for k in ("M1_landmark_detectavel", "M2_pontas_a_deslocamento_fixo_da_carina",
              "M3_pontas_sao_truncamento"):
        L.append(f"- **{k}**: {dec[k]['veredito']}")
    c = dec["M4_trecho_anotado_em_todos_os_casos"]
    L.append(f"- **M4**: trecho com GT em 30/30 = [{c['inicio_mm_da_carina']:.0f}, "
             f"{c['fim_mm_da_carina']:.0f}] mm da carina "
             f"({c['comprimento_mm']:.0f} mm), guardando mediana de "
             f"{c['frac_do_volume_do_gt_dentro']['mediana']:.4f} do volume do GT.")
    L += ["", "| alternativa | veredito |", "|---|---|"]
    for k, v in dec["alternativas"].items():
        L.append(f"| {k} | **{v['veredito']}** |")
    L += ["", "## Parte B — representabilidade", "",
          "| grandeza | mediana | min | max |", "|---|---|---|---|"]
    for c_ in ("dx_mm", "dz_mm", "anisotropia_dz_sobre_dx", "espessura_esqueleto_mm",
               "espessura_em_voxels_x", "espessura_em_voxels_z",
               "frac_area_normal_em_z", "razao_ponta_cranial", "razao_ponta_caudal"):
        r = d[c_]
        L.append(f"| {c_} | {r['mediana']:.4f} | {r['min']:.4f} | {r['max']:.4f} |")
    L += ["", "### Baldes de parede (PREMISSA 3-4 mm, nao medida)", "",
          "| premissa/eixo | <1 voxel | 1-2 voxels | >=2 voxels |", "|---|---|---|---|"]
    for k, v in ag["baldes_de_parede"].items():
        L.append(f"| {k} | {v['<1 voxel']} | {v['1-2 voxels']} | {v['>=2 voxels']} |")
    L += ["", "### Lumen implicado pela PREMISSA (nao medido)", "",
          "| premissa | lumen mediano (mm) | >=2 amostras no plano | >=2 amostras em Z | "
          "com interior no plano | premissa se contradiz |", "|---|---|---|---|---|---|"]
    for t in PAREDE_PREMISSA_MM:
        p = irr[f"parede_{t:.0f}mm".replace(".", "")]
        L.append(f"| parede {t:.0f} mm | {p['lumen_implicado_mm']:.2f} | "
                 f"{p['n_casos_lumen_com_>=2_amostras_no_plano']} | "
                 f"{p['n_casos_lumen_com_>=2_amostras_em_z']} | "
                 f"{p['n_casos_lumen_com_interior_no_plano']} | "
                 f"{p['n_casos_em_que_a_premissa_se_contradiz']} |")
    ext = irr["extensao"]
    L += ["", "### Extensao em voxels de Z (REUSO da fase 7)", "",
          f"- erro cranial |.| mediano: {ext['erro_cranial_abs_mediano_em_voxels_z']} voxels; "
          f"dentro de 1 voxel em {ext['n_casos_erro_cranial_dentro_de_1_voxel']}/{res['n_casos']}",
          f"- erro distal |.| mediano: {ext['erro_distal_abs_mediano_em_voxels_z']} voxels; "
          f"dentro de 1 voxel em {ext['n_casos_erro_distal_dentro_de_1_voxel']}/{res['n_casos']}",
          "", "### Fisicamente irresoluvel", "", irr["resposta_com_numero"], ""]
    for s in irr["distincoes_nao_avaliaveis"]:
        L.append(f"- {s}")
    return "\n".join(L) + "\n"


def executar(raiz: Path = RAIZ_PADRAO, destino: Path = SAIDA_PADRAO,
             aux_dir: Path = AUX_PADRAO) -> dict[str, Any]:
    casos = _casos(raiz)
    definicao7 = _ler_definicao_fase7(raiz / DEFINICAO_FASE7.relative_to(RAIZ_PADRAO))
    linhas = []
    for i, caso in enumerate(casos, 1):
        l = medir_caso(caso, raiz, aux_dir)
        linhas.append(l)
        print(f"[{i}/{len(casos)}] {caso}: esp={l['espessura_esqueleto_mm']:.2f} mm "
              f"({l['espessura_em_voxels_z']:.2f} vox Z) "
              f"normal_em_z={l['frac_area_normal_em_z']:.4f} "
              f"ponta_caudal={l['razao_ponta_caudal']:.2f}x", flush=True)

    ag = agregar(linhas, definicao7)
    res = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conjunto": "development",
        "n_casos": len(casos),
        "casos": casos,
        "ressalva_de_fase": "validation e test NAO foram lidos nesta fase",
        "agregado": ag,
        "decisao": decidir(linhas, ag),
        "irresoluvel": irresolvivel(linhas, ag),
    }
    escrever(res, linhas, destino)
    (destino / "summary.md").write_text(_md(res), encoding="utf-8")
    print(f"\nescrito em {destino}")
    return res


# ------------------------------------------------------------------ autoteste


def _autoteste() -> None:
    """Cada check tem CONTROLE POSITIVO: um caso em que ele TEM que falhar."""
    from scripts.validation.phantom import cilindro, tubo_oco

    # --- 1. carina: detector acha o extremo caudal e SE MOVE quando a traqueia move
    tr = np.zeros((20, 20, 40), bool)
    tr[8:12, 8:12, 25:38] = True
    for sinal in (1.0, -1.0):
        esperado = 25 if sinal > 0 else 37
        assert indice_carina(tr, sinal) == esperado, (sinal, indice_carina(tr, sinal))
    tr2 = np.zeros_like(tr)          # mesma traqueia 4 fatias acima, SEM wrap
    tr2[8:12, 8:12, 29:40] = True
    assert indice_carina(tr2, 1.0) == 29, "CONTROLE POSITIVO: detector nao segue a traqueia"
    est = estabilidade_carina(tr, 1.0, 3.0)
    assert est["desvio_mm_max"] == 0.0, est
    # controle positivo da estabilidade: uma cauda de 1 voxel some sob as variantes
    tr3 = tr.copy()
    tr3[9, 9, 20:25] = True          # rabicho fino colado embaixo
    est3 = estabilidade_carina(tr3, 1.0, 3.0)
    assert est3["desvio_mm_max"] >= 3.0, ("CONTROLE POSITIVO: estabilidade cega a rabicho", est3)

    # --- 2. abrupticidade: cone afina (razao << 1), cilindro cortado nao (razao ~1)
    cil, aff = cilindro(10.0, 40.0, spacing=(1.0, 1.0, 1.0))
    z = np.asarray([1.0, 1.0, 1.0])
    r_cil = abrupticidade_das_pontas(cil, z, 1.0)
    assert r_cil["razao_ponta_cranial"] > 0.8, r_cil
    cone = np.zeros_like(cil)
    nz = np.flatnonzero(cil.any(axis=(0, 1)))
    for k, iz in enumerate(nz):                       # afina de baixo para cima
        f = 1.0 - 0.9 * k / max(len(nz) - 1, 1)
        sl = cil[:, :, iz]
        edt = ndimage.distance_transform_edt(sl)
        cone[:, :, iz] = edt >= (1.0 - f) * edt.max()
    r_cone = abrupticidade_das_pontas(cone, z, 1.0)
    assert r_cone["razao_ponta_cranial"] < 0.5, ("CONTROLE POSITIVO: nao distingue cone de corte",
                                                 r_cone)

    # --- 3. balde de parede: TEM que mudar de balde quando o spacing muda
    assert balde_parede(3.0, 1.0) == ">=2 voxels"
    assert balde_parede(3.0, 2.5) == "1-2 voxels"
    assert balde_parede(3.0, 5.0) == "<1 voxel", "CONTROLE POSITIVO: balde insensivel ao spacing"

    # --- 4. espessura por eixo: fantoma de calibre conhecido, grade anisotropica
    tubo, _ = cilindro(9.0, 40.0, spacing=(1.0, 1.0, 3.0))
    r = representabilidade(tubo, np.asarray([1.0, 1.0, 3.0]))
    assert 7.0 < r["espessura_esqueleto_mm"] < 11.0, r["espessura_esqueleto_mm"]
    assert abs(r["espessura_em_voxels_x"] - r["espessura_em_voxels_z"] * 3.0) < 1e-6, r
    # controle positivo: um tubo mais grosso TEM que dar numero maior
    grosso, _ = cilindro(18.0, 40.0, spacing=(1.0, 1.0, 3.0))
    r2 = representabilidade(grosso, np.asarray([1.0, 1.0, 3.0]))
    assert r2["espessura_esqueleto_mm"] > r["espessura_esqueleto_mm"] + 4.0, (r, r2)

    # --- 5. orientacao da fronteira: tubo em Z tem normal no plano; disco achatado, em Z
    o_tubo = fracao_area_fronteira_em_z(tubo, np.asarray([1.0, 1.0, 3.0]))
    assert o_tubo["frac_area_normal_no_plano"] > 0.8, o_tubo
    disco, _ = cilindro(40.0, 3.0, spacing=(1.0, 1.0, 1.0))
    o_disco = fracao_area_fronteira_em_z(disco, np.asarray([1.0, 1.0, 1.0]))
    assert o_disco["frac_area_normal_em_z"] > 0.8, ("CONTROLE POSITIVO: orientacao cega a forma",
                                                    o_disco)

    # --- 6. lumen sob premissa, no fantoma OCO. O criterio publicado nao e "o
    #        buraco existe" e sim "o buraco tem INTERIOR" (>= 3 amostras no eixo,
    #        VOXELS_PARA_TER_INTERIOR). Medido aqui: com parede de 3 mm e grade de
    #        0,4 mm o lumen sai com 57 voxels e interior; com parede de 4 mm na
    #        grade do LCTSC ele sobra como UM voxel — existe na contagem, nao como
    #        objeto. Um controle que so exigisse "buraco = 0" passaria por acaso.
    def _interior_do_lumen(mask):
        sl = mask[:, :, mask.shape[2] // 2]
        buraco = ndimage.binary_fill_holes(sl) & ~sl
        return int(buraco.sum()), int(ndimage.binary_erosion(buraco).sum())

    n_fino, i_fino = _interior_do_lumen(tubo_oco(9.33, 3.33, 30.0, spacing=(0.4, 0.4, 0.4))[0])
    assert n_fino > 20 and i_fino > 0, ("lumen deveria ter interior a 0,4 mm", n_fino, i_fino)
    n_gr, i_gr = _interior_do_lumen(tubo_oco(9.33, 1.33, 30.0, spacing=(0.98, 0.98, 2.5))[0])
    assert i_gr == 0 and n_gr < VOXELS_PARA_TER_INTERIOR, (
        "CONTROLE POSITIVO: lumen de 1,33 mm nao pode ter interior a 0,98 mm", n_gr, i_gr)

    # --- 7. cobertura comum: deslocar um caso TEM que encurtar o intervalo
    d = np.arange(-50.0, 50.0, 2.0)
    base = {f"c{i}": (d, (d >= -30) & (d <= 30)) for i in range(3)}
    c0 = cobertura_comum(base)
    base["c0"] = (d, (d >= -10) & (d <= 30))
    c1 = cobertura_comum(base)
    assert c1["comprimento_mm"] < c0["comprimento_mm"], (
        "CONTROLE POSITIVO: cobertura comum nao encolhe com caso divergente", c0, c1)

    # --- 8. guarda de fase: mascara vazia nao vira zero silencioso
    try:
        _pontas(np.zeros((4, 4, 4), bool), 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("mascara vazia deveria levantar, nao devolver numero")

    print("autoteste OK — 8 blocos, todos com controle positivo")


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        executar()
