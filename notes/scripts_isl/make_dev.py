"""P0 — MNIST dev set from the official TRAIN split + leakage checks.

dev = train images of each digit with per-digit index 60..259 (candidates mnist_cand60 are 0..59), resized like the
test PNGs (PIL LANCZOS 28 -> 100). The baseline's 76 hand-picked originals (datasets/train, non-augmented) are located in
the official splits by nearest 28x28 correlation; any that fall inside the dev range are dropped from dev.

Usage: make_dev.py            -> tests/mnist_dev/<d>/<d>_v<k>.png + tests/_isl/mnist_dev_manifest.json
"""
import json
from pathlib import Path

import cv2
import numpy as np
import torchvision
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "tests" / "_mnist_raw"
OUT = REPO / "tests" / "mnist_dev"
MANIFEST = REPO / "tests" / "_isl" / "mnist_dev_manifest.json"
DEV_RANGE = range(60, 260)


def _norm(a):
    a = a.reshape(len(a), -1).astype(float)
    a -= a.mean(1, keepdims=True)
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-9)


def main():
    tr = torchvision.datasets.MNIST(str(RAW), train=True)
    te = torchvision.datasets.MNIST(str(RAW), train=False)
    X, y = tr.data.numpy(), tr.targets.numpy()
    by_digit = {d: np.where(y == d)[0] for d in range(10)}

    # where do the baseline originals come from? (per-digit train index of the nearest image)
    nt, ne = _norm(X), _norm(te.data.numpy())
    originals = {}
    for p in sorted((REPO / "datasets" / "train").rglob("*.png")):
        if "_aug" in p.name:
            continue
        v = _norm(cv2.resize(cv2.imread(str(p), 0), (28, 28), interpolation=cv2.INTER_AREA)[None])[0]
        ct = nt @ v
        i = int(ct.argmax())
        d = int(y[i])
        originals[p.name] = {"digit": d, "train_k": int(np.where(by_digit[d] == i)[0][0]), "ncc_train": round(float(ct.max()), 4),
                             "ncc_test_max": round(float((ne @ v).max()), 4), "folder": p.parent.name}
    clash = {(o["digit"], o["train_k"]) for o in originals.values() if o["train_k"] in DEV_RANGE}

    OUT.mkdir(parents=True, exist_ok=False)
    rows, test_bytes = [], {x.tobytes() for x in te.data.numpy()}
    for d in range(10):
        (OUT / str(d)).mkdir()
        for k in DEV_RANGE:
            if (d, k) in clash:
                continue
            img = X[by_digit[d][k]]
            assert img.tobytes() not in test_bytes
            name = f"{d}_v{k:03d}.png"
            Image.fromarray(img).resize((100, 100), Image.LANCZOS).save(OUT / str(d) / name)
            rows.append({"file": f"{d}/{name}", "digit": d, "train_k": k, "train_index": int(by_digit[d][k])})
    MANIFEST.write_text(json.dumps({"dev": rows, "baseline_originals": originals,
                                    "excluded_from_dev": sorted(map(list, clash))}, indent=1))
    ks = sorted(o["train_k"] for o in originals.values())
    print(f"dev images: {len(rows)}; baseline originals in dev range (excluded): {len(clash)}")
    print(f"baseline originals: per-digit train index range {ks[0]}..{ks[-1]}, "
          f"min NCC to train {min(o['ncc_train'] for o in originals.values())}, "
          f"max NCC to test {max(o['ncc_test_max'] for o in originals.values())}")


if __name__ == "__main__":
    main()
