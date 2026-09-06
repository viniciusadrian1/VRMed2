# VRmed — execução autônoma noturna, Fases 13–17

## Estado inicial (registrado ANTES de qualquer alteração)

| | |
|---|---|
| Início | 2026-09-06 (madrugada) |
| Commit inicial | `a590aa3adda8be8aa9dd14ddb58ed01cf62f5c69` |
| Branch | `master` |
| `git status` | **limpo** — zero arquivos modificados, zero não rastreados |
| Python | 3.13.11 · Windows-11-10.0.26200-SP0 |
| PyTorch | 2.6.0+cu124 · CUDA 12.4 · `cuda.is_available() = True` |
| GPU | NVIDIA GeForce RTX 4060 Ti — 16.380 MiB |
| RAM | 31,8 GiB total · **15,3 GiB disponíveis** |
| CPUs | 12 |
| Disco C: | 930,6 GiB total · **170,4 GiB livres** |
| SimpleITK | 2.5.6 |
| VTK | **9.7.0** |
| pydicom | 3.0.2 |
| trimesh | 5.0.0 |
| numpy / scipy / skimage | 2.5.2 / 1.18.1 / 0.26.0 |
| pandas / nibabel | 3.0.5 / 5.4.2 |

**Nenhum trabalho existente foi apagado.** Todo experimento novo vai para
`.clinica-dados/overnight/` (gitignored) e `docs/overnight/`.

**Travas ativas em toda a execução:** não treinar · não alterar `BASELINE_ESOFAGO_V1` ·
não ler nem recalcular `Tier2_TEST`/`Tier2_VALIDATION` do LCTSC · MASTER de reconstrução
(`marching_cubes · σ=0 · Taubin=4 · level=0.5 · offset=0 · sem decimação`) **não é
substituído automaticamente** · nada de e-mail, conta ou aceite de EULA.

---

## Checkpoints por fase

| Fase | Início | Fim | Duração | Status | Resultado principal |
|---|---|---|---|---|---|
| 13 — Ontologia do esôfago | 03:1x | 03:4x | ~35 min | **CONCLUÍDA — A** | `ESOPHAGUS_ONTOLOGY_V1` congelada; **K4 RESOLVIDO**; 12 testes de regressão passando |
| 14 — Prontidão para treino | 03:5x | 04:1x | ~20 min | **CONCLUÍDA — C** | cenário C, nenhum TEST defensável; K1/K2/K3 bloqueados, K4 resolvido |
| 15 — Teste independente | 03:0x | — | — | **em curso** (workflow `wu8f0od0a`, 7 arms) | — |
| 16 — Independência do baseline | — | — | — | pendente | — |
| 17 — Benchmark de reconstrução | — | — | — | pendente | — |


### Fase 13 — detalhe

**Arquivos criados**
- `docs/ESOPHAGUS-ONTOLOGY-V1.md` — especificação normativa congelada
- `scripts/validation/tier2/ontologia_esofago.py` — fonte da verdade legível por máquina + varredor
- `tests/test_ontologia_esofago.py` — 12 testes de regressão
- `docs/RELATORIO-FASE13-ONTOLOGIA-ESOFAGO.md`

**Arquivos modificados** (histórico preservado, nada apagado)
- `docs/VRMED-ANATOMICAL-ONTOLOGY.md` — 3 qualificações: linha do GT §1.2, traqueia §1.7, ponteiro para a V1

**Experimentos executados:** varredura lexical de 30 documentos (0 violações) · suíte de 12 testes.

**Achado de instrumento:** o controle positivo (teste 12) reprovou a primeira versão do
varredor — ele achava 3 de 4 violações injetadas, porque o padrão de parede/lúmen só casava
o infinitivo. Regex ampliado. **Um varredor que devolve zero por estar quebrado é pior que
nenhum varredor.**

**Bloqueios:** nenhum. K4 fechado; K1/K2/K3 permanecem fora do alcance desta fase.
