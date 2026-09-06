# VRmed — execução autônoma, Fases 13 a 17

Data: 2026-09-06 · Commit inicial `a590aa3` · Branch `master` · **Nada treinado**
Nenhum conjunto congelado tocado · Nenhuma linha de histórico apagada

---

# Resumo executivo

Cinco fases, das quais **quatro concluídas e uma parcial declarada**. O saldo em uma frase:
**o projeto fechou o único critério de prontidão que estava sob seu controle, encontrou o
melhor candidato a teste independente em quinze fases, manteve o MASTER de reconstrução por
medição — e continua com o treino bloqueado, agora por um motivo mais bem caracterizado.**

| Fase | Resultado | O que decidiu |
|---|---|---|
| **13** — Ontologia | **A** | `ESOPHAGUS_ONTOLOGY_V1` congelada · **K4 RESOLVIDO** · 13 testes de regressão |
| **14** — Prontidão | **C** | cenário C · K1, K2, K3 bloqueados por razões independentes |
| **15** — Teste independente | **B** (parcial) | **LyNoS** — 79 candidatos, 230 consultas · classe E |
| **16** — Independência | *em curso* | auditoria do TotalSegmentator v2 dataset a dataset |
| **17** — Reconstrução | **A** | **MASTER MANTIDO** · 182 medições em fantoma + 44 em anatomia real · 4 achados de instrumento |

**Nove achados de instrumento** ao longo da noite — sete deles erro do próprio trabalho desta
execução, todos encontrados por controle positivo e todos corrigidos. É o número que melhor
descreve a noite: **o que mais rendeu foi apontar os instrumentos para si mesmos.**

# Estado inicial

| | |
|---|---|
| Commit | `a590aa3adda8be8aa9dd14ddb58ed01cf62f5c69` · `master` · árvore **limpa** |
| Python · PyTorch · CUDA | 3.13.11 · 2.6.0+cu124 · 12.4 (`cuda.is_available() = True`) |
| GPU · RAM · CPUs · Disco | RTX 4060 Ti 16.380 MiB · 31,8 GiB (15,3 livres) · 12 · 170,4 GiB livres |
| VTK · SimpleITK · pydicom · trimesh | 9.7.0 · 2.5.6 · 3.0.2 · 5.0.0 |

**Split congelado, verificado no início e no fim:** `sha256` `6e54c02b58bbb9b3a1667d4672eddef6`,
**mtime 2026-09-04T21:19:49** — anterior a esta execução. `development` 30 · `validation` 15 ·
`test` 15. **Nenhum `case_id` de `validation` ou `test` foi lido.**

# Fase 13 — ESOPHAGUS_ONTOLOGY_V1

**Resultado: A. K4 RESOLVIDO.**

A ontologia já estava 90 % correta — a Fase 9 removera cricoide e junção gastroesofágica por
medição. Faltavam três coisas: qualificar duas linhas históricas, criar um documento
normativo versionado, e criar o mecanismo que impede a definição de derreter de novo.

**O precedente que justifica o mecanismo:** a Fase 6 escreveu *"limite superior = cricoide"*;
a Fase 7 mediu que o cricoide não é localizável; **a contradição ficou de pé entre as duas
fases até a Fase 9 removê-la.**

**Congelado:** máscara binária **preenchida** · **parede e lúmen NÃO separados** · extensão
longitudinal **HERDADA / NÃO AVALIÁVEL** · 8 métricas · mm físicos · RTOG 1106.

**Histórico preservado:** três linhas **qualificadas**, zero apagadas.

**O achado da fase.** O teste 13 é controle positivo — injeta violações e exige que o varredor
as ache. Ele **reprovou a primeira versão do varredor** (3 de 4 violações) e depois **reprovou
o relatório desta própria fase**, duas vezes: uma citação de fixture lida como proposta, e o
marcador de negação `proibid` que não casava `proíbem`. *Um varredor que devolve zero por estar
quebrado é pior que nenhum varredor.*

**Correção contra mim mesmo:** banir `digital twin` era errado. Três documentos de análise
usam o termo corretamente — para **contrastar** com *patient-specific*. A regra virou de
companhia. Termo canônico registrado: **patient-specific 3D model**.

# Fase 14 — prontidão para treinamento

**Resultado: C — nenhum TEST defensável.** Esta fase não treinou nada.

| Critério | Estado | Razão |
|---|---|---|
| **K1** desenho TRAIN/VAL/TEST | **BLOQUEADO** | LCTSC `development` consumido; `validation`/`test` congelados e o `test` **já foi consumido** na Fase 7 para a hipótese cardíaca |
| **K2** baseline sem leakage conhecido | **BLOQUEADO** | 420 de 1.559 imagens do treino do TS v2 **não são atribuídas** |
| **K3** avaliação futura independente | **BLOQUEADO** | o único candidato com objeto e desenho certos (iCurveE) não foi obtido |
| **K4** alvo congelado | **RESOLVIDO** | Fase 13 |

**Guardas executadas:** 30 testes + 21 guardas com controle positivo.
`protocolo_esofago --mutacao` devolve **10/10** — as guardas anti-leakage derrubam o autoteste
quando desligadas, logo não estão zeradas.

**Retorno da Fase 15:** K1 e K3 mudaram de **motivo**, não de **estado** — de *"não há
candidato"* para *"há um candidato cuja independência não é estabelecível pelo mesmo motivo
que trava K2"*. É um bloqueio melhor caracterizado, não um bloqueio menor.

# Fase 15 — busca de teste independente

**Resultado: B — parcialmente defensável, com ressalvas.** **Parcial e declarada como tal:** a
sessão anterior morreu durante a etapa de fonte primária; os 7 arms concluíram e foram
**recuperados do journal do workflow**, mas as fichas restantes e as três rodadas de refutação
**não rodaram**. Portanto **não houve passe cético** sobre estes resultados.

**79 candidatos · 230 consultas registradas · A=0 · B=1 · C=57 · D=14 · E=7.**

## O achado — LyNoS

15 TCs mediastinais (St. Olavs / NTNU, Noruega), esôfago em **arquivo NIfTI próprio e
binário**, canal não-DICOM, fora do TCIA e de tudo que o VRmed usou.

**A lacuna que o travava foi fechada por MEDIÇÃO, não por documento.** Nenhuma fonte primária
menciona RTOG 1106 nem critério parede/lúmen — pela regra da Fase 9, seria eliminado por
"definição não documentável". Baixados **1,80 MiB** (2 máscaras, tamanho conferido por `HEAD`
antes; nenhuma TC de 180–263 MB, nenhum ZIP de 2,90 GB):

| | Pat1 | Pat2 |
|---|---|---|
| valores únicos | `{0, 1}` | `{0, 1}` |
| **fração de buracos** | **0,028 %** | **0,001 %** |

**É exatamente o que a `ESOPHAGUS_ONTOLOGY_V1` especifica.** Este é o retorno concreto de ter
congelado a ontologia horas antes: um candidato que a regra antiga descartaria por silêncio
documental passa agora por **verificação direta do artefato**.

**Por que é E e não A.** A anotação é de 2019, **três anos antes** do preprint do
TotalSegmentator — o GT **não pode** ser *model-in-the-loop* dele. Mas **anterioridade da
anotação não é anterioridade da imagem**, e as 420 imagens não atribuídas vêm de *"other
institutions"*. Três ressalvas medidas: **n=15**, **TC com contraste e diagnóstica** (não de
planejamento), e **conflito de licença** entre três fontes oficiais do mesmo dataset (Zenodo
`cc-by-4.0`, HuggingFace `mit`, GitHub `MIT`/BSD-2).

**A classe D é o achado mais desconfortável:** 14 datasets existem e não podem ser obtidos
dentro das travas — entre eles o `RADCURE` (3.337 RTSTRUCT) e **um estudo de *edge roughness*
com múltiplos médicos no esôfago**, exatamente o desenho que a Fase 11 procurou por duas
ondas. Nenhum termo aceito, nenhuma conta criada, nenhum acesso solicitado.

# Fase 16 — independência do baseline

**EM CURSO** no encerramento deste relatório. Workflow `wqo33i814`, 5 arms auditando pesos e
model card, documentação pública do TotalSegmentator, manifestos locais, o par
`Dataset343_mediastinum_1786subj` × SAROS, e LCTSC × NSCLC-Radiomics.

*(Esta seção é atualizada quando a fase concluir; o relatório é publicado com ela em aberto
porque o restante está fechado e o enunciado manda não deixar relatório incompleto.)*

**O que já se sabe, das fases anteriores:** o SAROS mostrou forte correspondência com
`pericardium`, e a Fase 8 registrou que o dataset de treino do task 343 tem os **rótulos
idênticos** aos do SAROS e proveniência com placeholders (`reference: "Jakob"`,
`licence: "-"`). **Dice alto entre modelo e dataset é exatamente o que se esperaria se o
dataset estivesse no treino** — o sinal aponta para os dois lados.

# Fase 17 — benchmark de reconstrução

**Resultado: MASTER MANTIDO.** 182 medições (14 variantes × 13 fantomas), 8/8 métricas
congeladas, em `docs/overnight/reconstruction_benchmark.csv`.

**O número que decide é o erro contra a fórmula fechada** — Dice contra a máscara é
tautológico com σ=0 e dá 1,0000 em toda variante de marching cubes.

| Variante | mediana \|erro %\| |
|---|---:|
| `mc_taubin20` | 1,31 |
| **`MASTER` (taubin4)** | **1,57** |
| `sdf` | 2,88 |
| `mc_sigma1` | 6,13 |
| `surface_nets` | **15,85** |

**A troca que a mediana esconde:** mais Taubin melhora monotonicamente estrutura grande e
lisa e **piora monotonicamente estrutura fina**. De taubin4 para taubin20: ganho de 0,27 pp na
esfera, perda de **2,11 pp** no tubo de 3 mm — quase 8× maior. **O alvo central do projeto é
tubular e fino: a evidência aponta para menos suavização, não mais.**

**σ=0 confirmado por medição.** `sigma=1` erra a topologia nas **duas direções opostas ao
mesmo tempo**: funde `dois_cilindros_contato` (2 componentes → 1) **e** rompe
`ponte_fina_gap4` (1 → 2).

**Surface Nets permanece experimental, agora com número:** −71,70 % de volume na esfera de
6 mm, −58,90 % no tubo fino, Dice mínimo 0,1950.

**Derivadas.** LOD 50 % custa ASSD máximo 0,0047 mm e devolve metade do tamanho — mas
introduz arestas não-manifold que a extração não tinha; LOD 10 % rompe a ponte fina.
**Draco: 7,74×–13,20× de compressão por erro de vértice de 0,00099–0,00328 mm** — micrômetros,
três ordens de grandeza abaixo do piso de resolução da grade.

## Anatomia real — 44 medições em quatro calibres

**FATO.** O caso `cta-cardio` está **fora de todo split congelado**. Quatro calibres:
esôfago 25,3 · traqueia 46,6 · aorta 132,3 · coração 494,5 mL.

**O achado.** O erro de volume é **monotônico no tamanho da estrutura, em 11 de 11 variantes,
sem uma única inversão**, e sempre **negativo** — toda extração subestima.

| MASTER | esôfago | traqueia | aorta | coração |
|---|---:|---:|---:|---:|
| erro de volume | **−0,450 %** | −0,199 % | −0,160 % | −0,040 % |

**INFERÊNCIA.** É função da razão superfície/volume, não do método: objeto pequeno tem mais
fronteira por unidade de volume, e é na fronteira que a discretização cobra. **O esôfago é o
pior caso entre as estruturas reais do projeto — 11× o erro do coração.**

**E Surface Nets quebra watertight nas quatro estruturas, sem exceção** (8/8/4/4 arestas
não-manifold), com −0,78 % a −7,05 % de volume. Nos fantomas ele só perdia volume; em anatomia
real quebra a topologia. Uma malha não-watertight **não tem volume definido** — e o VRmed
publica volume.

# O que mudou no VRmed

1. **`ESOPHAGUS_ONTOLOGY_V1` existe e é normativa** — em duas formas que a suíte obriga a
   concordar, com 13 testes de regressão. **K4 saiu de NÃO para RESOLVIDO.**
2. **Um candidato real a teste independente foi identificado** (LyNoS) e sua compatibilidade
   com a ontologia foi **medida**.
3. **O MASTER de reconstrução ganhou justificativa quantitativa** — antes era decisão
   congelada; agora `σ=0` e `Taubin=4` têm o número que os sustenta e o número que rejeita as
   alternativas, **em fantoma com resposta fechada e em anatomia real**.
4. **Draco passou de "lossy, não medido nesta escala" para 7,7×–13,2× com perda em
   micrômetros.**
5. **Cinco instrumentos novos** com autoteste: `ontologia_esofago.py`, `benchmark_fase17.py`,
   e as suítes que os defendem.
6. **A suíte de regressão passou de 18 para 31 testes.**

# O que NÃO mudou

- **Nada foi treinado.** Nenhum epoch, nenhum modelo, nenhuma otimização.
- **`BASELINE_ESOFAGO_V1` intocado** — Dice 0,7880, nenhum número recalculado.
- **`Tier2_TEST` e `Tier2_VALIDATION` não foram lidos** — só as contagens; `sha256` e `mtime`
  do split conferidos no início e no fim.
- **O MASTER de reconstrução não foi substituído.** Candidatas registradas, nenhuma promovida.
- **Nenhuma linha de histórico apagada.**
- **Nenhum e-mail enviado, nenhuma conta criada, nenhum EULA aceito, nenhum acesso solicitado.**

# Evidências novas

| Evidência | Onde |
|---|---|
| Máscara do LyNoS é binária e preenchida (buracos 0,028 %) | Fase 15 §3.1 |
| `sigma=1` funde e rompe topologia ao mesmo tempo | Fase 17 §3.1 |
| Surface Nets perde 71,7 % do volume em estrutura de 6 mm | Fase 17 §4 |
| Draco: 7,7×–13,2× por 0,0009–0,0033 mm | Fase 17 §6 |
| Mais Taubin melhora o grande e piora o fino, monotonicamente | Fase 17 §2.1 |
| **O erro de volume escala com o tamanho da estrutura em 11/11 variantes** — o esôfago é o pior caso real | Fase 17 §6-bis |
| Surface Nets quebra watertight nas 4 estruturas reais | Fase 17 §6-bis |
| `tubo_fino_d2_aniso` não fecha em 14/14 variantes — limite sub-voxel | Fase 17 §3.3 |
| 230 consultas com fonte, string e data | Fase 15 §4 |
| 17ª coleção do TCIA fora da API anônima (`OPC-Radiomics`) | Fase 15 §4 |

# Os nove achados de instrumento

**Sete são erro do próprio trabalho desta noite.** Todos foram encontrados por controle
positivo — nenhum apareceu sozinho.

| # | Fase | O que estava errado |
|---|---|---|
| 1 | 13 | varredor achava 3 de 4 violações injetadas (regex só casava o infinitivo) |
| 2 | 13 | dois falsos positivos: linhas que **proíbem** a frase eram acusadas de cometê-la |
| 3 | 13 | banir `digital twin` era errado — o uso para contrastar é o correto |
| 4 | 13 | marcador de negação era sufixo (`proibid`), não radical — não casava `proíbem` |
| 5 | 17 | `surface_nets` medido **duas vezes** como se fossem variantes distintas |
| 6 | 17 | três colunas de topologia **vazias** por chave inventada; `dict.get` silencioso |
| 7 | 17 | **duas das oito métricas congeladas ausentes do CSV** — a ontologia congelada horas antes não impediu o instrumento de ignorá-la |
| 8 | 17 | **Hausdorff do Draco errado por quatro ordens de grandeza** (10,27 mm × 0,0009 mm): `trimesh` não decodifica Draco, avisa em `stderr` e **termina com código 0** |
| 9 | 15 | a eliminação do HaN-Seg tinha o motivo errado publicado |

**O #8 é o mais instrutivo.** O número falso era plausível o bastante para entrar num
relatório. *Um erro que não interrompe o processo é o mais caro de todos.*

# Bloqueios ainda existentes

1. **420 de 1.559 imagens do treino do TotalSegmentator v2 não são atribuídas.** É a raiz de
   K2 e, por consequência, de K1 e K3. **Nenhuma busca fecha essa lacuna — ela se fecha do
   lado do modelo, não do lado do dado.**
2. **Não existe conjunto com dois contornos humanos de esôfago no mesmo exame** (Fases 11–12).
3. **14 datasets inacessíveis** dentro das travas — lacuna declarada, nunca "não tem".
4. **Conflito de licença do LyNoS** entre três fontes oficiais.
5. **A Fase 15 não teve passe cético.**

# Critérios

| | Estado | Razão |
|---|---|---|
| **K1** | **BLOQUEADO** | há candidato (LyNoS), mas independência não estabelecível |
| **K2** | **BLOQUEADO** | 27 % do treino do baseline não é declarado *(Fase 16 em curso)* |
| **K3** | **BLOQUEADO** | mesma raiz de K1 |
| **K4** | **RESOLVIDO** | `ESOPHAGUS_ONTOLOGY_V1`, 13 testes |

# Treinamento

# **BLOQUEADO**

Um critério resolvido de quatro não desbloqueia nada. **INFERÊNCIA:** K4 era o único sob
controle do projeto; os outros três dependem de terceiros — de uma lista de treino auditável,
ou de um conjunto cuja independência seja estabelecível.

# MASTER de reconstrução

# **MANTIDO**

`marching_cubes · σ=0 · Taubin=4 · level=0,5 · offset=0 · sem decimação`

**Candidatas registradas, nenhuma promovida:** `mc_taubin8/12/20` ganham 0,07–0,27 pp em
estrutura grande e perdem 0,71–2,11 pp em estrutura fina — troca desfavorável para um alvo
tubular. **Rejeitadas por medição:** `mc_sigma1` (funde e rompe) e `surface_nets` (−71,7 %).

# Datasets encontrados

**79 candidatos.** Um relevante: **LyNoS** (classe E). Zero de classe A — e a razão é sempre a
mesma lacuna de 27 %.

# Questões ainda abertas

1. O LyNoS sobrevive a um passe cético de independência?
2. O conflito de licença dele resolve para qual das três?
3. **O `Dataset343` e o SAROS são o mesmo conjunto?** *(Fase 16)*
4. n=15 e TC com contraste bastam para uma comparação com sentido?
5. O `RADCURE` valeria uma solicitação formal de acesso — decisão do usuário?

# Recomendações

- **RECOMENDAÇÃO.** Resolver o conflito de licença do LyNoS **antes** de qualquer uso.
- **RECOMENDAÇÃO.** Submeter o LyNoS ao passe cético que esta execução não chegou a rodar.
- **RECOMENDAÇÃO.** Considerar, como fase futura, se existe baseline com **treino auditável** —
  é a única via que ataca K2 sem depender de dado novo. **Não é recomendação de trocar o
  baseline**, que continua congelado.
- **RECOMENDAÇÃO.** Não promover nenhuma variante de reconstrução com base nesta fase.

# Próxima única ação recomendada

**Submeter o LyNoS a um passe cético de independência e resolver seu conflito de licença — na
mesma rodada, porque a licença decide se o candidato pode ser usado e a independência decide
se ele significa alguma coisa.**

É a única ação que pode mover um critério de estado: se a independência do LyNoS for
estabelecível, K1 e K3 saem de BLOQUEADO. Se não for, o bloqueio fica provado estrutural — e
aí a pergunta seguinte é sobre o **baseline**, não sobre o dado.
