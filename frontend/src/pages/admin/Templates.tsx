import { useEffect, useState } from "react";
import { errorText, get, patch } from "../../api";
import { useApp } from "../../context";
import { Alert } from "../../components/ui";

interface TUnit {
  id?: string;
  topic_id: string;
  topic_title?: string | null;
  sequence?: number;
  estimated_lessons: number;
  material_ids: string[];
  curriculum_ids: string[];
}
interface Template {
  id: string;
  name: string;
  subject_id: string;
  archived: boolean;
  version: number;
  units: TUnit[];
}

export default function TemplatesAdmin() {
  const { reference, reloadReference, toast } = useApp();
  const [items, setItems] = useState<Template[]>([]);
  const [drafts, setDrafts] = useState<Record<string, TUnit[]>>({});
  const load = () =>
    get<{ items: Template[] }>("/admin/templates").then((r) => {
      setItems(r.items);
      setDrafts(Object.fromEntries(r.items.map((t) => [t.id, t.units.map((u) => ({ ...u }))])));
    });
  useEffect(() => {
    load();
  }, []);

  async function save(t: Template) {
    try {
      await patch(`/admin/templates/${t.id}`, {
        version: t.version,
        units: drafts[t.id].map((u) => ({ topic_id: u.topic_id, estimated_lessons: u.estimated_lessons, material_ids: u.material_ids, curriculum_ids: u.curriculum_ids })),
      });
      toast("Vorlage gespeichert. Bestehende Pläne bleiben unverändert.");
      load();
      reloadReference();
    } catch (e) {
      toast(errorText(e), "error");
    }
  }

  function move(tid: string, idx: number, dir: -1 | 1) {
    const list = [...drafts[tid]];
    const j = idx + dir;
    if (j < 0 || j >= list.length) return;
    [list[idx], list[j]] = [list[j], list[idx]];
    setDrafts({ ...drafts, [tid]: list });
  }

  return (
    <div className="stack">
      <Alert kind="info">Vorlagen enthalten geordnete Einheiten mit geschätztem Stundenbedarf. Neue Pläne werden daraus kopiert; spätere Änderungen hier wirken nicht auf bestehende Pläne.</Alert>
      {items.map((t) => {
        const topics = reference?.topics.filter((x) => x.subject_id === t.subject_id) ?? [];
        const list = drafts[t.id] ?? [];
        return (
          <section key={t.id} className="card stack">
            <h2>{t.name}</h2>
            <ol className="plain stack-sm">
              {list.map((u, i) => (
                <li key={i} className="template-row">
                  <span className="seq">{i + 1}.</span>
                  <select aria-label="Thema" value={u.topic_id} onChange={(e) => setDrafts({ ...drafts, [t.id]: list.map((x, k) => (k === i ? { ...x, topic_id: e.target.value, material_ids: [] } : x)) })}>
                    {topics.map((tp) => (
                      <option key={tp.id} value={tp.id}>
                        {tp.title}
                      </option>
                    ))}
                  </select>
                  <label className="inline-field">
                    <span>Std.</span>
                    <input type="number" min={1} className="num" value={u.estimated_lessons} onChange={(e) => setDrafts({ ...drafts, [t.id]: list.map((x, k) => (k === i ? { ...x, estimated_lessons: Math.max(1, Number(e.target.value) || 1) } : x)) })} />
                  </label>
                  <button type="button" className="btn-icon" aria-label="Nach oben" onClick={() => move(t.id, i, -1)}>↑</button>
                  <button type="button" className="btn-icon" aria-label="Nach unten" onClick={() => move(t.id, i, 1)}>↓</button>
                  <button type="button" className="btn-icon" aria-label="Entfernen" onClick={() => setDrafts({ ...drafts, [t.id]: list.filter((_, k) => k !== i) })}>✕</button>
                </li>
              ))}
            </ol>
            <p className="small muted">Summe: {list.reduce((a, u) => a + u.estimated_lessons, 0)} Unterrichtsstunden</p>
            <div className="row">
              <button type="button" className="btn btn-small" onClick={() => topics[0] && setDrafts({ ...drafts, [t.id]: [...list, { topic_id: topics[0].id, estimated_lessons: 5, material_ids: [], curriculum_ids: [] }] })}>
                + Einheit
              </button>
              <button type="button" className="btn btn-primary btn-small" onClick={() => save(t)}>
                Vorlage speichern
              </button>
            </div>
          </section>
        );
      })}
    </div>
  );
}
