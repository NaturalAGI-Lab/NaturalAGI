"""Word version of experiments/isl_transfer_2026-10/report_ISL.md for the professor.

Text and tables come from the markdown (one source); figures are drawn here from the result tables and per-image dumps
of the ISL experiments. A paragraph `<!-- FIG:<name> | <caption> -->` in the markdown places a figure.
Reuses the styles and markdown -> docx helpers of notes/scripts_pipeline/pl_report_docx.py.

Usage: isl_report_docx.py  -> experiments/isl_transfer_2026-10/report_ISL.docx, figures in tests/_isl/report_figures/
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "notes" / "scripts_pipeline"))
sys.path.insert(0, str(REPO / "notes" / "scripts_isl"))
import pl_report_docx as R  # noqa: E402  (styles, palette, markdown -> docx)
import isl_sim as S  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

EXP = REPO / "experiments" / "isl_transfer_2026-10"
ISL = REPO / "tests" / "_isl"
R.FIG = ISL / "report_figures"
MD = EXP / "report_ISL.md"
OUT = EXP / "report_ISL.docx"
CM, INK, MUTED, LINE, FILL, BAND = R.CM, R.INK, R.MUTED, R.LINE, R.FILL, R.BAND
AFTER, AFTER_DARK, AFTER_LIGHT, BEFORE, HIGHLIGHT = R.AFTER, R.AFTER_DARK, R.AFTER_LIGHT, R.BEFORE, R.HIGHLIGHT
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(REPO / "datasets" / "mnist_all_manifest.csv"))}


def _rows(path, key="stem"):
    out = {}
    for line in open(path):
        r = json.loads(line)
        out[r[key] if key in r else Path(r["path"]).stem] = r
    return out


def _acc(rows, keys):
    return 100.0 * sum(rows[k]["pred"] == rows[k]["true"] for k in keys) / len(keys)


def _bars(ax, groups, series, colors, labels, ylim, fmt="{:.1f}"):
    x = np.arange(len(groups))
    w = 0.8 / len(series)
    for i, (vals, col, lab) in enumerate(zip(series, colors, labels)):
        pos = x - 0.4 + w * (i + 0.5)
        ax.bar(pos, vals, width=w * 0.92, color=col, label=lab)
        for p, v in zip(pos, vals):
            ax.text(p, v + (ylim[1] - ylim[0]) * 0.015, fmt.format(v), ha="center", va="bottom", fontsize=7.2)
    ax.set_xticks(x, groups)
    ax.set_ylim(*ylim)
    ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
    R._clean(ax)


# ----------------------------------------------------------------------------------------------- figures
def fig_same76():
    ours = _rows(ISL / "final2_base76_test.jsonl")
    com = {Path(json.loads(l)["path"]).stem: json.loads(l) for l in open(ISL / "coman_mnist_all.jsonl")}
    keys = sorted(ours)
    sub = {"усі 10 000": keys, "complete": [k for k in keys if MANIFEST.get(k) == "complete"],
           "incomplete": [k for k in keys if MANIFEST.get(k) == "incomplete"]}
    fig, ax = plt.subplots(figsize=(16 * CM, 6.0 * CM))
    _bars(ax, list(sub), [[_acc(com, v) for v in sub.values()], [_acc(ours, v) for v in sub.values()]],
          [BEFORE, AFTER], ["ComAN (порівняння графів)", "без матчингу (проєкція)"], (0, 105))
    ax.set_ylabel("top-1, %", color=MUTED)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=7.5)
    return R._save(fig, "isl_same76")


def fig_pipeline():
    fig, ax = R._canvas(8.0)
    R._box(ax, 0.0, 7.3, 16, 0.7, "ComAN (реалізація Микити)", "", fc=BAND, ec=BAND)
    top = [(0.0, 2.9, "Зображення", "один поріг;\nпошук зв'язного\nграфа"),
           (3.3, 3.2, "Граф контуру", "GNG + RDP;\n~13 ознак вузла"),
           (6.9, 5.4, "Порівняння графів", "редукція до ізоморфізму + GED з кожним\nіз 13 концептів (перетин графів\nприкладів, діапазони min…max, ручні підкласи)"),
           (12.7, 3.3, "Рішення", "схожість +\nλ·складність\n(λ з тесту)")]
    for i, (x, w, t, b) in enumerate(top):
        R._box(ax, x, 5.25, w, 1.85, t, b)
        if i:
            R._arrow(ax, top[i - 1][0] + top[i - 1][1] + 0.03, 6.17, x - 0.03, 6.17)
    R._box(ax, 0.0, 4.25, 16, 0.7, "Модель без матчингу (Ваш розділ IV)", "", fc=FILL, ec=AFTER)
    bot = [(0.0, 2.55, "Детектор D", "4 канали: пороги\n110/150/190 +\nдрібний масштаб"),
           (2.85, 3.05, "Примітиви", "критичні точки E/C/J,\nштрихи, петлі,\nдуги вздовж обходу"),
           (6.2, 3.3, "Проєкція Π на H0", "синапси на всіх рівнях\nсегментації; перекриття\nполів; фовеа; MAX"),
           (9.8, 3.0, "Нейрони", "лічильники f(e);\nатрактор f ≥ τ;\nкарта за новизною"),
           (13.1, 2.9, "Сома + WTA", "перекриття ÷ √(загальний\nвхід); переможець")]
    for i, (x, w, t, b) in enumerate(bot):
        R._box(ax, x, 1.4, w, 2.6, t, b, fc="white", ec=AFTER)
        if i:
            R._arrow(ax, bot[i - 1][0] + bot[i - 1][1] + 0.03, 2.7, x - 0.03, 2.7, color=AFTER)
    R._box(ax, 0.0, 0.0, 16, 1.15, "Навчання лише на позитивах",
           "мітка = сигнал ψ, що відкриває пластичність; сім'я аугментацій голосує більшістю; ручних підкласів немає",
           fc=BAND)
    return R._save(fig, "isl_pipeline")


def fig_projection(split="dev", stem="4_v061"):
    data = json.loads((S.CACHE / "t110r" / split / stem[0] / f"{stem}.json").read_text())
    pts, rels = S.extract(data)
    xy = np.array(data["nodes"], float)
    skel = np.array(data["skel"], float)
    c = skel.mean(0)
    unit = np.clip((xy - c) / S.FOV + 0.5, 0, 0.999)
    fig, axes = plt.subplots(1, 3, figsize=(16 * CM, 5.8 * CM))
    img = 255 - __import__("cv2").imread(str(REPO / "tests" / "mnist_dev" / stem[0] / f"{stem}.png"), 0)
    axes[0].imshow(img, cmap="gray")
    axes[0].set_xticks([]), axes[0].set_yticks([])
    for sp in axes[0].spines.values():
        sp.set_edgecolor(LINE)
    axes[0].set_title("а) зображення (dev)", fontsize=8)
    ax = axes[1]
    for u, v in data["edges"]:
        ax.plot(unit[[u, v], 0], unit[[u, v], 1], color=AFTER_LIGHT, lw=2.2, zorder=1)
    marks = {"E": ("o", HIGHLIGHT), "C": ("^", AFTER), "J": ("s", AFTER_DARK)}
    for p in pts:
        m, col = marks[p["type"]]
        ax.scatter(*p["pos"], marker=m, s=46, color=col, zorder=3, edgecolor="white", linewidth=0.6)
    for r in rels:
        for a in r.get("arcs", []):
            ax.scatter(*a["pos"], marker="x", s=16, color=INK, zorder=2, linewidth=0.8)
    for k in range(1, 4):
        ax.axvline(k / 4, color=LINE, lw=0.6, zorder=0), ax.axhline(k / 4, color=LINE, lw=0.6, zorder=0)
    ax.set_xlim(0, 1), ax.set_ylim(1, 0), ax.set_aspect("equal"), ax.set_xticks([]), ax.set_yticks([])
    ax.set_title("б) примітиви на сітці 4 × 4\n(центр мас, поле зору 80 px)", fontsize=8)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=HIGHLIGHT, label="кінець E"),
                       Line2D([], [], marker="^", ls="", color=AFTER, label="кут C"),
                       Line2D([], [], marker="s", ls="", color=AFTER_DARK, label="перехрестя J"),
                       Line2D([], [], marker="x", ls="", color=INK, label="точки дуг")],
              loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=2, frameon=False, fontsize=6.6)
    ax = axes[2]
    act = S.activate(pts, rels, {**S.DEFAULT, **S.IMPROVEMENTS["best2"]})
    kinds = Counter({"E": "точки", "C": "точки", "J": "точки", "R": "гіперребра", "K": "дуги", "JB": "гілки"}[k[0]]
                    for k in act)
    names = ["точки", "гіперребра", "дуги", "гілки"]
    ax.barh(range(len(names))[::-1], [kinds[n] for n in names], color=[AFTER, AFTER_DARK, AFTER_LIGHT, BEFORE])
    for i, n in enumerate(names):
        ax.text(kinds[n] + 10, len(names) - 1 - i, str(kinds[n]), va="center", fontsize=7.5)
    ax.set_yticks(range(len(names))[::-1], names)
    ax.set_xlim(0, max(kinds.values()) * 1.25)
    R._clean(ax)
    ax.set_title(f"в) активовані синапси H0: {len(act)}", fontsize=8)
    fig.tight_layout(w_pad=1.2)
    return R._save(fig, "isl_projection")


def fig_waterfall():
    single = [("перекриття полів", 1.53), ("правила скелета", 0.47), ("три фільтри + MAX", 3.32),
              ("вигин одним числом", -2.58), ("сила n/(n+1)", -1.38), ("best = поля + фільтри", 5.21)]
    later = [("дуги вздовж обходу", -0.64, 0.69), ("дрібний масштаб", 1.25, 0.57), ("фовеа", 0.37, 1.07),
             ("ширша аугментація", 0.82, -0.74), ("ρ 0.8", 0.03, 0.26), ("best2 (усі п'ять)", 1.87, 3.26)]
    fig, axes = plt.subplots(1, 2, figsize=(16 * CM, 6.4 * CM), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    y = np.arange(len(single))[::-1]
    vals = [v for _, v in single]
    ax.barh(y, vals, color=[AFTER if v > 0 else HIGHLIGHT for v in vals], height=0.6)
    for yi, v in zip(y, vals):
        ax.text(v + (0.15 if v >= 0 else -0.15), yi, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=7.5)
    ax.set_yticks(y, [n for n, _ in single]), ax.axvline(0, color=INK, lw=0.6), ax.set_xlim(-4, 7)
    ax.set_title("а) над еталоном без матчингу, MNIST", fontsize=8)
    R._clean(ax)
    ax = axes[1]
    y = np.arange(len(later))[::-1]
    ax.barh(y + 0.18, [m for _, m, _ in later], height=0.34, color=AFTER, label="MNIST")
    ax.barh(y - 0.18, [e for _, _, e in later], height=0.34, color=AFTER_LIGHT, label="EMNIST")
    for yi, (_, m, e) in zip(y, later):
        for v, dy in ((m, 0.18), (e, -0.18)):
            ax.text(v + (0.08 if v >= 0 else -0.08), yi + dy, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right",
                    fontsize=6.6)
    ax.set_yticks(y, [n for n, _, _ in later]), ax.axvline(0, color=INK, lw=0.6), ax.set_xlim(-1.4, 4.2)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.06), ncol=2, frameon=False, fontsize=7)
    ax.set_title("б) над best, MNIST і EMNIST", fontsize=8, loc="left")
    R._clean(ax)
    for a in axes:
        a.set_xlabel("Δ top-1 на dev, п.п.", color=MUTED)
    fig.tight_layout(w_pad=1.5)
    return R._save(fig, "isl_waterfall")


def fig_final():
    groups = ["MNIST\n10 на цифру", "MNIST\n60 на цифру", "EMNIST\n10 на літеру", "EMNIST\n60 на літеру"]
    ref, best, best2 = [81.44, 89.93, 63.78, 71.91], [87.07, 93.04, 71.59, 80.27], [89.55, 94.50, 73.49, 82.61]
    fig, ax = plt.subplots(figsize=(16 * CM, 6.2 * CM))
    _bars(ax, groups, [ref, best, best2], [BEFORE, AFTER_LIGHT, AFTER], ["еталон без матчингу", "best", "best2"], (50, 102))
    ax.set_ylabel("top-1 на офіційному тесті, %", color=MUTED)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=7.5)
    return R._save(fig, "isl_final")


def fig_perdigit():
    ours = _rows(ISL / "final2_base76_test.jsonl")
    com = {Path(json.loads(l)["path"]).stem: json.loads(l) for l in open(ISL / "coman_mnist_all.jsonl")}
    digits = list("0123456789")
    rc = [_acc(com, [k for k in ours if ours[k]["true"] == d]) for d in digits]
    ro = [_acc(ours, [k for k in ours if ours[k]["true"] == d]) for d in digits]
    fig, ax = plt.subplots(figsize=(16 * CM, 5.4 * CM))
    x = np.arange(10)
    for xi, a, b in zip(x, rc, ro):
        ax.plot([xi, xi], [a, b], color=HIGHLIGHT if b < a else LINE, lw=1.6, zorder=1)
    ax.scatter(x, rc, color=BEFORE, s=30, zorder=2, label="ComAN")
    ax.scatter(x, ro, color=AFTER, s=36, zorder=3, label="без матчингу")
    ax.set_xticks(x, digits), ax.set_ylim(55, 100), ax.set_ylabel("recall, %", color=MUTED)
    ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
    R._clean(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=7.5)
    return R._save(fig, "isl_perdigit")


def fig_reduction():
    taus = [1.0, 0.8, 0.0]
    lines = [("MNIST, 10 на цифру, best (ρ 0.6)", [86.37, 86.84, 85.89], AFTER, -1),
             ("EMNIST, 10 на літеру, best", [70.81, 71.62, 69.69], AFTER_DARK, 1),
             ("76 оригіналів, карта за новизною, best2", [None, 88.90, 88.46], AFTER_LIGHT, 1),
             ("76 оригіналів, ручні підкласи, best2", [None, 81.26, 82.57], HIGHLIGHT, 1),
             ("76 оригіналів, ручні підкласи, еталон", [55.91, 72.85, 84.32], BEFORE, -1)]
    fig, axes = plt.subplots(1, 2, figsize=(16 * CM, 7.0 * CM))
    for name, vals, col, side in lines:
        ax = axes[0] if "ручні" not in name else axes[1]
        xs = [i for i, v in enumerate(vals) if v is not None]
        ax.plot(xs, [vals[i] for i in xs], marker="o", color=col, lw=1.8, label=name)
        for i in xs:
            ax.text(i + 0.06, vals[i] + 0.9 * side, f"{vals[i]:.1f}", ha="left", va="bottom" if side > 0 else "top",
                    fontsize=6.8, color=col)
    for ax, title in zip(axes, ("а) нейрони за новизною: τ 0.8 найкраще", "б) ручні підкласи: редукція програє")):
        ax.set_xticks(range(3), ["τ 1.0", "τ 0.8", "τ 0 (без\nредукції)"])
        ax.set_title(title, fontsize=8)
        ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
        R._clean(ax)
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.22), frameon=False, fontsize=6.6)
    axes[0].set_ylim(66, 92), axes[1].set_ylim(50, 90)
    axes[0].set_ylabel("top-1 на dev, %", color=MUTED)
    fig.tight_layout(w_pad=1.5)
    return R._save(fig, "isl_reduction")


def fig_errors():
    cats = [("S роздільність", AFTER_DARK), ("M конкуренція", AFTER), ("C покриття", AFTER_LIGHT), ("D детектор", BEFORE)]
    data = {"EMNIST": [43, 30, 22, 6], "MNIST": [30, 28, 35, 7]}
    fig, ax = plt.subplots(figsize=(16 * CM, 3.6 * CM))
    for row, (name, vals) in enumerate(data.items()):
        left = 0
        for (lab, col), v in zip(cats, vals):
            ax.barh(row, v, left=left, color=col, height=0.6, edgecolor="white", linewidth=1.2)
            ax.text(left + v / 2, row, f"{v} %", ha="center", va="center", color="white" if col != AFTER_LIGHT else INK,
                    fontsize=7.5)
            left += v
    ax.set_yticks(range(2), list(data)), ax.invert_yaxis(), ax.set_xlim(0, 101), ax.set_xticks([])
    R._clean(ax)
    ax.legend(handles=[Line2D([], [], color=c, lw=6, label=l) for l, c in cats], loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=4, frameon=False, fontsize=7.2)
    return R._save(fig, "isl_errors")


FIGS = {"same76": fig_same76, "pipeline": fig_pipeline, "projection": fig_projection, "waterfall": fig_waterfall,
        "final": fig_final, "perdigit": fig_perdigit, "reduction": fig_reduction, "errors": fig_errors}


# ----------------------------------------------------------------------------------------------- document
def add_cover(doc, sections):
    for _ in range(2):
        doc.add_paragraph()
    p = doc.add_paragraph(style="Title")
    p.add_run("ISL без матчингу гіперграфів")
    p = doc.add_paragraph()
    R.add_inline(p, "Опис системи, покращення відносно ComAN і відповідність аксіомам та принципам теорії", size=13,
                 color=MUTED)
    p.paragraph_format.space_after = Pt(22)
    tiles = doc.add_table(rows=1, cols=2)
    R._fixed_widths(tiles, [8.3, 8.3])
    R._cell_margins(tiles, 150, 150, 190)
    R._borders(tiles, inside="#FFFFFF", outer="#FFFFFF")
    for cell, (label, runs, sub) in zip(tiles.rows[0].cells, (
            ("MNIST, ті самі 76 оригіналів, усі 10 000",
             [("82.2 %", 17, BEFORE, False), ("  →  ", 17, MUTED, False), ("89.1 %", 22, AFTER_DARK, True)],
             "ComAN → без матчингу; на complete рівні"),
            ("Перші 60 зразків train на клас, без відбору",
             [("MNIST 94.5 %", 13, AFTER_DARK, True), ("  ·  ", 13, MUTED, False), ("EMNIST 82.6 %", 13, AFTER_DARK, True)],
             "офіційні тести, один прогін"))):
        R._shade(cell._tc, FILL)
        R.add_inline(cell.paragraphs[0], label, size=8.5, color=MUTED)
        par = cell.add_paragraph()
        par.paragraph_format.space_before, par.paragraph_format.space_after = Pt(4), Pt(2)
        for text, size, color, bold in runs:
            r = par.add_run(text)
            r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bold, R._rgb(color)
            R._set_font(r, R.HEAD_FONT)
        R.add_inline(cell.add_paragraph(), sub, size=8.5)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    R.add_inline(p, "**Позначення.** ✅ — відповідає теорії і Ви це прямо пропонували або це є в рукописі; "
                    "⚠️ — на нашу думку, відповідає аксіомам і «коридору» біологічної адекватності, але Вами не "
                    "підтверджено; ❌ — не відповідає, прибрано.", size=10)
    meta = [("Дата", "22 жовтня 2026"), ("Дані й код", "`experiments/isl_transfer_2026-10/`, `notes/scripts_isl/`"),
            ("Протокол", "налаштування лише на dev із train; офіційні тести — один прогін")]
    t = doc.add_table(rows=len(meta), cols=2)
    R._fixed_widths(t, [3.2, 13.4])
    R._cell_margins(t, 30, 30, 0), R._borders(t, inside="#FFFFFF", outer="#FFFFFF")
    for row, (k, v) in zip(t.rows, meta):
        R.add_inline(row.cells[0].paragraphs[0], k, size=9, color=MUTED)
        R.add_inline(row.cells[1].paragraphs[0], v, size=9)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    h = doc.add_paragraph()
    r = h.add_run("Зміст")
    R._set_font(r, R.HEAD_FONT)
    r.font.size, r.font.bold, r.font.color.rgb = Pt(18), True, R._rgb(AFTER_DARK)
    h.paragraph_format.space_after = Pt(10)
    for level, title in sections:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0 if level == 2 else 0.8)
        p.paragraph_format.space_after = Pt(3 if level == 2 else 1)
        R.add_inline(p, title, size=11 if level == 2 else 9.5, bold=level == 2, color=INK if level == 2 else MUTED)


def add_footer(doc):
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    R.add_inline(p, "ISL без матчингу · ", size=8, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    run.append(t)
    fld.append(run)
    p._p.append(fld)


FIG_RE = re.compile(r"^<!--\s*FIG:(\w+)\s*\|\s*(.+?)\s*-->$")


NUM = "\u2063"   # invisible marker: a numbered-list item


def build():
    text = re.sub(r"(?m)^(\s*)\d+\. ", lambda m: f"{m.group(1)}- {NUM}", MD.read_text())
    blocks = R.parse_md(text)
    first = next(i for i, b in enumerate(blocks) if b[0] == "h" and b[1] == 2)
    blocks = blocks[first:]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
    R.setup_styles(doc)
    add_cover(doc, [(b[1], b[2]) for b in blocks if b[0] == "h" and b[1] in (2, 3)])
    add_footer(doc)
    figs = R.Figures(doc)
    made = {}
    for block in blocks:
        kind = block[0]
        if kind == "p":
            m = FIG_RE.match(block[1].strip())
            if m:
                name, caption = m.groups()
                made[name] = made.get(name) or FIGS[name]()
                figs.add(made[name], caption)
                continue
            if block[1].strip().startswith("<!--"):
                continue
            R.add_inline(doc.add_paragraph(), block[1])
        elif kind == "h":
            p = doc.add_paragraph(style="Heading 1" if block[1] == 2 else "Heading 2")
            R.add_inline(p, block[2])
        elif kind == "ul":
            for level, text in block[1]:
                numbered = text.startswith(NUM)
                style = ("List Number" if numbered else "List Bullet") if level == 0 else "List Bullet 2"
                R.add_inline(doc.add_paragraph(style=style), text.lstrip(NUM))
        elif kind == "table":
            R.add_table(doc, block[1])
        elif kind == "code":
            R.add_code(doc, block[1])
    missing = set(FIGS) - set(made)
    if missing:
        raise SystemExit(f"figures not placed: {missing}")
    doc.save(OUT)
    return OUT, len(made)


if __name__ == "__main__":
    print(build())
