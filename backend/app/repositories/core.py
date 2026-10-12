"""Repository-Schicht: kapselt Abfragen, damit Services datenbankunabhängig bleiben.

Alle Abfragen sind Standard-SQLAlchemy ohne SQLite-Spezifika, so dass ein späterer
Wechsel auf PostgreSQL nur Konfiguration und Migration betrifft.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    CalendarClosure,
    CurriculumReference,
    Favorite,
    Material,
    PlanTemplate,
    PlanUnit,
    SchoolClass,
    SchoolYear,
    Subject,
    Topic,
    User,
)


class ClassRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_owner(self, owner_id: str) -> Sequence[SchoolClass]:
        return self.db.scalars(
            select(SchoolClass)
            .where(SchoolClass.owner_id == owner_id)
            .options(selectinload(SchoolClass.subject_hours), selectinload(SchoolClass.school_year))
            .order_by(SchoolClass.name)
        ).all()

    def get_owned(self, class_id: str, owner_id: str) -> SchoolClass | None:
        """Liefert nur Klassen des Eigentümers; fremde Klassen sind 'nicht vorhanden'."""
        return self.db.scalar(
            select(SchoolClass).where(SchoolClass.id == class_id, SchoolClass.owner_id == owner_id)
        )


class UnitRepository:
    def __init__(self, db: Session):
        self.db = db

    def _base(self):
        return select(PlanUnit).options(
            selectinload(PlanUnit.materials).selectinload(Material.files),
            selectinload(PlanUnit.curriculum),
            selectinload(PlanUnit.topic),
            selectinload(PlanUnit.subject),
        )

    def list_for_class(self, class_id: str, from_date: date | None = None, to_date: date | None = None) -> Sequence[PlanUnit]:
        q = self._base().where(PlanUnit.class_id == class_id)
        if from_date:
            q = q.where(PlanUnit.week_start_date >= from_date)
        if to_date:
            q = q.where(PlanUnit.week_start_date <= to_date)
        return self.db.scalars(q.order_by(PlanUnit.week_start_date, PlanUnit.subject_id, PlanUnit.sequence, PlanUnit.id)).all()

    def get_owned(self, unit_id: str, owner_id: str) -> PlanUnit | None:
        return self.db.scalar(
            self._base().join(SchoolClass, SchoolClass.id == PlanUnit.class_id).where(PlanUnit.id == unit_id, SchoolClass.owner_id == owner_id)
        )

    def count_for_class(self, class_id: str) -> int:
        return self.db.scalar(select(func.count()).select_from(PlanUnit).where(PlanUnit.class_id == class_id)) or 0

    def lessons_in_week(self, class_id: str, subject_id: str, week: date, exclude_unit_id: str | None = None) -> int:
        q = select(func.coalesce(func.sum(PlanUnit.planned_lessons), 0)).where(
            PlanUnit.class_id == class_id, PlanUnit.subject_id == subject_id, PlanUnit.week_start_date == week
        )
        if exclude_unit_id:
            q = q.where(PlanUnit.id != exclude_unit_id)
        return int(self.db.scalar(q) or 0)


class MaterialRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, material_id: str) -> Material | None:
        return self.db.scalar(
            select(Material)
            .where(Material.id == material_id)
            .options(selectinload(Material.files), selectinload(Material.curriculum), selectinload(Material.topic).selectinload(Topic.subject))
        )

    def search(
        self,
        *,
        statuses: Sequence[str],
        subject_ids: Sequence[str] = (),
        topic_ids: Sequence[str] = (),
        curriculum_ids: Sequence[str] = (),
        levels: Sequence[str] = (),
        types: Sequence[str] = (),
        duration_min: int | None = None,
        duration_max: int | None = None,
        grade: int | None = None,
        text: str | None = None,
    ) -> list[tuple[str, str, str, str]]:
        """Liefert leichte Trefferzeilen (id, title, description, keywords)."""
        q = (
            select(Material.id, Material.title, Material.description, Material.keywords)
            .join(Topic, Topic.id == Material.topic_id)
            .where(Material.status.in_(list(statuses)))
        )
        if subject_ids:
            q = q.where(Topic.subject_id.in_(list(subject_ids)))
        if topic_ids:
            q = q.where(Material.topic_id.in_(list(topic_ids)))
        if levels:
            q = q.where(Material.level.in_(list(levels)))
        if types:
            q = q.where(Material.type.in_(list(types)))
        if duration_min is not None:
            q = q.where(Material.duration_minutes >= duration_min)
        if duration_max is not None:
            q = q.where(Material.duration_minutes <= duration_max)
        if grade is not None:
            q = q.where(Topic.suggested_grade == grade)
        if curriculum_ids:
            from ..models import material_curriculum

            sub = select(material_curriculum.c.material_id).where(material_curriculum.c.curriculum_id.in_(list(curriculum_ids)))
            q = q.where(Material.id.in_(sub))
        if text:
            for term in text.lower().split():
                like = f"%{term}%"
                q = q.where(
                    or_(
                        func.lower(Material.title).like(like),
                        func.lower(Material.description).like(like),
                        func.lower(Material.keywords).like(like),
                    )
                )
        return [tuple(r) for r in self.db.execute(q).all()]

    def load_many(self, ids: Sequence[str]) -> list[Material]:
        if not ids:
            return []
        rows = self.db.scalars(
            select(Material)
            .where(Material.id.in_(list(ids)))
            .options(selectinload(Material.files), selectinload(Material.curriculum), selectinload(Material.topic).selectinload(Topic.subject))
        ).all()
        by_id = {m.id: m for m in rows}
        return [by_id[i] for i in ids if i in by_id]


class ReferenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def subjects(self) -> Sequence[Subject]:
        return self.db.scalars(select(Subject).order_by(Subject.sort_order, Subject.title)).all()

    def topics(self, include_archived: bool = False) -> Sequence[Topic]:
        q = select(Topic).options(selectinload(Topic.prerequisites))
        if not include_archived:
            q = q.where(Topic.archived.is_(False))
        return self.db.scalars(q.order_by(Topic.subject_id, Topic.sequence, Topic.title)).all()

    def curriculum(self, include_archived: bool = False) -> Sequence[CurriculumReference]:
        q = select(CurriculumReference)
        if not include_archived:
            q = q.where(CurriculumReference.archived.is_(False))
        return self.db.scalars(q.order_by(CurriculumReference.subject_id, CurriculumReference.section_code)).all()

    def school_years(self) -> Sequence[SchoolYear]:
        return self.db.scalars(select(SchoolYear).order_by(SchoolYear.starts_on)).all()

    def closures(self, school_year_id: str) -> Sequence[CalendarClosure]:
        return self.db.scalars(
            select(CalendarClosure).where(CalendarClosure.school_year_id == school_year_id).order_by(CalendarClosure.starts_on)
        ).all()

    def templates(self, include_archived: bool = False) -> Sequence[PlanTemplate]:
        q = select(PlanTemplate).options(selectinload(PlanTemplate.units))
        if not include_archived:
            q = q.where(PlanTemplate.archived.is_(False))
        return self.db.scalars(q.order_by(PlanTemplate.name)).all()


class FavoriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def ids_for_user(self, user_id: str) -> set[str]:
        return set(self.db.scalars(select(Favorite.material_id).where(Favorite.user_id == user_id)).all())

    def get(self, user_id: str, material_id: str) -> Favorite | None:
        return self.db.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.material_id == material_id))


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))
