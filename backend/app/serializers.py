"""Umwandlung von Modellen in JSON-Strukturen der API."""
from __future__ import annotations

from .models import (
    CalendarClosure,
    CurriculumReference,
    Material,
    MaterialFile,
    PlanTemplate,
    PlanUnit,
    SchoolClass,
    SchoolYear,
    Subject,
    Topic,
    User,
)
from .services.calendar import WeekInfo

TYPE_LABELS = {"worksheet": "Arbeitsblatt", "lesson_plan": "Unterrichtsplan", "assessment": "Lernstandskontrolle"}
LEVEL_LABELS = {"basis": "Basis", "standard": "Standard", "erweitert": "Erweitert", "differenziert": "Differenziert (3 Niveaus)"}
STATUS_LABELS = {"draft": "Entwurf", "reviewed": "Geprüft", "released": "Freigegeben", "archived": "Archiviert"}


def user_out(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role,
        "active": u.active,
        "must_change_password": u.must_change_password,
        "version": u.version,
        "created_at": u.created_at.isoformat(),
    }


def subject_out(s: Subject) -> dict:
    return {"id": s.id, "code": s.code, "title": s.title, "sort_order": s.sort_order}


def topic_out(t: Topic) -> dict:
    return {
        "id": t.id,
        "subject_id": t.subject_id,
        "title": t.title,
        "description": t.description,
        "suggested_grade": t.suggested_grade,
        "sequence": t.sequence,
        "planning_note": t.planning_note,
        "prerequisite_ids": [p.id for p in t.prerequisites],
        "archived": t.archived,
        "version": t.version,
    }


def curriculum_out(c: CurriculumReference) -> dict:
    return {
        "id": c.id,
        "subject_id": c.subject_id,
        "official_grade_band": c.official_grade_band,
        "section_code": c.section_code,
        "section_title": c.section_title,
        "paraphrased_goal": c.paraphrased_goal,
        "source_url": c.source_url,
        "source_version": c.source_version,
        "retrieved_on": c.retrieved_on.isoformat() if c.retrieved_on else None,
        "verification_status": c.verification_status,
        "reviewer_id": c.reviewer_id,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "archived": c.archived,
        "version": c.version,
    }


def file_out(f: MaterialFile) -> dict:
    return {
        "id": f.id,
        "purpose": f.purpose,
        "original_name": f.original_name,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "sha256": f.sha256,
        "url": f"/api/v1/materials/{f.material_id}/files/{f.id}",
    }


def material_summary(m: Material, favorite_ids: set[str] | None = None) -> dict:
    files = {f.purpose: f for f in m.files}
    return {
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "topic_id": m.topic_id,
        "topic_title": m.topic.title if m.topic else None,
        "subject_id": m.topic.subject_id if m.topic else None,
        "type": m.type,
        "type_label": TYPE_LABELS.get(m.type, m.type),
        "level": m.level,
        "level_label": LEVEL_LABELS.get(m.level, m.level),
        "duration_minutes": m.duration_minutes,
        "status": m.status,
        "status_label": STATUS_LABELS.get(m.status, m.status),
        "is_demo": m.is_demo,
        "has_main_file": "main" in files,
        "has_solution": "solution" in files,
        "curriculum_ids": [c.id for c in m.curriculum],
        "is_favorite": (m.id in favorite_ids) if favorite_ids is not None else None,
        "version": m.version,
    }


def material_detail(m: Material, favorite_ids: set[str] | None = None) -> dict:
    data = material_summary(m, favorite_ids)
    data.update(
        {
            "learning_goal": m.learning_goal,
            "keywords": [k.strip() for k in m.keywords.split(",") if k.strip()],
            "author": m.author,
            "license_text": m.license_text,
            "reviewer_id": m.reviewer_id,
            "reviewer_name": m.reviewer.display_name if m.reviewer else None,
            "reviewed_at": m.reviewed_at.isoformat() if m.reviewed_at else None,
            "review_note": m.review_note,
            "curriculum": [curriculum_out(c) for c in m.curriculum],
            "files": [file_out(f) for f in sorted(m.files, key=lambda f: f.purpose)],
            "subject_title": m.topic.subject.title if m.topic and m.topic.subject else None,
            "updated_at": m.updated_at.isoformat(),
        }
    )
    return data


def school_year_out(y: SchoolYear) -> dict:
    return {"id": y.id, "label": y.label, "starts_on": y.starts_on.isoformat(), "ends_on": y.ends_on.isoformat(), "version": y.version}


def closure_out(c: CalendarClosure) -> dict:
    return {
        "id": c.id,
        "school_year_id": c.school_year_id,
        "title": c.title,
        "starts_on": c.starts_on.isoformat(),
        "ends_on": c.ends_on.isoformat(),
        "kind": c.kind,
        "source": c.source,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "review_status": c.review_status,
        "version": c.version,
    }


def class_out(c: SchoolClass) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "grade": c.grade,
        "state": c.state,
        "school_type": c.school_type,
        "school_year_id": c.school_year_id,
        "school_year_label": c.school_year.label if c.school_year else None,
        "weekdays": list(c.weekdays),
        "subject_hours": [{"subject_id": h.subject_id, "weekly_hours": h.weekly_hours} for h in c.subject_hours],
        "version": c.version,
    }


def unit_out(u: PlanUnit, visible_material_ids: set[str] | None = None) -> dict:
    materials = []
    for m in u.materials:
        files = {f.purpose for f in m.files}
        materials.append(
            {
                "id": m.id,
                "title": m.title,
                "type": m.type,
                "type_label": TYPE_LABELS.get(m.type, m.type),
                "status": m.status,
                "is_demo": m.is_demo,
                "has_main_file": "main" in files,
                "has_solution": "solution" in files,
                "available": m.status in ("released", "archived"),
            }
        )
    return {
        "id": u.id,
        "class_id": u.class_id,
        "subject_id": u.subject_id,
        "subject_title": u.subject.title if u.subject else None,
        "topic_id": u.topic_id,
        "topic_title": u.topic.title if u.topic else None,
        "week_start_date": u.week_start_date.isoformat(),
        "planned_lessons": u.planned_lessons,
        "status": u.status,
        "notes": u.notes,
        "sequence": u.sequence,
        "materials": materials,
        "curriculum": [{"id": c.id, "section_code": c.section_code, "paraphrased_goal": c.paraphrased_goal, "verification_status": c.verification_status} for c in u.curriculum],
        "version": u.version,
        "updated_at": u.updated_at.isoformat(),
    }


def week_out(w: WeekInfo) -> dict:
    return {
        "week_start": w.week_start.isoformat(),
        "week_end": w.week_end.isoformat(),
        "iso_year": w.iso_year,
        "iso_week": w.iso_week,
        "in_school_year": w.in_school_year,
        "teaching_week": w.teaching_week,
        "teaching_days": [d.isoformat() for d in w.teaching_days],
        "regular_days": w.regular_days,
        "shortened": w.shortened,
        "fully_free": w.fully_free,
        "closures": [{"title": c.title, "kind": c.kind, "starts_on": c.starts_on.isoformat(), "ends_on": c.ends_on.isoformat(), "approved": c.approved} for c in w.closures],
    }


def template_out(t: PlanTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "subject_id": t.subject_id,
        "grade": t.grade,
        "archived": t.archived,
        "version": t.version,
        "units": [
            {
                "id": u.id,
                "topic_id": u.topic_id,
                "topic_title": u.topic.title if u.topic else None,
                "sequence": u.sequence,
                "estimated_lessons": u.estimated_lessons,
                "material_ids": [m.id for m in u.materials],
                "curriculum_ids": [c.id for c in u.curriculum],
            }
            for u in t.units
        ],
    }
