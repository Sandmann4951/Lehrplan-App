"""Idempotenter Seed: legt nur fehlende Datensätze an (stabile IDs).

Ein zweiter Lauf erzeugt keine Duplikate und überschreibt keine
Änderungen der Administration.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ..models import (
    CalendarClosure,
    CurriculumReference,
    Material,
    MaterialFile,
    PlanTemplate,
    SchoolYear,
    Subject,
    TemplateUnit,
    Topic,
)
from ..services.library import write_blob
from . import data as d

PDF_DIR = Path(__file__).resolve().parent / "pdfs"


def load_seed(db: Session) -> dict[str, int]:
    created = {"subjects": 0, "topics": 0, "curriculum": 0, "school_years": 0, "closures": 0, "materials": 0, "files": 0, "templates": 0}

    subjects: dict[str, Subject] = {}
    for s in d.SUBJECTS:
        obj = db.get(Subject, s["id"])
        if obj is None:
            obj = Subject(**s)
            db.add(obj)
            created["subjects"] += 1
        subjects[s["code"]] = obj
    db.flush()

    curriculum: dict[str, CurriculumReference] = {}
    for c in d.CURRICULUM:
        cid = d.sid(f"curriculum:{c['key']}")
        obj = db.get(CurriculumReference, cid)
        if obj is None:
            obj = CurriculumReference(
                id=cid,
                subject_id=subjects[c["subject"]].id,
                official_grade_band="1/2",
                section_code=c["code"],
                section_title=c["title"],
                paraphrased_goal=c["goal"],
                source_url=c["url"],
                source_version="LehrplanPLUS Grundschule, Fachlehrplan 1/2 (Abruf)",
                retrieved_on=d.RETRIEVED,
                verification_status="unverified",
            )
            db.add(obj)
            created["curriculum"] += 1
        curriculum[c["key"]] = obj
    db.flush()

    topics: dict[str, Topic] = {}
    for t in d.TOPICS:
        tid = d.sid(f"topic:{t['key']}")
        obj = db.get(Topic, tid)
        if obj is None:
            obj = Topic(
                id=tid,
                subject_id=subjects[t["subject"]].id,
                title=t["title"],
                description=t["description"],
                suggested_grade=1,
                sequence=t["sequence"],
                planning_note=d.PLANNING_NOTE_D if t["subject"] == "D" else "",
            )
            db.add(obj)
            created["topics"] += 1
        topics[t["key"]] = obj
    db.flush()
    for t in d.TOPICS:
        obj = topics[t["key"]]
        if not obj.prerequisites and t["prereq"]:
            obj.prerequisites = [topics[k] for k in t["prereq"]]

    year = db.get(SchoolYear, d.SCHOOL_YEAR["id"])
    if year is None:
        year = SchoolYear(**d.SCHOOL_YEAR)
        db.add(year)
        created["school_years"] += 1
        db.flush()
    for title, start, end, kind in d.CLOSURES:
        cid = d.sid(f"closure:{year.label}:{title}")
        if db.get(CalendarClosure, cid) is None:
            db.add(CalendarClosure(id=cid, school_year_id=year.id, title=title, starts_on=start, ends_on=end, kind=kind, source=d._SRC, review_status="unreviewed"))
            created["closures"] += 1

    materials: dict[str, Material] = {}
    for m in d.MATERIALS:
        mid = d.sid(f"material:{m['key']}")
        obj = db.get(Material, mid)
        if obj is None:
            obj = Material(
                id=mid,
                topic_id=topics[m["topic"]].id,
                title=m["title"],
                description=m["description"],
                learning_goal=m["goal"],
                keywords=m["keywords"],
                type=m["type"],
                level=m["level"],
                duration_minutes=m["duration"],
                author=d.AUTHOR,
                license_text=d.LICENSE,
                # Technische Demo-Freigabe: sichtbar für die technische Abnahme,
                # aber ausdrücklich als nicht fachlich geprüft gekennzeichnet.
                status="released",
                is_demo=True,
                review_note="Demonstrationsmaterial für die technische Abnahme – keine fachliche Prüfung erfolgt.",
                curriculum=[curriculum[k] for k in m["curriculum"]],
            )
            db.add(obj)
            created["materials"] += 1
            for purpose, name in (("main", m["main"]), ("solution", m["solution"])):
                if not name:
                    continue
                data = (PDF_DIR / name).read_bytes()
                key, digest = write_blob(data)
                obj.files.append(MaterialFile(purpose=purpose, original_name=name, storage_key=key, mime_type="application/pdf", size_bytes=len(data), sha256=digest))
                created["files"] += 1
        materials[m["key"]] = obj
    db.flush()

    lessons = {t["key"]: t["lessons"] for t in d.TOPICS}
    by_topic = {m["topic"]: materials[m["key"]] for m in d.MATERIALS}
    for tpl in d.TEMPLATES:
        tid = d.sid(tpl["key"])
        if db.get(PlanTemplate, tid) is None:
            obj = PlanTemplate(id=tid, name=tpl["name"], subject_id=subjects[tpl["subject"]].id, grade=1)
            for i, key in enumerate(tpl["topics"], start=1):
                obj.units.append(
                    TemplateUnit(
                        id=d.sid(f"{tpl['key']}:unit:{key}"),
                        topic_id=topics[key].id,
                        sequence=i,
                        estimated_lessons=lessons[key],
                        materials=[by_topic[key]] if key in by_topic else [],
                        curriculum=[curriculum[c] for c in d.TOPIC_CURRICULUM.get(key, [])],
                    )
                )
            db.add(obj)
            created["templates"] += 1
    db.commit()
    return created
