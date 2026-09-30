#!/usr/bin/env bash
set -euo pipefail
# Certificado de IP dura poucos dias: executar automaticamente a cada 12 horas.
imagem=$(cat /opt/vrmed/certbot-image.txt)
docker run --rm --name vrmed-certbot-renovacao \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -v /var/www/vrmed-acme:/var/www/vrmed-acme \
  "$imagem" renew --quiet --no-random-sleep-on-renew "$@"
nginx -t
systemctl reload nginx
openssl x509 -checkend 86400 -noout -in /etc/letsencrypt/live/vrmed-ip/fullchain.pem
