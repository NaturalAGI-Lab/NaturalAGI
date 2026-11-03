import json

import numpy as np
import pytest


def _model(band, roots=True, letter_root=False):
    BandModel = band[0].BandModel
    ids, letters, forms, roles, lo, hi, c = [], [], [], [], [], [], []

    def add(bid, letter, form, role, lo_, hi_):
        ids.append(bid); letters.append(letter); forms.append(form); roles.append(role)
        lo.append(lo_); hi.append(hi_); c.append([(a + b) / 2 for a, b in zip(lo_, hi_)])

    add("A_uA_00", "A", "uA", "leaf", [0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    add("A_la_00", "A", "la", "leaf", [4.0, 4.0, 4.0], [5.0, 5.0, 5.0])
    add("B_uB_00", "B", "uB", "leaf", [9.0, 9.0, 9.0], [10.0, 10.0, 10.0])
    if roots:
        add("A_root", "A", "*" if letter_root else "uA", "root", [0.0, 0.0, 0.0], [5.0, 5.0, 5.0])
    return BandModel("m", "dm1", ["d0", "d1", "d2"], np.ones(3), np.ones(3), ids, letters, forms, roles, lo, hi, c)


def test_inside_the_band_only_the_centre_term_remains(band):
    model = _model(band, roots=False)
    x = np.array([0.5, 0.5, 0.5])                       # exactly the centre of A_uA_00
    assert band[1].score_concepts(x, model)[0] == pytest.approx(0.0)
    y = np.array([1.0, 1.0, 1.0])                       # on the band edge: no violation, centre term only
    expected = 5.0 * 3 * (0.5**2) / (1.0 + 0.5 + 1e-9)
    assert band[1].score_concepts(y, model)[0] == pytest.approx(expected)


def test_outside_the_band_pays_the_violation(band):
    model = _model(band, roots=False)
    x = np.array([2.0, 0.5, 0.5])
    expected = 1.0 + 5.0 * (1.5**2) / (2.0 + 0.5 + 1e-9)
    assert band[1].score_concepts(x, model)[0] == pytest.approx(expected)


def test_letter_is_best_form_tempered_by_its_root(band):
    model = _model(band)
    ranked = band[1].score_letters(np.array([0.5, 0.5, 0.5]), model)
    assert [r.letter for r in ranked] == ["A", "B"]
    best = ranked[0]
    assert best.form == "uA" and best.leaf_id == "A_uA_00"
    assert best.score == pytest.approx(0.7 * best.leaf_score + 0.3 * best.root_score)


def test_letter_wide_root_applies_to_every_form(band):
    model = _model(band, letter_root=True)
    ranked = band[1].score_letters(np.array([4.5, 4.5, 4.5]), model)
    assert ranked[0].form == "la" and ranked[0].root_score is not None


def test_explanation_is_json_serialisable_and_names_the_costly_dims(band):
    model = _model(band, roots=False)
    out = band[1].explain_dims(np.array([3.0, 0.5, 0.5]), model, 0)
    assert out[0]["dim"] == "d0" and out[0]["inside_band"] is False
    json.dumps(out)


def test_select_typical_returns_the_medoid_first(selection):
    rng = np.random.default_rng(0)
    dm = np.abs(rng.normal(1.0, 0.05, size=(10, 83)))
    dm[7] = dm.mean(0)
    picked = selection.select_typical(dm, 1)
    assert picked == [7]
    assert len(selection.select_typical(dm, 3)) == 3 and selection.select_typical(dm, 20) == list(range(10))


def _two_letter_model(band):
    model_cls = band[0].BandModel
    import numpy as np
    D = 4
    lo = np.array([[0.9, 0.9, 0, 0], [0, 0, 0.9, 0.9], [0.9, 0.9, 0, 0], [0, 0, 0.9, 0.9]])
    hi = lo + 0.2; centre = lo + 0.1
    return model_cls("m", "dm2", [f"d{i}" for i in range(D)], np.ones(D), np.ones(D),
                     ["A_leaf", "A_root", "B_leaf", "B_root"], ["A", "A", "B", "B"], ["*", "*", "*", "*"],
                     ["leaf", "root", "leaf", "root"], lo, hi, centre, alpha=1.0, leaf_weight=0.5, root_weight=0.5)


def test_committee_is_the_mean_of_the_maps(band):
    import numpy as np
    _, scorer = band
    m = _two_letter_model(band)
    x1, x2 = np.array([1.0, 1.0, 0.0, 0.0]), np.array([0.5, 0.5, 0.5, 0.5])
    s1 = {s.letter: s.score for s in scorer.score_letters(x1, m)}
    s2 = {s.letter: s.score for s in scorer.score_letters(x2, m)}
    com = {s.letter: s.score for s in scorer.score_letters_committee([x1, x2], m)}
    for L in "AB":
        assert com[L] == pytest.approx((s1[L] + s2[L]) / 2)
    assert scorer.score_letters_committee([x1], m)[0].score == pytest.approx(s1["A"])
