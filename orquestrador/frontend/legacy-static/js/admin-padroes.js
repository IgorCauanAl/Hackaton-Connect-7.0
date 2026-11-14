const ui = window.adminUi;
const actor = ui.requireAdmin();
const patternGrid = document.getElementById("pattern-grid");
const mcpResults = document.getElementById("mcp-results");
const generateButton = document.getElementById("generate-insights");
let radarItems = [];

function renderPatterns(items) {
  patternGrid.replaceChildren();
  if (!items.length) {
    patternGrid.append(ui.element("p", "admin-empty", "Ainda não há padrões gerados. Selecione “Gerar insights” para analisar demandas validadas."));
    document.getElementById("insight-count").textContent = "Nenhum padrão disponível";
    document.getElementById("insight-origin").textContent = "";
    return;
  }

  document.getElementById("insight-count").textContent = `${items.length} padrões recorrentes detectados`;
  document.getElementById("insight-origin").textContent = items.some((item) => item.origem === "referencia")
    ? "Interpretações de referência (modo de contingência)"
    : "Interpretações sugeridas pela IA; exigem validação humana";
  for (const item of items) {
    const card = ui.element("article", "pattern-card");
    card.append(
      ui.element("h2", "", item.titulo),
      ui.element("div", "pattern-count", String(item.quantidade)),
      ui.element("small", "", "demandas validadas"),
    );
    const analysis = ui.element("section", "pattern-analysis");
    analysis.append(
      ui.element("strong", "", item.origem === "ia" ? "Análise da IA" : "Sugestão de referência — IA indisponível"),
      ui.element("p", "", item.sugestao),
    );
    card.append(analysis);
    const button = ui.element("button", "", "Ver demandas relacionadas →");
    button.type = "button";
    button.addEventListener("click", () => loadRelated(item));
    card.append(button);
    patternGrid.append(card);
  }
}

function renderMcpResults(items, mcpRadar, startupResults, radarError) {
  mcpResults.replaceChildren();
  if (radarError) {
    const row = ui.element("tr");
    const cell = ui.element("td", "", `Falha ao consultar o radar MCP: ${radarError}`);
    cell.colSpan = 5;
    row.append(cell);
    mcpResults.append(row);
    return;
  }
  if (!items.length || !mcpRadar.length) {
    const row = ui.element("tr");
    const cell = ui.element("td", "", "O MCP não retornou padrões ativos. Gere os insights para atualizar o radar.");
    cell.colSpan = 5;
    row.append(cell);
    mcpResults.append(row);
    return;
  }

  for (const item of items) {
    const mcpItem = mcpRadar.find((entry) => entry.tag === item.tag);
    const result = startupResults.get(item.grupo_id);
    const row = ui.element("tr");
    row.append(
      ui.element("td", "", `${item.titulo} · ${item.tag || "sem tag"}`),
      ui.element("td", "", mcpItem ? String(mcpItem.quantidade) : "Não retornado"),
    );

    let startupText = "Nenhuma startup encontrada para esta tag.";
    if (result?.error) startupText = `Falha na consulta: ${result.error}`;
    else if (result?.items.length) {
      startupText = result.items.map((startup) => `${startup.nome}: ${startup.solucao || startup.descricao}`).join(" · ");
    }
    row.append(ui.element("td", "", startupText));
    row.append(ui.element("td", "", mcpItem?.sugestao_ia || "Sem sugestão retornada pelo MCP."));
    row.append(ui.element("td", "", mcpItem?.origem === "ia" ? "IA" : mcpItem ? "Referência" : "Não informado"));
    mcpResults.append(row);
  }
}

async function loadMcpResults(items) {
  let mcpRadar;
  try {
    mcpRadar = await ui.api("/api/mcp/radar");
  } catch (error) {
    renderMcpResults(items, [], new Map(), error.message);
    return;
  }

  const startupEntries = await Promise.all(items.map(async (item) => {
    if (!item.tag) return [item.grupo_id, { items: [], error: "O padrão não possui uma tag para consulta." }];
    try {
      const results = await ui.api(`/api/mcp/startups?tag=${encodeURIComponent(item.tag)}`);
      return [item.grupo_id, { items: results, error: "" }];
    } catch (error) {
      return [item.grupo_id, { items: [], error: error.message }];
    }
  }));
  renderMcpResults(items, mcpRadar, new Map(startupEntries), "");
}

async function loadPatterns() {
  if (!actor) return;
  try {
    const result = await ui.api("/api/admin/radar");
    radarItems = result.radar || [];
    renderPatterns(radarItems);
    await loadMcpResults(radarItems);
  } catch (error) {
    ui.showError(error);
  }
}

async function loadRelated(item) {
  try {
    const demands = await ui.api(`/api/admin/radar/${item.grupo_id}/demandas`);
    document.getElementById("related-title").textContent = `Demandas relacionadas · ${item.titulo}`;
    const list = document.getElementById("related-list");
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
    document.getElementById("related-panel").hidden = false;
  } catch (error) {
    ui.showError(error);
  }
}

generateButton.addEventListener("click", async () => {
  generateButton.disabled = true;
  generateButton.textContent = "Analisando...";
  try {
    const result = await ui.api("/api/admin/insights/gerar", { method: "POST" });
    radarItems = result.radar || [];
    renderPatterns(radarItems);
    await loadMcpResults(radarItems);
  } catch (error) {
    ui.showError(error);
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "ϟ Gerar insights";
  }
});

document.getElementById("close-related").addEventListener("click", () => {
  document.getElementById("related-panel").hidden = true;
});

loadPatterns();
