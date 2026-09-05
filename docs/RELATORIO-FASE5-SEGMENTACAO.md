# VRmed — Fase 5: investigação controlada de melhoria da segmentação

Data: 2026-09-04 · Escopo: **bloco A (segmentação)**, conjunto de *development* apenas.

> Avaliação de erro de segmentação para uso **educacional e experimental**. Não é validação
> clínica nem avaliação de acurácia diagnóstica. O que se pode dizer destes resultados:
> *"observamos redução ou aumento de erro na coorte de avaliação sob estas condições"*.

**Resultado em uma linha: nenhuma intervenção passou. O baseline permanece.** E o motivo
principal é mais interessante que o resultado: o maior componente do erro da medula **não é
erro do modelo**.

---

## 1. Objetivo

A cadeia A→B mostrou que a reconstrução não acrescenta erro mensurável na resolução da grade
(residual `C − A` de +0,0000 em 15/15 pares), enquanto o erro de segmentação vai de 0,64 a
0,98 de Dice. Esta fase investiga **se o bloco A pode ser melhorado por configuração,
preprocessing ou pós-processamento** — sem treinar nada e sem substituir o baseline.

---

## 2. Baseline congelado — `A_BASELINE_V1`

Congelado em `.clinica-dados/tier2/lctsc/fase5/baseline.json` **antes** de qualquer
experimento.

| | |
|---|---|
| modelo | TotalSegmentator **2.18.0**, task `total`, GPU, pesos distribuídos com a versão |
| inferência | `fast=False` (1,5 mm) · `higher_order_resampling_LEGACY=True` · `robust_crop=True` · `roi_subset` de 8 estruturas |
| preprocessing | **nenhum nosso** — a entrada é o `gt/image.nii.gz` do `dcmrtstruct2nii`, sem reamostragem, recorte ou normalização |
| **postprocessing** | **NENHUM** |
| ambiente | Python 3.13.11 · torch 2.6.0+cu124 · CUDA 12.4 · numpy 2.5.2 · scipy 1.18.1 |

**A auditoria mudou o desenho da fase.** `scripts/geometry/mask_processing.py::processar_mascara`
**não é chamada em nenhum ponto do caminho Tier 2** — verificado por varredura no repositório.
A predição avaliada é saída **crua** do TotalSegmentator. Portanto os experimentos da Parte 3
são **aditivos**, não modificações de um passo existente, e não há interação com
pós-processamento pré-existente para desemaranhar.

### Critérios de aceitação, declarados antes

| critério | valor | de onde vem |
|---|---|---|
| melhoria de Dice | ≥ 0,01 | meia-largura dos IC 95 % já publicados vai de 0,005 a 0,031 — abaixo disso não é discriminável |
| regressão de Dice | ≥ 0,01 | simétrico de propósito |
| regressão de HD95 | ≥ 1,0 mm | ~1 voxel no plano |
| regressão de volume | ≥ 2,0 pontos percentuais | |

Alvos: `SpinalCord`, `Esophagus`. Controles de não regressão: `Lung_R`, `Lung_L`.
`Heart` **não é alvo** (§8).

---

## 3. Taxonomia de erros

| código | significado |
|---|---|
| **E1** | extensão indevida — a predição continua além de onde a estrutura foi contornada |
| **E2** | estrutura mais estreita — a predição é sistematicamente mais fina que o GT |
| **E3** | deslocamento de fronteira — casca fina espalhada, sem bloco localizado |
| **E4** | falso positivo localizado |
| **E5** | falso negativo localizado |
| **E6** | divergência de definição do GT — o desacordo é de especificação, não erro |
| **E7** | artefato de aquisição/spacing |
| **E8** | caso anômalo |

Todo experimento declara qual código ataca. A distinção que mais importou nesta fase foi
**E1 contra E6**, e ela decidiu o resultado.

---

## 4. Experimentos — matriz completa

Development, n = 30. `Δdice` é a **mediana das diferenças pareadas**, não a diferença das
medianas. Baseline ao lado de cada linha.

| experimento | variante | estrutura | papel | alterados | Δdice | max\|Δdice\| | Δhd95 mm | ΔFP mL | ΔFN mL | Δ\|vol\| pp | regressão |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A component_cleanup | 0,1 mL | SpinalCord | alvo | **0/30** | 0,0000 | 0,00000 | 0,000 | 0,000 | 0,000 | 0,00 | — |
| A component_cleanup | 0,5 mL | Esophagus | alvo | 3/30 | 0,0000 | 0,00176 | 0,000 | 0,000 | 0,000 | 0,00 | — |
| A component_cleanup | 2 mL | Lung_L | controle | 9/30 | 0,0000 | 0,00126 | 0,000 | 0,000 | 0,000 | 0,00 | — |
| **B terminação torácica** | — | **SpinalCord** | alvo | 30/30 | **−0,1169** | 0,25801 | **+8,588** | **−12,421** | **+17,255** | **33,11** | **dice+hd95+volume** |
| B terminação torácica | — | Esophagus | alvo | 25/30 | −0,0094 | 0,04530 | +1,615 | −0,079 | +0,787 | 0,00 | hd95 |
| B terminação torácica | — | Lung_R / Lung_L | controle | 0/30 | 0,0000 | 0,00000 | 0,000 | 0,000 | 0,000 | 0,00 | — |
| **C dilatação 1 voxel** | — | SpinalCord | alvo | 30/30 | **−0,0109** | 0,05289 | +0,730 | +11,079 | −6,629 | **27,33** | **dice+volume** |
| C dilatação 1 voxel | — | Esophagus | alvo | 30/30 | **−0,0179** | 0,08113 | 0,000 | +7,694 | −3,421 | **25,71** | **dice+volume** |
| C dilatação 1 voxel | — | Lung_R | **controle** | 30/30 | −0,0020 | 0,02101 | +0,531 | +54,889 | −42,767 | **3,98** | **volume** |
| C dilatação 1 voxel | — | Lung_L | **controle** | 30/30 | −0,0022 | 0,04515 | +0,682 | +48,329 | −33,919 | **4,98** | **volume** |
| C fechamento | — | SpinalCord | alvo | 30/30 | +0,0004 | 0,00150 | 0,000 | +0,048 | −0,108 | 0,15 | — |
| C fechamento | — | Esophagus | alvo | 30/30 | +0,0002 | 0,00105 | 0,000 | +0,053 | −0,054 | 0,25 | — |
| C abertura | — | SpinalCord | alvo | 30/30 | −0,0005 | 0,00267 | 0,000 | −0,275 | +0,233 | −0,76 | — |
| C calibre condicionado | — | SpinalCord | alvo | 30/30 | −0,0010 | 0,02333 | 0,000 | +1,333 | −1,021 | **3,06** | **volume** |
| C calibre condicionado | — | Esophagus | alvo | 30/30 | +0,0003 | 0,03431 | −0,148 | +1,254 | −0,873 | **2,28** | **volume** |

**Maior ganho pareado positivo em qualquer alvo: +0,0004** (fechamento na medula) — **25×
abaixo** do limiar declarado de 0,01.

---

## 5. SpinalCord — o achado central da fase

### O que foi medido (n = 30)

| medida | mediana | P5 | P95 |
|---|---|---|---|
| frac_FP_extensão | **0,804** | 0,000 | 0,958 |
| FP_extensão proximal (cranial) | **4,107 mL** | | |
| FP_extensão distal | 0,240 mL | | |
| frac_FN_fino (≤ 1 voxel) | **0,891** | 0,788 | 0,962 |
| **frac_campo_pred** | **1,0000** | 0,932 | 1,000 |
| frac_campo_gt | 0,817 | 0,640 | 1,000 |

O FP é **extensão** (0,804), concentrado na ponta **proximal** — 4,107 mL contra 0,240 mL
distal, razão 17×. O FN é **casca de 1 voxel** (0,891). Isso confirma, por caminho
independente, o que a coorte já mostrava.

### A medida que reenquadra tudo

O diagnóstico acrescentou uma coluna que o pedido não previa e que **inverte a leitura**:
`frac_campo_pred` — quanto do campo de visão em Z cada máscara ocupa. E1 ("a predição passou
do ponto") e E6 ("o contornador parou antes") produzem **exatamente o mesmo** FP de extensão;
só a fração do campo separa os dois. E o campo sai do `shape` do array, não do GT.

**A predição ocupa o campo inteiro em 25/30 casos, com mínimo de 0,908.** A medula
simplesmente não termina dentro do campo de visão — atravessa a aquisição toda, o que é
anatomicamente correto. O GT ocupa 0,817 do campo porque o atlas manda parar.

E a estratificação fecha o argumento:

| | S1 | S2 | S3 | amplitude |
|---|---|---|---|---|
| frac_FP_extensão | 0,9375 | 0,1247 | 0,8040 | **0,8128** |
| frac_campo_gt | 0,7925 | 0,9929 | 0,7207 | 0,2722 |
| **frac_campo_pred** | **1,0000** | **1,0000** | **1,0000** | **0,0000** |

**O modelo se comporta de forma idêntica nas três instituições.** O que varia em 0,81 é
quanto do campo o contornador desenhou. O "efeito de instituição" na medula, publicado na
coorte com amplitude de 0,13 de Dice, é em boa parte **E6 — divergência de definição do GT**,
não E1 e não desempenho do modelo.

### A refutação experimental

`EXP-B` testou a hipótese E1 diretamente: truncar a medula na janela em Z dos **pulmões
preditos** — uma regra que não vê o GT e roda num caso sem GT. A previsão estava registrada
no docstring antes da execução.

Ela **removeu quase exatamente o FP de extensão** que o diagnóstico mediu (FP mediano
14,005 → 2,238 mL, Δ −12,421 mL) e **criou mais FN do que o FP que removeu** (+17,255 mL).
Dice piorou em **25/30 casos**, Δ −0,1169, com regressão em Dice, HD95 e volume
simultaneamente.

**Leitura:** a janela torácica definida pelos pulmões preditos é **mais curta que o próprio
suporte em Z do GT da medula**. Logo a extensão da medula além do GT não pode ser removida
por referência torácica — e a hipótese E1 fica refutada por experimento, não por argumento.

---

## 6. Esophagus — regime oposto

| medida | mediana |
|---|---|
| frac_FP_extensão | **0,177** |
| FP_lateral | **6,348 mL** |
| FP_extensão | 1,612 mL |
| diferença de comprimento | **0,000 mm** |
| frac_campo_pred / frac_campo_gt | **0,566 / 0,557** |

O esôfago está no **regime contrário** ao da medula: o FP é **fronteira** (E3), não extensão.
A predição para praticamente onde o GT para — as frações de campo são quase idênticas (0,566
contra 0,557) e a diferença de comprimento mediana é **exatamente zero**. A pouca extensão que
existe é **distal** (1,483 mL contra 0,000 proximal), e no lado cranial a predição para
**antes** do GT (erro_proximal −3,0 mm).

Consequência prática: **os dois alvos precisam de remédios opostos**, e uma regra que ajude um
tende a atrapalhar o outro. `EXP-B` confirmou — a mesma terminação que destruiu a medula
também regrediu o esôfago em HD95 (+1,615 mm, 25/30 casos).

Nota de instituição: em S3 a predição é mais estreita (razão de área 0,889; 0,728 das fatias)
e em S1 mais larga (1,092; 0,300) — a instituição **inverte o sentido** do erro de fronteira,
amplitude 0,428.

---

## 7. Lung — controle de não regressão

Os pulmões cumpriram o papel de controle e **detectaram uma intervenção suspeita**.

`C_dilatação` melhora o FN em toda parte (−42,767 mL em Lung_R, −33,919 em Lung_L) mas troca
por FP muito maior (+54,889 e +48,329 mL), e estoura o limiar de volume nos **dois controles**
(+3,98 e +4,98 pp). É o padrão clássico de operação que "melhora recall" às custas de tudo o
mais — e foi pega pelo controle, não pelo alvo.

**Armadilha de leitura registrada:** em `C_dilatação/Lung_L` a **mediana do Dice sobe**
(0,9588 → 0,9618) enquanto a **mediana das diferenças pareadas é negativa** (−0,0022, com
18/30 casos piorando). Mediana de medianas e mediana de diferenças não são a mesma coisa, e a
primeira teria vendido uma regressão como ganho. Toda a matriz usa diferença pareada.

Nas demais intervenções os pulmões ficaram estáveis: `EXP-A` e `EXP-B` alteram 0/30 casos nos
controles, e `C_fechamento` move +0,0002.

---

## 8. Heart — ontologia, não otimização

**O coração não é alvo de otimização enquanto a definição anatômica entre previsão e GT não
estiver harmonizada.** Registrado como decisão de método, com o número que a sustenta.

Duas avaliações rotuladas, n = 30:

| | precision | recall | Dice |
|---|---|---|---|
| `heart_gt_definition` (variante A) | **0,9825** | **0,6719** | 0,7996 |
| `heart_gt_definition` (variante B) | 0,8740 | 0,6719 | 0,7571 |

Precision de 0,98 com recall de 0,67 é a assinatura de **"o GT é um superconjunto"**, não de
erro de localização.

O que o FN do coração é, medido: uma camada **espessa** em volta da predição — distância
radial mediana **4,312 mm**, P95 **13,262 mm**, com apenas **19,7 %** do FN dentro de 2 mm.
Contraste no mesmo instrumento: o esôfago tem P95 de 6,590 mm e 60,2 % dentro de 2 mm. E
**79,05 %** do anel de 1 voxel imediatamente fora da predição cai dentro do GT, contra 0,28 a
0,41 nas outras quatro estruturas.

Divergência total sem cancelamento: **342,27 mL**, dos quais **80,75 % é envelope lateral** e
19,25 % é corte em Z. A truncagem em Z é de um lado só: 37,50 mm além do GT no superior,
0,00 mm no inferior.

Estável nas três instituições (amplitude de 0,0112 em precision, 0,0305 em recall) — o que é
esperado de um viés de **definição**, não de contornador.

**Hipótese, não conclusão:** que essa camada *seja* o saco pericárdico e a gordura pericárdica
é compatível com os números, mas **não há ground truth de pericárdio neste dataset**. O que
foi medido é distância radial e fração de anel envolvido; a identidade anatômica não foi
medida e não é afirmada.

O TotalSegmentator 2.18.0 instalado **tem** uma classe `pericardium` na tarefa
`trunk_cavities` (task 343). Ela **não foi rodada** para "consertar" o coração. Uma comparação
ontologicamente correta exigiria confirmar que essa classe é o saco e não a cavidade — o nome
não é a definição — e reproduzir o corte superior do atlas a partir de referência **anatômica**
e não do alcance em Z do próprio GT. Fica para uma fase futura.

### Uma correção de método que os céticos levantaram e procede

A variante `A_suporte_gt` recorta a predição na janela em Z do GT **daquele caso** antes de
medir. Ela é uma variante de **avaliação**, já declarada circular no relatório da coorte — mas
publicar a precision resultante (0,9825) como resposta a *"a predição está contida no GT?"*
usa uma máscara construída com o GT. O número continua válido como **avaliação**; ele não pode
ser lido como propriedade da predição isolada. A variante B (0,8740) é a que não tem essa
dependência.

---

## 9. Threshold / confidence — **BLOQUEADO, com prova**

O TotalSegmentator 2.18.0 tem `-sp/--save_probabilities`. A investigação foi conclusiva e
**economizou a maior parte do orçamento da fase**.

Primeiro, o controle: a flag **não altera a predição** — o run com `-sp` reproduz o baseline
(Dice 1,0 em esophagus e spinal_cord; ≥ 0,99997 nos demais).

**O que ela grava:** `prob.npz` com uma chave `probabilities`, shape `(24, 260, 158, 229)`,
float32, softmax em [5,14e−24; 1,0], **796 MB em disco** por caso.

**Bloqueio 1 — a probabilidade não existe para os alvos.** `save_probabilities_path` é o
**mesmo caminho para toda parte do modelo**. Com o `roi_subset` congelado o run usa 3 partes
(291, 293, 294) e **cada uma sobrescreve a anterior**; sobra só a última. Os 24 canais
observados são `class_map_part_muscles`. Portanto `spinal_cord` é isolável (canal 11), mas
**`esophagus` e os cinco lobos pulmonares não têm probabilidade salva nenhuma** — pertencem à
parte `organs`, que foi sobrescrita.

**Bloqueio 2 — a grade.** A probabilidade sai na **grade interna do nnU-Net** (1,5 mm
isotrópico, RAS, recortada), não na grade da entrada. Trazê-la de volta **não reproduz a
máscara entregue com nenhuma ordem de interpolação**: teto de **Dice ≈ 0,955** (order 0 →
0,9484; order 1 → 0,9543; order 3 → 0,9546; canal + limiar → 0,9553).

E a leitura do npz **é exata** — `argmax` sobre os canais reproduz voxel a voxel o rótulo
interno (Dice 1,000000, `array_equal` True). Então toda a perda é **reamostragem**, com
atribuição limpa.

**Conclusão:** o sinal que uma curva de threshold mediria é **menor que os 0,045 de Dice que a
reamostragem custa**. A curva não seria interpretável. Resultado honesto: **limitação
documentada**, não uma curva inventada.

---

## 10. Spacing — pergunta não respondida

`fast=True` foi comparado ao baseline em 11 casos declarados antes, cobrindo os spacings
disponíveis.

**Primeiro achado, e ele invalida o experimento como teste de resolução:** `fast=True`
**não é uma alteração única**. Ele troca resolução interna (1,5 → 3,0 mm), **modelo**
(ensemble 291–295 → modelo único 297) e **trainer** (`nnUNetTrainerNoMirroring` →
`nnUNetTrainer_4000epochs_NoMirroring`) de uma vez só. Não existe, na configuração congelada,
parâmetro que mude **só** a resolução. Isso viola o princípio de uma alteração por experimento
e está declarado.

O que foi medido: o caminho de 3 mm **piora tudo** — Δ pareado de −0,0446 (SpinalCord),
−0,0581 (Esophagus), −0,0089 (Lung_R), −0,0114 (Lung_L), com **43 de 44 pares negativos**. O
erro adicional é **falta, não sobra**: o FP fica igual e o FN quase dobra. Ambos os controles
também regrediram, então a degradação é **global** — não é ganho no alvo pago no controle.

A alternativa de reamostrar a entrada para isotrópico **não é interpretável nesta base**: só o
**round-trip** da máscara para a grade original e de volta já custa 0,0510 de Dice na medula e
0,0543 no esôfago — **5× o limiar** de 0,01. Medido sem GT, sobre a própria predição.

**A pergunta original — se a heterogeneidade de spacing contribui para o erro — continua sem
resposta.** A penalidade de ir para 3 mm não acompanha o dz da entrada, e n por subgrupo é de
1 a 4 casos, com instituição/spacing/comprimento de campo confundidos.

Custo: o modo fast leva 50,7 s medianos contra 69,0 s do baseline, VRAM de pico 3.291,7 MiB.

---

## 11. Instituição

Usada **apenas como estratificação de avaliação**, nunca como feature.

O resultado mais importante está em §5: na medula, a amplitude de 0,813 no `frac_FP_extensão`
entre instituições convive com amplitude **0,0000** no `frac_campo_pred`. **O modelo não varia
entre instituições; o contorno varia.**

`frac_FN_fino` é a única fração **estável** entre instituições nas duas estruturas — amplitude
0,077 (medula) e 0,095 (esôfago), contra 0,813 e 0,183 do `frac_FP_extensão`. O erro de
fronteira é propriedade do modelo; o erro de extensão é propriedade do contorno.

---

## 12. Holdout

Split **30 development / 15 validation / 15 test**, estratificado **10/5/5 por instituição**,
determinístico por `sha256(semente|case_id)` — não por `random` com semente, cuja ordem
depende da iteração.

**O conjunto de teste não foi tocado.** Verificado por varredura: nenhum arquivo produzido
nesta fase cita qualquer um dos 15 casos de teste. O conjunto de validação também não foi
usado — nenhuma intervenção chegou a merecer confirmação.

**Ressalva declarada, não escondida.** A coorte de 60 casos foi medida e publicada **antes**
deste split existir, então a distribuição inteira já era conhecida. O holdout **não** protege
contra conhecimento prévio da dificuldade dos casos. Ele protege contra o que importa aqui:
nenhuma intervenção existia ainda, então o teste continua sendo dado nunca usado para
**escolher** ou **ajustar** regra.

O caso reincidente `LCTSC-Train-S3-006` caiu em *development* — serve de diagnóstico sem
contaminar o teste. Não foi usado para calibrar nada.

---

## 13. Melhorias

**Nenhuma.** O maior ganho pareado positivo em qualquer alvo foi **+0,0004** de Dice
(`C_fechamento`, medula), **25× abaixo** do limiar declarado.

`C_fechamento` é a única operação que move os quatro alvos e controles na direção de melhoria
**sem disparar regressão nenhuma** — melhora em 28/30 casos na medula. E é pequena demais para
contar: Δ mediano de +0,0002 a +0,0004 nas quatro estruturas, máximo absoluto de +0,00150.

---

## 14. Regressões

| intervenção | regressão | evidência |
|---|---|---|
| **B terminação torácica** | Dice, HD95 e volume na medula | Δ −0,1169; 25/30 casos piores; ΔFN +17,255 excede ΔFP −12,421 |
| **C dilatação 1 voxel** | Dice e volume nos **dois alvos** e volume nos **dois controles** | +3,98 e +4,98 pp de volume nos pulmões |
| **C calibre condicionado** | volume nos dois alvos | +3,06 e +2,28 pp |
| **spacing `fast=True`** | Dice em SpinalCord, Esophagus e Lung_L | 43/44 pares negativos; degradação global |

---

## 15. Resultados inconclusivos

**Se existe alguma regra de terminação longitudinal lícita** que reduza o FP de extensão da
medula sem criar FN maior. `EXP-B` testou **uma** regra (janela dos pulmões preditos, margem
0 mm) e ela falhou. Outras margens, outras referências anatômicas preditas e outros critérios
(ruptura de continuidade, queda de área) não foram executados.

**Se a heterogeneidade de spacing contribui para o erro** (§10). O experimento disponível não
isola resolução.

**Dentro de S3**, o `frac_campo_gt` da medula acompanha o dz — 0,601 a 0,667 nos casos de
3,0 mm e 0,991 no caso de 1,25 mm — mas n por subgrupo é de 1 a 4 e instituição, spacing e
comprimento de campo estão confundidos.

**A identidade anatômica da camada em volta do coração** (§8).

---

## 16. O que não funcionou — e o que isso ensinou

**`EXP-A component_cleanup` é praticamente inerte** porque a saída crua do TotalSegmentator
quase não tem componente residual: **0/30 casos alterados na medula** nos três limiares, 3/30
no esôfago. A hipótese E4 não tem material para atacar nesta saída.

E aqui houve uma **leitura de instrumento que quase enganou**: o `Δdice 0,0000` do `EXP-A`
**não é ausência de efeito** — com 1 a 9 de 30 casos alterados, a mediana das diferenças é zero
**por construção**. A coluna `max|Δdice|` foi acrescentada à matriz exatamente para impedir
essa leitura. O efeito real existe e é minúsculo (+0,00038 a +0,00176 nos 3 casos que mudaram).

**Uma métrica cega foi encontrada e descartada** (Parte 17): o critério topológico de
adjacência — "componente de FN que encosta na predição" — dá **1,0000 nas cinco estruturas**,
inclusive nos pulmões e no esôfago. Não separa envelope de deslocamento de fronteira, então
não serve para o argumento do coração. Foi substituído por distância radial e fração de anel,
que discriminam (0,7905 no coração contra 0,2754–0,4106 nas outras).

---

## 17. Hipóteses futuras

1. **Harmonizar a definição do coração** antes de qualquer otimização: confirmar o que
   `pericardium` da `trunk_cavities` de fato delimita, e derivar o corte superior de
   referência anatômica.
2. **Outras regras de terminação para a medula** — margem não nula sobre a janela torácica,
   critério de ruptura de continuidade, queda de área transversal. Todas ainda proibidas de
   ver o GT.
3. **Probabilidade por parte do modelo**: rodar `-sp` uma vez **por parte** contorna o
   Bloqueio 1 e daria acesso ao esôfago e aos pulmões. Não resolve o Bloqueio 2 (a grade).
4. **Um teto de referência.** O LCTSC não publica concordância interobservador, então não se
   sabe quanto do erro restante é do modelo e quanto é desacordo entre anotadores.

---

## 18. Decisão

| intervenção | classificação |
|---|---|
| A component_cleanup (3 limiares) | **SEM EVIDÊNCIA** |
| B terminação torácica | **REJEITADA** |
| C dilatação 1 voxel | **REJEITADA** |
| C fechamento | **SEM EVIDÊNCIA** |
| C abertura | **SEM EVIDÊNCIA** |
| C calibre condicionado | **REJEITADA** |
| spacing `fast=True` | **REJEITADA** |
| threshold / confidence | **BLOQUEADO** — não avaliável nesta configuração |

**Nenhuma intervenção alcançou PROMISSORA.** `A_BASELINE_V1` permanece inalterado. Nenhuma
chegou a ser testada em *validation* ou *test*, porque nenhuma passou no *development*.

---

## 19. Critério de saída

**1. Qual é o principal mecanismo de erro da SpinalCord?**
**E6 — divergência de definição do GT**, não E1. O FP é 80 % extensão, mas a predição ocupa o
campo de visão **inteiro** em 25/30 casos (mínimo 0,908) com amplitude **zero** entre
instituições, enquanto o GT ocupa 0,817 e varia 0,27 entre elas. O modelo segmenta a medula
por toda a aquisição — anatomicamente correto; o atlas manda o contorno parar. O componente
que **é** do modelo é o FN de casca fina (E2/E3, `frac_FN_fino` 0,891), estável entre
instituições e pequeno em volume.

**2. Qual é o principal mecanismo de erro do Esophagus?**
**E3 — deslocamento de fronteira.** FP lateral de 6,348 mL contra 1,612 mL de extensão,
diferença de comprimento mediana de exatamente 0 mm, frações de campo quase idênticas (0,566
contra 0,557). Regime **oposto** ao da medula.

**3. Os pulmões permaneceram estáveis?**
**Sim, exceto sob `C_dilatação` e `fast=True`.** Em `EXP-A` e `EXP-B` os controles têm 0/30
casos alterados. `C_dilatação` estourou o limiar de volume nos dois (+3,98 e +4,98 pp) e
`fast=True` regrediu Lung_L. O controle funcionou: pegou intervenções que o alvo sozinho não
teria reprovado.

**4. Quais intervenções realmente melhoraram o resultado?**
**Nenhuma.** Máximo de +0,0004, 25× abaixo do limiar.

**5. Quais causaram regressão?**
Terminação torácica, dilatação de 1 voxel, calibre condicionado e `fast=True` (§14).

**6. Existe evidência suficiente para alterar o baseline?**
**Não.** `A_BASELINE_V1` permanece.

**7. Qual intervenção deve passar para a próxima fase?**
**Nenhuma de pós-processamento.** O que passa é uma **conclusão**: o maior componente do erro
da medula é ontológico, e nenhuma operação sobre a máscara pode corrigi-lo — corrigir exigiria
mudar a **definição de avaliação**, não o modelo. Para o esôfago, o erro é de fronteira e
nenhuma morfologia testada o reduziu.

**8. Ainda precisamos de um modelo especializado?**
**Para o esôfago, provavelmente sim** — o erro é de fronteira, distribuído, e resistiu a todas
as operações morfológicas testadas; não é o tipo de erro que pós-processamento corrige.

**Para a medula, a pergunta está mal colocada.** Um modelo especializado treinado contra este
GT aprenderia a **parar onde o atlas de radioterapia manda parar**, que é uma convenção de
contorno e não a anatomia. Isso melhoraria o Dice contra o LCTSC e pioraria a fidelidade
anatômica — exatamente o oposto do que o VRmed quer. Antes de treinar qualquer coisa para a
medula, é preciso decidir **qual definição o VRmed adota**.

**A conclusão da Parte 16 se confirma:** o problema não foi resolvido por configuração,
preprocessing ou pós-processamento. Mas a razão não é que faltou uma operação melhor — é que
uma fatia grande do "erro" medido não é erro.

---

## 20. Reprodutibilidade

```bash
python -m scripts.validation.tier2.fase5                        # congela baseline + split
python -m scripts.validation.tier2.diagnostico_longitudinal     # Partes 5 e 6
python -m scripts.validation.tier2.confianca                    # Parte 7
python -m scripts.validation.tier2.ontologia_coracao            # Parte 14
python -m scripts.validation.tier2.experimentos_pos             # Parte 3
python -m scripts.validation.tier2.experimento_spacing          # Parte 8
```

Todo módulo tem `--autoteste` com **controle positivo**: a métrica precisa falhar quando
deveria falhar. Nenhuma métrica nova entrou sem isso.

Nenhuma regra de pós-processamento recebe o ground truth — verificado por
`inspect.signature` no autoteste, e cada operação roda num caso sem GT. Saídas em
`.clinica-dados/tier2/lctsc/fase5/` (fora do Git).
