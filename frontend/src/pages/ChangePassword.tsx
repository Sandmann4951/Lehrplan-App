import { useState, type FormEvent } from "react";
import { ApiError, post } from "../api";
import { useApp } from "../context";
import { Alert, Field } from "../components/ui";
import type { User } from "../types";

export function ChangePasswordForm({ onDone }: { onDone?: () => void }) {
  const { setUser, toast } = useApp();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (next !== repeat) {
      setErrors({ repeat: "Die Passwörter stimmen nicht überein." });
      return;
    }
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      const r = await post<{ user: User }>("/auth/change-password", { current_password: current, new_password: next });
      setUser(r.user);
      toast("Passwort geändert.");
      setCurrent("");
      setNext("");
      setRepeat("");
      onDone?.();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        setMessage(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="stack" noValidate>
      {message && <Alert kind="error">{message}</Alert>}
      <Field label="Aktuelles Passwort" error={errors.current_password}>
        <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
      </Field>
      <Field label="Neues Passwort" error={errors.new_password} hint="Mindestens 10 Zeichen.">
        <input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={10} />
      </Field>
      <Field label="Neues Passwort wiederholen" error={errors.repeat}>
        <input type="password" autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} required />
      </Field>
      <button className="btn btn-primary" type="submit" disabled={busy || !current || !next}>
        Passwort ändern
      </button>
    </form>
  );
}

export default function ChangePasswordPage({ forced }: { forced?: boolean }) {
  const { logout } = useApp();
  return (
    <main className="auth-page" id="main">
      <div className="card auth-card">
        <h1>Passwort ändern</h1>
        {forced && <Alert kind="warn">Ihr Passwort wurde zurückgesetzt. Bitte vergeben Sie jetzt ein eigenes Passwort.</Alert>}
        <ChangePasswordForm />
        <button type="button" className="btn btn-ghost" onClick={() => logout()}>
          Abmelden
        </button>
      </div>
    </main>
  );
}
