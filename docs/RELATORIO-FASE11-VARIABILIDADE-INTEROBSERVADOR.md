# Fase 11 — busca de variabilidade interobservador para o esôfago

Data: 2026-09-06 · Duas ondas · 56 agentes, 0 erros · Nada treinado

> **Resultado: B — EXISTE, MAS É INADEQUADO.**
> O desenho interobservador **existe** em dado público, aberto e licenciado — e não
> aplicado ao esôfago. E existe **um** conjunto com o objeto e o desenho certos, atrás de
> acesso restrito. Nenhum contorno novo entrou. `TREINO: BLOQUEADO`.
> O `Tier2_TEST` e o `Tier2_VALIDATION` do LCTSC **não foram lidos** (guarda g7).

---

## 1. Objetivo

Determinar se existe fonte de dados legítima com **múltiplos anotadores independentes
sobre os mesmos exames** de TC torácica, com anotação humana do esôfago, utilizável para
estimar a variabilidade interobservador.

A pergunta por trás é a que as Fases 9 e 10 deixaram sem resposta: **qual parte do erro
observado no esôfago é indistinguível da variabilidade humana de anotação?** Sem um piso
humano, o Dice 0,7880 do `BASELINE_ESOFAGO_V1` é um número auto-referente — não se sabe se
está longe do que um humano faria ou dentro da faixa em que dois humanos discordam entre si.

## 2. Hipótese

**H1:** existe dataset público satisfazendo **simultaneamente** os sete filtros.
**H0:** não existe entre os candidatos pesquisáveis, e a inexistência prática pode ser
demonstrada por busca reproduzível.

**Critério declarado antes de buscar:** a decisão só pode ser tomada sobre fonte primária
aberta, nunca sobre snippet de busca; toda exclusão tem de citar o **número do filtro** e a
evidência verbatim; e uma lacuna de acesso **nunca** pode ser registrada como ausência.

## 3. Estratégia de busca

Duas ondas, porque a primeira **falhou na própria auditoria** e a segunda existe para
consertá-la — o registro dessa falha é parte do resultado (§12.1).

| | 1ª onda | 2ª onda |
|---|---|---|
| Agentes | 40 | 16 |
| Estratégia | censo TCIA por nome + 6 arms de busca + 24 fichas + 4 céticos | instrumento consertado + índice IDC + varredura completa + 5 lacunas + comissionamento + 3 céticos + juiz |
| Cobertura de nome | **58 structure sets = 0,062 %** | **11.439 abertos (12,1 %) + 19.358 RTSTRUCT pelo índice IDC = canal DICOM público inteiro** |

**Os sete filtros**, aplicados sempre nesta ordem, com o número citado em toda exclusão:

| | Filtro |
|---|---|
| **F1** | mesmo exame com ≥2 contornos de esôfago |
| **F2** | contornos humanos (não pseudo-rótulo, não *model-in-the-loop* irrecuperável, não dois *outputs* do mesmo modelo, não consenso de um modelo) |
| **F3** | número de anotadores verificável |
| **F4** | licença/acesso verificável |
| **F5** | anatomia comparável ao objeto do VRmed |
| **F6** | contornos recuperáveis **individualmente** |
| **F7** | comparação geométrica em mm |

**Parte C respeitada em todo o relatório:** *interobserver* ≠ *interinstitution* ≠
*intraobserver*. Dois datasets não são dois observadores; dois hospitais não são dois
observadores; dois algoritmos não são dois observadores; consenso não substitui os
contornos individuais.

## 4. Fontes consultadas

**Canal DICOM — enumerado, não amostrado.**

| Fonte | O que foi enumerado |
|---|---|
| API NBIA do TCIA | **156 coleções** (todas as que a API anônima expõe), 94.276 séries de contorno |
| **Índice público do IDC v24** (`idc-index-data 24.2.2`) | **19.358 RTSTRUCT + 190.146 SEG**, 41.444 nomes de ROI, 176 coleções — sem credencial, sem baixar pixel |
| Tabela de coleções do site do TCIA | 237 linhas (180 *Public* / 50 *Limited* / 7 em branco); 85 sem correspondência na API, 19 delas declarando RTSTRUCT/SEG |
| **TCIA Analysis Results** | **60 registros, enumerados como universo pela primeira vez** — `esophag\|oesophag` ocorre **0 vezes** |

**Canal não-DICOM e literatura.** Zenodo, Figshare, Dryad, OSF · Grand Challenge (QUBIQ,
SegTHOR, StructSeg2019, SegRap2023, HECKTOR, LNQ, AMOS, FLARE, HaN-Seg, PDDCA, AAPM RT-MAC,
LCTSC, OpenKBP, Gold Atlas) · PubMed, Europe PMC, arXiv, Red Journal, *Radiotherapy and
Oncology*, *Physics and Imaging in Radiation Oncology* · GitHub · Synapse/Sage, PhysioNet,
Kaggle, HuggingFace, MIDRC, Stanford AIMI · e um arm deliberadamente **oblíquo** (ensaios de
credenciamento de contornagem — EORTC, RTOG/NRG, TROG, IAEA; atlas de consenso; QA de
contorno; plataformas educacionais).

## 5. Candidatos

**32 candidatos com ficha de fonte primária aberta. Zero válidos.**

### 5.1 O padrão que o corpus revela

Multi-observador humano em imagem médica pública **existe, é abundante e é acessível**:

| Candidato | Observadores | Objeto | Licença | Elimina |
|---|---|---|---|---|
| **QIBA CT-1C** | **7** leitores nomeados | nódulo em *phantom* | CC BY 3.0 | **F5** |
| **NSCLC-Radiomics-Interobserver1** | **5** humanos (`GTV-1vis-1..5`) | GTV | CC BY-NC 3.0 | **F5** |
| **RIDER Pilot** | 5 leitores nomeados | nódulo | CC BY 4.0 | **F5** |
| **RIDER Lung CT / QIBA VolCT** | 5 leitores × 2 exames × 32 casos | nódulo | — | **F5** |
| **Gold Atlas** | 5 observadores | pelve | Zenodo *restricted* | F5 + F4 |
| **LIDC-IDRI** | 4 leitores | nódulo pulmonar | CC BY 3.0 | **F5** |
| **NLST / LIDC-annot-NLST501** | 4 leitores | nódulo | CC BY 4.0 | **F5** |
| **CURVAS** (MICCAI 2024) | 3 observadores | abdome | Zenodo | **F5** |
| **Pancreatic-CT-CBCT-SEG** | 2 (`Obs1`/`Obs2`) | intestino, estômago-duodeno | CC BY 4.0 | **F5** |
| **HaN-Seg / vOARiability** | 2 (JO/SO) | cabeça-pescoço (esôfago **cervical**) | CC BY-ND | F5 + F6 |
| **google-deepmind/tcia-ct-scan** | 2 (oncologista × *radiographer*) | 21 estruturas de Brouwer | CC BY 4.0 | **F5** |

**Todos morrem no mesmo filtro.** O desenho existe; o objeto nunca é o esôfago.

### 5.2 O candidato com o objeto e o desenho certos

**iCurveE** — ensaio prospectivo multicêntrico (NCT05787522), *Nature Communications* 2026.
Verbatim dos *Methods*:

> *"Experts A and B independently delineated each CT image, resulting in two sets of OARs,
> which were then reviewed by Expert C, who compared and selected the most accurate
> delineations from Experts A and B."*
> *"The bilateral lungs, heart, **esophagus**, aorta, spinal cord, trachea, and bronchial
> tree were delineated according to the Radiation Therapy Oncology Group (RTOG) 1106 atlas."*

500 TCs torácicas, cinco hospitais, esôfago pelo mesmo atlas que o VRmed adota. *Data
availability*, integral:

> *"The CT imaging datasets and delineation results generated in this study are available
> under restricted access due to utilization in ongoing research projects and patient
> privacy protection; access can be obtained by contacting the corresponding author […]
> with a research protocol and proof of ethical approval."*

**Elimina F4.** E — correção obtida na refutação — **não é "só F4"**: a etapa de seleção por
um terceiro especialista é exatamente a armadilha da Parte C. Nada na fonte diz que os dois
conjuntos originais foram retidos e são entregáveis separadamente, logo **F6 passa de
satisfeito a INDETERMINADO, com indício contrário**. Isso não tira o iCurveE de B — a perna
2 de B fala em *"acesso/licença/**procedência** suficiente"*, e procedência insuficiente é
mais um motivo para B, não menos. Mas a frase *"falha só em F4"* **não pode ser escrita**.

### 5.3 Os candidatos com esôfago

Cinco coleções, e só cinco, têm esôfago como órgão no canal DICOM público inteiro:

| Coleção | Séries | Casos | Elimina | Por quê |
|---|---:|---:|---|---|
| `pediatric_ct_seg` | 359 | 359 | **F1** (+F2) | `Esophagus` exatamente 1× em 359/359; `StructureSetName = 'AR AutoSegmentation'`, 42/42 AUTOMATIC |
| `nsclc_radiomics` | 355 | 355 | **F1** | um radio-oncologista |
| `4d_lung` | 101 | 101 | **F1** + F5 | `Esophagus_c00..c90` — o sufixo é **fase respiratória**, não anotador; SEMIAUTOMATIC em 800/800 |
| `lctsc` | 60 | 60 | **F1** | 60 CT / 60 RTSTRUCT, zero estudos com mais de um |
| `eay131` | 33 | 17 | **F1** + F5 | sítio de lesão, não OAR; cada par é contorno + seu `SEED POINT` |

Fora do DICOM: **STOPSTORM** (Zenodo, CC BY 4.0) tem delineação humana **real** de esôfago —
ROI `Esophagus` em 113/117/108 fatias — mas **uma só por caso**. Elimina F1.

### 5.4 As duas quase-interseções, derrubadas por medição

**NSCLC-Radiomics** era a única coleção com esôfago contornado em ≥2 arquivos sobre a mesma
série de CT. Não é um segundo observador: **Dice = 1,0000 em 13/13 casos**, contagem de
voxel idêntica em 12/13. É re-exportação `dcmqi` do mesmo contorno. Derrubado por geometria,
não por presunção.

**NLST** é a única interseção esôfago × múltiplos contornos de todo o corpus: 1.035 TCs com
dois contornos de esôfago cada. **2.070/2.070 declaram `AlgorithmType = AUTOMATIC`** —
TotalSegmentator v1.5.6 × nnU-Net. Dois modelos, não dois observadores (Parte C). Elimina F2.

## 6. Filtros — a tabela de eliminação

| Filtro | Quantos elimina | Exemplos |
|---|---:|---|
| **F5** anatomia não comparável | **11** | QIBA CT-1C, Interobserver1, LIDC-IDRI, RIDER, CURVAS, Pancreatic, Gold Atlas, deepmind H&N |
| **F1** < 2 contornos de esôfago no mesmo exame | **9** | LCTSC, NSCLC-Radiomics, Pediatric-CT-SEG, 4D-Lung, STOPSTORM, S0819 |
| **F4** acesso/licença | **5** | **iCurveE**, NSCLC-Cetuximab/RTOG-0617, NRG-1308, MIDI-B, 16 coleções fora da API |
| **F2** não humano | **4** | **NLST**, QIN-LUNGCT-SEG, Lung Phantom, Guérendel/NKI |
| **F6** individuais não recuperáveis | **2** | Lung-Fused-CT-Pathology (voto majoritário), HaN-Seg (curado) |
| **F3** anotadores não verificáveis | 1 | ACRIN-HNSCC (identidade ausente) |
| **F7** geometria em mm | **0** | nenhum candidato chegou até aqui |

**Nenhum candidato passou de F5.** F7 nunca foi exercido em candidato real — está
exercitado apenas no comissionamento (§10) e nos controles sintéticos das guardas.

## 7. Dataset escolhido

**Nenhum.**

`N casos utilizáveis = 0` · `N observadores independentes = 0` · `N contornos totais = 0`

A formulação permitida, e a única que este dado sustenta:

> *Não foi identificado, na busca realizada, dataset público, acessível e legalmente
> utilizável que satisfaça **simultaneamente** F1–F7 para o esôfago em TC torácica.*

## 8. Procedência

**A negativa deixou de ser amostral.** O índice público do IDC v24 traz `ROINames` de todos
os 19.358 RTSTRUCT do canal DICOM público, sem credencial e sem baixar pixel. Reproduzível
em ~10 s por [`idc_esofago.py`](scripts/validation/tier2/idc_esofago.py):

```bash
.venv-pipeline/Scripts/python.exe -m scripts.validation.tier2.idc_esofago
```

| Pergunta | Resposta sobre o catálogo inteiro |
|---|---:|
| RTSTRUCT no índice público | 19.358 |
| com esôfago **órgão** | **908**, em **5** coleções |
| **F1 dentro do arquivo** (≥2 nomes de esôfago) | **0** |
| nome repetido escondido pelo `DISTINCT` (Q4) | **0** |
| **F1 entre arquivos** (mesma série de CT) | **16**, todos `eay131`, todos pares contorno + `SEED POINT` |
| CTs com ≥2 SEG **MANUAL** de esôfago | **0** |

**O que este canal não cobre, declarado:** acesso restrito (iCurveE, RTOG-0617, NRG-1308) e
o canal não-DICOM (STOPSTORM, PleThora, SAROS, CURVAS) — tratados a mão, um a um.
`ROIGenerationAlgorithms` só vem preenchido em ~25 %, então **F2 não é decidível pelo
índice**; e o índice **não tem `ContentCreatorName`**, o que torna o defeito D7 (§12.1)
indetectável ali por construção.

**Sobreposição de UID entre coleções = ZERO** (156 coleções, 94.276 séries de contorno;
[`sobreposicao_uid.py`](scripts/validation/tier2/sobreposicao_uid.py)). Nenhum
`StudyInstanceUID`, `SeriesInstanceUID` ou `PatientID` de contorno aparece em duas coleções.
O padrão "segundo grupo re-anota os mesmos exames" **existe**, mas só fora do NBIA — PleThora
re-anota as mesmas TCs do NSCLC-Radiomics e o SAROS re-anota 900 TCs de 27 coleções, ambos
ZIP NIfTI. **Nenhum dos dois tem esôfago**; o artigo do SAROS diz textualmente que
*"the esophagus […] w[as] not included"*.

## 9. Número de observadores

**Para o esôfago: 1 por exame, em 5 de 5 coleções que o contornam.** Sem exceção medida no
canal DICOM público.

**Fora do esôfago**, o campo tem de 2 a 7 observadores por exame, humanos e licenciados —
é a base da classe B (§15).

## 10. Variabilidade observada

> ### ⚠ OBJETO = GTV, NÃO ESÔFAGO — ELIMINADO POR F5
> Esta seção **não** é uma medida do esôfago. Nenhum contorno de esôfago foi lido aqui.

A Parte E manda medir os humanos entre si **antes** do baseline. Não há dataset válido para
isso, então o que foi feito é **comissionamento do instrumento**: exercitar as guardas
g5/g6/g9/g10 em desacordo humano **real** — que até aqui só tinham controle sintético — sobre
`NSCLC-Radiomics-Interobserver1`, 5 observadores humanos, 21 casos, **210 pares**, tudo em mm.

| Métrica | Mediana | IQR | min | max |
|---|---:|---:|---:|---:|
| Dice | 0,840 | 0,777–0,890 | 0,471 | 0,940 |
| IoU | 0,724 | 0,635–0,802 | 0,308 | 0,888 |
| HD95 (mm) | 5,099 | 5,000–7,245 | 1,414 | 30,00 |
| ASSD (mm) | 1,471 | 1,061–2,141 | 0,258 | 7,325 |
| dif. volume (%) | 18,5 | 7,97–37,29 | 0,03 | 105,8 |
| dif. comprimento (mm) | 5,0 | 0,0–10,0 | 0,0 | 50,0 |

**Parte F — decomposição** (mediana / p90): **A extensão 5,00 / 15,00 mm** · B largura
1,03 / 2,40 mm · C lateral 1,13 / 3,52 mm · D longitudinal 0,96 / 3,24 mm.

**A discordância humana é dominada pela EXTENSÃO** — onde a estrutura começa e termina em z —
não pela largura nem pela posição. 76/210 pares diferem ≥10 mm de comprimento; só 56/210
concordam exatamente. Isso ecoa o que a Fase 9 já tinha medido no esôfago do LCTSC ao
declarar a extensão longitudinal **herdada e não avaliável**, e o que a Fase 10 mediu ao
achar que a única quantidade acima do piso de resolução era a ponta caudal.

**Fantoma de resposta conhecida:** duas esferas R=15 mm deslocadas de d=5 mm têm solução
fechada (a distância de superfície é uniforme em [0,d], logo HD=d, ASSD=d/2). Medido:
Dice 0,753 (esperado 0,752) · HD 5,000 (5,000) · ASSD 2,371 (2,500) · F_C lateral 5,000
(5,000). O instrumento acerta o que tem resposta analítica.

**Existe um piso de erro humano?** Nesta estrutura, sim, e ele é grosso: metade dos pares de
humanos concorda a Dice ≤ 0,840 e 24/210 pares ficam abaixo de 0,7. **Mas isso não é um
limiar e não se transfere ao esôfago** — ver §11.

## 11. Comparação metodológica com o LCTSC

**A régua de Dice NÃO transfere. Isto foi medido, não suposto.**

Dice é razão volume/volume, e a perda de Dice por milímetro de desacordo escala com a razão
superfície/volume. Medida nos dois objetos:

| Objeto | S/V | Consequência |
|---|---:|---|
| GTV (mediana de 105 máscaras) | **0,1444 /mm** | — |
| Esôfago | **0,3251–0,3805 /mm** | perde Dice **2,8–3,1× mais rápido** por mm de desacordo |

E no modo dominante — extensão, com p90 de 15 mm — **a distorção inverte de sinal**.

**Duas limitações do próprio instrumento, medidas:** na grade real (dz = 5 mm) o ASSD é
subestimado em **−38 %**, e um deslocamento de parede de 1 mm em **−58,9 %**; **108/210 pares
estão no piso de quantização da fatia**. O HD95 mediano de 5,099 mm é literalmente
√(5²+1²) — "um plano de distância". Refazendo tudo com passo no plano de 0,5 mm as medianas
não se movem (Dice 0,840→0,840; ASSD 1,471→1,378): **o eixo que quantiza é o z**, não a
rasterização.

**Portanto: nenhuma comparação com o Dice 0,7880 do `BASELINE_ESOFAGO_V1` no LCTSC
`development` é feita neste relatório, e nenhuma é autorizada por ele.** O que sobrevive
como transferível é o **milímetro** — com o piso de 5 mm e o viés de −38 % a −59 % declarados
junto — e o **achado qualitativo** de que a discordância humana se concentra na extensão.

## 12. Limitações

### 12.1 O instrumento errou, foi refutado e foi consertado — e ainda tem dívida

A 1ª onda concluiu negativo com **0,062 % de cobertura** e um **falso negativo provado**: deu
a `Pancreatic-CT-CBCT-SEG` o veredito *"nem esôfago nem indício de múltiplos observadores"*,
numa coleção cuja própria página diz *"repeat OAR delineations by two independent observers"*
e cujos ROI se chamam `BowelSmObs1`/`BowelSmObs2` — com o token `Obs` **literalmente no
nome**. Causa raiz: a normalização minusculizava **antes** de marcar fronteira, e `Obs` sumia
dentro de `bowelsmobs1`. De 21 convenções reais de rotulagem testadas, o detector via 5; 16
davam negativo e 11 sumiam sem nem virar ambiguidade registrada.

Seis defeitos corrigidos na 2ª onda (`interobservador.py`, 807 → 1489 linhas): fronteira
camelCase, amostragem estratificada por estudo, detecção **entre** arquivos, ambiguidade que
não vira negativo, leitor de SEG, e tri-estado `true/false/null`. **Mutação: 21/21 guardas
mortas** (a 1ª onda tinha 20/21). Prova do conserto em fonte primária: 130/130 structure
sets, 20 famílias fortes, `Obs1`/`Obs2` encontrados.

**Três cegueiras estruturais foram descobertas nesta fase, em dado real, e as três são a
mesma falha deslocada:**

1. o observador mora **dentro** de um arquivo (`GTV-1vis-1..5` num só RTSTRUCT) — contar
   arquivos dá falso negativo;
2. o observador mora em **arquivos separados** apontando para a mesma CT (padrão S0819) —
   ler cada arquivo isolado dá falso negativo;
3. **D7 — o observador mora fora do nome.** `QIBA CT-1C` tem **7 leitores humanos nomeados
   em `ContentCreatorName`** e `SegmentLabel` constante `'Test Label'` em **462/462**. Um
   censo por nome sai negativo numa coleção com sete observadores.

**Dívida em aberto, declarada:** **D7 não foi corrigido** (`grep -c ContentCreatorName
interobservador.py` = 0) — a varredura só escapou porque três dos quatro agentes leram a tag
à mão. E o **tri-estado está meio consertado**: nas linhas 404 e 899 um arquivo *aberto* com
nomes não recuperáveis ainda sai `False`, não `null`.

### 12.2 Cobertura

- A negativa do canal DICOM aberto vale a **12,1 %** (11.439 de 94.276 séries de contorno).
  Treze coleções ficaram abaixo de 5 % de leitura DICOM (S0819 0,1 %, LIDC-IDRI 0,1 %,
  EAY131 0,8 %, NLST 4,0 %, ISPY2 4,5 %…). **Nenhuma é coleção de OAR torácico**, e todas
  têm o canal de nomes coberto por outra via — mas o veredito não carrega a fração, e uma
  coleção lida a 2,3 % recebe a mesma frase negativa de uma lida a 100 %.
- **Uma** coleção ficou `null` (não medida ≠ negativa): `Lung-Fused-CT-Pathology` — as 12
  séries que a API declara SEG desempacotam em 3.204 arquivos `CT Image Storage` sem
  `SegmentSequence`. Cai por F6 independentemente do `null`.
- **16 coleções fora da API** não tiveram conteúdo verificado: 0 séries na API anônima,
  16/16 com restrição de reconstrução facial, todas de cabeça/pescoço/cérebro. **F4 medido,
  conteúdo não verificado** — não se afirma ausência.
- A leitura de 359/359 do `Pediatric-CT-SEG` **não é reproduzível a partir do repositório**
  (20 arquivos em disco); a conclusão é sustentada pelo índice IDC e pelo verbatim de Jordan
  et al. 2022 (*"stored in a single DICOM RTSTRUCT file for each subject"*).
- **LCTSC: 30 de 60** structure sets — os outros 30 são o holdout travado pela guarda g7 e
  **não podem** ser lidos.
- Os 60 Analysis Results dependem de a API e o *sitemap* estarem completos; 6 estão ocultos
  da tabela de navegação.
- **A negativa tem prazo de validade.** O TCIA publica Analysis Results continuamente; o
  censo tem carimbo de 2026-09-06.

### 12.3 Do comissionamento

O objeto é GTV. A régua de Dice não transfere (§11). O ASSD é enviesado −38 % a −59 % na
grade real e 108/210 pares estão no piso de 5 mm. A guarda g12 barra a **palavra** "esôfago",
**não a afirmação**: *"a concordância do órgão-alvo do VRmed é 0,84"* passa limpo por ela.

### 12.4 Frases proibidas

1. ~~"Não existe dataset interobservador de esôfago."~~ → *"não foi identificado, na busca realizada…"*
2. ~~"A concordância interobservador do esôfago é 0,840."~~ — o objeto é GTV.
3. ~~"A concordância do órgão-alvo do VRmed é 0,84."~~ — a mesma frase sem a palavra; **g12 não a barra**.
4. ~~"Dice 0,840 é a régua de escala para o esôfago."~~ — S/V difere 2,8–3,1×, e no modo extensão a distorção inverte de sinal.
5. ~~"O ASSD interobservador é 1,47 mm."~~ — subestimado em −38 % na grade real.
6. ~~"iCurveE / RTOG-0617 / NRG-1308 não têm anotação interobservador de esôfago."~~ — não foi possível verificar; **F4, não ausência**.
7. ~~"Sobreposição zero de UID prova que ninguém re-anota os mesmos exames."~~ — vale só no canal DICOM do NBIA.
8. ~~"O tri-estado separa lacuna de negativa."~~ — separa pela metade.
9. ~~"paciente"~~ / ~~"validado clinicamente"~~ — nunca.

## 13. Impacto no erro do baseline

**Nenhum. E essa é a resposta, não uma lacuna.**

A pergunta que abriu a fase — *qual parte do erro do esôfago é indistinguível da
variabilidade humana?* — **continua sem resposta**, e agora se sabe por quê: não existe, no
canal público enumerado, um segundo contorno humano do esôfago sobre o mesmo exame com que
comparar. **F7 continua sem denominador.**

O `BASELINE_ESOFAGO_V1` permanece **intocado**: Dice 0,7880 no LCTSC `development`, mesmo
número da Fase 10, medido pelo mesmo instrumento congelado. Nenhum contorno novo entrou,
nenhuma métrica dele foi recalculada, e **nenhuma comparação com o 0,840 do GTV é feita ou
autorizada** (§11, §12.4).

O que a fase acrescenta ao entendimento do erro é **qualitativo e indireto**: em desacordo
humano real sobre estrutura de tecido mole em TC torácica, a discordância é **dominada pela
extensão** (A: mediana 5 mm, p90 15 mm) e não pela largura (B: 1,03 mm). Isso é
**consistente** com o que a Fase 9 mediu ao declarar a extensão do esôfago herdada e não
avaliável, e com a Fase 10, onde a única quantidade acima do piso de resolução era a ponta
caudal — mas consistência entre objetos diferentes é **coincidência de padrão, não
evidência**, e não é usada aqui como argumento.

## 14. Impacto no treinamento

# **TREINO: BLOQUEADO**

A Fase 9 bloqueou o treino por 9 guardas de independência do conjunto de teste. A Fase 10
acrescentou um motivo de natureza diferente (não se sabe a composição do erro). **A Fase 11
não remove nenhum dos dois e não tentou.** Ela nunca foi fase de dado de treino — era a
pergunta sobre a existência de uma **referência externa de variabilidade humana**.

- **Zero contornos novos, zero casos, zero anotadores.** Baseline intocado, nenhum modelo
  escolhido, nada otimizado.
- **O único número em mm que a fase produziu é de GTV** e está explicitamente proibido de
  servir de limiar de aceitação para o esôfago. Um treino desbloqueado por ele estaria
  calibrado contra o objeto errado, com ASSD enviesado 38–59 % para baixo e piso de 5 mm.
- **O que desbloquearia** está fora desta fase e é de duas naturezas: **(a)** acesso ao
  iCurveE, ou **(b)** produzir um segundo observador localmente sobre os exames já
  disponíveis. Nenhuma das duas é busca; ambas são **aquisição**.

## 15. Decisão final

# **B — EXISTE, MAS É INADEQUADO**

O texto do enunciado, verbatim: *"Existe multi-observador, porém não é comparável ao objeto
do VRmed **ou** não possui acesso/licença/procedência suficiente."* **As duas pernas foram
provadas, cada uma com instância medida em fonte primária.**

**Perna 1 — não comparável ao objeto.** `QIBA CT-1C` (7 leitores nomeados, 462/462 séries
abertas, CC BY 3.0), `NSCLC-Radiomics-Interobserver1` (5 observadores humanos, 21/21
arquivos, 210 pares **medidos** em mm), `Pancreatic-CT-CBCT-SEG` (2 observadores, 130/130,
CC BY 4.0), `CURVAS`, `Gold Atlas`, deepmind H&N. Todos satisfazem F1, F2, F3, F4, F6, F7 e
morrem em **F5**.

**Perna 2 — acesso/procedência insuficientes.** **iCurveE**: o objeto certo (esôfago, atlas
RTOG 1106), o desenho certo (dois especialistas independentes), a escala certa (500 TCs
torácicas) — e acesso restrito, com a procedência dos contornos individuais indeterminada
pela etapa de seleção por um terceiro.

**Por que não A.** Nenhum candidato satisfaz F1 ∧ F2 ∧ F5. A única coleção com esôfago em
≥2 arquivos sobre a mesma CT foi derrubada **por medição** (Dice = 1,0000 em 13/13 — é
re-exportação); a única interseção esôfago × múltiplo do corpus declara AUTOMATIC em
2.070/2.070.

**Por que não C.** C descreve uma negativa pura, e a fase **não produziu negativa pura**:
produziu positivos medidos de multi-observador humano com acesso legítimo. Classificar C
descartaria um fato medido — o desenho que a Fase 11 procura **existe em dado público,
aberto e licenciado**, só não aplicado ao esôfago. E o argumento de que "um dataset sem
esôfago está fora do universo do discurso" torna a **perna 1 de B literalmente vazia**: se
todo objeto não-comparável for excluído do universo, nada jamais poderia satisfazer a perna
que existe justamente para nomear objetos não-comparáveis.

**Por que não D.** D exige que a informação faltante seja **capaz de mudar a classe**. Todo
candidato que chegou a ficha foi decidido contra um filtro nomeado, com verbatim de fonte
primária. Acesso restrito **não é falta de informação** — F4 é um filtro e "restrito" é um
veredito. A única coleção `null` do corpus cai por F6 independentemente.

**Não escolhi B por conveniência.** Um crítico da 1ª onda votou C — com uma rubrica que ele
**inferiu por analogia** com a Fase 10, por não ter o texto do enunciado. Contra o texto
real, C é a classe que precisa de uma ressalva anexa para não ser lida como inexistência;
**B é a classe que torna a frase proibida impossível de escrever**, porque afirma o
positivo: multi-observador existe, é público, e não está no esôfago.

---

## Próxima ação

**Solicitar formalmente acesso ao iCurveE** (autor correspondente do artigo na *Nature
Communications*, NCT05787522), registrando o pedido **e a resposta — qualquer que seja** —
como ficha de fonte primária em `.clinica-dados/fase11/fichas/`.

> **Executada na Fase 12 — e o resultado foi melhor do que o pedido.** O fio foi até o fim:
> classe **C, acesso não obtido** (o rascunho está pronto e **não enviado**). Mas duas coisas
> desta seção precisam de correção. **(1)** A frase "falha só em F4" já estava proibida aqui,
> e a Fase 12 confirmou o porquê: o padrão-ouro é o contorno de **um** especialista escolhido
> órgão a órgão por um terceiro, e a fonte é **muda** sobre a retenção das séries de A e B —
> pelo caminho A/B/C o iCurveE **não** é dataset interobservador utilizável. **(2)** A
> afirmação desta fase de que a variabilidade humana do esôfago **não é mensurável** ficou
> **parcialmente superada**: o Source Data **aberto** do mesmo artigo contém a concordância
> por caso do próprio esôfago contra uma referência que é um contorno humano — mediana
> **0,7555**, n=493, sob RTOG 1106. Não precisou de acesso nenhum.
> Ver `docs/RELATORIO-FASE12-ICURVEE-ACESSO.md`.

**Por que esta e não outra:** é o **único** ponto do corpus inteiro em que um filtro pode
mudar de estado. Todo o resto está decidido por medição em fonte primária; F4 é o único dos
sete filtros que um pedido pode alterar. Se o acesso for concedido, F6 passa de
indeterminado a medível e a fase pode ser reaberta em A ou fechada em B com procedência
verificada. Se for negado, a negativa fica documentada com a resposta anexa — o que é um
resultado, não um fracasso.

**Fila de manutenção, não próxima ação:** fechar o **D7** (ler `ContentCreatorName` (0070,0084),
`OperatorsName` e `ReviewerName` cruzados por estudo + série alvo, como o D3 já faz com o
`ROIName`) e o tri-estado (linhas 404 e 899). É a manutenção necessária para a próxima
varredura ser confiável **sem** agente lendo tag à mão — mas não muda a classe B.

---

## Apêndice — reprodutibilidade

| Instrumento | O que faz | Autoteste |
|---|---|---|
| [`idc_esofago.py`](scripts/validation/tier2/idc_esofago.py) | a afirmação central sobre o catálogo inteiro, ~10 s | 5 controles de crivo, sem rede |
| [`interobservador.py`](scripts/validation/tier2/interobservador.py) | censo por nome; detecção dentro/entre arquivos; SEG; tri-estado | **11 guardas**, 21 convenções, mutação **21/21** |
| [`concordancia.py`](scripts/validation/tier2/concordancia.py) | concordância par-a-par em mm — **OBJETO = GTV, NÃO ESÔFAGO** | fantoma analítico + g5/g6/g9/g10/g12 |
| [`sobreposicao_uid.py`](scripts/validation/tier2/sobreposicao_uid.py) | sobreposição de UID entre as 156 coleções | — |
| [`fase11/`](scripts/validation/tier2/fase11/) | drivers de uma passada, preservados porque os artefatos que gravam são gitignored | — |

```bash
.venv-pipeline/Scripts/python.exe -m scripts.validation.tier2.idc_esofago
.venv-pipeline/Scripts/python.exe -m scripts.validation.tier2.interobservador --autoteste
.venv-pipeline/Scripts/python.exe -m scripts.validation.tier2.interobservador --mutacao
.venv-pipeline/Scripts/python.exe -m scripts.validation.tier2.concordancia --autoteste
```

**Ambiente:** Python 3.13.11 · `idc-index` 0.12.5 · `idc-index-data` 24.2.2 (IDC v24) ·
`pydicom` conforme `requirements-lock.txt`.

**Um número que mudou na conferência final e vale registrar como aviso de instrumento:**
aplicar `CRIVO_ESOFAGO` sobre o nome **cru** (`'Esophagus'`, com maiúscula) devolve **0** em
vez de 908 — o crivo espera o nome já minúsculo. Um zero silencioso ali inverteria a
conclusão da fase. É por isso que `idc_esofago.py` tem controle negativo de maiúscula no
autoteste.
