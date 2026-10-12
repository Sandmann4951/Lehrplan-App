#!/usr/bin/env bash
# Sicherung wiederherstellen. Die Anwendung wird dafür gestoppt.
# Ablauf: Version und Prüfsummen prüfen, aktuellen Stand zusätzlich sichern,
# Datenbank und Dateien gemeinsam ersetzen, Anwendung neu starten.
# Aufruf: scripts/restore.sh backups/lehrplan-manual-YYYYMMDDTHHMMSSZ.tar.gz
source "$(dirname "$0")/_common.sh"
ARCHIVE="${1:?Pfad zur Sicherung (tar.gz) angeben}"
[ -f "$ARCHIVE" ] || { echo "Datei nicht gefunden: $ARCHIVE" >&2; exit 1; }
DIR="$(cd "$(dirname "$ARCHIVE")" && pwd)"
NAME="$(basename "$ARCHIVE")"
read -r -p "Aktuellen Stand durch $NAME ersetzen? Die Anwendung wird gestoppt. [ja/NEIN] " ANSWER
[ "$ANSWER" = "ja" ] || { echo "Abgebrochen."; exit 1; }
$DC stop app || true
$DC run --rm --no-deps -v "$DIR:/restore:ro" app python -m app.cli restore "/restore/$NAME" --force
$DC start app
echo "Wiederherstellung abgeschlossen. Bitte Anmeldung und Pläne stichprobenartig prüfen."
