const ui = window.adminUi;
const actor = ui.requireAdmin();
const highlight = document.getElementById("radar-highlight");
const grid = document.getElementById("radar-grid");

function showRelated(item) {
  ui.api(`/api/admin/radar/${item.grupo_id}/demandas`).then((demands) => {
    const panel = document.getElementById("radar-related");
    document.getElementById("radar-related-title").textContent = `Demandas relacionadas · ${item.titulo}`;
    const list = document.getElementById("radar-related-list");
    list.replaceChildren();
    if (!demands.length) list.append(ui.element("p", "admin-empty", "Nenhuma demanda associada."));
    for (const demand of demands) {
      const row = ui.element("div", "related-demand");
      row.append(ui.element("span", "", `#${demand.id} · ${demand.titulo} · ${ui.humanize(demand.ramo)}`));
      const link = ui.element("a", "", "Abrir");
      link.href = `/admin-demanda.html?id=${encodeURIComponent(demand.id)}`;
      row.append(link);
      list.append(row);
    }
    panel.hidden = false;
  }).catch(ui.showError);
}

function renderRadar(items, warning) {
  grid.replaceChildren();
  highlight.hidden = true;
  if (!items.length) {
    grid.append(ui.element("p", "admin-empty", "Nenhuma oportunidade mapeada. Gere os insights na página Análise de padrões."));
    return;
  }

  const [first, ...others] = items;
  highlight.append(
    ui.element("p", "highlight-label", "1º lugar · Maior recorrência"),
    ui.element("h2", "", first.titulo),
    ui.element("p", "radar-stat", `${first.quantidade} demandas relacionadas · pontuação ${first.pontuacao}/100`),
    ui.element("p", "", first.sugestao),
    ui.element("p", "", warning || "Interpretação sugerida; requer validação humana."),
  );
  const primaryButton = ui.element("button", "", `Ver demandas relacionadas (${first.quantidade}) →`);
  primaryButton.type = "button";
  primaryButton.addEventListener("click", () => showRelated(first));
  highlight.append(primaryButton);
  highlight.hidden = false;

  for (const item of others) {
    const card = ui.element("article", "radar-card");
    card.append(
      ui.element("h2", "", item.titulo),
      ui.element("small", "", `${item.quantidade} demandas · pontuação ${item.pontuacao}/100`),
      ui.element("p", "", item.sugestao),
    );
    const button = ui.element("button", "", "Ver demandas relacionadas →");
    button.type = "button";
    button.addEventListener("click", () => showRelated(item));
    card.append(button);
    grid.append(card);
  }
}

async function initialize() {
  if (!actor) return;
  try {
    const result = await ui.api("/api/admin/radar");
    renderRadar(result.radar || [], result.aviso);
  } catch (error) {
    ui.showError(error);
  }
}

document.getElementById("close-radar-related").addEventListener("click", () => {
  document.getElementById("radar-related").hidden = true;
});

initialize();
