import { useState } from "react";
import { ApiError, post } from "../api";
import { useApp } from "../context";
import type { SchoolClass } from "../types";
import { Alert, Dialog } from "./ui";

export default function InitPlanDialog({ open, onClose, onDone, schoolClass, hasUnits }: { open: boolean; onClose: () => void; onDone: () => void; schoolClass: SchoolClass; hasUnits: boolean }) {
  const { reference, toast } = useApp();
  const [selected, setSelected] = useState<string[] | null>(null);
  const [replace, setReplace] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const templates = reference?.templates ?? [];
  const chosen = selected ?? templates.map((t) => t.id);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const r = await post<{ created_units: number; unplaced: unknown[]; replaced_units: number }>(`/classes/${schoolClass.id}/initialize-plan`, {
        template_ids: chosen,
        confirm: true,
        replace_existing: replace,
      });
      toast(`${r.created_units} Planeinträge angelegt${r.replaced_units ? `, ${r.replaced_units} ersetzt` : ""}.`);
      if (r.unplaced.length) toast("Einige Einheiten passten nicht mehr ins Schuljahr.", "error");
      onDone();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Fehler beim Anlegen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Plan aus Vorlage anlegen"
      footer={
        <>
          <span className="spacer" />
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Abbrechen
          </button>
          <button type="button" className="btn btn-primary" onClick={run} disabled={busy || chosen.length === 0 || (hasUnits && !replace)}>
            {busy ? "Wird angelegt …" : "Bestätigen und anlegen"}
          </button>
        </>
      }
    >
      <p>
        Die Vorlage wird in Ihren persönlichen Plan <strong>kopiert</strong>. Die Einheiten werden nacheinander auf die Unterrichtswochen verteilt – passend zu Ihren Wochenstunden; Ferien bleiben frei, verkürzte Wochen erhalten weniger
        Stunden. Spätere Änderungen an der Vorlage verändern Ihren Plan nicht.
      </p>
      <fieldset className="fieldset">
        <legend>Vorlagen</legend>
        {templates.map((t) => (
          <label key={t.id} className="check">
            <input type="checkbox" checked={chosen.includes(t.id)} onChange={() => setSelected(chosen.includes(t.id) ? chosen.filter((x) => x !== t.id) : [...chosen, t.id])} />
            <span>
              {t.name} <span className="muted">· {t.units} Themen</span>
            </span>
          </label>
        ))}
      </fieldset>
      <Alert kind="info">Die Startinhalte decken nur einen Teil des Schuljahrs ab. Weitere Einheiten können Sie jederzeit selbst hinzufügen.</Alert>
      {hasUnits && (
        <Alert kind="warn">
          <p>Ihr Plan enthält bereits Einheiten. Sie werden nur ersetzt, wenn Sie dies ausdrücklich bestätigen.</p>
          <label className="check">
            <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />
            <span>Ja, alle vorhandenen Einheiten dieser Klasse ersetzen</span>
          </label>
        </Alert>
      )}
      {error && <Alert kind="error">{error}</Alert>}
    </Dialog>
  );
}
