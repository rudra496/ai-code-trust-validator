"""Python language parser using native AST."""
import ast
from typing import Any

from ai_trust_validator.languages.base import LanguageParser, ParseResult


class PythonParser(LanguageParser):
    language = "python"
    extensions = [".py", ".pyw", ".pyi"]

    def parse(self, code: str) -> ParseResult:
        lines = code.split('\n')
        try:
            tree = ast.parse(code)
            return ParseResult(success=True, ast=tree, code=code, language="python", lines=lines)
        except SyntaxError as e:
            return ParseResult(success=False, ast=None, code=code, language="python", lines=lines, error=f"Syntax error at line {e.lineno}: {e.msg}")

    def get_line(self, node: Any) -> int:
        return getattr(node, "lineno", 0)
