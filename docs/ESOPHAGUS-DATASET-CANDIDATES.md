# Candidatos a dataset de esôfago — matriz completa

Consulta: **2026-09-06** · 7 arms · **230 consultas registradas** · **79 candidatos**
Crivo: `ESOPHAGUS_ONTOLOGY_V1` (congelada 2026-09-06)

| Classe | N | Significado |
|---|---:|---|
| **A** — adequado | **0** | passa nos sete filtros |
| **B** — potencialmente adequado | **1** | HaN-Seg, por reclassificação |
| **C** — inadequado | **57** | falha de definição, objeto ou GT |
| **D** — inacessível | **14** | existe, não se pode obter dentro das travas |
| **E** — independência indeterminada | **7** | tudo o mais passa; a independência não |

**Nenhum candidato é classe A**, e a razão é sempre a mesma: o TotalSegmentator v2 declara
1.559 imagens de treino com **420 não atribuídas**, logo a independência de **nenhum** dataset
público pode ser presumida.

---

## 1. Os candidatos que importam — classe E e B

### 1.1 LyNoS — o achado novo desta fase

| Campo | Valor |
|---|---|
| **Nome** | LyNoS / `ct_mediastinal_structures_segmentation` (Bouget et al., SINTEF + NTNU + St. Olavs Hospital, Trondheim) |
| **Modalidade** | TC torácica/mediastinal **com contraste**, NIfTI completo. Spacing medido: 0,742×0,742×0,5 mm (Pat1), 0,688×0,688×0,5 mm (Pat2) |
| **Estrutura** | **Esôfago em arquivo NIfTI próprio e binário** — `patN_labels_Esophagus.nii.gz`. Também LymphNodes (384), Azygos, BrachiocephalicVeins, SubCarArt |
| **N casos** | **15** TCs (de 31 do St. Olavs; as outras 16 não são públicas) |
| **Licença** | **CONFLITO declarado**: Zenodo `cc-by-4.0`; HuggingFace `mit`; GitHub `MIT` / BSD-2-Clause |
| **Definição do esôfago** | **não documentada em texto — mas MEDIDA** (§1.2) |
| **Proveniência** | 15 casos de câncer de pulmão, Noruega. Canal **não-DICOM**, fora do NBIA |
| **Overlap com TS** | **INDETERMINADO** |
| **Overlap com VRmed** | muito improvável, não demonstrado — instituições, países, canais e modalidade disjuntos |
| **TRAIN? VAL? TEST?** | TEST **com ressalvas** |
| **Status** | **E — independência indeterminada** |
| **URL** | `zenodo.org/records/10102261` · `huggingface.co/datasets/andreped/LyNoS` · `github.com/raidionics/LyNoS` |

### 1.2 A lacuna do LyNoS foi fechada por medição, não por documento

**FATO.** Nenhuma fonte primária do LyNoS menciona RTOG 1106, critério parede/lúmen, ou
limites cranial/caudal. Pela Fase 9, isso seria eliminação por "definição não documentável".

**Mas a definição foi medida.** Baixados **1,80 MiB** — exatamente 2 máscaras de esôfago, com
tamanho conferido por `HEAD` antes; nenhuma TC (180–263 MB cada) e nenhum ZIP (2,90 GB):

| Medida | Pat1 |
|---|---|
| valores únicos | `{0, 1}` — **binária** |
| voxels positivos | 163.849 · volume 45.104,7 mm³ |
| fatias axiais com esôfago | 650 de 829 (z 162–811) = 325,0 mm |
| componentes conexos 3D | 13 · maior/total = **0,9997** |
| **fração de buracos** | **0,028 %** (Pat1) e 0,001 % (Pat2) |

**INFERÊNCIA.** A máscara é exatamente o que a `ESOPHAGUS_ONTOLOGY_V1` pede: binária,
**preenchida** — parede e lúmen como alvo único. A compatibilidade com a ontologia é **SIM**,
estabelecida por medição.

### 1.3 Por que o LyNoS é E e não A

**FATO cronológico que ajuda:** a anotação nasce no artigo de 2019 (Bouget et al., IJCARS),
**três anos antes** do preprint do TotalSegmentator (arXiv 2208.05868, ago/2022). O GT do
esôfago do LyNoS **não pode ser** *model-in-the-loop* do TS.

**FATO que impede A:** anterioridade da anotação não é anterioridade da imagem. As 420
imagens não atribuídas do TS v2 vêm de *"other institutions"*, e nada exclui St. Olavs.
**"Não encontramos overlap" não é "independente".**

**Ressalvas que o tornam TEST com condição, não TEST limpo:**
1. **n=15** — intervalos de confiança largos em Dice/HD95.
2. **TC com contraste, diagnóstica**, não de planejamento — muda a aparência do esôfago e das
   estruturas vizinhas em relação a tudo que o VRmed mediu até aqui.
3. **Conflito de licença** entre três fontes oficiais do mesmo dataset.

### 1.4 Os outros seis da classe E

| Dataset | Licença | Por que E |
|---|---|---|
| **SegRap2023** | nenhuma licença de dado publicada | **CONTESTA a Fase 12**: o site teria aberto o acesso desde 2023-10-31. Sem licença, continua sem servir |
| **HaN-Seg** | CC BY-NC-ND 4.0 | anotação humana, canal não-DICOM legítimo; a definição de esôfago é **cervical**, não torácica |
| **Multi-organ Abdominal CT Reference Standard** | CC BY 4.0 | **primeiro exemplar confirmado** do padrão "segundo grupo re-anota exames públicos" — mas abdominal |
| **MICCAI FLARE22** | CC BY 4.0 | registrado para não ficar fora do log; **não auditado** em fonte primária |
| **Zenodo 1169360/1169361** | CC BY 4.0 | ponteiro cruzado do mesmo Multi-Organ Abdominal |

### 1.5 O único B — HaN-Seg, por reclassificação

**FATO.** É a resposta à pergunta explícita do arm oblíquo: *existe candidato cujo motivo de
eliminação mudou agora que a ontologia está congelada?* **Sim** — o HaN-Seg fora eliminado por
"definição não documentável"; sob a V1 o motivo correto é outro (esôfago **cervical**, não
comparável ao objeto torácico). Muda o motivo, não o veredito.

## 2. Classe D — existe e não se pode obter (14)

**Estes são LACUNAS DECLARADAS, nunca "não tem".** O conteúdo não foi verificado.

| Dataset | Por que inacessível |
|---|---|
| **RADCURE** | maior conjunto de RTSTRUCT do TCIA (3.337); acesso controlado, NIH Controlled Data Access Policy |
| **OPC-Radiomics** | **17ª coleção** da classe "declara RTSTRUCT/SEG e fica fora da API anônima" — achado novo |
| **HNC-IMRT-70-33** | esôfago presente no vocabulário público; acesso fechado |
| **iCurveE** | já classificado na Fase 12; esta consulta acrescenta evidência |
| **estudo de *edge roughness*** | **o exemplo mais nítido do padrão que a fase procura** — multi-médico no esôfago — e inacessível |
| **BTCV / Multi-Atlas Beyond the Cranial Vault** | exige entrar no *team* do Synapse; a fase não pode aceitar termo |
| **WORD** | exige solicitação de acesso em nome do usuário — proibido |
| **HND (SoMNet)** | exige assinatura do IEEE DataPort |
| **RTOG-0617 / NRG-1308** | acesso restrito (Fases 11–12) |

**Nenhuma dessas foi aberta.** Nenhum termo foi aceito, nenhuma conta criada, nenhum acesso
solicitado.

## 3. Classe C — amostra dos 57

| Dataset | Motivo |
|---|---|
| `TCGA-ESCA` | só CT, **nenhuma segmentação** |
| `CMB-GEC` | único achado cujo `cancer_location` é literalmente gastroesofágico — sem contorno de OAR |
| `EAY131-Tumor-Annotations` | sítio de lesão, não OAR — refina o censo da Fase 11 |
| `StructSeg2019-T3` | sem licença **e** desafio abandonado |
| `AMOS22` | licença conflitante + GT *model-in-the-loop* |
| `SynthRAD2023/2025` | único desafio ativo com TC torácica de RT e licença aberta — mas a tarefa é síntese, não segmentação |
| `DoseRAD2026` | casos torácicos, licença aberta, tarefa é cálculo de dose |
| `HaN-Seg2023` | reprovado no crivo da V1 **por definição**, não por acesso |

## 4. Log de consultas — o que torna a busca reproduzível

**230 consultas**, por fonte:

| Fonte | N |
|---|---:|
| WebSearch | 33 |
| WebFetch | 20 |
| Europe PMC REST `/search` | 19 |
| Zenodo API `/api/records` (frase exata) | 13 |
| Zenodo API `/api/records` (booleano) | 12 |
| DataCite API | 9 |
| Figshare API `/v2/articles/search` | 8 + 3 |
| Synapse/Sage REST `/repo/v1/search` | 7 |
| PhysioNet `physionet.org/content/` | 7 |
| grand-challenge.org (busca + API) | 3 + 2 |
| HuggingFace Datasets API | 3 |
| TCIA WordPress REST API | 2 |
| TCIA sitemap XML (2ª fonte independente) | 2 |
| curl `zenodo.org/api/records` | 2 |
| outras | resto |

**Fontes cobertas:** TCIA/IDC (reexecução do censo), Zenodo, Figshare, Dryad, OSF, DataCite,
Synapse/Sage, PhysioNet, MIDRC, Stanford AIMI, HuggingFace, ScienceDB, Kaggle (só descoberta),
Grand Challenge, Europe PMC, arXiv/medRxiv, repositórios institucionais.

## 5. Limitações desta matriz

- **FATO.** A execução foi interrompida pelo fim da sessão durante a etapa de fonte primária.
  **7 de 7 arms concluíram**; **6 fichas** de fonte primária foram salvas; as demais não
  rodaram. Recuperado do journal do workflow, não refeito.
- **FATO.** **FLARE22 não foi auditado** em fonte primária — está na matriz como ponteiro.
- **FATO.** Os 14 candidatos de classe D **não tiveram conteúdo verificado**.
- **INFERÊNCIA.** A cobertura de repositórios é ampla mas não exaustiva; um dataset publicado
  depois de 2026-09-06 não está aqui.
