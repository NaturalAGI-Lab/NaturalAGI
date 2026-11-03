"""Track B — matching-free ISL (manuscript Section IV: structural projection onto a redundant material hypergraph).

No hypergraph matching, no global analysis of the training pool, no negatives, no test-tuned knobs.

Detector layer D (exogenous, §2.1; cache from isl_cache.py): skeleton graph -> critical points (end E, corner C,
junction J; Def. 3: types decided by the local neighbourhood only) and strokes between them (relations).
Frame: centred on the stroke's centre of mass (saccades land near the centre of gravity), fixed scale (the dataset
already normalises size); control: bbox stretch.

H0 (redundant material hypergraph, §IV.1–2): every possible synapse
  point synapse     = (type, position segment, parameter segments)       E: outgoing direction; C: opening direction,
                                                                          turn; J: degree
  relation synapse  = hyperedge (type_u, type_v, stroke position, orientation, length, bulge)   (closure of a stroke)
at EVERY level of the segmentation hierarchy (eq. 42: coarse ... fine), plus "at least k" multiplicity. A stimulus
activates synapses by topography (projection Π) — there is no correspondence search.

Learning of one detector neuron (positive examples only, Axiom 3; label = top-down ψ that only opens plasticity,
Hypothesis 4): presence of synapse e in original o = majority over o's augmentation family (§12: augmentation explores
parameters); f(e) = mean presence over the neuron's originals (eq. 25); attractor = {e : f(e) >= tau} (Mode-1 pruning).
Map (Theorem 3): in class c's map only the winner learns (its bAP); a new neuron is recruited when the winner's response
is below rho x its response to its own seed family.
Soma readout (pre-registered): a = weighted coverage of the attractor; b = branch nonlinearity; c = divisive
normalisation by the stimulus' total drive (feedforward inhibition); d = c x intrinsic gain from the neuron's own
positives. WTA = argmax (fixed point of uniform lateral inhibition, Maass 2000); cfg `competition` = 'distinct' |
'pareto' replaces it by a local rule over the neurons' reaction vectors (his point 3; see compete()).

Usage: isl_sim.py grid [--train cand60:10] [--dev dev] [--out results_B.csv]
"""
import argparse
import csv
import itertools
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "tests" / "_isl" / "skel"
OUT_DIR = REPO / "experiments" / "isl_transfer_2026-10"

CORNER_ANGLE = 160.0      # production rule: a degree-2 node is a corner when its angle is < 160° (structural analyzer)
FOV = 80.0                # px: field of view around the centre of mass (digits occupy ~71 px of 100)
STRAIGHT = 0.15           # |bulge| below this = straight stroke
LEVELS = {                # segmentation hierarchy per parameter (number of segments per level, coarse -> fine)
    "pos": [1, 2, 4],     # square grid side
    "dir": [1, 2, 4, 8],  # signed direction, 360°
    "ori": [1, 2, 4, 8],  # orientation, 180°
    "turn": [1, 2],
    "deg": [1, 2],
    "len": [1, 2, 4],
    "bulge": [1, 3],
    "size": [1, 2, 4],
    "curv": [1, 2, 4],    # total turning along a stroke: <60 | >=60 ; <30 | 30-90 | 90-180 | >=180 degrees
    "bend": [1, 2, 4],    # bend at a joint along a stroke: <25 | >=25 ; <15 | 15-45 | 45-90 | >=90 degrees
    "side": [1, 3],       # straight | bends toward the centre of mass | away from it
    "tort": [1, 2, 4],    # P3b stroke tortuosity = path length / chord: <1.1 | >=1.1 ; <1.05 | 1.05-1.2 | 1.2-1.5 | >=1.5
    "nlen": [1, 2, 4],    # P3b stroke length / the image's longest stroke, equal bins
    "ang": [1, 2, 4],     # P3b angle between consecutive junction branches: <90 | >=90 ; <45 | 45-90 | 90-135 | >=135
}
JA_LEVELS = {"pos": [1, 2], "ang": [1, 2, 4]}   # P3b junction-angle synapses: coarse position only
FOVEA = {"pos": [8], "dir": [16]}   # finer segmentation at the anchors only (attention operator F, §13)


# ----------------------------------------------------------------------------------------------- detector layer
_LOADED = {}


def load(split, channels=("t110",), limit=None):
    """-> list of dict(cls, stem, family, aug, data=[one cached skeleton per detector channel]); aug 0 = the original.
    Several channels = several binarisation filters of the same image (his point 2: alternative filters)."""
    key = (split, tuple(channels), limit)
    if key in _LOADED:
        return _LOADED[key]
    root = CACHE / channels[0] / split
    items = []
    for cdir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(cdir.glob("*.json"))
        for f in files:
            stem = f.stem
            m = re.match(r"^(.*)_a(\d+)$", stem)
            family, aug = (m.group(1), int(m.group(2))) if m else (stem, 0)
            items.append({"cls": cdir.name, "stem": stem, "family": family, "aug": aug, "path": f})
    if limit:
        keep = {}
        for it in items:
            if it["aug"] == 0:
                keep.setdefault(it["cls"], [])
                if len(keep[it["cls"]]) < limit:
                    keep[it["cls"]].append(it["family"])
        allowed = {f for v in keep.values() for f in v}
        items = [it for it in items if it["family"] in allowed]
    for it in items:
        rel = it["path"].relative_to(CACHE / channels[0])
        it["data"] = []
        for ch in channels:
            f = CACHE / ch / rel
            it["data"].append(json.loads(f.read_text()) if f.exists() else {"error": "missing"})
    _LOADED[key] = items
    return items


def _angle_deg(v):
    return math.degrees(math.atan2(v[1], v[0])) % 360.0


def extract(data, frame="centroid"):
    """Critical points and strokes of one skeleton graph in a normalised frame. -> (points, relations)"""
    if "error" in data or not data.get("nodes"):
        return [], []
    xy = np.array(data["nodes"], float)
    n = len(xy)
    adj = defaultdict(set)
    for u, v in data["edges"]:
        if u != v:
            adj[u].add(v), adj[v].add(u)
    skel = np.array(data["skel"], float) if data.get("skel") else xy
    if frame == "centroid":
        c = skel.mean(0)
        unit = (xy - c) / FOV + 0.5
        centre = np.array([0.5, 0.5])
    else:                                   # control: bbox stretched to the unit square
        lo, hi = xy.min(0), xy.max(0)
        unit = (xy - lo) / np.maximum(hi - lo, 1e-6)
        centre = unit.mean(0)
    unit = np.clip(unit, 0.0, 0.999)

    def interior(i):
        a, b = list(adj[i])
        u1, u2 = xy[a] - xy[i], xy[b] - xy[i]
        cos = float(u1 @ u2 / max(np.linalg.norm(u1) * np.linalg.norm(u2), 1e-9))
        return math.degrees(math.acos(max(-1.0, min(1.0, cos))))

    kind = {}
    for i in range(n):
        d = len(adj[i])
        if d == 1:
            kind[i] = "E"
        elif d >= 3:
            kind[i] = "J"
        elif d == 2 and interior(i) < CORNER_ANGLE:
            kind[i] = "C"
    points = []
    for i, k in kind.items():
        p = {"type": k, "pos": unit[i]}
        if k == "E":
            nb = next(iter(adj[i]))
            p["dir"] = _angle_deg(xy[i] - xy[nb])
        elif k == "C":
            a, b = list(adj[i])
            u1 = (xy[a] - xy[i]) / max(np.linalg.norm(xy[a] - xy[i]), 1e-9)
            u2 = (xy[b] - xy[i]) / max(np.linalg.norm(xy[b] - xy[i]), 1e-9)
            p["dir"] = _angle_deg(u1 + u2)          # opening (bisector) direction
            p["turn"] = 180.0 - interior(i)
        else:
            p["deg"] = len(adj[i])
            p["branches"] = [_angle_deg(xy[nb] - xy[i]) for nb in adj[i]]
        points.append(p)

    # strokes = paths between critical points through smooth nodes (closure of the base spatial graph)
    seen, relations = set(), []
    for s in kind:
        for nb in adj[s]:
            path, prev, cur = [s], s, nb
            while cur not in kind:
                path.append(cur)
                nxt = [x for x in adj[cur] if x != prev]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                if cur == s and len(path) > 2:
                    break
            path.append(cur)
            key = frozenset(zip(path[:-1], path[1:])) | frozenset(zip(path[1:], path[:-1]))
            if key in seen:
                continue
            seen.add(key)
            relations.append(_stroke(path, kind, unit, xy, centre))
    # loops without critical points (e.g. a clean "0")
    covered = {e for k in seen for e in k}
    for u in range(n):
        for v in adj[u]:
            if (u, v) in covered or u in kind:
                continue
            loop, prev, cur = [u], None, u
            while True:
                nxt = [x for x in adj[cur] if x != prev and (cur, x) not in covered]
                if not nxt:
                    break
                covered.add((cur, nxt[0])), covered.add((nxt[0], cur))
                prev, cur = cur, nxt[0]
                if cur == u:
                    break
                loop.append(cur)
            if len(loop) >= 3:
                pts = unit[loop]
                ev = np.linalg.eigh(np.cov((pts - pts.mean(0)).T))[1][:, -1]
                relations.append({"type": "OO", "pos": pts.mean(0), "ori": _angle_deg(ev) % 180.0,
                                  "size": float(np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1).sum())})
    return points, relations


def _stroke(path, kind, unit, xy, centre):
    a, b = path[0], path[-1]
    ta, tb = kind.get(a, "S"), kind.get(b, "S")
    if (ta, _angle_deg(unit[b] - unit[a])) > (tb, _angle_deg(unit[a] - unit[b])):   # canonical end order
        a, b, ta, tb = b, a, tb, ta
        path = path[::-1]
    pts = unit[path]
    chord = pts[-1] - pts[0]
    clen = float(np.linalg.norm(chord))
    length = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    bulge, side = 0.0, 0
    if clen > 1e-6 and len(pts) > 2:
        normal = np.array([-chord[1], chord[0]]) / clen
        dev = (pts - pts[0]) @ normal
        i = int(np.argmax(np.abs(dev)))
        bulge = abs(float(dev[i])) / clen
        mid = (pts[0] + pts[-1]) / 2
        side = 1 if float((pts[i] - mid) @ (centre - mid)) > 0 else -1
    elif clen <= 1e-6:
        bulge = 1.0
    arcs = _arcs(pts, centre)
    seg = np.diff(pts, axis=0)
    seg = seg[np.linalg.norm(seg, axis=1) > 1e-9]
    turning = 0.0
    if len(seg) > 1:
        ang = np.arctan2(seg[:, 1], seg[:, 0])
        turning = float(np.degrees(np.abs((np.diff(ang) + np.pi) % (2 * np.pi) - np.pi)).sum())
    return {"type": ta + tb, "pos": pts.mean(0), "ori": _angle_deg(chord) % 180.0 if clen > 1e-6 else 0.0,
            "len": length, "bulge": 0 if bulge < STRAIGHT else (1 if side > 0 else 2), "curv": turning, "arcs": arcs,
            "chord": clen}


def _arcs(pts, centre, parts=4):
    """Parametric relation arcs along the traversal of a stroke (his two-level graph; eq. 155-157): the stroke resampled
    into equal parts; at every joint the tangent orientation, the bend and the side it bends to (traversal-independent)."""
    seglen = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total = float(seglen.sum())
    if len(pts) < 2 or total < 1e-6:
        return []
    cum = np.concatenate([[0.0], np.cumsum(seglen)])
    t = np.linspace(0.0, total, parts + 1)
    res = np.stack([np.interp(t, cum, pts[:, 0]), np.interp(t, cum, pts[:, 1])], 1)
    out = []
    for i in range(1, parts):
        v1, v2 = res[i] - res[i - 1], res[i + 1] - res[i]
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-9 or n2 < 1e-9:
            continue
        bend = math.degrees(math.acos(max(-1.0, min(1.0, float(v1 @ v2) / (n1 * n2)))))
        side = 0
        if bend >= 15.0:
            inside = (res[i - 1] + res[i + 1]) / 2 - res[i]
            side = 1 if float(inside @ (centre - res[i])) > 0 else 2
        out.append({"pos": res[i], "ori": _angle_deg(res[i + 1] - res[i - 1]) % 180.0, "bend": bend, "side": side})
    return out


# ----------------------------------------------------------------------------------------------- projection onto H0
PARAMS = {"E": ["pos", "dir"], "C": ["pos", "dir", "turn"], "J": ["pos", "deg"], "OO": ["pos", "ori", "size"]}
REL_PARAMS = ["pos", "ori", "len", "bulge"]


def _segment(name, value, level):
    if level == 1:
        return 0
    if name == "pos":
        return int(value[1] * level) * level + int(value[0] * level)
    if name == "dir":
        return int(((value + 180.0 / level) % 360.0) / (360.0 / level))      # sectors centred on 0°, 45°, ...
    if name == "ori":
        return int(((value + 90.0 / level) % 180.0) / (180.0 / level))
    if name == "turn":
        return int(value >= 60.0)
    if name == "deg":
        return int(value >= 4)
    if name == "len":
        return min(int(value / 1.2 * level), level - 1)                         # 1.2 = longest plausible stroke
    if name == "bulge":
        return int(value)
    if name == "size":
        return min(int(value / 3.0 * level), level - 1)
    if name == "bend":
        return int(value >= 25.0) if level == 2 else sum(value >= e for e in (15.0, 45.0, 90.0))
    if name == "side":
        return int(value)
    if name == "tort":
        return int(value >= 1.1) if level == 2 else sum(value >= e for e in (1.05, 1.2, 1.5))
    if name == "nlen":
        return min(int(value * level), level - 1)
    if name == "ang":
        return int(value >= 90.0) if level == 2 else sum(value >= e for e in (45.0, 90.0, 135.0))
    raise KeyError(name)


CURV_EDGES = {1: [], 2: [60.0], 4: [30.0, 90.0, 180.0]}


def _neighbours(name, value, level):
    """Overlapping receptive fields: the adjacent segment nearest to the value (half activation)."""
    if level == 1:
        return []
    if name == "pos":
        out, row, col = [], int(value[1] * level), int(value[0] * level)
        fx, fy = value[0] * level - col, value[1] * level - row
        c2 = col - 1 if fx < 0.5 else col + 1
        r2 = row - 1 if fy < 0.5 else row + 1
        if 0 <= c2 < level:
            out.append(row * level + c2)
        if 0 <= r2 < level:
            out.append(r2 * level + col)
        return out
    if name in ("dir", "ori") and level >= 4:
        span = 360.0 if name == "dir" else 180.0
        w = span / level
        x = ((value + w / 2) % span) / w
        s, t = int(x), x - int(x)
        return [(s - 1) % level if t < 0.5 else (s + 1) % level]
    if name == "len":
        x = value / 1.2 * level
        s = min(int(x), level - 1)
        n = s - 1 if x - s < 0.5 else s + 1
        return [n] if 0 <= n < level else []
    return []


def _curv_segment(value, level):
    return 0 if level == 1 else sum(value >= e for e in CURV_EDGES[level])


def _project(prim, params, levels, overlap):
    """(key-suffix, membership) for every level combination; with overlap also the half-active neighbours."""
    for combo in itertools.product(*[levels[n] for n in params]):
        exact = [(n, l, _curv_segment(prim[n], l) if n == "curv" else _segment(n, prim[n], l)) for n, l in zip(params, combo)]
        yield tuple(exact), 1.0
        if overlap:
            for i, (n, l, _) in enumerate(exact):
                for nb in _neighbours(n, prim[n], l):
                    yield tuple(exact[:i] + [(n, l, nb)] + exact[i + 1:]), 0.5


def _quantised(params, names):
    """Key suffixes from pre-quantised parameters {(name, level): segment} (two-level hypergraph, isl_2l), plus level 1."""
    lv = {n: [1] + sorted(L for (m, L) in params if m == n) for n in names}
    for combo in itertools.product(*[lv[n] for n in names]):
        yield tuple((n, L, 0 if L == 1 else params[(n, L)]) for n, L in zip(names, combo))


def activate(points, relations, cfg, extra=None):
    """Synapses of H0 activated by a stimulus (projection by topography). -> {key: activation = weight x membership}
    extra: the run hyperedges and break anchors of the two-level hypergraph (P3a), from activate_channels."""
    levels = cfg["levels"]
    overlap = cfg.get("rf", "exact") == "overlap"
    rel_params = REL_PARAMS + (["curv"] if cfg.get("curves") else [])
    memb = defaultdict(list)
    fov = {n: v + FOVEA.get(n, []) for n, v in levels.items()} if cfg.get("fovea") else levels
    for p in points:
        plevels = fov if not cfg.get("fixations") or p.get("fix") else levels       # P7: fovea only where fixated
        for suffix, m in _project(p, PARAMS[p["type"]], plevels, overlap):
            memb[(p["type"],) + suffix].append(m)
        if cfg.get("chains") and p["type"] == "J":                    # the direction each stroke leaves a junction
            for d in p["branches"]:
                for suffix, m in _project({"pos": p["pos"], "dir": d}, ["pos", "dir"], plevels, overlap):
                    memb[("JB",) + suffix].append(m)
    if cfg.get("chains"):
        for r in relations:
            for arc in r.get("arcs", []):
                for suffix, m in _project(arc, ["pos", "ori", "bend", "side"], levels, overlap):
                    memb[("K",) + suffix].append(m)
    if cfg["relations"]:
        for r in relations:
            params = PARAMS["OO"] if r["type"] == "OO" else rel_params
            for suffix, m in _project(r, params, levels, overlap):
                memb[("R", r["type"]) + suffix].append(m)
    if cfg.get("comanfeat"):                      # P3b: ComAN-like parameters (parametric synapses)
        strokes = [r for r in relations if r["type"] != "OO"]
        longest = max((r["len"] for r in strokes), default=0.0) or 1e-9
        for r in strokes:
            prim = {"tort": min(r["len"] / max(r.get("chord", 0.0), 1e-6), 10.0), "nlen": r["len"] / longest}
            for suffix, m in _project(prim, ["tort", "nlen"], levels, False):
                memb[("RT", r["type"]) + suffix].append(m)
        for p in points:
            if p["type"] != "J" or len(p.get("branches", [])) < 2:
                continue
            br = sorted(p["branches"])
            gaps = [min((br[(i + 1) % len(br)] - br[i]) % 360.0, 180.0) for i in range(len(br))]
            for stat, v in (("min", min(gaps)), ("max", max(gaps)), ("mean", float(np.mean(gaps)))):
                for suffix, m in _project({"pos": p["pos"], "ang": v}, ["pos", "ang"], JA_LEVELS, False):
                    memb[("JA", stat) + suffix].append(m)
    if extra:                                     # P3a: parametric hyperedges (runs of constant turn sign) + break anchors
        for h in extra.get("runs", []):
            for suffix in _quantised(h["params"], ["pos", "ori", "len", "turn"]):
                memb[("RN", h["cls"]) + suffix].append(1.0)
        for a in extra.get("banchors", []):
            for suffix in _quantised(a["params"], ["pos"]):
                memb[("B",) + suffix].append(1.0)
    act = {}
    for key, ms in memb.items():
        w = key_weight(key)
        for k, m in enumerate(sorted(ms, reverse=True), 1):                        # "at least k" multiplicity
            act[key + (("n", k),)] = w * m
    return act


def key_weight(key):
    """Synapse weight = 1 + information of its tuning (log2 of the number of segments at its levels)."""
    return 1.0 + sum(math.log2(l * l if n == "pos" else (len(CURV_EDGES[l]) + 1 if n == "curv" else l))
                     for n, l, _ in _named(key))


def shape_anchor_act(dense, cfg):
    """R2: the 32 dense centre-line points with their tangent orientation as point synapses (position cell x tangent
    orientation at the hierarchy levels; "at least k" multiplicity as in activate). dense = dense_representation()."""
    if not dense or not dense.get("points"):
        return {}
    levels = {"pos": cfg["levels"]["pos"], "ori": cfg["levels"]["ori"]}
    overlap = cfg.get("rf", "exact") == "overlap"
    pts = np.asarray(dense["points"], float).reshape(-1, 2)
    tans = np.asarray(dense["tangents"], float).reshape(-1, 2)          # doubled-angle unit vectors
    memb = defaultdict(list)
    for (x, y), (c2, s2) in zip(pts, tans):
        ori = (math.degrees(math.atan2(s2, c2)) / 2.0) % 180.0
        prim = {"pos": (min(max(x, 0.0), 0.999), min(max(y, 0.0), 0.999)), "ori": ori}
        for suffix, m in _project(prim, ["pos", "ori"], levels, overlap):
            memb[("SP",) + suffix].append(m)
    act = {}
    for key, ms in memb.items():
        w = key_weight(key)
        for k, m in enumerate(sorted(ms, reverse=True)[:4], 1):          # multiplicity capped at 4 per cell
            act[key + (("n", k),)] = w * m
    return act


def activate_channels(datas, cfg, dense=None):
    """Several filters of one image project onto the same synapses; the afferent takes the MAX (Lampl et al. 2004).
    dense: the image's dense centre-line description (R2 shape anchors, only with cfg["shape_anchors"])."""
    out = {}
    if cfg.get("shape_anchors") and dense:
        out.update(shape_anchor_act(dense, cfg))
    for d in datas:
        pts, rels = extract(d, cfg["frame"])
        extra = None
        if cfg.get("runs") or cfg.get("fixations"):
            if str(Path(__file__).parent) not in sys.path:
                sys.path.insert(0, str(Path(__file__).parent))
            import isl_2l as I2                    # two-level hypergraph (his first letter), traversal from the capture point
            hg = I2.build(d, "sign")
            if hg and cfg.get("runs"):
                extra = {"runs": [h for h in hg["hyper"] if h["kind"] == "sign"],
                         "banchors": [a for a in hg["anchors"] if a["type"] == "B"]}
            if cfg.get("fixations"):
                fix = [a["pos"] for a in hg["anchors"][:cfg["fixations"]]] if hg else []
                for p in pts:
                    p["fix"] = any(float(np.linalg.norm(p["pos"] - q)) < 0.03 for q in fix)
        for k, v in activate(pts, rels, cfg, extra).items():
            if v > out.get(k, 0.0):
                out[k] = v
    return out


# ----------------------------------------------------------------------------------------------- neurons
class Neuron:
    def __init__(self, cls, seed_family):
        self.cls, self.families = cls, []
        self.members = []                  # ids of the originals it absorbed (census / export)
        self.counts = Counter()            # Σ over originals of the (majority) presence of each synapse
        self.weights = {}
        self.seed = seed_family
        self.gain = 1.0

    def learn(self, family_keys, weights):
        self.families.append(family_keys)
        self.counts.update(family_keys)
        self.weights.update(weights)

    def attractor(self, tau):
        n = len(self.families)
        return {k: self.weights[k] for k, c in self.counts.items() if c / n >= tau - 1e-9}


def family_presence(members, augmented):
    """Synapses present in a majority of an original's augmentation family (§12)."""
    if not augmented or len(members) == 1:
        keep = set(members[0])
    else:
        votes = Counter(k for m in members for k in m)
        keep = {k for k, v in votes.items() if v * 2 >= len(members)}
    return keep, {k: key_weight(k) for k in keep}


def branch_of(key):
    """Dendritic branch of a synapse = its primitive type and coarse (2x2) position."""
    pos = next((s for n, l, s in _named(key) if n == "pos" and l == 2), -1)
    return (key[0], key[1] if key[0] == "R" else "", pos)


def branches(att):
    of = {k: branch_of(k) for k in att}
    tot = defaultdict(float)
    for k, w in att.items():
        tot[of[k]] += w
    return of, dict(tot)


def response(att, att_w, act, readout, total_drive=None, br=None):
    if not att:
        return 0.0
    common = att.keys() & act.keys()
    overlap = sum(act[k] for k in common)
    if readout == "a":
        return overlap / att_w
    if readout == "b":                                   # sigmoidal branch integration, soma sums the branches
        of, tot = br if br is not None else branches(att)
        got = defaultdict(float)
        for k in common:
            got[of[k]] += act[k]
        return sum(t / (1.0 + math.exp(-10.0 * (got.get(b, 0.0) / t - 0.5))) for b, t in tot.items()) / att_w
    drive = total_drive if total_drive is not None else sum(act.values())
    return overlap / math.sqrt(att_w * max(drive, 1e-9))   # c, d: divisive normalisation by the stimulus drive


def _named(key):
    return [x for x in key if isinstance(x, tuple) and len(x) == 3]


# ----------------------------------------------------------------------------------------------- training / evaluation
def build_stimuli(items, cfg):
    by_family = defaultdict(list)
    for it in items:
        by_family[(it["cls"], it["family"])].append((it["aug"], activate_channels(it["data"], cfg, it.get("dense"))))
    stimuli = {}
    for (cls, fam), members in by_family.items():
        members.sort(key=lambda t: t[0])
        acts = [a for _, a in members] if cfg["augment"] else [members[0][1]]
        keys, w = family_presence(acts, cfg["augment"])
        stimuli[(cls, fam)] = (keys, w)
    return stimuli


def train(stimuli, cfg, order_seed):
    rng = random.Random(order_seed)
    labels = {k: k[0] for k in stimuli}
    if cfg.get("shuffle_labels"):
        ls = list(labels.values())
        random.Random(1234).shuffle(ls)
        labels = dict(zip(labels, ls))
    neurons = defaultdict(list)
    if cfg.get("groups"):                  # fixed map: one neuron per given subclass (his hand-made subclasses)
        for fam in sorted(stimuli):
            keys, w = stimuli[fam]
            gid = cfg["groups"][fam[1]]
            nrn = next((n for n in neurons[labels[fam]] if n.seed == gid), None)
            if nrn is None:
                nrn = Neuron(labels[fam], gid)
                neurons[labels[fam]].append(nrn)
            nrn.learn(keys, w)
            nrn.members.append(fam)
        rng = None
    for cls in sorted(set(labels.values())) if not cfg.get("groups") else []:
        fams = sorted(k for k in stimuli if labels[k] == cls)
        rng.shuffle(fams)
        for fam in fams:
            keys, w = stimuli[fam]
            act = {k: w[k] for k in keys}
            best, best_r = None, -1.0
            for nrn in neurons[cls]:
                att = nrn.attractor(cfg["tau"])
                r = response(att, sum(att.values()) or 1e-9, act, cfg["readout"])
                if r > best_r:
                    best, best_r = nrn, r
            if best is not None and best_r >= cfg["rho"] * best.self_r:
                best.learn(keys, w)
                best.members.append(fam)
            else:
                nrn = Neuron(cls, fam)
                nrn.learn(keys, w)
                nrn.members.append(fam)
                att = nrn.attractor(cfg["tau"])
                nrn.self_r = response(att, sum(att.values()) or 1e-9, act, cfg["readout"]) or 1.0
                neurons[cls].append(nrn)
    flat = [n for v in neurons.values() for n in v]
    for nrn in flat:
        nrn.att = nrn.attractor(cfg["tau"])
        nrn.att_w = sum(nrn.att.values()) or 1e-9
        nrn.br = branches(nrn.att) if cfg["readout"] == "b" else None
    if cfg.get("gain") == "confirm":                     # strength grows with repeated confirmation: n / (n + 1)
        for nrn in flat:
            nrn.gain = len(nrn.families) / (len(nrn.families) + 1.0)
    if cfg["readout"] == "d":                            # intrinsic gain from the neuron's OWN positives only
        for nrn in flat:
            own = [response(nrn.att, nrn.att_w, {k: 1.0 for k in fam}, "c") for fam in nrn.families]
            nrn.gain = 1.0 / max(float(np.mean(own)), 1e-6)
    return flat


def own_mean(nrn, stimuli):
    """Mean readout-c response of a trained neuron to the stimuli of the families it absorbed (its own positives)."""
    vals = [response(nrn.att, nrn.att_w, {k: stimuli[f][1][k] for k in stimuli[f][0]}, "c") for f in nrn.members]
    return float(np.mean(vals)) if vals else 0.0


def band(values, tau=0.8):
    """Shortest interval holding >= tau of the values (Def. 1) -> (lo, hi)."""
    s = sorted(values)
    k = max(1, math.ceil(tau * len(s)))
    i = min(range(len(s) - k + 1), key=lambda j: s[j + k - 1] - s[j])
    return s[i], s[i + k - 1]


def param_score(vec, bands, floor=0.01):
    """R1: mean over dimensions of 1 inside the neuron's own band, falling linearly to 0 one band-width outside."""
    tot = 0.0
    for v, (lo, hi) in zip(vec, bands):
        w = max(hi - lo, floor)
        tot += 1.0 if lo <= v <= hi else max(0.0, 1.0 - (lo - v if v < lo else v - hi) / w)
    return tot / len(bands)


def attach_param_bands(neurons, family_vectors, tau=0.8):
    """R1: per neuron, bands over the descriptors of its OWN absorbed families (originals + augmentations)."""
    for nrn in neurons:
        vecs = [v for fam in nrn.members for v in family_vectors.get(fam, [])]
        nrn.pbands = [band(col, tau) for col in zip(*vecs)] if len(vecs) >= 2 else None


def attach_homeostasis(neurons, stimuli):
    """R5: intrinsic plasticity — gain = 1 / mean reaction on the neuron's own positives (Desai 1999)."""
    for nrn in neurons:
        mu = own_mean(nrn, stimuli)
        nrn.hgain = 1.0 / mu if mu > 0 else 1.0


def wjaccard(a, b):
    keys = a.keys() | b.keys()
    num = sum(min(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    den = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    return num / den if den else 0.0


def consolidate(neurons, cfg, theta):
    """R4 sleep-like consolidation: within a class, repeatedly merge the pair of neurons whose attractors overlap most
    (weighted Jaccard >= theta) and re-reduce the attractor over the joined originals (f >= tau). Local: only
    neurons of the same map compare their own attractors."""
    by = defaultdict(list)
    for n in neurons:
        by[n.cls].append(n)
    out = []
    for cls, ns in by.items():
        ns = list(ns)
        while len(ns) > 1:
            best, pair = -1.0, None
            for a in range(len(ns)):
                for b in range(a + 1, len(ns)):
                    j = wjaccard(ns[a].att, ns[b].att)
                    if j > best:
                        best, pair = j, (a, b)
            if best < theta:
                break
            a, b = pair
            m = Neuron(cls, ns[a].seed)
            for src in (ns[a], ns[b]):
                m.families += src.families
                m.counts.update(src.counts)
                m.weights.update(src.weights)
                m.members += src.members
            m.self_r = max(getattr(ns[a], "self_r", 1.0), getattr(ns[b], "self_r", 1.0))
            m.att = m.attractor(cfg["tau"])
            m.att_w = sum(m.att.values()) or 1e-9
            m.br = None
            ns = [x for k, x in enumerate(ns) if k not in pair] + [m]
        out += ns
    return out


_ACT_CACHE = {}


_STREAM = False


def test_acts(test_items, cfg):
    if _STREAM or len(test_items) > 3000:                  # large test sets: stream (activations of 20 800 images do not fit in memory)
        return ((lambda act: (act, sum(act.values())))(activate_channels(it["data"], cfg, it.get("dense"))) for it in test_items)
    key = (cfg["frame"], cfg["relations"], json.dumps(cfg["levels"], sort_keys=True), cfg.get("rf"), cfg.get("curves"),
           cfg.get("chains"), cfg.get("fovea"), cfg.get("runs"), cfg.get("comanfeat"), cfg.get("fixations"),
           cfg.get("shape_anchors"), id(test_items))
    if key not in _ACT_CACHE:
        out = []
        for it in test_items:
            act = activate_channels(it["data"], cfg, it.get("dense"))
            out.append((act, sum(act.values())))
        _ACT_CACHE[key] = out
    return _ACT_CACHE[key]


STRUCT = ("R", "K", "RN")   # relational synapses (hyperedges, arcs along strokes, P3a runs); others are point synapses


def _parts(nrn):
    """Structural / parametric halves of a neuron's attractor and its key set (computed once per trained neuron)."""
    if getattr(nrn, "parts", None) is None:
        s = {k: w for k, w in nrn.att.items() if k[0] in STRUCT}
        p = {k: w for k, w in nrn.att.items() if k[0] not in STRUCT}
        nrn.parts = (s, sum(s.values()) or 1e-9, p, sum(p.values()) or 1e-9, frozenset(nrn.att))
    return nrn.parts


def reaction_vector(nrn, act, drive_s, drive_p):
    """(structural, parametric) reaction, each part normalised as readout c (§15: both kinds of terms)."""
    s, sw, p, pw, _ = _parts(nrn)
    rs = sum(act[k] for k in s.keys() & act.keys()) / math.sqrt(sw * max(drive_s, 1e-9))
    rp = sum(act[k] for k in p.keys() & act.keys()) / math.sqrt(pw * max(drive_p, 1e-9))
    return rs, rp


def compete(cands, neurons, act, rule, gain=None, bonus=None):
    """Local WTA among co-activated neurons, the same rule for every neuron (his point 3).
    cands = [(scalar response, neuron index)] sorted by response, descending. -> index of the winner.
      pareto    a neuron is inhibited if another is >= on both reaction parts and > on one; largest sum among survivors
      distinct  co-active = response >= 0.9 x the strongest (k-WTA); j inhibits i if j's normalised activation on
                A_j minus A_i exceeds i's on A_i minus A_j; the winner is the one nobody inhibits, else the argmax"""
    if rule == "pareto":
        drive_s = sum(v for k, v in act.items() if k[0] in STRUCT)
        drive_p = sum(v for k, v in act.items() if k[0] not in STRUCT)
        vec = {i: reaction_vector(neurons[i], act, drive_s, drive_p) for _, i in cands}
        alive = [i for i in vec if not any(vec[j][0] >= vec[i][0] and vec[j][1] >= vec[i][1] and vec[j] != vec[i]
                                           for j in vec)]
        return max(alive, key=lambda i: (vec[i][0] + vec[i][1], -i))
    if rule not in ("distinct", "distinct_pool", "distinct_iter", "distinct_iter_free"):
        raise KeyError(rule)
    resp = {i: r for r, i in cands}
    if rule == "distinct":
        co = [i for r, i in cands if r >= 0.9 * cands[0][0]]
    elif rule == "distinct_pool":                        # P6 (ii): above the mean of the whole competing pool
        pool = sum(resp.values()) / len(resp)
        co = [i for r, i in cands if r > pool] or [cands[0][1]]
    else:                                                # P6 (i), (i'): everyone with a positive response starts active
        co = [i for r, i in cands if r > 0]
    if len(co) == 1:
        return co[0]
    sets = {i: _parts(neurons[i])[4] for i in co}
    memo = {}

    def evidence(i, j):                                  # i's normalised activation on what only i expects
        if (i, j) not in memo:
            d = sets[i] - sets[j]
            w = sum(neurons[i].att[k] for k in d)
            ev = sum(act[k] for k in d if k in act) / w if w else 0.0
            memo[(i, j)] = ev * (gain[i] if gain else 1.0) + (bonus[i] if bonus else 0.0)   # R5 / R1
        return memo[(i, j)]
    if rule in ("distinct", "distinct_pool"):
        free = [i for i in co if not any(j != i and evidence(j, i) > evidence(i, j) for j in co)]
        return free[0] if len(free) == 1 else cands[0][1]
    active = co
    while len(active) > 1:                               # rounds of mutual inhibition, the same rule for every neuron
        if rule == "distinct_iter":
            nxt = [i for i in active if not any(j != i and resp[j] > resp[i] and evidence(j, i) > evidence(i, j)
                                                for j in active)]
        else:
            nxt = [i for i in active if not any(j != i and evidence(j, i) > evidence(i, j) for j in active)]
        if not nxt or len(nxt) == len(active):
            break
        active = nxt
    return active[0] if len(active) == 1 else max(active, key=lambda i: (resp[i], -i))


def evaluate(neurons, test_items, cfg):
    rows = []
    for it, (act, drive) in zip(test_items, test_acts(test_items, cfg)):
        scores = []
        bonus_of = {}
        for i, nrn in enumerate(neurons):
            if len(nrn.families) < cfg.get("min_originals", 1):     # unconsolidated trace (single exposure)
                continue
            r = response(nrn.att, nrn.att_w, act, "c" if cfg["readout"] == "d" else cfg["readout"], drive, nrn.br) * nrn.gain
            if cfg.get("homeostasis"):                 # R5: reaction divided by the neuron's mean on its own positives
                r *= getattr(nrn, "hgain", 1.0)
            if cfg.get("param_beta") and it.get("dense") and getattr(nrn, "pbands", None):     # R1: soma reads p
                p_i = param_score(it["dense"]["orient"], nrn.pbands)
                bonus_of[i] = cfg["param_beta"] * p_i
                r += bonus_of[i]
            scores.append((r, -i, nrn.cls, i))
        scores.sort(reverse=True)
        ranked = list(dict.fromkeys(s[2] for s in scores))
        winner = scores[0][3] if scores else -1
        if cfg.get("competition") and scores and scores[0][0] > 0:      # vector reaction + local WTA (his point 3)
            gain = {i: getattr(n, "hgain", 1.0) for i, n in enumerate(neurons)} if cfg.get("homeostasis") else None
            winner = compete([(s[0], s[3]) for s in scores], neurons, act, cfg["competition"], gain, bonus_of or None)
            ranked = [neurons[winner].cls] + [c for c in ranked if c != neurons[winner].cls]
        row = {"true": it["cls"], "pred": ranked[0] if scores and scores[0][0] > 0 else "none",
               "top3": ranked[:3], "winner": winner, "stem": it["stem"]}
        if cfg.get("class_scores"):            # analysis: best response and neuron of every class
            best = {}
            for r, _, c, i in scores:
                if c not in best:
                    best[c] = (round(r, 5), i)
            row["class_scores"] = best
            row["r_win"] = next((round(r, 6) for r, _, _, i in scores if i == winner), 0.0)
        rows.append(row)
    return rows


_PAR = None


def _eval_chunk(idx):
    global _STREAM
    _STREAM = True                              # a worker evaluates its chunk once: no activation cache (memory)
    neurons, items, cfg = _PAR
    return list(zip(idx, evaluate(neurons, [items[i] for i in idx], cfg)))


def evaluate_parallel(neurons, test_items, cfg, workers):
    """Same as evaluate(); the trained neurons are shared with forked workers (copy-on-write), images interleaved."""
    import multiprocessing as mp
    global _PAR
    _PAR = (neurons, test_items, cfg)
    chunks = [list(range(w, len(test_items), workers)) for w in range(workers)]
    with mp.get_context("fork").Pool(workers) as pool:
        parts = pool.map(_eval_chunk, chunks)
    rows = [None] * len(test_items)
    for part in parts:
        for i, row in part:
            rows[i] = row
    return rows


def summarise(rows, neurons):
    n = len(rows)
    top1 = sum(r["pred"] == r["true"] for r in rows) / n
    top3 = sum(r["true"] in r["top3"] for r in rows) / n
    wins = Counter(r["winner"] for r in rows)
    foreign = Counter(r["winner"] for r in rows if r["pred"] != r["true"])
    univ = max((foreign[i] / wins[i] for i in wins if wins[i] >= 20), default=0.0)
    return {"top1": round(100 * top1, 2), "top3": round(100 * top3, 2), "neurons": len(neurons),
            "att_size_median": int(np.median([len(x.att) for x in neurons])) if neurons else 0,
            "univ_max": round(univ, 3)}


def mcnemar(a, b):
    """Two-sided exact McNemar p for paired correctness lists."""
    b01 = sum(1 for x, y in zip(a, b) if x and not y)
    b10 = sum(1 for x, y in zip(a, b) if y and not x)
    m = b01 + b10
    if m == 0:
        return 1.0, b01, b10
    k = min(b01, b10)
    p = sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m
    return min(1.0, 2 * p), b01, b10


DEFAULT = {"frame": "centroid", "levels": LEVELS, "relations": True, "augment": True, "tau": 1.0, "rho": 0.6,
           "readout": "c", "shuffle_labels": False, "min_originals": 1,
           "channels": ("t110",), "rf": "exact", "curves": False, "gain": "none"}


def run(cfg, train_items, dev_items, orders=(0,), tag=""):
    t0 = time.time()
    stimuli = build_stimuli(train_items, cfg)
    results = []
    for seed in orders:
        neurons = train(stimuli, cfg, seed)
        workers = cfg.get("workers", 1)
        rows = evaluate_parallel(neurons, dev_items, cfg, workers) if workers > 1 else evaluate(neurons, dev_items, cfg)
        results.append((summarise(rows, neurons), rows, neurons))
    s = [r[0] for r in results]
    agg = {k: round(float(np.mean([x[k] for x in s])), 2) for k in ("top1", "top3", "neurons", "att_size_median", "univ_max")}
    agg["top1_sd"] = round(float(np.std([x["top1"] for x in s])), 2)
    agg["secs"] = round(time.time() - t0, 1)
    print(f"{tag:<34} top1 {agg['top1']:6.2f} ±{agg['top1_sd']:<5} top3 {agg['top3']:6.2f} neurons {agg['neurons']:6.1f} "
          f"|A|~{agg['att_size_median']:<6} univ {agg['univ_max']:.2f}  ({agg['secs']}s)", flush=True)
    return agg, results


def inspect(cfg, train_items, dev_items, seed=0):
    """Per-class recall, top confusions and the neurons that win most often on other classes."""
    neurons = train(build_stimuli(train_items, cfg), cfg, seed)
    rows = evaluate(neurons, dev_items, cfg)
    print(summarise(rows, neurons))
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        per[r["true"]][1] += 1
        per[r["true"]][0] += r["pred"] == r["true"]
    print("recall: " + "  ".join(f"{c} {100 * a / n:.0f}" for c, (a, n) in sorted(per.items())))
    pairs = Counter((r["true"], r["pred"]) for r in rows if r["pred"] != r["true"])
    print("top confusions: " + ", ".join(f"{t}->{p} {n}" for (t, p), n in pairs.most_common(8)))
    wins = Counter(r["winner"] for r in rows)
    foreign = defaultdict(Counter)
    for r in rows:
        if r["pred"] != r["true"]:
            foreign[r["winner"]][r["true"]] += 1
    for i, _ in sorted(foreign.items(), key=lambda kv: -sum(kv[1].values()))[:5]:
        n = neurons[i]
        print(f"neuron {i} class {n.cls}: originals {len(n.families)}, |A| {len(n.att)}, wins {wins[i]}, "
              f"foreign {sum(foreign[i].values())} {dict(foreign[i].most_common(5))}")
    sizes = sorted(len(n.att) for n in neurons)
    print(f"attractor sizes: min {sizes[0]}, median {sizes[len(sizes) // 2]}, max {sizes[-1]}")


IMPROVEMENTS = {   # pre-registered 2026-10-20, before running: each alone on the reference, then all together
    "ref": {},
    "rf": {"rf": "overlap"},
    "rules": {"channels": ("t110r",)},
    "filters3": {"channels": ("t110r", "t150r", "t190r")},
    "curves": {"curves": True},
    "gain": {"gain": "confirm"},
    "all": {"rf": "overlap", "channels": ("t110r", "t150r", "t190r"), "curves": True, "gain": "confirm"},
    # post-hoc (added 2026-10-20 AFTER the single-switch results): only the switches that were non-inferior alone
    "best": {"rf": "overlap", "channels": ("t110r", "t150r", "t190r")},
}
_BEST = IMPROVEMENTS["best"]
IMPROVEMENTS.update({   # pre-registered 2026-10-21 from the error analysis, each on top of `best`
    "chains": {**_BEST, "chains": True},
    "fine": {**_BEST, "channels": ("t110r", "t150r", "t190r", "t150rf")},
    "fovea": {**_BEST, "fovea": True},
    "wideaug": {**_BEST, "train_channels": ("t110rw", "t150rw", "t190rw")},
    "rho8": {**_BEST, "rho": 0.8},
})
IMPROVEMENTS.update({
    # pre-registered rule: all five were non-inferior (> -1 pp) on both dev sets -> together
    "best2": {"rf": "overlap", "channels": ("t110r", "t150r", "t190r", "t150rf"), "chains": True, "fovea": True,
              "rho": 0.8, "train_channels": ("t110rw", "t150rw", "t190rw", "t150rfw")},
    # post-hoc (2026-10-21, after the single results): only the two that helped on BOTH dev sets
    "best2pos": {"rf": "overlap", "channels": ("t110r", "t150r", "t190r", "t150rf"), "fovea": True},
})


def improve(a):
    split, _, lim = a.train.partition(":")
    limit = int(lim) if lim else None
    names = list(IMPROVEMENTS) if a.variants == "all" else a.variants.split(",")
    groups = json.loads(Path(a.groups).read_text()) if a.groups else None
    out = OUT_DIR / a.out
    first = not out.exists()
    with out.open("a", newline="") as fh:
        wr = csv.writer(fh)
        if first:
            wr.writerow(["train", "dev", "variant", "map", "tau", "rho", "channels", "rf", "curves", "gain", "orders",
                         "top1", "top1_sd", "top3", "neurons", "att_size_median", "univ_max", "secs"])
        for name in names:
            over = IMPROVEMENTS[name]
            _ACT_CACHE.clear()                      # one variant's activations at a time (memory)
            for k in [k for k in _LOADED if tuple(k[1]) != tuple({**DEFAULT, **over}["channels"])]:
                del _LOADED[k]
            for tau in map(float, a.taus.split(",")):
                rhos = [over["rho"]] if "rho" in over else list(map(float, a.rhos.split(",")))
                for rho in (rhos if not groups else [0.0]):
                    cfg = {**DEFAULT, **over, "tau": tau, "rho": over.get("rho", rho), "workers": a.workers}
                    if groups:
                        cfg["groups"] = groups
                    ch = cfg["channels"]
                    tr = load(split, cfg.get("train_channels", ch), limit)
                    dev = [it for it in load(a.dev, ch) if it["aug"] == 0]
                    tag = f"{name} tau{tau}" + ("" if groups else f" rho{cfg['rho']}")
                    agg, res = run(cfg, tr, dev, tuple(range(1 if groups else a.orders)), tag)
                    if a.dump:
                        with open(a.dump, "a") as fd:
                            for r in res[0][1]:
                                fd.write(json.dumps({"config": tag, "train": a.train, "test": a.dev, **r}) + "\n")
                    wr.writerow([a.train, a.dev, name, "hand" if groups else "novelty", tau, cfg["rho"], "+".join(ch), cfg["rf"],
                                 cfg["curves"], cfg["gain"], 1 if groups else a.orders, agg["top1"], agg["top1_sd"],
                                 agg["top3"], agg["neurons"], agg["att_size_median"], agg["univ_max"], agg["secs"]])
                    fh.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["grid", "one", "inspect", "consolidation", "base76", "many", "improve"])
    ap.add_argument("--variants", default="all", help="comma list of improve variants")
    ap.add_argument("--taus", default="1.0,0.8,0.0")
    ap.add_argument("--rhos", default="0.6,0.7")
    ap.add_argument("--groups", default="", help="json {family: subclass} -> fixed map instead of novelty")
    ap.add_argument("--rules-tag", default="r", help="suffix of the rule-based caches")
    ap.add_argument("--dump", default="", help="write per-image predictions (order 0) to this jsonl")
    ap.add_argument("--workers", type=int, default=1, help="parallel evaluation processes (fork)")
    ap.add_argument("--tau", type=float, default=1.0)
    ap.add_argument("--rho", type=float, default=0.6)
    ap.add_argument("--readout", default="c")
    ap.add_argument("--train", default="cand60:10", help="split[:originals per class]")
    ap.add_argument("--dev", default="dev")
    ap.add_argument("--orders", type=int, default=5)
    ap.add_argument("--out", default="results_B.csv")
    a = ap.parse_args()
    split, _, lim = a.train.partition(":")
    train_items = load(split, limit=int(lim) if lim else None)
    dev_items = [it for it in load(a.dev) if it["aug"] == 0]
    orders = tuple(range(a.orders))
    print(f"train {split}: {len({(i['cls'], i['family']) for i in train_items})} originals, "
          f"{len(train_items)} skeletons; dev {len(dev_items)}", flush=True)
    if a.cmd == "improve":
        improve(a)
        return
    if a.cmd == "inspect":
        inspect({**DEFAULT, "tau": a.tau, "rho": a.rho, "readout": a.readout}, train_items, dev_items)
        return
    configs = []
    if a.cmd == "consolidation":       # post-hoc (after inspecting the grid): only neurons confirmed by >= 2 originals compete
        for tau in (1.0, 0.8):
            for rho in (0.5, 0.6, 0.7):
                for ro in ("a", "c"):
                    configs.append((f"consol2 tau{tau} rho{rho} read-{ro}",
                                    {**DEFAULT, "tau": tau, "rho": rho, "readout": ro, "min_originals": 2}))
    if a.cmd == "base76":                 # his 76 originals: hand subclasses (one neuron each) vs novelty
        groups = json.loads((REPO / "tests" / "_isl" / "base76_subclasses.json").read_text())
        for tau in (1.0, 0.9, 0.8, 0.0):
            for ro in ("a", "c"):
                configs.append((f"hand-subclasses tau{tau} read-{ro}", {**DEFAULT, "tau": tau, "readout": ro, "groups": groups}))
        for rho in (0.5, 0.6, 0.7):
            configs.append((f"novelty tau1.0 rho{rho} read-c", {**DEFAULT, "rho": rho}))
    if a.cmd == "many":                   # 60 originals per digit: does reduction help with more examples per style?
        for tau in (1.0, 0.8, 0.0):
            for rho in (0.5, 0.6, 0.7):
                configs.append((f"tau{tau} rho{rho} read-c", {**DEFAULT, "tau": tau, "rho": rho}))
        configs.append(("consol2 tau0.8 rho0.5 read-c", {**DEFAULT, "tau": 0.8, "rho": 0.5, "min_originals": 2}))
    if a.cmd == "one":
        configs.append(("default", dict(DEFAULT)))
    elif a.cmd == "grid":
        for tau in (1.0, 0.9, 0.8):
            for rho in (0.5, 0.6, 0.7):
                for ro in ("a", "b", "c", "d"):
                    configs.append((f"tau{tau} rho{rho} read-{ro}", {**DEFAULT, "tau": tau, "rho": rho, "readout": ro}))
        controls = [("ctl: shuffled labels", {"shuffle_labels": True}), ("ctl: tau 0 (no reduction)", {"tau": 0.0}),
                    ("ctl: coarsest level only", {"levels": {k: [v[0]] for k, v in LEVELS.items()}}),
                    ("ctl: no relations (no hyperedges)", {"relations": False}),
                    ("ctl: no augmentation", {"augment": False}), ("ctl: bbox frame", {"frame": "bbox"})]
        configs += [(name, {**DEFAULT, **over}) for name, over in controls]
    out = OUT_DIR / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    first = not out.exists()
    with out.open("a", newline="") as fh:
        wr = csv.writer(fh)
        if first:
            wr.writerow(["train", "dev", "config", "tau", "rho", "readout", "frame", "relations", "augment", "orders",
                         "top1", "top1_sd", "top3", "neurons", "att_size_median", "univ_max", "secs"])
        for name, cfg in configs:
            agg, _ = run(cfg, train_items, dev_items, orders, name)
            wr.writerow([a.train, a.dev, name, cfg["tau"], cfg["rho"], cfg["readout"], cfg["frame"], cfg["relations"],
                         cfg["augment"], len(orders), agg["top1"], agg["top1_sd"], agg["top3"], agg["neurons"],
                         agg["att_size_median"], agg["univ_max"], agg["secs"]])
            fh.flush()


if __name__ == "__main__":
    main()
