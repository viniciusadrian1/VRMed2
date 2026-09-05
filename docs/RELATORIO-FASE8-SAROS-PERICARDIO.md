# VRmed — Fase 8: identidade anatômica do rótulo `pericardium`

Data: 2026-09-05 · Objetivo único: descobrir o que o rótulo `pericardium` do TotalSegmentator
representa **anatomicamente**, usando o SAROS como referência. Nada foi treinado.

> Uso educacional e experimental. Não é validação clínica.

**Em uma linha: a leitura "`pericardium` = saco pericárdico" está refutada, e a refutação não
depende da predição. Mas a independência da referência não pôde ser estabelecida, então a
correspondência positiva não pode ser lida como prova de identidade anatômica.**

---

## 1. Objetivo

A Fase 7 validou o **mapping** `Heart (GT LCTSC) → pericardium` no holdout (15/15 em validation
e 15/15 em test). Isso mostrou que `pericardium` representa melhor **o objeto que o LCTSC
contorna** — não o que ele é anatomicamente. Esta fase ataca a segunda pergunta.

A pergunta **não** é "o Dice melhora?". É: **a geometria prevista corresponde ao objeto que o
SAROS chama de pericardium?**

---

## 2. Fonte SAROS

| item | valor |
|---|---|
| DOI do dado | `10.25737/SZ96-ZG60` → *analysis result* no TCIA, não coleção NBIA |
| formato real do GT | **NIfTI** (`body-regions.nii.gz`), não DICOM-SEG |
| escala | 900 TCs, 882 casos, 28 coleções, 20.150 fatias anotadas |
| download | HTTP direto, sem cadastro. ZIP de 91.193.563 bytes, sha256 `b509ff70…37e5` |
| imagens | API NBIA v1 sem token (a mesma rota que `tier2/tcia.py` já usa) |

---

## 3. Licença e proveniência

| item | licença | onde foi lida |
|---|---|---|
| **máscaras SAROS + planilha** | **CC BY 4.0** | campo `License` da tabela de download do TCIA |
| código `UMEssen/saros-dataset` | MIT | arquivo `LICENSE` do repo |
| imagens de origem | CC BY 3.0 (12 casos) · CC BY-NC 3.0 (1) · CC BY 4.0 (1) | API do NBIA, por série |
| imagens de cabeça/pescoço | NIH Controlled Data Access | excluídas do subconjunto |

Licença do **dado** e do **código** são coisas diferentes, e divergem — confirmado, não
presumido. As licenças das imagens foram **lidas da API por série**, nunca digitadas.

**Proveniência do GT:** modelos internos geraram propostas; humanos revisaram e refinaram com
ITK-SNAP. Equipe de controle: *"senior annotators, a data scientist, and a senior radiologist
with 7 years of experience in abdominal imaging"*. É **model-in-the-loop**, não anotação do
zero.

---

## 4. Definição anatômica do GT — e o teto que ela impõe

O paper descreve o dataset como fornecendo *"large-scale annotation of **body regions**,
including the subcutaneous tissue, all muscles and bones, the abdominal and thoracic cavities,
the mediastinum, and the **pericardium**"*.

**`pericardium` no SAROS é um rótulo de REGIÃO CORPORAL**, listado ao lado de cavidades e do
mediastino. Não é descrito como o saco fibroso.

**Isso limita por definição o máximo que esta fase pode concluir.** Mesmo com Dice perfeito, o
resultado seria "corresponde à região pericárdica", nunca "é o saco pericárdico" — porque a
própria referência não é o saco.

Índice numérico do rótulo: **7**, obtido do enum `BodyRegions` do repositório dos autores — o
mesmo que escreve o `label_map` destes arquivos. **Não adivinhado**, e corroborado por
consequência: `brain` (10) aparece em exatamente os 3 casos `wholebody`; `breast_implant` (8)
em 0/14, coerente com `has_breast_implant = FALSE` na planilha.

---

## 5. Seleção de casos

Declarada **antes** de qualquer medida, gravada em `.clinica-dados/saros/subconjunto.json`.

Split `test` — o conjunto de teste pré-definido pelos próprios autores. Elegibilidade:
`split == test` **e** `anatomic_region ∈ {thorax, wholebody}` **e** coleção fora das restritas
→ **70 elegíveis**. Ordem por `sha256("saros-pericardio-fase8|" + id)`, os 15 primeiros.

**14 de 15 adquiridos.** `case_647` abortou com `affine difere (max |delta| = 10); orientação
LPI != LPS`. Diagnóstico medido: os arrays **já estão pareados voxel a voxel** — só o affine
diverge, porque o leitor escreveu direção z = −1 para essa série. Não corrigi: reescrever
geometria depois de ver o dado é exatamente o que o método proíbe.

*(Ressalva de método: `case_647` foi excluído de **todas** as partes, mas a Parte 1 não usa a
imagem — só o GT. Ela poderia ter rodado com 15.)*

---

## 6. Pipeline

`scripts/validation/saros_pericardium.py`. TotalSegmentator 2.18.0, task `trunk_cavities`
(343), `fast=False`. A imagem submetida é a reconstrução reamostrada para 5 mm que reproduz o
`download.py` dos autores — necessário para compartilhar a grade com o GT, e uma ressalva:
isso alinha a entrada com o pré-processamento da distribuição de treino suspeita.

---

## 7. Controles de geometria

Delta de affine **0,0 exato** nos 14 pares imagem↔máscara. Alinhamento verificado antes de
cada medida; divergência aborta com exceção.

### A anotação esparsa, confirmada no dado — e o paper está certo em substância, errado como índice

| | |
|---|---|
| fração anotada | mediana **0,2132** (min 0,2055 · máx 0,2292) |
| passo modal entre fatias anotadas | **5, em 14/14 casos** |
| período 5 **puro** | **apenas 3/14** |

Onze dos catorze casos têm exatamente **uma** emenda irregular (passo 1, 2, 3, 4 ou 6).
**Selecionar fatias por `[::5]` erra em 11 de 14 casos.** A seleção tem de ser sempre pelo
teste `!= 255`.

**Controle positivo da restrição:** um falso positivo maciço colocado **só nas fatias de
ignore** não altera métrica nenhuma (Dice restrito 1,0), enquanto o mesmo objeto derruba o Dice
abaixo de 0,4 sem a restrição. Controle inverso: erro real dentro de fatia anotada leva o Dice
restrito a 0,0.

---

## 8. Métricas

**HD95 e ASSD em 3D são NÃO APLICÁVEIS** com esta anotação. Com 4 de cada 5 fatias em ignore, o
vizinho em z de uma fatia anotada está a 25 mm e não foi anotado — a "superfície 3D" do objeto
anotado é a superfície de lajes, e um HD95 3D mediria as tampas artificiais delas. Só a
distância **no plano**, por fatia anotada, é interpretável: HD95 mediano 3,74 mm (min 1,46 ·
máx 8,x), e ela **não diz nada sobre concordância em z**.

Volume calculado direto da máscara em mL — a regra do VRmed de que volume de malha só vale em
malha watertight não se aplica aqui, porque não há malha.

---

## 9. Resultados agregados

### Parte 1 — a geometria do próprio GT (imune à circularidade)

| | GT SAROS | predição TS | saco sintético de 2 mm (controle) |
|---|---|---|---|
| razão de preenchimento 2D | **1,0000** em 14/14 | **1,0000** em 14/14 | **0,0724** |
| meia-espessura mediana | **14,32 mm** | 14,54 mm | **0,730 mm** |
| P95 da meia-espessura | 39,14 mm | — | 1,460 mm |

**O `pericardium` do GT do SAROS — humano-revisado, sem nenhuma predição envolvida — é um
sólido preenchido.** Recomputei de forma independente em cinco casos que o agente não usou
(`case_000` a `case_004`): preenchimento **1,0000 exato**, meia-espessura 12,25 a 15,03 mm.

O **controle de calibração** é o que dá força a isso: a mesma função classifica um saco fibroso
sintético de 2 mm como **casca**. A medida sabe distinguir; o GT não é uma casca.

### Parte 2 — a comparação (herda a ressalva de independência)

| métrica | mediana | P5 | P95 | min | máx |
|---|---|---|---|---|---|
| Dice (fatias anotadas) | **0,9657** | 0,9226 | 0,9787 | 0,9222 | 0,9829 |
| IoU | 0,9337 | | | | |
| recall | 0,9633 | | | | |
| precision | 0,9719 | | | | |
| erro absoluto de volume | 4,96 mL / 2,26 % | | | | |

### Parte 3 — discriminar entre as hipóteses

| Dice do `pericardium` predito contra… | mediana | máx |
|---|---|---|
| **`pericardium` do SAROS** | **0,9657** | 0,9829 |
| `mediastinum` | 0,0190 | 0,0458 |
| `thoracic_cavity` | 0,0007 | 0,0017 |
| `abdominal_cavity` | 0,0010 | 0,0080 |

Melhor alvo = `pericardium` em **14/14**. Composição da predição em rótulos do SAROS:
`pericardium` **0,9719** (min 0,9483), `mediastinum` 0,0191, resto ≈ 0.

---

## 10. Resultados pareados

O desacordo que resta **tem endereço anatômico**: o extremo **superior**, sobre a raiz dos
grandes vasos. O GT do SAROS mantém os grandes vasos **dentro** do `pericardium`; a predição os
recorta e os chama de `mediastinum`. Fração do GT coberta pelo `mediastinum` predito:
`case_391` 0,1234 · `case_406` 0,1141 · `case_459` 0,1012 (mediana 0,0241).

Relação com o coração: **93,25 %** do `heart` predito cai dentro do GT `pericardium` (min
0,8828), e **29 % a 47 % do volume do GT não é coração**. Compatível com região preenchida, não
com saco.

---

## 11. Casos representativos

Melhor concordância `case_510` (0,9829) · mediana `case_461` · pior `case_459` (0,9222).
Figuras em `.clinica-dados/saros/resultados/`, com CT + GT + predição em fatias anotadas. As
figuras de `case_492` e `case_459` mostram o contorno do GT envolvendo a raiz aórtica e o
tronco pulmonar — exatamente a região do desacordo.

---

## 12. Limitações

**A independência da referência NÃO está estabelecida — e a evidência local pende contra ela.**
Os metadados do modelo estão em disco nesta máquina e dizem:

```
Dataset343_mediastinum_1786subj
labels: {background, abdominal_cavity, thoracic_cavity, pericardium, mediastinum}
reference: "Jakob" · licence: "-" · name: "Segmentation of X" · numTraining: 1786
```

O conjunto de rótulos é **idêntico** aos rótulos torácicos/abdominais de região do SAROS, e os
campos de proveniência são **placeholders**. São 1786 sujeitos contra os 900 do SAROS — então
não é *só* SAROS, mas o SAROS pode estar contido. **Não é possível confirmar nem descartar.**

Consequência: **um Dice de 0,9657 é compatível com memorização.** Toda a Parte 2 e a Parte 3
herdam essa ressalva.

*(Erro de método corrigido aqui: a fase declarou essa proveniência como "não investigada"
enquanto o arquivo estava em disco a segundos de leitura. Foi lido e está acima.)*

**"Sólido" é sobredeterminado.** A anotação foi feita em fatias de 5 mm. Nessa espessura a
linha pericárdica sofre volume parcial e não seria traçável como anel fechado mesmo que alguém
quisesse. Intenção de rotular região **e** inviabilidade técnica produzem o mesmo resultado, e
esta fase não os separa.

**A sonda padrão de memorização foi fechada pela própria seleção.** Declarar `split == test`
impede comparar desempenho em casos dos 5 folds contra casos retidos — um degrau ali seria
evidência. A declaração prévia é boa prática; o custo que ela impôs à pergunta central não foi
antecipado.

**A independência efetiva entre casos é menor que 14:** eles vêm de apenas 5 coleções do TCIA
(ACRIN-NSCLC-FDG-PET com 5, LIDC-IDRI com 4).

**"Fator 20× na espessura e 14× na razão" não são duas confirmações** — são duas projeções do
mesmo fato geométrico (máscara sem buraco interno). Numa máscara preenchida a EDT interna é
função determinística do raio.

**Nenhum comparador externo foi usado**, embora exista um óbvio: o paper do SAROS reporta o
Dice do modelo dos próprios autores no mesmo split `test`. Seria o calibrador natural para
decidir se 0,9657 é alto demais.

---

## 13. Interpretação anatômica

| hipótese | veredito | evidência |
|---|---|---|
| **(a) saco / pericárdio fibroso** | **REFUTADA** | preenchimento 1,0000 dos **dois** lados contra 0,0724 do saco sintético; meia-espessura 14,3 mm contra 0,73 mm. **Imune à circularidade** |
| **(b) região pericárdica preenchida** | **compatível** | preenchimento 1,0000; contém 93 % do coração predito e é 29–47 % maior que ele |
| **(c) coração + pericárdio** | **não separável de (b)** | o excedente é envelope maciço, não borda fina. Nenhuma medida desta fase separa os dois |
| **(d) outra cavidade torácica** | **refutada** | Dice 0,0190 contra `mediastinum` e 0,0007 contra `thoracic_cavity`; melhor alvo em 14/14 |
| **(e) objeto não identificado** | **refutada** | composição 0,9719 de um único rótulo |

*(Ressalva de classe: (d) e (e) saem de tabelas predição × GT, que herdam a ressalva de
independência. Sob contaminação, elas mostram que o modelo reproduz o rótulo que talvez tenha
aprendido — não que o objeto seja aquilo. Foram rebaixadas de "demonstrado" para "refutada com
ressalva".)*

*(A escolha de (b) sobre (c) usou parcimônia, que é critério estético e não medida. A
refutação apontou uma medida GT-only que separaria as duas — a composição do anel de 1 voxel
imediatamente fora do GT — e ela não foi feita. Fica como pendência.)*

---

## 14. Impacto no VRmed

**Nenhuma mudança de pipeline, modelo ou mapping.** O que muda é a **ontologia**: a linha que
dizia "identidade anatômica não determinada" passa a dizer o que está refutado e o que
permanece aberto.

---

## 15. Decisão final

# **CATEGORIA B — IDENTIDADE ANATÔMICA PARCIALMENTE APOIADA**

**O `pericardium` do TotalSegmentator corresponde ao `pericardium` do SAROS?**
**Geometricamente sim, nos casos medidos** — Dice 0,9657, composição 0,9719, melhor alvo em
14/14, forma idêntica. **Mas com independência indeterminada**, então isso pode medir
memorização.

**Em que grau?** Alto na sobreposição e **idêntico na forma**: os dois são sólidos preenchidos
com meia-espessura de ~14,3 e ~14,5 mm.

**Quais diferenças permanecem?** Uma, com endereço: o extremo superior sobre a raiz dos grandes
vasos. O SAROS os mantém dentro; a predição os chama de `mediastinum`.

**O mapping `Heart (LCTSC) → pericardium` continua válido?**
**Sim, e esta fase não o toca.** Ele foi validado no holdout contra o objeto que o LCTSC
contorna, e essa validação não dependia da identidade anatômica.

**A ontologia precisa ser alterada?**
**Sim, num ponto e num só:** onde ela dizia que a identidade anatômica é "não determinada",
passa a registrar que **"saco pericárdico" está refutado** — por medida que não envolve
predição — e que o rótulo é **compatível com região pericárdica preenchida**, com a
independência da referência ainda indeterminada.

**Existe razão para iniciar treinamento cardíaco?**
**Não.** Nada nesta fase sugere isso. O objeto que o GT do LCTSC contorna já é produzido pelo
modelo; o problema era de rótulo e foi resolvido sem treino.

**Isso muda o plano do esôfago?**
**Não.** Nenhuma consequência metodológica do esôfago depende do que `pericardium` é.

---

## 16. Reprodutibilidade

```bash
python -m scripts.validation.saros_pericardium --autoteste
python -m scripts.validation.saros_pericardium
```

Autoteste com controles positivos que **falham** para: máscara desalinhada, affine
incompatível, caso sem GT, máscara vazia, spacing ausente, e comparação entre arquivos de casos
**diferentes**. Mais o controle da restrição às fatias anotadas (§7).

Subconjunto declarado em `.clinica-dados/saros/subconjunto.json` **antes** do manifesto.
Saídas em `.clinica-dados/saros/`.
