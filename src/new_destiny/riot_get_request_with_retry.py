from __future__ import annotations

from .utilities import custom_print
from .riot_get_request import perform_riot_request
from .exceptions import RiotRelatedRateLimitException, RiotNetworkError
import asyncio
import httpx
import random
from functools import wraps
from .settings.config import ND_DEBUG

"""
Note: the retry logic is currently only meant for background processes. 
If a UI-triggered request gets 429'd or the like I recommend error handling that and no retry support. 
This is intentional, as users do not want to wait for a retry on top of the regular processing time.
Background jobs can happily wait.
"""


def _exp_backoff_with_jitter(*, attempt: int, base: float = 1.0, cap: float = 20.0) -> float:
    """
    Calculate exponential backoff with full jitter.

    Args:
        attempt: 1-based attempt number
        base: Base delay in seconds
        cap: Maximum delay in seconds

    Returns:
        Random sleep time between 0 and the exponential backoff ceiling
    """
    ceiling = min(cap, base * (2 ** (attempt - 1)))
    return random.uniform(0.0, ceiling)


def retry_on_riot_rate_limited_or_network_error(
    *,
    default_rate_limit_attempts: int = 3,
    default_network_attempts: int = 5,
):
    """
    Retry decorator for Riot API requests that handles:
      - RiotRelatedRateLimitException: Sleep retry_after + 1 seconds then retry
      - RiotNetworkError: Exponential backoff with jitter (transient network/infrastructure issues)
      - All other exceptions (RiotAPIError): Raised immediately without retry

    Args:
        default_rate_limit_attempts: Default number of retry attempts for rate limit exceptions.
        default_network_attempts: Default number of retry attempts for network exceptions.

    Per-call overrides (optional):
        attempts: int
        network_tolerance: int

    Note:
        Adds +1 second to retry_after for rate limits to ensure Redis has time to expire keys.
        If we sleep the exact amount and retry instantly, Redis may not have expired the violated key yet,
        causing a 0 second retry_after loop that exhausts attempts immediately.
    """
    if default_rate_limit_attempts < 1:
        raise ValueError("default_rate_limit_attempts must be >= 1. If you do not want retries do not use this function.")
    if default_network_attempts < 1:
        raise ValueError("default_network_attempts must be >= 1. If you do not want retries do not use this function.")

    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # Allow per-call overrides without type checkers complaining
            attempts = int(kwargs.pop("attempts", default_rate_limit_attempts))
            network_tolerance = int(kwargs.pop("network_tolerance", default_network_attempts))

            if attempts < 1:
                raise ValueError("attempts must be >= 1")
            if network_tolerance < 1:
                raise ValueError("network_tolerance must be >= 1")

            # Track budgets separately (not just "attempt number")
            rl_failures_seen = 0
            net_failures_seen = 0

            # Note: This loop is not bounded by a single total attempt count
            # It will terminate when an exception type exhausts its own budget,
            # or when the call succeeds, or when a non-retryable exception occurs.
            while True:
                try:
                    return await fn(*args, **kwargs)

                except RiotRelatedRateLimitException as exc:
                    rl_failures_seen += 1

                    if rl_failures_seen >= attempts:
                        # Exhausted RL budget
                        raise

                    sleep_s = int(exc.retry_after) + 1
                    if ND_DEBUG:
                        custom_print(
                            f"[Riot RL] {exc.__class__.__name__}, enforcement_type={exc.enforcement_type} "
                            f"retry_after={exc.retry_after} sleep={sleep_s}s "
                            f"rate_limit_failures_seen={rl_failures_seen} max_rate_limit_failures={attempts}",
                            color="yellow",
                        )
                    await asyncio.sleep(sleep_s)
                    continue

                except RiotNetworkError as exc:
                    net_failures_seen += 1

                    if net_failures_seen >= network_tolerance:
                        # Exhausted network budget
                        raise

                    sleep_s = _exp_backoff_with_jitter(attempt=net_failures_seen, base=1.0, cap=20.0)
                    if ND_DEBUG:
                        custom_print(
                            f"[Network] {exc.error_type}: {exc.message} "
                            f"sleep={sleep_s:.2f}s "
                            f"network_failures_seen={net_failures_seen} max_network_failures={network_tolerance}",
                            color="yellow",
                        )
                    await asyncio.sleep(sleep_s)
                    continue

        return wrapper

    return decorator


@retry_on_riot_rate_limited_or_network_error(
    default_rate_limit_attempts=3,
    default_network_attempts=5,
)
async def riot_request_with_retry(
    *,
    riot_endpoint: str,
    client: httpx.AsyncClient,
    async_redis_client,
    **kwargs,
):
    """
    Performs a Riot API request with automatic retry logic for rate limit failures and transient network failures.

    Optional per-call overrides (kwarg):
      - attempts: int
            Default 3
            How many total times should New Destiny attempt an individual request with respects to inbound rate limits. 
            Ex. 3 rate limits in a row == bubble the error up and stop sleeping & retrying
            1 means no retry. Bubble on first encounter--or just do not use this retry function.
      - network_tolerance: int
            Default 5
            How many total times should New Destiny tolerate potential transient network issues such as failure to connect.
            Some amount of this is unavoidable. If you run a job long enough you will see this.
            Sometimes a well foramtted request will just run into network issues.
            1 means no retry. Bubble on first encounter--or just do not use this retry function.

    Retries on:
      - RiotRelatedRateLimitException: Sleeps retry_after + 1 seconds, then retries (RL budget)
      - RiotNetworkError: Uses exponential backoff with jitter (NET budget)

    Does NOT retry on:
      - RiotAPIError: Real API errors (4XX client errors, 500 server errors) - raised immediately
      - Other exceptions: Unknown errors that should bubble up

    Note:
        **kwargs exists so type checkers don't complain when passing retry override kwargs.
        The decorator will pop these kwargs and will not forward them to perform_riot_request.
    """
    return await perform_riot_request(
        riot_endpoint=riot_endpoint,
        client=client,
        async_redis_client=async_redis_client,
    )
