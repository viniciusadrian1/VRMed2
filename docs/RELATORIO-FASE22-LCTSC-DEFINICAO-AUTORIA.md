# Fase 22 — definição e autoria do ground truth do LCTSC

Data: 2026-09-06 · 5 arms · 5 passes céticos · 60 RTSTRUCT abertos · Nada treinado

> **DECISÃO: B — parcialmente documentadas.**
> A **definição** está documentada e verificada em fonte primária. A **autoria** não:
> quantas pessoas contornaram as 60 séries continua `UNKNOWN`.
>
> E a fase resolveu a contradição da Fase 21 **contra o próprio projeto**.

---

## 1. A afirmação do repositório está correta

`docs/VRMED-ANATOMICAL-ONTOLOGY.md` linha 82: *"GT LCTSC: Esophagus, do nível abaixo do
cricoide à junção gastroesofágica (atlas RTOG 1106)"*.

**VERIFICADA**, quase palavra por palavra, por três céticos independentes que abriram o
artigo primário (Yang et al., *Med Phys* 2018) e a página da coleção no TCIA:

> *"The esophagus should be contoured from the beginning at the level just below the
> cricoid"* … *"to its entrance to the stomach at GE junction"* … *"using the RTOG 1106
> contouring atlas"*.

**Nenhuma correção factual é necessária no documento de ontologia anatômica.**

## 2. A definição — bem documentada

| Item | LCTSC declara |
|---|---|
| cranial | *"at the level just below the cricoid"*; operacional: a fatia **abaixo** da primeira em que a lâmina da cricoide aparece |
| caudal | *"its entrance to the stomach at GE junction"*; operacional: primeira fatia (±1) em que esôfago e estômago se unem |
| parede | *"the mucosal, submucosa, and all muscular layers out to the fatty adventitia"* |
| janela | *"mediastinal window/level on CT"* — sem valores numéricos |
| atlas | *"RTOG 1106 contouring atlas"*, citado nominalmente |
| lúmen | **não declarado** |
| conteúdo | **não declarado** |

Matriz completa: [`FASE22-MATRIZ-LCTSC-RTOG-VRMED.md`](FASE22-MATRIZ-LCTSC-RTOG-VRMED.md).

## 3. A autoria — não documentada

| Papel | Estado |
|---|---|
| anotador do GT | **UNKNOWN** — são contornos **clínicos de rotina** de três serviços, reaproveitados: *"The manual contours that were used in clinic for treatment planning were used as ground 'truth.'"* |
| quantos | **UNKNOWN** para as 60 séries |
| especialidade | **UNKNOWN** |
| revisão | **SIM**, por **uma** pessoa — um organizador do desafio, identificado por iniciais, **físico médico clínico** — *"reviewed (and edited if necessary) to ensure consistency across the 60 patients"* |
| consenso / adjudicação | **não houve** |
| humano ou modelo | **HUMANO** |

**Não confundir** com o único número publicado: o sub-estudo de variabilidade de **3
casos**, recontornados por **três dos autores**. Isso é outra coisa, e um arm quase a
apresentou como se fosse a autoria do GT — um cético o derrubou.

### 3.1 O arquivo concorda com o artigo

Os **60 RTSTRUCT foram abertos pela primeira vez em 22 fases**:

- `ROIGenerationAlgorithm` = **`MANUAL` em 59/60**;
- CT referenciada por UID em **60/60**;
- `ContentCreatorName`, `ReviewerName`, `OperatorsName`, `InstitutionName`, `StationName`:
  **vazias em 60/60** — a autoria **não está no arquivo**.

Duas evidências independentes — texto e tag — apontam para o mesmo lugar: **método
manual declarado, autor não identificado.**

## 4. A contradição da Fase 21 — resolvida contra o projeto

O SegTHOR foi reprovado por delinear o esôfago **a partir da 4ª vértebra cervical**. Um
avaliador chamou o critério de inconsistente.

**Ele estava certo.** O LCTSC **não é omisso** — declara sua extensão de forma **mais
operacional que o SegTHOR** — e começa **logo abaixo da cricoide**, que é **onde o esôfago
começa**. Portanto **o GT do LCTSC também cobre o esôfago cervical**.

### 4.1 E a medição concorda

Se o contorno começa junto à cricoide, tem de subir acima do ápice pulmonar. Medido nos
arquivos, em duas coortes independentes:

| Coorte | esôfago acima do ápice pulmonar | casos |
|---|---|---|
| **LCTSC** (60) | mediana **+17,5 mm** | **54/60** |
| **4D-Lung** (5) | mediana **+21,0 mm** | **5/5** |

**Documento e voxel convergem.** É a evidência mais forte da fase, porque as duas vias são
independentes.

**Limite declarado:** *acima do ápice pulmonar* ≠ *cervical*. A fronteira é o **opérculo
torácico**, marco que nenhuma coorte declara e que a Fase 9 mediu como **não localizável**
pelo projeto. A medida mostra que o contorno sobe; **não prova** onde ele cruza.

### 4.2 E o desafio tolera sobre-extensão

Um cético trouxe a frase seguinte do mesmo parágrafo, que inverte metade de qualquer
conclusão forte: *"participants would not be penalized for contouring too great an extent
of these structures"*.

O LCTSC **tolera sobre-extensão por desenho**. Isso enfraquece seu uso como padrão estrito
de extensão — e **reforça** a decisão da ontologia de **herdar** a extensão do GT.

## 5. "RTOG 1106" é um ensaio, não um atlas

**FATO.** RTOG 1106 / ACRIN 6697 é um **ensaio clínico**. Não existe documento chamado
"atlas RTOG 1106". A string *"RTOG 1106"* aparece **zero vezes** em Kong et al. 2011 — a
única ocorrência de "1106" ali é um número de página numa referência.

E ainda assim os dois nomes circulam de forma intercambiável na literatura revisada por
pares, e o próprio LCTSC cita *"the RTOG 1106 contouring atlas"*.

**A `ESOPHAGUS_ONTOLOGY_V1` congelou um nome ambíguo.** Registrado. **Não alterado** —
resolver isso seria uma V2, e a decisão não é desta fase.

### 5.1 E as duas fontes do atlas divergem entre si

| Fonte | Limite cranial |
|---|---|
| Kong et al. 2011 (artigo, IJROBP) | *"should begin at the level of cricoid cartilage"* |
| *Deck* oficial da NRG | *"just below the"* |
| STOPSTORM (Fase 20) | **arco aórtico** |

**Três convenções publicadas** para a mesma estrutura. O próprio Kong 2011 registra a
variabilidade de extensão como problema conhecido e **sem consenso**.

## 6. Extensão longitudinal — a posição do VRmed continua adequada

A ontologia diz: **extensão herdada do GT, não avaliável anatomicamente**; cricoide e
junção gastroesofágica **não localizáveis** pelo projeto.

Esta fase **vindica** essa posição, e agora com razão documentada: o GT **usa** os dois
marcos; as fontes do atlas **divergem** sobre o cranial; o desafio **tolera**
sobre-extensão; e a literatura de origem **declara falta de consenso**.

**`ONTOLOGY_CHANGE: NÃO`.**

## 7. Parede versus lúmen

Nenhuma fonte declara o lúmen. As duas especificam apenas a **fronteira externa**
(*"out to the fatty adventitia"*).

A compatibilidade com a ontologia vem de **medição**: as 60 máscaras do LCTSC têm
**0,0000 % de buracos 2D** (Fase 21). Contorno planar fechado de RTSTRUCT é preenchido por
construção — **propriedade do formato, não declaração de protocolo**, e assim fica escrito.

## 9. Adendo — o juiz-sintetizador e o quinto arm (chegaram depois)

> Este adendo entra **depois** do relatório acima, que foi escrito com 4 de 5 arms. O
> workflow fechou 11/11 e o juiz refinou quatro pontos. **O texto acima é preservado.**

### 9.1 A verificação da linha 82 é **PARCIAL**, não plena

O juiz classificou `afirmacao_do_repo_verificada` como **PARCIALMENTE**: o **conteúdo** se
sustenta quase palavra por palavra; a **atribuição** tem ressalva — *"RTOG 1106"* nomeia
coisas diferentes conforme quem escreve (o ensaio `NCT01507428`, o artigo-atlas de Kong
2011, e um *deck* da NRG com slides *"RTOG 1106 Required OARs"*).

Onde o relatório acima diz "VERIFICADA", leia-se **"conteúdo verificado, atribuição
ambígua"**.

### 9.2 São **três** redações do limite cranial, não duas — e uma contradição interna

| Fonte | Cranial |
|---|---|
| Kong et al. 2011 | *"begin **at the level of** cricoid cartilage"* |
| LCTSC · deck NRG · TCIA | *"at the level **just below** the cricoid"* |
| **Yang et al. 2020** (descrição de dados) | *"edited to be **in the first slice of** cricoid cartilage"* |

E **dentro do próprio deck RTOG 1106** o texto da regra diz *"just below the cricoid"*
enquanto uma legenda de slide do **mesmo arquivo** diz *"Esophagus starts at the level of
cricoid"*.

### 9.3 Protocolo prescrito ≠ execução descrita

O protocolo publica tolerância de **±1 fatia** e o critério de **≥10 cm² de estômago**.
A descrição do que foi **efetivamente feito** (Yang 2020) **não menciona nenhum dos dois**
e diz que as pontas foram **editadas aos marcos**.

### 9.4 O corte de 1 cm — e a assimetria que um cético impôs

**FATO, citação literal:** *"both ground truth and submitted contours were cropped 1 cm
superior to the inferior border"*. O desafio **cortou 1 cm de cada extremidade**, do GT e
das submissões, **antes de pontuar**.

**Mas a frase seguinte do mesmo parágrafo, que um cético trouxe, corta metade da
conclusão:** *"participants would not be penalized for contouring too great an extent of
these structures in the inferior-superior direction, but would be penalized for a
substantial undersegmentation."*

**A extensão é excluída ASSIMETRICAMENTE:** sobre-extensão não penaliza; **sub-segmentação
longitudinal continua penalizando**. Não é "a extensão não é avaliável" — é "a extensão
excessiva é tolerada".

> **Consequência para o VRmed, registrada e NÃO executada nesta fase.** O projeto computa
> Dice contra fatias do GT do LCTSC que **os próprios autores do dataset cortaram antes de
> pontuar**. Isso é **limitação declarada** do `A_BASELINE_V1`, não erro dele.
> **Nenhuma métrica foi recalculada** — a regra desta execução proíbe, e o split é
> histórico e congelado. Fica como recomendação para uma fase dedicada.

### 9.5 A taxa de edição do QA é UNKNOWN — e isso atinge o split congelado

Sabe-se que *"in some cases"* as extremidades foram estendidas no QA. **Não há registro por
caso.** Portanto **é impossível saber se um dado RTSTRUCT do split congelado é contorno
clínico puro ou editado pelo organizador.**

### 9.6 "expert" nunca é substanciado

A palavra **"expert"** aparece no **título** do artigo de descrição de dados e **nunca é
substanciada no método**. O único qualificador de pessoa em toda a cadeia é o do QA:
*"one experienced clinical medical physicist (GS)"*.

### 9.7 Corroboração interna que o juiz recuperou

A **Fase 9** já havia medido, e ninguém tinha ligado a este ponto: a ponta cranial do GT do
LCTSC está em mediana **+120,0 mm acima da carina**, com corte no limite de campo em apenas
**1/30** casos. O contorno sobe muito, e **não** porque a imagem acabou.

Terceira via independente concordando com o documento e com a medição de ápice pulmonar.


## 8. Decisão

```
DECISAO: B — parcialmente documentadas
LCTSC_DEFINITION: DOCUMENTADA E VERIFICADA — cranial "just below the cricoid",
  caudal "entrance to the stomach at GE junction", parede ate a adventicia gordurosa,
  janela de mediastino, atlas RTOG 1106 citado nominalmente
LCTSC_ANNOTATOR: UNKNOWN — contornos clinicos de rotina de 3 servicos, reaproveitados.
  Numero de anotadores e especialidade nunca declarados
LCTSC_REVIEW: UMA revisao, por UMA pessoa (organizador do desafio, fisico medico
  clinico, identificado por iniciais), com edicao quando necessaria. Sem consenso,
  sem adjudicacao
LCTSC_HUMAN_GT: SIM — manual, confirmado no artigo E na tag do arquivo (MANUAL 59/60)
LCTSC_VS_RTOG: TRES redacoes publicadas do limite cranial, e o deck da
  NRG se contradiz internamente. COMPATIVEL na parede, na janela e no caudal; PARCIALMENTE no cranial
  (Kong diz "at the level of", o deck da NRG diz "just below the"); e "RTOG 1106" e
  um ENSAIO, nao um atlas — a string aparece ZERO vezes em Kong et al. 2011
LCTSC_VS_VRMED: COMPATIVEL no alvo preenchido (medido: 0,0000 % de buracos em 60/60);
  PARCIALMENTE na extensao — o GT usa marcos que o projeto declara nao localizaveis,
  o que e exatamente o motivo de a ontologia HERDAR a extensao
ONTOLOGY_CHANGE: NAO
```
