# VRmed — Fase 6: definição anatômica e plano para modelo especializado

Data: 2026-09-05 · Escopo: **definição, investigação e plano**. Nada foi treinado.

> Uso educacional e experimental. Não é validação clínica.

**Resultado em uma linha: não comece o treinamento. E um dos três problemas que motivavam
esta fase não era problema de segmentação — era de correspondência de rótulo, e tem solução
imediata.**

---

## 1. Objetivo

A Fase 5 fechou dizendo que o gargalo é o bloco A e que o esôfago seria o candidato a modelo
especializado. Esta fase testou se isso se sustenta — **antes** de treinar qualquer coisa.
Ordem: primeiro definição, depois dataset, depois separação, depois modelo.

---

## 2. Baseline

`A_BASELINE_V1` **inalterado**: TotalSegmentator 2.18.0, task `total`, `fast=False`,
`higher_order_resampling_LEGACY=True`, `robust_crop=True`, `roi_subset` de 8 estruturas, zero
pós-processamento. MASTER de reconstrução inalterada. Split 30/15/15 preservado; o conjunto de
teste **não foi tocado** — verificado por varredura em todos os arquivos produzidos.

---

## 3. Ontologia VRmed

Criada em [`VRMED-ANATOMICAL-ONTOLOGY.md`](VRMED-ANATOMICAL-ONTOLOGY.md). Antes dela o VRmed
não tinha ontologia anatômica: o que existia era `classe_de()`, heurística por nome que devolve
classe de **processamento**, nunca dizendo o que entra e o que não entra numa estrutura.

Estabelece que **o nome do rótulo não é a definição**, e separa três vocabulários que vinham
sendo confundidos: estrutura anatômica, rótulo de modelo e contorno de radioterapia.

---

## 4. Esôfago

| | mediana no development (n=30) |
|---|---|
| fração do erro que é **extensão** | 0,2119 |
| fração que é **localização** | 0,1355 |
| **residual de fronteira** | 0,6526 |
| deslocamento de centroide por fatia | 1,2208 mm (P95 5,2490) |

A definição do VRmed e a do GT **coincidem** para o esôfago — Δ comprimento mediano de
exatamente 0,000 mm, frações de campo 0,566 contra 0,557. Não há divergência de definição a
descontar. É o único dos três nessa situação.

**A ressalva que derruba metade da leitura.** A investigação classificou 0,6526 como
"residual de definição" e, pelo teste de consistência intra-instituição, 0,1751 do erro total
como compatível com convenção de contorno. **Isso não se sustenta**, por duas razões que a
refutação verificou no código:

O **controle positivo** do regime "definição" é uma **erosão uniforme** do GT — que é
exatamente a assinatura de um modelo que segmenta fino demais, isto é, **erro de modelo**. O
balde residual não distingue convenção de erro; ele mapeia os dois para o mesmo lugar.

E o veredito de S1 (9/10 no mesmo sentido, exatamente no limiar de 0,90) só existe com
tolerância de empate **zero**: dois casos de S1 estão a menos de 1 % de 1,0, com quase metade
das fatias apontando para o outro lado.

**Leitura corrigida:** o erro do esôfago é de fronteira, e **não há evidência de que parcela
relevante dele seja definição**. Ele continua sendo o candidato legítimo a erro de modelo — a
conclusão da Fase 5 sobrevive, o suporte numérico dela é que era mais fraco do que parecia.

---

## 5. Medula

**Não otimizada, e a distinção que o pedido pede fica registrada:**

> **Contorno de radioterapia ≠ estrutura anatômica.** O `SpinalCord` do LCTSC é desenhado para
> planejar dose e para onde o atlas manda. A medula não termina no tórax.

O VRmed adota o limite do campo de aquisição. Sob essa definição, a extensão do modelo além do
contorno **não é erro do modelo** — e a formulação correta é essa, não "o modelo é ruim".

**Correção ao que publiquei na Fase 5.** Eu afirmei que `frac_campo_pred` tem amplitude 0,0000
entre instituições contra 0,27 do `frac_campo_gt`, e li isso como prova de invariância do
modelo. **O argumento é inválido:** a variável está **saturada no teto** — 25 de 30 casos
valem exatamente 1,0, o mínimo é 0,9078, e a dispersão real é 0,0922. Amplitude zero entre
medianas de uma variável presa no máximo é aritmética, não concordância.

O que sobrevive: a predição preenche o campo em 25/30 casos e o FP é **17× maior na ponta
cranial** (4,107 mL contra 0,240 mL). Na ponta caudal a concordância é **imposta pelo campo de
visão** — `erro_distal` mediano de 1,25 mm, |erro_distal| ≤ 3 mm em 19/30.

**Portanto a divergência é uma única decisão de fronteira cranial**, não uma propriedade
global. Separar definição de erro ali exigiria referência anatômica independente, que este
dataset não tem.

---

## 6. Coração e pericárdio

**O achado mais consequente da fase.**

`pericardium` (task `trunk_cavities`, 343) roda **sem bloqueio de licença**
(`requires_license` devolve `False`), 39,1 s por caso.

**A classe não é o saco pericárdico.** É um **sólido preenchido**: razão de preenchimento
**1,0000 em 6/6** casos, meia-espessura mediana **10,375 mm** e P95 **29,456 mm**. Um saco
fibroso tem 1–2 mm. Compatível com a **região pericárdica preenchida**; que seja isso é
hipótese, o que está medido é a geometria.

**E ela explica o GT muito melhor que o `heart`:**

| contra o GT `Heart` do LCTSC | Dice | precision | recall |
|---|---|---|---|
| `heart` | 0,7709 | 0,8851 | 0,7010 |
| **`pericardium`** | **0,9056** | 0,8403 | **0,9811** |
| união | 0,8836 | 0,8029 | 0,9818 |

Recomputei de forma independente em `LCTSC-Train-S1-005`: 0,7560 contra **0,9375**. A união
não ajuda — acrescentar `heart` só piora a precision sem ganhar recall (+0,0007).

**O Dice de 0,7552 publicado na coorte comparava dois objetos diferentes.** O objeto que o GT
contorna existe na saída do modelo, sob outro nome, em outra tarefa.

**Duas ressalvas que ficam ao lado do número.** A escolha de `pericardium` foi feita
**comparando contra o GT nos mesmos 6 casos do development** — é seleção legítima, mas 0,9056
é número de **seleção**, não de validação. E `pericardium` continua **caracterizado, não
identificado**: não há referência anatômica de pericárdio aqui. O SAROS anota a classe em 900
TCs sob CC BY 4.0 e não foi usado — o impedimento é esforço, não impossibilidade.

**Correção adicional:** o `precision 0,9825` que publiquei é da variante `A_suporte_gt`, que
recorta a predição no suporte do GT — circular. No campo completo é **0,8740**, com 28/30
casos abaixo de 0,90.

---

## 7. Datasets

Matriz completa em [`VRMED-DATASET-MATRIX.md`](VRMED-DATASET-MATRIX.md). Três achados:

**Não existe dataset público de esôfago torácico com múltiplos anotadores ou consenso.** Os
quatro verificados têm um conjunto de contornos por caso.

**NSCLC-Radiomics não é independente do LCTSC** — ambos contêm dados do MAASTRO.

**O maior dataset disponível é o treino do próprio modelo que se quer superar** — o
TotalSegmentator dataset, 1228 TCs, CC BY 4.0, com GT model-in-the-loop.

SegTHOR segue bloqueado por DUA que proíbe redistribuição. StructSeg2019 não publica licença.
SegRap2023 encerrou o compartilhamento. autoPET usa pseudo-rótulo do TotalSegmentator.

---

## 8. Modelo especializado — candidatos

Hardware medido: **RTX 4060 Ti, 16.380 MiB**, i5-12400F, 31,8 GiB RAM, 215 GB livres.

**`nnunetv2` 2.8.1 já está instalado** como dependência do TotalSegmentator. **MONAI está
ausente.** Escolher nnU-Net custa zero dependência nova.

A rede que produz o esôfago hoje tem **exatamente 31.214.109 parâmetros**, confirmado por dois
caminhos independentes.

Custo medido de um passo (patch 128³, batch 2, AMP fp16): **4.811 MiB alocados / 6.730 MiB
reservados** — cabe com folga. **0,453 s/passo**, o que dá **31,5 h por fold** e **157,5 h
(6,6 dias) para cinco folds** no schedule padrão. São limites inferiores: medem só o passo da
rede, sem dataloader nem augmentação.

**Candidato principal: nenhum, por ora** — ver §15.

---

## 9. Estratégia de treino (plano, não execução)

```
TRAIN       fonte externa (TotalSegmentator dataset e/ou NSCLC-Radiomics)
VALIDATION  LCTSC development + validation (30 + 15)
TEST        Tier2_TEST — 15 casos, INTOCADO, nunca em treino nem em hiperparâmetro
```

O LCTSC de development **não basta como treino**: 24 casos sobrariam reservando 2 de validação
por instituição, e 15 reservando 5. Os dados de treino teriam de vir de fora.

---

## 10. Estratégia de validação

Avaliação no `Tier2_TEST` **uma única vez**, ao final, com a matriz da Fase 5. Controles de
não regressão em `Lung_R` e `Lung_L`. Estratificação por instituição obrigatória — um ganho
que só aparece num serviço é ganho fraco.

---

## 11. Critérios de sucesso

Os da Fase 5, mantidos: Δ Dice ≥ +0,01 · sem regressão de Dice ≥ 0,01 · sem regressão de HD95
≥ 1,0 mm · sem regressão de volume ≥ 2 pp. Mais: melhora em múltiplos casos, melhora fora do
treino, ausência de regressão nos controles, manutenção do comportamento geométrico, e
avaliação no holdout intocado.

---

## 12. Riscos

**Aprender estilo de contorno em vez de anatomia — e este é mensurável, não hipotético.**

Descritores de **estilo** separam as instituições; descritores de **anatomia** não:

| descritor | tipo | ICC1 | p (permutação) |
|---|---|---|---|
| `frac_fatias_mais_estreita` | estilo | **0,5098** | **0,0005** |
| `razao_area_mediana` | estilo | **0,4719** | **0,0005** |
| `area_gt_mediana_mm2` | anatomia | 0,0788 | 0,1580 |
| `volume_gt_mL` | anatomia | 0,0275 | 0,3008 |
| `comprimento_gt_mm` | anatomia | −0,0762 | 0,7417 |

Cerca de **metade da variância dos descritores de estilo é atribuível à instituição, e
praticamente nada da variância dos descritores anatômicos**. Um modelo treinado neste dado
teria mais sinal de convenção de contorno do que de anatomia para aprender.

**Confundimento não resolvido:** S1 tem dz 3,0 mm em 10/10 e S2 tem 2,5 mm em 10/10 — para 20
dos 30 casos, instituição e spacing são a mesma variável. O contraste com `comprimento_gt_mm`
(que não separa) enfraquece a explicação por grade, mas não a elimina.

**Bloqueado:** não há como medir variabilidade intra-observador — o LCTSC dá um contorno por
caso, sem repetições.

**Escala de dados:** 488.710 voxels positivos de esôfago em 30 casos, contra 31.214.109
parâmetros — **0,0157 voxel por parâmetro**.

---

## 13. O que está comprovado

- **`pericardium` é sólido, não casca** (preenchimento 1,0000 em 6/6; meia-espessura 10,4 mm).
- **`pericardium` explica o GT `Heart` melhor que `heart`** (0,9056 contra 0,7709), com recall
  de 0,9811 e amplitude de 0,0294 entre instituições — recomputado por caminho independente.
- **A tarefa `trunk_cavities` roda sem licença acadêmica**, 39,1 s/caso.
- **Estilo separa instituições e anatomia não** (ICC1 0,47–0,51 contra 0,03–0,08).
- **Não existe dataset público de esôfago torácico com múltiplos anotadores.**
- **A definição do esôfago do VRmed coincide com a do LCTSC** (Δ comprimento 0,000 mm).
- **nnU-Net já está instalado**; um fold custa ≥ 31,5 h nesta máquina.

## 14. O que é hipótese

- Que `pericardium` **seja** anatomicamente a região pericárdica — o nome não é a definição, e
  não há GT de pericárdio aqui.
- Que a divergência do esôfago em S1 seja convenção de contorno — o teste que a sustentava foi
  refutado.
- Que o efeito de instituição seja convenção e não aquisição — confundido com spacing.
- Que um modelo especializado reduza o erro de fronteira do esôfago. **É hipótese, não fato.**

---

## 15. Decisão

### Respostas ao critério de saída

**1. A definição do esôfago está clara para treinar?**
**Sim.** É o único dos três em que a definição do VRmed e a do GT coincidem, e está escrita na
ontologia.

**2. Existe dataset suficientemente bom para treinamento?**
**Não com este dataset.** O veredito é calculado, não opinado: estilo domina a variação
(ICC1 0,5098 com p 0,0005), instituição e spacing são inseparáveis em 20/30 casos, e o LCTSC
de development não tem volume. Fontes externas existem, mas o maior é o treino do próprio
modelo a superar.

**3. Existe dataset independente para validação?**
**Sim, um só** — o `Tier2_TEST` de 15 casos, intocado. Uma coleção, um estilo por instituição.

**4. O problema do esôfago parece ser do modelo?**
**Sim, provavelmente** — e agora por eliminação mais limpa: a definição coincide, a extensão
é 0,21, a localização é 0,14. O que não se sustenta é a fração que fora atribuída a definição.

**5. Existe risco de o modelo aprender apenas o estilo de contorno?**
**Sim, e está medido.** Metade da variância dos descritores de estilo é atribuível à
instituição; a dos descritores anatômicos é ~zero.

**6. Qual arquitetura seria a candidata principal?**
**nnU-Net**, se e quando houver dado — já instalado, mesma família do baseline, o que torna a
comparação limpa. Mas a escolha está **suspensa**: não se escolhe arquitetura antes de haver
dado que a sustente.

**7. É seguro começar treinamento?**
# **NÃO — dados insuficientes.**

### O que fazer em vez disso

**A ação de maior retorno agora não é treinar — é trocar o rótulo do coração.** O ganho de
0,7709 → 0,9056 de Dice não custa treino nenhum: custa rodar uma tarefa que já está instalada
e sem bloqueio de licença. É maior que qualquer ganho que a Fase 5 buscou, e vem de corrigir
uma correspondência de rótulo, não de melhorar um modelo.

**Condições para reabrir a decisão de treinar**, todas verificáveis:

1. Confirmar `pericardium` contra uma referência de pericárdio — **SAROS**, CC BY 4.0, 900 TCs.
2. Adquirir dado de esôfago com **anotador ou instituição independente** do LCTSC.
3. Medir variabilidade interobservador para ter **teto de referência** — sem ele não se sabe
   quanto do erro restante é do modelo.
4. Desconfundir instituição de spacing.

Nenhuma delas exige treinar nada. Todas reduzem risco antes de gastar 31,5 h por fold.
