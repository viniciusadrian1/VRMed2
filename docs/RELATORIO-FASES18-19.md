# Fases 18–19 — auditoria final do LyNoS e rota para um baseline auditável

Execução autônoma · 2026-09-06 · **Nada treinado · Nada avaliado no LyNoS · Split congelado intocado**

> **A Fase 18 derrubou três afirmações da Fase 15 — inclusive uma que era erro nosso — e
> encontrou um overlap que ninguém tinha procurado.**
> **A Fase 19 construiu a infraestrutura que torna o próximo baseline auditável, e parou
> exatamente onde deve parar: sem dados.**

---

## Fase 18

### LyNoS

**FATO.** 15 TCs mediastinais com contraste, St. Olavs Hospital / SINTEF / NTNU, esôfago em
NIfTI binário próprio. Todas as 15 máscaras foram baixadas (11 MiB) e medidas.

O que a fase mediu diretamente, sem intermediário:

| Medida | Resultado |
|---|---|
| compatibilidade com a `ESOPHAGUS_ONTOLOGY_V1` | **SIM, 15/15** |
| buracos 2D (critério do "preenchido") | **0,0000 % a 0,0420 %** |
| volume · extensão axial | 26,5–62,7 mL · 171–325 mm |
| orientação | `LPS` em 15/15 |
| máscara na mesma grade da TC | **15/15 verificado** (240 KiB, não 3 GB) |
| HuggingFace × Zenodo, CRC-32 | **15/15 idênticos** (76 KiB, não 2,7 GiB) |

As duas últimas linhas eram **premissas** em qualquer análise anterior. Agora são medidas.

### Licença — **RESOLVIDO**, e a Fase 15 estava errada

**A "divergência entre três fontes oficiais" não existia.** Era confusão nossa entre
**código** e **dado**:

1. o GitHub **não hospeda imagem alguma** — árvore recursiva completa: 23 blobs, ~400 KB,
   dos quais 366 KB são um notebook. Seu README escopa literalmente: *"The code in this
   repository is released under MIT license"*;
2. o `license: mit` do card do HuggingFace é **contradito pela prosa do próprio arquivo**, e
   o `LyNoS.py` **baixa os bytes do Zenodo**;
3. o **BSD-2-Clause pertence a outro repositório** (`dbouget/ct_mediastinal_structures_segmentation`,
   o do modelo pré-treinado). O rótulo da Fase 15 — *"LyNoS / ct_mediastinal_structures_segmentation"* —
   **fundiu dois repositórios** e importou a licença de um para o outro.

**`LYNOS_LICENSE = RESOLVIDO — CC BY 4.0`** (Zenodo 10102261, versão única, aberto, sem
embargo). Ressalva: **nenhuma fonte nomeia o titular de direitos** sobre as imagens.

**E não existe DOI do dataset.** O campo `doi` do Zenodo é o DOI do **artigo**
(`10.1080/21681163.2022.2043778`, `provider: external`, `conceptdoi: null`). A primeira
versão da ficha desta execução registrou `10.5281/zenodo.10102261` — **um DOI inexistente**,
corrigido.

### Overlap

**Dois overlaps distintos, e só um deles é o que se procurava.**

**1 — Com o treino do baseline: `SEM_OVERLAP_DETECTADO`.**

| Medida | Valor |
|---|---|
| match exato contra `shapes_after_crop` do `Dataset291` | 2/15 (`pat4`, `pat13`) |
| esperado sob a nula (permutação exata por bloco) | 0,931 |
| **p** | **0,229** |

**Um defeito de instrumento quase produziu o oposto.** O primeiro nulo sorteava `y` e `x` de
**casos diferentes**, gerando alvos retangulares contra um pool que é **75,0 % quadrado no
plano**. O esperado saía **0,041**, e 2 acertos virariam *"sinal de 49×"*. O nulo correto
embaralha **blocos** (eixo axial × plano), preserva a quadratura, e dissolve o sinal.
O acerto do `pat4` cai em `(221, 221)` — a **segunda moda do pool inteiro**, 48 imagens.

**Piso de detecção declarado:** 3 acertos já dariam `p = 0,043`; com poder ≈0,75 por membro,
**a sonda só separa inclusão do acaso a partir de ~4 casos em 15.** De 1 a 3 é invisível.

**2 — Com o AeroPath: `OVERLAP_IDENTIFICADO`, por hash.**

**FATO.** As 15 TCs do LyNoS são **byte-idênticas** aos sujeitos 1–15 do **AeroPath** —
mesmo `SHA-256` de Git-LFS e mesmo tamanho, **15/15**, com mapeamento verificado
(`Pat10→AeroPath/1`, `Pat1→2`, …). **Nenhuma fonte oficial declara esse overlap**, e a
string `LyNoS` não ocorre no texto do artigo do AeroPath.

O espelho `MedOtter/AeroPath` no HuggingFace redistribui os **volumes completos** — terceiro
canal público das mesmas imagens.

A **anotação** de esôfago não vazou por aí (o AeroPath só rotula vias aéreas e pulmões).
**A imagem, sim.**

### Ontologia

`LYNOS_ONTOLOGY = SIM` — 15/15, por medição, com controle positivo (um anel oco sintético é
**reprovado** pelo mesmo código). A ontologia **não foi reescrita** para caber no dataset: o
limiar de "preenchida" separa os dois regimes por duas ordens de grandeza.

### Independência

`LYNOS_INDEPENDENCE = INDETERMINADA` — e por **mais** razões que na Fase 15:

- **420/1.559** imagens de treino do baseline não atribuídas; códigos de instituição
  anonimizados (A–J) **sem chave publicada**;
- zero menções a Noruega, Trondheim, St. Olavs, NTNU ou SINTEF em 44 páginas do artigo do
  TotalSegmentator — **e ausência de menção não é evidência de ausência**;
- o mesmo artigo declara *"CT images from 8 different sites and 16 different scanners"* —
  **o treino é multi-site por declaração própria**;
- **a janela de aquisição da imagem é UNKNOWN**, o que desmonta o argumento cronológico que
  sustentava o LyNoS na Fase 15: anterioridade da **anotação** (2019) não é anterioridade da
  **imagem**;
- as imagens circulam em **três canais públicos** sem qualquer declaração de overlap.

E a **circularidade de anotação** do baseline (SegTHOR/BTCV semeando a primeira segmentação
do treino) permanece **invisível a qualquer sonda de imagem** — esta fase não mudou isso.

### TEST

`LYNOS_TEST_STATUS = CANDIDATO A TEST EXTERNO SECUNDÁRIO, CONDICIONAL`

**Nunca "TEST independente".** Seis condições cumulativas antes de qualquer uso (§11.1 do
relatório da fase), das quais as duas mais duras: **excluir explicitamente AeroPath, seus
espelhos e o depósito Dryad de qualquer treino**, e **nunca** usar o modelo pré-treinado do
próprio grupo como comparador — ele viu os 15 na validação cruzada.

**n=15 foi quantificado sem gastar o conjunto.** Nenhum Dice foi medido no LyNoS: um
conjunto olhado antes de o protocolo ser congelado deixa de poder servir de TEST. A força
do conjunto foi calculada a partir da dispersão que o projeto já tem:

| n | largura do IC95 | | Δ de Dice | poder em n=15 |
|---:|---:|---|---:|---:|
| **15** | **0,0772** | | 0,02 | 0,156 |
| 30 | 0,0550 | | **0,05** | **0,485** |
| 60 | 0,0388 | | 0,10 | 0,921 |

Com n=15, **um único caso trocado move a média em 0,0203 de Dice**. E este é um **piso
otimista**: a dispersão de referência é do LCTSC (sem contraste), e o LyNoS é diagnóstico
**com** contraste.

**DECISÃO DA FASE 18: B — candidato parcial.**

---

## Fase 19

### Dataset próprio

`VRMED-ESOPHAGUS-DATASET-V1` — **22 campos obrigatórios**, `UNKNOWN` explícito jamais
estimado. `case_id`, `image_sha256` e `mask_sha256` **não podem** ser `UNKNOWN`: são
identidade, não metadado.

**Estado: esquema pronto, zero casos.** Preencher split com caso inventado seria a fraude
que 18 fases documentaram nos outros.

### Proveniência

Manifesto **JSONL canônico** — ordenado por `case_id`, chaves ordenadas, com `sha256`
próprio. A serialização é canônica de propósito: sem isso o congelamento viraria ruído de
ordem de inserção em vez de trava.

Responde por construção à pergunta que o baseline atual não responde: **"de onde veio este
caso?"**

### Splits

**Desenho, não lista.** Nove regras, todas verificadas por código. A proporção **não** foi
fixada — fixá-la antes de saber quantos casos existem seria número inventado.

**Vazamento verificado por quatro identidades:** `case_id`, `study_id`, `series_id` e o
**`sha256` do conteúdo**. As três primeiras podem ser renomeadas por engano; o hash não.

### Hashes

`SHA-256` de imagem, máscara, manifesto e snapshot. Depois do congelamento, qualquer
mudança exige **VERSION INCREMENT** — nunca edição silenciosa da V1. `congelar()` **recusa**
manifesto inválido: não se congela defeito.

### Anti-leakage

**PASS.** Sete injeções deliberadas exigem falha do sistema e restauram o estado. A sétima
**abre de fato** o TEST para o contexto de treino, confirma que a mutação teve efeito,
restaura, e então exige que a trava **volte a valer**.

**Cinco mutantes plantados nos próprios validadores, cinco derrubados** (4, 4, 3, 3 e 1
falhas). Um validador que devolve "nenhum erro" precisa provar que consegue ver.

### Ontologia

`ESOPHAGUS_ONTOLOGY_V1`, **sem segunda definição**. A validação de alvo do `plano.py`
**importa** a função que julgou o LyNoS na Fase 18 em vez de reimplementá-la — duas cópias
divergiriam, e a divergência apareceria como diferença de desempenho.

### Baseline

`BASELINE_ESOFAGO_VRMED_V1` — **nnU-Net v2 `3d_fullres`**, seed `20260906`, **os cinco
folds** (não apenas o `0`), com o `splits_final.json` publicado junto dos pesos — que é
exatamente o arquivo cuja ausência torna o baseline atual inauditável.

**Critério de sucesso procedimental, não numérico.** Um limiar de Dice escolhido agora seria
chute; escolhido depois, seria ajuste ao resultado. O modelo é aceito se for reproduzível a
partir do manifesto congelado, do seed e do commit — **qualquer que seja o Dice**.

### Reprodutibilidade

Versões **lidas do interpretador**, nunca digitadas: Python 3.13.11 · `nnunetv2` 2.8.1 ·
`torch` 2.6.0+cu124 · `numpy` 2.5.2 · `SimpleITK` 2.5.6 · `nibabel` 5.4.2 ·
`TotalSegmentator` 2.18.0 · RTX 4060 Ti 16.380 MiB.

**`MONAI` aparece como AUSENTE de propósito**, e um teste falha se ele passar a ser
reportado como presente sem estar instalado.

**RESULTADO DA FASE 19: B — parcialmente pronto.**

### O achado de desenho da fase

O contrafactual do `candidatos.py` mediu um limite que nenhum download resolve:

> **`study_id` e `series_id` não existem no canal NIfTI.** Duas das quatro identidades
> anti-vazamento ficam **cegas** para qualquer dataset distribuído fora do DICOM — e o LyNoS
> é um deles.

---

## Critérios K

| | Estado | Por quê |
|---|---|---|
| **K1** — desenho TRAIN/VAL/TEST defensável | **BLOQUEADO** | o **desenho** está pronto e testado; a **lista** não existe, e nenhum caso tem procedência completa |
| **K2** — baseline comparável sem vazamento conhecido | **BLOQUEADO** | inalterado pela Fase 18: circularidade de anotação (SegTHOR/BTCV) + 420 imagens não atribuídas |
| **K3** — avaliação futura com conjunto independente | **BLOQUEADO** | o único candidato é condicional, e sua imagem circula em três canais públicos |
| **K4** — definição do alvo congelada | **RESOLVIDO** | `ESOPHAGUS_ONTOLOGY_V1`, verificada em 15/15 casos novos nesta execução |

**A Fase 18 não moveu K1, K2 nem K3.** Ela tornou o bloqueio de K3 **mais preciso**: a
barreira não é falta de dataset, é falta de **procedência da imagem** — e isso não se resolve
buscando mais, resolve-se do lado do modelo.

## Treinamento

# **BLOQUEADO**

**INFRAESTRUTURA e METODOLOGIA: prontas.** **DADOS: bloqueados.**

Pré-registro escrito em [`BASELINE-ESOPHAGUS-VRMED-V1.md`](BASELINE-ESOPHAGUS-VRMED-V1.md).
**"Pronto para pré-registro" não significa "pronto para treinar".**

## Próxima ação

> **Ingerir os 15 casos do LyNoS pelo funil do `VRMED-ESOPHAGUS-DATASET-V1` — baixando as
> TCs para gerar `image_sha256` — e congelá-los como TEST-2 condicional antes de qualquer
> outro trabalho.**

Uma única ação, e é a certa por três razões medidas nesta execução: é o **único** bloqueio
estrutural que um download resolve (o contrafactual provou que a validação passa depois
dele); congelar **antes** é a única forma de o conjunto ainda poder servir de TEST; e o
esquema, o funil e as guardas **já existem e estão testados** — falta só o dado passar por
eles.

---

## Correções a relatórios anteriores

**O histórico é preservado; o estado atual é corrigido.**

| Onde | Antes | Agora |
|---|---|---|
| Fase 15 §3.3.3 · matriz §1.1 | "conflito de licença entre três fontes oficiais" | **REFUTADO** — CC BY 4.0; era confusão código × dado |
| Fase 15, rótulo | "LyNoS / ct_mediastinal_structures_segmentation" | **dois repositórios distintos**; o BSD-2-Clause é do segundo |
| Fase 15 §3.2 | "canais e modalidade disjuntos" | **incompleto** — a imagem é a mesma do AeroPath |
| Fase 15 §3.2 | anterioridade da anotação a favor | **neutralizado** — janela de aquisição UNKNOWN |
| Ficha de candidato (1ª versão desta execução) | `10.5281/zenodo.10102261` | **DOI inexistente** |

## Instrumentos e defeitos

**Seis módulos novos**, todos com autoteste que roda antes do dado:
`lynos/auditoria.py` · `lynos/calibracao.py` · `lynos/grade_ct.py` · `lynos/adequacao.py` ·
`lynos/integridade.py` · `baseline_v1/{manifesto,plano,candidatos}.py` ·
`tests/test_baseline_v1.py`.

**Cinco defeitos encontrados por controle, não por revisão — quatro deles meus:**

1. **nulo da sonda deflacionado 22×** — sem a correção, esta execução publicaria "overlap de
   49×";
2. **premissa não verificada** (máscara na grade da TC) — virou verificação de 15/15;
3. **guarda olhando o campo errado** — procurava a declaração de contexto em `nota`, e ela
   mora em `cmd`;
4. **achado confundido com defeito** — o bloqueio residual do contrafactual era informação,
   e agora o teste **exige** que ele continue aparecendo;
5. **DOI fabricado** — `10.5281/zenodo.10102261` não existe.

## Auditoria final

**PASS = 157 · FAIL = 0 · SKIP = 0** — 48 de suíte + 81 de autoteste + 28 de mutação.
Varredura de docs: **40 documentos, 0 violações**.
Split congelado: `sha256` `6e54c02b58bbb9b3a1667d4672eddef6…`, mtime `2026-09-04T21:19:49`,
**INTOCADO**.
