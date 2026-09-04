# VRmed — Reconstrução de superfície (máscara → malha)

> Estado: Fase 1 implementada **atrás de flag**. O default do pipeline continua o
> comportamento histórico. Nada virou padrão sem número que justifique (§65).

## Como rodar

```bash
# default (comportamento histórico, inalterado)
python scripts/tc-para-vrmed.py --input ct.nii.gz --masks-dir masks --output caso.glb

# método alternativo (benchmark)
python scripts/tc-para-vrmed.py ... --reconstrucao surface_nets

# MASTER: sem decimação de VR e sem afastamento artificial
python scripts/tc-para-vrmed.py ... --master --output caso-master.glb
```

A API única fica em `scripts/geometry/reconstruction.py`:

```python
reconstruct_surface(mask, affine, method="marching_cubes",
                    smoothing="auto", sigma_mm=None, taubin_iters=4,
                    offset_mm=0.0, level=0.5) -> ResultadoSuperficie | None
```

Métodos: `marching_cubes` (baseline), `surface_nets` (vtkSurfaceNets3D),
`flying_edges` (vtkFlyingEdges3D), `sdf` (suaviza o zero-level-set).
Todos devolvem a malha em **metros / eixos glTF**, então são comparáveis.

Devolve `None` quando a estrutura tem < 50 voxels **ou quando não sobrevive à
suavização** (antes isso estourava exceção; ver "vaso fino" abaixo).

## O que foi medido (não suposto)

### 1. Surface Nets NÃO deve virar default

Benchmark em caso real (`torax-alta`, 9 estruturas, malha × máscara):

| faixa | pipeline | Dice | ASSD (mm) | erro vol. | tris | tempo |
|---|---|---|---|---|---|---|
| grande (7) | marching_cubes | **0,9976** | **0,062** | −0,06% | 307.596 | 2,83 s |
| grande | surface_nets | 0,9916 | 0,178 | −0,19% | 308.600 | **0,76 s** |
| grande | flying_edges | 0,9964 | 0,089 | −0,06% | 307.584 | 2,07 s |
| médio (2) | marching_cubes | **0,9878** | **0,070** | **−1,20%** | 40.692 | 2,14 s |
| médio | surface_nets | 0,9597 | 0,193 | **−3,47%** | 40.958 | **0,36 s** |
| médio | flying_edges | 0,9847 | 0,088 | −1,23% | 40.692 | 1,41 s |

Confirmado contra **verdade analítica** (fantoma, esfera de 10 mm, iso 1,0 mm):

| método | erro de volume | erro de diâmetro |
|---|---|---|
| máscara (discretização) | −1,6% | — |
| marching_cubes | −6,9% | −1,4% |
| **surface_nets** | **−29,0%** | **−10,0%** |
| flying_edges | −7,0% | −1,5% |
| sdf | −7,5% | −1,6% |

**Conclusão:** a recomendação da pesquisa (adotar Surface Nets) **foi falseada
pelo experimento**. Ele é 3–4× mais rápido e não reduz triângulos; com a
suavização embutida no default, encolhe demais. Fica disponível na flag para
estudo (tem vantagem em estrutura fina, ver abaixo), **não como padrão**.

### 2. A gaussiana na máscara binária é o que apaga vaso fino

Tubo de 30 mm, spacing 0,7 mm isotrópico, `marching_cubes`:

| diâmetro | verdade | máscara | **com** gaussiana | **sem** gaussiana |
|---|---|---|---|---|
| 1,0 mm | 23,6 mm³ | 14,7 | **ausente** | **ausente** |
| 1,5 mm | 53,0 | 73,7 | **−80%** | **+24%** |
| 2,0 mm | 94,2 | 73,7 | **−89%** | **−30%** |
| 3,0 mm | 212,1 | 191,7 | −34% | **−13%** |
| 4,0 mm | 377,0 | 309,7 | −30% | **−20%** |
| 6,0 mm | 848,2 | 899,7 | **−0%** | +5% |

Leitura honesta:

- **Vaso de 2 mm perde 89% do volume** com a suavização atual; sem ela, 30%.
  São ~59 pontos percentuais recuperados numa linha de configuração.
- A gaussiana **ajuda** a estrutura grande (−0% contra +5% em 6 mm). Por isso a
  saída não é "remover a gaussiana", e sim **σ por classe**.
- Abaixo de ~1,5 voxel de seção a estrutura **não existe nem na máscara** — esse
  é um teto físico da discretização, que nenhum extrator recupera.
- Surface Nets preserva melhor o fino (−57% em 1,5 mm contra −80%) e pior o
  grande. É um trade-off real, não "melhor" ou "pior".

## Recomendação técnica (medida — ver relatório)

> **Atualizado.** O benchmark por faixa de calibre já rodou. Resultado, ablações e
> recomendação de default estão em
> [`RELATORIO-VALIDACAO-RECONSTRUCAO.md`](RELATORIO-VALIDACAO-RECONSTRUCAO.md).
> Resumo: **σ = 0 vence em erro de volume nas 4 faixas** (< 3, 3–10, 10–30, > 30 mm),
> então a saída não é σ por classe — é σ = 0 na MASTER, com Taubin mantido. A tabela por
> classe abaixo era a hipótese pré-medição; ficou superada.

A hipótese original era **σ por classe anatômica**, reaproveitando as classes de
`scripts/geometry/mask_processing.py` (`orgao`, `vaso`, `via_aerea`, `camara`,
`lesao`):

| classe | suavização sugerida | motivo |
|---|---|---|
| orgao / camara | σ atual | a suavização ajuda; erro já é < 1% |
| vaso / via_aerea | **sem gaussiana** (ou σ ≤ 0,25 × menor voxel) | recupera ~60 pp em 2 mm |
| lesao | **sem gaussiana** | lesão pequena é o caso que mais some |

Antes de virar default, rodar o benchmark com σ por classe e comparar por faixa
de escala (o critério do §16: vencer em **cada** faixa, não na média).

## Suavização no domínio da malha (Fase 3)

`reconstruct_surface` ganhou `mesh_smoothing` (`"taubin"` default — comportamento anterior
bit a bit —, `"windowed_sinc"`, `"none"`) mais `ws_iters` e `ws_pass_band`.

Benchmark de Taubin 4/8/12/20 e WindowedSinc por faixa de calibre:
[`RELATORIO-VALIDACAO-RECONSTRUCAO.md` §8](RELATORIO-VALIDACAO-RECONSTRUCAO.md).
Resultado: **nenhuma variante supera o baseline sob o critério declarado**, e o `taubin_iters = 4`
segue como default. A primeira execução reprovava as quatro variantes por um **artefato do
instrumento** (dimensão medida por bounding box, que mede a escada e não o calibre) — corrigido
para `calibre_mediano_secao`, com autoteste que falha se calibre e volume discordarem de sinal.

## Master mesh

`--master` gera a referência de fidelidade: **sem decimação de VR** e **sem o
afastamento artificial de −0,15 mm** (a master representa a anatomia; z-fighting
é problema do renderer, não da geometria). O relatório grava a proveniência:

```json
"reconstrucao": {"metodo": "...", "master": true, "afastamento_artificial": false, "max_tris": null}
```

Os derivados (web/quest/AR) devem sair da master — nunca o contrário.

## Correções de bug feitas nesta fase

- `flying_edges`/`surface_nets` estouravam `AttributeError` quando a isosuperfície
  saía vazia (estrutura dissolvida). Agora devolve `None` = "ausente".
- O fantoma tinha **discretização não-monotônica**: `_grade` gerava `n` par ou
  ímpar conforme o diâmetro, deslocando meio voxel a rede de amostragem — d=2,0 mm
  produzia máscara menor que d=1,5 mm. Corrigido com supersampling (3³ por voxel)
  + `n` forçado a ímpar. Um fantoma que não cresce com o diâmetro não detecta
  regressão nenhuma.
