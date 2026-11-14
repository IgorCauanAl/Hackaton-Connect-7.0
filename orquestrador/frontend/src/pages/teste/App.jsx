import { useEffect, useState } from "react";

import LojistaSidebar from "../../components/LojistaSidebar.jsx";
import { queryParam } from "../../lib/format.js";
import { backendGet, orchestrate, unwrap } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

function FeedbackCard({ feedback }) {
  return (
    <section className="feedback-card">
      <header className="feedback-heading">
        <div>
          <h2>Avaliação do lojista</h2>
          <p>Exemplo preenchido para esta demonstração</p>
        </div>
        <span className="status-badge complete">Avaliação concluída</span>
      </header>
      <div className="feedback-grid">
        <div className="feedback-item">
          <span>A solução atendeu à necessidade?</span>
          <strong>{feedback.respostas?.resolveu_dor === "sim" ? "Sim" : "Não"}</strong>
        </div>
        <div className="feedback-item">
          <span>Facilidade de utilização</span>
          <strong>{feedback.respostas?.facilidade_de_uso || feedback.nota}/5</strong>
        </div>
        <div className="feedback-item">
          <span>Impacto percebido</span>
          <strong>Positivo</strong>
        </div>
        <div className="feedback-item">
          <span>Recomendaria a solução?</span>
          <strong>{feedback.respostas?.continuaria_usando === "sim" ? "Sim" : "Não"}</strong>
        </div>
      </div>
      <div className="comment-box">
        <span>O que o lojista comentou</span>
        <blockquote>{feedback.comentario}</blockquote>
        <small>Registrado como demonstração</small>
      </div>
    </section>
  );
}

export default function App() {
  const [actor] = useState(readActor);
  const [testId] = useState(() => Number(queryParam("teste_id")));
  const [test, setTest] = useState(null);
  const [startup, setStartup] = useState(null);
  const [demand, setDemand] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [concluding, setConcluding] = useState(false);

  useEffect(() => {
    if (!actor || actor.perfil !== "lojista" || !Number.isInteger(actor.id)) {
      window.location.replace("/");
      return;
    }
    if (!Number.isInteger(testId) || testId < 1) {
      setLoading(false);
      setError("Identificador de teste inválido.");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        const teste = await backendGet(`/api/testes/${testId}`, actor);
        const [startupCarregada, demanda, feedbacks] = await Promise.all([
          backendGet(`/api/startups/${teste.startup_id}`, actor),
          backendGet(`/api/demandas/${teste.demanda_id}`, actor),
          backendGet("/api/feedbacks", actor),
        ]);
        if (!ativo) return;
        setTest(teste);
        setStartup(startupCarregada);
        setDemand(demanda);
        const encontrado = Array.isArray(feedbacks)
          ? feedbacks.find((item) => item.teste_id === testId)
          : null;
        setFeedback(encontrado || null);
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
  }, [actor, testId]);

  async function concluirDemo() {
    setConcluding(true);
    setActionError("");
    try {
      const envelope = await orchestrate(`/testes/${testId}/feedback`, {
        method: "POST",
        actor,
      });
      const resultado = unwrap(envelope);
      if (!resultado || typeof resultado !== "object") {
        throw new Error("O feedback não retornou um registro válido.");
      }
      setFeedback(resultado);
      setTest((atual) => (atual ? { ...atual, status: "concluido" } : atual));
    } catch (falha) {
      setActionError(falha.message || String(falha));
      setConcluding(false);
    }
  }

  if (!actor || actor.perfil !== "lojista") return null;

  const concluded = test?.status === "concluido";
  const resultsUrl = `/resultados.html?demanda_id=${encodeURIComponent(test?.demanda_id ?? "")}`;
  const solutionUrl = `/solucao.html?demanda_id=${encodeURIComponent(
    test?.demanda_id ?? "",
  )}&startup_id=${encodeURIComponent(test?.startup_id ?? "")}`;

  return (
    <>
      <LojistaSidebar active="chat" name={actor.nome} />

      <div className="app-area">
        <header className="topbar">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/">Início</a>
            <span>›</span>
            <a href="/chat.html">Encontrar soluções</a>
            <span>›</span>
            <strong>Avaliação do teste</strong>
          </nav>
        </header>

        <main className="page-content">
          <a className="back-link" href={test ? resultsUrl : "/chat.html"}>
            ← Voltar aos resultados
          </a>

          {error ? (
            <div className="page-error" role="alert">
              {error}
            </div>
          ) : null}
          {loading ? (
            <div className="loading-state" role="status">
              Carregando teste...
            </div>
          ) : null}

          {!loading && !error && test ? (
            <div>
              <section className="test-summary">
                <div className="summary-heading">
                  <div>
                    <div className="title-line">
                      <h1>Avaliação do teste</h1>
                      <span
                        className={`status-badge${concluded ? " complete" : " pending"}`}
                      >
                        {concluded ? "Teste concluído" : "Teste solicitado"}
                      </span>
                    </div>
                    <p>
                      {concluded
                        ? "Período de demonstração encerrado; confira a avaliação registrada."
                        : "Teste solicitado. O pedido foi enviado à empresa."}
                    </p>
                  </div>
                  <span className="demo-badge">Demonstração</span>
                </div>
                <div className="summary-grid">
                  <div>
                    <span className="metric-label">Empresa</span>
                    <strong>{startup?.nome || "Empresa"}</strong>
                    <small>{startup?.descricao || ""}</small>
                  </div>
                  <div>
                    <span className="metric-label">Oportunidade</span>
                    <strong>{demand?.titulo || "Necessidade comercial"}</strong>
                    <small>Compartilhada com autorização do lojista</small>
                  </div>
                  <div>
                    <span className="metric-label">Duração</span>
                    <strong>{test.dias} dias</strong>
                    <small>Prazo previsto: {test.fim_previsto}</small>
                  </div>
                </div>
              </section>

              {feedback ? <FeedbackCard feedback={feedback} /> : null}

              {!feedback ? (
                <section className="pending-card">
                  <h2>Período de teste em andamento</h2>
                  <p>
                    O teste foi solicitado e ficará registrado por{" "}
                    <strong>{test.dias} dias</strong>.
                  </p>
                  <div className="demo-notice">
                    Esta ação encerra o teste agora e registra uma avaliação de exemplo.
                  </div>
                  <button
                    className="primary-button"
                    type="button"
                    disabled={concluding}
                    onClick={concluirDemo}
                  >
                    {concluding ? "Finalizando..." : "Finalizar demonstração"}
                  </button>
                  <p className="action-error" role="alert">
                    {actionError}
                  </p>
                </section>
              ) : null}

              <div className="bottom-actions">
                <a className="secondary-link" href={resultsUrl}>
                  Voltar às soluções
                </a>
                <a className="primary-link" href="/chat.html">
                  Registrar outra necessidade
                </a>
              </div>
            </div>
          ) : null}
        </main>
      </div>
    </>
  );
}
