import logging
import os
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor
import networkx as nx

from common.decorator import timed
from concept_minor_classifier import ConceptMinorClassifier
from repository.concept_repository import ConceptRepository
from repository.image_repository import ImageRepository
from models import ClassificationResult

logging.basicConfig(level=logging.DEBUG)


class ClassificationOrchestrator:
    """
    Orchestrates the classification process using multiprocessing based on available CPU cores.

    This class handles:
    - Dynamic CPU detection
    - Process pool management
    - Work distribution across processes
    - Result aggregation
    """

    def __init__(
        self,
        neo4j_dsn: str,
        neo4j_user: str,
        neo4j_pass: str,
        ged_timeout: float = 15,
        max_workers_override: int = None,
        use_multiprocessing: bool = True,
    ):
        self.neo4j_dsn = neo4j_dsn
        self.neo4j_user = neo4j_user
        self.neo4j_pass = neo4j_pass
        self.ged_timeout = ged_timeout
        self.use_multiprocessing = use_multiprocessing

        # Determine optimal worker count
        self.max_workers = self._determine_worker_count(max_workers_override)

        logging.info(
            f"ClassificationOrchestrator initialized with {self.max_workers} workers"
        )

    def _determine_worker_count(self, override: int = None) -> int:
        """
        Dynamically determine the optimal number of worker processes.

        Args:
            override: Manual override for worker count

        Returns:
            Optimal number of workers
        """
        if override:
            return max(1, override)

        # Get CPU count
        cpu_count = os.cpu_count() or 1

        # Use all available CPUs, but at least 1 and at most 8
        optimal_workers = max(1, min(8, cpu_count))

        logging.info(f"Detected {cpu_count} CPUs, using {optimal_workers} workers")
        return optimal_workers

    def classify_image(
        self,
        image_id: str,
    ) -> List[ClassificationResult]:
        """
        Orchestrate the classification of an image against all concepts.

        Args:
            image_id: ID of the image to classify

        Returns:
            List of classification results
        """
        logging.info(f"Starting classification orchestration for image {image_id}")

        # Get concepts and image data
        concept_repository = ConceptRepository(
            self.neo4j_dsn, self.neo4j_user, self.neo4j_pass
        )
        image_repository = ImageRepository(
            self.neo4j_dsn, self.neo4j_user, self.neo4j_pass
        )

        try:
            concept_ids = concept_repository.get_all_concept_ids()
            image_graph = image_repository.get_image_graph(image_id)

            logging.info(f"Found {len(concept_ids)} concepts to process")

            if self.use_multiprocessing and len(concept_ids) > 1:
                results = self._classify_with_multiprocessing(image_graph, concept_ids)
            else:
                results = self._classify_sequentially(image_graph, concept_ids)

            return self._process_and_sort_results(results, image_id)

        finally:
            concept_repository.close()
            image_repository.close()

    def _classify_with_multiprocessing(
        self,
        image_graph: nx.Graph,
        concept_ids: List[str],
    ) -> List[ClassificationResult]:
        """
        Distribute classification work across multiple processes.

        Args:
            image_graph: The image graph to classify
            concept_ids: List of concept IDs to check against

        Returns:
            List of classification results
        """
        results = []

        # Prepare work packages for each concept
        work_packages = [
            {
                "image_graph": image_graph,
                "concept_id": concept_id,
                "neo4j_dsn": self.neo4j_dsn,
                "neo4j_user": self.neo4j_user,
                "neo4j_pass": self.neo4j_pass,
                "ged_timeout": self.ged_timeout,
            }
            for concept_id in concept_ids
        ]

        logging.info(
            f"Distributing {len(work_packages)} tasks across {self.max_workers} processes"
        )

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_concept = {
                executor.submit(_process_single_concept, package): package["concept_id"]
                for package in work_packages
            }

            # Collect results
            for future in future_to_concept:
                concept_id = future_to_concept[future]
                try:
                    result = future.result(timeout=120)  # 2 minutes per concept
                    results.append(result)
                    logging.debug(f"Completed classification for concept {concept_id}")
                except Exception as e:
                    logging.error(f"Error processing concept {concept_id}: {str(e)}")
                    # Create a failed result
                    results.append(
                        ClassificationResult(
                            concept_id=concept_id,
                            is_minor=False,
                            message=f"Processing error: {str(e)}",
                        )
                    )

        logging.info(
            f"Multiprocessing classification completed. Processed {len(results)} concepts"
        )
        return results

    def _classify_sequentially(
        self,
        image_graph: nx.Graph,
        concept_ids: List[str],
    ) -> List[ClassificationResult]:
        """
        Process concepts sequentially (fallback method).

        Args:
            image_graph: The image graph to classify
            concept_ids: List of concept IDs to check against

        Returns:
            List of classification results
        """
        logging.info("Processing concepts sequentially")
        results = []

        # Create a single classifier instance for sequential processing
        concept_repository = ConceptRepository(
            self.neo4j_dsn, self.neo4j_user, self.neo4j_pass
        )
        image_repository = ImageRepository(
            self.neo4j_dsn, self.neo4j_user, self.neo4j_pass
        )

        classifier = ConceptMinorClassifier(
            concept_repository=concept_repository,
            image_repository=image_repository,
            ged_timeout=self.ged_timeout,
        )

        try:
            for concept_id in concept_ids:
                try:
                    result = classifier.check_single_concept(image_graph, concept_id)
                    results.append(result)
                except Exception as e:
                    logging.error(f"Error processing concept {concept_id}: {str(e)}")
                    results.append(
                        ClassificationResult(
                            concept_id=concept_id,
                            is_minor=False,
                            message=f"Sequential processing error: {str(e)}",
                        )
                    )
        finally:
            concept_repository.close()
            image_repository.close()

        logging.info(
            f"Sequential classification completed. Processed {len(results)} concepts"
        )
        return results

    def _process_and_sort_results(
        self, results: List[ClassificationResult], image_id: str
    ) -> List[ClassificationResult]:
        """
        Filter and sort classification results.

        Args:
            results: Raw classification results
            image_id: ID of the processed image

        Returns:
            Filtered and sorted results
        """
        if not results:
            logging.warning(f"No classification results for image {image_id}")
            return []

        # Filter only successful matches
        filtered_results = [result for result in results if result.is_minor]

        # Sort by similarity (descending) and complexity (descending)
        sorted_results = sorted(
            filtered_results,
            key=lambda x: (x.similarity or 0, x.concept_complexity or 0),
            reverse=True,
        )

        logging.info(
            f"Found {len(sorted_results)} matching concepts out of {len(results)} processed"
        )
        return sorted_results

@timed(label="process_single_concept")
def _process_single_concept(work_package: Dict[str, Any]) -> ClassificationResult:
    """
    Worker function for processing a single concept in a separate process.

    This function is called by each worker process and handles:
    - Creating fresh repository connections
    - Instantiating a classifier
    - Processing the concept
    - Cleaning up resources

    Args:
        work_package: Dictionary containing all necessary parameters

    Returns:
        Classification result for the concept
    """
    try:
        # Extract parameters
        image_graph = work_package["image_graph"]
        concept_id = work_package["concept_id"]
        neo4j_dsn = work_package["neo4j_dsn"]
        neo4j_user = work_package["neo4j_user"]
        neo4j_pass = work_package["neo4j_pass"]
        ged_timeout = work_package["ged_timeout"]

        # Create fresh repository instances for this process
        concept_repository = ConceptRepository(neo4j_dsn, neo4j_user, neo4j_pass)
        image_repository = ImageRepository(neo4j_dsn, neo4j_user, neo4j_pass)

        # Create classifier instance for this worker
        classifier = ConceptMinorClassifier(
            concept_repository=concept_repository,
            image_repository=image_repository,
            ged_timeout=ged_timeout,
        )

        # Process the concept
        result = classifier.check_single_concept(image_graph, concept_id)

        return result

    except Exception as e:
        logging.error(
            f"Worker error processing concept {work_package.get('concept_id', 'unknown')}: {str(e)}"
        )
        return ClassificationResult(
            concept_id=work_package.get("concept_id", "unknown"),
            is_minor=False,
            message=f"Worker process error: {str(e)}",
        )
    finally:
        # Clean up connections
        try:
            if "concept_repository" in locals():
                concept_repository.close()
            if "image_repository" in locals():
                image_repository.close()
        except Exception as e:
            logging.warning(f"Error cleaning up connections: {str(e)}")
