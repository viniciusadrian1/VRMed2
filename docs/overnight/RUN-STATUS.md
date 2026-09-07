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

---

## Fases 18–19 — 2026-09-06

| Fase | Estado | Resultado |
|---|---|---|
| **18** — auditoria do LyNoS | em curso | ontologia 15/15 · sonda calibrada · licença em apuração |
| **19** — baseline próprio auditável | infraestrutura CONCLUÍDA | esquema, travas e pré-registro escritos; **dados BLOQUEADOS** |

### Instrumentos novos

| Módulo | Verificações | Falhas |
|---|---:|---:|
| `lynos/auditoria.py` | 10 | 0 |
| `lynos/calibracao.py` | 8 | 0 |
| `lynos/grade_ct.py` | 5 | 0 |
| `lynos/adequacao.py` | 6 | 0 |
| `baseline_v1/manifesto.py` | 24 | 0 |
| `baseline_v1/plano.py` | 14 | 0 |
| `baseline_v1/candidatos.py` | 7 | 0 |
| `tests/test_baseline_v1.py` | 17 | 0 |

### Suítes anteriores — sem regressão

`test_geometria` 10/10 · `test_controles_positivos` 8/8 · `test_ontologia_esofago` 13/13
`interobservador --mutacao` 21/21 · `estilo_esofago --mutacao` 7/7
varredura de docs: 39 documentos, **0 violações**

### Split congelado

`sha256` `6e54c02b58bbb9b3a1667d4672eddef6…` · mtime 2026-09-04T21:19:49 · **INTOCADO**
development 30 · validation 15 · test 15

### Achados de instrumento desta execução

1. **O nulo da sonda geométrica estava deflacionado.** Embaralhava `y` e `x` de casos
   diferentes, gerando alvos retangulares contra um pool 75 % quadrado. Dava 0,041
   esperado em 15 e transformava 2 acertos em "sinal de 50×". O nulo por bloco dá
   **0,931** e **p = 0,229** — sem excesso sobre o acaso.
2. **Uma premissa não verificada virou verificação.** A sonda lê o cabeçalho da máscara
   em vez do da TC; isso só vale se as duas moram na mesma grade. Confirmado 15/15 por
   Range HTTP, 240 KiB em vez de ~3 GB.
3. **Guarda olhando o campo errado.** O teste que proíbe ler TEST fora de `avaliacao`
   procurava a declaração em `nota`; ela mora em `cmd`.
4. **Um bloqueio residual foi confundido com defeito.** O contrafactual "e se a licença
   fosse resolvida?" revelou que o LyNoS **continua** barrado por falta de
   `image_sha256`. Era achado, não bug.

---

## Fases 20–21 — 2026-09-06

| Fase | Estado | Resultado |
|---|---|---|
| **20** — dados auditáveis | em curso | canal DICOM resolve identidade; procedência da anotação é o gargalo |
| **21** — funil de ingestão | **CONCLUÍDA — A** | 14/14 casos, 13/13 mutantes, determinismo OK |

### Medições da Fase 20 (do índice público do IDC, sem baixar imagem)

| Medida | Valor |
|---|---|
| RTSTRUCT com esôfago-órgão | **908** em 5 coleções (reproduz a Fase 11) |
| **sujeitos distintos** com contorno de esôfago | **807** — não 908 |
| máscara ligada à imagem por `ReferencedSeriesInstanceUID` | **908/908** |
| `ROIGenerationAlgorithm` declarado para a ROI de esôfago | **UNKNOWN em 908/908** |
| 4D-Lung | 6.690 séries de **20 sujeitos**; esôfago em **16** |
| licença das RTSTRUCT de esôfago do NSCLC-Radiomics | **CC BY-NC 3.0** |
| UIDs de versões anteriores ausentes do índice atual | **13.081 de 58.060 (22,5 %)** |
| séries derivadas (analysis results) no IDC | **471.946**, das quais 378.153 do TotalSegmentator |

### Instrumentos novos

| Módulo | Verificações | Falhas |
|---|---:|---:|
| `fase20/censo_identidade.py` | 10 | 0 |
| `fase20/proveniencia_roi.py` | 14 | 0 |
| `fase20/log_de_busca.py` | 11 | 0 |
| `fase21/funil.py` | 16 | 0 |
| `fase21/mutacao.py` | 31 | 0 |
| `fase21/anonimizacao.py` | 11 | 0 |

### Auditoria

`PASS=258 · FAIL=0 · SKIP=0` — 49 de suíte + 168 de autoteste + 41 de mutação.
Docs: **44 documentos, 0 violações**. Split congelado **INTOCADO**.

### Defeitos de instrumento desta execução

1. **Harness contava `AssertionError` como recusa** — os 14 casos passaram sem provar nada.
2. **A correção colidiu com `DesalinhamentoGeometrico`**, que já é `AssertionError`.
3. **Regex de anonimização cego a `_`** — `1957-03-04_prontuario_123456789` não casava.
4. **`series_revised_idc_version` mal lido** como "foi revisada"; vem em 100 % das séries.
5. **DOI inexistente** já corrigido na Fase 18, e um mutante sobrevivente (**L4**) virou teste.
6. **Heredoc converteu `` em byte de backspace** num regex — o `cat -A` mostrou `^H`.

---

## Fases 22–23 — 2026-09-06

| Fase | Estado | Resultado |
|---|---|---|
| **22** — definição e autoria do LCTSC | **CONCLUÍDA — B** | definição documentada; autoria UNKNOWN; contradição resolvida contra o projeto |
| **23** — primeiro dataset auditável | **CONCLUÍDA — B** | **5/5 casos reais elegíveis**; pool sem split congelado |

### A correção que a Fase 22 impôs à Fase 20

| | Fase 20 dizia | Correto |
|---|---|---|
| `ROIGenerationAlgorithm` nos 908 | UNKNOWN em 908/908 | **MANUAL 731 · SEMIAUTOMATIC 101 · INDETERMINADO 42 · UNKNOWN 34** |

Causa: a coluna do índice é **deduplicada** (0, 1 ou 2 valores, nunca por ROI) e meu leitor
a tratava como lista paralela. Detectado ao abrir os 60 RTSTRUCT do LCTSC.

### Medições novas

| Medida | Valor |
|---|---|
| RTSTRUCT do LCTSC abertos | **60** — primeira vez em 22 fases |
| `ROIGenerationAlgorithm` do esôfago (LCTSC) | **MANUAL 59/60** |
| tags de autoria no arquivo | **vazias em 60/60** |
| esôfago acima do ápice pulmonar — LCTSC | mediana **+17,5 mm**, 54/60 |
| esôfago acima do ápice pulmonar — 4D-Lung | mediana **+21,0 mm**, 5/5 |
| amostra real adquirida | **5 sujeitos**, 108,2 MB |
| casos elegíveis (critério 23.18) | **5/5** |
| vínculo máscara↔imagem por UID | **5/5** |
| ontologia nos casos reais | 5/5 aprovados, buracos 0,0000 % |
| colisões de identidade (pool e cruzado) | **0** |

### Instrumentos novos

| Módulo | Verificações |
|---|---:|
| `fase22/rtstruct_lctsc.py` | 9 |
| `fase23/aquisicao.py` | 7 |
| `fase23/ingerir_real.py` | 8 |
| `fase23/pool.py` | 5 |

### Auditoria

`PASS=340 · FAIL=0 · SKIP=0` — 49 de suíte + 250 de autoteste + 41 de mutação.
Docs: **54 documentos, 0 violações**. Split congelado **INTOCADO**.

### Adendo do juiz (Fase 22) — workflow fechou 11/11

| Refinamento | Efeito |
|---|---|
| verificação da linha 82 | **PARCIAL**, não plena — conteúdo sim, atribuição ambígua |
| redações do limite cranial | **três**, mais contradição interna no próprio *deck* da NRG |
| protocolo × execução | tolerância ±1 fatia e critério ≥10 cm² **não aparecem** no que foi feito |
| corte de 1 cm no *scoring* | **real**, mas **assimétrico**: sobre-extensão tolerada, sub-segmentação penalizada |
| taxa de edição do QA | **UNKNOWN** — atinge o próprio split congelado |
| "expert" | aparece no **título**, nunca substanciado no método |
| Fase 9 | ponta cranial **+120,0 mm acima da carina**, truncamento em 1/30 |

---

## Fases 24 e 25 — universo de 16 fechado e congelado (2026-09-06)

**`VRMED-ESOPHAGUS-POOL16-V1` — TRAIN 10 · VALIDATION 6 · TEST 0**
`sha256_manifesto` (conteúdo canônico) `9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192`

| Portão | Fase 24 | Fase 25 |
|---|---|---|
| universo 16 = 5 + 11 | OK | — |
| reprodução dos 5 (regra 14) | OK, campo a campo | — |
| um por sujeito · sem bloqueados | OK | — |
| esquema 22 campos, 16/16 | — | OK, 0 erros |
| banda `[2, 8]` declarada antes | — | 6 → DENTRO |
| sujeito em dois splits | — | nenhum |
| licença bloqueante | — | nenhuma |
| TEST vazio e inalcançável | — | OK, por `AcessoIndevido` |

### Correções que estas fases impuseram a fases anteriores

| Alvo | Correção | Onde ficou registrada |
|---|---|---|
| Fase 23 · regra de seleção de série | **não era reproduzível** — o `<` estrito deixava a ordem de iteração decidir empates; corrigido com `(ct_mb, ct_uid)`; reproduz as 5 seleções originais | `RELATORIO-FASE24-POOL-16.md` §2 |
| Fase 24 · desidentificação | *"método UNKNOWN"* **estava errado** — há declaração explícita no grupo 0012 em 16/16 | adendo em `RELATORIO-FASE24-POOL-16.md` |
| identidade do congelamento | hash de **bytes** é dependente de plataforma (CRLF); vale o hash de **conteúdo canônico** | `RELATORIO-FASE25-CONGELAMENTO.md` §7.1 |

### Auditoria

`60` de suíte + `168` de autoteste + `13/13` mutantes mortos, com controle negativo antes e depois.
`ESOPHAGUS_ONTOLOGY_V1` **não tocada**. Split histórico do LCTSC **intocado**.
Não treinou, não mediu Dice, não rodou benchmark, não encostou no TEST.

**O que continua UNKNOWN:** `institution` (tag removida na origem), `annotation_protocol`,
data de anotação (deslocada na origem), conformidade da desidentificação, e a independência do
LyNoS — **INCONCLUSIVA por construção**, nunca "sem overlap".

---

## Fases 26 e 27 — treino do baseline (2026-09-06)

**FASE 26: BLOQUEADA POR TEMPO DE PAREDE. FASE 27: NÃO INICIADA (bloqueio da 26).**

Preflight **LIBERADO**: 12/12 versões idênticas ao pré-registro, 32/32 arquivos íntegros por
`sha256`, composição 10 / 6 / 0, `sha256_manifesto` `9388c736…82632192` confere, TEST
inalcançável de `treino` **e** de `validacao`, e — a trava que decidiu a fase —
**`validation` inalcançável de `treino`**.

| Medição | Valor |
|---|---|
| tempo de época (execução única e limpa) | **148,92 s** |
| épocas vinculadas pelo protocolo | **1000** (`nnUNetTrainer.py:159`, comando sem sinalizadores) |
| custo por fold | **41,4 h** |
| custo dos 5 folds | **206,8 h ≈ 8,6 dias** |

**Nenhum parâmetro foi encurtado para caber no tempo.** Não se reduziu época, não se trocou o
*trainer*, não se rodou um fold só, e não se declarou concluído o que não concluiu.

### Quatro desvios, formalizados na V2 do pré-registro

A V1 permanece intacta, como ela própria exige. `BASELINE-ESOPHAGUS-VRMED-V2.md`.

| # | Desvio | Motivo |
|---|---|---|
| 1 | `imagesTr` = 10 (só TRAIN), não 16 | a tabela `PERMISSOES` congelada só deixa `treino` ler `train`; **e** o planner extrai *fingerprint* de tudo que está em `imagesTr` — os 6 moldariam spacing, normalização e *patch size* sem entrar em lote nenhum (**vazamento transdutivo**, não coberto pelas 9 regras de split) |
| 2 | semente efetiva do split é **12345**, não a pré-registrada 20260906 | `nnUNetTrainer.py:624` fixa a semente no código e `nnUNetv2_train` não aceita parâmetro. A semente pré-registrada **não tem ponto de aplicação**. Lacuna **nomeada, não consertada** |
| 3 | VALIDATION é holdout pós-treino, **e não é um TEST** | mesma coleção, mesmo TPS, mesmo processo de contorno — não há independência de fonte |
| 4 | homônimo "validation" desambiguado | `find_best_configuration` lê as predições *out-of-fold* dos 10, nunca os 6 |

### Incidente

Dois treinos concorrentes no mesmo `fold_0` — o primeiro lançamento com `nohup &` sobreviveu
ao shell. Detectado por dois `training_log_*.txt` no mesmo diretório. **Os dois logs foram
preservados** antes da limpeza; a medição contaminada foi descartada; um único treino foi
relançado. `splits_final.json` não foi regerado.

### Auditoria

`72` de suíte (12 novos, anti-vazamento) + `203` de autoteste, 0 falhas. Varredura: **61
documentos, 0 violações**. Manifesto, snapshot e split **intactos**. TEST = 0 e nunca lido.
