# VRmed — ontologia anatômica

Data: 2026-09-05 · Estado: **primeira versão**. Antes deste documento o VRmed não tinha
ontologia anatômica nenhuma.

> Documento de **definição**, para uso educacional e experimental. Não é referência clínica
> e não descreve prática assistencial.

## Por que este documento existe

O que passava por ontologia no VRmed era `scripts/geometry/mask_processing.py::classe_de()` —
uma heurística que olha o **nome do arquivo** e devolve `lesao` / `via_aerea` / `vaso` /
`camara` / `orgao`. Isso é classe de **processamento** (decide se aplica `fill_holes`, qual σ
usar). Ela nunca disse **o que entra e o que não entra** numa estrutura.

A Fase 5 mostrou o custo dessa lacuna: mediu-se um Dice de 0,7552 para o coração e de 0,8227
para a medula, e não havia como decidir se aquilo era erro do modelo ou desacordo de
definição — porque **a definição do VRmed nunca tinha sido escrita**.

**Regra que este documento estabelece:** o nome do rótulo **não é** a definição. Toda
estrutura declara o que inclui, o que exclui, e onde termina.

---

## 0. Três vocabulários que não são o mesmo

| | o que é |
|---|---|
| **Estrutura anatômica** | o objeto no corpo, com limites descritos anatomicamente |
| **Rótulo de modelo** | o que uma rede foi treinada a produzir sob um nome |
| **Contorno de radioterapia** | o que um serviço desenha para planejar dose, segundo um atlas |

Os três divergem, e a divergência **não é erro de ninguém**. Um contorno de radioterapia é
desenhado para dosimetria: tende a ser generoso nas bordas e a parar onde o atlas manda, não
onde a anatomia acaba. Confundir os três foi a causa das duas maiores confusões de medição
deste projeto.

---

## 1. As estruturas

Notação: **VRmed** = o que o projeto quer representar · **TS** = rótulo do TotalSegmentator
2.18.0 · **GT** = o que os ground truths disponíveis chamam com esse nome.

### 1.1 `SpinalCord` — medula espinal

| | |
|---|---|
| **TS** | `spinal_cord` (task `total`) |
| **GT LCTSC** | `SpinalCord`, contorno de radioterapia |
| **entra** | medula espinal propriamente dita, dentro do canal vertebral |
| **não entra** | canal vertebral ósseo, raízes nervosas, saco dural, líquor |
| **limite superior** | **VRmed adota: o limite do campo de aquisição.** A medula é contínua e não termina no tórax |
| **limite inferior** | idem |
| **cavidades** | nenhuma |

**A divergência, medida.** O `spinal_cord` do TS preenche o campo de visão em **25 de 30
casos** do development, com mínimo de 0,9078 — ele não termina a medula dentro da aquisição.
O GT do LCTSC ocupa mediana **0,817** do campo, porque o atlas manda o contorno parar.

O falso positivo resultante é **assimétrico**: 4,107 mL na ponta cranial contra 0,240 mL na
caudal (razão 17×). Na ponta caudal a concordância é **imposta pelo campo de visão** —
`erro_distal` mediano de 1,25 mm, com |erro_distal| ≤ 3 mm em 19/30 casos.

**Portanto a divergência é uma única decisão de fronteira cranial, não uma propriedade
global.** Isso é mais estreito do que a Fase 5 afirmou — ver a correção em §4.

**Consequência para o VRmed:** com a definição acima, a extensão do `spinal_cord` até o limite
do campo **não é erro**. Um Dice contra o `SpinalCord` do LCTSC mede concordância com uma
convenção de contorno, não fidelidade anatômica.

### 1.2 `Esophagus` — esôfago

| | |
|---|---|
| **TS** | `esophagus` |
| **GT LCTSC** | `Esophagus`, do nível abaixo do cricoide à junção gastroesofágica (atlas RTOG 1106) |
| **entra** | parede e lúmen esofágicos |
| **não entra** | conteúdo alimentar, gordura periesofágica, traqueia adjacente |
| **limite superior** | **VRmed adota: cricoide**, coincidindo com o atlas |
| **limite inferior** | **junção gastroesofágica**, coincidindo com o atlas |
| **cavidades** | lúmen — o VRmed representa o esôfago **preenchido**, sem lúmen vazado |

**Aqui a definição do VRmed e a do GT coincidem em EXTENSÃO TOTAL**, e a medição confirma:
diferença de comprimento mediana **exatamente 0,000 mm**. Só 0,2119 do erro é extensão.

> **Correção (Fase 7): os dois limites acima NÃO são operacionais.** O pipeline **não localiza
> cricoide nem junção gastroesofágica** — o próprio repositório declara isso em
> `benchmark_tier2.py` e no relatório de reconstrução. Não há uma única medida de onde está
> qualquer um dos dois marcos em nenhum dos 30 casos. O que foi medido é **distância
> predição↔GT**, não predição↔anatomia: `erro_cranial` mediano −3,0 mm (em 18/30 a predição
> para antes do GT) e `erro_distal` +6,0 mm (em 23/30 ela passa). Os dois erros têm sinais
> opostos e se cancelam no comprimento total, o que explica o Δ de 0,000 mm.
>
> Um modelo treinado contra este GT aprenderia **onde o contornador parou**, não onde está o
> cricoide. A definição é operacional para parede, lúmen, gordura e tecido vizinho; **não é**
> para as duas extremidades.

**Parede e lúmen — medido na Fase 7 (n=30):**

O GT é **maciço**: `fill_holes` 2D preencheu **0,0000 mL em 30/30 casos**, 0 fatias com buraco.
E o lúmen com gás está **dentro** do contorno — a fração de HU < −200 é 0,0494 no GT inteiro e
**sobe para 0,0673** no interior erodido, o oposto do que volume parcial de borda produziria.

**A distinção parede/lúmen não é representável nesta grade.** Espessura característica mediana
**9,33 mm**; em Z isso são ~3,5 voxels (dz mediano 2,5 mm), e uma parede de 3–4 mm ocupa
**1,0–1,6 voxel em Z**. Exigir que um modelo a separe é exigir o impossível.

**Adjacência não explica o erro:** só **3,35 %** da superfície do GT está a 1 passo da traqueia
predita e **3,80 %** da aorta (7,29 % e 5,39 % restringindo às fatias onde o vizinho existe).
Válido nos limiares medidos — 1 passo e 2 mm.

**O FN é mais gorduroso que o FP** (fração de gordura 0,1837 contra 0,1087): o que o modelo
deixa de fora é mais gorduroso que o que ele acrescenta.

**Portanto o erro do esôfago não é explicado por definição** — é o candidato legítimo a erro
de modelo. Ver §4 para a ressalva sobre a decomposição.

### 1.3 `Heart` — coração

| | |
|---|---|
| **TS** | `heart` (task `total`) — miocárdio e câmaras, **sem** pericárdio |
| **TS alternativo** | `pericardium` (task `trunk_cavities`, 343) — ver §1.8 |
| **GT LCTSC** | `Heart` do atlas RTOG 1106: *"contoured along with the pericardial sac"*, do nível inferior da artéria pulmonar até o ápice |
| **entra (VRmed)** | miocárdio, câmaras e grandes vasos intrapericárdicos proximais |
| **não entra (VRmed)** | saco pericárdico, gordura pericárdica, mediastino |
| **limite superior** | **VRmed adota: o limite anatômico do miocárdio**, não o corte da artéria pulmonar do atlas |

**O VRmed adota a definição do modelo, não a do atlas.** Um par anatômico coração/pericárdio
é mais útil para estudo do que um bloco único que mistura os dois.

**Consequência direta:** o `Heart` do LCTSC **não é um ground truth válido para o `Heart` do
VRmed.** São estruturas diferentes. O Dice de 0,7552 publicado na coorte compara dois objetos
distintos — e §1.8 mostra que o objeto certo para comparar com esse GT existe e é outro.

### 1.4 e 1.5 `Lung_R` / `Lung_L` — pulmões

| | |
|---|---|
| **TS** | 5 lobos: `lung_upper_lobe_left`, `lung_lower_lobe_left`, `lung_upper_lobe_right`, `lung_middle_lobe_right`, `lung_lower_lobe_right` |
| **GT LCTSC** | `Lung_L`, `Lung_R` — pulmão inteiro, sem lobos |
| **entra (VRmed)** | parênquima pulmonar, **com** a divisão lobar preservada |
| **não entra** | vias aéreas e vasos hilares acima de ~5 mm (o atlas RTOG 1106 os exclui; o TS os inclui se estiverem dentro da fronteira do lobo) |

**A união de lobos apaga as fissuras.** Comparar `Lung_L` do GT com a união dos dois lobos
esquerdos mede a **envoltória pulmonar**, não a lobação. É a comparação disponível, e é
honesta desde que rotulada.

**Não há ground truth de lobo neste dataset.** A lobação do VRmed permanece **sem Tier 2**.

O atlas ainda admite brônquios secundários como **opcionais** — ou seja, o GT é ambíguo no
hilo **por especificação**, e parte da discordância ali não é erro de ninguém.

### 1.6 `Aorta` — aorta torácica

| | |
|---|---|
| **TS** | `aorta` |
| **GT** | **nenhum disponível.** O LCTSC não a anota |
| **entra (VRmed)** | lúmen e parede da aorta torácica: raiz, ascendente, arco, descendente |
| **não entra** | ramos do arco além da origem, aorta abdominal |
| **estado de validação** | **não medido** |

### 1.7 `Trachea` — traqueia

| | |
|---|---|
| **TS** | `trachea` |
| **GT** | **nenhum disponível.** O LCTSC não a anota |
| **entra (VRmed)** | lúmen e parede traqueal, da cricoide à carina |
| **não entra** | brônquios principais além da carina, laringe |
| **estado de validação** | **não medido** |

### 1.8 `Pericardium` — e o achado que reorganiza o tórax

| | |
|---|---|
| **TS** | `pericardium` (task `trunk_cavities`, 343) |
| **GT** | nenhum no LCTSC. O **SAROS** anota `pericardium` (900 TCs, CC BY 4.0) — não usado ainda |
| **estado** | **caracterizado geometricamente, não identificado anatomicamente** |

**O que a classe é, medido em 6 casos do development:**

Ela **não é o saco pericárdico**. É um **sólido preenchido** — razão de preenchimento
**1,0000 em 6/6** (o `fill_holes` 3D e o 2D por fatia não encontram vazio nenhum para
preencher), com meia-espessura mediana de **10,375 mm** e P95 de **29,456 mm**. Um saco
fibroso tem 1–2 mm de espessura. O `heart` entra como controle e também dá sólido, com
meia-espessura de 6,498 mm.

Compatível com: a **região pericárdica preenchida** — o volume que o saco delimita, coração
incluso. Que ela *seja* isso é **hipótese**; o que está medido é a geometria.

**E aqui está o achado.** Contra o GT `Heart` do LCTSC, nos mesmos 6 casos:

| predição | Dice | precision | recall |
|---|---|---|---|
| `heart` sozinho | 0,7709 | 0,8851 | 0,7010 |
| **`pericardium` sozinho** | **0,9056** | 0,8403 | **0,9811** |
| `heart` ∪ `pericardium` | 0,8836 | 0,8029 | 0,9818 |

**O que o LCTSC chama de `Heart` é geometricamente o que este modelo chama de
`pericardium`** — não o que ele chama de `heart`. Acrescentar o `heart` à união só piora a
precision (0,8403 → 0,8029) sem ganhar recall (+0,0007).

Recomputado por mim de forma independente em `LCTSC-Train-S1-005`: `heart` 0,7560 contra
`pericardium` 0,9375. Amplitude do recall de `pericardium` entre as três instituições: 0,0294.

**Ressalva que estava aqui e foi resolvida:** a escolha de `pericardium` foi feita comparando
contra o GT nos mesmos casos do development, então `0,9056` era número de **seleção**. Ele foi
levado ao holdout na Fase 7 e **sobreviveu**.

### Validação independente (Fase 7) — SELEÇÃO × VALIDAÇÃO

A comparação foi **congelada na Fase 6** e medida uma única vez em `validation` (15) e `test`
(15), com diferenças **pareadas por caso**:

| conjunto | | Dice | recall | precision | HD95 | \|erro vol\| |
|---|---|---|---|---|---|---|
| validation | `heart` | 0,7472 | 0,6542 | 0,8787 | 28,24 mm | 23,82 % |
| validation | **`pericardium`** | **0,9093** | **0,9734** | 0,8665 | **14,00 mm** | **13,78 %** |
| test | `heart` | 0,7488 | 0,6628 | 0,8709 | 27,50 mm | 22,34 % |
| test | **`pericardium`** | **0,9089** | **0,9697** | 0,8501 | **10,00 mm** | **12,97 %** |

**15 de 15 casos melhoraram em cada conjunto.** Δ Dice pareado: **+0,1418** (validation) e
**+0,1569** (test). Δ HD95: **−16,99 mm** e **−17,50 mm**. Erro absoluto de volume que não
cancela: **−164,8 mL** e **−146,6 mL**.

**Custo honesto:** a precision cai 0,0136 e 0,0215. É real e fica registrado. Não estava entre
os portões de regressão declarados (Dice, HD95, volume) e não foi acrescentada a eles depois de
ver o resultado.

**Uma leitura que quase enganou:** o Δ de `volume_error_pct` sai **+40,2 pp**, o que pareceria
regressão enorme. É **troca de sinal**: o `heart` subestima (−23,8 %) e o `pericardium`
superestima (+13,8 %). Em módulo o erro **cai** 10 pp. O que decide é o \|erro\| e o erro
absoluto em mL.

> **Estado do mapeamento: `Heart` (GT LCTSC) → `pericardium`, VALIDADO NO HOLDOUT.**
> Seleção na Fase 6 (development, n=6) · validação na Fase 7 (validation + test, n=15+15).

**O que o holdout NÃO estabelece.** Que `pericardium` seja anatomicamente o saco pericárdico.
Ele mostra que ela representa melhor **o objeto que o LCTSC contorna como `Heart`** — um
contorno de radioterapia que inclui saco e gordura.

### Identidade anatômica (Fase 8, contra o SAROS)

> **"Saco pericárdico" está REFUTADO.** Compatível com **região pericárdica preenchida**.
> Independência da referência **indeterminada**.

| | GT SAROS | predição TS | saco fibroso sintético de 2 mm |
|---|---|---|---|
| razão de preenchimento 2D | **1,0000** (14/14) | **1,0000** (14/14) | **0,0724** |
| meia-espessura mediana | **14,32 mm** | 14,54 mm | **0,730 mm** |

**A refutação não depende da predição.** O `pericardium` do GT do SAROS — humano-revisado — é
ele mesmo um **sólido preenchido**, e a mesma função classifica um saco sintético de 2 mm como
casca. Recomputado de forma independente em 5 casos adicionais: preenchimento 1,0000 exato.

O paper do SAROS descreve `pericardium` como rótulo de **região corporal**, ao lado das
cavidades e do mediastino — não como o saco. **Isso limita por definição o que se pode
afirmar**, venha o Dice que vier.

Correspondência medida (14 casos, restrita às fatias anotadas — o SAROS anota ~21 % das fatias
e marca o resto como *ignore*): Dice **0,9657**, composição **0,9719** de um único rótulo,
melhor alvo em 14/14 contra `mediastinum` (0,0190) e `thoracic_cavity` (0,0007).

**Ressalva que não pode sair do lado desse número.** O dataset de treino da tarefa 343 é
`Dataset343_mediastinum_1786subj`, com rótulos **idênticos** aos do SAROS e campos de
proveniência em branco (`reference: "Jakob"`, `licence: "-"`). São 1786 sujeitos contra os 900
do SAROS — não é *só* SAROS, mas o SAROS pode estar contido. **Um Dice de 0,9657 é compatível
com memorização.**

**A diferença que resta tem endereço:** o extremo superior, sobre a raiz dos grandes vasos. O
SAROS os mantém dentro do `pericardium`; a predição os chama de `mediastinum`.

Detalhes em [`RELATORIO-FASE8-SAROS-PERICARDIO.md`](RELATORIO-FASE8-SAROS-PERICARDIO.md).

---

## 2. Matriz de correspondência

| VRmed | rótulo TS | GT LCTSC corresponde? | evidência |
|---|---|---|---|
| SpinalCord | `spinal_cord` | **parcialmente** — mesma estrutura, limite cranial diferente | FP 17× maior na ponta cranial |
| Esophagus | `esophagus` | **sim** | Δ comprimento mediano 0,000 mm |
| Heart | `heart` | **não** — o GT inclui pericárdio | Dice 0,7709 contra 0,9056 do `pericardium` |
| Pericardium | `pericardium` | o GT `Heart` é o melhor proxy disponível | Dice 0,9056 · recall 0,9811 |
| Lung_R / Lung_L | união de lobos | **envoltória sim, lobação não** | união apaga fissuras |
| Aorta | `aorta` | **não existe GT** | LCTSC não anota |
| Trachea | `trachea` | **não existe GT** | LCTSC não anota |

---

## 3. Consequência para a avaliação

A Fase 5 concluiu que "o gargalo é A, o bloco de segmentação". Este documento estreita isso:

**O coração nunca foi um problema de segmentação.** Era um problema de correspondência de
rótulo. O objeto que o GT contorna existe na saída do modelo, sob outro nome, em outra tarefa.

**A medula é uma decisão de fronteira cranial**, e o VRmed já a tomou: o limite é o campo de
aquisição. Sob essa definição, boa parte do "erro" deixa de ser erro — mas ver §4.

**O esôfago é o único dos três em que a definição do VRmed e a do GT coincidem.** É por isso
que ele continua sendo o candidato a erro de modelo.

---

## 4. Correções ao que já foi publicado

Duas afirmações anteriores não sobrevivem à revisão e ficam registradas aqui, não apagadas.

**(a) A medula — o argumento da "amplitude zero" era inválido.** A Fase 5 afirmou que
`frac_campo_pred` tem amplitude 0,0000 entre instituições enquanto `frac_campo_gt` varia 0,27,
e leu isso como prova de que o modelo é invariante e só o contorno varia.

`frac_campo_pred` é uma variável **saturada no teto**: 25 de 30 casos valem exatamente 1,0 e o
mínimo é 0,9078 — a dispersão real é 0,0922, não zero. Amplitude zero **entre medianas** de
uma variável presa no máximo é aritmética, não concordância, e compará-la com a amplitude de
uma variável não saturada não é comparação válida.

O que sobrevive: a predição de fato preenche o campo em 25/30 casos, e o FP é 17× maior na
ponta cranial. O que **não** sobrevive: que a saturação prove invariância do modelo entre
instituições. Separar definição de erro na medula exigiria uma referência anatômica
independente, que este dataset não tem.

**(b) O coração — `precision 0,9825` é circular.** Esse número vem da variante `A_suporte_gt`,
que **recorta a predição no suporte em Z do GT** antes de medir. O recall é idêntico nas duas
variantes (0,6719) e só a precision muda. No campo completo a precision mediana é **0,8740**,
com 28 de 30 casos abaixo de 0,90 e 12,6 % da predição de `heart` caindo fora do GT.

"O GT é um superconjunto" continua sustentado — mas por `pericardium` (§1.8), não pela
precision da variante A.

---

## 5. O que esta ontologia ainda não resolve

- **`pericardium` está caracterizado, não identificado.** Falta uma referência anatômica
  independente. O SAROS anota a classe em 900 TCs sob CC BY 4.0 e não foi usado — é o
  caminho, e o impedimento é de esforço, não de impossibilidade.
- **Aorta e traqueia continuam sem qualquer validação.**
- **A lobação pulmonar continua sem ground truth.**
- **A escolha de `pericardium` precisa de confirmação em dado retido.**
