# ESOPHAGUS_ONTOLOGY_V1 — definição congelada do alvo `esophagus`

**Congelada em:** 2026-09-06 · **Protocolo de referência:** RTOG 1106
**Fonte da verdade legível por máquina:** [`ontologia_esofago.py`](scripts/validation/tier2/ontologia_esofago.py)
**Regressão:** [`tests/test_ontologia_esofago.py`](tests/test_ontologia_esofago.py) — 12 testes

> **Regra de mudança.** Qualquer alteração nesta especificação é uma **nova versão (V2)**,
> com data e motivo. Nunca uma edição silenciosa da V1. A suíte de regressão existe para
> tornar a edição silenciosa impossível.

---

## 0. Por que esta versão existe

A Fase 12 mediu o critério **K4** — *"definição do alvo congelada"* — como **NÃO**, e
registrou que era o único dos quatro critérios de prontidão inteiramente sob controle do
projeto: não depende de dado novo, de acesso nem de permissão de terceiros.

O motivo é operacional, não burocrático: **sem alvo congelado, comparar qualquer Dice entre
dois mundos mede desacordo de definição, não desempenho.** A banda humana publicada
(0,7555) e o baseline (0,7880) só podem ser postos lado a lado — mesmo como ordem de
grandeza — se estiver escrito o que cada um está tentando contornar.

## 1. O alvo

| | |
|---|---|
| Nome no VRmed | `esophagus` |
| Rótulo no TotalSegmentator | `esophagus` (task `total`) |
| Rótulo no GT do LCTSC | `Esophagus` |
| **Representação** | **máscara binária PREENCHIDA (sólida)** |
| **Parede vs lúmen** | **NÃO SEPARADOS — um único alvo** |
| Unidade de toda distância | **milímetros físicos**; índice de voxel nunca é medida final |

### 1.1 Inclui

- a **parede** esofágica;
- o **lúmen** esofágico, **preenchido** (não vazado);
- o envelope tecidual definido pelo protocolo **RTOG 1106**.

### 1.2 Exclui

- **conteúdo** (alimentar, líquido, gasoso) **como classe independente**;
- **tecido adiposo** periesofágico;
- **estruturas vizinhas**: traqueia, aorta, veia ázigos, corpo vertebral;
- qualquer **limite anatômico não observável** no exame.

### 1.3 As duas confusões que esta seção existe para evitar

1. **Lúmen preenchido (dentro do alvo) × conteúdo como classe (fora do alvo).** O lúmen
   **não** é excluído — ele é preenchido. O que é excluído é tratar o conteúdo como uma
   classe separada a ser segmentada.
2. **Excluir gordura periesofágica (fora) × excluir a parede (a parede ESTÁ dentro).**

## 2. Parede vs lúmen — **NÃO SEPARADOS**

Registro explícito, exigido pelo item 6 do enunciado da Fase 13.

**Não é escolha de conveniência — é limite de resolução medido.** A parede esofágica tem
3–4 mm e ocupa **1,0–1,6 voxel em Z** na grade do LCTSC (dz 2,5–3,0 mm). Exigir que um
modelo separe parede de lúmen nessa grade é exigir o impossível. A separação seria uma
ontologia diferente, com outra grade e outro protocolo — não esta.

## 3. Extensão longitudinal — **HERDADA DO GT / NÃO AVALIÁVEL ANATOMICAMENTE**

Registro explícito, exigido pelo item 7 do enunciado.

**O VRmed não demonstra capacidade de inferir o cricoide nem a junção gastroesofágica.**
Qualquer texto do projeto que sugira o contrário é regressão, e a suíte de testes falha.

**Decidido por medição na Fase 9**, sobre 30 casos do `development`:

1. As pontas do GT **não** estão a deslocamento fixo da carina — IQR **23,5 mm** cranial e
   **13,6 mm** caudal, ambos acima do HD95 de 6,27 mm que se quer medir.
2. As duas pontas são **cortes, não terminações**: a fatia terminal caudal tem **2,2447×** a
   área mediana do próprio caso, e em **30/30** fica acima de 1,00×. Uma estrutura que acaba
   anatomicamente **afina**; esta acaba na largura cheia.
3. O corte **não vem do campo de visão**: caudal no limite em 0/30, cranial em 1/30.

Ancorar na carina injetaria erro maior que o erro que se quer medir. Recortar ao trecho
comum a 30/30 guardaria só 0,6881 do volume e trocaria uma fronteira arbitrária por outra.

### 3.1 Marcos, separados por capacidade

| Marco | Status | Evidência |
|---|---|---|
| **cricoide** | **não localizável pelo VRmed** | nenhuma medida de onde ele está existe no repositório |
| **junção gastroesofágica** | **não localizável pelo VRmed** | idem |
| **carina** | **localizável** | extremo caudal da `trachea` predita; 30/30 casos; desvio mediano 0,00 mm e máximo 3,0 mm sob três variantes do detector (Fase 10). **Não é usada como âncora do alvo.** |

## 4. Limites observáveis e não observáveis

**Observáveis** — a definição é operacional aqui:
- fronteira lateral parede × gordura, na janela de mediastino;
- fronteira com traqueia e aorta, quando há contraste de densidade.

**Não observáveis** — a definição é herdada aqui:
- extremidade cranial (nível do cricoide);
- extremidade caudal (junção gastroesofágica).

## 5. Limitações de resolução

- Grade do LCTSC: **0,977–1,270 mm** no plano, **dz 2,5–3,0 mm**.
- **Piso de resolução no plano: 1,953 mm** (um voxel de ida e volta).
- Diferenças de largura **abaixo de 1,953 mm não são representáveis** nesta grade — medidas
  ou não, não existiriam no dado. (Medido na Fase 10: a diferença de largura entre dois
  estilos de contorno é 0,0014 mm pontual, com IC95 até 1,153 mm — tudo abaixo do piso.)

## 6. Métricas — **CONGELADAS**

| # | Métrica |
|---|---|
| 1 | Dice |
| 2 | IoU |
| 3 | Precision |
| 4 | Recall |
| 5 | HD95 (mm) |
| 6 | ASSD (mm) |
| 7 | erro absoluto de volume |
| 8 | erro percentual de volume |

**Nenhuma métrica pode ser acrescentada como critério de aprovação sem registrar a mudança
numa nova versão desta ontologia.** Métricas exploratórias podem ser medidas e publicadas,
desde que declaradas exploratórias e fora do critério.

## 7. Relação com o RTOG 1106 e com o LCTSC

O GT do LCTSC declara o esôfago pelo atlas **RTOG 1106**, *"do nível abaixo do cricoide à
junção gastroesofágica"*. **Isso é descrição do protocolo de contornagem do GT, não
capacidade do VRmed.**

O alvo do VRmed **coincide com o do GT em extensão total** — diferença de comprimento
mediana **0,000 mm**, medida — mas **por herança, não por localização de marco**.

## 8. Relação com o baseline

`BASELINE_ESOFAGO_V1`: TotalSegmentator 2.18.0, task `total`, saída crua, campo completo,
**zero pós-processamento**. Dice mediano **0,7880** no LCTSC `development` (n=30).

**Esta ontologia não altera o baseline.** Ela apenas escreve contra o que ele é medido.

## 9. Relação com a referência humana

A banda humana publicada (iCurveE, Fase 12) tem vDSC mediano **0,7555** (n=493) contra uma
referência humana curada, sob o **mesmo atlas RTOG 1106**.

**É teto otimista, não piso** — a referência é curada e travada por consenso, então dois
observadores arbitrários concordariam ≤ isso. E vem de **outra coorte, com outro padrão-ouro
e outra grade**.

**A comparação com o 0,7880 do baseline é de ordem de grandeza e jamais de contabilidade.**
As frases abaixo são proibidas e a suíte de regressão as detecta:

- ❌ *"o modelo está dentro da variabilidade humana"*
- ❌ *"o modelo é melhor que humano"*
- ❌ *"0,7880 supera 0,7555"*
- ❌ *"o modelo atingiu nível humano"*
- ❌ *"validado clinicamente"*

## 10. Termo canônico do projeto

O VRmed produz um **patient-specific 3D model**. O termo *digital twin* **não** descreve o
estado técnico atual — o projeto não modela estado fisiológico nem simulação. O termo pode
aparecer para **contrastar** (documentos de análise estratégica fazem exatamente isso), e o
teste de higiene exige que qualquer documento que o use também mencione *patient-specific*.

---

## Verificação

```bash
.venv-pipeline/Scripts/python.exe tests/test_ontologia_esofago.py
.venv-pipeline/Scripts/python.exe -m scripts.validation.tier2.ontologia_esofago --varrer
```
