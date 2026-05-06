"""Fill MicroCAD conference application form for Mykyta Lapin.

Reads the Ukrainian application form template and appends data after each
label, preserving original formatting.
"""
from pathlib import Path
from copy import deepcopy

from docx import Document
from docx.shared import Pt

SRC = Path('/Users/mlapin/Development/personal/NaturalAGI/'
           'Zayavka-na-uchast-v-konferentsiyi.docx')
OUT = Path('/Users/mlapin/Development/personal/NaturalAGI/'
           'papers/microcad_2025_thesis/Lapin_zayavka.docx')

# Data known from sources: CLAUDE.md, itssi_paper_2025.tex, paper emails.
# Patronymic, phone, and exact academic status require user confirmation.
DATA = {
    "Прізвище:": "Лапін",
    "Ім’я:": "Микита",
    "По-батькові:": "Олексійович",
    "Назва організації:":
        "Національний технічний університет "
        "«Харківський політехнічний інститут»",
    "Посада:": "аспірант",
    "Науковий ступінь, вчене звання:": "магістр",
    "Тел.:": "+380 (99) 244-45-01",
    "Е-mail:": "Mykyta.Lapin@cit.khpi.edu.ua",
    "Номер секції/підсекції":
        "Секція 9, підсекція 9.2 — Штучний інтелект, "
        "аналіз даних та математичне моделювання",
    "Назва доповіді":
        "Структура як носій пояснень: графові атрактори "
        "для розпізнавання контурних образів",
}


def append_value(para, value: str) -> None:
    """Append a value after the label, copying the last run's formatting."""
    if para.runs:
        run = para.add_run(f" {value}")
        src = para.runs[0]
        run.font.name = src.font.name or "Times New Roman"
        if src.font.size:
            run.font.size = src.font.size
        run.bold = False  # values are plain
    else:
        run = para.add_run(f" {value}")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def main() -> None:
    doc = Document(SRC)

    for p in doc.paragraphs:
        text = p.text.strip()
        for label, value in DATA.items():
            if text == label or text.startswith(label):
                append_value(p, value)
                break

    doc.save(OUT)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
