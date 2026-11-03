"""Census of a trained map (lab log L1): how many `best2` neurons rest on ONE original (attractor = one sample's
augmentation family) and how often they win on the official tests (joined with the order-0 dumps by neuron index).
Usage: isl_census.py base76 cand60:10 cand60:60 ecand60:10 ecand60:60
"""
import json
import sys
from collections import Counter

import isl_sim as S

DUMPS = {"base76": "final2_base76_test.jsonl", "cand60:10": "final2_mnist_test.jsonl", "cand60:60": "final2_mnist_test.jsonl",
         "ecand60:10": "final2_emnist_test.jsonl", "ecand60:60": "final2_emnist_test.jsonl"}
for train in sys.argv[1:]:
    split, _, lim = train.partition(":")
    cfg = {**S.DEFAULT, **S.IMPROVEMENTS["best2"], "tau": 0.8}
    tr = S.load(split, cfg["train_channels"], int(lim) if lim else None)
    neurons = S.train(S.build_stimuli(tr, cfg), cfg, 0)
    sizes = [len(n.families) for n in neurons]
    n_orig = sum(sizes)
    single = sum(1 for s in sizes if s == 1)
    rows = [json.loads(l) for l in open(S.REPO / "tests" / "_isl" / DUMPS[train])]
    rows = [r for r in rows if r["train"] == train and "best2" in r["config"]]
    wins = Counter("single" if sizes[r["winner"]] == 1 else "multi" for r in rows)
    corr = Counter("single" if sizes[r["winner"]] == 1 else "multi" for r in rows if r["pred"] == r["true"])
    print(f"{train}: originals {n_orig}, neurons {len(neurons)}, single-original neurons {single} "
          f"({100 * single / len(neurons):.0f} % of neurons, {100 * single / n_orig:.0f} % of originals); "
          f"max originals per neuron {max(sizes)}, median {sorted(sizes)[len(sizes) // 2]}; "
          f"test rows {len(rows)}: wins by single {100 * wins['single'] / max(len(rows), 1):.1f} % "
          f"(acc {100 * corr['single'] / max(wins['single'], 1):.1f} %), by multi acc {100 * corr['multi'] / max(wins['multi'], 1):.1f} %",
          flush=True)
    S._LOADED.clear()
