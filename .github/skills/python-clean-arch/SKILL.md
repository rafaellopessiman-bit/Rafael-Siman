---
name: python-clean-arch
description: >
  Estrutura de pastas, camadas e padrões de Clean Architecture para o projeto atlas_local
  (Python 3.12 + PyMongo/Motor + Groq LLM). Guia para criar novos módulos, conhecer as
  fronteiras de camada e convenções de nomenclatura.
---

# Skill: Python Clean Architecture — atlas_local

Esta skill é carregada automaticamente pelo agente **Atlas Architect** e descreve a estrutura
modular do projeto `atlas_local`, as fronteiras entre camadas e os padrões de implementação
esperados em cada módulo.

---

## Estrutura de Pastas (referência canônica)

```text
src/
├── config.py               # get_settings() — leitura centralizada de .env
├── exceptions.py           # Exceções customizadas (não quebre a interface pública)
├── main.py                 # Entrypoint CLI — sem lógica de negócio aqui
├── main_cli_index.py       # Handler CLI: indexação de documentos
├── main_cli_parser.py      # Construção do ArgumentParser
├── main_tabular_compat.py  # Compatibilidade de dados tabulares
│
├── core/                   # Núcleo transversal (sem dependências de negócio)
│   ├── llm_client.py       # Cliente Groq — llama-3.3-70b-versatile
│   ├── output.py           # ÚNICO lugar com print() — renderização de saída
│   ├── schemas.py          # Pydantic schemas / dataclasses compartilhados
│   └── metrics.py          # Coleta de métricas de execução
│
├── storage/                # Acesso ao MongoDB Atlas Local
│   └── document_store.py   # CRUD + índices para knowledge_documents
│
├── knowledge/              # Carregamento e recuperação de documentos
│   ├── loader.py           # Leitura de arquivos (.txt, .md, .json, .csv)
│   └── retriever.py        # Recuperação semântica top-K
│
├── planner/                # Geração de planos de execução (LLM-driven)
│   └── planner.py
│
├── tabular/                # Processamento de dados tabulares e SQL
│   └── executor.py
│
└── integrations/           # Integrações externas (APIs, webhooks)
```

---

## Regra de Dependência (Dependency Rule)

```text
main.py  →  handlers (main_cli_*.py)
              ↓
         knowledge / planner / tabular
              ↓
         storage  (document_store)
              ↓
         core   (llm_client, output, schemas)
              ↓
         config.py / exceptions.py
```

> **Nunca**: camadas internas importem módulos de camadas externas.
> `core/` não importa de `knowledge/` ou `storage/`.
> `storage/` não importa de `knowledge/`.

---

## Template: Novo Módulo de Domínio

```python
# src/knowledge/novo_modulo.py
"""
Descrição concisa do módulo.
Segue Dependency Rule: importa apenas de core/ e config.py.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import get_settings
from src.core.output import render_result
from src.exceptions import AtlasBaseError

if TYPE_CHECKING:
    from pymongo.collection import Collection


class NovoModuloError(AtlasBaseError):
    """Erros específicos do NovoModulo."""


def processar(collection: "Collection", query: str) -> dict:
    """
    Processa query contra a collection e retorna resultado.

    Args:
        collection: Collection PyMongo já inicializada.
        query: Texto a ser processado.

    Returns:
        dict com resultado formatado.

    Raises:
        NovoModuloError: quando o processamento falha.
    """
    settings = get_settings()
    # ... implementação
    render_result({"status": "ok"})
    return {"status": "ok"}
```

---

## Template: Acesso ao MongoDB (storage/)

```python
# src/storage/novo_store.py
from __future__ import annotations

from datetime import datetime, timezone

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from src.config import get_settings
from src.exceptions import StorageError


def get_collection(db_name: str, collection_name: str) -> Collection:
    settings = get_settings()
    client = MongoClient(settings.mongodb_uri)
    return client[db_name][collection_name]


def upsert(collection: Collection, filter_q: dict, data: dict) -> None:
    now = datetime.now(timezone.utc)
    try:
        collection.update_one(
            filter_q,
            {
                "$set": {**data, "updatedAt": now},
                "$setOnInsert": {"createdAt": now, "schemaVersion": 1},
            },
            upsert=True,
        )
    except Exception as exc:
        raise StorageError(f"Falha no upsert: {exc}") from exc
```

---

## Template: Handler CLI (main_cli_*.py)

```python
# src/main_cli_novo.py
"""Handler para o subcommand 'novo' do CLI."""
from __future__ import annotations

import argparse

from src.core.output import render_result
from src.exceptions import AtlasBaseError
from src.knowledge.novo_modulo import processar
from src.storage.document_store import get_collection


def handle_novo(args: argparse.Namespace) -> int:
    """Executa lógica do subcommand 'novo'. Retorna exit code."""
    try:
        col = get_collection("atlas_local_dev", "knowledge_documents")
        result = processar(col, args.query)
        render_result(result)
        return 0
    except AtlasBaseError as exc:
        render_result({"error": str(exc)}, is_error=True)
        return 1
```

---

## Convenções Obrigatórias

| Regra | Detalhe |
|---|---|
| Configuração | Sempre via `get_settings()` de `src/config.py` — nunca `os.environ` direto |
| Output | Apenas `src/core/output.py` usa `print()` — outros módulos chamam `render_result()` |
| Exceções | Somente exceções de `src/exceptions.py` — não crie exceções genéricas |
| Tipagem | Type hints em todas as funções públicas (compatível com `mypy`) |
| Imports | Ordem: stdlib → third-party → local (`src.*`) |
| Estilo | PEP 8 obrigatório |
| Testes | Pasta `tests/` — mocks para Groq API, sem chamadas reais à rede |

---

## Configuração com get_settings()

```python
# src/config.py — uso correto
from src.config import get_settings

settings = get_settings()
print(settings.mongodb_uri)   # ❌ nunca faça isso fora de output.py
uri = settings.mongodb_uri    # ✅ use em código interno
```

---

## Padrões de Teste

```python
# tests/test_novo_modulo.py
from unittest.mock import MagicMock, patch

import pytest

from src.knowledge.novo_modulo import processar, NovoModuloError


def test_processar_retorna_resultado():
    col = MagicMock()
    col.find_one.return_value = {"content": "texto", "_id": "abc"}
    result = processar(col, "minha query")
    assert result["status"] == "ok"


def test_processar_levanta_erro_quando_collection_falha():
    col = MagicMock()
    col.find_one.side_effect = Exception("conexão perdida")
    with pytest.raises(NovoModuloError):
        processar(col, "query")
```

```bash
# Executar testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Comandos de Desenvolvimento

```bash
# Ativar ambiente virtual
.venv\Scripts\Activate.ps1          # Windows PowerShell
source .venv/bin/activate           # Linux/macOS

# Instalar dependências
pip install -r requirements.txt

# Subir MongoDB Atlas Local
docker compose up -d

# Rodar CLI
python -m src.main --help
python -m src.main index --dir data/entrada/
python -m src.main query "Como funciona o sistema?"
```

---

## Anti-Padrões Proibidos

- ❌ Lógica de negócio em `main.py` — delegue para handlers em `main_cli_*.py`
- ❌ Importar `storage/` a partir de `core/` — viola Dependency Rule
- ❌ `time.sleep()` em testes — use mocks de tempo
- ❌ Chamadas reais à API Groq em testes — use `unittest.mock`
- ❌ Commits de `.env` — use `.env.example` como referência
- ❌ Quebrar a interface pública de `src/exceptions.py` — há testes de contrato
