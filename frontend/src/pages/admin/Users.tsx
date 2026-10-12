import { useEffect, useState, type FormEvent } from "react";
import { ApiError, errorText, get, patch, post } from "../../api";
import { useApp } from "../../context";
import type { User } from "../../types";
import { Alert, Badge, Field } from "../../components/ui";

export default function UsersAdmin() {
  const { user: me, toast } = useApp();
  const [users, setUsers] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<"teacher" | "admin">("teacher");
  const [temp, setTemp] = useState<{ email: string; password: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = () => get<{ items: User[] }>("/admin/users").then((r) => setUsers(r.items)).catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    setErrors({});
    setError(null);
    try {
      const r = await post<{ user: User; temporary_password: string }>("/admin/users", { email, display_name: name, role });
      setTemp({ email: r.user.email, password: r.temporary_password });
      setEmail("");
      setName("");
      load();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        setError(err.message);
      }
    }
  }

  async function update(u: User, body: Partial<User>) {
    try {
      await patch(`/admin/users/${u.id}`, { version: u.version, ...body });
      toast("Benutzer gespeichert.");
      load();
    } catch (err) {
      toast(errorText(err), "error");
      load();
    }
  }

  async function reset(u: User) {
    try {
      const r = await post<{ temporary_password: string }>(`/admin/users/${u.id}/reset-password`);
      setTemp({ email: u.email, password: r.temporary_password });
      load();
    } catch (err) {
      toast(errorText(err), "error");
    }
  }

  return (
    <div className="stack">
      {temp && (
        <Alert kind="ok">
          <p>
            Temporäres Passwort für <strong>{temp.email}</strong>: <code className="secret">{temp.password}</code>
          </p>
          <p className="small">Wird nur jetzt angezeigt. Bitte persönlich übergeben – beim nächsten Login muss das Passwort geändert werden.</p>
          <button type="button" className="btn btn-small" onClick={() => setTemp(null)}>
            Ausblenden
          </button>
        </Alert>
      )}
      <form className="card form-grid" onSubmit={create}>
        <h2 className="span-all">Benutzer anlegen</h2>
        {error && <div className="span-all"><Alert kind="error">{error}</Alert></div>}
        <Field label="E-Mail" error={errors.email}>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Anzeigename" error={errors.display_name}>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Rolle">
          <select value={role} onChange={(e) => setRole(e.target.value as "teacher" | "admin")}>
            <option value="teacher">Lehrkraft</option>
            <option value="admin">Administrator</option>
          </select>
        </Field>
        <div className="field-end">
          <button className="btn btn-primary" type="submit" disabled={!email || !name}>
            Anlegen
          </button>
        </div>
      </form>

      <p className="muted small">{users.length} von höchstens 20 Konten im Pilot. Administratoren sehen keine persönlichen Pläne.</p>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>E-Mail</th>
              <th>Rolle</th>
              <th>Status</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td data-label="Name">{u.display_name}</td>
                <td data-label="E-Mail">{u.email}</td>
                <td data-label="Rolle">
                  <select aria-label={`Rolle von ${u.display_name}`} value={u.role} onChange={(e) => update(u, { role: e.target.value as User["role"] })} disabled={u.id === me?.id}>
                    <option value="teacher">Lehrkraft</option>
                    <option value="admin">Administrator</option>
                  </select>
                </td>
                <td data-label="Status">
                  {u.active ? <Badge kind="ok">✔ aktiv</Badge> : <Badge kind="warn">⛔ gesperrt</Badge>}
                  {u.must_change_password && <Badge>Passwortwechsel offen</Badge>}
                </td>
                <td data-label="Aktionen">
                  <div className="row">
                    {u.id !== me?.id && (
                      <button type="button" className="btn btn-small" onClick={() => update(u, { active: !u.active })}>
                        {u.active ? "Sperren" : "Entsperren"}
                      </button>
                    )}
                    <button type="button" className="btn btn-small btn-ghost" onClick={() => reset(u)}>
                      Passwort zurücksetzen
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
