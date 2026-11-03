import numpy as np


def test_wide_letter_gets_more_originals(selection):
    rng = np.random.default_rng(0)
    D = 141
    tight = np.abs(rng.normal(1.0, 0.02, (40, D)))                       # one writing mode
    wide = np.vstack([np.abs(rng.normal(c, 0.02, (10, D))) for c in (0.5, 1.0, 2.0, 4.0)])   # four modes
    plan = selection.adaptive_budget({"O": tight, "G": wide}, total=12, k_min=2, k_max=10)
    assert sum(k for k, _ in plan.values()) <= 12
    assert plan["G"][0] > plan["O"][0]
    assert len(plan["G"][1]) == plan["G"][0] and len(set(plan["G"][1])) == plan["G"][0]


def test_budget_is_spent_and_indices_are_valid(selection):
    rng = np.random.default_rng(1)
    pools = {L: np.abs(rng.normal(1.0, 0.3 * (i + 1), (30, 141))) for i, L in enumerate("ABC")}
    plan = selection.adaptive_budget(pools, total=15, k_min=2, k_max=12)
    assert 12 <= sum(k for k, _ in plan.values()) <= 15
    for L, (k, idx) in plan.items():
        assert all(0 <= i < 30 for i in idx)


def test_stratified_selection_keeps_the_minority_structure(selection):
    rng = np.random.default_rng(2)
    D = 141
    major = np.abs(rng.normal(1.0, 0.05, (45, D))); major[:, 78:81] = [2, 0, 0]     # 75 %: two endpoints, no junction
    minor = np.abs(rng.normal(1.0, 0.05, (15, D))); minor[:, 78:81] = [3, 1, 0]     # 25 %: a stem attached
    pool = np.vstack([major, minor])
    picked = selection.select_stratified(pool, 4)
    assert len(picked) == len(set(picked)) == 4
    assert sum(i >= 45 for i in picked) >= 1                    # the minority structure is represented
    plan = selection.adaptive_budget({"Y": pool, "V": major}, total=8, k_min=2, k_max=6, stratify=True)
    assert all(0 <= i < len(p) for (k, idx), p in zip(plan.values(), (pool, major)) for i in idx)
