# Comparar e Quiz no monitor, contexto do ditado — 30/09/2026

## Escopo aprovado para publicação na CX33

O pedido é manter as atividades dentro do monitor da Sala de Estudos, sem sair
da imersão. Entrega **Comparar e Quiz** dentro da tela física. O usuário confirmou
que Estudo 3D, Clínica e Duelo devem continuar redirecionando e autorizou retirar
Arena VR do menu. Não confundir com uma incorporação completa de todas as páginas.

- Menu, pares saudável/patológico, escolha de órgão, giro, inclinação, zoom,
  controles simultâneos ou separados, restauração e notas paginadas ficam na tela.
- Estado local à sala, sem trocar URL ou encerrar a sessão XR ao comparar.
- Modelos e notas reutilizam o catálogo do Comparar. Fígado e rim têm ambos os
  assets. O coração patológico continua ausente: aviso explícito, sem inventar
  geometria substituta. Tamanhos normalizados, não apresentados como escala real.
- A rota `/compare` independente não foi alterada. Sala clássica preservada.
- Mouse, teclado e controles acionam as mesmas funções; registro acessível local.
- Estudo 3D, Clínica e Duelo abrem fora da sala, **somente após confirmação**.
  Antes saíam imediatamente no primeiro clique.

### Quiz incorporado

- Reutiliza `buildQuiz`, anotações válidas, 25 segundos por questão e histórico
  existentes. Não inventa perguntas ou pontos anatômicos. Sem anotações nomeadas,
  orienta a criá-las em Estudo 3D (com confirmação de saída).
- Seleção paginada de modelos; até 3/5/10 questões; tempo livre/cronometrado;
  órgão real, marcador amarelo, giro/inclinação/zoom; feedback, resultado,
  revisão paginada integral e repetição dentro do monitor.
- Redutor atômico por ID da questão impede resposta duplicada e eventos antigos.
  Tempo/alternativas aguardam o modelo e pausam com aba ou sessão XR ocultas.
  Fechar a atividade pelo Menu encerra a tentativa; histórico só salva ao concluir.
- Miologia não é oferecida no monitor por sua restrição no Quest. Outros modelos
  pesados, especialmente crânio, ainda exigem avaliação física. Nenhum órgão
  recebe redução de geometria. Modelos ausentes/falhos não geram substituto fictício.
- Quiz é local: usa notas deste navegador/origem, não transfere as da Vercel
  automaticamente. Notas/resultados de teste foram criados apenas em localhost.
- `/quiz` continua independente e a sala clássica mantém sua navegação original;
  Arena VR também foi retirada do menu clássico, sem remover a rota legada.

## Renderização e segurança XR

Dois render targets no Comparar, um no Quiz: 640 × 320, RGBA8, sem mipmaps,
sombras ou pós-processamento.
Somente o renderizador já existente na sala é usado; não há captura de HTML ou
outro contexto WebGL. Os órgãos são renderizados novamente somente ao carregar,
girar, aproximar ou restaurar o contexto gráfico. Não há animação contínua.
O framebuffer e os flags XR são restaurados no `finally`; a câmera do headset
não é movimentada. GLBs mantêm geometria/material originais, sem simplificação.
Clones não descartam materiais/geometrias do cache compartilhado.

Isso limita trabalho redundante; **não é medição de FPS no Quest**. Carga inicial,
decodificação e memória dos modelos continuam existindo. Não certificar desempenho
sem teste físico, principalmente com o rim patológico (aproximadamente 4,83 MB).

## Transcrição

A mesma API e o mesmo `gpt-4o-mini-transcribe` agora recebem um prompt em pt-BR
com orientação de transcrição literal e vocabulário anatômico do órgão selecionado.
O navegador envia somente o identificador público do catálogo; o servidor monta
o contexto por allowlist. Texto/prompt arbitrário vindo do cliente não é incorporado.
Na sala, sem órgão selecionado, usa contexto genérico de estudo anatômico.

Trocar de órgão cancela gravação/transcrição pendente para não inserir texto do
contexto antigo. Mantidos limite de áudio, limites por IP/instância, prazo, bloqueio
de origem externa, liberação do microfone e revisão explícita antes de enviar.
Não foram alteradas as permissões do Quest nem o cancelamento quando a sessão fica
oculta. Sem gravação do usuário ou dados pessoais nos testes.

Fonte técnica: [OpenAI — contexto de transcrição](https://developers.openai.com/api/docs/guides/speech-to-text#prompting).
O modelo atual tem remoção anunciada para 26/02/2027; migração não incluída nesta
etapa e deve ser planejada separadamente com comparação de custo/qualidade.

## Evidência

- `typecheck`, `lint`, `build`, `verify:core`: passaram.
- `verify:sala-estudos`: geometria anterior preservada; 180 alvos do menu,
  234 raios do Comparar e 216 do Quiz, ambas as mãos/alturas/cantos, sem obstrução da
  carcaça; limites de zoom/inclinação e restauração XR testados.
- `verify:transcricao`: 17 testes com adaptadores sintéticos, incluindo contexto
  permitido, descarte de entrada arbitrária e troca de órgão durante transcrição.
- `verify:duelo-http -- http://127.0.0.1:3003`: dois clientes HTTP/SSE passaram
  no build local de produção. Não modificadas regras de jogo ou salas online.
- Navegador: comparação dentro do monitor, modelos do fígado e do rim, giro/zoom,
  notas paginadas, ausência do coração patológico e confirmação de saída verificados.
  URL continua em `/sala`; comparação clássica permanece disponível.
- Quiz no navegador: duas anotações sintéticas criadas pelo visualizador normal;
  acerto via teclado, erro via mouse na tela 3D, troca de questão, resultado 1/2,
  revisão e timeout de 25 segundos confirmados sem sair de `/sala`. Console sem erros.
- `verificar-quiz-monitor.ts` integrado a `verify:sala-estudos`/`verify:core`:
  geração existente, dois controles simultâneos, clique/timeout concorrentes,
  evento antigo, resultado, repetição, páginas longas e orientação do marcador.
- API real no build local: HTTP 200 para frase sintética gerada com voz pt-BR
  do Windows: “Onde fica a epiglote? Qual é a função da cartilagem tireóidea?”.
  Retornou a frase, mas “tireoidea” sem acento. Não é avaliação de precisão com
  fala humana, ruído de estande ou microfone do Quest, nem comparação A/B.

Pendentes: teste com fala real/exemplos do usuário, primeira permissão no headset,
leitura/precisão da mira sentado e estabilidade/FPS no Quest. Publicação autorizada
por commit na master e imagem candidata na CX33; consultar a tag ativa e a revisão
da imagem para confirmar qual versão está servida. Preservar retorno à imagem anterior.
