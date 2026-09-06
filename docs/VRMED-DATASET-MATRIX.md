# VRmed — matriz de datasets para o esôfago

Data: 2026-09-05 · Pergunta: **existe dataset público bom o bastante para treinar um modelo
de esôfago, e um dataset independente para validá-lo?**

> Levantamento para uso educacional e experimental. Licenças foram lidas na fonte quando
> possível; o que não foi confirmado está na §4.

## 0. Os dois filtros que eliminam a maioria

**Filtro 1 — o GT não pode ser saída de modelo.** Já custou caro nesta base: o Zenodo
`10.5281/zenodo.7975081` anota heart, trachea, aorta e esophagus sob CC BY 4.0, e o "ground
truth" dele é saída de nnU-Net. Era o candidato mais conveniente e o mais inválido.

**Filtro 2 — treino e validação servem a propósitos opostos.** Um dataset que está no treino
do TotalSegmentator **não pode validar** o `A_BASELINE_V1` — mas **pode** treinar um modelo
especializado. Os dois usos são registrados separadamente.

---

## 1. A matriz

| Dataset | Esôfago | N casos | N anotadores | Instituições | GT humano | Licença | Acesso | Serve para |
|---|---|---|---|---|---|---|---|---|
| **LCTSC** (TCIA) | sim | 60 | 1/caso | 3 (MDACC, MSKCC, MAASTRO) | sim, contorno de RT | **CC BY 3.0** (lida na API) | REST, sem cadastro | **validação** — já em uso |
| **NSCLC-Radiomics** (TCIA) | sim | 422 | 1 ("a radiation oncologist") | MAASTRO | sim, manual — **convenção NÃO documentada** (Fase 10) | **CC BY-NC 3.0** (lida na API) | download sem aprovação | treino, com ressalva; **não serve para medir estilo** |
| **TotalSegmentator dataset** (Zenodo 6802613) | sim | 1228 | equipe do Basel | 1 (Basel) | **model-in-the-loop** | **CC BY 4.0** | direto, sem cadastro | **treino** — não valida |
| **AMOS22** (Zenodo 7262581) | sim | 500 CT + 100 MRI | 5 juniores + 3 sêniores | 2 (mesmo distrito) | **model-in-the-loop** | **conflitante**: CC BY 4.0 no Zenodo, CC BY-NC-SA no artigo | direto | treino, com ressalva |
| **SegTHOR** | sim | 60 | 1 radioterapeuta | 1 (CHB Rouen) | sim, manual | **DUA proíbe redistribuição** | cadastro + termo assinado + aprovação humana | **bloqueado** |
| **StructSeg2019 T3** | sim | 60 | 1 oncologista + verificação | 1 (Zhejiang) | sim | **nenhuma publicada na fonte** | grand-challenge | **rejeitado** — sem licença |
| **SegRap2023** | sim | 120 treino + 20 val | — | — | sim | **nenhuma publicada** | **gated**: exige *signed End User Agreement* por e-mail | **bloqueado** — não "encerrado" (corrigido na Fase 9) |
| **RAOS** | sim | — | **1 sênior** ("annotated from scratch") | — | sim, R1 puro | ver fonte | GitHub | treino, anotador único |
| **SAROS** | **não** | 900 (882 casos) | model-in-the-loop + revisão humana | 28 coleções TCIA | sim, revisado | **CC BY 4.0** (máscaras; código é MIT) | HTTP direto, sem cadastro | **usado na Fase 8** para o pericárdio. Anotação **esparsa**: ~21 % das fatias, resto = *ignore* (255) |
| **autoPET** | não | — | — | — | **pseudo-rótulo do TotalSegmentator** | — | — | **rejeitado** — filtro 1 |
| **CT-ORG** | não | 140 | — | — | parcial (lungs/bones semiautomáticos) | TCIA | TCIA | — |
| **MSD Task06** | não (tumor) | 96 | — | — | sim | CC BY-SA 4.0 | AWS | — |
| **Pediatric-CT-SEG** | **sim** | — | contornos de especialista | — | sim | ver fonte | TCIA | **Fase 9**: falha em definição documentável e em equivalência anatômica |
| **HaN-Seg** | **cervical apenas** | — | humano | — | sim | verificável | direto | **Fase 9**: cobre só esôfago cervical, não o objeto do baseline |

---

## 2. Os três achados que decidem

**Não foi identificado dataset público de esôfago torácico com múltiplos anotadores
independentes — agora medido em escala de catálogo, não inferido.** A Fase 11 enumerou o
canal DICOM público inteiro pelo índice do IDC v24: dos **19.358 RTSTRUCT**, apenas **908**
têm esôfago como órgão, em **5** coleções (`pediatric_ct_seg` 359, `nsclc_radiomics` 355,
`4d_lung` 101, `lctsc` 60, `eay131` 33) — e o número de séries com **≥2 nomes de esôfago no
mesmo arquivo é ZERO**, assim como o de TCs com ≥2 SEG *manual* de esôfago. Reproduzível em
~10 s: `python -m scripts.validation.tier2.idc_esofago`.

> **O que a Fase 11 descobriu e esta matriz não registrava:** multi-observador humano
> **existe e é abundante** em dado público licenciado — QIBA CT-1C (7 leitores), LIDC-IDRI e
> NLST (4), NSCLC-Radiomics-Interobserver1 e RIDER (5), Gold Atlas (5), CURVAS (3),
> Pancreatic-CT-CBCT-SEG (2). **Todos morrem em F5: nenhum é esôfago.** E existe um conjunto
> com o objeto e o desenho certos — **iCurveE** (NCT05787522, *Nat Commun* 2026: dois
> especialistas independentes, 500 TCs torácicas, esôfago pelo atlas RTOG 1106) — sob
> **acesso restrito**. Classificação da fase: **B — existe, mas é inadequado**.
> Ver `docs/RELATORIO-FASE11-VARIABILIDADE-INTEROBSERVADOR.md`.
>
> **Fase 12 — o fio do iCurveE foi até o fim: classe C, acesso não obtido** (nada foi pedido,
> nada foi negado; o canal continua aberto). O desenho A/B/C **não** serve como dataset
> interobservador — o padrão-ouro é o contorno de um único especialista escolhido órgão a
> órgão por um terceiro, e a fonte é muda sobre a retenção das séries de A e de B. Mas o
> **Source Data aberto** do artigo entregou a banda de concordância do próprio esôfago
> (mediana 0,7555, n=493), que a Fase 11 tinha declarado não mensurável.
> Rascunho de pedido pronto e **não enviado** em `docs/ICURVEE-PEDIDO-ACESSO.md`.

Dos quatro torácicos com esôfago verificados — LCTSC, NSCLC-Radiomics,
StructSeg2019-T3, SegTHOR — todos têm **um** conjunto de contornos por caso. Isso importa
diretamente: a Fase 5 mediu que o **sentido** do erro do esôfago inverte entre instituições
(S3 mais estreita, S1 mais larga, amplitude 0,428). Um dataset de anotador único ensina o
estilo desse anotador, e não há como medir quanto disso é estilo sem contornos repetidos.

**NSCLC-Radiomics não é independente do LCTSC.** Ambos contêm dados do **MAASTRO** — o LCTSC
é *"made available from three different institutions: MD Anderson, Memorial Sloan-Kettering,
and the MAASTRO clinic, with 20 cases from each"*. Usar um para treinar e o outro para validar
compartilharia origem em um terço da coorte.

> **Fase 10 — a procedência foi confirmada por DICOM, e "mesma instituição" não bastou.**
> Dois canais diretos: `ProtocolName = "MAASTRO_PETCT_WholeBodyC"` em `LUNG1-110`, e casamento de
> `RCCTPET_THORAX_8F` com `LCTSC-Train-S1-008` (**por substring**, após remover a decoração
> Siemens `Specials^…(Adult)`). As duas ressalvas obrigatórias: o caso com a string MAASTRO é o
> **menos comparável** do conjunto (PET/CT de corpo inteiro, sem gating), e os dois exames casados
> distam **5 anos** e 3× de corrente de tubo.
>
> **O que a Fase 10 mediu e importa para quem for usar este par:** mesma instituição **não** é
> mesmo protocolo. Concordam apenas os campos de **geometria** (dz 3,0 mm, `PixelSpacing`,
> `ReconstructionDiameter`); divergem **todos** os de aquisição (`ConvolutionKernel`, `KVP`,
> `Manufacturer`). O lado NSCLC é **quatro populações**: 15 casos 4DCT fase 50 %, 3 helicoidais
> sem gating, 6 re-exportações CMS XiO com o cabeçalho de aquisição apagado, 1 PET/CT de corpo
> inteiro. E as eras **não se cruzam**: LCTSC-S1 em 4 meses de 2003–2004, NSCLC ao longo de
> 8 anos de 2005–2014, sem um único dia em comum.

**O maior dataset disponível é o de treino do próprio modelo que queremos superar.** O
TotalSegmentator dataset tem 1228 TCs sob CC BY 4.0, download direto — e é exatamente o
conjunto em que o task `total` foi treinado. Ele serve para treinar um especializado, **nunca
para validar contra o baseline**. E o GT dele é model-in-the-loop: *"After manual segmentation
of the first 5 patients was completed, a preliminary nnU-Net was trained, and its predictions
were manually refined"*.

---

## 3. Resposta objetiva

**Existe dataset suficientemente bom para TREINAR um modelo de esôfago?**
**Tecnicamente sim, metodologicamente frágil.** O TotalSegmentator dataset (1228 casos,
CC BY 4.0) e o NSCLC-Radiomics (422 casos, CC BY-NC 3.0) dão volume. Ambos têm GT de origem
comprometida para o propósito: o primeiro é model-in-the-loop do próprio modelo que se quer
superar, o segundo é de anotador único e compartilha instituição com a coorte de validação.

**Existe dataset INDEPENDENTE para VALIDAR?**
**O LCTSC, e só ele** — e ele já é a coorte de avaliação. Com o `Tier2_TEST` de 15 casos
intocado, há validação independente **disponível**, mas de uma única coleção e um único estilo
de contorno por instituição.

**Recomendação ordenada, se e quando houver decisão de treinar:**

1. **SAROS** para o pericárdio — CC BY 4.0, 900 TCs, 28 coleções, anota `pericardium`. É o que
   fecharia a lacuna da §1.8 da ontologia. **Não é esôfago**, mas é a aquisição de maior
   retorno agora.
2. **TotalSegmentator dataset** para treino de esôfago, com o entendimento explícito de que o
   modelo herdaria as convenções do Basel.
3. **NSCLC-Radiomics** como reforço, com a sobreposição MAASTRO declarada.
4. **SegTHOR**, se e quando o acesso oficial for concedido — o DUA exige termo assinado e
   aprovação humana, o que não é automatizável nem contornável.

---

## 4. Não verificado

- A licença do **RAOS** não foi lida na fonte oficial.
- O conflito de licença do **AMOS22** (CC BY 4.0 no Zenodo contra CC BY-NC-SA no artigo
  NeurIPS) não foi resolvido — na dúvida, vale a mais restritiva.
- **Nenhum dataset foi baixado** nesta fase (Fase 6). Todos os números de N casos e
  anotadores vêm de páginas e artigos, não de inspeção do dado. **A Fase 11 corrigiu isso
  para o que importa:** 11.439 structure sets abertos e lidos, e o catálogo DICOM público
  inteiro varrido por nome pelo índice do IDC.
- **Ainda não verificado (Fase 11):** o conteúdo das **16 coleções fora da API** do TCIA
  (0 séries na API anônima; F4 medido, conteúdo **não** verificado) e das coleções de acesso
  restrito (NSCLC-Cetuximab/RTOG-0617, NRG-1308, iCurveE). Não se afirma ausência sobre elas.
- Não foi verificado se **NSCLC-Radiomics** ou **RAOS** estão no treino do TotalSegmentator
  além do que o artigo declara (só Basel).
- A definição de esôfago de cada dataset **não foi comparada estrutura a estrutura** com a do
  VRmed — só a do LCTSC foi, e ela coincide. **Fase 10:** a do NSCLC-Radiomics não pode ser
  comparada — ela **não existe publicada**.
- **Sobreposição de pessoas entre LCTSC-S1 e NSCLC-Radiomics: não medida e não mensurável** com as
  tags disponíveis (`PatientBirthDate` vazio nos dois lados, `PatientAge` ausente no lado LCTSC).
  As datas não se cruzam, o que exclui reuso do **mesmo exame** — não exclui a mesma pessoa.
- **Armadilha registrada:** `AccessionNumber = 2819497684894126` aparece em 18/25 casos NSCLC e
  também em `LCTSC-Test-S1-101`. É constante de desidentificação, **não** é canal institucional.
- **Nenhum dos quatro conjuntos torácicos com esôfago tem mais de um contorno por caso** — a Fase
  10 fechou com essa lacuna como próxima ação.
