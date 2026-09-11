# Fase 29 — Auditoria de Candidatos para TEST

**Data:** 2026-09-10 · **Natureza:** auditoria documental · **Nada baixado, nada treinado**
**Decisão:** **C — não existe TEST externo adequado neste momento**, com recomendação forte de
**D (TEST próprio)**. **A = 0 · B = 0.**

> **Os dois candidatos B herdados da Fase 28 foram REBAIXADOS**, ambos por evidência positiva e
> não por dúvida. **TEST continua 0 e protegido.**

---

## 1. Objetivo

Transformar a descoberta da Fase 28 numa decisão auditável: resolver as evidências pendentes
sobre os candidatos B, reavaliar os C, e documentar com rigor a linhagem do TotalSegmentator
v2 — o modelo que o VRmed usa como `BASELINE_ESOFAGO_V1`.

**Nota de caminho.** O pedido cita `docs/RELATORIO-FASE26-PREREG-BASELINE.md`, que **não
existe**. O pré-registro está em [`BASELINE-ESOPHAGUS-VRMED-V1.md`](BASELINE-ESOPHAGUS-VRMED-V1.md)
com a emenda [V2](BASELINE-ESOPHAGUS-VRMED-V2.md); o relatório da fase é
[`RELATORIO-FASE26-BASELINE.md`](RELATORIO-FASE26-BASELINE.md). Foram lidos os reais.

---

## 2. Estado herdado da Fase 28

| | |
|---|---|
| A | 0 |
| B | 2 — StructSeg 2019 Task 3, Pediatric-CT-SEG |
| C | 3 — RTOG-0617, RADCURE, TROTS |
| TEST | **0** |
| `sha256_manifesto` | `9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192` |

---

## 3. Critério formal de aprovação A

Implementado em [`fase29/decisao.py`](../scripts/validation/fase29/decisao.py) e **reaplicado**
por [`test_fase29_auditoria_test.py`](../tests/test_fase29_auditoria_test.py).

A Fase 28 tratava independência como campo único. Isso **diluía o próprio buraco que ela
descobriu**. A Fase 29 decompõe em **cinco eixos**, cada um com veredito próprio:

| eixo | pergunta |
|---|---|
| `imagem` | as imagens são outras? |
| `exame` | os estudos/séries são outros? |
| `instituicao` | a origem é outra? |
| `anotacao` | quem anotou não anotou o nosso dado? |
| `linhagem_anotacao` | o **rótulo** não descende de modelo que tocou o nosso pipeline? |

**A exige os cinco em `DEMONSTRADA`**, mais ontologia `COMPATIVEL`, anotação humana documentada,
acesso viável e licença não bloqueante — sem overlap detectado, sem conflito metodológico
crítico, e sem estar na lista de proibidos. `PLAUSIVEL` **não basta**; *"não detectado"* **nunca
vira** `DEMONSTRADA`.

---

## 4. 29A — StructSeg 2019 Task 3

### 4.1 Identificação
Thoracic OAR, 60 pacientes (50 com GT público), Cancer Hospital of UCAS = Zhejiang Cancer
Hospital. Página oficial `structseg2019.grand-challenge.org`. **Sem DOI.**

### 4.2 Imagens
**DEMONSTRADO:** 50 CT de tórax de adultos com câncer de pulmão, scanner único Philips Brilliance
Big Bore, 512×512×80–127, **z = 3,0–5,0 mm** — grosseiro para uma estrutura fina como o esôfago.

### 4.3 Máscaras — **bloqueador técnico**
`.nii.gz` multiclasse 1..6, mas a **ordem das classes está em conflito não resolvido**: a página
oficial e uma equipe participante dizem `4 = esôfago`; um README de terceiro e inferência
volumétrica dizem outra ordem. **Só se resolve medindo volumes no próprio dado — que não se tem.**

### 4.4 Ontologia — **PARCIAL**
Sem atlas, sem limite cranio-caudal, sem convenção parede/lúmen. Esôfago = convenção local.

### 4.5 Anotação
**Fonte primária, literal:** *"Each CT scan is annotated by one experienced oncologist and
verified by another one."* Design doc 2020: *"All annotations are from actual radiation therapy
plans following clinical practice."* **Merge de múltiplas anotações: "None."**

### 4.6 Revisão
Declarada (2º oncologista), mas **não demonstrada quantitativamente** — sem kappa, sem Dice
interobservador. Organizadores foram perguntados no formulário BIAS e **não responderam**.

### 4.7 Licença — **UNKNOWN, com sinal restritivo**
Nenhum texto de licença publicado para 2019. O único sinal documental dos organizadores é o
*challenge design document* do StructSeg **2020** (Zenodo `10.5281/zenodo.3718885`), campo *"Data
usage agreement"*: **"CC BY NC SA."** — não-comercial **e** ShareAlike. Não demonstrado que se
aplique retroativamente a 2019. E um repositório de terceiro que teve os dados declara que eles
*"can not be publicly posted, or distributed to anyone outside of this project."*

### 4.8 Acesso — **BLOQUEADO, e isso é DEMONSTRADO**
`/Download/` devolve **HTTP 403** para não autenticado; `structseg-challenge.org` e `www.*` são
**NXDOMAIN** (reverificado 2026-09-10). Conjunto de teste nunca liberado; servidor de avaliação
extinto.

### 4.9 Instituições
**DEMONSTRADA** disjunção em relação a LCTSC (MAASTRO/MDACC/MSKCC), 4D-Lung (VCU) e Basel.

### 4.10 Overlap — **RISCO CONFIRMADO por outra via**
Os 50 casos públicos aparecem como **dado de TREINO** em modelos de fundação: **Hermes**
(arXiv 2306.02416, split 75/5/20) e **Iris** (arXiv 2503.19359, Tab. 5). SAT-DS e SA-Med2D-20M
verificados **negativos**.

### 4.11 Independência (cinco eixos)
`imagem` PLAUSÍVEL · `exame` INCONCLUSIVO · `instituicao` **DEMONSTRADA** · `anotacao`
INCONCLUSIVO · `linhagem_anotacao` INCONCLUSIVO.

### 4.12 Decisão — **D**
Rebaixado de B. Três bloqueadores independentes: **acesso demonstradamente indisponível**,
**licença UNKNOWN com sinal NC/SA**, e **ordem de classes irresolvível sem o dado**.

*Divergência registrada:* a investigação recomendou **E**, o cético **D**. Adotei **D** — não é
"já utilizado/conflitante", é "não utilizável". A remediação única seria contato com os
organizadores, **não executado** (enviar mensagem em nome do usuário exige autorização explícita,
e a regra 14 proíbe fabricar contato ou resposta).

---

## 5. 29B — Pediatric-CT-SEG

### 5.1 Identificação
TCIA, DOI `10.7937/TCIA.X0H0-1706`; artigo Jordan et al., Med Phys 2022 (`10.1002/mp.15485`).
359 pacientes, **5 dias a 16 anos** (mediana 6), 718 séries, 65,69 GB, Children's Wisconsin.

### 5.2 Imagens
**DEMONSTRADO.** 3 scanners, 110.442 imagens.

### 5.3 Máscaras
RTSTRUCT DICOM, **"Esophagus" em 353 dos 359**. Exige **rasterização** — penalizante em estrutura
fina. A **v1 tinha 103 séries com RTSTRUCT duplicado**; é preciso fixar a **v2 (2022-03-31)**.

### 5.4 Ontologia — **PARCIAL**
**Nenhum atlas ou guideline de contorno (RTOG etc.) é citado.**

### 5.5 Anotação
*"Four expert medical analysts retrospectively and manually contoured 25 structures … using the
ProKnow contouring software"*; pulmão, pele e osso foram semiautomáticos (Eclipse
SmartSegmentation + correção).

**Mas que o esôfago esteja entre as 25 manuais é ARITMÉTICA do investigador** (29 − 4 = 25). O
artigo diz *"up to 29"* e **nunca lista quais 25**. Logo: **PLAUSÍVEL, não demonstrado.**

### 5.6 Revisão
*"A quality assurance (QA) review was performed by a board-certified radiation oncologist"* —
agradecimento nominal. **Sem métrica de concordância.**

### 5.7 Licença — **CC BY 4.0**
Campo oficial da coleção no TCIA. Confiança média-alta: **o artigo não enuncia licença**.

### 5.8 Acesso — **ABERTO**, direto, sem DUA restritivo. Espelho no IDC.

### 5.9 Instituições
Children's Wisconsin (+ Marquette, MCW, Varian, Stanford).

### 5.10 Overlap
Overlap de paciente **implausível** (disjunção por idade). Mas **contaminação por PESOS em
aberto**: existem pesos pediátricos treinados **neste próprio dataset** (Adamson V-Net com
299/359; nnU-Net pediátrico; UM2ii; PSAT).

### 5.11 Independência
`imagem` **DEMONSTRADA** · `exame` **DEMONSTRADA** · `instituicao` INCONCLUSIVO · `anotacao`
INCONCLUSIVO (analistas não nominados) · `linhagem_anotacao` **DEMONSTRADA** para o esôfago.

### 5.12 Decisão — **C**, condicional

**A pergunta central não era licença — era se ele é teste válido para esôfago ADULTO. E a
resposta é NÃO, refutada por evidência positiva:**

| | |
|---|---|
| modelo adulto neste dataset | **DSC 0,47 ± 0,18** (val) e **0,48 ± 0,24** (test) no esôfago |
| teto *in-domain* do próprio dataset | **0,70** |

**Uso condicional autorizado:** bancada de análise de *domain shift*. **Nunca** TEST de esôfago
adulto. Não foi promovido só por ter licença aberta.

---

## 6. 29C — RTOG-0617 / RADCURE / TROTS

### RADCURE — **C**
**Achado duro, verificado em fonte primária:** o CSV oficial
`RADCURE_OAR_contour_mapping_v04_20241219.csv` tem **3.337 linhas** e a coluna de esôfago
preenchida em **2.708** (`ESOPHAGUS` 2654 · `OESOPHAGUS` 27 · `esophagus` 19 · `Esophagus` 7 ·
`EESOPHAGUS` 1; 629 vazias). Nomenclatura heterogênea → exige harmonização TG-263.

**Mas:** é coorte de **cabeça-pescoço** (cobre esôfago cervical/torácico alto, não o órgão
inteiro); acesso sob **NIH Controlled Data Access**; e o **overlap é DEMONSTRADO** — o TCIA
declara que RADCURE *"replaces the OPC-Radiomics dataset"* (603 pacientes, 419 com esôfago, que
circularam anos como coleção separada), e **RADCURE é corpus de treino** de modelos públicos de
auto-segmentação de 19 OARs incluindo esôfago.

### NSCLC-Cetuximab / RTOG-0617 — **C**
A pergunta que decide continua **em aberto**: **não foi demonstrado que existe contorno de
esôfago nos RTSTRUCT**. Acesso sob NIH Controlled Data Access (dbGaP/DUA, não redistribuível).
É, porém, **a única coorte do lote com a população certa** — adultos com NSCLC.

### TROTS — **D**
Licença CC BY, mas **sem utilidade**: estruturas embutidas em Matlab/HDF5 como conjuntos de
voxels amostrados para otimização de dose, **não máscara de imagem**; protocolos são
próstata/cabeça-pescoço/fígado. Quem delineou não é descrito.

---

## 7. 29D — Linhagem do TotalSegmentator v2

**Esta é a frente crítica, e o vocabulário aqui é deliberadamente restritivo.**

### 7.1 O que é DEMONSTRADO

**(a) As imagens do v1 vieram do PACS de Basel.** *"we randomly sampled CT images from our PACS"*
— arXiv:2208.05868 §2.1.

**(b) O esôfago do v1 foi PRÉ-SEGMENTADO por modelos treinados em BTCV e SegTHOR.** Material
Suplementar A, *"List of pretrained models used during data annotation"*, lista **Task 17
(Multi-Atlas Beyond the Cranial Vault / BTCV)** com classes incluindo `esophagus`, e **Task 55
(SegTHOR)** com classes *"aorta, esophagus, heart, trachea"*.

**(c) Como foram usados.** Versão publicada: *"If an existing model for a given structure was
publicly available (Appendix S2), that model was used to create a first segmentation, which was
then validated and refined manually."* **68 das 104 classes** receberam primeira segmentação
automática — **o esôfago entre elas**; 36 foram segmentadas manualmente do zero.

**(d) Houve refino humano, iterativo.** nnU-Net preliminar após 5 pacientes, retreino após 5, 20,
100 e 1000 sujeitos; todos os 1204 exames revisados; supervisão por **dois médicos com 3 e 6 anos
de experiência em body imaging**.

### 7.2 O que NÃO é demonstrado — e não pode ser afirmado

**Não há evidência de contaminação de IMAGENS.** O suplemento descreve uso de **modelos**
treinados em BTCV/SegTHOR, **não das imagens**. Afirmar overlap de imagem seria inventar.

**Para o v2, a documentação é INCONCLUSIVA.** Não existe artigo revisado por pares nem model card
do v2 — só `resources/improvements_in_v2.md` e o CHANGELOG. As imagens de treino foram de
**1139 para 1559**, e *"we did not publish the additional subjects we used for TotalSegmentator
v2 training"*. A origem das adicionais é *"more images from GE scanners and other institutions"*
— **não rastreável**.

**Que o esôfago do v2 descenda das mesmas sementes é PLAUSÍVEL, não demonstrado** — o changelog
não lista o esôfago entre as classes reanotadas e declara *"same subjects as in v1 for training
and validation"*, mas não há documentação v2-específica do processo.

**Patient overlap é NÃO VERIFICÁVEL** — nenhum identificador de paciente ou exame é publicado.

### 7.3 As quatro distinções, separadas

| conceito | o que é | estado aqui |
|---|---|---|
| **image overlap** | os mesmos pixels nos dois conjuntos | **NÃO DEMONSTRADO** entre TS e BTCV/SegTHOR |
| **patient overlap** | o mesmo paciente, talvez outro exame | **NÃO VERIFICÁVEL** — sem identificadores |
| **annotation lineage overlap** | o rótulo foi produzido por modelo treinado nos rótulos de outro dataset | **DEMONSTRADO** para o esôfago do v1 |
| **model-derived annotation dependence** | o próprio GT é (em parte) saída de modelo | **DEMONSTRADO** — 68/104 classes, esôfago entre elas |

### 7.4 O que PODE e o que NÃO PODE ser concluído para o VRmed

**PODE:**

1. **SegTHOR e BTCV não podem servir de TEST** para um pipeline cujo baseline de comparação é o
   TotalSegmentator — o rótulo do baseline **descende deles**. Isso reforça, por via
   independente, a proibição que o projeto já tinha sobre o SegTHOR.
2. **O GT do TotalSegmentator não é anotação humana de novo** para o esôfago. Chamá-lo de "GT
   humano" seria falso.

**NÃO PODE:**

3. Afirmar que qualquer dataset **compartilha imagens** com o TotalSegmentator.
4. Afirmar que o esôfago do **v2** está contaminado — ou que está limpo. É **INCONCLUSIVO**.
5. Usar o artigo do **v1** para afirmar qualquer coisa sobre o **v2**.

**Uma distinção que protege o projeto e vale explicitar:** o modelo próprio do VRmed (Fase 26B)
foi treinado nas máscaras RTSTRUCT do 4D-Lung, **não em saída do TotalSegmentator**. A
dependência de linhagem descrita aqui afeta **o baseline de comparação**, não o treino do modelo
do VRmed.

---

## 8. Matriz comparativa final

| Candidato | Imagem | Máscara | Licença | Acesso | Ontologia | Anotação humana | Revisão | Instituição | Indep. de exame | Indep. de anotação | Overlap | Adequação ao adulto | Status | Pendências |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **StructSeg 2019 T3** | 50 CT tórax, z 3–5 mm | .nii.gz, **ordem de classes em conflito** | **UNKNOWN** (sinal NC/SA) | **BLOQUEADO** (403 / NXDOMAIN) | PARCIAL | declarada, não demonstrada | declarada, sem métrica | DEMONSTRADA | INCONCLUSIVO | INCONCLUSIVO | **treino de Hermes e Iris** | sim, mas z grosseiro | **D** | acesso, licença, ordem de classes |
| **Pediatric-CT-SEG** | 359 pac., 5 d–16 a | RTSTRUCT, esôfago em 353 | **CC BY 4.0** | **ABERTO** | PARCIAL | **PLAUSÍVEL** (aritmética) | QA por radio-onc. | INCONCLUSIVO | DEMONSTRADA | INCONCLUSIVO | pesos treinados nele | **NÃO — DSC 0,47** | **C** | ROI Names; fixar v2; inventário de pesos |
| **RADCURE** | 3.337 (H&N) | **2.708 com esôfago** (CSV oficial) | RESTRITA | DUA | UNKNOWN | clínica, QA semanal | rounds de QA | DEMONSTRADA | INCONCLUSIVO | INCONCLUSIVO | **superset de OPC-Radiomics; é corpus de treino** | parcial (H&N) | **C** | extensão real; excluir OPC-* |
| **RTOG-0617** | 490 NSCLC | **existência não demonstrada** | RESTRITA | DUA | UNKNOWN | UNKNOWN | UNKNOWN | INCONCLUSIVO | INCONCLUSIVO | INCONCLUSIVO | INCONCLUSIVO | **SIM** | **C** | confirmar contorno de esôfago |
| **TROTS** | 120, não torácico | Matlab/HDF5, não é máscara | CC BY | ABERTO | **INCOMPATÍVEL** | UNKNOWN | UNKNOWN | DEMONSTRADA | INCONCLUSIVO | INCONCLUSIVO | INCONCLUSIVO | protocolos errados | **D** | — |

**A = 0 · B = 0 · C = 3 · D = 2 · E = 0**

---

## 9. Decisão sobre TEST

### **C — Não existe TEST externo adequado neste momento.**

Com **recomendação forte de D (TEST próprio)**.

**Por que não é B.** A Fase 28 entregou dois candidatos B. **Os dois caíram**, e nenhum por
falta de pesquisa:

- **StructSeg** caiu por **acesso demonstradamente indisponível** — não é pendência de
  evidência, é impossibilidade material.
- **Pediatric-CT-SEG** caiu por **evidência positiva contrária**: DSC 0,47 de um modelo adulto
  no esôfago daquele dataset. Não é dúvida; é medição.

Restam três C, e nenhum deles é um TEST — são materiais de uso condicional com pendências que
exigem acesso controlado ou harmonização pesada.

**TEST permanece 0 e protegido por `AcessoIndevido`.**

---

## 10. Riscos e pendências

| # | Risco / pendência | Estado |
|---|---|---|
| 1 | linhagem de anotação do **v2** | **INCONCLUSIVA** — sem artigo, model card ou lista por caso |
| 2 | os **~420 sujeitos adicionais** do treino v2 | **não publicados** |
| 3 | nenhum candidato tem os **cinco eixos** demonstrados | zero de cinco em três deles |
| 4 | contaminação por **pesos de fundação** | vetor novo: StructSeg em Hermes/Iris, Pediatric-CT-SEG em modelos pediátricos |
| 5 | contato com organizadores | **não executado** — exige autorização explícita do usuário |
| 6 | truncamento nas sínteses | **erro meu** (corte de JSON); dossiês recuperados do journal e reclassificados |

---

## 11. Próxima fase recomendada

**Fase 30 — viabilidade de um TEST próprio**, e não mais busca externa.

A busca externa já rendeu o que tinha a render: **33 datasets na Fase 28, 5 auditados a fundo na
29, zero aprovados**. O gargalo não é falta de procura — é que os poucos torácicos com esôfago
estão gastos, bloqueados ou contaminados, e o eixo de linhagem de anotação não fecha para
ninguém.

O que a Fase 30 deveria comparar, com números:

1. **custo de um TEST próprio** — quantos casos, de que fonte pública ainda não usada, anotados
   sob a `ESOPHAGUS_ONTOLOGY_V1` por quem e a que custo;
2. **contra o custo de destravar um externo** — os três C exigem DUA, harmonização ou contato;
3. **e a pergunta anterior a ambas:** com TRAIN = 10, um TEST externo mudaria alguma conclusão
   defensável? Ou o gargalo real é o **n do treino**, e não a ausência de TEST?

**Duas ações baratas que podem ser feitas antes**, e que não exigem download nem dinheiro:
abrir os ROI Names de um RTSTRUCT v2 do Pediatric-CT-SEG (minutos, fecha "esôfago é manual"), e
confirmar se o RTOG-0617 tem contorno de esôfago (decide se vale pedir acesso).
