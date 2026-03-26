---
agent: "NestJS Atlas Architect"
description: >
  Projeta ou revisa equipes e agentes personalizados usando princípios de machine teaching:
  skills explícitas, cenários, selectors, handoffs e metas balanceadas.
---

## Contexto

Use este prompt para desenhar ou revisar agentes personalizados, líderes de equipe e fluxos multiagente do projeto atlas_local.

Referências conceituais incorporadas:

- decompor o problema em **skills** explícitas
- organizar o sistema por **cenários**
- usar um **selector** para decidir qual skill ou agente atua
- separar **percepção, decisão, explicação e validação**
- evitar arquiteturas multiagente desnecessariamente monolíticas ou artificiais

## Tarefa

1. Identificar o objetivo operacional da equipe ou do agente
2. Classificar os cenários que o sistema precisa cobrir
3. Mapear as skills explícitas necessárias
4. Definir qual agente atua como selector ou supervisor
5. Desenhar os handoffs entre agentes ou entre equipes
6. Verificar se existe over-orchestration e simplificar quando possível
7. Produzir uma recomendação final com critérios de uso

## Formato de Saída

```markdown
### Objetivo do Sistema de Agentes
[o que a equipe ou o agente precisa resolver]

### Cenários Cobertos
- [cenário 1]
- [cenário 2]
- [cenário 3]

### Mapa de Skills
| Skill | Responsável | Quando Acionar |
|-------|-------------|----------------|
| ...   | ...         | ...            |

### Selector / Supervisor
[quem decide o roteamento e com base em quais sinais]

### Handoffs
| Origem | Destino | Gatilho | Insumos Obrigatórios |
|--------|---------|---------|----------------------|
| ...    | ...     | ...     | ...                  |

### Riscos de Design
1. [risco]
2. [risco]

### Recomendação Final
[estrutura sugerida + simplificações]
```
