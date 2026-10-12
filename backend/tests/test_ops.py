"""A01, A10, F13: Seed, Import, Sicherung und Wiederherstellung."""
import hashlib
import json
import tarfile

import pytest
from sqlalchemy import func, select

from app.config import reload_settings, settings
from app.db import db_session, reset_engine
from app.migrations import upgrade_head
from app.models import Material, MaterialFile, PlanUnit, Topic, User
from app.seed.loader import load_seed
from app.services.backup import BackupError, create_backup, restore_backup, verify_backup

from .conftest import Api, create_class


def test_a01_seed_idempotent(seeded):
    with db_session() as db:
        counts = (db.scalar(select(func.count()).select_from(Topic)), db.scalar(select(func.count()).select_from(Material)), db.scalar(select(func.count()).select_from(MaterialFile)))
        created = load_seed(db)
        assert all(v == 0 for v in created.values())
        assert counts == (10, 10, 18)
        assert (db.scalar(select(func.count()).select_from(Topic)), db.scalar(select(func.count()).select_from(Material))) == (10, 10)


def test_calendar_import_preview_and_apply(app, seeded, admin):
    payload = {
        "school_year": {"label": "2027/2028", "starts_on": "2027-09-14", "ends_on": "2028-07-28"},
        "source": "Testquelle",
        "closures": [
            {"title": "Herbstferien", "starts_on": "2027-11-02", "ends_on": "2027-11-05", "kind": "holiday"},
            {"title": "Fehler", "starts_on": "2027-12-10", "ends_on": "2027-12-01"},
            {"title": "Außerhalb", "starts_on": "2029-01-01", "ends_on": "2029-01-02"},
        ],
    }
    r = admin.post("/api/v1/admin/calendar/import", json=payload, params={"dry_run": True})
    body = r.json()
    assert len(body["errors"]) == 2 and body["applied"] is False
    r = admin.post("/api/v1/admin/calendar/import", json=payload, params={"dry_run": False})
    assert r.json()["applied"] is False  # Fehler verhindern die Übernahme
    payload["closures"] = payload["closures"][:1]
    r = admin.post("/api/v1/admin/calendar/import", json=payload, params={"dry_run": False})
    assert r.json()["applied"] is True
    years = admin.get("/api/v1/admin/calendar").json()["school_years"]
    y = next(y for y in years if y["label"] == "2027/2028")
    assert y["closures"][0]["review_status"] == "unreviewed"
    assert y["status"]["demo_only"] is True


def test_content_import_creates_drafts(app, seeded, admin):
    ref = admin.get("/api/v1/reference").json()
    topic = ref["topics"][0]
    payload = {"schema_version": 1, "materials": [{"id": "11111111-1111-4111-8111-111111111111", "topic_id": topic["id"], "title": "Import", "type": "worksheet", "level": "basis", "duration_minutes": 15}]}
    r = admin.post("/api/v1/admin/import/content", json=payload, params={"dry_run": False})
    assert r.json()["applied"] is True, r.json()
    m = admin.get("/api/v1/admin/materials/11111111-1111-4111-8111-111111111111").json()
    assert m["status"] == "draft"
    bad = {"schema_version": 1, "materials": [{"topic_id": "gibt-es-nicht", "title": "X", "type": "worksheet", "level": "basis", "duration_minutes": 15}]}
    r = admin.post("/api/v1/admin/import/content", json=bad, params={"dry_run": False})
    assert r.json()["errors"] and r.json()["applied"] is False


def test_maintenance_lock_blocks_writes(app, seeded, teacher_a):
    settings.maintenance_lock.write_text("{}")
    try:
        ref = teacher_a.get("/api/v1/reference")
        assert ref.status_code == 200  # Lesen geht
        r = teacher_a.post("/api/v1/classes", json={"name": "x", "school_year_id": ref.json()["school_years"][0]["id"]})
        assert r.status_code == 503
    finally:
        settings.maintenance_lock.unlink()


def _file_hashes() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in settings.materials_dir.rglob("*") if p.is_file()}


def test_a10_backup_restore_into_empty_environment(app, seeded, teacher_a, tmp_path, monkeypatch):
    cls = create_class(teacher_a)
    teacher_a.post(f"/api/v1/classes/{cls['id']}/initialize-plan", json={"confirm": True})
    with db_session() as db:
        users_before = sorted(db.scalars(select(User.email)).all())
        units_before = db.scalar(select(func.count()).select_from(PlanUnit))
    hashes_before = _file_hashes()

    archive = create_backup("manual", tmp_path / "export", settle_s=0)
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert "manifest.json" in names and "lehrplan.sqlite3" in names
    manifest = json.loads(tarfile.open(archive).extractfile("manifest.json").read())
    assert manifest["schema_version"] == "0001" and manifest["software_version"]
    assert len([k for k in manifest["files"] if k.startswith("materials/")]) == 18

    # Testdaten verändern
    teacher_a.delete(f"/api/v1/classes/{cls['id']}")

    # Leere Umgebung
    reset_engine()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "leer"))
    reload_settings()
    assert not settings.sqlite_path.exists()
    restore_backup(archive)
    upgrade_head()
    with db_session() as db:
        assert sorted(db.scalars(select(User.email)).all()) == users_before
        assert db.scalar(select(func.count()).select_from(PlanUnit)) == units_before
    assert _file_hashes() == hashes_before
    # Login funktioniert in der wiederhergestellten Umgebung
    from app.main import create_app

    api = Api(create_app(enable_background=False), "a@schule.test")
    assert len(api.get("/api/v1/classes").json()["items"]) == 1


def test_restore_rejects_tampered_backup(seeded, tmp_path):
    archive = create_backup("manual", tmp_path / "b", settle_s=0)
    work = tmp_path / "x"
    work.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(work, filter="data")
    (work / "lehrplan.sqlite3").write_bytes(b"manipuliert")
    bad = tmp_path / "bad.tar.gz"
    with tarfile.open(bad, "w:gz") as tar:
        for p in work.iterdir():
            tar.add(p, arcname=p.name)
    with pytest.raises(BackupError, match="Prüfsumme"):
        verify_backup(bad, tmp_path / "check")


def test_restore_refuses_while_running(seeded, tmp_path):
    archive = create_backup("manual", tmp_path / "b", settle_s=0)
    settings.heartbeat_file.touch()
    try:
        with pytest.raises(BackupError, match="stoppen"):
            restore_backup(archive)
    finally:
        settings.heartbeat_file.unlink()


def test_restore_keeps_pre_restore_backup(seeded, tmp_path):
    archive = create_backup("manual", tmp_path / "b", settle_s=0)
    result = restore_backup(archive)
    assert result["pre_restore_backup"] and "pre-restore" in result["pre_restore_backup"]


def test_health_and_openapi(app, env):
    api = Api(app)
    assert api.get("/api/v1/health").json()["status"] == "ok"
    spec = api.get("/api/v1/openapi.json").json()
    assert "/api/v1/classes/{class_id}/recommendations" in spec["paths"]
