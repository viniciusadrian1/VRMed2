# Arena Médica — revisão isolada para comparação

## Estado

Proposta implementada, inspecionada no navegador e aprovada visualmente pelo usuário. Em 25/09/2026, ele autorizou promover a revisão a cenário padrão e publicá-la no GitHub/Vercel para teste físico no Quest, que permanece pendente. Não é uma declaração de qualidade comercial concluída. Este relatório preserva o histórico da cópia experimental; a aplicação principal usa a revisão diretamente, sem comparador.

## Preservação

- Base: `C:\Users\vinic\Downloads\InnerVision\vrmed`; depois da aprovação, recebeu a revisão como padrão. O componente `AmbienteHospital` e seus assets continuam guardados, sem montagem simultânea.
- Revisão: `C:\Users\vinic\Downloads\InnerVision\vrmed-arena-revisao`, worktree separado, disponível na porta 3001.
- A revisão partiu do mesmo HEAD e recebeu uma cópia das 46 alterações locais da base; os arquivos copiados foram conferidos por SHA-256.
- Conferência posterior de 762 arquivos presentes na base: somente `components/duelo/DueloApp.tsx` e `package.json` diferem em conteúdo na cópia. Há 223 diferenças exclusivamente de LF/CRLF introduzidas pelo checkout do Git; não são mudanças de conteúdo. Os arquivos novos são adicionais.
- Escola, Arena original, modelos anatômicos, regras, pontuação e alvos das alternativas não foram substituídos. A cena original aberta no Blender foi restaurada após cada exportação.
- Não foram copiadas credenciais ou arquivos `.env`. O teste de tutor com API externa não faz parte desta revisão.

## Como comparar na cópia experimental

Abrir `http://127.0.0.1:3001/duelo`. O botão inferior **Arena: revisão experimental** alterna com **Arena: versão atual** na mesma aplicação. Não é um terceiro tema: são duas versões da Arena Médica. O seletor Escola continua mostrando a Escola existente.

A escolha acontece fora da sessão XR e é mantida ao entrar em VR. O endereço HTTP local é uma prévia desktop: não constitui uma publicação acessível pelo Quest. Um teste remoto em headset exige origem segura apropriada, sem desativar proteções do navegador.

## Direção implementada

- Arquitetura hospitalar com forro modular, luminárias embutidas, rodapé sanitário, protetores de parede, nichos e persiana.
- Família de bancadas, armários e prateleiras com espessuras, juntas, alças e portas coerentes; materiais branco quente, verde-petróleo e metal escovado.
- Carrinho com cinco gavetas separadas, perfis de puxada, rodízios duplos com freios, pega lateral, bandeja e instrumental cenográfico.
- Estação de exame com base moldada, braço articulado, ventilação, teclado, seletores, trackball e sonda com cabo e suporte. Não apresenta medidas clínicas inventadas.
- Leito com estrutura de elevação, grades, cabeceiras abertas, colchão, travesseiro, cobertura com caimento e espessura, cortina pregueada e cabeceira técnica.
- Apoio posterior e área de higienização seguem a mesma família de mobiliário. Cuba com interior e torneira modelada.
- Placas claras integradas às superfícies, títulos centralizados e fontes autoradas na proporção física para evitar deformação. Subtítulos dos letreiros principais removidos.
- O palco anatômico, console, iluminação reativa e interface aprovada são reutilizados. O monitor do leito acompanha o estado da partida.
- Materiais PBR com microacabamentos locais, reflexão estática limitada ao cenário e oclusão gravada. Sem novas luzes dinâmicas, transparência de vidro, sombras dinâmicas ou pós-processamento.

## Arquivos desta revisão

Novos:

- `components/duelo/ArenaMedicaRevisao.tsx`
- `scripts/criar-arena-revisao.py`
- `scripts/texturas-arena-revisao.py`
- `scripts/verificar-arena-revisao.ts`
- `public/models/props/arena-medica-revisao.glb`
- `public/models/props/piso-arena-revisao.glb`
- Este relatório.

Alterados somente na cópia: `components/duelo/DueloApp.tsx` (comparador) e `package.json` (comando de teste). Nenhuma dependência nova ou mudança de lockfile.

Os muitos outros arquivos modificados apontados por `git status` são a base local anterior copiada, não devem ser confundidos com a autoria desta revisão.

## Autoria e orçamento

O gerador de texturas usa Pillow/fontTools disponíveis no Python local e a fonte Inter já incluída no projeto. O gerador 3D foi executado pelo Blender MCP, em cena separada, reutilizando funções de geometria e acabamento existentes. `tmp_revisao/arena-revisao.blend` mantém uma cena editável; os scripts e texturas permitem regeneração. Essa pasta é ignorada pelo Git.

| Asset | Triângulos | Malhas | Bytes |
| --- | ---: | ---: | ---: |
| Arena revisada | 94.040 | 13 | 7.995.460 |
| Piso revisado | 2 | 1 | 84.408 |

São 602 objetos de autoria agrupados por material para exportação, não 602 objetos desenhados individualmente em runtime. Atlas de inscrições 2048 × 1024; mapas de microacabamento 256 × 256; piso 512 × 512. Imagens incorporadas ao GLB, sem CDN. Geometria não usa Draco nesta proposta. Não houve simplificação anatômica.

O tamanho de download aumentou em relação aos principais GLBs de cenário anteriores. A arquitetura e os props estão agrupados em uma malha por material, o que limita as chamadas, mas reduz a granularidade do descarte por visibilidade. É um compromisso a medir no headset, não uma otimização presumida.

## Validação realizada

Na promoção ao projeto principal, typecheck, lint, build e `verify:core` foram
executados novamente e passaram. O teste HTTP/SSE também passou contra o build
de produção local (`next start`, porta 3002), não apenas contra o desenvolvimento.
Os dois GLBs copiados tiveram SHA-256 conferido; componentes e assets principais
da Escola foram comparados à versão aprovada e permanecem idênticos.
Quest físico ainda não foi testado; publicar não equivale a validar o headset.

- `npm run typecheck`: passou.
- `npm run lint`: passou.
- `npm run build`: passou.
- `npm run verify:core`: passou, incluindo XR, Duelo, áudio, apresentação, controles, Escola, retaguarda, tutor, perguntas, tipografia, sinalização, acabamento e painéis XR.
- `npm run verify:arena-revisao`: passou com os assets finais. Valida normais, UVs, imagens locais, materiais opacos, limites espaciais, corredor livre, orçamento e 24 alvos entre centro/bordas das quatro alternativas com dois raios de controle.
- `npm run verify:duelo-http -- http://127.0.0.1:3001`: passou. HTTP/SSE com dois clientes locais, respostas, placar compartilhado, rejeição de protocolo antigo e adulteração.
- Navegador: início de partida por mouse, resposta correta por mouse, resposta errada por teclado, estados de acerto/erro/tempo, troca de órgão sem manter o anterior e tela final após oito rodadas.
- Alternância entre Arena atual/revisada e carregamento da Escola conferidos visualmente.
- Durante inspeção, corrigidos lençol atravessando colchão, ausência de espessura da cobertura, tela dinâmica escondida pela moldura e braço de sustentação que atravessava o monitor. A placa lateral de higienização revelou rotação de UV causada pela reordenação de loops do BMesh: o mapeamento agora usa coordenadas físicas. Há testes de regressão dos eixos da inscrição e da face desobstruída do monitor.

## Limitações

- Sem teste físico de Quest, controladores, conforto ou resolução estéreo nesta etapa. Os testes de raios não substituem o headset.
- Amostra aquecida no navegador local: 144 FPS, p95 de 7,1–7,3 ms, 74 chamadas e 108.701 triângulos, menu com coração, DPR 1. Não é média de toda a sessão nem promessa de desempenho em Quest.
- Comparação com a Arena atual no mesmo enquadramento/menu: 144 FPS, p95 7,1 ms, 112 chamadas e 70.270 triângulos. A revisão reduz chamadas, mas aumenta geometria e download; não foi demonstrado ganho de FPS.
- O medidor existente descarta intervalos acima de 500 ms; por isso esta leitura **não mede travadas longas nem o carregamento inicial**. O medidor não foi alterado neste trabalho.
- Avisos já presentes de extensão antiga `KHR_materials_pbrSpecularGlossiness` em modelo carregado e de `THREE.Clock` obsoleto foram observados. Não foi detectada exceção de runtime nos logs consultados.
- Em uma sequência de navegação a câmera ficou em um ângulo impróprio; a troca a partir do enquadramento inicial foi repetida com sucesso, sem alterar os controles existentes. Não atribuir esse episódio a falha de carregamento sem reprodução controlada.
- Escola ainda não recebeu uma segunda revisão: permanece preservada para receber o mesmo processo depois da avaliação desta proposta da Arena.
- A nova sala ainda é estilizada. A aprovação do conjunto e da qualidade individual dos props depende da comparação pelo usuário, não dos testes automatizados.

## Próximo passo

A comparação visual foi aprovada. Testar a publicação em Quest com origem segura, medindo carregamento, estabilidade, mira dos controles e leitura a distância antes de considerar a validação XR concluída ou aplicar uma segunda revisão à Escola. A publicação foi expressamente autorizada pelo usuário; o resultado do deploy deve ser confirmado pela Vercel, não presumido a partir do build local.
