# FACESP Match — Backend operacional (monolito modular)

Python + FastAPI + SQLite. A IA e o MCP são módulos de outras pessoas: aqui só existe a **porta** (`IAGateway`) e fallbacks.

## Rodar
```bash
pip install -r requirements.txt
python -m app.seed                 # apaga e recria o banco da demo (rodar no início do dia)
uvicorn app.main:app --reload      # também faz o seed sozinho se o banco estiver vazio
python -m unittest discover -s tests -v
```
O frontend inicial está em `frontend/` e é servido pelo FastAPI: acesse `http://127.0.0.1:8000/`.
Na tela de acesso, os lojistas e startups são carregados pela API. Ao entrar como lojista, o chat
consulta `GET /api/chat/roteiro`, envia as respostas para `POST /api/demandas` e mostra a classificação
e o matching retornados na página `frontend/resultados.html`. O perfil escolhido fica em
`sessionStorage` (`orvyn-demo-actor`) para uso pelas telas; esse fluxo é demonstrativo e não substitui
autenticação real.
Ao entrar como startup, a página `frontend/oportunidade.html` lista os relatórios encaminhados e abre
somente a versão anonimizada do relatório.
O perfil de associação abre `frontend/admin.html`, com a fila de curadoria, os detalhes das demandas,
a análise de padrões e o radar de oportunidades. O lojista pode abrir os detalhes da solução e pedir
um teste de 15 dias após consentir. A conclusão/avaliação do teste continua demonstrativa: o endpoint
atual preenche um feedback de exemplo, não recebe respostas reais.
Nos resultados, a resposta do assistente é uma síntese em linguagem natural das respostas, do texto livre,
dos critérios do matching e da solução cadastrada; ela não é uma resposta gerada por um modelo de IA.
Na análise de padrões, a sugestão é identificada como análise da IA ou referência de contingência.
O painel também consulta `GET /api/mcp/radar` e `GET /api/mcp/startups?tag=...` para exibir o retorno
das ferramentas MCP em modo somente leitura.

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
