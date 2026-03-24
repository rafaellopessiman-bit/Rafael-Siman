# ── atlas_local Dev Container ────────────────────────────────────────────────
# Python 3.12 + ferramentas de desenvolvimento para MongoDB Atlas Local
# Build:  docker compose --profile app build
# ─────────────────────────────────────────────────────────────────────────────
FROM mcr.microsoft.com/devcontainers/python:3.12

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /workspace

# Dependências de sistema (mongosh, curl para healthcheck, git)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       git \
       gnupg \
       jq \
    && rm -rf /var/lib/apt/lists/*

# Instala mongosh para interação direta com Atlas Local
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc \
    | gpg --dearmor -o /usr/share/keyrings/mongodb-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" \
    | tee /etc/apt/sources.list.d/mongodb-org-8.0.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends mongodb-mongosh \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python antecipadamente (cache de layer Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# O restante do código é montado via volume pelo Dev Container / docker-compose
