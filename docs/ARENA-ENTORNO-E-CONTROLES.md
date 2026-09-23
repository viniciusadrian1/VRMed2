# Arena médica — entorno e seleção com controles (23/09/2026)

## Escopo e preservação

O usuário aprovou o centro da arena e pediu mais qualidade no entorno. Relatou
alternativas que não respondiam ou pareciam selecionar a opção errada **no Quest
com controles**. Esta revisão preserva `ArenaMedica.tsx`, `DueloGame.tsx`, a bancada
central, posições das alternativas e regras de pontuação/arbitragem online.

## Diagnóstico da seleção

Três problemas verificáveis foram encontrados:

1. A biblioteca instalada `@pmndrs/pointer-events` só gera `click` quando o botão
   é solto em até **300 ms**, sobre o mesmo objeto. O teste com o ponteiro real
   da biblioteca reproduziu a perda de resposta ao segurar por 700 ms.
2. O botão animava a escala do grupo que continha o próprio alvo do laser:
   crescia no hover e encolhia no aperto. As bordas da região selecionável se
   deslocavam durante a interação.
3. Fundo do painel e fundo dos botões compartilhavam a mesma ordem de desenho.
   A ordenação de transparências por distância cobria alguns botões. Na captura
   inicial, alternativas inferiores ativas pareciam apagadas. A inspeção após
   recarregar confirmou a correção das cores, ícones e estados.

Esses defeitos são causas concretas de falhas de interação/leitura, mas não
substituem a reprodução de todos os sintomas no aparelho do usuário.

### Correções

- Raio XR confirma no **aperto do gatilho**; seu `click` de soltura é ignorado,
  evitando perda por duração e confirmação duplicada/em outra tela.
- Mouse e toque mantêm o clique convencional. Botão secundário não responde.
- Uma única malha-alvo com dimensões fixas. Apenas o desenho comprime levemente.
- Contorno de mira sem crescimento sobre a alternativa vizinha; corredores
  entre opções continuam neutros.
- Hover e pressão registrados por `pointerId`, para não misturar os dois lasers.
- Háptica usa a fonte do ponteiro que interagiu, quando disponível.
- Prioridade de raycast dos botões e decoração com `pointerEvents="none"`.
- Camadas explícitas para painel, botões, contorno/ícone e texto. As camadas
  visuais não fazem raycast nem escrevem no buffer de profundidade.

Referência de semântica: [interações do React Three XR](https://pmndrs.github.io/xr/docs/tutorials/interactions).
O limite de 300 ms foi verificado no código **instalado** da biblioteca, não
inferido a partir da documentação. O `Button3D` é compartilhado com Arena/Sala;
por isso esses modos também precisam de um smoke test físico em VR.

## Entorno autoral

Produzido pelo Blender MCP com o script reproduzível
`scripts/criar-entorno-arena.py`, em cena separada, sem sobrescrever a cena
original do usuário. Exportado para `public/models/props/entorno-arena.glb`.

- Baías de preparo e suprimentos: molduras, armários com ferragens, visores,
  bancada, cuba, torneira e recipientes de treinamento.
- Carrinho com rodízios, gavetas, bandeja, alça e instrumentos estilizados.
- Estação de simulação com monitor, teclado, sonda e cabo. O visor é abstrato e
  rotulado; não representa medida fisiológica nem nova capacidade do produto.
- Janela técnica opaca, dutos, travessas, ventilação e porta de apoio.
- LEDs laterais ligados aos sinais existentes da partida. Monitor do adversário
  apoiado junto à bancada lateral.
- Prateleiras/pôsteres simples e instâncias antigas de carrinho/monitor/ultrassom
  substituídos; seus arquivos originais permanecem no acervo. Cortina e cadeira
  permanecem nas zonas de apoio.

### Orçamento medido do novo arquivo

| Item | Valor |
| --- | --- |
| Tamanho | 1.379.572 bytes |
| Triângulos | 19.388 |
| Malhas / materiais | 8 / 8 |
| Texturas / animações | 0 / 0 |
| Draco | Não utilizado; glTF padrão local |

Geometria agrupada por material; oito primitivas no asset, não oito draw calls
na cena inteira. Sem novas luzes dinâmicas, sombras, pós-processamento ou
dependências. Nenhum órgão foi simplificado. DPR em XR permanece inalterado.
**FPS, latência e conforto no Quest não foram medidos nesta revisão.**

## Validação realizada

- `npm run typecheck`, `npm run lint` e `npm run build`: passaram.
- `npm run verify:core`: passaram ciclo XR, salas online, áudio, apresentação
  e o novo `verify:botoes-xr`.
- O teste de ponteiro usa `createRayPointer` real da versão instalada: aperto
  de 700/80 ms, ausência de duplicação, mover C→D antes de soltar, desabilitado,
  centro/bordas A–D, corredores e decoração interceptora; contrato mouse/toque.
- Teste do GLB verifica limite de tamanho/triângulos, oito malhas e ausência de
  texturas externas/animações. Integridade byte a byte do crânio e guardas de
  remoção do órgão anterior continuam passando.
- Navegador desktop: início por mouse, resposta B correta (+100), entrada de
  teclado, troca de rodada/modelo, feedback de erro/tempo e estados reativos.
- Build de produção em `localhost:3001`: entorno e UI carregaram; inspeção
  frontal/lateral; alternância para Escola preservada.
- Console do Duelo de produção: sem erros capturados. Avisos existentes sobre
  `THREE.Clock` depreciado e `KHR_materials_pbrSpecularGlossiness` em assets do
  acervo permanecem; não são extensões do novo entorno.
- `/arena` informa corretamente que este navegador desktop não oferece VR;
  não considerar a abertura dessa rota um teste imersivo.
- Sala de Estudos: cena carregada, hub aberto pelo monitor, botões legíveis e
  navegação por clique em Duelo confirmada na build de produção.

### Evidências

- [Menu e entorno](evidencias-arena/entorno-menu.png)
- [Resposta correta pelo mouse](evidencias-arena/entorno-acerto.png)
- [Build de produção](evidencias-arena/entorno-producao.png)

## Homologação pendente no Quest

Após o deploy, reabrir `/duelo` no Quest Browser e entrar em **Arena médica**:

1. Testar controle esquerdo e direito separadamente; mirar centro e bordas das
   quatro opções. Observar o contorno antes de apertar.
2. Testar aperto rápido e segurar por cerca de 1 segundo. Deve confirmar uma
   única vez ao apertar, sem depender da soltura.
3. Apertar uma opção e mover o laser antes de soltar: não deve escolher outra
   nem responder automaticamente à próxima rodada.
4. Apontar entre opções: não deve responder. Usar os dois lasers e conferir
   contorno/háptica, legibilidade e conforto.
5. Testar partida completa, Escola, Arena/Sala, entrar/sair do VR e Duelo online
   com dois aparelhos. Testes automatizados de salas não validam rede real.
6. Medir estabilidade com o painel Desempenho durante modelos leves e crânio;
   a presença do crânio pesado continua exigindo homologação específica.

## Arquivos principais

- `components/arena/ui3d.tsx` e `lib/botao3d-interacao.ts`: interação e desenho.
- `components/duelo/AmbienteHospital.tsx` e `EntornoHospital.tsx`: composição.
- `public/models/props/entorno-arena.glb`, `CREDITS.md` e
  `scripts/criar-entorno-arena.py`: asset autoral e reprodução.
- `scripts/verificar-botoes-xr.ts`, `verificar-apresentacao-duelo.ts` e
  `package.json`: regressão e orçamento.

O usuário autorizou enviar esta revisão à `master` de
`viniciusadrian1/VRMed2` para teste no Quest. Aprovação de deploy não é
homologação física do headset.
