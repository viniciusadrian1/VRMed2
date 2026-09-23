# Duelo — arena médica e diagnóstico do crânio

Implementação e inspeção em 22/09/2026, com evidências também registradas na madrugada de 23/09 em UTC. Runtime continua Next.js + React Three Fiber + WebXR. Nenhuma migração para Unity, nova dependência ou alteração de pontuação/arbitragem.

## Resultado e limite da entrega

A apresentação desktop foi implementada e testada. O Hospital passou a se apresentar como **Arena médica**, selecionada inicialmente; a Escola continua disponível. O ambiente recebe uma cópia dos estados da partida e reage sem interferir na lógica online.

**A homologação no Quest permanece pendente.** A consulta local `adb devices -l` não encontrou dispositivos. O navegador de teste não ofereceu sessão imersiva. A bancada Unity confirma medidas e composição aproximada, não conforto, leitura estereoscópica ou desempenho no headset. Portanto, esta entrega não deve ser anunciada como pronta para evento em Quest antes do teste físico.

## Baseline observada

- Hospital com preenchimento luminoso excessivo, props competindo com a área de interação e divisória transparente atravessando a leitura da interface.
- Interface sem uma carcaça física clara e pouco contraste entre protagonista e fundo.
- Rodadas em desenvolvimento nas quais o marcador aparecia, mas o órgão não. O cleanup retirava o clone da cena e o segundo setup do Strict Mode não o recolocava.
- Personagens decorativos com cerca de 1,94 milhão de triângulos cada e arquivos de 63–69 MB: custo desproporcional ao papel visual.
- Crânio branco sobre fundo claro, com luz de ambiente preenchendo as cavidades e apagando visualmente o relevo.

Foram inspecionados menu, Escola, Hospital, contagem, rodada, acerto, erro, combo, últimos segundos e encerramento. A análise começou antes das mudanças visuais maiores. As capturas existentes mostram etapas diferentes; não devem ser usadas como benchmark de cenas idênticas.

## Incrementos implementados

| Área | Alteração | Verificação |
| --- | --- | --- |
| Órgão e ciclo de vida | Reanexar o clone no remonte de efeitos; manter chave por rodada, remoção do anterior e geometria compartilhada | Rodadas sucessivas no navegador, desenvolvimento e produção; guardas estáticas no teste |
| Palco | Bancada autoral produzida no Blender, aro luminoso, luminária, placa e coração de demonstração apenas no menu | GLB carregado na aplicação; composição horizontal e vertical |
| Painel | Console com carcaça, base, identidade VRmed, sequência e painel central integrado ao cenário | Mouse, teclado, placar, cronômetro e alternativas |
| Iluminação | Principal quente, recorte frio reativo e preenchimento moderado; sem sombras dinâmicas ou pós-processamento no Duelo | Inspeção visual dos estados, sem modificar câmera XR |
| Props | Carrinhos e ultrassom nas laterais, monitor de estado, faixas de LED e organização do fundo | Não interceptam raycast; botões continuam operáveis |
| Feedback | Verde no acerto, coral no erro, âmbar nos últimos cinco segundos, vitória quente e derrota fria/instrutiva | Acerto, erro, tensão e derrota observados; vitória/empate cobertos pela função de apresentação e teste unitário |
| Game feel | Contagem, entrada do órgão, hit-stop, sons, háptica e retrospecto existentes preservados e ligados à ambientação | Rodada, combo ×2, retrospecto e regressão de áudio |
| Legibilidade | Correção da ordem de transparência da barra de tempo; enquadramento vertical sem corte do console | Navegador 390×844 e desktop |
| Qualidade | Nitidez alta opcional no desktop; DPR 1 preservado em XR; medidor local opt-in | Alternância DPR 1/2 e amostras de cinco segundos |

O monitor lateral informa explicitamente que mostra o estado da partida, não um sinal clínico. Cor sempre acompanha texto. As novas faixas luminosas usam pulso lento de baixa amplitude, com `prefers-reduced-motion`; não há estrobo nem movimento automático da câmera XR. Os props não bloqueiam os ponteiros.

O combo é derivado do histórico já existente e só afeta apresentação. As regras de 100/200 pontos, salas, janela de arbitragem, revanche e abandono não foram modificadas. Não foi adicionado sistema novo de recompensas, progressão ou simulação clínica.

## Blender MCP e assets

O Blender MCP foi usado de fato para criar a bancada, gerar variantes dos personagens e inspecionar/renderizar o crânio. Foram utilizadas cenas separadas, restaurando a cena ativa anterior; nenhum original anatômico foi exportado por cima. As cenas de trabalho temporárias podem permanecer na sessão do Blender, sem salvamento sobre o arquivo original.

| Asset | Original | Variante utilizada |
| --- | --- | --- |
| Bancada autoral | Novo asset | 125.028 bytes; 1.728 triângulos; 5 malhas e 5 materiais; sem texturas/Draco |
| Dr. Caloni | 68.920.504 bytes; 1.931.304 triângulos | 3.420.812 bytes; 45.000 triângulos |
| Dra. Reis | 62.679.356 bytes; 1.939.470 triângulos | 3.305.708 bytes; 44.999 triângulos |
| Dr. Chefe | 63.970.536 bytes; 1.954.070 triângulos | 3.413.232 bytes; 45.000 triângulos |

As variantes dos **personagens de cenário, não modelos anatômicos**, usam Draco e três texturas de até 1.024 px cada. Os originais continuam intactos. A aplicação carrega o decodificador local em `/draco/`. Não foi aplicado `simplify-ratio` a órgão algum. A bancada usa metros e origem no piso; seu tampo fica aproximadamente a 0,86 m. Os avatares não possuíam clips de animação; a movimentação procedural existente continua.

Os três personagens foram carregados visualmente. A redução é de aproximadamente 97,7% dos triângulos **dos personagens**, não de toda a cena. Não implica o mesmo percentual de ganho de FPS. Créditos e origem constam em `public/models/props/CREDITS.md`; não foram incorporados assets do Surgeon Simulator.

## Crânio: por que parecia ter baixa resolução

Auditoria do GLB original:

- 3.288.940 bytes; 25 malhas; 586.499 vértices; **1.126.158 triângulos**.
- Uma animação, 22 canais e dois materiais; nenhuma textura embutida e nenhuma malha com UV.
- Normais presentes; zero normais de vértice nulas/não finitas na inspeção numérica e zero transformações globais com determinante negativo. Isso não certifica orientação de cada face nem fidelidade clínica.
- Comparação dos frames 0 e 96 mostrou movimento em 46 nós, incluindo pais e filhos: não significa 46 ossos. Pivôs, hierarquia, dentes, mandíbula e abertura foram preservados.
- Dimensões fechadas na escala original: aproximadamente 14,88 × 23,00 × 25,11 unidades do arquivo. Não se deve assumir centímetros; o aplicativo normaliza o modelo.
- SHA-256 preservado: `849278d46cc5756074e237e725341a9cf30778fee913c70b5bd00803ed44d2e5`.

**Conclusão observada:** já há bastante geometria, inclusive suturas visíveis sob iluminação neutra no Blender. No visualizador web, o ambiente de estúdio branco e o material/fundo muito claros reduziam a percepção das cavidades e dos relevos. Mais polígonos não foi a solução. Ausência de textura não é, por si só, prova de falta de resolução geométrica.

Foi aplicado acabamento de osso seco somente em materiais clonados: tom marfim, roughness 0,72, dentes com acabamento separado (roughness 0,38) e metalness zero. A luz de preenchimento foi reduzida e o ambiente branco removido **somente para o crânio**. O fundo de estudo azul-acinzentado não cobre o passthrough em AR. Nenhuma sutura ou informação anatômica foi inventada.

O visualizador já utilizava DPR automático entre 1 e 2 fora de XR; não era correto atribuir todo o problema a DPR fixo 1. Agora há opção explícita de alta nitidez (DPR 2 mesmo em monitor 1×). A comparação web final também altera material/iluminação: não é um ensaio isolado do efeito do DPR. As duas imagens fechadas do Blender usam câmera e iluminação iguais, isolando melhor o acabamento do material.

Não foram criados mapas de normal/cavity/roughness em textura: o asset não possui UV, e uma nova etapa de UV/bake merece revisão própria para não esconder ou fabricar suturas. O relevo atual continua vindo da geometria original. Foi mantida uma opção manual de DPR, em vez de adaptação automática não validada, para evitar oscilações de nitidez. O crânio continua pesado para um headset e **precisa de medição real no Quest**.

Comparações em `docs/evidencias-arena/`:

- `cranio-antes.png` e `cranio-depois.png`: navegador, fechado e vista padrão; depois com alta nitidez e nova iluminação.
- `cranio-aberto-web.png`: abertura no aplicativo.
- `blender-cranio-original.png` e `blender-cranio-osso.png`: comparação controlada de material.
- `blender-cranio-aberto.png`: hierarquia aberta, com enquadramento ajustado para incluir os ossos.
- `auditoria-cranio-blender.json`: inspeção numérica.
- `cranio-material.png`: etapa intermediária, não o resultado final.

## Unity MCP: o que foi realmente validado

O relay oficial `unity_mcp` executou `Unity_RunCommand` no Unity 6000.5.10f1, projeto “Tutorial no Editor do Guia de Configuração”. O outro endpoint configurado, `unityMCP` em `127.0.0.1:8080`, respondeu como servidor, mas não tinha instâncias de Editor conectadas. Portanto, não é correto afirmar que os dois conectores estão equivalentes.

Uma cena de preview reproduziu os volumes principais em escala humana, com conversão de eixo Z entre Three.js e Unity:

- olhos a 1,60 m do piso;
- centro da interface a 1,45 m e centro do órgão a 1,50 m;
- distância olhos–console de aproximadamente 3,314 m;
- azimute do console +14,9° e do órgão −19,0°.

`unity-escala.png` é um **blockout**, não uma reprodução da iluminação final nem prova de experiência em headset. A cena de preview foi encerrada e nenhum arquivo de cena do projeto Unity foi salvo. A criação temporária de objetos pode ter marcado o Editor como contendo alterações pendentes; esse indicador não foi limpo à força para não ocultar possíveis mudanças do usuário.

## Desempenho medido e limites

Foi incluído um medidor opcional de FPS médio, p95 de intervalo entre frames, chamadas de desenho, triângulos e DPR em janelas de cinco segundos. Ele não envia telemetria. Os contadores do renderer são uma amostra, não um perfil de GPU nem necessariamente o total de um quadro estereoscópico.

No computador desta execução foram observadas amostras próximas de 144 FPS / p95 7,1 ms em DPR 1 e uma amostra de 137 FPS / p95 8,6 ms em DPR 2. Rodadas posteriores à troca dos personagens exibiram 187–196 chamadas e aproximadamente 124–228 mil triângulos, dependendo do órgão. Essas cenas não são idênticas, o hardware não foi caracterizado e o limite de atualização influencia o resultado: **não são benchmark comparativo nem previsão de FPS do Quest**.

O cenário ainda pode ficar próximo de 200 chamadas por quadro, incluindo interface textual. Se o teste físico mostrar gargalo, priorizar agrupamento/instanciamento de props e geometria estática, não simplificação automática dos órgãos. O crânio tem um orçamento separado, superior a um milhão de triângulos.

## Matriz de validação

- `npm run typecheck`: passou.
- `npm run lint`: passou.
- `npm run build`: passou.
- `npm run verify:xr`: passou; verifica ciclo/guardas, **não substitui headset**.
- `npm run verify:duelo`: passou; pareamento, pontuação/janela, tempo, revanche e abandono.
- `npm run verify:audio`: passou; eventos, combo e tensão.
- `npm run verify:apresentacao`: passou; sinais, material, integridade do crânio, orçamento dos personagens e guardas estáticas de remoção/remonte do órgão.
- `npm run verify:core`: inclui as quatro verificações acima.
- Navegador: menu, contagem, rodadas sucessivas, acerto, erro, combo ×2, alerta final, retrospecto, mouse e teclado verificados. Barra de tempo visível após correção da fila transparente.
- Duelo online: duas sessões reais locais entraram na mesma sala; mesma pergunta/tempo, erro local, acerto e pontuação espelhada (200×0 / 0×200); rodada seguinte sincronizada. Não foi teste entre dois headsets nem de latência em internet pública.
- Escola preservada e inspecionada; Arena médica inspecionada em 1144×910, 1280×720 e 390×844.
- Build de produção iniciado em `127.0.0.1:3001`; rodada com GLBs e cronômetro carregou sem erro de console.
- Crânio: abrir/fechar, aproximação, reset de vista e alta nitidez testados. Houve aviso de hooks durante Fast Refresh ao editar dependências; não é evidência de falha em carregamento limpo. Avisos antigos de `THREE.Clock` e material legado de props não foram tratados como novos erros da arena.
- Sem teste auditivo humano de espacialização/háptica física, sem sessão XR real, sem medição térmica prolongada. Não se afirma ausência de desconforto sem headset.

## Arquivos alterados/criados

- Apresentação: `components/duelo/ArenaMedica.tsx`, `EstadoArena.tsx`, `MedidorDuelo.tsx`, `AmbienteHospital.tsx`, `DueloApp.tsx`, `DueloGame.tsx`, `Oponente.tsx`; `lib/duelo-apresentacao.ts`; `components/arena/ui3d.tsx`.
- Crânio: `components/viewer/GLBModel.tsx`, `components/viewer/Scene.tsx`, `lib/material-osso.ts`. O GLB original não foi alterado.
- Assets: `public/models/props/bancada-arena.glb`, `dr-caloni-arena.glb`, `dra-reis-arena.glb`, `dr-chefe-arena.glb` e `CREDITS.md`.
- Reprodução/auditoria: `scripts/criar-bancada-arena.py`, `criar-avatares-arena.py`, `diagnosticar-cranio-blender.py`, `auditar-assets-arena.mjs`, `inspecionar-unity-mcp.py`, `validar-escala-unity.cs`, `verificar-apresentacao-duelo.ts`; `package.json`.
- Documentação: este relatório, atualização de `docs/CONTEXTO.md` e capturas em `docs/evidencias-arena/`.

Scripts Blender são executados no Blender/MCP; a ponte Unity requer o relay oficial e o SDK MCP Python presentes neste computador. Não são dependências do runtime nem etapas obrigatórias do build web.

## Próxima validação necessária

1. Conectar um Quest e servir a aplicação em contexto seguro (HTTPS ou encaminhamento USB para localhost).
2. Testar sentado e em pé: ler alternativas/marcadores, responder com controle e mãos quando suportado, entrar/sair/reentrar em XR, confirmar ausência de sobreposição de órgãos.
3. Jogar uma partida completa, incluindo vitória, derrota, combo e últimos segundos; testar sala entre dois dispositivos e abandono/revanche.
4. Medir frame time/estabilidade em sessão prolongada, especificamente no crânio aberto e fechado. Não aprovar para evento apenas com o FPS desktop.
5. Se necessário, otimizar cenário/textos e definir preset de qualidade por evidência; preservar a anatomia e manter DPR 1 como base XR.

Este relatório registra a entrega local anterior ao envio ao GitHub. Publicação do
commit e implantação são etapas separadas; build local aprovado não comprova deploy
nem homologação em headset.
