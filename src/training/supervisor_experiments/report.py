"""Artifact writers: figures to researches/figures/, findings to researches/."""
from pathlib import Path

from . import REPO

RESEARCHES = REPO / "researches"
FIGURES = RESEARCHES / "figures"


def save_figure(fig, relpath: str) -> Path:
    path = FIGURES / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"saved {path.relative_to(REPO)}")
    return path


def write_text(relpath: str, text: str) -> Path:
    path = RESEARCHES / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"saved {path.relative_to(REPO)} ({len(text.splitlines())} lines)")
    return path


def df_to_markdown(df, floatfmt: str = ".4f") -> str:
    try:
        return df.to_markdown(floatfmt=floatfmt)
    except ImportError:
        return df.to_string()


PROGRAM_SECTIONS = [
    ("1. Post-mortem 2→7", "two_to_seven_postmortem.md"),
    ("2. Параметри концептів і компресія (S6)", "concept_parameter_compression.md"),
    ("3. Збіжність редукції (S5)", "concept_convergence_findings.md"),
    ("4. Залежність від порядку (S2)", "order_dependence_findings.md"),
    ("5. Залежність від кількості прикладів (S3)", "sample_count_findings.md"),
    ("6. Варіанти датасетів MNIST (S1)", "dataset_variants_findings.md"),
    ("7. Аугментація (S4)", "augmentation_findings.md"),
]


def write_program_summary() -> Path:
    lines = ["# Зведення дослідницької програми (базлайн 91.13%, run_20260630_235356)",
             "", "Артефакти по пунктах керівника:", ""]
    for title, fname in PROGRAM_SECTIONS:
        path = RESEARCHES / fname
        status = "✅" if path.exists() else "⏳ ще не виконано"
        lines.append(f"- **{title}** — [{fname}]({fname}) {status}")
    lines += ["", "Фігури: `researches/figures/`. Відтворення: "
              "`src/training/supervisor_experiments.ipynb` (kernel natural-agi)."]
    return write_text("supervisor_program_summary.md", "\n".join(lines) + "\n")
