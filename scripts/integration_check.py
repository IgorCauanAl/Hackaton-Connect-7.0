#!/usr/bin/env python3
"""Verificação de integração real do ORVYN HUB.

Executa cenários ponta a ponta contra os serviços **de verdade**:

    backend operacional (:8000) ← orquestrador (:8200) → IA/MCP (:8100)

Pré-requisitos:
    ./scripts/dev.sh          # em outro terminal, mantém os serviços no ar

Execução:
    cd orquestrador && uv run python ../scripts/integration_check.py

Cenários com indisponibilidade usam processos temporários em portas efêmeras
(8199 IA heurística sem chave; 8098/8298 backend/orquestrador com IA morta).
Nada é simulado: os processos são reais, apenas isolados. O script não mata
processos que não iniciou. Os cenários de escrita gravam demandas/teste/
relatório de demonstração no banco local.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import httpx

RAIZ = Path(__file__).resolve().parents[1]
LOG_DIR = Path("/tmp/opencode/orvyn-integracao")

TEXTO_WHATSAPP = (
    "Não consigo atender todo mundo no WhatsApp fora do horário comercial "
    "e perco muitas vendas."
)

RESPOSTAS = {
    "objetivo": "vender_mais",
    "dificuldade": "atender_whatsapp",
    "canais": ["loja", "whatsapp", "instagram"],
    "ferramentas": ["planilha"],
    "orcamento": "100_300",
    "urgencia": "ate_15_dias",
}

H_LOJISTA = {"X-Perfil": "lojista", "X-Ator-Id": "1"}
H_ADMIN = {"X-Perfil": "admin"}


def H_STARTUP(startup_id: int) -> dict[str, str]:
    return {"X-Perfil": "startup", "X-Ator-Id": str(startup_id)}


class Falha(AssertionError):
    pass


def exigir(condicao: Any, mensagem: str) -> None:
    if not condicao:
        raise Falha(mensagem)


def corpo_demanda(texto: str = TEXTO_WHATSAPP) -> dict[str, Any]:
    return {"lojista_id": 1, "respostas": RESPOSTAS, "texto_livre": texto}


def resultado_json(resposta: httpx.Response) -> Any:
    try:
        return resposta.json()
    except ValueError as exc:  # pragma: no cover - diagnóstico
        raise Falha(
            f"Resposta não é JSON (HTTP {resposta.status_code}): {resposta.text[:200]}"
        ) from exc


def etapas(envelope: dict[str, Any]) -> set[str]:
    return {
        item.get("etapa")
        for item in (envelope.get("orquestracao") or {}).get("etapas") or []
    }


def avisos(envelope: dict[str, Any]) -> set[str]:
    return {
        item.get("codigo")
        for item in (envelope.get("orquestracao") or {}).get("avisos") or []
    }


# --------------------------------------------------------------------- infra
def porta_livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", porta)) != 0


def iniciar_processo(
    nome: str, comando: list[str], cwd: Path, env: dict[str, str]
) -> tuple[subprocess.Popen[bytes], Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_DIR / f"{nome}.log", "wb")  # noqa: SIM115 - fd vive com o processo
    processo = subprocess.Popen(
        comando,
        cwd=cwd,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return processo, log


def encerrar_processo(processo: subprocess.Popen[bytes], log: Any) -> None:
    if processo.poll() is None:
        try:
            os.killpg(os.getpgid(processo.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            processo.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - limpeza teimosa
            try:
                os.killpg(os.getpgid(processo.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            processo.wait(timeout=5)
    log.close()


async def esperar_http(
    url: str,
    *,
    processo: subprocess.Popen[bytes] | None = None,
    limite: float = 90.0,
) -> None:
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if processo is not None and processo.poll() is not None:
            raise Falha(
                f"processo temporário terminou antes de responder ({url}); "
                f"veja {LOG_DIR}"
            )
        try:
            async with httpx.AsyncClient(timeout=2.0) as cliente:
                resposta = await cliente.get(url)
                if resposta.status_code < 500:
                    return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.4)
    raise Falha(f"tempo esgotado esperando {url} (logs em {LOG_DIR})")


def python_ia_mcp() -> list[str]:
    venv = RAIZ / "ia-mcp" / ".venv" / "bin" / "python"
    if venv.is_file():
        return [str(venv)]
    return ["uv", "run", "--project", str(RAIZ / "ia-mcp"), "python"]


@asynccontextmanager
async def ia_heuristica_sem_chave() -> AsyncIterator[str]:
    """Sobe uma instância temporária do IA/MCP em modo heurístico, sem chave."""

    porta = 8199
    if not porta_livre(porta):
        raise Falha(f"a porta temporária {porta} está ocupada; encerre o processo")

    env = os.environ.copy()
    for chave in list(env):
        if chave.startswith("IA_MCP_AI_"):
            env.pop(chave)
    env.update(
        {
            "AI_PROVIDER": "heuristic",
            "AI_BASE_URL": "",
            "AI_MODEL": "",
            "AI_API_KEY": "",
            "IA_MCP_BACKEND_BASE_URL": "http://127.0.0.1:8000",
            "IA_MCP_API_PORT": str(porta),
        }
    )
    comando = python_ia_mcp() + [
        "-m",
        "uvicorn",
        "ia_mcp.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(porta),
        "--log-level",
        "warning",
    ]
    processo, log = iniciar_processo("ia-heuristica", comando, RAIZ / "ia-mcp", env)
    try:
        await esperar_http(
            f"http://127.0.0.1:{porta}/openapi.json", processo=processo
        )
        yield f"http://127.0.0.1:{porta}"
    finally:
        encerrar_processo(processo, log)


@asynccontextmanager
async def par_com_ia_indisponivel() -> AsyncIterator[tuple[str, str]]:
    """Backend + orquestrador temporários apontando para uma IA morta.

    Usa uma **cópia** do banco da demo, então não interfere nos dados reais.
    """

    porta_backend, porta_orq = 8098, 8298
    for porta in (porta_backend, porta_orq):
        if not porta_livre(porta):
            raise Falha(f"a porta temporária {porta} está ocupada; encerre o processo")

    origem_db = RAIZ / "back-end" / "facesp_demo.db"
    if not origem_db.is_file():
        raise Falha(
            "banco da demo não encontrado; rode ./scripts/dev.sh antes"
        )

    tmp = Path(tempfile.mkdtemp(prefix="facesp-fallback-", dir="/tmp/opencode"))
    copia_db = tmp / "demo.db"
    shutil.copy2(origem_db, copia_db)

    env_backend = os.environ.copy()
    env_backend.update(
        {
            "FACESP_DB_PATH": str(copia_db),
            "FACESP_IA_URL": "http://127.0.0.1:9",
            "FACESP_IA_TIMEOUT": "1",
        }
    )
    backend, log_backend = iniciar_processo(
        "backend-fallback",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(porta_backend),
            "--log-level",
            "warning",
        ],
        RAIZ / "back-end",
        env_backend,
    )

    env_orq = os.environ.copy()
    env_orq.update(
        {
            "ORQ_BACKEND_BASE_URL": f"http://127.0.0.1:{porta_backend}",
            "ORQ_BACKEND_TIMEOUT_SECONDS": "10",
            "ORQ_IA_BASE_URL": "http://127.0.0.1:9",
            "ORQ_IA_TIMEOUT_SECONDS": "3",
            "ORQ_FRONTEND_ENABLED": "false",
            "ORQ_API_PORT": str(porta_orq),
        }
    )
    orq, log_orq = iniciar_processo(
        "orquestrador-fallback",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "orquestrador.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(porta_orq),
            "--log-level",
            "warning",
        ],
        RAIZ / "orquestrador",
        env_orq,
    )

    try:
        await esperar_http(
            f"http://127.0.0.1:{porta_backend}/api/saude", processo=backend
        )
        await esperar_http(f"http://127.0.0.1:{porta_orq}/health", processo=orq)
        yield (
            f"http://127.0.0.1:{porta_backend}",
            f"http://127.0.0.1:{porta_orq}",
        )
    finally:
        encerrar_processo(orq, log_orq)
        encerrar_processo(backend, log_backend)
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ relatório
class Relatorio:
    def __init__(self) -> None:
        self.itens: list[tuple[str, str, str]] = []

    async def executar(self, nome: str, funcao, *args) -> Any:
        print(f"\n▶ {nome}")
        try:
            detalhe = await funcao(*args)
        except Exception as exc:  # noqa: BLE001 - queremos registrar qualquer falha
            texto = f"{type(exc).__name__}: {exc}"
            self.itens.append((nome, "FALHOU", texto))
            print(f"  ✗ FALHOU — {texto}")
            return None
        self.itens.append((nome, "OK", detalhe or ""))
        print(f"  ✓ OK — {detalhe}")
        return detalhe

    def resumo(self) -> int:
        print("\n" + "═" * 72)
        print("RESUMO DA VERIFICAÇÃO DE INTEGRAÇÃO")
        print("═" * 72)
        for indice, (nome, estado, detalhe) in enumerate(self.itens, start=1):
            marca = "✓" if estado == "OK" else "✗"
            print(f"{marca} {indice:02d}. {nome}")
            if detalhe:
                print(f"      {detalhe}")
        falhas = sum(1 for _, estado, _ in self.itens if estado != "OK")
        print("─" * 72)
        print(f"{len(self.itens) - falhas}/{len(self.itens)} cenários OK")
        return 0 if falhas == 0 else 1


# ------------------------------------------------------------------ cenários
async def cenario_saude_frontend(args: argparse.Namespace) -> str:
    async with httpx.AsyncClient(timeout=30.0) as c:
        for nome, url in (
            ("backend", f"{args.backend}/api/saude"),
            ("IA/MCP", f"{args.ia}/openapi.json"),
            ("orquestrador", f"{args.orq}/health"),
        ):
            resposta = await c.get(url)
            exigir(resposta.status_code == 200, f"{nome} não respondeu 200: {url}")

        raiz = await c.get(f"{args.orq}/")
        exigir(raiz.status_code == 200, f"frontend / retornou {raiz.status_code}")
        exigir('id="root"' in raiz.text, "HTML do frontend sem o container React")

        paginas = [
            "index",
            "chat",
            "resultados",
            "solucao",
            "teste",
            "oportunidade",
            "admin",
            "admin-demandas",
            "admin-demanda",
            "admin-radar",
            "admin-padroes",
        ]
        for pagina in paginas:
            resposta = await c.get(f"{args.orq}/{pagina}.html")
            exigir(
                resposta.status_code == 200,
                f"página /{pagina}.html retornou {resposta.status_code}",
            )
            exigir("text/html" in resposta.headers.get("content-type", ""), pagina)

        proxy = await c.get(f"{args.orq}/api/lojistas", headers=H_LOJISTA)
        exigir(proxy.status_code == 200, f"proxy /api/lojistas: {proxy.status_code}")
        exigir(isinstance(resultado_json(proxy), list), "proxy não devolveu lista")

    return "3 serviços no ar, 11 páginas e proxy GET /api funcionando"


async def cenario_demanda_com_ia(
    args: argparse.Namespace,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=90.0) as c:
        resposta = await c.post(
            f"{args.orq}/orquestracao/demandas",
            headers=H_LOJISTA,
            json=corpo_demanda(),
        )
        exigir(
            resposta.status_code == 201,
            f"registro retornou {resposta.status_code}: {resposta.text[:300]}",
        )
        envelope = resultado_json(resposta)
        dados = envelope["resultado"]

        exigir(dados["status"] == "sucesso", f"status inesperado: {dados['status']}")
        exigir(isinstance(dados["demanda_id"], int), "demanda_id ausente")
        exigir(dados["tags_identificadas"], "IA não retornou tags")
        exigir(
            dados["tags_origem"] == "ia",
            f"tags deveriam vir da IA, vieram de '{dados['tags_origem']}'",
        )
        exigir("classificacao_ia" in etapas(envelope), "etapa de classificação ausente")
        exigir(dados["ranking_startups"], "ranking vazio para demanda compatível")
        exigir(len(dados["ranking_startups"]) <= 3, "ranking com mais de 3 startups")
        for item in dados["ranking_startups"]:
            exigir(0 <= int(item["indice"]) <= 100, f"índice fora de 0–100: {item}")

    return {
        "demanda_id": dados["demanda_id"],
        "startup_id": dados["ranking_startups"][0]["startup_id"],
        "tags": dados["tags_identificadas"],
        "ranking": dados["ranking_startups"],
    }


async def cenario_heuristica_sem_chave(args: argparse.Namespace) -> str:
    async with ia_heuristica_sem_chave() as base:
        async with httpx.AsyncClient(timeout=30.0) as c:
            resposta = await c.post(
                f"{base}/ia/classificar", json={"texto": TEXTO_WHATSAPP}
            )
            exigir(resposta.status_code == 200, f"classificar: {resposta.status_code}")
            tags = resultado_json(resposta).get("tags")
            exigir(isinstance(tags, list) and tags, "heurístico não retornou tags")
            exigir(
                {"atendimento", "whatsapp"} & set(tags),
                f"tags inesperadas do heurístico: {tags}",
            )
    return f"instância temporária sem chave retornou {tags}"


async def cenario_fallback_ia(args: argparse.Namespace) -> str:
    async with par_com_ia_indisponivel() as (_, orq):
        async with httpx.AsyncClient(timeout=90.0) as c:
            resposta = await c.post(
                f"{orq}/orquestracao/demandas",
                headers=H_LOJISTA,
                json=corpo_demanda(),
            )
            exigir(
                resposta.status_code == 201,
                f"registro com IA morta: {resposta.status_code} {resposta.text[:200]}",
            )
            envelope = resultado_json(resposta)
            dados = envelope["resultado"]
            exigir(
                dados["tags_origem"] == "botoes",
                f"fallback deveria usar botões, usou '{dados['tags_origem']}'",
            )
            exigir(
                "ia_indisponivel" in avisos(envelope),
                "aviso ia_indisponivel não foi gerado",
            )

            insights = await c.post(
                f"{orq}/orquestracao/insights", headers=H_ADMIN
            )
            exigir(insights.status_code == 200, f"insights: {insights.status_code}")
            radar = resultado_json(insights)["resultado"]["radar"]
            exigir(radar, "radar vazio no fallback")
            exigir(
                all(item["origem"] == "referencia" for item in radar),
                "fallback de insights não usou as interpretações de referência",
            )
    return (
        "demanda registrada com tags dos botões e insights de referência "
        "quando a IA está fora do ar"
    )


async def cenario_matching(
    args: argparse.Namespace, demanda: dict[str, Any]
) -> str:
    demanda_id = demanda["demanda_id"]
    async with httpx.AsyncClient(timeout=30.0) as c:
        resposta = await c.get(
            f"{args.orq}/orquestracao/demandas/{demanda_id}/matching",
            headers=H_LOJISTA,
        )
        exigir(resposta.status_code == 200, f"matching: {resposta.status_code}")
        dados = resultado_json(resposta)["resultado"]
        ranking = dados["ranking_startups"]
        exigir(isinstance(dados["sem_match"], bool), "sem_match ausente")
        exigir(ranking, "ranking vazio")
        exigir(len(ranking) <= 3, "ranking acima de 3")
        for item in ranking:
            indice = int(item["indice"])
            exigir(0 <= indice <= 100, f"índice {indice} fora de 0–100")
            exigir(item["nome"] and item["motivo"], "startup sem nome/motivo")
            criterios = item["criterios"]
            exigir(len(criterios) >= 8, f"critérios insuficientes: {len(criterios)}")
            for criterio in criterios:
                for campo in ("criterio", "peso", "pontuacao", "pontos", "motivo"):
                    exigir(campo in criterio, f"critério sem '{campo}'")
                exigir(criterio["motivo"], "critério sem justificativa")
            soma = sum(float(criterio["pontos"]) for criterio in criterios)
            exigir(
                abs(soma - indice) <= 1.0,
                f"soma dos pontos ({soma:.1f}) não fecha com o índice ({indice})",
            )

        direto = await c.get(
            f"{args.backend}/api/demandas/{demanda_id}/matching",
            headers=H_LOJISTA,
        )
        exigir(direto.status_code == 200, "matching direto no backend falhou")
        exigir(
            resultado_json(direto) == dados,
            "orquestrador alterou o matching do backend",
        )
    return (
        f"{len(ranking)} recomendação(ões), índices "
        f"{[item['indice'] for item in ranking]} e 8 critérios justificados"
    )


async def cenario_validacao(
    args: argparse.Namespace, demanda: dict[str, Any]
) -> str:
    demanda_id = demanda["demanda_id"]
    async with httpx.AsyncClient(timeout=30.0) as c:
        fila = await c.get(
            f"{args.orq}/api/admin/demandas",
            params={"status": "pendente"},
            headers=H_ADMIN,
        )
        exigir(fila.status_code == 200, f"fila admin: {fila.status_code}")
        ids = {item["id"] for item in resultado_json(fila)}
        exigir(demanda_id in ids, "demanda não apareceu na fila da curadoria")

        resposta = await c.post(
            f"{args.orq}/orquestracao/demandas/{demanda_id}/validar",
            headers=H_ADMIN,
        )
        exigir(resposta.status_code == 200, f"validar: {resposta.status_code}")
        corpo = resultado_json(resposta)["resultado"]
        exigir(corpo.get("status") == "validado", f"status: {corpo.get('status')}")

        detalhe = await c.get(
            f"{args.orq}/api/admin/demandas/{demanda_id}", headers=H_ADMIN
        )
        exigir(
            resultado_json(detalhe)["status"] == "validada",
            "backend não persistiu a validação",
        )
    return f"demanda {demanda_id} validada e persistida pelo backend"


async def cenario_insights_padroes(args: argparse.Namespace) -> str:
    vocabulario = json.loads(
        (RAIZ / "back-end" / "config" / "vocabulario.json").read_text("utf-8")
    )["tags"]
    async with httpx.AsyncClient(timeout=120.0) as c:
        resposta = await c.post(f"{args.orq}/orquestracao/insights", headers=H_ADMIN)
        exigir(resposta.status_code == 200, f"insights: {resposta.status_code}")
        radar = resultado_json(resposta)["resultado"]["radar"]
        exigir(radar, "radar vazio")
        for item in radar:
            exigir(isinstance(item["quantidade"], int), "quantidade não inteira")
            exigir(isinstance(item["pontuacao"], (int, float)), "pontuação inválida")
            exigir(item["origem"] in ("ia", "referencia"), "origem inválida")

        padroes = await c.get(f"{args.orq}/orquestracao/padroes", headers=H_ADMIN)
        exigir(padroes.status_code == 200, f"padrões: {padroes.status_code}")
        itens = resultado_json(padroes)["resultado"]["radar"]
        exigir(len(itens) == len(radar), "padrões divergiram do radar")
        tags = [item.get("tag") for item in itens if item.get("tag")]
        exigir(tags, "nenhuma tag derivada para os grupos")
        exigir(set(tags) <= set(vocabulario), f"tag fora do vocabulário: {tags}")

    return (
        f"{len(radar)} grupos no radar; tags derivadas {sorted(set(tags))}"
    )


async def chamar_mcp(url: str, ferramenta: str, argumentos: dict[str, Any]) -> Any:
    from fastmcp import Client

    async with Client(url, timeout=30) as cliente:
        resposta = await cliente.call_tool(
            ferramenta, argumentos, raise_on_error=False
        )
    if getattr(resposta, "is_error", False):
        raise Falha(f"ferramenta MCP '{ferramenta}' retornou erro")
    dados = getattr(resposta, "data", None)
    if dados is not None:
        return dados
    for bloco in getattr(resposta, "content", None) or []:
        texto = getattr(bloco, "text", None)
        if texto:
            return json.loads(texto)
    raise Falha(f"ferramenta MCP '{ferramenta}' sem payload")


async def cenario_mcp_radar(args: argparse.Namespace) -> str:
    dados = await chamar_mcp(args.mcp, "listar_radar", {})
    exigir(isinstance(dados, list) and dados, "listar_radar não retornou lista")
    for item in dados:
        for campo in ("dor", "quantidade", "sugestao_ia", "origem"):
            exigir(campo in item, f"listar_radar sem '{campo}'")
        exigir(isinstance(item["quantidade"], int), "quantidade não inteira")
    return f"listar_radar devolveu {len(dados)} grupo(s) do backend real"


async def cenario_mcp_startups(args: argparse.Namespace) -> str:
    dados = await chamar_mcp(args.mcp, "buscar_startups", {"tag": "atendimento"})
    exigir(isinstance(dados, list) and dados, "buscar_startups não retornou lista")
    for item in dados:
        for campo in ("id", "nome", "descricao", "solucao", "segmentos", "tags"):
            exigir(campo in item, f"buscar_startups sem '{campo}'")
        exigir(isinstance(item["id"], int), "startup sem id inteiro")
        exigir("atendimento" in item["tags"], "filtro de tag não foi aplicado")
    return f"buscar_startups(tag=atendimento) devolveu {len(dados)} startup(s)"


async def cenario_encaminhamento(
    args: argparse.Namespace, demanda: dict[str, Any]
) -> str:
    demanda_id = demanda["demanda_id"]
    startup_id = demanda["startup_id"]
    headers_startup = H_STARTUP(startup_id)

    async with httpx.AsyncClient(timeout=90.0) as c:
        resposta = await c.post(
            f"{args.orq}/orquestracao/demandas/{demanda_id}/encaminhar",
            headers=H_ADMIN,
            json={"startup_id": startup_id},
        )
        exigir(resposta.status_code == 200, f"encaminhar: {resposta.status_code}")
        dados = resultado_json(resposta)["resultado"]
        exigir(dados["status"] == "encaminhada", "status não mudou para encaminhada")
        relatorio_id = dados["relatorio_id"]
        exigir(dados["relatorio"]["demanda_id"] == demanda_id, "relatório de outra demanda")
        exigir(dados["relatorio"]["startup_id"] == startup_id, "relatório de outra startup")

        anonimo = await c.get(
            f"{args.orq}/orquestracao/relatorios/{relatorio_id}",
            params={"versao": "anonimizada"},
            headers=headers_startup,
        )
        exigir(anonimo.status_code == 200, f"relatório anônimo: {anonimo.status_code}")
        documento = resultado_json(anonimo)["resultado"]
        exigir(documento["versao"] == "anonimizada", "versão incorreta")
        for bloco in ("resumo", "perfil_loja", "dor_contexto", "compatibilidade", "sinal_mercado"):
            exigir(bloco in documento["blocos"], f"bloco '{bloco}' ausente")
        exigir("nome" not in documento["blocos"]["perfil_loja"], "nome do lojista exposto")
        exigir(
            "texto_livre" not in documento["blocos"]["dor_contexto"],
            "texto livre do lojista exposto na versão anônima",
        )

        oportunidades = await c.get(
            f"{args.orq}/orquestracao/startups/{startup_id}/relatorios",
            headers=headers_startup,
        )
        exigir(oportunidades.status_code == 200, "oportunidades da startup falharam")
        ids = {item["relatorio_id"] for item in resultado_json(oportunidades)["resultado"]}
        exigir(relatorio_id in ids, "relatório não listado para a startup")

        teste = await c.post(
            f"{args.orq}/orquestracao/testes",
            headers=H_LOJISTA,
            json={
                "demanda_id": demanda_id,
                "startup_id": startup_id,
                "autorizacao": True,
            },
        )
        exigir(teste.status_code == 201, f"registro de teste: {teste.status_code}")
        teste_id = resultado_json(teste)["resultado"]["teste_id"]

        consulta = await c.get(
            f"{args.orq}/orquestracao/testes/{teste_id}", headers=H_LOJISTA
        )
        exigir(consulta.status_code == 200, "consulta do teste falhou")
        exigir(resultado_json(consulta)["resultado"]["status"] == "solicitado", "status do teste")

        feedback = await c.post(
            f"{args.orq}/orquestracao/testes/{teste_id}/feedback", headers=H_LOJISTA
        )
        exigir(feedback.status_code == 200, f"feedback: {feedback.status_code}")
        avaliacao = resultado_json(feedback)["resultado"]
        exigir(avaliacao["teste_id"] == teste_id, "feedback de outro teste")
        exigir(isinstance(avaliacao["nota"], int), "feedback sem nota")

        completo = await c.get(
            f"{args.orq}/orquestracao/relatorios/{relatorio_id}",
            params={"versao": "completa"},
            headers=headers_startup,
        )
        exigir(completo.status_code == 200, f"relatório completo: {completo.status_code}")
        documento = resultado_json(completo)["resultado"]
        exigir(documento["versao"] == "completa", "versão completa esperada")
        exigir("proximo_passo" in documento["blocos"], "bloco próximo passo ausente")

    return (
        f"relatório {relatorio_id}, teste {teste_id} e feedback demonstrativo "
        "concluídos com autorização"
    )


# ----------------------------------------------------------------------- main
def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="http://localhost:8000")
    parser.add_argument("--ia", default="http://localhost:8100")
    parser.add_argument("--orq", default="http://localhost:8200")
    parser.add_argument("--mcp", default="http://localhost:8100/mcp/")
    return parser.parse_args()


async def main() -> int:
    args = argumentos()
    relatorio = Relatorio()

    await relatorio.executar("Saúde dos serviços e frontend React", cenario_saude_frontend, args)

    demanda = await relatorio.executar(
        "Registro de demanda com classificação via IA", cenario_demanda_com_ia, args
    )

    await relatorio.executar(
        "IA/MCP heurística sem chave (instância isolada)",
        cenario_heuristica_sem_chave,
        args,
    )

    await relatorio.executar(
        "Fallback quando a IA está indisponível (instâncias isoladas)",
        cenario_fallback_ia,
        args,
    )

    if demanda is None:
        print("\n! Cenários dependentes foram pulados: o registro da demanda falhou.")
    else:
        await relatorio.executar("Contrato do matching (0–100, top 3, critérios)", cenario_matching, args, demanda)
        await relatorio.executar("Validação da demanda pela curadoria", cenario_validacao, args, demanda)

    await relatorio.executar(
        "Insights, radar e padrões (quantidades do backend)", cenario_insights_padroes, args
    )
    await relatorio.executar("MCP — listar_radar (FastMCP real)", cenario_mcp_radar, args)
    await relatorio.executar("MCP — buscar_startups (FastMCP real)", cenario_mcp_startups, args)

    if demanda is not None:
        await relatorio.executar(
            "Encaminhamento, relatório anônimo e ciclo de teste/feedback",
            cenario_encaminhamento,
            args,
            demanda,
        )

    return relatorio.resumo()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
