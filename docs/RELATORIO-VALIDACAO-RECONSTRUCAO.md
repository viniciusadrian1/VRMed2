# VRmed — Relatório de validação da reconstrução

Data: 2026-09-04 · Escopo: **somente reconstrução de superfície** (máscara → malha).
Nada aqui trata de Niivue, AR, WebXR, patologia ou features de produto.

> **Natureza deste documento.** É um relatório de **engenharia geométrica**: mede erro de
> volume, de área, de distância e de topologia entre representações digitais. Não é
> validação clínica, não é avaliação de acurácia diagnóstica e nenhum número abaixo
> autoriza uso assistencial. Uso do VRmed continua **educacional e experimental**.

---

## 0. Definição dos tiers (vale para todo o relatório)

| Tier | O que mede | Referência | Estado neste repositório |
|---|---|---|---|
| **Tier 1** | **Fidelidade da reconstrução à máscara.** Quanto a malha se afasta da máscara binária que a gerou. | A própria máscara de entrada (voxels × spacing) | **Presente** — 7 estruturas reais |
| **Tier 2** | **Acurácia da segmentação contra ground truth independente.** Quanto a máscara se afasta de uma anotação externa. | Dataset rotulado por terceiros | **PRESENTE desde a §9** — LCTSC/TCIA, 5 estruturas, **1 caso**. Era ausente quando as §§1–7 foram escritas, e elas continuam valendo assim |
| **Tier 3** | **Validação contra fantoma analítico.** Volume e área têm fórmula fechada, então o erro medido é erro **real**. | Fórmula (esfera π/6·d³, cilindro π/4·d²·h) | **Presente** — 14 alvos sintéticos |

Três consequências que atravessam tudo:

1. **Um Dice alto no Tier 1 não diz que a geometria está certa.** Diz que a malha é fiel
   à máscara. Máscara errada + reconstrução perfeita = Dice ~1,0 no Tier 1.
2. **Nenhum número das §§1–8 estima Tier 2.** Nada nelas pode ser lido como "a segmentação
   acertou X%". O Tier 2 está na **§9**, e nunca se soma aos outros tiers.
3. **Só o Tier 3 mede erro absoluto.** É onde as decisões de configuração foram tomadas.

---

## 1. Cobertura efetiva do benchmark

21 alvos × 4 variantes = **84 linhas**. Agregação por **mediana** dentro de
(tier, faixa de calibre, variante). Cada erro na sua coluna — nada somado em nota única.

Faixa é de **calibre** (espessura característica), não de volume. No Tier 3 é o diâmetro
nominal do fantoma; no Tier 1 é `2 × mediana(EDT amostrada no esqueleto)` — aproximação
para agrupar, não medida de precisão.

| Faixa de calibre | Tier 3 (fantoma) | Tier 1 (estrutura real) |
|---|---|---|
| **< 3 mm** | 2 alvos (tubo 2 mm, iso + aniso) | **0 alvos** |
| **3–10 mm** | 4 alvos (tubos 5 e 8 mm) | 4 alvos (5,60 · 7,99 · 8,11 · 9,18 mm) |
| **10–30 mm** | 4 alvos (esfera e tubo 20 mm) | 3 alvos (11,52 · 20,28 · 23,18 mm) |
| **> 30 mm** | 4 alvos (cilindro e esfera 40 mm) | **0 alvos** |

**Lacunas declaradas.** As faixas extremas do Tier 1 estão vazias: a estrutura real mais
fina medida tem **5,60 mm** de calibre e a mais grossa, **23,18 mm**. Portanto as
conclusões para `< 3 mm` e `> 30 mm` apoiam-se **exclusivamente no Tier 3**. Isso não as
invalida (o Tier 3 é a única fonte de erro absoluto), mas significa que não há confirmação
em dado real nessas duas faixas.

**Força estatística.** n = 2 a 4 alvos por célula, mediana, sem intervalo de confiança.
O que se afirma abaixo como "comprovado" é **consistência direcional em todas as faixas**,
não significância estatística. Onde a margem é pequena o suficiente para caber no ruído de
4 amostras, o item está na seção 4 (inconclusivo), não na 2.

**Variantes comparadas.** `sigma_auto` (baseline histórico, σ = 0,25 × menor voxel),
`sigma_zero` (σ = 0), `sigma_meio` (σ = 0,5 × o automático) e `surface_nets` — este
último marcado `*` em todas as tabelas: é **candidato experimental**, nunca baseline.
Método oficial de baseline em todas as comparações: **marching cubes**.

---

## 2. O que melhorou comprovadamente

### 2.1 σ = 0 reduz o erro de volume em **todas** as quatro faixas de calibre

Tier 3 — erro de volume contra a verdade analítica (mediana):

| Faixa | `sigma_auto` (baseline) | **`sigma_zero`** | `sigma_meio` | `surface_nets *` |
|---|---|---|---|---|
| < 3 mm | −89,99 % | **−28,24 %** | −33,27 % | −76,30 % |
| 3–10 mm | −8,79 % | **−3,57 %** | −4,11 % | −19,83 % |
| 10–30 mm | −1,40 % | **−0,55 %** | −0,64 % | −3,49 % |
| > 30 mm | −0,40 % | **−0,13 %** | −0,16 % | −1,17 % |

`sigma_zero` vence em **4 de 4 faixas**, sem exceção e sem regressão. Este é exatamente o
critério §16 (vencer em **cada** faixa, não na média) — e é o único item deste relatório
que o satisfaz de forma integral.

Confirmação no Tier 1 (mesma direção, dado real):

| Faixa (Tier 1) | `sigma_auto` | **`sigma_zero`** |
|---|---|---|
| 3–10 mm | −2,27 % | **−0,70 %** |
| 10–30 mm | −0,32 % | **−0,07 %** |

A ablação isolada da gaussiana, alvo a alvo, mostra o mesmo em números absolutos:

| alvo | com gaussiana | sem gaussiana |
|---|---|---|
| tubo 2 mm (fantoma) | −69,79 % | **−5,20 %** |
| tubo 3 mm (fantoma) | −23,19 % | **−1,84 %** |
| esophagus | −1,53 % | **−0,31 %** |
| trachea | −0,87 % | **−0,17 %** |
| heart | −0,12 % | **−0,03 %** |
| lung_upper_lobe_left | −0,050 % | **−0,012 %** |

Seis alvos, seis vitórias de σ = 0, em três ordens de grandeza de calibre.

### 2.2 Taubin (4 iterações) é ganho consistente e praticamente gratuito

Ablação isolada, mesma reconstrução, só o número de iterações muda:

| alvo | volume `com_taubin_4` | volume `sem_taubin` | área `com` (mm²) | área `sem` (mm²) |
|---|---|---|---|---|
| heart | **−0,124 %** | −0,128 % | **54 436** | 54 655 |
| lung_upper_lobe_left | **−0,050 %** | −0,052 % | **90 589** | 90 979 |
| trachea | **−0,873 %** | −0,903 % | **10 195** | 10 218 |
| esophagus | **−1,532 %** | −1,567 % | **11 924** | 11 963 |
| tubo 2 mm | **−69,79 %** | −70,22 % | 93,5 | 91,6 |
| tubo 3 mm | **−23,19 %** | −23,37 % | 241,0 | 240,6 |

Seis de seis com erro de volume **menor** com Taubin, e área menor (menos escada) em
quatro de seis. Contagem de triângulos idêntica, custo de tempo desprezível. Ao contrário
da gaussiana, o Taubin opera na **malha**, não na máscara binária — não apaga estrutura
fina: no tubo de 2 mm ele **melhora** o volume (−69,79 % contra −70,22 %).
**Manter Taubin = 4.**

### 2.3 O `fill_holes` condicionado por classe evita fabricação de volume

Fantoma de casca esférica 20/10 mm, cavidade interna com resposta analítica conhecida:

| variante | volume fabricado | Δ volume da máscara | componentes na malha |
|---|---|---|---|
| `com_fill_holes` | **+521,1 mm³** | **+14,26 %** | 1 (cavidade destruída) |
| `sem_fill_holes` | 0,0 mm³ | 0,00 % | **2 (cavidade preservada)** |

Nas estruturas reais testadas (`heart`, `trachea`) o `fill_holes` foi **no-op**: 0,0 mm³
fechados, nenhum buraco interno detectado. Ou seja, a guarda por classe **não custa nada**
no dado real e impede uma fabricação de 14 % de volume no caso em que existe cavidade.

Ressalva de medição: na variante `sem_fill_holes` da casca, o `volume_error_pct` sai
**+26,46 %** — isso é artefato de medir volume com `trimesh` em malha de duas cascas
aninhadas (o corpo interno entra com sinal invertido), não ganho de volume. O critério
válido nessa linha é **contagem de componentes**, não volume.

### 2.4 O critério para decimar calibre fino é **volume**, não distância

Ablação de decimação, alvo a 10 % dos triângulos:

| alvo | calibre | erro de volume | Hausdorff |
|---|---|---|---|
| tubo 2 mm | < 3 mm | **−29,08 %** | 0,47 mm |
| tubo 5 mm | 3–10 mm | −5,95 % | 0,54 mm |
| esophagus | 3–10 mm | −0,32 % | 0,96 mm |
| trachea | 10–30 mm | −0,12 % | 0,82 mm |
| aorta | > 30 mm | −0,00 % | 1,04 mm |
| heart | > 30 mm | +0,01 % | **1,11 mm** |

O Hausdorff é **maior** justamente onde o dano relativo é **menor**. O erro absoluto em mm
é limitado pelo raio da estrutura: em calibre fino um deslocamento pequeno em milímetros
já é fração enorme da espessura. Usar Hausdorff como critério de aceitação de decimação
esconde exatamente a regressão que importa.

### 2.5 Fusão de componentes é dano silencioso — só `n_componentes` detecta

`heart` na ablação de decimação: 3 componentes → **2** a 10 % dos triângulos → **1** no
piso de 3000 tris, com erro de volume de apenas **−0,35 %**. Nenhuma métrica de volume,
área, ASSD ou RMS registra a perda. A verificação de componentes antes/depois passa a ser
obrigatória em qualquer operação destrutiva.

### 2.6 Duas correções de instrumentação (o teste encontrou bug no próprio teste)

- **Fantoma não-monotônico:** `_grade` alternava `n` par/ímpar conforme o diâmetro,
  deslocando meio voxel a rede de amostragem — d = 2,0 mm produzia máscara **menor** que
  d = 1,5 mm. Corrigido com supersampling 3³ + `n` forçado a ímpar. Um fantoma que não
  cresce com o diâmetro não detecta regressão nenhuma; todos os números Tier 3 acima são
  pós-correção.
- **Isosuperfície vazia:** `flying_edges` e `surface_nets` estouravam exceção quando a
  estrutura não sobrevivia à suavização. Agora devolvem `None` = "ausente", e a linha
  entra no benchmark como estrutura não preservada em vez de derrubar a execução.

---

## 3. O que piorou comprovadamente

### 3.1 A gaussiana na máscara destrói calibre fino

`sigma_auto` na faixa < 3 mm (Tier 3): **−89,99 % de volume**, **−65,96 % de área**, e
Dice de reconstrução **0,3268** contra a máscara. Isto é, a variante que hoje é default
apaga aproximadamente nove décimos do volume de um tubo de 2 mm. Na faixa 3–10 mm o custo
ainda é de −8,79 % contra −3,57 % de σ = 0.

A causa é conhecida e específica: a gaussiana é aplicada sobre a **ocupação binária** antes
do marching cubes. Em estrutura de poucos voxels de seção, borrar antes de cortar em
`level = 0.5` remove o material que definiria a superfície.

### 3.2 Surface Nets perde em todos os critérios e em todas as faixas

Tier 3, erro contra verdade analítica:

| Faixa | volume `sigma_zero` | volume `surface_nets *` | área `sigma_zero` | área `surface_nets *` |
|---|---|---|---|---|
| < 3 mm | −28,24 % | **−76,30 %** | −10,41 % | **−53,45 %** |
| 3–10 mm | −3,57 % | **−19,83 %** | +0,30 % | **−14,46 %** |
| 10–30 mm | −0,55 % | **−3,49 %** | +3,80 % | −3,85 % |
| > 30 mm | −0,13 % | **−1,17 %** | +3,41 % | −1,63 % |

Tier 1, dado real:

| Faixa | Dice | ASSD (mm) | HD95 (mm) | erro vol. | **watertight** |
|---|---|---|---|---|---|
| 3–10 mm · `marching_cubes` | 1,0000 | 0,000 | 0,00 | −0,70 % | **4/4** |
| 3–10 mm · `surface_nets *` | 0,9360 | 0,298 | 0,93 | −11,29 % | **1/4** |
| 10–30 mm · `marching_cubes` | 1,0000 | 0,000 | 0,00 | −0,07 % | **3/3** |
| 10–30 mm · `surface_nets *` | 0,9803 | 0,188 | 0,68 | −1,01 % | **1/3** |

Avaliação nos seis critérios exigidos: **perde em volume** (4/4 faixas), **perde em área**
(4/4), **perde em ASSD** (2/2 faixas Tier 1), **perde em HD95** (2/2), **perde em Dice**
(2/2) e **quebra estanqueidade** (de 7/7 malhas watertight para 2/7). Sua única vantagem
medida é tempo (0,32 s contra 0,42 s na faixa 10–30 mm) — irrelevante num pipeline offline.

**A recomendação da pesquisa de adotar Surface Nets foi falseada pelo experimento.**
Permanece disponível atrás de flag, como candidato experimental, **nunca como default**.

### 3.3 Decimação percentual agressiva destrói calibre fino

| variante | tubo 2 mm | tubo 5 mm | esophagus | trachea | aorta | heart |
|---|---|---|---|---|---|---|
| 70 % | −1,91 % | −0,36 % | −0,05 % | −0,04 % | −0,01 % | −0,01 % |
| 50 % | −3,84 % | −0,75 % | −0,07 % | −0,06 % | −0,02 % | −0,01 % |
| 30 % | −5,23 % | −1,71 % | −0,11 % | −0,05 % | −0,01 % | −0,00 % |
| **10 %** | **−29,08 %** | **−5,95 %** | −0,32 % | −0,12 % | −0,00 % | +0,01 % |

Alvo **percentual** é a operação errada para estrutura fina: 10 % dos triângulos de um
tubo de 2 mm são 140 triângulos, o que não descreve mais um cilindro.

### 3.4 O piso de 3000 triângulos não protege o fino — e mutila o grosso

| alvo | tris antes → depois | redução | Hausdorff | Δ área | componentes |
|---|---|---|---|---|---|
| tubo 2 mm | 1400 → 1400 | **0,00 %** | 0,25 mm | 0,00 % | 1 → 1 |
| trachea | 36 828 → 3000 | 91,85 % | 1,10 mm | −0,27 % | 1 → 1 |
| aorta | 135 908 → 3000 | 97,79 % | 1,90 mm | −3,08 % | 1 → 1 |
| **heart** | 226 476 → 3000 | **98,68 %** | **13,47 mm** | −3,81 % | **3 → 1** |

O piso é **no-op** no alvo que deveria proteger (o tubo fino já tem menos de 3000
triângulos) e é destrutivo justamente nas estruturas grandes. Quem destrói o fino é o
**alvo percentual**, aplicado antes do piso.

### 3.5 Decimação abre a malha

Praticamente todas as MASTERs entram watertight e saem **não-watertight** já em 30–50 %
de redução — `fast_simplification` abre borda. `trachea` já sai aberta a **70 %**. Os
fantomas de tubo sobrevivem watertight em todos os níveis (geometria simples). Consequência
prática: **`volume_ml` calculado em derivado decimado é inválido**; volume só vale na
MASTER.

### 3.6 O afastamento de contato fabrica volume

`pulmonary_vein` + `heart`, ablação isolada: `com_encostar` inventa **0,219 mL = +1,116 %**
de volume que não existe na máscara. É pequeno, mas é fabricação — e não pertence a uma
malha que se pretende referência de fidelidade.

---

## 4. Resultado inconclusivo

### 4.1 Volume e área discordam em calibre grande

| Faixa (Tier 3) | erro de volume | erro de área |
|---|---|---|
| 10–30 mm | `sigma_zero` **−0,55 %** vs `sigma_auto` −1,40 % | `sigma_auto` **−0,44 %** vs `sigma_zero` +3,80 % |
| > 30 mm | `sigma_zero` **−0,13 %** vs `sigma_auto` −0,40 % | `sigma_auto` **+0,19 %** vs `sigma_zero` +3,41 % |

σ = 0 vence em volume; σ automático vence em área. A área de σ = 0 vem inflada porque a
malha reproduz a escada de voxel. Em magnitude absoluta a vantagem de área do σ automático
(≈ 3,3 pontos percentuais) é maior que sua desvantagem de volume (0,27 a 0,85 pp).
**Sem um critério declarado de qual erro pesa mais, não há vencedor único nestas duas
faixas.** A seção 6 declara esse critério explicitamente e por isso consegue decidir; o que
fica inconclusivo é a comparação em si.

### 4.2 Dice, ASSD e HD95 são degenerados no Tier 1 para σ = 0

`sigma_zero` produz `dice = 1,0000 · assd = 0,000 mm · hd95 = 0,00 mm` em **todas** as
linhas Tier 1. Não é excelência: sem suavização, a malha rasterizada de volta reproduz a
máscara **por construção**. As três métricas não têm poder de discriminação para essa
variante. No Tier 1 só `volume_error`, `area_error`, `watertight` e contagem de componentes
discriminam. Foi por isso que a decisão de σ repousou no Tier 3.

### 4.3 `sigma_meio` contra `sigma_zero` em calibre grande

| Faixa | `sigma_zero` | `sigma_meio` | margem |
|---|---|---|---|
| < 3 mm | −28,24 % | −33,27 % | 5,03 pp (conclusivo) |
| 3–10 mm | −3,57 % | −4,11 % | 0,54 pp (conclusivo) |
| 10–30 mm | −0,55 % | −0,64 % | **0,09 pp** |
| > 30 mm | −0,13 % | −0,16 % | **0,03 pp** |

Nas duas faixas grossas a margem cabe no ruído de 4 fantomas. `sigma_zero` é escolhido
nessas faixas por **consistência de direção**, não por diferença demonstrada.

### 4.4 Topologia não discriminou neste conjunto

Todas as 84 linhas do benchmark de σ saíram com `delta_componentes = 0` e
`fracao_maior_componente = 1,0000`. A métrica foi exercitada e não encontrou sinal nestes
7 alvos reais e 14 fantomas. Fragmentação por reconstrução **não foi observada** — o que
não é o mesmo que demonstrar que não ocorre. O único lugar onde topologia mudou foi a
**decimação** (item 2.5), não a reconstrução.

### 4.5 Continuidade de vasos e lúmens

Todos os fantomas tubulares saíram com 1 componente e `frac_maior = 1,0000` em todas as
variantes, inclusive `sigma_auto` no tubo de 2 mm — que perdeu 90 % do volume **sem
fragmentar**. Ou seja: a continuidade sobreviveu, o calibre não. **Continuidade sozinha não
é critério de preservação de estrutura fina**; precisa vir acompanhada de erro de volume.
Nenhum caso de descontinuidade foi produzido neste conjunto, então o poder do teste é
desconhecido.

### 4.6 Preservação de estrutura pequena: `preservada` não separou variantes

`estrutura_preservada` saiu positivo em 21/21 alvos nas 4 variantes. Nenhuma estrutura
desapareceu por completo neste conjunto — o desaparecimento total só apareceu em execuções
anteriores com tubo de 1,0 mm, abaixo do teto físico de discretização. Para os alvos aqui,
o dano se manifesta como **encolhimento**, não como ausência.

### 4.7 As lacunas de cobertura do Tier 1

`< 3 mm` e `> 30 mm` não têm estrutura real. As conclusões nessas faixas são **Tier 3 puro**.

---

## 5. Hipótese futura (não medido)

1. **Suavização no domínio da malha em vez da máscara.** O Taubin já demonstrou reduzir
   área sem custar volume (item 2.2). A hipótese é que aumentar iterações de Taubin, ou
   usar `vtkWindowedSincPolyDataFilter`, elimine a escada de voxel que hoje infla a área do
   σ = 0 (+3,4 a +3,8 pp) **sem** reintroduzir a perda de volume da gaussiana. É a única
   rota identificada para ganhar nas duas métricas ao mesmo tempo. **Não testada.**
2. **σ condicionado por calibre, não por classe.** O σ por classe hoje implementado é
   heurístico (nome da estrutura → classe → σ). Os dados sugerem que a variável causal é o
   **calibre**, não a classe: `esophagus` (8,1 mm) e `aorta` (20,3 mm) reagem à gaussiana em
   ordens de grandeza diferentes apesar de classes distintas. `espessura.py` já mede
   calibre; condicionar σ a ele é testável. **Não testado.**
3. **Decimação com orçamento por calibre.** O dado mostra que alvo percentual global é o
   que destrói o fino (item 3.3) e que o piso fixo não protege (item 3.4). Um orçamento
   derivado da espessura da estrutura, com verificação obrigatória de componentes,
   é a substituição natural. **Não testado.**
4. **Reamostragem antes da reconstrução.** Abaixo de ~1,5 voxel de seção a estrutura não
   existe nem na máscara — nenhum extrator recupera. Supersampling ou reamostragem da
   máscara antes do marching cubes é a única rota, e é cara. **Não testada.**
5. **Referência de área verdadeira no Tier 1.** Hoje a área de referência do Tier 1 é
   **proxy** (a malha σ = 0, Taubin = 0). Não existe área verdadeira para uma máscara de
   voxel. `area_error_%` do Tier 1 deve ser lido como "quanto esta variante encolhe a
   superfície em relação à malha mais aderente", nunca como erro absoluto.
6. **Tier 2 exige dataset externo anotado.** Enquanto não houver, a acurácia da segmentação
   permanece **não medida** — e nenhuma métrica deste relatório a substitui.

---

## 6. Recomendação objetiva de configuração

**Critério declarado.** Para a MASTER, o erro que pesa é o de **volume**: é a grandeza que
tem verdade analítica no Tier 3, é a que degrada monotonicamente com o calibre e é a única
em que uma variante venceu em todas as quatro faixas. Área é critério **secundário** porque
sua parcela dominante em σ = 0 é escada de voxel — um artefato de representação removível a
jusante, não perda de material. Aparência não entra em nenhum dos dois.

### MASTER

```
--reconstrucao marching_cubes
sigma_mm      = 0.0        # sem gaussiana na máscara, em toda faixa de calibre
taubin        = 4
level         = 0.5
fill_holes    = por classe (pular onde a cavidade é real)
afastamento   = 0.0 mm     # nenhum
decimação     = nenhuma
```

Justificativa por item:

| Decisão | Evidência | Tier |
|---|---|---|
| `marching_cubes` | vence Surface Nets em volume, área, Dice, ASSD, HD95 e watertight, em 4/4 faixas (§3.2) | 3 + 1 |
| `sigma = 0.0` | menor erro de volume em 4/4 faixas, sem regressão (§2.1) | 3 |
| `taubin = 4` | menor erro de volume em 6/6 alvos, área menor em 4/6, custo nulo (§2.2) | 3 + 1 |
| `fill_holes` por classe | evita fabricar +14,26 % de volume; no-op no dado real (§2.3) | 3 |
| sem afastamento | fabrica +1,116 % de volume (§3.6) | 1 |
| sem decimação | abre a malha a partir de 30–50 %, invalidando `volume_ml` (§3.5) | 1 |

**Mudança de default proposta:** apenas `sigma_auto → sigma_zero`. Todo o resto já é o
comportamento atual. A mudança satisfaz o critério §16 (vencer em cada faixa) e é a única
do conjunto testado que o satisfaz.

### DERIVADOS (web / Quest / AR)

```
origem        = MASTER (decimação apenas — nunca reconstruir de novo)
decimação     = alvo percentual APENAS para calibre > 10 mm
                calibre 3–10 mm: não passar de 50 %
                calibre < 10 mm: sem piso fixo, orçamento absoluto
verificação   = n_componentes antes/depois obrigatório; abortar se fundiu
volume_ml     = NÃO publicar (malha decimada não é watertight)
```

Justificativa:

- **Reconstruir o derivado com σ automático seria trocar a fidelidade da geometria por
  aparência de superfície** — reintroduziria −8,79 % de volume em 3–10 mm (§2.1) para
  ganhar ≈ 3,3 pp de área em calibre grande (§4.1). O guardrail é explícito: aparência não
  promove default. Derivado sai da MASTER, sempre.
- **A escada de voxel do σ = 0, se incomodar visualmente, se resolve no domínio da malha**
  (mais Taubin), não voltando a gaussiana para a máscara — e isso é hipótese a testar
  (§5.1), não recomendação.
- **Sem piso de 3000 triângulos.** Ele não protege o fino e degrada o grosso: `heart` a
  13,47 mm de Hausdorff e 3 componentes → 1 (§3.4).
- **`volume_ml` não deve ser publicado a partir de derivado.** A decimação abre a malha
  (§3.5) e volume só vale em malha estanque.

### O que NÃO muda

- **Marching cubes continua o baseline oficial.** Nenhuma alternativa testada o superou.
- **Surface Nets continua atrás de flag, como candidato experimental.** Falhou nos seis
  critérios de confirmação.
- **A MASTER não foi alterada por este relatório.** A mudança de default de σ está
  *recomendada com evidência*, não aplicada — aplicação depende de decisão explícita.

---

## 7. Reprodutibilidade

```bash
python scripts/validation/benchmark_sigma.py     # 84 linhas → .clinica-dados/benchmark-sigma/
python scripts/validation/ablation.py            # 5 ablações → .clinica-dados/ablation/
python scripts/validation/espessura.py           # calibre por estrutura
python scripts/validation/phantom.py             # autoteste dos fantomas
```

Saídas versionadas em `.clinica-dados/` (fora do Git, por conter dado derivado de exame).
Ambiente fixado em `requirements-lock.txt`. Toda medição roda em malha **pré-Draco**: o
`trimesh` não decodifica Draco e lê zeros — medir o asset publicado dá número falso.

---

## 8. Suavização no domínio da malha

Data: 2026-09-04 · Escopo: **só o filtro aplicado depois da extração**. Extrator e
borramento ficam fixos (`marching_cubes` + `sigma_mm = 0.0`) em todas as variantes; a única
coisa que varia é o filtro de malha.

A hipótese da §5.1 era: suavizar **depois** da reconstrução reduziria a escada de voxel do
σ = 0 sem reintroduzir a perda de volume que a gaussiana na máscara causa. Esta seção a
testa. Os tiers são os da §0 e não mudam.

### 8.0 Variantes e parâmetros (todos declarados, nenhum ajustado por resultado)

| variante | parâmetros |
|---|---|
| `V0_taubin4` | marching_cubes, σ=0, `filter_taubin(lamb=0.5, nu=0.53)`, 4 iterações — **baseline congelado**, é o default vigente |
| `V1_taubin8` | idem, 8 iterações |
| `V2_taubin12` | idem, 12 iterações |
| `V3_taubin20` | idem, 20 iterações |
| `V4_wsinc` | `vtkWindowedSincPolyDataFilter`, `iterations=20`, `pass_band=0.1`, `NormalizeCoordinatesOn`, `FeatureEdgeSmoothingOff`, `BoundarySmoothingOff`, `NonManifoldSmoothingOn` |

Os valores 20/0,1 do WindowedSinc são os da documentação do VTK e são os mesmos que o ramo
`flying_edges` já usava desde a Fase 1. Foram fixados **antes** de qualquer medição.

23 alvos × 5 variantes = 115 linhas (80 Tier 3, 35 Tier 1) em
`.clinica-dados/benchmark-smoothing/`, mais 8 fantomas de topologia × 5 variantes = 40 linhas
em `.clinica-dados/benchmark-topologia/`. Limiar de relevância declarado: **1 ponto
percentual** no módulo do erro mediano da faixa.

**O default do pipeline não foi alterado.** `reconstruct_surface` ganhou o parâmetro
`mesh_smoothing`, com default `"taubin"` que reproduz o comportamento anterior — verificado
bit a bit: 8 combinações (2 fantomas × 4 métodos) devolvem vértices idênticos e nenhum
`params` existente muda de valor.

### 8.1 O primeiro resultado foi um artefato do instrumento — e isso é o achado principal

A primeira execução reprovou **as quatro** variantes numa única porta: "degradou estrutura
fina", medida pelo erro de dimensão na faixa `< 3 mm`. A refutação adversarial derrubou esse
veredito, e a checagem independente confirmou.

A dimensão dos alvos tubulares estava sendo medida por **bounding box em x/y** — uma
estatística de **máximo** sobre os vértices extremos da escada do marching cubes. Ela mede o
quanto o filtro raspa a ponta da escada, não o calibre da estrutura. Varredura de
`taubin_iters` de 1 em 1 no tubo de 2 mm (spacing 0,7 × 0,7 × 1,25 mm):

| taubin | bbox_xy erro % | volume erro % | calibre mediano erro % |
|---|---|---|---|
| 0 | **+5,000** | −27,755 | −21,738 |
| 1 | −6,667 | **−34,146** | −21,738 |
| 2 | +1,989 | −27,444 | −19,889 |
| 3 | −7,906 | **−33,913** | −20,865 |
| **4** | **−0,182** | −27,089 | −18,570 |
| 6 | −1,447 | −26,756 | −17,601 |
| 8 | −2,317 | −26,460 | −16,864 |
| 12 | −3,465 | −25,983 | −15,804 |
| 20 | −4,904 | −25,343 | −14,465 |

Três defeitos, todos verificados:

1. **A bbox anda no sentido oposto ao volume.** Ela diz que o tubo afinou 4,9 % enquanto o
   volume subiu 1,7 pp. Calibre e volume de um tubo são a mesma grandeza vista de dois modos
   (V ∝ d²·h) — quando discordam de sinal, o estimador está medindo outra coisa.
2. **O baseline congelado pousou no mínimo global acidental.** O `−0,182 %` do `taubin=4` é
   um **cruzamento de zero** entre o viés de meio voxel do marching cubes (`+5,000 %` em
   `taubin=0`, exatamente 3 voxels × 0,7 mm = 2,1000 mm) e o encolhimento progressivo. A
   porta comparava `|erro|` contra esse ponto com limiar de 1 pp, então **nenhuma outra
   contagem de iterações podia passar** — aplicada a `taubin=0`, isto é, à malha **sem filtro
   nenhum**, a mesma porta também reprova. Um critério que veta "não fazer nada" como
   degradação de estrutura fina não é evidência contra as variantes.
3. **O volume oscila por paridade.** Com `lamb=0,5 / nu=0,53`, contagens **ímpares** contraem
   ~7 pp a mais que as pares. O benchmark só amostrou 4/8/12/20 — todas pares. Toda afirmação
   de monotonicidade descrevia a subsequência par, não o filtro.

**Correção aplicada:** `medir_dimensao` passou a usar `calibre_mediano_mm` — 2 × **mediana**
do raio dos vértices numa faixa central, robusta a vértice extremo e cega para as tampas. A
bbox continua gravada em `dimensao_bbox_mm`, rotulada como o que é. O autoteste ganhou uma
asserção com dentes: **se calibre e volume discordarem de sinal, ele falha**, com a mensagem
"o estimador de dimensão está medindo a escada, não a estrutura". É a regressão que deixaria
alguém voltar a um estimador de máximo.

Com o estimador corrigido, o veredito inverte: de *"não adotar, porta 5 reprovada"* nas
quatro variantes para **"melhora parcial, zero portas reprovadas"** nas quatro.

### 8.2 O que melhorou comprovadamente

**Mais Taubin aproxima o calibre da verdade em estrutura fina — monotonicamente.** Tier 3,
erro de calibre contra o diâmetro analítico:

| alvo | V0 (4) | V1 (8) | V2 (12) | V3 (20) | V4 wsinc |
|---|---|---|---|---|---|
| tubo 2 mm | −18,570 | −16,865 | −15,805 | **−14,465** | −15,020 |
| tubo 5 mm | −5,186 | −4,834 | −4,698 | **−4,604** | −5,046 |
| tubo 8 mm | −1,784 | −1,481 | −1,415 | **−0,736** | −0,872 |

Monotônico nos três, sem exceção, e confirmado num terceiro spacing (0,35 mm isotrópico:
−12,500 % em `taubin=0` → −10,815 % em `taubin=4` → −9,226 % em `taubin=20`). O erro de
volume acompanha na mesma direção: o tubo de 2 mm vai de −27,089 % (V0) a −25,343 % (V3),
1,75 pp acima do limiar declarado.

**Mais Taubin reduz a área em calibre grosso.** Tier 3, faixa 10–30 mm: `area_err` cai de
+3,80 % (V0) a +1,09 % (V3); faixa > 30 mm, de +3,41 % a +1,18 %. É a escada de voxel sendo
removida, exatamente o que a hipótese da §5.1 previa — e a única parte dela que se sustenta.

**Nenhuma variante alterou a topologia da malha.** Verificado, não suposto: o filtro só
desloca vértices; `trimesh.Trimesh(process=True)` funde vértices **antes** dele e o array de
faces nunca é reatribuído. Há guarda explícita que levanta exceção se a contagem de
triângulos mudar. Contagem idêntica de vértices e triângulos nas cinco variantes, em todos os
alvos — o experimento isolou mesmo a suavização.

**O default é bit a bit idêntico.** Ver §8.0.

### 8.3 O que piorou comprovadamente

**Mais Taubin afasta a área da verdade em calibre fino.** Tier 3, tubo de 2 mm: `area_err` vai
de −9,027 % (V0) a −12,295 % (V3) no aniso e de −11,793 % a −14,862 % no iso. É coerente com o
calibre: a malha converge para um cilindro mais fino que o verdadeiro, e a área acompanha o
calibre. Direção oposta à do calibre e do volume — trade-off real, não ruído.

**`V4_wsinc` perde para `V3_taubin20` no que importa em estrutura fina.** Tubo de 2 mm:
calibre −15,020 % contra −14,465 %; volume −26,139 % contra −25,343 %; área −12,721 % contra
−12,295 %. Perde nos três. Em calibre grosso empata (área +1,07 contra +1,09 em 10–30 mm).
Não há eixo em que o WindowedSinc, no par (20; 0,1), supere o Taubin.

**O "ganho de área" da faixa 3–10 mm é artefato de reordenação da mediana.** Três dos quatro
alvos **pioram** de V0 para V3 — tubo 5 mm[aniso] |área| 0,852 → 1,583; tubo 5 mm[iso] 3,907 →
4,584; tubo 8 mm[iso] 1,450 → 1,540 (cruzou zero). Só o tubo 8 mm[aniso] melhora (3,928 →
1,004). A mediana da faixa "melhora" 1,12 pp porque trocou de par de alvos. E não é monotônica
nas iterações: −0,84 / −1,15 / −1,12 pp para V1/V2/V3.

### 8.4 Resultado inconclusivo

**Nenhuma variante é forte candidata, e o motivo é o critério da Parte D, não uma reprovação.**
Volume e área melhoram em faixas **diferentes**: o calibre e o volume ganham no fino, a área
ganha no grosso, e a área **perde** no fino. Pela regra declarada — melhorar volume **e** área
em **todas** as faixas — nenhuma passa. Todas as quatro saem como `melhora parcial`, com
**zero portas reprovadas**.

**As portas 3 e 4 (topologia) são tautológicas para estas variantes e não creditam ninguém.**
Elas leem `watertight`, `body_count`, `n_boundary_edges` e `genus`, todos funções exclusivas do
array de faces — que o filtro nunca altera. O `nao` em fechou_cavidade, fundiu_componentes,
criou_ponte, removeu_conexao_fina e abriu_malha é **garantido antes de rodar**. Das seis
matrizes do benchmark de topologia, cinco são controle negativo; só `gerou_self_intersection`
depende da posição dos vértices, e deu 0 em 40/40 — o que, com encolhimento máximo de área de
3,2 % e um detector que descarta pares que compartilham vértice e pares quase-paralelos, é mais
compatível com "nenhuma geometria do conjunto podia dobrar" do que com "os filtros são seguros".

**O Tier 1 não discrimina nada aqui, por duas vias.** `dice`/`ASSD`/`HD95` são tautológicos com
σ = 0 (já declarado na §4.2), e o `HD95` assume **apenas dois valores** nas 35 linhas — 0,0 e
0,6816 mm: é função degrau quantizada na grade de voxel, com um bit de resolução. E o
`area_err` do Tier 1 é contra um **proxy** que é a malha σ=0/taubin=0 — a mesma família das
variantes julgadas, então `V0_taubin4` fica "melhor" por ser a mais próxima do proxy. A coluna
ordena distância até uma escolha, não qualidade.

**A faixa `< 3 mm` ainda mistura duas grandezas.** O `tubo_oco_10_6mm` entra na faixa pela
**parede** de 2 mm mas é medido pelo **diâmetro externo** de 10 mm. Metade da mediana da faixa
está medindo 10 mm e não pode detectar degradação de parede fina. Por isso a conclusão de §8.2
para estrutura fina está apoiada no **`tubo_2mm` alvo a alvo**, não na mediana da faixa.

**n efetivo = 2 por faixa.** Os pares `[aniso]` e `[iso]` têm o mesmo spacing no plano
(0,7 mm), então a dimensão sai idêntica dígito a dígito nos dois. A mediana de 4 valores com 2
distintos é a média de 2 pontos. Não há intervalo de confiança; o limiar de 1 pp é aplicado
sobre isso.

**O regime de malha aberta nunca foi exercitado.** Nenhuma das 155 linhas dos dois benchmarks
saiu não-watertight — o pad de 1 voxel de `_campo_suavizado` fecha até estrutura cortada pelo
campo de visão. `genus = "nao aplicavel"` e `volume = "invalido"` só existiram no autoteste.

### 8.5 Hipótese futura

1. **Suavização com peso por calibre.** O dado mostra que o filtro ajuda o fino (calibre,
   volume) e ajuda o grosso (área), mas prejudica a área do fino. Um número de iterações
   condicionado ao calibre — que `espessura.py` já mede — é a forma óbvia de pegar os dois
   ganhos sem o custo. **Não testado.**
2. **Varredura de iterações de 1 em 1, e contagens ímpares.** A oscilação de paridade (~7 pp
   no volume) nunca foi caracterizada; só a subsequência par foi amostrada. Antes de qualquer
   promoção, é preciso saber se o ótimo está numa contagem que o benchmark não olhou.
3. **Espaço de parâmetros do WindowedSinc.** Só o par (20; 0,1) foi medido, e ele perde para
   Taubin. `pass_band` é o knob que controla o corte espectral; não foi variado.
4. **Métrica de calibre para estrutura não-tubular.** `calibre_mediano_mm` pressupõe um eixo.
   Para a parede do tubo oco, para a bifurcação e para órgão, ela não se aplica — e é por isso
   que a faixa `< 3 mm` continua misturando grandezas.
5. **Detector de auto-intersecção com poder demonstrado no regime real.** O controle positivo
   atual são duas esferas já sobrepostas e concatenadas — um fixture, não uma dobra induzida
   por filtro. Enquanto não houver um controle onde a suavização **cause** a dobra, o `0` não
   distingue "seguro" de "cego".
6. **Hausdorff e RMS bidirecionais.** Os atuais são unilaterais (malha → verdade) e não
   detectam pedaço da verdade que a malha não cobre.

### 8.6 Decisão

```
MASTER permanece inalterada.
marching_cubes · sigma = 0.0 · mesh_smoothing = taubin · taubin_iters = 4
```

Não porque as variantes tenham sido reprovadas — **elas não foram**, e a reprovação original
era artefato do instrumento. E sim porque nenhuma satisfaz o critério declarado na Parte D:
melhorar volume **e** área em **todas** as faixas. `V3_taubin20` é a candidata mais forte
medida (melhor calibre e volume no fino, melhor área no grosso), mas paga com área no fino, e
os dois portões que poderiam absolvê-la são tautológicos. Promover com essa base seria trocar
um número por uma preferência.

O que muda a decisão é a hipótese 1 (iterações por calibre) mais a hipótese 2 (varredura
ímpar/par). Até lá, `taubin_iters = 4` continua sendo o default **por não ter sido superado
sob o critério declarado** — e não por ter vencido um teste que, como se demonstrou, não podia
aprovar ninguém.

---

## 9. Tier 2 — segmentação contra ground truth independente

Data: 2026-09-04. **Este é o primeiro Tier 2 do repositório.** Até esta seção, a linha
"Tier 2 — ausente" da §0 valia sem exceção.

Tier 2 quantifica **apenas o bloco A** da decomposição de erro (A = segmentação,
B = reconstrução, C = simplificação, D = compressão). Nenhum número desta seção se soma aos
das §§2–8, e nenhum diz coisa alguma sobre reconstrução de malha.

### 9.1 Dataset, licença e por que ele é válido

**LCTSC** — Lung CT Segmentation Challenge 2017, no TCIA.
DOI `10.7937/K9/TCIA.2017.3r3fvz08`. Ground truth = RTSTRUCT de contorno de radioterapia,
de três instituições, publicado em 2017.

Licença: **Creative Commons Attribution 3.0 Unported**,
`http://creativecommons.org/licenses/by/3.0/` — `LicenseName` e `LicenseURI` foram **lidos do
registro de série devolvido pela API do TCIA**, não digitados a mão, e ficam gravados no
manifesto do caso e no marcador de cache de cada série.

**Validade da independência**, que é a única coisa que faz um Tier 2 significar alguma coisa:
o task `total` do TotalSegmentator v2 foi treinado **exclusivamente em TCs clínicas de rotina
do University Hospital Basel** (1082 treino / 57 validação / 65 teste, todos do mesmo pool).
Nenhum dataset público de desafio entra nesse treino — os únicos citados são de sub-tasks que o
VRmed não usa (`lung_nodules`, `teeth`). O LCTSC **não está no treino**, é cinco anos anterior
ao modelo, e sua anotação é humana.

**Descartado por contaminação:** Zenodo `10.5281/zenodo.7975081` anota exatamente heart,
trachea, aorta e esophagus nas coleções NLST/NSCLC-Radiomics, sob CC BY 4.0 — mas o "ground
truth" dele é **saída de nnU-Net**. É o dataset mais conveniente do conjunto e o mais inválido.

**Segundo colocado, pendente:** SegTHOR 2019 cobre heart, aorta, trachea e esophagus — 4/4 com
o mediastino do VRmed, e cobre exatamente as duas estruturas que o LCTSC deixa órfãs. Perde por
procedência de acesso: o CodaLab exige cadastro manual e o único mirror aberto no Zenodo é um
re-upload sem declaração de proveniência nem de autorização. São complementares, não
concorrentes.

**Caso medido:** `LCTSC-Train-S1-001`, RTSTRUCT de MIM Software 6.6.7. O
`LCTSC-Test-S1-101` é recusado explicitamente pelo código: é o único escrito por Plastimatch e
passou por um round-trip extra de geometria em 2019.

**n = 1.** Um caso. Não arredondado para cima, sem média, sem desvio-padrão. Não há o que
agregar.

### 9.2 Parte K — controle de geometria (o que foi provado, não presumido)

A grade é compartilhada **por construção**: o TotalSegmentator rodou sobre exatamente o
`gt/image.nii.gz` que o `dcmrtstruct2nii` gravou, não sobre uma conversão paralela. É a
diferença entre *garantir* alinhamento e *verificar* alinhamento.

Verificado mesmo assim, antes de **cada** comparação: `delta_affine_max = 0.0` **exato** —
igualdade bit a bit, não "dentro da tolerância" — nos 5 pares (predição, GT) e nos 14 arquivos.
`shape (512, 512, 140)`; `zooms = (0,9765625 · 0,9765625 · 3,0) mm` lidos de
`header.get_zooms()`, **não** de `np.diag(affine)`; orientação LPS; `det(affine[:3,:3]) =
+2,861`. Linha desalinhada é abortada com exceção, não vira "Dice ruim".

**A pegadinha que o controle pegou.** Nesta série, a ordem espacial das fatias **diverge tanto
do nome de arquivo quanto do `InstanceNumber`**: a primeira fatia espacial é `00000084.dcm`
com `InstanceNumber` 140, e a última é `00000104.dcm` com `InstanceNumber` 1. Ordenar por
qualquer um dos dois **inverteria a série inteira**. A ordenação usa a projeção de
`ImagePositionPatient` na normal do plano (produto vetorial das duas direções de
`ImageOrientationPatient`) — critério espacial. `SpacingBetweenSlices` está **ausente** na tag,
então o espaçamento em Z foi **medido** das posições: mediana 3,0 mm, uniforme dentro de 1e-3.

**GT lido com limiar `> 0,5`**: o `dcmrtstruct2nii` grava foreground como **255**, não 1
(confirmado: `dtype uint8`, valores únicos `{0, 255}`). Ler `== 1` daria máscara vazia e um
Dice 0,0 que pareceria erro do modelo.

**Dependência com remendo declarado:** `dcmrtstruct2nii` 5 chama `pydicom.read_file`, API
removida no pydicom 3. Rebaixar o pydicom mudaria o ambiente do pipeline de produção (pinado
em 3.0.2), então há um shim local que restaura o alias antes da chamada. Nenhum arquivo do
pacote instalado foi editado e nenhuma versão pinada foi trocada. `dcmrtstruct2nii` entra em
`requirements.txt` como linha comentada, marcada como **só para validação Tier 2**.

### 9.3 Resultados

| estrutura (ROI do GT) | variante | Dice | IoU | NSD@1mm | NSD@2mm | HD95 (mm) | ASSD (mm) | erro vol. (%) | recall GT | containment |
|---|---|---|---|---|---|---|---|---|---|---|
| SpinalCord | padrão | 0,8884 | 0,7993 | 0,8524 | 0,9604 | 2,184 | 0,665 | −15,38 | 0,8201 | 0,9692 |
| Lung_R | padrão | 0,9664 | 0,9350 | 0,7335 | 0,7861 | 12,197 | 1,888 | +2,20 | 0,9770 | 0,9560 |
| Lung_L | padrão | 0,9624 | 0,9275 | 0,7738 | 0,8201 | 10,263 | 1,467 | +5,39 | 0,9883 | 0,9378 |
| **Heart** | **recorte_z** | 0,8652 | 0,7625 | 0,3742 | 0,4645 | 18,000 | 3,426 | **−17,24** | 0,7907 | 0,9553 |
| Heart | sem_recorte | 0,8033 | 0,6712 | 0,3020 | 0,3856 | 33,000 | 5,788 | −3,14 | 0,7907 | 0,8163 |
| Esophagus | recorte_z | 0,8309 | 0,7107 | 0,6979 | 0,8477 | 4,026 | 1,078 | −2,83 | 0,8191 | 0,8430 |
| Esophagus | sem_recorte | 0,8307 | 0,7105 | 0,6974 | 0,8472 | 4,026 | 1,080 | −2,80 | 0,8191 | 0,8427 |
| **aorta** | — | **não medido: o dataset não anota esta estrutura** | | | | | | | | |
| **trachea** | — | **não medido: o dataset não anota esta estrutura** | | | | | | | | |

Aorta e traqueia **não foram estimadas por nenhuma via**. O LCTSC não as contorna.

### 9.4 O que melhorou comprovadamente

**O Tier 2 deixou de estar ausente.** A cadeia TCIA → RTSTRUCT → NIfTI → TotalSegmentator →
métrica em mm fecha ponta a ponta, com licença lida da fonte, geometria provada e o resultado
gravado em CSV + JSON + Markdown com campos de reprodutibilidade.

**As distâncias estão em milímetros físicos, e isso foi verificado sem confiar no autoteste.**
Toda distância publicada cai na rede física do voxel: `HD95` da medula = **2,18366 mm =
√5 × 0,9765625** (em índice de voxel seria 2,2361); `HD95` do esôfago = **√17 × 0,9765625**;
`HD95` do coração = **11 × 3,0**. O conjunto de distâncias alcançáveis abaixo de 3 mm, medido
nos dados reais, é `{0 · 0,9766 · 1,3811 · 1,9531 · 2,1837 · 2,7621 · 2,9297}` — todos
múltiplos físicos do spacing.

**O erro líquido de volume do coração era cancelamento, e agora está decomposto.** O
`−3,14 %` publicado na primeira execução é a soma de **+96,4 mL de predição fora da janela do
contorno** com **−143,2 mL de déficit dentro dela** (mais 25,3 mL sobrando dentro). A
discordância que **não** cancela é **264,9 mL = 38,7 % do volume do GT** — doze vezes o número
que a tabela mandava ler. Ambos agora saem no relatório.

**A envoltória pulmonar concorda bem.** Dice 0,9664 e 0,9624, recall 0,977 e 0,988. É o
resultado mais sólido do conjunto — e mede a envoltória, não a lobação.

### 9.5 O que piorou comprovadamente

**A ressalva do pericárdio existia só em prosa.** Na primeira execução, o recorte em Z estava
codificado como `if gt_roi == "Esophagus"` literal. A assimetria era o oposto do que a
magnitude pede: o esôfago ganhou a linha corrigida para um efeito de **0,014 mL** (0,03 % da
predição), enquanto o coração — onde a mesma operação move **96,4 mL**, 14,6 % da predição —
ficou só com o parágrafo. Um relatório que diz "não leia este Dice como acurácia" e não produz
a linha corrigida deixa o número não corrigido como o único que o leitor tem.

**Corrigido:** a condição virou `ROIS_COM_JANELA_Z = ("Esophagus", "Heart")` e o coração ganhou
as duas linhas. Dentro da janela compartilhada, o erro de volume é **−17,24 %** — o pericárdio
aparecendo como viés, que é o que a ressalva sempre disse e o número nunca mostrou.

**A atribuição "o coração é dominado por divergência de extensão em Z" estava superestimada.**
Removida a extensão **por completo**, a discordância não desaparece: `HD95` cai de 33,0 para
18,0 mm e `ASSD` de 5,788 para 3,426 — a extensão explica ~45 % e ~41 %, não "domina". Para o
`NSD@1mm` o argumento cai de vez: apagar as 14 fatias de sobra move 0,3020 → 0,3742. O que
sobra é discordância **dentro** da janela compartilhada. Só o `HD` (42,0 mm = 14 fatias × 3 mm)
é efeito puro de extensão.

### 9.6 Resultado inconclusivo

**`NSD@1mm` e `NSD@2mm` são estruturalmente cegos ao eixo Z.** Com voxel de 3,0 mm em Z,
**nenhum** deslocamento em Z cabe sob os limiares de 1 mm ou 2 mm — o menor deslocamento
possível nesse eixo vale 3,0 mm. As duas colunas creditam apenas concordância **no plano**. O
`NSD@1mm` de 0,3742 do coração é em boa parte artefato de grade, não sinal de contorno, e as
duas colunas não deveriam sustentar argumento nenhum sobre o eixo em que o problema está.

**A explicação "hilo" para o `HD95` dos pulmões é hipótese não medida.** Localizados os falsos
positivos: 55–60 % são casca de **1 voxel** encostada na superfície do GT, e o maior bloco do
lado direito tem 51 mL espalhados por **49 fatias / 147 mm** de altura. Uma estrutura que
atravessa quase toda a extensão craniocaudal do pulmão não é uma região hilar. A assinatura é
**deslocamento sistemático de fronteira** — predição uniformemente um pouco maior —, não
disputa de definição no hilo. O `+2,20 %` e `+5,39 %` de volume são compatíveis com isso.

**O recorte em Z é circular por construção.** A janela vem de `z_gt.min()/max()` **deste caso**,
não do atlas: o pipeline não localiza cricoide nem artéria pulmonar. Ele define como comparável
exatamente onde o GT existe, e por isso **não detecta** o caso em que o contornador divergiu do
atlas. Além disso ele só corta em Z: no esôfago, 6,84 dos 6,86 mL de falso positivo são
**laterais** dentro da janela — o recorte endereça 0,2 % da discordância real. Declarado no
código, não escondido.

**O déficit de 15,4 % da medula não tem padrão limpo.** A razão de área predição/GT fatia a
fatia tem mediana 0,851 mas vai de 0,560 a 1,189, com desvio-padrão 0,100, e em 10 das 140
fatias a predição é **maior**. Um contorno com margem constante daria razão bem mais estável e
nunca maior que 1. "Seção transversal mais fina" descreve a tendência, não uma regularidade.

**Variabilidade interobservador não é medida e não é separável.** O LCTSC declara que
**manteve de propósito** a variabilidade entre as três instituições, e o paper não reporta
nenhuma métrica de concordância interobservador. Sem isso não há teto de referência: não se
sabe qual Dice um segundo anotador tiraria contra o mesmo GT, então "Dice 0,87" não tem régua.

**O spacing que escala todos os milímetros vem de um arquivo que a prova de alinhamento não
cobre.** Ele é lido de `gt/image.nii.gz`, enquanto o verificador compara `pred_masks/*` contra
`gt/mask_*`. Neste caso os três coincidem bit a bit, então nenhum número está errado — mas a
prova tem esse buraco.

**n = 1.** Nenhuma dispersão, nenhuma generalização. Isto **não é uma estimativa de acurácia do
modelo de segmentação**: é a primeira medida tirada com o instrumento montado.

### 9.7 Hipótese futura

1. **Rodar a coorte inteira (60 casos).** O instrumento fecha; o que falta é volume de dados.
   Só com dispersão dá para separar erro de modelo de variabilidade entre as três instituições.
2. **SegTHOR por via oficial**, para cobrir aorta e traqueia — as duas estruturas do VRmed que
   hoje não têm Tier 2 nenhum. Exige cadastro no CodaLab.
3. **NSD com limiar ≥ 1 voxel do maior eixo** (aqui, 3 mm), ou distâncias com interpolação
   sub-voxel. O `NSD@1mm` numa grade de 3 mm em Z mede menos do que aparenta.
4. **Localizar o falso positivo antes de explicá-lo.** A lição do "hilo": uma explicação de
   especificação colada num padrão que os dados não mostram é pior que nenhuma explicação. Um
   mapa de FP/FN por região deveria preceder qualquer atribuição de causa.
5. **Janela de comparação vinda de referência anatômica**, não do alcance do próprio GT — para
   que o recorte deixe de ser circular.
6. **Ground truth de lobos.** O LCTSC não anota lobos, então a lobação do VRmed continua **sem
   Tier 2**. O volume e a contagem de componentes por lobo (abaixo) são o único sinal
   disponível, e **não são métrica de acurácia**.

### 9.8 Lobos — NÃO é Tier 2

Sem ground truth de lobo, isto é sinal interno, não acurácia:

| lobo (predição) | volume (mL) | componentes conexos | maior fragmento |
|---|---|---|---|
| lung_upper_lobe_right | 1399,1 | 1 | — |
| lung_upper_lobe_left | 1250,3 | 1 | — |
| lung_lower_lobe_left | 638,1 | **4** | 3 fragmentos somam 0,246 mL de 638,1 |
| lung_lower_lobe_right | 588,8 | 1 | — |
| lung_middle_lobe_right | 353,0 | **3** | 2 fragmentos somam 0,014 mL de 353,0 |

Os fragmentos são residuais por qualquer critério (82, 2 e 2 voxels no lobo inferior esquerdo;
3 e 2 no lobo médio direito). Registrado porque contagem de componentes é o único detector de
fragmentação que existe aqui — ver §2.5.

### 9.9 Estado da decomposição de erro

| bloco | o que mede | quantificável hoje? |
|---|---|---|
| **A — segmentação** | máscara × ground truth independente | **Sim, parcialmente.** 5 estruturas, 1 caso, LCTSC (§9.3). Aorta e traqueia: não medido |
| **B — reconstrução** | malha × máscara e malha × verdade analítica | **Sim.** Tier 1 (7 estruturas) e Tier 3 (fantomas), §§2–8 |
| **C — simplificação** | derivado × MASTER | **Sim.** Ablação de decimação, §2.4 e §3.3–3.5 |
| **D — compressão** | asset Draco × pré-Draco | **Não.** O `trimesh` não decodifica Draco e lê zeros; medir o asset publicado dá número falso. Nunca quantificado |

**Os quatro nunca se somam.** Um número único de "erro do VRmed" não existe e não deve ser
produzido.
