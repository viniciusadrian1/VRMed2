# Fase 16 — auditoria de independência do baseline

Data: 2026-09-06 · 8 agentes · Nada treinado · Nenhum peso baixado

> **K2: BLOQUEADO · K3: BLOQUEADO.**
> A fase não fabricou prova de independência — e o achado central é justamente que
> **o pacote distribuído a torna estruturalmente indemonstrável.**
>
> Dois **OVERLAP IDENTIFICADO** novos, duas **independências demonstradas** (ambas
> estreitas), uma via de contaminação **impossível de detectar por medição**, e quatro
> correções numéricas contra afirmações do próprio dossiê.

---

## 1. O achado que ninguém consegue tocar

**FATO.** O suplemento S2 do artigo do TotalSegmentator declara que **SegTHOR** (nnU-Net
Task 55 — classes aorta, **esôfago**, coração, traqueia) e **BTCV** (Task 17, inclui esôfago)
foram usados como modelos pré-treinados para gerar a **primeira segmentação** do conjunto de
treino, depois refinada por humanos.

**INFERÊNCIA.** Isso não é vazamento de **imagem** — as imagens são de Basel. É **circularidade
de anotação**: o rótulo de esôfago do treino do baseline foi semeado por modelos treinados em
SegTHOR e BTCV. **Nenhuma sonda de imagem detecta isso** — nem as desta fase.

**Consequência dupla:**
- O `BASELINE_ESOFAGO_V1` herda convenção de contorno de SegTHOR/BTCV por um caminho que o
  projeto não tinha mapeado.
- **SegTHOR e BTCV saem da lista de candidatos a teste** para esôfago:
  `INDEPENDÊNCIA IMPOSSÍVEL DE ESTABELECER`. A lista de K3 **encolheu**.

## 2. Matriz de independência

| Dataset | Decisão | Base |
|---|---|---|
| **`Dataset343` (`pericardium`) × task `total`** | **OVERLAP IDENTIFICADO** | 1.524 formas em comum; 85,3 % do 343 vem do pool do `total` |
| **Coorte NSCLC do VRmed × SAROS** | **OVERLAP IDENTIFICADO** | `LUNG1-059` = `case_567` (**fold-2**), `LUNG1-042` = `case_546` (**fold-5**) — casamento exato de `tcia_case_id`, `SeriesInstanceUID` **e** `StudyInstanceUID`, ambos em folds de **treino** |
| **TotalSegmentator dataset (Zenodo)** | **OVERLAP IDENTIFICADO** | é o próprio treino, 73,1 % declarado |
| **SegTHOR × rótulo `esophagus`** | **IMPOSSÍVEL DE ESTABELECER** | circularidade de anotação (§1) |
| **BTCV × rótulo `esophagus`** | **IMPOSSÍVEL DE ESTABELECER** | idem |
| **LCTSC × task `total`** | **INDETERMINADA** | teto ≲4/60 num único canal |
| **NSCLC-Radiomics × task `total`** | **INDETERMINADA** | teto ≲4/25 |
| **SAROS × `Dataset343`** | **INDETERMINADA** | teto quantificado ≲30 casos |
| **LyNoS** | **INDETERMINADA** | não testado — mas a sonda **agora pode** ser aplicada |
| **LCTSC × SAROS** | **DEMONSTRADA** *(só neste par, só no canal de UID)* | interseção zero nas três chaves |
| **`Dataset117`** *(controle negativo)* | **DEMONSTRADA** | 291×117 = 0/1559 |

## 3. O que a forense dos pesos encontrou — e o que não encontrou

**FATO.** Inventário de `C:\Users\vinic\.totalsegmentator\nnunet\results`: 10 tasks, ~2,3 GB,
**apenas `fold_0`** em cada.

**Não existe:** model card · `splits_final.json` · **nenhum identificador de caso** — nem em
`dataset.json`, nem em `dataset_fingerprint.json`, nem dentro dos `.pth` (verificado lendo
opcodes com `pickletools`, **sem executar o pickle**).

**A ausência é o achado.** Não há como demonstrar independência com o que o pacote distribui.

### 3.1 Três descobertas laterais

1. **A opacidade não é do `343` — é do produto inteiro.** Os placeholders que a Fase 8 tratou
   como suspeitos do `343` (`reference: "Jakob"`, `licence: "-"`, `release: "0.0"`) estão
   **idênticos** em todas as 10 tasks, **inclusive na que produz o `BASELINE_ESOFAGO_V1`**.
2. **`debug.json` grava a máquina de treino**, não os dados: `rndapollolp01.uhbs.ch`
   (*uhbs* = University Hospital Basel), `/mnt/nor/nnunet/results_v2`, `/dojo`. **Treinar EM
   Basel não é treinar SÓ COM dados de Basel** — e essa distinção é exatamente onde o
   projeto errou por duas fases.
3. **Todos os modelos são `fold=0`, não `fold='all'`.** O modelo publicado viu ~80 % das
   imagens declaradas; **o arquivo que diz qual 80 % não foi publicado.** Logo nem as 1.139
   imagens *públicas* são atribuíveis ao treino efetivo — **a opacidade é maior que 26,9 %**.

### 3.2 O instrumento novo: sonda geométrica

**FATO.** `dataset_fingerprint.json` traz `shapes_after_crop` das **1.559 imagens de treino
reais, inclusive das 420 não publicadas**. Isso permite, pela primeira vez no projeto, um
**teste de condição necessária** sobre o treino não divulgado.

| Coorte | Acertos | Nulo esperado | p |
|---|---:|---:|---:|
| LCTSC (60 séries) | 3 | 2,40 | 0,502 |
| NSCLC-Radiomics (25) | 1 | 1,00 | 1,000 |

**Sem excesso sobre o acaso em nenhuma das duas.** Poder ≈0,75 por membro; `k ≥ 5` excluído a
~99,9 %.

**Mas teto não é prova.** A sonda é cega aos ~25 % do pool recortados *in-plane* e cega por
completo ao canal documental — inclusive à circularidade do §1.

## 4. SAROS × Dataset343 — a hipótese da Fase 8, testada e derrubada

**A acusação, na forma mais forte:** rótulos **idênticos**, 343 treinado em 2025 (depois da
publicação do SAROS), zero proveniência declarada, e o repositório **nunca menciona SAROS**.

**Três medições a derrubaram:**

| Teste | Resultado |
|---|---|
| **Teto populacional** | no máximo **262** imagens do 343 estão fora do pool do `total`. O SAROS tem 900 — não cabe |
| **Assinatura de espessura** | SAROS é 15/15 exatamente 5,0 mm → a 1,5 mm força `z ≡ {0,3,7} mod 10`. Medido no resíduo: **0,344** contra 0,323 no pool de Basel e 0,300 de acaso. **Sem enriquecimento.** Teto 95 %: **≈30 casos** |
| **Envelope de intensidade** | um cético o levantou como prova de dado externo — e **outro o refutou**: o envelope é função do conjunto de rótulos, não da origem; `294/297/298` são o mesmo pool com envelopes piores |

**Ressalva grave, declarada:** os 15 casos SAROS locais são **15/15 do split `test`** — a
amostra errada para detectar inclusão nos folds de treino.

## 5. Quatro correções numéricas contra o próprio dossiê

Os céticos derrubaram fatos dos arms. Todos entram corrigidos:

| Afirmação | Correção |
|---|---|
| *"1.524/1.559 (97,8 %) do task `total` está no 343"* | o denominador é `293/294/295`. Contra o **`Dataset291` — que é o que produz o esôfago do baseline** — é **1.334/1.559 = 85,6 %** |
| *"452 casos de origem não documentada no 343"* | **inflado em 72 %**; o teto correto é **262** (o 452 compara só contra o `291`) |
| *"1786/1786 spacings exatamente (1,5,1,5,1,5)"* | são **1.716/1.786**; os 70 fora da moda são *ulp* de float32 |
| *"o envelope de intensidade prova dado externo"* | **refutado** — é função do conjunto de rótulos |

**E uma correção de sinal contrário:** o arm dos pesos concluiu que a sonda geométrica *"não
tem poder"*. **Falso** — `(333,333)` ocorre 68× no `291`, e 75 % do pool é *in-plane* quadrado.
A sonda **tem** poder ≈0,75, e o zero anterior deixa de ser nulo e vira **negativo genuíno com
teto**.

## 6. O defeito ativo que a fase encontrou e corrigiu

**FATO.** A correção da Fase 9 — sobre os números 1082/57/65 serem da v1 — foi feita **só no
documento**. A afirmação falsa continuava sendo **emitida por máquina** em dois lugares:

- `.clinica-dados/tier2/lctsc/manifest.json`, campo **`proveniencia_gt`**;
- `scripts/validation/tier2/coorte.py:158` — **o gerador**, que a reemitiria a cada regeneração.

Ambos diziam: *"o task `total` foi treinado exclusivamente em TCs clínicas do University
Hospital Basel, sem datasets públicos de desafio — o LCTSC não está no treino."*

**Corrigidos nesta fase, o gerador junto com o artefato** — porque corrigir só o artefato é o
erro que a Fase 9 cometeu. O campo agora declara `INDETERMINADA`, com o teto medido e a
ressalva de que **teto não é prova**.

Também corrigido: `docs/RELATORIO-VALIDACAO-RECONSTRUCAO.md`, onde o argumento de anterioridade
seguia vivo — *"é cinco anos anterior ao modelo"* escrito como evidência **contra**
contaminação. **É o oposto: anterioridade é a pré-condição da contaminação.** Os logs dos pesos
datam o treino do `Dataset291` em **2023-05-13**, seis anos depois do LCTSC.

## 7. Frases proibidas

1. ❌ *"O LCTSC é conjunto de teste independente."* / *"O LCTSC não está no treino."*
2. ❌ *"Não encontramos overlap, logo é independente."*
3. ❌ *"`pericardium` é uma segunda opinião independente do task `total`."* — **OVERLAP IDENTIFICADO**
4. ❌ *"O SAROS está no treino do 343."* — teto ≲30, sem enriquecimento
5. ❌ *"O SAROS não está no treino do 343."* — teto não é ausência
6. ❌ *"O envelope de intensidade prova dado externo no 343."* — refutado
7. ❌ *"A sonda geométrica não tem poder."* — refutado; poder ≈0,75
8. ❌ *"O treino é de Basel."* — `debug.json` é proveniência de **máquina**
9. ❌ Qualquer uso da sobreposição-zero da Fase 11 como evidência sobre o treino do TS — **erro de categoria**, e o mesmo instrumento tem falso negativo medido (não viu `LUNG1-059` no SAROS)

## 8. Veredito

### K2 — baseline comparável sem leakage conhecido: **BLOQUEADO**

420 de 1.559 imagens (26,9 %) não atribuídas, **e não há lista de casos em disco**. Agravado
por `fold=0` (a opacidade é maior que 26,9 %) e pelo fato de que a saída *"trocar por outro
modelo do próprio TS"* **fechou**: `trunk_cavities` tem overlap identificado com o `total`.

**O que mudou:** o bloqueio deixou de ser ilimitado e ganhou **teto quantificado** — ≲4/60 e
≲4/25, num único canal. **Um teto num canal não é um baseline sem leakage conhecido.**

### K3 — avaliação futura com conjunto independente: **BLOQUEADO**

O iCurveE segue não obtido; o LyNoS segue indeterminado pela mesma raiz; e a fase **removeu
dois candidatos** (SegTHOR, BTCV) por circularidade de rótulo.

**O que mudou:** existe agora um **instrumento falsificável e barato** — a sonda calibrada, com
controles positivo e negativo — que converte INDETERMINADA em OVERLAP IDENTIFICADO com **um
único acerto**. Ele **não** consegue produzir INDEPENDÊNCIA DEMONSTRADA, e **nenhum instrumento
disponível ao projeto consegue**.

**RECOMENDAÇÃO.** Registrar K3 como **bloqueio estrutural**, não pendência de busca. Nenhuma
busca por dataset o fecha enquanto 26,9 % do treino do baseline for cego.

---

```
FASE 16 CONCLUÍDA
K2: BLOQUEADO — 26,9 % do treino não atribuído; sem lista de casos em disco; fold=0 agrava
K3: BLOQUEADO — estrutural, não pendência de busca
OVERLAP IDENTIFICADO: Dataset343 × task total · coorte NSCLC do VRmed × SAROS (folds de treino) · TotalSegmentator dataset
IMPOSSÍVEL DE ESTABELECER: SegTHOR e BTCV no rótulo esophagus — circularidade de anotação, invisível a toda sonda de imagem
DEMONSTRADA: LCTSC × SAROS (só no canal de UID) · Dataset117 (controle)
DEFEITO ATIVO CORRIGIDO: a afirmação refutada da Fase 9 ainda era emitida por máquina em manifest.json e no gerador coorte.py
PRÓXIMO PASSO: aplicar a sonda geométrica calibrada ao LyNoS — é o único candidato vivo de K1/K3 e o instrumento já existe
```
