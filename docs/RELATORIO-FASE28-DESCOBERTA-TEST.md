# Fase 28 — descoberta e auditoria de candidato a TEST independente

**Data:** 2026-09-10 · **Natureza:** pesquisa e auditoria · **Nada foi baixado, nada treinado**
**Resultado:** **NENHUM CANDIDATO FORTE. A = 0.**

> Este é o desfecho correto, não uma falha da pesquisa. **TEST continua 0.**

---

## 1. Objetivo e o que a fase NÃO fez

Descobrir, auditar e classificar candidatos públicos a TEST externo independente para
**esôfago como órgão em CT torácica**.

**Não** treinou, **não** rodou inferência, **não** mediu Dice, **não** baixou dataset,
**não** tocou no manifesto, no snapshot, no split ou no TEST.

---

## 2. Metodologia

**50 fichas** pesquisadas por 6 frentes paralelas, consolidadas em **33 datasets distintos**;
depois **8 análises adversariais** sobre os mais promissores.

| Frente | Escopo |
|---|---|
| já problemáticos | LCTSC, LyNoS, NSCLC-Radiomics, SegTHOR — para atualizar ficha, não promover |
| OAR torácico | StructSeg, SegRap, coleções TCIA de NSCLC com RTSTRUCT, RTOG-0617 |
| multi-órgão | TotalSegmentator, AMOS, WORD, AbdomenCT-1K, FLARE, SAROS, autoPET, CT-ORG, MSD |
| esôfago específico | TCGA-ESCA, Zenodo, PhysioNet, grand-challenge |
| busca aberta | TCIA browser, Zenodo, Synapse, Figshare, revisões recentes |
| **proveniência do TotalSegmentator** | o que treinou o modelo que o VRmed usa como baseline |

Regra imposta a todas: **fonte primária ou UNKNOWN**. *"O artigo diz expert"* não é evidência
de anotação humana. **85 becos sem saída** foram registrados como `nao_encontrado`.

**Incidente de método, registrado.** A primeira síntese leu **10 das 50 fichas** porque eu
truncei o JSON de entrada em 45 KB. A própria síntese detectou e declarou o truncamento em vez
de preencher a tabela com linhas inventadas. As 50 foram recuperadas do journal e
reclassificadas. **O erro foi meu, e a instrumentação o pegou.**

---

## 3. O achado central — por que nenhum candidato pode chegar a A hoje

**FATO.** O baseline do projeto é **TotalSegmentator 2.18.0** — pesos **v2**, verificado no
ambiente instalado.

Boa parte da "evidência positiva de independência" que a pesquisa produziu se apoia numa frase
do artigo do TotalSegmentator **v1**: os 1204 exames de treino teriam sido *amostrados
aleatoriamente do PACS do University Hospital Basel*. Se isso valesse, nenhum dataset público
teria entrado no treino, e o eixo de independência estaria resolvido para todos.

**Só que é a versão errada.** O projeto não usa v1. E para a v2 **não existe lista de datasets
de treino por caso**.

**E há um segundo problema, pior, que nenhuma sonda de imagem detecta.** O suplemento do
TotalSegmentator declara que modelos pré-treinados foram usados para gerar a **primeira**
segmentação do conjunto de treino — e para o esôfago os modelos nomeados são **BTCV (Task 17)
e SegTHOR (Task 55)**.

**INFERÊNCIA — e é a conclusão estrutural da fase.** O rótulo de esôfago do baseline do VRmed
**descende de SegTHOR**. Isso é **dependência de anotação**, não sobreposição de imagem:
nenhuma comparação de `PatientID`, `StudyInstanceUID`, `SeriesInstanceUID` ou `sha256`
conseguiria detectá-la, porque não há imagem em comum — há **linhagem de rótulo** em comum.

Consequência prática: o eixo **independência** fica **INCONCLUSIVO para todo candidato**, e
isso sozinho **limita todos a B**. Não é pessimismo — é a aplicação da regra que o projeto
carrega desde a Fase 18: *"não detectado" nunca é "independência demonstrada"*.

---

## 4. Tabela comparativa — 33 datasets

| candidato | sujeitos | licença | anotação | ontologia | overlap | independência | status |
|---|---|---|---|---|---|---|---|
| **StructSeg 2019 · Task 3** | 60 (50 GT) | **UNKNOWN** | HUMANA_REVISADA | **UNKNOWN** | não detectado | INCONCLUSIVA | **B** |
| **Pediatric-CT-SEG** | 359 | CC BY 4.0 | HUMANA_MANUAL | **UNKNOWN** | não detectado | INCONCLUSIVA | **B** |
| NSCLC-Cetuximab / RTOG-0617 | 490 | RESTRITA | UNKNOWN | UNKNOWN | n/a | INCONCLUSIVA | C |
| RADCURE | 3346 | RESTRITA | UNKNOWN | UNKNOWN | n/a | INCONCLUSIVA | C |
| TROTS | 120 | CC BY | UNKNOWN | UNKNOWN | n/a | INCONCLUSIVA | C |
| SegRap 2023 | 200 | CONFLITO | UNKNOWN | **INCOMPATÍVEL** | n/a | INCONCLUSIVA | D |
| HaN-Seg | 42 | **SEM DERIVADAS** | HUMANA_REVISADA | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| OpenKBP | 340 | UNKNOWN | UNKNOWN | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| AMOS 2022 | 600 | CC BY 4.0 | UNKNOWN | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| WORD | 150 | CONFLITO | HUMANA_MANUAL | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| AbdomenCT-1K | 1112 | CONFLITO | SEMIAUTOMÁTICA | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| FLARE 2022 | 2300 | CONFLITO | SEMIAUTOMÁTICA | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| FLARE 2023 | 4000+ | UNKNOWN | **DERIVADA DE MODELO** | INCOMPATÍVEL | derivado | REFUTADA | D |
| AbdomenAtlas 1.1 | 9262 | NÃO COMERCIAL | SEMIAUTOMÁTICA | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| Multi-organ Abdominal CT Ref. | 90 | CC BY | HUMANA_REVISADA | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| Learn2Reg Abdomen CT-CT | — | UNKNOWN | UNKNOWN | INCOMPATÍVEL | n/a | INCONCLUSIVA | D |
| SAROS | 900 | CC BY | SEMIAUTOMÁTICA | **sem esôfago** | **DETECTADO** | INCONCLUSIVA | D |
| autoPET | 1014 | CC BY | HUMANA_MANUAL | **sem esôfago** | n/a | INCONCLUSIVA | D |
| CT-ORG | 140 | CC BY | SEMIAUTOMÁTICA | **sem esôfago** | n/a | INCONCLUSIVA | D |
| Medical Segmentation Decathlon | 2633 | UNKNOWN | UNKNOWN | **sem esôfago** | n/a | INCONCLUSIVA | D |
| TCGA-ESCA | — | CC BY | UNKNOWN | **sem máscara** | n/a | INCONCLUSIVA | D |
| CMB-GEC | — | CC BY | UNKNOWN | **sem esôfago** | n/a | INCONCLUSIVA | D |
| VAREPOP-APOLLO | — | CC BY | UNKNOWN | **sem esôfago** | n/a | INCONCLUSIVA | D |
| **4D-Lung** | 16 | CC BY 3.0 | SEMIAUTOMÁTICA | compatível | **IDENTIDADE** | n/a | **E** |
| **LCTSC** | 60 | CC BY 3.0 | HUMANA_REVISADA | compatível | **já em uso** | INCONCLUSIVA | **E** |
| **NSCLC-Radiomics** | 422 | **CC BY-NC** | UNKNOWN | divergente | **DETECTADO** | INCONCLUSIVA | **E** |
| **LyNoS** | 15 | CC BY 4.0 | UNKNOWN | UNKNOWN | **DETECTADO (hash)** | INCONCLUSIVA | **E** |
| **SegTHOR** | 60 | **UNKNOWN** | HUMANA_MANUAL | parcial | vetor | INCONCLUSIVA | **E** |
| **TotalSegmentator (Zenodo)** | 1228 | CC BY 4.0 | SEMIAUTOMÁTICA | UNKNOWN | **IDENTIDADE** | **REFUTADA** | **E** |
| BTCV | 30–50 | UNKNOWN | HUMANA_REVISADA | INCOMPATÍVEL | **derivado** | REFUTADA | E |
| CADS-dataset | — | CONFLITO | DERIVADA DE MODELO | UNKNOWN | derivado | REFUTADA | E |
| NLST organ segmentation | — | CC BY | DERIVADA DE MODELO | UNKNOWN | derivado | REFUTADA | E |
| Generalizable CBCT Esophagus | — | CC BY | DERIVADA DE MODELO | INCOMPATÍVEL | n/a | INCONCLUSIVA | E |

**A = 0 · B = 2 · C = 3 · D = 18 · E = 10**

---

## 5. Os quatro já proibidos — motivo documentado, não reavaliação

| dataset | motivo, além da proibição de projeto |
|---|---|
| **LCTSC** | já é **"validação — já em uso"** (`VRMED-DATASET-MATRIX.md`), medido nas Fases 6, 7, 10, 11, 21 e 22. E a Fase 16 **bane literalmente** a frase *"O LCTSC é conjunto de teste independente"* |
| **NSCLC-Radiomics** | **CC BY-NC 3.0** (bloqueio jurídico duro); compartilha **MAASTRO** com o LCTSC; e há anotações de esôfago **geradas por IA** publicadas no IDC / Zenodo 7975081 |
| **LyNoS** | **overlap de imagem provado por hash**: 15/15 byte-a-byte idênticos ao AeroPath, e os mesmos volumes circulam em ≥4 embalagens. A anotação "manual" consta só num README de GitHub |
| **SegTHOR** | licença **sem texto primário recuperável**; GT público só em 40 de 60; e é **vetor de contaminação** — nnU-Net Task055 treinado nele gerou máscaras de esôfago de terceiros |

### 5.1 O desacordo entre céticos, e como foi resolvido

**Dois céticos discordaram sobre o LCTSC**: um recomendou **A**, outro **B** com objeções
fatais. O segundo está certo, e por três razões verificadas por mim no repositório:

1. o LCTSC **já está em uso** como validação, com split congelado;
2. a Fase 16 tem uma lista de **frases proibidas** e essa é a primeira delas;
3. a "evidência positiva" do primeiro cético é sobre o **TotalSegmentator v1** — e o baseline
   do projeto é **2.18.0**.

**O primeiro cético respondeu bem a uma pergunta que não era a da fase.** Suas correções
factuais são valiosas e ficam registradas — o mapeamento S1=MAASTRO / S2=MDACC / S3=MSKCC
está publicado (`10.1002/mp.14107`), os limites craniocaudais **estão** na página do TCIA, e o
RTOG 1106 manda contornar até a adventícia gordurosa, o que resolve "parede vs lúmen" como
sólido. Nada disso reverte uma proibição de projeto.

---

## 6. Os dois candidatos B

### 6.1 StructSeg 2019 · Task 3 — o melhor candidato torácico

**A favor (FATO).** Único do lote com **esôfago em CT torácica** de pacientes de câncer de
pulmão. A página oficial declara: cada CT anotado por **um oncologista experiente e verificado
por um segundo**. Disjunção institucional positiva — Zhejiang Cancer Hospital, distinto de VCU
(4D-Lung) e de Basel (TotalSegmentator).

**Pendências que impedem A:**

| # | Pendência | O que faltaria |
|---|---|---|
| 1 | **licença UNKNOWN** | nenhum texto de licença publicado — só os ToS genéricos da plataforma. Precisa de declaração explícita do detentor |
| 2 | **ontologia UNKNOWN** | não declara onde o esôfago começa/termina, nem parede vs lúmen, nem atlas. Sem isso não dá para saber se mede a mesma coisa que a `ESOPHAGUS_ONTOLOGY_V1` |
| 3 | **acesso incerto** | desafio encerrado em 2019; a própria home admite *"results site (under repair)"* |
| 4 | independência | INCONCLUSIVA, como todos (§3) |

### 6.2 Pediatric-CT-SEG — o melhor em licença e anotação

**A favor (FATO).** Único que reúne **CC BY 4.0**, **RTSTRUCT**, **anotação humana manual** e
**download direto** — 359 sujeitos, DOI `10.7937/TCIA.X0H0-1706`.

**Pendências que impedem A:**

| # | Pendência | Gravidade |
|---|---|---|
| 1 | **população pediátrica** (5 dias a 16 anos) | **grave** — o pool de treino é adulto com NSCLC; calibre e anatomia do esôfago são outros |
| 2 | **ontologia UNKNOWN** | protocolo de contorno não verificado |
| 3 | reamostragem para 2,0 mm antes do contorno | afeta a comparabilidade geométrica |
| 4 | independência | INCONCLUSIVA (§3) |

**INFERÊNCIA.** Mesmo que licença e ontologia fossem resolvidas, avaliar aqui mediria
**transferência para outra população**, que é uma pergunta legítima mas **diferente** de
"o modelo funciona no domínio para o qual foi treinado".

---

## 7. Análise adversarial

Sete perguntas fixas por candidato promissor, em 8 execuções independentes:

1. Como poderia se relacionar ao 4D-Lung? 2. Ao treino do TotalSegmentator? 3. Poderia
compartilhar casos sem UID? 4. A máscara poderia vir de modelo? 5. O artigo diz "expert" sem
provar quem anotou? 6. A licença permite nosso uso? 7. A ontologia coincide de fato?

**Nenhum candidato sobreviveu às sete.** Os padrões que mais derrubaram:

- **re-publicação sob outro nome** — LyNoS/AeroPath são o mesmo dado em ≥4 embalagens, e
  nenhum identificador denuncia isso;
- **contaminação de rótulo por modelo** — SegTHOR → TotalSegmentator → NSCLC-Radiomics (IDC),
  uma cadeia que atravessa três datasets sem compartilhar uma única imagem;
- **"expert" sem substância** — a palavra aparece; quem anotou, quantos, e com que revisão,
  não.

---

## 8. Testes

**`tests/test_fase28_test_discovery.py` — 11/11.** E a parte que importa: a regra do status A
virou **código**, não parágrafo.

| # | O que trava |
|---|---|
| 01–04 | manifesto, snapshot, split e TEST=0 **inalterados**, com controle negativo |
| 05 | nenhum candidato entrou no manifesto; `source_dataset` continua só `4D-Lung (TCIA)` |
| 07 | **A exige evidência positiva nos quatro eixos** — reaplica a regra sobre o JSON gerado |
| **08** | **controle positivo:** um candidato sintético que cumpre tudo **tem de poder** ser A — senão a regra estaria só proibindo tudo |
| **09** | **controle negativo:** cada eixo quebrado sozinho (11 variações) **tem de** impedir o A |
| 10 | relação INCONCLUSIVA com o TotalSegmentator **nunca** vira independência DEMONSTRÁVEL |
| 11 | os quatro proibidos não podem virar A |

`fase28/classificar.py` (5 autotestes) **rebaixa automaticamente** qualquer A sem os quatro
eixos, e registra o rebaixamento — em vez de confiar em quem preencheu a ficha.

**Suíte completa: 110/110 nos arquivos de teste · 220/220 nos autotestes de módulo.**

---

## 9. Conclusão

**Nenhum candidato forte. A = 0. TEST continua 0.**

A razão não é falta de datasets — são 33 auditados, vários com licença aberta e milhares de
sujeitos. A razão é **estrutural**:

1. **O eixo de independência não fecha para ninguém**, porque o TotalSegmentator v2 não publica
   lista de treino por caso, e o rótulo de esôfago dele descende de SegTHOR e BTCV. Isso é
   dependência de **anotação**, invisível a qualquer sonda de imagem.
2. **Quase todo dataset multi-órgão é abdominal ou de cabeça-pescoço** — o esôfago aparece só
   nas pontas, fora do que o VRmed audita.
3. **Os torácicos com esôfago são poucos, e os quatro melhores já estão gastos** — usados,
   proibidos, ou contaminados.

**Melhor candidato atual: StructSeg 2019 · Task 3.** Para subir a A precisaria de: texto de
licença explícito; protocolo de contorno declarado (limites craniocaudais e parede/lúmen); e
confirmação de que o download ainda existe. Os três são **verificáveis por contato com os
organizadores** — nenhum exige dinheiro nem download.

---

## 10. É seguro ir para uma Fase 29 de aquisição?

**Não como aquisição. Sim como resolução de pendências, sem baixar nada.**

| # | O que a Fase 29 poderia fazer sem risco |
|---|---|
| 1 | contatar os organizadores do StructSeg pedindo **licença e protocolo de contorno por escrito** |
| 2 | verificar se o **RTOG-0617** tem contorno de esôfago (hoje UNKNOWN) — resolve um C |
| 3 | mapear a **cadeia de linhagem de rótulo** do TotalSegmentator v2, se houver documentação |
| 4 | avaliar formalmente se um TEST **próprio**, anotado sob a `ESOPHAGUS_ONTOLOGY_V1`, sai mais barato que auditar um externo |

**O que a Fase 29 NÃO deve fazer:** baixar StructSeg ou Pediatric-CT-SEG antes de licença e
ontologia resolvidas, e **promover qualquer coisa a TEST** sem os quatro eixos.

> **É preferível concluir "não temos TEST" do que promover um conjunto duvidoso só para obter
> uma métrica externa.** É essa a conclusão, e ela é o resultado da fase — não a ausência dele.
