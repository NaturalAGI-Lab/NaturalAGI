import functools
import logging
import time

logger = logging.getLogger(__name__)


def timed(
    func=None, *, log_level=logging.INFO, threshold_ms=None, label=None, repeat=1
):
    """Decorator that logs average elapsed time of *repeat* executions.

    Args:
        log_level: standard logging level or Loguru's if you swap logger.
        threshold_ms: if set, emit WARNING when elapsed > threshold.
        label: friendly name to show; defaults to func.__qualname__.
        repeat: run the function N times and average (basic smoothing).
    """

    def deco(f):
        lbl = label or f.__qualname__

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            total_ns = 0
            for _ in range(repeat):
                start = time.perf_counter_ns()
                result = f(*args, **kwargs)
                total_ns += time.perf_counter_ns() - start
            avg_ms = total_ns / repeat / 1_000_000
            level = (
                logging.WARNING if threshold_ms and avg_ms > threshold_ms else log_level
            )
            logger.log(
                level,
                "⏱ %s took %.3f ms (avg of %d run%s)",
                lbl,
                avg_ms,
                repeat,
                "s" if repeat > 1 else "",
            )
            return result

        return wrapper

    if func is None:
        return deco
    else:
        return deco(func)
