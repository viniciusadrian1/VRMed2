# VRmed — Fase 9: desenho experimental do modelo de esôfago

Data: 2026-09-05 · Esta fase termina **antes do primeiro epoch**. Nada foi treinado.

> Uso educacional e experimental. Não é validação clínica.

**Em uma linha: TREINO BLOQUEADO — e não só porque falta um teste independente. A pergunta
"o novo modelo supera o baseline?" também não é respondível hoje, o que é menos óbvio e mais
grave.**

---

## 1. Objetivo

Transformar a preparação do esôfago em um experimento treinável e avaliável. A pergunta:
*qual experimento demonstraria que um modelo especializado realmente melhora a segmentação, em
vez de apenas aprender a convenção de um dataset?*

---

## 2. Estado atual

`BASELINE_ESOFAGO_V1` inalterado: TotalSegmentator 2.18.0, task `total`, saída crua, campo
completo, LCTSC development n=30. Mediana: Dice 0,7880 · HD95 6,27 mm · ASSD 1,39 mm ·
precision 0,8078 · recall 0,8038. Cauda: Dice 0,4849–0,8761 · HD95 2,62–38,62 mm.

---

## 3. Definição operacional

A ontologia tinha uma **contradição**: dizia "limite superior = cricoide" e, logo abaixo, que o
cricoide não é localizável. Esta fase a resolve **por medição**, não por escolha.

O pipeline não localiza cricoide nem junção gastroesofágica. Mas localiza a **carina** (extremo
caudal da máscara `trachea`): presente em **30/30** casos, estável dentro do critério declarado
em **29/30** (pior caso 2 voxels). Tendo o marco, três medidas fecham a questão:

| medida | resultado |
|---|---|
| **As pontas estão a deslocamento fixo da carina?** | **Não.** Cranial: mediana +120,0 mm, IQR **23,5 mm**. Caudal: −105,5 mm, IQR **13,6 mm**. Ambos **acima do HD95 mediano de 6,27 mm** que se quer medir |
| **As pontas são cortes ou terminações?** | **Cortes.** A fatia terminal caudal tem **2,2447×** a área mediana do próprio caso, e em **30/30** está acima de 1,00×. Uma estrutura que acaba anatomicamente **afina**; esta acaba na largura cheia |
| **O corte vem do campo de visão?** | **Não.** Caudal no limite do campo em **0/30**, cranial em **1/30**. É decisão de contorno |

### Veredito por alternativa

| | veredito | pelo dado |
|---|---|---|
| **A** preservar a extensão do GT como definição | **refutada** | elevaria o corte a fato anatômico, e a ponta caudal está no ponto mais largo em 30/30 |
| **B** landmarks detectáveis | **refutada** | o único marco é a carina; ancorar num deslocamento fixo injetaria erro de dezenas de mm — **maior que o erro que se quer medir** |
| **C** recortar ao trecho consistente | **refutada** | o trecho 30/30 existe (−76 a +91 mm da carina) mas guarda só **0,6881** do volume, e seus limites são os dois casos mais truncados — trocaria uma fronteira arbitrária por outra |
| **D** herdada do GT, declarada **não avaliável** | **ESCOLHIDA** | é a única compatível com as três medidas. Herdar já é o que o pipeline faz; o que muda é **parar de chamar isso de definição anatômica** |

**Ressalva que não pode cair junto:** com **1 contorno por caso**, a dispersão acima é um
**limite superior** da reprodutibilidade — mistura variação anatômica com decisão do
contornador, e separá-las é impossível neste dataset. Ela prova que a extensão **não é
reconstruível a partir do marco**, não que o contornador tenha errado.

---

## 4. Resolução e representabilidade

Espessura característica mediana **9,3253 mm** = 8,94 voxels em X e **3,46 voxels em Z**.

**A espessura de parede NÃO é medível a partir do GT** — ele é maciço e não separa parede de
lúmen. O que se pode fazer é declarar a espessura anatômica da literatura (3–4 mm) como
**premissa** e compará-la com o `dz` de cada caso. Sob essa premissa declarada, a parede ocupa
**1,0–1,6 voxel em Z**.

**Distinções que a aquisição não suporta, e que portanto não podem ser critério de avaliação de
nenhum modelo futuro:** parede contra lúmen · a posição exata da fronteira em Z dentro de um
voxel · qualquer afirmação sobre a extensão longitudinal (§3).

---

## 5. Datasets candidatos

A matriz foi reusada e **ampliada com busca própria**. Dois candidatos novos, nenhum suficiente:

**Pediatric-CT-SEG** — anota `Esophagus`, contornos de especialista. **Falha** em definição
documentável (protocolo de contorno não publicado) e em equivalência anatômica com o objeto do
baseline.

**HaN-Seg** — esôfago **cervical** com GT humano e licença verificável, e traz um landmark
independente para o limite superior. **Falha em cobertura**: é esôfago cervical, não o objeto
que o `BASELINE_ESOFAGO_V1` mede.

**Varredura sistemática do TCIA:** `Modality=SEG` devolve 26.432 séries em 34 coleções — **todas
de lesão**, nenhuma com OAR de esôfago. `Modality=RTSTRUCT` devolve 67.844 séries em 29
coleções; as 10 maiores estão **bloqueadas por acesso**.

### Duas correções à minha própria matriz

**SegRap2023 não está "encerrado"** como registrei. Está **gated por acordo assinado**, sem
licença publicada: 120 casos de treino com rótulos seguem disponíveis mediante *"a signed End
User Agreement"* enviada por e-mail.

**A definição de esôfago do LCTSC é documentável**, e explica independentemente por que o GT é
maciço: *"The esophagus should be contoured from the beginning at the level just below the
cricoid to its entrance to the stomach at GE junction"*, usando janela de mediastino.

---

## 6. Análise de independência

### O mapeamento S1/S2/S3 foi RECUPERADO

Eu havia declarado isso um bloqueio na Fase 7. Foi resolvido por **quatro canais independentes**:

| | instituição | evidência |
|---|---|---|
| **LCTSC-S1** | **MAASTRO** | `dz` medido 3,0 mm em 20/20 (o artigo declara MAASTRO = 3 mm); `SeriesDescription` *"RespCT … 50% Ex"* — fase expiratória do 4DCT — em 19/20 (o artigo: MAASTRO = *"exhale phase of 4DCT"*) |
| **LCTSC-S2** | **MDACC** | `dz` 2,5 mm em 20/20 (artigo: MDACC = 2,5 mm); `"Ave-IP(10) 0%_10%…90%"` — projeção de intensidade média de 10 fases — em 19/20 (artigo: MDACC = *"mean intensity projection of the 4DCT"*) |
| **LCTSC-S3** | MSKCC | por eliminação e por assinatura *free-breathing*: nenhum descritor de 4DCT em 20/20, cabeçalho de fabricante removido em 20/20 |

**E isso inverte a leitura do overlap MAASTRO.** Como S1 = MAASTRO, o par
**LCTSC-S1 × NSCLC-Radiomics** é a **única célula pública** em que anatomia e instituição ficam
fixas e **só o estilo de anotação muda** — mesmos scanners (Sensation Open, Biograph 40), mesma
família de protocolo. O overlap deixa de ser só contaminação e vira **instrumento** para medir
o efeito de estilo. É hipótese, não resultado.

### A correção mais séria — e ela é contra o que eu publiquei

O `RELATORIO-TIER2-COORTE.md` §1 afirma que o task `total` da v2 foi treinado *"exclusivamente
em TCs clínicas de rotina do University Hospital Basel (1082 / 57 / 65)"*. **Isso está errado.**

O repositório oficial declara, em `resources/improvements_in_v2.md`:

> *"We increased the number of training images from 1139 to 1559."*
> *"more images from GE scanners and **other institutions**"*
> *"we did not publish the additional subjects we used for TotalSegmentator v2 training"*

**27 % do treino da v2 (420 imagens) é não declarado e vem de outras instituições.** Os números
1082/57/65 descrevem o dataset **público da v1**, não o treino real da v2.

**Consequência:** não posso afirmar que o LCTSC está fora do treino do TotalSegmentator v2.
Isso **não prova contaminação** — remove a prova de independência que eu havia declarado. O
Tier 2 continua sendo a melhor avaliação disponível; deixa de ser uma avaliação com
independência **estabelecida** e passa a ser uma com independência **não verificável**.

### Sobre a ausência de interseção de UID

A interseção entre LCTSC-S1 e NSCLC-Radiomics é 0/20 em `PatientID`, `StudyInstanceUID` e
`SeriesInstanceUID` — mas as raízes de UID são de organizações distintas (`…14519.5` contra
`…32722.99`), ou seja, **reanonimização independente**. **Ausência de interseção de UID não é
evidência de independência de casos.**

---

## 7. Desenho TRAIN / VALIDATION / TEST

**Não há desenho válido hoje.** Nenhuma fonte pública satisfaz simultaneamente os sete
critérios obrigatórios: GT humano · independente do treino · independente da validação ·
licença e acesso verificáveis · definição documentável · geometria suficiente para mm · sem uso
prévio para hiperparâmetro.

---

## 8. Candidato de modelo

`nnU-Net 3d_fullres`, **registrado e não otimizado**. `nnunetv2` 2.8.1 já instalado. Patch
128³, batch 2, AMP fp16, 4.811 MiB de 16.380 MiB, 0,453 s/passo → **31,5 h por fold**. Sem
cascata (29/30 casos cabem em 128 fatias). Desequilíbrio de classe: **0,72 %** do patch.

---

## 9. Métricas e 10. Critérios

Congelados e inalterados: Δ Dice ≥ +0,01 · sem regressão de Dice ≥ 0,01, de HD95 ≥ 1,0 mm, de
volume ≥ 2 pp · melhora em múltiplos casos · melhora fora do treino · sem regressão em
`Lung_R`/`Lung_L` · benefício na MASTER · sem ajuste manual por caso.

**As duas perguntas são diferentes e podem ter respostas opostas:**

**(i) o novo modelo supera o baseline?** — **também não é respondível hoje.** Este é o achado
menos óbvio da fase. Não basta faltar o teste: o comparador (`BASELINE_ESOFAGO_V1`) tem 27 % do
treino não declarado, então nem a comparação contra ele tem independência garantida.

**(ii) o resultado generaliza ou é efeito de domínio?** — o mecanismo que faria (i) e (ii)
divergirem **já está medido**: ICC1 de descritores de **estilo** por instituição 0,5098 e
0,4719 (p 0,0005) contra ICC1 de **anatomia** 0,0788 / 0,0275 / −0,0762 (p 0,16–0,74).
Instituição explica convenção de contorno e **não** explica anatomia.

---

## 11. Controles anti-leakage

`scripts/validation/tier2/protocolo_esofago.py` — **dez guardas como código executável**, cada
uma com exceção própria e controle positivo. Verificadas **por mutação**: desligar cada uma
derruba o autoteste, **10/10**.

Cobrem: treino sem TEST definido · treino usando LCTSC test · GT não-humano · caso em treino e
teste · caso repetido · dataset sem licença confirmada · affine incompatível · máscara fora da
grade · avaliação sobre fatias *ignore* (o SAROS ensinou: 4 de 5 fatias são 255) · comparação
entre definições anatômicas incompatíveis.

**A decisão é produzida por código rodando contra o estado real do repositório**, não por prosa:
`decidir()` lê o `split.json` real e chama as guardas. Saída: **9 guardas recusaram**.

---

## 12. Riscos

**O comparador não tem independência garantida** (§6) — risco novo desta fase.

**Aprender estilo em vez de anatomia**, já medido.

**A dispersão da extensão é um limite superior**, não uma medida de erro: com 1 contorno por
caso, variação anatômica e decisão do contornador são inseparáveis.

**O par MAASTRO como instrumento é hipótese**, não desenho validado.

---

## 13. Decisão final

# **TREINO BLOQUEADO**

**1. Existe conjunto de TESTE independente adequado?** **Não.**
**2. Qual?** Nenhum. Pediatric-CT-SEG falha em definição documentável e equivalência anatômica;
HaN-Seg cobre só esôfago cervical; WORD e SegRap2023 falham em licença/acesso; SEG do TCIA não
tem OAR de esôfago; os 10 maiores RTSTRUCT estão bloqueados.
**3. Independente do treino?** Não avaliável — nenhum candidato passa.
**4. Independente da validation?** Idem.
**5. Definição anatômica?** Do LCTSC, documentável e recuperada (§5). Do VRmed, corrigida para
conter só critérios observáveis (§3).
**6. Instituição/origem?** LCTSC recuperado: S1 = MAASTRO, S2 = MDACC, S3 = MSKCC.
**7. Risco de leakage?** **Sim, identificado e não eliminável hoje** — 27 % do treino do
comparador é não declarado e inclui outras instituições.
**8. O treino pode começar?** **Não.**
**9. Qual bloqueio falta?** Dois, e o segundo é novo: *(a)* não existe teste público que
satisfaça os sete critérios; *(b)* o próprio comparador tem treino parcialmente não declarado,
então nem a pergunta (i) é respondível.
**10. Menor próximo experimento?** Abaixo.

---

## 14. Próximo experimento

**Usar o par LCTSC-S1 × NSCLC-Radiomics para medir o efeito de estilo de anotação, sem treinar
nada.**

É a única célula pública em que **anatomia e instituição ficam fixas** (S1 = MAASTRO = a mesma
instituição do NSCLC-Radiomics, mesmos scanners, mesma família de protocolo) **e só a convenção
de contorno muda**. Rodar o `BASELINE_ESOFAGO_V1` — sem alterá-lo — nos dois conjuntos e medir
a diferença dá o **tamanho do efeito de estilo isolado da anatomia**.

Por que é o menor experimento que reduz mais incerteza: não exige treino, não exige dataset
novo além de um download com licença já verificada, não gasta holdout nenhum, e responde a
pergunta que decide se um modelo especializado faria sentido — **se o efeito de estilo for da
ordem do erro que se quer corrigir, um modelo treinado numa fonte só aprenderia estilo, e o
bloqueio deixa de ser logístico e passa a ser conceitual.**

---

## 15. Reprodutibilidade

```bash
python -m scripts.validation.tier2.representabilidade_esofago --autoteste
python -m scripts.validation.tier2.representabilidade_esofago
python -m scripts.validation.tier2.protocolo_esofago --autoteste
python -m scripts.validation.tier2.protocolo_esofago --mutacao   # 10/10 guardas
python -m scripts.validation.tier2.protocolo_esofago             # imprime a decisão
```
