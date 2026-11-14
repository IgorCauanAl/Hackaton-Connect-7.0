"""Seed determinístico da demo. Uso: python -m app.seed  (apaga e recria o banco)."""
from __future__ import annotations

import sqlite3

from app.container import montar
from app.core.config import Settings
from app.core.security import Ator, Perfil
from app.infra import database
from app.infra import repositories as r

TEXTO_MARIA = "Não consigo atender todo mundo no WhatsApp fora do horário comercial e perco muitas vendas."
TEXTO_JOAO = "Queria um sistema que buscasse o pet na casa do cliente."

LOJISTAS = [
    {"id": 1, "nome": "Loja da Maria (Moda de Rua)", "ramo": "moda", "tipo": "loja de rua", "porte": "micro",
     "cidade": "São Paulo", "regiao": "Centro", "canais": ["loja", "whatsapp", "instagram"], "ferramentas": ["planilha"],
     "texto_livre_demo": TEXTO_MARIA,
     "respostas_demo": {"objetivo": "vender_mais", "dificuldade": "atender_whatsapp", "canais": ["loja", "whatsapp", "instagram"],
                        "ferramentas": ["planilha"], "orcamento": "100_300", "urgencia": "ate_15_dias"}},
    {"id": 2, "nome": "Pet Shop do João", "ramo": "petshop", "tipo": "loja de bairro", "porte": "micro",
     "cidade": "Guarulhos", "regiao": "Zona Leste", "canais": ["loja", "whatsapp"], "ferramentas": ["sistema_caixa"],
     "texto_livre_demo": TEXTO_JOAO,
     "respostas_demo": {"objetivo": "outro", "dificuldade": "outro", "canais": ["loja", "whatsapp"],
                        "ferramentas": ["sistema_caixa"], "orcamento": "100_300", "urgencia": "ate_2_meses"}},
]

_S = dict(portfolio_url="https://exemplo.com/portfolio", whatsapp="+55 11 90000-0000")
STARTUPS = [
    dict(id=1, nome="ZapBot", categoria="chatbot", descricao="Atendimento automático no WhatsApp 24h.",
         solucao="Chatbot que responde clientes e captura pedidos fora do horário comercial.",
         objetivos=["vender_mais"], dores=["atender_whatsapp"], tags=["atendimento", "whatsapp", "automacao"],
         segmentos=["varejo", "moda", "calcados", "cosmeticos"], canais=["whatsapp", "instagram", "loja"],
         preco_min=150, preco_max=320, dias_implantacao=7, **_S),
    dict(id=2, nome="VendasZap", categoria="chatbot", descricao="Catálogo e vendas pelo WhatsApp.",
         solucao="Vitrine digital e fechamento de vendas dentro do WhatsApp.",
         objetivos=["vender_mais"], dores=["atender_whatsapp", "vender_online"], tags=["whatsapp", "vendas_online"],
         segmentos=["varejo", "moda", "acessorios"], canais=["whatsapp", "instagram"],
         preco_min=99, preco_max=250, dias_implantacao=10, **_S),
    dict(id=3, nome="AtendeJá", categoria="chatbot", descricao="Central omnichannel de atendimento.",
         solucao="Unifica WhatsApp e Instagram com respostas automáticas e fila de atendentes.",
         objetivos=["vender_mais", "fidelizar_clientes"], dores=["atender_whatsapp", "atrair_clientes"],
         tags=["atendimento", "whatsapp", "marketing"], segmentos=["varejo", "moda", "brinquedos"],
         canais=["whatsapp", "instagram", "site_proprio"], preco_min=300, preco_max=700, dias_implantacao=20, **_S),
    dict(id=4, nome="GestorPro", categoria="sistema_caixa", descricao="Gestão simples para pequenos varejos.",
         solucao="Caixa, estoque e financeiro em um só painel.",
         objetivos=["organizar_gestao", "reduzir_custos"], dores=["controle_estoque_caixa"], tags=["gestao", "estoque", "caixa"],
         segmentos=["varejo", "moda", "petshop"], canais=["loja"], preco_min=80, preco_max=250, dias_implantacao=14, **_S),
    dict(id=5, nome="ERP Fácil", categoria="sistema_caixa", descricao="ERP com estoque e fiscal.",
         solucao="Controle de estoque, notas fiscais e relatórios.",
         objetivos=["organizar_gestao"], dores=["controle_estoque_caixa"], tags=["estoque", "caixa", "gestao"],
         segmentos=["varejo", "calcados", "brinquedos"], canais=["loja", "marketplace"], preco_min=200, preco_max=800,
         dias_implantacao=45, **_S),
    dict(id=6, nome="FideliPay", categoria="crm", descricao="Fidelidade e cashback para lojas físicas.",
         solucao="Programa de pontos e campanhas para trazer o cliente de volta.",
         objetivos=["fidelizar_clientes", "vender_mais"], dores=["trazer_cliente_de_volta"], tags=["fidelizacao", "marketing"],
         segmentos=["varejo", "moda", "cosmeticos"], canais=["loja", "whatsapp"], preco_min=100, preco_max=300,
         dias_implantacao=10, **_S),
    dict(id=7, nome="LojaOnline360", categoria="ecommerce", descricao="Loja virtual e marketplaces integrados.",
         solucao="Cria a loja online e sincroniza estoque com marketplaces.",
         objetivos=["vender_mais"], dores=["vender_online", "atrair_clientes"], tags=["vendas_online", "marketing", "estoque"],
         segmentos=["varejo", "moda", "acessorios"], canais=["site_proprio", "marketplace", "instagram"],
         preco_min=250, preco_max=900, dias_implantacao=30, **_S),
]

GRUPOS = [(1, "atendimento", "Atendimento WhatsApp"), (2, "estoque", "Controle de estoque"),
          (3, "marketing", "Divulgação e marketing"), (4, "fidelizacao", "Fidelização de clientes"),
          (5, "logistica", "Entrega e busca domiciliar")]

REFERENCIA = {
    1: "Oportunidade de criar bot de atendimento 24h para lojas de rua.",
    2: "Oportunidade de controle de estoque simples e integrado ao caixa.",
    3: "Oportunidade de ferramentas de divulgação com baixo custo para o pequeno varejo.",
    4: "Oportunidade de programa de fidelidade acessível para lojas físicas.",
    5: "Demanda isolada: acompanhar antes de considerar uma solução dedicada."}

# (tag, ramo, região, texto, status)
_ATEND = [
    "Perco vendas porque não respondo o WhatsApp fora do horário.", "Clientes chamam à noite no WhatsApp e ninguém atende.",
    "Atendimento no WhatsApp fora do horário comercial é meu maior gargalo.", "Não dou conta das mensagens do WhatsApp depois que fecho a loja.",
    "Cliente manda mensagem no domingo e compra no concorrente.", "Falta alguém para responder o WhatsApp à noite e no fim de semana.",
    "Muita pergunta repetida no WhatsApp fora do expediente.", "Perco pedidos por demora na resposta no WhatsApp à noite.",
    "Preciso atender o WhatsApp mesmo com a loja fechada.", "As mensagens do WhatsApp acumulam fora do horário e eu perco clientes.",
    "Atendo sozinha e não consigo responder todo mundo no WhatsApp à noite.", "Clientes pedem preço no WhatsApp de madrugada e desistem se não respondo."]
_ESTOQUE = ["Não sei quanto tenho de cada produto em estoque.", "Faço o estoque na caderneta e sempre erro a contagem.",
            "Falta produto na prateleira e eu só descubro quando o cliente pede.", "Controle de caixa e estoque é todo manual.",
            "Compro mercadoria repetida por falta de controle."]
_MKT = ["Não sei como divulgar minha loja sem gastar muito.", "Posto no Instagram mas não vira venda.",
        "Falta tempo para criar campanhas de divulgação.", "Quero atrair clientes novos para a loja de rua."]
_FIDEL = ["Cliente compra uma vez e nunca mais volta.", "Queria um jeito de premiar clientes fiéis.", "Não consigo trazer o cliente de volta depois da primeira compra."]
_RAMOS = ["moda", "calcados", "acessorios", "cosmeticos", "brinquedos"]
_REGIOES = ["Centro", "Zona Leste", "Zona Norte", "Zona Sul", "ABC"]


class _IASeed:
    """Classificador fixo usado só pelo seed (a IA real é do outro módulo)."""

    def extrair_tags(self, texto):
        return ["logistica"] if "pet" in texto else ["atendimento", "whatsapp"]

    def resumir(self, texto):
        return texto

    def interpretar_grupos(self, grupos):
        raise NotImplementedError


def _historicas() -> list[dict]:
    itens = []
    blocos = [("atendimento", _ATEND[1:], "validada"), ("estoque", _ESTOQUE[:4], "validada"),
              ("marketing", _MKT[:3], "validada"), ("fidelizacao", _FIDEL[:2], "validada"),
              ("atendimento", ["Cliente chama no WhatsApp fora do horário e fico sem responder."], "pendente"),
              ("estoque", _ESTOQUE[4:], "pendente"), ("marketing", _MKT[3:], "pendente"), ("fidelizacao", _FIDEL[2:], "pendente")]
    n = 0
    for tag, textos, status in blocos:
        for texto in textos:
            itens.append({"tag": tag, "ramo": _RAMOS[n % 5], "regiao": _REGIOES[(n * 2) % 5], "texto": texto, "status": status})
            n += 1
    return itens


def carregar(conn: sqlite3.Connection, settings: Settings | None = None) -> None:
    settings = settings or Settings()
    database.drop_all(conn)
    database.init_schema(conn)
    lojistas, startups, grupos = r.LojistaRepository(conn), r.StartupRepository(conn), r.GrupoRepository(conn)
    demandas, insights, historico = r.DemandaRepository(conn), r.InsightRepository(conn), r.HistoricoRepository(conn)

    for l in LOJISTAS:
        lojistas.criar(l)
    for s in STARTUPS:
        startups.criar(s)
    for gid, tag, titulo in GRUPOS:
        grupos.criar({"id": gid, "tag": tag, "titulo": titulo})
        insights.criar({"grupo_id": gid, "titulo": titulo, "quantidade": 0, "pontuacao": 0,
                        "sugestao_ia": REFERENCIA[gid], "origem": "referencia", "ativo": 0})
    ids_grupo = {tag: gid for gid, tag, _ in GRUPOS}
    for d in _historicas():
        did = demandas.criar({"lojista_id": None, "ramo": d["ramo"], "regiao": d["regiao"], "titulo": d["texto"][:80],
                              "texto": d["texto"], "respostas": None, "tags": [d["tag"]], "tags_origem": "base_demonstrativa",
                              "status": d["status"], "origem": "base_demonstrativa", "sem_match": 0, "grupo_id": ids_grupo[d["tag"]],
                              "validada_por": "admin" if d["status"] == "validada" else None})
        historico.registrar(did, "importada", "Base demonstrativa")

    # Ciclo fechado de referência (lojista 1): demanda validada + teste concluído + feedback demonstrativo.
    svc = montar(conn, settings, ia=_IASeed())
    maria, admin = Ator(Perfil.LOJISTA, 1), Ator(Perfil.ADMIN)
    res = svc.demandas.registrar(maria, 1, LOJISTAS[0]["respostas_demo"], TEXTO_MARIA)
    svc.curadoria.validar(admin, res["demanda_id"])
    teste = svc.testes.solicitar(maria, res["demanda_id"], res["ranking_startups"][0]["startup_id"], True)
    svc.testes.concluir_com_feedback_demo(maria, teste["teste_id"])
    svc.curadoria.encaminhar(admin, res["demanda_id"], res["ranking_startups"][0]["startup_id"])
    # Caso sem match (lojista 2) aguardando curadoria.
    svc.demandas.registrar(Ator(Perfil.LOJISTA, 2), 2, LOJISTAS[1]["respostas_demo"], TEXTO_JOAO)
    conn.commit()


if __name__ == "__main__":
    cfg = Settings.from_env()
    conexao = database.connect(cfg.db_path)
    carregar(conexao, cfg)
    print(f"Seed carregado em {cfg.db_path}")
