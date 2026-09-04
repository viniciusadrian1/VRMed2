"""Mapa espacial do erro de segmentacao — ONDE o FP/FN esta, que forma e que espessura tem.

Este modulo existe por causa de um erro de metodo que ja aconteceu neste
repositorio: o relatorio atribuiu o HD95 dos pulmoes a uma "discordancia no
hilo" SEM NUNCA TER LOCALIZADO o falso positivo. Quando alguem localizou,
55-60 % do FP era casca de 1 voxel encostada na superficie do GT e o maior
bloco atravessava 49 fatias / 147 mm. A explicacao estava errada; os numeros
estavam certos.

A ordem correta e   localizar -> medir -> hipotese
e NUNCA               hipotese -> procurar evidencia.

Por isso este arquivo NAO nomeia estrutura anatomica nenhuma como causa. Ele
descreve a GEOMETRIA do erro: onde esta em Z, em quantos pedacos, de que
tamanho cada pedaco, e a que distancia da superficie do GT cada voxel esta.
Causa e hipotese, sai numa secao separada e rotulada como tal.

O QUE E MEDIDO (por estrutura, para FP, para FN e para os dois juntos):
  1. Componentes conexos rotulados, com o VOLUME de cada um, ordenados por
     tamanho. "3 componentes" pode ser 1 blob e 2 voxels — a contagem sozinha
     nao diz nada.
  2. Espessura do erro. Duas escalas, de proposito:
       - `camada_vox`: distancia de chessboard (`distance_transform_cdt`) em
         NUMERO DE VOXELS ate o GT. camada 1 = voxel encostado no GT. E a
         escala certa para "casca de 1 voxel" numa grade ANISOTROPICA: em mm,
         um vizinho no plano dista 0,98 mm e um vizinho em Z dista 3,0 mm, e
         um limiar unico em mm chamaria o mesmo primeiro anel de "fino" num
         eixo e "espesso" no outro.
       - `espessura_mm`: EDT euclidiana com `sampling=spacing`, em milimetros.
         E a espessura fisica, publicada porque e ela que se compara com HD95
         e ASSD.
     Ambas sao distancia ate o VOXEL de GT mais proximo (FP) ou ate o voxel de
     fundo mais proximo (FN) — a rede de voxels, nao uma superficie
     interpolada. Declarado, nao escondido.
  3. Distribuicao em Z: volume de FP e de FN por fatia e por tercos do suporte
     do GT. Erro concentrado num terco nao tem a mesma causa que erro
     espalhado.
  4. Extensao de cada componente: bounding box em mm e numero de fatias que
     ele atravessa. Um componente que cruza quase toda a extensao craniocaudal
     NAO e uma regiao anatomica localizada.
  5. Classificacao do erro em (a) casca fina espalhada, (b) bloco localizado,
     (c) diferenca de extensao nas pontas, (d) misto — por REGRA DECLARADA no
     codigo (`classificar`), com limiares nomeados, nunca escrita a mao depois
     de olhar o resultado.

TIER: isto e diagnostico do bloco A (segmentacao) da decomposicao de erro. Nao
diz nada sobre reconstrucao, simplificacao ou compressao (B, C, D) e nao se
soma a eles. Uso educacional/experimental: "caso" e "estrutura", nunca
"paciente".

  python -m scripts.validation.tier2.mapa_erro --caso LCTSC-Train-S1-001
  python -m scripts.validation.tier2.mapa_erro --autoteste
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import distance_transform_cdt, distance_transform_edt, find_objects, label

from . import geometria, mapeamento, rtstruct as rtst

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
NA = "nao aplicavel"
NM = "nao medido"

# Ordem pedida para o relatorio. Estrutura ausente do caso e simplesmente pulada.
ORDEM_ESTRUTURAS = ("Lung_R", "Lung_L", "Heart", "SpinalCord", "Esophagus")

# Conectividade dos componentes: `structure=None` do scipy.ndimage.label = face
# (6-vizinhanca) em 3D. Mesma escolha do benchmark_tier2, para os numeros de
# "n componentes" serem comparaveis entre os dois relatorios.
CONECTIVIDADE = "face (6-vizinhanca, structure padrao do scipy.ndimage.label)"

# Margem do recorte de trabalho. O recorte e so custo: contem todo o GT e toda a
# predicao mais 2 voxels de fundo em volta, entao toda EDT/CDT calculada dentro
# dele e EXATA (o vizinho mais proximo procurado nunca cai fora).
MARGEM_RECORTE = 2

# Quantos componentes saem detalhados por (estrutura, tipo). O resto vira uma
# linha agregada — nunca e descartado do volume total.
TOP_COMPONENTES = 20

# --------------------------------------------------------------- limiares da REGRA
# Todos declarados aqui e usados so em `classificar()`. Nenhum limiar e
# escolhido depois de ver o resultado de uma estrutura.

# Fracao do volume de erro em camada <= 1 voxel para o erro ser "casca fina".
LIMIAR_CASCA_FRAC = 0.50
# Fracao do volume de erro no maior componente para o erro ser "bloco".
LIMIAR_BLOCO_FRAC = 0.50
# Fracao do volume de erro em fatias onde a outra mascara nao existe, para o
# erro ser "diferenca de extensao nas pontas".
LIMIAR_EXTENSAO_FRAC = 0.50
# Extensao em Z do maior componente, como fracao da extensao em Z do GT, para
# ele ainda contar como LOCALIZADO. Acima disso ele atravessa a estrutura e nao
# e uma regiao localizada, por maior que seja seu volume.
LIMIAR_LOCAL_Z_FRAC = 0.33

CLASSE_CASCA = "a) casca fina espalhada"
CLASSE_BLOCO = "b) bloco localizado"
CLASSE_EXTENSAO = "c) diferenca de extensao nas pontas"
CLASSE_MISTO = "d) misto — nenhum criterio isolado domina"

COLUNAS = (
    "dataset", "case_id", "structure", "gt_roi_name", "tipo",
    "volume_ml", "frac_do_volume_gt", "n_voxels",
    "n_componentes", "maior_componente_ml", "frac_maior_componente",
    "frac_camada_1vox", "frac_camada_ge_2vox",
    "espessura_mm_mediana", "espessura_mm_p95", "espessura_mm_max",
    "frac_fora_do_suporte_z", "ml_fora_do_suporte_z",
    "ml_terco_inferior", "ml_terco_medio", "ml_terco_superior",
    "fatias_com_erro", "maior_comp_n_fatias", "maior_comp_z_mm",
    "frac_z_maior_comp_sobre_gt", "maior_comp_bbox_mm",
    "classe", "regra_aplicada",
    "spacing_mm", "conectividade", "erro",
)

COLUNAS_COMPONENTES = (
    "dataset", "case_id", "structure", "tipo", "rank",
    "volume_ml", "n_voxels", "frac_do_erro",
    "bbox_mm_eixo0", "bbox_mm_eixo1", "bbox_mm_eixo2",
    "n_fatias_z", "z_min", "z_max",
    "camada_vox_mediana", "camada_vox_max",
    "espessura_mm_mediana", "espessura_mm_p95", "espessura_mm_max",
)


# --------------------------------------------------------------------- utilitarios


def _ml(n_voxels: int, voxel_mm3: float) -> float:
    return float(n_voxels) * voxel_mm3 / 1000.0


def _p(v, q: float):
    """Percentil que devolve string quando o conjunto e vazio, nunca um float plausivel."""
    a = np.asarray(v, dtype=float)
    return float(np.percentile(a, q)) if a.size else "invalido: conjunto vazio"


def _frac(num: float, den: float, motivo: str):
    return float(num) / float(den) if den > 0 else f"invalido: {motivo}"


def _rotulos_z(orientacao: str) -> tuple[str, str, str]:
    """Nomes dos tercos ao longo do eixo 2, derivados do codigo de eixo do NIfTI.

    Nao presume nada: se o eixo 2 nao for craniocaudal, os tercos saem nomeados
    por indice, e o relatorio diz isso.
    """
    eixo = orientacao[2] if len(orientacao) >= 3 else "?"
    if eixo == "S":  # indice cresce em direcao superior
        return ("inferior", "medio", "superior")
    if eixo == "I":  # indice cresce em direcao inferior
        return ("superior", "medio", "inferior")
    return ("indice_baixo", "indice_medio", "indice_alto")


def _recorte(*mascaras: np.ndarray) -> tuple[tuple[slice, ...], np.ndarray]:
    """Caixa que contem todas as mascaras + MARGEM_RECORTE voxels de fundo em volta.

    Devolve (slices, offset). A margem garante que o fundo existe em volta do
    GT, condicao para a EDT interna (profundidade do FN) ser exata no recorte.
    """
    uniao = np.zeros_like(mascaras[0], dtype=bool)
    for m in mascaras:
        uniao |= m
    if not uniao.any():
        return tuple(slice(0, s) for s in uniao.shape), np.zeros(uniao.ndim, dtype=int)
    cortes = []
    for eixo in range(uniao.ndim):
        outros = tuple(e for e in range(uniao.ndim) if e != eixo)
        idx = np.flatnonzero(uniao.any(axis=outros))
        ini = max(int(idx.min()) - MARGEM_RECORTE, 0)
        fim = min(int(idx.max()) + MARGEM_RECORTE + 1, uniao.shape[eixo])
        cortes.append(slice(ini, fim))
    return tuple(cortes), np.array([c.start for c in cortes], dtype=int)


def _suporte_z(m: np.ndarray) -> tuple[int, int, int]:
    """(z_min, z_max, n_fatias_com_voxel) no eixo 2."""
    idx = np.flatnonzero(m.any(axis=(0, 1)))
    if not idx.size:
        return (-1, -1, 0)
    return (int(idx.min()), int(idx.max()), int(idx.size))


# ------------------------------------------------------------------- componentes


def _componentes(erro: np.ndarray, camada: np.ndarray, dist_mm: np.ndarray,
                 spacing, offset: np.ndarray) -> list[dict]:
    """Componentes conexos do erro, com volume, bbox em mm e extensao em fatias.

    Ordenados por volume decrescente. Indices Z sao devolvidos na grade
    ORIGINAL (o offset do recorte e somado de volta).
    """
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    rotulos, n = label(erro)
    if n == 0:
        return []
    tamanhos = np.bincount(rotulos.ravel())[1:]
    caixas = find_objects(rotulos)
    ordem = np.argsort(tamanhos)[::-1]

    saida = []
    for rank, i in enumerate(ordem, start=1):
        cx = caixas[i]
        sel = rotulos[cx] == (i + 1)
        camadas = camada[cx][sel]
        mms = dist_mm[cx][sel]
        z0, z1 = int(cx[2].start) + int(offset[2]), int(cx[2].stop) - 1 + int(offset[2])
        saida.append({
            "rank": rank,
            "n_voxels": int(tamanhos[i]),
            "volume_ml": _ml(int(tamanhos[i]), voxel_mm3),
            "bbox_mm": [float((c.stop - c.start) * s) for c, s in zip(cx, spacing)],
            "bbox_index": [[int(c.start) + int(o), int(c.stop) - 1 + int(o)]
                           for c, o in zip(cx, offset)],
            "n_fatias_z": int(cx[2].stop - cx[2].start),
            "z_min": z0,
            "z_max": z1,
            "camada_vox_mediana": float(np.median(camadas)),
            "camada_vox_max": int(camadas.max()),
            "espessura_mm_mediana": float(np.median(mms)),
            "espessura_mm_p95": float(np.percentile(mms, 95)),
            "espessura_mm_max": float(mms.max()),
        })
    return saida


# ----------------------------------------------------------------- classificacao


def classificar(m: dict) -> tuple[str, str]:
    """REGRA declarada. Avaliada NESTA ORDEM, com os limiares do topo do modulo.

    Entrada: o dicionario de medidas de um tipo de erro (fp / fn / combinado).
    Saida: (classe, regra_aplicada) — a regra sai junto do veredito para o
    leitor poder conferir a decisao sem reexecutar nada.

      0) erro vazio                                        -> nao aplicavel
      c) frac_fora_do_suporte_z >= LIMIAR_EXTENSAO_FRAC    -> extensao nas pontas
      a) frac_camada_1vox       >= LIMIAR_CASCA_FRAC       -> casca fina espalhada
      b) frac_maior_componente  >= LIMIAR_BLOCO_FRAC
         E frac_z_maior_comp_sobre_gt <= LIMIAR_LOCAL_Z_FRAC -> bloco localizado
      d) senao                                             -> misto

    A ordem importa e e deliberada: um erro que esta onde a outra mascara nem
    existe nao e "casca" nem "bloco" — nao ha com o que ele concordar ali. E o
    criterio (b) exige as DUAS condicoes: um componente que concentra o volume
    mas atravessa a estrutura inteira em Z nao e localizado, e foi exatamente
    esse o engano do relatorio anterior.
    """
    if m["n_voxels"] == 0:
        return NA, "conjunto de erro vazio"

    fora = m["frac_fora_do_suporte_z"]
    if isinstance(fora, float) and fora >= LIMIAR_EXTENSAO_FRAC:
        return CLASSE_EXTENSAO, (
            f"frac_fora_do_suporte_z={fora:.3f} >= {LIMIAR_EXTENSAO_FRAC}")

    casca = m["frac_camada_1vox"]
    if isinstance(casca, float) and casca >= LIMIAR_CASCA_FRAC:
        return CLASSE_CASCA, f"frac_camada_1vox={casca:.3f} >= {LIMIAR_CASCA_FRAC}"

    maior = m["frac_maior_componente"]
    z_frac = m["frac_z_maior_comp_sobre_gt"]
    if (isinstance(maior, float) and maior >= LIMIAR_BLOCO_FRAC
            and isinstance(z_frac, float) and z_frac <= LIMIAR_LOCAL_Z_FRAC):
        return CLASSE_BLOCO, (
            f"frac_maior_componente={maior:.3f} >= {LIMIAR_BLOCO_FRAC} e "
            f"frac_z_maior_comp_sobre_gt={z_frac:.3f} <= {LIMIAR_LOCAL_Z_FRAC}")

    def _n(v):
        return f"{v:.3f}" if isinstance(v, float) else str(v)

    return CLASSE_MISTO, (
        f"nenhum criterio atingido: frac_fora_do_suporte_z={_n(fora)}, "
        f"frac_camada_1vox={_n(casca)}, frac_maior_componente={_n(maior)}, "
        f"frac_z_maior_comp_sobre_gt={_n(z_frac)}")


# ------------------------------------------------------------------ medida de um tipo


def _medir_tipo(erro: np.ndarray, camada: np.ndarray, dist_mm: np.ndarray,
                fatias_sem_referencia: np.ndarray, gt_z: tuple[int, int, int],
                spacing, offset: np.ndarray, volume_gt_ml: float) -> dict:
    """Todas as medidas de UM conjunto de erro (FP, FN, ou os dois juntos).

    `fatias_sem_referencia` e a mascara booleana, por fatia Z do recorte, das
    fatias em que a mascara de REFERENCIA daquele tipo nao tem voxel nenhum
    (para FP a referencia e o GT; para FN e a predicao). E ali que mora a
    "diferenca de extensao nas pontas".
    """
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))
    n_vox = int(np.count_nonzero(erro))
    vol = _ml(n_vox, voxel_mm3)

    por_fatia = np.count_nonzero(erro, axis=(0, 1))  # eixo 2 = Z
    z0_gt, z1_gt, n_fatias_gt = gt_z
    extensao_gt = (z1_gt - z0_gt + 1) if n_fatias_gt else 0

    # tercos do SUPORTE DO GT (na grade original), nao do volume inteiro
    tercos = {"inferior": 0, "medio": 0, "superior": 0}
    if extensao_gt:
        bordas = np.linspace(z0_gt, z1_gt + 1, 4)
        z_orig = np.arange(por_fatia.size) + int(offset[2])
        for nome, (a, b) in zip(("inferior", "medio", "superior"),
                                zip(bordas[:-1], bordas[1:])):
            sel = (z_orig >= a) & (z_orig < b)
            tercos[nome] = int(por_fatia[sel].sum())

    n_fora = int(por_fatia[fatias_sem_referencia].sum())

    camadas = camada[erro] if n_vox else np.array([], dtype=int)
    mms = dist_mm[erro] if n_vox else np.array([], dtype=float)
    n_casca = int(np.count_nonzero(camadas <= 1)) if n_vox else 0

    comps = _componentes(erro, camada, dist_mm, spacing, offset)
    maior = comps[0] if comps else None
    frac_z = (_frac(maior["n_fatias_z"], extensao_gt, "GT sem voxel em Z")
              if maior else "invalido: sem componente")

    m = {
        "n_voxels": n_vox,
        "volume_ml": vol,
        "frac_do_volume_gt": _frac(vol, volume_gt_ml, "GT vazio"),
        "n_componentes": len(comps),
        "conectividade": CONECTIVIDADE,
        "maior_componente_ml": maior["volume_ml"] if maior else "invalido: sem componente",
        "frac_maior_componente": (_frac(maior["n_voxels"], n_vox, "erro vazio")
                                  if maior else "invalido: sem componente"),
        "frac_camada_1vox": _frac(n_casca, n_vox, "erro vazio"),
        "frac_camada_ge_2vox": _frac(n_vox - n_casca, n_vox, "erro vazio"),
        "espessura_mm_mediana": _p(mms, 50),
        "espessura_mm_p95": _p(mms, 95),
        "espessura_mm_max": float(mms.max()) if n_vox else "invalido: erro vazio",
        "ml_fora_do_suporte_z": _ml(n_fora, voxel_mm3),
        "frac_fora_do_suporte_z": _frac(n_fora, n_vox, "erro vazio"),
        "ml_terco_inferior": _ml(tercos["inferior"], voxel_mm3),
        "ml_terco_medio": _ml(tercos["medio"], voxel_mm3),
        "ml_terco_superior": _ml(tercos["superior"], voxel_mm3),
        "fatias_com_erro": int(np.count_nonzero(por_fatia)),
        "maior_comp_n_fatias": maior["n_fatias_z"] if maior else "invalido: sem componente",
        "maior_comp_z_mm": (float(maior["bbox_mm"][2]) if maior
                            else "invalido: sem componente"),
        "maior_comp_bbox_mm": ([round(v, 3) for v in maior["bbox_mm"]] if maior
                               else "invalido: sem componente"),
        "frac_z_maior_comp_sobre_gt": frac_z,
        "ml_por_fatia_z": {int(z) + int(offset[2]): _ml(int(c), voxel_mm3)
                           for z, c in enumerate(por_fatia) if c},
        "componentes": comps[:TOP_COMPONENTES],
        "componentes_restantes": {
            "n": max(len(comps) - TOP_COMPONENTES, 0),
            "volume_ml": _ml(sum(c["n_voxels"] for c in comps[TOP_COMPONENTES:]), voxel_mm3),
        },
    }
    m["classe"], m["regra_aplicada"] = classificar(m)
    return m


def mapear(pred: np.ndarray, gt: np.ndarray, spacing) -> dict:
    """Mapa de erro de UM par (predicao, ground truth) ja alinhado e ja booleano.

    Nucleo puro: nao le arquivo, nao escreve nada. E o que o autoteste exercita.
    """
    pred = np.asarray(pred) > 0.5
    gt = np.asarray(gt) > 0.5
    spacing = tuple(float(s) for s in spacing)
    voxel_mm3 = float(np.prod(np.asarray(spacing, float)))

    cortes, offset = _recorte(pred, gt)
    p, g = pred[cortes], gt[cortes]

    fp, fn = p & ~g, g & ~p
    erro = fp | fn

    # Distancia ate a rede de voxels do GT. Fora do GT (FP): ate o voxel de GT
    # mais proximo. Dentro do GT (FN): ate o voxel de fundo mais proximo, isto
    # e, a profundidade do buraco. As duas medidas em duas escalas.
    camada_fora = distance_transform_cdt(~g, metric="chessboard").astype(np.int32)
    camada_dentro = distance_transform_cdt(g, metric="chessboard").astype(np.int32)
    mm_fora = distance_transform_edt(~g, sampling=spacing)
    mm_dentro = distance_transform_edt(g, sampling=spacing)

    camada = np.where(g, camada_dentro, camada_fora)
    dist_mm = np.where(g, mm_dentro, mm_fora)

    gt_z = _suporte_z(gt)
    pred_z = _suporte_z(pred)
    sem_gt = ~g.any(axis=(0, 1))      # fatias do recorte onde o GT nao existe
    sem_pred = ~p.any(axis=(0, 1))    # fatias do recorte onde a predicao nao existe
    volume_gt_ml = _ml(int(g.sum()), voxel_mm3)

    tipos = {
        "fp": _medir_tipo(fp, camada, dist_mm, sem_gt, gt_z, spacing, offset, volume_gt_ml),
        "fn": _medir_tipo(fn, camada, dist_mm, sem_pred, gt_z, spacing, offset, volume_gt_ml),
        "combinado": _medir_tipo(erro, camada, dist_mm, sem_gt & sem_pred, gt_z,
                                 spacing, offset, volume_gt_ml),
    }
    # No combinado, "fora do suporte" precisa somar as duas referencias, e nao a
    # intersecao delas: recalculado aqui a partir dos dois tipos.
    n_fora_comb = (tipos["fp"]["ml_fora_do_suporte_z"] + tipos["fn"]["ml_fora_do_suporte_z"])
    tipos["combinado"]["ml_fora_do_suporte_z"] = n_fora_comb
    tipos["combinado"]["frac_fora_do_suporte_z"] = _frac(
        n_fora_comb, tipos["combinado"]["volume_ml"], "erro vazio")
    # o maior componente do combinado e o maior entre FP e FN (conjuntos disjuntos)
    comps = sorted(tipos["fp"]["componentes"] + tipos["fn"]["componentes"],
                   key=lambda c: c["n_voxels"], reverse=True)
    if comps and tipos["combinado"]["n_voxels"]:
        extensao_gt = (gt_z[1] - gt_z[0] + 1) if gt_z[2] else 0
        tipos["combinado"].update(
            n_componentes=tipos["fp"]["n_componentes"] + tipos["fn"]["n_componentes"],
            maior_componente_ml=comps[0]["volume_ml"],
            frac_maior_componente=_frac(comps[0]["n_voxels"],
                                        tipos["combinado"]["n_voxels"], "erro vazio"),
            maior_comp_n_fatias=comps[0]["n_fatias_z"],
            maior_comp_z_mm=float(comps[0]["bbox_mm"][2]),
            maior_comp_bbox_mm=[round(v, 3) for v in comps[0]["bbox_mm"]],
            frac_z_maior_comp_sobre_gt=_frac(comps[0]["n_fatias_z"], extensao_gt,
                                             "GT sem voxel em Z"),
            componentes=comps[:TOP_COMPONENTES],
        )
    tipos["combinado"]["classe"], tipos["combinado"]["regra_aplicada"] = classificar(
        tipos["combinado"])

    return {
        "spacing_mm": list(spacing),
        "voxel_mm3": voxel_mm3,
        "volume_gt_ml": volume_gt_ml,
        "volume_pred_ml": _ml(int(p.sum()), voxel_mm3),
        "extensao_z_gt": {"z_min": gt_z[0], "z_max": gt_z[1], "n_fatias": gt_z[2]},
        "extensao_z_pred": {"z_min": pred_z[0], "z_max": pred_z[1], "n_fatias": pred_z[2]},
        "recorte_index": [[int(c.start), int(c.stop)] for c in cortes],
        "tipos": tipos,
    }


# ---------------------------------------------------------------------- execucao


def rodar(caso: str, raiz: Path = RAIZ_PADRAO, log=print) -> dict:
    """Mapa de erro de todas as estruturas de um caso. Aceita qualquer caso da coorte."""
    destino = Path(raiz) / caso
    manifesto = json.loads((destino / "manifesto.json").read_text(encoding="utf-8"))
    dir_gt, dir_pred = destino / "gt", destino / "pred_masks"

    rois = list(manifesto["rois_encontradas"])
    ordenadas = [r for r in ORDEM_ESTRUTURAS if r in rois] + [r for r in rois
                                                              if r not in ORDEM_ESTRUTURAS]

    resultados: dict = {}
    linhas: list[dict] = []
    linhas_comp: list[dict] = []
    orientacao = manifesto.get("orientacao", "???")

    for gt_roi in ordenadas:
        canonica = mapeamento.canonizar(gt_roi)
        if canonica is None:
            log(f"  {gt_roi}: sem mapeamento — pulada")
            continue
        alvos = mapeamento.MAPA_LCTSC[canonica]
        caminho_gt = dir_gt / f"{rtst.PREFIXO_MASCARA}{gt_roi}.nii.gz"
        caminhos_pred = [dir_pred / f"{n}.nii.gz" for n in alvos]
        structure = "+".join(alvos)

        # Parte K ANTES de qualquer medida. Grade divergente aborta a estrutura
        # com erro explicito — nunca vira "mapa de erro ruim".
        try:
            alinhamento = [geometria.verificar_alinhamento(p, caminho_gt) for p in caminhos_pred]
        except geometria.DesalinhamentoGeometrico as e:
            linha = {c: None for c in COLUNAS}
            linha.update(dataset=manifesto["dataset"], case_id=manifesto["case_id"],
                         structure=structure, gt_roi_name=gt_roi, tipo="—",
                         erro=f"ABORTADA: {e}")
            linhas.append(linha)
            resultados[gt_roi] = {"erro": f"ABORTADA: {e}"}
            log(f"  {gt_roi}: ABORTADA — {e}")
            continue

        # Spacing lido do PROPRIO arquivo de GT que entra na comparacao, e nao de
        # `gt/image.nii.gz`: assim o mm de toda distancia publicada vem de um
        # arquivo coberto pela prova de alinhamento acima.
        geo_gt = geometria.descrever_nifti(caminho_gt)
        spacing = tuple(geo_gt["zooms_mm"])

        gt = rtst.carregar_mascara(caminho_gt)
        pred, _ = mapeamento.unir_predicao(dir_pred, alvos)
        r = mapear(pred, gt, spacing)
        r.update(
            gt_roi_name=gt_roi, structure=structure,
            estruturas_totalsegmentator=list(alvos), uniao_de_lobos=len(alvos) > 1,
            orientacao=geo_gt["orientacao"],
            rotulos_terco_z=list(_rotulos_z(geo_gt["orientacao"])),
            alinhamento_veredito=[a["veredito"] for a in alinhamento],
            delta_affine_max=[a["delta_affine_max"] for a in alinhamento],
        )
        resultados[gt_roi] = r
        log(f"  {gt_roi}: FP {r['tipos']['fp']['volume_ml']:.3f} mL / "
            f"FN {r['tipos']['fn']['volume_ml']:.3f} mL -> {r['tipos']['combinado']['classe']}")

        for tipo in ("fp", "fn", "combinado"):
            m = r["tipos"][tipo]
            linha = {c: None for c in COLUNAS}
            linha.update(
                dataset=manifesto["dataset"], case_id=manifesto["case_id"],
                structure=structure, gt_roi_name=gt_roi, tipo=tipo,
                spacing_mm=[round(s, 6) for s in spacing],
                conectividade=CONECTIVIDADE, erro="",
            )
            for c in COLUNAS:
                if c in m:
                    linha[c] = m[c]
            linhas.append(linha)
            for comp in m["componentes"]:
                if tipo == "combinado":
                    continue  # componentes do combinado sao os mesmos de fp/fn
                linhas_comp.append({
                    "dataset": manifesto["dataset"], "case_id": manifesto["case_id"],
                    "structure": structure, "tipo": tipo, "rank": comp["rank"],
                    "volume_ml": comp["volume_ml"], "n_voxels": comp["n_voxels"],
                    "frac_do_erro": _frac(comp["n_voxels"], m["n_voxels"], "erro vazio"),
                    "bbox_mm_eixo0": round(comp["bbox_mm"][0], 3),
                    "bbox_mm_eixo1": round(comp["bbox_mm"][1], 3),
                    "bbox_mm_eixo2": round(comp["bbox_mm"][2], 3),
                    "n_fatias_z": comp["n_fatias_z"],
                    "z_min": comp["z_min"], "z_max": comp["z_max"],
                    "camada_vox_mediana": comp["camada_vox_mediana"],
                    "camada_vox_max": comp["camada_vox_max"],
                    "espessura_mm_mediana": comp["espessura_mm_mediana"],
                    "espessura_mm_p95": comp["espessura_mm_p95"],
                    "espessura_mm_max": comp["espessura_mm_max"],
                })

    return {"manifesto": manifesto, "caso": caso, "orientacao": orientacao,
            "resultados": resultados, "linhas": linhas, "linhas_componentes": linhas_comp}


# ------------------------------------------------------------------------ relatorio


def _f(v, casas=4) -> str:
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    if v is None:
        return "—"
    return str(v)


def _summary_md(r: dict) -> str:
    man = r["manifesto"]
    md = [
        "# Mapa espacial do erro — Tier2 (bloco A, segmentacao)",
        "",
        f"Caso `{man['case_id']}` · dataset `{man['dataset']}` · "
        f"shape {man.get('shape')} · orientacao {man.get('orientacao')}",
        "",
        "**Este documento localiza e mede o erro. Ele nao explica o erro.** Nenhuma linha "
        "abaixo nomeia estrutura anatomica como causa: o que esta medido e ONDE o erro esta, "
        "em quantos pedacos, de que tamanho e a que distancia da superficie do GT. Hipotese de "
        "causa fica na secao final, rotulada como hipotese.",
        "",
        "Tier2 quantifica apenas o bloco **A** da decomposicao de erro (A = segmentacao, "
        "B = reconstrucao, C = simplificacao, D = compressao). Os blocos nunca se somam.",
        "",
        "## Como cada numero e obtido",
        "",
        f"- Componentes conexos: `scipy.ndimage.label`, conectividade {CONECTIVIDADE}.",
        "- `camada_vox`: distancia de chessboard (`distance_transform_cdt`) em NUMERO DE "
        "VOXELS ate o GT. `camada = 1` e o voxel encostado no GT. Esta e a escala usada para "
        "\"casca de 1 voxel\" porque a grade e anisotropica — em mm, o primeiro vizinho vale "
        "0,98 mm no plano e 3,0 mm em Z, e um limiar unico em mm mediria coisas diferentes em "
        "eixos diferentes.",
        "- `espessura_mm`: EDT euclidiana (`distance_transform_edt`) com `sampling=spacing`. "
        "Espessura fisica, comparavel com HD95/ASSD.",
        "- Ambas medem distancia ate o VOXEL mais proximo (do GT, para FP; do fundo, para FN), "
        "nao ate uma superficie interpolada.",
        "- Tercos em Z: divisao do SUPORTE DO GT em tres faixas de indice iguais. Erro em "
        "fatias onde a mascara de referencia nao existe sai separado, em "
        "`ml_fora_do_suporte_z`.",
        "- Spacing lido do proprio `mask_*.nii.gz` do GT, que e um dos dois arquivos cobertos "
        "pela verificacao de alinhamento — nao de `gt/image.nii.gz`.",
        "",
        "## Regra de classificacao (declarada no codigo, avaliada nesta ordem)",
        "",
        "```",
        "0) erro vazio                                                  -> nao aplicavel",
        f"c) frac_fora_do_suporte_z    >= {LIMIAR_EXTENSAO_FRAC}"
        f"                          -> {CLASSE_EXTENSAO}",
        f"a) frac_camada_1vox          >= {LIMIAR_CASCA_FRAC}"
        f"                          -> {CLASSE_CASCA}",
        f"b) frac_maior_componente     >= {LIMIAR_BLOCO_FRAC} E",
        f"   frac_z_maior_comp_sobre_gt<= {LIMIAR_LOCAL_Z_FRAC}"
        f"                         -> {CLASSE_BLOCO}",
        f"d) senao                                                       -> {CLASSE_MISTO}",
        "```",
        "",
        "O criterio (b) exige as DUAS condicoes de proposito: um componente que concentra o "
        "volume mas atravessa a estrutura inteira em Z **nao** e uma regiao localizada.",
        "",
        "## Resumo por estrutura",
        "",
        "| estrutura | erro FP (mL) | erro FN (mL) | erro total / vol. GT | casca <=1 vox | "
        "n comp. (FP/FN) | maior comp. (mL) | fatias do maior comp. | classe |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for roi, d in r["resultados"].items():
        if "erro" in d and "tipos" not in d:
            md.append(f"| {roi} | ABORTADA | | | | | | | {d['erro']} |")
            continue
        fp, fn, cb = d["tipos"]["fp"], d["tipos"]["fn"], d["tipos"]["combinado"]
        md.append(
            f"| {roi} | {_f(fp['volume_ml'], 3)} | {_f(fn['volume_ml'], 3)} | "
            f"{_f(cb['frac_do_volume_gt'], 4)} | {_f(cb['frac_camada_1vox'], 4)} | "
            f"{fp['n_componentes']}/{fn['n_componentes']} | "
            f"{_f(cb['maior_componente_ml'], 3)} | {_f(cb['maior_comp_n_fatias'])} | "
            f"**{cb['classe']}** |")

    md += ["", "## Detalhe por estrutura", ""]
    for roi, d in r["resultados"].items():
        md.append(f"### {roi}")
        md.append("")
        if "erro" in d and "tipos" not in d:
            md += [f"**{d['erro']}** — nenhuma medida produzida.", ""]
            continue
        rot = d["rotulos_terco_z"]
        md += [
            f"Predicao = `{'` + `'.join(d['estruturas_totalsegmentator'])}`"
            f"{' (uniao de lobos)' if d['uniao_de_lobos'] else ''}. "
            f"Alinhamento: {', '.join(d['alinhamento_veredito'])} "
            f"(delta_affine_max = {d['delta_affine_max']}).",
            "",
            f"Volume GT {_f(d['volume_gt_ml'], 3)} mL · predicao {_f(d['volume_pred_ml'], 3)} mL · "
            f"spacing {d['spacing_mm']} mm · orientacao {d['orientacao']} "
            f"(tercos do eixo 2 nomeados {rot[0]}/{rot[1]}/{rot[2]}).",
            "",
            f"Extensao em Z — GT: fatias {d['extensao_z_gt']['z_min']}–"
            f"{d['extensao_z_gt']['z_max']} ({d['extensao_z_gt']['n_fatias']} fatias) · "
            f"predicao: {d['extensao_z_pred']['z_min']}–{d['extensao_z_pred']['z_max']} "
            f"({d['extensao_z_pred']['n_fatias']} fatias).",
            "",
            "| medida | FP | FN |",
            "|---|---|---|",
        ]
        fp, fn = d["tipos"]["fp"], d["tipos"]["fn"]
        campos = [
            ("volume (mL)", "volume_ml", 3),
            ("fracao do volume do GT", "frac_do_volume_gt", 4),
            ("n componentes", "n_componentes", 0),
            ("maior componente (mL)", "maior_componente_ml", 3),
            ("fracao no maior componente", "frac_maior_componente", 4),
            ("fracao em camada <= 1 voxel", "frac_camada_1vox", 4),
            ("fracao em camada >= 2 voxels", "frac_camada_ge_2vox", 4),
            ("espessura mediana (mm)", "espessura_mm_mediana", 3),
            ("espessura p95 (mm)", "espessura_mm_p95", 3),
            ("espessura maxima (mm)", "espessura_mm_max", 3),
            ("mL onde a outra mascara nao existe em Z", "ml_fora_do_suporte_z", 3),
            ("fracao onde a outra mascara nao existe em Z", "frac_fora_do_suporte_z", 4),
            (f"mL no terco {rot[0]}", "ml_terco_inferior", 3),
            (f"mL no terco {rot[1]}", "ml_terco_medio", 3),
            (f"mL no terco {rot[2]}", "ml_terco_superior", 3),
            ("fatias com erro", "fatias_com_erro", 0),
            ("fatias do maior componente", "maior_comp_n_fatias", 0),
            ("extensao Z do maior componente (mm)", "maior_comp_z_mm", 1),
            ("bbox do maior componente (mm)", "maior_comp_bbox_mm", 0),
            ("extensao Z do maior comp. / extensao Z do GT", "frac_z_maior_comp_sobre_gt", 4),
        ]
        for rotulo, chave, casas in campos:
            md.append(f"| {rotulo} | {_f(fp[chave], casas)} | {_f(fn[chave], casas)} |")
        md += [
            "",
            f"**Classe FP:** {fp['classe']} — `{fp['regra_aplicada']}`  ",
            f"**Classe FN:** {fn['classe']} — `{fn['regra_aplicada']}`  ",
            f"**Classe combinada:** {d['tipos']['combinado']['classe']} — "
            f"`{d['tipos']['combinado']['regra_aplicada']}`",
            "",
        ]
        for tipo, rotulo in (("fp", "falso positivo"), ("fn", "falso negativo")):
            comps = d["tipos"][tipo]["componentes"]
            if not comps:
                md += [f"Sem componentes de {rotulo}.", ""]
                continue
            md += [
                f"Maiores componentes de {rotulo} (ate {TOP_COMPONENTES}):",
                "",
                "| # | mL | fatias Z | z_min–z_max | bbox mm (eixo0 × eixo1 × eixo2) | "
                "camada mediana (vox) | espessura p95 (mm) |",
                "|---|---|---|---|---|---|---|",
            ]
            for c in comps:
                bb = " × ".join(f"{v:.1f}" for v in c["bbox_mm"])
                md.append(
                    f"| {c['rank']} | {c['volume_ml']:.4f} | {c['n_fatias_z']} | "
                    f"{c['z_min']}–{c['z_max']} | {bb} | {c['camada_vox_mediana']:.1f} | "
                    f"{c['espessura_mm_p95']:.3f} |")
            resto = d["tipos"][tipo]["componentes_restantes"]
            if resto["n"]:
                md.append(f"| … | {resto['volume_ml']:.4f} | | | outros {resto['n']} "
                          f"componentes somados | | |")
            md.append("")

    md += [
        "## Hipoteses de causa — NAO MEDIDO",
        "",
        "Esta secao existe para manter a separacao explicita, e esta **vazia por decisao de "
        "metodo**. Este modulo produz geometria do erro, nao causa. Nenhuma atribuicao "
        "anatomica, de aquisicao ou de protocolo de contorno e derivavel dos numeros acima: "
        "eles dizem onde o erro esta e que forma tem, nao por que ele existe.",
        "",
        "Para que uma hipotese de causa passe a ser afirmavel seria preciso, no minimo: "
        "(1) a mesma assinatura geometrica repetida na coorte inteira, e nao em n = 1; "
        "(2) uma medida independente da causa proposta, feita sobre a imagem ou sobre a "
        "especificacao do contorno, e nao sobre o proprio mapa de erro. Nada disso foi feito "
        "aqui.",
        "",
        "## Limites deste instrumento",
        "",
        "- **n = 1 caso.** Nenhuma dispersao, nenhuma generalizacao.",
        "- A classificacao e uma REGRA com limiares declarados, nao uma inferencia. Mudar "
        f"`LIMIAR_CASCA_FRAC` ({LIMIAR_CASCA_FRAC}), `LIMIAR_BLOCO_FRAC` ({LIMIAR_BLOCO_FRAC}), "
        f"`LIMIAR_EXTENSAO_FRAC` ({LIMIAR_EXTENSAO_FRAC}) ou `LIMIAR_LOCAL_Z_FRAC` "
        f"({LIMIAR_LOCAL_Z_FRAC}) muda o veredito. Os limiares foram fixados antes de rodar e "
        "sao os mesmos para todas as estruturas.",
        "- Distancias sao ate o voxel mais proximo na grade, nao ate uma superficie "
        "interpolada. Em Z, a menor distancia nao nula possivel e o proprio spacing.",
        "- \"Fora do suporte em Z\" so detecta divergencia de extensao no eixo 2. Divergencia "
        "de extensao no plano nao e separada por este criterio e cai em casca ou bloco.",
        "- Componentes usam vizinhanca de FACE. Dois blocos que se tocam so por quina saem "
        "como dois componentes.",
        "- Este mapa nao mede reconstrucao, simplificacao nem compressao (blocos B, C, D).",
        "",
    ]
    return "\n".join(md)


def gravar(r: dict, saida: Path, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    csv_p = saida / "mapa_erro.csv"
    csv_c = saida / "mapa_erro_componentes.csv"
    json_p = saida / "mapa_erro.json"
    md_p = saida / "summary_mapa_erro.md"

    with csv_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(r["linhas"])
    with csv_c.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_COMPONENTES)
        w.writeheader()
        w.writerows(r["linhas_componentes"])

    man = r["manifesto"]
    json_p.write_text(json.dumps({
        "tier": "Tier2 — mapa espacial do erro de SEGMENTACAO (bloco A)",
        "bloco_de_erro": "A (segmentacao). Nao diz nada sobre B/C/D e nao se soma a eles.",
        "n_casos": 1,
        "aviso": ("localiza e mede o erro; NAO atribui causa. Causa e hipotese e nao esta "
                  "neste arquivo."),
        "dataset": man["dataset"], "case_id": man["case_id"],
        "licenca": man.get("licenca"), "shape": man.get("shape"),
        "orientacao": man.get("orientacao"),
        "regra_de_classificacao": {
            "ordem": ["c) extensao nas pontas", "a) casca fina espalhada",
                      "b) bloco localizado", "d) misto"],
            "LIMIAR_EXTENSAO_FRAC": LIMIAR_EXTENSAO_FRAC,
            "LIMIAR_CASCA_FRAC": LIMIAR_CASCA_FRAC,
            "LIMIAR_BLOCO_FRAC": LIMIAR_BLOCO_FRAC,
            "LIMIAR_LOCAL_Z_FRAC": LIMIAR_LOCAL_Z_FRAC,
            "conectividade": CONECTIVIDADE,
            "escala_da_casca": ("camada de chessboard em NUMERO DE VOXELS "
                                "(distance_transform_cdt), nao em mm — a grade e anisotropica"),
            "escala_da_espessura_mm": "distance_transform_edt com sampling=spacing",
        },
        "hipoteses_de_causa": NM + ": este modulo nao atribui causa",
        "por_estrutura": r["resultados"],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    md_p.write_text(_summary_md(r), encoding="utf-8")
    for p in (csv_p, csv_c, json_p, md_p):
        log(f"gravado: {p}")
    return {"csv": csv_p, "csv_componentes": csv_c, "json": json_p, "md": md_p}


# -------------------------------------------------------------------------- autoteste


def _gt_sintetico() -> np.ndarray:
    """Cilindro grosseiro, assimetrico, com 31 fatias em Z."""
    g = np.zeros((60, 60, 60), dtype=bool)
    yy, xx = np.mgrid[0:60, 0:60]
    disco = ((yy - 30) ** 2 + (xx - 26) ** 2) <= 12 ** 2
    g[:, :, 10:41] = disco[:, :, None]
    return g


def _autoteste() -> None:
    """CONTROLE POSITIVO: a classificacao tem que separar dois erros de forma conhecida.

    (A) mascara deslocada de 1 voxel  -> tem que sair "casca fina espalhada".
    (B) blob adicionado longe         -> tem que sair "bloco localizado".

    Se os dois cairem na mesma classe, a regra nao serve para nada e o autoteste
    reprova dizendo isso, em vez de imprimir OK.
    """
    spacing = (0.9765625, 0.9765625, 3.0)  # anisotropico de proposito
    gt = _gt_sintetico()

    # (A) deslocamento de 1 voxel no eixo 0
    a = mapear(np.roll(gt, 1, axis=0), gt, spacing)
    ca = a["tipos"]["combinado"]
    print(f"(A) deslocada 1 voxel: classe={ca['classe']!r} "
          f"frac_camada_1vox={ca['frac_camada_1vox']:.4f} "
          f"frac_maior_componente={ca['frac_maior_componente']:.4f} "
          f"erro={ca['volume_ml']:.3f} mL  [{ca['regra_aplicada']}]")

    # (B) blob longe da estrutura, dentro do intervalo Z do GT (para o criterio
    # de extensao nao roubar o teste: o que se quer testar aqui e forma, nao ponta)
    pred_b = gt.copy()
    pred_b[5:13, 5:13, 20:25] = True
    b = mapear(pred_b, gt, spacing)
    cb = b["tipos"]["combinado"]
    print(f"(B) blob distante: classe={cb['classe']!r} "
          f"frac_camada_1vox={cb['frac_camada_1vox']:.4f} "
          f"frac_maior_componente={cb['frac_maior_componente']:.4f} "
          f"frac_z_maior_comp_sobre_gt={cb['frac_z_maior_comp_sobre_gt']:.4f} "
          f"erro={cb['volume_ml']:.3f} mL  [{cb['regra_aplicada']}]")

    falhas = []
    if ca["classe"] != CLASSE_CASCA:
        falhas.append(f"(A) deslocamento de 1 voxel saiu como {ca['classe']!r}, "
                      f"esperado {CLASSE_CASCA!r}")
    if cb["classe"] != CLASSE_BLOCO:
        falhas.append(f"(B) blob distante saiu como {cb['classe']!r}, "
                      f"esperado {CLASSE_BLOCO!r}")
    if ca["classe"] == cb["classe"]:
        falhas.append("(A) e (B) cairam na MESMA classe — a regra nao separa casca de bloco "
                      "e NAO SERVE como classificador")
    if falhas:
        raise AssertionError("CONTROLE POSITIVO REPROVADO:\n  - " + "\n  - ".join(falhas))

    # (C) sanidade da escala: numa grade anisotropica, a casca de 1 voxel
    # deslocada em Z tem espessura fisica = spacing[2], nunca 1.0 mm.
    c = mapear(np.roll(gt, 1, axis=2), gt, spacing)
    cc = c["tipos"]["fp"]
    assert abs(cc["espessura_mm_mediana"] - spacing[2]) < 1e-9, cc["espessura_mm_mediana"]
    assert cc["frac_camada_1vox"] == 1.0, cc["frac_camada_1vox"]
    print(f"(C) deslocada 1 voxel em Z: espessura_mm_mediana={cc['espessura_mm_mediana']} "
          f"(= spacing[2], NAO 1.0) e frac_camada_1vox={cc['frac_camada_1vox']}")

    # (D) identidade: erro vazio nao pode virar float plausivel
    d = mapear(gt, gt, spacing)["tipos"]["combinado"]
    assert d["volume_ml"] == 0.0 and d["classe"] == NA, d
    assert isinstance(d["frac_camada_1vox"], str), d["frac_camada_1vox"]
    print(f"(D) identidade: volume_ml=0.0, classe={d['classe']!r}, "
          f"frac_camada_1vox={d['frac_camada_1vox']!r}")

    print("mapa_erro.py: autoteste OK")


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Mapa espacial do erro de segmentacao (Tier2, bloco A). "
                    "Localiza e mede; nao atribui causa.")
    p.add_argument("--caso", default="LCTSC-Train-S1-001")
    p.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    p.add_argument("--saida", type=Path, default=None,
                   help="padrao: <raiz>/resultados/mapa_erro")
    p.add_argument("--autoteste", action="store_true")
    a = p.parse_args(argv)
    if a.autoteste:
        _autoteste()
        return 0
    r = rodar(a.caso, a.raiz)
    gravar(r, a.saida or (a.raiz / "resultados" / "mapa_erro"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
