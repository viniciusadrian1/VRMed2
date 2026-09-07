# Fase 26A — decisão de regra de parada do baseline

**Data:** 2026-09-07 · **Commit:** `ce29dbf` · **Estado:** treino **PAUSADO**, decisão tomada
**Recomendação:** **MANTER O PROTOCOLO.** *Early stopping* **não** é recomendado. **V3 não é
necessária.**

> A pergunta que originou a fase — *"early stopping evitaria sobreajuste e computação
> desnecessária?"* — tem duas metades, e elas têm respostas diferentes. A metade do
> sobreajuste **não se resolve com early stopping neste framework**. A metade da computação é
> real, mas é argumento econômico, e a instrução desta fase proíbe decidir por economia.

---

## 1. Estado atual da execução

Registro completo em `docs/overnight/phase26a/estado_ao_pausar.json`.

| | |
|---|---|
| fold | **0**, de 5 planejados |
| épocas concluídas | **64 de 1000 (6,4 %)** |
| folds concluídos | **0** |
| tempo de época | média 140,42 s · últimas 20: **139,73 s** · min 138,27 · max 155,08 |
| arquivos preservados | `checkpoint_best.pth` (245.765.782 B), `checkpoint_latest.pth` (245.764.234 B), `debug.json`, `progress.png`, `training_log_2026_9_6_23_29_47.txt` |

**Correção de registro.** O `RELATORIO-FASE26-BASELINE.md` diz *"2 de 1000 épocas"*. Isso
estava correto **no momento em que foi escrito** (23h40); o treino continuou rodando e chegou
a **64 épocas** antes da pausa. O relatório da Fase 26 **não foi alterado** — a correção fica
aqui, com a razão, e o histórico permanece.

**Um fold parcial não é experimento concluído.** Nenhuma métrica científica sai daqui, e
nenhuma é produzida neste relatório.

*Sobre o `pseudo dice` que aparece no log (melhor 0,7636 na época 52):* é sinal de
acompanhamento do nnU-Net calculado sobre os **2 casos de validação interna do fold 0**, sobre
recortes e não sobre o volume reconstruído. Não é desempenho, não é o Dice final, e não foi
medido nos 6 casos do holdout. **Não é usado como base para nenhuma decisão desta fase** — a
instrução do Passo 7 é explícita, e vale igualmente para 64 épocas.

---

## 2. Arqueologia do protocolo

### O que a V1 **exige** explicitamente

| Item | Estado na V1 |
|---|---|
| dataset `501`, configuração `3d_fullres` | **exigido** |
| **os cinco folds, não apenas o `0`** | **exigido** — *"Folds: os cinco, não apenas o `0`."* |
| `seed = 20260906` | **exigido** (mas sem ponto de aplicação — V2, desvio 2) |
| as oito métricas congeladas | **exigido** |
| pré-processamento do nnU-Net, sem etapa nossa | **exigido** |
| pós-processamento | só o que `find_best_configuration` escolher **do validation**, nunca do TEST |
| **número de épocas** | **SILENCIOSA** |
| **critério de parada** | **SILENCIOSA** |
| ***trainer*** | **SILENCIOSA** |
| **qual checkpoint é o modelo final** | **SILENCIOSA** |

Os comandos da V1 são `nnUNetv2_train 501 3d_fullres FOLD --npz` — **sem sinalizadores**.
Silêncio + comando nu = **vinculação por referência aos defaults do framework**.

### A cláusula de emenda da V1

> *"Alterar qualquer um destes exige nova versão do pré-registro, com data e motivo, e a
> versão antiga permanece no histórico."*

A lista protegida é: TEST não usado para seleção; manifesto e `sha256`; o split; a ontologia e
as oito métricas; o `seed`; e os critérios de sucesso e regressão.

**Nenhum critério de sucesso ou de regressão da V1 depende de número de épocas ou de critério
de parada.** Os cinco critérios de sucesso são **procedimentais**, e a V1 é explícita: *"Um
modelo que satisfaz os cinco é aceito qualquer que seja o Dice."*

### O que a V2 mudou

Os quatro desvios já documentados: `imagesTr` = 10 e não 16 (permissões + vazamento
transdutivo); semente efetiva 12345 e não 20260906 (lacuna nomeada); VALIDATION é holdout
pós-treino e não TEST; homônimo "validation" desambiguado.

---

## 3. O que o nnU-Net 2.8.1 instalado realmente faz

Tudo abaixo foi lido do pacote em `.venv-pipeline/Lib/site-packages/nnunetv2`, não de memória.

### 3.1 *Early stopping*: **não existe**

**FATO.** Varredura de todo o pacote por `early_stop`, `earlystop`, `EarlyStopping`,
`patience`, `no_improvement`, `should_stop`, `stop_training`: **zero ocorrências**.

**FATO.** O laço de treino é fixo, e não tem `break`:

```python
for epoch in range(self.current_epoch, self.num_epochs):   # nnUNetTrainer.py:1420
    self.on_epoch_start()
    ...
    self.on_epoch_end()
self.on_train_end()
```

**FATO.** `nnUNetv2_train` **não aceita** nenhuma flag de parada ou *patience*.

**Ressalva de escopo, para a afirmação ser exata.** Existe **um** `try/except RuntimeError` em
volta de um laço de treino no pacote — mas apenas em
`nnUNetTrainerBenchmark_5epochs_noDataLoading.py`, e ele serve para **registrar crash**
(`crashed_with_runtime_error`), nunca para parar por critério de métrica. O
`nnUNetTrainer` base, que é o que este projeto usa, **não tem esse tratamento**. E
`checkpoint_best` / `_best_ema` salvam o melhor modelo, mas **nunca interrompem o laço**.

**Resposta às perguntas do Passo 3:**

| # | Pergunta | Resposta |
|---|---|---|
| 1 | *Early stopping* é suportado? | **NÃO** |
| 2 | Está ligado por default? | **NÃO** — não existe |
| 3 | Como seria habilitado? | **Escrevendo uma subclasse nova de `nnUNetTrainer`** |
| 4 | Que sinal decidiria a parada? | Teria de ser `ema_fg_dice` — o único sinal de validação por época |
| 5 | Esse sinal vem só do fold interno 8/2? | **Sim** (§3.2 e §5) |
| 6 | Tocaria nos 6 do holdout? | **Não** — eles não existem em nenhuma árvore que o *dataloader* enxerga |
| 7 | Que *patience* seria possível? | Qualquer um — **e é exatamente esse o problema** (§6) |
| 8 | O que aconteceria com o "melhor checkpoint"? | Continuaria existindo; *early stopping* não o altera |
| 9 | E com a seleção do modelo final? | Mudaria: `checkpoint_final` passaria a ser a época da parada |
| 10 | Seria emenda de protocolo? | **Sim** — e emenda que exige **código novo** |

### 3.2 O que existe no lugar: seleção de checkpoint por validação interna

**FATO.** A cada época:

```python
if self._best_ema is None or self.logger.get_value('ema_fg_dice', step=-1) > self._best_ema:
    self._best_ema = self.logger.get_value('ema_fg_dice', step=-1)
    self.save_checkpoint(join(self.output_folder, 'checkpoint_best.pth'))   # :1185-1188
```

E a EMA é determinística, com coeficiente fixo:

```python
new_ema_pseudo_dice = self.get_value('ema_fg_dice', step=step-1) * 0.9 + 0.1 * value  # MetaLogger.log
```

`mean_fg_dice` vem de `tp/fp/fn` acumulados nas 50 iterações de validação do **fold interno**
— 2 dos 10 casos de TRAIN. **Sem sorteio, sem parâmetro escondido.**

### 3.3 O achado que inverte a leitura fácil

**FATO.** O `checkpoint_best.pth` **não é o que a inferência usa por padrão**:

```python
parser.add_argument('-chk', type=str, required=False, default='checkpoint_final.pth')  # predict_from_raw_data.py:843
```

E `checkpoint_final.pth` são **os pesos da última época**:

```python
def on_train_end(self):
    self.current_epoch -= 1
    self.save_checkpoint(join(self.output_folder, "checkpoint_final.pth"))   # :987
    ...
    os.remove(join(self.output_folder, "checkpoint_latest.pth"))
```

**INFERÊNCIA — e é o ponto central desta fase.** Seria fácil concluir *"o nnU-Net já protege
contra sobreajuste, porque salva o melhor checkpoint"*. **Isso está errado por default.** Ele
salva o melhor, mas **entrega o último**. A proteção existe no disco e não está ligada.

### 3.4 Variantes de duração

**FATO.** `nnUNetTrainer_Xepochs.py` traz variantes prontas (5, 10, 20, 50, 100, 250, 500,
750, 1000, 2000, 4000, 8000 épocas), e cada uma altera **uma única linha**:

```python
class nnUNetTrainer_250epochs(nnUNetTrainer):
    def __init__(self, ...):
        super().__init__(...)
        self.num_epochs = 250
```

**FATO.** O agendador é construído sobre `self.num_epochs`:
`PolyLRScheduler(optimizer, self.initial_lr, self.num_epochs)`, com
`lr = initial_lr · (1 − passo/max_passos)^0,9`.

**INFERÊNCIA.** Um orçamento menor é um treino **recozido**, não um treino de 1000 truncado: a
taxa de aprendizado decai completamente dentro do novo orçamento.

**E aqui vai o limite dessa inferência, porque ela é fácil de esticar demais.** "Recozido" não
quer dizer "convergido". `num_iterations_per_epoch` continua **250** em qualquer variante,
então 250 épocas são **62.500 iterações contra 250.000** — **um quarto do orçamento de
otimização**. O que se ganha é uma curva de *learning rate* bem-formada sobre quatro vezes
menos passos de gradiente, e o esperado é um Dice **inferior** ao do orçamento cheio. Um
orçamento menor produz um modelo **legítimo e comparável a si mesmo**, não um substituto
equivalente do baseline de 1000 épocas.

---

## 4. Tabela de custo

Com **148,92 s/época** (medição limpa inicial, a pedido do Passo 5) e, entre parênteses, com
**139,73 s/época** (média medida das últimas 20 épocas):

| épocas | 1 fold | 5 folds |
|---|---|---|
| 50 | 2,07 h (1,94) | 10,3 h (9,7) |
| 100 | 4,14 h (3,88) | 20,7 h (19,4) |
| 150 | 6,20 h (5,82) | 31,0 h (29,1) |
| 200 | 8,27 h (7,76) | 41,4 h (38,8) |
| 300 | 12,41 h (11,64) | 62,0 h (58,2) |
| 500 | 20,68 h (19,41) | 103,4 h (97,0) |
| **1000** | **41,37 h** (38,81) | **206,8 h** (194,1) |

**Estes são pontos de referência de custo, não pontos de parada esperados.**

---

## 5. Análise de vazamento — os 6 do holdout

**Provado em disco, não afirmado:**

| Árvore | Arquivos | Caso do holdout presente? |
|---|---|---|
| `nnUNet_raw/.../imagesTr` | 10 | **NENHUM** |
| `nnUNet_raw/.../labelsTr` | 10 | **NENHUM** |
| `nnUNet_preprocessed/.../nnUNetPlans_3d_fullres` | 30 | **NENHUM** |
| `nnUNet_preprocessed/.../gt_segmentations` | 10 | **NENHUM** |
| os 5 folds de `splits_final.json` | universo de 10 | **NENHUM** |

`dataset.json` → `numTraining = 10`. Universo dos folds **== partição train**, exatamente.

**Cadeia do sinal.** `checkpoint_best` ← `ema_fg_dice` ← `mean_fg_dice` ← `tp/fp/fn` do
`dataloader_val` ← `nnUNet_preprocessed/Dataset501` ← **somente os 10 de TRAIN**. Como os 6 não
existem em nenhum ponto dessa cadeia, **nenhum sinal derivado deles pode existir** — nem para
*early stopping*, nem para checkpoint, nem para qualquer outra decisão.

**Contextos:** `treino` → só `train`; `test` e `validation` inalcançáveis de `treino`
(`AcessoIndevido`); TEST continua **vazio**. Controle negativo: `treino` **lê** os 10 de
`train`, então o guarda não está simplesmente proibindo tudo.

### 5.1 Que tipo de barreira é essa — dito com precisão

Cinco vetores de ataque foram tentados contra a garantia (variável de ambiente, *glob* do
dataset, cascata, `sampling_probabilities`, `split = "all"`) e **nenhum alcança o holdout**.

Mas a natureza da barreira precisa ficar clara, porque ela **não é um `assert` no código do
nnU-Net**: é **configuração mais ausência física dos arquivos**. Os 6 casos nunca foram
pré-processados, então não existem `.b2nd` para eles.

**INFERÊNCIA, e é uma boa notícia.** Se alguém repontasse `nnUNet_preprocessed` para outra
árvore, ou editasse `splits_final.json` para incluir `4DLUNG-101/103/104/107/115/116`, o
*dataloader* tentaria abrir um arquivo inexistente e **quebraria com erro duro**. O caminho de
vazamento é **um crash, nunca contaminação silenciosa** — que é exatamente o modo de falha que
se quer, já que contaminação silenciosa é a que não se descobre.

---

## 6. Comparação metodológica

### Opção A — manter 1000 épocas, exatamente como está

| Critério | Avaliação |
|---|---|
| validade metodológica | **alta** — é o protocolo pré-registrado, vinculado por referência |
| risco de vazamento | **nulo** |
| reprodutibilidade | **alta** — zero código novo, zero discricionariedade nossa |
| custo | **206,8 h** |
| compatibilidade V1/V2 | **total** |
| ponto fraco | entrega os pesos da **última época** (§3.3); com 8 casos de treino por fold, o risco de sobreajuste no modelo entregue é real e **não mitigado por default** |

### Opção B — *early stopping* por validação interna

| Critério | Avaliação |
|---|---|
| validade metodológica | **baixa** |
| risco de vazamento | **nulo** quanto aos 6 — mas esse nunca foi o risco aqui |
| reprodutibilidade | **reduzida** — exige **subclasse nova de trainer**, código não testado, no caminho crítico |
| custo | menor, mas **desconhecido antes de rodar** |
| compatibilidade V1/V2 | exige emenda **e** código novo |
| ponto fraco decisivo | **exigiria escolher `patience`, `min_delta` e a métrica monitorada sem nenhuma evidência para calibrá-los.** Qualquer valor seria arbitrário — e a instrução proíbe escolher *patience* por conveniência de tempo |

**Riscos concretos de escrever esse código:** um bug numa subclasse de trainer é silencioso —
ele produz um modelo, não um erro; a parada passaria a depender de um sinal calculado sobre
**2 casos**, que é ruidoso por construção (o `pseudo dice` do fold 0 oscilou 0,678–0,764 em 10
épocas); e `checkpoint_final` passaria a ser "a época em que parou", o que torna a comparação
entre folds menos interpretável, já que cada fold pararia numa época diferente.

### Opção C — orçamento máximo emendado formalmente

| Critério | Avaliação |
|---|---|
| validade metodológica | **média** |
| risco de vazamento | **nulo** |
| reprodutibilidade | **alta** — usa variante **já distribuída** no pacote, zero código novo |
| custo | proporcional ao orçamento |
| compatibilidade V1/V2 | exige emenda (V3) |
| ponto fraco | **não há evidência que justifique 250 em vez de 500 ou 100.** Qualquer número seria escolhido por custo — exatamente o que a instrução proíbe |

---

## 7. Recomendação

### **MANTER O PROTOCOLO. Não implementar *early stopping*. V3 não é necessária.**

**Por que não *early stopping* (Opção B):**

1. **Não existe no framework.** Habilitá-lo significa escrever código novo no caminho crítico
   de um experimento cujo objetivo declarado é **auditabilidade**. Trocar zero linhas por N
   linhas não auditadas é mover na direção errada.
2. **Os parâmetros seriam arbitrários.** *Patience*, `min_delta` e métrica teriam de ser
   fixados sem nenhuma evidência. A única evidência disponível são 64 épocas de um fold —
   e usá-la seria exatamente o que o Passo 7 proíbe.
3. **O sinal é ruidoso demais para governar uma parada.** `ema_fg_dice` vem de **2 casos**.
4. **O ganho que ele busca já está disponível sem código novo** — ver abaixo.

**Por que não mudar o orçamento de épocas (Opção C):** não há evidência que sustente um número
em vez de outro. Escolher seria decidir por custo, e a instrução proíbe.

**Por que V3 não é necessária:** a lista protegida pela cláusula de emenda da V1 não inclui
número de épocas nem critério de parada, e **nenhum critério de sucesso ou regressão depende
deles**. Manter o protocolo não altera nada, logo não há o que emendar.

### O que **deve** ser feito, e não é *early stopping*

**A pergunta certa não é "quando parar" — é "qual checkpoint é entregue".**

O nnU-Net treina o orçamento inteiro e salva **dois** modelos: `checkpoint_best.pth`
(melhor EMA da validação interna) e `checkpoint_final.pth` (última época). A inferência usa
**o último**, por default. Isso é uma escolha implícita que ninguém declarou.

**Regra declarada agora, antes de qualquer resultado existir** — ela pertence ao plano de
análise da Fase 27, não ao protocolo de treino, e por isso não é emenda:

| | |
|---|---|
| **primário** | **`checkpoint_final.pth`** — o default do framework, nenhuma discricionariedade nossa exercida |
| **secundário** | **`checkpoint_best.pth`** — selecionado por `ema_fg_dice` (EMA α = 0,1 sobre `mean_fg_dice` do fold interno) |
| regra de uso | **os dois são medidos e os dois são reportados, sempre.** O primário é o resultado. O secundário é análise de sensibilidade declarada |
| proibição | **é proibido trocar o primário pelo secundário depois de ver qual deu melhor nos 6 casos.** Isso seria seleção de modelo no holdout |

Por que o primário é o `final` e não o `best`: manter o default é a escolha que **não** exerce
discricionariedade — o mesmo princípio que manteve `seed = 12345` na V2. E `ema_fg_dice`
calculado sobre 2 casos é ruidoso o bastante para que "melhor EMA" não signifique
necessariamente "melhor modelo".

Custo desta regra: **zero** treino adicional. Os dois checkpoints saem da mesma execução.

### E o custo de 206,8 h?

**Continua de pé, e continua sendo o bloqueio prático.** Esta fase não o resolve, porque
resolvê-lo por decisão metodológica seria decidir por economia.

Se você quiser um resultado antes disso, o caminho honesto é uma **fase experimental separada
e explicitamente autorizada** — por exemplo `nnUNetTrainer_250epochs` nos 5 folds (~48,6 h) —
que produz diagnóstico da Fase 27 e **não** é o baseline. O baseline pré-registrado de 1000
épocas continua sendo o canônico, pendente, declarado como dívida. Isso não é emenda: é outro
experimento, com outro nome.

---

## 8. Testes

**`tests/test_fase26a_regra_de_parada.py` — 14/14, 0 falhas.**

Metade deles não olha o VRmed: olha o `nnunetv2` **instalado**. Se alguém atualizar o pacote
ou instalar uma variante com parada própria, as conclusões desta fase deixariam de valer em
silêncio. Estes testes são o alarme.

| # | O que trava |
|---|---|
| 1 | o pacote instalado **não tem** nenhum termo de parada antecipada |
| 2 | o laço de treino é `for` fixo sobre `num_epochs`, **sem `break`** |
| 3 | o orçamento default continua **1000**, com 250 iterações/época |
| 4 | `checkpoint_best` continua saindo de `ema_fg_dice` |
| 5 | a EMA é determinística, coeficiente fixo, **sem aleatoriedade** |
| 6 | **nenhum critério de parada aleatório** (`random`, `np.random`, `torch.rand`, `shuffle`) |
| 7 | a variante de épocas altera **somente** `num_epochs` |
| 8 | o agendador recoze **dentro** do orçamento |
| 9 | os 6 do holdout **não estão** em `imagesTr` nem `labelsTr` |
| 10 | **nem no pré-processado** — `imagesTr` limpo não bastaria |
| 11 | **nenhum fold** contém caso do holdout |
| 12 | o universo pré-processado **é exatamente** a partição train |
| 13 | manifesto e snapshot **inalterados** |
| 14 | split inalterado, TEST inacessível, com controle negativo |

**Suíte completa — 86/86:** `geometria` 10 · `controles_positivos` 8 · `ontologia_esofago` 13 ·
`baseline_v1` 18 · `fase25_congelamento` 11 · `fase26_treino` 12 · **`fase26a_regra_de_parada` 14**.

**Nenhum teste existente foi enfraquecido.**

---

## 9. Respostas diretas ao Passo 3

1. **Early stopping é suportado?** Não.
2. **Ligado por default?** Não existe.
3. **Como habilitar?** Subclasse nova de `nnUNetTrainer`. Código novo.
4. **Sinal de parada?** Seria `ema_fg_dice`.
5. **Só do split interno 8/2?** Sim.
6. **Tocaria nos 6?** Não — provado em disco e por teste.
7. **Patience possível?** Qualquer valor — e não há evidência para escolher nenhum.
8. **Melhor checkpoint?** Continua existindo; não é alterado por *early stopping*.
9. **Seleção do modelo final?** Mudaria: `checkpoint_final` viraria a época da parada.
10. **É emenda de protocolo?** Sim, e com código novo.

---

## 10. O que esta fase não fez

Não retomou o treino, não lançou fold nenhum, não alterou dataset, split, manifesto,
snapshot ou ontologia, não preencheu o TEST, não calculou desempenho científico, e não apagou
nada. A única ação relacionada a GPU foi **parar** o treino e **inspecionar** instalação, código
e logs.
