from src.reduction_strategy.corner_point_reduction_strategy import (
    signed_area,
    orientation_from_windings,
)


def test_signed_area_sign_distinguishes_winding():
    """concept-6 loops anchored at their intersection: the concept loop is
    traversed counter-clockwise (positive area), the image loop clockwise
    (negative area)."""
    concept = [(-0.37, 0.67), (0.1, 0.33), (0.57, 0.37), (0.2, 0.83)]
    image = [(-0.3, -0.2), (-0.6, 0.3), (-0.4, 0.8), (0.0, 0.6), (0.2, 0.0)]

    assert signed_area(concept) > 0
    assert signed_area(image) < 0


def test_orientation_reverse_only_when_confident_and_opposite():
    # confident + opposite winding -> reverse the large set before matching
    assert orientation_from_windings(0.248, -0.485) == "reverse"
    # same sign -> co-oriented, keep cost-based default
    assert orientation_from_windings(0.248, 0.485) is None
    # either side near-zero (collinear / undefined winding) -> degenerate, default
    assert orientation_from_windings(0.005, -0.485) is None
    assert orientation_from_windings(0.248, -0.005) is None
