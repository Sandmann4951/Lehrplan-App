import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { errorText, get } from "../api";
import { useApp } from "../context";
import type { CalendarStatus, Unit, Week } from "../types";
import { mondayOf, todayBerlin } from "../util";
import { Alert, Spinner } from "../components/ui";
import { ClassPicker, NoClass, StatusBadge, WeekHeader } from "../components/plan";
import UnitEditor from "../components/UnitEditor";
import InitPlanDialog from "../components/InitPlanDialog";

export default function PlanPage() {
  const { classes, classId, reference } = useApp();
  const [params] = useSearchParams();
  const focusWeek = params.get("woche") ?? mondayOf(todayBerlin());
  const [weeks, setWeeks] = useState<Week[] | null>(null);
  const [calendar, setCalendar] = useState<CalendarStatus | undefined>();
  const [units, setUnits] = useState<Unit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ unit: Unit | null; week?: string; subjectId?: string; focus?: "move" } | null>(null);
  const [initOpen, setInitOpen] = useState(false);
  const [onlyTeaching, setOnlyTeaching] = useState(false);
  const scrolled = useRef(false);
  const schoolClass = classes.find((c) => c.id === classId) ?? null;

  const load = useCallback(async () => {
    if (!classId) return;
    try {
      const [w, u] = await Promise.all([get<{ items: Week[]; calendar_status: CalendarStatus }>(`/classes/${classId}/weeks`), get<{ items: Unit[] }>(`/classes/${classId}/units`)]);
      setWeeks(w.items);
      setCalendar(w.calendar_status);
      setUnits(u.items);
      setError(null);
    } catch (e) {
      setError(errorText(e));
    }
  }, [classId]);

  useEffect(() => {
    scrolled.current = false;
    load();
  }, [load]);

  useEffect(() => {
    if (!weeks || scrolled.current) return;
    const el = document.getElementById(`w-${focusWeek}`);
    if (el) {
      el.scrollIntoView({ block: "start" });
      scrolled.current = true;
    }
  }, [weeks, focusWeek]);

  const byWeek = useMemo(() => {
    const map = new Map<string, Unit[]>();
    units.forEach((u) => map.set(u.week_start_date, [...(map.get(u.week_start_date) ?? []), u]));
    return map;
  }, [units]);

  if (!classes.length) return <section className="page"><h1>Wochenplan</h1><NoClass /></section>;

  const outside = units.filter((u) => weeks && !weeks.some((w) => w.week_start === u.week_start_date));

  return (
    <section className="page">
      <div className="page-head">
        <h1>Wochenplan{schoolClass ? ` · ${schoolClass.name}` : ""}</h1>
        <ClassPicker />
      </div>
      <div className="toolbar">
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ unit: null, week: focusWeek })}>
          + Einheit hinzufügen
        </button>
        <button type="button" className="btn" onClick={() => setInitOpen(true)}>
          Plan aus Vorlage …
        </button>
        <label className="check inline">
          <input type="checkbox" checked={onlyTeaching} onChange={(e) => setOnlyTeaching(e.target.checked)} />
          <span>Nur Wochen mit Einheiten</span>
        </label>
      </div>
      {error && <Alert kind="error">{error}</Alert>}
      {calendar?.demo_only && <Alert kind="warn">Die Ferien- und Feiertagsdaten sind noch nicht von der Administration geprüft. Vor dem echten Unterrichtseinsatz bitte freigeben lassen.</Alert>}
      {!weeks ? (
        <Spinner />
      ) : (
        <ol className="weeklist">
          {weeks
            .filter((w) => !onlyTeaching || byWeek.has(w.week_start))
            .map((w) => {
              const wu = byWeek.get(w.week_start) ?? [];
              return (
                <li key={w.week_start} id={`w-${w.week_start}`} className={w.week_start === mondayOf(todayBerlin()) ? "week current" : w.fully_free ? "week free" : "week"}>
                  <WeekHeader week={w} />
                  {wu.length > 0 && (
                    <ul className="week-units">
                      {wu.map((u) => (
                        <li key={u.id} className="week-unit">
                          <div className="week-unit-main">
                            <span className="muted small">{u.subject_title}</span>
                            <span className="week-unit-title">{u.topic_title}</span>
                            <span className="small">
                              {u.planned_lessons} Std. · <StatusBadge status={u.status} />
                              {u.materials.length === 0 && <span className="warn-text"> · kein Material</span>}
                            </span>
                          </div>
                          <div className="week-unit-actions">
                            <button type="button" className="btn btn-small" onClick={() => setEditing({ unit: u, focus: "move" })} aria-label={`${u.topic_title} verschieben`}>
                              Verschieben
                            </button>
                            <button type="button" className="btn btn-small btn-ghost" onClick={() => setEditing({ unit: u })} aria-label={`${u.topic_title} bearbeiten`}>
                              Bearbeiten
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                  {reference && !w.fully_free && w.in_school_year && (
                    <p className="small muted cap-line">
                      {reference.subjects
                        .map((s) => {
                          const planned = wu.filter((u) => u.subject_id === s.id).reduce((a, u) => a + u.planned_lessons, 0);
                          const cap = w.capacity[s.id] ?? 0;
                          return `${s.title}: ${planned}/${cap}${planned > cap ? " ⚠" : ""}`;
                        })
                        .join(" · ")}
                      <button type="button" className="btn-link" onClick={() => setEditing({ unit: null, week: w.week_start })}>
                        + Einheit in dieser Woche
                      </button>
                    </p>
                  )}
                </li>
              );
            })}
        </ol>
      )}
      {outside.length > 0 && <Alert kind="warn">{outside.length} Einheit(en) liegen außerhalb des Schuljahrs.</Alert>}
      {schoolClass && editing && (
        <UnitEditor open onClose={() => setEditing(null)} onSaved={load} schoolClass={schoolClass} unit={editing.unit} defaultWeek={editing.week} focus={editing.focus} />
      )}
      {schoolClass && <InitPlanDialog open={initOpen} onClose={() => setInitOpen(false)} onDone={load} schoolClass={schoolClass} hasUnits={units.length > 0} />}
    </section>
  );
}
