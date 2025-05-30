import json
import textwrap
from urllib.parse import urlparse
from .rate_limit_helpers import derive_riot_method_config, derive_riot_service

def format_offending_context(offending_context) -> str:
    """
    Format the offending_context into a readable multiline string. 
    Used for better logging support when a Riot rate limit exception or a general non-ok response (RiotAPIError) occurs.
    Expects offending_context to be a dict: {headers: obj, body: obj}.
    The headers are pretty printed with one key per line.
    The body is converted to a JSON string (if possible) and wrapped to 100 characters per line,
    with a maximum of 30 lines.
    """
    if not offending_context:
        return ""

    headers = offending_context.get("headers", {})
    body    = offending_context.get("body", None)

    lines = ["  offending_context:", "    Headers:"]
    for key, value in headers.items():
        lines.append(f"      {key}: {value}")

    lines.append(f"    Body:  type({type(body)})")
    body_str = json.dumps(body, indent=2) if isinstance(body, dict) else str(body)
    for ln in textwrap.wrap(body_str, width=100)[:30]:
        lines.append("      " + ln)
    if len(body_str) > 100 * 30:
        lines.append("      ... (truncated)")

    return "\n".join(lines)


###### Exception Classes ######
###### Exception Classes ######
###### Exception Classes ######

class RiotRelatedException(Exception):
    pass

class RiotRelatedRateLimitException(Exception):
    pass

class ApplicationRateLimitExceeded(RiotRelatedException, RiotRelatedRateLimitException):
    def __init__(self, retry_after: int, minutes_key: str, seconds_key: str, enforcement_type: str, subdomain: str, riot_endpoint: str, reason: str, seconds_limit= None, minutes_limit= None, seconds_count= None, seconds_window=None, minutes_count= None, minutes_window=None, offending_context=None):
        self.retry_after = retry_after
        self.seconds_key = seconds_key
        self.seconds_count = seconds_count # Only exists when internally enforced. This represents the current count of the seconds_key stored in redis.
        self.seconds_limit = seconds_limit
        self.seconds_window = f"{seconds_window} seconds"
        self.minutes_key = minutes_key
        self.minutes_count = minutes_count # Only exists when internally enforced. This represents the current count of the mintes_key stored in redis.
        self.minutes_limit = minutes_limit
        self.minutes_window = f"{minutes_window} seconds"
        self.enforcement_type = enforcement_type
        self.subdomain = subdomain
        self.riot_endpoint = riot_endpoint
        self.reason = reason
        self.offending_context = offending_context # If intenerally enforced this cannot be known, so it will default to None. Only exists when externally enforced

    def __str__(self):
        lines = [
            "ApplicationRateLimitExceeded:",
            f"  retry_after: {self.retry_after}",
            f"  seconds_key: {self.seconds_key}",
            f"  seconds_count: {self.seconds_count if self.seconds_count else 'N/A - Riot headers source of truth'}",
            f"  seconds_limit: {self.seconds_limit}",
            f"  seconds_window: {self.seconds_window}",
            f"  minutes_key: {self.minutes_key}",
            f"  minutes_count: {self.minutes_count if self.minutes_count else 'N/A - Riot headers source of truth'}",
            f"  minutes_limit: {self.minutes_limit}",
            f"  minutes_window: {self.minutes_window}",
            f"  enforcement_type: {self.enforcement_type}",
            f"  subdomain: {self.subdomain}",
            f"  riot_endpoint: {self.riot_endpoint}",
            f"  reason: {self.reason}",
        ]
        if self.offending_context is not None:
            lines.append(format_offending_context(self.offending_context))
        return f"\033[31m{'\n'.join(lines)}\033[0m"

    def to_dict(self):
        return {
            "type": "ApplicationRateLimitExceeded",
            "retry_after": self.retry_after,
            "seconds_key": self.seconds_key,
            "seconds_limit": self.seconds_limit,
            "seconds_count": self.seconds_count,
            "seconds_window": self.seconds_window,
            "minutes_key": self.minutes_key,
            "minutes_limit": self.minutes_limit,
            "minutes_count": self.minutes_count,
            "minutes_window": self.minutes_window,
            "enforcement_type": self.enforcement_type,
            "subdomain": self.subdomain,
            "url": self.riot_endpoint,
            "reason": self.reason,
            "offending_context": self.offending_context
        }


class MethodRateLimitExceeded(RiotRelatedException, RiotRelatedRateLimitException):
    def __init__(self, retry_after: int, method: str, minutes_key: str, seconds_key: str, enforcement_type: str, subdomain: str, riot_endpoint:str, reason: str, seconds_limit= None, minutes_limit= None, seconds_count= None, seconds_window=None, minutes_count= None, minutes_window=None, offending_context=None):
        self.retry_after = retry_after
        self.method = method
        self.seconds_key = seconds_key
        self.seconds_count = seconds_count # Only exists when internally enforced. This represents the current count of the seconds_key stored in redis.
        self.seconds_limit = seconds_limit
        self.seconds_window = seconds_window
        self.minutes_key = minutes_key
        self.minutes_count = minutes_count # Only exists when internally enforced. This represents the current count of the mintes_key stored in redis.
        self.minutes_limit = minutes_limit
        self.minutes_window = minutes_window
        self.enforcement_type = enforcement_type
        self.subdomain = subdomain
        self.riot_endpoint = riot_endpoint
        self.reason = reason
        self.offending_context = offending_context

    def __str__(self):
        lines = [
            "MethodRateLimitExceeded:",
            f"  retry_after: {self.retry_after}",
            f"  method: {self.method}",
            f"  seconds_key: {self.seconds_key}",
            f"  seconds_count: {self.seconds_count if self.seconds_count else 'N/A - Riot headers source of truth'}",
            f"  seconds_limit: {self.seconds_limit}",
            f"  seconds_window: {self.seconds_window}",
            f"  minutes_key: {self.minutes_key}",
            f"  minutes_count: {self.minutes_count if self.minutes_count else 'N/A - Riot headers source of truth'}",
            f"  minutes_limit: {self.minutes_limit}",
            f"  minutes_window: {self.minutes_window}",
            f"  enforcement_type: {self.enforcement_type}",
            f"  subdomain: {self.subdomain}",
            f"  riot_endpoint: {self.riot_endpoint}",
            f"  reason: {self.reason}",
        ]
        if self.offending_context is not None:
            lines.append(format_offending_context(self.offending_context))
        return f"\033[31m{'\n'.join(lines)}\033[0m"

    def to_dict(self) -> dict:
        return {
            "type": "MethodRateLimitExceeded",
            "retry_after": self.retry_after,
            "method": self.method,
            "minutes_key": self.minutes_key,
            "seconds_key": self.seconds_key,
            "enforcement_type": self.enforcement_type,
            "subdomain": self.subdomain,
            "riot_endpoint": self.riot_endpoint,
            "reason": self.reason,
            "seconds_limit": self.seconds_limit,
            "minutes_limit": self.minutes_limit,
            "seconds_count": self.seconds_count,
            "minutes_count": self.minutes_count,
            "offending_context": self.offending_context,  # Ensure this is serializable if nested
        }


class ServiceRateLimitExceeded(RiotRelatedException, RiotRelatedRateLimitException):
    def __init__(self, retry_after: int, service: str, enforcement_type: str, subdomain: str, riot_endpoint: str, offending_context=None):
        self.retry_after = retry_after
        self.service = service
        self.enforcement_type = enforcement_type
        self.subdomain = subdomain
        self.riot_endpoint = riot_endpoint
        self.offending_context = offending_context

    def __str__(self):
        lines = [
            "ServiceRateLimitExceeded:",
            f"  retry_after: {self.retry_after}",
            f"  service: {self.service}",
            f"  enforcement_type: {self.enforcement_type}",
            f"  subdomain: {self.subdomain}",
            f"  riot_endpoint: {self.riot_endpoint}",
        ]
        if self.offending_context is not None:
            lines.append(format_offending_context(self.offending_context))
        return f"\033[31m{'\n'.join(lines)}\033[0m"

    def to_dict(self) -> dict:
        return {
            "type": "ServiceRateLimitExceeded",
            "retry_after": self.retry_after,
            "service": self.service,
            "enforcement_type": self.enforcement_type,
            "subdomain": self.subdomain,
            "riot_endpoint": self.riot_endpoint,
            "offending_context": self.offending_context,
        }

class UnspecifiedRateLimitExceeded(RiotRelatedException, RiotRelatedRateLimitException):
    """
    This is an edge case exception class. 
    It is very uncommon but possible that Riot experience an API degredation and the type of 429 cannot be classified easily.
    In this case gather all information possible.
    """
    def __init__(self, retry_after: int, subdomain: str, service: str, method: str, enforcement_type: str, riot_endpoint:str, offending_context=None):
        self.retry_after = retry_after
        self.enforcement_type = enforcement_type
        self.subdomain = subdomain
        self.riot_endpoint = riot_endpoint
        self.offending_context = offending_context
        self.service = service
        self.method = method

    def __str__(self):
        lines = [
            "UnspecifiedRateLimitExceeded:",
            f"  retry_after: {self.retry_after}",
            f"  service: {self.service}",
            f"  method: {self.method}",
            f"  enforcement_type: {self.enforcement_type}",
            f"  subdomain: {self.subdomain}",
            f"  riot_endpoint: {self.riot_endpoint}",
        ]
        if self.offending_context is not None:
            lines.append(format_offending_context(self.offending_context))
        return f"\033[31m{'\n'.join(lines)}\033[0m"
    
    def to_dict(self) -> dict:
        return {
            "type": "UnspecifiedRateLimitExceeded",
            "retry_after": self.retry_after,
            "method": self.method,
            "enforcement_type": self.enforcement_type,
            "subdomain": self.subdomain,
            "riot_endpoint": self.riot_endpoint,
            "offending_context": self.offending_context,
        }


class RiotAPIError(RiotRelatedException):
    """
    500 series or non 429 status code errors received from Riot.
    """
    def __init__(self, status_code: int, riot_endpoint:str, message: dict, offending_context=None):
        self.status_code = status_code
        self.message = message
        self.subdomain = self.get_subdomain(riot_endpoint=riot_endpoint)
        self.service = derive_riot_service(riot_endpoint=riot_endpoint)
        self.method = derive_riot_method_config(riot_endpoint=riot_endpoint, router=self.subdomain, service=self.service)["method"]
        self.riot_endpoint = riot_endpoint
        self.offending_context = offending_context

    def get_subdomain(self, riot_endpoint: str):
        parsed_url = urlparse(riot_endpoint)
        hostname = parsed_url.hostname  # Ex. "na1.api.riotgames.com"
        
        if not hostname:
            raise ValueError(f"Invalid URL: No hostname found. Subdomain (what Riot docs inaccurately calls per 'region' for per-region enforcement) cannot be determined from {riot_endpoint}")

        subdomain = hostname.split(".")[0]  # Extracts "na1" from "na1.api.riotgames.com"
        return subdomain.lower()
    
    def __str__(self):
        lines = [
            "RiotAPIError:",
            f"  status_code: {self.status_code}",
            f"  subdomain: {self.subdomain}",
            f"  message: {self.message}",
            f"  service: {self.service}",
            f"  method: {self.method}",
            f"  riot_endpoint: {self.riot_endpoint}"
        ]
        if self.offending_context is not None:
            lines.append(format_offending_context(self.offending_context))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "type": "RiotAPIError",
            "status_code": self.status_code,
            "subdomain": self.subdomain,
            "message": self.message,
            "service": self.service,
            "method": self.method,
            "riot_endpoint": self.riot_endpoint,
            "offending_context": self.offending_context,
        }


class BatchJobStopSignal(Exception):
    """
    Basic exception to stop processing a batch job
    """
    pass
