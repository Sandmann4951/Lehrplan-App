import { useEffect, useState } from "react";
import { errorText, get, post } from "../../api";
import { useApp } from "../../context";
import { formatDateTime } from "../../util";
import { Alert, Badge, Field, Spinner } from "../../components/ui";

interface PilotStatus {
  material_counts: Record<string, number>;
  demo_materials: number;
  professionally_released: number;
  required_for_classroom_pilot: number;
  classroom_pilot_ready: boolean;
  calendars: { school_year: string; total: number; unreviewed: number; demo_only: boolean }[];
}

export function StatusAdmin() {
  const { toast } = useApp();
  const [s, setS] = useState<PilotStatus | null>(null);
  const [json, setJson] = useState("");
  const [result, setResult] = useState<any>(null);
  useEffect(() => {
    get<PilotStatus>("/admin/pilot-status").then(setS);
  }, []);

  async function importContent(dry: boolean) {
    try {
      const r = await post("/admin/import/content", JSON.parse(json), { dry_run: dry });
      setResult(r);
      if (r.applied) toast("Inhalte als Entwurf importiert.");
    } catch (e) {
      setResult({ errors: [{ path: "", message: e instanceof SyntaxError ? "Kein gültiges JSON." : errorText(e) }] });
    }
  }

  if (!s) return <Spinner />;
  return (
    <div className="stack">
      <section className="card">
        <h2>Freigabestand für den Unterrichtspiloten</h2>
        <p>
          Fachlich freigegebene Materialien: <strong>{s.professionally_released}</strong> von {s.required_for_classroom_pilot} erforderlichen{" "}
          {s.classroom_pilot_ready ? <Badge kind="ok">✔ bereit</Badge> : <Badge kind="warn">⚠ noch nicht bereit</Badge>}
        </p>
        <p className="small">
          Demonstrationsmaterial (nicht fachlich geprüft): {s.demo_materials} · Status: {Object.entries(s.material_counts).map(([k, v]) => `${{ draft: "Entwurf", reviewed: "geprüft", released: "freigegeben", archived: "archiviert" }[k] ?? k}: ${v}`).join(", ")}
        </p>
        {s.calendars.map((c) => (
          <p key={c.school_year} className="small">
            Kalender {c.school_year}: {c.total} Einträge, {c.unreviewed} ungeprüft {c.demo_only ? <Badge kind="warn">nur Demo</Badge> : <Badge kind="ok">freigegeben</Badge>}
          </p>
        ))}
      </section>
      <section className="card">
        <h2>Sicherung</h2>
        <p className="small">Tägliche Sicherung (14 Tagesstände) läuft automatisch. Manuelle Sicherung und Wiederherstellung erfolgen über die Betriebsskripte <code>scripts/backup.sh</code> und <code>scripts/restore.sh</code> (siehe Betriebsanleitung).</p>
      </section>
      <section className="card stack">
        <h2>Inhaltsimport (JSON)</h2>
        <p className="small muted">Themen, Lehrplanbezüge und Materialmetadaten (z. B. aus der Artifacts-Demo). Materialien werden immer als Entwurf importiert; PDFs werden anschließend hochgeladen.</p>
        <Field label="Inhalts-JSON">
          <textarea rows={8} className="mono" value={json} onChange={(e) => setJson(e.target.value)} placeholder='{"schema_version": 1, "topics": [], "curriculum": [], "materials": []}' spellCheck={false} />
        </Field>
        <div className="row">
          <button type="button" className="btn" onClick={() => importContent(true)} disabled={!json}>Vorschau prüfen</button>
          <button type="button" className="btn btn-primary" onClick={() => importContent(false)} disabled={!result || result.errors?.length > 0 || result.applied}>Übernehmen</button>
        </div>
        {result && (result.errors?.length ? (
          <Alert kind="error"><ul>{result.errors.map((e: any, i: number) => <li key={i}><code>{e.path || "–"}</code>: {e.message}</li>)}</ul></Alert>
        ) : (
          <Alert kind="ok">{result.applied ? "Übernommen." : "Keine Fehler."} {result.summary && JSON.stringify(result.summary)}</Alert>
        ))}
      </section>
    </div>
  );
}

interface AuditItem {
  id: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  timestamp: string;
  details: Record<string, unknown> | null;
}

export function AuditAdmin() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: AuditItem[]; total: number; page_size: number } | null>(null);
  useEffect(() => {
    get("/admin/audit", { page, page_size: 50 }).then(setData);
  }, [page]);
  if (!data) return <Spinner />;
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <div className="stack">
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Zeit</th><th>Person</th><th>Aktion</th><th>Objekt</th></tr></thead>
          <tbody>
            {data.items.map((a) => (
              <tr key={a.id}>
                <td data-label="Zeit">{formatDateTime(a.timestamp)}</td>
                <td data-label="Person">{a.actor_name ?? "System"}</td>
                <td data-label="Aktion">{a.action}</td>
                <td data-label="Objekt">{a.entity_type} {a.details ? <span className="small muted">{JSON.stringify(a.details)}</span> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="pager" aria-label="Seiten">
        <button type="button" className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ Zurück</button>
        <span>Seite {page} von {pages}</span>
        <button type="button" className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Weiter ›</button>
      </nav>
    </div>
  );
}
