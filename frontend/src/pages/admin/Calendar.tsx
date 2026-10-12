import { useEffect, useState } from "react";
import { ApiError, del, errorText, get, patch, post } from "../../api";
import { useApp } from "../../context";
import type { CalendarStatus, SchoolYear } from "../../types";
import { formatDate, todayBerlin } from "../../util";
import { Alert, Badge, Dialog, Field } from "../../components/ui";

interface Closure {
  id: string;
  school_year_id: string;
  title: string;
  starts_on: string;
  ends_on: string;
  kind: string;
  source: string;
  reviewed_at: string | null;
  review_status: "unreviewed" | "approved";
  version: number;
}
type YearData = SchoolYear & { closures: Closure[]; status: CalendarStatus };

const KINDS: Record<string, string> = { holiday: "Ferien", public_holiday: "Feiertag", school_free: "Schulfrei", special: "Sondertag" };

const EXAMPLE = `{
  "school_year": {"label": "2026/2027", "starts_on": "2026-09-15", "ends_on": "2027-07-30"},
  "source": "https://www.km.bayern.de/…",
  "review_status": "unreviewed",
  "replace": false,
  "closures": [
    {"title": "Herbstferien", "starts_on": "2026-11-02", "ends_on": "2026-11-06", "kind": "holiday"}
  ]
}`;

export default function CalendarAdmin() {
  const { reloadReference, toast } = useApp();
  const [years, setYears] = useState<YearData[]>([]);
  const [edit, setEdit] = useState<Partial<Closure> | null>(null);
  const [yearEdit, setYearEdit] = useState<Partial<SchoolYear> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [json, setJson] = useState(EXAMPLE);
  const [importResult, setImportResult] = useState<any>(null);

  const load = () => get<{ school_years: YearData[] }>("/admin/calendar").then((r) => setYears(r.school_years));
  useEffect(() => {
    load();
  }, []);

  async function approve(c: Closure, status: "approved" | "unreviewed") {
    try {
      await patch(`/admin/calendar/closures/${c.id}`, { version: c.version, review_status: status, reviewed_at: status === "approved" ? todayBerlin() : null });
      load();
    } catch (e) {
      toast(errorText(e), "error");
    }
  }

  async function saveClosure() {
    if (!edit) return;
    setError(null);
    try {
      const body = { title: edit.title, starts_on: edit.starts_on, ends_on: edit.ends_on, kind: edit.kind, source: edit.source };
      if (edit.id) await patch(`/admin/calendar/closures/${edit.id}`, { ...body, version: edit.version });
      else await post("/admin/calendar/closures", { ...body, school_year_id: edit.school_year_id });
      toast("Eintrag gespeichert.");
      setEdit(null);
      load();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function saveYear() {
    if (!yearEdit) return;
    setError(null);
    try {
      if (yearEdit.id) await patch(`/admin/calendar/school-years/${yearEdit.id}`, { version: yearEdit.version, label: yearEdit.label, starts_on: yearEdit.starts_on, ends_on: yearEdit.ends_on });
      else await post("/admin/calendar/school-years", { label: yearEdit.label, starts_on: yearEdit.starts_on, ends_on: yearEdit.ends_on });
      toast("Schuljahr gespeichert.");
      setYearEdit(null);
      load();
      reloadReference();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function runImport(dryRun: boolean) {
    setImportResult(null);
    let payload: unknown;
    try {
      payload = JSON.parse(json);
    } catch {
      setImportResult({ errors: [{ path: "", message: "Kein gültiges JSON." }] });
      return;
    }
    try {
      const r = await post("/admin/calendar/import", payload, { dry_run: dryRun });
      setImportResult(r);
      if (r.applied) {
        toast("Kalender importiert.");
        load();
        reloadReference();
      }
    } catch (e) {
      setImportResult({ errors: [{ path: "", message: e instanceof ApiError ? e.message : "Fehler" }] });
    }
  }

  return (
    <div className="stack">
      <Alert kind="info">Ferien, Feiertage und schulfreie Tage gelten für alle Klassen des Schuljahrs. Ungeprüfte Einträge sind nur zur Demonstration zulässig – vor dem echten Unterrichtseinsatz gegen die amtliche Quelle prüfen und freigeben. Kalenderänderungen berechnen Wochenangaben neu, verschieben aber keine Einheiten.</Alert>
      <button type="button" className="btn" onClick={() => setYearEdit({ label: "", starts_on: "", ends_on: "" })}>+ Schuljahr anlegen</button>
      {years.map((y) => (
        <section key={y.id} className="card">
          <div className="row-between">
            <h2>Schuljahr {y.label}</h2>
            <button type="button" className="btn btn-small btn-ghost" onClick={() => setYearEdit({ ...y })}>Bearbeiten</button>
          </div>
          <p>
            {formatDate(y.starts_on)} – {formatDate(y.ends_on)} ·{" "}
            {y.status.demo_only ? <Badge kind="warn">⚠ {y.status.unreviewed} ungeprüft – nur Demo</Badge> : <Badge kind="ok">✔ alle Einträge freigegeben</Badge>}
          </p>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Bezeichnung</th><th>Zeitraum</th><th>Art</th><th>Prüfung</th><th>Aktionen</th></tr></thead>
              <tbody>
                {y.closures.map((c) => (
                  <tr key={c.id}>
                    <td data-label="Bezeichnung">{c.title}<br /><span className="small muted">{c.source}</span></td>
                    <td data-label="Zeitraum">{formatDate(c.starts_on)}{c.ends_on !== c.starts_on && <> – {formatDate(c.ends_on)}</>}</td>
                    <td data-label="Art">{KINDS[c.kind] ?? c.kind}</td>
                    <td data-label="Prüfung">{c.review_status === "approved" ? <Badge kind="ok">✔ freigegeben {c.reviewed_at && formatDate(c.reviewed_at)}</Badge> : <Badge kind="warn">⚠ ungeprüft</Badge>}</td>
                    <td data-label="Aktionen">
                      <div className="row">
                        {c.review_status === "approved" ? (
                          <button type="button" className="btn btn-small btn-ghost" onClick={() => approve(c, "unreviewed")}>Zurücknehmen</button>
                        ) : (
                          <button type="button" className="btn btn-small" onClick={() => approve(c, "approved")}>Geprüft & freigeben</button>
                        )}
                        <button type="button" className="btn btn-small btn-ghost" onClick={() => setEdit({ ...c })}>Bearbeiten</button>
                        <button type="button" className="btn btn-small btn-danger-ghost" onClick={async () => { await del(`/admin/calendar/closures/${c.id}`); load(); }}>Löschen</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className="btn btn-small" onClick={() => setEdit({ school_year_id: y.id, title: "", starts_on: "", ends_on: "", kind: "holiday", source: "" })}>+ Eintrag</button>
        </section>
      ))}

      <section className="card stack">
        <h2>JSON-Import</h2>
        <p className="small muted">Erst „Vorschau prüfen“, dann übernehmen. Fehlerhafte Dateien werden nicht übernommen. Mit "replace": true werden die Einträge des Schuljahrs ersetzt.</p>
        <Field label="Kalender-JSON">
          <textarea rows={12} className="mono" value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false} />
        </Field>
        <div className="row">
          <button type="button" className="btn" onClick={() => runImport(true)}>Vorschau prüfen</button>
          <button type="button" className="btn btn-primary" onClick={() => runImport(false)} disabled={!importResult || importResult.errors?.length > 0 || importResult.applied}>Übernehmen</button>
        </div>
        {importResult && (
          <>
            {importResult.errors?.length > 0 ? (
              <Alert kind="error">
                <p>{importResult.errors.length} Fehler:</p>
                <ul>{importResult.errors.map((e: any, i: number) => <li key={i}><code>{e.path || "–"}</code>: {e.message}</li>)}</ul>
              </Alert>
            ) : importResult.applied ? (
              <Alert kind="ok">Import übernommen.</Alert>
            ) : (
              <Alert kind="ok">Keine Fehler. {importResult.summary?.closures} Einträge für {importResult.summary?.school_year?.label}{importResult.summary?.replace ? " (ersetzt vorhandene)" : ""}.</Alert>
            )}
            {importResult.preview?.length > 0 && (
              <ul className="small">{importResult.preview.map((p: any, i: number) => <li key={i}>{p.title}: {formatDate(p.starts_on)} – {formatDate(p.ends_on)} ({KINDS[p.kind] ?? p.kind}, {p.review_status === "approved" ? "freigegeben" : "ungeprüft"})</li>)}</ul>
            )}
          </>
        )}
      </section>

      <Dialog open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Eintrag bearbeiten" : "Eintrag anlegen"} footer={<><span className="spacer" /><button type="button" className="btn btn-ghost" onClick={() => setEdit(null)}>Abbrechen</button><button type="button" className="btn btn-primary" onClick={saveClosure}>Speichern</button></>}>
        {edit && (
          <div className="stack">
            {error && <Alert kind="error">{error}</Alert>}
            <Field label="Bezeichnung"><input value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></Field>
            <div className="form-grid">
              <Field label="Von (einschließlich)"><input type="date" value={edit.starts_on} onChange={(e) => setEdit({ ...edit, starts_on: e.target.value })} /></Field>
              <Field label="Bis (einschließlich)"><input type="date" value={edit.ends_on} onChange={(e) => setEdit({ ...edit, ends_on: e.target.value })} /></Field>
              <Field label="Art">
                <select value={edit.kind} onChange={(e) => setEdit({ ...edit, kind: e.target.value })}>
                  {Object.entries(KINDS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Quelle / Herkunft (URL oder Beschreibung)"><input value={edit.source} onChange={(e) => setEdit({ ...edit, source: e.target.value })} /></Field>
          </div>
        )}
      </Dialog>

      <Dialog open={!!yearEdit} onClose={() => setYearEdit(null)} title={yearEdit?.id ? "Schuljahr bearbeiten" : "Schuljahr anlegen"} footer={<><span className="spacer" /><button type="button" className="btn btn-ghost" onClick={() => setYearEdit(null)}>Abbrechen</button><button type="button" className="btn btn-primary" onClick={saveYear}>Speichern</button></>}>
        {yearEdit && (
          <div className="stack">
            {error && <Alert kind="error">{error}</Alert>}
            <Field label="Bezeichnung"><input value={yearEdit.label} onChange={(e) => setYearEdit({ ...yearEdit, label: e.target.value })} placeholder="2027/2028" /></Field>
            <div className="form-grid">
              <Field label="Erster Unterrichtstag"><input type="date" value={yearEdit.starts_on} onChange={(e) => setYearEdit({ ...yearEdit, starts_on: e.target.value })} /></Field>
              <Field label="Letzter Unterrichtstag"><input type="date" value={yearEdit.ends_on} onChange={(e) => setYearEdit({ ...yearEdit, ends_on: e.target.value })} /></Field>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
