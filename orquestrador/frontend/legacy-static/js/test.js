const SESSION_KEY = "orvyn-demo-actor";
const loadingState = document.getElementById("loading-state");
const testContent = document.getElementById("test-content");
const pageError = document.getElementById("page-error");
const feedbackCard = document.getElementById("feedback-card");
const pendingCard = document.getElementById("pending-card");
let actor;
let testId;

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

function showFeedback(feedback) {
  document.getElementById("feedback-solved").textContent =
    feedback.respostas?.resolveu_dor === "sim" ? "Sim" : "Não";
  document.getElementById("feedback-ease").textContent =
    `${feedback.respostas?.facilidade_de_uso || feedback.nota}/5`;
  document.getElementById("feedback-impact").textContent = "Positivo";
  document.getElementById("feedback-recommend").textContent =
    feedback.respostas?.continuaria_usando === "sim" ? "Sim" : "Não";
  document.getElementById("feedback-comment").textContent = feedback.comentario;
  feedbackCard.hidden = false;
  pendingCard.hidden = true;
}

async function loadFeedback(headers) {
  const feedbacks = await getJson("/api/feedbacks", { headers });
  return feedbacks.find((item) => item.teste_id === testId) || null;
}

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

  testId = Number(new URLSearchParams(window.location.search).get("teste_id"));
  if (!Number.isInteger(testId) || testId < 1) {
    showError(new Error("Identificador de teste inválido."));
    return;
  }

  document.getElementById("profile-name").textContent = actor.nome || "Lojista";
  document.getElementById("profile-initials").textContent = initials(actor.nome || "Lojista");
  const headers = { "X-Perfil": "lojista", "X-Ator-Id": String(actor.id) };
  try {
    const test = await getJson(`/api/testes/${testId}`, { headers });
    const [startup, demand, feedback] = await Promise.all([
      getJson(`/api/startups/${test.startup_id}`, { headers }),
      getJson(`/api/demandas/${test.demanda_id}`, { headers }),
      loadFeedback(headers),
    ]);
    const concluded = test.status === "concluido";
    document.getElementById("test-status").textContent = concluded ? "Teste concluído" : "Teste solicitado";
    document.getElementById("test-status").classList.toggle("pending", !concluded);
    document.getElementById("test-caption").textContent = concluded
      ? "Período de demonstração encerrado; confira o feedback registrado."
      : "Teste solicitado. A solicitação foi enviada à startup.";
    document.getElementById("startup-name").textContent = startup.nome;
    document.getElementById("startup-solution").textContent = startup.descricao || "";
    document.getElementById("opportunity-title").textContent = demand.titulo || "Necessidade comercial";
    document.getElementById("test-duration").textContent = `${test.dias} dias`;
    document.getElementById("test-date").textContent = `Previsto até ${test.fim_previsto}`;
    document.getElementById("results-link").href = `/resultados.html?demanda_id=${encodeURIComponent(test.demanda_id)}`;
    document.getElementById("back-link").href = `/solucao.html?demanda_id=${encodeURIComponent(test.demanda_id)}&startup_id=${encodeURIComponent(test.startup_id)}`;
    document.getElementById("pending-days").textContent = `${test.dias} dias`;

    if (feedback) showFeedback(feedback);
    else pendingCard.hidden = false;

    loadingState.hidden = true;
    testContent.hidden = false;
  } catch (error) {
    showError(error);
  }
}

document.getElementById("complete-demo").addEventListener("click", async () => {
  const button = document.getElementById("complete-demo");
  const error = document.getElementById("action-error");
  button.disabled = true;
  error.textContent = "";
  try {
    const headers = {
      "X-Perfil": "lojista",
      "X-Ator-Id": String(actor.id),
    };
    const feedback = await getJson(`/api/testes/${testId}/feedback-demo`, {
      method: "POST",
      headers,
    });
    showFeedback(feedback);
  } catch (exception) {
    error.textContent = exception.message;
    button.disabled = false;
  }
});

initialize();
