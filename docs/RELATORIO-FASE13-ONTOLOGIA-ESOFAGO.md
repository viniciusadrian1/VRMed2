# Fase 13 — ESOPHAGUS_ONTOLOGY_V1

Data: 2026-09-06 · Nada treinado · Nenhum conjunto congelado tocado

> **K4: RESOLVIDO.** A definição do alvo `esophagus` está congelada, escrita em duas formas
> que a suíte de testes obriga a concordar, e protegida por 12 testes de regressão — um
> deles um controle positivo que já encontrou um ponto cego real do próprio instrumento.

---

## 1. Objetivo

Fechar o critério **K4** da Parte K da Fase 12 — *"definição do alvo congelada"* —, que era
o único dos quatro critérios de prontidão inteiramente sob controle do projeto.

**FATO.** O motivo é operacional: sem alvo congelado, comparar qualquer Dice entre dois
mundos mede desacordo de definição, não desempenho. A banda humana (0,7555) e o baseline
(0,7880) só podem ser postos lado a lado, mesmo como ordem de grandeza, se estiver escrito o
que cada um tenta contornar.

## 2. Estado encontrado

**FATO.** A ontologia **já estava 90 % correta**. A Fase 9 tinha removido os limites
"cricoide" e "junção gastroesofágica" da definição do VRmed, por medição, e declarado a
extensão herdada. O que faltava era: (a) duas linhas históricas que ainda descreviam marcos
sem marcar que eram protocolo do GT; (b) um documento normativo versionado; (c) qualquer
mecanismo que impedisse a definição de derreter de novo.

**FATO — o precedente que justifica (c).** A Fase 6 escreveu *"limite superior = cricoide"*.
A Fase 7 mediu que o cricoide não é localizável. **A contradição ficou de pé entre as duas
fases até a Fase 9 removê-la.** Uma definição congelada que ninguém verifica volta a derreter.

## 3. Contradições históricas localizadas e tratadas

**Regra seguida: não apagar histórico científico.** Nenhuma linha foi removida; todas foram
qualificadas.

| Documento | Linha | Antes | Depois |
|---|---|---|---|
| `VRMED-ANATOMICAL-ONTOLOGY.md` | §1.2, tabela | *"`Esophagus`, do nível abaixo do cricoide à junção gastroesofágica (atlas RTOG 1106)"* | mesma frase **+** *"Isto é descrição do PROTOCOLO de contornagem do GT — não é capacidade do VRmed, que não localiza nenhum dos dois marcos"* |
| `VRMED-ANATOMICAL-ONTOLOGY.md` | §1.7, traqueia | *"lúmen e parede traqueal, da cricoide à carina"* | separa o que é medido do que é protocolo: **localiza a carina** (30/30, desvio mediano 0,00 mm) e **não localiza o cricoide** |
| `VRMED-ANATOMICAL-ONTOLOGY.md` | cabeçalho §1.2 | — | aponta para a V1 como normativa e declara que, em divergência, **vale a V1** |

**FATO.** As demais ocorrências de "cricoide" nos documentos (Fases 7, 9, 10, 12,
RELATORIO-TIER2-COORTE, RELATORIO-VALIDACAO-RECONSTRUCAO) **já estavam corretas** — todas
aparecem em contexto de negação ou de citação do protocolo alheio. Verificado pela varredura
automática, não por leitura.

## 4. ESOPHAGUS_ONTOLOGY_V1 — o que foi congelado

Especificação normativa: **[`docs/ESOPHAGUS-ONTOLOGY-V1.md`](ESOPHAGUS-ONTOLOGY-V1.md)**
Fonte da verdade legível por máquina: **[`ontologia_esofago.py`](scripts/validation/tier2/ontologia_esofago.py)**

| Item | Congelado como |
|---|---|
| Representação | **máscara binária PREENCHIDA (sólida)** |
| **Parede vs lúmen** | **NÃO SEPARADOS — um único alvo** |
| Inclui | parede · lúmen preenchido · envelope tecidual do RTOG 1106 |
| Exclui | conteúdo **como classe independente** · tecido adiposo periesofágico · estruturas vizinhas (traqueia, aorta, ázigos, corpo vertebral) · qualquer limite não observável |
| **Extensão longitudinal** | **HERDADA DO GT / NÃO AVALIÁVEL ANATOMICAMENTE** |
| Marcos não localizáveis | cricoide · junção gastroesofágica |
| Marco localizável | **carina** — e **não** é usada como âncora do alvo |
| Unidade de distância | **mm físicos**; índice de voxel nunca é medida final |
| Protocolo | **RTOG 1106** |
| Métricas | **8, congeladas** (§6) |

### 4.1 As duas confusões que a V1 registra explicitamente

**FATO.** São os dois erros de leitura mais prováveis, e por isso estão escritos:

1. **Lúmen preenchido (dentro) × conteúdo como classe (fora).** O lúmen **não** é excluído —
   ele é preenchido. O que é excluído é tratar o conteúdo como classe a segmentar.
2. **Excluir gordura periesofágica (fora) × excluir a parede (a parede ESTÁ dentro).**

### 4.2 Parede vs lúmen: por que não é escolha de conveniência

**FATO.** A parede esofágica tem 3–4 mm e ocupa **1,0–1,6 voxel em Z** na grade do LCTSC
(dz 2,5–3,0 mm). **INFERÊNCIA:** exigir que um modelo a separe do lúmen nessa grade é exigir
o impossível. A separação seria outra ontologia, com outra grade — não esta.

### 4.3 Extensão: a decisão vem com a medida

**FATO**, medido na Fase 9 sobre 30 casos do `development`:

1. As pontas do GT **não** estão a deslocamento fixo da carina — IQR **23,5 mm** cranial e
   **13,6 mm** caudal, ambos acima do HD95 de 6,27 mm que se quer medir.
2. As pontas são **cortes, não terminações** — a fatia terminal caudal tem **2,2447×** a área
   mediana do próprio caso, e em **30/30** fica acima de 1,00×. Uma estrutura que acaba
   anatomicamente afina; esta acaba na largura cheia.
3. O corte **não vem do campo de visão** — caudal no limite em 0/30, cranial em 1/30.

## 5. Métricas — congeladas

**FATO.** Oito, sem acréscimo: Dice · IoU · Precision · Recall · HD95 (mm) · ASSD (mm) ·
erro absoluto de volume · erro percentual de volume.

**Regra registrada:** nenhuma métrica entra como **critério de aprovação** sem uma nova
versão da ontologia. Métricas exploratórias podem ser medidas e publicadas, desde que
declaradas exploratórias e fora do critério. O teste 5 falha se a lista mudar.

## 6. Testes de regressão

**FATO.** `tests/test_ontologia_esofago.py` — **12 testes, 12 passando**.

| Faixa | O que defende |
|---|---|
| 1–4 | o alvo congelado: máscara preenchida, quatro exclusões, extensão herdada, marcos separados por capacidade |
| 5–7 | as 8 métricas, a unidade em mm, versão e protocolo declarados |
| 8 | a referência humana declara **teto otimista** e **mundos diferentes** — sem isso o 0,7555 vira nota de aprovação |
| 9 | varredura de **todos os 30 `.md`** de `docs/` por frase proibida e por regressão de ontologia |
| 10 | o `.md` e o `.py` são a **mesma** especificação — divergir é o modo de falha clássico |
| 11 | a linha do GT pode citar o cricoide, **desde que marque que é protocolo do GT** |
| **12** | **CONTROLE POSITIVO** — injeta violações conhecidas e exige que o varredor as ache |

### 6.1 O teste 12 encontrou um ponto cego real

**FATO.** Na primeira execução, o teste 12 falhou: o varredor achou 3 de 4 violações
injetadas. O padrão de parede/lúmen só casava o infinitivo `separar` e passava limpo por
*"separamos parede e lumen em duas classes"*. O regex foi ampliado para conjugação livre.

**Este é o valor do controle positivo.** Sem ele, os testes 9–11 provariam apenas que o
código roda — não que ele enxerga. Um varredor que devolve "zero violações" por estar
quebrado é pior que nenhum varredor, porque produz confiança falsa.

### 6.2 Dois falsos positivos corrigidos no crivo

**FATO.** A primeira versão acusou `ICURVEE-PEDIDO-ACESSO.md:280` e
`RELATORIO-FASE12:411` por *"validado clinicamente"* — mas as duas linhas **proíbem** a
frase. Um documento que bane uma frase precisa escrevê-la. Os marcadores de negação foram
ampliados para cobrir ênfase markdown (`**não**`) e o `❌` das listas de proibição.

### 6.3 O termo `digital twin` — regra de companhia, não de ausência

**FATO.** A primeira versão baniu o termo e acusou 19 linhas em 3 documentos de análise
estratégica. **INFERÊNCIA:** o banimento era errado — aqueles documentos usam o termo
exatamente como se deve, para **contrastar** (*"Patient-specific model vs Patient Digital
Twin"*, *"requisitos mínimos de um patient digital twin, mapeados no VRmed real"*).

**Regra final:** o termo canônico é **patient-specific 3D model**. `digital twin` não é
proibido — é proibido como **descrição técnica atual**, porque o VRmed não modela estado
fisiológico nem simulação. Um documento que use o termo precisa também mencionar
*patient-specific*, senão está usando-o como se fosse o que o projeto é. **Resultado da
varredura: 30 documentos, 0 violações.**

### 6.4 O varredor reprovou o relatório desta própria fase — duas vezes

**FATO.** Depois de escrito, este documento foi varrido e **acusado**, em duas rodadas:

1. **Linha 119** — a frase que descreve o conserto do regex cita o texto do próprio
   fixture (*"separamos parede e lumen em duas classes"*). O varredor leu a citação como
   proposta.
2. **Linha 128** — a frase que explica o falso positivo cita *"validado clinicamente"* e
   diz que as duas linhas originais **proíbem** a frase. O marcador de negação era
   `proibid`, sufixo que não casa `proíbem`.

**As duas correções, e por que são diferentes:**

- **Isenção meta+citação.** Um documento que descreve o detector precisa poder citar o que
  ele detecta. A isenção exige **as duas coisas**: vocabulário de instrumento na linha
  (*varredor, crivo, regex, controle positivo, falso positivo…*) **e** a frase entre aspas.
  Vocabulário sozinho seria porta de fuga — bastaria escrever "varredor" para afirmar
  qualquer coisa. **O teste 12 agora cobre exatamente isso**: uma linha com vocabulário de
  instrumento e a afirmação *solta* continua sendo acusada.
- **Radical em vez de sufixo.** `proibid` → `proib`, cobrindo *proíbem / proibida /
  proibir*.

**INFERÊNCIA.** Que o instrumento tenha reprovado o documento que o descreve é o sinal mais
forte desta fase de que ele não está zerado por conveniência.

## 7. O que esta fase NÃO fez

- **Não treinou nada.** Nenhum epoch, nenhum modelo.
- **Não alterou o `BASELINE_ESOFAGO_V1`.** Nem um número dele foi recalculado.
- **Não leu nem tocou** `Tier2_TEST` ou `Tier2_VALIDATION` do LCTSC.
- **Não apagou histórico.** Nenhuma linha removida; todas qualificadas.
- **Não resolveu K1, K2 nem K3** — e não tentou. São de outra natureza.

## 8. Limitações

**FATO.** A varredura é **lexical**, não semântica: detecta as frases e os padrões
declarados, não uma afirmação equivalente escrita de outro jeito. O teste 12 mede sua
sensibilidade contra violações conhecidas — não contra violações não imaginadas.

**FATO.** A concordância entre o `.md` e o `.py` (teste 10) é verificada por presença de
termos-chave, não por equivalência semântica completa.

**INFERÊNCIA.** A V1 congela a **definição**, não a **implementação**. Nada aqui verifica que
o pipeline de fato produz uma máscara preenchida — isso é medição de outra fase.

**RECOMENDAÇÃO.** Quando houver mudança de grade (outro dataset, outro dz), a §5 de
resolução precisa ser reavaliada: os números de piso são do LCTSC.

---

```
FASE 13 CONCLUÍDA
ONTOLOGIA: A
VERSÃO: ESOPHAGUS_ONTOLOGY_V1
RTOG 1106: adotado como protocolo de referência; a extensão que ele define é herdada do GT, não localizada pelo VRmed
EXTENSÃO LONGITUDINAL: HERDADA / NÃO AVALIÁVEL
PAREDE VS LÚMEN: NÃO SEPARADOS
MÉTRICAS: CONGELADAS (8)
K4: RESOLVIDO
TREINO: BLOQUEADO
PRÓXIMO PASSO: reavaliar K1–K3 contra o estado real do repositório (Fase 14) — K4 sozinho não desbloqueia nada
```
