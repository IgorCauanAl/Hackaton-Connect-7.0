import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { StatusChip } from "../../components/Tags.jsx";
import { humanize } from "../../lib/format.js";
import { backendGet } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

export default function App() {
  const [actor] = useState(readActor);
  const [stats, setStats] = useState(null);
  const [pending, setPending] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!actor || actor.perfil !== "admin") {
      window.location.replace("/");
      return;
    }

    let ativo = true;

    async function carregar() {
      try {
        const [dashboard, fila, lojistas] = await Promise.all([
          backendGet("/api/admin/dashboard", actor),
          backendGet("/api/admin/demandas?status=pendente", actor),
          backendGet("/api/lojistas", actor),
        ]);
        if (!ativo) return;
        setStats(dashboard);
        setPending(Array.isArray(fila) ? fila : []);
        setMerchants(Array.isArray(lojistas) ? lojistas : []);
      } catch (falha) {
        if (ativo) setError(falha.message || String(falha));
      }
    }

    carregar();
    return () => {
      ativo = false;
    };
  }, [actor]);

  if (!actor || actor.perfil !== "admin") return null;

  const nomes = new Map(merchants.map((merchant) => [merchant.id, merchant.nome]));

  return (
    <AdminShell active="admin" topbar="Visão geral">
      <div className="admin-page-heading">
        <h1>Painel da associação</h1>
        <p>Acompanhe as demandas do varejo</p>
      </div>

      <AdminError message={error} />

      <section className="metric-grid" aria-label="Indicadores">
        <article className="metric-card">
          <span>Lojistas</span>
          <strong>{stats?.lojistas ?? "—"}</strong>
          <small>Ativos na plataforma</small>
        </article>
        <article className="metric-card">
          <span>Startups</span>
          <strong>{stats?.startups ?? "—"}</strong>
          <small>Cadastradas e aptas</small>
        </article>
        <article className="metric-card">
          <span>Demandas</span>
          <strong>{stats?.demandas ?? "—"}</strong>
          <small>Registradas no ciclo</small>
        </article>
        <article className="metric-card">
          <span>Oportunidades</span>
          <strong>{stats?.oportunidades_identificadas ?? "—"}</strong>
          <small>Matches identificados</small>
        </article>
      </section>

      <section className="admin-panel">
        <header className="panel-heading">
          <div>
            <h2>Fila de curadoria</h2>
            <p>Demandas aguardando validação e triagem</p>
          </div>
          <a href="/admin-demandas.html">Ver todas →</a>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lojista</th>
                <th>Segmento</th>
                <th>Necessidade</th>
                <th>Status</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {stats === null && !error ? (
                <tr>
                  <td colSpan="5">Carregando demandas...</td>
                </tr>
              ) : null}
              {stats !== null && pending.length === 0 ? (
                <tr>
                  <td colSpan="5">Nenhuma demanda pendente.</td>
                </tr>
              ) : null}
              {pending.slice(0, 8).map((demand) => (
                <tr key={demand.id}>
                  <td>{nomes.get(demand.lojista_id) || "Demanda demonstrativa"}</td>
                  <td>{humanize(demand.ramo)}</td>
                  <td>{demand.titulo || demand.texto}</td>
                  <td>
                    <StatusChip status={demand.status} />
                  </td>
                  <td>
                    <a
                      className="table-action"
                      href={`/admin-demanda.html?id=${encodeURIComponent(demand.id)}`}
                    >
                      Analisar
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AdminShell>
  );
}
