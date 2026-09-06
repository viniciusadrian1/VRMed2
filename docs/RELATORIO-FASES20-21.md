# Fases 20–21 — dados auditáveis e o funil de ingestão

Execução autônoma · 2026-09-06 · **Nada treinado · Split congelado intocado**

> **A Fase 20 mudou a pergunta e a resposta mudou junto.** As Fases 11 e 15 procuravam
> *teste independente*; a Fase 20 procura dados para um dataset **próprio**. E a resposta
> não é um dataset: **o canal DICOM resolve identidade por completo e procedência da
> anotação não resolve de jeito nenhum.**
>
> **A Fase 21 provou o funil em arquivos reais** — e três defeitos meus apareceram, todos
> por controle, nenhum por revisão.

---

## Fase 20 — Dados auditáveis

### Candidatos

**47 candidatos · 235 consultas registradas · 15 fontes.**

| A | B | C | D | E | F |
|---:|---:|---:|---:|---:|---:|
| 3 | 2 | 4 | 14 | 6 | 18 |

**Nenhum dos três classe A é um dataset:** dois são **canais** (TCIA, IDC) e um é
**documento normativo** (atlas Kong et al. 2011).

### Fontes

TCIA 41 · Zenodo 37 · IDC 26 · arXiv 12 · HuggingFace 10 · Europe PMC 10 · DataCite 10 ·
GitHub 8 · PubMed 7 · Figshare 4 · Grand Challenge 4 · Dryad 1 · OSF 1 · PhysioNet 1 ·
outras 63. **Nenhuma conta criada, nenhum termo aceito, nenhum acesso solicitado.**

### Licenças

**Legíveis por máquina:** `idc_index.parquet` traz `license_short_name` **por série**.
97 % do IDC é CC BY 3.0/4.0. Mas **varia dentro da coleção**, e o caso concreto morde: as
RTSTRUCT de esôfago do **NSCLC-Radiomics são CC BY-NC 3.0** — mais restritivas que a
manchete da coleção que o VRmed já usou.

### Identidade

| Canal | das 4 chaves | Composição |
|---|---:|---|
| **DICOM** | **4** | **3 declaradas pelo produtor** (`PatientID`, `StudyInstanceUID`, `SeriesInstanceUID`) + `sha256` computado localmente |
| **NIfTI** | **2** | `case_id` externo + `sha256` computado |

**Correção conceitual imposta por um cético:** `sha256` **não é identidade DICOM** — é
hash de conteúdo, calculado localmente, e existe **igualmente nos dois canais**. O ganho
real do DICOM é **+2**. O número (4 × 2) não muda; a composição estava errada.

**Máscara ligada à imagem por identificador: 908/908** via `ReferencedSeriesInstanceUID`.

**E um limite do próprio DICOM:** `13.081 de 58.060` séries de versões anteriores do IDC
(**22,5 %**) têm UID **ausente** do índice corrente. `series_id` detecta vazamento
**hoje**; entre *releases*, **só o `sha256` não deriva** — argumento **medido** a favor do
desenho de quatro chaves.

### Procedência — o gargalo, e é total

**`ROIGenerationAlgorithm` está VAZIA nas 908 RTSTRUCT com esôfago-órgão do canal público
inteiro.** A Fase 11 registrou ~25 % de preenchimento no geral; **para o esôfago são 0 %**.

Identidade e licença são verificáveis por máquina. **Procedência não é** — e é a única
cujo modo de falha é **silencioso e irreversível**.

**O negativo perfeito:** `totalsegmentator_ct_segmentations` — **378.153 séries, 26.194
sujeitos, CC BY 4.0, DICOM completo, inclui esôfago** — e é saída de modelo. O canal de
*analysis results* tem **471.946 séries derivadas**.

### Overlap

Quatro instrumentos, **cada um com sensibilidade declarada** (§6 do relatório da fase).
Onde não houve detecção, está escrito **"não detectado pelo instrumento X"** — nunca "não
houve overlap".

### Ranking

1. **Canal IDC/TCIA** — 4 identidades, licença por série, máscara↔imagem por UID.
   Bloqueio: nenhum como canal; a procedência **não vem do canal**.
2. **Atlas Kong et al. 2011** — a **regra**, não o dado. Não altera a ontologia.
3. **Pediatric-CT-SEG** — o melhor dataset por metadado: **359 sujeitos, 1:1, CC BY 4.0,
   identidade completa, GT manual por quatro analistas com revisão de radio-oncologista
   certificado, esôfago em 353/359** — e reprovado na **ontologia**: idade **mediana 6
   anos, 100 % abaixo de 18**, medida no `PatientAge` do índice.

**Nenhum promovido automaticamente.**

### Bloqueios

procedência `UNKNOWN` em 908/908 · o melhor dataset é pediátrico · 4D-Lung tem 6.690
séries de **20 sujeitos** · licença varia por série · 14 candidatos inacessíveis · LCTSC e
NSCLC-Radiomics **já usados**, split congelado.

---

## Fase 21 — Funil

### DICOM

Fixture real escrita com `pydicom`. Entrega `PatientID`, `StudyInstanceUID`,
`SeriesInstanceUID` e `SOPInstanceUID` (8/8 únicos), mais `PixelSpacing`,
`SliceThickness`, `ImagePositionPatient`, `ImageOrientationPatient`, `RescaleSlope` e
`RescaleIntercept`.

### NIfTI

**2 das 4 chaves.** `study_id` e `series_id` são `UNKNOWN` porque **o cabeçalho NIfTI-1
não tem campo para eles** — ausência no formato, não na nossa leitura. **Consequência:
duas das quatro regras anti-vazamento ficam inverificáveis** para um caso NIfTI.

### Anonimização

Quatro eixos — 24 tags do PS3.15 Anexo E, UIDs, tags privadas, caminho e nome. Veredito
**"SEM ACHADO NAS QUATRO VARREDURAS"**, acompanhado do que **não** significa: pixel não
foi lido, reidentificação por combinação não é avaliada, licença aberta **não é**
consentimento. `PatientID` e UIDs saem **`INDETERMINADO`**, nunca `OK`.

### Ontologia

**E aqui a Fase 21 pagou uma dívida que ninguém tinha cobrado.** O crítico apontou que a
propriedade central da `ESOPHAGUS_ONTOLOGY_V1` — máscara **preenchida** — **nunca fora
verificada voxel a voxel** no dado que o projeto **já usa**.

Medido nas 60 máscaras de esôfago do LCTSC: **buracos 2D = 0,0000 % em 60/60.**
A propriedade **se confirma** no GT do split congelado.

**E a medição achou um bug meu:** as 60 reprovavam no critério `binária` porque usam
`{0, 255}` — que é **a convenção de foreground do próprio projeto**
(`dataset_esofago.FOREGROUND = 255`). O validador do funil **rejeitaria o dado que o
projeto usa**. Corrigido: binária = no máximo dois valores distintos, um deles 0.

### Hashes

`sha256` de imagem, máscara, manifesto e snapshot. Manifesto **JSONL canônico**, hash
**independente da ordem de inserção**. `congelar()` recusa manifesto inválido.

### Manifesto

Determinismo e reexecução verificados (21.11, 21.12), incluindo o **teste de sinal
contrário**: dois diretórios diferentes produzem hashes **diferentes**, porque o caminho
entra no manifesto.

### Split

**Quatro identidades.** Casos 09–12 provam a detecção por `case_id`, `study_id`,
`series_id` e **conteúdo**.

### TEST isolation

Por **exceção**, não por convenção de nome. Casos 14 e mutantes L1–L3.

### Mutation

**13/13 mortos** (5 validators, 5 loader, 3 hashing), numa **cópia** da árvore, com
controle negativo antes e depois.

**A primeira rodada deu 12/13.** O sobrevivente **L4** — *contexto desconhecido deixa de
ser recusado* — expôs que **nada testava** essa guarda. Um contexto digitado errado
devolveria lista vazia em silêncio. Teste acrescentado.

### Determinismo

Duas passadas independentes: **mesmos `sha256` de conteúdo**. Duas execuções no mesmo
diretório: **mesmo manifesto e mesmo snapshot**.

---

## Critérios K

| | Estado | Por quê |
|---|---|---|
| **K1** — desenho TRAIN/VAL/TEST defensável | **BLOQUEADO** | desenho e funil prontos e testados; **zero casos** com procedência completa |
| **K2** — baseline comparável sem vazamento conhecido | **BLOQUEADO** | inalterado: circularidade SegTHOR/BTCV + 420 imagens não atribuídas |
| **K3** — avaliação futura com conjunto independente | **BLOQUEADO** | nenhum candidato classe A é dataset |
| **K4** — definição do alvo congelada | **RESOLVIDO** | e agora **verificada no GT que o projeto usa**: 60/60 preenchidas |

## Estado do dataset próprio

**Esquema pronto, funil provado, zero casos.** `VRMED-ESOPHAGUS-DATASET-V1` intacto com
22 campos; a [proposta de V2](VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md) permanece
**proposta**, com recomendação explícita de **não promover agora**.

## Estado do treinamento

# **BLOQUEADO**

Nem a Fase 20 nem a Fase 21 o desbloqueiam, e nenhuma tentou.

## O que mudou

- **A pergunta.** TRAIN não precisa de independência do TotalSegmentator; precisa de
  identidade, procedência, licença e GT humano.
- **A rota deixou de ser hipotética.** O canal DICOM entrega identidade e licença
  verificáveis por máquina, e a máscara vem ligada à imagem por identificador em 908/908.
- **O gargalo mudou de nome.** Não é mais "independência"; é **procedência da anotação**,
  `UNKNOWN` em 908/908.
- **A ontologia foi verificada onde nunca tinha sido:** no GT do split congelado.
- **Três defeitos meus corrigidos**, mais dois vãos latentes do crivo herdado **medidos e
  não editados** (o instrumento é auditado e o número 908 está publicado).

## O que NÃO mudou

- **K1, K2 e K3 continuam bloqueados.**
- **A `ESOPHAGUS_ONTOLOGY_V1` não foi alterada** — nem quando apareceram duas regras de
  extensão publicadas e divergentes (Kong 2011 no cricoide; STOPSTORM no arco aórtico).
  Isso **reforça** a decisão de herdar a extensão do GT.
- **O MASTER de reconstrução** não foi tocado.
- **O split congelado** segue `INTOCADO` (`sha256` `6e54c02b58bbb9b3a1667d4672eddef6…`).
- **Nada foi treinado, avaliado, ou solicitado a terceiros.**

## Auditoria final

**PASS = 307 · FAIL = 0 · SKIP = 0** — 49 de suíte + 217 de autoteste de módulo +
41 de mutação (13 da Fase 21, 21 do `interobservador`, 7 do `estilo_esofago`).
Varredura de docs: **48 documentos, 0 violações**.
Split congelado: `sha256` `6e54c02b58bbb9b3a1667d4672eddef6…` · development 30 ·
validation 15 · test 15 · **INTOCADO**.

## Contradição declarada e não resolvida

Sobre a **extensão cervical**: dois céticos reprovaram o SegTHOR porque seu esôfago começa
na **4ª vértebra cervical**; um terceiro chamou isso de critério inconsistente, apontando
que o **LCTSC — que o VRmed já usa, com split congelado** — teria definição comparável.

**Não resolvido.** A resolução exige ler a definição de extensão do LCTSC contra a do
SegTHOR em fonte primária, e o resultado pode atingir uma coorte **já em uso**.

## Próxima ação única

> **Ler o artigo primário do LCTSC (AAPM 2017 Thoracic Auto-segmentation Challenge) e
> extrair a definição de extensão do esôfago e a autoria do contorno — e confrontá-la com
> Kong 2011.**

É a ação certa por três razões medidas nesta execução: resolve a **única contradição que a
fase deixou aberta**, e ela é contra o próprio projeto; ataca o **gargalo real** —
procedência — no único conjunto onde o VRmed pode agir sem pedir acesso a ninguém; e é a
lacuna que o crítico nomeou como a mais grave: **ninguém nunca leu quem contornou o
esôfago do dado que o projeto já usa**.
