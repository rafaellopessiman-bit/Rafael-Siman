---
description: >
  Use when: creating, updating, or reporting any execution plan, todo list, progress state,
  or step tracking in chat. Defines the single source of truth for plan governance,
  synchronization cadence, allowed status transitions, and conflict resolution.
applyTo: "**"
---

# Plan Governance — atlas_local

## Fonte Única de Verdade

- Esta instrução é a autoridade principal para governança de plano no chat.
- Se houver sobreposição com agentes, prompts ou instruções gerais, esta instrução prevalece para criação, atualização e encerramento de planos.
- Outros arquivos devem referenciar esta instrução, não duplicar regras extensas de sincronização.

## Quando Criar Plano

- Crie plano apenas quando a tarefa tiver múltiplas etapas, risco de regressão, validação explícita, ou edição relevante em mais de um arquivo.
- Não crie plano para pedidos triviais de uma única ação claramente executável.
- Ao criar plano, use títulos curtos, orientados a ação e verificáveis.

## Estados Permitidos

- Use apenas: `not-started`, `in-progress`, `completed`.
- Mantenha no máximo um item como `in-progress` por vez.
- Não deixe item concluído em `not-started` ou `in-progress`.
- Não marque item como `completed` antes da validação mínima esperada para aquela etapa.

## Sincronização Obrigatória

- Sincronize o plano imediatamente após qualquer lote relevante.
- Considere lote relevante:
  - edição de 3 ou mais arquivos
  - conclusão de uma etapa planejada
  - rodada de testes focados
  - execução da suíte completa
  - mudança de estratégia por erro, bloqueio ou descoberta relevante
- Se o estado real divergir do plano visível, corrija o plano antes de seguir com novas ações.

## Antes da Resposta Final

- O plano exibido no chat deve refletir o estado real do trabalho naquele momento.
- Se todas as etapas conhecidas terminaram, todas devem estar em `completed` antes da resposta final.
- Se restarem riscos ou trabalho pendente, o plano deve mostrar explicitamente o que ficou em aberto.

## Replanejamento

- Ao descobrir escopo adicional, atualize o plano em vez de manter etapas implícitas fora do chat.
- Ao descartar uma etapa por mudança de abordagem, remova ou substitua a etapa obsoleta na próxima sincronização.
- Não mantenha plano stale por conveniência narrativa.

## Validação Mínima por Tipo de Etapa

- Implementação: código alterado e verificado sem erros óbvios.
- Testes: resultado executado e interpretado.
- Revisão: achados ou veredicto emitidos.
- Documentação: arquivo atualizado de acordo com a mudança real.

## Anti-padrões Proibidos

- Encerrar resposta com plano desatualizado.
- Manter múltiplos itens `in-progress` sem necessidade explícita.
- Declarar conclusão só no texto final e não no plano.
- Tratar o plano como decorativo; ele deve ser operacional.
