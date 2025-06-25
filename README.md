    ...I ain't got time to bleed.
# Welcome to `New Destiny`
- The hardest part of being a 3rd party Riot dev is waiting for production approval, the second hardest part is sorting your rate limiting solution.
- `New Destiny` is an easy to use, fully async, fast, scalable, interpretable rate limiting solution for the Riot Games API (currently for League of Legends only) built on `Python`, `asyncio`, and `Redis`.
- `New Destiny` is responsible for respecting the communicated Riot API rate limits.
- _You_ are responsible for protecting your environment variables. Do not expose your `ND_RIOT_API_KEY` to anyone not involved with your project, including Users and Github/source control.
- Plays nice with and without Docker.
- [GitHub](https://github.com/victorhaynes/new-destiny)
- [PYPI](https://pypi.org/project/new-destiny/)

# User Expectations
- Basic willingness to respect the Riot API standards
- Basic python knowledge
- Basic asynchronous programming understanding
- Basic understanding of Redis (TLDR it is a key-value pair in-memory databse that supports TTLs)
- Read Riot's documentation for their API ❗️ Then read it again❗️
- If you have fundamental questions about how the API works you seek answers in the (un?)official Riot `Third Party Developer Community` discord.

# Simple Configuration
`New Destinity` requires environment variables to function. It also requires access to a Redis instance:
- `ND_RIOT_API_KEY` takes a string value: enter your Riot-issued API key. If using a development key be sure to keep it updated.
- `ND_PRODUCTION` takes an integer value 0 or 1: specify whether or not you are using a **Production API Key**. As you know from the Riot API Docs your **Application Rate Limit** differs depending on what kind of key you have:
    - `ND_PRODUCTION=0`: Development & Personal API Keys:
        - 20 requests, per 1 second, per routing value
        - 100 requests, per 2 minutes or 120 seconds, per routing value
    - `ND_PRODUCTION=1`: Production API Keys start at:
        - 500 requests, per 10 seconds, per routing value
        - 30,000 requests, per 10 minutes or 600 seconds, per routing value
    - `ND_PRODUCTION=1`: with custom settings: If you have higher limits you can specify them with the optional:
        - `ND_CUSTOM_SECONDS_LIMIT` and `ND_CUSTOM_SECONDS_WINDOW`
        - `ND_CUSTOM_MINUTES_LIMIT` and `ND_CUSTOM_MINUTES_WINDOW`
- `ND_REDIS_URL` takes a string value: enter the address your `Redis` instance is running on.
Can be an actual address, "localhost", or "service_name" if your application code & `Redis` are in the same Docker compose stack.
- `ND_REDIS_PORT` takes an integer value: enter the port number `Redis` is listening to.
- `ND_DEBUG` takes an integer value 0 or 1: decide if you want the rate limiter to log what it is attempting to do/experiencing. Very useful if you are experiencing unexpected behavior in your application code or from the Riot API (which does happen). Highly recommend you set this to 1 until you are comfortable with your code and mine. Note debug mode is safe to use in an production environment. It **will** expose to whoever has access to your server logs: things like player PUUIDs (which are encrypted and have basically no malintent usecase), response headers, resesponse bodies, show what URL is being tried, along with the current state of your rate limiter(s). But `New Destiny` will **not** expose your API key.

## Example Configuration
Use an `.env` file to declare these values:

```bash
# This file is part of your application's code base.
# Example:
# your_project/.env
ND_RIOT_API_KEY="RGAPI-ABC-123"
ND_PRODUCTION=1
ND_REDIS_URL="your_redis_address_or_docker_service_name"
ND_REDIS_PORT=123
ND_DEBUG=1
```
In the rare case where Riot has given you heightened allowances you can configure your custom `Application Rate Limits` and window durations **using time in seconds--NOT minutes**. You are not allowed to use custom limits if you are not in production mode:
```bash
# Instead of the Application Rate Limit being the default 500/10s and 30,000/10m
# This is specifying 900/s and 60,000/3m
# And just because you specify this doesn't mean you Riot will give you this throughput
ND_RIOT_API_KEY="RGAPI-ABC-123"
ND_REDIS_URL="localhost"
ND_REDIS_PORT=6379
ND_DEBUG=1
ND_PRODUCTION=1
ND_CUSTOM_SECONDS_LIMIT=900
ND_CUSTOM_SECONDS_WINDOW=1
ND_CUSTOM_MINUTES_LIMIT=60000
ND_CUSTOM_MINUTES_WINDOW=180
```

# Usage
```sh
pip install new-destiny
```
```bash
# your_project/.env
# Step 1) setup your .env file, use this setting along with your other config
ND_DEBUG=1
```
```py
# your_project/example.py
from new_destiny.riot_get_request import perform_riot_request
from new_destiny.settings.config import ND_REDIS_PORT, ND_REDIS_URL
from new_destiny.rate_limit_exceptions import RiotRelatedRateLimitException, RiotAPIError, RiotRelatedException
# You can catch these exception subclasses if you want to but it is probably unnecessary:
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

    """
    EXAMPLE 1:
    A simple GET request using New Destiny
    """
    start_time = time.monotonic()
    async with httpx.AsyncClient(verify=ssl_context) as client:
        # Note: You may only use actual, properly formatted Riot API Endpoints.
        # Otherwise New Destiny will not know what ratelimit applies to the request.
        region = "asia"
        gamename = "hide on bush"
        tagline = "KR1"
        account_endpoint = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gamename}/{tagline}"
        account_details = await perform_riot_request(
            riot_endpoint=account_endpoint,
            client=client,
            async_redis_client=async_redis_client
        )
    
    """
    Do whatever you want with the response
    """
    print("EXAMPLE 1")
    print("Type:", type(account_details))
    print("Response:", account_details)
    print("Time:", time.monotonic() - start_time)
    print("Feelin' lucky?")

    """
    EXAMPLE 2: New Destiny with concurrency.
    Raise first exception (which include RiotRelatedRateLimitException(s)) if any encoutnered.
    """
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

    """
    EXAMPLE 3: New Destiny with concurrency.
    Supress but gather any experienced errors.
    """
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
            # Potentially raise the Exception of other types, filter it out etc,
            pass

    print("EXAMPLE 3")
    print("Type:", type(batch_results))
    print("Length:", len(batch_results))
    print("Type of first element:", type(batch_results[0]))
    print("Time:", time.monotonic() - start_time)
    print("Dead man walkin'.")

if __name__ == "__main__":
    asyncio.run(main())
```
For the next example try this `.env` file configuration so I can illuminate how the `riot_request_with_retry()` function works.
```bash
# your_project/.env
# This how you would set a very low custom Application Rate limit
ND_PRODUCTION=1
ND_CUSTOM_SECONDS_LIMIT=5
ND_CUSTOM_SECONDS_WINDOW=10
ND_DEBUG=1
```
```py
from new_destiny.riot_get_request_with_retry import riot_request_with_retry

    """
    EXAMPLE 4: Imagine you have a workflow that requires many requests to build something "whole".
    """
    # Imagine you want the match details for n = LAGE_NUBMER of T1 Faker's matches.
    # For either resource or rate limit concerns you do not want to fire off n = LAGE_NUBMER requests concurrently.
    # You can use riot_request_with_retry() to automatically retry a request that gets rate limited 
    # (raises an exception of type RiotRelatedRateLimitException)
    # up to a total number of attempts (default is 3). This protects your workflow against rate limit exceptions.
    # If a request gets rate limited more than the # of attempts specified the exception will propogate to the context of the caller like normal. 
    # You can catch it with try/except. Other types of Exceptions will get raised/propagate immediately and do not get retried.

    # You can still use standard python/asyncio tools to control the level of concurrecy or batch size
    # but this example simply demonstrates how this would work if you have a series requests that fire one at a time.
    # This function is useful if you have background jobs that interact with the Riot API.
    # This is not the "default" method because it is probably inappropriate to have potential UI users of your application experience retry times
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
```
```sh
# To run this code:
python example.py
```
```sh
# To examine what is going on inside Redis, first open the Redis CLI where your Redis server is running:
redis-cli
```
```
keys *
get key_name
TTL key_name
```
# Debugging / Examining The Behavior
```bash
ND_RIOT_API_KEY="RGAPI-ABC-123"
ND_DEBUG=1
ND_PRODUCTION=0
```
Try using a dumb value for `ND_RIOT_API_KEY` and running the example code. Examine the traceback and you'll notice all kinds of helpful information gets captured. This gets even more helpful when you start experiencing `internally` (blocked by `New Destiny`) and `externally` (Blocked by Riot/`429` was actually received) enforced `RiotRelatedRateLimitException` errors and not just general `RiotAPIError`s. See "design philosophy" for more.

### Important:
`New Destiny` works best when you configure it to use your actual `Application Rate Limit` values. Just because you can override it does not mean you should. The examples below will illuminte why.

 This package also works best when you size your concurrent request batches appropriately relative to the size of your rate limits. If you know you're limited to 10/s or 500/10s don't spawn 1000 concurrent requests. `New Destiny` protects almost flawlessly for **synchronous** (one at a time) requests. However edge cases exist where you can experience multiple inbound `429`s during a batch of **concurrent** requests. The larger your batch size is relative to your limits the greater chance there is for this. If you have N total items split into M batches you can experience multiple inbound `429`s within a batch and this is not ideal, but you will **not** experience more `429s` after the first batch than ran into them.

### Example 1: Blocked by `New Destiny` (good/respectful/standard scenario) not by Riot.

If you want to see the actual `internal` rate limiting behavior in action set `ND_PRODUCTION=0` and simply spawn a lot of concurrent `perform_riot_request()`. Try doing N = 25 concurrently and view the output. This should easily exceed the Personal & Development API key rate limits and this will protect you from slamming Riot N - M times because the straw that will break the proverbial camel's back never gets sent. It gets blocked internally.
```py
    start_time = time.monotonic()
    match_endpoints = [
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
    ]

    start_time = time.monotonic()
    async with httpx.AsyncClient(verify=ssl_context) as client:
        batch_results = await asyncio.gather(
            *[perform_riot_request(
                riot_endpoint=endpoint,
                client=client,
                async_redis_client=async_redis_client)
                for endpoint in match_endpoints]
        , return_exceptions=True)
    
    for i, res in enumerate(batch_results):
        if not isinstance(res, Exception):
            print(i+1, "- got real data")
        else:
            # RiotRelatedRateLimitException(s) have an .enforcement_type attribute 
            # with a str value of "internal" or "external"
            t = res.enforcement_type + "ly blocked"
            if "internal" in t:
                custom_print(t, "yellow")
            elif "external" in t:
                custom_print(t, "red")
            else: 
                raise res # Some other exception is at play


    print("BEHAVIOR EXAMPLE")
    print("Type:", type(batch_results))
    print("Length:", len(batch_results))
    print("Type of first element", type(batch_results[0]))
    print("Time:", time.monotonic() - start_time)
```

### Example 2: Blocked by Riot (or a "leakage" scenario)
```sh
# Real Production keys will have limits too high for this example to illustrate
ND_RIOT_API_KEY="USE_A_DEVELOPMENT_OR_PERSONAL_KEY"
ND_PRODUCTION=1
ND_DEBUG=0 # Turn it off to not clutter the output
ND_CUSTOM_SECONDS_LIMIT=9999 # well above the Dev/Personal limit
ND_CUSTOM_SECONDS_WINDOW=20 # well above the Dev/Personal limit
```

If you want to see the `external` rate limiting behavior use a Personal or Development API key, set `ND_PRODUCTION=1`, and use high values like `ND_CUSTOM_SECONDS_LIMIT=9999` and `ND_CUSTOM_SECONDS_WINDOW=20`. If you actually exceed whatever your real assigned rate limit(s) is/are you will receive inbound `429` responses from Riot and they will raise a specific `RiotRelatedRateLimitException` exception subclass with an `.enforcement_type="external"` attribute. This is the behavior within a batch.
```py
# Run the same code as Example 1 but with more URLs that will exceed 10/s requests
    match_endpoints = [
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
    ]
```
### Example 3: Blocked by Riot first, then `New Destiny` while looping through baches
With the same `.env` config as Example 2:
```py
    start_time = time.monotonic()
    match_endpoints = [
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658126453",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658058516",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658013757",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7657080042",
        "https://asia.api.riotgames.com/lol/match/v5/matches/KR_7658105279",
    ]

    start_time = time.monotonic()
    async with httpx.AsyncClient(verify=ssl_context) as client:
        for batch_start in range(0, len(match_endpoints), 30):
            current_batch = match_endpoints[batch_start:batch_start + 30]
            
            batch_results = await asyncio.gather(
                *[perform_riot_request(
                    riot_endpoint=endpoint,
                    client=client,
                    async_redis_client=async_redis_client)
                    for endpoint in current_batch],
                return_exceptions=True
            )

            for i, res in enumerate(batch_results):
                index = batch_start + i + 1
                if not isinstance(res, Exception):
                    print(index, "- got real data")
                else:
                    t = getattr(res, 'enforcement_type', 'unknown') + "ly blocked"
                    if "internal" in t:
                        custom_print(t, "yellow")
                    elif "external" in t:
                        custom_print(t, "red")
                    else: 
                        raise res  # Some other exception is at play


    print("BEHAVIOR EXAMPLE 3")
    print("Type:", type(batch_results))
    print("Length:", len(batch_results))
    print("Type of first element", type(batch_results[0]))
    print("Time:", time.monotonic() - start_time)
```
If you are looping through a list of items in batches one batch may experierence multiple `429`s but subsequent batches will get blocked internally. **Some amount of leakage is natural** as my counters and TTLs are not perfectly in sync with Riot. But through standard configuration and sensible usage this is not much of a problem. My own 3rd party application is running `New Destiny` with automated background jobs and it is in good standing. The vast majority of rate limit exceptions I experience are internally enforced.

# Question & Answer

## Who are you?
Victor Haynes, a software engineer and ERP consulting professional.
Or "vanilli." on Discord.
## TLDR
`riot_get_request.py` defines how your application interacts with the Riot API.
`rate_limiter.py` defines how New Destiny interacts with your application.

## What routing values (regions) are supported?
All of them other than China. Riot does not allow us to interact with Chinese data. This is why you never see it on 3rd party applications.

## What services and methods are supported?
In my opinion, most of the important methods.  
All methods for `League-V4`, `League-EXP-V4`, `Match-V5`, and `Champion-Mastery-V4`.

`Summoner-V4`:
Everything except /fulfillment/v1/summoners/by-puuid/{rsoPUUID}
This is off-limits. It will be added when I get around to integrating RSO into my own application.
If there is high demand I may prioritize this.

`ACCOUNT-V1` supports:
- /riot/account/v1/accounts/by-riot-id
- /riot/account/v1/accounts/by-puuid
- /riot/account/v1/active-shards/by-game

If you want more methods or LoL-related services supported,
feel free to request them and I'll do my best to add them or open a pull request.

## Where do your rate limit values come from?

The Application Rate Limits are explained above.
For the Method Rate Limits examine the `RATE_LIMITS_BY_SERVICE_BY_METHOD` variable in `rate_limit_helpers.py` file.
As for where they come from, these are representations of what the Riot API actually returns in its headers when you hit a method 
(what we think of as endpoints) and they are hard coded. Eventually these will be synced/explicitly checked at initialization but not for now.
These values changing substantially are an edge case I have not experienced in years.

If rate limits do change and they are lower, `New Destiny` will still function/protect your app you just might actually see an inbound status code `429` response
on the 1st request/concurrent batch to hit Riot's API which means Riot blocked you not `New Destiny` (see examples for exactly how this works).
`New Destiny` will still block other outbound requests for the duration of the inbound `retry-after` header.
If the rate limits change and they are higher then you lose the delta in throughput.
But again I have not seen that actually happen and this edge case will eventually be handled.

Anyway and notably, not only are rate limits enforced by routing value they can vary by routing value for the same method and this is not well documented.
If you log onto your developer account and click on "APPS" you would think the rate limits shown would be the Method Rate Limits for the given methods within a service but they are not.
They are directionally correct but they are totally unreliable. 
That is why I pulled my rate limit values from actual response headers and not from here.

## What about Service Rate Limits?
 
`New Destiny` handles them as they are served.
It's unknowable when they’ll occur, and they do **not** come with `retry-after` headers. You can think of them as outages beyond our control.
There is a default retry time of 68 seconds if a `ServiceRateLimitExceeded` exception occurs.
If you want to be less cautious than I am, you can change the `SERVICE_BLOCK_DURATION` value in `rate_limiter.py` 
to any integer greater than 0 in your own installation.

## Does this work with `insert_name` `Python` API framework?
First of all, you can use this in just a python script file if you want.
But if your framework allows asynchronous code to be executed and awaited properly inside of
its endpoint functions/view functions/controllers then yes.
There is a production FastAPI application running this package for example.


## What is `Redis`?
An in-memory key/value pair database that is extremely fast. Notably, it supports TTLs (Time to Live) so things automatically drop out of it when configured correctly.
Good for data that does not need to be durable. 
So while I would not store a User profile in `Redis` I would and do store rate limit keys (the identifier that ties an outgoing request to the applicable count/limit).
If `Redis` crashes, you delete the keys, or you restart it etc. the worst case scenario is you will be out of sync with Riot's (the source of truth) 
version of your request count vs the allotted limit for a given time span. Limits are typically only applied to up to 10 minute windows so they do reset naturally.
See next answer.

## What is the design philosphy of `New Destiny`?
`Respect`, `interpretability`, and `unopinionated`

On `respect`:

If you examine the source code you'll notice that: 1) the rate limiter is checked and or incremented **before** request goes out to Riot and 
2) there are `internal` and `external` `enforcement_types` for the `RiotRelatedRateLimitException` series of errors. 
In a perfect world you would only ever experience internally-enforced rate limits.
That means `New Destiny` prevented you from ever actually exceeding the rate limit for the request you are making (even by 1 request). 
The goal is to both prevent `429` and handle `429`s, rather than just handling them once they happen.
But staying perfectly on top of whatever Riot is cooking is challenging so real in-bound `429`s will occasionally happen. 
This is nothing to panic about as pointed out in the examples.
Others deal with the `429`s as they come and do not bother trying to prevent them in the first place. I try to prevent them.

On `interpretability`:

It is very easy to connect to your `Redis` instance and see what is going on.
Every `New Destiny` related `Redis` key begins with a `nd_` prefix.
For a given outbound request you can see what rate limits apply to the request, how long the current count is valid for (the key's TTL) and what your current count is.
Additionally, all of the New Destiny specific errors tell you what endpoint caused the error and they capture useful metadata about the request.

This was created to solve my own problem. I had a rate limiting solution in place for my own application. 
It functioned well enough but it was a "black box". If you're curious about what is happening to your requests `New Destiny` probably gives you a way to figure it out.
Especially in debug mode.

On `unopinionated`:

Other than the fact that you have to use `Python` and `Redis` this package can work in more than one way. 
It plays nicely with standard `asyncio` syntax.
Other packages move what I consider should-be application logic into the rate limiting solution.
Rather than relying on a package full of custom methods like `get_my_summoner()` and `my_summoners_matches()` that have their own assumptions, 
you decide what you want and how you want it to work by simply building a URL and using `asyncio` to deal with as much or as little concurrency as you want.
You can decide what errors are ok and what are not, you can decide if one request depends on another etc.

In short, `New Destiny` stays out of your way and lets you own your logic.


## What is a `UnspecifiedRateLimitExceeded` error?
Whatever Riot cooked burnt so this is a fail-safe that prevents you from continuing to slam 
them after getting a `429` that cannot be attributed to an Application, Method, or Service rate limit.
It is rare but sometimes you get rate limited by Riot without explanation.
