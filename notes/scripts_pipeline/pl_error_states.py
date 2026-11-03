"""Where do the top-1 errors of a band model come from? Reads a pl_dump jsonl (26 ranked letters with band scores).
States per error, using each letter's own 'normal' score range (90th percentile over its correctly classified images):
  BOTH-COVER  own concept and the winner both look normal            -> genuine ambiguity / same glyph
  OWN-MISSING own concept is far off, the winner looks normal        -> no concept for this writing mode
  NOBODY      nobody looks normal                                    -> odd image / broken skeleton
  RIVAL-LEAKS own looks normal, the winner does not                  -> a too-permissive rival
Also writes montages of error images for eyeballing. Usage: pl_error_states.py <dump.jsonl> <tag>
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
rows = [json.loads(l) for l in open(sys.argv[1])]
tag = sys.argv[2]
rows = [r for r in rows if r["status"] == "success" and r["ranked"]]
score = lambda r, L: next(x["bs"] for x in r["ranked"] if x["c"] == L)
thr = {L: np.percentile([score(r, L) for r in rows if r["true"] == L and r["pred"] == L], 90) for L in sorted({r["true"] for r in rows})}
errors = [r for r in rows if r["pred"] != r["true"]]
same_glyph = {frozenset("IL")}
states, pair_states = Counter(), defaultdict(Counter)
byrank = Counter()
for r in errors:
    own, riv = score(r, r["true"]) <= thr[r["true"]], score(r, r["pred"]) <= thr[r["pred"]]
    st = "BOTH-COVER" if own and riv else "OWN-MISSING" if riv else "RIVAL-LEAKS" if own else "NOBODY"
    r["state"] = st; states[st] += 1; pair_states[frozenset((r["true"], r["pred"]))][st] += 1
    rk = [x["c"] for x in r["ranked"]].index(r["true"]); r["rank"] = rk; byrank[min(rk, 5)] += 1
n = len(rows); e = len(errors)
print(f"{tag}: {n} answered, top-1 {100*(n-e)/n:.2f}%, errors {e}")
print("states:", "  ".join(f"{k} {v} ({100*v/e:.0f}%)" for k, v in states.most_common()))
sg = sum(1 for r in errors if frozenset((r["true"], r["pred"])) in same_glyph)
print(f"same-glyph pairs (I/l): {sg} ({100*sg/e:.1f}% of errors, {100*sg/n:.1f} pp)")
print("truth rank among errors: " + "  ".join(f"{'6+' if k==5 else k+1}: {100*v/e:.0f}%" for k, v in sorted(byrank.items())))
print("\ntop pairs with their state mix:")
for pair, c in sorted(pair_states.items(), key=lambda kv: -sum(kv[1].values()))[:14]:
    tot = sum(c.values()); print(f"  {'/'.join(sorted(pair))}: {tot:4d}  " + "  ".join(f"{k} {100*v/tot:.0f}%" for k, v in c.most_common()))
print("\nstate by truth rank:")
for st in states:
    rk = Counter(min(r["rank"], 5) for r in errors if r["state"] == st); tot = sum(rk.values())
    print(f"  {st:12s} 2nd {100*rk[1]/tot:.0f}%  3rd {100*rk[2]/tot:.0f}%  6+ {100*rk[5]/tot:.0f}%")

def montage(sel, name, cols=12, size=64):
    sel = sel[: cols * 6]
    rowsimg = []
    for i in range(0, len(sel), cols):
        tiles = []
        for r in sel[i:i + cols]:
            p = REPO / "tests" / "emnist_testfull" / r["true"] / Path(r["path"]).name
            im = cv2.resize(cv2.imread(str(p), 0), (size, size), interpolation=cv2.INTER_AREA)
            im = cv2.copyMakeBorder(im, 14, 0, 0, 0, cv2.BORDER_CONSTANT, value=0)
            cv2.putText(im, f"{r['true']}>{r['pred']}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, 255, 1)
            tiles.append(im)
        while len(tiles) < cols:
            tiles.append(np.zeros_like(tiles[0]))
        rowsimg.append(np.hstack(tiles))
    out = REPO / "notes" / "images" / f"errors_{tag}_{name}.png"
    cv2.imwrite(str(out), np.vstack(rowsimg)); print("wrote", out.relative_to(REPO))

rng = np.random.default_rng(0)
for st in ("BOTH-COVER", "OWN-MISSING", "NOBODY"):
    pool = [r for r in errors if r["state"] == st]
    montage([pool[i] for i in rng.permutation(len(pool))], st.lower())
json.dump({"thr": thr, "errors": [{"path": r["path"], "true": r["true"], "pred": r["pred"], "state": r["state"], "rank": r["rank"]} for r in errors]}, open(REPO / "tests" / "_fewshot_ref" / f"errors_{tag}.json", "w"))
