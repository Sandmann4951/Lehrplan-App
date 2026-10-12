import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { errorText, get } from "../api";
import type { MaterialDetail, MaterialFile } from "../types";
import { bytes, formatDate } from "../util";
import { Alert, Badge, Spinner } from "../components/ui";
import { FavoriteButton } from "../components/MaterialCard";

function FileActions({ file, label }: { file: MaterialFile; label: string }) {
  return (
    <div className="file-actions">
      <p className="file-name">
        <strong>{label}</strong> <span className="muted small">· {file.original_name} · {bytes(file.size_bytes)}</span>
      </p>
      <div className="row">
        <a className="btn btn-primary" href={file.url} target="_blank" rel="noopener">
          Öffnen
        </a>
        <a className="btn" href={`${file.url}?download=true`} download={file.original_name}>
          Herunterladen
        </a>
      </div>
    </div>
  );
}

export default function MaterialPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [m, setM] = useState<MaterialDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<"main" | "solution">("main");

  useEffect(() => {
    setM(null);
    get<MaterialDetail>(`/materials/${id}`)
      .then(setM)
      .catch((e) => setError(errorText(e)));
  }, [id]);

  if (error)
    return (
      <section className="page">
        <Alert kind="error">{error}</Alert>
        <Link to="/bibliothek">Zur Bibliothek</Link>
      </section>
    );
  if (!m) return <Spinner />;

  const main = m.files.find((f) => f.purpose === "main");
  const solution = m.files.find((f) => f.purpose === "solution");
  const shown = preview === "solution" && solution ? solution : main;
  const solutionLabel = m.type === "assessment" ? "Auswertungshilfe" : "Lösung";

  return (
    <section className="page">
      <button type="button" className="btn btn-ghost btn-small" onClick={() => navigate(-1)}>
        ‹ Zurück
      </button>
      <div className="page-head">
        <h1>{m.title}</h1>
        <FavoriteButton material={m} onChange={(f) => setM({ ...m, is_favorite: f })} />
      </div>
      <p className="mcard-meta">
        <Badge>{m.subject_title}</Badge>
        <Badge>{m.type_label}</Badge>
        <Badge>{m.level_label}</Badge>
        <Badge>{m.duration_minutes} Minuten</Badge>
        {m.status === "archived" && <Badge kind="warn">archiviert</Badge>}
      </p>
      {m.is_demo && (
        <Alert kind="warn">
          <strong>Demonstrationsmaterial – nicht fachlich geprüft.</strong> Es dient der technischen Erprobung und ist vor dem Unterrichtseinsatz durch eine Lehrkraft zu prüfen.
        </Alert>
      )}

      <div className="detail-grid">
        <div className="stack">
          <section className="card">
            <h2>Beschreibung</h2>
            <p className="pre">{m.description || "—"}</p>
            <h3>Lernziel</h3>
            <p className="pre">{m.learning_goal || "—"}</p>
            <dl className="facts">
              <dt>Thema (interne Pilotplanung)</dt>
              <dd>{m.topic_title}</dd>
              <dt>Zeitbedarf</dt>
              <dd>{m.duration_minutes} Minuten</dd>
              <dt>Autor</dt>
              <dd>{m.author || "—"}</dd>
              <dt>Lizenz / Nutzungserlaubnis</dt>
              <dd className="pre">{m.license_text || "—"}</dd>
              <dt>Freigabestand</dt>
              <dd>
                {m.status_label}
                {m.is_demo ? " (technische Demo-Freigabe, keine fachliche Prüfung)" : m.reviewed_at ? ` · fachlich geprüft am ${formatDate(m.reviewed_at)}${m.reviewer_name ? ` von ${m.reviewer_name}` : ""}` : ""}
              </dd>
              {m.keywords.length > 0 && (
                <>
                  <dt>Schlagwörter</dt>
                  <dd>{m.keywords.join(", ")}</dd>
                </>
              )}
            </dl>
          </section>

          <section className="card">
            <h2>Offizieller Lehrplanbezug</h2>
            <p className="muted small">LehrplanPLUS Bayern, Fachlehrplan Jahrgangsstufen 1/2 (sinngemäß). Die Themenzuordnung zu Klasse 1 ist eine pädagogische Pilotplanung.</p>
            {m.curriculum.length === 0 && <p>Kein Kompetenzbezug hinterlegt.</p>}
            <ul className="plain stack-sm">
              {m.curriculum.map((c) => (
                <li key={c.id}>
                  <strong>{c.section_code}</strong> {c.section_title}
                  <br />
                  {c.paraphrased_goal}
                  <br />
                  <span className="small muted">
                    {c.verification_status === "verified" ? "✔ geprüft" : "⚠ ungeprüft"} · Abruf {c.retrieved_on ? formatDate(c.retrieved_on) : "—"} ·{" "}
                    <a href={c.source_url} target="_blank" rel="noopener noreferrer">
                      Quelle (online)
                    </a>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className="card">
          <h2>Dateien</h2>
          {main ? <FileActions file={main} label="Schülerdatei / Hauptdatei" /> : <Alert kind="warn">Keine Hauptdatei vorhanden.</Alert>}
          {solution ? (
            <FileActions file={solution} label={solutionLabel} />
          ) : (
            <Alert kind="info">Zu diesem Material gibt es keine {solutionLabel}.</Alert>
          )}
          {main && (
            <>
              {solution && (
                <div className="segmented" role="group" aria-label="Vorschau wählen">
                  <button type="button" aria-pressed={preview === "main"} onClick={() => setPreview("main")}>
                    Vorschau Hauptdatei
                  </button>
                  <button type="button" aria-pressed={preview === "solution"} onClick={() => setPreview("solution")}>
                    Vorschau {solutionLabel}
                  </button>
                </div>
              )}
              {shown && (
                <object key={shown.id} className="pdf-preview" data={shown.url} type="application/pdf" aria-label={`PDF-Vorschau ${shown.original_name}`}>
                  <div className="pdf-fallback">
                    <p>Die eingebettete Vorschau wird von diesem Browser nicht unterstützt.</p>
                    <a className="btn btn-primary" href={shown.url} target="_blank" rel="noopener">
                      PDF öffnen
                    </a>
                  </div>
                </object>
              )}
              <p className="small muted">Falls die Vorschau leer bleibt: „Öffnen“ oder „Herunterladen“ verwenden.</p>
            </>
          )}
        </section>
      </div>
    </section>
  );
}
