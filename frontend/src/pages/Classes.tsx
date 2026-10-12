import { useState, type FormEvent } from "react";
import { ApiError, del, patch, post } from "../api";
import { useApp } from "../context";
import type { SchoolClass } from "../types";
import { WEEKDAYS } from "../util";
import { Alert, Dialog, Field } from "../components/ui";

interface FormState {
  name: string;
  school_year_id: string;
  weekdays: number[];
  hours: Record<string, number>;
}

export default function ClassesPage() {
  const { classes, reference, reloadClasses, setClassId, toast } = useApp();
  const [editing, setEditing] = useState<SchoolClass | "new" | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<SchoolClass | null>(null);

  function open(c: SchoolClass | "new") {
    setErrors({});
    setMessage(null);
    if (c === "new") {
      const hours: Record<string, number> = {};
      reference?.subjects.forEach((s) => (hours[s.id] = s.code === "D" ? 7 : s.code === "M" ? 5 : 2));
      setForm({ name: "", school_year_id: reference?.school_years[0]?.id ?? "", weekdays: [0, 1, 2, 3, 4], hours });
    } else {
      const hours: Record<string, number> = {};
      c.subject_hours.forEach((h) => (hours[h.subject_id] = h.weekly_hours));
      setForm({ name: c.name, school_year_id: c.school_year_id, weekdays: [...c.weekdays], hours });
    }
    setEditing(c);
  }

  async function save(e?: FormEvent) {
    e?.preventDefault();
    if (!form || !editing) return;
    const body = {
      name: form.name,
      school_year_id: form.school_year_id,
      weekdays: form.weekdays,
      subject_hours: Object.entries(form.hours).map(([subject_id, weekly_hours]) => ({ subject_id, weekly_hours })),
    };
    try {
      if (editing === "new") {
        const c = await post<SchoolClass>("/classes", body);
        setClassId(c.id);
        toast("Klasse angelegt.");
      } else {
        await patch(`/classes/${editing.id}`, { ...body, version: editing.version });
        toast("Klasse gespeichert.");
      }
      await reloadClasses();
      setEditing(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        setMessage(err.status === 409 ? "Die Klasse wurde inzwischen geändert. Bitte Dialog schließen und erneut öffnen." : err.message);
      }
    }
  }

  async function remove() {
    if (!deleting) return;
    try {
      await del(`/classes/${deleting.id}`);
      toast("Klasse gelöscht.");
      setDeleting(null);
      await reloadClasses();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.", "error");
    }
  }

  return (
    <section className="page">
      <div className="page-head">
        <h1>Meine Klassen</h1>
        <button type="button" className="btn btn-primary" onClick={() => open("new")}>
          + Klasse anlegen
        </button>
      </div>
      {classes.length === 0 && <Alert kind="info">Legen Sie Ihre erste Klasse an, um mit der Wochenplanung zu beginnen.</Alert>}
      <div className="cards">
        {classes.map((c) => (
          <article key={c.id} className="card">
            <h2>{c.name}</h2>
            <p className="muted">
              Schuljahr {c.school_year_label} · Jahrgangsstufe {c.grade} · Bayern · Grundschule
            </p>
            <p className="small">Unterrichtstage: {c.weekdays.map((d) => WEEKDAYS[d].slice(0, 2)).join(", ")}</p>
            <p className="small">
              Wochenstunden: {c.subject_hours.map((h) => `${reference?.subjects.find((s) => s.id === h.subject_id)?.title ?? "?"} ${h.weekly_hours}`).join(" · ")}
            </p>
            <div className="row">
              <button type="button" className="btn btn-small" onClick={() => open(c)}>
                Bearbeiten
              </button>
              <button type="button" className="btn btn-small btn-danger-ghost" onClick={() => setDeleting(c)}>
                Löschen
              </button>
            </div>
          </article>
        ))}
      </div>

      <Dialog
        open={!!editing && !!form}
        onClose={() => setEditing(null)}
        title={editing === "new" ? "Klasse anlegen" : "Klasse bearbeiten"}
        footer={
          <>
            <span className="spacer" />
            <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>
              Abbrechen
            </button>
            <button type="button" className="btn btn-primary" onClick={() => save()} disabled={!form?.name || !form?.weekdays.length}>
              Speichern
            </button>
          </>
        }
      >
        {form && (
          <form onSubmit={save} className="stack">
            {message && <Alert kind="error">{message}</Alert>}
            <Field label="Name der Klasse" error={errors.name}>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={100} placeholder="z. B. 1a" />
            </Field>
            <Field label="Schuljahr" error={errors.school_year_id}>
              <select value={form.school_year_id} onChange={(e) => setForm({ ...form, school_year_id: e.target.value })}>
                {reference?.school_years.map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.label}
                  </option>
                ))}
              </select>
            </Field>
            <p className="muted small">Im Pilot fest: Jahrgangsstufe 1 · Bayern · Grundschule</p>
            <fieldset className="fieldset">
              <legend>Unterrichtswochentage</legend>
              <div className="chips">
                {WEEKDAYS.slice(0, 6).map((d, i) => (
                  <label key={d} className="check chip">
                    <input
                      type="checkbox"
                      checked={form.weekdays.includes(i)}
                      onChange={() => setForm({ ...form, weekdays: form.weekdays.includes(i) ? form.weekdays.filter((x) => x !== i) : [...form.weekdays, i].sort() })}
                    />
                    <span>{d}</span>
                  </label>
                ))}
              </div>
              {(errors.weekdays || form.weekdays.length === 0) && <p className="field-msg">⚠ Mindestens ein Wochentag ist erforderlich.</p>}
            </fieldset>
            <fieldset className="fieldset">
              <legend>Wochenstunden je Fach</legend>
              <div className="form-grid">
                {reference?.subjects.map((s) => (
                  <Field key={s.id} label={s.title}>
                    <input type="number" min={0} max={20} inputMode="numeric" value={form.hours[s.id] ?? 0} onChange={(e) => setForm({ ...form, hours: { ...form.hours, [s.id]: Math.max(0, Number(e.target.value) || 0) } })} />
                  </Field>
                ))}
              </div>
            </fieldset>
          </form>
        )}
      </Dialog>

      <Dialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Klasse löschen?"
        footer={
          <>
            <span className="spacer" />
            <button type="button" className="btn btn-ghost" onClick={() => setDeleting(null)}>
              Abbrechen
            </button>
            <button type="button" className="btn btn-danger" onClick={remove}>
              Endgültig löschen
            </button>
          </>
        }
      >
        <p>
          Die Klasse <strong>{deleting?.name}</strong> und alle ihre geplanten Einheiten werden gelöscht. Materialien der Bibliothek bleiben erhalten.
        </p>
      </Dialog>
    </section>
  );
}
