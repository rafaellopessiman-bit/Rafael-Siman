# Setup — Atlas Local no Windows 11

## Pré-requisitos

| Software        | Versão mínima | Verificar                  |
|-----------------|---------------|----------------------------|
| Windows 11      | 23H2+         | `winver`                   |
| Docker Desktop  | 4.30+         | `docker --version`         |
| WSL2            | ativo         | `wsl --status`             |
| Node.js         | 22 LTS        | `node --version`           |
| Python          | 3.12+         | `python --version`         |
| Git             | 2.40+         | `git --version`            |

## Setup Rápido

```powershell
# 1. Clonar e entrar no projeto
cd C:\Users\bonvi\Documents
git clone <repo-url> atlas_local
cd atlas_local

# 2. Criar .env
Copy-Item .env.example .env
# Editar .env → preencher GROQ_API_KEY

# 3. Criar e ativar venv Python
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Validar tudo de uma vez
.\scripts\windows\bootstrap.ps1

# 5. Subir ambiente
.\scripts\windows\start-all.ps1
```

## Verificação Pós-Setup

```powershell
# Health check completo
.\scripts\windows\health-check.ps1

# Indexar documentos de exemplo
.\scripts\windows\reindex-docs.ps1

# Testar CLI Python
python -m src.main ask "O que há nos documentos?"

# Testar API NestJS
# Swagger: http://localhost:3000/api
# Health:  http://localhost:3000/health
```

## Estrutura de Pastas Operacionais

```text
atlas_local/
├── scripts/windows/       ← Scripts PowerShell de operação
│   ├── bootstrap.ps1      ← Valida ambiente
│   ├── start-all.ps1      ← Sobe Docker + API
│   ├── stop-all.ps1       ← Para containers
│   ├── health-check.ps1   ← Verifica tudo
│   ├── backup-mongo.ps1   ← Backup MongoDB + SQLite
│   ├── restore-mongo.ps1  ← Restaura backup
│   ├── reindex-docs.ps1   ← Reindexa documentos
│   ├── clean-temp.ps1     ← Limpa temp e logs antigos
│   └── collect-diagnostics.ps1 ← Gera relatório de suporte
├── data/
│   ├── entrada/           ← Documentos para indexação
│   ├── indice/            ← Índice gerado
│   ├── processados/       ← Artefatos processados
│   ├── backup/            ← Backups MongoDB e SQLite
│   └── temp/              ← Temporários (auto-limpeza)
├── logs/
│   ├── app/               ← Logs de start/stop
│   ├── maintenance/       ← Logs de backup/reindex
│   └── diagnostics/       ← Relatórios de health e diagnóstico
└── .vscode/
    └── tasks.json         ← Tarefas prontas (Ctrl+Shift+B)
```

## VS Code Tasks

Acesse via **Ctrl+Shift+P** → `Tasks: Run Task`:

| Task                          | O que faz                         |
|-------------------------------|-----------------------------------|
| Atlas: Bootstrap Ambiente     | Valida pré-requisitos             |
| Atlas: Start (Docker + API)   | Sobe MongoDB + NestJS             |
| Atlas: Stop                   | Para containers                   |
| Atlas: Health Check           | Verifica saúde de tudo            |
| Atlas: Reindex Documentos     | Reindexa via CLI Python           |
| Atlas: Backup MongoDB + SQLite| Backup com timestamp              |
| Atlas: Limpeza                | Remove temp e logs antigos        |
| Atlas: Coletar Diagnóstico    | Gera relatório para suporte       |
| Python: Executar Testes       | pytest tests/ -v                  |
| NestJS: Executar Testes e2e   | npm run test:e2e                  |
| Python: Ask                   | Pergunta interativa ao RAG        |
| Atlas: Abrir Swagger          | Abre /api no browser              |

## Portas Utilizadas

| Porta | Serviço               |
|-------|-----------------------|
| 3000  | NestJS API + Swagger  |
| 27017 | MongoDB Atlas Local   |

## Variáveis de Ambiente Essenciais

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| GROQ_API_KEY | Sim | Chave da API Groq |
| GROQ_MODEL | Não | Modelo LLM (default: llama-3.3-70b-versatile) |
| MONGODB_URI | Não | URI do MongoDB (tem default) |
| MONGODB_DB | Não | Nome do banco (default: atlas_local_db) |
| DATABASE_PATH | Não | Caminho do SQLite local |
| DOCUMENTS_PATH | Não | Pasta de documentos |
