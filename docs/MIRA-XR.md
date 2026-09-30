# Mira e seleção com controles — 30/09/2026

## Diagnóstico

O relato foi de linha curta e dificuldade para saber onde o gatilho clicaria.
Inspeção da versão instalada de `@react-three/xr` / `@pmndrs/xr` confirmou:

- A linha padrão para controles termina em `min(1 m, distância da interseção)`.
  O raycast alcança mais longe: o limite era visual, não da seleção.
- O material padrão esmaece a ponta e tem opacidade 0,4. Cursor/linha eram
  desenhados nas ordens 1/2, antes da UI transparente (998–1228); o próprio
  painel podia cobrir o cursor.
- O visualizador ainda habilitava o grab padrão. `CombinedPointer` escolhe a
  interseção mais próxima: uma malha junto ao controle desativava o raio.
  Reproduzido com as classes reais no teste; não observado em headset nesta sessão.
- Itens/flashcards da Sala e seleção anatômica da Arena/Clínica usavam somente
  `onClick`, cujo padrão XR descarta apertos acima de 300 ms. Duelo e painéis
  já usavam `selectstart` corretamente.

## Alterações

- `lib/xr-mira.ts` compartilha configuração nas três stores: Sala/Duelo/Clínica,
  Arena e visualizador AR/VR, para os dois controles e raios das mãos.
- Linha contínua até o alvo, com teto visual de 12 m. No vazio é mais discreta,
  sem cursor prometendo um alvo inexistente. O alcance lógico não foi limitado.
- Cursor de 2,4 cm com ponto branco, anel colorido e contorno escuro, desenhado
  depois dos painéis. Ciano indica uma superfície interativa; âmbar indica
  gatilho pressionado, não acerto ou sucesso de uma operação.
- Distância mínima do raio: 5 cm, evitando a zona cega padrão de 20 cm ao
  aproximar a mão de um painel. Não houve aumento/invasão dos alvos dos botões.
- Grab/toque concorrentes desabilitados também no visualizador. A manipulação
  continua lendo grip, pinça e analógicos diretamente; câmera e regras intactas.
- Perfis dos controles no visualizador passam a usar `/webxr-profiles/` local.
- Itens da Sala, flashcards e seleção na Arena/Clínica confirmam no aperto do
  gatilho, sem duplicação na soltura; mouse/toque continuam no clique normal.
- Hover dos itens da Sala considera ambos os ponteiros. Háptica curta no aperto.

Não há nova dependência, pós-processamento, textura de mira, requisição externa
ou estado React por quadro. Continuam duas malhas de mira por ponteiro; só o
material do cursor ganhou o desenho procedural do anel.

## Validação local

- `npm run typecheck`, `npm run lint`, `npm run build` e `npm run verify:core`: passaram.
- Novo `verify:mira-xr` (incluído em `verify:core`): 12 casos de distância com os
  dois controles (8 cm–8 m), alinhamento de linha/cursor/interseção, painel
  inclinado, aperto de 800 ms, disputa com grab, cenário sem interação, vazio,
  prioridade da UI e desligamento do ponteiro.
- Mantidos os testes existentes de 324 cliques nos pixels dos painéis,
  redimensionamento/arraste, botões, controles e troca de órgão.
- Bancada WebGL no navegador renderizou os materiais reais e a comparação do
  padrão antigo com o novo, inclusive o estado pressionado, sem erro no console.
  A bancada não simula rastreamento, headset, desempenho ou conforto em XR.
- No build local: Sala abriu o tutor ao clicar no livro; visualizador carregou
  laringe/camadas; Duelo iniciou por mouse e confirmou alternativa com placar
  e feedback. Sem erros de console nesses fluxos (aviso existente `THREE.Clock`
  obsoleto). `verify:duelo-http` também passou com dois clientes HTTP/SSE locais.

## Reteste necessário no Quest

1. Sala: mirar rádio, livro, computador, flashcards e botões do tutor, sentado.
2. Duelo Escola/Hospital: menu, alternativas, aperto rápido e mantido, bordas.
3. Visualizador AR/VR: tutor/ferramentas claros e escuros, painéis próximos e
   afastados; minimizar, reabrir, arrastar, redimensionar e rolar.
4. Aproximar o órgão do controle sem perder a mira; testar giro, translação,
   grip e abertura/fechamento do crânio.
5. Usar cada controle e depois ambos; mirar no vazio; sair e reentrar na sessão.
6. Avaliar espessura/contraste no passthrough e precisão sobre botões pequenos.

Sem headset conectado, não há homologação física nem medição de FPS nesta etapa.
Alterações apenas locais: não publicadas no GitHub nem na CX33.
