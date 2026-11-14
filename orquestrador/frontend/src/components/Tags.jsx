import { humanize } from "../lib/format.js";

const ORIGIN_LABELS = {
  ia: "Tags geradas pela IA",
  botoes: "Tags derivadas das respostas guiadas",
};

export function TagList({ tags, className = "tag-row" }) {
  if (!tags?.length) return <span className="tag-empty">Nenhuma tag identificada.</span>;
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
    <span className={`origin-badge ${origin}`} title="Origem das tags da demanda">
      {ORIGIN_LABELS[origin] || `Tags: ${origin}`}
    </span>
  );
}

export function StatusChip({ status }) {
  const labels = {
    pendente: "Pendente de validação",
    validada: "Validada",
    encaminhada: "Encaminhada",
  };
  return <span className={`status-chip status-${status}`}>{labels[status] || status}</span>;
}
