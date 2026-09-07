# Fase 26B — experimento exploratório de orçamento reduzido (250 épocas)

**Data:** 2026-09-07 · **Commit:** `51a23d3` · **Run ID:** `VRMED-FASE26B-250EP-5FOLD`
**Estado:** **TREINO EM EXECUÇÃO** — 5 folds sequenciais · resultados **pendentes**

> **Isto NÃO é o baseline definitivo.** O baseline canônico de 1000 épocas das Fases 19/26
> continua **oficialmente pendente** e não foi declarado concluído. Este é um
> **EXPERIMENTO EXPLORATÓRIO DE ORÇAMENTO REDUZIDO**, e nenhum número dele pode ser
> apresentado como substituto do canônico.

---

## 1. Objetivo e motivação

**Pergunta científica:** *250 épocas produzem um modelo internamente utilizável para o
próximo estágio do VRmed?*

**Motivação.** O baseline canônico exige **206,8 h** (8,6 dias) de GPU dedicada — medição da
Fase 26, não estimativa. Enquanto ele não roda, a Fase 27 (diagnóstico: por caso, *failure
modes*, fase respiratória, *spacing*) fica bloqueada, e o projeto não sabe sequer se o
pipeline produz segmentação sensata.

Este experimento responde à pergunta diagnóstica a **1/4 do custo de otimização**, e é
declarado como o que é: exploratório.

**O que ele explicitamente não faz:** não substitui o canônico, não altera o pré-registro
histórico, não altera dataset, split, manifesto, snapshot ou ontologia, não usa os 6 casos de
holdout para nenhuma decisão de treino, e não usa TEST.

---

## 2. Relação com o baseline canônico de 1000 épocas

**Não são o mesmo experimento, e não serão comparados numericamente como se fossem.**

| | canônico (Fase 26) | experimental (Fase 26B) |
|---|---|---|
| trainer | `nnUNetTrainer` | `nnUNetTrainer_250epochs` |
| épocas | 1000 | 250 |
| iterações totais por fold | 250.000 | **62.500 — 1/4 do orçamento** |
| estado | **pendente**, fold 0 pausado em 64/1000 | em execução |
| natureza | **baseline canônico** | **exploratório** |

**O canônico não é benchmark de desempenho**, porque não tem os cinco folds concluídos e não
tem resultado final. Comparar números contra ele seria comparar contra nada.

**E "recozido" não quer dizer "convergido"** (correção registrada na Fase 26A): a variante
reparametriza o `PolyLRScheduler` para o horizonte de 250 e recoze integralmente, mas são
**quatro vezes menos passos de gradiente**. O esperado é Dice **inferior** ao do orçamento
cheio. Um orçamento menor produz um modelo legítimo e comparável **a si mesmo**, não um
substituto equivalente.

### 2.1 O run parcial de 1000 épocas está preservado e não foi tocado

`.clinica-dados/fase26/nnUNet_results/.../nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/`
continua com `checkpoint_best.pth`, `checkpoint_latest.pth`, `debug.json`, `progress.png` e o
log das 64 épocas. **Nada foi apagado, nada foi continuado, nada foi misturado.** A 26B tem
árvore própria e o nome da pasta do trainer já as separa por construção.

---

## 3. Protocolo

**A única mudança experimental autorizada é `num_epochs = 250`**, por meio da variante que já
vem no pacote. Verificado por teste: `nnUNetTrainer_250epochs` altera **exclusivamente**
`num_epochs` — nenhum outro atributo.

Não foi criada subclasse nova, não foi implementado *early stopping*, não foi criado agendador
customizado, e não foram alterados arquitetura, *loss*, otimizador, augmentação, *patch size*,
*batch size* ou pré-processamento.

```
nnUNetv2_train 501 3d_fullres FOLD -tr nnUNetTrainer_250epochs --npz     (FOLD 0..4)
```

| Parâmetro | Valor | Origem |
|---|---|---|
| *patch size* | 48 × 224 × 192 | planner (idêntico ao da Fase 26) |
| *batch size* | 2 | planner |
| spacing alvo | 3,0 × 0,9766 × 0,9766 mm | planner |
| normalização | `CTNormalization` | planner |
| arquitetura | `PlainConvUNet`, 6 estágios, `(32,64,128,256,320,320)` | planner |
| otimizador | SGD nesterov, momentum 0,99 | default |
| *learning rate* | 0,01, **PolyLR sobre horizonte de 250** | default reparametrizado |
| *loss* | Dice + CE, com *deep supervision* | default |
| iterações/época | 250 · validação 50 | default |

### 3.1 Prova de que nada além de `num_epochs` difere

A árvore `nnUNet_raw` da 26B foi criada por **cópia byte a byte** da árvore da Fase 26, e a
identidade foi verificada: **21/21 arquivos com `sha256` idêntico**. Depois do
`plan_and_preprocess`:

| Artefato | 26 vs 26B |
|---|---|
| `nnUNetPlans.json` | **IDÊNTICO** (`067bf8da308e0428…`) |
| `dataset_fingerprint.json` | **IDÊNTICO** (`3511a5fac36e5d78…`) |
| `dataset.json` | **IDÊNTICO** (`2c92c906627d80a0…`) |
| `splits_final.json` | **IDÊNTICO** — copiado, **não regerado** (`41e2dbe86f0dbec0…`) |

Os folds não foram regenerados: são **literalmente o mesmo arquivo** da Fase 26, e um teste
compara os bytes para garantir que continuem sendo.

---

## 4. Dataset e split

| | |
|---|---|
| dataset | `VRMED-ESOPHAGUS-POOL16-V1` |
| `sha256_manifesto` | `9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192` — **intacto** |
| ontologia | `ESOPHAGUS_ONTOLOGY_V1` — **intacta** |
| **TRAIN / VALIDATION / TEST** | **10 / 6 / 0** — inalterado |

Os 5 folds sobre os 10 de TRAIN (8 treino / 2 validação interna cada), cada caso validando
internamente em exatamente um fold:

| fold | validação interna |
|---|---|
| 0 | `4DLUNG-100`, `4DLUNG-111` |
| 1 | `4DLUNG-106`, `4DLUNG-114` |
| 2 | `4DLUNG-108`, `4DLUNG-110` |
| 3 | `4DLUNG-102`, `4DLUNG-112` |
| 4 | `4DLUNG-105`, `4DLUNG-109` |

Os 6 do holdout (`101`, `103`, `104`, `107`, `115`, `116`) estão **fora** de `imagesTr`,
`labelsTr`, do pré-processado, de `gt_segmentations` e de todos os folds.

---

## 5. Seed — a lacuna não é reinterpretada

| | |
|---|---|
| `20260906` | **IDENTIFICADOR do experimento**, registrado no `dataset.json` e no run |
| **`12345`** | **semente efetiva do framework** — fixa em `nnUNetTrainer.py:624`, e `nnUNetv2_train` não aceita parâmetro de semente |

A lacuna documentada na V1/V2 continua valendo exatamente como está. Chamar `20260906` de
semente do treino seria falso, e este relatório não o faz.

---

## 6. Preflight da 26B — 14/14 LIBERADO

Módulo: [`fase26b/preflight.py`](../scripts/validation/fase26b/preflight.py) · 7 autotestes,
0 falhas.

| # | Verificação | Resultado |
|---|---|---|
| 01 | dataset correto | `VRMED-ESOPHAGUS-POOL16-V1` · `ESOPHAGUS_ONTOLOGY_V1` |
| 02 | manifest hash | `9388c736…82632192`, intacto |
| 03 | split | `{train: 10, validation: 6, test: 0}` |
| 04 | TEST vazio | 0, e inalcançável do contexto de treino |
| 05 | 10 casos em `imagesTr` | 10 imagens, 10 rótulos, confere com a partição train |
| 06 | holdout fora do raw | **nenhum invasor** |
| 07 | holdout fora do pré-processado | **nenhum invasor** |
| 08 | folds | 5 folds, universo de 10, igual à partição train |
| 09 | trainer | resolve para `nnUNetTrainer_250epochs` pelo caminho do próprio nnU-Net |
| 10 | `num_epochs` | **250** |
| 11 | sem *early stopping* | **0 achados** em todo o pacote |
| 12 | sem trainer customizado nosso | **0 arquivos** |
| 13 | saída separada da Fase 26 | pastas e diretórios distintos |
| 14 | sem checkpoint herdado | **0 encontrados** |

---

## 7. Hardware e ambiente

RTX 4060 Ti · 16.379 MiB · CUDA 12.4 · `torch` 2.6.0+cu124 · `nnunetv2` 2.8.1 ·
Python 3.13.11 · Windows 11.

**Diretório de resultados:**
`.clinica-dados/fase26b/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer_250epochs__nnUNetPlans__3d_fullres/`

---

## 8. Regra de checkpoint — declarada na Fase 26A, antes de qualquer resultado

| | |
|---|---|
| **primário** | `checkpoint_final.pth` — default do framework, nenhuma discricionariedade nossa |
| **secundário** | `checkpoint_best.pth` — melhor `ema_fg_dice` da validação interna |
| regra | **os dois medidos e reportados, sempre**, para todos os folds |
| **proibição** | trocar o primário pelo secundário depois de ver qual deu melhor nos 6 casos |

Esta regra vale igualmente para todos os folds e **não será revisada depois dos resultados**.

---

## 9. Testes

**`tests/test_fase26b_250epochs.py` — 11/13, com 2 PENDENTES.**

A separação é explícita e deliberada:

- **[PRE] 11/11 passam** — trainer correto, 250 épocas e só isso, saída separada, dataset =
  partição train, holdout ausente de tudo, TEST vazio e inalcançável, folds corretos **e
  byte-idênticos aos da Fase 26**, manifesto intacto, snapshot intacto, nenhuma herança de
  checkpoint do experimento de 1000, nenhuma rotina de parada customizada.
- **[POS] 2 PENDENTES** — `checkpoints_presentes_apos_o_treino` e
  `todos_os_folds_rodaram_250_epocas` dependem de fold concluído.

**PENDENTE não é PASS**, e o executor imprime isso literalmente. "Ainda não rodou" e "passou"
são coisas diferentes, e confundi-las é como um relatório de fase mente sem que ninguém
perceba.

**Suíte completa: 97 testes** — os 86 anteriores mais os 11 [PRE] da 26B. Nenhum teste
existente foi enfraquecido.

---

## 10. Resultados

**PENDENTES.** O treino está em execução. Nenhuma métrica é publicada aqui, e nenhuma será
inventada.

Ficam pendentes, e serão preenchidos quando os cinco folds terminarem:

- resultados por fold (validação interna *out-of-fold*, n = 2 por fold);
- resultados nos 6 casos do holdout, com `checkpoint_final` **e** `checkpoint_best`;
- as oito métricas congeladas: média, mediana, mínimo, máximo, desvio amostral, por caso e
  por fold;
- *failure cases* pela regra já declarada na Fase 27 — os três de menor Dice, desempate por
  HD95 maior, mais qualquer caso com recall < 0,50, precision < 0,50 ou predição vazia;
- curvas de *train loss*, *validation loss* interna e pseudo-Dice ao longo das 250 épocas;
- análise de sobreajuste/subajuste, **sem usar os 6 do holdout para decidir quando houve**;
- observações descritivas de fase respiratória (`c00`×12, `c80`×2, `c10`×1, `c40`×1) — **sem
  teste estatístico**, porque dois estratos têm n = 1;
- observações de *spacing* nos casos fora de 0,9766 mm, **sem remover caso e sem alterar
  split**.

---

## 11. Limitações que já valem, independentemente do resultado

1. **n = 6** na avaliação do holdout — intervalo largo, nenhuma diferença conclusiva.
2. **TEST = 0** — não existe desempenho externo publicável.
3. Os 6 vêm da **mesma coleção, mesmo TPS, mesmo processo de contorno** que os 10 — não há
   independência de fonte, e o holdout **não é um TEST**.
4. GT **`SEMIAUTOMATIC`** em 16/16 — não é anotação humana pura.
5. `institution` e `annotation_protocol` **UNKNOWN**.
6. Extensão longitudinal **herdada do GT**, não avaliável anatomicamente.
7. **1/4 do orçamento de otimização** do canônico — Dice esperado inferior.
8. **Não se afirmará que 250 épocas evita sobreajuste.** O objetivo é observar comportamento,
   não provar causalidade.

---

## 12. Estado dos arquivos

| Caminho | O que é |
|---|---|
| `scripts/validation/fase26b/preflight.py` | 14 verificações + 7 autotestes |
| `tests/test_fase26b_250epochs.py` | 11 [PRE] + 2 [POS] |
| `docs/overnight/phase26b/preflight.json` | verificações e identidade do run |
| `.clinica-dados/fase26b/` | árvore própria do experimento (fora do git) |

**Nenhum artefato da Fase 26 ou anterior foi sobrescrito.**
