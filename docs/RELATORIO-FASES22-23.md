# Fases 22–23 — o GT do LCTSC e o primeiro dataset auditável

Execução autônoma · 2026-09-06 · **Nada treinado · Split histórico intocado**

> **Duas coisas grandes aconteceram, e uma delas foi contra o próprio projeto.**
>
> A Fase 22 abriu os 60 RTSTRUCT do LCTSC — **primeira vez em 22 fases** — e o que estava
> lá dentro **derrubou o achado principal da Fase 20**. A contradição que a Fase 21 deixou
> aberta resolveu-se **contra nós**.
>
> A Fase 23 fez o funil processar **dado clínico real**, baixado nesta execução: **5/5
> elegíveis**.

---

# Fase 22

## Definição LCTSC

**Documentada e verificada em fonte primária.** A afirmação que o repositório já fazia —
*"do nível abaixo do cricoide à junção gastroesofágica (atlas RTOG 1106)"* — está
**correta**, confirmada por três céticos independentes que abriram Yang et al. 2018 e a
página do TCIA.

| | LCTSC declara |
|---|---|
| cranial | *"at the level just below the cricoid"* — operacional: a fatia abaixo da primeira em que a lâmina da cricoide aparece |
| caudal | *"its entrance to the stomach at GE junction"* |
| parede | *"the mucosal, submucosa, and all muscular layers out to the fatty adventitia"* |
| janela | *"mediastinal window/level on CT"* |
| lúmen · conteúdo | **não declarados** |

## Autoria

**`UNKNOWN`, e essa é a resposta.** O GT são **contornos clínicos de rotina** de três
serviços, reaproveitados: *"The manual contours that were used in clinic for treatment
planning were used as ground 'truth.'"*

- **quantos anotadores:** UNKNOWN · **especialidade:** UNKNOWN
- **revisão:** **uma**, por **uma** pessoa — organizador do desafio, físico médico clínico
- **consenso · adjudicação:** não houve

**Confirmado no arquivo:** `ROIGenerationAlgorithm` = **`MANUAL` em 59/60**;
`ContentCreatorName`, `ReviewerName`, `OperatorsName`, `InstitutionName`, `StationName`
**vazias em 60/60**. Método declarado, autor não identificado — texto e tag concordam.

## Protocolo

**`RTOG 1106` é um ENSAIO, não um atlas.** A string aparece **zero vezes** em Kong et al.
2011 — a única ocorrência de "1106" ali é número de página. E ainda assim os dois nomes
circulam de forma intercambiável, e o LCTSC cita *"the RTOG 1106 contouring atlas"*.

**A `ESOPHAGUS_ONTOLOGY_V1` congelou um nome ambíguo.** Registrado. **Não alterado.**

## RTOG 1106 · Kong 2011 · VRMed

**Três convenções publicadas para o mesmo limite cranial:**

| Fonte | Cranial |
|---|---|
| Kong et al. 2011 (artigo) | *"at the level of cricoid cartilage"* |
| *Deck* oficial da NRG | *"just below the"* |
| STOPSTORM (Fase 20) | **arco aórtico** |

O próprio Kong 2011 registra a variabilidade de extensão como problema **sem consenso**.

## Contradições — a que fecha contra o projeto

O SegTHOR foi reprovado por delinear a partir da **4ª vértebra cervical**. Um avaliador
chamou o critério de inconsistente. **Ele estava certo.**

O LCTSC **não é omisso** — declara a extensão de forma **mais operacional que o SegTHOR** —
e começa **logo abaixo da cricoide**, que é **onde o esôfago começa**. **O GT do LCTSC
também cobre o esôfago cervical.**

**E a medição concorda com o documento**, por duas vias independentes:

| Coorte | esôfago acima do ápice pulmonar | casos |
|---|---|---|
| **LCTSC** (60) | mediana **+17,5 mm** | **54/60** |
| **4D-Lung** (5) | mediana **+21,0 mm** | **5/5** |

**Limite:** *acima do ápice* ≠ *cervical*. A fronteira é o opérculo torácico, que nenhuma
coorte declara e que a Fase 9 mediu como **não localizável**. A medida mostra que sobe;
**não prova** onde cruza.

**E o desafio tolera sobre-extensão:** *"participants would not be penalized for contouring
too great an extent of these structures"*.

**`ONTOLOGY_CHANGE: NÃO`.** A fase **vindica** a posição da ontologia — extensão herdada do
GT, marcos não localizáveis — e agora com razão documentada.

## A correção que a Fase 22 impôs à Fase 20

Abrir os arquivos derrubou o achado central da fase anterior.

| | Fase 20 dizia | Correto |
|---|---|---|
| `ROIGenerationAlgorithm` nos 908 | **UNKNOWN em 908/908** | **MANUAL 731 · SEMIAUTOMATIC 101 · INDETERMINADO 42 · UNKNOWN 34** |

**A causa era minha.** A coluna do índice é **deduplicada** — `len` é sempre 0, 1 ou 2,
nunca um valor por ROI. Meu leitor exigia `len(algos) == len(nomes)` para alinhar por
posição, e tudo caía em `UNKNOWN`.

**Duas validações cruzadas dão confiança na correção:** o índice diz `MANUAL 59 / vazio 1`
para o LCTSC e os **arquivos dizem exatamente isso**, caso a caso; e diz `SEMIAUTOMATIC`
em 101/101 do 4D-Lung, cujo artigo descreve propagação por registro rígido. **A tag é
honesta.**

Correção propagada a quatro documentos, **com o texto original preservado**.

---

# Fase 23

## Fontes e candidatos

Candidatos da Fase 20 revistos sob a **regra nova**: para TRAIN não é preciso provar
independência do TotalSegmentator no nível impossível que o TEST exige.

**4D-Lung** foi escolhido — não por ser o melhor, por ser o **mais informativo**: objeto
certo, CC BY 3.0 **por série**, DICOM com as três identidades, vínculo por UID, e
`SEMIAUTOMATIC` declarado no arquivo.

## Aquisição

Tamanho **registrado antes** (265,3 MB; teto 400 MB declarado antes de olhar) ·
**5 sujeitos distintos** — nunca séries · **108,2 MB** baixados · NBIA anônimo ·
**nenhuma conta, nenhum termo, nenhum pedido de acesso**.

## Identidade

`PatientID`, `StudyInstanceUID`, `SeriesInstanceUID`, `SOPInstanceUID` + `image_sha256` e
`mask_sha256` calculados. **4/4 chaves do esquema em 5/5.** O `SOPInstanceUID` é extra, não
substituto.

## Proveniência

`SEMIAUTOMATIC` declarado no arquivo · máscara **derivada** (RTSTRUCT poligonal → voxel) ·
`annotation_protocol` **UNKNOWN** · `institution` **UNKNOWN** · `annotation_date_known`
**False**.

**Circularidade investigada:** propagação por **registro rígido** com ajuste manual por
fase. Registro rígido **não é modelo de segmentação** — a recusa dura não se aplica. Mas o
pool **não é referência humana pura**, e isso está no manifesto, não na memória de quem leu.

## Licença

**CC BY 3.0, lida por série.** Não é detalhe: na mesma varredura, as RTSTRUCT de esôfago do
NSCLC-Radiomics saíram **CC BY-NC 3.0**, mais restritivas que a manchete da coleção.

## Anotação

Humana clínica, com propagação geométrica. **Nenhum caso tratado como padrão humano puro.**

## Ontologia

**5/5 aprovados.** Buracos 2D **0,0000 %** · volumes 26,4–60,7 mL · extensão 174–249 mm ·
orientação LPS. Faixa compatível com o LCTSC (24,2–90,6 mL; 150–270 mm).
**Nenhuma máscara editada.**

## Anonimização

3 achados por caso: `PatientName` = `P104`…`P115` (pseudônimo), `AccessionNumber`
**idêntico nos 5** (placeholder), 3 tags privadas. Caminho OK.
**Nenhum caso declarado anonimizado.**

## Pool

**5 casos**, `split` = `"NAO ATRIBUIDO"` em todos. **Nenhum split congelado, nenhuma
proporção fixada.** Com n=5, fixar seria escolher o resultado antes de ter o dado.

## Split

**Não congelado.** O TEST futuro permanece protegido, e o pool **não é candidato a TEST**.

## Bloqueios

n=5 · pool inteiro `SEMIAUTOMATIC` · `institution` e `annotation_protocol` UNKNOWN ·
`StudyDate` deslocado · **nenhum TEST**.

---

## Critérios K

| | Estado | Por quê |
|---|---|---|
| **K1** | **BLOQUEADO** — mas mexeu | pela primeira vez existe **pool real com procedência completa**: 5 casos. Insuficiente para desenho, suficiente para provar que o funil funciona em dado clínico |
| **K2** | **BLOQUEADO** | inalterado: circularidade SegTHOR/BTCV + 420 imagens não atribuídas |
| **K3** | **BLOQUEADO** | nenhum candidato a TEST; o pool novo é TRAIN/VALIDATION |
| **K4** | **RESOLVIDO** | e agora com a definição do GT do LCTSC **lida em fonte primária** e a extensão medida em duas coortes |

## Estado do dataset próprio

**Esquema V1 intacto (22 campos) · funil provado em dado real · 5 casos no pool · nenhum
split congelado.**

A V1 **absorveu os 5 casos sem precisar de campo novo**. A [proposta de
V2](VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md) **continua proposta** — e ganhou evidência: o
`SEMIAUTOMATIC` viajou em **texto livre**, não em campo tipado, que é exatamente a lacuna 2
da proposta.

## Treinamento

# **BLOQUEADO**

Nenhuma das duas fases o desbloqueia, e nenhuma tentou.

## Próxima ação única

> **Ingerir os 11 sujeitos restantes do 4D-Lung com esôfago (16 no total, 5 já feitos) e
> congelar o pool como TRAIN/VALIDATION do `VRMED-ESOPHAGUS-DATASET-V1` — deixando TEST
> vazio e explicitamente protegido.**

É a ação certa por três razões medidas: o funil **já provou** que processa esta coleção
sem exceção (5/5); **16 sujeitos** é o teto real da coleção e conhecê-lo evita planejar
sobre um número inflado (as 101 séries são 16 sujeitos); e congelar TRAIN/VALIDATION
**sem** TEST é o único movimento que aumenta K1 sem tocar em K3.

---

## Auditoria final

**PASS = 340 · FAIL = 0 · SKIP = 0** — 49 de suíte + 250 de autoteste de módulo +
41 de mutação (13 da Fase 21, 21 do `interobservador`, 7 do `estilo_esofago`).
Varredura de docs: **54 documentos, 0 violações**.
Split congelado: `sha256` `6e54c02b58bbb9b3a1667d4672eddef6…` · development 30 ·
validation 15 · test 15 · **INTOCADO**.

## Os defeitos que os controles pegaram

| # | Defeito | Como apareceu |
|---|---|---|
| 1 | **"908/908 UNKNOWN" da Fase 20** — coluna deduplicada lida como lista paralela | abrir os 60 arquivos do LCTSC contradisse o índice |
| 2 | `Manufacturer = Plastimatch` e `StructureSetLabel = AutoSS` usados como sinal de automação na Fase 20 | **aparecem no LCTSC**, contorno clínico humano — a tag nomeia quem escreveu o arquivo |
| 3 | harness de mutação abortou | **o controle negativo** detectou que a árvore copiada não tinha `docs/` |
| 4 | linha malformada em `pool.py` | `SyntaxError` na primeira execução |
