"""
Controles POSITIVOS das métricas — o "teste dos testes".

Uma métrica só é confiável se FALHA quando deveria falhar. `tests/test_geometria.py`
verifica que o pipeline se comporta; esta suite verifica que os INSTRUMENTOS que
julgam o pipeline conseguem, de fato, enxergar o defeito que dizem enxergar.

Motivação medida nesta base (não hipotética):
  - os portões topológicos do benchmark de Taubin eram TAUTOLÓGICOS: Taubin e
    windowed_sinc só deslocam vértices e nunca tocam no array de faces, então
    `n_componentes`, `genus` e `n_boundary_edges` são invariantes por construção
    — "não houve falha" já estava garantido antes de rodar;
  - `n_self_intersections` deu 0 em 40/40 malhas, mas o único controle positivo
    era um FIXTURE (duas icosferas já sobrepostas e concatenadas), não uma dobra
    causada por um filtro;
  - `test_02` de `test_geometria.py` usa tolerância de 3,0 % contra erro medido
    de 0,659 %; `test_05` nunca falha pela via que diz proteger; `test_07`
    devolve dice 1,0 para QUALQUER spacing.

REGRA DESTA SUITE: cada teste induz o defeito (não importa um fixture pronto) e
prova as DUAS direções — a métrica passa no caso são E acusa no caso quebrado.

QUANDO A MÉTRICA NÃO ACUSA, o controle NÃO é afrouxado. A cegueira vira fato
medido, com `assert` vivo fixando o comportamento observado e a linha de saída
prefixada por `ACHADO:`. Se alguém consertar a métrica, o assert quebra e manda
atualizar a documentação — que é o comportamento certo.

Três cegueiras de primeira ordem ficaram registradas aqui:
  1. `comparar_topologia["fechou_cavidade"]` (teste 03) não dispara ao fechar uma
     cavidade SELADA: ele lê `genus`, e casca esférica e bola maciça têm genus 0.
  2. `volume_ml_se_watertight` (teste 03) anda no SENTIDO CONTRÁRIO nessa mesma
     malha: fechar a cavidade ACRESCENTA 4 169 voxels e o volume relatado CAI.
  3. `dimensao_bbox_mm` (teste 06) subestima em 5,4× a perda de calibre que
     `calibre_mediano_mm` mede certo.

Rodar:
    .venv-pipeline/Scripts/python.exe tests/test_controles_positivos.py

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

import trimesh  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.ndimage import binary_erosion, distance_transform_edt  # noqa: E402

from scripts.geometry.reconstruction import reconstruct_surface  # noqa: E402
from scripts.validation.benchmark_smoothing import medir_dimensao  # noqa: E402
from scripts.validation.phantom import (  # noqa: E402
    duas_estruturas_adjacentes,
    esfera,
    esfera_com_cavidade,
    tubo_fino,
    tubo_oco,
)
from scripts.validation.segmentation_metrics import compare_masks  # noqa: E402
from scripts.validation.topology_metrics import (  # noqa: E402
    CONECTIVIDADE,
    comparar_topologia,
    qualidade_topologica,
)

# Linhas coletadas pelo runner para o bloco final "MÉTRICAS CEGAS".
ACHADOS: list[str] = []


def _achado(texto: str) -> str:
    """Registra uma cegueira medida e devolve a linha já prefixada."""
    ACHADOS.append(texto)
    return f"ACHADO: {texto}"


# ------------------------------------------------------------------ auxiliares


def _malha(mask: np.ndarray, affine: np.ndarray, **kw) -> trimesh.Trimesh:
    """Reconstrói com σ=0 (MASTER) e falha em vez de devolver None silencioso."""
    kw.setdefault("sigma_mm", 0.0)
    r = reconstruct_surface(mask, affine, **kw)
    assert r is not None, f"fantoma dissolvido na reconstrucao com {kw}: controle invalido"
    return r.mesh


def _com_vertices(mesh: trimesh.Trimesh, v: np.ndarray) -> trimesh.Trimesh:
    """Mesma lista de FACES, vértices novos — o defeito é geométrico, não topológico.

    `process=False` é obrigatório: com `process=True` o trimesh funde vértices
    coincidentes e reescreve as faces, o que apagaria o defeito induzido.
    """
    return trimesh.Trimesh(vertices=v, faces=mesh.faces.copy(), process=False)


def _eixo_e_secao(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(coordenada ao longo do eixo, seção transversal, centro da seção) em metros glTF.

    `RAS_PARA_GLTF` manda o z do RAS para o y do glTF, então o eixo de um tubo
    construído ao longo de z na máscara é o `v[:, 1]` da malha — a mesma
    convenção que `benchmark_smoothing.calibre_mediano_mm` assume.
    """
    v = np.asarray(mesh.vertices, dtype=float)
    secao = v[:, [0, 2]]
    return v[:, 1], secao, secao.mean(axis=0)


def _pct(medido: float, referencia: float) -> float:
    return 100.0 * (medido - referencia) / referencia


# --------------------------------------------------------------------- testes


def test_01_self_intersection_dobra_induzida() -> str:
    """CONTROLE 1: dobrar a parede de um tubo fino tem de acusar auto-interseção.

    DEFEITO INDUZIDO (não é fixture): num tubo de 4 mm reconstruído pelo pipeline,
    uma calota de vértices do lado +x é empurrada 2,5 raios para dentro — ou seja,
    ATRAVESSA a parede oposta. As faces não são tocadas; só as posições dos
    vértices mudam, que é exatamente o que um filtro de suavização faz.

    DUAS DIREÇÕES:
      são     -> `n_self_intersections == 0` na malha do pipeline;
      quebrado -> `n_self_intersections > 0` na malha dobrada.

    SUBPRODUTO — a tautologia medida: `watertight`, `n_componentes`, `genus` e
    `n_boundary_edges` saem IDÊNTICOS nas duas malhas. Deslocar vértice não
    altera o array de faces, então esses quatro campos são invariantes por
    construção sob qualquer filtro de malha. Um portão de regressão feito só com
    eles aprova a malha dobrada sem olhar para ela — é o achado que originou esta
    suite, e este teste o fixa com `assert`.

    TOLERÂNCIA: nenhuma. É contagem inteira: 0 contra > 0.
    """
    mask, affine = tubo_fino(4.0, 30.0, spacing=(0.5, 0.5, 0.5))
    sa = _malha(mask, affine)
    q_sa = qualidade_topologica(sa)
    assert isinstance(q_sa["n_self_intersections"], int), (
        f"metrica nao mediu ({q_sa['n_self_intersections']}): rtree ausente? controle invalido"
    )
    assert q_sa["n_self_intersections"] == 0, (
        f"a malha SA ja sai com {q_sa['n_self_intersections']} auto-interseccoes: "
        "o caso base nao serve de referencia"
    )

    eixo, secao, centro = _eixo_e_secao(sa)
    raio_med = float(np.median(np.linalg.norm(secao - centro, axis=1)))
    v = np.asarray(sa.vertices, dtype=float).copy()
    # calota: lado +x da seção, numa faixa curta (±2 mm) no meio do tubo
    calota = (v[:, 0] - centro[0] > 0.3 * raio_med) & (np.abs(eixo - eixo.mean()) < 0.002)
    assert calota.sum() >= 20, f"calota com {int(calota.sum())} vertices: pequena demais para dobrar"
    v[calota, 0] -= 2.5 * raio_med  # atravessa a parede oposta (que está a −1 raio)

    q_dobrada = qualidade_topologica(_com_vertices(sa, v))
    assert isinstance(q_dobrada["n_self_intersections"], int), q_dobrada["n_self_intersections"]
    assert q_dobrada["n_self_intersections"] > 0, (
        f"METRICA CEGA: {int(calota.sum())} vertices atravessaram a parede oposta e "
        "n_self_intersections continuou 0"
    )

    invariantes = ("watertight", "n_componentes", "genus", "n_boundary_edges")
    iguais = [k for k in invariantes if q_sa[k] == q_dobrada[k]]
    assert set(iguais) == set(invariantes), (
        f"portoes topologicos deixaram de ser invariantes a deslocamento de vertice: {iguais}"
    )
    _achado(
        "portoes topologicos (watertight/n_componentes/genus/n_boundary_edges) sao "
        "INVARIANTES sob deslocamento de vertice — aprovam a malha dobrada; so "
        "n_self_intersections a reprova"
    )
    return (
        f"self_int: sa=0 -> dobrada={q_dobrada['n_self_intersections']} "
        f"({int(calota.sum())} vertices empurrados 2,5 raios) | "
        f"invariantes inalterados: {', '.join(invariantes)}"
    )


def test_02_fusao_de_componentes_limiar_de_separacao() -> str:
    """CONTROLE 2: aproximar duas estruturas até fundir; achar o limiar de `n_componentes`.

    DEFEITO INDUZIDO: duas esferas de 12 mm em grade de 1,0 mm, com σ = 1,5 mm
    FIXO, e o vão varrido de 3,0 mm até 1,0 mm. A MÁSCARA mantém 2 componentes em
    todo o varrimento (verificado a cada passo), então qualquer fusão observada na
    malha é da SUAVIZAÇÃO, não do fantoma — é isto que distingue este controle de
    um fixture já fundido.

    DUAS DIREÇÕES:
      são      -> vão largo: `n_componentes == 2` (a métrica não inventa fusão);
      quebrado -> vão estreito: `n_componentes == 1` (a métrica acusa).

    LIMIAR: medido entre 1,75 mm (ainda 2 corpos) e 1,50 mm (1 corpo) — impresso
    na linha de resultado, não fixado em assert: ele depende de σ e do spacing e
    travá-lo transformaria o controle num teste de regressão do σ.

    DANO SILENCIOSO: o volume da malha muda pouco na travessia do limiar (número
    impresso). Volume e Dice não separam "duas estruturas vizinhas" de "uma
    estrutura fundida" — só a contagem de componentes separa. Por isso o teste
    exige monotonia: depois de fundir, não pode voltar a separar.
    """
    sigma_mm, spacing = 1.5, (1.0, 1.0, 1.0)
    gaps = (3.0, 2.5, 2.0, 1.75, 1.5, 1.25, 1.0)
    corpos: list[int] = []
    volumes: list[float] = []
    for gap in gaps:
        mask, affine = duas_estruturas_adjacentes(gap, spacing=spacing, diametro_mm=12.0)
        n_mascara = int(ndimage.label(mask, structure=CONECTIVIDADE)[1])
        assert n_mascara == 2, (
            f"vao {gap} mm: a MASCARA ja tem {n_mascara} componente(s) — a fusao seria "
            "do fantoma, nao do pipeline, e o controle nao provaria nada"
        )
        q = qualidade_topologica(_malha(mask, affine, sigma_mm=sigma_mm))
        corpos.append(int(q["n_componentes"]))
        volumes.append(float(q["volume_ml_se_watertight"]))

    assert corpos[0] == 2, f"vao de {gaps[0]} mm ja sai fundido ({corpos[0]} corpo): caso sao invalido"
    assert corpos[-1] == 1, (
        f"METRICA CEGA ou sigma insuficiente: vao de {gaps[-1]} mm com sigma={sigma_mm} mm "
        f"continuou com {corpos[-1]} corpos — nao houve fusao para detectar"
    )
    # monotonia: 2…2,1…1. Uma volta de 1 para 2 significaria contagem instável.
    assert corpos == sorted(corpos, reverse=True), f"contagem nao-monotona no varrimento: {corpos}"

    i = corpos.index(1)
    limiar = f"({gaps[i]:.2f}, {gaps[i - 1]:.2f}] mm"
    d_vol = _pct(volumes[i], volumes[i - 1])
    return (
        f"corpos por vao {list(zip(gaps, corpos))} | limiar de separacao {limiar} "
        f"(sigma={sigma_mm} mm, spacing 1,0 mm) | volume na travessia {d_vol:+.2f} % "
        "— dano silencioso para volume, visivel so em n_componentes"
    )


def test_03_fechamento_de_cavidade() -> str:
    """CONTROLE 3: fechar deliberadamente a cavidade e ver quem acusa.

    Dois defeitos induzidos, porque a cavidade tem dois sabores topológicos:

    (a) LÚMEN PASSANTE (`tubo_oco` 10/6 mm): o lúmen é fechado fatia a fatia com
        `binary_fill_holes` 2D — exatamente o que um pipeline descuidado faz ao
        rodar preenchimento por corte axial. `genus` cai de 1 para 0 e
        `comparar_topologia["fechou_cavidade"]` dispara. A métrica FUNCIONA aqui.

    (b) CAVIDADE SELADA (`esfera_com_cavidade` 20/10 mm): a cavidade é engolida
        por `binary_fill_holes` 3D. `n_componentes` cai de 2 para 1 e acusa.
        `genus` NÃO: casca esférica (2 componentes, euler 4) e bola maciça
        (1 componente, euler 2) têm genus 0 — e o campo chamado justamente
        `fechou_cavidade` sai False. **Métrica cega**, registrada, não afrouxada.

    (c) Pior que cego: `volume_ml_se_watertight` INVERTE o sinal em (b). Fechar a
        cavidade acrescenta ~4 169 voxels de material e o volume relatado CAI, de
        4,69 para 4,17 mL, porque o `trimesh` soma a casca interna com sinal
        trocado (ressalva já registrada em §2.3 do relatório). O teste fixa a
        inversão com assert em vez de deixá-la passar por "erro pequeno".

    DUAS DIREÇÕES: nos dois casos a malha SÃ é medida primeiro e tem de sair com
    a topologia certa (genus 1 em (a), 2 componentes em (b)); o defeito é induzido
    depois, na mesma grade e com o mesmo σ.
    """
    # (a) lúmen passante — genus acusa
    mask, affine = tubo_oco(10.0, 6.0, 20.0, spacing=(0.5, 0.5, 0.5))
    fatiado = mask.copy()
    for k in range(mask.shape[2]):
        fatiado[:, :, k] = ndimage.binary_fill_holes(mask[:, :, k])
    assert int(fatiado.sum()) > int(mask.sum()), "o preenchimento 2D nao fechou o lumen"

    q_a_sa = qualidade_topologica(_malha(mask, affine))
    q_a_q = qualidade_topologica(_malha(fatiado, affine))
    assert q_a_sa["genus"] == 1, f"tubo oco SA com genus {q_a_sa['genus']}, esperado 1"
    assert q_a_q["genus"] == 0, f"lumen fechado com genus {q_a_q['genus']}, esperado 0"
    c_a = comparar_topologia(q_a_sa, q_a_q)
    assert c_a["fechou_cavidade"] is True, f"fechou_cavidade={c_a['fechou_cavidade']} no lumen passante"

    # (b)+(c) cavidade selada — genus cego, volume invertido
    mask, affine = esfera_com_cavidade(20.0, 10.0, spacing=(0.5, 0.5, 0.5))
    cheia = ndimage.binary_fill_holes(mask)
    ganho_vox = int(cheia.sum()) - int(mask.sum())
    assert ganho_vox > 0, "binary_fill_holes nao engoliu a cavidade: defeito nao foi induzido"

    q_b_sa = qualidade_topologica(_malha(mask, affine))
    q_b_q = qualidade_topologica(_malha(cheia, affine))
    assert q_b_sa["n_componentes"] == 2, f"casca SA com {q_b_sa['n_componentes']} corpo(s), esperado 2"
    assert q_b_q["n_componentes"] == 1, (
        f"METRICA CEGA: cavidade engolida e n_componentes continuou {q_b_q['n_componentes']}"
    )
    c_b = comparar_topologia(q_b_sa, q_b_q)
    assert c_b["fundiu_componentes"] is True, c_b["fundiu_componentes"]

    # cegueira 1: genus não muda; o campo com o nome do defeito não dispara
    assert q_b_sa["genus"] == 0 and q_b_q["genus"] == 0, (
        f"genus deixou de ser cego a cavidade selada ({q_b_sa['genus']} -> {q_b_q['genus']}): "
        "a metrica melhorou, atualize o ACHADO deste teste"
    )
    assert c_b["fechou_cavidade"] is False, (
        f"fechou_cavidade virou {c_b['fechou_cavidade']}: atualize o ACHADO deste teste"
    )
    _achado(
        "comparar_topologia['fechou_cavidade'] NAO dispara ao fechar cavidade SELADA "
        "(le genus, e casca esferica e bola macica tem genus 0); quem acusa e n_componentes"
    )

    # cegueira 2: volume anda no sentido contrário ao material acrescentado
    v_sa, v_q = q_b_sa["volume_ml_se_watertight"], q_b_q["volume_ml_se_watertight"]
    assert v_q < v_sa, (
        f"volume deixou de inverter ({v_sa} -> {v_q}) com +{ganho_vox} voxels: "
        "atualize o ACHADO deste teste"
    )
    _achado(
        f"volume_ml_se_watertight INVERTE o sinal em casca aninhada: +{ganho_vox} voxels de "
        f"material e o volume relatado cai {v_sa} -> {v_q} mL (trimesh soma a casca interna "
        "com sinal trocado) — volume nao e criterio valido nesta malha"
    )
    return (
        f"(a) lumen passante: genus {q_a_sa['genus']}->{q_a_q['genus']}, fechou_cavidade=True | "
        f"(b) cavidade selada: n_componentes {q_b_sa['n_componentes']}->{q_b_q['n_componentes']} "
        f"acusa, genus {q_b_sa['genus']}->{q_b_q['genus']} CEGO, fechou_cavidade=False | "
        f"(c) volume {v_sa}->{v_q} mL com +{ganho_vox} voxels: SINAL INVERTIDO"
    )


def test_04_borda_aberta_por_remocao_de_faces() -> str:
    """CONTROLE 4: arrancar faces de uma REGIÃO e exigir watertight=False e borda > 0.

    DEFEITO INDUZIDO: numa esfera de 20 mm reconstruída pelo pipeline, as faces
    cujo centróide está acima do percentil 97 do eixo y (uma calota contígua, não
    um `faces[:-10]` arbitrário) são removidas. É o modelo de um recorte de FOV ou
    de uma decimação que rasga a malha.

    DUAS DIREÇÕES:
      são      -> `watertight is True`, `n_boundary_edges == 0`, volume numérico;
      quebrado -> `watertight is False`, `n_boundary_edges > 0`, e volume/genus
                  saem como STRING ("invalido"/"não aplicável"), nunca como float
                  plausível — a convenção de valor ausente do módulo é parte do
                  que este controle verifica.

    Também se exige `delta_boundary_edges == n_boundary_edges` do lado quebrado:
    o delta tem de propagar a contagem inteira, não um sinal booleano.
    """
    mask, affine = esfera(20.0, spacing=(0.7, 0.7, 0.7))
    sa = _malha(mask, affine)
    q_sa = qualidade_topologica(sa)
    assert q_sa["watertight"] is True and q_sa["n_boundary_edges"] == 0, (
        f"esfera SA ja aberta: watertight={q_sa['watertight']} borda={q_sa['n_boundary_edges']}"
    )
    assert isinstance(q_sa["volume_ml_se_watertight"], float), q_sa["volume_ml_se_watertight"]

    centroides = np.asarray(sa.triangles).mean(axis=1)
    calota = centroides[:, 1] > np.percentile(centroides[:, 1], 97.0)
    assert calota.sum() > 0, "nenhuma face selecionada para remocao"
    aberta = trimesh.Trimesh(vertices=sa.vertices.copy(), faces=sa.faces[~calota].copy(), process=False)

    q_q = qualidade_topologica(aberta)
    assert q_q["watertight"] is False, "METRICA CEGA: malha com faces removidas continuou watertight"
    assert q_q["n_boundary_edges"] > 0, (
        f"METRICA CEGA: {int(calota.sum())} faces removidas e n_boundary_edges = 0"
    )
    assert q_q["volume_ml_se_watertight"] == "invalido", (
        f"volume de malha aberta devolveu {q_q['volume_ml_se_watertight']!r} em vez de 'invalido'"
    )
    assert q_q["genus"] == "nao aplicavel", f"genus de malha aberta = {q_q['genus']!r}"

    c = comparar_topologia(q_sa, q_q)
    assert c["abriu_malha"] is True, c["abriu_malha"]
    assert c["delta_boundary_edges"] == q_q["n_boundary_edges"], (
        f"delta {c['delta_boundary_edges']} != contagem {q_q['n_boundary_edges']}"
    )
    assert c["delta_volume_ml"] == "invalido", c["delta_volume_ml"]
    return (
        f"removidas {int(calota.sum())}/{len(sa.faces)} faces | "
        f"watertight True->False | boundary_edges 0->{q_q['n_boundary_edges']} | "
        f"volume {q_sa['volume_ml_se_watertight']} mL -> 'invalido' | genus 0 -> 'nao aplicavel'"
    )


def test_05_volume_sob_escala_conhecida() -> str:
    """CONTROLE 5: escalar por fator conhecido; o erro de volume tem de dar fator³ − 1.

    DEFEITO INDUZIDO em dois níveis, porque são dois instrumentos diferentes:

    (a) MALHA — `trimesh.volume` da esfera reconstruída, escalada por 1,10 e por
        0,90. A resposta é aritmética exata: 1,331 e 0,729.
        TOLERÂNCIA: 1e-9 RELATIVA. Aqui não há discretização nenhuma no caminho
        (a escala é multiplicação de vértices), então qualquer folga maior estaria
        escondendo bug de unidade, não ruído.

    (b) MÁSCARA — `compare_masks(...)["volume_error_pct"]` entre a esfera de
        30,0 mm e a de 33,0 mm rasterizadas na MESMA grade (as margens são
        escolhidas para o lado total bater; o teste verifica isso antes de medir).
        Esperado +33,10 %; medido +33,11 %.
        TOLERÂNCIA: 1,0 pp. Não é folga arbitrária: é o custo de discretizar duas
        esferas diferentes na mesma grade de 0,5 mm, e ainda assim é 33× menor que
        o efeito que se quer detectar.

    DUAS DIREÇÕES: fator 1,0 tem de dar erro EXATAMENTE 0 (a métrica não inventa
    diferença) e fator 1,10 tem de dar +33,1 % (a métrica não é um zero constante
    — o assert `> 30` reprova qualquer implementação que devolva ~0 sempre).
    """
    mask, affine = esfera(20.0, spacing=(0.7, 0.7, 0.7))
    sa = _malha(mask, affine)
    v0 = abs(float(sa.volume))
    razoes: dict[float, float] = {}
    for fator in (1.0, 1.10, 0.90):
        escalada = sa.copy()
        escalada.apply_scale(fator)
        razoes[fator] = abs(float(escalada.volume)) / v0
        esperado = fator**3
        assert abs(razoes[fator] - esperado) <= 1e-9 * esperado, (
            f"escala {fator}: razao de volume {razoes[fator]:.12f}, esperado {esperado:.12f}"
        )
    assert razoes[1.0] == 1.0, f"escala 1,0 mexeu no volume: {razoes[1.0]}"
    assert (razoes[1.10] - 1.0) * 100.0 > 30.0, "a metrica de volume nao acusou a escala de 1,10"

    # (b) nível máscara, mesma grade para as duas esferas
    d, spc, margem = 30.0, 0.5, 6.0
    m_ref, _ = esfera(d, spacing=(spc,) * 3, margem_mm=margem)
    m_maior, _ = esfera(d * 1.10, spacing=(spc,) * 3, margem_mm=margem - d * 0.05)
    assert m_ref.shape == m_maior.shape, (
        f"as duas esferas nao cairam na mesma grade: {m_ref.shape} vs {m_maior.shape}"
    )
    erro_igual = compare_masks(m_ref, m_ref, (spc,) * 3)["volume_error_pct"]
    erro_maior = compare_masks(m_maior, m_ref, (spc,) * 3)["volume_error_pct"]
    assert erro_igual == 0.0, f"mascara contra si mesma deu erro de volume {erro_igual}"
    assert abs(erro_maior - 33.1) <= 1.0, (
        f"erro de volume da escala 1,10 = {erro_maior:+.4f} %, esperado +33,10 % (limite 1,0 pp)"
    )
    return (
        f"malha: 1,10 -> {razoes[1.10]:.9f} (esperado 1,331) | 0,90 -> {razoes[0.90]:.9f} "
        f"(esperado 0,729) | 1,0 -> {razoes[1.0]:.9f} || mascara d={d}->{d * 1.1} mm: "
        f"{erro_maior:+.4f} % (esperado +33,10, desvio {erro_maior - 33.1:+.4f} pp)"
    )


def test_06_calibre_mediano_acompanha_e_bbox_nao() -> str:
    """CONTROLE 6: encolher o calibre de um tubo; a MEDIANA acompanha, a BBOX não.

    Os dois instrumentos saem da mesma chamada real do repositório
    (`benchmark_smoothing.medir_dimensao`): `dimensao_medida_mm` é
    `calibre_mediano_mm`, `dimensao_bbox_mm` é a bounding box da seção.

    DOIS DEFEITOS INDUZIDOS sobre a mesma malha de tubo de 4 mm:

    (a) encolhimento radial UNIFORME de 10 %. Os DOIS instrumentos acertam:
        −10,000 % cada. Este ramo existe para que o teste não seja uma acusação
        genérica contra a bbox — no defeito uniforme ela funciona.

    (b) o MESMO encolhimento de 10 %, aplicado a todos os vértices MENOS os 2 %
        de maior raio. Isso modela o que o docstring de `calibre_mediano_mm` já
        registra: a bbox é uma estatística de MÁXIMO sobre as pontas da escada do
        marching cubes, então mede o que o filtro faz com as pontas e não com a
        parede. Medido: calibre −10,233 % (acerta), bbox −1,882 % (subestima 5,4×).

    TOLERÂNCIAS:
      - calibre: |erro − (−10 %)| <= 1,5 pp nos dois ramos. A folga cobre a
        mediana caminhar entre vértices vizinhos; 1,5 pp é 6,7× menor que o
        efeito de 10 pp que se quer detectar.
      - bbox no ramo (b): |erro_bbox| <= 0,4 · |erro_calibre|, fixando a cegueira
        medida. Se alguém trocar a bbox por um instrumento que enxergue, este
        assert quebra e manda atualizar o ACHADO — é o comportamento certo.
    """
    mask, affine = tubo_fino(4.0, 30.0, spacing=(0.5, 0.5, 0.5))
    sa = _malha(mask, affine)
    dims = {"d": 4.0, "h": 30.0}

    def medir(mesh: trimesh.Trimesh) -> tuple[float, float]:
        m = medir_dimensao(mesh, "tubo", dims)
        return float(m["dimensao_medida_mm"]), float(m["dimensao_bbox_mm"])

    cal0, bbox0 = medir(sa)
    assert abs(_pct(cal0, 4.0)) <= 5.0, f"calibre da malha SA = {cal0:.4f} mm, longe do nominal 4,0"

    _eixo, secao, centro = _eixo_e_secao(sa)
    raios = np.linalg.norm(secao - centro, axis=1)
    encolhida = centro + (secao - centro) * 0.90  # −10 % no raio

    def aplicar(mover: np.ndarray) -> tuple[float, float]:
        v = np.asarray(sa.vertices, dtype=float).copy()
        v[mover, 0] = encolhida[mover, 0]
        v[mover, 2] = encolhida[mover, 1]
        return medir(_com_vertices(sa, v))

    # (a) uniforme
    cal_a, bbox_a = aplicar(np.ones(len(raios), dtype=bool))
    e_cal_a, e_bbox_a = _pct(cal_a, cal0), _pct(bbox_a, bbox0)
    assert abs(e_cal_a + 10.0) <= 1.5, f"calibre no defeito uniforme = {e_cal_a:+.3f} %, esperado −10 %"
    assert abs(e_bbox_a + 10.0) <= 1.5, f"bbox no defeito uniforme = {e_bbox_a:+.3f} %, esperado −10 %"

    # (b) preservando as pontas da escada (2 % de maior raio)
    poupados = raios >= np.percentile(raios, 98.0)
    cal_b, bbox_b = aplicar(~poupados)
    e_cal_b, e_bbox_b = _pct(cal_b, cal0), _pct(bbox_b, bbox0)
    assert abs(e_cal_b + 10.0) <= 1.5, (
        f"METRICA CEGA: parede encolhida 10 % e calibre_mediano acusou so {e_cal_b:+.3f} %"
    )
    assert abs(e_bbox_b) <= 0.4 * abs(e_cal_b), (
        f"bbox deixou de ser cega ({e_bbox_b:+.3f} % contra {e_cal_b:+.3f} % da mediana): "
        "atualize o ACHADO deste teste"
    )
    _achado(
        f"dimensao_bbox_mm subestima a perda de calibre em {abs(e_cal_b / e_bbox_b):.1f}x quando as "
        f"pontas da escada nao se movem ({e_bbox_b:+.3f} % contra {e_cal_b:+.3f} % de "
        "calibre_mediano_mm) — bbox mede a ponta da escada, nao a parede"
    )
    return (
        f"SA calibre={cal0:.4f} mm bbox={bbox0:.4f} mm (nominal 4,0) | "
        f"(a) 10 % uniforme: calibre {e_cal_a:+.3f} % / bbox {e_bbox_a:+.3f} % — os dois acertam | "
        f"(b) 10 % poupando o percentil 98: calibre {e_cal_b:+.3f} % / bbox {e_bbox_b:+.3f} % "
        f"— bbox subestima {abs(e_cal_b / e_bbox_b):.1f}x"
    )


def test_07_hd95_devolve_o_spacing_de_cada_eixo() -> str:
    """CONTROLE 7: deslocar 1 voxel em CADA eixo e exigir HD95 = spacing daquele eixo.

    DEFEITO INDUZIDO: um cubo de 16³ voxels em grade ANISOTRÓPICA
    (0,7 × 1,0 × 3,0 mm) é deslocado de exatamente 1 voxel, um eixo de cada vez.
    A resposta física é o spacing daquele eixo: 0,7 · 1,0 · 3,0 mm. O valor 1,0 é
    a mesma distância contada em ÍNDICE DE VOXEL.

    O eixo de 3,0 mm é o que importa: com spacing isotrópico de 1 mm a versão
    correta e a bugada dão o mesmo número e o controle não provaria nada.

    MUTANTE EXPLÍCITO: `_hd95_em_indice_de_voxel` reimplementa a mesma métrica
    SEM `sampling=spacing` — é a única linha que separa milímetro de contagem.
    O teste exige que o mutante devolva 1,0 nos três eixos e que a implementação
    real NÃO devolva. Isto é o que faz do controle um controle: sem o mutante,
    "HD95 = 0,7" seria só um número plausível.

    TOLERÂNCIA: 1e-9 mm. O deslocamento é um passo de face exato na grade.

    (Contraste com `test_geometria.test_07`: lá `compare_masks(m, m, spacing)`
    devolve dice 1,0 e hd95 0,0 para QUALQUER spacing — o assert é cego à troca
    mm↔índice porque zero vezes qualquer escala continua zero.)
    """
    spacing = (0.7, 1.0, 3.0)
    cubo = np.zeros((40, 40, 40), dtype=bool)
    cubo[12:28, 12:28, 12:28] = True

    def hd95_em_indice_de_voxel(a: np.ndarray, b: np.ndarray) -> float:
        """A MESMA métrica sem `sampling=spacing`: o bug que o controle procura."""
        sa = a & ~binary_erosion(a, border_value=0)
        sb = b & ~binary_erosion(b, border_value=0)
        d_ab = distance_transform_edt(~sb)[sa]
        d_ba = distance_transform_edt(~sa)[sb]
        return float(max(np.percentile(d_ab, 95), np.percentile(d_ba, 95)))

    medidos: list[float] = []
    mutantes: list[float] = []
    for eixo in range(3):
        deslocado = np.roll(cubo, 1, axis=eixo)
        r = compare_masks(deslocado, cubo, spacing)
        medidos.append(r["hd95_mm"])
        mutantes.append(hd95_em_indice_de_voxel(deslocado, cubo))
        assert abs(r["hd95_mm"] - spacing[eixo]) < 1e-9, (
            f"eixo {eixo}: hd95 = {r['hd95_mm']} mm, esperado {spacing[eixo]} mm (= spacing do eixo)"
        )
        assert r["dice"] < 1.0, f"eixo {eixo}: mascara deslocada com dice 1,0"

    assert mutantes == [1.0, 1.0, 1.0], (
        f"o mutante sem sampling nao devolveu 1,0 nos tres eixos ({mutantes}): "
        "o controle perdeu o poder de separar mm de indice de voxel"
    )
    difere = [i for i in range(3) if abs(medidos[i] - mutantes[i]) > 1e-9]
    assert len(difere) >= 2, (
        f"a implementacao real so difere do mutante nos eixos {difere}: "
        "spacing anisotropico nao foi exercitado"
    )
    return (
        f"hd95 por eixo = {[round(v, 4) for v in medidos]} mm contra spacing {list(spacing)} "
        f"| mutante sem sampling = {mutantes} (1,0 em todos: indice de voxel) "
        f"| eixos onde os dois divergem: {difere}"
    )


def test_08_dice_nao_ordena_qualidade_espacial() -> str:
    """CONTROLE 8: duas máscaras com Dice IDÊNTICO e HD95 8× diferente.

    CONSTRUÇÃO: cubo de 24³ voxels. Duas predições retiram os MESMOS 576 voxels:
      - `raso`  — uma lasca de 1 voxel sobre a face inteira (24 × 24 × 1);
      - `fundo` — um furo de 6 × 6 voxels com 16 de profundidade (6 × 6 × 16).
    Mesmo |P|, mesma interseção com a referência ⇒ Dice idêntico BIT A BIT.

    DUAS DIREÇÕES, e as duas são sobre o Dice:
      o que ele FAZ  -> detecta a perda de volume: dice < 1,0 nos dois casos;
      o que NÃO faz  -> ordenar: `dice_raso == dice_fundo` na última casa. Um
                        portão de promoção baseado em Dice aprova as duas
                        predições como equivalentes.
    HD95 separa: 1,0 mm contra 8,0 mm (8×). ASSD também (0,169 contra 0,375).

    TOLERÂNCIA do Dice: igualdade EXATA (`==`). Não é aproximação — os dois
    numeradores e denominadores são os mesmos inteiros. Se algum dia diferirem, a
    construção deixou de valer e o teste tem de falhar, não arredondar.
    """
    lado, borda, spacing = 24, 12, (1.0, 1.0, 1.0)
    n = lado + 2 * borda
    ref = np.zeros((n, n, n), dtype=bool)
    ref[borda : borda + lado, borda : borda + lado, borda : borda + lado] = True

    raso = ref.copy()
    raso[borda : borda + lado, borda : borda + lado, borda + lado - 1 : borda + lado] = False
    fundo = ref.copy()
    c = borda + (lado - 6) // 2
    fundo[c : c + 6, c : c + 6, borda + lado - 16 : borda + lado] = False

    removidos_raso = int(ref.sum() - raso.sum())
    removidos_fundo = int(ref.sum() - fundo.sum())
    assert removidos_raso == removidos_fundo == 576, (
        f"construcao invalida: raso removeu {removidos_raso}, fundo removeu {removidos_fundo}"
    )

    r_raso = compare_masks(raso, ref, spacing)
    r_fundo = compare_masks(fundo, ref, spacing)

    assert r_raso["dice"] < 1.0 and r_fundo["dice"] < 1.0, "dice nao caiu: a perda de volume sumiu"
    assert r_raso["dice"] == r_fundo["dice"], (
        f"a construcao falhou: dice {r_raso['dice']!r} != {r_fundo['dice']!r} — "
        "sem Dice identico o controle nao prova cegueira"
    )
    assert r_raso["volume_error_pct"] == r_fundo["volume_error_pct"], "erro de volume tambem tem de empatar"
    assert r_fundo["hd95_mm"] >= 4.0 * r_raso["hd95_mm"], (
        f"METRICA CEGA: hd95 {r_fundo['hd95_mm']} vs {r_raso['hd95_mm']} — nem HD95 separou "
        "um furo de 16 voxels de uma lasca de 1"
    )
    _achado(
        f"dice e volume_error_pct sao IDENTICOS ({r_raso['dice']:.12f} / "
        f"{r_raso['volume_error_pct']:+.4f} %) para uma lasca de 1 voxel e um furo de 16 — "
        f"nao ordenam qualidade espacial; HD95 separa {r_raso['hd95_mm']:.1f} vs "
        f"{r_fundo['hd95_mm']:.1f} mm"
    )
    return (
        f"raso : dice={r_raso['dice']:.12f} hd95={r_raso['hd95_mm']:.4f} assd={r_raso['assd_mm']:.4f} "
        f"hd={r_raso['hd_mm']:.4f} | "
        f"fundo: dice={r_fundo['dice']:.12f} hd95={r_fundo['hd95_mm']:.4f} "
        f"assd={r_fundo['assd_mm']:.4f} hd={r_fundo['hd_mm']:.4f} | "
        f"dice identico={r_raso['dice'] == r_fundo['dice']}, razao hd95="
        f"{r_fundo['hd95_mm'] / r_raso['hd95_mm']:.1f}x"
    )


# --------------------------------------------------------------------- runner


def main() -> int:
    testes = [(nome, fn) for nome, fn in sorted(globals().items()) if nome.startswith("test_")]
    falhas: list[str] = []
    print(f"VRmed — controles positivos das metricas ({len(testes)} testes, assert puro, sem pytest)\n")
    for nome, fn in testes:
        try:
            detalhe = fn() or ""
            print(f"  PASS  {nome}\n        {detalhe}")
        except Exception as e:  # AssertionError e qualquer quebra contam como falha
            falhas.append(nome)
            print(f"  FAIL  {nome}\n        {type(e).__name__}: {e}")
            traceback.print_exc(limit=3)
    if ACHADOS:
        print(f"\nMETRICAS CEGAS / DEGENERADAS MEDIDAS ({len(ACHADOS)}):")
        for i, a in enumerate(ACHADOS, 1):
            print(f"  {i}. {a}")
    print(f"\n{len(testes) - len(falhas)}/{len(testes)} passaram", end="")
    print(f" — FALHOU: {', '.join(falhas)}" if falhas else " — OK")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
