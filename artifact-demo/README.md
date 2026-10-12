# Variante B – Claude-Artifacts-Demo

Klickbare React-Demo derselben Abläufe wie der lokale Pilot (Dashboard, Bibliothek, Materialdetails, Wochenplan, Merkliste, JSON-Export/-Import). Kein Ersatz für die Abnahme von Variante A.

- `template.html` – Quelltext der Demo (Platzhalter `__SEED__`)
- `seed.json` – Startdaten, erzeugt aus `backend/app/seed/data.py` (gleiche stabile IDs wie der Pilot)
- `index.html` – zusammengesetzte, veröffentlichte Seite

Neu zusammensetzen:
```bash
python3 -c "s=open('artifact-demo/template.html').read();open('artifact-demo/index.html','w').write(s.replace('__SEED__',open('artifact-demo/seed.json').read()))"
```

Speicher: persönlicher Artifact-Speicher (`db`, privat je Person) – sonst nur sitzungsbezogen; der aktive Modus wird angezeigt. Die Anmeldung ist simuliert (fiktive Demo-Konten, keine Passwörter). Arbeitsblätter sind druckfähige HTML-Ansichten statt PDFs.
