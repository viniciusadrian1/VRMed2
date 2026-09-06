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
| 15 — Teste independente | 03:0x | 07:5x | ~4 h (interrompida) | **PARCIAL — B** | **LyNoS** encontrado; 79 candidatos, 230 consultas; sem passe cético |
| 16 — Independência do baseline | 07:4x | 08:3x | ~50 min | **CONCLUÍDA** | K2/K3 bloqueados; **circularidade SegTHOR/BTCV**; 2 overlaps; defeito ativo corrigido |
| 17 — Benchmark de reconstrução | 04:2x | 05:1x | ~50 min | **CONCLUÍDA** | **MASTER MANTIDO**; 182 medições; 4 achados de instrumento |


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


### Fase 17 — detalhe

**Arquivos criados**
- `scripts/validation/benchmark_fase17.py` — 14 variantes × 13 fantomas, checkpoint por linha
- `docs/overnight/reconstruction_benchmark.csv` — 182 linhas, 8/8 métricas congeladas
- `docs/RELATORIO-FASE17-RECONSTRUCAO.md`
- `.clinica-dados/overnight/fase17/` — GLB, Draco e JSON de comparação (gitignored)

**Experimentos executados:** 182 reconstruções + 39 decimações + 4 compressões Draco medidas
com decodificador oficial.

**Resultado principal:** MASTER mantido. `sigma=1` rejeitado **por medição** — funde dois
cilindros em contato (2 componentes → 1) *e* rompe a ponte fina (1 → 2), as duas falhas
opostas ao mesmo tempo. Surface Nets perde 71,7 % do volume na esfera de 6 mm.

**Quatro achados de instrumento, todos erro meu:**
1. `surface_nets` medido duas vezes como se fossem variantes distintas (o método ignora o
   filtro de malha — vértices byte a byte idênticos).
2. Três colunas de topologia vazias por chave inventada; `dict.get` devolveu `""` em silêncio.
3. Duas das oito métricas congeladas ausentes do CSV — a ontologia congelada há três horas
   não impediu o instrumento de ignorá-la.
4. **Hausdorff do Draco errado por quatro ordens de grandeza** (10,27 mm contra 0,0009 mm):
   `trimesh` não decodifica Draco, avisa em `stderr` e termina com código 0.

**Bloqueios:** nenhum. Draco cobriu 4 das 13 malhas — declarado, não omitido.


---

## Interrupção da sessão — 2026-09-06, ~07:30

**FATO.** A sessão anterior encerrou e derrubou três processos de fundo: o workflow da Fase 15,
o da Fase 16 e o braço de anatomia real da Fase 17.

**O que sobreviveu, e como:**

| Processo | Estado | Recuperação |
|---|---|---|
| Fases 13, 14, 17 | **commitadas** | nada a fazer |
| Fase 15 (workflow) | 13 resultados de agente no journal | **recuperados** — os 7 arms completos + 6 fichas; o relatório foi escrito a partir deles e a lacuna declarada |
| Fase 16 (workflow) | **0 resultados** | **relançada do zero** |
| Anatomia real (Fase 17) | 8 de 48 linhas no CSV | **retomada** por script que lê o CSV e pula o que já está lá |

**INFERÊNCIA.** O checkpoint por linha do benchmark e o journal do workflow foram o que
permitiu não perder trabalho. O único custo real foi o passe cético da Fase 15, que não chegou
a rodar — e isso está declarado no relatório dela, não escondido.

### Fase 15 — detalhe

**Arquivos criados:** `docs/RELATORIO-FASE15-TESTE-INDEPENDENTE.md` ·
`docs/ESOPHAGUS-DATASET-CANDIDATES.md` · `.clinica-dados/overnight/fase15_recuperado.json`

**Resultado principal:** **LyNoS** — 15 TCs mediastinais, esôfago em NIfTI binário
**preenchido** (fração de buracos 0,028 %), canal não-DICOM, GT de 2019 anterior ao
TotalSegmentator. Classe **E**: independência indeterminada pelas 420 imagens não atribuídas.

**Bloqueios:** sem passe cético; conflito de licença entre três fontes oficiais; 14 candidatos
de classe D não verificados.


### Fase 16 — detalhe

**Arquivos criados:** `docs/RELATORIO-FASE16-INDEPENDENCIA-BASELINE.md`

**Arquivos modificados:** `scripts/validation/tier2/coorte.py` (o **gerador**) ·
`.clinica-dados/tier2/lctsc/manifest.json` · `docs/RELATORIO-VALIDACAO-RECONSTRUCAO.md`

**Resultado principal:** a independência do baseline é **estruturalmente indemonstrável** com o
que o pacote distribui — não há model card, não há `splits_final.json`, não há um único
identificador de caso. E a via de contaminação mais grave é **invisível a toda sonda de
imagem**: SegTHOR e BTCV semearam o rótulo de esôfago do treino (suplemento S2).

**Achados de instrumento (4):** quatro correções numéricas contra afirmações dos próprios arms,
todas encontradas pelos céticos — incluindo uma refutação de sinal contrário (a sonda **tem**
poder, ao contrário do que o arm concluiu).

**Bloqueios:** K2 e K3 permanecem. K3 passa a ser registrado como **estrutural**, não pendência
de busca.
