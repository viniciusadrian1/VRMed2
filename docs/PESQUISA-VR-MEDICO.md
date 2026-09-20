<!-- Pesquisa feita em 2026-09-17 varrendo simuladores cirurgicos em VR, atlas de
anatomia 3D/VR, literatura de gamificacao em educacao medica, documentacao tecnica
de WebXR/Quest e formatos de evento. Cada afirmacao numerica traz a fonte; o que e
opiniao esta marcado como "observacao, sem fonte". -->

# VRmed — como os melhores fazem e o que a gente faz a seguir

Documento de trabalho. Todo número aqui tem fonte (URL) ou é cálculo feito a partir do nosso próprio código — e está marcado como tal. Onde é opinião, está escrito "observação, sem fonte".

---

## 1. Diagnóstico honesto

Li o código antes de comparar: `components/viewer/Scene.tsx`, `components/viewer/SafeEnvironment.tsx`, `components/viewer/OrganModel.tsx`, `components/arena/*`, `components/duelo/*`, `components/clinica/*`, `lib/quiz.ts`, `lib/store.ts`, `lib/duelo-salas.ts`, `app/api/duelo/route.ts`, `public/descriptions/`.

**O VRmed não tem problema de falta de peças. Tem problema de onde as peças vivem e do que sobra depois da partida.**

Cinco constatações verificadas no código, não inferidas:

**(a) Nenhuma estrutura tem nome dentro do VR.** `identifyStructure()` roda no clique (`OrganModel.tsx`), mas quem mostra é `components/viewer/InspectBar.tsx`, que é DOM — e DOM some na sessão imersiva. Dentro do óculos a pessoa gira um modelo bonito e mudo. Isso é a função número 1 de todo concorrente do campo: o Dissection Master XR anuncia 3.000+ estruturas "named, annotated, and linked to additional information" (https://www.medicalholodeck.com/en/human-anatomy-atlas-in-virtual-reality-dissection-master-xr/); BioDigital tem 14.000 estruturas selecionáveis individualmente (https://www.biodigital.com/product/the-biodigital-human).

**(b) O mapa de ambiente é desligado de propósito dentro da sessão.** `Scene.tsx` linha ~219: `inSession ? (emAR ? null : <XRStage/>) : (<><SafeEnvironment/><ContactShadows/>…)`. Arena e Duelo nunca tiveram env map — e o comentário em `ArenaModel.tsx` linhas 75-92 admite a consequência e aplica um remendo: clampa `metalness ≤ 0.1` e `roughness ≥ 0.55` em todo material. Resultado: todo órgão, dentro do óculos, é o mesmo plástico fosco. O custo do PMREM é de **geração**, não de quadro (`PMREMGenerator.fromScene`, https://threejs.org/docs/pages/PMREMGenerator.html) — dá para gerar antes de entrar e manter.

**(c) A cena VR usa 4 fontes de luz com PBR.** `Scene.tsx` 193-206: `ambientLight` + 2 direcionais + `hemisphereLight` (linha 138). `ArenaScene.tsx` 290-295 e `DueloApp.tsx` 92-95: idênticos, copiados. A Meta recomenda o oposto: com uso pesado de PBR, "limite-se a uma luz direcional ou uma pontual" (https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/). E `ambientLight` é o termo que literalmente apaga a forma — todo ponto recebe o mesmo.

**(d) Nada sobra depois da partida.** `lib/store.ts` linha 427, `partialize`: persiste `analyticsConsent`, `currentOrganId`, `annotationsByOrgan`, `chat`, `sessions`, `quizResults`. Não existe registro por estrutura. `ArenaAttempt` (`components/arena/types.ts`) guarda só `{label, acertou}` — nem a posição do alvo, nem o que a pessoa clicou errado. O sorteio é `Math.random` puro em três lugares. O placar evapora; o erro evapora.

**(e) O quiz cai em distrator genérico.** `lib/quiz.ts` linhas 26-39, `FALLBACK_TERMS`: "Artéria", "Veia", "Ligamento", "Tecido conjuntivo", "Cápsula". Quando faltam anotações do usuário, a questão vira reconhecimento de palavra, não discriminação anatômica.

**(f) Não existe tutorial em VR.** `grep -rn "tutorial\|onboarding" components/ lib/` retorna vazio. Numa feira, 100% dos usuários são novatos de VR.

E o que o campo diz que gamificação é — que não é o que a gente construiu:

- Nos simuladores sérios a gamificação é **estrutura de sessão em três atos**: briefing → execução → **debrief**, e o valor está quase todo no terceiro ato. UbiSim segue o padrão INACSL (https://www.ubisimvr.com/how-it-works); o framework acadêmico é o PEARLS, cinco fases (https://pubmed.ncbi.nlm.nih.gov/25710312/).
- Ninguém dá **um número**. Osso VR avalia por Time and Motion, Instrument Handling, Knowledge of Instruments, Flow of Operation, Knowledge of Procedure (https://www.ossovr.com/vr-surgical-training-research). Level Ex pontua velocidade, trauma tecidual, perda de sangue e acurácia separados (https://www.builtinchicago.org/articles/level-ex-gamification-surgery-training).
- Oxford Medical Simulation resume a tese: cada ação é classificada, rastreada **e explicada** (https://oxfordmedicalsimulation.com/feedback/).
- Na meta-análise de jogos para raciocínio clínico, os elementos presentes na maioria das intervenções são decisão baseada em cenário (69%), feedback/reflexão (62%) e acompanhamento de progresso (65%). **Competição aparece em ~27%** (https://pmc.ncbi.nlm.nih.gov/articles/PMC12805841/). O VRmed hoje tem competição e não tem os outros três.
- 78% dos estudos de aprendizagem gamificada em medicina ficam no nível SOLO uni-estrutural — recordar, reconhecer (https://pmc.ncbi.nlm.nih.gov/articles/PMC10765768/). Arena, quiz e duelo são os três desse nível.
- E o ganho mais barato disponível: feedback elaborado d = 0,49; só a resposta correta d = 0,32; só certo/errado d = 0,05 (van der Kleij et al., 2015, https://journals.sagepub.com/doi/abs/10.3102/0034654314564881). Hoje entregamos os dois piores.

**Resumo em uma frase:** o VRmed está no nível de execução dos concorrentes e abaixo deles em primeiro ato (briefing/onboarding), terceiro ato (debrief que explica) e apresentação (luz, material, tipografia). Nenhuma dessas três coisas exige Unity, servidor novo ou asset novo.

---

## 2. O que descarto e por quê

| Descartado | Quem faz | Por que não cabe |
|---|---|---|
| **Unity / Unreal** | 3D Organon XR, Osso VR, PrecisionOS, Human Anatomy VR | Exige instalação e loja. Nosso diferencial declarado é rodar no navegador do Quest 3 sem instalar nada. Trocar isso joga fora a tese do projeto. |
| **Háptica de força** | FundamentalVR (https://www.healthysimulation.com/vendors/fundamental-surgery/) | Hardware. Metade das métricas deles (economia de movimento, consciência espacial 3D) é medível sem háptica — é isso que aproveito. |
| **Conta de usuário / LMS / painel de turma** | Complete Anatomy Curriculum Manager, ClassVR, 3D Organon Medverse | Exige nuvem, autenticação, LGPD e vínculo institucional. Uma instância pequena no Render não sustenta, e o público do evento joga uma vez. Substituto: apelido de 3 letras + localStorage + QR no fim. |
| **Ranking global e ofensiva (streak) diária** | Duolingo | Duas razões. (1) Mecânica morta: num estande ninguém volta amanhã. (2) Placar/ranking é o elemento de design mais citado como causa de efeito negativo em educação (https://link.springer.com/chapter/10.1007/978-3-319-97934-2_9); leaderboard reduz engajamento social de parte dos estudantes e estudantes de medicina preferiram modo em equipe ao individual (https://pmc.ncbi.nlm.nih.gov/articles/PMC10114491/). |
| **Pós-processamento (bloom, DoF, vinheta de câmera)** | Qualquer jogo de PC | Na GPU de tile do Quest, cada passe resolve uma textura extra, ~1 ms **por olho** (https://developers.meta.com/horizon/blog/pc-rendering-techniques-to-avoid-when-developing-for-mobile-vr/). E profundidade de campo é conceitualmente errada em VR: o olho escolhe onde focar, borrão artificial briga com o conflito vergência-acomodação. `@react-three/postprocessing` **não está** no nosso `package.json` — manter assim. |
| **Vídeo 360 / gravação de sessão em vídeo** | Virti, SimX replay | Peso de asset e de memória. A versão barata do replay é gravar **eventos** (`{t, alvo, clique, acertou}`) e reconstruir a pose — cabe num array. |
| **FSRS completo (13 parâmetros)** | Anki (https://github.com/open-spaced-repetition/fsrs4anki) | Sessão de 3 minutos não gera histórico para otimizar 13 parâmetros. Complexidade morta. Três caixas de Leitner entregam quase todo o ganho. |
| **Dados cadavéricos / visualizador DICOM completo** | Anatomage Table, ImmersiveTouch | Licença, tamanho e escopo. A `/clinica` já reconstrói exame real anonimizado — é o suficiente. |
| **Multiusuário com avatar e voz** | 3D Organon Medverse | Servidor de estado. O SSE de `app/api/duelo/route.ts` já dá 90% do valor com 10% do custo (tela de plateia). |
| **WebXR colocalizado (Shared Spaces)** | Navegador do Horizon OS v39 (https://www.uploadvr.com/quest-web-browser-experimental-colocation-webxr/) | Experimental, desligado por padrão, exige `chrome://flags` em cada óculos, só entre Quest. Flag de navegador que muda de versão é exatamente o que quebra no dia. Fica em "trabalhos futuros" do artigo. |

---

## 3. NÚCLEO — o que muda a percepção já no próximo evento

Ordenado por impacto percebido ÷ esforço.

### N1. Passe de luz único: IBL na sessão, uma luz de chave + rim, sombra de contato, fim do clamp, fim da cúpula

**O que é.** Um componente `<LuzEstudio/>` compartilhado, substituindo os quatro blocos de luz copiados com valores diferentes, mais o env map mantido dentro da sessão.

**De onde veio.** Sketchfab lista os três itens que fazem uma vitrine 3D parecer profissional: HDRi/IBL como base do fluxo PBR, iluminação de três pontos e sombra de chão — "often the finishing touch… ancora o modelo no espaço" (https://sketchfab.com/blogs/community/how-to-fine-tune-your-lighting-and-shadows-on-sketchfab/). Meta: uma direcional com PBR pesado, sombra assada em vez de tempo real, cor de limpeza branca ou preta para ativar o fast-clear das GPUs Adreno (https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/).

**O que muda na tela.** O órgão para de ser plástico fosco chapado: ganha reflexo especular, variação entre o lado da luz e a sombra, um fio de contra-luz separando a silhueta do fundo, e uma sombra embaixo que diz a que distância ele está do chão. É o mesmo salto que a correção de espaço de cor deu no duelo, mas no modelo em si. Vale para **todos os modos de uma vez**.

**Onde mexe.**
- `components/viewer/SafeEnvironment.tsx` — virar singleton de módulo (o `useMemo` hoje gera um PMREM novo por componente montado), gerado no carregamento da página.
- `components/viewer/Scene.tsx` linha ~219 — remover o `inSession ?` que tira o `SafeEnvironment`; linhas 138 e 193-206 — matar `hemisphereLight` e `ambientLight`, manter **uma** direcional de chave e acrescentar um rim atrás do modelo relativo ao jogador.
- `components/arena/ArenaScene.tsx` 290-295 e `components/duelo/DueloApp.tsx` 92-95 — trocar os quatro blocos pelo `<LuzEstudio/>`.
- `components/arena/ArenaModel.tsx` 79-92 — apagar o clamp de `metalness`/`roughness` (e o clone de material que só existe para ele: menos memória no Quest).
- `ArenaScene.tsx` linha ~302 e `DueloApp.tsx` ~107 — a esfera `args={[28,24,16]}` com `meshBasicMaterial` `#0a1017` pinta a tela inteira por cima de um clearColor quase idêntico. Ou vira gradiente (profundidade de graça) ou some (fps de graça).
- Sombra de contato dentro do VR: plano com textura radial desenhada em canvas, custo zero por quadro. `Scene.tsx` já tem `ContactShadows` fora do VR — falta `frames={1}` e o equivalente barato dentro.

**Esforço.** Baixo/médio. Uns 4 arquivos, sem lógica nova.

**Como verificar sem headset.** `npm run dev`, abrir `/arena` e `/viewer` no Chrome desktop e tirar print antes/depois dos 19 modelos (o `preserveDrawingBuffer` que já está lá serve para isso). Para conferir o caminho de sessão sem óculos, a extensão WebXR API Emulator do Chrome entra em sessão falsa e o `inSession` passa a valer `true`. Depois, no Quest: OVR Metrics Tool, orçamento de 13,7 ms a 72 fps.

**Risco.** A geração do PMREM pode dar um engasgo de um quadro em GPU fraca — por isso gerar **uma vez no carregamento da página**, nunca ao entrar na sessão. Tirar o clamp pode explodir algum GLB com `metalness=1` autorado errado: conferir os 19 um a um, ou manter um teto de 0,3.

---

### N2. Rótulo da estrutura dentro do VR: mirar + gatilho = nome flutuante

**O que é.** Uma instância de `Text3D` em billboard, presa ao `event.point` do clique, sumindo em ~6 s.

**De onde veio.** É a função nº 1 de todo atlas em VR: Dissection Master XR (https://www.medicalholodeck.com/en/human-anatomy-atlas-in-virtual-reality-dissection-master-xr/), 3D Organon (https://www.3dorganon.com/for-students/), BioDigital (https://www.biodigital.com/product/the-biodigital-human).

**O que muda na tela.** Hoje, dentro do óculos, a pessoa gira um fígado bonito e **não aprende nenhum nome**. Passa a mirar, apertar o gatilho e ver o nome ao lado da estrutura. Vira atlas; hoje é escultura.

**Onde mexe.** `components/viewer/OrganModel.tsx` já chama `identifyStructure(event.object)` no `onClick` e grava em `inspectedLabel` — todo o trabalho está feito. Falta o consumidor 3D: um `Text3D` de `components/arena/ui3d.tsx` (troika, já offline, fontes já em `public/fonts/`) posicionado em `event.point`, com billboard para a cabeça. Item #13 do backlog da auditoria de 2026-09-03.

**Esforço.** Baixo.

**Como verificar sem headset.** Desktop: o `Text3D` renderiza igual fora da sessão. Clicar em estruturas de `larynx.glb` (20 nomeadas) e conferir posição e texto. Rodar `npx tsx scripts/verify-arena.ts` se ele tocar no mesmo caminho.

**Risco.** Um troika novo por quadro custa caro — **uma** instância reaproveitada. Nos 6 modelos de sistema `detectStructures()` retorna vazio (está no CLAUDE.md, é esperado): o rótulo precisa dizer "tecido: músculo", nunca inventar nome anatômico.

---

### N3. Régua de tipografia angular: nenhuma letra abaixo de ~1,2°

**O que é.** Um helper `tamanhoPorAngulo(distancia, graus)` e uma varredura de todos os `size=` fixos.

**De onde veio.** O limiar de leitura em VR é o **tamanho angular** do glifo, não a densidade de pixels: um estudo aponta mínimo legível de 1,33° e recomendado 3,45° (https://link.springer.com/chapter/10.1007/978-3-031-05939-1_13). Meta: fonte de no mínimo 14px, 18px+ para leitura confortável, alvo de clique ≥ 3° de FOV (https://developers.meta.com/horizon/design/styles_typography/). Quest 3 resolve ~25 pixels por grau (https://vr-compare.com/headset/metaquest3).

**O que muda na tela.** Texto que se lê sem chegar o rosto. **Cálculo nosso a partir das constantes do código** (`DueloApp.tsx` linha 88, `DueloGame.tsx` linhas 83-98):

| painel | distância | `size` atual | ângulo | `size` para 1,2° |
|---|---|---|---|---|
| Lousa (escola) — `XROrigin [0.28,−1.3,0.99]`, lousa z = −1.06 | 2,05 m | 0,028 | **0,78°** | 0,043 |
| Painel (hospital) — `XROrigin [0,−1.3,2.55]`, `HOSP_UI [0.75,0.15,−0.55]` | 3,19 m | 0,028 | **0,50°** | 0,067 |
| idem | 3,19 m | 0,042 | **0,75°** | 0,067 |

Ou seja: os textos secundários do duelo estão entre metade e dois terços do mínimo legível publicado. Os títulos (`size` 0,09-0,1 na lousa ≈ 2,5-2,8°) estão bem.

**Onde mexe.** Helper novo em `components/arena/ui3d.tsx`:
```ts
// 2·d·tan(θ/2) — dimensiona por ângulo, não por metro absoluto.
export const tamanhoPorAngulo = (d: number, graus = 1.2) =>
  2 * d * Math.tan((graus * Math.PI) / 360);
```
Aplicar nos ~20 `Text3D` de `components/duelo/DueloGame.tsx` (linhas 1443, 1446, 1450, 1529, 1540, 1547, 1555, 1870, 1913, 1922, 1944, 1953, 1965, 1988, 1995…), em `components/viewer/Scene.tsx`, `SairDoVR.tsx` e nos painéis de `components/sala/`.

**Esforço.** Baixo. É a correção mais barata do lote e a mais defensável em banca, porque tem norma publicada atrás.

**Como verificar sem headset.** Script no padrão dos que já existem (`scripts/conferir-escala-xr.mjs`, `scripts/verificar-duelo-salas.ts`): lê as constantes de posição e os `size=`, calcula o ângulo e falha com `assert` se algum ficar abaixo de 1,0°. Roda em `npx tsx`, sem three.js, sem óculos.

**Risco.** Texto maior transborda o painel — refazer o layout junto, cortando palavra. Isso é bom: hoje há hierarquia demais em pouco espaço.

---

### N4. Feedback elaborado: dizer **por quê**, e acender a resposta certa **no modelo**

**O que é.** Três mudanças que são a mesma mudança: (1) duas frases explicando o erro; (2) a estrutura correta piscando no lugar dela; (3) o retrospecto listando os erros como botões clicáveis.

**De onde veio.** van der Kleij et al. (2015): feedback elaborado d = 0,49 contra 0,32 de só mostrar a resposta e 0,05 de certo/errado, com vantagem maior nos objetivos de ordem superior (https://journals.sagepub.com/doi/abs/10.3102/0034654314564881). Oxford Medical Simulation: cada ação classificada, rastreada e **explicada** (https://oxfordmedicalsimulation.com/feedback/). Estudo controlado de feedback gamificado em VR: feedback imediato acelera a correção durante a execução, feedback pós-tarefa sustenta a consolidação reflexiva — os dois juntos batem qualquer um sozinho (https://arxiv.org/pdf/2605.00389).

**O que muda na tela.** Errou a cartilagem cricoide: além de acender a certa, uma linha curta ("é o único anel cartilaginoso completo da via aérea — a tireóidea é escudo, aberta atrás"), 2,5 s. E a estrutura certa pisca no lugar dela por ~1 s antes do próximo alvo — **em anatomia o que precisa ficar na cabeça é a posição**, não o nome num painel. No fim, "as 3 que você errou" viram botões que destacam a estrutura na cena atual.

**Onde mexe.**
- Fonte do texto, **já offline e já no repo**: `public/descriptions/<id>.json` tem `shortDescription`/`fullDescription`/`sources` para os 19 modelos (conferido). Para o nível de estrutura, `lib/anatomy-labels.ts`. Nada de IA em runtime — quebraria offline e poderia inventar anatomia.
- `components/quiz/QuestionCard.tsx` (hoje imprime só `question.correctAnswer`), `components/arena/ArenaGame.tsx` `handleHit()` (~linha 214), `components/arena/ArenaModel.tsx` para o destaque.
- `components/arena/types.ts` — `ArenaAttempt` precisa ganhar a posição local do alvo e o rótulo do que a pessoa clicou. Hoje é só `{label, acertou}`.
- O padrão de encenação **já existe** em `components/duelo/DueloGame.tsx` (fase "feedback", revelação da resposta). É replicar, não inventar.

**Esforço.** Baixo/médio.

**Como verificar sem headset.** Desktop em `/arena` e `/quiz`. Assert em script: para cada estrutura do banco, existe texto curado ou o código cai no comportamento atual (nunca campo vazio).

**Risco.** Pausa de 1 s a cada erro derruba o ritmo se os erros forem muitos — limitar a revelação às 3 primeiras ocorrências da mesma estrutura na partida. E **não navegar** para o `/viewer` a partir do retrospecto: recarregar a página derruba a sessão WebXR (é o que `lib/xr-sessao.ts` e `lib/xr-log.ts` existem para diagnosticar). Destacar dentro da cena atual.

---

### N5. Distratores anatomicamente vizinhos

**O que é.** Trocar `FALLBACK_TERMS` por estruturas da mesma região do mesmo modelo.

**De onde veio.** BioDigital sobe a dificuldade exigindo que o aluno gire, aproxime ou oculte camadas para achar a estrutura no 3D (https://support.biodigital.com/hc/en-us/articles/1500010289681-Create-a-Select-Anatomy-in-3D-quiz-question). Complemento: 78% dos estudos de gamificação médica ficam em reconhecimento (https://pmc.ncbi.nlm.nih.gov/articles/PMC10765768/) — distrator implausível rebaixa ainda mais, para reconhecimento de palavra.

**O que muda na tela.** A alternativa errada deixa de ser "Artéria" ou "Tecido conjuntivo" e passa a ser a cartilagem vizinha: na laringe, tireóidea × cricoide × aritenoide. A questão passa a exigir olhar o modelo — que é exatamente o que temos e um quiz de texto não tem.

**Onde mexe.** `lib/quiz.ts` linhas 26-39 (`FALLBACK_TERMS`) e `buildQuiz()` linha 58: candidatos vindos de `detectStructures()` e `lib/anatomy-labels.ts` em vez da lista genérica. `components/duelo/DueloGame.tsx` `montarRodadas()` já usa nomes do mesmo modelo nas rodadas de 200 pontos — o problema está nas rodadas de órgão e no `/quiz`.

**Esforço.** Baixo.

**Como verificar sem headset.** `buildQuiz()` é função pura. Script `scripts/verificar-quiz.ts` com `assert`: nenhuma questão tem distrator fora do modelo corrente; toda questão tem 4 alternativas distintas; há ao menos um distrator "distante" por questão.

**Risco.** Distrator vizinho demais vira pegadinha injusta e trava o público leigo na primeira pergunta. Manter **um** distrator distante entre os três errados.

---

### N6. Ciclo de bancada: rodada com fim garantido, combo com teto, modo atração

**O que é.** Três ajustes pequenos no mesmo lugar: a partida vira "rodada de 8 estruturas" (o tempo passa a ser limite por alvo), o combo ganha teto ×3 e vale mais o que a pessoa já errou, e sem ninguém no óculos a cena entra em loop de atração.

**De onde veio.** Level Ex reporta sessão média de ~13 minutos por médico, com níveis discretos: a unidade de jogo é o **caso**, não o cronômetro (https://medcitynews.com/2020/12/level-ex-pitches-gaming-as-a-tool-for-reaching-doctors/). Guias de ativação em feira recomendam 2-3 minutos por pessoa do público geral e posicionamento visível, porque quem vê acontecendo é quem se aproxima (https://www.3dexhibits.com/tips-and-trends/best-practices-for-integrating-virtual-reality-into-your-trade-show-exhibit). Fliperama resolveu isso com attract mode em loop mostrando gameplay + tabela de recordes (https://arcadeblogger.com/2021/01/31/anatomy-of-arcade-high-score-tables/). Sobre o combo: o mapeamento sistemático de efeitos negativos de gamificação lista "preferência por tarefas fáceis" entre os quatro efeitos recorrentes (https://www.sciencedirect.com/science/article/abs/pii/S0950584922002518) — que é literalmente o que um multiplicador sem teto incentiva.

**O que muda na tela.** A rodada sempre termina, sempre termina com debrief, e sempre dá vontade de fazer mais uma — a fila anda porque tem fim previsível e ninguém é interrompido no meio. E o placar passa a premiar quem aprendeu, não quem correu para a estrutura grande.

**Onde mexe.** `components/arena/ArenaGame.tsx`: `MISS_PENALTY = 2` (linha 24), `setScore((v) => v + 100 * nextCombo)` (linha 221), condição de fim de fase, e `hits` virando progresso "3/8" visível. O "vigia de entrada" e o retorno automático ao ocioso já existem (linhas ~19-40) — falta o loop de atração. A pontuação 100/200 do duelo (`montarRodadas()`) é sadia: **não mexer**.

**Esforço.** Baixo.

**Como verificar sem headset.** Desktop, cronometrar 5 partidas. Assert: a fase sempre sai de "jogando" (teto de tempo total como rede de segurança).

**Risco.** Perde-se um pouco da euforia do combo, que é o que faz a plateia parar para ver. Manter o som que sobe de nota (`lib/arena-audio.ts`, `playHit(combo)`) e o "+pontos" flutuante — a sensação vem do som e da animação, não da aritmética. Loop de atração com modelo girando custa GPU o tempo todo: usar `larynx.glb` (18k), nunca o crânio (1,13M).

---

### N7. Memória por estrutura: três caixas de Leitner alimentando o sorteio, e faixa por órgão

**O que é.** Um `Record<string, {caixa: 1|2|3, acertos, erros, ultimaVez}>` no persist que já existe, lido na hora de sortear.

**De onde veio.** Kenhub monta o quiz por repetição espaçada adaptativa (https://www.kenhub.com/en/for-medical-students); Gimkit reapresenta com mais frequência o que o aluno errou (https://ditchthattextbook.com/game-show-classroom-comparing-the-big-5/). Evidência: Larsen, Butler & Roediger (2009) — testar repetidamente deu 39% de acerto contra 26% do reestudo, mais de 6 meses depois (https://asmepublications.onlinelibrary.wiley.com/doi/10.1111/j.1365-2923.2009.03518.x). Revisão do Anki na graduação médica: uso frequente associado a 4-13 pontos a mais no USMLE Step 1, com relação dose-resposta (https://pmc.ncbi.nlm.nih.gov/articles/PMC13197492/). Ensaio randomizado em Anatomical Sciences Education (2026): 7,3/10 contra 5,4/10 de acerto diagnóstico três meses depois (p<0,001; Hedges g=0,80; n=42 na análise primária, de 337 inscritos) — https://pmc.ncbi.nlm.nih.gov/articles/PMC13545336/. E progressão por competência, não por XP: Osso VR dá nota por domínio dos passos, precisão e eficiência (https://www.ossovr.com/vr-surgical-training-research); VirtaMed usa alvos quantitativos intermediários (https://www.virtamed.com/en/products-and-solutions/services/proficiency-development).

**O que muda na tela.** O sorteio deixa de ser uniforme: o que a pessoa errou volta na partida seguinte, o que ela acertou duas vezes some por um tempo. E a tela final deixa de dizer "recorde 1450" e passa a dizer "você domina 12 das 20 estruturas da laringe · revisar: aritenoide, epiglote, ligamento vocal". **É a diferença entre um joguinho e uma ferramenta de estudo, e é o argumento mais forte para a banca.**

**Onde mexe.** `lib/store.ts` — mais um campo no `partialize` (linha 427), ao lado de `quizResults`; o `armazenamentoQueSoGravaMudancas()` já cuida do custo de gravação. Consumido por `pickTarget()` em `components/arena/ArenaGame.tsx`, `montarRodadas()` em `components/duelo/DueloGame.tsx` (~linha 183) e `buildQuiz()` em `lib/quiz.ts`. A faixa por órgão é função de leitura sobre esse mapa + `lib/organs.ts` — nenhum estado novo.

**Esforço.** Médio.

**Como verificar sem headset.** Script com `assert`: simular 50 respostas sintéticas e conferir que um item errado 3× aparece antes de um item acertado 3×; que a fração de itens "difíceis" por partida tem teto (senão a pessoa nunca fecha uma rodada limpa); que o denominador da faixa vem de `detectStructures()`, nunca de um número redondo.

**Risco.** No duelo **online** as rodadas são sorteadas por quem cria a sala e repassadas pelo servidor (`lib/duelo-salas.ts`) — personalizar lá quebra a simetria da partida. Aplicar só no bot, na arena e no quiz. E é localStorage: num óculos compartilhado a faixa é do **aparelho**, não da pessoa. Dizer isso na UI ("progresso deste aparelho") e oferecer "zerar progresso", senão o segundo visitante herda o ouro do primeiro.

---

### N8. Tela da plateia: `/tv` com placar, pergunta atual e código gigante

**O que é.** Uma rota 2D (sem three.js, sem WebXR) que só **lê** o estado da sala pelo SSE que já existe.

**De onde veio.** SimX prevê aprendizes em modo observação (https://www.simxvr.com/features/); UbiSim lista "observation" como formato de facilitação (https://www.ubisimvr.com/how-it-works); Jackbox leva ao extremo com modo plateia (https://www.jackboxgames.com/blog/how-to-play-party-pack-nine-remotely). Guia de feira: espelhar a visão transforma a demo em entretenimento do estande, e a fila vira plateia (https://www.3dexhibits.com/tips-and-trends/best-practices-for-integrating-virtual-reality-into-your-trade-show-exhibit).

**O que muda na tela.** Hoje a plateia olha duas pessoas de óculos em silêncio. Passa a ver, num monitor, a pergunta atual, quem respondeu primeiro, o placar e a revelação da resposta — e o código da sala em fonte gigante, para o próximo já saber o que fazer. **É o maior ganho de percepção por linha de código de toda esta lista** (observação, sem fonte).

**Onde mexe.** `app/api/duelo/route.ts` linha 134 hoje exige `Salas.indiceDe(sala, jogador) >= 0` — só jogador registrado pode ouvir. A mudança é pequena e cirúrgica: um parâmetro `espectador=1` que passa pela validação de sala mas **não** chama `Salas.conectar`/`desconectar` nem conta como jogador, com teto de espectadores pela mesma razão do `MAX_SALAS`. `lib/duelo-salas.ts` não muda — nenhuma regra é tocada. Cliente novo em `app/tv/page.tsx`, reusando o formato de `VisaoSala`.

Junto: apelido de 3 letras (estilo fliperama, roleta A-Z com o analógico — teclado virtual em VR é sofrimento) num campo do `partialize`, para o placar ter dono.

**Esforço.** Baixo/médio.

**Como verificar sem headset.** Inteiramente no navegador: `npm run dev`, abrir `/duelo` em duas abas e `/tv` numa terceira. Depois `npx tsx scripts/verificar-duelo-salas.ts` — **obrigatório**, porque mexemos na rota.

**Risco.** Instância única no Render: se o SSE cair no meio da apresentação, a TV congela. Reconexão automática (o `EventSource` já reconecta com `retry: 2000`) e, no pior caso, a partida nos óculos continua sem a TV. Um deploy no meio do evento apaga as salas — o próprio `route.ts` já documenta isso na linha 16. Guardar o top 10 do dia no localStorage do notebook da TV como rede.

---

### N9. Onboarding de 30 segundos dentro do VR, uma mecânica por vez

**O que é.** Três gestos guiados antes da primeira partida: apontar e apertar o gatilho num alvo → girar o órgão com o analógico → escolher uma alternativa.

**De onde veio.** Meta: em VR, tutorial que parece manual é pulado; ensine fazendo, uma mecânica por vez, e leve ao momento bom nos primeiros minutos; ~40% dos novos usuários adultos jogam sentados no primeiro mês; dado interno deles: quem jogou >30 min no primeiro dia tem 3× mais chance de voltar do que quem jogou <5 min (https://developers.meta.com/horizon/blog/growth-insights-series-building-competency-new-user-onboarding/).

**O que muda na tela.** Quem nunca usou VR — a maioria numa feira — para de perder metade da partida descobrindo o controle.

**Onde mexe.** Não existe nada disso hoje (grep por "tutorial|onboarding" em `components/` e `lib/` retorna vazio). Primeira fase opcional da arena, reusando `ArenaScene.tsx` e `ui3d.tsx`, com sinalizador em `lib/store.ts` para pular quem já fez.

**Esforço.** Médio.

**Como verificar sem headset.** Desktop com mouse cobre o fluxo de estados; o gesto em si precisa do óculos, mas a máquina de estados (avançou? pulou? persistiu?) é testável com `assert`.

**Risco.** Numa fila, tutorial obrigatório mata o ritmo: botão de pular grande, e oferecer só na primeira vez daquele óculos. Sem narração longa — o barulho do evento cobre. Suportar sentado (fila de evento costuma ser em cadeira).

---

## 4. DEPOIS

Cabe nas restrições, mas não muda a percepção no próximo evento.

**Ferramentas do `/viewer` que hoje param na porta do VR.** Complete Anatomy, Anatomage e 3D Organon vendem exatamente isso.
- **Corte anatômico com a mão.** O motor já existe: `computeClippingPlanes()` em `lib/model-utils.ts`, `localClippingEnabled` já ligado em `Scene.tsx`, `ModelStateApplier` já leva os planos para o mundo a cada quadro. Falta remover o `inSession ? [] : …` de `OrganModel.tsx` linha 115 e alimentar `clipping` com a pose do controle secundário. Inspiração: https://3d4medical.com/support/complete-anatomy/cut-tool. **Aviso:** a malha é casca oca — o corte mostra vazio, não superfície de secção. Rotular honestamente ("corte da superfície") ou tampar com stencil (mais um passe). Limitar a 1 plano em VR.
- **Menu de pulso (isolar / raio-X / opacidade / mostrar tudo).** As ações já estão na store (`isolateLayer`, `showAllLayers`, `applyXray`, `setLayerOpacity`); falta a casca 3D. `components/viewer/LayersPanel.tsx` é DOM puro.
- **Busca de estrutura por nome.** Não existe busca nenhuma no `/viewer`. Tudo pronto: `detectStructures()` devolve label + position, `viewerBridge.frameTo()` faz o voo da câmera, `setInspectedLabel()` acende o emissive. É um combobox sobre `useVRMedStore(s => s.structures)`. Nos 6 sistemas precisa dizer que não há malha nomeada, em vez de parecer quebrado.
- **Roteiro guiado: 6-8 paradas por modelo.** BioDigital chama de virtual tour; 3D Organon, de Scene Save & Sequence; Anatomyou faz percurso endoscópico com hotspots. Mecanismo pequeno: um JSON por modelo ao lado de `public/descriptions/`, e um player que só chama `frameTo` + `isolateLayer` + `AudioNarration`. **O custo real é conteúdo, não código** — começar por laringe e coração, conferindo cada frase contra Moore/Gray. Roteiro errado é pior que roteiro nenhum. https://www.biodigital.com/product/the-biodigital-human
- **Narração pré-gerada em MP3.** `lib/organs.ts` já prevê `getAudioFallbackPath()`. Web Speech no navegador do Quest é incerto e pode depender de rede — arquivo commitado resolve VR e offline de uma vez. Áudio precisa de gesto do usuário para desbloquear, como `desbloquearAudio()` já faz em `lib/arena-audio.ts`.
- **Régua / cubo de 1 cm e "modo formiga" com fator visível.** `lib/organs.ts` já tem `tamanhoRealCm` auditado e `escalaReal()` já aplica; `scripts/conferir-escala-xr.mjs` já valida. Falta **exibir**. Human Anatomy VR tem "ant mode" com 40× — a diferença nossa é mostrar "aumento 12× · tamanho real 4,5 cm", para ninguém aprender tamanho errado. `XRManipulation.tsx` tem `MAX_SCALE 6` hoje.
- **`/compare` em VR.** Dois modelos lado a lado em tamanho real, num grupo pai que `XRManipulation` transforma junto — mais simples que a câmera sincronizada do desktop. Limitar a pares com ≤75k triângulos cada. Só 3 órgãos têm par cadastrado e só fígado e rim têm arquivo: a interface precisa continuar dizendo isso.

**Gamificação de segunda camada.**
- **Ajuda que decai sozinha (guidance fading).** Primeira tentativa sem ajuda; errou uma vez, halo na região; errou de novo, a estrutura acende por 1 s. Conforme acerta aquele órgão, a ajuda entra mais tarde e mais fraca. Achado experimental: transparência **adaptativa** do guia melhora retenção e reduz dependência, comparada a guia sempre visível (https://arxiv.org/pdf/2603.06253). Usar contorno/emissive pulsante, nunca preencher a superfície nem mudar a cor do tecido.
- **Modo dupla cooperativo no duelo.** Sailer & Homner (2020): competição + colaboração supera competição pura nos desfechos comportamentais (https://link.springer.com/article/10.1007/S10648-019-09498-W). Escape rooms em educação médica: conhecimento SMD 0,84 (IC 0,36-1,33), trabalho em equipe SMD 4,91 (https://pubmed.ncbi.nlm.nih.gov/39093839/). Human Dx: acurácia individual 62,5% contra 85,6% em grupos de 9 (https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2726709). **Resolve um problema real de fila:** no 1×1 a pessoa leiga perde de 800 a 0 e sai. Mexe em `lib/duelo-salas.ts` e `app/api/duelo/route.ts` — é mudança de regra, exige `npx tsx scripts/verificar-duelo-salas.ts` passando, e **não entra perto do evento**.
- **Fantasma do jogador anterior.** Kahoot Ghost Mode: o fantasma repete as respostas e os tempos da partida anterior (https://kahoot.com/blog/2015/03/20/introducing-ghost-mode-repetition-self-motivation/). Guardar só a curva de pontos por segundo (~60 números), não a partida inteira. É o adversário perfeito para **um** óculos com fila.
- **Rodada relacional: "qual destas sustenta as pregas vocais?"** Sobe do nível SOLO uni-estrutural para o relacional, que é a lacuna declarada da área (https://pmc.ncbi.nlm.nih.gov/articles/PMC10765768/). Um terceiro tipo em `montarRodadas()`, lido de JSON estático. `public/flashcards/base.json` já traz perguntas de função — e já se marca como "revisão humana pendente". **Sem revisão humana não entra.**
- **Replay como linha do tempo de eventos.** SimX grava a sessão e deixa o grupo voltar para dentro do cenário (https://www.simxvr.com/features/). Versão barata: array de `{t, alvo, clique, acertou}` e a pose reconstruída. A fita de uma marca por rodada já existe no placar do duelo — aqui ela só vira clicável.
- **QR no fim da partida.** Resultado + o que revisar + link para o `/viewer` naquelas estruturas, no celular do visitante, sem conta. Decidir **antes do dia** para qual endereço o QR aponta (o do Render, não o localhost do notebook); a biblioteca de QR viaja no bundle, nada de CDN; nenhum dado pessoal na URL.
- **Ligar o debrief ao `/history` e ao PDF.** `app/history/page.tsx`, `components/history/SessionList.tsx` e `lib/pdf-export.ts` já existem — falta arena e duelo escreverem ali. O PDF **não pode** virar certificado nem trazer número com cara de validação clínica.

**Método e higiene de render.**
- **Orçamento de desenho medido em draw calls.** Meta: 1000 triângulos enviados como draw calls individuais já derrubam abaixo de 72 fps, embora a GPU aguente ordens de grandeza mais triângulos — o gargalo é CPU (https://developers.meta.com/horizon/documentation/web/webxr-perf-workflow/). Orçamento: 13,7 ms a 72 fps, 11,1 ms a 90. Contador visível só em dev, teto anotado no CLAUDE.md junto da regra dos 982k de `myology.glb`. **Só vale número lido no Quest 3, em sessão real.**
- **Alavancas de resolução certas.** `setFramebufferScaleFactor` não pode ser chamado com sessão ativa (https://threejs.org/docs/pages/WebXRManager.html); `setFoveation` vai de 0 a 1 — está em 0.5 em `lib/xr-store.ts` linha 32 e `ArenaScene.tsx` linha 147. O `dpr={inXR ? 1 : [1,2]}` de `Scene.tsx` linha 314 **não faz o que o comentário diz**: dentro da sessão o framebuffer vem da sessão XR, não do dpr do canvas. E `preserveDrawingBuffer: true` (linha 317) impede otimização de swap do navegador e existe só para a captura de tela — que já renderiza e chama `toDataURL` no mesmo tique. Mexer atrás de flag de URL; o projeto já tem cicatriz com configuração de sessão.
- **Tone mapping único.** O Canvas do R3F cria o renderer com `ACESFilmicToneMapping` por padrão, diferente do three.js puro (https://r3f.docs.pmnd.rs/api/canvas); a UI 3D usa `toneMapped={false}`. Ou seja, painel e órgão em pipelines de cor diferentes. `ClinicaViewer.tsx` linha 489 pede `NeutralToneMapping` pelo `gl`, que pode estar sendo ignorado. Escolher um, documentar no CLAUDE.md, e **fazer cedo, não na véspera**.
- **Animação de câmera por delta.** `Scene.tsx`, `CameraRig.useFrame`: `camera.position.lerp(goal, 0.14)` roda a 60 no desktop e 72/90 no óculos — durações diferentes. Trocar por `1 - Math.pow(1 - 0.14, delta * 60)`. `Button3D` e `DueloGame` já fazem certo. Diff de duas linhas.
- **Affordances de botão.** Hoje só há crescimento de escala 1,08 no hover; entre puxar o gatilho e a tela mudar não há sinal visual (som e vibração existem). `Button3D` em `ui3d.tsx`: `onPointerDown/Up` com escala 0,97 + borda acesa. E `Floater` não é billboard — de lado, o "+100" aparece esticado; envolver em `<Billboard>` como `Oponente.tsx` já faz. **Sem piscar:** o próprio código já documenta que piscar a 72 Hz incomoda, e a Meta cita a ISO 9241-391 para conteúdo com flashes.
- **`depthTest={false}` em toda a UI.** `ui3d.tsx`: `TEXT_MATERIAL` (linha 90), `Panel`, `Button3D`, `Floater`, `BarraTempo`, todos com `renderOrder` 998/999. Em estéreo, a placa a 3 m aparece por cima de um órgão a 1 m — o conflito oclusão × estereopsia descrito no CHI 2018, que causa desconforto e visão dupla (https://dl.acm.org/doi/10.1145/3173574.3173638). A saída é **posicional** (painel fisicamente à frente) + `polygonOffset` entre placa e rótulo; deixar `depthTest` desligado só no cursor. Há regressão conhecida (a divisória de vidro do hospital apagava metade do painel) — isso é sintoma de layout, não de depth. Fazer com teste no óculos, modo a modo.
- **Instrumentar a própria demonstração.** 6 identificações antes de entrar no óculos e as mesmas 6 depois, com consentimento (o `ConsentBanner.tsx`, `app/api/feedback/route.ts` e `components/admin/FeedbackExport.tsx` já fazem a canalização). É o único número que o VRmed pode afirmar sem citar terceiros. **Amostra pequena, sem controle e sem aleatorização: é dado descritivo de uso, não eficácia.**

---

## 5. IDEIAS GRANDES — precisam de decisão do grupo

**G1. Painéis como XRLayer.** `@react-three/xr` v6 expõe `<XRLayer shape="quad"|"cylinder">`; conferi que `node_modules/@react-three/xr/dist/layer.d.ts` existe nesta instalação. A Meta mede, no exemplo de Cube Layer, 2,4 ms de renderização economizados e mais de 25% de carga de GPU a menos, e diz que UI 2D fica mais nítida numa layer porque evita o duplo aliasing do eye buffer (https://developers.meta.com/horizon/blog/achieve-better-rendering-and-performance-with-webxr-layers-in-oculus-browser/ ; https://pmndrs.github.io/xr/docs/tutorials/layers). **Cálculo nosso:** o painel de 1,7 m do duelo, visto a 3,19 m, ocupa ~30° e é pintado com textura de 512 px → ~17 px/grau, contra os ~25 px/grau que a tela do Quest 3 resolve. É a alavanca mais direta para a UI deixar de parecer WebGL borrado. **Decisão:** layer composita fora da cena 3D — não é ocluída pelo modelo nem recebe o laser igual. Vale para telas cheias (menu, contagem, retrospecto), não para botões que convivem com o órgão. Precisa ser testado no navegador do Quest antes de apostar nisso para o evento.

**G2. Translucidez barata de tecido (SSS aproximado).** Barré-Brisebois & Bouchard, GDC 2011: poucas operações vetoriais, sem passe extra, roda em móvel (https://colinbarrebrisebois.com/2011/03/07/gdc-2011-approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look/). Um `onBeforeCompile` em `lib/model-utils.ts` (onde `prepareModel` já clona materiais), com intensidade por órgão e interruptor. É o maior ganho de "parece profissional" por milissegundo. **Decisão:** risco científico — exagerar muda a cor percebida e pode induzir erro de leitura anatômica. Precisa de validação de quem cuida do conteúdo.

**G3. `/clinica` com decisão antes da revelação.** Hoje mostra o caso 3D. Passaria a perguntar "qual estrutura está alterada aqui?" antes de revelar — `MapaAchados.tsx` vira gabarito atrasado em vez de legenda imediata. É o único modo que pode chegar ao nível relacional, e o de maior valor para a banca porque roda sobre exame real anonimizado (`docs/FASE21-ANONIMIZACAO-CHECKLIST.md`, `docs/FASE23-ANONIMIZACAO-RESULTADO.md`). Referência: Prognosis: Your Diagnosis fecha todo caso com a discussão do raciocínio (https://clinicalodyssey.com/game/prognosis-your-diagnosis). **Decisão:** território regulatório. Exige texto clínico revisado com fonte, o enquadramento "visualização educacional — não substitui laudo" (`docs/PROMPT-CLINICA.md`) em **toda** tela do modo inclusive a de resultado, nenhuma linguagem de diagnóstico, e nunca a palavra vetada em texto de usuário. É o item mais caro da lista.

**G4. Animação de função: um coração que bate.** É o eixo em que nenhum modelo nosso compete — Complete HeartX faz o usuário ouvir o som e ver as valvas (https://www.elsevier.com/products/complete-heartx); Primal Pictures é inteiro construído sobre animação funcional. O caminho já foi aberto pelo crânio: a animação vem do próprio GLB, dirigida pelo campo `explosao` em `lib/organs.ts`. **Decisão:** depende de **asset**, não de código — anatomicamente correto, licenciado, dentro de 150k triângulos. Animar à mão é ensinar fisiologia errada. Se não achar modelo confiável, **não fazer**.

**G5. Torneio de bancada (chaveamento hot seat).** Oito pessoas da fila se inscrevem na TV, o chaveamento aparece, cada duelo dura ~2 min, o óculos passa de mão em mão. Só na TV; `DueloGame.tsx` não muda e o bot serve de bye. **Decisão:** chaveamento é rígido — se alguém desiste, trava; precisa de substituição por bot com um clique. Só faz sentido em picos de movimento.

---

## 6. O que NÃO fazer

1. **Não construir ranking global.** É o elemento de design mais citado como causa de efeito negativo em educação (https://link.springer.com/chapter/10.1007/978-3-319-97934-2_9); leaderboard reduz engajamento social de parte dos estudantes (https://pmc.ncbi.nlm.nih.gov/articles/PMC10114491/). O VRmed hoje não tem um — **isso é acerto, não falta**. Placar do dia que zera à noite, sim; tabela permanente, não. E escrever a justificativa no `docs/CONTEXTO.md`: numa banca de IC, explicar por que você **não** gamificou algo vale tanto quanto mostrar o que gamificou.
2. **Não construir ofensiva (streak) diária.** Mecânica morta num estande onde ninguém volta amanhã, e a literatura crítica aponta ansiedade e obrigação (https://thedecisionlab.com/insights/consumer-insights/streak-creep-the-perils-of-too-much-gamification).
3. **Não adicionar pós-processamento.** ~1 ms por passe **por olho** na GPU de tile do Quest; DoF é perceptualmente errado em VR. O brilho do "acertou" se faz com emissive + sprite de halo, que custa um quad. Manter `@react-three/postprocessing` fora do `package.json`.
4. **Não gerar texto de feedback por IA em runtime.** Quebra o offline do evento e pode inventar anatomia. Pré-gerar, revisar à mão, versionar no repo. Sem texto curado, mostrar só o destaque no 3D.
5. **Não medir performance no desktop e achar que está bom.** Só vale número lido no Quest 3, em sessão WebXR real, com OVR Metrics Tool.
6. **Não mexer em `lib/duelo-salas.ts` / `app/api/duelo/route.ts` perto do evento.** São regras de partida e as salas vivem em memória de uma instância. Se entrar, entra semanas antes, com `npx tsx scripts/verificar-duelo-salas.ts` passando.
7. **Não prometer sincronização entre dispositivos.** Tudo é localStorage. Dizer "progresso deste aparelho" na UI e oferecer "zerar progresso".
8. **Não vender AR como ganho de aprendizado.** Na meta-análise de 24 ensaios randomizados, VR teve efeito moderado e significativo (SMD = 0,58; IC 95% 0,22-0,95; p<0,01) e **AR não mostrou efeito** (SMD = −0,02; IC 95% −0,39 a 0,34; p=0,90) — https://anatomypubs.onlinelibrary.wiley.com/doi/10.1002/ase.2501. O AR continua como conveniência.
9. **Não dizer "VR ensina mais".** Duas formulações honestas e defensáveis: (a) o maior efeito aparece quando VR **suplementa** o ensino convencional, não quando substitui (mesma meta-análise); (b) o argumento próprio do meio é que **VR reduz a carga cognitiva de entender relação espacial** (https://pmc.ncbi.nlm.nih.gov/articles/PMC13197557/) — o que implica, no desenho, que cada elemento de HUD acrescentado ao campo de visão consome de volta o que o 3D economizou.
10. **Não citar número de fornecedor sem marcar como tal.** Os números do Osso VR (92% de acurácia, 67% menos erros, 230-300% de melhora) e quase tudo que circula sobre Duolingo vêm do material das próprias empresas ou de blogs de marketing. Se for ao artigo, vai com a fonte primária. Três pendências de checagem antes de citar: o ano de Hanus & Fox (páginas secundárias divergem), os ensaios por trás dos números do Osso VR, e as sínteses de Kahoot (as mais entusiasmadas são do fornecedor).
11. **Não usar a palavra vetada em texto de usuário.** Vale para toda tela nova desta lista, inclusive as de debrief e as da `/clinica`.

---

## 7. Fontes

**Simuladores e produtos clínicos**
- Osso VR — pesquisa e escalas de avaliação: https://www.ossovr.com/vr-surgical-training-research
- Oxford Medical Simulation — feedback com rationale por ação: https://oxfordmedicalsimulation.com/feedback/
- SimX — gravação com timestamp e replay em 3D: https://www.simxvr.com/features/
- UbiSim — prebriefing INACSL e formato de observação: https://www.ubisimvr.com/how-it-works
- VirtaMed — proficiency-based progression: https://www.virtamed.com/en/products-and-solutions/services/proficiency-development
- FundamentalVR — métricas (economia de movimento, consciência espacial 3D, gaze): https://www.healthysimulation.com/vendors/fundamental-surgery/
- Level Ex — pontuação multi-eixo: https://www.builtinchicago.org/articles/level-ex-gamification-surgery-training e https://www.levelex.com/games/
- PrecisionOS — mentor de IA "Delphi": https://www.precisionostech.com/individuals/
- Health Scholars — BARS por voz, com válvula contra falso-negativo: https://www.healthscholars.com/blog/what-makes-health-scholars-vr-training-different/
- Body Interact — relatório de desempenho e debriefing: https://bodyinteract.com/blog/bodyinteract-ai-simulation-feedback-report/
- Prognosis: Your Diagnosis — caso curto fechado por discussão: https://clinicalodyssey.com/game/prognosis-your-diagnosis
- PEARLS (Eppich & Cheng, 2015): https://pubmed.ncbi.nlm.nih.gov/25710312/
- ImmersiveTouch: https://www.immersivetouch.com/immersiveview-surgical-plan

**Atlas de anatomia 3D/VR**
- 3D Organon XR: https://www.3dorganon.com/for-students/ · avaliação formativa e spotters 3D: https://www.3dorganon.com/formative-assessment-quizzes/ · Medverse: https://www.3dorganon.com/medverse-3/
- Complete Anatomy — ferramenta de corte: https://3d4medical.com/support/complete-anatomy/cut-tool · Curriculum Manager: https://3d4medical.com/apps/complete-anatomy/curriculum-manager
- Complete HeartX: https://www.elsevier.com/products/complete-heartx
- Medicalholodeck Dissection Master XR: https://www.medicalholodeck.com/en/human-anatomy-atlas-in-virtual-reality-dissection-master-xr/
- BioDigital Human: https://www.biodigital.com/product/the-biodigital-human · quiz "select anatomy in 3D": https://support.biodigital.com/hc/en-us/articles/1500010289681-Create-a-Select-Anatomy-in-3D-quiz-question
- Human Anatomy VR: https://www.meta.com/experiences/human-anatomy-vr/6643334382420936/
- Sharecare YOU: https://sidequestvr.com/app/6028/sharecare-you-anatomy
- Anatomage Table: https://anatomage.com/table/ · Primal Pictures: https://primalpictures.com/functional-anatomy/
- Visible Body — flashcards + quiz 3D: https://www.visiblebody.com/blog/introducing-flashcards-for-human-anatomy-atlas-in-web-suite-and-courseware
- Anatomyou VR (percurso endoscópico): https://blogs.ubc.ca/vreducation/2021/12/03/anatomyou-vr-human-anatomy/
- Kenhub: https://www.kenhub.com/en/for-medical-students · Osmosis: https://www.osmosis.org/why-osmosis/spaced-repetition · AMBOSS: https://www.amboss.com/us/features
- ClassVR (painel do professor no navegador): https://www.classvr.com/us/classroom-management/

**Evidência**
- Meta-análise VR/AR em anatomia (Salimi et al., 2024): https://anatomypubs.onlinelibrary.wiley.com/doi/10.1002/ase.2501
- Análise sistemática de 6 apps de anatomia em VR (Scientific Reports, 2024): https://pmc.ncbi.nlm.nih.gov/articles/PMC11685998/
- Framework de 57 requisitos técnicos para app de anatomia em VR (2025): https://pmc.ncbi.nlm.nih.gov/articles/PMC11992126/
- Sailer & Homner (2020), meta-análise de gamificação: https://link.springer.com/article/10.1007/S10648-019-09498-W
- Revisão SOLO de gamificação em medicina (2024): https://pmc.ncbi.nlm.nih.gov/articles/PMC10765768/
- Meta-análise de gamificação para raciocínio clínico: https://pmc.ncbi.nlm.nih.gov/articles/PMC12805841/
- Gentry et al. (JMIR, 2019) — evidência de qualidade baixa a muito baixa: https://www.jmir.org/2019/3/e12994/
- van Gaalen et al. (2021), 44 estudos: https://pmc.ncbi.nlm.nih.gov/articles/PMC8041684/
- van der Kleij et al. (2015), feedback elaborado × KCR × KR: https://journals.sagepub.com/doi/abs/10.3102/0034654314564881
- Larsen, Butler & Roediger (2009), testar × reestudar: https://asmepublications.onlinelibrary.wiley.com/doi/10.1111/j.1365-2923.2009.03518.x
- Revisão do Anki na graduação médica: https://pmc.ncbi.nlm.nih.gov/articles/PMC13197492/
- ECR de repetição espaçada em histopatologia (2026): https://pmc.ncbi.nlm.nih.gov/articles/PMC13545336/
- Piloto randomizado, anatomia do carpo em VR (2025): https://pubmed.ncbi.nlm.nih.gov/41164347/
- Spotter tradicional × hotspot (108 alunos): https://pmc.ncbi.nlm.nih.gov/articles/PMC12413472/
- Escape rooms em educação médica: https://pubmed.ncbi.nlm.nih.gov/39093839/
- Human Dx (JAMA Network Open, 2019): https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2726709
- Sitzmann (2011), jogos de simulação: https://onlinelibrary.wiley.com/doi/10.1111/j.1744-6570.2011.01190.x
- Efeitos negativos de gamificação (mapeamento sistemático, 2023): https://www.sciencedirect.com/science/article/abs/pii/S0950584922002518 · "The Dark Side of Gamification": https://link.springer.com/chapter/10.1007/978-3-319-97934-2_9
- Gamificação sob a teoria da autodeterminação: https://link.springer.com/article/10.1007/s11423-023-10337-7
- Efeito de novidade (756 alunos, 14 semanas): https://eric.ed.gov/?id=EJ1325797
- Alerta sobre gamificação competitiva (BMC Med Educ, 2023): https://pmc.ncbi.nlm.nih.gov/articles/PMC10114491/
- Carga cognitiva 2D × 3D em anatomia: https://pmc.ncbi.nlm.nih.gov/articles/PMC13197557/
- Guia adaptativo com transparência decrescente: https://arxiv.org/pdf/2603.06253
- Feedback gamificado em VR (imediato × pós-tarefa): https://arxiv.org/pdf/2605.00389

**Técnica (a régua dentro da qual tudo tem que caber)**
- Meta, WebXR performance best practices: https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/
- Meta, workflow de otimização (orçamento por quadro): https://developers.meta.com/horizon/documentation/web/webxr-perf-workflow/
- Meta, técnicas de PC a evitar no VR móvel: https://developers.meta.com/horizon/blog/pc-rendering-techniques-to-avoid-when-developing-for-mobile-vr/
- Meta, WebXR Layers: https://developers.meta.com/horizon/blog/achieve-better-rendering-and-performance-with-webxr-layers-in-oculus-browser/ · pmndrs/xr: https://pmndrs.github.io/xr/docs/tutorials/layers
- Meta, tipografia e acessibilidade: https://developers.meta.com/horizon/design/styles_typography/ · conforto: https://developers.meta.com/horizon/design/locomotion-comfort-usability/
- Android XR, design visual: https://developer.android.com/design/ui/xr/guides/visual-design
- three.js WebXRManager (foveation, framebufferScaleFactor): https://threejs.org/docs/pages/WebXRManager.html · PMREMGenerator: https://threejs.org/docs/pages/PMREMGenerator.html
- react-three-fiber, padrões do Canvas: https://r3f.docs.pmnd.rs/api/canvas
- Sketchfab, iluminação e sombras: https://sketchfab.com/blogs/community/how-to-fine-tune-your-lighting-and-shadows-on-sketchfab/
- GDC 2011, SSS barato: https://colinbarrebrisebois.com/2011/03/07/gdc-2011-approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look/
- CHI 2018, conflito de profundidade em UI estéreo: https://dl.acm.org/doi/10.1145/3173574.3173638
- Legibilidade por tamanho angular em VR: https://link.springer.com/chapter/10.1007/978-3-031-05939-1_13 · especificação do Quest 3: https://vr-compare.com/headset/metaquest3
- Conflito vergência-acomodação: https://en.wikipedia.org/wiki/Vergence-accommodation_conflict

**Formato de evento / identidade sem conta**
- Kahoot, entrar com PIN + apelido: https://support.kahoot.com/hc/en-us/articles/360039890713-Kahoot-join-How-to-join-a-Kahoot-game · Ghost Mode: https://kahoot.com/blog/2015/03/20/introducing-ghost-mode-repetition-self-motivation/
- Jackbox, tela do jogo × tela do jogador: https://www.jackboxgames.com/blog/how-to-play-party-pack-nine-remotely
- Comparativo Gimkit/Blooket/Quizizz/Quizlet Live: https://ditchthattextbook.com/game-show-classroom-comparing-the-big-5/
- Tabelas de recorde e attract mode: https://arcadeblogger.com/2021/01/31/anatomy-of-arcade-high-score-tables/
- Boas práticas de VR em feira: https://www.3dexhibits.com/tips-and-trends/best-practices-for-integrating-virtual-reality-into-your-trade-show-exhibit
- Meta, onboarding de novos usuários em VR: https://developers.meta.com/horizon/blog/growth-insights-series-building-competency-new-user-onboarding/
- WebXR colocalizado experimental no Quest: https://www.uploadvr.com/quest-web-browser-experimental-colocation-webxr/
- FSRS/Anki: https://github.com/open-spaced-repetition/fsrs4anki