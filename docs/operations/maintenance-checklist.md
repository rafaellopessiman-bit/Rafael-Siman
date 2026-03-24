# Checklist de Manutenção — Atlas Local

## Diário (quando usar o projeto)

- [ ] Verificar se Docker Desktop está rodando
- [ ] Confirmar containers ativos: `docker compose ps`

## Semanal

- [ ] Executar health check
  ```powershell
  .\scripts\windows\health-check.ps1
  ```
- [ ] Verificar espaço em disco (mínimo recomendado: 5 GB livres)
- [ ] Revisar se há documentos novos em `data\entrada\` que precisam de reindexação
  ```powershell
  .\scripts\windows\reindex-docs.ps1
  ```

## Quinzenal

- [ ] Fazer backup
  ```powershell
  .\scripts\windows\backup-mongo.ps1
  ```
- [ ] Limpar temporários e logs antigos
  ```powershell
  .\scripts\windows\clean-temp.ps1
  ```
- [ ] Verificar atualizações do Docker Desktop
- [ ] Verificar se a imagem `mongodb/mongodb-atlas-local` tem atualização:
  ```powershell
  docker pull mongodb/mongodb-atlas-local:latest
  ```

## Mensal

- [ ] Atualizar dependências Python
  ```powershell
  .venv\Scripts\Activate.ps1
  pip install --upgrade -r requirements.txt
  ```
- [ ] Rodar testes completos
  ```powershell
  python -m pytest tests/ -v
  ```
- [ ] Verificar backups antigos (manter últimos 3, remover resto)
  ```powershell
  Get-ChildItem data\backup -Directory |
    Sort-Object Name -Descending |
    Select-Object -Skip 3 |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
  ```
- [ ] Coletar diagnóstico para referência
  ```powershell
  .\scripts\windows\collect-diagnostics.ps1
  ```
- [ ] Fazer `docker system prune -f` para limpar imagens não usadas

## Trimestral

- [ ] Atualizar Node.js para última LTS se disponível
- [ ] Atualizar Python se patch disponível
- [ ] Revisar `.env` — chaves e configurações ainda válidas?
- [ ] Testar restore de backup (em pasta separada)
  ```powershell
  .\scripts\windows\restore-mongo.ps1
  ```
- [ ] Revisar `docker-compose.yml` contra release notes do Atlas Local

## Sinais de Alerta

| Sinal                            | Ação                                           |
|----------------------------------|-------------------------------------------------|
| Health check com FAIL            | Ver troubleshooting.md                          |
| Disco com < 2 GB livres         | Executar clean-temp.ps1 e docker system prune   |
| Container reiniciando em loop    | `docker logs <container> --tail 100`            |
| SQLite > 500 MB                 | Verificar duplicatas, considerar limpeza        |
| Backup > 1 GB total             | Remover backups antigos                         |
| Testes Python falhando           | Verificar venv e dependências                   |
| GROQ_API_KEY expirada           | Renovar em console.groq.com                     |
