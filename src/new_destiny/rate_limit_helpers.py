from urllib.parse import urlparse, unquote
import re
import json
import gzip

###### Helper Functions ######
###### Helper Functions ######
###### Helper Functions ######
def derive_riot_service(riot_endpoint: str) -> str:
    if isinstance(riot_endpoint, str):
        path = urlparse(riot_endpoint).path.lower()
    elif isinstance(riot_endpoint, ParseResult):
        path = riot_endpoint.path.lower()    
    else:
        raise TypeError(f"Expected a str or ParseResult, got {type(riot_endpoint)}")
    
    if "/lol/summoner/v4" in path or "/fulfillment/v1" in path:
        return "SUMMONER-V4"
    elif "/lol/platform/v3" in path:
        return "CHAMPION-V3"
    elif '/lol/league/v4' in path:
        return "LEAGUE-V4"
    elif "/lol/league-exp/v4" in path:
        return 'LEAGUE-EXP-V4'
    elif "/lol/clash/v1" in path:
        return "CLASH-V1"
    elif "/riot/account/v1" in path:
        return "ACCOUNT-V1"
    elif "/lol/match/v5/" in path:
        return "MATCH-V5"
    elif "/lol/status/v4" in path:
        return "LOL-STATUS-V4"
    elif "/lol/challenges/v1" in path:
        return "LOL-CHALLENGES-V1"
    elif "lol/champion-mastery/v4" in path:
        return "CHAMPION-MASTERY-V4"
    elif "/lol/spectator/v5" in path:
        return "SPECTATOR-V5"
    else:
        raise TypeError("No appropriate Riot Service could be determined.")

def derive_riot_method_config(
    riot_endpoint: str,
    router: str,
    service: str
) -> dict:
    """
    Find the rate‐limit config for a given Riot API URL + service,
    using the provided router (subdomain) to pick the right limits.

    Returns a dict:
        {
          "method":   ...,
          "pattern":  ...,
          "router":   "<your router>",
          "seconds":  {"limit": X, "window": Y},
          "minutes":  {"limit": A, "window": B},
        }

    Raises ValueError if service/method/router is unknown.
    """
    rate_limits = RATE_LIMITS_BY_SERVICE_BY_METHOD

    # normalize path
    parsed = urlparse(riot_endpoint)
    path = unquote(parsed.path or riot_endpoint)
    if not path.startswith("/"):
        path = "/" + path

    # look up service
    if service not in rate_limits:
        raise ValueError(f"Unknown service: {service}")

    # find matching method
    for method_cfg in rate_limits[service]:
        if re.match(method_cfg["pattern"], path):
            routers_cfg = method_cfg.get("routers", {})

            # pick your router's limits or fallback to default
            if router in routers_cfg:
                limit_cfg = routers_cfg[router]
            elif "default" in routers_cfg:
                limit_cfg = routers_cfg["default"]
            else:
                raise ValueError(
                    f"No rate‐limit entry for router '{router}' "
                    f"in method {method_cfg['method']}"
                )

            return {
                "method":  method_cfg["method"],
                "pattern": method_cfg["pattern"],
                "router":  router,
                "seconds": limit_cfg.get("seconds", {}),
                "minutes": limit_cfg.get("minutes", {}),
            }

    raise ValueError(f"No matching method for URL: {path} in service: {service}")


LOL_PLATFORM_ROUTERS = (
    "na1", "br1", "la1", "la2", "euw1", "eun1", "tr1", "ru",
    "me1", "jp1", "kr", "oc1", "sg2", "tw2", "vn2",
)
LOL_REGIONAL_ROUTERS = ("americas", "asia", "europe")
LOL_MATCH_ROUTERS = LOL_REGIONAL_ROUTERS + ("sea",)


def build_router_limits(
    routers,
    *,
    seconds_limit: int,
    seconds_window: int,
    minutes_limit: int | None = None,
    minutes_window: int | None = None
) -> dict:
    return {
        router: {
            "seconds": {"limit": seconds_limit, "window": seconds_window},
            "minutes": {"limit": minutes_limit, "window": minutes_window},
        }
        for router in routers
    }



RATE_LIMITS_BY_SERVICE_BY_METHOD = {
    "SUMMONER-V4": [
        {
            "method": "/lol/summoner/v4/summoners/by-account",
            "pattern": r"^\/lol\/summoner\/v4\/summoners\/by-account\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "br1": {
                    "seconds": {"limit": 1300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la1": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "euw1": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "eun1": {
                    "seconds": {"limit": 1600, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tr1": {
                    "seconds": {"limit": 1300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "ru": {
                    "seconds": {"limit": 600, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "me1": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "jp1": {
                    "seconds": {"limit": 800, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "kr": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "oc1": {
                    "seconds": {"limit": 800, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sg2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tw2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "vn2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/summoner/v4/summoners/by-puuid",
            "pattern": r"^\/lol\/summoner\/v4\/summoners\/by-puuid\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "br1": {
                    "seconds": {"limit": 1300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la1": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "euw1": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "eun1": {
                    "seconds": {"limit": 1600, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tr1": {
                    "seconds": {"limit": 1300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "ru": {
                    "seconds": {"limit": 600, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "me1": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "jp1": {
                    "seconds": {"limit": 800, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "kr": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "oc1": {
                    "seconds": {"limit": 800, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sg2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tw2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "vn2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/summoner/v4/summoners/me",
            "pattern": r"^\/lol\/summoner\/v4\/summoners\/me$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10},
                    "minutes": {"limit": 1200000, "window": 600}
                }
            }
        },
        {
            "method": "/lol/summoner/v4/summoners",
            "pattern": r"^\/lol\/summoner\/v4\/summoners\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "br1": {
                    "seconds": {"limit": 1300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la1": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "euw1": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "eun1": {
                    "seconds": {"limit": 1600, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tr1": {
                    "seconds": {"limit": 1300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "ru": {
                    "seconds": {"limit": 600, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "me1": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "jp1": {
                    "seconds": {"limit": 800, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "kr": {
                    "seconds": {"limit": 2000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "oc1": {
                    "seconds": {"limit": 800, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sg2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tw2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "vn2": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/fulfillment/v1/summoners/by-puuid",
            "pattern": r"^\/fulfillment\/v1\/summoners\/by-puuid\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
            }
        },
    ],
    "CHAMPION-V3": [
        {
            "method": "/lol/platform/v3/champion-rotations",
            "pattern": r"^\/lol\/platform\/v3\/champion-rotations$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=30,
                seconds_window=10,
                minutes_limit=500,
                minutes_window=600,
            ),
        },
    ],
    "LEAGUE-V4": [
        {
            "method": "/lol/league/v4/challengerleagues/by-queue",
            "pattern": r"^\/lol\/league\/v4\/challengerleagues\/by-queue\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
            }
        },
        {
            "method": "/lol/league/v4/leagues",
            "pattern": r"^\/lol\/league\/v4\/leagues\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "br1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la2": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "euw1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "eun1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tr1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "ru": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "me1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "jp1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "kr": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "oc1": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sg2": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tw2": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "vn2": {
                    "seconds": {"limit": 500, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/league/v4/masterleagues/by-queue",
            "pattern": r"^\/lol\/league\/v4\/masterleagues\/by-queue\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
            }
        },
        {
            "method": "/lol/league/v4/grandmasterleagues/by-queue",
            "pattern": r"^\/lol\/league\/v4\/grandmasterleagues\/by-queue\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 30, "window": 10}, 
                    "minutes": {"limit": 500, "window": 600}
                },
            }
        },
        {
            "method": "/lol/league/v4/entries/by-puuid",
            "pattern": r"^\/lol\/league\/v4\/entries\/by-puuid\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 300, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/league/v4/entries",
            "pattern": r"^\/lol\/league\/v4\/entries\/([^/]+)\/([^/]+)\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "br1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "euw1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "eun1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tr1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "ru": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "me1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "jp1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "kr": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "oc1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sg2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tw2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "vn2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
    ],
    "LEAGUE-EXP-V4": [
        {
            "method": "/lol/league-exp/v4/entries",
            "pattern": r"^\/lol\/league-exp\/v4\/entries\/([^/]+)\/([^/]+)\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "br1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "la2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "euw1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "eun1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tr1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "ru": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "me1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "jp1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "kr": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "oc1": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sg2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "tw2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "vn2": {
                    "seconds": {"limit": 50, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
    ],
    "CLASH-V1": [
        {
            "method": "/lol/clash/v1/teams",
            "pattern": r"^\/lol\/clash\/v1\/teams\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=200,
                seconds_window=60,
            ),
        },
        {
            "method": "/lol/clash/v1/tournaments",
            "pattern": r"^\/lol\/clash\/v1\/tournaments\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=10,
                seconds_window=60,
            ),
        },
        {
            "method": "/lol/clash/v1/tournaments/by-team",
            "pattern": r"^\/lol\/clash\/v1\/tournaments\/by-team\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=200,
                seconds_window=60,
            ),
        },
        {
            "method": "/lol/clash/v1/tournaments",
            "pattern": r"^\/lol\/clash\/v1\/tournaments$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=10,
                seconds_window=60,
            ),
        },
        {
            "method": "/lol/clash/v1/players/by-puuid",
            "pattern": r"^\/lol\/clash\/v1\/players\/by-puuid\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
    ],
    "ACCOUNT-V1": [ # Note SEA is not a region/router option for ACCOUNT-V1
        {
            "method": "/riot/account/v1/accounts/by-riot-id",
            "pattern": r"^\/riot\/account\/v1\/accounts\/by-riot-id\/([^/]+)\/([^/]+)$",
            "routers": {
                "americas": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "asia": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "europe": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/riot/account/v1/accounts/by-puuid",
            "pattern": r"^\/riot\/account\/v1\/accounts\/by-puuid\/([^/]+)$",
            "routers": {
                "americas": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "asia": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
                "europe": {
                    "seconds": {"limit": 1000, "window": 60}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/riot/account/v1/active-shards/by-game",
            "pattern": r"^\/riot\/account\/v1\/active-shards\/by-game\/([^/]+)\/by-puuid\/([^/]+)$",
            "routers": build_router_limits(
                LOL_REGIONAL_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
        {
            "method": "/riot/account/v1/region/by-game",
            "pattern": r"^\/riot\/account\/v1\/region\/by-game\/([^/]+)\/by-puuid\/([^/]+)$",
            "routers": build_router_limits(
                LOL_REGIONAL_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
    ],
    "MATCH-V5": [
        {
            "method": "/lol/match/v5/matches",
            "pattern": r"^\/lol\/match\/v5\/matches\/([^/]+)$",
            "routers": {
                "americas": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "asia": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "europe": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sea": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/match/v5/matches/by-puuid",
            "pattern": r"^\/lol\/match\/v5\/matches\/by-puuid\/([^/]+)\/ids$",
            "routers": {
                "americas": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "asia": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "europe": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sea": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/match/v5/matches/{matchId}/timeline",
            "pattern": r"^\/lol\/match\/v5\/matches\/([^/]+)\/timeline$",
            "routers": {
                "americas": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "asia": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "europe": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
                "sea": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": None, "window": None}
                },
            }
        },
        {
            "method": "/lol/match/v5/matches/by-puuid/replays",
            "pattern": r"^\/lol\/match\/v5\/matches\/by-puuid\/([^/]+)\/replays$",
            "routers": build_router_limits(
                LOL_MATCH_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        }
    ],
    "LOL-STATUS-V4": [
        {
            "method": "/lol/status/v4/platform-data",
            "pattern": r"^\/lol\/status\/v4\/platform-data$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
    ],
    "LOL-CHALLENGES-V1": [
        {
            "method": "/lol/challenges/v1/challenges/config",
            "pattern": r"^\/lol\/challenges\/v1\/challenges\/config$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
        {
            "method": "/lol/challenges/v1/challenges/percentiles",
            "pattern": r"^\/lol\/challenges\/v1\/challenges\/percentiles$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
        {
            "method": "/lol/challenges/v1/challenges/leaderboards/by-level",
            "pattern": r"^\/lol\/challenges\/v1\/challenges\/([^/]+)\/leaderboards\/by-level\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
        {
            "method": "/lol/challenges/v1/challenges/percentiles/by-challenge",
            "pattern": r"^\/lol\/challenges\/v1\/challenges\/([^/]+)\/percentiles$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
        {
            "method": "/lol/challenges/v1/challenges/config/by-challenge",
            "pattern": r"^\/lol\/challenges\/v1\/challenges\/([^/]+)\/config$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
        {
            "method": "/lol/challenges/v1/player-data",
            "pattern": r"^\/lol\/challenges\/v1\/player-data\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
    ],
    "CHAMPION-MASTERY-V4": [
        {
            "method": "/lol/champion-mastery/v4/champion-masteries/by-puuid/by-champion",
            "pattern": r"^\/lol\/champion-mastery\/v4\/champion-masteries\/by-puuid\/([^/]+)\/by-champion\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
            }
        },
        {
            "method": "/lol/champion-mastery/v4/champion-masteries/by-puuid/top",
            "pattern": r"^\/lol\/champion-mastery\/v4\/champion-masteries\/by-puuid\/([^/]+)\/top$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
            }
        },
        {
            "method": "/lol/champion-mastery/v4/champion-masteries/by-puuid",
            "pattern": r"^\/lol\/champion-mastery\/v4\/champion-masteries\/by-puuid\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
            }
        },
        {
            "method": "/lol/champion-mastery/v4/scores",
            "pattern": r"^\/lol\/champion-mastery\/v4\/scores\/by-puuid\/([^/]+)$",
            "routers": {
                "na1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "br1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "la2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "euw1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "eun1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tr1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "ru": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "me1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "jp1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "kr": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "oc1": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "sg2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "tw2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "vn2": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
            }
        },
    ],
    "SPECTATOR-V5": [
        {
            "method": "/lol/spectator/v5/active-games/by-summoner",
            "pattern": r"^\/lol\/spectator\/v5\/active-games\/by-summoner\/([^/]+)$",
            "routers": build_router_limits(
                LOL_PLATFORM_ROUTERS,
                seconds_limit=20000,
                seconds_window=10,
                minutes_limit=1200000,
                minutes_window=600,
            ),
        },
    ],
}
