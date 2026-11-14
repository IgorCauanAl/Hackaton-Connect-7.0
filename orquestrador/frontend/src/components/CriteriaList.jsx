import { criterionLabel, criterionTone } from "../lib/criteria.js";
import { percent, points } from "../lib/format.js";

export function CriterionItem({ item, headingClass = "criterion-heading" }) {
  const score = percent(item.pontuacao);
  const { tone, label } = criterionTone(item.pontuacao);
  return (
    <div className="criterion">
      <div className={headingClass}>
        <span>{criterionLabel(item.criterio)}</span>
        <span>{score}%</span>
      </div>
      <div className="criterion-track" aria-hidden="true">
        <span className="criterion-value" style={{ width: `${score}%` }} />
      </div>
      <div className={`criterion-note ${tone}`}>
        <span>{label}</span>
        <small>{points(item.pontos)} pts</small>
      </div>
      {item.motivo ? <p className="criterion-reason">{item.motivo}</p> : null}
    </div>
  );
}

export function CriteriaList({ criteria, headingClass, className = "criteria-list" }) {
  if (!criteria?.length) {
    return <p className="criterion-reason">Nenhum critério detalhado foi retornado.</p>;
  }
  return (
    <div className={className}>
      {criteria.map((item, index) => (
        <CriterionItem key={`${item.criterio}-${index}`} item={item} headingClass={headingClass} />
      ))}
    </div>
  );
}
