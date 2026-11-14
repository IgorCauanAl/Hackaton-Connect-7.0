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
      topbar={
        <>
          Demandas <span className="crumb-separator">›</span> Curadoria
        </>
      }
    >
      <div className="admin-page-heading heading-with-action">
        <div>
          <h1>Demandas</h1>
          <p>Analise e encaminhe necessidades comerciais</p>
        </div>
        <label className="filter-label" htmlFor="status-filter">
          Status
          <select
            id="status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="pendente">Pendentes</option>
            <option value="validada">Validadas</option>
            <option value="encaminhada">Encaminhadas</option>
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
                <th>Lojista</th>
                <th>Segmento</th>
                <th>Necessidade</th>
                <th>Tags</th>
                <th>Status</th>
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
                  <td colSpan="6">Nenhuma demanda encontrada para este filtro.</td>
                </tr>
              ) : null}
              {!loading
                ? demands.map((demand) => (
                    <tr key={demand.id}>
                      <td>{nomes.get(demand.lojista_id) || "Demanda demonstrativa"}</td>
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
                          Analisar
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
