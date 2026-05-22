"""Compose Fig 2 by combining the MNIST raster (left) with the drawio graph (right).

Two steps before running this:
    1. Ensure papers/itssi_paper_2026/figures/digit7_sample.png exists.
    2. Export the graph-only drawio panel WITHOUT -e flag (PIL cannot read
       embedded-XML PNGs):
         /Applications/draw.io.app/Contents/MacOS/draw.io \\
           -x -f png -b 20 --width 1700 \\
           -o /tmp/fig_2_graph_half_clean.png \\
           fig_2_digit7_graph.drawio

Then run this script with the venv interpreter:
    natural-agi/bin/python papers/itssi_paper_2026/figures/compose_fig_2.py
"""
from pathlib import Path

from PIL import Image
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
LEFT = HERE / "digit7_sample.png"
RIGHT = Path("/tmp/fig_2_graph_half_clean.png")
OUT = HERE / "fig_2_digit7_graph.png"


def main() -> None:
    if not LEFT.exists():
        raise SystemExit(f"missing {LEFT}")
    if not RIGHT.exists():
        raise SystemExit(
            f"missing {RIGHT} — export the graph half via drawio CLI first"
        )

    fig, axes = plt.subplots(1, 2, figsize=(14, 7.2), dpi=300)

    left = Image.open(LEFT)
    right = Image.open(RIGHT)

    axes[0].imshow(left, cmap="gray", interpolation="nearest", vmin=0, vmax=255)
    axes[0].set_title(
        "Input image (100×100, grayscale)",
        fontsize=14,
        family="serif",
        pad=12,
    )
    axes[0].set_xlabel(
        f"{LEFT.name}  (structure = complete)",
        fontsize=10,
        family="monospace",
        color="#444",
    )
    axes[0].set_xticks([])
    axes[0].set_yticks([])
    for spine in axes[0].spines.values():
        spine.set_edgecolor("#999")
        spine.set_linewidth(1.0)

    axes[1].imshow(right, interpolation="lanczos")
    axes[1].set_title(
        "Skeleton graph  Point  /  Vector  (normalised coordinates)",
        fontsize=14,
        family="serif",
        pad=12,
    )
    axes[1].set_xlabel(
        "Vector panel  (.drawio  →  Visio  .vsdx)",
        fontsize=10,
        family="monospace",
        color="#444",
    )
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    for spine in axes[1].spines.values():
        spine.set_edgecolor("#999")
        spine.set_linewidth(1.0)

    fig.tight_layout()
    fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
