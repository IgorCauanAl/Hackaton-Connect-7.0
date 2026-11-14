# Orquestrador — detalhamento técnico

Documento de apoio ao [README](../README.md). Descreve o contrato interno, a
ordem das chamadas, as decisões de projeto e os cenários cobertos pelos testes.

## 1. Papel do módulo

O Orquestrador (Módulo 03) é um **BFF** (Backend For Frontend). Ele existe para
que o frontend não precise conhecer três serviços, dois vocabulários e quatro
formatos de erro diferentes.

Responsabilidades:

- compor chamadas entre backend operacional e IA/MCP;
- validar payloads de entrada antes de gastar chamadas externas;
- validar contratos de resposta antes de devolver ao frontend;
- centralizar o formato de erro e o `trace_id`;
- garantir idempotência de `POST`;
- registrar a trilha (`etapas`/`avisos`) do que aconteceu.

Não-responsabilidades (explícitas):

- não calcula matching, pesos, índices ou quantidades;
- não persiste nada;
- não autentica (propaga identidade; o backend decide);
- não duplica CRUDs, rotas do backend ou ferramentas MCP;
- não chama a IA para gerar números — a IA só interpreta texto.

## 2. Ordem das chamadas

### 2.1 Registrar demanda (ORQ-RF-01)

```
POST /orquestracao/demandas
  │
  ├─[1] valida payload (Pydantic)            → 422 sem chamadas externas
  ├─[2] POST {IA}/ia/classificar             → tags ou aviso
  ├─[3] POST {BACKEND}/api/demandas          → registro + matching + persistência
  └─[4] valida contrato da resposta          → 502 contrato_invalido
```

Detalhes:

- A classificação acontece **antes** do registro para que o backend receba
  `tags` e não chame a IA uma segunda vez.
- Se a IA falhar (timeout, `5xx`, JSON inválido, `tags` ausente/vazia), o campo
  `tags` é **omitido** do corpo. O backend então aplica o fallback por botões e
  marca `tags_origem = "botoes"`.
- Uma falha de IA nunca derruba o fluxo: no máximo gera o aviso
  `ia_indisponivel` ou `classificacao_vazia`.
- O backend executa registro, classificação, matching e persistência em uma
  transação; o orquestrador não repete nada disso.

### 2.2 Consultar matching (ORQ-RF-02)

```
GET /orquestracao/demandas/{id}/matching
  └─ GET {BACKEND}/api/demandas/{id}/matching
```

Valida que `ranking_startups` é lista e `sem_match` é booleano. Se
`sem_match=true` vier acompanhado de ranking, registra o aviso
`matching_inconsistente` (o dado do backend é preservado, sem correção local).

### 2.3 Insights, Radar e padrões (ORQ-RF-03)

```
POST /orquestracao/insights        →  POST {BACKEND}/api/admin/insights/gerar
GET  /orquestracao/radar           →  GET  {BACKEND}/api/admin/radar
GET  /orquestracao/padroes         →  Radar + tag do grupo (leitura das demandas)
GET  /orquestracao/mcp/radar       →  ferramenta MCP listar_radar
GET  /orquestracao/mcp/startups    →  ferramenta MCP buscar_startups?tag=
```

- Exclusivo de `admin` (associação); as ferramentas MCP aceitam `admin`/`mcp`.
  A checagem é antecipada no orquestrador; o backend revalida.
- O envio de grupos para a IA é feito **pelo backend**, que tem acesso às
  quantidades. O orquestrador nunca envia números para a IA.
- Cada item do Radar precisa conter exatamente os campos:
  `grupo_id, titulo, quantidade, pontuacao, sugestao, origem, destaque,
  requer_validacao_humana`.
- `quantidade` precisa ser inteira e `sugestao` texto não vazio.
- Se algum item tiver `origem = "referencia"`, o orquestrador adiciona o aviso
  `fallback_referencia`: a IA não respondeu e o backend usou a interpretação
  determinística.
- O endpoint `padroes` acrescenta `tag` ao radar lendo as demandas reais do
  grupo (o backend ainda não expõe a tag nesse payload). Nenhuma quantidade,
  pontuação ou regra de matching é recalculada.
- As rotas MCP chamam o FastMCP do IA/MCP via Streamable HTTP e validam o
  contrato antes de devolver; falha de transporte vira `503 mcp_indisponivel`.

### 2.4 Teste demonstrativo (ORQ-RF-04)

```
POST /orquestracao/testes
  ├─ valida perfil lojista e autorização expressa  → 403/409 sem chamadas
  ├─ POST {BACKEND}/api/testes                     → teste_id/teste_status
  ├─ GET  {BACKEND}/api/testes/{teste_id}          → confirma status
  └─ devolve {resultado: registro, teste: detalhe}
```

- `autorizacao=false` é bloqueado com `409 regra_de_negocio`, etapa
  `autorizacao`.
- Se o status consultado divergir do status retornado no registro, gera o aviso
  `status_divergente` (não falha: o ciclo é assíncrono no backend).
- `POST /orquestracao/testes/{id}/feedback` valida que o `teste_id` devolvido é
  o mesmo solicitado.

### 2.5 Oportunidades e relatórios (ORQ-RF-05)

```
POST /orquestracao/demandas/{id}/encaminhar
  ├─ valida perfil admin                           → 403 sem chamadas
  ├─ POST {BACKEND}/api/admin/demandas/{id}/encaminhar
  ├─ GET  {BACKEND}/api/startups/{sid}/oportunidades
  ├─ GET  {BACKEND}/api/relatorios/{rid}?versao=anonimizada
  └─ confere relatorio.demanda_id e relatorio.startup_id
```

- O relatório é gerado e persistido pelo backend; o orquestrador apenas lê.
- Se o relatório não aparecer na lista de oportunidades da startup, gera o
  aviso `relatorio_nao_listado` (não falha).
- Se os vínculos `demanda_id`/`startup_id` não baterem, retorna
  `502 contrato_invalido` — proteção contra vazamento entre lojistas.
- `GET /orquestracao/relatorios/{id}` aceita `versao=anonimizada|completa`
  (padrão `anonimizada`) e rejeita qualquer outro valor com `422`.

## 3. Contrato de resposta

Sucesso:

```json
{
  "resultado": { "...": "payload do serviço de origem" },
  "orquestracao": {
    "etapas": [
      {"etapa": "classificacao_ia", "status": "ok", "duracao_ms": 41},
      {"etapa": "registro_demanda", "status": "ok", "duracao_ms": 12}
    ],
    "avisos": [
      {"codigo": "sem_match", "detalhe": "Nenhuma solução compatível..."}
    ]
  }
}
```

- `resultado` é **pass-through**: o orquestrador não renomeia campos.
- `etapas` preserva a ordem e registra `falha` + `detalhe` quando a etapa
  lança erro.
- `avisos` são não fatais e possuem `codigo` estável para o frontend.

## 4. Idempotência

Implementada em `idempotency.py`:

- fingerprint = SHA-256 de `(método, rota, X-Perfil, X-Ator-Id, corpo)`;
- cache em memória com TTL configurável;
- replay devolve o corpo e o status originais com
  `X-Idempotente-Replay: true`;
- mesma chave com fingerprint diferente → `409 idempotency_conflict`;
- sem chave, o comportamento é o normal (sem deduplicação).

Rotas idempotentes: `POST /demandas`, `POST /insights`, `POST /testes`,
`POST /testes/{id}/feedback`, `POST /demandas/{id}/encaminhar`.

## 5. Erros e mapeamento

`errors.py` centraliza a tradução:

| Exceção | HTTP | `codigo` |
| --- | --- | --- |
| `AcessoNegado` | 403 | `acesso_negado` |
| `ErroDeValidacao` | 409 | `regra_de_negocio` |
| `RequisicaoInvalida` | 422 | `requisicao_invalida` |
| `ServicoIndisponivel` | 503 | `backend_timeout` |
| `FalhaNoBackend` | 502 | `backend_indisponivel` |
| `RespostaInvalida` | 502 | `contrato_invalido` |

O `BackendClient` traduz 4xx preservando o status (`401/403/404/409/422`) e o
`detail` do backend. `IOError`/timeout viram `503`. Respostas `5xx` viram `502`.

Sobre a IA/MCP:

- o orquestrador trata **qualquer** falha como não fatal (`IAIndisponivel`);
- o `503 {"detail": "Serviço de IA indisponível"}` do IA/MCP ativa o fallback do
  backend, nunca vira `503` para o frontend em `/demandas`;
- para `insights`, o backend também tem fallback determinístico.

## 6. Observabilidade

- `X-Trace-Id` é gerado por requisição (nunca herdado do cliente) e devolvido no
  header e no corpo de erro;
- cada requisição gera uma linha de log com método, rota, status, duração e
  trace;
- erros controlados são logados em `WARNING` com etapa/código; inesperados em
  `ERROR` com stack trace;
- nenhum payload sensível (texto livre, relatório) é logado.

## 7. Decisões de projeto

| Decisão | Motivo |
| --- | --- |
| BFF separado, não middleware no backend | Evita acoplar o domínio ao frontend e mantém o backend como fonte da verdade |
| Classificar via IA antes de registrar | Elimina chamada duplicada de IA e mantém `tags_origem="ia"` |
| Envelope aditivo `{resultado, orquestracao}` | O frontend recebe dados + diagnóstico sem alterar os contratos originais |
| Validação de contrato nas respostas | Falha cedo com `502 contrato_invalido` em vez de propagar dado quebrado |
| Idempotência em memória | Suficiente para demo em processo único; interface pronta para Redis |
| Timeouts separados (backend 10s, IA 25s) | LLM é mais lento que o backend; o timeout maior evita fallback prematuro |
| Sem autenticação própria | Evita duplicar a autorização já implementada no backend |

## 8. Testes

`uv run pytest` — 65 testes, todos com `httpx.MockTransport` (sem rede):

| Arquivo | Cobre |
| --- | --- |
| `test_rf01_demandas.py` | classificação → registro, fallback de IA, sem_match, 5xx, contrato, matching |
| `test_rf03_insights.py` | insights/radar, 403, fallback de referência, contrato do Radar |
| `test_rf04_testes.py` | autorização, registro + confirmação, feedback, divergências |
| `test_rf05_relatorios.py` | encaminhamento, vínculos, versões, 403 |
| `test_transversais.py` | health, trace, headers, 422, 404, idempotência, timeouts, 4xx/JSON inválido |

Para regressão completa do repositório:

```bash
cd orquestrador && uv run pytest
cd ia-mcp     && uv run pytest
cd back-end   && python3 -m unittest discover -s tests -v
```

## 9. Limitações conhecidas

- Store de idempotência em memória: reinício do processo limpa as chaves.
- Não há cache de respostas de matching/Radar (cada leitura vai ao backend).
- O orquestrador não faz retry automático; falhas são explícitas para o
  frontend, que pode repetir com a mesma `Idempotency-Key`.
- A `versao=completa` do relatório depende da autorização do backend: o
  orquestrador apenas repassa a identidade.
