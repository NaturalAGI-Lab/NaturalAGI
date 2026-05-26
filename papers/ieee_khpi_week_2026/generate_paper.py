"""IEEE KhPI Week 2026 paper generator (.docx).

Usage:
    natural-agi/bin/python papers/ieee_khpi_week_2026/generate_paper.py

What it does:
- Loads the official KhPIWeek_conference_template.docx as a starting point so
  the IEEE conference styles ("paper title", "Author", "Abstract",
  "Keywords", "Heading 1/2", "Body Text") are guaranteed to exist.
- Wipes the example body content from the template, then rebuilds the
  IEEE conference section topology exactly: title (1-col, narrow top margin,
  first-page IEEE header + copyright footer), two 3-col author bands, and a
  2-col body section with template-faithful margins and column gap.
- Writes title, 5 authors, abstract, keywords, the SECTIONS list (each
  Heading-1 section with its paragraphs and optional Heading-2 subsections),
  three numeric tables, the confusion-matrix figure, and numbered
  references — all from content.py.

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
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt

import content as C

HERE = Path(__file__).parent
TEMPLATE = HERE / "journal_rules" / "KhPIWeek_conference_template.docx"
OUT = HERE / "ieee_khpi_week_2026.docx"
FIGURES_DIR = HERE.parent.parent / "experiments" / "run_20260427_144233"

TWIP_EMU = 635

CONF_HEADER = "2026 IEEE 7th KhPI Week on Advanced Technology (KhPIWeek)"
CONF_FOOTER = "979-8-3315-5236-7/26/$31.00 ©2026 IEEE"


def _twips(value: int) -> Emu:
    return Emu(value * TWIP_EMU)


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
    _apply_section_margins(
        span_section, top=1080, right=907, bottom=1440, left=907, header=720, footer=1181
    )
    _add_table(doc, table_data)
    body_section = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_columns(body_section, 2, space_twips=360)
    _apply_section_margins(
        body_section, top=1080, right=907, bottom=1440, left=907, header=720, footer=1181
    )


def _add_author_paragraph(
    doc: Document, author: dict, *, with_column_break: bool = False
) -> None:
    """Render one author block as a centred ``Author``-styled paragraph.

    Layout matches the official KhPIWeek template: name (bold), department,
    organisation, city/country, email — each on its own line via soft breaks.

    When ``with_column_break`` is True, a column break is appended so the
    next author starts at the top of the next column (used to balance
    multi-author rows in a 3-col section without relying on LibreOffice's
    height-balancing heuristics).
    """
    p = doc.add_paragraph()
    try:
        p.style = doc.styles["Author"]
    except KeyError:
        pass
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)

    name_run = p.add_run(author["name"])
    name_run.bold = True
    name_run.add_break()
    p.add_run(author["department"]).add_break()
    p.add_run(author["organisation"]).add_break()
    p.add_run(author["city_country"]).add_break()
    p.add_run(author["email"])

    if with_column_break:
        p.add_run().add_break(WD_BREAK.COLUMN)


def _add_author_row(doc: Document, authors: list[dict], num_cols: int = 3) -> None:
    """Render a single ``num_cols``-col author row, forcing one author per column.

    Rules for the trailing column break after each author:
    - Full row (len == num_cols): break after every author EXCEPT the last,
      otherwise the final break would push content past the section's last
      column and create a page break.
    - Under-filled row (len < num_cols): break after every author, so the
      remaining columns are left empty rather than letting LibreOffice
      height-balance the row and split the trailing author's email across
      the empty columns.
    """
    is_full_row = len(authors) == num_cols
    last_idx = len(authors) - 1
    for idx, author in enumerate(authors):
        skip_break = is_full_row and idx == last_idx
        _add_author_paragraph(doc, author, with_column_break=not skip_break)


def _set_columns(section, num: int, space_twips: int = 720) -> None:
    """Configure ``section`` to render its content in ``num`` columns.

    ``space_twips`` is the inter-column gap in twips (template uses 720 for
    the 3-col author blocks and 360 for the 2-col body).
    """
    sectPr = section._sectPr
    cols = sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sectPr.append(cols)
    if num > 1:
        cols.set(qn("w:num"), str(num))
        cols.set(qn("w:equalWidth"), "1")
    else:
        for attr in (qn("w:num"), qn("w:equalWidth")):
            if attr in cols.attrib:
                del cols.attrib[attr]
    cols.set(qn("w:space"), str(space_twips))


def _apply_section_margins(
    section,
    *,
    top: int,
    right: int,
    bottom: int,
    left: int,
    header: int,
    footer: int,
) -> None:
    """Set every page margin on ``section`` from twip values (template fidelity)."""
    section.top_margin = _twips(top)
    section.right_margin = _twips(right)
    section.bottom_margin = _twips(bottom)
    section.left_margin = _twips(left)
    section.header_distance = _twips(header)
    section.footer_distance = _twips(footer)


def _apply_first_page_header_footer(section, header_text: str, footer_text: str) -> None:
    """Enable first-page header/footer and populate IEEE notice + copyright."""
    section.different_first_page_header_footer = True

    hp = section.first_page_header.paragraphs[0]
    hp.text = header_text
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    fp = section.first_page_footer.paragraphs[0]
    fp.text = footer_text
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER


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
    """Render the References block per template convention.

    The KhPIWeek template uses ``Heading 5`` (unnumbered) for the
    "References" heading and a lowercase ``references`` style (with built-in
    [N] auto-numbering) for the entries. References are NOT a numbered
    Heading 1 section in this template — the section after Conclusion is
    the last numbered section, and References sits below it unnumbered.
    """
    _add_styled(doc, "References", "Heading 5")
    for ref in C.REFERENCES:
        try:
            doc.add_paragraph(ref, style=doc.styles["references"])
        except KeyError:
            doc.add_paragraph(ref, style=doc.styles["Normal"])


def build_document() -> None:
    doc = Document(str(TEMPLATE))
    _clear_body(doc)

    # --- Title (initial section will be re-styled below to 1-col with IEEE
    #     header/footer once the section structure is in place) ---
    _add_styled(doc, C.TITLE, "paper title")

    # --- Authors: first 3-col section (up to 3 authors per row) ---
    first_authors_sec = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_columns(first_authors_sec, 3, space_twips=720)
    _apply_section_margins(
        first_authors_sec, top=450, right=893, bottom=1440, left=893, header=720, footer=720
    )
    _add_author_row(doc, C.AUTHORS[:3])

    # --- Authors: second 3-col section for the remaining authors (row 2) ---
    if len(C.AUTHORS) > 3:
        second_authors_sec = doc.add_section(WD_SECTION.CONTINUOUS)
        _set_columns(second_authors_sec, 3, space_twips=720)
        _apply_section_margins(
            second_authors_sec, top=450, right=893, bottom=1440, left=893, header=720, footer=720
        )
        _add_author_row(doc, C.AUTHORS[3:])

    # --- Body section: 2-col, wider top margin (template section 3) ---
    body_section = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_columns(body_section, 2, space_twips=360)
    _apply_section_margins(
        body_section, top=1080, right=907, bottom=1440, left=907, header=720, footer=1181
    )

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

    # --- Now finalise the title section's properties (it's section 0 once
    #     the author/body sections have been appended). 1-col, narrow top
    #     margin, IEEE first-page header + copyright footer. ---
    title_sec = doc.sections[0]
    _set_columns(title_sec, 1, space_twips=720)
    _apply_section_margins(
        title_sec, top=540, right=893, bottom=1440, left=893, header=255, footer=1020
    )
    _apply_first_page_header_footer(title_sec, CONF_HEADER, CONF_FOOTER)

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
