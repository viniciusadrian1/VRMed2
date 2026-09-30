# Ajustes de controles, painéis e sugestões — 30/09/2026

## Escopo e estado

Revisão local após relato de botões ocupando a mesa, travadas com os painéis
AR/VR e sugestões genéricas no tutor. Sem alterar modelos anatômicos, salas,
regra do Duelo, câmera XR, API da OpenAI ou dependências. O usuário autorizou o
commit na master e a publicação desta revisão na CX33 para reteste no Quest.
A imagem ativa é identificada pelo SHA na tag e no label OCI do contêiner;
não confundir com a sala renovada publicada anteriormente. Homologação no
headset continua pendente.

## Controles da sala individual

`SalaRecentravelXR.tsx` usa um painel compacto à direita do assento, voltado para
o aluno, com Recentralizar e Sair do VR empilhados. Coordenadas locais em
`lib/sala-recentrar.ts`: x=0,94 m, z=-1,42 m, largura 0,62 m, altura 0,39 m.
A altura continua acompanhando a pose inicial/recentralização, sem alterar o
piso ou seguir a cabeça continuamente. Atalhos Y/B e encerramento seguro mantidos.

O teste geométrico revelou uma falha numérica na diagonal dos dois triângulos
do botão, em uma combinação de altura e ângulo. `Button3D` passa a reutilizar
`raioPlacaXR`, já usado nas janelas: mesmo retângulo, sem fenda na diagonal.

Regressão: 30 poses, ambos os botões e ambas as mãos (120 seleções), com
gatilho longo. Mais 30 linhas de visão de três alturas para monitor, rádio
e livro, sem interseção com o painel. São testes de geometria, não de conforto
real do headset. Confirmar acesso lateral e leitura sentado no Quest.

## Custo dos painéis HTML em AR/VR

O caminho anterior copiava centenas de propriedades CSS por nó, inclusive
descendentes ocultos e linhas inteiramente fora da janela de rolagem. Além
disso, a validação de hover relia estilo/layout a cada movimento do raio.

Mudanças em `lib/renderizar-painel-dom.ts` e `PainelSiteXR.tsx`:

- CSS computado restrito às propriedades visuais usadas, compartilhado por
  classes na captura. Fonte local, cores, ícones, Markdown e resolução 2× mantidos.
- Abas ocultas não clonam descendentes. Mensagens/camadas fora do recorte viram
  espaçadores de dimensão medida; itens parcialmente visíveis continuam completos.
  O DOM original e o histórico permanecem intactos.
- Dois canvases reutilizados por painel. Textura visível só troca após imagem válida.
- Capturas pendentes canceladas ao minimizar/desmontar; suspensas enquanto a
  sessão/página está oculta. Intervalo contado após concluir a captura, evitando
  emendar capturas lentas. Mudanças de tabindex não geram recaptura.
- Hover consulta o mapa da textura, sem reler layout por quadro; clique mantém
  validação do alvo atual. Slider e rolagem sem mudança não pedem captura.
- Alça, redimensionamento e identidade visual do site preservados.

### Medição exploratória no navegador desktop

Mesmo painel de ferramentas da laringe e resolução, na prévia de desenvolvimento
`/viewer?inspecao=paineis&debug=paineis`. Comparação local, não benchmark controlado
nem medição no Quest. A preparação inclui alvos, cópia de estilos e serialização;
o total também inclui decodificação e desenho em canvas, mas não mede o custo
posterior de upload da textura à GPU.

| Medida de ferramentas | Antes | Depois |
| --- | --- | --- |
| Preparação por captura | 914–1004 ms (3 amostras) | 25–27 ms (2 amostras) |
| Total por captura | 953–1160 ms (3 amostras) | 45–48 ms (2 amostras) |
| Comprimento da URL SVG codificada | 7.432.807 caracteres | 238.827 caracteres |
| Nós copiados/visitados | 697 | 242 |

Esses valores não são FPS nem garantem eliminação de travadas. A coleta ocorreu
antes do ajuste final de preservação do estilo de scrollbar; pequenas variações
são esperadas. O tutor também caiu de cerca de 150–172 ms de preparação para
10–12 ms no histórico inspecionado. Não expor conteúdo de conversa em logs:
`debug=paineis` registra apenas tempos, contagens e tamanho da captura.

## Perguntas por modelo

`lib/tutor-perguntas.ts` define três sugestões educativas distintas para cada um
dos 19 modelos. O ID legado `estomago` considera o trato digestório completo.
Não prometem isolar estruturas que o GLB não disponibiliza.

`ChatPanelContent` reutilizado no site e XR recebe as sugestões pelo modelo atual.
Na conversa existente, ficam no grupo expansível “Dúvidas sobre …”, sem apagar
o histórico. A captura reconhece `summary` como alvo clicável. Sem chamada extra
à OpenAI para gerar sugestões; elas passam pelo fluxo normal ao serem escolhidas.

## Verificação

Passaram `npm run typecheck`, `npm run lint`, `npm run verify:core` e
`npm run build`. `verify:paineis-xr` incorpora os testes de recorte, cancelamento,
hover sem layout e sugestões para todos os modelos, com/sem histórico e DOM/XR.
Mantidos 324 cliques por pixel e 96 casos de borda/manipulação das janelas.

No navegador integrado, com mouse sobre as superfícies 3D reais da prévia:
abas Camadas/Cortes/Notas/Áudio, corte axial, rolagem de lista e conversa, ocultação
de camada após rolar, temas claro/escuro, sugestões coração/laringe,
minimização/reabertura e ausência de capturas do tutor minimizado foram conferidos.
Sem erros no console. Nenhuma chamada nova à OpenAI foi necessária nesses testes.

### Reteste físico obrigatório

1. `/sala`: sentado, conferir monitor, livro e rádio desobstruídos; olhar à direita
   e usar ambos os botões. Repetir Y/B e sair/reentrar no VR.
2. `/viewer`: testar AR e VR, com um e dois painéis, tanto laringe quanto crânio.
3. Comparar fluidez parado, rolando, durante resposta do tutor e movendo janelas;
   medir FPS/longas travadas no dispositivo antes de declarar resolvido.
4. Confirmar cliques após mover/redimensionar, sliders, minimização e recuperação.
5. Trocar órgão e conferir novas dúvidas sem apagar a conversa.

Se ainda houver travadas, medir separadamente captura/CPU, upload de textura e
renderização da anatomia. Trocar de servidor não remove esses custos do Quest.
