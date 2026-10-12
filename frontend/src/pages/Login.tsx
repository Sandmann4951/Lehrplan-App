import { useState, type FormEvent } from "react";
import { post, setCsrf, ApiError } from "../api";
import { useApp } from "../context";
import { Alert, Field } from "../components/ui";
import type { User } from "../types";

export default function LoginPage() {
  const { setUser } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await post<{ user: User; csrf_token: string }>("/auth/login", { email, password });
      setCsrf(r.csrf_token);
      setUser(r.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anmeldung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page" id="main">
      <form className="card auth-card" onSubmit={submit} noValidate>
        <div className="auth-brand">
          <img src="/favicon.svg" alt="" width={40} height={40} />
          <div>
            <h1>Unterrichtsassistent</h1>
            <p className="muted">Pilot · Bayern · Grundschule Klasse 1</p>
          </div>
        </div>
        {error && <Alert kind="error">{error}</Alert>}
        <Field label="E-Mail">
          <input type="email" autoComplete="username" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </Field>
        <Field label="Passwort">
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy || !email || !password}>
          {busy ? "Anmelden …" : "Anmelden"}
        </button>
        <p className="muted small">Zugangsdaten erhalten Sie von der Administration Ihrer Schule. Eine Selbstregistrierung gibt es nicht.</p>
      </form>
    </main>
  );
}
