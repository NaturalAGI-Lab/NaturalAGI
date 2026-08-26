"""Render the three figures for the ITSSI XAI paper.

Reproducible: run with the project venv, e.g.

    .venv/bin/python papers/itssi_xai_2026/render_figures.py

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

TEXT_WIDTH_CM = 16.0
CM_TO_IN = 1 / 2.54
DPI = 400

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
plt.rcParams["axes.unicode_minus"] = False


def _save(fig, name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / name
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Fig 1 — pipeline scheme
# ---------------------------------------------------------------------------

ROW1_STAGES = [
    "Вхідне\nзображення\n(100×100)",
    "Бінаризація\n(θ = 110)",
    "Стоншення\nдо 1 пкс",
    "Growing\nNeural Gas",
]
ROW2_STAGES = [
    "Спрощення Рамера—\nДугласа—Пекера\n(ε = 4,55)",
    "Двочастковий\nатрибутований граф",
    "Ознаки та\nнормалізація",
]


def build_fig1_pipeline() -> Path:
    # Data units are defined to equal inches (axes fill the whole figure and
    # xlim/ylim span exactly [0, fig_w_in] x [0, fig_h_in]). This keeps each
    # row's box width independent of the other row's — with a shared,
    # auto-rescaled axis a wider row-2 box would otherwise silently shrink
    # every row-1 box too.
    box_w1, box_w2 = 1.3, 1.9
    box_h = 0.85
    gap_x = 0.32
    row_gap_y = 0.55
    margin = 0.15

    row1_w_total = len(ROW1_STAGES) * box_w1 + (len(ROW1_STAGES) - 1) * gap_x
    row2_w_total = len(ROW2_STAGES) * box_w2 + (len(ROW2_STAGES) - 1) * gap_x
    content_w = max(row1_w_total, row2_w_total)
    content_h = 2 * box_h + row_gap_y

    fig_w_in = content_w + 2 * margin
    fig_h_in = content_h + 2 * margin

    fig = plt.figure(figsize=(fig_w_in, fig_h_in))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, fig_w_in)
    ax.set_ylim(0, fig_h_in)
    ax.axis("off")

    row1_y = margin + box_h + row_gap_y + box_h / 2
    row2_y = margin + box_h / 2
    x1_start = margin + (content_w - row1_w_total) / 2
    x2_start = margin + (content_w - row2_w_total) / 2
    x1 = [x1_start + box_w1 / 2 + i * (box_w1 + gap_x) for i in range(len(ROW1_STAGES))]
    x2 = [x2_start + box_w2 / 2 + i * (box_w2 + gap_x) for i in range(len(ROW2_STAGES))]

    def draw_box(cx, cy, text, box_w):
        box = FancyBboxPatch(
            (cx - box_w / 2, cy - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            linewidth=1.3,
            edgecolor="black",
            facecolor="white",
        )
        ax.add_patch(box)
        ax.text(cx, cy, text, ha="center", va="center", fontsize=9, linespacing=1.4)

    def draw_arrow(p_from, p_to):
        ax.annotate(
            "",
            xy=p_to,
            xytext=p_from,
            arrowprops=dict(arrowstyle="-|>", lw=1.3, color="black", shrinkA=0, shrinkB=0),
        )

    def draw_line(p_from, p_to):
        ax.plot([p_from[0], p_to[0]], [p_from[1], p_to[1]], lw=1.3, color="black")

    for cx, text in zip(x1, ROW1_STAGES):
        draw_box(cx, row1_y, text, box_w1)
    for cx, text in zip(x2, ROW2_STAGES):
        draw_box(cx, row2_y, text, box_w2)

    for i in range(len(x1) - 1):
        draw_arrow((x1[i] + box_w1 / 2, row1_y), (x1[i + 1] - box_w1 / 2, row1_y))
    for i in range(len(x2) - 1):
        draw_arrow((x2[i] + box_w2 / 2, row2_y), (x2[i + 1] - box_w2 / 2, row2_y))

    # wrap-around connector: end of row 1 -> start of row 2, routed as a clean
    # orthogonal elbow through the gap between the rows (down / left / down)
    # so it never crosses or originates inside a box.
    row1_bottom = row1_y - box_h / 2
    row2_top = row2_y + box_h / 2
    mid_y = (row1_bottom + row2_top) / 2
    gng_bottom_center = (x1[-1], row1_bottom)
    rdp_top_center = (x2[0], row2_top)
    draw_line(gng_bottom_center, (x1[-1], mid_y))
    draw_line((x1[-1], mid_y), (x2[0], mid_y))
    draw_arrow((x2[0], mid_y), rdp_top_center)

    return _save(fig, "fig_pipeline.png")


# ---------------------------------------------------------------------------
# Fig 2 — worked classification trace (mnist_test_2_00766)
# ---------------------------------------------------------------------------

# Crop boxes (x0, y0, x1, y1) measured on the two source evidence images.
# Padding of ~10 px is included so graph nodes/edges are not clipped.
CONSTRUCTION_STAGES_CROPS = {
    "original": (84, 84, 734, 725),  # panel 1: "Оригінал" (content starts at y=84, no gap to spare)
    "skeleton": (1480, 84, 2192, 725),  # panel 3: "Скелет 1px + pruning"
}
TRIPTYCH_CROPS = {
    "graph": (733, 143, 1345, 681),  # panel 2: "Граф изображения"
    "concept_2_1": (2104, 151, 2716, 673),  # panel 4: "Концепт 2_1"
    "concept_7_1": (2789, 143, 3402, 681),  # panel 5: "Концепт 7_1"
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

    row1_panels = [
        (_load_crop(stages_path, CONSTRUCTION_STAGES_CROPS["original"]), "1. Вхідне\nзображення"),
        (_load_crop(stages_path, CONSTRUCTION_STAGES_CROPS["skeleton"]), "2. Скелет\n(1 пкс)"),
        (_load_crop(triptych_path, TRIPTYCH_CROPS["graph"]), "3. Граф\nзображення"),
    ]
    row2_panels = [
        (_load_crop(triptych_path, TRIPTYCH_CROPS["concept_2_1"]), "4. Концепт 2_1\n(очікуваний)"),
        (_load_crop(triptych_path, TRIPTYCH_CROPS["concept_7_1"]), "5. Концепт 7_1\n(передбачений)"),
    ]

    # Layout in inches, laid out manually (rather than plt.subplots) so each
    # panel's axes exactly matches its crop's aspect ratio -- no letterboxed
    # blank space -- and row 2 can be capped below MAX_UPSCALE even though it
    # has fewer, and thus naturally wider, panels than row 1.
    fig_w_in = TEXT_WIDTH_CM * CM_TO_IN
    margin_left = margin_right = 0.12
    margin_top = 0.10
    margin_bottom = 0.08
    title_h = 0.46
    row_gap = 0.26
    legend_h = 0.42
    gap_x = 0.10
    title_fontsize = 12.5
    legend_fontsize = 9
    MAX_UPSCALE = 1.5

    usable_w = fig_w_in - margin_left - margin_right

    def natural_panel_w(n):
        return (usable_w - (n - 1) * gap_x) / n

    row1_w = natural_panel_w(len(row1_panels))
    row1_aspects = [img.shape[0] / img.shape[1] for img, _ in row1_panels]
    row1_h = max(row1_w * a for a in row1_aspects)

    native_w_row2 = [img.shape[1] for img, _ in row2_panels]
    cap_w_in = MAX_UPSCALE * min(native_w_row2) / DPI
    row2_w = min(natural_panel_w(len(row2_panels)), cap_w_in)
    row2_aspects = [img.shape[0] / img.shape[1] for img, _ in row2_panels]
    row2_h = max(row2_w * a for a in row2_aspects)

    fig_h_in = (
        margin_top + title_h + row1_h + row_gap + title_h + row2_h + legend_h + margin_bottom
    )

    fig = plt.figure(figsize=(fig_w_in, fig_h_in))

    def place_row(panels, panel_w, y_title_top, y_img_top, start_x):
        for i, (img, title) in enumerate(panels):
            aspect = img.shape[0] / img.shape[1]
            h = panel_w * aspect
            x = start_x + i * (panel_w + gap_x)
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
                linespacing=1.2,
            )

    y_title1_top = fig_h_in - margin_top
    y_row1_img_top = y_title1_top - title_h
    y_row1_img_bottom = y_row1_img_top - row1_h
    place_row(row1_panels, row1_w, y_title1_top, y_row1_img_top, margin_left)

    row2_content_w = len(row2_panels) * row2_w + (len(row2_panels) - 1) * gap_x
    start_x2 = margin_left + (usable_w - row2_content_w) / 2
    y_title2_top = y_row1_img_bottom - row_gap
    y_row2_img_top = y_title2_top - title_h
    y_row2_img_bottom = y_row2_img_top - row2_h
    place_row(row2_panels, row2_w, y_title2_top, y_row2_img_top, start_x2)

    fig.text(
        0.5,
        (y_row2_img_bottom - 0.04) / fig_h_in,
        "Позначення вузлів графа: StP — стартова точка; EnP — кінцева точка; "
        "CrP — кутова точка; IntP — точка перетину; H, V, Vec — горизонтальне,\n"
        "вертикальне ребро та вектор напрямку відповідно.",
        ha="center",
        va="top",
        fontsize=legend_fontsize,
    )

    upscale_row1 = [row1_w * DPI / img.shape[1] for img, _ in row1_panels]
    upscale_row2 = [row2_w * DPI / img.shape[1] for img, _ in row2_panels]
    print(
        f"[fig2] panel width row1={row1_w:.3f}in row2={row2_w:.3f}in "
        f"(cap={cap_w_in:.3f}in) | upscale row1={[f'{u:.2f}x' for u in upscale_row1]} "
        f"row2={[f'{u:.2f}x' for u in upscale_row2]}"
    )

    return _save(fig, "fig_trace.png")


# ---------------------------------------------------------------------------
# Fig 3 — confusion matrix
# ---------------------------------------------------------------------------

CLASSES = [str(i) for i in range(10)]


def _load_incorrect_rows():
    with open(RUN_DIR / "incorrect_results.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_support():
    with open(RUN_DIR / "per_class_metrics.csv", newline="", encoding="utf-8") as f:
        return {row["class"]: int(row["support"]) for row in csv.DictReader(f)}


def _build_confusion_matrix():
    rows = _load_incorrect_rows()
    support = _load_support()

    success_rows = [r for r in rows if r["status"] == "success"]
    not_classified = [
        r for r in success_rows if r["predicted"].strip().lower() in ("not classified", "none", "")
    ]
    misclassified = [r for r in success_rows if r not in not_classified]

    matrix = {c: {c2: 0 for c2 in CLASSES} for c in CLASSES}
    not_recognized = {c: 0 for c in CLASSES}

    for r in misclassified:
        matrix[r["expected"]][r["predicted"]] += 1
    for r in not_classified:
        not_recognized[r["expected"]] += 1

    for c in CLASSES:
        wrong_total = sum(matrix[c][c2] for c2 in CLASSES if c2 != c) + not_recognized[c]
        matrix[c][c] = support[c] - wrong_total

    return matrix, not_recognized, support


def build_fig3_confusion() -> Path:
    matrix, not_recognized, support = _build_confusion_matrix()

    grid = np.array([[matrix[c][c2] for c2 in CLASSES] for c in CLASSES])
    not_rec_col = np.array([not_recognized[c] for c in CLASSES])
    full = np.hstack([grid, not_rec_col[:, None]])

    total_sum = int(full.sum())
    diag_sum = int(np.trace(grid))
    accuracy = 100 * diag_sum / total_sum
    row_sums = full.sum(axis=1)
    support_arr = np.array([support[c] for c in CLASSES])
    assert np.array_equal(row_sums, support_arr), "row sums must equal per-class support"
    assert total_sum == sum(support.values()), "matrix total must equal total support"

    col_labels = CLASSES + ["Не\nрозпізнано"]

    fig_w_in = TEXT_WIDTH_CM * CM_TO_IN
    fig, ax = plt.subplots(figsize=(fig_w_in, fig_w_in * 0.78))

    # single light colormap; a mild power-law norm keeps small off-diagonal
    # counts visibly shaded instead of washing out next to the large diagonal.
    norm = PowerNorm(gamma=0.45, vmin=0, vmax=full.max())
    im = ax.imshow(full, cmap="Blues", norm=norm)

    for i in range(len(CLASSES)):
        for j in range(len(col_labels)):
            val = int(full[i, j])
            if val == 0:
                continue
            is_diag = j == i
            shade = norm(val)
            color = "white" if shade > 0.6 else "black"
            weight = "bold" if is_diag else "normal"
            ax.text(j, i, str(val), ha="center", va="center", fontsize=8, color=color, fontweight=weight)

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=8.5)
    ax.set_yticks(range(len(CLASSES)))
    ax.set_yticklabels(CLASSES, fontsize=8.5)
    ax.set_xlabel("Передбачений клас", fontsize=10)
    ax.set_ylabel("Справжній клас", fontsize=10)
    ax.set_xticks(np.arange(-0.5, len(col_labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(CLASSES), 1), minor=True)
    ax.grid(which="minor", color="lightgray", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    # separator before the "not recognized" column
    ax.axvline(len(CLASSES) - 0.5, color="black", linewidth=1.0)

    fig.tight_layout()

    print("--- Fig 3 validation ---")
    print(f"total matrix sum: {total_sum} (expected 8685: {total_sum == 8685})")
    print(f"diagonal sum: {diag_sum}")
    print(f"accuracy = diag_sum/total_sum = {accuracy:.4f}% (expected 91.13% +/-0.01)")
    print("row sums equal per-class support:", bool(np.array_equal(row_sums, support_arr)))

    return _save(fig, "fig_confusion.png")


if __name__ == "__main__":
    p1 = build_fig1_pipeline()
    print("wrote", p1)
    p2 = build_fig2_trace()
    if p2:
        print("wrote", p2)
    p3 = build_fig3_confusion()
    print("wrote", p3)
