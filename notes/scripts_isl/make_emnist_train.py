"""O2 / Q1 — ComAN training folders from the Section IV novelty map (Theorem 3 instead of hand subclasses).

Every consolidated neuron of the map (a groups JSON, >= 2 originals each) becomes a ComAN subclass:
<out>/<class>_<k>/ holds its originals and 10 augmentations of each (rotation ±10°, shift ±3 px — the same seeds as
the ISL cache, crc32("<stem>:<j>"), so both models see the same variants; §12).
Usage: make_emnist_train.py [--groups tests/_isl/emnist_groups_10.json --src tests/emnist_cand60 --out tests/_isl_train_emnist]
"""
import argparse
import json
import shutil
import zlib

import cv2

import isl_cache as C
import isl_sim as S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default="tests/_isl/emnist_groups_10.json")
    ap.add_argument("--src", default="tests/emnist_cand60")
    ap.add_argument("--out", default="tests/_isl_train_emnist")
    a = ap.parse_args()
    SRC, OUT = S.REPO / a.src, S.REPO / a.out
    groups = json.loads((S.REPO / a.groups).read_text())
    if OUT.exists():
        shutil.rmtree(OUT)
    n = 0
    for sub, stems in groups.items():
        d = OUT / sub
        d.mkdir(parents=True)
        for stem in stems:
            src = SRC / stem.split("_")[0] / f"{stem}.png"
            img = cv2.imread(str(src), cv2.IMREAD_GRAYSCALE)
            cv2.imwrite(str(d / f"{stem}.png"), img)
            for j in range(1, 11):
                cv2.imwrite(str(d / f"{stem}_aug{j}.png"), C.augment(img, zlib.crc32(f"{stem}:{j}".encode())))
            n += 11
    print(f"{len(groups)} subclasses, {n} images -> {OUT}")


if __name__ == "__main__":
    main()
