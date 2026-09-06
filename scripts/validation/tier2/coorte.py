"""
Tier2 em COORTE — enumera, processa e agrega os 60 casos do LCTSC.

Tier2 mede a acuracia da SEGMENTACAO contra ground truth INDEPENDENTE. Na
decomposicao de erro (A = segmentacao, B = reconstrucao, C = simplificacao,
D = compressao) isto quantifica APENAS o bloco A. Os blocos NUNCA sao somados.

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

TRES ETAPAS, nesta ordem, cada uma retomavel:

  1. `enumerar()`   — API do TCIA -> manifest.json + cases.csv. Nao baixa imagem.
     Baixa so os RTSTRUCT (poucas centenas de KB cada) para registrar QUAIS ROIs
     existem em cada caso antes de processar qualquer coisa (Parte 6.8).
  2. `processar()`  — por caso: ingestao + TotalSegmentator + metricas. Pula o
     que ja esta feito; nunca rebaixa serie ja cacheada.
  3. `agregar()`    — distribuicao por estrutura (n, mediana, media, desvio,
     P5/P25/P75/P95, min, max, IC bootstrap) e ranking automatico de extremos.

REGRA DE AVALIACAO (Parte 10): a coorte e AVALIACAO, nao desenvolvimento.
Nenhum limiar, post-processing, parametro do TotalSegmentator ou regra de recorte
pode ser ajustado em funcao do que ela mostrar. Hipotese de melhoria vira
experimento separado, com split proprio.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import benchmark_tier2 as bench  # noqa: E402
from scripts.validation.tier2 import ingestao, mapeamento, rtstruct as rtst, tcia  # noqa: E402

COLECAO = "LCTSC"
RAIZ = Path(".clinica-dados/tier2/lctsc")
NM = "nao medido"

# Percentis publicados. Fixados aqui, antes da coorte rodar (Parte 18): escolher
# percentil depois de ver o resultado e p-hacking.
PERCENTIS = (5, 25, 50, 75, 95)
N_BOOTSTRAP = 2000
SEMENTE_BOOTSTRAP = 20260904  # fixa: o IC tem que ser reproduzivel

# Metricas que entram na estatistica de coorte. Ordem = ordem de publicacao.
METRICAS = (
    "dice", "iou", "nsd_1mm", "nsd_2mm", "nsd_1vox", "nsd_2vox",
    "hd95_mm", "assd_mm", "hd_mm", "volume_error_pct",
    "volume_pred_ml", "volume_gt_ml",
    "recall_gt", "precision_pred",
    "fp_fora_do_suporte_ml", "fp_dentro_do_suporte_ml", "fn_dentro_do_suporte_ml",
    "erro_absoluto_ml",
)

# Rankings gerados automaticamente. (coluna, maior_e_pior)
RANKINGS = (
    ("dice", False),            # menor Dice = pior
    ("hd95_mm", True),
    ("assd_mm", True),
    ("erro_absoluto_ml", True),
    ("fp_dentro_do_suporte_ml", True),
    ("fn_dentro_do_suporte_ml", True),
)
N_EXTREMOS = 5


# ------------------------------------------------------------------ 1. enumerar


def instituicao_de(case_id: str) -> str:
    """LCTSC-Train-S1-001 -> S1. O sufixo S1/S2/S3 identifica a instituicao de origem.

    Nao ha campo de instituicao na API; o codigo vem do proprio identificador, como
    a documentacao da colecao descreve. Registrado como derivado, nao como metadado
    lido — ver o campo `instituicao_origem` do manifesto.
    """
    partes = case_id.split("-")
    for p in partes:
        if p.startswith("S") and p[1:].isdigit():
            return p
    return NM


def enumerar(raiz: Path = RAIZ, baixar_rtstruct: bool = True, log=print) -> dict:
    """Monta manifest.json + cases.csv. Nao baixa imagem de CT."""
    series = tcia.listar_series(COLECAO)
    por_caso: dict[str, dict] = {}
    for s in series:
        cid = s["PatientID"]
        por_caso.setdefault(cid, {})[s.get("Modality")] = s

    casos = []
    for cid in sorted(por_caso):
        ct, rt = por_caso[cid].get("CT"), por_caso[cid].get("RTSTRUCT")
        lic = tcia.licenca(ct or rt or {})
        caso = {
            "case_id": cid,
            "instituicao_origem": instituicao_de(cid),
            "particao_original_do_desafio": "Train" if "-Train-" in cid else "Test",
            "modalidade": "CT + RTSTRUCT" if ct and rt else NM,
            "ct_series_uid": (ct or {}).get("SeriesInstanceUID", NM),
            "rtstruct_series_uid": (rt or {}).get("SeriesInstanceUID", NM),
            "study_uid": (ct or {}).get("StudyInstanceUID", NM),
            "n_imagens_ct": int((ct or {}).get("ImageCount") or 0) or NM,
            "tamanho_ct_bytes": int((ct or {}).get("FileSize") or 0) or NM,
            "fabricante_rtstruct": (rt or {}).get("Manufacturer", NM),
            "software_rtstruct": (rt or {}).get("SoftwareVersions", NM),
            # spacing so e conhecido depois de ler o DICOM; preenchido no processamento
            "spacing_mm": NM,
            "rois": NM,
            **{f"licenca_{k}": v for k, v in lic.items()},
        }
        casos.append(caso)

    if baixar_rtstruct:
        # Parte 6.8: registrar QUAIS ROIs existem em cada caso ANTES de processar.
        # O RTSTRUCT tem centenas de KB; e barato e evita descobrir no meio da coorte
        # que um caso nao anota o que se espera.
        for caso in casos:
            cid = caso["case_id"]
            destino = raiz / cid / "rtstruct"
            try:
                rt_serie = por_caso[cid].get("RTSTRUCT")
                if rt_serie is None:
                    caso["rois"] = "nao medido: sem serie RTSTRUCT"
                    continue
                tcia.baixar_serie(rt_serie, destino)
                arq = next(destino.glob("*.dcm"))
                caso["rois"] = sorted(rtst.listar_rois(arq))
                nao_mapeadas = [r for r in caso["rois"] if mapeamento.canonizar(r) is None]
                caso["rois_sem_mapeamento"] = nao_mapeadas
                log(f"  {cid}: {len(caso['rois'])} ROIs {caso['rois']}"
                    + (f"  (sem mapeamento: {nao_mapeadas})" if nao_mapeadas else ""))
            except Exception as e:  # um RTSTRUCT ilegivel nao derruba a enumeracao
                caso["rois"] = f"nao medido: {type(e).__name__}: {e}"
                log(f"  {cid}: ROIs nao lidas — {e}")

    manifesto = {
        "colecao": COLECAO,
        "tier": "Tier2 — acuracia da segmentacao contra ground truth independente",
        "bloco_da_decomposicao": "A (segmentacao). Nunca somado a B/C/D.",
        "n_casos": len(casos),
        "instituicoes": sorted({c["instituicao_origem"] for c in casos}),
        # CORRIGIDO na Fase 16. A versao anterior afirmava que o task `total` foi
        # treinado "exclusivamente em TCs clinicas do University Hospital Basel, sem
        # datasets publicos de desafio — o LCTSC nao esta no treino". As tres partes
        # eram falsas ou indemonstraveis, e o campo se chama PROVENIENCIA: era o
        # ultimo lugar do repositorio que ainda EMITIA a afirmacao, por maquina.
        # A correcao fica no GERADOR, e nao so no manifest, porque a correcao
        # equivalente da Fase 9 foi feita so no documento e a regeneracao a desfaria.
        "proveniencia_gt": (
            "RTSTRUCT de contorno de radioterapia do LCTSC (2017), anotacao humana de "
            "tres instituicoes. NAO e saida de TotalSegmentator, de nnU-Net nem de "
            "pseudo-rotulagem. INDEPENDENCIA EM RELACAO AO TREINO DO BASELINE: "
            "INDETERMINADA. O TotalSegmentator v2 declara 1.559 imagens de treino e o "
            "autor afirma verbatim que nao publicou os sujeitos adicionais: 420 (26,9%) "
            "sao nao atribuidos. Nao existe splits_final.json nem lista de casos no "
            "pacote distribuido, e o modelo publicado e fold=0, entao nem as 1.139 "
            "imagens publicas sao atribuiveis ao treino efetivo. Sonda geometrica "
            "calibrada (Fase 16): 3/60 acertos contra nulo de 2,40 (p=0,502) — sem "
            "excesso sobre o acaso, teto <=4/60 num unico canal. ISSO NAO E PROVA DE "
            "INDEPENDENCIA: e um teto medido num canal, cego ao canal documental."
        ),
        "independencia_gt_vs_treino_do_baseline": "INDETERMINADA",
        "independencia_teto_medido": (
            "<=4 de 60 series no canal de forma geometrica; ver "
            "docs/RELATORIO-FASE16-INDEPENDENCIA-BASELINE.md"
        ),
        "casos": casos,
    }
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "manifest.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")

    campos = [c for c in casos[0] if c != "rois"] + ["rois"]
    with (raiz / "cases.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for c in casos:
            w.writerow({**c, "rois": ";".join(c["rois"]) if isinstance(c["rois"], list) else c["rois"]})

    log(f"manifesto: {len(casos)} casos, instituicoes {manifesto['instituicoes']}")
    return manifesto


# ------------------------------------------------------------------ 2. processar


def _feito(raiz: Path, caso: str) -> bool:
    """Ja processado = existe linha de resultado deste caso."""
    p = raiz / caso / "tier2_caso.json"
    return p.exists() and p.stat().st_size > 0


def processar(
    casos: list[str] | None = None, raiz: Path = RAIZ, refazer: bool = False, log=print
) -> dict:
    """Roda ingestao + metricas para cada caso. Retomavel: pula o que ja terminou."""
    manifesto_path = raiz / "manifest.json"
    if not manifesto_path.exists():
        raise FileNotFoundError(f"rode enumerar() primeiro: {manifesto_path} nao existe")
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    todos = [c["case_id"] for c in manifesto["casos"]]
    alvo = casos or todos

    feitos, pulados, falhos = [], [], []
    for i, cid in enumerate(alvo, 1):
        if not refazer and _feito(raiz, cid):
            pulados.append(cid)
            log(f"[{i}/{len(alvo)}] {cid}: ja processado — pulado")
            continue
        log(f"[{i}/{len(alvo)}] {cid}: ingerindo...")
        try:
            ingestao.ingerir(cid, raiz=raiz, log=lambda *a: None)
            r = bench.rodar(cid, raiz=raiz, log=lambda *a: None)
            (raiz / cid / "tier2_caso.json").write_text(
                json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            feitos.append(cid)
            # `erro` vem como string VAZIA quando nao houve erro, nao como None —
            # testar `is None` fazia o log dizer "0 linhas com metrica" enquanto o
            # arquivo tinha 12. Bug so do contador; os dados sempre estiveram certos.
            n_ok = sum(1 for l in r["linhas"] if not l.get("erro") and isinstance(l.get("dice"), float))
            log(f"[{i}/{len(alvo)}] {cid}: OK ({n_ok} linhas com metrica)")
        except Exception as e:
            falhos.append({"case_id": cid, "erro": f"{type(e).__name__}: {e}",
                           "traceback": traceback.format_exc()[-2000:]})
            log(f"[{i}/{len(alvo)}] {cid}: FALHOU — {type(e).__name__}: {e}")

    resumo = {"feitos": feitos, "pulados": pulados, "falhos": falhos,
              "n_feitos": len(feitos), "n_pulados": len(pulados), "n_falhos": len(falhos)}
    (raiz / "processamento.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"processados {len(feitos)}, pulados {len(pulados)}, falhos {len(falhos)}")
    return resumo


# ------------------------------------------------------------------ 3. agregar


def _numeros(valores) -> list[float]:
    """So float finito entra na estatistica. String ('nao medido', 'invalido') fica fora."""
    out = []
    for v in valores:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        f = float(v)
        if np.isfinite(f):
            out.append(f)
    return out


def _ic_bootstrap(xs: list[float], nivel: float = 0.95) -> dict:
    """IC percentil da MEDIANA por bootstrap. Requer n >= 5.

    Bootstrap e nao-parametrico: nao assume normalidade, que nao vale para Dice
    (limitado em 1) nem para HD95 (cauda longa). Abaixo de n=5 o IC nao e
    reportado — com poucos casos o intervalo e mais artefato do reamostrador do
    que informacao sobre a coorte.
    """
    n = len(xs)
    if n < 5:
        return {"ic95_mediana": f"nao medido: n={n} < 5"}
    rng = np.random.default_rng(SEMENTE_BOOTSTRAP)
    arr = np.asarray(xs, dtype=float)
    medianas = np.median(rng.choice(arr, size=(N_BOOTSTRAP, n), replace=True), axis=1)
    lo, hi = np.percentile(medianas, [(1 - nivel) / 2 * 100, (1 + nivel) / 2 * 100])
    return {"ic95_mediana": [round(float(lo), 4), round(float(hi), 4)],
            "metodo_ic": f"bootstrap percentil, {N_BOOTSTRAP} reamostragens, semente {SEMENTE_BOOTSTRAP}"}


def _dist(xs: list[float]) -> dict:
    """Distribuicao de uma metrica. Arredondada a 4 casas: nao inventar precisao."""
    n = len(xs)
    if n == 0:
        return {"n": 0, "mediana": NM}
    d: dict[str, Any] = {"n": n, "mediana": round(statistics.median(xs), 4),
                         "media": round(statistics.fmean(xs), 4),
                         "min": round(min(xs), 4), "max": round(max(xs), 4)}
    d["desvio"] = round(statistics.stdev(xs), 4) if n >= 2 else f"nao medido: n={n} < 2"
    for p in PERCENTIS:
        d[f"p{p}"] = round(float(np.percentile(xs, p)), 4)
    d.update(_ic_bootstrap(xs))
    return d


def carregar_linhas(raiz: Path = RAIZ) -> list[dict]:
    """Junta as linhas de todos os casos processados."""
    linhas = []
    for p in sorted(raiz.glob("*/tier2_caso.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        linhas.extend(r.get("linhas", []))
    return linhas


def agregar(raiz: Path = RAIZ, log=print) -> dict:
    """Distribuicao por (estrutura, variante) + ranking automatico de extremos."""
    linhas = carregar_linhas(raiz)
    if not linhas:
        raise RuntimeError("nenhuma linha: rode processar() primeiro")

    casos = sorted({l["case_id"] for l in linhas})
    chaves = sorted({(l["gt_roi_name"], l["variante"]) for l in linhas
                     if isinstance(l.get("dice"), float)})

    dist: dict[str, dict] = {}
    for roi, variante in chaves:
        sel = [l for l in linhas if l["gt_roi_name"] == roi and l["variante"] == variante]
        bloco = {"n_casos": len({l["case_id"] for l in sel}),
                 "estruturas_totalsegmentator": sel[0].get("structure", NM)}
        for m in METRICAS:
            bloco[m] = _dist(_numeros([l.get(m) for l in sel]))
        dist[f"{roi}|{variante}"] = bloco

    # Ranking automatico (Parte 9): gerado por ordenacao, nunca por escolha manual.
    rankings: dict[str, dict] = {}
    for roi, variante in chaves:
        sel = [l for l in linhas if l["gt_roi_name"] == roi and l["variante"] == variante]
        r: dict[str, Any] = {}
        for coluna, maior_e_pior in RANKINGS:
            com_valor = [l for l in sel if isinstance(l.get(coluna), (int, float))
                         and np.isfinite(float(l[coluna]))]
            if not com_valor:
                r[coluna] = NM
                continue
            ordenado = sorted(com_valor, key=lambda l: float(l[coluna]), reverse=maior_e_pior)
            r[coluna] = {
                "piores": [{"case_id": l["case_id"], coluna: round(float(l[coluna]), 4)}
                           for l in ordenado[:N_EXTREMOS]],
                "melhores": [{"case_id": l["case_id"], coluna: round(float(l[coluna]), 4)}
                             for l in ordenado[-N_EXTREMOS:][::-1]],
            }
        rankings[f"{roi}|{variante}"] = r

    # Estruturas sem cobertura no dataset: continuam "nao medido", nunca estimadas.
    sem_cobertura = sorted({l["structure"] for l in linhas
                            if l.get("gt_roi_name") == bench.SEM_COBERTURA})

    saida = {
        "tier": "Tier2 — bloco A da decomposicao. Nunca somado a B/C/D.",
        "n_casos_processados": len(casos),
        "casos": casos,
        "percentis_publicados": list(PERCENTIS),
        "distribuicao": dist,
        "rankings": rankings,
        "sem_cobertura_no_dataset": sem_cobertura,
        "nota_estatistica": (
            "IC de mediana por bootstrap percentil, nao-parametrico. Nenhuma metrica foi "
            "escolhida depois de ver o resultado: METRICAS, PERCENTIS e RANKINGS estao "
            "fixados no topo do modulo. Linguagem de conclusao segue a Parte 18 — "
            "'observado', 'consistente', 'sem evidencia de diferenca'."
        ),
    }
    destino = raiz / "resultados"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "coorte.json").write_text(
        json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")

    # CSV plano: uma linha por (estrutura, variante, metrica)
    with (destino / "coorte.csv").open("w", newline="", encoding="utf-8") as f:
        campos = ["gt_roi_name", "variante", "metrica", "n", "mediana", "media", "desvio",
                  *[f"p{p}" for p in PERCENTIS], "min", "max", "ic95_lo", "ic95_hi"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for chave, bloco in dist.items():
            roi, variante = chave.split("|")
            for m in METRICAS:
                d = bloco[m]
                ic = d.get("ic95_mediana")
                w.writerow({
                    "gt_roi_name": roi, "variante": variante, "metrica": m,
                    **{k: d.get(k, "") for k in ("n", "mediana", "media", "desvio", "min", "max")},
                    **{f"p{p}": d.get(f"p{p}", "") for p in PERCENTIS},
                    "ic95_lo": ic[0] if isinstance(ic, list) else ic,
                    "ic95_hi": ic[1] if isinstance(ic, list) else "",
                })
    log(f"agregado: {len(casos)} casos, {len(chaves)} pares (estrutura, variante)")
    return saida


# ------------------------------------------------------------------ CLI


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tier2 em coorte (LCTSC)")
    ap.add_argument("etapa", choices=("enumerar", "processar", "agregar", "tudo"))
    ap.add_argument("--raiz", type=Path, default=RAIZ)
    ap.add_argument("--casos", nargs="*", default=None, help="subconjunto de case_id")
    ap.add_argument("--refazer", action="store_true")
    ap.add_argument("--sem-rtstruct", action="store_true",
                    help="enumerar sem baixar RTSTRUCT (nao registra ROIs por caso)")
    a = ap.parse_args(argv)

    if a.etapa in ("enumerar", "tudo"):
        enumerar(a.raiz, baixar_rtstruct=not a.sem_rtstruct)
    if a.etapa in ("processar", "tudo"):
        processar(a.casos, a.raiz, refazer=a.refazer)
    if a.etapa in ("agregar", "tudo"):
        agregar(a.raiz)
    return 0


def _autoteste() -> None:
    """Checks que falham se a estatistica ou o ranking pararem de funcionar."""
    # instituicao vem do identificador
    assert instituicao_de("LCTSC-Train-S1-001") == "S1"
    assert instituicao_de("LCTSC-Test-S3-201") == "S3"
    assert instituicao_de("SEM-CODIGO") == NM

    # strings ('nao medido', 'invalido') nunca entram na estatistica
    assert _numeros([1.0, "nao medido", None, 2.0, float("nan"), True]) == [1.0, 2.0]

    # distribuicao: mediana, percentis e min/max coerentes
    d = _dist([1.0, 2.0, 3.0, 4.0, 5.0])
    assert d["n"] == 5 and d["mediana"] == 3.0 and d["min"] == 1.0 and d["max"] == 5.0
    assert isinstance(d["ic95_mediana"], list), d
    # com n < 5 o IC nao e reportado como numero
    assert isinstance(_dist([1.0, 2.0])["ic95_mediana"], str)
    # com n = 1 nao ha desvio
    assert isinstance(_dist([7.0])["desvio"], str)

    # bootstrap reproduzivel: mesma entrada, mesmo IC
    assert _dist([1.0, 2.0, 3.0, 4.0, 5.0])["ic95_mediana"] == d["ic95_mediana"]

    # o IC da mediana tem que CONTER a mediana
    lo, hi = d["ic95_mediana"]
    assert lo <= d["mediana"] <= hi, (lo, d["mediana"], hi)

    print("coorte.py: autoteste OK")


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(_main())
