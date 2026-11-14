import { useEffect, useState } from "react";

import BrandMark from "../../components/BrandMark.jsx";
import Icon from "../../components/Icon.jsx";
import { formatSegment } from "../../lib/format.js";
import { backendGet } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

function StartupSidebar({ name }) {
  const iniciais = String(name || "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase("pt-BR"))
    .join("");

  return (
    <aside className="sidebar">
      <div className="sidebar-main">
        <a className="brand" href="/" aria-label="InovaVarejo - início">
          <BrandMark className="brand-mark" />
          <span>InovaVarejo</span>
        </a>
        <p className="nav-caption">Sua empresa</p>
        <nav className="side-nav" aria-label="Solicitações da empresa">
          <a className="nav-link active" href="/oportunidade.html" aria-current="page">
            <Icon name="document" className="nav-icon" />
            Solicitações recebidas
          </a>
        </nav>
      </div>
      <div className="sidebar-profile">
        <span className="avatar">{iniciais || "--"}</span>
        <span className="profile-copy">
          <strong>{name || "Carregando empresa..."}</strong>
          <small>Empresa de tecnologia</small>
        </span>
      </div>
    </aside>
  );
}

function formatContext(signal) {
  const total = Number(signal?.lojistas_mesma_dor || 0);
  const sameSegment = Number(signal?.no_mesmo_ramo || 0);
  const sameRegion = Number(signal?.na_mesma_regiao || 0);
  return `${total} ${total === 1 ? "lojista relatou" : "lojistas relataram"} uma necessidade semelhante. ${sameSegment} no mesmo segmento e ${sameRegion} na mesma região.`;
}

function formatNeed(tags) {
  if (!tags?.length) return "Necessidade informada pela loja.";
  return `Assuntos relacionados: ${tags.map(formatSegment).join(", ")}.`;
}

function formatApplication(blocks, startup) {
  const compatibility = blocks.compatibilidade;
  const score = compatibility?.indice;
  const reasons = (compatibility?.criterios || [])
    .filter((criterion) => criterion.motivo)
    .slice(0, 2)
    .map((criterion) => criterion.motivo);
  const details = [];

  if (startup.solucao) details.push(startup.solucao);
  if (Number.isFinite(score)) details.push(`Aderência à necessidade: ${score} de 100.`);
  details.push(...reasons);
  return details.join(" ");
}

export default function App() {
  const [actor] = useState(readActor);
  const [startup, setStartup] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [selected, setSelected] = useState(0);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!actor || actor.perfil !== "startup" || !Number.isInteger(actor.id)) {
      window.location.replace("/");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        const [startupCarregada, oportunidades] = await Promise.all([
          backendGet(`/api/startups/${actor.id}`, actor),
          backendGet(`/api/startups/${actor.id}/oportunidades`, actor),
        ]);
        if (!ativo) return;
        setStartup(startupCarregada);
        setOpportunities(Array.isArray(oportunidades) ? oportunidades : []);
      } catch (falha) {
        if (ativo) setError(falha.message || String(falha));
      } finally {
        if (ativo) setLoading(false);
      }
    }

    carregar();
    return () => {
      ativo = false;
    };
  }, [actor]);

  useEffect(() => {
    const opportunity = opportunities[selected];
    if (!actor || !opportunity) return;
    let ativo = true;

    async function carregarRelatorio() {
      setError("");
      try {
        const dados = await backendGet(
          `/api/relatorios/${opportunity.relatorio_id}?versao=anonimizada`,
          actor,
        );
        if (ativo) setReport(dados);
      } catch (falha) {
        if (ativo) setError(falha.message || String(falha));
      }
    }

    carregarRelatorio();
    return () => {
      ativo = false;
    };
  }, [actor, opportunities, selected]);

  if (!actor || actor.perfil !== "startup") return null;

  const opportunity = opportunities[selected];
  const blocks = report?.blocos || {};
  const summary = blocks.resumo?.resumo || opportunity?.titulo;
  const segment = blocks.perfil_loja?.ramo || opportunity?.ramo;
  const tags = blocks.dor_contexto?.tags || [];

  return (
    <>
      <StartupSidebar name={startup?.nome || actor.nome} />

      <div className="app-area">
        <header className="topbar">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/" aria-label="Início">
              <Icon name="home" />
            </a>
            <span aria-hidden="true">›</span>
            <strong>Oportunidade recebida</strong>
          </nav>
        </header>

        <main className="page-content">
          <div className="page-heading">
            <span className="forwarded-label">
              <span aria-hidden="true">•</span> Enviado pela associação comercial
            </span>
            <h1>Oportunidade recebida</h1>
            <p>Veja como sua solução pode ajudar um negócio local.</p>
          </div>

          {opportunities.length > 1 ? (
            <label className="opportunity-picker" htmlFor="opportunity-picker">
              <span>Oportunidade</span>
              <select
                id="opportunity-picker"
                value={selected}
                onChange={(event) => setSelected(Number(event.target.value))}
              >
                {opportunities.map((item, index) => (
                  <option key={item.relatorio_id} value={index}>
                    {item.titulo || `Oportunidade ${index + 1}`}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {error ? (
            <div className="page-error" role="alert">
              {error}
            </div>
          ) : null}
          {loading ? (
            <div className="loading-state" role="status">
              Carregando oportunidades...
            </div>
          ) : null}

          {!loading && !error && opportunity && report ? (
            <div>
              <section className="summary-card" aria-label="Resumo da oportunidade">
                <div className="summary-item">
                  <span className="summary-label">Oportunidade</span>
                  <strong>{summary || "Necessidade comercial"}</strong>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Ramo do negócio</span>
                  <strong>{formatSegment(segment)}</strong>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Origem</span>
                  <strong>Associação comercial</strong>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Status</span>
                  <span className="status-badge">
                    {opportunity.status === "encaminhada"
                      ? "Recebida"
                      : formatSegment(opportunity.status)}
                  </span>
                </div>
              </section>

              <section
                className="report-card"
                aria-label="Resumo da oportunidade"
              >
                <header className="report-header">
                  <div>
                    <h2>Resumo da oportunidade</h2>
                    <p>Informações para entender a necessidade do lojista</p>
                  </div>
                  <span className="privacy-badge">
                    <span aria-hidden="true">●</span> Identificação do lojista protegida
                  </span>
                </header>

                <div className="report-sections">
                  <article className="report-section">
                    <h3>
                      <span>1.</span> Problema identificado
                    </h3>
                    <p>
                      {summary || "Necessidade comercial identificada pela associação."}
                    </p>
                  </article>
                  <article className="report-section">
                    <h3><span>2.</span> O que a loja precisa</h3>
                    <p>
                      {formatNeed(tags) ||
                        "Pedido de ajuda enviado pela loja."}
                    </p>
                  </article>
                  <article className="report-section">
                    <h3><span>3.</span> Informações do negócio</h3>
                    <p>
                      {formatContext(blocks.sinal_mercado) ||
                        "Contexto comercial disponível no relatório."}
                    </p>
                  </article>
                  <article className="report-section">
                    <h3>
                      <span>4.</span> Oportunidade de aplicação
                    </h3>
                    <p>
                      {formatApplication(blocks, startup || {}) ||
                        "Avalie como sua solução pode ajudar esta loja."}
                    </p>
                  </article>
                </div>

                <footer className="report-footer">
                  <span>InovaVarejo</span>
                  <span>Esta página é apenas para consulta</span>
                </footer>
              </section>
            </div>
          ) : null}

          {!loading && !error && opportunities.length === 0 ? (
            <section className="empty-state">
              <span className="empty-icon" aria-hidden="true">
                ▣
              </span>
              <h2>Nenhuma oportunidade recebida ainda</h2>
              <p>
                Quando a associação encaminhar uma demanda para sua startup, o relatório aparecerá
                aqui.
              </p>
            </section>
          ) : null}
        </main>
      </div>
    </>
  );
}
