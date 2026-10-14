import pytest

from new_destiny.rate_limit_helpers import (
    derive_riot_method_config,
    derive_riot_service,
)


@pytest.mark.parametrize(
    (
        "endpoint",
        "router",
        "expected_service",
        "expected_method",
        "expected_limit",
        "expected_window",
    ),
    [
        (
            "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/puuid",
            "na1",
            "SUMMONER-V4",
            "/lol/summoner/v4/summoners/by-puuid",
            2000,
            60,
        ),
        (
            "https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
            "americas",
            "MATCH-V5",
            "/lol/match/v5/matches",
            20000,
            10,
        ),
        (
            "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/hide%20on%20bush/kr1",
            "americas",
            "ACCOUNT-V1",
            "/riot/account/v1/accounts/by-riot-id",
            1000,
            60,
        ),
    ],
)
def test_rate_limit_classifier_matches_service_method_and_router(
    endpoint: str,
    router: str,
    expected_service: str,
    expected_method: str,
    expected_limit: int,
    expected_window: int,
) -> None:
    service = derive_riot_service(endpoint)
    config = derive_riot_method_config(endpoint, router, service)

    assert service == expected_service
    assert config["method"] == expected_method
    assert config["router"] == router
    assert config["seconds"] == {"limit": expected_limit, "window": expected_window}


def test_rate_limit_classifier_rejects_an_unmatched_method() -> None:
    with pytest.raises(ValueError, match="No matching method"):
        derive_riot_method_config(
            "https://americas.api.riotgames.com/lol/match/v5/unknown/NA1_1",
            "americas",
            "MATCH-V5",
        )


def test_rate_limit_classifier_rejects_a_wrong_router_for_a_method() -> None:
    with pytest.raises(ValueError, match=r"No rate.*router 'na1'"):
        derive_riot_method_config(
            "https://na1.api.riotgames.com/lol/match/v5/matches/NA1_1",
            "na1",
            "MATCH-V5",
        )
