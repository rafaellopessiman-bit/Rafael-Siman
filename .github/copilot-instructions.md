# Project Guidelines — atlas_local

## Visão Geral

`atlas_local` é um sistema de **inteligência documental local** em Python. Processa e indexa documentos (`.txt`, `.md`, `.json`, `.csv`), usa recuperação semântica por top-K e um LLM (Groq / llama-3.3-70b-versatile) para responder perguntas sobre o conteúdo indexado. O banco de dados primário em desenvolvimento é **MongoDB Atlas Local** (via Docker).

## Stack Técnica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| LLM | Groq API — modelo `llama-3.3-70b-versatile` |
| Banco de dados | MongoDB Atlas Local (`mongodb/mongodb-atlas-local`) |
| Driver MongoDB | PyMongo / Motor (async) |
| Configuração | `python-dotenv` + `.env` na raiz |
| Testes | `pytest` — pasta `tests/` |
| Ambiente dev | Docker Compose + VS Code Dev Containers |

## Estrutura de Pastas

```
src/
  config.py           # Configurações globais e variáveis de ambiente
  main.py             # Entrypoint CLI principal
  core/               # LLM client, schemas, métricas, output rendering
  storage/            # Document store (acesso ao MongoDB)
  knowledge/          # Loader e retriever de documentos
  planner/            # Geração de planos de execução
  tabular/            # Processamento de dados tabulares e SQL
  integrations/       # Integrações externas (ex.: APIs)
data/
  entrada/            # Documentos de entrada para indexação
  indice/             # Índice gerado (indice.json)
  processados/        # Artefatos de saída processados
tests/                # Testes unitários e de integração
tools/                # Scripts utilitários e patches
```

## Convenções de Código

- **PEP 8** obrigatório. Tipagem com `mypy`-compatible type hints em funções públicas.
- Imports ordenados: stdlib → third-party → local (`src.*`).
- Nunca use `print()` fora de `src/core/output.py` — use o módulo `output` para renderização.
- Exceções customizadas vivem em `src/exceptions.py` — não crie exceções genéricas.
- Configurações: sempre leia de `src/core/config.py` (via `get_settings()`), nunca diretamente de `os.environ` nos módulos internos.

## MongoDB e Schemas

- Siga as regras em `.github/instructions/mongodb-conventions.instructions.md` (auto-carregado pelo Copilot via `applyTo`).
- Collections: `snake_case` plural. Campos: `camelCase`.
- Todo documento deve ter `createdAt`, `updatedAt` (UTC) e `schemaVersion`.
- URI de conexão: variável `MONGODB_URI` no `.env` (fallback: `mongodb://localhost:27017/`).

## Testes

```bash
# Rodar todos os testes
pytest tests/ -v

# Rodar um teste específico
pytest tests/test_smoke.py -v

# Com cobertura
pytest tests/ --cov=src --cov-report=term-missing
```

- Testes não devem fazer chamadas reais à API do Groq — use mocks.
- Fixtures de banco de dados usam banco SQLite em memória (legado) ou MongoDB Atlas Local em container.

## Build e Execução

```bash
# Ativar ambiente virtual
.venv\Scripts\Activate.ps1          # Windows PowerShell
source .venv/bin/activate           # Linux/macOS

# Instalar dependências
pip install -r requirements.txt

# Rodar CLI principal
python -m src.main --help

# Subir MongoDB Atlas Local
docker compose up -d
```

## O que NÃO fazer

- Não commite `.env` — use `.env.example` como referência.
- Não adicione lógica de negócio em `main.py` — use os módulos em `src/`.
- Não quebre a interface pública de `src/exceptions.py` (há testes de contrato).
- Não use `time.sleep()` em testes — use mocks de tempo.
