#!/usr/bin/env bash
set -euo pipefail
# Executar apenas na CX33 do VRmed, a partir de uma release extraída de git archive.
# Preserva imagem anterior, configuração, chave e arquivo persistente de feedback.
test "$(hostname)" = vrmed-prod
fase=${1:?Informe preparar ou promover}
revisao=${2:?Informe o SHA completo do commit}
[[ "$revisao" =~ ^[a-f0-9]{40}$ ]]
release="/opt/vrmed/releases/$revisao"
test "$(pwd -P)" = "$release"
test -f Dockerfile
test -f /opt/vrmed/.env
imagem="vrmed:cx33-${revisao:0:12}"

saudavel() {
  for tentativa in $(seq 1 45); do
    estado=$(docker inspect --format '{{.State.Health.Status}}' "$1")
    if [ "$estado" = healthy ]; then return 0; fi
    if [ "$estado" = unhealthy ]; then return 1; fi
    sleep 2
  done
  return 1
}

if [ "$fase" = preparar ]; then
  # Nada da produção é interrompido durante build/testes.
  if docker container inspect vrmed-candidato >/dev/null 2>&1; then
    echo 'Já existe um candidato; inspecione antes de continuar.' >&2; exit 1
  fi
  docker build --label "org.opencontainers.image.revision=$revisao" -t "$imagem" .
  docker run -d --name vrmed-candidato --init \
    --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 3g --cpus 3 \
    --env-file /opt/vrmed/.env -e NODE_OPTIONS=--max-old-space-size=2048 \
    -p 127.0.0.1:3001:3000 "$imagem"
  saudavel vrmed-candidato
  for rota in / /sala /sala?versao=classica /duelo /viewer /models/props/sala-estudos-revisao.glb /models/props/monitor-estudos-revisao.glb; do
    curl -fsS -o /dev/null "http://127.0.0.1:3001$rota"
  done
  echo 'Candidato saudável; produção permanece na imagem anterior.'
elif [ "$fase" = promover ]; then
  test "$(docker inspect --format '{{.Config.Image}}' vrmed-candidato)" = "$imagem"
  saudavel vrmed-candidato
  backup="/opt/vrmed/backups/deploy-$(date -u +%Y%m%dT%H%M%SZ)-${revisao:0:12}"
  install -d -m 0700 "$backup"
  cp -p /opt/vrmed/compose.yml "$backup/compose.yml"
  cp -p /etc/nginx/sites-available/vrmed "$backup/nginx.conf"
  sed -E "s@^(    image:).*@\1 $imagem@" /opt/vrmed/compose.yml > "$backup/compose-novo.yml"
  docker compose -f "$backup/compose-novo.yml" config --quiet
  restaurar() {
    install -m 0600 "$backup/compose.yml" /opt/vrmed/compose.yml
    install -m 0644 "$backup/nginx.conf" /etc/nginx/sites-available/vrmed
    docker compose -f /opt/vrmed/compose.yml up -d --no-build
    nginx -t && systemctl reload nginx
    echo "Falha na promoção; configuração anterior restaurada de $backup" >&2
  }
  trap restaurar ERR
  install -m 0644 infra/hetzner/nginx.conf /etc/nginx/sites-available/vrmed
  nginx -t
  install -m 0600 "$backup/compose-novo.yml" /opt/vrmed/compose.yml
  docker compose -f /opt/vrmed/compose.yml up -d --no-build
  saudavel vrmed-web
  systemctl reload nginx
  curl -fsS -o /dev/null https://2.28.109.190/sala
  trap - ERR
  # Contêiner temporário não tem dados reais nem volume persistente.
  docker stop vrmed-candidato >/dev/null
  docker rm vrmed-candidato >/dev/null
  echo "Publicação concluída: $imagem"
  echo "Retorno disponível em: $backup"
else
  echo 'Fase inválida.' >&2; exit 1
fi
