import { useApp } from "../context";
import { ChangePasswordForm } from "./ChangePassword";

export default function AccountPage() {
  const { user, logout } = useApp();
  return (
    <section className="page narrow">
      <h1>Mein Konto</h1>
      <div className="card">
        <dl className="facts">
          <dt>Name</dt>
          <dd>{user?.display_name}</dd>
          <dt>E-Mail</dt>
          <dd>{user?.email}</dd>
          <dt>Rolle</dt>
          <dd>{user?.role === "admin" ? "Administrator" : "Lehrkraft"}</dd>
        </dl>
      </div>
      <div className="card">
        <h2>Passwort ändern</h2>
        <ChangePasswordForm />
      </div>
      <button type="button" className="btn" onClick={() => logout()}>
        Abmelden
      </button>
      <p className="muted small">
        Datenschutz: Die Anwendung speichert keine Schülernamen, Noten, Fotos oder Schülerkonten. Ihre Pläne sind nur für Sie sichtbar – auch Administratoren sehen sie in der Anwendung nicht.
      </p>
    </section>
  );
}
