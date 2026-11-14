/**
 * Rótulos dos critérios do matching (definidos pelo backend) e leitura visual
 * da pontuação. Os limiares reaproveitam os usados pelo backend em
 * `back-end/app/domain/matching.py` e `js/matching-assistant.js`:
 * >= 0.8 contribui positivamente; < 0.4 é ponto de atenção.
 */

export const CRITERION_LABELS = {
  dor_especifica: "Aderência à necessidade",
  tags_ia: "Compatibilidade das tags",
  objetivo: "Alinhamento ao objetivo",
  ramo: "Compatibilidade com o segmento",
  canais: "Adequação aos canais",
  preco: "Compatibilidade de preço",
  ferramenta_atual: "Adequação às ferramentas atuais",
  urgencia: "Prazo de implantação",
};

export function criterionLabel(criterio) {
  return CRITERION_LABELS[criterio] || String(criterio || "").replaceAll("_", " ");
}

export function criterionTone(pontuacao) {
  const value = Number(pontuacao);
  if (value >= 0.8) return { tone: "positive", label: "Contribui positivamente" };
  if (value < 0.4) return { tone: "attention", label: "Ponto de atenção" };
  return { tone: "neutral", label: "Contribuição neutra" };
}
