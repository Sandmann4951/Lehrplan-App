import { Link } from "react-router-dom";
import { ApiError, patch } from "../api";
import { useApp } from "../context";
import type { CalendarStatus, Unit, Week } from "../types";
import { addDays, formatRange, mondayOf, STATUS_ICON, STATUS_LABEL, todayBerlin } from "../util";
import { Alert, Badge } from "./ui";

export function ClassPicker() {
  const { classes, classId, setClassId } = useApp();
  if (classes.length <= 1) return null;
  return (
    <label className="inline-field">
      <span>Klasse</span>
      <select value={classId ?? ""} onChange={(e) => setClassId(e.target.value)}>
        {classes.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({c.school_year_label})
          </option>
        ))}
      </select>
    </label>
  );
}

export function WeekNav({ week, onChange }: { week: string; onChange: (w: string) => void }) {
  return (
    <div className="weeknav" role="group" aria-label="Woche wählen">
      <button type="button" className="btn" onClick={() => onChange(addDays(week, -7))} aria-label="Vorherige Woche">
        ‹ <span className="hide-sm">Vorwoche</span>
      </button>
      <label className="sr-only" htmlFor="weekdate">
        Datum innerhalb der Woche
      </label>
      <input id="weekdate" type="date" value={week} onChange={(e) => e.target.value && onChange(mondayOf(e.target.value))} />
      <button type="button" className="btn" onClick={() => onChange(addDays(week, 7))} aria-label="Nächste Woche">
        <span className="hide-sm">Nächste</span> ›
      </button>
      <button type="button" className="btn btn-ghost" onClick={() => onChange(mondayOf(todayBerlin()))}>
        Heute
      </button>
    </div>
  );
}

export function WeekHeader({ week, calendar }: { week: Week; calendar?: CalendarStatus }) {
  return (
    <div className="weekhead">
      <div className="weekhead-main">
        <span className="kw">KW {week.iso_week}</span>
        <span>{formatRange(week.week_start, week.week_end)}</span>
        {week.teaching_week ? <Badge kind="info">Unterrichtswoche {week.teaching_week}</Badge> : null}
        {!week.in_school_year && <Badge>außerhalb des Schuljahrs</Badge>}
        {week.fully_free && <Badge kind="warn">unterrichtsfrei</Badge>}
        {week.shortened && (
          <Badge kind="warn" title="Wochenkapazität wird anteilig gekürzt">
            verkürzt · {week.teaching_days.length} von {week.regular_days} Tagen
          </Badge>
        )}
      </div>
      {week.closures.length > 0 && (
        <p className="muted small">
          {week.closures.map((c) => c.title + (c.approved ? "" : " (ungeprüft)")).join(", ")}
        </p>
      )}
      {calendar?.demo_only && (
        <p className="small warn-text">⚠ Kalenderdaten noch nicht freigegeben – nur zur Demonstration verwenden.</p>
      )}
    </div>
  );
}

export function StatusBadge({ status }: { status: Unit["status"] }) {
  return (
    <span className={`status status-${status}`}>
      <span aria-hidden="true">{STATUS_ICON[status]}</span> {STATUS_LABEL[status]}
    </span>
  );
}

export function UnitCard({ unit, onEdit, onMove, onChanged }: { unit: Unit; onEdit: () => void; onMove: () => void; onChanged: () => void }) {
  const { toast } = useApp();
  async function setStatus(status: Unit["status"]) {
    try {
      await patch(`/units/${unit.id}`, { version: unit.version, status });
      toast(status === "completed" ? "Einheit als abgeschlossen markiert." : "Status gespeichert.");
      onChanged();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        toast("Die Einheit wurde inzwischen geändert. Bitte neu laden und erneut versuchen.", "error");
        onChanged();
      } else toast(e instanceof ApiError ? e.message : "Speichern fehlgeschlagen.", "error");
    }
  }
  return (
    <article className="unit">
      <div className="unit-head">
        <div>
          <p className="unit-subject">{unit.subject_title}</p>
          <h3 className="unit-title">{unit.topic_title}</h3>
        </div>
        <StatusBadge status={unit.status} />
      </div>
      <p className="muted small">
        {unit.planned_lessons} {unit.planned_lessons === 1 ? "Stunde" : "Stunden"}
        {unit.curriculum.length > 0 && <> · Kompetenzbezug: {unit.curriculum.map((c) => c.section_code).join(", ")}</>}
      </p>
      {unit.notes && <p className="unit-notes">{unit.notes}</p>}
      {unit.materials.length > 0 ? (
        <ul className="unit-materials">
          {unit.materials.map((m) => (
            <li key={m.id}>
              {m.available ? <Link to={`/material/${m.id}`}>{m.title}</Link> : <span>{m.title}</span>}
              <span className="muted small"> · {m.type_label}</span>
              {m.status === "archived" && <span className="muted small"> · archiviert</span>}
              {!m.has_main_file && <span className="warn-text small"> · Datei fehlt</span>}
            </li>
          ))}
        </ul>
      ) : (
        <p className="small warn-text">⚠ Noch kein Material verknüpft.</p>
      )}
      <div className="unit-actions">
        {unit.status === "planned" && (
          <button type="button" className="btn btn-small" onClick={() => setStatus("started")}>
            Begonnen
          </button>
        )}
        {unit.status !== "completed" ? (
          <button type="button" className="btn btn-small btn-primary" onClick={() => setStatus("completed")}>
            ✔ Abschließen
          </button>
        ) : (
          <button type="button" className="btn btn-small" onClick={() => setStatus("started")}>
            Wieder öffnen
          </button>
        )}
        <button type="button" className="btn btn-small" onClick={onMove}>
          Verschieben
        </button>
        <button type="button" className="btn btn-small btn-ghost" onClick={onEdit}>
          Bearbeiten
        </button>
      </div>
    </article>
  );
}

export function NoClass() {
  return (
    <Alert kind="info">
      <p>Sie haben noch keine Klasse angelegt.</p>
      <Link className="btn btn-primary" to="/klassen">
        Klasse anlegen
      </Link>
    </Alert>
  );
}
