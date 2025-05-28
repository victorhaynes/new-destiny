import os
from dotenv import load_dotenv
load_dotenv()

try:
    ND_RIOT_API_KEY = os.environ["ND_RIOT_API_KEY"]
except KeyError:
    raise RuntimeError("Missing ND_RIOT_API_KEY, please set it in your application's .env file or your environment.")

try:
    ND_REDIS_URL = os.environ["ND_REDIS_URL"]
except KeyError:
    raise RuntimeError("Missing ND_REDIS_URL, please set it in your application's .env file or your environment.")

try:
    ND_REDIS_PORT = os.environ["ND_REDIS_PORT"]
except KeyError:
    raise RuntimeError("Missing ND_REDIS_PORT, please set it in your application's .env file or your environment.")

try:
    ND_DEBUG = os.environ["ND_DEBUG"]
    if ND_DEBUG not in ("1", "0"):
        raise ValueError(f"ND_DEBUG must be 0 or 1. You set it to {ND_DEBUG}.")
    ND_DEBUG = int(ND_DEBUG)
except KeyError:
    raise RuntimeError("Missing ND_DEBUG, please set it to 0 or 1 (bool) in your application's .env file or your environment.")

try:
    ND_PRODUCTION = os.environ["ND_PRODUCTION"]
    if ND_PRODUCTION not in ("1", "0"):
        raise ValueError(f"ND_PRODUCTION must be 0 or 1. You set it to {ND_PRODUCTION}.")
    ND_PRODUCTION = int(ND_PRODUCTION)
except KeyError:
    raise RuntimeError("Missing ND_PRODUCTION, please set it to 0 or 1 (bool) in your application's .env file or your environment.")

def get_validated_positive_int(var_name):
    val = os.getenv(var_name)
    if val is None:
        return None
    if not val.isalnum():
        raise ValueError(f"{var_name} must be an alphanumeric integer representation. You set it to: {val}")
    try:
        int_val = int(val)
        if int_val <= 0:
            raise ValueError
        return int_val
    except ValueError:
        raise ValueError(f"Choose a sensical integer value > 0 for {var_name}, or do not specify it. You set it to: {val}")

# Assign validated values (or None)
ND_CUSTOM_SECONDS_LIMIT = get_validated_positive_int("ND_CUSTOM_SECONDS_LIMIT")
ND_CUSTOM_SECONDS_WINDOW = get_validated_positive_int("ND_CUSTOM_SECONDS_WINDOW")
ND_CUSTOM_MINUTES_LIMIT = get_validated_positive_int("ND_CUSTOM_MINUTES_LIMIT")
ND_CUSTOM_MINUTES_WINDOW = get_validated_positive_int("ND_CUSTOM_MINUTES_WINDOW")

if (ND_CUSTOM_SECONDS_LIMIT or ND_CUSTOM_SECONDS_WINDOW or ND_CUSTOM_MINUTES_LIMIT or ND_CUSTOM_MINUTES_WINDOW) and not ND_PRODUCTION:
    raise ValueError("Only Production API Keys have custom limits. Either set ND_PRODUCTION to 1 or remove all ND_CUSTOM variables.")