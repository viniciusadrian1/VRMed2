# VRmed — contexto do projeto

> Documento de continuidade. Se você (ou uma IA assistente) está abrindo este projeto numa
> máquina nova, leia isto primeiro. Última atualização: 2026-07-07.

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
