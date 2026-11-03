"""Second round by the OLD approach: the band concepts shortlist the top-5 letters, a structural graph comparator
ranks the fold concepts of those letters. Reads the shortlist dumps and the band-decide dump of the same images.
Usage: pl_round2_structural.py <decide_dump.jsonl> <name=shortlist_dump.jsonl> ..."""
import json, sys, numpy as np
dec = {json.loads(l)["path"]: json.loads(l) for l in open(sys.argv[1])}
for arg in sys.argv[2:]:
    name, path = arg.split("=", 1); rows = [json.loads(l) for l in open(path)]; rows = [r for r in rows if r["status"] == "success" and r["ranked"] and r["path"] in dec and dec[r["path"]]["ranked"]]
    n = len(rows); res = {}
    def add(k, ok): res[k] = res.get(k, 0) + int(ok)
    for r in rows:
        t = r["true"]; d = dec[r["path"]]["ranked"]
        two_stage = [x["c"] for x in d]                                   # live order: bands + shape context
        band = [x["c"] for x in sorted(d, key=lambda x: x["bs"])]          # band concepts alone
        top5 = band[:5]
        struct = []
        for x in r["ranked"]:
            if x["c"] not in struct: struct.append(x["c"])
        struct = [c for c in struct if c in top5] + [c for c in top5 if c not in struct]
        add("band concepts only", band[0] == t); add("bands + shape context (examples)", two_stage[0] == t); add("structural comparator inside the band top-5", struct[0] == t)
        bs = {x["c"]: x["bs"] for x in d}; b = np.array([bs[c] for c in top5]); zb = (b - b.mean()) / (b.std() + 1e-9)
        pos = np.array([struct.index(c) for c in top5], float); zs = (pos - pos.mean()) / (pos.std() + 1e-9)
        for lam in (0.25, 0.5, 1.0):
            add(f"bands + {lam} x structural rank", top5[int(np.argmin(zb + lam * zs))] == t)
        add("truth inside the band top-5", t in top5)
    print(f"{name}: {n} images"); [print(f"   {k:46s}: {100*v/n:.2f}") for k, v in res.items()]
