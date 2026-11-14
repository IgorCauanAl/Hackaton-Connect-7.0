# FACESP Match — Backend operacional (monolito modular)

Python + FastAPI + SQLite. A IA e o MCP são módulos de outras pessoas: aqui só existe a **porta** (`IAGateway`) e fallbacks.

## Rodar
```bash
pip install -r requirements.txt
python -m app.seed                 # apaga e recria o banco da demo (rodar no início do dia)
uvicorn app.main:app --reload      # também faz o seed sozinho se o banco estiver vazio
python -m unittest discover -s tests -v
```
Variáveis (`.env.example`): `FACESP_DB_PATH`, `FACESP_IA_URL` (vazio = IA indisponível, usa fallbacks), `FACESP_IA_TIMEOUT`.

## Camadas (dependências só apontam para dentro)
```
api/        FastAPI: rotas finas, schemas Pydantic, deps (ator por header)
services/   casos de uso + regras + autorização por perfil
domain/     matching (Strategy por critério, puro/determinístico) e roteiro do chat
infra/      repositories (único lugar com SQL), database, ia_gateway (porta + adaptadores)
container.py  composition root (DI manual)     core/  config, erros, segurança
config/     matching.json (pesos, corte 50, frases de motivo) e vocabulario.json (tags)
```
Padrões: Repository, Strategy (critérios), Ports & Adapters + Null Object (IA), Composition Root, exceções de domínio → HTTP.

## Acesso (demo)
Headers: `X-Perfil: lojista|startup|admin|mcp` e `X-Ator-Id: <id do lojista/startup>`.

## Endpoints
| Quem | Método e rota |
|---|---|
| Lojista | `GET /api/chat/roteiro` · `GET /api/lojistas` · `GET /api/lojistas/{id}` · `POST /api/demandas` · `GET /api/demandas/{id}/matching` · `POST /api/testes` · `POST /api/testes/{id}/feedback-demo` · `GET /api/feedbacks` |
| Startup | `GET /api/startups[/{id}]` · `GET /api/startups/{id}/dashboard` · `GET /api/startups/{id}/oportunidades` · `GET /api/relatorios/{id}?versao=anonimizada\|completa` |
| Associação | `GET /api/admin/dashboard` · `GET /api/admin/demandas?status=` · `GET /api/admin/demandas/{id}` · `POST .../validar` · `POST .../encaminhar {startup_id}` · `POST /api/admin/insights/gerar` · `GET /api/admin/radar` · `GET /api/admin/radar/{grupo_id}/demandas` · `GET /api/admin/feedbacks` |
| MCP (só leitura) | `GET /api/mcp/radar` · `GET /api/mcp/startups?tag=&segmento=` (ou importe `LeituraMcpService`) |

## Regras principais
- **Matching** (`domain/matching.py`): 8 critérios com pesos em `config/matching.json` (soma 100), índice 0–100, corte 50, até 3 resultados, desempate por nome. A IA só fornece as tags; o cálculo é do backend.
- **Fallbacks**: IA falhou → tags vêm das respostas dos botões; resumo = texto truncado; insights → versão de referência pré-gerada (`origem: "referencia"`).
- **Insights**: só demandas `validada`/`encaminhada` entram. Quantidades e pontuação são calculadas pelo código; a IA só interpreta.
- **Sem match**: demanda vai para a fila (`sem_match=true`) e entra nos insights quando validada.
- **Teste**: exige `autorizacao=true` e startup entre as recomendadas; 15 dias; `solicitado → concluido`.
- **Relatório (6 blocos)**: anonimizado (ramo, tipo, porte, região, tags, resumo) ou completo (só com consentimento do lojista).

## Contrato que o colega de IA precisa atender (HTTP em `FACESP_IA_URL`)
```
POST /ia/classificar {"texto"}  -> {"tags": [..]}      (tags fora de config/vocabulario.json são descartadas)
POST /ia/resumir     {"texto"}  -> {"resumo": ".."}
POST /ia/insights    {"grupos": [{"chave","titulo","quantidade","exemplos"}]} -> {"interpretacoes": {chave: ".."}}
```
