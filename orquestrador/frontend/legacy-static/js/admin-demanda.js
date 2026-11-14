const ui = window.adminUi;
const actor = ui.requireAdmin();
const demandContent = document.getElementById("demand-content");
const validateButton = document.getElementById("validate-demand");
const forwardButton = document.getElementById("forward-demand");
const startupWrap = document.getElementById("startup-wrap");
const startupSelect = document.getElementById("startup-select");
const actionMessage = document.getElementById("action-message");
const demandId = Number(new URLSearchParams(window.location.search).get("id"));
let demand;

function addAnswer(label, value) {
  const item = ui.element("div", "answer-item");
  item.append(ui.element("span", "", label), ui.element("strong", "", ui.humanize(value)));
  document.getElementById("answer-grid").append(item);
}

function populateMatches(matches) {
  const container = document.getElementById("match-list");
  container.replaceChildren();
  startupSelect.replaceChildren();
  const placeholder = new Option("Selecione uma startup recomendada", "", true, true);
  placeholder.disabled = true;
  startupSelect.add(placeholder);

  if (!matches.length) {
    container.append(ui.element("p", "admin-empty", "Nenhuma startup compatível foi identificada."));
    return;
  }

  for (const [index, match] of matches.entries()) {
    const item = ui.element("article", "match-item");
    item.append(
      ui.element("strong", "", `${index + 1}º · ${match.nome}`),
      ui.element("span", "", `${match.indice}/100`),
      ui.element("p", "", match.motivo || "Compatibilidade identificada."),
    );
    container.append(item);
    startupSelect.add(new Option(`${match.nome} — ${match.indice}/100`, match.startup_id));
  }
}

function setActions() {
  const status = demand.status;
  validateButton.hidden = status !== "pendente";
  startupWrap.hidden = status !== "validada" || demand.matching.length === 0;
  forwardButton.hidden = status !== "validada" || demand.matching.length === 0;
  if (status === "encaminhada") actionMessage.textContent = "Demanda já encaminhada à startup.";
  else if (status === "validada" && demand.matching.length === 0) actionMessage.textContent = "Demanda validada; sem startup compatível para encaminhar.";
  else actionMessage.textContent = "";
}

async function loadDemand() {
  if (!actor) return;
  if (!Number.isInteger(demandId) || demandId < 1) {
    ui.showError(new Error("Identificador de demanda inválido."));
    document.getElementById("admin-loading").hidden = true;
    return;
  }
  try {
    const [details, merchants] = await Promise.all([
      ui.api(`/api/admin/demandas/${demandId}`),
      ui.api("/api/lojistas"),
    ]);
    demand = details;
    const merchant = merchants.find((item) => item.id === demand.lojista_id);
    document.getElementById("demand-merchant").textContent = merchant?.nome || "Demanda demonstrativa";
    document.getElementById("demand-segment").textContent = ui.humanize(demand.ramo);
    document.getElementById("demand-protocol").textContent = `#DEM-${String(demand.id).padStart(4, "0")}`;
    const status = document.getElementById("demand-status");
    status.textContent = ui.statusLabel(demand.status);
    status.className = `status-chip status-${demand.status}`;
    document.getElementById("demand-text").textContent = demand.texto || demand.titulo || "";

    const answers = demand.respostas || {};
    const labels = {
      objetivo: "Objetivo", dificuldade: "Principal gargalo", canais: "Canais predominantes",
      ferramentas: "Ferramentas atuais", orcamento: "Orçamento mensal", urgencia: "Prazo esperado",
    };
    const answerGrid = document.getElementById("answer-grid");
    answerGrid.replaceChildren();
    for (const [key, label] of Object.entries(labels)) {
      if (answers[key] !== undefined) addAnswer(label, answers[key]);
    }
    if (Object.keys(answers).length === 0) addAnswer("Diagnóstico", "Informação não disponível para esta demanda importada.");
    ui.renderTags(document.getElementById("demand-tags"), demand.tags);
    populateMatches(demand.matching || []);
    const history = document.getElementById("history-list");
    history.replaceChildren();
    for (const entry of demand.historico || []) {
      const item = ui.element("li");
      item.append(ui.element("strong", "", ui.humanize(entry.evento)), document.createTextNode(` — ${entry.detalhe}`));
      history.append(item);
    }
    setActions();
    document.getElementById("admin-loading").hidden = true;
    demandContent.hidden = false;
  } catch (error) {
    document.getElementById("admin-loading").hidden = true;
    ui.showError(error);
  }
}

validateButton.addEventListener("click", async () => {
  validateButton.disabled = true;
  try {
    await ui.api(`/api/admin/demandas/${demandId}/validar`, { method: "POST" });
    actionMessage.textContent = "Demanda validada.";
    await loadDemand();
  } catch (error) {
    ui.showError(error);
    validateButton.disabled = false;
  }
});

forwardButton.addEventListener("click", async () => {
  const startupId = Number(startupSelect.value);
  if (!Number.isInteger(startupId) || startupId < 1) {
    actionMessage.textContent = "Selecione uma startup recomendada.";
    return;
  }
  forwardButton.disabled = true;
  try {
    const result = await ui.api(`/api/admin/demandas/${demandId}/encaminhar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ startup_id: startupId }),
    });
    actionMessage.textContent = `Relatório #${result.relatorio_id} encaminhado.`;
    await loadDemand();
  } catch (error) {
    ui.showError(error);
    forwardButton.disabled = false;
  }
});

loadDemand();
