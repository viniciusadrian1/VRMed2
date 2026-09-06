# Fase 24 — o universo de 16 sujeitos com esôfago do 4D-Lung

**Data:** 2026-09-06 · **Estado:** concluída, todos os portões passaram
**Escopo:** ingerir e auditar os 11 sujeitos restantes, preservando intactos os 5 já auditados
na Fase 23.
**O que esta fase NÃO fez:** não treinou, não mediu Dice, não tocou em TEST, não alterou a
`ESOPHAGUS_ONTOLOGY_V1`, não recalculou métrica histórica nenhuma.

---

## 1. O universo: por que 16, e por que não se corrigiu nada em silêncio

**FATO.** O índice `rtstruct_index` do IDC traz **101 RTSTRUCT com ROI de esôfago** na coleção
`4d_lung`. Agrupados por **`PatientID`** — nunca por série — dão **16 sujeitos** distribuídos em
20 estudos. A assimetria é real e está documentada: 11 sujeitos têm 1 RTSTRUCT; os sujeitos
100–103 têm 10 cada (fases respiratórias); o sujeito 107 tem 50 (5 estudos semanais × 10 fases).

A regra da execução mandava **parar e investigar** diante de qualquer discrepância no universo.
Houve uma verificação que merece registro: **o sujeito `113_HM10395` não existe** no conjunto com
esôfago. Os 16 são `100`–`112`, `114`, `115`, `116`. Isso **não** é uma perda — é a numeração
original da coleção, que salta o 113. Nenhum caso foi descartado para chegar a 16.

**5 (Fase 23) + 11 (Fase 24) = 16 = universo esperado.** Sem discrepância.

---

## 2. O erro que a Fase 24 encontrou na Fase 23: a regra de seleção não era reproduzível

Este é o achado com maior consequência da fase, e ele é sobre **o nosso código**, não sobre o dado.

**FATO.** A regra de escolha de série por sujeito em `fase23/aquisicao.py` era:

```python
if p not in porsuj or mb < porsuj[p]["ct_mb"]:   # defeituoso
```

O `<` estrito significa que, **em caso de empate no tamanho, vence quem a iteração viu primeiro**.
E há empates de verdade: o sujeito 107 tem **10 candidatos com exatamente 43,158 MB**, e os
sujeitos 100–103 têm empates de 10 vias cada. A seleção dependia da ordem em que o parquet foi
lido — ou seja, **não era reproduzível**, e um relatório que diz "escolhemos a menor série" estaria
descrevendo algo que a próxima execução poderia contradizer.

**Correção aplicada** — critério de desempate total e explícito, e ordem de saída canônica:

```python
escolhidos_por_suj = {p: sorted(v, key=lambda x: (x["ct_mb"], x["ct_uid"]))[0]
                      for p, v in porsuj.items()}
ordenados = [escolhidos_por_suj[p] for p in sorted(escolhidos_por_suj)]
```

**Regra 14 preservada, e isso foi verificado, não assumido.** A regra nova **reproduz exatamente as
5 seleções da Fase 23**, caso a caso. Um autoteste novo falha se isso algum dia deixar de ser
verdade, e outro prova que embaralhar a entrada não muda a saída. O autoteste do módulo foi de
**7 para 14 verificações**.

**INFERÊNCIA.** Se os empates tivessem sido resolvidos de outro jeito, os 5 casos da Fase 23
poderiam ter séries diferentes hoje — e a Fase 23 teria congelado uma escolha que ela não
conseguiria justificar. O defeito foi encontrado antes de qualquer congelamento.

---

## 3. O teto de download abortou o plano, e não foi levantado em silêncio

**FATO.** O plano dos 11 pediu **719,5 MB** (tamanho não comprimido no índice) contra um teto de
`TETO_MB = 400.0` herdado da Fase 23. O guarda **abortou**, corretamente.

O teto da Fase 23 existia porque aquela fase era **uma amostra de 5**. Esta fase é **o fechamento
do universo** — o número de casos não é escolha nossa, é o que a coleção tem. Em vez de editar o
valor no lugar, declarou-se `TETO_MB_FASE24 = 1000.0` como constante separada, com o teto virando
**parâmetro explícito** (`--teto`) e a justificativa escrita junto. O teto histórico da Fase 23
continua no arquivo, intacto.

**Baixado de verdade: 280,3 MB** para os 11 sujeitos.

---

## 4. Ingestão: o mesmo funil, sem caminho paralelo

**FATO.** Os 11 novos passaram pelo **mesmo** `fase23/ingerir_real.py` que os 5 originais —
nenhuma rotina alternativa foi escrita para os casos novos. Resultado: **16/16 elegíveis, 0
bloqueados**.

| Verificação | Resultado nos 16 |
|---|---|
| canal de identidade | DICOM em 16/16 |
| identidades verificáveis das 4 chaves | **4/4 em 16/16** (`case_id`, `study_id`, `series_id` do arquivo + `sha256` computado) |
| vínculo máscara↔imagem | `ReferencedSeriesInstanceUID` em 16/16 |
| pareamento por nome de arquivo, ordem ou pasta | **recusado em 16/16** |
| máscara binária | 16/16, `uint8`, foreground `255.0` |
| componentes 3D | **1 em 16/16** |
| furos 2D | **0,0000 % em 16/16** |
| orientação | `LPS` em 16/16 |
| espaçamento z uniforme | 16/16 · `SliceThickness` 3,0 mm em 16/16 |
| `RescaleSlope/Intercept` | `(1,0 / −1000,0)` em 16/16 |
| `ROIGenerationAlgorithm` | **`SEMIAUTOMATIC` em 16/16** |

**Nenhuma operação morfológica foi aplicada.** Sem fechamento, sem preenchimento de furos, sem
erosão, dilatação ou suavização. Os 0,0000 % de furos são uma **medida do dado como ele veio**, não
o efeito de um conserto nosso.

**FATO, e é uma limitação, não um elogio.** `SEMIAUTOMATIC` em 16/16 significa que **nenhum caso
deste pool é GT humano puro**. É contorno de radioterapia gerado com auxílio de algoritmo e
revisado; o campo DICOM declara isso e o projeto o registra como está. A regra 12 proíbe chamá-lo
de outra coisa.

### 4.1 Heterogeneidade de fase respiratória — achado novo, registrado

**FATO.** Os nomes de ROI dos 16 não são todos iguais: `Esophagus_c00` em 12 casos,
`Esophagus_c80` em 2, `Esophagus_c10` em 1, `Esophagus_c40` em 1. O sufixo `cNN` é a **fase do
ciclo respiratório**.

**INFERÊNCIA.** A regra de seleção escolhe a **menor série por sujeito**, e a menor série não cai
sempre na mesma fase respiratória. O pool é, portanto, **heterogêneo em fase respiratória** —
14 casos em fases próximas do fim da expiração (`c00`/`c10`) e 2 em `c80`.

**RECOMENDAÇÃO.** Registrar como característica declarada do pool. Não é motivo para trocar a
regra de seleção: trocar a regra depois de ver o resultado é escolher o dado. E não há evidência,
neste momento, de que a fase respiratória prejudique o uso pretendido.

---

## 5. Reprodução dos 5 (regra 14)

**FATO.** Os 5 casos da Fase 23 foram **reprocessados do zero** pelo pipeline da Fase 24 e
comparados campo a campo contra o pool histórico, em 11 campos imutáveis (`case_id`, `study_id`,
`series_id`, `image_sha256`, `mask_sha256`, `spacing`, `orientation`, `shape`, `license_class`,
`source_dataset`, `source_case_id`).

**Resultado: idênticos, campo a campo.** O campo `notes` ficou deliberadamente fora da comparação —
texto pode ser reescrito sem que o **dado** mude, e incluí-lo faria o teste falhar por motivo
errado.

---

## 6. Redundância interna e duplicatas

**FATO.** `16 sujeitos, uma série por sujeito = True`. Zero `study_id`, `series_id`,
`image_sha256` ou `mask_sha256` repetidos.

**Colisões por IDENTIDADE (as 4 chaves): 0.**

**Colisão por GRADE (triagem grosseira): 1** — `4DLUNG-112` e `4DLUNG-116` compartilham
`shape (512,512,118)` e `spacing (0,9766, 0,9766, 3,0)`.

**Isto NÃO é uma duplicata.** São `PatientID`, `StudyInstanceUID`, `SeriesInstanceUID` e
`sha256` de conteúdo todos diferentes. Grade igual é o esperado num scanner com protocolo fixo, e
a comparação por grade existe como **triagem**, não como critério de identidade. Registrado para
que ninguém a reencontre depois e a interprete como achado.

---

## 7. Anonimização — o checklist existente, aplicado aos 16

A regra é explícita: **não chamar de "anônimo" só porque veio da NBIA**. O checklist da Fase 21 foi
rodado nos 16 casos.

| Item | Resultado |
|---|---|
| `PatientName` presente | **ACHADO em 16/16** |
| `AccessionNumber` presente | **ACHADO em 16/16** |
| tags privadas | **3 por caso, em 16/16** |
| PHI no caminho de arquivo | OK em 16/16 |

**FATO, e é o dado que importa:** os 16 valores de `PatientName` são `P100`…`P116` — um
**pseudônimo que espelha o `PatientID`**, não um nome. E os 16 valores de `AccessionNumber` são
**a mesma string** (`2819497684894126`) — uma constante de preenchimento, não 16 números de
acesso distintos.

**INFERÊNCIA.** As duas tags estão **presentes mas preenchidas com substituto**, o que é
consistente com um processo de desidentificação que substitui em vez de remover.

**O que NÃO se conclui (regra 13).** O projeto **não declara este dataset anonimizado**. Não foi
localizada declaração explícita do método de desidentificação aplicado pela fonte, e "tag presente
com valor substituto" é evidência de substituição, não certificado de conformidade. O estado
registrado é: **tags de PHI presentes, valores aparentemente substituídos, método de
desidentificação UNKNOWN.**

---

## 8. Anti-leakage cruzado contra os datasets já usados

| Dataset de referência | n | Chaves comparadas | Estado |
|---|---|---|---|
| LCTSC | 120 | study, series, case | **NÃO DETECTADO** |
| NSCLC-Radiomics | 25 | series | **NÃO DETECTADO** |
| LyNoS | 15 | apenas hash de conteúdo | **IDENTIDADE INDISPONÍVEL** |

**A leitura correta, e ela é restritiva.** *"NÃO DETECTADO" é o resultado do instrumento, não uma
afirmação de independência.* Nenhuma destas chaves prova ausência.

E o caso do LyNoS é pior que inconclusivo por omissão — é inconclusivo **por construção**: LyNoS é
NIfTI e **não tem `StudyInstanceUID` nem `SeriesInstanceUID`**. Só resta comparar hash de conteúdo,
e os formatos diferem (NIfTI original × DICOM convertido por nós). **Um mesmo exame presente nos
dois canais não seria detectado.** Isto é **INCONCLUSIVO**, nunca "sem overlap".

---

## 9. Testes

**Suítes do projeto — 49/49:**

| Arquivo | Resultado |
|---|---|
| `tests/test_geometria.py` | 10/10 |
| `tests/test_controles_positivos.py` | 8/8 |
| `tests/test_ontologia_esofago.py` | 13/13 |
| `tests/test_baseline_v1.py` | 18/18 |

**Autotestes de módulo — 156/156, 0 falhas:** `manifesto` 29 · `plano` 14 · `candidatos` 7 ·
`funil` 16 · `mutacao` 31 · `anonimizacao` 11 · `aquisicao` **14** · `ingerir_real` 8 · `pool` 5 ·
`consolidar` 8 · `split` 13.

**Nota de ambiente.** `pytest` **não está instalado** no `.venv-pipeline`; os quatro arquivos de
teste rodam como programas autônomos e foi assim que foram executados. Nenhum teste foi pulado.

---

## 10. Riscos e limitações declarados

| # | Item | Estado |
|---|---|---|
| 1 | Anotação é `SEMIAUTOMATIC` em 16/16 | **não é GT humano puro** — limitação do pool, declarada |
| 2 | Independência de LyNoS | **INCONCLUSIVA por construção**, não "sem overlap" |
| 3 | `institution` | **UNKNOWN em 16/16** — não estimado |
| 4 | Método de desidentificação da fonte | **UNKNOWN** — dataset não declarado anonimizado |
| 5 | Fase respiratória | heterogênea (`c00`×12, `c80`×2, `c10`×1, `c40`×1) |
| 6 | Extensão longitudinal | **herdada do GT**, não avaliável anatomicamente (ontologia) |
| 7 | n = 16 | pool pequeno; TEST permanece vazio e protegido |
| 8 | `aquisicao.json` traz `"fase": 23` | é o rótulo do **módulo** `fase23/aquisicao.py`, reusado sem cópia — correto, não corrigido |

---

## 11. Portões da Fase 24

```
reproducao=True | um_por_sujeito=True | universo=True | sem_bloqueados=True
```

Todos passaram. A Fase 25 está liberada.

---

## 12. Arquivos e hashes

| Arquivo | sha256 |
|---|---|
| `docs/FASE24-POOL-16.json` | `1a013531ad65b89275e8878ac6180cdbe0e376cb3d4d88c4433897fb519b11b9` |
| `docs/overnight/phase24/ingestao_real_16.json` | `69abeda8b0e5aaf1b6d43b3b0cb569964da74a6807333c158a4b71fe0cd3d02a` |
| `docs/overnight/phase24/consolidacao.json` | `1b415fbd935a235d2b75217e33aacb51b0863158fdb04e1cd521d66f52041484` |

**Incidente de processo registrado (regra 6).** A execução da Fase 24 sobrescreveu
`docs/overnight/phase23/aquisicao.json` e `.../ingestao_real.json` — artefatos **históricos**. Foi
detectado, o conteúdo novo foi movido para `docs/overnight/phase24/`, e os dois arquivos da Fase 23
foram **restaurados** via `git checkout --`. O `INGESTAO` de `fase24/consolidar.py` passou a apontar
para o caminho da Fase 24. Nenhum resultado histórico ficou alterado.

---

## 13. Os 16 sujeitos, um por linha

Coleção **4D-Lung (TCIA)** · licença **CC BY 3.0** declarada **por série** no índice do IDC ·
`license_class` `ABERTA_ATRIBUICAO` · `institution` **UNKNOWN** em todos ·
`split` **`NAO ATRIBUIDO`** em todos (a Fase 25 atribui) ·
máscara **derivada**: RTSTRUCT poligonal → voxel (`dcmrtstruct2nii`) ·
vínculo confirmado por `ReferencedSeriesInstanceUID`.

| # | case_id | orig. | study_id (final) | series_id (final) | shape | spacing (mm) | ROI | algoritmo | orient. | vol (mL) | ext. axial (mm) | comp. 3D | furos 2D | image_sha256 (8) | mask_sha256 (8) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `4DLUNG-100_HM10395` | **F24** | …4293614571 | …2990015277 | 512x512x142 | 0.9766, 0.9766, 3 | `Esophagus_c80` | SEMIAUTOMATIC | LPS | 46.57 | 252.0 | 1 | 0.0000 % | `9769dfc3` | `c83a5528` |
| 2 | `4DLUNG-101_HM10395` | **F24** | …4721386157 | …5159753289 | 512x512x149 | 0.9766, 0.9766, 3 | `Esophagus_c80` | SEMIAUTOMATIC | LPS | 26.00 | 243.0 | 1 | 0.0000 % | `665d0eae` | `47ec65ff` |
| 3 | `4DLUNG-102_HM10395` | **F24** | …7853057341 | …2525949755 | 512x512x133 | 0.9766, 0.9766, 3 | `Esophagus_c10` | SEMIAUTOMATIC | LPS | 38.52 | 243.0 | 1 | 0.0000 % | `feae6707` | `6198cfa5` |
| 4 | `4DLUNG-103_HM10395` | **F24** | …2441043192 | …9948920812 | 512x512x117 | 0.9766, 0.9766, 3 | `Esophagus_c40` | SEMIAUTOMATIC | LPS | 44.42 | 267.0 | 1 | 0.0000 % | `3b1ecb4f` | `84f905c8` |
| 5 | `4DLUNG-104_HM10395` | F23 | …4654184934 | …1716106982 | 512x512x103 | 1.0527, 1.0527, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 33.65 | 249.0 | 1 | 0.0000 % | `5275c0d4` | `85b2d0a2` |
| 6 | `4DLUNG-105_HM10395` | **F24** | …9880484518 | …2999769532 | 512x512x113 | 1.1113, 1.1113, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 23.59 | 246.0 | 1 | 0.0000 % | `6ac0cc72` | `5291f0e6` |
| 7 | `4DLUNG-106_HM10395` | F23 | …2380253394 | …5144859846 | 512x512x103 | 1.1621, 1.1621, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 27.51 | 207.0 | 1 | 0.0000 % | `4c5250b9` | `44da9a2c` |
| 8 | `4DLUNG-107_HM10395` | F23 | …5966589680 | …1607425027 | 512x512x82 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 26.35 | 174.0 | 1 | 0.0000 % | `196b3bca` | `89c4c8e3` |
| 9 | `4DLUNG-108_HM10395` | **F24** | …0716007025 | …6968456978 | 512x512x119 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 30.34 | 246.0 | 1 | 0.0000 % | `97257b6a` | `ca9e4fe5` |
| 10 | `4DLUNG-109_HM10395` | F23 | …3460832263 | …2738982830 | 512x512x112 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 60.69 | 198.0 | 1 | 0.0000 % | `665ceb7c` | `2d957ab3` |
| 11 | `4DLUNG-110_HM10395` | **F24** | …9532865942 | …3407447181 | 512x512x113 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 49.76 | 252.0 | 1 | 0.0000 % | `17e904bb` | `81b5c1d6` |
| 12 | `4DLUNG-111_HM10395` | **F24** | …2839934158 | …6905762069 | 512x512x114 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 37.88 | 219.0 | 1 | 0.0000 % | `56dcfa50` | `53f1f892` |
| 13 | `4DLUNG-112_HM10395` | **F24** | …8078834722 | …7880556175 | 512x512x118 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 27.68 | 243.0 | 1 | 0.0000 % | `88540440` | `7d6997fd` |
| 14 | `4DLUNG-114_HM10395` | **F24** | …8666941182 | …6113826031 | 512x512x131 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 37.18 | 264.0 | 1 | 0.0000 % | `9ea7668a` | `b44d97e1` |
| 15 | `4DLUNG-115_HM10395` | F23 | …8374106742 | …0741961243 | 512x512x104 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 32.89 | 240.0 | 1 | 0.0000 % | `cb4c76c6` | `4bf1eec0` |
| 16 | `4DLUNG-116_HM10395` | **F24** | …2799691968 | …2674751894 | 512x512x118 | 0.9766, 0.9766, 3 | `Esophagus_c00` | SEMIAUTOMATIC | LPS | 30.71 | 249.0 | 1 | 0.0000 % | `e4b2d333` | `3b89da80` |

**F23** = já auditado na Fase 23 e reproduzido campo a campo aqui · **F24** = ingerido nesta fase.

---

## Adendo (Fase 25) — a desidentificação **é declarada em fonte primária**, e a seção 7 estava incompleta

**O texto acima está preservado como foi escrito.** Esta correção segue a regra 16: registrar,
corrigir a documentação quando a evidência justificar, e manter o histórico da correção.

A seção 7 concluiu **"método de desidentificação UNKNOWN"** porque a Fase 24 só inspecionou as
tags de PHI (`PatientName`, `AccessionNumber`, tags privadas). Ao montar o manifesto, a Fase 25
abriu as tags do **grupo 0012** — o grupo em que o DICOM registra a própria desidentificação — e
elas **não estão vazias**:

| Tag | Valor, em 16/16 |
|---|---|
| `PatientIdentityRemoved` (0012,0062) | **`YES`** |
| `DeidentificationMethod` (0012,0063) | `Per DICOM PS 3.15 AnnexE. Details in 0012,0064` |
| `LongitudinalTemporalInformationModified` (0028,0303) | **`MODIFIED`** |
| `InstitutionName` | **ausente** |
| `PatientBirthDate` | vazio · `PatientAge` ausente · `PatientSex` retido (9 M / 7 F) |

`DeidentificationMethodCodeSequence` (0012,0064), em 16/16:

```
113100  Basic Application Confidentiality Profile
113101  Clean Pixel Data Option
113105  Clean Descriptors Option
113107  Retain Longitudinal With Modified Dates Option
113108  Retain Patient Characteristics Option
113109  Retain Device Identity Option
113111  Retain Safe Private Option
```

**O que muda.** Existe **declaração explícita e estruturada** do perfil de desidentificação
aplicado, em fonte primária (o próprio arquivo). A frase da seção 7 — *"método de
desidentificação UNKNOWN"* — **estava errada**, e o certo é: **perfil declarado, `PS 3.15 Annex E`,
Basic Application Confidentiality Profile com cinco opções de retenção nomeadas.**

**O que NÃO muda (regra 13).** O projeto continua **não declarando o dataset anonimizado**.
Uma declaração do produtor é evidência do que ele afirma ter feito, não verificação independente
de que foi feito. Não auditamos pixel data em busca de *burned-in*, e `Retain Device Identity` e
`Retain Safe Private` são retenções deliberadas. O estado correto é: **desidentificação declarada
em fonte primária, com perfil nomeado; conformidade não verificada de forma independente por
este projeto.**

**E três achados da Fase 24 deixam de ser mistério:**

1. `AccessionNumber` idêntico nos 16 e `PatientName` = `P100`…`P116` são **o efeito esperado** do
   *Basic Application Confidentiality Profile*, que substitui em vez de remover.
2. `institution` = **UNKNOWN em 16/16** não é desleixo nosso: a tag `InstitutionName` foi
   **removida na origem**. UNKNOWN é a resposta correta, e agora com causa conhecida.
3. `annotation_date_known` = **False** é confirmado por `Retain Longitudinal With Modified Dates`
   e `LongitudinalTemporalInformationModified = MODIFIED`: as datas **existem mas foram
   deslocadas**. Há data no arquivo; a data verdadeira não é conhecida. Isso também explica os
   `StudyDate` de 1997–2003 numa coleção publicada muito depois.

**Fato adicional registrado:** `Manufacturer` / `ManufacturerModelName` = **`ADAC` / `Pinnacle3`**
em 16/16 — um sistema de **planejamento de radioterapia**, não um tomógrafo. **INFERÊNCIA:** as
séries foram exportadas pelo TPS, o que é coerente com um fluxo de planejamento de RT e com o
`SEMIAUTOMATIC` do RTSTRUCT. **Não se conclui** daí qual foi o equipamento de aquisição.
