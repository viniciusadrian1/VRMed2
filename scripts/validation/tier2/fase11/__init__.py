"""Drivers de uma passada da Fase 11 — preservados por reprodutibilidade, nao reusaveis.

Cada arquivo aqui produziu numero PUBLICADO no
docs/RELATORIO-FASE11-VARIABILIDADE-INTEROBSERVADOR.md. Como os artefatos que
eles gravam vivem em .clinica-dados/ (gitignored), apagar o driver tornaria o
numero irreproduzivel — por isso ficam.

Os INSTRUMENTOS da fase, esses sim reusaveis e com autoteste, estao um nivel
acima: interobservador.py (censo por nome, 11 guardas), idc_esofago.py (a
afirmacao central, reexecutavel em ~10 s), concordancia.py (concordancia
par-a-par; OBJETO = GTV, NAO ESOFAGO) e sobreposicao_uid.py.
"""
