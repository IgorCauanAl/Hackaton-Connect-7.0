/**
 * Cliente HTTP do frontend.
 *
 * O navegador conversa **apenas** com o orquestrador (mesma origem):
 * - leituras simples passam pelo pass-through `/api/*` do orquestrador;
 * - fluxos compostos usam `/orquestracao/*`.
 *
 * Nenhuma URL de backend ou chave de IA aparece aqui.
 */

export class ApiError extends Error {
  constructor(message, { status = 0, codigo = "", etapa = "", traceId = "", payload = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.codigo = codigo;
    this.etapa = etapa;
    this.traceId = traceId;
    this.payload = payload;
  }
}

export function actorHeaders(actor) {
  if (!actor) return {};
  const headers = { "X-Perfil": actor.perfil };
  if (Number.isInteger(actor.id) && actor.id > 0) {
    headers["X-Ator-Id"] = String(actor.id);
  }
  return headers;
}

function validationMessage(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.detalhe || JSON.stringify(item))
      .filter(Boolean)
      .join("; ");
  }
  return "";
}

async function request(path, { method = "GET", body, actor, headers = {}, signal } = {}) {
  const requestHeaders = {
    ...actorHeaders(actor),
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...headers,
  };

  let response;
  try {
    response = await fetch(path, {
      method,
      headers: requestHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new ApiError(
      "Serviço indisponível. Verifique se o orquestrador está em execução e tente novamente.",
      { codigo: "servico_indisponivel" },
    );
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" && detail.trim()
      ? detail.trim()
      : validationMessage(detail) || `Falha na requisição (${response.status}).`;
    throw new ApiError(message, {
      status: response.status,
      codigo: data?.codigo || "",
      etapa: data?.etapa || "",
      traceId: data?.trace_id || "",
      payload: data,
    });
  }

  return data;
}

/** Leitura simples via pass-through do orquestrador. */
export function backendGet(path, actor, options = {}) {
  return request(path, { ...options, actor, method: "GET" });
}

/** Fluxo composto: sempre pelo orquestrador. */
export function orchestrate(path, { method = "GET", body, actor, headers, signal } = {}) {
  return request(`/orquestracao${path}`, { method, body, actor, headers, signal });
}

export function unwrap(envelope) {
  if (envelope && typeof envelope === "object" && "resultado" in envelope) {
    return envelope.resultado;
  }
  return envelope;
}

export default request;
