import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { cls } from "../../util";
import UsersAdmin from "./Users";
import MaterialsAdmin, { MaterialEdit } from "./Materials";
import { CurriculumAdmin, TopicsAdmin } from "./Content";
import CalendarAdmin from "./Calendar";
import TemplatesAdmin from "./Templates";
import { AuditAdmin, StatusAdmin } from "./Status";

const TABS = [
  { to: "status", label: "Status" },
  { to: "benutzer", label: "Benutzer" },
  { to: "materialien", label: "Materialien" },
  { to: "themen", label: "Themen" },
  { to: "lehrplan", label: "Lehrplanbezüge" },
  { to: "kalender", label: "Kalender" },
  { to: "vorlagen", label: "Vorlagen" },
  { to: "protokoll", label: "Protokoll" },
];

export default function AdminPage() {
  return (
    <section className="page">
      <h1>Verwaltung</h1>
      <nav className="tabs" aria-label="Verwaltungsbereiche">
        {TABS.map((t) => (
          <NavLink key={t.to} to={`/verwaltung/${t.to}`} className={({ isActive }) => cls("tab", isActive && "active")}>
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route index element={<Navigate to="status" replace />} />
        <Route path="status" element={<StatusAdmin />} />
        <Route path="benutzer" element={<UsersAdmin />} />
        <Route path="materialien" element={<MaterialsAdmin />} />
        <Route path="materialien/:id" element={<MaterialEdit />} />
        <Route path="themen" element={<TopicsAdmin />} />
        <Route path="lehrplan" element={<CurriculumAdmin />} />
        <Route path="kalender" element={<CalendarAdmin />} />
        <Route path="vorlagen" element={<TemplatesAdmin />} />
        <Route path="protokoll" element={<AuditAdmin />} />
      </Routes>
    </section>
  );
}
