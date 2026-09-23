# Escola de medicina — Duelo

## Resultado e escopo

Incremento de 23/09/2026 sobre `fbbd0b3`: transformar a Escola em sala de aula
de anatomia, mantendo as regras e a Arena médica já existentes. Runtime continua
Next.js/React Three Fiber/WebXR. Nenhuma dependência nova, CDN ou alteração nos
endpoints/regras das salas online.

### Ambientação

- Sala autoral produzida pelo Blender MCP, com materiais de madeira, giz,
  metal, tecido e marfim; superfícies chanfradas e silhuetas legíveis.
- Bancada de demonstração com luminária, aro luminoso e gavetas; o órgão ativo
  continua livre à esquerda da lousa. No menu há um coração do acervo.
- Lousa física enquadra placar, alternativas, resultado e progresso. Faixas
  da bancada, vitrine e janela acompanham acerto, erro, tempo e resultado.
- Vitrine de osteologia, dois microscópios, biblioteca de atlas, carteiras,
  cadernos, janelas, luminárias e porta dão contexto de aula de medicina.
- Iluminação quente/neutra principal, preenchimento hemisférico e recorte
  reativo suave; sem sombras dinâmicas nem pós-processamento adicional.
- Enquadramento desktop mais aberto; visão vertical preserva a lousa e coloca
  o órgão acima dela durante a rodada. Origem e câmera XR não são animadas.

### Esqueleto e integridade anatômica

O arquivo de artrologia existente contém malhas de ossos e dentes aproveitáveis.
A variante seleciona essas camadas, sem decimar, e conserva 158.090 triângulos.
O original permanece intacto. Materiais de apresentação de osso/dente têm
roughness diferenciada, sem inventar detalhes anatômicos.

O padrão é uma prancha renderizada no Blender a partir dessas mesmas malhas.
O jogador pode escolher **Ver esqueleto 3D**, na cena ou no botão acessível do
desktop. O GLB detalhado não é pré-carregado; só monta no menu ou no final.
Ao começar a partida, a vitrine volta à prancha para priorizar o órgão avaliado.
O recurso não é um novo modo de identificação de ossos; é uma exposição de apoio.

### Controles

`BotaoLousa` agora é uma apresentação do `Button3D` compartilhado, não uma
implementação concorrente de eventos. Herda acionamento no início do gatilho,
proteção contra clique duplicado/soltura em outra opção, hitbox sem crescimento
no hover, prioridade sobre cenário/órgão e háptica no controle de origem.

Alternativas: 1,10 m de largura × 0,094 m de altura, passo vertical 0,115 m;
há intervalo neutro entre alvos. Tamanho do texto considera rótulos longos sem
aumentar o alvo. A vitrine possui comando lateral, acima do piso, fora da lousa.
Props e malhas decorativas não recebem raycast. Mouse e atalhos foram mantidos.

## Orçamento dos assets

| Asset | Malhas | Triângulos | Bytes |
| --- | ---: | ---: | ---: |
| escola-medicina.glb | 10 | 19.043 | 1.361.416 |
| esqueleto-estudo.glb, opcional | 3 | 158.090 | 447.592 |
| esqueleto-prancha.png, 512 × 1.024 | plano em runtime | 2 | 652.819 |

São medidas dos arquivos, não FPS nem custo total da cena. Órgãos, personagem,
interface e efeitos acrescentam trabalho ao renderer. O esqueleto usa Draco;
a sala não necessita decodificação Draco. Unidades da sala em metros, piso em
y = −1,30 no runtime. XR permanece com DPR 1. Não há LOD anatômico automático.

## Verificações

Resultado final: typecheck, lint, todos os seis verificadores e build aprovados.
Console do navegador de desenvolvimento e do build final sem erros nas sessões
inspecionadas. Houve uma nova rodada completa de verificações após os ajustes
de tipografia e posição do comando da vitrine.

- `npm run typecheck`, `npm run lint`, `npm run build`.
- `npm run verify:core`: XR, salas online, áudio, apresentação, botões XR e o
  novo `verify:escola`.
- `verify:escola` usa a biblioteca real de ponteiros instalada com dois raios
  independentes: centros/bordas A–D, intervalos, gatilho de 700 ms, deslocamento
  antes da soltura, bloqueios, fonte háptica e orçamento dos assets.
- Navegador desktop: menu, contagem, rodada, acerto por mouse, resposta por
  teclado, combo, erro/bloqueio, revelação, troca de cérebro/laringe/coração/
  sistema digestório e tela final. Sem órgão anterior remanescente observado.
- Vitrine: GLB carregado, troca pelo botão 3D, prancha durante rodada e retorno
  à versão solicitada no final. GLBs servidos localmente, sem CDN.
- Build de produção: carregamento de Escola/Hospital, teclado online digitando
  `12`, apagando para `1` e voltando ao menu. Sem abrir sala pública de teste.
- Revisão de enquadramento em 1.144 × 910, 1.280 × 720 e tela vertical 390 × 844.
  A revisão vertical motivou um limite conservador para fontes longas.

Capturas em `docs/evidencias-escola/`: menu, acerto, sequência, erro do jogador,
revelação, bancada de microscopia, tela vertical e final. Algumas foram feitas antes do último ajuste da posição do
comando da vitrine; `menu-esqueleto-3d.png` e `final.png` mostram a posição revista.

## Limitações e teste no Quest

- Não houve acesso a um Quest físico nesta etapa. Os testes geométricos não
  equivalem a tracking real, conforto, precisão com tremor ou FPS do headset.
- Testar sentado/em pé, controle esquerdo/direito e alternância entre ambos;
  mirar cada borda A–D e segurar o gatilho antes de soltar sobre outro botão.
- Testar prancha e esqueleto detalhado no menu, início/fim de partida e oito
  rodadas seguidas; comparar estabilidade. Manter a prancha como padrão.
- Confirmar texto vertical longo e oclusão ao se aproximar da lousa no XR.
- O teste online automatizado cobre arbitragem; não houve partida com dois
  headsets nesta revisão. Sons foram validados por teste, não por escuta humana.
- Avisos existentes do loader de materiais legados e de `THREE.Clock` não foram
  tratados como falhas introduzidas por este cenário. Não se promete ganho de FPS.
- A licença original do acervo anatômico não é redefinida pela variante.

## Arquivos e reprodução

- Runtime: `components/duelo/AmbienteEscola.tsx`, `BotaoLousa.tsx`, `DueloApp.tsx`,
  `DueloGame.tsx`, `components/arena/ui3d.tsx`, `lib/escola-apresentacao.ts`.
- Teste: `scripts/verificar-escola.ts`, integrado ao `verify:core` em `package.json`.
- Blender: `scripts/criar-escola-medicina.py` e `scripts/preparar-esqueleto-escola.py`.
  Executar no Blender com `__file__` apontando ao caminho do script no projeto.
  Cada script usa uma cena separada e restaura a cena ativa no bloco `finally`;
  não salva nem sobrescreve o arquivo `.blend` do usuário.
- Assets: os três arquivos da tabela em `public/models/props/`; proveniência em
  `public/models/props/CREDITS.md`. Cenário e anatomia originais preservados.
