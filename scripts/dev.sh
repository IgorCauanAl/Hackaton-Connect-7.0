#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

# ------------------------------------------------------------------ ambiente
if [[ -f "$RAIZ/.env" ]]; then
  set -a
  source "$RAIZ/.env"
  set +a
  echo "• Ambiente carregado de $RAIZ/.env"
else
  echo "• Aviso: $RAIZ/.env não encontrado; usando padrões (veja .env.example)."
fi

BACKEND_PORT="${FACESP_API_PORT:-8000}"
IA_PORT="${IA_MCP_API_PORT:-8100}"
ORQ_PORT="${ORQ_API_PORT:-8200}"

# --------------------------------------------------------------- pré-requisitos
for ferramenta in uv curl npm; do
  if ! command -v "$ferramenta" >/dev/null 2>&1; then
    echo "✗ '$ferramenta' não encontrado no PATH." >&2
    exit 1
  fi
done

porta_ocupada() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") >/dev/null 2>&1
}

for porta in "$BACKEND_PORT" "$IA_PORT" "$ORQ_PORT"; do
  if porta_ocupada "$porta"; then
    echo "✗ A porta $porta já está em uso. Encerre o processo existente ou ajuste o .env." >&2
    echo "  (o script não mata processos de outros membros da equipe)" >&2
    exit 1
  fi
done

# ---------------------------------------------------------- dependências locais
if [[ ! -d "$RAIZ/ia-mcp/.venv" ]]; then
  echo "• Instalando dependências do IA/MCP..."
  (cd "$RAIZ/ia-mcp" && uv sync)
fi

if [[ ! -d "$RAIZ/orquestrador/.venv" ]]; then
  echo "• Instalando dependências do orquestrador..."
  (cd "$RAIZ/orquestrador" && uv sync)
fi

if [[ ! -d "$RAIZ/orquestrador/frontend/node_modules" ]]; then
  echo "• Instalando dependências do frontend..."
  (cd "$RAIZ/orquestrador/frontend" && npm install)
fi

if [[ ! -f "$RAIZ/orquestrador/frontend/dist/index.html" ]] \
   || [[ "${ORVYN_FORCE_BUILD:-0}" == "1" ]]; then
  echo "• Gerando build do frontend (Vite)..."
  (cd "$RAIZ/orquestrador/frontend" && npm run build)
fi

# --------------------------------------------------------------------- limpeza
PIDS=()
cleanup() {
  trap - INT TERM EXIT
  echo
  echo "• Encerrando serviços iniciados por este script..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  wait >/dev/null 2>&1 || true
  echo "• Pronto."
}
trap cleanup INT TERM EXIT

esperar() {
  local nome="$1" url="$2" pid="$3" limite="${4:-90}"
  local i
  for ((i = 0; i < limite; i++)); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      printf '  ✓ %s (%s)\n' "$nome" "$url"
      return 0
    fi
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      printf '  ✗ %s terminou antes de responder (%s)\n' "$nome" "$url" >&2
      return 1
    fi
    sleep 1
  done
  printf '  ✗ %s não respondeu em %ss (%s)\n' "$nome" "$limite" "$url" >&2
  return 1
}

# -------------------------------------------------------------------- backend
echo "• Subindo backend operacional na porta $BACKEND_PORT..."
(
  cd "$RAIZ/back-end"
  exec uv run --no-project --with-requirements ../requirements.txt \
    uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
) &
PIDS+=("$!")
esperar "backend" "http://127.0.0.1:$BACKEND_PORT/api/saude" "${PIDS[-1]}" || exit 1

# --------------------------------------------------------------------- IA/MCP
echo "• Subindo IA/MCP na porta $IA_PORT..."
(
  cd "$RAIZ/ia-mcp"
  exec uv run uvicorn ia_mcp.main:app \
    --host "${IA_MCP_API_HOST:-0.0.0.0}" --port "$IA_PORT"
) &
PIDS+=("$!")
esperar "IA/MCP" "http://127.0.0.1:$IA_PORT/openapi.json" "${PIDS[-1]}" || exit 1

# ------------------------------------------------------------- orquestrador
echo "• Subindo orquestrador + frontend na porta $ORQ_PORT..."
(
  cd "$RAIZ/orquestrador"
  exec uv run uvicorn orquestrador.main:app \
    --host "${ORQ_API_HOST:-0.0.0.0}" --port "$ORQ_PORT"
) &
PIDS+=("$!")
esperar "orquestrador" "http://127.0.0.1:$ORQ_PORT/health" "${PIDS[-1]}" || exit 1

cat <<EOF

────────────────────────────────────────────────────────────
  ORVYN HUB no ar
────────────────────────────────────────────────────────────
  Frontend + API   http://localhost:$ORQ_PORT/
  Orquestrador     http://localhost:$ORQ_PORT/health
  IA/MCP           http://localhost:$IA_PORT/ia/*  (MCP: /mcp/)
  Backend          http://localhost:$BACKEND_PORT/api/saude

  Teste de integração (em outro terminal):
    cd orquestrador && uv run python ../scripts/integration_check.py

  Ctrl+C encerra os três serviços iniciados aqui.
────────────────────────────────────────────────────────────
EOF

wait
