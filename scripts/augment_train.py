"""Generate additional augmented variants of the concept-training samples.

The existing datasets/train/<cid>/ files are already augmented (\"*_augN.png\",
~10 variants per source). New variants are generated from the _aug1 files by
default to avoid compounding distortions.

Usage:
    natural-agi/bin/python scripts/augment_train.py --dst datasets/train_aug2x --per-image 1
"""
import argparse
import random
import re
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, grey_dilation, grey_erosion, map_coordinates

REPO = Path(__file__).resolve().parents[1]


def elastic(arr: np.ndarray, alpha: float, sigma: float,
            rng: np.random.Generator) -> np.ndarray:
    dx = gaussian_filter(rng.uniform(-1, 1, arr.shape), sigma) * alpha
    dy = gaussian_filter(rng.uniform(-1, 1, arr.shape), sigma) * alpha
    yy, xx = np.meshgrid(np.arange(arr.shape[0]), np.arange(arr.shape[1]),
                         indexing="ij")
    return map_coordinates(arr, [yy + dy, xx + dx], order=1, mode="constant")


def augment_once(img: Image.Image, rng: random.Random) -> Image.Image:
    np_rng = np.random.default_rng(rng.getrandbits(32))
    out = img.rotate(rng.uniform(-12, 12), resample=Image.BILINEAR, fillcolor=0)
    scale = rng.uniform(0.85, 1.15)
    side = max(1, round(out.width * scale))
    scaled = out.resize((side, side), Image.LANCZOS)
    canvas = Image.new("L", img.size, 0)
    canvas.paste(scaled, ((img.size[0] - side) // 2, (img.size[1] - side) // 2))
    arr = np.asarray(canvas, dtype=np.float32)
    arr = elastic(arr, alpha=rng.uniform(8, 20), sigma=4.0, rng=np_rng)
    if rng.random() < 0.5:
        arr = (grey_dilation(arr, size=(2, 2)) if rng.random() < 0.5
               else grey_erosion(arr, size=(2, 2)))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=str(REPO / "datasets" / "train"))
    parser.add_argument("--dst", required=True)
    parser.add_argument("--per-image", type=int, default=1,
                        help="new variants per source file")
    parser.add_argument("--source-pattern", default=r"_aug1\.png$",
                        help="regex over filenames to pick generation sources")
    parser.add_argument("--copy-all", action="store_true",
                        help="copy every existing file into dst (default: yes)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    src_root = Path(args.src)
    dst_root = Path(args.dst)
    source_re = re.compile(args.source_pattern)

    for concept_dir in sorted(p for p in src_root.iterdir() if p.is_dir()):
        out_dir = dst_root / concept_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(concept_dir.glob("*.png"))
        generated = 0
        for png in files:
            img = Image.open(png).convert("L")
            img.save(out_dir / png.name)
            if source_re.search(png.name):
                for k in range(args.per_image):
                    augment_once(img, rng).save(
                        out_dir / f"{png.stem}_x{k + 1}.png")
                    generated += 1
        print(f"{concept_dir.name}: {len(files)} копій + {generated} нових")


if __name__ == "__main__":
    main()
