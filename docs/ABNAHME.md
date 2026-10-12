# Abnahmeprotokoll Variante A (technische Abnahme)

Stand: 12.10.2026 · Software 0.1.0 · Schema 0001 · Durchführung: Entwickler (Vorabnahme)

Testumgebung der Vorabnahme: Linux-Container, 4 CPU-Kerne (Lasttest zusätzlich auf 2 Kerne begrenzt), Docker 29, Chromium (Playwright). Die Abnahme auf dem Referenzsystem des Auftraggebers und die Gerätetests (iPhone/iPad/Android) stehen aus – Spalte „Abnahme vor Ort“.

Automatisierte Nachweise: `cd backend && pytest` (53 Tests) und `python -m tools.perf_test`.

| ID | Prüfung | Testdaten / Schritte | Erwartet | Ergebnis Vorabnahme | Abnahme vor Ort |
|---|---|---|---|---|---|
| A01 | Installation, Admin, Seed | `scripts/start.sh` (bzw. `docker compose up -d`), `setup-admin.sh`, `seed.sh` zweimal | Anwendung läuft, Admin angelegt, zweiter Seed ohne Duplikate | ✔ Container „healthy“, zweiter Seed meldet 0 neue Datensätze (10 Themen, 10 Materialien, 18 Dateien). Test `test_a01_seed_idempotent` | ☐ |
| A02 | Zugriffsschutz zwischen Lehrkräften | Lehrkraft A legt Klasse, Einheit, Favorit an; B ruft Liste, Detail, Units, Dashboard, Empfehlungen, PATCH/DELETE, Initialisierung, Favoriten direkt per API auf | B sieht/ändert nichts (404), A unverändert; Admin sieht A's Pläne ebenfalls nicht | ✔ `test_a02_isolation_between_teachers`, `test_admin_has_no_access_to_teacher_plans` | ☐ |
| A03 | Suche Fach + Thema + Niveau | Fach M, Thema „Zahlen bis 10 zerlegen“, Niveau differenziert; zusätzlicher Entwurf zum selben Thema | nur „Zahlen zerlegen“ (freigegeben); Entwürfe/Archiv nicht sichtbar | ✔ `test_a03_…`, `test_archived_not_in_search`, UND/ODER-Logik `test_filters_and_or_semantics_and_paging` | ☐ |
| A04 | Dateien | Arbeitsblatt + Lösung öffnen/herunterladen; Datei-URL ohne Login; PNG-Upload; Upload ohne PDF-Signatur; Upload > 20 MB; Pfad `../../etc/passwd.pdf` | getrennt inline/attachment; 401; 415; 415; 413; 422 | ✔ `test_a04_*`; manuell: inline/attachment-Header, ohne Login 401 | ☐ |
| A05 | Kalender | Schuljahr ab Mi 16.09.2026, Ferien 21.–25.09., Jahreswechsel 2026/27 | Teilwoche = UW 1 (verkürzt, 3 Tage), Ferienwoche ohne Nummer, nächste Woche = UW 2; 28.12.2026 = KW 53/2026, 04.01.2027 = KW 1/2027 | ✔ `test_a05_school_year_starting_wednesday`, `test_a05_year_change_iso_week` + 6 weitere Kalendertests | ☐ |
| A06 | Vorlage, Verschieben, Abschließen | Plan aus Vorlage für A und B; eine Einheit von A verschieben (Datum Mi → Montag) und abschließen | nur die gewählte Einheit ändert sich; B unverändert; Überplanungswarnung; fehlendes Material wird angezeigt | ✔ `test_a06_…`, `test_missing_materials_shown`, `test_free_week_warning`; UI: Verschieben per Datumsfeld bei 360–1280 px | ☐ |
| A07 | Empfehlungen | 3 Zusatzmaterialien (mit/ohne gemeinsamen Bezug, Entwurf), Niveau „basis“, zweifacher Aufruf | 125 / 120 / 105 Punkte in dieser Reihenfolge, Entwurf fehlt, identische Reihenfolge; Ferienwoche wird nicht befüllt | ✔ `test_a07_scores_and_determinism`, `test_recommendations_free_week_and_fallback`, `test_max_five_per_subject` | ☐ |
| A08 | Versionskonflikt | Zwei Browser (1280 px und 390 px) öffnen dieselbe Einheit, Browser 1 speichert, dann Browser 2 | Browser 2 erhält 409, Hinweis „Versionskonflikt“, Optionen Neu laden / erneut speichern; kein stiller Verlust | ✔ API `test_a08_version_conflict`; UI-Test (Playwright): Konfliktdialog erscheint, „Änderungen behalten und erneut speichern“ speichert Browser-2-Stand | ☐ |
| A09 | Neustart und Offline | Server stoppen/starten; Login, Plan, Merkliste, Vorschau, Download | alles verfügbar, Änderungen erhalten; keine externen Ressourcen | ✔ nach Neustart: Login 200, Plan/Notizen erhalten, Merkliste erhalten, PDF inline + Download; Frontend-Build ohne externe URLs (nur XML-Namespaces und Lehrplan-Quelllinks) | ☐ (Netzwerkkabel ziehen) |
| A10 | Sicherung & Wiederherstellung | Backup, Testdaten ändern, Restore in **leerer** Umgebung | Benutzer, Pläne, Datei-Prüfsummen = gesicherter Stand | ✔ `test_a10_backup_restore_into_empty_environment`; Docker: `backup.sh` → Klasse anlegen → `restore.sh` → Klasse wieder entfernt, `pre-restore`-Sicherung angelegt; manipulierte Sicherung wird abgewiesen | ☐ |
| A11 | Last | 1.000 Materialien, 5 parallele Benutzer, 100 Aktionen (Suche, Dashboard, Planspeichern), ohne Dateiübertragung | p95 < 2 s | ✔ auf 2 Kerne begrenzt (`taskset -c 0,1`), 2 Worker: Suche p95 100 ms, Dashboard p95 216 ms, Planspeichern p95 103 ms | ☐ (Referenzsystem) |
| A12 | Responsiv, Touch, Tastatur | 360×740, 390×844, 768×1024, 1280×800, 844×390 (quer): Login, Filter, PDF öffnen, Favoriten, Planverschiebung, Menü | kein horizontales Scrollen; Touchflächen ≥ 44×44; per Tastatur bedienbar | ✔ Playwright/Chromium: horizontaler Überlauf 0 px auf allen Ansichten, keine Bedienelemente < 44 px; Tastatur: Login, Navigation zu „Verschieben“, Fokus im Datumsfeld, Escape schließt Dialog | ☐ Safari iPhone/iPad, Chrome Android, Firefox/Edge Desktop |

## Weitere Nachweise
- Sicherheit: Argon2id-Hash (`test_password_hash_is_argon2id`), Cookie-Flags HttpOnly/SameSite=Lax/Max-Age 8 h (`test_cookie_flags`), `Secure` im HTTPS-Betrieb (manuell geprüft mit `make-cert.sh`), CSRF (`test_csrf_required_for_writes`), Login-Sperre (`test_login_rate_limit`), gesperrte Benutzer verlieren Sitzungen (`test_locked_user_sessions_invalidated`), Passwort-Reset mit Wechselpflicht (`test_reset_password_forces_change`), Audit ohne Geheimnisse.
- Freigabeprozess: Freigabe ohne geprüfte Kompetenzreferenz / Hauptdatei wird abgewiesen (`test_release_workflow_requires_checks`).
- Wartungssperre während Sicherung: Schreiben → 503, Lesen → 200 (`test_maintenance_lock_blocks_writes`).
- Importe: Kalender-JSON mit Vorschau und Fehlerliste, Inhaltsimport als Entwurf (`test_calendar_import_preview_and_apply`, `test_content_import_creates_drafts`).

## Abnahmeentscheidung
☐ Technische Abnahme erteilt  ☐ mit Auflagen  ☐ nicht erteilt

Ort, Datum, Unterschrift Auftraggeber: ______________________
