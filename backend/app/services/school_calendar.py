"""Verbindet Kalenderregeln mit gespeicherten Stammdaten."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import CalendarClosure, SchoolClass, SchoolYear
from .calendar import Closure, SchoolCalendar


def today_local() -> date:
    return datetime.now(settings.timezone).date()


def closures_for_year(db: Session, school_year_id: str) -> list[Closure]:
    rows = db.scalars(select(CalendarClosure).where(CalendarClosure.school_year_id == school_year_id)).all()
    return [Closure(r.starts_on, r.ends_on, r.title, r.kind, r.review_status == "approved") for r in rows]


def calendar_for(db: Session, year: SchoolYear, weekdays: list[int]) -> SchoolCalendar:
    return SchoolCalendar(year.starts_on, year.ends_on, weekdays, closures_for_year(db, year.id))


def calendar_for_class(db: Session, cls: SchoolClass) -> SchoolCalendar:
    return calendar_for(db, cls.school_year, list(cls.weekdays))


def calendar_status(db: Session, school_year_id: str) -> dict:
    rows = db.scalars(select(CalendarClosure).where(CalendarClosure.school_year_id == school_year_id)).all()
    unreviewed = sum(1 for r in rows if r.review_status != "approved")
    return {"total": len(rows), "unreviewed": unreviewed, "approved": len(rows) - unreviewed, "demo_only": unreviewed > 0 or not rows}
