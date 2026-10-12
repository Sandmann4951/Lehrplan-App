# Bekannte Einschränkungen des Piloten

## Inhalte
- Geliefert sind **10 Demonstrationsdatensätze** (18 PDFs), nicht die 30 fachlich freigegebenen Datensätze für den Unterrichtspiloten (siehe [INHALTSPRUEFLISTE.md](INHALTSPRUEFLISTE.md)). Die Demo-Materialien sind technisch „freigegeben“, damit Suche und Empfehlungen geprüft werden können, werden aber überall als „Demo · nicht fachlich geprüft“ angezeigt.
- Die neun Lehrplanbezüge sind **sinngemäße Formulierungen** mit Abschnittscodes nach bestem Wissen und stehen auf „ungeprüft“. Abschnittscodes und Formulierungen sind gegen LehrplanPLUS zu prüfen.
- Die Kalenderdaten 2026/2027 (Unterrichtsbeginn 15.09.2026, Ende 30.07.2027, Ferien, Buß- und Bettag, Christi Himmelfahrt) sind **Vorbelegungen** und stehen auf „ungeprüft“ – nur zur Demonstration. Bewegliche Ferientage und schulinterne freie Tage fehlen.
- Die Pilotvorlagen decken ca. 17 (Deutsch) bzw. 17 (Mathematik) Unterrichtswochen ab, nicht das ganze Schuljahr. Themen werden in der Vorlage nacheinander, nicht parallel geplant.

## Funktionsumfang (bewusst nicht im Pilot)
- Keine Selbstregistrierung, keine Einladungs-E-Mails, kein Single Sign-on, keine Mandanten/Mehrschulbetrieb.
- Keine Uploads durch Lehrkräfte, keine Bewertungen, keine KI-Erstellung, keine gemeinsamen Kollegiumspläne.
- Keine PDF-Volltextsuche (Suche in Titel, Beschreibung, Schlagwörtern).
- Ältere Dateiversionen werden nicht aufbewahrt; Sicherungen enthalten den jeweiligen Stand.
- Drag-and-drop im Wochenplan ist nicht umgesetzt (optional laut Auftrag); Verschieben erfolgt per Datumsauswahl.
- Kein Mehrklassen-Vergleich und keine Druckansicht des gesamten Jahresplans (Browser-Druck des Wochenplans ist möglich).

## Technik und Betrieb
- **SQLite** ist für bis zu 20 Konten / 5 gleichzeitige Nutzer ausgelegt. Ein Wechsel auf PostgreSQL ist im Datenmodell vorbereitet, aber nicht implementiert; die Sicherungs-/Wiederherstellungsfunktion ist SQLite-spezifisch.
- Die Anwendung benötigt einen eingeschalteten Server. Zugriff von außen nur über VPN oder separat beauftragtes Hosting.
- LAN-Modus nutzt ein selbst erzeugtes Zertifikat; die CA muss auf allen Endgeräten installiert werden, sonst warnt der Browser.
- Die eingebettete PDF-Vorschau hängt vom Browser ab. Auf iPhone/Android wird häufig nur die erste Seite oder gar keine Vorschau angezeigt; dann „Öffnen“ bzw. „Herunterladen“ verwenden.
- Login-Sperre nach 10 Fehlversuchen gilt je Kombination aus E-Mail und IP-Adresse. Hinter einem Reverse-Proxy ohne Weitergabe der Client-IP würden alle Nutzer dieselbe IP teilen.
- Während einer Sicherung (wenige Sekunden) werden Schreibanfragen mit „Sicherung läuft“ (HTTP 503) abgewiesen und müssen wiederholt werden.
- Personen mit Betriebssystem-/Docker-Zugriff können Datenbank und Sicherungen technisch lesen (siehe Betriebsanleitung).
- Getestet wurden Chromium-basierte Browser bei 360, 390, 768, 1280 px und im Querformat sowie Tastaturbedienung (automatisiert). **Manuelle Tests in Safari (iPhone/iPad) und Chrome auf Android-Geräten stehen aus** und sind Teil der Abnahme vor Ort.
