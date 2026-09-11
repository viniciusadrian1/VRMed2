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

---

## Fase 26A — regra de parada (2026-09-07)

**DECISÃO: MANTER O PROTOCOLO.** *Early stopping* **não** recomendado. **V3 não necessária.**
Treino **pausado** em 64/1000 épocas do fold 0; nada apagado.

| Fato verificado no pacote instalado | |
|---|---|
| *early stopping* nativo | **não existe** — 0 ocorrências de `early_stop`/`patience`/`should_stop` em todo o `nnunetv2` |
| laço de treino | `for epoch in range(current_epoch, num_epochs)` — fixo, **sem `break`** |
| `checkpoint_best.pth` | salvo por `ema_fg_dice` (EMA α=0,1 sobre `mean_fg_dice` do fold interno) |
| **`nnUNetv2_predict`** | usa **`checkpoint_final.pth`** por default — os pesos da **última época** |
| variante de épocas | altera **só** `num_epochs`; PolyLR recoze no novo orçamento |

**O achado que decidiu a fase:** seria fácil concluir que o nnU-Net já protege contra
sobreajuste porque salva o melhor checkpoint. **Ele salva o melhor e entrega o último.** A
pergunta certa não é *quando parar*, é **qual checkpoint é entregue**.

**Regra declarada (plano de análise da Fase 27, não emenda de protocolo):** primário =
`checkpoint_final` (default do framework, zero discricionariedade); secundário =
`checkpoint_best`; **os dois sempre reportados**, e é **proibido** trocar o primário pelo
secundário depois de ver qual foi melhor nos 6 casos.

**Por que não *early stopping*:** exigiria código novo no caminho crítico de um experimento
cujo objetivo é auditabilidade; *patience* e `min_delta` seriam arbitrários, sem evidência
para calibrá-los; e o sinal (`ema_fg_dice` sobre **2 casos**) é ruidoso demais para governar
uma parada.

**Vazamento:** os 6 do holdout ausentes de `imagesTr`, `labelsTr`, do pré-processado, de
`gt_segmentations` e dos 5 folds. Cinco vetores de ataque testados, nenhum alcança. A barreira
é **configuração + ausência física dos `.b2nd`**: um caminho de vazamento produziria **crash
duro, nunca contaminação silenciosa**.

**Custo continua de pé:** 206,8 h para os 5 folds. Não foi resolvido, porque resolvê-lo por
decisão metodológica seria decidir por economia.

**Testes:** 86/86 (14 novos, metade deles travando o comportamento do **framework instalado**).
Varredura: 62 documentos, 0 violações. Nenhum teste existente enfraquecido.

**Refinamento da verificação adversarial (26A).** O argumento decisivo contra *early stopping*
não é nenhum dos quatro iniciais: é **incompatibilidade estrutural com o agendador**. O
`PolyLRScheduler` é parametrizado pela duração total (`max_steps = num_epochs = 1000`), então
parar antes **não recoze** — parar na época 150 entrega pesos com **86,4 % do LR inicial**.
É a diferença técnica entre a Opção B e a C: um orçamento menor **declarado antes** reparametriza
o agendador e recoze integralmente; parar no meio de um horizonte de 1000 não.

Verificação empírica independente (reconstrução da EMA reproduz os **53 recordes** do log,
último na época 55 = `0,7202`): na época 63 havia **8 épocas sem recorde**, mas o pseudo-Dice
**cru** era **0,7461 — o 2º maior das 64**. Um `patience=10` estaria a duas épocas de disparar
no melhor momento recente. Meia-vida da EMA = **6,58 épocas**: qualquer *patience* dessa ordem
mede o atraso do filtro, não platô. *(Isto demonstra que o sinal é inadequado; não calibra
nenhum parâmetro — a proibição do Passo 7 segue respeitada.)*

---

## Fase 26B / 27B — experimento de 250 épocas concluído (2026-09-09)

**EXPERIMENTO EXPLORATÓRIO.** O baseline canônico de 1000 épocas continua **pendente**.

5/5 folds · **1.250/1.250 épocas** · **47,76 h** · trainer `nnUNetTrainer_250epochs`
(só `num_epochs` difere; `nnUNetPlans.json`, `dataset_fingerprint.json`, `dataset.json` e
`splits_final.json` **byte-idênticos** aos da Fase 26).

| | Dice |
|---|---|
| *out-of-fold* (n=10, 1 rede por caso) | 0,7008 ± 0,1369 |
| *out-of-fold* **sem os 2 colapsos** (n=8) | **0,7613 ± 0,0558** |
| conjunto reservado (n=6, ensemble de 5) — `final` | **0,7630 ± 0,0192** |
| conjunto reservado — `best` | 0,7639 ± 0,0224 |

### Três correções que a verificação adversarial impôs

| # | Erro evitado | Verificado por |
|---|---|---|
| 1 | *"o modelo melhora e estabiliza no reservado"* — **comparação inválida**: 1 rede × ensemble de 5, variâncias de natureza diferente, e o gap inteiro são **2 casos** (sem eles, diferença de **0,0018**; Welch p=0,94) | recálculo próprio |
| 2 | *"precision>recall + volume negativo + razão<1 = três evidências"* — **circular**: `recall/precision = Vpred/Vref` **exatamente** (delta ≤ 1,1e−16). É o mesmo número três vezes | verificado voxel a voxel |
| 3 | *"`final` e `best` são idênticos"* — vale **só para o Dice**: HD95 piora 2,7 % com `best` (caso 107: +31,7 %) e erro de volume melhora 11,5 % | comparação caso a caso |

Ainda: **~80 % do erro de fronteira é simétrico** (FP+FN 87,92 mL contra líquido 17,40 mL) —
imprecisão de localização, não encolhimento. E a diferença treino↔validação **nasce grande**
nos folds 1 e 4 (−0,23 e −0,27 já no primeiro quarto), o que aponta para dificuldade dos casos
e não sobreajuste progressivo.

**Failure cases** (regra declarada): `104`, `116`, `115`. Os dois piores falham de formas
**opostas** — `116` perde um trecho inteiro (recall 0,654, HD95 20,3 mm, −24 % volume);
`104` tem o pior Dice mas o **melhor** HD95 (4,71 mm) e volume exato (+0,75 %).

**Testes:** 99/99 nos arquivos + 215/215 nos autotestes. Varredura: 0 violações.
TEST continua **0**; manifesto, snapshot e split **intactos**.

---

## Fase 28 — descoberta de TEST independente (2026-09-10)

**NENHUM CANDIDATO FORTE. A = 0. TEST continua 0.** Nada baixado, nada treinado.

**50 fichas** pesquisadas em 6 frentes → **33 datasets distintos** → 8 análises adversariais.
**A=0 · B=2 · C=3 · D=18 · E=10.**

### O achado estrutural

O baseline do projeto é **TotalSegmentator 2.18.0 (pesos v2)**. Boa parte da "evidência de
independência" que a pesquisa produziu se apoia no artigo do **v1** (1204 exames do PACS de
Basel) — **versão errada**, e para a v2 não há lista de treino por caso.

Pior: o suplemento do TotalSegmentator declara que **BTCV (Task 17) e SegTHOR (Task 55)** foram
usados como modelos pré-treinados para gerar a **primeira** segmentação do treino. O rótulo de
esôfago do baseline **descende de SegTHOR** — **dependência de anotação**, invisível a qualquer
sonda de `PatientID`/`StudyUID`/`SeriesUID`/`sha256`, porque não há imagem em comum.

**Consequência:** o eixo independência fica INCONCLUSIVO para **todo** candidato, o que sozinho
limita todos a B.

### Melhor candidato: StructSeg 2019 · Task 3 (B)

Único com esôfago em CT torácica e anotação por 1 oncologista + verificação por um 2º, com
disjunção institucional positiva. Pendências: **licença sem texto publicado**, **protocolo de
contorno não declarado**, site do desafio *"under repair"*. Segundo: **Pediatric-CT-SEG** (CC BY
4.0, RTSTRUCT, humana manual, download direto) — barrado por população **pediátrica** e
ontologia UNKNOWN.

### Desacordo entre céticos, resolvido

Um cético recomendou **A para o LCTSC**. Errado: o LCTSC já é *"validação — já em uso"*, a
Fase 16 **bane literalmente** a frase *"O LCTSC é conjunto de teste independente"*, e a
"evidência positiva" dele era sobre o TotalSegmentator **v1**. As correções factuais que ele
trouxe ficam registradas; a proibição não se reverte por evidência.

### Incidente de método

A primeira síntese leu **10 das 50 fichas** porque eu truncei o JSON de entrada em 45 KB. Ela
**detectou e declarou** o truncamento em vez de inventar linhas. As 50 foram recuperadas do
journal e reclassificadas.

**Testes:** 110/110 nos arquivos (11 novos) + 220/220 nos autotestes. A regra do status A virou
**código**, com controle positivo (um candidato perfeito **tem de** poder ser A) e negativo
(cada eixo quebrado sozinho **tem de** impedir). Varredura: 65 documentos, 0 violações.

---

## Fase 29 — auditoria de candidatos a TEST (2026-09-10)

**DECISÃO: C — não existe TEST externo adequado neste momento**, com recomendação forte de
**D (TEST próprio)**. **A = 0 · B = 0 · C = 3 · D = 2.** TEST continua **0 e protegido**.

**Os dois candidatos B da Fase 28 caíram, ambos por evidência positiva:**

| candidato | de | para | por quê |
|---|---|---|---|
| **StructSeg 2019 T3** | B | **D** | acesso **demonstradamente bloqueado** (`/Download/` HTTP 403, domínio NXDOMAIN); licença 2019 UNKNOWN com sinal **CC BY NC SA** no design doc de 2020; ordem das classes em conflito não resolvido; e os 50 casos são **treino** de Hermes e Iris |
| **Pediatric-CT-SEG** | B | **C** | adequação ao adulto **refutada por medição**: modelo adulto rende **DSC 0,47 ± 0,18** no esôfago daquele dataset (teto in-domain 0,70). Uso condicional: bancada de *domain shift*, nunca TEST adulto |

**RADCURE** ganhou um achado duro: o CSV oficial tem **2.708 de 3.337** linhas com esôfago — mas
é coorte de cabeça-pescoço, acesso sob DUA, e **é superset do OPC-Radiomics** e corpus de treino
de modelos públicos de OAR.

### 29D — linhagem do TotalSegmentator v2, com vocabulário restritivo

| conceito | estado |
|---|---|
| **image overlap** com BTCV/SegTHOR | **NÃO DEMONSTRADO** — o suplemento descreve uso de *modelos*, não das imagens |
| **patient overlap** | **NÃO VERIFICÁVEL** — nenhum identificador publicado |
| **annotation lineage overlap** | **DEMONSTRADO para o v1** — esôfago pré-segmentado por Task 17 (BTCV) e Task 55 (SegTHOR) |
| **model-derived annotation dependence** | **DEMONSTRADO** — 68 das 104 classes, esôfago entre elas |
| o mesmo para o **v2** | **INCONCLUSIVO** — sem artigo, sem model card; treino foi de 1139→1559 e os ~420 adicionais **não foram publicados** |

**Pode-se concluir:** SegTHOR e BTCV não servem de TEST para um pipeline cujo baseline descende
deles; e o GT do TotalSegmentator **não é anotação humana de novo** para o esôfago.
**Não se pode concluir:** que haja compartilhamento de imagens, nem que o v2 esteja limpo ou
contaminado.

**Distinção que protege o projeto:** o modelo próprio do VRmed (26B) foi treinado nas máscaras do
4D-Lung, **não em saída do TotalSegmentator**. A linhagem afeta o **baseline de comparação**, não
o treino do modelo.

### Regra do A, agora com cinco eixos

Independência decomposta em **imagem · exame · instituição · anotação · linhagem_anotacao**, os
cinco exigidos em `DEMONSTRADA`. `PLAUSIVEL` não basta.

**Testes:** 125/125 nos arquivos (15 novos) + 230/230 nos autotestes. `git status` mostra
**apenas arquivos novos** — nada modificado. Varredura: 66 documentos, 0 violações.
