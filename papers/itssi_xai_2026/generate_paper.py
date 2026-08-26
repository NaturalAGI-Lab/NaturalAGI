"""ITSSI-2026 (XAI) генератор статті у форматі .docx.

Використання:
    .venv/bin/python papers/itssi_xai_2026/generate_paper.py

Що робить:
- Зчитує content.py (весь змістовний текст + метадані + бібліографію)
- Формує Word-документ згідно з вимогами ITSSI для україномовної подачі:
  * 10pt Times New Roman, line-spacing 1.0
  * A4, поля 2 см
  * EN заголовок/анотація/ключові слова на початку (одразу після УДК
    і рядка автора латиницею), UA — наприкінці, після блока
    "Відомості про авторів". Порядок за ArticleRequirements_UA.pdf
    (18.07.2026), розділ "ФОРМАЛЬНА СТРУКТУРА СТАТТІ", і звірено
    з версткою журналу, випуск 2 (36), с. 70-94.
  * Структурована анотація UA+EN (6 міток)
  * Обов'язкові декларації (UA заголовки) перед References
  * Відомості про автора UA + EN
  * Harvard BSI для джерел (латиниця)

Клоновано з papers/itssi_paper_2026/generate_paper.py (10pt/OMML/margins/
declarations machinery). Відмінності від джерела задокументовані в звіті
побудови (не тут — щоб уникнути дублювання джерела правди).

Таблиці: на відміну від джерела (яке пропускало таблиці), цей генератор
РЕНДЕРИТЬ таблиці з C.TABLES (список словників header/rows), 9pt, по
центру, шапка жирним.

Рисунки: C.FIGURES перелічує файли відносно figures/. Якщо файл
відсутній на диску, замість картинки друкується курсивна позначка —
build не падає (зручно для скелета без реальних рисунків).

Формули:
- Display equations (FORMULAS) і inline math у прозі ($...$) збираються
  через pandoc у нативні Word Office Math (OMML) елементи, як і в
  джерелі. Display формули прив'язуються до абзаців через
  `anchor_paragraph` — вставляються відразу після абзацу, текст якого
  містить цей рядок-маркер.
- Таблиці/рисунки прив'язуються інакше: абзац-маркер `__TABLE__:<id>` /
  `__FIGURE__:<id>` у C.SECTIONS вставляє відповідний об'єкт у цьому
  місці розділу (див. docstring content.py).

Перевірка результату:
    soffice --headless --convert-to pdf --outdir papers/itssi_xai_2026/ \\
        papers/itssi_xai_2026/itssi_xai_2026.docx
    pdfinfo papers/itssi_xai_2026/itssi_xai_2026.pdf | grep Pages
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Cm, Inches, Pt
from lxml import etree

import content as C

OUT = Path(__file__).parent / "itssi_xai_2026.docx"
FIGURES_DIR = Path(__file__).parent / "figures"
FONT = "Times New Roman"
BODY_SIZE_PT = 10
TABLE_SIZE_PT = 9
INDENT_CM = 1.0


# ---------- LaTeX -> OMML cache (pandoc-backed) ----------
# Cloned verbatim from papers/itssi_paper_2026/generate_paper.py: pandoc
# converts $...$ / $$...$$ LaTeX into native Word Office Math (OMML)
# elements once per unique expression; each insertion point deep-copies
# the cached <m:oMath> element.

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_NS = {"w": NS_W, "m": NS_M}

_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\$([^$\n]+?)\$", re.DOTALL)
_ITALIC_RE = re.compile(r"\*(.+?)\*")

_OMATH_CACHE: dict[str, etree._Element] = {}


def _collect_math_expressions(*paragraph_lists: list[str]) -> set[str]:
    found: set[str] = set()
    for paragraphs in paragraph_lists:
        for para in paragraphs:
            for match in _MATH_RE.finditer(para):
                latex = (match.group(1) or match.group(2)).strip()
                if latex:
                    found.add(latex)
    return found


def _build_omml_cache(latex_expressions: set[str]) -> None:
    """Run pandoc once on all expressions, populate _OMATH_CACHE keyed by LaTeX."""
    if not latex_expressions:
        return

    expr_list = sorted(latex_expressions)
    md_lines = [f"MARK_{i} ${expr}$\n" for i, expr in enumerate(expr_list)]
    md_content = "\n".join(md_lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        md_path = tmp / "math.md"
        dx_path = tmp / "math.docx"
        md_path.write_text(md_content, encoding="utf-8")
        subprocess.run(
            [
                "pandoc", str(md_path), "-o", str(dx_path),
                "--from", "markdown+tex_math_dollars+raw_tex",
                "--to", "docx",
            ],
            check=True,
        )
        with zipfile.ZipFile(dx_path) as z:
            doc_xml = z.read("word/document.xml")

    tree = etree.fromstring(doc_xml)
    paragraphs = tree.findall(".//w:body/w:p", _NS)
    mark_re = re.compile(r"MARK_(\d+)")
    t_qn = f"{{{NS_W}}}t"
    for p in paragraphs:
        text = "".join((t.text or "") for t in p.iter(t_qn))
        m = mark_re.search(text)
        if not m:
            continue
        idx = int(m.group(1))
        omath = p.find("m:oMath", _NS)
        if omath is None:
            ompara = p.find("m:oMathPara", _NS)
            if ompara is not None:
                omath = ompara.find("m:oMath", _NS)
        if omath is not None:
            _normalize_math_font_size(omath, half_points=BODY_SIZE_PT * 2)
            _OMATH_CACHE[expr_list[idx]] = omath


def _normalize_math_font_size(omath: etree._Element, *, half_points: int) -> None:
    """Force every <m:r> run inside `omath` to render at `half_points/2` pt."""
    sz_qn = f"{{{NS_W}}}sz"
    sz_cs_qn = f"{{{NS_W}}}szCs"
    rPr_qn = f"{{{NS_W}}}rPr"
    m_r_qn = f"{{{NS_M}}}r"
    m_rPr_qn = f"{{{NS_M}}}rPr"
    m_t_qn = f"{{{NS_M}}}t"
    val = str(half_points)

    for m_r in omath.iter(m_r_qn):
        w_rPr = m_r.find(rPr_qn)
        if w_rPr is None:
            w_rPr = etree.Element(rPr_qn)
            insert_at = 0
            for i, child in enumerate(m_r):
                if child.tag == m_rPr_qn:
                    insert_at = i + 1
                elif child.tag == m_t_qn:
                    insert_at = i
                    break
            m_r.insert(insert_at, w_rPr)
        for child_tag in (sz_qn, sz_cs_qn):
            existing = w_rPr.find(child_tag)
            if existing is None:
                etree.SubElement(w_rPr, child_tag, {f"{{{NS_W}}}val": val})
            else:
                existing.set(f"{{{NS_W}}}val", val)


def _omath_for(latex: str) -> etree._Element | None:
    cached = _OMATH_CACHE.get(latex.strip())
    return deepcopy(cached) if cached is not None else None


# ---------- Низькорівневі помічники ----------

def style_run(
    run,
    *,
    size: int = BODY_SIZE_PT,
    bold: bool = False,
    italic: bool = False,
    superscript: bool = False,
) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.superscript = superscript


def new_paragraph(
    doc,
    *,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    indent_cm: float | None = None,
    space_before: int = 0,
    space_after: int = 0,
):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(14)
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent_cm is not None:
        pf.first_line_indent = Cm(indent_cm)
    return p


def add_text(p, text: str, **style) -> None:
    """Add text to paragraph; expand $...$ markers into inline OMML equations."""
    if "$" not in text:
        run = p.add_run(text)
        style_run(run, **style)
        return

    pos = 0
    for match in _MATH_RE.finditer(text):
        if match.start() > pos:
            run = p.add_run(text[pos:match.start()])
            style_run(run, **style)
        latex = (match.group(1) or match.group(2)).strip()
        omath = _omath_for(latex)
        if omath is not None:
            p._element.append(omath)
        else:
            run = p.add_run(f"${latex}$")
            style_run(run, **style)
        pos = match.end()
    if pos < len(text):
        run = p.add_run(text[pos:])
        style_run(run, **style)


def add_marked_text(p, text: str, **style) -> None:
    """Add text expanding *...* into italic runs (Harvard BSI venue names).

    Delegates each non-italic / italic segment to add_text so $...$ math
    keeps working inside references too.
    """
    pos = 0
    for m in _ITALIC_RE.finditer(text):
        if m.start() > pos:
            add_text(p, text[pos:m.start()], **style)
        add_text(p, m.group(1), **{**style, "italic": True})
        pos = m.end()
    if pos < len(text):
        add_text(p, text[pos:], **style)


def add_line(
    doc,
    text: str,
    *,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    size: int = BODY_SIZE_PT,
    bold: bool = False,
    italic: bool = False,
    indent_cm: float | None = None,
    space_before: int = 0,
    space_after: int = 0,
):
    p = new_paragraph(
        doc,
        align=align,
        indent_cm=indent_cm,
        space_before=space_before,
        space_after=space_after,
    )
    add_text(p, text, size=size, bold=bold, italic=italic)
    return p


def add_blank_line(doc) -> None:
    new_paragraph(doc)


# ---------- Рисунки і таблиці ----------

def _style_cell(cell, text: str, *, bold: bool = False, align=None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.line_spacing = 1.0
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    run = p.add_run(text)
    style_run(run, size=TABLE_SIZE_PT, bold=bold)


def add_table_from_data(
    doc,
    table: dict,
    *,
    col_widths_cm: list[float] | None = None,
    style: str = "Table Grid",
) -> None:
    header = table["header"]
    rows = table["rows"]
    n_cols = len(header)
    if any(not h.strip() for h in header):
        raise ValueError(f"table {table.get('id')!r}: header has an empty cell")
    for row in rows:
        if len(row) != n_cols:
            raise ValueError(
                f"table {table.get('id')!r}: row {row!r} does not match "
                f"header width {n_cols}"
            )

    p = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6)
    add_text(
        p,
        f"Таблиця {table['number']} – {table['caption']}",
        bold=True,
        italic=True,
        size=TABLE_SIZE_PT,
    )

    docx_table = doc.add_table(rows=len(rows) + 1, cols=n_cols)
    try:
        docx_table.style = style
    except KeyError:
        docx_table.style = "Table Grid"
    docx_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    docx_table.autofit = True

    for i, h in enumerate(header):
        _style_cell(docx_table.rows[0].cells[i], h, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    for r_idx, row in enumerate(rows, start=1):
        for c_idx, value in enumerate(row):
            align = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            _style_cell(docx_table.rows[r_idx].cells[c_idx], value, align=align)

    if col_widths_cm and len(col_widths_cm) == n_cols:
        for c_idx, width in enumerate(col_widths_cm):
            for row in docx_table.rows:
                row.cells[c_idx].width = Cm(width)

    add_blank_line(doc)


def add_image(
    doc,
    image_path: Path,
    *,
    width_inches: float = 5.5,
    caption_below: str | None = None,
) -> None:
    p = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(width_inches))
    if caption_below:
        cap = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
        add_text(cap, caption_below, italic=True, size=TABLE_SIZE_PT)


def add_figure_from_data(doc, fig: dict) -> None:
    path = FIGURES_DIR / fig["file"]
    caption = f"Рис. {fig['number']} – {fig['caption']}"
    if path.exists():
        add_image(doc, path, width_inches=fig.get("width_inches", 5.5), caption_below=caption)
    else:
        add_line(
            doc,
            f"[Рисунок відсутній: figures/{fig['file']}]",
            align=WD_ALIGN_PARAGRAPH.CENTER,
            italic=True,
            space_before=6,
        )
        add_line(doc, caption, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, space_after=6)


# ---------- Високорівневі блоки ----------

def setup_document(doc) -> None:
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(BODY_SIZE_PT)

    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)


def add_udc(doc) -> None:
    add_line(doc, f"УДК {C.UDC}", bold=True)


def add_author_short_ua(doc) -> None:
    add_line(doc, f"{C.AUTHOR_UA['surname']} {C.AUTHOR_UA['initials']}", bold=True)


def add_author_short_en(doc) -> None:
    add_line(doc, C.AUTHOR_EN["full_name"], bold=True)


def add_title(doc, title: str) -> None:
    add_line(
        doc,
        title.upper(),
        align=WD_ALIGN_PARAGRAPH.CENTER,
        bold=True,
        space_before=6,
        space_after=6,
    )


def add_structured_abstract(
    doc,
    *,
    label_subject: str,
    label_goal: str,
    label_tasks: str,
    label_methods: str,
    label_results: str,
    label_conclusions: str,
    parts: dict,
) -> None:
    labels = {
        "subject": label_subject,
        "goal": label_goal,
        "tasks": label_tasks,
        "methods": label_methods,
        "results": label_results,
        "conclusions": label_conclusions,
    }
    p = new_paragraph(doc, indent_cm=INDENT_CM)
    for i, (key, label) in enumerate(labels.items()):
        if i:
            add_text(p, " ")
        add_text(p, f"{label}. ", bold=True, italic=True)
        add_text(p, parts[key])


def add_keywords(doc, *, label: str, words: list[str]) -> None:
    p = new_paragraph(doc, indent_cm=INDENT_CM)
    add_text(p, f"{label}: ", bold=True, italic=True)
    add_text(p, "; ".join(words) + ".")


"""Literal in-text citation -> "[N]", N being the entry's position in
C.REFERENCES. ITSSI prints numeric citations and orders References by first
mention (Harvard BSI reference bodies, numeric citation markers); see the
journal's own typeset issue 2(36). Parenthetical citations collapse to the
marker; narrative ones keep the author name and only the year-paren becomes
the marker. Order matters only in that longer literals must precede any
literal they contain.

Generated by renumber_refs.py together with C.REFERENCES — edit the SOURCES
table there, not this tuple."""
CITATION_MARKERS: tuple[tuple[str, str], ...] = (
    (
        "(Elsharkawi et al., 2026; Senior et al., 2025; Gan et al., 2023; Dong et al., 2026)",
        "[15, 16, 23, 24]",
    ),
    (
        "(Forest et al., 2025; Sovatzidi et al., 2026; García-Cuesta et al., 2025)",
        "[9, 10, 11]",
    ),
    (
        "(Piao et al., 2023; Tang et al., 2025; Moscatelli et al., 2026)",
        "[20, 21, 22]",
    ),
    ("(Baniecki and Biecek, 2024; Bello et al., 2025)", "[6, 7]"),
    (
        "(Growing Neural Gas, GNG; Fritzke, 1995)",
        "(Growing Neural Gas, GNG) [37]",
    ),
    ("(García-Cuesta et al., 2025)", "[11]"),
    ("(Rajabi and Etminani, 2024)", "[8]"),
    ("(Douglas and Peucker, 1973)", "[38]"),
    ("(Baniecki and Biecek, 2024)", "[6]"),
    ("García-Cuesta et al. (2025)", "García-Cuesta et al. [11]"),
    ("Baniecki and Biecek (2024)", "Baniecki and Biecek [6]"),
    ("(Elsharkawi et al., 2026)", "[15]"),
    ("(Moscatelli et al., 2026)", "[22]"),
    ("(Lundberg and Lee, 2017)", "[2]"),
    ("Hooshyar and Yang (2024)", "Hooshyar and Yang [4]"),
    ("(Riesen and Bunke, 2009)", "[18]"),
    ("(Lapin and Bokhan, 2025)", "[35]"),
    ("(Sovatzidi et al., 2026)", "[10]"),
    ("Elsharkawi et al. (2026)", "Elsharkawi et al. [15]"),
    ("Moscatelli et al. (2026)", "Moscatelli et al. [22]"),
    ("Riesen and Bunke (2009)", "Riesen and Bunke [18]"),
    ("Sovatzidi et al. (2026)", "Sovatzidi et al. [10]"),
    ("(Ribeiro et al., 2016)", "[1]"),
    ("(Parzhyn et al., 2025)", "[32]"),
    ("(Parzhyn et al., 2022)", "[33]"),
    ("(Zhang and Suen, 1984)", "[36]"),
    ("Chatbri et al. (2016)", "Chatbri et al. [13]"),
    ("(Forest et al., 2025)", "[9]"),
    ("(Senior et al., 2025)", "[16]"),
    ("(Ghader et al., 2026)", "[31]"),
    ("(Snell et al., 2017)", "[25]"),
    ("(Nawaz et al., 2025)", "[30]"),
    ("(LeCun et al., 1998)", "[39]"),
    ("(Bello et al., 2025)", "[7]"),
    ("Forest et al. (2025)", "Forest et al. [9]"),
    ("Senior et al. (2025)", "Senior et al. [16]"),
    ("Ghader et al. (2026)", "Ghader et al. [31]"),
    ("Slack et al. (2020)", "Slack et al. [3]"),
    ("Conte et al. (2004)", "Conte et al. [17]"),
    ("(Finn et al., 2017)", "[26]"),
    ("Bello et al. (2025)", "Bello et al. [7]"),
    ("(Piao et al., 2023)", "[20]"),
    ("(Tang et al., 2025)", "[21]"),
    ("(Dong et al., 2026)", "[24]"),
    ("(Han et al., 2022)", "[12]"),
    ("Shen et al. (2016)", "Shen et al. [14]"),
    ("Wang et al. (2021)", "Wang et al. [19]"),
    ("Lake et al. (2015)", "Lake et al. [27]"),
    ("Piao et al. (2023)", "Piao et al. [20]"),
    ("Tang et al. (2025)", "Tang et al. [21]"),
    ("(Gan et al., 2023)", "[23]"),
    ("Dong et al. (2026)", "Dong et al. [24]"),
    ("Gan et al. (2023)", "Gan et al. [23]"),
    ("(Ji et al., 2026)", "[28]"),
    ("Ji et al. (2026)", "Ji et al. [28]"),
    ("(Parzhyn, 2025)", "[34]"),
    ("(Hinton, 2022)", "[29]"),
    ("Rudin (2019)", "Rudin [5]"),
)

_LEFTOVER_CITATION_RE = re.compile(r"\([^()]{0,120}?\d{4}[a-z]?\)")


def number_citations(text: str) -> str:
    for literal, marker in CITATION_MARKERS:
        text = text.replace(literal, marker)
    return text


def add_section_heading(doc, heading: str) -> None:
    add_line(doc, heading, bold=True, space_before=8, space_after=4)


def render_section(
    doc, heading: str, paragraphs: list[str], used_formulas: set[str],
) -> None:
    """Render one numbered section: heading, then body paragraphs.

    A paragraph equal to "__TABLE__:<id>" / "__FIGURE__:<id>" inserts the
    matching C.TABLES / C.FIGURES entry instead of body text. After every
    plain paragraph, any not-yet-used FORMULAS entry whose
    `anchor_paragraph` substring occurs in that paragraph is inserted as a
    display equation right after it (mirrors the source generator).
    """
    add_section_heading(doc, heading)
    for para in paragraphs:
        if para.startswith("__TABLE__:"):
            table_id = para.split(":", 1)[1]
            table = next(t for t in C.TABLES if t["id"] == table_id)
            add_table_from_data(doc, table)
            continue
        if para.startswith("__FIGURE__:"):
            fig_id = para.split(":", 1)[1]
            fig = next(f for f in C.FIGURES if f["id"] == fig_id)
            add_figure_from_data(doc, fig)
            continue
        if para.startswith("__FORMULA__:"):
            f_id = para.split(":", 1)[1]
            f = next(f for f in C.FORMULAS if f["id"] == f_id)
            add_display_equation(
                doc, latex=f["latex"], number=f["number"], caption=f.get("caption"),
            )
            used_formulas.add(f["id"])
            continue

        numbered = number_citations(para)
        leftover = _LEFTOVER_CITATION_RE.search(numbered)
        if leftover:
            raise SystemExit(
                f"Unmapped in-text citation {leftover.group(0)!r} in: {para[:90]}..."
            )
        add_line(doc, numbered, indent_cm=INDENT_CM)
        for f in C.FORMULAS:
            if f["id"] in used_formulas:
                continue
            if f.get("anchor_paragraph") and f["anchor_paragraph"] in para:
                add_display_equation(
                    doc, latex=f["latex"], number=f["number"], caption=f["caption"],
                )
                used_formulas.add(f["id"])


def add_display_equation(
    doc, latex: str, *, number: int | None = None, caption: str | None = None,
) -> None:
    p = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=4, space_after=4)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.line_spacing = 1.0
    omath = _omath_for(latex)
    if omath is not None:
        ompara = etree.SubElement(p._element, f"{{{NS_M}}}oMathPara")
        ompara.append(omath)
    else:
        cap_text = caption or latex
        add_text(p, f"[TODO MathType: {cap_text}]", italic=True)
    if number is not None:
        from docx.enum.text import WD_TAB_ALIGNMENT
        p.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), WD_TAB_ALIGNMENT.RIGHT)
        run = p.add_run(f"\t({number})")
        style_run(run)


def add_declarations(doc) -> None:
    for heading, body in (
        ("Конфлікт інтересів", C.DECLARATIONS["coi"]),
        ("Фінансування", C.DECLARATIONS["funding"]),
        ("Доступність даних", C.DECLARATIONS["data"]),
        ("Використання інструментів штучного інтелекту", C.DECLARATIONS["ai"]),
    ):
        add_line(doc, heading, bold=True, italic=True, space_before=4)
        add_line(doc, body, indent_cm=INDENT_CM)


def add_references(doc) -> None:
    add_section_heading(doc, "References")
    for number, ref in enumerate(C.REFERENCES, 1):
        p = new_paragraph(doc)
        pf = p.paragraph_format
        pf.left_indent = Cm(INDENT_CM)
        pf.first_line_indent = Cm(-INDENT_CM)
        add_marked_text(p, f"{number}. {ref}")


def add_authors_block(doc) -> None:
    """Bilingual 'About the Authors' block for a single-author paper.

    UA name/info (hanging first line), EN name/info (indented), then one
    shared contact line (e-mail; ORCID; Scopus), sourced from
    AUTHORS_INFO_EN so it is not duplicated between languages.
    """
    add_line(
        doc,
        "Відомості про автора / About the Author",
        align=WD_ALIGN_PARAGRAPH.CENTER,
        italic=True,
        space_before=8,
        space_after=4,
    )

    def _hanging_paragraph():
        p = new_paragraph(doc)
        pf = p.paragraph_format
        pf.left_indent = Cm(INDENT_CM)
        pf.first_line_indent = Cm(-INDENT_CM)
        return p

    def _indented_paragraph():
        p = new_paragraph(doc)
        pf = p.paragraph_format
        pf.left_indent = Cm(INDENT_CM)
        return p

    ua = C.AUTHORS_INFO_UA
    en = C.AUTHORS_INFO_EN
    corresponding_ua = " (автор-кореспондент)" if ua.get("is_corresponding") else ""
    corresponding_en = " (corresponding author)" if en.get("is_corresponding") else ""

    p = _hanging_paragraph()
    add_text(p, f"{ua['full_name']}{corresponding_ua}", bold=True)
    add_text(p, f" – {ua['info_block']}.")

    p = _indented_paragraph()
    add_text(p, f"{en['full_name']}{corresponding_en}", bold=True)
    add_text(p, f" – {en['info_block']};")

    p = _indented_paragraph()
    add_text(p, f"e-mail: {en['email']}; ")
    add_text(p, f"ORCID Author ID: {en['orcid']}; ")
    add_text(p, f"Scopus Author ID: {en['scopus']}.")
    if en.get("phone"):
        p = _indented_paragraph()
        add_text(p, f"моб. {en['phone']}")


# ---------- Основна збірка ----------

def main() -> None:
    doc = Document()
    setup_document(doc)

    section_paragraphs = [paragraphs for _, paragraphs in C.SECTIONS]
    inline_math = _collect_math_expressions(
        *section_paragraphs,
        list(C.ABSTRACT_UA.values()),
        list(C.ABSTRACT_EN.values()),
    )
    display_latex = {f["latex"] for f in C.FORMULAS}
    _build_omml_cache(inline_math | display_latex)

    # --- Header: UDC + Latin author line + EN title + EN abstract + EN keywords.
    # Order per ArticleRequirements_UA.pdf (18.07.2026) "ФОРМАЛЬНА СТРУКТУРА
    # СТАТТІ" and confirmed against the journal's typeset PDF of issue 2(36).
    add_udc(doc)
    add_author_short_en(doc)
    add_title(doc, C.TITLE_EN)

    add_structured_abstract(
        doc,
        label_subject="Subject of study",
        label_goal="Purpose",
        label_tasks="Objectives",
        label_methods="Methods",
        label_results="Results",
        label_conclusions="Conclusions",
        parts=C.ABSTRACT_EN,
    )
    add_keywords(doc, label="Keywords", words=C.KEYWORDS_EN)

    # --- Body sections ---
    used_formulas: set[str] = set()
    for heading, paragraphs in C.SECTIONS:
        render_section(doc, heading, paragraphs, used_formulas)

    # --- Mandatory ITSSI declarations ---
    add_blank_line(doc)
    add_declarations(doc)

    # --- References ---
    add_blank_line(doc)
    add_references(doc)

    # --- Author info (UA + EN) ---
    add_blank_line(doc)
    add_authors_block(doc)

    # --- Trailing UA block: UA title + UA abstract + UA keywords ---
    add_blank_line(doc)
    add_title(doc, C.TITLE_UA)

    add_structured_abstract(
        doc,
        label_subject="Предмет дослідження",
        label_goal="Мета",
        label_tasks="Завдання",
        label_methods="Методи",
        label_results="Результати",
        label_conclusions="Висновки",
        parts=C.ABSTRACT_UA,
    )
    add_keywords(doc, label="Ключові слова", words=C.KEYWORDS_UA)

    doc.save(str(OUT))
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
