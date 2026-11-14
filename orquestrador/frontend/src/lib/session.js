/**
 * Sessão demonstrativa: o frontend não autentica. Apenas guarda o ambiente
 * escolhido e repassa `X-Perfil`/`X-Ator-Id`; a autorização é do backend.
 */

export const SESSION_KEY = "orvyn-demo-actor";

export function readActor() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveActor(actor) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(actor));
}

export function requireActor(profile) {
  const actor = readActor();
  const validId = profile === "admin" || (Number.isInteger(actor?.id) && actor.id > 0);
  if (!actor || actor.perfil !== profile || !validId) {
    window.location.replace("/");
    return null;
  }
  return actor;
}

export function requireAdmin() {
  return requireActor("admin");
}
