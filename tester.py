# your_project/example.py
from src.new_destiny.riot_get_request import perform_riot_request
from src.new_destiny.riot_get_request_with_retry import riot_request_with_retry
from src.new_destiny.settings.config import ND_REDIS_PORT, ND_REDIS_URL
from src.new_destiny.rate_limit_exceptions import RiotRelatedRateLimitException, RiotAPIError, RiotRelatedException
from src.new_destiny.utilities import custom_print
# You can catch these exception subclasses if you want to but it is probably unnecessary:
# from new_destiny.rate_limit_exceptions import ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
import ssl
import httpx
import certifi 
import redis
import asyncio
import time # Not a requirement, just for logging purposes

ssl_context = ssl.create_default_context(cafile=certifi.where())
async_redis_client = redis.asyncio.Redis(host=ND_REDIS_URL, port=ND_REDIS_PORT, db=0, decode_responses=True)

async def main():
    # Example application code:
    # do_some_work() ...

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
                        raise res  # Unknown exception


    print("BEHAVIOR EXAMPLE")
    print("Type:", type(batch_results))
    print("Length:", len(batch_results))
    print("Type of first element", type(batch_results[0]))
    print("Time:", time.monotonic() - start_time)

if __name__ == "__main__":
    asyncio.run(main())