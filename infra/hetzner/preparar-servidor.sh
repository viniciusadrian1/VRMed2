#!/usr/bin/env bash
set -euo pipefail
# Preparação inicial da CX33 exclusiva do VRmed. Não altera dados de outras aplicações.
test "$(hostname)" = vrmed-prod
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl nginx unattended-upgrades
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod 0644 /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: %s\nComponents: stable\nArchitectures: amd64\nSigned-By: /etc/apt/keyrings/docker.asc\n' "$VERSION_CODENAME" > /etc/apt/sources.list.d/docker.sources
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker nginx unattended-upgrades
install -d -m 0700 /opt/vrmed /opt/vrmed/releases /opt/vrmed/backups
install -d -m 0755 /var/www/vrmed-acme
install -d -m 0700 -o 1001 -g 1001 /opt/vrmed/data
if [ ! -e /opt/vrmed/data/feedback.jsonl ]; then
  install -m 0600 -o 1001 -g 1001 /dev/null /opt/vrmed/data/feedback.jsonl
fi
# Mantém o acesso SSH por chave e a senha de recuperação no console da Hetzner.
printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin prohibit-password\n' > /etc/ssh/sshd_config.d/00-vrmed.conf
sshd -t
systemctl reload ssh
ufw status
docker --version
docker compose version
