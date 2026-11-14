const ui = window.adminUi;
const actor = ui.requireAdmin();
const statusFilter = document.getElementById("status-filter");
const demandsBody = document.getElementById("demands-body");

async function loadDemands() {
  if (!actor) return;
  const status = statusFilter.value;
  const query = status ? `?status=${encodeURIComponent(status)}` : "?status=";
  try {
    const [demands, merchants] = await Promise.all([
      ui.api(`/api/admin/demandas${query}`),
      ui.api("/api/lojistas"),
    ]);
    const merchantNames = new Map(merchants.map((merchant) => [merchant.id, merchant.nome]));
    demandsBody.replaceChildren();
    if (demands.length === 0) {
      const row = ui.element("tr");
      const cell = ui.element("td", "", "Nenhuma demanda encontrada para este filtro.");
      cell.colSpan = 6;
      row.append(cell);
      demandsBody.append(row);
      return;
    }

    for (const demand of demands) {
      const row = ui.element("tr");
      row.append(
        ui.element("td", "", merchantNames.get(demand.lojista_id) || "Demanda demonstrativa"),
        ui.element("td", "", ui.humanize(demand.ramo)),
        ui.element("td", "", demand.titulo || demand.texto),
      );
      const tagsCell = ui.element("td");
      for (const tag of (demand.tags || []).slice(0, 3)) {
        tagsCell.append(ui.element("span", "tag-chip", ui.humanize(tag)));
      }
      const statusCell = ui.element("td");
      statusCell.append(ui.element("span", `status-chip status-${demand.status}`, ui.statusLabel(demand.status)));
      const actionCell = ui.element("td");
      const action = ui.element("a", "table-action", "Analisar");
      action.href = `/admin-demanda.html?id=${encodeURIComponent(demand.id)}`;
      actionCell.append(action);
      row.append(tagsCell, statusCell, actionCell);
      demandsBody.append(row);
    }
  } catch (error) {
    ui.showError(error);
    demandsBody.replaceChildren();
  }
}

statusFilter.addEventListener("change", loadDemands);
loadDemands();
