"""Bibliotheksservice: Suche, Sichtbarkeit und Dateiablage."""
from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..errors import ApiError, not_found
from ..models import Favorite, Material, MaterialFile, PlanUnit, SchoolClass, plan_unit_materials
from ..repositories.core import MaterialRepository

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100


@dataclass
class SearchParams:
    subject_ids: list[str]
    topic_ids: list[str]
    curriculum_ids: list[str]
    levels: list[str]
    types: list[str]
    duration_min: int | None
    duration_max: int | None
    q: str | None
    sort: str
    page: int
    page_size: int


def _relevance(row: tuple[str, str, str, str], terms: list[str]) -> int:
    _, title, desc, keywords = (x.lower() for x in row)
    score = 0
    for t in terms:
        if t in title:
            score += 3
        if t in keywords:
            score += 2
        if t in desc:
            score += 1
    return score


def search_materials(db: Session, p: SearchParams, statuses: tuple[str, ...] = ("released",)) -> tuple[list[Material], int]:
    repo = MaterialRepository(db)
    rows = repo.search(
        statuses=statuses,
        subject_ids=p.subject_ids,
        topic_ids=p.topic_ids,
        curriculum_ids=p.curriculum_ids,
        levels=p.levels,
        types=p.types,
        duration_min=p.duration_min,
        duration_max=p.duration_max,
        text=p.q,
    )
    terms = (p.q or "").lower().split()
    if p.sort == "relevance" and terms:
        rows.sort(key=lambda r: (-_relevance(r, terms), r[1].lower(), r[0]))
    else:
        rows.sort(key=lambda r: (r[1].lower(), r[0]))
    start = (p.page - 1) * p.page_size
    page_ids = [r[0] for r in rows[start : start + p.page_size]]
    return repo.load_many(page_ids), len(rows)


def can_view_material(db: Session, material: Material, user_id: str, is_admin: bool) -> bool:
    """Freigegeben: alle. Archiviert: wenn in eigenem Plan oder Merkliste. Sonst nur Admin."""
    if is_admin or material.status == "released":
        return True
    if material.status == "archived":
        in_plan = db.scalar(
            select(PlanUnit.id)
            .join(plan_unit_materials, plan_unit_materials.c.plan_unit_id == PlanUnit.id)
            .join(SchoolClass, SchoolClass.id == PlanUnit.class_id)
            .where(plan_unit_materials.c.material_id == material.id, SchoolClass.owner_id == user_id)
            .limit(1)
        )
        if in_plan:
            return True
        fav = db.scalar(select(Favorite.id).where(Favorite.user_id == user_id, Favorite.material_id == material.id))
        return fav is not None
    return False


def get_visible_material(db: Session, material_id: str, user_id: str, is_admin: bool) -> Material:
    m = MaterialRepository(db).get(material_id)
    if m is None or not can_view_material(db, m, user_id, is_admin):
        raise not_found("Material nicht gefunden.")
    return m


# -- Dateiablage -----------------------------------------------------------

PDF_MAGIC = b"%PDF-"


def storage_path(storage_key: str) -> Path:
    # Schlüssel sind generiert (hex); zusätzliche Absicherung gegen Pfadmanipulation
    if not storage_key or any(c not in "0123456789abcdef" for c in storage_key):
        raise ApiError(400, "invalid_storage_key", "Ungültiger Dateischlüssel.")
    base = settings.materials_dir.resolve()
    path = (base / storage_key[:2] / storage_key).resolve()
    if base not in path.parents:
        raise ApiError(400, "invalid_storage_key", "Ungültiger Dateischlüssel.")
    return path


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name.replace("\\", "/")).strip() or "datei.pdf"
    cleaned = "".join(c for c in name if c.isalnum() or c in "._- äöüÄÖÜß")
    cleaned = cleaned.strip(". ") or "datei.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned[:200]


def validate_pdf(data: bytes, filename: str, content_type: str | None) -> None:
    if len(data) == 0:
        raise ApiError(422, "empty_file", "Die Datei ist leer.")
    if len(data) > settings.max_upload_bytes:
        raise ApiError(413, "file_too_large", f"Die Datei ist größer als {settings.max_upload_bytes // (1024 * 1024)} MB.")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ApiError(422, "invalid_filename", "Ungültiger Dateiname.")
    if not filename.lower().endswith(".pdf"):
        raise ApiError(415, "unsupported_media_type", "Nur PDF-Dateien sind erlaubt.")
    if content_type and content_type not in ("application/pdf", "application/x-pdf", "application/octet-stream"):
        raise ApiError(415, "unsupported_media_type", "Nur PDF-Dateien sind erlaubt.")
    if not data.startswith(PDF_MAGIC):
        raise ApiError(415, "unsupported_media_type", "Die Datei besitzt keine gültige PDF-Signatur.")


def write_blob(data: bytes) -> tuple[str, str]:
    """Schreibt Daten atomar unter generiertem Schlüssel. Liefert (storage_key, sha256)."""
    key = secrets.token_hex(20)
    path = storage_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return key, hashlib.sha256(data).hexdigest()


def delete_blob(storage_key: str) -> None:
    try:
        storage_path(storage_key).unlink(missing_ok=True)
    except ApiError:
        pass


def attach_file(db: Session, material: Material, purpose: str, data: bytes, filename: str, content_type: str | None) -> tuple[MaterialFile, str | None]:
    """Legt Datei ab und verknüpft sie. Gibt (Datei, alter Schlüssel zum Löschen nach Commit) zurück."""
    validate_pdf(data, filename, content_type)
    key, digest = write_blob(data)
    old_key = None
    existing = next((f for f in material.files if f.purpose == purpose), None)
    if existing is not None:
        old_key = existing.storage_key
        existing.storage_key = key
        existing.original_name = sanitize_filename(filename)
        existing.size_bytes = len(data)
        existing.sha256 = digest
        existing.mime_type = "application/pdf"
        f = existing
    else:
        f = MaterialFile(
            purpose=purpose,
            original_name=sanitize_filename(filename),
            storage_key=key,
            mime_type="application/pdf",
            size_bytes=len(data),
            sha256=digest,
        )
        material.files.append(f)
    material.version += 1
    return f, old_key


def file_is_valid(f: MaterialFile) -> bool:
    try:
        path = storage_path(f.storage_key)
    except ApiError:
        return False
    if not path.exists() or path.stat().st_size != f.size_bytes:
        return False
    with open(path, "rb") as fh:
        return fh.read(5) == PDF_MAGIC
