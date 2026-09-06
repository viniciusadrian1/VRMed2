"""Autoteste das fichas da Fase 11-B: a citacao esta mesmo no arquivo salvo?

Uma ficha vale pelo verbatim. Este check falha se:
  (a) um `trecho` com `arquivo_local` .txt nao existir naquele arquivo;
  (b) um numero-chave da ficha divergir do arquivo de medida;
  (c) uma serie listada em `arquivos_lidos` nao existir em disco.

Comparacao normalizada para so-alfanumerico-minusculo: aspas curvas, travessoes
e o '?' de fallback de encoding nao podem reprovar uma citacao correta.

Uso: python -m scripts.validation.tier2.fichas_fase11b_conferir
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FICHAS = RAIZ / ".clinica-dados/fase11/fichas"


def _n(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main() -> int:
    # so as fichas com ESTE esquema — o diretorio e compartilhado com outros
    # agentes da mesma onda, que gravam fichas de outro formato.
    fichas = sorted(p for p in FICHAS.glob("*.json")
                    if "colecao_na_api_do_tcia" in p.read_text("utf-8", errors="replace")[:4000])
    assert fichas, "nenhuma ficha gravada"
    citacoes = arquivos = 0
    for p in fichas:
        f = json.loads(p.read_text("utf-8"))
        for campo in ("candidato", "doi", "licenca", "filtro_que_elimina", "veredito",
                      "evidencia_verbatim", "arquivos_lidos", "cobertura", "filtros"):
            assert f.get(campo), f"{p.name}: campo obrigatorio vazio: {campo}"
        assert set(f["filtros"]) == {f"F{i}" for i in range(1, 8)}, f"{p.name}: faltam filtros"

        # (a) verbatim
        for e in f["evidencia_verbatim"]:
            local = e.get("arquivo_local")
            if not local or not local.endswith(".txt"):
                continue
            fonte = Path(local).read_text("utf-8", errors="replace")
            assert _n(e["trecho"]) in _n(fonte), \
                f"{p.name}: citacao NAO encontrada em {Path(local).name}: {e['trecho'][:70]}..."
            citacoes += 1

        # (b) numeros
        med = f["medicao"]
        c, i, r = med["censo_api"], med["cruzamento_idc"], med["rotulos_lidos_do_arquivo"]
        cob = f["cobertura"]
        assert cob["series_de_contorno_na_colecao"] == c["contornos"] == i["contornos_na_api"]
        assert cob["cobertas_pelo_indice_idc"] == i["cobertos_pelo_idc"]
        assert cob["arquivos_de_contorno_abertos"] == r["series_lidas"]
        assert i["ausentes_do_idc"] == 0, f"{p.name}: indice do IDC incompleto — lacuna a declarar"

        # esofago: se a ficha diz zero, o indice tem de dizer zero
        eso = i["esofagos_por_serie"]
        tem_eso = any(int(k) > 0 for k in eso)
        diz_zero = "zero esofago" in f["veredito"].lower() or "zero esofago" in json.dumps(
            f["filtros"], ensure_ascii=False).lower()
        if tem_eso:
            assert not diz_zero, f"{p.name}: ficha diz zero esofago mas o indice acha {eso}"
        else:
            assert diz_zero, f"{p.name}: indice nao acha esofago e a ficha nao declara isso"

        # (c) arquivos em disco
        for a in f["arquivos_lidos"]:
            d = Path(a["diretorio"])
            assert d.name == a["SeriesInstanceUID"], f"{p.name}: diretorio != UID em {d}"
            assert (d / "_tcia_serie.json").exists(), f"{p.name}: sem marcador da API em {d}"
            arquivos += 1

    print(f"OK — {len(fichas)} fichas, {citacoes} citacoes conferidas no arquivo de origem, "
          f"{arquivos} series de contorno conferidas em disco")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
