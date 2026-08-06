# VRmed no FIAP Next — plano da experiência VR

> Plano aprovado em 2026-07-07. Objetivo: transformar o VRmed numa experiência de estande capaz
> de **ganhar votação popular** no FIAP Next.

## Restrições reais do evento

- **Ambiente barulhento** → entrada por voz **descartada** (microfone não funciona no caos).
  Mas atenção: o **áudio de saída do headset funciona muito bem** (alto-falantes junto ao ouvido).
- **Meta Quest, sem modificação física** — só dá para mudar software.
- **O público joga** → à prova de leigo, zero instrução, troca rápida.
- **1 headset garantido**, 2 se der. **Monitor provável**, não garantido.
- Prazo: mais de 2 semanas.

---

## Diagnóstico: a experiência em VR hoje é praticamente vazia

| No headset hoje | Situação |
|---|---|
| Ver o órgão flutuando, na escala certa, iluminado | ✅ funciona |
| Apontar o laser e apertar o gatilho → estrutura acende em azul | ✅ funciona (padrão do `@react-three/xr`) |
| **Ler o nome da estrutura clicada** | ❌ **impossível** |
| Ler qualquer rótulo, painel ou botão | ❌ impossível |
| Aproximar, orbitar, girar, pegar o modelo | ❌ não existe |
| Andar / teletransportar | ❌ desligado |

**Causa raiz:** `StructureHotspots.tsx` e `AnnotationSystem.tsx` usam drei `<Html>`, que cria um
nó **DOM real** — e o DOM não é composto dentro de uma sessão `immersive-vr`. Toda a UI
(`ViewerControls`, `ToolsPanel`, `InspectBar`, `ChatPanel`) é DOM. Além disso,
`viewerBridge.frameTo/zoom/resetCamera` **viram no-op em VR**, porque o `@react-three/xr`
substitui a câmera pela câmera do headset.

**Conclusão:** não é "melhorar o VR", é **construir o VR**. A base (laser, clique, escala,
iluminação) já funciona e as peças de jogo já existem no código.

---

## O conceito: "Código Vermelho — Plantão de 60 segundos"

Jogo de identificação anatômica sob pressão, 60–90s, desenhado para barulho, leigo e plateia.

**A virada sobre o barulho:** o microfone morreu, mas o barulho da plateia **vira o produto** —
a torcida gritando "atrás! embaixo!" é exatamente o espetáculo que queremos.

### O laço principal

1. **Entra** → órgão gigante (2–3 m) à frente. Escala é o "uau" que só existe em VR.
2. **Alvo em texto 3D:** *"Encontre: Cartilagem tireóidea"* + cronômetro.
3. **Aponta e puxa o gatilho** → acerto: flash verde, partículas, som, combo sobe.
   Erro: flash vermelho, −2s.
4. **60 segundos**, quantas conseguir. Streak multiplica.
5. **Fim:** pontuação + recorde do dia + **"Laudo do Cirurgião"** escrito pela IA → **QR code**
   para levar no celular.

### Por que ganha voto

- **Atrai de longe:** modo atração rodando sozinho (gira, corte varre, coração bate).
- **Entendível em 5s:** apontar e apertar. Sem tutorial.
- **Gera torcida:** cronômetro e placar visíveis; a plateia grita direção.
- **Vira fila** — e fila é a maior prova social do estande.
- **Fica na memória:** o QR leva o laudo para casa; na hora de votar, a pessoa lembra.

---

## Mecânicas (por impacto ÷ esforço)

### Essenciais

| # | Mecânica | Nota |
|---|---|---|
| 1 | **UI em espaço 3D** | drei `<Text>`/`<Billboard>` (troika **já instalado**). Destrava tudo. |
| 2 | **Alvo + acerto/erro** | Sorteia de `detectStructures()`, compara com `identifyStructure()` no clique. |
| 3 | **Escala gigante** | 2–3 m em vez dos 2 m normalizados. |
| 4 | **Perfil de performance Quest** | Sem isso engasga e dá enjoo. |

### O "show"

| # | Mecânica | Nota |
|---|---|---|
| 5 | **Pegar com squeeze** | Grab pointer **já vem ativo**; falta o objeto ser agarrável. |
| 6 | **Coração batendo** | `useFrame` com escala senoidal + som no headset. |
| 7 | **Modo atração (idle)** | Sequência automática quando ninguém joga. |
| 8 | **Explodir camadas** | Afasta as malhas radialmente e junta. Momento filmável. |
| 9 | **Combo + recorde do dia** | Ranking local em texto 3D. |

### IA de verdade

| # | Mecânica | Nota |
|---|---|---|
| 10 | **Laudo do Cirurgião** | `/api/chat` já existe. Vai para o monitor + QR. Custo: <R$ 0,01/jogador com `gpt-4o-mini`. |
| 11 | **Dica quando trava** | >15s sem acerto → dica em texto 3D. |
| 12 | **Micro-aula no acerto** | Uma frase de por que a estrutura importa. |

**Narrativa:** *"Você é o cirurgião. A equipe te guia. 60 segundos."* Drama moderado — público de
tecnologia gosta, estudante de saúde detesta drama falso. `COMPARISON_NOTES` já serve de fala do mentor.

---

## 1 headset vs 2

**1 headset (base)** — rodadas de 60s, fila visível, monitor por **casting nativo do Quest
(zero código)**. **Duelo por revezamento (hot seat)**: dois amigos, 60s cada, o segundo entra
sabendo o número a bater. Gera rivalidade **sem headset extra, sem rede, sem servidor**.

**2 headsets** — **semente compartilhada** (mesmo código de sala → mesma sequência de alvos,
cada um no seu ritmo, compara no fim). Zero rede. Duelo sincronizado por SSE só se sobrar tempo.

---

## Plano técnico

Decisão de arquitetura: **modo novo e isolado** (ex.: rota `/arena`), com `<Canvas>` e store XR
próprios. Importa o que já existe (`detectStructures`, `identifyStructure`, `GLBModel`, catálogo)
e **não toca** em visualizador, comparar, quiz, histórico e landing. Se o jogo quebrar, o app
continua de pé — importante porque o visualizador é o que sustenta a defesa da IC.
Sem conflito com o `viewerBridge` (singleton), porque em VR a câmera é a cabeça do jogador.

### Fase 0 — Fundação VR (bloqueante)

1. **Ramificação por sessão:** `useXR(s => s.session)` para trocar UI DOM por UI 3D
   (hoje **não existe nenhum** hook desses no app).
2. **UI 3D:** `XRHud` com drei `<Text>` + `<Billboard>` — sem dependência nova.
3. **Rótulo da estrutura em VR** ancorado na malha — conserta o laço quebrado hoje.
4. **Perfil de performance Quest:** `shadows={false}`, remover `<ContactShadows>`, remover
   `<SafeEnvironment>` (busca HDR na rede — falha no wifi do evento), `foveation` e `frameRate`
   no `createXRStore`, tirar `occlude` dos `<Html>` (raycast por frame para conteúdo invisível).
5. **`emulate: true` em desenvolvimento** para iterar sem headset.

**Modelos permitidos em VR:** `larynx` (18k, 20 estruturas) e `coracao` (11k).
**`myology` (982k) é proibido.**

### Fase 1 — O jogo
`ChallengeMode` dentro do Canvas: alvos de `detectStructures()`, acerto comparando
`identifyStructure(event.object)`, máquina `setup → playing → result` (copiar de `QuizMode.tsx`),
cronômetro em `<Text>` 3D, feedback com `highlightMesh` + partículas + som.

### Fase 2 — Espetáculo
Batimento (`useFrame`), explodir camadas, modo atração dirigindo a store
(`setLayerOpacity`/`isolateLayer`/`applyXray`/`setClipPlane` — o `ModelStateApplier` já aplica e
re-renderiza sozinho: canal de animação de graça), grab.

### Fase 3 — IA + levar para casa
Laudo via `/api/chat` + QR code na tela de resultado.

### Fase 4 — Plateia (opcional)
Casting nativo por padrão; página `/palco` com SSE só se sobrar tempo.

---

## Verificação

1. **No headset (sem substituto):** texto 3D aparece? gatilho acerta? nome aparece? fps segura?
   (Meta Quest Developer Hub / OVR Metrics).
2. **Sem headset:** `emulate: true` + emulador WebXR no desktop para a lógica.
3. **Meta:** 72fps estáveis no Quest 2, 90 no Quest 3.
4. **Teste com leigo:** tem que jogar **sem nenhuma instrução falada**. Se precisar explicar, falhou.
5. **Ensaio de estande:** sem wifi, bateria, higiene, troca em <15s.

## Riscos

| Risco | Mitigação |
|---|---|
| **HTTPS/WebXR** | `navigator.xr` não existe em `http://IP`. Usar HTTPS ou `adb reverse` por USB. **Testar primeiro.** |
| Wifi do evento cai | Tudo local (Draco já é); remover HDR remoto; testar offline |
| Casting instável | Plano B: visualizador desktop no monitor em paralelo |
| Bateria do Quest | Power bank + rodízio; brilho reduzido |
| Enjoo | Sem locomoção artificial; câmera nunca se move sozinha |
| `myology` na demo | Bloquear modelos pesados na lista de VR |

## Ordem

Fase 0 (fundação) → Fase 1 (jogo) → Fase 2 (show) → Fase 3 (IA/QR) → Fase 4 (plateia, se sobrar).
