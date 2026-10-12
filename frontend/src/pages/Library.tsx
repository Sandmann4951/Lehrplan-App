import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { errorText, get } from "../api";
import { useApp } from "../context";
import type { ListResponse, MaterialSummary } from "../types";
import { Alert, Empty, Spinner } from "../components/ui";
import MaterialCard from "../components/MaterialCard";
import { cls } from "../util";

const MULTI = ["subject", "topic", "competency", "level", "type"] as const;
const DURATIONS = [
  { value: "", label: "beliebig" },
  { value: "20", label: "bis 20 Min." },
  { value: "45", label: "bis 45 Min." },
  { value: "90", label: "bis 90 Min." },
];

export default function LibraryPage() {
  const { reference } = useApp();
  const [params, setParams] = useSearchParams();
  const [result, setResult] = useState<ListResponse<MaterialSummary> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [q, setQ] = useState(params.get("q") ?? "");

  const page = Number(params.get("page") ?? "1");
  const sort = params.get("sort") ?? "relevance";
  const sel = (k: string) => params.getAll(k);

  useEffect(() => {
    const query: Record<string, string | string[] | number> = { page, page_size: 20, sort };
    MULTI.forEach((k) => (query[k] = sel(k)));
    const qv = params.get("q");
    if (qv) query.q = qv;
    const dm = params.get("duration_max");
    if (dm) query.duration_max = dm;
    setResult(null);
    get<ListResponse<MaterialSummary>>("/materials", query)
      .then((r) => {
        setResult(r);
        setError(null);
      })
      .catch((e) => setError(errorText(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  function update(fn: (p: URLSearchParams) => void) {
    setParams((p) => {
      fn(p);
      p.delete("page");
      return p;
    });
  }

  function toggle(key: string, value: string) {
    update((p) => {
      const cur = p.getAll(key);
      p.delete(key);
      (cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value]).forEach((v) => p.append(key, v));
    });
  }

  function search(e: FormEvent) {
    e.preventDefault();
    update((p) => (q.trim() ? p.set("q", q.trim()) : p.delete("q")));
  }

  const subjects = sel("subject");
  const topics = useMemo(() => reference?.topics.filter((t) => !subjects.length || subjects.includes(t.subject_id)) ?? [], [reference, subjects]);
  const competencies = useMemo(() => reference?.curriculum.filter((c) => !subjects.length || subjects.includes(c.subject_id)) ?? [], [reference, subjects]);
  const activeCount = MULTI.reduce((a, k) => a + sel(k).length, 0) + (params.get("duration_max") ? 1 : 0);

  const setFavorite = (id: string, fav: boolean) => setResult((r) => r && { ...r, items: r.items.map((m) => (m.id === id ? { ...m, is_favorite: fav } : m)) });

  const group = (title: string, key: string, options: { value: string; label: string }[]) => (
    <fieldset className="fieldset filter-group">
      <legend>{title}</legend>
      {options.map((o) => (
        <label key={o.value} className="check">
          <input type="checkbox" checked={sel(key).includes(o.value)} onChange={() => toggle(key, o.value)} />
          <span>{o.label}</span>
        </label>
      ))}
    </fieldset>
  );

  const pages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  return (
    <section className="page">
      <div className="page-head">
        <h1>Materialbibliothek</h1>
      </div>
      <form className="searchbar" role="search" onSubmit={search}>
        <label className="sr-only" htmlFor="q">
          Suche in Titel, Beschreibung und Schlagwörtern
        </label>
        <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Suchen (Titel, Beschreibung, Schlagwörter)" enterKeyHint="search" />
        <button className="btn btn-primary" type="submit">
          Suchen
        </button>
        <button type="button" className="btn filter-toggle" aria-expanded={panelOpen} aria-controls="filterpanel" onClick={() => setPanelOpen(true)}>
          Filter{activeCount ? ` (${activeCount})` : ""}
        </button>
      </form>

      <div className="library">
        <aside id="filterpanel" className={cls("filterpanel", panelOpen && "open")} aria-label="Filter">
          <div className="filterpanel-head">
            <h2>Filter</h2>
            <button type="button" className="btn-icon filter-close" onClick={() => setPanelOpen(false)} aria-label="Filter schließen">
              ✕
            </button>
          </div>
          <div className="filterpanel-body">
            {reference && (
              <>
                {group("Fach", "subject", reference.subjects.map((s) => ({ value: s.id, label: s.title })))}
                {group("Thema", "topic", topics.map((t) => ({ value: t.id, label: t.title })))}
                {group("Kompetenz (LehrplanPLUS 1/2)", "competency", competencies.map((c) => ({ value: c.id, label: `${c.section_code} ${c.section_title}` })))}
                {group("Niveau", "level", reference.levels)}
                {group("Materialtyp", "type", reference.material_types)}
                <fieldset className="fieldset filter-group">
                  <legend>Dauer</legend>
                  <select aria-label="Maximale Dauer" value={params.get("duration_max") ?? ""} onChange={(e) => update((p) => (e.target.value ? p.set("duration_max", e.target.value) : p.delete("duration_max")))}>
                    {DURATIONS.map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                  </select>
                </fieldset>
              </>
            )}
          </div>
          <div className="filterpanel-foot">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() =>
                update((p) => {
                  MULTI.forEach((k) => p.delete(k));
                  p.delete("duration_max");
                })
              }
            >
              Zurücksetzen
            </button>
            <button type="button" className="btn btn-primary filter-close" onClick={() => setPanelOpen(false)}>
              {result ? `${result.total} Treffer anzeigen` : "Anzeigen"}
            </button>
          </div>
        </aside>
        {panelOpen && <div className="backdrop" onClick={() => setPanelOpen(false)} aria-hidden="true" />}

        <div className="results">
          <div className="results-head">
            <p role="status">{result ? `${result.total} ${result.total === 1 ? "Material" : "Materialien"}` : ""}</p>
            <label className="inline-field">
              <span>Sortierung</span>
              <select value={sort} onChange={(e) => update((p) => p.set("sort", e.target.value))}>
                <option value="relevance">Relevanz</option>
                <option value="title">Titel</option>
              </select>
            </label>
          </div>
          {error && <Alert kind="error">{error}</Alert>}
          {!result && !error && <Spinner />}
          {result && result.items.length === 0 && <Empty title="Keine passenden freigegebenen Materialien gefunden." />}
          <div className="stack">
            {result?.items.map((m) => (
              <MaterialCard key={m.id} m={m} onFavorite={(f) => setFavorite(m.id, f)} />
            ))}
          </div>
          {result && pages > 1 && (
            <nav className="pager" aria-label="Seiten">
              <button type="button" className="btn" disabled={page <= 1} onClick={() => setParams((p) => { p.set("page", String(page - 1)); return p; })}>
                ‹ Zurück
              </button>
              <span>
                Seite {page} von {pages}
              </span>
              <button type="button" className="btn" disabled={page >= pages} onClick={() => setParams((p) => { p.set("page", String(page + 1)); return p; })}>
                Weiter ›
              </button>
            </nav>
          )}
        </div>
      </div>
    </section>
  );
}
