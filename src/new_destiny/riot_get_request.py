from .rate_limiter import ApplicationRateLimiter, MethodRateLimiter, ServiceRateLimiter, UnspecifiedRiotRateLimiter
from .exceptions import RiotAPIError, RiotNetworkError
from .json_types import JSONValue, RiotResponse
import httpx
from dotenv import load_dotenv
from .utilities import custom_print
from typing import Any, cast
from json import JSONDecodeError
from .settings.config import ND_RIOT_API_KEY, ND_LOG_LEVEL
load_dotenv()

riot_key = ND_RIOT_API_KEY
log_level = ND_LOG_LEVEL
auth_headers: dict[str, str] = {"X-Riot-Token": riot_key}


def _parse_json_value(response: httpx.Response) -> JSONValue:
    """Cast the JSON boundary returned by httpx into the library's JSON type."""
    return cast(JSONValue, response.json())

async def perform_riot_request(
    riot_endpoint: str, 
    client: httpx.AsyncClient, 
    async_redis_client: Any,
) -> RiotResponse:
    """
    Performs a GET request to the Riot API while respecting their rate limiting.
    In the vast majority of cases you should expect this function to return valid JSON data in either a dict or list form.
    In rare cases (See Status Code 204 case) this function may correctly return None.
    In all other cases you will experience a RiotRelatedException--either a RiotAPIError due to a 4XX or 5XX response from Riot, 
    or an exception from the RiotRelatedRateLimitException classes where a rate limit is hit and New Destiny caught it.
    Note that some 5XX errors are transient network related issues. You may want to catch httpx.RequestError (catch all),
    httpx.ConnectionError, or httpx.TimeoutException errors in your application. These will buble up.
    """
    # Instantiate the rate limiters
    application_rate_limiter = ApplicationRateLimiter(riot_endpoint, async_redis_client)
    method_rate_limiter = MethodRateLimiter(riot_endpoint, async_redis_client)
    service_rate_limiter = ServiceRateLimiter(riot_endpoint, async_redis_client)
    unspecified_rate_limiter = UnspecifiedRiotRateLimiter(riot_endpoint, async_redis_client)

    # Check if any limit is currently hit and increment
    await application_rate_limiter.check_and_increment()
    await method_rate_limiter.check_and_increment()
    await service_rate_limiter.is_allowed()
    await unspecified_rate_limiter.is_allowed()
    if log_level >= 3: custom_print("rate limiter checks passed", color="black")

    # Perform the GET request with network error handling
    try:
        if log_level >= 3: custom_print(riot_endpoint, color="black")
        response = await client.get(riot_endpoint, headers=auth_headers)
    except httpx.TimeoutException as e:
        raise RiotNetworkError(
            error_type="timeout",
            message=f"Request timed out: {str(e)}",
            riot_endpoint=riot_endpoint,
            original_exception=e
        )
    except httpx.ConnectError as e:
        raise RiotNetworkError(
            error_type="connection",
            message=f"Failed to connect: {str(e)}",
            riot_endpoint=riot_endpoint,
            original_exception=e
        )
    except httpx.RequestError as e:
        # Catches all request-level errors (DNS, SSL, etc.) but NOT status code errors
        raise RiotNetworkError(
            error_type="request_error",
            message=f"Request error occurred: {str(e)}",
            riot_endpoint=riot_endpoint,
            original_exception=e
        )
    status = response.status_code
    expected_spectator_404 = (
        status == 404
        and service_rate_limiter.service == "SPECTATOR-V5"
        and method_rate_limiter.method == "/lol/spectator/v5/active-games/by-summoner"
    )
    expected_spectator_404 = (
        status == 404
        and service_rate_limiter.service == "SPECTATOR-V5"
        and method_rate_limiter.method == "/lol/spectator/v5/active-games/by-summoner"
    )
    
    # 200 OK
    if status == 200:
        body = cast(RiotResponse, _parse_json_value(response))
        return body

    elif status == 204: # No Content - this happens mostly when LEAGUE-EXP-V4 Apex tiers are empty in the early season
        return None

    elif service_rate_limiter.service == 'MATCH-V5' and status == 403:
        # This means the game mode was the new BRAWL game mode and the Riot API does not support it by their design choice
        # https://x.com/RiotGamesDevRel/status/1922373887599489163
        if log_level >= 2:
            custom_print({
                "event": "riot_api_response",
                "status_code": status,
                "service": service_rate_limiter.service,
                "method": method_rate_limiter.method,
                "subdomain": service_rate_limiter.subdomain,
                "riot_endpoint": riot_endpoint,
                "handling": "ignored_brawl_match_v5_response",
            }, color="cyan")
        return None

    # Rate limited by Riot
    elif status == 429:
        headers = dict(response.headers)
        body = _parse_json_value(response)
        retry_after_header = headers.get("retry-after")
        retry_after = int(retry_after_header or 68) + 1
        rate_limit_type = headers.get("x-rate-limit-type", None)
        if log_level >= 2:
            custom_print({
                "event": "riot_rate_limit_response",
                "status_code": status,
                "rate_limit_type": rate_limit_type or "unspecified",
                "enforcement_type": "external",
                "retry_after_header_seconds": retry_after_header or "missing",
                "effective_retry_after_seconds": retry_after,
                "service": service_rate_limiter.service,
                "method": method_rate_limiter.method,
                "subdomain": service_rate_limiter.subdomain,
                "riot_endpoint": riot_endpoint,
                "fallback_blocking_key": unspecified_rate_limiter.blocking_key,
            }, color="yellow")
            custom_print({"response_headers": headers, "response_body": body}, color="yellow")
        if rate_limit_type == "application":
            await application_rate_limiter.write_inbound_application_rate_limit(retry_after=retry_after, offending_context={"headers": headers, "body": body})
        elif rate_limit_type == "method":
            await method_rate_limiter.write_inbound_method_rate_limit(retry_after=retry_after, offending_context={"headers": headers, "body": body})
        elif rate_limit_type == "service":
            await service_rate_limiter.write_inbound_service_rate_limit(offending_context={"headers": headers, "body": body}) # Note this takes a default value defined in the ServiceRateLimiter class
        else: # If Riot failed to provide the X-Rate-Limit-Type header which is a bug that has rarely been observed...write a block-all to be respectful
            if log_level >= 2:
                custom_print({
                    "event": "riot_unexpected_rate_limit",
                    "message": "Riot returned a 429 without a recognized rate-limit type; applying the unspecified fallback scope.",
                    "enforcement_type": "external",
                    "scope": "known-unpredictable_for_spectator_otherwise_unspecified",
                    "service": service_rate_limiter.service,
                    "method": method_rate_limiter.method,
                    "subdomain": service_rate_limiter.subdomain,
                    "riot_endpoint": riot_endpoint,
                    "blocking_key": unspecified_rate_limiter.blocking_key,
                    "effective_retry_after_seconds": retry_after,
                }, color="red")
            await unspecified_rate_limiter.write_inbound_unspecified_rate_limit(retry_after=retry_after, offending_context={"headers": headers, "body": body})

    # Transient gateway/proxy errors - treat as network errors (can be retried)
    elif status in {502, 503, 504}:
        headers = dict(response.headers)
        error_messages = {
            502: "Bad Gateway - upstream server returned invalid response",
            503: "Service Unavailable - server temporarily overloaded or down",
            504: "Gateway Timeout - upstream server failed to respond in time"
        }
        error_msg = error_messages.get(status, f"Gateway error {status}")
        if log_level >= 1:
            custom_print(status, color="yellow")
            custom_print(headers, color="yellow")
            custom_print(riot_endpoint, color="yellow")
        raise RiotNetworkError(
            error_type="gateway",
            message=f"{status} {error_msg}",
            riot_endpoint=riot_endpoint,
            original_exception=None  # We got a response, just a bad gateway status
        )

    # Cloudflare-specific errors (52X range) - also transient infrastructure issues
    elif 520 <= status <= 527:
        headers = dict(response.headers)
        cloudflare_errors = {
            520: "Web server returned unknown error",
            521: "Web server is down",
            522: "Connection timed out",
            523: "Origin is unreachable",
            524: "Timeout occurred",
            525: "SSL handshake failed",
            526: "Invalid SSL certificate",
            527: "Railgun error"
        }
        error_msg = cloudflare_errors.get(status, f"Cloudflare error {status}")
        if log_level >= 1:
            custom_print(status, color="yellow")
            custom_print(headers, color="yellow")
            custom_print(riot_endpoint, color="yellow")
        raise RiotNetworkError(
            error_type="cloudflare",
            message=f"Cloudflare {status}: {error_msg}",
            riot_endpoint=riot_endpoint,
            original_exception=None
        )

    else: # Real API errors (4XX client errors, 500 server errors)
        headers = dict(response.headers)
        if log_level >= 1:
            if expected_spectator_404 and log_level >= 2:
                custom_print({
                    "event": "riot_expected_empty_response",
                    "status_code": status,
                    "service": service_rate_limiter.service,
                    "method": method_rate_limiter.method,
                    "subdomain": service_rate_limiter.subdomain,
                    "riot_endpoint": riot_endpoint,
                    "handling": "no_active_game",
                }, color="cyan")
            elif not expected_spectator_404:
                custom_print(status, color="red")
                custom_print(headers, color="red")
                custom_print(riot_endpoint, color="red")
                custom_print(response, color="red")
        try:
            body = _parse_json_value(response)
            raise RiotAPIError(
                status_code=status,
                message=body,
                riot_endpoint=riot_endpoint,
                offending_context={"headers": headers, "body": body},
            )
        except JSONDecodeError as err: # Occasionally Riot returns a null body with a 500 series error possibly with 502s and 504s
            raise RiotAPIError(
                status_code=status,
                message=f"Riot returned null body so parsing failed, {str(err)}.",
                riot_endpoint=riot_endpoint,
                offending_context={"headers": headers, "body": None},
            )
