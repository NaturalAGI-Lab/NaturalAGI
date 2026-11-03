import logging

from neo4j import ManagedTransaction

from logic.direction_map import DM_VERSION, compute_direction_map, dim_schema

from .base_analyzer import BaseAnalyzer

_schema_written = False
# Slant normalisation for the map of the image being analysed; set by the handler from the request
# parameter `deslant` before analyze_graph (one event at a time per worker).
DESLANT = False
NORMALISATION = "bbox"      # "bbox" | "moment" (request parameter `normalisation`)
MOMENT_RANGE = 2.0


class DirectionMapAnalyzer(BaseAnalyzer):
    """Graph-level direction map of the skeleton (see logic/direction_map.py).

    Stored once per image on a dedicated :GraphFeatures node instead of being fanned out to
    every :Point / :Vector like the older graph-level features: 83 extra properties per node
    would dilute the node similarity used by the concept fold and by the GED cost, and would
    multiply the write cost by the number of nodes.

    Runs after merge_close_intersection_points, i.e. on the graph the pipeline persists.
    Opt-in (request parameter `direction_map` or a band mode); a failure here must never break
    the default analysis, so errors are logged and swallowed.
    """

    def analyze(self):
        try:
            return [float(v) for v in compute_direction_map(self.graph, deslant=DESLANT, normalisation=NORMALISATION, moment_range=MOMENT_RANGE)]
        except Exception as e:  # noqa: BLE001
            logging.error(f"Direction map failed: {e}", exc_info=True)
            return None

    def persist(self, mx: ManagedTransaction, session_id: str, image_id: str, result) -> None:
        if result is None:
            return
        global _schema_written
        if not _schema_written:
            names, blocks, grids = dim_schema()
            mx.run(
                """
                MERGE (s:DirectionMapSchema {dm_version: $v})
                ON CREATE SET s.dim_names = $names, s.dim_block = $blocks, s.dim_grid = $grids
                """,
                v=DM_VERSION, names=names, blocks=blocks, grids=grids,
            )
            _schema_written = True
        mx.run(
            """
            OPTIONAL MATCH (p:Point {image_id: $image_id})
            WITH head(collect(p.image_path)) AS image_path
            MERGE (f:GraphFeatures {image_id: $image_id})
            SET f.session_id = $session_id, f.image_path = image_path,
                f.dm = $dm, f.dm_version = $v
            """,
            image_id=image_id, session_id=session_id, dm=result, v=DM_VERSION,
        )
