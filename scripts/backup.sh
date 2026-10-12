#!/usr/bin/env bash
# Manuelle Sicherung erstellen und nach ./backups auf den Host kopieren.
# Die laufende Anwendung sperrt während des Snapshots Schreiboperationen (HTTP 503).
source "$(dirname "$0")/_common.sh"
mkdir -p backups
if [ -n "$($DC ps -q --status running app 2>/dev/null)" ]; then
  FILE=$($DC exec -T app python -m app.cli backup --kind manual | tail -n1 | tr -d '\r')
  $DC cp "app:$FILE" "backups/$(basename "$FILE")"
else
  FILE=$($DC run --rm --no-deps -v "$ROOT/backups:/export" app sh -c 'python -m app.cli backup --kind manual --output /tmp/export && cp /tmp/export/*.tar.gz /export/ && ls /tmp/export' | tail -n1 | tr -d '\r')
fi
echo "Sicherung erstellt: backups/$(basename "$FILE")"
echo "Bitte zusätzlich auf einen zweiten Datenträger kopieren (siehe docs/BETRIEB.md)."
