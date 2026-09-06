# Fase 18 — auditoria cética definitiva do LyNoS

Data: 2026-09-06 · 7 arms de fonte primária · 7 passes céticos · 15 casos medidos · Nada treinado

> **A fase virou o LyNoS do avesso, e três coisas que a Fase 15 afirmou não sobreviveram.**
> O conflito de licença **não existia** — era confusão nossa entre código e dado. Em
> compensação, apareceu um overlap que ninguém tinha procurado: **as 15 imagens do LyNoS
> são byte-idênticas às do AeroPath**, provado por SHA-256, e **nenhuma fonte oficial
> declara isso**.

```
LYNOS_OVERLAP      = OVERLAP_IDENTIFICADO (com o AeroPath, por hash) ·
                     SEM_OVERLAP_DETECTADO (com o treino do Dataset291, p = 0,229)
LYNOS_LICENSE      = RESOLVIDO — CC BY 4.0 (Zenodo), com ressalva de titularidade
LYNOS_ONTOLOGY     = SIM — 15/15, por medição
LYNOS_INDEPENDENCE = INDETERMINADA
LYNOS_TEST_STATUS  = CANDIDATO A TEST EXTERNO SECUNDÁRIO, CONDICIONAL
```

**DECISÃO: B — candidato parcial.**

---

## 1. Objetivo

Determinar exatamente o que pode e o que **não** pode ser afirmado sobre o LyNoS como
futuro conjunto de avaliação. A Fase 15 o classificou como **E** (independência
indeterminada) e registrou explicitamente que **não houve passe cético** — a sessão caiu
antes. Esta fase é esse passe, mais medição direta.

## 2. Estado inicial

Herdado da Fase 15, e tudo isto foi testado aqui:

| Afirmação da Fase 15 | Estado após a Fase 18 |
|---|---|
| esôfago binário preenchido, compatível com a ontologia | **CONFIRMADO** e ampliado de 2 para **15/15** casos |
| conflito de licença entre três fontes oficiais | **REFUTADO** — ver §3 |
| GT de 2019, anterior ao TotalSegmentator | **MANTIDO**, mas irrelevante para a imagem — ver §5 |
| independência indeterminada | **MANTIDO**, e por mais razões — ver §9 |
| n=15 com IC largo | **QUANTIFICADO** — ver §7 |

**Instrumentos existentes localizados e reusados:** `screen_geometria.py` (sonda da Fase
16), `sobreposicao_uid.py`, `ontologia_esofago.py`, e as 2 máscaras já baixadas na Fase 15.

## 3. Licença — **RESOLVIDO**, e a Fase 15 estava errada

**FATO.** O Zenodo (`api/records/10102261`) declara `metadata.license = {"id":
"cc-by-4.0"}`, `access_right: "open"`, sem embargo, **versão única** (`hits.total = 1`).
Verificado diretamente nesta sessão.

**FATO.** O `LICENSE` de `github.com/raidionics/LyNoS` é MIT, `spdx_id: MIT`, com **um
único commit** em toda a história do arquivo (`6c74cba861`, 2023-11-08). **Nunca houve
mudança de licença.**

**FATO — e este é o ponto.** O README declara o escopo literalmente:

> "The code in this repository is released under MIT license"

**A palavra `code` é o único escopo declarado.** E o repositório GitHub **não hospeda
imagem nenhuma**: a árvore recursiva completa tem 23 blobs, ~400 KB, dos quais 366 KB são
um único *notebook*. Não há `.nii`, `.nii.gz` nem diretório de dados.

**FATO.** O `LyNoS.py` do HuggingFace **baixa o zip do Zenodo** (`_URLS` aponta para
`zenodo.org/records/10102261/files/LyNoS.zip`). Os bytes que o usuário recebe vêm do
Zenodo.

### 3.1 De onde veio o "conflito" que a Fase 15 registrou

Três erros nossos, todos identificados em fonte primária:

1. **BSD-2-Clause nunca existiu em `raidionics/LyNoS`.** Ele pertence a
   `dbouget/ct_mediastinal_structures_segmentation` — **outro repositório**, o do modelo
   pré-treinado. O rótulo da Fase 15, *"LyNoS / ct_mediastinal_structures_segmentation"*,
   **fundiu dois repositórios** e importou a licença de um para o outro.
2. **O `license: mit` do card do HuggingFace é contradito pela prosa do próprio README**,
   no mesmo arquivo.
3. **Confusão código × dado.** Contar "2 de 3 fontes dizem MIT" soma uma fonte que **não
   distribui dado** (GitHub) a um campo YAML contradito pelo próprio arquivo.

**STATUS_LICENCA = RESOLVIDO.** A única declaração que fala pelos **dados** é a do
registro que hospeda os bytes: **CC BY 4.0**.

### 3.2 A anomalia do card, e o que ela virou

**FATO.** `cardData.pretty_name` do LyNoS diz literalmente **`"AeroPath"`** — outro
dataset do mesmo autor. O `cardData` inteiro é **idêntico campo a campo** ao do AeroPath
nos 6 campos. O `LyNoS.py` carrega um comentário residual `# append AeroPath`.

**E o cético achou algo mais forte que a hipótese original:** o **próprio AeroPath**
declara `license: mit` no card mas distribui um `license.md` de **18.666 bytes** cujo
texto é **CC BY 4.0**, e seu README diz `"Licenses/Restrictions: CC-BY 4.0 (See
license.md)"`. **O campo `license` do card deste autor é comprovadamente errado no
dataset-fonte da cópia.**

**RECOMENDAÇÃO.** O card do HuggingFace é fonte de **baixa autoridade** para licença.
Citar CC BY 4.0 com atribuição a Bouget et al. e ao registro Zenodo.

**RESSALVA que o cético impôs e que fica registrada:** *nenhuma* das fontes nomeia o
**titular de direitos** sobre as imagens de TC. Aprovação ética, consentimento e
autorização institucional para redistribuição são `UNKNOWN` por todas as fontes oficiais.

### 3.3 Não existe DOI do dataset

**FATO.** O campo `doi` do registro Zenodo é **`10.1080/21681163.2022.2043778`**, com
`provider: "external"` e `conceptdoi: null`. Esse é o DOI do **artigo** na Taylor &
Francis (Crossref: `type: journal-article`).

**Consequência prática, e ela nos atingiu:** a primeira versão da ficha de candidato desta
fase registrou `10.5281/zenodo.10102261` — **um DOI que não existe**. Corrigido no mesmo
commit em que foi detectado.

## 4. Sonda geométrica — controles, um defeito, e o resultado

### 4.1 Os controles passaram, mas o instrumento estava quebrado do lado do nulo

`controle positivo = DETECTADO` · `controle negativo = NÃO DETECTADO` — ambos OK.

**Mas os controles não cobriam o nulo, e o nulo estava errado.** A primeira calibração
sorteava `y` e `x` de **casos diferentes**, produzindo alvos **retangulares**. O pool de
treino é **75,0 % quadrado no plano** (1.169/1.559). O nulo passou a gerar alvos que quase
nunca poderiam casar:

| | nulo defeituoso | nulo por bloco (correto) |
|---|---:|---:|
| esperado em 15 (match exato) | 0,041 | **0,931** |
| razão obs/esperado | 49× | **2,15** |
| **p** | — | **0,229** |

O nulo correto embaralha **blocos** — eixo axial `(n, dz)` contra plano `(rows, cols, py,
px)` — preservando a quadratura e destruindo exatamente o que a nula precisa destruir: a
associação entre extensão axial e campo de visão do mesmo exame. Com 15 casos há 225 pares,
então é **teste de permutação exato**, não amostragem.

**Sem a correção, esta fase teria publicado "sinal de overlap de 49×".**

### 4.2 O resultado

| Medida | Valor |
|---|---|
| match exato (3 eixos) | **2/15** — `pat4`, `pat13` |
| esperado sob a nula | 0,931 |
| **p (permutação, 200.000)** | **0,229** |
| match tolerância ±2 | 7/15 · esperado 6,737 · p = 0,555 |

**Por que os dois acertos são baratos:** o plano de `pat4` é `(221, 221)` — a **segunda
moda do pool inteiro**, 48 imagens de treino. O de `pat13` é `(231, 231)`, 15 imagens.

**Classificação:**
- **coorte:** `SEM_OVERLAP_DETECTADO`
- **`pat4` e `pat13`, individualmente:** `INDETERMINADO` — a geometria exata está na lista

**E a regra vale nos dois sentidos.** A Fase 16 fixou que *"sem overlap detectado" não é
"independência demonstrada"*. O espelho é igualmente obrigatório: **`OVERLAP_IDENTIFICADO`
por coincidência geométrica não é overlap demonstrado.**

### 4.3 O piso de detecção — a limitação que importa

Da distribuição nula: **3 acertos** já dariam `p = 0,043`. Com poder ≈0,75 por membro
(limite declarado da Fase 16, não remedido aqui), isso significa:

> **A sonda só distingue inclusão do acaso a partir de ~4 casos incluídos em 15. A
> inclusão de 1 a 3 casos é invisível para ela.**

E **`pat5` e `pat12` são os únicos dois casos com ZERO imagens de treino no seu plano** —
para eles o negativo tem alguma força. Para os outros treze, o plano é comum demais.

### 4.4 A premissa que virou verificação

A sonda lê o cabeçalho da **máscara** (1 MiB) em vez do da **TC** (180–263 MB). Isso só
vale se as duas moram na mesma grade — e isso era **premissa**.

**Verificado 15/15** por `Range` HTTP + descompressão incremental do cabeçalho NIfTI-1:
**240 KiB** de tráfego em vez de ~3 GB. `VEREDITO: PREMISSA VERIFICADA`.

## 5. Proveniência — quatro datas, quatro entidades

### 5.1 O achado que muda tudo: a imagem não é exclusiva do LyNoS

**FATO, provado por hash.** As 15 TCs do LyNoS são **byte-a-byte idênticas** aos sujeitos
1–15 do **AeroPath** — mesmo `SHA-256` de Git-LFS e mesmo tamanho, **15/15**. Mapeamento
verificado: `Pat1→2, Pat2→3, Pat3→4, Pat4→5, Pat5→6, Pat6→7, Pat7→8, Pat8→9, Pat9→10,
Pat10→1, Pat11→11, …, Pat15→15`.

O cético re-verificou paginando as duas árvores do HuggingFace: *"isso não é
plausibilidade, é hash"*.

**Nenhuma fonte declara esse overlap.** O artigo do AeroPath cita o do LyNoS mas a string
`LyNoS` **não ocorre** no texto completo do AeroPath.

**E o cético piorou o quadro:** a organização `MedOtter` no HuggingFace espelha o AeroPath
**com os volumes completos** — o arm tinha registrado, erradamente, que só espelhava
fatias médias. **Terceiro canal público das mesmas imagens.**

**Consequência direta:** qualquer modelo que tenha visto AeroPath (vias aéreas/pulmões) viu
**as imagens** do LyNoS. A **anotação** de esôfago não vazou por aí — o AeroPath só rotula
vias aéreas e pulmões — mas a imagem sim.

### 5.2 A cadeia de anotação do esôfago

| Pergunta | Resposta |
|---|---|
| janela de aquisição das TCs | **UNKNOWN** |
| scanner, protocolo de contraste | **UNKNOWN** |
| comitê de ética, número de aprovação | **UNKNOWN pelas fontes do LyNoS** — obtido lateralmente via AeroPath (§6.2) |
| critério de inclusão | **UNKNOWN** — apenas *"lung cancer patients"* |
| quem anotou o esôfago | **UNKNOWN** |
| medida interobservador para o esôfago | **NÃO EXISTE** |

**FATO decisivo.** O único exercício de segundo leitor documentado (preprint de 2021, sobre
**linfonodos**) declara literalmente: *"the task was not asked to be performed by the second
expert"*.

**INFERÊNCIA.** O esôfago do LyNoS deve ser tratado como referência de **anotador único e
não identificado**.

**Ressalva que o cético impôs:** o README do repositório oficial diz *"The annotations for
the benchmark subset have been proofed by an expert radiologist"* — logo *"não documentado
em lugar nenhum"* é forte demais. O que é verdade: **não se diz quais anotações, nem por
quem, nem com que protocolo.**

**FATO.** O texto completo do artigo de 2019 é **fechado** (Unpaywall `oa_status: closed`,
OpenAlex sem full-text, sem preprint). Tudo acima vem da *landing page* pública, do preprint
de 2021 e dos READMEs. **Isto é lacuna declarada, não inexistência.**

### 5.3 Um precursor provável, e uma citação nossa que estava errada

**INFERÊNCIA (média).** As imagens provavelmente foram **reaproveitadas** de um estudo
clínico anterior de St. Olavs (Reynisson et al., 2015, PLoS ONE; dados no Dryad
`10.5061/dryad.mj76c` sob **CC0**), e não adquiridas para o estudo de anotação de 2019. A
correspondência é **por tamanho** (15 de 17, delta 428–1917 bytes), não por hash.

**O cético derrubou parte disso, e entra corrigido:**
- Reynisson **nunca nomeia St. Olavs** — diz apenas *"patients included in a clinical study
  approved by the Regional Ethical Committee"*;
- a citação de apoio do arm apontava para o **artigo errado** (o PMID citado é um estudo de
  RM em transtorno bipolar);
- **contra-indício**: o LyNoS é descrito em toda parte como *contrast-enhanced*, e o artigo
  de Reynisson tem **zero** ocorrências de *contrast*.

**Portanto: precursor PLAUSÍVEL, NÃO DEMONSTRADO.**

## 6. Compatibilidade anatômica — **SIM, 15/15**

**FATO, medido.** As 15 máscaras contra a `ESOPHAGUS_ONTOLOGY_V1`:

| Critério | Resultado |
|---|---|
| binária (`{0,1}`) | **15/15** |
| não vazia | **15/15** |
| **preenchida** (parede + lúmen um objeto) | **15/15** — buracos 2D de **0,0000 % a 0,0420 %** |
| objeto único dominante | 15/15 (maior componente > 0,99) |
| calibre compatível | 15/15 |
| **ONTOLOGY_COMPATIBLE** | **SIM** |

Volume 26,5–62,7 mL · extensão axial 171–325 mm · orientação `LPS` em 15/15 ·
spacing in-plane 0,648–0,824 mm, `dz` 0,5 mm (14 casos) e 1,25 mm (`pat9`).

**A ontologia não foi reescrita para caber no dataset.** O limiar de "preenchida" (1 %)
separa os dois regimes por **duas ordens de grandeza**, e o controle positivo — um anel oco
sintético — é reprovado pelo mesmo código.

**Ressalva declarada:** a **extensão longitudinal é herdada do GT e não avaliável
anatomicamente**, por definição da V1. Ela **não** é critério de aprovação aqui.

### 6.1 As máscaras medidas são as máscaras que a licença cobre

**A pergunta não é retórica.** A ontologia foi medida em 15 arquivos do **HuggingFace**;
a licença apurada no §3 é a do **Zenodo**. São hosts diferentes, e *"o loader baixa do
Zenodo, logo é o mesmo dado"* é **inferência sobre um script**, não verificação de bytes.
Se divergissem, as duas metades desta fase ficariam desconectadas.

**FATO, verificado.** O `Central Directory` do `LyNoS.zip` foi lido por `Range` HTTP e
traz o **CRC-32 de cada membro**. Comparado ao CRC-32 dos arquivos locais:

**15/15 IDÊNTICOS** — CRC-32 e tamanho, arquivo a arquivo. Tráfego: **76,2 KiB** contra
2,70 GiB do zip. O depósito tem 107 entradas.

**VEREDITO: MESMO DADO.** A medição de ontologia vale para o dado licenciado.

**Ressalva declarada:** CRC-32 não é criptográfico. Ele responde à pergunta feita —
divergência acidental entre espelhos — e não serve contra adversário.

### 6.2 A aprovação ética existe, por identidade de hash

**FATO.** O artigo do AeroPath declara: **REK Sør-Øst A, referência 2010/3385a**, acesso
para pesquisa de 16/03/2011 a dezembro de 2023, com consentimento informado por escrito.

**INFERÊNCIA.** Como as imagens do LyNoS **são** as do AeroPath (§5.1, por SHA-256), essa
aprovação cobre as mesmas imagens. O arm de proveniência havia registrado ética como
`UNKNOWN` — e estava certo *pela sua própria fonte*; o número veio pelo caminho lateral.

**A transferência é inferência, não fato**, e fica marcada como tal: nenhuma fonte do
LyNoS cita esse número. E **CC BY 4.0 não cobre o eixo ético**: aprovação para uso
secundário, consentimento e base legal sob GDPR para processamento fora do EEE são
questões **independentes da licença**, e permanecem em aberto.

## 7. Tamanho amostral — n=15

**Nenhum Dice foi medido no LyNoS, de propósito.** Medir agora **gastaria** o candidato:
um conjunto olhado antes de o protocolo ser congelado deixa de poder servir de TEST. E a
regra 20 desta fase proíbe tratá-lo como TEST enquanto a independência do baseline estiver
indeterminada — e ela está.

A pergunta *"quão forte seria um resultado em n=15?"* é de **desenho**, e se responde com a
dispersão que o projeto já tem (Dice do esôfago, `development` do LCTSC, n=30,
`A_BASELINE_V1`: média 0,7759, dp 0,0790, IQR 0,0643):

| n | largura do IC95 da média | erro padrão |
|---:|---:|---:|
| **15** | **0,0772** | 0,0200 |
| 30 | 0,0550 | 0,0141 |
| 60 | 0,0388 | 0,0100 |
| 100 | 0,0300 | 0,0077 |

| Diferença de Dice | Poder em n=15 |
|---:|---:|
| 0,02 | **0,156** |
| 0,05 | **0,485** |
| 0,10 | 0,921 |

**Leitura:** com n=15, **trocar um caso mediano pelo pior observado move a média em 0,0203
de Dice** — quase o tamanho do efeito de 0,02 que se quereria detectar. E **uma diferença
de 0,05 é detectada menos da metade das vezes**.

**Ressalva.** Esta é a dispersão do **LCTSC** (TC de planejamento, sem contraste). O LyNoS
é TC diagnóstica **com contraste**; a dispersão dele quase certamente é **maior**. Estes
intervalos são um **piso otimista** de largura.

## 8. Riscos

| Risco | Gravidade |
|---|---|
| **imagem em ≥3 canais públicos** (LyNoS, AeroPath, espelho MedOtter) sem nenhuma declaração de overlap | **alto** — qualquer pré-treino que tocou AeroPath contamina |
| **anotador único não identificado**, sem medida interobservador | alto — não há banda humana local para contextualizar |
| **420/1.559 imagens de treino do baseline não atribuídas** | alto — impede qualquer declaração de independência |
| n=15 | alto — poder 0,485 para Δ=0,05 |
| protocolo diferente (contraste, diagnóstica) | médio — comparar com LCTSC mediria também protocolo |
| titular de direitos das imagens não nomeado | médio |
| `study_id` e `series_id` inexistentes no canal NIfTI | médio — **2 das 4 identidades anti-vazamento ficam cegas** |
| modelo pré-treinado do próprio grupo viu os 15 na validação cruzada | médio — nunca usar como baseline comparativo aqui |

## 9. O que está demonstrado

1. **Compatibilidade com a `ESOPHAGUS_ONTOLOGY_V1`: SIM, 15/15, por medição.**
2. **Licença dos dados: CC BY 4.0**, do registro que hospeda os bytes. O "conflito" da
   Fase 15 era confusão código × dado nossa.
3. **A máscara mora na grade da TC: 15/15**, verificado, não assumido.
4. **HuggingFace e Zenodo distribuem os mesmos bytes: 15/15** por CRC-32 — a medição de
   ontologia vale para o dado licenciado.
5. **As imagens do LyNoS são as imagens do AeroPath**, por SHA-256, 15/15, sem declaração
   em nenhuma fonte oficial.
6. **A sonda geométrica não vê excesso sobre o acaso** contra o treino do `Dataset291`:
   2/15 exatos, esperado 0,931, **p = 0,229**.
7. **n=15 dá IC95 de 0,077 de Dice e poder 0,485 para Δ=0,05.**
8. **O esôfago do LyNoS tem anotador único não identificado** e **nenhuma** medida
   interobservador.

## 10. O que permanece indeterminado

- **A independência.** Não foi encontrada **nenhuma** menção de Noruega, Trondheim, St.
  Olavs, NTNU ou SINTEF em 44 páginas do artigo do TotalSegmentator nem no repositório —
  **e ausência de menção não é evidência de ausência**. Os códigos de instituição do
  `meta.csv` são anonimizados (A–J) e **não há chave publicada**.
  E o cético acrescentou o que inverte o tom: o mesmo artigo declara *"CT images from 8
  different sites and 16 different scanners were included"*. **O treino é multi-site por
  declaração própria.**
- **A janela de aquisição da imagem.** UNKNOWN. Logo a anterioridade da anotação (2019)
  **não** estabelece anterioridade da imagem.
- **O precursor Dryad/Reynisson.** Plausível por tamanho, **não demonstrado** por hash.
- **Quem anotou o esôfago, com que protocolo, e se houve revisão.**
- **O titular de direitos, a aprovação ética e o consentimento** para as imagens do LyNoS.
- **A base legal para reuso** de dado clínico norueguês por entidade fora do EEE —
  eixo que **CC BY 4.0 não cobre** e que nenhum arm tocou.
- **A circularidade de anotação do baseline** (SegTHOR/BTCV semeando o treino) — **nenhuma
  sonda de imagem a enxerga**, e esta fase não mudou isso.

## 11. Decisão

# **B — candidato parcial**

**Por que não A.** A exigiria independência ao menos plausível. Três fatos a impedem: as
420 imagens não atribuídas do treino do baseline; a **imagem circulando em três canais
públicos** sem declaração; e a **janela de aquisição UNKNOWN**, que desmonta o argumento
cronológico que sustentava o LyNoS na Fase 15.

**Por que não C.** C seria rejeição. Seria excessivo: o alvo é **compatível por medição**
em 15/15, a licença **está resolvida e é aberta**, a sonda **não encontrou excesso sobre o
acaso**, e um grupo independente (Mathai et al., 2024) já o usa como teste
*out-of-distribution*. É utilizável — **como teste externo SECUNDÁRIO e condicional**.

**Nunca escrever "TEST independente".** A forma correta é **"candidato a TEST externo"** ou
**"TEST condicional"**.

### 11.1 Protocolo de uso, se e quando

```
TRAIN       = dados próprios auditáveis            (não existem)
VALIDATION  = dados próprios auditáveis            (não existem)
TEST        = dados próprios congelados            (não existem)
TEST-2      = LyNoS, CONDICIONAL e SECUNDÁRIO      (candidato)
```

Condições **obrigatórias e cumulativas** antes de qualquer uso:

1. auditar e **excluir explicitamente** do treino: `andreped/AeroPath`,
   `raidionics/AeroPath`, `zenodo.org/records/10069289`, `MedOtter/AeroPath`, Dryad
   `10.5061/dryad.mj76c`;
2. baixar as 15 TCs e registrar `image_sha256` — **hoje o esquema recusa a ficha por falta
   dele**;
3. registrar literalmente: aquisição UNKNOWN, scanner UNKNOWN, contraste UNKNOWN, ética
   UNKNOWN, anotador UNKNOWN, sem medida interobservador;
4. **nunca** usar o modelo pré-treinado do `raidionics` como comparador sobre o LyNoS — ele
   viu os 15 na validação cruzada;
5. reportar o resultado com IC e com a **declaração de poder** do §7;
6. citar CC BY 4.0 com atribuição a Bouget et al. e ao Zenodo 10102261, **nunca MIT**.

---

## 12. Correções a relatórios anteriores

**O histórico é preservado; o estado atual é corrigido.**

| Onde | Afirmação anterior | Correção |
|---|---|---|
| Fase 15 §3.3.3 e matriz §1.1 | *"Conflito de licença entre três fontes oficiais"* | **REFUTADO.** GitHub não hospeda dado; o MIT tem escopo de código, declarado no README; o card do HF é contradito pela prosa do próprio arquivo. **CC BY 4.0** (Zenodo). |
| Fase 15, rótulo do dataset | *"LyNoS / ct_mediastinal_structures_segmentation"* | **Dois repositórios distintos.** O BSD-2-Clause é do segundo, que é o do modelo pré-treinado. |
| Fase 15 §3.2 | *"instituições, países, canais e modalidade disjuntos"* | **INCOMPLETO.** Verdadeiro quanto ao LCTSC e ao NSCLC; **falso** como afirmação de exclusividade — a imagem é a mesma do AeroPath. |
| Fase 15 §3.2 | anterioridade da anotação como argumento a favor | **MANTIDO mas neutralizado**: a janela de aquisição da imagem é UNKNOWN. |
| Ficha de candidato desta fase (1ª versão) | `source_doi = 10.5281/zenodo.10102261` | **DOI INEXISTENTE.** O registro usa o DOI do artigo, `provider: external`, `conceptdoi: null`. |

---

```
FASE 18 CONCLUÍDA
DECISÃO: B — candidato parcial
LYNOS_OVERLAP      = OVERLAP_IDENTIFICADO (AeroPath, por SHA-256, 15/15, não declarado) ·
                     SEM_OVERLAP_DETECTADO (treino do Dataset291: 2/15, esperado 0,931, p = 0,229)
LYNOS_LICENSE      = RESOLVIDO — CC BY 4.0 (Zenodo 10102261); o "conflito" da Fase 15 era confusão código × dado
LYNOS_ONTOLOGY     = SIM — 15/15 por medição, buracos 2D de 0,0000 % a 0,0420 %
LYNOS_INDEPENDENCE = INDETERMINADA — 420/1559 não atribuídas, aquisição UNKNOWN, imagem em 3 canais públicos
LYNOS_TEST_STATUS  = CANDIDATO A TEST EXTERNO SECUNDÁRIO, CONDICIONAL — nunca "TEST independente"
INTEGRIDADE     = 15/15 CRC-32 identicos entre HuggingFace e Zenodo (76 KiB de trafego)
DEFEITO DE INSTRUMENTO CORRIGIDO: o nulo da sonda estava deflacionado 22x; sem a correção esta fase publicaria "overlap de 49x"
TREINO: BLOQUEADO
```
