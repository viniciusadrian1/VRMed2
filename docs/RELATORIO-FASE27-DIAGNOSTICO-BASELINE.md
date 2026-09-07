# Fase 27 — diagnóstico do baseline

**Data:** 2026-09-06 · **Estado:** **NÃO INICIADA — bloqueada pela Fase 26**

> **Este relatório não contém nenhuma métrica, nenhuma tabela por caso, nenhuma curva e
> nenhum *failure case*.** Não porque foram omitidos, mas porque **não existe modelo
> treinado**. Publicar qualquer número aqui seria inventá-lo.

---

## 1. Por que não iniciou

O pedido condiciona esta fase de forma explícita:

> *"Somente iniciar após Fase 26 concluir sem bloqueio."*

A Fase 26 **não concluiu sem bloqueio**. Ela parou em bloqueio de tempo de parede, medido e
não estimado:

| | |
|---|---|
| tempo de época medido (execução única e limpa) | **148,92 s** |
| épocas vinculadas pelo protocolo | **1000** (default do `nnUNetTrainer`) |
| custo por fold | **41,4 h** |
| custo dos 5 folds | **206,8 h ≈ 8,6 dias** |
| épocas concluídas | **2** |
| checkpoints produzidos | **nenhum** (o primeiro sai na época 50) |

Detalhes em [`RELATORIO-FASE26-BASELINE.md`](RELATORIO-FASE26-BASELINE.md) §5.

**Não se improvisou um protocolo mais barato para poder produzir números.** Reduzir épocas,
trocar o *trainer* por uma variante curta ou rodar só um fold produziria uma tabela de
métricas — e ela descreveria um experimento que ninguém pré-registrou. A regra desta execução
proíbe isso, e a proibição foi respeitada.

---

## 2. O que está pronto e verificado, esperando um modelo

A ausência de resultado **não** é ausência de trabalho. Toda a instrumentação da Fase 27 está
escrita, testada e pronta para rodar sem nenhuma decisão nova.

### 2.1 Avaliador — [`fase27/avaliar.py`](../scripts/validation/fase27/avaliar.py)

**12 autotestes, 0 falhas.** As oito métricas congeladas, com o código que já existia:

| Métrica congelada | De onde vem |
|---|---|
| `dice`, `iou` | `segmentation_metrics.compare_masks` |
| `hd95`, `assd` | `segmentation_metrics.surface_distances` (mm) |
| `precision`, `recall` | `benchmark_tier2.recall_containment` |
| `erro_volume_absoluto` | contagem de voxels × volume do voxel (mL) |
| `erro_volume_percentual` | `segmentation_metrics.volume_error_pct` |

**Nenhuma métrica nova entra no critério.** `hd`, `nsd_1mm`, `nsd_2mm`, `nsd_1vox` e
`nsd_2vox` saem do mesmo cálculo e são publicadas como **exploratórias**, num campo separado,
fora do critério — exatamente o que a ontologia permite. Um autoteste falha se qualquer uma
delas vazar para o nível do critério.

**Contra o que se compara:** contra o GT do **manifesto congelado**, lido do caminho que o
manifesto declara — e não contra a cópia relabelada que foi para a árvore do nnU-Net. A cópia
foi provada idêntica em conjunto de foreground, mas comparar contra o original tira a cópia
da cadeia de evidência por completo.

**Os autotestes provam que o instrumento enxerga**, e não apenas que ele roda:

| # | O que é provado |
|---|---|
| 1 | máscaras idênticas ⇒ dice = iou = 1, distâncias = 0, erro de volume = 0 |
| 4 | predição **inflada** ⇒ recall alto **e** precision baixa, erro percentual **positivo** |
| 5 | predição **encolhida** ⇒ precision alta **e** recall baixo, erro percentual **negativo** |
| 6 | predição **vazia** ⇒ dice = 0, e `precision` vira `"invalido"`, nunca um float plausível |
| 7 | dobrar o *spacing* **dobra** o HD95 — a distância é milímetro físico, não índice de voxel |
| 8 | dobrar o *spacing* multiplica o erro de volume absoluto por 8 |
| 9–11 | o resumo tem desvio **amostral** (`ddof=1`), ignora NaN, e não inventa estatística de lista vazia |
| 12 | a lista de métricas é a da ontologia congelada, não uma cópia local que possa divergir |

O teste 4 e o teste 5 são o que impede o erro clássico de publicar `precision` e `recall`
trocados: eles exigem que as duas metades **assimétricas** se comportem em direções opostas.

### 2.2 Controles anti-vazamento — [`test_fase26_treino.py`](../tests/test_fase26_treino.py)

**12/12.** Já rodando e já verdes. Caem se o TEST for preenchido, se um caso de VALIDATION
aparecer em `imagesTr`, se o manifesto ou o snapshot mudarem, se a composição do split mudar,
ou se os folds deixarem de cobrir exatamente os 10 de TRAIN.

### 2.3 O holdout, montado e separado

Os 6 casos da partição VALIDATION estão em `.clinica-dados/fase26/validation_holdout/`,
**fora da árvore do nnU-Net** — o que não está em `imagesTr` não pode ser sorteado para
treino por engano. Imagem e rótulo prontos, geometria conferida, foreground idêntico ao
congelado.

---

## 3. O que será medido quando houver modelo — declarado agora, antes de ver qualquer número

Declarar isto **antes** é o que impede escolher a análise depois de ver o resultado.

1. **VALIDATION (n = 6)** — avaliação interna, as oito métricas, tabela por caso com
   `case_id`, dice, iou, precision, recall, hd95, assd, volume GT, volume previsto, erro
   absoluto e erro percentual.
2. **TRAIN (n = 10)** — **apenas** para diagnóstico de ajuste, nunca como resultado.
3. **Por fold** — os cinco preservados, nenhum eleito "o modelo".
4. **Curvas** — *train loss*, *validation loss* e pseudo-Dice por época, dos cinco folds.
5. ***Failure cases*** — pela regra descritiva declarada abaixo, nunca por escolha manual.
6. **Fase respiratória** — `c00`×12, `c80`×2, `c10`×1, `c40`×1. Com **n = 1** em `c10` e
   **n = 1** em `c40`, **nenhuma inferência estatística será feita** — no máximo observação
   descritiva.
7. ***Spacing*** — os casos fora de 0,9766 mm, em caráter diagnóstico. Sem seleção, sem
   exclusão, sem reconfiguração.

### 3.1 A regra de *failure case*, declarada antes

Como o protocolo não define uma, fica declarada aqui, **puramente descritiva**:

> *Failure cases* são os **três casos de menor Dice** na VALIDATION, em ordem crescente, com
> desempate por HD95 maior. Adicionalmente, qualquer caso com **recall < 0,50**,
> **precision < 0,50** ou **predição vazia** é reportado, esteja ou onde estiver no ranking.

Ela é mecânica de propósito: não há espaço para escolher o caso "interessante". **Nenhum
outlier será removido** e o VALIDATION **não será alterado** porque um caso ficou ruim.

---

## 4. O que já se sabe que as limitações serão — independentemente do número

Estas valem qualquer que seja o Dice, e ficam escritas antes para não parecerem desculpa
depois:

| # | Limitação | Consequência |
|---|---|---|
| 1 | **n = 6** na avaliação interna | intervalo largo; nenhuma diferença será conclusiva |
| 2 | **TEST = 0** | **não existe desempenho externo publicável** |
| 3 | mesma coleção, mesmo TPS, mesmo processo de contorno | não há independência de fonte |
| 4 | GT `SEMIAUTOMATIC` em 16/16 | não é anotação humana pura |
| 5 | `institution` e `annotation_protocol` **UNKNOWN** | não se pode falar de instituição |
| 6 | extensão longitudinal **herdada do GT** | não avaliável anatomicamente |
| 7 | pós-processamento escolhido de 10 predições *out-of-fold* | decisão em n minúsculo |
| 8 | fase respiratória heterogênea | dois estratos com n = 1 |

**O modelo é BASELINE INTERNO / EXPERIMENTAL.** Não será descrito como independente, nem como
generalizável para outras instituições, nem como *external-test validated*, e nenhum
resultado interno será convertido em benchmark externo.

---

## 5. Definition of Done — estado honesto

| Item | Estado |
|---|---|
| avaliação interna concluída | **NÃO** — sem modelo |
| métricas por caso | **NÃO** — sem modelo |
| métricas por fold | **NÃO** — sem modelo |
| *failure cases* | **NÃO** — sem modelo (mas a **regra** está declarada, §3.1) |
| análise de overfitting/underfitting | **NÃO** — 2 épocas de 1000 não sustentam leitura |
| análise de fase respiratória | **NÃO** — sem modelo |
| análise de *spacing* | **NÃO** — sem modelo |
| visualizações | **NÃO** — sem predição para visualizar |
| **nenhum TEST utilizado** | **CONFIRMADO** — TEST = 0 e inalcançável de `treino` |
| **nenhum caso externo utilizado** | **CONFIRMADO** — `imagesTr` ⊆ manifesto congelado |
| **nenhuma alteração no dataset** | **CONFIRMADO** — 32/32 originais conferem por `sha256` |
| relatório Fase 27 criado | **OK** — este documento |

---

## 6. Próximos bloqueios científicos, em ordem

1. **Tempo de GPU.** 206,8 h para o protocolo completo. É o bloqueio imediato, e é só recurso.
2. **TEST inexistente.** Enquanto TEST = 0, **nenhum número é desempenho publicável**. E as
   quatro fontes já usadas estão proibidas como TEST — LCTSC, LyNoS, NSCLC-Radiomics e
   SegTHOR. Um TEST independente exige fase própria, e *"independente"* precisa ser
   demonstrado, nunca presumido.
3. **n = 16 no total.** Mesmo com o treino completo, o pool não sustenta afirmação forte.
4. **GT `SEMIAUTOMATIC`.** O teto do que se pode afirmar sobre concordância é limitado pela
   natureza do próprio alvo.
5. **A semente pré-registrada não tem ponto de aplicação** (Fase 26 §6, desvio 2). Se
   reprodutibilidade bit-a-bit vier a ser exigida, isso precisa de solução própria — e ela
   não é escrever um `splits_final.json` à mão sem registrar o motivo.
