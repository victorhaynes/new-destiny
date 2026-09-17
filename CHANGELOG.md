# Changelog

All notable changes to this project will be documented in this file.

## [0.3.8]
### Changed
- Included `enforcement_type` consistently in rate-limit events and replaced verbose expected Spectator `404` output with a structured no-active-game event without changing the exception contract.
- Replaced the boolean `ND_DEBUG` setting with required `ND_LOG_LEVEL` levels `0` through `3`. Production deployments can now capture errors and rate-limit events without successful request tracing; `ND_DEBUG` is no longer supported.

## [0.3.7]
### Changed
- Isolated unspecified Riot server-enforced throttles for the Spectator active-game endpoint to a method-and-routing-value Redis block instead of the shared subdomain fallback. This is necessary because Spectator endpoint requests have been observed receiving unexpected server-enforced throttles frequently (basically on every session opened) even while traffic remains well below Riot's communicated rate limits.
- Improved structured logging for external unexpected throttles, internal preflight blocks, retry metadata, and the resulting blocking scope.
- Replaced inconsistent Redis key names with the `nd:` namespace and a consistent scope/kind/routing-value layout. The Spectator exception uses the explicit `known-unpredictable` scope because that endpoint can be server-throttled while well below Riot's communicated limits, while truly unexpected throttles use `unspecified`. Existing Redis state is not migrated automatically; clear or expire old keys before adopting this schema.

## [0.3.6] - 2026-05-15
### Changed
- Relaxed minimum python requirement to 3.12.

## [0.3.5] - 2026-03-16
### Changed
- Clarified the schema-agnostic typing design in the README and documented a simple local `cast(..., Any)` pattern for callers who want less type-checker noise.
- Kept the public JSON helper API focused on the base `expect_*()` functions rather than adding field-specific sugar.
- Added focused tests for the JSON type helper behavior.

## [0.3.4] - 2026-03-16
### Changed
- Aligned `RiotAPIError.message` with the library's schema-agnostic `JSONValue` type so non-object JSON error bodies type-check correctly.
- Added and exported a typed `RiotOffendingContext` shape for captured Riot error metadata (`headers` plus `body`).
- Tightened exception and rate-limiter signatures to use the shared offending-context type consistently.

## [0.3.3] - 2026-03-16
### Changed
- File clean up.

## [0.3.2] - 2026-03-16
### Changed
- Folder cean up.

## [0.3.1] - 2026-03-16
### Changed
- Expanded the LoL rate limit map to cover `CHAMPION-V3`, `CLASH-V1`, `LOL-STATUS-V4`, `LOL-CHALLENGES-V1`, `SPECTATOR-V5`, `ACCOUNT-V1 /region/by-game`, and `MATCH-V5 /matches/by-puuid/{puuid}/replays`
- Fixed the `ACCOUNT-V1 active-shards` regex to match Riot's actual `/by-puuid/` path shape
- Added focused matcher coverage for the newly supported endpoint patterns

## [0.3.0] - 2026-01-22
### Changed
- The optional logging/output for the "attempts" and "network_tolerance" kwargs for `riot_request_with_retry`function is now more clear and has better wording.

## [0.2.9] - 2026-01-21
### Changed
- New "attempts" and "network_tolerance" kwargs available on `riot_request_with_retry` function
- Can now tolerate, sleep, and retry up to n-1 rate limit related errors or m-1 network related errors on-demand for an indvidual request. Totally optional to include. Separate tolerances/budgets for these two types of issues.

## [0.2.8] - 2026-01-21
### Changed
- Changelog versioning & dates correction
- pyproject.toml explicitly upadted to exclude files. Not strictly necessary but more safe.

## [0.2.7] - 2026-01-21
### Changed
- Improved typing
- Made core fields available for type-checkers on the RiotRelatedRateLimitException class
- Added new RiotNetworkError class so transient network issues do not get raised as RiotAPIError(s). These are semantically different
- Updated retry logic to work for both rate limit exceptions and RiotNetworkError(s)
- Made depdenencies less strict, more compatible

## [0.2.6] - 2025-12-17
### Changed
- Improved type safety across exception classes
- Added proper type hints across the package
- Should now play nicer with Pylance/MyPy
- Improved documentation

## [0.2.5] - 2025-06-17
### Changed
- Update to methods supported per Riot's deprecation of endpoints (https://x.com/riotgamesdevrel/status/1932188110454235582)
- Added changelog
- Updated project description

## [0.2.4] - 2025-06-17
### Changed
- Minor example & readme updates

## [0.2.2] - 2025-06-17
### Changed
- Minor example & readme updates

## [0.2.1] - 2025-06-05
### Changed
- Minor example & readme updates

## [0.2.0] - 2025-05-30
### Changed
- Edge cases & limitations laid out clearly in readme

## [0.1.8] - 2025-05-29
### Changed
- Minor example & readme updates

## [0.1.7] - 2025-05-29
### Changed
- Minor example & readme updates

## [0.1.6] - 2025-05-29
### Changed
- Minor example & readme updates

## [0.1.0] - 2024-06-07
### Added
- Initial release
