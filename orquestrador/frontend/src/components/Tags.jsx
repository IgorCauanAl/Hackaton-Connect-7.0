import { humanize } from "../lib/format.js";

const ORIGIN_LABELS = {
  ia: "Assuntos sugeridos a partir do relato",
  botoes: "Assuntos identificados nas respostas",
};

export function TagList({ tags, className = "tag-row" }) {
  if (!tags?.length) return <span className="tag-empty">Nenhum assunto relacionado.</span>;
  return (
    <div className={className}>
      {tags.map((tag) => (
        <span className="tag-chip" key={tag}>{humanize(tag)}</span>
      ))}
    </div>
  );
}

export function TagOriginBadge({ origin }) {
  if (!origin) return null;
  return (
    <span className={`origin-badge ${origin}`} title="Como os assuntos foram identificados">
      {ORIGIN_LABELS[origin] || "Assuntos identificados pelo sistema"}
    </span>
  );
}

export function StatusChip({ status }) {
  const labels = {
    pendente: "Aguardando análise",
    validada: "Analisada",
    encaminhada: "Enviada à empresa",
  };
  return <span className={`status-chip status-${status}`}>{labels[status] || status}</span>;
}
