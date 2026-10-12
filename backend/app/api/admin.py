"""Administration: Benutzer, Bibliothek, Lehrplanstammdaten, Kalender, Vorlagen, Importe.

Administratorrechte geben bewusst KEINEN Zugriff auf persönliche Pläne.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..audit import audit
from ..config import settings
from ..db import get_db
from ..deps import Auth, require_admin
from ..errors import ApiError, check_version, invalid, not_found
from ..models import (
    ROLE_ADMIN,
    AuditEvent,
    CalendarClosure,
    CurriculumReference,
    Material,
    PlanTemplate,
    SchoolYear,
    Subject,
    TemplateUnit,
    Topic,
    User,
    UserSession,
    plan_unit_materials,
    template_unit_materials,
)
from ..repositories.core import MaterialRepository, ReferenceRepository
from ..schemas import (
    ClosureIn,
    ClosureUpdate,
    CurriculumIn,
    CurriculumUpdate,
    MaterialIn,
    MaterialReviewIn,
    MaterialUpdate,
    SchoolYearIn,
    SchoolYearUpdate,
    TemplateIn,
    TemplateUpdate,
    TopicIn,
    TopicUpdate,
    UserCreate,
    UserUpdate,
    VersionIn,
)
from ..security import generate_temp_password, hash_password
from ..serializers import (
    closure_out,
    curriculum_out,
    material_detail,
    material_summary,
    school_year_out,
    template_out,
    topic_out,
    user_out,
)
from ..services.library import PAGE_SIZE_MAX, SearchParams, attach_file, delete_blob, file_is_valid, search_materials
from ..services.school_calendar import calendar_status

router = APIRouter(prefix="/admin", tags=["Administration"])


def _get(db: Session, model, obj_id: str, label: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise not_found(f"{label} nicht gefunden.")
    return obj


# ===========================================================================
# Benutzer
# ===========================================================================

@router.get("/users", summary="Benutzer auflisten")
def list_users(auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.display_name)).all()
    return {"items": [user_out(u) for u in users], "total": len(users), "page": 1, "page_size": max(len(users), 1)}


@router.post("/users", status_code=201, summary="Benutzer anlegen (temporäres Passwort)")
def create_user(body: UserCreate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise invalid("E-Mail bereits vergeben.", {"email": "Diese E-Mail-Adresse ist bereits registriert."})
    count = db.scalar(select(func.count()).select_from(User)) or 0
    if count >= 20:
        raise invalid("Pilotgrenze erreicht: höchstens 20 Benutzerkonten.")
    temp = generate_temp_password()
    user = User(email=body.email, display_name=body.display_name, role=body.role, password_hash=hash_password(temp), must_change_password=True)
    db.add(user)
    db.flush()
    audit(db, auth.user.id, "user_created", "user", user.id, {"role": body.role})
    db.commit()
    return {"user": user_out(user), "temporary_password": temp}


def _active_admins(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == ROLE_ADMIN, User.active.is_(True))) or 0


@router.patch("/users/{user_id}", summary="Benutzer ändern oder sperren")
def update_user(user_id: str, body: UserUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get(db, User, user_id, "Benutzer")
    check_version(user, body.version)
    removing_admin = user.role == ROLE_ADMIN and user.active and (body.active is False or body.role == "teacher")
    if removing_admin and _active_admins(db) <= 1:
        raise invalid("Der letzte aktive Administrator kann nicht gesperrt oder herabgestuft werden.")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.active is not None and body.active != user.active:
        user.active = body.active
        if not body.active:
            # Laufende Sitzungen sofort ungültig machen
            db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        audit(db, auth.user.id, "user_locked" if not body.active else "user_unlocked", "user", user.id)
    user.version += 1
    audit(db, auth.user.id, "user_updated", "user", user.id)
    db.commit()
    return user_out(user)


@router.post("/users/{user_id}/reset-password", summary="Passwort zurücksetzen (temporär, Wechselpflicht)")
def reset_password(user_id: str, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get(db, User, user_id, "Benutzer")
    temp = generate_temp_password()
    user.password_hash = hash_password(temp)
    user.must_change_password = True
    user.version += 1
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    audit(db, auth.user.id, "password_reset", "user", user.id)
    db.commit()
    return {"user": user_out(user), "temporary_password": temp}


# ===========================================================================
# Materialien
# ===========================================================================

@router.get("/materials", summary="Alle Materialien inkl. Entwürfe und Archiv")
def admin_list_materials(
    status: list[str] = Query(default=[]),
    subject: list[str] = Query(default=[]),
    topic: list[str] = Query(default=[]),
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=PAGE_SIZE_MAX),
    auth: Auth = Depends(require_admin),
    db: Session = Depends(get_db),
):
    statuses = tuple(status) or ("draft", "reviewed", "released", "archived")
    params = SearchParams(subject, topic, [], [], [], None, None, q, "title", page, page_size)
    items, total = search_materials(db, params, statuses)
    return {"items": [material_summary(m) for m in items], "total": total, "page": page, "page_size": page_size}


@router.get("/materials/{material_id}", summary="Materialdetails (Admin)")
def admin_get_material(material_id: str, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    data = material_detail(m)
    data["release_check"] = release_problems(m)
    return data


def _curriculum_for(db: Session, ids: list[str], subject_id: str) -> list[CurriculumReference]:
    refs = []
    for cid in dict.fromkeys(ids):
        c = db.get(CurriculumReference, cid)
        if c is None or c.subject_id != subject_id:
            raise invalid("Ungültiger Kompetenzbezug.", {"curriculum_ids": f"Bezug {cid} existiert nicht oder gehört zu einem anderen Fach."})
        refs.append(c)
    return refs


@router.post("/materials", status_code=201, summary="Material anlegen (Status Entwurf)")
def create_material(body: MaterialIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    topic = db.get(Topic, body.topic_id)
    if topic is None:
        raise invalid("Unbekanntes Thema.", {"topic_id": "Thema existiert nicht."})
    m = Material(
        topic_id=topic.id,
        title=body.title,
        description=body.description,
        learning_goal=body.learning_goal,
        keywords=body.keywords,
        type=body.type,
        level=body.level,
        duration_minutes=body.duration_minutes,
        author=body.author,
        license_text=body.license_text,
        status="draft",
        curriculum=_curriculum_for(db, body.curriculum_ids, topic.subject_id),
    )
    db.add(m)
    db.flush()
    audit(db, auth.user.id, "material_created", "material", m.id)
    db.commit()
    return material_detail(MaterialRepository(db).get(m.id))


@router.patch("/materials/{material_id}", summary="Material bearbeiten")
def update_material(material_id: str, body: MaterialUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, body.version)
    data = body.model_dump(exclude_unset=True, exclude={"version", "curriculum_ids"})
    if "topic_id" in data:
        topic = db.get(Topic, data["topic_id"])
        if topic is None:
            raise invalid("Unbekanntes Thema.", {"topic_id": "Thema existiert nicht."})
    for key, value in data.items():
        if value is not None:
            setattr(m, key, value)
    subject_id = db.get(Topic, m.topic_id).subject_id
    if body.curriculum_ids is not None:
        m.curriculum = _curriculum_for(db, body.curriculum_ids, subject_id)
    m.version += 1
    audit(db, auth.user.id, "material_updated", "material", m.id, {"fields": sorted(data)})
    db.commit()
    return material_detail(MaterialRepository(db).get(m.id))


@router.post("/materials/{material_id}/files", summary="PDF hochladen oder ersetzen (main/solution)")
async def upload_file(
    material_id: str,
    purpose: str = Form(...),
    version: int = Form(...),
    file: UploadFile = File(...),
    auth: Auth = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if purpose not in ("main", "solution"):
        raise invalid("Ungültiger Dateizweck.", {"purpose": "main oder solution"})
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, version)
    # Größe begrenzt einlesen
    data = await file.read(settings.max_upload_bytes + 1)
    f, old_key = attach_file(db, m, purpose, data, file.filename or "", file.content_type)
    try:
        db.flush()
        audit(db, auth.user.id, "material_file_replaced" if old_key else "material_file_added", "material", m.id, {"purpose": purpose, "sha256": f.sha256, "size": f.size_bytes})
        db.commit()
    except Exception:
        db.rollback()
        delete_blob(f.storage_key)
        raise
    if old_key:
        delete_blob(old_key)
    return material_detail(MaterialRepository(db).get(m.id))


@router.delete("/materials/{material_id}/files/{file_id}", summary="Datei entfernen")
def delete_file(material_id: str, file_id: str, version: int = Query(...), auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, version)
    f = next((f for f in m.files if f.id == file_id), None)
    if f is None:
        raise not_found("Datei nicht gefunden.")
    if f.purpose == "main" and m.status == "released":
        raise invalid("Die Hauptdatei eines freigegebenen Materials kann nicht entfernt werden. Bitte zuerst archivieren oder ersetzen.")
    key = f.storage_key
    m.files.remove(f)
    m.version += 1
    audit(db, auth.user.id, "material_file_removed", "material", m.id, {"purpose": f.purpose})
    db.commit()
    delete_blob(key)
    return material_detail(MaterialRepository(db).get(m.id))


def release_problems(m: Material) -> list[str]:
    problems = []
    if not any(c.verification_status == "verified" for c in m.curriculum):
        problems.append("Mindestens eine überprüfte Kompetenzreferenz fehlt.")
    main = next((f for f in m.files if f.purpose == "main"), None)
    if main is None or not file_is_valid(main):
        problems.append("Gültige Hauptdatei (PDF) fehlt.")
    if not m.license_text.strip():
        problems.append("Dokumentierte Nutzungserlaubnis (Lizenz) fehlt.")
    if not m.author.strip():
        problems.append("Autor fehlt.")
    if not m.reviewer_id or not m.reviewed_at:
        problems.append("Fachliche Prüfung mit Prüfer und Datum fehlt.")
    return problems


@router.post("/materials/{material_id}/review", summary="Fachliche Prüfung erfassen (→ geprüft)")
def review_material(material_id: str, body: MaterialReviewIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, body.version)
    if m.status not in ("draft", "reviewed"):
        raise invalid("Nur Entwürfe können geprüft werden.")
    reviewer = db.get(User, body.reviewer_id)
    if reviewer is None:
        raise invalid("Unbekannter Prüfer.", {"reviewer_id": "Benutzer existiert nicht."})
    if body.reviewed_at > date.today():
        raise invalid("Prüfdatum liegt in der Zukunft.", {"reviewed_at": "Datum prüfen."})
    m.reviewer_id = reviewer.id
    m.reviewed_at = body.reviewed_at
    m.review_note = body.review_note
    m.status = "reviewed"
    m.is_demo = False
    m.version += 1
    audit(db, auth.user.id, "material_reviewed", "material", m.id, {"reviewer_id": reviewer.id})
    db.commit()
    return material_detail(MaterialRepository(db).get(m.id))


@router.post("/materials/{material_id}/release", summary="Freigeben (nur nach vollständiger Prüfung)")
def release_material(material_id: str, body: VersionIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, body.version)
    if m.status != "reviewed":
        raise invalid("Freigabe nur aus dem Status 'geprüft' möglich.")
    problems = release_problems(m)
    if problems:
        raise ApiError(422, "release_blocked", "Freigabe nicht möglich.", {"release": " ".join(problems)}, extra={"problems": problems})
    m.status = "released"
    m.version += 1
    audit(db, auth.user.id, "material_released", "material", m.id)
    db.commit()
    return material_detail(MaterialRepository(db).get(m.id))


@router.post("/materials/{material_id}/archive", summary="Archivieren")
def archive_material(material_id: str, body: VersionIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, body.version)
    m.status = "archived"
    m.version += 1
    audit(db, auth.user.id, "material_archived", "material", m.id)
    db.commit()
    return material_detail(MaterialRepository(db).get(m.id))


@router.post("/materials/{material_id}/reopen", summary="Archiviertes oder geprüftes Material zurück in Entwurf")
def reopen_material(material_id: str, body: VersionIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    check_version(m, body.version)
    m.status = "draft"
    m.version += 1
    audit(db, auth.user.id, "material_reopened", "material", m.id)
    db.commit()
    return material_detail(MaterialRepository(db).get(m.id))


@router.delete("/materials/{material_id}", status_code=204, summary="Unreferenzierten Entwurf löschen")
def delete_material(material_id: str, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    m = MaterialRepository(db).get(material_id)
    if m is None:
        raise not_found("Material nicht gefunden.")
    if m.status != "draft":
        raise invalid("Nur Entwürfe können gelöscht werden. Bitte stattdessen archivieren.")
    referenced = db.scalar(select(func.count()).select_from(plan_unit_materials).where(plan_unit_materials.c.material_id == m.id)) or 0
    referenced += db.scalar(select(func.count()).select_from(template_unit_materials).where(template_unit_materials.c.material_id == m.id)) or 0
    if referenced:
        raise invalid("Das Material wird in Plänen oder Vorlagen verwendet. Bitte archivieren.")
    keys = [f.storage_key for f in m.files]
    db.delete(m)
    audit(db, auth.user.id, "material_deleted", "material", material_id)
    db.commit()
    for k in keys:
        delete_blob(k)


@router.get("/pilot-status", summary="Stand der Inhaltsfreigabe für den Unterrichtspiloten")
def pilot_status(auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(select(Material.status, Material.is_demo, func.count()).group_by(Material.status, Material.is_demo)).all()
    counts: dict[str, int] = {}
    demo = 0
    reviewed_released = 0
    for status, is_demo, n in rows:
        counts[status] = counts.get(status, 0) + n
        if is_demo:
            demo += n
        elif status == "released":
            reviewed_released += n
    years = db.scalars(select(SchoolYear)).all()
    return {
        "material_counts": counts,
        "demo_materials": demo,
        "professionally_released": reviewed_released,
        "required_for_classroom_pilot": 30,
        "classroom_pilot_ready": reviewed_released >= 30,
        "calendars": [{"school_year": y.label, **calendar_status(db, y.id)} for y in years],
    }


# ===========================================================================
# Themen und Lehrplanbezüge
# ===========================================================================

@router.get("/topics", summary="Themen (inkl. archivierter)")
def admin_topics(auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    items = [topic_out(t) for t in ReferenceRepository(db).topics(include_archived=True)]
    return {"items": items, "total": len(items), "page": 1, "page_size": max(len(items), 1)}


def _prereqs(db: Session, ids: list[str], self_id: str | None) -> list[Topic]:
    result = []
    for tid in dict.fromkeys(ids):
        if tid == self_id:
            raise invalid("Ein Thema kann nicht Voraussetzung für sich selbst sein.", {"prerequisite_ids": "Zirkelbezug."})
        t = db.get(Topic, tid)
        if t is None:
            raise invalid("Unbekannte Voraussetzung.", {"prerequisite_ids": f"Thema {tid} existiert nicht."})
        result.append(t)
    return result


@router.post("/topics", status_code=201, summary="Thema anlegen")
def create_topic(body: TopicIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(Subject, body.subject_id) is None:
        raise invalid("Unbekanntes Fach.", {"subject_id": "Fach existiert nicht."})
    t = Topic(**body.model_dump(exclude={"prerequisite_ids"}))
    t.prerequisites = _prereqs(db, body.prerequisite_ids, None)
    db.add(t)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise invalid("Thema existiert bereits in diesem Fach.", {"title": "Doppelter Titel."})
    audit(db, auth.user.id, "topic_created", "topic", t.id)
    db.commit()
    return topic_out(t)


@router.patch("/topics/{topic_id}", summary="Thema ändern oder archivieren")
def update_topic(topic_id: str, body: TopicUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    t = _get(db, Topic, topic_id, "Thema")
    check_version(t, body.version)
    for key, value in body.model_dump(exclude_unset=True, exclude={"version", "prerequisite_ids"}).items():
        if value is not None:
            setattr(t, key, value)
    if body.prerequisite_ids is not None:
        t.prerequisites = _prereqs(db, body.prerequisite_ids, t.id)
    t.version += 1
    audit(db, auth.user.id, "topic_updated", "topic", t.id)
    db.commit()
    return topic_out(t)


@router.get("/curriculum", summary="Lehrplanbezüge (inkl. archivierter)")
def admin_curriculum(auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    items = [curriculum_out(c) for c in ReferenceRepository(db).curriculum(include_archived=True)]
    return {"items": items, "total": len(items), "page": 1, "page_size": max(len(items), 1)}


@router.post("/curriculum", status_code=201, summary="Lehrplanbezug anlegen")
def create_curriculum(body: CurriculumIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(Subject, body.subject_id) is None:
        raise invalid("Unbekanntes Fach.", {"subject_id": "Fach existiert nicht."})
    c = CurriculumReference(**body.model_dump(), verification_status="unverified")
    db.add(c)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise invalid("Abschnitt existiert bereits.", {"section_code": "Doppelter Abschnittscode."})
    audit(db, auth.user.id, "curriculum_created", "curriculum", c.id)
    db.commit()
    return curriculum_out(c)


@router.patch("/curriculum/{ref_id}", summary="Lehrplanbezug ändern, prüfen oder archivieren")
def update_curriculum(ref_id: str, body: CurriculumUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    c = _get(db, CurriculumReference, ref_id, "Lehrplanbezug")
    check_version(c, body.version)
    data = body.model_dump(exclude_unset=True, exclude={"version"})
    for key, value in data.items():
        if key == "verification_status":
            continue
        if value is not None:
            setattr(c, key, value)
    if body.verification_status is not None and body.verification_status != c.verification_status:
        c.verification_status = body.verification_status
        if body.verification_status == "verified":
            c.reviewer_id = auth.user.id
            c.reviewed_at = date.today()
        else:
            c.reviewer_id = None
            c.reviewed_at = None
    c.version += 1
    audit(db, auth.user.id, "curriculum_updated", "curriculum", c.id, {"fields": sorted(data)})
    db.commit()
    return curriculum_out(c)


# ===========================================================================
# Kalender
# ===========================================================================

@router.get("/calendar", summary="Schuljahre und Schließtage")
def admin_calendar(auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    repo = ReferenceRepository(db)
    return {
        "school_years": [
            {**school_year_out(y), "closures": [closure_out(c) for c in repo.closures(y.id)], "status": calendar_status(db, y.id)}
            for y in repo.school_years()
        ]
    }


@router.post("/calendar/school-years", status_code=201, summary="Schuljahr anlegen")
def create_school_year(body: SchoolYearIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(SchoolYear).where(SchoolYear.label == body.label)):
        raise invalid("Schuljahr existiert bereits.", {"label": "Doppelte Bezeichnung."})
    y = SchoolYear(**body.model_dump())
    db.add(y)
    db.flush()
    audit(db, auth.user.id, "school_year_created", "school_year", y.id)
    db.commit()
    return school_year_out(y)


@router.patch("/calendar/school-years/{year_id}", summary="Schuljahr ändern")
def update_school_year(year_id: str, body: SchoolYearUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    y = _get(db, SchoolYear, year_id, "Schuljahr")
    check_version(y, body.version)
    for key, value in body.model_dump(exclude_unset=True, exclude={"version"}).items():
        if value is not None:
            setattr(y, key, value)
    if y.ends_on < y.starts_on:
        raise invalid("Ende muss am oder nach dem Beginn liegen.", {"ends_on": "Datum prüfen."})
    y.version += 1
    audit(db, auth.user.id, "school_year_updated", "school_year", y.id)
    db.commit()
    return school_year_out(y)


@router.post("/calendar/closures", status_code=201, summary="Ferien/Feiertag/Sondertag anlegen")
def create_closure(body: ClosureIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    _get(db, SchoolYear, body.school_year_id, "Schuljahr")
    c = CalendarClosure(**body.model_dump())
    db.add(c)
    db.flush()
    audit(db, auth.user.id, "closure_created", "calendar_closure", c.id)
    db.commit()
    return closure_out(c)


@router.patch("/calendar/closures/{closure_id}", summary="Eintrag ändern oder freigeben")
def update_closure(closure_id: str, body: ClosureUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    c = _get(db, CalendarClosure, closure_id, "Kalendereintrag")
    check_version(c, body.version)
    for key, value in body.model_dump(exclude_unset=True, exclude={"version"}).items():
        if value is not None:
            setattr(c, key, value)
    if body.review_status == "approved" and c.reviewed_at is None:
        c.reviewed_at = date.today()
    if c.ends_on < c.starts_on:
        raise invalid("Ende muss am oder nach dem Beginn liegen.", {"ends_on": "Datum prüfen."})
    try:
        ClosureIn(school_year_id=c.school_year_id, title=c.title, starts_on=c.starts_on, ends_on=c.ends_on, kind=c.kind, source=c.source, reviewed_at=c.reviewed_at, review_status=c.review_status)
    except ValidationError as exc:
        raise invalid("Ungültiger Kalendereintrag.", {"_": str(exc.errors()[0]["msg"])})
    c.version += 1
    audit(db, auth.user.id, "closure_updated", "calendar_closure", c.id)
    db.commit()
    return closure_out(c)


@router.delete("/calendar/closures/{closure_id}", status_code=204, summary="Eintrag löschen")
def delete_closure(closure_id: str, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    c = _get(db, CalendarClosure, closure_id, "Kalendereintrag")
    db.delete(c)
    audit(db, auth.user.id, "closure_deleted", "calendar_closure", closure_id)
    db.commit()


@router.post("/calendar/import", summary="Kalender-JSON importieren (dry_run = Vorschau mit Fehlerliste)")
def import_calendar(payload: dict, dry_run: bool = True, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    from ..services.importer import import_calendar as do_import

    result = do_import(db, payload, dry_run=dry_run, actor_id=auth.user.id)
    if not dry_run and not result["errors"]:
        db.commit()
    else:
        db.rollback()
    return result


@router.post("/import/content", summary="Inhalts-JSON importieren (Themen, Lehrplanbezüge, Materialien als Entwurf)")
def import_content(payload: dict, dry_run: bool = True, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    from ..services.importer import import_content as do_import

    result = do_import(db, payload, dry_run=dry_run, actor_id=auth.user.id)
    if not dry_run and not result["errors"]:
        db.commit()
    else:
        db.rollback()
    return result


# ===========================================================================
# Vorlagen
# ===========================================================================

def _template_query():
    return select(PlanTemplate).options(selectinload(PlanTemplate.units).selectinload(TemplateUnit.topic))


@router.get("/templates", summary="Planvorlagen")
def admin_templates(auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    items = [template_out(t) for t in db.scalars(_template_query().order_by(PlanTemplate.name)).all()]
    return {"items": items, "total": len(items), "page": 1, "page_size": max(len(items), 1)}


def _template_units(db: Session, subject_id: str, units) -> list[TemplateUnit]:
    result = []
    for i, u in enumerate(units, start=1):
        topic = db.get(Topic, u.topic_id)
        if topic is None or topic.subject_id != subject_id:
            raise invalid("Thema passt nicht zum Vorlagenfach.", {f"units.{i - 1}.topic_id": "Ungültiges Thema."})
        mats = []
        for mid in dict.fromkeys(u.material_ids):
            m = db.get(Material, mid)
            if m is None or m.topic_id != topic.id:
                raise invalid("Material passt nicht zum Thema.", {f"units.{i - 1}.material_ids": f"Material {mid} ungültig."})
            mats.append(m)
        result.append(
            TemplateUnit(topic_id=topic.id, sequence=i, estimated_lessons=u.estimated_lessons, materials=mats, curriculum=_curriculum_for(db, u.curriculum_ids, subject_id))
        )
    return result


@router.post("/templates", status_code=201, summary="Vorlage anlegen")
def create_template(body: TemplateIn, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(Subject, body.subject_id) is None:
        raise invalid("Unbekanntes Fach.", {"subject_id": "Fach existiert nicht."})
    if db.scalar(select(PlanTemplate).where(PlanTemplate.name == body.name)):
        raise invalid("Name bereits vergeben.", {"name": "Doppelter Name."})
    t = PlanTemplate(name=body.name, subject_id=body.subject_id, units=_template_units(db, body.subject_id, body.units))
    db.add(t)
    db.flush()
    audit(db, auth.user.id, "template_created", "template", t.id)
    db.commit()
    return template_out(db.scalar(_template_query().where(PlanTemplate.id == t.id)))


@router.patch("/templates/{template_id}", summary="Vorlage ändern (bestehende Pläne bleiben unverändert)")
def update_template(template_id: str, body: TemplateUpdate, auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.scalar(_template_query().where(PlanTemplate.id == template_id))
    if t is None:
        raise not_found("Vorlage nicht gefunden.")
    check_version(t, body.version)
    if body.name is not None:
        t.name = body.name
    if body.archived is not None:
        t.archived = body.archived
    if body.units is not None:
        new_units = _template_units(db, t.subject_id, body.units)
        t.units.clear()
        db.flush()
        t.units.extend(new_units)
    t.version += 1
    audit(db, auth.user.id, "template_updated", "template", t.id)
    db.commit()
    return template_out(db.scalar(_template_query().where(PlanTemplate.id == t.id)))


# ===========================================================================
# Audit
# ===========================================================================

@router.get("/audit", summary="Audit-Protokoll")
def audit_log(page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=PAGE_SIZE_MAX), auth: Auth = Depends(require_admin), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(AuditEvent)) or 0
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    names = {u.id: u.display_name for u in db.scalars(select(User)).all()}
    items = [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "actor_name": names.get(r.actor_id) if r.actor_id else None,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "timestamp": r.timestamp.isoformat(),
            "details": r.details,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
