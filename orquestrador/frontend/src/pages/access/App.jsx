import { useEffect, useMemo, useState } from "react";

import { backendGet } from "../../lib/http.js";
import { saveActor } from "../../lib/session.js";
import BrandMark from "../../components/BrandMark.jsx";

const ADMIN_ACTOR = { perfil: "admin", id: null };

function MerchantIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M3 20.25h18M4.5 20.25V9.5m15 10.75V9.5M3.5 9.5l1.2-5h14.6l1.2 5m-17 0a2.5 2.5 0 0 0 4.25 1.77A2.5 2.5 0 0 0 12 11.27a2.5 2.5 0 0 0 4.25 0A2.5 2.5 0 0 0 20.5 9.5M9 20.25v-5.5h6v5.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

function StartupIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M15.6 14.4a6 6 0 0 1-5.85 7.35v-4.8m5.85-2.55A15 15 0 0 0 21.75 2.25 15 15 0 0 0 9.6 8.4m6 6a15 15 0 0 1-5.85 2.55m-.15-8.55a6 6 0 0 0-7.35 5.85h4.8m2.55-5.85a15 15 0 0 0-2.55 5.85m2.7 2.7a4.5 4.5 0 0 0-1.8 4.35 4.5 4.5 0 0 0 4.35-1.8M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

function AssociationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M16.5 18.75a8.9 8.9 0 0 0 3.75-.5 3 3 0 0 0-4.7-2.7m.95 3.2v.03c0 .23-.01.45-.04.67A12 12 0 0 1 12 21a12 12 0 0 1-5.96-1.58 6 6 0 0 1-.04-.67m12-0a6 6 0 0 0-.94-3.2m0 0a6 6 0 0 0-10.12 0m0 0a3 3 0 0 0-4.7 2.7 9 9 0 0 0 3.76.48m.94-3.18a6 6 0 0 0-.94 3.2M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

export default function App() {
  const [status, setStatus] = useState("checking");
  const [lojistas, setLojistas] = useState([]);
  const [startups, setStartups] = useState([]);
  const [lojistaId, setLojistaId] = useState("");
  const [startupId, setStartupId] = useState("");
  const [message, setMessage] = useState({ state: "", text: "" });

  useEffect(() => {
    let ativo = true;

    async function carregar() {
      try {
        await backendGet("/api/saude", ADMIN_ACTOR);
        const [lojistasCarregados, startupsCarregadas] = await Promise.all([
          backendGet("/api/lojistas", ADMIN_ACTOR),
          backendGet("/api/startups", ADMIN_ACTOR),
        ]);
        if (!ativo) return;
        setLojistas(Array.isArray(lojistasCarregados) ? lojistasCarregados : []);
        setStartups(Array.isArray(startupsCarregadas) ? startupsCarregadas : []);
        setStatus("connected");
        if (lojistasCarregados.length === 0 || startupsCarregadas.length === 0) {
          setMessage({
            state: "error",
            text: "Ainda não há cadastros disponíveis para todos os perfis.",
          });
        }
      } catch (error) {
        if (!ativo) return;
        setStatus("error");
        setMessage({
          state: "error",
          text: `Não foi possível carregar os ambientes: ${error.message}`,
        });
      }
    }

    carregar();
    return () => {
      ativo = false;
    };
  }, []);

  const connected = status === "connected";

  const lojistaSelecionado = useMemo(
    () => lojistas.find((item) => String(item.id) === String(lojistaId)),
    [lojistas, lojistaId],
  );
  const startupSelecionada = useMemo(
    () => startups.find((item) => String(item.id) === String(startupId)),
    [startups, startupId],
  );

  function selecionar(perfil, id, nome) {
    try {
      saveActor({ perfil, id, nome });
    } catch (error) {
      setMessage({
        state: "error",
        text: `Não foi possível guardar o ambiente selecionado: ${error.message}`,
      });
      return;
    }

    if (perfil === "lojista") {
      window.location.assign("/chat.html");
      return;
    }
    if (perfil === "startup") {
      window.location.assign("/oportunidade.html");
      return;
    }
    if (perfil === "admin") {
      window.location.assign("/admin.html");
      return;
    }

    setMessage({
      state: "success",
      text: `Ambiente ${nome} selecionado. A escolha ficará disponível para as próximas telas.`,
    });
  }

  return (
    <>
      <header className="site-header">
        <div className="header-content">
          <a className="brand" href="/" aria-label="InovaVarejo - início">
            <BrandMark className="brand-icon" />
            <span>InovaVarejo</span>
          </a>
          <div
            className="system-status"
            aria-live="polite"
            data-state={connected ? "connected" : status === "error" ? "error" : undefined}
          >
            <span className="status-dot" />
            <span>
              {status === "checking"
                ? "Conectando ao sistema..."
                : connected
                  ? "Sistema conectado"
                  : "Sistema indisponível"}
            </span>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="page-heading">
          <h1>Como você quer entrar?</h1>
          <p>Escolha o perfil que representa você.</p>
        </div>

        <section className="access-grid" aria-label="Perfis de acesso">
          <article className="access-card">
            <div className="card-content">
              <div className="card-icon" aria-hidden="true">
                <MerchantIcon />
              </div>
              <h2>Lojista</h2>
              <p className="card-description">Encontre soluções para seu negócio.</p>
              <div className="field">
                <label htmlFor="lojista-select">Seu estabelecimento</label>
                <select
                  id="lojista-select"
                  value={lojistaId}
                  disabled={!connected || lojistas.length === 0}
                  onChange={(event) => setLojistaId(event.target.value)}
                >
                  <option value="">
                    {connected ? "Selecione um estabelecimento" : "Carregando estabelecimentos..."}
                  </option>
                  {lojistas.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              className="access-button"
              type="button"
              disabled={!lojistaId || !connected}
              onClick={() => selecionar("lojista", lojistaSelecionado.id, lojistaSelecionado.nome)}
            >
              Entrar como lojista
            </button>
          </article>

          <article className="access-card">
            <div className="card-content">
              <div className="card-icon" aria-hidden="true">
                <StartupIcon />
              </div>
              <h2>Empresa de tecnologia</h2>
              <p className="card-description">Consulte oportunidades comerciais.</p>
              <div className="field">
                <label htmlFor="startup-select">Sua empresa</label>
                <select
                  id="startup-select"
                  value={startupId}
                  disabled={!connected || startups.length === 0}
                  onChange={(event) => setStartupId(event.target.value)}
                >
                  <option value="">
                    {connected ? "Selecione sua empresa" : "Carregando empresas..."}
                  </option>
                  {startups.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              className="access-button"
              type="button"
              disabled={!startupId || !connected}
              onClick={() =>
                selecionar("startup", startupSelecionada.id, startupSelecionada.nome)
              }
            >
              Entrar como empresa
            </button>
          </article>

          <article className="access-card">
            <div className="card-content">
              <div className="card-icon" aria-hidden="true">
                <AssociationIcon />
              </div>
              <h2>Associação</h2>
              <p className="card-description">Gerencie demandas e oportunidades.</p>
              <div className="field">
                <span className="field-label">Acesso da associação</span>
                <div className="permission-value">
                  <span>Gerenciar solicitações</span>
                </div>
              </div>
            </div>
            <button
              className="access-button"
              type="button"
              disabled={!connected}
              onClick={() => selecionar("admin", null, "Associação")}
            >
              Entrar como associação
            </button>
          </article>
        </section>

        <p className="access-message" role="status" aria-live="polite" data-state={message.state}>
          {message.text}
        </p>
        <p className="demo-notice">
          Versão de demonstração: os perfis servem apenas para apresentar as telas.
        </p>
      </main>

      <footer className="site-footer">
        <div className="footer-content">
          <span>© 2026 InovaVarejo — Hackaton-Connect-7.0-Demo</span>
          <nav aria-label="Links institucionais">
            <a href="#termos">Termos</a>
            <a href="#privacidade">Privacidade</a>
            <a href="mailto:ajuda@orvyn.example">Ajuda</a>
          </nav>
        </div>
      </footer>
    </>
  );
}
