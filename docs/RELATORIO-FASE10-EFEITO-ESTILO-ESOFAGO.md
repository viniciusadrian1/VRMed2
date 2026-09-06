# Fase 10 — efeito de estilo de contorno no esôfago

Data: 2026-09-05 · Par experimental: **LCTSC-S1 × NSCLC-Radiomics (MAASTRO)** ·
Casos: 30 (lado A, LCTSC `development`) + 25 (lado B, NSCLC) = 55

> **Classificação: D — INCONCLUSIVO.** Os dois conjuntos não são comparáveis o bastante para
> separar convenção de contorno de protocolo de aquisição e de acaso. Nada foi treinado.
> O `Tier2_TEST` e o `Tier2_VALIDATION` do LCTSC **não foram lidos**.

---

## 0. O que esta fase mediu e o que ela não conseguiu concluir

Esta fase perguntou **quanto do erro do `BASELINE_ESOFAGO_V1` é explicável por diferença de
convenção de contorno**, e não por incapacidade do modelo. A estratégia era usar um par que
fixasse instituição e geometria de voxel e deixasse só a convenção variar — os casos do
**MAASTRO** presentes nos dois conjuntos.

O desenho **não entregou o controle que prometia**. O par fixa instituição e voxel; **não fixa
protocolo de aquisição**. E a convenção do lado B **não existe documentada em lugar nenhum** —
isso é um resultado desta fase, não uma lacuna de busca. Uma diferença medida entre os dois lados
não pode ser atribuída a uma regra de contorno quando uma das duas regras é desconhecida.

O número que teria sustentado a resposta "estilo é relevante" existe e está publicado aqui ao
lado da recusa em usá-lo (§8.4). Ele não sobreviveu à própria auditoria.

---

## 1. Objetivo

Reduzir a incerteza **causal** sobre a origem do erro do esôfago. As fases anteriores mediram
que o `A_BASELINE_V1` atinge Dice mediano **0,7880** no esôfago do LCTSC `development` (n=30),
contra 0,9089 do coração após a correção de rótulo da Fase 7. A pergunta desta fase é se essa
distância é **erro do modelo** ou **desacordo entre convenções humanas de onde o esôfago começa,
termina e quão largo ele é**.

A fase **não** foi autorizada a treinar, e não treinou. A decisão da Fase 9 —
`TREINO BLOQUEADO` — permanece intacta e esta fase não a revisa.

## 2. Hipótese

**H1 (testada):** parte substancial do erro do baseline no esôfago decorre de diferença de
convenção de contorno entre conjuntos, não de erro de segmentação.

**H0:** o erro do baseline é indiferente à convenção — com instituição e voxel fixos, trocar a
convenção não move as métricas de erro além do que o acaso move.

**Critério declarado antes de medir:** H1 só seria aceita se um efeito sobrevivesse
simultaneamente a (a) correção de multiplicidade Benjamini-Hochberg, (b) intervalo de confiança
excluindo zero e (c) magnitude acima do efeito mínimo detectável (MDE) simulado do desenho.

**Nenhuma medida passou nos três.** Nenhuma passou sequer em dois.

## 3. Datasets utilizados

| | **Lado A** | **Lado B** |
|---|---|---|
| Coleção | LCTSC (TCIA) | NSCLC-Radiomics (TCIA) |
| Recorte | `development` da Fase 5 | subconjunto declarado antes de medir |
| N | 30 (10 S1 · 10 S2 · 10 S3) | 25 |
| Instituição do recorte comparado | **MAASTRO** (S1, n=10) | **MAASTRO** (25) |
| Licença | CC BY 3.0 | **CC BY-NC 3.0** (lida na API) |
| Origem do RTSTRUCT | MIM Software | Varian 15.5.11 |
| GT | contorno de radioterapia, 1 por caso | contorno manual, 1 por caso |

**Declarado antes da aquisição:** 25 casos NSCLC. **Adquiridos:** 25. **Abortos:** 0. O
`subconjunto.json` grava `declarado_em` anterior à primeira medição.

**6 de 36 casos examinados (16,7 %) do NSCLC não têm ROI de esôfago.** Nos 30 que têm, o nome é
uniformemente `"Esophagus"` — não há variação de nomenclatura a resolver.

**Nada foi treinado.** O `BASELINE_ESOFAGO_V1` não foi alterado — foi **chamado**. As 25
predições do lado B foram rodadas do zero com o `roi_subset` de 8 estruturas do baseline; as
máscaras de esôfago que já existiam no `aux_masks` **não serviam** e foram rejeitadas por guarda
(0/30 idênticas voxel a voxel; Dice `aux` × baseline mediano 0,9382, mínimo 0,8986; a Fase 7 já
tinha medido que trocar só a lista de ROIs muda a predição).

## 4. Comparabilidade institucional

Esta é a seção que decide a classe. **A comparabilidade falhou parcialmente.**

### 4.1 O que concorda e o que não concorda

| Situação | Campos | Natureza |
|---|---|---|
| **Concordantes (4)** | `SliceThickness`, `PixelSpacing`, `dz` (3,0 mm em 10/10 e 25/25), `ReconstructionDiameter` (500 mm) | **todos de geometria** |
| **Sobreposição parcial (4)** | `Manufacturer`, `ManufacturerModelName`, `ConvolutionKernel` (só B19f em comum), `KVP` (120 × 120/140) | **todos de aquisição/reconstrução** |
| **Não comparáveis (3)** | `SeriesDescription`, `StudyDescription`, `ProtocolName` — anonimização oposta nos dois lados | procedência |
| **Ausentes nos dois (2)** | `ContrastBolusAgent`, `PatientBirthDate` | — |

**Leitura:** tudo que concorda é geometria; tudo que diverge é aquisição. O par fixa
**instituição e grade de voxel**, e **não** fixa protocolo. Ele isola
`convenção + protocolo de reconstrução`, não convenção sozinha.

### 4.2 Correção obrigatória a esta própria seção

A afirmação inicial de que *"a estratégia de correlação respiratória não bate entre os dois
lados"* foi **refutada** na auditoria. Ela não tinha sido medida — foi **inferida da ausência**
de `SeriesDescription` no lado B. A tabela lê 14 tags e **`ScanOptions` não está entre elas**.
Lendo `ScanOptions` do DICOM real, a fase respiratória **é recuperável**: o marcador Siemens
`TM50PC` (reconstrução gated na fase 50 %) aparece em **15/25** do lado B — exatamente a fase que
o lado A declara como `"50% Ex"` em 9/10.

Isso **não salva a comparabilidade**: revela que o lado B é **quatro populações de aquisição**,
não uma. Ver §4.3.

### 4.3 O lado B não é homogêneo consigo mesmo

| Subgrupo | N | O que é |
|---|---|---|
| 4DCT reconstruído na fase 50 % (`TM50PC`) | **15** | **o único comparável ao lado A** |
| `RT_Thorax3mm` helicoidal, sem gating | 3 | não comparável |
| re-exportação CMS XiO (cabeçalho de aquisição apagado) | 6 | procedência de arquivo, não de exame |
| PET/CT de corpo inteiro (`LUNG1-110`, 355 mA, sem gating) | 1 | **o menos comparável dos 25** |

Comparar o lado A contra o lado B **como bloco único mede a média de quatro protocolos**, não uma
convenção.

### 4.4 Confundidor de primeira ordem que a fase não tinha medido: **era de aquisição**

| | Janela | Duração |
|---|---|---|
| Lado A | 2003-11-01 a 2004-03-03 | 4 meses |
| Lado B | 2005-11-16 a 2014-01-01 | **mais de 8 anos** |

**Interseção vazia.** Os dois lados não se sobrepõem no tempo em nenhum dia. Uma diferença entre
eles pode ser convenção, scanner, protocolo, ou uma década de mudança de prática — e este desenho
não separa esses quatro.

**Consequência favorável, e só ela:** a ausência de sobreposição de datas **exclui reuso do mesmo
exame** entre os conjuntos. **Sobreposição de pessoas continua não medida e não é mensurável**
com as tags disponíveis (`PatientBirthDate` vazio nos dois lados; `PatientAge` ausente em 10/10
do lado A).

### 4.5 Canais de procedência do MAASTRO — com as ressalvas devidas

Dois canais **diretos**, lidos do DICOM, e não de página de dataset:

1. `ProtocolName = "MAASTRO_PETCT_WholeBodyC"` em `LUNG1-110`. **Ressalva obrigatória:** a string
   institucional mais direta do conjunto está justamente no **caso menos comparável** — PET/CT de
   corpo inteiro, 355 mA, sem gating.
2. Casamento de protocolo `RCCTPET_THORAX_8F` entre `LCTSC-Train-S1-008` e `LUNG1-328`.
   **Correção:** **não é casamento exato.** O lado A traz `Specials^RCCTPET_THORAX_8F (Adult)`; a
   igualdade só aparece depois de remover a decoração Siemens. É **substring**. E os dois exames
   casados estão a 5 anos e a 3× de corrente de tubo de distância um do outro.

**Armadilha registrada para não ser citada em fase futura:** `AccessionNumber` = 2819497684894126
aparece em 18/25 do lado B **e** em `LCTSC-Test-S1-101` — que é o único caso do lado A com todo o
texto livre apagado. É **constante de desidentificação** (4 valores distintos em 25 casos), **não**
é um quinto canal institucional.

### 4.6 O que deveria estar na tabela e não estava

- **`PatientSex`**, presente em **55/55**. No par ele **favorece** o desenho: S1 7M/3F contra
  NSCLC 18M/7F, Fisher p = 1,0. A omissão custou credibilidade de graça. Mas na comparação de
  quatro grupos (§7) ele é confundidor real: o **S3 é invertido** (3M/7F) e o sexo prediz
  `area_mediana_mm2` nesta amostra (p 0,0390).
- **Composição da coorte / carga de lesão:** os 13 campos comparados são **todos** de
  aquisição, geometria ou anonimização — **nenhum de composição**. O lado B tem `GTV-1` em 36/36
  e `gtv-2` em 22/36 com o RTSTRUCT em disco, nunca convertido; o lado A não tem GTV algum. As
  duas coortes têm **carga de lesão desconhecida e impareável**.

## 5. Definição dos GTs

### 5.1 O achado central desta seção

**Não existe documentação de convenção de contorno do esôfago no NSCLC-Radiomics.** A fonte
declara **quem** contornou e **o quê** — *"manual delineation by a radiation oncologist"* de
GTV-1 *"and selected anatomical structures (i.e., lung, heart and esophagus)"* — e não declara
**nenhuma regra de como**. Não há atlas, janela de visualização, limites cranial/caudal,
tratamento de lúmen, tratamento de gordura periesofágica, número de anotadores nem revisão.

**A comparação é assimétrica por construção.** O LCTSC tem convenção rastreável; o NSCLC não tem
nenhuma. Uma diferença medida **não pode ser atribuída a uma regra específica**, porque um dos
dois lados não tem regra publicada com que confrontar.

### 5.2 A harmonização do LCTSC foi deliberadamente parcial

Yang et al. 2018, textual: *"extensive editing of contouring was undesirable, because
interobserver variability present in the original contours would be lost"*. O LCTSC **preserva de
propósito** a variabilidade entre instituições. Isso é bom para o propósito original do desafio e
é exatamente o que torna o lado A não-uniforme como referência de convenção.

### 5.3 O que a ontologia do VRmed diz hoje

A extensão longitudinal do esôfago ficou declarada, na Fase 9, como **herdada do GT e não
avaliável** — os limites "cricoide" e "junção gastroesofágica" foram removidos por não serem
observáveis. Esta fase **não** reabre essa decisão e depende dela: quando §6 mede "extensão", ela
mede extensão **do contorno**, não extensão **do órgão**.

## 6. Métricas morfológicas

29 medidas de forma, calculadas nos 55 casos, comparadas entre os quatro grupos e no par.

### 6.1 Nada de calibre separa os grupos

| Medida | LCTSC-S1 | NSCLC | Diferença | p |
|---|---|---|---|---|
| `raio_caracteristico_mm` | 9,250 | 9,252 | **0,0014 mm** | KW 0,4473 |
| `volume_mL` | — | — | — | 0,4080 |
| `comprimento_z_mm` | — | — | 0,00 mm | 0,8713 |
| `area_mediana_mm2` | — | — | — | 0,2889 |

**Correção de linguagem obrigatória:** "praticamente idêntico" é leitura errada de p alto. A
frase correta é: **compatível com zero; este dado só exclui diferença de calibre acima de
~1,15 mm** — cerca de 12 % da estrutura. É o que o IC95 `[-1,153; +1,116]` realmente diz. O poder
no efeito observado dessa medida é **0,058**, praticamente o próprio alfa.

### 6.2 Achado de instrumento — a diferença é menor do que a grade sabe desenhar

| Quantidade | Valor |
|---|---|
| Diferença pontual de largura | 0,0014 mm |
| Borda do IC95 | 1,153 mm |
| MDE simulado | 1,549 mm |
| **Piso de resolução (1 voxel no plano)** | **1,953 mm** |

As três primeiras estão **abaixo** da última. Nenhuma diferença de largura desta magnitude é
representável nesta grade — medida ou não medida, ela não existiria no dado.

### 6.3 Multiplicidade

29 medidas testadas · 1,45 p abaixo de alfa esperados por acaso · **1 observado** ·
**0 sobrevive ao Benjamini-Hochberg**.

`razao_ponta_caudal` é a única com IC95 excluindo zero (diferença −0,563, −28,6 %, Cliff −0,520,
p MW 0,0185) — e **não sobrevive ao BH**.

### 6.4 Déficit de poder — e a correção ao modo de declará-lo

Em **29/29** medidas o efeito observado fica abaixo do MDE. Isso torna todo p alto desta seção
**ausência de poder, não ausência de efeito**.

**Correção:** "não tem poder para nenhuma" achata uma faixa de quase 10× num binário. O poder
**no efeito observado** (Monte Carlo, 4000 repetições) é:

| Medida | Poder |
|---|---|
| `lateral_mediana_mm` | 0,539 |
| `razao_ponta_caudal` | 0,538 |
| `carina_mm_ate_gt_caudal` | 0,488 |
| `dice` | 0,261 |
| `recall` | 0,203 |
| `raio_caracteristico_mm` | **0,058** |

E o MDE publicado é simulado a **alfa 0,05 não corrigido**, enquanto a regra de decisão publicada
exige sobreviver ao BH. **O MDE sob a regra realmente usada é maior que o publicado** — o déficit
de poder é ainda pior que o declarado.

### 6.5 Dois artefatos de grade, um diagnosticado e um que faltava

- `n_fatias_gt` p 0,0008 é **artefato**: está em voxels e o S2 tem dz 2,5 mm. A versão física dá
  p 0,8713. Já estava diagnosticado.
- **As métricas de ponta têm a mesma doença e ela não tinha sido diagnosticada.**
  `area_ponta_caudal_mm2` × dz: rho −0,3736 (p 0,0050); `razao_ponta_caudal` × dz: rho −0,2768
  (p 0,0408); `razao_ponta_cranial` × dz: rho +0,3106 (p 0,0210). O ordenamento
  S3 > S2 > S1 > NSCLC é **monótono no dz** (3,0400 · 2,5278 · 2,2715 · 3,0411 mm). E
  `area_ponta_caudal_mm2` é absoluta e correlaciona com tamanho (× volume rho +0,4962,
  p 0,000117).

Várias medianas coincidem exatamente entre S1 e NSCLC porque **os dois compartilham a mesma
grade** — não porque as estruturas sejam iguais.

## 7. Efeito de instituição

A comparação de quatro grupos (S1 · S2 · S3 · NSCLC) **estava abaixo do padrão da própria fase**
e é rebaixada aqui.

**O que faltava:** cada medida trazia apenas `{H, p, n_grupos_usados}` — **zero** tamanho de
efeito, **zero** IC, **zero** MDE, **zero** correção de multiplicidade, enquanto §6, §8 e §10
corrigem. Rodar 29 Kruskal-Wallis na mesma amostra sem BH e concluir por p alto é exatamente o
erro que a fase evita em todo o resto.

**Aplicando o BH da própria fase aos 29 KW:** sobrevivem **dois** —

| Medida | p BH | Status |
|---|---|---|
| `n_fatias_gt` | 0,0209 | **artefato de grade**, já descartado |
| `area_ponta_caudal_mm2` | 0,0209 | escala absoluta, correlaciona com dz e com volume |
| `razao_ponta_caudal` | **0,1294** | **não sobrevive** |

Ou seja: das duas sobreviventes, uma é artefato conhecido e a outra é confundida por dz e por
tamanho. **Nenhum efeito de instituição está estabelecido neste desenho.**

> **Instrumento corrigido e reexecutado.** `comparar_quatro_grupos` agora aplica o mesmo
> Benjamini-Hochberg das demais partes, com os dois controles de sempre no autoteste (BH tem de
> engolir o vencedor de loteria e poupar um p de 1e-6) mais uma guarda para o bloco de
> multiplicidade não reentrar na família que ele corrige. O BH foi recalculado a partir de
> `morfologia_por_caso.csv` e gravado em `morfologia.json`: **29 testes · 1,45 esperados por
> acaso · 3 p brutos abaixo de alfa · 2 sobreviventes.** Os `H` e `p` originais foram conferidos
> número a número e **não mudaram** — a correção acrescenta colunas, não reescreve medições.

Confundidor adicional já citado em §4.6: sexo desbalanceado no S3 (3M/7F contra 7M/3F em S1 e S2)
e preditivo de `area_mediana_mm2` (p 0,0390).

## 8. Experimento MAASTRO

### 8.1 A régua e sua estabilidade

Todas as medidas longitudinais são ancoradas na **carina** (extremo caudal da `trachea`
predita). A régua foi atacada e **não caiu**: sob três variantes do detector, o desvio do índice
é mediana **0,00 mm** e máximo **3,0 mm** (uma fatia) nos dois lados, sem diferença entre S1 e
NSCLC (p 0,8946), mesmo número de componentes conexos (p 0,8803) e mesmo volume de traqueia
predita (p 0,5714). **Não há evidência de deriva de régua entre os lados.**

**Mas "disponível em 55/55" não é "plausível em 55/55".** Em `LUNG1-099` a régua devolve ponta
caudal do GT **39 mm acima da carina**, com comprimento total 117 mm contra mediana de grupo
228 mm. Nenhum contorno de esôfago termina cranial à carina. É o mesmo caso com HD95 145,11 mm e
precision 0,3543 — o pior do lado B. **Ele passa hoje por "régua disponível" e não deveria.**

### 8.2 Dependência de subgrupo — o teste que separa convenção de aquisição

Restringindo o lado B aos **15 casos de protocolo comparável** (4DCT fase 50 %), três achados se
comportam de formas qualitativamente diferentes:

| Achado | Subgrupo **comparável** (n=15) | Subgrupo **não comparável** (n=10) | Segue |
|---|---|---|---|
| `recall` | p 0,1416 · Cliff −0,360 — **perde alfa** | **p 0,0058** | **aquisição** |
| `razao_ponta_caudal` | **p 0,0247** · Cliff −0,547 | p 0,0757 | **convenção** |
| `lateral_mediana_mm` | **p 0,0284** · Cliff +0,533 | p 0,2413 | **convenção** |
| extensão caudal | **4,5 mm** | **13,5 mm** | **aquisição** |

**Re-etiquetagem obrigatória:** o achado de `recall` (Cliff −0,512, IC95 `[-0,808; -0,160]`,
p MW 0,0204, BH 0,1633) **é conduzido pelos 10 casos de protocolo divergente**. A frase correta é
"a diferença de recall acompanha a divergência de aquisição" — exatamente o confundimento que o
par deveria eliminar. Não é evidência de convenção.

`razao_ponta_caudal` e `lateral_mediana_mm` fazem o oposto: **sobrevivem ao recorte e ficam mais
fortes**. Essa é a diferença qualitativa entre eles e o recall. **Continua valendo que nenhum dos
três passa no BH e que todos ficam abaixo do MDE.**

### 8.3 A extensão caudal — a única quantidade que estava acima do piso

Os **10,5 mm** de extensão caudal a mais no S1 eram a **única** diferença acima da resolução de
grade, e o **único insumo real** dos tetos de Dice (a largura devolve 1,0000 nos três cenários
reais). Ela não passa em nenhum critério que a própria fase aplica em todo o resto:

| Critério | Valor |
|---|---|
| IC95 da diferença (bootstrap, 20 000 reamostragens) | **`[-3,00; +18,00]` mm — inclui zero** |
| p MW | 0,2960 |
| Cliff | +0,232 (pequeno) |
| MDE | 16,2 mm |
| Subgrupo comparável | cai para **4,5 mm** |
| Mesmo encurtamento medido **por caso** (`span`) | **0,00 mm** (Cliff −0,112, p 0,6213) |
| `comprimento_z_mm` por caso | **0,00 mm** (p 0,6213) |

**Os 10,5 mm existem só como diferença de duas marginais.** Medido caso a caso, o encurtamento é
zero.

### 8.4 O teto de Dice — o número que teria sustentado B, e por que ele não sustenta

| Cenário | Teto de Dice |
|---|---|
| Deslocamento de um voxel de largura | 0,8613 (min–max 0,8083–0,8975; n=35) |
| Aparo de 10,5 mm de extensão caudal | 0,9562 (min–max 0,9307–0,9661; n=10) |
| **"Pior caso" publicado (combinado)** | **0,8369** (min–max 0,8146–0,8573) |
| Baseline `development` | 0,7880 |

Este é o número que apontava para a classe B. **Quatro problemas o derrubam:**

1. **O rótulo "mais pessimista que este dado permite" é falso.** O cenário é conservador na
   largura (inflada ao piso de grade de 1,953 mm, **acima** da borda do IC95 de 1,153 mm) e
   **não-conservador na extensão** (estimador pontual de 10,5 mm, sem propagação de incerteza).
   Aplicando à extensão o mesmo tratamento de borda que se aplicou à largura: a 16,2 mm o teto
   só-por-extensão vai a 0,9444 e o combinado a **0,8269**; a 18,0 mm (borda do IC95), a 0,9328 e
   **0,8179** (min 0,8007).

2. **A régua de comparação está errada.** O teto combinado é mediana de **10 casos S1** e é
   comparado ao 0,7880 do `development` **inteiro** (n=30, três instituições). O baseline do
   próprio S1 é **0,7995**. A margem publicada usa o denominador errado.

3. **A subtração é proibida pelo próprio código.** O docstring de `teto_do_estilo` diz, em disco,
   que *"a diferença entre os dois NÃO é a fração de erro atribuível a estilo"* e que *"a
   comparação com 0,7880 é de ordem de grandeza, não de contabilidade"*. A coluna
   `vs baseline: +0,168 / +0,049` reintroduzia exatamente a subtração que o autor do instrumento
   proibiu. **Ela está removida desta publicação.**

4. **O teto foi ancorado na medida de menor efeito de toda a tabela.** `MEDIDA_DO_TETO =
   raio_caracteristico_mm` — diferença 0,0014 mm, Cliff +0,024 ("desprezível"), poder 0,058. A
   medida de **maior** efeito da fase (`razao_ponta_caudal`, Cliff −0,520) **nunca foi traduzida
   para Dice**. A escolha é defensável (única medida absoluta, em mm, transversal, com caminho
   geométrico direto para Dice); a consequência não estava escrita.

**Achado de instrumento adicional:** o teto por largura **mistura duas operações diferentes** —
o S1 é **dilatado** (mediana 0,8796, n=10) e o NSCLC é **erodido** (mediana 0,8592, n=25). A
mediana publicada de 0,8613 sobre os 35 é a mistura, não uma quantidade única.

**Correção de notação:** `[0,9307–0,9661]`, `[0,8146–0,8573]` e `[0,8083–0,8975]` são
**mín–máx**, não IC e não IQR — enquanto em §9 os mesmos colchetes significam p25–p75. Os IQR
reais são 0,9467/0,9596 · 0,8279/0,8510 · 0,8505/0,8735. Duas semânticas para o mesmo símbolo,
e a versão mín–máx é a que acompanha o número mais citado da fase.

## 9. Baseline

O `BASELINE_ESOFAGO_V1`, **sem nenhuma alteração**, roda no NSCLC-Radiomics com desempenho da
mesma ordem do LCTSC `development`:

| | Lado A (`development`, n=30) | Lado B (NSCLC, n=25) |
|---|---|---|
| Dice | **0,7880** | **0,7686** `[p25 0,7413 – p75 0,8194]` |
| mín / máx | — | 0,4785 / 0,8570 |
| HD95 | — | 9,0000 mm |
| ASSD | — | 1,4364 mm |
| precision | — | 0,7804 |
| recall | — | 0,8222 |

**No par MAASTRO** (S1 n=10 × NSCLC n=25), com instituição e geometria de voxel fixas:

| | Valor |
|---|---|
| Dice mediana S1 | 0,7995 |
| Dice mediana NSCLC | 0,7686 |
| **Diferença** | **−0,0309** |
| Cliff | −0,232 (pequeno) |
| IC95 do Cliff | `[-0,624; +0,200]` — **inclui zero** |
| p MW | 0,2980 |
| **MDE do desenho** | **0,0670** |

**A diferença é menos da metade do efeito mínimo detectável.** Restringindo ao subgrupo de
protocolo comparável ela vai a 0,0371 (p 0,3317, Cliff −0,240) — ainda pouco mais da metade do
MDE, e com n de 25 para 15 o MDE real do recorte é **maior** que 0,0670, o que torna a conclusão
ainda mais dominada por falta de poder. **Nenhum recorte do lado B produz uma diferença de Dice
que este desenho consiga enxergar.**

**Erro lateral** (métrica nova desta fase — distância no plano entre centroides de GT e predição):
pequeno e parecido nos quatro grupos, mediana por caso entre **1,04 e 1,49 mm** contra um pixel de
0,977 mm. LCTSC-S1 1,0441 · S2 1,2641 · S3 1,4919 (grade 1,2695 mm) · NSCLC 1,3017. **O
deslocamento típico do baseline cabe em cerca de um pixel.**

**Verificação de estanqueidade da escala de HU:** os 6 casos re-exportados por CMS XiO têm
`RescaleIntercept = 0` (contra −1024 nos outros 19), o que levantaria suspeita de inferência
sobre imagem em escala errada. Medido no `image.nii.gz` convertido dos 25: o piso é −1024 e o
pico de ar fica na posição esperada em **25/25**. A conversão tratou o intercept corretamente.
Suspeita levantada e **descartada por medição**.

## 10. Análise de associação erro × estilo

**Regra respeitada em toda esta seção: associação não é causalidade.** Nada aqui é apresentado
como causa.

### 10.1 Multiplicidade

25 testes · 1,25 p abaixo de alfa esperados por acaso · **3 observados** ·
**0 sobrevive ao Benjamini-Hochberg**.

### 10.2 As três associações do enunciado que não envolvem volume são próximas de zero

| Par (grupo TODOS, n=55) | rho | p |
|---|---|---|
| erro lateral × área transversal | +0,0676 | 0,6240 |
| Dice × calibre | +0,1823 | 0,1829 |
| HD95 × comprimento | −0,1499 | 0,2747 |

### 10.3 Achado de instrumento — o sinal da associação mais forte inverte com a normalização

| Versão (n=55) | rho | p |
|---|---|---|
| erro de volume **em % do GT** × largura | **−0,3464** | 0,0096 |
| erro de volume **em mL** × largura | **+0,3412** | 0,0108 |
| volume do GT × largura | +0,6244 | 0,0000 |

O sinal inverte em **4 de 5 recortes**. **A associação mais forte desta parte segue tamanho e a
escolha de normalização, não convenção de contorno.**

### 10.4 Limitação desta seção, declarada

A Parte 7 fica abaixo do padrão que a própria fase impõe em §6 e §9: `rho` é tamanho de efeito,
mas **não há IC e não há MDE**. Com n=10 (recorte S1), um rho de −0,7212 tem intervalo largo o
bastante para incluir zero ou quase — e esse rho está entre os três p brutos abaixo de alfa.

### 10.5 Modelos nulos

**Nulo escalar cruzado** (constante = mediana do alvo no grupo **fonte**, avaliada nos casos do
grupo **alvo**; a função **recusa** fonte == alvo, com `ValueError` explícito e controle positivo
no autoteste — verificado lendo o código):

| Alvo | Cruzamento | Nulo | Baseline | Nulo ganha em |
|---|---|---|---|---|
| `volume_mL` | NSCLC→S1 | 21,04 % | **9,84 %** | 3/10 |
| | S1→NSCLC | 19,51 % | **14,77 %** | 11/25 |
| | NSCLC→S3 | 23,21 % | **19,25 %** | 4/10 |
| `raio_caracteristico_mm` | NSCLC→S1 | **6,08 %** | 13,71 % | 7/10 (p 0,7695) |
| | S1→NSCLC | **7,89 %** | 11,80 % | 14/25 |

**Volume:** o baseline ganha da constante em 3 dos 4 cruzamentos — a rede usa informação
específica do caso. **Calibre:** nos dois sentidos do par MAASTRO, uma constante tirada do outro
conjunto **erra menos que a rede**. O padrão não se repete em S2 nem em S3 e o p é alto —
**inconclusivo**, registrado, não interpretado.

**Nulo espacial: não construído, de propósito.** Envelope mediano, calibre normalizado e perfil
longitudinal só viram Dice depois de receberem uma **posição**, e as fontes de posição disponíveis
são circulares (vêm do GT ou da própria rede). **Correção à formulação:** a enumeração original se
declarava exaustiva ("existem exatamente três fontes") e isso não é sustentável; e "posição fixa
em coordenada de imagem, avaliada cruzando grupos" é um **nulo fraco legítimo** — prever mal é o
resultado esperado de um nulo, não motivo para não construí-lo. O correto é dizer **pouco
informativo**, não **inválido**.

## 11. Limitações

**Estruturais — impedem a atribuição causal:**

1. A convenção de contorno do lado B **não é documentada em lugar nenhum**. Comparação assimétrica
   por construção.
2. O par fixa instituição e voxel, **não fixa protocolo**: kernel, kVp e família de aquisição
   divergem.
3. O lado B é **quatro populações de aquisição**, não uma.
4. **Era de aquisição sem interseção**: 4 meses contra 8 anos, sem um dia em comum.
5. **Sobreposição de pessoas entre LCTSC-S1 e NSCLC-Radiomics não foi medida e não é verificável**
   com as tags disponíveis. As datas não se sobrepõem, o que exclui reuso do mesmo exame — não
   exclui a mesma pessoa examinada em anos diferentes.
6. **Composição das coortes impareável**: carga de lesão desconhecida dos dois lados (GTV presente
   em disco só no lado B, nunca convertido).

**De poder e de instrumento:**

7. Efeito observado abaixo do MDE em **29/29** medidas de forma e **8/8** métricas de erro. O MDE
   publicado é a alfa não corrigido, logo **subestima** o déficit.
8. Diferença de largura **abaixo do piso de resolução** da grade (1,953 mm).
9. `n_fatias_gt` e as métricas de ponta são **quantizadas pelo dz** e correlacionam com ele.
10. Medidas absolutas de ponta correlacionam com **tamanho** (volume, área).
11. O S3 tem dz implícito variando 1,25–3,00 mm **dentro do próprio grupo**.
12. `LUNG1-099` tem régua implausível (ponta caudal 39 mm acima da carina) e passa hoje por
    "régua disponível em 55/55".
13. `LUNG1-021` teve fatias não equidistantes silenciosamente regularizadas na conversão,
    esticando z em 0,51 %.
14. 6/25 do lado B re-exportados por CMS XiO entram em todas as medidas em mm com o cabeçalho de
    aquisição apagado.
15. §7 (quatro grupos) rodou sem tamanho de efeito, IC, MDE ou BH; suas afirmações negativas estão
    rebaixadas nesta publicação.
16. §10 rodou sem IC e sem MDE nos coeficientes de correlação.

**Não medido:**

- Distância da GTV-1 ao esôfago no lado B (dado em disco, não convertido).
- Reprodutibilidade intra-anotador em qualquer um dos lados (1 contorno por caso nos dois).
- Qualquer caso do `Tier2_TEST` ou `Tier2_VALIDATION` do LCTSC.

## 12. Classificação A/B/C/D

# **D — INCONCLUSIVO**

**Os conjuntos não são comparáveis o bastante para separar as causas.**

A regra declarada antes de medir era: *se a comparabilidade institucional da Parte 1 falhar, D é
a resposta correta por mais tentador que seja concluir outra coisa.* **Ela falhou parcialmente**,
e §5, §6, §8 e §10 acrescentaram bloqueios independentes.

**Os bloqueios, cada um suficiente sozinho:**

| # | Origem | Bloqueio |
|---|---|---|
| 1 | §4.1 | O par fixa instituição e voxel, **não** protocolo — isola convenção **+** reconstrução |
| 2 | §4.1 | Procedência institucional do lado B continua **hipótese** (3 campos não comparáveis) |
| 3 | §5.1 | A convenção do lado B é **desconhecida** — não há regra com que confrontar |
| 4 | §6.3 | 29 medidas de forma, **0 sobrevivem ao BH**; efeito abaixo do MDE em 29/29 |
| 5 | §10.1 | 25 associações, **0 sobrevivem ao BH** |
| 6 | §10.3 | A associação mais forte **inverte de sinal** com a normalização |
| 7 | §4.4 | **Era de aquisição sem interseção** — 4 meses contra 8 anos |
| 8 | §4.3 | Heterogeneidade de aquisição **dentro** do lado B: quatro populações |
| 9 | §8.2 | Os sinais de erro **dependem de subgrupo**, e o mais forte segue **aquisição** |
| 10 | §4.4 | **Sobreposição de pessoas impossível de verificar** |

**O número que teria sustentado B está publicado ao lado da recusa** (§8.4): teto de Dice no
"pior cenário" 0,8369, contra baseline 0,7880. Ele **aponta** para B — estilo relevante, com erro
sobrando. Ele **não pode ser publicado como B** por quatro razões medidas: o cenário não é o mais
pessimista (com a borda do IC95 da extensão cai a 0,8179), a régua de comparação é o denominador
errado (o S1 tem baseline 0,7995, não 0,7880), a subtração é proibida pelo próprio instrumento, e
o teto está ancorado na medida de **menor** efeito da tabela.

**Não escolhi D por conveniência.** D é o resultado menos interessante desta fase e o único que o
dado sustenta. B era o resultado que a fase parecia estar produzindo até a auditoria, e foi a
auditoria — não a preferência — que o desmontou.

**O que mudaria a classe:**

- documentação de convenção de contorno do lado B → removeria o bloqueio 3;
- um par com o **mesmo** kernel, kVp e estratégia respiratória → removeria 1 e 8;
- um conjunto com **múltiplos anotadores independentes** sobre os **mesmos** casos → mediria
  estilo diretamente, sem depender de par entre coleções;
- n suficiente para levar o MDE abaixo dos efeitos observados → removeria 4 e 5.

## 13. Impacto no treino

**`TREINO BLOQUEADO` — permanece.**

A Fase 9 bloqueou o treino por 9 guardas independentes, todas relativas a independência do
conjunto de teste. **Esta fase não removeu nenhuma delas e não tentou.** Ela acrescenta um motivo
novo e de natureza diferente: **não se sabe qual fração do erro do baseline é do modelo.** Treinar
para reduzir um erro cuja composição é desconhecida otimizaria contra um alvo que não foi medido.

Aplicando a regra do enunciado para a classe D, textualmente: **não concluir nada sobre capacidade
do modelo. O bloqueio experimental permanece.**

Três consequências que **não** seguem deste resultado e não devem ser escritas em fase futura:

- O baseline **não** foi mostrado ruim. Dice 0,7686 no lado B contra 0,7880 no lado A é
  desempenho da mesma ordem, com diferença abaixo do MDE.
- O efeito de estilo **não** foi mostrado grande. Ele não foi mostrado — foi **não medido por
  falta de comparabilidade e de poder**.
- Nenhuma associação desta fase é causa. Nenhuma sobreviveu à multiplicidade, e a mais forte
  inverte de sinal conforme a normalização.

**Estanqueidade verificada:** nenhum caso do `test` ou do `validation` do LCTSC foi lido. Os 30
casos do lado A são **exatamente** o `development` (igualdade de conjuntos; interseção 0 com
`validation` e 0 com `test`; o lado A reusado da Fase 7 também é 30/30 `development`). Os nomes
`LCTSC-Test-*` que aparecem nos arquivos **não são vazamento**: o split do projeto reparticiona a
coleção inteira, e oito casos com prefixo `Test` caem no `development`.

## 14. Próxima ação

**Uma única ação: adquirir um conjunto com múltiplos anotadores independentes sobre os mesmos
casos, ou concluir que ele não existe publicamente.**

Justificativa: dos 10 bloqueios de §12, **quatro** (1, 3, 8, 9) existem porque esta fase tentou
medir estilo **entre coleções**, comparando duas populações que diferem em muito mais que estilo.
Um conjunto com contornos repetidos sobre os **mesmos** casos mede estilo **dentro** do caso —
anatomia, aquisição, era, scanner e coorte ficam **idênticos por construção**, não por
argumento. É o único desenho que remove os bloqueios estruturais em vez de contorná-los.

A matriz de datasets já registra que **nenhum dos quatro torácicos com esôfago verificados**
(LCTSC, NSCLC-Radiomics, StructSeg2019-T3, SegTHOR) tem mais de um conjunto de contornos por
caso. Se a busca confirmar que não existe conjunto público com múltiplos anotadores, o resultado
**também é uma conclusão** — e aí a fase seguinte discute explicitar variabilidade humana por
outra via, não medi-la.

**O que não fazer em seguida:** não republicar esta fase com o lado B estratificado esperando que
D vire B. A estratificação foi feita (§8.2) e **reforçou** D. Não há recorte do lado B que
produza uma diferença de Dice visível a este desenho.

---

## Apêndice A — correções aplicadas a afirmações desta própria fase

| Afirmação original | Veredito | Correção |
|---|---|---|
| "a estratégia respiratória não bate entre os lados" | **refutada** | Não foi medida, foi inferida de ausência. `ScanOptions` mostra `TM50PC` em 15/25 — mesma fase 50 % do lado A |
| "casamento **exato** de protocolo `RCCTPET_THORAX_8F`" | **enfraquecida** | É substring após remover a decoração Siemens `Specials^…(Adult)`; os dois exames distam 5 anos e 3× de corrente |
| `LUNG1-110` como canal institucional limpo | **enfraquecida** | É o caso **menos** comparável do conjunto (PET/CT de corpo inteiro) |
| "S1 se estende 10,5 mm mais caudal" | **enfraquecida** | IC95 `[-3,0; +18,0]` inclui zero; cai a 4,5 mm no subgrupo comparável; medido por caso é **0,00 mm** |
| `recall` com IC95 fora de zero como sinal de convenção | **enfraquecida** | Conduzido pelos 10 casos de protocolo divergente (p 0,0058 lá, 0,1416 nos comparáveis) — segue **aquisição** |
| "0,8369 é o cenário mais pessimista compatível com o dado" | **enfraquecida** | Conservador na largura, não-conservador na extensão; com a borda do IC95 cai a 0,8179 |
| Coluna "vs baseline 0,7880 → +0,168 / +0,049" | **refutada** | Contabilidade proibida pelo docstring do próprio `teto_do_estilo`. **Coluna removida** |
| Ponta caudal "separa nas duas escalas" (KW p 0,0014 / 0,0134) | **enfraquecida** | §7 rodou 29 KW **sem BH**; sob BH `razao_ponta_caudal` vai a 0,1294 e **não sobrevive** |
| "calibre praticamente idêntico (9,250 × 9,252)" | **enfraquecida** | p alto lido como ausência de efeito. Correto: compatível com zero, exclui só diferença acima de ~1,15 mm |
| "não tem poder para nenhuma" (29/29 abaixo do MDE) | **enfraquecida** | Verdadeiro como escrito, mas achata poder de 0,058 a 0,539 num binário |
| Colchetes `[a–b]` no bloco do teto | **enfraquecida** | São **mín–máx**; em §9 os mesmos colchetes são p25–p75. Notação agora declarada em cada uso |
| "existem exatamente três fontes de posição" (nulo espacial) | **enfraquecida** | Enumeração não é exaustiva; posição fixa cruzando grupos é nulo **fraco legítimo**, não inválido |
| "régua disponível em 55/55" | **enfraquecida** | Disponível foi verificado; **plausível nunca foi**. `LUNG1-099` viola |

**Sobreviveram ao ataque:** a estabilidade da carina entre os lados; as trancas de estanqueidade
(`test`/`validation` não lidos, baseline chamado e não alterado, subconjunto declarado antes);
a reprodução independente do teto por extensão (0,9562, min 0,9307, max 0,9661); a contagem de
IC95 excluindo zero (exatamente uma medida em cada critério); a heterogeneidade do lado B; a
correção de escala de HU nos casos XiO; o nulo escalar cruzado; e **a classe D**.

## Apêndice B — dívida de instrumento registrada

Itens medidos e **não** corrigidos nesta fase, para não confundir correção de instrumento com
resultado:

1. `CAMPOS_PROTOCOLO` lê 14 tags e não inclui `ScanOptions`, `StudyDate`/`SeriesDate`,
   `ImageType`, `XRayTubeCurrent`, `Exposure`, `SoftwareVersions` nem `PatientSex`.
2. §7 ainda precisa de **tamanho de efeito, IC e MDE**. A correção de multiplicidade foi feita
   nesta fase (ver caixa em §7); o resto do aparato de §6 continua faltando lá.
3. `carina_desvio_mm_max` e `carina_n_componentes_traqueia` são calculados por caso e
   **descartados**; os números são favoráveis e publicá-los só fortaleceria a régua.
4. Falta guarda de **plausibilidade** da régua (ponta caudal do GT tem de ficar caudal à carina),
   com controle positivo.
5. `spearman` devolve `{n, rho, p}` sem IC — abaixo do padrão de §6 e §9.
6. Análise de sensibilidade excluindo os 6 casos XiO e os 4 de 140 kVp: pedida pela própria
   limitação, não executada.
