/**
 * Rótulos dos critérios do matching (definidos pelo backend) e leitura visual
 * da pontuação. Os limiares reaproveitam os usados pelo backend em
 * `back-end/app/domain/matching.py` e `js/matching-assistant.js`:
 * >= 0.8 contribui positivamente; < 0.4 é ponto de atenção.
 */

export const CRITERION_LABELS = {
  dor_especifica: "Atende à necessidade",
  tags_ia: "Temas do seu relato",
  objetivo: "Alinhamento ao objetivo",
  ramo: "Conhecimento do seu ramo",
  canais: "Canais de venda que você usa",
  preco: "Faixa de preço",
  ferramenta_atual: "Ferramentas que você usa",
  urgencia: "Prazo de implantação",
};

export function criterionLabel(criterio) {
  return CRITERION_LABELS[criterio] || String(criterio || "").replaceAll("_", " ");
}

export function criterionTone(pontuacao) {
  const value = Number(pontuacao);
  if (value >= 0.8) return { tone: "positive", label: "Boa combinação" };
  if (value < 0.4) return { tone: "attention", label: "Pode não atender" };
  return { tone: "neutral", label: "Combina em parte" };
}
