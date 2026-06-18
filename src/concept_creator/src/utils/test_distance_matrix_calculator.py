import logging

import numpy as np

from src.utils.distance_matrix_calculator import DistanceMatrixCalculator


def _calc():
    return DistanceMatrixCalculator(logging.getLogger("test"))


def test_counter_oriented_sequence_removes_geometrically_correct_corner():
    """Regression for 8_1 / image 6245cc98.

    The figure-8 lower loop yields corner sequences traversed in OPPOSITE
    angular order:
        concept (cols): [-82987685 (0.3,-0.8),  A (-0.4,-0.6)]
        image   (rows): [B (-0.1,-0.6), M=-65809004 (0.5,-0.8), C (0.6,-0.3)]
    The geometrically correct matching (-82987685<->M, A<->B) is a CROSSING in
    index space, so a forward-only monotone DP cannot express it and drops the
    wrong corner (B). Orientation-agnostic matching must drop C instead.
    """
    calc = _calc()
    dm = np.array([[0.143, 0.090],   # B
                   [0.070, 0.266],   # M
                   [0.222, 0.320]])  # C
    points_large = ["B", "M", "C"]

    removed = calc.find_ordered_points_for_difference(dm, points_large, 1)

    assert removed == ["C"]


def test_co_oriented_sequence_preserves_forward_choice():
    """When the sequences are already co-oriented (the 3_1 case the monotone DP
    was added for), the forward matching is optimal and must be preserved."""
    calc = _calc()
    dm = np.array([[0.0, 0.9],   # X -> col0
                   [0.9, 0.0],   # Y -> col1
                   [0.9, 0.9]])  # Z surplus
    points_large = ["X", "Y", "Z"]

    removed = calc.find_ordered_points_for_difference(dm, points_large, 1)

    assert removed == ["Z"]


def test_orientation_param_forces_chosen_direction():
    """The strategy decides orientation geometrically (winding) and passes it in;
    the DP must honour a forced orientation, and default to cost-min when None.

    Real concept-6 / b2f649f1 loop matrix (rows=image corners, cols=concept):
    forward is cheaper (0.6116) so cost-min drops node2 — but the loops are
    counter-oriented, so winding forces 'reverse' and drops node3 (correct).
    """
    calc = _calc()
    dm = np.array([[0.202, 0.379, 0.278],   # node3
                   [0.219, 0.318, 0.198],   # 207514122
                   [0.085, 0.270, 0.091],   # -10503959
                   [0.145, 0.169, 0.262]])  # node2
    large = ["node3", "207514122", "-10503959", "node2"]

    assert calc.find_ordered_points_for_difference(dm, large, 1) == ["node2"]
    assert calc.find_ordered_points_for_difference(dm, large, 1, orientation="forward") == ["node2"]
    assert calc.find_ordered_points_for_difference(dm, large, 1, orientation="reverse") == ["node3"]


def test_removes_requested_count():
    """difference=2 removes exactly two points, keeping the best monotone pair
    under whichever orientation is cheaper."""
    calc = _calc()
    dm = np.array([[0.0, 0.9],
                   [0.9, 0.9],
                   [0.9, 0.9],
                   [0.9, 0.0]])
    points_large = ["X", "Y", "Z", "W"]

    removed = calc.find_ordered_points_for_difference(dm, points_large, 2)

    assert set(removed) == {"Y", "Z"}
