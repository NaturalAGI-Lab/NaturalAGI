"""N-2L — the professor's two-level hypergraph scheme from his first letter, as a model (offline, cached skeletons).

  primitives        points of the simplified skeleton graph (end E, junction J, corner C, smooth S) and the segments
                    between them; frame = skeleton centre of mass, field of view 80 px
  parametric fibre  quantised parameters per element on the segmentation hierarchy (modal group)
  traversal         from a capture point chosen bottom-up (top-most end, else junction, else node), depth first,
                    continuations in order of signed turn; relation arcs = signed turn between consecutive segments
  reduction         maximal runs of a path where a relation parameter stays constant (`sign`: the turn keeps one sign,
                    `dir`: the segment direction stays in one sector) -> hyperedge; run ends -> anchor candidates
  alignment         ONLY by anchor candidates: optimal assignment (Hungarian) on type, position and traversal rank
  learning          per subclass: every example aligned to the seed (first original); counters f(e) for anchors,
                    hyperedges and parametric vertices (accumulating hypergraph); attractor = f >= tau
  inference         the example aligned to every attractor by anchors; reaction = matched attractor weight, two-sided
                    normalisation (or one-sided coverage, or a (structural, parametric) vector with a Pareto rule);
                    WTA = argmax; several detector channels -> MAX per neuron
Usage: isl_2l.py eval [--variant V1] [--split dev] [--dump]   |   isl_2l.py order [--variant V]   |   isl_2l.py all
Pre-registration and results: experiments/isl_transfer_2026-10/lab_N_2L.md
"""
import argparse
import csv
import json
import math
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "tests" / "_isl" / "skel"
OUT_DIR = REPO / "experiments" / "isl_transfer_2026-10"
DUMP_DIR = REPO / "tests" / "_isl"
GROUPS = REPO / "tests" / "_isl" / "base76_subclasses.json"
MANIFEST = REPO / "datasets" / "mnist_all_manifest.csv"
COMAN = REPO / "tests" / "_isl" / "coman_mnist_all.jsonl"

CORNER_ANGLE = 160.0          # production rule: degree-2 node with interior angle < 160° is a corner
TURN = 180.0 - CORNER_ANGLE   # a turn larger than this is a left / right turn, else straight (0)
FOV = 80.0
NM = 1.0                      # non-match cost of an anchor
POS_TOL = 0.25                # position difference (unit frame) that costs one non-match
CURV_EDGES = {2: [60.0], 4: [30.0, 90.0, 180.0]}
LV = {"pos": (2, 4), "dir": (4, 8), "ori": (4, 8), "len": (2, 4), "turn": (2, 4), "deg": (2,)}


# ----------------------------------------------------------------------------------------------- data
def load(split, channel):
    """-> [dict(cls, stem, family, aug, data)] from the skeleton cache (aug 0 = the original)."""
    items = []
    for cdir in sorted(p for p in (CACHE / channel / split).iterdir() if p.is_dir()):
        for f in sorted(cdir.glob("*.json")):
            m = re.match(r"^(.*)_a(\d+)$", f.stem)
            family, aug = (m.group(1), int(m.group(2))) if m else (f.stem, 0)
            items.append({"cls": cdir.name, "stem": f.stem, "family": family, "aug": aug,
                          "data": json.loads(f.read_text())})
    return items


# ----------------------------------------------------------------------------------------------- quantisation
def seg(name, value, level):
    if name == "pos":
        return int(min(value[1], 0.999) * level) * level + int(min(value[0], 0.999) * level)
    if name == "dir":
        return int(((value + 180.0 / level) % 360.0) / (360.0 / level))
    if name == "ori":
        return int(((value + 90.0 / level) % 180.0) / (180.0 / level))
    if name == "len":
        return min(int(value / 1.2 * level), level - 1)
    if name == "turn":
        return sum(value >= e for e in CURV_EDGES[level])
    if name == "deg":
        return int(value >= 4)
    raise KeyError(name)


def pweight(name, level):
    """Weight of a parametric vertex = 1 + information of its tuning (log2 of the number of segments)."""
    return 1.0 + math.log2(level * level if name == "pos" else level)


def _angle(v):
    return math.degrees(math.atan2(v[1], v[0])) % 360.0


def signed_turn(v1, v2):
    return math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))


def turn_class(t):
    return "L" if t > TURN else ("R" if t < -TURN else "0")


# ----------------------------------------------------------------------------------------------- two-level hypergraph
def build(data, reduction="sign"):
    """Skeleton graph -> two-level hypergraph: anchors [dict(type, pos, rank, params)] and hyperedges
    [dict(a, b, kind, cls, params)] (a, b = anchor indices). None when the detector produced no graph."""
    if not data or "error" in data or not data.get("nodes") or not data.get("edges"):
        return None
    xy = np.array(data["nodes"], float)
    adj = defaultdict(set)
    for u, v in data["edges"]:
        if u != v:
            adj[u].add(v), adj[v].add(u)
    if not adj:
        return None
    skel = np.array(data["skel"], float) if data.get("skel") else xy
    unit = np.clip((xy - skel.mean(0)) / FOV + 0.5, 0.0, 0.999)

    def kind(i):
        d = len(adj[i])
        if d == 1:
            return "E"
        if d >= 3:
            return "J"
        a, b = list(adj[i])
        u1, u2 = xy[a] - xy[i], xy[b] - xy[i]
        cos = float(u1 @ u2 / max(np.linalg.norm(u1) * np.linalg.norm(u2), 1e-9))
        return "C" if math.degrees(math.acos(max(-1.0, min(1.0, cos)))) < CORNER_ANGLE else "S"
    kinds = {i: kind(i) for i in adj}
    seen = set()

    def visited(u, v):
        return (min(u, v), max(u, v)) in seen

    def mark(u, v):
        seen.add((min(u, v), max(u, v)))

    def capture(nodes):
        for t in ("E", "J"):
            c = [i for i in nodes if kinds[i] == t]
            if c:
                return min(c, key=lambda i: (xy[i][1], xy[i][0]))
        return min(nodes, key=lambda i: (xy[i][1], xy[i][0]))

    paths, order = [], []

    def walk(start, nxt):
        path = [start, nxt]
        mark(start, nxt)
        cur = nxt
        while kinds[cur] in ("S", "C"):
            cand = [x for x in adj[cur] if not visited(cur, x)]
            if not cand:
                break
            mark(cur, cand[0])
            path.append(cand[0])
            cur = cand[0]
        return path

    def explore(node, d_in):
        if node not in order:
            order.append(node)
        conts = sorted((m for m in adj[node] if not visited(node, m)),
                       key=lambda m: -signed_turn(d_in, xy[m] - xy[node]))
        for m in conts:
            if visited(node, m):
                continue
            p = walk(node, m)
            paths.append(p)
            for q in p:
                if q not in order:
                    order.append(q)
            explore(p[-1], xy[p[-1]] - xy[p[-2]])

    caps = []
    while True:
        left = {u for u in adj for v in adj[u] if not visited(u, v)}
        if not left:
            break
        comp, stack = set(), [next(iter(left))]          # the component holding unvisited edges
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            stack.extend(adj[u])
        start = capture(sorted(comp & left))
        caps.append(start)
        explore(start, np.array([0.0, 1.0]))            # enter from the top
    rank = {n: i for i, n in enumerate(order)}

    runs = []                                            # (node list, kind, cls)
    for p in paths:
        segs = [xy[p[i + 1]] - xy[p[i]] for i in range(len(p) - 1)]
        if reduction in ("sign", "both"):
            start, sign = 0, None
            for i in range(1, len(segs)):
                c = turn_class(signed_turn(segs[i - 1], segs[i]))
                if c == "0" or sign is None or c == sign:
                    sign = c if c != "0" else sign
                    continue
                runs.append((p[start:i + 1], "sign", sign))
                start, sign = i, c
            runs.append((p[start:], "sign", sign or "0"))
        if reduction in ("dir", "both"):
            start = 0
            for i in range(1, len(segs)):
                if seg("dir", _angle(segs[i]), 8) != seg("dir", _angle(segs[i - 1]), 8):
                    runs.append((p[start:i + 1], "dir", seg("dir", _angle(segs[start]), 8)))
                    start = i
            runs.append((p[start:], "dir", seg("dir", _angle(segs[start]), 8)))

    anchor_nodes = sorted({r[0][0] for r in runs} | {r[0][-1] for r in runs} | set(caps), key=lambda n: rank[n])
    idx = {n: i for i, n in enumerate(anchor_nodes)}
    na = max(len(anchor_nodes) - 1, 1)
    anchors = []
    for i, n in enumerate(anchor_nodes):
        t = kinds[n] if kinds[n] in ("E", "J") else "B"
        par = {("pos", L): seg("pos", unit[n], L) for L in LV["pos"]}
        if t == "E":
            d = _angle(xy[n] - xy[next(iter(adj[n]))])
            par.update({("dir", L): seg("dir", d, L) for L in LV["dir"]})
        elif t == "J":
            par[("deg", 2)] = seg("deg", len(adj[n]), 2)
        anchors.append({"type": t, "pos": unit[n].copy(), "rank": i / na, "params": par})
    hyper = []
    for nodes, kind_, cls in runs:
        pts = unit[nodes]
        length = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
        sv = [xy[nodes[i + 1]] - xy[nodes[i]] for i in range(len(nodes) - 1)]
        turning = sum(abs(signed_turn(sv[i - 1], sv[i])) for i in range(1, len(sv)))
        chord = pts[-1] - pts[0]
        par = {("ori", L): seg("ori", _angle(chord) % 180.0, L) for L in LV["ori"]}
        par.update({("len", L): seg("len", length, L) for L in LV["len"]})
        par.update({("turn", L): seg("turn", turning, L) for L in LV["turn"]})
        par.update({("pos", L): seg("pos", pts.mean(0), L) for L in LV["pos"]})
        hyper.append({"a": idx[nodes[0]], "b": idx[nodes[-1]], "kind": kind_, "cls": cls, "params": par})
    return {"anchors": anchors, "hyper": hyper}


def weight_of(hg):
    """(structural, parametric) weight of a hypergraph's own elements."""
    s = len(hg["anchors"]) + len(hg["hyper"])
    p = sum(pweight(n, L) for el in hg["anchors"] + hg["hyper"] for (n, L) in el["params"])
    return s, p


# ----------------------------------------------------------------------------------------------- alignment
def align(A, B, use_rank=True, tol=POS_TOL):
    """Optimal assignment of anchors of A to anchors of B (same type only, non-match cost NM). -> {i: j}"""
    a, b = A["anchors"], B["anchors"]
    if not a or not b:
        return {}
    pa = np.array([x["pos"] for x in a])
    pb = np.array([x["pos"] for x in b])
    cost = np.linalg.norm(pa[:, None, :] - pb[None, :, :], axis=2) / tol
    if use_rank:
        cost = cost + np.abs(np.array([x["rank"] for x in a])[:, None] - np.array([x["rank"] for x in b])[None, :])
    ta = np.array([x["type"] for x in a])
    tb = np.array([x["type"] for x in b])
    cost = np.where(ta[:, None] == tb[None, :], cost, NM)
    cost = np.minimum(cost, NM)
    rows, cols = linear_sum_assignment(cost)
    return {int(i): int(j) for i, j in zip(rows, cols) if cost[i, j] < NM}


def correspond(A, B, m):
    """Matched elements of A given the anchor map m (A -> B): yields keys of A's matched elements."""
    out = set()
    for i, j in m.items():
        out.add(("A", i))
        pa, pb = A["anchors"][i]["params"], B["anchors"][j]["params"]
        out.update(("A", i) + k for k, v in pa.items() if pb.get(k) == v)
    hb = defaultdict(list)
    for h in B["hyper"]:
        hb[frozenset((h["a"], h["b"]))].append(h)
    for k, h in enumerate(A["hyper"]):
        if h["a"] not in m or h["b"] not in m:
            continue
        cands = [g for g in hb.get(frozenset((m[h["a"]], m[h["b"]])), []) if g["kind"] == h["kind"] and g["cls"] == h["cls"]]
        if not cands:
            continue
        best = max(cands, key=lambda g: sum(g["params"].get(q) == v for q, v in h["params"].items()))
        out.add(("H", k))
        out.update(("H", k) + q for q, v in h["params"].items() if best["params"].get(q) == v)
    return out


# ----------------------------------------------------------------------------------------------- learning
def elements(hg):
    """All element keys of a hypergraph with their weight: structural ('A', i) / ('H', k), parametric (+ (name, L))."""
    w = {}
    for i, a in enumerate(hg["anchors"]):
        w[("A", i)] = 1.0
        w.update({("A", i) + k: pweight(*k) for k in a["params"]})
    for k, h in enumerate(hg["hyper"]):
        w[("H", k)] = 1.0
        w.update({("H", k) + q: pweight(*q) for q in h["params"]})
    return w


def learn(examples, tau, use_rank=True, tol=POS_TOL, originals=None):
    """Accumulating hypergraph on the seed (examples[0]); counters f(e) over all examples; attractor = f >= tau,
    glued by its anchors. -> attractor hypergraph (anchor positions / ranks = mean over the matched examples).
    originals (post-hoc §12 variant): flags per example; structural elements are counted over the originals only,
    parametric vertices over every example (augmentation explores the parameters, the structure comes from originals)."""
    seed = examples[0]
    counts = Counter(elements(seed).keys())
    pos_sum = {i: a["pos"].copy() for i, a in enumerate(seed["anchors"])}
    rank_sum = {i: a["rank"] for i, a in enumerate(seed["anchors"])}
    hits = Counter({i: 1 for i in range(len(seed["anchors"]))})
    struct_counts = Counter(k for k in counts if len(k) == 2)
    for k, ex in enumerate(examples[1:], 1):
        m = align(seed, ex, use_rank, tol)
        hit = correspond(seed, ex, m)
        counts.update(hit)
        if originals is not None and originals[k]:
            struct_counts.update(e for e in hit if len(e) == 2)
        for i, j in m.items():
            pos_sum[i] = pos_sum[i] + ex["anchors"][j]["pos"]
            rank_sum[i] += ex["anchors"][j]["rank"]
            hits[i] += 1
    n = len(examples)
    keep = {k for k, c in counts.items() if c / n >= tau - 1e-9}
    if originals is not None:
        n_orig = sum(originals)
        keep = {k for k in keep if len(k) > 2} | {k for k, c in struct_counts.items() if c / n_orig >= tau - 1e-9}
    kept_a = [i for i in range(len(seed["anchors"])) if ("A", i) in keep]
    new = {i: r for r, i in enumerate(kept_a)}
    anchors = []
    for i in kept_a:
        a = seed["anchors"][i]
        anchors.append({"type": a["type"], "pos": pos_sum[i] / hits[i], "rank": rank_sum[i] / hits[i],
                        "params": {k: v for k, v in a["params"].items() if ("A", i) + k in keep}})
    hyper = []
    for k, h in enumerate(seed["hyper"]):
        if ("H", k) in keep and h["a"] in new and h["b"] in new:
            hyper.append({"a": new[h["a"]], "b": new[h["b"]], "kind": h["kind"], "cls": h["cls"],
                          "params": {q: v for q, v in h["params"].items() if ("H", k) + q in keep}})
    return {"anchors": anchors, "hyper": hyper}


def signature(att):
    return (tuple(sorted(a["type"] for a in att["anchors"])),
            tuple(sorted((h["kind"], str(h["cls"]), *sorted((att["anchors"][h["a"]]["type"], att["anchors"][h["b"]]["type"])))
                         for h in att["hyper"])))


# ----------------------------------------------------------------------------------------------- reaction
def reaction(att, att_w, test, test_w, use_rank=True, tol=POS_TOL):
    """-> (matched structural weight, matched parametric weight) normalised: two-sided pair, one-sided pair."""
    if test is None or not att["anchors"]:
        return (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)
    m = align(att, test, use_rank, tol)
    hit = correspond(att, test, m)
    ms = sum(1.0 for k in hit if len(k) == 2)
    mp = sum(pweight(*k[2:]) for k in hit if len(k) > 2)
    (as_, ap), (ts, tp) = att_w, test_w
    two = ((ms + mp) / math.sqrt(max((as_ + ap) * (ts + tp), 1e-9)), 0.0)
    one = ((ms + mp) / max(as_ + ap, 1e-9), 0.0)
    vec = (ms / math.sqrt(max(as_ * ts, 1e-9)), mp / math.sqrt(max(ap * tp, 1e-9)) if ap and tp else 0.0)
    return two, one, vec


# ----------------------------------------------------------------------------------------------- variants
BASE = {"channels": ("t110",), "reduction": "sign", "tau": 1.0, "readout": "two", "rank": True}
VARIANTS = {
    "V1": {},
    "V2": {"reduction": "dir"},
    "V3": {"reduction": "both"},
    "V4": {"tau": 0.8},
    "V5": {"readout": "one"},
    "V6": {"readout": "vec"},
    "V8": {"rank": False},
    # stage B (pre-declared rule: the best choice of each group on dev) and C (= B + three filters, MAX)
    "B": {"reduction": "both", "tau": 0.8, "readout": "one", "rank": False},
    "C": {"reduction": "both", "tau": 0.8, "readout": "one", "rank": False, "channels": ("t110r", "t150r", "t190r")},
    # POST-HOC diagnostics (added after seeing A-C; dev only, never selected for the test)
    "P1": {"reduction": "both", "tau": 0.8, "readout": "two", "rank": False},
    "P2": {"reduction": "both", "tau": 0.8, "readout": "two", "rank": False, "tol": 0.5},
    "P3": {"reduction": "both", "tau": 0.8, "readout": "two", "rank": False, "tol": 0.5, "orig_struct": True},
    "P4": {"reduction": "both", "tau": 1.0, "readout": "two", "rank": False, "tol": 0.5, "orig_struct": True},
}


def cfg_of(name):
    if name in VARIANTS:
        return {**BASE, **VARIANTS[name]}
    return {**BASE, **json.loads(name)}


def train_neurons(cfg, order_seed=None):
    """One attractor per hand subclass and per detector channel. -> {subclass: [(attractor, weight) per channel]}"""
    groups = json.loads(GROUPS.read_text())
    neurons = defaultdict(list)
    for ch in cfg["channels"]:
        items = load("base76", ch)
        by_sub = defaultdict(list)
        for it in items:
            by_sub[groups[it["family"]]].append(it)
        for sub in sorted(by_sub):
            its = sorted(by_sub[sub], key=lambda it: (it["aug"] != 0, it["family"], it["aug"]))
            if order_seed is not None:                   # shuffled order; the seed = first original of that order
                rng = random.Random(order_seed)
                rng.shuffle(its)
                first = next(k for k, it in enumerate(its) if it["aug"] == 0)
                its.insert(0, its.pop(first))
            built = [(build(it["data"], cfg["reduction"]), it["aug"] == 0) for it in its]
            hgs = [h for h, _ in built if h is not None]
            orig = [o for h, o in built if h is not None] if cfg.get("orig_struct") else None
            att = learn(hgs, cfg["tau"], cfg["rank"], cfg.get("tol", POS_TOL), orig)
            neurons[sub].append((att, weight_of(att)))
    return neurons


def decide(scores, readout):
    """scores {sub: (r1, r2)} -> ranked subclasses. WTA = argmax; vector: Pareto rule, survivors by the sum."""
    if readout != "vec":
        return sorted(scores, key=lambda s: -scores[s][0])
    subs = list(scores)
    alive = [s for s in subs if not any(scores[t][0] >= scores[s][0] and scores[t][1] >= scores[s][1]
                                        and scores[t] != scores[s] for t in subs)]
    rest = [s for s in subs if s not in alive]
    key = lambda s: -(scores[s][0] + scores[s][1])
    return sorted(alive, key=key) + sorted(rest, key=key)


def evaluate(cfg, split, neurons, dump=None):
    tests = {ch: load(split, ch) for ch in cfg["channels"]}
    first = tests[cfg["channels"][0]]
    rows = []
    for k, it in enumerate(first):
        thg = []
        for ch in cfg["channels"]:
            h = build(tests[ch][k]["data"], cfg["reduction"])
            thg.append((h, weight_of(h) if h else (0, 0)))
        scores = {}
        for sub, per_ch in neurons.items():
            best = (0.0, 0.0)
            for (att, aw), (h, tw) in zip(per_ch, thg):
                two, one, vec = reaction(att, aw, h, tw, cfg["rank"], cfg.get("tol", POS_TOL))
                r = {"two": two, "one": one, "vec": vec}[cfg["readout"]]
                best = r if (r[0] + r[1]) > (best[0] + best[1]) else best         # MAX over channels
            scores[sub] = best
        ranked = decide(scores, cfg["readout"])
        classes = list(dict.fromkeys(s.split("_")[0] for s in ranked if sum(scores[s]) > 0))
        rows.append({"stem": it["stem"], "true": it["cls"], "pred": classes[0] if classes else "none", "top3": classes[:3],
                     "winner": ranked[0] if ranked and sum(scores[ranked[0]]) > 0 else None})
    if dump:
        with open(dump, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    return rows


def acc(rows):
    n = max(len(rows), 1)
    return 100.0 * sum(r["pred"] == r["true"] for r in rows) / n, 100.0 * sum(r["true"] in r["top3"] for r in rows) / n


def mcnemar(a, b):
    b01 = sum(1 for x, y in zip(a, b) if x and not y)
    b10 = sum(1 for x, y in zip(a, b) if y and not x)
    m = b01 + b10
    if m == 0:
        return 1.0, b01, b10
    k = min(b01, b10)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m), b01, b10


def write_row(row):
    out = OUT_DIR / "results_N_2L.csv"
    first = not out.exists()
    with out.open("a", newline="") as fh:
        wr = csv.writer(fh)
        if first:
            wr.writerow(list(row))
        wr.writerow(list(row.values()))


def run_variant(name, split="dev", dump=False):
    cfg = cfg_of(name)
    t0 = time.time()
    neurons = train_neurons(cfg)
    sizes = [len(a["anchors"]) for per in neurons.values() for a, _ in per]
    hsz = [len(a["hyper"]) for per in neurons.values() for a, _ in per]
    path = DUMP_DIR / f"n2l_{name if name in VARIANTS else 'custom'}_{split}.jsonl" if dump else None
    rows = evaluate(cfg, split, neurons, path)
    t1, t3 = acc(rows)
    row = {"variant": name, "split": split, "channels": "+".join(cfg["channels"]), "reduction": cfg["reduction"],
           "tau": cfg["tau"], "readout": cfg["readout"], "rank": cfg["rank"], "top1": round(t1, 2), "top3": round(t3, 2),
           "anchors_median": float(np.median(sizes)), "hyper_median": float(np.median(hsz)),
           "none": sum(r["pred"] == "none" for r in rows), "secs": round(time.time() - t0, 1)}
    write_row(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
    return rows


def test_report(rows):
    """all / complete / incomplete, top-3, McNemar vs ComAN as is (his 21.10 run)."""
    struct = {r["image_path"].split("/")[-1][:-4]: r["structure"] for r in csv.DictReader(open(MANIFEST))}
    coman = {}
    for line in open(COMAN):
        r = json.loads(line)
        coman[Path(r["path"]).stem] = r["pred"] == r["true"]
    out = {}
    for part in ("all", "complete", "incomplete"):
        sel = [r for r in rows if part == "all" or struct.get(r["stem"]) == part]
        t1, t3 = acc(sel)
        a = [coman.get(r["stem"], False) for r in sel]
        b = [r["pred"] == r["true"] for r in sel]
        p, only_c, only_n = mcnemar(a, b)
        d = [int(y) - int(x) for x, y in zip(a, b)]
        mean = sum(d) / len(d)
        sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (len(d) - 1))
        out[part] = {"n": len(sel), "top1": round(t1, 2), "top3": round(t3, 2), "coman": round(100 * sum(a) / len(a), 2),
                     "delta": round(100 * mean, 2), "ci": (round(100 * (mean - 1.96 * sd / math.sqrt(len(d))), 2),
                                                           round(100 * (mean + 1.96 * sd / math.sqrt(len(d))), 2)),
                     "p": float(f"{p:.3g}"), "coman_only": only_c, "new_only": only_n}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["eval", "order", "test"])
    ap.add_argument("--variant", default="V1")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--dump", action="store_true")
    a = ap.parse_args()
    if a.cmd == "eval":
        run_variant(a.variant, a.split, a.dump)
    elif a.cmd == "order":
        cfg = cfg_of(a.variant)
        sigs = [train_neurons(cfg, seed) for seed in (None, 1, 2)]
        same = sum(all(signature(s[sub][0][0]) == signature(sigs[0][sub][0][0]) for s in sigs[1:]) for sub in sigs[0])
        print(f"order: attractor signature identical in all 3 orders for {same}/{len(sigs[0])} subclasses")
    else:
        rows = run_variant(a.variant, "mtest", dump=True)
        print(json.dumps(test_report(rows), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
