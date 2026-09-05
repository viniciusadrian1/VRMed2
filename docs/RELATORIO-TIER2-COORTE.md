# VRmed — Tier 2 em coorte

Data: 2026-09-04 · Escopo: **acurácia da segmentação contra ground truth independente**.

> **Natureza deste documento.** Avaliação de **acurácia de segmentação** para uso
> educacional e experimental. Não é validação clínica, não é avaliação de acurácia
> diagnóstica, e nenhum número abaixo autoriza uso assistencial.

Na decomposição de erro — **A** segmentação · **B** reconstrução · **C** simplificação ·
**D** compressão — este documento quantifica **apenas o bloco A**. Os blocos **nunca são
somados**. Nada aqui diz coisa alguma sobre reconstrução de malha; isso está em
[`RELATORIO-VALIDACAO-RECONSTRUCAO.md`](RELATORIO-VALIDACAO-RECONSTRUCAO.md).

---

## 1. Dataset e procedência

**LCTSC** — Lung CT Segmentation Challenge 2017, no TCIA.
DOI `10.7937/K9/TCIA.2017.3r3fvz08`.

| item | valor |
|---|---|
| Licença | **Creative Commons Attribution 3.0 Unported** · `http://creativecommons.org/licenses/by/3.0/` |
| Como a licença foi obtida | **Lida** dos campos `LicenseName`/`LicenseURI` do registro de série da API do TCIA, em cada uma das 120 séries — não digitada a mão |
| Ground truth | RTSTRUCT de contorno de radioterapia, anotação **humana**, 3 instituições, 2017 |
| Modalidade | CT DICOM + RTSTRUCT DICOM |
| Download | REST API pública, sem cadastro e sem token |

**Independência do ground truth — a condição que faz um Tier 2 significar alguma coisa.**
O task `total` do TotalSegmentator v2 foi treinado **exclusivamente em TCs clínicas de
rotina do University Hospital Basel** (1082 treino / 57 validação / 65 teste, todos do
mesmo pool). Nenhum dataset público de desafio entra nesse treino; os únicos citados são de
sub-tasks que o VRmed não usa (`lung_nodules`, `teeth`). O LCTSC **não está no treino**, é
cinco anos anterior ao modelo, e sua anotação é humana.

**Descartado por contaminação.** Zenodo `10.5281/zenodo.7975081` anota exatamente heart,
trachea, aorta e esophagus nas coleções NLST/NSCLC-Radiomics, sob CC BY 4.0 — mas o "ground
truth" dele é **saída de nnU-Net**. Era o candidato mais conveniente do conjunto e o mais
inválido.

---

## 2. Coorte

**60 casos, 100 % da coleção. Nenhum caso excluído.**

| instituição | n | partição original | spacing em Z |
|---|---|---|---|
| S1 | 20 | 12 Train + 8 Test | **3,0 mm em 20/20** |
| S2 | 20 | 12 Train + 8 Test | **2,5 mm em 20/20** |
| S3 | 20 | 12 Train + 8 Test | **misto**: 1,25 (1) · 2,0 (7) · 2,5 (5) · 3,0 (7) |

O código de instituição vem do próprio identificador (`LCTSC-Train-S1-001` → `S1`) — não
existe campo de instituição na API. Registrado no manifesto como **derivado**, não como
metadado lido.

**ROIs: 60/60 casos com exatamente as mesmas cinco** — `Esophagus`, `Heart`, `Lung_L`,
`Lung_R`, `SpinalCord`. Zero divergência de nome, zero ROI sem mapeamento. Os nomes foram
**lidos do RTSTRUCT** antes de qualquer processamento, não presumidos da literatura.

**Nenhuma exclusão seletiva.** `LCTSC-Test-S1-101` é o único RTSTRUCT escrito por
Plastimatch (os outros 59 são MIM Software 6.6.7) e passou por um round-trip extra de
geometria em 2019. Ele **entra** na coorte: excluí-lo seria escolher casos, e o manifesto
grava fabricante e versão por caso, então o outlier fica sinalizado pelo dado e não por uma
regra escrita à mão.

---

## 3. Pipeline

Idêntico para os 60 casos, sem exceção:

```
TCIA DICOM → ingestão → imagem NIfTI → RTSTRUCT → GT → TotalSegmentator
           → predição → verificação geométrica → métricas
```

| componente | versão |
|---|---|
| Python | 3.13.11 (`.venv-pipeline`) |
| TotalSegmentator | 2.18.0, task `total`, GPU |
| PyTorch | 2.6.0+cu124 |
| dcmrtstruct2nii | 5 (MIT) |
| pydicom | 3.0.2 |
| nibabel · SimpleITK · numpy · scipy · scikit-image | 5.4.2 · 2.5.6 · 2.5.2 · 1.18.1 · 0.26.0 |
| código | hash sha256 do arquivo que produziu a predição, gravado por linha |

**Remendo declarado.** `dcmrtstruct2nii` 5 chama `pydicom.read_file`, API removida no
pydicom 3. Rebaixar o pydicom mudaria o ambiente do pipeline de produção (pinado em 3.0.2),
então há um shim local que restaura o alias antes da chamada. Nenhum arquivo do pacote
instalado foi editado e nenhuma versão pinada foi trocada. `dcmrtstruct2nii` entra em
`requirements.txt` como linha comentada, marcada como **só para validação Tier 2**.

**Resultado do processamento: 60 feitos, 0 falhos, 0 pulados.**

---

## 4. Controle geométrico

A grade é compartilhada **por construção**: o TotalSegmentator roda sobre exatamente o
`gt/image.nii.gz` que o `dcmrtstruct2nii` gravou, não sobre uma conversão paralela. É a
diferença entre *garantir* alinhamento e *verificar* alinhamento.

Verificado assim mesmo, antes de **cada** comparação: `delta_affine_max = 0,0` **exato** —
igualdade bit a bit, não "dentro da tolerância". Linha desalinhada é **abortada com
exceção**, nunca vira "Dice baixo".

**A pegadinha que o controle pegou.** Nestas séries a ordem espacial das fatias **diverge
tanto do nome de arquivo quanto do `InstanceNumber`**: no caso de referência, a primeira
fatia espacial é `00000084.dcm` com `InstanceNumber` 140 e a última é `00000104.dcm` com
`InstanceNumber` 1. Ordenar por qualquer um dos dois **inverteria a série inteira**. A
ordenação usa a projeção de `ImagePositionPatient` na normal do plano (produto vetorial das
duas direções de `ImageOrientationPatient`) — critério espacial.

`SpacingBetweenSlices` está **ausente** na tag; o espaçamento em Z foi **medido** das
posições, uniforme dentro de 1e-3. O GT é lido com limiar `> 0,5`: o `dcmrtstruct2nii` grava
foreground como **255**, e ler `== 1` daria máscara vazia e um Dice 0,0 que pareceria erro
do modelo.

---

## 5. Definição das métricas

Todas as distâncias em **milímetros físicos**, com `spacing` de `header.get_zooms()` — nunca
`np.diag(affine)`, que mente em série oblíqua.

### 5.1 As duas avaliações, sempre as duas, para todas as estruturas

| | o que compara | uso |
|---|---|---|
| **A — suporte do GT** | só onde o GT existe em Z | separa "contorno diferente" de "extensão diferente" |
| **B — campo completo** | toda a extensão da predição | o que o modelo de fato produz |

**A é circular por construção** e isso está declarado no código: a janela vem de
`z_gt.min()/max()` **deste caso**, não de referência anatômica — o pipeline não localiza
cricoide nem artéria pulmonar. Ela define como comparável exatamente onde o GT existe e
**não detecta** o caso em que o contornador divergiu do atlas.

Antes, A só era calculada para `Esophagus` e `Heart`. A aplicação seletiva era o problema:
escolher onde recortar depois de ver o resultado é o oposto de método. Agora as duas saem
para todas as cinco estruturas — e o resultado justifica: nos pulmões a diferença A→B é de
0,0007 de Dice, na medula é de **0,061**.

### 5.2 NSD: o limiar fixo em mm tem um eixo estruturalmente cego

Com voxel de 3,0 mm em Z, **nenhum** deslocamento em Z cabe sob os limiares de 1 mm ou 2 mm
— o menor deslocamento possível nesse eixo já vale 3,0 mm. `nsd_1mm` e `nsd_2mm` creditam
apenas concordância **no plano**.

Adicionado `nsd_1vox` / `nsd_2vox` com **τ = k × max(spacing)**: a menor distância que a
grade consegue expressar em **todos** os eixos. `k = 1` e `k = 2` por simetria com os
limiares fixos, **não** por produzirem número melhor — o critério foi fixado no código
**antes** de a coorte rodar. Em grade isotrópica de 1 mm as duas famílias coincidem.

O efeito é grande e sistemático (mediana da coorte, variante B):

| estrutura | `nsd_1mm` | `nsd_1vox` | diferença |
|---|---|---|---|
| Lung_R | 0,6667 | **0,9235** | +0,257 |
| Lung_L | 0,6628 | **0,8949** | +0,232 |
| Esophagus | 0,6723 | **0,8786** | +0,206 |
| Heart | 0,1974 | **0,4069** | +0,210 |
| SpinalCord | 0,7272 | **0,8854** | +0,158 |

**Ressalva do τ ancorado:** como o spacing varia na coorte (§2), τ varia por caso — de 1,25
a 3,0 mm. `nsd_1vox` responde "concordância dentro de um voxel **desta** grade", que é uma
distância física diferente em cada caso. É o preço de não ter eixo cego; está declarado, não
escondido.

### 5.3 Decomposição do erro de volume

O erro líquido **cancela e engana**. Publicados sempre os quatro termos: FP fora do suporte,
FP dentro, FN dentro, líquido e **absoluto**.

---

## 6. Resultados por estrutura

Mediana da coorte, **n = 60** em todas as células. IC 95 % da mediana por bootstrap
percentil (2000 reamostragens, semente fixa).

### Variante B — campo completo

| estrutura | Dice | IC 95 % | HD95 (mm) | ASSD (mm) | erro vol. | recall | precision | `nsd_1vox` |
|---|---|---|---|---|---|---|---|---|
| **Lung_R** | **0,9706** | [0,9664 – 0,9755] | 5,91 | 1,101 | +0,35 % | 0,9753 | 0,9678 | 0,9235 |
| **Lung_L** | **0,9600** | [0,9537 – 0,9708] | 5,91 | 1,178 | +1,65 % | 0,9766 | 0,9627 | 0,8949 |
| **SpinalCord** | **0,8227** | [0,7853 – 0,8470] | 43,03 | 3,450 | +5,75 % | 0,8479 | 0,8010 | 0,8854 |
| **Esophagus** | **0,8003** | [0,7753 – 0,8089] | 5,39 | 1,273 | −0,36 % | 0,7851 | 0,8098 | 0,8786 |
| **Heart** | **0,7552** | [0,7447 – 0,7669] | 30,00 | 6,663 | −23,14 % | 0,6652 | 0,8727 | 0,4069 |

### Variante A — suporte do GT

| estrutura | Dice | IC 95 % | HD95 (mm) | erro vol. | recall | precision |
|---|---|---|---|---|---|---|
| Lung_R | 0,9709 | [0,9664 – 0,9757] | 5,91 | +0,34 % | 0,9753 | 0,9681 |
| Lung_L | 0,9607 | [0,9539 – 0,9708] | 5,91 | +1,56 % | 0,9766 | 0,9632 |
| SpinalCord | 0,8835 | [0,8762 – 0,8889] | **2,18** | −10,49 % | 0,8479 | 0,9353 |
| Esophagus | 0,8130 | [0,7940 – 0,8239] | 4,45 | −3,79 % | 0,7851 | 0,8436 |
| Heart | 0,7924 | [0,7848 – 0,8076] | 22,85 | −31,89 % | 0,6652 | **0,9818** |

### Estruturas sem cobertura

| estrutura | status |
|---|---|
| **aorta** | **não medido: o dataset não anota esta estrutura** |
| **trachea** | **não medido: o dataset não anota esta estrutura** |

Não estimadas por nenhuma outra via. Ver §12 para o encaminhamento.

### 6.1 Decomposição do erro de volume (mediana, mL, variante B)

| estrutura | FP fora | FP dentro | FN dentro | **erro absoluto** | vol. GT | absoluto / GT |
|---|---|---|---|---|---|---|
| Heart | 63,04 | 8,22 | 249,58 | **327,12** | 728,26 | **45 %** |
| Lung_R | 0,56 | 55,17 | 51,67 | **104,90** | 1869,74 | 5,6 % |
| Lung_L | 0,44 | 55,82 | 40,08 | **102,46** | 1533,47 | 6,7 % |
| SpinalCord | 11,42 | 3,52 | 9,19 | **24,97** | 61,84 | **40 %** |
| Esophagus | 0,97 | 6,19 | 8,05 | **16,10** | 40,64 | **40 %** |

**É aqui que o erro líquido se desmascara.** O esôfago tem erro líquido de −0,36 % e
discordância absoluta de **40 % do volume do GT**. A medula tem +5,75 % líquido e **40 %**
absoluto. Ler o erro percentual de volume como medida de concordância é ler o resultado do
cancelamento, não a concordância.

### 6.2 O coração: divergência de definição, medida

`Heart` do LCTSC segue o atlas RTOG 1106 e **inclui o saco pericárdico e a gordura
pericárdica**, com corte superior no nível inferior da artéria pulmonar. O `heart` do
TotalSegmentator v2 não inclui pericárdio — a classe `pericardium` nem existe no task
`total`. **O GT é maior por construção.**

A assinatura numérica confirma: na variante A, **precision 0,9818 e recall 0,6652**. Ou
seja, 98 % da predição está dentro do GT e apenas 67 % do GT é coberto. Isso é exatamente o
padrão de "o GT é um superconjunto", não de erro de localização. O Dice 0,7552 **não deve
ser lido como acurácia do coração**.

---

## 7. Distribuição entre casos

### 7.1 Dispersão (Dice, variante B)

| estrutura | P5 | P25 | mediana | P75 | P95 | amplitude P5–P95 |
|---|---|---|---|---|---|---|
| Lung_R | 0,917 | 0,947 | 0,971 | 0,981 | 0,986 | 0,069 |
| Lung_L | 0,874 | 0,946 | 0,960 | 0,977 | 0,985 | 0,111 |
| Esophagus | 0,621 | 0,758 | 0,800 | 0,821 | 0,855 | **0,234** |
| Heart | 0,693 | 0,733 | 0,755 | 0,790 | 0,827 | 0,134 |
| SpinalCord | 0,607 | 0,756 | 0,823 | 0,863 | 0,888 | **0,281** |

Medula e esôfago são as estruturas **instáveis** — quase 0,3 de amplitude entre o P5 e o
P95. Os pulmões são estáveis.

### 7.2 Efeito de instituição — e o confundimento que ele esconde

Dice mediano, variante B, n = 20 por instituição:

| estrutura | S1 | S2 | S3 | amplitude |
|---|---|---|---|---|
| **SpinalCord** | 0,7851 | 0,8621 | 0,7302 | **0,1319** |
| Esophagus | 0,8019 | 0,8123 | 0,7616 | 0,0507 |
| Lung_R | 0,9817 | 0,9451 | 0,9729 | 0,0367 |
| Lung_L | 0,9784 | 0,9508 | 0,9659 | 0,0276 |
| **Heart** | 0,7570 | 0,7481 | 0,7621 | **0,0140** |

A medula varia mais **entre instituições** (0,13) do que várias estruturas variam entre si.
O coração é o **mais consistente** — coerente com o viés do pericárdio ser uma constante de
definição e não uma variação de quem contornou.

**O confundimento.** S1 é 100 % spacing 3,0 mm e S2 é 100 % spacing 2,5 mm — para essas duas
instituições, **instituição e espessura de fatia são a mesma variável**. Um efeito atribuído
a convenção de contorno poderia ser efeito de resolução.

**Teste de desacoplamento.** S3 é a única instituição com spacing misto, o que permite
separar as duas coisas dentro dela:

| SpinalCord, dentro de S3 | 1,25 mm (n=1) | 2,0 mm (n=7) | 2,5 mm (n=5) | 3,0 mm (n=7) |
|---|---|---|---|---|
| Dice mediano | 0,8897 | 0,7236 | 0,7018 | 0,7368 |

Entre 2,0 e 3,0 mm o Dice é **plano** (0,70–0,74) — o spacing não explica a variação. E a
comparação decisiva: **no mesmo spacing de 2,5 mm, S2 dá 0,8565 (n=25) e S3 dá 0,7018
(n=5)**. Uma diferença de 0,15 com espessura de fatia idêntica.

**Conclusão do teste:** o efeito de instituição na medula **não é explicado por espessura de
fatia**. É consistente com diferença de convenção de contorno — que é exatamente o que os
autores do LCTSC declaram ter mantido de propósito. Não é prova: n = 5 no braço S3 de 2,5 mm,
e população não foi controlada.

---

## 8. Melhores e piores casos

Ranking **gerado automaticamente por ordenação**, nunca por escolha manual. Cinco extremos
por métrica; abaixo os três piores de cada.

| estrutura | piores por Dice | piores por HD95 (mm) |
|---|---|---|
| Heart | Test-S3-204 (0,685) · Train-S3-002 (0,692) · Test-S2-102 (0,692) | Train-S3-006 (41,96) · Train-S1-009 (40,96) · Test-S3-102 (38,67) |
| SpinalCord | Test-S3-103 (0,572) · Test-S3-203 (0,579) · Test-S3-102 (0,603) | **Train-S3-006 (157,37)** · Test-S3-201 (114,72) · Test-S3-103 (114,01) |
| Esophagus | Train-S3-006 (0,485) · Train-S1-012 (0,582) · Test-S3-204 (0,604) | Test-S1-204 (58,89) · Train-S1-012 (38,62) · Train-S3-006 (35,16) |
| Lung_R | Test-S2-203 (0,827) · Test-S2-104 (0,866) · Train-S2-006 (0,886) | Train-S2-006 (19,91) · Test-S2-104 (19,35) · Test-S2-203 (17,92) |

**Caso reincidente: `LCTSC-Train-S3-006` aparece entre os três piores em quatro rankings
distintos.** É o candidato óbvio para inspeção — e a inspeção é §9, não especulação aqui.

Os três piores do `Lung_R` são todos **S2**, e os três piores da `SpinalCord` são todos
**S3**. Consistente com §7.2.

---

## 9. Diagnóstico espacial de erro

A regra do instrumento é **localizar → medir → hipótese**, nunca hipótese → procurar
evidência. Ela existe porque foi violada antes nesta base: o relatório anterior atribuiu o
HD95 dos pulmões a "discordância no hilo" **sem nunca localizar o falso positivo**.

**Quando alguém localizou, a explicação caiu.** Medido no caso de referência: 55–60 % do FP
é casca de 1 voxel encostada na superfície do GT, e o **maior bloco de FP atravessa 49
fatias / 147 mm — 64 % da extensão craniocaudal do GT**. Uma estrutura que cruza quase todo
o pulmão não é uma região hilar. A assinatura é **deslocamento sistemático de fronteira**,
não disputa de definição localizada. Os números estavam certos; a explicação estava errada.

Consequência de método, já aplicada: `scripts/validation/tier2/mapa_erro.py` classifica o
erro por **regra declarada no código** (casca fina espalhada / bloco localizado / diferença
de extensão nas pontas), com limiares fixados antes, e sua seção de hipóteses sai vazia por
decisão. Uma varredura por `hilo|hilar|pericardi|cricoi|bronqui` nos artefatos de saída não
retorna nenhuma linha.

### 9.1 Medido nos casos que o ranking apontou

Rodado em três casos escolhidos **pelo ranking automático**, não à mão: o reincidente
`Train-S3-006`, o segundo reincidente `Test-S3-203` e um caso de referência `Train-S1-003`.
A classe é calculada por regra declarada, não escrita.

| caso | estrutura | tipo | vol (mL) | frac. camada 1 voxel | espessura P95 (mm) | classe calculada |
|---|---|---|---|---|---|---|
| Train-S3-006 | SpinalCord | FP | 40,82 | 0,171 | **159,65** | c) extensão nas pontas |
| Train-S3-006 | SpinalCord | FN | 4,91 | **1,000** | 2,34 | a) casca fina espalhada |
| Test-S3-203 | SpinalCord | FP | 45,21 | 0,102 | **101,53** | c) extensão nas pontas |
| Test-S3-203 | SpinalCord | FN | 6,21 | 0,938 | 2,18 | a) casca fina espalhada |
| Train-S1-003 | SpinalCord | FP | 13,34 | 0,145 | **79,36** | c) extensão nas pontas |
| Train-S1-003 | SpinalCord | FN | 16,94 | 0,956 | 2,76 | a) casca fina espalhada |
| Train-S3-006 | Heart | FP | 90,44 | 0,198 | 51,00 | c) extensão nas pontas |
| Train-S3-006 | Heart | FN | 266,60 | 0,311 | 32,20 | d) misto |
| Train-S1-003 | Heart | FN | 183,98 | 0,291 | 26,70 | d) misto |
| Train-S3-006 | Esophagus | FP | **42,83** | 0,171 | **34,96** | c) extensão nas pontas |
| Test-S3-203 | Esophagus | FP | 4,04 | 0,924 | 2,50 | a) casca fina espalhada |
| Train-S1-003 | Esophagus | FP | 6,58 | 0,968 | 2,93 | a) casca fina espalhada |

**O erro da medula tem duas componentes distintas, e elas não são o mesmo fenômeno.**
Consistente nos três casos: o **FP é extensão** — 13 a 45 mL de predição com espessura P95 de
79 a 160 mm, ou seja, a predição continua onde o contorno acabou; e o **FN é casca fina** —
5 a 17 mL com 94 a 100 % em camada de 1 voxel e espessura P95 de apenas 2,2 a 2,8 mm, ou
seja, a predição é ligeiramente mais estreita que o GT em quase toda fatia. É isso que
produz a diferença A→B de HD95 de **2,18 mm para 43,03 mm**: a variante A remove o FP de
extensão e o que sobra é a casca fina.

**O FN do coração é um bloco só**, não erro espalhado: `frac_maior_componente` de 0,974 a
0,993 nos três casos. Compatível com o pericárdio ser um envelope contíguo — o que a §6.2
já mostra pela via numérica (precision 0,98 com recall 0,67). Localizado antes de explicado.

**O caso reincidente tem uma assinatura própria.** No `Train-S3-006` o FP do esôfago muda de
classe: 42,83 mL com espessura P95 de 34,96 mm, contra 4 a 7 mL e P95 de 2,5 a 2,9 mm nos
outros dois. Não é fronteira deslocada, é extensão — e é o que explica o Dice de 0,485,
o pior da coorte para essa estrutura. **Por que** a predição se estende ali não foi medido e
não é nomeado aqui.

**Limite honesto do instrumento:** `frac_camada_1vox` não tem valor único numa grade
anisotrópica de 0,977 × 0,977 × 3,0 mm. No mesmo FP do `Lung_R` vale **0,71** pelo critério
de camada *chessboard* e **0,29** pelo critério de ≤ 0,977 mm — os dois lados do limiar de
0,50 que decide a classe. A classificação de `Lung_R` e `Lung_L` como "casca fina espalhada"
é **consequência da escala escolhida**, e a coluna vizinha do mesmo módulo reporta espessura
P95 de 12,0 mm. Marcado como inconclusivo, não como resultado.

---

## 10. Limitações

**Do ground truth.** Os autores do LCTSC são explícitos: *"The editing specifically did not
remove inter-institutional variability in the original contours."* Não há métrica de
concordância interobservador publicada — portanto **não existe teto de referência**: não se
sabe qual Dice um segundo anotador tiraria contra o mesmo GT, e "Dice 0,80" não tem régua.

**Contorno de radioterapia não é contorno de anatomia.** É desenhado para dosimetria, tende
a ser generoso e suavizado nas bordas. A coorte é de casos de tratamento torácico, não
população geral.

**Definição divergente em três das cinco estruturas** — pericárdio no coração, janela de
contorno do esôfago, união de lobos nos pulmões. A união **apaga as fissuras**: o Dice mede
a envoltória pulmonar, **não a lobação**. Não há ground truth de lobo neste dataset.

**Da grade.** Distâncias quantizadas: em Z o voxel é de 1,25 a 3,0 mm conforme o caso.
`nsd_1mm` e `nsd_2mm` são estruturalmente cegos ao eixo Z na maior parte da coorte (§5.2).

**Da amostra.** n = 60, uma coleção, três instituições. Instituição e spacing confundidos em
S1 e S2; o desacoplamento de §7.2 vale só dentro de S3, com n pequeno.

**Do escopo.** Nada aqui mede reconstrução (B), simplificação (C) ou compressão (D).

---

## 11. O que está demonstrado

**Os pulmões concordam bem com o GT, de forma estável.** Dice 0,971 e 0,960, IC estreito,
recall > 0,975, P5 acima de 0,87. É o resultado mais sólido da coorte — e mede a
**envoltória pulmonar**, não a lobação.

**O erro líquido de volume esconde a discordância real.** Esôfago: −0,36 % líquido contra
**40 % de erro absoluto** sobre o volume do GT. Medula: +5,75 % contra **40 %**. Demonstrado
em 60 casos, com os quatro termos publicados.

**A divergência de definição do coração é medida, não suposta.** Precision 0,9818 com recall
0,6652 na variante A é a assinatura de "o GT é um superconjunto", e é estável nas três
instituições (amplitude 0,014 — a menor da coorte).

**A avaliação dupla A/B não é recorte conveniente.** Ela move o número só onde há divergência
real de extensão: 0,0007 de Dice nos pulmões contra 0,061 na medula, e HD95 de 2,18 mm para
43,03 mm na mesma estrutura.

**O efeito de instituição na medula não é efeito de espessura de fatia.** No mesmo spacing de
2,5 mm, S2 dá 0,8565 e S3 dá 0,7018.

**O NSD com limiar fixo em mm subestima a concordância nesta grade** em 0,16 a 0,26 de forma
sistemática nas cinco estruturas.

---

## 12. O que continua hipótese

**A causa do efeito de instituição.** O desacoplamento mostra que não é spacing; **não
mostra o que é**. Convenção de contorno é a hipótese, com n = 5 no braço decisivo.

**A caracterização espacial do erro dos pulmões.** Sabe-se que é deslocamento de fronteira
espalhado e não bloco localizado; a **causa** não foi medida e não deve ser nomeada.

**A classificação do mapa de erro** depende de limiares declarados sobre os quais não houve
análise de sensibilidade, e `frac_camada_1vox` é ambígua em grade anisotrópica (§9).

**Aorta e traqueia continuam sem Tier 2 nenhum.** O SegTHOR cobriria exatamente esse buraco
(4/4 com o mediastino do VRmed), mas está **pendente de aquisição**: a licença oficial é um
Data Use Agreement do Centre Henri Becquerel que **proíbe redistribuição pública**, o acesso
exige termo assinado por e-mail e aprovação humana, e o CodaLab legado está descontinuado. O
mirror do Zenodo é **redistribuição não autorizada** e sua declaração CC-BY-4.0 é inválida na
origem — **não foi usado**. Nenhum dataset público único cobre aorta *e* traqueia com os
critérios do LCTSC.

---

## 13. Critério de conclusão (Parte 20)

### A — Segmentação

**Sim, para as cinco estruturas anotadas — com a ressalva de definição junto de cada número.**
n = 60, três instituições, IC estreito. Os pulmões estão caracterizados com folga; medula e
esôfago têm dispersão alta (amplitude P5–P95 de 0,28 e 0,23) e a caracterização é da
**distribuição**, não de um valor. O coração **não** está caracterizado como acurácia: o
número mede uma divergência de definição somada ao erro do modelo, e este desenho não
consegue separar os dois.

**Não, para aorta e traqueia.** Zero cobertura. Não estimadas.

### B — Reconstrução

**Sim, `marching_cubes + σ=0 + Taubin 4` continua defensável, e a coorte reforça.**
A cadeia A→B medida em 3 casos × 5 estruturas deu residual `C − A` de **+0,0000 em 15/15**:
na resolução da grade da máscara a reconstrução **não acrescenta erro mensurável** sobre a
segmentação. O erro de B é inteiramente sub-voxel (−0,39 % de volume numa esfera de 20 mm,
medido pelo único caminho não-degenerado). Com Dice de A entre 0,64 e 0,98 nos mesmos casos,
**o gargalo é A com folga de ordens de grandeza**.

### C — Simplificação

Regras que o dado sustenta, agora com o instrumento corrigido (o Hausdorff publicado antes
estava contaminado por um piso de ruído de 0,15–0,31 mm; ver
`RELATORIO-VALIDACAO-RECONSTRUCAO.md`):

- decimar **calibre fino por percentual é perigoso**: 10 % dos triângulos custa −29,08 % de
  volume no tubo de 2 mm, contra ≤ 0,32 % nas estruturas grossas;
- o critério de aceitação para fino é **volume**, não distância;
- **piso fixo de 3000 triângulos não deve ser usado**: é no-op no fino e destrói o grosso
  (`heart` a 13,47 mm de Hausdorff, 3 componentes → 1);
- **verificação de componentes antes/depois é obrigatória** — fusão é dano silencioso que
  nenhuma métrica de volume ou distância detecta;
- **`volume_ml` não deve ser publicado a partir de derivado**: a decimação abre a malha a
  partir de 30–50 %.

### D — Compressão

**Deixou de estar sem instrumento.** DracoPy 2.0.0 decodifica Draco no Windows/Python 3.13
sem compilar; o `trimesh` **não** decodifica e produz número falso (posições zeradas com
contagem correta).

Medido no par real do repositório (11 malhas):

| grandeza | resultado |
|---|---|
| deslocamento máximo de vértice | **0,0014 a 0,0168 mm** — duas ordens de grandeza abaixo do voxel |
| Hausdorff de superfície | 0,0012 a 0,0143 mm |
| erro de área | −0,00089 % a +0,00321 % |
| erro de volume | **inválido em 6/11** (malha não fechada); 0,0 a −0,002 % nas 5 fechadas |
| compressão | 6,351× no arquivo (−84,26 %); 5,45× a 7,92× por malha |

**Geometricamente o Draco é desprezível. Topologicamente não é.** Ele descarta as faces de
área zero deixadas pelo marching cubes e, onde elas seguravam a conectividade, a malha abre
ou fragmenta — `lung_left` foi de 1 para 3 componentes com +6 arestas de borda, com
casamento exato de contagens (−2 faces degeneradas = −2 faces). `inferior_vena_cava` perdeu
o watertight.

---

## 14. Reprodutibilidade

```bash
python -m scripts.validation.tier2.coorte enumerar    # manifest.json + cases.csv
python -m scripts.validation.tier2.coorte processar   # 60 casos, retomável
python -m scripts.validation.tier2.coorte agregar     # distribuição + rankings
python -m scripts.validation.tier2.mapa_erro --caso <ID>
python -m scripts.validation.tier2.cadeia_ab --casos <ID> ...
python -m scripts.validation.compressao               # bloco D
```

Saídas em `.clinica-dados/tier2/lctsc/` (fora do Git, por conter dado derivado de exame).
`METRICAS`, `PERCENTIS` e `RANKINGS` estão fixados no topo de `coorte.py`, **antes** de a
coorte rodar — escolher métrica ou percentil depois de ver o resultado é p-hacking. O IC usa
semente fixa e é reproduzível.

**A coorte é avaliação, não desenvolvimento.** Nenhum limiar, post-processing, parâmetro do
TotalSegmentator ou regra de recorte foi ajustado em função do que ela mostrou. Hipótese de
melhoria vira experimento separado, com split próprio.
