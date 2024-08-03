import json
import traceback

from pydantic_settings import BaseSettings

from contour_analysis_repository import ContourAnalysisRepository

HANDLER_NAME = "Contour analysis"


class Settings(BaseSettings):
    """Settings"""

    neo4j_dsn: str
    neo4j_user: str
    neo4j_pass: str
    next_nuclio: str = ""


def init_context(context):
    """Initializes nuclio context

    Args:
        context ([type]): Nuclio context
    """
    context.logger.debug_with(
        f"Exporter initializing with:\n{Settings().model_dump()}", handler=HANDLER_NAME
    )

    contour_analysis_repository = ContourAnalysisRepository(
        Settings().neo4j_dsn, Settings().neo4j_user, Settings().neo4j_pass
    )
    setattr(
        context.user_data, "contour_analysis_repository", contour_analysis_repository
    )
    setattr(context.user_data, "next_nuclio", Settings().next_nuclio)


def kafka_handler(context, event):
    """Handles Kafka messages"""
    try:

        input_data = json.loads(event.body)

        context.logger.debug_with(
            f"Input data: {input_data}", handler=HANDLER_NAME
        )

        try:
            context.user_data.contour_analysis_repository.analyze_contour(input_data)
        except Exception as e:
            context.logger.error_with(f"Error analyzing contour:\n {e}", handler=HANDLER_NAME)
            traceback.print_exc()

    except Exception as e:
        context.logger.error_with(f"Error:\n {e}", handler=HANDLER_NAME)
        traceback.print_exc()


def handler(context, event):
    """Nuclio handler"""

    context.logger.info_with(
        f"Got request: {event.trigger.kind} {event.content_type}", handler=HANDLER_NAME
    )
    context.logger.info_with(
        f"{HANDLER_NAME}: Input Headers: {event.headers}", handler=HANDLER_NAME
    )

    if event.trigger.kind == "kafka-cluster":
        kafka_handler(context, event)

    else:
        context.logger.error_with(
            "Unknown trigger. Expected kafka or http", handler=HANDLER_NAME
        )
