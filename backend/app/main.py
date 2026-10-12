"""FastAPI-Anwendung: REST-API unter /api/v1 und ausgelieferter Frontend-Build."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import admin, auth, library, planning
from .config import settings
from .errors import install_error_handlers

log = logging.getLogger("lehrplan")

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


async def _heartbeat_loop() -> None:
    while True:
        try:
            settings.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
            settings.heartbeat_file.touch()
        except OSError:
            log.warning("Heartbeat konnte nicht geschrieben werden")
        await asyncio.sleep(30)


async def _daily_backup_loop() -> None:
    from .services.backup import BackupError, create_backup, prune_backups

    while True:
        await asyncio.sleep(60)
        try:
            now = datetime.now(settings.timezone)
            hh, mm = (int(x) for x in settings.backup_time.split(":"))
            if (now.hour, now.minute) < (hh, mm):
                continue
            today = now.strftime("%Y%m%d")
            # Ein täglicher Stand pro lokalem Kalendertag
            marker = settings.backup_dir / f".daily-{today}"
            if marker.exists():
                continue
            path = await asyncio.to_thread(create_backup, "daily")
            settings.backup_dir.mkdir(parents=True, exist_ok=True)
            for old in settings.backup_dir.glob(".daily-*"):
                old.unlink(missing_ok=True)
            marker.touch()
            removed = prune_backups("daily")
            log.info("Tägliche Sicherung erstellt: %s (entfernt: %d)", path.name, len(removed))
        except BackupError as exc:
            log.error("Tägliche Sicherung fehlgeschlagen: %s", exc)
        except Exception:  # pragma: no cover
            log.exception("Tägliche Sicherung fehlgeschlagen")


def _acquire_scheduler_lock():
    """Nur ein Worker-Prozess führt die tägliche Sicherung aus (exklusive Dateisperre)."""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows ohne Docker
        return object()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    fh = open(settings.data_dir / "scheduler.lock", "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(_heartbeat_loop())]
    scheduler_lock = None
    if settings.backup_auto and settings.sqlite_path:
        scheduler_lock = _acquire_scheduler_lock()
        if scheduler_lock is not None:
            tasks.append(asyncio.create_task(_daily_backup_loop()))
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        if scheduler_lock is not None and hasattr(scheduler_lock, "close"):
            scheduler_lock.close()
        settings.heartbeat_file.unlink(missing_ok=True)


def create_app(enable_background: bool = True) -> FastAPI:
    app = FastAPI(
        title="Unterrichtsassistent Bayern – Pilot",
        version=__version__,
        description="Lokale Webanwendung für Materialbibliothek, Lehrplanbezüge und Wochenplanung (Deutsch/Mathematik, Klasse 1).",
        openapi_url="/api/v1/openapi.json",
        # Swagger-UI lädt Skripte von einem CDN – daher nur auf ausdrücklichen Wunsch (API_DOCS=true).
        docs_url="/api/v1/docs" if os.environ.get("API_DOCS", "").lower() in ("1", "true", "ja") else None,
        redoc_url=None,
        lifespan=lifespan if enable_background else None,
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def maintenance_and_headers(request: Request, call_next):
        if request.method in UNSAFE and request.url.path.startswith("/api/") and settings.maintenance_lock.exists():
            # Sperre älter als 1 h gilt als verwaist
            if time.time() - settings.maintenance_lock.stat().st_mtime < 3600:
                return JSONResponse(
                    status_code=503,
                    content={"code": "maintenance", "message": "Sicherung läuft. Bitte in wenigen Sekunden erneut speichern.", "field_errors": {}},
                    headers={"Retry-After": "5"},
                )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-src 'self'; object-src 'self'; frame-ancestors 'self'",
        )
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(planning.router, prefix=api_prefix)
    app.include_router(library.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)

    @app.get("/api/v1/health", tags=["Betrieb"], summary="Statusprüfung")
    def health():
        from .services.backup import current_schema_version

        return {
            "status": "ok",
            "version": __version__,
            "schema_version": current_schema_version(settings.sqlite_path) if settings.sqlite_path else None,
            "maintenance": settings.maintenance_lock.exists(),
        }

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    dist = settings.frontend_dist
    if not dist or not Path(dist).exists():
        return
    dist = Path(dist).resolve()
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"code": "not_found", "message": "Nicht gefunden.", "field_errors": {}})
        candidate = (dist / path).resolve()
        if path and dist in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
