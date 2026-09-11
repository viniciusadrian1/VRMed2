# BASELINE_ESOFAGO_VRMED_V3 — segunda emenda ao pré-registro

Escrito em **2026-09-11** · Fase 32 · Estado: **emenda tardia, com motivo e data declarados**

> A [V1](BASELINE-ESOPHAGUS-VRMED-V1.md) e a [V2](BASELINE-ESOPHAGUS-VRMED-V2.md)
> **permanecem intactas no histórico**, byte a byte, como a V1 exige: *"Alterar qualquer um
> destes exige nova versão do pré-registro, com data e motivo, e a versão antiga permanece
> no histórico."* Este documento não substitui nenhuma das duas.
>
> **Escrito ANTES do primeiro `nnUNetv2_train` sobre o `Dataset502_VRmedEsofagoV2`.** O
> `sha256` deste arquivo está carimbado em
> [`FASE32-PROTOCOLO-TREINO-V2.json`](FASE32-PROTOCOLO-TREINO-V2.json) e o relatório da
> Fase 33 é obrigado a citá-lo. *"Escrevi antes"* não é verificável; um hash é.

---

## 1. Por que existe uma V3, e por que ela chega uma fase atrasada

A cláusula de emenda da V1 protege uma lista curta. **O split está nela:**

> - o manifesto congelado e seu `sha256`;
> - **o split, em qualquer partição**;
> - a `ESOPHAGUS_ONTOLOGY_V1` e as oito métricas;
> - o `seed`; os critérios de sucesso e de regressão.

A Fase 31 congelou o `VRMED-ESOPHAGUS-POOL46-V2` e o split operante do projeto passou de
**10 / 6 / 0** para **32 / 14 / 0**. Isso é exatamente o item protegido. A emenda era
devida **naquela fase**, e não foi escrita.

**FATO.** Uma varredura por *"pré-registro"* e por *"BASELINE-ESOPHAGUS-VRMED-V2"* em
[`RELATORIO-FASE31-AMPLIACAO-TRAIN.md`](RELATORIO-FASE31-AMPLIACAO-TRAIN.md) não retorna
nenhuma ocorrência. A decisão de ampliar o TRAIN foi tomada **sem consultar a cláusula que
a governava**.

**Esta V3 não conserta isso.** Um pré-registro escrito depois do fato não torna o fato
conforme, e a epígrafe da V1 existe precisamente para impedir essa leitura. O que esta V3
faz é o que ainda dá para fazer com honestidade: **registrar o que mudou, quando mudou, e
que o registro chegou uma fase depois da mudança.** O que ela fixa vale daqui para frente.

**É a quarta ocorrência do mesmo padrão.** Nas Fases 24, 29 e 31 uma regra que existia só
em prosa foi violada por um script; a resposta foi, das três vezes, transformar a regra em
código. A regra do §7 da V2 e a cláusula de emenda da V1 eram as últimas regras centrais
que viviam **apenas em prosa**. A resposta é a mesma: [§8](#8-a-regra-vira-teste).

---

## 2. Emenda 1 — o dataset, o split e o identificador

| | antes (V1/V2) | agora (V3) |
|---|---|---|
| pool | `VRMED-ESOPHAGUS-POOL16-V1` | `VRMED-ESOPHAGUS-POOL46-V2` |
| casos | 16 | **46** |
| split | 10 / 6 / 0 | **32 / 14 / 0** |
| regra de split | `VRMED-SPLIT-RULE-V1` | `VRMED-SPLIT-RULE-V2` (estratificada por fonte) |
| identificador | `Dataset501_VRmedEsofago` | **`Dataset502_VRmedEsofagoV2`** |
| árvore | `.clinica-dados/fase26`, `fase26b` | `.clinica-dados/fase32` |

**Motivo.** A Fase 30 mediu que o TRAIN de 10 era o fator limitante e recomendou ampliá-lo
antes de construir qualquer conjunto de avaliação próprio. A Fase 31 executou.

**O identificador mudou de propósito.** Reaproveitar `Dataset501` para 32 casos faria dois
conteúdos distintos compartilharem um nome, e todo diretório de resultado que carrega esse
nome ficaria ambíguo depois do fato. O `Dataset501` das Fases 26 e 26B continua sendo,
para sempre, os 10 casos que ele sempre foi.

**A V1 continua reproduzível.** O manifesto V1 mantém o `sha256` canônico
`9388c736…82632192`, os mesmos 16 casos e o mesmo 10 / 6 / 0. A Fase 32 confere isso por
impressão digital tirada antes e depois, arquivo a arquivo.

**Propriedade preservada, e ela não é conveniência.** A `VRMED-SPLIT-RULE-V2` reusa o
mecanismo de *bucket* da V1, então nenhum caso já atribuído se move: os 10 de TRAIN da V1
seguem em TRAIN, e os 6 de VALIDATION seguem em VALIDATION. Reatribuir um caso congelado
seria vazamento com cara de manutenção.

---

## 3. Emenda 2 — a fonte nova, e o que ela custa para sempre

**Entram 30 casos do LCTSC (TCIA)**, exatamente a partição `development` do split
congelado na Fase 5. As partições `validation` (15) e `test` (15) daquele split
**não foram tocadas**, e há teste que falha se forem.

### 3.1 O que o texto da V2 diz, e o que este documento decide

A V2, §7, lista entre o que continua proibido:

> - usar LCTSC, LyNoS, NSCLC-Radiomics ou SegTHOR;

**O item não tem qualificador.** Duas leituras são defensáveis e o texto não decide entre
elas:

| leitura | o que sustenta |
|---|---|
| **escopo TEST** | o item dois acima diz "preencher o TEST nesta fase"; a V1 fala do LCTSC exclusivamente como candidato a TEST (*"escolher por resultado de LCTSC seria usar TEST para desenho"*); os quatro nomes estão codificados em testes de escopo de TEST (`test_fase28`, `test_fase29`) |
| **escopo geral** | o item, como escrito, não qualifica nada |

**Esta V3 não afirma qual das duas o autor da V2 quis dizer** — não há como saber, e
inventar a intenção seria pior que declarar a ambiguidade. O que ela faz é **substituir o
item por uma regra que não admite duas leituras**, com escopo explícito por papel:

```
FONTES_PERMITIDAS_NO_POOL   = {"4D-Lung (TCIA)", "LCTSC (TCIA)"}
FONTES_PROIBIDAS_COMO_TEST  = {"LCTSC (TCIA)", "LyNoS", "NSCLC-Radiomics", "SegTHOR"}
                              ∪ {toda fonte já usada em train ou validation}
```

Ambas ficam gravadas, legíveis por máquina, em
[`FASE32-PROTOCOLO-TREINO-V2.json`](FASE32-PROTOCOLO-TREINO-V2.json), e são conferidas
contra o manifesto congelado por um teste executável.

### 3.2 O preço, dito por inteiro

Usar o LCTSC no TRAIN **desqualifica o LCTSC como conjunto de avaliação externo, para
sempre e por inteiro** — inclusive as suas partições `validation` e `test`, que nunca
foram tocadas, porque passam a vir da mesma coleção e do mesmo processo de contorno que o
treino.

**Isso não custou nada que o projeto ainda tivesse**, e o motivo é anterior à Fase 31: a
Fase 29 já havia concluído que o LCTSC **não** pode ser tratado como conjunto de avaliação
independente, e a Fase 16 registra a frase como proibida. O preço estava pago antes de a
Fase 31 gastá-lo. **Isso justifica o resultado; não justifica o procedimento** — a Fase 31
não fez essa checagem.

**Reverter foi considerado e é inviável.** O 4D-Lung está esgotado no nível de sujeito
(16 de 16 elegíveis, revalidado na Fase 31 rodando o filtro de novo), e a Fase 28 auditou
33 coleções sem encontrar candidato forte. Voltar ao TRAIN de 10 significaria descartar a
única ampliação disponível para manter conformidade com uma cláusula cuja violação já não
tem consequência material. Fica registrado que a alternativa foi olhada.

---

## 4. Emenda 3 — o *trainer*, e o nome do que sai dele

**`nnUNetTrainer_250epochs`, 5 folds.** Não é o *trainer* canônico.

**Isto não é escolha nova desta fase.** A Fase 26A, §7, examinou e **recusou** mudar o
orçamento de épocas por argumento de custo — *"não há evidência que sustente um número em
vez de outro. Escolher seria decidir por custo, e a instrução proíbe"* — e abriu, no mesmo
parágrafo, o único caminho que considerou honesto:

> uma **fase experimental separada e explicitamente autorizada** — por exemplo
> `nnUNetTrainer_250epochs` nos 5 folds — que produz diagnóstico da Fase 27 e **não** é o
> baseline. O baseline pré-registrado de 1000 épocas continua sendo o canônico, pendente,
> declarado como dívida. Isso não é emenda: é outro experimento, com outro nome.

A Fase 26B percorreu esse caminho com 10 casos. A Fase 33 percorre o mesmo caminho com 32.
**O custo é fato registrado, não é o fundamento** — o fundamento é a autorização acima.

### 4.1 O nome

O artefato da Fase 33 é o **MODELO INTERNO EXPERIMENTAL V2**.

Nunca *"baseline V2"*, *"baseline ampliado"*, *"baseline com 32 casos"* nem *"o baseline"*.
**O baseline canônico de 1000 épocas continua pendente**, e o único run que existe dele é o
fold 0 da Fase 26, pausado em 64 de 1000 épocas e preservado como está.

### 4.2 O orçamento pode ser insuficiente, e isso fica declarado antes

**FATO.** Uma época do nnU-Net são 250 iterações de 2 patches, constantes que **não**
dependem do número de casos. Logo 250 épocas são os mesmos 125 000 patches com 10 ou com
32 casos.

**FATO medido.** O volume de treino por fold passa de ~267 Mvox para ~1 137 Mvox. Os mesmos
125 000 patches cobrem cada voxel **~227 vezes** em vez de **~966**.

**HIPÓTESE, declarada como tal e não resolvida por esta fase.** Um resultado fraco na Fase
33 é **ambíguo** entre *"mais casos não ajudaram"* e *"o orçamento de passos não acompanhou
a diversidade"*. A licença que a Fase 27B deu às 250 épocas foi emitida sob n = 10 e **não
transfere de graça** para n = 32. Nenhum resultado da Fase 33 pode ser lido como se
resolvesse essa ambiguidade.

---

## 5. Emenda 4 — o plano também é hiperparâmetro, e ele mudou

A V2, §5, vincula os hiperparâmetros **por referência**: comando sem sinalizadores ⇒
defaults do framework, mais o que o planner deriva do dado. O que o planner deriva mudou,
porque o dado mudou:

| | 26B (`Dataset501`) | V2 (`Dataset502`) | |
|---|---|---|---|
| *target spacing* (z, y, x) | 3,0 · 0,9766 · 0,9766 | **2,5** · 0,9766 · 0,9766 | mudou |
| *patch size* | 48 × 224 × 192 | **56 × 192 × 192** | mudou |
| voxels por patch | 2 064 384 | 2 064 384 | **idêntico** |
| *batch size* | 2 | 2 | idêntico |
| arquitetura, estágios, kernels, strides | `PlainConvUNet`, 6 estágios | **idênticos** | idêntico |
| parâmetros | 30 703 498 | 30 703 498 | **idêntico** |
| normalização | `CTNormalization` sobre 10 casos | `CTNormalization` sobre **32** casos | mudou |

**Motivo do registro.** "Vinculado por referência" cobre o que o framework deriva — não
cobre a mudança da entrada da derivação. Chamar isso de "nada mudou" seria esconder três
mudanças reais atrás de uma cláusula de estilo.

**O plano é congelado por `sha256` antes do treino** e não é editado à mão. Se ele não
coubesse no hardware, a resposta seria registrar o gargalo, não ajustar o plano — a
pergunta é *"cabe?"*, não *"o que eu fiz caber?"*.

---

## 6. Emenda 5 — o `seed`, dito pela última vez

A V2 já havia nomeado a lacuna. A V3 fecha o assunto com o que foi lido no pacote
instalado (`nnunetv2 2.8.1`):

**FATO.** O `nnUNetTrainer` **não semeia** `torch`, `numpy` nem `random`. O
`nnUNetv2_train` roda com `cudnn.deterministic = False` e `cudnn.benchmark = True`
(`run/run_training.py:118-119`). O **único** passo semeado é a divisão em 5 folds:
`generate_crossval_split(all_keys_sorted, seed=12345, n_splits=5)`, com o `12345` fixo no
código do framework.

**Decisão.** Nenhum *trainer* customizado é criado. `vrmed_seed = 20260906` continua sendo
**identificador do experimento**, e o `dataset.json` do `Dataset502` carrega uma nota que
diz isso literalmente, para que o campo não seja lido como controle de treino.

**O que substitui o `seed`, e é mais forte que ele:** o `splits_final.json` foi gerado
**nesta fase**, pela própria função do framework, e **congelado por `sha256` antes de
qualquer treino**. Um artefato conferível vale mais que uma semente que o framework não
aceita. Isso também cumpre, pela primeira vez, o critério de sucesso 2 da V1 — *"o
`splits_final.json` efetivo é publicado junto com os pesos"* — antes dos pesos existirem.

---

## 7. O que NÃO muda

| Item | Estado |
|---|---|
| `ESOPHAGUS_ONTOLOGY_V1` | **intacta**, carimbada no `dataset.json` |
| as oito métricas congeladas | **intactas**; nenhuma nova entra no critério |
| manifesto V1 e seu `sha256` | **intactos** — `9388c736…82632192`, 16 casos, 10 / 6 / 0 |
| `VRMED-SPLIT-RULE-V1` | **intacta**, e continua valendo para o pool de 16 |
| **TEST = 0** | **intacto**, e continua protegido por `AcessoIndevido` de verdade |
| configuração `3d_fullres` | **intacta** |
| **os cinco folds, não apenas o `0`** | **intacto** |
| `checkpoint_final` primário, `checkpoint_best` secundário | **intacto**, regra fixada pela Fase 26A |
| **sem parada antecipada** | **intacto**; a Fase 26A recusou *early stopping* por cinco motivos |
| **nada é selecionado pela partição `validation`** | **intacto**: nem época, nem checkpoint, nem pós-processamento, nem limiar |
| a lista de frases proibidas | **intacta** |
| descrição do modelo | **intacta**: BASELINE INTERNO / EXPERIMENTAL, nada além |

### 7.1 Critério de sucesso 4 da V1: insatisfazível hoje

A V1 lista cinco critérios procedimentais. O quarto é *"o TEST foi lido **uma única vez**,
em contexto `avaliacao`"*.

**Com TEST = 0 não há o que ler.** O critério não é violado — ele é **insatisfazível**.
Consequência que precisa ficar escrita: **nenhum modelo do projeto pode ser descrito como
aceito pelos cinco critérios**, nem o da Fase 26B nem o da Fase 33. Nenhum critério é
afrouxado por esta emenda; o que muda é que a impossibilidade passa a estar declarada em
vez de silenciosa.

---

## 8. A regra vira teste

O §7 da V2 e a cláusula de emenda da V1 eram as últimas regras centrais que existiam
**apenas em prosa**, e foram exatamente as que caíram. A partir desta emenda:

- as duas listas de fontes do [§3.1](#31-o-que-o-texto-da-v2-diz-e-o-que-este-documento-decide)
  vivem em `FASE32-PROTOCOLO-TREINO-V2.json`, legíveis por máquina;
- `tests/test_fase32_replanejamento.py` falha se o manifesto congelado contiver fonte fora
  da lista permitida, ou se a partição `test` contiver fonte da lista proibida como TEST;
- o `sha256` deste documento está no protocolo, e o teste falha se o documento for editado
  depois de congelado.

Uma regra que só existe em prosa é uma regra que alguém vai violar sem perceber. Já
aconteceu quatro vezes.

---

## 9. O que continua proibido, e não muda com esta emenda

- reportar qualquer número medido na partição `validation` como desempenho externo,
  independência ou generalização — os 14 casos **não** são um conjunto de teste;
- descrever o LCTSC como avaliação independente do projeto — a Fase 29 já concluiu que ele
  não é, e a Fase 16 registra a frase como proibida;
- preencher o TEST sem uma fase própria, explicitamente autorizada;
- usar desempenho para editar dataset, remover caso ou reescolher fold;
- chamar o alvo do 4D-Lung de anotação humana pura — ele é `SEMIAUTOMATIC` em 16/16; e
  chamar o do LCTSC de anotação de múltiplos observadores — a revisão foi de **uma** pessoa,
  com taxa de edição UNKNOWN;
- afirmar diversidade institucional por caso: `institution` é **UNKNOWN em 46 de 46**
  registros, e o que se sabe é da coleção, não do caso;
- descrever o modelo como algo além de **BASELINE INTERNO / EXPERIMENTAL**.

---

## 10. Ordem dos acontecimentos, dita como foi

**FATO.** Este documento foi escrito na Fase 32, **antes** de qualquer época de treino
sobre o `Dataset502_VRmedEsofagoV2` — a árvore `nnUNet_results` daquele dataset está vazia
e há teste que falha se deixar de estar.

**FATO.** A mudança de split que o motiva aconteceu na **Fase 31**, uma fase antes, sem
consulta ao pré-registro. Este documento é, portanto, **prospectivo em relação à Fase 33 e
retroativo em relação à Fase 31**, e as duas coisas estão ditas em vez de misturadas.
