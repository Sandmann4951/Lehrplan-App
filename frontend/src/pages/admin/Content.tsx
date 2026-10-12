import { useEffect, useState } from "react";
import { errorText, get, patch, post } from "../../api";
import { useApp } from "../../context";
import type { Curriculum, Topic } from "../../types";
import { formatDate } from "../../util";
import { Alert, Badge, Dialog, Field } from "../../components/ui";

export function TopicsAdmin() {
  const { reference, reloadReference, toast } = useApp();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [edit, setEdit] = useState<Partial<Topic> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => get<{ items: Topic[] }>("/admin/topics").then((r) => setTopics(r.items));
  useEffect(() => {
    load();
  }, []);

  async function save() {
    if (!edit) return;
    setError(null);
    try {
      const body = { title: edit.title, description: edit.description, sequence: Number(edit.sequence ?? 0), planning_note: edit.planning_note, prerequisite_ids: edit.prerequisite_ids ?? [] };
      if (edit.id) await patch(`/admin/topics/${edit.id}`, { ...body, version: edit.version, archived: edit.archived });
      else await post("/admin/topics", { ...body, subject_id: edit.subject_id, suggested_grade: 1 });
      toast("Thema gespeichert.");
      setEdit(null);
      load();
      reloadReference();
    } catch (e) {
      setError(errorText(e));
    }
  }

  return (
    <div className="stack">
      <Alert kind="info">Themen und Reihenfolge sind eine interne pädagogische Pilotplanung – keine amtlich vorgeschriebene Wochenfolge.</Alert>
      <button type="button" className="btn btn-primary" onClick={() => setEdit({ subject_id: reference?.subjects[0]?.id, title: "", description: "", sequence: 10, planning_note: "", prerequisite_ids: [] })}>
        + Thema anlegen
      </button>
      {reference?.subjects.map((s) => (
        <section key={s.id} className="card">
          <h2>{s.title}</h2>
          <ol className="plain stack-sm">
            {topics
              .filter((t) => t.subject_id === s.id)
              .map((t) => (
                <li key={t.id} className="row-between">
                  <span>
                    <strong>{t.sequence}. {t.title}</strong> {t.archived && <Badge kind="warn">archiviert</Badge>}
                    <br />
                    <span className="small muted">{t.description}</span>
                    {t.planning_note && <><br /><span className="small">Planungsnotiz: {t.planning_note}</span></>}
                  </span>
                  <button type="button" className="btn btn-small" onClick={() => setEdit({ ...t })}>
                    Bearbeiten
                  </button>
                </li>
              ))}
          </ol>
        </section>
      ))}
      <Dialog
        open={!!edit}
        onClose={() => setEdit(null)}
        title={edit?.id ? "Thema bearbeiten" : "Thema anlegen"}
        footer={
          <>
            <span className="spacer" />
            <button type="button" className="btn btn-ghost" onClick={() => setEdit(null)}>Abbrechen</button>
            <button type="button" className="btn btn-primary" onClick={save}>Speichern</button>
          </>
        }
      >
        {edit && (
          <div className="stack">
            {error && <Alert kind="error">{error}</Alert>}
            {!edit.id && (
              <Field label="Fach">
                <select value={edit.subject_id} onChange={(e) => setEdit({ ...edit, subject_id: e.target.value })}>
                  {reference?.subjects.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                </select>
              </Field>
            )}
            <Field label="Titel"><input value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></Field>
            <Field label="Beschreibung"><textarea rows={3} value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></Field>
            <Field label="Reihenfolge"><input type="number" value={edit.sequence} onChange={(e) => setEdit({ ...edit, sequence: Number(e.target.value) })} /></Field>
            <Field label="Planungsnotiz (z. B. Lehrwerk, Buchstabenfolge)"><input value={edit.planning_note} onChange={(e) => setEdit({ ...edit, planning_note: e.target.value })} /></Field>
            <fieldset className="fieldset">
              <legend>Voraussetzungen</legend>
              {topics.filter((t) => t.subject_id === edit.subject_id && t.id !== edit.id).map((t) => (
                <label key={t.id} className="check">
                  <input type="checkbox" checked={(edit.prerequisite_ids ?? []).includes(t.id)} onChange={() => {
                    const cur = edit.prerequisite_ids ?? [];
                    setEdit({ ...edit, prerequisite_ids: cur.includes(t.id) ? cur.filter((x) => x !== t.id) : [...cur, t.id] });
                  }} />
                  <span>{t.title}</span>
                </label>
              ))}
            </fieldset>
            {edit.id && (
              <label className="check">
                <input type="checkbox" checked={!!edit.archived} onChange={(e) => setEdit({ ...edit, archived: e.target.checked })} />
                <span>Archiviert (statt Löschen)</span>
              </label>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
}

export function CurriculumAdmin() {
  const { reference, reloadReference, toast } = useApp();
  const [items, setItems] = useState<Curriculum[]>([]);
  const [edit, setEdit] = useState<Partial<Curriculum> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => get<{ items: Curriculum[] }>("/admin/curriculum").then((r) => setItems(r.items));
  useEffect(() => {
    load();
  }, []);

  async function setStatus(c: Curriculum, status: "verified" | "unverified") {
    try {
      await patch(`/admin/curriculum/${c.id}`, { version: c.version, verification_status: status });
      toast(status === "verified" ? "Als geprüft markiert." : "Prüfung zurückgenommen.");
      load();
      reloadReference();
    } catch (e) {
      toast(errorText(e), "error");
    }
  }

  async function save() {
    if (!edit) return;
    setError(null);
    try {
      if (edit.id) {
        await patch(`/admin/curriculum/${edit.id}`, { version: edit.version, section_title: edit.section_title, paraphrased_goal: edit.paraphrased_goal, source_url: edit.source_url, source_version: edit.source_version, retrieved_on: edit.retrieved_on || null, archived: edit.archived });
      } else {
        await post("/admin/curriculum", { subject_id: edit.subject_id, official_grade_band: edit.official_grade_band || "1/2", section_code: edit.section_code, section_title: edit.section_title, paraphrased_goal: edit.paraphrased_goal, source_url: edit.source_url, source_version: edit.source_version, retrieved_on: edit.retrieved_on || null });
      }
      toast("Lehrplanbezug gespeichert.");
      setEdit(null);
      load();
      reloadReference();
    } catch (e) {
      setError(errorText(e));
    }
  }

  return (
    <div className="stack">
      <Alert kind="info">Offizieller Kompetenzbezug (LehrplanPLUS, Jgst. 1/2 zusammengefasst). Ziele sind sinngemäß formuliert; Quelle und Abrufdatum werden je Bezug gespeichert. Erst „geprüft“ erlaubt die Materialfreigabe.</Alert>
      <button type="button" className="btn btn-primary" onClick={() => setEdit({ subject_id: reference?.subjects[0]?.id, official_grade_band: "1/2", section_code: "", section_title: "", paraphrased_goal: "", source_url: "https://www.lehrplanplus.bayern.de/", source_version: "", retrieved_on: "" })}>
        + Lehrplanbezug anlegen
      </button>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Abschnitt</th><th>Ziel (sinngemäß)</th><th>Quelle</th><th>Status</th><th>Aktionen</th></tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td data-label="Abschnitt"><strong>{c.section_code}</strong><br />{c.section_title}</td>
                <td data-label="Ziel">{c.paraphrased_goal}</td>
                <td data-label="Quelle"><a href={c.source_url} target="_blank" rel="noopener noreferrer">Link</a><br /><span className="small muted">Abruf {c.retrieved_on ? formatDate(c.retrieved_on) : "—"}</span></td>
                <td data-label="Status">{c.verification_status === "verified" ? <Badge kind="ok">✔ geprüft {c.reviewed_at && formatDate(c.reviewed_at)}</Badge> : <Badge kind="warn">⚠ ungeprüft</Badge>}{c.archived && <Badge>archiviert</Badge>}</td>
                <td data-label="Aktionen">
                  <div className="row">
                    {c.verification_status === "verified" ? (
                      <button type="button" className="btn btn-small btn-ghost" onClick={() => setStatus(c, "unverified")}>Prüfung zurücknehmen</button>
                    ) : (
                      <button type="button" className="btn btn-small" onClick={() => setStatus(c, "verified")}>Als geprüft markieren</button>
                    )}
                    <button type="button" className="btn btn-small btn-ghost" onClick={() => setEdit({ ...c, retrieved_on: c.retrieved_on ?? "" })}>Bearbeiten</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Dialog
        open={!!edit}
        onClose={() => setEdit(null)}
        title={edit?.id ? "Lehrplanbezug bearbeiten" : "Lehrplanbezug anlegen"}
        footer={<><span className="spacer" /><button type="button" className="btn btn-ghost" onClick={() => setEdit(null)}>Abbrechen</button><button type="button" className="btn btn-primary" onClick={save}>Speichern</button></>}
      >
        {edit && (
          <div className="stack">
            {error && <Alert kind="error">{error}</Alert>}
            {!edit.id && (
              <div className="form-grid">
                <Field label="Fach">
                  <select value={edit.subject_id} onChange={(e) => setEdit({ ...edit, subject_id: e.target.value })}>
                    {reference?.subjects.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                  </select>
                </Field>
                <Field label="Jahrgangsband"><input value={edit.official_grade_band} onChange={(e) => setEdit({ ...edit, official_grade_band: e.target.value })} /></Field>
                <Field label="Abschnittscode"><input value={edit.section_code} onChange={(e) => setEdit({ ...edit, section_code: e.target.value })} placeholder="z. B. D 1/2 2.1" /></Field>
              </div>
            )}
            <Field label="Abschnittstitel"><input value={edit.section_title} onChange={(e) => setEdit({ ...edit, section_title: e.target.value })} /></Field>
            <Field label="Ziel (sinngemäß, eigene Formulierung)"><textarea rows={3} value={edit.paraphrased_goal} onChange={(e) => setEdit({ ...edit, paraphrased_goal: e.target.value })} /></Field>
            <Field label="Quelle (URL)"><input type="url" value={edit.source_url} onChange={(e) => setEdit({ ...edit, source_url: e.target.value })} /></Field>
            <div className="form-grid">
              <Field label="Quellenversion"><input value={edit.source_version} onChange={(e) => setEdit({ ...edit, source_version: e.target.value })} /></Field>
              <Field label="Abrufdatum"><input type="date" value={edit.retrieved_on ?? ""} onChange={(e) => setEdit({ ...edit, retrieved_on: e.target.value })} /></Field>
            </div>
            {edit.id && (
              <label className="check"><input type="checkbox" checked={!!edit.archived} onChange={(e) => setEdit({ ...edit, archived: e.target.checked })} /><span>Archiviert</span></label>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
}
