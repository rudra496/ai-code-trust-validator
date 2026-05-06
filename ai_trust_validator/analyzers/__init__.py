"""Base analyzer module."""

import ast
from abc import ABC, abstractmethod
from typing import List

from ai_trust_validator.config import Config
from ai_trust_validator.models import Issue


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""

    base_score: int = 100

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def analyze(self, tree: ast.AST, code: str) -> List[Issue]:
        """
        Analyze AST and code, returning list of issues found.

        Args:
            tree: Parsed AST of the code
            code: Original source code as string

        Returns:
            List of Issue objects found
        """
        pass

    def _get_line(self, node: ast.AST) -> int:
        """Get line number from AST node."""
        return getattr(node, "lineno", 0)
