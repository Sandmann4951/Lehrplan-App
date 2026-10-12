"""F03, F10, F12, A03, A04: Suche, Freigabe, Dateien."""
from datetime import date

from .conftest import Api, reference, subject_id, topic_id

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _draft(admin: Api, ref: dict, title: str = "Neues Arbeitsblatt", topic: str = "Mengen erkennen und zählen", level: str = "basis") -> dict:
    r = admin.post(
        "/api/v1/admin/materials",
        json={"topic_id": topic_id(ref, topic), "title": title, "type": "worksheet", "level": level, "duration_minutes": 30, "author": "Test", "license_text": "CC BY 4.0"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_a03_filter_subject_topic_level_only_released(app, seeded, admin, teacher_a):
    ref = reference(teacher_a)
    m_id = subject_id(ref, "M")
    t_id = topic_id(ref, "Zahlen bis 10 zerlegen")
    draft = _draft(admin, ref, "Entwurf zerlegen", "Zahlen bis 10 zerlegen", "differenziert")
    r = teacher_a.get("/api/v1/materials", params={"subject": m_id, "topic": t_id, "level": "differenziert"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["title"] for i in items] == ["Zahlen zerlegen"]
    assert all(i["status"] == "released" for i in items)
    assert draft["id"] not in [i["id"] for i in items]
    # Entwurf über Detail-URL nicht sichtbar
    assert teacher_a.get(f"/api/v1/materials/{draft['id']}").status_code == 404


def test_filters_and_or_semantics_and_paging(app, seeded, teacher_a):
    ref = reference(teacher_a)
    r = teacher_a.get("/api/v1/materials", params=[("type", "lesson_plan"), ("type", "assessment")])
    assert r.json()["total"] == 4  # ODER innerhalb eines Filters
    r = teacher_a.get("/api/v1/materials", params=[("type", "lesson_plan"), ("subject", subject_id(ref, "D"))])
    assert r.json()["total"] == 1  # UND zwischen Filtern
    r = teacher_a.get("/api/v1/materials", params={"page_size": 3, "page": 2, "sort": "title"})
    body = r.json()
    assert body["total"] == 10 and body["page"] == 2 and body["page_size"] == 3 and len(body["items"]) == 3
    assert teacher_a.get("/api/v1/materials", params={"page_size": 101}).status_code == 422
    r = teacher_a.get("/api/v1/materials", params={"duration_max": 20})
    assert {i["type"] for i in r.json()["items"]} == {"assessment"}


def test_text_search_title_description_keywords(app, seeded, teacher_a):
    r = teacher_a.get("/api/v1/materials", params={"q": "Schüttelbox"})  # nur in Beschreibung
    assert [i["title"] for i in r.json()["items"]] == ["Zahlen zerlegen"]
    r = teacher_a.get("/api/v1/materials", params={"q": "Rechengeschichte"})  # Schlagwort
    assert [i["title"] for i in r.json()["items"]] == ["Plus und minus mit Plättchen"]
    r = teacher_a.get("/api/v1/materials", params={"q": "zahlen"})
    assert r.json()["items"][0]["title"] in ("Zahlen vergleichen", "Zahlen zerlegen")  # Titeltreffer zuerst


def test_competency_filter(app, seeded, teacher_a):
    ref = reference(teacher_a)
    c = next(c for c in ref["curriculum"] if c["section_code"] == "M 1/2 1.2")
    r = teacher_a.get("/api/v1/materials", params={"competency": c["id"]})
    assert {i["title"] for i in r.json()["items"]} == {"Zahlen zerlegen", "Plus und minus mit Plättchen"}


def test_a04_main_and_solution_separately(app, seeded, teacher_a):
    items = teacher_a.get("/api/v1/materials", params={"q": "Anlaute"}).json()["items"]
    detail = teacher_a.get(f"/api/v1/materials/{items[0]['id']}").json()
    files = {f["purpose"]: f for f in detail["files"]}
    assert set(files) == {"main", "solution"}
    r = teacher_a.get(files["main"]["url"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and "inline" in r.headers["content-disposition"]
    r = teacher_a.get(files["solution"]["url"], params={"download": True})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert detail["is_demo"] is True


def test_missing_solution_reported(app, seeded, teacher_a):
    items = teacher_a.get("/api/v1/materials", params={"type": "lesson_plan"}).json()["items"]
    assert all(i["has_solution"] is False for i in items)


def test_a04_file_url_without_login_rejected(app, seeded, teacher_a):
    items = teacher_a.get("/api/v1/materials").json()["items"]
    detail = teacher_a.get(f"/api/v1/materials/{items[0]['id']}").json()
    anon = Api(app)
    r = anon.get(detail["files"][0]["url"])
    assert r.status_code == 401


def test_a04_upload_validation(app, seeded, admin):
    ref = reference(admin)
    m = _draft(admin, ref)
    url = f"/api/v1/admin/materials/{m['id']}/files"
    r = admin.post(url, data={"purpose": "main", "version": m["version"]}, files={"file": ("bild.png", b"\x89PNG....", "image/png")})
    assert r.status_code == 415
    r = admin.post(url, data={"purpose": "main", "version": m["version"]}, files={"file": ("fake.pdf", b"kein pdf", "application/pdf")})
    assert r.status_code == 415
    big = b"%PDF-" + b"0" * (20 * 1024 * 1024)
    r = admin.post(url, data={"purpose": "main", "version": m["version"]}, files={"file": ("gross.pdf", big, "application/pdf")})
    assert r.status_code == 413
    r = admin.post(url, data={"purpose": "main", "version": m["version"]}, files={"file": ("../../etc/passwd.pdf", PDF, "application/pdf")})
    assert r.status_code == 422
    r = admin.post(url, data={"purpose": "main", "version": m["version"]}, files={"file": ("blatt.pdf", PDF, "application/pdf")})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == m["version"] + 1
    assert r.json()["status"] == "draft"


def test_release_workflow_requires_checks(app, seeded, admin):
    ref = reference(admin)
    m = _draft(admin, ref)
    me = admin.get("/api/v1/auth/me").json()["user"]
    r = admin.post(f"/api/v1/admin/materials/{m['id']}/release", json={"version": m["version"]})
    assert r.status_code == 422  # noch nicht geprüft
    r = admin.post(f"/api/v1/admin/materials/{m['id']}/review", json={"version": m["version"], "reviewer_id": me["id"], "reviewed_at": date.today().isoformat()})
    assert r.status_code == 200
    m = r.json()
    r = admin.post(f"/api/v1/admin/materials/{m['id']}/release", json={"version": m["version"]})
    assert r.status_code == 422
    problems = " ".join(r.json()["problems"])
    assert "Kompetenzreferenz" in problems and "Hauptdatei" in problems

    # Bezug prüfen, Datei hochladen → Freigabe möglich
    c = next(c for c in ref["curriculum"] if c["section_code"] == "M 1/2 1.1")
    r = admin.patch(f"/api/v1/admin/curriculum/{c['id']}", json={"version": c["version"], "verification_status": "verified"})
    assert r.status_code == 200
    m = admin.patch(f"/api/v1/admin/materials/{m['id']}", json={"version": m["version"], "curriculum_ids": [c["id"]]}).json()
    m = admin.post(f"/api/v1/admin/materials/{m['id']}/files", data={"purpose": "main", "version": m["version"]}, files={"file": ("a.pdf", PDF, "application/pdf")}).json()
    r = admin.post(f"/api/v1/admin/materials/{m['id']}/release", json={"version": m["version"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "released" and r.json()["is_demo"] is False


def test_archived_not_in_search(app, seeded, admin, teacher_a):
    item = teacher_a.get("/api/v1/materials", params={"q": "Anlaute"}).json()["items"][0]
    r = admin.post(f"/api/v1/admin/materials/{item['id']}/archive", json={"version": item["version"]})
    assert r.status_code == 200
    assert teacher_a.get("/api/v1/materials", params={"q": "Anlaute"}).json()["total"] == 0


def test_favorites_persist_after_logout(app, seeded, teacher_a):
    item = teacher_a.get("/api/v1/materials").json()["items"][0]
    teacher_a.put(f"/api/v1/favorites/{item['id']}")
    teacher_a.post("/api/v1/auth/logout")
    again = Api(app, "a@schule.test")
    favs = again.get("/api/v1/favorites").json()["items"]
    assert [f["id"] for f in favs] == [item["id"]]


def test_text_fields_stored_as_text(app, seeded, admin):
    ref = reference(admin)
    m = _draft(admin, ref, "<script>alert(1)</script>")
    assert admin.get(f"/api/v1/admin/materials/{m['id']}").json()["title"] == "<script>alert(1)</script>"
