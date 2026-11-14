# AGENTS.md

## Project

Hackathon challenge (Connect 7.0): team selected FACESP — "Conectar as demandas do varejo às soluções tecnológicas para desenvolver um MVP" (connect retail demands to tech solutions, build an MVP). READMEs and code comments are in Portuguese.

## Repo state

Three Python services, all run with `uv`/Python 3.12+ unless noted:

- `back-end/` — monolito modular FastAPI + SQLite (fonte da verdade: matching, persistência, autorização, CRUDs). Testes com `python3 -m unittest discover -s tests -v`.
- `ia-mcp/` — FastAPI + FastMCP em processo único (porta 8100): `/ia/classificar`, `/ia/resumir`, `/ia/insights` e MCP somente leitura em `/mcp/`. Testes com `uv run pytest`.
- `orquestrador/` — BFF (porta 8200) que compõe backend + IA/MCP, valida contratos, centraliza erros e aplica idempotência. Testes com `uv run pytest`.

Working branch is `IA/MCP` (created from `main`); `main` is the default branch. IntelliJ IDEA metadata lives in `.idea/` (untracked; `workspace.xml` is gitignored by `.idea/.gitignore`).

## Conventions / gotchas

- Backend requires `X-Perfil: lojista|startup|admin|mcp` (and optional `X-Ator-Id`) on every route; authorization stays in the backend. The orchestrator only propagates these headers.
- The IA/MCP never computes matching, weights, quantities or status and never persists. Official tags live in `back-end/config/vocabulario.json`, mirrored in `ia-mcp/src/ia_mcp/vocabulary/tags.json` (anti-drift test).
- All configuration is via environment variables (`FACESP_*`, `IA_MCP_*`, `ORQ_*`); no fixed URLs, credentials or paths in code.
- Total IA failure returns `503 {"detail": "Serviço de IA indisponível"}`; the backend has deterministic fallbacks, so the orchestrator downgrades it to a warning.
- Keep `.gitignore` Java entries only if the team still opens the repo in IntelliJ; Python artifacts are ignored by service-level `.gitignore` files.
