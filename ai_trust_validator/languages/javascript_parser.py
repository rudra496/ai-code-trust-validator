"""JavaScript/TypeScript language parser using regex-based analysis."""
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from ai_trust_validator.languages.base import LanguageParser, ParseResult


@dataclass
class JSNode:
    type: str
    line: int
    name: str = None
    value: str = None

class JavaScriptParser(LanguageParser):
    language = "javascript"
    extensions = [".js", ".mjs", ".cjs", ".jsx"]

    PATTERNS = {
        'import_default': re.compile(r'import\s+(\w+)\s+from\s*["\']([^"\']+)["\']'),
        'import_named': re.compile(r'import\s+\{([^}]+)\}\s+from\s*["\']([^"\']+)["\']'),
        'require': re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*["\']([^"\']+)["\']\s*\)'),
        'function_decl': re.compile(r'function\s+(\w+)\s*\(([^)]*)\)'),
        'arrow_func': re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>'),
        'class_decl': re.compile(r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{'),
        'eval': re.compile(r'\beval\s*\('),
        'inner_html': re.compile(r'\.innerHTML\s*='),
    }

    def parse(self, code: str) -> ParseResult:
        lines = code.split('\n')
        return ParseResult(success=True, ast=[], code=code, language="javascript", lines=lines,
            imports=[m.group(2) for m in self.PATTERNS['import_default'].finditer(code)] +
                    [m.group(2) for m in self.PATTERNS['import_named'].finditer(code)],
            functions=[m.group(1) for m in self.PATTERNS['function_decl'].finditer(code)],
            classes=[m.group(1) for m in self.PATTERNS['class_decl'].finditer(code)])

    def get_line(self, node: Any) -> int:
        return getattr(node, "line", 0) if hasattr(node, "line") else 0

    def find_security_issues(self, code: str) -> List[Dict]:
        issues, lines = [], code.split('\n')
        security_patterns = [
            (self.PATTERNS['eval'], 'critical', 'eval() can execute arbitrary code'),
            (self.PATTERNS['inner_html'], 'high', 'innerHTML can lead to XSS'),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, severity, message in security_patterns:
                if pattern.search(line) and not line.strip().startswith('//'):
                    issues.append({'severity': severity, 'message': message, 'line': i})
        return issues

    def find_best_practice_issues(self, code: str) -> List[Dict]:
        issues, lines = [], code.split('\n')
        patterns = [
            (re.compile(r'\bvar\s+\w+'), 'info', 'Use let or const instead of var'),
            (re.compile(r'==\s*[^=]'), 'medium', 'Use === instead of =='),
            (re.compile(r'console\.(log|debug|info)'), 'info', 'Remove console statements'),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, severity, message in patterns:
                if pattern.search(line) and not line.strip().startswith('//'):
                    issues.append({'severity': severity, 'message': message, 'line': i})
        return issues

class TypeScriptParser(JavaScriptParser):
    language = "typescript"
    extensions = [".ts", ".tsx", ".mts"]
