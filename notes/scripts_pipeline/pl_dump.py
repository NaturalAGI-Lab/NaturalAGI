"""Classify a tests/<dir> split through the live pipeline and dump full ranked results.
Usage: pl_dump.py <method> <dir rel. tests/> <per_class|0=all> <out.jsonl> [extra_json] [skip_first]"""
import os, sys, uuid, json, string
from collections import defaultdict
sys.path.insert(0, "src/training")
from classifier import classify_images_stream, extract_class_from_concept_id
METHOD, DIR, PER, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
EXTRA = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
SKIP = int(sys.argv[6]) if len(sys.argv) > 6 else 0
P = {"ged_timeout": 15, "skeletonization_threshold": 110, "simplification_epsilon": 4.55,   # thick_stroke_threshold comes via EXTRA when wanted
     "comparison_method": METHOD, "preprocess_fallback": True, **EXTRA}
imgs, truth, paths = [], {}, {}
for L in sorted(d for d in os.listdir(f"tests/{DIR}") if os.path.isdir(f"tests/{DIR}/{d}")):  # any class layout (letters, digits)
    fs = sorted(os.listdir(f"tests/{DIR}/{L}"))[SKIP:]
    if PER: fs = fs[:PER]
    for f in fs:
        iid = str(uuid.uuid4()); p = f"/opt/nuclio/shared_storage/{DIR}/{L}/{f}"
        imgs.append((p, iid, {**P, "image_id": iid})); truth[iid] = L; paths[iid] = p
print(f"[{METHOD}] {DIR}: submitting {len(imgs)} images {EXTRA}", flush=True)
res = classify_images_stream(imgs, idle_timeout=300)
acc = r0 = t3 = 0; st = defaultdict(int)
with open(OUT, "w") as fo:
    for iid, r in res.items():
        exp = truth[iid]; s = r.get("status"); st[s] += 1; ranked = []; pred = "none"
        if s == "success":
            ranked = [{"c": extract_class_from_concept_id(c["concept_id"]), "cid": c["concept_id"], "sim": c.get("similarity"),
                       "minor": bool(c.get("is_minor")), "cc": c.get("concept_complexity"), "ic": c.get("image_complexity"),
                       "bs": c.get("band_score"), "br": c.get("band_rank"), "ex": c.get("explanation")}
                      for c in r.get("classification_results", [])]
            m = [c for c in ranked if c["minor"]]
            if m: pred = m[0]["c"]
            if ranked: r0 += ranked[0]["c"] == exp
            t3 += exp in [c["c"] for c in ranked[:3]]
        acc += pred == exp
        ms = (r.get("profiling") or {}).get("classification_time_ms")
        fo.write(json.dumps({"image_id": iid, "path": paths[iid], "true": exp, "pred": pred, "status": s, "ms": ms, "ranked": ranked}) + "\n")
n = max(1, len(res))
print(f"[{METHOD}] n={len(res)} ACC={100*acc/n:.2f}% RANK0={100*r0/n:.2f}% TOP3={100*t3/n:.2f}% status={dict(st)}", flush=True)
