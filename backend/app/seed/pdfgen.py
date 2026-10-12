"""Erzeugt die zehn Demonstrations-PDFs (A4, schwarz-weiß, große Schrift).

Die PDFs sind selbst erstellt, deterministisch (``invariant``) und als
Demonstrationsmaterial gekennzeichnet. Aufruf::

    python -m app.seed.pdfgen            # schreibt nach app/seed/pdfs/
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

W, H = A4
M = 50  # Rand
PDF_DIR = Path(__file__).resolve().parent / "pdfs"
FOOTER = "Demonstrationsmaterial – nicht fachlich geprüft · selbst erstellt für den technischen Pilot · CC BY 4.0"
FONT = "Helvetica"
BOLD = "Helvetica-Bold"


class Sheet:
    def __init__(self, path: Path, title: str, subtitle: str):
        self.c = Canvas(str(path), pagesize=A4, invariant=1)
        self.c.setTitle(title)
        self.c.setAuthor("Pilot Unterrichtsassistent (Demonstration)")
        self.c.setSubject(subtitle)
        self.title = title
        self.subtitle = subtitle
        self.page = 0
        self.y = 0.0
        self.new_page()

    # -- Seitenrahmen --------------------------------------------------------
    def new_page(self, with_name: bool = True) -> None:
        if self.page:
            self._footer()
            self.c.showPage()
        self.page += 1
        c = self.c
        c.setFillGray(0)
        c.setFont(FONT, 11)
        c.drawString(M, H - 40, self.subtitle)
        c.setFont(BOLD, 22)
        c.drawString(M, H - 68, self.title)
        self.y = H - 85
        if with_name:
            c.setFont(FONT, 14)
            c.drawString(M, self.y - 20, "Name:")
            c.line(M + 50, self.y - 22, M + 300, self.y - 22)
            c.drawString(M + 320, self.y - 20, "Datum:")
            c.line(M + 375, self.y - 22, W - M, self.y - 22)
            self.y -= 45
        c.setLineWidth(1)

    def _footer(self) -> None:
        self.c.setFont(FONT, 8)
        self.c.setFillGray(0.3)
        self.c.drawString(M, 25, FOOTER)
        self.c.drawRightString(W - M, 25, f"Seite {self.page}")
        self.c.setFillGray(0)

    def save(self) -> None:
        self._footer()
        self.c.save()

    def need(self, height: float) -> None:
        if self.y - height < 60:
            self.new_page(with_name=False)

    # -- Bausteine --------------------------------------------------------------
    def section(self, label: str, stars: int, instruction: str) -> None:
        self.need(80)
        c = self.c
        self.y -= 14
        c.setLineWidth(1.5)
        c.roundRect(M, self.y - 30, W - 2 * M, 30, 6)
        c.setFont(BOLD, 16)
        c.drawString(M + 10, self.y - 21, label)
        # Niveau als Sterne (gezeichnet, nicht nur farblich)
        for i in range(stars):
            star(c, W - M - 20 - i * 22, self.y - 15, 8)
        self.y -= 50
        c.setFont(FONT, 17)
        for line in wrap(instruction, 60):
            c.drawString(M, self.y, line)
            self.y -= 22
        self.y -= 6

    def text(self, s: str, size: int = 14, bold: bool = False, width: int = 80, indent: float = 0) -> None:
        self.c.setFont(BOLD if bold else FONT, size)
        for line in wrap(s, width):
            self.need(size + 6)
            self.c.drawString(M + indent, self.y, line)
            self.y -= size + 6

    def heading(self, s: str) -> None:
        self.need(40)
        self.y -= 8
        self.text(s, 16, bold=True)

    def bullets(self, items: list[str], size: int = 13) -> None:
        for it in items:
            lines = wrap(it, 78)
            for i, line in enumerate(lines):
                self.need(size + 6)
                self.c.setFont(FONT, size)
                if i == 0:
                    self.c.circle(M + 6, self.y + 4, 2, fill=1)
                self.c.drawString(M + 16, self.y, line)
                self.y -= size + 5

    def write_lines(self, n: int, gap: float = 34) -> None:
        """Schreiblinien (Grundlinie + Mittellinie gestrichelt)."""
        c = self.c
        for _ in range(n):
            self.need(gap + 4)
            base = self.y - gap + 8
            c.setLineWidth(1)
            c.line(M, base, W - M, base)
            c.setDash(2, 3)
            c.setLineWidth(0.5)
            c.line(M, base + 12, W - M, base + 12)
            c.setDash()
            c.line(M, base + 24, W - M, base + 24)
            self.y -= gap + 8


def wrap(s: str, width: int) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


# -- einfache Strichzeichnungen ------------------------------------------------

def star(c: Canvas, x: float, y: float, r: float) -> None:
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((x + rad * math.cos(ang), y + rad * math.sin(ang)))
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def icon(c: Canvas, name: str, x: float, y: float, s: float = 40) -> None:
    """Zeichnet ein Symbol mit Mittelpunkt (x, y) und Größe s."""
    c.setLineWidth(2)
    r = s / 2
    if name == "Sonne":
        c.circle(x, y, r * 0.5)
        for i in range(8):
            a = i * math.pi / 4
            c.line(x + r * 0.62 * math.cos(a), y + r * 0.62 * math.sin(a), x + r * math.cos(a), y + r * math.sin(a))
    elif name == "Mond":
        p = c.beginPath()
        p.arc(x - r, y - r, x + r, y + r, 60, 240)
        p.arcTo(x - r * 0.4, y - r * 0.8, x + r * 1.0, y + r * 0.8, 240 + 0, -240)
        c.drawPath(p)
    elif name == "Ball":
        c.circle(x, y, r * 0.8)
        c.line(x - r * 0.8, y, x + r * 0.8, y)
        c.arc(x - r * 0.4, y - r * 0.8, x + r * 0.4, y + r * 0.8, 90, 180)
    elif name == "Haus":
        c.rect(x - r * 0.7, y - r, r * 1.4, r * 1.1)
        p = c.beginPath()
        p.moveTo(x - r * 0.9, y + r * 0.1)
        p.lineTo(x, y + r)
        p.lineTo(x + r * 0.9, y + r * 0.1)
        c.drawPath(p)
        c.rect(x - r * 0.15, y - r, r * 0.3, r * 0.5)
    elif name == "Fisch":
        c.ellipse(x - r * 0.8, y - r * 0.4, x + r * 0.4, y + r * 0.4)
        p = c.beginPath()
        p.moveTo(x + r * 0.4, y)
        p.lineTo(x + r, y + r * 0.4)
        p.lineTo(x + r, y - r * 0.4)
        p.close()
        c.drawPath(p)
        c.circle(x - r * 0.5, y + r * 0.1, 2, fill=1)
    elif name == "Apfel":
        c.circle(x, y - r * 0.1, r * 0.7)
        c.line(x, y + r * 0.6, x + r * 0.1, y + r * 0.95)
        c.ellipse(x + r * 0.1, y + r * 0.6, x + r * 0.5, y + r * 0.85)
    elif name == "Eis":
        p = c.beginPath()
        p.moveTo(x - r * 0.45, y)
        p.lineTo(x, y - r)
        p.lineTo(x + r * 0.45, y)
        p.close()
        c.drawPath(p)
        c.circle(x, y + r * 0.3, r * 0.45)
    elif name == "Baum":
        c.rect(x - r * 0.12, y - r, r * 0.24, r * 0.7)
        c.circle(x, y + r * 0.2, r * 0.6)
    elif name == "Maus":
        c.ellipse(x - r * 0.7, y - r * 0.4, x + r * 0.5, y + r * 0.3)
        c.circle(x - r * 0.45, y + r * 0.4, r * 0.2)
        c.line(x + r * 0.5, y - r * 0.1, x + r, y + r * 0.2)
        c.circle(x - r * 0.55, y, 1.5, fill=1)
    elif name == "Tomate":
        c.ellipse(x - r * 0.75, y - r * 0.55, x + r * 0.75, y + r * 0.45)
        c.line(x, y + r * 0.45, x, y + r * 0.75)
    else:
        c.rect(x - r, y - r, s, s)
    c.setLineWidth(1)


def dots(c: Canvas, n: int, x: float, y: float, cols: int = 5, d: float = 16, filled: bool = True) -> None:
    for i in range(n):
        cx = x + (i % cols) * (d + 6)
        cy = y - (i // cols) * (d + 6)
        c.circle(cx, cy, d / 2, fill=1 if filled else 0)


def box(c: Canvas, x: float, y: float, w: float = 40, h: float = 40, text: str | None = None, size: int = 22) -> None:
    c.setLineWidth(1.5)
    c.rect(x, y, w, h)
    c.setLineWidth(1)
    if text is not None:
        c.setFont(BOLD, size)
        c.drawCentredString(x + w / 2, y + h / 2 - size / 3, text)


def shape(c: Canvas, kind: str, x: float, y: float, s: float = 30, fill: int = 0) -> None:
    c.setLineWidth(2)
    if kind == "Kreis":
        c.circle(x, y, s / 2, fill=fill)
    elif kind == "Quadrat":
        c.rect(x - s / 2, y - s / 2, s, s, fill=fill)
    elif kind == "Dreieck":
        p = c.beginPath()
        p.moveTo(x - s / 2, y - s / 2)
        p.lineTo(x + s / 2, y - s / 2)
        p.lineTo(x, y + s / 2)
        p.close()
        c.drawPath(p, fill=fill)
    elif kind == "Rechteck":
        c.rect(x - s * 0.8, y - s / 3, s * 1.6, s * 2 / 3, fill=fill)
    c.setLineWidth(1)


# ===========================================================================
# Deutsch
# ===========================================================================

ANLAUT_A = [("Sonne", "S", "M  S  B"), ("Mond", "M", "M  F  A"), ("Ball", "B", "E  H  B"), ("Haus", "H", "H  S  M")]
ANLAUT_B = [("Fisch", "F"), ("Apfel", "A"), ("Eis", "E"), ("Maus", "M")]


def d_anlaute(main: Path, solution: Path) -> None:
    for path, sol in ((main, False), (solution, True)):
        s = Sheet(path, "Anlaute hören" + (" – Lösung" if sol else ""), "Deutsch · Klasse 1 · Laute hören und unterscheiden")
        c = s.c
        s.section("Teil A", 1, "Sprich das Wort. Welchen Laut hörst du am Anfang? Kreise den Buchstaben ein.")
        for i, (name, letter, choices) in enumerate(ANLAUT_A):
            x = M + 40 + i * 125
            icon(c, name, x, s.y - 30, 50)
            c.setFont(FONT, 20)
            c.drawCentredString(x, s.y - 90, choices)
            if sol:
                c.setFont(FONT, 11)
                c.drawCentredString(x, s.y - 110, f"{name}: {letter}")
                idx = choices.split().index(letter)
                c.setLineWidth(2)
                c.circle(x - 30 + idx * 30.5, s.y - 84, 13)
                c.setLineWidth(1)
        s.y -= 125
        s.section("Teil B", 2, "Sprich das Wort. Schreibe den Anfangsbuchstaben in das Kästchen.")
        for i, (name, letter) in enumerate(ANLAUT_B):
            x = M + 40 + i * 125
            icon(c, name, x, s.y - 30, 50)
            box(c, x - 22, s.y - 110, 44, 44, letter if sol else None, 26)
        s.y -= 135
        s.section("Teil C", 3, "Finde ein eigenes Wort, das mit M anfängt. Male es und schreibe den ersten Buchstaben.")
        c.setLineWidth(1.5)
        c.rect(M, s.y - 115, W - 2 * M - 80, 115)
        box(c, W - M - 60, s.y - 60, 50, 50, "M" if sol else None, 28)
        if sol:
            c.setFont(FONT, 13)
            c.drawString(M + 10, s.y - 20, "Beispiele: Maus, Mond, Mama, Milch, Möhre, Mütze")
        s.y -= 170
        s.save()


GRID = ["M a m O", "t m L M", "o M e m", "M i s m"]


def d_buchstabe_m(main: Path, solution: Path) -> None:
    count = sum(row.replace(" ", "").lower().count("m") for row in GRID)
    for path, sol in ((main, False), (solution, True)):
        s = Sheet(path, "Der Buchstabe M m" + (" – Lösung" if sol else ""), "Deutsch · Klasse 1 · Buchstaben und Laute zuordnen")
        c = s.c
        s.section("Teil A", 1, "Spure die Buchstaben nach. Sprich dabei leise: mmm.")
        c.setFont(BOLD, 60)
        for i in range(6):
            c.setFillGray(0.0 if (sol or i == 0) else 0.75)
            c.drawString(M + i * 80, s.y - 60, "M" if i < 3 else "m")
        c.setFillGray(0)
        s.y -= 85
        s.write_lines(1, 40)
        s.section("Teil B", 2, "Kreise alle M und m ein. Wie viele findest du?")
        for r, row in enumerate(GRID):
            for col, ch in enumerate(row.split()):
                x = M + 40 + col * 70
                y = s.y - 25 - r * 45
                c.setFont(BOLD, 30)
                c.drawCentredString(x, y, ch)
                if sol and ch.lower() == "m":
                    c.setLineWidth(2)
                    c.circle(x, y + 10, 20)
                    c.setLineWidth(1)
        c.setFont(FONT, 18)
        c.drawString(M + 320, s.y - 70, "Ich finde")
        box(c, M + 405, s.y - 85, 44, 40, str(count) if sol else None)
        c.drawString(M + 460, s.y - 70, "M m.")
        s.y -= 200
        s.section("Teil C", 3, "Lies die Wörter. Schreibe sie ab.")
        for word in ("Mama", "Oma", "Mimi"):
            s.need(50)
            c.setFont(BOLD, 24)
            c.drawString(M, s.y - 26, word)
            c.setLineWidth(1)
            c.line(M + 120, s.y - 28, W - M, s.y - 28)
            if sol:
                c.setFont(FONT, 18)
                c.drawString(M + 130, s.y - 25, word)
            s.y -= 48
        s.save()


SILBEN = [("Sonne", 2, "Son-ne"), ("Mond", 1, "Mond"), ("Apfel", 2, "Ap-fel"), ("Tomate", 3, "To-ma-te")]


def d_silben(main: Path, solution: Path) -> None:
    for path, sol in ((main, False), (solution, True)):
        s = Sheet(path, "Silben schwingen und lesen" + (" – Lösung" if sol else ""), "Deutsch · Klasse 1 · Silben und erste Wörter lesen")
        c = s.c
        s.section("Teil A", 1, "Sprich das Wort und klatsche dazu. Male für jede Silbe einen Kreis aus.")
        for i, (name, n, split) in enumerate(SILBEN):
            x = M + 45 + i * 125
            icon(c, name, x, s.y - 28, 50)
            c.setFont(FONT, 13)
            c.drawCentredString(x, s.y - 72, split if sol else name)
            for k in range(3):
                c.circle(x - 30 + k * 30, s.y - 98, 10, fill=1 if (sol and k < n) else 0)
        s.y -= 125
        s.section("Teil B", 2, "Lies die Silben. Verbinde sie zu einem Wort.")
        pairs = [("Ma", "ma"), ("O", "ma"), ("Li", "na"), ("Ro", "se")]
        right = ["se", "ma", "na", "ma"]
        for i, (left, _) in enumerate(pairs):
            y = s.y - 20 - i * 42
            c.setFont(BOLD, 24)
            c.drawString(M + 40, y, left)
            c.drawString(M + 300, y, right[i])
            c.circle(M + 110, y + 8, 4, fill=1)
            c.circle(M + 285, y + 8, 4, fill=1)
        if sol:
            c.setLineWidth(1.5)
            mapping = {0: 1, 1: 3, 2: 2, 3: 0}
            for i, j in mapping.items():
                c.line(M + 110, s.y - 12 - i * 42, M + 285, s.y - 12 - j * 42)
            c.setFont(FONT, 12)
            c.drawString(M + 380, s.y - 20, "Mama, Oma, Lina, Rose")
            c.setLineWidth(1)
        s.y -= 185
        s.section("Teil C", 3, "Lies die Wörter mit Silbenbögen. Schreibe sie ab.")
        for word in ("Ro-se", "La-ma", "Mo-na-te"):
            s.need(50)
            c.setFont(BOLD, 24)
            parts = word.split("-")
            x = M
            for part in parts:
                wpx = c.stringWidth(part, BOLD, 24)
                c.drawString(x, s.y - 26, part)
                c.arc(x, s.y - 40, x + wpx, s.y - 30, 180, 180)
                x += wpx + 2
            c.line(M + 150, s.y - 28, W - M, s.y - 28)
            if sol:
                c.setFont(FONT, 18)
                c.drawString(M + 160, s.y - 25, word.replace("-", ""))
            s.y -= 50
        s.save()


def lesson_plan(path: Path, title: str, subtitle: str, sections: dict[str, list[str] | str]) -> None:
    s = Sheet(path, title, subtitle)
    s.y += 45  # kein Namensfeld für Lehrkräfte – Platz zurückgeben
    s.c.setFillGray(1)
    s.c.rect(M - 2, s.y - 47, W - 2 * M + 4, 47, stroke=0, fill=1)
    s.c.setFillGray(0)
    s.text("Unterrichtsplan für eine Unterrichtsstunde (45 Minuten)", 13)
    for heading, body in sections.items():
        s.heading(heading)
        if isinstance(body, list):
            s.bullets(body)
        else:
            s.text(body, 13)
    s.save()


def d_schreiben_plan(main: Path) -> None:
    lesson_plan(
        main,
        "Buchstaben schreiben: M und m",
        "Deutsch · Klasse 1 · Buchstaben und erste Wörter schreiben",
        {
            "Lernziel": "Die Kinder schreiben M und m formklar in der Lineatur und schreiben erste kurze Wörter (Mama, Oma) ab.",
            "Voraussetzung": "Laut /m/ ist eingeführt; Kinder kennen die Lineatur mit Grund- und Mittellinie.",
            "Materialliste": ["Arbeitsblatt „Der Buchstabe M m“", "Tafel mit Lineatur", "Sandtablett oder Fühlbuchstaben", "Bleistift, Wachsmalkreide"],
            "Einstieg (10 Minuten)": [
                "Sitzkreis: Gegenstände mit /m/ aus einer Fühlkiste ertasten und benennen.",
                "Lehrkraft schreibt M und m groß an die Tafel; Kinder schreiben in die Luft und auf den Rücken des Nachbarkindes.",
            ],
            "Arbeitsphase (25 Minuten)": [
                "Schwungübung (Bögen) auf Papier mit Wachsmalkreide.",
                "Teil A des Arbeitsblatts: Nachspuren, dann selbstständig in der Lineatur.",
                "Teil B: Buchstabenjagd; Teil C: Wörter abschreiben (für schnellere Kinder).",
                "Lehrkraft begleitet die Stifthaltung und Bewegungsrichtung einzelner Kinder.",
            ],
            "Abschluss (10 Minuten)": [
                "Kinder zeigen ihren schönsten Buchstaben und begründen kurz.",
                "Gemeinsames Lesen der Wörter Mama, Oma, Mimi.",
            ],
            "Differenzierung": [
                "Basis: Buchstaben im Sand oder mit Fühlbuchstaben nachfahren, nur Teil A.",
                "Standard: Teil A und B des Arbeitsblatts.",
                "Erweitert: Teil C und eigene Wörter mit M finden und aufschreiben.",
            ],
            "Hinweis": "Bitte Buchstabenfolge und Schreibschrift/Druckschrift an das eingesetzte Lehrwerk anpassen.",
        },
    )


STORY = (
    "Mia geht in den Garten. Sie nimmt ihren roten Ball mit. Unter dem großen Baum liegt ein Apfel. "
    "Mia hebt den Apfel auf und isst ihn. Dann geht sie zum kleinen Teich. Im Wasser schwimmt ein Fisch. "
    "Mia winkt dem Fisch zu und läuft mit ihrem Ball nach Hause."
)
QUESTIONS = [
    ("Was nimmt Mia mit?", ["Eis", "Ball", "Fisch"], "Ball"),
    ("Was liegt unter dem Baum?", ["Apfel", "Mond", "Haus"], "Apfel"),
    ("Was schwimmt im Teich?", ["Sonne", "Maus", "Fisch"], "Fisch"),
]


def d_zuhoeren_lsk(main: Path, solution: Path) -> None:
    s = Sheet(main, "Gut zuhören", "Deutsch · Klasse 1 · Zuhören und verständlich erzählen · Lernstandskontrolle")
    c = s.c
    s.text("Deine Lehrerin oder dein Lehrer liest eine Geschichte vor. Hör gut zu.", 16)
    for i, (q, options, _) in enumerate(QUESTIONS, start=1):
        s.section(f"Aufgabe {i}", 1, f"{q} Kreuze das richtige Bild an.")
        for k, name in enumerate(options):
            x = M + 70 + k * 160
            icon(c, name, x, s.y - 30, 55)
            box(c, x - 14, s.y - 100, 28, 28)
        s.y -= 115
    s.section("Aufgabe 4", 2, "Erzähle: Was macht Mia am Ende der Geschichte?")
    s.text("(mündlich – deine Lehrkraft hört zu)", 13)
    s.save()

    s = Sheet(solution, "Gut zuhören – Auswertungshilfe", "Deutsch · Klasse 1 · Zuhören und verständlich erzählen · Lernstandskontrolle")
    s.y += 45
    s.c.setFillGray(1)
    s.c.rect(M - 2, s.y - 47, W - 2 * M + 4, 47, stroke=0, fill=1)
    s.c.setFillGray(0)
    s.text("Formative Lernstandskontrolle – keine amtlich vorgegebene Prüfung. Ergebnisse werden nicht in der Anwendung erfasst.", 12)
    s.heading("Vorlesetext (langsam, zweimal vorlesen)")
    s.text(STORY, 13)
    s.heading("Lösungen")
    s.bullets([f"Aufgabe {i}: {q} – {a}" for i, (q, _, a) in enumerate(QUESTIONS, start=1)])
    s.bullets(["Aufgabe 4: Mia winkt dem Fisch zu und läuft mit dem Ball nach Hause (sinngemäß)."])
    s.heading("Beobachtungshinweise")
    s.bullets(
        [
            "Hört das Kind bis zum Ende zu, ohne zu unterbrechen?",
            "Beantwortet es die Fragen 1–3 sicher (3 von 3 richtig: sicher; 2: weitgehend; 0–1: Unterstützung anbieten)?",
            "Erzählt es in ganzen Sätzen und in sinnvoller Reihenfolge?",
            "Förderidee: Geschichten mit Bildkarten nacherzählen lassen; Fragen vorab stellen (gezieltes Zuhören).",
        ]
    )
    s.save()


# ===========================================================================
# Mathematik
# ===========================================================================

def m_mengen(main: Path, solution: Path) -> None:
    a = [3, 5, 2, 4]
    b = [7, 9, 6, 10]
    for path, sol in ((main, False), (solution, True)):
        s = Sheet(path, "Mengen zählen bis 10" + (" – Lösung" if sol else ""), "Mathematik · Klasse 1 · Mengen erkennen und zählen")
        c = s.c
        s.section("Teil A", 1, "Zähle die Punkte. Schreibe die Zahl in das Kästchen.")
        for i, n in enumerate(a):
            x = M + 10 + i * 125
            dots(c, n, x + 8, s.y - 15, cols=3)
            box(c, x + 15, s.y - 110, 44, 44, str(n) if sol else None)
        s.y -= 130
        s.section("Teil B", 2, "Zähle genau. Schreibe die Zahl auf.")
        for i, n in enumerate(b):
            x = M + 10 + i * 125
            dots(c, n, x + 8, s.y - 15, cols=5, d=14)
            box(c, x + 15, s.y - 110, 44, 44, str(n) if sol else None)
        s.y -= 130
        s.section("Teil C", 3, "Male so viele Punkte, wie die Zahl zeigt.")
        for i, n in enumerate([6, 8, 10]):
            x = M + i * 165
            box(c, x, s.y - 50, 44, 44, str(n))
            c.rect(x + 50, s.y - 120, 105, 115)
            if sol:
                dots(c, n, x + 62, s.y - 18, cols=4, d=12)
        s.y -= 140
        s.save()


def m_vergleichen(main: Path, solution: Path) -> None:
    pairs_a = [(4, 6), (8, 5), (3, 7)]
    pairs_b = [(5, 3), (2, 9), (6, 6), (10, 8)]
    for path, sol in ((main, False), (solution, True)):
        s = Sheet(path, "Zahlen vergleichen" + (" – Lösung" if sol else ""), "Mathematik · Klasse 1 · Zahlen bis 10 darstellen und vergleichen")
        c = s.c
        s.section("Teil A", 1, "Wo sind mehr Punkte? Kreise die größere Menge ein.")
        for i, (l, r) in enumerate(pairs_a):
            y = s.y - 20 - i * 60
            dots(c, l, M + 20, y, cols=5, d=13)
            dots(c, r, M + 260, y, cols=5, d=13)
            if sol:
                c.setLineWidth(2)
                if l > r:
                    c.roundRect(M + 5, y - 30, 120, 45, 10)
                else:
                    c.roundRect(M + 245, y - 30, 120, 45, 10)
                c.setLineWidth(1)
        s.y -= 195
        s.section("Teil B", 2, "Setze das richtige Zeichen ein: <  >  =")
        for i, (l, r) in enumerate(pairs_b):
            x = M + 10 + (i % 2) * 250
            y = s.y - 40 - (i // 2) * 60
            c.setFont(BOLD, 28)
            c.drawString(x, y, str(l))
            box(c, x + 45, y - 10, 40, 40, (("<" if l < r else ">" if l > r else "=") if sol else None), 24)
            c.setFont(BOLD, 28)
            c.drawString(x + 100, y, str(r))
        s.y -= 140
        s.section("Teil C", 3, "Finde passende Zahlen. Es gibt mehrere Lösungen.")
        tasks = [("4", "<", None), (None, ">", "7"), ("9", ">", None)]
        answers = ["5, 6, 7, 8, 9 oder 10", "8, 9 oder 10", "0 bis 8"]
        for i, (l, op, r) in enumerate(tasks):
            y = s.y - 40 - i * 55
            c.setFont(BOLD, 28)
            if l:
                c.drawString(M + 10, y, l)
            else:
                box(c, M, y - 10, 40, 40)
            c.drawString(M + 60, y, op)
            if r:
                c.drawString(M + 100, y, r)
            else:
                box(c, M + 95, y - 10, 40, 40)
            if sol:
                c.setFont(FONT, 14)
                c.drawString(M + 170, y + 5, f"möglich: {answers[i]}")
        s.y -= 180
        s.save()


def zahlenhaus(c: Canvas, x: float, y: float, top: int, rows: list[tuple[int | None, int | None]], cell: float = 40) -> float:
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x + cell, y + cell * 0.8)
    p.lineTo(x + 2 * cell, y)
    p.close()
    c.setLineWidth(1.5)
    c.drawPath(p)
    c.setFont(BOLD, 22)
    c.drawCentredString(x + cell, y + 8, str(top))
    for i, (l, r) in enumerate(rows):
        yy = y - (i + 1) * cell
        box(c, x, yy, cell, cell, None if l is None else str(l))
        box(c, x + cell, yy, cell, cell, None if r is None else str(r))
    return y - (len(rows) + 1) * cell


def m_zerlegen(main: Path, solution: Path) -> None:
    for path, sol in ((main, False), (solution, True)):
        s = Sheet(path, "Zahlen zerlegen" + (" – Lösung" if sol else ""), "Mathematik · Klasse 1 · Zahlen bis 10 zerlegen")
        c = s.c
        s.section("Teil A", 1, "Schüttelbox: 5 Plättchen. Wie viele liegen links, wie viele rechts? Schreibe auf.")
        splits = [(2, 3), (4, 1), (0, 5)]
        for i, (l, r) in enumerate(splits):
            x = M + i * 165
            c.rect(x, s.y - 60, 140, 55)
            c.line(x + 70, s.y - 60, x + 70, s.y - 5)
            dots(c, l, x + 12, s.y - 20, cols=2, d=12)
            dots(c, r, x + 82, s.y - 20, cols=3, d=12)
            box(c, x + 20, s.y - 105, 36, 36, str(l) if sol else None, 20)
            box(c, x + 84, s.y - 105, 36, 36, str(r) if sol else None, 20)
        s.y -= 125
        s.section("Teil B", 2, "Fülle das Zahlenhaus aus.")
        top = s.y - 25
        rows6 = [(1, None), (2, None), (None, 3), (5, None)]
        rows6_sol = [(1, 5), (2, 4), (3, 3), (5, 1)]
        zahlenhaus(c, M + 40, top, 6, rows6_sol if sol else rows6)
        rows8 = [(7, None), (None, 4), (2, None), (None, 8)]
        rows8_sol = [(7, 1), (4, 4), (2, 6), (0, 8)]
        zahlenhaus(c, M + 280, top, 8, rows8_sol if sol else rows8)
        s.y = top - 5 * 40 - 15
        s.new_page(with_name=False)
        s.section("Teil C", 3, "Finde alle Zerlegungen der 10. Fange mit 0 und 10 an.")
        rows10 = [(i, 10 - i) for i in range(11)]
        zahlenhaus(c, M + 40, s.y - 30, 10, rows10 if sol else [(0, 10)] + [(None, None)] * 10, cell=36)
        c.setFont(FONT, 14)
        c.drawString(M + 220, s.y - 60, "Tipp: Wenn links eins mehr wird,")
        c.drawString(M + 220, s.y - 80, "wird rechts eins weniger.")
        s.y -= 480
        s.save()


def m_plusminus_plan(main: Path) -> None:
    lesson_plan(
        main,
        "Plus und minus mit Plättchen",
        "Mathematik · Klasse 1 · Im Zahlenraum bis 10 addieren und subtrahieren",
        {
            "Lernziel": "Die Kinder verstehen Addition als Hinzufügen und Subtraktion als Wegnehmen und notieren passende Aufgaben im Zahlenraum bis 10.",
            "Voraussetzung": "Sicheres Zählen und Zerlegen bis 10; Zeichen + und – sind bekannt oder werden eingeführt.",
            "Materialliste": ["Wendeplättchen (je Kind 10)", "Zehnerstreifen", "Rechengeschichten-Bildkarten", "Heft oder Arbeitsblatt"],
            "Einstieg (10 Minuten)": [
                "Rechengeschichte spielen: 4 Kinder stehen vorne, 2 kommen dazu. Wie viele sind es jetzt?",
                "Gemeinsam die Aufgabe 4 + 2 = 6 an die Tafel schreiben; dann umgekehrt: 2 Kinder gehen weg (6 – 2 = 4).",
            ],
            "Arbeitsphase (25 Minuten)": [
                "Partnerarbeit: Ein Kind legt Plättchen, das andere legt dazu oder nimmt weg; beide schreiben die Aufgabe.",
                "Bildkarten: Kinder erzählen eine Rechengeschichte und legen sie mit Plättchen nach.",
                "Lehrkraft beobachtet: zählen die Kinder alles ab oder rechnen sie geschickt weiter?",
            ],
            "Abschluss (10 Minuten)": [
                "Zwei Kinder stellen ihre Rechengeschichte vor; die Klasse findet die passende Aufgabe.",
                "Kurzer Blitzrechen-Moment: 5 + 1, 5 – 1, 3 + 3.",
            ],
            "Differenzierung": [
                "Basis: nur Aufgaben bis 5, Plättchen bleiben liegen, Zehnerstreifen als Hilfe.",
                "Standard: Aufgaben bis 10 mit Plättchen und Notation.",
                "Erweitert: Umkehraufgaben finden (4 + 2 = 6, also 6 – 2 = 4) und eigene Aufgaben erfinden.",
            ],
        },
    )


FORMEN = [("Kreis", 3), ("Dreieck", 4), ("Quadrat", 2), ("Rechteck", 3)]


def m_formen_lsk(main: Path, solution: Path) -> None:
    layout = ["Dreieck", "Kreis", "Quadrat", "Dreieck", "Rechteck", "Kreis", "Dreieck", "Rechteck", "Quadrat", "Kreis", "Dreieck", "Rechteck"]
    pattern = ["Kreis", "Quadrat", "Kreis", "Quadrat", "Kreis"]
    pattern2 = ["Dreieck", "Dreieck", "Kreis", "Dreieck", "Dreieck"]
    s = Sheet(main, "Formen und Muster", "Mathematik · Klasse 1 · Formen erkennen und einfache Muster fortsetzen · Lernstandskontrolle")
    c = s.c
    s.section("Aufgabe 1", 1, "Male alle Dreiecke an. Wie viele Dreiecke sind es?")
    for i, k in enumerate(layout):
        shape(c, k, M + 30 + (i % 6) * 80, s.y - 25 - (i // 6) * 60, 34)
    c.setFont(FONT, 18)
    c.drawString(M, s.y - 150, "Es sind")
    box(c, M + 75, s.y - 162, 40, 40)
    c.drawString(M + 125, s.y - 150, "Dreiecke.")
    s.y -= 175
    s.section("Aufgabe 2", 2, "Setze das Muster fort. Zeichne die nächsten zwei Formen.")
    for row, pat in enumerate((pattern, pattern2)):
        y = s.y - 25 - row * 70
        for i, k in enumerate(pat):
            shape(c, k, M + 30 + i * 70, y, 34)
        for j in range(2):
            c.setDash(3, 3)
            c.rect(M + 30 + (5 + j) * 70 - 25, y - 25, 50, 50)
            c.setDash()
    s.y -= 160
    s.section("Aufgabe 3", 3, "Erfinde ein eigenes Muster mit zwei Formen.")
    c.rect(M, s.y - 70, W - 2 * M, 70)
    s.y -= 90
    s.save()

    s = Sheet(solution, "Formen und Muster – Auswertungshilfe", "Mathematik · Klasse 1 · Formen erkennen und einfache Muster fortsetzen · Lernstandskontrolle")
    s.y += 45
    s.c.setFillGray(1)
    s.c.rect(M - 2, s.y - 47, W - 2 * M + 4, 47, stroke=0, fill=1)
    s.c.setFillGray(0)
    s.text("Formative Lernstandskontrolle – keine amtlich vorgegebene Prüfung. Ergebnisse werden nicht in der Anwendung erfasst.", 12)
    s.heading("Lösungen")
    s.bullets(
        [
            f"Aufgabe 1: {layout.count('Dreieck')} Dreiecke.",
            "Aufgabe 2, Reihe 1: Quadrat, Kreis (Muster Kreis–Quadrat).",
            "Aufgabe 2, Reihe 2: Dreieck, Kreis (Muster Dreieck–Dreieck–Kreis).",
            "Aufgabe 3: individuell; Muster muss sich mindestens zweimal wiederholen.",
        ]
    )
    s.heading("Beobachtungshinweise")
    s.bullets(
        [
            "Unterscheidet das Kind Dreieck, Quadrat, Rechteck und Kreis sicher?",
            "Erkennt es die Regel des Musters und kann sie in Worten beschreiben?",
            "Förderidee: Formen mit Legeplättchen nachlegen; Muster mit Klatschen und Stampfen rhythmisch darstellen.",
        ]
    )
    s.save()


GENERATORS: dict[str, Callable[..., None]] = {}


def generate_all(target: Path = PDF_DIR) -> dict[str, Path]:
    target.mkdir(parents=True, exist_ok=True)
    files = {
        "d1": ("d1-anlaute.pdf", "d1-anlaute-loesung.pdf", d_anlaute),
        "d2": ("d2-buchstabe-m.pdf", "d2-buchstabe-m-loesung.pdf", d_buchstabe_m),
        "d3": ("d3-silben.pdf", "d3-silben-loesung.pdf", d_silben),
        "d4": ("d4-schreiben-unterrichtsplan.pdf", None, d_schreiben_plan),
        "d5": ("d5-zuhoeren-lernstand.pdf", "d5-zuhoeren-auswertung.pdf", d_zuhoeren_lsk),
        "m1": ("m1-mengen.pdf", "m1-mengen-loesung.pdf", m_mengen),
        "m2": ("m2-vergleichen.pdf", "m2-vergleichen-loesung.pdf", m_vergleichen),
        "m3": ("m3-zerlegen.pdf", "m3-zerlegen-loesung.pdf", m_zerlegen),
        "m4": ("m4-plus-minus-unterrichtsplan.pdf", None, m_plusminus_plan),
        "m5": ("m5-formen-lernstand.pdf", "m5-formen-auswertung.pdf", m_formen_lsk),
    }
    out: dict[str, Path] = {}
    for key, (main, sol, fn) in files.items():
        if sol:
            fn(target / main, target / sol)
            out[f"{key}-solution"] = target / sol
        else:
            fn(target / main)
        out[f"{key}-main"] = target / main
    return out


if __name__ == "__main__":
    for k, p in generate_all().items():
        print(k, p.name, p.stat().st_size)
