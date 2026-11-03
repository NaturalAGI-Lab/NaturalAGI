"""Regenerates the golden direction maps from the REFERENCE implementation that produced every
offline number (notes/scripts_fewshot/fs_decide.py: desc + matrix). Run from the repo root:
    ./.venv/bin/python unit_tests/fixtures/make_golden.py
Provenance only; the unit tests read skeletons/*.json and golden_dm.json."""
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "notes" / "scripts_fewshot"))
from fs_decide import desc, matrix  # noqa: E402

REF = REPO / "tests" / "_fewshot_ref" / "skel_cache"
OUT = Path(__file__).resolve().parent
picks = []
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    picks.append(sorted((REF / "testfull" / letter).glob("*.json"))[0])
for form in ("uA", "lb", "uO", "lq"):
    picks.append(sorted((REF / "e52_train" / form).glob("*.json"))[0])

(OUT / "skeletons").mkdir(exist_ok=True)
golden = {}
for src in picks:
    name = src.name.replace(".png.json", "")
    shutil.copy(src, OUT / "skeletons" / f"{name}.json")
    X, _ = matrix([desc(str(src))], (2, 3))
    golden[name] = [float(v) for v in X[0]]
json.dump(golden, open(OUT / "golden_dm.json", "w"))
print(f"{len(golden)} fixtures, {len(next(iter(golden.values())))} dims")
