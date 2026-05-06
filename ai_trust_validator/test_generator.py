"""
Test Generator - Generate pytest tests for AI-generated code.
"""

import ast
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GeneratedTest:
    """A generated test case."""
    function_name: str
    test_code: str
    test_type: str  # "basic", "edge_case", "error"


class TestGenerator:
    """Generate pytest tests for AI-generated functions."""

    def __init__(self):
        self.imports_added = set()

    def generate_tests(self, code: str, module_name: str = "module") -> str:
        """Generate pytest tests for all functions in code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return "# Cannot generate tests: code has syntax errors"

        tests = []
        imports = set()

        # Find all functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                func_tests = self._generate_function_tests(node, module_name)
                tests.extend(func_tests)

        if not tests:
            return "# No testable functions found"

        # Build test file
        test_lines = [
            '"""Auto-generated tests by AI Code Trust Validator."""',
            "",
            "import pytest",
            f"from {module_name} import *",
            "",
            "",
        ]

        for i, test in enumerate(tests):
            test_lines.append(test.test_code)
            if i < len(tests) - 1:
                test_lines.append("")
                test_lines.append("")

        return "\n".join(test_lines)

    def _generate_function_tests(self, node: ast.FunctionDef, module_name: str) -> List[GeneratedTest]:
        """Generate tests for a single function."""
        tests = []
        func_name = node.name

        # Analyze function signature
        params = self._get_parameters(node)
        return_type = self._get_return_type(node)

        # Basic test
        tests.append(self._create_basic_test(func_name, params, return_type))

        # Edge case tests
        if params:
            tests.extend(self._create_edge_case_tests(func_name, params))

        # Error tests
        tests.extend(self._create_error_tests(func_name, params))

        return tests

    def _get_parameters(self, node: ast.FunctionDef) -> List[str]:
        """Extract parameter names."""
        return [arg.arg for arg in node.args.args if arg.arg != "self"]

    def _get_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation if present."""
        if node.returns:
            return ast.unparse(node.returns) if hasattr(ast, 'unparse') else None
        return None

    def _create_basic_test(self, func_name: str, params: List[str], return_type: Optional[str]) -> GeneratedTest:
        """Create a basic functionality test."""
        # Generate sample inputs based on common patterns
        args = []
        for param in params:
            sample = self._guess_sample_input(param)
            args.append(sample)

        args_str = ", ".join(args) if args else ""

        if return_type:
            assertion = f"assert isinstance(result, {return_type})"
        else:
            assertion = "assert result is not None"

        test_code = f'''def test_{func_name}_basic():
    """Test basic functionality of {func_name}."""
    result = {func_name}({args_str})
    {assertion}'''

        return GeneratedTest(
            function_name=func_name,
            test_code=test_code,
            test_type="basic"
        )

    def _create_edge_case_tests(self, func_name: str, params: List[str]) -> List[GeneratedTest]:
        """Create edge case tests."""
        tests = []

        # Empty input test
        if params:
            empty_args = []
            for param in params:
                if self._is_string_param(param):
                    empty_args.append('""')
                elif self._is_list_param(param):
                    empty_args.append("[]")
                elif self._is_dict_param(param):
                    empty_args.append("{}")
                elif self._is_numeric_param(param):
                    empty_args.append("0")
                else:
                    empty_args.append("None")

            tests.append(GeneratedTest(
                function_name=func_name,
                test_code=f'''def test_{func_name}_empty_input():
    """Test {func_name} with empty input."""
    result = {func_name}({", ".join(empty_args)})
    # Should handle empty input gracefully
    assert result is not None or result == [] or result == {{}}''',
                test_type="edge_case"
            ))

            # None input test
            none_args = ["None"] * len(params)
            tests.append(GeneratedTest(
                function_name=func_name,
                test_code=f'''def test_{func_name}_none_input():
    """Test {func_name} with None input."""
    try:
        result = {func_name}({", ".join(none_args)})
    except (TypeError, ValueError, AttributeError):
        pass  # Expected for None input''',
                test_type="edge_case"
            ))

        return tests

    def _create_error_tests(self, func_name: str, params: List[str]) -> List[GeneratedTest]:
        """Create error handling tests."""
        tests = []

        if params:
            # Wrong type test
            tests.append(GeneratedTest(
                function_name=func_name,
                test_code=f'''def test_{func_name}_wrong_type():
    """Test {func_name} with wrong input types."""
    with pytest.raises((TypeError, ValueError, AttributeError)):
        {func_name}("wrong_type_input" * 100)''',
                test_type="error"
            ))

        return tests

    def _guess_sample_input(self, param_name: str) -> str:
        """Guess a sample input based on parameter name."""
        param_lower = param_name.lower()

        # String patterns
        if any(word in param_lower for word in ["name", "str", "text", "msg", "message"]):
            return '"test"'

        # Numeric patterns
        if any(word in param_lower for word in ["count", "num", "size", "length", "index"]):
            return "1"

        # Boolean patterns
        if any(word in param_lower for word in ["is_", "has_", "flag", "enable"]):
            return "True"

        # List patterns
        if any(word in param_lower for word in ["list", "items", "values", "data"]):
            return "[]"

        # Dict patterns
        if any(word in param_lower for word in ["dict", "config", "options", "kwargs"]):
            return "{}"

        # Default
        return "None"

    def _is_string_param(self, param: str) -> bool:
        return any(word in param.lower() for word in ["str", "text", "name", "msg"])

    def _is_list_param(self, param: str) -> bool:
        return any(word in param.lower() for word in ["list", "items", "array"])

    def _is_dict_param(self, param: str) -> bool:
        return any(word in param.lower() for word in ["dict", "config", "map"])

    def _is_numeric_param(self, param: str) -> bool:
        return any(word in param.lower() for word in ["num", "count", "size", "index", "int"])
