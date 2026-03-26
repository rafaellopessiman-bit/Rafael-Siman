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

```text
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

## Equipes de Agentes

O projeto possui **duas equipes** de agentes especializados:

### Equipe NestJS/Atlas (Pesquisa e Análise)

Foco: **pesquisa, análise arquitetural e design** — NÃO implementa código, produz design docs, ADRs e recomendações.

| Agente | Foco |
|--------|------|
| **NestJS Atlas Architect** (líder) | Orquestra pesquisa, distribui análises, consolida entregas |
| **Atlas Schema Expert** | Pesquisa de data modeling, embedding vs referencing, design docs |
| **NestJS Architecture Expert** | Análise de padrões arquiteturais, ADRs, avaliação de trade-offs |
| **Atlas Local Infrastructure Expert** | Análise de Docker, Dev Containers, CI/CD, documentação operacional |
| **Atlas Architect** | Análise profunda de performance, capacity planning, índices, segurança |

### Equipe Python/IA (Programação e Pipeline)

Foco: **implementação, testes e manutenção** do pipeline Python de retrieval e IA.

| Agente | Foco |
|--------|------|
| **Python IA Tech Lead** (líder) | Orquestra pipeline Python de retrieval e IA |
| **Python Retrieval Architect** | FTS5, BM25, scoring, fusão, chunking, evaluation |
| **Python LLM Integration Expert** | Groq API, prompts, cache, abstention |
| **Python QA Reviewer** | Revisão, cobertura, regressão, contratos |
| **Python Testing Specialist** | pytest, fixtures, mocks, coverage |

### Roteamento entre Equipes

- **Pesquisa, análise, design, schema, MongoDB, arquitetura, Docker** → Equipe NestJS/Atlas (pesquisa)
- **Implementação, retrieval, scoring, LLM, testes Python, avaliação** → Equipe Python/IA (programação)
- **Análise que resulta em implementação** → NestJS/Atlas analisa → handoff → Python/IA implementa

## Princípios de Machine Teaching para Agentes

- Trate cada equipe como uma **rede de skills explícitas**, não como um agente monolítico que tenta fazer tudo
- **Classifique o cenário primeiro**: schema, arquitetura, infraestrutura, retrieval, LLM, QA, testes, ou cross-team
- **Professor antes de executor**: líderes devem decompor o problema, sequenciar trabalho e delegar com contexto claro
- **Handoff obrigatório** entre especialistas/equipes: contexto, cenário, objetivo, restrições, evidências e critério de pronto
- **Balanceie objetivos**: qualidade, latência, custo, explicabilidade e prazo
- **Evite multiagentes artificiais**: use múltiplos especialistas apenas quando houver ganho real de especialização
- **Explique o sistema por partes**: sempre que possível, separe percepção, decisão, explicação e validação

## Sincronização do Plano no Chat

- A governança de plano no chat é definida pela instrução dedicada `.github/instructions/plan-governance.instructions.md`.
- Não replique regras extensas de sincronização em outros arquivos; use essa instrução como fonte única.

## Template de Handoff Entre Equipes

Use este template sempre que uma equipe concluir análise e encaminhar trabalho para outra:

```md
### Handoff
- Contexto: [qual problema está sendo resolvido]
- Cenário: [retrieval | llm | qa | testing | schema | arquitetura | infraestrutura | performance | cross-team]
- Objetivo: [resultado esperado]
- Restrições: [regras técnicas, compatibilidade, limites]
- Evidências: [métricas, docs, diagnósticos, benchmark, traces]
- Critério de pronto: [condições verificáveis para concluir]
```

## Matriz Oficial de Cenários — atlas_local

| Área | Cenários Oficiais | Sinais de Entrada | Especialista Primário | Entregável Esperado |
|---|---|---|---|---|
| Retrieval | `literal`, `semântico`, `metadata-heavy`, `baixa evidência`, `regressão de ranking` | queda de MRR, top1 piora, chunks irrelevantes, score opaco | Python Retrieval Architect | ajuste de ranking, baseline, testes, trace |
| LLM | `resposta factual`, `síntese`, `planejamento`, `follow-up`, `abstenção` | resposta alucinada, prompt ruim, custo alto, latência, baixa confiança | Python LLM Integration Expert | prompt revisado, mocks, política de geração |
| QA | `revisão de mudança`, `regressão`, `coverage gap`, `contrato quebrado` | testes falhando, diff de risco, baseline alterado, cobertura baixa | Python QA Reviewer | veredicto, riscos, ações corretivas |
| Testing | `novo módulo`, `bugfix`, `regressão`, `mock externo`, `integração local` | falta de testes, flaky, módulo novo, edge cases não cobertos | Python Testing Specialist | suite pytest, fixtures, mocks |
| Infra | `bootstrap`, `operação local`, `diagnóstico`, `observabilidade`, `backup/restore`, `ci/cd` | container não sobe, health check falha, logs ruins, restore incerto | Atlas Local Infrastructure Expert | runbook, config review, rollback plan |
| Arquitetura | `modularização`, `boundary`, `integração`, `escalabilidade`, `operabilidade` | acoplamento alto, estrutura confusa, dependências cruzadas | NestJS Architecture Expert | ADR, diagrama C4, plano de migração |
| Schema | `catálogo`, `documento`, `evento`, `cache`, `read model` | dúvidas de modelagem, queries lentas, arrays crescendo | Atlas Schema Expert | design doc, diagrama ER, índices |
| Performance MongoDB | `read-heavy`, `write-heavy`, `growth`, `retention`, `security`, `cost` | explain ruim, índice faltando, working set alto, custo operacional | Atlas Architect | design review, análise de capacidade, recomendação |

### Regra de Roteamento por Cenário

- Um cenário primário deve ser escolhido antes de qualquer delegação.
- Se houver cenário secundário, ele entra como suporte, não como dono da tarefa.
- Se a análise gerar implementação, use o template de handoff acima.
- Se um único especialista cobre o cenário com segurança, não fragmentar a tarefa.

### Prompts Disponíveis

- `new-schema.prompt.md` — Gerar schema MongoDB
- `docker-atlas-local.prompt.md` — Infraestrutura Docker
- `retrieval-regression.prompt.md` — Verificar regressão no retrieval
- `corpus-hygiene.prompt.md` — Auditoria de qualidade do corpus
- `data-prep-audit.prompt.md` — Auditoria de preparação e saneamento de dados
- `outlier-analysis.prompt.md` — Auditoria de outliers e clusters suspeitos no corpus
- `feature-selection-review.prompt.md` — Revisão disciplinada de sinais e features
- `new-python-feature.prompt.md` — Template TDD para nova feature Python
- `agent-brain-design.prompt.md` — Projetar ou revisar equipes/agentes com abordagem de machine teaching
- `cross-team-handoff.prompt.md` — Padronizar handoff entre equipes ou especialistas
- `initial-triage.prompt.md` — Triagem inicial para classificar cenário, equipe e especialista primário

## O que NÃO fazer

- Não commite `.env` — use `.env.example` como referência.
- Não adicione lógica de negócio em `main.py` — use os módulos em `src/`.
- Não quebre a interface pública de `src/exceptions.py` (há testes de contrato).
- Não use `time.sleep()` em testes — use mocks de tempo.
