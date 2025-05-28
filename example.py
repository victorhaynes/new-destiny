# your_project/example.py
from new_destiny.riot_get_request import perform_riot_request
from new_destiny.riot_get_request_with_retry import riot_request_with_retry
from new_destiny.settings.config import ND_REDIS_PORT, ND_REDIS_URL
from new_destiny.rate_limit_exceptions import RiotRelatedRateLimitException, RiotAPIError, RiotRelatedException
# from new_destiny.rate_limit_exceptions import ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
import ssl
import httpx
import certifi
import redis
import asyncio
import time # Not a requirement, just for logging purposes

# 2) Configure SSL Context for HTTPX. Accept this default or choose your own.
ssl_context = ssl.create_default_context(cafile=certifi.where())

# 3) Connect to Redis
async_redis_client = redis.asyncio.Redis(host=ND_REDIS_URL, port=ND_REDIS_PORT, db=0, decode_responses=True)

# 4) Your async application code
async def main():
    # Example application code:
    # do_some_work() ...

    # 5) Example One: Time to use New Destiny
    start_time = time.monotonic()
    async with httpx.AsyncClient(verify=ssl_context) as client:
        """
        Note: You may only use actual, properly formatted Riot API Endpoints.
        Otherwise New Destiny will not know what ratelimit applies to the request.
        """
        region = "asia"
        gamename = "hide on bush"
        tagline = "KR1"
        account_endpoint = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gamename}/{tagline}"
        account_details = await perform_riot_request(
            riot_endpoint=account_endpoint,
            client=client,
            async_redis_client=async_redis_client
        )
    
    # 6) Do whatever you want with the response
    print("EXAMPLE 1")
    print("Type:", type(account_details))
    print("Response: ",account_details)
    print("Time:", time.monotonic() - start_time)
    print("Feelin' lucky?")

    # 7) Example Two: New Destiny with concurrency. Raise first exception (which include RiotRelatedRateLimitException(s)) if any encoutnered.
    try:
        match_endpoints = [
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657049506",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656996570",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656945076",
            "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7656366075"
        ]

        start_time = time.monotonic()
        async with httpx.AsyncClient(verify=ssl_context) as client:
            batch_results = await asyncio.gather(
                *[perform_riot_request(
                    riot_endpoint=endpoint,
                    client=client,
                    async_redis_client=async_redis_client)
                    for endpoint in match_endpoints]
            , return_exceptions=False)

        print("EXAMPLE 2")
        print("Type:", type(batch_results))
        print("Length:", len(batch_results))
        print("Type of first element", type(batch_results[0]))
        print("Time:", time.monotonic() - start_time)
        print("End of the line.")

    except RiotRelatedRateLimitException as exc:
        # This explicitly means you were either rate limited by New Destiny (internally) or Riot (externally)
        # Important!
        # You can also specifically catch: ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
        # These also fall under type RiotRelatedException
        # See: Q&A Design philosphy 'Respect' section for more.
        print(exc)
        print(exc.retry_after)
        pass
    except RiotAPIError as exc:
        # Your error handling logic
        # RiotAPIError is raised when a non-429, non-ok response is returned from Riot such as a 500 series (rare) or 404.
        pass
    except RiotRelatedException as exc:
        # Use this if you want a catch-all for any Riot API related exception.
        # This just the union of RiotRelatedRateLimitException and RiotAPIError        
        pass
    except Exception as exc:
        # If 'exc' exception is not of type RiotRelatedException it has nothing to
        # do with Riot, likely has nothing to do with New Destiny, and is likely your application code
        pass

    # 7) Example Three: New Destiny with concurrency. Supress but gather any experienced errors.
    start_time = time.monotonic()
    async with httpx.AsyncClient(verify=ssl_context) as client:
        batch_results = await asyncio.gather(
            *[perform_riot_request(
                riot_endpoint=endpoint,
                client=client,
                async_redis_client=async_redis_client)
                for endpoint in match_endpoints]
        , return_exceptions=True)

    for result in batch_results:
        if isinstance(result, RiotRelatedRateLimitException):
            print(result.retry_after)
            # Do whatever you want
        elif isinstance(result, Exception):
            # Potentially raise the Exception, filter it out etc,
            pass

    print("EXAMPLE 3")
    print("Type:", type(batch_results))
    print("Length:", len(batch_results))
    print("Type of first element:", type(batch_results[0]))
    print("Time:", time.monotonic() - start_time)
    print("Dead man walkin'.")
    
    # 8) Example Four: Imagine you have a workflow that requires many requests to build something "whole".
    # Imagine you want the match details of n = LAGE_NUBMER Faker matches.
    # For either resource or rate limit concerns you do not want to fire off n = LAGE_NUBMER requests concurrently.
    # You can use riot_request_with_retry() to automatically retry a request that gets rate limited (raises an exception of type RiotRelatedRateLimitException)
    # up to a total number of attempts (default is 3).
    # If a request gets rate limited more than the # of attempts specified the exception will propogate here. You can catch it with try/except.
    # Other types of Exceptions will get raised immediately and do not get retried.

    # You can still use standard python/asyncio tools to control the level of concurrecy or batch size
    # but this example simply demonstrates how this would work if you have a series requests that fire one at a time.
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


if __name__ == "__main__":
    asyncio.run(main())