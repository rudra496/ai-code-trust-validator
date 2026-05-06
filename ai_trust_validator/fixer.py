"""
Fix Suggester - Generate fix suggestions for common issues.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from ai_trust_validator.models import Issue, ValidationResult


@dataclass
class FixSuggestion:
    """A suggested fix for an issue."""
    issue: Issue
    original_code: str
    suggested_fix: str
    confidence: float  # 0.0 to 1.0
    auto_applicable: bool


class FixSuggester:
    """Generate fix suggestions for validation issues."""

    # Patterns for common fixes
    SQL_INJECTION_FIX = 'Use parameterized queries: cursor.execute("SELECT * FROM table WHERE id = ?", (value,))'
    HARDCODED_SECRET_FIX = 'Use environment variables: import os; password = os.environ.get("DB_PASSWORD")'
    EVAL_FIX = 'Avoid eval(). If necessary, use ast.literal_eval() for safe evaluation of literals.'
    BARE_EXCEPT_FIX = 'Use "except Exception:" to avoid catching SystemExit, KeyboardInterrupt, etc.'
    MUTABLE_DEFAULT_FIX = 'Use None as default and create inside function: def func(items=None): items = items or []'

    def __init__(self):
        self.auto_fixable = {
            "bare_except",
            "mutable_default",
            "unused_import",
        }

    def suggest_fixes(self, result: ValidationResult, code: str) -> List[FixSuggestion]:
        """Generate fix suggestions for all issues."""
        suggestions = []
        lines = code.split("\n")

        for issue in result.all_issues:
            suggestion = self._generate_fix(issue, lines)
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    def _generate_fix(self, issue: Issue, lines: List[str]) -> Optional[FixSuggestion]:
        """Generate a fix for a single issue."""
        original = lines[issue.line - 1] if issue.line and issue.line <= len(lines) else ""

        # Security fixes
        if issue.category == "security":
            return self._fix_security(issue, original)

        # Hallucination fixes
        elif issue.category == "hallucination":
            return self._fix_hallucination(issue, original)

        # Logic fixes
        elif issue.category == "logic":
            return self._fix_logic(issue, original, lines)

        # Best practices fixes
        elif issue.category == "best_practices":
            return self._fix_best_practices(issue, original)

        return None

    def _fix_security(self, issue: Issue, original: str) -> Optional[FixSuggestion]:
        """Generate security-related fixes."""
        if "SQL injection" in issue.message and "f-string" in issue.message:
            # Try to convert f-string to parameterized query
            fixed = self._convert_fstring_to_param(original)
            if fixed:
                return FixSuggestion(
                    issue=issue,
                    original_code=original,
                    suggested_fix=fixed,
                    confidence=0.8,
                    auto_applicable=False
                )

        elif "hardcoded" in issue.message.lower():
            # Suggest environment variable pattern
            var_match = re.search(r'(\w+)\s*=\s*["\']([^"\']+)["\']', original)
            if var_match:
                var_name, _ = var_match.groups()
                env_name = var_name.upper()
                fixed = f'{var_name} = os.environ.get("{env_name}")'
                return FixSuggestion(
                    issue=issue,
                    original_code=original,
                    suggested_fix=fixed,
                    confidence=0.7,
                    auto_applicable=False
                )

        elif "eval()" in issue.message:
            fixed = original.replace("eval(", "ast.literal_eval(")
            return FixSuggestion(
                issue=issue,
                original_code=original,
                suggested_fix=fixed,
                confidence=0.6,
                auto_applicable=False
            )

        elif "shell=True" in issue.message:
            fixed = original.replace("shell=True", "shell=False")
            return FixSuggestion(
                issue=issue,
                original_code=original,
                suggested_fix=fixed,
                confidence=0.8,
                auto_applicable=True
            )

        return None

    def _fix_hallucination(self, issue: Issue, original: str) -> Optional[FixSuggestion]:
        """Generate hallucination-related fixes."""
        if "Import" in issue.message and "does not exist" in issue.message:
            # Try to suggest alternatives
            import_match = re.search(r'import\s+(\w+)', original)
            if import_match:
                module = import_match.group(1)
                alternative = self._find_alternative_module(module)
                if alternative:
                    fixed = original.replace(module, alternative)
                    return FixSuggestion(
                        issue=issue,
                        original_code=original,
                        suggested_fix=fixed,
                        confidence=0.5,
                        auto_applicable=False
                    )

        return None

    def _fix_logic(self, issue: Issue, original: str, lines: List[str]) -> Optional[FixSuggestion]:
        """Generate logic-related fixes."""
        if "Unreachable" in issue.message:
            return FixSuggestion(
                issue=issue,
                original_code=original,
                suggested_fix=f"# DELETE: Unreachable code\n# {original}",
                confidence=0.9,
                auto_applicable=True
            )

        elif "infinite loop" in issue.message.lower():
            return FixSuggestion(
                issue=issue,
                original_code=original,
                suggested_fix="# WARNING: Add break condition or timeout\nwhile True:\n    # Add: if condition: break\n    pass",
                confidence=0.6,
                auto_applicable=False
            )

        elif "unused" in issue.message.lower():
            var_match = re.search(r'(\w+)\s*=', original)
            if var_match:
                var_name = var_match.group(1)
                fixed = f"_ = {var_name}  # Intentionally unused" if "=" in original else f"# REMOVE: {original}"
                return FixSuggestion(
                    issue=issue,
                    original_code=original,
                    suggested_fix=fixed,
                    confidence=0.7,
                    auto_applicable=True
                )

        return None

    def _fix_best_practices(self, issue: Issue, original: str) -> Optional[FixSuggestion]:
        """Generate best practice fixes."""
        if "Bare" in issue.message and "except" in original:
            fixed = original.replace("except:", "except Exception:")
            return FixSuggestion(
                issue=issue,
                original_code=original,
                suggested_fix=fixed,
                confidence=0.95,
                auto_applicable=True
            )

        elif "mutable default" in issue.message.lower():
            # Convert [] default to None
            fixed = re.sub(r'=\s*\[\]', '= None', original)
            if fixed != original:
                return FixSuggestion(
                    issue=issue,
                    original_code=original,
                    suggested_fix=f"{fixed}\n    # Add at start of function: items = items or []",
                    confidence=0.9,
                    auto_applicable=True
                )

        elif "missing docstring" in issue.message.lower():
            if "def " in original:
                func_match = re.search(r'def\s+(\w+)', original)
                if func_match:
                    func_name = func_match.group(1)
                    fixed = f'{original}\n    """TODO: Add description for {func_name}."""'
                    return FixSuggestion(
                        issue=issue,
                        original_code=original,
                        suggested_fix=fixed,
                        confidence=0.8,
                        auto_applicable=True
                    )

        return None

    def _convert_fstring_to_param(self, line: str) -> Optional[str]:
        """Convert SQL f-string to parameterized query."""
        # Simple pattern: f"SELECT ... {var}"
        match = re.search(r'f["\'](.+?)\{(\w+)\}(.+?)["\']', line)
        if match:
            prefix, var, suffix = match.groups()
            # Replace {var} with ?
            query = prefix + "?" + suffix
            # Use tuple for single param
            return line[:match.start()] + f'"{query}", ({var},)' + line[match.end():]
        return None

    def _find_alternative_module(self, hallucinated: str) -> Optional[str]:
        """Suggest real alternative for hallucinated module."""
        # Common hallucinations and their real alternatives
        alternatives = {
            "quick_sort": "sorted",
            "fast_hash": "hashlib",
            "smart_parser": "json",
            "easy_http": "requests",
            "ai_utils": "openai",
            "ml_helpers": "sklearn",
            "data_processor": "pandas",
            "text_analyzer": "nltk",
        }

        hall_lower = hallucinated.lower()
        for pattern, alt in alternatives.items():
            if pattern in hall_lower:
                return alt

        return None

    def apply_fix(self, code: str, suggestion: FixSuggestion) -> str:
        """Apply a fix suggestion to code."""
        lines = code.split("\n")
        if suggestion.issue.line and suggestion.issue.line <= len(lines):
            lines[suggestion.issue.line - 1] = suggestion.suggested_fix
        return "\n".join(lines)
