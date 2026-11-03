"""Neo4j access for band concepts.

Band nodes deliberately carry none of `image_id`, `session_id`, `samples` or `concept_id`:
the existing clean-up queries delete by those properties without a label filter, and
`concept_id` is how the structural classifier discovers concepts.
"""
from __future__ import annotations

import os
from typing import Dict, List

import numpy as np
from neo4j import GraphDatabase


class BandRepository:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def read_schema(self) -> dict:
        with self.driver.session() as session:
            record = session.run(
                "MATCH (s:DirectionMapSchema) RETURN s.dm_version AS dm_version, s.dim_names AS dim_names, "
                "s.dim_block AS dim_block, s.dim_grid AS dim_grid ORDER BY s.dm_version DESC LIMIT 1"
            ).single()
        if record is None:
            raise ValueError("No :DirectionMapSchema in Neo4j: ingest images with direction_map enabled first")
        return dict(record)

    def read_session_features(self, session_id: str, dm_version: str) -> Dict[str, np.ndarray]:
        """{file stem: direction map} for one ingest session."""
        with self.driver.session() as session:
            rows = session.run(
                "MATCH (f:GraphFeatures {session_id: $sid}) WHERE f.dm_version = $v "
                "RETURN f.image_path AS path, f.dm AS dm",
                sid=session_id, v=dm_version,
            ).data()
        return {
            os.path.splitext(os.path.basename(r["path"]))[0]: np.array(r["dm"], float)
            for r in rows
            if r["path"] and r["dm"]
        }

    def read_session_shapes(self, session_id: str) -> Dict[str, tuple]:
        """{file stem: (shape points, tangents)} (flat lists) for the images that carry them."""
        with self.driver.session() as session:
            rows = session.run(
                "MATCH (f:GraphFeatures {session_id: $sid}) WHERE f.sp IS NOT NULL "
                "RETURN f.image_path AS path, f.sp AS sp, f.st AS st",
                sid=session_id,
            ).data()
        return {os.path.splitext(os.path.basename(r["path"]))[0]: (r["sp"], r["st"]) for r in rows if r["path"]}

    def write_model(self, model: dict, concepts: List[dict]) -> None:
        def work(tx):
            tx.run(
                "MATCH (m:BandModel {model_id: $id}) OPTIONAL MATCH (m)-[:HAS_CONCEPT]->(c) DETACH DELETE c, m",
                id=model["model_id"],
            )
            tx.run("CREATE (m:BandModel) SET m = $props", props=model)
            tx.run(
                "MATCH (m:BandModel {model_id: $id}) UNWIND $rows AS row "
                "CREATE (c:BandConcept) SET c = row CREATE (m)-[:HAS_CONCEPT]->(c)",
                id=model["model_id"], rows=concepts,
            )
            tx.run(
                "MATCH (r:BandConcept {model_id: $id, role: 'root'}), (l:BandConcept {model_id: $id, role: 'leaf'}) "
                "WHERE r.letter = l.letter AND (r.form = l.form OR r.form = '*') CREATE (r)-[:GENERALISES]->(l)",
                id=model["model_id"],
            )

        with self.driver.session() as session:
            session.execute_write(work)
