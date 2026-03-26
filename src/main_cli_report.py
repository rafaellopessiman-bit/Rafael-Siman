from __future__ import annotations

import csv
import io
import json
import zipfile
from argparse import Namespace
from collections import Counter
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from src.core.config import get_settings
from src.storage.document_store import (
    fetch_all_chunks,
    fetch_all_documents,
    fetch_latest_document_audit_decisions,
)

DEFAULT_OUTPUT_FORMAT = "markdown"
DEFAULT_OUTPUT_DIR = Path("data/processados")


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _current_timestamp() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(timespec="seconds")


def _build_report_payload(db_path: str, docs_path: str, output_format: str) -> dict[str, Any]:
    documents = fetch_all_documents(db_path=db_path, base_dir=docs_path)
    chunks = fetch_all_chunks(db_path=db_path, base_dir=docs_path)
    latest_decisions = fetch_latest_document_audit_decisions(db_path=db_path, base_dir=docs_path)

    documents_by_path = {
        str(document.get("file_path", "")): document
        for document in documents
        if str(document.get("file_path", ""))
    }
    decisions_by_path = {
        str(item.get("file_path", "")): item
        for item in latest_decisions
        if str(item.get("file_path", ""))
    }

    all_paths = sorted(set(documents_by_path) | set(decisions_by_path))
    rows: list[dict[str, Any]] = []
    extension_counts: Counter[str] = Counter()
    theme_counts: Counter[str] = Counter()
    latest_action_counts: Counter[str] = Counter()
    latest_source_counts: Counter[str] = Counter()
    latest_flag_counts: Counter[str] = Counter()

    for file_path in all_paths:
        document = documents_by_path.get(file_path, {})
        decision = decisions_by_path.get(file_path, {})
        metadata = document.get("metadata", {}) if isinstance(document.get("metadata"), dict) else {}
        flags = decision.get("flags", []) if isinstance(decision.get("flags"), list) else []
        extension = str(document.get("file_extension") or metadata.get("file_extension") or "")
        theme = str(metadata.get("theme") or "")
        if extension:
            extension_counts[extension] += 1
        if theme:
            theme_counts[theme] += 1
        if decision.get("remediation_action"):
            latest_action_counts[str(decision["remediation_action"])] += 1
        if decision.get("source_command"):
            latest_source_counts[str(decision["source_command"])] += 1
        for flag in flags:
            latest_flag_counts[str(flag)] += 1

        rows.append(
            {
                "file_path": file_path,
                "file_name": str(document.get("file_name") or metadata.get("file_name") or ""),
                "file_extension": extension,
                "indexed": bool(document),
                "updated_at": str(document.get("updated_at") or ""),
                "title": str(metadata.get("title") or ""),
                "author": str(metadata.get("author") or ""),
                "theme": theme,
                "content_length": len(str(document.get("content") or "")),
                "latest_audit_timestamp": str(decision.get("audit_timestamp") or ""),
                "latest_action": str(decision.get("remediation_action") or ""),
                "latest_should_index": bool(decision.get("should_index")) if decision else None,
                "latest_source_command": str(decision.get("source_command") or ""),
                "latest_flags": list(flags),
                "duplicate_of": str(decision.get("duplicate_of") or ""),
            }
        )

    summary = {
        "indexed_documents": len(documents),
        "indexed_chunks": len(chunks),
        "documents_with_history": len(latest_decisions),
        "rows_total": len(rows),
        "latest_action_counts": dict(sorted(latest_action_counts.items())),
        "latest_source_counts": dict(sorted(latest_source_counts.items())),
        "latest_flag_counts": dict(sorted(latest_flag_counts.items())),
        "extension_counts": dict(sorted(extension_counts.items())),
        "theme_counts": dict(sorted(theme_counts.items())),
        "pending_ocr_documents": sum(1 for row in rows if row["latest_action"] == "ocr_required"),
        "review_documents": sum(1 for row in rows if row["latest_action"] == "index_with_review"),
        "isolated_documents": sum(1 for row in rows if row["latest_action"] == "isolate"),
        "duplicate_documents": sum(1 for row in rows if row["latest_action"] == "ignore_duplicate"),
        "indexed_without_history": sum(1 for row in rows if row["indexed"] and not row["latest_action"]),
    }

    return {
        "status": "ok",
        "report": {
            "database_path": db_path,
            "documents_path": str(docs_path),
            "generated_at": _current_timestamp(),
            "output": output_format,
        },
        "summary": summary,
        "documents": rows,
    }


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_csv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "file_path",
            "file_name",
            "file_extension",
            "indexed",
            "updated_at",
            "title",
            "author",
            "theme",
            "content_length",
            "latest_audit_timestamp",
            "latest_action",
            "latest_should_index",
            "latest_source_command",
            "latest_flags",
            "duplicate_of",
        ],
    )
    writer.writeheader()
    for row in payload["documents"]:
        writer.writerow(
            {
                **row,
                "latest_flags": ";".join(row["latest_flags"]),
            }
        )
    return output.getvalue()


def _render_markdown(payload: dict[str, Any]) -> str:
    report = payload["report"]
    summary = payload["summary"]
    rows = payload["documents"]

    lines = [
        "# Atlas Local Report",
        "",
        f"- Banco: {report['database_path']}",
        f"- Origem: {report['documents_path']}",
        f"- Gerado em: {report['generated_at']}",
        f"- Documentos indexados: {summary['indexed_documents']}",
        f"- Chunks indexados: {summary['indexed_chunks']}",
        f"- OCR pendente: {summary['pending_ocr_documents']}",
        f"- Em revisao: {summary['review_documents']}",
        f"- Isolados: {summary['isolated_documents']}",
        f"- Duplicados ignorados: {summary['duplicate_documents']}",
        "",
        "## Latest Actions",
        "",
        "| Action | Total |",
        "| --- | ---: |",
    ]

    for action, total in summary["latest_action_counts"].items():
        lines.append(f"| {action} | {total} |")

    lines.extend(
        [
            "",
            "## Extensions",
            "",
            "| Extension | Total |",
            "| --- | ---: |",
        ]
    )
    for extension, total in summary["extension_counts"].items():
        lines.append(f"| {extension} | {total} |")

    lines.extend(
        [
            "",
            "## Operational Rows",
            "",
            "| File | Ext | Indexed | Action | Flags | Theme |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        flags = ", ".join(row["latest_flags"]) if row["latest_flags"] else ""
        lines.append(
            f"| {row['file_path']} | {row['file_extension']} | {'yes' if row['indexed'] else 'no'} | {row['latest_action']} | {flags} | {row['theme']} |"
        )

    return "\n".join(lines)


def _render_output(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return _render_json(payload)
    if output_format == "csv":
        return _render_csv(payload)
    return _render_markdown(payload)


def _resolve_output_path(
    output_format: str,
    output_path: str | Path | None = None,
    prefix: str = "report",
) -> Path:
    extension = {
        "markdown": ".md",
        "json": ".json",
        "csv": ".csv",
        "xlsx": ".xlsx",
    }[output_format]

    if output_path is not None:
        path = Path(output_path)
        if not path.suffix:
            path = path.with_suffix(extension)
        return path

    timestamp = _current_timestamp().replace(":", "-")
    return DEFAULT_OUTPUT_DIR / f"{prefix}-{timestamp}{extension}"


def _write_xlsx_artifact(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheets = _build_workbook_sheets(payload)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("docProps/app.xml", _app_props_xml(sheets))
        archive.writestr("docProps/core.xml", _core_props_xml(payload["report"]["generated_at"]))
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(sheets))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, sheet in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(sheet))


def _build_workbook_sheets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = payload["summary"]
    rows = payload["documents"]

    def _count_rows(items: dict[str, Any], left_header: str, right_header: str) -> list[list[Any]]:
        result = [[left_header, right_header]]
        result.extend([[key, value] for key, value in items.items()])
        return result

    def _doc_rows(filtered_rows: list[dict[str, Any]]) -> list[list[Any]]:
        result = [[
            "file_path",
            "file_name",
            "file_extension",
            "indexed",
            "updated_at",
            "title",
            "author",
            "theme",
            "content_length",
            "latest_audit_timestamp",
            "latest_action",
            "latest_should_index",
            "latest_source_command",
            "latest_flags",
            "duplicate_of",
        ]]
        for row in filtered_rows:
            result.append([
                row["file_path"],
                row["file_name"],
                row["file_extension"],
                "yes" if row["indexed"] else "no",
                row["updated_at"],
                row["title"],
                row["author"],
                row["theme"],
                row["content_length"],
                row["latest_audit_timestamp"],
                row["latest_action"],
                "yes" if row["latest_should_index"] is True else "no" if row["latest_should_index"] is False else "",
                row["latest_source_command"],
                ", ".join(row["latest_flags"]),
                row["duplicate_of"],
            ])
        return result

    return [
        _build_sheet("Summary", [["metric", "value"], *[[key, value] for key, value in summary.items() if not isinstance(value, dict)]]),
        _build_sheet("LatestActions", _count_rows(summary["latest_action_counts"], "action", "total")),
        _build_sheet("Extensions", _count_rows(summary["extension_counts"], "extension", "total")),
        _build_sheet("Themes", _count_rows(summary["theme_counts"], "theme", "total")),
        _build_sheet("Flags", _count_rows(summary["latest_flag_counts"], "flag", "total")),
        _build_sheet("PendingOCR", _doc_rows([row for row in rows if row["latest_action"] == "ocr_required"])),
        _build_sheet("Review", _doc_rows([row for row in rows if row["latest_action"] == "index_with_review"])),
        _build_sheet("Isolated", _doc_rows([row for row in rows if row["latest_action"] == "isolate"])),
        _build_sheet("Duplicates", _doc_rows([row for row in rows if row["latest_action"] == "ignore_duplicate"])),
        _build_sheet("Documents", _doc_rows(rows)),
    ]


def _build_sheet(name: str, rows: list[list[Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "rows": rows,
        "column_widths": _estimate_column_widths(rows),
        "freeze_header": bool(rows),
        "auto_filter": len(rows) > 1,
    }


def _estimate_column_widths(rows: list[list[Any]]) -> list[float]:
    if not rows:
        return []

    column_count = max(len(row) for row in rows)
    widths: list[float] = []
    for column_index in range(column_count):
        max_length = 0
        for row in rows:
            if column_index >= len(row):
                continue
            value = row[column_index]
            text = "" if value is None else str(value)
            line_length = max((len(part) for part in text.splitlines()), default=0)
            max_length = max(max_length, line_length)
        widths.append(float(min(max(max_length + 2, 10), 60)))
    return widths


def _content_types_xml(sheet_count: int) -> str:
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f'{overrides}'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )


def _app_props_xml(sheets: list[dict[str, Any]]) -> str:
    titles = "".join(f"<vt:lpstr>{escape(sheet['name'])}</vt:lpstr>" for sheet in sheets)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>atlas_local</Application>'
        '<TitlesOfParts><vt:vector size="%d" baseType="lpstr">%s</vt:vector></TitlesOfParts>'
        '</Properties>'
    ) % (len(sheets), titles)


def _core_props_xml(generated_at: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>Atlas Local Report</dc:title>'
        '<dc:creator>atlas_local</dc:creator>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{escape(generated_at)}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{escape(generated_at)}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def _workbook_xml(sheets: list[dict[str, Any]]) -> str:
    sheet_nodes = "".join(
        f'<sheet name="{escape(sheet["name"])}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{sheet_nodes}</sheets>'
        '</workbook>'
    )


def _workbook_rels_xml(sheets: list[dict[str, Any]]) -> str:
    relationships = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index, _sheet in enumerate(sheets, start=1)
    )
    relationships += '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(sheets) + 1)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{relationships}'
        '</Relationships>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills>'
        '<borders count="2"><border/><border><left style="thin"><color auto="1"/></left><right style="thin"><color auto="1"/></right><top style="thin"><color auto="1"/></top><bottom style="thin"><color auto="1"/></bottom></border></borders>'
        '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="3">'
        '<xf xfId="0"/>'
        '<xf xfId="0" fontId="1" fillId="2" borderId="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf xfId="0" borderId="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def _worksheet_xml(sheet: dict[str, Any]) -> str:
    rows = sheet["rows"]
    row_nodes = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_reference = f"{_column_name(column_index)}{row_index}"
            style_id = _style_for_cell(row_index, value)
            cells.append(_cell_xml(cell_reference, value, style_id=style_id))
        row_nodes.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    dimension_xml = _dimension_xml(rows)
    freeze_xml = _sheet_views_xml() if sheet.get("freeze_header") else ""
    cols_xml = _columns_xml(sheet.get("column_widths", []))
    auto_filter_xml = _auto_filter_xml(rows) if sheet.get("auto_filter") else ""

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'{dimension_xml}'
        f'{freeze_xml}'
        f'{cols_xml}'
        f'<sheetData>{"".join(row_nodes)}</sheetData>'
        f'{auto_filter_xml}'
        '</worksheet>'
    )


def _dimension_xml(rows: list[list[Any]]) -> str:
    if not rows:
        return '<dimension ref="A1"/>'
    max_columns = max((len(row) for row in rows), default=1)
    return f'<dimension ref="A1:{_column_name(max_columns)}{len(rows)}"/>'


def _sheet_views_xml() -> str:
    return (
        '<sheetViews>'
        '<sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
        '</sheetView>'
        '</sheetViews>'
    )


def _columns_xml(widths: list[float]) -> str:
    if not widths:
        return ""
    cols = "".join(
        f'<col min="{index}" max="{index}" width="{width:.2f}" bestFit="1" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    return f'<cols>{cols}</cols>'


def _auto_filter_xml(rows: list[list[Any]]) -> str:
    if len(rows) <= 1:
        return ""
    max_columns = max((len(row) for row in rows), default=1)
    return f'<autoFilter ref="A1:{_column_name(max_columns)}{len(rows)}"/>'


def _style_for_cell(row_index: int, value: Any) -> int:
    if row_index == 1:
        return 1
    if isinstance(value, str) and ("\n" in value or len(value) > 24):
        return 2
    return 0


def _cell_xml(cell_reference: str, value: Any, style_id: int = 0) -> str:
    style_attr = f' s="{style_id}"' if style_id else ""
    if value is None:
        return f'<c r="{cell_reference}"{style_attr} t="inlineStr"><is><t></t></is></c>'

    if isinstance(value, bool):
        text = "yes" if value else "no"
        return f'<c r="{cell_reference}"{style_attr} t="inlineStr"><is><t>{escape(text)}</t></is></c>'

    if isinstance(value, (int, float)):
        return f'<c r="{cell_reference}"{style_attr}><v>{value}</v></c>'

    text = str(value)
    preserve = ' xml:space="preserve"' if text != text.strip() else ''
    return f'<c r="{cell_reference}"{style_attr} t="inlineStr"><is><t{preserve}>{escape(text)}</t></is></c>'


def _column_name(index: int) -> str:
    letters = []
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def generate_report_artifact(
    db_path: str,
    docs_path: str,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    output_path: str | Path | None = None,
    prefix: str = "report",
) -> dict[str, Any]:
    payload = _build_report_payload(db_path=db_path, docs_path=docs_path, output_format=output_format)

    if output_format == "xlsx":
        resolved_path = _resolve_output_path(output_format=output_format, output_path=output_path, prefix=prefix)
        _write_xlsx_artifact(payload, resolved_path)
        return {
            "payload": payload,
            "output_format": output_format,
            "output_path": str(resolved_path),
            "written": True,
        }

    content = _render_output(payload, output_format)
    if output_path is not None:
        resolved_path = _resolve_output_path(output_format=output_format, output_path=output_path, prefix=prefix)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content, encoding="utf-8")
        return {
            "payload": payload,
            "output_format": output_format,
            "output_path": str(resolved_path),
            "content": content,
            "written": True,
        }

    return {
        "payload": payload,
        "output_format": output_format,
        "content": content,
        "written": False,
    }


def _handle_report(args: Namespace | None = None) -> str:
    settings = get_settings()
    docs_path = getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada")
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    output_format = getattr(args, "output", None) or DEFAULT_OUTPUT_FORMAT
    output_path = getattr(args, "output_path", None)

    artifact = generate_report_artifact(
        db_path=db_path,
        docs_path=str(docs_path),
        output_format=output_format,
        output_path=output_path,
    )

    if artifact.get("written"):
        return f"Relatorio gerado em: {artifact['output_path']}"

    return str(artifact["content"])
