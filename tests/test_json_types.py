import pytest

from new_destiny.json_types import (
    expect_bool,
    expect_float,
    expect_int,
    expect_number,
    expect_object,
    expect_string,
)


def test_expect_object_returns_dict() -> None:
    payload = {"puuid": "abc123", "gameName": "hide on bush"}

    assert expect_object(payload) == payload


def test_expect_string_returns_string() -> None:
    assert expect_string("abc123") == "abc123"


def test_expect_numeric_helpers_accept_expected_values() -> None:
    assert expect_int(12) == 12
    assert expect_float(12) == 12.0
    assert expect_float(1.5) == 1.5
    assert expect_number(1.5) == 1.5
    assert expect_bool(True) is True


def test_expect_object_raises_for_non_object() -> None:
    with pytest.raises(ValueError, match="Expected dict but got list"):
        expect_object([])


def test_expect_string_raises_for_non_string() -> None:
    with pytest.raises(ValueError, match="Expected str but got int"):
        expect_string(123)
