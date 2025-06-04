from typing import Any
from neo4j import GraphDatabase, ManagedTransaction
from .visitor import Visitor

class VisitorResultPersistenceService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def save_visitor_result(self, visitor: Visitor, result: Any, image_id: str, session_id: str) -> None:
        with self.driver.session() as session:
            session.write_transaction(self._save_result, visitor, result, image_id, session_id)

    def _save_result(self, tx: ManagedTransaction, visitor: Visitor, result: Any, image_id: str, session_id: str) -> None:
        visitor.save_result(tx, image_id, session_id, result)

    def close(self):
        self.driver.close()