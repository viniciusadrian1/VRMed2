"""Consolida a Fase 11 em DADO: dossie.json + manifesto_uid.json.

Tres coisas que a fase nao tinha e o critico cobrou:

  1. FICHAS COMO DADO. As 24 fichas de fonte primaria da 1a onda viviam em prosa,
     dentro do transcript. Aqui elas viram um JSON estruturado, extraido do
     PROPRIO transcript (nao redigitado por ninguem), com a contestacao do arm
     cetico anexada a cada candidato que foi contestado.
  2. CONTRADICOES RESOLVIDAS POR MEDICAO. Tres pontos em que ficha e dossie se
     contradiziam foram remedidos em disco. Cada um sai com `versao_que_vale`.
  3. MANIFESTO DE UID. O que foi lido, de onde, quando: uma linha por serie
     baixada, a partir do marcador `_tcia_serie.json` que tcia.baixar_serie grava.

  python -m scripts.validation.tier2.dossie_fase11 --autoteste
  python -m scripts.validation.tier2.dossie_fase11

LIMITES DECLARADOS
- A evidencia verbatim das fichas ja vinha TRUNCADA pelo agente que a reportou
  (termina em "[...]"). O campo `evidencia_truncada` marca isso caso a caso; o
  dossie nao inventa o que falta.
- O manifesto NAO carrega checksum: sao ~13,7 mil series e ~37 GB de DICOM.
  A identidade por linha e SeriesInstanceUID + n_arquivos + bytes + mtime.
  # ponytail: sem sha256 no volume todo; se um dia precisar de prova de bit,
  # hashear so as series citadas como evidencia nas fichas.
- Sem o transcript da 1a onda em disco, as fichas nao sao regeneraveis: o script
  cai para o `fichas_1a_onda.json` ja congelado e diz isso na proveniencia.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]
FASE11 = RAIZ / ".clinica-dados" / "fase11"
CENSO_TIER2 = RAIZ / ".clinica-dados" / "tier2" / "censo"
TRANSCRIPT = (
    Path.home() / ".claude" / "projects" / "C--Users-vinic-Downloads-InnerVision"
    / "25590899-20fd-4398-869f-48a0e90bae78.jsonl"
)

# ---------------------------------------------------------------- fichas

_CABECALHO = re.compile(
    r"\[(ELIMINADO|INDETERMINADO|VALIDO)\] (.{3,400}?)\s*\|\s*elimina:\s*(.*?)\s*\|\s*tipo:\s*(.*?)\s*"
    r"\|\s*fonte aberta:\s*(\w+)\s*\n\s*obs=(\d+) casos=(\d+) contornos=(\d+)\s*\n(.*)",
    re.S,
)
_CONTESTACAO = re.compile(
    r"\[(ENFRAQUECIDA|SOBREVIVE|REFUTADA)\] (.{5,300}?)\n\s{4,}(.{20,1200}?)(?=\n\s*\[|\n\n|$)", re.S
)


def _desescapar(linha: str) -> str:
    return linha.replace("\\r\\n", "\n").replace("\\n", "\n").replace('\\"', '"')


def extrair_fichas(transcript: Path) -> tuple[list[dict], list[dict]]:
    """Le as fichas e as contestacoes do transcript da 1a onda. Nada e redigitado."""
    fichas: dict[str, dict] = {}
    contestacoes: dict[str, dict] = {}
    for linha in transcript.open(encoding="utf-8"):
        txt = _desescapar(linha)
        for m in re.finditer(r"\[(?:ELIMINADO|INDETERMINADO|VALIDO)\] ", txt):
            mm = _CABECALHO.match(txt[m.start(): m.start() + 3000])
            if not mm:
                continue
            nome = mm.group(2).strip()
            if nome in fichas:
                continue
            ev = re.split(r"\n\[(?:ELIMINADO|INDETERMINADO|VALIDO)\]|\",\"is_error\"|\n\n", mm.group(9))[0].strip()
            fichas[nome] = {
                "candidato": nome,
                "veredito": mm.group(1),
                "filtro_que_elimina": mm.group(3),
                "tipo_declarado": mm.group(4),
                "fonte_aberta": mm.group(5) == "True",
                "n_observadores_declarados": int(mm.group(6)),
                "n_contornos_declarados": int(mm.group(8)),
                "evidencia_verbatim": ev[:1500],
                "evidencia_truncada": ev.rstrip().endswith("[...]"),
            }
        for mm in _CONTESTACAO.finditer(txt):
            alvo = mm.group(2).strip()
            if alvo in contestacoes:
                continue
            contestacoes[alvo] = {
                "resultado_do_ataque": mm.group(1),
                "afirmacao_atacada": alvo,
                "o_que_ficou": mm.group(3).strip()[:1500],
            }
    return list(fichas.values()), list(contestacoes.values())


# Candidatos citados pelo arm cetico que NAO tem ficha no formato padrao.
# Ficam aqui para que a contestacao deles nao seja descartada como ruido de outra fase.
SEM_FICHA_PADRAO = [
    "google-deepmind/tcia-ct-scan-dataset",
    "Mediastinal-Lymph-Node-SEG",
    "Pediatric-CT-SEG",
    "iCurveE",
]


def casar_contestacoes(fichas: list[dict], contestacoes: list[dict]) -> None:
    """Anexa cada contestacao ao candidato cujo nome ela cita.

    O transcript tem contestacoes de TODAS as fases do projeto. Sem casar com um
    candidato da fase 11, a contestacao nao entra no dossie da fase 11 — vai para
    o balde `nao_casadas`, que o main mantem separado e rotulado.
    """
    for c in contestacoes:
        c["casada_com"] = []
        alvo = c["afirmacao_atacada"].lower()
        for f in fichas:
            chave = re.split(r"[ (—/]", f["candidato"])[0]
            if len(chave) >= 5 and chave.lower() in alvo:
                f.setdefault("contestacoes", []).append(c["resultado_do_ataque"] + ": " + c["afirmacao_atacada"])
                c["casada_com"].append(f["candidato"])
        for nome in SEM_FICHA_PADRAO:
            if nome.lower() in alvo:
                c["casada_com"].append(nome + " (candidato SEM ficha no formato padrao)")


# ---------------------------------------------------------------- medicoes

def _rtstructs(raiz: Path):
    import pydicom

    for p in sorted(raiz.rglob("*.dcm")):
        ds = pydicom.dcmread(str(p), stop_before_pixels=True, specific_tags=[(0x0008, 0x0060)])
        if getattr(ds, "Modality", None) == "RTSTRUCT":
            yield p, pydicom.dcmread(str(p), stop_before_pixels=True)


def _rois_e_pontos(ds) -> dict[str, tuple[int, int]]:
    """ROIName -> (n_fatias com contorno, n_pontos). ROI sem geometria sai (0, 0)."""
    num2nome = {r.ROINumber: str(r.ROIName) for r in getattr(ds, "StructureSetROISequence", [])}
    out: dict[str, tuple[int, int]] = {n: (0, 0) for n in num2nome.values()}
    for rc in getattr(ds, "ROIContourSequence", []):
        seq = list(getattr(rc, "ContourSequence", []) or [])
        nome = num2nome.get(rc.ReferencedROINumber, f"?{rc.ReferencedROINumber}")
        out[nome] = (len(seq), sum(int(getattr(c, "NumberOfContourPoints", 0)) for c in seq))
    return out


def medir_c1_interobserver1() -> dict:
    """'o structure set contem 20-24 ROIs' x '13 ROIs'."""
    raiz = CENSO_TIER2 / "NSCLC-Radiomics-Interobserver1"
    if not raiz.exists():
        return {"medido": False, "motivo": f"{raiz} ausente"}
    hist_rois, hist_vis, arquivos = Counter(), Counter(), []
    for p, ds in _rtstructs(raiz):
        rois = [str(r.ROIName) for r in getattr(ds, "StructureSetROISequence", [])]
        vis = [r for r in rois if "vis" in r.lower()]
        hist_rois[len(rois)] += 1
        hist_vis[len(vis)] += 1
        arquivos.append({"serie": p.parent.name, "n_rois": len(rois), "n_rois_vis": len(vis)})
    n = sum(hist_rois.values())
    return {
        "medido": True,
        "n_rtstruct": n,
        "histograma_n_rois": dict(sorted(hist_rois.items())),
        "histograma_n_rois_vis": dict(sorted(hist_vis.items())),
        "faixa_n_rois": [min(hist_rois), max(hist_rois)] if hist_rois else None,
        "moda_n_rois": hist_rois.most_common(1)[0] if hist_rois else None,
        "versao_que_vale": (
            "NENHUMA DAS DUAS como enunciada. Medido: 13 a 24 ROIs por structure set, "
            "moda 13 (10 dos 21 arquivos); so 5 dos 21 caem na faixa 20-24. O '13' da outra "
            "ficha nao era contagem de ROI: era a contagem de ARQUIVOS com exatamente 5 ROIs "
            "'vis' (13 arquivos com 5 vis, 5 arquivos com 10 vis) — e essa, medida, confere. "
            "As duas frases falavam de coisas diferentes com o mesmo numero."
        ),
        "o_que_nao_muda": "F5 continua sendo o filtro que elimina: nenhum ROI de esofago, so GTV e limiares.",
        "arquivos": arquivos,
    }


def medir_c2_familias() -> dict:
    """'0 de 39 familias' x '35 colecoes com >=2 contornos por estudo'."""
    por_shard, colecoes_padrao, colecoes_ambiguas = {}, [], []
    n_col = n_rts = 0
    for i in range(4):
        f = FASE11 / "censo" / f"shard_{i}.json"
        if not f.exists():
            return {"medido": False, "motivo": f"{f} ausente"}
        d = json.loads(f.read_text(encoding="utf-8"))
        pad = amb = 0
        for c in d["colecoes"]:
            n_col += 1
            tem_pad = tem_amb = False
            for r in c.get("rtstruct_lidos", []):
                n_rts += 1
                cl = r.get("classificacao", {})
                tem_pad = tem_pad or bool(cl.get("padrao_observador"))
                tem_amb = tem_amb or bool(cl.get("familias_ambiguas"))
            pad += tem_pad
            amb += tem_amb
            if tem_pad:
                colecoes_padrao.append(c["colecao"])
            if tem_amb:
                colecoes_ambiguas.append(c["colecao"])
        por_shard[f"shard_{i}"] = {
            "n_colecoes": d["n_colecoes_neste_shard"], "com_padrao_observador": pad, "com_familia_ambigua": amb
        }

    sob = FASE11 / "sobreposicao_uid.json"
    n_multi = None
    if sob.exists():
        n_multi = json.loads(sob.read_text(encoding="utf-8")).get("ataque2_n_colecoes_com_estudo_multi")

    return {
        "medido": True,
        "escopo_a_criterio_de_familia_dentro_de_um_ROIName": {
            "n_colecoes_examinadas": n_col,
            "n_structure_sets_abertos": n_rts,
            "colecoes_com_padrao_observador": sorted(set(colecoes_padrao)),
            "colecoes_com_familia_ambigua": sorted(set(colecoes_ambiguas)),
            "por_shard": por_shard,
        },
        "escopo_b_contagem_de_structure_sets_por_estudo": {
            "n_colecoes_com_estudo_multi": n_multi,
            "fonte": "sobreposicao_uid.json, ataque2 (getSeries nas 156 colecoes)",
        },
        "versao_que_vale": (
            "AS DUAS, em escopos diferentes — e o erro foi generalizar o '0 de 39'. "
            "Criterio de familia (base+tipo+sufixo DENTRO de um mesmo ROIName), nas 156 colecoes "
            "e nos 58 structure sets abertos: 1 colecao com padrao_observador "
            "(NSCLC-Radiomics-Interobserver1, no shard_0) e 2 com familia ambigua "
            "(CC-Radiomics-Phantom-3, NSCLC-Radiomics, no shard_2). O '0 de 39' e verdadeiro "
            "so nos shards 1 e 3. Contagem de ARQUIVOS por estudo, outro criterio: 35 colecoes "
            "com pelo menos um estudo com >=2 RTSTRUCT ou >=2 SEG. Nao se contradizem: uma mede "
            "sufixo dentro do nome, a outra mede numero de arquivos."
        ),
    }


def medir_c3_stopstorm() -> dict:
    """'template em branco' x '31 ROIs com pontos, Esophagus com 67'."""
    raiz = FASE11 / "stopstorm"
    if not raiz.exists():
        return {"medido": False, "motivo": f"{raiz} ausente"}
    arquivos = []
    for p, ds in _rtstructs(raiz):
        o = _rois_e_pontos(ds)
        eso = {k: {"n_fatias": v[0], "n_pontos": v[1]} for k, v in o.items() if "sopha" in k.lower()}
        arquivos.append(
            {
                "arquivo": str(p.relative_to(RAIZ)),
                "n_rois": len(o),
                "n_rois_com_geometria": sum(1 for v in o.values() if v[0] > 0),
                "esofago": eso,
            }
        )
    return {
        "medido": True,
        "arquivos": arquivos,
        "versao_que_vale": (
            "A SEGUNDA. 'Template em branco' e FALSO: nos 3 RTSS do Contouring Benchmark sao "
            "31 ROIs e 31 com geometria, com 'Esophagus' em 1 fatia e 67/66/65 pontos; nos 3 "
            "Planning Contours sao 38/38/36 ROIs, todos com geometria, com 'Esophagus' em "
            "113/117/108 fatias e 10193/11341/7824 pontos. O veredito ELIMINADO sobrevive, "
            "mas por F1 (uma delineacao por caso), nao por ausencia de delineacao."
        ),
    }


def _resumo_sobreposicao() -> dict:
    """Cabecalho da medicao mais forte da fase, para o dossie nao depender de outro arquivo."""
    f = FASE11 / "sobreposicao_uid.json"
    if not f.exists():
        return {"medido": False, "motivo": f"{f} ausente — rode sobreposicao_uid.py"}
    d = json.loads(f.read_text(encoding="utf-8"))
    return {
        "medido": True,
        "proveniencia": d.get("proveniencia"),
        "n_colecoes": d["n_colecoes"],
        "n_colecoes_com_contorno": d["n_colecoes_com_contorno"],
        "n_series_de_contorno": d["n_series_de_contorno"],
        "estudos_em_varias_colecoes": len(d["ataque1_estudos_em_varias_colecoes"]),
        "series_em_varias_colecoes": len(d["ataque1_series_em_varias_colecoes"]),
        "pacientes_em_varias_colecoes": len(d["ataque1_pacientes_em_varias_colecoes"]),
        "n_colecoes_com_estudo_multi": d["ataque2_n_colecoes_com_estudo_multi"],
        "leitura": (
            "zero sobreposicao de UID entre colecoes NAO e 'o TCIA nao re-anota': e 'no canal "
            "DICOM do NBIA nao ha re-anotacao com o mesmo UID'. PleThora e SAROS re-anotam "
            "colecoes do TCIA fora do NBIA, como ZIP de NIfTI, e sao invisiveis aqui."
        ),
    }


# ---------------------------------------------------------------- manifesto

def manifesto_uid(raizes: list[Path]) -> dict:
    """Uma linha por serie baixada, a partir do marcador que tcia.baixar_serie grava."""
    linhas, por_colecao, por_modalidade = [], Counter(), Counter()
    ilegiveis = []
    for raiz in raizes:
        if not raiz.exists():
            continue
        for marcador in raiz.rglob("_tcia_serie.json"):
            try:
                s = json.loads(marcador.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                ilegiveis.append({"marcador": str(marcador.relative_to(RAIZ)), "erro": repr(e)})
                continue
            dcms = list(marcador.parent.glob("*.dcm"))
            linhas.append(
                {
                    "colecao": s.get("Collection"),
                    "modalidade": s.get("Modality"),
                    "serie_uid": s.get("SeriesInstanceUID"),
                    "estudo_uid": s.get("StudyInstanceUID"),
                    "paciente": s.get("PatientID"),
                    "licenca": s.get("LicenseName"),
                    "licenca_uri": s.get("LicenseURI"),
                    "caminho": str(marcador.parent.relative_to(RAIZ)),
                    "n_arquivos_dcm": len(dcms),
                    "bytes": sum(p.stat().st_size for p in dcms),
                    "baixado_em": datetime.fromtimestamp(
                        marcador.stat().st_mtime, timezone.utc
                    ).isoformat(timespec="seconds"),
                }
            )
            por_colecao[s.get("Collection")] += 1
            por_modalidade[s.get("Modality")] += 1
    linhas.sort(key=lambda x: (x["colecao"] or "", x["modalidade"] or "", x["serie_uid"] or ""))
    return {
        "n_series": len(linhas),
        "n_colecoes": len(por_colecao),
        "por_modalidade": dict(por_modalidade.most_common()),
        "por_colecao": dict(por_colecao.most_common()),
        "marcadores_ilegiveis": ilegiveis,
        "fonte": "marcador _tcia_serie.json gravado por tcia.baixar_serie (registro cru da API do NBIA)",
        "identidade_por_linha": "SeriesInstanceUID + n_arquivos_dcm + bytes + mtime do marcador. Sem checksum.",
        "series": linhas,
    }


def manifesto_fora_do_nbia() -> list[dict]:
    """Fontes que nao passam pelo NBIA e por isso nao tem marcador. Declaradas, nao inferidas."""
    fora = []
    for p in sorted((FASE11 / "stopstorm").rglob("*")) if (FASE11 / "stopstorm").exists() else []:
        if p.is_file():
            fora.append(
                {
                    "origem": "Zenodo, registro 'STOPSTORM Benchmark Data' (fora do NBIA: sem SeriesInstanceUID de API)",
                    "arquivo": str(p.relative_to(RAIZ)),
                    "bytes": p.stat().st_size,
                    "obtido_em": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                }
            )
    return fora


# ---------------------------------------------------------------- versoes

def versoes() -> dict:
    import hashlib

    import pydicom

    lock = RAIZ / "requirements-lock.txt"
    return {
        "python": sys.version.split()[0],
        "python_completo": sys.version,
        "pydicom": pydicom.__version__,
        "plataforma": platform.platform(),
        "interpretador": sys.executable,
        "requirements_lock": {
            "arquivo": str(lock.relative_to(RAIZ)) if lock.exists() else None,
            "sha256": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,
            "n_linhas": len(lock.read_text(encoding="utf-8").splitlines()) if lock.exists() else None,
        },
    }


# ---------------------------------------------------------------- autoteste

def autoteste() -> None:
    linha = (
        '{"x":"[ELIMINADO] Colecao-Teste (TCIA)  | elimina: F5 | tipo: interobserver | fonte aberta: True'
        '\\r\\n   obs=2 casos=0 contornos=7\\r\\n    Verbatim: \\"dois observadores\\" [...]\\r\\n\\r\\n'
        '[ENFRAQUECIDA] Colecao-Teste — a ficha diz X\\r\\n     Remedido: era Y. [...]"}\n'
    )
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.jsonl"
        f.write_text(linha, encoding="utf-8")
        fichas, contest = extrair_fichas(f)
    assert len(fichas) == 1, fichas
    assert fichas[0]["candidato"] == "Colecao-Teste (TCIA)"
    assert fichas[0]["filtro_que_elimina"] == "F5"
    assert fichas[0]["n_observadores_declarados"] == 2
    assert fichas[0]["n_contornos_declarados"] == 7
    assert fichas[0]["evidencia_truncada"] is True, fichas[0]["evidencia_verbatim"]
    assert 'dois observadores' in fichas[0]["evidencia_verbatim"]
    assert len(contest) == 1 and contest[0]["resultado_do_ataque"] == "ENFRAQUECIDA"
    casar_contestacoes(fichas, contest)
    assert contest[0]["casada_com"] == ["Colecao-Teste (TCIA)"], contest[0]
    assert fichas[0]["contestacoes"], fichas[0]

    # ficha sem "[...]" nao pode sair marcada como truncada
    f2, _ = extrair_fichas_de_texto(
        '[ELIMINADO] Outra  | elimina: F1 | tipo: nenhuma | fonte aberta: True\n'
        '   obs=0 casos=0 contornos=0\n    Evidencia inteira.\n'
    )
    assert f2[0]["evidencia_truncada"] is False, f2[0]

    # _rois_e_pontos: ROI declarada sem geometria tem de sair (0, 0), nao sumir
    class _ROI:
        def __init__(self, n, nome):
            self.ROINumber, self.ROIName = n, nome

    class _C:
        NumberOfContourPoints = 4

    class _RC:
        def __init__(self, n, seq):
            self.ReferencedROINumber, self.ContourSequence = n, seq

    class _DS:
        StructureSetROISequence = [_ROI(1, "Esophagus"), _ROI(2, "Vazia")]
        ROIContourSequence = [_RC(1, [_C(), _C()])]

    o = _rois_e_pontos(_DS())
    assert o == {"Esophagus": (2, 8), "Vazia": (0, 0)}, o
    print("autoteste: OK (extracao de ficha, casamento de contestacao, truncagem, ROI sem geometria)")


def extrair_fichas_de_texto(txt: str) -> tuple[list[dict], list[dict]]:
    """Mesmo extrator, sobre uma string. Usado pelo autoteste."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.jsonl"
        f.write_text(txt.replace("\n", "\\n"), encoding="utf-8")
        return extrair_fichas(f)


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--transcript", type=Path, default=TRANSCRIPT)
    ap.add_argument("--saida", type=Path, default=FASE11)
    args = ap.parse_args(argv)

    if args.autoteste:
        autoteste()
        return
    autoteste()

    args.saida.mkdir(parents=True, exist_ok=True)
    congelado = args.saida / "fichas_1a_onda.json"

    if args.transcript.exists():
        fichas, contestacoes = extrair_fichas(args.transcript)
        casar_contestacoes(fichas, contestacoes)
        origem = f"extraidas do transcript da 1a onda: {args.transcript}"
        congelado.write_text(
            json.dumps({"fichas": fichas, "contestacoes": contestacoes, "origem": origem}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    elif congelado.exists():
        d = json.loads(congelado.read_text(encoding="utf-8"))
        fichas, contestacoes, origem = d["fichas"], d["contestacoes"], d["origem"] + " (relido do congelado; transcript ausente)"
    else:
        raise SystemExit(f"sem transcript ({args.transcript}) e sem congelado ({congelado})")

    man = manifesto_uid([FASE11, CENSO_TIER2])
    man["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    man["fora_do_nbia"] = manifesto_fora_do_nbia()
    (args.saida / "manifesto_uid.json").write_text(
        json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    da_fase = [c for c in contestacoes if c["casada_com"]]
    avulsas = [c for c in contestacoes if not c["casada_com"]]

    dossie = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pergunta_da_fase": (
            "Existe dataset publico, acessivel e legalmente utilizavel com >=2 anotacoes HUMANAS "
            "INDEPENDENTES do ESOFAGO sobre os MESMOS exames de TC toracica?"
        ),
        "forma_da_resposta": (
            "Nao foi identificado, na busca realizada, dataset que satisfaca simultaneamente os "
            "sete filtros. Nunca 'nao existe'."
        ),
        "versoes": versoes(),
        "fichas": {
            "n": len(fichas),
            "origem": origem,
            "ressalva": (
                "a evidencia verbatim foi reportada ja truncada pelo agente da 1a onda; "
                "`evidencia_truncada` marca onde. Para o texto integral, a fonte primaria "
                "esta citada na propria ficha."
            ),
            "itens": fichas,
        },
        "contestacoes_do_arm_cetico": {
            "n": len(da_fase), "itens": da_fase,
            "criterio": (
                "contestacao que cita, pelo NOME, um candidato da fase 11. Casamento por nome "
                "e imperfeito: uma contestacao de outra fase que mencione a mesma colecao entra "
                "aqui. Leia `afirmacao_atacada` antes de usar."
            ),
        },
        "contestacoes_nao_casadas": {
            "n": len(avulsas),
            "ressalva": (
                "o transcript cobre todas as fases do projeto; estas contestacoes nao citam "
                "nenhum candidato da fase 11 e provavelmente sao de outra fase. Ficam listadas "
                "porque descartar em silencio transformaria lacuna em negativa."
            ),
            "afirmacoes": [c["afirmacao_atacada"][:200] for c in avulsas],
        },
        "candidatos_sem_ficha_no_formato_padrao": {
            "nomes": SEM_FICHA_PADRAO,
            "ressalva": (
                "aparecem no dossie da 1a onda so em prosa (secao cetica). Nao entram na "
                "contagem de 24 fichas; a ausencia de ficha e lacuna declarada, nao veredito."
            ),
        },
        "contradicoes_resolvidas_por_medicao": {
            "c1_n_rois_do_NSCLC_Radiomics_Interobserver1": medir_c1_interobserver1(),
            "c2_familias_de_observador_x_structure_sets_por_estudo": medir_c2_familias(),
            "c3_stopstorm_template_em_branco": medir_c3_stopstorm(),
        },
        "manifesto_uid": {
            "arquivo": "manifesto_uid.json",
            "n_series": man["n_series"],
            "n_colecoes": man["n_colecoes"],
            "por_modalidade": man["por_modalidade"],
        },
        "medicao_de_sobreposicao_de_uid": _resumo_sobreposicao(),
        "artefatos": {
            "sobreposicao_uid": "scripts/validation/tier2/sobreposicao_uid.py -> .clinica-dados/fase11/sobreposicao_uid.json",
            "censo": ".clinica-dados/fase11/censo/shard_0..3.json",
            "instrumento": "scripts/validation/tier2/interobservador.py",
        },
    }
    (args.saida / "dossie.json").write_text(json.dumps(dossie, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"dossie.json: {len(fichas)} fichas, {len(contestacoes)} contestacoes")
    print(f"manifesto_uid.json: {man['n_series']} series, {man['n_colecoes']} colecoes, {man['por_modalidade']}")
    for k, v in dossie["contradicoes_resolvidas_por_medicao"].items():
        print(f"\n[{k}] medido={v.get('medido')}")
        print("  ->", v.get("versao_que_vale", v.get("motivo"))[:400])


if __name__ == "__main__":
    main()
