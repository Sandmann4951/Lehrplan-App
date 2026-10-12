"""F01, F12, A02: Anmeldung, Sitzungen, CSRF und Zugriffsschutz."""
from app.config import settings
from app.db import db_session
from app.models import User
from sqlalchemy import select

from .conftest import PASSWORD, Api, create_class, make_user, reference, subject_id, topic_id


def test_login_logout_me(app, teacher_a):
    r = teacher_a.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "a@schule.test"
    assert teacher_a.post("/api/v1/auth/logout").status_code == 200
    assert teacher_a.get("/api/v1/auth/me").status_code == 401


def test_email_normalized_and_wrong_password(app, env):
    make_user("lehrer@schule.test")
    api = Api(app)
    assert api.login("  LEHRER@Schule.Test ").status_code == 200
    r = Api(app).login("lehrer@schule.test", "falsch")
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"
    assert set(r.json()) >= {"code", "message", "field_errors"}


def test_password_hash_is_argon2id(env):
    make_user("x@schule.test")
    with db_session() as db:
        u = db.scalar(select(User).where(User.email == "x@schule.test"))
        assert u.password_hash.startswith("$argon2id$")
        assert PASSWORD not in u.password_hash


def test_cookie_flags(app, env):
    make_user("c@schule.test")
    r = Api(app).client.post("/api/v1/auth/login", json={"email": "c@schule.test", "password": PASSWORD})
    cookies = r.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("lp_session="))
    assert "HttpOnly" in session_cookie
    assert "samesite=lax" in session_cookie.lower()
    assert "Max-Age=28800" in session_cookie  # 8 Stunden


def test_csrf_required_for_writes(app, seeded, teacher_a):
    ref = reference(teacher_a)
    r = teacher_a.client.post("/api/v1/classes", json={"name": "x", "school_year_id": ref["school_years"][0]["id"]})
    assert r.status_code == 403
    assert r.json()["code"] == "csrf_failed"


def test_login_rate_limit(app, env):
    make_user("rl@schule.test")
    api = Api(app)
    for _ in range(settings.login_max_failures):
        assert api.login("rl@schule.test", "falsch").status_code == 401
    # Auch das richtige Passwort wird nun zeitlich gesperrt
    r = api.login("rl@schule.test", PASSWORD)
    assert r.status_code == 429


def test_locked_user_sessions_invalidated(app, seeded, admin, teacher_a):
    users = admin.get("/api/v1/admin/users").json()["items"]
    a = next(u for u in users if u["email"] == "a@schule.test")
    r = admin.patch(f"/api/v1/admin/users/{a['id']}", json={"version": a["version"], "active": False})
    assert r.status_code == 200
    assert teacher_a.get("/api/v1/auth/me").status_code == 401
    assert Api(app).login("a@schule.test").status_code == 401


def test_reset_password_forces_change(app, seeded, admin, teacher_a):
    users = admin.get("/api/v1/admin/users").json()["items"]
    a = next(u for u in users if u["email"] == "a@schule.test")
    r = admin.post(f"/api/v1/admin/users/{a['id']}/reset-password")
    temp = r.json()["temporary_password"]
    api = Api(app)
    assert api.login("a@schule.test", temp).status_code == 200
    r = api.get("/api/v1/classes")
    assert r.status_code == 403 and r.json()["code"] == "password_change_required"
    r = api.post("/api/v1/auth/change-password", json={"current_password": temp, "new_password": "NeuesPasswort2026"})
    assert r.status_code == 200
    assert api.get("/api/v1/classes").status_code == 200


def test_teacher_cannot_use_admin_endpoints(app, seeded, teacher_a):
    assert teacher_a.get("/api/v1/admin/users").status_code == 403
    assert teacher_a.post("/api/v1/admin/users", json={"email": "z@z.de", "display_name": "Z"}).status_code == 403


def test_a02_isolation_between_teachers(app, seeded, teacher_a, teacher_b):
    cls = create_class(teacher_a)
    ref = reference(teacher_a)
    d = subject_id(ref, "D")
    unit = teacher_a.post(
        f"/api/v1/classes/{cls['id']}/units",
        json={"subject_id": d, "topic_id": topic_id(ref, "Laute hören und unterscheiden"), "week_start_date": "2026-09-21", "planned_lessons": 3},
    ).json()["unit"]
    mat = teacher_a.get("/api/v1/materials").json()["items"][0]
    assert teacher_a.put(f"/api/v1/favorites/{mat['id']}").status_code == 200

    # B sieht nichts von A – weder Liste noch direkte Aufrufe
    assert teacher_b.get("/api/v1/classes").json()["items"] == []
    assert teacher_b.get(f"/api/v1/classes/{cls['id']}").status_code == 404
    assert teacher_b.get(f"/api/v1/classes/{cls['id']}/units").status_code == 404
    assert teacher_b.get(f"/api/v1/classes/{cls['id']}/dashboard").status_code == 404
    assert teacher_b.get(f"/api/v1/classes/{cls['id']}/recommendations", params={"week_start": "2026-09-21"}).status_code == 404
    assert teacher_b.patch(f"/api/v1/classes/{cls['id']}", json={"version": 1, "name": "gehackt"}).status_code == 404
    assert teacher_b.delete(f"/api/v1/classes/{cls['id']}").status_code == 404
    assert teacher_b.patch(f"/api/v1/units/{unit['id']}", json={"version": unit["version"], "status": "completed"}).status_code == 404
    assert teacher_b.delete(f"/api/v1/units/{unit['id']}").status_code == 404
    assert teacher_b.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={"confirm": True}).status_code == 404
    assert teacher_b.get("/api/v1/favorites").json()["items"] == []
    assert teacher_b.delete(f"/api/v1/favorites/{mat['id']}").status_code == 404

    # A's Daten unverändert
    assert teacher_a.get(f"/api/v1/classes/{cls['id']}").json()["name"] == "1a"
    units = teacher_a.get(f"/api/v1/classes/{cls['id']}/units").json()["items"]
    assert units[0]["status"] == "planned"
    assert len(teacher_a.get("/api/v1/favorites").json()["items"]) == 1


def test_admin_has_no_access_to_teacher_plans(app, seeded, admin, teacher_a):
    cls = create_class(teacher_a)
    assert admin.get(f"/api/v1/classes/{cls['id']}").status_code == 404
    assert admin.get(f"/api/v1/classes/{cls['id']}/units").status_code == 404
    assert admin.get("/api/v1/classes").json()["items"] == []


def test_audit_has_no_secrets(app, seeded, admin):
    r = admin.post("/api/v1/admin/users", json={"email": "neu@schule.test", "display_name": "Neu"})
    temp = r.json()["temporary_password"]
    events = admin.get("/api/v1/admin/audit").json()["items"]
    assert events
    assert temp not in str(events)
