"""Empfehlungsservice (F07) – nachvollziehbar, deterministisch, ohne KI.

Punkte je Material:
  100  Material gehört zu einem in der Woche geplanten Thema (Voraussetzung)
  +20  mindestens ein gemeinsamer Kompetenzbezug mit der geplanten Einheit
   +5  Niveau entspricht dem gewählten Niveau
Gleichstand: Titel, dann ID. Höchstens fünf Vorschläge pro Fach.
Eine Kalenderwoche allein bestimmt niemals ein Thema.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Material, PlanUnit, SchoolClass, Subject, Topic, material_curriculum
from ..serializers import LEVEL_LABELS, material_summary
from .calendar import week_start

SCORE_TOPIC = 100
SCORE_COMPETENCY = 20
SCORE_LEVEL = 5
MAX_PER_SUBJECT = 5


def _candidates(db: Session, topic_id: str, grade: int) -> list[tuple[str, str, str]]:
    """Leichte Kandidatenliste (id, title, level) – vermeidet ORM-Laden aller Materialien."""
    rows = db.execute(
        select(Material.id, Material.title, Material.level)
        .join(Topic, Topic.id == Material.topic_id)
        .where(Material.topic_id == topic_id, Material.status == "released", Topic.suggested_grade == grade)
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]


def _score(db: Session, candidates: list[tuple[str, str, str]], unit_competencies: set[str], level: str | None, topic_title: str) -> list[dict]:
    shared_by_material: dict[str, set[str]] = {}
    if unit_competencies and candidates:
        links = db.execute(
            select(material_curriculum.c.material_id, material_curriculum.c.curriculum_id).where(
                material_curriculum.c.material_id.in_([c[0] for c in candidates]),
                material_curriculum.c.curriculum_id.in_(list(unit_competencies)),
            )
        ).all()
        for mid, cid in links:
            shared_by_material.setdefault(mid, set()).add(cid)
    scored = []
    for mid, title, mlevel in candidates:
        score = SCORE_TOPIC
        reasons = [f"Thema „{topic_title}“ ist eingeplant (+{SCORE_TOPIC})"]
        shared = shared_by_material.get(mid)
        if shared:
            score += SCORE_COMPETENCY
            reasons.append(("gemeinsamer Kompetenzbezug", shared))
        if level and mlevel == level:
            score += SCORE_LEVEL
            reasons.append(f"Niveau {LEVEL_LABELS.get(level, level)} (+{SCORE_LEVEL})")
        scored.append((score, title.lower(), mid, reasons))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    top = scored[:MAX_PER_SUBJECT]
    if not top:
        return []
    objs = {
        m.id: m
        for m in db.scalars(
            select(Material).where(Material.id.in_([t[2] for t in top])).options(selectinload(Material.curriculum), selectinload(Material.files), selectinload(Material.topic))
        ).all()
    }
    result = []
    for score, _, mid, reasons in top:
        m = objs[mid]
        text = []
        for r in reasons:
            if isinstance(r, tuple):
                codes = sorted(c.section_code for c in m.curriculum if c.id in r[1])
                text.append(f"gemeinsamer Kompetenzbezug {', '.join(codes)} (+{SCORE_COMPETENCY})")
            else:
                text.append(r)
        result.append({"score": score, "reason": "; ".join(text), "material": material_summary(m)})
    return result


def recommend(db: Session, cls: SchoolClass, week: date, level: str | None, favorite_ids: set[str]) -> dict:
    monday = week_start(week)
    units = list(
        db.scalars(
            select(PlanUnit)
            .where(PlanUnit.class_id == cls.id)
            .options(selectinload(PlanUnit.curriculum), selectinload(PlanUnit.topic))
            .order_by(PlanUnit.week_start_date, PlanUnit.sequence, PlanUnit.id)
        ).all()
    )
    subjects = db.scalars(select(Subject).order_by(Subject.sort_order, Subject.title)).all()
    result = []
    for subject in subjects:
        week_units = [u for u in units if u.subject_id == subject.id and u.week_start_date == monday]
        entry: dict = {"subject_id": subject.id, "subject_title": subject.title, "mode": "planned", "topics": [], "items": []}
        if week_units:
            topic_order: list[str] = []
            competencies: dict[str, set[str]] = {}
            titles: dict[str, str] = {}
            for u in week_units:
                if u.topic_id not in competencies:
                    topic_order.append(u.topic_id)
                    competencies[u.topic_id] = set()
                    titles[u.topic_id] = u.topic.title
                competencies[u.topic_id].update(c.id for c in u.curriculum)
            all_items: list[dict] = []
            for tid in topic_order:
                all_items.extend(_score(db, _candidates(db, tid, cls.grade), competencies[tid], level, titles[tid]))
            all_items.sort(key=lambda x: (-x["score"], x["material"]["title"].lower(), x["material"]["id"]))
            entry["topics"] = [{"id": t, "title": titles[t]} for t in topic_order]
            entry["items"] = all_items[:MAX_PER_SUBJECT]
        else:
            # Nächstes offenes Thema aus dem persönlichen Plan als gekennzeichneter Vorschlag
            open_units = [u for u in units if u.subject_id == subject.id and u.status != "completed"]
            upcoming = [u for u in open_units if u.week_start_date > monday]
            candidate = upcoming[0] if upcoming else (open_units[0] if open_units else None)
            if candidate is not None:
                entry["mode"] = "next_open_topic"
                entry["topics"] = [{"id": candidate.topic_id, "title": candidate.topic.title, "planned_week": candidate.week_start_date.isoformat()}]
                comps = {c.id for c in candidate.curriculum}
                entry["items"] = _score(db, _candidates(db, candidate.topic_id, cls.grade), comps, level, candidate.topic.title)
                for item in entry["items"]:
                    item["reason"] = "Vorschlag: nächstes offenes Thema im Plan (nicht eingeplant). " + item["reason"]
            else:
                entry["mode"] = "empty"
        for item in entry["items"]:
            item["material"]["is_favorite"] = item["material"]["id"] in favorite_ids
        if entry["mode"] != "empty" and not entry["items"]:
            entry["empty_reason"] = "Für das Thema ist noch kein freigegebenes Material vorhanden."
        elif entry["mode"] == "empty":
            entry["empty_reason"] = "Für dieses Fach ist in Ihrem Plan keine offene Einheit vorhanden."
        result.append(entry)
    return {"week_start": monday.isoformat(), "level": level, "subjects": result}
