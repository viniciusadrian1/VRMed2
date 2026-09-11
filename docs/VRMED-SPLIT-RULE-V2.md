# VRMED-SPLIT-RULE-V2

**Declarada em 2026-09-10, Fase 31 — antes de qualquer número ser visto.**
Aplica-se ao pool `VRMED-ESOPHAGUS-POOL46-V2`. A
[V1](RELATORIO-FASE25-CONGELAMENTO.md) permanece válida e inalterada para o pool de 16.

---

## A regra

```python
bucket(case_id) = int(sha256(case_id), 16) % 100          # idêntico à V1
split           = "validation" se bucket < 25, senão "train"
                  # aplicado DENTRO DE CADA ESTRATO
estrato         = source_dataset
test            = VAZIO, sempre
seed            = não há — não há sorteio
```

**Bandas de aceitação, declaradas antes de calcular:**

| estrato | n | banda para `validation` |
|---|---|---|
| `4D-Lung (TCIA)` | 16 | **[2, 8]** |
| `LCTSC (TCIA)` | 30 | **[4, 12]** |
| global | 46 | **[6, 20]** |

Resultado fora da banda **bloqueia o congelamento**. Não se re-sorteia, não se ajusta o
limiar, não se troca a regra — qualquer uma dessas coisas seria escolher o split depois
de ver o split.

---

## O que muda em relação à V1, e por quê

**A V1 aplicava o limiar ao pool inteiro.** Com uma fonte só, isso bastava.

**A V2 estratifica por `source_dataset`.** Com duas fontes de tamanhos diferentes — 16 e
30 — o sorteio poderia concentrar a validation numa delas. Uma validation composta só de
LCTSC mediria outra coisa que uma composta só de 4D-Lung: são instituições, protocolos de
contorno e tipos de anotação diferentes. A estratificação **garante que as duas fontes
apareçam nos dois lados**.

## O que deliberadamente NÃO muda

**O mecanismo do bucket é o mesmo da V1.** Isso preserva a propriedade que a Fase 25
declarou e provou por autoteste: **um caso novo não move nenhum caso já atribuído.**

Consequência: os 16 casos do 4D-Lung caem exatamente onde já estavam (10 train, 6
validation). **Isso não é conveniência — é a propriedade declarada.** Reatribuir um caso
já congelado seria vazamento com cara de manutenção: um caso que o modelo da Fase 26B
treinou passaria a ser validation, e qualquer comparação que envolvesse aquele modelo
ficaria contaminada.

## As quatro propriedades, herdadas e reprovadas por autoteste

| # | Propriedade | Como é provada |
|---|---|---|
| 1 | **determinística sem semente** | não há sorteio; `sha256` de uma string é o mesmo em qualquer máquina |
| 2 | **estável sob crescimento** | autoteste acrescenta um caso e exige que nenhum existente mude |
| 3 | **independente de ordem** | autoteste embaralha a entrada e exige a mesma atribuição |
| 4 | **cega ao conteúdo** | autoteste injeta `volume_ml=999`, `spacing=[9,9,9]`, `extensao=1` e exige que nada mude |

O autoteste 1 verifica ainda que `bucket()` da V2 devolve **exatamente** o mesmo valor
que o `bucket()` da V1 — se as duas divergirem, a propriedade 2 deixa de valer e o teste
cai.

## Resultado da aplicação

| estrato | n | train | validation | banda | |
|---|---|---|---|---|---|
| 4D-Lung | 16 | 10 | **6** | [2, 8] | DENTRO |
| LCTSC | 30 | 22 | **8** | [4, 12] | DENTRO |
| **TOTAL** | **46** | **32** | **14** | [6, 20] | **DENTRO** |
| test | | | **0** | | protegido |

`validation` global = 14 de 46 = **30,4 %** contra alvo de 25 %. Dentro da banda
declarada, **e não ajustado** — mesmo princípio da V1, onde 6 de 16 deram 37,5 %.

## Agrupamento por sujeito

Ambas as fontes têm **uma série por sujeito**, então "preservar casos por estudo/coorte"
é satisfeito trivialmente. Ainda assim a verificação existe e é executada: a auditoria
agrupa por `(source_dataset, source_case_id)` e falha se algum sujeito aparecer nos dois
lados. **46 sujeitos, nenhum em dois splits.**

## TEST

**`test` = 0, e a regra nunca atribui `test`.** A proteção continua sendo
`AcessoIndevido` levantada de verdade: contexto `treino` não alcança `test` **nem**
`validation`; contexto `avaliacao` alcança `test`. Controle negativo: `treino` lê os 32
de `train`.
