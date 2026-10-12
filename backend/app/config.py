"""Zentrale Konfiguration aus Umgebungsvariablen."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "ja", "on"}


@dataclass
class Settings:
    data_dir: Path
    database_url: str
    session_hours: int = 8
    cookie_secure: bool = False
    tls_cert_file: str | None = None
    tls_key_file: str | None = None
    max_upload_bytes: int = 20 * 1024 * 1024
    backup_auto: bool = True
    backup_time: str = "02:30"
    backup_keep: int = 14
    login_max_failures: int = 10
    login_window_minutes: int = 15
    frontend_dist: Path | None = None
    busy_timeout_ms: int = 5000
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Europe/Berlin"))

    @property
    def materials_dir(self) -> Path:
        return self.data_dir / "materials"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def maintenance_lock(self) -> Path:
        return self.data_dir / "maintenance.lock"

    @property
    def heartbeat_file(self) -> Path:
        return self.data_dir / "server.heartbeat"

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url[len(prefix):])
        return None


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[2] / "data")).resolve()
    database_url = os.environ.get("DATABASE_URL") or f"sqlite:///{data_dir / 'lehrplan.sqlite3'}"
    cert = os.environ.get("TLS_CERT_FILE") or None
    key = os.environ.get("TLS_KEY_FILE") or None
    tls = bool(cert and key)
    dist = os.environ.get("FRONTEND_DIST")
    if dist is None:
        candidate = Path(__file__).resolve().parents[2] / "frontend" / "dist"
        dist_path = candidate if candidate.exists() else None
    else:
        dist_path = Path(dist) if dist else None
    return Settings(
        data_dir=data_dir,
        database_url=database_url,
        session_hours=int(os.environ.get("SESSION_HOURS", "8")),
        cookie_secure=_bool("COOKIE_SECURE", tls),
        tls_cert_file=cert,
        tls_key_file=key,
        max_upload_bytes=int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024,
        backup_auto=_bool("BACKUP_AUTO", True),
        backup_time=os.environ.get("BACKUP_TIME", "02:30"),
        backup_keep=int(os.environ.get("BACKUP_KEEP", "14")),
        frontend_dist=dist_path,
    )


settings = load_settings()


def reload_settings() -> Settings:
    """Für Tests und CLI: Einstellungen neu einlesen (in-place, damit Importe gültig bleiben)."""
    new = load_settings()
    settings.__dict__.update(new.__dict__)
    return settings
