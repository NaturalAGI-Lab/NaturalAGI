from neo4j import Driver, ManagedTransaction

from service.graph_analysis.analyzers.base_analyzer import BaseAnalyzer


class AnalysisResultPersistenceService:
    def __init__(self, driver: Driver):
        self.driver = driver

    def save_all_results(
        self,
        analyzer_results: list[tuple[BaseAnalyzer, any]],
        image_id: str,
        session_id: str,
    ) -> None:
        with self.driver.session() as session:
            session.execute_write(self._save_all, analyzer_results, image_id, session_id)

    def _save_all(
        self,
        tx: ManagedTransaction,
        analyzer_results: list[tuple[BaseAnalyzer, any]],
        image_id: str,
        session_id: str,
    ) -> None:
        for analyzer, result in analyzer_results:
            analyzer.persist(tx, session_id, image_id, result)
