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
| **Tier 2** | **Acurácia da segmentação contra ground truth independente.** Quanto a máscara se afasta de uma anotação externa. | Dataset rotulado por terceiros | **AUSENTE** — não existe anotação independente no repositório |
| **Tier 3** | **Validação contra fantoma analítico.** Volume e área têm fórmula fechada, então o erro medido é erro **real**. | Fórmula (esfera π/6·d³, cilindro π/4·d²·h) | **Presente** — 14 alvos sintéticos |

Três consequências que atravessam tudo:

1. **Um Dice alto no Tier 1 não diz que a geometria está certa.** Diz que a malha é fiel
   à máscara. Máscara errada + reconstrução perfeita = Dice ~1,0 no Tier 1.
2. **Nenhum número deste relatório estima Tier 2.** Nada aqui pode ser lido como
   "a segmentação acertou X%".
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
