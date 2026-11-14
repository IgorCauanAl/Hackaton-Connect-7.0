import { initials } from "../lib/format.js";

const NAV = [
  { id: "admin", href: "/admin.html", icon: "▦", label: "Visão geral" },
  { id: "demandas", href: "/admin-demandas.html", icon: "▤", label: "Demandas" },
  { id: "radar", href: "/admin-radar.html", icon: "ϟ", label: "Radar de oportunidades" },
  { id: "padroes", href: "/admin-padroes.html", icon: "▥", label: "Análise de padrões" },
];

export function AdminSidebar({ active }) {
  return (
    <aside className="admin-sidebar">
      <div>
        <a className="admin-brand" href="/">InovaVarejo</a>
        <a className="admin-primary-link" href="/admin-demandas.html">Revisar demandas →</a>
        <p className="admin-nav-label">Administração</p>
        <nav className="admin-nav" aria-label="Administração">
          {NAV.map((item) => (
            <a
              key={item.id}
              href={item.href}
              className={active === item.id ? "active" : undefined}
              aria-current={active === item.id ? "page" : undefined}
            >
              {item.icon} <span>{item.label}</span>
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
          <span className="admin-connection">
            <i></i> Sistema conectado
          </span>
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
