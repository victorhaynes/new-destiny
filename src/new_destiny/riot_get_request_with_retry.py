from .utilities import custom_print
from .riot_get_request import perform_riot_request
from .rate_limit_exceptions import RiotRelatedRateLimitException, BatchJobStopSignal
import asyncio
import httpx

"""
Note: the retry logic is currently only meant for background processes. 
If a UI-triggered request gets 429'd I recommend using erorr handling that and no retry support. 
This is intentional, as users do not want to wait for a retry on top of the regular processing time.
Background jobs can happily wait.
"""


def retry_on_riot_timeout(default_attempts: int=3):
    """
    Note: if we sleep the exact amount and retry instantly it is possible and likely Redis did not have time to expire the violated key. 
    If that happens we will raise a Rate Limit style exception but with a 0 second retry_after time and that will instantly call Redis again with 0 second sleep and max out the attempts
    """
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            total_attempts = kwargs.pop("attempts", default_attempts)
            last_exec = None
            for attempt in range(1, total_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except RiotRelatedRateLimitException as exc:
                    last_exec = exc
                    if attempt < total_attempts:
                        custom_print(f"Experienced {type(exc)} sleeping for {exc.retry_after} then retrying. Retry #{attempt}...", color="yellow")
                        custom_print(exc, color="yellow")
                        await asyncio.sleep(int(exc.retry_after)+1)
                    else:
                        raise
            raise last_exec
        return wrapper
    return decorator

@retry_on_riot_timeout()
async def riot_request_with_retry(*, riot_endpoint: str, client: httpx.AsyncClient, async_redis_client):
    """Call this function like perform_riot_request() but include an 'attempts' integer argument."""
    try:
        return await perform_riot_request(riot_endpoint=riot_endpoint, client=client, async_redis_client=async_redis_client)
    except Exception as exc:
        if isinstance(exc, RiotRelatedRateLimitException):
            # this means it is RiotRelatedException or more specifically in (ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded)
            # raise it for retry in the decorator
            raise 
        raise # RiotApiError, BatchJobStopSignal, or other general non-custom exception will just get raised and returned to the caller