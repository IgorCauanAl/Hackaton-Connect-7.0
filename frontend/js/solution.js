const SESSION_KEY = "orvyn-demo-actor";
const LABELS = {
  dor_especifica: "Aderência à necessidade",
  tags_ia: "Compatibilidade das tags",
  objetivo: "Alinhamento ao objetivo",
  ramo: "Compatibilidade com o segmento",
  canais: "Adequação aos canais",
  preco: "Compatibilidade de preço",
  ferramenta_atual: "Adequação às ferramentas atuais",
  urgencia: "Prazo de implantação",
};

const pageError = document.getElementById("page-error");
const loadingState = document.getElementById("loading-state");
const content = document.getElementById("solution-content");
const consent = document.getElementById("consent");
const requestButton = document.getElementById("request-test");

function initials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase("pt-BR")).join("");
}

async function getJson(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Falha ao consultar o backend (${response.status}).`);
  return data;
}

function showError(error) {
  loadingState.hidden = true;
  pageError.textContent = error.message || String(error);
  pageError.hidden = false;
}

function renderCriteria(criteria) {
  const list = document.getElementById("criteria-list");
  list.replaceChildren();
  for (const item of criteria) {
    const percent = Math.max(0, Math.min(100, Math.round(Number(item.pontuacao) * 100)));
    const row = document.createElement("div");
    row.className = "criterion";
    const header = document.createElement("div");
    header.className = "criterion-header";
    const label = document.createElement("span");
    label.textContent = LABELS[item.criterio] || item.criterio;
    const score = document.createElement("span");
    score.textContent = `${percent}%`;
    header.append(label, score);
    const track = document.createElement("div");
    track.className = "criterion-track";
    const value = document.createElement("span");
    value.className = "criterion-value";
    value.style.width = `${percent}%`;
    track.append(value);
    row.append(header, track);
    if (item.motivo) {
      const reason = document.createElement("p");
      reason.className = "criterion-reason";
      reason.textContent = item.motivo;
      row.append(reason);
    }
    list.append(row);
  }
}

let actor;
let demandId;
let startupId;

async function initialize() {
  try {
    actor = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
  } catch {
    actor = null;
  }
  if (!actor || actor.perfil !== "lojista" || !Number.isInteger(actor.id)) {
    window.location.replace("/");
    return;
  }

  const params = new URLSearchParams(window.location.search);
  demandId = Number(params.get("demanda_id"));
  startupId = Number(params.get("startup_id"));
  if (!Number.isInteger(demandId) || demandId < 1 || !Number.isInteger(startupId) || startupId < 1) {
    showError(new Error("Demanda ou startup inválida. Volte aos resultados e tente novamente."));
    return;
  }

  const headers = { "X-Perfil": "lojista", "X-Ator-Id": String(actor.id) };
  document.getElementById("profile-name").textContent = actor.nome || "Lojista";
  document.getElementById("profile-initials").textContent = initials(actor.nome || "Lojista");
  const resultUrl = `/resultados.html?demanda_id=${encodeURIComponent(demandId)}`;
  document.getElementById("back-link").href = resultUrl;
  document.getElementById("results-link").href = resultUrl;

  try {
    const [startup, matching, demand] = await Promise.all([
      getJson(`/api/startups/${startupId}`, { headers }),
      getJson(`/api/demandas/${demandId}/matching`, { headers }),
      getJson(`/api/demandas/${demandId}`, { headers }),
    ]);
    const match = matching.ranking_startups.find((item) => item.startup_id === startupId);
    if (!match) throw new Error("Esta startup não está entre as soluções recomendadas para a demanda.");

    document.getElementById("solution-name").textContent = startup.nome;
    document.getElementById("solution-description").textContent = startup.descricao || "";
    document.getElementById("solution-offer").textContent = startup.solucao || startup.descricao || "Detalhes da solução não informados.";
    document.getElementById("solution-category").textContent = startup.categoria || "Solução para varejo";
    document.getElementById("solution-rank").textContent = `${matching.ranking_startups.findIndex((item) => item.startup_id === startupId) + 1}º lugar · Maior compatibilidade`;
    document.getElementById("overall-score").textContent = String(match.indice);
    document.getElementById("fit-label").textContent = match.indice >= 85 ? "Alta compatibilidade" : "Compatibilidade identificada";
    document.getElementById("demand-title").textContent = `Com base na necessidade: ${demand.titulo}`;
    document.getElementById("assistant-answer").textContent = window.matchingAssistant.compose(demand, match, startup);
    renderCriteria(match.criterios || []);
    loadingState.hidden = true;
    content.hidden = false;
  } catch (error) {
    showError(error);
  }
}

consent.addEventListener("change", () => {
  requestButton.disabled = !consent.checked;
  document.getElementById("consent-error").textContent = "";
});

requestButton.addEventListener("click", async () => {
  if (!consent.checked) {
    document.getElementById("consent-error").textContent = "Autorize o compartilhamento para continuar.";
    return;
  }
  requestButton.disabled = true;
  requestButton.textContent = "Solicitando...";
  try {
    const response = await getJson("/api/testes", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Perfil": "lojista",
        "X-Ator-Id": String(actor.id),
      },
      body: JSON.stringify({ demanda_id: demandId, startup_id: startupId, autorizacao: true }),
    });
    window.location.assign(`/teste.html?teste_id=${encodeURIComponent(response.teste_id)}`);
  } catch (error) {
    requestButton.disabled = false;
    requestButton.textContent = "Solicitar teste de 15 dias →";
    document.getElementById("consent-error").textContent = error.message;
  }
});

initialize();
