import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { StatusChip, TagList, TagOriginBadge } from "../../components/Tags.jsx";
import { humanize, queryParam } from "../../lib/format.js";
import { backendGet, orchestrate } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

const ANSWER_LABELS = {
  objetivo: "Objetivo",
  dificuldade: "Principal gargalo",
  canais: "Canais predominantes",
  ferramentas: "Ferramentas atuais",
  orcamento: "Orçamento mensal",
  urgencia: "Prazo esperado",
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
      setError("Identificador de demanda inválido.");
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
      setActionMessage("Demanda validada.");
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
      setActionMessage("Selecione uma startup recomendada.");
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
          <a href="/admin-demandas.html">Demandas</a>
          <span className="crumb-separator">›</span> Detalhes
        </>
      }
    >
      <a className="admin-back-link" href="/admin-demandas.html">
        ← Voltar às demandas
      </a>
      <div className="admin-page-heading">
        <h1>Detalhes da demanda</h1>
        <p>Análise e curadoria técnica da solicitação comercial</p>
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
              <span className="field-label">Lojista</span>
              <strong>{merchant?.nome || "Demanda demonstrativa"}</strong>
            </div>
            <div>
              <span className="field-label">Segmento comercial</span>
              <strong>{humanize(demand.ramo)}</strong>
            </div>
            <div>
              <span className="field-label">Protocolo</span>
              <strong>{`#DEM-${String(demand.id).padStart(4, "0")}`}</strong>
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
                  <h2>Respostas do diagnóstico</h2>
                  <p>Informações fornecidas pelo lojista</p>
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
                    <span>Diagnóstico</span>
                    <strong>Informação não disponível para esta demanda importada.</strong>
                  </div>
                ) : null}
              </div>
            </article>

            <article className="admin-panel tags-panel">
              <header className="panel-heading">
                <div>
                  <h2>Tags identificadas</h2>
                  <p>Classificação da necessidade</p>
                </div>
              </header>
              <TagOriginBadge origin={demand.tags_origem} />
              <TagList tags={demand.tags} className="admin-tags" />
              <p className="panel-note">
                Tags geradas pelo diagnóstico e pelo classificador.
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
                <h2>Resultado do matching</h2>
                <p>
                  Startups aptas identificadas pelo motor de compatibilidade
                </p>
              </div>
            </header>
            <div>
              {matching.length === 0 ? (
                <p className="admin-empty">
                  Nenhuma startup compatível foi identificada.
                </p>
              ) : null}
              {matching.map((match, index) => (
                <article className="match-item" key={match.startup_id}>
                  <strong>
                    {index + 1}º · {match.nome}
                  </strong>
                  <span>{match.indice}/100</span>
                  <p>{match.motivo || "Compatibilidade identificada."}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="admin-panel action-panel">
            <header className="panel-heading">
              <div>
                <h2>Curadoria da associação</h2>
                <p>Valide a demanda antes de encaminhá-la a uma startup</p>
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
                  Validar demanda
                </button>
              ) : null}

              {semStatus === "validada" && matching.length > 0 ? (
                <>
                  <label htmlFor="startup-select">
                    Startup recomendada
                    <select
                      id="startup-select"
                      value={selectedStartup}
                      onChange={(event) => setSelectedStartup(event.target.value)}
                    >
                      <option value="">Selecione uma startup recomendada</option>
                      {matching.map((match) => (
                        <option key={match.startup_id} value={match.startup_id}>
                          {match.nome} — {match.indice}/100
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
                    Encaminhar oportunidade
                  </button>
                </>
              ) : null}

              <span className="action-message" role="status">
                {semStatus === "encaminhada"
                  ? "Demanda já encaminhada à startup."
                  : semStatus === "validada" && matching.length === 0
                    ? "Demanda validada; sem startup compatível para encaminhar."
                    : actionMessage}
              </span>
            </div>
          </section>

          <section className="admin-panel">
            <header className="panel-heading">
              <div>
                <h2>Histórico</h2>
                <p>Etapas registradas para esta demanda</p>
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
