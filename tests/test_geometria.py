"""
Suite de regressão geométrica do VRmed — 10 testes, um por invariante.

Não há pytest neste ambiente (`.venv-pipeline` não o tem instalado), então cada
teste é uma função com `assert` puro e o `__main__` roda todas e sai com código
!= 0 na primeira falha acumulada. Os nomes seguem a convenção `test_*` de
propósito: se algum dia o pytest entrar no ambiente, a suite é coletada sem
mudar uma linha.

Rodar:
    .venv-pipeline/Scripts/python.exe tests/test_geometria.py

REGRAS QUE ESTA SUITE DEFENDE (e que motivam cada tolerância declarada):

  - Toda distância é medida em MILÍMETROS FÍSICOS, nunca em índice de voxel.
    O teste 10 é o guarda explícito disso.
  - Volume só é número válido em malha watertight. Onde a malha não fecha, o
    teste falha declarando "não aplicável" em vez de comparar um float inválido.
  - Tier 3 (fantoma analítico) é o ÚNICO tier aqui que mede erro absoluto: a
    resposta é fórmula fechada (π/6·d³, π/4·d²·h). Nada nesta suite mede
    acurácia de segmentação (Tier 2) — esse tier não existe no repositório.
  - Dice/ASSD/HD95 de Tier 1 com σ=0 são TAUTOLÓGICOS (a malha rasterizada de
    volta reproduz a máscara por construção) e por isso não aparecem como
    critério de aprovação em teste nenhum aqui.

Nenhuma tolerância abaixo foi ajustada para o teste passar: cada uma é ancorada
num número já publicado em `docs/RELATORIO-VALIDACAO-RECONSTRUCAO.md`, com folga
declarada. Se um teste falhar, a falha é o resultado — não afrouxe o limite.

Isto é engenharia geométrica. Nenhum número aqui é clínico.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scipy import ndimage  # noqa: E402

from scripts.geometry.coordinates import (  # noqa: E402
    gltf_m_para_voxel,
    voxel_para_gltf_m,
    voxel_para_ras_mm,
)
from scripts.geometry.mask_processing import processar_mascara  # noqa: E402
from scripts.geometry.reconstruction import reconstruct_surface  # noqa: E402
from scripts.validation.benchmark_sigma import recortar  # noqa: E402
from scripts.validation.phantom import (  # noqa: E402
    cilindro,
    duas_estruturas_adjacentes,
    esfera,
    esfera_com_cavidade,
    tubo_fino,
)
from scripts.validation.segmentation_metrics import compare_masks  # noqa: E402


# ------------------------------------------------------------------ auxiliares


def _volume_mm3(malha) -> float:
    """Volume da malha em mm³ (a malha sai do pipeline em metros/eixos glTF).

    Falha em vez de devolver float se a malha não for watertight: volume de
    malha aberta é INVÁLIDO, não é "um número com mais erro".
    """
    assert malha.is_watertight, "volume nao aplicavel: malha nao e watertight"
    return abs(float(malha.volume)) * 1e9  # m³ -> mm³


def _erro_pct(medido: float, analitico: float) -> float:
    return 100.0 * (medido - analitico) / analitico


# --------------------------------------------------------------------- testes


def test_01_esfera_analitica() -> str:
    """Tier 3: esfera de 20 mm contra π/6·d³ (verdade analítica, erro absoluto).

    TOLERÂNCIA: 4,0 % de erro de volume.
    Justificativa: o relatório (§2.1, Tier 3, faixa 10–30 mm, variante
    `sigma_auto` = default atual do pipeline) mede mediana −1,40 %. 4 % é ~2,2×
    o pior valor conhecido — folga suficiente para variação de spacing, apertada
    o bastante para pegar regressão real (a mesma esfera com surface_nets dá
    −3,49 % na faixa e a versão sem o pad do FOV degrada bem mais).
    """
    d = 20.0
    analitico = np.pi / 6.0 * d**3
    mask, affine = esfera(d, spacing=(0.7, 0.7, 0.7))
    r = reconstruct_surface(mask, affine)
    assert r is not None, "esfera de 20 mm nao deveria desaparecer na reconstrucao"

    erro = _erro_pct(_volume_mm3(r.mesh), analitico)
    assert abs(erro) <= 4.0, f"erro de volume da esfera {erro:+.3f} % excede 4,0 %"
    return f"erro_volume={erro:+.3f}% (analitico {analitico:.1f} mm3)"


def test_02_cilindro_analitico() -> str:
    """Tier 3: cilindro d=40 h=40 mm contra π/4·d²·h.

    TOLERÂNCIA: 3,0 % de erro de volume.
    Justificativa: relatório §2.1, Tier 3, faixa > 30 mm, `sigma_auto`: mediana
    −0,40 %. Estrutura grossa é o regime em que o pipeline erra menos, então a
    tolerância aqui é MAIS APERTADA que a da esfera de propósito — 3 % ainda é
    7× o erro esperado, mas rejeita qualquer perda de volume de calibre grosso.
    O cilindro também tem quinas (as duas tampas), que é onde a suavização
    morde: é o teste que separa "erro de discretização" de "erro de suavização".
    """
    d, h = 40.0, 40.0
    analitico = np.pi / 4.0 * d**2 * h
    mask, affine = cilindro(d, h, spacing=(0.7, 0.7, 0.7), eixo=2)
    r = reconstruct_surface(mask, affine)
    assert r is not None, "cilindro de 40 mm nao deveria desaparecer na reconstrucao"

    erro = _erro_pct(_volume_mm3(r.mesh), analitico)
    assert abs(erro) <= 3.0, f"erro de volume do cilindro {erro:+.3f} % excede 3,0 %"
    return f"erro_volume={erro:+.3f}% (analitico {analitico:.1f} mm3)"


def test_03_tubo_fino_sigma_zero_preserva_mais() -> str:
    """Tier 3: tubo de 2 mm — σ=0 preserva mais volume que σ automático.

    Guarda de REGRESSÃO do achado já medido (relatório §2.1 / §3.1): na faixa
    < 3 mm o erro de volume é −89,99 % com σ automático e −28,24 % com σ=0.

    TOLERÂNCIA: σ=0 tem de recuperar ao menos 30 pontos percentuais de volume.
    Justificativa: o ganho medido é de ~62 pp (89,99 − 28,24). Exigir 30 pp é
    metade do ganho conhecido — margem que absorve mudança de spacing ou de
    versão do skimage, mas que falha imediatamente se alguém religar a gaussiana
    na máscara binária de calibre fino (o ganho cairia a ~0 pp).

    Não se exige valor absoluto de erro aqui: com 2 mm de calibre em voxel de
    0,7 mm a estrutura tem ~3 voxels de seção e a discretização sozinha já custa
    dezenas de %. O que este teste protege é a ORDEM entre as duas variantes.
    """
    d, h = 2.0, 30.0
    analitico = np.pi / 4.0 * d**2 * h
    mask, affine = tubo_fino(d, h, spacing=(0.7, 0.7, 0.7))

    r_auto = reconstruct_surface(mask, affine, sigma_mm=None)  # default do pipeline
    r_zero = reconstruct_surface(mask, affine, sigma_mm=0.0)
    assert r_zero is not None, "tubo de 2 mm sumiu ate com sigma=0: reconstrucao quebrada"
    # None = estrutura dissolvida pela suavizacao; volume preservado = 0.
    vol_auto = 0.0 if r_auto is None else _volume_mm3(r_auto.mesh)
    vol_zero = _volume_mm3(r_zero.mesh)

    erro_auto = _erro_pct(vol_auto, analitico)
    erro_zero = _erro_pct(vol_zero, analitico)
    ganho_pp = abs(erro_auto) - abs(erro_zero)

    assert vol_zero > vol_auto, (
        f"sigma=0 NAO preservou mais volume: zero={vol_zero:.2f} mm3 vs auto={vol_auto:.2f} mm3"
    )
    assert ganho_pp >= 30.0, f"ganho de sigma=0 caiu para {ganho_pp:.1f} pp (esperado >= 30 pp)"
    return f"auto={erro_auto:+.2f}%  zero={erro_zero:+.2f}%  ganho={ganho_pp:.1f} pp"


def test_04_cavidade_sobrevive_sem_fill_holes() -> str:
    """Casca esférica 20/10 mm com `fill_holes` DESLIGADO continua com cavidade.

    `esfera_com_cavidade` é oca por construção. Com a regra de classe que não
    fecha buraco (classe `vaso`, ver `mask_processing.REGRAS`), a malha tem de
    sair com DOIS corpos: casca externa + parede da cavidade. Um corpo só = o
    `binary_fill_holes` engoliu a cavidade e fabricou volume (§2.3 do relatório
    mede +14,26 % de volume fabricado quando isso acontece).

    TOLERÂNCIA: nenhuma — é contagem inteira de componentes, não medida contínua.
    O critério válido nesta linha é `n_componentes`, e explicitamente NÃO o
    volume: em malha de duas cascas aninhadas o `trimesh` soma o corpo interno
    com sinal invertido e o `volume_error_pct` sai +26,46 % sem nenhum ganho real
    de volume (ressalva registrada em §2.3).
    """
    mask, affine = esfera_com_cavidade(20.0, 10.0, spacing=(0.5, 0.5, 0.5))
    zooms = np.linalg.norm(affine[:3, :3], axis=0)
    voxels_antes = int(mask.sum())

    # "aorta" cai na classe `vaso`: fechar_buracos=False.
    limpa, relatorio = processar_mascara(mask, zooms, "aorta")
    assert int(limpa.sum()) == voxels_antes, (
        f"a limpeza mexeu na mascara oca: {voxels_antes} -> {int(limpa.sum())} voxels"
    )

    r = reconstruct_surface(limpa, affine)
    assert r is not None, "casca esferica de 20 mm nao deveria desaparecer"
    corpos = int(r.mesh.body_count)
    assert corpos == 2, f"cavidade perdida: malha com {corpos} corpo(s), esperado 2"
    return f"corpos={corpos}  voxels={voxels_antes}  ops={relatorio['operacoes']}"


def test_05_componentes_multiplos_nao_fundem() -> str:
    """Duas esferas de 10 mm com vão de 3 mm dão 2 componentes na malha.

    Vão de 3 mm em voxel de 1,0 mm = 3 voxels de separação — folgado para o σ
    automático (max(0,6; 0,5·1,0) = 0,6 mm). Se saírem fundidas, a suavização
    está vazando entre estruturas vizinhas, que é dano silencioso: Dice e volume
    quase não mudam e só a contagem de componentes detecta (§2.5).

    TOLERÂNCIA: nenhuma — contagem inteira. Verifica-se também que a máscara de
    entrada tem 2 componentes, para que a falha aponte a reconstrução e não o
    fantoma.

    Verificação de que o assert é vivo (mutação medida, não suposta): com σ
    dobrado e vão de 1 mm as duas esferas SAEM FUNDIDAS (`body_count` = 1) e o
    assert dispara. Com o vão de 3 mm deste teste, porém, σ tem de crescer ~4×
    para fundir — e nessa altura a estrutura se dissolve ANTES de fundir
    (`reconstruct_surface` devolve None). Ou seja: neste vão o teste pega
    regressão de suavização, mas pela via "estrutura sumiu", não pela via
    "fundiu". Limitação declarada, não corrigida com vão menor: 3 mm é o caso
    folgado que o enunciado pede.
    """
    mask, affine = duas_estruturas_adjacentes(3.0, spacing=(1.0, 1.0, 1.0))
    comp_mascara = int(ndimage.label(mask)[1])
    assert comp_mascara == 2, f"fantoma invalido: mascara com {comp_mascara} componentes"

    r = reconstruct_surface(mask, affine)
    assert r is not None, "duas esferas de 10 mm nao deveriam desaparecer"
    corpos = int(r.mesh.body_count)
    assert corpos == 2, f"fusao indevida: malha com {corpos} corpo(s), esperado 2"
    return f"mascara={comp_mascara} corpos_malha={corpos}"


def test_06_spacing_anisotropico_nao_vira_isotropico() -> str:
    """Mesma esfera em (0,7 0,7 2,5) e (0,7 0,7 0,7) erra na MESMA ORDEM.

    Se alguém passar a tratar o spacing como isotrópico (usar o menor zoom nos
    três eixos, ou ignorar o affine), a esfera reconstruída na grade de fatia
    grossa fica ACHATADA em z por um fator 0,7/2,5 = 0,28. Isso foi MEDIDO, não
    suposto: injetando um affine isotrópico (diag 0,7) sobre a máscara
    rasterizada com fatia de 2,5 mm, o erro de volume vai a **−73,4 %** e este
    teste falha no limite (a) abaixo. Uma ordem de grandeza fora do erro
    isotrópico legítimo.

    TOLERÂNCIAS declaradas:
      (a) |erro| <= 15 % nas duas grades. Medido: −1,80 % (iso) e −6,56 %
          (aniso, 13 fatias cobrindo 20 mm). 15 % dá ~2,3× de folga sobre o pior
          caso e ainda rejeita com sobra o −72 % do cenário isotrópico.
      (b) razão |erro_aniso| / |erro_iso| <= 10. A razão medida é 3,6 — perder
          resolução em um eixo por 3,6× custa erro na mesma DÉCADA, não em outra.
          Tratar spacing como isotrópico levaria essa razão a ~40.
    """
    d = 20.0
    analitico = np.pi / 6.0 * d**3
    erros = {}
    for rotulo, spacing in (("iso", (0.7, 0.7, 0.7)), ("aniso", (0.7, 0.7, 2.5))):
        mask, affine = esfera(d, spacing=spacing)
        r = reconstruct_surface(mask, affine)
        assert r is not None, f"esfera de 20 mm sumiu no spacing {spacing}"
        erros[rotulo] = _erro_pct(_volume_mm3(r.mesh), analitico)

    for rotulo, erro in erros.items():
        assert abs(erro) <= 15.0, f"erro de volume {rotulo} = {erro:+.3f} % excede 15 %"
    razao = abs(erros["aniso"]) / abs(erros["iso"])
    assert razao <= 10.0, (
        f"erro anisotropico {erros['aniso']:+.2f} % e {razao:.1f}x o isotropico "
        f"{erros['iso']:+.2f} % — spacing pode ter virado isotropico"
    )
    return f"iso={erros['iso']:+.3f}%  aniso={erros['aniso']:+.3f}%  razao={razao:.2f}x"


def test_07_identidade_de_mascara() -> str:
    """compare_masks(m, m, spacing) = Dice 1,0 · HD95 0,0 · ASSD 0,0.

    TOLERÂNCIA: ZERO, igualdade exata. Identidade não é aproximação: as
    distâncias saem de uma EDT amostrada na própria superfície, então qualquer
    valor não-nulo aqui denuncia bug de indexação, não ruído numérico.

    (Este é o único contexto em que dice=1,0 / hd95=0 é evidência de algo: com
    a máscara comparada consigo mesma. Em Tier 1 com σ=0 os mesmos três números
    aparecem TAUTOLOGICAMENTE e não provam superioridade de configuração.)
    """
    spacing = (1.5, 1.0, 2.0)  # anisotrópico de propósito: exercita o `sampling`
    cubo = np.zeros((30, 30, 30), dtype=bool)
    cubo[10:20, 10:20, 10:20] = True

    r = compare_masks(cubo, cubo, spacing)
    assert r["dice"] == 1.0, f"dice da identidade = {r['dice']}"
    assert r["iou"] == 1.0, f"iou da identidade = {r['iou']}"
    assert r["hd95_mm"] == 0.0, f"hd95 da identidade = {r['hd95_mm']}"
    assert r["assd_mm"] == 0.0, f"assd da identidade = {r['assd_mm']}"
    assert r["volume_error_pct"] == 0.0, f"erro de volume da identidade = {r['volume_error_pct']}"
    return f"dice={r['dice']}  hd95={r['hd95_mm']}  assd={r['assd_mm']}"


def test_08_dilatacao_de_um_voxel_em_mm() -> str:
    """Dilatação de 1 voxel (face) → HD95 igual ao SPACING EM MM, não 1,0.

    Com spacing isotrópico de 2,0 mm, cada voxel da superfície dilatada está a
    exatamente um passo de face da superfície original: a resposta física é
    2,0 mm. O valor 1,0 seria a mesma distância contada em ÍNDICE DE VOXEL —
    é essa troca que o teste rejeita.

    TOLERÂNCIA: 1e-9 mm (igualdade em ponto flutuante). A distância é exata por
    construção — um passo de face na grade — então não há espaço para folga.
    O caso anisotrópico entra junto: HD95 tem de ficar entre o menor e o maior
    spacing, e nunca virar contagem adimensional.
    """
    cubo = np.zeros((30, 30, 30), dtype=bool)
    cubo[10:20, 10:20, 10:20] = True
    dilatada = ndimage.binary_dilation(cubo)  # structure=None => vizinhanca de face

    spacing = (2.0, 2.0, 2.0)
    r = compare_masks(dilatada, cubo, spacing)
    assert abs(r["hd95_mm"] - 2.0) < 1e-9, (
        f"hd95 = {r['hd95_mm']} mm; esperado 2,0 mm (= spacing). "
        "1,0 significaria distancia contada em indice de voxel"
    )
    assert r["hd95_mm"] != 1.0, "hd95 = 1,0: distancia esta em indice de voxel, nao em mm"
    assert r["dice"] < 1.0, "mascara dilatada nao pode ter dice 1,0 contra a original"

    spacing_aniso = (1.5, 1.0, 2.0)
    r2 = compare_masks(dilatada, cubo, spacing_aniso)
    assert min(spacing_aniso) - 1e-9 <= r2["hd95_mm"] <= max(spacing_aniso) + 1e-9, (
        f"hd95 anisotropico = {r2['hd95_mm']} mm fora de [{min(spacing_aniso)}, {max(spacing_aniso)}]"
    )
    return f"hd95(2,0 mm iso)={r['hd95_mm']:.4f}  hd95(1,5/1,0/2,0)={r2['hd95_mm']:.4f}"


def test_09_affine_preservado_no_recorte_e_no_round_trip() -> str:
    """Recorte não move voxel em mm RAS; round-trip voxel→glTF→voxel < 1e-6.

    Duas metades, ambas sobre affine OBLÍQUA (rotação de 15° + spacing
    anisotrópico), porque affine diagonal esconde exatamente os bugs de
    transposição que a oblíqua expõe.

    TOLERÂNCIAS:
      (a) recorte: 1e-9 mm. `recortar` só corrige a origem — as coordenadas
          físicas têm de ser IDÊNTICAS, não parecidas. 1e-9 mm é ruído de float64
          sobre coordenadas da ordem de centenas de mm.
      (b) round-trip: 1e-6 (em índice de voxel e em mm), o mesmo limite já usado
          em `coordinates._round_trip`. A cadeia é rotação pura + escala, então
          o erro real fica em ~1e-13; 1e-6 é o teto de sanidade.
    """
    t = np.deg2rad(15.0)
    rot = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(t), -np.sin(t)], [0.0, np.sin(t), np.cos(t)]])
    affine = np.eye(4)
    affine[:3, :3] = rot @ np.diag([0.7, 0.7, 2.5])
    affine[:3, 3] = [-180.5, 12.25, -400.75]

    # (a) recorte: mesma nuvem de pontos em mm RAS antes e depois
    mask = np.zeros((60, 55, 40), dtype=bool)
    mask[12:30, 20:41, 5:19] = True
    mask[45:52, 8:14, 25:33] = True  # segundo blob: bounding box larga
    recortada, affine_recortado = recortar(mask, affine, margem_vox=4)

    idx_orig = np.stack(np.nonzero(mask), axis=1).astype(float)
    idx_rec = np.stack(np.nonzero(recortada), axis=1).astype(float)
    assert idx_orig.shape == idx_rec.shape, (
        f"o recorte perdeu voxels: {idx_orig.shape[0]} -> {idx_rec.shape[0]}"
    )
    # np.nonzero varre em ordem C nos dois casos => as listas correspondem 1 a 1.
    desloc_mm = np.abs(
        voxel_para_ras_mm(idx_rec, affine_recortado) - voxel_para_ras_mm(idx_orig, affine)
    ).max()
    assert desloc_mm < 1e-9, f"recortar() moveu voxel em {desloc_mm:.3e} mm RAS"

    # (b) round-trip voxel -> glTF (m) -> voxel, na mesma affine oblíqua
    rng = np.random.default_rng(0)
    pts_vox = rng.uniform(0.0, 256.0, size=(5000, 3))
    erro_vox = np.abs(gltf_m_para_voxel(voxel_para_gltf_m(pts_vox, affine), affine) - pts_vox).max()
    assert erro_vox < 1e-6, f"round-trip obliquo fora da tolerancia: {erro_vox:.3e} voxel"

    # sanidade: a affine é mesmo oblíqua (senão o teste não prova nada)
    linear = affine[:3, :3]
    fora_diagonal = np.abs(linear - np.diag(np.diag(linear))).max()
    assert fora_diagonal > 0.1, "a affine de teste virou diagonal: o caso obliquo nao foi exercitado"
    return f"desloc_recorte={desloc_mm:.2e} mm  erro_round_trip={erro_vox:.2e} voxel"


def test_10_distancia_em_mm_e_nao_em_indice_de_voxel() -> str:
    """GUARDA CENTRAL: a MESMA geometria em 0,5 mm e 1,0 mm dá a MESMA distância.

    Duas esferas concêntricas, d=24 mm e d=20 mm: a diferença física entre as
    superfícies é 2,0 mm de raio, INDEPENDENTE da grade em que se rasteriza.
    Rasterizamos o par em spacing 0,5 mm e em spacing 1,0 mm e exigimos que
    HD95 e ASSD em mm coincidam nas duas grades.

    SE ALGUÉM VOLTAR A USAR ÍNDICE DE VOXEL COMO DISTÂNCIA, O VALOR DOBRA QUANDO
    O SPACING DOBRA — a mesma separação de 2 mm viraria 4 "unidades" na grade de
    0,5 mm e 2 "unidades" na de 1,0 mm — E ESTE TESTE FALHA. É exatamente para
    isso que ele existe: `sampling=spacing` na EDT é a única linha que separa
    milímetro físico de contagem de voxel.

    TOLERÂNCIAS:
      (a) |HD95(0,5) − HD95(1,0)| <= 0,5 mm. Medido: 2,1213 e 2,2361 (Δ = 0,115).
          O limite é 1/4 da separação real de 2 mm — pequeno o bastante para
          reprovar o cenário de índice de voxel, cujo Δ seria ~2,0 mm (17× o
          limite), e grande o bastante para absorver a quantização da EDT, que
          nesta métrica vale um passo de voxel.
      (b) |ASSD(0,5) − ASSD(1,0)| <= 0,3 mm. Medido: 1,9256 e 1,9175
          (Δ = 0,008). ASSD é média sobre toda a superfície, então quantiza bem
          menos que o percentil 95 — daí a tolerância mais apertada.
      (c) as duas medidas ficam a <= 0,5 mm da separação analítica de 2,0 mm.
          Sem isso o teste passaria com dois valores igualmente errados.
    """
    separacao_analitica_mm = 2.0  # (24 − 20)/2
    medidas = {}
    for sp in (0.5, 1.0):
        spacing = (sp, sp, sp)
        # margens escolhidas para as DUAS esferas caírem na MESMA grade
        # (lado = d + 2·margem = 30 mm nos dois casos), senão compare_masks
        # rejeitaria formas diferentes.
        grande, affine_g = esfera(24.0, spacing=spacing, margem_mm=3.0)
        pequena, affine_p = esfera(20.0, spacing=spacing, margem_mm=5.0)
        assert grande.shape == pequena.shape and np.allclose(affine_g, affine_p), (
            f"as duas esferas nao cairam na mesma grade em spacing {sp}"
        )
        medidas[sp] = compare_masks(grande, pequena, spacing)

    d_hd95 = abs(medidas[0.5]["hd95_mm"] - medidas[1.0]["hd95_mm"])
    d_assd = abs(medidas[0.5]["assd_mm"] - medidas[1.0]["assd_mm"])
    assert d_hd95 <= 0.5, (
        f"HD95 mudou {d_hd95:.4f} mm entre spacing 0,5 e 1,0 "
        f"({medidas[0.5]['hd95_mm']:.4f} vs {medidas[1.0]['hd95_mm']:.4f}) — "
        "distancia provavelmente voltou a ser indice de voxel"
    )
    assert d_assd <= 0.3, (
        f"ASSD mudou {d_assd:.4f} mm entre spacing 0,5 e 1,0 "
        f"({medidas[0.5]['assd_mm']:.4f} vs {medidas[1.0]['assd_mm']:.4f}) — "
        "distancia provavelmente voltou a ser indice de voxel"
    )
    for sp, m in medidas.items():
        assert abs(m["assd_mm"] - separacao_analitica_mm) <= 0.5, (
            f"ASSD em spacing {sp} = {m['assd_mm']:.4f} mm, longe da separacao real de 2,0 mm"
        )
    return (
        f"hd95 0,5={medidas[0.5]['hd95_mm']:.4f} 1,0={medidas[1.0]['hd95_mm']:.4f} (d={d_hd95:.4f}) | "
        f"assd 0,5={medidas[0.5]['assd_mm']:.4f} 1,0={medidas[1.0]['assd_mm']:.4f} (d={d_assd:.4f})"
    )


# --------------------------------------------------------------------- runner


def main() -> int:
    testes = [(nome, fn) for nome, fn in sorted(globals().items()) if nome.startswith("test_")]
    falhas: list[str] = []
    print(f"VRmed — suite de regressao geometrica ({len(testes)} testes, assert puro, sem pytest)\n")
    for nome, fn in testes:
        try:
            detalhe = fn() or ""
            print(f"  PASS  {nome}\n        {detalhe}")
        except Exception as e:  # AssertionError e qualquer quebra contam como falha
            falhas.append(nome)
            print(f"  FAIL  {nome}\n        {type(e).__name__}: {e}")
            traceback.print_exc(limit=3)
    print(f"\n{len(testes) - len(falhas)}/{len(testes)} passaram", end="")
    print(f" — FALHOU: {', '.join(falhas)}" if falhas else " — OK")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
