from __future__ import annotations

from typing import TypedDict

type JSONPrimitive = str | int | float | bool | None
type JSONObject = dict[str, JSONValue]
type JSONArray = list[JSONValue]
type JSONValue = JSONPrimitive | JSONObject | JSONArray
type RiotResponse = JSONObject | JSONArray | None


class RiotOffendingContext(TypedDict):
    headers: dict[str, str]
    body: JSONValue | None


def expect_object(value: RiotResponse) -> JSONObject:
    """Narrow a Riot response to a JSON object."""
    if not isinstance(value, dict):
        raise ValueError(f"Expected dict but got {type(value).__name__}")
    return value


def expect_array(value: RiotResponse) -> JSONArray:
    """Narrow a Riot response to a JSON array."""
    if not isinstance(value, list):
        raise ValueError(f"Expected list but got {type(value).__name__}")
    return value


def expect_string(value: JSONValue) -> str:
    """Narrow a JSON value to a string."""
    if not isinstance(value, str):
        raise ValueError(f"Expected str but got {type(value).__name__}")
    return value


def expect_int(value: JSONValue) -> int:
    """Narrow a JSON value to an int, excluding bool."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected int but got {type(value).__name__}")
    return value


def expect_float(value: JSONValue) -> float:
    """Narrow a JSON value to a float or int, excluding bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected float but got {type(value).__name__}")
    return float(value)


def expect_bool(value: JSONValue) -> bool:
    """Narrow a JSON value to a bool."""
    if not isinstance(value, bool):
        raise ValueError(f"Expected bool but got {type(value).__name__}")
    return value


def expect_number(value: JSONValue) -> int | float:
    """Narrow a JSON value to a number, excluding bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected int or float but got {type(value).__name__}")
    return value
