"""F03/F04: Materialbibliothek, Detailansicht, Dateien und Merkliste."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import Auth, get_auth
from ..errors import invalid, not_found
from ..models import MATERIAL_LEVELS, MATERIAL_TYPES, Favorite, Material
from ..repositories.core import FavoriteRepository, ReferenceRepository
from ..serializers import (
    LEVEL_LABELS,
    TYPE_LABELS,
    curriculum_out,
    material_detail,
    material_summary,
    school_year_out,
    subject_out,
    topic_out,
)
from ..services.library import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX, SearchParams, get_visible_material, search_materials, storage_path

router = APIRouter(tags=["Bibliothek"])


@router.get("/reference", summary="Stammdaten für Filter und Formulare")
def reference_data(auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    repo = ReferenceRepository(db)
    return {
        "subjects": [subject_out(s) for s in repo.subjects()],
        "topics": [topic_out(t) for t in repo.topics()],
        "curriculum": [curriculum_out(c) for c in repo.curriculum()],
        "school_years": [school_year_out(y) for y in repo.school_years()],
        "material_types": [{"value": t, "label": TYPE_LABELS[t]} for t in MATERIAL_TYPES],
        "levels": [{"value": l, "label": LEVEL_LABELS[l]} for l in MATERIAL_LEVELS],
        "templates": [{"id": t.id, "name": t.name, "subject_id": t.subject_id, "units": len(t.units)} for t in repo.templates()],
    }


@router.get("/materials", summary="Materialsuche (nur freigegebene Materialien)")
def list_materials(
    subject: list[str] = Query(default=[]),
    topic: list[str] = Query(default=[]),
    competency: list[str] = Query(default=[]),
    level: list[str] = Query(default=[]),
    type: list[str] = Query(default=[]),
    duration_min: int | None = Query(default=None, ge=1),
    duration_max: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None, max_length=200),
    sort: str = Query(default="relevance", pattern="^(relevance|title)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    auth: Auth = Depends(get_auth),
    db: Session = Depends(get_db),
):
    bad_levels = [l for l in level if l not in MATERIAL_LEVELS]
    bad_types = [t for t in type if t not in MATERIAL_TYPES]
    if bad_levels or bad_types:
        raise invalid("Ungültiger Filterwert.", {**({"level": "Unbekanntes Niveau."} if bad_levels else {}), **({"type": "Unbekannter Materialtyp."} if bad_types else {})})
    params = SearchParams(subject, topic, competency, level, type, duration_min, duration_max, (q or "").strip() or None, sort, page, page_size)
    items, total = search_materials(db, params)
    favs = FavoriteRepository(db).ids_for_user(auth.user.id)
    return {"items": [material_summary(m, favs) for m in items], "total": total, "page": page, "page_size": page_size}


@router.get("/materials/{material_id}", summary="Materialdetails")
def get_material(material_id: str, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    m = get_visible_material(db, material_id, auth.user.id, auth.is_admin)
    return material_detail(m, FavoriteRepository(db).ids_for_user(auth.user.id))


@router.get("/materials/{material_id}/files/{file_id}", summary="PDF anzeigen oder herunterladen (nach Rechteprüfung)")
def get_file(material_id: str, file_id: str, download: bool = False, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    m = get_visible_material(db, material_id, auth.user.id, auth.is_admin)
    f = next((f for f in m.files if f.id == file_id), None)
    if f is None:
        raise not_found("Datei nicht gefunden.")
    path = storage_path(f.storage_key)
    if not path.exists():
        raise not_found("Datei fehlt im Speicher. Bitte Administrator informieren.")
    disposition = "attachment" if download else "inline"
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(f.original_name)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


# -- Merkliste -----------------------------------------------------------------

@router.get("/favorites", summary="Eigene Merkliste")
def list_favorites(auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    favs = db.scalars(
        select(Favorite)
        .where(Favorite.user_id == auth.user.id)
        .options(selectinload(Favorite.material).selectinload(Material.files), selectinload(Favorite.material).selectinload(Material.topic), selectinload(Favorite.material).selectinload(Material.curriculum))
        .order_by(Favorite.created_at.desc())
    ).all()
    ids = {f.material_id for f in favs}
    items = [material_summary(f.material, ids) for f in favs if f.material.status in ("released", "archived")]
    return {"items": items, "total": len(items), "page": 1, "page_size": max(len(items), 1)}


@router.put("/favorites/{material_id}", summary="Material merken")
def add_favorite(material_id: str, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    m = get_visible_material(db, material_id, auth.user.id, auth.is_admin)
    if FavoriteRepository(db).get(auth.user.id, m.id) is None:
        db.add(Favorite(user_id=auth.user.id, material_id=m.id))
        db.commit()
    return {"material_id": m.id, "is_favorite": True}


@router.delete("/favorites/{material_id}", summary="Material von Merkliste entfernen")
def remove_favorite(material_id: str, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    fav = FavoriteRepository(db).get(auth.user.id, material_id)
    if fav is None:
        raise not_found("Nicht auf der Merkliste.")
    db.delete(fav)
    db.commit()
    return {"material_id": material_id, "is_favorite": False}
