from neo4j import GraphDatabase, ManagedTransaction

from service.graph_analysis.analyzers.base_analyzer import BaseAnalyzer


class AnalysisResultPersistenceService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def save_analysis_result(self, analyzer: BaseAnalyzer, result: any, image_id: str, session_id: str) -> None:
        with self.driver.session() as session:
            session.write_transaction(self._save_result, analyzer, result, image_id, session_id)

    def _save_result(self, tx: ManagedTransaction, analyzer: BaseAnalyzer, result: any, image_id: str, session_id: str) -> None:
        analyzer.persist(tx, session_id, image_id, result)

    def close(self):
        self.driver.close()