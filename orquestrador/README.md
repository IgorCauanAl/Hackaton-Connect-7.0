# Orquestrador — FACESP Match (Módulo 03)

BFF que coordena os fluxos entre o **frontend**, o **backend operacional** e o
**serviço IA/MCP**. Ele não recalcula matching, não persiste dados, não
autentica e não duplica CRUDs: apenas **compõe**, **valida contratos**,
**centraliza erros**, aplica **idempotência** e devolve a **trilha de execução**.

```
React  →  Orquestrador (:8200)  →  Backend operacional (:8000)
                                 →  IA/MCP (:8100)
```

## Requisitos atendidos

| Requisito | Descrição | Onde |
| --- | --- | --- |
| ORQ-RF-01 | Registro de demanda com classificação via IA | `services/demandas.py` |
| ORQ-RF-02 | Consulta do matching calculado pelo backend | `services/demandas.py` |
| ORQ-RF-03 | Geração/consulta de insights e Radar (admin) | `services/insights.py` |
| ORQ-RF-04 | Ciclo de teste demonstrativo com autorização | `services/testes.py` |
| ORQ-RF-05 | Encaminhamento de oportunidade e relatórios | `services/relatorios.py` |
| ORQ-RF-06 | Idempotência, erros centralizados e trace | `idempotency.py`, `main.py` |
| ORQ-RF-07 | Validação de pré-condições de negócio | serviços + `errors.py` |

## Como rodar

Requer Python 3.12+ e [uv](https://docs.astral.sh/uv/).

```bash
cd orquestrador
cp .env.example .env          # ajuste as URLs se necessário
uv sync
uv run uvicorn orquestrador.main:app --host 0.0.0.0 --port 8200
```

Verificação:

```bash
uv run pytest
curl http://localhost:8200/health
```

Documentação interativa: <http://localhost:8200/docs>.

## Configuração

Somente variáveis de ambiente (prefixo `ORQ_`), com `.env` opcional:

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `ORQ_BACKEND_BASE_URL` | `http://localhost:8000` | Backend operacional |
| `ORQ_BACKEND_TIMEOUT_SECONDS` | `10` | Timeout do backend |
| `ORQ_IA_BASE_URL` | `http://localhost:8100` | Serviço IA/MCP |
| `ORQ_IA_TIMEOUT_SECONDS` | `25` | Timeout da IA (deve cobrir o modelo) |
| `ORQ_API_HOST` | `0.0.0.0` | Host HTTP |
| `ORQ_API_PORT` | `8200` | Porta HTTP |
| `ORQ_IDEMPOTENCY_TTL_SECONDS` | `600` | Retenção das chaves idempotentes |
| `ORQ_LOG_LEVEL` | `INFO` | Nível de log |

Nenhuma URL, credencial ou caminho é fixado no código.

## Identidade do ator

O orquestrador **não autentica**. Ele exige e propaga:

- `X-Perfil`: `lojista` | `startup` | `admin` | `mcp`
- `X-Ator-Id` (opcional): id do lojista/startup

O backend operacional continua sendo a autoridade final; cabe ao orquestrador
apenas antecipar as pré-condições que ele mesmo conhece (ex.: insights e
encaminhamento são exclusivos de `admin`).

## Rotas

Todas as rotas exigem `X-Perfil`. Sucesso devolve
`{"resultado": ..., "orquestracao": {"etapas": [...], "avisos": [...]}}`.

| Método | Rota | Perfil | Ação |
| --- | --- | --- | --- |
| `POST` | `/orquestracao/demandas` | lojista | Classifica via IA e registra a demanda |
| `GET` | `/orquestracao/demandas/{id}/matching` | lojista/admin | Consulta o ranking já calculado |
| `POST` | `/orquestracao/insights` | admin | Gera insights via IA (fallback no backend) |
| `GET` | `/orquestracao/radar` | admin | Consulta o Radar |
| `POST` | `/orquestracao/testes` | lojista | Solicita teste e confirma o status |
| `GET` | `/orquestracao/testes/{id}` | lojista/admin | Consulta o teste |
| `POST` | `/orquestracao/testes/{id}/feedback` | lojista/admin | Solicita o feedback demonstrativo |
| `POST` | `/orquestracao/demandas/{id}/encaminhar` | admin | Encaminha oportunidade e confirma o relatório |
| `GET` | `/orquestracao/startups/{id}/relatorios` | startup/admin | Lista oportunidades da startup |
| `GET` | `/orquestracao/relatorios/{id}` | startup/admin | Lê o relatório (`versao=anonimizada\|completa`) |
| `GET` | `/health` | público | Health check |

Exemplo:

```bash
curl -X POST http://localhost:8200/orquestracao/demandas \
  -H 'Content-Type: application/json' \
  -H 'X-Perfil: lojista' -H 'X-Ator-Id: 1' \
  -d '{
    "lojista_id": 1,
    "respostas": {
      "objetivo": "vender_mais",
      "dificuldade": "atender_whatsapp",
      "canais": ["whatsapp"],
      "ferramentas": ["planilha"],
      "orcamento": "100_300",
      "urgencia": "ate_15_dias"
    },
    "texto_livre": "Perco vendas porque não consigo responder no WhatsApp."
  }'
```

## Fluxo de demandas (ORQ-RF-01/02)

1. Valida o payload no orquestrador (`422` sem chamar ninguém).
2. Chama `POST /ia/classificar` com o texto livre.
3. Se a IA falhar ou devolver lista vazia, segue **sem** `tags` e o backend
   aplica o fallback por botões (aviso `ia_indisponivel`/`classificacao_vazia`).
4. Chama `POST /api/demandas` **uma única vez**; o backend registra,
   calcula o matching e persiste.
5. Valida o contrato da resposta (`demanda_id`, `status`, `ranking_startups`).
6. `status == "sem_match"` gera o aviso `sem_match`, sem tratar como erro.

## Idempotência (ORQ-RF-06)

Envie `Idempotency-Key` em qualquer `POST`. A chave é combinada com método,
rota, ator e corpo:

- repetição idêntica → replay da resposta original + `X-Idempotente-Replay: true`;
- mesma chave com corpo diferente → `409 idempotency_conflict`.

O store é em memória com TTL (`ORQ_IDEMPOTENCY_TTL_SECONDS`); a interface
`IdempotencyStore` permite trocar por Redis sem tocar nas rotas.

## Erros

Formato único:

```json
{
  "detail": "motivo legível",
  "codigo": "regra_de_negocio",
  "etapa": "autorizacao",
  "trace_id": "9f1c2a7b3d4e"
}
```

| HTTP | `codigo` | Quando |
| --- | --- | --- |
| 401 | `ator_invalido` | `X-Perfil` inválido/ausente no serviço |
| 403 | `acesso_negado` | Pré-condição de perfil |
| 404 | `nao_encontrado` | Recurso ausente no backend |
| 409 | `regra_de_negocio`, `idempotency_conflict` | Regra de negócio |
| 422 | `requisicao_invalida` | Payload inválido |
| 502 | `backend_indisponivel`, `contrato_invalido` | Backend 5xx ou resposta fora do contrato |
| 503 | `backend_timeout`, `servico_indisponivel` | Timeout/rede |

Todo erro devolve `X-Trace-Id`, também presente no corpo. O `503` de IA **não
propaga**: o backend possui fallback determinístico e o orquestrador apenas
registra o aviso.

## Estrutura

```
src/orquestrador/
├── api/            # rotas, schemas de entrada e dependências
├── clients/        # HTTP do backend e do IA/MCP
├── services/       # um serviço por requisito funcional
├── config.py       # Settings (ORQ_*)
├── container.py    # composition root
├── domain.py       # Ator
├── errors.py       # erros → HTTP
├── idempotency.py  # Idempotency-Key
├── main.py         # FastAPI, handlers, trace
└── trilha.py       # etapas/avisos
```

Detalhamento em [`docs/orquestrador.md`](docs/orquestrador.md).
