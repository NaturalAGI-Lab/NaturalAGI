import networkx as nx

from src.synced_graph_algorithm import SyncedGraphMinorFinder
from src.property_handlers.property_handlers import PropertyProcessor
from src.node_similarity_calculator import NodeSimilarityCalculator
from src.critical_point_preprocessor import CriticalPointPreprocessor


def _finder():
    return SyncedGraphMinorFinder(
        prop_manager=PropertyProcessor(),
        similarity_calculator=NodeSimilarityCalculator(),
        critical_point_preprocessor=CriticalPointPreprocessor(),
    )


def _hv(x, y):
    return {"labels": ["HorizontalVector", "Vector"], "normalized_x": x, "normalized_y": y}


def _vv(x, y):
    return {"labels": ["VerticalVector", "Vector"], "normalized_x": x, "normalized_y": y}


def _pt(x, y):
    return {"labels": ["Point"], "normalized_x": x, "normalized_y": y}


def test_image_arc_has_extra_node_surplus_dropped_keeps_min_in_order():
    # Concept: Start - HV(1) - End.  Image: Start - HV(11) - P(12) - VV(13) - End.
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, **_hv(0.5, 0.0))
    G_c.add_node(2, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=0.0)
    G_c.add_edges_from([(0, 1), (1, 2)])

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, **_hv(0.5, 0.05))
    G_i.add_node(12, **_pt(0.6, 0.3))
    G_i.add_node(13, **_vv(0.6, 0.6))
    G_i.add_node(14, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=0.0)
    G_i.add_edges_from([(10, 11), (11, 12), (12, 13), (13, 14)])

    result = nx.Graph()
    finder = _finder()
    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=2, path1=[0, 1, 2],
        start2=10, end2=14, path2=[10, 11, 12, 13, 14],
    )

    # Exactly one intermediate (min(1,3)) kept, plus the two anchors.
    assert set(result.nodes) == {0, 1, 2}
    # Intermediate keyed by the CONCEPT node id (1), not any image id (11/12/13).
    assert 1 in result.nodes
    assert not ({11, 12, 13} & set(result.nodes))
    # Order preserved: start - intermediate - end.
    assert list(nx.all_simple_paths(result, 0, 2)) == [[0, 1, 2]]
    # Properties merged from concept node 1 and image node 11 (HV ↔ HV).
    assert "Vector" in result.nodes[1]["labels"]


def test_concept_longer_than_image_keeps_concept_ids_drops_concept_surplus():
    # Concept: Start - HV - P - VV - P(surplus) - End  (4 intermediates).
    # Image:   Start - HV - P - VV - End                (3 intermediates).
    # Only monotone same-type triple is the first three concept intermediates.
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, **_hv(0.2, 0.0))
    G_c.add_node(2, **_pt(0.4, 0.1))
    G_c.add_node(3, **_vv(0.5, 0.3))
    G_c.add_node(4, **_pt(0.55, 0.5))
    G_c.add_node(5, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_c.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, **_hv(0.2, 0.02))
    G_i.add_node(12, **_pt(0.4, 0.12))
    G_i.add_node(13, **_vv(0.5, 0.32))
    G_i.add_node(14, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_i.add_edges_from([(10, 11), (11, 12), (12, 13), (13, 14)])

    result = nx.Graph()
    finder = _finder()
    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=5, path1=[0, 1, 2, 3, 4, 5],
        start2=10, end2=14, path2=[10, 11, 12, 13, 14],
    )

    # min(4,3)=3 intermediates kept, all keyed by concept ids; surplus concept 4 dropped.
    assert set(result.nodes) == {0, 1, 2, 3, 5}
    assert 4 not in result.nodes
    assert not (set(range(10, 15)) & set(result.nodes))
    assert list(nx.all_simple_paths(result, 0, 5)) == [[0, 1, 2, 3, 5]]


def test_intermediate_already_in_result_is_not_re_merged():
    # A concept intermediate (1) that overlapping segments revisit must not be
    # re-merged once present: process_properties is the merge op, and recomputing
    # it only to discard the result (the "already exists" path) emits a spurious
    # merge/correspondence. Anchors already guard this; the intermediate must too.
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, **_hv(0.5, 0.0))
    G_c.add_node(2, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=0.0)
    G_c.add_edges_from([(0, 1), (1, 2)])

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, **_hv(0.5, 0.05))
    G_i.add_node(12, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=0.0)
    G_i.add_edges_from([(10, 11), (11, 12)])

    finder = _finder()
    # Concept node 1 was already merged by a prior overlapping segment.
    result = nx.Graph()
    result.add_node(1, **_hv(0.5, 0.0))

    g_args = []
    original = finder.prop_manager.process_properties

    def _spy(mcm_props, g_props, h_props):
        g_args.append(g_props)
        return original(mcm_props, g_props, h_props)

    finder.prop_manager.process_properties = _spy

    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=2, path1=[0, 1, 2],
        start2=10, end2=12, path2=[10, 11, 12],
    )

    # The already-present intermediate (concept node 1) must not be re-merged.
    assert sum(1 for g in g_args if g is G_c.nodes[1]) == 0
    # Only the two fresh anchors get merged.
    assert g_args == [G_c.nodes[0], G_c.nodes[2]]
    assert set(result.nodes) == {0, 1, 2}


def test_adjacent_anchors_no_intermediates_direct_edge():
    G_c = nx.Graph()
    G_c.add_node(0, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_c.add_node(1, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_c.add_edge(0, 1)

    G_i = nx.Graph()
    G_i.add_node(10, labels=["StartPoint", "Point"], normalized_x=0.0, normalized_y=0.0)
    G_i.add_node(11, labels=["EndPoint", "Point"], normalized_x=1.0, normalized_y=1.0)
    G_i.add_edge(10, 11)

    result = nx.Graph()
    finder = _finder()
    finder._create_reduced_path_in_result(
        result_graph=result, graph1=G_c, graph2=G_i,
        start1=0, end1=1, path1=[0, 1],
        start2=10, end2=11, path2=[10, 11],
    )

    assert set(result.nodes) == {0, 1}
    assert result.has_edge(0, 1)
