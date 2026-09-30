#!/usr/bin/env bash
set -euo pipefail
origem=/opt/vrmed/releases/0888dbb-cx33-1/infra/hetzner
test -f /etc/letsencrypt/live/vrmed-ip/fullchain.pem
test -f /opt/vrmed/.env
install -m 0600 "$origem/compose.yml" /opt/vrmed/compose.yml
docker compose -f /opt/vrmed/compose.yml config --quiet
docker compose -f /opt/vrmed/compose.yml up -d --no-build
for tentativa in $(seq 1 30); do
  if curl -fsS -o /dev/null http://127.0.0.1:3000/; then break; fi
  sleep 1
done
curl -fsS -o /dev/null http://127.0.0.1:3000/
cp -p /etc/nginx/sites-available/vrmed /etc/nginx/sites-available/vrmed.pre-https
install -m 0644 "$origem/nginx.conf" /etc/nginx/sites-available/vrmed
if ! nginx -t; then
  cp -p /etc/nginx/sites-available/vrmed.pre-https /etc/nginx/sites-available/vrmed
  exit 1
fi
systemctl reload nginx
install -m 0700 "$origem/renovar-certificado.sh" /opt/vrmed/renovar-certificado.sh
install -m 0700 "$origem/backup-feedback.sh" /opt/vrmed/backup-feedback.sh
install -m 0644 "$origem"/vrmed-certificado.{service,timer} "$origem"/vrmed-backup.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vrmed-certificado.timer vrmed-backup.timer
systemctl start vrmed-certificado.service vrmed-backup.service
systemctl list-timers vrmed-certificado.timer vrmed-backup.timer
docker compose -f /opt/vrmed/compose.yml ps
