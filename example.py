# your_project/example.py
from new_destiny.json_types import expect_dict, expect_string
from new_destiny.riot_get_request import perform_riot_request
from new_destiny.riot_get_request_with_retry import riot_request_with_retry
from new_destiny.settings.config import ND_REDIS_PORT, ND_REDIS_URL
from new_destiny.exceptions import RiotRelatedRateLimitException, RiotAPIError, RiotNetworkError, RiotRelatedException
# You can catch these exception subclasses if you want to but it is probably unnecessary:
# from new_destiny.exceptions import ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
import ssl
import httpx
import certifi 
import redis.asyncio
import asyncio
import time # Not a requirement, just for logging purposes

# Rate-limit exception metrics are enabled by default. Set
# ND_ENABLE_ERROR_METRICS=0 if you do not want those temporary Redis counters.
# Admitted-request metrics are higher volume and disabled by default. Set
# ND_ENABLE_REQUEST_METRICS=1 when you want method-level traffic analysis.

# 2) Configure SSL Context for HTTPX. HTTPX uses this to verify Riot's HTTPS certificate.
# The explicit Certifi bundle helps when local Python does not have its CA certificates configured.
# This is safe for production as written. If SSL is unfamiliar, safely use this code as written and do not change it.
ssl_context = ssl.create_default_context(cafile=certifi.where())

# 3) Connect to Redis
async_redis_client = redis.asyncio.Redis(host=ND_REDIS_URL, port=ND_REDIS_PORT, db=0, decode_responses=True)

# 4) Your async application code
# HTTPX was selected because it provides an async client with connection reuse and
# concurrency support while your application keeps control of the client lifecycle.
async def main():
    # Example application code:
    # do_some_work() ...

    # 5) Example One: Time to use New Destiny
    # start_time = time.monotonic()
    # async with httpx.AsyncClient(verify=ssl_context) as client:
    #     """
    #     Note: You may only use actual, properly formatted Riot API Endpoints.
    #     Otherwise New Destiny will not know what ratelimit applies to the request.
    #     """
    #     region = "asia"
    #     gamename = "hide on bush"
    #     tagline = "KR1"
    #     account_endpoint = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gamename}/{tagline}"
    #     account_details = await perform_riot_request(
    #         riot_endpoint=account_endpoint,
    #         client=client,
    #         async_redis_client=async_redis_client
    #     )
    #     if account_details is None:
    #         raise ValueError("Expected account details but Riot returned no content.")
    #     account_payload = expect_dict(account_details)
    #     puuid = expect_string(account_payload["puuid"])
    
    # # 6) Do whatever you want with the response
    # print("EXAMPLE 1")
    # print("Type:", type(account_details))
    # print("PUUID:", puuid)
    # print("Response: ",account_details)
    # print("Time:", time.monotonic() - start_time)
    # print("Feelin' lucky?")

    # 7) Example Two: New Destiny with concurrency. Raise the first exception (which includes RiotRelatedRateLimitException(s)) if any are encountered.
    # try:
    #     match_endpoints = [
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
    #         "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075"
    #     ]

    #     start_time = time.monotonic()
    #     async with httpx.AsyncClient(verify=ssl_context) as client:
    #         batch_results = await asyncio.gather(
    #             *[perform_riot_request(
    #                 riot_endpoint=endpoint,
    #                 client=client,
    #                 async_redis_client=async_redis_client)
    #                 for endpoint in match_endpoints]
    #         , return_exceptions=False)

    #     print("EXAMPLE 2")
    #     print("Type:", type(batch_results))
    #     print("Length:", len(batch_results))
    #     print("Type of first element", type(batch_results[0]))
    #     print("Time:", time.monotonic() - start_time)
    #     print("End of the line.")

    # except RiotRelatedRateLimitException as exc:
    #     # This means New Destiny stopped the request before sending it (internal),
    #     # or Riot received it and returned a 429 (external).
    #     # Important!
    #     # You can also specifically catch: ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
    #     # These also fall under type RiotRelatedException
    #     # See: Q&A Design philosphy 'Respect' section for more.
    #     print(exc)
    #     print(exc.retry_after)
    #     pass
    # except RiotAPIError as exc:
    #     # Your error handling logic
    #     # RiotAPIError is raised for non-success API responses that are not rate limits.
    #     pass
    # except RiotNetworkError as exc:
    #     # A transient connection, gateway, or Cloudflare failure occurred.
    #     pass
    # except RiotRelatedException as exc:
    #     # Use this if you want a catch-all for any Riot API related exception.
    #     # This includes rate-limit, API, and transient network errors.
    #     pass
    # except Exception as exc:
    #     # If 'exc' exception is not of type RiotRelatedException it has nothing to
    #     # do with Riot, likely has nothing to do with New Destiny, and is likely your application code
    #     pass

    # # 8) Example Three: New Destiny with concurrency. Suppress but gather any experienced errors.
    # start_time = time.monotonic()
    # async with httpx.AsyncClient(verify=ssl_context) as client:
    #     batch_results = await asyncio.gather(
    #         *[perform_riot_request(
    #             riot_endpoint=endpoint,
    #             client=client,
    #             async_redis_client=async_redis_client)
    #             for endpoint in match_endpoints]
    #     , return_exceptions=True)

    # for result in batch_results:
    #     if isinstance(result, RiotRelatedRateLimitException):
    #         print(result.retry_after)
    #         # Do whatever you want
    #     elif isinstance(result, Exception):
    #         # Potentially raise the Exception, filter it out etc,
    #         pass

    # print("EXAMPLE 3")
    # print("Type:", type(batch_results))
    # print("Length:", len(batch_results))
    # print("Type of first element:", type(batch_results[0]))
    # print("Time:", time.monotonic() - start_time)
    # print("Dead man walkin'.")
    
    # 9) Example Four: Imagine you have a workflow that requires many requests to build something "whole".
    # Imagine you want the match details for n = LARGE_NUMBER of Faker matches.
    # For either resource or rate limit concerns you do not want to fire off n = LARGE_NUMBER requests concurrently.
    # You can use riot_request_with_retry() to automatically retry a request that gets rate limited 
    # (raises an exception of type RiotRelatedRateLimitException)
    # up to a total number of attempts (default is 3). This protects your workflow against rate limit exceptions.
    # If a request gets rate limited more than the number of attempts specified the exception will propagate here.
    # You can catch it with try/except. Other types of Exceptions will get raised immediately and do not get retried.

    # You can still use standard python/asyncio tools to control the level of concurrency or batch size
    # but this example simply demonstrates how this would work if you have a series of requests that fire one at a time.
    # This function is useful if you have background jobs that interact with the Riot API.
    # It is probably inappropriate to have potential UI users of your application experience retry times
    # if you do chose to expose a UI to users.
    fakers_matches = [
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658139863",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656081157",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656041838",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656007612",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655955675",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7655891458",
    ]

    start_time = time.monotonic()
    match_details = []
    async with httpx.AsyncClient(verify=ssl_context) as client:
        for endpoint in fakers_matches:
            match_detail = await riot_request_with_retry(
                riot_endpoint=endpoint,
                client=client,
                async_redis_client=async_redis_client,
                attempts=3 # Try this with 1 and some other larger number like 3
            )
            match_details.append(match_detail)

    print("EXAMPLE 4")
    print("Type:", type(match_details))
    print("Length:", len(match_details))
    print("Type of first element", type(match_details[0]))
    print("Time:", time.monotonic() - start_time)
    print("Go ahead. I like moving targets.")

    # 10) Example Five: Spectator active-game edge case.
    # A player who is not currently in a game produces an expected 404.
    # spectator_endpoint = f"https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    # try:
    #     async with httpx.AsyncClient(verify=ssl_context) as client:
    #         spectator_details = await perform_riot_request(
    #             riot_endpoint=spectator_endpoint,
    #             client=client,
    #             async_redis_client=async_redis_client,
    #         )
    # except RiotAPIError as exc:
    #     # <- Your error handling logic here ->
    #     # RiotAPIError is raised for non-success API responses that are NOT rate limits.
    #     # In general this works exactly how you would think it does.
    #     # IMPORTANT EDGE CASE: Riot returns a 404 when a player exists but is
    #     # not currently in-game. This differs from the normal Riot API pattern,
    #     # but it is the expected Spectator-V5 response for no active game.
    #     # At ND_LOG_LEVEL=2 or higher, New Destiny logs this expected response as
    #     # a structured no-active-game event instead of noisy error output.
    #     if exc.status_code == 404:
    #         spectator_details = None
    #         print("Riot says this player is not currently in-game.")
    #     else:
    #         raise


if __name__ == "__main__":
    asyncio.run(main())
