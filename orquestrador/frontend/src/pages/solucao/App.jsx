import { useEffect, useState } from "react";

import { CriteriaList } from "../../components/CriteriaList.jsx";
import LojistaSidebar from "../../components/LojistaSidebar.jsx";
import { composeAssistantAnswer } from "../../lib/assistant.js";
import { queryParam } from "../../lib/format.js";
import { backendGet, orchestrate, unwrap } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

export default function App() {
  const [actor] = useState(readActor);
  const [demandId] = useState(() => Number(queryParam("demanda_id")));
  const [startupId] = useState(() => Number(queryParam("startup_id")));
  const [startup, setStartup] = useState(null);
  const [demand, setDemand] = useState(null);
  const [match, setMatch] = useState(null);
  const [rank, setRank] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [consent, setConsent] = useState(false);
  const [consentError, setConsentError] = useState("");
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (!actor || actor.perfil !== "lojista" || !Number.isInteger(actor.id)) {
      window.location.replace("/");
      return;
    }
    if (
      !Number.isInteger(demandId) ||
      demandId < 1 ||
      !Number.isInteger(startupId) ||
      startupId < 1
    ) {
      setLoading(false);
      setError("Não encontramos este pedido ou esta empresa. Volte às opções e tente novamente.");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        const [startupCarregada, matching, demanda] = await Promise.all([
          backendGet(`/api/startups/${startupId}`, actor),
          backendGet(`/api/demandas/${demandId}/matching`, actor),
          backendGet(`/api/demandas/${demandId}`, actor),
        ]);
        if (!ativo) return;
        const ranking = Array.isArray(matching?.ranking_startups)
          ? matching.ranking_startups
          : [];
        const encontrado = ranking.find((item) => item.startup_id === startupId);
        if (!encontrado) {
          throw new Error(
            "Esta empresa não está entre as opções recomendadas para este pedido.",
          );
        }
        setStartup(startupCarregada);
        setDemand(demanda);
        setMatch(encontrado);
        setRank(ranking.findIndex((item) => item.startup_id === startupId) + 1);
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
  }, [actor, demandId, startupId]);

  async function solicitarTeste() {
    setConsentError("");
    if (!consent) {
      setConsentError("Autorize o compartilhamento para continuar.");
      return;
    }
    setRequesting(true);
    try {
      const envelope = await orchestrate("/testes", {
        method: "POST",
        actor,
        body: { demanda_id: demandId, startup_id: startupId, autorizacao: true },
      });
      const resultado = unwrap(envelope);
      if (!Number.isInteger(resultado?.teste_id)) {
        throw new Error("A solicitação de teste não retornou um identificador válido.");
      }
      window.location.assign(`/teste.html?teste_id=${encodeURIComponent(resultado.teste_id)}`);
    } catch (falha) {
      setRequesting(false);
      setConsentError(falha.message || String(falha));
    }
  }

  if (!actor || actor.perfil !== "lojista") return null;

  const resultUrl = `/resultados.html?demanda_id=${encodeURIComponent(demandId)}`;

  return (
    <>
      <LojistaSidebar active="chat" name={actor.nome} />

      <div className="app-area">
        <header className="topbar">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/">Início</a>
            <span>›</span>
            <a href={resultUrl}>Soluções encontradas</a>
            <span>›</span>
            <strong>Detalhes</strong>
          </nav>
        </header>

        <main className="page-content">
          <a className="back-link" href={resultUrl}>
            ← Voltar aos resultados
          </a>

          {error ? (
            <div className="page-error" role="alert">
              {error}
            </div>
          ) : null}
          {loading ? (
            <div className="loading-state" role="status">
              Carregando solução...
            </div>
          ) : null}

          {!loading && !error && startup && match ? (
            <div>
              <section className="solution-card">
                <div className="solution-labels">
                  <span className="rank-badge">
                    {rank === 1 ? "Nossa principal indicação" : `${rank}ª opção`}
                  </span>
                  <span className="category-badge">
                    {startup.categoria || "Solução para varejo"}
                  </span>
                </div>
                <h1>{startup.nome}</h1>
                <p className="solution-description">{startup.descricao || ""}</p>
                <div className="offer-box">
                  <span>Como a solução pode ajudar</span>
                  <p>
                    {startup.solucao ||
                      startup.descricao ||
                      "Detalhes da solução não informados."}
                  </p>
                </div>
              </section>

              <section className="compatibility-section">
                <h2>Por que esta solução pode ajudar</h2>
                <p className="section-subtitle">A partir do que você contou sobre seu negócio</p>
                <div className="compatibility-grid">
                  <div className="score-card">
                    <span className="metric-label">Aderência à sua necessidade</span>
                    <p className="score">
                      <strong>{match.indice}</strong>
                      <span>/100</span>
                    </p>
                    <span className="high-fit">
                      {match.indice >= 85 ? "Boa combinação" : "Pode atender"}
                    </span>
                    <p className="demand-note">
                      Para a necessidade: {demand?.titulo || "informada por você"}
                    </p>
                  </div>
                  <div className="criteria-card">
                    <CriteriaList
                      criteria={match.criterios}
                      headingClass="criterion-header"
                      className="criteria-list"
                    />
                  </div>
                </div>
                <section className="assistant-insight" aria-label="Por que recomendamos">
                  <span>Por que recomendamos</span>
                  <p>{composeAssistantAnswer(demand, match, startup)}</p>
                  <small>
                    Com base nas respostas que você compartilhou.
                  </small>
                </section>
              </section>

              <section className="test-card">
                <div>
                  <h2>Teste por 15 dias</h2>
                  <p>
                    Solicite um teste desta solução. A empresa receberá seu pedido após sua
                    autorização.
                  </p>
                </div>
                <label className="consent-row">
                  <input
                    id="consent"
                    type="checkbox"
                    checked={consent}
                    onChange={(event) => {
                      setConsent(event.target.checked);
                      setConsentError("");
                    }}
                  />
                  <span>
                    Autorizo compartilhar este pedido com a empresa para iniciar o teste.
                  </span>
                </label>
                <div className="test-actions">
                  <span className="form-error" role="alert">
                    {consentError}
                  </span>
                  <button
                    className="primary-button"
                    type="button"
                    disabled={!consent || requesting}
                    onClick={solicitarTeste}
                  >
                    {requesting ? "Solicitando..." : "Solicitar teste de 15 dias →"}
                  </button>
                </div>
              </section>
            </div>
          ) : null}
        </main>
      </div>
    </>
  );
}
