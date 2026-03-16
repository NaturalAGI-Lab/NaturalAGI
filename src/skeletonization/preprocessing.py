"""
Image preprocessing utilities for skeletonization pipeline.
Extracted from experiments.ipynb.
"""
from __future__ import annotations

import os
from typing import Generator, Optional, Tuple

import numpy as np
from skimage.filters import threshold_otsu
from skimage.morphology import closing, remove_small_objects, skeletonize as skimage_skeletonize, square
from skan import Skeleton, summarize


def iterate_over_images_in_folder(folder_path: str) -> Generator[str, None, None]:
    """Yield image filenames from a folder."""
    for file in os.listdir(folder_path):
        if file.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")):
            yield file


def custom_binary_image(
    image: np.ndarray,
    threshold: Optional[float] = None,
    max_size: int = 9,
    closing_size: int = 0,
) -> Tuple[np.ndarray, float]:
    """
    Binarize image with configurable parameters.

    Args:
        image: Grayscale image array.
        threshold: Fixed threshold value. If None, Otsu is used.
        max_size: Remove objects with this many pixels or fewer.
        closing_size: Morphological closing kernel size (0 = disabled).

    Returns:
        (binary_image, threshold_used)
    """
    if threshold is None:
        threshold = threshold_otsu(image)

    binary = image > threshold
    binary = remove_small_objects(binary, max_size=max_size)

    if closing_size > 0:
        binary = closing(binary, square(closing_size))

    return binary, threshold


def custom_skeletonize(
    image: np.ndarray,
    threshold: Optional[float] = None,
    max_size: int = 9,
    closing_size: int = 0,
    min_branch_len: int = 7,
    use_adaptive: bool = False,
    prune_percent: float = 0.05,
    min_absolute: int = 5,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Skeletonize an image with configurable pruning.

    Args:
        image: Grayscale image array.
        threshold: Fixed binarization threshold. If None, Otsu is used.
        max_size: Remove objects with this many pixels or fewer.
        closing_size: Morphological closing kernel size (0 = disabled).
        min_branch_len: Fixed branch pruning threshold in pixels (used when use_adaptive=False).
        use_adaptive: If True, prune branches shorter than prune_percent of total skeleton length.
        prune_percent: Fraction of total skeleton length used as pruning threshold (e.g. 0.05 = 5%).
        min_absolute: Minimum pruning threshold in pixels (safety floor for adaptive mode).

    Returns:
        (skeleton, binary, threshold_used)
    """
    binary, threshold_used = custom_binary_image(image, threshold, max_size, closing_size)
    skeleton = skimage_skeletonize(binary)

    sk = Skeleton(skeleton, source_image=binary)
    summary = summarize(sk, separator="_")

    if use_adaptive:
        total_length = summary["branch_distance"].sum()
        prune_threshold = max(total_length * prune_percent, min_absolute)
        print(f"   Adaptive pruning: total={total_length:.1f}px, threshold={prune_threshold:.1f}px ({prune_percent*100}%)")
    else:
        prune_threshold = min_branch_len
        print(f"   Fixed pruning: threshold={prune_threshold}px")

    short_branches = summary[
        (summary.branch_type == 1) & (summary.branch_distance < prune_threshold)
    ].index
    print(f"   Pruning {len(short_branches)} short branches")
    sk = sk.prune_paths(short_branches)
    skeleton = sk.skeleton_image

    return skeleton, binary, threshold_used


def skeleton_to_points(skeleton: np.ndarray) -> np.ndarray:
    """Convert a skeleton image to an (N, 2) array of (x, y) points."""
    h, w = skeleton.shape
    points = [
        [x, y]
        for y in range(h)
        for x in range(w)
        if skeleton[y, x] > 0
    ]
    return np.array(points)
