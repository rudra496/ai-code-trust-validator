"""JavaScript/TypeScript Security Analyzer."""
import re
from typing import List
from ai_trust_validator.models import Issue

class JSSecurityAnalyzer:
    base_score = 100
    
    SECURITY_PATTERNS = [
        (re.compile(r'\beval\s*\('), "critical", "eval() can execute arbitrary code", "Avoid eval(). Use JSON.parse() for JSON."),
        (re.compile(r'\.innerHTML\s*='), "high", "innerHTML assignment can lead to XSS", "Use textContent or DOMPurify."),
        (re.compile(r'document\.write\s*\('), "high", "document.write() can lead to XSS", "Use DOM manipulation methods."),
        (re.compile(r'setTimeout\s*\(\s*["\']'), "high", "setTimeout with string executes code", "Use setTimeout(() => {...}, delay)."),
        (re.compile(r'(?i)(password|api_key|secret)\s*[=:]\s*["\'][^"\']+(["\'])'), "high", "Hardcoded secret detected", "Use environment variables."),
        (re.compile(r'__proto__\s*[=:]'), "critical", "__proto__ manipulation", "Use Object.create(null)."),
        (re.compile(r'child_process\.exec\s*\('), "critical", "Command injection risk", "Use execFile() or spawn()."),
        (re.compile(r'@ts-ignore'), "medium", "@ts-ignore bypasses type checking", "Fix the type error instead."),
    ]
    
    def analyze(self, code: str, lines: List[str]) -> List[Issue]:
        issues = []
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(('//', '/*', '*')): continue
            for pattern, severity, message, suggestion in self.SECURITY_PATTERNS:
                if pattern.search(line):
                    issues.append(Issue(severity=severity, category="security", message=message, line=i, suggestion=suggestion))
        return issues
    
    def detect_vulnerable_deps(self, code: str, lines: List[str]) -> List[Issue]:
        issues, vulnerable = [], {'event-stream': 'Known malicious package', 'lodash': 'Versions < 4.17.21 vulnerable'}
        for i, line in enumerate(lines, 1):
            for pkg, warning in vulnerable.items():
                if f"'{pkg}'" in line or f'"{pkg}"' in line:
                    issues.append(Issue(severity="high", category="security", message=f"Vulnerable dependency: {warning}", line=i))
        return issues
