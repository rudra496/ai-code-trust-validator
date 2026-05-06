"""
Core Validator Module

Main validation engine that orchestrates all analyzers and produces trust scores.
"""

import ast
from pathlib import Path
from typing import Optional

from ai_trust_validator.analyzers.best_practices import BestPracticesAnalyzer
from ai_trust_validator.analyzers.hallucination import HallucinationAnalyzer
from ai_trust_validator.analyzers.logic import LogicAnalyzer
from ai_trust_validator.analyzers.security import SecurityAnalyzer
from ai_trust_validator.config import Config
from ai_trust_validator.models import CategoryScore, Issue, ValidationResult


class Validator:
    """
    Main validator class that coordinates all analyzers.

    Usage:
        validator = Validator()
        result = validator.validate("path/to/file.py")
        print(f"Trust score: {result.trust_score}")
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._analyzers = self._init_analyzers()

    def _init_analyzers(self) -> dict:
        """Initialize all enabled analyzers."""
        analyzers = {}

        if self.config.checks.security.enabled:
            analyzers["security"] = SecurityAnalyzer(self.config)
        if self.config.checks.hallucinations.enabled:
            analyzers["hallucinations"] = HallucinationAnalyzer(self.config)
        if self.config.checks.logic.enabled:
            analyzers["logic"] = LogicAnalyzer(self.config)
        if self.config.checks.best_practices.enabled:
            analyzers["best_practices"] = BestPracticesAnalyzer(self.config)

        return analyzers

    def validate(self, source: str | Path, is_file: bool = True) -> ValidationResult:
        """
        Validate source code and return a trust score.

        Args:
            source: File path or code string
            is_file: True if source is a file path, False if code string

        Returns:
            ValidationResult with trust score and issues
        """
        if is_file:
            file_path = str(source)
            code = Path(source).read_text(encoding="utf-8")
        else:
            file_path = None
            code = str(source)

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                file_path=file_path,
                trust_score=0,
                categories={},
                all_issues=[Issue(
                    severity="critical",
                    category="logic",
                    message=f"Syntax error: {e.msg}",
                    line=e.lineno,
                    suggestion="Fix syntax errors before validation"
                )]
            )

        categories: dict[str, CategoryScore] = {}
        all_issues: list[Issue] = []

        for name, analyzer in self._analyzers.items():
            weight = getattr(self.config.checks, name.replace("-", "_")).weight
            issues = analyzer.analyze(tree, code)
            score = self._calculate_score(issues, analyzer.base_score)

            categories[name] = CategoryScore(
                score=score,
                weight=weight,
                issues=issues
            )
            all_issues.extend(issues)

        total_weight = sum(c.weight for c in categories.values())
        weighted_sum = sum(c.weighted_score() for c in categories.values())
        trust_score = int(weighted_sum / total_weight) if total_weight > 0 else 0

        return ValidationResult(
            file_path=file_path,
            trust_score=min(100, max(0, trust_score)),
            categories=categories,
            all_issues=all_issues
        )

    def _calculate_score(self, issues: list[Issue], base_score: int) -> int:
        """Calculate score based on issues found."""
        score = base_score

        for issue in issues:
            if issue.severity == "critical":
                score -= 25
            elif issue.severity == "high":
                score -= 15
            elif issue.severity == "medium":
                score -= 8
            elif issue.severity == "low":
                score -= 3

        return min(100, max(0, score))

    def validate_directory(
        self,
        directory: str | Path,
        pattern: str = "**/*.py"
    ) -> list[ValidationResult]:
        """
        Validate all matching files in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for files to validate

        Returns:
            List of ValidationResult for each file
        """
        results = []
        dir_path = Path(directory)

        for file_path in dir_path.glob(pattern):
            if any(str(file_path).startswith(str(dir_path / ignore))
                   for ignore in self.config.ignore):
                continue

            results.append(self.validate(file_path))

        return results
