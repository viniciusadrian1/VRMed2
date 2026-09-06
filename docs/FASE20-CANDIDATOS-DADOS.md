# Fase 20 — candidatos a dados auditáveis

Consulta: **2026-09-06** · 6 arms · 6 passes céticos · **235 consultas registradas** ·
**47 candidatos** · Log: [`overnight/phase20/source_log.csv`](overnight/phase20/source_log.csv)

> **A pergunta desta fase é diferente das anteriores.** As Fases 11 e 15 procuravam
> **teste independente** — o que exigia independência do TotalSegmentator. A Fase 20
> procura dados para um dataset **próprio e auditável**, sobretudo TRAIN e VALIDATION.
> **TRAIN não precisa ser independente do TotalSegmentator**: o VRmed não vai usá-lo.
> TRAIN precisa de **identidade preservável, procedência registrável, licença verificada
> e GT humano**.


> ### ⚠ CORREÇÃO DA FASE 22 — 2026-09-06
>
> **O achado central deste relatório está REFUTADO por medição posterior.**
> Onde se lê *"`ROIGenerationAlgorithm` UNKNOWN em 908/908 — procedência é bloqueio
> total"*, o correto é:
>
> | Algoritmo declarado | RTSTRUCT |
> |---|---:|
> | **MANUAL** | **731** |
> | **SEMIAUTOMATIC** | **101** |
> | INDETERMINADO (2 valores na série) | 42 |
> | UNKNOWN (tag ausente) | 34 |
>
> **A causa era minha, não do dado.** A coluna `ROIGenerationAlgorithms` do
> `rtstruct_index` é um conjunto **DEDUPLICADO** por série — `len` é sempre 0, 1 ou 2,
> nunca um valor por ROI. Meu leitor exigia `len(algos) == len(nomes)` para alinhar por
> posição e, como o DISTINCT colapsa ROIs de mesmo algoritmo, o alinhamento nunca valia
> e **tudo caía em UNKNOWN**.
>
> Detectado ao **abrir os 60 arquivos RTSTRUCT do LCTSC** (Fase 22), que declaram
> `MANUAL` em 59/60 — exatamente o que o índice, lido corretamente, também diz.
>
> **O texto original abaixo é preservado como histórico.** Ver
> [`RELATORIO-FASE22-LCTSC-DEFINICAO-AUTORIA.md`](RELATORIO-FASE22-LCTSC-DEFINICAO-AUTORIA.md).


---

## 1. O resultado em uma linha

**O canal DICOM resolve identidade por completo e procedência da anotação não resolve de
jeito nenhum.**

| Medida (do índice público do IDC, sem baixar imagem) | Valor |
|---|---|
| RTSTRUCT com esôfago-órgão | **908** em 5 coleções |
| **sujeitos distintos** com contorno de esôfago | **807** |
| máscara ligada à imagem por `ReferencedSeriesInstanceUID` | **908/908** |
| **`ROIGenerationAlgorithm` declarado para a ROI de esôfago** | **UNKNOWN em 908/908** |

A tag DICOM que responderia *"humano ou modelo?"* existe no padrão, está no índice, e
**não está preenchida em nenhum dos 908**.

## 2. Classificação

| Classe | N | Significado |
|---|---:|---|
| **A** | **3** | não são datasets — são **canais** (TCIA, IDC) e um **documento normativo** (atlas Kong 2011) |
| **B** | **2** | potencialmente elegível com ressalvas (o STOPSTORM caiu para F por medição) |
| **C** | **4** | inadequado |
| **D** | **14** | inacessível dentro das travas |
| **E** | **6** | independência ou definição indeterminada |
| **F** | **18** | reprovado por procedência, alvo ou vazamento |

**Nenhum candidato classe A é um dataset.** Os três A são infraestrutura e regra.

## 3. Os três melhores — e o que bloqueia cada um

### 3.1 Canal IDC / TCIA — **A (como canal, não como dataset)**

**Por que passou.** Entrega `PatientID`, `StudyInstanceUID`, `SeriesInstanceUID` e
`SOPInstanceUID` no próprio arquivo; `license_short_name` **por série** no índice; e
`referenced_SeriesInstanceUID` liga máscara a imagem **por identificador** — a prioridade
2 da Fase 20.1 satisfeita por construção.

**O que ainda bloqueia.** Nada, como canal. Mas duas ressalvas **medidas**:

1. **O UID não é âncora durável.** `13.081 de 58.060` séries de versões anteriores
   (**22,5 %**) têm UID **ausente** do índice corrente. `series_id` detecta vazamento
   **hoje**; entre releases, só o `sha256` do conteúdo não deriva.
2. **97 % do IDC é CC BY 3.0/4.0**, mas a licença **varia por série** — e o caso concreto
   importa: as RTSTRUCT de esôfago do NSCLC-Radiomics são **CC BY-NC 3.0**, mais
   restritivas que a manchete da coleção.

**Risco.** Confundir "identidade entregue" com "procedência conhecida". São eixos
distintos, e o segundo está vazio.

**Próximo passo.** Nenhum — o canal já está caracterizado e instrumentado
(`fase20/censo_identidade.py`, `fase20/proveniencia_roi.py`).

### 3.2 STOPSTORM Benchmark Data — **F**, e o mais instrutivo de todos

`10.5281/zenodo.22127731` · concept DOI `10.5281/zenodo.22127730` · **CC BY 4.0** ·
publicado **2026-08-27**.

**Por que passou.** É o único achado de 2025–2026 que fecha três eixos ao mesmo tempo:
licença permissiva **verificada na fonte primária**, acesso aberto sem conta nem termo,
DOI **próprio e de conceito** (ao contrário do LyNoS), esôfago entre os OARs, DICOM com
UIDs, e **CT ligada por UID em 3/3**. Ainda traz, dentro do pacote, o **atlas Kong 2011** —
a regra de contorno de OAR torácico.

**O que ainda bloqueia — e foi um arm que precisou ser refutado.** Um arm classificou B
afirmando autoria humana *"verificada no arquivo, `ROIGenerationAlgorithm`"*. **Medido nos
3 RTSTRUCT:**

| Campo | Valor |
|---|---|
| `ROIGenerationAlgorithm` | **VAZIO em 93/93 ROIs** (31 × 3) |
| `StructureSetLabel` | **`AutoSS`** — *automatic structure set* |
| `Manufacturer` | **`Plastimatch`** |
| `PatientID` | **`NOID` nos três casos** |

Ausência da tag é `UNKNOWN`, **nunca `MANUAL` por omissão** — e os dois sinais que
existem apontam para o outro lado. **Isso não prova que a máscara é ruim:** num benchmark
de contorno, o structure set distribuído costuma ser o **ponto de partida** dado aos
centros, não a referência. Prova que **não entra como GT humano sem apuração documental**.

**E aí a medição seguinte fechou o caso.** Baixei o PDF do benchmark (0,96 MB) e medi as
fatias por ROI:

> **Cada um dos 31 ROIs, nos 3 casos, tem contorno em EXATAMENTE UMA FATIA.**
> O esôfago tem **1 contorno em 1 fatia**.

O PDF confirma em texto: *"we provided the above-mentioned contour **templates**. There is
**one slice** where you can find all the contours. **Please delete our temporary contours
from the templates** and start contouring according to the guidelines."*

**São templates de nomenclatura, não segmentações.** O pacote distribui a **tarefa**, não a
referência. **Classe F** — não há ground truth de esôfago ali, e isso é **medido**.

**O que o pacote entrega de valor: a regra.** O PDF traz a definição operacional de
extensão do esôfago atribuída a Kong et al. — *"mucosa, submucosa, and all muscular layers
out to the fatty adventitia"*, cranial **no arco aórtico** (não no cricoide) e caudal
*"until it ends at the stomach"*. **Mais uma convenção de extensão diferente** — o que
reforça, e não contradiz, a decisão da `ESOPHAGUS_ONTOLOGY_V1` de **herdar** a extensão do
GT em vez de fixá-la.

**Risco.** É o risco de sempre, na forma mais sedutora: licença impecável, identidade
impecável, formato impecável, e a procedência da anotação vazia. Foi assim que
`totalsegmentator_ct_segmentations` (**378.153 séries, CC BY 4.0, DICOM completo**) chegou
a parecer candidato.

**Próximo passo.** Nenhum, como fonte de dado. Como fonte de **regra**, o PDF já foi lido
e a citação está registrada.

### 3.3 Atlas Kong et al. 2011 — **A, e não é dataset**

**Por que passou.** Responde à pergunta que o Arm 5 foi buscar: existe documento público
que define **operacionalmente** os limites cranial e caudal do esôfago em contorno de RT
torácica. Autoria conjunta RTOG/EORTC/SWOG. Citações verificadas *verbatim* por um cético.

**O que ele muda — e o que ele não muda.** Ele dá a **regra**. Não dá dado, e **não
altera a `ESOPHAGUS_ONTOLOGY_V1`**: a Fase 9 mediu que as duas pontas do GT **não são
localizáveis** na imagem (IQR de 23,5 mm cranial e 13,6 mm caudal, contra um HD95 de
6,27 mm), e por isso a extensão longitudinal permanece **herdada do GT e não avaliável
anatomicamente**. Existir uma regra publicada e o projeto **conseguir verificá-la** são
coisas diferentes.

## 4. Os que não passaram, com o motivo medido

| Candidato | Classe | Motivo — e como foi estabelecido |
|---|---|---|
| **Pediatric-CT-SEG** | **C** | 359 sujeitos, 1:1 série/sujeito, CC BY 4.0, identidade completa, GT manual declarado — e **reprovado na ontologia**: idade **mediana 6 anos, 100 % abaixo de 18** (medido no `PatientAge` do índice). Sob a V1, calibrada na grade adulta do LCTSC, é **outro objeto** |
| **4D-Lung** | **C** | 6.690 séries de **20 sujeitos** (334,5 por sujeito); esôfago em **16**. `PatientAge` zerado (`000Y`) em 16/20 — idade **não avaliável**. `StudyDate` **deslocado sinteticamente**: data não serve de chave nem para inferir anterioridade |
| **EAY131 / NCI-MATCH** | **F** | catálogo de **lesão** (RECIST/PERCIST), não OAR. Dos 33 aceitos pelo crivo, **5 são sítio de lesão** (`PARAESOPHAGEAL`, `GASTRO ESOPHAGEAL`) |
| **`totalsegmentator_ct_segmentations`** | **F** | **378.153 séries, 26.194 sujeitos, CC BY 4.0, DICOM completo, inclui esôfago — e é saída de modelo.** O negativo perfeito |
| **`nnU-Net-BPR-annotations`** | **F** | AI-derived; a palavra *review* aparece uma vez no artigo, e é sobre revisão de **código** |
| **SegTHOR** | **E/F** | licença não localizada em fonte primária; e o esôfago é delineado **a partir da 4ª vértebra cervical** — inclui porção cervical. Dois céticos divergiram sobre o peso deste segundo motivo (§5) |
| **NSCLC-Radiomics-Interobserver1** | **F** | 5 observadores, 22 sujeitos — e **zero esôfago**: todas as ROIs são `GTV-1vis-1..5` / `GTV-1auto-1..5`. Verificado por medição direta |
| **LCTSC, NSCLC-Radiomics** | — | **já usados pelo VRmed**; split congelado, proibido reusar em desenho novo |

## 5. Contradição entre céticos, declarada e não resolvida

Sobre o **SegTHOR**, dois céticos discordaram:

- um reprovou por **ontologia** (esôfago começa na 4ª vértebra **cervical**, logo inclui
  porção cervical — mesmo modo de falha do HaN-Seg);
- outro chamou isso de **critério aplicado de forma inconsistente**, apontando que o
  **LCTSC — que o VRmed já usa, com split congelado** — teria definição de extensão
  comparável, e que a premissa sobre o RTOG 1106 não se sustenta.

**Não resolvido nesta fase, e registrado como tal.** A resolução exige ler a definição de
extensão do LCTSC contra a do SegTHOR em fonte primária — e o resultado pode atingir uma
coorte que o projeto **já usa**, o que a torna uma pergunta cara e importante.

## 6. Limitações desta matriz

- **FATO.** Um dos 6 passes céticos não havia concluído quando esta matriz foi escrita;
  as classificações do arm correspondente são de primeira ordem.
- **FATO.** `ROIGenerationAlgorithm` é **declarativa**: diz o que o autor escreveu, não o
  que fez. `MANUAL` declarado **não excluiria** pré-anotação por modelo corrigida à mão —
  a circularidade que a Fase 16 encontrou no TotalSegmentator seria invisível aqui também.
- **FATO.** O crivo herdado da Fase 11 aceita `Esophagus_PRV` (margem de planejamento) e
  `PARAESOPHAGEAL` (sítio de lesão). Medidos: **0 PRV** e **5 sítios de lesão** entre os
  908. O instrumento **não foi alterado** — é auditado e o número 908 está publicado.
- **FATO.** Os 14 candidatos de classe D **não tiveram conteúdo verificado**. Nenhum termo
  foi aceito, nenhuma conta criada, nenhum acesso solicitado.
