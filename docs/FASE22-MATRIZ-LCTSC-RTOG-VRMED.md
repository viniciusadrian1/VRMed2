# Matriz de definição do esôfago — LCTSC × RTOG 1106 × VRMED V1

Fase 22 · 2026-09-06 · 5 arms de fonte primária · 5 passes céticos ·
**A `ESOPHAGUS_ONTOLOGY_V1` NÃO foi alterada**

> **A afirmação que o repositório já fazia está VERIFICADA.**
> `docs/VRMED-ANATOMICAL-ONTOLOGY.md` linha 82 diz *"GT LCTSC: Esophagus, do nível abaixo
> do cricoide à junção gastroesofágica (atlas RTOG 1106)"*. Três céticos independentes
> abriram o artigo primário e a página do TCIA e confirmaram, quase palavra por palavra.
> **Não há afirmação falsa viva no repositório sobre este ponto.**

---

## 1. A matriz

| Conceito | LCTSC | RTOG 1106 / Kong et al. 2011 | ESOPHAGUS_ONTOLOGY_V1 | Status |
|---|---|---|---|---|
| **início cranial** | *"contoured from the beginning at the level just below the cricoid"*; operacional: a fatia **abaixo** da primeira em que a lâmina da cricoide é visível | **Kong 2011:** *"should begin at the level of cricoid cartilage"*. **Deck NRG:** *"just below the"* — **as duas fontes divergem** | **cricoide declarado NÃO LOCALIZÁVEL** pelo projeto (Fase 9); extensão **herdada do GT** | **PARCIALMENTE COMPATÍVEL** |
| **término caudal** | *"to its entrance to the stomach at GE junction"*; operacional: primeira fatia (±1) em que esôfago e estômago se unem | *"continue on every CT image to include the gastroesophageal junction until it ends at the stomach"* | **junção gastroesofágica declarada NÃO LOCALIZÁVEL**; extensão herdada do GT | **PARCIALMENTE COMPATÍVEL** |
| **junção gastroesofágica** | incluída, é o marco caudal | incluída | não localizável; entra pelo GT | PARCIALMENTE COMPATÍVEL |
| **relação com cricoide** | marco cranial **explícito e operacionalizado** | marco cranial, com formulação divergente entre artigo e deck | marco **não localizável** — afirmar o contrário é regressão | **PARCIALMENTE COMPATÍVEL** |
| **relação com carina** | não usada | não usada | **localizável** (30/30, desvio mediano 0,00 mm, Fase 10) — mas **não é âncora do alvo** | NÃO INFORMADO (nas fontes) |
| **relação com ázigos** | não mencionada | não mencionada | estrutura vizinha, **excluída** do alvo | NÃO INFORMADO |
| **relação com arco aórtico** | não usado como marco | **não** no artigo de Kong; aparece como limite cranial no protocolo do **STOPSTORM** (Fase 20) — **terceira convenção** | não usado | NÃO INFORMADO |
| **lúmen** | **não declarado separadamente**; contorno definido pelo limite externo | **não declarado**; só o limite externo | **PREENCHIDO** — parede + lúmen como um objeto | **COMPATÍVEL na prática** (ver §3) |
| **parede** | *"to correspond to the mucosal, submucosa, and all muscular layers out to the fatty adventitia"* | idêntico, palavra por palavra | parede **incluída**; fronteira externa é a adventícia | **COMPATÍVEL** |
| **conteúdo** | não mencionado | não mencionado | **excluído como CLASSE**, mas o lúmen é preenchido | NÃO INFORMADO |
| **janela de TC** | *"The esophagus will be contoured using mediastinal window/level on CT"* | idêntico. Valores numéricos **não** são dados em nenhuma das duas | não especifica janela | **COMPATÍVEL** |
| **atlas citado** | *"using the RTOG 1106 contouring atlas"*, nominalmente | **"RTOG 1106" aparece ZERO vezes em Kong et al. 2011** | congelou o nome **"RTOG 1106"** | **PARCIALMENTE COMPATÍVEL** (ver §4) |
| **autoria / anotadores** | contornos **clínicos de rotina** de 3 instituições, reaproveitados. **Número de anotadores: UNKNOWN** | não aplicável | não especifica | **NÃO INFORMADO** |
| **revisão** | **SIM**, por **uma** pessoa: um organizador do desafio, identificado por iniciais, físico médico clínico. *"All contours were reviewed (and edited if necessary) to ensure consistency across the 60 patients"* | não aplicável | não especifica | **PARCIALMENTE COMPATÍVEL** |

## 2. A contradição da Fase 21 — resolvida, e contra o projeto

A Fase 21 deixou aberto: o SegTHOR foi reprovado por começar na **4ª vértebra cervical**;
um avaliador chamou o critério de inconsistente porque o LCTSC teria extensão comparável.

**O avaliador estava certo.** O LCTSC **não é omisso** — ele declara a extensão de forma
**explícita e mais operacional que o SegTHOR**, e seu limite cranial é **logo abaixo da
cricoide**. Como o esôfago **se origina** na borda inferior da cricoide, o GT do LCTSC
cobre o esôfago **desde o seu início**, incluindo a porção cervical.

**Portanto: o VRmed aplicou ao SegTHOR um critério que a própria coorte que ele usa não
satisfaz.** O cenário é o **(b)** — inconsistência real — e não o (c) que eu considerava
mais provável.

### 2.1 A medição concorda com o documento

Se o contorno começa logo abaixo da cricoide, ele tem de subir **acima do ápice pulmonar**.
Medido, em duas coortes independentes, abrindo os arquivos:

| Coorte | topo do esôfago menos topo do pulmão | casos acima do ápice |
|---|---|---|
| **LCTSC** (60) | mediana **+17,5 mm** (−21,0 a +39,0) | **54/60** |
| **4D-Lung** (amostra de 5) | mediana **+21,0 mm** (+12,0 a +27,0) | **5/5** |

**Documento e medida convergem.** É a confirmação mais forte desta fase, porque as duas
evidências são independentes: uma vem do texto, a outra dos voxels.

**Limite declarado:** *acima do ápice pulmonar* **não é o mesmo que** *cervical*. Os ápices
sobem acima da primeira costela. A fronteira cervical/torácica é o **opérculo torácico** —
marco que **nenhuma** das coortes declara e que a Fase 9 mediu como **não localizável**
pelo projeto. A medida mostra que o contorno vai alto; **não prova** onde ele cruza.

### 2.2 E uma ressalva que um cético impôs

O artigo do LCTSC diz, no mesmo parágrafo: *"participants would not be penalized for
contouring too great an extent of these structures"*. Ou seja, o desafio **tolera
sobre-extensão** por desenho. Isso enfraquece qualquer uso da extensão do LCTSC como
padrão estrito — e **reforça** a decisão da ontologia de herdar a extensão em vez de fixá-la.

## 3. Lúmen — por que "compatível na prática" e não "compatível"

**Nenhuma** das fontes primárias declara se o lúmen é incluído ou excluído. As duas
especificam apenas a **fronteira externa** (*"out to the fatty adventitia"*).

A compatibilidade vem de **medição, não de texto**: as 60 máscaras do LCTSC têm
**0,0000 % de buracos 2D** (Fase 21). Contorno planar fechado de RTSTRUCT é preenchido por
construção. **O objeto é o que a `ESOPHAGUS_ONTOLOGY_V1` especifica** — mas por
propriedade do formato, não por declaração de protocolo.

## 4. "RTOG 1106" é um ensaio, não um atlas

**FATO.** RTOG 1106 / ACRIN 6697 é um **ensaio clínico**. **Nenhum documento chamado
"atlas RTOG 1106" existe.** A string *"RTOG 1106"* aparece **zero vezes** em Kong et al.
2011 — a única ocorrência de "1106" ali é um número de página numa referência.

**E ainda assim os dois nomes são usados de forma intercambiável na literatura revisada
por pares**, e o LCTSC cita *"the RTOG 1106 contouring atlas"* nominalmente.

**Consequência para o VRmed:** a `ESOPHAGUS_ONTOLOGY_V1` congelou o nome **"RTOG 1106"**
como protocolo de referência. O nome é **ambíguo** — designa um ensaio, cuja documentação
de contorno remete ao atlas de Kong et al. 2011, que por sua vez não se autodenomina assim.

**A ontologia NÃO foi alterada.** Registrar a ambiguidade é o que esta fase faz; resolvê-la
seria uma V2, e essa decisão não é desta fase.

## 5. O que continua NÃO INFORMADO

- **quantas pessoas** desenharam os contornos das 60 séries — UNKNOWN;
- **qual especialidade** tinham — UNKNOWN (a única especialidade declarada em toda a
  cadeia é a do **revisor de QA**, um físico médico);
- tratamento explícito de **lúmen** e **conteúdo** — nenhuma fonte declara;
- **valores numéricos** de janela/nível — nenhuma fonte dá;
- **ázigos** e **arco aórtico** — não mencionados por nenhuma das duas.

## 6. Decisão

**`ONTOLOGY_CHANGE: NÃO`.** Nada aqui altera a `ESOPHAGUS_ONTOLOGY_V1`.

Ao contrário: a fase **vindica** a posição dela. A ontologia diz que a extensão é
**herdada do GT e não avaliável anatomicamente**, e que cricoide e junção gastroesofágica
**não são localizáveis** pelo projeto. As fontes primárias mostram exatamente por quê:
o GT **usa** esses dois marcos, as duas fontes do atlas **divergem** sobre o cranial, o
desafio **tolera** sobre-extensão, e o próprio Kong 2011 registra a variabilidade de
extensão como problema conhecido e sem consenso.
