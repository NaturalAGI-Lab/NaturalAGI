"""Augmentation recipe for few-shot originals (measured on EMNIST, notes/port_log_2026-09-18.md):
rotation +-8 deg composed with an elastic warp, and a 2-3 px stroke break on the first fifth of the copies.
No learning anywhere; copies are deterministic per file name."""
import zlib

import cv2
import numpy as np


def rot(im, rng, deg=8):
    return cv2.warpAffine(im, cv2.getRotationMatrix2D((im.shape[1] / 2, im.shape[0] / 2), float(rng.uniform(-deg, deg)), 1.0), (im.shape[1], im.shape[0]))


def shear(im, rng):
    s = float(rng.uniform(-0.3, 0.3))
    return cv2.warpAffine(im, np.float32([[1, s, -s * im.shape[0] / 2], [0, 1, 0]]), (im.shape[1], im.shape[0]))


def elastic(im, rng, alpha=14.0, sigma=9.0):
    h, w = im.shape
    dx = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32) * 2 - 1, (0, 0), sigma) * alpha * 8
    dy = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32) * 2 - 1, (0, 0), sigma) * alpha * 8
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(im, gx + dx, gy + dy, cv2.INTER_LINEAR, borderValue=0)


def erase(im, rng, rmin=2, rmax=3):
    out = im.copy()
    ys, xs = np.where(im > 110)
    if len(ys):
        j = int(rng.integers(len(ys)))
        cv2.circle(out, (int(xs[j]), int(ys[j])), int(rng.integers(rmin, rmax + 1)), 0, -1)
    return out


def augment(im, rng, k, copies=10, recipe="best"):
    if recipe == "rot8":
        return rot(im, rng)
    out = elastic(rot(im, rng), rng)
    if recipe == "best_shear" and k % 2:
        out = shear(out, rng)
    if k < max(1, copies // 5):
        out = erase(out, rng)
    return out


def rng_for(file_name: str, recipe: str = "best") -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(f"{recipe}|{file_name}".encode()))


def write_copies(src_png: str, dst_dir: str, copies: int = 10, recipe: str = "best") -> list:
    """<stem>_aug1..N.png next to a copy of the original; returns the written file names."""
    import os
    import shutil
    name = os.path.basename(src_png)
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy(src_png, os.path.join(dst_dir, name))
    im = cv2.imread(src_png, 0)
    rng = rng_for(name, recipe)
    out = [name]
    for k in range(copies):
        aug = name.replace(".png", f"_aug{k + 1}.png")
        cv2.imwrite(os.path.join(dst_dir, aug), augment(im, rng, k, copies, recipe))
        out.append(aug)
    return out
