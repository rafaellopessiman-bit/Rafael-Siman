# Troubleshooting — Atlas Local no Windows 11

## Diagnóstico Rápido

```powershell
# Primeiro passo — sempre
.\scripts\windows\health-check.ps1

# Se precisar de detalhes completos
.\scripts\windows\collect-diagnostics.ps1
# → Relatório em logs\diagnostics\
```

---

## Problemas Comuns

### Docker Desktop não inicia

**Sintoma:** `docker info` falha, health-check reporta FAIL.

**Soluções (em ordem):**
1. Reiniciar Docker Desktop
2. Verificar WSL2: `wsl --update`
3. Verificar Hyper-V habilitado: `Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V`
4. Reiniciar Windows

### Porta 3000 ou 27017 ocupada

**Sintoma:** `start-all.ps1` falha, container não sobe.

```powershell
# Descobrir o que ocupa a porta
Get-NetTCPConnection -LocalPort 3000 -State Listen |
    Select-Object OwningProcess |
    ForEach-Object { Get-Process -Id $_.OwningProcess }

# Matar processo se seguro
Stop-Process -Id <PID> -Force
```

### MongoDB container não fica healthy

**Sintoma:** health-check mostra MongoDB WARN/FAIL.

```powershell
# Ver logs do container
docker logs atlas-local-db --tail 50

# Reiniciar só o MongoDB
docker compose restart atlas-local-db

# Se persistir — recriar sem perder volume
docker compose down
docker compose up -d atlas-local-db
```

### NestJS não responde em /health

**Sintoma:** API timeout, health-check FAIL.

```powershell
# Ver logs do NestJS
docker logs atlas-local-nestjs --tail 50

# Rebuild se deps mudaram
docker compose build nestjs-app
docker compose up -d nestjs-app
```

### Python venv corrompida

**Sintoma:** `ModuleNotFoundError`, pip não funciona.

```powershell
# Recriar do zero
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### SQLite database locked

**Sintoma:** erro de lock ao indexar ou consultar.

```powershell
# Verificar quem segura o arquivo
Get-Process | Where-Object {
    $_.Modules.FileName -match 'atlas_local.db'
} -ErrorAction SilentlyContinue

# Encerrar processo se seguro, ou aguardar
# O SQLite libera locks automaticamente quando a operação termina
```

### Indexação sem documentos

**Sintoma:** `Nenhum arquivo textual suportado foi encontrado`.

**Verificar:**
1. Há arquivos em `data\entrada\`?
2. Extensões suportadas: `.txt`, `.md`, `.json`
3. Arquivos não estão vazios?

```powershell
Get-ChildItem data\entrada -Recurse -Include *.txt,*.md,*.json | Measure-Object
```

### Erro de GROQ_API_KEY

**Sintoma:** `GROQ_API_KEY está ausente ou vazio`.

```powershell
# Verificar .env
Select-String -Pattern 'GROQ_API_KEY' -Path .env

# A chave precisa ser válida e sem espaços extras
# Formato: gsk_xxxxxxxxxxxxxxxxxxxx
```

### DevContainer não abre

**Sintoma:** VS Code falha ao reabrir no container.

**Soluções:**
1. Verificar Docker Desktop rodando
2. `Ctrl+Shift+P` → `Dev Containers: Rebuild Container`
3. Verificar se `docker-compose.yml` está válido: `docker compose config`
4. Limpar cache de dev container:
   - `Ctrl+Shift+P` → `Dev Containers: Clean Up Dev Containers`

### Espaço em disco insuficiente

```powershell
# Verificar espaço
Get-PSDrive C | Select-Object Used, Free

# Limpar temporários do projeto
.\scripts\windows\clean-temp.ps1

# Limpar Docker agressivamente (cuidado: remove tudo parado)
docker system prune -f
```

---

## Recuperação de Dados

### Restaurar backup MongoDB

```powershell
# Listar backups disponíveis
.\scripts\windows\restore-mongo.ps1

# Restaurar um específico
.\scripts\windows\restore-mongo.ps1 -BackupName mongo_20260324_120000
```

### Restaurar SQLite

```powershell
# Copiar backup manualmente
Copy-Item data\backup\atlas_local_20260324_120000.db data\atlas_local.db
```

---

## Comandos Úteis

```powershell
# Status dos containers
docker compose ps

# Entrar no container MongoDB
docker exec -it atlas-local-db mongosh

# Entrar no container NestJS
docker exec -it atlas-local-nestjs sh

# Logs em tempo real
docker compose logs -f

# Reconstruir tudo do zero (PERDE DADOS do volume)
docker compose down -v
docker compose up -d --build
```
