"""AI Code Trust Validator - v0.4.0"""
__version__ = "0.4.0"
__author__ = "Rudra Sarker"
__email__ = "rudra496@users.noreply.github.com"
__url__ = "https://github.com/rudra496/ai-code-trust-validator"

from ai_trust_validator.config import Config
from ai_trust_validator.models import CategoryScore, Issue, ValidationResult
from ai_trust_validator.validator import Validator
from ai_trust_validator.analyzers.best_practices import BestPracticesAnalyzer
from ai_trust_validator.analyzers.hallucination import HallucinationAnalyzer
from ai_trust_validator.analyzers.js_hallucination import JSHallucinationAnalyzer
from ai_trust_validator.analyzers.js_security import JSSecurityAnalyzer
from ai_trust_validator.analyzers.logic import LogicAnalyzer
from ai_trust_validator.analyzers.security import SecurityAnalyzer
from ai_trust_validator.ai_fix import AIAutoFixer, FixResult, LLMConfig, ai_fix_code
from ai_trust_validator.analytics import AnalyticsDB, TeamStats, generate_analytics_report
from ai_trust_validator.api_server import run_server
from ai_trust_validator.benchmark import BenchmarkSuite, run_full_benchmark
from ai_trust_validator.cache import CacheEntry, CacheManager
from ai_trust_validator.fixer import FixSuggestion, FixSuggester
from ai_trust_validator.languages import detect_language, get_parser
from ai_trust_validator.lsp_server import LSPServer, run_lsp_server
from ai_trust_validator.multi_file import MultiFileAnalyzer, MultiFileResult
from ai_trust_validator.multi_lang_validator import MultiLanguageValidator
from ai_trust_validator.plugin import AnalyzerPlugin, PluginManager, PluginMetadata
from ai_trust_validator.reporters import HTMLReporter, JSONReporter, SARIFReporter
from ai_trust_validator.test_generator import TestGenerator
from ai_trust_validator.watcher import Watcher, watch_with_dashboard

__all__ = [
    "AnalyzerPlugin", "AnalyticsDB", "AIAutoFixer", "BestPracticesAnalyzer",
    "BenchmarkSuite", "CacheEntry", "CacheManager", "CategoryScore", "Config",
    "FixResult", "FixSuggestion", "FixSuggester", "HallucinationAnalyzer",
    "HTMLReporter", "Issue", "JSONReporter", "JSHallucinationAnalyzer",
    "JSSecurityAnalyzer", "LLMConfig", "LSPServer", "LogicAnalyzer",
    "MultiFileAnalyzer", "MultiFileResult", "MultiLanguageValidator",
    "PluginManager", "PluginMetadata", "SARIFReporter", "SecurityAnalyzer",
    "TestGenerator", "Validator", "Watcher",
    "__author__", "__email__", "__url__", "__version__",
    "ai_fix_code", "detect_language", "generate_analytics_report",
    "get_parser", "run_full_benchmark", "run_lsp_server", "run_server",
    "watch_with_dashboard",
]
