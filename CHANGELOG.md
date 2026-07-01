# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-beta.1] - 2026-07-01

### Added
- Core asynchronous `PrivacyGateway` pipeline architecture supporting both streaming and unary calls.
- Zero-Inference Mutation Engine for executing right-to-left character mutations.
- Policy evaluation schemas (`default`, `romania-gdpr`, `financial-services`, `healthcare-hipaa`).
- Translation adapters for OpenAI, Anthropic, and Azure OpenAI Service.
- High-speed `StreamingInterpolator` for continuous real-time response de-anonymization.

### Fixed
- Fixed token offset shifts during multiple multi-character string replacements.

### Security
- Implemented `RequestBlockedError` execution barrier preventing restricted PII from transiting to third-party endpoints.
