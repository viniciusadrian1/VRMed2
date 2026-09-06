# BASELINE_ESOFAGO_VRMED_V1 — pré-registro interno

Escrito em **2026-09-06** · Fase 19 · Estado: **PRÉ-REGISTRO — não treinado**

> **Pré-registro não é permissão para treinar.** Este documento fixa o que será feito
> *se* e *quando* os dados existirem. Hoje eles não existem, e o treino está
> **BLOQUEADO POR DADO**. O valor de um pré-registro está inteiramente em ter sido
> escrito **antes** — depois, ele é só uma descrição.

---

## Objetivo

Construir um baseline de segmentação de esôfago torácico cuja **independência seja
demonstrável desde o começo**, em contraste com o `BASELINE_ESOFAGO_V1` atual
(TotalSegmentator 2.18.0), cuja independência a Fase 16 mediu como **indeterminada por
construção**.

**O objetivo não é desempenho.** É auditabilidade. Um baseline pior e auditável responde
uma pergunta que um baseline melhor e opaco não responde.

## Dataset

[`VRMED-ESOPHAGUS-DATASET-V1`](VRMED-ESOPHAGUS-DATASET-V1.md) — 22 campos obrigatórios
por caso, `UNKNOWN` explícito nunca estimado, `sha256` de imagem e de máscara, manifesto
JSONL canônico com `sha256` próprio.

**Estado: ESQUEMA VAZIO.** Nenhum caso ingerido. A ingestão reusa o funil que já existe
em [`dataset_esofago.py`](../scripts/validation/tier2/dataset_esofago.py), com as três
recusas: procedência (`gt_humano` sem valor padrão), grade (sem reamostragem, nunca) e
máscara vazia.

## Ontologia

[`ESOPHAGUS_ONTOLOGY_V1`](ESOPHAGUS-ONTOLOGY-V1.md), congelada em 2026-09-06.

Máscara binária **preenchida**; parede e lúmen são **um objeto**; extensão longitudinal
**herdada do GT e não avaliável anatomicamente**; RTOG 1106 como protocolo de referência.

**Não haverá segunda definição.** O `dataset.json` do nnU-Net carimba a versão da
ontologia, e o teste 13 da suíte falha se o alvo do baseline divergir dela.

## Split

Desenho em [`VRMED-ESOPHAGUS-DATASET-V1` §4](VRMED-ESOPHAGUS-DATASET-V1.md#4-split--o-desenho-não-a-lista).
Nove regras, todas verificadas por código; quatro identidades checadas contra vazamento
(caso, estudo, série, **conteúdo**).

**A lista de casos não existe e não será inventada.** A proporção entra na V2, junto com
os dados.

## Modelo

**nnU-Net v2, configuração `3d_fullres`.** `nnunetv2 2.8.1` já está instalado.

**Por quê:** é a arquitetura mais simples que a stack existente suporta sem código novo;
o planner deriva *patch size*, *spacing* e normalização **do dado**, o que remove um
canal inteiro de escolha humana — e portanto de vazamento por escolha; e torna o
baseline comparável ao TotalSegmentator sem replicar a opacidade dele, já que a
diferença passa a ser a procedência, não a arquitetura.

**O que não é:** não é proposta de arquitetura melhor. A Fase 19 não tem dado para
escolher arquitetura, e escolher por resultado de LCTSC seria usar TEST para desenho.

**Folds: os cinco, não apenas o `0`.** A Fase 16 mediu que os pesos públicos do
TotalSegmentator são `fold=0` e que o `splits_final.json` nunca foi publicado — logo nem
as imagens declaradas são atribuíveis ao treino efetivo. **Publicar o `splits_final.json`
e os cinco folds é exatamente o que fecha esse buraco do nosso lado.**

## Pré-processamento

O do nnU-Net, sem etapa nossa. Nenhuma reamostragem, recorte ou normalização
proprietária antes do planner.

**Pós-processamento: nenhum**, salvo o que `nnUNetv2_find_best_configuration` escolher
**a partir do VALIDATION** — nunca do TEST.

## Seeds

`20260906`, único e fixo, declarado antes de existir treino. Registrado em
`plano.SEED`, no relatório de ambiente e no `dataset.json`.

## Métricas

As oito congeladas, e só elas como critério: `dice`, `iou`, `precision`, `recall`,
`hd95`, `assd`, `erro_volume_absoluto`, `erro_volume_percentual`.

Métricas exploratórias podem ser medidas e publicadas — desde que declaradas
exploratórias e **fora do critério**.

## Critérios de sucesso

**NÃO é um limiar numérico de Dice.** Um limiar escolhido agora, sem dado, seria chute;
escolhido depois, seria ajuste ao resultado.

O critério da V1 é **procedimental**:

1. o treino reproduz o `sha256` do manifesto congelado;
2. o `splits_final.json` efetivo é publicado junto com os pesos;
3. todo caso do TRAIN tem procedência completa;
4. o TEST foi lido **uma única vez**, em contexto `avaliacao`;
5. a suíte de guardas passa antes e depois.

Um modelo que satisfaz os cinco é aceito **qualquer que seja o Dice**. Um modelo que
falha em qualquer um é rejeitado **qualquer que seja o Dice**.

## Critérios de regressão

- qualquer execução que não reproduza o `sha256` do manifesto congelado;
- qualquer leitura de TEST em contexto de treino (`AcessoIndevido`);
- qualquer alteração do manifesto congelado sem `VERSION INCREMENT`;
- qualquer divergência entre o alvo do baseline e a `ESOPHAGUS_ONTOLOGY_V1`;
- qualquer caso entrando sem `license_class`.

**Todos independentes do Dice.**

## Teste externo

**Estado: sem TEST externo elegível.**

O único candidato vivo é o **LyNoS** (Fase 18). Ele passa em ontologia (15/15) e em
licença **não passa** — três fontes oficiais em conflito. E sua independência permanece
**indeterminada**: a sonda geométrica não distingue inclusão de acaso abaixo de ~4 casos
em 15, e nenhuma sonda de imagem enxerga circularidade de anotação.

**Enquanto isso valer, o LyNoS é "candidato a TEST externo", nunca "TEST independente".**

**RECOMENDAÇÃO.** O TEST da V1 deve ser conjunto próprio, congelado antes do treino, com
procedência completa. Um TEST externo entra como **segunda** avaliação, declarada como
condicional — nunca como a avaliação principal.

## Regras anti-leakage

Sete injeções deliberadas, todas exigindo falha do sistema
(`tests/test_baseline_v1.py`, testes 08–14):

| # | Injeção | Guarda que dispara |
|---|---|---|
| 1 | trocar um `case_id` de split | `validar_vazamento` — quatro identidades |
| 2 | trocar um hash | `verificar_congelamento` → `conteudo alterado` |
| 3 | mover caso de validation para test | `verificar_congelamento` → `VERSION INCREMENT` |
| 4 | inserir máscara sem licença | `validar_licenca` — 4 classes bloqueantes |
| 5 | remover campo obrigatório | `validar_entrada` → `campos ausentes` |
| 6 | alterar a ontologia | snapshot carimba `ontologia` + teste 13 |
| 7 | liberar acesso ao TEST no loader | `AcessoIndevido`, e a trava é restaurada |

**Mutação:** cinco mutantes plantados nos próprios validadores, cinco derrubados.
Um validador que devolve "nenhum erro" precisa provar que consegue ver.

## Reprodutibilidade

Versões **realmente instaladas**, lidas do interpretador (nunca digitadas):

| Pacote | Versão |
|---|---|
| Python | 3.13.11 (Windows-11-10.0.26200-SP0) |
| `nnunetv2` | 2.8.1 |
| `torch` | 2.6.0+cu124 (CUDA 12.4) |
| `numpy` | 2.5.2 |
| `scipy` | 1.18.1 |
| `scikit-image` | 0.26.0 |
| `SimpleITK` | 2.5.6 |
| `pydicom` | 3.0.2 |
| `nibabel` | 5.4.2 |
| `TotalSegmentator` | 2.18.0 |
| `dcmrtstruct2nii` | 5 |
| `batchgenerators` | 0.25.3 |
| `acvl_utils` | 0.2.6 |
| `dynamic_network_architectures` | 0.4.4 |
| `MONAI` | **AUSENTE** |
| `trimesh` | 5.0.0 · `vtk` 9.7.0 · `scikit-learn` 1.9.0 |

GPU: NVIDIA GeForce RTX 4060 Ti, 16.380 MiB.

`MONAI` aparece como **AUSENTE** de propósito: o relatório reflete a máquina, não a
lista de dependências que seria elegante ter. O teste 07 falha se ele passar a ser
reportado como presente sem estar instalado.

Também registrados: `seed`, versão da ontologia, versão do esquema, e o commit.

## Comandos

| Passo | Comando | Lê | Nunca lê |
|---|---|---|---|
| planejar e pré-processar | `nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity` | train + validation | **test** |
| treinar os 5 folds | `nnUNetv2_train 501 3d_fullres FOLD --npz` (FOLD 0..4) | train + validation | **test** |
| escolher pós-processamento | `nnUNetv2_find_best_configuration 501 -c 3d_fullres` | validation | **test** |
| congelar o split efetivo | copiar `splits_final.json` para o snapshot | — | — |
| avaliar **uma vez**, no fim | `nnUNetv2_predict ...` (contexto `avaliacao`) | test | — |

## O que NÃO será alterado após o treino

- **o TEST não será usado para seleção** — nem de modelo, nem de época, nem de
  pós-processamento, nem de limiar;
- o manifesto congelado e seu `sha256`;
- o split, em qualquer partição;
- a `ESOPHAGUS_ONTOLOGY_V1` e as oito métricas;
- o `seed`;
- os critérios de sucesso e de regressão **deste documento**.

Alterar qualquer um destes exige **nova versão do pré-registro**, com data e motivo, e a
versão antiga permanece no histórico.

---

## Estado de prontidão

| Camada | Estado |
|---|---|
| **INFRAESTRUTURA** | **PRONTA** — esquema, hashes, congelamento, travas, 17 testes, 5 mutantes derrubados |
| **METODOLOGIA** | **PRONTA** — ontologia congelada, split desenhado, métricas fixas, critérios escritos antes |
| **DADOS** | **BLOQUEADO** — zero casos com procedência completa; nenhum TEST externo elegível |
| **TREINAMENTO** | **BLOQUEADO** — depende inteiramente da camada de dados |
