"""Build the AIS template the author writes in: journal headings, figures, tables and formulas, no prose.

Usage:
    .venv/bin/python papers/concept_stability_2026/ais/writing_kit/build_template.py

The layout is the journal's (../../journal_rules/ais_layout.md), so the text is
written straight into the final format.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

import build_docx as B  # noqa: E402
import content as C  # noqa: E402

TEXT = "[text]"
CAPTION = "[caption]"
KEEP_END = ("Conflicts of interest", "Funding", "Data Availability")


def placeholder_blocks(blocks: list) -> list:
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
    return result


def blank_content() -> None:
    C.SECTIONS = [{"title": s["title"], "blocks": placeholder_blocks(s["blocks"])} for s in C.SECTIONS]
    C.ABSTRACT = [(label, TEXT) for label, _ in C.ABSTRACT]
    C.UA_ABSTRACT = [(label, "[текст]") for label, _ in C.UA_ABSTRACT]
    C.END_SECTIONS = [(title, text if title in KEEP_END else TEXT) for title, text in C.END_SECTIONS]


def main() -> None:
    blank_content()
    B.OUT = HERE / "lapin_ais_2026_template.docx"
    B.main()


if __name__ == "__main__":
    main()
