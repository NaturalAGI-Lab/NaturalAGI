"""Builds a training set with a chosen augmentation recipe: originals are copied, augmentations regenerated.
Recipes (10 copies per original unless the name says x20), measured offline in notes/fewshot_error_analysis §14:
  rot8        rotation +-8 deg                       (what tests/emnist52/train ships with)
  best        rotation o elastic warp, a 2-3 px stroke break on 20% of the copies
  best_shear  the same plus shear on every second copy
Usage: make_aug_set.py <src train dir rel. tests/> <dst train dir rel. tests/> <recipe> [copies]
"""
import os
import shutil
import sys
import zlib
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]


sys.path.insert(0, str(REPO / 'src' / 'training'))
from augment import augment  # noqa: E402  (the recipe lives in the project now)


def main():
    src, dst, recipe = REPO / "tests" / sys.argv[1], REPO / "tests" / sys.argv[2], sys.argv[3]
    copies = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    n = 0
    for form in sorted(d for d in os.listdir(src) if (src / d).is_dir()):
        (dst / form).mkdir(parents=True, exist_ok=True)
        for f in sorted(os.listdir(src / form)):
            if "_aug" in f or not f.endswith(".png"):
                continue
            shutil.copy(src / form / f, dst / form / f)
            im = cv2.imread(str(src / form / f), 0)
            rng = np.random.default_rng(zlib.crc32(f"{recipe}|{f}".encode()))
            for k in range(copies):
                cv2.imwrite(str(dst / form / f.replace(".png", f"_aug{k + 1}.png")), augment(im, rng, k, copies, recipe))
                n += 1
    print(f"{dst}: {n} augmented images, recipe {recipe}, {copies} copies per original")


if __name__ == "__main__":
    main()
