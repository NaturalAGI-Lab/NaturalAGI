"""Generate MicroCAD conference thesis in Ukrainian as a Word document.

Requirements (per https://web.kpi.kharkov.ua/microcad/vimogi-do-oformlennya/):
- Max 1 A4 page (no images added)
- Times New Roman 14pt
- Margins 2cm (all sides)
- Single line spacing
- Title: uppercase, centered, bold
- Authors: centered, bold (second line)
- Organization + city: centered, italic semibold (third line)
- Body indent 1cm
- References per DSTU 8302:2015 (numbered list)

Authors: Lapin, Bokhan, Perevoznyk, Parzhyn, Aleksandrova
(Aleksandrova T.Ye. — scientific supervisor of the NDR at the SAY department).
"""
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


OUT = Path(__file__).parent / "Lapin.docx"
FONT = "Times New Roman"


def style_run(run, *, size=14, bold=False, italic=False,
              superscript=False, subscript=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.superscript = superscript
    run.font.subscript = subscript


def make_paragraph(doc, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                   first_line_indent_cm=None,
                   space_before=0, space_after=0):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = 1.0
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if first_line_indent_cm is not None:
        pf.first_line_indent = Cm(first_line_indent_cm)
    return p


def add_text(p, text, **style):
    run = p.add_run(text)
    style_run(run, **style)
    return run


def add_line(doc, text, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             size=14, bold=False, italic=False,
             first_line_indent_cm=None, space_before=0, space_after=0):
    p = make_paragraph(doc, align=align,
                       first_line_indent_cm=first_line_indent_cm,
                       space_before=space_before, space_after=space_after)
    add_text(p, text, size=size, bold=bold, italic=italic)
    return p


def add_authors_line(doc):
    """Author block with superscript affiliation markers."""
    p = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    # Лапін¹, Бохан¹, Перевозник¹, Паржин², Александрова¹
    parts = [
        ("Лапін М.О.", "1"),
        (", Бохан К.О.", "1"),
        (", Перевозник К.М.", "1"),
        (", Паржин Ю.В.", "2"),
        (", Александрова Т.Є.", "1"),
    ]
    for name, marker in parts:
        add_text(p, name, bold=True)
        add_text(p, marker, bold=True, superscript=True)


def add_affiliations(doc):
    """Two-line affiliation block, italic bold per MicroCAD requirements."""
    p1 = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(p1, "1", bold=True, italic=True, superscript=True)
    add_text(
        p1,
        " Національний технічний університет «Харківський політехнічний "
        "інститут», м. Харків",
        bold=True, italic=True,
    )
    p2 = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(p2, "2", bold=True, italic=True, superscript=True)
    add_text(p2, " Augusta University, м. Огаста, США",
             bold=True, italic=True)


def add_formula_paragraph(doc, before_text, after_text):
    """Paragraph containing the inline formula C_{i+1} = CRO(C_i, G_{i+1})."""
    p = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                       first_line_indent_cm=1.0)
    add_text(p, before_text)
    # C
    add_text(p, "C")
    add_text(p, "i+1", subscript=True)
    add_text(p, " = CRO(C")
    add_text(p, "i", subscript=True)
    add_text(p, ", G")
    add_text(p, "i+1", subscript=True)
    add_text(p, ")")
    add_text(p, after_text)


def main() -> None:
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(14)

    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    # Title
    add_line(
        doc,
        "СТРУКТУРА ЯК НОСІЙ ПОЯСНЕНЬ: ГРАФОВІ АТРАКТОРИ "
        "ДЛЯ РОЗПІЗНАВАННЯ КОНТУРНИХ ОБРАЗІВ",
        align=WD_ALIGN_PARAGRAPH.CENTER, bold=True,
    )
    add_authors_line(doc)
    add_affiliations(doc)

    # Body paragraphs (re-authored to sound less AI-generated)
    para1 = (
        "Глибокі нейромережі класифікують образи дедалі точніше, однак "
        "пояснити їхні рішення важко. Post-hoc методи на кшталт LIME чи "
        "SHAP наближують поведінку вже навченої моделі та піддаються "
        "змагальним атакам [1]. У медицині, безпеці й юриспруденції це "
        "неприйнятно: пояснення має випливати із самої моделі, а не з її "
        "зовнішньої апроксимації."
    )
    para2 = (
        "В роботі розглянуто питання перенесення семантики класифікатора "
        "безпосередньо у структуру графового представлення, щоб пояснення "
        "випливало із самої моделі. Контур зображення розкладається на "
        "вершини двох типів: критичні точки (кінці, кути, перетини) та "
        "відрізки. Нормалізовані координати, напрямки й кількість циклів "
        "зберігаються прямо на вершинах графа, а не в прихованих вагах [2]."
    )
    before_formula = (
        "Концепт класу будується з 2–6 прикладів: кожен новий зразок "
        "скорочує попередній концепт за правилом "
    )
    after_formula = (
        ". Рідкісні гілки відсікаються, близькі точки перетину зливаються, "
        "а числові атрибути перетворюються на діапазони {min, max, center}. "
        "Процедура збігається до стабільного графового атрактора без "
        "використання зворотного поширення помилки та градієнтної "
        "оптимізації [3]."
    )
    para5 = (
        "На етапі класифікації тестовий граф порівнюється з кожним "
        "концептом за метрикою Graph Edit Distance; прогнозованим "
        "обирається клас того концепту, для якого досягнуто мінімальної "
        "відстані редагування. Валідацію проведено на повному тестовому "
        "наборі MNIST (12 000 зображень, 10 класів) із алфавітом з 13 "
        "концептів-атракторів. Досягнуто точність класифікації 74,12 %, "
        "макро-точність 78,04 %, F1-міру 74,49 %. Основні помилки "
        "зосереджено на структурно подібних парах цифр: 5→3 (33,3 % "
        "помилок класу 5), 3→7 (21,1 %), 8→6 (20,0 %), що узгоджується з "
        "інтерпретованою природою методу: кожну помилку можна "
        "проаналізувати на рівні графів."
    )

    add_line(doc, para1, first_line_indent_cm=1.0)
    add_line(doc, para2, first_line_indent_cm=1.0)
    add_formula_paragraph(doc, before_formula, after_formula)
    add_line(doc, para5, first_line_indent_cm=1.0)

    # References header
    add_line(
        doc, "Література",
        align=WD_ALIGN_PARAGRAPH.CENTER, bold=True,
    )

    # Reference 1: conference paper (italic title of proceedings, em-dash pages)
    p1 = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                        first_line_indent_cm=1.0)
    add_text(p1, "1. Slack D., Hilgard S., Jia E., Singh S., Lakkaraju H. "
             "Fooling LIME and SHAP: adversarial attacks on post hoc "
             "explanation methods. ")
    add_text(p1, "Proceedings of the AAAI/ACM Conference on AI, Ethics, "
             "and Society", italic=True)
    add_text(p1, " : AIES ’20, New York, USA, February 7–8, 2020. New "
             "York : ACM, 2020. P. 180—186. DOI: 10.1145/3375627.3375830.")

    # Reference 2: journal article (italic journal, em-dash pages)
    p2 = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                        first_line_indent_cm=1.0)
    add_text(p2, "2. Parzhyn Y., Lapin M., Bokhan K. A new approach to "
             "building energy models of neural networks. ")
    add_text(p2, "Advanced Information Systems", italic=True)
    add_text(p2, ". 2025. Vol. 9, no. 4. P. 100—119. "
             "DOI: 10.20998/2522-9052.2025.4.13.")

    # Reference 3: arXiv preprint (electronic resource)
    p3 = make_paragraph(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                        first_line_indent_cm=1.0)
    add_text(p3, "3. Parzhyn Y. Architecture of information : preprint. ")
    add_text(p3, "arXiv", italic=True)
    add_text(p3, ". 2025. arXiv:2503.21794. URL: "
             "https://arxiv.org/abs/2503.21794 "
             "(дата звернення: 16.04.2026). "
             "DOI: 10.48550/arXiv.2503.21794.")

    doc.save(OUT)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
