"""Baixa a pagina da fonte primaria e guarda HTML + texto, para citar VERBATIM.

Resumo de modelo nao serve de evidencia: a ficha cita o texto que esta no
arquivo salvo aqui. Uso:
  python -m scripts.validation.tier2.fichas_fase11b_pagina <url> <nome> [regex]
"""
from __future__ import annotations

import html
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
BRUTO = RAIZ / ".clinica-dados/fase11/fichas/_bruto"
UA = {"User-Agent": "Mozilla/5.0 (vrmed fase11 ficha; contato via TCIA help desk)"}


def texto(url: str, nome: str) -> str:
    BRUTO.mkdir(parents=True, exist_ok=True)
    cru = BRUTO / f"{nome}.html"
    txt = BRUTO / f"{nome}.txt"
    if not cru.exists():
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310
            cru.write_bytes(r.read())
    bruto = cru.read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", bruto)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|td)>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    txt.write_text(s, encoding="utf-8")
    return s


if __name__ == "__main__":
    url, nome = sys.argv[1], sys.argv[2]
    s = texto(url, nome)
    if len(sys.argv) > 3:
        alvo = re.compile(sys.argv[3], re.I)
        for linha in s.splitlines():
            if alvo.search(linha):
                print(linha.strip())
    else:
        print(s)
