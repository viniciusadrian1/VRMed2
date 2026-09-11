# Fase 30 — Viabilidade de TEST próprio e análise de poder com TRAIN = 10

**Data:** 2026-09-10 · **Natureza:** viabilidade e planejamento
**Nada baixado, nada treinado, nada inferido, nada anotado.**

**Decisão: (4) aumentar TRAIN primeiro, TEST próprio em seguida.**
**Tamanho mínimo com utilidade real: n = 10. Recomendado: n = 15–20 — depois de TRAIN crescer.**

---

## 1. O achado que decide a fase

**O gargalo não é o TEST. É o TRAIN — e isso é quantitativo, não opinião.**

Os cinco modelos do *cross-validation*, todos treinados com os **mesmos 10 casos** e os mesmos
hiperparâmetros, deram Dice de fold **0,6009 · 0,6042 · 0,7613 · 0,7672 · 0,7706** —
**desvio de 0,0898 entre redes, amplitude de 0,170**.

Agora compare com o que um TEST compraria:

| TEST | IC ±, σ otimista | IC ±, σ intermediário | IC ±, σ pessimista |
|---|---|---|---|
| n = 15 | **0,0106** = 0,12× o dp entre folds | **0,0309** = 0,34× | 0,0758 = 0,84× |

**INFERÊNCIA.** Num TEST de 15 casos, sob os dois cenários mais prováveis de σ, a medida seria
**3 a 8 vezes mais fina do que o próprio modelo varia** entre folds. Seria reportar um número
preciso sobre um objeto impreciso. **A incerteza dominante hoje não é de medição — é do modelo.**

---

## 2. 30A — o que um TEST faz com TRAIN = 10

### 2.1 Dados observados (lidos dos artefatos, não de memória)

**Conjunto reservado, n = 6, ensemble de 5 folds** (`avaliacao_26b_final.json`):

| case_id | Dice | HD95 | ASSD | ΔVol % |
|---|---|---|---|---|
| 4DLUNG-104 | 0,7402 | 4,71 | 1,403 | +0,75 |
| 4DLUNG-116 | 0,7440 | 20,28 | 2,677 | −24,12 |
| 4DLUNG-115 | 0,7584 | 9,85 | 1,775 | −3,77 |
| 4DLUNG-101 | 0,7699 | 7,74 | 1,368 | −8,25 |
| 4DLUNG-103 | 0,7756 | 15,41 | 2,023 | −12,48 |
| 4DLUNG-107 | 0,7902 | 6,84 | 1,230 | −4,98 |

**Dice: média 0,7630 · dp 0,0192.** **ΔVol %: média −8,81 · dp 8,71.**

**Out-of-fold, n = 10, uma rede por caso** (`summary.json` dos 5 folds): média **0,7008 · dp
0,1369**; sem os dois colapsos (`106` 0,4401 e `109` 0,4781), n = 8: **0,7613 · dp 0,0558**.

### 2.2 Os três σ, e por que não viram um só

**Eles vêm de estimadores diferentes** — 0,0192 é de um **ensemble de 5 redes** sobre 6 casos;
0,1369 é de **uma rede por caso** sobre 10. Fundi-los seria o mesmo erro que a verificação da
Fase 27B pegou. Aqui cada cenário roda separado e declara a origem.

| cenário | σ | origem |
|---|---|---|
| otimista | 0,0192 | reservado n=6, ensemble, mix estreito de casos |
| intermediário | 0,0558 | OOF n=8, uma rede por caso, sem os colapsos |
| pessimista | 0,1369 | OOF n=10, uma rede por caso, **com** os colapsos |

**Um fator de 7 entre o melhor e o pior.** Escolher um número único aqui seria esconder
justamente a incerteza que mais importa.

### 2.3 Efeito de um caso extremo — aritmética exata

Deslocamento da média por um caso, e a chance de ele aparecer (binomial com
p = 2/16 = 12,5 %, a frequência de colapso observada):

| n | 1 colapso | 2 colapsos | 1 excelente | P(≥1 colapso) |
|---|---|---|---|---|
| 3 | **−0,1043** | −0,2087 | +0,0357 | 33,0 % |
| 5 | **−0,0626** | −0,1252 | +0,0214 | 48,7 % |
| 6 | −0,0522 | −0,1043 | +0,0178 | 55,1 % |
| 10 | −0,0313 | −0,0626 | +0,0107 | 73,7 % |
| 15 | −0,0209 | −0,0417 | +0,0071 | 86,5 % |
| 20 | −0,0157 | −0,0313 | +0,0053 | 93,1 % |
| 30 | −0,0104 | −0,0209 | +0,0036 | 98,2 % |

**A leitura que importa, e ela é desconfortável.** Com n = 5, há **49 % de chance** de o TEST
conter um colapso, e esse único caso moveria a média em **0,063** — mais do que a diferença
entre qualquer par de conclusões que o projeto queira distinguir. **A média de um TEST pequeno
seria, em boa medida, o resultado de um sorteio.**

*Premissa explícita:* p = 12,5 % vem de 2 colapsos em 16 casos avaliados, e é ela mesma
incertíssima com esse n. Serve para ordem de grandeza, não para decisão fina.

### 2.4 Quatro coisas que não são a mesma

| conceito | o que um TEST maior resolve |
|---|---|
| **precisão do estimador** | **sim** — é literalmente o que o IC mede |
| **generalização** | **não** — depende de o TEST vir de outra população/instituição, não do n |
| **validade externa** | **não** — depende de independência demonstrada, que a Fase 29 não achou |
| **tamanho do treino** | **não** — TEST não treina nada |

Confundir os quatro é o erro que faria alguém achar que um TEST de 20 casos da mesma coorte
resolveria o problema científico do projeto. Não resolveria nenhum dos três últimos.

---

## 3. 30B — tamanho de TEST minimamente útil

| n | largura do IC (σ interm.) | sensibilidade a outlier | utilidade científica | interpretação |
|---|---|---|---|---|
| **3** | ±0,139 | 1 colapso move **0,104** | **nenhuma** | a média é o sorteio, não o modelo |
| **5** | ±0,069 | move 0,063 | **muito baixa** | 49 % de chance de um colapso dominar |
| **6** | ±0,059 | move 0,052 | baixa | é o n atual do reservado — já se sabe o que ele entrega |
| **8** | ±0,047 | move 0,039 | baixa-média | ainda sensível a um caso |
| **10** | ±0,040 | move 0,031 | **mínima defensável** | um caso deixa de virar a conclusão |
| **15** | ±0,031 | move 0,021 | **boa** | estável a um caso; 0,34× o dp entre folds |
| **20** | ±0,026 | move 0,016 | boa | ganho marginal sobre 15 |
| **25** | ±0,023 | move 0,013 | marginal | |
| **30** | ±0,021 | move 0,010 | marginal | mede 4× mais fino que o modelo varia |

**Simulação** (reamostragem dos 6 valores observados — SIMULAÇÃO, não teoria, e limitada por a
distribuição de origem ter 6 pontos): n=5 → largura 0,0305; n=10 → 0,0215; n=15 → 0,0177;
n=20 → 0,0153.

**Critério usado, declarado antes de olhar a tabela:** um TEST tem utilidade real quando
**remover ou acrescentar um caso não muda a conclusão qualitativa**. Com uma conclusão do tipo
"Dice ≈ 0,76", um deslocamento de 0,03 não muda; um de 0,10 muda.

→ **Mínimo com utilidade real: n = 10. Recomendado: n = 15–20.**

**Sobre as outras métricas.** O erro percentual de volume tem **dp 8,71 pp** nos 6 casos —
quatro vezes o desvio relativo do Dice. Um TEST dimensionado pelo Dice **não** dá precisão
equivalente em volume: com n = 15, o IC de ΔVol% seria de ±4,8 pp. HD95 (dp 5,90 mm) é ainda
mais disperso. **Dimensionar pelo Dice e depois reportar volume com a mesma confiança seria
erro.**

---

## 4. 30C — o gargalo é TRAIN

| cenário | reduz incerteza de desempenho | de generalização | de capacidade do modelo | de variabilidade populacional |
|---|---|---|---|---|
| 1 · TRAIN 10, TEST 0 | — | — | — | — |
| 2 · TRAIN 10, TEST 5 | pouco (±0,069) | não | **não** | pouco |
| 3 · TRAIN 10, TEST 10 | médio (±0,040) | não | **não** | médio |
| 4 · TRAIN 10, TEST 15 | bom (±0,031) | não | **não** | bom |
| 5 · TRAIN 15, TEST 10 | médio | não | **sim** | médio |
| 6 · TRAIN 20, TEST 10 | médio | não | **sim** | bom |
| 7 · TRAIN 25, TEST 10 | médio | não | **sim** | bom |
| 8 · TRAIN 30, TEST 10 | médio | não | **sim** | muito bom |

**O padrão:** as colunas 3 e 4 só se movem quando **TRAIN** cresce. Nenhum tamanho de TEST as
move.

**O que se pode afirmar, e o que não.** Não se afirma que mais TRAIN **melhora o desempenho** —
isso exigiria experimento. O que se afirma é metodologicamente seguro: **mais TRAIN aumenta a
informação disponível para estimar o modelo e reduz a dependência de poucos casos.** A evidência
direta disso já existe no projeto: com 8 casos por fold, trocar quais 2 saem move o Dice do fold
de 0,60 a 0,77.

---

## 5. 30D — requisitos de um TEST próprio

Ontologia: **`ESOPHAGUS_ONTOLOGY_V1`**, sem alteração.

| # | Requisito | Especificação mínima |
|---|---|---|
| 1 | número de casos | 10 mínimo, 15–20 recomendado |
| 2 | população | adulto, tórax; **não** pediátrico (Fase 29 refutou: DSC 0,47) |
| 3 | aquisição | CT torácica; declarar fabricante e protocolo |
| 4 | resolução | z ≤ 3,0 mm; evitar 5 mm (degrada estrutura fina) |
| 5 | variedade institucional | **≥ 2 instituições**, nenhuma delas VCU |
| 6 | protocolo de anotação | escrito **antes**, com limites cranial e caudal explícitos |
| 7 | anotadores | ver §6 |
| 8 | revisão | obrigatória, e **quantificada** (Dice interobservador) |
| 9 | independência do TRAIN | outra coorte, outra instituição, verificada por UID e `sha256` |
| 10 | independência do baseline | **impossível de garantir hoje** — ver §8 |
| 11 | controle de acesso | contexto `avaliacao`, leitura única |
| 12 | versionamento | esquema `VRMED-ESOPHAGUS-DATASET-V1`, 22 campos |
| 13 | congelamento | manifesto + snapshot + `sha256`, como o pool16 |
| 14 | custo estimado | ver §6 — dominado por hora de especialista |
| 15 | tempo estimado | 2–6 semanas conforme o modelo de anotação |
| 16 | risco de viés | **o maior**: anotar nós mesmos o TEST cria dependência de anotador com quem definiu a ontologia |

**O risco 16 merece destaque.** Um TEST anotado pela mesma equipe que escreveu a ontologia mede
**aderência à nossa própria convenção**, não desempenho anatômico. É defensável para uso
interno, e **não** é validade externa.

---

## 6. 30E — desenhos de anotação

| modelo | vantagem | desvantagem | viés | custo | reprodutibilidade | valor científico |
|---|---|---|---|---|---|---|
| **A** · 1 anotador + revisão | mais barato, mais rápido | sem medida de concordância | do anotador único | 1× | baixa | baixo — é o que o 4D-Lung já tem |
| **B** · 2 independentes + adjudicação | mede concordância | adjudicação pode ser dominada por um | do adjudicador | 2,5× | **boa** | **bom** |
| **C** · 2 independentes + 3º adjudicador | melhor controle de viés | mais caro e lento | menor | 3,5× | **melhor** | **melhor** |
| **D** · 1 especialista + revisão cega | barato, cegamento reduz ancoragem | ainda 1 fonte primária | do especialista | 1,5× | média | médio |

**Mínimo defensável: modelo B.** Ele é o menor desenho que produz **Dice interobservador** — e
sem esse número o projeto não tem piso contra o qual comparar o modelo. Sem ele, um Dice de 0,76
não tem referência: pode estar próximo do teto humano ou longe.

**Ideal: modelo C**, se houver três especialistas disponíveis.

**Modelo A é explicitamente insuficiente** para um TEST — reproduziria a limitação que o projeto
já carrega no 4D-Lung (`SEMIAUTOMATIC`, revisor único, taxa de edição UNKNOWN).

---

## 7. 30F — três desenhos de tamanho

| | TEST-MICRO (5) | TEST-COMPACT (10) | TEST-ROBUST (15–20) |
|---|---|---|---|
| objetivo | prova de conceito do pipeline de anotação | primeira estimativa defensável | estimativa estável |
| poder descritivo | IC ±0,069 (σ interm.) | ±0,040 | ±0,031 a ±0,026 |
| limitação | **49 % de chance de um colapso dominar** | 1 caso move 0,031 | 1 caso move 0,021 |
| custo relativo | 1× | 2× | 3–4× |
| valor científico | baixo | médio | **bom** |
| risco de conclusão instável | **alto** | moderado | baixo |

### Recomendação: **TEST-ROBUST, com n = 15**

Não porque "15 é suficiente" — mas porque **15 casos fornecem, sob σ intermediário, um IC de
±0,031 e estabilidade a um caso de 0,021**, que é a faixa onde a conclusão deixa de depender de
qual caso entrou. Ir a 20 melhora pouco (±0,026); ficar em 10 dobra a sensibilidade a um caso.

**E com uma condição:** só depois de TRAIN crescer. Um TEST-ROBUST medindo um modelo que varia
0,09 entre folds gasta precisão onde ela não falta.

---

## 8. 30G — comparação com os candidatos C externos

| | RTOG-0617 | RADCURE | Pediatric-CT-SEG |
|---|---|---|---|
| benefício científico | **alto** — adultos com NSCLC, a população certa | médio — H&N, esôfago parcial | **nenhum como TEST adulto** |
| dificuldade | alta — NIH Controlled Data Access | alta — DUA + harmonização TG-263 | baixa |
| restrições | dbGaP/DUA, não redistribuível | idem | CC BY 4.0 |
| tempo | semanas a meses (aprovação) | idem + harmonização | dias |
| risco | **existência do contorno de esôfago não demonstrada** | é corpus de treino de modelos de OAR; superset de OPC-Radiomics | pesos treinados nele |
| independência | INCONCLUSIVA nos 5 eixos | INCONCLUSIVA | INCONCLUSIVA em 2 |
| potencial como TEST | **condicional** — decide-se com uma verificação barata | baixo | **nulo** (domain shift apenas) |

**O único com sinal real é o RTOG-0617**, e ele tem uma pergunta binária barata na frente:
**existe contorno de esôfago nos RTSTRUCT?** Se não existe, cai para E e o assunto fecha. Se
existe, vira o melhor candidato externo do projeto — adultos, NSCLC, a população certa.

---

## 9. 30H — TEST para medir o modelo × TEST para comparar com o baseline

**São dois TESTs diferentes, com requisitos diferentes, e o projeto vinha tratando como um.**

| | TEST para medir **o modelo próprio** | TEST para **comparar com o TotalSegmentator** |
|---|---|---|
| precisa ser independente do **treino** do VRmed | **sim** | sim |
| do **validation** | sim (senão a seleção contamina) | sim |
| da seleção de arquitetura / hiperparâmetro / época | sim — e no VRmed **já está**: a arquitetura veio do planner, o orçamento do pré-registro, e o checkpoint primário foi declarado antes | sim |
| da **linhagem de anotação do baseline** | **não precisa** | **precisa, e é aqui que trava** |

**Por que o segundo trava.** A Fase 29 demonstrou que o rótulo de esôfago do TotalSegmentator
**v1** foi pré-segmentado por modelos treinados em BTCV e SegTHOR (68 das 104 classes), e que
para o **v2** a documentação é **inconclusiva** — não há artigo, model card, nem lista de treino
por caso, e os ~420 sujeitos adicionais não foram publicados.

**Consequência científica.** Uma comparação "VRmed × TotalSegmentator" num TEST qualquer mede a
diferença entre **um modelo treinado em GT de radioterapia** e **um modelo cujo GT descende de
outros modelos**. A diferença observada seria interpretável apenas como *diferença entre duas
convenções de rótulo*, não como *diferença de qualidade anatômica*.

**Isso não elimina o baseline**, e o baseline **não é GT humano** — as duas coisas continuam
valendo. O que muda é o que se pode escrever sobre a comparação: ela é uma **referência de
convenção**, não um veredito de acurácia.

**INFERÊNCIA prática, e é uma boa notícia:** o TEST para **medir o modelo próprio** é bem mais
fácil de construir do que o TEST para **comparar com o baseline**. O primeiro precisa apenas ser
independente do nosso treino. O segundo precisaria de algo que hoje não existe: um GT cuja
linhagem seja comprovadamente disjunta da do TotalSegmentator.

---

## 10. 30I — os quatro cenários

### A · Manter TEST = 0 e aumentar TRAIN
**Vantagens:** ataca a incerteza dominante (dp 0,0898 entre folds); nenhum custo de anotação;
nenhum risco de criar um TEST enviesado.
**Desvantagens:** continua sem número publicável; a dívida do TEST só adia.
**Risco:** baixo. **Custo:** baixo (dados públicos já auditados). **Tempo:** semanas.

### B · Criar pequeno TEST próprio agora
**Vantagens:** primeiro número com holdout de verdade.
**Desvantagens:** mede com precisão um modelo instável; se n < 10, a média é sorteio.
**Risco:** **alto** — o viés de anotador próprio (§5, risco 16) contamina o resultado
permanentemente. **Custo:** alto (hora de especialista). **Tempo:** 2–6 semanas.

### C · Destravar TEST externo
**Vantagens:** independência de instituição sem custo de anotação.
**Desvantagens:** DUA, meses, e o eixo de linhagem continua aberto.
**Risco:** alto de gastar meses e terminar em C de novo. **Tempo:** meses.

### D · Aumentar TRAIN e depois criar TEST próprio
**Vantagens:** ataca primeiro o que domina a incerteza e **depois** mede, quando medir valer a
pena; o TEST pode ser dimensionado com σ melhor conhecido.
**Desvantagens:** o número publicável demora mais.
**Risco:** baixo. **Custo:** médio, distribuído. **Tempo:** semanas + 2–6 semanas.

---

## 11. 30J — decisão

### **(4) Aumentar TRAIN primeiro; TEST próprio em seguida.**

**Fundamentação, em três números:**

1. **dp entre folds = 0,0898** com TRAIN = 10. É a maior fonte de incerteza do projeto.
2. **Um TEST de 15 mediria a ±0,031** (σ intermediário) — **3× mais fino do que o objeto varia**.
3. **Com n = 5, há 49 % de chance** de um colapso dominar a média.

Investir primeiro no TEST seria comprar precisão de medida quando o que falta é estabilidade do
medido.

**O que fica decidido, e o que não.** Fica decidido **não criar TEST agora**. **Não** fica
decidido que mais TRAIN melhora o Dice — isso exige experimento, e esta fase não treinou nada.

---

## 12. Respostas diretas ao critério de sucesso

1. **Tamanho mínimo com utilidade real:** **n = 10** — abaixo disso um caso vira a conclusão.
2. **Recomendado:** **n = 15** (TEST-ROBUST), com modelo de anotação **B** no mínimo.
3. **TEST próprio é preferível aos C externos?** **Sim para medir o modelo próprio** — mais
   rápido, sem DUA, ontologia sob controle. **Não resolve** a comparação com o baseline. E o
   RTOG-0617 continua valendo uma verificação barata antes de descartar.
4. **Com TRAIN = 10, o gargalo é TRAIN**, demonstrado pelo dp de 0,0898 entre folds.
5. **Sequência:** Fase 31 amplia TRAIN → Fase 32 reavalia σ e redimensiona → Fase 33 constrói o
   TEST.
6. **Cenário que maximiza valor por custo:** **D**.

---

## 13. Riscos e pendências

| # | Item | Estado |
|---|---|---|
| 1 | σ de um TEST futuro | **desconhecido**; os três cenários diferem por fator 7 |
| 2 | p de colapso = 12,5 % | de 2 em 16 — ordem de grandeza, não decisão fina |
| 3 | viés de anotador próprio | **o maior risco** de um TEST interno |
| 4 | linhagem do TotalSegmentator v2 | continua **inconclusiva** (Fase 29) |
| 5 | RTOG-0617 | contorno de esôfago **não demonstrado** — verificação barata pendente |
| 6 | IC assume amostragem independente | com casos de uma só coorte, é **aproximação** |

---

## 14. Próxima fase

**Fase 31 — ampliação auditável do TRAIN.** Mesma disciplina das Fases 23–25: funil de ingestão,
22 campos, anti-leakage por quatro identidades, e **nova versão do congelamento** — nunca edição
da V1.

**Duas verificações baratas que cabem antes**, sem download e sem contato: confirmar se o
RTOG-0617 tem contorno de esôfago, e abrir os ROI Names de um RTSTRUCT do Pediatric-CT-SEG para
fechar a pendência de "esôfago é manual".
