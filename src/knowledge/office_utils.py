from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from src.exceptions import AtlasLoadError

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
WORKBOOK_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
CORE_NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
}


def extract_docx_text(file_path: str | Path) -> tuple[str, dict[str, Any]]:
    path = Path(file_path)
    try:
        with zipfile.ZipFile(path) as archive:
            try:
                document_xml = archive.read("word/document.xml")
            except KeyError as exc:
                raise AtlasLoadError(f"DOCX sem conteudo principal: {path}") from exc

            root = ET.fromstring(document_xml)
            paragraphs: list[str] = []
            for paragraph in root.findall(".//w:p", WORD_NS):
                texts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)]
                joined = "".join(texts).strip()
                if joined:
                    paragraphs.append(joined)

            if not paragraphs:
                raise AtlasLoadError(f"DOCX sem texto extraivel: {path}")

            metadata = _extract_core_metadata(archive)
    except zipfile.BadZipFile as exc:
        raise AtlasLoadError(f"Falha ao abrir DOCX {path}: {exc}") from exc

    metadata["source_kind"] = "docx"
    return "\n\n".join(paragraphs), metadata


def extract_xlsx_text(file_path: str | Path) -> tuple[str, dict[str, Any]]:
    path = Path(file_path)
    try:
        with zipfile.ZipFile(path) as archive:
            workbook_xml = archive.read("xl/workbook.xml")
            workbook_root = ET.fromstring(workbook_xml)
            rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relationships = {
                rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
                for rel in rels_root.findall("rel:Relationship", WORKBOOK_NS)
            }
            shared_strings = _read_shared_strings(archive)

            sheets_output: list[str] = []
            sheet_names: list[str] = []
            for sheet in workbook_root.findall("main:sheets/main:sheet", WORKBOOK_NS):
                sheet_name = sheet.attrib.get("name", "Sheet")
                rel_id = sheet.attrib.get(f"{{{WORKBOOK_NS['r']}}}id", "")
                target = relationships.get(rel_id, "")
                if not target:
                    continue
                normalized_target = target.lstrip("/")
                if not normalized_target.startswith("xl/"):
                    normalized_target = f"xl/{normalized_target}"
                rows = _read_sheet_rows(archive, normalized_target, shared_strings)
                if not rows:
                    continue
                sheet_names.append(sheet_name)
                sheets_output.append(f"[Sheet: {sheet_name}]")
                sheets_output.extend(rows)

            if not sheets_output:
                raise AtlasLoadError(f"XLSX sem texto extraivel: {path}")

            metadata = _extract_core_metadata(archive)
            metadata["sheet_names"] = sheet_names
            metadata["sheet_count"] = len(sheet_names)
            metadata["source_kind"] = "xlsx"
    except KeyError as exc:
        raise AtlasLoadError(f"Falha ao ler XLSX {path}: {exc}") from exc
    except zipfile.BadZipFile as exc:
        raise AtlasLoadError(f"Falha ao abrir XLSX {path}: {exc}") from exc

    return "\n".join(sheets_output), metadata


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        shared_xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(shared_xml)
    values: list[str] = []
    for node in root.findall("main:si", WORKBOOK_NS):
        texts = [item.text or "" for item in node.findall(".//main:t", WORKBOOK_NS)]
        values.append("".join(texts))
    return values


def _read_sheet_rows(
    archive: zipfile.ZipFile,
    target: str,
    shared_strings: list[str],
) -> list[str]:
    root = ET.fromstring(archive.read(target))
    rows: list[str] = []
    for row in root.findall("main:sheetData/main:row", WORKBOOK_NS):
        values: list[str] = []
        for cell in row.findall("main:c", WORKBOOK_NS):
            cell_type = cell.attrib.get("t", "")
            value = ""
            if cell_type == "inlineStr":
                value = "".join(item.text or "" for item in cell.findall(".//main:t", WORKBOOK_NS))
            else:
                raw_value = cell.findtext("main:v", default="", namespaces=WORKBOOK_NS)
                if cell_type == "s" and raw_value.isdigit():
                    index = int(raw_value)
                    value = shared_strings[index] if index < len(shared_strings) else raw_value
                else:
                    value = raw_value
            value = value.strip()
            if value:
                values.append(value)
        if values:
            rows.append("\t".join(values))
    return rows


def _extract_core_metadata(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        core_xml = archive.read("docProps/core.xml")
    except KeyError:
        return {}

    root = ET.fromstring(core_xml)
    title = root.findtext("dc:title", default="", namespaces=CORE_NS).strip()
    author = root.findtext("dc:creator", default="", namespaces=CORE_NS).strip()
    return {
        key: value
        for key, value in {"title": title, "author": author}.items()
        if value
    }
