from .rate_limiter import ApplicationRateLimiter, MethodRateLimiter, ServiceRateLimiter, UnspecifiedRiotRateLimiter
from .rate_limit_exceptions import RiotAPIError
import httpx
from dotenv import load_dotenv
from .utilities import custom_print
import asyncio
import json
import os
from json import JSONDecodeError
from .settings.config import ND_RIOT_API_KEY, ND_DEBUG
load_dotenv()

riot_key = ND_RIOT_API_KEY
debug = int(ND_DEBUG)
auth_headers = {'X-Riot-Token': riot_key}

async def perform_riot_request(riot_endpoint, client: httpx.AsyncClient, async_redis_client):
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
    if debug: custom_print("rate limiter checks passed", color="black")

    # Perform the GET request
    if debug: custom_print(riot_endpoint, color="black")
    response = await client.get(riot_endpoint, headers=auth_headers)
    status = response.status_code
    
    # 200 OK
    if status == 200:
        body = response.json()
        return body

    elif status == 204: # No Content - this happens mostly when LEAGUE-EXP-V4 Apex tiers are empty in the early season
        return None

    elif service_rate_limiter.service == 'MATCH-V5' and status == 403:
        # This means the game mode was the new BRAWL game mode and the Riot API does not support it by their design choice
        # https://x.com/RiotGamesDevRel/status/1922373887599489163
        if debug: custom_print(f"Riot API returned 403 for {service_rate_limiter.service} with URL: {riot_endpoint}", color="cyan")
        return None

    # Rate limited by Riot
    elif status == 429:
        headers = dict(response.headers)
        body = response.json()
        retry_after = int(headers.get("retry-after", 68)) + 1
        rate_limit_type = headers.get("x-rate-limit-type", None)
        if debug: 
            custom_print(rate_limit_type, color="yellow")
            custom_print(headers, color="yellow")
        if rate_limit_type == "application":
            await application_rate_limiter.write_inbound_application_rate_limit(retry_after=retry_after, offending_context={"headers": headers, "body": body})
        elif rate_limit_type == "method":
            await method_rate_limiter.write_inbound_method_rate_limit(retry_after=retry_after, offending_context={"headers": headers, "body": body})
        elif rate_limit_type == "service":
            await service_rate_limiter.write_inbound_service_rate_limit(offending_context={"headers": headers, "body": body}) # Note this takes a default value defined in the ServiceRateLimiter class
        else: # If Riot failed to provide the X-Rate-Limit-Type header which is a bug that has rarely been observed...write a block-all to be respectful
            await unspecified_rate_limiter.write_inbound_unspecified_rate_limit(retry_after=retry_after, offending_context={"headers": headers, "body": body})

    else: # 500 series or anything not 200/204/429
        headers = dict(response.headers)
        if debug:
            custom_print(status, color="red")
            custom_print(headers, color="red")
            custom_print(riot_endpoint, color="red")
            custom_print(response, color="red")
        try:
            body = response.json()
            raise RiotAPIError(
                status_code= status,
                message=body,
                riot_endpoint=riot_endpoint,
                offending_context={"headers": headers, "body": body},
            )
        except JSONDecodeError as err: # Ocassionally Riot returns a null body with a 500 series error possibly with 502s and 504s
            raise RiotAPIError(
                status_code= status,
                message= f"Riot returned null body so parising failed, {str(err)}.",
                riot_endpoint=riot_endpoint,
                offending_context={"headers": headers, "body": None},
            )