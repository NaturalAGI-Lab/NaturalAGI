"""Contour-completeness heuristic, extracted from datasets/mnist_filter.ipynb
(cells 3/6/11) so the 60k train split can be annotated without the notebook.

Operates on the RAW 28x28 arrays (thresholds are tuned for that scale).
"""
import struct

import numpy as np
from scipy import ndimage
from skimage.measure import euler_number
from skimage.morphology import skeletonize

MAX_COMPONENTS = 1
MAX_AFTER_EROSION = 2
MAX_ENDPOINT_RATIO = 0.20


def read_mnist_images(path) -> np.ndarray:
    with open(path, "rb") as f:
        magic, n, rows, cols = struct.unpack(">IIII", f.read(16))
        assert magic == 2051
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return data.reshape(n, rows, cols)


def read_mnist_labels(path) -> np.ndarray:
    with open(path, "rb") as f:
        magic, n = struct.unpack(">II", f.read(8))
        assert magic == 2049
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return data


def analyze_image(img_arr: np.ndarray, threshold: int = 50,
                  min_component_size: int = 5) -> dict:
    binary = img_arr > threshold

    lab, n_raw = ndimage.label(binary)
    orig_sizes = sorted(
        [int((lab == i).sum()) for i in range(1, n_raw + 1)], reverse=True)
    n_components = len([s for s in orig_sizes if s >= min_component_size])

    eroded = ndimage.binary_erosion(binary, structure=np.ones((2, 2)), iterations=1)
    lab_e, _ = ndimage.label(eroded)
    if lab_e.max() > 0:
        sizes_e = [int((lab_e == i).sum()) for i in range(1, lab_e.max() + 1)]
        n_after_erosion = len([s for s in sizes_e if s >= 3])
    else:
        n_after_erosion = 0

    skel = skeletonize(binary).astype(np.int32)
    skel_len = int(skel.sum())
    if skel_len > 0:
        neighbor_count = (
            ndimage.convolve(skel, np.ones((3, 3), dtype=np.int32), mode="constant")
            - skel
        )
        n_endpoints = int(((skel == 1) & (neighbor_count == 1)).sum())
        endpoint_ratio = n_endpoints / skel_len
    else:
        endpoint_ratio = 0.0

    n_holes = n_components - int(euler_number(binary, connectivity=1))

    return {
        "n_components": n_components,
        "n_after_erosion": n_after_erosion,
        "endpoint_ratio": round(endpoint_ratio, 4),
        "n_holes": n_holes,
    }


def is_complete(metrics: dict, cls: int) -> bool:
    ok = (metrics["n_components"] <= MAX_COMPONENTS
          and metrics["n_after_erosion"] <= MAX_AFTER_EROSION
          and metrics["endpoint_ratio"] <= MAX_ENDPOINT_RATIO)
    if cls == 8:
        ok = ok and metrics["n_holes"] == 2
    return ok
