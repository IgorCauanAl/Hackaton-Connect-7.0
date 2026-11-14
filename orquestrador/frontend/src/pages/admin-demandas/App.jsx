import { useEffect, useState } from "react";

import { AdminError, AdminShell } from "../../components/AdminShell.jsx";
import { StatusChip } from "../../components/Tags.jsx";
import { humanize } from "../../lib/format.js";
import { backendGet } from "../../lib/http.js";
import { readActor } from "../../lib/session.js";

export default function App() {
  const [actor] = useState(readActor);
  const [status, setStatus] = useState("pendente");
  const [demands, setDemands] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!actor || actor.perfil !== "admin") {
      window.location.replace("/");
      return;
    }

    let ativo = true;

    async function carregar() {
      setLoading(true);
      setError("");
      const query = status ? `?status=${encodeURIComponent(status)}` : "?status=";
      try {
        const [fila, lojistas] = await Promise.all([
          backendGet(`/api/admin/demandas${query}`, actor),
          backendGet("/api/lojistas", actor),
        ]);
        if (!ativo) return;
        setDemands(Array.isArray(fila) ? fila : []);
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
  }, [actor, status]);

  if (!actor || actor.perfil !== "admin") return null;

  const nomes = new Map(merchants.map((merchant) => [merchant.id, merchant.nome]));

  return (
    <AdminShell
      active="demandas"
      topbar={<>Solicitações <span className="crumb-separator">›</span> Revisão</>}
    >
      <div className="admin-page-heading heading-with-action">
        <div>
          <h1>Solicitações das lojas</h1>
          <p>Entenda cada necessidade e indique quem pode ajudar.</p>
        </div>
        <label className="filter-label" htmlFor="status-filter">
          Mostrar
          <select
            id="status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="pendente">Aguardando análise</option>
            <option value="validada">Analisadas</option>
            <option value="encaminhada">Enviadas à startup</option>
            <option value="">Todas</option>
          </select>
        </label>
      </div>

      <AdminError message={error} />

      <section className="admin-panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Loja</th>
                <th>Ramo do negócio</th>
                <th>Necessidade</th>
                <th>Assuntos relacionados</th>
                <th>Etapa</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6">Carregando demandas...</td>
                </tr>
              ) : null}
              {!loading && demands.length === 0 ? (
                <tr>
                  <td colSpan="6">Nenhuma solicitação encontrada.</td>
                </tr>
              ) : null}
              {!loading
                ? demands.map((demand) => (
                    <tr key={demand.id}>
                      <td>{nomes.get(demand.lojista_id) || "Loja demonstrativa"}</td>
                      <td>{humanize(demand.ramo)}</td>
                      <td>{demand.titulo || demand.texto}</td>
                      <td>
                        {(demand.tags || []).slice(0, 3).map((tag) => (
                          <span className="tag-chip" key={tag}>
                            {humanize(tag)}
                          </span>
                        ))}
                      </td>
                      <td>
                        <StatusChip status={demand.status} />
                      </td>
                      <td>
                        <a
                          className="table-action"
                          href={`/admin-demanda.html?id=${encodeURIComponent(demand.id)}`}
                        >
                          Ver solicitação
                        </a>
                      </td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </section>
    </AdminShell>
  );
}
