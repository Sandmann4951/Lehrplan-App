#!/usr/bin/env bash
# Container-Status, Statusprüfung und vorhandene Sicherungen anzeigen.
source "$(dirname "$0")/_common.sh"
$DC ps
echo
if $DC exec -T app python -c "import json,urllib.request,ssl,os;s='https' if os.environ.get('TLS_CERT_FILE') else 'http';print(json.dumps(json.load(urllib.request.urlopen(f'{s}://127.0.0.1:8000/api/v1/health',context=ssl._create_unverified_context())),ensure_ascii=False))" 2>/dev/null; then
  echo
  echo "Sicherungen im Datenvolume:"
  $DC exec -T app python -m app.cli list-backups
else
  echo "Anwendung läuft nicht oder antwortet nicht."
fi
