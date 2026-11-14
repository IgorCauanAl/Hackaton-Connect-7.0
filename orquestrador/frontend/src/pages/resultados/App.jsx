import { useEffect, useState } from "react";

import { CriteriaList } from "../../components/CriteriaList.jsx";
import Icon from "../../components/Icon.jsx";
import LojistaSidebar from "../../components/LojistaSidebar.jsx";
import { composeAssistantAnswer } from "../../lib/assistant.js";
import { backendGet } from "../../lib/http.js";
import { queryParam } from "../../lib/format.js";
import { readActor } from "../../lib/session.js";

const AVISOS_KEY = "orvyn-ultimos-avisos";

function mensagemDeAvisos(avisos) {
  if (!avisos.length) return "";
  const codigos = new Set(avisos.map((aviso) => aviso.codigo));
  if (codigos.has("ia_indisponivel") || codigos.has("classificacao_vazia")) {
    return "A busca automática está temporariamente indisponível. Usamos suas respostas para continuar procurando opções.";
  }
  return avisos.map((aviso) => aviso.detalhe).join(" ");
}

export default function App() {
  const [actor] = useState(readActor);
  const [demandId] = useState(() => Number(queryParam("demanda_id")));
  const [matching, setMatching] = useState(null);
  const [demand, setDemand] = useState(null);
  const [startups, setStartups] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!actor || actor.perfil !== "lojista" || !Number.isInteger(actor.id)) {
      window.location.replace("/");
      return;
    }
    if (!Number.isInteger(demandId) || demandId < 1) {
      setLoading(false);
      setError("Não conseguimos abrir este pedido. Volte às perguntas e tente novamente.");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        try {
          const avisos = JSON.parse(sessionStorage.getItem(AVISOS_KEY) || "[]");
          if (ativo) setNotice(mensagemDeAvisos(Array.isArray(avisos) ? avisos : []));
          sessionStorage.removeItem(AVISOS_KEY);
        } catch {
          sessionStorage.removeItem(AVISOS_KEY);
        }

        const [matchingCarregado, demandaCarregada] = await Promise.all([
          backendGet(`/api/demandas/${demandId}/matching`, actor),
          backendGet(`/api/demandas/${demandId}`, actor),
        ]);
        if (!ativo) return;
        setMatching(matchingCarregado);
        setDemand(demandaCarregada);

        const ranking = Array.isArray(matchingCarregado?.ranking_startups)
          ? matchingCarregado.ranking_startups
          : [];
        const entradas = await Promise.all(
          ranking.map(async (match) => {
            const startup = await backendGet(`/api/startups/${match.startup_id}`, actor);
            return [match.startup_id, startup];
          }),
        );
        if (!ativo) return;
        setStartups(Object.fromEntries(entradas));
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
  }, [actor, demandId]);

  if (!actor || actor.perfil !== "lojista") return null;

  const ranking = Array.isArray(matching?.ranking_startups) ? matching.ranking_startups : [];

  return (
    <>
      <LojistaSidebar active="chat" name={actor.nome} />

      <div className="app-area">
        <header className="topbar">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/" aria-label="Início">
              <Icon name="home" />
            </a>
            <span aria-hidden="true">›</span>
            <a href="/chat.html">Encontrar soluções</a>
            <span aria-hidden="true">›</span>
            <strong>Resultados</strong>
          </nav>
        </header>

        <main className="page-content">
          <a className="back-link" href="/chat.html">
            ← Voltar às perguntas
          </a>
          <div className="page-heading">
            <div>
              <p className="eyebrow">Encontramos opções para você</p>
              <h1>Opções para sua necessidade</h1>
              <p>
                {demand?.titulo || "Confira as soluções encontradas para sua necessidade."}
              </p>
            </div>
          </div>

          {notice ? (
            <div className="inline-notice" role="status">
              {notice}
            </div>
          ) : null}
          {error ? (
            <div className="page-error" role="alert">
              {error}
            </div>
          ) : null}
          {loading ? (
            <div className="loading-state" role="status">
              Carregando resultados...
            </div>
          ) : null}

          {!loading && !error && ranking.length > 0 ? (
            <section className="results-list" aria-label="Soluções recomendadas">
              {ranking.map((match, index) => {
                const startup = startups[match.startup_id] || {};
                return (
                  <article className="solution-card" key={match.startup_id}>
                    <div className="solution-topline">
                      <span className="rank-badge">
                        {index === 0 ? "Nossa principal indicação" : "Outra opção"}
                      </span>
                      <div className="score-box">
                        <strong>{match.indice}</strong>
                        <span>/100 de aderência à sua necessidade</span>
                      </div>
                    </div>

                    <h2>{startup.nome || match.nome || "Empresa de tecnologia"}</h2>
                    <p className="solution-description">
                      {startup.descricao || "Informações da empresa em breve."}
                    </p>

                    <section className="assistant-answer">
                      <strong>Por que indicamos esta opção</strong>
                      <p>{composeAssistantAnswer(demand, match, startup)}</p>
                      <small>
                        Com base no que você contou sobre seu negócio.
                      </small>
                    </section>

                    <div className="solution-offer">
                      <strong>Solução oferecida</strong>
                      <p>
                        {startup.solucao ||
                          startup.descricao ||
                          "Consulte a empresa para mais informações."}
                      </p>
                    </div>

                    <details className="criteria-details">
                      <summary>Veja por que esta opção combina</summary>
                      <CriteriaList criteria={match.criterios} className="criteria-list" />
                    </details>

                    <a
                      className="detail-link"
                      href={`/solucao.html?demanda_id=${encodeURIComponent(demandId)}&startup_id=${encodeURIComponent(match.startup_id)}`}
                    >
                      Conhecer solução e pedir teste
                    </a>
                  </article>
                );
              })}
            </section>
          ) : null}

          {!loading && !error && ranking.length === 0 ? (
            <section className="empty-state">
              <span className="empty-icon" aria-hidden="true">
                <Icon name="search" size={22} />
              </span>
              <h2>Ainda não encontramos uma opção para sua necessidade</h2>
              <p>
                A associação pode ajudar a encontrar uma solução. Você também pode alterar suas
                respostas e tentar novamente.
              </p>
              <a className="primary-link" href="/chat.html">
                Alterar respostas
              </a>
            </section>
          ) : null}
        </main>
      </div>
    </>
  );
}
