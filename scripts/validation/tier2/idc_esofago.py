"""Fase 11 — a afirmacao central da fase, reexecutavel em ~10 segundos.

POR QUE ESTE MODULO EXISTE
A Fase 11 conclui uma NEGATIVA ("nao foi identificado dataset com >=2 contornos
humanos independentes do esofago sobre o mesmo exame"). Na 1a onda essa negativa
repousava em 58 structure sets abertos de 94.276 series de contorno — 0,062% —
e tinha um falso negativo PROVADO (Pancreatic-CT-CBCT-SEG saiu como "nem esofago
nem indicio de multiplos observadores" numa colecao cuja propria pagina diz
"repeat OAR delineations by two independent observers").

O indice publico do IDC troca amostra por CENSO: `rtstruct_index` traz ROINames
de TODOS os 19.358 RTSTRUCT do canal DICOM publico, sem baixar um byte de pixel,
sem credencial. A negativa deixa de ser "nao achamos na amostra" e passa a ser
"enumeramos o canal inteiro".

O QUE ESTE MODULO NAO PROVA — leia antes de citar
 - Cobre o canal DICOM PUBLICO. Nao cobre acesso restrito (iCurveE,
   NSCLC-Cetuximab/RTOG-0617, NRG-1308) nem o canal nao-DICOM (Zenodo, ZIP
   NIfTI: STOPSTORM, PleThora, SAROS, CURVAS). Esses foram tratados a mao.
 - `ROINames` e agregado com DISTINCT por serie: dois ROI de mesmo nome no mesmo
   arquivo colapsam. Por isso Q4 existe — `total_rois` maior que o numero de
   nomes distintos denunciaria o colapso. Q4 = 0, entao o DISTINCT nao escondeu nada.
 - `ROIGenerationAlgorithms` so vem preenchido em ~25% das series: F2 (humano
   contra automatico) NAO e decidivel por este indice. Quem decide F2 e a
   fonte primaria, arquivo por arquivo.
 - O indice nao tem ContentCreatorName. O defeito D7 (identidade do observador
   morando FORA do nome, como em QIBA CT-1C: 7 leitores humanos com SegmentLabel
   constante 'Test Label') e INDETECTAVEL aqui por construcao.
"""

from __future__ import annotations

import sys

# Reusa os crivos do instrumento auditado, em vez de reescrever regex aqui.
# ATENCAO: os crivos esperam o nome JA MINUSCULO — aplicar sobre 'Esophagus'
# cru devolve False e produziria um zero silencioso (aconteceu na conferencia).
from scripts.validation.tier2.interobservador import CRIVO_ESOFAGO, CRIVO_TUMOR

# Medido em 2026-09-06 sobre idc-index-data 24.2.2 (IDC v24). Se o indice for
# atualizado estes numeros mudam: e por isso que a checagem compara com
# tolerancia e IMPRIME o valor novo, em vez de falhar em silencio.
ESPERADO = {
    "n_rtstruct_no_indice": 19358,
    "n_com_esofago_orgao": 908,
    "colecoes": {"pediatric_ct_seg": 359, "nsclc_radiomics": 355,
                 "4d_lung": 101, "lctsc": 60, "eay131": 33},
    "q2_dois_nomes_no_mesmo_arquivo": 0,
    "q4_nome_repetido_escondido": 0,
    "q3_cts_com_dois_rtstruct_de_esofago": 16,
    "q3_colecoes": {"eay131"},
}


def _nomes_de_esofago(nomes) -> list[str]:
    """Nomes que o crivo aceita como esofago ORGAO (F5 exclui sitio de lesao)."""
    saida = []
    for n in nomes if nomes is not None else []:
        s = str(n).lower()
        if CRIVO_ESOFAGO.search(s) and not CRIVO_TUMOR.search(s):
            saida.append(str(n))
    return saida


def consultar() -> dict:
    """As quatro perguntas que decidem a fase, sobre o catalogo inteiro."""
    from idc_index import index

    cli = index.IDCClient()
    cli.fetch_index("rtstruct_index")
    rt = cli.rtstruct_index.copy()
    colecao = cli.index[["SeriesInstanceUID", "collection_id"]].drop_duplicates("SeriesInstanceUID")
    rt = rt.merge(colecao, on="SeriesInstanceUID", how="left")

    rt["_eso"] = rt["ROINames"].apply(_nomes_de_esofago)
    rt["_n"] = rt["_eso"].apply(len)
    com = rt[rt["_n"] > 0]

    # Q3 — o caso simetrico (defeito D3): observadores em ARQUIVOS SEPARADOS
    # apontando para a MESMA serie de CT. Sem essa pergunta, um dataset onde
    # cada observador grava seu proprio RTSTRUCT sairia negativo.
    por_ct = com.groupby("referenced_SeriesInstanceUID").size()
    alvos = por_ct[por_ct >= 2].index

    return {
        "versao_indice": "idc-index-data 24.2.2 (IDC v24)",
        "n_rtstruct_no_indice": int(len(rt)),
        "n_com_esofago_orgao": int(len(com)),
        "colecoes": com.groupby("collection_id").size().to_dict(),
        "casos_ct_por_colecao": com.groupby("collection_id")["referenced_SeriesInstanceUID"].nunique().to_dict(),
        "q2_dois_nomes_no_mesmo_arquivo": int((com["_n"] >= 2).sum()),
        "q4_nome_repetido_escondido": int((com["total_rois"] > com["ROINames"].apply(len)).sum()),
        "q3_cts_com_dois_rtstruct_de_esofago": int((por_ct >= 2).sum()),
        "q3_colecoes": sorted(set(com[com["referenced_SeriesInstanceUID"].isin(alvos)]["collection_id"])),
        "q3_nomes": sorted({n for lista in com[com["referenced_SeriesInstanceUID"].isin(alvos)]["_eso"] for n in lista}),
    }


def _autoteste() -> None:
    """Controles do CRIVO, sem rede — o erro que este autoteste existe para pegar.

    Na conferencia manual, aplicar o crivo sobre o nome CRU devolveu 908 -> 0.
    Um zero silencioso aqui viraria a conclusao da fase inteira, entao o
    controle negativo abaixo e tao obrigatorio quanto o positivo.
    """
    assert _nomes_de_esofago(["Esophagus"]) == ["Esophagus"], "crivo perdeu 'Esophagus' com maiuscula"
    assert _nomes_de_esofago(["ESOPHAGUS", "Oesophagus", "esofago"]), "crivo perdeu grafia alternativa"
    assert _nomes_de_esofago(["Heart", "Lung_L", "SpinalCord"]) == [], "crivo aceitou nao-esofago"
    # F5: sitio de lesao esofagico NAO e o orgao.
    assert _nomes_de_esofago(["GTV esophagus"]) == [], "crivo aceitou tumor como orgao"
    # A armadilha do DISTINCT: dois nomes IGUAIS colapsam no indice; e por isso
    # que Q4 compara total_rois com o numero de nomes, e nao confia na lista.
    assert len(_nomes_de_esofago(["Esophagus", "Esophagus"])) == 2, "contagem de repetidos quebrou"
    print("idc_esofago.py: autoteste do crivo OK (5 controles, sem rede)")


def _conferir(r: dict) -> int:
    """Compara com o publicado. Divergencia NAO e erro: o indice e atualizado."""
    divergencias = []
    for chave in ("n_rtstruct_no_indice", "n_com_esofago_orgao",
                  "q2_dois_nomes_no_mesmo_arquivo", "q4_nome_repetido_escondido",
                  "q3_cts_com_dois_rtstruct_de_esofago"):
        if r[chave] != ESPERADO[chave]:
            divergencias.append(f"  {chave}: publicado {ESPERADO[chave]} -> agora {r[chave]}")

    print(f"\nRTSTRUCT no indice publico ......... {r['n_rtstruct_no_indice']}")
    print(f"com esofago ORGAO .................. {r['n_com_esofago_orgao']} em {len(r['colecoes'])} colecoes")
    for col, n in sorted(r["colecoes"].items(), key=lambda kv: -kv[1]):
        print(f"    {col:<24} {n:>5} series | {r['casos_ct_por_colecao'][col]:>5} series de CT")
    print(f"\nF1 dentro do arquivo (>=2 nomes) ... {r['q2_dois_nomes_no_mesmo_arquivo']}")
    print(f"nome repetido escondido (Q4) ....... {r['q4_nome_repetido_escondido']}")
    print(f"F1 entre arquivos (mesma CT) ....... {r['q3_cts_com_dois_rtstruct_de_esofago']}"
          f" em {r['q3_colecoes']}")
    if r["q3_nomes"]:
        print("    nomes:", ", ".join(r["q3_nomes"][:6]))
        print("    (na medicao de 2026-09-06 sao pares contorno + SEED POINT do MESMO ato"
              "\n     de anotacao, em colecao de catalogo de lesao — nao dois observadores)")

    if divergencias:
        print("\nDIVERGENCIA em relacao ao publicado no RELATORIO-FASE11 —"
              "\no indice do IDC foi atualizado; a fase precisa ser relida:")
        print("\n".join(divergencias))
        return 1
    print("\nBate com o publicado no RELATORIO-FASE11-VARIABILIDADE-INTEROBSERVADOR.md")
    return 0


if __name__ == "__main__":
    _autoteste()
    if "--autoteste" not in sys.argv:
        raise SystemExit(_conferir(consultar()))
