"""Build datasets/mnist_train_all/ (60k MNIST train split @100x100) + manifest.

Mirrors the datasets/mnist_all pipeline: PNG per class dir, LANCZOS upscale to
100x100, heuristic completeness annotation (no manual review — stated caveat).

Usage:
    natural-agi/bin/python scripts/build_mnist_train_dataset.py [--limit N]
"""
import argparse
import csv
import sys
import time
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from completeness_heuristic import (analyze_image, is_complete,
                                    read_mnist_images, read_mnist_labels)

RAW_DIR = REPO / "src" / "training" / "data" / "MNIST" / "raw"
OUT_DIR = REPO / "datasets" / "mnist_train_all"
MANIFEST = REPO / "datasets" / "mnist_train_all_manifest.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None,
                        help="process only the first N images (smoke runs)")
    args = parser.parse_args()

    images = read_mnist_images(RAW_DIR / "train-images-idx3-ubyte")
    labels = read_mnist_labels(RAW_DIR / "train-labels-idx1-ubyte")
    total = min(len(images), args.limit or len(images))
    print(f"Building {total} images -> {OUT_DIR} ({args.size}x{args.size})")

    for cls in range(10):
        (OUT_DIR / str(cls)).mkdir(parents=True, exist_ok=True)

    rows = []
    started = time.monotonic()
    complete_count = 0
    for idx in range(total):
        arr = images[idx]
        cls = int(labels[idx])
        name = f"mnist_train_{cls}_{idx:05d}.png"
        out_path = OUT_DIR / str(cls) / name

        metrics = analyze_image(arr)
        structure = "complete" if is_complete(metrics, cls) else "incomplete"
        complete_count += structure == "complete"

        if not out_path.exists():
            img = Image.fromarray(arr, mode="L")
            img.resize((args.size, args.size), Image.LANCZOS).save(out_path)

        rows.append({
            "image_path": f"mnist_train_all/{cls}/{name}",
            "class": cls,
            "structure": structure,
        })
        if (idx + 1) % 5000 == 0:
            elapsed = time.monotonic() - started
            print(f"  {idx + 1}/{total} ({elapsed:.0f}s)", flush=True)

    with MANIFEST.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image_path", "class", "structure"])
        writer.writeheader()
        writer.writerows(rows)

    share = complete_count / total * 100
    print(f"Done: {total} images, complete={complete_count} ({share:.1f}%), "
          f"manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
