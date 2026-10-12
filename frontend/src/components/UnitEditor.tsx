import { useEffect, useMemo, useState } from "react";
import { ApiError, get, patch, post, del } from "../api";
import { useApp } from "../context";
import type { MaterialSummary, SchoolClass, Unit, Warning } from "../types";
import { addDays, mondayOf, formatDate, STATUS_LABEL } from "../util";
import { Alert, Dialog, Field } from "./ui";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  schoolClass: SchoolClass;
  unit?: Unit | null; // bearbeiten; sonst neu
  defaultWeek?: string;
  defaultSubjectId?: string;
  focus?: "move";
}

interface Draft {
  subject_id: string;
  topic_id: string;
  week: string;
  planned_lessons: number;
  status: Unit["status"];
  notes: string;
  material_ids: string[];
  curriculum_ids: string[];
}

function fromUnit(u: Unit): Draft {
  return {
    subject_id: u.subject_id,
    topic_id: u.topic_id,
    week: u.week_start_date,
    planned_lessons: u.planned_lessons,
    status: u.status,
    notes: u.notes,
    material_ids: u.materials.map((m) => m.id),
    curriculum_ids: u.curriculum.map((c) => c.id),
  };
}

export default function UnitEditor({ open, onClose, onSaved, schoolClass, unit, defaultWeek, defaultSubjectId, focus }: Props) {
  const { reference, toast } = useApp();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [version, setVersion] = useState<number>(0);
  const [warnings, setWarnings] = useState<Warning[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [materials, setMaterials] = useState<MaterialSummary[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (!open || !reference) return;
    setWarnings(null);
    setError(null);
    setFieldErrors({});
    setConflict(false);
    setConfirmDelete(false);
    if (unit) {
      setDraft(fromUnit(unit));
      setVersion(unit.version);
    } else {
      const subject = defaultSubjectId ?? reference.subjects[0]?.id ?? "";
      const topic = reference.topics.find((t) => t.subject_id === subject);
      setDraft({ subject_id: subject, topic_id: topic?.id ?? "", week: defaultWeek ?? mondayOf(new Date().toISOString().slice(0, 10)), planned_lessons: 1, status: "planned", notes: "", material_ids: [], curriculum_ids: [] });
    }
  }, [open, unit, reference, defaultWeek, defaultSubjectId]);

  useEffect(() => {
    if (!open || !draft?.topic_id) return;
    get<{ items: MaterialSummary[] }>("/materials", { topic: draft.topic_id, page_size: 100, sort: "title" })
      .then((r) => setMaterials(r.items))
      .catch(() => setMaterials([]));
  }, [open, draft?.topic_id]);

  const topics = useMemo(() => reference?.topics.filter((t) => t.subject_id === draft?.subject_id) ?? [], [reference, draft?.subject_id]);
  const curriculum = useMemo(() => reference?.curriculum.filter((c) => c.subject_id === draft?.subject_id) ?? [], [reference, draft?.subject_id]);
  const linkedUnavailable = unit?.materials.filter((m) => !materials.some((x) => x.id === m.id)) ?? [];

  if (!draft || !reference) return null;
  const set = (patchObj: Partial<Draft>) => {
    setDraft({ ...draft, ...patchObj });
    setWarnings(null);
  };

  async function save(confirmed: boolean) {
    if (!draft) return;
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      const week = mondayOf(draft.week);
      if (!confirmed) {
        const check = await post<{ warnings: Warning[] }>(`/classes/${schoolClass.id}/units/check`, {
          subject_id: draft.subject_id,
          week_start_date: week,
          planned_lessons: draft.planned_lessons,
          unit_id: unit?.id,
        });
        const relevant = unit && unit.week_start_date === week && unit.planned_lessons >= draft.planned_lessons ? [] : check.warnings;
        if (relevant.length) {
          setWarnings(relevant);
          return;
        }
      }
      if (unit) {
        await patch(`/units/${unit.id}`, {
          version,
          topic_id: draft.topic_id,
          week_start_date: week,
          planned_lessons: draft.planned_lessons,
          status: draft.status,
          notes: draft.notes,
          material_ids: draft.material_ids,
          curriculum_ids: draft.curriculum_ids,
        });
      } else {
        await post(`/classes/${schoolClass.id}/units`, { ...draft, week: undefined, week_start_date: week });
      }
      toast(unit ? "Einheit gespeichert." : "Einheit hinzugefügt.");
      onSaved();
      onClose();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      } else if (e instanceof ApiError) {
        setError(e.message);
        setFieldErrors(e.fieldErrors);
      } else setError("Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function reloadFromServer(keepMine: boolean) {
    if (!unit) return;
    const res = await get<{ items: Unit[] }>(`/classes/${schoolClass.id}/units`, { from: unit.week_start_date, to: addDays(unit.week_start_date, 400) });
    let fresh = res.items.find((u) => u.id === unit.id);
    if (!fresh) {
      const all = await get<{ items: Unit[] }>(`/classes/${schoolClass.id}/units`);
      fresh = all.items.find((u) => u.id === unit.id);
    }
    if (!fresh) {
      setError("Die Einheit wurde inzwischen gelöscht.");
      setConflict(false);
      return;
    }
    setVersion(fresh.version);
    if (!keepMine) setDraft(fromUnit(fresh));
    setConflict(false);
    if (keepMine) toast("Aktuelle Version geladen. Ihre Änderungen bleiben erhalten – bitte erneut speichern.");
  }

  async function remove() {
    if (!unit) return;
    setBusy(true);
    try {
      await del(`/units/${unit.id}`, { version });
      toast("Einheit gelöscht.");
      onSaved();
      onClose();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConflict(true);
      else setError(e instanceof ApiError ? e.message : "Löschen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={unit ? (focus === "move" ? "Einheit verschieben" : "Einheit bearbeiten") : "Einheit hinzufügen"}
      wide
      footer={
        <>
          {unit && !confirmDelete && (
            <button type="button" className="btn btn-danger-ghost" onClick={() => setConfirmDelete(true)} disabled={busy}>
              Löschen
            </button>
          )}
          {confirmDelete && (
            <button type="button" className="btn btn-danger" onClick={remove} disabled={busy}>
              Wirklich löschen
            </button>
          )}
          <span className="spacer" />
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Abbrechen
          </button>
          {warnings ? (
            <button type="button" className="btn btn-primary" onClick={() => save(true)} disabled={busy}>
              Trotzdem speichern
            </button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => save(false)} disabled={busy || !draft.topic_id}>
              {busy ? "Speichert …" : "Speichern"}
            </button>
          )}
        </>
      }
    >
      {conflict && (
        <Alert kind="error">
          <p>
            <strong>Versionskonflikt:</strong> Diese Einheit wurde inzwischen an anderer Stelle geändert. Ihre Änderung wurde nicht gespeichert.
          </p>
          <div className="row">
            <button type="button" className="btn btn-small" onClick={() => reloadFromServer(false)}>
              Neu laden (meine Änderungen verwerfen)
            </button>
            <button type="button" className="btn btn-small btn-primary" onClick={() => reloadFromServer(true)}>
              Meine Änderungen behalten und erneut speichern
            </button>
          </div>
        </Alert>
      )}
      {error && <Alert kind="error">{error}</Alert>}
      {warnings && (
        <Alert kind="warn">
          <ul className="plain">
            {warnings.map((w) => (
              <li key={w.code}>{w.message}</li>
            ))}
          </ul>
          <p>Sie entscheiden, ob trotzdem gespeichert wird.</p>
        </Alert>
      )}
      <div className="form-grid">
        <Field label="Fach" error={fieldErrors.subject_id}>
          <select
            value={draft.subject_id}
            disabled={!!unit}
            onChange={(e) => {
              const t = reference.topics.find((x) => x.subject_id === e.target.value);
              set({ subject_id: e.target.value, topic_id: t?.id ?? "", material_ids: [], curriculum_ids: [] });
            }}
          >
            {reference.subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Thema" error={fieldErrors.topic_id}>
          <select value={draft.topic_id} onChange={(e) => set({ topic_id: e.target.value, material_ids: [] })}>
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Woche (beliebiges Datum der Woche)" hint={`Woche ab Montag, ${formatDate(mondayOf(draft.week))}`} error={fieldErrors.week_start_date}>
          <input type="date" value={draft.week} onChange={(e) => e.target.value && set({ week: e.target.value })} required data-autofocus={focus === "move" ? "" : undefined} />
        </Field>
        <Field label="Unterrichtsstunden (à 45 Min.)" error={fieldErrors.planned_lessons}>
          <input type="number" min={1} max={60} inputMode="numeric" value={draft.planned_lessons} onChange={(e) => set({ planned_lessons: Math.max(1, Number(e.target.value) || 1) })} />
        </Field>
        <Field label="Status">
          <select value={draft.status} onChange={(e) => set({ status: e.target.value as Unit["status"] })}>
            {Object.entries(STATUS_LABEL).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Notizen (z. B. Lehrwerk, Buchstabenfolge)">
        <textarea rows={3} value={draft.notes} onChange={(e) => set({ notes: e.target.value })} maxLength={5000} />
      </Field>
      <fieldset className="fieldset">
        <legend>Verknüpfte Materialien</legend>
        {materials.length === 0 && linkedUnavailable.length === 0 && <p className="muted">Für dieses Thema ist noch kein freigegebenes Material vorhanden.</p>}
        {materials.map((m) => (
          <label key={m.id} className="check">
            <input type="checkbox" checked={draft.material_ids.includes(m.id)} onChange={() => set({ material_ids: toggle(draft.material_ids, m.id) })} />
            <span>
              {m.title} <span className="muted">· {m.type_label}</span>
            </span>
          </label>
        ))}
        {linkedUnavailable.map((m) => (
          <label key={m.id} className="check">
            <input type="checkbox" checked={draft.material_ids.includes(m.id)} onChange={() => set({ material_ids: toggle(draft.material_ids, m.id) })} />
            <span>
              {m.title} <span className="muted">· archiviert, nicht mehr empfohlen</span>
            </span>
          </label>
        ))}
      </fieldset>
      <fieldset className="fieldset">
        <legend>Kompetenzbezüge (LehrplanPLUS, Jgst. 1/2)</legend>
        {curriculum.map((c) => (
          <label key={c.id} className="check">
            <input type="checkbox" checked={draft.curriculum_ids.includes(c.id)} onChange={() => set({ curriculum_ids: toggle(draft.curriculum_ids, c.id) })} />
            <span>
              <strong>{c.section_code}</strong> {c.section_title}
              {c.verification_status !== "verified" && <span className="muted"> · ungeprüft</span>}
            </span>
          </label>
        ))}
      </fieldset>
    </Dialog>
  );
}
