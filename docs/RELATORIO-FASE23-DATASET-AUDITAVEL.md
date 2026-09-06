# Fase 23 — o primeiro dataset auditável do VRmed

Data: 2026-09-06 · **5 casos reais ingeridos** · Nada treinado · Split histórico intocado

> **RESULTADO: B — pool real existe, é pequeno, e não é TEST.**
>
> Pela primeira vez o funil processou **dado clínico de verdade**, baixado nesta execução,
> ponta a ponta, sem afrouxar nenhuma trava. **5/5 elegíveis** pelo critério 23.18 completo.
>
> E o pool inteiro é **`SEMIAUTOMATIC`** — o que o torna utilizável em TRAIN **com a
> ressalva gravada** e inutilizável como referência humana pura.

---

## 1. Fontes e candidatos

Revisão dos candidatos da Fase 20 sob a **regra nova do 23.3**: para TRAIN não é preciso
provar independência do TotalSegmentator no nível impossível que o TEST exige.

Matriz completa: [`FASE23-MATRIZ-AQUISICAO.md`](FASE23-MATRIZ-AQUISICAO.md).

| Candidato | TRAIN | Por quê |
|---|---|---|
| **4D-Lung** | **SIM, com ressalva** | objeto certo, CC BY 3.0 por série, DICOM com 3 identidades, vínculo por UID, `SEMIAUTOMATIC` declarado |
| Pediatric-CT-SEG | NÃO | ontologia: idade mediana **6 anos** |
| NSCLC-Radiomics | NÃO | já usado; e RTSTRUCT de esôfago em **CC BY-NC 3.0** |
| LCTSC | NÃO | split histórico congelado |
| EAY131 | NÃO | objeto errado (lesão) |
| LyNoS | NÃO (TEST-2 condicional) | 2/4 identidades; imagem não exclusiva |
| STOPSTORM | NÃO | não há GT: templates de nomenclatura |

## 2. Aquisição — conservadora e registrada

| | |
|---|---|
| tamanho **registrado antes** | 265,3 MB · teto **400 MB**, declarado antes de olhar |
| **sujeitos distintos** | 5 — nunca séries (o 4D-Lung tem até 8 4DCT semanais × 10 fases por sujeito) |
| baixado de fato | **108,2 MB** |
| canal | NBIA anônimo, coleção pública |
| conta · termo · pedido de acesso | **nenhum** |

## 3. Identidade (23.7)

Extraído de cada caso: `PatientID`, `StudyInstanceUID`, `SeriesInstanceUID`,
`SOPInstanceUID`, mais `image_sha256` e `mask_sha256` calculados localmente.

**O `SOPInstanceUID` não substitui as quatro chaves** — é extra do canal. As quatro do
esquema são `case_id`, `study_id`, `series_id` e o **`sha256` do conteúdo**.

## 4. Vínculo imagem–máscara (23.8)

**Confirmado por `ReferencedSeriesInstanceUID` em 5/5.** O funil **recusa** par por nome de
arquivo, por ordem ou por pasta — as três formas clássicas de casar a máscara de um caso
com a imagem de outro. Sem vínculo formal, o caso sai `BLOCKED`.

## 5. Proveniência e anotação (23.9, 23.10)

| Campo | Valor |
|---|---|
| `source_dataset` | 4D-Lung (TCIA) |
| `source_doi` | `10.7937/K9/TCIA.2016.ELN8YGLE` |
| `annotation_source` | contorno clínico de RT; `ROIGenerationAlgorithm` **`SEMIAUTOMATIC`** no próprio arquivo |
| `annotation_protocol` | **UNKNOWN** — o 4D-Lung não cita atlas |
| `annotation_date_known` | **False** |
| `institution` | **UNKNOWN** |
| `human_or_model` | **humano, com propagação geométrica** |
| `mascara_origem` | **derivada**: contorno poligonal do RTSTRUCT → voxel |

### 5.1 Circularidade — investigada e registrada

O artigo do 4D-Lung descreve: contorno manual **numa** fase, propagado às demais por
**registro rígido**, e *"adjusted manually"* em cada uma.

**Registro rígido não é modelo de segmentação.** A recusa dura do projeto
(`gt_humano=False` para saída de modelo) **não se aplica**. Mas a nuance vai para o
manifesto, e não para a memória de quem leu o artigo:

> **O pool não é referência humana pura.** É anotação humana propagada geometricamente,
> com ajuste manual por fase. Utilizável em TRAIN; **jamais** como padrão de comparação
> humano.

## 6. Ontologia (23.11) — 5/5 aprovados

| case_id | volume | extensão axial | buracos 2D | orientação |
|---|---:|---:|---:|---|
| `4DLUNG-104_HM10395` | 33,65 mL | 249,0 mm | 0,0000 % | LPS |
| `4DLUNG-106_HM10395` | 27,51 mL | 207,0 mm | 0,0000 % | LPS |
| `4DLUNG-107_HM10395` | 26,35 mL | 174,0 mm | 0,0000 % | LPS |
| `4DLUNG-109_HM10395` | 60,69 mL | 198,0 mm | 0,0000 % | LPS |
| `4DLUNG-115_HM10395` | 32,89 mL | 240,0 mm | 0,0000 % | LPS |

Faixa compatível com o LCTSC (24,2–90,6 mL; 150–270 mm). **Nenhuma máscara foi editada.**

## 7. Licença (23.15) — por série

**CC BY 3.0**, lida **por série** no índice do IDC — não do cabeçalho da coleção. Essa
distinção não é acadêmica: na mesma varredura, as RTSTRUCT de esôfago do NSCLC-Radiomics
saíram **CC BY-NC 3.0**, mais restritivas que a manchete da coleção.

## 8. Anonimização (23.17) — em dado real

| Tag | Estado | Observação |
|---|---|---|
| `PatientName` | **ACHADO** | `P104`…`P115` — pseudônimo espelhando o `PatientID` |
| `PatientID` | INDETERMINADO | presente e **exigido** pelo esquema |
| `AccessionNumber` | **ACHADO** | `2819497684894126` — **idêntico nos 5 pacientes** |
| UIDs | INDETERMINADO | presentes; remapeamento na origem não verificável daqui |
| tags privadas | **ACHADO** | 3 distintas por caso |
| caminho / nome | OK | 0 suspeitos |

**Nenhum caso é declarado "anonimizado".** O `AccessionNumber` constante entre pacientes
diferentes é **placeholder de desidentificação** — mas quem o tratasse como identidade
juntaria os cinco casos num só.

Detalhes: [`FASE23-ANONIMIZACAO-RESULTADO.md`](FASE23-ANONIMIZACAO-RESULTADO.md).

## 9. Duplicata (23.14)

| Verificação | Resultado |
|---|---|
| 4 chaves de identidade, dentro do pool | **0 colisões** |
| triagem por grade `(shape, spacing)` | 0 — as 5 grades são distintas |
| pool × LCTSC | **0** |
| pool × NSCLC-Radiomics | **0** |
| pool × LyNoS (`sha256`) | **0** |

**Limite declarado:** LyNoS e AeroPath são NIfTI, **sem UID**; o hash não cruza formatos.
**Um mesmo exame nos dois canais não seria detectado.** Isso é *"não detectado pelo
instrumento"*, nunca *"não há overlap"*.

## 10. Pool (23.12) — e o que ele não é

[`FASE23-POOL-CANDIDATO.json`](FASE23-POOL-CANDIDATO.json) — **5 casos**, `split` =
`"NAO ATRIBUIDO"` em todos.

**Nenhum split foi congelado. Nenhuma proporção foi fixada.** Com n=5, fixar seria escolher
o resultado antes de ter o dado. O TEST futuro permanece protegido — e o pool **não é
candidato a TEST**.

## 11. Bloqueios

1. **n = 5** — prova de funil, não coorte.
2. **Pool inteiro `SEMIAUTOMATIC`.**
3. **`institution` UNKNOWN** nos 5.
4. **`annotation_protocol` UNKNOWN** — o 4D-Lung não cita atlas.
5. **`StudyDate` deslocado sinteticamente** — data não serve de chave nem de anterioridade.
6. **Nenhum TEST.**

## 12. Esquema — nenhuma mudança

A `VRMED-ESOPHAGUS-DATASET-V1` **absorveu os 5 casos reais sem precisar de campo novo**.
Os estados que a Fase 23 precisou representar — máscara derivada, método semi-automático,
instituição desconhecida — couberam em `notes`, `annotation_source` e `institution`.

A [proposta de V2](VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md) **continua proposta**. E ganhou
evidência: a lacuna 2 (dado derivado não bloqueável por máquina) apareceu de novo aqui —
`SEMIAUTOMATIC` viajou em **texto livre**, não em campo tipado.

## 13. Resultado

```
FASE 23 CONCLUIDA
RESULTADO: B — pool real existe, e pequeno, e nao e TEST
AMOSTRAS REAIS: 5 sujeitos distintos (4D-Lung), 108,2 MB
CASOS ELEGIVEIS: 5/5 pelo criterio 23.18 completo
IDENTIDADE: 4/4 chaves em 5/5 — 3 do arquivo DICOM + sha256 computado
VINCULO: ReferencedSeriesInstanceUID em 5/5; par por nome/ordem/pasta RECUSADO
LICENCA: CC BY 3.0 lida POR SERIE
PROVENIENCIA: SEMIAUTOMATIC declarado no arquivo; mascara DERIVADA; protocolo UNKNOWN
ONTOLOGIA: 5/5 aprovados, buracos 2D 0,0000 %
ANONIMIZACAO: 3 achados por caso, nenhum declarado anonimizado
DUPLICATA: 0 colisoes dentro do pool e contra LCTSC, NSCLC e LyNoS
SPLIT: NAO CONGELADO — 5 casos com split "NAO ATRIBUIDO"
TREINAMENTO: BLOQUEADO
```
