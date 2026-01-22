# Changelog

All notable changes to this project will be documented in this file.


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

