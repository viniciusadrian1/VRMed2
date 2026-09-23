# VRmed — contexto do projeto

## Polimento contínuo do Duelo (2026-09-18)

O passe de acabamento do `/duelo` começou pela sensação de jogo sem alterar as
regras das salas online: o modelo da rodada agora é remontado por identidade
própria (evita órgãos antigos empilhados), entra com uma microanimação de escala
e profundidade, e reage ao resultado com brilho temporário verde, coral ou âmbar.
O briefing usa a instrução curta "Mire · gatilho responde · analógico gira", o
feedback mostra combo quando há sequência de acertos e a tela final informa o
que revisar. Os materiais do GLB são restaurados após o feedback.

O build deixou de depender de rede para baixar Inter/Fraunces durante o
`next build`: a interface usa a fonte local disponível e fallbacks do sistema.
`npm run typecheck` e `npm run build` passam. Teste em Quest ainda é obrigatório
para confirmar legibilidade, brilho e conforto.

O visualizador principal também passou a mostrar a estrutura identificada como
texto 3D dentro do VR/AR, ancorado no ponto clicado e acompanhado pelo root do
modelo; no desktop, a barra DOM continua sendo usada.

`Button3D`, usado por Arena, Duelo e Sala, agora também tem estado visual de
pressionamento (compressão curta ao apertar), além do hover, som e háptica já
existentes. Isso dá confirmação imediata entre o gatilho e a troca de tela sem
adicionar custo de pós-processamento.

O resultado do Quiz agora também oferece "Revisar no modelo 3D": o órgão da
tentativa é colocado na store antes da partida e o debrief leva de volta ao
visualizador sem rota ou fluxo paralelo.

O rótulo 3D de estrutura no Viewer/VR agora entra com escala curta, ponto
âmbar de ancoragem e pequeno deslocamento da superfície. A posição continua no
espaço local do root, então acompanha manipulação e abertura do modelo.

Arena e Duelo passaram a usar `LuzEstudio`, com luz-chave quente, contraluz fria
e preenchimento hemisférico reduzido. O objetivo é recuperar volume nos órgãos
sem HDR remoto, pós-processamento ou sombra dinâmica; validar o resultado final
no Quest antes de ajustar intensidades novamente.

A Arena passou a exibir também uma barra de tempo drenando no painel da partida.
Ela lê uma ref no `useFrame`, sem atualização React por quadro, e reaproveita o
mesmo componente de barra do Duelo.

O debrief da Arena agora mostra acertos, tentativas, precisão percentual derivada
da partida e recorde separado; os alvos errados continuam listados para revisão.

Durante a partida, a Arena também explicita o resultado imediato: `Acerto` ou
`Erro · −2 s`, além do flash, som e flutuante de pontos já existentes.

O combo da Arena agora tem teto explícito em `x3`: mantém a progressão sonora e
visual, mas impede que a pontuação cresça indefinidamente e incentive apenas
velocidade em vez de identificação cuidadosa.

Na Clínica, o canvas agora fixa explicitamente o fundo da cena além do clear do
renderer, evitando que a abertura de um caso herde um frame branco durante a
preparação do GLB.

Na inspeção em navegador local, os casos clínicos responderam `200` e o GLB foi
carregado, mas o backend de teste registrou `THREE.WebGLRenderer: Context Lost`
depois de abrir várias cenas 3D na mesma sessão. Duelo, Sala e Viewer renderizam
normalmente; a Clínica ainda precisa de confirmação em uma sessão limpa/Quest
antes de qualquer ajuste adicional de shader ou asset.

As verificações de ciclo XR, salas do Duelo e vocabulário de áudio agora rodam
offline com Node 22+, sem baixar `tsx`: `npm run verify:xr`,
`npm run verify:duelo` e `npm run verify:audio`.

O lint oficial foi delimitado ao código executável do produto (`app`,
`components`, `lib`, `scripts` e `eslint.config.mjs`), deixando datasets e
documentos de pesquisa fora da varredura: `npm run lint` passa sem warnings.

O enquadramento/reset da câmera do Viewer também passou a usar suavização baseada
em `delta`, mantendo a duração percebida estável entre monitores e taxas de
atualização diferentes do Quest.

No modo Comparar, o carregamento assíncrono dos GLBs agora exibe um estado
explícito por lado (saudável ou patológico), evitando um canvas aparentemente
vazio durante a preparação do modelo.

Na inspeção visual do Duelo em navegador, as listas de marcas, teclas, alternativas
e telas online receberam chaves com prefixo e índice para evitar colisões quando
uma alternativa se repete entre rodadas. O texto duplicado de atalhos que ficava
fantasma no rodapé do canvas foi mantido somente para leitores de tela (`sr-only`),
pois o briefing 3D já apresenta as instruções ao jogador.

Na Sala de estudos, a descrição duplicada de interação também ficou somente em
`sr-only`; o cenário permanece livre para os objetos interativos e os botões
visíveis continuam sendo o ponto de entrada para VR e para o Tutor.

> Documento de continuidade. Se você (ou uma IA assistente) está abrindo este projeto numa
> máquina nova, leia isto primeiro. Última atualização: 2026-08-29.

## Modos novos (2026-08-29): Sala de Estudos e Duelo 1x1

Dois modos do plano multi-modo do grupo implementados DENTRO do app web
(decisão: sem Unity). `/sala` = quarto 3D com rádio lo-fi sintetizado,
flashcards (base curada + geração por IA), hub de modos e livro-tutor.
`/duelo` = quiz 1x1 contra bot (3 dificuldades, 100/200 pts, avatar médico
procedural). Detalhes e pendências: `docs/PLANO-MULTIMODO.md`.

**Duelo online (2026-09-15):** dois óculos pela internet, só com Wi-Fi, sem
notebook. Um cria a sala (código de 4 dígitos na lousa/painel), o outro digita
num teclado 3D. O site no Render é o árbitro: `app/api/duelo/route.ts`
(SSE + POST; WebSocket não cabe numa rota do Next 16) sobre as regras puras de
`lib/duelo-salas.ts`; no óculos, `components/duelo/useDueloOnline.ts`. Ganha o
acerto com menor tempo de reação medido no óculos (janela de 600 ms), não quem
tem a internet mais rápida. **Salas vivem na memória do processo:** exige UMA
instância no Render e um deploy derruba as partidas abertas — não publicar
durante o evento. Checagem: `npm run verify:duelo`.

**Apresentação do duelo (2026-09-17) — "parecer um jogo, não um protótipo":** as REGRAS já
eram boas; o que denunciava protótipo era a encenação (tudo acontecia trocando string em
`Text3D`). O que mudou, tudo em apresentação — `lib/duelo-salas.ts` e `app/api/duelo/route.ts`
não foram tocados:

- **Vocabulário sonoro** (`lib/arena-audio.ts`, reescrito): um som por evento. Antes o MEU erro e
  o ponto DO ADVERSÁRIO tocavam o mesmo som, o tempo esgotar era mudo e vitória/derrota/empate
  eram idênticos. Agora há síntese em camadas (transiente de ruído + corpo + variação de ±25
  cents), tique da contagem em tríade, tensão nos últimos 5 s, som de clique/hover na UI e
  `desbloquearAudio()` num gesto real — sem ele o duelo online corria mudo, porque o primeiro som
  vinha do servidor. Checagem: `npm run verify:audio`.
- **Háptica** (`lib/xr-haptica.ts`, novo): `pulsar()` no hover, clique, acerto, erro e ponto do
  adversário. API de gamepad, não de sessão — não encosta no ciclo WebXR.
- **Placar de duelo único** `VOCÊ 300 × 200 NOME` com fita de uma marca por rodada, no topo do
  painel/lousa. Antes os meus pontos eram um canto e os dele flutuavam sobre o avatar, 1,7 m
  ATRÁS de mim na escola. O telão do hospital nunca mais apaga.
- **Revelação da resposta:** as alternativas ficam na tela no feedback — a certa acende, a que a
  pessoa errou fica coral. Antes viravam uma frase e quem errou nunca via qual era.
- **Alvo de clique:** o `BotaoLousa` ganhou `altura` própria. As teclas do código se sobrepunham
  3 cm (passo 0,11 com alvo de 0,14) e as alternativas tinham 1,2 mm de folga.
- Barra de tempo drenando, contagem com cartão de apresentação (quem × quem, regras e dica do
  analógico), "+pontos" saindo do órgão, pausa curta do modelo no acerto, transição de entrada
  de cada tela (`Entrada`, só escala/profundidade — opacidade cai no array de material do troika)
  e tela de fim com retrospecto medido na própria partida (acertos, maior sequência, reação
  média, o que revisar).
- **Espaço de cor corrigido** em `ui3d.tsx`: a textura dos painéis nascia em `NoColorSpace` e o
  app inteiro (Arena, Sala, Duelo) desenhava lavado. Ao corrigir, as cores autoradas olhando o
  resultado errado foram reautoradas no mesmo passe.

**Unity como bancada de assets (2026-09-01):** o grupo quer trocar o AMBIENTE do
Duelo por um cenário que só abre no Unity (.unitypackage). Fluxo: importar no
projeto Unity ("Tutorial no Editor do Guia de Configuração") → exportar GLB via
UnityGLTF → dieta (simplify se preciso + webp + draco) → palco do /duelo web.
O produto continua sendo o site; Unity NÃO vira runtime. Claude opera o Editor
via MCP (ver memória unity-mcp-setup: servidor HTTP :8080 da janela MCP for
Unity precisa estar ligado).

**Componentes 21st.dev na landing (2026-09-03):** 6 componentes Magic UI/Aceternity adaptados aos
nossos tokens (azul clinico + ambar, tema claro/escuro) e com guard de prefers-reduced-motion, em
components/ui/: dot-pattern (fundo do hero e do CTA, no lugar do vrmed-grid), number-ticker (faixa
de stats: 18 e 100%), magic-card (spotlight nos 3 cards do Catalogo), word-reveal (H1 do hero,
palavra a palavra), border-beam (um feixe ambar no card Pesquisa), timeline (secao Como funciona).
A Marquee custom foi mantida (ja tinha pausa no hover, fade e reduced-motion). Sem dependencia nova
(framer-motion/lucide/tailwind ja existiam).

**Auditoria geral (2026-09-03):** varredura da plataforma inteira por 13 lentes + juiz +
refutador adversarial (`docs/AUDITORIA-2026-09-03.md`). 109 achados; 29 corrigidos em 27
commits (vitrine honesta = fontes do tutor, par patológico, aviso educacional; acessibilidade
de quiz/duelo por teclado; robustez do tutor; overlay que travava o catálogo). Pendências que
exigem headset ou decisão do grupo: bloquear modelos > 150k no Entrar em VR (#14), rótulo da
estrutura em VR (#13), persistência do feedback no Render (#28), unificar store de XR (#20),
rate limit no /api/chat (#27). Backlog de 69 achados aprovados (47 sem refutação adversarial
por limite de uso) aguardando um 3º lote.

**Sala no Quest (teste do grupo, 2026-09-02):** origem do VR movida para o CENTRO DO ASSENTO
(`XROrigin [0,0,-1.15]`; antes ficava em z −0,55, atrás do encosto, e a cabeça entrava nele).
Painéis reposicionados a ~1,1 m dos olhos (flashcards à esquerda, tutor à direita, hub atrás do
monitor), estado único "um pop-up por vez" em `SalaInterativos` e botão × em cada painel.
Câmera de desktop = olho sentado no assento.

**Tutor de IA reescrito (2026-09-02):** `lib/medical-system-prompt.ts` agora pede texto corrido
curto (2 a 5 frases; até 3 parágrafos se pedirem detalhe), SEM Markdown e sem travessão, porque a
gaveta da Sala e o painel VR mostram texto puro (os asteriscos apareciam literalmente). Caiu a
exigência de `[Fonte: X]` atrás de cada frase (só forçava citação inventada): fontes = tratados da
graduação (Moore, Gray, Netter, Sobotta, Guyton, Robbins), uma referência natural no fim e só com
certeza. Teto de 700 tokens. O chip de citação do `MarkdownContent` (Estudo 3D) ficou sem uso.

**Sair do VR (2026-09-02):** `components/xr/SairDoVR.tsx` — botão 3D filho do `<XROrigin>` em
todos os modos com sessão (Sala, Duelo, Clínica, Arena, Estudo 3D): encerra a sessão e faz
`history.back()`. Dentro da sessão o DOM some, então antes não havia como voltar. Posição
relativa aos pés: `[-0.45, 0.95, -0.5]` sentado, `1.25` de pé. O emulador iwer do modo dev
quebra com three 0.184 (`material.onBuild is not a function`) — testar só no headset.

**Spotify no rádio da Sala (2026-09-02):** modo "controle remoto" (Spotify Connect pela Web
API, login PKCE no navegador, `lib/spotify.ts`, `docs/SALA-SPOTIFY.md`). Regras de 2026 que
limitam: app em modo dev aceita só 5 usuários cadastrados, dono precisa de Premium, controle
exige Premium do usuário, redirect `http://127.0.0.1:3000/sala` (não localhost). Sem
`NEXT_PUBLIC_SPOTIFY_CLIENT_ID` o botão nem aparece; o lo-fi local continua o padrão. Web
Playback SDK (som na própria página) ficou fora até um teste-piloto no Quest.

## VRmed Clínica (modo 3) — estado em 2026-08-26

Terceiro modo do app, em `/clinica`: casos 3D gerados de **exames reais anonimizados**
(TCIA/LIDC-IDRI e 3D Slicer sample data). Master prompt com regras e fases:
`docs/PROMPT-CLINICA.md` (ler antes de mexer). Enquadramento obrigatório: "visualização
educacional — não substitui laudo" (nunca "diagnóstico/assistência", território ANVISA).

**Pipeline (Python, roda SÓ no PC Windows com RTX 4060 Ti — TotalSegmentator usa CUDA):**

- **2026-09-01 — plano DICOM→3D do grupo reconciliado:** `docs/PLANO-CLINICA-DICOM.md`. O
  pipeline JÁ era segmentação anatômica (TotalSegmentator) → marching cubes; o plano evolui
  ele, não substitui. Código novo em `scripts/clinica/` (ingestao, segmentacao, metricas, qa,
  cores) + `scripts/preparar-caso.py` (etapas 1+2 + QA, sem malha). Caso cardíaco com contraste
  `cta-cardio` (3D Slicer) preparado em 153 s e PUBLICADO em `public/pacientes/` como
  "Coração e grandes vasos" **sem pulmões** (o viewer ainda não tem toggle e eles escondiam o
  coração; a versão completa fica em `.clinica-dados/cta-cardio/`). No GLB completo o pulmão
  direito saiu escuro (aviso "normais invertidas" — `fix_normals(multibody)` não corrige todos
  os corpos; item da etapa 3a). Câmaras cardíacas exigem licença acadêmica gratuita do
  TotalSegmentator (`totalseg_set_license`) — ainda não configurada.
- **2026-09-02 — etapa 3a + viewer (resposta à crítica "parece massinha"):** `scripts/clinica/malha.py`
  (σ proporcional ao spacing, pad/tampa no limite do exame, nível 0,5 com afastamento só nas
  câmaras, ilhas < 30 mm³ e buracos tratados na máscara, vasos encostados no coração, cor por HU
  em duas profundidades com sRGB linearizado, oclusão pela ocupação da vizinhança);
  `tc-para-vrmed.py` virou CLI fino com `--camaras`, `--sem-pulmoes` e orçamento que respeita o
  teto de 150k. Viewer: RoomEnvironment local + NeutralToneMapping + 1 luz, envelope translúcido
  do coração com toggle, corte por plano (axial/coronal/sagital) e **vista inicial de frente**
  (o pipeline exporta a frente em −Z; o modelo gira 180° no viewer — antes a primeira vista era
  das costas, em todos os casos). Caso `cta-cardio` republicado com câmaras (149.674 tris).
  Diagnóstico completo com fontes: `docs/CLINICA-FIDELIDADE.md`.
- `scripts/tc-para-vrmed.py` — máscaras → GLB nomeado (etapa 3a; importa `scripts/clinica/malha.py`,
  presets/cores/segmentação do pacote; preset `cardiaco`). Flags:
  `--pulmoes-inteiros` (une lobos → pulmão esq/dir sem linhas de fissura) e
  `--cores-tc exame.nii.gz` (cor por vértice pela densidade HU real + oclusão de cavidade —
  a "textura" vem do próprio exame). Depois SEMPRE `npx gltf-transform draco` (nunca --simplify).
- `scripts/achados-pulmao.py` — TC + máscaras → JSON de achados (enfisema LAA-950 por lobo,
  opacidades candidatas com posição normalizada).
- `scripts/pintar-pulmao.py` — pinta os achados na TEXTURA do modelo ilustrativo de pulmão
  (modo "Mapa de achados", secundário).
- Dados brutos/máscaras em `.clinica-dados/` (gitignored, só existe no PC). Os GLBs finais
  vão para `public/pacientes/` + `manifest.json` (commitados — o site funciona em qualquer máquina).
- venv: `.venv-pipeline` (Windows). Torch 2.6.0+cu124 fixado — NÃO deixar pip trocar por CPU.

**Frontend Clínica:** `components/clinica/` (ClinicaApp, ClinicaViewer, MapaAchados) — canvas
e XR store próprios, isolados da store global. Visão padrão = "Reconstrução real" (malha medida,
pulmões inteiros, cores da TC); alternativa = "Mapa de achados". Lição aprendida: marching cubes
exporta normais para DENTRO — `fix_normals(multibody=True)` no pipeline é obrigatório (sem isso
a iluminação inverte e a amostragem de HU cai na parede torácica).

**Pendências Clínica:** etapa 3b (volume HU recortado + função de transferência + ray marching
no viewer — a resposta definitiva à "textura"); viewer com escala real e régua; `.stl` e normais
guiadas pelo gradiente do HU na 3a; esqueleto/pericárdio como contexto opcional; validação de
acurácia (§5 do prompt: Dice/HD95 vs ground truth, script `validar-segmentacao.py` ainda não
existe — sem ela tudo é "experimental"); reprocessar os dois casos de tórax com a malha nova;
caso de enfisema grave (DPOC) para o contraste saudável×fumante; teste em Quest; Fase 3
(upload → processamento na nuvem: R2 + Modal + Neon; tarefa licenciada exige consulta ao autor).
Licença acadêmica do TotalSegmentator: configurada em 2026-09-02 (regras em
`docs/PLANO-CLINICA-DICOM.md` §4).

**Multi-máquina:** no Mac dá para editar frontend, rodar `npm run dev`, commitar e push
(Render faz deploy automático do GitHub). Processamento de exames novos: só no PC (CUDA).
`.env` (OPENAI_API_KEY) não está no git — copiar manualmente se precisar do tutor local.
O domínio público (canonical/Open Graph/sitemap/robots) vem de `NEXT_PUBLIC_SITE_URL` ou, sem
ela, de `RENDER_EXTERNAL_URL` (injetada pelo Render); em dev cai em `http://localhost:3000`.

## O que é

Plataforma de estudo de anatomia em 3D/VR, em **pt-BR**, para estudantes de medicina e da área
da saúde. É um projeto de **Iniciação Científica** — o que significa que dados de uso são
anônimos, com consentimento (LGPD), e que **honestidade nos números importa**.

**Stack:** Next.js 16 (App Router, Turbopack) · React 19 · TypeScript estrito · Tailwind v4 ·
React Three Fiber v9 + drei v10 + three 0.184 · @react-three/xr v6 (WebXR) · Zustand v5 (persist) ·
OpenAI SDK (gpt-4o, tutor com streaming) · UI estilo shadcn (Radix + cva).

**Rodar:** `npm install` → `npm run dev`. Requer `.env` com `OPENAI_API_KEY` (só o tutor de IA
depende dela; o resto funciona sem).

---

## Números reais do catálogo — nunca inventar

Definidos em `lib/organs.ts`. A landing lê direto de lá, então os números se mantêm corretos
sozinhos. **Não fabricar estatísticas** (é projeto de pesquisa):

- **19 modelos** = 6 sistemas (corpo inteiro) + 7 regiões (anatomia nomeada) + 6 órgãos
- **3 órgãos** têm par patológico cadastrado para o modo Comparar: coração, fígado e rim
  (policístico, desde 2026-09-16, no lugar do pulmão). Só fígado e rim têm o arquivo; o coração
  mostra o modelo de demonstração até chegar o modelo com hipertrofia.
- **Crânio que se abre** (`cranio`, 2026-09-16): a animação do próprio GLB separa os ossos
  (0–4 s abre, 4–8 s fecha). Na tela, o controle "Separar os ossos"; no VR, o analógico
  esquerdo (puxar abre, empurrar fecha; A/X fecha). Campo `explosao` no catálogo.
- VR pelo navegador (WebXR), 100% pt-BR, tutor de IA citando apenas fontes médicas reconhecidas

### Peso dos modelos (medido) — decisivo para VR

| Modelo | Triângulos | Uso em VR |
|---|---|---|
| `larynx.glb` | 18k, **20 estruturas nomeadas** | ✅ ideal para jogo/identificação |
| `coracao.glb` | 11k (malha única) | ✅ ideal para o "uau" visual |
| `splanchnology.glb` | 303k | ⚠️ limítrofe |
| `myology.glb` | **982k** | ❌ **proibido em VR** — não sustenta 72–90fps estéreo |
| `cranio.glb` | **1,13M** (25 malhas: 22 ossos + dentes superiores e inferiores; 3,3 MB com Draco) | ⚠️ pedido para o Quest pela abertura; **testar no óculos** |
| `pathological/rim.glb` | **1,43M** (4,8 MB com Draco) | só no Comparar (2D) |

Só **regiões** e **órgãos** têm malhas com nomes anatômicos reais (`layerBy: "mesh"`).
Os **sistemas** usam `layerBy: "material"` → as camadas são tecidos, e `detectStructures()`
retorna vazio para eles (por isso não têm pontos numerados).

---

## Estado atual (o que já foi feito)

Auditoria completa de 7 dimensões (2026-06-12) + correções aplicadas:

- **Landing page reconstruída** do zero: hero 3D, vitrine de recursos com mockups, bento grid,
  catálogo lido do `organs.ts`, marquee de fontes, CTA final.
- **SEO/PWA:** `manifest.ts`, `robots.ts`, `sitemap.ts`, `opengraph-image.tsx`, `apple-icon.tsx`,
  metadata por rota (layouts em viewer/compare/quiz/history), admin com `noindex`.
- **Correções:** AbortController no chat (streaming cancelado ao fechar/trocar), ErrorBoundary
  para GLB corrompido (cai no placeholder), `frameloop="demand"` em Compare/Quiz (não queimam GPU
  ociosa), chat memoizado (fim do re-parse O(n²)), regiões `aria-live`, páginas de erro/404,
  guarda de `prefers-reduced-motion`, contraste WCAG AA do texto secundário, ESLint ignorando
  `public/**`.
- **Identificação de estruturas:** pontos numerados só aparecem em modelos com nomes anatômicos
  reais (um ponto por estrutura, sem repetição, com oclusão). Traduções pt-BR em
  `lib/anatomy-labels.ts`.
- **Decodificador Draco local** em `public/draco/` — funciona offline, sem CDN.
- **Correção de VR:** `frameloop` vira `"always"` durante a sessão XR (antes ficava preto).
- **Correção de áudio:** narração usa a voz do navegador sempre que existir síntese, não só
  quando há voz pt-BR instalada.

**Build de produção passa** (16 rotas).

---

## Backlog adiado (decisões conscientes)

- **Hotspots 3D inacessíveis por teclado** (a11y): usam drei `<Html>` dentro do Canvas.
  Solução: lista DOM paralela de estruturas chamando `setInspectedLabel` + `viewerBridge.frameTo`.
- **Trilho de ferramentas no mobile** não se esconde; tooltips saem da tela.
- **Sem testes.** Bons primeiros alvos (funções puras): `lib/quiz.ts` (buildQuiz),
  `lib/model-utils.ts` (getClipCut/computeClippingPlanes), `lib/format.ts` (stableHash),
  `lib/anatomy-labels.ts` (translateMeshName).
- **~12 erros de lint pré-existentes** (não são regressões): `react-hooks/purity` (`Date.now()`
  em handlers), `set-state-in-effect`, `refs`, `exhaustive-deps`. Em boa parte falso-positivo
  para event handlers — corrigir caso a caso, **não em massa**.
- **Modelos patológicos faltando:** só o fígado cirrótico existe. Coração hipertrófico e pulmão
  enfisematoso continuam no placeholder. **Tentativa de derivar por código foi revertida** —
  deformar a malha por escala gera um borrão não-fiel; patologia real é geometria nova.
  Caminho correto: obter GLBs reais e otimizar com Draco.

---

## Tarja branca ao sair do VR/AR (2026-09-16)

**Sintoma (relato, intermitente):** depois de sair do VR ou do AR no Quest 3, às vezes surge no
topo uma faixa branca "aplicação executada em segundo plano" com **Retomar / Sair**. Os botões
não respondem e a faixa bloqueia a interface.

**O que ela é:** interface **nativa do Quest Browser**, não do VRmed. Nenhum elemento do app tem
esse texto, e a página não recebe os cliques dela. O navegador a mostra quando exibe a página 2D
e acha que ainda existe uma sessão imersiva ou uma oferta de sessão (three.js#29457, ata do W3C
Immersive Web de 2024-03-25, immersive-web/webxr#1365). **Não foi reproduzida em aparelho**: o
diagnóstico veio do código e dessas fontes.

**Chamadas de WebXR que o app fazia sem clique ou deixava sem dono, todas fechadas:**

| Caminho | Correção |
|---|---|
| `createXRStore` chama `navigator.xr.offerSession` (extensão própria do Quest) ao montar e **a cada fim de sessão**, e entra sozinho em `sessiongranted` | `offerSession: false, enterGrantedSession: false` nas 3 stores (`lib/xr-store.ts`, `viewer/Scene.tsx`, `arena/ArenaScene.tsx`) |
| Cena 3D desmontando com a sessão viva: o R3F e o `<XR>` não encerram a sessão (`WebXRManager.dispose` é vazio) | cleanup no `SairDoVR` chama `end()`, adiado um tique para ignorar o remonte do StrictMode e do Fast Refresh em dev |
| Hub da Sala navegando com a sessão viva (`window.location.href`) | `sairENavegar`: `end()` primeiro e navegação só depois |
| "Sair do VR" com clique duplo; "Entrar em VR" com clique duplo ou por cima de uma sessão pausada pelo botão Meta | `sairENavegar` (uma vez só) e `entrarNoXR` (sem pedidos sobrepostos, encerra a viva antes) em `lib/xr-sessao.ts` |

**Checagem sem headset:** `npm run verify:xr`, que também falha se uma cena
nova criar store sem as opções, navegar direto ou chamar `store.enterVR()` sem `entrarNoXR`.

**Registro de diagnóstico no aparelho (`lib/xr-log.ts`):** vem desligado. Para ligar, abrir
`/viewer?debug=xrlog`; também funciona em `/sala`, `/duelo`, `/clinica` e `/arena`, mas não nas
outras páginas. A flag fica gravada no aparelho. O registro anota:
- quem pediu e quem encerrou cada sessão, com "a página chamou end" ou "SEM end da página";
- ofertas pendentes e quadros de XR parados;
- o que há no topo da página no momento em que se toca **"Marcar: tarja apareceu"**.

Para desligar, usar o botão **Desligar** ou abrir `?debug=off`. Para remover do projeto, apagar o
arquivo e o import dele em `components/xr/SairDoVR.tsx`. O passo a passo no óculos está em
`docs/TESTAR-VR.md`.

---

## Pegadinhas que já custaram tempo

- **Cache do Turbopack:** ao editar variáveis CSS em `app/globals.css`, um cache antigo de
  `next build` pode fazer o dev server servir valores velhos. `rm -rf .next` + reiniciar resolve.
- **Otimização de GLB:** `--simplify-ratio 0.5` **destrói** modelos anatômicos (dizima metade dos
  triângulos). Para modelos com detalhe, usar **só compressão Draco**, sem simplificação.
- **WebXR exige contexto seguro (HTTPS ou localhost).** Acessar `http://192.168.x.x:3000` do
  Quest faz `navigator.xr` **não existir** — o botão de VR não funciona. Usar HTTPS ou cabo USB
  com `adb reverse`.
- **Screenshot de página com WebGL contínuo trava** as ferramentas de preview. Alternativa:
  ler pixels via `drawImage` num canvas 2D + `getImageData`.
- **`material-*` no `<Text>` do drei não funciona com `outlineWidth`:** o troika expõe `material`
  como ARRAY `[contorno, texto]`, então `material-depthTest={false}` caía no array e o texto era
  depth-testado — qualquer transparência à frente (vidro da divisória do hospital) apagava o
  texto atrás. `Text3D` agora passa um material-base próprio (`TEXT_MATERIAL` em `ui3d.tsx`).
- **A câmera de desktop tem de ser o olho do VR.** O layout do hospital foi desenhado numa câmera
  a 2,8m do chão vista de cima e "funcionava"; no Quest a pergunta ficava a 3m de altura e 44° à
  esquerda. Regra: `camera.position` = XROrigin + altura dos olhos (1,2m sentado / 1,6m de pé),
  olhando para −z, antes de posicionar qualquer painel.
- **Uma store XR por app, não por montagem:** `createXRStore` pendura overlay + listeners e nunca é
  destruída (e `destroy()` no cleanup quebra a religada sob StrictMode). Usar `obterXRStore()` de
  `lib/xr-store.ts` (Sala e Duelo já usam; Arena/Clínica/Viewer ainda criam a própria).

---

## Onde está o quê

```
app/            rotas (viewer, compare, quiz, history, admin, api/chat, api/feedback)
components/
  viewer/       Scene, OrganModel, ToolsPanel, StructureHotspots, XRButton…
  chat/         tutor de IA (streaming + citações)
  quiz/         jogo de identificação (máquina de estados reaproveitável)
  landing/      página inicial
lib/
  organs.ts        catálogo (SYSTEMS / REGIONS / ORGANS)
  model-utils.ts   detectStructures, identifyStructure, camadas, planos de corte
  store.ts         Zustand (estado do visualizador; layers/structures são transitórios)
  viewer-bridge.ts ponte imperativa DOM→3D (frameTo/zoom/reset) — vira no-op em VR
  anatomy-labels.ts traduções pt-BR
public/models/  systems/ · organs/ (regiões) · healthy/ · pathological/
public/draco/   decodificador local
```

**Próximo passo planejado:** ver `docs/PLANO-FIAP-NEXT.md`.

### Atualização — arena médica (22/09/2026)

O Hospital do Duelo agora se apresenta como **Arena médica** e é o ambiente inicial;
a Escola permanece disponível. Bancada autoral, console físico, iluminação e LEDs
reagem a uma cópia do estado da partida, sem alterar regras online. Personagens de
cenário usam variantes locais leves; órgãos não foram simplificados. O crânio ganhou
acabamento de osso e iluminação específica, mantendo GLB e abertura originais.

Baseline, arquivos, evidências Blender/Unity, testes e limites estão em
`docs/ARENA-MEDICA-2026-09-22.md`. Desktop e testes automatizados verificados;
**homologação física no Quest ainda pendente**. Não confundir a bancada de escala
Unity nem o teste `verify:xr` com validação de conforto/performance em headset.

### Atualização — entorno e controles (23/09/2026)

O centro aprovado da Arena médica permanece intacto. O entorno agora usa um GLB
autoral de oito malhas: armários, preparo, carrinho, estação de simulação e
arquitetura técnica. O botão 3D confirma raios XR no aperto, com alvo estável,
contorno por ponteiro e camadas visuais ordenadas. Isso corrige a perda de
`click` após 300 ms da biblioteca instalada e o fundo cobrindo alternativas.

Diagnóstico, orçamento do GLB, testes e roteiro de homologação física em
`docs/ARENA-ENTORNO-E-CONTROLES.md`. Novo comando: `npm run verify:botoes-xr`
(também em `verify:core`). **O Quest com controles ainda precisa do reteste físico.**
