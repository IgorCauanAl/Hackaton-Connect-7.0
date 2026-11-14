import sqlite3
import unittest

from app import seed
from app.container import montar
from app.core.config import Settings
from app.core.errors import AcessoNegado, RegraDeNegocio
from app.core.security import Ator, Perfil
from app.infra import database
from app.infra.ia_gateway import IAIndisponivelGateway

ADMIN, MARIA, JOAO = Ator(Perfil.ADMIN), Ator(Perfil.LOJISTA, 1), Ator(Perfil.LOJISTA, 2)


class IAFake:
    def extrair_tags(self, texto): return ["atendimento", "whatsapp", "tag_fora_do_vocabulario"]
    def resumir(self, texto): return "Resumo da IA"
    def interpretar_grupos(self, grupos): return {g["chave"]: f"IA: {g['titulo']}" for g in grupos}


def novo_ambiente(ia=None):
    conn = database.connect(":memory:")
    seed.carregar(conn, Settings())
    return conn, montar(conn, Settings(), ia=ia or IAIndisponivelGateway())


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.svc = novo_ambiente()
        self.maria = LOJ = seed.LOJISTAS[0]["respostas_demo"]

    def test_maria_recebe_ranking_ordenado_e_deterministico(self):
        a = self.svc.demandas.registrar(MARIA, 1, self.maria, seed.TEXTO_MARIA)
        b = self.svc.demandas.registrar(MARIA, 1, self.maria, seed.TEXTO_MARIA)
        self.assertEqual(a["status"], "sucesso")
        self.assertLessEqual(len(a["ranking_startups"]), 3)
        indices = [x["indice"] for x in a["ranking_startups"]]
        self.assertEqual(indices, sorted(indices, reverse=True))
        self.assertEqual(a["ranking_startups"][0]["nome"], "ZapBot")
        self.assertGreaterEqual(indices[0], 85)
        self.assertEqual(a["ranking_startups"], b["ranking_startups"])  # determinístico
        self.assertTrue(all(0 <= i <= 100 for i in indices))

    def test_petshop_sem_match_vai_para_fila(self):
        res = self.svc.demandas.registrar(JOAO, 2, seed.LOJISTAS[1]["respostas_demo"], seed.TEXTO_JOAO)
        self.assertEqual(res["status"], "sem_match")
        self.assertEqual(res["ranking_startups"], [])
        fila = [d["id"] for d in self.svc.curadoria.fila(ADMIN)]
        self.assertIn(res["demanda_id"], fila)

    def test_fallback_pelos_botoes_quando_ia_falha(self):
        res = self.svc.demandas.registrar(MARIA, 1, self.maria, seed.TEXTO_MARIA)
        self.assertEqual(res["tags_origem"], "botoes")
        self.assertEqual(res["tags_identificadas"], ["atendimento", "whatsapp"])

    def test_tags_da_ia_sao_filtradas_pelo_vocabulario(self):
        _, svc = novo_ambiente(IAFake())
        res = svc.demandas.registrar(MARIA, 1, self.maria, seed.TEXTO_MARIA)
        self.assertEqual(res["tags_origem"], "ia")
        self.assertNotIn("tag_fora_do_vocabulario", res["tags_identificadas"])


class FluxoTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.svc = novo_ambiente()
        self.res = self.svc.demandas.registrar(MARIA, 1, seed.LOJISTAS[0]["respostas_demo"], seed.TEXTO_MARIA)
        self.did = self.res["demanda_id"]
        self.sid = self.res["ranking_startups"][0]["startup_id"]

    def test_teste_exige_autorizacao_e_startup_recomendada(self):
        with self.assertRaises(RegraDeNegocio):
            self.svc.testes.solicitar(MARIA, self.did, self.sid, False)
        with self.assertRaises(RegraDeNegocio):
            self.svc.testes.solicitar(MARIA, self.did, 4, True)  # GestorPro não foi recomendada
        ok = self.svc.testes.solicitar(MARIA, self.did, self.sid, True)
        self.assertEqual(ok["dias"], 15)

    def test_lojista_nao_acessa_demanda_de_outro(self):
        with self.assertRaises(AcessoNegado):
            self.svc.demandas.obter(JOAO, self.did)
        with self.assertRaises(AcessoNegado):
            self.svc.demandas.registrar(JOAO, 1, seed.LOJISTAS[0]["respostas_demo"], "x")

    def test_feedback_demo_conclui_teste(self):
        t = self.svc.testes.solicitar(MARIA, self.did, self.sid, True)["teste_id"]
        fb = self.svc.testes.concluir_com_feedback_demo(MARIA, t)
        self.assertEqual(fb["nota"], 5)
        self.assertEqual(self.svc.testes.obter(MARIA, t)["status"], "concluido")
        self.assertTrue(fb["demonstrativo"])
        # startup só vê os próprios feedbacks
        outros = self.svc.testes.feedbacks(Ator(Perfil.STARTUP, 7))
        self.assertEqual(outros, [])

    def test_validar_so_pendentes_e_so_admin(self):
        with self.assertRaises(AcessoNegado):
            self.svc.curadoria.validar(MARIA, self.did)
        self.svc.curadoria.validar(ADMIN, self.did)
        with self.assertRaises(RegraDeNegocio):
            self.svc.curadoria.validar(ADMIN, self.did)

    def test_relatorio_completo_exige_consentimento(self):
        self.svc.curadoria.validar(ADMIN, self.did)
        self.svc.curadoria.encaminhar(ADMIN, self.did, self.sid)
        startup = Ator(Perfil.STARTUP, self.sid)
        rel_id = self.svc.relatorios.listar_da_startup(startup, self.sid)[0]["relatorio_id"]
        anon = self.svc.relatorios.ver(startup, rel_id, "anonimizada")["blocos"]
        self.assertNotIn("texto_livre", anon["dor_contexto"])
        self.assertNotIn("nome", anon["perfil_loja"])
        self.assertNotIn("proximo_passo", anon)
        with self.assertRaises(AcessoNegado):
            self.svc.relatorios.ver(startup, rel_id, "completa")
        self.svc.testes.solicitar(MARIA, self.did, self.sid, True)
        completa = self.svc.relatorios.ver(startup, rel_id, "completa")["blocos"]
        self.assertEqual(completa["dor_contexto"]["texto_livre"], seed.TEXTO_MARIA)
        self.assertEqual(completa["proximo_passo"]["janela_dias"], 15)
        with self.assertRaises(AcessoNegado):
            self.svc.relatorios.ver(Ator(Perfil.STARTUP, 99), rel_id)


class RadarTests(unittest.TestCase):
    def test_fallback_usa_versao_de_referencia_e_so_validadas(self):
        _, svc = novo_ambiente()
        radar = svc.radar.gerar_insights(ADMIN)["radar"]
        self.assertEqual(radar[0]["titulo"], "Atendimento WhatsApp")
        self.assertEqual(radar[0]["quantidade"], 12)  # a pendente não conta
        self.assertTrue(radar[0]["destaque"] and radar[0]["requer_validacao_humana"])
        self.assertEqual(radar[0]["origem"], "referencia")
        qtds = [i["quantidade"] for i in radar]
        self.assertEqual(qtds, sorted(qtds, reverse=True))

    def test_validar_pendente_aumenta_contagem_e_ia_interpreta(self):
        _, svc = novo_ambiente(IAFake())
        pendente = next(d for d in svc.curadoria.fila(ADMIN) if "WhatsApp" in d["texto"] and d["lojista_id"] is None)
        svc.curadoria.validar(ADMIN, pendente["id"])
        radar = svc.radar.gerar_insights(ADMIN)["radar"]
        self.assertEqual(radar[0]["quantidade"], 13)
        self.assertEqual(radar[0]["origem"], "ia")
        self.assertTrue(radar[0]["sugestao"].startswith("IA:"))

    def test_mcp_somente_leitura(self):
        _, svc = novo_ambiente()
        svc.radar.gerar_insights(ADMIN)
        mcp = Ator(Perfil.MCP)
        self.assertGreater(len(svc.mcp.listar_radar(mcp)), 0)
        self.assertEqual({s["nome"] for s in svc.mcp.buscar_startups(mcp, tag="fidelizacao")}, {"FideliPay"})
        self.assertFalse([m for m in dir(svc.mcp) if m.startswith(("criar", "atualizar", "excluir", "validar"))])
        with self.assertRaises(AcessoNegado):
            svc.mcp.listar_radar(MARIA)

    def test_dashboard_admin(self):
        _, svc = novo_ambiente()
        d = svc.paineis.admin(ADMIN)
        self.assertEqual((d["lojistas"], d["startups"]), (2, 7))
        self.assertTrue(25 <= d["demandas"] <= 30)


if __name__ == "__main__":
    unittest.main()
