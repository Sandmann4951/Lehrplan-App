# Unterrichtsassistent Bayern – lokaler Pilot (Variante A)

Lokale Webanwendung, mit der Lehrkräfte für **Deutsch und Mathematik, Klasse 1, Grundschule Bayern** passende Materialien finden und ihren Unterricht wochenweise planen. Ein zentraler Server verwaltet Benutzer, Lehrplanbezüge, PDF-Dateien und persönliche Klassenpläne in einer lokalen SQLite-Datenbank. Nach der Installation läuft die Anwendung **ohne Internet und ohne KI-Dienst**.

| Bereich | Umsetzung |
|---|---|
| Oberfläche | React 18 + TypeScript (Vite), responsiv ab 360 px, deutschsprachig, keine externen Ressourcen |
| Backend | FastAPI, SQLAlchemy 2 + Alembic-Migrationen, Repository-Schicht |
| Datenhaltung | SQLite (WAL, Fremdschlüssel aktiv, Busy-Timeout) + Materialverzeichnis im Datenvolume |
| Betrieb | Docker Compose, ein Anwendungsdienst, persistentes Volume, Skripte für start/stop/status/backup/restore |
| Sicherheit | Argon2id, serverseitige Sitzungen (8 h), HttpOnly/SameSite=Lax/Secure-Cookies, CSRF-Schutz, Login-Sperre |

## Schnellstart (Linux)

```bash
cp .env.example .env               # Standard: nur localhost
scripts/start.sh                   # baut und startet (docker compose up -d --build), Migrationen laufen automatisch
scripts/setup-admin.sh admin@schule.de "Vorname Nachname"   # Passwort wird abgefragt
scripts/seed.sh                    # Beispieldaten (idempotent)
```

Danach im Browser: <http://localhost:8000>. Weitere Lehrkräfte legt der Administrator unter **Verwaltung → Benutzer** an.

Alle Betriebsdetails (Windows mit Docker Desktop, LAN-Modus mit HTTPS, Sicherung, Wiederherstellung, Firewall): **[docs/BETRIEB.md](docs/BETRIEB.md)**.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/BETRIEB.md](docs/BETRIEB.md) | Installation, Start, LAN/HTTPS, Sicherung & Wiederherstellung, Datenschutzhinweise |
| [docs/BENUTZERHANDBUCH.md](docs/BENUTZERHANDBUCH.md) | Anleitung für Lehrkräfte und Administration |
| [docs/ABNAHME.md](docs/ABNAHME.md) | Abnahmeprotokoll A01–A12 mit Testdaten, Schritten und Ergebnissen |
| [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md) | Aufbau, Datenmodell, Regeln (Kalender, Planung, Empfehlungen), Entscheidungen |
| [docs/INHALTSPRUEFLISTE.md](docs/INHALTSPRUEFLISTE.md) | Prüfliste für die fachliche Freigabe der 30 Datensätze |
| [docs/EINSCHRAENKUNGEN.md](docs/EINSCHRAENKUNGEN.md) | Bekannte Einschränkungen des Piloten |
| [docs/openapi.json](docs/openapi.json) | OpenAPI-Vertrag (live unter `/api/v1/openapi.json`) |

## Projektstruktur

```
backend/            FastAPI-Anwendung
  app/api/          REST-Endpunkte unter /api/v1
  app/services/     Kalender, Bibliothek, Planung, Empfehlungen, Import, Sicherung
  app/repositories/ Datenzugriff (vorbereitet für PostgreSQL)
  app/seed/         Startinhalte + 10 Demo-Datensätze inkl. PDF-Generator
  alembic/          Migrationen
  tests/            Automatisierte Tests (Rechte, Kalender, Filter, Empfehlungen, Konflikte, Sicherung)
  tools/perf_test.py  Lasttest A11
frontend/           React-Oberfläche
scripts/            Betriebsskripte
docs/               Dokumentation
```

## Entwicklung

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.lock
python -m app.cli create-admin --email admin@schule.de
python -m app.cli seed
python -m app.cli serve --workers 1        # http://127.0.0.1:8000
pytest                                      # automatisierte Tests
python -m tools.perf_test                   # Lasttest A11

# Frontend (zweites Terminal, leitet /api an Port 8000 weiter)
cd frontend && npm ci && npm run dev        # http://127.0.0.1:5173
```

Die Demo-PDFs werden mit `python -m app.seed.pdfgen` deterministisch neu erzeugt.

## Lizenz und Inhalte

Die zehn Demonstrationsdatensätze sind selbst erstellt und ausdrücklich **nicht fachlich geprüft**. Für die Freigabe des Unterrichtspiloten verantwortet der Auftraggeber bzw. eine benannte Lehrkraft die vollständigen 30 Datensätze, Lizenzen und fachliche Prüfung (siehe Inhaltsprüfliste).
