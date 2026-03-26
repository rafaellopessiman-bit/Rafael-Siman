---
agent: "Python IA Tech Lead"
description: >
  Template para implementar uma nova feature no pipeline Python.
  Segue o workflow TDD: testes primeiro, depois implementação, depois validação.
---

## Informações Necessárias

Antes de começar, preciso saber:

1. **O que**: Descreva a feature em 1-2 frases
2. **Onde**: Qual módulo será afetado (`knowledge/`, `storage/`, `core/`, `planner/`, `tabular/`)
3. **Impacto no retrieval**: Essa mudança afeta scoring ou ranking? (sim/não)

## Workflow de Implementação

### Fase 1 — Testes Primeiro

- Criar arquivo `tests/test_<feature>.py` com pelo menos 8 testes:
  - 3+ happy path
  - 2+ edge cases (vazio, None, limites)
  - 1+ erro esperado
  - 1+ integração com módulo adjacente
  - 1+ regressão se impacta retrieval

### Fase 2 — Implementação

- Código em `src/<modulo>/<feature>.py`
- Type hints em todas as funções públicas
- Sem `print()` — usar `src/core/output.py`
- Constantes nomeadas no topo do módulo

### Fase 3 — Validação

```bash
pytest tests/ -v --tb=short
# Se impacta retrieval:
python -m src.main evaluate
```

### Fase 4 — Revisão

- Verificar que 181+ testes passam
- Se impacta retrieval, comparar com baseline
- Emitir resumo da mudança

## Formato de Entrega

```markdown
### Feature: [nome]
### Arquivos Criados/Modificados: [lista]
### Testes: XXX criados, XXX total passando
### Baseline Impact: [sem impacto | melhorou X% | inalterado]
```
