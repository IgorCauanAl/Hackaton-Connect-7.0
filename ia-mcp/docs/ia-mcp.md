# Módulo IA/MCP — FACESP Match

Serviço independente de IA e MCP. Este documento descreve instalação,
configuração, contratos e integração com o backend operacional.

## 1. Fronteira de responsabilidade

| Componente | Responsabilidade |
|---|---|
| **IA/MCP** (este módulo) | Classificar texto, resumir demandas, interpretar grupos, abstrair o provedor de IA, aplicar fallback e expor ferramentas MCP somente leitura. |
| **Backend operacional** | Persistência, schema, migrations, CRUDs, matching, autenticação e API REST operacional. |
| **Orquestrador / `IAGateway`** | Buscar dados, chamar os endpoints de IA por HTTP, decidir persistência e acionar o fallback de fluxo. |

O módulo **não** acessa banco de dados, **não** persiste nada, **não** calcula
matching e **não** implementa endpoints operacionais.

## 2. Arquitetura

Um único processo Uvicorn atende tanto a API de IA quanto o servidor MCP:

```text
Backend / IAGateway
  │  POST /ia/classificar
  │  POST /ia/resumir
  │  POST /ia/insights
  ▼
┌──────────────────────────────────────────────┐
│ ia-mcp — Uvicorn :8100                       │
│                                              │
│  FastAPI                                     │
│   ├── /ia/classificar                        │
│   ├── /ia/resumir                            │
│   ├── /ia/insights                           │
│   └── /mcp/  ← FastMCP (Streamable HTTP)     │
│                                              │
│  Cadeia de IA: modelo → heurístico local     │
│  Cliente HTTP do backend (somente GET)       │
└──────────────────────────────────────────────┘
  │  GET /api/mcp/radar
  │  GET /api/mcp/startups?tag=&segmento=
  ▼
Backend operacional
```

O `IAGateway` chama a IA por HTTP. As ferramentas MCP chamam a API REST do
backend operacional; não há acesso direto ao SQLite.

## 3. Instalação

Requisitos: Python ≥ 3.12 e [`uv`](https://docs.astral.sh/uv/).

```bash
cd ia-mcp
uv sync
cp .env.example .env
```

## 4. Execução

```bash
uv run uvicorn ia_mcp.main:app --host 0.0.0.0 --port 8100
```

Ou, usando as variáveis `IA_MCP_API_HOST` / `IA_MCP_API_PORT`:

```bash
uv run python -m ia_mcp.main
```

Endpoints:

- API de IA: `http://localhost:8100/ia/*`
- MCP: `http://localhost:8100/mcp/`
- OpenAPI: `http://localhost:8100/docs`

## 5. Configuração

Todas as variáveis usam o prefixo `IA_MCP_` e podem vir do ambiente ou de um
arquivo `.env`. Nenhuma URL, credencial ou caminho de recurso externo é fixado
no código.

| Variável | Padrão | Descrição |
|---|---|---|
| `IA_MCP_BACKEND_BASE_URL` | `http://localhost:8000` | URL do backend operacional usada pelas ferramentas MCP. |
| `IA_MCP_BACKEND_TIMEOUT_SECONDS` | `10` | Timeout das chamadas ao backend. |
| `IA_MCP_AI_PROVIDER` | `auto` | `auto`, `openai_compatible` ou `heuristic`. |
| `IA_MCP_AI_BASE_URL` | vazio | Base da API OpenAI-compatible (ex.: `https://api.openai.com/v1`). |
| `IA_MCP_AI_API_KEY` | vazio | Chave do provedor. Não é logada. |
| `IA_MCP_AI_MODEL` | vazio | Modelo usado nas chamadas. |
| `IA_MCP_AI_TIMEOUT_SECONDS` | `20` | Timeout das chamadas ao provedor. |
| `IA_MCP_VOCABULARY_PATH` | `src/ia_mcp/vocabulary/tags.json` | JSON de tags fornecido pelo backend. |
| `IA_MCP_KEYWORDS_PATH` | `src/ia_mcp/vocabulary/keywords.json` | Sinônimos do fallback heurístico. |
| `IA_MCP_API_HOST` | `0.0.0.0` | Host do Uvicorn no entrypoint `python -m ia_mcp.main`. |
| `IA_MCP_API_PORT` | `8100` | Porta do serviço. |
| `IA_MCP_MCP_PATH` | `/mcp` | Caminho de montagem do FastMCP. |
| `IA_MCP_MAX_TAGS` | `8` | Máximo de tags retornadas por classificação. |
| `IA_MCP_MIN_TAG_CONFIDENCE` | `0.35` | Confiança mínima do heurístico para aceitar uma tag. |
| `IA_MCP_MAX_TEXT_CHARS` | `4000` | Limite de texto processado (texto maior é truncado). |
| `IA_MCP_MAX_SUMMARY_CHARS` | `600` | Limite do resumo retornado. |
| `IA_MCP_LOG_LEVEL` | `INFO` | Nível de log. |
| `IA_MCP_LOG_TEXT` | `false` | Quando `true`, registra o texto recebido em nível `DEBUG`. |

### Modos do provedor

- `auto`: usa o modelo OpenAI-compatible se `IA_MCP_AI_BASE_URL` e
  `IA_MCP_AI_MODEL` estiverem configurados; caso contrário, usa apenas o
  heurístico. Em falha técnica do modelo, cai no heurístico.
- `openai_compatible`: exige URL e modelo; ainda usa o heurístico como fallback.
- `heuristic`: funciona offline, sem rede e sem credenciais.

### Qual provedor gratuito usar

O serviço fala o protocolo **OpenAI-compatible**; qualquer provedor que o
implemente funciona sem mudar código. Para a demo do hackathon:

| Provedor | Free tier | Quando usar |
|---|---|---|
| **Groq** (`https://api.groq.com/openai/v1`) | ~30 req/min e ~1k req/dia, sem cartão | **Recomendado para a demo**: baixa latência e JSON confiável |
| **Google AI Studio / Gemini Flash** | cota diária gratuita | Alternativa com bom entendimento de português |
| **Ollama local** (`http://localhost:11434/v1`) | ilimitado no próprio laptop | Demo sem internet ou com dados sensíveis |

Configuração típica com Groq:

```bash
IA_MCP_AI_PROVIDER=openai_compatible
IA_MCP_AI_BASE_URL=https://api.groq.com/openai/v1
IA_MCP_AI_MODEL=openai/gpt-oss-120b
IA_MCP_AI_API_KEY=<chave>
```

Por que não alucina:

- `temperature=0` e resposta pedida em JSON (extraída e validada no código);
- o prompt recebe o **vocabulário fechado** e a instrução de responder somente
  com tags dele;
- tags fora do vocabulário são descartadas no código;
- o modelo **não calcula** nada: quantidades, pontuação e matching são do
  backend;
- qualquer falha técnica cai no heurístico determinístico, sem inventar dados.


## 6. Contratos HTTP

### 6.1 `POST /ia/classificar`

Request:

```json
{ "texto": "Tenho uma loja de roupas e perco vendas por não responder no WhatsApp." }
```

Response `200`:

```json
{ "tags": ["atendimento", "whatsapp", "vendas_online"] }
```

Regras:

- a resposta de sucesso contém **somente** `tags`;
- todas as tags pertencem ao vocabulário carregado;
- tags desconhecidas retornadas pelo modelo são descartadas;
- sem nenhuma tag válida, retorna `{"tags": []}` com `200`;
- texto vazio ou ausente retorna `422`.

### 6.2 `POST /ia/resumir`

Request:

```json
{ "texto": "Texto livre da demanda." }
```

Response `200`:

```json
{ "resumo": "Resumo objetivo da demanda." }
```

O resumo é limitado por `IA_MCP_MAX_SUMMARY_CHARS`. Se o modelo falhar, o
resumo extrativo local é usado.

### 6.3 `POST /ia/insights`

Request:

```json
{
  "grupos": [
    {
      "chave": "atendimento",
      "titulo": "Atendimento fora do horário",
      "quantidade": 7,
      "exemplos": ["Não consigo responder à noite."]
    }
  ]
}
```

Response `200`:

```json
{
  "interpretacoes": {
    "atendimento": "Interpretação textual do grupo."
  }
}
```

Regras:

- cada chave de `interpretacoes` é a `chave` de um grupo recebido;
- os valores são strings;
- não há contagens, pesos, scores de matching nem status na resposta
  (`quantidade` é apenas contexto de entrada, nunca recalculado);
- `{"grupos": []}` retorna `{"interpretacoes": {}}`;
- campos extras nos grupos são ignorados, para tolerar evoluções do backend.

### 6.4 Falhas

| Situação | HTTP |
|---|---|
| Corpo inválido (texto vazio, campo ausente, `chave` vazia) | `422` |
| Modelo falha e heurístico responde | `200` com o resultado local |
| Modelo e heurístico falham tecnicamente | `503` |
| Erro inesperado | `500` |

Corpo do `503`:

```json
{ "detail": "Serviço de IA indisponível" }
```

O `IAGateway` pode usar esse `503` para acionar o fallback já existente no
backend.

## 7. Vocabulário de tags

O contrato HTTP de classificação recebe apenas `texto`, portanto o vocabulário
é carregado de um **arquivo JSON fornecido pelo backend**. O arquivo
`src/ia_mcp/vocabulary/tags.json` já contém as 11 tags oficiais de
`back-end/config/vocabulario.json`; a sincronia entre as duas cópias é validada
por `tests/integration/test_backend_contract.py`.

Formato mínimo:

```json
{ "tags": ["atendimento", "whatsapp", "vendas_online"] }
```

Formato enriquecido (recomendado):

```json
{
  "tags": [
    {
      "tag": "atendimento",
      "label": "Atendimento",
      "keywords": ["atendimento", "responder", "demora"]
    }
  ]
}
```

Também é aceita uma lista simples na raiz do arquivo.

Regras:

- o vocabulário é validado no startup; arquivo ausente, vazio ou inválido
  impede a inicialização com erro claro;
- tags duplicadas são rejeitadas;
- `keywords.json` é local e contém apenas sinônimos para o fallback heurístico;
- sinônimos de tags que não existem no vocabulário são ignorados com aviso;
- qualquer alteração no vocabulário oficial deve ser replicada em
  `src/ia_mcp/vocabulary/tags.json` (o teste de contrato acusa divergência).

## 8. Ferramentas MCP

Servidor: `http://localhost:8100/mcp/` (Streamable HTTP, mesmo processo da API).

| Ferramenta | Fonte | Parâmetros |
|---|---|---|
| `listar_radar` | `GET {backend}/api/mcp/radar` | nenhum |
| `buscar_startups` | `GET {backend}/api/mcp/startups` | `tag`, `segmento` (opcionais) |

Ambas são somente leitura (`readOnlyHint: true`), não escrevem dados e não
aplicam matching.

O backend exige o header `X-Perfil` em todas as rotas `/api/*`. O cliente envia
`X-Perfil: mcp` por padrão (`IA_MCP_BACKEND_PERFIL`) e, se configurado,
`X-Ator-Id` (`IA_MCP_BACKEND_ATOR_ID`).

### Pass-through

O módulo **não presume o schema** das respostas do backend. O JSON recebido é
devolvido sem remapeamento, tanto para listas quanto para envelopes. Os
contratos atuais estão em `back-end/app/services/consultas.py`:

Em erro de backend (HTTP ≥ 400, timeout, rede ou JSON inválido), a ferramenta
retorna erro MCP controlado, sem derrubar o servidor.

### Configuração de cliente MCP

Exemplo genérico:

```json
{
  "mcpServers": {
    "facesp-ia-mcp": {
      "url": "http://localhost:8100/mcp/"
    }
  }
}
```

O nome exato do campo varia conforme o cliente (Claude Desktop, IDEs, SDKs).
O transporte é Streamable HTTP, não `stdio`.

## 9. Fallback e limites

1. O modelo OpenAI-compatible é tentado primeiro (quando configurado).
2. Timeout, erro HTTP, envelope inválido, JSON inválido ou ausência de tags
   válidas acionam o heurístico local.
3. O heurístico faz correspondência lexical normalizada (sem acentos e sem
   diferença de caixa) e respeita `IA_MCP_MIN_TAG_CONFIDENCE`.
4. Se ambos falharem tecnicamente, a API responde `503`.
5. Nenhum texto livre é logado por padrão (`IA_MCP_LOG_TEXT=false`).

## 10. Testes

```bash
cd ia-mcp
uv run pytest
```

Cobertura atual:

- contratos exatos dos três endpoints, incluindo ausência de campos extras;
- validação de payloads inválidos (`422`);
- falha total (`503`);
- vocabulário simples e enriquecido, validação e normalização;
- classificação com tags fora do vocabulário descartadas;
- fluxo completo `LLM → heurístico` via `POST /ia/classificar`, incluindo
  HTTP 500, timeout, JSON inválido e resposta só com tags inválidas;
- provedor OpenAI-compatible com `httpx.MockTransport`, sem rede;
- fallback em HTTP 500, timeout e JSON inválido;
- resumo via modelo e extrativo;
- insights por chave de grupo, sem contagens;
- cadeia de provedores e `ServiceUnavailableError`;
- ferramentas MCP, pass-through e parâmetros de consulta;
- cliente do backend e tratamento de indisponibilidade;
- processo único: rotas `/ia/*` e MCP em `/mcp/`.

Nenhum teste depende da API real nem do banco do backend operacional.

## 11. Checklist de integração

- [ ] Substituir o `tags.json` provisório pelo arquivo oficial do backend.
- [ ] Fornecer exemplos reais ou OpenAPI de `/api/mcp/radar` e
      `/api/mcp/startups` para validação de compatibilidade.
- [ ] Confirmar com o responsável pelo backend a URL e o timeout de produção.
- [ ] Configurar `IA_MCP_AI_BASE_URL`, `IA_MCP_AI_MODEL` e `IA_MCP_AI_API_KEY`
      no ambiente do serviço.
- [ ] Apontar o `IAGateway` para `http://<host>:8100/ia/*`.
- [ ] Configurar o cliente MCP para `http://<host>:8100/mcp/`.
- [ ] Validar o `503` como gatilho de fallback no `IAGateway`.
- [ ] Revisar se todas as tags retornadas pertencem ao vocabulário oficial.

## 12. Estrutura do pacote

```text
ia-mcp/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── docs/ia-mcp.md
├── src/ia_mcp/
│   ├── main.py
│   ├── config.py
│   ├── errors.py
│   ├── text.py
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── backend/client.py
│   ├── domain/models.py
│   ├── mcp/server.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── chain.py
│   │   ├── heuristic.py
│   │   ├── openai_compatible.py
│   │   └── prompts.py
│   ├── services/
│   │   ├── classification.py
│   │   ├── facade.py
│   │   ├── insights.py
│   │   └── summarization.py
│   └── vocabulary/
│       ├── keywords.json
│       ├── loader.py
│       └── tags.json
└── tests/
    ├── api/
    ├── backend/
    ├── integration/
    ├── mcp/
    ├── providers/
    ├── services/
    └── vocabulary/
```
