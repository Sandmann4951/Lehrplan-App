import { Link } from "react-router-dom";
import { ApiError, del, put } from "../api";
import { useApp } from "../context";
import type { MaterialSummary } from "../types";
import { Badge, DemoBadge } from "./ui";

export function FavoriteButton({ material, onChange }: { material: MaterialSummary; onChange: (fav: boolean) => void }) {
  const { toast } = useApp();
  const fav = !!material.is_favorite;
  async function toggle() {
    try {
      if (fav) await del(`/favorites/${material.id}`);
      else await put(`/favorites/${material.id}`);
      onChange(!fav);
      toast(fav ? "Von der Merkliste entfernt." : "Auf die Merkliste gesetzt.");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Merkliste konnte nicht gespeichert werden.", "error");
    }
  }
  return (
    <button type="button" className={`btn btn-small fav ${fav ? "fav-on" : ""}`} aria-pressed={fav} onClick={toggle}>
      <span aria-hidden="true">{fav ? "★" : "☆"}</span> {fav ? "Gemerkt" : "Merken"}
    </button>
  );
}

export default function MaterialCard({ m, reason, onFavorite }: { m: MaterialSummary; reason?: string; onFavorite?: (fav: boolean) => void }) {
  return (
    <article className="mcard">
      <div className="mcard-main">
        <h3 className="mcard-title">
          <Link to={`/material/${m.id}`}>{m.title}</Link>
        </h3>
        <p className="mcard-meta">
          <Badge>{m.type_label}</Badge>
          <Badge>{m.level_label}</Badge>
          <Badge>{m.duration_minutes} Min.</Badge>
          {m.is_demo && <DemoBadge />}
          {m.status === "archived" && <Badge kind="warn">archiviert</Badge>}
        </p>
        {m.topic_title && <p className="muted small">Thema: {m.topic_title}</p>}
        {reason && <p className="reason small">Begründung: {reason}</p>}
        <p className="small">{m.has_solution ? "✔ Lösung vorhanden" : "– keine Lösung / Auswertungshilfe"}</p>
      </div>
      {onFavorite && (
        <div className="mcard-actions">
          <FavoriteButton material={m} onChange={onFavorite} />
        </div>
      )}
    </article>
  );
}
