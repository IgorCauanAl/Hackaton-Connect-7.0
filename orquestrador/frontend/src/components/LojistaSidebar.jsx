import { initials } from "../lib/format.js";

/**
 * Sidebar do lojista. `variant="chat"` usa os ícones com `.nav-icon`
 * (chat.css); `variant="workspace"` reproduz o markup das demais telas.
 */
export default function LojistaSidebar({ active, name, variant = "workspace" }) {
  const withIcons = variant === "chat";
  const link = (href, icon, label, isActive = false) => (
    <a
      href={href}
      className={`nav-link${isActive ? " active" : ""}`}
      aria-current={isActive ? "page" : undefined}
    >
      {withIcons ? (
        <span className="nav-icon" aria-hidden="true">{icon}</span>
      ) : (
        <span aria-hidden="true">{icon}</span>
      )}
      {label}
    </a>
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-main">
        <a className="brand" href="/" aria-label="InovaVarejo - início">
          <span className="brand-mark" aria-hidden="true">O</span>
          <span>InovaVarejo</span>
        </a>
        <a className="new-demand-button" href="/chat.html">
          <span aria-hidden="true">＋</span>
          Nova necessidade
        </a>
        <p className="nav-caption">Workspace</p>
        <nav className="side-nav" aria-label="Workspace">
          {link("/", "⌂", "Visão geral")}
          {link("/chat.html", "⌕", "Encontrar soluções", active === "chat")}
          {link("/", "⚙", "Configurações")}
        </nav>
      </div>
      <div className="sidebar-profile">
        <span className="avatar">{initials(name) || "--"}</span>
        <span className="profile-copy">
          <strong>{name || "Carregando perfil..."}</strong>
          <small>Lojista</small>
        </span>
      </div>
    </aside>
  );
}
