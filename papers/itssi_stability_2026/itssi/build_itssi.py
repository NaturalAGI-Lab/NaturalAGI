"""Build the ITSSI journal files from the AIS Word submission.

Run: uv run -q --with python-docx --with lxml --with pymupdf python build_itssi.py
"""
import copy
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import docx
import pymupdf
from docx.image.image import Image
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "ais/writing_kit/lapin_ais_2026_submission.docx"
TRANSLATION = HERE / "translation/translation_uk.json"
DRAFTS = {"en": HERE / "drafts/drafts_en.json", "uk": HERE / "drafts/drafts_uk.json"}
REFERENCES = HERE / "drafts/references.json"
OUTPUT = {"en": HERE / "lapin_itssi_2026_en.docx", "uk": HERE / "lapin_itssi_2026_uk.docx"}
SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
EMU_IN = 914400
FONT_HALF_PT = "20"
ABSTRACT_MIN = 1600
ABSTRACT_MAX = 1800
TEXT_HEIGHT_PT = (16838 - 1134 - 1417) / 20
PAGE_TOP_PT = 1134 / 20
LINK_COLOR = "0563C1"

FIGURE_WIDTH_IN = {1: 4.4, 2: 4.8, 3: 3.6, 4: 3.3, 5: 4.1, 6: 2.7, 7: 4.8}
TABLE_CELL_PADDING_TW = "30"

EN_HEADINGS = {
    "1. Introduction": "1 Introduction",
    "1.1 Research Background": "1.1 Background and Significance of the Study",
    "1.2 Literature Review and Problem Statement": "1.2 Literature Review and Problem Statement",
    "1.3 Research Aim and Objectives": "1.3 Aim and Objectives of the Study",
    "2. Materials and Methods": "2 Materials and Methods",
    "3. Results": "3 Results",
    "4. Discussion": "4 Discussion",
    "5. Conclusions": "5 Conclusions",
}
BOLD_LEAD_UK = {
    "p137": "Відхилення до зіставлення",
    "p138": "Структурна невідповідність",
    "p139": "Переважання складності",
}
STATEMENTS = {
    "en": [
        ("Conflict of Interest", "The authors declare that they have no conflict of interest of a financial, personal, professional, or other nature that could have influenced the conduct of the study or the interpretation or publication of its results."),
        ("Funding", "This research received no financial support."),
        ("Data Availability", "The data supporting the findings of this study are available in the NaturalAGI repository at https://github.com/NaturalAGI-Lab/NaturalAGI."),
        ("Use of Artificial Intelligence Tools", "The authors confirm that no generative artificial intelligence or AI-assisted tools were used in the preparation of this manuscript to create text or images, generate or analyse data, or formulate conclusions."),
    ],
    "uk": [
        ("Конфлікт інтересів", "Автори заявляють про відсутність конфлікту інтересів, зокрема фінансового, особистого, професійного чи іншого характеру, який міг би вплинути на проведення дослідження, інтерпретацію або публікацію його результатів."),
        ("Фінансування", "Дослідження виконано без фінансової підтримки."),
        ("Доступність даних", "Дані, що підтверджують результати цього дослідження, доступні в репозитарії NaturalAGI за посиланням https://github.com/NaturalAGI-Lab/NaturalAGI."),
        ("Використання інструментів штучного інтелекту", "Автори підтверджують, що під час підготовки цього рукопису не використовували генеративний штучний інтелект або інструменти на його основі для створення тексту чи зображень, генерування або аналізу даних, а також формулювання висновків."),
    ],
}
RELEVANCE = {
    "en": "Therefore, research on … is timely and relevant.",
    "uk": "Отже, дослідження, присвячене …, є актуальним.",
}
NOTES = {
    "en": "[Author note: the abstract has {n} characters with spaces; {m} more are needed to reach {lo}.]",
    "uk": "[Примітка автору: анотація має {n} {n_unit} із пробілами; до {lo} потрібно ще {m} {m_unit}.]",
}
UK_CHAR_FORMS = ("знак", "знаки", "знаків")
UK_SAMPLE_FORMS = ("зразок", "зразки", "зразків")
HEAD_BODY = {"en": ("1 Introduction", "Conflict of Interest"), "uk": ("1 Вступ", "Конфлікт інтересів")}
RECEIVED = {
    "en": ["Received xx.xx.2026", "Accepted for publication xx.xx.2026", "Published xx.xx.2026"],
    "uk": [
        "Received (Надійшла до редакції) xx.xx.2026",
        "Accepted for publication (Прийнято до друку) xx.xx.2026",
        "Published (Опубліковано) xx.xx.2026",
    ],
}
PHONE_LABEL = {"en": "tel.:", "uk": "тел.:"}
PHONE_UA = "+38 (0__) ___-__-__"
PHONE_US = "+1 (___) ___-____"
US_AFFILIATION = "Augusta University"
ABOUT = {"en": "About the Authors", "uk": "Відомості про авторів / About the Authors"}
# Edits to the source text: EN edits apply to the AIS docx paragraph; the UK side
# is already in translation_uk.json and is only asserted there.
TEXT_EDITS = {
    "en": [("p64", "until sample 15.", "until sample 15 (Fig. 1).")],
    "uk": [("p64", "до зразка 15.", "до зразка 15 (рис. 1).")],
}

CITE_RE = re.compile(r"\[((?:n?\d+(?:\s*[–-]\s*n?\d+)?)(?:,\s*n?\d+(?:\s*[–-]\s*n?\d+)?)*)\]")
RANGE_RE = re.compile(r"(n?)(\d+)\s*[–-]\s*n?(\d+)")
URL_RE = re.compile(r"https?://\S+")
QUOTE_TABLE = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"'})
PLACEHOLDER_RE = re.compile(r"(⟦M\d+⟧|\t)")
FORMULA_RE = re.compile(r"⟦M\d+⟧")
SPACED_HYPHEN_RE = re.compile(r"(?<=\S) - (?=\S)")
NUMERIC_RANGE_RE = re.compile(r"(?<![\w.,/–-])(\d+)-(\d+)(?![\w/–-]|[.,]\d)")
GLUED_FORMULA_RE = re.compile(r"(?<=[^\s(\[])(?=⟦M\d+⟧)")
UK_SAMPLES_RE = re.compile(r"\bза (\d+) (зразк\w*)")
FIGURE_MENTION_RE = re.compile(
    r"(?:Figs?\.|Figures?|[Рр]ис\.)\s*\d+[a-z]?(?:\s*(?:,|and|і|та|–)\s*(?:Figs?\.|Figures?|[Рр]ис\.)?\s*\d+[a-z]?)*")
CAPTION_RE = re.compile(r"(?:Fig\.|Рис\.) (\d+)\. ")
RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
             "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
             "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
             "vertAlign", "rtl", "cs", "em", "lang"]


class BuildError(Exception):
    pass


def check(cond: bool, message: str) -> None:
    if not cond:
        raise BuildError(message)


def must_search(pattern: str, text: str) -> re.Match[str]:
    m = re.search(pattern, text)
    if m is None:
        raise BuildError(f"pattern {pattern!r} not found in {text[:60]!r}")
    return m


def uk_plural(n: int, forms: tuple[str, str, str]) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


# ----------------------------------------------------------------- typography

def typeset_plain(text: str) -> str:
    text = SPACED_HYPHEN_RE.sub(" – ", text)
    return NUMERIC_RANGE_RE.sub(r"\1–\2", text)


def typeset(text: str) -> str:
    """En dashes for spaced hyphens and numeric ranges, outside URLs; keeps the length."""
    out, pos = [], 0
    for m in URL_RE.finditer(text):
        out += [typeset_plain(text[pos:m.start()]), m.group(0)]
        pos = m.end()
    out.append(typeset_plain(text[pos:]))
    return "".join(out)


def space_formulas(text: str) -> str:
    return GLUED_FORMULA_RE.sub(" ", text)


# ---------------------------------------------------------------- XML helpers

def w(tag: str) -> str:
    return qn(f"w:{tag}")


def in_math(el) -> bool:
    return any(a.tag == M + "oMath" for a in el.iterancestors())


def text_of(p) -> str:
    return "".join(t.text or "" for t in p.iter(w("t")) if not in_math(t))


def rpr_set(rpr, name: str, **attrs: str) -> None:
    el = rpr.find(w(name))
    if el is None:
        el = OxmlElement(f"w:{name}")
        later = RPR_ORDER[RPR_ORDER.index(name) + 1:]
        anchor = next((c for c in rpr if c.tag.split("}")[1] in later), None)
        if anchor is None:
            rpr.append(el)
        else:
            anchor.addprevious(el)
    for key, val in attrs.items():
        el.set(w(key), val)


def make_rpr(bold: bool, italic: bool, highlight: bool, lang: str):
    rpr = OxmlElement("w:rPr")
    if bold:
        rpr_set(rpr, "b")
        rpr_set(rpr, "bCs")
    if italic:
        rpr_set(rpr, "i")
        rpr_set(rpr, "iCs")
    rpr_set(rpr, "color", val="000000")
    rpr_set(rpr, "sz", val=FONT_HALF_PT)
    rpr_set(rpr, "szCs", val=FONT_HALF_PT)
    if highlight:
        rpr_set(rpr, "highlight", val="yellow")
    rpr_set(rpr, "lang", val=lang)
    return rpr


def make_run(text: str, bold=False, italic=False, highlight=False, lang="en-US"):
    r = OxmlElement("w:r")
    r.append(make_rpr(bold, italic, highlight, lang))
    parts = text.split("\t")
    for i, part in enumerate(parts):
        if i:
            r.append(OxmlElement("w:tab"))
        if part:
            t = OxmlElement("w:t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = part
            r.append(t)
    return r


def clear_content(p) -> None:
    for child in list(p):
        if child.tag != w("pPr"):
            p.remove(child)


def new_paragraph(ppr_source) -> BaseOxmlElement:
    p = OxmlElement("w:p")
    if not isinstance(p, BaseOxmlElement):
        raise BuildError("python-docx created a w:p outside its element classes")
    ppr = ppr_source.find(w("pPr"))
    if ppr is not None:
        p.append(copy.deepcopy(ppr))
    return p


def simple_paragraph(ppr_source, text: str, lang: str, bold=False, highlight=False):
    p = new_paragraph(ppr_source)
    p.append(make_run(text, bold=bold, highlight=highlight, lang=lang))
    return p


# ------------------------------------------------------------ source indexing

class Item:
    def __init__(self, item_id: str, kind: str, el, text: str) -> None:
        self.id, self.kind, self.el, self.text = item_id, kind, el, text

    @property
    def paragraph(self):
        return self.el if self.kind == "p" else self.el.find(w("p"))


def walk_items(children, start: str, stop: str, count_all_math=True):
    """Same traversal as translation/extract.py; returns items and the OMML list."""
    items, omaths, started = [], [], False

    def ptext(p) -> str:
        out = []
        for el in p.iter():
            if el.tag == M + "oMath":
                omaths.append(el)
                out.append(f"⟦M{len(omaths)}⟧")
            elif el.tag == w("t") and not in_math(el):
                out.append(el.text or "")
            elif el.tag == w("tab") and not in_math(el):
                out.append("\t")
        return "".join(out)

    for child in children:
        if child.tag == w("p"):
            t = ptext(child)
            if t.strip() == start:
                started = True
            if t.strip() == stop:
                break
            if started and t.strip():
                items.append(Item(f"p{len(items) + 1}", "p", child, t))
        elif child.tag == w("tbl") and started:
            for ci, tc in enumerate(child.iter(w("tc"))):
                t = "".join(ptext(p) for p in tc.iter(w("p")))
                if t.strip():
                    items.append(Item(f"t{ci}", "cell", tc, t))
    return items, omaths


def split_source(kids: list) -> dict:
    texts = [text_of(k) if k.tag == w("p") else "" for k in kids]

    def find(pred) -> int:
        return next(i for i, t in enumerate(texts) if pred(t))

    i_intro = find(lambda t: t == "1. Introduction")
    i_conf = find(lambda t: t.startswith("Conflicts of interest."))
    i_refs = find(lambda t: t == "References")
    i_recv = find(lambda t: t.startswith("Received"))
    i_about = find(lambda t: t.startswith("ВІДОМОСТІ"))
    check(texts[0].startswith("UDC") and texts[11].startswith("Abstract.") and texts[12].startswith("Keywords:"), "front matter layout changed")
    check(texts[5].startswith("Анотація") and texts[6].startswith("Ключові слова"), "Ukrainian front matter layout changed")
    authors = [kids[i:i + 4] for i in range(i_about + 1, len(kids) - 1, 4)]
    check(len(authors) == 5 and all(len(a) == 4 for a in authors), "author blocks layout changed")
    return {
        "udc": kids[0], "ua_head": kids[1:4], "ua_title": kids[4], "ua_abs": kids[5], "ua_kw": kids[6],
        "en_head": kids[7:10], "en_title": kids[10], "en_abs": kids[11], "en_kw": kids[12],
        "body": kids[i_intro:i_conf], "statement": kids[i_conf], "ref_head": kids[i_refs],
        "ref_sample": kids[i_refs + 1], "received": kids[i_recv], "about": kids[i_about], "authors": authors,
        "sect": kids[-1],
    }


# ----------------------------------------------------------- text replacement

def italic_tokens(p) -> list[str]:
    tokens = []
    for r in p.findall(w("r")):
        rpr = r.find(w("rPr"))
        italic = rpr is not None and rpr.find(w("i")) is not None and rpr.find(w("i")).get(w("val")) != "0"
        sub = rpr is not None and rpr.find(w("vertAlign")) is not None
        text = "".join(t.text or "" for t in r.findall(w("t"))).strip()
        if italic and text and not sub:
            tokens.append(text)
    return tokens


def is_bold(r) -> bool:
    rpr = r.find(w("rPr"))
    b = rpr.find(w("b")) if rpr is not None else None
    return b is not None and b.get(w("val")) not in ("0", "false")


def bold_profile(p) -> tuple[bool, bool]:
    runs = [r for r in p.findall(w("r")) if "".join(t.text or "" for t in r.findall(w("t"))).strip()]
    if not runs:
        return False, False
    return all(is_bold(r) for r in runs), is_bold(runs[0])


def split_italics(text: str, tokens: list[str]) -> list[tuple[str, bool]]:
    if not tokens:
        return [(text, False)]
    pattern = "|".join(r"(?<!\w)" + re.escape(t) + r"(?!\w)" for t in sorted(set(tokens), key=len, reverse=True))
    out, pos = [], 0
    for m in re.finditer(pattern, text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def set_text(p, text: str, omaths: dict, lang: str, bold_all=False, bold_lead="", tokens=(), highlight=False) -> None:
    clear_content(p)
    if bold_lead:
        check(text.startswith(bold_lead), f"bold lead {bold_lead!r} not at start of {text[:40]!r}")
        p.append(make_run(bold_lead, bold=True, highlight=highlight, lang=lang))
        text = text[len(bold_lead):]
    for piece in PLACEHOLDER_RE.split(text):
        if not piece:
            continue
        if piece.startswith("⟦"):
            p.append(copy.deepcopy(omaths[int(piece[2:-1])]))
            continue
        for chunk, italic in split_italics(piece, list(tokens)):
            p.append(make_run(chunk, bold=bold_all, italic=italic, highlight=highlight, lang=lang))


# ------------------------------------------------------------------ citations

def expand_cite(body: str) -> list[str]:
    keys = []
    for token in (t.strip() for t in body.split(",")):
        m = RANGE_RE.fullmatch(token)
        if m:
            keys += [f"{m.group(1)}{k}" for k in range(int(m.group(2)), int(m.group(3)) + 1)]
        else:
            keys.append(token)
    return keys


def first_mention_order(texts: list[str]) -> list[str]:
    order: list[str] = []
    for text in texts:
        for m in CITE_RE.finditer(text):
            for key in expand_cite(m.group(1)):
                if key not in order:
                    order.append(key)
    return order


def compress(numbers: list[int]) -> str:
    out, i = [], 0
    while i < len(numbers):
        j = i
        while j + 1 < len(numbers) and numbers[j + 1] == numbers[j] + 1:
            j += 1
        if j - i >= 2:
            out.append(f"{numbers[i]}–{numbers[j]}")
        else:
            out += [str(n) for n in numbers[i:j + 1]]
        i = j + 1
    return ", ".join(out)


def renumber(match: re.Match, mapping: dict[str, int]) -> str:
    keys = expand_cite(match.group(1))
    missing = [k for k in keys if k not in mapping]
    check(not missing, f"citation keys without a mapping: {missing}")
    return "[" + compress(sorted(mapping[k] for k in keys)) + "]"


def rewrite_paragraph(p, pattern: re.Pattern, fn) -> None:
    nodes = [t for r in p.findall(w("r")) for t in r.findall(w("t"))]
    texts = [n.text or "" for n in nodes]
    starts = [sum(len(t) for t in texts[:i]) for i in range(len(texts))]
    full = "".join(texts)
    edits = [(m.start(), m.end(), fn(m)) for m in pattern.finditer(full)]
    for s, e, rep in reversed(edits):
        first = True
        for node, a in zip(nodes, starts):
            text = node.text or ""
            lo, hi = max(s, a) - a, min(e, a + len(text)) - a
            if hi <= lo:
                continue
            node.text = text[:lo] + (rep if first else "") + text[hi:]
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            first = False


def edit_paragraph(p, old: str, new: str) -> None:
    count = text_of(p).count(old)
    check(count == 1, f"text edit {old!r} found {count} times, expected once")
    rewrite_paragraph(p, re.compile(re.escape(old)), lambda m: new)
    check(text_of(p).count(new) == 1, f"text edit {new!r} not applied")


def edited_text(text: str, edits: list[tuple[str, str]]) -> str:
    for old, new in edits:
        check(text.count(old) == 1, f"text edit {old!r} found {text.count(old)} times, expected once")
        text = text.replace(old, new)
    return text


def edits_for(lang: str, item_id: str) -> list[tuple[str, str]]:
    return [(old, new) for i, old, new in TEXT_EDITS[lang] if i == item_id]


def check_uk_edits(translation: dict) -> None:
    for item_id, old, new in TEXT_EDITS["uk"]:
        uk = translation[item_id]["uk"]
        check(uk.count(new) == 1 and old not in uk, f"{item_id}: translation_uk.json lacks the edit {new!r}")


def typeset_paragraph(p) -> None:
    nodes = [t for t in p.iter(w("t")) if not in_math(t)]
    full = "".join(n.text or "" for n in nodes)
    new = typeset(full)
    check(len(new) == len(full), "typography changed the text length")
    pos = 0
    for n in nodes:
        size = len(n.text or "")
        if new[pos:pos + size] != (n.text or ""):
            n.text = new[pos:pos + size]
        pos += size


def space_before_formulas(p) -> None:
    for omath in p.findall(M + "oMath"):
        prev = omath.getprevious()
        if prev is None or prev.tag != w("r") or not len(prev) or prev[-1].tag != w("t") or not prev[-1].text:
            continue
        t = prev[-1]
        if GLUED_FORMULA_RE.search(t.text[-1] + "⟦M0⟧"):
            t.text += " "
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


# ------------------------------------------------------------------ hyperlinks

def trim_url(url: str) -> str:
    while url and (url[-1] in '.,;:"\'' or (url[-1] == ")" and url.count("(") < url.count(")"))):
        url = url[:-1]
    return url


def make_hyperlink(doc, url: str, rpr_source):
    h = OxmlElement("w:hyperlink")
    h.set(R_NS + "id", doc.part.relate_to(url, RT.HYPERLINK, is_external=True))
    r = OxmlElement("w:r")
    if rpr_source is not None:
        rpr = copy.deepcopy(rpr_source)
        rpr_set(rpr, "color", val=LINK_COLOR)
        r.append(rpr)
    t = OxmlElement("w:t")
    t.text = url
    r.append(t)
    h.append(r)
    return h


def linkify(doc, p) -> None:
    for r in list(p.findall(w("r"))):
        ts = r.findall(w("t"))
        if len(ts) != 1 or not URL_RE.search(ts[0].text or ""):
            continue
        text, rpr = ts[0].text, r.find(w("rPr"))
        extra = [c.tag for c in r if c.tag not in (w("rPr"), w("t"))]
        check(not extra, f"run with a URL also holds {extra}; linkify would drop them")
        pieces, pos = [], 0
        for m in URL_RE.finditer(text):
            url = trim_url(m.group(0))
            pieces.append(("t", text[pos:m.start()]))
            pieces.append(("u", url))
            pos = m.start() + len(url)
        pieces.append(("t", text[pos:]))
        anchor = r
        for kind, value in pieces:
            if not value:
                continue
            if kind == "u":
                new = make_hyperlink(doc, value, rpr)
            else:
                new = OxmlElement("w:r")
                if rpr is not None:
                    new.append(copy.deepcopy(rpr))
                t = OxmlElement("w:t")
                t.text = value
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                new.append(t)
            anchor.addnext(new)
            anchor = new
        r.getparent().remove(r)


# ---------------------------------------------------------------- normalisation

def normalise_formatting(root) -> None:
    for u in list(root.iter(w("u"))):
        u.getparent().remove(u)
    for tag in ("sz", "szCs"):
        for el in root.iter(w(tag)):
            if el.getparent().tag == w("rPr"):
                el.set(w("val"), FONT_HALF_PT)
    for spacing in root.iter(w("spacing")):
        if spacing.getparent().tag == w("pPr") and spacing.get(w("line")) is not None:
            spacing.set(w("line"), "240")
            spacing.set(w("lineRule"), "auto")


def tighten_tables(root) -> None:
    for mar in root.iter(w("tcMar")):
        for side in ("top", "bottom"):
            mar.find(w(side)).set(w("w"), TABLE_CELL_PADDING_TW)


def replace_quotes(root) -> None:
    for t in root.iter(w("t")):
        if t.text:
            t.text = t.text.translate(QUOTE_TABLE)


# -------------------------------------------------------------------- figures

def scale_figures(doc, root) -> list[dict]:
    report = []
    for n, drawing in enumerate(root.iter(w("drawing")), start=1):
        inline = drawing.find(WP + "inline")
        extent = inline.find(WP + "extent")
        embed = inline.find(f".//{A}blip").get(R_NS + "embed")
        image = Image.from_blob(doc.part.related_parts[embed].blob)
        width_in = FIGURE_WIDTH_IN[n]
        cx = round(width_in * EMU_IN)
        cy = round(cx * image.px_height / image.px_width)
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))
        for ext in inline.iter(A + "ext"):
            ext.set("cx", str(cx))
            ext.set("cy", str(cy))
        report.append({"n": n, "px": (image.px_width, image.px_height), "width_in": width_in,
                       "height_in": cy / EMU_IN, "dpi": image.px_width / width_in})
    return report


# ----------------------------------------------------------------- the builder

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_drafts(lang: str) -> list[dict]:
    """Drafts for one language; both files must hold the same ids and the same English text."""
    en = load_json(DRAFTS["en"])
    uk = load_json(DRAFTS["uk"])
    check([d["id"] for d in en] == [d["id"] for d in uk], "drafts_en and drafts_uk hold different ids")
    for de, du in zip(en, uk):
        check(de["en"] == du["en"], f"draft {de['id']}: English text differs between drafts_en and drafts_uk")
        check(de.get("after") == du.get("after") and de.get("replace") == du.get("replace"),
              f"draft {de['id']}: placement differs between drafts_en and drafts_uk")
    drafts = en if lang == "en" else uk
    for d in drafts:
        check(bool(d.get(lang)), f"draft {d['id']} has no {lang!r} text")
    return drafts


def needs_translation(text: str) -> bool:
    """True when the text holds a letter; formula slots, numbers and ids like 2_2 do not count."""
    return re.search(r"[^\W\d_]", FORMULA_RE.sub("", text)) is not None


def apply_body_text(lang: str, items: list[Item], omaths: dict, translation: dict,
                    drafts: list[dict]) -> dict[str, BaseOxmlElement]:
    """Rewrite headings, translated text and drafts; return id -> paragraph element for inserted drafts."""
    by_id = {it.id: it for it in items}
    created: dict[str, BaseOxmlElement] = {}
    if lang == "en":
        for it in items:
            if it.text in EN_HEADINGS and it.text != EN_HEADINGS[it.text]:
                set_text(it.paragraph, EN_HEADINGS[it.text], omaths, "en-US", bold_all=True)
        for item_id, old, new in TEXT_EDITS["en"]:
            edit_paragraph(by_id[item_id].paragraph, old, new)
    else:
        check_uk_edits(translation)
        for it in items:
            if it.id in translation and it.id in by_id:
                p = it.paragraph
                all_bold, first_bold = bold_profile(p)
                lead = BOLD_LEAD_UK.get(it.id, "")
                check(not (first_bold and not all_bold) or bool(lead), f"{it.id}: bold lead label has no Ukrainian mapping")
                set_text(p, translation[it.id]["uk"], omaths, "uk-UA", bold_all=all_bold, bold_lead=lead, tokens=italic_tokens(p))
    for d in drafts:
        text = d[lang]
        check("⟦" not in text, f"draft {d['id']} contains a formula slot")
        if d.get("replace"):
            p = by_id[d["id"]].paragraph
            set_text(p, text, omaths, "en-US" if lang == "en" else "uk-UA", highlight=True)
            created[d["id"]] = p
        else:
            anchor = created[d["after"]] if d["after"] in created else by_id[d["after"]].paragraph
            inserted = new_paragraph(anchor)
            set_text(inserted, text, omaths, "en-US" if lang == "en" else "uk-UA", highlight=True)
            anchor.addnext(inserted)
            created[d["id"]] = inserted
    return created


def add_relevance(lang: str, items: list[Item]) -> None:
    last = next(it for it in items if it.id == "p6").paragraph
    p = new_paragraph(last)
    p.append(make_run(RELEVANCE[lang], highlight=True, lang="en-US" if lang == "en" else "uk-UA"))
    last.addnext(p)


def abstract_note(p, note_lang: str, label: str) -> int:
    text = text_of(p).strip()
    check(text.startswith(label), f"abstract label {label!r} missing")
    body = text[len(label):].strip()
    n = len(body)
    missing = max(ABSTRACT_MIN - n, 0)
    note = NOTES[note_lang].format(n=n, m=missing, lo=ABSTRACT_MIN, n_unit=uk_plural(n, UK_CHAR_FORMS),
                                   m_unit=uk_plural(missing, UK_CHAR_FORMS))
    p.append(make_run(" " + note, highlight=True, lang="en-US" if note_lang == "en" else "uk-UA"))
    return n


def space_after_ukrainian_label(p) -> None:
    for t in p.iter(w("t")):
        if t.text == ".":
            t.text = ". "
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            return


def live_body(src: dict) -> list:
    """Body elements after all insertions, without empty and section-break paragraphs."""
    stop = src["statement"]
    kept = []
    for el in [src["body"][0], *src["body"][0].itersiblings()]:
        if el is stop:
            break
        if el.tag == w("tbl") or text_of(el).strip() or list(el.iter(w("drawing"))):
            kept.append(el)
    return kept


def statements_block(src: dict, lang: str) -> list:
    heading_ppr, text_ppr = src["body"][0], src["body"][2]
    code = "en-US" if lang == "en" else "uk-UA"
    out = []
    for heading, text in STATEMENTS[lang]:
        out.append(simple_paragraph(heading_ppr, heading, code, bold=True))
        out.append(simple_paragraph(text_ppr, text, code))
    return out


def reference_paragraphs(src: dict, refs: dict[str, str], order: list[str]) -> list:
    out = []
    for number, key in enumerate(order, start=1):
        p = new_paragraph(src["ref_sample"])
        p.append(make_run(f"{number}. "))
        for i, part in enumerate(refs[key].split("*")):
            if part:
                p.append(make_run(part, italic=bool(i % 2)))
        check(refs[key].count("*") % 2 == 0, f"unbalanced italic markup in reference {key}")
        out.append(p)
    return out


def contact_line(block: list) -> str:
    first, second = text_of(block[2]), text_of(block[3])
    email = must_search(r"e-mail:\s*(\S+?);", first).group(1)
    orcid = must_search(r"https://orcid\.org/[\dX-]+", first).group(0)
    scopus = must_search(r"authorId=(\d+)", second).group(1)
    return (f"email: {email}; ORCID ID: {orcid}; "
            f"Scopus Author ID: https://www.scopus.com/authid/detail.uri?authorId={scopus}")


def author_paragraphs(src: dict, lang: str) -> list:
    code = "en-US" if lang == "en" else "uk-UA"
    out = [simple_paragraph(src["about"], ABOUT[lang], code, bold=True)]
    us = [US_AFFILIATION in text_of(block[1]) for block in src["authors"]]
    check(sum(us) == 1, f"expected one author at {US_AFFILIATION}, found {sum(us)}")
    for block, in_us in zip(src["authors"], us):
        out += [block[0], block[1], simple_paragraph(block[2], contact_line(block), "en-US")]
        phone = f"{PHONE_LABEL[lang]} {PHONE_US if in_us else PHONE_UA}"
        out.append(simple_paragraph(block[3], phone, code, highlight=True))
    return out


def received_paragraphs(src: dict, lang: str) -> list:
    return [simple_paragraph(src["received"], text, "en-US") for text in RECEIVED[lang]]


def build(lang: str, shared: dict) -> dict:
    doc = docx.Document(SOURCE)
    body = doc.element.body
    kids = list(body)
    src = split_source(kids)
    start, stop = HEAD_BODY[lang]
    translation = {x["id"]: x for x in load_json(TRANSLATION)}
    items, omath_list = walk_items(src["body"], "1. Introduction", "References")
    omaths = {i + 1: copy.deepcopy(o) for i, o in enumerate(omath_list)}
    check(len(omaths) == 28, f"expected 28 formulas, found {len(omaths)}")
    untranslated = [it.id for it in items if it.id not in translation and needs_translation(it.text)]
    check(not untranslated, f"untranslated items with words: {untranslated}")
    apply_body_text(lang, items, omaths, translation, load_drafts(lang))
    add_relevance(lang, items)

    body_paras = live_body(src)
    paragraphs = [p for k in body_paras for p in ([k] if k.tag == w("p") else k.iter(w("p")))]
    for p in [*paragraphs, src["en_abs"], src["ua_abs"]]:
        typeset_paragraph(p)
    for p in paragraphs:
        space_before_formulas(p)

    notes = {}
    space_after_ukrainian_label(src["ua_abs"])
    notes["en"] = abstract_note(src["en_abs"], "en", "Abstract.")
    notes["uk"] = abstract_note(src["ua_abs"], "uk", "Анотація.")

    en_order_texts = [text_of(p) for p in paragraphs]
    if lang == "en":
        order = first_mention_order(en_order_texts)
        shared["order"] = order
    order = shared["order"]
    mapping = {key: i + 1 for i, key in enumerate(order)}
    check(set(first_mention_order(en_order_texts)) == set(order), "cited keys differ between language files")
    refs = load_json(REFERENCES)
    check(set(order) <= set(refs), f"cited keys without a reference: {sorted(set(order) - set(refs))}")
    check(set(refs) <= set(order), f"references never cited: {sorted(set(refs) - set(order))}")
    for p in paragraphs:
        rewrite_paragraph(p, CITE_RE, lambda m: renumber(m, mapping))

    ordered = [src["udc"], *src["en_head"], src["en_title"], src["en_abs"], src["en_kw"], *body_paras,
               *statements_block(src, lang), copy.deepcopy(src["ref_head"]),
               *reference_paragraphs(src, refs, order), *received_paragraphs(src, lang),
               *author_paragraphs(src, lang),
               *src["ua_head"], src["ua_title"], src["ua_abs"], src["ua_kw"]]
    for child in kids:
        body.remove(child)
    for el in ordered:
        body.append(el)
    sect = src["sect"]
    for cols in sect.findall(w("cols")):
        sect.remove(cols)
    body.append(sect)

    replace_quotes(body)
    normalise_formatting(body)
    tighten_tables(body)
    for p in list(body.iter(w("p"))):
        linkify(doc, p)
    figures = scale_figures(doc, body)
    doc.save(OUTPUT[lang])
    return {"notes": notes, "figures": figures, "order": order}


# ------------------------------------------------------------------------ PDF

def convert_pdf(path: Path) -> Path:
    pdf = path.with_suffix(".pdf")
    pdf.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([SOFFICE, f"-env:UserInstallation={Path(profile).as_uri()}", "--headless",
                        "--convert-to", "pdf", "--outdir", str(path.parent), str(path)],
                       check=True, capture_output=True)
    check(pdf.exists(), f"LibreOffice did not create {pdf.name}")
    return pdf


def heading_position(pdf, text: str) -> tuple[int, float]:
    for n, page in enumerate(pdf):
        for block in page.get_text("blocks"):
            if block[4].strip().split("\n")[0].strip() == text:
                return n, block[1]
    raise BuildError(f"heading {text!r} not found in PDF")


def figure_area(pdf) -> tuple[float, int]:
    """Estimated points of page height used by figures, captions and the table, and pages touched."""
    total, pages = 0.0, set()
    for n, page in enumerate(pdf):
        total_page = 0.0
        for info in page.get_image_info():
            total_page += info["bbox"][3] - info["bbox"][1]
        for block in page.get_text("blocks"):
            if re.match(r"(Fig\.|Рис\.|Table \d|Таблиця \d)", block[4].strip()):
                total_page += block[3] - block[1] + 14
        for table in page.find_tables().tables:
            total_page += table.bbox[3] - table.bbox[1]
        if total_page:
            pages.add(n)
        total += total_page
    return total, len(pages)


def pdf_report(lang: str, pdf_path: Path) -> dict:
    pdf = pymupdf.open(pdf_path)
    start, stop = HEAD_BODY[lang]
    p0, y0 = heading_position(pdf, start)
    p1, y1 = heading_position(pdf, stop)
    body_pages = (p1 - p0) + (y1 - y0) / TEXT_HEIGHT_PT
    area, touched = figure_area(pdf)
    return {"total_pages": len(pdf), "body_pages": body_pages, "body_page_span": p1 - p0 + 1,
            "figure_table_pages": area / TEXT_HEIGHT_PT, "figure_pages_touched": touched}


# ----------------------------------------------------------------- verification

def output_items(lang: str) -> list[Item]:
    children = list(docx.Document(OUTPUT[lang]).element.body)
    start, stop = HEAD_BODY[lang]
    return walk_items(children, start, stop)[0]


def expected_texts(lang: str, order: list[str]) -> list[str]:
    """Source body text with every known change applied at string level."""
    mapping = {key: i + 1 for i, key in enumerate(order)}
    src_items, _ = walk_items(list(docx.Document(SOURCE).element.body), "1. Introduction", "References")
    translation = {x["id"]: x for x in load_json(TRANSLATION)}
    drafts = load_drafts(lang)
    cut = next(i for i, it in enumerate(src_items) if it.text.startswith("Conflicts of interest."))
    src_items = src_items[:cut]
    texts = {it.id: it.text for it in src_items}
    seq = [it.id for it in src_items]
    for it in src_items:
        if lang == "en":
            heading = EN_HEADINGS[it.text] if it.text in EN_HEADINGS else it.text
            texts[it.id] = edited_text(heading, edits_for("en", it.id))
        elif it.id in translation:
            texts[it.id] = translation[it.id]["uk"]
    for d in drafts:
        texts[d["id"]] = d[lang]
        if not d.get("replace"):
            seq.insert(seq.index(d["after"]) + 1, d["id"])
    seq.insert(seq.index("p6") + 1, "relevance")
    texts["relevance"] = RELEVANCE[lang]
    out = [space_formulas(typeset(texts[i])) for i in seq]
    return [CITE_RE.sub(lambda m: renumber(m, mapping), t).translate(QUOTE_TABLE) for t in out]


def norm(s: str) -> str:
    return "".join(s.split())


def verify_text(lang: str, order: list[str]) -> list[str]:
    got = [norm(it.text) for it in output_items(lang)]
    want = [norm(t) for t in expected_texts(lang, order)]
    problems = []
    if len(got) != len(want):
        problems.append(f"{lang}: body item count {len(got)} != expected {len(want)}")
    for i, (g, e) in enumerate(zip(got, want)):
        if g != e:
            problems.append(f"{lang}: body item {i} differs:\n    got  {g[:120]}\n    want {e[:120]}")
    return problems


def verify_structure(lang: str, refs: dict) -> tuple[list[str], dict]:
    doc = docx.Document(OUTPUT[lang])
    body = doc.element.body
    problems, stats = [], {}
    stats["omml"] = len(list(body.iter(M + "oMath")))
    stats["images"] = len(list(body.iter(w("drawing"))))
    stats["tables"] = len(list(body.iter(w("tbl"))))
    stats["sections"] = len(list(body.iter(w("sectPr"))))
    stats["columns"] = len(list(body.iter(w("cols"))))
    stats["underlines"] = len(list(body.iter(w("u"))))
    stats["empty_cells"] = sum(1 for tc in body.iter(w("tc")) if not "".join(text_of(p) for p in tc.iter(w("p"))).strip() and not list(tc.iter(M + "oMath")))
    stats["sizes"] = sorted({el.get(w("val")) for el in body.iter(w("sz"))})
    stats["straight_quote_violations"] = sum(len(re.findall("[«»“”„]", text_of(p))) for p in body.iter(w("p")))
    for name, want in (("omml", 28), ("images", 7), ("tables", 1), ("sections", 1)):
        if stats[name] != want:
            problems.append(f"{lang}: {name} = {stats[name]}, expected {want}")
    for name in ("columns", "underlines", "empty_cells", "straight_quote_violations"):
        if stats[name]:
            problems.append(f"{lang}: {name} = {stats[name]}")
    if stats["sizes"] != [FONT_HALF_PT]:
        problems.append(f"{lang}: font sizes {stats['sizes']}")
    return problems, stats


def verify_references(lang: str, order: list[str], refs: dict) -> tuple[list[str], dict]:
    paras = [text_of(p) for p in docx.Document(OUTPUT[lang]).element.body.iter(w("p"))]
    start = paras.index("References")
    printed = []
    for text in paras[start + 1:]:
        m = re.match(r"(\d+)\. ", text)
        if not m:
            break
        printed.append(text)
    years = [int(must_search(r"\((\d{4})\)", t).group(1)) for t in printed]
    stats = {"count": len(printed), "doi": sum("https://doi.org/" in t for t in printed),
             "recent": sum(y >= 2023 for y in years)}
    problems = []
    if len(printed) != 52:
        problems.append(f"{lang}: {len(printed)} references, expected 52")
    if stats["doi"] < 0.9 * len(printed):
        problems.append(f"{lang}: DOI share {stats['doi']}/{len(printed)} below 90 %")
    if stats["recent"] < 0.5 * len(printed):
        problems.append(f"{lang}: 2023+ share {stats['recent']}/{len(printed)} below 50 %")
    expected = [f"{i}. " + refs[k].replace("*", "") for i, k in enumerate(order, start=1)]
    if [norm(t) for t in printed] != [norm(t) for t in expected]:
        problems.append(f"{lang}: printed references differ from references.json order")
    body_text = "\n".join(it.text for it in output_items(lang))
    first_seen: list[int] = []
    for m in CITE_RE.finditer(body_text):
        for key in expand_cite(m.group(1)):
            if int(key) not in first_seen:
                first_seen.append(int(key))
    if first_seen != list(range(1, 53)):
        problems.append(f"{lang}: first-mention order is not 1..52: {first_seen}")
    return problems, stats


def abstract_texts(lang: str) -> list[str]:
    paras = [text_of(p) for p in docx.Document(OUTPUT[lang]).element.body.iter(w("p"))]
    found = [t for t in paras if t.startswith(("Abstract.", "Анотація."))]
    check(len(found) == 2, f"{lang}: expected two abstracts, found {len(found)}")
    return found


def verify_typography(lang: str) -> list[str]:
    problems = []
    texts = [(it.id, it.text) for it in output_items(lang)] + [("abstract", t) for t in abstract_texts(lang)]
    for item_id, text in texts:
        if typeset(text) != text:
            problems.append(f"{lang}: {item_id} has a spaced hyphen or a hyphenated numeric range")
        if space_formulas(text) != text:
            problems.append(f"{lang}: {item_id} runs text into a formula")
        for m in UK_SAMPLES_RE.finditer(text):
            want = uk_plural(int(m.group(1)), UK_SAMPLE_FORMS)
            if m.group(2) != want:
                problems.append(f"{lang}: {item_id} has {m.group(0)!r}, expected {want!r}")
    return problems


def figure_numbers(text: str) -> list[int]:
    return [int(n) for m in FIGURE_MENTION_RE.finditer(text) for n in re.findall(r"\d+", m.group(0))]


def verify_figures(lang: str) -> list[str]:
    """Figures are numbered by first mention, and each caption follows its first mention."""
    mention_at: dict[int, int] = {}
    caption_at: dict[int, int] = {}
    for i, it in enumerate(output_items(lang)):
        caption = CAPTION_RE.match(it.text)
        if caption:
            caption_at[int(caption.group(1))] = i
            continue
        for n in figure_numbers(it.text):
            mention_at.setdefault(n, i)
    problems = []
    first = sorted(mention_at, key=lambda n: mention_at[n])
    if first != list(range(1, 8)):
        problems.append(f"{lang}: figures first mentioned in order {first}, expected 1..7")
    if sorted(caption_at, key=lambda n: caption_at[n]) != list(range(1, 8)):
        problems.append(f"{lang}: captions in order {sorted(caption_at, key=lambda n: caption_at[n])}")
    for n in range(1, 8):
        if n in mention_at and n in caption_at and mention_at[n] > caption_at[n]:
            problems.append(f"{lang}: Fig. {n} is first mentioned after its caption")
    return problems


def numbers_of(text: str, lang: str) -> Counter[str]:
    """Digit-only numbers, with 8,683 / 8 683 -> 8683 and 90,05 -> 90.05 (UK decimal comma)."""
    text = URL_RE.sub(" ", CITE_RE.sub(" ", FORMULA_RE.sub(" ", text)))
    group = "[ ,  ]" if lang == "en" else "[   ]"
    text = re.sub(rf"(?<![\d.,])\d{{1,3}}(?:{group}\d{{3}})+(?![\d,])",
                  lambda m: re.sub(r"[^\d]", "", m.group(0)), text)
    if lang == "uk":
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    return Counter(re.findall(r"\d+(?:\.\d+)*", text))


def verify_parity() -> list[str]:
    """Each EN body item and its UK counterpart hold the same citations, formulas and numbers."""
    en, uk = output_items("en"), output_items("uk")
    if len(en) != len(uk):
        return [f"parity: {len(en)} EN items vs {len(uk)} UK items"]
    problems = []
    for i, (a, b) in enumerate(zip(en, uk)):
        for name, ca, cb in (("citations", Counter(CITE_RE.findall(a.text)), Counter(CITE_RE.findall(b.text))),
                             ("formulas", Counter(FORMULA_RE.findall(a.text)), Counter(FORMULA_RE.findall(b.text))),
                             ("numbers", numbers_of(a.text, "en"), numbers_of(b.text, "uk"))):
            if ca != cb:
                problems.append(f"parity: item {i} ({a.text[:40]!r}) {name} differ: "
                                f"EN-only {dict(ca - cb)}, UK-only {dict(cb - ca)}")
    return problems


def verify_pdf(lang: str, report: dict) -> list[str]:
    problems = []
    if report["body_pages"] < 8:
        problems.append(f"{lang}: body is {report['body_pages']:.2f} pages, need >= 8")
    if report["figure_table_pages"] > 3:
        problems.append(f"{lang}: figures + table take {report['figure_table_pages']:.2f} pages, limit 3")
    return problems


def main() -> int:
    shared: dict = {}
    results = {lang: build(lang, shared) for lang in ("en", "uk")}
    refs = load_json(REFERENCES)
    problems: list[str] = []
    for lang in ("en", "uk"):
        out = results[lang]
        pdf_stats = pdf_report(lang, convert_pdf(OUTPUT[lang]))
        p1, s1 = verify_structure(lang, refs)
        p2, s2 = verify_references(lang, shared["order"], refs)
        problems += verify_text(lang, shared["order"]) + p1 + p2 + verify_pdf(lang, pdf_stats)
        problems += verify_typography(lang) + verify_figures(lang)
        print(f"== {lang}: {OUTPUT[lang].name}")
        print("abstract characters (with spaces):", out["notes"])
        print("structure:", s1)
        print("references:", s2)
        print("pdf:", {k: round(v, 2) if isinstance(v, float) else v for k, v in pdf_stats.items()})
        for f in out["figures"]:
            print(f"  fig {f['n']}: {f['px'][0]}x{f['px'][1]} px -> {f['width_in']:.2f} x {f['height_in']:.2f} in, {f['dpi']:.0f} dpi")
    problems += verify_parity()
    print("PROBLEMS:" if problems else "ALL CHECKS PASSED")
    for p in problems:
        print(" -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as exc:
        print("BUILD ERROR:", exc)
        sys.exit(2)
