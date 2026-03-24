import csv
from pathlib import Path

from src.core.schemas import TableColumnSchema, TableSchema
from src.exceptions import AtlasLoadError


def extract_table_schema(file_path: str | Path) -> TableSchema:
    csv_path = Path(file_path)

    if not csv_path.exists():
        raise AtlasLoadError(f"Arquivo CSV não encontrado: {csv_path}")

    if not csv_path.is_file():
        raise AtlasLoadError(f"O caminho informado não é um arquivo CSV: {csv_path}")

    if csv_path.suffix.lower() != ".csv":
        raise AtlasLoadError(f"Extensão inválida para rota tabular: {csv_path.name}")

    raw_content = csv_path.read_text(encoding="utf-8-sig").strip()
    if not raw_content:
        raise AtlasLoadError(f"Arquivo CSV vazio: {csv_path}")

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            rows = [dict(row) for row in reader]
            fieldnames = reader.fieldnames
    except Exception as exc:
        raise AtlasLoadError(f"Falha ao ler CSV {csv_path}: {exc}") from exc

    if not fieldnames:
        raise AtlasLoadError(f"CSV sem cabeçalho válido: {csv_path}")

    if not rows:
        raise AtlasLoadError(f"CSV sem linhas de dados: {csv_path}")

    columns = [
        TableColumnSchema(
            name=column_name,
            inferred_type=_infer_column_type(rows, column_name),
        )
        for column_name in fieldnames
    ]

    return TableSchema(
        file_name=csv_path.name,
        file_path=str(csv_path),
        table_name="dataset",
        columns=columns,
    )


def _infer_column_type(rows: list[dict[str, str]], column_name: str) -> str:
    values = [str(row.get(column_name, "")).strip() for row in rows]
    non_empty_values = [value for value in values if value]

    if not non_empty_values:
        return "TEXT"

    if all(_is_int(value) for value in non_empty_values):
        return "INTEGER"

    if all(_is_float(value) for value in non_empty_values):
        return "DOUBLE"

    if all(_is_bool(value) for value in non_empty_values):
        return "BOOLEAN"

    return "TEXT"


def _is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_bool(value: str) -> bool:
    return value.lower() in {"true", "false", "1", "0", "yes", "no"}
