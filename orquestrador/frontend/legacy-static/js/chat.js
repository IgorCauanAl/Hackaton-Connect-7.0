const SESSION_KEY = "orvyn-demo-actor";
const conversation = document.getElementById("conversation");
const answerForm = document.getElementById("answer-form");
const questionPrompt = document.getElementById("question-prompt");
const answerOptions = document.getElementById("answer-options");
const formHint = document.getElementById("form-hint");
const textForm = document.getElementById("text-form");
const freeText = document.getElementById("free-text");
const characterCount = document.getElementById("character-count");
const submitButton = document.getElementById("submit-demand");
const chatError = document.getElementById("chat-error");
const progressLabel = document.getElementById("progress-label");
const progressValue = document.getElementById("progress-value");
const progressBadge = document.getElementById("progress-badge");
let actor;
let questions = [];
let currentQuestion = 0;
let answers = {};

function showError(error) {
  chatError.textContent = error.message || String(error);
  chatError.hidden = false;
}

function clearError() {
  chatError.textContent = "";
  chatError.hidden = true;
}

async function getJson(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Falha ao consultar o backend (${response.status}).`);
  }

  return data;
}

function addMessage(role, text) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  row.append(bubble);
  conversation.append(row);
  row.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function updateProgress(step, finalStep = false) {
  const total = questions.length;
  const current = Math.min(step, total);
  progressLabel.textContent = `Etapa ${current} de ${total}`;
  progressValue.style.width = `${total ? (current / total) * 100 : 0}%`;
  progressBadge.textContent = finalStep ? "Etapa final de análise" : "Diagnóstico guiado";
}

function renderQuestion() {
  clearError();
  const question = questions[currentQuestion];
  if (!question) {
    renderTextStep();
    return;
  }

  updateProgress(currentQuestion + 1);
  addMessage("assistant", question.pergunta);
  questionPrompt.textContent = question.pergunta;
  formHint.textContent = question.multipla
    ? "Selecione uma ou mais opções."
    : "Selecione uma opção para continuar.";
  answerOptions.replaceChildren();

  for (const option of question.opcoes) {
    const label = document.createElement("label");
    label.className = "answer-option";
    const input = document.createElement("input");
    input.type = question.multipla ? "checkbox" : "radio";
    input.name = "chat-answer";
    input.value = option.valor;
    const text = document.createElement("span");
    text.textContent = option.rotulo;
    label.append(input, text);
    answerOptions.append(label);
  }

  answerForm.hidden = false;
  textForm.hidden = true;
}

function renderTextStep() {
  clearError();
  updateProgress(questions.length, true);
  addMessage("assistant", "Descreva com suas palavras o principal desafio no dia a dia:");
  answerForm.hidden = true;
  textForm.hidden = false;
  freeText.focus();
}

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase("pt-BR"))
    .join("");
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

  document.getElementById("profile-name").textContent = actor.nome || "Lojista";
  document.getElementById("profile-initials").textContent = initials(actor.nome || "Lojista");

  try {
    const headers = { "X-Perfil": "lojista", "X-Ator-Id": String(actor.id) };
    const [lojista, roteiro] = await Promise.all([
      getJson(`/api/lojistas/${actor.id}`, { headers }),
      getJson("/api/chat/roteiro"),
    ]);

    actor.nome = lojista.nome;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(actor));
    document.getElementById("profile-name").textContent = lojista.nome;
    document.getElementById("profile-initials").textContent = initials(lojista.nome);
    questions = roteiro.perguntas;
    progressBadge.textContent = "Diagnóstico guiado";
    renderQuestion();
  } catch (error) {
    progressLabel.textContent = "Não foi possível iniciar";
    progressBadge.textContent = "Erro";
    showError(error);
  }
}

answerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  clearError();

  const question = questions[currentQuestion];
  const selected = [...answerOptions.querySelectorAll("input:checked")];
  if (selected.length === 0) {
    showError(new Error("Selecione uma resposta antes de continuar."));
    return;
  }

  const values = selected.map((input) => input.value);
  const labels = selected.map((input) => input.nextElementSibling.textContent);
  answers[question.id] = question.multipla ? values : values[0];
  addMessage("user", labels.join(", "));
  currentQuestion += 1;
  renderQuestion();
});

freeText.addEventListener("input", () => {
  characterCount.textContent = String(freeText.value.length);
});

textForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  const texto = freeText.value.trim();

  if (!texto || texto.length > 500) {
    showError(new Error("Descreva sua necessidade com até 500 caracteres."));
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Analisando...";

  try {
    const result = await getJson("/api/demandas", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Perfil": "lojista",
        "X-Ator-Id": String(actor.id),
      },
      body: JSON.stringify({
        lojista_id: actor.id,
        respostas: answers,
        texto_livre: texto,
      }),
    });
    window.location.assign(`/resultados.html?demanda_id=${encodeURIComponent(result.demanda_id)}`);
  } catch (error) {
    showError(error);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Analisar necessidade";
  }
});

document.getElementById("new-demand").addEventListener("click", () => {
  window.location.reload();
});

initialize();
