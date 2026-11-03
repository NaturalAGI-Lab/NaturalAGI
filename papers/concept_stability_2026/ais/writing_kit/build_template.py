"""Build the AIS template the author writes in: journal headings, figures, tables and formulas, no prose.

Usage:
    .venv/bin/python papers/concept_stability_2026/ais/writing_kit/build_template.py

The layout is the journal's (../../journal_rules/ais_layout.md), so the text is
written straight into the final format. The paragraph outline from guide.md is
placed under each heading in red italics, for the author to replace.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import RGBColor

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

import build_docx as B  # noqa: E402
import content as C  # noqa: E402

TEXT = "[text]"
CAPTION = "[caption]"
KEEP_END = ("Conflicts of interest", "Funding", "Data Availability")
OPEN, CLOSE = "⟦", "⟧"
EXTRA: dict = {}
RED = RGBColor(0xC0, 0x00, 0x00)


def read_outline() -> dict:
    text = (HERE / "guide.md").read_text()
    body = text[text.index("## Розділи"):text.index("## Рисунки")]
    notes: dict = {}
    for chunk in re.split(r"^### ", body, flags=re.M)[1:]:
        title, *lines = chunk.strip().split("\n")
        items = [line.removeprefix("- ").strip().replace("`", "") for line in lines if line.strip()]
        notes[title.strip()] = items
    return notes


def keyed_notes(notes: dict) -> dict:
    keyed: dict = {}
    for title, items in notes.items():
        number = title.split()[0].rstrip(".")
        for item in items:
            sub = re.match(r"(\d\.\d\.\d)", item)
            keyed.setdefault(sub.group(1) if sub else number, []).append(item)
    return keyed


def note(item: str) -> tuple:
    return ("p", f"{OPEN}{item}{CLOSE}")


def placeholder_blocks(blocks: list, keyed: dict) -> list:
    result = []
    for block in blocks:
        kind = block[0]
        if kind == "p":
            if not result or result[-1] != ("p", TEXT):
                result.append(("p", TEXT))
        elif kind == "fig":
            result.append(("fig", block[1], block[2], CAPTION, block[4]))
        elif kind == "tbl":
            result.append(("tbl", block[1], CAPTION) + tuple(block[3:]))
        else:
            result.append(block)
            if kind == "h2":
                result.extend(note(item) for item in keyed.get(block[1].split()[0], []))
    return result


def blank_content() -> None:
    notes = read_outline()
    keyed = keyed_notes(notes)
    sections = []
    for section in C.SECTIONS:
        number = section["title"].split(".")[0]
        lead = [note(item) for item in keyed.get(number, [])]
        blocks = section["blocks"] + EXTRA.get(number, [])
        sections.append({"title": section["title"], "blocks": lead + placeholder_blocks(blocks, keyed)})
    C.SECTIONS = sections
    abstract = notes["Анотація"]
    C.ABSTRACT = [(label, f"{OPEN}{item.split(': ', 1)[-1]}{CLOSE} {TEXT}")
                  for (label, _), item in zip(C.ABSTRACT, abstract[1:])]
    C.UA_ABSTRACT = [(label, f"{OPEN}{abstract[0]}{CLOSE} [текст]" if index == 0 else "[текст]")
                     for index, (label, _) in enumerate(C.UA_ABSTRACT)]
    end_note = f"{OPEN}{' '.join(notes['Кінцеві розділи'])}{CLOSE} {TEXT}"
    C.END_SECTIONS = [(title, text if title in KEEP_END else end_note) for title, text in C.END_SECTIONS]


def paint_notes(path: Path) -> None:
    doc = Document(str(path))
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith(OPEN):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        inside = False
        for run in paragraph.runs:
            if OPEN in run.text:
                inside = True
            if inside:
                run.font.color.rgb = RED
                run.font.italic = True
            if CLOSE in run.text:
                inside = False
            run.text = run.text.replace(OPEN, "").replace(CLOSE, "")
    doc.save(str(path))


def main() -> None:
    blank_content()
    B.OUT = HERE / "lapin_ais_2026_template.docx"
    B.main()
    paint_notes(B.OUT)


if __name__ == "__main__":
    main()
