import numpy as np
import pytest


@pytest.fixture(scope="module")
def dense():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "src" / "skeletonization" / "dense_features.py"
    spec = importlib.util.spec_from_file_location("dense_features", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_vertical_line_puts_all_mass_in_the_vertical_bin(dense):
    img = np.zeros((100, 100), np.uint8); img[10:90, 50] = 1
    out = dense.dense_representation(img)
    orient = np.array(out["orient"]); g2 = orient[:16].reshape(4, 4); g3 = orient[16:].reshape(9, 4)
    assert g2.sum() == pytest.approx(1.0) and g3.sum() == pytest.approx(1.0)
    assert g2[:, 2].sum() == pytest.approx(1.0, abs=1e-6)            # bin 2 of 4 = 90 degrees
    assert len(out["points"]) == 2 * dense.N_POINTS and len(out["tangents"]) == 2 * dense.N_POINTS
    assert len(dense.orient_dimension_names()) == 52


def test_too_short_centre_line_gives_nothing(dense):
    img = np.zeros((20, 20), np.uint8); img[5, 5] = 1
    assert dense.dense_representation(img) is None


def test_deslant_turns_a_slanted_line_upright(dense):
    img = np.zeros((100, 100), np.uint8)
    for y in range(10, 90):
        img[y, 30 + (y - 10) // 2] = 1                       # a line leaning 27 degrees
    plain = np.array(dense.dense_representation(img)["orient"])[:16].reshape(4, 4)
    upright = np.array(dense.dense_representation(img, deslant=True)["orient"])[:16].reshape(4, 4)
    assert upright[:, 2].sum() > 0.9 and plain[:, 2].sum() < upright[:, 2].sum()
