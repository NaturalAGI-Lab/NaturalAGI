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
