from typing import Any, Dict, List, Optional, Sequence, Tuple

import networkx as nx
import pytest

from common.critical_point import CriticalPointType
from src.logic.synced_traversal_generator import SyncedTraversalGenerator


Branch = Tuple[Any, Any]
MatchedBranch = Tuple[Any, Any, Any, Any]


def _add_node(
    graph: nx.Graph,
    node_id: Any,
    labels: Optional[Sequence[CriticalPointType]],
    x: float,
    y: float,
) -> None:
    label_values: List[str] = []
    if labels is not None:
        for label in labels:
            label_values.append(label.value)
    graph.add_node(node_id, labels=label_values, normalized_x=x, normalized_y=y)


def _matched_by_concept_exit(
    matches: List[MatchedBranch],
) -> Dict[Any, Tuple[Any, Any, Any]]:
    matched_by_exit: Dict[Any, Tuple[Any, Any, Any]] = {}
    for dest_c, dest_i, exit_c, exit_i in matches:
        matched_by_exit[exit_c] = (dest_c, dest_i, exit_i)
    return matched_by_exit


def test_match_branches_uses_destination_before_exit_for_degree_four_near_tie() -> None:
    graph_c = nx.Graph()
    graph_i = nx.Graph()

    concept_nodes = {
        "c6dbaeb2": (0.17, -0.33, None),
        -8298768: (0.27, -0.63, CriticalPointType.CORNER_POINT),
        "bab44759": (-0.23, -0.13, None),
        -6626715: (-0.03, -0.73, CriticalPointType.CORNER_POINT),
        "6561da65": (0.20, 0.17, None),
        -8867513: (0.30, 0.37, CriticalPointType.CORNER_POINT),
        "4121c8e7": (-0.10, 0.33, None),
        -2143561: (-0.20, 0.63, CriticalPointType.CORNER_POINT),
    }
    image_nodes = {
        "b5aa6942": (-0.00, -0.40, None),
        -3026437: (-0.00, -0.70, CriticalPointType.CORNER_POINT),
        "acb19d82": (0.30, -0.20, None),
        -2355132: (0.70, -0.30, CriticalPointType.CORNER_POINT),
        "73cc7d82": (-0.40, 0.10, None),
        -1858804: (-0.70, 0.30, CriticalPointType.CORNER_POINT),
        "0e6c78e2": (0.00, 0.30, None),
        56701781: (0.10, 0.60, CriticalPointType.CORNER_POINT),
    }

    for node_id, (x, y, label) in concept_nodes.items():
        labels = [label] if label is not None else None
        _add_node(graph_c, node_id, labels, x, y)
    for node_id, (x, y, label) in image_nodes.items():
        labels = [label] if label is not None else None
        _add_node(graph_i, node_id, labels, x, y)

    branches_c: List[Branch] = [
        ("c6dbaeb2", -8298768),
        ("bab44759", -6626715),
        ("6561da65", -8867513),
        ("4121c8e7", -2143561),
    ]
    branches_i: List[Branch] = [
        ("b5aa6942", -3026437),
        ("acb19d82", -2355132),
        ("73cc7d82", -1858804),
        ("0e6c78e2", 56701781),
    ]

    generator = SyncedTraversalGenerator({CriticalPointType.CORNER_POINT})

    matches = generator._match_branches(graph_c, graph_i, branches_c, branches_i)

    matched_by_exit = _matched_by_concept_exit(matches)
    assert matched_by_exit["c6dbaeb2"] == (-8298768, -2355132, "acb19d82")
    assert matched_by_exit["bab44759"] == (-6626715, -3026437, "b5aa6942")


def test_match_branches_uses_exit_geometry_for_parallel_arcs_to_same_destination() -> None:
    graph_c = nx.Graph()
    graph_i = nx.Graph()

    _add_node(graph_c, "c_upper_exit", None, 0.20, 0.30)
    _add_node(graph_c, "c_lower_exit", None, 0.20, -0.30)
    _add_node(
        graph_c,
        "c_loop_corner",
        [CriticalPointType.CORNER_POINT],
        0.70,
        0.00,
    )
    _add_node(graph_i, "i_lower_exit", None, 0.18, -0.28)
    _add_node(graph_i, "i_upper_exit", None, 0.22, 0.31)
    _add_node(
        graph_i,
        "i_loop_corner",
        [CriticalPointType.CORNER_POINT],
        0.70,
        0.00,
    )

    branches_c: List[Branch] = [
        ("c_upper_exit", "c_loop_corner"),
        ("c_lower_exit", "c_loop_corner"),
    ]
    branches_i: List[Branch] = [
        ("i_lower_exit", "i_loop_corner"),
        ("i_upper_exit", "i_loop_corner"),
    ]
    generator = SyncedTraversalGenerator({CriticalPointType.CORNER_POINT})

    matches = generator._match_branches(graph_c, graph_i, branches_c, branches_i)

    matched_by_exit = _matched_by_concept_exit(matches)
    assert matched_by_exit["c_upper_exit"] == (
        "c_loop_corner",
        "i_loop_corner",
        "i_upper_exit",
    )
    assert matched_by_exit["c_lower_exit"] == (
        "c_loop_corner",
        "i_loop_corner",
        "i_lower_exit",
    )


def test_revisited_intersection_does_not_reuse_consumed_image_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_c = nx.Graph()
    graph_i = nx.Graph()

    start_labels = [
        CriticalPointType.START_POINT,
        CriticalPointType.INTERSECTION_POINT,
    ]
    corner_labels = [CriticalPointType.CORNER_POINT]

    _add_node(graph_c, "c_start", start_labels, 0.00, 0.00)
    _add_node(graph_c, "c_exit_a", None, 0.10, 0.00)
    _add_node(graph_c, "c_return_a", None, -0.10, 0.00)
    _add_node(graph_c, "c_dest_a", corner_labels, 0.40, 0.00)
    _add_node(graph_c, "c_exit_b", None, 0.00, 0.20)
    _add_node(graph_c, "c_dest_b", corner_labels, 0.00, 0.50)
    graph_c.add_edges_from(
        [
            ("c_start", "c_exit_a"),
            ("c_exit_a", "c_dest_a"),
            ("c_start", "c_return_a"),
            ("c_return_a", "c_dest_a"),
            ("c_start", "c_exit_b"),
            ("c_exit_b", "c_dest_b"),
        ]
    )

    _add_node(graph_i, "i_start", start_labels, 0.00, 0.00)
    _add_node(graph_i, "i_exit_a", None, 0.10, 0.00)
    _add_node(graph_i, "i_return_a", None, -0.10, 0.00)
    _add_node(graph_i, "i_dest_a", corner_labels, 0.40, 0.00)
    graph_i.add_edges_from(
        [
            ("i_start", "i_exit_a"),
            ("i_exit_a", "i_dest_a"),
            ("i_start", "i_return_a"),
            ("i_return_a", "i_dest_a"),
        ]
    )

    generator = SyncedTraversalGenerator({CriticalPointType.CORNER_POINT})
    call_count = 0

    def fake_match_branches(
        G_c: nx.Graph,
        G_i: nx.Graph,
        branches_c: List[Branch],
        branches_i: List[Branch],
    ) -> List[MatchedBranch]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [("c_dest_a", "i_dest_a", "c_exit_a", "i_exit_a")]
        if call_count == 2:
            return [("c_dest_b", "i_dest_a", "c_exit_b", "i_exit_a")]
        return []

    monkeypatch.setattr(generator, "_match_branches", fake_match_branches)

    traversal = generator.generate_synced_traversal(graph_c, graph_i)

    duplicate_claim_paths: List[List[Tuple[Any, Any]]] = []
    for path in traversal:
        if ("c_dest_b", "i_dest_a") in path:
            duplicate_claim_paths.append(path)

    assert call_count >= 2
    assert duplicate_claim_paths == []
