from __future__ import annotations


import pytest
from fastapi.testclient import TestClient

from app.config import reload_settings, settings
from app.db import db_session, reset_engine
from app.main import create_app
from app.migrations import upgrade_head
from app.models import ROLE_ADMIN, ROLE_TEACHER, User
from app.security import hash_password

PASSWORD = "Testpasswort123"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BACKUP_AUTO", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_engine()
    reload_settings()
    upgrade_head()
    yield settings
    reset_engine()


@pytest.fixture()
def seeded(env):
    from app.seed.loader import load_seed

    with db_session() as db:
        load_seed(db)
    return env


def make_user(email: str, role: str = ROLE_TEACHER, name: str | None = None) -> str:
    with db_session() as db:
        u = User(email=email, display_name=name or email, role=role, password_hash=hash_password(PASSWORD))
        db.add(u)
        db.commit()
        return u.id


class Api:
    """TestClient mit Sitzung und CSRF-Header."""

    def __init__(self, app, email: str | None = None):
        self.client = TestClient(app)
        self.csrf = None
        if email:
            self.login(email)

    def login(self, email: str, password: str = PASSWORD):
        r = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        if r.status_code == 200:
            self.csrf = r.json()["csrf_token"]
        return r

    def _h(self, headers=None):
        h = dict(headers or {})
        if self.csrf:
            h.setdefault("X-CSRF-Token", self.csrf)
        return h

    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def post(self, url, **kw):
        kw["headers"] = self._h(kw.get("headers"))
        return self.client.post(url, **kw)

    def patch(self, url, **kw):
        kw["headers"] = self._h(kw.get("headers"))
        return self.client.patch(url, **kw)

    def put(self, url, **kw):
        kw["headers"] = self._h(kw.get("headers"))
        return self.client.put(url, **kw)

    def delete(self, url, **kw):
        kw["headers"] = self._h(kw.get("headers"))
        return self.client.delete(url, **kw)


@pytest.fixture()
def app(env):
    return create_app(enable_background=False)


@pytest.fixture()
def admin(app, env):
    make_user("admin@schule.test", ROLE_ADMIN, "Admin")
    return Api(app, "admin@schule.test")


@pytest.fixture()
def teacher_a(app, env):
    make_user("a@schule.test", ROLE_TEACHER, "Lehrkraft A")
    return Api(app, "a@schule.test")


@pytest.fixture()
def teacher_b(app, env):
    make_user("b@schule.test", ROLE_TEACHER, "Lehrkraft B")
    return Api(app, "b@schule.test")


def reference(api: Api) -> dict:
    return api.get("/api/v1/reference").json()


def subject_id(ref: dict, code: str) -> str:
    return next(s["id"] for s in ref["subjects"] if s["code"] == code)


def topic_id(ref: dict, title: str) -> str:
    return next(t["id"] for t in ref["topics"] if t["title"] == title)


def create_class(api: Api, name: str = "1a", **extra) -> dict:
    ref = reference(api)
    body = {"name": name, "school_year_id": ref["school_years"][0]["id"], **extra}
    r = api.post("/api/v1/classes", json=body)
    assert r.status_code == 201, r.text
    return r.json()
