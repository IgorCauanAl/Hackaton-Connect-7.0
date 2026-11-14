/**
 * Síntese em linguagem natural exibida ao lojista.
 *
 * É apenas redação sobre dados que já existem (respostas do diagnóstico,
 * critérios e índice calculados pelo backend). Não cria nota, peso ou
 * classificação nova.
 */

const LABELS = {
  objetivo: {
    vender_mais: "vender mais",
    reduzir_custos: "reduzir custos",
    organizar_gestao: "organizar a gestão",
    fidelizar_clientes: "fidelizar clientes",
    outro: "melhorar outro aspecto do negócio",
  },
  dificuldade: {
    atrair_clientes: "atrair novos clientes",
    atender_whatsapp: "responder aos clientes pelo WhatsApp",
    vender_online: "vender pela internet",
    trazer_cliente_de_volta: "fazer os clientes voltarem",
    controle_estoque_caixa: "controlar estoque e caixa",
    outro: "resolver outra dificuldade",
  },
  canais: {
    loja: "loja física",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    site_proprio: "site próprio",
    marketplace: "marketplace",
  },
  ferramentas: {
    nenhuma: "nenhuma ferramenta específica",
    planilha: "planilha",
    sistema_caixa: "sistema de caixa",
    crm: "CRM",
    outra: "outra ferramenta",
  },
  orcamento: {
    ate_100: "até R$ 100 por mês",
    "100_300": "R$ 100 a R$ 300 por mês",
    "300_800": "R$ 300 a R$ 800 por mês",
    acima: "mais de R$ 800 por mês",
  },
  urgencia: {
    ate_15_dias: "em até 15 dias",
    ate_2_meses: "em até dois meses",
    sem_pressa: "sem prazo definido",
  },
};

const evidenceByCriterion = {
  dor_especifica: (answers) =>
    `atua na dificuldade de ${LABELS.dificuldade[answers.dificuldade] || "que você relatou"}`,
  tags_ia: () => "se conecta aos assuntos identificados no seu relato",
  objetivo: (answers) =>
    `está alinhada ao seu objetivo de ${LABELS.objetivo[answers.objetivo] || "melhorar o negócio"}`,
  ramo: (_, demand) => `é compatível com o segmento ${demand.ramo || "do seu negócio"}`,
  canais: () => "tem boa aderência aos canais de venda que você informou",
  preco: () => "a faixa de preço cadastrada é compatível com o orçamento informado",
  ferramenta_atual: (answers) => {
    const tools = (answers.ferramentas || []).filter((value) => value !== "nenhuma");
    if (!tools.length) return "não exige que você já tenha uma ferramenta específica";
    return `não duplica diretamente a ferramenta que você informou (${naturalList(
      tools.map((value) => LABELS.ferramentas[value] || value),
    )})`;
  },
  urgencia: (answers) =>
    `tem prazo de implantação compatível com o que você precisa (${
      LABELS.urgencia[answers.urgencia] || "prazo informado"
    })`,
};

const cautionByCriterion = {
  canais: "confirme com a startup se todos os seus canais de venda estão contemplados",
  preco: "confirme o preço final, pois a faixa cadastrada pode ultrapassar seu orçamento",
  ferramenta_atual: "confirme a integração com a ferramenta que você já utiliza",
  urgencia: "confirme o prazo, pois a implantação pode levar mais tempo que o desejado",
};

function naturalList(items) {
  if (items.length < 2) return items[0] || "";
  if (items.length === 2) return `${items[0]} e ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} e ${items[items.length - 1]}`;
}

export function composeAssistantAnswer(demand, match, startup) {
  const answers = demand?.respostas || {};
  const channels = (answers.canais || []).map((value) => LABELS.canais[value] || value);
  const criteria = match?.criterios || [];
  const strengths = criteria
    .filter((item) => Number(item.pontuacao) >= 0.8 && evidenceByCriterion[item.criterio])
    .sort((left, right) => Number(right.pontos) - Number(left.pontos))
    .slice(0, 3)
    .map((item) => evidenceByCriterion[item.criterio](answers, demand));
  const caution = criteria
    .filter((item) => Number(item.pontuacao) < 0.4 && cautionByCriterion[item.criterio])
    .map((item) => cautionByCriterion[item.criterio])[0];
  const goal = LABELS.objetivo[answers.objetivo] || "melhorar o negócio";
  const difficulty =
    LABELS.dificuldade[answers.dificuldade] || "resolver uma dificuldade do negócio";
  const solution = startup?.solucao || startup?.descricao || "a solução cadastrada pela startup";
  const context = demand?.texto ? `Você relatou: “${demand.texto.trim()}”. ` : "";
  const evidence = strengths.length
    ? `Ela combina com o que você procura porque ${naturalList(strengths)}.`
    : "A recomendação considera seu objetivo, segmento, canais, orçamento e prazo.";
  const caveatText = caution ? ` Como ponto de atenção, ${caution}.` : "";

  return `${context}Você quer ${goal} e destacou como principal desafio ${difficulty}. ${
    startup?.nome || "A startup"
  } foi recomendada: ${solution} ${evidence} A aderência estimada é ${
    match?.indice ?? "--"
  } de 100. Também consideramos que você vende por ${
    naturalList(channels) || "canais não informados"
  }, pode investir ${
    LABELS.orcamento[answers.orcamento] || "o valor informado"
  } e precisa da solução ${
    LABELS.urgencia[answers.urgencia] || "no prazo indicado"
  }.${caveatText}`;
}
