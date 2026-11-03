"""Word version of experiments/isl_transfer_2026-10/report_letters.md — the answer to the professor's two letters
(lab log M and N): his model (ComAN) cleaned and improved, the Section IV projection with attractors over sets, his
two-level scheme.

Text and tables come from the markdown; figures and the cover numbers are computed here from the per-image dumps
(ComAN: pl_dump rows scored like coman_rerank.py; the offline models: rows with `stem` / `pred` / `top3`). A paragraph
`<!-- FIG:<name> | <caption> -->` places a figure. Styles and markdown -> docx helpers: notes/scripts_pipeline/pl_report_docx.py.

Usage: letters_report_docx.py  -> experiments/isl_transfer_2026-10/report_letters.docx, figures in tests/_isl/report_figures/
"""
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "notes" / "scripts_pipeline"))
sys.path.insert(0, str(REPO / "notes" / "scripts_isl"))
import pl_report_docx as R  # noqa: E402  (styles, palette, markdown -> docx)
import coman_rerank as K  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

EXP = REPO / "experiments" / "isl_transfer_2026-10"
ISL = REPO / "tests" / "_isl"
DUMPS = ISL / "coman"
R.FIG = ISL / "report_figures"
MD = EXP / "report_letters.md"
OUT = EXP / "report_letters.docx"
CM, INK, MUTED, LINE, FILL = R.CM, R.INK, R.MUTED, R.LINE, R.FILL
AFTER, AFTER_DARK, AFTER_LIGHT, BEFORE, HIGHLIGHT = R.AFTER, R.AFTER_DARK, R.AFTER_LIGHT, R.BEFORE, R.HIGHLIGHT
MANIFEST = {r["image_path"].split("/")[-1][:-4]: r["structure"]
            for r in csv.DictReader(open(REPO / "datasets" / "mnist_all_manifest.csv"))}


def _spec(*names, lam=0.0):
    return "+".join(str(DUMPS / f"{n}.jsonl") for n in names) + f"@{lam}"


COMAN_FINAL = json.loads((ISL / "coman_final_spec.json").read_text()) if (ISL / "coman_final_spec.json").exists() else None
MODELS = {  # official test: name -> ("coman", spec) | ("rows", dump with stem / pred / top3), colour
    "ComAN, як є": (("coman", str(ISL / "coman_mnist_all.jsonl") + "@0.1"), BEFORE),
    "ComAN без «спостерігача»": (("coman", _spec("clean_test")), LINE),
    "ComAN покращена": (("rows", str(ISL / "Q_param_test.jsonl")), AFTER_LIGHT),   # N final + parametric layer (Q2)
    "розділ IV": (("rows", str(ISL / "R_mnist76_test.jsonl")), AFTER_DARK),   # R final
    "дворівнева схема": (("rows", str(ISL / "n2l_V4_mtest.jsonl")), HIGHLIGHT),
}
DEV_STEPS = [  # (label, spec, accepted) — ComAN on dev
    ("модель як є", _spec("m0_dev", lam=0.1), None),
    ("без «спостерігача»", _spec("m1_dev"), None),
    ("+ 28 ознак", _spec("m3_dev"), True),
    ("інтервал за більшістю (τ 0.9)", _spec("m4_N160m9_dev"), False),
    ("+ поступовий штраф", _spec("m5_soft4"), True),
    ("+ три фільтри, MAX", _spec("m5_soft4", "m6_t150", "m6_t190"), True),
    ("+ складність у реакції (§15)", _spec("m5_soft4", "m6_t150", "m6_t190", lam=0.05), True),
    ("+ один детектор", _spec("m9_D110_t110", "m9_D110_t150", "m9_D110_t190", lam=0.05), True),
    ("+ дрібний скелет (4-й фільтр)", _spec("m9_D110_t110", "m9_D110_t150", "m9_D110_t190", "n3_fine_t150", lam=0.05), True),
    ("+ вага ε = 1", _spec("n2_eps1_t110", "n2_eps1_t150", "n2_eps1_t190", lam=0.05), True),
    ("+ правило стійки", _spec("n4_stems_t110", "n4_stems_t150", "n4_stems_t190", lam=0.05), True),
    ("+ концепти з кожного фільтра", _spec("n1_multi_t110", "n1_multi_t150", "n1_multi_t190", lam=0.05), True),
]
if COMAN_FINAL:
    DEV_STEPS.append((COMAN_FINAL["label"], COMAN_FINAL["dev"], True))
_CACHE = {}


def pred(source):
    """{stem: (true, ranked classes)} for a ComAN spec or an offline-model dump."""
    kind, ref = source
    if ref not in _CACHE:
        if kind == "coman":
            _CACHE[ref] = {Path(p).stem: v for p, v in K.predictions(*K.load_spec(ref)).items()}
        else:
            rows = (json.loads(line) for line in open(ref))
            _CACHE[ref] = {r["stem"]: (r["true"], [r["pred"]] + [c for c in r["top3"] if c != r["pred"]]) for r in rows}
    return _CACHE[ref]


def acc(source, part=""):
    p = pred(source)
    if part:
        p = {k: v for k, v in p.items() if MANIFEST.get(k) == part}
    return K.accuracy(p)


def recall(source, digit):
    rows = [cl for t, cl in pred(source).values() if t == digit]
    return 100.0 * sum(1 for cl in rows if cl and cl[0] == digit) / len(rows)


# ----------------------------------------------------------------------------------------------- figures
def fig_models():
    groups = ["complete (бенчмарк)", "усі 10 000", "incomplete"]
    fig, ax = plt.subplots(figsize=(16 * CM, 6.4 * CM))
    x = np.arange(len(groups))
    w = 0.84 / len(MODELS)
    for i, (name, (src, col)) in enumerate(MODELS.items()):
        vals = [acc(src, p)[0] for p in ("complete", "", "incomplete")]
        pos = x - 0.42 + w * (i + 0.5)
        ax.bar(pos, vals, width=w * 0.9, color=col, label=name)
        for p, v in zip(pos, vals):
            ax.text(p, v + 1.2, f"{v:.0f}", ha="center", va="bottom", fontsize=6.6)
    ax.set_xticks(x, groups), ax.set_ylim(0, 105), ax.set_ylabel("top-1, %", color=MUTED)
    ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    R._clean(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=7.0)
    return R._save(fig, "letters_models")


def fig_steps():
    labels = [s[0] for s in DEV_STEPS]
    vals = [acc(("coman", s[1]))[0] for s in DEV_STEPS]
    cols = [BEFORE if a is None else (AFTER if a else LINE) for _, _, a in DEV_STEPS]
    cols[-1] = AFTER_DARK
    fig, ax = plt.subplots(figsize=(16 * CM, 8.4 * CM))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, vals, color=cols, height=0.62)
    for yi, v in zip(y, vals):
        ax.text(v + 0.3, yi, f"{v:.2f}", va="center", fontsize=7.2)
    ax.axvline(vals[0], color=BEFORE, lw=0.8, ls="--")
    ax.set_yticks(y, labels), ax.set_xlim(60, 90), ax.set_xlabel("top-1 на dev, %", color=MUTED)
    ax.grid(axis="x", color=LINE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    R._clean(ax)
    ax.legend(handles=[Patch(color=c, label=l) for c, l in ((BEFORE, "вихідні точки"), (AFTER, "прийнято, кожен окремо"),
                                                           (LINE, "відхилено"), (AFTER_DARK, "усі прийняті разом"))],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, frameon=False, fontsize=7.0)
    return R._save(fig, "letters_steps")


def fig_perdigit():
    shown = ["ComAN, як є", "ComAN покращена", "розділ IV"]
    digits = list("0123456789")
    fig, ax = plt.subplots(figsize=(16 * CM, 5.6 * CM))
    x = np.arange(10)
    for k, name in enumerate(shown):
        src, col = MODELS[name]
        ax.scatter(x + (k - 1) * 0.18, [recall(src, d) for d in digits], color=col, s=30, zorder=3, label=name)
    ax.set_xticks(x, digits), ax.set_ylim(50, 100), ax.set_ylabel("recall, %", color=MUTED)
    ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    R._clean(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=7.5)
    return R._save(fig, "letters_perdigit")


FIGS = {"models": fig_models, "steps": fig_steps, "perdigit": fig_perdigit}


# ----------------------------------------------------------------------------------------------- document
def add_cover(doc, sections):
    base, coman, proj = (MODELS[n][0] for n in ("ComAN, як є", "ComAN покращена", "розділ IV"))
    for _ in range(2):
        doc.add_paragraph()
    p = doc.add_paragraph(style="Title")
    p.add_run("Перевірка Ваших пропозицій")
    p = doc.add_paragraph()
    R.add_inline(p, "Модель Микити без «спостерігача», модель за розділом IV і Ваша дворівнева схема — на тих самих "
                    "76 оригіналах", size=13, color=MUTED)
    p.paragraph_format.space_after = Pt(22)
    tiles = doc.add_table(rows=1, cols=2)
    R._fixed_widths(tiles, [8.3, 8.3])
    R._cell_margins(tiles, 150, 150, 190)
    R._borders(tiles, inside="#FFFFFF", outer="#FFFFFF")
    for cell, (label, runs, sub) in zip(tiles.rows[0].cells, (
            ("Модель Микити, бенчмарк complete",
             [(f"{acc(base, 'complete')[0]:.1f}", 17, BEFORE, False), ("  →  ", 17, MUTED, False),
              (f"{acc(coman, 'complete')[0]:.1f} %", 21, AFTER_DARK, True)],
             f"без ручок з тесту + Ваші пп. 1–2; усі 10 000: {acc(base)[0]:.1f} → {acc(coman)[0]:.1f} %"),
            ("Розділ IV, без матчингу: complete · усі 10 000",
             [(f"{acc(proj, 'complete')[0]:.1f} %", 21, AFTER_DARK, True), ("  ·  ", 13, MUTED, False),
              (f"{acc(proj)[0]:.1f} %", 15, AFTER_DARK, False)],
             f"incomplete {acc(proj, 'incomplete')[0]:.0f} % (у моделі Микити {acc(base, 'incomplete')[0]:.0f} %)"))):
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
    R.add_inline(p, "**Позначення.** ✅ — відповідає теорії, і Ви це прямо пропонували або це є в рукописі; "
                    "⚠️ — на нашу думку, відповідає аксіомам і «коридору» біологічної адекватності, але Вами не "
                    "підтверджено; ❌ — не відповідає, прибрано.", size=10)
    meta = [("Дата", "22–26 жовтня 2026"), ("Дані й код", "`experiments/isl_transfer_2026-10/`, `notes/scripts_isl/`"),
            ("Протокол", "рішення лише на dev із train, за правилом, записаним до запуску; офіційний тест — один прогін "
                         "на кожну фінальну модель")]
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
    R.add_inline(p, "Перевірка Ваших пропозицій · ", size=8, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    run.append(t)
    fld.append(run)
    p._p.append(fld)


FIG_RE = re.compile(r"^<!--\s*FIG:(\w+)\s*\|\s*(.+?)\s*-->$")
NUM = "⁣"   # invisible marker: a numbered-list item


def build():
    text = MD.read_text()
    if "⟨" in text:
        raise SystemExit(f"unfilled placeholders: {sorted(set(re.findall(r'⟨[A-Z_0-9]+⟩', text)))}")
    text = re.sub(r"(?m)^(\s*)\d+\. ", lambda m: f"{m.group(1)}- {NUM}", text)
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
            for level, item in block[1]:
                numbered = item.startswith(NUM)
                style = ("List Number" if numbered else "List Bullet") if level == 0 else "List Bullet 2"
                R.add_inline(doc.add_paragraph(style=style), item.lstrip(NUM))
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
