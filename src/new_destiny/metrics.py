"""Best-effort Redis counters for observed New Destiny rate-limit events."""

from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import Any

from .exceptions import (
    ApplicationRateLimitExceeded,
    MethodRateLimitExceeded,
    RiotRelatedRateLimitException,
    ServiceRateLimitExceeded,
    UnspecifiedRateLimitExceeded,
)
RATE_LIMIT_METRICS_RETENTION_SECONDS = 25 * 60 * 60
logger = logging.getLogger(__name__)


def _key_token(value: str) -> str:
    """Keep dynamic Redis key segments readable and delimiter-safe."""
    token = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return token or "unknown"


def _rate_limit_type(error: RiotRelatedRateLimitException) -> str:
    if isinstance(error, ApplicationRateLimitExceeded):
        return "application"
    if isinstance(error, MethodRateLimitExceeded):
        return "method"
    if isinstance(error, ServiceRateLimitExceeded):
        return "service"
    if isinstance(error, UnspecifiedRateLimitExceeded):
        return "unspecified"
    raise TypeError(f"Unsupported rate-limit exception: {type(error).__name__}")


def _minute_bucket(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")


def build_rate_limit_metric_key(
    error: RiotRelatedRateLimitException,
    *,
    now: datetime | None = None,
) -> str:
    """Build the scope-first key for one minute of observed rate-limit events."""
    rate_limit_type = _rate_limit_type(error)
    parts = [
        "nd",
        "metrics",
        "rate-limit",
        rate_limit_type,
        _key_token(error.routing_value),
        _key_token(error.enforcement_type),
    ]

    if rate_limit_type == "service":
        parts.append(_key_token(error.service))
    elif rate_limit_type in {"method", "unspecified"}:
        parts.extend((_key_token(error.service), _key_token(error.method)))

    parts.append(_minute_bucket(now))
    return ":".join(parts)


async def record_rate_limit_event(
    async_redis_client: Any,
    error: RiotRelatedRateLimitException,
    *,
    now: datetime | None = None,
) -> str:
    """Increment one bucketed counter without affecting rate-limit handling.

    The Redis pipeline keeps the increment and TTL update in one round trip.
    Metrics are best effort: a Redis metrics failure must never replace the
    rate-limit exception that the caller needs to handle.
    """
    key = build_rate_limit_metric_key(error, now=now)

    try:
        pipeline = async_redis_client.pipeline(transaction=True)
        pipeline.incr(key)
        pipeline.expire(key, RATE_LIMIT_METRICS_RETENTION_SECONDS)
        await pipeline.execute()
    except Exception as metric_error:  # pragma: no cover - exercised by integration failures
        logger.warning(
            "New Destiny rate-limit metric recording failed for %s: %s",
            key,
            type(metric_error).__name__,
        )

    return key
