# Auditoria de Extensões VS Code

Data da auditoria: 2026-03-24

Objetivo:

- reduzir a superfície de acesso irrestrito ao filesystem do workspace;
- revisar extensões AI e publishers não essenciais;
- manter apenas o conjunto necessário para o fluxo atual do projeto.

## Método

Referência operacional recomendada:

```powershell
code --list-extensions
```

Neste host, o comando `code --list-extensions` não retornou saída útil no terminal integrado. A auditoria foi feita pela pasta local de extensões do VS Code.

## Extensões encontradas

### Baixa preocupação / esperadas

| Extensão | Motivo |
| --- | --- |
| `davidanson.vscode-markdownlint` | lint Markdown |
| `eamodio.gitlens` | inspeção Git |
| `github.copilot-chat` | assistência AI conhecida |
| `google.geminicodeassist` | assistência AI conhecida |
| `mechatroner.rainbow-csv` | utilitário de CSV |
| `ms-azuretools.vscode-containers` | containers / Docker |
| `ms-python.debugpy` | debug Python |
| `ms-python.python` | runtime Python |
| `ms-python.vscode-pylance` | análise Python |
| `ms-python.vscode-python-envs` | ambientes Python |
| `ms-vscode-remote.remote-containers` | Dev Containers |
| `ms-vscode.powershell` | scripts PowerShell |
| `ms-ceintl.vscode-language-pack-pt-br` | language pack |

### Revisar e remover se não forem estritamente necessárias

| Extensão | Ação sugerida | Observação |
| --- | --- | --- |
| `appland.appmap` | revisar | acessa telemetria de execução e estrutura do projeto |
| `ex3ndr.llama-coder` | revisar / remover | publisher menos estabelecido; extensão AI |
| `futuretechnexus.getbotai` | revisar / remover | extensão AI; validar política de privacidade |
| `keploy.keployio` | revisar | útil só se houver uso ativo de geração/observação de testes |
| `kodu-ai.claude-dev-experimental` | remover se não usada | experimental + AI + acesso amplo ao workspace |

## Checklist de revisão em 10 minutos

1. Confirmar se cada extensão AI é realmente usada no fluxo atual.
2. Verificar publisher, página da Marketplace e política de privacidade.
3. Remover extensões AI redundantes. Hoje há múltiplas instaladas no host.
4. Manter no máximo um conjunto principal por função: chat, completion, containers, Python.
5. Revalidar permissões após updates de extensões experimentais.

## Comandos úteis

```powershell
# Listar extensões
code --list-extensions

# Desinstalar uma extensão
code --uninstall-extension ex3ndr.llama-coder

# Repetir a auditoria após limpeza
code --list-extensions
```

## Resultado aplicado no projeto

- telemetria nativa do VS Code desativada no workspace;
- sugestões AI inline automáticas desativadas no workspace;
- arquivos `.aiexclude` e `.copilotignore` criados na raiz para reduzir contexto de arquivos sensíveis e artefatos locais.
