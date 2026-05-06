"""Multi-language Validator extending core validator for JS/TS support."""
import ast
from pathlib import Path
from typing import List, Optional

from ai_trust_validator.analyzers.js_hallucination import JSHallucinationAnalyzer
from ai_trust_validator.analyzers.js_security import JSSecurityAnalyzer
from ai_trust_validator.config import Config
from ai_trust_validator.languages import detect_language, get_parser
from ai_trust_validator.models import CategoryScore, Issue, ValidationResult
from ai_trust_validator.validator import Validator


class MultiLanguageValidator(Validator):
    """Extended validator supporting Python, JavaScript, and TypeScript."""

    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self._js_security = JSSecurityAnalyzer()
        self._js_hallucination = JSHallucinationAnalyzer()

    def validate(self, source: str | Path, is_file: bool = True) -> ValidationResult:
        if is_file:
            file_path, code = str(source), Path(source).read_text(encoding="utf-8")
            language = detect_language(file_path)
        else:
            file_path, code, language = None, str(source), "python"

        return self._validate_js_ts(code, file_path, language) if language in ("javascript", "typescript") else self._validate_python(code, file_path)

    def _validate_python(self, code: str, file_path: Optional[str]) -> ValidationResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(file_path=file_path, trust_score=0, categories={}, all_issues=[Issue(severity="critical", category="logic", message=f"Syntax error: {e.msg}", line=e.lineno)])

        categories, all_issues = {}, []
        for name, analyzer in self._analyzers.items():
            weight = getattr(self.config.checks, name.replace("-", "_")).weight
            issues = analyzer.analyze(tree, code)
            categories[name] = CategoryScore(score=self._calculate_score(issues, analyzer.base_score), weight=weight, issues=issues)
            all_issues.extend(issues)

        total_weight = sum(c.weight for c in categories.values())
        trust_score = int(sum(c.weighted_score() for c in categories.values()) / total_weight) if total_weight > 0 else 0
        return ValidationResult(file_path=file_path, trust_score=min(100, max(0, trust_score)), categories=categories, all_issues=all_issues)

    def _validate_js_ts(self, code: str, file_path: Optional[str], language: str) -> ValidationResult:
        lines = code.split('\n')
        parser = get_parser(file_path or "", language)
        categories, all_issues = {}, []

        # Security
        security_issues = self._js_security.analyze(code, lines) + self._js_security.detect_vulnerable_deps(code, lines)
        categories["security"] = CategoryScore(score=self._calculate_score(security_issues, 100), weight=self.config.checks.security.weight, issues=security_issues)
        all_issues.extend(security_issues)

        # Hallucinations
        hallucination_issues = self._js_hallucination.analyze(code, lines) + self._js_hallucination.check_api_endpoints(code, lines)
        categories["hallucinations"] = CategoryScore(score=self._calculate_score(hallucination_issues, 100), weight=self.config.checks.hallucinations.weight, issues=hallucination_issues)
        all_issues.extend(hallucination_issues)

        # Logic & Best Practices
        logic_issues, bp_issues = self._analyze_js_logic(code, lines), parser.find_best_practice_issues(code)
        bp_issues_obj = [Issue(severity=bp['severity'], category="best_practices", message=bp['message'], line=bp.get('line')) for bp in bp_issues]

        categories["logic"] = CategoryScore(score=self._calculate_score(logic_issues, 100), weight=self.config.checks.logic.weight, issues=logic_issues)
        categories["best_practices"] = CategoryScore(score=self._calculate_score(bp_issues_obj, 100), weight=self.config.checks.best_practices.weight, issues=bp_issues_obj)
        all_issues.extend(logic_issues + bp_issues_obj)

        total_weight = sum(c.weight for c in categories.values())
        trust_score = int(sum(c.weighted_score() for c in categories.values()) / total_weight) if total_weight > 0 else 0
        return ValidationResult(file_path=file_path, trust_score=min(100, max(0, trust_score)), categories=categories, all_issues=all_issues)

    def _analyze_js_logic(self, code: str, lines: List[str]) -> List[Issue]:
        import re
        issues = []
        patterns = [
            (re.compile(r'while\s*\(\s*true\s*\)\s*\{(?![^}]*break)'), 'high', 'Infinite loop without break'),
            (re.compile(r'for\s*\(\s*;\s*;\s*\)'), 'high', 'Infinite for loop'),
            (re.compile(r'await\s+\w+\s*;(?![^;]*catch)'), 'low', 'Async without error handling'),
        ]
        for i, line in enumerate(lines, 1):
            for pattern, severity, message in patterns:
                if pattern.search(line):
                    issues.append(Issue(severity=severity, category="logic", message=message, line=i))
        return issues

    def validate_directory(self, directory: str | Path, pattern: str = "**/*") -> list[ValidationResult]:
        results, dir_path, extensions = [], Path(directory), {'.py', '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.mts'}
        for file_path in dir_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                if not any(str(file_path).startswith(str(dir_path / ignore)) for ignore in self.config.ignore):
                    results.append(self.validate(file_path))
        return results
