"""F06, F07, A06, A07, A08: Plan, Empfehlungen und Konflikte."""
from .conftest import create_class, reference, subject_id, topic_id


def _init(api, cls):
    r = api.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={"confirm": True})
    assert r.status_code == 200, r.text
    return r.json()


def test_initialize_requires_confirmation_and_no_silent_overwrite(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    assert teacher_a.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={}).status_code == 422
    result = _init(teacher_a, cls)
    assert result["created_units"] > 0 and result["unplaced"] == []
    r = teacher_a.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={"confirm": True})
    assert r.status_code == 422 and r.json()["code"] == "plan_not_empty"
    r = teacher_a.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={"confirm": True, "replace_existing": True})
    assert r.status_code == 200 and r.json()["replaced_units"] == result["created_units"]


def test_plan_respects_capacity_and_holidays(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    _init(teacher_a, cls)
    units = teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"]
    weeks = {w["week_start"]: w for w in teacher_a.get(f"/api/v1/classes/{cls['id']}/weeks").json()["items"]}
    per_week: dict[tuple[str, str], int] = {}
    for u in units:
        key = (u["week_start_date"], u["subject_id"])
        per_week[key] = per_week.get(key, 0) + u["planned_lessons"]
    for (week, subject), lessons in per_week.items():
        assert not weeks[week]["fully_free"], f"Einheit in freier Woche {week}"
        assert lessons <= weeks[week]["capacity"][subject]
    # Erste Woche (Di 15.09.) ist verkürzt: 7 × 4 / 5 = 5 Stunden Deutsch
    d = subject_id(reference(teacher_a), "D")
    assert per_week[("2026-09-14", d)] == 5
    # Lange Einheiten werden auf mehrere Einträge verteilt
    assert sum(1 for u in units if u["topic_title"] == "Buchstaben und Laute zuordnen") >= 5
    # Herbstferien (02.–06.11.2026) bleiben leer
    assert not any(u["week_start_date"] == "2026-11-02" for u in units)


def test_a06_move_and_complete_only_affect_selected_unit(app, seeded, teacher_a, teacher_b):
    cls = create_class(teacher_a)
    cls_b = create_class(teacher_b, "1b")
    _init(teacher_a, cls)
    _init(teacher_b, cls_b)
    before_b = teacher_b.get(f"/api/v1/classes/{cls_b['id']}/units").json()["items"]
    units = teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"]
    target = units[0]
    others = {u["id"]: u for u in units[1:]}

    r = teacher_a.patch(f"/api/v1/units/{target['id']}", json={"version": target["version"], "week_start_date": "2026-10-14"})
    assert r.status_code == 200
    moved = r.json()["unit"]
    assert moved["week_start_date"] == "2026-10-12"  # auf Montag normalisiert
    assert any(w["code"] == "overplanned" for w in r.json()["warnings"])

    r = teacher_a.patch(f"/api/v1/units/{target['id']}", json={"version": moved["version"], "status": "completed"})
    assert r.json()["unit"]["status"] == "completed"

    after = {u["id"]: u for u in teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"]}
    for uid, u in others.items():
        assert after[uid]["week_start_date"] == u["week_start_date"]
        assert after[uid]["status"] == "planned"
        assert after[uid]["version"] == u["version"]
    assert teacher_b.get(f"/api/v1/classes/{cls_b['id']}/units").json()["items"] == before_b


def test_free_week_warning(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    ref = reference(teacher_a)
    r = teacher_a.post(
        f"/api/v1/classes/{cls['id']}/units/check",
        json={"subject_id": subject_id(ref, "M"), "week_start_date": "2026-11-04", "planned_lessons": 2},
    )
    assert [w["code"] for w in r.json()["warnings"]] == ["free_week"]


def test_subject_topic_mismatch_rejected(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    ref = reference(teacher_a)
    r = teacher_a.post(
        f"/api/v1/classes/{cls['id']}/units",
        json={"subject_id": subject_id(ref, "D"), "topic_id": topic_id(ref, "Zahlen bis 10 zerlegen"), "week_start_date": "2026-09-21", "planned_lessons": 2},
    )
    assert r.status_code == 422


def test_missing_materials_shown(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    ref = reference(teacher_a)
    r = teacher_a.post(
        f"/api/v1/classes/{cls['id']}/units",
        json={"subject_id": subject_id(ref, "D"), "topic_id": topic_id(ref, "Silben und erste Wörter lesen"), "week_start_date": "2026-09-21", "planned_lessons": 2},
    )
    assert r.json()["unit"]["materials"] == []


def test_a08_version_conflict(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    _init(teacher_a, cls)
    unit = teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"][0]
    # Browser 1 speichert
    r1 = teacher_a.patch(f"/api/v1/units/{unit['id']}", json={"version": unit["version"], "notes": "Browser 1"})
    assert r1.status_code == 200
    # Browser 2 mit veralteter Version
    r2 = teacher_a.patch(f"/api/v1/units/{unit['id']}", json={"version": unit["version"], "notes": "Browser 2"})
    assert r2.status_code == 409
    assert r2.json()["code"] == "version_conflict"
    assert r2.json()["current_version"] == unit["version"] + 1
    current = teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"][0]
    assert current["notes"] == "Browser 1"  # kein stiller Datenverlust
    # Neu laden und erneut speichern
    r3 = teacher_a.patch(f"/api/v1/units/{unit['id']}", json={"version": current["version"], "notes": "Browser 2"})
    assert r3.status_code == 200


def test_template_change_does_not_touch_existing_plans(app, seeded, admin, teacher_a):
    cls = create_class(teacher_a)
    _init(teacher_a, cls)
    before = teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"]
    tpl = admin.get("/api/v1/admin/templates").json()["items"][0]
    units = [{"topic_id": u["topic_id"], "estimated_lessons": 1} for u in tpl["units"]]
    assert admin.patch(f"/api/v1/admin/templates/{tpl['id']}", json={"version": tpl["version"], "units": units}).status_code == 200
    assert teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"] == before


def test_delete_class_removes_units_keeps_materials(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    _init(teacher_a, cls)
    assert teacher_a.delete(f"/api/v1/classes/{cls['id']}").status_code == 204
    assert teacher_a.get(f"/api/v1/classes/{cls['id']}").status_code == 404
    assert teacher_a.get("/api/v1/materials").json()["total"] == 10


# -- Empfehlungen --------------------------------------------------------------

def test_a07_scores_and_determinism(app, seeded, admin, teacher_a):
    ref = reference(admin)
    # Zusätzliche freigegebene Materialien zum Thema Mengen erzeugen (verschiedene Punkte)

    from app.db import db_session
    from app.models import CurriculumReference, Material

    t_mengen = topic_id(ref, "Mengen erkennen und zählen")
    with db_session() as db:
        m11 = db.get(CurriculumReference, next(c["id"] for c in ref["curriculum"] if c["section_code"] == "M 1/2 1.1"))
        m12 = db.get(CurriculumReference, next(c["id"] for c in ref["curriculum"] if c["section_code"] == "M 1/2 1.2"))
        db.add_all(
            [
                Material(topic_id=t_mengen, title="B Zählen Basis", type="worksheet", level="basis", duration_minutes=20, status="released", curriculum=[m11]),
                Material(topic_id=t_mengen, title="A Zählen ohne Bezug", type="worksheet", level="basis", duration_minutes=20, status="released", curriculum=[m12]),
                Material(topic_id=t_mengen, title="C Zählen Entwurf", type="worksheet", level="basis", duration_minutes=20, status="draft", curriculum=[m11]),
            ]
        )
        db.commit()

    cls = create_class(teacher_a)
    _init(teacher_a, cls)
    params = {"week_start": "2026-09-21", "level": "basis"}
    r1 = teacher_a.get(f"/api/v1/classes/{cls['id']}/recommendations", params=params).json()
    r2 = teacher_a.get(f"/api/v1/classes/{cls['id']}/recommendations", params=params).json()
    assert r1 == r2
    math = next(s for s in r1["subjects"] if s["subject_title"] == "Mathematik")
    got = [(i["material"]["title"], i["score"]) for i in math["items"]]
    assert got == [("B Zählen Basis", 125), ("Mengen zählen bis 10", 120), ("A Zählen ohne Bezug", 105)]
    assert "Entwurf" not in str(got)
    assert all(i["reason"] for i in math["items"])


def test_recommendations_free_week_and_fallback(app, seeded, teacher_a):
    cls = create_class(teacher_a)
    # Nichts eingeplant → leer
    r = teacher_a.get(f"/api/v1/classes/{cls['id']}/recommendations", params={"week_start": "2026-11-02"}).json()
    assert all(s["mode"] == "empty" and s["items"] == [] for s in r["subjects"])
    _init(teacher_a, cls)
    # Herbstferien: keine Einheit eingeplant → nächstes offenes Thema als gekennzeichneter Vorschlag, nicht eingeplant
    r = teacher_a.get(f"/api/v1/classes/{cls['id']}/recommendations", params={"week_start": "2026-11-02"}).json()
    for s in r["subjects"]:
        assert s["mode"] == "next_open_topic"
        assert all(i["reason"].startswith("Vorschlag") for i in s["items"])
    units = teacher_a.get(f"/api/v1/classes/{cls['id']}/units", params={"from": "2026-11-02", "to": "2026-11-02"}).json()["items"]
    assert units == []  # keine automatische Befüllung


def test_max_five_per_subject(app, seeded, teacher_a):
    from app.db import db_session
    from app.models import Material

    ref = reference(teacher_a)
    t = topic_id(ref, "Mengen erkennen und zählen")
    with db_session() as db:
        for i in range(8):
            db.add(Material(topic_id=t, title=f"Zusatz {i}", type="worksheet", level="basis", duration_minutes=20, status="released"))
        db.commit()
    cls = create_class(teacher_a)
    _init(teacher_a, cls)
    r = teacher_a.get(f"/api/v1/classes/{cls['id']}/recommendations", params={"week_start": "2026-09-21"}).json()
    math = next(s for s in r["subjects"] if s["subject_title"] == "Mathematik")
    assert len(math["items"]) == 5
