"""One-shot preprocessing: upscale `datasets/mnist_all/{cls}/*.png` to 100x100
in place so the classification pipeline (trained on 100x100 `datasets/train/`)
can evaluate against it.

Idempotent: skips images that are already 100x100.
"""

from __future__ import annotations

import os
import sys
from PIL import Image

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "datasets", "mnist_all")
)
TARGET_SIZE = (100, 100)
RESAMPLE = Image.Resampling.LANCZOS


def resize_dir(cls_dir: str) -> tuple[int, int, int]:
    """Returns (resized, skipped, errors)."""
    resized = skipped = errors = 0
    for fname in os.listdir(cls_dir):
        if not fname.endswith(".png"):
            continue
        path = os.path.join(cls_dir, fname)
        try:
            with Image.open(path) as im:
                if im.size == TARGET_SIZE:
                    skipped += 1
                    continue
                resized_im = im.resize(TARGET_SIZE, RESAMPLE)
            resized_im.save(path, format="PNG")
            resized += 1
        except Exception as e:
            print(f"  ERROR {path}: {e}", file=sys.stderr)
            errors += 1
    return resized, skipped, errors


def main() -> int:
    if not os.path.isdir(ROOT):
        print(f"ERROR: {ROOT} not found", file=sys.stderr)
        return 1

    total_resized = total_skipped = total_errors = 0
    classes = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
    for cls in classes:
        cls_dir = os.path.join(ROOT, cls)
        r, s, e = resize_dir(cls_dir)
        print(f"class {cls}: resized={r}, skipped={s}, errors={e}")
        total_resized += r
        total_skipped += s
        total_errors += e

    print(f"\nTOTAL: resized={total_resized}, skipped={total_skipped}, errors={total_errors}")
    return 0 if total_errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
