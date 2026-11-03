"""Where the final ComAN's gain comes from — numbers for the explanation the professor asked for (29.10.2026), computed
offline from the existing dumps; no live run, no new use of the official test (only the dumps of runs already made).

  dev     leave-one-out from the final on dev (each part removed alone): parametric layer, complexity term, filters;
          and the parametric bands at f = 1 (min / max over the concept's own images) instead of >= 0.8
  test    as is (his run 21.10) vs final on the official test: the chain of the runs, per digit, fixed / broken images,
          whether an attractor of the true class embeds at all, which concept wins the errors, which filter wins
  figure  example images (fixed / broken) -> <out>/examples.png
Usage: coman_explain.py <out dir>   (writes <out>/coman_explain.json and examples.png)
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

import coman_param_layer as Q  # noqa: E402
import coman_rerank as K  # noqa: E402

REPO = K.REPO
CO = REPO / "tests" / "_isl" / "coman"
FILTERS = ("t110", "t150", "t190", "fine150")
DEV = {f: CO / f"n_comb_{f}.jsonl" for f in FILTERS}
TEST = {f: CO / f"final2_test_{f}.jsonl" for f in FILTERS}
AS_IS = REPO / "tests" / "_isl" / "coman_mnist_all.jsonl"
SUB = Q.MANIFEST


def load(path):
    return {Path(r["path"]).stem: r for r in (json.loads(line) for line in open(path))}


def reactions(dumps, lam):
    """{stem: (true, {cid: (class, r, filter, cc)})} — per concept MAX over the filters + lam·log2(cc), minors only."""
    out = {}
    first = next(iter(dumps.values()))
    for stem in first:
        best = {}
        for f, d in dumps.items():
            for e in (d.get(stem) or {}).get("ranked", []):
                if e["minor"]:
                    r = (e["sim"] or 0.0) + lam * math.log2(max(e["cc"] or 1, 1))
                    if e["cid"] not in best or r > best[e["cid"]][1]:
                        best[e["cid"]] = (e["c"], r, f, e["cc"])
        out[stem] = (first[stem]["true"], best)
    return out


def models(tau):
    train = Q.load_desc("_isl_train")
    by = defaultdict(list)
    for r in train.values():
        if r.get("orient"):
            by[r["cls"]].append(r["orient"])
    return {sub: {"bands": [Q.band(col, tau) for col in zip(*vecs)]} for sub, vecs in by.items()}


def ranked(reac, desc, mods, beta):
    """{stem: (true, [(score, class, cid, filter)] best first)}."""
    out = {}
    for stem, (true, best) in reac.items():
        d = desc.get(stem, {})
        sc = []
        for cid, (cls, r, f, _) in best.items():
            m = mods.get(cid.split("s")[0])
            p = Q.param_score(d["orient"], m["bands"]) if beta and d.get("orient") and m else 0.0
            sc.append((r + beta * p, cls, cid, f))
        out[stem] = (true, sorted(sc, key=lambda t: -t[0]))
    return out


def acc(rk, keep=None):
    stems = [s for s in rk if keep is None or SUB.get(s) == keep]
    return round(100.0 * sum(1 for s in stems if rk[s][1] and rk[s][1][0][1] == rk[s][0]) / len(stems), 2)


def paired(a, b):
    """b − a on dev, 95 % CI and exact McNemar p (coman_rerank)."""
    pa = {s: (t, [x[1] for x in r]) for s, (t, r) in a.items()}
    pb = {s: (t, [x[1] for x in r]) for s, (t, r) in b.items()}
    d = K.paired(pa, pb)
    return {k: (round(v, 2) if k in ("delta", "lo", "hi") else v) for k, v in d.items()}


def dev_part():
    dumps = {f: load(p) for f, p in DEV.items()}
    desc = Q.load_desc("mnist_dev")
    m08, m10 = models(0.8), models(1.0)
    final = ranked(reactions(dumps, 0.05), desc, m08, 0.5)
    rows = {"final (4 filters, λ 0.05, parametric β 0.5, bands ≥ 0.8)": final}
    rows["− parametric layer (β 0) = N final"] = ranked(reactions(dumps, 0.05), desc, m08, 0.0)
    rows["− complexity term (λ 0)"] = ranked(reactions(dumps, 0.0), desc, m08, 0.5)
    rows["− fine filter (110 / 150 / 190)"] = ranked(reactions({f: dumps[f] for f in FILTERS[:3]}, 0.05), desc, m08, 0.5)
    for f in FILTERS:
        rows[f"only filter {f}"] = ranked(reactions({f: dumps[f]}, 0.05), desc, m08, 0.5)
    degenerate = {"4_1sD110ps", "4_1sD190ps", "8_1sD190ps"}  # folded from a subset of the originals, 3 nodes
    rows["− 3 concepts folded with skipped examples (4_1 D110 / D190, 8_1 D190)"] = ranked(
        {s: (t, {c: v for c, v in b.items() if c not in degenerate}) for s, (t, b) in reactions(dumps, 0.05).items()},
        desc, m08, 0.5)
    rows["parametric bands at f = 1 (min / max of own images)"] = ranked(reactions(dumps, 0.05), desc, m10, 0.5)
    rows["strict f = 1: − the 3 concepts and bands at f = 1"] = ranked(
        {s: (t, {c: v for c, v in b.items() if c not in degenerate}) for s, (t, b) in reactions(dumps, 0.05).items()},
        desc, m10, 0.5)
    for beta in (0.1, 0.3):
        rows[f"bands f = 1, β {beta}"] = ranked(reactions(dumps, 0.05), desc, m10, beta)
    return {name: {"dev": acc(rk), **({} if rk is final else {"vs_final": paired(final, rk)})} for name, rk in rows.items()}


def test_part():
    dumps = {f: load(p) for f, p in TEST.items()}
    desc = Q.load_desc("mnist_all")
    final = ranked(reactions(dumps, 0.05), desc, models(0.8), 0.5)
    q = {json.loads(line)["stem"]: json.loads(line)["pred"] for line in open(REPO / "tests/_isl/Q_param_test.jsonl")}
    assert sum(1 for s, (t, r) in final.items() if (r[0][1] if r else "none") != q[s]) == 0, "final not reproduced"
    asis = ranked(reactions({"t110": load(AS_IS)}, 0.10), {}, {}, 0.0)
    asis0 = ranked(reactions({"t110": load(AS_IS)}, 0.0), {}, {}, 0.0)
    comp = [s for s in final if SUB.get(s) == "complete"]
    pred = lambda rk, s: rk[s][1][0][1] if rk[s][1] else "none"  # noqa: E731
    win = lambda rk, s: rk[s][1][0] if rk[s][1] else None  # noqa: E731
    out = {"as_is_lambda_0.10_complete": acc(asis, "complete"), "as_is_lambda_0_complete": acc(asis0, "complete"),
           "final_complete": acc(final, "complete"), "n_complete": len(comp)}
    fixed = [s for s in comp if pred(asis, s) != final[s][0] and pred(final, s) == final[s][0]]
    broken = [s for s in comp if pred(asis, s) == final[s][0] and pred(final, s) != final[s][0]]
    out["fixed"], out["broken"] = len(fixed), len(broken)
    out["no_answer"] = {"as_is": sum(pred(asis, s) == "none" for s in comp), "final": sum(pred(final, s) == "none" for s in comp)}
    # does an attractor of the true class embed (minor) at all?
    emb = lambda rk, s: any(c == rk[s][0] for _, c, _, _ in rk[s][1])  # noqa: E731
    out["true_embeds"] = {"as_is": sum(emb(asis, s) for s in comp), "final": sum(emb(final, s) for s in comp)}
    cause = Counter()
    for s in fixed:
        cause["as is: no attractor of the true class embedded" if not emb(asis, s) else
              "as is: true class embedded but lost the competition"] += 1
    out["fixed_cause"] = dict(cause)
    bcause = Counter()
    for s in broken:
        bcause["final: no attractor of the true class embedded" if not emb(final, s) else
               "final: true class embedded but lost"] += 1
    out["broken_cause"] = dict(bcause)
    out["per_digit_complete"] = {d: {"as_is": acc({s: v for s, v in asis.items() if v[0] == d}, "complete"),
                                     "final": acc({s: v for s, v in final.items() if v[0] == d}, "complete")}
                                 for d in "0123456789"}
    out["wrong_winner_concepts"] = {
        "as_is": Counter(win(asis, s)[2] for s in comp if pred(asis, s) not in (final[s][0], "none")).most_common(8),
        "final": Counter(win(final, s)[2] for s in comp if pred(final, s) not in (final[s][0], "none")).most_common(8)}
    out["confusions_complete"] = {
        "as_is": Counter(f"{final[s][0]}→{pred(asis, s)}" for s in comp if pred(asis, s) != final[s][0]).most_common(10),
        "final": Counter(f"{final[s][0]}→{pred(final, s)}" for s in comp if pred(final, s) != final[s][0]).most_common(10)}
    out["winner_filter_final_complete"] = dict(Counter(win(final, s)[3] for s in comp if win(final, s)))
    # in which filters does an attractor of the true class embed (minor) — from the raw per-filter dumps
    emb_f = {s: {f for f, d in dumps.items() for e in (d.get(s) or {}).get("ranked", [])
                 if e["minor"] and e["c"] == final[s][0]} for s in comp}
    out["true_embeds_by_filter_final"] = {f: sum(f in emb_f[s] for s in comp) for f in FILTERS}
    out["true_embeds_only_without_110_final"] = sum(bool(emb_f[s]) and "t110" not in emb_f[s] for s in comp)
    out["fixed_no_embed_as_is_now_via"] = dict(Counter(
        "filter 110 (refolded concepts, stems rule)" if "t110" in emb_f[s] else "only other filters"
        for s in fixed if not emb(asis, s)))
    out["fixed_by_digit"] = dict(Counter(final[s][0] for s in fixed))
    out["broken_by_digit"] = dict(Counter(final[s][0] for s in broken))
    examples = {"fixed": [], "broken": []}
    for kind, pool in (("fixed", fixed), ("broken", broken)):
        seen = set()
        for s in sorted(pool):
            key = (final[s][0], pred(asis, s), pred(final, s))
            if key in seen:
                continue
            seen.add(key)
            examples[kind].append({"stem": s, "true": final[s][0], "as_is": pred(asis, s),
                                   "as_is_concept": win(asis, s)[2] if win(asis, s) else None,
                                   "final": pred(final, s), "final_concept": win(final, s)[2] if win(final, s) else None,
                                   "final_filter": win(final, s)[3] if win(final, s) else None,
                                   "true_embedded_as_is": emb(asis, s)})
    out["examples"] = examples
    return out


def figure(examples, path):
    pick = examples["fixed"][::max(1, len(examples["fixed"]) // 8)][:8] + examples["broken"][::max(1, len(examples["broken"]) // 4)][:4]
    fig, axes = plt.subplots(2, 6, figsize=(13, 5.4))
    for ax, e in zip(axes.flat, pick):
        img = Image.open(REPO / "tests" / "mnist_all" / e["true"] / f"{e['stem']}.png")
        ax.imshow(img, cmap="gray_r")
        ok = e["final"] == e["true"]
        ax.set_title(f"{e['stem'][-7:]}, правильна {e['true']}\nбуло {e['as_is']} ({e['as_is_concept'] or 'без відповіді'})\n"
                     f"стало {e['final']} ({(e['final_concept'] or '—').replace('ps', '')})",
                     fontsize=8, color="#1b6e20" if ok else "#a3241a")
        ax.axis("off")
    for ax in list(axes.flat)[len(pick):]:
        ax.axis("off")
    fig.suptitle("complete: зображення, виправлені (зелені) та зіпсовані (червоні) фінальною ComAN порівняно з ComAN як є",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    res = {"dev": dev_part(), "test": test_part()}
    figure(res["test"]["examples"], out / "examples.png")
    (out / "coman_explain.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res["test"].items() if k != "examples"}, ensure_ascii=False, indent=1))
    print(json.dumps(res["dev"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
