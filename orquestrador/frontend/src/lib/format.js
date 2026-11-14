export function initials(name) {
  return String(name || "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toLocaleUpperCase("pt-BR"))
    .join("");
}

export function humanize(value) {
  if (Array.isArray(value)) return value.map(humanize).join(", ");
  if (value === null || value === undefined || value === "") return "Não informado";
  return String(value).replaceAll("_", " ");
}

export function statusLabel(status) {
  return (
    {
      pendente: "Pendente de validação",
      validada: "Validada",
      encaminhada: "Encaminhada",
    }[status] || status
  );
}

export function formatSegment(value) {
  if (!value) return "Não informado";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase("pt-BR"));
}

/** Converte a pontuação 0..1 do backend em percentual inteiro 0..100. */
export function percent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, Math.round(number * 100)));
}

export function points(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return number.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}

export function queryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}
