"""Re-run the 10 Sep 2026 classical baselines (script at eea6e6b, 805 training samples, f34b049 test set)
and score every model on both the archive's 8,708 and the 8,707 ISL was run on.

The one image ISL's run_20260630_235356 did not see is mnist_test_4_00059: commit f292d11 relabelled it
complete -> incomplete, and f292d11's manifest has 8,707 complete images.

python -I rescore_8707.py <old_script.py> <repo_root> <out_dir>
"""
import csv
import importlib.util
import json
import os
import sys

import numpy as np

EXCLUDED = "mnist_all/4/mnist_test_4_00059.png"


def load_module(script: str, repo: str):
    sys.path.insert(0, os.path.join(repo, "src", "training"))
    spec = importlib.util.spec_from_file_location("cb_eea6e6b", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cb_eea6e6b"] = module
    spec.loader.exec_module(module)
    return module


def complete_paths(manifest: str) -> list[str]:
    with open(manifest, newline="") as f:
        return [row["image_path"] for row in csv.DictReader(f) if row["structure"] == "complete"]


def summarise(m, y_true: np.ndarray, preds: list[np.ndarray]) -> dict:
    scores = [m._score(y_true, p) for p in preds]
    agg = m.aggregate_seed_metrics(scores)
    recalls = np.mean([m.per_class_frame(y_true, p)["recall"].to_numpy() for p in preds], axis=0)
    agg["per_class_recall"] = [float(r) for r in recalls]
    agg["recall_min"], agg["recall_max"] = float(recalls.min()), float(recalls.max())
    agg["n"] = int(len(y_true))
    return agg


def main() -> None:
    script, repo, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    m = load_module(script, repo)
    import torch
    torch.set_num_threads(min(10, os.cpu_count() or 10))

    root = m.ensure_frozen_corpus(os.path.join(repo, "experiments", ".cache", "f34b049_datasets"))
    paths = complete_paths(os.path.join(root, "mnist_all_manifest.csv"))
    keep = np.array([p != EXCLUDED for p in paths])
    assert len(paths) == 8708 and int((~keep).sum()) == 1

    train = m.load_train_set(os.path.join(root, "train"))
    test = m.load_test_set(os.path.join(root, "mnist_all_manifest.csv"), root)
    train_flat, test_flat = m.flatten_split(train), m.flatten_split(test)
    train_cnn, test_cnn = m.to_cnn_split(train), m.to_cnn_split(test)

    preds: dict[str, list[np.ndarray]] = {}
    for name, metrics in m.run_deterministic_models(train_flat, test_flat).items():
        preds[f"{name}_single_fit"] = [metrics.y_pred]
        print(name, "done", flush=True)
    for name, fn, tr, te in (("mlp", m.build_mlp, train_flat, test_flat), ("cnn", m.build_cnn, train_cnn, test_cnn)):
        for key, result in m.run_torch_model(name, fn, tr, te, m.SEEDS, m.CONVERGENCE_MAX_EPOCHS).items():
            preds[key] = [s.y_pred for s in result.seed_metrics]
            print(key, "done, epochs", result.epochs_run, flush=True)

    out = {"excluded": EXCLUDED, "models": {}}
    for key, p in preds.items():
        out["models"][key] = {
            "all_8708": summarise(m, test.y, p),
            "isl_8707": summarise(m, test.y[keep], [x[keep] for x in p]),
            "excluded_true": int(test.y[~keep][0]),
            "excluded_pred": [int(x[~keep][0]) for x in p],
        }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "rescore_8707.json"), "w") as f:
        json.dump(out, f, indent=2)
    np.savez(os.path.join(out_dir, "predictions.npz"), paths=np.array(paths), y_true=test.y,
             **{k: np.stack(v) for k, v in preds.items()})
    for key, r in out["models"].items():
        a, b = r["all_8708"], r["isl_8707"]
        print(f"{key:28s} 8708 {a['accuracy']:.2f} sd {a['accuracy_sd']}  |  8707 {b['accuracy']:.2f} sd {b['accuracy_sd']}"
              f"  recall {b['recall_min']:.2f}-{b['recall_max']:.2f}")


main()
