from new_destiny.exceptions import RiotAPIError, RiotNetworkError


def test_network_error_serializes_its_own_fields() -> None:
    error = RiotNetworkError(
        error_type="timeout",
        message="request timed out",
        riot_endpoint="https://na1.api.riotgames.com/lol/match/v5/matches/NA1_1",
    )

    assert error.to_dict() == {
        "type": "RiotNetworkError",
        "error_type": "timeout",
        "message": "request timed out",
        "riot_endpoint": "https://na1.api.riotgames.com/lol/match/v5/matches/NA1_1",
        "original_exception": None,
    }


def test_api_error_preserves_arbitrary_json_message() -> None:
    error = RiotAPIError(
        status_code=500,
        riot_endpoint="https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
        message=["riot", {"status": "error"}],
    )

    assert error.message == ["riot", {"status": "error"}]
    assert error.to_dict()["status_code"] == 500
