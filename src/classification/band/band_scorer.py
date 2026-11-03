"""Scores an image's direction map against a band model. Lower is better.

score(x, concept) = sum_d w_d * outside_d / scale_d  +  alpha * sum_d w_d * (x_d - c_d)^2 / (|x_d| + |c_d|)
where outside_d is how far x_d lies beyond the concept's band [lo_d, hi_d] (0 inside it).
A glyph form is scored by its best leaf, tempered by the form's root; a letter by its best form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from .band_model import BandModel


@dataclass
class LetterScore:
    letter: str
    form: str
    leaf_id: str
    leaf_score: float
    root_score: Optional[float]
    score: float


def score_concepts(x: np.ndarray, model: BandModel) -> np.ndarray:
    x = np.asarray(x, float)
    outside = np.maximum(model.lo - x, 0.0) + np.maximum(x - model.hi, 0.0)
    violation = (outside * model.w_over_scale).sum(1)
    num = (x - model.centre) ** 2
    den = np.abs(x) + np.abs(model.centre) + 1e-9
    return violation + model.alpha * (num / den * model.weights).sum(1)


def score_letters(x: np.ndarray, model: BandModel) -> List[LetterScore]:
    """One entry per letter, best first."""
    return sorted(_letter_totals(x, model).values(), key=lambda s: s.score)


def score_letters_committee(xs: List[np.ndarray], model: BandModel) -> List[LetterScore]:
    """Several direction maps of the same image (a committee of skeletons): a letter's score is the
    mean of its scores over the maps; the leaf and form come from the first map."""
    if len(xs) == 1:
        return score_letters(xs[0], model)
    totals = [_letter_totals(x, model) for x in xs]
    out = []
    for letter, first in totals[0].items():
        others = [t[letter].score for t in totals[1:] if letter in t]
        mean = float(np.mean([first.score] + others))
        out.append(LetterScore(first.letter, first.form, first.leaf_id, first.leaf_score, first.root_score, mean))
    return sorted(out, key=lambda s: s.score)


def _letter_totals(x: np.ndarray, model: BandModel) -> Dict[str, LetterScore]:
    scores = score_concepts(x, model)
    best_leaf: Dict[tuple, int] = {}
    root_of: Dict[tuple, int] = {}
    for i, (letter, form, role) in enumerate(zip(model.letters, model.forms, model.roles)):
        key = (letter, form)
        if role == "root":
            root_of[key] = i
        elif key not in best_leaf or scores[i] < scores[best_leaf[key]]:
            best_leaf[key] = i
    per_letter: Dict[str, LetterScore] = {}
    for (letter, form), i in best_leaf.items():
        # a root may belong to one glyph form or, with form "*", to the whole letter
        root_idx = root_of.get((letter, form), root_of.get((letter, "*")))
        root = float(scores[root_idx]) if root_idx is not None else None
        leaf = float(scores[i])
        total = model.leaf_weight * leaf + model.root_weight * root if root is not None else leaf
        if letter not in per_letter or total < per_letter[letter].score:
            per_letter[letter] = LetterScore(letter, form, model.band_ids[i], leaf, root, total)
    return per_letter


def explain_dims(x: np.ndarray, model: BandModel, concept_index: int, top: int = 5) -> List[dict]:
    """The dimensions that cost this concept the most, in words a person can check."""
    x = np.asarray(x, float)
    lo, hi, c = model.lo[concept_index], model.hi[concept_index], model.centre[concept_index]
    outside = (np.maximum(lo - x, 0.0) + np.maximum(x - hi, 0.0)) * model.w_over_scale
    centre = model.alpha * (x - c) ** 2 / (np.abs(x) + np.abs(c) + 1e-9) * model.weights
    cost = outside + centre
    order = np.argsort(-cost)[:top]
    return [
        {
            "dim": model.dim_names[i],
            "value": round(float(x[i]), 4),
            "lo": round(float(lo[i]), 4),
            "hi": round(float(hi[i]), 4),
            "inside_band": bool(lo[i] <= x[i] <= hi[i]),
            "cost": round(float(cost[i]), 5),
        }
        for i in order
        if cost[i] > 0
    ]
