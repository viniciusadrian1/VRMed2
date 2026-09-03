# VRmed — contexto do projeto

> Documento de continuidade. Se você (ou uma IA assistente) está abrindo este projeto numa
> máquina nova, leia isto primeiro. Última atualização: 2026-08-29.

## Modos novos (2026-08-29): Sala de Estudos e Duelo 1x1

Dois modos do plano multi-modo do grupo implementados DENTRO do app web
(decisão: sem Unity). `/sala` = quarto 3D com rádio lo-fi sintetizado,
flashcards (base curada + geração por IA), hub de modos e livro-tutor.
`/duelo` = quiz 1x1 contra bot (3 dificuldades, 100/200 pts, avatar médico
procedural); online fica para a fase 2. Detalhes e pendências:
`docs/PLANO-MULTIMODO.md`.

**Unity como bancada de assets (2026-09-01):** o grupo quer trocar o AMBIENTE do
Duelo por um cenário que só abre no Unity (.unitypackage). Fluxo: importar no
projeto Unity ("Tutorial no Editor do Guia de Configuração") → exportar GLB via
UnityGLTF → dieta (simplify se preciso + webp + draco) → palco do /duelo web.
O produto continua sendo o site; Unity NÃO vira runtime. Claude opera o Editor
via MCP (ver memória unity-mcp-setup: servidor HTTP :8080 da janela MCP for
Unity precisa estar ligado).

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

- **18 modelos** = 6 sistemas (corpo inteiro) + 6 regiões (anatomia nomeada) + 6 órgãos
- **3 órgãos** têm par patológico para o modo Comparar: coração, pulmão, fígado
- VR pelo navegador (WebXR), 100% pt-BR, tutor de IA citando apenas fontes médicas reconhecidas

### Peso dos modelos (medido) — decisivo para VR

| Modelo | Triângulos | Uso em VR |
|---|---|---|
| `larynx.glb` | 18k, **20 estruturas nomeadas** | ✅ ideal para jogo/identificação |
| `coracao.glb` | 11k (malha única) | ✅ ideal para o "uau" visual |
| `splanchnology.glb` | 303k | ⚠️ limítrofe |
| `myology.glb` | **982k** | ❌ **proibido em VR** — não sustenta 72–90fps estéreo |

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
