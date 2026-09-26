# Escola — revisão aprovada e promoção

## Promoção autorizada em 26/09/2026

O usuário aprovou visualmente esta revisão e autorizou substituir a Escola atual
e publicar no GitHub/Vercel para teste no Quest. A promoção usa exatamente os
dois GLBs aprovados na cópia, conferidos por SHA-256:

- `escola-medicina-revisao.glb`: `bdc05360a2c1ab8f9d41c2071bb603bc668dae486520e5ef16ddd4a1e4704ba7`.
- `piso-escola-revisao.glb`: `56c96b975c43f547c6a115f6cbbc3c588e50832e44d4a7ef950f861def7dc470`.

`AmbienteEscola` monta a revisão por padrão; `revisao={false}` preserva acesso à
implementação anterior. Seus GLBs permanecem intactos, mas não são pré-carregados.
O piso antigo não é sobreposto ao novo. `DueloApp` não recebe o comparador nem a
troca de ambiente inicial da prévia. A Arena publicada permanece inalterada.

O teste `verify:escola-revisao` passa a fazer parte de `verify:core` e exige a
revisão como padrão, os assets anteriores preservados e ausência do comparador.
Validação concluída no projeto principal em 26/09/2026:

- `npm run typecheck`, `npm run lint`, `npm run verify:core` e `npm run build`: passaram.
- `npm run verify:duelo-http -- http://127.0.0.1:3004`: passou no build de produção,
  com dois clientes, HTTP/SSE, placar compartilhado e rejeição de protocolo antigo/adulteração.
- `/duelo` e os dois GLBs: HTTP 200 no servidor local de produção; hashes dos
  downloads idênticos aos arquivos aprovados. `git diff --check` passou.
- `DueloApp`, Arena, regras e assets antigos sem diferenças em relação a `c2206af`.
- Nenhuma dependência nova, segredo ou arquivo de ambiente incluído.

O envio à `master` aciona a publicação pela integração existente da Vercel. O
resultado do deploy deve ser confirmado no status do commit e no endereço público,
não inferido do build local. Teste físico no Quest permanece pendente. A seção
abaixo registra a etapa isolada, não o estado atual de aprovação.

## Histórico da cópia isolada e preservação

Criada após a aprovação/publicação da nova Arena Médica. O usuário pediu o mesmo
processo para a Escola: preservar a versão atual, trabalhar em cópia, mostrar e
só substituir depois de aprovação. Durante essa etapa, a proposta ainda não
havia sido publicada nem commitada.

- Projeto principal: `C:\Users\vinic\Downloads\InnerVision\vrmed`, limpo após
  o commit `c2206af` da Arena. A Escola publicada não foi modificada nesta etapa.
- Cópia de trabalho: `C:\Users\vinic\Downloads\InnerVision\vrmed-escola-revisao`,
  worktree isolado iniciado no mesmo commit. Sem cópia de `.env` ou credenciais.
- Prévia: `http://127.0.0.1:3003/duelo`. O botão **Escola: revisão experimental**
  alterna com **Escola: versão atual**, mantendo enquadramento e partida.
- O comparador só aparece fora da sessão XR; o ambiente escolhido acompanha a
  sessão. HTTP local não é uma publicação remota segura para o Quest.
- Os GLBs anteriores de Escola, piso e esqueleto foram comparados por SHA-256
  com a base e permanecem idênticos. Regras, botões e Arena também têm o mesmo
  conteúdo; diferenças de LF/CRLF do checkout não são alterações de código.

## Direção e alterações

Marcenaria acadêmica em carvalho, verde profundo, cerâmica e pequenos detalhes
metálicos. O objetivo é unidade construtiva com objetos reconhecíveis de perto,
sem transformar a Escola em outro hospital nem acrescentar anatomia fictícia.

- Biblioteca frontal e posterior com painéis rebaixados, folgas de portas,
  encaixes, puxadores com retorno, rodapé recuado e prateleiras com espessura.
- Livros com lombadas curvas impressas, capas separadas, miolo com textura de
  folhas, cabeceado, fita de marcação e aparadores. Títulos do acervo são autorais;
  não reproduzem capas ou identidade de editoras comerciais.
- Caderno aberto com páginas abauladas e roteiro de estudo, além de dois volumes
  apoiados na bancada. O painel posterior traz fichas impressas de observação.
- Microscópios com carcaça contínua, oculares, platina, trilhos, objetivas,
  condensador, controles concêntricos serrilhados, pés de apoio e cabos.
  São modelos cenográficos, não simulação óptica ou equipamento clínico validado.
- Bancada de microscopia da mesma família de armários, com tampo cerâmico,
  espelho técnico, tomadas e sinalização preservada.
- Lambris emoldurados, caixilhos e peitoris, forro com encaixes e luminárias
  lineares suspensas, porta com batentes e acabamento da vitrine osteológica.
- Materiais PBR locais, madeira com microacabamento, piso com contatos gravados
  e preenchimento emissivo discreto do forro. Sem luz dinâmica nova, sombras
  dinâmicas, pós-processamento, vidro transparente ou dependência externa.

68 elementos centrais foram comparados por vértices antes/depois da autoria:
lousa, palco, postos, mesas e seus detalhes não mudaram de geometria ou posição.
Acervo anatômico, prancha leve e esqueleto opcional fora das rodadas preservados.
O centro e as alternativas continuam com o funcionamento aprovado.

## Autoria e orçamento

Modelagem via Blender MCP, em cenas separadas; a cena original `Scene` com três
objetos foi restaurada após as exportações. Scripts reprodutíveis:

1. `python scripts/texturas-escola-revisao.py` gera texturas locais com Pillow,
   fontTools e Inter já existente no projeto.
2. `scripts/criar-escola-revisao.py` é executado no Blender com `__file__` correto.
   Reutiliza apenas as funções de autoria/exportação necessárias, sem exportar
   sobre os cenários antigos. A cena editável fica em
   `tmp_escola_revisao/escola-revisao.blend` (pasta ignorada pelo Git).

| Asset | Triângulos | Malhas | Bytes |
| --- | ---: | ---: | ---: |
| Escola atual | 38.366 | 11 | 3.072.104 |
| Escola proposta | 63.376 | 19 | 5.142.160 |
| Piso proposto | 2 | 1 | 105.416 |

781 objetos de autoria agrupados por material na exportação. Atlas de encadernação
2048², madeira 512², folhas 256², piso 512². Texturas incorporadas, sem CDN e sem
Draco nos props. Não há simplificação de órgãos ou do esqueleto.
O detalhamento aumenta geometria, materiais e download: não é uma otimização
presumida de desempenho. A amostra de desktop não substitui o Quest.

## Validação e correções

- Typecheck, lint, build e `verify:core`: passaram na cópia.
- `verify:escola-revisao`: passou nos arquivos finais. Valida orçamento, texturas
  locais, UVs, normais, limites da sala, volumes dos dois jogadores, corredor e
  24 pontos entre centro/bordas das alternativas com dois raios de controle.
- `verify:duelo-http -- http://127.0.0.1:3003`: passou com dois clientes locais,
  HTTP/SSE, placar compartilhado e rejeição de protocolo antigo/adulteração.
- Navegador: frente, microscopia e fundo inspecionados; início por mouse, resposta
  por mouse, erro e acerto por teclado observados, incluindo pontuação e feedback.
  Trocas coração → rim → cérebro sem permanência visual do órgão anterior.
- Corrigida a união de camadas `Mapa UV`/`UVMap` do Blender localizado, que
  deixava lombadas sem textura. Camadas agora têm nome e seleção consistentes.
- Corrigida orientação das normais de lombadas/páginas abertas; há regressão
  geométrica para a face externa e as coordenadas UV da encadernação.
- Durante geração houve um carregamento 404 do novo asset ainda inexistente.
  Após exportação e recarga, os modelos carregaram; os logs posteriores consultados
  não mostraram outra exceção. Não confundir esse episódio transitório com teste XR.

## Limites da inspeção inicial

Inspeção concluída na virada para 26/09/2026. Amostras locais aquecidas, menu com
coração, esqueleto detalhado desligado, viewport 1280 × 720 e DPR 1:

| Versão | FPS | p95 | Chamadas | Triângulos da cena |
| --- | ---: | ---: | ---: | ---: |
| Atual | 142 | 7,4 ms | 83 | 53.394 |
| Proposta | 144 | 7,1 ms | 91 | 78.404 |

São amostras breves observadas no medidor, não benchmark controlado nem média da
sessão. A pequena diferença de FPS não demonstra ganho; a proposta custa mais
geometria e chamadas. Carregamento frio e memória GPU não foram medidos.

Quest físico, conforto estéreo, legibilidade dos detalhes, estabilidade e custo de
carregamento ainda pendentes. O medidor existente descarta deltas superiores a
500 ms e não permite concluir que não há travadas longas. DPR em XR continua 1.
Nenhuma validação médica nova ou teste de hardware foi realizado.

A inspeção visual orientou o refinamento de textura, luz e material. A aprovação
estética foi recebida em 26/09/2026, conforme a seção de promoção. O comparador
permanece somente na cópia local e não acompanha a publicação.

## Arquivos da proposta

- Novos: `components/duelo/SalaEscolaRevisao.tsx`, dois GLBs de revisão,
  três scripts de autoria/teste e este relatório.
- Alterados apenas nesta cópia: `components/duelo/AmbienteEscola.tsx` (opção com
  padrão antigo), `components/duelo/DueloApp.tsx` (comparador), `package.json`
  (teste) e `docs/CONTEXTO.md` (registro da cópia).
- Imagens de inspeção em `tmp_escola_revisao/`, fora do Git.
