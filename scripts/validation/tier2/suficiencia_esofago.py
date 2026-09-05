"""Parte 13 — os dados que TEMOS bastam para um modelo especializado de esofago?

Isto e SIMULACAO DE RISCO. Nao treina nada, nao carrega peso, nao escreve
mascara. Mede o que existe no `development` e transforma "sera que da?" em
numero.

------------------------------------------------------------------------------
O QUE ESTE ARQUIVO PODE E NAO PODE FAZER COM O GT

O GT entra aqui como OBJETO DE MEDIDA — quantos voxels ele tem, que forma tem,
quanto ele varia entre servicos. Isso e inventario, nao fabricacao: nenhuma
mascara e construida, nenhuma constante daqui vira regra de pos-processamento.

A predicao entra por UM motivo so, e vale explicar porque e o eixo do
argumento de estilo: o TotalSegmentator e um modelo unico, que nunca viu o
rotulo de instituicao. Ele e, portanto, uma REGUA CONSTANTE apontada para as
tres instituicoes. Se a razao (predicao / GT) muda sistematicamente conforme o
servico, a coisa que mudou nao foi a regua — foi a convencao de contorno. E
por isso que a razao de area serve de descritor de ESTILO e o volume bruto do
GT nao serve: o volume bruto mistura anatomia do caso com convencao do servico,
a razao divide a anatomia fora.

Os valores de razao de area NAO sao remedidos aqui — sao lidos de
fase5/diagnostico/diagnostico_longitudinal.csv, que ja os mediu com autoteste
proprio. Reimplementar seria criar uma segunda definicao da mesma coisa.
------------------------------------------------------------------------------

SPLIT: so `development` (30 casos). O `validation` e o `test` nao sao lidos,
nao sao medidos e nao sao citados. Ha um assert que derruba a execucao se um
caso de fora do development entrar na lista.

O QUE E MEDIDO
  1. Inventario do GT de esofago no development: voxels, fatias, volume,
     comprimento em Z, area por fatia, tudo por caso / por instituicao / por
     spacing em Z, mais os casos extremos pela regra de Tukey.
  2. Decomposicao de variancia ENTRE instituicoes contra DENTRO de instituicao
     (ANOVA de um fator + ICC(1) + teste de permutacao), aplicada aos
     descritores de estilo e aos de anatomia.
  3. Risco de superajuste em numero: voxels positivos contra parametros de uma
     nnU-Net 3D; casos independentes contra parametros; simulacao das divisoes
     treino/validacao possiveis com 30 casos estratificados 10/10/10.
  4. Tamanho de amostra necessario para SEPARAR instituicoes no efeito
     observado, contra o tamanho de amostra que existe.

PREMISSAS DECLARADAS (nao sao medida — sao referencia externa)
  - numero de parametros de uma nnU-Net 3D "tipica": ordem de 1e7. A tarefa
    declara essa ordem; aqui ela e usada como premissa, com 3,1e7 de
    sensibilidade. NAO foi medida nesta base.
  - o teste de tamanho de amostra usa alfa 0,05 bilateral e poder 0,80, com
    aproximacao normal. Declarado antes de olhar o resultado.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import fase5, geometria  # noqa: E402

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase6" / "suficiencia"
CSV_FASE5 = RAIZ_PADRAO / "fase5" / "diagnostico" / "diagnostico_longitudinal.csv"
NM = "nao medido"
NA = "nao aplicavel"

ESTRUTURA = "Esophagus"
MASCARA_GT = "mask_Esophagus.nii.gz"
MASCARA_PRED = "esophagus.nii.gz"

# ------------------------------------------------------------------ premissas

# Ordem de grandeza declarada na tarefa. NAO medida aqui — nenhuma rede foi
# instanciada nesta fase. O par existe para mostrar que o veredito nao depende
# de qual das duas se escolhe.
PARAMETROS_NNUNET = {"ordem_1e7": 1.0e7, "sensibilidade_3e7": 3.1e7}

# Declarados ANTES de olhar o resultado (mesma disciplina da fase 5).
LIMIAR_ICC_ESTILO = 0.50        # metade da variancia do descritor vindo do servico
LIMIAR_P_PERMUTACAO = 0.05
ALFA = 0.05                     # bilateral
PODER = 0.80
Z_ALFA, Z_PODER = 1.959964, 0.841621

N_PERMUTACOES = 10000
SEMENTE_PERMUTACAO = "vrmed-fase6-suficiencia"

# Descritores separados por natureza. A separacao e o experimento: se o padrao
# por instituicao aparecer nos de ESTILO e nao nos de ANATOMIA, o que difere
# entre servicos e a convencao de contorno, nao o corpo dos casos.
DESCRITORES_ESTILO = ("razao_area_mediana", "frac_fatias_mais_estreita")
DESCRITORES_ANATOMIA = ("volume_gt_mL", "comprimento_gt_mm", "area_gt_mediana_mm2")


# ------------------------------------------------------- medida de uma mascara


def descrever_mascara(m: np.ndarray, spacing) -> dict:
    """Inventario geometrico de uma mascara booleana. Funcao pura — testavel.

    Z e o eixo 2 (as mascaras do Tier2 chegam todas com o eixo de fatia em 2;
    quem confere isso e geometria.verificar_alinhamento, chamada por medir_caso).
    """
    dx, dy, dz = (float(v) for v in spacing[:3])
    area_voxel = dx * dy
    voxel_mm3 = area_voxel * dz

    m = np.asarray(m, dtype=bool)
    n_voxels = int(m.sum())
    if n_voxels == 0:
        return {"n_voxels": 0, "volume_mL": NA, "n_fatias": 0, "erro": "mascara vazia"}

    por_fatia = m.reshape(-1, m.shape[2]).sum(axis=0)
    com_voxel = np.flatnonzero(por_fatia)
    z0, z1 = int(com_voxel[0]), int(com_voxel[-1])
    extensao_fatias = z1 - z0 + 1
    areas = por_fatia[com_voxel].astype(float) * area_voxel

    return {
        "n_voxels": n_voxels,
        "volume_mL": n_voxels * voxel_mm3 / 1000.0,
        "voxel_mm3": voxel_mm3,
        "spacing_mm": [dx, dy, dz],
        "n_fatias": int(com_voxel.size),
        "extensao_fatias": extensao_fatias,
        "fatias_vazias_internas": extensao_fatias - int(com_voxel.size),
        "comprimento_z_mm": extensao_fatias * dz,
        "z_min": z0, "z_max": z1,
        "campo_z_mm": float(m.shape[2]) * dz,
        "area_mediana_mm2": float(np.percentile(areas, 50)),
        "area_p5_mm2": float(np.percentile(areas, 5)),
        "area_p95_mm2": float(np.percentile(areas, 95)),
        "area_min_mm2": float(areas.min()),
        "area_max_mm2": float(areas.max()),
        "voxels_por_fatia_mediana": float(np.percentile(por_fatia[com_voxel], 50)),
        "areas_mm2": areas.tolist(),  # consumido pela agregacao, nao vai para o CSV
    }


def medir_caso(caso: str, raiz: Path = RAIZ_PADRAO) -> dict:
    """Le o GT de esofago do caso e o descreve. A grade e conferida ANTES."""
    dir_caso = Path(raiz) / caso
    p_gt = dir_caso / "gt" / MASCARA_GT
    p_pred = dir_caso / "pred_masks" / MASCARA_PRED

    # Obrigatorio antes de qualquer medida: se as grades divergirem, os numeros
    # da fase 5 que vamos importar para este caso nao se referem a esta mascara.
    alinhamento = geometria.verificar_alinhamento(p_pred, p_gt)

    img = nib.load(str(p_gt))
    codigos = nib.aff2axcodes(img.affine)
    # descrever_mascara conta fatia no eixo 2. Se o eixo 2 nao for o cranio-caudal,
    # "comprimento em Z" e "area por fatia" medem outra coisa — para aqui.
    if codigos[2] not in ("S", "I"):
        raise AssertionError(f"{caso}: eixo 2 e {codigos[2]}, nao o cranio-caudal — "
                             "a contagem por fatia nao se aplica")
    d = descrever_mascara(np.asarray(img.dataobj) > 0.5, img.header.get_zooms()[:3])
    d.update({
        "case_id": caso,
        "instituicao": fase5.instituicao_de(caso),
        "orientacao": "".join(nib.aff2axcodes(img.affine)),
        "alinhamento": alinhamento["veredito"],
    })
    return d


# --------------------------------------------------- decomposicao de variancia


def _p(v, q: float):
    v = np.asarray([x for x in v if isinstance(x, (int, float))], dtype=float)
    return float(np.percentile(v, q)) if v.size else NM


def _iqr(v) -> float:
    v = np.asarray(v, dtype=float)
    return float(np.percentile(v, 75) - np.percentile(v, 25))


def _f_um_fator(valores: np.ndarray, indices: list[np.ndarray]) -> float:
    """F de ANOVA de um fator. Separada para o teste de permutacao reusar."""
    media = valores.mean()
    ssb = sum(idx.size * (valores[idx].mean() - media) ** 2 for idx in indices)
    ssw = sum(float(((valores[idx] - valores[idx].mean()) ** 2).sum()) for idx in indices)
    k, n = len(indices), valores.size
    if ssw <= 0 or n <= k:
        return math.inf if ssb > 0 else 0.0
    return (ssb / (k - 1)) / (ssw / (n - k))


def decompor_variancia(valores, grupos, n_perm: int = N_PERMUTACOES,
                       semente: str = SEMENTE_PERMUTACAO) -> dict:
    """Quanto da variacao de um descritor esta ENTRE grupos e quanto esta DENTRO.

    Devolve eta2 (fracao da soma de quadrados que e entre grupos), ICC(1) com
    correcao para grupos desbalanceados, F, um p por permutacao dos rotulos, e
    um par robusto (amplitude das medianas de grupo contra a mediana dos IQR
    internos) que nao depende de normalidade.

    p por permutacao: embaralha os ROTULOS de grupo mantendo os valores. Sob a
    hipotese de que o grupo nao importa, o F observado e so mais um da
    distribuicao embaralhada.
    """
    v = np.asarray(valores, dtype=float)
    g = list(grupos)
    if v.size != len(g):
        raise ValueError("valores e grupos com tamanhos diferentes")
    nomes = sorted(set(g))
    indices = [np.flatnonzero(np.array(g) == nome) for nome in nomes]
    k, n = len(nomes), v.size
    if k < 2 or n <= k:
        return {"veredito": NA, "motivo": f"k={k}, n={n}"}

    media = v.mean()
    sst = float(((v - media) ** 2).sum())
    ssb = float(sum(idx.size * (v[idx].mean() - media) ** 2 for idx in indices))
    ssw = sst - ssb
    if sst <= 0:
        return {"veredito": NA, "motivo": "variancia total zero — descritor constante"}

    msb, msw = ssb / (k - 1), ssw / (n - k)
    # n0 de Snedecor: vira o proprio n do grupo quando balanceado.
    n0 = (n - sum(idx.size ** 2 for idx in indices) / n) / (k - 1)
    den = msb + (n0 - 1) * msw
    icc = (msb - msw) / den if den != 0 else NA

    f_obs = _f_um_fator(v, indices)
    rng = random.Random(semente)
    tamanhos = [idx.size for idx in indices]
    extremos = 0
    for _ in range(n_perm):
        ordem = list(range(n))
        rng.shuffle(ordem)
        i, perm = 0, []
        for t in tamanhos:
            perm.append(np.array(ordem[i:i + t]))
            i += t
        if _f_um_fator(v, perm) >= f_obs:
            extremos += 1
    p = (extremos + 1) / (n_perm + 1)  # estimador conservador; nunca devolve 0

    medianas = {nome: float(np.median(v[idx])) for nome, idx in zip(nomes, indices)}
    iqrs = {nome: _iqr(v[idx]) for nome, idx in zip(nomes, indices)}
    amplitude = max(medianas.values()) - min(medianas.values())
    iqr_tipico = float(np.median(list(iqrs.values())))

    return {
        "n": n, "k": k, "grupos": nomes, "n_por_grupo": tamanhos,
        "media_geral": float(media),
        "medias_de_grupo": {nome: float(v[idx].mean()) for nome, idx in zip(nomes, indices)},
        "medianas_de_grupo": medianas,
        "desvios_de_grupo": {nome: float(v[idx].std(ddof=1)) if idx.size > 1 else NA
                             for nome, idx in zip(nomes, indices)},
        "iqr_de_grupo": iqrs,
        "SSB": ssb, "SSW": ssw, "SST": sst, "MSB": msb, "MSW": msw,
        "eta2_entre_grupos": ssb / sst,
        "F": f_obs, "ICC1": icc,
        "p_permutacao": p, "n_permutacoes": n_perm,
        "amplitude_das_medianas": amplitude,
        "IQR_interno_tipico": iqr_tipico,
        "razao_entre_sobre_dentro_robusta": (amplitude / iqr_tipico) if iqr_tipico > 0 else NA,
        "veredito": (
            "variacao ENTRE grupos domina" if (isinstance(icc, float)
                                               and icc >= LIMIAR_ICC_ESTILO
                                               and p < LIMIAR_P_PERMUTACAO)
            else "variacao DENTRO dos grupos domina"
        ),
    }


def n_por_grupo_necessario(d1: dict, d2: dict) -> dict:
    """Quantos casos por instituicao para SEPARAR duas instituicoes no efeito visto.

    Formula classica de duas amostras: n = 2 (z_alfa + z_poder)^2 / d^2, com d
    de Cohen sobre o desvio agrupado. Premissas em ALFA/PODER, declaradas no
    topo. Isto responde "o dado que existe consegue enxergar o efeito que ele
    mesmo mostrou?" — nao e poder de um modelo, e poder da MEDIDA.
    """
    s1, s2, n1, n2 = d1["sd"], d2["sd"], d1["n"], d2["n"]
    if not (isinstance(s1, float) and isinstance(s2, float)) or n1 < 2 or n2 < 2:
        return {"veredito": NA, "motivo": "desvio indisponivel"}
    sp2 = ((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)
    if sp2 <= 0:
        return {"veredito": NA, "motivo": "desvio agrupado zero"}
    delta = abs(d1["media"] - d2["media"])
    d_cohen = delta / math.sqrt(sp2)
    if d_cohen == 0:
        return {"veredito": NA, "motivo": "diferenca de medias zero"}
    n = 2 * (Z_ALFA + Z_PODER) ** 2 / d_cohen ** 2
    return {
        "par": f"{d1['nome']} x {d2['nome']}",
        "diferenca_de_medias": delta,
        "desvio_agrupado": math.sqrt(sp2),
        "d_de_cohen": d_cohen,
        "n_por_grupo_necessario": math.ceil(n),
        "alfa": ALFA, "poder": PODER,
        "premissa": "aproximacao normal, duas amostras, bilateral",
    }


# ------------------------------------------------------- simulacao de divisoes


def simular_divisoes(voxels_por_instituicao: dict[str, list[int]]) -> list[dict]:
    """Divisoes treino/validacao possiveis mantendo a estratificacao 1/1/1.

    Para cada v (casos de validacao POR INSTITUICAO), devolve quantos casos
    sobram para treino em cada braco e os LIMITES exatos de voxels positivos de
    treino — minimo se a validacao levar os maiores casos, maximo se levar os
    menores. Limite exato, nao estimativa: nao ha como saber quais casos iriam
    para validacao, entao se declara o intervalo inteiro.
    """
    instituicoes = sorted(voxels_por_instituicao)
    por_inst = {i: sorted(voxels_por_instituicao[i]) for i in instituicoes}
    n_inst = {i: len(por_inst[i]) for i in instituicoes}
    minimo = min(n_inst.values())
    total = sum(sum(v) for v in por_inst.values())

    linhas = []
    for v in range(0, minimo):
        treino_por_inst = {i: n_inst[i] - v for i in instituicoes}
        # pior caso: validacao leva os v maiores de cada instituicao
        vox_min = sum(sum(por_inst[i][:n_inst[i] - v]) for i in instituicoes)
        # melhor caso: validacao leva os v menores
        vox_max = sum(sum(por_inst[i][v:]) for i in instituicoes)
        linhas.append({
            "casos_validacao_por_instituicao": v,
            "n_treino": sum(treino_por_inst.values()),
            "n_validacao": v * len(instituicoes),
            "treino_por_instituicao": treino_por_inst,
            "voxels_treino_min": vox_min,
            "voxels_treino_max": vox_max,
            "frac_voxels_treino_min": vox_min / total if total else NA,
            "voxels_por_parametro_min": {
                nome: vox_min / p for nome, p in PARAMETROS_NNUNET.items()},
            "voxels_por_parametro_max": {
                nome: vox_max / p for nome, p in PARAMETROS_NNUNET.items()},
        })
    return linhas


# ---------------------------------------------------------------- agregadores


def _resumo(valores) -> dict:
    v = [x for x in valores if isinstance(x, (int, float))]
    if not v:
        return {"n": 0, "mediana": NM}
    a = np.asarray(v, dtype=float)
    return {
        "n": int(a.size), "soma": float(a.sum()),
        "mediana": float(np.percentile(a, 50)),
        "media": float(a.mean()),
        "sd": float(a.std(ddof=1)) if a.size > 1 else NA,
        "p5": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95)),
        "min": float(a.min()), "max": float(a.max()),
        "iqr": _iqr(a),
    }


def _extremos_tukey(casos: list[dict], chave: str) -> dict:
    """Regra de Tukey (1,5 x IQR). Boring de proposito: e o criterio padrao e
    nao foi escolhido depois de olhar quem ficaria de fora."""
    v = np.asarray([c[chave] for c in casos], dtype=float)
    q1, q3 = float(np.percentile(v, 25)), float(np.percentile(v, 75))
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    fora = [{"case_id": c["case_id"], "instituicao": c["instituicao"], chave: c[chave],
             "lado": "abaixo" if c[chave] < lo else "acima"}
            for c in casos if c[chave] < lo or c[chave] > hi]
    return {"q1": q1, "q3": q3, "iqr": iqr, "limite_inferior": lo, "limite_superior": hi,
            "n_fora": len(fora), "casos": sorted(fora, key=lambda r: r[chave])}


def _ler_estilo_fase5(caminho: Path, casos_permitidos: set[str]) -> dict[str, dict]:
    """Descritores de estilo ja medidos na fase 5. Nao remedidos aqui."""
    if not Path(caminho).exists():
        return {}
    out = {}
    with open(caminho, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["structure"] != ESTRUTURA or r["case_id"] not in casos_permitidos:
                continue
            out[r["case_id"]] = {k: float(r[k]) for k in
                                 ("razao_area_mediana", "frac_fatias_mais_estreita",
                                  "volume_gt_mL", "comprimento_gt_mm",
                                  "area_gt_mediana_mm2", "n_fatias_gt")}
    return out


# --------------------------------------------------------------------- rodada


def rodar(raiz: Path = RAIZ_PADRAO, log=print) -> dict:
    raiz = Path(raiz)
    split = fase5.carregar_split(raiz)
    dev = sorted(split["development"])
    proibidos = set(split["validation"]) | set(split["test"])
    assert not (set(dev) & proibidos), "caso fora do development entrou na lista"
    log(f"development: {len(dev)} casos — validation/test nao sao lidos")

    casos: list[dict] = []
    for i, caso in enumerate(dev, 1):
        d = medir_caso(caso, raiz)
        casos.append(d)
        log(f"  [{i:2d}/{len(dev)}] {caso} — {d['n_voxels']} voxels, "
            f"{d['n_fatias']} fatias, {d['volume_mL']:.2f} mL")
    assert all(c["case_id"] not in proibidos for c in casos)

    # ---- 1. inventario
    todas_areas = [a for c in casos for a in c["areas_mm2"]]
    total_voxels = sum(c["n_voxels"] for c in casos)
    inventario = {
        "n_casos": len(casos),
        "n_fatias_com_esofago_total": sum(c["n_fatias"] for c in casos),
        "n_voxels_positivos_total": total_voxels,
        "maior_contribuicao_de_um_caso": max(c["n_voxels"] for c in casos) / total_voxels,
        "volume_mL": _resumo([c["volume_mL"] for c in casos]),
        "comprimento_z_mm": _resumo([c["comprimento_z_mm"] for c in casos]),
        "n_fatias_por_caso": _resumo([c["n_fatias"] for c in casos]),
        "area_por_fatia_mm2_todas_as_fatias": _resumo(todas_areas),
        "area_mediana_por_caso_mm2": _resumo([c["area_mediana_mm2"] for c in casos]),
        "fatias_vazias_internas_total": sum(c["fatias_vazias_internas"] for c in casos),
        "casos_com_fatia_vazia_interna": [c["case_id"] for c in casos
                                          if c["fatias_vazias_internas"] > 0],
        "frac_do_campo_z_ocupada_pelo_gt": _resumo(
            [c["comprimento_z_mm"] / c["campo_z_mm"] for c in casos]),
    }

    # ---- 2. estratos
    def _estratos(chave_grupo) -> dict:
        grupos: dict[Any, list[dict]] = {}
        for c in casos:
            grupos.setdefault(chave_grupo(c), []).append(c)
        return {str(g): {
            "n_casos": len(v),
            "casos": sorted(c["case_id"] for c in v),
            "n_voxels_total": sum(c["n_voxels"] for c in v),
            "volume_mL": _resumo([c["volume_mL"] for c in v]),
            "comprimento_z_mm": _resumo([c["comprimento_z_mm"] for c in v]),
            "area_mediana_mm2": _resumo([c["area_mediana_mm2"] for c in v]),
            "n_fatias": _resumo([c["n_fatias"] for c in v]),
        } for g, v in sorted(grupos.items(), key=lambda kv: str(kv[0]))}

    por_instituicao = _estratos(lambda c: c["instituicao"])
    por_dz = _estratos(lambda c: round(c["spacing_mm"][2], 3))

    # o confundimento e a limitacao central: se dz nao varia dentro da
    # instituicao, "efeito de instituicao" e "efeito de spacing" sao a mesma
    # coluna do dado e nenhuma medida daqui os separa.
    cruz: dict[str, dict[str, int]] = {}
    for c in casos:
        cruz.setdefault(c["instituicao"], {}).setdefault(str(round(c["spacing_mm"][2], 3)), 0)
        cruz[c["instituicao"]][str(round(c["spacing_mm"][2], 3))] += 1
    confundidas = [i for i, d in cruz.items() if len(d) == 1]

    # ---- 3. extremos
    extremos = {k: _extremos_tukey(casos, k) for k in
                ("volume_mL", "comprimento_z_mm", "area_mediana_mm2", "n_voxels")}

    # ---- 4. estilo x anatomia
    estilo = _ler_estilo_fase5(raiz / CSV_FASE5.relative_to(RAIZ_PADRAO), set(dev))
    variancia: dict[str, dict] = {}
    fonte_estilo = str(CSV_FASE5) if estilo else NM

    def _serie(nome: str) -> tuple[list[float], list[str]] | None:
        if nome in ("volume_mL", "comprimento_z_mm", "area_mediana_mm2", "n_fatias"):
            return ([c[nome] for c in casos], [c["instituicao"] for c in casos])
        if estilo and all(c["case_id"] in estilo for c in casos):
            return ([estilo[c["case_id"]][nome] for c in casos],
                    [c["instituicao"] for c in casos])
        return None

    for nome in (*DESCRITORES_ESTILO, *DESCRITORES_ANATOMIA, "n_fatias"):
        s = _serie(nome)
        variancia[nome] = decompor_variancia(*s) if s else {"veredito": NM,
                                                            "motivo": "descritor indisponivel"}

    # CONTRASTE INTERNO — o controle que torna o achado de estilo interpretavel.
    # comprimento_z_mm e anatomia em milimetro, independente da grade; a razao de
    # area e a mesma anatomia vista por uma regua constante (a predicao). Se o
    # comprimento NAO separa instituicoes e a razao SEPARA, o que muda entre
    # servicos nao e o corpo dos casos.
    principal = DESCRITORES_ESTILO[0]
    anat, est = variancia.get("comprimento_gt_mm", {}), variancia.get(principal, {})
    contraste = {
        "descritor_de_anatomia": "comprimento_gt_mm",
        "descritor_de_estilo": principal,
        "eta2_anatomia": anat.get("eta2_entre_grupos", NM),
        "p_anatomia": anat.get("p_permutacao", NM),
        "eta2_estilo": est.get("eta2_entre_grupos", NM),
        "p_estilo": est.get("p_permutacao", NM),
        "estilo_separa_e_anatomia_nao": bool(
            isinstance(est.get("p_permutacao"), float) and isinstance(anat.get("p_permutacao"), float)
            and est["p_permutacao"] < LIMIAR_P_PERMUTACAO <= anat["p_permutacao"]),
        "ressalva_n_fatias": (
            "n_fatias depende do spacing em Z e por isso NAO e descritor de anatomia puro; "
            "a versao independente da grade e comprimento_gt_mm, em milimetro"
        ),
    }

    # tamanho de amostra necessario para separar as duas instituicoes mais
    # distantes no descritor de estilo principal
    poder = {"veredito": NM}
    v_principal = variancia.get(principal, {})
    if isinstance(v_principal.get("medias_de_grupo"), dict):
        medias = v_principal["medias_de_grupo"]
        alto = max(medias, key=medias.get)
        baixo = min(medias, key=medias.get)
        poder = n_por_grupo_necessario(
            {"nome": alto, "media": medias[alto],
             "sd": v_principal["desvios_de_grupo"][alto],
             "n": v_principal["n_por_grupo"][v_principal["grupos"].index(alto)]},
            {"nome": baixo, "media": medias[baixo],
             "sd": v_principal["desvios_de_grupo"][baixo],
             "n": v_principal["n_por_grupo"][v_principal["grupos"].index(baixo)]},
        )
        poder["descritor"] = principal
        poder["disponivel_por_instituicao_no_development"] = min(v_principal["n_por_grupo"])

    # ---- 5. risco de superajuste
    risco = {
        "premissa_parametros": PARAMETROS_NNUNET,
        "premissa_origem": ("ordem declarada na tarefa; NAO medida nesta base — "
                            "nenhuma rede foi instanciada nesta fase"),
        "voxels_positivos": total_voxels,
        "voxels_por_parametro": {n: total_voxels / p for n, p in PARAMETROS_NNUNET.items()},
        "casos_independentes": len(casos),
        "parametros_por_caso": {n: p / len(casos) for n, p in PARAMETROS_NNUNET.items()},
        "nota_unidade_independente": (
            "voxel nao e unidade independente: os voxels de um caso vem do mesmo corpo, "
            "do mesmo aparelho e do mesmo contorno. A razao voxels/parametros e o limite "
            "SUPERIOR otimista; a razao casos/parametros e o limite inferior honesto."
        ),
    }
    voxels_por_inst = {i: [c["n_voxels"] for c in casos if c["instituicao"] == i]
                       for i in sorted({c["instituicao"] for c in casos})}
    divisoes = simular_divisoes(voxels_por_inst)

    # RECONCILIACAO — nesta base ja se descobriu cinco vezes que a metrica
    # estava errada e nao o pipeline. Volume, fatias e comprimento sao medidos
    # aqui a partir da mascara e TAMBEM existem na fase 5, medidos por outro
    # codigo. Se as duas medidas divergirem, uma das duas esta errada e o
    # inventario inteiro fica suspeito. Delta maximo vai gravado.
    reconciliacao = {"veredito": NM, "motivo": "csv da fase 5 ausente"}
    if estilo:
        deltas = {"volume_mL": [], "n_fatias": [], "comprimento_z_mm": []}
        for c in casos:
            e = estilo[c["case_id"]]
            deltas["volume_mL"].append(abs(c["volume_mL"] - e["volume_gt_mL"]))
            deltas["n_fatias"].append(abs(c["n_fatias"] - e["n_fatias_gt"]))
            deltas["comprimento_z_mm"].append(abs(c["comprimento_z_mm"] - e["comprimento_gt_mm"]))
        maximos = {k: float(max(v)) for k, v in deltas.items()}
        # tolerancias: volume e float acumulado (1e-6 mL), fatia e contagem
        # (exata), comprimento e multiplo do dz (exato ate arredondamento).
        ok = (maximos["volume_mL"] < 1e-6 and maximos["n_fatias"] == 0
              and maximos["comprimento_z_mm"] < 1e-6)
        reconciliacao = {
            "contra": str(CSV_FASE5), "delta_maximo": maximos,
            "veredito": "confere" if ok else "DIVERGE — inventario suspeito",
        }

    resultado = {
        "estrutura": ESTRUTURA,
        "split_usado": "development",
        "casos_usados": dev,
        "fonte_dos_descritores_de_estilo": fonte_estilo,
        "reconciliacao_com_fase5": reconciliacao,
        "contraste_anatomia_x_estilo": contraste,
        "orientacoes": sorted({c["orientacao"] for c in casos}),
        "inventario": inventario,
        "por_instituicao": por_instituicao,
        "por_spacing_z": por_dz,
        "cruzamento_instituicao_x_spacing_z": cruz,
        "instituicoes_com_spacing_z_unico": sorted(confundidas),
        "extremos_tukey": extremos,
        "variancia_entre_x_dentro": variancia,
        "tamanho_de_amostra": poder,
        "risco_de_superajuste": risco,
        "divisoes_possiveis": divisoes,
        "casos": [{k: v for k, v in c.items() if k != "areas_mm2"} for c in casos],
    }
    resultado["veredito"] = _veredito(resultado)
    return resultado


# -------------------------------------------------------------------- veredito


def _veredito(r: dict) -> dict:
    """Veredito por REGRA declarada, aplicada aos numeros medidos.

    Nao ha julgamento livre aqui: cada criterio e uma comparacao contra um
    limiar do topo do arquivo, e o veredito e a conjuncao deles.
    """
    criterios = []

    for nome in DESCRITORES_ESTILO:
        v = r["variancia_entre_x_dentro"].get(nome, {})
        icc, p = v.get("ICC1"), v.get("p_permutacao")
        ok = isinstance(icc, float) and isinstance(p, float)
        criterios.append({
            "criterio": f"estilo `{nome}`: variacao entre instituicoes domina?",
            "regra": f"ICC1 >= {LIMIAR_ICC_ESTILO} e p_permutacao < {LIMIAR_P_PERMUTACAO}",
            "medido": {"ICC1": icc, "p_permutacao": p,
                       "eta2": v.get("eta2_entre_grupos"),
                       "razao_robusta": v.get("razao_entre_sobre_dentro_robusta")},
            "atende": bool(ok and icc >= LIMIAR_ICC_ESTILO and p < LIMIAR_P_PERMUTACAO),
        })

    poder = r["tamanho_de_amostra"]
    n_nec = poder.get("n_por_grupo_necessario")
    n_disp = poder.get("disponivel_por_instituicao_no_development")
    criterios.append({
        "criterio": "ha casos suficientes por instituicao para SEPARAR o efeito de estilo?",
        "regra": "n_por_grupo_necessario <= n disponivel por instituicao",
        "medido": {"necessario": n_nec, "disponivel": n_disp},
        "atende": bool(isinstance(n_nec, int) and isinstance(n_disp, int) and n_nec <= n_disp),
    })

    conf = r["instituicoes_com_spacing_z_unico"]
    criterios.append({
        "criterio": "instituicao e spacing em Z sao separaveis neste dado?",
        "regra": "nenhuma instituicao com spacing em Z unico",
        "medido": {"instituicoes_com_spacing_unico": conf},
        "atende": not conf,
    })

    estilo_domina = any(c["atende"] for c in criterios[:len(DESCRITORES_ESTILO)])
    poder_ok = criterios[-2]["atende"]
    separavel = criterios[-1]["atende"]

    if not estilo_domina and poder_ok and separavel:
        decisao = "SIM"
    elif estilo_domina or not separavel:
        decisao = "NAO COM ESTE DATASET"
    else:
        decisao = "NAO"

    return {
        "decisao": decisao,
        "criterios": criterios,
        "estilo_domina_a_variacao": estilo_domina,
        "poder_suficiente_para_separar_estilo": poder_ok,
        "instituicao_separavel_de_spacing": separavel,
        "limiares_declarados": {
            "ICC1": LIMIAR_ICC_ESTILO, "p_permutacao": LIMIAR_P_PERMUTACAO,
            "alfa": ALFA, "poder": PODER,
        },
    }


# --------------------------------------------------------------------- saidas


def _f(v, casas=4) -> str:
    if isinstance(v, float):
        return f"{v:.{casas}f}".replace(".", ",")
    if isinstance(v, int):
        return str(v)
    return str(v)


COLUNAS_CASO = ("case_id", "instituicao", "spacing_mm", "orientacao", "alinhamento",
                "n_voxels", "volume_mL", "voxel_mm3", "n_fatias", "extensao_fatias",
                "fatias_vazias_internas", "comprimento_z_mm", "campo_z_mm",
                "area_mediana_mm2", "area_p5_mm2", "area_p95_mm2",
                "area_min_mm2", "area_max_mm2")


def _summary_md(r: dict) -> str:
    inv, ver = r["inventario"], r["veredito"]
    L = [
        "# Parte 13 — suficiencia do dado para um modelo especializado de esofago",
        "",
        f"**VEREDITO: {ver['decisao']}**",
        "",
        "Simulacao de risco. Nada foi treinado. Split usado: `development` "
        f"({inv['n_casos']} casos). `validation` e `test` nao foram lidos.",
        "",
        f"Reconciliacao com a fase 5 (volume, fatias, comprimento medidos por outro "
        f"codigo): **{r['reconciliacao_com_fase5'].get('veredito', NM)}** — delta maximo "
        f"`{json.dumps(r['reconciliacao_com_fase5'].get('delta_maximo', NM), ensure_ascii=False)}`. "
        f"Orientacoes encontradas: {r.get('orientacoes', NM)}.",
        "",
        "## 1. Inventario do GT de esofago",
        "",
        "| medida | valor |",
        "|---|---|",
        f"| casos | {inv['n_casos']} |",
        f"| fatias com esofago (soma) | {inv['n_fatias_com_esofago_total']} |",
        f"| voxels positivos (soma) | {inv['n_voxels_positivos_total']} |",
        f"| maior contribuicao de um unico caso | {_f(inv['maior_contribuicao_de_um_caso'])} |",
        f"| fatias vazias internas ao suporte (soma) | {inv['fatias_vazias_internas_total']} |",
        "",
        "| distribuicao por caso | mediana | P5 | P95 | min | max |",
        "|---|---|---|---|---|---|",
    ]
    for rot, chave in (("volume (mL)", "volume_mL"),
                       ("comprimento em Z (mm)", "comprimento_z_mm"),
                       ("fatias com esofago", "n_fatias_por_caso"),
                       ("area mediana por caso (mm2)", "area_mediana_por_caso_mm2"),
                       ("fracao do campo Z ocupada", "frac_do_campo_z_ocupada_pelo_gt")):
        d = inv[chave]
        L.append(f"| {rot} | {_f(d['mediana'])} | {_f(d['p5'])} | {_f(d['p95'])} | "
                 f"{_f(d['min'])} | {_f(d['max'])} |")
    a = inv["area_por_fatia_mm2_todas_as_fatias"]
    L += ["",
          f"Area transversal por fatia, agrupando as {a['n']} fatias de todos os casos: "
          f"mediana {_f(a['mediana'])} mm2, P5 {_f(a['p5'])}, P95 {_f(a['p95'])}, "
          f"min {_f(a['min'])}, max {_f(a['max'])}.",
          "",
          "## 2. Por instituicao e por spacing em Z", "",
          "| estrato | n | voxels | volume mediano (mL) | comprimento mediano (mm) | "
          "area mediana (mm2) |", "|---|---|---|---|---|---|"]
    for rotulo, bloco in (("instituicao", r["por_instituicao"]), ("dz", r["por_spacing_z"])):
        for g, d in bloco.items():
            L.append(f"| {rotulo} {g} | {d['n_casos']} | {d['n_voxels_total']} | "
                     f"{_f(d['volume_mL']['mediana'])} | "
                     f"{_f(d['comprimento_z_mm']['mediana'])} | "
                     f"{_f(d['area_mediana_mm2']['mediana'])} |")
    L += ["", "Cruzamento instituicao x spacing em Z: "
          f"`{json.dumps(r['cruzamento_instituicao_x_spacing_z'], ensure_ascii=False)}`.",
          f"Instituicoes com um unico spacing em Z: "
          f"{r['instituicoes_com_spacing_z_unico'] or 'nenhuma'}. "
          "Onde isso acontece, instituicao e spacing sao a MESMA coluna do dado e "
          "nenhuma medida deste arquivo os separa.",
          "", "## 3. Casos extremos (regra de Tukey, 1,5 x IQR)", ""]
    for chave, d in r["extremos_tukey"].items():
        fora = ", ".join(f"{c['case_id']} ({_f(c[chave], 2)}, {c['lado']})"
                         for c in d["casos"]) or "nenhum"
        L.append(f"- **{chave}**: limites [{_f(d['limite_inferior'], 2)}, "
                 f"{_f(d['limite_superior'], 2)}] — {d['n_fora']} fora: {fora}")

    L += ["", "## 4. Variacao ENTRE instituicoes contra DENTRO de instituicao", "",
          "ICC1 = fracao da variancia do descritor atribuivel a instituicao. "
          "p por permutacao dos rotulos de instituicao "
          f"({N_PERMUTACOES} permutacoes, semente fixa).", "",
          "| descritor | tipo | ICC1 | eta2 | F | p | amplitude das medianas | "
          "IQR interno tipico | razao |", "|---|---|---|---|---|---|---|---|---|"]
    for nome, v in r["variancia_entre_x_dentro"].items():
        tipo = ("estilo" if nome in DESCRITORES_ESTILO else "anatomia")
        if "ICC1" not in v:
            L.append(f"| `{nome}` | {tipo} | {v.get('veredito', NM)} | | | | | | |")
            continue
        L.append(f"| `{nome}` | {tipo} | {_f(v['ICC1'])} | {_f(v['eta2_entre_grupos'])} | "
                 f"{_f(v['F'], 3)} | {_f(v['p_permutacao'])} | "
                 f"{_f(v['amplitude_das_medianas'])} | {_f(v['IQR_interno_tipico'])} | "
                 f"{_f(v['razao_entre_sobre_dentro_robusta'], 3)} |")

    ct = r["contraste_anatomia_x_estilo"]
    L += ["", "**Contraste anatomia x estilo** — o controle interno. "
              f"`{ct['descritor_de_anatomia']}` (anatomia em milimetro, independente da "
              f"grade): eta2 {_f(ct['eta2_anatomia'])}, p {_f(ct['p_anatomia'])}. "
              f"`{ct['descritor_de_estilo']}` (a mesma anatomia medida contra uma regua "
              f"constante — a predicao de um modelo unico que nunca viu o rotulo de "
              f"instituicao): eta2 {_f(ct['eta2_estilo'])}, p {_f(ct['p_estilo'])}. "
              f"Estilo separa instituicoes e anatomia nao: "
              f"**{'sim' if ct['estilo_separa_e_anatomia_nao'] else 'nao'}**.",
          "", f"Ressalva: {ct['ressalva_n_fatias']}."]

    p = r["tamanho_de_amostra"]
    if p.get("n_por_grupo_necessario"):
        L += ["", f"Para SEPARAR {p['par']} no descritor `{p['descritor']}` com alfa "
                  f"{ALFA} e poder {PODER}: d de Cohen {_f(p['d_de_cohen'], 3)}, "
                  f"**{p['n_por_grupo_necessario']} casos por instituicao necessarios** "
                  f"contra {p['disponivel_por_instituicao_no_development']} disponiveis."]

    risco = r["risco_de_superajuste"]
    L += ["", "## 5. Risco de superajuste, em numero", "",
          "| medida | ordem 1e7 | sensibilidade 3,1e7 |", "|---|---|---|",
          f"| voxels positivos por parametro | "
          f"{_f(risco['voxels_por_parametro']['ordem_1e7'])} | "
          f"{_f(risco['voxels_por_parametro']['sensibilidade_3e7'])} |",
          f"| parametros por caso independente | "
          f"{_f(risco['parametros_por_caso']['ordem_1e7'], 0)} | "
          f"{_f(risco['parametros_por_caso']['sensibilidade_3e7'], 0)} |",
          "", f"O numero de parametros e PREMISSA, nao medida: {risco['premissa_origem']}.",
          "", risco["nota_unidade_independente"], "",
          "## 6. Divisoes treino/validacao possiveis (estratificadas 1/1/1)", "",
          "| val. por instituicao | n treino | n validacao | treino por instituicao | "
          "voxels de treino (min-max) | voxels/parametro a 1e7 (min-max) |",
          "|---|---|---|---|---|---|"]
    for d in r["divisoes_possiveis"]:
        L.append(f"| {d['casos_validacao_por_instituicao']} | {d['n_treino']} | "
                 f"{d['n_validacao']} | "
                 f"{json.dumps(d['treino_por_instituicao'], ensure_ascii=False)} | "
                 f"{d['voxels_treino_min']}-{d['voxels_treino_max']} | "
                 f"{_f(d['voxels_por_parametro_min']['ordem_1e7'], 3)}-"
                 f"{_f(d['voxels_por_parametro_max']['ordem_1e7'], 3)} |")

    L += ["", "## 7. Veredito", "", f"**{ver['decisao']}**", "",
          "| criterio | regra | atende |", "|---|---|---|"]
    for c in ver["criterios"]:
        L.append(f"| {c['criterio']} | `{c['regra']}` | {'sim' if c['atende'] else 'nao'} |")
    L += ["", "Limiares declarados antes de olhar o resultado: "
              f"`{json.dumps(ver['limiares_declarados'], ensure_ascii=False)}`.", ""]
    return "\n".join(L)


def gravar(r: dict, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)

    p_json = saida / "suficiencia_esofago.json"
    p_json.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")

    p_csv = saida / "por_caso.csv"
    with open(p_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COLUNAS_CASO))
        w.writeheader()
        for c in r["casos"]:
            w.writerow({k: (json.dumps(c[k]) if isinstance(c.get(k), list) else c.get(k, NM))
                        for k in COLUNAS_CASO})

    p_md = saida / "summary.md"
    p_md.write_text(_summary_md(r), encoding="utf-8")
    for p in (p_json, p_csv, p_md):
        log(f"gravado: {p}")
    return {"json": str(p_json), "csv": str(p_csv), "md": str(p_md)}


# -------------------------------------------------------------------- autoteste


def _tubo(shape=(30, 30, 40), z=(5, 25), raio=3, gap=None) -> np.ndarray:
    m = np.zeros(shape, dtype=bool)
    cx, cy = shape[0] // 2, shape[1] // 2
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    disco = (xx - cx) ** 2 + (yy - cy) ** 2 <= raio ** 2
    for k in range(z[0], z[1] + 1):
        if gap and gap[0] <= k <= gap[1]:
            continue
        m[:, :, k] = disco
    return m


def _autoteste() -> None:
    # ---- descrever_mascara: numero conhecido, calculado a mao
    sp = (1.0, 2.0, 3.0)
    m = _tubo(z=(5, 24))
    d = descrever_mascara(m, sp)
    n_disco = int(m[:, :, 5].sum())
    assert d["n_voxels"] == n_disco * 20, d["n_voxels"]
    assert d["n_fatias"] == 20 and d["extensao_fatias"] == 20
    assert d["comprimento_z_mm"] == 60.0, d["comprimento_z_mm"]
    assert abs(d["volume_mL"] - n_disco * 20 * 6.0 / 1000) < 1e-12
    assert abs(d["area_mediana_mm2"] - n_disco * 2.0) < 1e-9
    assert d["campo_z_mm"] == 120.0

    # CONTROLE POSITIVO: descontinuidade em Z TEM que aparecer. Se a medida nao
    # separar "fatias com voxel" de "extensao do suporte", ela nao serve.
    dg = descrever_mascara(_tubo(z=(5, 24), gap=(10, 12)), sp)
    assert dg["n_fatias"] == 17 and dg["extensao_fatias"] == 20, dg
    assert dg["fatias_vazias_internas"] == 3, dg["fatias_vazias_internas"]
    assert d["fatias_vazias_internas"] == 0

    # mascara vazia nao inventa numero
    assert descrever_mascara(np.zeros((4, 4, 4), bool), sp)["volume_mL"] == NA

    # ---- decompor_variancia
    rng = np.random.default_rng(20260905)
    grupos = ["S1"] * 10 + ["S2"] * 10 + ["S3"] * 10

    # CONTROLE POSITIVO 1: efeito de grupo forte -> tem que DETECTAR
    com = np.concatenate([rng.normal(0, 1, 10), rng.normal(6, 1, 10), rng.normal(12, 1, 10)])
    a = decompor_variancia(com, grupos, n_perm=2000)
    assert a["ICC1"] > 0.8, a["ICC1"]
    assert a["eta2_entre_grupos"] > 0.8, a["eta2_entre_grupos"]
    assert a["p_permutacao"] < 0.01, a["p_permutacao"]
    assert a["veredito"].startswith("variacao ENTRE"), a["veredito"]
    assert a["razao_entre_sobre_dentro_robusta"] > 1.0

    # CONTROLE POSITIVO 2 (o que importa): SEM efeito de grupo, a metrica tem
    # que FALHAR em achar estrutura. Uma metrica que acusa instituicao em dado
    # embaralhado acusaria instituicao em qualquer coisa.
    sem = rng.normal(0, 1, 30)
    b = decompor_variancia(sem, grupos, n_perm=2000)
    assert b["ICC1"] < LIMIAR_ICC_ESTILO, b["ICC1"]
    assert b["p_permutacao"] > LIMIAR_P_PERMUTACAO, b["p_permutacao"]
    assert b["veredito"].startswith("variacao DENTRO"), b["veredito"]

    # CONTROLE POSITIVO 3: embaralhar os rotulos do dado COM efeito destroi o
    # efeito. Se nao destruir, a funcao esta lendo o valor, nao o rotulo.
    embaralhado = list(grupos)
    random.Random(7).shuffle(embaralhado)
    c = decompor_variancia(com, embaralhado, n_perm=2000)
    assert c["ICC1"] < a["ICC1"], (c["ICC1"], a["ICC1"])

    # degenerados nao explodem e nao inventam
    assert decompor_variancia([1.0] * 30, grupos, n_perm=10)["veredito"] == NA
    assert decompor_variancia([1.0, 2.0], ["S1", "S1"], n_perm=10)["veredito"] == NA
    # ICC(1) de grupos balanceados == eta2 corrigido: confere contra a definicao
    v = np.asarray(com); k, n = 3, 30
    ssb = sum(10 * (v[i:i + 10].mean() - v.mean()) ** 2 for i in (0, 10, 20))
    assert abs(a["SSB"] - ssb) < 1e-9, (a["SSB"], ssb)
    msb, msw = ssb / (k - 1), (a["SST"] - ssb) / (n - k)
    assert abs(a["ICC1"] - (msb - msw) / (msb + 9 * msw)) < 1e-9

    # ---- n_por_grupo_necessario: efeito grande pede n pequeno e vice-versa
    grande = n_por_grupo_necessario({"nome": "A", "media": 0.0, "sd": 1.0, "n": 10},
                                    {"nome": "B", "media": 2.0, "sd": 1.0, "n": 10})
    pequeno = n_por_grupo_necessario({"nome": "A", "media": 0.0, "sd": 1.0, "n": 10},
                                     {"nome": "B", "media": 0.2, "sd": 1.0, "n": 10})
    assert grande["n_por_grupo_necessario"] < pequeno["n_por_grupo_necessario"]
    # confere contra a formula a mao: d = 2 -> n = 2 (1,95996 + 0,84162)^2 / 4
    assert grande["n_por_grupo_necessario"] == math.ceil(
        2 * (Z_ALFA + Z_PODER) ** 2 / 4), grande
    assert n_por_grupo_necessario({"nome": "A", "media": 1.0, "sd": 0.0, "n": 10},
                                  {"nome": "B", "media": 1.0, "sd": 0.0, "n": 10}
                                  )["veredito"] == NA

    # ---- simular_divisoes: conservacao de casos e de voxels
    vox = {"S1": list(range(1, 11)), "S2": list(range(11, 21)), "S3": list(range(21, 31))}
    div = simular_divisoes(vox)
    assert len(div) == 10 and div[0]["n_treino"] == 30 and div[0]["n_validacao"] == 0
    assert div[0]["voxels_treino_min"] == div[0]["voxels_treino_max"] == sum(range(1, 31))
    for d_ in div:
        assert d_["n_treino"] + d_["n_validacao"] == 30
        assert d_["voxels_treino_min"] <= d_["voxels_treino_max"]
        assert sum(d_["treino_por_instituicao"].values()) == d_["n_treino"]
    # v=1 tirando o maior de cada instituicao: 30-10-20-30 = perde 60
    assert div[1]["voxels_treino_min"] == sum(range(1, 31)) - (10 + 20 + 30)
    assert div[1]["voxels_treino_max"] == sum(range(1, 31)) - (1 + 11 + 21)

    # ---- Tukey acha o outlier plantado e nao acha o que nao existe
    base = [{"case_id": f"c{i}", "instituicao": "S1", "volume_mL": 10.0 + i * 0.1}
            for i in range(20)]
    assert _extremos_tukey(base, "volume_mL")["n_fora"] == 0
    base.append({"case_id": "gordo", "instituicao": "S1", "volume_mL": 500.0})
    e = _extremos_tukey(base, "volume_mL")
    assert e["n_fora"] == 1 and e["casos"][0]["case_id"] == "gordo", e

    print("suficiencia_esofago.py: autoteste OK")


def _main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--autoteste" in argv:
        _autoteste()
        return 0
    raiz = RAIZ_PADRAO
    if "--raiz" in argv:
        raiz = Path(argv[argv.index("--raiz") + 1])
    r = rodar(raiz)
    gravar(r, raiz / "fase6" / "suficiencia")
    print("\n" + _summary_md(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
