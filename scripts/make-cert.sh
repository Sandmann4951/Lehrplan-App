#!/usr/bin/env bash
# Erzeugt eine lokale Zertifizierungsstelle (CA) und ein Serverzertifikat für den LAN-Modus.
# Aufruf: scripts/make-cert.sh <Hostname> <IP-Adresse>
#   z. B.  scripts/make-cert.sh lehrplan-server 192.168.10.20
# Danach certs/ca.crt auf den Endgeräten als vertrauenswürdig installieren (siehe docs/BETRIEB.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOSTNAME_="${1:?Hostname angeben}"
IP="${2:?IP-Adresse angeben}"
mkdir -p "$ROOT/certs"
cd "$ROOT/certs"
if [ ! -f ca.key ]; then
  openssl req -x509 -newkey rsa:3072 -sha256 -days 3650 -nodes -keyout ca.key -out ca.crt -subj "/CN=Unterrichtsassistent Schul-CA"
fi
openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/CN=$HOSTNAME_"
cat > server.ext <<EXT
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:$HOSTNAME_,DNS:localhost,IP:$IP,IP:127.0.0.1
EXT
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 825 -sha256 -extfile server.ext
rm -f server.csr server.ext
chmod 600 ca.key
# Der Container läuft als UID 10001 und muss den Serverschlüssel lesen können.
if [ "$(id -u)" = "0" ]; then chown 10001:10001 server.key; chmod 600 server.key; else chmod 644 server.key; echo "Hinweis: server.key ist für alle lesbar (kein root). Zugriff auf den Ordner certs/ einschränken."; fi
echo "Zertifikat erstellt: certs/server.crt (gültig 825 Tage). CA für Endgeräte: certs/ca.crt"
