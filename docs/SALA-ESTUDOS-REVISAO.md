# Sala de estudos — biblioteca e monitor integrado

## Preservação

A sala anterior (cadeira, rádio, livro e hub flutuante) está preservada no commit
`0c97726` e na branch `backup/sala-estudos-20260930`. Os GLBs originais não foram
sobrescritos. O botão **Ver sala clássica**, fora do VR, permite comparar; a URL
`/sala?versao=classica` também carrega a versão anterior. A cadeira, a altura do
tampo de 76,5 cm e a origem do assento em `[0, 0, -1.15]` permanecem iguais.

## Nova versão

- Biblioteca contemporânea: estantes integradas, marcenaria sálvia/carvalho,
  encadernações com capas, miolos e lombadas curvas, gaveteiro, luminária,
  janela com persiana, tapete, banco ao fundo e planta com folhas modeladas.
- Letreiro físico no painel acústico; nada de texto de cenário sobreposto.
- Monitor autoral com base, moldura, carcassa e ventilação; área útil de
  1,04 × 0,57 m. Menu de seis modos **dentro da tela**, com profundidade real.
- Alvos contínuos de 45,8 × 10,4 cm, sem escala/posição animada durante a mira,
  resposta no início do gatilho, hover independente das duas mãos e háptica.
- Navegação encerra a sessão XR antes de mudar de rota e avisa na própria tela.
- Links equivalentes acessíveis por Tab no desktop. Livro/tutor, rádio/Spotify,
  flashcards, saída do VR e recentralização continuam funcionando.
- Sem captura de HTML no monitor, sem pós-processamento, luz dinâmica adicional
  ou animação por quadro no menu. DPR 1 em XR mantido.

## Autoria e custo geométrico

Gerador: `scripts/criar-sala-estudos-revisao.py`, executado pelo Blender MCP em
cena independente; restaura a cena original no `finally`. Texturas e funções de
encadernação reutilizam autoria da Escola. O script de texturas gera o atlas
local; não usa CDN nem novos assets de terceiros. A fonte do letreiro usa Segoe
UI Bold instalada no Windows, convertida em contorno geométrico, sem distribuir
o arquivo de fonte. Os props licenciados originais mantêm os créditos existentes.

- Ambiente: 49.416 triângulos / 13 malhas / aproximadamente 4,22 MB.
- Monitor: 4.136 triângulos / 3 malhas / aproximadamente 0,37 MB.
- Esses valores são **somente dos dois assets novos**, não de toda a cena.
- Materiais opacos, mapas incorporados, UVs com nome único, normais verificadas.
- Oclusão estática por cor de vértice. Nenhum shadow map em runtime.
- GLBs sem Draco nesta revisão; preserva exportação simples e testável, sem
  acrescentar custo de decodificação. Órgãos anatômicos não foram alterados.
- Arquivo de autoria local: `tmp_sala_estudos/sala-estudos-revisao.blend`
  (ignorado pelo Git; o gerador e os GLBs finais estão versionados).

## Verificação

`npm run verify:sala-estudos` faz leitura real dos GLBs, testa normais, UVs,
orçamento de geometria, espaço do aluno, altura do tampo, limites da tela,
216 interseções com os raios do sistema XR (duas mãos, alturas e cantos), visão
sentada/em pé e bloqueio de interação pelo verso. Faz parte de `verify:core`.

No navegador local: abertura do menu na tela, navegação para Estudo 3D, livro
abrindo tutor com ditado, troca para a sala clássica e links por Tab verificados.
Inspecionados desktop paisagem e retrato. Typecheck, lint, build de produção e
verify:core passaram; HTTP/SSE com dois jogadores também passou no build local.
No build final, console sem erros; aviso preexistente de depreciação de THREE.Clock.
O aviso transitório de dependências do hook durante hot reload não se reproduziu
na abertura limpa do build final. Publicação remota é verificada após a promoção.

## Pendências de hardware

Não houve acesso a Quest físico. Validar leitura sentado, alcance do gatilho nas
seis opções, ambas as mãos, recentralização Y/B, ditado após permissão do microfone,
saída/reentrada de VR e fluidez. Os testes geométricos não certificam FPS, latência
de entrada nem conforto. A hospedagem na CX33 não transfere a renderização do
3D do headset para o servidor.
