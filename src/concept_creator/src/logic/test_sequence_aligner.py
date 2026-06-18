from src.logic.sequence_aligner import align_monotone_one_to_one

V = ["Vector"]
P = ["Point"]
HV = ["HorizontalVector", "Vector"]
VV = ["VerticalVector", "Vector"]


def test_equal_length_identity_best_is_full_diagonal():
    sim = [[0.9, 0.1], [0.1, 0.9]]
    assert align_monotone_one_to_one(sim, [V, V], [V, V]) == [(0, 0), (1, 1)]


def test_unequal_length_saturates_shorter_indices_strictly_increasing():
    # A has 1 node, B has 3; A's node matches its best same-type column.
    sim = [[0.9, 0.0, 0.5]]
    pairs = align_monotone_one_to_one(sim, [HV], [HV, P, VV])
    assert pairs == [(0, 0)]
    assert len(pairs) == min(1, 3)


def test_longer_concept_drops_surplus_keeps_min():
    # A=[V,P,V,P] (4), B=[V,P,V] (3): only monotone same-type triple is (0,1,2).
    sim = [[0.8, 0.0, 0.4],
           [0.0, 0.8, 0.0],
           [0.4, 0.0, 0.8],
           [0.0, 0.5, 0.0]]
    pairs = align_monotone_one_to_one(sim, [V, P, V, P], [V, P, V])
    assert pairs == [(0, 0), (1, 1), (2, 2)]


def test_crossing_temptation_prefers_monotone_over_higher_crossing_cell():
    # Off-diagonal cells are larger, but the only count-2 monotone match is the diagonal.
    sim = [[0.1, 0.9], [0.8, 0.2]]
    assert align_monotone_one_to_one(sim, [V, V], [V, V]) == [(0, 0), (1, 1)]


def test_type_incompatible_never_matched_even_with_high_similarity():
    sim = [[0.99]]
    assert align_monotone_one_to_one(sim, [V], [P]) == []


def test_horizontal_and_vertical_vectors_match_via_shared_vector_label():
    sim = [[0.4]]
    assert align_monotone_one_to_one(sim, [HV], [VV]) == [(0, 0)]


def test_empty_a_or_b_returns_empty():
    assert align_monotone_one_to_one([], [], [V, V]) == []
    assert align_monotone_one_to_one([[], []], [V, V], []) == []


def test_all_zero_row_still_matched_when_cardinality_demands_it():
    # min == 1, so the single shorter-side node is matched despite zero similarity.
    sim = [[0.0, 0.0, 0.0]]
    assert align_monotone_one_to_one(sim, [V], [V, V, V]) == [(0, 0)]


def test_both_length_one_same_type_forced_match():
    assert align_monotone_one_to_one([[0.3]], [P], [P]) == [(0, 0)]
