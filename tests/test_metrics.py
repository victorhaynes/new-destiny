from datetime import datetime, timezone
import importlib

import pytest

from new_destiny.exceptions import (
    ApplicationRateLimitExceeded,
    MethodRateLimitExceeded,
    ServiceRateLimitExceeded,
    UnspecifiedRateLimitExceeded,
)
from new_destiny.metrics import build_rate_limit_metric_key, record_rate_limit_event


BUCKET = datetime(2026, 10, 26, 20, 41, 35, tzinfo=timezone.utc)


def _application_error() -> ApplicationRateLimitExceeded:
    return ApplicationRateLimitExceeded(
        retry_after=10,
        minutes_key="minutes",
        seconds_key="seconds",
        enforcement_type="internal",
        routing_value="na1",
        riot_endpoint="https://na1.api.riotgames.com/lol/match/v5/matches/NA1_1",
        reason="application limit",
        seconds_limit=500,
        minutes_limit=30000,
        seconds_window=10,
        minutes_window=600,
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            _application_error(),
            "nd:metrics:rate-limit:application:na1:internal:2026-10-26T20:41Z",
        ),
        (
            MethodRateLimitExceeded(
                retry_after=10,
                method="/lol/match/v5/matches",
                service="MATCH-V5",
                enforcement_type="external",
                routing_value="americas",
                riot_endpoint="https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
                reason="method limit",
            ),
            "nd:metrics:rate-limit:method:americas:external:match-v5:lol-match-v5-matches:2026-10-26T20:41Z",
        ),
        (
            ServiceRateLimitExceeded(
                retry_after=68,
                service="MATCH-V5",
                enforcement_type="external",
                routing_value="americas",
                riot_endpoint="https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
            ),
            "nd:metrics:rate-limit:service:americas:external:match-v5:2026-10-26T20:41Z",
        ),
        (
            UnspecifiedRateLimitExceeded(
                retry_after=10,
                routing_value="americas",
                service="MATCH-V5",
                method="/lol/match/v5/matches",
                enforcement_type="external",
                riot_endpoint="https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
            ),
            "nd:metrics:rate-limit:unspecified:americas:external:match-v5:lol-match-v5-matches:2026-10-26T20:41Z",
        ),
    ],
)
def test_rate_limit_metric_key_is_scope_first(error, expected: str) -> None:
    assert build_rate_limit_metric_key(error, now=BUCKET) == expected


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.executed = False

    def incr(self, key: str) -> None:
        self.calls.append(("incr", key))

    def expire(self, key: str, seconds: int) -> None:
        self.calls.append(("expire", (key, seconds)))

    async def execute(self) -> list[object]:
        self.executed = True
        return []


class FakeRedis:
    def __init__(self) -> None:
        self.pipeline_instance = FakePipeline()

    def pipeline(self, *, transaction: bool) -> FakePipeline:
        assert transaction is True
        return self.pipeline_instance


@pytest.mark.asyncio
async def test_record_rate_limit_event_increments_and_expires_one_key() -> None:
    redis = FakeRedis()
    error = _application_error()

    key = await record_rate_limit_event(redis, error, now=BUCKET)

    assert redis.pipeline_instance.executed is True
    assert redis.pipeline_instance.calls == [
        ("incr", key),
        ("expire", (key, 25 * 60 * 60)),
    ]


class BrokenRedis:
    def pipeline(self, *, transaction: bool) -> None:
        raise RuntimeError("metrics Redis unavailable")


@pytest.mark.asyncio
async def test_record_rate_limit_event_is_best_effort() -> None:
    key = await record_rate_limit_event(BrokenRedis(), _application_error(), now=BUCKET)

    assert key == "nd:metrics:rate-limit:application:na1:internal:2026-10-26T20:41Z"


@pytest.mark.asyncio
async def test_request_path_skips_metrics_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ND_RIOT_API_KEY", "test-key")
    monkeypatch.setenv("ND_REDIS_URL", "localhost")
    monkeypatch.setenv("ND_REDIS_PORT", "6379")
    monkeypatch.setenv("ND_LOG_LEVEL", "0")
    monkeypatch.setenv("ND_PRODUCTION", "0")
    request_module = importlib.import_module("new_destiny.riot_get_request")

    async def raise_rate_limit(*args: object, **kwargs: object) -> None:
        raise _application_error()

    async def unexpected_metrics_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("metrics should be disabled")

    monkeypatch.setattr(request_module, "ND_ENABLE_METRICS", 0)
    monkeypatch.setattr(request_module, "_perform_riot_request", raise_rate_limit)
    monkeypatch.setattr(request_module, "record_rate_limit_event", unexpected_metrics_call)

    with pytest.raises(ApplicationRateLimitExceeded):
        await request_module.perform_riot_request("endpoint", object(), object())


@pytest.mark.asyncio
async def test_request_path_records_metrics_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ND_RIOT_API_KEY", "test-key")
    monkeypatch.setenv("ND_REDIS_URL", "localhost")
    monkeypatch.setenv("ND_REDIS_PORT", "6379")
    monkeypatch.setenv("ND_LOG_LEVEL", "0")
    monkeypatch.setenv("ND_PRODUCTION", "0")
    request_module = importlib.import_module("new_destiny.riot_get_request")

    error = _application_error()
    recorded: list[object] = []

    async def raise_rate_limit(*args: object, **kwargs: object) -> None:
        raise error

    async def record_metrics(*args: object, **kwargs: object) -> None:
        recorded.append(args)

    monkeypatch.setattr(request_module, "ND_ENABLE_METRICS", 1)
    monkeypatch.setattr(request_module, "_perform_riot_request", raise_rate_limit)
    monkeypatch.setattr(request_module, "record_rate_limit_event", record_metrics)

    redis = object()
    with pytest.raises(ApplicationRateLimitExceeded):
        await request_module.perform_riot_request("endpoint", object(), redis)

    assert len(recorded) == 1
    assert recorded[0][0] is redis
    assert recorded[0][1] is error
