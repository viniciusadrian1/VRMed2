# Plano multi-modo — Sala de Estudos e Duelo 1×1

> Origem: planejamento do grupo (2026-08-29) para dois novos modos. O plano
> original recomendava Unity; decisão registrada com o grupo: **os modos
> entram no VRmed web existente** (Next.js + R3F + WebXR) — reaproveitam o
> tutor de IA, os modelos, o padrão de XR endurecido e o deploy do Render,
> e continuam abrindo por link no navegador do Quest, sem sideload.

## O que já está implementado (Fase 1)

### `/sala` — Sala de Estudos Individual (Modo 1)
- Quarto procedural (mesa, cadeira, janela, planta, luz quente) — zero assets.
- **Rádio lo-fi**: síntese WebAudio própria (livre de copyright, offline).
  Para usar faixas reais: colocar MP3s royalty-free em `public/audio/lofi/`
  com `manifest.json` (`{"tracks":[{"title":"…","file":"a.mp3"}]}`).
- **Computador**: hub 3D → Estudo/Arena/Clínica/Quiz. WebView em VR é
  inviável em qualquer engine — hub interno confirmado como decisão.
- **Flashcards**: base curada em `public/flashcards/base.json` (6 temas ×
  4 cartas) + geração de cartas novas via `/api/chat` ("+4 com IA").
- **Livro → tutor de IA**: gaveta DOM com streaming no desktop; painel 3D
  com perguntas rápidas dentro do VR.

### `/duelo` — Jogo de Conhecimento Médico 1×1 (Modo 2)
- 8 rodadas alternando órgão inteiro (100 pts) e estrutura da laringe
  marcada (200 pts); opções em botões 3D; cronômetro de 18s por rodada.
- **Bot** com 3 dificuldades (atraso e taxa de acerto): Iniciante /
  Residente / Especialista. Avatar médico low-poly procedural com reações
  (comemora/murcha) — substituível por GLB (Mixamo/Sketchfab CC) depois.
- Funciona em desktop (mouse) e VR (laser) com a mesma cena.

## Pendências (Fase 2)
- **Online 1×1**: WebSocket (servidor no Render) ou serviço realtime;
  a máquina de estados já separa "quem pontuou" de "como a resposta chegou",
  então o oponente remoto substitui o bot sem reescrever o jogo.
- **RAG com material próprio**: o grupo vai fornecer apostilas/resumos;
  indexar e fundamentar flashcards + tutor nesse material (hoje: fontes
  abertas via system prompt existente).
- **Voz no tutor** (reconhecimento + síntese) — avaliar `lib/tts.ts` existente.
- Música lo-fi por arquivos (baixar faixas royalty-free e criar o manifest).
- Auto-reset da sala/duelo ao fim da sessão XR (regra de estande da Arena).
- Teste de conforto/fps no Quest 2 real (os dois modos).

## Regras herdadas que valem aqui
- UI em VR é 3D (Text3D/Panel/Button3D com fonte local) — DOM é invisível.
- XR store endurecido (perfis locais, só raio, sem MR, `frameRate: false`).
- Rotas isoladas: nada de store global; cada modo com canvas próprio.
- `Panel`/`Text3D` têm raycast desligado — item clicável precisa de malha
  raycastável própria (plano invisível).
- Sem CDN em runtime; sem áudio com copyright; conteúdo médico com fontes.
