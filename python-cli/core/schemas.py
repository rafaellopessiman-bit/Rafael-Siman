from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(..., description="Nome do arquivo.")
    file_path: str = Field(..., description="Caminho do arquivo.")
    content_preview: str = Field(..., description="Prévia curta do conteúdo.")
    score: float = Field(default=0.0, description="Score do retrieval.")


class KnowledgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Literal["knowledge"] = "knowledge"
    status: Literal["ok", "insufficient_context", "error"] = "ok"
    answer: str = Field(..., description="Resposta final da rota textual.")
    sources: list[SourceDocument] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Literal["planner"] = "planner"
    status: Literal["ok", "error"] = "ok"
    objective: str = Field(..., description="Objetivo informado pelo usuário.")
    steps: list[str] = Field(default_factory=list, description="Plano em passos ordenados.")
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class TableColumnSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Nome da coluna.")
    inferred_type: str = Field(..., description="Tipo inferido localmente para a coluna.")


class TableSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(..., description="Nome do arquivo CSV.")
    file_path: str = Field(..., description="Caminho do arquivo CSV.")
    table_name: str = Field(default="dataset", description="Nome lógico da tabela local.")
    columns: list[TableColumnSchema] = Field(default_factory=list, description="Schema extraído localmente.")


class TabularQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str = Field(..., description="SQL validado e executado localmente.")
    columns: list[str] = Field(default_factory=list, description="Colunas retornadas pela query.")
    rows: list[list[Any]] = Field(default_factory=list, description="Linhas retornadas pela query.")
    row_count: int = Field(default=0, description="Quantidade de linhas retornadas.")
    truncated: bool = Field(default=False, description="Indica se a saída foi truncada.")


class TabularResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Literal["tabular"] = "tabular"
    status: Literal["ok", "blocked", "error"] = "ok"
    question: str = Field(..., description="Pergunta original do usuário.")
    answer: str = Field(..., description="Resposta final da rota tabular.")
    table_schema: TableSchema | None = Field(default=None, description="Schema local extraído do CSV.")
    result: TabularQueryResult | None = Field(default=None, description="Resultado da query tabular.")
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

