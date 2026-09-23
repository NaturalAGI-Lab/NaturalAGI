"""ITSSI-2026 генератор статті у форматі .docx.

Використання:
    .venv/bin/python papers/itssi_paper_2026/generate_paper.py

Що робить:
- Зчитує content.py (весь змістовний текст + метадані + бібліографію)
- Формує Word-документ згідно з вимогами ITSSI:
  * 10pt Times New Roman, line-spacing 1.0
  * A4, поля 2 см (стандарт, не суперечить вимогам)
  * Лапки " " (текст редагований вручну)
  * Структурована анотація UA+EN (6 міток)
  * Обов'язкові декларації перед references
  * Відомості про авторів UA + EN
  * Harvard BSI для джерел

Чого НЕ робить (робити вручну в Word перед подачею):
- Не генерує таблиці — вони дрібні, але унікальні для кожної версії; краще
  створити їх у Word вручну (Insert → Table), щоб контролювати ширину колонок.

Формули:
- Display equations (FORMULAS) і inline math у прозі ($...$) збираються
  через pandoc у нативні Word Office Math (OMML) елементи. У Word після
  відкриття файлу: MathType → Convert Equations → Equations to MathType
  equations конвертує всі формули у MathType-об'єкти разом.
- Display формули прив'язуються до абзаців через `anchor_paragraph` —
  display equation вставляється відразу після абзацу, текст якого містить
  цей рядок-маркер.

Перевірка результату:
    soffice --headless --convert-to pdf --outdir papers/itssi_paper_2026/ \\
        papers/itssi_paper_2026/itssi_paper_2026.docx
    pdfinfo papers/itssi_paper_2026/itssi_paper_2026.pdf | grep Pages
"""
from __future__ import annotations

import csv
import re
import subprocess
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Cm, Inches, Pt
from lxml import etree

import content as C

OUT = Path(__file__).parent / "itssi_paper_2026.docx"
FIGURES_DIR = Path(__file__).parent / "figures"
FONT = "Times New Roman"
BODY_SIZE_PT = 10
TABLE_SIZE_PT = 9
INDENT_CM = 1.0


# ---------- LaTeX → OMML cache (pandoc-backed) ----------
# Pandoc converts $...$ inline math and $$...$$ display math into native Word
# Office Math (OMML) elements. We run pandoc once on every unique LaTeX
# expression in the corpus, cache the resulting <m:oMath> element, and
# deep-copy it at every insertion point. MathType's "Convert Equations"
# command in Word recognises these as native equations.

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_NS = {"w": NS_W, "m": NS_M}

# Matches $$...$$ (display) before $...$ (inline) so display markers win.
_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\$([^$\n]+?)\$", re.DOTALL)

_OMATH_CACHE: dict[str, etree._Element] = {}


def _collect_math_expressions(*paragraph_lists: list[str]) -> set[str]:
    """Walk every paragraph string and collect unique LaTeX math substrings."""
    found: set[str] = set()
    for paragraphs in paragraph_lists:
        for para in paragraphs:
            for match in _MATH_RE.finditer(para):
                latex = (match.group(1) or match.group(2)).strip()
                if latex:
                    found.add(latex)
    return found


def _build_omml_cache(latex_expressions: set[str]) -> None:
    """Run pandoc once on all expressions, populate _OMATH_CACHE keyed by LaTeX.

    Each expression is wrapped in $...$ so pandoc emits an inline <m:oMath>
    element. The same element renders correctly inline (appended to a text
    paragraph) and as display math (wrapped in <m:oMathPara>).
    """
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
    """Force every <m:r> run inside `omath` to render at `half_points/2` pt.

    Without this, pandoc-emitted math runs carry no <w:rPr> and inherit the
    docDefaults size (11 pt in python-docx's base template) — which makes
    inline equations taller than the surrounding 10 pt body text and
    silently expands line height. We inject (or update) a <w:rPr> child of
    every <m:r> setting both <w:sz> and <w:szCs> to match the body font.
    """
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
            # OMML schema order: m:rPr, then w:rPr, then m:t — insert w:rPr
            # before m:t (and after m:rPr if it exists).
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
    """Return a fresh deepcopy of the cached <m:oMath> element, or None."""
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
    """Add text to paragraph; expand $...$ markers into inline OMML equations.

    Substrings between $-delimiters are looked up in _OMATH_CACHE and
    appended as <m:oMath> elements alongside regular text runs. Unknown
    expressions fall back to literal text so a missing-cache build still
    produces readable output.
    """
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


def add_display_equation(
    doc, latex: str, *, number: int | None = None, caption: str | None = None,
) -> None:
    """Insert a centered display equation as an OMML <m:oMathPara>.

    If `number` is given, append a tab-separated (N) at the right.
    If the LaTeX is not in the cache, fall back to a TODO placeholder.
    """
    p = new_paragraph(
        doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=4, space_after=4,
    )
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
        run = p.add_run(f"\t\t({number})")
        style_run(run)


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


def add_table_from_csv(
    doc,
    csv_path: Path,
    *,
    headers: list[str] | None = None,
    caption_above: str | None = None,
    caption_below: str | None = None,
    col_widths_cm: list[float] | None = None,
    style: str = "Light Grid Accent 1",
) -> None:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    csv_headers = rows[0]
    body_rows = rows[1:]
    table_headers = headers if headers is not None else csv_headers
    n_cols = len(table_headers)

    if caption_above:
        p = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6)
        add_text(p, caption_above, bold=True, italic=True, size=TABLE_SIZE_PT)

    table = doc.add_table(rows=len(body_rows) + 1, cols=n_cols)
    try:
        table.style = style
    except KeyError:
        table.style = "Table Grid"
    table.autofit = True

    for i, header in enumerate(table_headers):
        _style_cell(
            table.rows[0].cells[i],
            header,
            bold=True,
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )

    for r_idx, row in enumerate(body_rows, start=1):
        for c_idx in range(n_cols):
            value = row[c_idx] if c_idx < len(row) else ""
            align = (
                WD_ALIGN_PARAGRAPH.LEFT
                if c_idx == 0
                else WD_ALIGN_PARAGRAPH.CENTER
            )
            _style_cell(table.rows[r_idx].cells[c_idx], value, align=align)

    if col_widths_cm and len(col_widths_cm) == n_cols:
        for c_idx, width in enumerate(col_widths_cm):
            for row in table.rows:
                row.cells[c_idx].width = Cm(width)

    if caption_below:
        p = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
        add_text(p, caption_below, italic=True, size=TABLE_SIZE_PT)


def add_image(
    doc,
    image_path: Path,
    *,
    width_inches: float = 5.5,
    caption_below: str | None = None,
    align_center: bool = True,
) -> None:
    p = new_paragraph(
        doc,
        align=(
            WD_ALIGN_PARAGRAPH.CENTER
            if align_center
            else WD_ALIGN_PARAGRAPH.LEFT
        ),
        space_before=6,
    )
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(width_inches))
    if caption_below:
        cap = new_paragraph(
            doc,
            align=WD_ALIGN_PARAGRAPH.CENTER,
            space_after=6,
        )
        add_text(cap, caption_below, italic=True, size=TABLE_SIZE_PT)


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


def add_authors_short(doc) -> None:
    """Authors line under the UDC. EN primary body uses 'First Last, ...' Latin form."""
    names = ", ".join(a["full_name_en"] for a in C.AUTHORS)
    add_line(doc, names, bold=True)


def add_authors_short_ua(doc) -> None:
    """UA appendix: 'Прізвище І. Б., ...' for the trailing UA tail block."""
    names = ", ".join(
        f"{a['surname_ua']} {a['initials_ua']}" for a in C.AUTHORS
    )
    add_line(doc, names, bold=True)


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
    """Структурована анотація: кожна частина — окремий абзац з bold-міткою."""
    labels = {
        "subject": label_subject,
        "goal": label_goal,
        "tasks": label_tasks,
        "methods": label_methods,
        "results": label_results,
        "conclusions": label_conclusions,
    }
    for key, label in labels.items():
        p = new_paragraph(doc, indent_cm=INDENT_CM)
        add_text(p, f"{label}. ", bold=True, italic=True)
        add_text(p, parts[key])


def add_keywords(doc, *, label: str, words: list[str]) -> None:
    p = new_paragraph(doc, indent_cm=INDENT_CM)
    add_text(p, f"{label}: ", bold=True, italic=True)
    add_text(p, "; ".join(words) + ".")


def add_section_heading(doc, heading: str) -> None:
    add_line(
        doc,
        heading,
        bold=True,
        space_before=8,
        space_after=4,
    )


def add_section(doc, heading: str, paragraphs: list[str]) -> None:
    add_section_heading(doc, heading)
    for para in paragraphs:
        add_line(doc, para, indent_cm=INDENT_CM)


# Subsection prefix at start of paragraph: "Subsection 4.1.1 (Title). body…"
_SUBSECTION_RE = re.compile(
    r"^Subsection\s+(\d+\.\d+(?:\.\d+)?)\s*\(([^)]+)\)\.\s*"
)
# Theorem/Definition/Corollary/Axiom announcement (with parentheses or colon)
# preceded by start-of-paragraph or sentence boundary ". ".
# References like "by Theorem 1," or "of Theorem 2." (no parens / no colon)
# are intentionally NOT matched.
_CALLOUT_RE = re.compile(
    r"(?:^|(?<=\. ))"
    r"(?:Theorem|Definition|Corollary|Axiom)\s+\d+"
    r"(?:\s*\([^)]+\)(?:\s*[\.:])?|\s*:)"
)


def _add_paragraph_with_callouts(
    doc, text: str, *, indent_cm: float | None = None,
) -> None:
    """Render one paragraph; bold theorem-style announcement labels inline."""
    p = new_paragraph(doc, indent_cm=indent_cm)
    pos = 0
    for m in _CALLOUT_RE.finditer(text):
        if m.start() > pos:
            add_text(p, text[pos:m.start()])
        add_text(p, m.group(0), bold=True)
        pos = m.end()
    if pos < len(text):
        add_text(p, text[pos:])


def _render_paragraph_smart(doc, text: str) -> None:
    """Render a body paragraph: extract Subsection-prefix as a heading,
    and bold theorem/definition/corollary/axiom announcements inline."""
    m = _SUBSECTION_RE.match(text)
    if m:
        section_num, title = m.group(1), m.group(2)
        body = text[m.end():]
        add_line(
            doc,
            f"{section_num}. {title}",
            bold=True,
            space_before=6,
            space_after=2,
        )
        if body.strip():
            _add_paragraph_with_callouts(doc, body, indent_cm=INDENT_CM)
        return
    _add_paragraph_with_callouts(doc, text, indent_cm=INDENT_CM)


def render_with_anchored_formulas(
    doc, paragraphs: list[str], formulas: list[dict],
    used: set[str],
) -> None:
    """Render paragraphs; after any paragraph whose text contains a formula's
    `anchor_paragraph` substring, insert a display equation for that formula.

    `used` tracks which formula IDs have already been emitted so the same
    formula is never inserted twice across multiple sections.
    """
    for para in paragraphs:
        _render_paragraph_smart(doc, para)
        for f in formulas:
            if f["id"] in used:
                continue
            if f["anchor_paragraph"] in para:
                add_display_equation(
                    doc,
                    latex=f["latex"],
                    number=f["number"],
                    caption=f["caption"],
                )
                used.add(f["id"])


def add_figure_placeholder(doc, *, number: int, caption: str) -> None:
    """Placeholder під рисунок. Замінити на Insert → Pictures."""
    add_line(
        doc,
        f"[Рисунок {number}: {caption}]",
        align=WD_ALIGN_PARAGRAPH.CENTER,
        italic=True,
        space_before=6,
    )
    add_line(
        doc,
        f"Рис. {number}. {caption}",
        align=WD_ALIGN_PARAGRAPH.CENTER,
        italic=True,
        space_after=6,
    )


def add_declarations(doc) -> None:
    for heading, body in (
        ("Conflict of interest", C.DECLARATION_COI),
        ("Funding", C.DECLARATION_FUNDING),
        ("Data availability", C.DECLARATION_DATA),
        ("Use of artificial intelligence tools", C.DECLARATION_AI),
    ):
        add_line(doc, heading, bold=True, italic=True, space_before=4)
        add_line(doc, body, indent_cm=INDENT_CM)


def format_reference(ref: dict, idx: int) -> tuple[str, str, str]:
    """Одна Harvard-BSI стаття, розбита на 3 сегменти:
    (prefix, italic_venue, suffix). Italic — тільки назва журналу/праць.

    Harvard BSI per ITSSI guidelines starts each entry with the surname,
    not a numeric prefix (cf. journal_rules/author_guidelines.md sample).
    `idx` is kept as a parameter for backwards compatibility but unused.
    """
    del idx  # Unused — Harvard BSI entries are not numerically prefixed.
    authors = ref["authors"]
    year = ref["year"]
    title = ref["title"]
    venue = ref["venue"]
    vol = ref.get("volume")
    issue = ref.get("issue")
    pages = ref.get("pages")
    doi = ref.get("doi")

    prefix = f"{authors} ({year}), \"{title}\", "
    italic = venue

    tail_parts: list[str] = []
    if vol and issue:
        tail_parts.append(f", Vol. {vol}, No. {issue}")
    elif vol:
        tail_parts.append(f", Vol. {vol}")
    if pages:
        tail_parts.append(f", pp. {pages}")
    if doi:
        tail_parts.append(f". DOI: {doi}")
    elif ref.get("url"):
        tail_parts.append(f". Available at: {ref['url']}")
    suffix = "".join(tail_parts) + "."
    return prefix, italic, suffix


def add_references(doc) -> None:
    add_section_heading(doc, "References")
    for idx, ref in enumerate(C.REFERENCES, start=1):
        prefix, italic, suffix = format_reference(ref, idx)
        p = new_paragraph(doc, indent_cm=INDENT_CM)
        add_text(p, prefix)
        add_text(p, italic, italic=True)
        add_text(p, suffix)


def add_authors_block(doc) -> None:
    """Bilingual 'About the Authors' block in the ITSSI sample format.

    One italic centered heading combining UA + EN labels, followed by one
    block per author with three paragraphs in a hanging-indent layout
    (first line flush at the left margin, continuation lines indented):
      (1) bold UA name, en-dash, UA degree / position / affiliation. Period.
      (2) bold EN name, en-dash, EN degree / position / affiliation. Semicolon.
      (3) e-mail; ORCID Author ID: <URL>; Scopus Author ID: <URL>. Period.
    Blocks are separated by an empty paragraph for clear visual grouping.
    """
    add_line(
        doc,
        "Відомості про авторів / About the Authors",
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

    for idx, a in enumerate(C.AUTHORS):
        if idx > 0:
            add_blank_line(doc)

        corresponding_tag_ua = (
            " (автор-кореспондент)" if a.get("is_corresponding") else ""
        )
        if a.get("info_block_ua"):
            ua_body = a["info_block_ua"]
        else:
            ua_body = (
                f"{a['degree_ua']}, {a['position_ua']}, {a['org_ua']}, "
                f"{a['city_ua']}, {a['country_ua']}"
            )
        p = _hanging_paragraph()
        add_text(p, f"{a['full_name_ua']}{corresponding_tag_ua}", bold=True)
        add_text(p, f" – {ua_body}.")

        corresponding_tag_en = (
            " (corresponding author)" if a.get("is_corresponding") else ""
        )
        if a.get("info_block_en"):
            en_body = a["info_block_en"]
        else:
            en_body = (
                f"{a['degree_en']}, {a['position_en']}, {a['org_en']}, "
                f"{a['city_en']}, {a['country_en']}"
            )
        p = _indented_paragraph()
        add_text(p, f"{a['full_name_en']}{corresponding_tag_en}", bold=True)
        add_text(p, f" – {en_body};")

        p = _indented_paragraph()
        add_text(p, f"e-mail: {a['email']}; ")
        add_text(p, f"ORCID Author ID: {a['orcid']}; ")
        add_text(p, f"Scopus Author ID: {a['scopus']}.")


# ---------- Основна збірка ----------

def main() -> None:
    doc = Document()
    setup_document(doc)

    # --- Pre-compute OMML for every $...$/$$..$$ math expression in the corpus.
    # This is one pandoc subprocess call regardless of how many formulas there
    # are, so adding inline math to prose has no per-formula latency cost.
    inline_math = _collect_math_expressions(
        C.SECTION_4_THEORY_PART_1,
        C.SECTION_4_THEORY_PART_2,
        C.SECTION_4_THEORY_PART_3,
        C.SECTION_4_METHODS_PART_1,
        C.SECTION_4_METHODS_PART_2,
        C.SECTION_5_RESULTS,
        C.SECTION_6_DISCUSSION,
        C.SECTION_7_CONCLUSIONS,
    )
    display_latex = {f["latex"] for f in C.FORMULAS}
    _build_omml_cache(inline_math | display_latex)

    # --- Header (UDC + EN authors line + EN title) ---
    add_udc(doc)
    add_authors_short(doc)
    add_title(doc, C.TITLE_EN)

    # --- Structured EN abstract ---
    add_line(doc, "Abstract", bold=True, italic=True, space_before=4)
    add_structured_abstract(
        doc,
        label_subject="Subject of study",
        label_goal="Aim",
        label_tasks="Objectives",
        label_methods="Methods",
        label_results="Results",
        label_conclusions="Conclusions",
        parts={
            "subject": C.ABSTRACT_EN_SUBJECT,
            "goal": C.ABSTRACT_EN_GOAL,
            "tasks": C.ABSTRACT_EN_TASKS,
            "methods": C.ABSTRACT_EN_METHODS,
            "results": C.ABSTRACT_EN_RESULTS,
            "conclusions": C.ABSTRACT_EN_CONCLUSIONS,
        },
    )
    add_keywords(doc, label="Keywords", words=C.KEYWORDS_EN)

    # --- Body sections (EN, ITSSI seven-section structure) ---
    add_section(doc, "1. Introduction", C.SECTION_1_INTRO)
    add_section(
        doc,
        "2. Analysis of sources and definition of the problem",
        C.SECTION_2_LITERATURE,
    )
    add_section(doc, "3. Research objectives and tasks", C.SECTION_3_AIM)

    # §4 = §4.1 theoretical framework + §4.2 experimental implementation
    add_section_heading(doc, "4. Materials and research methods")

    add_line(
        doc,
        "4.1. Theoretical framework: Invariant Structural Learning",
        bold=True,
        italic=True,
        space_before=4,
    )
    used_formulas: set[str] = set()
    render_with_anchored_formulas(
        doc, C.SECTION_4_THEORY_PART_1, C.FORMULAS, used_formulas,
    )
    render_with_anchored_formulas(
        doc, C.SECTION_4_THEORY_PART_2, C.FORMULAS, used_formulas,
    )
    render_with_anchored_formulas(
        doc, C.SECTION_4_THEORY_PART_3, C.FORMULAS, used_formulas,
    )

    add_line(
        doc,
        "4.2. Experimental implementation",
        bold=True,
        italic=True,
        space_before=4,
    )
    render_with_anchored_formulas(
        doc, C.SECTION_4_METHODS_PART_1, C.FORMULAS, used_formulas,
    )
    add_table_from_csv(
        doc,
        FIGURES_DIR / "table_features_en.csv",
        headers=["Name", "Description"],
        caption_above=(
            "Table 1. The fourteen-element node feature vector of the "
            "graph image representation, grouped by conceptual category."
        ),
        col_widths_cm=[6.5, 10.5],
    )
    render_with_anchored_formulas(
        doc, C.SECTION_4_METHODS_PART_2, C.FORMULAS, used_formulas,
    )

    add_section(doc, "5. Research results", C.SECTION_5_RESULTS)
    add_image(
        doc,
        FIGURES_DIR / "fig_1_pipeline.png",
        width_inches=6.0,
        caption_below=(
            "Figure 1. End-to-end pipeline from raster image to "
            "concept-attractor classification via graph edit distance."
        ),
    )
    add_image(
        doc,
        FIGURES_DIR / "fig_2_digit7_graph.png",
        width_inches=5.5,
        caption_below=(
            "Figure 2. Graph representation of digit 7: left — the "
            "original MNIST raster; right — the corresponding skeletal "
            "graph with Point and Vector nodes."
        ),
    )
    add_image(
        doc,
        FIGURES_DIR / "fig_3_concept_7_1.png",
        width_inches=4.5,
        caption_below=(
            "Figure 3. Concept-attractor 7_1 after structural reduction: "
            "a linear chain of three Point and two Vector nodes — one "
            "of the smallest nontrivial attractors in the alphabet."
        ),
    )
    add_image(
        doc,
        FIGURES_DIR / "fig_4_confusion_matrix.png",
        width_inches=5.5,
        caption_below=(
            "Figure 4. Confusion matrix on the complete-contour subset of "
            "MNIST (8 685 successfully classified images across 10 "
            "classes). The 'not classified' column contains images that "
            "did not match any concept."
        ),
    )

    add_table_from_csv(
        doc,
        FIGURES_DIR / "table_concept_alphabet.csv",
        headers=[
            "Concept",
            "Class",
            "Originals",
            "Augmented",
            "Training instances",
            "Concept node count",
        ],
        caption_above=(
            "Table 2. Concept alphabet: "
            "per-concept origin counts, augmented-variant counts, "
            "post-augmentation training-set size, concept node count, "
            "and class membership."
        ),
        col_widths_cm=[2.2, 1.5, 2.2, 2.2, 3.5, 3.0],
    )

    add_table_from_csv(
        doc,
        FIGURES_DIR / "table_2_per_class.csv",
        headers=[
            "Class",
            "Precision, %",
            "Recall, %",
            "F1, %",
            "Support",
        ],
        caption_above=(
            "Table 3. Per-class classifier metrics on the "
            "complete-contour subset of MNIST: precision, recall, F1, "
            "support."
        ),
        col_widths_cm=[2.0, 3.0, 3.0, 2.5, 4.0],
    )

    add_table_from_csv(
        doc,
        FIGURES_DIR / "table_3_confusions.csv",
        headers=[
            "True class",
            "Predicted class",
            "Count",
            "% of class errors",
        ],
        caption_above=(
            "Table 4. Top-10 confusion pairs (true → predicted): "
            "absolute count and share of class-level errors."
        ),
        col_widths_cm=[3.5, 4.0, 3.0, 4.5],
    )

    add_section(doc, "6. Discussion of results", C.SECTION_6_DISCUSSION)
    add_section(doc, "7. Conclusions", C.SECTION_7_CONCLUSIONS)

    # --- Mandatory ITSSI declarations ---
    add_blank_line(doc)
    add_declarations(doc)

    # --- References ---
    add_blank_line(doc)
    add_references(doc)

    # --- Bilingual author info (UA + EN interleaved, per ITSSI sample) ---
    add_blank_line(doc)
    add_authors_block(doc)

    # --- Trailing UA tail block: UA title + UA abstract + UA keywords ---
    add_blank_line(doc)
    add_authors_short_ua(doc)
    add_title(doc, C.TITLE_UA)

    add_line(doc, "Анотація", bold=True, italic=True, space_before=4)
    add_structured_abstract(
        doc,
        label_subject="Предмет дослідження",
        label_goal="Мета",
        label_tasks="Завдання",
        label_methods="Методи",
        label_results="Результати",
        label_conclusions="Висновки",
        parts={
            "subject": C.ABSTRACT_UA_SUBJECT,
            "goal": C.ABSTRACT_UA_GOAL,
            "tasks": C.ABSTRACT_UA_TASKS,
            "methods": C.ABSTRACT_UA_METHODS,
            "results": C.ABSTRACT_UA_RESULTS,
            "conclusions": C.ABSTRACT_UA_CONCLUSIONS,
        },
    )
    add_keywords(doc, label="Ключові слова", words=C.KEYWORDS_UA)

    doc.save(str(OUT))
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
