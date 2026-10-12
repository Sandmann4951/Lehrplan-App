import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useApp } from "./context";
import { Spinner } from "./components/ui";
import { cls } from "./util";
import LoginPage from "./pages/Login";
import ChangePasswordPage from "./pages/ChangePassword";
import DashboardPage from "./pages/Dashboard";
import PlanPage from "./pages/Plan";
import ClassesPage from "./pages/Classes";
import LibraryPage from "./pages/Library";
import MaterialPage from "./pages/Material";
import FavoritesPage from "./pages/Favorites";
import AccountPage from "./pages/Account";
import AdminPage from "./pages/admin/Admin";

function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout, toasts } = useApp();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setMenuOpen(false), [location.pathname]);

  const links = [
    { to: "/", label: "Übersicht", end: true },
    { to: "/plan", label: "Wochenplan" },
    { to: "/bibliothek", label: "Bibliothek" },
    { to: "/merkliste", label: "Merkliste" },
    { to: "/klassen", label: "Klassen" },
    ...(user?.role === "admin" ? [{ to: "/verwaltung", label: "Verwaltung" }] : []),
  ];

  return (
    <div className="app">
      <a href="#main" className="skip-link">Zum Inhalt springen</a>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand" aria-label="Unterrichtsassistent – zur Übersicht">
            <img src="/favicon.svg" alt="" width={28} height={28} />
            <span>Unterrichtsassistent</span>
          </NavLink>
          <button type="button" className="btn-icon menu-toggle" aria-expanded={menuOpen} aria-controls="hauptmenue" onClick={() => setMenuOpen((o) => !o)}>
            <span aria-hidden="true">{menuOpen ? "✕" : "☰"}</span>
            <span className="sr-only">Menü</span>
          </button>
          <nav id="hauptmenue" className={cls("mainnav", menuOpen && "open")} aria-label="Hauptnavigation">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => cls("navlink", isActive && "active")}>
                {l.label}
              </NavLink>
            ))}
            <NavLink to="/konto" className={({ isActive }) => cls("navlink", isActive && "active")}>
              Konto
            </NavLink>
            <button type="button" className="navlink navbutton" onClick={() => logout()}>
              Abmelden
            </button>
          </nav>
        </div>
      </header>
      <main id="main" className="main" tabIndex={-1}>
        {children}
      </main>
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={cls("toast", t.kind === "error" && "toast-error")} role={t.kind === "error" ? "alert" : "status"}>
            {t.kind === "error" ? "✖ " : "✔ "}
            {t.message}
          </div>
        ))}
      </div>
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useApp();
  if (loading) return <Spinner label="Anwendung wird geladen …" />;
  if (!user) return <LoginPage />;
  if (user.must_change_password) return <ChangePasswordPage forced />;
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/klassen" element={<ClassesPage />} />
        <Route path="/bibliothek" element={<LibraryPage />} />
        <Route path="/material/:id" element={<MaterialPage />} />
        <Route path="/merkliste" element={<FavoritesPage />} />
        <Route path="/konto" element={<AccountPage />} />
        <Route path="/verwaltung/*" element={user.role === "admin" ? <AdminPage /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
