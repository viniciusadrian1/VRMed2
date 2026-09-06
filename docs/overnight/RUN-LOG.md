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
