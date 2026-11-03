"""Per-concept background calibration: mu/sd of score0 = sim + 0.10*log2(concept_complexity) over calibration images
of OTHER classes -> calib_mu / calib_sd on the concept's nodes. Stats are comparator-specific.
Usage: pl_calib.py <calib_dump.jsonl> [--strip-offsets] [--dry]"""
import sys, json, math, numpy as np
from collections import defaultdict
from neo4j import GraphDatabase
DUMP = sys.argv[1]; STRIP = "--strip-offsets" in sys.argv; DRY = "--dry" in sys.argv
rows = [json.loads(l) for l in open(DUMP)]; rows = [r for r in rows if r["status"] == "success" and r["ranked"]]
bg = defaultdict(list)
for r in rows:
    for x in r["ranked"]:
        raw = x["sim"] or 0
        if STRIP: raw -= 3.0 if raw >= 3.0 else 2.0 if raw >= 2.0 else 0.0
        if x["c"] != r["true"]: bg[x["cid"]].append(raw + 0.10 * math.log2(max(x["cc"] or 1, 1)))
stats = {c: (float(np.mean(v)), float(max(np.std(v), 1e-3))) for c, v in bg.items()}
print(f"{len(rows)} calibration images, stats for {len(stats)} concepts")
if not DRY:
    d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "111122223333"))
    with d.session() as s:
        for c, (mu, sd) in stats.items(): s.run("MATCH (n {concept_id:$c}) SET n.calib_mu=$mu, n.calib_sd=$sd", c=c, mu=mu, sd=sd)
    d.close(); print("written")
