# Benutzerhandbuch

Die Anwendung läuft im Browser auf Computer, Tablet und Smartphone. Eine App-Installation ist nicht nötig. Die Adresse erhalten Sie von Ihrer Administration (z. B. `https://lehrplan-server:8000`).

## Für Lehrkräfte

### Anmelden
- E-Mail und Passwort eingeben. Nach einem Zurücksetzen durch die Administration vergeben Sie beim ersten Login ein eigenes Passwort (mind. 10 Zeichen).
- Die Sitzung endet nach 8 Stunden automatisch. **Abmelden** finden Sie im Menü (auf dem Smartphone über ☰).
- Unter **Konto** können Sie Ihr Passwort ändern.

### Klasse anlegen
**Klassen → + Klasse anlegen**: Name (z. B. „1a“), Schuljahr, Unterrichtswochentage und Wochenstunden je Fach (Vorschlag: Deutsch 7, Mathematik 5). Jahrgangsstufe 1, Bayern und Grundschule sind im Pilot fest eingestellt. Ihre Klassen und Pläne sieht niemand außer Ihnen – auch nicht die Administration.

### Plan aus der Vorlage anlegen
Auf der **Übersicht** oder im **Wochenplan**: „Plan aus Vorlage …“ → Vorlagen wählen → **Bestätigen und anlegen**. Die Themen werden nacheinander auf die Unterrichtswochen verteilt; Ferien bleiben frei, verkürzte Wochen erhalten anteilig weniger Stunden. Die Startinhalte decken nur einen Teil des Schuljahrs ab – weitere Einheiten fügen Sie selbst hinzu. Ein bestehender Plan wird nur ersetzt, wenn Sie das ausdrücklich ankreuzen.

### Übersicht (Dashboard)
- Wochenwahl: „‹ Vorwoche“, Datumsfeld, „Nächste ›“, „Heute“.
- Kopfzeile: **KW** (ISO-Kalenderwoche), Datumsbereich, **Unterrichtswoche** (zählt nur Wochen mit Unterricht), Hinweise „unterrichtsfrei“ oder „verkürzt“.
- **Geplante Einheiten** mit Stunden, Kompetenzbezug, verknüpften Materialien und Status (○ geplant, ◐ begonnen, ● abgeschlossen).
  - **Abschließen** ändert nur diese eine Einheit.
  - **Verschieben** öffnet die Datumsauswahl – ein beliebiges Datum der Zielwoche genügt.
- **Passende Materialien**: bis zu fünf Vorschläge je Fach mit Begründung und Punktzahl (Thema eingeplant +100, gemeinsamer Kompetenzbezug +20, gewähltes Niveau +5). Ist in der Woche nichts eingeplant, erscheint das nächste offene Thema als gekennzeichneter Vorschlag – es wird **nicht** automatisch eingeplant.

### Wochenplan
Alle Wochen des Schuljahrs mit Einheiten und Kapazität je Fach (z. B. „Deutsch: 7/7“; ⚠ bei Überplanung). „+ Einheit in dieser Woche“ fügt eine Einheit hinzu. Beim Speichern warnt die Anwendung bei Überplanung oder einer vollständig freien Zielwoche – Sie entscheiden, ob trotzdem gespeichert wird.

**Gleichzeitige Bearbeitung:** Wurde eine Einheit inzwischen an anderer Stelle (z. B. am Tablet) geändert, erscheint „Versionskonflikt“. Wählen Sie „Neu laden“ oder „Meine Änderungen behalten und erneut speichern“. Es geht nichts stillschweigend verloren.

### Bibliothek
- Suchfeld durchsucht Titel, Kurzbeschreibung und Schlagwörter (nicht den PDF-Text).
- **Filter** (auf dem Smartphone über die Schaltfläche „Filter“): Fach, Thema, Kompetenz, Niveau, Materialtyp, Dauer. Verschiedene Filter wirken zusammen (UND), mehrere Werte in einem Filter wirken alternativ (ODER).
- Sortierung nach Relevanz oder Titel; 20 Treffer je Seite.
- Es erscheinen nur **freigegebene** Materialien. Material mit dem Hinweis „Demo · nicht fachlich geprüft“ dient nur der Erprobung.

### Materialdetails
Beschreibung, Lernziel, offizieller Lehrplanbezug (mit Prüfstatus und Link zur Quelle), Zeitbedarf, Niveau, Typ, Lizenz, Autor, Freigabestand. **Schülerdatei** und **Lösung/Auswertungshilfe** haben getrennte Schaltflächen „Öffnen“ und „Herunterladen“; fehlt eine Lösung, wird das ausdrücklich angezeigt. Auf Mobilgeräten öffnet „Öffnen“ den PDF-Viewer des Geräts, von dort lässt sich die Datei teilen oder drucken.

### Merkliste
Mit „☆ Merken“ speichern Sie Materialien dauerhaft – auch nach dem Abmelden.

## Für die Administration

Menü **Verwaltung**:

| Bereich | Aufgaben |
|---|---|
| Status | Freigabestand (x von 30 fachlich freigegebenen Materialien), Kalenderprüfung, Inhaltsimport (JSON) |
| Benutzer | Anlegen (temporäres Passwort wird einmalig angezeigt), Rolle ändern, sperren/entsperren, Passwort zurücksetzen. Max. 20 Konten. |
| Materialien | Anlegen, Metadaten, PDF-Upload (nur PDF ≤ 20 MB) für Haupt- und Lösungsdatei, fachliche Prüfung erfassen, freigeben, archivieren |
| Themen | Titel, Beschreibung, Reihenfolge, Voraussetzungen, Planungsnotiz, archivieren |
| Lehrplanbezüge | Abschnitt, sinngemäßes Ziel, Quelle, Abrufdatum; „Als geprüft markieren“ |
| Kalender | Schuljahre, Ferien/Feiertage/Sondertage, Prüfung & Freigabe, JSON-Import mit Vorschau |
| Vorlagen | Reihenfolge und Stundenbedarf der Pilotvorlagen |
| Protokoll | Audit-Protokoll aller Verwaltungsaktionen |

**Freigabeablauf eines Materials:** Entwurf → *Als geprüft markieren* (Prüfer und Datum) → *Freigeben* → ggf. *Archivieren*. Die Freigabe ist nur möglich mit mindestens einer **geprüften** Kompetenzreferenz, gültiger Hauptdatei, Lizenz/Nutzungserlaubnis, Autor und fachlicher Prüfung. KI-Erstellung allein ersetzt keine fachliche Prüfung. Archivierte Materialien bleiben in bestehenden Plänen sichtbar, werden aber nicht mehr empfohlen.

Sicherung und Wiederherstellung erfolgen über die Betriebsskripte (siehe [BETRIEB.md](BETRIEB.md)).
