from .utilities import custom_print
from .riot_get_request import perform_riot_request
from .exceptions import RiotRelatedRateLimitException, RiotNetworkError
import asyncio
import httpx
import random
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


def retry_on_riot_rate_limited_or_network_error(default_attempts: int = 3):
    """
    Retry decorator for Riot API requests that handles:
      - RiotRelatedRateLimitException: Sleep retry_after + 1 seconds then retry
      - RiotNetworkError: Exponential backoff with jitter (transient network/infrastructure issues)
      - All other exceptions (RiotAPIError): Raised immediately without retry
    
    Args:
        default_attempts: Default number of retry attempts (can be overridden per-call with attempts kwarg)
    
    Note: 
        Adds +1 second to retry_after for rate limits to ensure Redis has time to expire keys.
        If we sleep the exact amount and retry instantly, Redis may not have expired the violated key yet,
        causing a 0 second retry_after loop that exhausts attempts immediately.
    """
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            total_attempts = kwargs.pop("attempts", default_attempts)
            
            for attempt in range(1, total_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                
                except RiotRelatedRateLimitException as exc:
                    if attempt < total_attempts:
                        sleep_s = int(exc.retry_after) + 1
                        if ND_DEBUG:
                            custom_print(
                                f"[Riot RL] {exc.__class__.__name__}, enforcement_type={exc.enforcement_type} "
                                f"retry_after={exc.retry_after} sleep={sleep_s}s attempt={attempt}/{total_attempts}",
                                color="yellow",
                            )
                        await asyncio.sleep(sleep_s)
                        continue
                    raise
                
                except RiotNetworkError as exc:
                    if attempt < total_attempts:
                        sleep_s = _exp_backoff_with_jitter(attempt=attempt, base=1.0, cap=20.0)
                        if ND_DEBUG:
                            custom_print(
                                f"[Network] {exc.error_type}: {exc.message} "
                                f"sleep={sleep_s:.2f}s attempt={attempt}/{total_attempts}",
                                color="yellow",
                            )
                        await asyncio.sleep(sleep_s)
                        continue
                    raise
        
        return wrapper
    return decorator


@retry_on_riot_rate_limited_or_network_error(default_attempts=3)
async def riot_request_with_retry(*, riot_endpoint: str, client: httpx.AsyncClient, async_redis_client, **kwargs):
    """
    Performs a Riot API request with automatic retry logic for transient failures.
    
    Retries on:
      - RiotRelatedRateLimitException: Sleeps retry_after + 1 seconds, then retries
      - RiotNetworkError: Uses exponential backoff with jitter (handles timeouts, connection errors, 
        gateway errors 502/503/504, Cloudflare 52X errors)
    
    Does NOT retry on:
      - RiotAPIError: Real API errors (4XX client errors, 500 server errors) - these indicate issues 
        with the request or Riot's API state that won't be fixed by retrying
      - Other exceptions: Unknown errors that should bubble up
    
    Args:
        riot_endpoint: Full Riot API endpoint URL
        client: httpx AsyncClient instance
        async_redis_client: Redis client for rate limiting
        attempts: Optional override for number of retry attempts (default: 3)
    
    Returns:
        dict, list, or None depending on the endpoint response
    
    Raises:
        RiotRelatedRateLimitException: After exhausting retry attempts on rate limits
        RiotNetworkError: After exhausting retry attempts on network errors
        RiotAPIError: Immediately without retry (real API errors)

    Note:
        **kwargs is used so type checkers don't complain about "attempts" being passed in.
        The decorator will pop the "attempts" kwarg and use it for retry logic.
    """
    return await perform_riot_request(
        riot_endpoint=riot_endpoint, 
        client=client, 
        async_redis_client=async_redis_client
    )