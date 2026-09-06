# Fase 17 — benchmark profundo de reconstrução 3D

Data: 2026-09-06 · 182 medições · 14 variantes × 13 fantomas · 8/8 métricas congeladas · Nada treinado

> **MASTER: MANTIDO.** Nenhuma variante o supera onde importa. Três variantes ficam
> **empatadas** dentro do ruído no volume analítico e **perdem** em outra dimensão;
> duas são **claramente piores** e a medição diz por quê.
>
> `docs/overnight/reconstruction_benchmark.csv` — 182 linhas, uma por (variante × estrutura).

---

## 1. Desenho

**FATO.** 13 fantomas sintéticos, 11 deles já existentes no projeto (`scripts/validation/phantom.py`),
reusados em vez de reconstruídos. Cada um estressa uma coisa: curvatura alta, estrutura
pequena (d=6 mm), estrutura fina (d=3 mm e d=2 mm), anisotropia da grade real do LCTSC
(0,977 × 0,977 × 3,0 mm), cavidade interna, bifurcação, fusão de estruturas em contato,
componentes separados por 2 mm, ponte fina, superfície aberta por corte.

**Por que fantoma e não caso real:** aqui a resposta certa é **fórmula fechada** — a esfera
tem π/6·d³, o cilindro π/4·d²·h. Num caso real o erro de reconstrução se confunde com o de
segmentação, e a Fase 10 mediu o quanto isso custa. No fantoma, a única fonte de erro é a
reconstrução — que é o objeto desta fase.

### 1.1 O que Dice mede aqui, e o que ele não mede

**FATO.** Dice/ASSD/HD95 de malha contra a máscara que a gerou são **tautológicos** com
σ=0: a malha rasterizada de volta reproduz a máscara por construção — e é por isso que
**todas** as variantes de marching cubes marcam Dice 1,0000. Eles entram como **detector de
dano** (decimação, suavização agressiva), **nunca** como prova de acurácia anatômica.

**O número que informa é o erro contra a fórmula.**

## 2. Fidelidade — erro contra a fórmula fechada

**FATO.** |erro %| do volume, mediana sobre as 5 estruturas com solução analítica:

| Variante | mediana \|%\| | máx \|%\| | leitura |
|---|---:|---:|---|
| `mc_taubin20` | **1,31** | 23,26 | melhor mediana, pior extremo |
| `mc_taubin12` | 1,44 | 22,42 | |
| `mc_taubin8` | 1,51 | 21,86 | |
| **`MASTER_mc_taubin4`** | **1,58** | **21,15** | **referência** |
| `mc_taubin2` | 1,61 | 20,70 | |
| `mc_taubin0` | 1,65 | 20,86 | sem suavização |
| `flying_edges` | 1,67 | 21,74 | |
| `mc_windowed_sinc` | 1,67 | 21,74 | |
| `sdf` | 2,88 | 21,15 | |
| `mc_sigma1_taubin4` | **6,14** | **52,50** | σ>0 é destrutivo |
| `surface_nets` | **15,86** | **71,70** | pior por uma ordem de grandeza |

### 2.1 A troca que a mediana esconde

**FATO**, erro com sinal, por estrutura:

| Variante | esfera d20 | esfera **d6** | cilindro | **tubo fino d3** |
|---|---:|---:|---:|---:|
| `mc_taubin0` | −1,65 | −20,86 | −0,85 | **+20,19** |
| **`MASTER` (taubin4)** | −1,58 | −20,24 | −0,72 | **+21,15** |
| `mc_taubin8` | −1,51 | −19,77 | −0,59 | +21,86 |
| `mc_taubin20` | **−1,31** | **−18,67** | **−0,20** | **+23,26** |

**INFERÊNCIA.** Mais Taubin melhora monotonicamente as estruturas grandes e lisas e
**piora monotonicamente a estrutura fina**. Não é "taubin20 é melhor" — é uma troca com
sinais opostos. Ganho de 0,27 pp na esfera custa 2,11 pp no tubo fino, **quase 8× mais**.

**FATO.** A esfera d=6 mm erra ~20 % em **todas** as variantes de marching cubes. Isso é
**piso de resolução**, não diferença de método: 6 mm numa grade de 1 mm.

## 3. Topologia

**FATO.** Todas as variantes de **extração** produzem: 0 arestas de borda, 0 arestas
não-manifold, e a mesma contagem de componentes conexos. A extração é limpa.

### 3.1 O achado que confirma σ=0 por medição

**FATO.** `mc_sigma1_taubin4` erra a topologia nas **duas direções opostas**, ao mesmo tempo:

| Fantoma | Correto | MASTER | `sigma1` |
|---|---:|---:|---:|
| `dois_cilindros_contato` | 2 | **2** ✓ | **1** ✗ — **fundiu** duas estruturas |
| `ponte_fina_gap4` | 1 | **1** ✓ | **2** ✗ — **rompeu** a ponte |

**INFERÊNCIA.** Borrar a ocupação antes de extrair funde o que deveria estar separado **e**
rompe o que deveria estar ligado. O σ=0 do MASTER não é conservadorismo — é a única
configuração medida que acerta os dois casos.

### 3.2 Cavidades

**FATO.** Cavidade interna preservada (2 componentes: casca externa + casca da cavidade) em
**todas** as variantes de extração, inclusive Surface Nets. Nenhuma fechou cavidade.

### 3.3 A estrutura que ninguém reconstrói fechada

**FATO.** `tubo_fino_d2_aniso` (tubo de 2 mm em fatias de 3 mm) sai **não-watertight em
14/14 variantes**. Não é falha de método — é sub-voxel: 2 mm de diâmetro em dz de 3 mm.

**RECOMENDAÇÃO.** Registrar como limite do pipeline, não como defeito de variante.

## 4. Surface Nets — mantém-se experimental

**FATO.** Perde por margem grande, e a perda é **sistemática de volume**:

| | esfera d20 | esfera d6 | tubo fino d3 | cilindro |
|---|---:|---:|---:|---:|
| erro vs fórmula | −9,24 % | **−71,70 %** | **−58,90 %** | −13,55 % |
| Dice vs máscara | — | — | mín **0,1950** | — |

Volume da cavidade: 4,2130 mL contra 4,6564 do MASTER; tubo oco 7,9185 contra 8,2834.

**INFERÊNCIA.** Ele encolhe a superfície. Em estrutura pequena ou fina isso destrói o
volume. **RECOMENDAÇÃO:** permanece experimental, como a regra 15 do enunciado já determina.
Esta fase acrescenta o número que justifica a regra.

### 4.1 Achado de instrumento — meu erro, corrigido

**FATO.** A primeira versão deste benchmark listava `surface_nets` e
`surface_nets_sem_taubin` como duas variantes. **São a mesma.** `reconstruction.py` fixa
`suavizar_malha=False` para esse método (linha 315) — ele usa a suavização interna do
`vtkSurfaceNets3D` e **ignora** `taubin_iters`/`mesh_smoothing`. Verificado: os vértices são
byte a byte idênticos entre Taubin 4 e 0, enquanto em marching cubes diferem.

Não é bug do módulo — é decisão documentada dele. **Foi erro do benchmark**, que mediu a
mesma coisa duas vezes. O autoteste agora tem um controle que falha se o comportamento mudar.

### 4.2 Segundo achado de instrumento

**FATO.** A primeira versão gravou **três colunas vazias** — `components`,
`boundary_edges`, `nonmanifold_edges` — porque usei chaves inventadas
(`componentes`, `arestas_de_borda`) em vez das reais (`n_componentes`,
`n_boundary_edges`, `n_arestas_nao_manifold`). `dict.get` com default silencioso devolveu
`""` e o CSV saiu completo, sem erro nenhum.

**INFERÊNCIA.** Toda a §3 desta fase teria sido escrita sobre colunas vazias. O autoteste
agora exige que essas colunas venham preenchidas num caso conhecido.

### 4.3 Terceiro achado de instrumento — duas métricas congeladas sumiram

**FATO.** O CSV saiu com as colunas `iou` e `volume_error_pct` **vazias**. Causa: pedi ao
módulo as chaves `iou` e `volume_malha_ml`, que **não existem** — os nomes reais são
`volume_mesh_ml` e `volume_error_pct`, e **IoU o módulo não fornece**. Outra vez, `dict.get`
devolveu `None` em silêncio.

**INFERÊNCIA — e é o ponto.** A `ESOPHAGUS_ONTOLOGY_V1`, congelada há três horas na Fase 13,
lista **oito** métricas. Este benchmark, escrito depois dela, **entregou seis**. Congelar uma
lista num documento não impede um instrumento de ignorá-la.

**Correção:** `volume_error_pct` lido da chave certa; **IoU calculado por identidade** —
para duas máscaras binárias na mesma grade, `IoU = D / (2 − D)` exatamente, não por
aproximação. O autoteste agora exige as seis colunas de fidelidade preenchidas e confere a
identidade IoU↔Dice.

**RECOMENDAÇÃO.** A suíte da ontologia deveria ganhar um teste que varre os CSV publicados e
falha quando uma métrica congelada não aparece. Não foi feito nesta execução — fica
registrado como dívida.

## 5. Derivadas — LOD (decimação sobre o MASTER)

**Regra respeitada: aplicadas SOBRE a malha do MASTER, nunca no lugar dela.**

**FATO:**

| Variante | triângulos | GLB (MB) | Dice med | Dice mín | ASSD máx (mm) | não-manifold máx |
|---|---:|---:|---:|---:|---:|---:|
| **MASTER** | 3.232 | 0,0590 | 1,0000 | 1,0000 | 0,0000 | **0** |
| `LOD_decim50` | 1.616 | 0,0299 | 1,0000 | 0,9972 | 0,0047 | 4 |
| `LOD_decim25` | 808 | 0,0153 | 0,9984 | 0,9700 | 0,0405 | **11** |
| `LOD_decim10` | 322 | 0,0066 | 0,9789 | **0,6391** | **0,5063** | 3 |

**FATO.** `LOD_decim10` **rompe a ponte fina** (1 componente → 2) e o Dice mínimo despenca
para 0,6391.

**INFERÊNCIA.** A decimação a 50 % custa quase nada em fidelidade (ASSD máximo 0,0047 mm)
e devolve metade do tamanho — mas **introduz arestas não-manifold**, que a extração não
tinha. A 10 % o dano é estrutural, não cosmético.

**RECOMENDAÇÃO.** LOD 50 % é o único nível cujo custo é aceitável sem inspeção caso a caso.
Abaixo disso, exige verificação de topologia por estrutura. **Nada disso altera o MASTER** —
são níveis de detalhe derivados, para transporte.

## 6. Compressão Draco — derivada de transporte

**Regra respeitada: aplicada SOBRE o GLB do MASTER, nunca no lugar da geometria em disco.**

**FATO**, medido com `gltf-transform 4.3.0` e o decodificador **DracoPy** — o mesmo que o
`DRACOLoader` roda no navegador:

| Malha | ratio | KB → KB | erro vértice máx | RMS vértice | Hausdorff | erro área | erro volume | tri/vert preservados |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| `esfera_d20_iso` | 7,74× | 65,1 → 8,4 | 0,00099 mm | 0,00057 mm | 0,0009 mm | 0,0006 % | 0,0010 % | ✔ |
| `tubo_fino_d3` | 8,00× | 18,6 → 2,3 | 0,00172 mm | 0,00110 mm | 0,0016 mm | 0,0029 % | 0,0090 % | ✔ |
| `bifurcacao_d8` | 10,13× | 108,4 → 10,7 | 0,00328 mm | 0,00196 mm | 0,0026 mm | −0,0016 % | −0,0020 % | ✔ |
| `tubo_oco_20_12` | **13,20×** | 188,6 → 14,3 | 0,00213 mm | 0,00126 mm | 0,0017 mm | 0,0022 % | 0,0020 % | ✔ |

**INFERÊNCIA.** Draco é lossy — quantiza posição — mas a perda medida é de **micrômetros**,
três ordens de grandeza abaixo do piso de resolução da grade (1,953 mm) e do menor detalhe
anatômico representável. Contagem de vértices e triângulos preservada exatamente em 4/4.
**Compressão de 7,7× a 13,2× por um custo geométrico que a grade nem representa.**

### 6.1 Quarto achado de instrumento — o número que eu quase publiquei

**FATO.** A primeira medição usou `trimesh.load` no GLB comprimido e devolveu Hausdorff de
**10,27 a 34,02 mm**. Números plausíveis o bastante para entrar num relatório — e
**inteiramente falsos**.

Causa, e o próprio trimesh avisa em `stderr`:
*"`KHR_draco_mesh_compression` GLTF extension has no handler, values are placeholder zeros"*.
Ele não decodifica Draco; devolveu **zeros de placeholder**, e a "distância" medida era a
distância entre a malha real e um objeto degenerado.

**A medição correta usa `scripts/validation/compressao.py`**, que já existia no projeto
exatamente para isso e traz o decodificador oficial. Diferença entre o número falso e o
verdadeiro: **10,27 mm contra 0,0009 mm — quatro ordens de grandeza.**

**INFERÊNCIA.** O aviso estava em `stderr` e passou despercebido porque o comando terminou com
código 0. Um erro que não interrompe o processo é o mais caro de todos.

## 7. Performance

**FATO.** Todas as variantes de extração custam entre 0,0056 s e 0,0090 s por fantoma, com
3.232 triângulos e 0,059 MB de GLB. **A diferença de custo entre variantes é irrelevante
nesta escala** — a decisão é de fidelidade e topologia, não de performance.

**FATO.** GPU não foi usada: a reconstrução é CPU/VTK e os fantomas cabem em memória. Não
houve benefício real em usar CUDA aqui, e forçá-la seria custo sem retorno.

## 8. Decisão

# **MASTER MANTIDO** — `marching_cubes · σ=0 · Taubin=4 · level=0,5 · offset=0 · sem decimação`

**Candidatas registradas, não promovidas:**

| Candidata | O que ganha | O que perde | Veredito |
|---|---|---|---|
| `mc_taubin8` / `mc_taubin12` / `mc_taubin20` | 0,07–0,27 pp no volume analítico de estruturas grandes | 0,71–2,11 pp na estrutura fina — perda ~8× maior que o ganho | **candidata fraca**; a troca é desfavorável para um alvo tubular como o esôfago |
| `flying_edges` | nada mensurável | 0,09 pp pior que o MASTER | equivalente; sem motivo para trocar |
| `mc_windowed_sinc` | nada mensurável | idêntico ao `flying_edges` | equivalente |
| `sdf` | nada | 1,30 pp pior na mediana | pior |
| `surface_nets` | — | −71,70 % em estrutura pequena | **experimental, como já era** |
| `mc_sigma1` | — | funde E rompe topologia | **rejeitada por medição** |

**INFERÊNCIA que mais importa para o VRmed.** O alvo central do projeto — o esôfago — é uma
estrutura **tubular e fina**. A dimensão em que mais Taubin piora é exatamente essa. Se
alguma variante for revisitada, a evidência aponta para **menos** suavização, não mais — e
mesmo assim o ganho está dentro do ruído.

## 9. Limitações

- **FATO.** Fantoma sintético não é anatomia. Nada aqui mede acurácia de segmentação.
- **FATO.** Dice/ASSD/HD95 contra a máscara de origem são tautológicos com σ=0 (§1.1).
- **FATO.** A medição do Draco cobriu 4 malhas, não as 13.
- **FATO.** Só uma grade anisotrópica foi testada (a do LCTSC). Outras espessuras de fatia
  não foram varridas.
- **INFERÊNCIA.** Os fantomas cobrem os modos de falha conhecidos, não os desconhecidos.

---

```
FASE 17 CONCLUÍDA
MASTER: MANTIDO
VARIANTES MEDIDAS: 14 × 13 fantomas = 182 linhas
CANDIDATAS: mc_taubin8/12/20 (troca desfavorável para estrutura fina) — nenhuma promovida
REJEITADAS POR MEDIÇÃO: mc_sigma1 (funde e rompe topologia), surface_nets (−71,7% em estrutura pequena)
LOD: 50% aceitável; 25% exige verificação; 10% rompe ponte fina
DRACO: 7,7x a 13,2x de compressao por perda de 0,0009-0,0033 mm (micrometros; 3 ordens abaixo do piso da grade)
ACHADOS DE INSTRUMENTO: 4 (surface_nets medido duas vezes; 3 colunas de topologia vazias; 2 metricas congeladas ausentes; Hausdorff do Draco falso por 4 ordens de grandeza)
PRÓXIMO PASSO: acrescentar à suíte da ontologia um teste que varre os CSV publicados e falha quando uma métrica congelada não aparece
```
