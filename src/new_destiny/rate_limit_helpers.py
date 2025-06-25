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
    elif '/lol/league/v4' in path:
        return "LEAGUE-V4"
    elif "/lol/league-exp/v4" in path:
        return 'LEAGUE-EXP-V4'
    elif "/riot/account/v1" in path:
        return "ACCOUNT-V1"
    elif "/lol/match/v5/" in path:
        return "MATCH-V5"
    elif "lol/champion-mastery/v4" in path:
        return "CHAMPION-MASTERY-V4"
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
            "pattern": r"^\/riot\/account\/v1\/active-shards\/by-game\/([^/]+)\/([^/]+)$",
            "routers": {
                "americas": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "asia": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
                "europe": {
                    "seconds": {"limit": 20000, "window": 10}, 
                    "minutes": {"limit": 1200000, "window": 600}
                },
            }
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
        }
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
    ]
}