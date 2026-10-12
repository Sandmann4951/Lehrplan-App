# Architektur und fachliche Regeln

## Aufbau

```
Browser ──HTTP(S)──▶ Uvicorn (FastAPI, 2 Worker) ──▶ Services ──▶ Repository-Schicht ──▶ SQLite (WAL)
                         │                                                     └──▶ /data/materials (PDF, generierte Schlüssel)
                         └── ausgelieferter Frontend-Build (statisch, gleiche Origin)
```

- Die Datenbank liegt ausschließlich im Datenverzeichnis des Servers (`/data`, Docker-Volume), außerhalb des Frontend-Verzeichnisses. Clients öffnen die Datei nie direkt.
- SQLite: `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000 ms`; Schreibvorgänge sind kurze Transaktionen je Anfrage.
- Getrennte Services: `library` (Suche, Sichtbarkeit, Dateiablage), `planning` (Vorlagenkopie, Kapazität, Warnungen), `recommendations` (Punkteverfahren, ohne KI), `calendar` (reine Kalenderregeln), `backup`, `importer`.
- Repository-Schicht (`app/repositories`) kapselt Abfragen; alle Abfragen sind dialektneutrales SQLAlchemy.
- Mehrere Worker-Prozesse (Standard 2) vermeiden GIL-Engpässe bei parallelen Nutzern. Die tägliche Sicherung läuft per Dateisperre nur in einem Prozess.

### Entscheidungen und Alternativen

| Thema | Entscheidung | Begründung / Alternative |
|---|---|---|
| Stack | React + TypeScript, FastAPI, SQLAlchemy + Alembic, SQLite | wie im Auftrag vorgeschlagen |
| PostgreSQL-Fähigkeit | UUIDs als Text, keine SQLite-spezifischen SQL-Konstrukte, Zeitstempel als UTC | Wechsel erfordert neue `DATABASE_URL`, Migration ausführen, Daten übertragen; Sicherungs-Skripte sind SQLite-spezifisch |
| Sitzungen | serverseitige Tabelle `sessions`, nur SHA-256 des Tokens gespeichert | JWT verworfen (keine sofortige Sperrung möglich) |
| CSRF | synchronisiertes Token je Sitzung, Header `X-CSRF-Token` | zusätzlich SameSite=Lax |
| PDF-Vorschau | eingebauter PDF-Viewer des Browsers (`<object>`), Fallback-Link | kein externer Viewer (Offline-Pflicht) |
| Router | react-router 6, keine UI-Bibliothek | geringe Abhängigkeiten, volle Kontrolle über Touchflächen |
| Demo-PDFs | mit ReportLab erzeugt und eingecheckt (`app/seed/pdfs`) | reproduzierbar (`python -m app.seed.pdfgen`) |

## Datenmodell

Alle Entitäten: UUID `id`, `created_at`, `updated_at` (UTC). Veränderbare Datensätze: Integer `version` für Konfliktprüfung (HTTP 409). Fremdschlüssel und Unique-Constraints sind Teil der Migration `0001`. Referenzierte Stammdaten werden archiviert statt gelöscht (`ON DELETE RESTRICT`).

| Tabelle | Wichtige Felder / Regeln |
|---|---|
| `users` | `email` eindeutig (normalisiert), `password_hash` (Argon2id), `role`, `active`, `must_change_password` |
| `sessions` | `user_id`, `token_hash`, `csrf_token`, `expires_at` |
| `login_attempts` | Fehlversuche je E-Mail + IP (Sperre nach 10 in 15 min) |
| `school_years` | `label`, `starts_on`, `ends_on` (Check Ende ≥ Beginn) |
| `calendar_closures` | `kind` (Ferien/Feiertag/schulfrei/Sondertag), `source`, `reviewed_at`, `review_status`; Überlappungen werden vereinigt |
| `subjects`, `topics`, `topic_prerequisites` | Fach-Code eindeutig; Thema je Fach eindeutig; Voraussetzungen M:N |
| `curriculum_references` | `official_grade_band`, `section_code`, `paraphrased_goal`, `source_url`, `source_version`, `retrieved_on`, `verification_status`, `reviewer_id` |
| `materials` (+ `material_curriculum`) | Typ, Niveau, Dauer > 0, Autor, Lizenz, Status, `is_demo`, Prüfer + Prüfdatum |
| `material_files` | `purpose` main/solution (je einmal), `storage_key` (generiert), `sha256`, `size_bytes` |
| `plan_templates`, `template_units` (+ M:N) | geordnete Einheiten mit `estimated_lessons` |
| `classes`, `class_subject_hours` | Pilot-Checks: Klasse 1, BY, Grundschule; `weekdays` (0 = Montag); Stunden je Fach |
| `plan_units` (+ M:N Material/Kompetenz) | `week_start_date` (Montag), `planned_lessons` > 0, Status geplant/begonnen/abgeschlossen |
| `favorites` | `user_id` + `material_id` eindeutig |
| `audit_events` | Akteur, Aktion, Objekt, Zeitpunkt, Details ohne Geheimnisse |

## Kalenderregeln (F05)

- Fachzeit Europe/Berlin; Zeitstempel in UTC, Unterrichtsdaten als ISO-Datum.
- Wochen laufen Montag–Sonntag. ISO-Kalenderwoche und Unterrichtswoche sind getrennte Angaben.
- **Vorgesehener Unterrichtstag** = gewählter Klassenwochentag innerhalb des Schuljahrs, der in keinem Ferien-/schulfreien Intervall liegt (Grenzen einschließlich).
- Die erste Woche mit mindestens einem Unterrichtstag ist **Unterrichtswoche 1**. Vollständig freie Wochen zählen nicht; teilweise freie Wochen zählen und sind „verkürzt“. Außerhalb des Schuljahrs gibt es keine Unterrichtswochenzahl.
- **Verkürzte Wochenkapazität** = ⌊Wochenstunden × aktive Tage / reguläre Tage⌋.
- Ungeprüfte Kalendereinträge sind nutzbar, werden aber überall als „nur Demo“ gekennzeichnet.

## Planung (F06)

- Vorlagenkopie nur mit `confirm: true`; ein nicht leerer Plan wird nur mit `replace_existing: true` ersetzt (sonst Fehler `plan_not_empty`).
- Verteilung: Einheiten je Fach in Vorlagenreihenfolge, Woche für Woche bis zur jeweiligen (ggf. verkürzten) Kapazität; lange Einheiten erhalten mehrere Planeinträge. Freie Wochen bleiben leer.
- Spätere Vorlagenänderungen wirken nicht auf bestehende Pläne. Kalenderänderungen berechnen Wochenangaben neu, verschieben aber keine Einheiten.
- Verschieben per Datumsauswahl (auf Montag normalisiert). Vor dem Speichern prüft `POST /classes/{id}/units/check` auf Überplanung und vollständig freie Zielwochen; die Lehrkraft entscheidet.
- Änderungen werden erst nach erfolgreicher Serverantwort angezeigt. Veraltete `version` → 409; die Oberfläche bietet „Neu laden“ oder „Änderungen behalten und erneut speichern“.

## Empfehlungen (F07)

Für Klasse und Woche, je Fach:
1. Kandidaten: nur **freigegebene** Materialien im passenden Jahrgang und Fach, deren Thema in dieser Woche **eingeplant** ist (Voraussetzung, 100 Punkte).
2. +20 Punkte bei mindestens einem gemeinsamen Kompetenzbezug mit der geplanten Einheit, +5 bei gewähltem Niveau.
3. Sortierung: Punkte absteigend, dann Titel, dann ID – deterministisch. Höchstens fünf je Fach, jeweils mit Begründung.
4. Ist kein Thema eingeplant: nächstes offenes Thema aus dem persönlichen Plan als ausdrücklich gekennzeichneter Vorschlag (wird nicht eingeplant). Sonst Leerzustand mit Link zur Bibliothek.
5. Eine Kalenderwoche allein bestimmt nie ein Thema.

## Lehrplanbezug (Kapitel 7)

Die Anwendung unterscheidet sichtbar:
- **Offizieller Kompetenzbezug**: `curriculum_references` (LehrplanPLUS, Jgst. 1/2, sinngemäß, mit Quelle und Abrufdatum, Prüfstatus).
- **Interne Themenauswahl**: `topics` (pädagogische Pilotplanung, Reihenfolge, Voraussetzungen, Planungsnotiz).
- **Zeitliche Planung**: `plan_templates` und persönliche `plan_units`.

## API

REST unter `/api/v1`, JSON (Multipart für PDF-Uploads). Listen: `{items, total, page, page_size}`. Fehler: `{code, message, field_errors}`. Statuscodes: 401 fehlende Anmeldung, 403 unzulässige Rollenaktion/CSRF, 404 auch für fremde persönliche Objekte, 409 Versionskonflikt, 413/415 Upload, 422 ungültige Eingabe, 429 Login-Sperre, 503 Wartung (Sicherung). Vollständiger Vertrag: [openapi.json](openapi.json), maschinenlesbar unter `/api/v1/openapi.json`; die interaktive Swagger-Oberfläche `/api/v1/docs` lädt Skripte aus dem Internet und wird nur mit `API_DOCS=true` aktiviert.

## Übernahme aus der Artifacts-Demo (Variante B)

`POST /api/v1/admin/import/content` akzeptiert `schema_version`, `topics`, `curriculum`, `materials` (weitere Schlüssel wie `classes`, `units`, `favorites` werden ignoriert). Materialien werden immer als **Entwurf** importiert; Dateien werden separat hochgeladen. Vorschau (`dry_run=true`) liefert eine Fehlerliste mit Pfadangaben.
