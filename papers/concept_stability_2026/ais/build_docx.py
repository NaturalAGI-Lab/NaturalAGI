"""Build the AIS submission .docx from content.py.

Usage:
    .venv/bin/python papers/concept_stability_2026/ais/build_docx.py

Layout follows ../journal_rules/ais_layout.md. Front matter and back matter run full
width; the body runs in two 8.0 cm columns with a 0.5 cm gutter, interrupted by
continuous section breaks wherever a wide figure or table needs the full
measure.

Verification:
    /Applications/LibreOffice.app/Contents/MacOS/soffice --headless \\
        --convert-to pdf --outdir papers/concept_stability_2026/ais \\
        papers/concept_stability_2026/ais/lapin_ais_2026.docx
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import content as C

HERE = Path(__file__).parent
FIGURES = HERE.parent / "figures"
OUT = HERE / "lapin_ais_2026.docx"

FONT = "Times New Roman"
TEXT_WIDTH = Cm(16.51)
COL_WIDTH = Cm(8.0)
COL_GAP_TWIPS = 283  # 0.5 cm

INLINE = re.compile(r"(\*\*.+?\*\*|\*.+?\*|<sub>.+?</sub>|<sup>.+?</sup>)")


# --------------------------------------------------------------------------
# low-level helpers
# --------------------------------------------------------------------------

def _el(tag: str, **attrs) -> OxmlElement:
    node = OxmlElement(tag)
    for key, value in attrs.items():
        node.set(qn(key), value)
    return node


def _set_columns(section, count: int) -> None:
    cols = section._sectPr.xpath("./w:cols")[0]
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), str(COL_GAP_TWIPS))
    cols.set(qn("w:equalWidth"), "1")


def _document_settings(doc: Document) -> None:
    settings = doc.settings.element
    # Justified 8 cm columns look ragged without it; AIS prints hyphenated.
    if not settings.xpath("./w:autoHyphenation"):
        settings.append(_el("w:autoHyphenation", **{"w:val": "true"}))
        settings.append(_el("w:hyphenationZone", **{"w:val": "227"}))
        settings.append(_el("w:doNotHyphenateCaps", **{"w:val": "true"}))


def _style_run(run, size: float, *, bold=False, italic=False, sub=False,
               sup=False, spacing=0) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    if sub:
        run.font.subscript = True
    if sup:
        run.font.superscript = True
    if spacing:
        run._r.get_or_add_rPr().append(
            _el("w:spacing", **{"w:val": str(spacing)}))
    # East-Asian font mapping keeps Cyrillic runs on Times in Word.
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = _el("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)


def add_runs(paragraph, text: str, size: float, *, bold=False,
             italic=False) -> None:
    """Render **bold**, *italic*, <sub>, <sup> markup into runs."""
    for token in INLINE.split(text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            _style_run(paragraph.add_run(token[2:-2]), size, bold=True,
                       italic=italic)
        elif token.startswith("<sub>"):
            _style_run(paragraph.add_run(token[5:-6]), size, bold=bold,
                       italic=italic, sub=True)
        elif token.startswith("<sup>"):
            _style_run(paragraph.add_run(token[5:-6]), size, bold=bold,
                       italic=italic, sup=True)
        elif token.startswith("*") and token.endswith("*"):
            _style_run(paragraph.add_run(token[1:-1]), size, bold=bold,
                       italic=True)
        else:
            _style_run(paragraph.add_run(token), size, bold=bold,
                       italic=italic)


def para(doc: Document, text: str = "", *, size=10.0, align=None, indent=None,
         space_before=0, space_after=0, bold=False, italic=False,
         keep_with_next=False):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    fmt.line_spacing = 1.0
    fmt.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent is not None:
        fmt.first_line_indent = indent
    if keep_with_next:
        fmt.keep_with_next = True
    if text:
        add_runs(p, text, size, bold=bold, italic=italic)
    return p


# AIS letter-spaces the two abstract markers; 1.5 pt of tracking reproduces
# the printed "A b s t r a c t ." without inserting literal spaces.
TRACKING = 30


# --------------------------------------------------------------------------
# page setup
# --------------------------------------------------------------------------

def setup_page(section) -> None:
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.25)
    section.right_margin = Cm(2.25)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.5)


# --------------------------------------------------------------------------
# front matter
# --------------------------------------------------------------------------

def _abstract_block(doc: Document, marker: str, labelled: list, kw_marker: str,
                    keywords: str, space_after: float) -> None:
    abstract = doc.add_paragraph()
    fmt = abstract.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt.left_indent = Cm(0.75)
    fmt.first_line_indent = Cm(0.75)
    fmt.line_spacing = 1.0
    fmt.space_after = Pt(3)
    _style_run(abstract.add_run(marker + " "), 9, spacing=TRACKING)
    for index, (label, text) in enumerate(labelled):
        if index:
            _style_run(abstract.add_run(" "), 9)
        _style_run(abstract.add_run(label + " "), 9, bold=True)
        add_runs(abstract, text, 9)

    kw = doc.add_paragraph()
    kfmt = kw.paragraph_format
    kfmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    kfmt.left_indent = Cm(0.75)
    kfmt.first_line_indent = Cm(0.75)
    kfmt.line_spacing = 1.0
    kfmt.space_after = Pt(space_after)
    _style_run(kw.add_run(kw_marker + " "), 9, bold=True, spacing=TRACKING)
    _style_run(kw.add_run(keywords + "."), 9)


def _title_block(doc: Document, authors: str, affiliations: list,
                 title: str) -> None:
    para(doc, authors, size=11, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
    for affiliation in affiliations:
        para(doc, affiliation, size=11, align=WD_ALIGN_PARAGRAPH.LEFT)
    para(doc, title, size=12, align=WD_ALIGN_PARAGRAPH.CENTER,
         space_before=8, space_after=8, bold=True)


def front_matter(doc: Document) -> None:
    p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=8)
    _style_run(p.add_run(C.UDC), 10)
    _title_block(doc, C.UA_AUTHORS, C.UA_AFFILIATIONS, C.UA_TITLE.upper())
    _abstract_block(doc, "Анотація.", C.UA_ABSTRACT, "Ключові слова:",
                    C.UA_KEYWORDS, 9)
    _title_block(doc, C.AUTHORS, C.AFFILIATIONS, C.TITLE)
    _abstract_block(doc, "Abstract.", C.ABSTRACT, "Keywords:", C.KEYWORDS, 10)


# --------------------------------------------------------------------------
# body blocks
# --------------------------------------------------------------------------

def switch_columns(doc: Document, count: int):
    section = doc.add_section(WD_SECTION.CONTINUOUS)
    setup_page(section)
    _set_columns(section, count)
    return section


def add_figure(doc: Document, filename: str, number: int, caption: str,
               placement: str, scale: float = 1.0) -> None:
    width = int((TEXT_WIDTH if placement == "full" else COL_WIDTH) * scale)
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIGURES / filename), width=width)

    cap = doc.add_paragraph()
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    cap.paragraph_format.line_spacing = 1.0
    cap.paragraph_format.keep_together = True
    _no_hyphen(cap)
    _style_run(cap.add_run(f"Fig. {number}. "), 9)
    add_runs(cap, caption, 9)


def _no_hyphen(paragraph) -> None:
    paragraph._p.get_or_add_pPr().append(
        _el("w:suppressAutoHyphens", **{"w:val": "true"}))


def _shade_header(cell) -> None:
    cell._tc.get_or_add_tcPr().append(
        _el("w:shd", **{"w:val": "clear", "w:fill": "F2F2F2"}))


def _fix_table_width(table, widths_emu: list) -> None:
    """Pin the table to an exact measure.

    Cell widths alone are advisory: Word and LibreOffice both re-run the
    autofit algorithm unless the table declares a fixed layout, its own
    total width, and a grid whose columns match.
    """
    total_dxa = sum(int(w / 635) for w in widths_emu)  # EMU -> twips
    tbl_pr = table._tbl.tblPr
    tbl_pr.append(_el("w:tblLayout", **{"w:type": "fixed"}))
    tbl_pr.append(_el("w:tblW", **{"w:w": str(total_dxa), "w:type": "dxa"}))

    grid = table._tbl.find(qn("w:tblGrid"))
    for column, node in enumerate(grid.findall(qn("w:gridCol"))):
        node.set(qn("w:w"), str(int(widths_emu[column] / 635)))


def add_table(doc: Document, number: int, caption: str, header: list,
              rows: list, placement: str, weights: list, rules: list,
              note: str | None) -> None:
    width = TEXT_WIDTH if placement == "full" else COL_WIDTH
    # Narrow columns break words mid-syllable before they wrap; anything
    # from five columns up needs the smaller size to hold its headers.
    size = 8.0 if (placement == "full" or len(header) >= 5) else 9.0

    cap = doc.add_paragraph()
    cap.paragraph_format.space_before = Pt(6)
    cap.paragraph_format.space_after = Pt(2)
    cap.paragraph_format.line_spacing = 1.0
    cap.paragraph_format.keep_with_next = True
    _no_hyphen(cap)
    _style_run(cap.add_run(f"Table {number}. "), 9)
    add_runs(cap, caption, 9)

    table = doc.add_table(rows=1, cols=len(header))
    table.style = doc.styles["Table Grid"]
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    widths = [int(width.emu * w) for w in weights]
    _fix_table_width(table, widths)
    for index, text in enumerate(header):
        cell = table.rows[0].cells[index]
        cell.width = widths[index]
        _shade_header(cell)
        cp = cell.paragraphs[0]
        cp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.line_spacing = 1.0
        cp.paragraph_format.space_after = Pt(0)
        _no_hyphen(cp)
        add_runs(cp, text, size, bold=True)

    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for index, text in enumerate(row):
            cells[index].width = widths[index]
            cp = cells[index].paragraphs[0]
            cp.paragraph_format.line_spacing = 1.0
            cp.paragraph_format.space_after = Pt(0)
            cp.paragraph_format.alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if index == 0
                else WD_ALIGN_PARAGRAPH.CENTER)
            _no_hyphen(cp)
            add_runs(cp, text, size)
        if row_index in rules:
            _rule_above(table.rows[-1])
    _keep_table_on_one_page(table)

    tail = doc.add_paragraph()
    tail.paragraph_format.space_after = Pt(8)
    tail.paragraph_format.line_spacing = 1.0
    if note:
        _style_run(tail.add_run(note), 8)


def _keep_table_on_one_page(table) -> None:
    """Rows never split, the header repeats, and every row but the last keeps
    with the next, so a short table moves whole instead of breaking."""
    for index, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(_el("w:cantSplit"))
        if index == 0:
            tr_pr.append(_el("w:tblHeader"))
        if index < len(table.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True


def _rule_above(row) -> None:
    """Thicker top border on a row — stands in for LaTeX \\midrule."""
    for cell in row.cells:
        borders = _el("w:tcBorders")
        borders.append(_el("w:top", **{"w:val": "single", "w:sz": "12",
                                       "w:space": "0", "w:color": "000000"}))
        cell._tc.get_or_add_tcPr().append(borders)


def add_equation(doc: Document, text: str, number: str) -> None:
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_before = Pt(4)
    fmt.space_after = Pt(4)
    fmt.line_spacing = 1.0
    fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fmt.tab_stops.add_tab_stop(Cm(4.0), WD_TAB_ALIGNMENT.CENTER)
    fmt.tab_stops.add_tab_stop(COL_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    _style_run(p.add_run("\t"), 10)
    add_runs(p, text, 10)
    _style_run(p.add_run(f"\t({number})"), 10)


def _placement(block) -> str | None:
    if block[0] == "fig":
        return block[4]
    if block[0] == "tbl":
        return block[5]
    return None


def body(doc: Document) -> None:
    columns = 2
    for section_data in C.SECTIONS:
        para(doc, section_data["title"], size=12,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_before=5, space_after=5,
             bold=True, keep_with_next=True)
        blocks = section_data["blocks"]
        for index, block in enumerate(blocks):
            kind = block[0]
            if kind == "p":
                para(doc, block[1], indent=Cm(0.75))
                continue
            if kind == "h2":
                para(doc, block[1], size=10, align=WD_ALIGN_PARAGRAPH.CENTER,
                     space_before=5, space_after=5, bold=True,
                     keep_with_next=True)
                continue
            if kind == "eq":
                add_equation(doc, block[1], block[2])
                continue

            wanted = 1 if _placement(block) == "full" else 2
            if columns != wanted:
                switch_columns(doc, wanted)
                columns = wanted

            if kind == "fig":
                add_figure(doc, *block[1:])
            else:
                number, caption, header, rows, placement, weights = block[1:7]
                note = block[8] if len(block) > 8 else None
                add_table(doc, number, caption, header, rows, placement,
                          weights, block[7], note)

            # A full-width float only borrows the measure for itself; the
            # prose after it belongs back in two columns unless another
            # full-width float follows immediately.
            following = blocks[index + 1] if index + 1 < len(blocks) else None
            if columns == 1 and (following is None
                                 or _placement(following) != "full"):
                switch_columns(doc, 2)
                columns = 2


# --------------------------------------------------------------------------
# back matter
# --------------------------------------------------------------------------

def back_matter(doc: Document) -> None:
    switch_columns(doc, 1)

    for title, text in C.END_SECTIONS:
        p = para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=3)
        _style_run(p.add_run(title + ". "), 10, bold=True)
        add_runs(p, text, 10)

    para(doc, "References", size=12, align=WD_ALIGN_PARAGRAPH.CENTER,
         space_before=5, space_after=5, bold=True, keep_with_next=True)
    for index, reference in enumerate(C.REFERENCES, start=1):
        p = doc.add_paragraph()
        fmt = p.paragraph_format
        fmt.left_indent = Cm(0.6)
        fmt.first_line_indent = Cm(-0.6)
        fmt.line_spacing = 1.0
        fmt.space_after = Pt(0)
        # Left, not justified: DOI URLs are unbreakable, and justifying
        # around them opens rivers of white space.
        fmt.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _no_hyphen(p)
        _style_run(p.add_run(f"{index}. "), 9)
        add_runs(p, reference, 9)

    dates = para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=10)
    _style_run(dates.add_run(f"{C.RECEIVED} __.__.2026"), 9)
    dates2 = para(doc, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=8)
    _style_run(dates2.add_run(f"{C.ACCEPTED} __.__.2026"), 9)

    para(doc, "ВІДОМОСТІ ПРО АВТОРІВ / ABOUT THE AUTHORS", size=9,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4, bold=True,
         keep_with_next=True)
    for author in C.AUTHOR_BLOCK:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _style_run(p.add_run(author["ua_name"] + " – "), 9, bold=True)
        _style_run(p.add_run(author["ua_body"]), 9)
        p2 = doc.add_paragraph()
        p2.paragraph_format.line_spacing = 1.0
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _style_run(p2.add_run(author["en_name"] + " – " + author["en_body"]), 9)
        p3 = doc.add_paragraph()
        p3.paragraph_format.line_spacing = 1.0
        p3.paragraph_format.space_after = Pt(0)
        _style_run(p3.add_run(f"e-mail: {author['email']}; "
                              f"ORCID Author ID: {author['orcid']};"), 9)
        p4 = doc.add_paragraph()
        p4.paragraph_format.line_spacing = 1.0
        p4.paragraph_format.space_after = Pt(8)
        _style_run(p4.add_run(f"Scopus ID: {author['scopus']}."), 9)


# --------------------------------------------------------------------------

def main() -> None:
    doc = Document()
    _document_settings(doc)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_after = Pt(0)

    section = doc.sections[0]
    setup_page(section)
    _set_columns(section, 1)

    front_matter(doc)
    switch_columns(doc, 2)
    body(doc)
    back_matter(doc)

    doc.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
