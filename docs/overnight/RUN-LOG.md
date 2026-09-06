# RUN-LOG — execução autônoma Fases 13–17

Registro cronológico de comandos, durações, falhas e decisões.
Fatos medidos são marcados **FATO**; deduções, **INFERÊNCIA**; sugestões, **RECOMENDAÇÃO**.

## Setup

- **FATO** commit inicial `a590aa3`, branch `master`, árvore de trabalho limpa.
- **FATO** GPU RTX 4060 Ti 16.380 MiB disponível; `torch.cuda.is_available() = True`.
- **FATO** 170,4 GiB livres em disco; 15,3 GiB de RAM disponíveis; 12 CPUs.
- **FATO** `du -sh .clinica-dados` excedeu 120 s e foi mandado para segundo plano em vez de
  bloquear o pipeline (política de timeout do enunciado).
- **DECISÃO** experimentos novos em `.clinica-dados/overnight/`; nada sobrescreve resultado
  congelado.

## Fase 13 — ESOPHAGUS_ONTOLOGY_V1

- **FATO** ontologia já estava 90% correta: a Fase 9 removera cricoide/JGE por medição.
  O que faltava era documento normativo versionado e mecanismo antirregressão.
- **FATO** 3 linhas qualificadas em `VRMED-ANATOMICAL-ONTOLOGY.md`; zero linhas apagadas.
- **FATO** varredura lexical: 30 documentos, 0 violações.
- **FATO** primeira versão do varredor tinha 2 falsos positivos (linhas que *proibiam* a
  frase) e 1 falso negativo (conjugação "separamos" escapava). Ambos corrigidos.
- **FATO** `digital twin`: banimento total era errado — 3 documentos de análise usam o termo
  corretamente, para contrastar. Regra virou de COMPANHIA (exige `patient-specific` no mesmo
  documento). Termo canônico registrado: `patient-specific 3D model`.
- **FATO** `tests/test_ontologia_esofago.py` — 12/12.
- **DECISÃO** K4 = RESOLVIDO. Não desbloqueia treino sozinho.
