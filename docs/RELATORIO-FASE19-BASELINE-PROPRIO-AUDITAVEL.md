# Fase 19 — baseline próprio auditável

Data: 2026-09-06 · Nada treinado · Nada avaliado · Split congelado intocado

> **RESULTADO: B — parcialmente pronto.**
> **INFRAESTRUTURA e METODOLOGIA prontas. DADOS bloqueados. TREINAMENTO bloqueado.**
>
> "Pronto para pré-registro" **não** significa "pronto para treinar", e a Fase 19 termina
> exatamente nessa distinção.

---

## 1. Objetivo e a razão dele

A Fase 16 mediu por que o `BASELINE_ESOFAGO_V1` (TotalSegmentator 2.18.0) não pode ser
auditado. **Nenhum dos defeitos é de modelagem:**

| Defeito | Consequência |
|---|---|
| 420 de 1.559 imagens de treino não atribuídas | independência de nenhum dataset público pode ser presumida |
| não existe lista dos casos efetivamente usados | nem as 1.139 públicas são atribuíveis |
| pesos `fold=0`, sem `splits_final.json` publicado | o modelo viu ~80 % e ninguém sabe quais |
| SegTHOR e BTCV semearam a **primeira segmentação** do treino (suplemento S2) | **circularidade de anotação** no esôfago |

**Nenhum é detectável depois. Todos são evitáveis antes.** Esta fase constrói o "antes".

A Fase 18 acrescentou a medida que fecha o argumento: a sonda geométrica **não distingue
inclusão do acaso abaixo de ~4 casos em 15**. Instrumento nenhum substitui procedência
registrada.

## 2. INFRAESTRUTURA — **PRONTA**

### 2.1 O que já existia e foi reusado

**Não foi criada uma segunda implementação.** A ingestão de caso já existia em
[`dataset_esofago.py`](../scripts/validation/tier2/dataset_esofago.py), com três recusas
no mesmo funil: procedência (`gt_humano` sem valor padrão), grade (**sem reamostragem,
nunca**) e máscara vazia. A camada que faltava era outra: **identidade, licença, split e
congelamento.**

A validação de alvo do `plano.py` **importa** `medir_mascara` e `classificar_ontologia` de
`lynos/auditoria.py` — a mesma função que julgou o LyNoS na Fase 18. Duas cópias
divergiriam, e a divergência apareceria como diferença de desempenho.

### 2.2 O que foi construído

| Módulo | Função | Autoteste |
|---|---|---:|
| `baseline_v1/manifesto.py` | 22 campos, hashes, congelamento, trava de acesso | 24/24 |
| `baseline_v1/plano.py` | desenho do split, config nnU-Net, validação de alvo, ambiente | 14/14 |
| `baseline_v1/candidatos.py` | o esquema aplicado ao candidato real | 7/7 |
| `tests/test_baseline_v1.py` | guardas 19.12 + reprodutibilidade negativa 19.14 | 17/17 |

### 2.3 A trava que importa

O TEST é **inalcançável** a partir do contexto de treino — por **exceção**, não por
convenção de nome:

| Contexto | Pode ler |
|---|---|
| `treino` | `train` |
| `validacao` | `train`, `validation` |
| `avaliacao` | `test` |

Qualquer outra combinação levanta `AcessoIndevido`. A única forma de ler o TEST é escrever
`contexto="avaliacao"` — frase que ninguém digita por acidente dentro de um laço de treino.

### 2.4 Vazamento verificado por **quatro** identidades

`case_id`, `study_id`, `series_id` e **`sha256` do conteúdo** (imagem e máscara).

As três primeiras podem ser renomeadas por engano; **o hash não pode**. Verificar só o
`case_id` é o modo clássico de deixar a mesma série entrar duas vezes com nomes diferentes.

## 3. DADOS — **BLOQUEADO**

**Zero casos ingeridos.** O manifesto existe e está vazio, e isso é deliberado: preencher
split com caso inventado seria exatamente a fraude que 18 fases documentaram nos outros.

### 3.1 O esquema testado contra o candidato real

Um esquema só testado com dado sintético é um esquema **não testado**. As 15 fichas do
LyNoS foram montadas a partir do que a Fase 18 **mediu** — `shape`, `spacing` e
`orientation` do JSON de medição; `mask_sha256` calculado do arquivo em disco.

**Resultado: RECUSADO**, e o motivo mudou durante a própria fase:

| Momento | Motivo da recusa |
|---|---|
| antes da apuração de licença | `license_class = CONFLITO` |
| **depois** (Fase 18 resolveu: CC BY 4.0) | **`image_sha256` é `UNKNOWN`** — a TC não foi baixada |

**Contrafactual medido:** se as 15 TCs fossem baixadas (2,70 GiB) e os hashes existissem,
a validação **passaria**. Mas **dois campos continuariam `UNKNOWN` e nenhum download os
resolve**:

> `study_id` e `series_id` **não existem no canal NIfTI**. Isso não é descuido do projeto
> — é propriedade da fonte. **Duas das quatro identidades anti-vazamento ficam cegas** para
> qualquer dataset distribuído fora do DICOM.

Esse é um achado de desenho, não um detalhe: o esquema tem quatro chaves porque três são
falíveis, e um canal NIfTI entrega apenas duas delas.

### 3.2 Nenhum TEST externo elegível

O LyNoS é **candidato a TEST externo secundário, condicional** (Fase 18, decisão B).
Enquanto a independência do baseline for indeterminada, ele **não** é "TEST independente".

## 4. METODOLOGIA — **PRONTA**

- **Alvo:** `ESOPHAGUS_ONTOLOGY_V1`, sem segunda definição. O `dataset.json` carimba a
  versão; o teste 13 falha se o alvo do baseline divergir dela.
- **Split:** nove regras escritas, todas verificadas por código. **A proporção não foi
  fixada** — fixá-la antes de saber quantos casos existem seria número inventado.
- **Métricas:** as oito congeladas, e só elas como critério.
- **Seed:** `20260906`, único, declarado antes de existir treino.
- **Critério de sucesso:** **procedimental, não numérico.** Um limiar de Dice escolhido
  agora seria chute; escolhido depois, seria ajuste ao resultado. O modelo é aceito se
  reproduzir o `sha256` do manifesto, publicar o `splits_final.json`, ter procedência
  completa no TRAIN, ler o TEST **uma única vez**, e passar nas guardas — **qualquer que
  seja o Dice**.

Restrição de desenho já medida (Fase 18.5): **n=15 dá IC95 de 0,077 de Dice e poder 0,485
para separar Δ=0,05.** Qualquer TEST desse tamanho herda isso.

## 5. Reprodutibilidade negativa (19.14) — sete injeções

Cada uma exige que o sistema **falhe**, e depois restaura o estado:

| # | Injeção | Guarda | Resultado |
|---|---|---|---|
| 1 | trocar `case_id` de split | `validar_vazamento` | falha ✔ |
| 2 | trocar um hash | `verificar_congelamento` → `conteudo alterado` | falha ✔ |
| 3 | mover caso de validation para test | → `VERSION INCREMENT` | falha ✔ |
| 4 | máscara sem licença (4 classes) | `validar_licenca` | falha ✔ |
| 5 | remover campo obrigatório (5 campos) | `validar_entrada` | falha ✔ |
| 6 | alterar a ontologia | snapshot carimba `ontologia` | falha ✔ |
| 7 | **liberar acesso ao TEST no loader** | `AcessoIndevido` | falha ✔, **e a trava volta** |

O teste 14 é o mais agressivo: ele **abre de fato** o TEST para o contexto de treino,
confirma que a mutação teve efeito, restaura, e então **exige que a trava volte a valer**.
Um teste que só verifica o estado bom não prova nada sobre o estado ruim.

### 5.1 Mutação nos próprios validadores

Um validador que devolve "nenhum erro" pode estar zerado por estar **quebrado**. Cinco
mutantes plantados, **cinco derrubados**:

| Mutante | Falhas provocadas |
|---|---:|
| `validar_vazamento` sempre vazio | 4 |
| `validar_licenca` sempre vazio | 4 |
| `carregar_particao` sem guarda | 3 |
| `verificar_congelamento` sempre intacto | 3 |
| campos ausentes ignorados | 1 |

## 6. Auditoria final (19.15) — **PASS = 157 · FAIL = 0 · SKIP = 0**

Três categorias, contadas separadamente porque medem coisas diferentes:
**48** testes de suíte · **81** verificações de autoteste de módulo ·
**28** guardas derrubadas por mutação.

| Suíte | Resultado |
|---|---|
| `tests/test_geometria.py` | **10/10** |
| `tests/test_controles_positivos.py` | **8/8** |
| `tests/test_ontologia_esofago.py` | **13/13** |
| `tests/test_baseline_v1.py` | **17/17** |
| `interobservador --mutacao` | **21/21 regras derrubam o autoteste** |
| `estilo_esofago --mutacao` | **7/7 guardas derrubam o autoteste** |
| varredura de docs | **40 documentos, 0 violações** |

Autotestes de módulo: `lynos.auditoria` 10 · `lynos.calibracao` 8 · `lynos.grade_ct` 5 ·
`lynos.adequacao` 6 · `lynos.integridade` 7 · `baseline_v1.manifesto` 24 ·
`baseline_v1.plano` 14 · `baseline_v1.candidatos` 7 — **81 verificações, 0 falhas**.

Suítes: 10 + 8 + 13 + 17 = **48**. Mutação: 21 + 7 = **28**. Total **157**.

**Nenhum SKIP silencioso.** O único `SKIP` possível é o de `candidatos.py` quando o JSON de
medição da Fase 18 não existe, e ele **imprime** a razão.

### 6.1 Split congelado

`sha256` `6e54c02b58bbb9b3a1667d4672eddef6…` · mtime `2026-09-04T21:19:49` · **INTOCADO**
`development` 30 · `validation` 15 · `test` 15

## 7. Defeitos que os próprios instrumentos encontraram

Três, todos meus, todos pegos por controle e não por revisão:

1. **Guarda olhando o campo errado.** O teste que proíbe ler TEST fora de `avaliacao`
   procurava a declaração em `nota`; ela mora em `cmd`. A intenção estava certa, o campo
   não.
2. **Um achado confundido com defeito.** O contrafactual "e se a licença fosse resolvida?"
   revelou que o LyNoS **continua** barrado por falta de `image_sha256`. Eu tinha escrito o
   teste para tratar isso como erro; era **informação**. Agora o teste **exige** que o
   bloqueio residual continue aparecendo — se sumir, foi porque alguém afrouxou a regra de
   identidade.
3. **DOI fabricado.** A primeira versão da ficha registrou `10.5281/zenodo.10102261`. Esse
   DOI **não existe**: o registro Zenodo usa o DOI do artigo, `provider: external`,
   `conceptdoi: null`.

## 8. O que a Fase 19 **não** resolve

- **Não resolve independência.** Procedência registrada torna a pergunta *respondível*, não
  a resposta *favorável*.
- **Não resolve circularidade de anotação.** Se a máscara de origem foi semeada por modelo,
  `annotation_source` registra — e nenhuma sonda de imagem detecta.
- **Não cria casos.** O esquema está pronto; os dados não existem.
- **Não cobre o eixo ético/legal.** CC BY 4.0 não é aprovação para uso secundário, nem
  consentimento, nem base legal sob GDPR. O esquema não tem campo para isso — **lacuna
  declarada da V1**.

## 9. Resultado

# **B — parcialmente pronto**

Não é **A** porque A seria "pronto para pré-registro" sem ressalva, e há duas: nenhum caso
existe, e o esquema tem uma cegueira estrutural conhecida (`study_id`/`series_id` em canal
NIfTI).

Não é **C** porque C seria "bloqueado por dados" e só isso — o que apagaria o fato de que
infraestrutura e metodologia estão **prontas e testadas**, com 17 guardas, 7 injeções e 5
mutantes derrubados.

| Camada | Estado |
|---|---|
| **INFRAESTRUTURA** | **PRONTA** |
| **METODOLOGIA** | **PRONTA** |
| **DADOS** | **BLOQUEADO** — zero casos com procedência completa |
| **TREINAMENTO** | **BLOQUEADO** — depende inteiramente da camada de dados |

---

```
FASE 19 CONCLUIDA
RESULTADO: B — parcialmente pronto
DATASET_PROPRIO: ESQUEMA PRONTO, VAZIO — 22 campos, 0 casos
PROVENIENCIA: MANIFESTO JSONL CANONICO COM SHA-256 — machine-readable, hash estavel e independente de ordem
SPLIT: DESENHO PRONTO (9 regras, 4 identidades) — lista NAO existe e nao sera inventada
ANTI_LEAKAGE: PASS — 7 injecoes exigem falha, 5 mutantes derrubados
REPRODUTIBILIDADE: PRONTA — seed 20260906, versoes lidas do interpretador, MONAI declarado AUSENTE
TESTES: PASS=157 FAIL=0 SKIP=0  (48 de suite + 81 de autoteste + 28 de mutacao)
TREINAMENTO: BLOQUEADO POR DADO
```
