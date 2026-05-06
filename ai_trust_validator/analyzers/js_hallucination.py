"""JavaScript/TypeScript Hallucination Analyzer."""
import re
from typing import List

from ai_trust_validator.models import Issue


class JSHallucinationAnalyzer:
    base_score = 100

    HALLUCINATED_PACKAGES = {
        'node-fetch-common': ('critical', 'node-fetch or undici'),
        'lodash-helpers': ('critical', 'lodash'),
        'axios-extensions': ('critical', 'axios or axios-cache-adapter'),
        'moment-plus': ('critical', 'moment or dayjs'),
        'javascript-utils': ('high', 'Native JS or lodash'),
    }

    HALLUCINATED_FUNCTIONS = {
        'quickSort': ('high', 'array.sort(compareFn)'),
        'unique': ('high', '[...new Set(array)]'),
        'capitalize': ('medium', "str.charAt(0).toUpperCase() + str.slice(1)"),
        'contains': ('medium', 'str.includes()'),
        'findAll': ('high', 'querySelectorAll()'),
        'addClass': ('high', 'element.classList.add()'),
        'fetch.get': ('high', 'fetch(url)'),
        'fetch.post': ('high', 'fetch(url, { method: "POST" })'),
    }

    def analyze(self, code: str, lines: List[str]) -> List[Issue]:
        issues = []
        # Check imports
        import_pattern = re.compile(r'(?:import|require)\s*\(?[\'"]([^\'"]+)[\'"]')
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(('//', '/*')): continue
            for match in import_pattern.finditer(line):
                pkg = match.group(1).split('/')[0]
                if pkg in self.HALLUCINATED_PACKAGES:
                    sev, alt = self.HALLUCINATED_PACKAGES[pkg]
                    issues.append(Issue(severity=sev, category="hallucination", message=f"Package '{pkg}' likely doesn't exist", line=i, suggestion=f"Use '{alt}' instead"))

        # Check function calls
        for func, (sev, alt) in self.HALLUCINATED_FUNCTIONS.items():
            pattern = re.compile(rf'\.{re.escape(func.split(".")[-1])}\s*\(')
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    issues.append(Issue(severity=sev, category="hallucination", message=f"Method '{func}()' may not exist", line=i, suggestion=f"Use {alt}"))
        return issues

    def check_api_endpoints(self, code: str, lines: List[str]) -> List[Issue]:
        issues = []
        patterns = [
            (re.compile(r'["\']https?://your-api'), 'high', 'Placeholder API URL'),
            (re.compile(r'["\']https?://api\.example'), 'high', 'Example API URL'),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, severity, message in patterns:
                if pattern.search(line):
                    issues.append(Issue(severity=severity, category="hallucination", message=message, line=i, suggestion="Replace with real API endpoint"))
        return issues
