"""Word version of experiments/fewshot_band_concepts_2026-10/report.md, with diagrams and real system output.

Text and tables come from report.md (one source for both versions); the figures are drawn here from the
dumps and CSVs of pl_report.py, the stored band model (Neo4j) and the production skeletonisation / feature /
scoring code run on test images.

Usage: pl_report_docx.py [--figures-only]
  -> experiments/fewshot_band_concepts_2026-10/report.docx; figures in tests/_fewshot_ref/report_figures/
Needs Neo4j (band model fs_final_B10 and the :GraphFeatures of the final-emnist run).
"""
import csv
import json
import os
import re
import sys
import warnings
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "experiments" / "fewshot_band_concepts_2026-10"
REF = REPO / "tests" / "_fewshot_ref"
FIG = REF / "report_figures"
OUT = EXP / "report.docx"
TEST = REPO / "tests" / "emnist_testfull"
CAND = REPO / "tests" / "emnist_cand60"
CAND_SEL = REPO / "tests" / "emnist_cand60_sel"
MODEL_ID = "fs_final_B10"
EXAMPLE = "D_full0048"
NEO4J = ("bolt://localhost:7687", ("neo4j", "111122223333"))

os.environ.update(KAFKA_TOPIC="-", DLQ_TOPIC="-", KAFKA_BOOTSTRAP_SERVERS="-")
sys.path.insert(0, str(REPO / "src" / "skeletonization"))
sys.path.insert(0, str(REPO / "src"))
from settings import Settings  # noqa: E402
from skeleton_gng_mapper import SkeletonGNGMapper  # noqa: E402
from dense_features import dense_representation  # noqa: E402

sys.path += [str(REPO / "src" / "contour_analysis" / "logic"), str(REPO / "src" / "classification")]
from direction_map import compute_direction_map, dim_schema, _deslanted_xy, _edge_samples  # noqa: E402
from band.band_model import BandModel  # noqa: E402
from band.band_repository import _shape, get_image_feature_set, get_image_shape  # noqa: E402
from band.band_scorer import score_letters_committee  # noqa: E402
from band.shape_context import POSITION_WEIGHT, distances, letter_distance, shape_context  # noqa: E402

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------- design tokens (figures and document)
INK, MUTED, LINE, FILL, BAND = "#1C2733", "#5B6775", "#C9D3DE", "#EEF3F8", "#F6F8FB"
AFTER, AFTER_DARK, AFTER_LIGHT = "#1A5A96", "#0F3A63", "#8DB2D6"
BEFORE, HIGHLIGHT, GOOD = "#9AA5B1", "#C8691C", "#2E7D4F"
CM = 1 / 2.54
plt.rcParams.update({
    "font.family": ["PT Sans", "Arial Unicode MS"], "font.size": 8.5, "text.color": INK, "axes.labelcolor": INK,
    "axes.edgecolor": LINE, "xtick.color": MUTED, "ytick.color": INK, "axes.titlesize": 9,
    "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "savefig.dpi": 220, "figure.facecolor": "white", "savefig.facecolor": "white",
})
CMAP = LinearSegmentedColormap.from_list("doc", ["#FFFFFF", "#DCE8F4", "#8DB2D6", AFTER, AFTER_DARK])
LETTERS = [chr(65 + i) for i in range(26)]


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return path


def _clean(ax, left=False):
    for side in ("top", "right") + (("left",) if not left else ()):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)


def _glyph(path):
    """Test / candidate PNG (white ink on black) -> dark ink on white for display."""
    return 255 - cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)


def _thumb(ax, path, frame=None, alpha=1.0):
    ax.imshow(_glyph(path), cmap="gray", vmin=0, vmax=255, alpha=alpha)
    ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(frame is not None)
        if frame:
            s.set_edgecolor(frame), s.set_linewidth(1.6)


def _dump(name):
    return [json.loads(line) for line in open(REF / name)]


def _csv(name):
    return list(csv.reader(open(EXP / name)))


# ---------------------------------------------------------------- figures: results
def fig_headline():
    rows = [("EMNIST-letters, top-1", 50.87, 84.61), ("EMNIST-letters, top-3", 70.04, 96.45),
            ("MNIST complete, top-1", 90.90, 97.44)]
    fig, ax = plt.subplots(figsize=(16 * CM, 4.3 * CM))
    for i, (label, b, a) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([b, a], [y, y], color=LINE, lw=3.2, zorder=1, solid_capstyle="round")
        ax.scatter([b], [y], s=48, color=BEFORE, zorder=2)
        ax.scatter([a], [y], s=64, color=AFTER, zorder=3)
        ax.text(b - 1.3, y, f"{b:.1f}", ha="right", va="center", color=MUTED)
        ax.text(a + 1.3, y, f"{a:.1f}", ha="left", va="center", color=AFTER_DARK, fontweight="bold")
        ax.text(107, y, f"+{a - b:.1f} п.п.", ha="left", va="center", color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1])
    ax.set_xlim(38, 116), ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks(range(40, 101, 10))
    ax.set_xlabel("точність, % від усіх зображень тесту", color=MUTED)
    ax.grid(axis="x", color=LINE, lw=0.5, alpha=0.6)
    _clean(ax)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=BEFORE, label="до"),
                       Line2D([], [], marker="o", ls="", color=AFTER, label="після")],
              loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, frameon=False, handletextpad=0.2)
    return _save(fig, "headline")


CHRONO = [
    ("база: fold-концепти", 51.15, 70.42), ("смугові концепти", 68.71, 89.98), ("аугментація", 70.55, 90.71),
    ("кривина, кінці", 73.11, 91.69), ("вага центру, поріг 170", 74.27, 92.83), ("вибір оригіналів", 76.15, 93.66),
    ("комітет скелетів", 78.55, 94.44), ("k-medoids ×12", 79.88, 94.88), ("правило стійки", 80.17, 94.93),
    ("щільна лінія + тур 2", 81.31, 95.70), ("без нахилу", 82.77, 96.20), ("моменти, топології", 84.77, 96.39),
    ("з'єднання частин*", 84.53, 96.45), ("концепт форми*", 84.61, 96.45), ("після прибирання*", 84.61, 96.45),
]


def fig_chronology():
    fig, ax = plt.subplots(figsize=(16 * CM, 7.6 * CM))
    x = np.arange(len(CHRONO))
    t1 = np.array([r[1] for r in CHRONO])
    t3 = np.array([r[2] for r in CHRONO])
    ax.plot(x, t3, color=AFTER_LIGHT, lw=1.6, marker="o", ms=3.5, label="top-3")
    ax.plot(x, t1, color=AFTER, lw=2.0, marker="o", ms=4.5, label="top-1")
    for i, v in enumerate(t1):
        below = i == 0
        ax.text(i, v - 2.2 if below else v + 1.4, f"{v + 1e-9:.1f}", ha="center", va="top" if below else "bottom",
                fontsize=7, color=AFTER_DARK)
    ax.text(len(x) - 0.6, t1[-1], "top-1", va="center", color=AFTER, fontweight="bold")
    ax.text(len(x) - 0.6, t3[-1], "top-3", va="center", color=AFTER_LIGHT, fontweight="bold")
    ax.axvspan(11.5, 14.5, color=BAND, zorder=0)
    ax.text(13, 52, "* від усіх 20 800", ha="center", fontsize=7, color=MUTED)
    ax.set_xticks(x, [f"{i}  {r[0]}" for i, r in enumerate(CHRONO)], rotation=45, ha="right", rotation_mode="anchor", fontsize=7.2)
    ax.set_ylim(45, 100), ax.set_xlim(-0.5, len(x) + 0.4)
    ax.set_ylabel("точність, %", color=MUTED)
    ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
    _clean(ax)
    return _save(fig, "chronology")


def fig_ablation():
    rows = list(csv.DictReader(open(EXP / "ablation.csv")))
    labels = ["1 скелет, тур 1", "3 скелети, тур 1", "1 скелет, тури 1 + 2", "3 скелети, тури 1 + 2 = фінал"]
    fig, axes = plt.subplots(1, 2, figsize=(16 * CM, 4.6 * CM), sharey=True)
    for ax, ds, lim in zip(axes, ("EMNIST", "MNIST"), ((81.6, 85.4), (95.0, 98.0))):
        vals = [float(r["top1"]) for r in rows if r["dataset"] == ds]
        y = np.arange(len(vals))[::-1]
        for yi, v, i in zip(y, vals, range(len(vals))):
            final = i == len(vals) - 1
            ax.plot([lim[0], v], [yi, yi], color=LINE, lw=1, zorder=1)
            ax.scatter([v], [yi], s=60 if final else 42, color=AFTER_DARK if final else AFTER, zorder=2)
            ax.text(v + (lim[1] - lim[0]) * 0.03, yi, f"{v:.2f}", va="center", fontsize=8,
                    fontweight="bold" if final else "normal", color=AFTER_DARK if final else INK)
        ax.set_xlim(*lim)
        ax.set_title(f"{ds}, top-1 %")
        ax.grid(axis="x", color=LINE, lw=0.5, alpha=0.6)
        _clean(ax)
    axes[0].set_yticks(np.arange(len(labels))[::-1], labels)
    fig.tight_layout(w_pad=2.5)
    return _save(fig, "ablation")


def fig_confusion(csv_name, title, name, threshold, size):
    rows = _csv(csv_name)
    cols = rows[0][1:]
    truth = [r[0] for r in rows[1:]]
    m = np.array([[float(v or 0) for v in r[1:]] for r in rows[1:]])
    share = m / np.maximum(m.sum(1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=size)
    ax.imshow(share, cmap=CMAP, vmin=0, vmax=1, aspect="auto")
    small = len(truth) > 12
    for i in range(len(truth)):
        for j in range(len(cols)):
            v = int(m[i, j])
            if v and (cols[j] == truth[i] or v >= threshold):
                ax.text(j, i, v, ha="center", va="center", fontsize=5.6 if small else 7.5,
                        color="white" if share[i, j] > 0.5 else INK)
    ax.set_xticks(range(len(cols)), cols), ax.set_yticks(range(len(truth)), truth)
    ax.tick_params(length=0, labelsize=7 if small else 8.5)
    ax.xaxis.set_ticks_position("top")
    ax.set_xlabel("відповідь системи", color=MUTED), ax.set_ylabel("правильний клас", color=MUTED)
    ax.xaxis.set_label_position("top")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, pad=22 if small else 18, loc="left")
    return _save(fig, name)


def fig_confusion_mnist():
    parts = []
    for csv_name, title in (("confusion_mnist_baseline.csv", "До: fold-концепти + GED · 90.9 %"),
                            ("confusion_mnist_final.csv", "Після: смугові концепти + концепти форми · 97.4 %")):
        rows = _csv(csv_name)
        parts.append((rows[0][1:], [r[0] for r in rows[1:]],
                      np.array([[float(v or 0) for v in r[1:]] for r in rows[1:]]), title))
    fig, axes = plt.subplots(1, 2, figsize=(16 * CM, 8.2 * CM), gridspec_kw={"width_ratios": [11, 10]})
    for ax, (cols, truth, m, title) in zip(axes, parts):
        share = m / np.maximum(m.sum(1, keepdims=True), 1)
        ax.imshow(share, cmap=CMAP, vmin=0, vmax=1)
        for i in range(len(truth)):
            for j in range(len(cols)):
                v = int(m[i, j])
                if v and (cols[j] == truth[i] or v >= 3):
                    ax.text(j, i, v, ha="center", va="center", fontsize=6.4,
                            color="white" if share[i, j] > 0.5 else INK)
        ax.set_xticks(range(len(cols)), cols), ax.set_yticks(range(len(truth)), truth)
        ax.tick_params(length=0, labelsize=8)
        ax.xaxis.set_ticks_position("top")
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(title, pad=16, fontsize=8.5)
    axes[0].set_ylabel("правильна цифра", color=MUTED)
    fig.tight_layout(w_pad=1.5)
    return _save(fig, "confusion_mnist")


def _dumbbell(ax, labels, before, after, title):
    y = np.arange(len(labels))[::-1]
    for yi, b, a in zip(y, before, after):
        ax.plot([b, a], [yi, yi], color=HIGHLIGHT if a < b else LINE, lw=1.6, zorder=1)
        ax.scatter([b], [yi], s=16, color=BEFORE, zorder=2)
        ax.scatter([a], [yi], s=22, color=AFTER, zorder=3)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 101), ax.set_ylim(-0.7, len(labels) - 0.3)
    ax.set_title(title)
    ax.grid(axis="x", color=LINE, lw=0.5, alpha=0.6)
    _clean(ax)


def fig_perclass(csv_name, name, height):
    rows = list(csv.DictReader(open(EXP / csv_name)))
    cls = sorted({r["class"] for r in rows})
    val = {(r["system"], r["class"], k): float(r[k]) for r in rows for k in ("recall", "precision")}

    def col(system, k):
        return [val[(system, c, k)] for c in cls]

    fig, axes = plt.subplots(1, 2, figsize=(16 * CM, height * CM), sharey=True)
    _dumbbell(axes[0], cls, col("baseline", "recall"), col("final", "recall"), "Recall, %")
    _dumbbell(axes[1], cls, col("baseline", "precision"), col("final", "precision"), "Precision, %")
    axes[1].legend(handles=[Line2D([], [], marker="o", ls="", color=BEFORE, label="до"),
                            Line2D([], [], marker="o", ls="", color=AFTER, label="після"),
                            Line2D([], [], color=HIGHLIGHT, lw=1.6, label="знизився")],
                   loc="lower left", frameon=False, fontsize=7.5, handletextpad=0.3)
    fig.tight_layout(w_pad=1.5)
    return _save(fig, name)


def _top_pairs(dump, k=10):
    from collections import Counter
    pairs = Counter()
    for r in dump:
        p = r["pred"] if r["pred"] not in (None, "none") else None
        if p and p != r["true"]:
            pairs["↔".join(sorted((r["true"], p)))] += 1
    return pairs.most_common(k)


def fig_pairs():
    before, after = _top_pairs(_dump("baseline_emnist.jsonl")), _top_pairs(_dump("final_emnist.jsonl"))
    fig, axes = plt.subplots(1, 2, figsize=(16 * CM, 6.0 * CM), sharex=True)
    for ax, pairs, color, title in ((axes[0], before, BEFORE, "До: 10 220 помилок"),
                                    (axes[1], after, AFTER, "Після: 3 201 помилка")):
        y = np.arange(len(pairs))[::-1]
        ax.barh(y, [c for _, c in pairs], color=color, height=0.68)
        for yi, (_, c) in zip(y, pairs):
            ax.text(c + 8, yi, c, va="center", fontsize=7.5, color=INK)
        ax.set_yticks(y, [p.replace("↔", " ↔ ") for p, _ in pairs])
        ax.set_title(title)
        ax.set_xlim(0, 700)
        ax.grid(axis="x", color=LINE, lw=0.5, alpha=0.6)
        _clean(ax)
    axes[0].set_xlabel("помилок (обидва напрямки)", color=MUTED)
    fig.tight_layout(w_pad=2)
    return _save(fig, "pairs")


def fig_errors():
    dump = _dump("final_emnist.jsonl")
    rows = [("I", "L"), ("L", "I"), ("G", "Q"), ("Q", "G"), ("V", "U"), ("O", "D"), ("Q", "A"), ("N", "H")]
    per = 10
    fig, axes = plt.subplots(len(rows), per + 1, figsize=(16 * CM, len(rows) * 1.45 * CM),
                             gridspec_kw={"width_ratios": [2.2] + [1] * per})
    for i, (t, p) in enumerate(rows):
        hits = sorted((r["path"] for r in dump if r["true"] == t and r["pred"] == p), key=lambda s: Path(s).name)
        axes[i, 0].axis("off")
        axes[i, 0].text(0.0, 0.5, f"{t} → {p}", fontsize=10, fontweight="bold", va="center", color=INK)
        axes[i, 0].text(0.0, 0.12, f"{len(hits)} зобр.", fontsize=7, va="center", color=MUTED)
        for j in range(per):
            ax = axes[i, j + 1]
            if j < len(hits):
                _thumb(ax, TEST / t / Path(hits[j]).name)
            else:
                ax.axis("off")
    fig.subplots_adjust(wspace=0.08, hspace=0.12)
    return _save(fig, "errors")


# ---------------------------------------------------------------- figures: how the system works
def _box(ax, x, y, w, h, title, body="", fc=FILL, ec=LINE, tc=INK, bc=MUTED):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=0.8))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=8.2, fontweight="bold", color=tc)
    if body:
        ax.text(x + w / 2, y + h - 0.62, body, ha="center", va="top", fontsize=6.8, color=bc, linespacing=1.3)


def _arrow(ax, x0, y0, x1, y1, color=MUTED):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=0.9, mutation_scale=9, shrinkA=0, shrinkB=0))


def _canvas(h):
    fig, ax = plt.subplots(figsize=(16 * CM, h * CM))
    ax.set_xlim(0, 16), ax.set_ylim(0, h), ax.set_aspect("equal"), ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def fig_pipeline_before():
    fig, ax = _canvas(5.1)
    top, h = 2.6, 2.45
    boxes = [(0.0, 2.3, "Зображення", "100 × 100,\nсірі тони"),
             (2.75, 2.9, "Скелет", "бінаризація,\nстоншення, GNG,\nспрощення RDP →\nграф 5–15 вузлів"),
             (6.1, 3.0, "Контурний аналіз", "ознаки вузлів:\nкоординати, кути,\nнапрямки, цикли"),
             (9.55, 3.2, "Порівняння графів", "граф зображення\nз кожним із\n91 fold-концепту:\nGED / direct_bridge"),
             (13.2, 2.8, "Рішення", "калібрування\nза «фоном»\nконцепту →\nнайкращий клас")]
    for i, (x, w, t, b) in enumerate(boxes):
        last = i == len(boxes) - 1
        _box(ax, x, top, w, h, t, b, fc=BEFORE if last else FILL, tc="white" if last else INK,
             bc="white" if last else MUTED)
        if i:
            px, pw = boxes[i - 1][0], boxes[i - 1][1]
            _arrow(ax, px + pw + 0.04, top + h / 2, x - 0.04, top + h / 2)
    _box(ax, 6.1, 0.05, 6.65, 1.95, "Fold-концепт літери (Neo4j)",
         "спільний мінор, тобто перетин графів навчальних зразків;\nсмуги ознак вузлів = мінімум … максимум;\n"
         "на EMNIST — кілька концептів на літеру", fc="white")
    _arrow(ax, 11.15, 2.04, 11.15, top - 0.04)
    return _save(fig, "pipeline_before")


def fig_pipeline_after():
    fig, ax = _canvas(8.2)
    w, gap = 3.6, (16 - 4 * 3.6) / 3
    xs = [i * (w + gap) for i in range(4)]
    y1, h1 = 5.75, 2.4
    top = [("Зображення", "100 × 100, сірі тони;\nодне на вході"),
           ("Комітет із 3 скелетів", "бінаризація 110 / 150 / 190;\nтовсті штрихи — поріг 170;\n"
                                    "правило стійки в перехресті;\nз'єднання частин"),
           ("Ознаки: 193 числа", "карта напрямків 2×2 і 3×3,\nкінці, перехрестя, цикли,\n"
                                 "кривина, напрямки кінців,\nорієнтації щільної лінії"),
           ("Щільна лінія", "32 точки центральної лінії\nі напрямок дотичної\nв кожній (до спрощення\nграфа)")]
    for i, (t, b) in enumerate(top):
        _box(ax, xs[i], y1, w, h1, t, b)
        if i:
            _arrow(ax, xs[i - 1] + w + 0.04, y1 + h1 / 2, xs[i] - 0.04, y1 + h1 / 2)
    y2, h2 = 2.7, 2.1
    _box(ax, xs[0], y2, 5.0, h2, "Тур 1 — усі 26 літер",
         "смугові концепти: ½ найкращий лист\n+ ½ корінь літери; середнє\nпо 3 скелетах → п'ятірка",
         fc="white", ec=AFTER)
    _box(ax, 5.6, y2 + 0.35, 1.5, 1.4, "топ-5", "", fc=FILL, ec=AFTER)
    _box(ax, 7.7, y2, 4.6, h2, "Тур 2 — тільки п'ятірка",
         "точки лінії ↔ опорні точки\nконцептів форми листків;\nсума з туром 1 (1 : 1)", fc="white", ec=AFTER)
    _box(ax, 12.9, y2, 3.1, h2, "Відповідь", "+ пояснення:\nпорушені виміри,\nпари точка ↔ опорна\nточка",
         fc=AFTER, ec=AFTER, tc="white", bc="white")
    _arrow(ax, 5.04, y2 + h2 / 2, 5.56, y2 + h2 / 2), _arrow(ax, 7.14, y2 + h2 / 2, 7.66, y2 + h2 / 2)
    _arrow(ax, 12.34, y2 + h2 / 2, 12.86, y2 + h2 / 2)
    _arrow(ax, xs[2] + w / 2, y1 - 0.04, 2.5, y2 + h2 + 0.04)
    _arrow(ax, xs[3] + w / 2, y1 - 0.04, 10.0, y2 + h2 + 0.04)
    _box(ax, 0.0, 0.0, 12.3, 2.0, "Концепти в Neo4j: BandModel → 26 коренів → 260 листків",
         "лист = один оригінал + 10 аугментацій: смуги 193 ознак (10-й … 90-й перцентиль і центр)\n"
         "та концепт форми (32 опорні точки: положення, допуск, оточення, напрямок);\n"
         "корінь = смуги всіх листків літери. Окремі зразки не зберігаються.", fc=BAND)
    _arrow(ax, 2.5, 2.04, 2.5, y2 - 0.04), _arrow(ax, 10.0, 2.04, 10.0, y2 - 0.04)
    return _save(fig, "pipeline_after")


def _skeletons(img):
    out = []
    for thr in (110, 150, 190):
        mapper = SkeletonGNGMapper(Settings(), thr, 4.55, thick_stroke_threshold=170,
                                   bridge_protect_stems=True, bridge_components=True)
        graph, used = mapper.process_image(img)
        out.append((thr, used, graph, mapper.last_skeleton, mapper.binary_image(img, used)))
    return out


def _draw_graph(ax, graph, xy=None, ms=1.0):
    xy = xy if xy is not None else {n: (d["x"], d["y"]) for n, d in graph.nodes(data=True)}
    for u, v in graph.edges():
        ax.plot([xy[u][0], xy[v][0]], [xy[u][1], xy[v][1]], color=AFTER, lw=1.4 * ms, zorder=2)
    for n in graph.nodes:
        deg = graph.degree(n)
        if deg == 1:
            ax.scatter(*xy[n], s=26 * ms, color=HIGHLIGHT, zorder=3, edgecolor="white", linewidth=0.5)
        elif deg >= 3:
            ax.scatter(*xy[n], s=30 * ms, marker="s", color=AFTER_DARK, zorder=3, edgecolor="white", linewidth=0.5)
        else:
            ax.scatter(*xy[n], s=8 * ms, color=AFTER, zorder=3)


def fig_processing(name=EXAMPLE):
    img = cv2.imread(str(TEST / name[0] / f"{name}.png"), cv2.IMREAD_GRAYSCALE)
    sk = _skeletons(img)
    dense = dense_representation(sk[0][3], deslant=True, normalisation="moment", moment_range=1.7)
    fig, axes = plt.subplots(1, 5, figsize=(16 * CM, 4.0 * CM))
    _thumb(axes[0], TEST / name[0] / f"{name}.png", frame=LINE)
    axes[0].set_title("а) зображення", fontsize=8)
    for ax, (thr, used, graph, skel, binary), letter in zip(axes[1:4], sk, "бвг"):
        ax.imshow(np.where(binary > 0, 0.86, 1.0), cmap="gray", vmin=0, vmax=1)
        ys, xs = np.nonzero(skel)
        ax.scatter(xs, ys, s=0.6, color=MUTED, zorder=1)
        _draw_graph(ax, graph)
        label = f"{letter}) поріг {thr}" + (f" → {used}" if used != thr else "")
        ax.set_title(label, fontsize=8)
        ax.set_xlim(0, 99), ax.set_ylim(99, 0), ax.set_xticks([]), ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor(LINE)
    ax = axes[4]
    p = np.array(dense["points"]).reshape(-1, 2)
    t = np.array(dense["tangents"]).reshape(-1, 2)
    for (px, py), (tx, ty) in zip(p, t):
        ax.plot([px - 0.045 * tx, px + 0.045 * tx], [py - 0.045 * ty, py + 0.045 * ty], color=AFTER, lw=1.2)
    ax.scatter(p[:, 0], p[:, 1], s=7, color=HIGHLIGHT, zorder=3)
    ax.set_xlim(-0.05, 1.05), ax.set_ylim(1.05, -0.05), ax.set_aspect("equal")
    ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor(LINE)
    ax.set_title("д) 32 точки лінії", fontsize=8)
    fig.tight_layout(w_pad=0.6)
    return _save(fig, "processing")


ORI = [0, 45, 90, 135]          # orientation bins, image coordinates (y down)


def _unit_coords(graph):
    ids = list(graph.nodes)
    xy = np.array([[graph.nodes[n]["x"], graph.nodes[n]["y"]] for n in ids], float)
    xy = _deslanted_xy(graph, ids, xy)
    samples = _edge_samples(graph, ids, xy)
    extent = np.maximum(xy.max(0) - xy.min(0), 1e-6)
    half = np.maximum(1.7 * np.maximum(samples.std(0), 1e-6), 0.02 * float(extent.max()))
    unit = np.clip((xy - (samples.mean(0) - half)) / (2 * half), 0, 1)
    return {n: tuple(u) for n, u in zip(ids, unit)}


def _orientation_glyphs(ax, values, grid=3, color=AFTER_DARK):
    vmax = max(values.max(), 1e-9)
    for c in range(grid * grid):
        cx, cy = (c % grid + 0.5) / grid, (c // grid + 0.5) / grid
        for b, deg in enumerate(ORI):
            ln = 0.42 / grid * values[c * 4 + b] / vmax
            if ln < 0.01:
                continue
            dx, dy = np.cos(np.radians(deg)) * ln, np.sin(np.radians(deg)) * ln
            ax.plot([cx - dx, cx + dx], [cy - dy, cy + dy], color=color, lw=2.4, solid_capstyle="round", zorder=4)


def _grid(ax, grid=3):
    for k in range(1, grid):
        ax.axvline(k / grid, color=LINE, lw=0.8, zorder=0), ax.axhline(k / grid, color=LINE, lw=0.8, zorder=0)
    ax.set_xlim(0, 1), ax.set_ylim(1, 0), ax.set_aspect("equal"), ax.set_xticks([]), ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor(LINE)


def fig_features(name=EXAMPLE):
    img = cv2.imread(str(TEST / name[0] / f"{name}.png"), cv2.IMREAD_GRAYSCALE)
    thr, used, graph, skel, _ = _skeletons(img)[0]
    names, blocks, _ = dim_schema()
    dm = compute_direction_map(graph, deslant=True, normalisation="moment", moment_range=1.7)
    dense = dense_representation(skel, deslant=True, normalisation="moment", moment_range=1.7)
    g3 = np.array([dm[i] for i, n in enumerate(names) if n.startswith("g3.orient")])
    d3 = np.array(dense["orient"][16:])
    fig = plt.figure(figsize=(16 * CM, 7.4 * CM))
    gs = fig.add_gridspec(2, 2, height_ratios=[5.2, 1.0], hspace=0.45, wspace=0.12)
    ax = fig.add_subplot(gs[0, 0])
    unit = _unit_coords(graph)
    for u, v in graph.edges():
        ax.plot([unit[u][0], unit[v][0]], [unit[u][1], unit[v][1]], color=AFTER_LIGHT, lw=3, zorder=1)
    _orientation_glyphs(ax, g3)
    for n in graph.nodes:
        if graph.degree(n) == 1:
            nb = next(iter(graph.neighbors(n)))
            d = np.subtract(unit[n], unit[nb])
            d = d / max(np.linalg.norm(d), 1e-9) * 0.09
            ax.annotate("", xy=(unit[n][0] + d[0], unit[n][1] + d[1]), xytext=unit[n],
                        arrowprops=dict(arrowstyle="-|>", color=HIGHLIGHT, lw=1.2, mutation_scale=8), zorder=5)
            ax.scatter(*unit[n], s=26, color=HIGHLIGHT, zorder=5, edgecolor="white", linewidth=0.5)
        elif graph.degree(n) >= 3:
            ax.scatter(*unit[n], s=30, marker="s", color=AFTER_DARK, zorder=5, edgecolor="white", linewidth=0.5)
    _grid(ax)
    ax.set_title("а) скелетний граф: напрямки в клітинках 3 × 3,\n    кінці (зі стрілкою напрямку), перехрестя", fontsize=8)
    ax = fig.add_subplot(gs[0, 1])
    ys, xs = np.nonzero(skel)
    pts = np.stack([xs, ys], 1).astype(float)
    c = pts - pts.mean(0)
    mu02 = float((c[:, 1] ** 2).mean())
    shear = float(np.clip((c[:, 0] * c[:, 1]).mean() / mu02, -1, 1)) if mu02 > 1e-9 else 0.0
    pts[:, 0] -= shear * c[:, 1]
    half = 1.7 * np.maximum(pts.std(0), 1e-6)
    upts = np.clip((pts - (pts.mean(0) - half)) / (2 * half), 0, 1)
    ax.scatter(upts[:, 0], upts[:, 1], s=1.5, color=AFTER_LIGHT, zorder=1)
    _orientation_glyphs(ax, d3)
    _grid(ax)
    ax.set_title("б) щільна центральна лінія (до спрощення графа):\n    той самий блок напрямків", fontsize=8)
    ax = fig.add_subplot(gs[1, :])
    comp = [("напрямки графа", 52), ("кінці, перехрестя", 26), ("загальні", 5), ("кривина", 26),
            ("напрямки кінців", 32), ("напрямки щільної лінії", 52)]
    colors = [AFTER_DARK, AFTER, BEFORE, AFTER_LIGHT, HIGHLIGHT, "#5E87B0"]
    left = 0
    for (label, n), col in zip(comp, colors):
        ax.barh(0, n, left=left, color=col, height=0.8, edgecolor="white", linewidth=1.5)
        ax.text(left + n / 2, 0, str(n), ha="center", va="center", color="white", fontsize=7.5, fontweight="bold")
        ax.text(left + n / 2, -0.75 if n >= 10 else 0.75, label, ha="center", va="top" if n >= 10 else "bottom",
                fontsize=6.8, color=INK)
        left += n
    ax.set_xlim(0, 193), ax.set_ylim(-1.6, 1.5), ax.axis("off")
    ax.set_title("в) з чого складаються 193 числа опису", fontsize=8)
    return _save(fig, "features")


def _driver():
    from neo4j import GraphDatabase
    return GraphDatabase.driver(NEO4J[0], auth=NEO4J[1])


def load_model(driver, model_id=MODEL_ID):
    """band_repository.load_band_models restricted to one model (that one loads every stored model)."""
    with driver.session() as session:
        m = session.run("MATCH (m:BandModel {model_id: $id}) RETURN properties(m) AS m", id=model_id).single()["m"]
        rows = session.run(
            "MATCH (:BandModel {model_id: $id})-[:HAS_CONCEPT]->(c:BandConcept) "
            "RETURN c.band_id AS band_id, c.letter AS letter, c.form AS form, c.role AS role, c.lo AS lo, "
            "c.hi AS hi, c.centre AS centre, c.shape_mu AS shape_mu, c.shape_tan AS shape_tan, "
            "c.shape_hist AS shape_hist, c.shape_tol AS shape_tol ORDER BY c.band_id", id=model_id).data()
    model = BandModel(
        model_id=model_id, dm_version=m["dm_version"], dim_names=list(m["dim_names"]), weights=m["weights"],
        scale=m["scale"], band_ids=[r["band_id"] for r in rows], letters=[r["letter"] for r in rows],
        forms=[r["form"] for r in rows], roles=[r["role"] for r in rows], lo=[r["lo"] for r in rows],
        hi=[r["hi"] for r in rows], centre=[r["centre"] for r in rows], alpha=float(m["alpha"]),
        leaf_weight=float(m["leaf_weight"]), root_weight=float(m["root_weight"]),
        shape_points=[_shape(r["shape_mu"]) for r in rows], shape_tangents=[_shape(r["shape_tan"]) for r in rows],
        stage2_lambda=float(m["stage2_lambda"]), stage2_topk=int(m["stage2_topk"]), stage2_beta=float(m["stage2_beta"]))
    model.shape_contexts = [None if sp is None or not r["shape_hist"]
                            else np.array(r["shape_hist"], np.float32).reshape(len(sp), sp.shape[1], -1)
                            for r, sp in zip(rows, model.shape_points)]
    model.shape_tol = [None if not r["shape_tol"] else np.array(r["shape_tol"], float) for r in rows]
    return model


def _image_id(name):
    for line in open(REF / "final_emnist.jsonl"):
        if f"/{name}.png" in line:
            return json.loads(line)["image_id"]
    raise KeyError(name)


def fig_concept_tree(driver, letter="D", leaf="D_b042"):
    with driver.session() as s:
        leaves = [r["b"] for r in s.run(
            "MATCH (r:BandConcept {model_id: $m, role: 'root', letter: $l})-[:GENERALISES]->(c) "
            "RETURN c.band_id AS b ORDER BY b", m=MODEL_ID, l=letter).data()]
    originals = [b.split("_", 1)[1] for b in leaves]
    fig = plt.figure(figsize=(16 * CM, 7.6 * CM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16), ax.set_ylim(0, 7.6), ax.axis("off")
    _box(ax, 5.3, 6.55, 5.4, 0.9, f"BandModel {MODEL_ID}", "", fc=FILL)
    _box(ax, 5.3, 5.0, 5.4, 1.15, f"корінь {letter}", f"смуги всіх {len(leaves)} листків літери", fc="white", ec=AFTER)
    _arrow(ax, 8.0, 6.53, 8.0, 6.18)
    ax.text(8.15, 6.36, "HAS_CONCEPT", fontsize=6, color=MUTED, va="center")
    n = len(originals)
    size, gap = 1.06, 0.12
    x0 = (16 - n * size - (n - 1) * gap) / 2
    for i, o in enumerate(originals):
        x = x0 + i * (size + gap)
        _arrow(ax, 8.0, 4.98, x + size / 2, 4.02, color=LINE)
        sub = fig.add_axes([x / 16, 2.95 / 7.6, size / 16, size / 7.6])
        _thumb(sub, CAND / letter / f"{o}.png", frame=HIGHLIGHT if o == leaf else LINE)
        ax.text(x + size / 2, 2.78, o.split("_")[1], ha="center", va="top", fontsize=5.6,
                color=HIGHLIGHT if o == leaf else MUTED)
    ax.text(8.15, 4.55, "GENERALISES", fontsize=6, color=MUTED, va="center")
    ax.text(0.1, 1.95, f"лист {leaf}:", fontsize=8, fontweight="bold", color=INK, va="center")
    ax.text(0.1, 1.55, "оригінал +\n10 аугментацій", fontsize=6.8, color=MUTED, va="top")
    augs = [CAND_SEL / letter / f"{leaf}.png"] + [CAND_SEL / letter / f"{leaf}_aug{k}.png" for k in range(1, 11)]
    for i, p in enumerate(augs):
        sub = fig.add_axes([(2.35 + i * 1.2) / 16, 0.65 / 7.6, 1.08 / 16, 1.08 / 7.6])
        _thumb(sub, p, frame=HIGHLIGHT if i == 0 else LINE)
    return _save(fig, "concept_tree"), len(leaves)


CELL2 = ["вгорі ліворуч", "вгорі праворуч", "внизу ліворуч", "внизу праворуч"]
CELL3 = ["вгорі ліворуч", "вгорі по центру", "вгорі праворуч", "посередині ліворуч", "в центрі",
         "посередині праворуч", "внизу ліворуч", "внизу по центру", "внизу праворуч"]
ORI_WORD = ["горизонталь", "діагональ \\", "вертикаль", "діагональ /"]
DIR_WORD = ["праворуч", "вниз-праворуч", "вниз", "вниз-ліворуч", "ліворуч", "вгору-ліворуч", "вгору", "вгору-праворуч"]
GLOB_WORD = {"n_endpoints": "кількість кінців", "n_junctions": "кількість перехресть", "n_cycles": "кількість петель",
             "aspect": "ширина / висота", "total_length": "загальна довжина штриха"}


def dim_label(name):
    parts = name.split(".")
    if parts[0] == "glob":
        return GLOB_WORD[parts[1]]
    g = int(parts[0][1])
    cells = CELL2 if g == 2 else CELL3
    kind = parts[1]
    if kind in ("orient", "dorient"):
        where = cells[int(parts[2][1:])]
        what = "граф" if kind == "orient" else "щільна лінія"
        return f"{what}: {ORI_WORD[int(parts[3][1:])]}, {where} ({g}×{g})"
    if kind in ("ep", "jp"):
        return f"{'кінці' if kind == 'ep' else 'перехрестя'}, {cells[int(parts[2][1:])]} ({g}×{g})"
    if kind == "curv":
        return f"кривина {'до центру' if parts[2] == 'in' else 'назовні'}, {cells[int(parts[3][1:])]} ({g}×{g})"
    if kind == "epdir":
        return f"кінець дивиться {DIR_WORD[int(parts[3][1:])]}, {cells[int(parts[2][1:])]}"
    return name


def fig_band(model, xs, a="D_D_b042", b="O_O_b029", k=8):
    ia, ib = model.band_ids.index(a), model.band_ids.index(b)
    x = xs[0]
    diff = np.abs(model.centre[ia] - model.centre[ib]) * model.w_over_scale
    order = np.argsort(-diff)[:k]
    fig, ax = plt.subplots(figsize=(16 * CM, 6.8 * CM))
    fig.subplots_adjust(left=0.36, right=0.97)
    for row, d in enumerate(order):
        y = k - 1 - row
        vals = [model.lo[ia, d], model.hi[ia, d], model.lo[ib, d], model.hi[ib, d], x[d]]
        lo, hi = min(vals), max(vals)
        span = max(hi - lo, 1e-9)
        f = lambda v: (v - lo) / span  # noqa: E731
        for idx, dy, col in ((ib, 0.17, BEFORE), (ia, -0.17, AFTER)):
            ax.plot([f(model.lo[idx, d]), f(model.hi[idx, d])], [y + dy] * 2, color=col, lw=6,
                    solid_capstyle="butt", alpha=0.9)
            ax.plot([f(model.centre[idx, d])] * 2, [y + dy - 0.17, y + dy + 0.17], color=INK, lw=1)
        ax.scatter([f(x[d])], [y], marker="D", s=34, color=HIGHLIGHT, zorder=3, edgecolor="white", linewidth=0.6)
        ax.text(-0.04, y, dim_label(model.dim_names[d]), ha="right", va="center", fontsize=7.6)
        ax.text(1.04, y, f"{x[d]:.3f}", ha="left", va="center", fontsize=7, color=HIGHLIGHT)
    ax.set_xlim(-0.02, 1.13), ax.set_ylim(-0.7, k - 0.3), ax.axis("off")
    ax.legend(handles=[Line2D([], [], color=AFTER, lw=6, label=f"лист {a.split('_', 1)[1]}"),
                       Line2D([], [], color=BEFORE, lw=6, label=f"лист {b.split('_', 1)[1]}"),
                       Line2D([], [], color=INK, lw=1, label="центр"),
                       Line2D([], [], marker="D", ls="", color=HIGHLIGHT, label=f"зображення {EXAMPLE}")],
              loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=4, frameon=False, fontsize=7.5)
    return _save(fig, "band")


def fig_selection():
    cfg = json.load(open(EXP / "run_config.json"))["emnist"]
    per = cfg["originals_per_letter"]
    chosen = set(cfg["chosen_originals"]["A"])
    fig = plt.figure(figsize=(16 * CM, 8.4 * CM))
    ax = fig.add_axes([0.04, 0.60, 0.95, 0.30])
    vals = [per[l] for l in LETTERS]
    ax.bar(range(26), vals, color=AFTER, width=0.7)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.4, v, ha="center", fontsize=7, color=INK)
    ax.set_xticks(range(26), LETTERS), ax.set_yticks([])
    ax.axhline(10, color=HIGHLIGHT, lw=0.9, ls=(0, (3, 2)))
    ax.text(25.7, 10, " у середньому 10", ha="left", va="center", fontsize=7, color=HIGHLIGHT)
    ax.set_xlim(-0.6, 28.4)
    _clean(ax)
    ax.set_title("а) оригіналів на літеру (адаптивний бюджет, разом 260)", fontsize=8)
    files = sorted(p.stem for p in (CAND / "A").glob("A_b*.png"))
    fig.text(0.04, 0.49, f"б) 60 кандидатів літери A; обрані {len(chosen)} — у рамці", fontsize=8, fontweight="bold")
    cols, size = 20, 0.045
    for i, stem in enumerate(files):
        r, c = divmod(i, cols)
        sub = fig.add_axes([0.04 + c * 0.0478, 0.37 - r * 0.095, size, size * 16 / 8.4])
        pick = stem in chosen
        _thumb(sub, CAND / "A" / f"{stem}.png", frame=AFTER if pick else None, alpha=1.0 if pick else 0.3)
    return _save(fig, "selection")


def fig_example(driver, model):
    image_id = _image_id(EXAMPLE)
    xs = get_image_feature_set(driver, image_id, model.dm_version)
    pts, tans = get_image_shape(driver, image_id)
    ranked = score_letters_committee(xs, model)[:5]
    h = shape_context(pts)
    sc = np.array([letter_distance(model, r.letter, h, pts, tans) for r in ranked])
    band = np.array([r.score for r in ranked])
    zb, zs = (band - band.mean()) / band.std(), (sc - sc.mean()) / sc.std()
    final = [ranked[i].letter for i in np.argsort(zb + model.stage2_lambda * zs, kind="stable")]

    def best_leaf(letter):
        best = (np.inf, None)
        for i, (l, role) in enumerate(zip(model.letters, model.roles)):
            if l == letter and role == "leaf" and model.shape_contexts[i] is not None:
                d = distances(h, pts, tans, model.shape_contexts[i], model.shape_points[i],
                              model.shape_tangents[i], model.stage2_beta).min()
                best = min(best, (float(d), i))
        return best[1]

    fig = plt.figure(figsize=(16 * CM, 10.4 * CM))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1], hspace=0.42, wspace=0.18)
    ax = fig.add_subplot(gs[0, 0])
    _thumb(ax, TEST / "D" / f"{EXAMPLE}.png", frame=LINE)
    ax.set_title(f"а) {EXAMPLE}\n    правильна відповідь D", fontsize=8)
    for col, letter in ((1, "D"), (2, "O")):
        i = best_leaf(letter)
        ap, at, ah = model.shape_points[i][0], model.shape_tangents[i][0], model.shape_contexts[i][0]
        tol = model.shape_tol[i]
        num = (h[:, None, :] - ah[None]) ** 2
        cost = 0.5 * (num / (h[:, None, :] + ah[None] + 1e-6)).sum(2)
        cost += POSITION_WEIGHT * np.linalg.norm(pts[:, None] - ap[None], axis=2)
        cost += model.stage2_beta * 0.5 * (1 - tans @ at.T)
        ax = fig.add_subplot(gs[0, col])
        for j, (px, py) in enumerate(ap):
            ax.add_patch(Circle((px, py), tol[j] if tol is not None else 0.03, fc=FILL, ec=LINE, lw=0.6, zorder=1))
            ax.plot([px - 0.04 * at[j, 0], px + 0.04 * at[j, 0]], [py - 0.04 * at[j, 1], py + 0.04 * at[j, 1]],
                    color=AFTER, lw=1.2, zorder=2)
        best = cost.argmin(1)
        worst = np.percentile(cost.min(1), 75)
        for k, (px, py) in enumerate(pts):
            q = ap[best[k]]
            bad = cost[k, best[k]] > worst
            ax.plot([px, q[0]], [py, q[1]], color=HIGHLIGHT if bad else MUTED, lw=0.8 if bad else 0.5, zorder=2)
            ax.scatter([px], [py], s=9, color=HIGHLIGHT if bad else INK, zorder=3)
        ax.set_xlim(-0.05, 1.05), ax.set_ylim(1.05, -0.05), ax.set_aspect("equal")
        ax.set_xticks([]), ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor(LINE)
        d = sc[[r.letter for r in ranked].index(letter)]
        ax.set_title(f"{'б' if col == 1 else 'в'}) концепт форми {model.band_ids[i].split('_', 1)[1]}\n"
                     f"    відстань {d:.3f}", fontsize=8)
    ax = fig.add_subplot(gs[1, 0])
    letters = [r.letter for r in ranked]
    y = np.arange(5)[::-1]
    ax.barh(y, band, color=[AFTER if l == "D" else BEFORE for l in letters], height=0.62)
    for yi, v in zip(y, band):
        ax.text(v + 0.2, yi, f"{v:.2f}", va="center", fontsize=7.5)
    ax.set_yticks(y, letters), ax.set_xlim(0, band.max() * 1.25), ax.set_xticks([])
    _clean(ax)
    ax.set_title("г) тур 1: штраф смуг", fontsize=8)
    ax = fig.add_subplot(gs[1, 1])
    ax.barh(y, sc, color=[AFTER if l == "D" else BEFORE for l in letters], height=0.62)
    for yi, v in zip(y, sc):
        ax.text(v + sc.max() * 0.02, yi, f"{v:.3f}", va="center", fontsize=7.5)
    ax.set_yticks(y, letters), ax.set_xlim(0, sc.max() * 1.3), ax.set_xticks([])
    _clean(ax)
    ax.set_title("д) тур 2: відстань форми", fontsize=8)
    ax = fig.add_subplot(gs[1, 2])
    for i, l in enumerate(letters):
        j = final.index(l)
        col = AFTER if l == "D" else BEFORE
        ax.plot([0, 1], [4 - i, 4 - j], color=col, lw=2 if l == "D" else 1.2)
        ax.text(-0.06, 4 - i, l, ha="right", va="center", fontsize=9, fontweight="bold", color=col if l == "D" else INK)
        ax.text(1.06, 4 - j, l, ha="left", va="center", fontsize=9, fontweight="bold", color=col if l == "D" else INK)
    ax.text(0, 4.75, "тур 1", ha="center", fontsize=7.5, color=MUTED)
    ax.text(1, 4.75, "підсумок", ha="center", fontsize=7.5, color=MUTED)
    ax.set_xlim(-0.35, 1.35), ax.set_ylim(-0.5, 5.1), ax.axis("off")
    ax.set_title("е) порядок літер", fontsize=8)
    info = {"top5": letters, "band": band.round(2).tolist(), "shape": sc.round(4).tolist(), "final": final}
    return _save(fig, "example"), info, xs


# ---------------------------------------------------------------- markdown -> docx
from docx import Document  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

BODY_FONT, HEAD_FONT, CODE_FONT = "Calibri", "Georgia", "Consolas"


def _rgb(hexstr):
    return RGBColor.from_string(hexstr.lstrip("#").upper())


def _set_font(style_or_run, name):
    style_or_run.font.name = name
    fonts = style_or_run._element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(attr), None)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)


ORDER = {
    "rPr": "rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid "
           "vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs "
           "em lang eastAsianLayout specVanish oMath",
    "tcPr": "cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark",
    "tblPr": "tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing "
             "tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription",
}


def _put(parent, child):
    """Insert a property element where the OOXML schema wants it (Word rejects out-of-order properties)."""
    order = ORDER[parent.tag.split("}")[1]].split()
    name = child.tag.split("}")[1]
    old = parent.find(child.tag)
    if old is not None:
        parent.remove(old)
    rank = order.index(name)
    for i, existing in enumerate(parent):
        tag = existing.tag.split("}")[1]
        if tag in order and order.index(tag) > rank:
            parent.insert(i, child)
            return
    parent.append(child)


def _shade(element, hexstr):
    props = element.get_or_add_tcPr() if hasattr(element, "get_or_add_tcPr") else element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"), shd.set(qn("w:color"), "auto"), shd.set(qn("w:fill"), hexstr.lstrip("#"))
    _put(props, shd)


def setup_styles(doc):
    st = doc.styles
    normal = st["Normal"]
    _set_font(normal, BODY_FONT)
    normal.font.size, normal.font.color.rgb = Pt(10.5), _rgb(INK)
    normal.paragraph_format.space_after, normal.paragraph_format.line_spacing = Pt(5), 1.15
    for name, size, color, before, after in (("Heading 1", 18, AFTER_DARK, 0, 10), ("Heading 2", 12.5, AFTER, 14, 5),
                                             ("Title", 30, AFTER_DARK, 0, 6)):
        s = st[name]
        _set_font(s, HEAD_FONT)
        s.font.size, s.font.bold, s.font.color.rgb = Pt(size), name != "Title", _rgb(color)
        s.font.italic = False
        s.paragraph_format.space_before, s.paragraph_format.space_after = Pt(before), Pt(after)
        s.paragraph_format.keep_with_next = True
    st["Heading 1"].paragraph_format.page_break_before = True
    cap = st["Caption"]
    _set_font(cap, BODY_FONT)
    cap.font.size, cap.font.italic, cap.font.bold, cap.font.color.rgb = Pt(8.5), False, False, _rgb(MUTED)
    cap.paragraph_format.space_after = Pt(12)
    for name in ("List Bullet", "List Bullet 2"):
        st[name].paragraph_format.space_after = Pt(3)


INLINE = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\\(\*)|(?<![*\w])\*([^*\s][^*]*?)\*(?![*\w])")


def add_inline(par, text, size=None, bold=False, color=None):
    pos = 0

    def run(t, b=False, code=False, link=False, italic=False):
        if not t:
            return
        r = par.add_run(t)
        r.bold = bold or b
        r.italic = italic or None
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = _rgb(color)
        if code:
            _set_font(r, CODE_FONT)
            r.font.size = Pt((size or 10.5) * 0.86)
            _shade(r._element, "#EEF1F5")
        if link:
            r.font.color.rgb = _rgb(AFTER)
    for m in INLINE.finditer(text):
        run(text[pos:m.start()])
        if m.group(1) is not None:
            for k, part in enumerate(re.split(r"`([^`]+)`", m.group(1))):
                run(part, b=True, code=k % 2 == 1)
        elif m.group(2) is not None:
            run(m.group(2), code=True)
        elif m.group(3) is not None:
            run(m.group(3), link=True)
        elif m.group(5) is not None:
            run(m.group(5))
        else:
            run(m.group(6), italic=True)
        pos = m.end()
    run(text[pos:])


def parse_md(text):
    lines = text.split("\n")
    blocks, i, para = [], 0, []

    def flush():
        if para:
            blocks.append(("p", " ".join(s.strip() for s in para)))
            para.clear()
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            blocks.append(("code", lines[i + 1:j]))
            i = j + 1
            continue
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            blocks.append(("h", level, line[level:].strip()))
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue
        elif re.match(r"^\s*- ", line):
            flush()
            items = []
            while i < len(lines) and lines[i].strip() and (re.match(r"^\s*- ", lines[i]) or lines[i].startswith("  ")):
                m = re.match(r"^(\s*)- (.*)", lines[i])
                if m:
                    items.append([len(m.group(1)) // 2, m.group(2).strip()])
                else:
                    items[-1][1] += " " + lines[i].strip()
                i += 1
            blocks.append(("ul", items))
            continue
        elif line.strip() == "---":
            flush()
        elif not line.strip():
            flush()
        else:
            para.append(line)
        i += 1
    flush()
    return blocks


def _key(block):
    kind = block[0]
    if kind == "h":
        return block[2]
    if kind == "p":
        return block[1]
    if kind == "table":
        return re.sub(r"\s+", " ", "| " + " | ".join(block[1][0]) + " |")
    if kind == "ul":
        return block[1][0][1]
    if kind == "code":
        return block[1][0] if block[1] else ""
    return ""


NUMERIC = re.compile(r"^[\s*+−\-–~≈.,%\d/()→…]+$")


def _cell_margins(table, top=50, bottom=50, side=90):
    tblpr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, v in (("top", top), ("bottom", bottom), ("left", side), ("right", side)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), str(v)), e.set(qn("w:type"), "dxa")
        mar.append(e)
    _put(tblpr, mar)


def _borders(table, inside=LINE, outer=AFTER_DARK, vertical=False):
    tblpr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    spec = {"top": (outer, 8), "bottom": (outer, 8), "insideH": (inside, 4)}
    if vertical:
        spec.update({"left": (inside, 4), "right": (inside, 4), "insideV": (inside, 4)})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        if edge in spec:
            e.set(qn("w:val"), "single"), e.set(qn("w:sz"), str(spec[edge][1]))
            e.set(qn("w:color"), spec[edge][0].lstrip("#"))
        else:
            e.set(qn("w:val"), "nil")
        b.append(e)
    _put(tblpr, b)


def _full_width(table):
    tblpr = table._tbl.tblPr
    w = OxmlElement("w:tblW")
    w.set(qn("w:w"), "5000"), w.set(qn("w:type"), "pct")
    _put(tblpr, w)


def _fixed_widths(table, widths_cm):
    table.autofit = False
    for col, w in zip(table.columns, widths_cm):
        col.width = Cm(w)
        for cell in col.cells:
            cell.width = Cm(w)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    _put(table._tbl.tblPr, layout)


def _repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader")
    h.set(qn("w:val"), "true")
    trpr.append(h)


def add_table(doc, rows):
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    table = doc.add_table(rows=len(rows), cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(table), _cell_margins(table)
    if ncols > 3 or sum(len(c) for c in rows[0]) > 40:
        _full_width(table)
    size = 8.5 if ncols >= 6 else 9
    # merge empty header cells into the cell on their left (grouped headers)
    spans, j = [], 0
    while j < ncols:
        k = j + 1
        while k < ncols and not rows[0][k]:
            k += 1
        spans.append((j, k - 1))
        j = k
    for a, b in spans:
        if b > a:
            table.cell(0, a).merge(table.cell(0, b))
    for i, r in enumerate(rows):
        header = i == 0
        for j, text in enumerate(r):
            if header and any(a < j <= b for a, b in spans):
                continue
            cell = table.cell(i, j)
            par = cell.paragraphs[0]
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            if header:
                _shade(cell._tc, AFTER_DARK)
                add_inline(par, text.replace("**", ""), size=size, bold=True, color="#FFFFFF")
            else:
                if i % 2 == 0:
                    _shade(cell._tc, BAND)
                add_inline(par, text, size=size)
                if NUMERIC.match(text.replace("**", "")) and text.strip():
                    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif text.strip() in ("✅", "⚠️ змінено", "✅ з приміткою", "✓", "—", "·"):
                    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if header:
            _repeat_header(table.rows[0])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_code(doc, lines):
    table = doc.add_table(rows=1, cols=1)
    _full_width(table), _cell_margins(table, 90, 90, 140)
    _borders(table, inside="#FFFFFF", outer="#FFFFFF")
    cell = table.cell(0, 0)
    _shade(cell._tc, "#F1F4F8")
    par = cell.paragraphs[0]
    par.paragraph_format.space_after, par.paragraph_format.line_spacing = Pt(0), 1.0
    for k, line in enumerate(lines):
        r = par.add_run(line)
        _set_font(r, CODE_FONT)
        r.font.size = Pt(7.2)
        r.font.color.rgb = _rgb(MUTED if line.lstrip().startswith("#") else INK)
        if k < len(lines) - 1:
            r.add_break()
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


class Figures:
    def __init__(self, doc):
        self.doc, self.n = doc, 0

    def add(self, path, caption, width=16.0):
        self.n += 1
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next, p.paragraph_format.space_after = True, Pt(3)
        p.add_run().add_picture(str(path), width=Cm(width))
        c = self.doc.add_paragraph(style="Caption")
        r = c.add_run(f"Рис. {self.n}. ")
        r.bold = True
        r.font.color.rgb = _rgb(INK)
        add_inline(c, caption, size=8.5)


def add_cover(doc, sections):
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph(style="Title")
    p.add_run("Few-shot розпізнавання на концептах")
    p = doc.add_paragraph()
    add_inline(p, "EMNIST-letters і MNIST · звіт про експеримент", size=14, color=MUTED)
    p.paragraph_format.space_after = Pt(28)
    tiles = doc.add_table(rows=1, cols=2)
    _fixed_widths(tiles, [8.3, 8.3])
    _cell_margins(tiles, 160, 160, 200)
    _borders(tiles, inside="#FFFFFF", outer="#FFFFFF")
    for cell, (label, before, after, sub) in zip(tiles.rows[0].cells, (
            ("EMNIST-letters · 26 класів · 20 800 зображень", "50.9 %", "84.6 %",
             "top-1 при ≈10 оригіналах на літеру; top-3 96.4 %"),
            ("MNIST complete · 10 класів · 8 708 зображень", "90.9 %", "97.4 %",
             "на тих самих 76 оригіналах, що й база"))):
        _shade(cell._tc, FILL)
        par = cell.paragraphs[0]
        add_inline(par, label, size=8.5, color=MUTED)
        par = cell.add_paragraph()
        par.paragraph_format.space_before, par.paragraph_format.space_after = Pt(4), Pt(2)
        r = par.add_run(before)
        r.font.size, r.font.color.rgb = Pt(18), _rgb(BEFORE)
        r = par.add_run("  →  ")
        r.font.size, r.font.color.rgb = Pt(18), _rgb(MUTED)
        r = par.add_run(after)
        r.font.size, r.font.bold, r.font.color.rgb = Pt(26), True, _rgb(AFTER_DARK)
        _set_font(r, HEAD_FONT)
        add_inline(cell.add_paragraph(), sub, size=8.5)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    add_inline(p, "Без backprop і нейромереж, без попіксельного порівняння зображень, з концептами, які можна "
                  "прочитати. Усе працює в живому конвеєрі Nuclio + Kafka + Neo4j, і кожне тестове зображення "
                  "отримує відповідь.", size=11)
    meta = [("Період роботи", "10 вересня – 5 жовтня 2026"), ("Гілка", "`experiment/gap-aware-associative-emnist`"),
            ("Фінальні моделі", "`fs_final_B10` (EMNIST), `mn_final` (MNIST)"),
            ("Дані й таблиці", "`experiments/fewshot_band_concepts_2026-10/` — report.md, lab_log.md, CSV")]
    t = doc.add_table(rows=len(meta), cols=2)
    _fixed_widths(t, [3.6, 13.0])
    _cell_margins(t, 30, 30, 0), _borders(t, inside="#FFFFFF", outer="#FFFFFF")
    for row, (k, v) in zip(t.rows, meta):
        add_inline(row.cells[0].paragraphs[0], k, size=9, color=MUTED)
        add_inline(row.cells[1].paragraphs[0], v, size=9)
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    h = doc.add_paragraph()
    r = h.add_run("Зміст")
    _set_font(r, HEAD_FONT)
    r.font.size, r.font.bold, r.font.color.rgb = Pt(18), True, _rgb(AFTER_DARK)
    h.paragraph_format.space_after = Pt(12)
    for level, title in sections:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0 if level == 2 else 0.8)
        p.paragraph_format.space_after = Pt(4 if level == 2 else 1)
        p.paragraph_format.space_before = Pt(6 if level == 2 else 0)
        add_inline(p, re.sub(r"\s*\(`.*?`.*?\)$", "", title), size=11 if level == 2 else 9.5,
                   bold=level == 2, color=INK if level == 2 else MUTED)


def add_footer(doc):
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_inline(p, "Few-shot розпізнавання на концептах · ", size=8, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "16")
    rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    p._p.append(fld)


def build_docx(figs, info):
    md = (EXP / "report.md").read_text()
    blocks = parse_md(md)
    first = next(i for i, b in enumerate(blocks) if b[0] == "h" and b[1] == 2)
    blocks = blocks[first:]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    setup_styles(doc)
    add_cover(doc, [(b[1], b[2]) for b in blocks if b[0] == "h" and b[1] in (2, 3)])
    add_footer(doc)
    F = Figures(doc)

    def fig(key, caption, width=16.0):
        return lambda: F.add(figs[key], caption, width)
    ex = info["example"]
    hooks = [
        # (substring of the block's first line, action, callbacks)
        ("| Набір | Система | top-1", "after", [fig("headline", "Точність до і після на повних тестах, відсоток від "
                                                              "усіх зображень.")]),
        ("зображення → скелет (бінаризація", "replace", [fig("pipeline_before", "Система «до»: рішення ухвалює "
                                                         "порівняння графа зображення з графом кожного fold-концепту.")]),
        ("зображення ─► скелет", "replace", [fig("pipeline_after", "Система «після»: ознаки скелетного графа і "
                                             "центральної лінії, рішення в два тури над концептами, що зберігаються "
                                             "в Neo4j.")]),
        ("| Що | Навіщо | Параметр", "after", [fig("processing", f"Обробка одного тестового зображення ({EXAMPLE}) "
                                                 "продакшн-кодом скелетизації: три скелети комітету (вузли графа: "
                                                 "● кінець, ■ перехрестя; сірим — бінаризація) і 32 точки центральної "
                                                 "лінії з напрямками дотичних після вирівнювання нахилу й нормування "
                                                 "за моментами.")]),
        ("Плюс 32 точки центральної лінії", "after", [fig("features", "Опис того самого зображення. Довжина рисочки "
                                                      "в клітинці — яка частка штриха проходить там у цьому напрямку "
                                                      "(0°, 45°, 90°, 135°). Кожне з 193 чисел має ім'я, наприклад "
                                                      "`g3.orient.c4.b2` — «вертикальний штрих у центральній клітинці "
                                                      "сітки 3 × 3».")]),
        ("**Лист** — один оригінал", "after", [
            fig("concept_tree", f"Концепти літери D у Neo4j: корінь узагальнює {info['d_leaves']} листків — по "
                                "одному на кожен оригінал, який обрала система. Нижче — лист D_b042: оригінал і 10 "
                                "аугментацій, з яких побудовано його смуги й концепт форми."),
            fig("band", "Смуговий концепт — це діапазон «від … до» по кожному виміру. Вісім вимірів, де листки "
                        f"D_b042 і O_b029 різняться найбільше; ромб — значення зображення {EXAMPLE}.")]),
        ("**скільки** оригіналів", "after", [fig("selection", "Вибір оригіналів: система сама вирішує, скільки "
                                          "оригіналів потрібно літері (широким формам більше), і які саме — "
                                          "k-medoids із покриттям топологій.")]),
        ("Тур 1 помиляється", "after", [fig("example", f"Рішення в два тури для {EXAMPLE} (відтворено з моделі "
                                                       f"`{MODEL_ID}` і збережених ознак). б, в — точки лінії "
                                                       "зображення (чорні) шукають опорні точки концепту форми "
                                                       "(кола = допуск, рисочки = напрямок); оранжеві — 25 % "
                                                       "найгірших пар. У концепті O немає опорних точок у кутах D, "
                                                       "тому відстань більша. г, д — оцінки турів (менше — краще); "
                                                       f"е — порядок літер. Підсумок: {', '.join(ex['final'])}.")]),
        ("top-1 / top-3 — від оброблених", "after", [fig("chronology", "Хронологія живих вимірів на повному тесті "
                                                     "EMNIST. Номери — рядки таблиці нижче.")]),
        ("| Тур 1 | Тур 2 | EMNIST top-1", "after", [fig("ablation", "Абляція: комітет скелетів і тур 2 вмикаються "
                                                     "окремо, усе інше незмінне.")]),
        ("| До | Після |", "replace", [
            fig("confusion_emnist_before", "Матриця плутанини EMNIST «до» (fold-концепти + direct_bridge + "
                                           "калібрування). Колір — частка рядка; числа — кількість зображень, поза "
                                           "діагоналлю показано клітинки ≥ 10; ∅ — без відповіді."),
            fig("confusion_emnist_after", "Матриця плутанини EMNIST «після». Помилки зібрались у кількох парах: "
                                          "I ↔ L, G ↔ Q, U ↔ V, D ↔ O.")]),
        ("**Найчастіші пари помилок**", "before", [fig("pairs", "Десять найчастіших пар помилок EMNIST до і після "
                                                     "(обидва напрямки разом, однакова шкала).")]),
        ("**Точність по класах**", "before", [fig("perclass_emnist", "Recall і precision по літерах EMNIST. "
                                                "Оранжева лінія — показник знизився.")]),
        ("| До (GED, `run_20260630_235356`", "replace", [fig("confusion_mnist", "Матриці плутанини MNIST complete "
                                                         "до і після. Числа — кількість зображень, поза діагоналлю "
                                                         "клітинки ≥ 3. Колонку «без відповіді» бази (22 зображення) "
                                                         "не показано.")]),
        ("**До** (∅ — зображення без відповіді", "skip", []),
        ("| | 0 | 1 | 2 | 3", "skip", []),
        ("**Після** (помилок 223", "skip", []),
        ("| Цифра | recall до", "before", [fig("perclass_mnist", "Recall і precision по цифрах MNIST.")]),
        ("EMNIST після: 3 201 помилка", "before", [fig("errors", "Реальні помилки фінальної системи на тесті "
                                                     "EMNIST: перші 10 за номером файлу в кожній парі «правильна "
                                                     "→ відповідь». Більшість — двозначні й для людини.")]),
    ]
    used = {k: 0 for k, _, _ in hooks}
    for block in blocks:
        key = _key(block)
        action = None
        for anchor, act, calls in hooks:
            if anchor in key:
                used[anchor] += 1
                action = (act, calls)
                break
        if action and action[0] == "before":
            for c in action[1]:
                c()
        if action and action[0] in ("replace", "skip"):
            for c in action[1]:
                c()
            continue
        kind = block[0]
        if kind == "h":
            level, title = block[1], block[2]
            if level == 2:
                p = doc.add_paragraph(style="Heading 1")
            else:
                p = doc.add_paragraph(style="Heading 2")
            add_inline(p, re.sub(r"\s*\(`.*$", "", title) if level == 3 and "(`" in title else title)
        elif kind == "p":
            add_inline(doc.add_paragraph(), block[1])
        elif kind == "ul":
            for level, text in block[1]:
                add_inline(doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2"), text)
        elif kind == "table":
            add_table(doc, block[1])
        elif kind == "code":
            add_code(doc, block[1])
        if action and action[0] == "after":
            for c in action[1]:
                c()
    missing = [k for k, n in used.items() if not n]
    if missing:
        raise SystemExit(f"report.md changed, hooks not found: {missing}")
    doc.save(OUT)
    return OUT


def main():
    driver = _driver()
    model = load_model(driver)
    figs = {"headline": fig_headline(), "chronology": fig_chronology(), "ablation": fig_ablation(),
            "pipeline_before": fig_pipeline_before(), "pipeline_after": fig_pipeline_after(),
            "processing": fig_processing(), "features": fig_features(), "selection": fig_selection(),
            "pairs": fig_pairs(), "errors": fig_errors(), "confusion_mnist": fig_confusion_mnist(),
            "perclass_emnist": fig_perclass("per_class_emnist.csv", "perclass_emnist", 11.5),
            "perclass_mnist": fig_perclass("per_class_mnist.csv", "perclass_mnist", 5.4)}
    figs["confusion_emnist_before"] = fig_confusion(
        "confusion_emnist_baseline.csv", "До: fold-концепти + direct_bridge + калібрування · top-1 50.9 %",
        "confusion_emnist_before", 10, (16 * CM, 15.6 * CM))
    figs["confusion_emnist_after"] = fig_confusion(
        "confusion_emnist_final.csv", "Після: смугові концепти + концепти форми · top-1 84.6 %",
        "confusion_emnist_after", 10, (16 * CM, 15.6 * CM))
    figs["concept_tree"], d_leaves = fig_concept_tree(driver)
    figs["example"], example, xs = fig_example(driver, model)
    figs["band"] = fig_band(model, xs)
    print("example:", example)
    if "--figures-only" in sys.argv:
        return
    print(build_docx(figs, {"example": example, "d_leaves": d_leaves}))


if __name__ == "__main__":
    main()
