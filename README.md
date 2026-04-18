<div align="center">

# 🛡️ AI Code Trust Validator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/rudra496/ai-code-trust-validator.svg?style=social)](https://github.com/rudra496/ai-code-trust-validator/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/rudra496/ai-code-trust-validator.svg?style=social)](https://github.com/rudra496/ai-code-trust-validator/network/members)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://github.com/rudra496/ai-code-trust-validator/pkgs/container/ai-code-trust-validator)
[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue?logo=visualstudiocode)](vscode-extension/)
[![JetBrains](https://img.shields.io/badge/JetBrains-Plugin-purple?logo=jetbrains)](jetbrains-plugin/)

**Trust your AI-generated code before shipping to production.**

*The complete quality gate for AI-assisted development*

[Installation](#-installation) • [Quick Start](#-quick-start) • [Features](#-features) • [CLI Reference](#-cli-reference) • [Documentation](#-documentation)

</div>

---

## 🎯 The Problem

**84% of developers use AI coding tools. Only 29% trust the output.** Studies show most developers use AI coding tools but few fully trust the output.

AI writes code fast, but that code often contains:
- 🔓 **Security vulnerabilities** — SQL injection, hardcoded secrets, command injection
- 🎭 **Hallucinations** — Fake imports, invented functions, imaginary APIs
- 🐛 **Logic errors** — Unreachable code, infinite loops, dead branches
- 📉 **Technical debt** — Missing docs, poor naming, deep nesting
- 🔗 **Dependency issues** — Circular imports, missing modules, unused code

**You can't ship what you can't trust.**

---

## ✨ Features

| Category | Features |
|----------|----------|
| **🔍 Analysis** | Security scanning, Hallucination detection, Logic validation, Best practices |
| **🌐 Multi-Language** | Python, JavaScript, TypeScript support |
| **🤖 AI Auto-Fix** | LLM-powered fixes (OpenAI, Anthropic, Ollama) |
| **📊 Reports** | JSON, HTML (beautiful dashboard), SARIF (GitHub Security), PDF |
| **🔧 Fixes** | Auto-fix suggestions, Confidence scores, One-click apply |
| **🧪 Testing** | Auto-generate pytest tests, Edge case detection, Coverage analysis |
| **🌐 API** | REST API server, OpenAPI docs, Batch validation, Webhook support |
| **👀 Monitoring** | File watch mode, Live dashboard, Continuous validation |
| **📦 Multi-file** | Dependency analysis, Circular dependency detection, Import validation |
| **⚡ Performance** | Intelligent caching, Incremental analysis, Fast analysis with intelligent caching |
| **🔌 Extensible** | Plugin system, Custom analyzers, Hook system |
| **🐳 Deployment** | Docker, Docker Compose, GitHub Action, Pre-commit hooks |
| **💻 IDE Integration** | VS Code extension, JetBrains plugin, LSP server |
| **📈 Team Analytics** | Dashboard, Leaderboards, Trend analysis, Project breakdown |

---

## 📦 Installation

```bash
# From PyPI (recommended)
pip install ai-trust-validator

# With server support
pip install ai-trust-validator[server]

# With all extras
pip install ai-trust-validator[all]

# From source
git clone https://github.com/rudra496/ai-code-trust-validator.git
cd ai-code-trust-validator
pip install -e ".[all]"

# Docker
docker pull ghcr.io/rudra496/ai-code-trust-validator:latest
docker run -v ./code:/code ghcr.io/rudra496/ai-code-trust-validator validate /code
```

---

## 🚀 Quick Start

### CLI

```bash
# Validate a file (Python, JS, or TS)
aitrust validate generated_code.py
aitrust validate src/app.js
aitrust validate src/component.tsx

# Validate directory with minimum score
aitrust validate src/ --min-score 75 --strict

# Generate HTML report
aitrust report src/ --format html --output report.html

# Get fix suggestions
aitrust suggest-fixes buggy_code.py

# AI-powered auto-fix (requires API key)
export OPENAI_API_KEY="sk-..."
aitrust ai-fix file.py --apply

# Generate tests
aitrust generate-tests module.py --output tests/test_module.py

# Start API server
aitrust serve --port 8080

# Watch for changes with live dashboard
aitrust watch src/ --dashboard

# Analyze dependencies
aitrust analyze-deps src/

# Run benchmarks
aitrust benchmark --iterations 100

# View team analytics
aitrust analytics --days 30

# Start LSP server (for IDE integration)
aitrust lsp

# Show supported languages
aitrust languages
```

### Python API

```python
from ai_trust_validator import Validator, Config, MultiLanguageValidator

# Simple validation (auto-detects language)
validator = MultiLanguageValidator()
result = validator.validate("generated_code.py")  # or .js, .ts files

print(f"Trust Score: {result.trust_score}/100")
print(f"Passed: {result.passed}")

for issue in result.critical_issues:
    print(f"[CRITICAL] {issue.message}")
    if issue.suggestion:
        print(f"  💡 {issue.suggestion}")

# With custom config
config = Config(min_score=80, strict_mode=True)
validator = Validator(config)
result = validator.validate_code(code_string)

# Multi-file analysis
from ai_trust_validator import MultiFileAnalyzer
analyzer = MultiFileAnalyzer(validator)
result = analyzer.analyze_directory("src/")
print(f"Circular deps: {result.circular_dependencies}")

# Team analytics
from ai_trust_validator import AnalyticsDB
db = AnalyticsDB()
db.record_validation("file.py", result, user="dev1", project="myapp")
stats = db.get_stats(days=30)
print(f"Team avg: {stats.average_score}")
```

---

## 🌐 JavaScript/TypeScript Support

The validator supports JavaScript and TypeScript files with comprehensive analysis:

### Supported File Types

| Language | Extensions | Analysis Type |
|----------|------------|---------------|
| JavaScript | .js, .mjs, .cjs, .jsx | Pattern-based analysis |
| TypeScript | .ts, .tsx, .mts | JS + type checking |

### Security Checks for JS/TS

- `eval()`, `new Function()` - Code injection risks
- `innerHTML`, `outerHTML` - XSS vulnerabilities
- `document.write()` - XSS and DOM manipulation risks
- `setTimeout(string)` - Code injection via strings
- Prototype pollution (`__proto__`, `constructor.prototype`)
- Hardcoded secrets and API keys
- `child_process.exec()` - Command injection
- `@ts-ignore`, `any` type - Type safety bypass

### Hallucination Detection

- Detects hallucinated npm packages
- Identifies fake/invented functions
- Checks for placeholder API URLs

### Usage

```python
from ai_trust_validator import MultiLanguageValidator, detect_language

validator = MultiLanguageValidator()

# Auto-detects language from file extension
result = validator.validate("src/app.js")
print(f"Language: {detect_language('src/app.js')}")  # 'javascript'
print(f"Trust Score: {result.trust_score}/100")
```

---

## 🤖 AI-Powered Auto-Fix

Use LLMs to automatically fix detected issues. Supports multiple providers:

### Supported Providers

| Provider | Environment Variable | Default Model |
|----------|---------------------|---------------|
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-haiku-20240307 |
| Ollama | `USE_OLLAMA=true` | llama3 |
| Custom | `LLM_BASE_URL` + `LLM_API_KEY` | configurable |

### CLI Usage

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."

# Fix a file (shows fixed code)
aitrust ai-fix file.py

# Apply fixes directly (creates .backup file)
aitrust ai-fix file.py --apply

# Fix only security issues
aitrust ai-fix file.py --category security

# Use different provider/model
aitrust ai-fix file.js --provider ollama --model llama3
aitrust ai-fix file.ts --provider anthropic --model claude-3-haiku-20240307
```

### Python API

```python
from ai_trust_validator import Validator, AIAutoFixer, LLMConfig

# Configure LLM
config = LLMConfig(
    provider="openai",
    model="gpt-4o-mini",
    api_key="sk-..."
)

fixer = AIAutoFixer(config)
validator = Validator()

# Validate and fix
code = open("file.py").read()
result = validator.validate(code, is_file=False)
fix_result = fixer.fix(code, result.all_issues, language="python")

if fix_result.success:
    print(f"Fixed with {fix_result.confidence:.0%} confidence")
    print(fix_result.fixed_code)
```

### Quick Fix Function

```python
from ai_trust_validator import ai_fix_code

result = ai_fix_code(
    code,
    issues,
    language="javascript",
    api_key="sk-..."
)
print(result.fixed_code)
```

---

## 💻 IDE Integration

### VS Code

```bash
# Install from VS Code Marketplace
# Search for "AI Trust Validator"

# Or install manually
cd vscode-extension
npm install
npm run compile
```

Features:
- Real-time diagnostics
- Trust score in status bar
- Quick fix suggestions
- Hover information
- Auto-validate on save

### JetBrains (IntelliJ, PyCharm)

```bash
# Install from JetBrains Marketplace
# Search for "AI Trust Validator"

# Or build from source
cd jetbrains-plugin
./gradlew build
# Install the built plugin from build/distributions/
```

Features:
- Real-time code analysis with inline warnings
- Trust score in status bar
- Tool window with detailed results
- One-click AI-powered fixes
- Project-wide validation

### LSP Server (Neovim, Emacs, etc.)

```bash
# Start LSP server
aitrust lsp

# Configure in your LSP client
# Command: aitrust lsp
# Language: python, javascript, typescript
```

---

## 📊 Example Output

```
🔍 Analyzing: generated_code.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 TRUST SCORE: 67/100 ⚠️

┌─────────────────────────────────────────────────────┐
│ Category              Score   Issues               │
├─────────────────────────────────────────────────────┤
│ Security              72      2 medium, 1 low      │
│ Hallucinations        45      3 critical           │
│ Logic                 85      1 minor              │
│ Best Practices        70      2 warnings           │
└─────────────────────────────────────────────────────┘

🚨 Critical Issues:
  [HALLUCINATION] Line 12: Import 'fancy_lib' does not exist
  [HALLUCINATION] Line 18: Function 'quick_sort_v2' not defined
  [SECURITY] Line 24: Potential SQL injection via f-string

💡 AI Suggestions:
  → Replace 'fancy_lib' with 'numpy' or 'pandas'
  → Use built-in sorted() instead of 'quick_sort_v2'
  → Use parameterized queries: cursor.execute("... WHERE id = ?", (user_id,))
```

---

## 🔧 CLI Reference

| Command | Description |
|---------|-------------|
| `aitrust validate <path>` | Validate code and show trust score |
| `aitrust report <path>` | Generate detailed report (JSON/HTML/SARIF) |
| `aitrust suggest-fixes <path>` | Show fix suggestions for issues |
| `aitrust ai-fix <path>` | Apply AI-powered fixes |
| `aitrust generate-tests <path>` | Generate pytest tests |
| `aitrust serve` | Start REST API server |
| `aitrust watch <path>` | Watch files for changes |
| `aitrust benchmark` | Run performance benchmarks |
| `aitrust analyze-deps <path>` | Multi-file dependency analysis |
| `aitrust analytics` | View team analytics |
| `aitrust cache <action>` | Manage validation cache |
| `aitrust lsp` | Start LSP server for IDEs |
| `aitrust languages` | Show supported languages |

---

## 🐳 Docker & Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  validator:
    image: ghcr.io/rudra496/ai-code-trust-validator:latest
    ports:
      - "8080:8080"
    command: serve --port 8080
    volumes:
      - ./code:/code:ro
      - ./.aitrust_cache:/app/.aitrust_cache
```

### GitHub Action

```yaml
name: AI Code Trust Check
on: [pull_request]

jobs:
  trust-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate AI Code
        uses: rudra496/ai-code-trust-validator@v0.4.0
        with:
          path: 'src/'
          min-score: '75'
          format: 'sarif'
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/rudra496/ai-code-trust-validator
    rev: v0.4.0
    hooks:
      - id: ai-trust-validator
        args: ['--min-score', '70']
```

---

## 🔌 Plugin System

Create custom analyzers:

```python
from ai_trust_validator import AnalyzerPlugin, PluginMetadata, Issue

class MyCustomAnalyzer(AnalyzerPlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="my_custom",
            version="1.0.0",
            author="You",
            description="Custom analyzer"
        )
    
    def analyze(self, tree, code, context):
        issues = []
        # Your analysis logic
        return issues

# Register
from ai_trust_validator import PluginManager
manager = PluginManager()
manager.register(MyCustomAnalyzer())
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Throughput | Fast analysis with intelligent caching |
| Avg validation | 5-20ms per file |
| Memory | <50MB typical |
| Cache hit rate | 95%+ on re-runs |

Run your own benchmarks:
```bash
aitrust benchmark --iterations 1000
```

---

## 🗺️ Roadmap

### Completed ✅

- [x] Core validation engine
- [x] Security analyzer
- [x] Hallucination detector
- [x] Logic analyzer
- [x] Best practices checker
- [x] CLI with rich output
- [x] JSON/HTML/SARIF reports
- [x] Fix suggestions
- [x] Test generation
- [x] REST API server
- [x] Docker support
- [x] GitHub Action
- [x] Pre-commit hooks
- [x] Plugin system
- [x] Multi-file analysis
- [x] Watch mode
- [x] Caching system
- [x] LSP server
- [x] VS Code extension
- [x] Web dashboard
- [x] Team analytics
- [x] **JavaScript/TypeScript support** (NEW in v0.4.0)
- [x] **AI-powered auto-fix with LLM integration** (NEW in v0.4.0)
- [x] **JetBrains plugin (IntelliJ, PyCharm)** (NEW in v0.4.0)

### Coming Soon 🚧

- [ ] Cloud hosted version

---

## 📊 Statistics

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/rudra496/ai-code-trust-validator)
![GitHub last commit](https://img.shields.io/github/last-commit/rudra496/ai-code-trust-validator)
![GitHub code size](https://img.shields.io/github/languages/code-size/rudra496/ai-code-trust-validator)
![GitHub issues](https://img.shields.io/github/issues/rudra496/ai-code-trust-validator)

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to help:**
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit pull requests
- ⭐ Star the repo!

---

## ⭐ Star History

<a href="https://star-history.com/#rudra496/ai-code-trust-validator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=rudra496/ai-code-trust-validator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=rudra496/ai-code-trust-validator&type=Date" />
   <img alt="Star History" src="https://api.star-history.com/svg?repos=rudra496/ai-code-trust-validator&type=Date" />
 </picture>
</a>

---

## 📄 License

MIT License — use it freely. Just don't blame us if AI breaks production. 😉

---

<div align="center">

## 🔗 Connect with the Creator

**[Rudra Sarker](https://rudra496.github.io/site)** • Developer & Researcher

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/rudrasarker)
[![Portfolio](https://img.shields.io/badge/Portfolio-Visit-green?logo=google-chrome)](https://rudra496.github.io/site)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?logo=github)](https://github.com/rudra496)

---

**Built to close the AI trust gap.** 

*If this helped you, consider giving it a ⭐ — it helps others find it too!*

**Made with ❤️ by [Rudra Sarker](https://rudra496.github.io/site)**

</div>
