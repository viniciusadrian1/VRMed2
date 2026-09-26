# Tipografia do Duelo — primeiro incremento

Data: 24/09/2026. Escopo: apresentação textual da Escola e da Arena Médica.

## Alterações

- Mantida a fonte Inter 600 local. O acabamento foi corrigido por função do texto, não por troca de fonte ou aumento de DPR.
- Interface da partida sem contorno pesado, com entrelinha explícita, perguntas alinhadas à esquerda e alternativas com selo A–D separado do rótulo.
- Faces dos botões do Duelo escurecidas para sustentar o contraste sem depender do contorno dos glifos. Bordas de acerto/erro mantêm a cor do estado.
- Placas físicas passam a receber iluminação e respeitar a profundidade; telas mantêm contraste próprio e também respeitam a oclusão. A interface de resposta continua protegida contra o órgão ampliado.
- Nome da Arena Médica apoiado na travessa; cabeçalho do console alinhado às margens; aviso do monitor trazido para dentro da moldura; plaquetas dos postos com título e orientação separados.
- Escola recebeu três pequenos suportes de placa: vitrine, bancada anatômica e orientação abaixo da lousa. A inspeção visual identificou oclusão pela bandeja de giz e o último suporte foi reposicionado.
- Aviso de erro da Escola movido para a linha de status, sem sobrepor a pergunta.
- Os tratamentos novos são opt-in no Duelo. Arena, Sala, Clínica e painéis de estudo mantêm o padrão anterior.

Não foram alterados: regras, pontuação, tempo, protocolo online, eventos dos controles, geometria dos alvos de clique, modelos anatômicos, câmera, DPR ou resolução XR. Nenhuma dependência ou asset externo foi acrescentado.

## Arquivos

- `lib/tipografia-3d.ts`: materiais por função e margens dos rótulos.
- `components/arena/ui3d.tsx`: opções de tratamento, alinhamento e contraste, preservando o padrão antigo.
- `components/duelo/tipografia.tsx`: adoção restrita ao Duelo.
- `components/duelo/DueloGame.tsx`: hierarquia da rodada, alinhamento, aviso de erro e telão.
- `components/duelo/BotaoLousa.tsx`: selo independente e tratamento compartilhado.
- `components/duelo/ArenaMedica.tsx`: console, pedestal, monitores e sinal da Escola.
- `components/duelo/AmbienteHospital.tsx`: letreiro apoiado e título do monitor.
- `components/duelo/AmbienteEscola.tsx`: placas e botão da vitrine.
- `components/duelo/OrientacaoEscola.tsx`: plaquetas dos competidores.
- `scripts/verificar-tipografia-duelo.mjs` e `package.json`: regressão tipográfica integrada à suíte.

## Validação realizada

Comandos concluídos com sucesso:

```text
npm run typecheck
npm run lint
npm run build
npm run verify:core
npm run verify:tipografia
npm run verify:duelo-http -- http://127.0.0.1:3000
git diff --check
```

`verify:core` inclui ciclo XR, salas Duelo, áudio, apresentação, botões XR, Escola, retaguarda, tutor, perguntas, tipografia e painéis XR.

O novo teste mede a fonte WOFF real com o parser já instalado do Troika: 119 rótulos, 30 perguntas, feedbacks, largura das plaquetas, margens dos selos e altura das alternativas. Verifica materiais, profundidade e contraste calculado das cores ativas. Esse cálculo não equivale a validar legibilidade no headset. O parser emite avisos de tabelas GSUB não suportadas; as verificações de glifos e medidas passam. O Node também mantém os avisos de tipagem de módulos já presentes na suíte.

Teste HTTP/SSE local com dois clientes passou: compartilhamento do placar, perguntas de identificação e conhecimento, rejeição de protocolo antigo e de gabarito adulterado. Não substitui um teste com dois headsets ou a infraestrutura de produção.

Inspeção real no navegador local, viewport de 1280 × 720, nitidez padrão:

- Menus da Arena Médica e Escola.
- Contagem de entrada, placar e rodada ativa nos dois cenários.
- Clique do mouse com acerto no Hospital.
- Clique do mouse com erro na Escola: aviso separado do enunciado.
- Resposta correta por teclado após o erro: destaque verde e explicação legíveis.
- Últimos segundos, tempo esgotado e revisão da resposta.
- Troca de órgão entre rodadas sem sobreposição observada nas capturas inspecionadas.
- Tela final nos dois cenários; revanche e retorno ao menu pelo teclado.
- Placas da bancada/vitrine, orientação do posto e letreiro do Hospital visíveis nas vistas inspecionadas.

Não foram registrados erros no console da aba consultada. Foram registrados dois avisos: extensão GLTF `KHR_materials_pbrSpecularGlossiness` não reconhecida e depreciação de `THREE.Clock`. Esses caminhos não foram modificados neste incremento.

## Limites e reteste

- **Quest físico não testado.** Conferir tamanho aparente, conforto, nitidez e contraste à distância real dos postos.
- Conferir ambas as mãos: centro/bordas das alternativas, intervalo entre elas e gatilho segurado. Os testes geométricos existentes passaram; não são um ensaio físico dos controles.
- Caminhar/olhar lateralmente para validar as novas placas com oclusão real. Elas não devem aparecer atravessando móveis ou paredes; a interface de resposta continua sobreposta por segurança de interação.
- Testar combo máximo e vitória no headset. Os textos de combo foram medidos automaticamente, mas esses estados não tiveram inspeção visual completa nesta sessão.
- Não houve medição comparativa de FPS/GPU, portanto não há promessa de ganho de desempenho. Foram acrescentados apenas três suportes cúbicos de placa à Escola; sem sombras, luzes, pós-processamento ou texturas adicionais. Textos físicos passam a usar material com iluminação.
- Letreiros incorporados aos GLBs e rótulos transitórios flutuantes não foram reexportados/redesenhados nesta etapa.
- Sem commit, push ou deploy nesta sessão.
