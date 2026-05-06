"""
Base language parser interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParseResult:
    """Result of parsing source code."""
    success: bool
    ast: Any
    code: str
    language: str
    lines: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    error: Optional[str] = None


class LanguageParser(ABC):
    """Base class for language-specific parsers."""

    language: str = "unknown"
    extensions: List[str] = []

    @abstractmethod
    def parse(self, code: str) -> ParseResult:
        pass

    @abstractmethod
    def get_line(self, node: Any) -> int:
        pass
