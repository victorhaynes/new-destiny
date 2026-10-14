import pytest

from new_destiny.json_types import (
    expect_bool,
    expect_float,
    expect_int,
    expect_number,
    expect_dict,
    expect_list,
    RiotResponse,
    expect_string,
)


def test_expect_dict_returns_dict() -> None:
    payload: RiotResponse = {"puuid": "abc123", "gameName": "hide on bush"}

    assert expect_dict(payload) == payload


def test_expect_string_returns_string() -> None:
    assert expect_string("abc123") == "abc123"


def test_expect_numeric_helpers_accept_expected_values() -> None:
    assert expect_int(12) == 12
    assert expect_float(12) == 12.0
    assert expect_float(1.5) == 1.5
    assert expect_number(1.5) == 1.5
    assert expect_bool(True) is True


def test_expect_dict_raises_for_non_dict() -> None:
    with pytest.raises(ValueError, match="Expected dict but got list"):
        expect_dict([])


def test_expect_list_returns_list() -> None:
    payload: RiotResponse = [{"puuid": "abc123"}, "complete", 1]

    assert expect_list(payload) == payload


def test_expect_list_raises_for_non_list() -> None:
    with pytest.raises(ValueError, match="Expected list but got dict"):
        expect_list({})


def test_expect_int_rejects_bool() -> None:
    with pytest.raises(ValueError, match="Expected int but got bool"):
        expect_int(True)


def test_expect_number_rejects_bool() -> None:
    with pytest.raises(ValueError, match="Expected int or float but got bool"):
        expect_number(False)


def test_expect_string_raises_for_non_string() -> None:
    with pytest.raises(ValueError, match="Expected str but got int"):
        expect_string(123)
