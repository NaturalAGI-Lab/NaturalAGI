"""
Probe for Bug A prerequisite: what does contour analysis store as Neo4j `n.id`?

This does not connect to Neo4j. It follows the in-memory source path:

1. skeletonization.converter.Converter creates NetworkX nodes keyed by
   hash(coordinates), and each node data dict initially has an `id` UUID string.
2. skeletonization.graph_serializer.GraphSerializer uses nx.node_link_data().
   NetworkX node-link format reserves the "id" field for the node key, so the
   node attribute UUID is overwritten/dropped in the serialized payload.
3. contour_analysis GraphDeserializer restores nodes keyed by hash(coordinates)
   with no node-data `id` attribute.
4. contour_analysis.service.graph_persistance_service.GraphPersistenceService
   builds point payloads as {"id": node_id, ..., **data}. Because data has no
   "id" after node-link round-trip, persisted Point.n.id is the node key.
5. concept_creator Neo4j extraction then uses `RETURN n.id as node_id`.

Therefore normal skeletonized image graph node IDs are coordinate-hash integers,
not per-image sequential integers and not UUIDs. Equal coordinates across images
can reuse IDs.
"""

import sys
from pathlib import Path

import numpy as np
import networkx as nx

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src" / "skeletonization"))

from converter import Converter  # noqa: E402


graph = Converter.convert_simplified_network_to_networkx(
    [[np.array([0.0, 0.0]), np.array([1.0, 1.0])]]
)

original_node_key, original_node_data = next(iter(graph.nodes(data=True)))

serialized = nx.node_link_data(graph)
roundtripped = nx.node_link_graph(serialized)

node_key, node_data = next(iter(roundtripped.nodes(data=True)))
persisted_payload = {
    "id": node_key,
    "image_id": "image-a",
    "session_id": "session-a",
    **node_data,
}

print("=== Bug A ID-source probe ===")
print(f"Original converter node key: {original_node_key!r} ({type(original_node_key).__name__})")
print(f"Original converter node data id: {original_node_data['id']!r}")
print(f"node_link serialized first node: {serialized['nodes'][0]!r}")
print(f"Round-tripped contour node key: {node_key!r} ({type(node_key).__name__})")
print(f"Round-tripped contour node data has id attr: {'id' in node_data}")
print(f"Persisted Point.n.id after {{'id': node_key, **data}}: {persisted_payload['id']!r}")
print(f"Edge/vector ids survive as UUIDs: {[data['id'] for _, _, data in roundtripped.edges(data=True)]}")
