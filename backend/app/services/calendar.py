"""Kalenderlogik (F05): ISO-Kalenderwochen und Unterrichtswochen.

Reine Funktionen ohne Datenbankzugriff, damit die Regeln direkt testbar sind.

Regeln:
- Eine Woche läuft von Montag bis Sonntag.
- Ein vorgesehener Unterrichtstag ist ein ausgewählter Klassenwochentag innerhalb
  des Schuljahrs, der in keinem Ferien- oder schulfreien Intervall liegt
  (Grenzen jeweils einschließlich).
- Die erste Woche mit mindestens einem Unterrichtstag ist Unterrichtswoche 1.
- Vollständig freie Wochen erhöhen die Zählung nicht; teilweise freie Wochen
  zählen, sind aber verkürzt.
- Außerhalb des Schuljahrs gibt es keine Unterrichtswochenzahl.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Sequence

WEEKDAY_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def merge_intervals(intervals: Iterable[tuple[date, date]]) -> list[tuple[date, date]]:
    """Überlappende oder direkt angrenzende Intervalle vereinigen."""
    result: list[tuple[date, date]] = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1] + timedelta(days=1):
            prev_start, prev_end = result[-1]
            result[-1] = (prev_start, max(prev_end, end))
        else:
            result.append((start, end))
    return result


@dataclass(frozen=True)
class Closure:
    starts_on: date
    ends_on: date
    title: str = ""
    kind: str = "holiday"
    approved: bool = True


@dataclass
class WeekInfo:
    week_start: date
    week_end: date
    iso_year: int
    iso_week: int
    in_school_year: bool
    teaching_week: int | None
    teaching_days: list[date]
    regular_days: int
    shortened: bool
    fully_free: bool
    closures: list[Closure] = field(default_factory=list)

    @property
    def active_days(self) -> int:
        return len(self.teaching_days)

    def capacity(self, weekly_hours: int) -> int:
        """Verkürzte Wochenkapazität = Wochenstunden × aktive Tage / reguläre Tage, abgerundet."""
        if self.regular_days == 0:
            return 0
        return (weekly_hours * self.active_days) // self.regular_days


class SchoolCalendar:
    def __init__(self, starts_on: date, ends_on: date, weekdays: Sequence[int], closures: Iterable[Closure] = ()):
        if ends_on < starts_on:
            raise ValueError("Ende des Schuljahrs liegt vor dem Beginn.")
        if not weekdays:
            raise ValueError("Mindestens ein Unterrichtswochentag ist erforderlich.")
        self.starts_on = starts_on
        self.ends_on = ends_on
        self.weekdays = sorted(set(int(w) for w in weekdays))
        self.closures = sorted(closures, key=lambda c: (c.starts_on, c.ends_on))
        self._free = merge_intervals((c.starts_on, c.ends_on) for c in self.closures)
        self._week_numbers: dict[date, int] | None = None

    # -- Tage ---------------------------------------------------------------
    def is_closed(self, d: date) -> bool:
        for start, end in self._free:
            if start <= d <= end:
                return True
            if start > d:
                break
        return False

    def is_teaching_day(self, d: date) -> bool:
        return (
            self.starts_on <= d <= self.ends_on
            and d.weekday() in self.weekdays
            and not self.is_closed(d)
        )

    def teaching_days_in_week(self, monday: date) -> list[date]:
        return [monday + timedelta(days=i) for i in range(7) if self.is_teaching_day(monday + timedelta(days=i))]

    # -- Wochen -------------------------------------------------------------
    def first_week(self) -> date:
        return week_start(self.starts_on)

    def last_week(self) -> date:
        return week_start(self.ends_on)

    def all_weeks(self) -> list[date]:
        weeks = []
        w = self.first_week()
        while w <= self.last_week():
            weeks.append(w)
            w += timedelta(days=7)
        return weeks

    def _numbers(self) -> dict[date, int]:
        if self._week_numbers is None:
            numbers: dict[date, int] = {}
            n = 0
            for w in self.all_weeks():
                if self.teaching_days_in_week(w):
                    n += 1
                    numbers[w] = n
            self._week_numbers = numbers
        return self._week_numbers

    def teaching_week_number(self, d: date) -> int | None:
        return self._numbers().get(week_start(d))

    def teaching_weeks(self) -> list[date]:
        return sorted(self._numbers())

    def week_info(self, d: date) -> WeekInfo:
        monday = week_start(d)
        sunday = monday + timedelta(days=6)
        iso = monday.isocalendar()
        in_year = not (sunday < self.starts_on or monday > self.ends_on)
        days = self.teaching_days_in_week(monday) if in_year else []
        regular = len(self.weekdays)
        number = self._numbers().get(monday) if in_year else None
        touching = [c for c in self.closures if not (c.ends_on < monday or c.starts_on > sunday)]
        return WeekInfo(
            week_start=monday,
            week_end=sunday,
            iso_year=iso[0],
            iso_week=iso[1],
            in_school_year=in_year,
            teaching_week=number,
            teaching_days=days,
            regular_days=regular,
            shortened=in_year and 0 < len(days) < regular,
            fully_free=in_year and len(days) == 0,
            closures=touching,
        )
