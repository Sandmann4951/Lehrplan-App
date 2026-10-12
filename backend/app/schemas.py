"""Eingabeschemata (Pydantic). Freitexte werden als reiner Text behandelt."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import CLOSURE_KINDS, MATERIAL_LEVELS, MATERIAL_TYPES, UNIT_STATUSES
from .security import normalize_email


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# -- Auth --------------------------------------------------------------------
class LoginIn(Strict):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        return normalize_email(v)


class ChangePasswordIn(Strict):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


# -- Klassen -------------------------------------------------------------------
class SubjectHoursIn(Strict):
    subject_id: str
    weekly_hours: int = Field(ge=0, le=20)


class ClassCreate(Strict):
    name: str = Field(min_length=1, max_length=100)
    school_year_id: str
    grade: Literal[1] = 1
    state: Literal["BY"] = "BY"
    school_type: Literal["grundschule"] = "grundschule"
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    subject_hours: list[SubjectHoursIn] = Field(default_factory=list)

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, v: list[int]) -> list[int]:
        v = sorted(set(v))
        if not v:
            raise ValueError("Mindestens ein Unterrichtswochentag ist erforderlich.")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("Wochentage 0 (Montag) bis 6 (Sonntag).")
        return v


class ClassUpdate(Strict):
    version: int
    name: str | None = Field(default=None, min_length=1, max_length=100)
    school_year_id: str | None = None
    weekdays: list[int] | None = None
    subject_hours: list[SubjectHoursIn] | None = None

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        return ClassCreate._weekdays(v)


# -- Plan ----------------------------------------------------------------------
class UnitCreate(Strict):
    subject_id: str
    topic_id: str
    week_start_date: date
    planned_lessons: int = Field(gt=0, le=60)
    status: Literal["planned", "started", "completed"] = "planned"
    notes: str = Field(default="", max_length=5000)
    material_ids: list[str] = Field(default_factory=list)
    curriculum_ids: list[str] = Field(default_factory=list)


class UnitUpdate(Strict):
    version: int
    topic_id: str | None = None
    week_start_date: date | None = None
    planned_lessons: int | None = Field(default=None, gt=0, le=60)
    status: Literal["planned", "started", "completed"] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    material_ids: list[str] | None = None
    curriculum_ids: list[str] | None = None


class UnitCheckIn(Strict):
    subject_id: str
    week_start_date: date
    planned_lessons: int = Field(gt=0, le=60)
    unit_id: str | None = None


class InitializePlanIn(Strict):
    template_ids: list[str] = Field(default_factory=list, description="Leer = alle aktiven Vorlagen für Klasse 1")
    start_week: date | None = None
    confirm: bool = Field(default=False, description="Muss true sein: Vorlagenkopie nur nach bestätigter Aktion")
    replace_existing: bool = Field(default=False, description="Vorhandene Einheiten ersetzen (nur mit Bestätigung)")


# -- Admin: Benutzer ---------------------------------------------------------
class UserCreate(Strict):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["teacher", "admin"] = "teacher"

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        v = normalize_email(v)
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("Ungültige E-Mail-Adresse.")
        return v


class UserUpdate(Strict):
    version: int
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["teacher", "admin"] | None = None
    active: bool | None = None


# -- Admin: Inhalte ----------------------------------------------------------
class TopicIn(Strict):
    subject_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    suggested_grade: int = Field(default=1, ge=1, le=4)
    sequence: int = 0
    planning_note: str = Field(default="", max_length=2000)
    prerequisite_ids: list[str] = Field(default_factory=list)


class TopicUpdate(Strict):
    version: int
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    suggested_grade: int | None = Field(default=None, ge=1, le=4)
    sequence: int | None = None
    planning_note: str | None = Field(default=None, max_length=2000)
    prerequisite_ids: list[str] | None = None
    archived: bool | None = None


class CurriculumIn(Strict):
    subject_id: str
    official_grade_band: str = Field(default="1/2", max_length=10)
    section_code: str = Field(min_length=1, max_length=40)
    section_title: str = Field(default="", max_length=300)
    paraphrased_goal: str = Field(min_length=1, max_length=2000)
    source_url: str = Field(min_length=1, max_length=500)
    source_version: str = Field(default="", max_length=100)
    retrieved_on: date | None = None


class CurriculumUpdate(Strict):
    version: int
    section_title: str | None = Field(default=None, max_length=300)
    paraphrased_goal: str | None = Field(default=None, min_length=1, max_length=2000)
    source_url: str | None = Field(default=None, max_length=500)
    source_version: str | None = Field(default=None, max_length=100)
    retrieved_on: date | None = None
    verification_status: Literal["unverified", "verified"] | None = None
    archived: bool | None = None


class MaterialIn(Strict):
    topic_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    learning_goal: str = Field(default="", max_length=2000)
    keywords: str = Field(default="", max_length=1000)
    type: str
    level: str
    duration_minutes: int = Field(gt=0, le=600)
    author: str = Field(default="", max_length=200)
    license_text: str = Field(default="", max_length=2000)
    curriculum_ids: list[str] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in MATERIAL_TYPES:
            raise ValueError(f"Erlaubt: {', '.join(MATERIAL_TYPES)}")
        return v

    @field_validator("level")
    @classmethod
    def _level(cls, v: str) -> str:
        if v not in MATERIAL_LEVELS:
            raise ValueError(f"Erlaubt: {', '.join(MATERIAL_LEVELS)}")
        return v


class MaterialUpdate(Strict):
    version: int
    topic_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    learning_goal: str | None = Field(default=None, max_length=2000)
    keywords: str | None = Field(default=None, max_length=1000)
    type: str | None = None
    level: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=600)
    author: str | None = Field(default=None, max_length=200)
    license_text: str | None = Field(default=None, max_length=2000)
    curriculum_ids: list[str] | None = None

    @field_validator("type")
    @classmethod
    def _type(cls, v: str | None) -> str | None:
        return v if v is None else MaterialIn._type(v)

    @field_validator("level")
    @classmethod
    def _level(cls, v: str | None) -> str | None:
        return v if v is None else MaterialIn._level(v)


class MaterialReviewIn(Strict):
    version: int
    reviewer_id: str
    reviewed_at: date
    review_note: str = Field(default="", max_length=2000)


class VersionIn(Strict):
    version: int


# -- Admin: Kalender ----------------------------------------------------------
class SchoolYearIn(Strict):
    label: str = Field(min_length=4, max_length=20)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def _interval(self):
        if self.ends_on < self.starts_on:
            raise ValueError("Ende muss am oder nach dem Beginn liegen.")
        return self


class SchoolYearUpdate(Strict):
    version: int
    label: str | None = Field(default=None, min_length=4, max_length=20)
    starts_on: date | None = None
    ends_on: date | None = None


class ClosureIn(Strict):
    school_year_id: str
    title: str = Field(min_length=1, max_length=200)
    starts_on: date
    ends_on: date
    kind: str = "holiday"
    source: str = Field(default="", max_length=1000)
    reviewed_at: date | None = None
    review_status: Literal["unreviewed", "approved"] = "unreviewed"

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in CLOSURE_KINDS:
            raise ValueError(f"Erlaubt: {', '.join(CLOSURE_KINDS)}")
        return v

    @model_validator(mode="after")
    def _interval(self):
        if self.ends_on < self.starts_on:
            raise ValueError("Ende muss am oder nach dem Beginn liegen.")
        if self.review_status == "approved" and self.reviewed_at is None:
            raise ValueError("Freigegebene Einträge benötigen ein Prüfdatum.")
        return self


class ClosureUpdate(Strict):
    version: int
    title: str | None = Field(default=None, min_length=1, max_length=200)
    starts_on: date | None = None
    ends_on: date | None = None
    kind: str | None = None
    source: str | None = Field(default=None, max_length=1000)
    reviewed_at: date | None = None
    review_status: Literal["unreviewed", "approved"] | None = None


# -- Admin: Vorlagen --------------------------------------------------------
class TemplateUnitIn(Strict):
    topic_id: str
    estimated_lessons: int = Field(gt=0, le=200)
    material_ids: list[str] = Field(default_factory=list)
    curriculum_ids: list[str] = Field(default_factory=list)


class TemplateIn(Strict):
    name: str = Field(min_length=1, max_length=200)
    subject_id: str
    units: list[TemplateUnitIn] = Field(default_factory=list)


class TemplateUpdate(Strict):
    version: int
    name: str | None = Field(default=None, min_length=1, max_length=200)
    archived: bool | None = None
    units: list[TemplateUnitIn] | None = None


ALLOWED_STATUSES = UNIT_STATUSES
