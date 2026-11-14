const systemStatus = document.querySelector(".system-status");
const connectionStatus = document.getElementById("connection-status");
const message = document.getElementById("access-message");
const lojistaSelect = document.getElementById("lojista-select");
const startupSelect = document.getElementById("startup-select");
const lojistaButton = document.getElementById("lojista-access");
const startupButton = document.getElementById("startup-access");
const adminButton = document.getElementById("admin-access");

async function getJson(path, headers = {}) {
  const response = await fetch(path, { headers });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `Falha ao consultar ${path} (${response.status}).`);
  }

  return data;
}

function fillSelect(select, items, placeholder) {
  const placeholderOption = new Option(placeholder, "", true, true);
  placeholderOption.disabled = true;
  select.replaceChildren(placeholderOption);

  for (const item of items) {
    select.add(new Option(item.nome, item.id));
  }

  select.disabled = items.length === 0;
}

function setConnected(connected) {
  systemStatus.dataset.state = connected ? "connected" : "error";
  connectionStatus.textContent = connected ? "Sistema conectado" : "Sistema indisponível";
  adminButton.disabled = !connected;
}

function reportError(error) {
  setConnected(false);
  message.dataset.state = "error";
  message.textContent = `Não foi possível carregar os ambientes: ${error.message}`;
}

function selectEnvironment(profile, id, name) {
  const actor = { perfil: profile, id, nome: name };

  try {
    sessionStorage.setItem("orvyn-demo-actor", JSON.stringify(actor));
  } catch (error) {
    message.dataset.state = "error";
    message.textContent = `Não foi possível guardar o ambiente selecionado: ${error.message}`;
    return;
  }

  if (profile === "lojista") {
    window.location.assign("/chat.html");
    return;
  }

  if (profile === "startup") {
    window.location.assign("/oportunidade.html");
    return;
  }

  if (profile === "admin") {
    window.location.assign("/admin.html");
    return;
  }

  message.dataset.state = "success";
  message.textContent = `Ambiente ${name} selecionado. A escolha ficará disponível para as próximas telas.`;
}

async function loadEnvironments() {
  try {
    await getJson("/api/saude");

    const headers = { "X-Perfil": "admin" };
    const [lojistas, startups] = await Promise.all([
      getJson("/api/lojistas", headers),
      getJson("/api/startups", headers),
    ]);

    fillSelect(lojistaSelect, lojistas, "Selecione um estabelecimento");
    fillSelect(startupSelect, startups, "Selecione uma startup");
    lojistaButton.disabled = true;
    startupButton.disabled = true;
    setConnected(true);

    if (lojistas.length === 0 || startups.length === 0) {
      message.dataset.state = "error";
      message.textContent = "O backend está conectado, mas não há ambientes disponíveis para todos os perfis.";
    }
  } catch (error) {
    reportError(error);
  }
}

lojistaSelect.addEventListener("change", () => {
  lojistaButton.disabled = !lojistaSelect.value;
});

startupSelect.addEventListener("change", () => {
  startupButton.disabled = !startupSelect.value;
});

lojistaButton.addEventListener("click", () => {
  const id = Number(lojistaSelect.value);
  const lojista = [...lojistaSelect.options].find((option) => Number(option.value) === id);

  if (Number.isInteger(id) && id > 0 && lojista) {
    selectEnvironment("lojista", id, lojista.textContent);
  }
});

startupButton.addEventListener("click", () => {
  const id = Number(startupSelect.value);
  const startup = [...startupSelect.options].find((option) => Number(option.value) === id);

  if (Number.isInteger(id) && id > 0 && startup) {
    selectEnvironment("startup", id, startup.textContent);
  }
});

adminButton.addEventListener("click", () => {
  selectEnvironment("admin", null, "Associação");
});

loadEnvironments();
