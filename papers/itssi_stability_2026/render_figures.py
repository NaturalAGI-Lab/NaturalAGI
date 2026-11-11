"""Render English-language figures for the concept-stability paper.

Re-plots from the committed formation-probe caches and baseline run
artifacts. Neo4j (holding the baseline image graphs) is required only for
the two triptychs; everything else runs offline.

Usage: .venv/bin/python papers/concept_stability_2026/render_figures.py
"""
import random
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

PAPER = Path(__file__).resolve().parent
REPO = PAPER.parents[1]
sys.path.insert(0, str(REPO / "src" / "training"))

from supervisor_experiments import convergence as cv  # noqa: E402
from supervisor_experiments import postmortem as pm  # noqa: E402
from supervisor_experiments import sample_count as sc  # noqa: E402

FIGURES = PAPER / "figures"


def save(fig, name: str) -> None:
    path = FIGURES / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"wrote {path.relative_to(REPO)}")


def render_offline() -> None:
    conv_df = cv.run_convergence_probes()
    save(cv.plot_trajectories(lang="en"), "trajectories.png")
    sc_df = sc.run_sample_count_grid()
    save(sc.plot_curves(sc_df, full_reference=conv_df, lang="en"), "curves.png")

    random.seed(0)
    np.random.seed(0)
    confusion = pm.load_confusion()
    params = pm.load_params()
    row = confusion[confusion.image_id == pm.PRIMARY_EXEMPLAR].iloc[0]
    save(pm.construction_figure(row, params, lang="en"),
         "mnist_test_2_00766_construction.png")


def render_neo4j() -> None:
    confusion = pm.load_confusion()
    params = pm.load_params()
    concepts = pm.load_run_concepts()
    for image_id, name in ((pm.PRIMARY_EXEMPLAR, "mnist_test_2_00766"),
                           (pm.CONTRAST_EXEMPLAR, "mnist_test_2_00984")):
        row = confusion[confusion.image_id == image_id].iloc[0]
        save(pm.triptych(image_id, row, concepts, params, lang="en"),
             f"{name}_triptych.png")


if __name__ == "__main__":
    render_offline()
    render_neo4j()
