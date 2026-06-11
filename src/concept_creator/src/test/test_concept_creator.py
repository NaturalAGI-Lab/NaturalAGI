"""
Unit tests for SyncedGraphMinorFinder and concept formation.

Run directly with the project venv:
    cd src/concept_creator
    PYTHONPATH=.:<repo>/common python src/test/test_concept_creator.py
"""
import logging
import sys
import unittest
from pathlib import Path

_TEST_DIR = Path(__file__).parent
_SERVICE_DIR = _TEST_DIR.parent.parent
sys.path.insert(0, str(_SERVICE_DIR))

from src.critical_point_preprocessor import CriticalPointPreprocessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.property_handlers import PropertyProcessor
from src.synced_graph_algorithm import SyncedGraphMinorFinder

from probes.instrumentation import FormationRecorder, attach_instrumentation
from probes.probe_concept_formation import (
    _build_offline_service,
    _determine_start_point,
    _run_offline,
    _load_graphs_from_dir,
    _range_width,
)
from probes.test_probe_selfcheck import _ensure_sample_data

logging.basicConfig(level=logging.WARNING)


def _run_offline_formation(samples_dir: Path):
    image_graphs = _load_graphs_from_dir(samples_dir)
    service = _build_offline_service()
    recorder = FormationRecorder(out_path=None, mismatch_threshold=0.35)
    step_ref = attach_instrumentation(service, recorder)
    step_ref[0] = 0
    image_graphs = _determine_start_point(image_graphs, logging.getLogger("test"))
    step_ref[0] = 1
    result = _run_offline(service, image_graphs, steps=None, step_ref=step_ref)
    return recorder, result


def _mean_xy_width(graph) -> float:
    widths = [
        (_range_width(d.get("normalized_x")) + _range_width(d.get("normalized_y"))) / 2
        for _, d in graph.nodes(data=True)
    ]
    return sum(widths) / len(widths) if widths else 0.0


class TestConceptFormation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean_dir, cls.flipped_dir = _ensure_sample_data()

    def test_clean_set_merges_without_mismatches(self):
        recorder, result = _run_offline_formation(self.clean_dir)
        mismatches = sum(1 for e in recorder.events if e.get("mismatch"))
        self.assertEqual(mismatches, 0)
        self.assertGreater(len(result.concept_graph.nodes), 0)
        self.assertLess(_mean_xy_width(result.concept_graph), 0.6)

    def test_flipped_sample_does_not_corrupt_concept(self):
        recorder, result = _run_offline_formation(self.flipped_dir)
        mismatches = sum(1 for e in recorder.events if e.get("mismatch"))
        self.assertEqual(
            mismatches, 0,
            "spatial guard must reject inconsistent pairs before merging",
        )
        self.assertLess(_mean_xy_width(result.concept_graph), 0.6)


class TestAlignPaths(unittest.TestCase):
    def setUp(self):
        self.finder = SyncedGraphMinorFinder(
            prop_manager=PropertyProcessor(),
            similarity_calculator=NodeSimilarityCalculator(),
            critical_point_preprocessor=CriticalPointPreprocessor(),
            logger=logging.getLogger("test_align"),
        )

    def test_alignment_is_one_to_one(self):
        sim = [
            [0.1, 0.2, 0.9],
            [0.1, 0.3, 0.8],
        ]
        match = self.finder._align_paths(sim)
        used = [j for j in match if j is not None]
        self.assertEqual(len(used), len(set(used)))

    def test_alignment_is_monotone(self):
        sim = [
            [0.1, 0.2, 0.9],
            [0.8, 0.1, 0.1],
        ]
        match = self.finder._align_paths(sim)
        used = [j for j in match if j is not None]
        self.assertEqual(used, sorted(used))

    def test_diagonal_preferred_for_similar_paths(self):
        sim = [
            [0.9, 0.2, 0.1],
            [0.2, 0.9, 0.2],
            [0.1, 0.2, 0.9],
        ]
        self.assertEqual(self.finder._align_paths(sim), [0, 1, 2])

    def test_empty_matrix(self):
        self.assertEqual(self.finder._align_paths([]), [])


if __name__ == "__main__":
    unittest.main()
