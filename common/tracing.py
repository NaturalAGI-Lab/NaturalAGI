import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

_propagator = TraceContextTextMapPropagator()

TRACING_ENABLED = os.environ.get("OTEL_TRACING_ENABLED", "true").lower() == "true"


def init_tracer(service_name: str, otlp_endpoint: str = "http://jaeger:4317") -> trace.Tracer:
    if not TRACING_ENABLED:
        return trace.get_tracer(service_name)

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def inject_trace_headers() -> list:
    carrier = {}
    _propagator.inject(carrier)
    return [(k, v.encode("utf-8")) for k, v in carrier.items()]


def extract_span_link(event_headers) -> list:
    parent_ctx = extract_trace_context(event_headers)
    if parent_ctx is None:
        return []
    parent_span = trace.get_current_span(parent_ctx)
    span_ctx = parent_span.get_span_context()
    if not span_ctx.is_valid:
        return []
    return [trace.Link(span_ctx)]


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
