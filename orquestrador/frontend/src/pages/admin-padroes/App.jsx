import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { backendGet, orchestrate, unwrap } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

/**
 * Necessidades recorrentes.
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
    ? "Resumo padrão usado; revise as sugestões antes de compartilhar."
    : patterns.length
      ? "Sugestões automáticas; revise antes de compartilhar."
      : "";

  return (
    <AdminShell
      active="padroes"
      topbar={
        <>
          Solicitações <span className="crumb-separator">›</span> Necessidades frequentes
        </>
      }
    >
      <div className="admin-page-heading heading-with-action">
        <div>
          <h1>O que as lojas mais precisam</h1>
          <p>Veja quais necessidades aparecem com mais frequência.</p>
        </div>
        <button
          className="admin-button"
          id="generate-insights"
          type="button"
          disabled={generating}
          onClick={gerarInsights}
        >
          {generating ? "Atualizando..." : "Atualizar recomendações"}
        </button>
      </div>

      <AdminError message={error} />

      <div className="insight-meta">
        <span id="insight-count">
          {patterns.length
            ? `${patterns.length} necessidades recorrentes`
            : "Ainda não há necessidades recorrentes."}
        </span>
        <span id="insight-origin">{originLabel}</span>
      </div>

      <section
        className="pattern-grid"
        id="pattern-grid"
        aria-label="Necessidades recorrentes"
      >
        {patterns.map((item) => (
          <article className="pattern-card" key={item.grupo_id}>
            <h2>{item.titulo}</h2>
            <div className="pattern-count">{item.quantidade}</div>
            <small>pedidos analisados</small>
            <section className="pattern-analysis">
              <strong>
                {item.origem === "ia"
                  ? "Resumo automático"
                  : "Resumo padrão"}
              </strong>
              <p>{item.sugestao}</p>
            </section>
            <button type="button" onClick={() => abrirRelacionadas(item)}>
              Ver pedidos parecidos →
            </button>
          </article>
        ))}
        {!patterns.length && !error ? (
          <p className="admin-empty">
            Ainda não há necessidades recorrentes. Selecione “Atualizar recomendações” para
            analisar os pedidos já revisados.
          </p>
        ) : null}
      </section>

      <section className="admin-panel mcp-panel">
        <header className="panel-heading">
          <div>
            <h2>Empresas que podem ajudar</h2>
            <p>Possíveis soluções para as necessidades mais frequentes.</p>
          </div>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Necessidade</th>
                <th>Pedidos parecidos</th>
                <th>Empresas encontradas</th>
                <th>Sugestão para a associação</th>
                <th>Resumo</th>
              </tr>
            </thead>
            <tbody id="mcp-results">
              {mcpState.loading ? (
                <tr>
                  <td colSpan="5">Buscando empresas que possam ajudar...</td>
                </tr>
              ) : null}
              {!mcpState.loading && mcpState.error ? (
                <tr>
                  <td colSpan="5">
                    Não foi possível buscar empresas. Atualize as recomendações e tente novamente.
                  </td>
                </tr>
              ) : null}
              {!mcpState.loading && !mcpState.error && mcpState.rows.length === 0 ? (
                <tr>
                  <td colSpan="5">
                    Ainda não encontramos empresas para as necessidades listadas.
                  </td>
                </tr>
              ) : null}
              {!mcpState.loading && !mcpState.error
                ? mcpState.rows.map((row) => (
                    <tr key={row.grupoId}>
                      <td>{row.titulo}</td>
                      <td>{row.mcpItem ? String(row.mcpItem.quantidade) : "Informação indisponível"}</td>
                      <td>
                        {row.startupError
                          ? "Não foi possível carregar as empresas para esta necessidade."
                          : row.startups.length
                            ? row.startups
                                .map(
                                  (startup) =>
                                    `${startup.nome}: ${
                                      startup.solucao || startup.descricao || ""
                                    }`,
                                )
                                .join(" · ")
                            : "Nenhuma empresa encontrada para esta necessidade."}
                      </td>
                      <td>
                        {row.mcpItem?.sugestao_ia ||
                          "Nenhuma sugestão disponível no momento."}
                      </td>
                      <td>
                        {!row.mcpItem
                          ? "Não informado"
                          : row.mcpItem.origem === "ia"
                            ? "Automático"
                            : "Padrão"}
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
              <h2 id="related-title">Pedidos parecidos · {related.titulo}</h2>
              <p>Solicitações que mencionam esta necessidade</p>
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
              <p className="admin-empty">Carregando pedidos parecidos...</p>
            ) : null}
            {!relatedLoading && relatedDemands.length === 0 ? (
              <p className="admin-empty">Nenhum pedido parecido encontrado.</p>
            ) : null}
            {relatedDemands.map((demand) => (
              <div className="related-demand" key={demand.id}>
                <span>
                  Pedido #{demand.id} · {demand.titulo} · {demand.ramo}
                </span>
                <a href={`/admin-demanda.html?id=${encodeURIComponent(demand.id)}`}>
                  Ver pedido
                </a>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </AdminShell>
  );
}
