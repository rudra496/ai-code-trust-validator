# Release Notes

All notable changes to AI Code Trust Validator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [v0.4.0] - 2026-05-06

### Added

- **JavaScript/TypeScript support** — Full analysis for `.js`, `.jsx`, `.ts`, `.tsx` files
  - Security scanning: `eval()`, `innerHTML`, XSS, prototype pollution, hardcoded secrets
  - Hallucination detection: fake npm packages, invented functions, placeholder URLs
  - Type safety checks: `@ts-ignore`, `any` type abuse
- **AI-powered auto-fix** — LLM integration to automatically fix detected issues
  - Support for OpenAI (GPT-4o-mini), Anthropic (Claude), Ollama (Llama), and custom providers
  - Confidence scoring on all fixes
  - One-click apply with automatic backup
  - Category-specific fixing (security, hallucination, logic, etc.)
- **JetBrains plugin** — Native IntelliJ IDEA and PyCharm integration
  - Real-time code analysis with inline warnings
  - Trust score in status bar
  - Tool window with detailed results
  - One-click AI-powered fixes
  - Project-wide validation
- **Web dashboard** — Interactive HTML dashboard with analytics
  - Team analytics with leaderboards
  - Trend analysis and project breakdown
  - Live dashboard in watch mode

### Changed

- Improved caching system for faster re-analysis
- Enhanced multi-language detection and routing

### Technical

- Plugin system for custom analyzers
- Hook system for extension points

---

## [v0.3.0] - 2026-05-05

### Added

- **VS Code extension** — Real-time validation in Visual Studio Code
  - Inline diagnostics on save
  - Trust score in status bar
  - Quick fix suggestions
  - Hover information
- **LSP server** — Language Server Protocol support for any LSP-compatible editor
  - Neovim, Emacs, Sublime Text, and more
- **Pre-commit hooks** — Validate code before every commit
- **GitHub Action** — CI/CD integration for pull requests
  - SARIF output for GitHub Security tab
  - Configurable minimum trust score
  - Block merge on low scores
- **Multi-file analysis** — Dependency graph analysis
  - Circular dependency detection
  - Import validation
  - Cross-file issue tracking
- **Watch mode** — Continuous validation on file changes
- **Team analytics** — Track validation trends across teams
- **Plugin system** — Extensible architecture for custom analyzers

### Changed

- Improved hallucination detection accuracy
- Faster AST parsing with intelligent caching

---

## [v0.2.0] - 2026-05-04

### Added

- **Security analyzer** — Detect common security vulnerabilities
  - SQL injection, command injection, hardcoded secrets
  - Path traversal, insecure deserialization
- **Hallucination detector** — Catch AI-generated fake code
  - Non-existent imports and packages
  - Invented function calls
  - Imaginary API endpoints
- **Logic analyzer** — Find logic errors in AI output
  - Unreachable code detection
  - Infinite loop detection
  - Dead branch analysis
- **Best practices checker** — Code quality rules
  - Naming conventions
  - Code complexity metrics
  - Documentation coverage
- **REST API server** — HTTP interface for integration
  - OpenAPI documentation
  - Batch validation endpoint
  - Webhook support
- **Multiple report formats** — JSON, HTML, SARIF

### Changed

- Replaced simple scoring with weighted category system
- Added configurable severity thresholds

---

## [v0.1.0] - 2026-05-03

### Added

- Initial release
- Core validation engine with AST-based Python analysis
- CLI with rich terminal output
- Trust score (0-100) with category breakdowns
- JSON report generation
- Docker support
- Configuration via `.aitrust.yaml`
- Basic test suite
