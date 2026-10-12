import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, del, errorText, get, patch, post } from "../../api";
import { useApp } from "../../context";
import type { ListResponse, MaterialDetail, MaterialSummary, User } from "../../types";
import { bytes, todayBerlin } from "../../util";
import { Alert, Badge, DemoBadge, Field, Spinner } from "../../components/ui";

const STATUS = [
  { value: "draft", label: "Entwurf" },
  { value: "reviewed", label: "Geprüft" },
  { value: "released", label: "Freigegeben" },
  { value: "archived", label: "Archiviert" },
];

export default function MaterialsAdmin() {
  const { reference } = useApp();
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [result, setResult] = useState<ListResponse<MaterialSummary> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<ListResponse<MaterialSummary>>("/admin/materials", { status: status ? [status] : [], q: q || undefined, page_size: 100 })
      .then(setResult)
      .catch((e) => setError(errorText(e)));
  }, [status, q]);

  async function createNew() {
    const topic = reference?.topics[0];
    if (!topic) return;
    try {
      const m = await post<MaterialDetail>("/admin/materials", { topic_id: topic.id, title: "Neues Material", type: "worksheet", level: "standard", duration_minutes: 45 });
      navigate(`/verwaltung/materialien/${m.id}`);
    } catch (e) {
      setError(errorText(e));
    }
  }

  return (
    <div className="stack">
      <div className="toolbar">
        <button type="button" className="btn btn-primary" onClick={createNew}>
          + Material anlegen
        </button>
        <label className="inline-field">
          <span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">alle</option>
            {STATUS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-field">
          <span>Suche</span>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
      </div>
      {error && <Alert kind="error">{error}</Alert>}
      {!result ? (
        <Spinner />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Titel</th>
                <th>Thema</th>
                <th>Typ</th>
                <th>Status</th>
                <th>Dateien</th>
              </tr>
            </thead>
            <tbody>
              {result.items.map((m) => (
                <tr key={m.id}>
                  <td data-label="Titel">
                    <Link to={`/verwaltung/materialien/${m.id}`}>{m.title}</Link>
                  </td>
                  <td data-label="Thema">{m.topic_title}</td>
                  <td data-label="Typ">{m.type_label}</td>
                  <td data-label="Status">
                    {m.status_label} {m.is_demo && <DemoBadge />}
                  </td>
                  <td data-label="Dateien">
                    {m.has_main_file ? "✔ Haupt" : "✖ Haupt"} · {m.has_solution ? "✔ Lösung" : "– Lösung"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function MaterialEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { reference, toast, user } = useApp();
  const [m, setM] = useState<MaterialDetail | null>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [reviewer, setReviewer] = useState("");
  const [reviewedAt, setReviewedAt] = useState(todayBerlin());
  const [reviewNote, setReviewNote] = useState("");

  const load = async () => {
    const d = await get<MaterialDetail>(`/admin/materials/${id}`);
    setM(d);
    setForm({
      title: d.title,
      topic_id: d.topic_id,
      description: d.description,
      learning_goal: d.learning_goal,
      keywords: d.keywords.join(", "),
      type: d.type,
      level: d.level,
      duration_minutes: d.duration_minutes,
      author: d.author,
      license_text: d.license_text,
      curriculum_ids: d.curriculum.map((c) => c.id),
    });
  };

  useEffect(() => {
    load().catch((e) => setError(errorText(e)));
    get<{ items: User[] }>("/admin/users").then((r) => setUsers(r.items));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!reviewer && user) setReviewer(user.id);
  }, [user, reviewer]);

  if (!m || !reference) return error ? <Alert kind="error">{error}</Alert> : <Spinner />;
  const subjectId = reference.topics.find((t) => t.id === form.topic_id)?.subject_id;

  async function run(fn: () => Promise<unknown>, okMessage: string) {
    setError(null);
    setErrors({});
    try {
      await fn();
      toast(okMessage);
      await load();
    } catch (e) {
      if (e instanceof ApiError) {
        setErrors(e.fieldErrors);
        const problems = e.body.problems as string[] | undefined;
        setError(e.status === 409 ? "Das Material wurde inzwischen geändert. Bitte Seite neu laden." : problems ? `${e.message} ${problems.join(" ")}` : e.message);
      } else setError("Aktion fehlgeschlagen.");
    }
  }

  const save = (e: FormEvent) => {
    e.preventDefault();
    run(() => patch(`/admin/materials/${m.id}`, { version: m.version, ...form, duration_minutes: Number(form.duration_minutes) }), "Material gespeichert.");
  };

  const upload = (purpose: "main" | "solution", file: File | undefined) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("purpose", purpose);
    fd.append("version", String(m.version));
    fd.append("file", file);
    run(() => post(`/admin/materials/${m.id}/files`, fd), "Datei hochgeladen.");
  };

  const fileOf = (p: "main" | "solution") => m.files.find((f) => f.purpose === p);

  return (
    <div className="stack">
      <Link to="/verwaltung/materialien">‹ Alle Materialien</Link>
      <div className="page-head">
        <h2>{m.title}</h2>
        <p>
          <Badge kind={m.status === "released" ? "ok" : m.status === "archived" ? "warn" : "neutral"}>{m.status_label}</Badge> {m.is_demo && <DemoBadge />}
        </p>
      </div>
      {error && <Alert kind="error">{error}</Alert>}

      <section className="card">
        <h3>Freigabe</h3>
        <p className="small muted">Ablauf: Entwurf → geprüft → freigegeben → archiviert. KI-Erstellung allein ersetzt keine fachliche Prüfung.</p>
        {m.release_check && m.release_check.length > 0 ? (
          <Alert kind="warn">
            <p>Vor der Freigabe fehlt noch:</p>
            <ul>
              {m.release_check.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </Alert>
        ) : (
          <Alert kind="ok">Alle Pflichtangaben für die Freigabe sind vorhanden.</Alert>
        )}
        {(m.status === "draft" || m.status === "reviewed") && (
          <div className="form-grid">
            <Field label="Fachliche Prüfung durch">
              <select value={reviewer} onChange={(e) => setReviewer(e.target.value)}>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Prüfdatum">
              <input type="date" value={reviewedAt} max={todayBerlin()} onChange={(e) => setReviewedAt(e.target.value)} />
            </Field>
            <Field label="Prüfnotiz">
              <input value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} />
            </Field>
            <div className="field-end">
              <button type="button" className="btn" onClick={() => run(() => post(`/admin/materials/${m.id}/review`, { version: m.version, reviewer_id: reviewer, reviewed_at: reviewedAt, review_note: reviewNote }), "Prüfung erfasst.")}>
                Als geprüft markieren
              </button>
            </div>
          </div>
        )}
        <div className="row">
          {m.status === "reviewed" && (
            <button type="button" className="btn btn-primary" onClick={() => run(() => post(`/admin/materials/${m.id}/release`, { version: m.version }), "Material freigegeben.")}>
              Freigeben
            </button>
          )}
          {m.status !== "archived" && (
            <button type="button" className="btn" onClick={() => run(() => post(`/admin/materials/${m.id}/archive`, { version: m.version }), "Material archiviert.")}>
              Archivieren
            </button>
          )}
          {(m.status === "archived" || m.status === "reviewed" || m.status === "released") && (
            <button type="button" className="btn btn-ghost" onClick={() => run(() => post(`/admin/materials/${m.id}/reopen`, { version: m.version }), "Material zurück in Entwurf.")}>
              Zurück in Entwurf
            </button>
          )}
          {m.status === "draft" && (
            <button
              type="button"
              className="btn btn-danger-ghost"
              onClick={async () => {
                try {
                  await del(`/admin/materials/${m.id}`);
                  toast("Entwurf gelöscht.");
                  navigate("/verwaltung/materialien");
                } catch (e) {
                  setError(errorText(e));
                }
              }}
            >
              Entwurf löschen
            </button>
          )}
        </div>
        {m.reviewed_at && (
          <p className="small">
            Geprüft am {m.reviewed_at} {m.reviewer_name && `von ${m.reviewer_name}`} {m.review_note && `– ${m.review_note}`}
          </p>
        )}
      </section>

      <section className="card">
        <h3>Dateien (nur PDF, max. 20 MB)</h3>
        {(["main", "solution"] as const).map((p) => {
          const f = fileOf(p);
          return (
            <div key={p} className="file-actions">
              <p>
                <strong>{p === "main" ? "Hauptdatei" : "Lösung / Auswertungshilfe"}:</strong>{" "}
                {f ? (
                  <>
                    <a href={f.url} target="_blank" rel="noopener">
                      {f.original_name}
                    </a>{" "}
                    <span className="muted small">
                      {bytes(f.size_bytes)} · SHA-256 {f.sha256.slice(0, 12)}…
                    </span>
                  </>
                ) : (
                  <span className="muted">keine</span>
                )}
              </p>
              <div className="row">
                <label className="btn btn-small file-btn">
                  {f ? "Ersetzen …" : "Hochladen …"}
                  <input type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(e) => upload(p, e.target.files?.[0])} />
                </label>
                {f && (
                  <button type="button" className="btn btn-small btn-ghost" onClick={() => run(() => del(`/admin/materials/${m.id}/files/${f.id}`, { version: m.version }), "Datei entfernt.")}>
                    Entfernen
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </section>

      <form className="card stack" onSubmit={save}>
        <h3>Metadaten</h3>
        <div className="form-grid">
          <Field label="Titel" error={errors.title}>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </Field>
          <Field label="Thema" error={errors.topic_id}>
            <select value={form.topic_id} onChange={(e) => setForm({ ...form, topic_id: e.target.value, curriculum_ids: [] })}>
              {reference.subjects.map((s) => (
                <optgroup key={s.id} label={s.title}>
                  {reference.topics
                    .filter((t) => t.subject_id === s.id)
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.title}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
          </Field>
          <Field label="Materialtyp">
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              {reference.material_types.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Niveau">
            <select value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })}>
              {reference.levels.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Dauer (Minuten)" error={errors.duration_minutes}>
            <input type="number" min={1} value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} />
          </Field>
          <Field label="Autor" error={errors.author}>
            <input value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
          </Field>
        </div>
        <Field label="Kurzbeschreibung">
          <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Lernziel">
          <textarea rows={2} value={form.learning_goal} onChange={(e) => setForm({ ...form, learning_goal: e.target.value })} />
        </Field>
        <Field label="Schlagwörter (durch Komma getrennt)">
          <input value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
        </Field>
        <Field label="Lizenz / Nutzungserlaubnis">
          <textarea rows={2} value={form.license_text} onChange={(e) => setForm({ ...form, license_text: e.target.value })} />
        </Field>
        <fieldset className="fieldset">
          <legend>Kompetenzbezüge</legend>
          {reference.curriculum
            .filter((c) => c.subject_id === subjectId)
            .map((c) => (
              <label key={c.id} className="check">
                <input
                  type="checkbox"
                  checked={form.curriculum_ids.includes(c.id)}
                  onChange={() => setForm({ ...form, curriculum_ids: form.curriculum_ids.includes(c.id) ? form.curriculum_ids.filter((x: string) => x !== c.id) : [...form.curriculum_ids, c.id] })}
                />
                <span>
                  <strong>{c.section_code}</strong> {c.section_title} {c.verification_status === "verified" ? "✔ geprüft" : "· ungeprüft"}
                </span>
              </label>
            ))}
        </fieldset>
        <button className="btn btn-primary" type="submit">
          Metadaten speichern
        </button>
      </form>
    </div>
  );
}
