# VRMED-ESOPHAGUS-DATASET-V2 — **PROPOSTA, NÃO PROMOVIDA**

Data: **2026-09-06** · Fase 21.13 · Estado: **PROPOSTA**

> **A V1 continua sendo o esquema em vigor.** Este documento não a edita, não a
> substitui e não entra em uso automaticamente. Ele registra quatro lacunas que as
> Fases 20 e 21 **mediram**, e propõe o que uma V2 precisaria ter — para que a
> decisão de promover seja tomada por uma pessoa, com o custo à vista.
>
> `tests/test_baseline_v1.py` falha se a V1 mudar. Isso vale também para esta
> proposta: enquanto ela for proposta, a V1 tem exatamente **22 campos**.

---

## 1. Por que reabrir o esquema agora

A Fase 19 escreveu a V1 antes de existir qualquer dado. As Fases 20 e 21 foram as
primeiras a **passar dado real e fixtures reais** por ela. Quatro coisas apareceram, e
nenhuma é opinião — todas saíram de medição.

## 2. Lacuna 1 — o canal de identidade não é declarado

**MEDIDO (Fase 21.4).** O canal DICOM entrega **4** identidades (`case_id`,
`study_id`, `series_id`, `SOPInstanceUID`); o canal NIfTI entrega **2** (`case_id`
externo e o `sha256` do conteúdo). O cabeçalho NIfTI-1 **não tem campo** para
`StudyInstanceUID` nem `SeriesInstanceUID` — não é limitação da nossa leitura, é
ausência no formato.

**Consequência que a V1 não registra.** Quando `study_id` e `series_id` são `UNKNOWN`,
**duas das quatro regras anti-vazamento deixam de ser verificáveis para aquele caso** —
e o manifesto não diz isso em lugar nenhum. Hoje `validar_vazamento` simplesmente pula
valores `UNKNOWN`, o que é correto (não acusar sem base) mas **silencioso**.

**Proposta.**

| Campo novo | Valores | Para quê |
|---|---|---|
| `identity_channel` | `DICOM` · `NIFTI` · `OTHER` | declara a origem da identidade |
| `identity_keys_verifiable` | lista | quais das 4 regras anti-vazamento valem para este caso |
| `sop_instance_count` | inteiro ou `UNKNOWN` | completude da série; detecta ingestão parcial |

## 3. Lacuna 2 — dado derivado não é bloqueável por máquina

**MEDIDO (Fase 20).** O índice do IDC tem **471.946 séries derivadas** em 24
*analysis results*. A maior é `totalsegmentator_ct_segmentations`: **378.153 séries,
26.194 sujeitos, CC BY 4.0, DICOM com identidade completa** — e é **saída de modelo**.

Ela é o negativo perfeito: passa em licença, passa em identidade, passa em formato, tem
n gigantesco, inclui esôfago — e **não pode ser ground truth**.

**O que a V1 tem.** `annotation_source`, texto livre. A recusa dura existe em
`dataset_esofago.Procedencia.gt_humano` — mas isso é **da ingestão**, não do manifesto.
Depois de ingerido, o manifesto não responde *"este GT é humano?"* sem alguém ler prosa.

**MEDIDO também (Fase 20).** A tag DICOM `(3006,0036) ROIGenerationAlgorithm` responde
isso quando existe — e para as **908** RTSTRUCT de esôfago do canal público ela é
`UNKNOWN` em **908/908**. Ou seja: o campo é necessário e a fonte quase nunca o preenche.

**Proposta.**

| Campo novo | Valores | Para quê |
|---|---|---|
| `annotation_is_human` | `true` · `false` · `UNKNOWN` | booleano explícito, bloqueável |
| `annotation_algorithm_declared` | `MANUAL` · `SEMIAUTOMATIC` · `AUTOMATIC` · `UNKNOWN` | o que a fonte declara, separado do que julgamos |
| `derived_from` | id do dataset-base ou `UNKNOWN` | dado derivado aponta para a origem |

**Regra proposta:** `annotation_is_human != true` **bloqueia** TRAIN e TEST, como
`license_class` bloqueia hoje. `UNKNOWN` bloqueia igual a `false` — porque a Fase 20
mediu que `UNKNOWN` é o caso comum, e tratá-lo como permissivo tornaria a regra inócua.

## 4. Lacuna 3 — licença não é o eixo ético

**MEDIDO (Fase 18).** O LyNoS é CC BY 4.0. A aprovação ética das **mesmas imagens**
(via identidade de hash com o AeroPath) é **REK Sør-Øst A, 2010/3385a**. São eixos
independentes, e a V1 só tem o primeiro.

CC BY 4.0 **não é** consentimento, **não é** aprovação para uso secundário e **não é**
base legal sob GDPR para processamento fora do EEE.

**Proposta.**

| Campo novo | Valores | Para quê |
|---|---|---|
| `ethics_approval` | referência ou `UNKNOWN` | ex.: `REK Sør-Øst A 2010/3385a` |
| `consent_basis` | texto ou `UNKNOWN` | consentimento informado, dispensa, etc. |
| `secondary_use_declared` | `true` · `false` · `UNKNOWN` | a fonte autoriza uso secundário? |

**Ressalva explícita da proposta:** estes campos **registram**, não **certificam**. Um
`UNKNOWN` aqui é informação legítima e não deve bloquear TRAIN por si só — bloquear uso
clínico não é competência deste esquema, e fingir que é seria pior que a lacuna.

## 5. Lacuna 4 — sujeitos versus séries

**MEDIDO (Fase 20).** `4D-Lung` tem **6.690 séries de 20 sujeitos** — 334,5 séries por
sujeito. As 101 RTSTRUCT com esôfago vêm de apenas **16 sujeitos**.

A V1 já protege contra isso: `case_id` é uma das quatro identidades, e séries do mesmo
sujeito compartilham `case_id`. **A regra funciona.** O que falta é o manifesto tornar o
risco *visível* antes de alguém montar um split contando linhas.

**Proposta.** Nenhum campo novo. Um **relatório obrigatório** no `congelar()`:
`sujeitos_distintos` por partição, ao lado de `n_entradas`. Congelar um split de 100
linhas que são 8 sujeitos deve ser possível — e deve estar escrito no snapshot.

## 6. Impacto e compatibilidade

| Item | Efeito |
|---|---|
| **campos** | 22 → **32** (+10) |
| **compatibilidade para trás** | **quebra**: `validar_entrada` recusa campo fora do esquema, então um manifesto V1 falha na V2 e vice-versa |
| **migração** | mecânica para 8 dos 10 campos (`UNKNOWN` explícito); `annotation_is_human` e `identity_channel` exigem **decisão humana por caso** |
| **custo real** | zero casos ingeridos hoje, então a migração é de **0 registros**. Este é o momento mais barato possível para promover — e também o momento com menos evidência de que os campos certos são estes |
| **risco de promover agora** | desenhar campos para dados que ainda não existem foi exatamente o que produziu estas quatro lacunas na V1 |
| **risco de não promover** | um dataset derivado (378 mil séries disponíveis, CC BY 4.0) entra como ground truth sem que o manifesto possa recusá-lo por máquina |

## 7. Recomendação

**RECOMENDAÇÃO: promover apenas a Lacuna 2 (dado derivado), e só quando o primeiro
caso real for ingerido.**

O raciocínio: das quatro, a Lacuna 2 é a única cujo **modo de falha é silencioso e
irreversível** — um GT de modelo ingerido como humano contamina o treino e **nenhuma
sonda posterior o detecta**, exatamente como a circularidade SegTHOR/BTCV que a Fase 16
encontrou no TotalSegmentator e que continua invisível. As outras três produzem
`UNKNOWN` visível, que é um estado honesto.

**Não promover nada agora.** A V1 nunca viu um caso real; alterá-la com base em fixtures
repetiria o erro que a criou.

## 8. O que fica decidido

- a **V1 permanece em vigor**, com 22 campos, sem edição;
- esta proposta é **registro**, não plano de execução;
- a promoção exige: primeiro caso real ingerido, decisão humana explícita, e uma nova
  versão com data e motivo — **nunca edição silenciosa da V1**.
