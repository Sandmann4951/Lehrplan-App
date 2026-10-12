"""Lasttest A11: 1.000 Materialdatensätze, fünf aktive Benutzer, 100 Aktionen.

Legt ein frisches Datenverzeichnis an, startet den Server lokal und misst die
Antwortzeiten für Suche, Dashboard und Planspeichern (ohne Dateiübertragung).

    cd backend && python -m tools.perf_test [--keep] [--port 8765]

Erfolgskriterium: p95 < 2 Sekunden je Aktionstyp.
"""
from __future__ import annotations

import argparse
import os
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

USERS = 5
ACTIONS = 100
MATERIALS = 1000
PASSWORD = "Lasttest-Passwort-2026"


def prepare(data_dir: Path) -> None:
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["BACKUP_AUTO"] = "false"
    from app.config import reload_settings

    reload_settings()
    from app.db import db_session
    from app.migrations import upgrade_head
    from app.models import Material, Topic, User
    from app.security import hash_password
    from app.seed.loader import load_seed

    upgrade_head()
    with db_session() as db:
        load_seed(db)
        topics = db.query(Topic).all()
        rnd = random.Random(42)
        types = ["worksheet", "lesson_plan", "assessment"]
        levels = ["basis", "standard", "erweitert", "differenziert"]
        for i in range(MATERIALS - 10):
            t = rnd.choice(topics)
            db.add(
                Material(
                    topic_id=t.id,
                    title=f"Lastmaterial {i:04d} {t.title}",
                    description=f"Beschreibung {i} zu {t.title} mit Übungen und Aufgaben.",
                    keywords="last, test, übung",
                    type=rnd.choice(types),
                    level=rnd.choice(levels),
                    duration_minutes=rnd.choice([20, 30, 45, 90]),
                    status="released",
                    is_demo=True,
                    author="Lasttest",
                    license_text="Test",
                )
            )
        h = hash_password(PASSWORD)
        for u in range(USERS):
            db.add(User(email=f"last{u}@schule.test", display_name=f"Last {u}", role="teacher", password_hash=h))
        db.commit()


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100 * len(s) + 0.5)) - 1))
    return s[k]


def user_session(base: str, idx: int, n_actions: int) -> dict[str, list[float]]:
    times: dict[str, list[float]] = {"search": [], "dashboard": [], "plan_save": []}
    with httpx.Client(base_url=base, timeout=30) as c:
        r = c.post("/api/v1/auth/login", json={"email": f"last{idx}@schule.test", "password": PASSWORD})
        r.raise_for_status()
        h = {"X-CSRF-Token": r.json()["csrf_token"]}
        ref = c.get("/api/v1/reference").json()
        cls = c.post("/api/v1/classes", json={"name": f"1{idx}", "school_year_id": ref["school_years"][0]["id"]}, headers=h).json()
        c.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={"confirm": True}, headers=h).raise_for_status()
        units = c.get(f"/api/v1/classes/{cls['id']}/units").json()["items"]
        rnd = random.Random(idx)
        weeks = ["2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12", "2026-11-09", "2027-01-11"]
        for a in range(n_actions):
            kind = ("search", "dashboard", "plan_save")[a % 3]
            t0 = time.perf_counter()
            if kind == "search":
                params = {"q": rnd.choice(["zahlen", "laute", "übung", "lastmaterial 01", ""]), "level": rnd.choice(["basis", "standard"]), "page_size": 20}
                c.get("/api/v1/materials", params=params).raise_for_status()
            elif kind == "dashboard":
                c.get(f"/api/v1/classes/{cls['id']}/dashboard", params={"week": rnd.choice(weeks)}).raise_for_status()
            else:
                u = rnd.choice(units)
                r = c.patch(f"/api/v1/units/{u['id']}", json={"version": u["version"], "notes": f"Notiz {a}"}, headers=h)
                r.raise_for_status()
                u["version"] = r.json()["unit"]["version"]
            times[kind].append(time.perf_counter() - t0)
    return times


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--keep", action="store_true", help="Datenverzeichnis nicht löschen")
    args = ap.parse_args()
    data_dir = Path(tempfile.mkdtemp(prefix="lehrplan-perf-"))
    print(f"Datenverzeichnis: {data_dir}")
    t = time.perf_counter()
    prepare(data_dir)
    print(f"Testdaten vorbereitet ({MATERIALS} Materialien, {USERS} Benutzer) in {time.perf_counter() - t:.1f}s")
    env = {**os.environ, "DATA_DIR": str(data_dir), "BACKUP_AUTO": "false", "FRONTEND_DIST": ""}
    server = subprocess.Popen([sys.executable, "-m", "app.cli", "serve", "--port", str(args.port)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{args.port}"
    try:
        for _ in range(50):
            try:
                if httpx.get(f"{base}/api/v1/health").status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        per_user = ACTIONS // USERS
        with ThreadPoolExecutor(max_workers=USERS) as ex:
            results = list(ex.map(lambda i: user_session(base, i, per_user), range(USERS)))
        merged: dict[str, list[float]] = {}
        for res in results:
            for k, v in res.items():
                merged.setdefault(k, []).extend(v)
        ok = True
        total = sum(len(v) for v in merged.values())
        print(f"\n{total} Aktionen, {USERS} parallele Benutzer")
        print(f"{'Aktion':<12} {'n':>4} {'Median':>9} {'p95':>9} {'Max':>9}")
        for k, v in merged.items():
            p95 = percentile(v, 95)
            ok &= p95 < 2.0
            print(f"{k:<12} {len(v):>4} {statistics.median(v) * 1000:>7.0f}ms {p95 * 1000:>7.0f}ms {max(v) * 1000:>7.0f}ms")
        print("\nErgebnis:", "BESTANDEN (p95 < 2 s)" if ok else "NICHT BESTANDEN")
        return 0 if ok else 1
    finally:
        server.terminate()
        server.wait(timeout=10)
        if not args.keep:
            shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
