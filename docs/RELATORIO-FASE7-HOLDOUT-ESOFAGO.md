# VRmed — Fase 7: holdout do mapeamento cardíaco e preparação do esôfago

Data: 2026-09-05 · Dois objetivos independentes. Nada foi treinado.

> Uso educacional e experimental. Não é validação clínica.

**Em uma linha: o mapeamento cardíaco foi promovido com 15/15 casos em cada conjunto retido.
O esôfago não pode começar a treinar — e a razão mudou: não é só falta de dado, é que a
definição não é operacional e o conjunto de teste acabou de ser gasto.**

---

## 1. Objetivo

**A** — validar no holdout a hipótese, congelada na Fase 6, de que `pericardium` representa
melhor o objeto que o LCTSC chama `Heart` do que `heart`. O `0,9056` da Fase 6 era número de
**seleção**.

**B** — preparar o primeiro modelo especializado do VRmed (esôfago) sem treinar: definição,
baseline, dataset, protocolo, candidato.

---

## 2. Holdout

Split verificado antes de qualquer coisa: **30 / 15 / 15**, estratificado 10/5/5 por
instituição, 60 casos únicos sem repetição nem perda. Varredura em todos os artefatos de
development e da Fase 6: **zero citações de caso de teste**. Integridade preservada.

O Objetivo B ficou restrito ao development — verificado: os 30 diretórios de máscaras
auxiliares e as 30 linhas do baseline são subconjunto estrito de `development`, interseção
vazia com os reservados.

---

## 3. Heart → Pericardium

Comparação **congelada na Fase 6**, medida uma vez, com diferenças **pareadas por caso**.

| conjunto | | Dice | recall | precision | HD95 | \|erro vol\| |
|---|---|---|---|---|---|---|
| validation | `heart` | 0,7472 | 0,6542 | 0,8787 | 28,24 mm | 23,82 % |
| validation | **`pericardium`** | **0,9093** | **0,9734** | 0,8665 | **14,00 mm** | **13,78 %** |
| test | `heart` | 0,7488 | 0,6628 | 0,8709 | 27,50 mm | 22,34 % |
| test | **`pericardium`** | **0,9089** | **0,9697** | 0,8501 | **10,00 mm** | **12,97 %** |

Diferenças pareadas (candidato − vigente):

| métrica | validation | test |
|---|---|---|
| Dice | **+0,1418** | **+0,1569** |
| IoU | +0,2193 | +0,2258 |
| recall | +0,3083 | +0,3046 |
| precision | −0,0136 | −0,0215 |
| HD95 | **−16,99 mm** | **−17,50 mm** |
| ASSD | −3,37 mm | −3,13 mm |
| erro absoluto (não cancela) | **−164,8 mL** | **−146,6 mL** |

**15 de 15 casos melhoraram em cada conjunto.**

### A leitura que quase enganou

O Δ de `volume_error_pct` sai **+40,2 pp**, o que reprovaria pelo critério declarado de 2 pp.
É **troca de sinal**: `heart` subestima (−23,8 %) e `pericardium` superestima (+13,8 %). Em
módulo o erro **cai** ~10 pp. Conferi os valores por variante antes de declarar — ler só o
delta assinado teria reprovado uma melhora real.

### O custo, registrado

A precision cai 0,0136 e 0,0215. É real. **Não estava entre os portões declarados** (Dice,
HD95, volume) e não foi acrescentada a eles depois de ver o resultado.

---

## 4. Resultado

**PROMOVER `heart` → `pericardium`.** A regra estava no código antes de rodar: promove só se
passar em validation **e** em test. O `holdout_heart.py` tem 6 controles de autoteste, **4
deles de reprovação** — nega promoção quando o ganho fica abaixo do limiar, quando aparece só
na validation, e quando vem com regressão de HD95. Limiares importados de `fase5.py`, não
recopiados.

---

## 5. Decisão ontológica

Registrada em [`VRMED-ANATOMICAL-ONTOLOGY.md`](VRMED-ANATOMICAL-ONTOLOGY.md) §1.8, com a
distinção **seleção × validação** explícita.

**O que isto NÃO estabelece.** Que `pericardium` seja anatomicamente o saco pericárdico. O
holdout mostra que ela representa melhor **o objeto que o LCTSC contorna como `Heart`** — que é
um contorno de radioterapia incluindo saco e gordura, e não a mesma coisa que o saco. A
identidade anatômica continua **não determinada** e depende do SAROS, que anota `pericardium`
sob CC BY 4.0 e não foi usado.

**Esta é mudança de mapeamento, não de modelo.** Nenhum treino de coração foi iniciado.

---

## 6. Esophagus

`BASELINE_ESOFAGO_V1` — TotalSegmentator 2.18.0, saída crua, variante campo completo,
**development n=30**. É a distribuição que qualquer modelo novo terá de superar.

| métrica | P5 | P25 | **mediana** | P75 | P95 | min | máx |
|---|---|---|---|---|---|---|---|
| Dice | 0,6351 | 0,7570 | **0,7880** | 0,8213 | 0,8537 | 0,4849 | 0,8761 |
| HD95 (mm) | 3,36 | 5,00 | **6,27** | 9,04 | 25,80 | 2,62 | 38,62 |
| ASSD (mm) | 1,00 | 1,15 | **1,39** | 1,72 | 4,79 | 0,89 | 7,22 |
| precision | 0,5355 | 0,7378 | **0,8078** | 0,8569 | 0,9235 | 0,3855 | 0,9302 |
| recall | 0,6254 | 0,7251 | **0,8038** | 0,8552 | 0,9217 | 0,5614 | 0,9239 |

O desvio importa mais que o centro: o Dice vai de **0,4849 a 0,8761**, e o HD95 de 2,62 a
38,62 mm. Um modelo que melhore a mediana e não mexa na cauda não resolve o problema.

---

## 7. Definição anatômica

### O que foi medido

**A hipótese de "fronteira ambígua por adjacência" não se sustenta como explicação do erro.**
Apenas **3,35 %** da superfície do GT está a 1 passo da traqueia predita e **3,80 %** da aorta.
Restringindo às fatias onde o vizinho existe, sobe para 7,29 % e 5,39 % a 1 passo, e 10,86 % e
8,18 % a ≤ 2 mm. **O erro do esôfago não pode ser terceirizado para a vizinhança.**

Limiares publicados: 1 passo e 2 mm. O 2 mm foi escolhido por ser próximo do ASSD mediano
(1,39 mm). Não há medida a 5 mm — a conclusão é válida **nos limiares medidos**.

**O GT é maciço e inclui o lúmen.** `fill_holes` 2D preencheu **0,0000 mL em 30/30 casos**, 0
fatias com buraco. E o lúmen com gás está **dentro** do contorno: a fração de HU < −200 é
0,0494 no GT inteiro e **sobe para 0,0673** no interior erodido — o oposto do que volume
parcial de borda produziria.

**O que o modelo deixa de fora é mais gorduroso que o que ele acrescenta:** fração de gordura
de **0,1837** no FN contra **0,1087** no FP.

**Não há campos de interrupção:** 0 fatias vazias internas em 30/30. O suporte é contíguo em Z.

### A definição NÃO é operacional — e isto é uma correção

A Fase 6 escreveu que o VRmed adota "extensão superior = cricoide" e "inferior = junção
gastroesofágica". **Nenhum dos dois limites é decidível nesta base.** O próprio repositório
admite: `benchmark_tier2.py` e o relatório de reconstrução dizem *"o pipeline não localiza
cricoide nem artéria pulmonar"*. Não existe uma única medida de onde está o cricoide ou a JGE
em nenhum dos 30 casos.

O que existe é **distância predição↔GT**, não predição↔anatomia: `erro_cranial` mediano
**−3,0 mm** (em 18/30 a predição para antes do GT) e `erro_distal` **+6,0 mm** (em 23/30 a
predição passa do GT). Isso descreve a divergência entre duas máscaras, não localiza um marco.

**Consequência:** a definição do esôfago é operacional para **parede, lúmen, gordura e tecido
vizinho**, e **não é** para as duas extremidades. Um modelo treinado contra este GT aprenderia
onde o contornador parou, não onde está o cricoide.

### A distinção parede/lúmen não é representável

Espessura característica mediana **9,33 mm**. Em Z isso são ~3,5 voxels (dz mediano 2,5 mm);
uma parede de 3–4 mm ocupa **1,0–1,6 voxel em Z**. **Exigir que um modelo separe parede de
lúmen nesta grade é exigir o impossível**, e a ontologia passa a dizer isso.

*(Ressalva de aritmética: os valores "9,33 mm", "8,94 voxels no plano" e "3,46 voxels em Z" são
três medianas independentes por caso. Não se dividem umas nas outras — 9,33/2,5 dá 3,73, não
3,46. A conclusão sobre representabilidade se sustenta; a igualdade encadeada, não.)*

---

## 8. Dataset candidato

Matriz reusada de [`VRMED-DATASET-MATRIX.md`](VRMED-DATASET-MATRIX.md).

**Escolhido: NSCLC-Radiomics.** É o único que junta GT humano manual, volume (422 casos),
licença explícita (CC BY-NC 3.0), acesso sem aprovação humana e formato DICOM+RTSTRUCT que o
pipeline já ingere.

Eliminados: TotalSegmentator dataset, AMOS22 e autoPET pelo filtro de **GT humano**
(model-in-the-loop ou pseudo-rótulo do próprio TS); StructSeg2019 por não publicar licença;
SegTHOR pelo DUA que proíbe redistribuição.

**Duas ressalvas que não podem sair do lado dessa escolha:**

O NSCLC-Radiomics **compartilha a instituição MAASTRO** com a coorte de validação. E o
mapeamento `S1`/`S2`/`S3` → MDACC/MSKCC/MAASTRO **não está estabelecido nesta base** — a matriz
diz que o LCTSC vem das três com 20 casos cada, mas nenhuma fonte associa os códigos aos nomes.
**O terço da coorte de avaliação que compartilha instituição com o treino não pode ser
identificado nem excluído.**

*(Nota de método: os totais 542 → 482 → 422 estão redigitados num dicionário do módulo, não
lidos da matriz. Conferem hoje; uma edição futura da matriz não propaga.)*

---

## 9. Modelo candidato

**nnU-Net 3d_fullres**, e a decisão de treinar continua **SUSPENSA**.

A favor: `nnunetv2` 2.8.1 **já instalado** (zero dependência nova), mesma família da rede de
31.214.109 parâmetros que produz o esôfago hoje — o que torna a comparação limpa —, e
reamostragem de volta à grade nativa tratada pela própria ferramenta.

**A cascata lowres→fullres não é necessária:** 29 dos 30 casos cabem em 128 fatias nativas
(mediana 86,5). Contexto não é o ingrediente que falta.

**O problema real é desequilíbrio de classe.** Mesmo com o esôfago **inteiro** dentro de um
patch 128³, apenas **0,72 %** do patch seria positivo (P5 0,45 % · máx 1,22 %). Por fatia no
plano, 1,00 %.

Custo: **31,46 h por fold**, 157,3 h para cinco folds no schedule padrão; 7,86 h/fold a 250
épocas. Patch 128³ batch 2 AMP: 4.811 MiB de 16.380 MiB disponíveis.

---

## 10. Protocolo de treinamento

Registrado, e com um defeito que a refutação encontrou e que precisa ser corrigido antes de
qualquer treino — ver §13.

| item | proposto |
|---|---|
| TRAIN | NSCLC-Radiomics (fonte externa; **nunca** LCTSC test) |
| VALIDATION | LCTSC development (30) |
| TEST | **problema — ver §13** |
| input | CT em HU, grade nativa |
| target | máscara binária de esôfago, GT humano, `gt_humano=True` obrigatório |
| spacing | reamostragem da própria nnU-Net; dz varia de 1,25 a 3,0 mm na coorte |
| loss | Dice + CE (padrão nnU-Net), justificada pelo desequilíbrio de 0,72 % |
| architecture | 3d_fullres, sem cascata |
| early stopping | por **Dice de validação e HD95 de validação**, nunca por Dice de treino |

---

## 11. Baseline

`BASELINE_ESOFAGO_V1`, §6. Registrado por caso, com distribuição completa e estratificação por
instituição.

---

## 12. Critérios de sucesso

Os congelados desde a Fase 5, inalterados: Δ Dice ≥ +0,01 · sem regressão de Dice ≥ 0,01 · sem
regressão de HD95 ≥ 1,0 mm · sem regressão de volume ≥ 2 pp. Mais: melhora em múltiplos casos,
melhora fora do treino, sem regressão nos controles (`Lung_R`, `Lung_L`), benefício visível na
MASTER resultante, e sem ajuste manual por caso.

**A cadeia A→B** já foi medida no baseline: residual `C − A` de **+0,0000 em 15/15 pares**.
Uma melhoria em A chega **integralmente** à MASTER — e uma piora também. `B` fica congelado nos
dois braços.

---

## 13. Riscos

**O conjunto de teste já foi gasto — e isto é o achado mais importante do Objetivo B.**
O protocolo do esôfago planejava "uma leitura, ao final" sobre o `test`. Mas o `test` foi lido
e medido **nesta mesma fase**, legitimamente, pela hipótese cardíaca. Uma avaliação futura do
esôfago sobre ele **seria a segunda leitura, não a primeira**. O conjunto não está mais virgem.

Isso não invalida o resultado do coração — aquela era a hipótese autorizada. Mas significa que
**o esôfago precisa de um conjunto de teste próprio**, e ele não existe hoje.

**Aprender estilo de contorno em vez de anatomia**, já medido na Fase 6: descritores de estilo
separam as instituições (ICC1 0,5098 e 0,4719, p 0,0005) e os de anatomia não (0,0788 / 0,0275
/ −0,0762). Treinar em NSCLC-Radiomics e validar em LCTSC mede a diferença de convenção entre
as duas fontes junto com o erro do modelo, sem separá-las.

**Desequilíbrio de classe de 0,72 %** por patch.

**Escala de dados:** para a razão voxel/parâmetro chegar a 1 seriam necessários **1.917 a 2.110
casos**; para 0,1, **192 a 211**. Existem 422 treináveis. Mas a razão voxel/parâmetro
**provavelmente não é o critério defensável** — voxel não é amostra independente e parâmetro
não é grau de liberdade efetivo. Fica registrada como ordem de grandeza, não como veredito.

---

## 14. O que está comprovado

- **`pericardium` supera `heart` contra o GT `Heart`, no holdout**, 15/15 em validation e
  15/15 em test, com Δ Dice +0,14 e +0,16 e HD95 −17 mm.
- **O GT do esôfago é maciço e inclui o lúmen** (0,0000 mL preenchidos em 30/30; fração de ar
  sobe no interior erodido).
- **A adjacência com traqueia e aorta não explica o erro** nos limiares medidos.
- **O suporte do GT é contíguo em Z** (0 fatias vazias internas em 30/30).
- **O FN é mais gorduroso que o FP** (0,1837 contra 0,1087).
- **O desequilíbrio de classe é de 0,72 %** por patch 128³.
- **A cascata não é necessária** (29/30 cabem em 128 fatias).
- O pipeline de ingestão **recusa** `gt_humano=False`, máscara fora da grade e máscara vazia —
  verificado por mutação, não só pelo caminho feliz.

## 15. O que continua hipótese

- Que `pericardium` **seja** anatomicamente o saco pericárdico.
- Que um modelo especializado reduza o erro de fronteira do esôfago.
- Que a razão voxel/parâmetro seja o critério certo de suficiência.
- O mapeamento `S1`/`S2`/`S3` → instituições nomeadas.

---

## 16. Decisão final

**`pericardium` venceu no holdout?** **Sim.** 15/15 em cada conjunto, Δ Dice +0,1418 e +0,1569.

**Podemos mudar oficialmente o mapping?** **Sim, e foi mudado.** É mudança de mapeamento
ontológico, não de modelo. Nenhum treino de coração iniciado.

**A definição do esôfago está suficientemente clara?** **Parcialmente — e menos do que a Fase 6
afirmou.** Parede, lúmen, gordura e tecido vizinho estão operacionais e medidos. **As duas
extremidades não estão**: o pipeline não localiza cricoide nem junção gastroesofágica, e o que
foi medido é distância predição↔GT, não predição↔anatomia.

**Existe dataset adequado?** **Não sem ressalva.** NSCLC-Radiomics é o único que passa nos
filtros, e ele compartilha MAASTRO com a coorte de validação, num terço que não pode ser
identificado.

**Existe informação suficiente para iniciar treinamento?** **Não.** Três bloqueios: a definição
das extremidades não é operacional, o conjunto de teste já foi gasto, e a fonte de treino
compartilha instituição com a validação de forma não rastreável.

**Medula — motivo para reabrir?** **Não.** A conclusão da Fase 6 permanece: divergência de
definição na fronteira cranial, e treinar para reproduzir o limite do atlas sem ground truth
anatômico compatível ensinaria convenção, não anatomia.

**Candidato principal?** **nnU-Net 3d_fullres**, com a decisão suspensa.

**Menor próxima experiência capaz de reduzir mais incerteza?**

**Baixar o SAROS e medir `pericardium` contra um GT de pericárdio.** Custo baixo — CC BY 4.0,
download direto, sem cadastro. Ele responde a única pergunta que ficou aberta no Objetivo A, que
é a identidade anatômica da classe que acabamos de promover. E é a única das pendências que não
depende de resolver dataset, definição e holdout de uma vez.

Em segundo lugar, e antes de qualquer treino: **estabelecer um conjunto de teste próprio para o
esôfago**, de fonte independente do treino e da validação. Sem ele, nenhum resultado de modelo
especializado será avaliável.
