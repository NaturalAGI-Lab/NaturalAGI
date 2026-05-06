"""ITSSI-2026 генератор статті у форматі .docx.

Використання:
    natural-agi/bin/python papers/itssi_paper_2026/generate_paper.py

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
- Не вставляє MathType-формули — генерує placeholder-параграф з маркером
  «[TODO MathType]». Відкрити документ у Word, видалити рядок, вставити
  MathType-об'єкт на його місце.
- Не вставляє рисунки (≥ 300 dpi .png). Генерує placeholder `[Рис. N: ...]`.
  Замінити на Insert → Pictures, вирівняти по центру, підписати знизу.
- Не генерує таблиці — вони дрібні, але унікальні для кожної версії; краще
  створити їх у Word вручну (Insert → Table), щоб контролювати ширину колонок.

Перевірка результату:
    soffice --headless --convert-to pdf --outdir papers/itssi_paper_2026/ \\
        papers/itssi_paper_2026/itssi_paper_2026.docx
    pdfinfo papers/itssi_paper_2026/itssi_paper_2026.pdf | grep Pages
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

import content as C

OUT = Path(__file__).parent / "itssi_paper_2026.docx"
FONT = "Times New Roman"
BODY_SIZE_PT = 10
INDENT_CM = 1.0


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
    pf.line_spacing = 1.0
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent_cm is not None:
        pf.first_line_indent = Cm(indent_cm)
    return p


def add_text(p, text: str, **style) -> None:
    run = p.add_run(text)
    style_run(run, **style)


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
    """Список авторів у форматі 'Прізвище І. Б., ...'."""
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


def add_formula_placeholder(
    doc,
    *,
    number: int,
    caption: str,
) -> None:
    """Placeholder під MathType. Автор вручну замінить у Word.

    Рекомендація: у фінальному Word-файлі виділити цей абзац, видалити текст,
    вставити MathType-об'єкт. Номер (N) і вирівнювання по правому краю
    залишаться, якщо вставити через inline equation.
    """
    p = new_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(p, f"[TODO MathType: {caption}]", italic=True)
    add_text(p, f"\t\t({number})")


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
        ("Конфлікт інтересів", C.DECLARATION_COI),
        ("Фінансування", C.DECLARATION_FUNDING),
        ("Доступність даних", C.DECLARATION_DATA),
        ("Використання засобів штучного інтелекту", C.DECLARATION_AI),
    ):
        add_line(doc, heading, bold=True, italic=True, space_before=4)
        add_line(doc, body, indent_cm=INDENT_CM)


def format_reference(ref: dict, idx: int) -> tuple[str, str, str]:
    """Одна Harvard-BSI стаття, розбита на 3 сегменти:
    (prefix, italic_venue, suffix). Italic — тільки назва журналу/праць.
    """
    authors = ref["authors"]
    year = ref["year"]
    title = ref["title"]
    venue = ref["venue"]
    vol = ref.get("volume")
    issue = ref.get("issue")
    pages = ref.get("pages")
    doi = ref.get("doi")

    prefix = f"{idx}. {authors} ({year}), \"{title}\", "
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


def add_author_details_block(
    doc,
    *,
    heading_ua: str,
    heading_en: str,
) -> None:
    """Відомості про авторів — двома мовами, один блок на автора."""
    add_section_heading(doc, heading_ua)
    for a in C.AUTHORS:
        p = new_paragraph(doc, indent_cm=INDENT_CM)
        add_text(
            p,
            f"{a['full_name_ua']} — {a['degree_ua']}, "
            f"{a['org_ua']}, {a['position_ua']}, "
            f"{a['city_ua']}, {a['country_ua']}; ",
        )
        add_text(p, f"e-mail: {a['email']}; ")
        add_text(p, f"ORCID: {a['orcid']}; ")
        add_text(p, f"Scopus Author ID: {a['scopus']}; ")
        add_text(p, f"моб. {a['phone']}.")

    add_section_heading(doc, heading_en)
    for a in C.AUTHORS:
        p = new_paragraph(doc, indent_cm=INDENT_CM)
        add_text(
            p,
            f"{a['full_name_en']} – {a['degree_en']}, "
            f"{a['position_en']}, {a['org_en']}, "
            f"{a['city_en']}, {a['country_en']}; ",
        )
        add_text(p, f"e-mail: {a['email']}; ")
        add_text(p, f"ORCID: {a['orcid']}; ")
        add_text(p, f"Scopus Author ID: {a['scopus']}; ")
        add_text(p, f"mob. {a['phone']}.")


# ---------- Основна збірка ----------

def main() -> None:
    doc = Document()
    setup_document(doc)

    # --- Шапка ---
    add_udc(doc)
    add_authors_short(doc)
    add_title(doc, C.TITLE_UA)

    # --- Структурована анотація UA ---
    add_line(doc, "Анотація", bold=True, italic=True, space_before=4)
    add_structured_abstract(
        doc,
        label_subject="Предмет",
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

    # --- Основні секції ---
    add_section(doc, "1. Вступ", C.SECTION_1_INTRO)
    add_section(
        doc,
        "2. Аналіз літературних джерел і визначення проблеми",
        C.SECTION_2_LITERATURE,
    )
    add_section(doc, "3. Мета й завдання дослідження", C.SECTION_3_AIM)

    add_section(doc, "4. Матеріали й методи дослідження", C.SECTION_4_METHODS)
    add_formula_placeholder(
        doc,
        number=1,
        caption="C_{i+1} = CRO(C_i, G_{i+1})",
    )

    add_section(doc, "5. Результати дослідження", C.SECTION_5_RESULTS)
    add_figure_placeholder(
        doc,
        number=1,
        caption=(
            "пайплайн: image → skeletonization → graph → concept reduction → "
            "GED-класифікація"
        ),
    )
    add_figure_placeholder(
        doc,
        number=2,
        caption="приклад графового представлення цифри 7 з MNIST",
    )
    add_figure_placeholder(
        doc,
        number=3,
        caption="концепт-атрактор після редукції 5 прикладів",
    )
    add_figure_placeholder(
        doc,
        number=4,
        caption="матриця плутанини класифікатора на повному тесті MNIST",
    )

    add_line(
        doc,
        "[TODO Table 1: порівняння з CNN/SVM/MLP — accuracy, training "
        "samples, explainability]",
        italic=True,
        space_before=4,
    )
    add_line(
        doc,
        "[TODO Table 2: per-class metrics (precision, recall, F1, support) "
        "з run_20260410_153216]",
        italic=True,
    )
    add_line(
        doc,
        "[TODO Table 3: top-10 пар помилок матриці плутанини]",
        italic=True,
    )

    add_section(doc, "6. Обговорення результатів", C.SECTION_6_DISCUSSION)
    add_section(doc, "7. Висновки", C.SECTION_7_CONCLUSIONS)

    # --- Декларації ---
    add_blank_line(doc)
    add_declarations(doc)

    # --- References ---
    add_blank_line(doc)
    add_references(doc)

    # --- Відомості про авторів ---
    add_blank_line(doc)
    add_author_details_block(
        doc,
        heading_ua="Відомості про авторів",
        heading_en="Information about the authors",
    )

    # --- Англомовна частина ---
    add_blank_line(doc)
    add_title(doc, C.TITLE_EN)

    add_line(doc, "Abstract", bold=True, italic=True, space_before=4)
    add_structured_abstract(
        doc,
        label_subject="Subject",
        label_goal="Goal",
        label_tasks="Tasks",
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

    doc.save(OUT)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
