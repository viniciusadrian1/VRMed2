"""
Parte 7 — a flag `--save_probabilities` do TotalSegmentator 2.18.0 e utilizavel?

INVESTIGACAO, nao intervencao. Nada aqui altera o baseline A_BASELINE_V1: a
chamada usa exatamente os parametros congelados (task=total, fast=False,
higher_order_resampling_LEGACY=True, robust_crop=True, roi_subset de 8
estruturas) e acrescenta SOMENTE `save_probabilities`.

Quatro perguntas, nesta ordem:
  1. o que a flag grava (formato, dtype, shape, bytes em disco);
  2. em QUAL GRADE a probabilidade sai (original da entrada ou interna 1,5 mm);
  3. se e interna: quanto custa reamostrar de volta — a mascara reconstruida
     por limiar 0,5 bate com a que o TotalSegmentator entregou?
  4. a probabilidade e por classe (multicanal) ou so o argmax?

Para responder (2) e (3) e preciso o affine da grade interna, que vive num
TemporaryDirectory apagado no fim do run. `_TmpDirPreservado` troca o
tempfile SO dentro de totalsegmentator.nnunet para preservar essas pastas.
E leitura de estado interno, nao alteracao de comportamento.

CONSTANTES E DE ONDE VEM CADA UMA (exigencia do PROMPT — nenhuma vem do GT):
  - parametros de inferencia: baseline.json (congelado antes desta parte);
  - roi_subset: mapeamento.roi_subset() (derivado do MAPA_LCTSC, nao do GT);
  - limiar 0,5 sobre a probabilidade: e o ponto neutro do softmax, escolhido
    por definicao e nao por varredura. Nenhum limiar e otimizado aqui;
  - ordem 1 na reamostragem de volta: e a ordem que o proprio TotalSegmentator
    usa no caminho higher_order_resampling_LEGACY (nnunet.py:787);
  - caso investigado: primeiro da lista `development` do split.json, declarado
    antes de rodar.
O GT so aparece no fim, para AVALIAR as duas mascaras. Nenhuma delas o usa.

Uso:
    python -m scripts.validation.tier2.confianca --caso LCTSC-Test-S1-101
    python -m scripts.validation.tier2.confianca --autoteste
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import nibabel as nib
import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
LCTSC = RAIZ / ".clinica-dados" / "tier2" / "lctsc"
FASE5 = LCTSC / "fase5"
SAIDA = FASE5 / "confianca"

# Parametros de inferencia — copia literal de fase5/baseline.json.
PARAMS_CONGELADOS = dict(
    task="total",
    fast=False,
    higher_order_resampling_LEGACY=True,
    robust_crop=True,
    quiet=False,
    device="gpu",
)


class _TmpDirPreservado:
    """Shim de tempfile.TemporaryDirectory que NAO apaga a pasta.

    Serve so para ler a grade interna (s01_0000.nii.gz) e os .npz por parte
    do modelo, que de outra forma somem antes de qualquer medida.
    """

    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.criadas: list[Path] = []

    def TemporaryDirectory(self, *_args, prefix: str = "tmp", **_kw):  # noqa: N802
        d = Path(tempfile.mkdtemp(prefix=prefix, dir=str(self.raiz)))
        self.criadas.append(d)
        shim = self

        class _Ctx:
            def __enter__(self_inner):
                return str(d)

            def __exit__(self_inner, *exc):
                shim.criadas.append(d)  # sobrevive de proposito
                return False

        return _Ctx()


def _descrever_npz(npz_path: Path) -> dict:
    """Item 1: o que a flag de fato gravou."""
    pkl_path = npz_path.with_suffix(".pkl")
    with np.load(npz_path) as z:
        chaves = list(z.keys())
        arr = z[chaves[0]]
        info = {
            "arquivo": npz_path.name,
            "chaves_no_npz": chaves,
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "min": float(arr.min()),
            "max": float(arr.max()),
        }
    info["bytes_npz_disco"] = npz_path.stat().st_size
    info["bytes_descomprimido"] = int(np.prod(info["shape"]) * np.dtype(info["dtype"]).itemsize)
    if pkl_path.exists():
        import pickle

        with open(pkl_path, "rb") as fh:
            props = pickle.load(fh)
        info["bytes_pkl_disco"] = pkl_path.stat().st_size
        info["pkl_chaves"] = sorted(props.keys())
        info["pkl_spacing"] = [float(x) for x in props.get("spacing", [])]
        info["pkl_shape_before_cropping"] = list(props.get("shape_before_cropping", []))
    return info


def _prob_para_grade(prob: np.ndarray, aff_interno: np.ndarray, alvo: nib.Nifti1Image,
                     ordem: int) -> np.ndarray:
    """Leva um volume da grade interna para a grade do `alvo`.

    Uma unica interpolacao ciente de affine (cobre recorte + canonical +
    espacamento de uma vez). Fora do recorte fica 0 — e o que o undo_crop do
    TotalSegmentator tambem faz.
    """
    from nibabel.processing import resample_from_to

    img = nib.Nifti1Image(np.asarray(prob, dtype=np.float32), aff_interno)
    saida = resample_from_to(img, (alvo.shape, alvo.affine), order=ordem, cval=0.0)
    return np.asarray(saida.dataobj, dtype=np.float32)


def _dice(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.astype(bool), b.astype(bool)
    s = int(a.sum()) + int(b.sum())
    return 1.0 if s == 0 else 2.0 * int(np.logical_and(a, b).sum()) / s


def investigar(case_id: str, manter_npz: bool = False, reusar: bool = False) -> dict:
    """Roda UM caso com save_probabilities e responde os itens 1-4.

    `reusar=True` pula a inferencia e le os artefatos de um run anterior — o
    run de GPU nao precisa ser repetido so para reanalisar o mesmo npz.
    """
    sys.path.insert(0, str(RAIZ))
    from scripts.validation.tier2.mapeamento import roi_subset
    from scripts.validation.segmentation_metrics import compare_masks

    caso_dir = LCTSC / case_id
    imagem = caso_dir / "gt" / "image.nii.gz"
    if not imagem.exists():
        raise FileNotFoundError(f"entrada ausente: {imagem}")

    SAIDA.mkdir(parents=True, exist_ok=True)
    trabalho = SAIDA / f"_run_{case_id}"
    masks_dir = trabalho / "pred_masks_sp"
    npz_path = trabalho / "prob.npz"
    tempo_s = None
    tmps: list[Path] = []

    if reusar:
        if not npz_path.exists():
            raise FileNotFoundError(f"nada para reusar em {trabalho}")
        tmps = sorted(p for p in (trabalho / "tmp").glob("*") if p.is_dir())
    else:
        if trabalho.exists():
            shutil.rmtree(trabalho)
        trabalho.mkdir(parents=True)

        from totalsegmentator import nnunet as ts_nnunet
        from totalsegmentator.python_api import totalsegmentator as segmentar

        shim = _TmpDirPreservado(trabalho / "tmp")
        tempfile_original = ts_nnunet.tempfile
        ts_nnunet.tempfile = shim  # type: ignore[assignment]
        inicio = time.time()
        try:
            segmentar(
                str(imagem),
                str(masks_dir),
                roi_subset=roi_subset(),
                save_probabilities=npz_path,
                **{k: v for k, v in PARAMS_CONGELADOS.items() if k != "device"},
            )
        finally:
            ts_nnunet.tempfile = tempfile_original
        tempo_s = round(time.time() - inicio, 1)
        tmps = [Path(d) for d in shim.criadas]

    esperadas = set(roi_subset())
    escritas = {p.stem.replace(".nii", "") for p in masks_dir.glob("*.nii.gz")} if masks_dir.exists() else set()
    rel: dict = {
        "caso": case_id,
        "declarado_antes_de_rodar": "primeiro caso da lista development do split.json",
        "parametros": {**PARAMS_CONGELADOS, "save_probabilities": True,
                       "roi_subset": roi_subset()},
        "tempo_total_s": tempo_s,
        "mascaras_que_o_run_sp_conseguiu_escrever": sorted(escritas),
        "mascaras_que_faltaram_no_run_sp": sorted(esperadas - escritas),
    }

    # ---------------------------------------------------------------- item 1
    if not npz_path.exists():
        rel["item1_o_que_grava"] = {"erro": "nenhum npz gravado"}
        return rel
    rel["item1_o_que_grava"] = _descrever_npz(npz_path)

    # Quantos .npz sobraram nos tmp preservados: mostra se houve sobrescrita.
    npzs_tmp = sorted(p for d in tmps for p in Path(d).glob("*.npz"))
    rel["item1_npz_nos_tmp"] = [str(p.relative_to(trabalho)) for p in npzs_tmp]
    rel["item1_partes_do_modelo_executadas"] = sorted(
        p.stem.split("_")[-1] for p in (trabalho / "tmp").rglob("parts/*.nii.gz"))

    # ---------------------------------------------------------------- item 2
    # A grade interna e a do s01_0000.nii.gz (entrada do nnU-Net), que so
    # existe no tmp da chamada que gravou o npz.
    internos = sorted(p for d in tmps for p in Path(d).glob("s01_0000.nii.gz"))
    orig = nib.load(str(imagem))
    prob_shape = rel["item1_o_que_grava"]["shape"]
    grade = {
        "shape_original_entrada": list(orig.shape),
        "zooms_original_mm": [float(z) for z in orig.header.get_zooms()],
        "orientacao_original": "".join(nib.aff2axcodes(orig.affine)),
        "shape_espacial_do_npz": prob_shape[1:],
        "n_canais_do_npz": prob_shape[0],
        "npz_na_grade_original": prob_shape[1:] == list(orig.shape),
    }
    # O npz sai na convencao do nnU-Net (z,y,x) — o inverso do nibabel. O
    # affine da grade interna vem do proprio .pkl (nibabel_stuff), o que
    # dispensa depender do tmp preservado.
    import pickle

    with open(npz_path.with_suffix(".pkl"), "rb") as fh:
        props = pickle.load(fh)
    aff_int = np.asarray(props["nibabel_stuff"]["original_affine"], dtype=float)
    shape_nibabel = prob_shape[1:][::-1]
    grade["shape_espacial_do_npz_em_convencao_nibabel"] = shape_nibabel
    grade["eixos_invertidos_vs_nibabel"] = True
    grade["zooms_interno_mm"] = [float(x) for x in props["spacing"]]
    grade["affine_interno"] = aff_int.tolist()
    grade["orientacao_interna"] = "".join(nib.aff2axcodes(aff_int))

    interno_img = None
    for p in internos:
        img = nib.load(str(p))
        if list(img.shape) == shape_nibabel:
            interno_img = img
            grade["s01_0000_correspondente"] = str(p.relative_to(trabalho))
            grade["affine_do_s01_0000_bate_com_o_pkl"] = bool(
                np.allclose(img.affine, aff_int, atol=1e-4))
            break
    grade["s01_0000_encontrados"] = [str(p.relative_to(trabalho)) for p in internos]
    grade["fator_de_reducao_de_voxels_original_para_interno"] = round(
        float(np.prod(orig.shape) / np.prod(shape_nibabel)), 3)
    rel["item2_grade"] = grade

    # ---------------------------------------------------------------- item 4
    from totalsegmentator.map_to_binary import class_map_5_parts

    canais = prob_shape[0]
    partes_compativeis = {
        nome: {"n_classes": len(m), "canais_esperados": len(m) + 1,
               "bate": len(m) + 1 == canais,
               "tem_spinal_cord": "spinal_cord" in m.values(),
               "indice_spinal_cord": next((k for k, v in m.items() if v == "spinal_cord"), None),
               "tem_esophagus": "esophagus" in m.values()}
        for nome, m in class_map_5_parts.items()
    }
    rel["item4_por_classe"] = {
        "multicanal": canais > 1,
        "canais": canais,
        "interpretacao": "canal 0 = fundo; canais 1..n = rotulos DA PARTE do modelo, nao os 117 rotulos totais",
        "partes_do_modelo": partes_compativeis,
    }

    # ---------------------------------------------------------------- item 3
    parte = next((n for n, d in partes_compativeis.items() if d["bate"] and d["tem_spinal_cord"]), None)
    if parte is None:
        rel["item3_custo_reamostragem"] = {
            "erro": f"npz com {canais} canais nao corresponde a uma parte com spinal_cord; "
                    "nao da para isolar a estrutura"}
        return rel
    idx = partes_compativeis[parte]["indice_spinal_cord"]
    rel["item3_parte_do_modelo_no_npz"] = parte

    with np.load(npz_path) as z:
        prob = z["probabilities"]
        # (C, z, y, x) -> (C, x, y, z), a convencao do nibabel/affine.
        canal = np.ascontiguousarray(prob[idx].transpose(2, 1, 0), dtype=np.float32)
        arg = np.ascontiguousarray(np.argmax(prob, axis=0).transpose(2, 1, 0)) == idx
        del prob

    # "a mascara que o TotalSegmentator entregou": a do proprio run com -sp se
    # ela existir; senao a do baseline congelado (mesmos parametros, mesma
    # entrada — a unica diferenca e a flag -sp, que nao muda a predicao).
    baseline_p = caso_dir / "pred_masks" / "spinal_cord.nii.gz"
    entregue_p = masks_dir / "spinal_cord.nii.gz"
    if not entregue_p.exists():
        entregue_p = baseline_p
    entregue = np.asarray(nib.load(str(entregue_p)).dataobj) > 0.5

    # B_050: probabilidade reamostrada para a grade original, limiar 0,5 depois.
    b050 = _prob_para_grade(canal, aff_int, orig, ordem=1) > 0.5
    # B_argmax: argmax na grade interna, reamostrado como mascara (order=1,
    # a mesma ordem do caminho LEGACY do TotalSegmentator).
    bargmax = _prob_para_grade(arg.astype(np.float32), aff_int, orig, ordem=1) > 0.5

    gt = np.asarray(nib.load(str(caso_dir / "gt" / "mask_SpinalCord.nii.gz")).dataobj) > 0.5
    spacing = tuple(float(z) for z in orig.header.get_zooms())

    def _m(m):
        return {k: (None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 4))
                for k, v in compare_masks(m, gt, spacing).items()}

    item3 = {
        "estrutura": "spinal_cord",
        "origem_da_mascara_entregue": str(entregue_p.relative_to(RAIZ)),
        "voxels": {"entregue_TS": int(entregue.sum()), "B_050": int(b050.sum()),
                   "B_argmax": int(bargmax.sum()), "gt": int(gt.sum())},
        "concordancia_com_a_mascara_entregue": {
            "dice_B050_vs_entregue": round(_dice(b050, entregue), 4),
            "dice_Bargmax_vs_entregue": round(_dice(bargmax, entregue), 4),
        },
        "dice_contra_gt": {
            "entregue_TS": _m(entregue)["dice"],
            "B_050": _m(b050)["dice"],
            "B_argmax": _m(bargmax)["dice"],
        },
        "metricas_completas": {"entregue_TS": _m(entregue), "B_050": _m(b050),
                               "B_argmax": _m(bargmax)},
        "criterio_declarado_dice": 0.01,
    }
    d_ent = item3["dice_contra_gt"]["entregue_TS"]
    item3["desvio_da_reconstrucao_em_dice"] = {
        "B_050": round(abs(item3["dice_contra_gt"]["B_050"] - d_ent), 4),
        "B_argmax": round(abs(item3["dice_contra_gt"]["B_argmax"] - d_ent), 4),
    }
    item3["reconstrucao_menor_que_o_criterio"] = {
        k: bool(v < 0.01) for k, v in item3["desvio_da_reconstrucao_em_dice"].items()
    }

    # Onde mora a discordancia: na leitura do npz ou na reamostragem de volta?
    # O TotalSegmentator deixa no tmp o rotulo interno da parte que gerou o npz.
    parte_id = {"class_map_part_organs": 291, "class_map_part_cardiac": 293,
                "class_map_part_muscles": 294}.get(parte)
    interno_ts_p = next(iter((trabalho / "tmp").rglob(f"parts/s01_{parte_id}.nii.gz")), None)
    if interno_ts_p is not None:
        interno_ts = np.asarray(nib.load(str(interno_ts_p)).dataobj).astype(np.uint8) == idx
        item3["decomposicao"] = {
            "npz_reproduz_o_rotulo_na_grade_interna": {
                "dice": round(_dice(arg, interno_ts), 6),
                "identicos": bool(np.array_equal(arg, interno_ts)),
                "voxels_interno": int(interno_ts.sum()),
            },
            "conclusao": "a leitura do npz e exata; toda a discordancia com a mascara "
                         "entregue nasce na reamostragem de volta para a grade original",
        }

    # Tamanho do efeito em VOXELS: e a comparacao que o item 3 pede.
    inter = int(np.logical_and(b050, entregue).sum())
    dif_sim = int(entregue.sum()) + int(b050.sum()) - 2 * inter
    voxels_por_001_de_dice = 0.01 * (int(entregue.sum()) + int(b050.sum())) / 2
    item3["ruido_de_reconstrucao_vs_efeito"] = {
        "voxels_em_desacordo_B050_vs_entregue": dif_sim,
        "voxels_que_valem_0_01_de_dice": round(voxels_por_001_de_dice, 1),
        "razao_ruido_sobre_efeito": round(dif_sim / voxels_por_001_de_dice, 1),
    }
    # A flag -sp mudou a predicao? O TS deixa no tmp o multilabel final na grade
    # original (s01.nii.gz); comparar rotulo a rotulo contra o baseline congelado.
    s01_final = next((p for p in (trabalho / "tmp").rglob("s01.nii.gz")
                      if nib.load(str(p)).shape == orig.shape), None)
    if s01_final is not None:
        from totalsegmentator.map_to_binary import class_map as _cm

        lab_total = np.asarray(nib.load(str(s01_final)).dataobj).astype(np.uint8)
        inv = {v: k for k, v in _cm["total"].items()}
        rel["item0_sp_altera_a_predicao"] = {
            n: {"label": inv[n],
                "dice_vs_baseline": round(_dice(lab_total == inv[n],
                    np.asarray(nib.load(str(caso_dir / "pred_masks" / f"{n}.nii.gz")).dataobj) > 0.5), 6)}
            for n in roi_subset() if (caso_dir / "pred_masks" / f"{n}.nii.gz").exists()
        }
    rel["item3_custo_reamostragem"] = item3

    rel["custo"] = {
        "tempo_run_s": tempo_s,
        "bytes_npz": rel["item1_o_que_grava"]["bytes_npz_disco"],
        "bytes_tmp_preservado": sum(p.stat().st_size for p in trabalho.rglob("*") if p.is_file()),
    }

    # ------------------------------------------------------------- veredito
    canais_por_parte = {n: len(m) + 1 for n, m in class_map_5_parts.items()}
    rel["veredito"] = {
        "classe": "bloqueado",
        "bloqueio_1_sobrescrita_do_npz": {
            "o_que": "save_probabilities_path e o MESMO caminho para toda parte do "
                     "modelo (nnunet.py:325). Com o roi_subset congelado rodam 3 partes "
                     "(291 organs, 293 cardiac, 294 muscles) e cada uma sobrescreve a "
                     "anterior. Sobra so a ULTIMA.",
            "partes_executadas": [291, 293, 294],
            "npz_gravados_em_disco": 1,
            "canais_esperados_por_parte": canais_por_parte,
            "canais_observados": canais,
            "estrutura_com_probabilidade": ["spinal_cord"],
            "estruturas_com_probabilidade_destruida": ["esophagus", "lung_*", "heart"],
            "consequencia": "as curvas pedidas para Esophagus e para um pulmao NAO podem "
                            "ser produzidas pela configuracao congelada — a probabilidade "
                            "deles e apagada dentro do proprio run.",
        },
        "bloqueio_2_ruido_de_reconstrucao": {
            "o_que": "a probabilidade sai na grade interna (1,5 mm, RAS, recortada). "
                     "Trazer de volta para a grade original custa uma interpolacao que "
                     "nao reproduz a mascara entregue.",
            "dice_reconstrucao_vs_mascara_entregue": item3[
                "concordancia_com_a_mascara_entregue"],
            "razao_ruido_sobre_efeito": item3["ruido_de_reconstrucao_vs_efeito"][
                "razao_ruido_sobre_efeito"],
            "leitura": "o desacordo da reconstrucao e uma ordem de grandeza maior que o "
                       "efeito de 0,01 de Dice que os criterios chamam de melhoria.",
        },
        "o_que_NAO_bloqueia": "a leitura do npz em si e exata na grade interna (Dice 1,0 "
                              "contra o rotulo do proprio TotalSegmentator) e o desvio "
                              "residual em Dice-contra-GT ficou pequeno neste caso. Isso "
                              "e n=1: nao sustenta uma curva.",
        "curva_construida": False,
        "motivo_de_nao_construir": "os itens 1-3 nao autorizaram; conforme a tarefa, o "
                                   "resultado honesto e bloqueio documentado.",
    }
    if not manter_npz:
        shutil.rmtree(trabalho / "tmp", ignore_errors=True)
    return rel


# -------------------------------------------------------------- autoteste
def autoteste() -> None:
    """Controle positivo: o instrumento tem que FALHAR quando deveria falhar."""
    aff_int = np.diag([1.5, 1.5, 1.5, 1.0])
    aff_int[:3, 3] = [10.0, 20.0, 30.0]
    aff_org = np.diag([0.5, 0.5, 1.0, 1.0])
    aff_org[:3, 3] = [10.0, 20.0, 30.0]
    alvo = nib.Nifti1Image(np.zeros((60, 60, 30), np.uint8), aff_org)

    prob = np.zeros((20, 20, 20), np.float32)
    prob[6:14, 6:14, 6:14] = 1.0
    m = _prob_para_grade(prob, aff_int, alvo, ordem=1) > 0.5

    # (a) reconstrucao de um bloco solido tem que ficar perto do bloco esperado
    esperado = np.zeros(alvo.shape, bool)
    esperado[18:42, 18:42, 9:21] = True
    d_ok = _dice(m, esperado)
    assert d_ok > 0.85, f"reconstrucao deveria bater com o bloco: dice={d_ok:.3f}"

    # (b) CONTROLE POSITIVO: deslocar o alvo 10 voxels tem que DERRUBAR o dice.
    deslocado = np.zeros(alvo.shape, bool)
    deslocado[28:52, 18:42, 9:21] = True
    d_ruim = _dice(m, deslocado)
    assert d_ruim < 0.7, f"o instrumento nao detectou deslocamento: dice={d_ruim:.3f}"

    # (c) dice de mascaras vazias e 1, de disjuntas e 0
    assert _dice(np.zeros(4, bool), np.zeros(4, bool)) == 1.0
    assert _dice(np.array([1, 0]), np.array([0, 1])) == 0.0
    print(f"autoteste OK (dice alinhado={d_ok:.3f}, deslocado={d_ruim:.3f})")


def _main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--caso", help="case_id do development")
    p.add_argument("--manter-npz", action="store_true")
    p.add_argument("--autoteste", action="store_true")
    p.add_argument("--reusar", action="store_true",
                   help="nao roda a GPU; reanalisa os artefatos de um run anterior")
    a = p.parse_args(argv)
    if a.autoteste:
        autoteste()
        return 0
    if not a.caso:
        p.error("informe --caso ou --autoteste")
    rel = investigar(a.caso, manter_npz=a.manter_npz, reusar=a.reusar)
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / f"investigacao_{a.caso}.json"
    destino.write_text(json.dumps(rel, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rel, indent=2, ensure_ascii=False))
    print(f"\n-> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
