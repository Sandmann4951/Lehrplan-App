"""Planungsservice (F06): Vorlagenkopie, Kapazität und Warnungen."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..errors import ApiError, invalid
from ..models import PlanTemplate, PlanUnit, SchoolClass, TemplateUnit
from ..repositories.core import UnitRepository
from .calendar import SchoolCalendar, week_start
from .school_calendar import calendar_for_class


def subject_hours(cls: SchoolClass) -> dict[str, int]:
    return {h.subject_id: h.weekly_hours for h in cls.subject_hours}


def week_warnings(db: Session, cls: SchoolClass, subject_id: str, week: date, lessons: int, exclude_unit_id: str | None = None, cal: SchoolCalendar | None = None) -> list[dict]:
    cal = cal or calendar_for_class(db, cls)
    info = cal.week_info(week)
    warnings: list[dict] = []
    if not info.in_school_year:
        warnings.append({"code": "outside_school_year", "message": "Die Zielwoche liegt außerhalb des Schuljahrs."})
        return warnings
    if info.fully_free:
        warnings.append({"code": "free_week", "message": "Die Zielwoche ist vollständig unterrichtsfrei (Ferien oder schulfreie Tage)."})
        return warnings
    hours = subject_hours(cls).get(subject_id, 0)
    capacity = info.capacity(hours)
    used = UnitRepository(db).lessons_in_week(cls.id, subject_id, info.week_start, exclude_unit_id)
    if used + lessons > capacity:
        warnings.append(
            {
                "code": "overplanned",
                "message": f"Überplanung: {used + lessons} geplante Stunden bei einer Kapazität von {capacity} Stunden in dieser Woche.",
                "capacity": capacity,
                "planned": used + lessons,
            }
        )
    return warnings


def normalize_week(d: date) -> date:
    return week_start(d)


def initialize_plan(
    db: Session,
    cls: SchoolClass,
    template_ids: list[str],
    start_week: date | None,
    replace_existing: bool,
) -> dict:
    """Kopiert Vorlagen in den persönlichen Plan.

    Die Zuordnung füllt Unterrichtswochen anhand der verfügbaren (ggf. verkürzten)
    Stunden je Fach. Lange Einheiten erhalten mehrere Planeinträge. Spätere
    Vorlagenänderungen wirken nicht auf die Kopie.
    """
    repo = UnitRepository(db)
    existing = repo.count_for_class(cls.id)
    if existing and not replace_existing:
        raise ApiError(
            422,
            "plan_not_empty",
            f"Der Plan enthält bereits {existing} Einheiten. Bitte ausdrücklich bestätigen, dass diese ersetzt werden sollen.",
            extra={"existing_units": existing},
        )

    q = select(PlanTemplate).where(PlanTemplate.archived.is_(False), PlanTemplate.grade == cls.grade).options(
        selectinload(PlanTemplate.units).selectinload(TemplateUnit.materials),
        selectinload(PlanTemplate.units).selectinload(TemplateUnit.curriculum),
    )
    if template_ids:
        q = q.where(PlanTemplate.id.in_(template_ids))
    templates = list(db.scalars(q.order_by(PlanTemplate.name)).all())
    if template_ids and len(templates) != len(set(template_ids)):
        raise invalid("Unbekannte oder archivierte Vorlage.", {"template_ids": "Vorlage nicht gefunden."})
    if not templates:
        raise invalid("Keine passende Vorlage vorhanden.")

    if existing and replace_existing:
        db.execute(delete(PlanUnit).where(PlanUnit.class_id == cls.id))

    cal = calendar_for_class(db, cls)
    start = week_start(start_week) if start_week else cal.first_week()
    weeks = [w for w in cal.teaching_weeks() if w >= start]
    hours = subject_hours(cls)

    created = 0
    unplaced: list[dict] = []
    per_subject: dict[str, int] = defaultdict(int)
    seen_subjects: set[str] = set()
    for tpl in templates:
        if tpl.subject_id in seen_subjects:
            raise invalid("Pro Fach darf nur eine Vorlage gewählt werden.", {"template_ids": "Mehrere Vorlagen für dasselbe Fach."})
        seen_subjects.add(tpl.subject_id)
        weekly = hours.get(tpl.subject_id, 0)
        capacities = [(w, cal.week_info(w).capacity(weekly)) for w in weeks]
        idx = 0
        used_in_week = 0
        seq = 0
        for tu in tpl.units:
            remaining = tu.estimated_lessons
            while remaining > 0:
                while idx < len(capacities) and capacities[idx][1] - used_in_week <= 0:
                    idx += 1
                    used_in_week = 0
                if idx >= len(capacities):
                    unplaced.append({"template": tpl.name, "topic_id": tu.topic_id, "lessons": remaining})
                    break
                week, cap = capacities[idx]
                take = min(remaining, cap - used_in_week)
                seq += 1
                db.add(
                    PlanUnit(
                        class_id=cls.id,
                        subject_id=tpl.subject_id,
                        topic_id=tu.topic_id,
                        week_start_date=week,
                        planned_lessons=take,
                        status="planned",
                        notes="",
                        sequence=seq,
                        template_unit_id=tu.id,
                        materials=list(tu.materials),
                        curriculum=list(tu.curriculum),
                    )
                )
                created += 1
                per_subject[tpl.subject_id] += take
                used_in_week += take
                remaining -= take
    return {"created_units": created, "lessons_per_subject": dict(per_subject), "unplaced": unplaced, "replaced_units": existing if replace_existing else 0}
