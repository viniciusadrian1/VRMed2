"""
Fase 5 — infraestrutura da investigacao de melhoria da SEGMENTACAO (bloco A).

Este modulo NAO roda experimento. Ele fixa as tres coisas que precisam existir
ANTES de qualquer experimento, para que nenhuma decisao possa ser tomada depois
de ver o resultado:

  1. A_BASELINE_V1  — a referencia congelada (o que produziu a coorte publicada)
  2. SPLIT          — development / validation / test, deterministico
  3. CRITERIOS      — limiares de melhoria e de regressao, declarados aqui

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

------------------------------------------------------------------------------
HONESTIDADE SOBRE O SPLIT (leia antes de confiar no holdout)

A coorte de 60 casos JA FOI medida e publicada antes deste split existir. Eu ja
vi a distribuicao inteira do baseline. Isso significa que o holdout aqui NAO e
um holdout puro no sentido forte — ele nao protege contra conhecimento previo da
DIFICULDADE dos casos.

O que ele protege, e que e o que importa nesta fase: nenhuma INTERVENCAO foi
inventada ainda. As medidas do baseline sao anteriores a qualquer regra de
pos-processamento, entao o conjunto de teste continua sendo dado que nunca foi
usado para ESCOLHER ou AJUSTAR uma intervencao. E essa a propriedade que faz o
holdout valer alguma coisa aqui.

Consequencia pratica declarada: um resultado que sobrevive ao teste e evidencia
de que a intervencao generaliza entre casos; NAO e evidencia de que ela
generaliza para outra coorte, outro dataset ou outra instituicao.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(".clinica-dados/tier2/lctsc")
NM = "nao medido"

# ---------------------------------------------------------------- 1. baseline


# Congelado em 2026-09-04. Reproduz exatamente o que gerou a coorte publicada em
# docs/RELATORIO-TIER2-COORTE.md. NENHUM experimento da Fase 5 pode sobrescrever
# estes valores; um experimento muda UMA coisa e declara qual.
A_BASELINE_V1: dict[str, Any] = {
    "id": "A_BASELINE_V1",
    "congelado_em": "2026-09-04",
    "produziu": "docs/RELATORIO-TIER2-COORTE.md (60 casos LCTSC)",
    "modelo": {
        "TotalSegmentator": "2.18.0",
        "task": "total",
        "pesos": "os distribuidos com a versao 2.18.0 (nao ha checkpoint local no repo)",
        "roi_subset": "as 8 estruturas de mapeamento.roi_subset()",
    },
    "parametros_de_inferencia": {
        # de scripts/clinica/segmentacao.py::rodar_segmentacao — os MESMOS da producao
        "fast": False,               # resolucao cheia; --fast seria 3 mm, --fastest 6 mm
        "higher_order_resampling_LEGACY": True,
        "robust_crop": True,
        "quiet": False,
        "device": "GPU",
    },
    "preprocessing": (
        "NENHUM alem do que o proprio TotalSegmentator faz internamente. A entrada e "
        "exatamente o gt/image.nii.gz gravado pelo dcmrtstruct2nii a partir da serie "
        "DICOM de referencia — sem reamostragem, recorte ou normalizacao nossa."
    ),
    "postprocessing": (
        "NENHUM. Auditado: scripts/geometry/mask_processing.py::processar_mascara NAO e "
        "chamada em nenhum ponto do caminho Tier2. A predicao avaliada e a saida CRUA do "
        "TotalSegmentator. Isto e o que torna os experimentos da Fase 5 aditivos."
    ),
    "ambiente": {
        "python": "3.13.11 (.venv-pipeline)",
        "torch": "2.6.0+cu124",
        "cuda": "12.4 (via torch cu124)",
        "numpy": "2.5.2", "scipy": "1.18.1", "nibabel": "5.4.2",
        "SimpleITK": "2.5.6", "pydicom": "3.0.2", "scikit-image": "0.26.0",
        "dcmrtstruct2nii": "5",
    },
    "codigo": {
        "segmentacao": "scripts/clinica/segmentacao.py::rodar_segmentacao",
        "ingestao": "scripts/validation/tier2/ingestao.py::ingerir",
        "metricas": "scripts/validation/tier2/benchmark_tier2.py::rodar",
        "nota": "o hash sha256 do arquivo que produziu cada predicao vai gravado por linha",
    },
}


# ------------------------------------------------------------------- 2. split


SEMENTE_SPLIT = "vrmed-fase5-2026-09-04"  # fixa; trocar isto invalida o holdout
PROPORCAO = {"development": 10, "validation": 5, "test": 5}  # POR INSTITUICAO


def _ordem_deterministica(case_id: str) -> str:
    """Chave de ordenacao estavel e independente do nome — nao da para escolher caso.

    sha256(semente + case_id). Nao usa random com semente porque a ordem do
    `random` depende da ordem de iteracao; o hash depende so do identificador.
    """
    return hashlib.sha256(f"{SEMENTE_SPLIT}|{case_id}".encode()).hexdigest()


def instituicao_de(case_id: str) -> str:
    for p in case_id.split("-"):
        if p.startswith("S") and p[1:].isdigit():
            return p
    return NM


def construir_split(case_ids: list[str]) -> dict[str, list[str]]:
    """development / validation / test, ESTRATIFICADO por instituicao.

    Estratificado porque instituicao e a maior fonte de variacao medida na coorte
    (amplitude de 0,13 de Dice na medula) e porque instituicao e spacing estao
    confundidos em S1 e S2 — um split desbalanceado mediria instituicao, nao
    intervencao.
    """
    por_inst: dict[str, list[str]] = {}
    for cid in case_ids:
        por_inst.setdefault(instituicao_de(cid), []).append(cid)

    split: dict[str, list[str]] = {k: [] for k in PROPORCAO}
    for inst in sorted(por_inst):
        ordenados = sorted(por_inst[inst], key=_ordem_deterministica)
        i = 0
        for nome, n in PROPORCAO.items():
            split[nome].extend(ordenados[i:i + n])
            i += n
        if i < len(ordenados):  # sobra vai para development, o unico que pode crescer
            split["development"].extend(ordenados[i:])
    return {k: sorted(v) for k, v in split.items()}


# --------------------------------------------------------------- 3. criterios


# Limiares DECLARADOS ANTES de qualquer experimento (Parte 12). Escolher limiar
# depois de ver o resultado e p-hacking; estes ficam aqui, versionados.
#
# 0,01 de Dice: e a menor diferenca que a coorte consegue distinguir com folga.
# Referencia empirica: os IC 95 % da mediana publicados tem meia-largura de
# 0,005 (Lung_R) a 0,031 (SpinalCord). Um efeito abaixo de 0,01 esta dentro do
# IC de metade das estruturas e nao e discriminavel com n desta ordem.
LIMIAR_MELHORIA_DICE = 0.01
LIMIAR_REGRESSAO_DICE = 0.01     # simetrico de proposito: nao aceitar assimetria
LIMIAR_REGRESSAO_HD95_MM = 1.0   # ~1 voxel no plano; abaixo disso e ruido de grade
LIMIAR_REGRESSAO_VOLUME_PCT = 2.0

# Estruturas que servem de CONTROLE DE NAO REGRESSAO (Parte 15), nunca de alvo.
CONTROLES = ("Lung_R", "Lung_L")
# Alvos permitidos nesta fase, em ordem de prioridade (Parte 2).
ALVOS = ("SpinalCord", "Esophagus")
# NAO e alvo: divergencia de definicao nao harmonizada (Parte 14).
NAO_OTIMIZAR = {
    "Heart": (
        "o GT inclui saco pericardico e gordura pericardica (atlas RTOG 1106) e o "
        "`heart` do TotalSegmentator nao inclui pericardio. O coracao NAO e alvo de "
        "otimizacao enquanto a definicao anatomica entre previsao e GT nao estiver "
        "harmonizada — ajustar o modelo para reproduzir outra definicao sem uma "
        "ontologia de estruturas seria otimizar contra um alvo que nao e o dele."
    ),
}

# Taxonomia de erro (Parte 1). Todo experimento declara qual tipo pretende reduzir.
TAXONOMIA = {
    "E1": "extensao indevida — a predicao continua alem de onde a estrutura foi contornada",
    "E2": "estrutura mais estreita — a predicao e sistematicamente mais fina que o GT",
    "E3": "deslocamento de fronteira — casca fina espalhada, sem bloco localizado",
    "E4": "falso positivo localizado — bloco de FP concentrado numa regiao",
    "E5": "falso negativo localizado — bloco de FN concentrado numa regiao",
    "E6": "divergencia de definicao do GT — o desacordo e de especificacao, nao erro",
    "E7": "artefato de aquisicao/spacing — o erro acompanha a grade, nao a anatomia",
    "E8": "caso anomalo — o caso destoa da coorte por motivo proprio",
}


def gravar(raiz: Path = RAIZ, log=print) -> dict:
    """Grava fase5_baseline.json + fase5_split.json. Recusa sobrescrever split existente."""
    manifesto = json.loads((raiz / "manifest.json").read_text(encoding="utf-8"))
    case_ids = [c["case_id"] for c in manifesto["casos"]]
    split = construir_split(case_ids)

    destino = raiz / "fase5"
    destino.mkdir(parents=True, exist_ok=True)

    p_split = destino / "split.json"
    if p_split.exists():
        antigo = json.loads(p_split.read_text(encoding="utf-8"))
        if antigo.get("split") != split:
            raise RuntimeError(
                "split.json ja existe e DIFERE do que seria gerado agora. Regerar um "
                "split depois de rodar experimento invalida o holdout. Apague o arquivo "
                "de proposito se souber o que esta fazendo."
            )
        log("split.json ja existe e confere — nao reescrito")
    else:
        p_split.write_text(json.dumps({
            "semente": SEMENTE_SPLIT,
            "metodo": "sha256(semente|case_id), estratificado por instituicao",
            "proporcao_por_instituicao": PROPORCAO,
            "ressalva": (
                "a coorte de 60 casos foi medida e publicada ANTES deste split. O holdout "
                "protege contra ajustar intervencao no dado de teste — nao contra "
                "conhecimento previo da dificuldade dos casos. Ver docstring do modulo."
            ),
            "split": split,
            "n": {k: len(v) for k, v in split.items()},
            "por_instituicao": {
                k: {i: sum(1 for c in v if instituicao_de(c) == i) for i in ("S1", "S2", "S3")}
                for k, v in split.items()
            },
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"split gravado: {[(k, len(v)) for k, v in split.items()]}")

    (destino / "baseline.json").write_text(json.dumps({
        **A_BASELINE_V1,
        "criterios": {
            "limiar_melhoria_dice": LIMIAR_MELHORIA_DICE,
            "limiar_regressao_dice": LIMIAR_REGRESSAO_DICE,
            "limiar_regressao_hd95_mm": LIMIAR_REGRESSAO_HD95_MM,
            "limiar_regressao_volume_pct": LIMIAR_REGRESSAO_VOLUME_PCT,
            "declarados_antes_de_qualquer_experimento": True,
        },
        "alvos": list(ALVOS),
        "controles_de_nao_regressao": list(CONTROLES),
        "nao_otimizar": NAO_OTIMIZAR,
        "taxonomia_de_erro": TAXONOMIA,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    log("baseline.json gravado")
    return {"split": split, "baseline": A_BASELINE_V1}


def carregar_split(raiz: Path = RAIZ) -> dict[str, list[str]]:
    return json.loads((raiz / "fase5" / "split.json").read_text(encoding="utf-8"))["split"]


def _autoteste() -> None:
    """Checks que falham se o split deixar de ser deterministico ou estratificado."""
    casos = [f"LCTSC-{p}-S{i}-{n:03d}"
             for i in (1, 2, 3) for p in ("Train", "Test") for n in range(1, 11)]
    a = construir_split(casos)
    b = construir_split(list(reversed(casos)))
    assert a == b, "split depende da ordem de entrada — nao e deterministico"

    todos = [c for v in a.values() for c in v]
    assert len(todos) == len(set(todos)) == len(casos), "caso repetido ou perdido no split"

    for nome, esperado in PROPORCAO.items():
        for inst in ("S1", "S2", "S3"):
            n = sum(1 for c in a[nome] if instituicao_de(c) == inst)
            if nome == "development":
                assert n >= esperado, (nome, inst, n)
            else:
                assert n == esperado, f"{nome}/{inst}: {n} != {esperado} — nao estratificado"

    # trocar a semente TEM que mudar o split (senao a semente nao esta em uso)
    import scripts.validation.tier2.fase5 as m
    orig = m.SEMENTE_SPLIT
    try:
        m.SEMENTE_SPLIT = "outra-semente"
        assert m.construir_split(casos) != a, "a semente nao afeta o split"
    finally:
        m.SEMENTE_SPLIT = orig

    assert "Heart" in NAO_OTIMIZAR and set(CONTROLES).isdisjoint(ALVOS)
    print("fase5.py: autoteste OK")


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        gravar()
