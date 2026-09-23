"""Render the three figures for the IEEE DESSERT'2026 paper.

Reproducible: run with the project venv, e.g.

    .venv/bin/python papers/ieee_dessert_2026/render_figures.py

Fig 1 (pipeline) and Fig 3 (confusion matrix) are generated purely from code
and committed artefacts under experiments/run_20260630_235356/.

Fig 2 (worked classification trace) recomposes two evidence figures from the
PhD wiki vault (read-only source, outside this repo):

    ~/Development/personal/PhDObsidian/raw/evidence/2026-07_supervisor_remarks/
        5_reduction_inference/construction_stages_2_00766.png
        2_figures/2_to_7_triptych_mnist_test_2_00766.png

If that vault is not present locally, Fig 2 generation is skipped (Fig 1 and
Fig 3 still render).
"""

import shutil
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import PowerNorm
from matplotlib.patches import FancyBboxPatch
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent / "figures"
RUN_DIR = REPO_ROOT / "experiments" / "run_20260630_235356"
VAULT_EVIDENCE = (
    REPO_ROOT.parent
    / "PhDObsidian"
    / "raw"
    / "evidence"
    / "2026-07_supervisor_remarks"
)

# figure* (full text-width) figures render at the DESSERT column width;
# the single-column confusion matrix renders narrower.
FULL_WIDTH_CM = 17.8
COL_WIDTH_CM = 8.6
CM_TO_IN = 1 / 2.54
TARGET_DPI = 400

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
plt.rcParams["axes.unicode_minus"] = False


def _save(fig, name: str, fig_w_in: float | None = None, target_width_cm: float | None = None) -> Path:
    """Save at TARGET_DPI, or at whatever dpi makes fig_w_in print at
    target_width_cm and TARGET_DPI once LaTeX scales it to that width."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / name
    if fig_w_in is not None and target_width_cm is not None:
        dpi = TARGET_DPI * (target_width_cm * CM_TO_IN) / fig_w_in
    else:
        dpi = TARGET_DPI
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Fig 1 — pipeline scheme
# ---------------------------------------------------------------------------

# (label, box width in design inches -- sized to the label's longest line)
STAGES = [
    ("Input image\n(100×100)", 1.10),
    ("Binarization\n(θ = 110)", 1.15),
    ("Thinning\nto 1 px", 0.90),
    ("Growing\nNeural Gas", 1.00),
    ("Ramer–Douglas–\nPeucker\nsimplification\n(ε = 4.55)", 1.35),
    ("Bipartite\nattributed\ngraph", 1.00),
    ("Features and\nnormalization", 1.25),
]


def build_fig1_pipeline() -> Path:
    # Single row, 7 boxes, right-arrows between them. Data units equal
    # design inches; the whole figure is later rescaled (via _save's
    # dpi trick) to print at exactly FULL_WIDTH_CM regardless of these
    # design-time box sizes -- only their *ratios* (box_w/content_w,
    # fontsize/fig_w_in) survive into the final printed figure.
    gap_x = 0.12
    margin = 0.06
    fontsize = 11
    target_height_cm = 2.2  # within the requested 2.0-2.4 cm range

    widths = [w for _, w in STAGES]
    content_w = sum(widths) + (len(STAGES) - 1) * gap_x
    fig_w_in = content_w + 2 * margin
    fig_h_in = (target_height_cm / FULL_WIDTH_CM) * fig_w_in
    box_h = fig_h_in - 2 * margin

    fig = plt.figure(figsize=(fig_w_in, fig_h_in))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, fig_w_in)
    ax.set_ylim(0, fig_h_in)
    ax.axis("off")

    row_y = fig_h_in / 2
    centers = []
    x = margin
    for w in widths:
        centers.append(x + w / 2)
        x += w + gap_x

    def draw_box(cx, cy, text, box_w):
        box = FancyBboxPatch(
            (cx - box_w / 2, cy - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            linewidth=1.2,
            edgecolor="black",
            facecolor="white",
        )
        ax.add_patch(box)
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, linespacing=1.3)

    def draw_arrow(p_from, p_to):
        ax.annotate(
            "",
            xy=p_to,
            xytext=p_from,
            arrowprops=dict(arrowstyle="-|>", lw=1.2, color="black", shrinkA=0, shrinkB=0),
        )

    for cx, (text, w) in zip(centers, STAGES):
        draw_box(cx, row_y, text, w)

    for i in range(len(centers) - 1):
        draw_arrow(
            (centers[i] + widths[i] / 2, row_y), (centers[i + 1] - widths[i + 1] / 2, row_y)
        )

    final_pt = fontsize * (FULL_WIDTH_CM * CM_TO_IN) / fig_w_in
    final_height_cm = (fig_h_in / fig_w_in) * FULL_WIDTH_CM
    print(
        f"[fig1] design fig_w_in={fig_w_in:.3f}in | at {FULL_WIDTH_CM}cm width: "
        f"height={final_height_cm:.2f}cm, font≈{final_pt:.2f}pt-equivalent (need >=7.5pt)"
    )

    return _save(fig, "fig_pipeline.png", fig_w_in=fig_w_in, target_width_cm=FULL_WIDTH_CM)


# ---------------------------------------------------------------------------
# Fig 2 — worked classification trace (mnist_test_2_00766)
# ---------------------------------------------------------------------------

# Crop boxes (x0, y0, x1, y1) measured on the two source evidence images.
# Padding of ~10 px is included so graph nodes/edges are not clipped, and the
# top edge is set to skip the source images' own (Russian) panel titles.
CONSTRUCTION_STAGES_CROPS = {
    "original": (84, 84, 734, 725),  # panel 1: content starts at y=84, no gap to spare
    "skeleton": (1480, 84, 2192, 725),  # panel 3: 1px skeleton
}
TRIPTYCH_CROPS = {
    "graph": (733, 143, 1345, 681),  # panel 2: image graph
    "concept_2_1": (2104, 151, 2716, 673),  # panel 4: concept 2_1
    "concept_7_1": (2789, 143, 3402, 681),  # panel 5: concept 7_1
}


def _load_crop(path: Path, box):
    im = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = box
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, im.width), min(y1, im.height)
    return np.asarray(im.crop((x0, y0, x1, y1)))


def build_fig2_trace() -> Path | None:
    stages_path = VAULT_EVIDENCE / "5_reduction_inference" / "construction_stages_2_00766.png"
    triptych_path = VAULT_EVIDENCE / "2_figures" / "2_to_7_triptych_mnist_test_2_00766.png"
    if not stages_path.exists() or not triptych_path.exists():
        print(f"[fig2] evidence source not found under {VAULT_EVIDENCE}, skipping fig_trace.png")
        return None

    panels = [
        (_load_crop(stages_path, CONSTRUCTION_STAGES_CROPS["original"]), "1. Input image"),
        (_load_crop(stages_path, CONSTRUCTION_STAGES_CROPS["skeleton"]), "2. Skeleton (1 px)"),
        (_load_crop(triptych_path, TRIPTYCH_CROPS["graph"]), "3. Image graph"),
        (_load_crop(triptych_path, TRIPTYCH_CROPS["concept_2_1"]), "4. Concept 2_1\n(expected)"),
        (_load_crop(triptych_path, TRIPTYCH_CROPS["concept_7_1"]), "5. Concept 7_1\n(predicted)"),
    ]

    # Single row, laid out manually (rather than plt.subplots) so each panel's
    # axes exactly matches its crop's aspect ratio -- no letterboxed blank
    # space. fig_w_in is the true final width (no post-hoc dpi rescaling, see
    # _save below), so every size below is a real physical inch amount.
    fig_w_in = FULL_WIDTH_CM * CM_TO_IN
    margin_left = margin_right = 0.05
    margin_top = 0.05
    margin_bottom = 0.05
    title_h = 0.32  # fits the 2-line titles (panels 4-5); 1-line titles just use less of it
    legend_h = 0.20
    gap_x = 0.06
    title_fontsize = 8
    legend_fontsize = 7

    usable_w = fig_w_in - margin_left - margin_right
    panel_w = (usable_w - (len(panels) - 1) * gap_x) / len(panels)
    aspects = [img.shape[0] / img.shape[1] for img, _ in panels]
    row_h = max(panel_w * a for a in aspects)

    fig_h_in = margin_top + title_h + row_h + legend_h + margin_bottom

    fig = plt.figure(figsize=(fig_w_in, fig_h_in))

    y_title_top = fig_h_in - margin_top
    y_img_top = y_title_top - title_h
    for i, (img, title) in enumerate(panels):
        aspect = img.shape[0] / img.shape[1]
        h = panel_w * aspect
        x = margin_left + i * (panel_w + gap_x)
        ax = fig.add_axes(
            (x / fig_w_in, (y_img_top - h) / fig_h_in, panel_w / fig_w_in, h / fig_h_in)
        )
        ax.imshow(img)
        ax.axis("off")
        fig.text(
            (x + panel_w / 2) / fig_w_in,
            y_title_top / fig_h_in,
            title,
            ha="center",
            va="top",
            multialignment="center",
            fontsize=title_fontsize,
            linespacing=1.15,
        )

    y_row_bottom = y_img_top - row_h
    fig.text(
        0.5,
        (y_row_bottom - 0.03) / fig_h_in,
        "StP — start; EnP — end; CrP — corner; IntP — intersection; "
        "H, V, Vec — horizontal/vertical edge, direction vector.",
        ha="center",
        va="top",
        fontsize=legend_fontsize,
    )

    upscales = [panel_w * TARGET_DPI / img.shape[1] for img, _ in panels]
    print(
        f"[fig2] panel_w={panel_w:.3f}in ({panel_w / CM_TO_IN:.2f}cm) "
        f"fig_h={fig_h_in:.3f}in ({fig_h_in / CM_TO_IN:.2f}cm) "
        f"upscale={[f'{u:.2f}x' for u in upscales]} (>1 = source crop upscaled)"
    )

    return _save(fig, "fig_trace.png")


# ---------------------------------------------------------------------------
# Fig 3 — confusion matrix
# ---------------------------------------------------------------------------

CLASSES = [str(i) for i in range(10)]


def copy_fig3_confusion() -> Path:
    """Fig. 3 is the run artefact itself, not a re-render."""
    src = RUN_DIR / "confusion_matrix.png"
    dst = OUTPUT_DIR / "fig_confusion.png"
    shutil.copyfile(src, dst)
    return dst


if __name__ == "__main__":
    p1 = build_fig1_pipeline()
    print("wrote", p1)
    p2 = build_fig2_trace()
    if p2:
        print("wrote", p2)
    p3 = copy_fig3_confusion()
    print("wrote", p3)
