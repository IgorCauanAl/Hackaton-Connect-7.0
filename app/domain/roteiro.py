"""Roteiro fixo do chat guiado (6 perguntas por botões + texto livre)."""

ROTEIRO = [
    {"id": "objetivo", "pergunta": "O que você quer melhorar na sua loja agora?", "multipla": False, "alimenta": "Tag macro da dor",
     "opcoes": [("vender_mais", "Vender mais"), ("reduzir_custos", "Reduzir custos"), ("organizar_gestao", "Organizar a gestão"),
                ("fidelizar_clientes", "Fidelizar clientes"), ("outro", "Outro")]},
    {"id": "dificuldade", "pergunta": "Onde você mais sente a dificuldade para vender?", "multipla": False, "alimenta": "Tag específica da dor",
     "opcoes": [("atrair_clientes", "Atrair clientes novos"), ("atender_whatsapp", "Atender no WhatsApp"), ("vender_online", "Vender online"),
                ("trazer_cliente_de_volta", "Trazer cliente de volta"), ("controle_estoque_caixa", "Controle de estoque e caixa")]},
    {"id": "canais", "pergunta": "Por onde seus clientes compram hoje?", "multipla": True, "alimenta": "Canais (critério de integração)",
     "opcoes": [("loja", "Loja"), ("whatsapp", "WhatsApp"), ("instagram", "Instagram"), ("site_proprio", "Site próprio"), ("marketplace", "Marketplace")]},
    {"id": "ferramentas", "pergunta": "Já usa alguma ferramenta para isso?", "multipla": True, "alimenta": "Evita recomendar o que já tem",
     "opcoes": [("nenhuma", "Nenhuma"), ("planilha", "Planilha"), ("sistema_caixa", "Sistema de caixa"), ("crm", "CRM"), ("outra", "Outra")]},
    {"id": "orcamento", "pergunta": "Quanto você pode investir por mês?", "multipla": False, "alimenta": "Critério de preço",
     "opcoes": [("ate_100", "Até R$ 100"), ("100_300", "R$ 100 a 300"), ("300_800", "R$ 300 a 800"), ("acima", "Acima")]},
    {"id": "urgencia", "pergunta": "Quando você precisa disso funcionando?", "multipla": False, "alimenta": "Urgência / critério de esforço",
     "opcoes": [("ate_15_dias", "Em até 15 dias"), ("ate_2_meses", "Até 2 meses"), ("sem_pressa", "Sem pressa")]},
]
TEXTO_LIVRE = {"id": "texto_livre", "pergunta": "Conte com suas palavras o que acontece e o que você já tentou", "max_caracteres": 500,
               "alimenta": "IA classifica e extrai tags"}


def roteiro_publico() -> dict:
    return {"perguntas": [{**p, "opcoes": [{"valor": v, "rotulo": r} for v, r in p["opcoes"]]} for p in ROTEIRO],
            "texto_livre": TEXTO_LIVRE, "total_etapas": len(ROTEIRO) + 1}
