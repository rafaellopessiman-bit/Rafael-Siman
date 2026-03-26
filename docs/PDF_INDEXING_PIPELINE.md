# Pipeline de Indexação de PDFs

## Objetivo

Transformar a biblioteca em uma base consultável por IA com:

- extração de texto interno de PDFs
- indexação incremental em SQLite local
- catálogo pesquisável por tema, autor, stack e conceitos
- reaproveitamento do fluxo atual de `ask`

## Fluxo

1. O comando `index` lê a pasta informada.
2. Arquivos `.pdf`, `.txt`, `.md` e `.json` são carregados em paralelo.
3. PDFs passam por extração de texto com `pypdf`.
4. O sistema infere metadados heurísticos:
   - `title`
   - `author`
   - `theme`
   - `stack`
   - `concepts`
   - `page_count`
5. Um cabeçalho de catálogo é prefixado ao texto indexável.
6. O conteúdo é chunkado e persistido no SQLite com FTS5.
7. O fluxo de recuperação atual passa a encontrar tanto conteúdo quanto catálogo.

## Comando recomendado

```powershell
python -m src.main index --path "E:\E-book" --db-path "data\ebooks_catalog.db" --workers 6 --batch-size 25
```

## Rotina operacional no Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\index-ebooks-library.ps1
```

Status da rotina:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\show-ebooks-index-status.ps1
```

Parar processos órfãos da indexação técnica:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\stop-ebooks-index.ps1
```

Estatisticas do catalogo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\show-ebooks-catalog-stats.ps1
```

Pacote padrao de consultas operacionais:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\run-ebooks-queries.ps1
```

Saidas esperadas:

- resumo de inserted, updated, unchanged e skipped
- amostras de erros de ingestao
- contagem de PDFs sem texto extraivel
- sugestao de OCR quando houver perda por PDFs digitalizados
- estatisticas finais do catalogo em `data\ebooks_catalog.db`
- heartbeat periodico com PID, CPU e estado do banco durante execucao
- protecao contra execucoes duplicadas via lock file em `logs\maintenance\ebooks-index.lock.json`
- script de parada controlada para processos órfãos da indexação técnica
- estatisticas on demand por tema, stack, documentos e chunks
- pacote de consultas padrao para arquitetura, banco, rag/agentes e debugging/performance/backend

## Consulta posterior

```powershell
python -m src.main ask "Quais livros cobrem clean architecture, mongodb e rag?" --path "E:\E-book" --db-path "data\ebooks_catalog.db"
python -m src.main ask "Quais documentos da biblioteca falam de debugging e performance em backend?" --path "E:\E-book" --db-path "data\ebooks_catalog.db"
```

## Observações operacionais

- O acervo é quase estável, então a estratégia incremental por hash é suficiente.
- Metadados são heurísticos e baratos; não dependem de chamada a LLM.
- Se a heurística evoluir, rode uma reindexação completa para atualizar o catálogo.
- PDFs digitalizados sem camada de texto continuam fora de cobertura; nesses casos, o próximo passo é OCR.
- A rotina Windows grava log em `logs\maintenance\ebooks-index.log` para auditoria operacional.
