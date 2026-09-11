# Fase 31 — ampliação auditável do TRAIN

**Data:** 2026-09-10 · **Decisão: (A) TRAIN ampliado e congelado com sucesso**
**Nada treinado, nada inferido. A V1 não foi tocada.**

| | V1 | **V2** |
|---|---|---|
| pool | 16 | **46** |
| TRAIN | 10 | **32** |
| VALIDATION | 6 | **14** |
| TEST | 0 | **0** |
| fontes | 4D-Lung | 4D-Lung + **LCTSC** |
| instituições | VCU | VCU + **MDACC, MSKCC, MAASTRO** |

`sha256` V2 (conteúdo canônico): **`f4bd480e8f8046923a8990096d40832145fb405f1a84ca85e8f3be6e6d20f60b`**
`sha256` V1, inalterado: `9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192`

---

## 1. O primeiro achado: a premissa da fase estava errada

O pedido dizia: *"O candidato natural é continuar o 4D-Lung, caso os 11 casos restantes
ainda estejam disponíveis."*

**Não há 11 restantes.** Os 11 foram ingeridos **na Fase 24** — foi exatamente ela que
completou 5 + 11 = 16.

E revalidei em vez de confiar no registro, como a fase manda: rodei de novo o filtro de
esôfago sobre o CSV de proveniência da Fase 20 e cruzei com o manifesto.

```
4d_lung: 101 linhas (RTSTRUCT com ROI de esôfago) | 16 sujeitos elegíveis
sujeitos já no manifesto V1: 16
SOBRANDO: NENHUM
```

**O 4D-Lung está esgotado no nível de sujeito.** Existem mais *séries* — 101 RTSTRUCT
para 16 sujeitos, porque cada um tem várias fases respiratórias — mas usá-las
acrescentaria séries do **mesmo paciente**, o que infla `n` sem acrescentar sujeito
independente. É precisamente o que a checagem `sujeitos_em_dois_splits` da Fase 25 existe
para impedir.

---

## 2. 31A — inventário das fontes

Feito **antes** de qualquer download, sobre o CSV de proveniência da Fase 20 (908 linhas,
5 coleções) mais os relatórios das Fases 20, 22, 23, 28 e 29.

| fonte | DOI | licença | bruto | já usados | restantes | anatomia | anotação | status |
|---|---|---|---|---|---|---|---|---|
| **4D-Lung** | `10.7937/K9/TCIA.2016.ELN8YGLE` | CC BY 3.0 | 16 c/ esôfago | **16** | **0** | CT torácica adulto | SEMIAUTOMATIC 16/16 | **ALREADY_USED** |
| **LCTSC** | `10.7937/K9/TCIA.2017.3r3fvz08` | CC BY 3.0 | 60 | 0 no pool | **60** | CT torácica adulto, 3 instituições | **MANUAL 59/60** | **ELIGIBLE_SOURCE** |
| **EAY131 / NCI-MATCH** | — | CC BY 4.0 | 17 | 0 | — | catálogo de **lesão** | UNKNOWN 33/33 | **INCOMPATIBLE** |
| **NSCLC-Radiomics** | `10.7937/K9/TCIA.2015.PF0M9REI` | **CC BY-NC 3.0** | 355 | 0 | — | CT torácica adulto | UNKNOWN | **BLOCKED** |
| **Pediatric-CT-SEG** | `10.7937/TCIA.X0H0-1706` | CC BY 4.0 | 359 | 0 | — | **pediátrico** | HUMANA_MANUAL | **INCOMPATIBLE** |

**Motivo de cada exclusão:**

- **EAY131** — já classificado **F** na Fase 20: *"catálogo de lesão (RECIST/PERCIST), não
  OAR"*, e dos 33 que passaram o crivo, **5 são sítio de lesão** (`PARAESOPHAGEAL`,
  `GASTRO ESOPHAGEAL`). Objeto errado. Sem evidência nova, a classificação permanece.
- **NSCLC-Radiomics** — **CC BY-NC 3.0** é bloqueio jurídico duro, e o projeto o proíbe.
- **Pediatric-CT-SEG** — a Fase 29 **refutou por medição**: modelo adulto rende
  DSC 0,47 ± 0,18 no esôfago daquele dataset. Outro objeto.

**Sobrou exatamente uma fonte: o LCTSC.**

---

## 3. 31B — por que o LCTSC, e por que só o `development`

A Fase 23 tinha marcado o LCTSC como *"JÁ USADO, split congelado"* e decidido **não**
adquiri-lo. Essa decisão é revisitada aqui com um motivo que não existia então: a Fase 30
demonstrou que **o gargalo é o TRAIN** (dp 0,0898 entre os 5 folds), e o 4D-Lung acabou.

**O argumento que fecha a questão:** o split congelado do LCTSC (Fase 5) tem uma partição
chamada **`development`, de 30 casos**. Usá-la para treinar é **exatamente para o que ela
foi congelada**. Não viola o congelamento — honra.

**`validation` 15 e `test` 15 do LCTSC ficam intocados**, e um teste verifica isso.

**Custo, declarado:** 30 dos 60 casos do LCTSC deixam de estar disponíveis como coorte de
medição do baseline. Restam 30 (val 15 + test 15). As medições históricas do
TotalSegmentator sobre o LCTSC continuam válidas como medições **daquele** modelo.

---

## 4. 31C — ingestão pelo mesmo funil, sem caminho paralelo

O funil da Fase 23 esperava `caso/ct` + `caso/rtstruct` — e é **exatamente** o layout do
LCTSC em disco. Zero conversão de formato necessária.

**Parametrizei o funil em vez de duplicá-lo**, com defaults inalterados — mesmo padrão de
`mutacao.py --saida` e `aquisicao.py --teto`. Entraram `PROCEDENCIAS` (com o 4D-Lung
idêntico ao que era), `--fonte`, `--somente` e `--saida`.

**E a neutralidade da mudança foi provada, não afirmada:** rodei o funil num caso 4D-Lung
com o diretório de trabalho redirecionado e comparei **19 campos imutáveis** contra o
manifesto V1.

```
campos comparados : 19
divergentes       : NENHUM
image_sha256 : 9769dfc3716e8ad12d12c370  ==  9769dfc3716e8ad12d12c370
mask_sha256  : c83a55284edba42ebc903d70  ==  c83a55284edba42ebc903d70
```

### Funil de 12 etapas, nos 30 casos

| | |
|---|---|
| candidatos | **30** (o `development` do LCTSC) |
| em disco | 30/30 (7,8 GB já baixados na Fase 5 — **nenhum download nesta fase**) |
| **elegíveis** | **30 de 30** |
| rejeitados por licença | 0 |
| rejeitados por ontologia | 0 |
| rejeitados por grade | 0 |
| rejeitados por vínculo | 0 |
| rejeitados por esquema | 0 |

Todos com `LPS`, **0,0000 % de furos 2D**, máscara binária não vazia, vínculo confirmado
por `ReferencedSeriesInstanceUID`, e pareamento por nome de arquivo **recusado**.

---

## 5. 31D — anti-leakage

**Cinco identidades dos 30 novos contra os 16 da V1:**

| chave | interseção |
|---|---|
| `case_id` | **VAZIA** |
| `study_id` | **VAZIA** |
| `series_id` | **VAZIA** |
| `image_sha256` | **VAZIA** |
| `mask_sha256` | **VAZIA** |
| `source_case_id` (sujeito) | **VAZIA** |

**Contra as coleções históricas** (por `SeriesInstanceUID` e `StudyInstanceUID`):

| coleção | resultado |
|---|---|
| `4d_lung` | NÃO DETECTADO |
| `eay131` | NÃO DETECTADO |
| `nsclc_radiomics` | NÃO DETECTADO |
| `pediatric_ct_seg` | NÃO DETECTADO |
| `lctsc` | 30/30 — **é a própria fonte**, esperado |

### Cross-format: o que NÃO foi verificado

**LyNoS: `NOT_AVAILABLE`.** Ele é NIfTI e **não publica** `StudyInstanceUID` nem
`SeriesInstanceUID`. Só restaria comparar hash de conteúdo, e os formatos diferem — um
mesmo exame nos dois canais **não seria detectado**. Isto é **INCONCLUSIVO**, e o registro
JSON grava a palavra `NOT_AVAILABLE`, nunca "sem overlap". Um teste verifica que a string
"sem overlap" não aparece no registro.

**Ressalva registrada:** LCTSC e NSCLC-Radiomics compartilham dados do **MAASTRO**, já
documentado no repositório. A comparação por UID acima dá 0, mas isso é no nível de UID.
O NSCLC-Radiomics **não entra** no pool V2, então a questão não afeta este congelamento.

*"NÃO DETECTADO" é o resultado do instrumento, não uma afirmação de independência.*

---

## 6. 31E — ontologia, e a exceção que fica exposta

Aplicada a `ESOPHAGUS_ONTOLOGY_V1` sem alteração, pela mesma `validar_alvo` que julgou o
LyNoS e o 4D-Lung.

**30/30 aprovados.** Mas há um achado que não vou esconder:

> **`LCTSC-Train-S3-002` tem 2 componentes conexos**, não 1. Todos os outros 45 casos do
> pool têm 1.

**A ontologia congelada aprova.** Ela exige aprovação nos critérios, máscara não vazia,
volume na faixa e `dtype` inteiro — **não exige componente único**; mede e reporta, mas
não bloqueia. Meu primeiro teste era mais estrito que o instrumento, e **o teste é que
estava errado**, não o caso.

**Decisão: mantido, e exposto.** Não excluí à mão porque sobrepor o instrumento congelado
com um critério inventado na hora é pior do que documentar. Há um teste dedicado
(`test_15b`) que **conta** a exceção e falha se o conjunto mudar — se amanhã aparecerem
cinco casos fragmentados, alguém é obrigado a olhar, em vez de o número crescer em
silêncio dentro de um pool aprovado.

---

## 7. 31F e 31G — licença e anotação

**Licença:** `ABERTA_ATRIBUICAO` em **46/46**. Zero bloqueantes. LCTSC é CC BY 3.0 lida na
API do TCIA; 4D-Lung é CC BY 3.0 por série no índice do IDC.

**Anotação, declarada por caso e não presumida:**

| declarado no `ROIGenerationAlgorithm` | n |
|---|---|
| `MANUAL` | **29** |
| `SEMIAUTOMATIC` | 16 |
| **vazio** | **1** (`LCTSC-Test-S1-101`) |

**O que isso significa e o que não significa.** `MANUAL` é o valor **declarado no
arquivo** — não é atestado de qualidade nem de independência. O LCTSC tem revisão por
**uma** pessoa (organizador do desafio, físico médico clínico) com **taxa de edição
UNKNOWN**, e o GT foi **cortado 1 cm** nas duas extremidades antes da pontuação do
desafio (Fase 22). O `annotation_protocol` do LCTSC é o **atlas RTOG 1106**, declarado —
contra `UNKNOWN` no 4D-Lung.

**O pool V2 mistura duas convenções de contorno.** Isso fica declarado: 16 casos
`SEMIAUTOMATIC` sem protocolo declarado, 30 com protocolo RTOG 1106 e anotação
majoritariamente manual.

---

## 8. 31H — o pool final e sua heterogeneidade

```
30 candidatos → 30 elegíveis → 0 rejeitados
pool V2 = 16 (V1, preservados) + 30 (novos) = 46
```

**A ampliação não é só de `n` — a heterogeneidade melhorou de verdade:**

| dimensão | V1 (16) | **V2 (46)** |
|---|---|---|
| instituições | VCU | VCU + MDACC, MSKCC, MAASTRO |
| **spacing z** | **3,0 mm em 100 %** | **3,0 · 2,5 · 2,0 · 1,25 mm** |
| spacing xy | 4 valores (0,977–1,162) | **7 valores (0,977–1,367)** |
| volume | 23,59 – 60,69 mL | **23,59 – 90,57 mL** |
| extensão axial | 174 – 267 mm | 174 – **270** mm |
| protocolo de contorno | UNKNOWN em 16/16 | UNKNOWN 16 · **RTOG 1106 em 30** |

O ganho em **spacing z** é o que mais importa para uma estrutura fina: a V1 era
inteiramente 3,0 mm, e o diagnóstico da Fase 27B já apontava a resolução grosseira como
suspeita nos casos ruins. A V2 traz 17 casos com z < 3,0 mm.

**Nenhum caso foi excluído por dificultar o Dice.** Zero rejeições.

---

## 9. 31I — split V2

Regra completa em [`VRMED-SPLIT-RULE-V2.md`](VRMED-SPLIT-RULE-V2.md), declarada **antes**
de calcular.

```
bucket(case_id) = sha256(case_id) mod 100        # idêntico à V1
validation se bucket < 25, DENTRO DE CADA ESTRATO
estrato = source_dataset ;  test = VAZIO ;  seed = não há
```

| estrato | n | train | validation | banda declarada | |
|---|---|---|---|---|---|
| 4D-Lung | 16 | 10 | 6 | [2, 8] | **DENTRO** |
| LCTSC | 30 | 22 | 8 | [4, 12] | **DENTRO** |
| **TOTAL** | **46** | **32** | **14** | [6, 20] | **DENTRO** |

**O que muda:** a estratificação. Com duas fontes de 16 e 30, um limiar global poderia
concentrar a validation numa delas — e uma validation só de LCTSC mediria outra coisa que
uma só de 4D-Lung. Estratificar **garante as duas nos dois lados**.

**O que deliberadamente não muda, e por quê.** O mecanismo do bucket é o mesmo, então os
16 do 4D-Lung caem onde já estavam. **Isso não é conveniência.** A Fase 25 declarou e
provou por autoteste que *um caso novo não move nenhum caso já atribuído*, e reatribuir
seria vazamento com cara de manutenção: um caso que o modelo da Fase 26B treinou passaria
a ser validation, contaminando qualquer comparação que envolvesse aquele modelo.

`validation` global = 14/46 = **30,4 %** contra alvo de 25 %. Dentro da banda, **não
ajustado** — mesmo princípio da V1, onde 6/16 deram 37,5 %.

**46 sujeitos, nenhum em dois splits.** 46 distintos nas cinco identidades.

---

## 10. 31J e 31K — congelamento e TEST

| | |
|---|---|
| versão | `VRMED-ESOPHAGUS-POOL46-V2` |
| esquema | `VRMED-ESOPHAGUS-DATASET-V1`, 22 campos, **46/46 válidas, 0 erros** |
| ontologia | `ESOPHAGUS_ONTOLOGY_V1`, carimbada no snapshot |
| **`sha256_manifesto`** | **`f4bd480e8f8046923a8990096d40832145fb405f1a84ca85e8f3be6e6d20f60b`** |
| carimbo | por parâmetro, não pelo relógio |

**TEST = 0 e protegido por execução:** `treino` **BLOQUEADO** para `test` **e** para
`validation`; `avaliacao` aberto. Controle negativo: `treino` lê os **32** de `train`.

---

## 11. Incidente

**A Fase 31 escreveu num artefato histórico — de novo.** A primeira execução do funil
gravou em `docs/overnight/phase23/ingestao_real.json`, sobrescrevendo os 5 casos da Fase
23 com os 30 do LCTSC.

**Causa:** acrescentei o parâmetro `--saida` mas **não o liguei** ao caminho de escrita.
**Correção:** o histórico foi restaurado por `git checkout --`, o `--saida` foi ligado de
verdade, e há agora um teste (`test_06`) que verifica que
`phase23/ingestao_real.json` continua com **5 casos, todos `HM10395`** — se alguém
sobrescrever de novo, ele acusa.

**É a terceira ocorrência do mesmo padrão** (Fases 24, 29 e 31). As duas anteriores foram
corrigidas com parâmetro; esta mostra que criar o parâmetro não basta se ele não for
usado.

---

## 12. Testes e integridade

**`tests/test_fase31_ampliacao_train.py` — 22/22.** Suíte completa: **164/164, zero
falhas.** Autotestes de módulo: **250/250**. Varredura: **68 documentos, 0 violações**.

**Integridade antes × depois — tudo inalterado:**

| artefato | |
|---|---|
| manifesto V1 (conteúdo **e** bytes) | INALTERADO |
| split V1 (10/6/0) | INALTERADO |
| snapshot V1 · pool16 · pool candidato F23 | INALTERADO |
| épocas por fold e cada `.pth` (26 e 26B) | INALTERADO |
| contagem de predições | INALTERADO |

**Um teste de fase anterior precisou ser corrigido.** O `test_07` da Fase 30 varria
`.clinica-dados/fase3*` e passou a acusar o diretório **legítimo** da Fase 31. A
heurística era larga demais: o invariante real da Fase 30 é que **ela** não criou árvore
de dados. Corrigido para checar `fase30` especificamente, com o motivo escrito no código.

---

## 13. Decisão: **(A) TRAIN ampliado e congelado com sucesso**

| | |
|---|---|
| pool | 16 → **46** |
| TRAIN | 10 → **32** (3,2×) |
| VALIDATION | 6 → **14** |
| TEST | 0 → **0** |

**O que NÃO se afirma.** Não se afirma que 32 casos resolvem sobreajuste, nem que o
desempenho vai melhorar. A amostra foi **ampliada** e a heterogeneidade **documentada**;
o efeito disso é questão empírica e esta fase não treinou nada.

**Risco residual de leakage:** baixo e nomeado — as cinco identidades estão limpas contra
a V1; o eixo **cross-format** (LyNoS) permanece `NOT_AVAILABLE`; e a partilha
LCTSC↔NSCLC-Radiomics via MAASTRO fica registrada, sem efeito aqui porque o
NSCLC-Radiomics não entra.

---

## 14. Próxima fase

**Fase 32 — replanejamento com o novo `n`**, antes de qualquer treino:

1. **novo σ esperado** — a Fase 30 dimensionou o TEST com σ de um pool de 16 e uma fonte;
   com 46 casos e duas fontes, os três cenários precisam ser refeitos;
2. **recalcular o tamanho do TEST** — a recomendação de n=15 dependia daquele σ;
3. **decidir se repete o experimento de 250 épocas** com TRAIN=32, e se o baseline
   canônico de 1000 épocas volta à mesa (o custo por fold muda com 3,2× mais dados por
   época? não — o nnU-Net fixa 250 iterações/época, então o custo **não** muda);
4. **medir se o dp entre folds cai** — era 0,0898 com TRAIN=10, e é a variável que a Fase
   30 identificou como dominante. Só um treino responde.
