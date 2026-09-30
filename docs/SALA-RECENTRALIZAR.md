# Recentralização da Sala de Estudos

Implementação local em 29/09/2026. Escopo: `/sala`, a sala individual com cadeira,
mesa, rádio e livro. Não altera a Escola do Duelo nem o visualizador de órgãos.

## Uso

Sente-se em uma cadeira física estável, olhe na direção desejada e aperte **Y no
controle esquerdo** ou **B no direito**. Também há o botão **Recentralizar** na
faixa à frente da mesa, ao lado de Sair do VR. Não é o botão Meta do sistema.
Com mãos rastreadas, use o botão pelo raio/pinça já oferecido pelo XR.
O texto confirma a recentralização; o botão pode ser usado novamente a qualquer
momento. A cadeira virtual não substitui um assento físico.

A entrada tenta acomodar a sala uma vez, quando recebe uma pose real. Se o
rastreio não estiver disponível, olhe à frente e peça a recentralização novamente.

## Comportamento e limites

- Alinha horizontalmente o centro do assento à cabeça e a mesa à direção do olhar.
- Move e gira a sala como conjunto; não modifica a câmera, a escala ou a altura
  real dos olhos. Não tenta transformar uma pessoa em pé em uma pessoa sentada.
- Não inclina o piso quando a pessoa olha para cima/baixo. Olhar quase vertical,
  pose estimada ou valores inválidos não produzem um reposicionamento.
- Após o ajuste, a sala fica parada. Rádio, livro e atividades abertas não são
  remontados. A luz e seu alvo acompanham a transformação da sala.
- Apertar e segurar Y/B dispara uma vez. Reconectar com botão segurado não dispara.
- Pedidos expiram em três segundos; abrir o menu do headset cancela o pedido.
- Ao sair, restaura a transformação original para o enquadramento desktop.
- Sair do VR continua montado fora do limite de erro da cena, preservando o
  encerramento seguro da sessão ao navegar.
- Nada publicado automaticamente; não há nova dependência ou asset.

## Verificação

`npm run verify:sala-recentrar` faz parte de `verify:core`: 30 poses sintéticas,
alturas sentada/em pé, rotação/deslocamento, piso sem elevação, repetição sem
deriva, raycast com as duas mãos, gatilho longo e borda de pressionamento.
As guardas de sessão e rastreio também têm verificações estruturais. Esses testes
não substituem rastreio, ergonomia ou desempenho no Quest físico.

Validação local: `typecheck`, `lint`, `build`, `verify:core` e `git diff --check`
passaram. A página foi inspecionada no navegador com `next start`: móveis e
objetos carregados, orientação de uso visível e tutor abrindo/fechando por teclado.
Sem erros de console capturados; permanece o aviso preexistente de depreciação de
`THREE.Clock`. O clique DOM automatizado não abriu o tutor nesta inspeção (o
teclado abriu); isso não foi tratado como comprovação de funcionamento do mouse.
O navegador integrado não oferece aqui o headset físico para validar a faixa XR.

Checklist no Quest (pendente):

1. Entrar sentado; conferir mesa, chão e alcance dos dois botões.
2. Girar a cadeira com segurança e apertar Y; repetir com B.
3. Clicar Recentralizar com os dois raios; segurar Y/B sem repetição.
4. Abrir flashcards/livro e ligar rádio; recentralizar sem perder a atividade.
5. Abrir o menu Meta/perder rastreio; voltar sem salto inesperado.
6. Sair/reentrar; conferir orientação, desktop e funcionamento de Sair do VR.
7. Conferir mãos sem controles e a faixa de botões em diferentes alturas.
