"""Regenerates golden_dm2_extra.json (the curv + epdir blocks) from the offline experiment that
measured them (notes/scripts_pipeline/exp_dm2.py: extra_dims, minus its dropped 'sharp' block).
Run from the repo root: ./.venv/bin/python unit_tests/fixtures/make_golden_dm2.py"""
import json
import sys
from pathlib import Path

import networkx as nx

REPO = Path(__file__).resolve().parents[2]
sys.argv = [sys.argv[0]]
sys.path.insert(0, str(REPO / "notes" / "scripts_pipeline"))
from exp_dm2 import extra_dims  # noqa: E402

OUT = Path(__file__).resolve().parent
golden = {}
for path in sorted((OUT / "skeletons").glob("*.json")):
    x = extra_dims(nx.node_link_graph(json.load(open(path))))
    golden[path.stem] = [float(v) for v in list(x[:26]) + list(x[35:])]   # skip sharp[9]
json.dump(golden, open(OUT / "golden_dm2_extra.json", "w"))
print(f"{len(golden)} fixtures, {len(next(iter(golden.values())))} extra dims")
