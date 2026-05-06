"""
SARIF Reporter - Output results in SARIF format for GitHub Advanced Security.
"""

import json
from typing import List
from ai_trust_validator.models import ValidationResult


class SARIFReporter:
    """Generate SARIF reports for GitHub Code Scanning integration."""

    def generate(self, results: List[ValidationResult]) -> str:
        """Generate SARIF report."""
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "AI Code Trust Validator",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/rudra496/ai-code-trust-validator",
                        "rules": self._generate_rules(results),
                        "organization": "rudra496"
                    }
                },
                "results": self._generate_results(results)
            }]
        }
        return json.dumps(sarif, indent=2)

    def _generate_rules(self, results: List[ValidationResult]) -> List[dict]:
        """Generate unique rules from all issues."""
        rules = {}
        
        for result in results:
            for issue in result.all_issues:
                rule_id = f"{issue.category}_{issue.severity}"
                if rule_id not in rules:
                    rules[rule_id] = {
                        "id": rule_id,
                        "name": f"{issue.category.title()} Issue",
                        "shortDescription": {
                            "text": f"{issue.severity.title()} {issue.category} issue detected"
                        },
                        "fullDescription": {
                            "text": f"Detected a {issue.severity} severity issue in the {issue.category} category during AI code validation."
                        },
                        "defaultConfiguration": {
                            "level": self._severity_to_level(issue.severity)
                        },
                        "helpUri": f"https://github.com/rudra496/ai-code-trust-validator/wiki/{issue.category}"
                    }
        
        return list(rules.values())

    def _generate_results(self, results: List[ValidationResult]) -> List[dict]:
        """Generate SARIF results."""
        sarif_results = []
        
        for result in results:
            if not result.file_path:
                continue
                
            for issue in result.all_issues:
                sarif_results.append({
                    "ruleId": f"{issue.category}_{issue.severity}",
                    "level": self._severity_to_level(issue.severity),
                    "message": {
                        "text": issue.message
                    },
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": result.file_path
                            },
                            "region": {
                                "startLine": issue.line or 1
                            } if issue.line else {}
                        }
                    }],
                    "properties": {
                        "suggestion": issue.suggestion,
                        "category": issue.category,
                        "severity": issue.severity
                    }
                })
        
        return sarif_results

    def _severity_to_level(self, severity: str) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "note"
        }
        return mapping.get(severity, "warning")
