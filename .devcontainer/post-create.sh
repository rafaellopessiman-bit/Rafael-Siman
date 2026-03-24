#!/usr/bin/env bash
# ── post-create.sh — Executado uma vez após criação do Dev Container ────────
set -euo pipefail

echo "🔧 [post-create] Configurando ambiente de desenvolvimento..."

# Cria venv se não existir (volume persistente entre rebuilds)
if [ ! -d "/workspace/.venv" ]; then
    python -m venv /workspace/.venv
    echo "  ✔ venv criado"
fi

# Ativa e instala dependências
source /workspace/.venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r /workspace/requirements.txt

# Instala ferramentas de dev extras (não vão no requirements.txt de prod)
pip install --quiet \
    pytest-cov \
    mypy \
    ruff

echo "  ✔ dependências instaladas"

# Verifica conectividade com MongoDB (aguarda healthcheck do compose)
echo "  ⏳ Aguardando MongoDB Atlas Local..."
for i in $(seq 1 15); do
    if mongosh --quiet --eval "db.runCommand({ping:1}).ok" \
       "mongodb://admin:password@atlas-local-db:27017/?authSource=admin" 2>/dev/null; then
        echo "  ✔ MongoDB Atlas Local conectado"
        break
    fi
    sleep 2
done

echo "✅ [post-create] Ambiente pronto!"
