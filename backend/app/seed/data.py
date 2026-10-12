"""Startinhalte für den Piloten (Bayern, Grundschule, Klasse 1).

Hinweise zur fachlichen Verantwortung:
- Themen und Reihenfolge sind eine pädagogische Pilotplanung (F08), keine amtliche Wochenfolge.
- Lehrplanbezüge sind sinngemäß formuliert und stehen auf „ungeprüft“, bis eine
  Lehrkraft sie gegen LehrplanPLUS geprüft hat.
- Kalenderdaten 2026/2027 sind Vorbelegungen und stehen auf „ungeprüft“ (nur Demo),
  bis sie gegen die amtliche Ferienordnung geprüft und freigegeben sind.
- Die zehn Materialien sind Demonstrationsmaterial (is_demo) und nicht fachlich geprüft.
"""
from __future__ import annotations

import uuid
from datetime import date

NS = uuid.UUID("6f1c9a52-6c3e-4f43-9a8e-2b8f2d1c7a10")


def sid(key: str) -> str:
    """Stabile, deterministische UUID für Seed-Datensätze."""
    return str(uuid.uuid5(NS, key))


RETRIEVED = date(2026, 10, 12)
URL_D = "https://www.lehrplanplus.bayern.de/fachlehrplan/grundschule/1/deutsch"
URL_M = "https://www.lehrplanplus.bayern.de/fachlehrplan/grundschule/1/mathematik"
KM_FERIEN = "https://www.km.bayern.de/ministerium/termine/ferientermine.html"

SUBJECTS = [
    {"id": sid("subject:D"), "code": "D", "title": "Deutsch", "sort_order": 1},
    {"id": sid("subject:M"), "code": "M", "title": "Mathematik", "sort_order": 2},
]

TOPICS = [
    # Deutsch
    {"key": "D1", "subject": "D", "title": "Laute hören und unterscheiden", "description": "Anlaute, Inlaute und Endlaute heraushören; Reime erkennen (phonologische Bewusstheit).", "sequence": 1, "lessons": 14, "prereq": []},
    {"key": "D2", "subject": "D", "title": "Buchstaben und Laute zuordnen", "description": "Laut-Buchstaben-Beziehungen aufbauen; Buchstaben in Wörtern wiederfinden.", "sequence": 2, "lessons": 35, "prereq": ["D1"]},
    {"key": "D3", "subject": "D", "title": "Silben und erste Wörter lesen", "description": "Silben schwingen, Silben zusammenziehen, kurze lautgetreue Wörter erlesen.", "sequence": 3, "lessons": 28, "prereq": ["D2"]},
    {"key": "D4", "subject": "D", "title": "Buchstaben und erste Wörter schreiben", "description": "Buchstaben formklar schreiben, kurze Wörter abschreiben und lautgetreu verschriften.", "sequence": 4, "lessons": 28, "prereq": ["D2"]},
    {"key": "D5", "subject": "D", "title": "Zuhören und verständlich erzählen", "description": "Aufmerksam zuhören, Fragen zu Gehörtem beantworten, Erlebnisse geordnet erzählen.", "sequence": 5, "lessons": 14, "prereq": []},
    # Mathematik
    {"key": "M1", "subject": "M", "title": "Mengen erkennen und zählen", "description": "Mengen bis 10 zählen, simultan und quasi-simultan erfassen, Anzahlen darstellen.", "sequence": 1, "lessons": 15, "prereq": []},
    {"key": "M2", "subject": "M", "title": "Zahlen bis 10 darstellen und vergleichen", "description": "Zahlen in verschiedenen Darstellungen zeigen, ordnen und mit <, >, = vergleichen.", "sequence": 2, "lessons": 20, "prereq": ["M1"]},
    {"key": "M3", "subject": "M", "title": "Zahlen bis 10 zerlegen", "description": "Zahlen systematisch zerlegen (Schüttelbox, Zahlenhaus), Zahlbeziehungen nutzen.", "sequence": 3, "lessons": 15, "prereq": ["M2"]},
    {"key": "M4", "subject": "M", "title": "Im Zahlenraum bis 10 addieren und subtrahieren", "description": "Addition und Subtraktion als Hinzufügen und Wegnehmen verstehen und notieren.", "sequence": 4, "lessons": 25, "prereq": ["M3"]},
    {"key": "M5", "subject": "M", "title": "Formen erkennen und einfache Muster fortsetzen", "description": "Ebene Figuren erkennen und benennen; einfache Muster beschreiben und fortsetzen.", "sequence": 5, "lessons": 10, "prereq": []},
]

PLANNING_NOTE_D = "Bitte Buchstabenfolge bzw. eingesetztes Lehrwerk als Planungsnotiz berücksichtigen."

# Sinngemäße Formulierungen – vor Freigabe gegen die Originalquelle prüfen.
CURRICULUM = [
    {"key": "D-1.1", "subject": "D", "code": "D 1/2 1.1", "title": "Verstehend zuhören", "goal": "Die Kinder hören aufmerksam zu und geben Gehörtes sinngemäß wieder.", "url": URL_D},
    {"key": "D-1.3", "subject": "D", "code": "D 1/2 1.3", "title": "Zu anderen sprechen", "goal": "Die Kinder erzählen Erlebnisse und Geschichten verständlich und in sinnvoller Reihenfolge.", "url": URL_D},
    {"key": "D-2.1", "subject": "D", "code": "D 1/2 2.1", "title": "Über Lesefähigkeiten verfügen", "goal": "Die Kinder nutzen Laut-Buchstaben-Beziehungen und Silben, um Wörter zu erlesen.", "url": URL_D},
    {"key": "D-3.1", "subject": "D", "code": "D 1/2 3.1", "title": "Über Schreibfertigkeiten verfügen", "goal": "Die Kinder schreiben Buchstaben und Wörter formklar und gut lesbar.", "url": URL_D},
    {"key": "D-3.2", "subject": "D", "code": "D 1/2 3.2", "title": "Richtig schreiben", "goal": "Die Kinder gliedern Wörter in Laute und Silben und verschriften lautgetreue Wörter.", "url": URL_D},
    {"key": "M-1.1", "subject": "M", "code": "M 1/2 1.1", "title": "Zahldarstellungen und Zahlbeziehungen verstehen", "goal": "Die Kinder erfassen Anzahlen, stellen Zahlen dar, vergleichen und zerlegen sie.", "url": URL_M},
    {"key": "M-1.2", "subject": "M", "code": "M 1/2 1.2", "title": "Rechenoperationen verstehen und beherrschen", "goal": "Die Kinder verstehen Addition und Subtraktion und rechnen im Zahlenraum bis 10.", "url": URL_M},
    {"key": "M-2.2", "subject": "M", "code": "M 1/2 2.2", "title": "Geometrische Figuren erkennen, benennen und darstellen", "goal": "Die Kinder erkennen und benennen ebene Figuren wie Kreis, Dreieck, Quadrat und Rechteck.", "url": URL_M},
    {"key": "M-3.1", "subject": "M", "code": "M 1/2 3.1", "title": "Gesetzmäßigkeiten erkennen, beschreiben und darstellen", "goal": "Die Kinder erkennen einfache Muster, beschreiben sie und setzen sie fort.", "url": URL_M},
]

TOPIC_CURRICULUM = {
    "D1": ["D-3.2", "D-2.1"],
    "D2": ["D-2.1", "D-3.2"],
    "D3": ["D-2.1"],
    "D4": ["D-3.1", "D-3.2"],
    "D5": ["D-1.1", "D-1.3"],
    "M1": ["M-1.1"],
    "M2": ["M-1.1"],
    "M3": ["M-1.1", "M-1.2"],
    "M4": ["M-1.2"],
    "M5": ["M-2.2", "M-3.1"],
}

SCHOOL_YEAR = {"id": sid("schoolyear:2026/2027"), "label": "2026/2027", "starts_on": date(2026, 9, 15), "ends_on": date(2027, 7, 30)}

_SRC = f"Vorbelegung durch den Entwickler; vor Unterrichtseinsatz gegen die amtliche Ferienordnung prüfen ({KM_FERIEN})"
CLOSURES = [
    ("Herbstferien", date(2026, 11, 2), date(2026, 11, 6), "holiday"),
    ("Buß- und Bettag", date(2026, 11, 18), date(2026, 11, 18), "public_holiday"),
    ("Weihnachtsferien", date(2026, 12, 24), date(2027, 1, 8), "holiday"),
    ("Frühjahrsferien", date(2027, 2, 8), date(2027, 2, 12), "holiday"),
    ("Osterferien", date(2027, 3, 22), date(2027, 4, 2), "holiday"),
    ("Christi Himmelfahrt", date(2027, 5, 6), date(2027, 5, 6), "public_holiday"),
    ("Pfingstferien", date(2027, 5, 18), date(2027, 5, 28), "holiday"),
]

LICENSE = "Selbst erstellt für den technischen Pilot (Demonstration). Nutzung im Pilotbetrieb erlaubt; Lizenz CC BY 4.0."
AUTHOR = "Entwicklerteam Pilot (Demonstration)"

MATERIALS = [
    {"key": "d1", "topic": "D1", "title": "Anlaute hören", "type": "worksheet", "level": "differenziert", "duration": 45,
     "description": "Arbeitsblatt mit drei Niveaustufen: Anlaut einkreisen, Anfangsbuchstaben schreiben, eigenes Wort finden.",
     "goal": "Die Kinder hören den Anlaut eines Wortes heraus und ordnen ihm einen Buchstaben zu.",
     "keywords": "Anlaut, Laute, Anfangslaut, phonologische Bewusstheit", "curriculum": ["D-3.2"], "main": "d1-anlaute.pdf", "solution": "d1-anlaute-loesung.pdf"},
    {"key": "d2", "topic": "D2", "title": "Der Buchstabe M m", "type": "worksheet", "level": "differenziert", "duration": 45,
     "description": "Nachspuren, Buchstabenjagd im Raster und erste Wörter mit M abschreiben.",
     "goal": "Die Kinder verbinden den Laut /m/ mit dem Buchstaben M m und finden ihn in Wörtern wieder.",
     "keywords": "Buchstabe, M, Laut, Buchstabeneinführung", "curriculum": ["D-2.1", "D-3.2"], "main": "d2-buchstabe-m.pdf", "solution": "d2-buchstabe-m-loesung.pdf"},
    {"key": "d3", "topic": "D3", "title": "Silben schwingen und lesen", "type": "worksheet", "level": "differenziert", "duration": 45,
     "description": "Silben klatschen und markieren, Silben zu Wörtern verbinden, Wörter mit Silbenbögen lesen.",
     "goal": "Die Kinder gliedern Wörter in Silben und erlesen kurze Wörter silbenweise.",
     "keywords": "Silben, lesen, Silbenbögen, klatschen", "curriculum": ["D-2.1"], "main": "d3-silben.pdf", "solution": "d3-silben-loesung.pdf"},
    {"key": "d4", "topic": "D4", "title": "Buchstaben schreiben: M und m", "type": "lesson_plan", "level": "standard", "duration": 45,
     "description": "Unterrichtsplan für eine Stunde mit Schwungübung, Schreiben in der Lineatur und Abschreiben erster Wörter.",
     "goal": "Die Kinder schreiben M und m formklar und schreiben erste kurze Wörter ab.",
     "keywords": "Schreiben, Lineatur, Unterrichtsplan, Buchstabe M", "curriculum": ["D-3.1"], "main": "d4-schreiben-unterrichtsplan.pdf", "solution": None},
    {"key": "d5", "topic": "D5", "title": "Gut zuhören – Lernstandskontrolle", "type": "assessment", "level": "standard", "duration": 20,
     "description": "Kurze formative Lernstandskontrolle zum Hörverstehen mit Bildauswahl und mündlicher Erzählaufgabe.",
     "goal": "Die Kinder beantworten Fragen zu einer vorgelesenen Geschichte und erzählen das Ende nach.",
     "keywords": "Zuhören, Hörverstehen, Erzählen, Lernstand", "curriculum": ["D-1.1", "D-1.3"], "main": "d5-zuhoeren-lernstand.pdf", "solution": "d5-zuhoeren-auswertung.pdf"},
    {"key": "m1", "topic": "M1", "title": "Mengen zählen bis 10", "type": "worksheet", "level": "differenziert", "duration": 45,
     "description": "Punktmengen zählen und Zahlen notieren; Mengen zu Zahlen selbst zeichnen.",
     "goal": "Die Kinder bestimmen Anzahlen bis 10 sicher und stellen Zahlen als Menge dar.",
     "keywords": "zählen, Menge, Anzahl, Punkte", "curriculum": ["M-1.1"], "main": "m1-mengen.pdf", "solution": "m1-mengen-loesung.pdf"},
    {"key": "m2", "topic": "M2", "title": "Zahlen vergleichen", "type": "worksheet", "level": "differenziert", "duration": 45,
     "description": "Mengen vergleichen, Relationszeichen einsetzen, passende Zahlen finden.",
     "goal": "Die Kinder vergleichen Zahlen bis 10 und verwenden die Zeichen <, > und =.",
     "keywords": "vergleichen, größer, kleiner, Relationszeichen", "curriculum": ["M-1.1"], "main": "m2-vergleichen.pdf", "solution": "m2-vergleichen-loesung.pdf"},
    {"key": "m3", "topic": "M3", "title": "Zahlen zerlegen", "type": "worksheet", "level": "differenziert", "duration": 45,
     "description": "Schüttelbox, Zahlenhäuser für 6 und 8 und alle Zerlegungen der 10.",
     "goal": "Die Kinder zerlegen Zahlen bis 10 systematisch und erkennen Zusammenhänge.",
     "keywords": "zerlegen, Zahlenhaus, Schüttelbox, Zerlegung", "curriculum": ["M-1.1", "M-1.2"], "main": "m3-zerlegen.pdf", "solution": "m3-zerlegen-loesung.pdf"},
    {"key": "m4", "topic": "M4", "title": "Plus und minus mit Plättchen", "type": "lesson_plan", "level": "standard", "duration": 45,
     "description": "Unterrichtsplan: Rechengeschichten spielen, mit Plättchen legen und Aufgaben notieren.",
     "goal": "Die Kinder verstehen Addition als Hinzufügen und Subtraktion als Wegnehmen.",
     "keywords": "plus, minus, addieren, subtrahieren, Rechengeschichte, Plättchen", "curriculum": ["M-1.2"], "main": "m4-plus-minus-unterrichtsplan.pdf", "solution": None},
    {"key": "m5", "topic": "M5", "title": "Formen und Muster – Lernstandskontrolle", "type": "assessment", "level": "standard", "duration": 20,
     "description": "Kurze formative Lernstandskontrolle: Dreiecke erkennen, Muster fortsetzen, eigenes Muster erfinden.",
     "goal": "Die Kinder erkennen ebene Figuren und setzen einfache Muster fort.",
     "keywords": "Formen, Dreieck, Kreis, Quadrat, Muster, Lernstand", "curriculum": ["M-2.2", "M-3.1"], "main": "m5-formen-lernstand.pdf", "solution": "m5-formen-auswertung.pdf"},
]

TEMPLATES = [
    {"key": "tpl:D", "name": "Pilotvorlage Deutsch Klasse 1", "subject": "D", "topics": ["D1", "D2", "D3", "D4", "D5"]},
    {"key": "tpl:M", "name": "Pilotvorlage Mathematik Klasse 1", "subject": "M", "topics": ["M1", "M2", "M3", "M4", "M5"]},
]
