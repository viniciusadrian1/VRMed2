# Auditoria geral da plataforma VRmed — 2026-09-03

## Resumo executivo

Varredura da plataforma inteira (landing/tour, Estudo 3D, Sala, Duelo, Arena, Quiz,
Clínica, Comparar, Histórico, Admin, APIs, privacidade) por 13 auditores com lentes
diferentes, seguida de um juiz por achado e de um refutador adversarial. Foram
levantados **109 achados únicos**; **29 foram corrigidos e commitados** nesta rodada
(27 commits, um por assunto). O tema mais forte foi **honestidade da vitrine**: a
landing prometia coisas que o produto não faz (fontes tipo PubMed/NEJM, revisão de
cada resposta por especialistas, par patológico para os 6 órgãos) — o que um avaliador
da FIAP desmente em um clique. O segundo tema foi **acessibilidade e robustez** (quiz e
duelo injogáveis por teclado, erros do tutor virando "resposta" no histórico, overlay de
carregamento travando o catálogo).

## Método

- **13 lentes em paralelo:** landing/tour, viewer, tutor, sala, duelo, arena/quiz,
  clínica (UI), comparar/histórico/admin, acessibilidade, performance, segurança/código,
  mobile/PWA, consistência de texto.
- **Juiz por achado:** confirma no código se o problema é real, se vale o esforço e se é
  seguro aplicar sem headset e sem decisão de produto.
- **Refutador adversarial:** tenta derrubar cada candidato à execução (procura o problema
  não existir, a correção quebrar outra coisa, contrariar decisão documentada, precisar de
  headset). Um achado só entrou na fila com o refutador confirmando.
- **Execução em 2 lotes,** um agente por correção, sequencial, com verificação `tsc` +
  `eslint` + `curl` e um commit por item.
- **Nota honesta:** o limite de uso do modelo Fable interrompeu a refutação de 47 achados
  e a síntese automática. A rodada foi retomada em outro modelo; por isso a execução ficou
  restrita ao subconjunto com melhor relação valor/risco/confiança, e os 47 sem refutação
  adversarial não foram aplicados.

## O que foi corrigido (29 correções)

### Vitrine e textos (landing, SEO, comparar)
- Fontes do tutor na landing, no mockup, no FeatureShowcase e no README alinhadas ao prompt
  real: os 6 tratados da graduação (Moore, Gray, Netter, Sobotta, Guyton, Robbins), sem
  sites. `869620f`
- Comparar deixa de rotular um modelo procedural como "Hipertrofia ventricular"/"Enfisema":
  marca o par patológico ausente como demonstração e a landing passa a dizer "3 com par
  patológico" (bate com o catálogo). `0123289`
- "Respostas avaliadas por especialistas" corrigido para o tempo verbal certo (só o que
  recebe 👍/👎 é revisado depois). `ba5b722`
- Aviso de uso educacional ("não substitui laudo") no rodapé da landing. `c2a49bc`
- Botão "Sobre o projeto" da barra superior corrigido (apontava para uma âncora inexistente). `f12a60f`
- Títulos de /sala e /duelo deixam de sair como "… · VRmed · VRmed". `9890bd6`
- URL canônica, Open Graph e sitemap com o domínio real em vez de um placeholder da Vercel. `8cb6058`
- Caminhos de navegação para Sala, Duelo, Clínica e Arena a partir da landing. `ef6928b`
- A cena 3D da landing deixa de renderizar sem parar quando sai da tela. `4f218a2`

### Privacidade / LGPD
- Política ganhou data, seção de serviços de terceiros (OpenAI nos EUA, Umami, tokens do
  Spotify no navegador) e link a partir da Sala; removida a afirmação falsa de que as
  conversas "nunca são enviadas a servidores". Contato ficou marcado como decisão do grupo
  (sem inventar e-mail). `7570458`

### Tutor de IA
- Erro do tutor não vira mais um turno "assistant" no histórico (não ganha botão de
  feedback nem é reenviado ao modelo); mensagens de erro unificadas, com log no servidor e
  botão "Tentar novamente"; histórico cortado no cliente para nunca estourar o limite de 40
  mensagens (o /viewer travava em erro para sempre depois de um chat longo). `c19ebd0`
- Gaveta do tutor na Sala preserva quebras de linha. `887a806`

### Estudo 3D (viewer)
- As 6 regiões ganharam descrição de verdade (antes mostravam um caminho de arquivo de
  desenvolvedor); texto de narração ausente ajustado. `5056baf`
- Overlay "Carregando modelo 3D…" não bloqueia mais o catálogo: a fonte de luz virou um
  mapa local, sem HDR de CDN. `462b421`
- Destaque azul de estrutura deixa de ficar preso ao limpar e passa a acompanhar o clique
  e os pontos numerados. `3ab6237`
- Narração não morre mais ao trocar de aba no painel de ferramentas. `76afc81`
- Corrigido o aviso de hidratação do botão de tema. `cc3e901`

### Quiz e Duelo
- Quiz ignora anotações com o texto padrão "Nova anotação" (que virava resposta correta). `a2bc557`
- Quiz mantém o foco do teclado depois de responder. `d70abd1`
- Duelo: a alternativa errada fica eliminada e travada em vez de continuar clicável. `563c87b`
- Duelo jogável por teclado e com nome acessível no canvas. `21706b2`

### Sala de Estudos
- Tutor 2D abre por teclado/celular, não só clicando no livro 3D. `414dcba`
- Hub do computador lista todos os modos (inclui Duelo e Comparar). `efd0dde`
- Cartas geradas por IA ficam distinguíveis da base curada. `3c7c7cf`
- Cada objeto tem seu próprio carregamento, então a sala não some inteira enquanto os GLBs
  baixam. `b3f0240`

### VR e API
- Glifos fora da fonte local (♪, →) removidos dos textos 3D — evitavam desenho e disparavam
  busca em CDN sem rede. `4c5b693`
- /api/feedback ganhou limite de frequência e passou a ignorar o horário enviado pelo
  cliente. `a66e32d`

## Recomendado, mas precisa de você

Achados reais e valiosos que **não** apliquei sozinho porque exigem teste no headset ou uma
decisão do grupo:

- **Bloquear modelos pesados no "Entrar em VR" (#14).** Hoje nada impede abrir Miologia
  (982 mil triângulos, proibido em VR) e outros modelos acima do teto de 150k. A correção é
  segura, mas grava a contagem de triângulos dos 18 modelos no catálogo — quero conferir cada
  número no headset antes. Alto valor.
- **Rótulo da estrutura clicada em VR (#13).** No Estudo 3D dentro do headset o nome não
  aparece (o texto vive no DOM, invisível em VR). A correção é simples, mas a posição do
  texto 3D precisa ser afinada no Quest.
- **Persistência do feedback da pesquisa (#28).** `feedback.jsonl` vive no disco efêmero do
  Render: cada deploy apaga as avaliações da Iniciação Científica. Precisa de um disco
  persistente (ou banco) — decisão de infra/custo do grupo.
- **Unificar a store de XR (#20).** Estudo 3D e Arena criam a store de VR à mão em vez de
  usar `obterXrStore()`; migrar é mecânico, mas quero um teste rápido no headset.
- **Limite de custo no /api/chat (#27) e botão "Entrar em VR" em aparelho sem VR (#38).**
  São problemas reais (qualquer script gasta a cota da OpenAI; o botão aparece e falha com
  erro cru em celular), mas os planos propostos tinham furos — precisam de um desenho melhor.

## Backlog aprovado, ainda não aplicado

Sobraram **69 achados** julgados reais, válidos e seguros que não entraram nesta rodada,
para manter o lote controlável. **47 deles não passaram pela refutação adversarial** (o
limite de uso interrompeu essa etapa), então merecem uma segunda olhada antes de aplicar.
Distribuição por área: Duelo 8, Arena/Quiz 8, Clínica 8, Comparar/Histórico/Admin 7,
Estudo 3D 6, acessibilidade 6, performance 5, segurança 5, mobile/PWA 5, tutor 4, Sala 3,
consistência de texto 3, landing 1. Posso rodar um terceiro lote quando você quiser.

## Descartados (falsos positivos / planos refutados)

- **#55** "grafia pré-Acordo Ortográfico" — o diagnóstico estava errado; "tireóidea" está correta.
- **#23 / #75** DoubleSide nos materiais — real, mas o ganho medido é nulo; não vale o risco.
- **#109** slugs de rota em inglês vs português — cosmético, com risco de quebrar links/SEO.
- **#27, #38, #30, #62** — problemas reais, mas os planos propostos foram refutados (ver seção acima).

## Limites desta auditoria

- Nada foi testado em headset; toda mudança de posição/escala em VR ficou de fora.
- Não rodei build de produção (o servidor de desenvolvimento estava em uso); a verificação
  foi `tsc` + `eslint` + `curl` nas rotas (todas respondendo, admin em 401 por design).
- O `eslint` acusa 9 erros do React Compiler (`Date.now` em handler, set-state em efeito,
  ref lido no render) em arquivos tocados — todos **preexistentes**, confirmados idênticos no
  commit anterior à auditoria; não foram introduzidos aqui e não foram consertados.
- 47 dos achados não aplicados não têm verificação adversarial por causa do limite de uso.
