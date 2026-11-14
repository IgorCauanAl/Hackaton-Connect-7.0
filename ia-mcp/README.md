# IA/MCP — FACESP Match

Serviço independente responsável pelos recursos de IA e pelas ferramentas MCP do
FACESP Match. O módulo **não** implementa backend operacional, orquestrador,
persistência, matching ou autenticação.

## O que o serviço entrega

- `POST /ia/classificar` → `{"tags": [...]}`
- `POST /ia/resumir` → `{"resumo": "..."}`
- `POST /ia/insights` → `{"interpretacoes": {"<id-do-grupo>": "..."}}`
- Servidor MCP montado em `/mcp/` com as ferramentas somente leitura:
  - `listar_radar` → `GET {backend}/api/mcp/radar`
  - `buscar_startups(tag, segmento)` → `GET {backend}/api/mcp/startups`

## Instalação

```bash
cd ia-mcp
uv sync
cp .env.example .env
```

## Execução

```bash
uv run uvicorn ia_mcp.main:app --host 0.0.0.0 --port 8100
```

- API de IA: `http://localhost:8100/ia/*`
- MCP (Streamable HTTP): `http://localhost:8100/mcp/`
- Documentação interativa: `http://localhost:8100/docs`

## Testes

```bash
uv run pytest
```

Os testes não usam rede real: provedores de IA e backend operacional são
substituídos por `httpx.MockTransport` e dublês.

## Configuração

A configuração vem de variáveis de ambiente e de um `.env` opcional. Os nomes
canônicos do provedor são `AI_PROVIDER`, `AI_BASE_URL`, `AI_API_KEY`,
`AI_MODEL` e `AI_TIMEOUT`; os nomes prefixados `IA_MCP_AI_*` também são aceitos
e têm precedência quando ambos existem. O restante usa o prefixo `IA_MCP_`.
Veja `.env.example` para a lista completa. Nenhuma URL, credencial ou caminho é
fixado no código.

Sem `AI_API_KEY`/`AI_MODEL`, o serviço usa o classificador heurístico local e
funciona offline. A chave nunca é logada nem devolvida nas respostas HTTP.

Para subir backend + IA/MCP + orquestrador de uma vez, use `../scripts/dev.sh`
na raiz do repositório.

## Contratos

Consulte [`docs/ia-mcp.md`](docs/ia-mcp.md) para os contratos completos, o
formato do vocabulário JSON, o comportamento de fallback e o checklist de
integração com o backend operacional.
