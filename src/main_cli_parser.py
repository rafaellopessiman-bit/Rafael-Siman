from __future__ import annotations

import argparse

AUDIT_OUTPUT_FORMATS = ("text", "json")
REPORT_OUTPUT_FORMATS = ("json", "csv", "markdown", "xlsx")
WATCH_REMEDIATION_POLICIES = ("manual", "ocr-required", "full-auto")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas_local")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Consultar documentos locais.")
    ask_parser.add_argument("question", nargs="+", help="Pergunta sobre os documentos locais.")
    ask_parser.add_argument("--path", dest="documents_path", help="Caminho da biblioteca consultada.")
    ask_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite consultado.")
    ask_parser.add_argument("--debug", action="store_true", default=False, help="Exibir trace detalhado de ranking.")

    plan_parser = subparsers.add_parser("plan", help="Gerar um plano simples.")
    plan_parser.add_argument("objective", nargs="+", help="Objetivo para o planner.")

    table_parser = subparsers.add_parser("table", help="Consultar um arquivo CSV local.")
    table_parser.add_argument("file_path", help="Caminho do arquivo CSV.")
    table_parser.add_argument("question", nargs="+", help="Pergunta sobre o CSV local.")

    index_parser = subparsers.add_parser("index", help="Indexar documentos no SQLite local.")
    index_parser.add_argument("--path", dest="documents_path", help="Caminho da biblioteca a ser indexada.")
    index_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite de indice.")
    index_parser.add_argument("--workers", type=int, help="Numero de workers para leitura paralela.")
    index_parser.add_argument("--batch-size", type=int, help="Quantidade de arquivos processados por lote durante a indexacao.")
    index_parser.add_argument("--enable-pdf-ocr", action="store_true", help="Habilitar OCR seletivo para PDFs sem texto extraivel.")
    index_parser.add_argument("--pdf-ocr-command", help="Comando externo usado para OCR de PDFs (default: ocrmypdf).")
    index_parser.add_argument("--pdf-ocr-language", help="Idioma(s) do OCR para PDF, no formato esperado pela ferramenta externa.")
    index_parser.add_argument("--enable-image-ocr", action="store_true", help="Habilitar OCR para imagens suportadas.")
    index_parser.add_argument("--image-ocr-command", help="Comando externo usado para OCR de imagens (default: tesseract).")
    index_parser.add_argument("--image-ocr-language", help="Idioma(s) do OCR para imagem, no formato esperado pela ferramenta externa.")
    index_parser.add_argument(
        "--isolate-flags",
        help="Lista CSV de flags que devem isolar documentos em vez de apenas marcar revisao.",
    )

    audit_parser = subparsers.add_parser("audit", help="Auditar qualidade do corpus local e opcionalmente reindexar candidatos automaticamente.")
    audit_parser.add_argument("--path", dest="documents_path", help="Caminho da biblioteca a ser auditada.")
    audit_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite para reindexacao seletiva.")
    audit_parser.add_argument("--workers", type=int, help="Numero de workers para leitura paralela.")
    audit_parser.add_argument("--batch-size", type=int, help="Quantidade de arquivos processados por lote durante a auditoria.")
    audit_parser.add_argument("--enable-pdf-ocr", action="store_true", help="Habilitar OCR seletivo para PDFs sem texto extraivel.")
    audit_parser.add_argument("--pdf-ocr-command", help="Comando externo usado para OCR de PDFs (default: ocrmypdf).")
    audit_parser.add_argument("--pdf-ocr-language", help="Idioma(s) do OCR para PDF, no formato esperado pela ferramenta externa.")
    audit_parser.add_argument("--enable-image-ocr", action="store_true", help="Habilitar OCR para imagens suportadas.")
    audit_parser.add_argument("--image-ocr-command", help="Comando externo usado para OCR de imagens (default: tesseract).")
    audit_parser.add_argument("--image-ocr-language", help="Idioma(s) do OCR para imagem, no formato esperado pela ferramenta externa.")
    audit_parser.add_argument(
        "--similarity-threshold",
        type=float,
        help="Threshold minimo de similaridade para formar clusters de documentos semelhantes.",
    )
    audit_parser.add_argument(
        "--output",
        choices=AUDIT_OUTPUT_FORMATS,
        default="text",
        help="Formato da saida da auditoria (default: text).",
    )
    audit_parser.add_argument(
        "--reindex-selective",
        action="store_true",
        help="Reindexar automaticamente apenas os arquivos sinalizados pela auditoria.",
    )
    audit_parser.add_argument(
        "--isolate-flags",
        help="Lista CSV de flags que devem isolar documentos em vez de apenas marcar revisao.",
    )

    history_parser = subparsers.add_parser("history", help="Consultar historico de qualidade de um documento no SQLite local.")
    history_parser.add_argument("file_path", help="Caminho do documento a consultar no historico.")
    history_parser.add_argument("--path", dest="documents_path", help="Caminho base da biblioteca para normalizacao do documento.")
    history_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite com o historico.")
    history_parser.add_argument("--limit", type=int, default=20, help="Quantidade maxima de eventos retornados (default: 20).")
    history_parser.add_argument("--offset", type=int, default=0, help="Deslocamento para paginacao do historico (default: 0).")
    history_parser.add_argument("--source-command", choices=("audit", "index", "watch"), help="Filtrar historico pela origem do evento.")
    history_parser.add_argument(
        "--action",
        dest="remediation_action",
        choices=("index", "index_with_review", "ignore_duplicate", "isolate", "ocr_required"),
        help="Filtrar historico pela acao de remediacao aplicada.",
    )
    history_parser.add_argument(
        "--output",
        choices=AUDIT_OUTPUT_FORMATS,
        default="text",
        help="Formato da saida do historico (default: text).",
    )

    schedule_history_parser = subparsers.add_parser("history-schedule", help="Consultar historico operacional do schedule persistido no SQLite local.")
    schedule_history_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite com o historico do schedule.")
    schedule_history_parser.add_argument("--limit", type=int, default=20, help="Quantidade maxima de execucoes retornadas (default: 20).")
    schedule_history_parser.add_argument("--offset", type=int, default=0, help="Deslocamento para paginacao do historico do schedule (default: 0).")
    schedule_history_parser.add_argument("--status", choices=("ok", "partial", "error"), help="Filtrar execucoes do schedule por status.")
    schedule_history_parser.add_argument(
        "--output",
        choices=AUDIT_OUTPUT_FORMATS,
        default="text",
        help="Formato da saida do historico do schedule (default: text).",
    )

    report_parser = subparsers.add_parser("report", help="Gerar relatorio operacional do corpus indexado e do historico de auditoria.")
    report_parser.add_argument("--path", dest="documents_path", help="Caminho base da biblioteca para normalizacao dos documentos.")
    report_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite usado para gerar o relatorio.")
    report_parser.add_argument(
        "--output",
        choices=REPORT_OUTPUT_FORMATS,
        default="markdown",
        help="Formato da saida do relatorio (default: markdown).",
    )
    report_parser.add_argument("--output-path", help="Caminho opcional para gravar o artefato do relatorio.")

    schedule_parser = subparsers.add_parser("schedule", help="Executar audit, report e OCR pendente em sequencia para automacao operacional.")
    schedule_parser.add_argument("--path", dest="documents_path", help="Caminho da biblioteca a processar.")
    schedule_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite usado na execucao.")
    schedule_parser.add_argument("--workers", type=int, help="Numero de workers para a etapa de auditoria.")
    schedule_parser.add_argument("--batch-size", type=int, help="Quantidade de arquivos processados por lote na auditoria.")
    schedule_parser.add_argument("--similarity-threshold", type=float, help="Threshold minimo para clusters na auditoria agendada.")
    schedule_parser.add_argument("--isolate-flags", help="Lista CSV de flags que devem isolar documentos na auditoria agendada.")
    schedule_parser.add_argument(
        "--jobs",
        nargs="+",
        choices=("all", "audit", "report", "ocr-pending", "evaluate"),
        default=["all"],
        help="Jobs a executar em sequencia (default: all).",
    )
    schedule_parser.add_argument("--output-dir", help="Diretorio de saida para os artefatos operacionais do runner.")
    schedule_parser.add_argument(
        "--report-output",
        choices=REPORT_OUTPUT_FORMATS,
        default="xlsx",
        help="Formato do artefato de report gerado pelo runner (default: xlsx).",
    )
    schedule_parser.add_argument("--report-output-path", help="Caminho explicito para o artefato de report do runner.")
    schedule_parser.add_argument("--audit-output-path", help="Caminho explicito para o JSON de auditoria do runner.")
    schedule_parser.add_argument("--pdf-ocr-command", help="Comando externo usado para OCR dos PDFs pendentes (default: ocrmypdf).")
    schedule_parser.add_argument("--pdf-ocr-language", help="Idioma(s) do OCR para PDFs pendentes.")
    schedule_parser.add_argument("--ocr-in-place", action="store_true", help="Sobrescrever o PDF original ao executar OCR pendente.")
    schedule_parser.add_argument(
        "--reindex-after-ocr",
        action="store_true",
        help="Reindexar automaticamente os artefatos OCR gerados para fechar o ciclo operacional.",
    )
    schedule_parser.add_argument("--notify-webhook-url", help="Webhook opcional para receber o resumo consolidado do schedule.")
    schedule_parser.add_argument(
        "--notify-on",
        choices=("always", "on-error", "on-issues", "never"),
        help="Quando enviar notificacao do schedule (default via config: on-issues).",
    )
    schedule_parser.add_argument(
        "--notify-timeout-seconds",
        type=int,
        help="Timeout da notificacao webhook em segundos.",
    )
    schedule_parser.add_argument(
        "--notify-format",
        choices=("raw", "teams", "slack"),
        help="Formato do payload enviado ao webhook.",
    )
    schedule_parser.add_argument("--eval-queries", dest="eval_queries_path", help="JSON com queries de benchmark para o job evaluate.")
    schedule_parser.add_argument("--eval-baseline", dest="eval_baseline_path", help="Baseline usado na comparacao automatica do evaluate.")
    schedule_parser.add_argument("--eval-top-k", type=int, help="Top-K usado pelo job evaluate.")
    schedule_parser.add_argument(
        "--critical-regression-exit-code",
        type=int,
        default=2,
        help="Exit code usado quando o evaluate detecta regressao critica (default: 2).",
    )

    watch_parser = subparsers.add_parser("watch", help="Monitorar a biblioteca local e indexar apenas arquivos novos ou alterados com remediacao automatica.")
    watch_parser.add_argument("--path", dest="documents_path", help="Caminho da biblioteca a monitorar.")
    watch_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite usado na indexacao incremental.")
    watch_parser.add_argument("--workers", type=int, help="Numero de workers para leitura dos arquivos alterados.")
    watch_parser.add_argument("--batch-size", type=int, help="Quantidade de arquivos alterados processados por lote.")
    watch_parser.add_argument("--interval-seconds", type=int, help="Intervalo entre scans do watch mode em segundos.")
    watch_parser.add_argument("--max-cycles", type=int, help="Quantidade maxima de ciclos antes de encerrar o watch mode.")
    watch_parser.add_argument(
        "--remediation-policy",
        choices=WATCH_REMEDIATION_POLICIES,
        help="Politica automatica de remediacao aplicada a arquivos alterados (default via config: full-auto).",
    )
    watch_parser.add_argument("--enable-pdf-ocr", action="store_true", help="Habilitar OCR seletivo ja no primeiro carregamento de PDFs alterados.")
    watch_parser.add_argument("--pdf-ocr-command", help="Comando externo usado para OCR de PDFs (default: ocrmypdf).")
    watch_parser.add_argument("--pdf-ocr-language", help="Idioma(s) do OCR para PDF, no formato esperado pela ferramenta externa.")
    watch_parser.add_argument("--enable-image-ocr", action="store_true", help="Habilitar OCR ja no primeiro carregamento de imagens alteradas.")
    watch_parser.add_argument("--image-ocr-command", help="Comando externo usado para OCR de imagens (default: tesseract).")
    watch_parser.add_argument("--image-ocr-language", help="Idioma(s) do OCR para imagem, no formato esperado pela ferramenta externa.")
    watch_parser.add_argument(
        "--isolate-flags",
        help="Lista CSV de flags que devem isolar documentos durante a remediacao automatica do watch mode.",
    )

    eval_parser = subparsers.add_parser("evaluate", help="Avaliar qualidade do retrieval com metricas IR.")
    eval_parser.add_argument("--db-path", dest="database_path", help="Caminho do banco SQLite a avaliar.")
    eval_parser.add_argument("--queries", dest="eval_queries_path", default="data/eval_queries.json", help="JSON com queries de benchmark.")
    eval_parser.add_argument("--save-baseline", action="store_true", help="Salvar resultado como baseline para deteccao de regressao.")
    eval_parser.add_argument("--baseline", dest="baseline_path", default="data/eval_baseline.json", help="Caminho do baseline para comparacao.")
    eval_parser.add_argument("--top-k", type=int, default=5, help="Numero de resultados por query (default: 5).")

    return parser
