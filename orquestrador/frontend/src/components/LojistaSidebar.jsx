import { initials } from "../lib/format.js";
import BrandMark from "./BrandMark.jsx";
import Icon from "./Icon.jsx";

export default function LojistaSidebar({ active, name }) {
  const link = (href, icon, label, isActive = false) => (
    <a
      href={href}
      className={`nav-link${isActive ? " active" : ""}`}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon name={icon} className="nav-icon" />
      {label}
    </a>
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-main">
        <a className="brand" href="/" aria-label="InovaVarejo - início">
          <BrandMark className="brand-mark" />
          <span>InovaVarejo</span>
        </a>
        <a className="new-demand-button" href="/chat.html">
          <Icon name="plus" size={17} />
          Nova necessidade
        </a>
        <p className="nav-caption">Começar</p>
        <nav className="side-nav" aria-label="Sua loja">
          {link("/chat.html", "storefront", "Encontrar soluções", active === "chat")}
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
