const SESSION_KEY = "orvyn-demo-actor";

const pageError = document.getElementById("page-error");
const loadingState = document.getElementById("loading-state");
const emptyState = document.getElementById("empty-state");
const opportunityContent = document.getElementById("opportunity-content");
const pickerWrap = document.getElementById("opportunity-picker-wrap");
const picker = document.getElementById("opportunity-picker");

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

function setReportText(id, value, fallback) {
  document.getElementById(id).textContent = value || fallback;
}

function showError(error) {
  loadingState.hidden = true;
  pageError.textContent = error.message || String(error);
  pageError.hidden = false;
}

function formatSegment(value) {
  if (!value) return "Não informado";
  return value
    .replaceAll("_", " ")
    .replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase("pt-BR"));
}

function formatContext(signal) {
  const total = Number(signal?.lojistas_mesma_dor || 0);
  const sameSegment = Number(signal?.no_mesmo_ramo || 0);
  const sameRegion = Number(signal?.na_mesma_regiao || 0);
  return `${total} ${total === 1 ? "lojista relatou" : "lojistas relataram"} uma necessidade semelhante. `
    + `${sameSegment} no mesmo segmento e ${sameRegion} na mesma região.`;
}

function formatNeed(tags) {
  if (!tags?.length) return "Necessidade comercial identificada no diagnóstico do lojista.";
  return `Demanda relacionada a: ${tags.map(formatSegment).join(", ")}.`;
}

function formatApplication(blocks, startup) {
  const compatibility = blocks.compatibilidade;
  const score = compatibility?.indice;
  const reasons = (compatibility?.criterios || [])
    .filter((criterion) => criterion.motivo)
    .slice(0, 2)
    .map((criterion) => criterion.motivo);
  const details = [];

  if (startup.solucao) details.push(startup.solucao);
  if (Number.isFinite(score)) details.push(`Compatibilidade calculada: ${score}/100.`);
  details.push(...reasons);
  return details.join(" ");
}

async function showOpportunity(opportunity, startup, headers) {
  loadingState.hidden = false;
  opportunityContent.hidden = true;
  pageError.hidden = true;

  const report = await getJson(`/api/relatorios/${opportunity.relatorio_id}?versao=anonimizada`, headers);
  const blocks = report.blocos;
  const summary = blocks.resumo?.resumo || opportunity.titulo;
  const segment = blocks.perfil_loja?.ramo || opportunity.ramo;
  const tags = blocks.dor_contexto?.tags || [];

  document.getElementById("summary-title").textContent = summary || "Necessidade comercial";
  document.getElementById("summary-segment").textContent = formatSegment(segment);
  document.getElementById("summary-status").textContent =
    opportunity.status === "encaminhada" ? "Encaminhada" : formatSegment(opportunity.status);
  setReportText("report-problem", summary, "Necessidade comercial identificada pela associação.");
  setReportText("report-need", formatNeed(tags), "Demanda comercial registrada no diagnóstico.");
  setReportText("report-context", formatContext(blocks.sinal_mercado), "Contexto comercial disponível no relatório.");
  setReportText("report-application", formatApplication(blocks, startup), "Avalie como sua solução pode atender à demanda.");

  loadingState.hidden = true;
  opportunityContent.hidden = false;
}

async function initialize() {
  let actor;
  try {
    actor = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
  } catch {
    actor = null;
  }

  if (!actor || actor.perfil !== "startup" || !Number.isInteger(actor.id)) {
    window.location.replace("/");
    return;
  }

  const headers = { "X-Perfil": "startup", "X-Ator-Id": String(actor.id) };

  try {
    const [startup, opportunities] = await Promise.all([
      getJson(`/api/startups/${actor.id}`, headers),
      getJson(`/api/startups/${actor.id}/oportunidades`, headers),
    ]);

    actor.nome = startup.nome;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(actor));
    document.getElementById("profile-name").textContent = startup.nome;
    document.getElementById("profile-initials").textContent = initials(startup.nome);
    loadingState.hidden = true;

    if (opportunities.length === 0) {
      emptyState.hidden = false;
      return;
    }

    if (opportunities.length > 1) {
      picker.replaceChildren();
      opportunities.forEach((opportunity, index) => {
        const option = new Option(opportunity.titulo || `Oportunidade ${index + 1}`, opportunity.relatorio_id);
        picker.add(option);
      });
      pickerWrap.hidden = false;
    }

    await showOpportunity(opportunities[0], startup, headers);
    picker.addEventListener("change", async () => {
      const selected = opportunities.find((item) => item.relatorio_id === Number(picker.value));
      if (selected) {
        try {
          await showOpportunity(selected, startup, headers);
        } catch (error) {
          showError(error);
        }
      }
    });
  } catch (error) {
    showError(error);
  }
}

initialize();
