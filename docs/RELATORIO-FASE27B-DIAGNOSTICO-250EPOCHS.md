# Fase 27B — diagnóstico do experimento de 250 épocas

**Data:** 2026-09-09 · **Run:** `VRMED-FASE26B-250EP-5FOLD` · **Commit:** `682e78c`
**Natureza:** **EXPERIMENTO EXPLORATÓRIO DE ORÇAMENTO REDUZIDO**

> O baseline canônico de 1000 épocas continua **oficialmente pendente**. Nada aqui o substitui,
> e nenhum número deste relatório é desempenho externo.

---

## 0. Três correções que a verificação adversarial impôs antes da publicação

Este relatório quase saiu com três afirmações erradas. Ficam registradas porque a versão
errada é intuitiva e vai ser reinventada por quem ler os números depois.

| # | O que eu ia afirmar | Por que está errado |
|---|---|---|
| 1 | *"O modelo vai melhor e é mais estável no conjunto reservado (0,763 ± 0,019) do que na validação interna (0,701 ± 0,137)."* | **Comparação inválida.** São estimadores diferentes (1 rede × ensemble de 5), variâncias de natureza diferente, e o gap inteiro são **2 casos**. |
| 2 | *"Precision > recall, erro de volume negativo e razão < 1 mostram sub-segmentação sistemática."* | **Circular.** `recall/precision = Vpred/Vref` **exatamente** — é o mesmo número três vezes, não três evidências. |
| 3 | *"`final` e `best` são praticamente idênticos."* | **Vale só para o Dice médio.** HD95 e erro de volume andam em **sentidos opostos**. |

Cada uma é desenvolvida abaixo com a formulação correta.

---

## 1. O que foi treinado e avaliado

| | |
|---|---|
| trainer | `nnUNetTrainer_250epochs` (variante do pacote, altera só `num_epochs`) |
| folds | 5, sobre os 10 casos de TRAIN (8 treino / 2 validação interna cada) |
| duração | **47,76 h** — 9,44 a 9,62 h por fold |
| avaliação interna | 10 casos *out-of-fold*, **uma rede por caso** (a do fold dele) |
| conjunto reservado | 6 casos da partição `validation`, preditos pelo **ensemble dos 5 folds** |
| TEST | **0 — não existe, e não foi criado** |

**Terminologia.** Evito "holdout": os 6 casos nunca entraram em treino, mas foram **lidos duas
vezes** (uma por checkpoint). O primário foi declarado na Fase 26A antes de qualquer resultado
e **não foi trocado**. Ainda assim, ler duas vezes não é o mesmo que nunca ter lido, e
**não existe desempenho externo neste projeto**.

---

## 2. Validação interna — e por que o desvio de 0,137 não é o que parece

**FATO.** Dice dos 10 casos *out-of-fold*: **média 0,7008 · mediana 0,7454 · dp 0,1369 ·
min 0,4401 · max 0,8642**.

| fold | Dice | casos |
|---|---|---|
| 0 | 0,7613 | `100` 0,7869 · `111` 0,7358 |
| 1 | **0,6009** | `106` **0,4401** · `114` 0,7617 |
| 2 | 0,7672 | `108` 0,6702 · `110` **0,8642** |
| 3 | **0,7706** | `102` 0,7861 · `112` 0,7550 |
| 4 | **0,6042** | `105` 0,7303 · `109` **0,4781** |

**FATO.** Esse 0,1369 **não é dispersão entre casos**. Ele mistura duas coisas:

- **dp entre as 5 redes** (médias por fold): **0,0898**
- **dp dentro dos folds** (dificuldade do caso): 0,1443

E é **dominado por dois colapsos**. Sem `106` e `109`: **n = 8, Dice 0,7613 ± 0,0558.**

---

## 3. A comparação que não se sustenta

**O que parecia acontecer:** o modelo melhora (+0,062) e fica 7× mais estável no conjunto
reservado. **INFERÊNCIA REFUTADA.** Quatro confundidores empurram todos no mesmo sentido:

**(A) Estimadores diferentes.** *Out-of-fold* = **uma** rede treinada em 8 casos. Reservado =
**ensemble de 5 redes**. O +0,062 mede, em boa parte, ganho de ensemble — não generalização.

**(B) Variâncias de natureza diferente.** O 0,137 tem componente **entre modelos** (0,0898); o
0,019 do ensemble **não tem nenhum** — é um preditor só.

**(C) n = 6 não sustenta afirmação sobre dispersão.** O IC 95 % do desvio, com n = 6, vai de
**0,0120 a 0,0472** — amplitude de quase 4×.

**(D) O mix de casos não é pareado.** O volume de GT do reservado (26,0–44,4 mL) está
**estritamente dentro** do de treino (23,6–60,7 mL). O caso `109`, o maior esôfago da coorte
(60,7 mL) e onde a validação interna colapsou, **não tem análogo no reservado**.

**O teste que fecha a questão:**

| conjunto | n | Dice |
|---|---|---|
| *out-of-fold*, todos | 10 | 0,7008 ± 0,1369 |
| *out-of-fold*, **sem os 2 colapsos** | 8 | **0,7613 ± 0,0558** |
| **conjunto reservado** | 6 | **0,7630 ± 0,0192** |

**Diferença entre as duas últimas linhas: 0,0018.** O "ganho" inteiro eram dois casos.

**FATO.** A diferença de média entre *out-of-fold* completo e reservado (+0,0622) **não é
significativa**: Welch p = 0,189; Mann-Whitney p = 0,368. Removendo os colapsos, p = 0,935.

**Formulação correta:** os dois números **não são diretamente comparáveis**. A menor dispersão
nos 6 é o esperado de um ensemble sobre um mix mais estreito de casos, e com n = 6 o intervalo
do desvio é largo de qualquer modo.

---

## 4. `checkpoint_final` × `checkpoint_best`

**FATO.** Dice médio: **0,7630** (final) contra **0,7639** (best) — diferença de **+0,0008**.
O **ranking completo dos 6 casos é idêntico**, e os *failure cases* também.

**Mas "praticamente idênticos" vale só para o Dice.** Caso a caso, o `best` ganha em 4 e
**perde em 2** (`104`: −0,0059; `115`: −0,0025): a média é **cancelamento**, não igualdade.
E duas métricas andam em **sentidos opostos**:

| | final | best | |
|---|---|---|---|
| HD95 médio | **10,80 mm** | 11,09 mm | best **2,7 % pior** |
| — caso `107` | **6,84 mm** | 9,00 mm | **+31,7 %** |
| erro absoluto de volume | 2,984 mL | **2,640 mL** | best **11,5 % melhor** |

**INFERÊNCIA.** A conclusão é robusta à escolha do checkpoint **quando enunciada em Dice e em
*failure cases***. Qualquer número de HD95 ou de volume **precisa dizer de qual checkpoint
veio**.

**RECOMENDAÇÃO.** A regra da Fase 26A se mostrou barata e correta: declarar o primário antes
custou zero e, aqui, não teria mudado nada — que é justamente o que se quer saber **depois**,
não antes.

---

## 5. Sub-segmentação — a leitura circular, e a correta

**A armadilha, e ela é fácil de cair.** Por definição:

```
precision = TP / Vpred        recall = TP / Vref
=>  recall / precision  =  Vpred / Vref     (exatamente)
```

**FATO, verificado voxel a voxel nos 6 casos** (delta ≤ 1,1 × 10⁻¹⁶): `101` 0,917455 =
0,917455 · `116` 0,758804 = 0,758804 · `104` 1,007508 = 1,007508.

Logo *"precision > recall"*, *"erro de volume negativo"* e *"razão predito/GT < 1"* são
**o mesmo número escrito de três formas**. Apresentá-las como três achados convergentes
seria contar a mesma evidência três vezes.

**O que de fato se observa — tendência de cauda, não sistemática:**

| | |
|---|---|
| conjunto reservado | erro de volume negativo em **5/6**; mediana **−6,6 %**; média −8,8 % inflada por um caso de −24,1 %; **sem ele, −5,75 %** |
| *out-of-fold* | razão < 1 em **7/10**; **3 super-segmentam** — `111` **+11,0 %**, `102` +5,1 %, `105` +1,6 % |

**E ~80 % do erro de fronteira é simétrico.** No reservado, FP + FN somam **87,92 mL**, mas o
líquido FN − FP é só **17,40 mL** — assimetria de **0,198**.

**INFERÊNCIA.** O erro é dominado por **imprecisão de localização da fronteira**, não por
encolhimento. Some-se a geometria: o esôfago é **tubular e fino**, então um deslocamento
sub-voxel de fronteira produz variação de volume muito maior do que produziria num órgão
compacto do mesmo volume.

**HIPÓTESE (exige experimento futuro):** o déficit líquido de volume vem da tendência do
`DC_and_CE_loss` a recuar em fronteiras de baixo contraste — o esôfago tem contraste fraco
contra o mediastino. Testável comparando perdas ou limiares, **em fase própria**.

---

## 6. Sobreajuste e subajuste

**FATO.** A diferença `train_loss − val_loss` cresce **monotonicamente nos 5 folds**:

| fold | ép. 0–62 | 63–125 | 126–187 | 188–249 | Dice do fold |
|---|---|---|---|---|---|
| 0 | −0,062 | −0,136 | −0,164 | −0,186 | 0,7613 |
| **1** | **−0,229** | −0,313 | −0,329 | −0,331 | **0,6009** |
| 2 | −0,041 | −0,131 | −0,156 | −0,169 | 0,7672 |
| 3 | −0,074 | −0,136 | −0,162 | −0,182 | 0,7706 |
| **4** | **−0,267** | −0,372 | −0,401 | −0,415 | **0,6042** |

**O padrão que importa:** nos folds 1 e 4 a diferença **já é grande no primeiro quarto**
(−0,23 e −0,27, contra −0,04 a −0,07 nos outros três). Ela não *cresce até* ficar grande —
ela **nasce grande**.

**INFERÊNCIA.** Isso é mais compatível com **dificuldade dos casos de validação daquele fold**
do que com sobreajuste progressivo. Um sobreajuste que se desenvolve deixaria os folds juntos
no início e os separaria ao longo do treino; aqui eles já começam separados.

**FATO.** Em todos os 5 folds o melhor pseudo-Dice veio **antes do fim** (épocas 54, 128, 135,
137, 205) e todos terminaram **abaixo do próprio pico**. Isso é o comportamento que a regra de
checkpoint da Fase 26A antecipou.

**O que NÃO se afirma.** Não se afirma que 250 épocas evita sobreajuste. O experimento
**não tem braço de comparação** — não há o run de 1000 épocas concluído para contrastar. O
objetivo era observar comportamento, e é isso que está acima.

---

## 7. Fase respiratória — observação descritiva, sem teste

Composição congelada: `c00` × 12, `c80` × 2, `c10` × 1, `c40` × 1.

| fase | n no reservado | casos | Dice |
|---|---|---|---|
| `c00` | 4 | `104`, `107`, `115`, `116` | 0,7402 · 0,7902 · 0,7584 · 0,7440 |
| `c80` | 1 | `101` | 0,7699 |
| `c40` | 1 | `103` | 0,7756 |

**Nenhum teste estatístico foi feito, e nenhum será.** Com **n = 1** em `c80` e `c40`,
inferência é impossível. Descritivamente, os dois casos de fase não-`c00` (0,7699 e 0,7756)
caem **dentro** da faixa dos quatro `c00` (0,7402–0,7902) — nada distingue os grupos, e nada
poderia com este n.

---

## 8. *Spacing* — o achado mais concreto, e ainda assim uma hipótese

Só **3 dos 16 casos** têm *spacing* fora de 0,9766 mm: `105` (1,1113) e `106` (1,1621) em
TRAIN, `104` (1,0527) no reservado.

**FATO.** O pior caso da validação interna é `106` — **Dice 0,4401, o *spacing* mais grosso do
pool**. E o pior Dice do reservado é `104` — **o único caso com *spacing* fora do padrão lá**.

**Mas a associação não se sustenta como regra:** `105`, também fora do padrão (1,1113),
obteve **0,7303** — dentro da faixa normal. E o outro colapso, `109` (0,4781), tem *spacing*
**padrão**: o que ele tem de atípico é o **volume**, 60,69 mL, o maior da coorte, e foi
segmentado a **43 %** do GT.

**INFERÊNCIA.** Os dois piores casos falham por razões **diferentes** — um é grade atípica, o
outro é anatomia atípica. Não há um fator único.

**HIPÓTESE.** Com apenas 2 casos fora do padrão no treino, o modelo tem pouquíssima exposição
a grades mais grossas; e com 1 caso acima de 50 mL, pouquíssima a esôfagos grandes. Ambas
testáveis — **e nenhuma foi testada aqui**.

**Nada foi removido, nada foi reconfigurado, o split não foi tocado.**

---

## 9. Figuras

`docs/overnight/phase26b/figuras/` — pior (`104`), mediano (`101`) e melhor (`107`), escolhidos
pela regra, não a dedo.

Regras de honestidade visual, aplicadas por código e cobertas por autoteste: cortes em
**posições fixas** (25/50/75 % da extensão do GT) e não escolhidos; **janela de mediastino
fixa** (nível 40, largura 400) igual para todos — janela por caso deixaria um caso ruim
parecer melhor; **contorno em vez de preenchimento**, para que a discordância apareça em vez
de sumir sob a cor de cima; e o **Dice impresso na própria figura**, para que nenhuma imagem
circule sem o número que a qualifica.

---

## 10. A pergunta científica

> **250 épocas produzem um modelo internamente utilizável para o próximo estágio do VRmed?**

**FATO.** Dice **0,7630 ± 0,0192** nos 6 casos reservados (0,740–0,790); ASSD mediano
**1,59 mm**; HD95 mediano **8,79 mm**; erro de volume mediano **−6,6 %**. Nenhuma predição
vazia, nenhum caso com recall ou precision abaixo de 0,50. Os 5 folds custaram 47,76 h.

**INFERÊNCIA.** Para o uso pretendido — **gerar malha 3D de esôfago para estudo anatômico em
VR** — o comportamento observado é adequado como **ponto de partida interno**. O erro
predominante é de fronteira, sub-voxel e em boa parte simétrico, que é o tipo de erro que a
reconstrução em malha suaviza; não há fragmentação nem predição vazia. O modo de falha que
**importaria** para esse uso é o do caso `116` — perda de um trecho longitudinal inteiro, que
produziria uma malha interrompida — e ele apareceu em **1 de 6**.

**HIPÓTESE.** O orçamento de 250 épocas não parece ser o fator limitante: as curvas dos cinco
folds achataram bem antes do fim e o pico veio, em média, na época 132 de 250. O limitante
aparente é **n = 10 no treino**, com cobertura rala de grades atípicas e de esôfagos grandes.
Exigiria experimento próprio para confirmar.

**O que NÃO se conclui.** Não se conclui que 250 épocas equivale a 1000 — o canônico não foi
concluído e **não há comparação**. Não se conclui generalização, independência, nem desempenho
externo. O modelo é **BASELINE INTERNO / EXPERIMENTAL**.

---

## 11. Limitações

1. **n = 6** no conjunto reservado, **n = 10** no treino. Nenhuma diferença aqui é conclusiva.
2. **TEST = 0.** Não existe desempenho externo, e os 6 foram lidos duas vezes.
3. Os 6 vêm da **mesma coleção, mesmo TPS, mesmo processo de contorno** que os 10.
4. GT **`SEMIAUTOMATIC`** em 16/16 — não é anotação humana pura.
5. **1/4 do orçamento** de otimização do canônico (62.500 iterações contra 250.000).
6. **Sem braço de comparação**: nada aqui mede 250 contra 1000.
7. `institution` e `annotation_protocol` **UNKNOWN**; extensão longitudinal **herdada do GT**.
8. A avaliação usa **ensemble de 5 folds**; resultados por fold isolado no reservado não foram
   medidos.

---

## 12. Próximos passos possíveis — nenhum executado

| # | Pergunta | Por quê |
|---|---|---|
| 1 | **De onde vem um TEST independente?** | É o bloqueio científico real. LCTSC, LyNoS, NSCLC-Radiomics e SegTHOR estão proibidos como TEST |
| 2 | O canônico de 1000 épocas muda o quadro? | 206,8 h. Só ele permite a comparação que este relatório recusa fazer |
| 3 | Grades atípicas são mesmo um fator? | Testável com aumento de dados de *spacing*, em fase própria |
| 4 | O que houve no caso `116`? | Perda de trecho longitudinal — o modo de falha que mais importa para malha em VR |

**O bloqueio continua sendo o TEST, e nenhuma quantidade de GPU o resolve.**
