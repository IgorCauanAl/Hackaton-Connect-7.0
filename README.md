# InovaVarejo

**InovaVarejo** é um sistema demo que tem como objetivo conectar pequenos varejistas a soluções de startups compatíveis com suas necessidades reais, usando um diagnóstico guiado, classificação por IA via protocolo MCP, matching determinístico e um ciclo de teste/feedback. Quando não há solução adequada o problema é armazenado no sistema, a demanda é transformada em oportunidade sendo enviada para CONNECT para futuros hackatons e podendo ser visualizada por outras startups.

Desenvolvido para o desafio **FACESP — Federação das Associações Comerciais do Estado de São Paulo**, no Connect 7.0: *“FACESP: Conectar as demandas do varejo às soluções tecnológicas

Como lojistas e associações comerciais podem usar tecnologia para encontrar e testar soluções de startups que atendam às suas necessidades e, quando não houver uma solução adequada, transformar essas necessidades em oportunidades de desenvolvimento conjunto?”*.

## 1. Problema que resolvemos

Pequenos varejistas de lojas físicas, digitais e híbridas têm dificuldade para descobrir, comparar e testar tecnologias que resolvam suas dores reais (atendimento fora do horário, vendas online, estoque, fidelização, etc.). As associações comerciais, por sua vez, não têm um mecanismo sistemático para qualificar essas demandas e conectá-las a startups — nem para transformar demandas sem resposta em oportunidades de desenvolvimento conjunto.

O InovaVarejo cria essa ponte: o lojista descreve sua necessidade, a plataforma identifica soluções compatíveis com justificativa por critério, permite testar por 15 dias e, quando não há match, encaminha a demanda qualificada à associação e às startups.

## 2. Arquitetura — Monólito modular

O backend operacional é um monólito modular: um único processo/deploy, mas organizado em módulos com fronteiras claras (Repository, Strategy, Ports & Adapters, Composition Root). Serviços auxiliares (IA/MCP e orquestrador) são processos independentes que se comunicam por HTTP, sem acesso direto ao banco.

### Diagrama da arquitetura

```text
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Frontend    │────▶│  Orquestrador    │────▶│  Backend operac. │
│  React/Vite  │     │  (BFF, :8200)    │     │  (monólito, :8000)│
│  (:8200)     │     │                  │────▶│                  │
└──────────────┘     └──────────────────┘     └────────┬─────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │  IA/MCP          │
                                              │  (:8100)         │
                                              │  FastAPI+FastMCP │
                                              └──────────────────┘
```

### Componentes

| Componente | Pasta | Porta | Responsabilidade |
|---|---|---|---|
| Frontend React | `orquestrador/frontend` | Servido em 8200 | Telas do lojista, startup e associação |
| Orquestrador (BFF) | `orquestrador` | 8200 | Compõe fluxos, valida contratos, centraliza erros, idempotência e serve o frontend |
| IA/MCP | `ia-mcp` | 8100 | Classificação, resumo e insights por IA + ferramentas MCP somente leitura |
| Backend operacional | `back-end` | 8000 | Fonte da verdade: matching, persistência, autorização e CRUDs |

### Monólito modular (backend)

Camadas com dependências apontando apenas para dentro:

```text
api/         → rotas finas, schemas Pydantic, deps (ator por header)
services/    → casos de uso + regras + autorização por perfil
domain/      → matching (Strategy por critério, puro/determinístico) e roteiro do chat
infra/       → repositories (único lugar com SQL), database, ia_gateway (porta + adaptadores)
container.py → composition root (DI manual)
core/        → config, erros, segurança
config/      → matching.json (pesos, corte 50, frases) e vocabulario.json (tags)
```

**Padrões aplicados:** Repository, Strategy (critérios de matching), Ports & Adapters + Null Object (IA), Composition Root e exceções de domínio → HTTP.

O backend nunca é chamado diretamente pelo frontend: leituras passam pelo pass-through `GET /api/*` do orquestrador e fluxos compostos/escritas por `/orquestracao/*`.

## 3. Ferramentas e tecnologias

| Camada | Tecnologias |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLite, Pydantic, Uvicorn |
| IA/MCP | Python 3.12+, FastAPI, FastMCP (Streamable HTTP), httpx, provedor OpenAI-compatible (Groq/Gemini/Ollama) com fallback heurístico |
| Orquestrador | Python 3.12+, FastAPI, httpx, FastMCP Client |
| Frontend | React 19, Vite 8 (multi-página), JavaScript (ESM) |
| Gestão de dependências | uv (Python), npm (Node) |
| Testes | unittest (backend), pytest (IA/MCP e orquestrador), integração ponta a ponta real (`scripts/integration_check.py`) |
| Configuração | 100% via variáveis de ambiente (`FACESP_*`, `IA_MCP_*`, `ORQ_*`, `AI_*`) |

## 4. Como o sistema atende aos critérios do desafio

### Art. 4º — Responder diretamente ao desafio (I)

- Diagnóstico guiado de 6 perguntas + texto livre → classificação por IA em tags oficiais → matching com startups → ranking com índice 0–100 e justificativa por critério.
- Quando não há match (`sem_match=true`), a demanda vai para a fila de curadoria e pode ser validada/encaminhada, transformando a necessidade em oportunidade de desenvolvimento conjunto.
- Painel da associação: fila de curadoria, validação, encaminhamento, radar de padrões e análise de padrões (insights).

### Art. 4º — Caráter inovador, criativo e original (II)

- Combina IA (classificação textual) com matching determinístico e explicável (8 critérios com pesos e motivos).
- Ferramentas MCP somente leitura (`listar_radar`, `buscar_startups`) expõem dados reais do backend para clientes MCP (IDEs/agentes).
- Síntese em linguagem natural (“resposta do assistente”) gerada a partir dos dados existentes, sem inventar nota/peso.

### Art. 4º — Aplicabilidade prática e viabilidade (III)

- Roda localmente com um comando (`./scripts/dev.sh`), sem serviços externos obrigatórios (funciona offline com heurístico).
- Monólito modular facilita manutenção e evolução por módulo.
- Frontend multi-página preserva URLs e layout original; pass-through `/api/*` evita CORS e mantém o backend como autoridade.
- Idempotência (`Idempotency-Key`), erros centralizados e trilha de execução facilitam operação e depuração.

### Art. 4º — Impacto positivo (IV)

- Melhora a descoberta e comparação de soluções para o lojista (ranking com justificativas por critério).
- Permite teste de 15 dias com feedback demonstrativo.
- Associações reaproveitam a abordagem (radar de padrões, insights com fallback de referência).
- Startups recebem relatório anonimizado/completo com demanda, compatibilidade e sinal de mercado.

### Critérios de sucesso do desafio

**Lojista entende por que uma solução é pertinente:**
- Índice 0–100.
- Top 3 recomendações.
- Critérios com pontuação e motivo.
- Síntese do assistente.
- Página de detalhes.

**Startup recebe informações suficientes:**

Relatório em 6 blocos:
1. Resumo.
2. Perfil da loja.
3. Dor/contexto.
4. Compatibilidade.
5. Sinal de mercado.
6. Próximo passo.

O relatório pode ser anonimizado ou completo, conforme consentimento.

**Outra associação reaproveita com ajustes locais:**
- Radar de padrões.
- Insights com fallback determinístico.
- Configuração 100% por ambiente.

## 5. Fluxo de demonstração (demo)

A demonstração segue um fluxo previsível: o texto livre do lojista já vem preenchido e o teste aparece como previamente concluído, com feedbacks preparados. Isso garante repetibilidade da apresentação sem depender de serviços externos.

### Participantes

**Lojista**
- Apresenta a necessidade.
- Consulta startups recomendadas.
- Acompanha testes e feedbacks.

**Associação**
- Realiza a curadoria das demandas.
- Valida demandas.
- Gera insights.
- Consulta o radar de oportunidades.
- Encaminha oportunidades às startups.

**Startup**
- Recebe oportunidades encaminhadas.
- Consulta relatórios.
- Recebe solicitações de teste.

### Etapas

1. **Identificação da necessidade** — atendimento guiado com 6 perguntas estruturadas (botões) + campo de texto livre.

2. **Classificação por IA** — o serviço de IA interpreta o texto e as respostas, retornando tags/categorias estruturadas. Se a IA falhar, usa-se fallback por botões.

3. **Índice de compatibilidade** — o backend compara a demanda com as startups cadastradas e devolve índice 0–100, top 3, pontuação por critério e justificativas.

4. **Curadoria** — a associação consulta a fila, valida demandas e prepara os dados para análise coletiva.

5. **Padrões e insights** — a associação aciona “Gerar insights”; a IA interpreta grupos de demandas e identifica dores recorrentes. Se indisponível, usa-se o fallback de referência pré-gerado.

6. **Radar de Oportunidades** — organiza as necessidades identificadas (problema, quantidade, categoria, interpretação da IA, startups relacionadas). Visão da associação.

7. **Encaminhamento** — a associação encaminha oportunidades às startups, que passam a ver relatórios com o contexto da demanda.

8. **Teste (15 dias)** — solicitação de teste com autorização. Na demo, o teste aparece como concluído.

9. **Feedback e encerramento** — feedback do lojista sobre a solução testada, fechando o ciclo:

```text
Necessidade → Classificação → Compatibilidade → Curadoria
     → Oportunidade → Startup → Teste → Feedback
```

## 6. Como executar

### Integrado (recomendado)

```bash
cp .env.example .env
./scripts/dev.sh
```

O script sobe backend (`:8000`), IA/MCP (`:8100`) e orquestrador + frontend (`:8200`), espera os health checks e encerra tudo com `Ctrl+C`.

### Por serviço

**Backend**

```bash
cd back-end
python3 -m app.seed
uvicorn app.main:app --reload
```

**IA/MCP**

```bash
cd ia-mcp
uv sync
uv run uvicorn ia_mcp.main:app --port 8100
```

**Orquestrador + frontend**

```bash
cd orquestrador
uv sync
cd frontend && npm install && npm run build && cd ..
uv run uvicorn orquestrador.main:app --port 8200
```

### Testes

```bash
cd back-end      && python3 -m unittest discover -s tests -v
cd ia-mcp        && uv run pytest
cd orquestrador  && uv run pytest
cd orquestrador  && uv run python ../scripts/integration_check.py
```

## 7. Configuração da IA (chave de API)

A chave fica apenas no ambiente do serviço IA/MCP (nunca no frontend).

Exemplo de configuração no `.env` (raiz) ou `ia-mcp/.env`:

```env
AI_PROVIDER=auto            # auto | openai_compatible | heuristic
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=openai/gpt-oss-120b
AI_API_KEY=sua-chave-aqui
AI_TIMEOUT=20
```

Nomes prefixados `IA_MCP_AI_*` também são aceitos (precedência).

Sem chave, o sistema usa o classificador heurístico local e funciona offline. Falhas de autenticação/timeout caem no fallback do backend sem bloquear o fluxo.

## 8. Endpoints principais

### Pass-through (somente GET)

```text
/api/{caminho}
```

### Fluxos compostos

```text
/orquestracao/demandas
/orquestracao/demandas/{id}/matching
/orquestracao/demandas/{id}/validar
/orquestracao/insights
/orquestracao/radar
/orquestracao/padroes
/orquestracao/mcp/radar
/orquestracao/mcp/startups
/orquestracao/testes
/orquestracao/demandas/{id}/encaminhar
/orquestracao/relatorios/{id}
```

### Frontend

```text
/
/chat.html
/resultados.html
/solucao.html
/teste.html
/oportunidade.html
/admin*.html
```

## 9. Estrutura do repositório

```text
.
├── back-end/          # Monólito modular FastAPI + SQLite
├── ia-mcp/            # FastAPI + FastMCP (IA e ferramentas MCP)
├── orquestrador/      # BFF + frontend React (Vite)
│   └── frontend/
├── scripts/           # dev.sh e integration_check.py
├── .env.example
└── README.md
```
