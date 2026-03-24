from src.core.schemas import KnowledgeResponse, PlanResponse, TabularResponse


def render_knowledge_response(response: KnowledgeResponse) -> str:
    lines = [
        "=== Atlas Local | Knowledge ===",
        f"Status: {response.status}",
        "",
        "Resposta:",
        response.answer,
    ]

    if response.warnings:
        lines.append("")
        lines.append("Avisos:")
        lines.extend(f"- {warning}" for warning in response.warnings)

    if response.errors:
        lines.append("")
        lines.append("Erros:")
        lines.extend(f"- {error}" for error in response.errors)

    if response.sources:
        lines.append("")
        lines.append("Fontes:")
        for index, source in enumerate(response.sources, start=1):
            lines.extend(
                [
                    f"[{index}] {source.file_name}",
                    f"  Caminho: {source.file_path}",
                    f"  Score: {source.score}",
                    f"  Prévia: {source.content_preview}",
                ]
            )

    return "\n".join(lines)


def render_plan_response(response: PlanResponse) -> str:
    lines = [
        "=== Atlas Local | Planner ===",
        f"Status: {response.status}",
        f"Objetivo: {response.objective}",
        "",
        "Plano:",
    ]

    if response.steps:
        lines.extend(f"{index}. {step}" for index, step in enumerate(response.steps, start=1))
    else:
        lines.append("Nenhum passo foi gerado.")

    if response.warnings:
        lines.append("")
        lines.append("Avisos:")
        lines.extend(f"- {warning}" for warning in response.warnings)

    if response.errors:
        lines.append("")
        lines.append("Erros:")
        lines.extend(f"- {error}" for error in response.errors)

    return "\n".join(lines)


def render_tabular_response(response: TabularResponse) -> str:
    lines = [
        "=== Atlas Local | Tabular ===",
        f"Status: {response.status}",
        f"Pergunta: {response.question}",
        "",
        "Resposta:",
        response.answer,
    ]

    if response.table_schema is not None:
        lines.append("")
        lines.append("Schema local:")
        lines.append(f"Arquivo: {response.table_schema.file_name}")
        lines.append(f"Caminho: {response.table_schema.file_path}")
        lines.append(f"Tabela: {response.table_schema.table_name}")
        for column in response.table_schema.columns:
            lines.append(f"- {column.name} ({column.inferred_type})")

    if response.result is not None:
        lines.append("")
        lines.append("SQL executado:")
        lines.append(response.result.sql)

        lines.append("")
        lines.append(f"Colunas: {', '.join(response.result.columns) if response.result.columns else '(nenhuma)'}")
        lines.append(f"Linhas retornadas: {response.result.row_count}")

        if response.result.truncated:
            lines.append("Saída truncada: sim")

        if response.result.rows:
            lines.append("")
            lines.append("Resultados:")
            for row in response.result.rows:
                lines.append(f"- {row}")

    if response.warnings:
        lines.append("")
        lines.append("Avisos:")
        lines.extend(f"- {warning}" for warning in response.warnings)

    if response.errors:
        lines.append("")
        lines.append("Erros:")
        lines.extend(f"- {error}" for error in response.errors)

    return "\n".join(lines)


def render_error(stage: str, message: str) -> str:
    return "\n".join(
        [
            "=== Atlas Local | Erro ===",
            f"Etapa: {stage}",
            f"Mensagem: {message}",
        ]
    )

