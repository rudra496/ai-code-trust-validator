"""
Logic Analyzer

Detects logic errors and code quality issues:
- Unreachable code
- Infinite loops
- Type mismatches
- Unused variables
- Dead code paths
"""

import ast
from typing import List, Set, Dict

from ai_trust_validator.analyzers import BaseAnalyzer
from ai_trust_validator.models import Issue


class LogicAnalyzer(BaseAnalyzer):
    """Analyzes code for logic errors."""

    base_score = 100

    def analyze(self, tree: ast.AST, code: str) -> List[Issue]:
        """Analyze code for logic issues."""
        issues: List[Issue] = []

        # Check for unreachable code
        issues.extend(self._check_unreachable_code(tree))

        # Check for infinite loops
        issues.extend(self._check_infinite_loops(tree))

        # Check for unused variables
        issues.extend(self._check_unused_variables(tree))

        # Check for always-true/false conditions
        issues.extend(self._check_constant_conditions(tree))

        # Check for empty blocks
        issues.extend(self._check_empty_blocks(tree, code))

        # Check for redundant comparisons
        issues.extend(self._check_redundant_comparisons(tree))

        return issues

    def _check_unreachable_code(self, tree: ast.AST) -> List[Issue]:
        """Check for unreachable code after return/raise/break/continue."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues.extend(self._check_unreachable_in_block(node.body))

            elif isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                issues.extend(self._check_unreachable_in_block(node.body))

            elif isinstance(node, ast.If):
                issues.extend(self._check_unreachable_in_block(node.body))
                issues.extend(self._check_unreachable_in_block(node.orelse))

            elif isinstance(node, (ast.With, ast.AsyncWith)):
                issues.extend(self._check_unreachable_in_block(node.body))

            elif isinstance(node, ast.Try):
                issues.extend(self._check_unreachable_in_block(node.body))
                for handler in node.handlers:
                    issues.extend(self._check_unreachable_in_block(handler.body))

        return issues

    def _check_unreachable_in_block(self, body: List[ast.stmt]) -> List[Issue]:
        """Check for unreachable statements in a block."""
        issues: List[Issue] = []

        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                # Check if there are statements after this
                if i < len(body) - 1:
                    for unreachable in body[i + 1:]:
                        issues.append(Issue(
                            severity="medium",
                            category="logic",
                            message=f"Unreachable code after {type(stmt).__name__.lower()}",
                            line=self._get_line(unreachable),
                            suggestion=f"Remove code after {type(stmt).__name__.lower()} statement"
                        ))
                break

        return issues

    def _check_infinite_loops(self, tree: ast.AST) -> List[Issue]:
        """Check for potential infinite loops."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                # Check if condition is always True with no break
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    # Check for break statement
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
                    has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(node))

                    if not (has_break or has_return or has_raise):
                        issues.append(Issue(
                            severity="high",
                            category="logic",
                            message="Potential infinite loop (while True with no exit)",
                            line=self._get_line(node),
                            suggestion="Add break condition or ensure loop can exit"
                        ))

        return issues

    def _check_unused_variables(self, tree: ast.AST) -> List[Issue]:
        """Check for unused variables."""
        issues: List[Issue] = []

        # Collect all assignments
        assigned: Dict[str, ast.AST] = {}
        used: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Skip common unused variable patterns
                        if not target.id.startswith("_"):
                            assigned[target.id] = node

            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)

        # Find unused
        for name, node in assigned.items():
            if name not in used:
                issues.append(Issue(
                    severity="low",
                    category="logic",
                    message=f"Variable '{name}' is assigned but never used",
                    line=self._get_line(node),
                    suggestion=f"Remove unused variable or prefix with _ if intentional"
                ))

        return issues

    def _check_constant_conditions(self, tree: ast.AST) -> List[Issue]:
        """Check for always-true or always-false conditions."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Constant):
                    if node.test.value:
                        issues.append(Issue(
                            severity="low",
                            category="logic",
                            message="If condition is always True",
                            line=self._get_line(node),
                            suggestion="Remove the condition or fix the logic"
                        ))
                    else:
                        issues.append(Issue(
                            severity="low",
                            category="logic",
                            message="If condition is always False (body never executes)",
                            line=self._get_line(node),
                            suggestion="Remove the condition or fix the logic"
                        ))

            elif isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant):
                    if not node.test.value:
                        issues.append(Issue(
                            severity="medium",
                            category="logic",
                            message="While condition is always False (loop never executes)",
                            line=self._get_line(node),
                            suggestion="Remove the loop or fix the condition"
                        ))

        return issues

    def _check_empty_blocks(self, tree: ast.AST, code: str) -> List[Issue]:
        """Check for empty code blocks."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    issues.append(Issue(
                        severity="info",
                        category="logic",
                        message=f"Empty {type(node).__name__} block",
                        line=self._get_line(node),
                        suggestion="Implement the block or remove it"
                    ))

            elif isinstance(node, ast.FunctionDef):
                body = node.body
                if len(body) == 1:
                    if isinstance(body[0], ast.Pass):
                        issues.append(Issue(
                            severity="medium",
                            category="logic",
                            message=f"Function '{node.name}' is empty",
                            line=self._get_line(node),
                            suggestion="Implement the function or mark as abstract"
                        ))
                    elif isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                        if str(body[0].value.value) == "...":
                            issues.append(Issue(
                                severity="medium",
                                category="logic",
                                message=f"Function '{node.name}' has ellipsis body",
                                line=self._get_line(node),
                                suggestion="Implement the function or mark as abstract"
                            ))

        return issues

    def _check_redundant_comparisons(self, tree: ast.AST) -> List[Issue]:
        """Check for redundant comparisons."""
        issues: List[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check for x == x or x != x
                if len(node.ops) == 1:
                    if isinstance(node.left, ast.Name):
                        left_name = node.left.id
                        if isinstance(node.comparators[0], ast.Name):
                            right_name = node.comparators[0].id
                            if left_name == right_name:
                                if isinstance(node.ops[0], ast.Eq):
                                    issues.append(Issue(
                                        severity="low",
                                        category="logic",
                                        message=f"Redundant comparison: {left_name} == {right_name}",
                                        line=self._get_line(node),
                                        suggestion="This is always True, check if this is intentional"
                                    ))
                                elif isinstance(node.ops[0], ast.NotEq):
                                    issues.append(Issue(
                                        severity="low",
                                        category="logic",
                                        message=f"Redundant comparison: {left_name} != {right_name}",
                                        line=self._get_line(node),
                                        suggestion="This is always False, check if this is intentional"
                                    ))

        return issues
