"""
Security Analyzer

Detects security vulnerabilities in AI-generated code:
- SQL injection patterns
- Command injection
- Hardcoded secrets
- Insecure configurations
- Dangerous function calls
"""

import ast
import re
from typing import List

from ai_trust_validator.analyzers import BaseAnalyzer
from ai_trust_validator.models import Issue


class SecurityAnalyzer(BaseAnalyzer):
    """Analyzes code for security vulnerabilities."""

    base_score = 100

    # Patterns for hardcoded secrets
    SECRET_PATTERNS = [
        (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+(["\'])', "Hardcoded password"),
        (r'(?i)(api_key|apikey|api-key)\s*=\s*["\'][^"\']+(["\'])', "Hardcoded API key"),
        (r'(?i)(secret|token)\s*=\s*["\'][^"\']+(["\'])', "Hardcoded secret/token"),
        (r'(?i)(aws_access_key|aws_secret)\s*=\s*["\'][^"\']+(["\'])', "Hardcoded AWS credentials"),
    ]

    # Dangerous functions that should be flagged
    DANGEROUS_FUNCTIONS = {
        "eval": "Use of eval() can execute arbitrary code",
        "exec": "Use of exec() can execute arbitrary code",
        "compile": "Compiling strings can execute arbitrary code",
        "__import__": "Dynamic imports can be exploited",
        "input": "In Python 2, input() evaluates code (use raw_input)",
    }

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'execute\s*\(\s*f["\']',  # execute(f"...")
        r'execute\s*\(\s*["\'].*%s.*["\'].*%',  # execute("...%s", ...)
        r'\+\s*["\'].*SELECT',  # string concat with SQL
        r'f["\'].*SELECT.*\{',  # f-string with SQL
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        (r'open\s*\(\s*f["\']', "Potential path traversal via f-string in open()"),
        (r'open\s*\(\s*["\'].*\.\.', "Path traversal: '..' in file path"),
        (r'Path\s*\(\s*f["\']', "Potential path traversal via f-string in Path()"),
    ]

    # SSRF (Server-Side Request Forgery) patterns
    SSRF_PATTERNS = [
        (r'requests\.(get|post|put|delete|patch)\s*\(\s*f["\']', "SSRF risk: user-controlled URL via f-string"),
        (r'urllib\.request\.urlopen\s*\(\s*f["\']', "SSRF risk: user-controlled URL via f-string"),
        (r'httpx\.(get|post)\s*\(\s*f["\']', "SSRF risk: user-controlled URL via f-string"),
    ]

    # YAML deserialization risk
    YAML_DESERIALIZATION = [
        (r'yaml\.load\s*\(', "yaml.load() without Loader is unsafe, use yaml.safe_load()"),
        (r'yaml\.load\s*\([^)]*\bLoader\s*=\s*None\b', "yaml.load with Loader=None is unsafe"),
        (r'pickle\.load\s*\(', "pickle.load() can execute arbitrary code, use json instead"),
        (r'pickle\.loads\s*\(', "pickle.loads() can execute arbitrary code"),
    ]

    # Hardcoded URLs / internal IPs
    INTERNAL_URL_PATTERNS = [
        (r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+|192\.168\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+)', "Hardcoded internal URL detected"),
    ]

    def analyze(self, tree: ast.AST, code: str) -> List[Issue]:
        """Analyze code for security issues."""
        issues: List[Issue] = []

        # Check for hardcoded secrets
        issues.extend(self._check_secrets(code))

        # Walk AST for structural issues
        for node in ast.walk(tree):
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                issues.extend(self._check_dangerous_call(node))

            # Check for SQL injection patterns
            if isinstance(node, ast.Call):
                issues.extend(self._check_sql_injection(node, code))

            # Check for insecure subprocess calls
            if isinstance(node, ast.Call):
                issues.extend(self._check_subprocess(node))

            # Check for os.system calls
            issues.extend(self._check_os_system(node))

        # Check for path traversal, SSRF, YAML deserialization
        issues.extend(self._check_pattern_list(code, self.PATH_TRAVERSAL_PATTERNS, "high", "security"))
        issues.extend(self._check_pattern_list(code, self.SSRF_PATTERNS, "high", "security"))
        issues.extend(self._check_pattern_list(code, self.YAML_DESERIALIZATION, "critical", "security"))
        issues.extend(self._check_pattern_list(code, self.INTERNAL_URL_PATTERNS, "medium", "security"))

        return issues

    def _check_secrets(self, code: str) -> List[Issue]:
        """Check for hardcoded secrets."""
        issues: List[Issue] = []
        lines = code.split("\n")

        for pattern, message in self.SECRET_PATTERNS:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append(Issue(
                        severity="high",
                        category="security",
                        message=message,
                        line=i,
                        suggestion="Use environment variables or secret management"
                    ))

        return issues

    def _check_dangerous_call(self, node: ast.Call) -> List[Issue]:
        """Check for dangerous function calls."""
        issues: List[Issue] = []

        func_name = self._get_func_name(node)
        if func_name in self.DANGEROUS_FUNCTIONS:
            severity = "critical" if func_name in ("eval", "exec") else "high"
            issues.append(Issue(
                severity=severity,
                category="security",
                message=self.DANGEROUS_FUNCTIONS[func_name],
                line=self._get_line(node),
                suggestion=f"Avoid {func_name}() or sanitize inputs carefully"
            ))

        return issues

    def _check_sql_injection(self, node: ast.Call, code: str) -> List[Issue]:
        """Check for SQL injection patterns."""
        issues: List[Issue] = []

        func_name = self._get_func_name(node)
        if func_name in ("execute", "executemany", "raw"):
            # Check if the call uses f-string or string formatting
            if node.args:
                arg = node.args[0]
                if isinstance(arg, ast.JoinedStr):  # f-string
                    issues.append(Issue(
                        severity="critical",
                        category="security",
                        message="Potential SQL injection via f-string",
                        line=self._get_line(node),
                        suggestion="Use parameterized queries with placeholders"
                    ))
                elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                    issues.append(Issue(
                        severity="high",
                        category="security",
                        message="Potential SQL injection via string formatting",
                        line=self._get_line(node),
                        suggestion="Use parameterized queries instead of % formatting"
                    ))

        return issues

    def _check_subprocess(self, node: ast.Call) -> List[Issue]:
        """Check for insecure subprocess calls."""
        issues: List[Issue] = []

        func_name = self._get_func_name(node)
        if func_name == "call" or func_name == "run":
            # Check if shell=True
            for kw in node.keywords:
                if kw.arg == "shell":
                    if isinstance(kw.value, ast.Constant) and kw.value.value:
                        issues.append(Issue(
                            severity="high",
                            category="security",
                            message="subprocess with shell=True is vulnerable to injection",
                            line=self._get_line(node),
                            suggestion="Remove shell=True and pass arguments as list"
                        ))

        return issues

    def _check_os_system(self, node: ast.AST) -> List[Issue]:
        """Check for os.system calls."""
        issues: List[Issue] = []

        if isinstance(node, ast.Call):
            func_name = self._get_func_name(node)
            if func_name == "system":
                issues.append(Issue(
                    severity="high",
                    category="security",
                    message="os.system() is vulnerable to command injection",
                    line=self._get_line(node),
                    suggestion="Use subprocess.run() with shell=False"
                ))

        return issues

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _check_pattern_list(self, code: str, patterns: list, severity: str, category: str) -> List[Issue]:
        """Check code against a list of (regex, message) patterns."""
        issues: List[Issue] = []
        lines = code.split("\n")
        for pattern, message in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append(Issue(
                        severity=severity,
                        category=category,
                        message=message,
                        line=i,
                    ))
        return issues
