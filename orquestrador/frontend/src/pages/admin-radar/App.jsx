import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { humanize } from "../../lib/format.js";
import { backendGet, orchestrate, unwrap } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

export default function App() {
  const [actor] = useState(readActor);
  const [radar, setRadar] = useState([]);
  const [warning, setWarning] = useState("");
  const [error, setError] = useState("");
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
        const envelope = await orchestrate("/radar", { actor });
        const resultado = unwrap(envelope) || {};
        if (!ativo) return;
        setRadar(Array.isArray(resultado.radar) ? resultado.radar : []);
        setWarning(resultado.aviso || "");
      } catch (falha) {
        if (ativo) setError(falha.message || String(falha));
      }
    }

    carregar();
    return () => {
      ativo = false;
    };
  }, [actor]);

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

  const [first, ...others] = radar;

  return (
    <AdminShell
      active="radar"
      topbar={
        <>
          Oportunidades <span className="crumb-separator">›</span> Radar de oportunidades
        </>
      }
    >
      <div className="admin-page-heading">
        <h1>Radar de oportunidades</h1>
        <p>Necessidades recorrentes do varejo</p>
      </div>

      <AdminError message={error} />

      {first ? (
        <div className="radar-highlight">
          <p className="highlight-label">1º lugar · Maior recorrência</p>
          <h2>{first.titulo}</h2>
          <p className="radar-stat">
            {first.quantidade} demandas relacionadas · pontuação {first.pontuacao}/100
          </p>
          <p>{first.sugestao}</p>
          <p>{warning || "Interpretação sugerida; requer validação humana."}</p>
          <button type="button" onClick={() => abrirRelacionadas(first)}>
            Ver demandas relacionadas ({first.quantidade}) →
          </button>
        </div>
      ) : null}

      <section className="radar-grid" aria-label="Oportunidades mapeadas">
        {!first && !error ? (
          <p className="admin-empty">
            Nenhuma oportunidade mapeada. Gere os insights na página Análise de padrões.
          </p>
        ) : null}
        {others.map((item) => (
          <article className="radar-card" key={item.grupo_id}>
            <h2>{item.titulo}</h2>
            <small>
              {item.quantidade} demandas · pontuação {item.pontuacao}/100
            </small>
            <p>{item.sugestao}</p>
            <button type="button" onClick={() => abrirRelacionadas(item)}>
              Ver demandas relacionadas →
            </button>
          </article>
        ))}
      </section>

      {related ? (
        <section className="admin-panel related-panel">
          <header className="panel-heading">
            <div>
              <h2>Demandas relacionadas · {related.titulo}</h2>
              <p>Demandas associadas a esta oportunidade</p>
            </div>
            <button
              className="text-button"
              type="button"
              onClick={() => {
                setRelated(null);
                setRelatedDemands([]);
              }}
            >
              Fechar
            </button>
          </header>
          <div>
            {relatedLoading ? (
              <p className="admin-empty">Carregando demandas relacionadas...</p>
            ) : null}
            {!relatedLoading && relatedDemands.length === 0 ? (
              <p className="admin-empty">Nenhuma demanda associada.</p>
            ) : null}
            {relatedDemands.map((demand) => (
              <div className="related-demand" key={demand.id}>
                <span>
                  #{demand.id} · {demand.titulo} · {humanize(demand.ramo)}
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
