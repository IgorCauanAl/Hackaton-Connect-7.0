const ui = window.adminUi;
const actor = ui.requireAdmin();
const queueBody = document.getElementById("queue-body");

function addMetric(id, value) {
  document.getElementById(id).textContent = String(value ?? 0);
}

async function loadDashboard() {
  if (!actor) return;
  try {
    const [stats, pending, merchants] = await Promise.all([
      ui.api("/api/admin/dashboard"),
      ui.api("/api/admin/demandas?status=pendente"),
      ui.api("/api/lojistas"),
    ]);
    addMetric("metric-lojistas", stats.lojistas);
    addMetric("metric-startups", stats.startups);
    addMetric("metric-demandas", stats.demandas);
    addMetric("metric-oportunidades", stats.oportunidades_identificadas);
    const merchantNames = new Map(merchants.map((merchant) => [merchant.id, merchant.nome]));
    queueBody.replaceChildren();
    if (pending.length === 0) {
      const row = ui.element("tr");
      row.append(ui.element("td", "", "Nenhuma demanda pendente."));
      row.firstElementChild.colSpan = 5;
      queueBody.append(row);
      return;
    }

    for (const demand of pending.slice(0, 8)) {
      const row = ui.element("tr");
      row.append(
        ui.element("td", "", merchantNames.get(demand.lojista_id) || "Demanda demonstrativa"),
        ui.element("td", "", ui.humanize(demand.ramo)),
        ui.element("td", "", demand.titulo || demand.texto),
      );
      const status = ui.element("span", `status-chip status-${demand.status}`, ui.statusLabel(demand.status));
      const statusCell = ui.element("td");
      statusCell.append(status);
      const actionCell = ui.element("td");
      const action = ui.element("a", "table-action", "Analisar");
      action.href = `/admin-demanda.html?id=${encodeURIComponent(demand.id)}`;
      actionCell.append(action);
      row.append(statusCell, actionCell);
      queueBody.append(row);
    }
  } catch (error) {
    ui.showError(error);
    queueBody.replaceChildren();
  }
}

loadDashboard();
