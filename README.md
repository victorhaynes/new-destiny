> *“...I ain't got time to bleed.”*
>
> — **Malcom Graves**
# Welcome to `New Destiny`
```
The hardest part of being a 3rd party Riot dev is waiting for production approval, the second hardest part is sorting your rate limiting solution.
```
- `New Destiny` is an easy to use, unpinionated, async OK, fast, scalable, interpretable rate limiting solution for the Riot Games API (currently for League of Legends only) built on `Python`, `asyncio`, and `Redis`.
- `New Destiny` is responsible for respecting the communicated Riot API rate limits.
- _You_ are responsible for protecting your environment variables. Do not expose your `ND_RIOT_API_KEY` to anyone not involved with your project, including Users and Github/source control.
- Plays nice with and without Docker.
- [GitHub](https://github.com/victorhaynes/new-destiny)
- [PYPI](https://pypi.org/project/new-destiny/)

## User Expectations
- Basic willingness to respect the Riot API standards
- Basic Python knowledge
- Basic asynchronous programming understanding
- Basic understanding of Redis (TLDR it is a key-value pair in-memory database that supports TTLs)
- Read Riot's documentation for their API ❗️ Then read it again❗️
- If you have fundamental questions about how the API works you seek answers in the (un?)official Riot `Third Party Developer Community` discord.

## Simple Configuration
`New Destiny` requires environment variables to function. It also requires access to a Redis instance:
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
- `ND_ENABLE_METRICS` takes an optional integer value, `0` or `1`, and defaults to `1`. New Destiny records rate-limit exception counters by default; set it to `0` when you do not need dashboard or traffic-visualization data and want your Redis keyspace easier to inspect.
- `ND_LOG_LEVEL` takes a required integer from 0 to 3:
    - `0`: no New Destiny logging.
    - `1`: API and network errors, plus unexpected HTTP `404` responses.
    - `2`: level 1 plus rate-limit events, internal rate-limit blocks, and expected Spectator no-active-game responses.
    - `3`: all level 2 events plus successful rate-limit checks and outbound Riot URLs.
  Error and debug logs can expose PUUIDs, response headers, response bodies, and URLs to whoever has access to your server logs. New Destiny does not include your API key in its own log output. `ND_DEBUG` is obsolete and is not supported.

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
ND_ENABLE_METRICS=1
ND_LOG_LEVEL=3
```
In the rare case where Riot has given you heightened allowances you can configure your custom `Application Rate Limits` and window durations **using time in seconds--NOT minutes**. You are not allowed to use custom limits if you are not in production mode:
```bash
# Instead of the Application Rate Limit being the default 500/10s and 30,000/10m
# This is specifying 900/s and 60,000/3m
# And just because you specify this doesn't mean Riot will give you this throughput
ND_RIOT_API_KEY="RGAPI-ABC-123"
ND_REDIS_URL="localhost"
ND_REDIS_PORT=6379
ND_LOG_LEVEL=3
ND_PRODUCTION=1
ND_CUSTOM_SECONDS_LIMIT=900
ND_CUSTOM_SECONDS_WINDOW=1
ND_CUSTOM_MINUTES_LIMIT=60000
ND_CUSTOM_MINUTES_WINDOW=180
```

# Quick Start

This is the basic integration/usage path: configure a shared Redis instance, use
the Application Rate Limits Riot allocated your key, and pass a properly constructed Riot API URL through `perform_riot_request()`. This is not a guide on how to use the Riot API in general.

### 1. Install

```sh
python -m pip install new-destiny
```

### 2. Configure

Create an `.env` file in your application directory. You probably do not want to expose this to SCM/GitHub.

```bash
ND_RIOT_API_KEY="RGAPI-ABC-123"
ND_PRODUCTION=0
ND_REDIS_URL="localhost"
ND_REDIS_PORT=6379
ND_ENABLE_METRICS=1
ND_LOG_LEVEL=1
```

Use `ND_PRODUCTION=1` only with a Production API Key. If you do not have a production key use `ND_PRODUCTION=0`. Do not add custom rate
limits unless Riot has explicitly allocated them to your key.

### 3. Make a request

```py
import asyncio
import certifi
import httpx
import redis.asyncio as redis
import ssl

from new_destiny.riot_get_request import perform_riot_request
from new_destiny.settings.config import ND_REDIS_PORT, ND_REDIS_URL


async def main():
    async_redis_client = redis.Redis(
        host=ND_REDIS_URL,
        port=ND_REDIS_PORT,
        db=0,
        decode_responses=True,
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    endpoint = (
        "https://asia.api.riotgames.com/riot/account/v1/"
        "accounts/by-riot-id/hide%20on%20bush/KR1"
    )

    async with httpx.AsyncClient(verify=ssl_context) as client:
        account = await perform_riot_request(
            riot_endpoint=endpoint,
            client=client,
            async_redis_client=async_redis_client,
        )
    print(account)


if __name__ == "__main__":
    asyncio.run(main())
```

`perform_riot_request()` is the standard request path. It checks all
applicable rate limits in Redis before sending the request. Reuse the same
Redis instance across processes that share a Riot API key and routing value.
Use the Usage section below when you need concurrency, retries,
typing helpers, Spectator handling, or Redis inspection.

# Rate-limit enforcement and Riot throttles

New Destiny **always** checks all known applicable rate limits before making a
request. For a request to reach Riot servers, every applicable preflight check
must pass. There are **four** modeled rate-limit types, each with a corresponding exception:

## 1. Application Rate Limits
### Exception Class: `ApplicationRateLimitExceeded`

Application Rate Limits apply to all requests for a routing value.

- This is essential to your platform-aware or server-aware Riot API key scoped
  limit.
- This is primarily the thing you care about.

## 2. Method Rate Limits
### Exception Class: `MethodRateLimitExceeded`

Method Rate Limits apply to one endpoint for one service and routing value.

- For example, `/lol/match/v5/matches/by-puuid/{puuid}/ids` has a different
  quota/bucket than `/lol/match/v5/matches/{matchId}/timeline`, even though they
  belong to the same service.
- These are generally, but are not always, much higher than your *Application
  Rate Limit*. They should be experienced infrequently in general.
- What Riot calls a "method" others would normally call an "endpoint"

## 3. Service Rate Limits
### Exception Class: `ServiceRateLimitExceeded`

Service Rate Limits apply across one Riot service for one routing value.

- From above, the service would be the entire `Match-V5` series of endpoints
  (or `Summoner-V4`, etc. Think "groups").
- These are issued by Riot as they deem necessary to protect their resources at
  a high level. They apply to everyone/every app that uses their service.
- They are not knowable in advance, but they need to be respected when they do
  happen.

## 4. Unspecified Rate Limits
### Exception Class: `UnspecifiedRateLimitExceeded`

Unspecified Rate Limits are the safe fallback when Riot returns a `429` without
a recognized rate-limit type.

- This does actually happen in real life. It is uncommon, but it needs to be
  respected.

# Request Admission

New Destiny checks the application, method, service, and unspecified fallback
scopes in order. The request is sent only when all of those checks pass. See
the [design philosophy](#what-is-the-design-philosophy-of-new-destiny) for more of the finer implementation details.

# Enforcement and Blocking - General Cases

The exception's `enforcement_type` describes where the rate-limit decision
occurred:

- `internal`: New Destiny stopped the request during preflight because its
  local Redis counters or a previously recorded Redis block said the request
  should not be sent. Riot did not receive that request.
- `external`: the request reached Riot and Riot returned a `429`. New Destiny
  then creates the appropriate temporary Redis block.

Rate-limit debug events include the same `enforcement_type` values. A
`riot_rate_limit_response` or `riot_unexpected_rate_limit` event is
`external`; a `riot_rate_limit_blocked_before_request` event is `internal`.

# Handling "Unspecified" Rate Limits - Edge Cases
Riot can return a `429` status code with an unrecognized or missing
`x-rate-limit-type`. New Destiny treats this as an unspecified,
externally enforced limit. The package records the response's `Retry-After`
value when it is available, writes a temporary Redis block, and raises
`UnspecifiedRateLimitExceeded` with `enforcement_type="external"`.
Subsequent requests are blocked internally until the temporary Redis block
expires. There is a `Spectator-V5` API/service specific exception described below.

# Spectator-V5 API (Service) Specific, Active-Game Bad Behavior - Edge Cases cont.

Regarding the `/lol/spectator/v5/active-games/by-summoner/{encryptedPUUID}` endpoint/method:

The `Spectator-V5` active-game endpoint is intentionally carved out from the
shared unspecified-limit fallback. An unexpected throttle for
`/lol/spectator/v5/active-games/by-summoner` uses a method-and-routing-value
key, such as:

```text
nd:known-unpredictable:block:na1:spectator-v5:lol-spectator-v5-active-games-by-summoner
```

This carve out means an unexpected `na1` Spectator throttle blocks subsequent `na1`
Spectator requests, but does not unnecessarily unrelated block Match-V5 or other Riot
endpoints. The application-wide limiter still applies to all of them.

This is necessary because even when you are within your Application, Method, and Service rate limits for this endpoint, Riot will offten send throttle responses anyways. This seems to be specific to this endpoint and this in a known feature.

This means an unexpected `na1` Spectator throttle blocks subsequent `na1`
Spectator requests, but does not unnecessarily block Match-V5 or other Riot
endpoints. The application-wide limiter still applies to all of them.

The TLDR is it is appropriate to respect the fact that you are getting throttled but there isn't much to be done about it other than wait for it go away and hope it doesn't happen. May I suggest making whatever application you build that uses Specator-V5 be resilliant. Handling exceptions intentionally will serve you well.

# Expected Spectator-V5 `404` - Edge cases cont.

An `404` status code from the Spectator active-game endpoint is the expected
no-active-game result. This is also anti-pattern with the other Riot APIs/endpoints. Typically you only get a 404 when something is not found because it is wrong or outdated--in general is always going to be missing. Specator-V5 gives you a 404 when a player that does exist is not in a game. It is reported as the concise
`riot_expected_empty_response` debug event while other unexpected `404`
responses retain their normal error diagnostics and exception behavior.

## Metrics

New Destiny records raised rate-limit exceptions as best-effort, one-minute
Redis counters by default. Set `ND_ENABLE_METRICS=0` to disable the counters.
These counters are observability data: they do not participate in request
admission or blocking. If recording a metric fails, New Destiny leaves the
original rate-limit exception and request behavior unchanged.

Metrics add temporary keys to the Redis database. Keep them enabled when you
want to answer questions such as, "How many application rate limits did we
experience in the last 12 hours?" or when you are building a dashboard or
other traffic visualization. Set `ND_ENABLE_METRICS=0` if you do not need that
observability data.

The metric key shape is:

```text
nd:metrics:rate-limit:<type>:<routing-value>:<enforcement>[:<service>[:<method>]]:<utc-minute>
```

Every counter includes:

- `type`: `application`, `method`, `service`, or `unspecified`.
- `routing-value`: the Riot routing value, such as `na1` or `americas`.
- `enforcement`: `internal` or `external`.
- `utc-minute`: the UTC minute in which the exception was recorded.

The service and method dimensions follow the scope of the exception:

- Application counters include neither service nor method.
- Service counters include the triggering service.
- Method counters include the triggering service and method.
- Unspecified counters include the service and method context available for the request.

The counter value is the number of raised exceptions for that key during the
UTC minute. Keys expire after approximately 25 hours, so consumers can sum
minute buckets for one-hour, 24-hour, or other views. New Destiny records the
detailed dimensions that are available; the consuming application decides
which dimensions to retain, aggregate, or publish in a dashboard.

# Usage

The examples below cover the finer details of `New Destiny`: one complete request script, concurrent batches, retrying background work, expected Spectator-V5 responses, typing helpers, and Redis inspection. For verbose diagnostics, set `ND_LOG_LEVEL=3` in your `.env` before running them.

```py
# your_project/example.py
from new_destiny.riot_get_request import perform_riot_request
from new_destiny.json_types import expect_dict, expect_string
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

    """
    EXAMPLE 1:
    A simple GET request using New Destiny.
    Let's get Faker's account details.
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

    if account_details is None:
        raise ValueError("Expected account details but Riot returned no content.")
    account_payload = expect_dict(account_details)
    puuid = expect_string(account_payload["puuid"])
    
    """
    Do whatever you want with the response
    """
    print("EXAMPLE 1")
    print("Type:", type(account_details))
    print("PUUID:", puuid)
    print("Response:", account_details)
    print("Time:", time.monotonic() - start_time)
    print("Feelin' lucky?")

    """
    EXAMPLE 2: New Destiny with concurrency.
    Raise first exception (which include RiotRelatedRateLimitException(s)) if any encountered.
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
        # This means New Destiny stopped the request before sending it (internal),
        # or Riot received it and returned a 429 (external).
        # Important!
        # You can also specifically catch: ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
        # These also fall under type RiotRelatedException
        # See: Q&A Design philosophy 'Respect' section for more.
        print(exc)
        print(exc.retry_after)
        pass
    except RiotAPIError as exc:
        # <- Your error handling logic here ->
        # RiotAPIError is raised for non-success API responses that are NOT rate limits.
        # In general this works exactly how you would think it does.
        pass
    except RiotNetworkError as exc:
        # A transient connection, gateway, or Cloudflare failure occurred.
        pass
    except RiotRelatedException as exc:
        # Use this if you want a catch-all for any Riot API related exception.
        # This includes rate-limit, API, and transient network errors.
        pass
    except Exception as exc:
        # If 'exc' exception is not of type RiotRelatedException it has nothing to
        # do with Riot, likely has nothing to do with New Destiny, and is likely your application code
        pass

    """
    EXAMPLE 3: New Destiny with concurrency.
    Suppress but gather any experienced errors.
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
ND_LOG_LEVEL=3
```
```py
from new_destiny.riot_get_request_with_retry import riot_request_with_retry

    """
    EXAMPLE 4: Imagine you have a workflow that requires many requests to build something "whole".
    """
    # Imagine you want the match details for n = LARGE_NUMBER of T1 Faker's matches.
    # For resource pressure and easier error handling, you may not want to fire
    # off n = LARGE_NUMBER requests concurrently.
    # You can use riot_request_with_retry() to retry a request that gets rate limited
    # (raises an exception of type RiotRelatedRateLimitException) up to a total
    # number of attempts (default is 3). This gives a background workflow a
    # retry path without hiding a failure forever.
    # If a request remains rate limited after the configured attempts, the
    # exception propagates to the caller normally. RiotAPIError and other
    # non-retryable exceptions also propagate immediately. RiotNetworkError
    # has its own retry budget.

    # You can still use standard Python/asyncio tools to control concurrency or
    # batch size, but this example simply demonstrates a series of one-at-a-time
    # requests.
    # This function is useful if you have background jobs that interact with the Riot API.
    # This is not the "default" method because it is probably inappropriate to have potential UI users of your application experience retry times
    # if you do choose to expose a UI to users.
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

```py
"""
EXAMPLE 5: Spectator active-game edge case.
A player who is not currently in a game produces an expected 404.
"""
spectator_endpoint = f"https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
try:
    async with httpx.AsyncClient(verify=ssl_context) as client:
        spectator_details = await perform_riot_request(
            riot_endpoint=spectator_endpoint,
            client=client,
            async_redis_client=async_redis_client,
        )
except RiotAPIError as exc:
    # <- Your error handling logic here ->
    # RiotAPIError is raised for non-success API responses that are NOT rate limits.
    # In general this works exactly how you would think it does.
    # IMPORTANT EDGE CASE: when you search for a player who exists but is not
    # currently in a game, the Spectator API returns a 404 instead of a 200
    # with an empty list or dict, or a 204. That differs from the pattern used
    # by the other Riot APIs, but that is how Spectator works.
    # At ND_LOG_LEVEL=2 or higher, New Destiny logs this expected response as
    # a structured no-active-game event instead of noisy error output.
    if exc.status_code == 404:
        spectator_details = None
        print("Riot says this player is not currently in-game.")
    else:
        raise
```

# Running Tests

The unit tests are separate from the live API demo. They do not require a Riot API key or Redis for the current test suite.

From the repository root, use Python 3.12 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Use `python -m pytest -q` when you want the compact summary. The current tests cover the JSON type-narrowing helpers, rate-limit classification and exception fields, and the best-effort metrics counters. Successful runs report test names and pass/fail status rather than making Riot requests or printing application diagnostics.

The live API exercise in `demo.py` is not the test suite. It makes real Riot requests, requires a configured `.env` file and Redis, and is useful for examining rate-limit and concurrency behavior:

```sh
ND_LOG_LEVEL=3 python demo.py
```

`perform_riot_request()` and `riot_request_with_retry()` return a schema-agnostic `RiotResponse` type:
- `dict[str, JSONValue]`
- `list[JSONValue]`
- `None`

If you want typing help despite the fact that `New Destiny` does not tie itself by design to Riot's payload contracts, use the helper functions in `new_destiny.json_types` like `expect_dict()`, `expect_list()`, `expect_string()`, `expect_int()`, etc.

This is a deliberate design choice. `New Destiny` stays schema-agnostic on purpose so the library does not become brittle when Riot adds, removes, or reshapes fields. The runtime stays flexible, and type-checker users can still narrow values when they want to.

If you want less type-checker noise in your application code, a simple option is to narrow once and then cast locally:

```py
from typing import Any, cast

account = cast(dict[str, Any], expect_dict(response))
puuid: str = account["puuid"]
game_name: str = account["gameName"]
```

This keeps `New Destiny` unopinionated while letting your own application decide how strict or relaxed to be about Riot's payload shapes.

Exception payloads follow the same schema-agnostic model:
- `RiotAPIError.message` is a `JSONValue`
- `exc.offending_context` is `RiotOffendingContext | None` with `headers: dict[str, str]` and `body: JSONValue | None`

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
ND_LOG_LEVEL=3
ND_PRODUCTION=0
```
Try using a dumb value for `ND_RIOT_API_KEY` and running the example code. Examine the traceback and you'll notice all kinds of helpful information gets captured. This gets even more helpful when you start experiencing `internally` enforced exceptions (the request was blocked by `New Destiny`) and `externally` enforced exceptions (the request reached Riot and Riot returned a `429`), rather than only general `RiotAPIError`s. See "design philosophy" for more.

# Important
`New Destiny` works best when you configure it to use your actual `Application Rate Limit` values. Just because you can override it does not mean you should. The examples below will illuminate why.

If you are looping through a list of items in batches, New Destiny atomically enforces the configured limits before requests are sent. When it is configured with the Application Rate Limits Riot gives your key, all callers share the same Redis instance, and no other uncoordinated traffic uses that key, excess requests should be internally blocked. A batch of 1,000 requests against a 50-request limit should therefore produce up to 50 admitted requests and at least 950 internal blocks. Batch size alone should not cause external `429`s; it primarily affects task and resource pressure. External enforcement is the fallback when the limit actually applied by Riot differs from the client model or another source is consuming the same allocation.

## Debugging Scenario 1: Blocked by `New Destiny` (good/respectful/standard scenario) not by Riot.

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
            # with a str value of "internal" or "external". Internal means
            # the request was stopped before it was sent; external means Riot
            # received it and returned a 429.
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

## Debugging Scenario 2: External enforcement: Riot returned a 429 (an intentional misconfiguration)
```sh
# Real Production keys will have limits too high for this example to illustrate
ND_RIOT_API_KEY="USE_A_DEVELOPMENT_OR_PERSONAL_KEY"
ND_PRODUCTION=1
ND_LOG_LEVEL=0 # Turn it off to not clutter the output
ND_CUSTOM_SECONDS_LIMIT=9999 # well above the Dev/Personal limit
ND_CUSTOM_SECONDS_WINDOW=20 # well above the Dev/Personal limit
```

If you want to see the `external` rate limiting behavior, use a Personal or Development API key, set `ND_PRODUCTION=1`, and use intentionally permissive values like `ND_CUSTOM_SECONDS_LIMIT=9999` and `ND_CUSTOM_SECONDS_WINDOW=20`. This deliberately configures New Destiny above the limit allocated to the Riot key, so Riot's server-side API protection becomes the stopgap. The requests can pass New Destiny's local limits and still receive inbound `429` responses from Riot. When that happens, New Destiny raises a specific `RiotRelatedRateLimitException` subclass with an `.enforcement_type="external"` attribute and records a temporary block for subsequent requests. This is a controlled demonstration, not a normal production or even development-appropriate configuration.
```py
# Run the same request batch as Debugging Scenario 1, but with more URLs that will exceed 10/s requests
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
## Debugging Scenario 3: Blocked by Riot first, then `New Destiny` while looping through batches
With the same `.env` config as Example 2:

This example keeps the intentionally permissive configuration from Example 2 and sends each group of 30 concurrently. The first batch can therefore produce multiple external `429`s: every request that passed local preflight may reach Riot before the first external response is observed. Once New Destiny records Riot's throttle, later requests for the affected scope are normally blocked internally until the temporary block expires. That transition from external to internal enforcement is what this example is meant to show.

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
If you are looping through a list of items in batches, New Destiny atomically enforces the configured limits before requests are sent. When it is configured with the Application Rate Limits Riot gives your key, all callers share the same Redis instance, and no other uncoordinated traffic uses that key, excess requests should be internally blocked. A batch of 1,000 requests against a 50-request limit should therefore produce up to 50 admitted requests and at least 950 internal blocks. Batch size alone should not cause external `429`s. External enforcement is the fallback when the limit actually applied by Riot differs from the client model (which again, can be due to edge case misalignments/a lack of perfection) or another source is consuming the same allocation. The metrics keys below let an application count internal and external outcomes separately without requiring New Destiny to assume what the application wants to do with the data.

# Question & Answer

### Who are you?
Victor Haynes, a software engineer and ERP consulting professional.
Or "vanilli." on Discord.
### TLDR
`riot_get_request.py` defines how your application interacts with the Riot API.
`rate_limiter.py` defines how New Destiny interacts with your application.

### What routing values (regions) are supported?
All of them other than China. Riot does not allow us to interact with Chinese data. This is why you never see it on 3rd party applications.

### What services and methods are supported?
In my opinion, most of the important methods.  
All methods for `League-V4`, `League-EXP-V4`, `Champion-V3`, `Clash-V1`, `Lol-Challenges-V1`, `Lol-Status-V4`, `Spectator-V5`, `Match-V5`, and `Champion-Mastery-V4`.

`Summoner-V4`:
Everything except /fulfillment/v1/summoners/by-puuid/{rsoPUUID}
This is off-limits. It will be added when I get around to integrating RSO into my own application.
If there is high demand I may prioritize this.

`ACCOUNT-V1` supports:
- /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
- /riot/account/v1/accounts/by-puuid/{puuid}
- /riot/account/v1/accounts/by-puuid/{puuid}/active-shards
- /riot/account/v1/active-shards/by-game/{game}/by-puuid/{puuid}
- /riot/account/v1/region/by-game/{game}/by-puuid/{puuid}

If you want more methods or LoL-related services supported,
feel free to request them and I'll do my best to add them or open a pull request.

### What does `routing_value` mean?
`routing_value` is the subdomain in the generic web-development sense: the
first hostname component in a Riot API URL. For example, the routing value is
`na1` in a platform endpoint such as
`https://na1.api.riotgames.com/lol/summoner/v4/...`, and `americas` in a
routing endpoint such as `https://americas.api.riotgames.com/riot/account/v1/...`.

Riot's documentation incorrectly calls this a region. The third-party
developer community often calls it a platform router. New Destiny exposes the
clearer name `routing_value` so the field describes its role in rate limiting.

New Destiny keeps the three pieces of request context separate:

- `routing_value`: where Riot routes the request, such as `na1` or `americas`.
- `service`: the API family, such as `SUMMONER-V4` or `ACCOUNT-V1`.
- `method`: the endpoint path, such as `/riot/account/v1/accounts/by-puuid`.

Rate-limit exceptions only include the fields relevant to the limit that was
triggered. Application exceptions include application window data; method
exceptions include the method and its service; service exceptions include the
service; and unspecified exceptions include the service and method context
available for that request. Every rate-limit exception includes
`enforcement_type` and `routing_value`.

### Where do your rate limit values come from?

The Application Rate Limits are explained above.
For the Method Rate Limits examine the `RATE_LIMITS_BY_SERVICE_BY_METHOD` variable in `rate_limit_helpers.py` file.
As for where they come from, these are representations of what the Riot API actually returns in its headers when you hit a method 
(what we think of as endpoints) and they are hard coded. Eventually these will be synced/explicitly checked at initialization but not for now.
These values changing substantially are an edge case I have not experienced in years.

If Riot's actual behavior is lower than the behavior represented in the package, you might see an inbound status code `429` response on the first request or concurrent batch to hit Riot's API. That means the request reached Riot and Riot blocked it, rather than New Destiny blocking it first (see examples for exactly how this works).
`New Destiny` will then block other outbound requests for the affected scope for the duration of the inbound `retry-after` header when Riot provides one.
If the rate limits change and they are higher then you lose the delta in throughput.
But again I have not seen that actually happen and this edge case will eventually be handled.

Anyway and notably, not only are rate limits enforced by routing value, they can vary by routing value for the same method and this is not well documented.
If you log onto your developer account and click on "APPS" you would think the rate limits shown would be the Method Rate Limits for the given methods within a service but they are not.
They are directionally correct but they are totally unreliable. 
That is why I pulled my rate limit values from actual response headers and not from there.

### What about Service Rate Limits?
 
`New Destiny` handles them as they are served.
It's unknowable when they’ll occur, and they do **not** come with `retry-after` headers. You can think of them as outages beyond our control.
There is a default retry time of 68 seconds if a `ServiceRateLimitExceeded` exception occurs.
If you want to be less cautious than I am, you can change the `SERVICE_BLOCK_DURATION` value in `rate_limiter.py` 
to any integer greater than 0 in your own installation.

### Does this work with `insert_name` `Python` API framework?
First of all, you can use this in just a python script file if you want.
But if your web framework allows asynchronous code to be executed and awaited properly inside of
its endpoint functions/view functions/controllers then yes.
There is a production FastAPI application (https://winrates.gg) running this package for example.


### What is `Redis`?
An in-memory key/value pair database that is extremely fast. Notably, it supports TTLs (Time to Live) so things automatically drop out of it when configured correctly.
Good for data that does not need to be durable. 
So while I would not store a User profile in `Redis` I would and do store rate limit keys (the identifier that ties an outgoing request to the applicable count/limit).
If `Redis` crashes, you delete the keys, or you restart it etc. the worst case scenario is you will be out of sync with Riot's (the source of truth)
version of your request count vs the allotted limit for a given time span. The normal application counter windows are short and reset naturally; custom windows can be longer if Riot has allocated them to you. In practice & in the worst case scenario losing your redis data would mean that New Destiny will be overly permissive for up to about 10 minutes (the longest window Riot keeps track of). So if you are continually generating traffic you can see more `externally` enfroced rate limits than you otherwise would but once they are experienced they will be respected and you can regain normal behavior/protection.

### What is the design philosophy of `New Destiny`?
`Respect`, `interpretability`, and `unopinionated`

On `respect`:

The rate limiter is checked and or incremented **before** a request goes out to Riot. The goal is to prevent `429`s when the configured model matches the limits Riot gives your key, and to handle them respectfully when Riot returns one. `internal` means New Destiny stopped the request; `external` means Riot received the request and returned a `429`.

New Destiny models the high-level rules Riot communicates in its API docs. It
cannot observe every implementation detail or stay synchronized with Riot's
counters in real time, so some misalignment is natural. The package uses the
information Riot provides, applies sensible defaults, and falls back safely
when it cannot classify a throttle. This is why a small amount of external
enforcement is possible even though the normal path is internally enforced.

On `interpretability`:

It is very easy to connect to your `Redis` instance and see what is going on.
Every `New Destiny` related `Redis` key begins with the `nd:` namespace. Keys
use the general shape
`nd:<scope>:<kind>:<routing-value>[:<service>[:<method>[:<window>]]]`.
Special behavior is represented by a semantic scope, such as
`known-unpredictable`, rather than by a manually maintained schema version.

The complete key families are:

```text
# Application-wide counters and Riot/application blocks
nd:application:count:<routing-value>:seconds
nd:application:count:<routing-value>:minutes
nd:application:block:<routing-value>

# Communicated endpoint and service limits
nd:method:count:<routing-value>:<service>:<method>:seconds
nd:method:count:<routing-value>:<service>:<method>:minutes
nd:method:block:<routing-value>:<service>:<method>
nd:service:block:<routing-value>:<service>

# Unexpected 429 fallback blocks
nd:unspecified:block:<routing-value>:shared
nd:known-unpredictable:block:<routing-value>:<service>:<method>

# Observed rate-limit exception counters, retained for approximately 25 hours
nd:metrics:rate-limit:<type>:<routing-value>:<enforcement>[:<service>[:<method>]]:<utc-minute>
```

`<routing-value>` is the routing value token derived from the Riot hostname.
`<method>` is a lowercase, hyphenated token derived from the configured Riot
method path. The `known-unpredictable` family is currently used for the
Spectator active-game method; its method-and-routing-value scope prevents that
endpoint's unusual throttles from blocking unrelated traffic.
The metrics family is created only when metrics are enabled and a rate-limit exception is raised. Its
semantics are documented in the [Metrics](#metrics) section.
For a given outbound request you can see what rate limits apply to the request, how long the current count is valid for (the key's TTL) and what your current count is.
Additionally, all of the New Destiny specific errors tell you what endpoint caused the error and they capture useful metadata about the request.

`New Destiny` was created to solve my own problem. I had a generic rate limiting solution in place for my own application. 
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


### What is a `UnspecifiedRateLimitExceeded` error?
Whatever Riot cooked burnt so this is a fail-safe that prevents you from continuing to slam 
them after getting a `429` that cannot be attributed to an Application, Method, or Service rate limit.
It is rare, but sometimes Riot returns a `429` without enough information to classify it. This exception is externally enforced because Riot returned the `429`; the fallback block is New Destiny's respectful response to it.
