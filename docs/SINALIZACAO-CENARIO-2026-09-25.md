# Duelo — placas físicas e telão integrado

## Escopo e decisões

Revisão solicitada após o primeiro passe de tipografia: as alternativas foram
aprovadas, mas os nomes da sala pareciam texto sobreposto. A intervenção fica na
sinalização do ambiente e no monitor superior. Regras, controles, pontuação,
órgãos e origem XR não foram alterados neste incremento.

O usuário pediu uso do Blender MCP. Após ativar o servidor do complemento, uma
consulta real confirmou conexão. A tentativa inicial de construir as placas em
runtime foi substituída por GLBs produzidos pelo Blender MCP. Não é uma migração
para Unity. A cena original do Blender, com cubo, câmera e luz, foi preservada.

Durante a inspeção ao vivo, o usuário pediu títulos maiores, centralização e
remoção de descrições que roubavam espaço. Resultado:

- Arena Médica centralizada na própria placa; VRmed discreto no canto.
- Preparo, Suprimentos, Apoio / materiais, Higienização e Posto de apoio centrados.
- Entrada somente com Centro de simulação, sem marca ao lado.
- Leito de treinamento conserva a descrição aprovada.
- Escola: Laboratório de anatomia, Responda na lousa, Osteologia, Microscopia
  e Atlas / estudo recebem o mesmo tipo de acabamento, com paleta mais quente.
- Duelo 1×1 no telão vira uma inscrição grande, centrada e desenhada na própria
  superfície do monitor; contagem, cronômetro e placar continuam compartilhando-a.

As placas têm corpo chanfrado, junta de contato, fixadores e superfície opaca.
Tinta e fundo compartilham o material iluminado, sem contorno ou letras acima do
cenário. Os GLBs antigos foram preservados: as novas carcaças envolvem os rótulos
substituídos. Microtextos de equipamentos e orientação dinâmica não são todos
convertidos em placas estáticas.

## Autoria e arquivos

- `lib/sinalizacao-duelo.json`: títulos, medidas métricas, posições e paletas.
- `scripts/preparar-texturas-sinalizacao.py`: atlas com a fonte Inter local já
  existente. Pillow/fontTools são ferramentas de autoria instaladas, não novas
  dependências do produto. Supersampling e centralização pela área visível da tinta.
- `scripts/criar-sinalizacao-duelo.py`: executado pelo Blender MCP; cria cenas
  separadas, agrupa por material, exporta GLBs com PNG incorporado e restaura a
  cena anteriormente ativa. Não apaga objetos preexistentes.
- `public/models/props/sinalizacao-hospital.glb` e `sinalizacao-escola.glb`.
- `components/duelo/SinalizacaoCenario.tsx`: carregamento local com isolamento de
  falhas, cache preservado, filtro anisotrópico limitado e ponteiros desativados.
- `components/duelo/AmbienteHospital.tsx` e `AmbienteEscola.tsx`: montagem das placas.
  A travessa do pórtico foi ajustada; não mudaram posições das alternativas.
- `components/duelo/TelaoDuelo.tsx` e `lib/telao-duelo.ts`: superfície do telão.
- `components/duelo/DueloGame.tsx`: troca apenas do desenho do conteúdo do telão.
- `scripts/verificar-sinalizacao-duelo.ts`, `scripts/verificar-tipografia-duelo.mjs`
  e `package.json`: testes e inclusão em `verify:core`.

Os arquivos de trabalho Blender e atlas intermediários ficam em `tmp_sinalizacao/`,
já ignorado pelo Git. Os scripts e GLBs são suficientes para reproduzir a autoria.
Um render de inspeção foi produzido em `tmp_sinalizacao/placa-arena-blender.png`;
ele usa luzes de bancada e não deve ser confundido com captura do jogo.

## Orçamento medido

| Conjunto | Placas | Malhas / materiais | Triângulos | Arquivo | Atlas |
|---|---:|---:|---:|---:|---|
| Hospital | 8 | 3 / 3 | 2.288 | 387.784 bytes | 2048 × 1024 |
| Escola | 5 | 3 / 3 | 1.862 | 280.620 bytes | 2048 × 512 |

Nenhuma animação, luz, câmera ou dependência externa nos GLBs. Não foi aplicada
simplificação ou Draco: a geometria já é pequena e o arquivo inclui a textura.
O atlas estático representa aproximadamente 10,67 MiB no Hospital e 5,33 MiB na
Escola, estimando RGBA8 com mipmaps; isso é estimativa de armazenamento da textura,
não medição de memória total da GPU. O cache pode manter ambos após trocar de sala.

O monitor usa uma textura 1024 × 320 reutilizada, redesenhada somente quando muda
texto/cor ou termina o carregamento da fonte; não captura HTML, não aloca textura
por segundo e não trabalha por frame. Sem bloom, novas luzes, sombras dinâmicas
ou aumento do DPR no XR. O modo Nitidez alta do desktop já existente permanece
opcional. Texto maior ajuda à distância, mas não elimina limites físicos de
resolução do headset ou de um framebuffer com DPR 1.

## Validação

- `npm run typecheck`, `npm run lint` e `npm run build`: passaram.
- `npm run verify:core`: passou, incluindo XR, áudio, regras online, apresentação,
  botões, Escola, retaguarda, tutor, questões e painéis.
- Novo teste dos GLBs: atlas incorporado e dimensões, materiais opacos iluminados,
  normais, escala, raios em nove pontos por placa, corredor livre e dois controles.
- Teste de tipografia: fonte real, 119 alternativas, margens e centralização do
  monitor com números e placares longos. O teste de Canvas registra comandos;
  a rasterização real é conferida no navegador, não simulada como prova visual.
- `npm run verify:duelo-http -- http://127.0.0.1:3000`: passou com dois clientes,
  HTTP/SSE, placar compartilhado e rejeição de protocolo/gabarito adulterado.
- Inspeção desktop no navegador: Arena, Escola, entrada, leito, apoio, menu e
  transição para contagem/rodada. Alternativas preservadas. A habilidade de
  inspeção visual orientou o aumento dos títulos e a retirada dos subtítulos.

Avisos preexistentes: extensão antiga de material de um GLB do acervo e
depreciação de THREE.Clock no navegador; parser de fonte avisa sobre tabelas
GSUB nos testes. O Blender avisa sobre futura depreciação de Material.use_nodes.

## Limites e reteste

Não houve medição de FPS nem teste em Quest físico. Conferir no aparelho:
leitura das placas frontal/oblíqua, cintilação em movimento, cronômetro/placar,
dois lasers, troca de ambiente e memória após sucessivas partidas. Não tratar
os raios sintéticos ou o render Blender como homologação de conforto no headset.

Não foram feitos commit, push ou deploy desta revisão. O diretório também contém
alterações anteriores de tipografia que foram preservadas; este relatório não
atribui todas as diferenças do Git ao incremento atual.
