(() => {
  const headers = { "X-Perfil": "admin" };

  function requireAdmin() {
    let actor;
    try {
      actor = JSON.parse(sessionStorage.getItem("orvyn-demo-actor") || "null");
    } catch {
      actor = null;
    }
    if (!actor || actor.perfil !== "admin") {
      window.location.replace("/");
      return null;
    }
    return actor;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { ...headers, ...(options.headers || {}) },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Falha ao consultar o backend (${response.status}).`);
    return data;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function showError(error) {
    const box = document.getElementById("admin-error");
    box.textContent = error.message || String(error);
    box.hidden = false;
  }

  function statusLabel(status) {
    return ({ pendente: "Pendente de validação", validada: "Validada", encaminhada: "Encaminhada" })[status] || status;
  }

  function humanize(value) {
    if (Array.isArray(value)) return value.map(humanize).join(", ");
    if (value === null || value === undefined || value === "") return "Não informado";
    return String(value).replaceAll("_", " ");
  }

  function renderTags(container, tags) {
    container.replaceChildren();
    for (const tag of tags || []) {
      container.append(element("span", "tag-chip", humanize(tag)));
    }
  }

  async function checkConnection() {
    const indicator = document.querySelector(".admin-connection");
    if (!indicator) return;
    try {
      const response = await fetch("/api/saude");
      const health = await response.json();
      if (!response.ok || health.status !== "ok") throw new Error("API indisponível");
      indicator.lastChild.textContent = " Sistema conectado";
    } catch {
      indicator.classList.add("offline");
      indicator.lastChild.textContent = " API indisponível";
    }
  }

  checkConnection();

  window.adminUi = { api, element, humanize, renderTags, requireAdmin, showError, statusLabel };
})();
