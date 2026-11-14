import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { StatusChip, TagList, TagOriginBadge } from "../../components/Tags.jsx";
import { humanize, queryParam } from "../../lib/format.js";
import { backendGet, orchestrate } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

const ANSWER_LABELS = {
  objetivo: "O que a loja quer melhorar",
  dificuldade: "Principal dificuldade",
  canais: "Onde a loja vende",
  ferramentas: "Ferramentas que já usa",
  orcamento: "Valor disponível por mês",
  urgencia: "Quando precisa da solução",
};

export default function App() {
  const [actor] = useState(readActor);
  const [demandId] = useState(() => Number(queryParam("id")));
  const [demand, setDemand] = useState(null);
  const [merchants, setMerchants] = useState([]);
  const [selectedStartup, setSelectedStartup] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!actor || actor.perfil !== "admin") {
      window.location.replace("/");
      return;
    }
    if (!Number.isInteger(demandId) || demandId < 1) {
      setLoading(false);
      setError("Não conseguimos abrir este pedido. Volte à lista e tente novamente.");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        const [detalhe, lojistas] = await Promise.all([
          backendGet(`/api/admin/demandas/${demandId}`, actor),
          backendGet("/api/lojistas", actor),
        ]);
        if (!ativo) return;
        setDemand(detalhe);
        setMerchants(Array.isArray(lojistas) ? lojistas : []);
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

  async function recarregar() {
    const detalhe = await backendGet(`/api/admin/demandas/${demandId}`, actor);
    setDemand(detalhe);
  }

  async function validar() {
    setBusy(true);
    setError("");
    try {
      await orchestrate(`/demandas/${demandId}/validar`, { method: "POST", actor });
      setActionMessage("Solicitação confirmada.");
      await recarregar();
    } catch (falha) {
      setError(falha.message || String(falha));
    } finally {
      setBusy(false);
    }
  }

  async function encaminhar() {
    const startupId = Number(selectedStartup);
    if (!Number.isInteger(startupId) || startupId < 1) {
      setActionMessage("Escolha uma empresa para receber este pedido.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const envelope = await orchestrate(`/demandas/${demandId}/encaminhar`, {
        method: "POST",
        actor,
        body: { startup_id: startupId },
      });
      const resultado = envelope?.resultado || {};
      setActionMessage(
        Number.isInteger(resultado.relatorio_id)
          ? `Relatório #${resultado.relatorio_id} encaminhado.`
          : "Oportunidade encaminhada.",
      );
      await recarregar();
    } catch (falha) {
      setError(falha.message || String(falha));
    } finally {
      setBusy(false);
    }
  }

  if (!actor || actor.perfil !== "admin") return null;

  const merchant = demand
    ? merchants.find((item) => item.id === demand.lojista_id)
    : null;
  const matching = Array.isArray(demand?.matching) ? demand.matching : [];
  const answers = demand?.respostas || {};
  const semStatus = demand?.status;

  return (
    <AdminShell
      active="demandas"
      topbar={
        <>
          <a href="/admin-demandas.html">Solicitações</a>
          <span className="crumb-separator">›</span> Detalhes
        </>
      }
    >
      <a className="admin-back-link" href="/admin-demandas.html">
        ← Voltar às solicitações
      </a>
      <div className="admin-page-heading">
        <h1>Detalhes da solicitação</h1>
        <p>Entenda o que a loja precisa e escolha como ajudar.</p>
      </div>

      <AdminError message={error} />

      {loading ? (
        <div className="admin-loading" role="status">
          Carregando demanda...
        </div>
      ) : null}

      {!loading && demand ? (
        <div>
          <section className="demand-summary">
            <div>
              <span className="field-label">Loja</span>
              <strong>{merchant?.nome || "Loja demonstrativa"}</strong>
            </div>
            <div>
              <span className="field-label">Ramo do negócio</span>
              <strong>{humanize(demand.ramo)}</strong>
            </div>
            <div>
              <span className="field-label">Número da solicitação</span>
              <strong>{`#${String(demand.id).padStart(4, "0")}`}</strong>
            </div>
            <div>
              <span className="field-label">Status</span>
              <StatusChip status={demand.status} />
            </div>
          </section>

          <section className="admin-detail-grid">
            <article className="admin-panel">
              <header className="panel-heading">
                <div>
                  <h2>Respostas da loja</h2>
                  <p>Informações compartilhadas no pedido de ajuda</p>
                </div>
              </header>
              <div className="answer-grid">
                {Object.entries(ANSWER_LABELS).map(([key, label]) =>
                  answers[key] !== undefined ? (
                    <div className="answer-item" key={key}>
                      <span>{label}</span>
                      <strong>{humanize(answers[key])}</strong>
                    </div>
                  ) : null,
                )}
                {Object.keys(answers).length === 0 ? (
                  <div className="answer-item">
                    <span>Respostas</span>
                    <strong>Informação não disponível para este pedido.</strong>
                  </div>
                ) : null}
              </div>
            </article>

            <article className="admin-panel tags-panel">
              <header className="panel-heading">
                <div>
                  <h2>Assuntos relacionados</h2>
                  <p>Temas que ajudam a entender o pedido</p>
                </div>
              </header>
              <TagOriginBadge origin={demand.tags_origem} />
              <TagList tags={demand.tags} className="admin-tags" />
              <p className="panel-note">
                Assuntos sugeridos a partir das respostas.
              </p>
            </article>
          </section>

          <section className="admin-panel description-panel">
            <header className="panel-heading">
              <div>
                <h2>Descrição da necessidade</h2>
                <p>Relato do lojista</p>
              </div>
            </header>
            <blockquote>{demand.texto || demand.titulo || ""}</blockquote>
          </section>

          <section className="admin-panel matches-panel">
            <header className="panel-heading">
              <div>
                <h2>Soluções que podem ajudar</h2>
                <p>
                  Empresas que oferecem soluções para esta necessidade
                </p>
              </div>
            </header>
            <div>
              {matching.length === 0 ? (
                <p className="admin-empty">
                  Ainda não encontramos uma empresa que atenda a esta necessidade.
                </p>
              ) : null}
              {matching.map((match, index) => (
                <article className="match-item" key={match.startup_id}>
                  <strong>
                    {index + 1}º · {match.nome}
                  </strong>
                  <span>{match.indice}/100</span>
                  <p>{match.motivo || "Esta empresa pode ajudar com a necessidade informada."}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="admin-panel action-panel">
            <header className="panel-heading">
              <div>
                <h2>Próximos passos</h2>
                <p>Confirme o pedido antes de enviá-lo à empresa escolhida.</p>
              </div>
            </header>
            <div className="action-controls">
              {semStatus === "pendente" ? (
                <button
                  className="admin-button"
                  type="button"
                  disabled={busy}
                  onClick={validar}
                >
                  Confirmar solicitação
                </button>
              ) : null}

              {semStatus === "validada" && matching.length > 0 ? (
                <>
                  <label htmlFor="startup-select">
                    Empresa que pode ajudar
                    <select
                      id="startup-select"
                      value={selectedStartup}
                      onChange={(event) => setSelectedStartup(event.target.value)}
                    >
                      <option value="">Escolha uma empresa</option>
                      {matching.map((match) => (
                        <option key={match.startup_id} value={match.startup_id}>
                          {match.nome} — {match.indice}% de aderência
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="admin-button"
                    type="button"
                    disabled={busy}
                    onClick={encaminhar}
                  >
                    Enviar solicitação
                  </button>
                </>
              ) : null}

              <span className="action-message" role="status">
                {semStatus === "encaminhada"
                  ? "Esta solicitação já foi enviada à empresa."
                  : semStatus === "validada" && matching.length === 0
                    ? "Solicitação confirmada; ainda não há uma empresa indicada."
                    : actionMessage}
              </span>
            </div>
          </section>

          <section className="admin-panel">
            <header className="panel-heading">
              <div>
                <h2>O que aconteceu</h2>
                <p>Acompanhe as etapas deste pedido.</p>
              </div>
            </header>
            <ol className="history-list">
              {(demand.historico || []).map((entry, index) => (
                <li key={`${entry.evento}-${index}`}>
                  <strong>{humanize(entry.evento)}</strong> — {entry.detalhe}
                </li>
              ))}
            </ol>
          </section>
        </div>
      ) : null}
    </AdminShell>
  );
}
