import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { backendGet, orchestrate, unwrap } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

/**
 * Análise de padrões.
 *
 * Os padrões (radar) vêm do backend via orquestrador; o orquestrador apenas
 * acrescenta a `tag` do grupo (derivada das demandas reais) para permitir a
 * consulta ao MCP. Nenhum cálculo de quantidade/pontuação é feito aqui.
 */
export default function App() {
  const [actor] = useState(readActor);
  const [patterns, setPatterns] = useState([]);
  const [mcpState, setMcpState] = useState({ loading: true, error: "", rows: [] });
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [related, setRelated] = useState(null);
  const [relatedDemands, setRelatedDemands] = useState([]);
  const [relatedLoading, setRelatedLoading] = useState(false);

  useEffect(() => {
    if (!actor || actor.perfil !== "admin") {
      window.location.replace("/");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        const envelope = await orchestrate("/padroes", { actor });
        const resultado = unwrap(envelope) || {};
        const radar = Array.isArray(resultado.radar) ? resultado.radar : [];
        if (!ativo) return;
        setPatterns(radar);
        await carregarMcp(radar, ativo);
      } catch (falha) {
        if (ativo) {
          setError(falha.message || String(falha));
          setMcpState({ loading: false, error: "", rows: [] });
        }
      }
    }

    carregar();
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actor]);

  async function carregarMcp(radar, ativo = true) {
    setMcpState({ loading: true, error: "", rows: [] });

    let mcpRadar;
    try {
      const envelope = await orchestrate("/mcp/radar", { actor });
      const resultado = unwrap(envelope);
      mcpRadar = Array.isArray(resultado) ? resultado : [];
    } catch (falha) {
      if (ativo) {
        setMcpState({
          loading: false,
          error: falha.message || String(falha),
          rows: [],
        });
      }
      return;
    }

    const rows = await Promise.all(
      radar.map(async (item) => {
        if (!item.tag) {
          return {
            grupoId: item.grupo_id,
            titulo: item.titulo,
            tag: "",
            mcpItem: null,
            startups: [],
            startupError: "O padrão não possui uma tag para consulta.",
            radarError: "",
          };
        }
        try {
          const envelope = await orchestrate(
            `/mcp/startups?tag=${encodeURIComponent(item.tag)}`,
            { actor },
          );
          const resultado = unwrap(envelope);
          return {
            grupoId: item.grupo_id,
            titulo: item.titulo,
            tag: item.tag,
            mcpItem:
              mcpRadar.find((entry) => entry.dor === item.titulo) ||
              mcpRadar.find((entry) => entry.tag === item.tag) ||
              null,
            startups: Array.isArray(resultado) ? resultado : [],
            startupError: "",
            radarError: "",
          };
        } catch (falha) {
          return {
            grupoId: item.grupo_id,
            titulo: item.titulo,
            tag: item.tag,
            mcpItem:
              mcpRadar.find((entry) => entry.dor === item.titulo) ||
              mcpRadar.find((entry) => entry.tag === item.tag) ||
              null,
            startups: [],
            startupError: falha.message || String(falha),
            radarError: "",
          };
        }
      }),
    );

    if (ativo) setMcpState({ loading: false, error: "", rows });
  }

  async function gerarInsights() {
    setGenerating(true);
    setError("");
    try {
      const envelope = await orchestrate("/insights", { method: "POST", actor });
      const resultado = unwrap(envelope) || {};
      const radar = Array.isArray(resultado.radar) ? resultado.radar : [];
      setPatterns(radar);
      await carregarMcp(radar);
    } catch (falha) {
      setError(falha.message || String(falha));
    } finally {
      setGenerating(false);
    }
  }

  async function abrirRelacionadas(item) {
    setRelated(item);
    setRelatedDemands([]);
    setRelatedLoading(true);
    setError("");
    try {
      const demands = await backendGet(
        `/api/admin/radar/${item.grupo_id}/demandas`,
        actor,
      );
      setRelatedDemands(Array.isArray(demands) ? demands : []);
    } catch (falha) {
      setError(falha.message || String(falha));
    } finally {
      setRelatedLoading(false);
    }
  }

  if (!actor || actor.perfil !== "admin") return null;

  const originLabel = patterns.some((item) => item.origem === "referencia")
    ? "Interpretações de referência (modo de contingência)"
    : patterns.length
      ? "Interpretações sugeridas pela IA; exigem validação humana"
      : "";

  return (
    <AdminShell
      active="padroes"
      topbar={
        <>
          Demandas <span className="crumb-separator">›</span> Análise de padrões
        </>
      }
    >
      <div className="admin-page-heading heading-with-action">
        <div>
          <h1>Análise de padrões</h1>
          <p>Identifique necessidades recorrentes no varejo</p>
        </div>
        <button
          className="admin-button"
          id="generate-insights"
          type="button"
          disabled={generating}
          onClick={gerarInsights}
        >
          {generating ? "Analisando..." : "ϟ Gerar insights"}
        </button>
      </div>

      <AdminError message={error} />

      <div className="insight-meta">
        <span id="insight-count">
          {patterns.length
            ? `${patterns.length} padrões recorrentes detectados`
            : "Ainda não há padrões gerados."}
        </span>
        <span id="insight-origin">{originLabel}</span>
      </div>

      <section className="pattern-grid" id="pattern-grid" aria-label="Padrões identificados">
        {patterns.map((item) => (
          <article className="pattern-card" key={item.grupo_id}>
            <h2>{item.titulo}</h2>
            <div className="pattern-count">{item.quantidade}</div>
            <small>demandas validadas</small>
            <section className="pattern-analysis">
              <strong>
                {item.origem === "ia"
                  ? "Análise da IA"
                  : "Sugestão de referência — IA indisponível"}
              </strong>
              <p>{item.sugestao}</p>
            </section>
            <button type="button" onClick={() => abrirRelacionadas(item)}>
              Ver demandas relacionadas →
            </button>
          </article>
        ))}
        {!patterns.length && !error ? (
          <p className="admin-empty">
            Ainda não há padrões gerados. Selecione “Gerar insights” para analisar
            demandas validadas.
          </p>
        ) : null}
      </section>

      <section className="admin-panel mcp-panel">
        <header className="panel-heading">
          <div>
            <h2>Análise dos padrões de problemas dos lojistas</h2>
            <p>Análise da IA e dados complementares retornados pelo MCP</p>
          </div>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Padrão</th>
                <th>Demandas no radar</th>
                <th>Startups retornadas</th>
                <th>Sugestão do radar MCP</th>
                <th>Origem</th>
              </tr>
            </thead>
            <tbody id="mcp-results">
              {mcpState.loading ? (
                <tr>
                  <td colSpan="5">Consultando o MCP...</td>
                </tr>
              ) : null}
              {!mcpState.loading && mcpState.error ? (
                <tr>
                  <td colSpan="5">Falha ao consultar o radar MCP: {mcpState.error}</td>
                </tr>
              ) : null}
              {!mcpState.loading && !mcpState.error && mcpState.rows.length === 0 ? (
                <tr>
                  <td colSpan="5">
                    O MCP não retornou padrões ativos. Gere os insights para
                    atualizar o radar.
                  </td>
                </tr>
              ) : null}
              {!mcpState.loading && !mcpState.error
                ? mcpState.rows.map((row) => (
                    <tr key={row.grupoId}>
                      <td>
                        {row.titulo} · {row.tag || "sem tag"}
                      </td>
                      <td>{row.mcpItem ? String(row.mcpItem.quantidade) : "Não retornado"}</td>
                      <td>
                        {row.startupError
                          ? `Falha na consulta: ${row.startupError}`
                          : row.startups.length
                            ? row.startups
                                .map(
                                  (startup) =>
                                    `${startup.nome}: ${
                                      startup.solucao || startup.descricao || ""
                                    }`,
                                )
                                .join(" · ")
                            : "Nenhuma startup encontrada para esta tag."}
                      </td>
                      <td>
                        {row.mcpItem?.sugestao_ia ||
                          "Sem sugestão retornada pelo MCP."}
                      </td>
                      <td>
                        {!row.mcpItem
                          ? "Não informado"
                          : row.mcpItem.origem === "ia"
                            ? "IA"
                            : "Referência"}
                      </td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </section>

      {related ? (
        <section className="admin-panel related-panel" id="related-panel">
          <header className="panel-heading">
            <div>
              <h2 id="related-title">Demandas relacionadas · {related.titulo}</h2>
              <p>Demandas que formam este padrão</p>
            </div>
            <button
              className="text-button"
              id="close-related"
              type="button"
              onClick={() => {
                setRelated(null);
                setRelatedDemands([]);
              }}
            >
              Fechar
            </button>
          </header>
          <div id="related-list">
            {relatedLoading ? (
              <p className="admin-empty">Carregando demandas relacionadas...</p>
            ) : null}
            {!relatedLoading && relatedDemands.length === 0 ? (
              <p className="admin-empty">Nenhuma demanda associada.</p>
            ) : null}
            {relatedDemands.map((demand) => (
              <div className="related-demand" key={demand.id}>
                <span>
                  #{demand.id} · {demand.titulo} · {demand.ramo}
                </span>
                <a href={`/admin-demanda.html?id=${encodeURIComponent(demand.id)}`}>
                  Abrir
                </a>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </AdminShell>
  );
}
