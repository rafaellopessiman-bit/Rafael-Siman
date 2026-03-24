import importlib

from src.core.schemas import (
    KnowledgeResponse,
    PlanResponse,
    SourceDocument,
    TableColumnSchema,
    TableSchema,
    TabularQueryResult,
    TabularResponse,
)
from src.main import build_parser


def test_imports_baseline():
    modules_to_check = [
        "src.main",
        "src.exceptions",
        "src.core.config",
        "src.core.llm_client",
        "src.core.output",
        "src.core.prompt_builder",
        "src.core.schemas",
        "src.knowledge.loader",
        "src.knowledge.retriever",
        "src.planner.planner",
        "src.tabular.schema_extractor",
        "src.tabular.sql_generator",
        "src.tabular.sql_validator",
        "src.tabular.executor",
    ]

    for module_name in modules_to_check:
        imported = importlib.import_module(module_name)
        assert imported is not None


def test_cli_parser_subcommands():
    parser = build_parser()

    ask_args = parser.parse_args(["ask", "pergunta de teste"])
    assert ask_args.command == "ask"
    assert ask_args.question == ["pergunta de teste"]

    plan_args = parser.parse_args(["plan", "objetivo de teste"])
    assert plan_args.command == "plan"
    assert plan_args.objective == ["objetivo de teste"]

    table_args = parser.parse_args(
        ["table", ".\\data\\entrada\\dados.csv", "pergunta tabular"]
    )
    assert table_args.command == "table"
    assert table_args.file_path == ".\\data\\entrada\\dados.csv"
    assert table_args.question == ["pergunta tabular"]


def test_core_schema_instantiation():
    source = SourceDocument(
        file_name="teste.txt",
        file_path="data\\entrada\\teste.txt",
        content_preview="conteúdo de teste",
        score=1.5,
    )

    knowledge = KnowledgeResponse(
        answer="Resposta de teste",
        sources=[source],
    )

    plan = PlanResponse(
        objective="Objetivo de teste",
        steps=["Passo 1", "Passo 2"],
    )

    table_schema = TableSchema(
        file_name="dados.csv",
        file_path="data\\entrada\\dados.csv",
        columns=[
            TableColumnSchema(name="produto", inferred_type="TEXT"),
            TableColumnSchema(name="quantidade", inferred_type="INTEGER"),
        ],
    )

    result = TabularQueryResult(
        sql="SELECT SUM(quantidade) FROM dataset",
        columns=["sum(quantidade)"],
        rows=[[10]],
        row_count=1,
        truncated=False,
    )

    tabular = TabularResponse(
        question="Qual é a quantidade total?",
        answer="A consulta retornou 1 linha e 1 coluna. Valor: 10",
        table_schema=table_schema,
        result=result,
    )

    assert knowledge.answer == "Resposta de teste"
    assert knowledge.sources[0].file_name == "teste.txt"
    assert plan.steps == ["Passo 1", "Passo 2"]
    assert tabular.result is not None
    assert tabular.result.row_count == 1
