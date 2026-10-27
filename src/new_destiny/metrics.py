"""Best-effort Redis counters for New Destiny traffic observations."""

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
REQUEST_METRICS_RETENTION_SECONDS = 25 * 60 * 60
logger = logging.getLogger(__name__)

_INCREMENT_AND_EXPIRE_ON_FIRST_WRITE = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


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


def build_request_metric_key(
    *,
    routing_value: str,
    service: str,
    method: str,
    now: datetime | None = None,
) -> str:
    """Build a minute bucket for one admitted outbound Riot request."""
    return ":".join(
        (
            "nd",
            "metrics",
            "request",
            _key_token(routing_value),
            _key_token(service),
            _key_token(method),
            _minute_bucket(now),
        )
    )


async def _record_counter(
    async_redis_client: Any,
    *,
    key: str,
    retention_seconds: int,
) -> str:
    """Increment a counter and set its TTL only on the first write."""
    try:
        await async_redis_client.eval(
            _INCREMENT_AND_EXPIRE_ON_FIRST_WRITE,
            1,
            key,
            retention_seconds,
        )
    except Exception as metric_error:  # pragma: no cover - exercised by integration failures
        logger.warning(
            "New Destiny metric recording failed for %s: %s",
            key,
            type(metric_error).__name__,
        )
    return key


async def record_rate_limit_event(
    async_redis_client: Any,
    error: RiotRelatedRateLimitException,
    *,
    now: datetime | None = None,
) -> str:
    """Increment one bucketed counter without affecting rate-limit handling.

    A Redis Lua script keeps the increment and first-write TTL update atomic.
    Metrics are best effort: a Redis metrics failure must never replace the
    rate-limit exception that the caller needs to handle.
    """
    key = build_rate_limit_metric_key(error, now=now)

    return await _record_counter(
        async_redis_client,
        key=key,
        retention_seconds=RATE_LIMIT_METRICS_RETENTION_SECONDS,
    )


async def record_request_event(
    async_redis_client: Any,
    *,
    routing_value: str,
    service: str,
    method: str,
    now: datetime | None = None,
) -> str:
    """Record one request admitted immediately before the HTTP call is sent."""
    key = build_request_metric_key(
        routing_value=routing_value,
        service=service,
        method=method,
        now=now,
    )
    return await _record_counter(
        async_redis_client,
        key=key,
        retention_seconds=REQUEST_METRICS_RETENTION_SECONDS,
    )
