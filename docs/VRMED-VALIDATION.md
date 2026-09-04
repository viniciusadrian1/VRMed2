# VRmed — Validação e benchmark

> Fase 2. Antes disso o pipeline **não sabia medir o próprio erro**: o único número
> era `perda_volume_pct`, que compara a malha com a máscara que ela mesma gerou.
> Agora há métrica contra verdade (fantoma) e contra referência (máscara/master).

Regra que atravessa tudo: **medida sempre em milímetros físicos**, nunca em índice
de voxel; e **volume só vale em malha watertight**.

## Ferramentas

### 1. Segmentação × ground-truth — `scripts/validation/segmentation_metrics.py`

```bash
python -m scripts.validation.segmentation_metrics \
  --prediction pred.nii.gz --ground-truth gt.nii.gz
```

Devolve JSON com `dice`, `iou`, `nsd_1mm`, `nsd_2mm`, `hd95_mm`, `assd_mm`,
`volume_error_pct`. Fronteira definida como `mask XOR binary_erosion(mask)`;
distâncias via `distance_transform_edt` com `sampling=spacing`. HD95 e ASSD são
simétricos. (A definição de fronteira varia entre bibliotecas — a nossa está
fixada aqui para os números serem comparáveis entre execuções.)

Autoteste de sanidade: `--autoteste` (identidade → Dice 1,0 / HD95 0; dilatação
de 1 voxel → HD95 ≈ 1 voxel em mm).

### 2. Máscara × malha e master × derivado — `scripts/validation/mesh_metrics.py`

```python
comparar_mascara_malha(mask, mesh, affine)  # isola o erro da RECONSTRUÇÃO
comparar_malhas(master, derivado)           # o que a decimação custou
```

A malha é rasterizada de volta para a grade da máscara com
`vtkPolyDataToImageStencil` (e não `trimesh.voxelized` + fill: a casca 26-conexa
do marching cubes vaza no flood-fill 6-conexo).

Medido em caso real: coração `dice 0,9965 · hd95 0,68 mm · volume −0,12%`;
decimar para 30% dos triângulos custou `hausdorff 0,51 mm · rms 0,079 mm`.

### 3. Fantoma com verdade conhecida — `scripts/validation/phantom.py`

```bash
python scripts/validation/phantom.py
```

Esfera, cilindro, tubo fino, duas estruturas adjacentes (fusão indevida) e esfera
com cavidade (detecta `fill_holes` destrutivo). Aceita spacing anisotrópico.
É o **único** teste que mede contra a anatomia real em vez da máscara.

### 4. Benchmark — `scripts/validation/benchmark.py`

```bash
python scripts/validation/benchmark.py \
  --masks .clinica-dados/torax-alta_masks \
  --pipelines marching_cubes,surface_nets,flying_edges,sdf \
  --out .clinica-dados/benchmark-torax-alta
```

Gera `benchmark.csv`, `benchmark.json` e `summary.md` **agregado por faixa de
escala** (grande > 100 cm³ · médio 1–100 cm³ · pequeno < 1 cm³).

**Critério de aprovação (§16):** um pipeline só é adotado se vencer **em cada
faixa**. Ganho na média com regressão nas estruturas pequenas é reprovação — a
média global é dominada por pulmão/fígado/coração e esconde o colapso do fino.

### 5. Benchmark de σ por faixa de calibre — `scripts/validation/benchmark_sigma.py`

```bash
python scripts/validation/benchmark_sigma.py   # 21 alvos × 4 variantes = 84 linhas
python scripts/validation/espessura.py         # calibre = 2 × mediana(EDT no esqueleto)
```

Agrega por **calibre** (< 3 · 3–10 · 10–30 · > 30 mm), não por volume, e separa Tier 1
(fidelidade à máscara) de Tier 3 (fantoma analítico). Relatório completo, com as 5 ablações
e a recomendação de default para MASTER e DERIVADOS:
[`RELATORIO-VALIDACAO-RECONSTRUCAO.md`](RELATORIO-VALIDACAO-RECONSTRUCAO.md).

## Resultados que já mudaram decisões

1. **Surface Nets não vira default.** Perdeu em Dice/ASSD/volume contra o
   baseline, tanto no caso real quanto contra a verdade analítica (esfera de
   10 mm: −29,0% de volume contra −6,9%). A recomendação da pesquisa foi
   falseada pelo experimento.
2. **A gaussiana na máscara binária é o que apaga vaso fino.** Num tubo de 2 mm:
   −89% de volume com ela, −30% sem. Detalhes em `VRMED-RECONSTRUCTION.md`.

   > **Histórico — hipótese superada.** A direção proposta na época era **σ por classe**
   > anatômica (`orgao`/`camara` mantendo σ, `vaso`/`via_aerea`/`lesao` sem gaussiana),
   > porque a gaussiana ajudava a estrutura grande. O benchmark por faixa de calibre
   > **superou essa hipótese**: σ = 0 venceu em erro de volume nas **quatro** faixas
   > (−28,24 / −3,57 / −0,55 / −0,13 % contra −89,99 / −8,79 / −1,40 / −0,40 %), sem
   > exceção — então não há faixa em que valha a pena manter a gaussiana, e a
   > condicionalidade por classe deixou de ter função no caminho da MASTER. Registrado
   > como hipótese falseada, não apagado. Ver `RELATORIO-VALIDACAO-RECONSTRUCAO.md` §2.1.
3. **Metade das estruturas publicadas não é watertight** (3/6 nos dois casos de
   tórax) — então `volume_ml` (`malha.py`) é inválido justamente nas maiores
   (pulmões, aorta, coração), que são cortadas pelo campo de visão.
4. **Os GLBs publicados estão em Draco e o trimesh não os decodifica** (lê zeros).
   Toda validação tem de rodar na malha **pré-Draco**; medir o asset publicado dá
   número falso.

## Estado congelado da configuração

| item | estado | evidência |
|---|---|---|
| `sigma = 0` | **default da MASTER** | venceu em erro de volume nas 4 faixas de calibre (§2.1) |
| `Taubin = 4` | **default vigente** | nenhuma variante superou sob o critério declarado (§8.6) |
| σ por classe | **hipótese superada** para o caminho MASTER | σ = 0 vence em todas as faixas, não só em algumas (§2.1) |
| Taubin 8 / 12 / 20 | **experimental** | melhora calibre no fino e área no grosso, piora área no fino (§8.2–8.3) |
| WindowedSinc (20; 0,1) | **experimental** | perde para Taubin 20 nos três eixos em estrutura fina (§8.3) |
| Surface Nets | **experimental** | perde em volume, área, Dice, ASSD, HD95 e watertight nas 4 faixas (§3.2) |
| `marching_cubes` | **baseline oficial** | nenhuma alternativa testada o superou |

MASTER completa: `marching_cubes · σ = 0 · Taubin = 4 · level = 0,5 · offset = 0 · sem decimação`.

## Limitações honestas

- **Tier 2 deixou de estar ausente** (2026-09-04): `scripts/validation/tier2/` mede a
  segmentação contra o **LCTSC/TCIA** (CC BY 3.0, ground truth de 2017, independente do
  TotalSegmentator). **1 caso, 5 estruturas**; aorta e traqueia não são anotadas pelo
  dataset e saem como "não medido". Resultado e ressalvas de definição em
  [`RELATORIO-VALIDACAO-RECONSTRUCAO.md` §9](RELATORIO-VALIDACAO-RECONSTRUCAO.md).
  Com n=1 isso **não é estimativa de acurácia do modelo** — é a primeira medida com o
  instrumento montado.
- O benchmark mede **malha × máscara**. A máscara não é a verdade — ela já é uma
  discretização. Por isso o fantoma existe: é o que separa "fiel à máscara" de
  "fiel à anatomia".
- Abaixo de ~1,5 voxel de seção a estrutura não existe nem na máscara. Nenhum
  extrator recupera isso; só resolução/reamostragem.
- Nada aqui é validação clínica. São métricas de engenharia geométrica.
  Uso segue **educacional/experimental, não diagnóstico**.
