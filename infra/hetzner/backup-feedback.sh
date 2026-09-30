#!/usr/bin/env bash
set -euo pipefail
umask 077
# Sete cópias locais rotativas. Não substituem backup externo da máquina.
dia=$(date +%u)
test -f /opt/vrmed/data/feedback.jsonl
gzip -c /opt/vrmed/data/feedback.jsonl > "/opt/vrmed/backups/feedback-dia-${dia}.jsonl.gz.novo"
mv "/opt/vrmed/backups/feedback-dia-${dia}.jsonl.gz.novo" "/opt/vrmed/backups/feedback-dia-${dia}.jsonl.gz"
