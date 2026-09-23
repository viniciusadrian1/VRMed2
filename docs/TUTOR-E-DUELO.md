# Tutor com foco 3D e perguntas acessíveis do Duelo

Implementação e validação local: 23/09/2026. Base: `4837113`.

## Entrega

O chat do visualizador pode solicitar foco em um alvo que realmente exista no
GLB carregado. No desktop, o alvo recebe enquadramento suave, destaque dourado,
rótulo e contexto semitransparente. Em VR/AR só o modelo recebe destaque: a
câmera do headset continua inteiramente controlada pelo aluno.

O Duelo ganhou 30 perguntas locais de conhecimento geral: coração (6), rins
(6), cérebro (6), fígado (4), sistema digestório (4) e laringe (4). Os textos
priorizam função e curiosidades; não dependem de IA ou conexão com a OpenAI.

Nenhum asset, dependência, regra de acerto ou controle de gatilho foi substituído.
O GPT usado pelo produto continua sendo o `gpt-4o` já configurado. O modelo do
agente de desenvolvimento não é o modelo executado pela aplicação.

## Tutor: fluxo e limites

1. `OrganModel` registra o órgão inteiro e os rótulos deduplicados das malhas
   reconhecidas, com uma revisão transitória. Modelos por tecido oferecem só
   foco no conjunto; placeholders não anunciam anatomia disponível.
2. O chat envia o histórico limitado e esse inventário ao servidor. A chave
   OpenAI existente é reutilizada somente no servidor, sem mudar o `.env`.
3. Uma função estrita `guiar_modelo` aceita apenas `focar`/`restaurar` e os IDs
   enumerados. Não aceita código, URLs, coordenadas nem troca de órgão.
4. O servidor valida a função antes de emitir o comando por NDJSON. Depois
   solicita a explicação textual. O cliente valida novamente o alvo e descarta
   comandos cujo contexto já mudou ou cujo guia foi desativado.
5. O enquadramento é calculado pelas dimensões reais da malha. Interação manual
   com a câmera cancela a transição. `prefers-reduced-motion` desativa a animação
   automática; VR/AR nunca executam esse movimento.

Há no máximo uma ação visual e duas chamadas de conclusão por pergunta guiada.
O chat sem guia mantém o caminho anterior de streaming textual. O guia pode
aumentar custo e latência; não foi feita medição financeira ou comparativo de
latência. A função segue o fluxo de [function calling da OpenAI](https://developers.openai.com/api/docs/guides/function-calling).

“Limpar foco” restaura as configurações prévias de camadas, sem apagar ajustes
do aluno. Alterar camadas, cortes, explosão, estrutura selecionada ou modo do
gizmo também encerra o destaque. Trocar o órgão aborta a resposta em andamento.
Desligar/religar o guia invalida comandos antigos. O pulso do marcador é suave,
dura três segundos e depois fica estático; não há bloom ou luz adicional.

O coração atual não tem um ventrículo esquerdo isolável. A IA deve explicar a
limitação e responder à pergunta sem simular uma segmentação inexistente. Isso
foi confirmado numa resposta real. Para esse exemplo ganhar foco específico,
será necessário um modelo segmentado/rotulado e validado anatomicamente.

Foi corrigido também um problema do detector: ele subia até `vrmed-root` e
anunciava “Vrmed Root” como estrutura de modelos anônimos. Há teste de regressão
para esse limite da hierarquia.

### Uso no headset

O incremento seguinte substitui o painel de perguntas rápidas por dois painéis
laterais: Ferramentas do modelo e Tutor de IA. Há teclado 3D, histórico
compartilhado com o DOM, perguntas rápidas, paginação e cancelamento.
Trocar de órgão cancela o pedido sem apagar o histórico. A câmera continua livre.

Detalhes e roteiro em `PAINEIS-ESTUDO-XR.md`. Não há reconhecimento de voz.
Ainda requer teste físico de posição, legibilidade, seleção e conforto no Quest.

## Duelo: variedade sem mudar a competição

- Oito rodadas, alternância 100/200 pontos, total disponível de 1.200 pontos.
- Duas identificações do conjunto, cinco perguntas de conhecimento e uma
  identificação de estrutura real da laringe.
- Se não houver pelo menos quatro rótulos únicos na laringe, a última rodada
  usa outra pergunta de conhecimento, sem inventar pontos anatômicos.
- Sem repetição da mesma pergunta na partida. Nas revanches, prioriza perguntas
  fora das últimas 20 sorteadas durante a montagem atual do componente. Não é
  histórico persistente entre recargas/aparelhos.
- Alternativas embaralhadas; explicação curta depois da resposta. Os enunciados
  e alternativas têm limites de tamanho testados para os painéis existentes.
- Permanecem 18 segundos por rodada e a janela de arbitragem online de 600 ms.

O banco é enviado com as rodadas aos dois clientes. A validação do servidor
confere pergunta, gabarito, explicação, modelo, opções e pontuação canônicos nas
questões novas. O protocolo passa para **versão 2**: páginas antigas recebem a
orientação de recarregar ambos os aparelhos. Um deploy ainda encerra salas em
memória, como já ocorria. Não houve migração para banco compartilhado ou
alteração da arquitetura de salas de instância única.

### Referências do conteúdo

As perguntas são autorais, curtas, para público geral; não são diagnóstico ou
aconselhamento clínico. Fontes por item estão em `FONTES_DUELO`:

- Coração e circulação: [NHLBI — fluxo do sangue](https://www.nhlbi.nih.gov/health/heart/blood-flow).
- Filtração, água, sais e néfrons: [NIDDK — como os rins funcionam](https://www.niddk.nih.gov/health-information/kidney-disease/kidneys-how-they-work).
- Digestão, bile, absorção e peristaltismo: [NIDDK — sistema digestório](https://www.niddk.nih.gov/health-information/digestive-diseases/digestive-system-how-it-works).
- Voz, fluxo de ar e pregas vocais: [NIDCD — voz](https://www.nidcd.nih.gov/health/taking-care-your-voice).
- Cérebro: [NINDS — Know Your Brain](https://www.ninds.nih.gov/sites/default/files/2025-05/know-your-brain-brian-basics.pdf).
  O acesso automatizado integral ao PDF NINDS falhou. Como apoio, foram
  consultados trechos indexados do material educacional [NIDA — The Brain](https://archives.nida.nih.gov/sites/default/files/the_brain_understanding_neurobiology_through_the_study_of_addiction.pdf)
  sobre sinais neurais e o resumo de [Cerebral cortex expansion and folding: what have we learned?](https://pubmed.ncbi.nlm.nih.gov/27056680/).

Recomenda-se revisão por um docente da área antes do evento. A validação de
código/gabarito não substitui revisão acadêmica das formulações e distratores.

## Validação realizada

- `npm run typecheck`: passou.
- `npm run lint`: passou.
- `npm run build`: passou.
- `npm run verify:core`: nove grupos passaram, incluindo XR, salas online,
  áudio, apresentação, botões XR, Escola, retaguarda, tutor e perguntas.
- `verify:tutor`: alvos inválidos, troca de contexto, desligar/religar guia,
  restauração real dos materiais Three.js sem mutação das camadas, raiz não
  anatômica, streaming UTF-8 fragmentado, falhas e comandos truncados/inválidos.
  As guardas de câmera XR incluem checagens estáticas, não um headset emulado.
- `verify:perguntas`: 1.000 sorteios reprodutíveis, todas as 30 perguntas
  alcançadas, variedade, arquivos GLB presentes, limites de texto e gabaritos.
- `npm run verify:duelo-http`: passou contra o build local em 3002. Dois
  clientes HTTP/SSE recebem rodadas idênticas e pontuação sincronizada após
  identificação e conhecimento. Versão antiga retorna 409; adulteração de
  gabarito retorna 400. O script encerra a própria sala e só aceita localhost.
- Navegador desktop: perguntas nos dois ambientes, resposta correta com mouse
  na Arena médica e com teclado na Escola, feedback, explicação, troca de
  rodadas e chegada à tela final em partida contra bot.
- OpenAI real: foco/explicação da epiglote e resposta sobre a impossibilidade
  de isolar o ventrículo no coração atual. O primeiro servidor de desenvolvimento
  tinha restrição de rede; o build local com acesso autorizado completou o teste.
- Inspeção final: limpar foco devolveu a opacidade e os pontos da laringe;
  os consoles observados do visualizador e do Duelo não registraram erros.
  Captura: [epiglote destacada](evidencias/tutor-epiglote-2026-09-23.png).

Avisos Node `MODULE_TYPELESS_PACKAGE_JSON` permanecem; não são falhas dos testes.

## Arquivos

- Contrato, estado e função do tutor: `lib/tutor-3d.ts`,
  `lib/tutor-3d-store.ts`, `lib/tutor-3d-servidor.ts`.
- Integração: `app/api/chat/route.ts`, `lib/chat-client.ts`,
  `components/chat/ChatPanel.tsx`, `lib/viewer-bridge.ts`.
- Cena: `components/viewer/Scene.tsx`, `OrganModel.tsx`, `FocoTutor3D.tsx`,
  `TutorPainelVR.tsx` e `lib/model-utils.ts`.
- Perguntas/salas: `lib/duelo-perguntas.ts`, `lib/duelo-schema.ts`,
  `lib/duelo-salas.ts`, `lib/duelo-apresentacao.ts`,
  `app/api/duelo/route.ts`, `components/duelo/DueloGame.tsx`.
- Verificações: `scripts/verificar-tutor-3d.ts`, `verificar-perguntas-duelo.ts`,
  `verificar-duelo-http.ts`, `verificar-apresentacao-duelo.ts`, `package.json`.
- Contexto: este relatório e `docs/CONTEXTO.md`.

## Homologação pendente

Não houve teste físico no Quest, medição de FPS/GPU ou partida entre dois
headsets reais. Não declarar conforto/performance homologados pelo build.

Após publicação autorizada, recarregar os dois aparelhos e verificar:

1. Abrir laringe no visualizador, selecionar uma peça e usar o Tutor 3D.
2. Confirmar destaque sem qualquer deslocamento da câmera da cabeça.
3. Ler/paginar, limpar foco, fechar painel e sair/reentrar em VR.
4. Jogar e pedir revanche nos dois ambientes, com controles e perguntas novas.
5. Conferir precisão A–D, explicações, troca sem órgão residual e FPS sustentado.

Não adicionar um asset cardíaco novo sem conferir licença, segmentação,
fidelidade anatômica e orçamento do Quest. Unity/Blender não foram necessários
neste incremento de integração e conteúdo; o runtime permanece web.
