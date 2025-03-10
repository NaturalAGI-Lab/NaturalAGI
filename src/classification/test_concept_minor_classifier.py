import argparse
import logging
import json
from typing import Dict, Any, List, Optional
import os

from common.params import ClassificationParams
from concept_minor_classifier import ConceptMinorClassifier

logging.basicConfig(level=logging.INFO)


def visualize_mapping(
    step_name: str,
    concept_graph,
    image_graph,
    mcm,
    concept_to_mcm,
    image_to_mcm,
    contractions,
    property_changes,
):
    """
    Simple visualization callback to log the mapping steps.
    This can be replaced with a more sophisticated visualization if needed.
    """
    logging.info(f"Visualization step: {step_name}")
    logging.info(f"Mapping size: {len(concept_to_mcm)}")
    logging.info(f"Concept nodes mapped: {list(concept_to_mcm.keys())}")
    logging.info(f"Image nodes mapped: {list(image_to_mcm.keys())}")


def classify_image(
    image_id: str,
    neo4j_dsn: str,
    neo4j_user: str,
    neo4j_pass: str,
    params_json: Optional[str] = None,
    visualize: bool = False,
) -> List[Dict[str, Any]]:
    """
    Classify an image using the ConceptMinorClassifier.

    Args:
        image_id: The ID of the image to classify
        neo4j_dsn: Neo4j database DSN
        neo4j_user: Neo4j username
        neo4j_pass: Neo4j password
        params_json: Optional JSON string with classification parameters
        visualize: Whether to use the visualization callback

    Returns:
        List of classification results, sorted by activation level
    """
    # Parse classification parameters
    if params_json:
        params_dict = json.loads(params_json)
        classification_params = ClassificationParams(**params_dict)
    else:
        classification_params = ClassificationParams()

    # Create the classifier
    classifier = ConceptMinorClassifier(
        neo4j_dsn=neo4j_dsn,
        neo4j_user=neo4j_user,
        neo4j_pass=neo4j_pass,
        use_multithreading=True,
    )

    try:
        # Classify the image
        visualization_callback = visualize_mapping if visualize else None
        results = classifier.classify(
            image_id=image_id,
            classification_params=classification_params,
            visualization_callback=visualization_callback,
        )

        # Print results
        logging.info(f"Classification results for image {image_id}:")

        if results:
            for i, result in enumerate(results):
                logging.info(
                    f"  {i+1}. Concept: {result['concept_id']}, "
                    f"Activation: {result.get('activation_level', 0):.4f}, "
                    f"Complexity: {result.get('concept_complexity', 0)}, "
                    f"Matched: {result.get('mapping_size', 0)}/{result.get('concept_size', 0)}"
                )
            logging.info(
                f"Found {len(results)} concept(s) that are minors of the image."
            )
        else:
            logging.info("No concepts found that are minors of the image.")

        return results

    finally:
        classifier.close()


def main():
    parser = argparse.ArgumentParser(
        description="Classify an image using concept minors"
    )
    parser.add_argument("--image_id", required=True, help="ID of the image to classify")
    parser.add_argument(
        "--neo4j_dsn",
        default=os.environ.get("NEO4J_DSN", "bolt://localhost:7687"),
        help="Neo4j connection string",
    )
    parser.add_argument(
        "--neo4j_user",
        default=os.environ.get("NEO4J_USER", "neo4j"),
        help="Neo4j username",
    )
    parser.add_argument(
        "--neo4j_pass",
        default=os.environ.get("NEO4J_PASS", "password"),
        help="Neo4j password",
    )
    parser.add_argument("--params", help="JSON string with classification parameters")
    parser.add_argument(
        "--visualize", action="store_true", help="Enable visualization callback"
    )

    args = parser.parse_args()

    results = classify_image(
        image_id=args.image_id,
        neo4j_dsn=args.neo4j_dsn,
        neo4j_user=args.neo4j_user,
        neo4j_pass=args.neo4j_pass,
        params_json=args.params,
        visualize=args.visualize,
    )

    # Print final results in JSON format
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
