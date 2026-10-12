"""Alembic-Anbindung: Migrationen programmatisch ausführen."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from .config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def upgrade_head() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(), "head")
