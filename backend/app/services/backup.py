"""F13 Sicherung und Wiederherstellung.

Sicherung:
- setzt eine Wartungssperre (Schreibanfragen erhalten HTTP 503),
- erstellt einen konsistenten Datenbankstand über die SQLite-Backup-API,
- kopiert alle Materialdateien,
- schreibt ein Manifest mit Schema-/Softwareversion und SHA-256-Prüfsummen,
- packt alles in ein tar.gz-Archiv.

Wiederherstellung nur bei gestoppter Anwendung: Manifest und Prüfsummen werden
geprüft, der aktuelle Stand zusätzlich gesichert, dann Datenbank und Dateien
gemeinsam ersetzt.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from ..config import settings

MANIFEST = "manifest.json"
DB_NAME = "lehrplan.sqlite3"
FORMAT_VERSION = 1


class BackupError(Exception):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def current_schema_version(db_path: Path) -> str | None:
    if not db_path.exists():
        return None
    con = sqlite3.connect(db_path)
    try:
        row = con.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def server_running(max_age_s: int = 90) -> bool:
    hb = settings.heartbeat_file
    if not hb.exists():
        return False
    return (time.time() - hb.stat().st_mtime) < max_age_s


class MaintenanceLock:
    def __init__(self, reason: str, settle_s: float = 0.5):
        self.reason = reason
        self.settle_s = settle_s

    def __enter__(self):
        lock = settings.maintenance_lock
        lock.parent.mkdir(parents=True, exist_ok=True)
        if lock.exists() and time.time() - lock.stat().st_mtime < 3600:
            raise BackupError("Eine andere Wartungsaktion läuft bereits (maintenance.lock).")
        lock.write_text(json.dumps({"reason": self.reason, "pid": os.getpid(), "since": datetime.now(timezone.utc).isoformat()}))
        # Laufende Schreibtransaktionen abschließen lassen
        time.sleep(self.settle_s)
        return self

    def __exit__(self, *exc):
        settings.maintenance_lock.unlink(missing_ok=True)


def create_backup(kind: str = "manual", target_dir: Path | None = None, settle_s: float = 0.5) -> Path:
    db_path = settings.sqlite_path
    if db_path is None:
        raise BackupError("Sicherung ist nur für SQLite implementiert.")
    if not db_path.exists():
        raise BackupError(f"Datenbank nicht gefunden: {db_path}")
    target_dir = target_dir or settings.backup_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = target_dir / f"lehrplan-{kind}-{stamp}.tar.gz"

    with MaintenanceLock(f"backup-{kind}", settle_s), tempfile.TemporaryDirectory(dir=target_dir) as tmp:
        tmpdir = Path(tmp)
        snapshot = tmpdir / DB_NAME
        src = sqlite3.connect(db_path, timeout=30)
        dst = sqlite3.connect(snapshot)
        try:
            with dst:
                src.backup(dst)  # konsistenter Stand über SQLite-Backup-API
        finally:
            dst.close()
            src.close()
        integrity = sqlite3.connect(snapshot).execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise BackupError(f"Integritätsprüfung des Snapshots fehlgeschlagen: {integrity}")

        files: dict[str, str] = {DB_NAME: _sha256(snapshot)}
        mat_src = settings.materials_dir
        mat_dst = tmpdir / "materials"
        mat_dst.mkdir()
        if mat_src.exists():
            for p in sorted(mat_src.rglob("*")):
                if p.is_file() and not p.name.endswith(".tmp"):
                    rel = p.relative_to(mat_src)
                    (mat_dst / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, mat_dst / rel)
                    files[f"materials/{rel.as_posix()}"] = _sha256(mat_dst / rel)
        manifest = {
            "format_version": FORMAT_VERSION,
            "kind": kind,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "software_version": __version__,
            "schema_version": current_schema_version(snapshot),
            "files": files,
        }
        (tmpdir / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        partial = archive.with_suffix(".partial")
        with tarfile.open(partial, "w:gz") as tar:
            tar.add(tmpdir / MANIFEST, arcname=MANIFEST)
            tar.add(snapshot, arcname=DB_NAME)
            tar.add(mat_dst, arcname="materials")
        os.replace(partial, archive)
    return archive


def prune_backups(kind: str = "daily", keep: int | None = None) -> list[Path]:
    keep = settings.backup_keep if keep is None else keep
    archives = sorted(settings.backup_dir.glob(f"lehrplan-{kind}-*.tar.gz"))
    removed = archives[:-keep] if keep > 0 and len(archives) > keep else []
    for p in removed:
        p.unlink(missing_ok=True)
    return removed


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if dest != target and dest not in target.parents:
            raise BackupError(f"Unzulässiger Pfad im Archiv: {member.name}")
        if member.issym() or member.islnk() or member.isdev():
            raise BackupError(f"Unzulässiger Dateityp im Archiv: {member.name}")
    tar.extractall(dest, filter="data")


def verify_backup(archive: Path, workdir: Path) -> dict:
    """Entpackt nach workdir und prüft Manifest und Prüfsummen."""
    if not archive.exists():
        raise BackupError(f"Sicherung nicht gefunden: {archive}")
    with tarfile.open(archive, "r:gz") as tar:
        _safe_extract(tar, workdir)
    manifest_path = workdir / MANIFEST
    if not manifest_path.exists():
        raise BackupError("Manifest fehlt in der Sicherung.")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format_version") != FORMAT_VERSION:
        raise BackupError(f"Nicht unterstütztes Sicherungsformat: {manifest.get('format_version')}")
    for rel, digest in manifest.get("files", {}).items():
        p = workdir / rel
        if not p.exists():
            raise BackupError(f"Datei fehlt in der Sicherung: {rel}")
        if _sha256(p) != digest:
            raise BackupError(f"Prüfsumme stimmt nicht: {rel}")
    extra = {p.relative_to(workdir).as_posix() for p in workdir.rglob("*") if p.is_file()} - set(manifest["files"]) - {MANIFEST}
    if extra:
        raise BackupError(f"Unerwartete Dateien in der Sicherung: {sorted(extra)[:5]}")
    return manifest


def restore_backup(archive: Path, force: bool = False, pre_backup: bool = True) -> dict:
    from alembic.script import ScriptDirectory

    from ..migrations import alembic_config

    if server_running() and not force:
        raise BackupError("Die Anwendung scheint zu laufen. Bitte zuerst stoppen (scripts/stop.sh).")
    db_path = settings.sqlite_path
    if db_path is None:
        raise BackupError("Wiederherstellung ist nur für SQLite implementiert.")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=settings.data_dir) as tmp:
        work = Path(tmp) / "extract"
        work.mkdir()
        manifest = verify_backup(archive, work)
        known = {rev.revision for rev in ScriptDirectory.from_config(alembic_config()).walk_revisions()}
        if manifest.get("schema_version") not in known:
            raise BackupError(f"Unbekannte Schemaversion {manifest.get('schema_version')} – Sicherung stammt von einer neueren Software.")

        pre = None
        if pre_backup and db_path.exists():
            pre = create_backup("pre-restore", settle_s=0)

        # Datenbank und Dateien gemeinsam ersetzen
        staging_db = db_path.with_name(db_path.name + ".restore")
        shutil.copy2(work / DB_NAME, staging_db)
        old_mat = settings.materials_dir.with_name("materials.old")
        if old_mat.exists():
            shutil.rmtree(old_mat)
        if settings.materials_dir.exists():
            os.replace(settings.materials_dir, old_mat)
        shutil.copytree(work / "materials", settings.materials_dir)
        for suffix in ("-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)
        os.replace(staging_db, db_path)
        if old_mat.exists():
            shutil.rmtree(old_mat)
    return {"manifest": manifest, "pre_restore_backup": str(pre) if pre else None}
