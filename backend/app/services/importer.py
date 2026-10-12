"""Validierte JSON-Importe mit Vorschau und Fehlerliste.

Kalender-Format::

    {
      "school_year": {"label": "2026/2027", "starts_on": "2026-09-15", "ends_on": "2027-07-30"},
      "source": "https://www.km.bayern.de/...",
      "reviewed_at": "2026-10-12",            # optional
      "review_status": "unreviewed",          # oder "approved"
      "replace": true,                        # vorhandene Einträge des Schuljahrs ersetzen
      "closures": [{"title": "Herbstferien", "starts_on": "...", "ends_on": "...", "kind": "holiday"}]
    }

Inhalts-Format (kompatibel zum Export der Claude-Artifacts-Demo)::

    {"schema_version": 1, "topics": [...], "curriculum": [...], "materials": [...]}

Materialien werden immer als Entwurf importiert. Dateien werden separat hochgeladen.
"""
from __future__ import annotations


from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..audit import audit
from ..models import CalendarClosure, CurriculumReference, Material, SchoolYear, Subject, Topic
from ..schemas import ClosureIn, CurriculumIn, MaterialIn, SchoolYearIn, TopicIn


def _err(errors: list[dict], path: str, message: str) -> None:
    errors.append({"path": path, "message": message})


def _pyd_errors(errors: list[dict], prefix: str, exc: ValidationError) -> None:
    for e in exc.errors():
        loc = ".".join(str(p) for p in e.get("loc", ()))
        _err(errors, f"{prefix}.{loc}" if loc else prefix, e.get("msg", "Ungültiger Wert"))


def import_calendar(db: Session, payload: dict, dry_run: bool, actor_id: str | None) -> dict:
    errors: list[dict] = []
    preview: list[dict] = []
    if not isinstance(payload, dict):
        return {"errors": [{"path": "", "message": "JSON-Objekt erwartet."}], "preview": [], "applied": False}
    sy_raw = payload.get("school_year")
    try:
        sy = SchoolYearIn.model_validate(sy_raw)
    except ValidationError as exc:
        _pyd_errors(errors, "school_year", exc)
        return {"errors": errors, "preview": [], "applied": False}
    source = str(payload.get("source", ""))[:1000]
    default_status = payload.get("review_status", "unreviewed")
    default_reviewed = payload.get("reviewed_at")
    closures_raw = payload.get("closures")
    if not isinstance(closures_raw, list):
        _err(errors, "closures", "Liste erwartet.")
        closures_raw = []
    year = db.scalar(select(SchoolYear).where(SchoolYear.label == sy.label))
    parsed: list[ClosureIn] = []
    for i, raw in enumerate(closures_raw):
        if not isinstance(raw, dict):
            _err(errors, f"closures.{i}", "Objekt erwartet.")
            continue
        data = {
            "school_year_id": year.id if year else "neu",
            "source": source,
            "review_status": default_status,
            "reviewed_at": default_reviewed,
            **raw,
        }
        try:
            c = ClosureIn.model_validate(data)
        except ValidationError as exc:
            _pyd_errors(errors, f"closures.{i}", exc)
            continue
        if c.ends_on < sy.starts_on or c.starts_on > sy.ends_on:
            _err(errors, f"closures.{i}", f"„{c.title}“ liegt außerhalb des Schuljahrs.")
            continue
        parsed.append(c)
        preview.append({"title": c.title, "starts_on": c.starts_on.isoformat(), "ends_on": c.ends_on.isoformat(), "kind": c.kind, "review_status": c.review_status})
    summary = {
        "school_year": {"label": sy.label, "starts_on": sy.starts_on.isoformat(), "ends_on": sy.ends_on.isoformat(), "exists": year is not None},
        "closures": len(parsed),
        "replace": bool(payload.get("replace", False)),
    }
    if errors or dry_run:
        return {"errors": errors, "preview": preview, "summary": summary, "applied": False}

    if year is None:
        year = SchoolYear(label=sy.label, starts_on=sy.starts_on, ends_on=sy.ends_on)
        db.add(year)
        db.flush()
    else:
        if (year.starts_on, year.ends_on) != (sy.starts_on, sy.ends_on):
            year.starts_on, year.ends_on = sy.starts_on, sy.ends_on
            year.version += 1
    if payload.get("replace"):
        db.execute(delete(CalendarClosure).where(CalendarClosure.school_year_id == year.id))
    for c in parsed:
        db.add(CalendarClosure(**{**c.model_dump(), "school_year_id": year.id}))
    audit(db, actor_id, "calendar_imported", "school_year", year.id, {"closures": len(parsed), "replace": bool(payload.get("replace"))})
    return {"errors": [], "preview": preview, "summary": summary, "applied": True}


def import_content(db: Session, payload: dict, dry_run: bool, actor_id: str | None) -> dict:
    errors: list[dict] = []
    if not isinstance(payload, dict):
        return {"errors": [{"path": "", "message": "JSON-Objekt erwartet."}], "applied": False}
    if payload.get("schema_version") not in (1, "1"):
        _err(errors, "schema_version", "schema_version 1 erwartet.")
    for key in ("topics", "curriculum", "materials"):
        if key in payload and not isinstance(payload[key], list):
            _err(errors, key, "Liste erwartet.")
    if errors:
        return {"errors": errors, "applied": False}

    subjects = {s.code: s for s in db.scalars(select(Subject)).all()}
    subjects_by_id = {s.id: s for s in subjects.values()}

    def subject_for(raw: dict, path: str) -> Subject | None:
        s = subjects.get(str(raw.get("subject_code", ""))) or subjects_by_id.get(str(raw.get("subject_id", "")))
        if s is None:
            _err(errors, path, "Unbekanntes Fach (subject_code D oder M bzw. gültige subject_id).")
        return s

    stats = {"topics_new": 0, "topics_updated": 0, "curriculum_new": 0, "curriculum_updated": 0, "materials_new": 0, "materials_updated": 0}
    topic_ids: dict[str, str] = {}  # Import-ID -> DB-ID

    for i, raw in enumerate(payload.get("topics", [])):
        path = f"topics.{i}"
        if not isinstance(raw, dict):
            _err(errors, path, "Objekt erwartet.")
            continue
        s = subject_for(raw, path)
        if s is None:
            continue
        try:
            t_in = TopicIn.model_validate({k: v for k, v in raw.items() if k in TopicIn.model_fields and k not in ("subject_id", "prerequisite_ids")} | {"subject_id": s.id})
        except ValidationError as exc:
            _pyd_errors(errors, path, exc)
            continue
        existing = (db.get(Topic, raw["id"]) if raw.get("id") else None) or db.scalar(select(Topic).where(Topic.subject_id == s.id, Topic.title == t_in.title))
        if existing:
            for k, v in t_in.model_dump(exclude={"prerequisite_ids"}).items():
                setattr(existing, k, v)
            existing.version += 1
            topic = existing
            stats["topics_updated"] += 1
        else:
            topic = Topic(**t_in.model_dump(exclude={"prerequisite_ids"}))
            if raw.get("id"):
                topic.id = str(raw["id"])
            db.add(topic)
            stats["topics_new"] += 1
        db.flush()
        if raw.get("id"):
            topic_ids[str(raw["id"])] = topic.id

    curriculum_ids: dict[str, str] = {}
    for i, raw in enumerate(payload.get("curriculum", [])):
        path = f"curriculum.{i}"
        if not isinstance(raw, dict):
            _err(errors, path, "Objekt erwartet.")
            continue
        s = subject_for(raw, path)
        if s is None:
            continue
        try:
            c_in = CurriculumIn.model_validate({k: v for k, v in raw.items() if k in CurriculumIn.model_fields and k != "subject_id"} | {"subject_id": s.id})
        except ValidationError as exc:
            _pyd_errors(errors, path, exc)
            continue
        existing = db.scalar(
            select(CurriculumReference).where(
                CurriculumReference.subject_id == s.id,
                CurriculumReference.official_grade_band == c_in.official_grade_band,
                CurriculumReference.section_code == c_in.section_code,
            )
        )
        if existing:
            for k, v in c_in.model_dump().items():
                setattr(existing, k, v)
            existing.verification_status = "unverified"  # geänderte Bezüge neu prüfen
            existing.version += 1
            ref = existing
            stats["curriculum_updated"] += 1
        else:
            ref = CurriculumReference(**c_in.model_dump(), verification_status="unverified")
            if raw.get("id"):
                ref.id = str(raw["id"])
            db.add(ref)
            stats["curriculum_new"] += 1
        db.flush()
        if raw.get("id"):
            curriculum_ids[str(raw["id"])] = ref.id

    for i, raw in enumerate(payload.get("materials", [])):
        path = f"materials.{i}"
        if not isinstance(raw, dict):
            _err(errors, path, "Objekt erwartet.")
            continue
        tid = topic_ids.get(str(raw.get("topic_id")), raw.get("topic_id"))
        topic = db.get(Topic, tid) if tid else None
        if topic is None:
            _err(errors, f"{path}.topic_id", "Referenziertes Thema existiert nicht.")
            continue
        refs = [curriculum_ids.get(str(c), str(c)) for c in raw.get("curriculum_ids", [])]
        try:
            m_in = MaterialIn.model_validate({k: v for k, v in raw.items() if k in MaterialIn.model_fields and k not in ("topic_id", "curriculum_ids")} | {"topic_id": topic.id, "curriculum_ids": refs})
        except ValidationError as exc:
            _pyd_errors(errors, path, exc)
            continue
        ref_objs = []
        for cid in m_in.curriculum_ids:
            c = db.get(CurriculumReference, cid)
            if c is None or c.subject_id != topic.subject_id:
                _err(errors, f"{path}.curriculum_ids", f"Bezug {cid} existiert nicht oder passt nicht zum Fach.")
            else:
                ref_objs.append(c)
        existing = db.get(Material, raw["id"]) if raw.get("id") else None
        if existing:
            for k, v in m_in.model_dump(exclude={"curriculum_ids"}).items():
                setattr(existing, k, v)
            existing.curriculum = ref_objs
            existing.status = "draft"
            existing.version += 1
            stats["materials_updated"] += 1
        else:
            m = Material(**m_in.model_dump(exclude={"curriculum_ids"}), status="draft", curriculum=ref_objs)
            if raw.get("id"):
                m.id = str(raw["id"])
            db.add(m)
            stats["materials_new"] += 1
        db.flush()

    applied = not dry_run and not errors
    if applied:
        audit(db, actor_id, "content_imported", "import", None, stats)
    return {"errors": errors, "summary": stats, "applied": applied}
