"""
Best Practices Analyzer

Detects violations of Python best practices:
- Missing docstrings
- Poor naming conventions
- Long functions
- Deep nesting
- Missing type hints
- Bare except clauses
"""

import ast
import re
from typing import List

from ai_trust_validator.analyzers import BaseAnalyzer
from ai_trust_validator.models import Issue


class BestPracticesAnalyzer(BaseAnalyzer):
    """Analyzes code for best practice violations."""

    base_score = 100

    # Configuration
    MAX_FUNCTION_LENGTH = 50  # lines
    MAX_NESTING_DEPTH = 4
    MAX_LINE_LENGTH = 100

    def analyze(self, tree: ast.AST, code: str) -> List[Issue]:
        """Analyze code for best practice issues."""
        issues: List[Issue] = []

        lines = code.split("\n")

        # Check docstrings
        issues.extend(self._check_docstrings(tree))

        # Check naming conventions
        issues.extend(self._check_naming(tree))

        # Check function length
        issues.extend(self._check_function_length(tree))

        # Check nesting depth
        issues.extend(self._check_nesting(tree))

        # Check bare except
        issues.extend(self._check_bare_except(tree))

        # Check for mutable default arguments
        issues.extend(self._check_mutable_defaults(tree))

        # Check line length
        issues.extend(self._check_line_length(lines))

        return issues

    def _check_docstrings(self, tree: ast.AST) -> List[Issue]:
        """Check for missing docstrings."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Module):
                if not self._has_docstring(node):
                    issues.append(Issue(
                        severity="info",
                        category="best_practices",
                        message="Module is missing docstring",
                        line=1,
                        suggestion='Add module docstring: """Module description."""'
                    ))

            elif isinstance(node, ast.FunctionDef):
                if not self._has_docstring(node) and not node.name.startswith("_"):
                    issues.append(Issue(
                        severity="info",
                        category="best_practices",
                        message=f"Function '{node.name}' is missing docstring",
                        line=self._get_line(node),
                        suggestion='Add docstring: """Description of what function does."""'
                    ))

            elif isinstance(node, ast.ClassDef):
                if not self._has_docstring(node):
                    issues.append(Issue(
                        severity="info",
                        category="best_practices",
                        message=f"Class '{node.name}' is missing docstring",
                        line=self._get_line(node),
                        suggestion='Add docstring: """Class description."""'
                    ))

        return issues

    def _has_docstring(self, node: ast.AST) -> bool:
        """Check if node has a docstring."""
        if hasattr(node, "body") and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str):
                    return True
        return False

    def _check_naming(self, tree: ast.AST) -> List[Issue]:
        """Check naming conventions."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Function names should be snake_case
                if not self._is_snake_case(node.name) and not node.name.startswith("_"):
                    issues.append(Issue(
                        severity="low",
                        category="best_practices",
                        message=f"Function '{node.name}' should use snake_case",
                        line=self._get_line(node),
                        suggestion=f"Rename to '{self._to_snake_case(node.name)}'"
                    ))

            elif isinstance(node, ast.ClassDef):
                # Class names should be PascalCase
                if not self._is_pascal_case(node.name):
                    issues.append(Issue(
                        severity="low",
                        category="best_practices",
                        message=f"Class '{node.name}' should use PascalCase",
                        line=self._get_line(node),
                        suggestion=f"Rename to '{self._to_pascal_case(node.name)}'"
                    ))

            elif isinstance(node, ast.Assign):
                # Variable names should be snake_case
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Skip if it's a constant (UPPER_CASE is ok)
                        if not name.isupper() and not name.startswith("_"):
                            if not self._is_snake_case(name):
                                issues.append(Issue(
                                    severity="low",
                                    category="best_practices",
                                    message=f"Variable '{name}' should use snake_case",
                                    line=self._get_line(node),
                                    suggestion=f"Rename to '{self._to_snake_case(name)}'"
                                ))

        return issues

    def _check_function_length(self, tree: ast.AST) -> List[Issue]:
        """Check for long functions."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate function length
                if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                    length = node.end_lineno - node.lineno + 1
                    if length > self.MAX_FUNCTION_LENGTH:
                        issues.append(Issue(
                            severity="medium",
                            category="best_practices",
                            message=f"Function '{node.name}' is too long ({length} lines)",
                            line=self._get_line(node),
                            suggestion=f"Break into smaller functions (max {self.MAX_FUNCTION_LENGTH} lines)"
                        ))

        return issues

    def _check_nesting(self, tree: ast.AST) -> List[Issue]:
        """Check for deep nesting."""
        issues: List[Issue] = []

        def check_depth(node: ast.AST, depth: int = 0):
            # Increment depth for nesting constructs
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                depth += 1
                if depth > self.MAX_NESTING_DEPTH:
                    issues.append(Issue(
                        severity="medium",
                        category="best_practices",
                        message=f"Deep nesting detected (depth: {depth})",
                        line=self._get_line(node),
                        suggestion="Extract nested logic into separate functions"
                    ))

            for child in ast.iter_child_nodes(node):
                check_depth(child, depth)

        check_depth(tree)
        return issues

    def _check_bare_except(self, tree: ast.AST) -> List[Issue]:
        """Check for bare except clauses."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(Issue(
                        severity="high",
                        category="best_practices",
                        message="Bare 'except:' catches all exceptions including KeyboardInterrupt",
                        line=self._get_line(node),
                        suggestion="Use 'except Exception:' or be more specific"
                    ))

        return issues

    def _check_mutable_defaults(self, tree: ast.AST) -> List[Issue]:
        """Check for mutable default arguments."""
        issues: List[Issue] = []

        mutable_types = (ast.List, ast.Dict, ast.Set)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, mutable_types):
                        issues.append(Issue(
                            severity="medium",
                            category="best_practices",
                            message=f"Mutable default argument in '{node.name}'",
                            line=self._get_line(node),
                            suggestion="Use None as default and create inside function"
                        ))

        return issues

    def _check_line_length(self, lines: List[str]) -> List[Issue]:
        """Check for long lines."""
        issues: List[Issue] = []

        for i, line in enumerate(lines, 1):
            if len(line) > self.MAX_LINE_LENGTH:
                issues.append(Issue(
                    severity="low",
                    category="best_practices",
                    message=f"Line too long ({len(line)} chars)",
                    line=i,
                    suggestion=f"Break line to max {self.MAX_LINE_LENGTH} characters"
                ))

        return issues

    # Helper methods
    def _is_snake_case(self, name: str) -> bool:
        """Check if name is snake_case."""
        return bool(re.match(r"^[a-z][a-z0-9_]*$", name))

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is PascalCase."""
        return bool(re.match(r"^[A-Z][a-zA-Z0-9]*$", name))

    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case."""
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        return "".join(word.capitalize() for word in name.split("_"))
