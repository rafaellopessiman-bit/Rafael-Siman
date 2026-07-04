# Agent Skills — atlas_local

Canônico para **Cursor Agent**: `.cursor/skills/<nome>/SKILL.md`

Espelho para **GitHub Copilot**: `.github/skills/<nome>/SKILL.md` (manter sincronizado)

## Skills

| Skill | Escopo | Uso |
| --- | --- | --- |
| `python-clean-arch` | `src/**/*.py` | Módulos Python, camadas, convenções |
| `nestjs-clean-arch` | `**/*.ts` | Módulos NestJS, features, domínios |
| `mongodb-atlas-schema` | `**/*.ts` | Schemas Mongoose, índices, embedding |

## Manutenção

1. Edite em `.cursor/skills/<nome>/SKILL.md`
2. Copie para `.github/skills/<nome>/SKILL.md`
3. Verifique referências em `.github/agents/*.agent.md`

Ver também: [docs/operations/vscode-multiagent-workflow.md](../../docs/operations/vscode-multiagent-workflow.md)
