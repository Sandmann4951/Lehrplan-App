"""F02/F05/F06/F07: Klassen, Wochen, persönliche Pläne und Empfehlungen.

Alle Objekte sind strikt auf den Eigentümer beschränkt – auch für Administratoren.
Fremde Objekte liefern 404.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Auth, get_auth
from ..errors import check_version, invalid, not_found
from ..models import ClassSubjectHours, CurriculumReference, Material, PlanUnit, SchoolClass, SchoolYear, Subject, Topic
from ..repositories.core import ClassRepository, FavoriteRepository, UnitRepository
from ..schemas import ClassCreate, ClassUpdate, InitializePlanIn, SubjectHoursIn, UnitCheckIn, UnitCreate, UnitUpdate
from ..serializers import class_out, unit_out, week_out
from ..services.calendar import week_start
from ..services.planning import initialize_plan, week_warnings
from ..services.recommendations import recommend
from ..services.school_calendar import calendar_for_class, calendar_status, today_local

router = APIRouter(tags=["Klassen und Planung"])


def _owned_class(db: Session, class_id: str, auth: Auth) -> SchoolClass:
    cls = ClassRepository(db).get_owned(class_id, auth.user.id)
    if cls is None:
        raise not_found("Klasse nicht gefunden.")
    return cls


def _owned_unit(db: Session, unit_id: str, auth: Auth) -> PlanUnit:
    unit = UnitRepository(db).get_owned(unit_id, auth.user.id)
    if unit is None:
        raise not_found("Einheit nicht gefunden.")
    return unit


def _apply_hours(db: Session, cls: SchoolClass, hours: list[SubjectHoursIn]) -> None:
    subject_ids = set(db.scalars(select(Subject.id)).all())
    seen = set()
    for h in hours:
        if h.subject_id not in subject_ids:
            raise invalid("Unbekanntes Fach.", {"subject_hours": f"Fach {h.subject_id} existiert nicht."})
        if h.subject_id in seen:
            raise invalid("Fach doppelt angegeben.", {"subject_hours": "Jedes Fach nur einmal."})
        seen.add(h.subject_id)
    cls.subject_hours.clear()
    db.flush()
    for h in hours:
        cls.subject_hours.append(ClassSubjectHours(subject_id=h.subject_id, weekly_hours=h.weekly_hours))


def _default_hours(db: Session) -> list[SubjectHoursIn]:
    defaults = {"D": 7, "M": 5}
    return [SubjectHoursIn(subject_id=s.id, weekly_hours=defaults.get(s.code, 2)) for s in db.scalars(select(Subject)).all()]


# -- Klassen -------------------------------------------------------------------

@router.get("/classes", summary="Eigene Klassen")
def list_classes(auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    items = [class_out(c) for c in ClassRepository(db).list_for_owner(auth.user.id)]
    return {"items": items, "total": len(items), "page": 1, "page_size": max(len(items), 1)}


@router.post("/classes", status_code=201, summary="Klasse anlegen")
def create_class(body: ClassCreate, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    if db.get(SchoolYear, body.school_year_id) is None:
        raise invalid("Unbekanntes Schuljahr.", {"school_year_id": "Schuljahr existiert nicht."})
    cls = SchoolClass(
        owner_id=auth.user.id,
        name=body.name,
        grade=body.grade,
        state=body.state,
        school_type=body.school_type,
        school_year_id=body.school_year_id,
        weekdays=body.weekdays,
    )
    db.add(cls)
    db.flush()
    _apply_hours(db, cls, body.subject_hours or _default_hours(db))
    db.commit()
    db.refresh(cls)
    return class_out(cls)


@router.get("/classes/{class_id}", summary="Klasse lesen")
def get_class(class_id: str, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    return class_out(_owned_class(db, class_id, auth))


@router.patch("/classes/{class_id}", summary="Klasse ändern")
def update_class(class_id: str, body: ClassUpdate, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    cls = _owned_class(db, class_id, auth)
    check_version(cls, body.version)
    if body.name is not None:
        cls.name = body.name
    if body.school_year_id is not None:
        if db.get(SchoolYear, body.school_year_id) is None:
            raise invalid("Unbekanntes Schuljahr.", {"school_year_id": "Schuljahr existiert nicht."})
        cls.school_year_id = body.school_year_id
    if body.weekdays is not None:
        cls.weekdays = body.weekdays
    if body.subject_hours is not None:
        _apply_hours(db, cls, body.subject_hours)
    cls.version += 1
    db.commit()
    db.refresh(cls)
    return class_out(cls)


@router.delete("/classes/{class_id}", status_code=204, summary="Klasse samt Einheiten löschen")
def delete_class(class_id: str, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    cls = _owned_class(db, class_id, auth)
    db.delete(cls)
    db.commit()


# -- Wochen / Kalender -------------------------------------------------------

@router.get("/classes/{class_id}/weeks", summary="Wochenangaben (ISO-KW, Unterrichtswoche) eines Zeitraums")
def class_weeks(
    class_id: str,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    auth: Auth = Depends(get_auth),
    db: Session = Depends(get_db),
):
    cls = _owned_class(db, class_id, auth)
    cal = calendar_for_class(db, cls)
    start = week_start(from_) if from_ else cal.first_week()
    end = week_start(to) if to else cal.last_week()
    if end < start:
        raise invalid("'to' liegt vor 'from'.", {"to": "Muss nach 'from' liegen."})
    if (end - start).days > 7 * 60:
        raise invalid("Zeitraum zu groß (max. 60 Wochen).")
    weeks = []
    hours = {h.subject_id: h.weekly_hours for h in cls.subject_hours}
    w = start
    while w <= end:
        info = cal.week_info(w)
        data = week_out(info)
        data["capacity"] = {sid: info.capacity(h) for sid, h in hours.items()}
        weeks.append(data)
        w += timedelta(days=7)
    return {"items": weeks, "calendar_status": calendar_status(db, cls.school_year_id)}


# -- Einheiten -----------------------------------------------------------------

def _validate_refs(db: Session, cls: SchoolClass, subject_id: str, topic_id: str, material_ids: list[str] | None, curriculum_ids: list[str] | None, auth: Auth, keep_material_ids: set[str] = frozenset()):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise invalid("Unbekanntes Thema.", {"topic_id": "Thema existiert nicht."})
    if topic.subject_id != subject_id:
        raise invalid("Planfach und Themenfach stimmen nicht überein.", {"topic_id": "Thema gehört zu einem anderen Fach."})
    materials: list[Material] | None = None
    if material_ids is not None:
        materials = []
        for mid in dict.fromkeys(material_ids):
            m = db.get(Material, mid)
            # Neue Verknüpfungen nur mit freigegebenen Materialien; bestehende (z. B. archivierte) bleiben erhalten.
            if m is None or (m.status != "released" and mid not in keep_material_ids):
                raise invalid("Material nicht verfügbar.", {"material_ids": f"Material {mid} ist nicht zugänglich."})
            materials.append(m)
    refs: list[CurriculumReference] | None = None
    if curriculum_ids is not None:
        refs = []
        for cid in dict.fromkeys(curriculum_ids):
            c = db.get(CurriculumReference, cid)
            if c is None or c.subject_id != subject_id:
                raise invalid("Ungültiger Kompetenzbezug.", {"curriculum_ids": f"Bezug {cid} passt nicht zum Fach."})
            refs.append(c)
    return topic, materials, refs


@router.get("/classes/{class_id}/units", summary="Einheiten eines Zeitraums")
def list_units(
    class_id: str,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    auth: Auth = Depends(get_auth),
    db: Session = Depends(get_db),
):
    cls = _owned_class(db, class_id, auth)
    items = [unit_out(u) for u in UnitRepository(db).list_for_class(cls.id, week_start(from_) if from_ else None, to)]
    return {"items": items, "total": len(items), "page": 1, "page_size": max(len(items), 1)}


@router.post("/classes/{class_id}/units/check", summary="Warnungen vor dem Speichern prüfen (Überplanung, freie Woche)")
def check_unit(class_id: str, body: UnitCheckIn, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    cls = _owned_class(db, class_id, auth)
    if body.unit_id:
        _owned_unit(db, body.unit_id, auth)
    return {"warnings": week_warnings(db, cls, body.subject_id, week_start(body.week_start_date), body.planned_lessons, body.unit_id)}


@router.post("/classes/{class_id}/units", status_code=201, summary="Einheit hinzufügen")
def create_unit(class_id: str, body: UnitCreate, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    cls = _owned_class(db, class_id, auth)
    if db.get(Subject, body.subject_id) is None:
        raise invalid("Unbekanntes Fach.", {"subject_id": "Fach existiert nicht."})
    _, materials, refs = _validate_refs(db, cls, body.subject_id, body.topic_id, body.material_ids, body.curriculum_ids, auth)
    week = week_start(body.week_start_date)
    warnings = week_warnings(db, cls, body.subject_id, week, body.planned_lessons)
    max_seq = max((u.sequence for u in cls.units if u.subject_id == body.subject_id), default=0)
    unit = PlanUnit(
        class_id=cls.id,
        subject_id=body.subject_id,
        topic_id=body.topic_id,
        week_start_date=week,
        planned_lessons=body.planned_lessons,
        status=body.status,
        notes=body.notes,
        sequence=max_seq + 1,
        materials=materials or [],
        curriculum=refs or [],
    )
    db.add(unit)
    db.commit()
    unit = UnitRepository(db).get_owned(unit.id, auth.user.id)
    return {"unit": unit_out(unit), "warnings": warnings}


@router.patch("/units/{unit_id}", summary="Einheit bearbeiten, verschieben oder Status ändern")
def update_unit(unit_id: str, body: UnitUpdate, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    unit = _owned_unit(db, unit_id, auth)
    check_version(unit, body.version)
    cls = unit.school_class
    keep = {m.id for m in unit.materials}
    if body.topic_id is not None or body.material_ids is not None or body.curriculum_ids is not None:
        topic, materials, refs = _validate_refs(
            db, cls, unit.subject_id, body.topic_id or unit.topic_id, body.material_ids, body.curriculum_ids, auth, keep_material_ids=keep
        )
        if body.topic_id is not None:
            unit.topic_id = topic.id
        if materials is not None:
            unit.materials = materials
        if refs is not None:
            unit.curriculum = refs
    warnings: list[dict] = []
    if body.week_start_date is not None:
        unit.week_start_date = week_start(body.week_start_date)
    if body.planned_lessons is not None:
        unit.planned_lessons = body.planned_lessons
    if body.week_start_date is not None or body.planned_lessons is not None:
        warnings = week_warnings(db, cls, unit.subject_id, unit.week_start_date, unit.planned_lessons, unit.id)
    if body.status is not None:
        unit.status = body.status
    if body.notes is not None:
        unit.notes = body.notes
    unit.version += 1
    db.commit()
    unit = UnitRepository(db).get_owned(unit.id, auth.user.id)
    return {"unit": unit_out(unit), "warnings": warnings}


@router.delete("/units/{unit_id}", status_code=204, summary="Einheit löschen")
def delete_unit(unit_id: str, version: int | None = None, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    unit = _owned_unit(db, unit_id, auth)
    if version is not None:
        check_version(unit, version)
    db.delete(unit)
    db.commit()


@router.post("/classes/{class_id}/initialize-plan", summary="Plan aus Vorlage anlegen (nur nach Bestätigung)")
def init_plan(class_id: str, body: InitializePlanIn, auth: Auth = Depends(get_auth), db: Session = Depends(get_db)):
    cls = _owned_class(db, class_id, auth)
    if not body.confirm:
        raise invalid("Die Vorlagenkopie muss ausdrücklich bestätigt werden.", {"confirm": "Bitte bestätigen."})
    result = initialize_plan(db, cls, body.template_ids, body.start_week, body.replace_existing)
    db.commit()
    return result


# -- Dashboard und Empfehlungen ---------------------------------------------------

@router.get("/classes/{class_id}/recommendations", summary="Nachvollziehbare Materialvorschläge für eine Woche")
def recommendations(
    class_id: str,
    week_start_: date = Query(alias="week_start"),
    level: str | None = None,
    auth: Auth = Depends(get_auth),
    db: Session = Depends(get_db),
):
    cls = _owned_class(db, class_id, auth)
    from ..models import MATERIAL_LEVELS

    if level is not None and level not in MATERIAL_LEVELS:
        raise invalid("Unbekanntes Niveau.", {"level": f"Erlaubt: {', '.join(MATERIAL_LEVELS)}"})
    return recommend(db, cls, week_start_, level, FavoriteRepository(db).ids_for_user(auth.user.id))


@router.get("/classes/{class_id}/dashboard", summary="Dashboard: Woche, Einheiten und Vorschläge")
def dashboard(
    class_id: str,
    week: date | None = None,
    level: str | None = None,
    auth: Auth = Depends(get_auth),
    db: Session = Depends(get_db),
):
    cls = _owned_class(db, class_id, auth)
    monday = week_start(week or today_local())
    cal = calendar_for_class(db, cls)
    info = cal.week_info(monday)
    hours = {h.subject_id: h.weekly_hours for h in cls.subject_hours}
    week_data = week_out(info)
    week_data["capacity"] = {sid: info.capacity(h) for sid, h in hours.items()}
    units = UnitRepository(db).list_for_class(cls.id, monday, monday)
    return {
        "class": class_out(cls),
        "week": week_data,
        "units": [unit_out(u) for u in units],
        "recommendations": recommend(db, cls, monday, level, FavoriteRepository(db).ids_for_user(auth.user.id)),
        "calendar_status": calendar_status(db, cls.school_year_id),
    }
