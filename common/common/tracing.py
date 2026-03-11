import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

_propagator = TraceContextTextMapPropagator()

TRACING_ENABLED = os.environ.get("OTEL_TRACING_ENABLED", "true").lower() == "true"

_tracer_cache: dict[str, trace.Tracer] = {}


def init_tracer(service_name: str, experiment_id: str | None = None) -> trace.Tracer:
    if not TRACING_ENABLED:
        return trace.get_tracer(service_name)

    if experiment_id is None:
        experiment_id = os.environ.get("MLFLOW_EXPERIMENT_ID", "0")

    cache_key = f"{service_name}:{experiment_id}"
    if cache_key in _tracer_cache:
        return _tracer_cache[cache_key]

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://mlflow:5000")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{otlp_endpoint}/v1/traces",
                headers={"x-mlflow-experiment-id": experiment_id},
            )
        )
    )
    tracer = provider.get_tracer(service_name)
    _tracer_cache[cache_key] = tracer
    return tracer


def inject_trace_headers() -> list:
    carrier = {}
    _propagator.inject(carrier)
    return [(k, v.encode("utf-8")) for k, v in carrier.items()]


def extract_trace_context(event_headers) -> Optional[object]:
    if not event_headers:
        return None

    if isinstance(event_headers, dict):
        carrier = {}
        for k, v in event_headers.items():
            if isinstance(v, bytes):
                carrier[k] = v.decode("utf-8")
            else:
                carrier[k] = str(v)
    elif isinstance(event_headers, (list, tuple)):
        carrier = {}
        for item in event_headers:
            k, v = item[0], item[1]
            if isinstance(v, bytes):
                carrier[k] = v.decode("utf-8")
            else:
                carrier[k] = str(v)
    else:
        logger.warning(f"Unknown event.headers type: {type(event_headers)}")
        return None

    return _propagator.extract(carrier)
