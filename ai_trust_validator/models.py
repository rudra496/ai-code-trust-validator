"""Data models for validation results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Issue:
    """Represents a single validation issue."""
    severity: str  # critical, high, medium, low, info
    category: str  # security, hallucination, logic, best_practices
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class CategoryScore:
    """Score breakdown for a single category."""
    score: int
    weight: float
    issues: List[Issue] = field(default_factory=list)

    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ValidationResult:
    """Complete validation result with scores and issues."""
    file_path: Optional[str]
    trust_score: int
    categories: Dict[str, CategoryScore]
    all_issues: List[Issue] = field(default_factory=list)

    @property
    def critical_issues(self) -> List[Issue]:
        return [i for i in self.all_issues if i.severity == "critical"]

    @property
    def high_issues(self) -> List[Issue]:
        return [i for i in self.all_issues if i.severity == "high"]

    @property
    def passed(self) -> bool:
        return self.trust_score >= 60 and len(self.critical_issues) == 0
