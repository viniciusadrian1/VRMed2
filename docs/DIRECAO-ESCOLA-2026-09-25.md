# Escola — revisão de modelagem e composição

## Escopo

Aplicação da mesma abordagem autoral da Arena Médica à Escola, a pedido do usuário.
A identidade continua acadêmica: carvalho, verde profundo, cerâmica clara e metal.
Não é uma cópia do hospital nem uma simples troca de cores.

Preservados: posições e geometria do palco, lousa, carteiras e dois postos em pé;
alternativas e sinalização aprovada; regras, controles, órgãos e acervo anatômico.
Os materiais compartilhados do mobiliário recebem a nova paleta e acabamento.
Nenhum commit ou envio remoto neste incremento.

## Mudanças visíveis

- Biblioteca de atlas reconstruída como um móvel único, com base fechada, três
  prateleiras, laterais de madeira, fundo verde, puxadores e filetes metálicos.
  Os livros têm miolo, capas e lombadas separados.
- Bancada de microscopia arredondada, tampo cerâmico, base recuada, portas verdes
  e puxadores curvos orientados para o centro da sala.
- Dois microscópios binoculares remodelados: arco, oculares, revólver, objetivas,
  platina, condensador, lâmina, ajustes de foco e cabos. São props estilizados;
  não simulam instrumentos ópticos funcionais.
- Vitrine de osteologia com moldura curva e difusor superior; mesmo vão para a
  prancha/esqueleto. Nenhuma anatomia foi criada, simplificada ou substituída.
- Parede frontal com painéis acústicos amplos, pilastras e cornija contínua;
  forro com peças curvas de madeira e difusores quentes; venezianas nas janelas.
- Fundo com armário baixo para material didático e nicho de atlas, sem novas
  cadeiras ou equipamentos dentro dos postos.
- Oclusão de proximidade gravada nas cores dos vértices, piso recalculado para
  os móveis novos e reflexos estáticos somente nos materiais do cenário.

Nenhuma luz dinâmica nova, sombra dinâmica, transparência ou pós-processamento.
Os difusores são superfícies emissivas; não acrescentam luzes ao GLB.

## Autoria e reprodução

`scripts/dirigir-arte-escola.py` foi executado pelo Blender MCP em cena separada,
`VRmed_Direcao_Escola`, usando Blender 5.2.1 LTS. A cena original `Scene`, com
Cube/Light/Camera, permaneceu intacta e foi restaurada ao final.

O script reutiliza a autoria anterior de `criar-escola-medicina.py` antes da união
das malhas, extrai somente as funções geométricas de `dirigir-arte-arena.py` e
reutiliza textura/oclusão/exportação de `refinar-ambientes-duelo.py`. Não executa
a remodelagem do Hospital. Uma guarda compara vértices em coordenadas mundiais
de 42 peças protegidas antes/depois da remodelagem.

Para reproduzir, executar o script pelo Blender com `__file__` apontando para seu
caminho absoluto. Ele grava os dois GLBs abaixo e a cena editável em
`tmp_acabamento/escola-direcao.blend`, ignorada pelo Git. O resumo da geração está
em `tmp_acabamento/escola-direcao.json`. Os assets anteriores foram mantidos.

## Orçamento medido nos arquivos

| Asset | Triângulos | Malhas | Bytes |
|---|---:|---:|---:|
| Escola anterior acabada | 21.694 | 11 | 1.947.696 |
| `escola-medicina-direcao.glb` | 38.366 | 11 | 3.072.104 |
| `piso-escola-direcao.glb` | 2 | 1 | 97.504 |

O ambiente principal acrescenta 16.672 triângulos e 1.124.408 bytes, mantendo
11 malhas agrupadas por material. Não é uma otimização de download. Esses números
não incluem órgãos, interface, avatar, sinalização ou o esqueleto opcional.

A textura local de madeira tem 128 × 128 pixels; a do piso, 512 × 512. Ambas são
incorporadas aos GLBs. O bake usa 12 raios por amostra. Sem Draco nesses props.
O esqueleto conserva sua versão original e seu carregamento opcional fora das
rodadas; a prancha leve continua sendo o padrão.

`useReflexosCenario` reaproveita o recurso introduzido no Hospital: PMREM de 128
pixels por face, criado localmente, sem atualização por quadro e sem alterar
`scene.environment`. As cópias dos materiais e o alvo são liberados na desmontagem.
Há custo de geração, textura e amostragem; não foram medidas memória GPU ou
estabilidade no Quest. DPR do XR continua 1.

## Arquivos deste incremento

- `scripts/dirigir-arte-escola.py`: autoria e exportação Blender.
- `public/models/props/escola-medicina-direcao.glb`: novo ambiente.
- `public/models/props/piso-escola-direcao.glb`: contatos da nova composição.
- `components/duelo/AmbienteEscola.tsx`: asset ativo e reflexos locais.
- `components/duelo/PisoCenario.tsx`: asset de piso da Escola.
- `components/duelo/DueloApp.tsx`: vistas laterais/fundo de inspeção da Escola,
  somente em desenvolvimento desktop. Produção e sessão XR ignoram a opção;
  câmeras normais e origem do jogador não foram alteradas.
- `scripts/verificar-escola.ts`: testa o GLB realmente usado, incluindo geometria
  dos postos, raios e orçamento atualizado.
- `scripts/verificar-acabamento-duelo.ts`: assets ativos, orçamento, limites da
  Escola, normais, imagens locais e interferência nos alvos.
- Este relatório e `docs/CONTEXTO.md`.

As demais alterações anteriores do worktree foram preservadas.

## Validação e limites

- Passaram: `typecheck`, `lint`, `verify:core`, build de produção e
  `verify:duelo-http -- http://127.0.0.1:3000` (HTTP/SSE local com dois clientes).
- Testes com a geometria exportada: normais finitas/unitárias, cores de oclusão,
  imagens incorporadas, limites da sala, volumes dos dois postos livres e 48
  alvos com dois raios, além dos testes específicos de botões e da Escola.
- Inspeção no navegador: frente, microscopia à direita, janela/biblioteca à
  esquerda e armazenamento ao fundo. Início de partida por teclado, acerto por
  mouse, resposta por teclado e combo ×2 observados. Troca rim → cérebro sem
  permanência do modelo anterior. Tela final e retorno ao menu por Escape também
  conferidos; a aba local ficou no menu da Escola para avaliação.
- Os testes de interação geométrica não substituem dois controles no headset.
  A qualidade das texturas foi inspecionada no navegador, não pelo decodificador
  substituto usado nos testes de geometria em Node.
- Avisos existentes de Node/Troika não impediram build/testes. Teste físico de
  nitidez, conforto e desempenho no Quest segue pendente; o medidor atual ignora
  deltas longos e não basta como prova de fluidez.
- Nenhum erro registrado no console da aba inspecionada. Permanecem avisos de
  `THREE.Clock` obsoleto e extensão `KHR_materials_pbrSpecularGlossiness` não
  reconhecida durante o carregamento; não foram corrigidos neste incremento.

A revisão está disponível localmente para aprovação visual, sem publicação.
Não foi necessário recorrer a Unity, Tripo, assets externos ou dependências novas.
