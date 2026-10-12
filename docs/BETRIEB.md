# Betriebsanleitung

## 1. Voraussetzungen

- **Referenzsystem:** Linux-Rechner mit 2 CPU-Kernen, 4 GB RAM, SSD mit mindestens 10 GB freiem Speicher.
- Docker Engine ≥ 24 mit Compose-Plugin (`docker compose version`).
- Internetzugang nur für Erstinstallation und Aktualisierung (Docker-Images, Pakete). Der Laufzeitbetrieb ist vollständig offline: kein CDN, keine externen Schriften, kein externer PDF-Viewer, keine Telemetrie. Nur die Links zur Originalquelle des Lehrplans benötigen Internet; gespeicherte Kompetenzbezüge sind offline sichtbar.
- Der Server muss eingeschaltet sein, solange die Anwendung genutzt wird.

## 2. Installation (Linux)

```bash
git clone <Repository> unterrichtsassistent && cd unterrichtsassistent
cp .env.example .env
scripts/start.sh                     # entspricht: docker compose up -d --build
scripts/setup-admin.sh admin@schule.de "Vorname Nachname"
scripts/seed.sh                      # Beispieldaten, beliebig oft ausführbar
scripts/status.sh
```

- Der **Erststart** führt die Datenbankmigrationen automatisch aus.
- Es gibt **keine Standardzugangsdaten**. Der Erstadministrator wird ausschließlich über `setup-admin.sh` angelegt; das Passwort (mind. 10 Zeichen) wird interaktiv abgefragt.
- `seed.sh` legt nur fehlende Datensätze an (stabile IDs). Ein zweiter Lauf erzeugt keine Duplikate und überschreibt keine Änderungen.

### Windows (lokale Nutzung mit Docker Desktop)

1. Docker Desktop installieren (WSL-2-Backend aktivieren) und starten.
2. Projektordner entpacken, z. B. nach `C:\unterrichtsassistent`.
3. In **PowerShell** im Projektordner:
   ```powershell
   Copy-Item .env.example .env
   docker compose up -d --build
   docker compose run --rm --no-deps app python -m app.cli create-admin --email admin@schule.de
   docker compose run --rm --no-deps app python -m app.cli seed
   ```
4. Browser: <http://localhost:8000>.
5. Sicherung: `docker compose exec app python -m app.cli backup`, danach mit `docker compose cp app:/data/backups/<Datei> .\backups\` herausholen. Die Bash-Skripte unter `scripts/` laufen alternativ in Git Bash oder WSL.

Hinweis: Die Datenbank liegt im Docker-Volume `lehrplan-data`, **nicht** auf einem Netzlaufwerk. Bitte den Projektordner nicht auf ein Netzlaufwerk legen.

## 3. Betriebsskripte

| Skript | Zweck |
|---|---|
| `scripts/start.sh` | Bauen, starten, auf Statusprüfung warten |
| `scripts/stop.sh` | Anwendung stoppen (Daten bleiben erhalten) |
| `scripts/status.sh` | Container-Status, Health-Check, Liste der Sicherungen |
| `scripts/setup-admin.sh` | Erstadministrator anlegen |
| `scripts/seed.sh` | Beispieldaten laden (idempotent) |
| `scripts/backup.sh` | Manuelle Sicherung erstellen und nach `./backups/` kopieren |
| `scripts/restore.sh <Datei>` | Sicherung wiederherstellen (stoppt die Anwendung) |
| `scripts/make-cert.sh <Host> <IP>` | Zertifikate für den LAN-Modus erzeugen |

Logs: `docker compose logs -f app`.

## 4. Netzwerk: Einzelplatz und LAN-Modus

**Einzelplatz (Standard):** Der Server bindet nur an `127.0.0.1:8000`. Nur dieser Rechner erreicht die Anwendung.

**Mehrbenutzerbetrieb im Schulnetz (LAN-Modus)** wird ausdrücklich aktiviert und nur mit HTTPS betrieben:

1. Feste IP-Adresse bzw. DNS-Namen für den Server festlegen (z. B. `lehrplan-server`, `192.168.10.20`).
2. Zertifikate erzeugen:
   ```bash
   sudo scripts/make-cert.sh lehrplan-server 192.168.10.20
   ```
   Es entstehen `certs/ca.crt` (eigene Schul-CA), `certs/server.crt` und `certs/server.key`.
3. In `.env` aktivieren:
   ```
   BIND_ADDRESS=0.0.0.0
   TLS_CERT_FILE=/certs/server.crt
   TLS_KEY_FILE=/certs/server.key
   ```
4. `scripts/start.sh` – die Anwendung ist nun unter `https://lehrplan-server:8000` erreichbar; Cookies werden automatisch mit `Secure` gesetzt.
5. **Zertifikatsverfahren für Endgeräte:** `certs/ca.crt` auf jedem Endgerät als vertrauenswürdige Stammzertifizierungsstelle installieren:
   - Windows: Doppelklick → „Zertifikat installieren“ → „Lokaler Computer“ → „Vertrauenswürdige Stammzertifizierungsstellen“.
   - macOS: Schlüsselbundverwaltung → System → Datei importieren → „Immer vertrauen“.
   - iPhone/iPad: Datei per AirDrop/Mail öffnen → Profil installieren → *Einstellungen → Allgemein → Info → Zertifikatsvertrauenseinstellungen* → Vertrauen aktivieren.
   - Android: *Einstellungen → Sicherheit → Verschlüsselung → Zertifikat installieren → CA-Zertifikat*.
   - Alternativ kann ein vorhandenes Schulzertifikat (z. B. aus der Schul-PKI) in `certs/` abgelegt werden.
   Das Serverzertifikat ist 825 Tage gültig; zur Erneuerung `make-cert.sh` erneut ausführen (die CA bleibt erhalten).
6. **Firewall:** Eingehenden TCP-Port 8000 auf dem Server nur aus dem Lehrer-/Verwaltungsnetz freigeben (z. B. `ufw allow from 192.168.10.0/24 to any port 8000 proto tcp`). Im Schulnetz sind ggf. Freigaben durch den Netzwerkbetreuer nötig.

**Zugriff von außerhalb** ist erst mit eingerichtetem VPN oder einer separat beauftragten Hostinglösung möglich. Eine öffentliche Internetfreigabe gehört nicht zum Pilotauftrag.

## 5. Sicherung und Wiederherstellung

### Was gesichert wird
Jede Sicherung (`lehrplan-<art>-<Zeitstempel>.tar.gz`) enthält
- einen **konsistenten Datenbankstand**, erstellt über die SQLite-Backup-API (kein Kopieren der laufenden Datei),
- alle Materialdateien,
- `manifest.json` mit Software- und Schemaversion sowie SHA-256-Prüfsummen aller Dateien.

Während des Snapshots setzt die Sicherung eine Wartungssperre: schreibende Anfragen erhalten kurz HTTP 503 („Sicherung läuft“), Lesen bleibt möglich.

### Automatisch
Täglich um `BACKUP_TIME` (Standard 02:30 Uhr, Europe/Berlin) entsteht eine Sicherung im Datenvolume unter `/data/backups`. Es werden **14 Tagesstände** aufbewahrt (`BACKUP_KEEP`). Läuft der Server zur geplanten Zeit nicht, wird die Sicherung beim nächsten Start nachgeholt.

### Manuell / Export
```bash
scripts/backup.sh          # legt die Datei zusätzlich unter ./backups/ ab
```

### Zweiter Datenträger (Betriebsaufgabe)
Sicherungen im Datenvolume schützen nicht vor einem Plattendefekt. Mindestens wöchentlich und vor jedem Update `scripts/backup.sh` ausführen und den Ordner `./backups/` auf einen **zweiten Datenträger** (USB-Platte, NAS) kopieren, z. B.:
```bash
rsync -a backups/ /media/sicherung/unterrichtsassistent/
```
Den zweiten Datenträger getrennt aufbewahren. Verantwortliche Person und Rhythmus im Betriebsplan festhalten.

### Wiederherstellung
```bash
scripts/restore.sh backups/lehrplan-manual-20261012T130513Z.tar.gz
```
Ablauf: Anwendung stoppen → Manifest, Version und alle Prüfsummen prüfen → aktuellen Stand zusätzlich als `pre-restore`-Sicherung ablegen → Datenbank und Dateien **gemeinsam** ersetzen → ggf. Migrationen ausführen → Anwendung starten. Bei Prüfsummenfehlern wird nichts verändert.

### Wiederherstellungstest in leerem Verzeichnis (Nachweis)
```bash
cd backend
DATA_DIR=/tmp/restore-test python -m app.cli restore ../backups/<Datei>
DATA_DIR=/tmp/restore-test python -m app.cli serve --port 8001 --workers 1
```
Anmeldung, Pläne und Merkliste unter <http://127.0.0.1:8001> prüfen. Der automatisierte Test `tests/test_ops.py::test_a10_backup_restore_into_empty_environment` führt denselben Nachweis bei jedem Testlauf.

## 6. Aktualisierung

```bash
scripts/backup.sh                 # vorher sichern
git pull                           # oder neues Release entpacken
scripts/start.sh                   # baut neu, Migrationen laufen automatisch
```

## 7. Konfiguration (`.env`)

| Variable | Standard | Bedeutung |
|---|---|---|
| `BIND_ADDRESS` | `127.0.0.1` | Netzwerkschnittstelle auf dem Host; `0.0.0.0` nur im LAN-Modus |
| `HOST_PORT` | `8000` | Port auf dem Host |
| `TLS_CERT_FILE`, `TLS_KEY_FILE` | – | HTTPS aktivieren (LAN-Modus) |
| `SESSION_HOURS` | `8` | Sitzungsdauer |
| `MAX_UPLOAD_MB` | `20` | Maximale PDF-Größe |
| `BACKUP_AUTO` / `BACKUP_TIME` / `BACKUP_KEEP` | `true` / `02:30` / `14` | Tägliche Sicherung |
| `WORKERS` | `2` | Anzahl Serverprozesse (≈ Anzahl CPU-Kerne) |
| `API_DOCS` | `false` | Swagger-Oberfläche unter `/api/v1/docs` (benötigt Internet) |

## 8. Datenschutz- und Sicherheitshinweise

- Die Anwendung speichert **keine Schülernamen, Noten, Fotos oder Schülerkonten**. Lernstandskontrollen erfassen keine individuellen Ergebnisse.
- Passwörter werden ausschließlich als Argon2id-Hash gespeichert und nie protokolliert. Das Audit-Protokoll enthält keine Passwörter oder Sitzungstoken.
- Administratorrechte geben in Oberfläche und API **keinen** Zugriff auf persönliche Pläne anderer Lehrkräfte.
- **Offenlegung:** Personen mit Betriebssystem- oder Docker-Zugriff auf den Server können die Datenbank und die Sicherungsdateien technisch lesen (einschließlich der persönlichen Pläne). Der Kreis dieser Personen ist zu begrenzen und zu dokumentieren; Sicherungsdatenträger sind verschlossen aufzubewahren.
- Benutzerdaten verbleiben lokal. Es werden keine Daten an Dritte übertragen; im Piloten werden keine API-Schlüssel benötigt.
- Login-Schutz: höchstens 10 Fehlversuche je Konto und IP in 15 Minuten, danach zeitlich begrenzte Sperre. Gesperrte Benutzer verlieren sofort alle Sitzungen.

## 9. API-Dokumentation

Der OpenAPI-Vertrag liegt unter `docs/openapi.json` und ist im laufenden Betrieb unter `/api/v1/openapi.json` abrufbar. Die interaktive Swagger-Oberfläche (`/api/v1/docs`) lädt Skripte aus dem Internet und ist deshalb standardmäßig abgeschaltet; zum Aktivieren `API_DOCS=true` in `.env` setzen (nur für Entwicklung/Abnahme mit Internetzugang).
