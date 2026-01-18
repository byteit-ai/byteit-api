# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-18

### Added
- Initial release of the ByteIT Python SDK
- `ByteITClient` for AI-powered document parsing
- Multiple output formats: text, JSON, Markdown, HTML
- Input connectors:
  - `LocalFileInputConnector`
  - `S3InputConnector`
- Output connector:
  - `LocalFileOutputConnector`
- Job management (list jobs, check status, download results)
- Support for PDF, Word, Excel, and other common document formats
- Batch processing support
- Environment variable configuration
- Custom base URL support (testing & staging)
- Python 3.8+ support
