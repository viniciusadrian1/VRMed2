# Fase 15 — busca exaustiva de teste independente

Data: 2026-09-06 · 7 arms · 230 consultas · 79 candidatos · Nada treinado

> **CENÁRIO B — TEST parcialmente defensável, com ressalvas.**
> A fase encontrou algo que 14 fases anteriores não tinham: **um dataset público, acessível,
> com esôfago torácico em máscara binária preenchida, fora de tudo que o VRmed já usou, e com
> GT anterior ao TotalSegmentator** — o **LyNoS**. Ele **não** resolve K1/K3 sozinho, e a
> razão está medida, não suposta.

Matriz completa: **[`docs/ESOPHAGUS-DATASET-CANDIDATES.md`](ESOPHAGUS-DATASET-CANDIDATES.md)**

---

## 1. Objetivo e escopo

Tentar encontrar um dataset de teste independente que resolva **K1** (desenho
TRAIN/VAL/TEST defensável) e **K3** (avaliação futura com conjunto independente).

**Escopo INCREMENTAL, declarado antes de buscar.** A Fase 11 já enumerou o canal DICOM
público inteiro — 19.358 RTSTRUCT do índice IDC, dos quais 908 com esôfago-órgão em apenas 5
coleções, e **zero** com dois contornos humanos no mesmo exame. Repetir aquilo seria trabalho
duplicado. Esta fase atacou as **cinco lacunas que a Fase 11 declarou**: o canal não-DICOM, as
16 coleções fora da API anônima, os repositórios não varridos, os suplementos de artigo, e o
que foi publicado depois do censo.

## 2. Estratégia e log

**FATO.** 7 arms, **230 consultas com fonte, string e data registradas** (§4 da matriz).
Fontes: TCIA/IDC · Zenodo · Figshare · Dryad · OSF · DataCite · Synapse/Sage · PhysioNet ·
MIDRC · Stanford AIMI · HuggingFace · ScienceDB · Kaggle (só descoberta) · Grand Challenge ·
Europe PMC · arXiv/medRxiv · repositórios institucionais.

**Sem log de consulta, um arm de busca não é evidência — é testemunho.** Foi por isso que o
log virou requisito desta fase.

## 3. O achado — LyNoS

**FATO.** `LyNoS` / `ct_mediastinal_structures_segmentation` (Bouget et al., SINTEF + NTNU +
St. Olavs Hospital, Trondheim). 15 TCs mediastinais, esôfago em **arquivo NIfTI próprio e
binário**, canal não-DICOM, fora do NBIA.

### 3.1 A lacuna que o travava foi fechada por MEDIÇÃO

Nenhuma fonte primária do LyNoS menciona RTOG 1106 nem critério parede/lúmen. Pela regra da
Fase 9 isso seria eliminação por "definição não documentável" — o mesmo motivo que derrubou o
`Pediatric-CT-SEG`.

**Mas a definição foi medida.** Baixados **1,80 MiB** — 2 máscaras de esôfago, tamanho
conferido por `HEAD` **antes** do download; nenhuma TC (180–263 MB cada), nenhum ZIP (2,90 GB):

| Medida | Pat1 | Pat2 |
|---|---|---|
| valores únicos | `{0, 1}` | `{0, 1}` |
| **fração de buracos** | **0,028 %** | **0,001 %** |
| componentes conexos 3D | 13 (maior/total 0,9997) | — |
| volume | 45.104,7 mm³ | — |
| extensão axial | 650 fatias, 325,0 mm | — |

**INFERÊNCIA.** É exatamente o que a `ESOPHAGUS_ONTOLOGY_V1` especifica: máscara binária
**preenchida**, parede e lúmen como alvo único. **Compatibilidade com a ontologia: SIM,
estabelecida por medição.**

Este é o retorno concreto de ter congelado a ontologia na Fase 13: um candidato que a regra
antiga descartaria por silêncio documental passa agora por **verificação direta do artefato**.

### 3.2 Por que ele é classe E e não A

**A favor** — e é bastante:

- **FATO cronológico.** A anotação nasce no artigo de 2019 (IJCARS), **três anos antes** do
  preprint do TotalSegmentator (arXiv 2208.05868, ago/2022). O GT do esôfago do LyNoS **não
  pode ser** *model-in-the-loop* do TS.
- **FATO.** Instituições, país, canal de distribuição e modalidade **disjuntos** do LCTSC e do
  NSCLC-Radiomics: Noruega × EUA/Países Baixos; NIfTI no Zenodo/HuggingFace × DICOM no NBIA.
- **FATO.** Acessível sem conta e sem termo.

**O que impede A, e é decisivo:**

**Anterioridade da anotação não é anterioridade da imagem.** As 420 imagens não atribuídas do
TS v2 vêm de *"other institutions"*, e nada exclui St. Olavs. Pela regra desta fase —
**"não encontramos overlap" não é "independente"** — a classe é **E**.

### 3.3 As três ressalvas que o tornam TEST condicional

1. **n = 15.** Intervalos de confiança largos em Dice e HD95.
2. **TC com contraste, diagnóstica** — não de planejamento. A aparência do esôfago e das
   estruturas vizinhas difere de tudo que o VRmed mediu até aqui. **INFERÊNCIA:** comparar
   Dice medido aqui com o 0,7880 do LCTSC mediria também a diferença de protocolo.
3. **Conflito de licença entre três fontes oficiais do mesmo dataset**: Zenodo declara
   `cc-by-4.0`, HuggingFace declara `mit`, GitHub declara `MIT`/BSD-2-Clause. **Na dúvida,
   vale a mais restritiva**, e o conflito precisa ser resolvido antes de qualquer uso.

## 4. O que mais a fase encontrou

**FATO.** 79 candidatos: **0 em A**, 1 em B, 57 em C, **14 em D**, 7 em E.

**Achados que corrigem ou refinam fases anteriores:**

- **SegRap2023** — a ficha da Fase 12 dizia *"gated por acordo assinado"*; este arm registra
  que o site teria aberto o acesso desde 2023-10-31. **Não muda o veredito** (continua sem
  licença de dado publicada), mas o motivo publicado estava desatualizado.
- **OPC-Radiomics** — **17ª** coleção da classe "declara RTSTRUCT/SEG e não aparece na API
  anônima". A Fase 11 tinha contado 16.
- **`EAY131-Tumor-Annotations`** — refina o censo: sítio de lesão, não OAR.
- **HaN-Seg** — o motivo de eliminação **mudou** sob a ontologia congelada: era "definição não
  documentável", agora é "esôfago **cervical**, objeto não comparável". Mesmo veredito, motivo
  correto.
- **Multi-organ Abdominal CT Reference Standard** — **primeiro exemplar confirmado** do padrão
  "segundo grupo re-anota exames públicos", que a Fase 11 procurou e não achou. É abdominal,
  então não serve — mas prova que o padrão existe.

**A classe D é o achado mais desconfortável.** 14 datasets **existem** e não podem ser obtidos
dentro das travas desta execução — entre eles o `RADCURE` (maior conjunto de RTSTRUCT do
TCIA, 3.337) e, o mais irônico, **um estudo de *edge roughness* com múltiplos médicos no
esôfago**: exatamente o desenho que a Fase 11 procurou por duas ondas, atrás de acesso
controlado.

**Nenhum termo foi aceito, nenhuma conta criada, nenhum acesso solicitado.** As 14 entram como
**lacuna declarada**, jamais como "não tem".

## 5. Cenário

# **B — TEST parcialmente defensável, com ressalvas**

**Por que não A.** A exigiria independência ao menos plausível. Com 420 imagens de treino não
atribuídas no TS v2, **nenhum** dataset público a tem. O LyNoS chega mais perto que qualquer
outro em 15 fases, e ainda assim para em E.

**Por que não C.** C seria "nenhum TEST defensável". Seria falso agora: existe **um** conjunto
público, acessível, com esôfago torácico compatível com a `ESOPHAGUS_ONTOLOGY_V1` — verificado
por medição do artefato, não por documento — fora de tudo que o VRmed usou, com GT anterior ao
modelo. Isso é *parcialmente* defensável, com as três ressalvas do §3.3 nomeadas.

**INFERÊNCIA.** A distância entre B e A aqui **não é de esforço de busca**. É a lacuna de
27 % no treino do baseline. Nenhuma busca, por mais exaustiva, fecha essa lacuna: ela se fecha
do lado do modelo, não do lado do dado.

## 6. Limitações

- **FATO.** A execução foi **interrompida pelo fim da sessão** durante a etapa de fonte
  primária. Os **7 arms concluíram**; **6 fichas** foram salvas e recuperadas do journal do
  workflow. As demais fichas e as três rodadas de refutação **não rodaram**.
- **FATO.** Portanto **não houve passe cético** sobre estes resultados — ao contrário das
  Fases 11, 12 e 17. As classificações são de primeira ordem.
- **FATO.** **FLARE22 não foi auditado** em fonte primária.
- **FATO.** Os 14 candidatos D não tiveram conteúdo verificado.
- **RECOMENDAÇÃO.** Antes de qualquer uso do LyNoS: resolver o conflito de licença nas três
  fontes, e submeter o candidato a um passe cético — em particular ao ataque de independência,
  que é o único que pode movê-lo de E.

---

```
FASE 15 CONCLUÍDA (parcial — interrompida na etapa de fonte primária, recuperada do journal)
CENÁRIO: B — TEST parcialmente defensável, com ressalvas
CANDIDATOS: 79 (A=0 · B=1 · C=57 · D=14 · E=7)
ACHADO PRINCIPAL: LyNoS — 15 TCs, esôfago binário PREENCHIDO compatível com a ONTOLOGY_V1 por MEDIÇÃO, canal não-DICOM, GT de 2019 (anterior ao TotalSegmentator), CC BY 4.0 / MIT em conflito
CLASSE DO LyNoS: E — independência indeterminada (as 420 imagens não atribuídas do TS v2)
CONSULTAS REGISTRADAS: 230
TREINO: BLOQUEADO
PRÓXIMO PASSO: resolver o conflito de licença do LyNoS nas três fontes oficiais e submetê-lo ao passe cético de independência que esta execução não chegou a rodar
```
