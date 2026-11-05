# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

### Changed

### Fixed

### Security

## [0.1.15-preview.1] - 2026-11-03

### Added

- Add regression coverage for the disabled SMS verification provider.

### Changed

- Bind client gateway ports to localhost by default and stop publishing internal service ports.
- Require distinct operator-supplied MySQL, MinIO, and Grafana passwords in the Compose environment stack.
- Apply the Compose MySQL and MinIO credentials to server configuration before startup.
- Fix the server container startup path so it launches binaries from `teamgramd/bin`.
- Correct deployment and compatibility documentation to describe the current server-only preview scope.
- Mark the first public release as a preview and document the upstream Teamgram attribution.

### Security

- Make the community `none` SMS verifier fail closed: it no longer returns a code or accepts a fixed code.
- Bind infrastructure, observability, and Elasticsearch host ports to localhost in the development Compose stack.

---

See [specs/release-and-changelog.md](specs/release-and-changelog.md) for version and release policy.
