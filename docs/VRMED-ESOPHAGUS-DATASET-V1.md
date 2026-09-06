# VRMED-ESOPHAGUS-DATASET-V1 — especificação do dataset próprio

Congelado em **2026-09-06** · Fase 19 · Estado: **ESQUEMA — nenhum caso ingerido**

> Esta é a versão humana da mesma especificação que
> [`scripts/validation/baseline_v1/manifesto.py`](../scripts/validation/baseline_v1/manifesto.py)
> guarda em forma legível por máquina. `tests/test_baseline_v1.py` falha se as duas
> divergirem. **Nenhum caso existe ainda** — e nenhum será inventado para preencher o
> esquema.

---

## 1. Por que este documento existe

A Fase 16 mediu por que o `BASELINE_ESOFAGO_V1` (TotalSegmentator 2.18.0) não pode ser
auditado. A lista de defeitos não tem **nada** de modelagem:

| Defeito medido | Consequência |
|---|---|
| 420 de 1.559 imagens de treino não são atribuídas a instituição nomeada | a independência de nenhum dataset público pode ser presumida |
| não existe lista dos casos efetivamente usados | nem as 1.139 imagens públicas são atribuíveis |
| os pesos publicados são `fold=0` e o `splits_final.json` nunca saiu | o modelo viu ~80 % das imagens e ninguém sabe quais |
| SegTHOR e BTCV foram usados como modelos pré-treinados para gerar a **primeira segmentação** do conjunto de treino (suplemento S2) | **circularidade de anotação** para o esôfago — invisível a qualquer sonda de imagem |

**Nenhum desses defeitos é detectável depois. Todos são evitáveis antes.** Este esquema
é o "antes".

**FATO.** A Fase 18 acrescentou uma medida ao mesmo argumento: a sonda geométrica
aplicada ao LyNoS não distingue inclusão de acaso abaixo de ~4 casos em 15
(§[Fase 18](RELATORIO-FASE18-AUDITORIA-LYNOS.md)). Instrumento nenhum substitui
procedência registrada.

## 2. O que o esquema exige

**22 campos obrigatórios por caso.** Um campo ausente é **erro**; um campo que o
projeto não sabe é `UNKNOWN` **explícito**. Os dois não são a mesma coisa — o primeiro
é descuido, o segundo é conhecimento sobre o próprio limite.

| Grupo | Campos |
|---|---|
| **Identidade** | `case_id`, `study_id`, `series_id` |
| **Conteúdo** | `image_path`, `mask_path`, `image_sha256`, `mask_sha256` |
| **Grade** | `spacing`, `orientation`, `shape` |
| **Origem clínica** | `institution`, `acquisition` |
| **Anotação** | `annotation_source`, `annotation_protocol`, `annotation_date_known` |
| **Procedência** | `source_dataset`, `source_case_id`, `source_doi` |
| **Direito** | `license`, `license_class` |
| **Uso** | `split`, `notes` |

**RECUSA.** `case_id`, `image_sha256` e `mask_sha256` **não podem** ser `UNKNOWN`: são
identidade, não metadado. Um caso sem hash não é um caso — é uma promessa.

**Formato.** JSONL, uma entrada por linha, ordenada por `case_id`, chaves ordenadas.
A serialização é canônica de propósito: sem isso, dois manifestos com o mesmo conteúdo
teriam hashes diferentes só por ordem de inserção, e o congelamento viraria ruído em vez
de trava.

## 3. Licença — a classificação é obrigatória

**Nenhum caso entra em dataset publicável sem `license_class`.**

| Classe | Significado | Bloqueia? |
|---|---|---|
| `ABERTA_ATRIBUICAO` | CC BY, MIT, BSD, Apache | não |
| `ABERTA_NAO_COMERCIAL` | CC BY-NC e variantes | não |
| `ABERTA_SEM_DERIVADAS` | CC BY-ND, CC BY-NC-ND | **sim** |
| `RESTRITA` | exige acordo, cadastro ou aprovação | **sim** |
| `CONFLITO` | fontes oficiais do mesmo dado declaram licenças diferentes | **sim** |
| `UNKNOWN` | nenhuma licença localizada em fonte primária | **sim** |

**`UNKNOWN` e `CONFLITO` não são a mesma coisa.** Desconhecida é ausência de
informação; conflitante é presença de informação contraditória — um estado **pior**,
porque parece resolvido. O LyNoS é exatamente o segundo caso (Fase 18 §3).

**Sem derivadas bloqueia** porque uma máscara reamostrada, recortada ou reprojetada
**já é** obra derivada. O bloqueio não é conservadorismo: é a leitura literal do termo.

## 4. Split — o desenho, não a lista

**Nove regras**, todas verificadas por código:

1. um mesmo **caso** nunca aparece em duas partições (`case_id`);
2. um mesmo **estudo** nunca aparece em duas partições (`study_id`);
3. uma mesma **série** nunca aparece em duas partições (`series_id`);
4. um mesmo **conteúdo** nunca aparece em duas partições (`sha256` de imagem e de
   máscara) — as três chaves acima podem ser renomeadas por engano; **o hash não pode**;
5. a fonte de cada caso é rastreável até `source_dataset` + `source_case_id` + `source_doi`;
6. a instituição é rastreável quando disponível; quando não, `UNKNOWN` explícito;
7. caso com procedência `UNKNOWN` **não entra em TEST** sem justificativa gravada em
   `notes` — e a justificativa é exigida não-vazia, para que a exceção não vire silêncio;
8. o TEST é congelado **antes** do treino, e qualquer alteração exige **VERSION INCREMENT**;
9. o TEST nunca participa de seleção de modelo, de hiperparâmetro nem de época.

**A proporção train/validation/test NÃO está fixada aqui.** Fixar proporção antes de
saber quantos casos existem seria número inventado. Ela entra na V2 do desenho, junto
com a primeira lista real.

**Restrição já conhecida, medida:** o TEST precisa de `n` suficiente para um IC útil.
Com a dispersão do próprio projeto (Dice do esôfago, `development`, n=30), **n=15 dá
IC95 de largura 0,077 de Dice e poder 0,485 para separar uma diferença de 0,05**.
Qualquer TEST de n=15 herda isso.

## 5. A trava de acesso

O TEST é **inalcançável** a partir do contexto de treino — por exceção, não por
convenção de nome:

| Contexto | Pode ler |
|---|---|
| `treino` | `train` |
| `validacao` | `train`, `validation` |
| `avaliacao` | `test` |

Qualquer outra combinação levanta `AcessoIndevido`. A única forma de ler o TEST é
declarar contexto `avaliacao` — uma frase que ninguém escreve por acidente dentro de um
laço de treino.

## 6. Congelamento e imutabilidade

`congelar()` grava um snapshot com: versão do esquema, versão e data do congelamento,
**versão da ontologia**, contagem por partição, `sha256` do manifesto canônico e
`sha256` por caso (imagem e máscara).

Depois disso, `verificar_congelamento()` responde **INTACTO** ou lista exatamente o que
mudou — caso acrescentado, caso removido, conteúdo alterado, ou metadado alterado — e
exige `VERSION INCREMENT`. **Nunca edição silenciosa da V1.**

`congelar()` **recusa** manifesto inválido. Não se congela defeito.

## 7. Alvo

O alvo é a [`ESOPHAGUS_ONTOLOGY_V1`](ESOPHAGUS-ONTOLOGY-V1.md), sem segunda definição:
máscara binária **preenchida**, parede e lúmen como alvo único, extensão longitudinal
herdada do GT e não avaliável anatomicamente, oito métricas congeladas.

A validação de alvo do `plano.py` **importa** a função que julgou o LyNoS na Fase 18 em
vez de reimplementá-la. Duas cópias divergiriam, e a divergência apareceria como
diferença de desempenho.

Verificações por caso: valores únicos, binariedade, máscara vazia, buracos internos
(critério do preenchido), componentes conexos, calibre, `dtype` inteiro, e volume dentro
de uma faixa de detecção de outlier grosseiro (5–150 mL, origem declarada: a própria
coorte medida na Fase 18, mais folga — **não é critério anatômico**).

## 8. O que este esquema NÃO resolve

- **Não resolve independência.** Procedência registrada torna a pergunta *respondível*;
  não torna a resposta *favorável*. Um caso pode ter procedência completa e ainda assim
  estar no treino de outro modelo.
- **Não resolve circularidade de anotação.** Se a máscara de origem foi semeada por um
  modelo, `annotation_source` registra isso — e é por isso que o campo existe e que
  `gt_humano` já era recusa em [`dataset_esofago.py`](../scripts/validation/tier2/dataset_esofago.py).
- **Não cria casos.** O esquema está pronto; os dados não existem.

## 9. Regra de mudança

Qualquer alteração deste esquema é uma **nova versão** (V2), com data e motivo, nunca
edição silenciosa da V1. `tests/test_baseline_v1.py` existe para tornar a edição
silenciosa impossível.
