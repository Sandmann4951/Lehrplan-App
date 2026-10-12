import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { errorText, get } from "../api";
import { useApp } from "../context";
import type { CalendarStatus, SchoolClass, SubjectRecommendations, Unit, Week } from "../types";
import { formatDate, mondayOf, todayBerlin } from "../util";
import { Alert, Empty, Spinner } from "../components/ui";
import { ClassPicker, NoClass, UnitCard, WeekHeader, WeekNav } from "../components/plan";
import UnitEditor from "../components/UnitEditor";
import MaterialCard from "../components/MaterialCard";
import InitPlanDialog from "../components/InitPlanDialog";

interface DashboardData {
  class: SchoolClass;
  week: Week;
  units: Unit[];
  recommendations: { week_start: string; level: string | null; subjects: SubjectRecommendations[] };
  calendar_status: CalendarStatus;
}

export default function DashboardPage() {
  const { user, classes, classId, reference } = useApp();
  const [params, setParams] = useSearchParams();
  const week = params.get("woche") ?? mondayOf(todayBerlin());
  const level = params.get("niveau") ?? "";
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ unit: Unit | null; focus?: "move"; subjectId?: string } | null>(null);
  const [initOpen, setInitOpen] = useState(false);
  const [hasAnyUnits, setHasAnyUnits] = useState(true);

  const load = useCallback(async () => {
    if (!classId) return;
    setError(null);
    try {
      const d = await get<DashboardData>(`/classes/${classId}/dashboard`, { week, level: level || undefined });
      setData(d);
      const all = await get<{ total: number }>(`/classes/${classId}/units`);
      setHasAnyUnits(all.total > 0);
    } catch (e) {
      setError(errorText(e));
    }
  }, [classId, week, level]);

  useEffect(() => {
    load();
  }, [load]);

  const setWeek = (w: string) => setParams((p) => { p.set("woche", w); return p; });
  const setLevel = (l: string) => setParams((p) => { if (l) p.set("niveau", l); else p.delete("niveau"); return p; });

  const updateFavorite = (id: string, fav: boolean) =>
    setData((d) => d && { ...d, recommendations: { ...d.recommendations, subjects: d.recommendations.subjects.map((s) => ({ ...s, items: s.items.map((i) => (i.material.id === id ? { ...i, material: { ...i.material, is_favorite: fav } } : i)) })) } });

  if (!classes.length) {
    return (
      <section className="page">
        <h1>Guten Tag, {user?.display_name}</h1>
        <NoClass />
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-head">
        <h1>Übersicht{data ? ` · ${data.class.name}` : ""}</h1>
        <ClassPicker />
      </div>
      <WeekNav week={week} onChange={setWeek} />
      {error && <Alert kind="error">{error}</Alert>}
      {!data ? (
        <Spinner />
      ) : (
        <>
          <WeekHeader week={data.week} calendar={data.calendar_status} />
          {!hasAnyUnits && (
            <Alert kind="info">
              <p>Ihr Plan ist noch leer. Legen Sie ihn aus der Pilotvorlage an oder fügen Sie Einheiten selbst hinzu.</p>
              <button type="button" className="btn btn-primary" onClick={() => setInitOpen(true)}>
                Plan aus Vorlage anlegen
              </button>
            </Alert>
          )}

          <div className="dash-grid">
            <section aria-labelledby="h-units">
              <div className="section-head">
                <h2 id="h-units">Geplante Einheiten</h2>
                <button type="button" className="btn btn-small" onClick={() => setEditing({ unit: null })}>
                  + Einheit
                </button>
              </div>
              {data.units.length === 0 ? (
                <Empty title={data.week.fully_free ? "Unterrichtsfreie Woche." : "In dieser Woche ist nichts geplant."}>
                  <Link to={`/plan?woche=${week}`}>Zum Wochenplan</Link>
                </Empty>
              ) : (
                <div className="stack">
                  {data.units.map((u) => (
                    <UnitCard key={u.id} unit={u} onChanged={load} onEdit={() => setEditing({ unit: u })} onMove={() => setEditing({ unit: u, focus: "move" })} />
                  ))}
                </div>
              )}
              {reference && data.units.length > 0 && (
                <p className="muted small">
                  Kapazität dieser Woche:{" "}
                  {reference.subjects
                    .map((s) => {
                      const planned = data.units.filter((u) => u.subject_id === s.id).reduce((a, u) => a + u.planned_lessons, 0);
                      const cap = data.week.capacity[s.id] ?? 0;
                      return `${s.title} ${planned}/${cap} Std.${planned > cap ? " ⚠ überplant" : ""}`;
                    })
                    .join(" · ")}
                </p>
              )}
            </section>

            <section aria-labelledby="h-rec">
              <div className="section-head">
                <h2 id="h-rec">Passende Materialien</h2>
                <label className="inline-field">
                  <span>Niveau</span>
                  <select value={level} onChange={(e) => setLevel(e.target.value)}>
                    <option value="">beliebig</option>
                    {reference?.levels.map((l) => (
                      <option key={l.value} value={l.value}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {data.recommendations.subjects.map((s) => (
                <div key={s.subject_id} className="rec-subject">
                  <h3>{s.subject_title}</h3>
                  {s.mode === "next_open_topic" && s.topics[0] && (
                    <Alert kind="info">
                      Vorschlag: In dieser Woche ist kein {s.subject_title}-Thema eingeplant. Nächstes offenes Thema im Plan: <strong>{s.topics[0].title}</strong>
                      {s.topics[0].planned_week && <> (geplant ab {formatDate(s.topics[0].planned_week)})</>}. Es wird nicht automatisch eingeplant.
                    </Alert>
                  )}
                  {s.items.length === 0 ? (
                    <Empty title={s.empty_reason ?? "Keine Vorschläge."}>
                      <Link to={`/bibliothek?subject=${s.subject_id}`}>In der Bibliothek suchen</Link>
                    </Empty>
                  ) : (
                    <div className="stack">
                      {s.items.map((i) => (
                        <MaterialCard key={i.material.id} m={i.material} reason={`${i.reason} = ${i.score} Punkte`} onFavorite={(f) => updateFavorite(i.material.id, f)} />
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </section>
          </div>

          {editing && (
            <UnitEditor
              open
              onClose={() => setEditing(null)}
              onSaved={load}
              schoolClass={data.class}
              unit={editing.unit}
              focus={editing.focus}
              defaultWeek={week}
            />
          )}
          <InitPlanDialog open={initOpen} onClose={() => setInitOpen(false)} onDone={load} schoolClass={data.class} hasUnits={hasAnyUnits} />
        </>
      )}
    </section>
  );
}
