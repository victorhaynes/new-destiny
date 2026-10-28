from datetime import datetime, timezone
import importlib

import httpx
import pytest

from new_destiny.exceptions import (
    ApplicationRateLimitExceeded,
    MethodRateLimitExceeded,
    ServiceRateLimitExceeded,
    UnspecifiedRateLimitExceeded,
)
from new_destiny.metrics import (
    build_rate_limit_metric_key,
    build_request_metric_key,
    _retry_after_metric_fields,
    record_rate_limit_event,
    record_request_event,
)
from new_destiny.riot_get_request import _resolve_retry_after
from new_destiny.rate_limiter import ServiceRateLimiter


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
                retry_after=61,
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


class EvalRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def eval(self, *args: object) -> int:
        self.calls.append(args)
        return 1


class SetRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def set(self, *args: object, **kwargs: object) -> None:
        self.calls.append((*args, kwargs))


@pytest.mark.asyncio
async def test_record_rate_limit_event_increments_and_expires_one_key() -> None:
    redis = EvalRedis()
    error = _application_error()

    key = await record_rate_limit_event(redis, error, now=BUCKET)

    assert key == "nd:metrics:rate-limit:application:na1:internal:2026-10-26T20:41Z"
    assert redis.calls[0][1:] == (
        1,
        key,
        25 * 60 * 60,
        "events",
        1,
        "effective_retry_after_seconds:10",
        1,
    )


@pytest.mark.asyncio
async def test_service_rate_limit_uses_the_61_second_fallback() -> None:
    redis = SetRedis()
    limiter = ServiceRateLimiter(
        "https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
        redis,
    )

    with pytest.raises(ServiceRateLimitExceeded) as raised:
        await limiter.write_inbound_service_rate_limit(
            offending_context={"headers": {}, "body": None},
            retry_after=None,
        )

    assert raised.value.retry_after == 61
    assert redis.calls[0] == (
        limiter.service_key,
        1,
        {"ex": 61, "nx": True},
    )


def test_external_retry_after_metrics_keep_raw_and_effective_values() -> None:
    error = MethodRateLimitExceeded(
        retry_after=61,
        method="/lol/match/v5/matches",
        service="MATCH-V5",
        enforcement_type="external",
        routing_value="americas",
        riot_endpoint="https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
        reason="method limit",
        offending_context={
            "headers": {"retry-after": "60"},
            "body": None,
        },
    )

    assert dict(_retry_after_metric_fields(error)) == {
        "events": 1,
        "effective_retry_after_seconds:61": 1,
        "riot_retry_after_seconds:60": 1,
    }


@pytest.mark.parametrize(
    ("headers", "field"),
    [
        ({}, "riot_retry_after_missing"),
        ({"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"}, "riot_retry_after_unusable"),
        ({"retry-after": "not-a-number"}, "riot_retry_after_unusable"),
    ],
)
def test_external_retry_after_metrics_classify_missing_or_unusable_values(
    headers: dict[str, str],
    field: str,
) -> None:
    error = ServiceRateLimitExceeded(
        retry_after=61,
        service="MATCH-V5",
        enforcement_type="external",
        routing_value="americas",
        riot_endpoint="https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
        offending_context={"headers": headers, "body": None},
    )

    assert dict(_retry_after_metric_fields(error))[field] == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, (61, "missing")),
        ("60", (61, "valid")),
        ("Wed, 21 Oct 2015 07:28:00 GMT", (61, "unusable")),
        ("not-a-number", (61, "unusable")),
        ("0", (61, "unusable")),
    ],
)
def test_retry_after_resolution_always_returns_a_protective_value(
    value: str | None,
    expected: tuple[int, str],
) -> None:
    assert _resolve_retry_after(value) == expected


def test_request_metric_key_captures_the_admission_scope() -> None:
    assert build_request_metric_key(
        routing_value="americas",
        service="MATCH-V5",
        method="/lol/match/v5/matches/{matchId}",
        now=BUCKET,
    ) == "nd:metrics:request:americas:match-v5:lol-match-v5-matches-matchid:2026-10-26T20:41Z"


@pytest.mark.asyncio
async def test_record_request_event_uses_the_same_expiring_counter_shape() -> None:
    redis = EvalRedis()

    key = await record_request_event(
        redis,
        routing_value="americas",
        service="MATCH-V5",
        method="/lol/match/v5/matches",
        now=BUCKET,
    )

    assert key == "nd:metrics:request:americas:match-v5:lol-match-v5-matches:2026-10-26T20:41Z"
    assert redis.calls[0][1:] == (1, key, 25 * 60 * 60)


class BrokenRedis:
    async def eval(self, *args: object) -> None:
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

    monkeypatch.setattr(request_module, "ND_ENABLE_ERROR_METRICS", 0)
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

    monkeypatch.setattr(request_module, "ND_ENABLE_ERROR_METRICS", 1)
    monkeypatch.setattr(request_module, "_perform_riot_request", raise_rate_limit)
    monkeypatch.setattr(request_module, "record_rate_limit_event", record_metrics)

    redis = object()
    with pytest.raises(ApplicationRateLimitExceeded):
        await request_module.perform_riot_request("endpoint", object(), redis)

    assert len(recorded) == 1
    assert recorded[0][0] is redis
    assert recorded[0][1] is error


@pytest.mark.asyncio
async def test_request_path_records_only_after_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ND_RIOT_API_KEY", "test-key")
    monkeypatch.setenv("ND_REDIS_URL", "localhost")
    monkeypatch.setenv("ND_REDIS_PORT", "6379")
    monkeypatch.setenv("ND_LOG_LEVEL", "0")
    monkeypatch.setenv("ND_PRODUCTION", "0")
    request_module = importlib.import_module("new_destiny.riot_get_request")

    class FakeApplicationLimiter:
        def __init__(self, *args: object) -> None:
            pass

        async def check_and_increment(self) -> None:
            pass

    class FakeMethodLimiter:
        routing_value = "americas"
        method = "/lol/match/v5/matches"

        def __init__(self, *args: object) -> None:
            pass

        async def check_and_increment(self) -> None:
            pass

    class FakeServiceLimiter:
        routing_value = "americas"
        service = "MATCH-V5"

        def __init__(self, *args: object) -> None:
            pass

        async def is_allowed(self) -> None:
            pass

    class FakeUnspecifiedLimiter:
        def __init__(self, *args: object) -> None:
            pass

        async def is_allowed(self) -> None:
            pass

    recorded: list[tuple[object, ...]] = []

    async def record_metrics(*args: object, **kwargs: object) -> None:
        recorded.append((*args, kwargs))

    class FakeClient:
        async def get(self, *args: object, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={"ok": True},
                request=httpx.Request("GET", "https://americas.api.riotgames.com"),
            )

    monkeypatch.setattr(request_module, "ApplicationRateLimiter", FakeApplicationLimiter)
    monkeypatch.setattr(request_module, "MethodRateLimiter", FakeMethodLimiter)
    monkeypatch.setattr(request_module, "ServiceRateLimiter", FakeServiceLimiter)
    monkeypatch.setattr(request_module, "UnspecifiedRiotRateLimiter", FakeUnspecifiedLimiter)
    monkeypatch.setattr(request_module, "ND_ENABLE_REQUEST_METRICS", 1)
    monkeypatch.setattr(request_module, "record_request_event", record_metrics)

    redis = object()
    response = await request_module._perform_riot_request(
        "https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
        FakeClient(),
        redis,
    )

    assert response == {"ok": True}
    assert recorded == [
        (
            redis,
            {
                "routing_value": "americas",
                "service": "MATCH-V5",
                "method": "/lol/match/v5/matches",
            },
        )
    ]


@pytest.mark.asyncio
async def test_malformed_429_body_and_retry_after_still_write_a_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ND_RIOT_API_KEY", "test-key")
    monkeypatch.setenv("ND_REDIS_URL", "localhost")
    monkeypatch.setenv("ND_REDIS_PORT", "6379")
    monkeypatch.setenv("ND_LOG_LEVEL", "0")
    monkeypatch.setenv("ND_PRODUCTION", "0")
    request_module = importlib.import_module("new_destiny.riot_get_request")
    block_calls: list[tuple[int, object]] = []

    class FakeApplicationLimiter:
        def __init__(self, *args: object) -> None:
            pass

        async def check_and_increment(self) -> None:
            pass

        async def write_inbound_application_rate_limit(
            self,
            *,
            retry_after: int,
            offending_context: object,
        ) -> None:
            block_calls.append((retry_after, offending_context))
            raise _application_error()

    class FakeMethodLimiter:
        method = "/lol/match/v5/matches"

        def __init__(self, *args: object) -> None:
            pass

        async def check_and_increment(self) -> None:
            pass

    class FakeServiceLimiter:
        service = "MATCH-V5"

        def __init__(self, *args: object) -> None:
            pass

        async def is_allowed(self) -> None:
            pass

    class FakeUnspecifiedLimiter:
        def __init__(self, *args: object) -> None:
            pass

        async def is_allowed(self) -> None:
            pass

    class FakeClient:
        async def get(self, *args: object, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                429,
                headers={
                    "x-rate-limit-type": "application",
                    "retry-after": "not-a-number",
                },
                content=b"not json",
                request=httpx.Request("GET", "https://americas.api.riotgames.com"),
            )

    monkeypatch.setattr(request_module, "ApplicationRateLimiter", FakeApplicationLimiter)
    monkeypatch.setattr(request_module, "MethodRateLimiter", FakeMethodLimiter)
    monkeypatch.setattr(request_module, "ServiceRateLimiter", FakeServiceLimiter)
    monkeypatch.setattr(request_module, "UnspecifiedRiotRateLimiter", FakeUnspecifiedLimiter)
    monkeypatch.setattr(request_module, "ND_ENABLE_REQUEST_METRICS", 0)

    with pytest.raises(ApplicationRateLimitExceeded):
        await request_module._perform_riot_request(
            "https://americas.api.riotgames.com/lol/match/v5/matches/NA1_1",
            FakeClient(),
            object(),
        )

    assert block_calls[0][0] == 61
    assert block_calls[0][1]["body"] is None
