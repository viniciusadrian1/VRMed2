# VRmed na CX33 — publicação em 30/09/2026 (UTC)

## Atualização da sala e ferramentas XR

A infraestrutura agora está integrada à árvore principal. A nova release inclui
a biblioteca de estudos e monitor integrado, preserva a sala clássica, e publica
recentralização, mira XR e transcrição. Consulte `docs/SALA-ESTUDOS-REVISAO.md`.
A seção "Máquina e versão" abaixo registra a **primeira implantação**, não a
imagem atual: obtenha a tag ativa com `docker ps --format '{{.Image}}'`.

Atualizações usam `publicar-atualizacao.sh preparar <SHA completo>` dentro de
`/opt/vrmed/releases/<SHA>`: build e testes, candidato em localhost:3001, sem
interromper o site. Após inspeção, `publicar-atualizacao.sh promover <SHA>` salva
Compose/Nginx em `/opt/vrmed/backups/deploy-<data>-<sha>`, troca a imagem e volta à
configuração anterior automaticamente se a promoção falhar. A troca reinicia o
processo; partidas em memória são interrompidas. Não executar durante uma partida.

O Nginx permite 2 MiB **somente** em `/api/transcricao`, sem buffering de upload
em disco, com limite próprio de 6/min/IP e 60/min/global. O aplicativo impõe
limites de bytes, concorrência e tempo; os demais corpos continuam em 512 KiB.
Áudio é enviado à OpenAI somente após gravação explícita e nunca vira pergunta
do tutor sem revisão/envio pelo aluno. Nenhuma chave entra no Git ou no build.

Retorno: restaurar os dois arquivos do diretório de backup, validar `nginx -t`,
executar Compose `up -d --no-build` e recarregar Nginx. As imagens antigas e o
arquivo persistente de feedback não são apagados pelo script. Não restaurar
credenciais nem feedback para reverter somente uma versão do aplicativo.

## Endereços

- Plataforma: https://2.28.109.190/
- Duelo: https://2.28.109.190/duelo
- Sala de estudos: https://2.28.109.190/sala
- Visualizador: https://2.28.109.190/viewer

O endereço usa certificado público de IP do Let's Encrypt, sem domínio comprado.
Não desative a validação TLS nem aceite certificados inseguros. Para colocar um
domínio próprio depois, ajustar DNS, certificado, Nginx e `NEXT_PUBLIC_SITE_URL`
no próximo build. O IP deve permanecer atribuído a esta máquina.

## Máquina e versão

- Hetzner: projeto VRMed `16211079`, servidor `vrmed-prod` / `168031840`.
- Falkenstein, CX33: 4 vCPU, 8 GB RAM, 80 GB SSD; Ubuntu 26.04.1 LTS.
- Valor aprovado na criação: US$ 9,99/mês + US$ 0,60/mês pelo IPv4, antes dos impostos.
- Código do GitHub: `0888dbb1814db62bc824dee9a108acba14cd0beb`.
- Arquivo de origem: SHA-256 `f059db3dba23f52f659761a654551e2b457d1b8aa07e3ac06b41fa0ced988adb`.
- Imagem em execução: `vrmed:cx33-0888dbb-1`.
- Manifesto da imagem: `sha256:728c684b23aa703344f43d133dbe8294cd0bfeefa2e973469ba5738f59e1cd3d`.
- Diretório da release: `/opt/vrmed/releases/0888dbb-cx33-1`.
- Docker 29.8.1 / Compose 5.5.1; Node 22; Next 16.2.6; Nginx 1.28.3.

A cópia de trabalho local está em `../vrmed-cx33`, isolada da árvore principal.
A criação de worktree pelo app falhou porque o diretório do chat é o pai do Git;
foi usado `git worktree add --detach` no repositório real. Não apagar esta cópia:
ela contém os novos arquivos de infraestrutura ainda não commitados.

Esta publicação **não inclui** a recentralização local da Sala nem a transcrição
incompleta. As alterações locais foram preservadas, sem publicação acidental.
Não houve commit/push, mudança de DNS nem alteração/desligamento da Vercel.

## Serviços e segurança

- Nginx escuta 80/443 e redireciona HTTP para HTTPS.
- O único contêiner web publica somente `127.0.0.1:3000`.
- Uma instância do Node: salas de Duelo em memória; reiniciar interrompe partidas.
- Aplicação como UID/GID 1001, sem capabilities, sem privilégios adicionais.
- Reinício `unless-stopped`, healthcheck, teto de 3 GiB e heap Node de 2 GiB.
- Logs Docker: três arquivos de 10 MB; access log Nginx desativado para não guardar
  conversas/identificadores presentes em URLs. Erros operacionais ficam no Nginx.
- SSH aceita chave; senha SSH desativada; senha root continua válida no console.
- UFW ativo: somente SSH, 80 e 443; Fail2ban/sshd e atualizações automáticas ativos.
- OpenAI reutilizada com autorização, em `/opt/vrmed/.env`, root:root, modo 600.
  Nunca usar `cat`, `docker inspect` completo nem `docker compose config` sem
  `--quiet` em saídas compartilhadas: podem revelar segredos.
- Limite do tutor: 6 requisições/minuto por IP, burst 6; global 60/minuto, burst 20.
  Turmas/eventos atrás do mesmo NAT compartilham o limite: revisar antes do evento.
  Esse limite reduz abuso, mas não substitui orçamento/cota no projeto OpenAI.
- O proxy sobrescreve IP encaminhado e remove `CF-Connecting-IP` do cliente.
- Corpo de requisição limitado a 512 KiB. Reavaliar ao publicar transcrição.
- `/admin` bloqueado externamente enquanto não houver senha administrativa.
- Spotify e analytics opcionais não foram configurados nesta migração.

## Certificado e renovação

- Certbot 5.8.0, imagem fixada por digest em `/opt/vrmed/certbot-image.txt`.
- Configuração: `/etc/letsencrypt/renewal/vrmed-ip.conf`.
- Certificado: `/etc/letsencrypt/live/vrmed-ip/fullchain.pem`.
- Certificado inicial válido até **06/10/2026 17:40:50 UTC**; validade curta esperada.
- `vrmed-certificado.timer`: verifica duas vezes ao dia, atraso aleatório até 30 min.
- `/opt/vrmed/renovar-certificado.sh`: renova e recarrega o Nginx.
- Webroot precisa ser montado com escrita para os desafios ACME. O script desativa
  a espera aleatória interna do Certbot porque o timer já distribui a execução.
- Teste do mesmo script com `--dry-run --non-interactive` passou. Renovação futura
  depende da máquina, timer, portas 80/443 e acesso ao Let's Encrypt disponíveis.

```sh
systemctl list-timers vrmed-certificado.timer
journalctl -u vrmed-certificado.service -n 30 --no-pager
/opt/vrmed/renovar-certificado.sh --dry-run --non-interactive
openssl x509 -noout -dates -in /etc/letsencrypt/live/vrmed-ip/fullchain.pem
```

Não executar `preparar-servidor.sh` ou `ativar-servicos.sh` como scripts de
atualização: registram a preparação inicial específica desta máquina/release.

## Feedback e backup

- Volume persistente: `/opt/vrmed/data/feedback.jsonl`, UID/GID 1001, modo 600.
- Montado em `/app/feedback.jsonl` no contêiner; não reside no código nem na imagem.
- `vrmed-backup.timer`: diariamente às 03:00 UTC, sete cópias locais rotativas em
  `/opt/vrmed/backups/feedback-dia-1.jsonl.gz` até `feedback-dia-7.jsonl.gz`.
- A chave OpenAI não é incluída nessas cópias de feedback.
- As cópias ficam **na mesma máquina**: não protegem contra perda completa do disco.
  Backups pagos da Hetzner/offsite não foram contratados.
- Dados anteriores da Vercel não foram exportados/importados. Histórico, notas e
  preferências salvos no navegador pertencem à origem antiga e não aparecem
  automaticamente neste IP; permanecem disponíveis na origem anterior.

## Operação

No PowerShell do computador autorizado:

```powershell
ssh root@2.28.109.190
```

Na máquina:

```sh
docker compose -f /opt/vrmed/compose.yml ps
docker stats --no-stream vrmed-web
docker logs --tail 50 vrmed-web
nginx -t
systemctl --failed
df -h /
```

Atualização: gerar uma release a partir de um commit revisado, construir imagem
com tag nova, rodar os testes, guardar a tag anterior, ajustar `image` no Compose
e executar `docker compose -f /opt/vrmed/compose.yml up -d --no-build` fora das
partidas. Não usar cluster/replicas nem copiar `.env` para a release. Se falhar,
voltar à tag anterior. A Vercel continua sendo uma alternativa independente;
jogadores de sites diferentes **não compartilham salas**.

## Validação executada

- `npm run lint`: zero erros; dois avisos existentes de eslint-disable sem efeito.
- `npm run verify:core`, `npm run build`, `npm run typecheck`: passaram em Linux.
- HTTP/SSE com dois jogadores: passou internamente e pelo HTTPS público/Nginx.
- Rotas `/`, `/duelo`, `/sala`, `/viewer`, `/clinica`, `/quiz`: HTTP 200 e header XR.
- Redirecionamento HTTP → HTTPS 308; arquivos ocultos negados; admin bloqueado.
- Hashes dos GLBs da Escola, Arena, crânio, coração, laringe e Draco conferidos.
- Tutor real com pergunta sintética, sem dados pessoais: HTTP 200, resposta em
  oito partes; conteúdo não registrado no teste.
- Limite de IA: dez payloads inválidos geraram 400 e depois 429, sem custo de IA.
- Desktop: Arena/Escola renderizadas; partida iniciada por teclado; resposta correta
  e feedback +100 observados. Console sem erros, com avisos preexistentes do Three
  (deprecações, extensão GLTF antiga e precisão de shader).
- Reinício do contêiner: HTTPS voltou a 200 e arquivo de feedback manteve inode,
  tamanho e permissão de escrita. Nenhum feedback sintético foi gravado na pesquisa.
- Timer de renovação e timer de backup ativos; nenhum serviço systemd com falha.
- Amostra ociosa após smoke tests: web ~62 MiB, CPU 0,01%; disco usado 6,1 GiB de
  75 GiB. **Não são benchmark nem garantia de capacidade com usuários concorrentes.**
- Headset físico e FPS do Quest não testados; o 3D continua sendo renderizado no
  dispositivo. Hospedar na CX33 não resolve por si só rasterização pesada dos painéis.

Comandos locais de verificação (o primeiro faz uma chamada real ao tutor):

```powershell
node infra/hetzner/verificar-publicacao.mjs
node infra/hetzner/verificar-duelo-publico.mjs
```

Referências oficiais consultadas:

- https://docs.docker.com/engine/install/ubuntu/
- https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability
- https://letsencrypt.org/2026/03/11/shorter-certs-certbot
- Documentação de self-hosting e `output` incluída no Next 16.2.6 instalado.
