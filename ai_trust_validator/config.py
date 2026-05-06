"""
Configuration module for AI Trust Validator.

Supports loading from .aitrust.yaml files with sensible defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class CheckConfig:
    """Configuration for a single check type."""
    enabled: bool = True
    weight: float = 1.0


@dataclass
class ChecksConfig:
    """Configuration for all check types."""
    security: CheckConfig = field(default_factory=lambda: CheckConfig(weight=2.0))
    hallucinations: CheckConfig = field(default_factory=lambda: CheckConfig(weight=2.5))
    logic: CheckConfig = field(default_factory=lambda: CheckConfig(weight=1.0))
    best_practices: CheckConfig = field(default_factory=lambda: CheckConfig(weight=0.5))


@dataclass
class Config:
    """
    Main configuration class.
    
    Loads from .aitrust.yaml if present, otherwise uses defaults.
    """
    min_score: int = 70
    strict_mode: bool = False
    checks: ChecksConfig = field(default_factory=ChecksConfig)
    ignore: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def find_and_load(cls, start_dir: Optional[str | Path] = None) -> "Config":
        """
        Find .aitrust.yaml starting from start_dir and walking up.
        
        Args:
            start_dir: Directory to start searching from (default: cwd)
            
        Returns:
            Config loaded from found file, or default config
        """
        current = Path(start_dir or Path.cwd()).resolve()

        while True:
            config_path = current / ".aitrust.yaml"
            if config_path.exists():
                return cls.from_file(config_path)

            parent = current.parent
            if parent == current:
                break
            current = parent

        return cls()

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        checks_data = data.get("checks", {})
        checks = ChecksConfig()

        for name in ["security", "hallucinations", "logic", "best_practices"]:
            if name in checks_data:
                check_data = checks_data[name]
                setattr(
                    checks,
                    name,
                    CheckConfig(
                        enabled=check_data.get("enabled", True),
                        weight=check_data.get("weight", 1.0)
                    )
                )

        return cls(
            min_score=data.get("min_score", 70),
            strict_mode=data.get("strict_mode", False),
            checks=checks,
            ignore=data.get("ignore", [])
        )
