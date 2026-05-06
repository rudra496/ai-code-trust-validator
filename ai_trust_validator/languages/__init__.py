"""Multi-language support module."""
from ai_trust_validator.languages.base import LanguageParser, ParseResult
from ai_trust_validator.languages.javascript_parser import JavaScriptParser
from ai_trust_validator.languages.python_parser import PythonParser
from ai_trust_validator.languages.typescript_parser import TypeScriptParser

LANGUAGE_MAP = {
    '.py': 'python', '.js': 'javascript', '.mjs': 'javascript',
    '.cjs': 'javascript', '.jsx': 'javascript', '.ts': 'typescript',
    '.tsx': 'typescript', '.mts': 'typescript',
}

def get_parser(file_path: str, language: str = None):
    from pathlib import Path
    lang = language.lower() if language else LANGUAGE_MAP.get(Path(file_path).suffix.lower(), 'python')
    parsers = {'python': PythonParser, 'javascript': JavaScriptParser, 'typescript': TypeScriptParser}
    return parsers.get(lang, PythonParser)()

def detect_language(file_path: str) -> str:
    from pathlib import Path
    return LANGUAGE_MAP.get(Path(file_path).suffix.lower(), 'python')
