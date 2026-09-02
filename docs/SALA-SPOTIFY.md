# Sala de Estudos — Spotify no rádio

Estado em 2026-09-02. O rádio 3D da Sala continua tocando o lo-fi local por padrão; o Spotify
é **opcional** e funciona como **controle remoto** (Spotify Connect pela Web API): quem
conectou a conta vê no rádio o que está tocando e usa os botões 3D para pausar, retomar e
pular faixa. O som sai do dispositivo escolhido no Spotify — celular, computador ou o
próprio app do Spotify do Quest (que desde 07/2025 toca em segundo plano no headset).

## Por que assim (regras do Spotify verificadas em 2026-09-02)

| Regra | Fonte | Consequência |
|---|---|---|
| App em *development mode* aceita **no máximo 5 usuários** cadastrados à mão (nome + e-mail) | developer.spotify.com/blog/2026-02-06, quota-modes | Serve ao grupo e à banca, não ao público de evento |
| O **dono** do app precisa manter **Premium**; se lapsar, o app para | guia de migração fev/2026 | Conta do grupo com Premium ativo |
| Extensão de quota só para empresas com ≥ 250 mil usuários mensais | blog 2025-04-15 | Sem caminho para "público geral" |
| Controlar reprodução (play/pause/next/transfer) exige **Premium do usuário**; ler o estado funciona em conta Free | referência Player; Policy IV.1 | Free vê "tocando agora", não controla |
| Redirect URI: HTTPS, ou loopback `http://127.0.0.1:porta` (`localhost` é rejeitado) | concepts/redirect_uri | Cadastrar `http://127.0.0.1:3000/sala` e `https://<site>/sala` |
| Web Playback SDK (som na própria página) exige script externo, Widevine e Premium; **não há confirmação** de funcionar no navegador do Quest | web-playback-sdk; docs Meta | Fica para um teste-piloto no headset; não entrou |
| Policy III.7: não mixar áudio do Spotify com outro áudio | Developer Policy 2025-05-15 | O lo-fi desliga quando o Spotify assume |
| Policy III.2: "não crie um jogo, incluindo quizzes" | Developer Policy 2025-05-15 | Risco de enquadramento (o VRmed tem /quiz e /duelo); o rádio fica só na Sala |
| Terms v10: uso pessoal, "Approved Devices" não cita headsets | Developer Terms 2025-05-15 | Uso não comercial de IC; registrar |
| LGPD: só os escopos necessários; política de privacidade visível; apagar dados ao desconectar | Terms Apêndice A; Policy I.1.2 | Sem e-mail/perfil; tokens só no navegador; "Desconectar" apaga |

## Configuração (uma vez, pelo grupo)

1. https://developer.spotify.com/dashboard → *Create app*. Redirect URIs: `http://127.0.0.1:3000/sala`
   e `https://<domínio do site>/sala`. API: *Web API*. Aceitar termos, salvar.
2. Copiar o **Client ID** para `.env.local` (`NEXT_PUBLIC_SPOTIFY_CLIENT_ID=…`) e para as variáveis
   de ambiente do Render. É público; não existe segredo no fluxo PKCE.
3. *Settings → User Management*: cadastrar os testadores (até 5) com o e-mail da conta Spotify.
4. Em desenvolvimento abrir o site por `http://127.0.0.1:3000/sala` (não `localhost`).

## Uso

1. Na tela 2D da Sala (antes de entrar em VR): **Conectar Spotify** → login no Spotify → volta
   para a Sala já conectado. O login precisa acontecer fora do VR: a navegação encerra a sessão.
2. Abrir o Spotify no celular, no computador ou no Quest e dar play em qualquer coisa.
3. Entrar em VR. O rádio mostra faixa e artista; clicar no rádio pausa/retoma; os botões
   `<<` e `>>` pulam faixa. Sem dispositivo ativo o rádio avisa "abra o Spotify… e dê play".
4. **Desconectar Spotify** apaga os tokens deste navegador.

## Código

- `lib/spotify.ts` — PKCE (authorize, troca do code, refresh), tokens em `localStorage`,
  chamadas à Web API com tratamento dos erros que importam (não testador, Premium, sem
  dispositivo, limite), evento `vrmed:spotify` ao conectar/desconectar.
- `components/sala/SalaApp.tsx` — botão Conectar/Desconectar e aviso de privacidade (DOM, fora
  do VR); conclui o login ao montar.
- `components/sala/SalaInterativos.tsx` — o rádio escuta o evento, sonda `/me/player` a cada 5 s
  enquanto conectado, mostra faixa/artista em Text3D e expõe os botões 3D.

## Pendências

- Logo do Spotify na atribuição 3D (as Design Guidelines pedem o logo, ≥ 21 px; hoje é texto
  "Spotify"). Baixar o asset oficial do kit de marca e aplicar como textura.
- Seletor de playlists no painel 3D (`playlists()` já existe em `lib/spotify.ts`).
- Teste-piloto do Web Playback SDK no Quest (1 h): open.spotify.com toca inteira? página mínima
  com o SDK dispara `ready`? clique no rádio dentro da sessão XR dá play sem `autoplay_failed`?
  Só então decidir se o som pode sair da própria página.
