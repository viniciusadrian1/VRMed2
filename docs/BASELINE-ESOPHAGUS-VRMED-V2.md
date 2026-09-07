# BASELINE_ESOFAGO_VRMED_V2 — emenda ao pré-registro

Escrito em **2026-09-06** · Fase 26 · Estado: **emenda, com motivo declarado**

> A V1 ([`BASELINE-ESOPHAGUS-VRMED-V1.md`](BASELINE-ESOPHAGUS-VRMED-V1.md)) **permanece
> intacta no histórico**, como ela própria exige: *"Alterar qualquer um destes exige nova
> versão do pré-registro, com data e motivo, e a versão antiga permanece no histórico."*
> Este documento não substitui a V1: ele registra **o que mudou, por quê, e o que
> deliberadamente não mudou.**

---

## 1. Por que existe uma V2

A V1 foi escrita na Fase 19, quando **nenhum caso existia** e o desenho pressupunha que
**haveria um TEST**. A tabela de comandos da V1 diz:

| Passo | Lê |
|---|---|
| `nnUNetv2_plan_and_preprocess -d 501` | **train + validation** |
| `nnUNetv2_train 501 3d_fullres FOLD --npz` | **train + validation** |
| `nnUNetv2_predict` (uma vez, no fim) | **test** |

Naquele desenho, os 16 casos seriam o pool de *cross-validation* e o TEST seria o holdout.
**Hoje TEST = 0**, congelado assim na Fase 25.

Sob a leitura literal da V1 com TEST = 0, o resultado seria: os 16 casos em `imagesTr`, o
*cross-validation* de 5 folds do nnU-Net reparticionando os 16, e **cada um dos 6 casos da
partição VALIDATION usado como dado de treino em 4 dos 5 folds**. Não sobraria nenhum caso
nunca visto por nenhum peso.

---

## 2. O que decidiu a questão: a tabela de permissões congelada

A Fase 25 congelou, em código executável e coberto por mutantes:

```python
PERMISSOES = {"treino": ("train",), "validacao": ("train", "validation"), "avaliacao": ("test",)}
```

O contexto de treino pode ler `train`, **e só `train`**. Colocar os 6 casos de VALIDATION em
`imagesTr` seria exatamente o vazamento que essa tabela existe para impedir — e dois dos 13
mutantes da suíte atacam precisamente essa permissão.

**A V2 obedece à tabela.** A V1 descreveu uma intenção; a Fase 25 congelou uma regra
executável. Onde as duas divergem, vale a regra executável, e a divergência fica escrita aqui.

### 2.1 O argumento mais forte não é o de permissão — é o do planner

Mesmo que os 6 fossem colocados em `imagesTr` e excluídos de todos os folds por um
`splits_final.json` escrito à mão, **eles ainda contaminariam o modelo**.

**FATO.** `nnUNetv2_plan_and_preprocess` extrai a *fingerprint* sobre **todos** os casos de
`imagesTr`: spacing-alvo (mediana dos spacings), estatísticas de intensidade de foreground
que definem a normalização, e daí *patch size* e *batch size*.

**INFERÊNCIA.** Isso é vazamento **transdutivo**: os 6 moldariam o pré-processamento do
modelo sem jamais entrar num lote de treino. As nove regras de split da V1 falam de caso,
estudo, série e conteúdo entre **partições do manifesto** — nenhuma delas fala do planner.
Era uma lacuna real, e ela fica fechada por construção quando `imagesTr` tem só os 10.

**Registro do que a fingerprint realmente viu** (dos 10 de TRAIN, e de mais ninguém):
`spacing` mediano `[3,0 · 0,9766 · 0,9766]` mm, forma mediana `[116 · 512 · 512]`,
intensidade de foreground `média −30,75 · mediana 12,0 · dp 162,51 · p0,5 −932,0 ·
p99,5 141,0` HU.

---

## 3. As quatro emendas

### Emenda 1 — `imagesTr` contém os 10 de TRAIN, não os 16

`numTraining = 10`. Os 6 de VALIDATION ficam **fora da árvore do nnU-Net**, em
`.clinica-dados/fase26/validation_holdout/`. O que não está em `imagesTr` não pode ser
sorteado para treino por engano.

**Motivo:** seções 2 e 2.1. **Alcance:** apenas o mapeamento partição → diretório. As
partições do manifesto congelado **não mudaram**: TRAIN continua os mesmos 10, VALIDATION os
mesmos 6, TEST continua 0.

### Emenda 2 — os 5 folds correm sobre os 10, com a semente do framework

`splits_final.json` foi **gerado pelo próprio nnU-Net**, não escrito por nós: 5 folds, 8
treino / 2 validação interna cada, cobrindo os 10 casos de TRAIN, cada um aparecendo como
validação interna em exatamente um fold.

**E aqui há uma lacuna que precisa ficar registrada, não resolvida em silêncio.**

**FATO.** A V1 fixou `seed = 20260906`. O nnU-Net **fixa a própria semente no código**:

```python
splits = generate_crossval_split(all_keys_sorted, seed=12345, n_splits=5)   # nnUNetTrainer.py:624
rnd = np.random.RandomState(seed=12345 + self.fold)                         # nnUNetTrainer.py:643
```

`nnUNetv2_train` **não aceita parâmetro de semente**. Logo, a semente pré-registrada
**não tem ponto de aplicação** neste caminho.

**Decisão:** manter o `splits_final.json` gerado pelo framework, com `seed=12345`. O comando
da V1 é `nnUNetv2_train ... --npz`, sem sinalizador nenhum — ele vincula os **defaults do
framework**, e a semente de particionamento é um deles. Escrever um `splits_final.json`
nosso faria do split um artefato de desenho nosso, quando o passo 4 da V1 (*"copiar
`splits_final.json` para o snapshot"*) pressupõe um arquivo **gerado**.

**Consequência declarada:** `seed = 20260906` continua registrado no `dataset.json`, no
relatório de ambiente e em `plano.SEED` como **identificador do experimento**, e
**não** como semente efetiva do particionamento nem da inicialização. Chamá-la de semente do
treino seria falso. A V2 não conserta essa lacuna — ela a nomeia.

### Emenda 3 — a partição VALIDATION é holdout pós-treino, e não é um TEST

Os 6 casos são preditos **depois** do treino, com `nnUNetv2_predict`, e avaliados uma vez
pelas oito métricas congeladas.

**Isto NÃO os transforma em TEST**, e a diferença não é de nome:

- o TEST continua **0** e continua **protegido por `AcessoIndevido`**;
- os 6 vêm da **mesma coleção, mesma instituição desconhecida, mesmo TPS e mesmo processo de
  contorno** que os 10 de treino — não há independência de fonte;
- o resultado neles é **desempenho interno na coorte congelada**, nunca desempenho externo.

Nenhum número medido nos 6 pode ser reportado como generalização, como independência, ou
como benchmark. Um TEST de verdade exige uma fase própria, explicitamente autorizada.

### Emenda 4 — o homônimo "validation" fica desambiguado

A V1 anota `nnUNetv2_find_best_configuration` como *"lê validation"*. **São duas coisas
diferentes com a mesma palavra**, e nenhum documento anterior as separou:

| Termo | O que é | n |
|---|---|---|
| `validation` do **nnU-Net** | predições *out-of-fold* do CV interno | 10 (os de TRAIN) |
| `validation` do **manifesto VRmed** | a partição congelada pela `VRMED-SPLIT-RULE-V1` | 6 |

`find_best_configuration` lê **o primeiro**. Ele nunca vê os 6. O pós-processamento é,
portanto, escolhido a partir de 10 predições *out-of-fold* — e essa é uma decisão tomada num
n minúsculo, o que fica declarado como limitação.

---

## 4. O que NÃO mudou

| Item | Estado |
|---|---|
| `ESOPHAGUS_ONTOLOGY_V1` | **intacta**, carimbada no `dataset.json` |
| as oito métricas congeladas | **intactas**, e nenhuma nova entra no critério |
| manifesto congelado e seu `sha256` | **intactos** — `9388c736…82632192` |
| as partições do split | **intactas** — 10 / 6 / 0 |
| `VRMED-SPLIT-RULE-V1` | **intacta** |
| dataset id `501`, configuração `3d_fullres` | **intactos** |
| **os cinco folds, não apenas o `0`** | **intacto** — correm sobre os 10 |
| hiperparâmetros | **intactos por referência**: comando sem sinalizadores ⇒ defaults do nnU-Net |
| TEST | **0, e não será criado nesta fase** |
| critérios de sucesso e de regressão da V1 | **intactos** |

---

## 5. Hiperparâmetros: o que "defaults" quer dizer, explicitamente

A V1 **não especifica** épocas, *trainer*, *batch size*, *loss*, otimizador, agendador nem
augmentação — uma varredura pelos três documentos do pré-registro não encontra nenhuma
ocorrência normativa desses termos. O comando é `nnUNetv2_train 501 3d_fullres FOLD --npz`,
sem sinalizadores.

**Isso não é uma lacuna: é vinculação por referência.** Um comando sem sinalizadores vincula
o `nnUNetTrainer` padrão. Trocá-lo por uma variante mais curta seria inventar um parâmetro
que o protocolo não sustenta. O que o padrão significa, lido do pacote instalado
(`nnunetv2 2.8.1`) e do plano derivado do dado:

| Parâmetro | Valor | Origem |
|---|---|---|
| trainer | `nnUNetTrainer` | default |
| épocas | **1000** | default |
| iterações por época | 250 | default |
| otimizador | SGD, momentum 0,99, nesterov | default |
| *learning rate* | 0,01, decaimento polinomial | default |
| *loss* | Dice + Cross-Entropy, com *deep supervision* | default |
| *batch size* | **2** | derivado do dado pelo planner |
| *patch size* | **48 × 224 × 192** | derivado do dado pelo planner |
| normalização | `CTNormalization` | derivada do dado |
| arquitetura | `PlainConvUNet`, 6 estágios, `(32, 64, 128, 256, 320, 320)` | derivada do dado |

---

## 6. Ordem dos acontecimentos, dita como foi

**FATO.** A decisão das emendas 1 e 2 foi tomada **antes** de a GPU ligar e está codificada em
[`fase26/dataset_nnunet.py`](../scripts/validation/fase26/dataset_nnunet.py), cujo autoteste
de controle negativo falha se o contexto de treino conseguir ler VALIDATION. **Este
documento foi escrito depois, durante a execução do fold 0.**

Isso é registrado porque um pré-registro escrito depois do resultado não é pré-registro. Aqui
não houve resultado nenhum quando a decisão foi tomada — não havia sequer uma época concluída
— mas a ordem exata dos passos é fato, e fica escrita.

---

## 7. O que continua proibido, e não muda com esta emenda

- reportar qualquer número dos 6 como desempenho externo, independência ou generalização;
- preencher o TEST nesta fase;
- usar LCTSC, LyNoS, NSCLC-Radiomics ou SegTHOR;
- usar desempenho para editar dataset, remover caso ou reescolher fold;
- chamar o GT do 4D-Lung de anotação humana pura — ele é `SEMIAUTOMATIC` em 16/16;
- descrever o modelo como algo além de **BASELINE INTERNO / EXPERIMENTAL**.
