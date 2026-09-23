# Ferramentas e tutor dentro de AR/VR

Implementação inicial: 23/09/2026, publicada em `ddc9dd2` após autorização.
Revisão de identidade e manipulação: 23/09/2026. Commit local autorizado pelo usuário;
publicação não solicitada nesta revisão.

## O que mudou

O visualizador monta dois painéis de geometria 3D nas sessões `immersive-ar` e
`immersive-vr`. Não depende de DOM overlay, teclado do sistema ou microfone.
O órgão permanece no centro; ferramentas à esquerda e tutor à direita.

- **Camadas:** três itens por página, seleção, visibilidade, isolamento, raio-X,
  mostrar todas, barra de opacidade de 0–100% e cinco opções de cor (incluindo original).
- **Cortes:** planos axial, sagital e coronal, posição em passos de 0,1, inversão,
  remoção de cortes e wireframe. Modelos com abertura também oferecem abrir/fechar.
- **Notas:** marcar um ponto com o gatilho, editar texto pelo teclado, percorrer
  notas/textos, localizar o ponto, mostrar/ocultar o rótulo desktop e excluir com
  confirmação. O marcador XR mostra o número; o texto completo fica no painel.
  Para não atribuir posições a ossos deslocados, fechar o crânio antes de marcar/localizar.
- **Áudio:** descrição paginada, fontes, ouvir, pausar, retomar, parar e velocidade.
  Usa a mesma narração na tela e no headset. Se o navegador/arquivo não fornecer áudio,
  informa a indisponibilidade e mantém o texto.
- **Tutor:** histórico compartilhado, leitura paginada, perguntas rápidas,
  pergunta livre com teclado 3D (500 caracteres), guia 3D, limpar foco, parar resposta,
  tentar novamente e limpar conversa com confirmação. Não adiciona reconhecimento de voz.

As notas e a conversa continuam usando o armazenamento já existente. Não houve
nova dependência, asset essencial, mudança de credencial, modelo OpenAI ou endpoint.

## Espaço e interação

Painéis de 1,04 × 1,12 m; centros a ±0,95 m lateralmente e 1,12 m à frente,
inclinados em 0,55 rad. A altura acompanha a pose real dos olhos na entrada,
0,12 m abaixo deles, tanto sentado quanto em pé. Depois ficam **fixos no mundo**.

**B/Y** ou **Reposicionar painéis** restauram tamanho/posição e trazem a interface
à frente do olhar atual. Mantêm a escolha de quais janelas estão minimizadas.
Nenhuma dessas ações move a câmera ou o órgão. A/X continuam reposicionando o órgão.
O botão de sair permanece montado durante toda a vida da cena e é ancorado abaixo
dos painéis, junto ao reposicionamento; não disputa as abas quando o aluno se senta.

Botões de 6,5 cm de altura, fonte local e confirmação no aperto do gatilho
reutilizam a interação estável do Duelo. O escudo dos painéis intercepta seus vãos:
clicar entre botões não seleciona o órgão por trás. A pinça iniciada sobre interface
fica reservada à interface até soltar, sem arrastar simultaneamente o modelo.
Superfícies cortadas, invisíveis ou de opacidade zero são retiradas do raycast.

Cortes agora continuam ativos em AR/VR e acompanham posição/escala/rotação do órgão.
São recortes de superfície, **não** uma reconstrução de tecido interno ou um volume médico.

## Ciclo de vida

`tutor-conversa.ts` é o serviço compartilhado entre chat DOM e XR: um pedido por vez.
Cancelar/trocar de órgão remove placeholder vazio, preserva texto parcial e impede
respostas/comandos atrasados. Fechar só o chat DOM não interrompe o texto lido no XR;
minimizar o tutor 3D preserva a resposta em andamento. Parar resposta ou sair da página encerra-a.
Entrar/sair da sessão sem sair da página mantém histórico e reprodutor.

`narracao-estudo.ts` mantém um único áudio. Fechar/trocar a aba não o interrompe;
trocar de órgão ou sair da página encerra a narração. Parar também cancela o início
adiado de 80 ms, evitando que a voz comece depois do comando de parada.
A velocidade de Web Speech vale na próxima reprodução, como indicado no painel.

## Arquivos

- `components/viewer/PainelXRBase.tsx`: base, escudo, paginação e teclado.
- `components/viewer/PaineisEstudoXR.tsx`: pose, disposição e reposicionamento.
- `components/viewer/FerramentasPainelXR.tsx`: quatro abas imersivas.
- `components/viewer/TutorPainelVR.tsx`: conversa 3D.
- `components/viewer/Scene.tsx`, `OrganModel.tsx`, `XRManipulation.tsx`:
  montagem, cortes, marcação e compatibilidade com manipulação.
- `components/chat/ChatPanel.tsx`, `components/viewer/AudioNarration.tsx`:
  preservação da interface DOM com serviços compartilhados.
- `app/viewer/page.tsx`: preparação e encerramento da narração/conversa.
- `components/arena/ui3d.tsx`: glifos locais adicionais e identificação da pinça na UI.
- `lib/painel-estudo-xr.ts`, `tutor-conversa.ts`, `narracao-estudo.ts`,
  `xr-foco-interface.ts`: contratos, conversa, narração e bloqueio da pinça.
- `lib/model-utils.ts`, `tts.ts`, `tutor-3d.ts`: raycast visível e cancelamentos.
- `scripts/verificar-paineis-estudo-xr.ts`, `registrar-aliases-teste.mjs`,
  `package.json`: testes determinísticos integrados em `verify:core`.

## Validação e limites

- Resultado final local: `npm run typecheck`, `npm run lint`, `npm run build`,
  `npm run verify:core` (incluindo `verify:paineis-xr`) e `git diff --check`
  passaram. Os testes Node usam a versão 22 instalada e não acessam a OpenAI.
- Testes usam a biblioteca instalada de raios, duas origens de controle e ambos
  os painéis inclinados: centros, bordas, vãos, oclusão e gatilho de 700 ms.
- Cobrem paginação sem perda de texto comum, teclado com acentos, limites,
  camadas/cortes/notas na store, raycast das superfícies visíveis, pinça reservada
  à UI, conversa compartilhada, clique duplo, cancelamento, falhas, resposta antiga
  concorrendo com nova e cancelamento/retomada de narração.
- Voz, relógio e respostas HTTP são simulados nesses testes. Não comprovam a voz
  disponível no Quest, operação da OpenAI em produção ou conforto físico.
- O navegador automatizado falhou **antes de abrir a página**, com
  `windows sandbox failed: helper_unknown_error: apply deny-read ACLs`, inclusive
  após reinicializar a ferramenta. Nenhuma captura visual foi obtida neste incremento.
- **Inspeção visual, headset Quest, AR/passthrough e hand tracking físico pendentes.**
  Não há medição nova de FPS, latência ou draw calls. Mantidos DPR 1 em XR,
  ausência de sombras caras/pós-processamento e apenas três camadas por página.
  O teclado desenha mais botões só enquanto aberto; é preciso medir esse caso no Quest.
- Publicação autorizada para homologação no Quest; não representa aprovação física
  de legibilidade, conforto ou desempenho.

### Inspeção local

Com `npm run dev`, selecionar um modelo e usar:
`/viewer?inspecao=ferramentas`, `?inspecao=tutor` ou `?inspecao=paineis`.
Esse enquadramento é exclusivo de desenvolvimento, não emula WebXR e é ignorado
em produção e durante uma sessão real. No headset, os painéis abrem normalmente
ao entrar em AR/VR, sem parâmetro.

### Roteiro de homologação no Quest

1. Em HTTPS/localhost, carregar laringe e entrar em VR; repetir depois em AR.
2. Testar sentado/em pé e entrar olhando para outra direção. Conferir altura,
   faixa livre central, saída, recorte dos textos e ausência de salto de câmera.
3. Testar cada controle: raios esquerdo/direito, aperto lento, soltar sobre outro
   botão, vãos e teclas. Recolher/reabrir e usar B/Y após virar/caminhar.
4. Isolar uma camada, mudar opacidade/cor, testar raio-X e restaurar. Verificar
   sincronização com o DOM ao sair do XR.
5. Ligar/inverter/deslocar três cortes; pegar/girar/escalar o órgão. Selecionar
   partes expostas pelo corte e confirmar que a superfície removida não recebe o laser.
6. Criar/editar uma nota, localizar ponto, navegar entre notas e cancelar exclusão.
   Confirmar persistência ao voltar à tela. No crânio, fechar antes de marcar.
7. Ouvir/pausar/retomar/parar descrição; testar parar imediatamente e trocar de aba.
   Se não houver voz, conferir aviso e leitura do texto.
8. Perguntar algo pelo teclado, incluindo acentos; conferir a mesma conversa no
   DOM, paginação de resposta longa, foco sem movimento da câmera e erro sem conexão.
9. Parar resposta e iniciar outra; trocar órgão enquanto responde; sair da página.
   Não deve restar pedido preso, voz atrasada ou foco no órgão anterior.
10. Testar hand tracking: pinça nos botões não arrasta o modelo; soltar e pinçar
    fora da UI permite manipular novamente. Medir fluidez com teclado aberto.

## Revisão — identidade do site e janelas manipuláveis

Atende ao retorno do usuário após o primeiro teste no Quest. Não altera o Duelo,
modelos anatômicos, credenciais, chamadas da IA ou regras de sessão.

### Visual

- Mesmos tokens claro/escuro de `app/globals.css`, acompanhando o tema do site.
  Teste automático impede divergência dessas cores. Fonte Inter local, sem contorno.
- Ferramentas: cabeçalho, trilho de abas, cartões com borda, seleção, profundidade,
  isolamento e slider de opacidade por camada. Cores continuam em cinco opções.
- Tutor: cabeçalho, guia 3D, pergunta em balão azul à direita, resposta à esquerda,
  histórico, campo de pergunta e teclado. A pergunta longa acima da resposta é um
  resumo; o texto completo permanece acessível pelo histórico paginado.
- O layout é adaptado ao laser: três camadas por página, alvos maiores e leitura
  paginada. Não é um DOM capturado nem uma promessa de igualdade pixel a pixel.
  Cortes, notas, áudio e todas as ações anteriores continuam disponíveis.

### Controles

1. **Mover:** apontar para a barra superior, segurar o gatilho, deslocar o controle
   e soltar. A captura mantém o arraste mesmo saindo da barra; só o ponteiro que
   começou o gesto pode movê-la. Ao soltar, a janela se orienta para o usuário.
2. **Tamanho:** −/+ na barra inferior; escala limitada a 65–155%.
3. **Distância:** Mais perto / Mais longe, em passos de 15 cm.
4. **Minimizar:** − no cabeçalho. A janela vira uma faixa reabrível, preservando
   aba, rascunho, edição e resposta. Não desmonta o conteúdo.
5. **Reabrir:** faixa da janela ou botões fixos Ferramentas / Tutor de IA.
6. **Recuperar:** Restaurar na janela retorna só ela ao padrão; B/Y ou Reposicionar
   recuperam ambas à frente do olhar. Câmera e órgão nunca são movidos.

O centro da janela fica entre ±2,2 m na horizontal, −0,65/+0,75 m na vertical e
0,55–2,4 m à frente da âncora de entrada/recentragem. Pose e escala são independentes
por janela e reiniciam numa nova sessão, sem gravar coordenadas físicas em localStorage.
O dock de recuperação tem prioridade sobre as janelas mesmo quando sobreposto.

Ordem visual e de interação acompanham a janela ativa. Painéis minimizados não
interceptam raios nem mouse invisivelmente; vãos dos painéis abertos continuam
bloqueando o órgão atrás. Pausa/desconexão, perda de captura e reset liberam gestos.
Som e háptica de confirmação preservados. DPR 1 em XR e ausência de novas luzes,
sombras ou pós-processamento preservados.

### Arquivos desta revisão

- `EstiloPainelXR.tsx`, `ContextoJanelaXR.tsx`, `JanelaMovelXR.tsx`: primitivas
  de estudo, contexto por janela e manipulação; todos em `components/viewer/`.
- `PainelXRBase.tsx`, `PaineisEstudoXR.tsx`, `FerramentasPainelXR.tsx`,
  `TutorPainelVR.tsx`, `Scene.tsx`: integração sem alterar os componentes DOM.
- `lib/tema-paineis-xr.ts`, `lib/janelas-estudo-xr.ts`: tokens, estado e matemática.
- `scripts/verificar-janelas-estudo-xr.ts` e `package.json`: novos testes dentro
  de `verify:paineis-xr`, que já integra `verify:core`.

### Evidências e limites desta revisão

Validação final local: `npm run typecheck`, `npm run lint`, `npm run build`,
`npm run verify:core` (incluindo os dois scripts de painéis) e `git diff --check`
passaram. Nenhuma publicação foi executada nesta revisão.

Testes determinísticos usam o raio real da biblioteca instalada: pegada sem salto,
arraste capturado com origens esquerda/direita, pai rotacionado/deslocado/escalado,
soltura, opacidade, limites, sobreposição, ocultação, reabertura e tokens dos dois temas.
Testes dos serviços continuam com HTTP/voz simulados, sem chamadas OpenAI.

A skill Computer Use foi usada para tentar inspecionar o site, mas o navegador
falhou na inicialização (ACL do sandbox), inclusive após reset. Referências visuais:
print fornecido pelo usuário e componentes/tokens reais do site. **Sem nova captura
visual, medição de FPS/draw calls ou homologação física.** Isso não bloqueou a edição.

Antes de aprovar para evento: repetir o roteiro acima em VR e AR no Quest; arrastar
cada janela para ambos os lados, testar escala mínima/máxima, sobrepor e alternar foco,
minimizar durante edição/resposta, reabrir pelo dock e recuperar com B/Y após caminhar.
Testar desconexão/pausa no meio do gesto e verificar que soltar não aciona outro botão.
Comparar tema claro/escuro com o site e medir fluidez com o teclado aberto.
