"""IEEE KhPI Week 2026 paper generator (.docx).

Usage:
    natural-agi/bin/python papers/ieee_khpi_week_2026/generate_paper.py

What it does:
- Loads the official KhPIWeek_conference_template.docx as a starting point so
  the IEEE conference styles ("paper title", "Author", "Abstract",
  "Keywords", "Heading 1/2", "Body Text") are guaranteed to exist.
- Wipes the example body content from the template.
- Writes title, 5 authors, abstract, keywords, the SECTIONS list (each
  Heading-1 section with its paragraphs and optional Heading-2 subsections),
  three numeric tables, then numbered references — all from content.py.

What it does NOT do (do these in Word before submission):
- Tables of equations or figures with captions are not auto-inserted; the
  text references "Table I/II/III" and "Fig. 1" but the confusion-matrix
  figure has to be dropped in by hand if you want it in the final PDF.
- Author layout: IEEE template typically lays authors out in 3 columns. The
  script writes 5 paragraphs in "Author" style; visual rearrangement
  (column splits) is done in Word.

Verification:
    /Applications/LibreOffice.app/Contents/MacOS/soffice \\
        --headless --convert-to pdf \\
        --outdir papers/ieee_khpi_week_2026 \\
        papers/ieee_khpi_week_2026/ieee_khpi_week_2026.docx
    /opt/homebrew/bin/pdfinfo papers/ieee_khpi_week_2026/ieee_khpi_week_2026.pdf | grep Pages
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

import content as C

HERE = Path(__file__).parent
TEMPLATE = HERE / "journal_rules" / "KhPIWeek_conference_template.docx"
OUT = HERE / "ieee_khpi_week_2026.docx"
FIGURES_DIR = HERE.parent.parent / "experiments" / "run_20260427_144233"


def _clear_body(doc: Document) -> None:
    """Remove every paragraph and table from the document body.

    Section properties (sectPr) are preserved so the template's column
    layout (single-col title, multi-col body) survives the wipe.
    """
    body = doc.element.body
    for child in list(body):
        if child.tag.endswith("}p") or child.tag.endswith("}tbl"):
            body.remove(child)


def _add_styled(doc: Document, text: str, style_name: str):
    p = doc.add_paragraph(text)
    try:
        p.style = doc.styles[style_name]
    except KeyError:
        # Fall back to Normal if the template lacks the named style — keeps
        # the script from crashing on minor template revisions.
        p.style = doc.styles["Normal"]
    return p


def _add_table(doc: Document, table_data: dict) -> None:
    """Render a numbered table with caption above and a header row."""
    cap_p = doc.add_paragraph(table_data["caption"])
    try:
        cap_p.style = doc.styles["table head"]
    except KeyError:
        cap_p.style = doc.styles["Normal"]
        for run in cap_p.runs:
            run.bold = True

    n_cols = len(table_data["header"])
    n_rows = 1 + len(table_data["rows"])
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    try:
        table.style = doc.styles["Table Grid"]
    except KeyError:
        pass

    for j, h in enumerate(table_data["header"]):
        cell = table.rows[0].cells[j]
        cell.text = h
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.size = Pt(9)

    for i, row in enumerate(table_data["rows"], start=1):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = val
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(9)


def _add_full_width_table(doc: Document, table_data: dict) -> None:
    """Insert a table that spans both body columns (IEEE "table*" pattern).

    Implementation: switch to a single-column continuous section just for the
    table, then switch back to 2-column for the following body text. Each
    table therefore lives in its own 1-col section, sandwiched between 2-col
    body sections. Word renders this with the table spanning the full page
    width and prose flowing in 2 columns above and below.
    """
    span_section = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_columns(span_section, 1)
    _add_table(doc, table_data)
    body_section = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_columns(body_section, 2)


def _add_author_block(doc: Document, author: dict) -> None:
    """One Author-styled paragraph per co-author, four lines each."""
    lines = [
        author["name"],
        author["department"],
        author["organisation"],
        f"{author['city_country']} — {author['email']}",
    ]
    p = doc.add_paragraph("\n".join(lines))
    try:
        p.style = doc.styles["Author"]
    except KeyError:
        p.style = doc.styles["Normal"]


def _set_columns(section, num: int) -> None:
    """Configure ``section`` to render its content in ``num`` columns."""
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    cols.set(qn("w:num"), str(num))
    cols.set(qn("w:equalWidth"), "1")
    cols.set(qn("w:space"), "425")


def _add_figure(doc: Document, image_path: Path, caption: str, width_in: float = 3.2) -> None:
    """Insert a centred figure with an IEEE-style "Fig. N." caption below it."""
    img_p = doc.add_paragraph()
    img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    img_p.add_run().add_picture(str(image_path), width=Inches(width_in))

    cap_p = doc.add_paragraph(caption)
    try:
        cap_p.style = doc.styles["Caption"]
    except KeyError:
        cap_p.style = doc.styles["Normal"]
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _add_references(doc: Document) -> None:
    _add_styled(doc, "References", "Heading 1")
    for i, ref in enumerate(C.REFERENCES, start=1):
        line = f"[{i}] {ref}"
        try:
            p = doc.add_paragraph(line, style=doc.styles["References"])
        except KeyError:
            p = doc.add_paragraph(line, style=doc.styles["Normal"])


def build_document() -> None:
    doc = Document(str(TEMPLATE))
    _clear_body(doc)

    # --- Title ---
    _add_styled(doc, C.TITLE, "paper title")

    # --- Authors ---
    for author in C.AUTHORS:
        _add_author_block(doc, author)

    # --- Abstract ---
    p = doc.add_paragraph()
    try:
        p.style = doc.styles["Abstract"]
    except KeyError:
        p.style = doc.styles["Normal"]
    run = p.add_run("Abstract—")
    run.bold = True
    run.italic = True
    p.add_run(C.ABSTRACT)

    # --- Keywords ---
    p = doc.add_paragraph()
    try:
        p.style = doc.styles["Keywords"]
    except KeyError:
        p.style = doc.styles["Normal"]
    run = p.add_run("Keywords—")
    run.bold = True
    run.italic = True
    p.add_run(", ".join(C.KEYWORDS))

    # --- Section break: switch to 2-column body (IEEE standard) ---
    body_section = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_columns(body_section, 2)

    # --- Sections ---
    confusion_matrix = FIGURES_DIR / "confusion_matrix.png"
    table_inserts = {
        "Experimental Setup": [("table", C.TABLE_DATASET)],
        "Results": [
            ("table", C.TABLE_OVERALL),
            ("table", C.TABLE_PERCLASS),
            (
                "figure",
                confusion_matrix,
                "Fig. 1. Confusion matrix on the complete-only MNIST test set (8 685 classified images).",
            ),
        ],
    }
    for heading, paragraphs in C.SECTIONS:
        _add_styled(doc, heading, "Heading 1")
        last_h2 = None
        for entry in paragraphs:
            if isinstance(entry, tuple) and entry[0] == "__HEADING2__":
                last_h2 = entry[1]
                _add_styled(doc, last_h2, "Heading 2")
                continue
            _add_styled(doc, entry, "Body Text")
            if last_h2 in table_inserts and table_inserts[last_h2]:
                for item in table_inserts.pop(last_h2):
                    if item[0] == "table":
                        _add_full_width_table(doc, item[1])
                    elif item[0] == "figure":
                        _, path, caption = item
                        if path.exists():
                            _add_figure(doc, path, caption)

    # --- References ---
    _add_references(doc)

    doc.save(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build_document()
