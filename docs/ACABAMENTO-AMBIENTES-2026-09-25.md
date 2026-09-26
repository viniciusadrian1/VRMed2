# Acabamento integrado das salas — 25/09/2026

Revisão local solicitada após a aprovação das placas físicas. Objetivo: integrar
materiais, equipamentos e contato com a arquitetura, sem alterar o centro aprovado,
as alternativas, o posicionamento XR ou as regras da competição.

## Entrega

- **Hospital:** materiais de esmalte, metal, borracha e tecido recalibrados;
  oclusão de proximidade gravada nos vértices dos equipamentos; piso com contatos
  calculados a partir do cenário (incluindo bancada, base do console e cadeira de rodas).
  Janela opaca com difusor, preenchimento discreto do teto, luminária de exame articulada
  sobre o leito e cobertura com queda lateral. Não há novas luzes em tempo real.
- **Escola:** mesma geometria, com oclusão gravada e textura local discreta de carvalho.
  Piso com contatos calculados, preservando as juntas, o tapete e as marcas dos postos.
  A prancha/esqueleto, a lousa e a posição das mesas continuam iguais.
- **Ambiente reativo:** o monitor do leito deixou de mostrar sempre “Em espera”.
  Agora comunica preparação, rodada, sequência, tempo final, acerto, revisão e resultado,
  usando o estado visual existente. Não apresenta sinais fisiológicos fictícios.
- **Preservado:** placas centralizadas, painel principal, alternativas e seus alvos,
  órgãos, câmera XR, pontuação, salas online, áudio e háptica.

Não é um novo modo de simulação clínica nem uma substituição da direção visual.
As interações livres com instrumentos e física de objetos não foram adicionadas:
esta entrega se concentra no acabamento, com o monitor como reação ambiental adicional.

## Autoria e reversibilidade

`scripts/refinar-ambientes-duelo.py` roda pelo Blender MCP, em cenas separadas.
Foi confirmado o retorno à cena original `Scene`, com seus três objetos intactos.
Os GLBs originais continuam no repositório sem mudanças; os componentes apontam para
variantes novas. Não houve importação nem simplificação de órgãos.

O cálculo offline usa 24 raios determinísticos por amostra, ponderados pelo cosseno,
com alcance de proximidade limitado. A oclusão é multiplicada no acabamento em `COLOR_0`.
O piso usa uma imagem opaca de 512×512, com contato calculado e gradiente difuso autorado.
**Não é um lightmap completo de iluminação global nem uma medição física de luz.**
As luzes direcionais/hemisféricas existentes continuam responsáveis pela anatomia.

A madeira usa uma imagem própria de 128×128 incorporada ao GLB. Sem CDN, bibliotecas
novas, captura de HTML, shader procedural caro, bloom ou sombras dinâmicas adicionais.
Os cinco contatos transparentes da retaguarda e quatro contatos estáticos da Escola
foram removidos para não duplicar sombras. O contato aproximado do avatar foi preservado.

As cenas de autoria e imagens intermediárias ficam em `tmp_acabamento/`, ignorado
pelo Git. O gerador e os GLBs finais são os artefatos reprodutíveis do produto.

## Orçamento medido dos arquivos finais

| Asset | Bytes | Triângulos | Malhas | Imagens |
|---|---:|---:|---:|---|
| entorno-arena-acabado.glb | 1.753.992 | 19.400 | 8 | nenhuma |
| retaguarda-arena-acabada.glb | 1.960.744 | 20.327 | 8 | nenhuma |
| piso-hospital-acabado.glb | 102.776 | 2 | 1 | 512×512 |
| escola-medicina-acabada.glb | 1.947.696 | 21.694 | 11 | 128×128 |
| piso-escola-acabado.glb | 101.868 | 2 | 1 | 512×512 |

A Escola mantém seus 21.694 triângulos originais, além dos dois do piso.
O entorno ganha dois triângulos da janela e a retaguarda ganha 1.904 da luminária/cobertura.
As cores por vértice aumentam o tamanho dos arquivos. Não afirmar otimização de download:
os cenários antigos tinham 1.379.572 / 1.321.600 / 1.530.688 bytes, respectivamente.

Cada piso ocupa aproximadamente 1,33 MiB como RGBA8 com mipmaps; madeira, 0,083 MiB.
São estimativas de textura, não memória total medida da GPU. O piso do Hospital substitui
a antiga textura de 512×512. O novo monitor pequeno usa 512×160 (aprox. 0,42 MiB com
mipmaps), uma textura reutilizada, redesenhada apenas quando o conteúdo muda.
Esses números não são uma medição de FPS nem uma garantia de desempenho no Quest.

## Arquivos deste incremento

- `components/duelo/AmbienteHospital.tsx`, `AmbienteEscola.tsx`: integração dos pisos/variantes.
- `components/duelo/EntornoHospital.tsx`, `RetaguardaHospital.tsx`: variantes e monitor do leito.
- `components/duelo/OrientacaoEscola.tsx`: remoção dos contatos estáticos duplicados.
- `components/duelo/PisoCenario.tsx`: piso opaco com fallback e cache GLTF preservado.
- `components/duelo/TelaoDuelo.tsx`: tamanho opcional e resolução compacta; padrão principal mantido.
- `lib/monitor-ambiente.ts`: apresentação do estado no monitor, sem arbitragem.
- `scripts/refinar-ambientes-duelo.py`: autoria Blender e exportação.
- `scripts/verificar-acabamento-duelo.ts`, `package.json`: testes integrados ao `verify:core`.
- Cinco GLBs da tabela; este relatório e `docs/CONTEXTO.md`.

Há alterações anteriores de tipografia/sinalização ainda não commitadas no mesmo
worktree. Elas foram preservadas e não devem ser confundidas com este incremento.

## Verificação

- Inspeção no navegador local: Hospital de frente e leito/fundo; Escola, menu,
  contagem, rodada, acerto, troca de órgão e tela final.
- Mouse: acerto em alternativa na Escola. Teclado: início de partida e acerto
  em outra rodada. Órgão anterior não permaneceu empilhado nas trocas observadas.
- Monitor do leito observado mudando de “Em espera” para “Rodada 1”.
- Sem erros de console no carregamento limpo final. Durante a edição, Fast Refresh
  registrou mudança no tamanho das dependências dos efeitos do telão, pois o código
  passou a aceitar resolução compacta. O diagnóstico foi separado numa nova aba,
  sem reutilizar o histórico de console da sessão de edição. Avisos antigos de
  GLB/Troika/depreciação permanecem; não há validação de todos os aparelhos/navegadores.
- `verify:acabamento`: GLBs finais carregados, normais/cores finitas, imagens
  incorporadas, limites de bytes/geometria, corredores e postos livres, 48 alvos
  de centro/borda com dois raios. Node substitui o decodificador de imagem apenas
  nesse teste geométrico; rasterização foi verificada no navegador.
- Integração HTTP/SSE local com dois clientes passou, incluindo placar compartilhado,
  rejeição de versão antiga e perguntas adulteradas. O primeiro comando tentou a
  porta padrão sem servidor; o teste foi repetido com a porta local correta.
- Validação final: `npm run typecheck`, `npm run lint`, `npm run verify:core`
  (incluindo o novo teste) e `npm run build` passaram, com as cinco variantes finais.
  Build gerou as 20 páginas sem erro. Isso não mede o desempenho do headset.

## Limites e reteste no Quest

Ainda não houve teste físico nem medição de FPS/p95 no headset nesta revisão.
O medidor atual descarta deltas acima de meio segundo: não usá-lo sozinho para
afirmar ausência de travadas. DPR 1 no XR foi mantido. Não há aprovação para evento
até testar ambas as salas, fundo/laterais, duas mãos, placas à distância, acerto/erro,
últimos segundos e pelo menos uma partida completa, incluindo online em dois óculos.

A inspeção detectou e corrigiu uma luminária inicialmente competindo com Suprimentos
(transferida ao leito) e uma grade duplicada no piso da Escola (removida da textura).
Não houve publicação nem commit neste incremento.
