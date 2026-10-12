import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { errorText, get } from "../api";
import type { ListResponse, MaterialSummary } from "../types";
import { Alert, Empty, Spinner } from "../components/ui";
import MaterialCard from "../components/MaterialCard";

export default function FavoritesPage() {
  const [items, setItems] = useState<MaterialSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<ListResponse<MaterialSummary>>("/favorites")
      .then((r) => setItems(r.items))
      .catch((e) => setError(errorText(e)));
  }, []);

  return (
    <section className="page">
      <h1>Merkliste</h1>
      {error && <Alert kind="error">{error}</Alert>}
      {!items && !error && <Spinner />}
      {items && items.length === 0 && (
        <Empty title="Ihre Merkliste ist leer.">
          <Link to="/bibliothek">Materialien in der Bibliothek finden</Link>
        </Empty>
      )}
      <div className="stack">
        {items?.map((m) => (
          <MaterialCard key={m.id} m={m} onFavorite={(f) => !f && setItems((list) => list?.filter((x) => x.id !== m.id) ?? null)} />
        ))}
      </div>
    </section>
  );
}
