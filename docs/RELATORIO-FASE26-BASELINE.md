# Fase 26 — treino do baseline interno

**Data:** 2026-09-06 · **Commit:** `a90d186f11f0d31fbfc0786245f3e838fdbd7ecf`
**Estado final:** **TREINO INICIADO — CONCLUSÃO BLOQUEADA POR TEMPO DE PAREDE**
**Modelo:** BASELINE INTERNO / EXPERIMENTAL

> O bloqueio não é metodológico e não é defeito do protocolo. É custo de máquina, **medido e
> não estimado**: 148,92 s por época × 1000 épocas × 5 folds = **206,8 h ≈ 8,6 dias**.
> Nenhum parâmetro foi encurtado para caber no tempo disponível.

---

## 1. Objetivo

Treinar o primeiro baseline reprodutível do VRmed sobre o pool congelado
`VRMED-ESOPHAGUS-POOL16-V1`, seguindo o pré-registro da Fase 19, sem tocar em TEST, sem
alterar o split e sem inventar hiperparâmetro.

**O objetivo declarado do pré-registro não é desempenho — é auditabilidade.**

---

## 2. Verificação pré-treino — nada ligou a GPU antes disto

Módulo: [`fase26/preflight.py`](../scripts/validation/fase26/preflight.py) · 11 autotestes,
0 falhas · registro em `docs/overnight/phase26/preflight.json`.

| Verificação | Resultado |
|---|---|
| dataset congelado | `VRMED-ESOPHAGUS-POOL16-V1`, 16 entradas |
| **TRAIN / VALIDATION / TEST** | **10 / 6 / 0** — confere com o congelamento |
| congelamento intacto | **sim** |
| `sha256_manifesto` | `9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192` — **confere** |
| ontologia no snapshot | `ESOPHAGUS_ONTOLOGY_V1` |
| arquivos em disco | **32 verificados · 0 ausentes · 0 com hash divergente** |
| manifesto válido pelo esquema | sim, 22 campos |
| TEST alcançável de `treino` / `validacao` | **BLOQUEADO** nos dois |
| TEST alcançável de `avaliacao` | aberto (controle: uma trava que nunca abre é parede) |
| `train` alcançável de `treino` | **10 casos** (controle negativo) |
| **`validation` alcançável de `treino`** | **BLOQUEADO** |
| CUDA | disponível |

**Arquivo presente não bastou.** Os 32 arquivos foram reconferidos por `sha256` contra o que
o manifesto declara — o conteúdo é o congelado, não apenas o caminho.

### 2.1 Ambiente — lido do interpretador, nunca digitado

| | |
|---|---|
| Python | 3.13.11 · Windows-11-10.0.26200-SP0 |
| GPU | **NVIDIA GeForce RTX 4060 Ti · 16.379 MiB** · compute capability 8.9 |
| CUDA | 12.4 · `torch` 2.6.0+cu124 |
| `nnunetv2` | 2.8.1 |
| MONAI | **AUSENTE** (estado esperado, e o relatório reflete a máquina) |

**As 12 versões da tabela do pré-registro conferem uma a uma.** Zero divergências.

*Nota de precisão:* o pré-registro registra a GPU como 16.380 MiB e a leitura desta execução
dá 16.379 MiB. É arredondamento de `total_memory // 1048576`, não outra placa. Fica anotado
para não virar dúvida depois.

---

## 3. Dataset entregue ao nnU-Net

Módulo: [`fase26/dataset_nnunet.py`](../scripts/validation/fase26/dataset_nnunet.py) · 12
autotestes, 0 falhas.

**A única porta de entrada é o carregador guardado:**

```python
man.carregar_particao(entradas, "train", "treino")
```

Não há lista escrita à mão, não há *glob* de diretório, não há filtro por nome.

| | |
|---|---|
| `Dataset501_VRmedEsofago` · `imagesTr` | **10 casos** (a partição TRAIN) |
| holdout, **fora da árvore do nnU-Net** | **6 casos** (a partição VALIDATION) |
| interseção | **vazia** |
| `imagesTr` confere com a partição train | **sim** |
| imagem ↔ rótulo pareados | **sim** |
| caso de VALIDATION dentro de `imagesTr` | **nenhum** |
| conversões com foreground idêntico | **16/16** |
| originais intactos por `sha256` após tudo | **32/32** |

### 3.1 O que foi feito com a máscara — e o que não foi

O nnU-Net exige rótulos `0/1`; as máscaras congeladas são `uint8` com foreground `255`. A
conversão remapeia **o valor do rótulo e nada mais**:

```
novo = (original > 0)   ->   uint8 {0, 1}
```

O **conjunto** de voxels de foreground é idêntico, e isso é **verificado voxel a voxel
relendo do disco**, não afirmado. O autoteste tem controle positivo: apaga um voxel de uma
máscara sintética e exige que o verificador acuse a diferença — um verificador que só diz
"idênticos" não verifica nada.

**Nenhuma operação morfológica, nenhuma reamostragem nossa, nenhum recorte.** As imagens
foram copiadas byte a byte. Os arquivos originais não foram tocados, e os 32 `sha256` foram
reconferidos depois da montagem.

### 3.2 `dataset.json` carimbado

`vrmed_dataset_version`, `vrmed_schema`, **`vrmed_ontology = ESOPHAGUS_ONTOLOGY_V1`**,
`vrmed_split_rule`, `vrmed_sha256_manifesto`, `vrmed_seed`, `vrmed_annotation_method_declared
= SEMIAUTOMATIC`, e a nota de que `imagesTr` contém somente TRAIN.

---

## 4. Protocolo executado

Pré-registro: [`BASELINE-ESOPHAGUS-VRMED-V1.md`](BASELINE-ESOPHAGUS-VRMED-V1.md), emendado
por [`BASELINE-ESOPHAGUS-VRMED-V2.md`](BASELINE-ESOPHAGUS-VRMED-V2.md) (seção 6 abaixo).

```
nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity -c 3d_fullres
nnUNetv2_train 501 3d_fullres 0 --npz
```

### 4.1 Plano derivado do dado, não escolhido por nós

| Parâmetro | Valor | Origem |
|---|---|---|
| *patch size* | **48 × 224 × 192** | planner |
| *batch size* | **2** | planner |
| spacing alvo | **3,0 × 0,9766 × 0,9766** mm | planner |
| normalização | `CTNormalization` | planner |
| arquitetura | `PlainConvUNet`, 6 estágios, `(32, 64, 128, 256, 320, 320)` | planner |
| `batch_dice` | `True` | planner |

*Fingerprint* de intensidade de foreground (dos 10 de TRAIN, **e de mais ninguém**):
média −30,75 · mediana 12,0 · dp 162,51 · p0,5 −932,0 · p99,5 141,0 HU.

### 4.2 Hiperparâmetros: defaults, por vinculação e não por omissão

O pré-registro **não especifica** épocas, *trainer*, *loss*, otimizador nem agendador — uma
varredura pelos três documentos não acha nenhuma ocorrência normativa desses termos. O
comando é `nnUNetv2_train 501 3d_fullres FOLD --npz`, **sem sinalizadores**, e um comando sem
sinalizadores vincula os defaults do framework. Lidos do pacote instalado:

| Parâmetro | Valor | Fonte |
|---|---|---|
| trainer | `nnUNetTrainer` | default |
| **épocas** | **1000** | `nnUNetTrainer.py:159` |
| iterações por época | 250 | `nnUNetTrainer.py:157` |
| iterações de validação | 50 | `nnUNetTrainer.py:158` |
| otimizador | SGD nesterov, momentum 0,99 | default |
| *learning rate* | 0,01, decaimento polinomial | `nnUNetTrainer.py:153` |
| *weight decay* | 3e−5 | `nnUNetTrainer.py:154` |
| *loss* | Dice + Cross-Entropy, com *deep supervision* | default |
| *oversample* de foreground | 0,33 | `nnUNetTrainer.py:155` |

**Nenhum destes foi alterado.** Trocar o trainer por uma variante mais curta seria inventar
um parâmetro que o protocolo não sustenta.

### 4.3 Os cinco folds

`splits_final.json` foi **gerado pelo próprio nnU-Net** sobre os 10 casos de TRAIN:

| fold | treino | validação interna |
|---|---|---|
| 0 | 8 | `4DLUNG-100`, `4DLUNG-111` |
| 1 | 8 | `4DLUNG-106`, `4DLUNG-114` |
| 2 | 8 | `4DLUNG-108`, `4DLUNG-110` |
| 3 | 8 | `4DLUNG-102`, `4DLUNG-112` |
| 4 | 8 | `4DLUNG-105`, `4DLUNG-109` |

Cada um dos 10 aparece como validação interna em **exatamente um** fold. Nenhum dos 6 casos
de VALIDATION aparece em fold nenhum. Cópia versionada em
`docs/overnight/phase26/splits_final.json`.

---

## 5. O bloqueio, medido

**FATO.** Tempos de época reais do fold 0, lidos do log:

```
Epoch 0   Epoch time: 155.08 s   train_loss  0.0480   val_loss  0.0017   pseudo dice 0.0
Epoch 1   Epoch time: 142.75 s   train_loss -0.0209   val_loss -0.1069   pseudo dice 0.0
```

**Média medida: 148,92 s por época.**

| | |
|---|---|
| 1000 épocas (1 fold) | **41,4 h** |
| 5 folds | **206,8 h ≈ 8,6 dias** |

**INFERÊNCIA.** O protocolo pré-registrado é **executável**, mas não neste lote: ele exige
~8,6 dias de GPU dedicada. O bloqueio é de recurso, não de método.

**Decisão, e o que ela NÃO foi.** Registrar o bloqueio e parar o avanço de fase. **Não** se
reduziu o número de épocas, **não** se trocou o trainer por uma variante curta, **não** se
reduziu para um fold só, e **não** se declarou concluído o que não concluiu. A regra desta
execução proíbe improvisar um protocolo mais barato, e a proibição foi respeitada.

*Sobre os números das duas épocas:* `pseudo dice 0.0` e o *loss* caindo para negativo são o
comportamento normal do início de um treino nnU-Net (a componente Dice do *loss* é negativa
por construção). **Duas épocas de 1000 não sustentam nenhuma leitura sobre qualidade**, e
nenhuma é feita aqui.

---

## 6. Desvios metodológicos — seção própria, como exigido

Os quatro desvios estão formalizados em
[`BASELINE-ESOPHAGUS-VRMED-V2.md`](BASELINE-ESOPHAGUS-VRMED-V2.md), com a V1 preservada
intacta no histórico, como a própria V1 exige.

### Desvio 1 — `imagesTr` tem 10 casos, e não 16

**O que a V1 dizia:** `plan_and_preprocess` e `train` *"leem train + validation"*.
**O que foi feito:** `imagesTr` = somente a partição TRAIN.

**Motivo, e ele é duplo.**

*Primeiro, a tabela de permissões congelada na Fase 25 já responde a questão, em código
executável:* `PERMISSOES = {"treino": ("train",), ...}`. O contexto de treino lê `train`, e só.
Dois dos 13 mutantes da suíte atacam exatamente essa permissão.

*Segundo, e mais forte: vazamento transdutivo.* `plan_and_preprocess` extrai a *fingerprint*
sobre **todos** os casos de `imagesTr` — spacing alvo, estatísticas de intensidade que
definem a normalização, e daí *patch* e *batch size*. Se os 6 estivessem lá, **moldariam o
pré-processamento do modelo mesmo sem entrar em nenhum lote de treino**. As nove regras de
split da V1 falam de caso, estudo, série e conteúdo entre partições — **nenhuma fala do
planner**. Era lacuna real, e fica fechada por construção.

**Consequência da leitura literal, se tivesse sido seguida:** com TEST = 0, os 6 casos de
VALIDATION seriam dados de treino em 4 dos 5 folds, e **não sobraria nenhum caso nunca
visto**.

### Desvio 2 — a semente pré-registrada não tem ponto de aplicação

**FATO.** A V1 fixou `seed = 20260906`. O nnU-Net fixa a própria semente **no código**:

```python
splits = generate_crossval_split(all_keys_sorted, seed=12345, n_splits=5)   # nnUNetTrainer.py:624
rnd = np.random.RandomState(seed=12345 + self.fold)                        # nnUNetTrainer.py:643
```

`nnUNetv2_train` **não aceita parâmetro de semente**.

**Decisão:** manter o `splits_final.json` gerado pelo framework. O comando sem sinalizadores
vincula os defaults, e a semente de particionamento é um deles; escrever um arquivo nosso
faria do split um artefato de desenho nosso, quando o passo 4 da V1 pressupõe um arquivo
*gerado*.

**Consequência declarada:** `seed = 20260906` permanece registrado como **identificador do
experimento**, e **não** como semente efetiva do particionamento ou da inicialização.
Chamá-la de semente do treino seria falso. **Esta lacuna é nomeada, não consertada.**

### Desvio 3 — a partição VALIDATION é holdout pós-treino, e não é um TEST

Os 6 casos serão preditos depois do treino e avaliados uma vez. **Isto não os transforma em
TEST:** vêm da mesma coleção, mesma instituição desconhecida, mesmo TPS e mesmo processo de
contorno que os 10 de treino. O resultado neles é **desempenho interno na coorte congelada**.
O TEST continua 0 e continua protegido por `AcessoIndevido`.

### Desvio 4 — o homônimo "validation" fica desambiguado

| Termo | O que é | n |
|---|---|---|
| `validation` do **nnU-Net** | predições *out-of-fold* do CV interno | 10 (os de TRAIN) |
| `validation` do **manifesto VRmed** | a partição congelada | 6 |

`nnUNetv2_find_best_configuration`, anotado na V1 como *"lê validation"*, lê **o primeiro**.
Nunca vê os 6. Nenhum documento anterior separava as duas coisas.

---

## 7. Incidentes

### Incidente 1 — dois treinos concorrentes no mesmo `fold_0`

**O que houve.** O primeiro lançamento usou `nohup ... &` dentro de uma chamada de shell. O
processo **sobreviveu** ao encerramento do shell, contrariando a suposição de que morreria
junto. Um segundo lançamento foi feito, e **dois treinos passaram a escrever no mesmo
diretório `fold_0`**, disputando a GPU.

**Como foi detectado.** Dois arquivos `training_log_*.txt` no mesmo `fold_0`, e quatro
processos `run_training` na lista de processos.

**Correção.** Ambos os processos encerrados; **os dois logs preservados** em
`docs/overnight/phase26/logs/incidente_treino_duplicado/` antes de qualquer limpeza;
`fold_0` limpo; um único treino relançado.

**Consequência sobre os números.** A primeira medição de tempo de época estava contaminada
por dois processos disputando a mesma GPU e **foi descartada**. Os 148,92 s da seção 5 são de
execução única e limpa. O `splits_final.json` não foi regerado — é o mesmo arquivo desde a
primeira execução, e está versionado.

**Nenhuma evidência foi apagada.**

### Não-incidente registrado

`Unable to plot network architecture: No module named 'hiddenlayer'` — o nnU-Net não
consegue desenhar o diagrama da rede. É cosmético, não afeta treino nem pesos, e fica
anotado para não virar dúvida na leitura do log.

---

## 8. Checkpoints

**Nenhum checkpoint foi produzido.** O nnU-Net salva `checkpoint_latest.pth` a cada 50
épocas e `checkpoint_best.pth` quando a métrica de validação interna melhora; o treino não
alcançou a época 50. O diretório `fold_0` contém, até aqui, `debug.json` e o log.

Nada foi apagado além do `fold_0` do incidente 1, cujos logs estão preservados.

---

## 9. Testes

**Arquivos de teste — 72/72:**

| Arquivo | Resultado |
|---|---|
| `tests/test_geometria.py` | 10/10 |
| `tests/test_controles_positivos.py` | 8/8 |
| `tests/test_ontologia_esofago.py` | 13/13 |
| `tests/test_baseline_v1.py` | 18/18 |
| `tests/test_fase25_congelamento.py` | 11/11 |
| **`tests/test_fase26_treino.py`** | **12/12** — novo |

`test_fase26_treino.py` é o teste que o pedido exigiu por nome. Ele cai se alguém preencher o
TEST, colocar um caso de VALIDATION em `imagesTr`, alterar o manifesto ou o snapshot, mudar a
composição do split, trocar os folds por outros que não cubram exatamente os 10, ou tirar o
carimbo da ontologia do `dataset.json`. Quando os artefatos de `.clinica-dados/` não existem,
os testes que dependem deles são **PULADOS de forma contada** — "pulou" e "passou" não são a
mesma coisa.

**Autotestes de módulo — 203/203, 0 falhas:** `manifesto` 29 · `plano` 14 · `candidatos` 7 ·
`funil` 16 · `mutacao` 31 · `anonimizacao` 11 · `aquisicao` 14 · `ingerir_real` 8 · `pool` 5 ·
`consolidar` 8 · `split` 13 · `congelar` 12 · **`preflight` 11** · **`dataset_nnunet` 12** ·
**`avaliar` 12**.

**Varredura de documentos:** 59 documentos, **0 violações**.

*Nota de ambiente:* `pytest` não está instalado no `.venv-pipeline`; os arquivos de teste
rodam como programas autônomos e foi assim que foram executados.

---

## 10. Controles contra vazamento — estado após o treino iniciado

| # | Controle | Estado |
|---|---|---|
| 1 | nenhum TEST foi usado | **confirmado** — TEST = 0, e inalcançável de `treino` |
| 2 | nenhum caso externo foi usado | **confirmado** — `imagesTr` ⊆ manifesto congelado |
| 3 | nenhum VALIDATION foi usado como treino | **confirmado** — interseção vazia, em disco |
| 4 | nenhum caso duplicado entrou | **confirmado** — 10 arquivos, 10 ids distintos |
| 5 | `sha256` do manifesto inalterado | **confirmado** — `9388c736…82632192` |
| 6 | snapshot inalterado | **confirmado** |
| 7 | split inalterado | **confirmado** — 10 / 6 / 0 |
| 8 | nenhum artefato do dataset alterado | **confirmado** — 32/32 originais por `sha256` |

---

## 11. Status final

| Item da Definition of Done | Estado |
|---|---|
| dataset correto verificado | **OK** |
| TRAIN = 10 · VALIDATION = 6 · TEST = 0 | **OK** |
| manifesto / snapshot / split intactos | **OK** |
| protocolo verificado | **OK** |
| ambiente registrado | **OK** |
| **treinamento executado** | **PARCIAL — iniciado, 2 de 1000 épocas do fold 0 de 5** |
| **checkpoints preservados** | **N/A — nenhum produzido (época < 50)** |
| resultados registrados | **OK** — `docs/overnight/phase26/run_fold0.json` |
| relatório Fase 26 criado | **OK** |

**FASE 26: BLOQUEADA POR TEMPO DE PAREDE.** Infraestrutura, dataset, protocolo, desvios,
travas e testes: todos concluídos e verificados. O que falta é exclusivamente **tempo de
GPU**, quantificado em 206,8 h.

**A Fase 27 NÃO foi iniciada**, porque o pedido a condiciona explicitamente a *"Fase 26
concluir sem bloqueio"*.

---

## 12. Arquivos gerados

| Caminho | O que é |
|---|---|
| `docs/BASELINE-ESOPHAGUS-VRMED-V2.md` | emenda ao pré-registro, com os 4 desvios |
| `docs/overnight/phase26/preflight.json` | verificação pré-treino completa |
| `docs/overnight/phase26/dataset_nnunet.json` | montagem do dataset e provas de conversão |
| `docs/overnight/phase26/splits_final.json` | os 5 folds, versionados |
| `docs/overnight/phase26/run_fold0.json` | configuração, tempos, *loss*, projeção |
| `docs/overnight/phase26/logs/incidente_treino_duplicado/` | os dois logs do incidente 1 |
| `scripts/validation/fase26/preflight.py` | 11 autotestes |
| `scripts/validation/fase26/dataset_nnunet.py` | 12 autotestes |
| `scripts/validation/fase27/avaliar.py` | 12 autotestes — pronto, ainda não usado |
| `tests/test_fase26_treino.py` | 12 controles anti-vazamento |

Artefatos pesados (dados pré-processados, pesos) em `.clinica-dados/fase26/`, fora do git.
**Nenhum diretório de fase anterior foi escrito.**

---

## 13. Como retomar

```
nnUNetv2_train 501 3d_fullres 0 --npz --c      # continua do último checkpoint
nnUNetv2_train 501 3d_fullres 1 --npz          # folds 1 a 4
```

com `nnUNet_raw`, `nnUNet_preprocessed` e `nnUNet_results` apontando para
`.clinica-dados/fase26/`. Custo medido: **41,4 h por fold**.
