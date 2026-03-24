---
description: "Gera docker-compose.yml e devcontainer.json atualizados para MongoDB Atlas Local. Use quando precisar configurar ou atualizar o ambiente de desenvolvimento local com Docker."
agent: "Atlas Architect"
argument-hint: "Informe porta, nome do banco e se quer Dev Container completo (sim/não)"
tools: [read, search, web, edit, execute]
---

Você é o **Atlas Architect**. Gere os arquivos de infraestrutura para rodar **MongoDB Atlas Local** em desenvolvimento usando Docker, adaptados ao projeto `atlas_local`.

## Inputs

- **Porta MongoDB**: {{mongoPort}}  _(padrão: `27017`)_
- **Nome do banco de desenvolvimento**: {{dbName}}  _(padrão: `atlas_local_dev`)_
- **Incluir Dev Container completo**: {{includeDevContainer}}  _(sim/não)_

## O que entregar

### 1. `docker-compose.yml`

Gere um `docker-compose.yml` completo na raiz do projeto com:
- Serviço `mongodb` usando a imagem oficial `mongodb/mongodb-atlas-local` (versão mais recente estável)
- Volume nomeado para persistência dos dados
- Health check configurado
- Variáveis de ambiente mínimas necessárias
- Porta mapeada conforme o input

Formato exato esperado — deve ser pronto para `docker compose up -d`.

### 2. `.env.example`

Atualize ou crie o arquivo `.env.example` com as variáveis de conexão MongoDB:

```env
MONGODB_URI=mongodb://localhost:{{mongoPort}}/
MONGODB_DB={{dbName}}
```

### 3. `devcontainer.json` _(se `includeDevContainer` = sim)_

Gere `.devcontainer/devcontainer.json` com:
- Imagem base Python 3.12
- Serviço `mongodb` do compose como `dockerComposeFile`
- Extensions recomendadas: MongoDB for VS Code, Python, Pylance, GitLens
- `postCreateCommand` para instalar dependências do `requirements.txt`
- `forwardPorts` incluindo a porta MongoDB

### 4. Comandos de Validação

Forneça os comandos prontos para:
```bash
# Subir o ambiente
docker compose up -d

# Verificar conexão
mongosh "mongodb://localhost:{{mongoPort}}/" --eval "db.runCommand({ ping: 1 })"

# Ver logs do container Atlas Local
docker compose logs -f mongodb
```

### 5. Checklist de Integração com o Projeto

- [ ] Adicionar `motor` ou `pymongo` ao `requirements.txt`
- [ ] Atualizar `src/storage/document_store.py` para usar a URI do `.env`
- [ ] Adicionar `.env` ao `.gitignore`
- [ ] Confirmar acesso em `mongosh` antes de iniciar o dev
