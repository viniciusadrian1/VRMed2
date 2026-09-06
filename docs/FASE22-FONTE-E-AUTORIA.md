# Fase 22 — fontes consultadas e autoria do ground truth do LCTSC

2026-09-06 · 5 arms de fonte primária · 5 passes céticos

---

## 1. Autoria do GT — o que as fontes dizem, e o que elas não dizem

| Papel | Resposta | Evidência |
|---|---|---|
| **AUTOR** (do artigo) | Yang J. et al., *Medical Physics* 2018; e o artigo de descrição de dados, Yang et al. 2020 | fontes primárias abertas |
| **ANOTADOR** (do contorno) | **UNKNOWN** | O GT são **contornos clínicos de rotina**, colhidos retrospectivamente dos planos de tratamento de **três serviços**. *"The manual contours that were used in clinic for treatment planning were used as ground 'truth.'"* Nenhuma fonte diz quantas pessoas os desenharam |
| **quantos anotadores** | **UNKNOWN** para as 60 séries | **Não confundir** com o único número publicado: o sub-estudo de variabilidade de **3 casos**, recontornados por **três dos autores** (MG, GS, JY). Isso é outra coisa |
| **especialidade** | **UNKNOWN** para os anotadores do GT | A única especialidade declarada em toda a cadeia é a do **revisor de QA** |
| **REVISOR** | **UM**, identificado por iniciais (GS), organizador do desafio, **físico médico clínico** | *"The clinical contours from all institutions were quality checked prior to making data available, by one of the challenge organizers (GS)"* e *"All contours were reviewed (and edited if necessary) to ensure consistency across the 60 patients using the RTOG 1106 contouring atlas."* |
| **CONSENSO** | **NÃO houve** para o GT das 60 séries | nenhuma fonte descreve adjudicação ou consenso multi-leitor no GT |
| **ADJUDICAÇÃO** | **UNKNOWN / não descrita** | — |
| **EDITOR** | o mesmo revisor de QA — a revisão incluía **editar** | *"(and edited if necessary)"* |
| **SOFTWARE** | **UNKNOWN** para a contornagem (sistemas de planejamento clínicos das três instituições, não nomeados). `Plastimatch` e `MIM Software` aparecem como `Manufacturer` nos RTSTRUCT — é quem **escreveu o arquivo** | medido nos 60 arquivos |
| **HUMANO ou MODELO** | **HUMANO.** Contornos manuais clínicos usados em tratamento real | *"manual contours"*, repetido. Nenhuma menção a autossegmentação na produção do GT |

### 1.1 Confirmado no arquivo, não só no artigo

Abertos os **60 RTSTRUCT** (primeira vez em 22 fases):

| Campo | Valor |
|---|---|
| `ROIGenerationAlgorithm` da ROI de esôfago | **`MANUAL` em 59/60**, vazio em 1 |
| `RTROIInterpretedType` | `ORGAN` em 39/60, vazio em 21 |
| nome da ROI | `Esophagus` em 60/60 |
| CT referenciada por UID | **60/60** |
| `ContentCreatorName`, `ReviewerName`, `ReviewDate`, `OperatorsName`, `InstitutionName`, `StationName` | **VAZIAS em 60/60** |
| `Manufacturer` | `Plastimatch` e `MIM Software Inc.` |
| `StructureSetLabel` | `RTstruct` e **`AutoSS`** |

**A autoria não está no arquivo.** As seis tags DICOM que poderiam carregá-la estão vazias
em 60/60. O que o arquivo **declara** é o método (`MANUAL`), e ele **concorda** com o
artigo — duas evidências independentes na mesma direção.

### 1.2 Um sinal meu que ficou mais fraco

Na Fase 20 usei `Manufacturer = Plastimatch` e `StructureSetLabel = AutoSS` como **sinais
de geração automática** ao avaliar o STOPSTORM. **Os dois aparecem aqui**, em contorno
clínico humano de radioterapia. A tag `Manufacturer` nomeia **o software que escreveu o
arquivo**, não quem desenhou o contorno.

O veredito do STOPSTORM **não muda** — ele se apoia na medição de **1 fatia por ROI** e no
texto do próprio PDF (*"delete our temporary contours from the templates"*), ambos
decisivos. Mas **dois dos três sinais que citei eram fracos**, e isso fica registrado.

## 2. Fontes consultadas

### 2.1 Primárias, abertas e lidas

| Fonte | Uso |
|---|---|
| Yang J. et al., *Med Phys* 2018 — artigo do desafio (PMC6714977) | definição, autoria, QA, sub-estudo de 3 casos |
| Yang et al. 2020 — artigo de **descrição de dados** (PMC8344378) | mapeamento S1/S2/S3→instituição, QA, especialidade do revisor |
| Kong F-M. et al., *IJROBP* 2011;81:1442-57 (PMC3933280) | o atlas de fato; extensão do esôfago; ausência de consenso |
| Página da coleção **LCTSC** no TCIA | *contouring guidelines*, licença, DOI |
| Handout oficial do desafio (J. Yang) | *"Use RTOG 1106 contouring atlas as guideline"* |
| *Deck* da NRG Oncology sobre OAR torácicos | formulação divergente do limite cranial |
| Lambert et al., **SegTHOR** (arXiv 1912.05950) | extensão a partir da 4ª vértebra cervical |

### 2.2 Não lidas — lacuna declarada

| Fonte | Por quê |
|---|---|
| **Documento de protocolo do ensaio RTOG 1106** | não localizado em acesso aberto. É a única fonte que fecharia a cadeia "LCTSC → RTOG 1106 → atlas" |

## 3. Os quatro achados que mais importam

1. **A afirmação do repositório é verdadeira.** `VRMED-ANATOMICAL-ONTOLOGY.md` linha 82
   está verificada quase palavra por palavra. **Nenhuma correção factual é necessária ali.**

2. **`RTOG 1106` é um ensaio, não um atlas.** A string aparece **zero vezes** em Kong et
   al. 2011. Os dois nomes são usados de forma intercambiável na literatura — e a
   `ESOPHAGUS_ONTOLOGY_V1` congelou o nome ambíguo. **Registrado, não alterado.**

3. **O GT do LCTSC cobre o esôfago cervical**, porque começa logo abaixo da cricoide, que
   é onde o esôfago começa. Isso resolve a contradição da Fase 21 **contra o projeto**.

4. **A autoria do GT das 60 séries é UNKNOWN** — número de anotadores, especialidade e
   instituição de cada contorno. O que existe é: contornos clínicos de rotina, **uma**
   revisão de QA por **um** físico médico, com edição quando necessária.

## 4. O que isso muda para o dataset próprio

O LCTSC **continua** sendo o que sempre foi para o projeto: coorte histórica, split
congelado, **não reutilizável** em desenho novo. Nada aqui a promove nem a rebaixa.

O que muda é o **padrão de exigência**: se a coorte mais bem documentada que o projeto usa
tem **anotador UNKNOWN** e **uma** revisão por **uma** pessoa, então exigir de um candidato
externo mais do que isso seria — como se viu no SegTHOR — aplicar um critério que o próprio
projeto não cumpre.
