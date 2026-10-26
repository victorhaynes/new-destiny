from new_destiny.exceptions import MethodRateLimitExceeded, RiotAPIError, RiotNetworkError


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
    assert error.routing_value == "americas"
    assert error.service == "MATCH-V5"
    assert error.method == "/lol/match/v5/matches"


def test_method_rate_limit_error_includes_service_and_routing_value() -> None:
    error = MethodRateLimitExceeded(
        retry_after=10,
        method="/riot/account/v1/accounts/by-puuid",
        service="ACCOUNT-V1",
        enforcement_type="external",
        routing_value="americas",
        riot_endpoint="https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/puuid",
        reason="Riot returned a method rate limit",
    )

    assert error.to_dict()["service"] == "ACCOUNT-V1"
    assert error.to_dict()["routing_value"] == "americas"
