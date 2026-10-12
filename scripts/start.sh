#!/usr/bin/env bash
# Anwendung bauen (falls nötig) und starten. Migrationen laufen beim Start automatisch.
source "$(dirname "$0")/_common.sh"
$DC up -d --build
echo "Warte auf Statusprüfung …"
for i in $(seq 1 30); do
  if $DC exec -T app python -c "import urllib.request,ssl,os;s='https' if os.environ.get('TLS_CERT_FILE') else 'http';urllib.request.urlopen(f'{s}://127.0.0.1:8000/api/v1/health',context=ssl._create_unverified_context())" >/dev/null 2>&1; then
    echo "Anwendung läuft: http(s)://localhost:${HOST_PORT:-8000}"
    exit 0
  fi
  sleep 2
done
echo "Anwendung antwortet nicht. Logs: $DC logs app" >&2
exit 1
