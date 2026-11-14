import { initials } from "../lib/format.js";
import BrandMark from "./BrandMark.jsx";
import Icon from "./Icon.jsx";

const NAV = [
  { id: "admin", href: "/admin.html", icon: "home", label: "Visão geral" },
  { id: "demandas", href: "/admin-demandas.html", icon: "document", label: "Solicitações" },
  { id: "radar", href: "/admin-radar.html", icon: "radar", label: "Oportunidades" },
  { id: "padroes", href: "/admin-padroes.html", icon: "chart", label: "Necessidades recorrentes" },
];

export function AdminSidebar({ active }) {
  return (
    <aside className="admin-sidebar">
      <div>
        <a className="admin-brand" href="/">
          <BrandMark className="admin-brand-mark" />
          <span>InovaVarejo</span>
        </a>
        <a className="admin-primary-link" href="/admin-demandas.html">
          Revisar solicitações <Icon name="arrowRight" size={16} />
        </a>
        <p className="admin-nav-label">Menu da associação</p>
        <nav className="admin-nav" aria-label="Administração">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={item.href}
              className={active === item.id ? "active" : undefined}
              aria-current={active === item.id ? "page" : undefined}
            >
              <Icon name={item.icon} className="admin-nav-icon" />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>
      </div>
      <div className="admin-profile">
        <span className="admin-avatar">{initials("Associação Comercial")}</span>
        <span>
          <strong>Associação Comercial</strong>
          <small>Administração</small>
        </span>
      </div>
    </aside>
  );
}

export function AdminShell({ active, topbar, children }) {
  return (
    <>
      <AdminSidebar active={active} />
      <div className="admin-app">
        <header className="admin-topbar">
          <span>{topbar}</span>
        </header>
        <main className="admin-content">{children}</main>
      </div>
    </>
  );
}

export function AdminError({ message }) {
  if (!message) return null;
  return (
    <div className="admin-error" role="alert">
      {message}
    </div>
  );
}
