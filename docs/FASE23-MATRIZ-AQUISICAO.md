# Fase 23 — matriz de aquisição

2026-09-06 · Candidatos revisados da Fase 20 sob a **regra nova do 23.3** ·
Amostra real adquirida: **5 sujeitos** · Pool elegível: **5**

> **A regra mudou, e ela é o eixo desta fase.** Para **TRAIN** não é preciso provar
> independência do TotalSegmentator no nível impossível que o TEST exige. É preciso:
> origem conhecida · anotação conhecida · licença conhecida · identidade conhecida ·
> ausência de circularidade conhecida · overlap investigado · **incerteza registrada**.
> Para **TEST**, as regras rígidas continuam valendo integralmente.

---

## 1. A matriz

| dataset | canal | n (sujeitos) | modality | annotation | annotation_source | annotation_method | institution | license | case_id | study_id | series_id | mask↔image | provenance | overlap VRmed | overlap TS | overlap AeroPath/LyNoS | TRAIN | VALIDATION | TEST | bloqueio | próxima ação |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **4D-Lung** | TCIA/IDC DICOM | **16** com esôfago (20 na coleção) | CT + RTSTRUCT | humana clínica de RT | contorno de planejamento | **`SEMIAUTOMATIC`** declarado no arquivo | UNKNOWN | **CC BY 3.0** por série | SIM | SIM | SIM | **UID 101/101** | DOI de coleção + UIDs | **0** colisões | não testável | não testável (canal ≠) | **SIM, com ressalva** | SIM | **NÃO** | GT propagado por registro rígido entre fases; `StudyDate` deslocado | **5 já ingeridos** |
| **Pediatric-CT-SEG** | TCIA/IDC DICOM | 359 | CT + RTSTRUCT | humana | 4 analistas + QA de radio-oncologista | **`MANUAL` 317 / indeterminado 42** | UNKNOWN | CC BY 4.0 | SIM | SIM | SIM | UID 359/359 | DOI + UIDs | 0 | não testável | não testável | **NÃO** | NÃO | NÃO | **ontologia**: idade mediana 6 anos, 100 % < 18 | nenhuma sob a V1 |
| **NSCLC-Radiomics** | TCIA/IDC DICOM | 422 | CT + RTSTRUCT | humana | contorno clínico | **`MANUAL` 355** | MAASTRO | **CC BY-NC 3.0** (RTSTRUCT de esôfago) | SIM | SIM | SIM | UID 355/355 | DOI + UIDs | **JÁ USADO** (Fase 10) | — | — | **NÃO** | NÃO | NÃO | já usado pelo VRmed; e licença **NC** | nenhuma |
| **LCTSC** | TCIA/IDC DICOM | 60 | CT + RTSTRUCT | humana clínica | 3 instituições, contorno de rotina | **`MANUAL` 59 / vazio 1** | MDACC, MSKCC, MAASTRO | CC BY 3.0 | SIM | SIM | SIM | UID 60/60 | DOI + UIDs | **JÁ USADO**, split congelado | — | — | **NÃO** | NÃO | NÃO | split histórico congelado | nenhuma |
| **EAY131** | TCIA/IDC DICOM | 17 com "esôfago" | CT + RTSTRUCT/SEG | humana | catálogo de **lesão** RECIST | `UNKNOWN` 33 | — | CC BY 4.0 | SIM | SIM | SIM | UID 33/33 | DOI + UIDs | 0 | — | — | **NÃO** | NÃO | NÃO | **objeto errado**: lesão, não OAR | nenhuma |
| **LyNoS** | Zenodo NIfTI | 15 | NIfTI | humana | Fase 18 | UNKNOWN | St. Olavs | CC BY 4.0 | externo | **UNKNOWN** | **UNKNOWN** | **por nome de arquivo** | DOI de artigo | imagem = AeroPath | indeterminado | **é o mesmo conjunto** | NÃO | **condicional** | **NÃO** | 2/4 identidades; imagem não exclusiva | manter como TEST-2 condicional |
| **STOPSTORM** | Zenodo DICOM | 3 | CT + RTSTRUCT | **nenhuma** | templates de nomenclatura | 1 fatia por ROI | — | CC BY 4.0 | `NOID` ×3 | SIM | SIM | UID 3/3 | DOI próprio | 0 | — | — | **NÃO** | NÃO | NÃO | **não há GT**: o pacote distribui a tarefa | nenhuma |
| **`totalsegmentator_ct_segmentations`** | IDC DICOM | 26.194 | SEG | **saída de modelo** | TotalSegmentator | AUTOMÁTICO | Basel | CC BY 4.0 | SIM | SIM | SIM | UID | DOI + UIDs | — | **é o próprio TS** | — | **NÃO** | NÃO | NÃO | **circularidade total** | nenhuma |

## 2. Por que 4D-Lung foi a amostra

Não por ser o melhor — por ser o **mais informativo para testar o funil**:

- **objeto certo** sob a `ESOPHAGUS_ONTOLOGY_V1`: esôfago torácico de adulto com NSCLC;
- **licença verificada por série** no índice do IDC, não pelo cabeçalho da coleção;
- **DICOM nativo** com as três identidades do arquivo;
- **vínculo por `ReferencedSeriesInstanceUID`**, nunca por nome de arquivo;
- e sobretudo: **`ROIGenerationAlgorithm = SEMIAUTOMATIC`** em 101/101.

Esse último ponto era o teste. O artigo descreve contorno manual numa fase, propagado às
demais por **registro rígido**, e *"adjusted manually"* em cada uma. Um funil honesto grava
isso como semi-automático e **não** como referência humana pura — sem por isso rejeitar o
caso. Registro rígido **não é modelo de segmentação**, então a recusa dura do projeto
(`gt_humano=False` para saída de modelo) não se aplica; a nuance vai para o manifesto.

## 3. Aquisição — conservadora (23.5)

| Etapa | Valor |
|---|---|
| tamanho **registrado antes** do download | 265,3 MB (teto 400 MB, declarado antes de olhar) |
| sujeitos **distintos** | 5 — nunca séries: o 4D-Lung tem até 8 4DCT semanais × 10 fases por sujeito |
| baixado de fato | **108,2 MB** |
| canal | NBIA anônimo, coleção pública |
| conta criada · termo aceito · acesso solicitado | **nenhum** |

## 4. Resultado da ingestão

**5/5 elegíveis** pelo critério 23.18 completo.

| case_id | algoritmo declarado | orientação | volume | extensão axial | buracos 2D |
|---|---|---|---:|---:|---:|
| `4DLUNG-104_HM10395` | SEMIAUTOMATIC | LPS | 33,65 mL | 249,0 mm | 0,0000 % |
| `4DLUNG-106_HM10395` | SEMIAUTOMATIC | LPS | 27,51 mL | 207,0 mm | 0,0000 % |
| `4DLUNG-107_HM10395` | SEMIAUTOMATIC | LPS | 26,35 mL | 174,0 mm | 0,0000 % |
| `4DLUNG-109_HM10395` | SEMIAUTOMATIC | LPS | 60,69 mL | 198,0 mm | 0,0000 % |
| `4DLUNG-115_HM10395` | SEMIAUTOMATIC | LPS | 32,89 mL | 240,0 mm | 0,0000 % |

Faixa compatível com o LCTSC medido na Fase 21 (24,2–90,6 mL; 150–270 mm).

## 5. Duplicata e overlap

| Verificação | Resultado |
|---|---|
| colisões nas **4 chaves de identidade** dentro do pool | **0** |
| triagem por grade `(shape, spacing)` | 0 — as 5 grades são distintas |
| pool × **LCTSC** (`StudyInstanceUID`, `SeriesInstanceUID`, `PatientID`) | **0** |
| pool × **NSCLC-Radiomics** (`SeriesInstanceUID`) | **0** |
| pool × **LyNoS** (`sha256`) | **0** |

**Limite declarado:** LyNoS e AeroPath são NIfTI e **não têm UID**; a comparação só pode
ser por hash de conteúdo, e os formatos diferem (NIfTI × DICOM convertido). **Um mesmo
exame nos dois canais não seria detectado.** Isso é "não detectado pelo instrumento",
nunca "não há overlap".

## 6. Anonimização (23.17) — em dado real

| Tag | Estado | Valor |
|---|---|---|
| `PatientName` | **ACHADO** | `P104`…`P115` — pseudônimo espelhando o `PatientID` |
| `PatientID` | INDETERMINADO | presente e **exigido** pelo esquema |
| `AccessionNumber` | **ACHADO** | `2819497684894126` — **idêntico nos 5 pacientes** |
| UIDs (Study/Series/SOP/FrameOfReference) | INDETERMINADO | presentes; remapeamento na origem não verificável daqui |
| tags privadas | **ACHADO** | 3 distintas por caso |
| caminho e nome de arquivo | OK | 0 suspeitos |

**Leitura.** O `AccessionNumber` constante entre pacientes diferentes é **placeholder de
desidentificação**, não vazamento — mas quem tratasse `AccessionNumber` como identidade
juntaria os cinco casos num só. Os `ACHADO` são pedidos de inspeção, e a inspeção foi
feita. **Nenhum caso é declarado "anonimizado".**

## 7. Bloqueios que permanecem

1. **n = 5.** Amostra de prova de funil, não coorte.
2. **`SEMIAUTOMATIC`** — o pool inteiro é anotação propagada por registro rígido com
   ajuste manual. Utilizável em TRAIN com a ressalva gravada; **inutilizável como
   referência humana pura**.
3. **`institution` = `UNKNOWN`** nos 5 — o 4D-Lung não a declara por caso.
4. **`annotation_protocol` = `UNKNOWN`** — nenhum atlas citado pelo 4D-Lung.
5. **`StudyDate` deslocado sinteticamente** (medido na Fase 20): data não serve de chave
   nem para inferir anterioridade.
6. **Nenhum TEST.** O pool é candidato a TRAIN/VALIDATION e a nada mais.
