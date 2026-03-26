# Backup e Restore — Atlas Local

## Estratégia

| Componente | O que é salvo | Onde |
| --- | --- | --- |
| MongoDB | Todas as collections via `mongodump` | `data\backup\mongo_<ts>\` |
| SQLite | Arquivo `atlas_local.db` completo | `data\backup\atlas_local_<ts>.db` |
| Índice local | Pasta `data\indice\` | `data\backup\indice_<ts>\` |

## Fazer Backup

```powershell
.\scripts\windows\backup-mongo.ps1
```

O script:

1. Executa `mongodump` dentro do container MongoDB
2. Copia o dump para `data\backup\mongo_<timestamp>\`
3. Copia `data\atlas_local.db` com timestamp
4. Copia `data\indice\` com timestamp
5. Loga tudo em `logs\maintenance\backup.log`

## Restaurar MongoDB

```powershell
# Listar backups disponíveis
.\scripts\windows\restore-mongo.ps1

# Restaurar um backup específico
.\scripts\windows\restore-mongo.ps1 -BackupName mongo_20260324_120000
```

O script:

1. Lista backups com tamanho
2. Pede confirmação antes de restaurar
3. Copia os dados para o container
4. Executa `mongorestore --drop` (substitui dados atuais)

## Restaurar SQLite

```powershell
# Restauração manual — copiar o arquivo de volta
Copy-Item data\backup\atlas_local_20260324_120000.db data\atlas_local.db -Force
```

## Restaurar Índice

```powershell
# Copiar pasta de índice de volta
Copy-Item data\backup\indice_20260324_120000\* data\indice\ -Recurse -Force
```

## Política de Retenção

Recomendado para uso individual:

- Manter os **3 últimos backups**
- Remover backups com mais de 90 dias

```powershell
# Remover backups antigos (manter últimos 3)
Get-ChildItem data\backup -Directory |
    Sort-Object Name -Descending |
    Select-Object -Skip 3 |
    ForEach-Object {
        Write-Host "Removendo: $($_.Name)" -ForegroundColor Yellow
        Remove-Item $_.FullName -Recurse -Force
    }
```

## Verificação de Integridade

Após restaurar, execute:

```powershell
# 1. Health check geral
.\scripts\windows\health-check.ps1

# 2. Verificar contagem no MongoDB
docker exec atlas-local-db mongosh --eval "
  use atlas_local_db;
  print('knowledge_documents:', db.knowledge_documents.countDocuments());
  print('query_logs:', db.query_logs.countDocuments());
  print('llm_cache:', db.llm_cache.countDocuments());
  print('document_index:', db.document_index.countDocuments());
"

# 3. Verificar SQLite
python -c "
from src.storage.document_store import DocumentStore
store = DocumentStore('data/atlas_local.db')
print(f'Documentos: {store.count_documents()}')
print(f'Chunks: {store.count_chunks()}')
"
```
