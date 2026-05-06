"""
JSON Reporter - Output results in JSON format for CI/CD integration.
"""

import json
from typing import List
from ai_trust_validator.models import ValidationResult


class JSONReporter:
    """Generate JSON reports from validation results."""

    def __init__(self, pretty: bool = True):
        self.pretty = pretty

    def generate(self, results: List[ValidationResult]) -> str:
        """Generate JSON report from validation results."""
        data = {
            "summary": self._generate_summary(results),
            "results": [self._result_to_dict(r) for r in results]
        }
        indent = 2 if self.pretty else None
        return json.dumps(data, indent=indent)

    def _generate_summary(self, results: List[ValidationResult]) -> dict:
        """Generate summary statistics."""
        if not results:
            return {
                "total_files": 0,
                "average_score": 0,
                "passed": 0,
                "failed": 0,
                "total_issues": 0,
                "critical_issues": 0
            }

        total_issues = sum(len(r.all_issues) for r in results)
        critical = sum(len(r.critical_issues) for r in results)
        avg_score = sum(r.trust_score for r in results) / len(results)
        passed = sum(1 for r in results if r.passed)

        return {
            "total_files": len(results),
            "average_score": round(avg_score, 1),
            "passed": passed,
            "failed": len(results) - passed,
            "total_issues": total_issues,
            "critical_issues": critical,
            "pass_rate": round(passed / len(results) * 100, 1) if results else 0
        }

    def _result_to_dict(self, result: ValidationResult) -> dict:
        """Convert a single result to dictionary."""
        return {
            "file_path": result.file_path,
            "trust_score": result.trust_score,
            "passed": result.passed,
            "critical_count": len(result.critical_issues),
            "high_count": len(result.high_issues),
            "categories": {
                name: {
                    "score": cat.score,
                    "weight": cat.weight,
                    "issue_count": len(cat.issues)
                }
                for name, cat in result.categories.items()
            },
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "line": i.line,
                    "column": i.column,
                    "suggestion": i.suggestion
                }
                for i in result.all_issues
            ]
        }
