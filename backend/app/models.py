"""SQLAlchemy-Datenmodell.

Alle Entitäten besitzen stabile UUIDs (als Text, portabel zu PostgreSQL),
created_at/updated_at in UTC. Veränderbare Datensätze tragen ``version``
für optimistische Konfliktprüfung.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Speichert naive UTC-Werte, liefert zeitzonenbewusste UTC-Werte."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


# ---------------------------------------------------------------------------
# Benutzer und Sitzungen
# ---------------------------------------------------------------------------

ROLE_TEACHER = "teacher"
ROLE_ADMIN = "admin"


class User(IdMixin, VersionMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('teacher','admin')", name="ck_users_role"),)

    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=ROLE_TEACHER)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class UserSession(IdMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    user: Mapped[User] = relationship()


class LoginAttempt(IdMixin, Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_lookup", "email", "ip", "attempted_at"),)

    email: Mapped[str] = mapped_column(String(254), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ---------------------------------------------------------------------------
# Schuljahr und Kalender
# ---------------------------------------------------------------------------


class SchoolYear(IdMixin, VersionMixin, Base):
    __tablename__ = "school_years"
    __table_args__ = (CheckConstraint("ends_on >= starts_on", name="ck_school_years_interval"),)

    label: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)

    closures: Mapped[list["CalendarClosure"]] = relationship(back_populates="school_year", order_by="CalendarClosure.starts_on")


CLOSURE_KINDS = ("holiday", "public_holiday", "school_free", "special")
REVIEW_STATUSES = ("unreviewed", "approved")


class CalendarClosure(IdMixin, VersionMixin, Base):
    __tablename__ = "calendar_closures"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="ck_closures_interval"),
        CheckConstraint("kind in ('holiday','public_holiday','school_free','special')", name="ck_closures_kind"),
        CheckConstraint("review_status in ('unreviewed','approved')", name="ck_closures_review"),
    )

    school_year_id: Mapped[str] = mapped_column(ForeignKey("school_years.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unreviewed")

    school_year: Mapped[SchoolYear] = relationship(back_populates="closures")


# ---------------------------------------------------------------------------
# Fächer, Themen, Lehrplanbezug
# ---------------------------------------------------------------------------


class Subject(IdMixin, VersionMixin, Base):
    __tablename__ = "subjects"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


topic_prerequisites = Table(
    "topic_prerequisites",
    Base.metadata,
    Column("topic_id", ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    Column("prerequisite_id", ForeignKey("topics.id", ondelete="RESTRICT"), primary_key=True),
)


class Topic(IdMixin, VersionMixin, Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "title", name="uq_topics_subject_title"),)

    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggested_grade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planning_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    subject: Mapped[Subject] = relationship()
    prerequisites: Mapped[list["Topic"]] = relationship(
        secondary=topic_prerequisites,
        primaryjoin=lambda: Topic.id == topic_prerequisites.c.topic_id,
        secondaryjoin=lambda: Topic.id == topic_prerequisites.c.prerequisite_id,
    )


class CurriculumReference(IdMixin, VersionMixin, Base):
    __tablename__ = "curriculum_references"
    __table_args__ = (
        UniqueConstraint("subject_id", "official_grade_band", "section_code", name="uq_curriculum_section"),
        CheckConstraint("verification_status in ('unverified','verified')", name="ck_curriculum_status"),
    )

    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    official_grade_band: Mapped[str] = mapped_column(String(10), nullable=False)
    section_code: Mapped[str] = mapped_column(String(40), nullable=False)
    section_title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    paraphrased_goal: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_version: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    retrieved_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified")
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    subject: Mapped[Subject] = relationship()


# ---------------------------------------------------------------------------
# Materialien
# ---------------------------------------------------------------------------

MATERIAL_TYPES = ("worksheet", "lesson_plan", "assessment")
MATERIAL_LEVELS = ("basis", "standard", "erweitert", "differenziert")
MATERIAL_STATUSES = ("draft", "reviewed", "released", "archived")

material_curriculum = Table(
    "material_curriculum",
    Base.metadata,
    Column("material_id", ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
    Column("curriculum_id", ForeignKey("curriculum_references.id", ondelete="RESTRICT"), primary_key=True),
)


class Material(IdMixin, VersionMixin, Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint("type in ('worksheet','lesson_plan','assessment')", name="ck_materials_type"),
        CheckConstraint("level in ('basis','standard','erweitert','differenziert')", name="ck_materials_level"),
        CheckConstraint("status in ('draft','reviewed','released','archived')", name="ck_materials_status"),
        CheckConstraint("duration_minutes > 0", name="ck_materials_duration"),
        Index("ix_materials_search", "status", "topic_id"),
    )

    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    learning_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    author: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    license_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    topic: Mapped[Topic] = relationship()
    curriculum: Mapped[list[CurriculumReference]] = relationship(secondary=material_curriculum)
    files: Mapped[list["MaterialFile"]] = relationship(back_populates="material", cascade="all, delete-orphan")
    reviewer: Mapped[User | None] = relationship()


class MaterialFile(IdMixin, Base):
    __tablename__ = "material_files"
    __table_args__ = (
        UniqueConstraint("material_id", "purpose", name="uq_material_file_purpose"),
        CheckConstraint("purpose in ('main','solution')", name="ck_material_files_purpose"),
    )

    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(10), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    material: Mapped[Material] = relationship(back_populates="files")


# ---------------------------------------------------------------------------
# Vorlagen
# ---------------------------------------------------------------------------

template_unit_materials = Table(
    "template_unit_materials",
    Base.metadata,
    Column("template_unit_id", ForeignKey("template_units.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", ForeignKey("materials.id", ondelete="RESTRICT"), primary_key=True),
)
template_unit_curriculum = Table(
    "template_unit_curriculum",
    Base.metadata,
    Column("template_unit_id", ForeignKey("template_units.id", ondelete="CASCADE"), primary_key=True),
    Column("curriculum_id", ForeignKey("curriculum_references.id", ondelete="RESTRICT"), primary_key=True),
)


class PlanTemplate(IdMixin, VersionMixin, Base):
    __tablename__ = "plan_templates"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    subject: Mapped[Subject] = relationship()
    units: Mapped[list["TemplateUnit"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateUnit.sequence"
    )


class TemplateUnit(IdMixin, Base):
    __tablename__ = "template_units"
    __table_args__ = (
        UniqueConstraint("template_id", "sequence", name="uq_template_unit_sequence"),
        CheckConstraint("estimated_lessons > 0", name="ck_template_units_lessons"),
    )

    template_id: Mapped[str] = mapped_column(ForeignKey("plan_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_lessons: Mapped[int] = mapped_column(Integer, nullable=False)

    template: Mapped[PlanTemplate] = relationship(back_populates="units")
    topic: Mapped[Topic] = relationship()
    materials: Mapped[list[Material]] = relationship(secondary=template_unit_materials)
    curriculum: Mapped[list[CurriculumReference]] = relationship(secondary=template_unit_curriculum)


# ---------------------------------------------------------------------------
# Klassen und persönliche Pläne
# ---------------------------------------------------------------------------


class SchoolClass(IdMixin, VersionMixin, Base):
    __tablename__ = "classes"
    __table_args__ = (
        CheckConstraint("grade = 1", name="ck_classes_grade_pilot"),
        CheckConstraint("state = 'BY'", name="ck_classes_state_pilot"),
        CheckConstraint("school_type = 'grundschule'", name="ck_classes_school_type_pilot"),
    )

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    state: Mapped[str] = mapped_column(String(5), nullable=False, default="BY")
    school_type: Mapped[str] = mapped_column(String(30), nullable=False, default="grundschule")
    school_year_id: Mapped[str] = mapped_column(ForeignKey("school_years.id", ondelete="RESTRICT"), nullable=False)
    weekdays: Mapped[list[int]] = mapped_column(JSON, nullable=False)

    school_year: Mapped[SchoolYear] = relationship()
    subject_hours: Mapped[list["ClassSubjectHours"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )
    units: Mapped[list["PlanUnit"]] = relationship(back_populates="school_class", cascade="all, delete-orphan", passive_deletes=True)


class ClassSubjectHours(Base):
    __tablename__ = "class_subject_hours"
    __table_args__ = (CheckConstraint("weekly_hours >= 0", name="ck_class_hours"),)

    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), primary_key=True)
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False)

    school_class: Mapped[SchoolClass] = relationship(back_populates="subject_hours")
    subject: Mapped[Subject] = relationship()


UNIT_STATUSES = ("planned", "started", "completed")

plan_unit_materials = Table(
    "plan_unit_materials",
    Base.metadata,
    Column("plan_unit_id", ForeignKey("plan_units.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", ForeignKey("materials.id", ondelete="RESTRICT"), primary_key=True),
)
plan_unit_curriculum = Table(
    "plan_unit_curriculum",
    Base.metadata,
    Column("plan_unit_id", ForeignKey("plan_units.id", ondelete="CASCADE"), primary_key=True),
    Column("curriculum_id", ForeignKey("curriculum_references.id", ondelete="RESTRICT"), primary_key=True),
)


class PlanUnit(IdMixin, VersionMixin, Base):
    __tablename__ = "plan_units"
    __table_args__ = (
        CheckConstraint("planned_lessons > 0", name="ck_plan_units_lessons"),
        CheckConstraint("status in ('planned','started','completed')", name="ck_plan_units_status"),
        Index("ix_plan_units_class_week", "class_id", "week_start_date"),
    )

    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_lessons: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    template_unit_id: Mapped[str | None] = mapped_column(ForeignKey("template_units.id", ondelete="SET NULL"), nullable=True)

    school_class: Mapped[SchoolClass] = relationship(back_populates="units")
    subject: Mapped[Subject] = relationship()
    topic: Mapped[Topic] = relationship()
    materials: Mapped[list[Material]] = relationship(secondary=plan_unit_materials)
    curriculum: Mapped[list[CurriculumReference]] = relationship(secondary=plan_unit_curriculum)


class Favorite(IdMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "material_id", name="uq_favorites_user_material"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=False)

    material: Mapped[Material] = relationship()


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
