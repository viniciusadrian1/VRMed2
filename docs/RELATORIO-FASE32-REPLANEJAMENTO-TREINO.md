# Fase 32 — replanejamento pré-treino para o `VRMED-ESOPHAGUS-POOL46-V2`

**2026-09-11 · planejamento, auditoria e preparação. Nenhum treino, nenhuma inferência,
nenhuma métrica de modelo.**

> **DECISÃO: PROTOCOLO A** — `nnUNetTrainer_250epochs`, 5 folds, `Dataset502_VRmedEsofagoV2`,
> `3d_fullres`, `checkpoint_final` primário e `checkpoint_best` secundário, sem parada
> antecipada e sem qualquer seleção pela partição `validation`. Congelado em
> [`FASE32-PROTOCOLO-TREINO-V2.json`](FASE32-PROTOCOLO-TREINO-V2.json).
>
> **O fundamento não é o custo.** É a autorização nominal que a Fase 26A, §7, deu a esta
> linha experimental separada — *"outro experimento, com outro nome"* — mais a decisão de
> manter os 5 folds. O baseline canônico de 1000 épocas **continua pendente**.
>
> Uma emenda ao pré-registro era **devida desde a Fase 31** e não foi escrita. Ela existe
> agora: [`BASELINE-ESOPHAGUS-VRMED-V3.md`](BASELINE-ESOPHAGUS-VRMED-V3.md). Ela não torna
> a Fase 31 conforme; registra o que mudou e que o registro chegou tarde.

---

## 0. Três coisas que esta fase derrubou, incluindo duas minhas

Antes de qualquer tabela, porque mudam como o resto se lê.

**1. O `dp = 0,0898` entre os folds não mede instabilidade de treino.** A Fase 30 o usou
como sinal de que o TRAIN era o gargalo. Cada fold, porém, foi medido em **dois** casos.
Análise de variância de uma via sobre os 10 Dice *out-of-fold* do 26B:

| | |
|---|---|
| MS entre folds | 0,016124 (df 4) |
| MS dentro dos folds | 0,020822 (df 5) |
| **F(4, 5)** | **0,774** · p = 0,586 |
| componente de variância entre folds | **−0,002349** → estimativa ≤ 0 |
| dp esperado só por amostragem, com 2 casos | **0,102** |

`F < 1`: **não há efeito de fold detectável acima do efeito de caso.** O 0,0898 observado é
*menor* que os 0,102 que a amostragem sozinha já produziria. Consequência direta: **"o dp
entre folds cai com TRAIN = 32?" foi retirado dos objetivos da Fase 33** — ele cairia para
~0,054–0,059 só por a validação interna passar de 2 para 6–7 casos, com modelo idêntico.

**2. "Instituições: VCU → VCU + MDACC, MSKCC, MAASTRO" é inferência de coleção, não fato de
caso — e eu escrevi isso como fato.** No manifesto congelado, `institution` é **UNKNOWN em
46 de 46** registros, nos dois manifestos. A tabela de abertura e a §8 do
[`RELATORIO-FASE31`](RELATORIO-FASE31-AMPLIACAO-TRAIN.md), e o `RUN-STATUS`, afirmam a
diversidade institucional sem essa ressalva. O que se sabe é da coleção; o campo por caso
não declara instituição, e o próprio `acquisition` do LCTSC diz isso literalmente. **Os
documentos da Fase 31 não são editados** — a correção fica aqui e na
[V3, §9](BASELINE-ESOPHAGUS-VRMED-V3.md).

**3. Os "206,8 h" que bloquearam a Fase 26 vêm de duas épocas, uma delas o *warmup*.**
[`RELATORIO-FASE26-BASELINE.md:181-192`](RELATORIO-FASE26-BASELINE.md) exibe duas linhas de
log — 155,08 s e 142,75 s — e delas tira "média medida: 148,92 s por época". Medindo as
**64 épocas** do mesmo log: **140,42 s** (140,19 excluindo a primeira). O canônico custaria
**~195 h**, não 206,8 h. O número errado aparece em quatro pontos daquele relatório e é
citado por 26A e 26B. **Os relatórios históricos não são editados**; a correção fica
registrada aqui, e o bloqueio de recurso continua real — 195 h ainda são 8 dias.

---

## 1. Integridade antes × depois (32A, 32T)

Impressão digital de 19 alvos: os quatro artefatos congelados da V1, os quatro da V2, a
ontologia, os dois pré-registros anteriores e as sete árvores de treino, predição e
avaliação — `sha256` **de cada arquivo**, mais o `sha256` canônico dos manifestos, mais
três sentinelas nos arquivos que já foram sobrescritos por engano em fases anteriores.

| | |
|---|---|
| alvos fotografados | **19**, mais 3 sentinelas |
| arquivos cobertos | **200** (4,48 GB), incluindo os **12** `.pth` inteiros |
| divergências antes × depois | **0** |

Os checkpoints entram inteiros de propósito: um `.pth` alterado é exatamente o dano que uma
contagem de arquivos não veria. O comparador tem controle positivo — adulterar um `sha256`,
alterar um arquivo dentro de uma árvore ou **acrescentar** um arquivo a ela tem de acusar, e
os três casos são autotestados.

---

## 2. O dataset V2 está pronto para treinar? (32B)

**Sim, e sem ressalva de integridade.**

| verificação | resultado |
|---|---|
| contagem | 46 · **32 / 14 / 0** — igual ao esperado |
| `sha256` canônico | `f4bd480e…6e6d20f60b` — igual ao congelado na Fase 31 |
| congelamento contra o snapshot | intacto |
| arquivos em disco | **92 conferidos por `sha256`**, 0 faltando, 0 divergentes |
| geometria manifesto × medida | **0 casos divergentes** em spacing, shape e orientação |
| licenças bloqueantes | **nenhuma** — 46/46 `ABERTA_ATRIBUICAO` |
| duplicatas | 0 em `case_id`, `series_id`, `study_id`, `image_sha256`, `mask_sha256` |
| sujeitos | **46**, nenhum em dois splits |
| ontologia | 46/46 aprovados pelo instrumento congelado |

A geometria não é lida do manifesto e conferida contra ela mesma: ela vem dos registros de
ingestão das Fases 24 e 31 — o que o instrumento mediu no arquivo real — e é cruzada com o
manifesto por `case_id`. Divergência entre as duas fontes é **erro**, não ajuste.

---

## 3. O TRAIN ficou mais diverso, ou só maior? (32C)

Só os **32 de train**. A partição `validation` não entra em nenhuma linha desta tabela.

| | V1 TRAIN = 10 | V2 TRAIN = 32 |
|---|---|---|
| `source_dataset` | 4D-Lung 10 | 4D-Lung 10 · **LCTSC 22** |
| `institution` | UNKNOWN 10 | **UNKNOWN 32** |
| `annotation_protocol` | UNKNOWN 10 | UNKNOWN 10 · **RTOG 1106 22** |
| algoritmo declarado | SEMIAUTOMATIC 10 | SEMIAUTOMATIC 10 · **MANUAL 22** |
| fase respiratória | 00 % 8 · 10 % 1 · 80 % 1 | os mesmos 10 · **NÃO APLICÁVEL 22** |
| **spacing z** | **3,0 mm em 10/10** | **3,0 (20) · 2,5 (10) · 2,0 (1) · 1,25 (1)** |
| spacing xy distintos | 3 | **5** |
| formas distintas | 9 | **23** |
| shape z | 103 – 142 (mediana 116) | **103 – 240** (mediana 144) |
| volume mL | 23,6 – 60,7 (mediana 37,5) | 23,6 – 61,9 (mediana 38,2) |
| extensão axial mm | 198 – 264 (mediana 244,5) | **186 – 270** (mediana 229,5) |
| componentes 3D | 1 em 10/10 | 1 em 31 · **2 em 1** |
| buracos 2D | 0,0 % máx | 0,0 % máx |

**Ficou mais diverso na aquisição, e isso é fato medido.** O spacing z era um valor único
em 100 % da V1 e agora são quatro, com 12 casos abaixo de 3,0 mm; as formas distintas
passaram de 9 para 23; a extensão em z chega a 240 fatias contra 142.

**Não ficou mais diverso no alvo.** Volume e extensão axial ficam praticamente onde
estavam: a mediana de volume sobe 0,7 mL e a extensão *cai* 15 mm. Trinta e dois esôfagos
não são mais variados que dez — são mais numerosos.

**E não ficou mais diverso institucionalmente, pelo que o registro sustenta.** 32/32
`UNKNOWN`. Ver [§0.2](#0-três-coisas-que-esta-fase-derrubou-incluindo-duas-minhas).

O que mudou de verdade na anotação: 22 casos entram com **protocolo de contorno declarado**
(atlas RTOG 1106, nomeado na página do TCIA) contra UNKNOWN nos 10 anteriores, e com
`ROIGenerationAlgorithm` **MANUAL** contra SEMIAUTOMATIC. São dois estilos de contorno
diferentes no mesmo TRAIN — ganho de heterogeneidade e, ao mesmo tempo, um fator novo que a
Fase 33 terá de considerar ao ler qualquer diferença.

---

## 4. A `validation`, descrita à parte (32D)

Nenhum caso foi movido. Nenhum caso foi lido.

| | 14 casos |
|---|---|
| fontes | 4D-Lung **6** · LCTSC **8** |
| spacing z | 3,0 (9) · 2,5 (2) · 2,0 (3) |
| protocolo | UNKNOWN 6 · RTOG 1106 8 |
| algoritmo declarado | SEMIAUTOMATIC 6 · MANUAL 7 · **VAZIO 1** |
| volume mL | 26,0 – 90,6 (mediana 33,3) |
| componentes 3D | 1 em 14/14 |
| sujeitos duplicados | nenhum · séries duplicadas: nenhuma |

O caso com `ROIGenerationAlgorithm` **VAZIO** é o mesmo que a procedência do LCTSC já
declarava: MANUAL em 59 dos 60, e este é o sexagésimo. Não é lacuna nova; é a lacuna
conhecida, aparecendo onde deveria.

**Os 6 casos da `validation` da V1 continuam, exatamente, na `validation` da V2**, e nenhum
deles está no TRAIN — propriedade da regra de split, verificada, e o instrumento de
comparação da Fase 33 depende dela.

---

## 5. O dataset nnU-Net (32E)

`Dataset502_VRmedEsofagoV2`, em `.clinica-dados/fase32/`.

**Por que um identificador novo.** Reaproveitar `Dataset501` para 32 casos faria dois
conteúdos distintos compartilharem um nome, e todo diretório de resultado que carrega esse
nome ficaria ambíguo depois do fato. O `Dataset501` das Fases 26 e 26B continua sendo, para
sempre, os 10 casos que sempre foi.

| | |
|---|---|
| `imagesTr` / `labelsTr` | **32 / 32**, exatamente a partição `train`, pareados |
| casos de `validation` em `imagesTr` | **0** |
| `imagesTs` | **não existe** — TEST = 0 |
| holdout | 14 casos **fora** da árvore do nnU-Net |
| conversão de máscara | 46 máscaras, conjunto de foreground **idêntico** voxel a voxel |
| originais | 92 arquivos reconferidos por `sha256`, todos intactos |

**Um código, dois perfis, e a neutralidade provada e não afirmada.** O montador da Fase 26
foi parametrizado em vez de duplicado. O default continua `v1`, e o autoteste 13 do módulo
**reproduz o `dataset.json` que está em disco desde a Fase 26 e falha se um campo divergir**
— a lição do incidente da Fase 31 foi que criar o parâmetro não basta se ele não for ligado.

---

## 6. O plano do planner (32F) e o que mudou (32G)

Executado com `nnUNetv2_extract_fingerprint --verify_dataset_integrity`,
`nnUNetv2_plan_experiment` e `nnUNetv2_preprocess -c 3d_fullres`. **Nada de treino, nada de
inferência.** O ciclo inteiro foi rodado **duas vezes, de forma independente**, e o
`nnUNetPlans.json` e o `dataset_fingerprint.json` saíram **byte a byte idênticos**.

| CAMPO | 26B | V2 | MUDOU? | CONSEQUÊNCIA |
|---|---|---|---|---|
| `dataset_name` | Dataset501 | **Dataset502** | sim | árvore e identificador separados |
| `experiment_planner` | `ExperimentPlanner` | `ExperimentPlanner` | não | mesmo método |
| mediana de spacing original | 3,0 · 0,97659999 | 3,0 · **0,9765625** | sim | só a mediana em xy muda de valor; o z mediano segue 3,0 |
| mediana de shape original | 116 · 512 · 512 | **144** · 512 · 512 | sim | casos mais longos entraram |
| **`target spacing`** | 3,0 · 0,9766 · 0,9766 | **2,5** · 0,9766 · 0,9766 | **sim** | a grade de treino deixa de ser a nativa dos 16 do 4D-Lung |
| **`patch_size`** | 48 · 224 · 192 | **56 · 192 · 192** | **sim** | mesmo orçamento, geometria redistribuída |
| voxels por patch | 2 064 384 | **2 064 384** | **não** | custo por iteração igual |
| `median_image_size` | 116 · 512 · 512 | **160** · 512 · 512 | sim | mais fatias após reamostragem |
| `batch_size` | 2 | 2 | não | — |
| `batch_dice` | True | True | não | — |
| normalização | `CTNormalization` | `CTNormalization` | não (o esquema) | **as estatísticas mudaram**: média de foreground −30,75 → **−16,14** HU, p99,5 141 → **245** |
| `network_class` | `PlainConvUNet` | `PlainConvUNet` | não | — |
| `n_stages` · features | 6 · (32…320) | 6 · (32…320) | não | — |
| `kernel_sizes` · `strides` | (1,3,3) + 5×(3,3,3) | **idênticos** | não | — |
| parâmetros | 30 703 498 | **30 703 498** | **não** | mesmo tamanho de checkpoint |
| MACs por patch | 6,14504 × 10¹¹ | **6,14504 × 10¹¹** | **não** | ver abaixo |

**Os MACs são exatamente iguais, e isso não é coincidência.** Os *strides* cumulativos são
z ÷ 8 e xy ÷ 32 nos dois planos, e as divisões são exatas: cada um dos 6 estágios tem o
**mesmo número de voxels** nas duas geometrias (2 064 384 · 516 096 · 64 512 · 8 064 · 1 008
· 252). O `compute_conv_feature_map_size` do próprio planner também coincide
(5,5414 × 10⁸). **O custo por iteração e o orçamento de ativação são os mesmos.**

**O que isso NÃO significa.** Identidade de custo não é identidade de experimento. Três
coisas mudaram no pré-processamento — grade-alvo, geometria do patch e estatísticas de
normalização — e elas mudaram porque **o nnU-Net as deriva do dado**. Congelar o plano
antigo sobre o dado novo seria deixar de usar o método do nnU-Net, o que é um desvio maior
que o registrado. Fica declarado: **a comparação 26B × Fase 33 é de pipeline inteiro contra
pipeline inteiro.**

---

## 7. 250 ou 1000 épocas (32H)

As nove perguntas, respondidas com o que existe.

**1. O 250 ainda é útil como experimento?** **Sim.** É a única linha com resultado completo
(5 folds, 47,76 h, holdout 0,7630 ± 0,0192) e é a linha que a Fase 26A autorizou por nome.

**2. 1000 é necessário?** **Não para a pergunta da Fase 33**, e não é sequer suficiente para
a dívida: o pré-registro nomeia `Dataset501` com 16 casos, então 1000 épocas sobre o
`Dataset502` também **não** seria o baseline pré-registrado. Rodá-lo agora trocaria uma
pendência por outra.

**3. 250 economiza GPU?** Sim — 49 h contra ~195 h. **E esse fato não é o fundamento**: a
Fase 26A registrou que escolher orçamento por custo é o que a instrução proíbe.

**4. O risco é comparável?** **Não simetricamente, e a assimetria é nova.** Uma época são
250 iterações de 2 patches, constantes que **não** dependem do número de casos. Logo 250
épocas são os mesmos 125 000 patches com 10 ou com 32 casos — mas o volume de treino por
fold passa de **267 Mvox** para **1 137 Mvox**:

| | 26B | V2 |
|---|---|---|
| voxels de treino por fold | 267 M | **1 137 M** |
| voxels sorteados por fold | 258 G | 258 G |
| **exposição média por voxel** | **~966 ×** | **~227 ×** |

**HIPÓTESE, declarada antes e não resolvida por esta fase:** um resultado fraco na Fase 33
será **ambíguo** entre *"mais casos não ajudaram"* e *"o orçamento de passos não acompanhou
a diversidade"*. A licença que a Fase 27B deu às 250 épocas foi emitida sob n = 10 e não
transfere de graça.

**5. O scheduler é apropriado?** Sim, e é o ponto que fecha a questão. `PolyLRScheduler
(optimizer, initial_lr, max_steps = num_epochs)`: com `num_epochs = 250` o *learning rate*
percorre o cronograma **inteiro** até ~0. **250 épocas não são um prefixo de 1000** — são
outro cronograma, completo. Duas consequências: o run do 26B é um treino terminado, não
truncado; e as 49 h **não são adiantamento** das ~195 h — cobrar o canônico depois custa o
valor cheio a mais.

**Corolário: um argumento antigo sai de circulação.** "O pico do *pseudo-dice* veio na época
132 de 250, logo já havia achatado" é **circular** — a posição do pico é função do horizonte,
porque o horizonte é o denominador do scheduler. Não use.

**6. O `checkpoint_best` é relevante?** Como **diagnóstico**, sim. No holdout do 26B ele deu
0,7639 ± 0,0224 contra 0,7630 ± 0,0192 do final — indistinguíveis em Dice. Ele é escolhido
pela EMA da validação **interna**, nunca pelo holdout.

**7. O `checkpoint_final` continua primário?** **Sim.** É o default do `nnUNetv2_predict`, é
o que a Fase 26A fixou antes de existir resultado, e trocá-lo agora seria escolher
checkpoint depois de ver métrica.

**8. Voltar ao pré-registro de 1000 épocas?** **Não nesta fase**, pelos motivos 2 e 4. A
dívida fica declarada, com o custo corrigido: **~195 h**, não 206,8 h.

**9. É necessária uma emenda nova?** **Sim — mas não por causa das épocas.** Ver a seção
seguinte.

---

## 8. A emenda, e por que ela era devida uma fase atrás (32P)

A cláusula de emenda da V1 protege uma lista curta, e **"o split, em qualquer partição"
está nela**. A Fase 31 mudou o split operante de 10 / 6 / 0 para 32 / 14 / 0. A emenda era
devida naquela fase.

**FATO.** Uma varredura por *"pré-registro"* e por *"BASELINE-ESOPHAGUS-VRMED-V2"* no
relatório da Fase 31 não retorna nenhuma ocorrência. A decisão foi tomada sem consultar a
cláusula que a governava. **É a quarta ocorrência do padrão** "regra que só existe em prosa"
— as três anteriores (Fases 24, 29, 31) foram de artefato sobrescrito e viraram código.

[`BASELINE-ESOPHAGUS-VRMED-V3.md`](BASELINE-ESOPHAGUS-VRMED-V3.md) registra cinco emendas:
o dataset e o split; a fonte nova e o que ela custa para sempre; o *trainer* de 250 épocas e
o nome do artefato; o plano como hiperparâmetro que mudou; e o `seed`. **V1 e V2 não foram
tocadas** — conferido por `sha256` antes e depois.

**Sobre o §7 da V2** (*"usar LCTSC, LyNoS, NSCLC-Radiomics ou SegTHOR"* entre os proibidos):
o item não tem qualificador, e duas leituras são defensáveis — escopo TEST, sustentada pelo
contexto da V1 e pelos testes que codificam os quatro nomes **com escopo de TEST**; ou
escopo geral, sustentada pela letra. **A V3 não afirma qual foi a intenção** e substitui o
item por duas listas legíveis por máquina, com escopo explícito por papel.

**O preço, dito por inteiro:** usar o LCTSC no TRAIN o desqualifica como avaliação externa
para sempre, inclusive as partições dele que ninguém tocou. Isso não custou nada que o
projeto ainda tivesse — a Fase 29 já o havia desqualificado — mas isso **justifica o
resultado, não o procedimento**.

**E a regra virou teste.** `test_28` lê as duas listas do protocolo vigente e falha se o
manifesto congelado contiver fonte fora da permitida, ou se `test` contiver fonte proibida.
O próprio teste já pegou uma omissão: o 4D-Lung faltava na lista de proibidos como TEST,
apesar de a regra o incluir.

---

## 9. Custo (32I) e viabilidade (32J)

**A base é medição, não multiplicação.** As 1 250 épocas do 26B foram lidas dos logs:
137,56 s por época, 136,00 a 138,50 entre folds, dp 2,10 s. O mesmo cálculo sobre as 64
épocas da Fase 26 — **mesma configuração, sessão diferente** — dá 140,42 s. A
reprodutibilidade da própria máquina é de **± 2 %**, e é isso que fixa a precisão.

| | por época | por fold | 5 folds | banda de parede |
|---|---|---|---|---|
| **250 épocas** | **138 ± 3 s** | 9,6 h | 47,9 h | **47 – 52 h** |
| 1000 épocas | 138 ± 3 s | 38,3 h | 191,7 h | **186 – 206 h** |

**Termos que a soma de épocas não cobre, e que só andam para cima:** o `Epoch time` do log é
gravado **antes** do checkpoint e do `plot_progress_png`, e a validação final passa de 2
para 6–7 casos por fold, cada um com mais *tiles* (a forma mediana vai de 116 para 160
fatias). No 26B esse termo foi de 0,43 h nos 5 folds; aqui deve ficar entre 0,5 e 1,5 h.

**Armazenamento.** `nnUNet_raw` 1,08 GB e `nnUNet_preprocessed` 1,24 GB, **já em disco**. O
pré-processamento levou **85 s** para os 32 casos; a *fingerprint*, 12 s; o planner, 8 s.
Os resultados devem ficar em 3,0–3,5 GB (mesmo número de parâmetros ⇒ mesmo tamanho de
checkpoint; predições de validação maiores). Livres: **103,7 GB**.

**Cabe no hardware?** RTX 4060 Ti, 16 379 MiB, 15 221 livres no momento da medição; 34,2 GB
de RAM; 12 CPUs lógicas. O orçamento de mapa de ativação e a contagem de parâmetros são
**idênticos** aos do 26B, que treinou 5 folds nesta mesma placa.

**Mas isso é precedente, não medição, e a diferença fica registrada.** Ninguém mediu o pico
de VRAM do 26B — os logs só trazem "RTX 4060 Ti · 16 379 MiB". Por isso o protocolo torna
obrigatório um **passo zero** na Fase 33: `nnUNetTrainerBenchmark_5epochs` no fold 0 com
`nvidia-smi` em paralelo, ~15 minutos, que grava em árvore própria e **não produz
checkpoint**. Converte as duas premissas mais frágeis — s/época e pico de VRAM no
`Dataset502` — em fato, ao custo de 0,5 % da corrida. **A Fase 32 está proibida de treinar e
não o rodou.**

**O plano não foi ajustado para caber.** A pergunta é *"cabe?"*, não *"o que eu fiz caber?"*.

---

## 10. Os folds (32K)

Gerados pela **própria função do framework** —
`generate_crossval_split(np.sort(ids), seed=12345, n_splits=5)`, a mesma que o
`nnUNetTrainer.do_split` chama — e **congelados em `splits_final.json` antes de qualquer
treino**. Verificado: os folds do 26B são reproduzidos byte a byte pela mesma chamada.

| fold | train | val | fontes na val | spacing z na val |
|---|---|---|---|---|
| 0 | 25 | 7 | 4D-Lung 3 · LCTSC 4 | 3,0 (5) · 2,5 (2) |
| 1 | 25 | 7 | 4D-Lung 2 · LCTSC 5 | 3,0 (4) · 2,5 (3) |
| 2 | 26 | 6 | **LCTSC 6** | 3,0 (3) · 2,5 (3) |
| 3 | 26 | 6 | **LCTSC 6** | 3,0 (3) · 2,5 (2) · 1,25 (1) |
| 4 | 26 | 6 | 4D-Lung 5 · LCTSC 1 | 3,0 (5) · 2,0 (1) |

**Auditoria: nenhum problema.** Nenhum caso nos dois lados, nenhum sujeito nos dois lados,
nenhum caso fora da partição `train`, e os 32 aparecem como validação interna exatamente uma
vez. Os 14 do holdout **não entram em fold nenhum** — há controle positivo que reprova um
fold contendo um deles.

**Duas fontes em todos os folds? Não.** Os folds 2 e 3 têm validação interna só de LCTSC.
O `KFold` do nnU-Net não é estratificado.

**Estratificar foi considerado e recusado.** Escrever um `splits_final.json` nosso faria do
split um artefato de desenho nosso, quando o pré-registro vincula os *defaults* do
framework; e não compraria poder, porque `df = 4` continua `df = 4`. **O que sai não é o
split — é o endpoint que dependia dele**, retirado na [§11](#11-comparabilidade-32o).
A composição por fonte fica declarada como limitação.

---

## 11. Comparabilidade (32O)

**Não se pode dizer "só o n mudou".** Mudam n, composição de fonte, protocolo de anotação,
grade-alvo em z, geometria do patch, estatísticas de normalização, e o tamanho da validação
interna. A comparação é de pipeline contra pipeline. Isso fica escrito no protocolo, antes
do resultado.

**O que se mede, declarado agora:**

| papel | endpoint |
|---|---|
| **primário** | Dice *out-of-fold* **por caso, n = 32**, com quebra por `source_dataset` |
| secundário | taxa de colapso *out-of-fold* (Dice < 0,50) com intervalo de Wilson |
| secundário | as 8 métricas congeladas nos 14 do holdout, em **três recortes**: os 6 comuns à V1, os 8 do LCTSC, e os 14 |
| secundário | os 6 comuns, contra o 26B — descritivo, poder baixo |
| **retirado** | "o dp entre folds cai?" — ver [§0.1](#0-três-coisas-que-esta-fase-derrubou-incluindo-duas-minhas) |

**O que se preserva:** as mesmas 8 métricas congeladas, os 5 folds, a mesma definição de
caso, a mesma distinção `final`/`best`, e a leitura do holdout **uma única vez**, pelo
**ensemble dos 5 folds** — como foi no 26B, conforme o próprio relatório da Fase 27B
registra.

**Os 6 casos comuns, e os seus vieses, ditos antes.** Eles são os únicos casos nunca
treinados nas duas versões, o que faz deles o pareamento mais limpo disponível. Mas: n = 6
dá pouquíssimo poder; e eles são **100 % 4D-Lung** enquanto o TRAIN da V2 é 69 % LCTSC, de
modo que uma piora neles poderia ser deslocamento de domínio e não regressão.

**Um viés que era hipótese e virou número.** No 26B a grade-alvo (3,0 mm em z) era a nativa
desses 6 casos: ida e volta eram identidade e o teto de Dice era 1,0. No plano V2 o alvo é
2,5 mm. Medi o teto imposto **só pela troca de grade**, passando a máscara de referência
pelo caminho real da predição (grade nativa → alvo pelos *kwargs* de `resampling_fn_seg` →
volta por `resampling_fn_probabilities` sobre *one-hot* → `argmax`):

| | |
|---|---|
| teto médio nos 6 | **0,9989** |
| teto em 5 dos 6 | **1,0000** |
| pior caso (`4DLUNG-104`) | **0,9935** |
| teto no 26B | 1,0 (alvo = nativo) |

**Existe, e é desprezível diante do que se quer medir.** Registrado porque medi, não porque
importa muito — e é preferível a deixá-lo como suspeita.

**Os 8 do LCTSC no holdout são a única primeira leitura que o projeto tem.** Fica decidido
**agora**, e não depois de ver número: eles entram na leitura única do holdout, em recorte
próprio, e **não** são um conjunto de teste — a fonte deles já está no TRAIN.

---

## 12. Seed (32L) e checkpoint (32M)

**Seed: opção 1 — documentar o comportamento real. Nenhum *trainer* customizado.**

**FATO**, lido no pacote instalado: o `nnUNetTrainer` **não semeia** `torch`, `numpy` nem
`random`; o `nnUNetv2_train` roda com `cudnn.deterministic = False` e
`cudnn.benchmark = True`. O único passo semeado é a divisão em 5 folds, com `seed = 12345`
fixo no código. Um *trainer* customizado só para semear seria inventar controle que o
protocolo não pede, e mexeria justamente no componente que a Fase 26A mandou não mexer.

**O que substitui o seed, e é mais forte:** o `splits_final.json` foi gerado nesta fase e
**congelado por `sha256` antes do treino**. Um artefato conferível vale mais que uma semente
que o framework não aceita. O `dataset.json` do `Dataset502` carrega uma nota dizendo
literalmente o que `vrmed_seed` **não** é, e há teste que falha se ela sumir.

**Checkpoint: primário `checkpoint_final`, secundário `checkpoint_best`.** Fixado antes,
igual ao 26B, sem mudança durante o treino. O `best` é escolhido pela EMA da validação
**interna** e nunca pelo holdout; o `nnUNetv2_predict` usa o `final` por default.

**`nnUNetv2_find_best_configuration`: não roda.** No 26B ele não deixou artefato nenhum em
disco. Rodá-lo agora escolheria pós-processamento a partir de 32 predições *out-of-fold* e
quebraria a comparação. A ambiguidade que a Fase 27 deixou aberta fica fechada.

---

## 13. TEST futuro (32Q)

**Nada foi construído, selecionado ou baixado.**

A Fase 30 recomendou `n = 15`, com mínimo de 10. **Esse número não é mais final**: ele foi
dimensionado sobre um pool de 16, uma fonte e um σ estimado em 10 casos — e a
[§0.1](#0-três-coisas-que-esta-fase-derrubou-incluindo-duas-minhas) mostra que o `dp` que
alimentou aquele cálculo media caso, não fold.

**Registro:** redimensionar depois dos resultados do novo treinamento. E fica registrado
também o que a [V3, §3.2](BASELINE-ESOPHAGUS-VRMED-V3.md) formaliza: as duas fontes do pool
estão agora permanentemente indisponíveis como avaliação externa deste projeto.

---

## 14. GPU (32S)

`nvidia-smi` no início da fase, sem treino:

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Ti (WDDM) |
| driver | 591.86 · CUDA runtime reportado 13.1 |
| VRAM | 16 380 MiB, **1 356 em uso**, 14 752 livres |
| temperatura / utilização | 28 °C · 10 % |
| torch | 2.6.0+cu124, CUDA 12.4, disponível |

O uso de 1 356 MiB é de aplicações de desktop, não de treino. Nenhum processo de
treinamento foi iniciado nesta fase.

---

## 15. Testes (32R)

| | |
|---|---|
| `tests/test_fase32_replanejamento.py` | **30/30**, 0 pulados, 0 falhas |
| suíte de arquivos, projeto inteiro | **194/194**, 0 pulados, 0 falhas |
| autotestes de módulo | **366 verificações, 0 falhas** em 30 módulos |
| varredura de frases proibidas | **71 documentos, 0 violações** |

Os 16 itens pedidos estão cobertos, e mais quatro que esta fase julgou necessários: o
subconjunto de holdout que sustenta a comparabilidade (21), a regra de fontes que saiu da
prosa (28), o `sha256` do pré-registro vigente (29) e o nome do artefato futuro (30).

**Dois testes meus falharam antes de passar, e os dois estavam certos.** O 28 pegou que o
4D-Lung faltava na lista de fontes proibidas como TEST, apesar de a regra o incluir. O 27
pegou uma linha do protocolo que, isolada, podia ser lida como afirmação sobre o LCTSC.

Nada ficou pulado: `test_07`, que compara a impressão digital antes × depois, rodou com as
duas fotos em disco e acusou **0 divergências**.

---

## 16. O que a Fase 32 deixa em aberto, de propósito

1. **O baseline canônico de 1000 épocas continua pendente**, e agora nem 1000 épocas sobre o
   `Dataset502` o produziriam — o pré-registro nomeia `Dataset501` com 16 casos.
2. **Se 250 épocas bastam para 32 casos é pergunta empírica não respondida**, e a Fase 33 não
   a responde: um resultado fraco será ambíguo entre orçamento e dados.
3. **s/época e pico de VRAM no `Dataset502` são inferência**, não medida, até o passo zero da
   Fase 33.
4. **A comparação entre as fontes sobre onde o esôfago começa é parcial — menos ausente do
   que parecia.** Um cético desta fase apontou que ela não existia; fui conferir e existe.
   **FATO**, [Fase 22 §4.1](RELATORIO-FASE22-LCTSC-DEFINICAO-AUTORIA.md): esôfago acima do
   ápice pulmonar, mediana **+17,5 mm** no LCTSC (54 de 60) e **+21,0 mm** no 4D-Lung
   (5 de 5). As duas coortes concordam em direção e ordem de grandeza. **A lacuna que
   sobra** é mais estreita: a medida da Fase 9 relativa à **carina** existe para o LCTSC e
   não para o 4D-Lung, e a medida de ápice do 4D-Lung cobre 5 dos 16. Num modelo que já
   sub-segmenta em extensão (erro de volume médio −8,81 %), estender a medida existente aos
   outros 11 é barato e **não precisa de GPU** — recomendado antes ou junto da Fase 33.
5. **σ entre execuções nunca foi medido** neste projeto. Sem `manual_seed` e com
   `cudnn.benchmark = True`, duas execuções idênticas não dão o mesmo número, e não se sabe
   por quanto.

---

## 17. Próximo passo

**Fase 33 — TREINO**, exatamente como
[`FASE32-PROTOCOLO-TREINO-V2.json`](FASE32-PROTOCOLO-TREINO-V2.json) fixa, começando pelo
passo zero de 15 minutos. O relatório da Fase 33 é obrigado a citar o `sha256` do
pré-registro vigente, `387f48fa…e5548d16`.

O artefato que sai de lá é o **MODELO INTERNO EXPERIMENTAL V2**. Não é o baseline, não é
avaliação externa, não é generalização, e nenhum número dos 14 casos do holdout pode ser
apresentado como qualquer uma dessas coisas.
