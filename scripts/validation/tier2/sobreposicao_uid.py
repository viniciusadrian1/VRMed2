"""Sonda de SOBREPOSICAO DE UID entre as colecoes do TCIA (Fase 11).

Pergunta que o censo por colecao NAO consegue fazer:
  existe alguma colecao do TCIA que RE-ANOTA os mesmos exames de outra colecao?
  (segunda anotacao morando em outro nome de colecao, apontando para os
   mesmos StudyInstanceUID / SeriesInstanceUID)

E a pergunta irma:
  existe algum ESTUDO, em qualquer colecao, com >=2 structure sets?
  (o padrao S0819: dois observadores em ARQUIVOS separados, invisivel
   para quem so le ROIName dentro de um unico arquivo)

Nao baixa imagem. So getSeries (metadados), filtrado por modalidade de contorno.

  python -m scripts.validation.tier2.sobreposicao_uid --autoteste   # sem rede
  python -m scripts.validation.tier2.sobreposicao_uid               # re-roda de verdade
  python -m scripts.validation.tier2.sobreposicao_uid --de-cache    # so re-analisa

LIMITE DECLARADO: getSeries so enxerga o canal DICOM do NBIA. Anotacao
distribuida como ZIP de NIfTI fora do NBIA (PleThora, SAROS) e invisivel
para esta sonda POR CONSTRUCAO. Zero aqui nao e zero no TCIA.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):  # execucao direta: python sobreposicao_uid.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import tcia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / ".clinica-dados" / "fase11"
MODALIDADES_CONTORNO = ("RTSTRUCT", "SEG")


def _get(path: str, params: dict, tentativas: int = 3, timeout: int = 180):
    url = f"{tcia.BASE}/{path}?{urllib.parse.urlencode(params)}"
    ultimo = None
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (host fixo, https)
                bruto = r.read()
            return json.loads(bruto) if bruto.strip() else []
        except Exception as e:  # noqa: BLE001
            ultimo = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{path} {params} falhou: {ultimo}")


def colecoes() -> list[str]:
    return sorted(d["Collection"] for d in _get("getCollectionValues", {}))


def coletar() -> tuple[dict[str, list[dict]], dict[str, str]]:
    """colecao -> series de contorno (metadados crus da API). Toca a rede."""
    cols = colecoes()
    print(f"colecoes: {len(cols)}", flush=True)
    contornos: dict[str, list[dict]] = {}
    falhas: dict[str, str] = {}
    for i, c in enumerate(cols, 1):
        acc: list[dict] = []
        for m in MODALIDADES_CONTORNO:
            try:
                acc.extend(_get("getSeries", {"Collection": c, "Modality": m}))
            except Exception as e:  # noqa: BLE001
                falhas[f"{c}/{m}"] = repr(e)
        contornos[c] = acc
        print(f"[{i}/{len(cols)}] {c}: {len(acc)} series de contorno", flush=True)
    return contornos, falhas


def analisar(contornos: dict[str, list[dict]]) -> dict:
    """Funcao pura: so olha o dict de metadados. E o que o autoteste exercita."""
    # --- ATAQUE 1: mesmo UID em >=2 COLECOES diferentes ---
    por_campo: dict[str, dict[str, set[str]]] = {
        "StudyInstanceUID": defaultdict(set),
        "SeriesInstanceUID": defaultdict(set),
        "PatientID": defaultdict(set),
    }
    for c, series in contornos.items():
        for s in series:
            for campo, mapa in por_campo.items():
                if s.get(campo):
                    mapa[s[campo]].add(c)
    cruzados = {
        campo: {k: sorted(v) for k, v in mapa.items() if len(v) > 1}
        for campo, mapa in por_campo.items()
    }

    # --- ATAQUE 2: mesmo ESTUDO com >=2 structure sets, dentro da mesma colecao ---
    multi: list[dict] = []
    for c, series in contornos.items():
        por_estudo: dict[str, list[dict]] = defaultdict(list)
        for s in series:
            por_estudo[s.get("StudyInstanceUID", "?")].append(s)
        for est, ss in por_estudo.items():
            rt = [x for x in ss if x.get("Modality") == "RTSTRUCT"]
            sg = [x for x in ss if x.get("Modality") == "SEG"]
            if len(rt) >= 2 or len(sg) >= 2:
                multi.append(
                    {
                        "colecao": c,
                        "estudo": est,
                        "paciente": ss[0].get("PatientID"),
                        "n_rtstruct": len(rt),
                        "n_seg": len(sg),
                        "descricoes": sorted({str(x.get("SeriesDescription")) for x in ss}),
                        "uids_rtstruct": [x["SeriesInstanceUID"] for x in rt],
                        "uids_seg": [x["SeriesInstanceUID"] for x in sg],
                        "licenca": tcia.licenca(ss[0]),
                    }
                )

    resumo_multi: dict[str, dict] = {}
    for m in multi:
        d = resumo_multi.setdefault(
            m["colecao"],
            {"n_estudos_multi": 0, "max_rtstruct": 0, "max_seg": 0, "descricoes": set()},
        )
        d["n_estudos_multi"] += 1
        d["max_rtstruct"] = max(d["max_rtstruct"], m["n_rtstruct"])
        d["max_seg"] = max(d["max_seg"], m["n_seg"])
        d["descricoes"].update(m["descricoes"])
    for d in resumo_multi.values():
        d["descricoes"] = sorted(d["descricoes"])[:40]

    return {
        "n_colecoes": len(contornos),
        "colecoes": sorted(contornos),
        "n_series_de_contorno": sum(len(v) for v in contornos.values()),
        "colecoes_com_contorno": {c: len(v) for c, v in contornos.items() if v},
        "n_colecoes_com_contorno": sum(1 for v in contornos.values() if v),
        "ataque1_estudos_em_varias_colecoes": cruzados["StudyInstanceUID"],
        "ataque1_series_em_varias_colecoes": cruzados["SeriesInstanceUID"],
        "ataque1_pacientes_em_varias_colecoes": cruzados["PatientID"],
        "ataque2_n_colecoes_com_estudo_multi": len(resumo_multi),
        "ataque2_resumo_por_colecao": resumo_multi,
        "ataque2_estudos_multi": multi,
    }


def autoteste() -> None:
    """Controle positivo E negativo, sem rede. Falha ruidosamente se o crivo apodrecer."""
    def s(col, est, ser, mod, pac="P1"):
        return {
            "Collection": col, "StudyInstanceUID": est, "SeriesInstanceUID": ser,
            "Modality": mod, "PatientID": pac, "SeriesDescription": f"{mod} {ser}",
            "LicenseName": "CC BY 4.0", "LicenseURI": "u", "CollectionURI": "c",
        }

    contornos = {
        # positivo do ataque 1: MESMO estudo e MESMA serie em duas colecoes
        "ColA": [s("ColA", "E1", "S1", "RTSTRUCT")],
        "ColB": [s("ColB", "E1", "S1", "RTSTRUCT")],
        # positivo do ataque 2: um estudo com 2 RTSTRUCT e outro com 2 SEG
        "ColC": [
            s("ColC", "E2", "S2", "RTSTRUCT", "P2"),
            s("ColC", "E2", "S3", "RTSTRUCT", "P2"),
            s("ColC", "E3", "S4", "SEG", "P3"),
            s("ColC", "E3", "S5", "SEG", "P3"),
            # negativo: estudo com UM structure set so
            s("ColC", "E4", "S6", "RTSTRUCT", "P4"),
        ],
        # negativo do ataque 1: colecao sem contorno nenhum
        "ColD": [],
    }
    r = analisar(contornos)

    assert list(r["ataque1_estudos_em_varias_colecoes"]) == ["E1"], r["ataque1_estudos_em_varias_colecoes"]
    assert r["ataque1_estudos_em_varias_colecoes"]["E1"] == ["ColA", "ColB"]
    assert list(r["ataque1_series_em_varias_colecoes"]) == ["S1"]
    assert list(r["ataque1_pacientes_em_varias_colecoes"]) == ["P1"]
    assert r["n_colecoes_com_contorno"] == 3, r["n_colecoes_com_contorno"]
    assert r["n_series_de_contorno"] == 7

    estudos_multi = sorted(m["estudo"] for m in r["ataque2_estudos_multi"])
    assert estudos_multi == ["E2", "E3"], estudos_multi  # E4 (1 arquivo) NAO entra
    assert r["ataque2_n_colecoes_com_estudo_multi"] == 1
    assert r["ataque2_resumo_por_colecao"]["ColC"]["max_rtstruct"] == 2
    assert r["ataque2_resumo_por_colecao"]["ColC"]["max_seg"] == 2
    assert r["ataque2_estudos_multi"][0]["licenca"]["nome"] == "CC BY 4.0"

    # controle negativo puro: nada cruzado, nada multi
    vazio = analisar({"X": [s("X", "E9", "S9", "RTSTRUCT")]})
    assert vazio["ataque1_estudos_em_varias_colecoes"] == {}
    assert vazio["ataque2_estudos_multi"] == []

    print("autoteste: OK (2 positivos de ataque1, 2 de ataque2, 3 negativos)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autoteste", action="store_true", help="roda o autoteste e sai (sem rede)")
    ap.add_argument("--de-cache", action="store_true", help="re-analisa contornos_crus.json sem tocar a rede")
    ap.add_argument("--saida", type=Path, default=SAIDA)
    args = ap.parse_args(argv)

    if args.autoteste:
        autoteste()
        return

    autoteste()  # o crivo se prova antes de gastar rede
    args.saida.mkdir(parents=True, exist_ok=True)
    cru = args.saida / "contornos_crus.json"

    if args.de_cache:
        contornos = json.loads(cru.read_text(encoding="utf-8"))
        falhas, fonte = {}, f"cache local {cru}"
    else:
        contornos, falhas = coletar()
        cru.write_text(json.dumps(contornos, ensure_ascii=False), encoding="utf-8")
        fonte = f"{tcia.BASE} getCollectionValues + getSeries(Modality in {MODALIDADES_CONTORNO})"

    out = analisar(contornos)
    out["proveniencia"] = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": fonte,
        "python": sys.version.split()[0],
        "plataforma": platform.platform(),
        "script": str(Path(__file__).resolve().relative_to(RAIZ)),
        "limite_declarado": (
            "getSeries so ve o canal DICOM do NBIA. Anotacao publicada como ZIP de NIfTI "
            "fora do NBIA (PleThora, SAROS) e invisivel aqui por construcao."
        ),
    }
    out["falhas"] = falhas
    (args.saida / "sobreposicao_uid.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== ATAQUE 1 (mesmo UID em >=2 colecoes) ===", flush=True)
    print(f"estudos:   {len(out['ataque1_estudos_em_varias_colecoes'])}")
    print(f"series:    {len(out['ataque1_series_em_varias_colecoes'])}")
    print(f"pacientes: {len(out['ataque1_pacientes_em_varias_colecoes'])}")
    print(f"\n=== ATAQUE 2 (estudo com >=2 structure sets): {out['ataque2_n_colecoes_com_estudo_multi']} colecoes ===")
    for c, d in sorted(out["ataque2_resumo_por_colecao"].items()):
        print(f"  {c}: {d['n_estudos_multi']} estudos, max RTSTRUCT={d['max_rtstruct']}, max SEG={d['max_seg']}")
    print(f"\n{out['n_series_de_contorno']} series de contorno em {out['n_colecoes_com_contorno']}/{out['n_colecoes']} colecoes")


if __name__ == "__main__":
    main()
