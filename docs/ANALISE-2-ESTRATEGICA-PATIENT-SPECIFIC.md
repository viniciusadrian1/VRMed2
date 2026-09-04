# VRmed — Análise técnica e estratégica II: rumo ao modelo 3D patient-specific

> **Read-only.** Nenhum código foi alterado. Esta é a segunda análise, prospectiva, construída
> sobre a auditoria de código anterior (`docs/AUDITORIA-TECNICA-VISAO-MEDICA.md`). Pesquisa de
> tecnologias feita com fontes; recomendações ancoradas no código real do VRmed.
> Data: 2026-09-04.

**Legenda de classificação (usada em todo o documento):**
🟢 já existe no VRmed · 🟡 dá pra implementar com o que já temos · 🔵 integrar open source externo ·
🟠 precisamos desenvolver · 🔴 problema de pesquisa/alto risco · ⚫ regulatório/clínico, não só técnico.

---

## Resumo executivo

**O VRmed já está sentado num cruzamento que quase ninguém ocupa: _patient-specific_ + _web/WebXR sem instalação_ + potencial de ser _validável_.** A auditoria anterior mostrou que a espinha dorsal científica (DICOM → HU → TotalSegmentator → máscara → mesh → GLB → Three.js → WebXR) já roda. Esta análise mostra que **quase todos os próximos saltos são integração e engenharia de produto, não pesquisa** — e que a maior parte usa tecnologia que já é dependência do projeto (SimpleITK, scipy, trimesh) ou que encaixa lado a lado sem trocar a stack (Niivue).

Cinco conclusões que orientam tudo:

1. **O pipeline é ótimo para ver, inadequado para medir.** Ele foi ajustado de propósito para VR/educação (contato garantido, anti-z-fighting, orçamento de triângulos) e **nunca mede o erro que introduz**. Serve para 🟢 visualização; **não** serve para 🔴 medição nem ⚫ planejamento — hoje. A perda de 13–19% de volume/relevo é documentada, mas não quantificada contra a realidade.

2. **O maior buraco competitivo é a falta de 2D↔3D** — e ele é barato de fechar. O pipeline **já calcula a matriz affine** (voxel↔mundo em RAS); só não a serializa. Ligar um painel 2D de slices ao modelo 3D é 🟡/🔵 (Niivue lê o `ct.nii.gz` que já produzimos), não pesquisa.

3. **A primeira patologia inteligente é o nódulo pulmonar** — e ela já está ao alcance: o TotalSegmentator (que já usamos) tem subtask `lung_nodules` (Apache-2.0) + `lung_vessels`; a cadeia máscara→malha se reaproveita; e a relação espacial (distância lesão↔vaso) sai de `scipy`+`trimesh`, já instalados.

4. **O moat não pode ser "usamos TotalSegmentator".** Os três diferenciais defensáveis são: **(#1) fidelidade auditável** (alta fidelidade + Dice/HD95 provados), **(#2) inteligência espacial patient-specific no navegador** (medidas geométricas automáticas sobre 2D↔3D — o quadrante que só o VRmed ocupa), e **(#3) dataset próprio + registro longitudinal** (colheita contínua). Visualização e infra não são moat.

5. **Há um teto regulatório ⚫ que separa dois trilhos.** Enquanto for "educacional, não substitui laudo", vende já. Qualquer medida com claim clínico empurra para SaMD (ANVISA/510(k)) e exige pré-requisitos que hoje não existem: **anonimização (pydicom) e validação (Dice/HD95)**. Manter os dois trilhos explícitos.

**O primeiro trimestre de maior alavancagem** (quase tudo 🟡/🔵, aproveitando o que já existe): reprodutibilidade do ambiente + unificar/endurecer VR + **2D↔3D com Niivue** + **validação quantitativa** com SimpleITK. Nada disso pede reescrever o pipeline.

---

## Sumário

1. DICOM → 3D com precisão médica + validação
2. Vínculo 2D ↔ 3D
3. Patologias — detecção, segmentação e relação espacial
4. Comparação temporal
5. Patient-specific model vs Patient Digital Twin
6. VR — "entrar dentro do exame"
7. Análise competitiva
8. Diferencial / moats proprietários
9. Roadmap de evolução revisado
10. Os 10 maiores avanços tecnológicos

---

## 1. Precisão: DICOM → 3D com validação médica

Legenda: 🟢 já existe · 🟡 dá pra fazer com o que temos · 🔵 integrar open source · 🟠 desenvolver · 🔴 pesquisa/alto risco · ⚫ regulatório/clínico.

O pipeline do VRmed é honesto e bem comentado — ele **assume** que é ilustrativo (o próprio `docs/CLINICA-FIDELIDADE.md` fala em perdas de 13–19%). O problema não é bug: é que **nenhuma etapa mede o erro que introduz**, e alguns passos trocam fidelidade por aparência de propósito (contato garantido, anti-z-fighting). Abaixo, onde exatamente se perde informação, quanto, e como medir.

### 1.1 Mapa de perda de precisão, etapa por etapa (com linha)

Cada linha abaixo aponta o arquivo real e a linha onde o erro nasce.

| Etapa | Onde (arquivo:linha) | Tipo de erro | Ordem de grandeza | Reversível? |
|---|---|---|---|---|
| DICOM → HU | `ingestao.py:51` (GDCM aplica RescaleSlope/Intercept) | Nenhum — transformação linear exata | 0 (exato) | — |
| HU → int16 | `ingestao.py:126` `np.rint(...).astype(int16)` | Quantização por arredondamento | ±0,5 HU (irrelevante para CT) | não |
| **Voxel anisotrópico mantido** | `ingestao.py:93-97` (só **avisa** se fatia > 3 mm); `docstring:l.3` "reamostragem isotrópica só AVISADA" | Anisotropia propaga para todo o resto: superfície em "escadinha" no eixo Z, marching cubes vê degraus | Fatia 2,5 mm × pixel 0,4 mm = anisotropia 6:1 → erro de forma dominante no eixo Z | sim (reamostrar) |
| Gantry oblíquo | `ingestao.py:113-118` (só **avisa**; `tc-para-vrmed` assume affine diagonal) | Cisalhamento geométrico não corrigido | proporcional ao tilt | sim (reamostrar) |
| **Segmentação em 1,5 mm** | `segmentacao.py:123-124` `higher_order_resampling_LEGACY=True` (TS reamostra internamente p/ 1,5 mm e volta) | Resolução efetiva da máscara é 1,5 mm mesmo em CT de 0,5 mm → **vasos finos e paredes finas somem** | perde estruturas < ~2–3 mm; `--fast` piora para 3 mm (`segmentacao.py:108`) | não (é o teto de detalhe) |
| Erro de rótulo do nnU-Net | `segmentacao.py` (inferência pré-treinada) | Falso-positivo/negativo por voxel; pior em patologia/anatomia atípica | TS reporta Dice médio 0,943 no **conjunto deles**, não no seu caso patológico | não |
| Máscara → binária | `tc-para-vrmed.py:61` `dataobj > 0.5` | Limiar rígido; sem efeito de volume parcial | ±½ voxel na borda | não |
| **Remoção de ilhas < 30 mm³** | `malha.py:84-98` `limpar()` | Estruturas verdadeiras pequenas apagadas | nódulo/vaso < 30 mm³ deletado | não |
| **Preenchimento de buracos** | `malha.py:98` `binary_fill_holes` | Lúmens e cavidades internas reais fechados | volume da cavidade somado ao sólido | não |
| **Dilatação artificial ("encostar")** | `malha.py:101-105`, chamado em `tc-para-vrmed.py:148-151` | Volume **inventado**: veias dilatadas 1 voxel para dentro do coração para garantir contato | +1 voxel na junção (geométrico, não medido) | não |
| **Suavização gaussiana** | `malha.py:137,139` σ = max(0,6 mm, 0,5×maior voxel) | Erode volume, encolhe convexidades, apaga relevo fino | docstring: os 1,3 mm antigos apagavam 17% da área e 5× o relevo; mesmo 0,6 mm reduz vaso fino | não |
| Marching cubes level 0,5 | `malha.py:142` | Isosuperfície interpolada sobre máscara borrada; viés de borda (encolhe convexo, expande côncavo) | sub-voxel, mas somado ao smoothing | não |
| **Filtro Taubin** | `malha.py:150` `lamb=0.5, nu=0.53, iterations=4` | Passa-baixa: remove alta frequência (textura, pequenas saliências). Melhor que Laplaciano puro (resiste ao encolhimento), mas ainda alisa | detalhe < poucos mm | não |
| **Afastamento pela normal** | `malha.py:154-155` −0,15 mm nas câmaras | Encolhimento sistemático da malha para evitar z-fighting | −0,15 mm em toda a superfície do coração (num vaso de 3 mm chegava a metade do volume, por isso limitado a `heart_`) | não |
| **Decimação** | `malha.py:159-170` `fast_simplification` p/ orçamento ~150k | Quadric decimation move vértices, achata detalhe; pisos de 3k tris em estruturas pequenas | perde geometria fina; grandes divididas proporcionalmente (`tc-para-vrmed.py:42-56`) | não |
| Volume da malha | `malha.py:273` `abs(mesh.volume)` | `trimesh.volume` só é confiável se **watertight**; malha decimada pode não ser | erro indefinido se `watertight=False` | — |

**Cadeia composta:** um vaso pulmonar de 3 mm num CT com fatia de 2,5 mm passa por: resolução de máscara de 1,5 mm → possível remoção como ilha → suavização σ≥0,75 mm → marching cubes → Taubin → dilatação de contato → decimação com piso de 3k tris. Cada passo é pequeno, mas eles **se somam na mesma direção** (perder relevo, encolher/inflar de forma não medida). O relatório atual (`tc-para-vrmed.py:185,193`) mede só o delta **máscara→malha** de volume — **não** captura as perdas anteriores (volume parcial, erro de segmentação, anisotropia).

### 1.2 O que já existe de QA — e o que falta

🟢 **Já existe** e é bom: o relatório por estrutura em `tc-para-vrmed.py:186-197` grava `volume_mascara_ml`, `volume_malha_ml`, `perda_volume_pct`, `toca_borda` e `watertight`, com aviso quando a perda passa de 5% em estruturas ≥ 10 mL (`:201`). Isso é o embrião de um relatório de fidelidade.

🟢 Existe também `metricas.py` (volume/bbox/componentes) e `qa.py` (PNGs de máscara sobre CT) — QA **visual**, não quantitativo contra verdade.

O que **não** existe (confirmado na auditoria de base): comparação contra ground-truth, Dice, HD95, ASSD, NSD, erro dimensional calibrado, e `validar-segmentacao.py`. Ou seja: hoje o pipeline **não sabe medir o próprio erro** — ele só reporta a diferença entre dois artefatos que ele mesmo produziu (máscara e malha), nunca contra a realidade.

### 1.3 Como MEDIR cada tipo de erro (glossário operacional)

- **Erro dimensional** — diâmetro/distância conhecida (fantoma ou objeto sintético) medida no fim do pipeline vs. valor real. Reporte erro absoluto (mm) e relativo (%).
- **Erro de volume** — |V_pipeline − V_verdade| / V_verdade. Para segmentação vs. GT use contagem de voxels × spacing; para malha vs. máscara, `trimesh.volume` **só** se `is_watertight` (senão o número em `malha.py:273` é lixo).
- **Dice / DSC** — sobreposição volumétrica: 2|A∩B| / (|A|+|B|). Sensível a estruturas grandes, quase cego a vasos finos.
- **NSD / Surface Dice @ tolerância τ** — fração da superfície dentro de τ mm da superfície de referência. Muito mais informativo que DSC para paredes e bordas; foi a métrica principal do TotalSegmentator (NSD 0,966).
- **HD95** — 95º percentil da distância de Hausdorff (near-worst-case robusto a outliers). Pega o pior desvio de borda sem explodir com 1 voxel espúrio.
- **ASSD / MSD** — distância média simétrica entre superfícies (mm). Erro "típico" de borda.
- **Preservação de pequenas estruturas** — taxa de detecção por classe: quantos vasos/lóbulos/nódulos verdadeiros sobrevivem a `limpar()` (`malha.py:84`) e à decimação. Reporte recall por faixa de tamanho.
- **Resolução espacial / spacing / anisotropia** — leia `spacing_mm` (já em `ingestao.py:163`); anisotropia = maior/menor eixo. Slice thickness > 1,5 mm já limita o que a segmentação enxerga (`segmentacao.py:123`).
- **Efeito de volume parcial** — voxel na borda contém mistura de tecidos; o limiar `> 0.5` (`tc-para-vrmed.py:61`) o resolve como tudo-ou-nada, viés sistemático de ±½ voxel.
- **Diferença máscara→malha** — voxelize a malha de volta na grade da máscara e compute DSC/HD95 entre elas: isola quanto o smoothing+Taubin+afastamento+decimação custaram, separado do erro de segmentação.

### 1.4 O pipeline é adequado para quê?

**(a) VISUALIZAÇÃO / educação — 🟢 SIM, adequado.** É exatamente para isto que ele foi ajustado (contato garantido, anti-z-fighting, orçamento de VR, cor pelo HU real). Continue assim. Único reparo honesto: rotular no viewer que a geometria é ilustrativa.

**(b) MEDIÇÃO (volumetria, diâmetros) — 🔴 NÃO, hoje não.** Erros não calibrados se acumulam numa direção (smoothing 13–19% documentado + afastamento + decimação + anisotropia), e `mesh.volume` roda mesmo com `watertight=False`. Para virar medição seria preciso: 🟡 reamostragem isotrópica antes da malha (`ingestao.py` só avisa); 🟠 desligar/parametrizar `encostar()` e o afastamento nos casos de medida; 🔵 validar contra fantoma e GT com as métricas de 1.5; e reportar incerteza por caso. **Meça no volume/máscara, nunca na malha decimada.**

**(c) PLANEJAMENTO cirúrgico/intervenção — ⚫🔴 NÃO.** Além de todo o item (b), exige segmentação validada por caso (não média populacional), resolução sub-milimétrica preservada (o teto de 1,5 mm da segmentação e a remoção de ilhas < 30 mm³ são impeditivos para vasos/margens), zero geometria inventada, e — o ponto ⚫ — é **software como dispositivo médico**: precisa de validação clínica formal, rastreabilidade e regulação. Não é questão de código.

Resumindo o que muda de nível para nível: **visualização → medição** = reamostrar isotrópico + calibrar com fantoma + desligar invenções geométricas + reportar incerteza. **Medição → planejamento** = validação clínica por caso + preservação de detalhe fino + trilha regulatória.

### 1.5 Pipeline de validação quantitativa concreto (proposta)

Objetivo: um script `validar-segmentacao.py` (🟠 a criar, ~150 linhas) + um `validar-malha.py` que produzam um relatório por caso e um agregado. Nada de treino — só medir.

**Ground-truth (contra o quê comparar):**
- 🔵 **Dataset do próprio TotalSegmentator** (~1.200 casos com máscaras de especialista, liberado no Zenodo pelo grupo de Wasserthal) — mede o erro de segmentação *na sua instalação*, com as classes que você usa.
- 🔵 **MM-WHS** (Multi-Modality Whole Heart Segmentation) para câmaras cardíacas; **LIDC-IDRI**/TCIA para pulmão/nódulos; **Medical Segmentation Decathlon** para fígado/baço. Máscaras de referência de especialistas.
- 🟠 **Fantoma sintético** para erro dimensional: gere um NIfTI com uma esfera/cilindro de dimensão e HU conhecidos, rode o pipeline inteiro, meça diâmetro e volume no GLB final. Este é o "botão de calibração" que o mundo físico exige — nenhum modelo teórico substitui.

**Métricas a rodar (nível máscara: segmentação vs GT):** DSC, **NSD/surface Dice @ τ=1 mm e 2 mm**, HD95, ASSD — por estrutura, por caso.

**Métricas a rodar (nível malha: isola perda máscara→malha):** voxelize a malha de volta → DSC/HD95 contra a máscara de origem; erro de volume malha vs máscara (só se `is_watertight`); distância superfície-a-superfície entre a malha do pipeline e uma malha gerada da GT.

**Bibliotecas (open source, com fonte):**
- 🔵 **DeepMind `surface-distance`** — `compute_surface_distances(mask_gt, mask_pred, spacing_mm)` e depois `compute_surface_dice_at_tolerance`, `compute_robust_hausdorff` (passe 95 p/ HD95), `compute_average_surface_distance`, `compute_dice_coefficient`. Trabalha em **máscaras com spacing anisotrópico** — encaixa direto na sua saída NIfTI. É a implementação usada no paper do TotalSegmentator. (https://github.com/google-deepmind/surface-distance)
- 🔵 **MONAI metrics** — `DiceMetric`, `HausdorffDistanceMetric(percentile=95)`, `SurfaceDistanceMetric(symmetric=True)`, `SurfaceDiceMetric`. Espera tensores CHW[D] one-hot. Bom se quiser rodar em lote/GPU. (https://docs.monai.io/en/stable/metrics.html)
- 🔵 **SimpleITK** (já é dependência sua!) — `LabelOverlapMeasuresImageFilter` (Dice/Jaccard) e `HausdorffDistanceImageFilter`. Zero dependência nova para o DSC/HD básico. (https://simpleitk.org)
- 🔵 **medpy** — `medpy.metric.binary.dc`, `.hd95`, `.assd` — API de uma linha por métrica, aceita `voxelspacing`. (https://loli.github.io/medpy/)
- 🔵 **seg-metrics** (Jia) — pacote que agrega Dice/HD/ASSD para muitas classes de uma vez, útil para o relatório em massa. (https://github.com/Jingnan-Jia/segmentation_metrics)

**Como reportar (por caso + agregado):**
- Tabela por caso × estrutura: DSC, NSD@1mm, HD95 (mm), ASSD (mm), erro de volume (%), spacing e anisotropia do exame.
- Agregado por estrutura: **mediana e IQR** (não média — distribuições de Dice são assimétricas), n de casos, taxa de detecção de estruturas pequenas.
- **Bland-Altman** para volume (pipeline vs GT) — expõe viés sistemático (o smoothing sempre encolhe → você deve ver viés negativo consistente, quantificando os "13–19%" documentados).
- Boxplot de HD95/ASSD por estrutura.
- Estenda o `relatorio` que já existe em `tc-para-vrmed.py:186` com esses campos quando houver GT — reaproveita a infraestrutura de JSON de relatório já pronta, sem reescrever nada.

**Regra de ouro que o VRmed já pratica (mantenha):** medir sempre na **máscara/volume**, nunca na malha decimada de VR; e nunca reportar número de precisão sem `is_watertight=True` (a checagem já está em `tc-para-vrmed.py:195`).

**Fontes:**
- TotalSegmentator (Dice 0,943 / NSD 0,966, modelo 1,5 mm) — Wasserthal et al., *Radiology: AI* 2023: https://pubs.rsna.org/doi/full/10.1148/ryai.230024
- DeepMind surface-distance: https://github.com/google-deepmind/surface-distance
- MONAI metrics: https://docs.monai.io/en/stable/metrics.html
- SimpleITK: https://simpleitk.org
- medpy: https://loli.github.io/medpy/
- seg-metrics: https://github.com/Jingnan-Jia/segmentation_metrics

## 2. Vínculo 2D ↔ 3D (slices ↔ modelo)

**Legenda:** 🟢 já existe no VRmed · 🟡 dá pra fazer com o que temos · 🔵 integrar open source · 🟠 precisamos desenvolver · 🔴 pesquisa/alto risco · ⚫ regulatório/clínico.

### 2.1 O que já temos (e jogamos fora)

O ponto central desta frente: **o VRmed já calcula toda a matriz de transformação voxel↔mundo — e a descarta depois de exportar o GLB.** Não é problema de pesquisa; é um dado que existe no pipeline e não chega ao viewer.

Onde a affine já vive no código real:

- 🟢 `scripts/clinica/ingestao.py` monta os componentes da affine em RAS e os devolve no dicionário de resumo: `spacing_mm` (de `img.GetSpacing()`), `origem_mm_ras` (`LPS_PARA_RAS @ origin`) e `direcao_ras` (`LPS_PARA_RAS @ direction`). O comentário no `salvar_nifti` é explícito: "SimpleITK escreve qform/sform em RAS — o nibabel do resto do pipeline lê o affine certo". A conversão LPS→RAS (`np.diag([-1,-1,1])`) já está feita, que é exatamente a fonte clássica de erro de espelhamento (DICOM é LPS; NIfTI é RAS+ — [nibabel](https://nipy.org/nibabel/nifti_images.html), [NIfTI qform/sform](https://nifti.nimh.nih.gov/nifti-1/documentation/nifti1fields/nifti1fields_pages/qsform_usage)).
- 🟢 `scripts/clinica/malha.py` usa a affine **nas duas direções**: voxel→mm (`verts_mm = verts @ affine[:3,:3].T + affine[:3,3]`, linha 144) na hora de gerar a malha, e mm→voxel (`vox = mm @ inv_affine[:3,:3].T + inv_affine[:3,3]`, linha 212) para reamostrar a HU/oclusão na superfície. Ele guarda inclusive `inv_affine` da grade da CT **e** `inv_affine_mascaras` da grade das máscaras (quando diferem). Ou seja: a máquina completa de ida-e-volta já está escrita e testada — só não é serializada.
- 🟢 O `ct.nii.gz` gerado carrega a affine embutida (qform/sform), e as máscaras de segmentação são NIfTI na mesma grade. Isso é ouro para o vínculo (ver 2.5).

O que **falta exportar** (e por isso hoje não há vínculo):

- 🔴 problema de dado, não técnico: `public/pacientes/manifest.json` só tem `slug/titulo/glb/fonteDados`. **Nenhum campo `affine`, `spacing`, `shape`, `origin`, nem mapa estrutura→voxels.** O `identifyStructure` (em `lib/model-utils.ts`) identifica a peça **só pelo nome da malha** — não sabe onde ela está na grade da TC.

### 2.2 Coordenadas: a cadeia de transformações real do VRmed

Para clicar no 3D e achar o slice, o ponto tem que atravessar **quatro** espaços — e dois deles são invenções do viewer, não da TC. Isto é o que torna o vínculo não-trivial no VRmed especificamente:

```
[i,j,k voxel] --affine(RAS,mm)--> [x,y,z mm RAS]
              --exportação GLB--> [metros, Y-up]        (malha.py: mm/1000; RAS→Y-up)
              --normalizeContent--> [caixa ±1, recentrado]  (lib/model-utils.ts:307)
              --pivot: scale 1.4, rotação 180° em Y--> [MUNDO three.js]
```

Os dois últimos passos são o problema. O `ClinicaViewer.tsx`:

1. 🟢 **`normalizeContent` (linha 307)** mede a bbox do modelo cru e aplica `scale = 2/maxDim` + recentragem. **Isto destrói a relação métrica**: depois dele, 1 unidade de mundo ≠ 1 mm nem 1 m. Qualquer vínculo por affine tem que compor a inversa dessa normalização (guardar `scale` e `center` usados). Como a normalização é determinística a partir da bbox do GLB, dá pra recalcular no cliente **sem novo dado** — 🟡.
2. 🟢 **O pivô aplica `scale={1.4}` e `rotation={[0, Math.PI, 0]}`** (linha 128) — meia-volta em Y porque "o pipeline exporta a frente do paciente em −Z". É uma `THREE.Matrix4` conhecida e invertível. 🟡.

**Conclusão da cadeia:** para ir de um clique a um voxel, componha `M = affine · (RAS→Y-up)⁻¹ · (m→mm) · normalize⁻¹ · pivot⁻¹` e aplique em `hit.point`. Todos os fatores são conhecidos hoje, menos a `affine` — que precisa ir para o manifest. **Nada aqui é pesquisa.**

### 2.3 Picking 3D → slice (o caminho que o código quase já faz)

🟢 O `handleClick` em `ClinicaViewer.tsx` (linha 112) **já produz o que precisamos**: `event.intersections` do raycaster do R3F, e ele já filtra `object.visible` e o lado certo do plano de corte (`plano.current.distanceToPoint(h.point) >= 0`). O `hit.point` é um `THREE.Vector3` em coordenadas de **mundo** — é exatamente a âncora do vínculo.

O que falta (🟡, só cliente + affine no manifest):

```
hit.point (mundo)
  → aplicar pivot⁻¹ e normalize⁻¹  → mm RAS (fatores já conhecidos no viewer)
  → mm @ inv_affine[:3,:3].T + inv_affine[:3,3]  → (i,j,k)  // MESMA fórmula do malha.py:212
  → índice do slice = componente do eixo do corte; posição no slice = (i,j) restantes
```

Isso resolve o **forward** (clicar na aorta no 3D → "aorta aparece nos slices axiais 112–140, aqui neste ponto") **sem** precisar de mapa estrutura→voxels: o `hit.point` já dá o voxel exato. O mapa por-estrutura só é preciso para o realce "esta estrutura inteira" (2.5).

O inverso (**2D → 3D**, "você está aqui"): dado `(i,j,k)` de um slice, `mm = affine @ [i,j,k,1]`, depois aplicar `normalize` e `pivot` para virar posição de mundo, e desenhar um **crosshair 3D** — que no VRmed pode ser uma pequena `sphereGeometry`/`Text3D` (o `Text3D` já é usado para o rótulo em VR, linha 219). 🟡.

### 2.4 Crosshair, clipping e MPR — onde o VRmed está e o gap

- 🟢 **Clipping plane já existe e funciona.** `ClinicaViewer` usa **um** `THREE.Plane` compartilhado por todos os materiais com `localClippingEnabled: true` (linha 448) e três presets axial/coronal/sagital. **Porém o `p.constant = ALCANCE - posicao*2*ALCANCE` está em unidades normalizadas (±1,5), não em mm.** Para o corte "casar" com um slice real, esse `constant` precisa ser mapeado de volta para índice de voxel via a mesma cadeia inversa da 2.3. 🟡.
- 🟠 **Não há painel 2D nenhum.** Hoje o corte só remove geometria do 3D; não se vê a imagem da TC no plano cortado. O "vínculo" que o usuário espera (mesa de dissecção: mexe no slice, o 3D acompanha) exige um **viewer 2D de slices** lado a lado — que o VRmed não tem. É o único bloco que pede biblioteca externa.
- 🟢 **Crosshair 3D**: trivial de adicionar (uma esfera na posição calculada). 🟡.
- 🟠 **MPR ortogonal** (axial+coronal+sagital sincronizados) e 🔴/🟠 **MPR oblíquo/reslice arbitrário** (cortar num plano que não é dos eixos): o oblíquo é o caso difícil — reamostragem trilinear do volume num plano arbitrário. Não vale reimplementar; é exatamente o que as libs abaixo já fazem na GPU.

### 2.5 A sacada preguiçosa: as máscaras JÁ SÃO o mapa estrutura→voxels

O briefing pede exportar "o mapa estrutura→voxels — hoje não exporta". Antes de gerar um formato novo: 🟡 **o pipeline já produz uma máscara NIfTI por estrutura** (é a entrada do `malha.py`, na grade da CT com a mesma affine). Uma máscara **é** o mapa estrutura→voxels — rotulada, esparsa, na grade certa. Duas saídas baratas, sem inventar formato:

1. Um **volume de rótulos** (segmentation NIfTI, inteiro por estrutura) — que Niivue e Cornerstone3D carregam **nativamente** como overlay colorido sobre a CT. Realçar "fígado" nos slices = pintar o label 5. Zero código de mapeamento novo.
2. Por-estrutura, um **bbox em voxel + centróide** no manifest (o `metricas.py` já computa volume/bbox/componentes) — barato, resolve "pular para o slice central desta estrutura". 🟡.

Ou seja: o "mapa estrutura→voxels" caro (dict de listas de voxels) é desnecessário — reaproveite os artefatos que o pipeline já cospe.

### 2.6 Biblioteca do painel 2D: comparação para menor impacto

Critério: entrar **lado a lado** com o three/R3F atual (não substituir o 3D), consumir o que o pipeline já produz (`ct.nii.gz` + máscaras NIfTI), e ser leve o bastante para um projeto de IC em Next.

| Lib | O que é | Encaixe no VRmed | Peso/atrito | Veredito |
|---|---|---|---|---|
| **Niivue** 🔵 | Viewer WebGL2 de volumes; carrega **NIfTI e DICOM** nativo, MPR (axial/coronal/sagital), crosshair configurável, overlays de rótulo, embute em React ([niivue.com/docs](https://niivue.com/docs/), [GitHub](https://github.com/niivue/niivue), [Class Niivue API](https://niivue.com/docs/api/niivue/classes/Niivue/)) | **Melhor encaixe.** Já produzimos `ct.nii.gz` + máscaras NIfTI na mesma affine — ele lê direto, sem servidor. Trabalha em coordenadas de mundo mm (RAS), a mesma convenção da nossa affine, então sincronizar é passar o mesmo `[x,y,z] mm`. Callback de crosshair ↔ nosso `hit.point`. | Leve, uma dependência, WebGL2 (mesmo requisito do three). | **Escolha para o painel 2D.** |
| **Cornerstone3D** 🔵 | Lib JS madura de imagem médica; MPR em qualquer orientação **inclusive oblíquo**, **synchronizers** entre viewports (câmera/window-level), ferramentas de segmentação e anotação, integra com React ([overview](https://www.cornerstonejs.org/docs/getting-started/overview/), [MPR/oblíquo](https://radicalimaging.com/post/3-medical-imaging-tasks-you-can-now-achieve-using-cornerstone3d-and-cornerstone3dtools)) | DICOM-first (pensado pra DICOMweb/PACS). Aceita volumes, mas o caminho feliz é DICOM; alimentar NIfTI dá mais trabalho que o Niivue. Ganha se um dia quisermos ferramentas de medição/segmentação no browser e MPR oblíquo pronto. | Mais pesado (core+tools+dicom-image-loader), mais superfície de API. | **Overkill agora**; reavaliar se o projeto virar ferramenta de anotação. |
| **VTK.js** 🔵/🟠 | Toolkit de visualização científica na web: **volume rendering** GPU, `ImageResliceMapper` (reslice planar arbitrário na GPU), `ResliceCursorWidget`, curviplanar ([v30](https://www.kitware.com/vtk-js-v30-release/), [ImageResliceMapper](https://kitware.github.io/vtk-js/examples/ImageResliceMapper.html)) | É a rota se quisermos **volume rendering** de verdade (hoje inexistente — `volume.py` não existe) e reslice oblíquo/curvo. Mas é outro renderizador WebGL ao lado do three — dois motores no mesmo app. | O mais pesado; curva de API alta; conviver com R3F é atrito real. | Só se **volume rendering** virar requisito; não para o vínculo básico. |
| **OHIF** 🔵 | Aplicação/visualizador completo construído sobre Cornerstone3D | É um app inteiro, não um componente. Não se "embute" limpo num canvas R3F existente. | Muito grande. | **Não** — é aplicação, não peça. |
| **itk-wasm** 🔵 | I/O e pipelines de imagem em WebAssembly (ler DICOM/NIfTI, registro, segmentação no browser) ([discourse VTK](https://discourse.vtk.org/t/showing-dicoms-using-vtk-js-and-itk-wasm/14461)) | Não é viewer — é I/O/processamento. Útil se um dia quisermos **ler DICOM no cliente** (hoje a ingestão é CLI Python no PC). Complementa Niivue/VTK.js, não os substitui. | Médio (WASM). | Fora de escopo do vínculo; guardar para ingestão no browser. |
| **three.js puro** 🟡 | O que já temos | O 3D fica no three (não trocar o que funciona). O painel 2D **não** deve ser reimplementado no three — desenhar slices com textura e reslice à mão é reinventar o Niivue. | — | **Manter o three no 3D**, delegar o 2D. |

### 2.7 Arquitetura recomendada (menor impacto)

**Two-pane, dois renderizadores, um sistema de coordenadas comum (mm RAS):**

- 🟢 **3D:** continua o `ClinicaViewer` atual (three + R3F + GLB). Não mexer no que funciona.
- 🔵 **2D:** um `<Niivue>` num painel ao lado, carregando `ct.nii.gz` como base e a máscara/label NIfTI como overlay. Um só download por caso já basta (o pipeline só precisa **publicar** o `ct.nii.gz` e o label, que hoje ficam locais).
- 🟡 **Sincronização pela affine, em mm RAS** (o denominador comum dos dois lados): clique no 3D → `hit.point` → mm RAS (2.3) → `nv.scene.crosshairPos`/`nv.moveCrosshairInVox`; e o callback de crosshair do Niivue → mm RAS → `normalize`/`pivot` → crosshair 3D + reposiciona o `THREE.Plane` de corte. É o mesmo padrão de "synchronizer" que o Cornerstone documenta, só que atravessando dois motores pela affine.

**O que classifica como 🟡 (só com o que temos):** exportar a affine + shape + spacing no `manifest.json` (já calculados na `ingestao.py`); compor as inversas de `normalize` e `pivot` no cliente; converter `hit.point`↔voxel (fórmula idêntica ao `malha.py`); crosshair 3D; mapear o `constant` do clipping para índice de slice.

**O que é 🔵 (integrar lib):** o painel 2D em si (Niivue) e a leitura do NIfTI no browser.

**O que fica 🟠/🔴/⚫:** MPR oblíquo/reslice arbitrário sincronizado ao 3D (🟠 — ou 🔵 se adotar VTK.js/Cornerstone que já fazem); volume rendering (🟠, `volume.py` não existe); e ⚫ qualquer uso além de educacional exige o aviso que o viewer já mostra ("não substitui laudo") + validação clínica que hoje não existe (sem Dice/HD95). O vínculo 2D↔3D **melhora a confiabilidade percebida** — o usuário passa a poder conferir a malha contra o slice real — mas não substitui validação.

### 2.8 Pegadinhas específicas do VRmed a não esquecer

- 🟢 **Espelhamento LPS/RAS já resolvido na ingestão** — se o painel 2D vier de outra fonte que não converte, o fígado aparece do lado errado. Niivue trabalha em RAS+, igual à nossa affine; casa.
- 🟢 **A rotação de 180° em Y do pivô** e o **Y-up do GLB** vs **Z-up/RAS** do NIfTI: são duas trocas de eixo que precisam entrar na composição, senão o crosshair cai no lugar espelhado/rodado. Ambas são constantes conhecidas no código.
- 🟢 **`normalizeContent` recentra por bbox do GLB**, não pela origem da TC — o "centro" do modelo 3D não é a origem mm. Tem que usar `scale`+`center` reais medidos, não assumir.
- ⚠️ **A malha perde 13–19% de volume/relevo** pela suavização (documentado no pipeline). Portanto o 3D e o slice **não coincidem perfeitamente** — a superfície reconstruída é mais lisa que a borda real na CT. Isso é um argumento *a favor* do vínculo (deixa o usuário ver a diferença), mas o crosshair pode cair alguns mm dentro/fora da borda real; comunicar isso, não vender precisão sub-milimétrica que não temos.

## 3. Patologias — detecção, segmentação e relação espacial

**Legenda:** 🟢 já existe no VRmed · 🟡 dá pra implementar com o que já temos · 🔵 integrar open source externo · 🟠 precisamos desenvolver · 🔴 problema de pesquisa/alto risco · ⚫ regulatório/clínico, não só técnico.

### 3.1 O salto conceitual: de "aqui está o pulmão" para "aqui está a lesão deste paciente"

Hoje o pipeline do VRmed produz **anatomia normal por classe** (TotalSegmentator v2 → máscara → malha → GLB nomeado), e as "patologias" existentes (`achados-pulmao.py` / `pintar-pulmao.py`) são **limiar de HU pintando um modelo ilustrativo** — hotspot aproximado, não a lesão real do paciente na malha real. O salto tem três componentes independentes:

1. **Detectar/segmentar a lesão** → uma máscara 3D da lesão *deste* exame (nódulo, tumor, hemorragia, etc.).
2. **Converter em malha** → exatamente a mesma cadeia `máscara → gaussian → marching_cubes → taubin → simplify` que já roda (🟢 pronto).
3. **Calcular a relação espacial** → distância lesão↔vaso/brônquio, volume, posição, contato com estruturas — o verdadeiro diferencial do VR (🟡, temos scipy+trimesh).

O ponto crítico: o componente (1) é o único que exige tecnologia nova, e — boa notícia — **para o caso torácico já existe modelo pré-treinado gratuito dentro da ferramenta que o VRmed já usa**. Os componentes (2) e (3) reaproveitam a stack atual quase sem custo.

---

### 3.2 Detecção e segmentação de lesões: o que existe pronto (open source, pré-treinado)

#### 3.2.1 TotalSegmentator — subtasks de patologia (o caminho de menor atrito) 🔵/🟢

O VRmed **já roda TotalSegmentator v2** (`segmentacao.py`, presets tórax/cardíaco/abdômen, `roi_subset`). O que a auditoria não mapeou é que o TotalSegmentator tem **subtasks de lesão/patologia** que produzem máscara — o mesmo formato que a cadeia máscara→malha consome. Fonte: [README oficial](https://github.com/wasserth/TotalSegmentator/blob/master/README.md).

| Subtask | O que segmenta | Licença | Encaixe no VRmed |
|---|---|---|---|
| `lung_nodules` | `lung`, `lung_nodules` (treinado em 1353 sujeitos, parte do LIDC-IDRI, por BLUEMIND AI) | **Apache-2.0 (livre, inclusive comercial)** | 🔵 **encaixe perfeito no pipeline tórax** |
| `lung_vessels` | `lung_arteries`, `lung_veins`, `lung_airways`, `lung_airways_wall` | Apache-2.0 (livre) | 🔵 dá o "vaso/brônquio" para medir relação espacial |
| `cerebral_bleed` | `intracerebral_hemorrhage` | Apache-2.0 (livre) | 🔵 fora do foco tórax, mas gratuito |
| `kidney_cysts` | `kidney_cyst_left/right` | Apache-2.0 (livre) | 🔵 abdômen |
| `pleural_pericard_effusion` | derrame pleural/pericárdico | **Restrita (comercial paga)** | ⚫ licença |
| `liver_vessels` | `liver_vessels`, `liver_tumor` | **Restrita (comercial paga)** | ⚫ licença + robustez menor |
| `liver_lesions` / `liver_lesions_mr` | lesões hepáticas (CT/MR) | **Restrita (comercial paga)** | ⚫ licença + robustez menor |

Detalhe importante que muda a estratégia: **`lung_nodules` e `lung_vessels` são Apache-2.0 (uso livre)**, enquanto as tasks hepáticas e de derrame são **restritas** (o README avisa que foram treinadas em datasets pequenos, "expect them to work less robustly", e exigem licença paga para uso comercial). Ou seja, o par **nódulo pulmonar + vasos/vias aéreas pulmonares está totalmente disponível, gratuito, e já dentro da ferramenta instalada** — praticamente `roi_subset`/task nova no `segmentacao.py` já existente.

> Custo de integração real: adicionar a chamada da task `lung_nodules` (e `lung_vessels`) ao `segmentacao.py`. É configuração + peso baixado pelo próprio TotalSegmentator, **não** treino. Classificação honesta: 🔵 (integrar open source já presente), beirando 🟡.

#### 3.2.2 MONAI Model Zoo — bundles pré-treinados 🔵

O [MONAI Model Zoo](https://project-monai.github.io/model-zoo.html) tem bundles prontos para inferência. Relevantes:

- **`lung_nodule_ct_detection`** — detecção 3D de nódulo em CT, treinado em **LUNA16**, arquitetura **RetinaNet**; reporta mAP≈0.852 / mAR≈0.998. **Atenção**: é **detecção (bounding box + probabilidade)**, *não* segmentação — dá "onde está e qual a chance de ser nódulo", mas **não entrega a máscara voxel-a-voxel** que a cadeia máscara→malha precisa. Útil como **rastreador/triagem** ("existem N candidatos, aqui"), não como fonte de malha. Requer ~12 GB de VRAM. Fonte: [tutorial MONAI](https://github.com/Project-MONAI/tutorials/blob/main/monailabel/monailabel_monaibundle_3dslicer_lung_nodule_detection.ipynb).
- **`Decathlon LiverTumourSegmentation`** — segmentação 3D pré-treinada no subset de tumor de fígado do MSD. Entrega máscara (bom para malha), mas fígado tem contraste bem menos robusto que nódulo em pulmão aerado (ver §3.6).

Custo: MONAI **não está instalado** (a auditoria confirma MONAI/nnU-Net ausentes; só `torch` transitivo do TotalSegmentator). Integrar o Model Zoo é 🔵 com peso de setup — adiciona MONAI+deps ao ambiente Python (que já é irreprodutível, sem `requirements.txt`). Por isso, quando a task equivalente existe **dentro do TotalSegmentator já instalado**, ela vence no critério "menor impacto na stack".

#### 3.2.3 MONAI Auto3DSeg / nnU-Net treinados do zero 🔴/🟠

Auto3DSeg e nnU-Net são o estado da arte para *treinar* segmentadores de tumor (ex.: [Auto3DSeg em KiTS23](https://arxiv.org/pdf/2310.04110), [BraTS 2023](https://arxiv.org/pdf/2510.25058), [pâncreas em MRI](https://arxiv.org/pdf/2508.21227)). Mas isso é **treino**, que o escopo atual explicitamente exclui ("NÃO treinar IA agora"). Fica registrado como 🔴 (pesquisa/alto risco: dados, GPU, validação Dice/HD95, tempo) para o futuro — não é o primeiro passo.

---

### 3.3 Segmentação da lesão → malha 3D: reaproveitamento total 🟢

Uma vez que a lesão vire **máscara binária** (saída do `lung_nodules`), ela entra **na mesma cadeia que já existe** em `malha.py`: `gaussian_filter → pad → marching_cubes(level 0.5) → filter_taubin → fix_normals → simplify → cor por vértice por HU`. Zero código novo de reconstrução.

Ressalva técnica honesta (já documentada na memória do projeto): a suavização gaussiana custa **13–19% de volume/relevo**. Para órgão grande é aceitável; para **nódulo pequeno (5–10 mm) isso distorce forma e volume de forma clinicamente relevante**. Recomendação: para lesões pequenas, usar **sigma menor/adaptativo ao tamanho do objeto** e **medir o volume da máscara (voxels × spacing), não da malha suavizada** (🟡, ajuste pontual em `malha.py`/`metricas.py`). O `metricas.py` já calcula volume em mL — reusar para a lesão.

---

### 3.4 Relação espacial: o diferencial que o VR realmente entrega 🟡

Aqui está o valor único do VRmed, e o melhor: **é quase tudo scipy + trimesh, que já estão instalados**. Não precisa de IA nem de dependência nova.

**a) Distância lesão ↔ estrutura (vaso, brônquio, parede):**
- **Rápido, em voxel:** `scipy.ndimage.distance_transform_edt` sobre a máscara *invertida* da estrutura-alvo (vasos/vias aéreas), amostrada nos voxels da lesão → distância mínima e mapa de distâncias. Multiplicar pelo `spacing` para milímetros. (🟡)
- **Preciso, superfície-a-superfície:** `trimesh.proximity.ProximityQuery(mesh_vaso).signed_distance(pontos_da_malha_lesao)` ou `.on_surface()` → distância mínima superfície↔superfície, ponto de contato mais próximo, e se há invasão (sinal negativo = dentro). (🟡)

**b) Volume, bbox, componentes:** já existe em `metricas.py` (volume mL, bbox, nº de componentes). Aplicar à lesão dá "nódulo de X mL, Y mm no maior eixo". (🟢)

**c) Posição anatômica:** cruzar a máscara da lesão com as máscaras de lobos/segmentos que o TotalSegmentator já produz (`lung_upper_lobe_left`, etc.) por sobreposição de voxels → "nódulo no lobo superior direito". (🟡)

**d) Contato/invasão de estrutura crítica:** limiar sobre a distância mínima (ex.: contato < 1 mm com artéria pulmonar) → **flag visual/hotspot no viewer VR**. O `ClinicaViewer` já identifica malha por nome e já faz corte por plano; adicionar uma malha "lesão" + rótulo de distância no `Text3D` (que já existe em VR) é incremento pequeno. (🟡)

Isso transforma o output de "está aqui" para "nódulo de 1,8 mL no lobo superior direito, a 3 mm da artéria segmentar, sem invasão da parede brônquica" — narrativa clínica que **em VR, com corte e escala real, é qualitativamente superior a um laudo 2D**.

---

### 3.5 Datasets públicos relevantes (para referência e futuro fine-tuning)

Como **não vamos treinar agora**, estes importam sobretudo (a) para *validar* a segmentação contra ground truth e (b) para um futuro fine-tuning. Licenças checadas — algumas são **não-comerciais**, o que importa se o VRmed virar produto.

| Dataset | Conteúdo | Licença | Fonte |
|---|---|---|---|
| **LIDC-IDRI** | 1018 CT torácicos, nódulos anotados por 4 radiologistas | TCIA; citada como **CC BY 3.0** na página TCIA, mas há fontes reportando **CC BY-NC** — **verificar antes de uso comercial** ⚫ | [TCIA LIDC-IDRI](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=1966254) |
| **LUNA16** | Subset curado do LIDC-IDRI p/ detecção de nódulo (base do `lung_nodule_ct_detection`) | **CC BY 3.0** (comercial OK c/ atribuição) | [LUNA16](https://luna16.grand-challenge.org/Data/) |
| **LNDb** | CT com nódulos, protocolo LungRADS | **CC BY-NC-ND** (não-comercial, sem derivados) ⚫ | [LNDb / Zenodo](https://zenodo.org/records/6613714) |
| **MSD (Decathlon)** | 10 tarefas: tumor de fígado, cérebro, pulmão, pâncreas, cólon, vaso hepático, etc. | **CC-BY-SA** (comercial OK, atribuição + share-alike) | [MSD / AWS Open Data](https://registry.opendata.aws/msd/), [Nature Comms](https://www.nature.com/articles/s41467-022-30695-9) |
| **KiTS23** | CT rim + tumor renal | Verificar no site do desafio (não confirmado aqui) ⚫ | [kits-challenge.org](https://kits-challenge.org/kits23/) |
| **TCIA (geral)** | dezenas de coleções oncológicas | por-coleção (mistura CC BY / CC BY-NC / restrita) — **checar cada uma** ⚫ | [cancerimagingarchive.net](https://www.cancerimagingarchive.net/) |

Alerta de licença: **LNDb (BY-NC-ND) e possivelmente LIDC-IDRI são não-comerciais**. O modelo `lung_nodules` do TotalSegmentator, apesar de treinado *parcialmente* no LIDC-IDRI, é distribuído sob **Apache-2.0** pelo autor — o VRmed consome o **modelo** (Apache-2.0), não os dados brutos, então o uso do modelo é livre; a restrição de dados só morde se formos **re-treinar** com os datasets. ⚫ (recomendo confirmação jurídica antes de comercializar).

---

### 3.6 RECOMENDAÇÃO FORTE: o primeiro caso de uso patológico deve ser o **nódulo pulmonar** 🔵

**Por quê o nódulo pulmonar vence todos os critérios simultaneamente:**

1. **Modelo pré-treinado gratuito, dentro da ferramenta já instalada.** `TotalSegmentator lung_nodules` é **Apache-2.0** e roda no `segmentacao.py` **que já existe**. Nenhum outro caso patológico tem modelo (a) gratuito comercialmente, (b) que gera *máscara* (não só box), e (c) já embutido na stack. Fígado/derrame são restritos; detecção MONAI só dá box; tumor cerebral/renal exigiria MONAI+treino. Menor impacto possível na stack atual — o critério-mestre do projeto.

2. **Contraste de imagem robusto.** Nódulo sólido (HU alto, ~+30 a +100) dentro de pulmão aerado (~−700 a −900 HU) é **um dos maiores contrastes naturais de toda a radiologia**. Segmentação é muito mais estável e menos dependente de contraste IV do que tumor de fígado (parênquima ~+40 a +60 vs. tumor ~+20 a +40 — contraste baixo, exige fase venosa correta). Menor risco de falha silenciosa.

3. **Encaixe perfeito no pipeline torácico existente.** O VRmed **já tem preset tórax** e já produz pulmão/lobos/coração. Adicionar `lung_nodules` **e** `lung_vessels` (também Apache-2.0) dá, no mesmo exame, **nódulo + artérias/veias/vias aéreas** — exatamente o par necessário para a "relação espacial" da §3.4, sem nenhum dado ou órgão novo.

4. **Cadeia máscara→malha reaproveitada 100%.** Máscara do nódulo → mesma pipeline → GLB "nodulo_1". Zero reconstrução nova (com o ajuste de sigma para objeto pequeno, §3.3).

5. **Relação espacial de altíssimo valor clínico e didático.** Distância nódulo↔vaso e nódulo↔brônquio, lobo, volume e taxa de crescimento são **exatamente as variáveis de decisão do LungRADS / Fleischner** (seguir, biopsiar, ressecar). Em VR, ver o nódulo em tamanho real, cortar o volume e medir a distância ao vaso é uma narrativa que o laudo 2D não entrega bem. Alto valor percebido, história de produto limpa.

6. **Ecossistema de validação maduro.** LIDC-IDRI/LUNA16 dão ground truth público para checar a segmentação antes de mostrar a paciente/médico (útil para o QA que o projeto ainda não tem — não há `validar-segmentacao.py`).

**Segundo lugar (registro):** `cerebral_bleed` (hemorragia intracraniana) é **Apache-2.0** e clinicamente altíssimo, mas está **fora do foco torácico atual** — exigiria preset e anatomia de cabeça novos; deixar para depois.

**O que NÃO fazer primeiro:** fígado/lesão hepática (licença restrita + contraste fraco + dependência de fase de contraste), e qualquer coisa que exija treino (🔴).

**Caveat regulatório/clínico obrigatório ⚫:** o output é **assistivo/educacional**, não diagnóstico. O modelo tem falsos-positivos/negativos (nenhuma métrica Dice/HD95 é medida no VRmed hoje — `validar-segmentacao.py` não existe), a suavização distorce volume de objeto pequeno, e não há anonimização (pydicom ausente). Qualquer exibição de "nódulo detectado" precisa de **disclaimer explícito**, e a posição no modelo é uma **estimativa da malha**, não medição certificada. Antes de qualquer uso além de demo, é preciso: (i) `requirements.txt`/ambiente reprodutível, (ii) validação quantitativa contra LIDC-IDRI, (iii) rótulo "não é dispositivo médico".

**Roteiro mínimo de implementação (menor diff):**
1. 🔵 `segmentacao.py`: habilitar tasks `lung_nodules` + `lung_vessels`.
2. 🟡 `malha.py`: sigma adaptativo p/ objeto pequeno; gerar GLB da lesão.
3. 🟡 novo passo (poucas linhas, scipy+trimesh): distância nódulo↔vaso/vias, volume (reusa `metricas.py`), lobo por sobreposição.
4. 🟡 `manifest.json` + `ClinicaViewer.tsx`: incluir malha "nodulo" e rótulo `Text3D` com distância/volume (infra de rótulo e VR já existe).

## 4. Comparação temporal (exame anterior × atual)

**Pergunta central:** dá para pegar a TC de 2025 e a de 2026 do mesmo paciente e afirmar com honestidade *"lesão 12 mm → 14,2 mm, volume +18%, distância ao vaso −3,2 mm"*, pintando 🔴 cresceu / 🟢 estável / 🟡 nova?

Resposta curta e honesta: **a base técnica existe e é open source (e boa parte já está instalada no VRmed via SimpleITK), mas a parte difícil não é registrar — é *saber quando a mudança medida é real e quando é ruído de registro/scanner/partial-volume*.** Abaixo separo o que dá para fazer de forma confiável do que seria irresponsável cravar clinicamente.

### 4.1 Onde o VRmed está hoje (âncora no código real)

- O pipeline processa **um exame por vez**: `ingestao.py` grava `ct.nii.gz` (int16, RAS, HU corrigido), `segmentacao.py` roda TotalSegmentator, `malha.py`/`tc-para-vrmed.py` viram GLB. **Não há noção de "paciente com N exames"**, nem armazenamento de série temporal, nem `manifest.json` com data/timepoint.
- **Não existe registro (alinhamento) em lugar nenhum.** `ingestao.py` faz LPS→RAS e *avisa* sobre reamostragem isotrópica mas **não aplica** — ou seja, dois exames do mesmo paciente saem em grades voxel potencialmente diferentes (spacing/origin/direção diferentes). Isso é exatamente o que registro resolve.
- O viewer clínico compara nada temporalmente: carrega um GLB e corta com 1 plano. Achados de pulmão são *hotspots aproximados por limiar de HU em modelo ilustrativo*, não medições na malha real.
- **SimpleITK já é dependência instalada** (usado só para ler DICOM/NIfTI). O `SimpleITK` traz o *ImageRegistrationMethod* completo (rígido, afim, B-spline, Demons, métricas de mutual information) — **a ferramenta de registro que precisamos já está no `import`, só não é chamada.** 🟢/🟡

> Conclusão de contexto: comparação temporal é **feature nova de pipeline** (🟠), mas construída em cima de uma dependência que já temos (🟡), não uma reescrita de stack.

### 4.2 A cadeia técnica correta (e onde cada peça é confiável)

Para dizer "12→14,2 mm" honestamente, a ordem é: **normalizar → registrar → medir na mesma referência → quantificar incerteza → só então colorir.**

#### Passo 1 — Normalização e grade comum (🟡 dá para fazer com o que temos)
Antes de qualquer registro, os dois volumes precisam existir e ser comparáveis:
- **Reamostrar para grade isotrópica comum** (ex.: 1×1×1 mm) com `sitk.Resample`. Isso é justamente o passo que `ingestao.py` hoje só *avisa*. Sem isso, "+18% de volume" pode ser só diferença de spacing.
- HU já é normalizado (RescaleSlope/Intercept) — bom. Mas **HU absoluto varia entre scanners/protocolos** (kVp, kernel de reconstrução, contraste iodado). Isso não quebra o registro, mas **contamina qualquer medida baseada em intensidade** (ex.: "densidade da lesão mudou").
- **Requisito não-técnico**: guardar `ct.nii.gz` de cada exame com identificador de paciente + data. Hoje isso não é persistido (sem banco, sem upload). ⚫/🟠

#### Passo 2 — Registro rígido → afim → deformável (🟡 SimpleITK já cobre)
A prática consolidada é registro **multi-estágio, do mais restrito ao mais flexível**:

| Estágio | Graus de liberdade | Para quê serve | Risco |
|---|---|---|---|
| **Rígido** (6 DOF) | rotação+translação | corrigir posição/pose do paciente na mesa | baixo, confiável |
| **Afim** (12 DOF) | +escala+cisalhamento | corrigir zoom/FOV, pequenas diferenças de protocolo | baixo–médio |
| **Deformável / DIR** (B-spline, Demons) | campo denso de deslocamento | respiração, enchimento de bexiga/intestino, mudança de peso, órgãos moles | **alto — pode "inventar" ou "apagar" mudança real** |

- SimpleITK faz os três nativamente (mutual information + gradient descent + esquema multi-resolução). Erros típicos de DIR em tórax reportados na literatura ficam na casa de **~2,4–2,7 mm** (B-spline/Demons), com trabalhos citando alvo de acurácia **≤ 2 mm (0,20 cm)** para aplicações exigentes. [SimpleITK/ITK B-spline & Demons](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4128373/), [avaliação de DIR em tórax](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3885126/)
- **A armadilha central do deformável**: um DIR "bem-sucedido" (imagens ficam parecidas) pode ter **deformado a própria lesão para casá-la com o exame antigo**, escondendo o crescimento que você queria medir. Por isso, para *medir crescimento de lesão*, o mais seguro é **registrar rígido/afim a região ao redor** e medir a lesão nesse referencial — não deformar em cima da lesão.

#### Passo 3 — Alternativa deep learning (🔵 integrar externo, 🔴 se treinar do zero)
- **MONAI** oferece framework de registro por deep learning, incl. **VoxelMorph** (`monai.networks.nets.VoxelMorph`), rápido e não-supervisionado; MONAI absorve pesquisa do VoxelMorph/DeepReg. [MONAI networks](https://docs.monai.io/en/latest/networks.html), [MONAI registration blog](https://medium.com/pytorch/monai-starts-to-explore-learning-based-medical-image-registration-ab6b143840b7), [VoxelMorph](https://deepai.org/publication/voxelmorph-a-learning-framework-for-deformable-medical-image-registration)
- Mas: MONAI **não está instalado** (a memória do projeto confirma MONAI/nnU-Net ausentes) e VoxelMorph em geral precisa de **treino/tuning por região anatômica**. Bom para longitudinal abdominal em pesquisa ([DIR longitudinal abdominopélvica não-supervisionada](https://arxiv.org/pdf/2005.07545)), **arriscado como caixa-preta clínica**. Para o VRmed, SimpleITK clássico é a escolha lazy e defensável; DL fica como P2.

#### Outras ferramentas open source (🔵)
- **SimpleElastix / itk-elastix** — bindings Python do elastix; rígido/afim/B-spline muito robustos e amplamente citados, encaixam como bloco dentro de pipelines SimpleITK (mesmo ecossistema ITK). [SimpleElastix](https://simpleelastix.github.io/), [itk-elastix (SciPy)](https://proceedings.scipy.org/articles/gerudo-f2bc6f59-00d)
- **ANTs / ANTsPy** — também ITK-based, forte em grande deformação e normalização. [contexto ANTs](https://www.opensourceimaging.org/project/simpleelastix/)
- **PlatiPy** — wrappers prontos de registro sobre SimpleITK, útil como referência de API. [PlatiPy registration](https://pyplati.github.io/platipy/registration.html)

Recomendação: **ficar em SimpleITK puro** (já instalado, sem dependência nova) e só considerar SimpleElastix se o B-spline do SimpleITK se mostrar instável. 🟡

### 4.3 Como medir cada número pedido

- **Diâmetro "12→14,2 mm"**: medir na **máscara de segmentação registrada**, não na malha suavizada. ⚠️ Lembrar que `malha.py` documenta **perda de 13–19% de volume/relevo** pela suavização gaussiana → **nunca medir tamanho de lesão no GLB**, sempre no volume/máscara. 🟡 (máscara existe) / ⚫ (medida precisa exige rigor)
- **Volume "+18%"**: `metricas.py` já calcula volume em mL a partir de máscara — reusar em dois timepoints e comparar. Só é confiável se (a) grade reamostrada igual, (b) mesma versão/preset de TotalSegmentator nos dois exames (senão a diferença pode ser da segmentação, não do paciente). 🟡
- **"Distância ao vaso −3,2 mm"**: distância entre superfícies de duas máscaras (lesão × vaso) no exame registrado — `scipy.ndimage.distance_transform_edt` ou distância ponto-a-malha em trimesh. Viável, mas herda toda a incerteza de segmentação + registro. 🟡/🟠
- **Código de cor 🔴/🟢/🟡**: só é honesto **se o threshold de "mudou" for maior que a incerteza combinada** (ver 4.4). 🟠

### 4.4 O que dá para afirmar com confiança × o que é arriscado

**✅ Confiável (dá para mostrar):**
- **Alinhar** os dois exames e mostrar lado a lado / overlay (rígido+afim é robusto). 🟡
- **Lesão nova** que não existia antes (🟡 "novo") — desde que não seja artefato de FOV/segmentação. Mudanças **grandes e inequívocas** (ex.: nódulo dobrou de tamanho, muito acima do erro).
- **Direção da tendência** ("cresceu vs estável") para alterações claramente acima do ruído.
- Overlay de campo de deformação / diferença de máscaras como **ferramenta de triagem visual** para o médico, explicitamente rotulada como aproximação.

**⚠️ Arriscado — não cravar sem validação clínica (⚫/🔴):**
- **Precisão de 1 casa decimal ("14,2 mm", "−3,2 mm", "+18%")**: sugere exatidão que o pipeline não tem. O **erro de registro (~2 mm) pode ser maior que a mudança real**, e a literatura de radioterapia é explícita: *não há consenso na comunidade sobre como quantificar a incerteza do DIR nem thresholds que separem um bom registro de um ruim*, e o DIR é um problema **mal-posto** cuja qualidade depende do algoritmo e do input. [Review de incertezas de DIR (Phys Med Biol)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10725576/), [framework de validação de DIR](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3732001/)
- **Partial volume**: em spacing grosso, um voxel na borda mistura lesão+tecido → medida de tamanho/volume oscila só por reamostragem.
- **Variabilidade inter-scanner/protocolo**: kernel de reconstrução, espessura de corte, contraste e kVp diferentes entre 2025 e 2026 mudam HU e bordas → parte do "+18%" pode ser do scanner, não do tumor.
- **Deformável escondendo a verdade**: DIR agressivo pode deformar a lesão e zerar artificialmente a diferença (ou criá-la).
- **Medir no GLB suavizado** (erro de 13–19% embutido) — proibido para números clínicos.

**Mitigações honestas (🟠 desenvolver):**
1. **Reportar incerteza junto do número**: "14 ± 2 mm" em vez de "14,2 mm". Sem barra de erro, o número é marketing.
2. **Inverse Consistency Error (ICE)** como QA automático do registro (registrar A→B e B→A; se não bate, registro é ruim) — método padrão da literatura. [Review de incertezas de DIR](https://pmc.ncbi.nlm.nih.gov/articles/PMC10725576/)
3. **Threshold de significância**: só pintar 🔴/🟢 quando |mudança| exceder o erro estimado; caso contrário, mostrar "estável / dentro da margem".
4. **Travar consistência de segmentação**: mesma versão/preset de TotalSegmentator nos dois timepoints, senão a diferença é do modelo.
5. **Alinhar RECIST/critérios clínicos**: crescimento tumoral clínico segue RECIST (diâmetro maior em corte axial), não volume 3D — o número que o médico usa é padronizado; entregar volume 3D como *complemento*, não substituto.

### 4.5 Recomendação de implementação (menor impacto na stack)

| Fase | O quê | Classe | Depende de |
|---|---|---|---|
| **P0** | Persistir `ct.nii.gz` + máscaras por paciente/data (não só o GLB) | 🟠 | armazenamento local; hoje inexistente |
| **P0** | Reamostragem isotrópica comum (o passo que `ingestao.py` só avisa) | 🟡 | SimpleITK (já temos) |
| **P1** | Registro rígido+afim entre timepoints com `sitk.ImageRegistrationMethod`; overlay no viewer | 🟡 | SimpleITK (já temos) |
| **P1** | Diff de máscaras + Δvolume via `metricas.py`, **com incerteza reportada** | 🟡 | reuso de `metricas.py` |
| **P1** | QA automático de registro (ICE) antes de mostrar qualquer número | 🟠 | SimpleITK |
| **P2** | DIR B-spline restrito à região peri-lesão (não sobre a lesão) | 🟡/🔴 | SimpleITK |
| **P2** | Registro por DL (MONAI/VoxelMorph) se DIR clássico falhar | 🔵/🔴 | instalar MONAI (ausente) |
| **⚫ Bloqueante clínico** | Validação (Dice/HD95/landmarks), disclaimers, não usar como diagnóstico | ⚫ | `validar-segmentacao.py` não existe hoje |

**Veredito:** tecnicamente **viável e barato de começar** (SimpleITK já está no projeto; o gargalo é *persistir séries por paciente* e *reamostrar*, não a matemática de registro). Mas o produto só é honesto se **entregar a comparação com incerteza explícita e evitar decimais falsos**: mostrar "cresceu ~2 mm (margem ±2 mm)" e overlay visual é defensável; cravar "14,2 mm, +18%, −3,2 mm" como fato clínico, sem validação Dice/HD95 e QA de registro, seria vender precisão que o pipeline não possui.

**Fontes:** [SimpleITK B-spline/Demons (PMC4128373)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4128373/) · [Avaliação de DIR em tórax (PMC3885126)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3885126/) · [DIR longitudinal abdominopélvica por DL (arXiv 2005.07545)](https://arxiv.org/pdf/2005.07545) · [Review e recomendações sobre incertezas de DIR (PMC10725576)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10725576/) · [Framework de validação de DIR (PMC3732001)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3732001/) · [MONAI networks/VoxelMorph](https://docs.monai.io/en/latest/networks.html) · [MONAI registration (blog PyTorch)](https://medium.com/pytorch/monai-starts-to-explore-learning-based-medical-image-registration-ab6b143840b7) · [VoxelMorph](https://deepai.org/publication/voxelmorph-a-learning-framework-for-deformable-medical-image-registration) · [SimpleElastix](https://simpleelastix.github.io/) · [itk-elastix (SciPy Proceedings)](https://proceedings.scipy.org/articles/gerudo-f2bc6f59-00d) · [PlatiPy registration](https://pyplati.github.io/platipy/registration.html)

## 5. Modelo 3D específico do paciente vs. Gêmeo Digital do paciente

> **TL;DR** — O VRmed hoje produz **modelos 3D específicos do paciente** (malhas estáticas derivadas de *um* exame). Isso **não** é um *digital twin*. "Gêmeo digital" implica um modelo **vivo, multimodal, atualizável, com estado e capacidade preditiva/simulação**, ligado a uma identidade de paciente persistente. O VRmed deve mirar **"modelo específico do paciente" honesto agora**, com o *twin* como norte de longo prazo — e evitar usar a palavra "gêmeo digital" no marketing até cumprir requisitos que hoje não existem.

### 5.1 As duas definições, sem buzzword

O termo "gêmeo digital" tem definição técnica consolidada, não é sinônimo chique de "modelo 3D". A definição de referência (National Academies, adotada pela FDA no simpósio FDA/MDIC de 2024) é:

> "um conjunto de construtos virtuais de informação que **imita a estrutura, o contexto e o comportamento** de um sistema natural/engenheirado, é **dinamicamente atualizado com dados do seu gêmeo físico**, tem **capacidade preditiva** e **informa decisões** que geram valor." — [NASEM / FDA-MDIC 2024](https://iopscience.iop.org/article/10.1088/2516-1091/ae1c05)

Contraste direto com um modelo 3D:

| Dimensão | Modelo 3D específico do paciente | Gêmeo digital do paciente |
|---|---|---|
| Origem | Reconstrução única de 1 exame (CT/MRI) | Modelo computacional vinculado ao paciente real |
| Temporalidade | **Estático** — foto de um instante | **Vivo** — atualiza com novos dados/sensores |
| Conteúdo | Geometria (anatomia + patologia visível) | Geometria **+ estado fisiológico + parâmetros + histórico** |
| Multimodalidade | Uma modalidade por reconstrução | Fusão CT+MRI+PET+laboratório+wearables |
| Capacidade | Visualizar, medir, cortar | **Simular, prever, testar intervenção in silico** |
| Identidade | Arquivo por exame | Entidade "paciente" persistente e versionada |

A própria literatura é explícita: *"uma reconstrução 3D única a partir de uma TC é útil para ensaio cirúrgico, mas é uma simulação estática a menos que o modelo continue ingerindo novas imagens ou dados fisiológicos"* ([RaftLabs, 2026](https://www.raftlabs.com/blog/digital-twins-in-healthcare); [Sermo](https://www.sermo.com/resources/digital-twins/)). O gêmeo digital em saúde é ainda mais difícil que na indústria porque *"o sistema modelado é biologicamente adaptativo, parcialmente observável… o estado verdadeiro do paciente não pode ser medido diretamente e precisa ser inferido sob incerteza"* ([Digital twins in healthcare IoT, ScienceDirect 2025](https://www.sciencedirect.com/science/article/pii/S2667295225000443); scoping review em [npj Digital Medicine 2024](https://www.nature.com/articles/s41746-024-01073-0)).

**Onde o VRmed cai hoje:** cada entrada do `public/pacientes/manifest.json` é **um exame → um GLB** (`slug`, `titulo`, `glb`, `dataProcessamento`, `fonteDados`). Não há entidade "paciente", não há duas modalidades do mesmo indivíduo, não há histórico. Confirmado no código: os três casos (`cta-cardio`, `torax-alta`, `torax-completo`) são exames independentes, alguns de fontes públicas diferentes (Slicer, TCIA/LIDC-IDRI). Isso é, de forma inequívoca, um **modelo 3D específico do paciente** — e nem "por paciente", mas "por exame".

### 5.2 O que PRECISARIA existir para o VRmed dizer honestamente "gêmeo digital"

Requisitos mínimos de um *patient digital twin*, mapeados no VRmed real:

| # | Requisito | Estado no VRmed | Marcador |
|---|---|---|---|
| R1 | **Geometria específica do paciente** (malha derivada do exame real) | Já existe: pipeline `tc-para-vrmed.py` → GLB por estrutura, cor por HU real | 🟢 |
| R2 | **Patologia junto da anatomia** | Parcial e ilustrativo: `achados-pulmao.py` detecta por **limiar de HU (não IA)** e pinta um **modelo ilustrativo**, não a mesh real | 🟡 |
| R3 | **Medidas quantitativas versionadas por exame** | `metricas.py` calcula volume mL/bbox/componentes, mas **não** é embutido no manifest nem versionado; sem Dice/HD95 | 🟡 |
| R4 | **Identidade de paciente persistente** (1 paciente ↔ N exames) | Não existe: manifest é indexado por exame, não por paciente | 🟠 |
| R5 | **Atualização temporal** (novo exame atualiza o mesmo twin, comparação longitudinal) | Não existe: cada GLB é imutável e isolado | 🟠 |
| R6 | **Multimodalidade real** (CT+MRI+PET do mesmo paciente) | `ingestao.py` lê DICOM/NRRD/NIfTI mas processa **uma série por vez**; sem MRI/PET no fluxo | 🟠 |
| R7 | **Fusão/registro entre modalidades** (co-registro rígido/deformável) | Não existe: sem VTK/ANTs/SimpleITK-registration; conversão é só LPS→RAS de uma série | 🔵/🟠 |
| R8 | **Metadados clínicos** (idade, diagnóstico, laudo estruturado) | Não existe; e **sem anonimização** (pydicom ausente) — bloqueia até ingerir dado clínico real | 🟠/⚫ |
| R9 | **Estado fisiológico / parâmetros** (pressão, fluxo, condução) | Não existe; nenhuma variável fisiológica é modelada | 🔴 |
| R10 | **Capacidade preditiva / simulação in silico** (FEA, CFD, eletrofisiologia) | Não existe; é o coração da definição de twin e é problema de pesquisa | 🔴 |
| R11 | **Ingestão contínua de dados** (sensores/wearables/EHR ao vivo) | Não existe; não há backend real, banco, nem upload (só 2 rotas serverless efêmeras) | 🟠 |
| R12 | **Validação/credibilidade regulatória** (V&V, credibilidade ASME V&V 40, uso clínico) | Não existe; sem validação Dice/HD95, sem anonimização, sem marcação CE/FDA | ⚫ |

**Leitura do mapa:** o VRmed tem **R1 sólido** e R2/R3 a meio caminho. Tudo de R4 em diante — identidade, tempo, multimodalidade, fusão, estado, simulação — está ausente. Ou seja, falta **exatamente o que define um twin** (dinamismo, estado, predição). Os itens 🔴 (R9, R10) e ⚫ (R8, R12) não são "mais código": são pesquisa e regulação. Isso é coerente com o estado do campo — mesmo projetos maduros como o **Living Heart** (Dassault) são twins de *modelo mecanístico validado*, usados para testar dispositivos in silico, e ainda assim restritos a domínios estreitos ([PNAS Nexus 2025](https://academic.oup.com/pnasnexus/article/4/5/pgaf123/8116190); [FDA-MDIC 2024](https://iopscience.iop.org/article/10.1088/2516-1091/ae1c05)).

### 5.3 Uma escala honesta de maturidade (onde marcar a linha)

Para não cair em buzzword, vale nomear os degraus:

1. **Modelo 3D anatômico ilustrativo** — não é do paciente (as 32 GLBs de prateleira). 🟢
2. **Modelo 3D específico do exame** — malha do exame real, geometria fiel. **← VRmed está aqui.** 🟢
3. **Modelo específico do paciente longitudinal** — identidade + N exames + medidas versionadas + comparação temporal. 🟠 (alcançável)
4. **Réplica multimodal registrada** — CT+MRI+PET fundidos + metadados clínicos anonimizados. 🔵/🟠
5. **Gêmeo digital (twin)** — tudo acima + estado fisiológico + simulação preditiva + atualização contínua + credibilidade validada. 🔴/⚫

O salto honesto e de baixo risco é **2 → 3**. O salto 4 → 5 é onde mora quase todo o risco de pesquisa e regulatório.

### 5.4 Recomendação: mirar "modelo específico do paciente" honesto agora

**Adotar publicamente o termo "modelo 3D específico do paciente" (patient-specific model), não "gêmeo digital".** Motivos:

- **É verdade verificável.** O VRmed reconstrói geometria fiel do exame real (R1 🟢). Chamar de twin seria *overclaim* — e overclaim em saúde tem custo de credibilidade e, eventualmente, regulatório (⚫).
- **O gap para twin é definidor, não cosmético.** Faltam estado fisiológico e simulação preditiva (R9/R10 🔴) — sem isso, por definição não é twin.
- **Menor impacto na stack.** Ficar em "modelo específico do paciente" não exige reescrever nada: aproveita o pipeline atual como está.

**Passos de baixo custo que aproximam do degrau 3 (o norte de curto prazo), com o que já existe:**

- 🟡 **Embutir `metricas.py` no manifest** (volume mL, nº de componentes por estrutura) — a máquina já calcula; falta só serializar no `manifest.json`. Transforma "malha bonita" em "malha com medida", que é o primeiro atributo quantitativo versionável. Menor diff possível.
- 🟠 **Reindexar o manifest por paciente** (`paciente → [exames]` em vez de lista plana de exames). É mudança de schema estático, sem backend. Habilita R4/R5 (identidade + comparação temporal) — o `torax-alta` vs `torax-completo` já é, de fato, um estudo longitudinal disfarçado de dois arquivos soltos.
- ⚫ **Antes de qualquer dado de paciente real:** anonimização (pydicom/dcm2niix ausentes) e validação Dice/HD95. São pré-condições clínicas, não features.

**Norte de longo prazo (twin):** manter como visão, não como claim. O caminho realista começa por **um único domínio mecanístico validado** (ex.: hemodinâmica cardíaca sobre a malha que já se produz), seguindo o padrão Living Heart / in silico trials — nunca "twin genérico do corpo". Isso é 🔴 (pesquisa) + ⚫ (regulatório) e depende de parceria clínica/acadêmica, não de sprint de engenharia.

**Frase honesta para o produto:** *"o VRmed reconstrói um modelo 3D do exame do paciente, fiel à densidade real da tomografia"* — precisa, defensável, e já verdadeira hoje. Reservar "gêmeo digital" para quando (e se) R9/R10/R12 existirem.

---

**Fontes:**
- [Computational modeling and simulation for medical devices: FDA/MDIC 2024 Symposium — IOPscience](https://iopscience.iop.org/article/10.1088/2516-1091/ae1c05)
- [Digital twins for health: a scoping review — npj Digital Medicine 2024](https://www.nature.com/articles/s41746-024-01073-0)
- [Digital twins in healthcare IoT: a systematic review — ScienceDirect 2025](https://www.sciencedirect.com/science/article/pii/S2667295225000443)
- [The future of in silico trials and digital twins in medicine — PNAS Nexus 2025](https://academic.oup.com/pnasnexus/article/4/5/pgaf123/8116190)
- [Digital Twins in Healthcare: What They Actually Do — RaftLabs 2026](https://www.raftlabs.com/blog/digital-twins-in-healthcare)
- [Digital Twins in Healthcare — Sermo](https://www.sermo.com/resources/digital-twins/)
- [Patient-Specific Articulated Digital Twins from a Single Full-Body CT Scan — arXiv](https://arxiv.org/pdf/2607.02156)

## 6. VR — "entrar dentro do exame"

O objetivo desta frente é sair do "GLB flutuando na frente do usuário" para "o médico/estudante entra na anatomia do paciente". O VRmed já tem a base de WebXR funcionando; o que falta é (a) **escala real**, (b) **locomoção para entrar de fato no modelo**, (c) **as ferramentas clínicas — corte, medição, rótulo — replicadas dentro da sessão**, e (d) **uma disciplina de performance** que hoje simplesmente não existe em runtime. Esta seção ancora cada recomendação no código real e classifica pelo esforço.

### 6.0 O que já existe (verdade de base do código)

Confirmado lendo `components/viewer/Scene.tsx`, `components/clinica/ClinicaViewer.tsx`, `components/viewer/XRManipulation.tsx`, `components/viewer/XRButton.tsx` e `lib/xr-store.ts`:

- 🟢 **Sessão immersive-vr** via `@react-three/xr` v6 (`XR`, `XROrigin`, `useXR`, `createXRStore`), com `XRButton` checando `navigator.xr.isSessionSupported("immersive-vr")` e botão de sair (`SairDoVR`).
- 🟢 **Manipulação do modelo em VR** (`XRManipulation.tsx`): pegar com 1 mão (gatilho lateral / pinça com hand-tracking + histerese), escalar+arrastar com 2 mãos, girar/tombar/aproximar pelos analógicos, botão A/X para reset — código maduro, com deadzone, clamp de delta ao repor o headset e reuso de vetores por quadro. **É um ativo forte; não reescrever.**
- 🟢 **Corte por 1 plano** (axial/coronal/sagital) com `localClippingEnabled` + `THREE.Plane`, **envelope translúcido** do coração, **clique-identifica** por nome de malha (com fallback para o `event` quando o raycast do R3F devolve interseções vazias em VR — detalhe já resolvido).
- 🟢 **Rótulo em VR como `Text3D`** (DOM é invisível dentro da sessão) e **palco de referência** (chão/grade/anel) para não cair no "vazio preto".
- 🟢 **Higiene de performance parcial**: em VR o `Scene.tsx` desliga sombras, força `dpr={1}`, `frameloop="always"`, remove `OrbitControls`/`CameraRig`/hotspots DOM/`ContactShadows`; a store "endurecida" (`lib/xr-store.ts`) desliga anchors/mesh/plane/hit-test/depth e usa `foveation: 0.5`.

**Três lacunas estruturais que atravessam toda a seção:**

1. ⚠️ **Duas stores XR divergentes.** `ClinicaViewer` usa a store endurecida `obterXRStore()` (com `foveation: 0.5`, perfis locais, teleporte/grab desligados). Mas o visualizador principal `Scene.tsx` cria **outra** store inline: `createXRStore({ emulate: false })` — **sem `foveation`, sem `baseAssetPath` local, sem o endurecimento**. Ou seja, o viewer principal entra em VR sem foveação explícita e buscando perfis de input na CDN externa. É a primeira coisa a unificar (🟡, trivial).
2. ⚠️ **Nenhuma guarda de triângulos em runtime.** O `CLAUDE.md` avisa que `myology.glb` tem 982k tris e é "proibido em VR", mas isso é uma regra humana, não código. Nada impede carregar um GLB pesado numa sessão e derrubar o frame-rate no Quest.
3. ⚠️ **As ferramentas clínicas são DOM-only.** Corte, slider de posição, toggle de envelope, alternância mapa/malha estão todos atrás de `!inSession` — **desaparecem ao entrar em VR**. Hoje quem está de headset não consegue mover o plano de corte nem esconder o envelope. Isso é o coração do "entrar no exame" e está faltando.

---

### 6.1 Escala real (1:1 mm) — "o coração do tamanho do coração"

Hoje o modelo é **normalizado**: `normalizeContent(group)` encaixa em ±1 e o pivô aplica `scale={1.4}` (viewer da clínica) — resultado bonito para vitrine, mas **descolado da anatomia real**. O pipeline já exporta em **metros, Y-up** (`tc-para-vrmed.py` via `trimesh.Scene.export`), então o dado para 1:1 já existe; só é jogado fora na visualização.

- 🟡 **Modo "escala real"**: pular `normalizeContent` e desenhar o GLB nas unidades nativas (metros), posicionando o `XROrigin` a ~1,5–2 m. Um coração de ~12 cm aparece com 12 cm; uma aorta com o calibre real. É a diferença didática entre "objeto" e "órgão". Baixo custo: é um branch no preparo do modelo + um HUD com a régua de escala.
- 🟡 **Toggle escala didática ⇄ escala real**: manter o gesto de 2 mãos para ampliar (já existe em `XRManipulation`), mas ancorar o "reset" (botão A/X) na escala **1:1 verdadeira**, com selo visível ("1:1" / "×3"). Reaproveita `home.current` do `XRManipulation`.
- ⚫ **Calibração/validação**: a malha carrega perdas documentadas (13–19% de volume/relevo pela suavização gaussiana — ver pipeline). "Escala real" precisa de um aviso de que a *dimensão* é fiel mas o *relevo fino* < 3 mm não é — senão vira alegação clínica indevida.

### 6.2 Exploração interna — "caminhar dentro do exame" (locomoção)

Este é o item que mais falta para o slogan. Hoje o `XROrigin` é **fixo** (`position={[0, FLOOR_Y, 2.4]}`), a store desliga `teleportPointer` e `grabPointer`, e a única forma de "entrar" é ampliar o modelo com as duas mãos até ele te engolir. Funciona como truque, mas não é navegação.

- 🟡 **Teleporte** (o padrão de conforto em VR): `@react-three/xr` v6 traz `TeleportTarget` + `onTeleport` movendo o `XROrigin`, e a store aceita `controller: { teleportPointer: true }`. Como a store atual **já** expõe `teleportPointer: false`, é literalmente virar a chave + adicionar um `TeleportTarget` no chão do palco. Baixo risco. ([tutorial oficial](https://pmndrs.github.io/xr/docs/tutorials/teleport))
- 🟡 **Locomoção suave por analógico** já é meia-implementável: `XRManipulation` já lê `xr-standard-thumbstick` com deadzone e curva quadrática. Hoje o analógico gira o *modelo*; um segundo modo (ou o analógico esquerdo) poderia transladar o **`XROrigin`** em vez do modelo. ⚠️ Locomoção suave causa enjoo — oferecer teleporte como padrão e o suave como opção, com **snap-turn** (giro em degraus) em vez de giro contínuo. ([Samsung Internet: VR locomotion em three.js](https://medium.com/samsung-internet-dev/vr-locomotion-740dafa85914))
- 🟡 **"Encolher-se para dentro"**: como o gesto de 2 mãos escala o modelo em torno do ponto médio, ampliar 5–6× (o `MAX_SCALE` já é 6) coloca o usuário dentro da cavidade — combinado com `mat.side = DoubleSide` (já setado no corte) as paredes internas aparecem. Falta só um "modo interior" que suba a intensidade da luz e reduza `MIN_HEAD_DISTANCE`.
- 🟠 **Conforto/vinheta**: para evitar enjoo ao entrar/ampliar, uma vinheta de túnel (escurecer a periferia durante o movimento) é padrão de indústria e não existe aqui. Precisa de um shader/overlay simples — desenvolvimento próprio, mas pequeno.

### 6.3 Corte, transparência e isolamento **em VR**

Toda a maquinaria existe (`localClippingEnabled`, `THREE.Plane` compartilhado, `clippingPlanes` por material, envelope translúcido, `DoubleSide` na parede interna). O problema é que **os controles são DOM e somem em VR**.

- 🟡 **Grab do plano de corte com o controle**: um "handle" 3D (um disco/seta) preso ao plano; agarrar (reusando a mesma detecção de squeeze/pinça do `XRManipulation`) e arrastar move `plano.current.constant`. Fazer o corte ser uma **ferramenta segurável na mão** ("passar a lâmina pelo órgão") é muito mais forte que um slider. Média complexidade porque exige portar o estado React do corte para dentro do `useFrame`.
- 🟡 **Toggle de camadas/envelope por botão físico**: mapear B/Y para alternar `mostrarEnvelope` e ciclar axial/coronal/sagital — hoje só existe em botão HTML. Reaproveita `isPressed()` do `XRManipulation`.
- 🟡 **Isolar estrutura**: já se sabe qual malha foi clicada (`identifyStructure`). "Isolar" = esconder as irmãs / deixá-las translúcidas. Estado já modelado por camadas no viewer principal (`layers` no Zustand); falta o gatilho em VR (gatilho do controle sobre a estrutura apontada).
- 🔵/🟠 **Corte por caixa/plano arbitrário**: three.js aceita múltiplos `clippingPlanes`; uma "caixa de recorte" (6 planos) segurável daria dissecção livre. Não é padrão pronto — desenvolvimento, mas em cima de API existente.

### 6.4 Medição em VR

**Não existe** — nem em VR nem no desktop clínico (o `metricas.py` calcula volume/bbox **offline**, no pipeline, não em runtime).

- 🟠 **Régua entre dois pontos**: dois toques de gatilho colocam esferas; a distância euclidiana no espaço do modelo, corrigida pela escala atual, vira o comprimento real em mm. Como o pipeline exporta em metros, a conversão é direta **se** o modelo estiver em escala real (ver 6.1). Baixo-médio esforço (é geometria + um `Text3D` com o valor).
- 🟠 **Ângulo/trajetória**: três pontos = ângulo; útil para planejamento (ex.: eixo de uma via). Extensão natural da régua.
- ⚫ **Precisão clínica**: qualquer número exibido carrega as perdas do pipeline (suavização, decimação ~150k, afastamento de −0,15 mm nas câmaras). Medição em VR deve ser rotulada **"aproximada, educacional"** — não é ferramenta de laudo.

### 6.5 Seleção, rótulos, crosshair e slice-plane em VR

- 🟢 **Seleção + rótulo 3D** já funcionam (clique-identifica + `Text3D`). 
- 🟡 **Crosshair/ray pointer persistente**: a store hoje desliga `grabPointer` e usa "só o ponteiro de raio" (comentário em `xr-store.ts`). Dá para exibir um retículo no ponto de impacto do raio para pré-visualizar o que será selecionado/medido — barato.
- 🟡 **Rótulo que segue a estrutura**: hoje o `Text3D` fica fixo em `[0, 1.35, 0.6]`; ancorá-lo ao ponto clicado (billboard virado para a câmera) melhora muito a leitura espacial. drei tem `<Billboard>`.
- 🟠 **Slice-plane interativo com preview do "corte" texturizado**: o corte hoje só *remove* geometria. Mostrar, na face do corte, uma amostra real de HU (o pipeline já sabe amostrar HU perto da superfície) aproximaria a experiência de olhar uma "fatia" de TC. É desenvolvimento (ligar dado de HU ao plano), mas é o que mais aproxima "3D" de "exame".

### 6.6 Comparação lado a lado

Existe uma frente 2D/desktop (`app/compare/`, `SplitView.tsx`, `SyncedCameras.tsx`, `ComparePlaceholder.tsx`), mas **não há comparação dentro do VR**.

- 🟡 **Dois modelos no mesmo palco** (ex.: coração normal × patológico — o catálogo já tem 3 pares patológicos): instanciar dois `ModeloPaciente`/`OrganModel` deslocados no X, cada um com seu pivô e `XRManipulation`. Baixo custo estrutural; **atenção à performance** (dois modelos dobram os tris — ver 6.8).
- 🟠 **Manipulação espelhada/sincronizada em VR**: girar um e o outro acompanhar (equivalente VR do `SyncedCameras`). Precisa de um pequeno barramento de estado entre os dois `XRManipulation`.

### 6.7 Vasos, lesões e relação espacial

- 🟢/🟡 **Cada estrutura é uma malha nomeada** (câmaras, artéria pulmonar são malhas próprias). Isso já permite realçar um vaso ou uma lesão por cor/emissivo ao apontá-lo.
- 🟡 **Hotspots de achados em VR**: o `MapaAchados`/`StructureHotspots` já cria pontos de achado (enfisema/lesões por limiar de HU — não IA). Em VR, virar cada achado num marcador 3D flutuante clicável (esfera pulsante + `Text3D`) reusa o dado que já é carregado do JSON de achados.
- ⚫ **Relação espacial vaso↔lesão** é justamente onde o 3D imersivo bate o 2D — mas os achados são **hotspots aproximados** sobre modelo ilustrativo (ou pintados por HU), não segmentação de vaso/lesão real. Vender "relação espacial precisa" seria alegação além do que o pipeline entrega. Manter o selo de "posição aproximada" que o código já mostra.

---

### 6.8 PERFORMANCE de grandes meshes no Quest — o capítulo crítico

Este é o maior risco técnico da frente. **Números de referência (fontes abaixo):**

- Orçamento prático para VR móvel: **~50k–150k triângulos na cena inteira**; embora a GPU do Quest 3 aguente 300k–500k tris **por olho** em bruto, o gargalo real costuma ser **draw calls** (CPU), não triângulos. Mandar muitas malhas separadas derruba o FPS antes de a GPU suar. ([Meta — WebXR Perf Best Practices](https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/), [Meta — Perf Workflow](https://developers.meta.com/horizon/documentation/web/webxr-perf-workflow/), [Low-poly — polygon budgets 2026](https://low-poly.com/blog/polygon-budgets-by-platform-2026))
- Alvo obrigatório: **≥72 FPS**; qualquer lógica por quadro acima de ~2 ms é candidata a corte. ([Meta — WebXR Perf Best Practices](https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/))

**Estado do VRmed vs. isso:**

- ⚠️ **Sem guarda de tris em runtime.** O orçamento de ~150k do pipeline (`fast_simplification.simplify`) só vale para o que passou pelo pipeline; a prateleira tem GLBs como `myology.glb` (982k) marcado "proibido em VR" só por convenção. **Recomendação 🟡 (fazer já):** ao entrar em VR, somar `geometry.index.count/3` de todas as malhas e, acima de um teto (ex.: 300k), **bloquear a entrada** ou trocar por um LOD/aviso. É um `traverse` de poucas linhas.
- ⚠️ **Draw calls não vigiados.** Cada estrutura nomeada é uma malha (`heart_*`, câmaras, etc.). Bom para clique-identifica, ruim para draw calls. **🟠**: para modelos com dezenas de submalhas, oferecer um "merge para VR" (mesclar por material) mantendo um índice nome→faixa de vértices para ainda identificar no clique. Mais trabalhoso porque quebra o `identifyStructure` atual.

**Técnicas, com veredito:**

| Técnica | Suporte hoje | Veredito |
|---|---|---|
| **Draco** (geometria) | 🟢 já usado, decoder local em `/public/draco/` via `useGLTF(path,'/draco/')` | Manter. Reduz download, **não** reduz tris/draw calls na GPU. |
| **meshopt** (`EXT_meshopt_compression`) | 🔵 suportado por three r122+ e drei via `extendLoader`/`MeshoptDecoder`, **não ligado** | Descompressão mais rápida que Draco e compatível; útil, mas exige registrar o `MeshoptDecoder` no `useGLTF`. Ganho marginal sobre Draco já em uso — **baixa prioridade**. ([GLTFLoader docs](https://threejs.org/docs/pages/GLTFLoader.html)) |
| **KTX2 / Basis** (texturas) | 🔵 **ausente** (memória confirma "sem KTX2/meshopt") | **Alto valor no Quest**: fica comprimida na GPU (~10× menos memória de textura). Mas os modelos do VRmed são **cor por vértice**, com poucas/nenhuma textura grande (exceto o "mapa de achados" pintado). Ligar KTX2 só compensa quando houver texturas pesadas. drei `useGLTF` não traz KTX2 pronto — precisa `setKTX2Loader` via `extendLoader`. ([drei #2639](https://github.com/pmndrs/drei/issues/2639), [three forum KTX2](https://discourse.threejs.org/t/how-to-load-a-gltf-that-uses-ktx2-textures-getting-error-setktx2loader-must-be-called-before-loading-ktx2-textures/48792)) |
| **LOD** (`THREE.LOD` / drei `<Detailed>`) | 🟠 ausente | drei `<Detailed distances={[...]}>` troca malha por distância. Útil para comparação/multi-modelo. Exige **gerar** os níveis (rodar o pipeline com orçamentos diferentes, ou decimar no `gltf-transform`). ([drei Detailed]) |
| **Foveação fixa (FFR)** | 🟢 na store da clínica (`foveation: 0.5`), ⚠️ **ausente no viewer principal** | three expõe `xr.setFoveation(0..1)` (0 = full-res, 1 = máx). **🟡 unificar**: aplicar `foveation` também no `createXRStore` do `Scene.tsx`. Ganho de fill-rate quase de graça. ([three WebXRManager](https://threejs.org/docs/pages/WebXRManager.html), [MDN fixedFoveation](https://developer.mozilla.org/en-US/docs/Web/API/XRProjectionLayer/fixedFoveation)) |
| **`setFramebufferScaleFactor`** | 🟡 não usado (só `dpr={1}`) | Permite baixar a resolução do framebuffer XR abaixo de 1 em cenas pesadas. Botão de emergência de fill-rate; expor como "modo desempenho". ([Meta Perf Workflow](https://developers.meta.com/horizon/documentation/web/webxr-perf-workflow/)) |
| **Streaming / progressive loading** | 🟠 ausente (GLBs estáticos em `/public`, `useGLTF` carrega inteiro) | Para o catálogo atual (18 modelos, ~11k–18k tris nos usados em VR) **é overkill — YAGNI**. Só vira necessidade quando houver modelos de paciente grandes. Existe `gltf-progressive` (Needle) como opção externa, mas não recomendo integrar agora. |
| **"Nanite-like" / virtualized geometry** | 🔴 **não existe na web** | Nanite é engine nativa (UE5). Não há equivalente em three.js/WebXR. Não perseguir. |
| **Off-main-thread (loader em worker)** | 🔵 padrão (Draco/meshopt já decodificam em worker) | Manter os decoders em worker evita travar o frame ao carregar. ([surma.dev — OMT three-XR](https://surma.dev/things/omt-for-three-xr/)) |

**Prioridade de performance:** (1) 🟡 unificar store + foveação no viewer principal; (2) 🟡 guarda de tris em runtime antes de entrar em VR; (3) 🟠 merge por material para modelos multi-malha; (4) 🟡 `setFramebufferScaleFactor` como modo desempenho; (5) só depois 🔵 meshopt/KTX2/LOD conforme surgirem modelos grandes.

### 6.9 Limitações reais do Quest 2/3 e o teto do "entrar no exame"

- ⚫/🔴 **Sem volume rendering pesado.** O grande sonho de "entrar no exame" seria *volume rendering* (renderizar o dado bruto da TC, não a malha). No Quest, ray-marching de volume por fragmento em WebGL2/WebXR é **caro demais** para caber no orçamento de fill-rate a 72 FPS com foveação — e o VRmed **não tem volume rendering** (o `volume.py` não existe; tudo é malha). Continuar com **malha decimada** é a escolha certa para VR. Volume rendering fica para o **desktop 2D/2.5D** (ver frentes de viewer clínico — Cornerstone3D/VTK.js/Niivue), não para o Quest.
- **Memória**: Quest 2 tem orçamento de memória apertado; texturas não comprimidas e muitos materiais clonados (o `prepareModel` clona materiais por malha) somam. Vigiar contagem de materiais/texturas.
- **Fill-rate** é o limite dominante em VR (2 olhos em alta densidade de pixels): por isso foveação, framebuffer scale e evitar transparências sobrepostas importam mais que a contagem de tris. ⚠️ O **envelope translúcido do coração** (transparência + `depthWrite:false`) é exatamente o tipo de overdraw a monitorar em VR.
- **HTTPS obrigatório** (já sabido): `navigator.xr` só existe em https/localhost — `XRButton` já degrada com tooltip. Em rede local usar `adb reverse` ou HTTPS.

---

### Roadmap priorizado (o que faz o slogan virar verdade)

1. 🟡 **Unificar a store XR** (`Scene.tsx` usar `obterXRStore()`) → foveação + endurecimento no viewer principal. *Trivial, alto retorno.*
2. 🟡 **Guarda de triângulos em runtime** antes de `enterVR()`. *Poucas linhas, evita o pior bug de campo.*
3. 🟡 **Ferramentas clínicas dentro do VR**: portar corte (handle segurável), toggle de envelope/camadas e isolar-estrutura para botões/gestos — hoje somem em `!inSession`. *É o núcleo do "entrar no exame".*
4. 🟡 **Escala real 1:1** (pular `normalizeContent`, HUD de escala) + 🟡 **teleporte** (`teleportPointer: true` + `TeleportTarget`). *Juntos entregam "andar dentro na dimensão certa".*
5. 🟠 **Medição em VR** (régua/ângulo) com selo "aproximada, educacional".
6. 🟡 **Comparação lado a lado em VR** (normal × patológico do próprio catálogo), vigiando o orçamento de tris.
7. 🟠 **Merge por material + LOD** só quando entrar modelo grande; 🔵 meshopt/KTX2 conforme texturas pesarem.

**Fontes:** [Meta — WebXR Performance Best Practices](https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/) · [Meta — WebXR Performance Optimization Workflow](https://developers.meta.com/horizon/documentation/web/webxr-perf-workflow/) · [Meta — Draw Call Cost Analysis](https://developers.meta.com/horizon/documentation/unity/po-draw-call-analysis/) · [Low-poly — Polygon Budgets by Platform 2026](https://low-poly.com/blog/polygon-budgets-by-platform-2026) · [three.js — WebXRManager (foveation)](https://threejs.org/docs/pages/WebXRManager.html) · [MDN — XRProjectionLayer.fixedFoveation](https://developer.mozilla.org/en-US/docs/Web/API/XRProjectionLayer/fixedFoveation) · [pmndrs/xr — Teleport tutorial](https://pmndrs.github.io/xr/docs/tutorials/teleport) · [pmndrs/xr — Performance](https://pmndrs.github.io/xr/docs/advanced/performance) · [Samsung Internet — VR locomotion em three.js](https://medium.com/samsung-internet-dev/vr-locomotion-740dafa85914) · [three.js — GLTFLoader (KTX2/meshopt)](https://threejs.org/docs/pages/GLTFLoader.html) · [drei #2639 — KTX2 em useGLTF](https://github.com/pmndrs/drei/issues/2639) · [surma.dev — three-XR off-main-thread](https://surma.dev/things/omt-for-three-xr/)

## 7. Análise competitiva

O VRmed vive num espaço disputado por três famílias de produto muito diferentes, e é preciso separá-las antes de comparar honestamente:

1. **Atlas anatômicos** (BioDigital, Complete Anatomy) — modelos idealizados, lindos, mas **não são o paciente**. Web/app, escala e maturidade enormes.
2. **Software clínico de segmentação e planejamento** (Materialise Mimics, 3D Slicer) — trabalham o **DICOM real** do paciente; um é produto maduro e caro com marcação regulatória, o outro é open source gratuito e poderosíssimo, ambos desktop.
3. **Sistemas imersivos/intraoperatórios** (DicomSegVR, CORTEXPLORER MED, Surglasses Caduceus S, HUVANT, mesa Anatomage) — VR/AR/haptics, do estudo educacional até a navegação cirúrgica com clearance da FDA.

O VRmed é um híbrido raro: pega DICOM do paciente → segmenta com IA → gera 3D patient-specific → entrega **no navegador com WebXR, sem instalação**. Quase ninguém ocupa exatamente essa interseção — o único que chega perto é o **DicomSegVR**, e vale estudá-lo de perto.

### Tabela comparativa

Legenda das células: **sim** = capacidade central madura · **parcial** = existe mas limitada/secundária/incerta · **não** = ausente.

| Produto | DICOM | Segmentação IA | Patologia | Patient-specific | 2D↔3D | VR | Comparação temporal | Digital Twin |
|---|---|---|---|---|---|---|---|---|
| **VRmed** (referência) | sim — SimpleITK/GDCM, HU, LPS→RAS | sim — TotalSegmentator (nnU-Net pré-treinado) | parcial — detecção por **limiar de HU**, não IA; hotspots aproximados | sim — pipeline gera GLB do próprio paciente | **não** — sem viewer de slices, sem link 2D↔3D | sim — WebXR (@react-three/xr), no navegador | não | não |
| **DicomSegVR** | sim — DICOM/NIfTI | sim — segmentação IA automática | não | sim — 3D do estudo do usuário | **sim** — dashboard Cornerstone (scrub de slices, RTSTRUCT, MPR na VR) | sim — app nativo Meta Quest, volume raymarched | não | não |
| **HUVANT** | parcial — para gerar modelos | não | não | parcial — simuladores hápticos sob medida | não | parcial — virtual + háptico físico | não | não |
| **Materialise Mimics** | sim — padrão-ouro DICOM | sim — CT Bone AI, coronária semi-auto | parcial — medição/quantificação clínica, não detecção automática | **sim** — uso central (implantes, guias, FEA/CFD) | sim — edição ligada aos cortes | parcial — XR case viewing via cloud | parcial — mask morphing 4D | parcial — FEA/CFD, biomecânica sim-ready |
| **CORTEXPLORER MED** | sim | parcial — cria/edita modelos 3D | não | sim — do exame do paciente | sim — axial/sagital/coronal/diagonal + trajetória | parcial — HMD mixed reality intraoperatório | não | parcial — overlay + tracking de instrumentos ao vivo |
| **Surglasses Caduceus S** | sim | parcial | não | sim | parcial | sim — HMD AR see-through | não | parcial — overlay 3D no paciente em tempo real |
| **Anatomage Table** | sim — carrega CT/MRI do paciente | parcial — casos processados; núcleo é cadáver digitalizado | parcial — biblioteca de casos patológicos | parcial — carrega dados do paciente, mas foco é Visible Human | sim — compara estrutura com corte CT/MRI, overlay | não — mesa autoestereoscópica (3D sem óculos) | parcial — simulação fisiológica (batimento) | não |
| **3D Slicer** | sim | sim — extensões TotalSegmentator/MONAI Auto3DSeg | parcial — radiômica/quantificação via extensões | sim | **sim** — MPR ligado ao 3D (padrão-ouro) | parcial — extensão SlicerVR (OpenXR) | parcial — módulo Sequences (4D) | parcial — pesquisa (CFD, biomecânica via extensões) |
| **BioDigital Human** | não — atlas, não dados do paciente | não | sim — 1000+ modelos de doença/condição | não | não | parcial — visualizações imersivas (incerto quanto a WebXR pleno) | não | não |
| **Complete Anatomy** | parcial — importa/correlaciona MRI/RX; módulo de radiologia (CT/MRI/angio) | não | parcial — conteúdo clínico/patológico curado | não | parcial — correlação radiológica | parcial — histórico de modo VR/AR (incerto na versão atual) | não | não |

Fontes: [DicomSegVR (dicomsegvr.com via busca)](http://www.dicomsegvr.com/) · [Materialise Mimics Innovation Suite](https://www.materialise.com/en/healthcare/mimics-innovation-suite) · [Mimics AI-Enabled Segmentation](https://www.materialise.com/en/healthcare/mimics-innovation-suite/ai-enabled-segmentation) · [CORTEXPLORER MED (ClinicalTrials NCT05269498)](https://clinicaltrials.gov/study/NCT05269498) · [Surglasses Caduceus S](https://surglasses.com/en/surgery/caduceus-s-ar/) · [Surglasses FDA 510(k)](https://www.medicaldesigndevelopment.com/topics/orthopedic/news/22618048/surglasses-receives-fda-clearance-for-ar-spine-navigation-system) · [Anatomage Table](https://anatomage.com/table/) · [3D Slicer](https://www.slicer.org/) · [SlicerMONAIAuto3DSeg](https://github.com/lassoan/SlicerMONAIAuto3DSeg) · [BioDigital Human](https://www.biodigital.com/product/the-biodigital-human) · [BioDigital (Wikipedia, SceneJS/WebGL)](https://en.wikipedia.org/wiki/BioDigital) · [Complete Anatomy (Elsevier)](https://www.elsevier.com/products/complete-anatomy) · [HUVANT (Mondo Digitale PDF)](https://www.mondodigitale.org/sites/default/files/allegati/pagina/2024/Huvant.pdf)

### Como cada um faz, tecnicamente

**DicomSegVR — o concorrente-espelho.** É quase o "VRmed do outro caminho": recebe DICOM/NIfTI, roda **segmentação IA automática** e entrega um 3D em que você "entra" na escala 1:1. Arquitetura em duas pontas: (1) um **dashboard web com viewer Cornerstone** completo — scrub de cortes, overlays de contorno RTSTRUCT, presets de janela/nível e preview 3D de cada máscara; (2) um **app nativo no Meta Quest** que pareia por código e renderiza, no headset, MPR + um **volume raymarched** + malhas por estrutura, em passthrough e hands-free. Modelo SaaS (trial 14 dias). É a prova viva de que a tese do VRmed tem mercado — mas a arquitetura difere de forma decisiva: DicomSegVR depende de **app nativo instalado no Quest** e usa **volume rendering raymarched**; o VRmed é **100% navegador (WebXR), sem instalar nada**, e hoje só rasteriza **malha GLB** (sem volume). Fontes: [busca dicomsegvr.com](http://www.dicomsegvr.com/), [perfil do criador (LinkedIn)](https://www.linkedin.com/in/gustavoogomesss/).

**Materialise Mimics — o padrão-ouro clínico/industrial.** Importa DICOM, segmenta (semi-automático clássico + **CT Bone AI** que rotula todos os ossos, coronária semi-auto, mask morphing 4D) e exporta para malhagem, FEA/CFD (Abaqus/Ansys), impressão 3D e planejamento de implantes. Tem componente cloud para compartilhar caso, segmentação IA na nuvem e **XR case viewing**. É desktop, **caro** (licenças de milhares de dólares/ano) e, crucialmente, **regulado** (marcação para uso clínico). Fontes: [Mimics Innovation Suite](https://www.materialise.com/en/healthcare/mimics-innovation-suite), [AI Segmentation](https://www.materialise.com/en/healthcare/mimics-innovation-suite/ai-enabled-segmentation).

**3D Slicer — o poder open source.** Construído sobre **ITK + VTK** (C++), com IO DICOM, módulo de volume rendering, registro, segmentação e modelos de superfície. IA entra por extensões: **SlicerTotalSegmentator** (nnU-Net, 104+ estruturas) e **SlicerMONAIAuto3DSeg** (MONAI/PyTorch). Tem **2D↔3D ligado** de fábrica (MPR sincronizado com o 3D — exatamente o que falta ao VRmed), módulo Sequences para 4D e **SlicerVR** (OpenXR) para imersão. Gratuito, mas desktop, curva de aprendizado alta e não é "produto" acabado. Fontes: [slicer.org](https://www.slicer.org/), [SlicerMONAIAuto3DSeg](https://github.com/lassoan/SlicerMONAIAuto3DSeg).

**Anatomage Table — o cadáver digital.** Mesa física de 84" com tela touch autoestereoscópica (3D **sem óculos**), corpo em escala 1:1 vindo do **Visible Human**, mais milhares de estruturas anotadas e capacidade de **carregar dados reais de paciente (CT/MRI)** e comparar/sobrepor cortes com o 3D, além de simular fisiologia (batimento). É hardware caro; o forte é educação/dissecção virtual, não reconstrução patient-specific em escala. Fonte: [Anatomage Table](https://anatomage.com/table/).

**CORTEXPLORER MED e Surglasses Caduceus S — navegação intraoperatória.** Categoria diferente: não é educação, é **cirurgia guiada**. CORTEXPLORER usa múltiplas câmeras de alta resolução para rastrear cena e instrumentos e, num **HMD de realidade mista**, sobrepõe anatomia e trajetória em 3D, atualizando a posição do instrumento em tempo real (em ensaio clínico para aneurisma cerebral). O Caduceus S da Surglasses é **AR see-through com clearance FDA 510(k)** para coluna, sobrepondo a anatomia 3D no paciente com 2–4 imagens de C-arm intraoperatórias. São ⚫ **regulatórios por natureza** e fora do escopo atual do VRmed. Fontes: [NCT05269498](https://clinicaltrials.gov/study/NCT05269498), [Caduceus S](https://surglasses.com/en/surgery/caduceus-s-ar/), [FDA clearance](https://www.medicaldesigndevelopment.com/topics/orthopedic/news/22618048/surglasses-receives-fda-clearance-for-ar-spine-navigation-system).

**HUVANT — háptico + virtual para treino cirúrgico.** Plataforma de simulação que combina **modelos hápticos físicos** (que reproduzem resposta mecânica/tátil de órgãos) com modelos virtuais, para treinar cirurgiões jovens a custo sustentável. É treinamento por simulação, não pipeline DICOM→3D nem viewer clínico. Fonte: [HUVANT (PDF)](https://www.mondodigitale.org/sites/default/files/allegati/pagina/2024/Huvant.pdf).

**BioDigital Human e Complete Anatomy — os atlas web/app.** BioDigital foi pioneiro em **WebGL sem plugin** (SceneJS), oferece 1000+ modelos de anatomia/doença em 8 idiomas e uma **API JavaScript** para embutir 3D em apps de terceiros — mas são **modelos idealizados, não o paciente**, e sem DICOM. Complete Anatomy (3D4Medical/Elsevier) é a plataforma de atlas mais polida do mercado (referência de UX/design), cloud, com cursos e um módulo de radiologia que permite **importar e correlacionar** MRI/RX/CT — porém o 3D continua sendo atlas idealizado, não reconstrução patient-specific. Fontes: [BioDigital](https://www.biodigital.com/product/the-biodigital-human), [Wikipedia BioDigital](https://en.wikipedia.org/wiki/BioDigital), [Complete Anatomy/Elsevier](https://www.elsevier.com/products/complete-anatomy).

### (a) O que eles fazem que o VRmed ainda não faz

- **2D↔3D ligado** — o buraco mais gritante. DicomSegVR (dashboard Cornerstone), 3D Slicer (MPR sincronizado) e Anatomage (compara corte×3D) todos deixam o usuário navegar cortes e ver o ponto correspondente no 3D. O VRmed **não tem viewer de slices nenhum** — só identifica estrutura pelo nome da malha.
- **Volume rendering** — DicomSegVR (raymarched no Quest), Mimics, 3D Slicer renderizam o **volume** (densidade real, não só a superfície). O VRmed só mostra malha GLB, perdendo 13–19% de volume/relevo na suavização.
- **Patologia por IA de verdade** — Mimics/Slicer têm quantificação e ferramentas clínicas validadas; o VRmed detecta lesão por **limiar de HU** (heurística, não IA) e pinta em modelo ilustrativo aproximado, não na mesh real.
- **Digital twin / simulação** — Mimics exporta para FEA/CFD; CORTEXPLORER/Surglasses fazem tracking ao vivo. VRmed: zero.
- **Comparação temporal (4D / follow-up)** — Mimics (morphing 4D) e Slicer (Sequences) lidam com séries temporais; VRmed não.
- **Marcação regulatória e validação** — Mimics, Caduceus S (FDA) são produtos clínicos; o VRmed não tem anonimização (pydicom ausente), nem validação Dice/HD95, nem backend real.
- **Escala de conteúdo e polimento** — Complete Anatomy/BioDigital têm milhares de modelos, cursos, 8 idiomas e UX referência.

### (b) O que o VRmed reproduz com open source (aproveitando a stack atual)

- 🔵 **Viewer 2D de cortes + link 2D↔3D no navegador** — integrar **Cornerstone3D** (o mesmo motor que o DicomSegVR usa no dashboard) ou **Niivue** (WebGL2, um script, ótimo para NIfTI — e o pipeline já produz `ct.nii.gz`). Niivue é o caminho mais barato: casa direto com o output atual sem servidor. Fecha o gap #1 sem tocar no pipeline. 🟡 O clique-por-nome de estrutura que já existe pode virar a ponte 2D→3D.
- 🔵 **Volume rendering no navegador** — **VTK.js** ou o próprio **Niivue** fazem ray-casting de volume em WebGL2, lendo o `ct.nii.gz` que o pipeline já gera. Dá para colocar volume ao lado da malha sem reescrever o pipeline de malha.
- 🔵 **Anonimização DICOM** — adicionar **pydicom**/**dcm2niix** ao pipeline (ambos ausentes hoje) resolve um requisito ⚫ básico antes de qualquer dado real; é dependência conhecida, baixo risco.
- 🔵/🟡 **Mais/ melhor segmentação** — já usam TotalSegmentator; dá para acrescentar modelos **MONAI Auto3DSeg** (mesma família do Slicer) para estruturas fora do preset, com pouco atrito.
- 🟡 **Comparação temporal simples** — com dois GLBs do mesmo paciente em datas diferentes, um seletor/overlay no viewer já entrega um "antes/depois" sem 4D real.

### (c) O que precisaria desenvolver internamente

- 🟠 **Patologia real (não por limiar)** — sair do threshold de HU para detecção/segmentação de lesão com modelo treinado é 🔴 problema de pesquisa (dados rotulados, validação). Curto prazo: assumir explicitamente que é "hotspot ilustrativo".
- 🟠 **Backend de verdade** — hoje não existe (só 2 rotas serverless na Render, sem banco/upload/GPU). Upload de estudo, fila de processamento e GPU são desenvolvimento próprio significativo.
- 🟠 **Reprodutibilidade do pipeline** — não há `requirements.txt`/`pyproject`; ambiente irreproduzível. É trabalho interno (baixo risco, alto valor) antes de escalar.
- ⚫ **Validação clínica (Dice/HD95) e caminho regulatório** — não é só técnico: é o que separa "demo educacional" de "ferramenta clínica". Mimics e Surglasses vivem disso.
- 🟠 **Digital twin / simulação** — FEA/CFD ou fisiologia são esforço grande e provavelmente fora do foco por ora.

### (d) Onde há diferenciação REAL

1. **Web-first + WebXR sem instalação** — este é o fosso. DicomSegVR ainda exige **app nativo no Quest**; Mimics/Slicer/Anatomage são desktop/hardware; atlas (BioDigital/Complete Anatomy) são web mas **não patient-specific**. O VRmed é o único que promete *DICOM do paciente → 3D → VR direto no navegador, zero instalação*. Defender e polir isso é a estratégia.
2. **Patient-specific acessível** — democratizar o que hoje é caro (Mimics) ou complexo (Slicer): pegar o exame real e transformar em 3D navegável **sem licença de milhares de dólares nem curva de Slicer**. Nicho de valor claro em educação e comunicação médico-paciente.
3. **2D↔3D no navegador** — se implementado com Cornerstone3D/Niivue, o VRmed junta o link 2D↔3D (força do Slicer) com a entrega web/VR (que o Slicer não tem bem). É a combinação que ninguém entrega limpa hoje.
4. **Fluxo integrado ponta-a-ponta** — Mimics/Slicer param no desktop; atlas não tocam DICOM; navegação intraop é outro mundo. Um pipeline honesto DICOM→IA→GLB→WebXR, empacotado e reproduzível, é raro.

### Nota honesta de maturidade

Não dá para fingir paridade. Mimics e Anatomage são **produtos maduros, validados e caros**, com anos de engenharia regulatória; Surglasses tem **FDA clearance**; 3D Slicer tem uma comunidade e um ecossistema de extensões que o VRmed não vai replicar. Complete Anatomy/BioDigital têm escala de conteúdo e UX de outra liga. O VRmed hoje é um **protótipo de pesquisa educacional** — sem backend real, sem anonimização, sem validação, com patologia por heurística. A janela de oportunidade não é competir de frente com esses gigantes, e sim ocupar a interseção que eles deixam vaga: **patient-specific, web-first, WebXR, sem instalação e barato** — fechando primeiro o gap de 2D↔3D (Cornerstone3D/Niivue) e a anonimização, que são baratos e destravam credibilidade.

## 8. Diferencial / moats proprietários

### 8.0 O ponto de partida incômodo: hoje o VRmed não tem moat

A pipeline atual é competente, mas **quase inteiramente reproduzível por um mestrando com uma RTX em um fim de semana**. TotalSegmentator (nnU-Net pré-treinado, só inferência), marching cubes do scikit-image, simplificação com `fast_simplification`, Draco via `gltf-transform`, WebXR com R3F/drei — cada peça é open source e documentada. "Usamos TotalSegmentator" **não é um diferencial**: é uma escolha de engenharia sensata que qualquer concorrente copia. Pior: TotalSegmentator herda limitações conhecidas justo onde a medicina paga caro — vasos finos, coronárias, ramos distais em regiões calcificadas/ruidosas ([revisão sobre segmentação de coronárias, arXiv 2512.12539](https://arxiv.org/pdf/2512.12539); [SADiff, PMC12194381](https://pmc.ncbi.nlm.nih.gov/articles/PMC12194381/)). E a própria malha.py **documenta 13–19% de perda de volume/relevo pela suavização** — ou seja, o output hoje é *ilustrativo bonito*, não *fiel medível*.

Isso define a régua: um moat do VRmed tem que ser algo que **não sai de graça do GitHub** e que **acumula valor com o tempo** (dado, validação, workflow, relação clínica). A tabela abaixo avalia os candidatos; escala 1–5 (5 = melhor para nós), Tempo em curto (<3m) / médio (3–9m) / longo (>9m).

### 8.1 Onde o mercado deixa a porta aberta

O gap estratégico é claro e vale explicitar, porque é a tese central de moat:

- **Anatomage, BioDigital, Complete Anatomy = anatomia de atlas, padronizada, não do paciente** ([BioDigital](https://www.biodigital.com/); [comparativo HealthySimulation](https://www.healthysimulation.com/virtual-anatomy/)). Eles têm modelos lindos e didáticos, mas você não joga a TC da *sua* mãe lá dentro. 🟠 **VRmed já nasce patient-specific** (pipeline TC→GLB nomeado por estrutura) — esse é o eixo a defender.
- **OHIF / Cornerstone3D / Niivue = 2D↔3D no navegador, mas radiológico, não WebXR imersivo com mesh patient-specific interativa** ([Cornerstone3D](https://github.com/cornerstonejs/cornerstone3D), construído sobre [VTK.js](https://www.kitware.com/vtk-js-v24-release-notes/); [Niivue](https://github.com/niivue/niivue)). Eles têm o slice linkado que o VRmed **não tem**; o VRmed tem a experiência 3D/VR que eles não priorizam.
- **HeartFlow (FFR-CT, De Novo FDA 2014) e Cleerly (37 medidas, ML FDA-cleared)** provam que o moat durável em imagem cardíaca é **uma medida proprietária, validada e reembolsada** — não o visualizador ([HeartFlow De Novo](https://ir.heartflow.com/news-releases/news-release-details/heartflow-secures-de-novo-clearance-us-food-and-drug); [Cleerly ISCHEMIA](https://cleerly.com/ischemia-reinvented)). Eles viraram um número que o cardiologista confia e o convênio paga.
- **Materialise Mimics** mostra que "3D patient-specific a partir de TC para diagnóstico/planejamento" **é dispositivo Classe II, exige 510(k)** ([Knobbe Martens sobre o 510(k) da Mimics](https://www.knobbe.com/blog/materialise-receives-first-ever-510k-clearance-anatomical-model-3d-printing-software/)). Isso é ao mesmo tempo barreira (custo/tempo) e moat (quem passa, defende).

Tradução: o VRmed está sentado exatamente no cruzamento *patient-specific + web/WebXR + validável*. Nenhum dos grandes ocupa esse quadrante inteiro. O moat tem que ser construído aí.

### 8.2 Avaliação dos candidatos a moat

| # | Candidato a moat | Marcador | Impacto | Dificuldade | Defensib. | Tempo | Por quê (uma frase) |
|---|---|---|---|---|---|---|---|
| 1 | **Reconstrução de alta fidelidade** (mesh que preserva volume/vasos, com knob de calibração) | 🟠 | 5 | 4 | 3 | médio | Ataca a perda de 13–19% já documentada na `malha.py`; vira "modelo bonito" em "modelo medível" — direto no que o mercado de atlas não faz. |
| 2 | **2D↔3D no navegador** (slice radiológico linkado à mesh real, clique no voxel = highlight na malha) | 🔵 | 5 | 3 | 2 | médio | Base pronta (Cornerstone3D/Niivue) integrável; sozinho é copiável, mas é o *chassi* que habilita os moats 3/9/11. |
| 3 | **Patient-specific intelligence** (medidas e relações espaciais automáticas: diâmetros, distâncias tumor↔margem, volumes por câmara) | 🟠 | 5 | 4 | 4 | médio | É o "número que o clínico confia" à la HeartFlow/Cleerly, mas geométrico e explicável; alta defensibilidade se validado. |
| 4 | **Validação / acurácia auditável** (Dice/HD95 por estrutura + relatório de incerteza versionado por caso) | ⚫🟠 | 5 | 3 | 4 | médio | Hoje inexiste (`validar-segmentacao.py` não existe); é o que separa "demo" de "ferramenta clínica" e sustenta 510(k)/ANVISA. |
| 5 | **Dataset próprio** (pares TC→mesh curados/corrigidos por especialista, coorte BR, com patologia anotada) | 🟠 | 5 | 4 | 5 | longo | Único moat que **compõe** (cada caso corrigido melhora o próximo); barreira que dinheiro sozinho não pula. |
| 6 | **Segmentação de patologias** (não só anatomia normal: lesão, enfisema, tumor — de verdade, com IA) | 🔴 | 4 | 5 | 4 | longo | Hoje é limiar de HU em modelo ilustrativo, não IA; virar detecção real é problema de pesquisa + regulatório. |
| 7 | **Registro longitudinal** (mesma anatomia em T0/T1/T2, quantificando mudança) | 🔵🟠 | 4 | 4 | 3 | médio | elastix/ANTs resolvem o registro ([revisão PMC12343390](https://pmc.ncbi.nlm.nih.gov/articles/PMC12343390/)); o moat é a **narrativa visual da mudança em 3D/VR**, não o algoritmo. |
| 8 | **Modelos próprios de segmentação** (treinar do zero, substituir TotalSegmentator) | 🔴 | 3 | 5 | 3 | longo | Alto custo, ganha pouco vs. fine-tune; só vale para nichos onde o pré-treinado falha (coronária, ramo distal). |
| 9 | **Experiência clínica / workflow** (do DICOM ao caso em VR sem CLI, com anonimização e laudo) | 🟡 | 4 | 3 | 2 | curto | Reduz atrito real (hoje é CLI + `npx` manual), mas workflow é imitável; é *retenção*, não *barreira*. |
| 10 | **Infra pipeline cloud GPU barato** (segmentação sob demanda serverless-GPU) | 🟠 | 3 | 3 | 1 | médio | Comodity puro (Modal/RunPod/spot); economiza custo, não defende — não é moat, é linha de OPEX. |
| 11 | **Visualização / WebXR nativo** (patient-specific em headset sem instalar nada) | 🟢🟡 | 4 | 2 | 2 | curto | Já funciona e encanta em demo; mas WebXR é padrão aberto — diferencia a *experiência*, não trava o concorrente. |

> Nota de leitura: **Defensibilidade** é o que mais separa os candidatos. Visualização e infra pontuam baixo (qualquer um copia); dataset e validação pontuam alto (acumulam e/ou viram barreira regulatória).

### 8.3 O que está superestimado (para não gastar bala à toa)

- **WebXR nativo (🟢🟡)** é o carro-chefe da *demo*, não do *moat*. Encanta investidor e professor, mas o dia que um concorrente quiser, ele faz — é padrão W3C. Mantenha como vantagem de experiência e go-to-market, não como tese de defensibilidade.
- **Modelos próprios do zero (🔴)** e **infra GPU barata (🟠)** são armadilhas de engenheiro: muito trabalho, pouca trava. Fine-tune pontual > treinar do zero; spot-GPU é OPEX, não moat.
- **Segmentação de patologia por IA de verdade (🔴)** é o moat mais valioso e o mais perigoso agora: é pesquisa + Classe II/III. Colocar cedo demais no roadmap queima caixa. Deixe como visão, não como próximo sprint.

### 8.4 Recomendação: os 2–3 moats a construir

Dado o estado real (web-first, WebXR funcional, pipeline TC→GLB pronto, **sem** backend/banco/validação), a jogada é **encaixar moats em cima do que já existe**, não reescrever.

**Moat #1 — "Fidelidade auditável" = Reconstrução de alta fidelidade + Validação (candidatos 1 + 4). 🟠⚫**
Combine porque um sem o outro é fraco: fidelidade sem prova é marketing; prova sem fidelidade é honestidade sobre um modelo ruim. Concretamente: (a) preservar volume/vasos na `malha.py` — reduzir a suavização agressiva, reintroduzir detalhe fino, expor um **knob de calibração** por estrutura (a física da TC varia; um sigma fixo nunca serve para coronária *e* fígado); (b) gerar, por caso, **Dice/HD95 contra a máscara e um mapa de incerteza da malha**, versionado. Isso vira o VRmed em "3D patient-specific que você pode *medir e auditar*" — exatamente a fronteira Classe II que a Mimics ocupa ([Knobbe/Materialise 510(k)](https://www.knobbe.com/blog/materialise-receives-first-ever-510k-clearance-anatomical-model-3d-printing-software/)), mas *web-native*. **Menor impacto na stack: mexe na pipeline Python que já existe.**

**Moat #2 — "Inteligência espacial patient-specific" no navegador = 2D↔3D + medidas automáticas (candidatos 2 + 3). 🔵🟠**
O chassi (slice linkado à mesh) você **integra** de open source maduro — Cornerstone3D/Niivue já fazem MPR, DICOM/NIfTI e rendering GPU no browser ([Cornerstone3D](https://github.com/cornerstonejs/cornerstone3D); [Niivue](https://github.com/niivue/niivue)) — e amarra ao viewer R3F que já existe (o manifest hoje nem tem `structures/tris`; falta o vínculo 2D↔3D, confirmado no estado atual). **Em cima disso** vem o moat proprietário: medidas geométricas automáticas ancoradas na mesh real (diâmetro de vaso, distância tumor↔margem, volume por câmara, relação espacial entre estruturas) — o análogo *explicável e geométrico* do "número que o clínico confia" que fez HeartFlow/Cleerly ([HeartFlow De Novo](https://ir.heartflow.com/news-releases/news-release-details/heartflow-secures-de-novo-clearance-us-food-and-drug); [Cleerly](https://cleerly.com/ischemia-reinvented)). Nenhum atlas (Anatomage/BioDigital) faz isso porque não são patient-specific; nenhum viewer radiológico entrega em VR. **Esse é o quadrante que só o VRmed ocupa.**

**Moat #3 (longo, o único que compõe) — Dataset próprio + registro longitudinal (candidatos 5 + 7). 🟠🔵**
O verdadeiro moat de longo prazo é o **volante de dados**: cada caso que um especialista corrige (a malha, a segmentação, a medida) vira par de treino curado — coorte brasileira, com patologia anotada, que ninguém mais tem. Some o registro longitudinal (elastix/ANTs resolvem o alinhamento — [revisão sistemática PMC12343390](https://pmc.ncbi.nlm.nih.gov/articles/PMC12343390/)) e o VRmed passa a **mostrar em 3D/VR como a doença do mesmo paciente mudou entre exames** — narrativa que nenhum atlas consegue por construção. Começa a colher dado *agora* (mesmo manual), mesmo que o produto longitudinal só maadure depois.

**Sequência sugerida:** #2 primeiro (habilita produto e começa a capturar correções → alimenta #3), #1 em paralelo na pipeline (barato, já temos o Python), #3 como colheita contínua desde o dia 1. Fuja de treinar modelo do zero e de patologia-por-IA até ter dataset (#3) e validação (#1) de pé — senão é 🔴 sem rede.

### 8.5 Alerta regulatório transversal ⚫

Todo moat acima que toque *diagnóstico/medida clínica* (especialmente #1 medidas, #3 mudança longitudinal) empurra o VRmed de "educacional/ilustrativo" para **Software as a Medical Device (Classe II, 510(k)/ANVISA)** — a mesma linha que a Mimics cruzou ([FDA Classe II para modelos 3D patient-specific diagnósticos](https://www.knobbe.com/blog/materialise-receives-first-ever-510k-clearance-anatomical-model-3d-printing-software/)). E hoje **não há anonimização** (pydicom ausente) nem validação Dice/HD95 no repo — pré-requisitos, não detalhes. A recomendação prática: manter dois trilhos explícitos — "educacional/visualização" (sem claim clínico, vende já) e "clínico validado" (com o moat de verdade, mas com custo regulatório embutido no roadmap). Vender claim clínico sem esse trilho é o risco que mata a empresa, não a concorrência.

---

## 9. Roadmap de evolução revisado

A análise técnica reordena a sequência que você propôs. Três mudanças de prioridade, com motivo:

- **2D↔3D sobe** (era Fase 3 → agora entre as primeiras): é o maior gap competitivo e é barato porque a affine já existe.
- **Validação sobe e roda em paralelo** (era Fase 2, mantém cedo): é pré-requisito de credibilidade e vira o moat #1; usa SimpleITK, que já é dependência.
- **Cloud/backend desce um pouco** (é o maior salto greenfield): vale fazer depois que 2D↔3D + validação já provaram valor localmente, para não construir infra cara sobre um protótipo não validado. Anonimização + reprodutibilidade (baratas) vêm antes, como pré-condição.

Ideia central: **Fases 0–2 são o "próximo trimestre" e podem correr em paralelo** (quase tudo 🟡/🔵). As fases pesadas (cloud, patologia, temporal) vêm depois, já com fidelidade medida e 2D↔3D no lugar.

### Fase 0 — Fundação quase de graça (paralelo, semanas) 🟡🟠(pequeno)
- **Construir:** `requirements.txt`/pin de torch+CUDA (ambiente reproduzível); unificar as duas stores XR em `obterXRStore()` + endurecer o viewer; **guarda de triângulos em runtime** (bloquear entrada em VR acima de ~150–300k); **escala real 1:1 mm** em VR (pular `normalizeContent`); exportar no `manifest.json` a **affine + shape + mapa estrutura→voxels** (as máscaras NIfTI já são esse mapa).
- **Tecnologias:** pip-tools; `@react-three/xr` (já); o próprio pipeline.
- **Depende de:** nada externo. **Já temos:** tudo perto. **Falta:** só fazer. **Risco:** baixo.

### Fase 1 — 2D↔3D no navegador 🔵🟡
- **Construir:** painel 2D de cortes (axial/coronal/sagital) lendo o `ct.nii.gz` + máscaras; sincronização com o 3D por coordenadas mm RAS; picking 3D→slice (reverter `normalizeContent` + pivô, aplicar mm→voxel) e slice→"você está aqui" no 3D; crosshair.
- **Tecnologias:** **Niivue** (WebGL2, lê NIfTI/DICOM nativo, trabalha em mm RAS — encaixe de menor impacto; mantém three no 3D). Cornerstone3D/VTK.js só se precisar de MPR oblíquo/volume depois.
- **Depende de:** Fase 0 (exportar affine). **Já temos:** affine calculada, máscaras, viewer 3D. **Falta:** serializar affine + o painel 2D + a ponte de coordenadas. **Risco:** baixo/médio (a malha suavizada não bate ao mm com o slice — comunicar como aproximação).

### Fase 2 — Validação quantitativa (moat #1, paralelo) 🔵⚫
- **Construir:** `validar-segmentacao.py` com Dice, HD95, ASSD, **NSD/Surface Dice**; um **fantoma sintético** (esfera/cilindro de dimensão conhecida) rodado no pipeline inteiro para calibração dimensional; relatório de fidelidade por estrutura (mediana/IQR); voxelizar a malha de volta para isolar a perda máscara→malha.
- **Tecnologias:** **SimpleITK** (já é dep!), `surface-distance` (DeepMind) ou MONAI metrics; datasets do próprio TotalSegmentator (Zenodo), MM-WHS (câmaras), LIDC (pulmão).
- **Depende de:** nada novo. **Já temos:** o embrião (relatório de perda de volume/watertight). **Falta:** métricas contra ground-truth + fantoma. **Risco:** médio (pode expor que a acurácia é limitada — é justamente o ponto de medir).

### Fase 3 — DICOM robusto + pré-condições legais 🔵🟠⚫
- **Construir:** **reamostragem isotrópica** (hoje só avisada) e correção de gantry oblíquo; **anonimização (pydicom/dcm2niix)** removendo PHI na entrada; automatizar o Draco (tirar o passo manual `npx`).
- **Depende de:** Fase 0. **Já temos:** ingestão DICOM completa. **Falta:** resample + anonimização. **Risco:** baixo técnico; ⚫ é pré-requisito para qualquer exame real não-público.

### Fase 4 — Upload + processamento em cloud (o grande salto) 🟠
- **Construir:** upload → storage privado (R2/S3) → fila → **worker com GPU** (Modal/RunPod) rodando o entrypoint do pipeline → banco (Neon/Postgres) de pacientes/casos/consentimento; **reindexar o `manifest` por paciente** (identidade + histórico); trocar em `ClinicaApp` a origem estática por API assinada (o viewer 3D/WebXR **não muda**).
- **Depende de:** Fases 0/3. **Já temos:** viewer desacoplado que consome GLB por fetch. **Falta:** toda a camada de backend/infra. **Risco:** alto (greenfield, custo GPU, segurança de PHI). **Nota:** é o que tira o VRmed de "protótipo local" e permite "médico envia exame".

### Fase 5 — Primeira patologia: nódulo pulmonar 🔵🟠
- **Construir:** habilitar tasks `lung_nodules` + `lung_vessels` no `segmentacao.py`; sigma gaussiano adaptativo em `malha.py` (não apagar nódulo pequeno); malha "nódulo" rotulada no viewer/VR.
- **Tecnologias:** TotalSegmentator subtasks (Apache-2.0). **Já temos:** a cadeia máscara→malha e o preset tórax. **Falta:** ligar as tasks + ajuste de suavização. **Risco:** médio (nódulo em pulmão aerado tem contraste robusto — bom primeiro caso). ⚫ disclaimer assistivo/educacional.

### Fase 6 — Inteligência espacial patient-specific (moat #2) 🟠
- **Construir:** medidas geométricas automáticas **sobre a máscara/volume** (nunca na malha de VR): diâmetros (RECIST), volume watertight, **distância lesão↔vaso/brônquio** (`scipy.distance_transform_edt` + `trimesh` signed distance), lobo/segmento, relações anatômicas; expor no 2D↔3D e em VR.
- **Depende de:** Fases 1, 2, 5. **Já temos:** scipy/trimesh (instalados), nomes de estrutura. **Falta:** a camada de medidas + UI. **Risco:** médio; ⚫ com selo de incerteza. **É o quadrante que só o VRmed ocupa.**

### Fase 7 — Comparação temporal 🟠⚫
- **Construir:** registro multi-estágio (rígido→afim→deformável) com SimpleITK; medir a lesão **no referencial registrado** (nunca deformar sobre a própria lesão); reportar mudança **com incerteza** ("14 ± 2 mm"), cor 🔴/🟢 só quando exceder o erro; QA de registro (Inverse Consistency).
- **Tecnologias:** **SimpleITK** (já é dep!), SimpleElastix/ANTs como alternativas. **Já temos:** o registrador (nunca chamado). **Falta:** o fluxo + persistência por paciente+data (depende da Fase 4). **Risco:** alto de over-claim (erro de registro pode superar a mudança real; variabilidade inter-scanner). ⚫ alinhar a RECIST.

### Fase 8 — Modelo específico do paciente, versionado 🟡🟠
- **Construir:** consolidar anatomia + patologia + medidas **versionadas por paciente/exame** num "patient-specific model" honesto (não "digital twin"). **Não** prometer twin (estado fisiológico/simulação = 🔴/⚫).
- **Depende de:** Fases 4, 6, 7. **Risco:** baixo se o vocabulário for honesto; ⚫ se virar claim.

### Fase 9 — Clinical VR ("entrar no exame") 🟡🟠
- **Construir:** portar corte/medida/isolamento/labels/comparação para gestos em VR (o plano de corte vira um "handle" segurável); locomoção (teleport/suave com vinheta anti-enjoo); comparação lado a lado; visualização de vasos/lesões e relações.
- **Tecnologias:** `@react-three/xr` v6 (TeleportTarget). **Já temos:** manipulação, corte, envelope, identificação. **Falta:** trazer as ferramentas DOM para dentro do VR. **Risco:** médio (conforto/performance no Quest).

### Fase 10 — Produto médico/regulado ⚫🔴
- **Construir:** conformidade SaMD (ANVISA/510(k)), QMS, validação clínica formal, trilha de auditoria.
- **Risco:** extremo — sai de engenharia e entra em regulatório/clínico. **Estratégia:** manter o trilho educacional vendendo enquanto o trilho clínico validado amadurece.

---

## 10. Os 10 maiores avanços tecnológicos

> *"Se tivéssemos que transformar o VRmed na melhor plataforma do mundo para transformar exames médicos em modelos 3D patient-specific, quais seriam os 10 maiores avanços?"* — ordenados por prioridade estratégica, cada um com os 10 campos pedidos.

### #1 — Vínculo 2D↔3D no navegador
1. **Problema:** o médico não consegue relacionar a lesão no 3D com os slices do exame; hoje não há viewer 2D — é o maior gap vs. concorrentes.
2. **Solução técnica:** painel 2D de cortes sincronizado ao 3D por coordenadas mm RAS; picking 3D→voxel/slice e slice→"você está aqui" no 3D.
3. **Tecnologia:** Niivue (2D, lê o `ct.nii.gz` que já geramos); three no 3D; a affine já calculada.
4. **Já temos:** affine (voxel↔mundo RAS), máscaras NIfTI, viewer 3D, `handleClick` com ponto em mundo.
5. **Falta:** serializar affine/shape no manifest; o painel 2D; reverter `normalizeContent`+pivô no picking.
6. **Dificuldade:** média-baixa. 🔵🟡
7. **Diferencial:** 2D↔3D patient-specific **no navegador + WebXR** — combinação que Mimics/Slicer (desktop) e atlas (BioDigital) não entregam juntos.
8. **Risco clínico:** ⚫ baixo se comunicado como aproximação (malha suavizada não bate ao mm).
9. **Prioridade:** máxima.
10. **Esforço:** ~3–5 semanas.

### #2 — Fidelidade auditável (validação Dice/HD95 + calibração)
1. **Problema:** o pipeline não sabe medir o próprio erro; sem isso qualquer número é indefensável e não há moat.
2. **Solução técnica:** `validar-segmentacao.py` com Dice/HD95/ASSD/NSD contra ground-truth + fantoma sintético para calibração dimensional; relatório de fidelidade por caso.
3. **Tecnologia:** SimpleITK (já é dep), surface-distance (DeepMind)/MONAI metrics; datasets TotalSegmentator/MM-WHS/LIDC.
4. **Já temos:** relatório de perda de volume/watertight (embrião), QA visual.
5. **Falta:** métricas contra verdade + fantoma + report.
6. **Dificuldade:** média. 🔵⚫
7. **Diferencial:** **moat #1** — "reconstrução com acurácia provada" é barreira que não sai de graça do GitHub e vira pré-requisito regulatório.
8. **Risco clínico:** ⚫ positivo (reduz risco ao expor limites).
9. **Prioridade:** máxima (paralelo ao #1).
10. **Esforço:** ~4–6 semanas.

### #3 — Reconstrução de alta fidelidade (reduzir a perda de 13–19%)
1. **Problema:** smoothing + Taubin + afastamento + decimação + anisotropia comem volume e relevo, e a segmentação a 1,5 mm apaga estruturas finas.
2. **Solução técnica:** reamostragem isotrópica na ingestão; sigma adaptativo por tamanho de estrutura; medir sempre no volume, nunca na malha de VR; separar mesh "medição" (fiel) da mesh "VR" (decimada).
3. **Tecnologia:** SimpleITK (resample), scipy/skimage/trimesh (já), opcional VTK/PyVista se o reparo de malha virar gargalo.
4. **Já temos:** todo o pipeline de mesh e o relatório de perda.
5. **Falta:** resample isotrópico, sigma adaptativo, dupla saída (medição vs VR).
6. **Dificuldade:** média. 🟠
7. **Diferencial:** compõe o moat #1 (fidelidade).
8. **Risco clínico:** ⚫ médio (fidelidade é a base de qualquer claim).
9. **Prioridade:** alta (junto do #2).
10. **Esforço:** ~4–6 semanas.

### #4 — Inteligência espacial patient-specific (medidas automáticas)
1. **Problema:** hoje o VRmed mostra "aqui está o pulmão", não "diâmetro da lesão 14 mm, a 3 mm da artéria".
2. **Solução técnica:** camada de medidas geométricas sobre a máscara: diâmetros (RECIST), volume watertight, distância lesão↔vaso/brônquio, lobo/segmento, relações; exibidas no 2D↔3D e em VR.
3. **Tecnologia:** scipy (`distance_transform_edt`) + trimesh (signed distance), ambos já instalados.
4. **Já temos:** scipy/trimesh, nomes de estruturas, máscaras.
5. **Falta:** a camada de medidas + UI + selo de incerteza.
6. **Dificuldade:** média. 🟠
7. **Diferencial:** **moat #2** — o quadrante único (patient-specific intelligence no navegador); análogo às "medidas proprietárias" de HeartFlow/Cleerly.
8. **Risco clínico:** ⚫ alto de over-claim — exige incerteza e disclaimer.
9. **Prioridade:** alta (depende de #1/#2/#5).
10. **Esforço:** ~6–10 semanas.

### #5 — Primeira patologia: nódulo pulmonar
1. **Problema:** a "patologia" atual é limiar de HU pintado em modelo ilustrativo (posição aproximada), não lesão real do paciente.
2. **Solução técnica:** segmentar nódulo com modelo pré-treinado → máscara → mesh (cadeia existente) → relação espacial com vasos/vias aéreas.
3. **Tecnologia:** TotalSegmentator subtasks `lung_nodules` + `lung_vessels` (Apache-2.0); datasets LUNA16/MSD (uso comercial permitido) para validar.
4. **Já temos:** TotalSegmentator, preset tórax, cadeia máscara→malha.
5. **Falta:** habilitar as tasks; sigma adaptativo p/ nódulos pequenos.
6. **Dificuldade:** média. 🔵🟠
7. **Diferencial:** primeiro passo real de "lesão deste paciente" com contraste de imagem robusto.
8. **Risco clínico:** ⚫ assistivo/educacional; sem detecção validada ainda.
9. **Prioridade:** alta.
10. **Esforço:** ~4–8 semanas.

### #6 — Backend cloud com GPU (upload → 3D)
1. **Problema:** sem backend/GPU no servidor, um médico não consegue enviar exame; o pipeline é CLI local.
2. **Solução técnica:** upload → storage privado → fila → worker GPU roda o entrypoint → banco por paciente; viewer passa a consumir API assinada.
3. **Tecnologia:** Modal/RunPod (GPU), R2/S3, Neon/Postgres, fila.
4. **Já temos:** o pipeline empacotável e o viewer desacoplado (consome GLB por fetch).
5. **Falta:** toda a camada de backend/infra/identidade.
6. **Dificuldade:** alta. 🟠
7. **Diferencial:** habilita o produto ("médico envia exame") e a colheita de dados (moat #3).
8. **Risco clínico:** ⚫ alto (PHI, segurança, LGPD).
9. **Prioridade:** alta, mas **depois** de #1/#2 provarem valor.
10. **Esforço:** ~8–12 semanas.

### #7 — Anonimização + reprodutibilidade (pré-condição de credibilidade)
1. **Problema:** sem anonimização não se pode tocar exame real (LGPD); sem manifesto de deps o pipeline é irreproduzível fora do seu PC.
2. **Solução técnica:** passo pydicom/dcm2niix que remove PHI na entrada; `requirements.txt`/pyproject com pin de torch+CUDA.
3. **Tecnologia:** pydicom, dcm2niix, pip-tools.
4. **Já temos:** ingestão; venv local.
5. **Falta:** anonimização + manifesto de deps.
6. **Dificuldade:** baixa. 🔵🟠(pequeno)
7. **Diferencial:** destrava credibilidade e CI; barato.
8. **Risco clínico:** ⚫ é o que reduz risco (PHI).
9. **Prioridade:** alta (pré-condição, faça cedo).
10. **Esforço:** ~1–2 semanas.

### #8 — VR "entrar no exame" (Clinical VR)
1. **Problema:** hoje é "GLB na frente do usuário"; as ferramentas clínicas somem em VR (são DOM).
2. **Solução técnica:** escala real 1:1; guarda de triângulos; corte/medida/isolamento/labels/comparação por gesto; locomoção com conforto.
3. **Tecnologia:** `@react-three/xr` v6 (TeleportTarget), foveação/framebuffer scale; unificar a store XR.
4. **Já temos:** manipulação, corte, envelope, identificação, export em metros.
5. **Falta:** trazer ferramentas para dentro do VR; guarda de tris; locomoção.
6. **Dificuldade:** média. 🟡🟠
7. **Diferencial:** experiência WebXR patient-specific sem instalação — difícil de igualar por desktop.
8. **Risco clínico:** ⚫ baixo (educacional); medição em VR com selo de aproximação.
9. **Prioridade:** média-alta (parte já é 🟡 quase de graça).
10. **Esforço:** ~4–8 semanas (o básico 🟡 em ~2).

### #9 — Comparação temporal confiável
1. **Problema:** comparar exame anterior × atual sem enganar (erro de registro pode superar a mudança real).
2. **Solução técnica:** registro rígido→afim→deformável; medir no referencial; reportar com incerteza; cor só quando exceder o erro; QA de registro.
3. **Tecnologia:** SimpleITK (já é dep), SimpleElastix/ANTs.
4. **Já temos:** o registrador (nunca chamado); `torax-alta`×`torax-completo` já é um longitudinal disfarçado.
5. **Falta:** o fluxo + persistência por paciente+data (depende do #6).
6. **Dificuldade:** alta. 🟠🔴(claim)
7. **Diferencial:** narrativa de evolução da doença em 3D/VR (raro na web).
8. **Risco clínico:** ⚫ alto de over-claim — alinhar a RECIST, nunca cravar decimais sem incerteza.
9. **Prioridade:** média (depois do backend).
10. **Esforço:** ~8–12 semanas.

### #10 — Dataset próprio + curadoria longitudinal (moat #3)
1. **Problema:** os moats técnicos são copiáveis; só dados proprietários compõem valor com o tempo.
2. **Solução técnica:** cada caso corrigido por especialista vira par de treino curado (coorte BR com patologia); registro longitudinal acumula trajetórias.
3. **Tecnologia:** o próprio produto como ferramenta de anotação; elastix/ANTs no registro; futuro MONAI/nnU-Net para treino.
4. **Já temos:** o pipeline que gera os casos.
5. **Falta:** produto em uso + fluxo de curadoria + governança de dados.
6. **Dificuldade:** alta/longa. 🟠🔵
7. **Diferencial:** **moat #3** — o único que vira barreira real e alimenta IA própria depois.
8. **Risco clínico:** ⚫ governança/consentimento/LGPD.
9. **Prioridade:** começar a colher desde o dia 1; colher, não construir do zero agora.
10. **Esforço:** contínuo (colheita), treino é 🔴 para depois.

---

### Fecho

O VRmed **não precisa virar outra coisa** para perseguir essa visão — precisa **fechar o 2D↔3D, provar a fidelidade e ganhar inteligência espacial**, tudo em cima do pipeline e do viewer que já existem, usando dependências que já estão instaladas. O trabalho de pesquisa de verdade (IA própria, digital twin com simulação, produto regulado) fica no fim, depois que dado e validação estiverem de pé. O diferencial defensável mora em **medida validada + dados próprios**, não no visualizador.

*Fim da análise. Read-only — nenhum arquivo de código foi alterado.*
