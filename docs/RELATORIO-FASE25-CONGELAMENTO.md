# Fase 25 — congelamento de TRAIN/VALIDATION, com TEST vazio e protegido

**Data:** 2026-09-06 · **Versão congelada:** `VRMED-ESOPHAGUS-POOL16-V1`
**Esquema:** `VRMED-ESOPHAGUS-DATASET-V1` · **Ontologia:** `ESOPHAGUS_ONTOLOGY_V1` (congelada
2026-09-06, **não tocada**)
**Composição:** **TRAIN 10 · VALIDATION 6 · TEST 0**

**O que esta fase NÃO fez:** não treinou, não mediu Dice, não rodou benchmark, não usou desempenho
de modelo em decisão nenhuma, não preencheu TEST, não reutilizou LCTSC, LyNoS, NSCLC-Radiomics ou
SegTHOR como TEST, e não recalculou métrica histórica.

---

## 1. A regra do split foi escrita antes de qualquer número ser visto

Esta é a única garantia que importa num split de n=16: **a regra não pode ter sido escolhida depois
de olhar o resultado.** Ela está em [`fase25/split.py`](../scripts/validation/fase25/split.py), foi
commitada antes da execução, e diz:

```python
REGRA_VERSAO      = "VRMED-SPLIT-RULE-V1"
LIMIAR_VALIDATION = 25          # por cento
BANDA_ACEITACAO   = (2, 8)      # min, max de casos em validation, para n=16
SEED              = None        # nao ha sorteio: nao ha semente

def bucket(case_id):  return int(hashlib.sha256(case_id.encode()).hexdigest(), 16) % 100
def atribuir(case_id): return "validation" if bucket(case_id) < LIMIAR_VALIDATION else "train"
```

**Quatro propriedades, cada uma provada por autoteste, não afirmada:**

| # | Propriedade | Por que ela existe |
|---|---|---|
| 1 | **determinística sem semente** | não há sorteio, então não há semente para perder, anotar errado ou divergir entre máquinas |
| 2 | **estável sob crescimento do pool** | um caso novo **não move** nenhum caso já atribuído — reatribuir caso congelado é vazamento com cara de manutenção |
| 3 | **independente de ordem** | é exatamente a falha que a Fase 24 achou na regra de seleção de série, e ela não se repete aqui |
| 4 | **cega ao conteúdo** | a chave é o **identificador** — nunca volume, extensão, spacing, qualidade da máscara ou desempenho de modelo |

O autoteste da propriedade 4 injeta `volume_ml=999`, `extensao_axial_mm=1` e `spacing=[9,9,9]` nas
entradas e **exige que a atribuição não mude**. Um split que reage ao alvo escolhe o resultado.

---

## 2. O resultado, e o que ele tem de desconfortável

```
TOTAL 16  |  TRAIN 10  |  VALIDATION 6  |  TEST 0
banda de aceitação declarada antes: [2, 8] -> DENTRO
```

**FATO, e ele precisa ficar escrito.** O alvo declarado era **25 %**; saíram **6 de 16 = 37,5 %**.
A diferença é real e não foi ajustada.

**Por que não se mexeu.** Com n=16 e limiar de 25 %, o número de casos em validation é uma binomial,
não uma cota — 6 está dentro do que a variação produz, e **a banda `[2, 8]` foi declarada
justamente para decidir isso antes de ver o número**. Baixar o limiar de 25 para, digamos, 19 até
sair "4 de 16" seria **escolher o split depois de ver o split**, que é a única coisa que a regra
existe para impedir. O desvio fica registrado como característica do congelamento, não corrigido.

---

## 3. Integridade de identidade

| Chave | Distintos | Repetidos |
|---|---|---|
| `case_id` | 16 | — |
| `study_id` | 16 | — |
| `series_id` | 16 | — |
| `image_sha256` | 16 | — |
| `mask_sha256` | 16 | — |

**Sujeitos: 16. Sujeito presente em dois splits: nenhum.**

Esta última verificação é separada de propósito. `validar_vazamento` compara `case_id` inteiro;
se um dia dois casos do **mesmo sujeito** entrarem no pool (por exemplo, duas fases respiratórias
do sujeito 107), o `case_id` seria diferente e o vazamento **passaria batido**. A checagem por
`source_case_id` existe para pegar exatamente isso, e ela tem **controle positivo**: o autoteste
injeta dois casos do mesmo sujeito em splits opostos e **exige que sejam acusados**. Um detector
que nunca acusa não detecta.

---

## 4. Procedência e licença dos 16

| Campo | Valor | n |
|---|---|---|
| `source_dataset` | `4D-Lung (TCIA)` | 16 |
| `source_doi` | `10.7937/K9/TCIA.2016.ELN8YGLE` | 16 |
| `license` | `CC BY 3.0` (declarada **por série** no índice do IDC) | 16 |
| `license_class` | `ABERTA_ATRIBUICAO` | 16 |
| `institution` | **`UNKNOWN`** | 16 |
| `annotation_protocol` | **`UNKNOWN`** | 16 |
| `annotation_date_known` | **`False`** | 16 |

**Licenças bloqueantes: nenhuma.** `CONFLITO`, `UNKNOWN`, `ABERTA_SEM_DERIVADAS` e `RESTRITA`
reprovariam a publicação, e nenhuma aparece.

Os três `UNKNOWN` **não são desleixo, e agora têm causa documentada** (ver o adendo da Fase 24):
`InstitutionName` foi **removida na origem**; o protocolo de contorno não é declarado pela fonte;
e as datas existem mas estão **deslocadas** (`Retain Longitudinal With Modified Dates Option`),
então há data no arquivo e a data verdadeira não é conhecida. **UNKNOWN continua UNKNOWN.**

---

## 5. Distribuição do pool — diagnóstico, e só

Esta seção existe para **expor anomalia**, nunca para consertar o split. O código diz isso em
`distribuicao()`, e o JSON carrega o aviso junto do dado.

| Dimensão | TRAIN (n=10) | VALIDATION (n=6) |
|---|---|---|
| volume (mL) | 23,59 · **med 37,53** · 60,69 | 26,00 · **med 31,80** · 44,42 |
| extensão axial (mm) | 198,0 · **med 244,5** · 264,0 | 174,0 · **med 246,0** · 267,0 |
| fase respiratória | `c00`×8, `c80`×1, `c10`×1 | `c00`×4, `c80`×1, `c40`×1 |
| spacing xy | 0,9766×8 · 1,1113×1 · 1,1621×1 | 0,9766×5 · 1,0527×1 |

**Duas observações, ambas registradas e nenhuma corrigida:**

1. **VALIDATION contém as duas pontas da extensão do pool** — o caso mais curto (174,0 mm) e o mais
   longo (267,0 mm). Com n=6, isso torna a mediana de validation pouco informativa sobre o meio da
   distribuição.
2. **TRAIN concentra a variação de spacing** — os três valores fora de 0,9766 estão 2 em train e
   1 em validation.

**INFERÊNCIA.** Nenhuma das duas indica um split defeituoso; são o que uma regra cega ao conteúdo
produz com n=16. **RECOMENDAÇÃO.** Registrar e reavaliar se o pool crescer — e reavaliar significa
**nova versão do congelamento**, nunca edição da V1.

---

## 6. TEST: vazio, e inalcançável por execução

**`n_test_no_manifesto = 0`.**

Vazio não basta — um TEST vazio protegido só por convenção de nome deixa de estar protegido no dia
em que alguém o preenche. A proteção é `AcessoIndevido`, levantada de verdade:

| Contexto | Lê `test`? | Esperado |
|---|---|---|
| `treino` | **BLOQUEADO** | bloqueado |
| `validacao` | **BLOQUEADO** | bloqueado |
| `avaliacao` | ABERTO | aberto |

**Controle negativo, e ele é obrigatório:** `treino` **consegue** ler `train`, e leu **10** casos.
Sem isso, um guarda que proibisse tudo passaria nos três testes acima sem provar nada.

---

## 7. O congelamento

| | |
|---|---|
| versão | `VRMED-ESOPHAGUS-POOL16-V1` |
| carimbo | `2026-09-06T00:00:00Z` — **entra por parâmetro**, porque um congelamento que se carimba com o relógio da máquina não é reproduzível |
| semente | **não há** — a regra não sorteia |
| critério | `sha256(case_id) mod 100 < 25` → validation |
| esquema | `VRMED-ESOPHAGUS-DATASET-V1`, 22 campos, 16/16 válidas, **0 erros** |
| ontologia | `ESOPHAGUS_ONTOLOGY_V1`, registrada no snapshot |
| **`sha256_manifesto`** | **`9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192`** |

### 7.1 Dois hashes que não podem ser confundidos

**FATO.** O arquivo `VRMED-ESOFAGO-MANIFESTO-V1.jsonl` foi gravado em Windows e saiu com **CRLF nas
16 linhas**. Logo:

| O que | sha256 | Reprodutível fora do Windows? |
|---|---|---|
| **conteúdo canônico** (o do snapshot, o da trava) | `9388c736…82632192` | **sim** |
| bytes do arquivo em disco | `5e05e899…6cb549d7` | **não** — muda com o fim de linha |

**A identidade do congelamento é a primeira.** `verificar_congelamento` recarrega o manifesto,
reconstrói a serialização canônica (ordenada por `case_id`, chaves ordenadas) e compara **conteúdo**,
então um checkout no Mac continua batendo. **RECOMENDAÇÃO:** nunca citar o hash de bytes como
identidade do congelamento — este projeto trabalha em duas máquinas e o hash de bytes divergiria
sem que nada tivesse mudado.

---

## 8. A instrumentação foi obrigada a provar que enxerga

**13 mutantes plantados numa CÓPIA da árvore — o repositório não é tocado.**

```
controle negativo (árvore intacta): funil=OK, manifesto=OK, suite=OK
MUTANTES MORTOS: 13/13
controle negativo depois:           funil=OK, manifesto=OK, suite=OK
```

| grupo | mutação | resultado |
|---|---|---|
| validators | `validar_vazamento` devolve lista vazia | MORREU |
| validators | `validar_licenca` devolve lista vazia | MORREU |
| validators | campos obrigatórios ausentes deixam de ser detectados | MORREU |
| validators | `sha256` malformado passa | MORREU |
| validators | `validar_alvo` aprova qualquer coisa (ontologia desligada) | MORREU |
| loader | `carregar_particao` sem a checagem de permissão | MORREU |
| loader | **treino passa a poder ler `test`** | MORREU |
| loader | **validação passa a poder ler `test`** | MORREU |
| loader | contexto desconhecido deixa de ser recusado | MORREU |
| loader | `carregar_particao` devolve TUDO, ignorando o split | MORREU |
| hashing | `verificar_congelamento` sempre diz INTACTO | MORREU |
| hashing | a serialização canônica deixa de ordenar por `case_id` | MORREU |
| hashing | `congelar` aceita manifesto inválido | MORREU |

Os dois mutantes em **negrito** são a prova direta de que a proteção do TEST não é decorativa: ao
afrouxar a permissão, a suíte cai.

**Incidente de processo, corrigido na raiz (regra 6).** A primeira execução gravou em
`docs/overnight/phase21/mutacao.json` — artefato **histórico**. O conteúdo era idêntico ao
congelado, exceto pelo nome do diretório temporário dentro de um *stack trace* capturado. O arquivo
da Fase 21 foi **restaurado** e `mutacao.py` ganhou `--saida`, com o **padrão inalterado**, para que
uma re-execução futura não repita o problema. Já era a segunda vez que uma fase nova sobrescrevia
artefato de fase antiga; a correção é no parâmetro, não na cópia manual.

---

## 9. Testes

**Arquivos de teste — 60/60:**

| Arquivo | Resultado |
|---|---|
| `tests/test_geometria.py` | 10/10 |
| `tests/test_controles_positivos.py` | 8/8 |
| `tests/test_ontologia_esofago.py` | 13/13 |
| `tests/test_baseline_v1.py` | 18/18 |
| **`tests/test_fase25_congelamento.py`** | **11/11** — novo |

`test_fase25_congelamento.py` não testa o código da Fase 25: testa o **artefato congelado**. Ele lê
o manifesto e o snapshot commitados e cai se alguém trocar um split, editar um caso, encostar no
TEST ou mexer no manifesto sem subir a versão. Inclui o controle negativo do guarda e uma
verificação de que **o `split` gravado é o que a regra produz** — ou seja, ninguém editou o campo à
mão depois do congelamento.

**Autotestes de módulo — 168/168, 0 falhas:** `manifesto` 29 · `plano` 14 · `candidatos` 7 ·
`funil` 16 · `mutacao` 31 · `anonimizacao` 11 · `aquisicao` 14 · `ingerir_real` 8 · `pool` 5 ·
`consolidar` 8 · `split` 13 · **`congelar` 12**.

**Nota de ambiente:** `pytest` não está instalado no `.venv-pipeline`; os cinco arquivos de teste
rodam como programas autônomos e foi assim que foram executados. Nenhum teste foi pulado.

---

## 10. Riscos e limitações do congelamento

| # | Item | Estado |
|---|---|---|
| 1 | **n = 16** | pool pequeno; qualquer estimativa terá intervalo largo |
| 2 | **VALIDATION = 6 (37,5 %)** contra alvo de 25 % | dentro da banda declarada; **não ajustado**, por princípio |
| 3 | **TEST = 0** | não há conjunto de avaliação independente. **Nada pode ser reportado como desempenho final** enquanto isso valer |
| 4 | anotação `SEMIAUTOMATIC` em 16/16 | **não é GT humano puro** |
| 5 | independência de **LyNoS** | **INCONCLUSIVA por construção** — NIfTI sem UIDs; nunca "sem overlap" |
| 6 | `institution`, `annotation_protocol` | **UNKNOWN**, com causa documentada |
| 7 | desidentificação | **declarada em fonte primária**; conformidade **não verificada** por este projeto |
| 8 | extensão longitudinal | **herdada do GT**, não avaliável anatomicamente |
| 9 | hash de bytes do manifesto | **dependente de plataforma** — usar o hash de conteúdo |
| 10 | fase respiratória heterogênea | registrada; `c00`×12, `c80`×2, `c10`×1, `c40`×1 |

**Sobre o item 3, explicitamente:** TEST vazio é uma **escolha declarada** desta fase, não um
esquecimento. Encher o TEST com casos deste mesmo pool tornaria a avaliação dependente da mesma
fonte, do mesmo TPS e do mesmo processo de contorno; encher com LCTSC, LyNoS, NSCLC-Radiomics ou
SegTHOR está **proibido pela regra desta execução**. Enquanto o TEST estiver vazio, **não existe
número de desempenho publicável** — e é assim que deve ser.

---

## 11. Arquivos e hashes

| Arquivo | sha256 (bytes) |
|---|---|
| `docs/VRMED-ESOFAGO-MANIFESTO-V1.jsonl` | `5e05e8997033a35cc1b8fe346895daf3d677ac3ff40949872f392e1c6cb549d7` |
| `docs/VRMED-ESOFAGO-SNAPSHOT-V1.json` | `398037723b9e6e86124f46b97f1c8967065ddf5a52d3069f1b8d7373b9701847` |
| `docs/overnight/phase25/split.json` | `c0a9f4453c70f87cbcb4f45a3b3136e9c611a7062ae8ff69a783fa3b2fd90e55` |
| `docs/overnight/phase25/auditoria.json` | `795320034091c8096ef52ef478c35110c69fec2584b9ed5aae4427fedc52dbe6` |
| `docs/overnight/phase25/mutacao_rerun.json` | `7720be1996b8f745bf8d93c6d601d9fd0bdf89361c24e48326dac4c3a9ec5e14` |

**Hash do congelamento (conteúdo canônico, o que vale):**
`9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192`

---

## 12. Os 16 casos e sua partição

`bucket` = `sha256(case_id) mod 100`. `validation` se `bucket < 25`.

| # | case_id | bucket | split |
|---|---|---|---|
| 1 | `4DLUNG-100_HM10395` | 34 | **train** |
| 2 | `4DLUNG-101_HM10395` | 22 | **validation** |
| 3 | `4DLUNG-102_HM10395` | 86 | **train** |
| 4 | `4DLUNG-103_HM10395` | 20 | **validation** |
| 5 | `4DLUNG-104_HM10395` | 20 | **validation** |
| 6 | `4DLUNG-105_HM10395` | 43 | **train** |
| 7 | `4DLUNG-106_HM10395` | 56 | **train** |
| 8 | `4DLUNG-107_HM10395` | 5 | **validation** |
| 9 | `4DLUNG-108_HM10395` | 48 | **train** |
| 10 | `4DLUNG-109_HM10395` | 99 | **train** |
| 11 | `4DLUNG-110_HM10395` | 98 | **train** |
| 12 | `4DLUNG-111_HM10395` | 44 | **train** |
| 13 | `4DLUNG-112_HM10395` | 53 | **train** |
| 14 | `4DLUNG-114_HM10395` | 99 | **train** |
| 15 | `4DLUNG-115_HM10395` | 7 | **validation** |
| 16 | `4DLUNG-116_HM10395` | 7 | **validation** |

O `bucket` é função pura do `case_id`: reproduzível em qualquer máquina, para sempre,
sem semente.
