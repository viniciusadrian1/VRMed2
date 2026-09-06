"""Fase 18 — auditoria do LyNoS contra a ESOPHAGUS_ONTOLOGY_V1 e contra o treino do baseline.

Duas perguntas independentes, medidas no MESMO artefato, que nao devem ser confundidas:

  (18.4) COMPATIBILIDADE. A mascara de esofago do LyNoS e o objeto que a
         ESOPHAGUS_ONTOLOGY_V1 congelou? (binaria, PREENCHIDA, parede+lumen juntos)
         Isso e verificavel por medicao direta e a resposta e definitiva.

  (18.2) SONDA GEOMETRICA. A imagem do LyNoS poderia estar entre as 1.559 imagens de
         treino do Dataset291 (task `total`, o que produz o esofago do baseline)?
         Isso e CONDICAO NECESSARIA, nunca suficiente. Ausencia de match e evidencia
         FRACA CONTRA; presenca e coincidencia geometrica, NAO identidade.

POR QUE A SONDA FUNCIONA SEM A TC
`dataset_fingerprint.json` do nnU-Net guarda `shapes_after_crop` dos 1.559 sujeitos de
treino, INCLUSIVE dos 420 nao atribuidos a instituicao nomeada. Se uma TC do LyNoS
estivesse la, o shape dela reamostrado a 1,5 mm isotropico teria de aparecer na lista.

A mascara NIfTI do LyNoS mora na MESMA grade da TC (mesmo shape, mesmo affine) — logo
o header da mascara basta para calcular o alvo da sonda, sem baixar 180-263 MB de TC.
Essa premissa NAO e assumida: `scripts/validation/lynos/grade_ct.py` a verifica lendo
so o cabecalho remoto da TC por Range HTTP.

CEGUEIRAS DECLARADAS DA SONDA (herdadas da Fase 16, nao corrigiveis aqui)
 - cega ao recorte in-plane: ~25 % do pool foi recortado no plano e muda de shape;
 - cega ao canal documental — inclusive a circularidade de anotacao (SegTHOR/BTCV
   semeando a primeira segmentacao do treino), que nenhuma sonda de imagem enxerga;
 - os pesos publicados sao `fold=0`: o modelo viu ~80 % das 1.559, e o arquivo que diz
   QUAIS 80 % nunca foi publicado. Logo "sem match" nao vira "fora do treino efetivo".

  python -m scripts.validation.lynos.auditoria --autoteste   # sem dados, so controles
  python -m scripts.validation.lynos.auditoria              # mede os 15 casos
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / ".clinica-dados" / "fase18" / "lynos"
SAIDA = RAIZ / "docs" / "overnight" / "phase18"

FINGERPRINT = Path(
    r"C:\Users\vinic\.totalsegmentator\nnunet\results"
    r"\Dataset291_TotalSegmentator_part1_organs_1559subj"
    r"\nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres\dataset_fingerprint.json"
)

# O nnU-Net do task `total` reamostra para 1,5 mm isotropico. Numero do proprio
# plans.json, nao escolha nossa.
ALVO_SPACING = 1.5
# Tolerancia por eixo, em voxels. Herdada da Fase 16 para que os dois resultados
# sejam comparaveis: mexer nela aqui seria mover a trave depois de ver o alvo.
TOL = 2


# ---------------------------------------------------------------- 18.4 ontologia


def medir_mascara(caminho: Path) -> dict:
    """Tudo o que a ESOPHAGUS_ONTOLOGY_V1 permite verificar num artefato de mascara."""
    img = nib.load(str(caminho))
    a = np.asanyarray(img.dataobj)
    zoom = tuple(float(v) for v in img.header.get_zooms()[:3])
    vals = np.unique(a)
    b = a > 0
    n_pos = int(b.sum())
    vox_mm3 = float(np.prod(zoom))

    per_slice = b.sum(axis=(0, 1))
    nz = np.nonzero(per_slice)[0]

    lab, n_comp = ndimage.label(b)
    tam = np.bincount(lab.ravel())[1:]

    # PREENCHIDA x ANULAR. Uma mascara so-de-parede tem o lumen como buraco em
    # praticamente toda fatia; uma preenchida tem buraco residual perto de zero.
    buracos = 0
    fatias_com_buraco = 0
    for k in nz:
        sl = b[:, :, k]
        d = int(ndimage.binary_fill_holes(sl).sum() - sl.sum())
        if d > 0:
            fatias_com_buraco += 1
            buracos += d
    f3 = ndimage.binary_fill_holes(b)

    eq = 2 * np.sqrt(per_slice[nz] * zoom[0] * zoom[1] / np.pi) if len(nz) else np.array([0.0])

    return {
        "arquivo": caminho.name,
        "shape": [int(v) for v in a.shape],
        "dtype": str(a.dtype),
        "spacing_mm": [round(v, 4) for v in zoom],
        "orientacao": "".join(nib.aff2axcodes(img.affine)),
        "valores_unicos": [float(v) for v in vals.tolist()],
        # BINARIA = no maximo DOIS valores distintos, um deles 0. NAO exige {0,1}.
        # A primeira versao exigia {0,1} e reprovava as 60 mascaras do LCTSC — que
        # usam {0,255}, a convencao de foreground DO PROPRIO PROJETO
        # (dataset_esofago.FOREGROUND = 255, herdada do dcmrtstruct2nii, lida com
        # limiar > 0.5). Ou seja: o validador do funil rejeitaria o dado que o
        # projeto ja usa. Achado ao medir o GT do split congelado, nao por revisao.
        "binaria": bool(len(vals) <= 2 and 0 in set(vals.tolist())),
        "valor_de_foreground": (float(max(vals.tolist())) if len(vals) else 0.0),
        "voxels_positivos": n_pos,
        "mascara_vazia": n_pos == 0,
        "volume_mm3": round(n_pos * vox_mm3, 1),
        "volume_ml": round(n_pos * vox_mm3 / 1000.0, 3),
        "fatias_com_alvo": int(len(nz)),
        "z_min": int(nz.min()) if len(nz) else -1,
        "z_max": int(nz.max()) if len(nz) else -1,
        "extensao_axial_mm": round((nz.max() - nz.min() + 1) * zoom[2], 1) if len(nz) else 0.0,
        "n_componentes_3d": int(n_comp),
        "maior_componente_fracao": round(float(tam.max() / tam.sum()), 4) if n_comp else 0.0,
        "fatias_com_buraco": int(fatias_com_buraco),
        "buracos_2d_voxels": int(buracos),
        "buracos_2d_pct": round(100.0 * buracos / n_pos, 4) if n_pos else 0.0,
        "buracos_3d_voxels": int(f3.sum() - n_pos),
        "buracos_3d_pct": round(100.0 * (f3.sum() - n_pos) / n_pos, 4) if n_pos else 0.0,
        "diametro_eq_mediano_mm": round(float(np.median(eq)), 2),
        "diametro_eq_p5_mm": round(float(np.percentile(eq, 5)), 2),
        "diametro_eq_p95_mm": round(float(np.percentile(eq, 95)), 2),
    }


# Limiar da decisao PREENCHIDA. Nao e arbitrario: uma mascara so-de-parede de um tubo
# de ~20 mm com parede de 3-4 mm teria o lumen inteiro como buraco — da ordem de 30-50 %
# da area por fatia. 1 % separa os dois regimes por duas ordens de grandeza.
LIMIAR_PREENCHIDA_PCT = 1.0


def classificar_ontologia(m: dict) -> dict:
    """Traduz as medidas em VEREDITO por criterio da V1. Sem reescrever a ontologia."""
    criterios = {
        "binaria": (m["binaria"], "valores unicos = " + str(m["valores_unicos"])),
        "nao_vazia": (not m["mascara_vazia"], str(m["voxels_positivos"]) + " voxels positivos"),
        "preenchida_parede_mais_lumen": (
            m["buracos_2d_pct"] < LIMIAR_PREENCHIDA_PCT,
            "buracos 2D = %.4f%% (limiar %.1f%%)" % (m["buracos_2d_pct"], LIMIAR_PREENCHIDA_PCT),
        ),
        "objeto_unico_dominante": (
            m["maior_componente_fracao"] > 0.99,
            "maior componente = %.4f do total em %d componentes"
            % (m["maior_componente_fracao"], m["n_componentes_3d"]),
        ),
        "calibre_compativel_com_esofago": (
            4.0 <= m["diametro_eq_mediano_mm"] <= 40.0,
            "diametro equivalente mediano = %.2f mm" % m["diametro_eq_mediano_mm"],
        ),
    }
    passou = all(v[0] for v in criterios.values())
    return {
        "criterios": {k: {"passou": bool(v[0]), "medida": v[1]} for k, v in criterios.items()},
        # A extensao longitudinal e HERDADA DO GT por definicao da V1 — nao e criterio
        # de aprovacao aqui, e afirmar o contrario seria regressao contra a ontologia.
        "extensao_longitudinal": onto.EXTENSAO_LONGITUDINAL,
        "ontology_compatible": "SIM" if passou else "PARCIAL",
    }


# ------------------------------------------------------------ 18.2 sonda geometrica


def shape_15(shape, spacing):
    """Shape que o nnU-Net produziria ao reamostrar esta grade para 1,5 mm isotropico.

    Mesma formula da Fase 16 (`screen_geometria.py`), aplicada agora a um header NIfTI
    em vez de a um diretorio DICOM. A ordem dos eixos segue a do fingerprint: (z, y, x).
    """
    return (
        int(round(shape[2] * spacing[2] / ALVO_SPACING)),
        int(round(shape[1] * spacing[1] / ALVO_SPACING)),
        int(round(shape[0] * spacing[0] / ALVO_SPACING)),
    )


def sondar(alvo, shapes, exatos):
    viz = [s for s in shapes if all(abs(s[i] - alvo[i]) <= TOL for i in range(3))]
    plano = [s for s in shapes if abs(s[1] - alvo[1]) <= TOL and abs(s[2] - alvo[2]) <= TOL]
    return {
        "shape_15mm": list(alvo),
        "match_exato": tuple(alvo) in exatos,
        "match_tol2": len(viz),
        "match_so_plano": len(plano),
    }


def classificar_sonda(r: dict) -> str:
    if r["match_exato"]:
        return "OVERLAP_IDENTIFICADO"
    if r["match_tol2"] > 0:
        return "INDETERMINADO"
    return "SEM_OVERLAP_DETECTADO"


def controles(shapes, exatos) -> dict:
    """Um instrumento que devolve zero precisa PROVAR que consegue enxergar.

    Positivo: uma grade fabricada para cair EXATAMENTE num shape que esta no
    fingerprint. Se a sonda nao a acusar, ela esta cega e nada abaixo vale.
    Negativo: uma grade absurda, longe de qualquer entrada. Se a sonda a acusar,
    ela acusa qualquer coisa e nada abaixo vale.
    """
    alvo_real = sorted(exatos)[len(exatos) // 2]
    # grade em 1,5 mm iso cujo shape@1.5 e o proprio alvo_real (identidade)
    pos_shape = (alvo_real[2], alvo_real[1], alvo_real[0])
    pos_spacing = (ALVO_SPACING, ALVO_SPACING, ALVO_SPACING)
    pos = sondar(shape_15(pos_shape, pos_spacing), shapes, exatos)

    neg_shape, neg_spacing = (4001, 4003, 4007), (1.0, 1.0, 1.0)
    neg = sondar(shape_15(neg_shape, neg_spacing), shapes, exatos)

    return {
        "positivo": {
            "grade": {"shape": list(pos_shape), "spacing": list(pos_spacing)},
            "esperado": "DETECTADO",
            "obtido": "DETECTADO" if pos["match_exato"] else "NAO DETECTADO",
            "passou": bool(pos["match_exato"]),
            "detalhe": pos,
        },
        "negativo": {
            "grade": {"shape": list(neg_shape), "spacing": list(neg_spacing)},
            "esperado": "NAO DETECTADO",
            "obtido": "DETECTADO" if neg["match_tol2"] else "NAO DETECTADO",
            "passou": not neg["match_tol2"],
            "detalhe": neg,
        },
    }


def calibrar(medidas, shapes, exatos, n_sorteios: int = 4000, semente: int = 20260906) -> dict:
    """Taxa nula da sonda SOB A GEOMETRIA DO PROPRIO LyNoS, por reamostragem.

    A pergunta que calibra: quantos matches uma coorte de 15 casos com estas mesmas
    marginais geometricas obteria POR ACASO? Sem esse numero, "0 de 15" nao tem escala
    — e sem escala nao da para dizer se o zero e informativo ou trivial.

    Marginais embaralhadas independentemente (produto das marginais): quebra a
    associacao real entre extensao em z e FOV no plano, que e exatamente o que a
    hipotese nula precisa destruir.
    """
    rng = np.random.default_rng(semente)
    ns = np.array([m["shape"][2] for m in medidas])
    dz = np.array([m["spacing_mm"][2] for m in medidas])
    rows = np.array([m["shape"][1] for m in medidas])
    py = np.array([m["spacing_mm"][1] for m in medidas])
    cols = np.array([m["shape"][0] for m in medidas])
    px = np.array([m["spacing_mm"][0] for m in medidas])

    hits_ex = 0
    hits_tol = 0
    for _ in range(n_sorteios):
        i, j, k = rng.integers(0, len(medidas), 3)
        alvo = (
            int(round(ns[i] * dz[i] / ALVO_SPACING)),
            int(round(rows[j] * py[j] / ALVO_SPACING)),
            int(round(cols[k] * px[k] / ALVO_SPACING)),
        )
        r = sondar(alvo, shapes, exatos)
        hits_ex += int(r["match_exato"])
        hits_tol += int(r["match_tol2"] > 0)

    p_ex = hits_ex / n_sorteios
    p_tol = hits_tol / n_sorteios
    n = len(medidas)
    return {
        "n_sorteios": n_sorteios,
        "semente": semente,
        "p_match_exato_por_caso": round(p_ex, 5),
        "p_match_tol2_por_caso": round(p_tol, 5),
        "esperado_exato_em_n": round(p_ex * n, 3),
        "esperado_tol2_em_n": round(p_tol * n, 3),
        # Poder: se um caso ESTIVESSE no treino, a sonda o veria? So o veria se o
        # recorte in-plane do nnU-Net nao tivesse mudado o shape. A Fase 16 mediu
        # esse teto em ~0,75 no pool; aqui ele entra como limite declarado, nao medido.
        "poder_por_membro_declarado": 0.75,
        "poder_origem": "Fase 16 — fracao do pool NAO recortada in-plane; nao remedido aqui",
    }


# ------------------------------------------------------------------------ autoteste


def autoteste() -> int:
    falhas = []

    # 1. shape_15 e aritmetica simples e verificavel a mao
    got = shape_15((512, 512, 100), (1.5, 1.5, 3.0))
    if got != (200, 512, 512):
        falhas.append("shape_15 identidade: esperado (200,512,512), obtido " + str(got))

    got = shape_15((256, 256, 50), (3.0, 3.0, 3.0))
    if got != (100, 512, 512):
        falhas.append("shape_15 reamostragem: esperado (100,512,512), obtido " + str(got))

    # 2. a sonda tem de achar o que esta na lista e nao achar o que nao esta
    shapes_fake = [[100, 200, 300], [400, 500, 600]]
    exatos_fake = {tuple(s) for s in shapes_fake}
    if not sondar((100, 200, 300), shapes_fake, exatos_fake)["match_exato"]:
        falhas.append("sonda nao achou entrada presente")
    if sondar((999, 999, 999), shapes_fake, exatos_fake)["match_tol2"]:
        falhas.append("sonda achou entrada ausente")
    # tolerancia: +-2 entra, +-3 nao
    if not sondar((102, 202, 302), shapes_fake, exatos_fake)["match_tol2"]:
        falhas.append("tolerancia +-2 deveria casar")
    if sondar((103, 203, 303), shapes_fake, exatos_fake)["match_tol2"]:
        falhas.append("tolerancia +-3 nao deveria casar")

    # 3. classificacao nunca pode transformar ausencia em independencia
    if classificar_sonda({"match_exato": False, "match_tol2": 0}) != "SEM_OVERLAP_DETECTADO":
        falhas.append("classificacao do zero mudou de nome")
    if classificar_sonda({"match_exato": True, "match_tol2": 1}) != "OVERLAP_IDENTIFICADO":
        falhas.append("classificacao do hit mudou de nome")

    # 4. o veredito de ontologia tem de REPROVAR uma mascara so-de-parede.
    #    Controle positivo do criterio: anel oco, lumen inteiro como buraco.
    anel = np.zeros((60, 60, 20), dtype=np.uint8)
    yy, xx = np.ogrid[:60, :60]
    d = np.sqrt((yy - 30) ** 2 + (xx - 30) ** 2)
    anel[(d >= 6) & (d <= 9)] = 1
    anel = np.repeat(anel[:, :, :1], 20, axis=2)
    tmp = Path(__file__).parent / "_autoteste_anel.nii.gz"
    nib.save(nib.Nifti1Image(anel, np.diag([1.0, 1.0, 2.0, 1.0])), str(tmp))
    try:
        v = classificar_ontologia(medir_mascara(tmp))
        if v["criterios"]["preenchida_parede_mais_lumen"]["passou"]:
            falhas.append("controle positivo do criterio PREENCHIDA falhou: "
                          "um anel oco passou como preenchido")
        if v["ontology_compatible"] == "SIM":
            falhas.append("anel oco foi declarado ONTOLOGY_COMPATIBLE=SIM")
    finally:
        tmp.unlink(missing_ok=True)

    # 5. e tem de APROVAR o mesmo anel depois de preenchido (controle negativo)
    cheio = np.zeros((60, 60, 20), dtype=np.uint8)
    cheio[d <= 9] = 1
    cheio = np.repeat(cheio[:, :, :1], 20, axis=2)
    tmp2 = Path(__file__).parent / "_autoteste_cheio.nii.gz"
    nib.save(nib.Nifti1Image(cheio, np.diag([1.0, 1.0, 2.0, 1.0])), str(tmp2))
    try:
        v2 = classificar_ontologia(medir_mascara(tmp2))
        if not v2["criterios"]["preenchida_parede_mais_lumen"]["passou"]:
            falhas.append("cilindro solido reprovou no criterio PREENCHIDA")
    finally:
        tmp2.unlink(missing_ok=True)

    # 6. CONVENCAO DE FOREGROUND: 0/255 e a do projeto (dataset_esofago.FOREGROUND)
    #    e TEM de passar. 0/1 tambem. Tres valores distintos NAO.
    import numpy as _np
    for valores, esperado, rotulo in (((0, 1), True, "0/1"),
                                      ((0, 255), True, "0/255 — convencao do projeto"),
                                      ((0, 1, 2), False, "tres rotulos"),
                                      ((0,), True, "so fundo")):
        arr = _np.zeros((8, 8, 4), dtype=_np.uint8)
        for i, v in enumerate(valores[1:], start=1):
            arr[i, i, :] = v
        t = Path(__file__).parent / "_autoteste_bin.nii.gz"
        nib.save(nib.Nifti1Image(arr, _np.eye(4)), str(t))
        try:
            got = medir_mascara(t)["binaria"]
            if got != esperado:
                falhas.append("binaria(%s) deu %s, esperado %s" % (rotulo, got, esperado))
        finally:
            t.unlink(missing_ok=True)

    # 7. a ontologia usada aqui e a congelada, nao uma copia divergente
    if onto.VERSAO != "ESOPHAGUS_ONTOLOGY_V1":
        falhas.append("ontologia importada nao e a V1: " + onto.VERSAO)

    for f in falhas:
        print("FALHA:", f)
    print("autoteste: %d verificacoes, %d falhas" % (14, len(falhas)))
    return 1 if falhas else 0


# ----------------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--dados", default=str(DADOS))
    a = ap.parse_args(argv)

    if a.autoteste:
        return autoteste()

    if autoteste() != 0:
        print("\nABORTADO: autoteste falhou. Instrumento antes de dado.")
        return 1
    print()

    dados = Path(a.dados)
    arquivos = sorted(dados.glob("pat*_labels_Esophagus.nii.gz"),
                      key=lambda p: int(p.name.split("_")[0][3:]))
    if not arquivos:
        print("sem mascaras em", dados)
        return 1

    fp = json.loads(FINGERPRINT.read_text())
    shapes = fp["shapes_after_crop"]
    exatos = {tuple(s) for s in shapes}
    print("fingerprint: %d shapes de treino, %d distintos" % (len(shapes), len(exatos)))

    ctl = controles(shapes, exatos)
    for nome, c in ctl.items():
        print("  controle %-9s esperado=%-14s obtido=%-14s %s"
              % (nome, c["esperado"], c["obtido"], "OK" if c["passou"] else "FALHOU"))
    if not all(c["passou"] for c in ctl.values()):
        print("\nABORTADO: controles da sonda falharam. NAO interpretar o LyNoS.")
        return 1
    print()

    linhas = []
    for p in arquivos:
        m = medir_mascara(p)
        v = classificar_ontologia(m)
        alvo = shape_15(m["shape"], m["spacing_mm"])
        s = sondar(alvo, shapes, exatos)
        s["classificacao"] = classificar_sonda(s)
        linhas.append({**m, **v, **s})
        print("%-32s %-9s buracos2D %6.4f%%  comp %2d  vol %7.2f mL  "
              "ext %6.1f mm  shape@1.5 %-18s %s"
              % (m["arquivo"], v["ontology_compatible"], m["buracos_2d_pct"],
                 m["n_componentes_3d"], m["volume_ml"], m["extensao_axial_mm"],
                 str(s["shape_15mm"]), s["classificacao"]))

    cal = calibrar(linhas, shapes, exatos)
    n_exato = sum(r["match_exato"] for r in linhas)
    n_tol = sum(r["match_tol2"] > 0 for r in linhas)
    compat = sum(r["ontology_compatible"] == "SIM" for r in linhas)

    print()
    print("ONTOLOGIA:  %d/%d compativeis (SIM)" % (compat, len(linhas)))
    print("SONDA:      match exato %d/%d  |  match tol+-2 %d/%d"
          % (n_exato, len(linhas), n_tol, len(linhas)))
    print("NULO:       [SUPERADO — ver lynos/calibracao.py] este nulo embaralha y e x de")
    print("            casos DIFERENTES e sai deflacionado. O correto (permutacao por")
    print("            bloco) da 0,931 esperado e p = 0,229. Use aquele, nao este.")
    print("NULO(velho):esperado por acaso  exato %.3f  tol+-2 %.3f  (%d sorteios)"
          % (cal["esperado_exato_em_n"], cal["esperado_tol2_em_n"], cal["n_sorteios"]))
    print("PODER:      %.2f por membro (limite declarado da Fase 16)"
          % cal["poder_por_membro_declarado"])

    SAIDA.mkdir(parents=True, exist_ok=True)
    doc = {
        "fase": 18,
        "ontologia": onto.VERSAO,
        "fingerprint": str(FINGERPRINT),
        "n_shapes_treino": len(shapes),
        "tolerancia_voxels": TOL,
        "spacing_alvo_mm": ALVO_SPACING,
        "controles": ctl,
        "calibracao": cal,
        "resumo": {
            "n_casos": len(linhas),
            "ontology_compatible_sim": compat,
            "match_exato": n_exato,
            "match_tol2": n_tol,
        },
        "casos": linhas,
    }
    (SAIDA / "lynos_auditoria.json").write_text(json.dumps(doc, indent=1))

    campos = ["arquivo", "shape", "spacing_mm", "orientacao", "dtype", "binaria",
              "voxels_positivos", "volume_ml", "extensao_axial_mm", "fatias_com_alvo",
              "n_componentes_3d", "maior_componente_fracao", "buracos_2d_pct",
              "buracos_3d_pct", "diametro_eq_mediano_mm", "ontology_compatible",
              "shape_15mm", "match_exato", "match_tol2", "match_so_plano",
              "classificacao"]
    with (SAIDA / "lynos_auditoria.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for r in linhas:
            w.writerow({k: r.get(k, "") for k in campos})

    # Guarda: nenhuma coluna pedida pode sair vazia. A Fase 17 aprendeu isso da
    # forma cara — tres colunas de topologia sairam em branco por chave inventada.
    for r in linhas:
        vazias = [k for k in campos if r.get(k, "") == "" and k in r or k not in r]
        if vazias:
            print("FALHA DE INSTRUMENTO: colunas ausentes/vazias", vazias)
            return 1

    print("\nescrito:", SAIDA / "lynos_auditoria.json", "e .csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
