const SESSION_KEY = "orvyn-demo-actor";
const CRITERION_LABELS = {
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
const resultsList = document.getElementById("results-list");
const emptyState = document.getElementById("empty-state");
const demandSummary = document.getElementById("demand-summary");
const demandIdLabel = document.getElementById("demand-id");

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase("pt-BR"))
    .join("");
}

async function getJson(path, headers = {}) {
  const response = await fetch(path, { headers });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Falha ao consultar o backend (${response.status}).`);
  }

  return data;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function createCriterion(item) {
  const score = Math.max(0, Math.min(100, Math.round(Number(item.pontuacao) * 100)));
  const criterion = element("div", "criterion");
  const heading = element("div", "criterion-heading");
  heading.append(
    element("span", "", CRITERION_LABELS[item.criterio] || item.criterio),
    element("span", "", `${score}%`),
  );
  const track = element("div", "criterion-track");
  const value = element("span", "criterion-value");
  value.style.width = `${score}%`;
  track.append(value);
  criterion.append(heading, track);

  if (item.motivo) {
    criterion.append(element("p", "criterion-reason", item.motivo));
  }

  return criterion;
}

async function createSolutionCard(match, index, headers, demandId, demand) {
  const startup = await getJson(`/api/startups/${match.startup_id}`, headers);
  const card = element("article", "solution-card");
  const top = element("div", "solution-topline");
  top.append(
    element("span", "rank-badge", `${index + 1}º lugar · ${index === 0 ? "Maior compatibilidade" : "Compatível"}`),
    element("div", "score-box"),
  );
  const scoreBox = top.lastElementChild;
  scoreBox.append(element("strong", "", String(match.indice)), element("span", "", "/100 de compatibilidade"));

  const title = element("h2", "", startup.nome);
  const description = element("p", "solution-description", startup.descricao || "Solução cadastrada na plataforma.");
  const assistantAnswer = element("section", "assistant-answer");
  assistantAnswer.append(
    element("strong", "", "Resposta do assistente"),
    element("p", "", window.matchingAssistant.compose(demand, match, startup)),
    element("small", "", "Síntese baseada no seu diagnóstico e nos critérios de compatibilidade."),
  );
  const offer = element("div", "solution-offer");
  offer.append(
    element("strong", "", "Solução oferecida"),
    element("p", "", startup.solucao || startup.descricao || "Consulte a startup para mais informações."),
  );

  const details = document.createElement("details");
  details.className = "criteria-details";
  details.append(element("summary", "", "Ver análise de compatibilidade"));
  const criteria = element("div", "criteria-list");
  for (const criterion of match.criterios || []) {
    criteria.append(createCriterion(criterion));
  }
  details.append(criteria);
  const action = element("a", "detail-link", "Ver detalhes e solicitar teste");
  action.href = `/solucao.html?demanda_id=${encodeURIComponent(demandId)}&startup_id=${encodeURIComponent(match.startup_id)}`;
  card.append(top, title, description, assistantAnswer, offer, details, action);
  return card;
}

async function initialize() {
  let actor;
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

  const demandId = Number(new URLSearchParams(window.location.search).get("demanda_id"));
  if (!Number.isInteger(demandId) || demandId < 1) {
    loadingState.hidden = true;
    pageError.textContent = "Identificador de demanda inválido. Volte ao diagnóstico e tente novamente.";
    pageError.hidden = false;
    return;
  }

  demandIdLabel.textContent = `Diagnóstico ID: #${demandId}`;
  const headers = { "X-Perfil": "lojista", "X-Ator-Id": String(actor.id) };

  try {
    const [matching, demand] = await Promise.all([
      getJson(`/api/demandas/${demandId}/matching`, headers),
      getJson(`/api/demandas/${demandId}`, headers),
    ]);

    demandSummary.textContent = demand.titulo || "Confira as soluções encontradas para sua necessidade.";
    loadingState.hidden = true;

    if (matching.ranking_startups.length === 0) {
      emptyState.hidden = false;
      return;
    }

    const cards = await Promise.all(
      matching.ranking_startups.map((match, index) => createSolutionCard(match, index, headers, demandId, demand)),
    );
    resultsList.replaceChildren(...cards);
    resultsList.hidden = false;
  } catch (error) {
    loadingState.hidden = true;
    pageError.textContent = error.message;
    pageError.hidden = false;
  }
}

initialize();
