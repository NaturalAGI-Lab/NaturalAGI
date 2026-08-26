"""Derive the reference apparatus from the body text and rewrite it in place.

The ITSSI author guidelines (18.07.2026) require sources to be listed in
order of first mention, each cited at least once, with no duplicates. This
script is the single derivation of that order:

- SOURCES maps every source key to the literal author-year forms used in
  SECTIONS and to a substring that identifies its bibliography entry;
- GROUPS lists multi-source parentheticals, whose members are ordered by
  their position inside the parenthesis;
- the body is walked in build order (generate_paper.main renders SECTIONS
  after the English abstract; neither abstract nor the declarations carry
  citations), the first mention of every key fixes its number, and both
  content.REFERENCES and generate_paper.CITATION_MARKERS are rewritten.

Run after any edit that adds, removes or moves an in-text citation:

    .venv/bin/python papers/itssi_xai_2026/renumber_refs.py
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import content as C  # noqa: E402

# key -> (bibliography-matching substring, in-text literals)
SOURCES: dict[str, tuple[str, tuple[str, ...]]] = {
    "ribeiro": ("Ribeiro, M., Singh", ("(Ribeiro et al., 2016)",)),
    "lundberg": ("Lundberg, S., Lee", ("(Lundberg and Lee, 2017)",)),
    "slack": ("Slack, D., Hilgard", ("Slack et al. (2020)",)),
    "hooshyar": ("Hooshyar, D., Yang", ("Hooshyar and Yang (2024)",)),
    "rudin": ("Rudin, C. (2019)", ("Rudin (2019)",)),
    "rajabi": ("Rajabi, E., Etminani", ("(Rajabi and Etminani, 2024)",)),
    "han": ("Han, K., Wang", ("(Han et al., 2022)",)),
    "chatbri": ("Chatbri, H.", ("Chatbri et al. (2016)",)),
    "shen": ("Shen, W., Jiang", ("Shen et al. (2016)",)),
    "conte": ("Conte, D., Foggia", ("Conte et al. (2004)",)),
    "riesen": (
        "Riesen, K., Bunke",
        ("(Riesen and Bunke, 2009)", "Riesen and Bunke (2009)"),
    ),
    "wang": ("Wang, R., Zhang", ("Wang et al. (2021)",)),
    "snell": ("Snell, J., Swersky", ("(Snell et al., 2017)",)),
    "finn": ("Finn, C., Abbeel", ("(Finn et al., 2017)",)),
    "lake": ("Lake, B., Salakhutdinov", ("Lake et al. (2015)",)),
    "hinton": ("Hinton, G. (2022)", ("(Hinton, 2022)",)),
    "nawaz": ("Nawaz, U.", ("(Nawaz et al., 2025)",)),
    "parzhyn_energy": ("Parzhyn, Y., Lapin", ("(Parzhyn et al., 2025)",)),
    "parzhyn_vector": ("Parzhyn, Y., Galkyn", ("(Parzhyn et al., 2022)",)),
    "parzhyn_arch": ("Parzhyn, Y. (2025)", ("(Parzhyn, 2025)",)),
    "lapin": (
        "Few-shot learning of a graph-based",
        ("(Lapin and Bokhan, 2025)",),
    ),
    "zhang": ("Zhang, T., Suen", ("(Zhang and Suen, 1984)",)),
    "fritzke": ("Fritzke, B. (1995)", ("(Growing Neural Gas, GNG; Fritzke, 1995)",)),
    "douglas": ("Douglas, D., Peucker", ("(Douglas and Peucker, 1973)",)),
    "lecun": ("LeCun, Y., Bottou", ("(LeCun et al., 1998)",)),
    "baniecki": (
        "Baniecki, H., Biecek",
        ("Baniecki and Biecek (2024)", "(Baniecki and Biecek, 2024)"),
    ),
    "bello": ("Bello, M., Amador", ("Bello et al. (2025)", "(Bello et al., 2025)")),
    "forest": (
        "Forest, F., Rombach",
        ("Forest et al. (2025)", "(Forest et al., 2025)"),
    ),
    "sovatzidi": (
        "Sovatzidi, G.",
        ("Sovatzidi et al. (2026)", "(Sovatzidi et al., 2026)"),
    ),
    "garcia": (
        "García-Cuesta, E.",
        ("García-Cuesta et al. (2025)", "(García-Cuesta et al., 2025)"),
    ),
    "elsharkawi": (
        "Elsharkawi, I.",
        ("Elsharkawi et al. (2026)", "(Elsharkawi et al., 2026)"),
    ),
    "senior": ("Senior, H., Slabaugh", ("Senior et al. (2025)", "(Senior et al., 2025)")),
    "piao": ("Piao, C., Xu", ("Piao et al. (2023)", "(Piao et al., 2023)")),
    "tang": ("Tang, J., Zhao", ("Tang et al. (2025)", "(Tang et al., 2025)")),
    "moscatelli": (
        "Moscatelli, A.",
        ("Moscatelli et al. (2026)", "(Moscatelli et al., 2026)"),
    ),
    "gan": ("Gan, J., Chen", ("Gan et al. (2023)", "(Gan et al., 2023)")),
    "dong": ("Dong, Y., Wu", ("Dong et al. (2026)", "(Dong et al., 2026)")),
    "ji": ("Ji, Z., Wei", ("Ji et al. (2026)", "(Ji et al., 2026)")),
    "ghader": ("Ghader, M.", ("Ghader et al. (2026)", "(Ghader et al., 2026)")),
}

# Multi-source parentheticals: literal -> member keys, in printed order.
GROUPS: dict[str, tuple[str, ...]] = {
    "(Baniecki and Biecek, 2024; Bello et al., 2025)": ("baniecki", "bello"),
    "(Forest et al., 2025; Sovatzidi et al., 2026; García-Cuesta et al., 2025)": (
        "forest",
        "sovatzidi",
        "garcia",
    ),
    "(Elsharkawi et al., 2026; Senior et al., 2025; Gan et al., 2023; "
    "Dong et al., 2026)": ("elsharkawi", "senior", "gan", "dong"),
    "(Piao et al., 2023; Tang et al., 2025; Moscatelli et al., 2026)": (
        "piao",
        "tang",
        "moscatelli",
    ),
}

# Bibliography entries for sources not yet present in content.REFERENCES.
NEW_REFS: dict[str, str] = {
    "baniecki": (
        "Baniecki, H., Biecek, P. (2024), \"Adversarial attacks and "
        "defenses in explainable artificial intelligence: a survey\", "
        "*Information Fusion*, Vol. 107, 102303. DOI: "
        "https://doi.org/10.1016/j.inffus.2024.102303"
    ),
    "bello": (
        "Bello, M., Amador, R., García, M., Del Ser, J., Mesejo, P., "
        "Cordón, Ó. (2025), \"The level of strength of an explanation: a "
        "quantitative evaluation technique for post-hoc XAI methods\", "
        "*Pattern Recognition*, Vol. 161, 111221. DOI: "
        "https://doi.org/10.1016/j.patcog.2024.111221"
    ),
    "forest": (
        "Forest, F., Rombach, K., Fink, O. (2025), \"Interpretable "
        "prognostics with concept bottleneck models\", *Information "
        "Fusion*, Vol. 124, 103427. DOI: "
        "https://doi.org/10.1016/j.inffus.2025.103427"
    ),
    "sovatzidi": (
        "Sovatzidi, G., Vasilakakis, M., Iakovidis, D. (2026), "
        "\"Intuitionistic fuzzy cognitive maps for interpretable image "
        "classification\", *Knowledge-Based Systems*, Vol. 346, 116130. "
        "DOI: https://doi.org/10.1016/j.knosys.2026.116130"
    ),
    "garcia": (
        "García-Cuesta, E., Manrique, D., Ionescu, R. (2025), "
        "\"Interpretable deep prototype-based neural networks: can a 1 "
        "look like a 0?\", *Electronics*, Vol. 14, No. 18, 3584. DOI: "
        "https://doi.org/10.3390/electronics14183584"
    ),
    "elsharkawi": (
        "Elsharkawi, I., Sharara, H., Rafea, A. (2026), \"ViG-LRGC: "
        "vision graph neural networks with learnable reparameterized "
        "graph construction\", *Pattern Recognition Letters*, Vol. 207, "
        "pp. 36–41. DOI: https://doi.org/10.1016/j.patrec.2026.06.001"
    ),
    "senior": (
        "Senior, H., Slabaugh, G., Yuan, S., Rossi, L. (2025), \"Graph "
        "neural networks in vision-language image understanding: a "
        "survey\", *The Visual Computer*, Vol. 41, No. 1, pp. 491–516. "
        "DOI: https://doi.org/10.1007/s00371-024-03343-0"
    ),
    "piao": (
        "Piao, C., Xu, T., Sun, X., Rong, Y., Zhao, K., Cheng, H. (2023), "
        "\"Computing graph edit distance via neural graph matching\", "
        "*Proceedings of the VLDB Endowment*, Vol. 16, No. 8, "
        "pp. 1817–1829. DOI: https://doi.org/10.14778/3594512.3594514"
    ),
    "tang": (
        "Tang, J., Zhao, X., Kong, L., Zhou, X., Li, J. (2025), \"Fused "
        "Gromov-Wasserstein alignment for graph edit distance computation "
        "and beyond\", *Proceedings of the VLDB Endowment*, Vol. 18, "
        "No. 10, pp. 3641–3654. DOI: "
        "https://doi.org/10.14778/3748191.3748221"
    ),
    "moscatelli": (
        "Moscatelli, A., Bérar, M., Héroux, P., Yger, F., Adam, S. "
        "(2026), \"Edges: an expressive and efficient model for learning "
        "graph edit distance\", *Pattern Recognition*, Vol. 179, 113764. "
        "DOI: https://doi.org/10.1016/j.patcog.2026.113764"
    ),
    "gan": (
        "Gan, J., Chen, Y., Hu, B., Leng, J., Wang, W., Gao, X. (2023), "
        "\"Characters as graphs: interpretable handwritten Chinese "
        "character recognition via Pyramid Graph Transformer\", *Pattern "
        "Recognition*, Vol. 137, 109317. DOI: "
        "https://doi.org/10.1016/j.patcog.2023.109317"
    ),
    "dong": (
        "Dong, Y., Wu, B., Ma, J., Li, X. (2026), \"Graph-based radical "
        "structure tree representation for zero-shot Chinese character "
        "recognition\", *Pattern Recognition*, Vol. 177, 113314. DOI: "
        "https://doi.org/10.1016/j.patcog.2026.113314"
    ),
    "ji": (
        "Ji, Z., Wei, R., Liu, J., Pang, Y., Han, J. (2026), "
        "\"Interpretable few-shot image classification via prototypical "
        "concept-guided mixture of LoRA experts\", *IEEE Transactions on "
        "Image Processing*, Vol. 35, pp. 930–942. DOI: "
        "https://doi.org/10.1109/TIP.2026.3654473"
    ),
    "ghader": (
        "Ghader, M., Kheradpisheh, S., Farahani, B., Fazlali, M. (2026), "
        "\"Backpropagation-free spiking neural networks with the "
        "forward–forward algorithm\", *Scientific Reports*, Vol. 16, "
        "No. 1, 14294. DOI: https://doi.org/10.1038/s41598-026-41671-4"
    ),
}

# Narrative literals keep the author name and replace only the year paren.
_NARRATIVE_RE = re.compile(r"^(?P<name>.+?)\s\((?P<year>\d{4})\)$")


def body_paragraphs() -> list[str]:
    """SECTIONS paragraphs in the order generate_paper renders them."""
    out: list[str] = []
    for _, paragraphs in C.SECTIONS:
        for para in paragraphs:
            if para.startswith(("__TABLE__:", "__FIGURE__:", "__FORMULA__:")):
                continue
            out.append(para)
    return out


def first_mentions(paragraphs: list[str]) -> list[str]:
    positions: dict[str, tuple[int, int]] = {}

    def offer(key: str, para_index: int, char_pos: int) -> None:
        cur = positions.get(key)
        if cur is None or (para_index, char_pos) < cur:
            positions[key] = (para_index, char_pos)

    for i, para in enumerate(paragraphs):
        for key, (_, literals) in SOURCES.items():
            for literal in literals:
                pos = para.find(literal)
                if pos >= 0:
                    offer(key, i, pos)
        for group, members in GROUPS.items():
            start = para.find(group)
            if start < 0:
                continue
            for member in members:
                fragment = SOURCES[member][1][-1].strip("()")
                offer(member, i, start + group.index(fragment))

    missing = sorted(set(SOURCES) - set(positions))
    if missing:
        raise SystemExit(f"sources never cited in the body: {missing}")
    return sorted(positions, key=lambda k: positions[k])


def resolve_reference_texts() -> dict[str, str]:
    """Map each key to its bibliography entry, taken from content.REFERENCES
    where it already exists and from NEW_REFS otherwise."""
    texts: dict[str, str] = {}
    taken: list[bool] = [False] * len(C.REFERENCES)
    for key, (needle, _) in SOURCES.items():
        hits = [i for i, ref in enumerate(C.REFERENCES) if needle in ref]
        if len(hits) > 1:
            raise SystemExit(f"{key!r}: matching substring {needle!r} is not unique")
        if hits:
            texts[key] = C.REFERENCES[hits[0]]
            taken[hits[0]] = True
        elif key in NEW_REFS:
            texts[key] = NEW_REFS[key]
        else:
            raise SystemExit(f"{key!r}: no bibliography entry found")
    orphans = [C.REFERENCES[i] for i, used in enumerate(taken) if not used]
    if orphans:
        raise SystemExit(f"references matched to no source: {orphans}")
    return texts


def marker_for(literal: str, number: int) -> str:
    if literal.startswith("(Growing Neural Gas"):
        return f"(Growing Neural Gas, GNG) [{number}]"
    if literal.startswith("("):
        return f"[{number}]"
    m = _NARRATIVE_RE.match(literal)
    if not m:
        raise SystemExit(f"unrecognised citation literal: {literal!r}")
    return f"{m.group('name')} [{number}]"


def build_markers(order: list[str]) -> list[tuple[str, str]]:
    number = {key: i for i, key in enumerate(order, 1)}
    pairs: list[tuple[str, str]] = []
    for group, members in GROUPS.items():
        joined = ", ".join(str(number[m]) for m in members)
        pairs.append((group, f"[{joined}]"))
    for key, (_, literals) in SOURCES.items():
        for literal in literals:
            pairs.append((literal, marker_for(literal, number[key])))
    # Longest first so that no literal is shadowed by one it contains.
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def wrap_entry(text: str, indent: str) -> list[str]:
    width = 72 - len(indent)
    chunks = textwrap.wrap(
        text, width=width, break_long_words=False, break_on_hyphens=False
    )
    lines = []
    for i, chunk in enumerate(chunks):
        piece = chunk if i == len(chunks) - 1 else chunk + " "
        piece = piece.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{indent}"{piece}"')
    return lines


def render_references(order: list[str], texts: dict[str, str]) -> str:
    out = ["REFERENCES: list[str] = ["]
    for key in order:
        lines = wrap_entry(texts[key], "        ")
        if len(lines) == 1:
            out.append(f"    ({lines[0].strip()}),")
        else:
            out.append("    (")
            out.extend(lines)
            out.append("    ),")
    out.append("]")
    return "\n".join(out) + "\n"


def render_markers(pairs: list[tuple[str, str]]) -> str:
    out = ["CITATION_MARKERS: tuple[tuple[str, str], ...] = ("]
    for literal, marker in pairs:
        lit = literal.replace("\\", "\\\\").replace('"', '\\"')
        mark = marker.replace("\\", "\\\\").replace('"', '\\"')
        line = f'    ("{lit}", "{mark}"),'
        if len(line) <= 79:
            out.append(line)
        else:
            out.append("    (")
            out.append(f'        "{lit}",')
            out.append(f'        "{mark}",')
            out.append("    ),")
    out.append(")")
    return "\n".join(out) + "\n"


def splice(path: Path, first_line_prefix: str, closer: str, block: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.startswith(first_line_prefix))
    end = start
    while lines[end].rstrip() != closer:
        end += 1
    path.write_text(
        "".join(lines[:start] + [block] + lines[end + 1:]), encoding="utf-8"
    )


def main() -> None:
    paragraphs = body_paragraphs()
    order = first_mentions(paragraphs)
    texts = resolve_reference_texts()
    pairs = build_markers(order)

    splice(HERE / "content.py", "REFERENCES: list[str] = [", "]",
           render_references(order, texts))
    splice(HERE / "generate_paper.py", "CITATION_MARKERS", ")",
           render_markers(pairs))

    print(f"{len(order)} references, ordered by first mention:")
    for i, key in enumerate(order, 1):
        print(f"  [{i:2d}] {key}")


if __name__ == "__main__":
    main()
