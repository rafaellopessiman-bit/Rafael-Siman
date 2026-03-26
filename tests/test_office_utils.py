import zipfile

from src.knowledge.office_utils import extract_docx_text, extract_xlsx_text


def test_extract_docx_text_reads_paragraphs(tmp_path):
    file_path = tmp_path / "sample.docx"
    with zipfile.ZipFile(file_path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                <w:p><w:r><w:t>Primeiro paragrafo</w:t></w:r></w:p>
                <w:p><w:r><w:t>Segundo paragrafo</w:t></w:r></w:p>
              </w:body>
            </w:document>
            """,
        )

    text, metadata = extract_docx_text(file_path)

    assert "Primeiro paragrafo" in text
    assert "Segundo paragrafo" in text
    assert metadata["source_kind"] == "docx"


def test_extract_xlsx_text_reads_sheet_rows(tmp_path):
    file_path = tmp_path / "sample.xlsx"
    with zipfile.ZipFile(file_path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Plan1" sheetId="1" r:id="rId1" />
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="worksheet" />
            </Relationships>
            """,
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <si><t>Nome</t></si>
              <si><t>Atlas</t></si>
            </sst>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="s"><v>0</v></c>
                  <c r="B1" t="s"><v>1</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )

    text, metadata = extract_xlsx_text(file_path)

    assert "[Sheet: Plan1]" in text
    assert "Nome\tAtlas" in text
    assert metadata["source_kind"] == "xlsx"
    assert metadata["sheet_count"] == 1
