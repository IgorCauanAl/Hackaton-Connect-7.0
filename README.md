# FACESP Match — InovaVarejo

MVP do desafio Connect 7.0: conecta demandas do varejo a soluções tecnológicas.
O repositório reúne três serviços Python e um frontend React:

| Componente | Pasta | Porta | Papel |
| --- | --- | --- | --- |
| Frontend React | `orquestrador/frontend` | servido pelo orquestrador (`8200`) | telas do lojista, da startup e da associação |
| Orquestrador (BFF) | `orquestrador` | `8200` | compõe os fluxos, valida contratos, centraliza erros e serve o frontend |
| IA/MCP | `ia-mcp` | `8100` | classificação/resumo/insights por IA + ferramentas MCP somente leitura |
| Backend operacional | `back-end` | `8000` | fonte da verdade: matching, persistência, autorização e CRUDs |

O frontend **nunca** chama o backend diretamente: leituras passam pelo
pass-through `GET /api/*` e os fluxos compostos/escritas por `/orquestracao/*`
no orquestrador.

## Execução integrada

Pré-requisitos: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 20+ e
`npm`.

```bash
cp .env.example .env      # ajuste portas/URLs se necessário
./scripts/dev.sh          # sobe backend, IA/MCP e orquestrador + frontend
```

O script:

- carrega o `.env` da raiz;
- recusa iniciar se `8000`, `8100` ou `8200` já estiverem em uso (não mata
  processos de outras pessoas);
- instala dependências e gera o build do frontend quando necessário;
- espera os health checks e então libera o terminal;
- ao receber `Ctrl+C`, encerra **apenas** os processos que ele iniciou.

Depois acesse:

- Aplicação: <http://localhost:8200/>
- Orquestrador: <http://localhost:8200/health>
- IA/MCP: <http://localhost:8100/ia/*> e MCP em `http://localhost:8100/mcp/`
- Backend: <http://localhost:8000/api/saude>

Para forçar a reconstrução do frontend: `InovaVarejo_FORCE_BUILD=1 ./scripts/dev.sh`.

### Frontend

O frontend está em `orquestrador/frontend` (React 19 + Vite, multi-página).
Cada tela mantém seu HTML/CSS, preservando as URLs originais
(`/chat.html`, `/resultados.html`, ...). O build em `dist/` é servido pelo
orquestrador na mesma origem, então não há CORS no caminho normal.

```bash
cd orquestrador/frontend
npm install
npm run build
npm run dev          # desenvolvimento em http://localhost:5173 (proxy para :8200)
```

Os arquivos estáticos originais foram preservados em
`orquestrador/frontend/legacy-static/` apenas como referência.

## Configuração da IA

Toda a configuração vem de variáveis de ambiente. Os nomes canônicos são
`AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` e `AI_TIMEOUT`
(os nomes prefixados `IA_MCP_AI_*` também são aceitos e têm precedência).

- **Sem chave** (`AI_API_KEY` vazio): o serviço usa o classificador heurístico
  local; o sistema funciona offline.
- **Com chave**: `AI_PROVIDER=openai_compatible` (ou `auto`) usa o provedor
  OpenAI-compatible configurado em `AI_BASE_URL`/`AI_MODEL`. Falhas de
  autenticação, timeout ou indisponibilidade caem automaticamente no
  heurístico/fallback do backend, sem bloquear o fluxo.

Exemplo com Groq:

```bash
AI_PROVIDER=auto
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=openai/gpt-oss-120b
AI_API_KEY=<sua-chave>
AI_TIMEOUT=20
```

A chave fica apenas no ambiente do serviço IA/MCP. Ela não é enviada ao
frontend, não aparece nas respostas HTTP e não é logada.

## Testes

Por serviço:

```bash
cd back-end      && python3 -m unittest discover -s tests -v
cd ia-mcp        && uv run pytest
cd orquestrador  && uv run pytest
```

Verificação de integração real (com os serviços no ar):

```bash
cd orquestrador
uv run python ../scripts/integration_check.py
```

O script exercita 10 cenários ponta a ponta, incluindo fallback com IA fora do
ar e as ferramentas MCP via cliente FastMCP real. Ele grava demandas, teste e
relatório de demonstração no banco local (`back-end/facesp_demo.db`). Para
testar indisponibilidade, sobe instâncias temporárias isoladas nas portas
`8199`, `8098` e `8298` (usando uma cópia do banco em `/tmp/opencode`), sem
tocar nos serviços em execução.

## Backend operacional

Python + FastAPI + SQLite. A IA e o MCP são módulos independentes: aqui existe
a **porta** (`IAGateway`) e os fallbacks determinísticos.

### Rodar isoladamente

```bash
pip install -r requirements.txt
python -m app.seed                 # apaga e recria o banco da demo
uvicorn app.main:app --reload      # também faz o seed sozinho se o banco estiver vazio
python -m unittest discover -s tests -v
```

Variáveis (`.env.example`): `FACESP_DB_PATH`, `FACESP_IA_URL` (vazio = IA
indisponível, usa fallbacks), `FACESP_IA_TIMEOUT`.

### Camadas (dependências só apontam para dentro)

```
api/        FastAPI: rotas finas, schemas Pydantic, deps (ator por header)
services/   casos de uso + regras + autorização por perfil
domain/     matching (Strategy por critério, puro/determinístico) e roteiro do chat
infra/      repositories (único lugar com SQL), database, ia_gateway (porta + adaptadores)
container.py  composition root (DI manual)     core/  config, erros, segurança
config/     matching.json (pesos, corte 50, frases de motivo) e vocabulario.json (tags)
```

Padrões: Repository, Strategy (critérios), Ports & Adapters + Null Object (IA),
Composition Root, exceções de domínio → HTTP.

### Acesso (demo)

Headers: `X-Perfil: lojista|startup|admin|mcp` e `X-Ator-Id: <id do lojista/startup>`.

### Endpoints

| Quem | Método e rota |
|---|---|
| Lojista | `GET /api/chat/roteiro` · `GET /api/lojistas` · `GET /api/lojistas/{id}` · `POST /api/demandas` · `GET /api/demandas/{id}/matching` · `POST /api/testes` · `POST /api/testes/{id}/feedback-demo` · `GET /api/feedbacks` |
| Startup | `GET /api/startups[/{id}]` · `GET /api/startups/{id}/dashboard` · `GET /api/startups/{id}/oportunidades` · `GET /api/relatorios/{id}?versao=anonimizada\|completa` |
| Associação | `GET /api/admin/dashboard` · `GET /api/admin/demandas?status=` · `GET /api/admin/demandas/{id}` · `POST .../validar` · `POST .../encaminhar {startup_id}` · `POST /api/admin/insights/gerar` · `GET /api/admin/radar` · `GET /api/admin/radar/{grupo_id}/demandas` · `GET /api/admin/feedbacks` |
| MCP (só leitura) | `GET /api/mcp/radar` · `GET /api/mcp/startups?tag=&segmento=` (ou importe `LeituraMcpService`) |

### Regras principais

- **Matching** (`domain/matching.py`): 8 critérios com pesos em
  `config/matching.json` (soma 100), índice 0–100, corte 50, até 3 resultados,
  desempate por nome. A IA só fornece as tags; o cálculo é do backend.
- **Fallbacks**: IA falhou → tags vêm das respostas dos botões; resumo = texto
  truncado; insights → versão de referência pré-gerada (`origem: "referencia"`).
- **Insights**: só demandas `validada`/`encaminhada` entram. Quantidades e
  pontuação são calculadas pelo código; a IA só interpreta.
- **Sem match**: demanda vai para a fila (`sem_match=true`) e entra nos insights
  quando validada.
- **Teste**: exige `autorizacao=true` e startup entre as recomendadas; 15 dias;
  `solicitado → concluido`.
- **Relatório (6 blocos)**: anonimizado (ramo, tipo, porte, região, tags,
  resumo) ou completo (só com consentimento do lojista).

### Contrato que a IA precisa atender (HTTP em `FACESP_IA_URL`)

```
POST /ia/classificar {"texto"}  -> {"tags": [..]}      (tags fora de config/vocabulario.json são descartadas)
POST /ia/resumir     {"texto"}  -> {"resumo": ".."}
POST /ia/insights    {"grupos": [{"chave","titulo","quantidade","exemplos"}]} -> {"interpretacoes": {chave: ".."}}
```
