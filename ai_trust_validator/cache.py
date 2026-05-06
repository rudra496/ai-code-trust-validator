"""
Intelligent Caching System - Speed up repeated validations.

Uses content hashing to cache results and skip re-analysis.
"""

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """A cached validation result."""
    file_hash: str
    trust_score: int
    issues_count: int
    critical_count: int
    timestamp: str
    config_hash: str
    result_data: Dict[str, Any]
    file_path: Optional[str] = None
    analysis_duration_ms: Optional[float] = None


class CacheManager:
    """
    Intelligent cache for validation results.
    
    Uses content hashing to detect changes and skip re-analysis.
    Thread-safe with automatic cleanup of old entries.
    """

    DEFAULT_CACHE_DIR = ".aitrust_cache"
    DEFAULT_TTL_DAYS = 7
    MAX_CACHE_SIZE_MB = 100

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
        enabled: bool = True
    ):
        self.enabled = enabled
        self.cache_dir = Path(cache_dir or self.DEFAULT_CACHE_DIR)
        self.ttl_days = ttl_days
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, CacheEntry] = {}

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def compute_hash(self, content: str, config_hash: str = "") -> str:
        """Compute content hash for cache key."""
        combined = f"{content}:{config_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def compute_config_hash(self, config: Any) -> str:
        """Compute hash from config settings."""
        config_str = json.dumps({
            "min_score": getattr(config, "min_score", 70),
            "strict_mode": getattr(config, "strict_mode", False),
            "checks": str(getattr(config, "checks", {})),
        }, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    def get(self, content: str, config: Any) -> Optional[CacheEntry]:
        """Get cached result if available and not expired."""
        if not self.enabled:
            return None

        config_hash = self.compute_config_hash(config)
        content_hash = self.compute_hash(content, config_hash)

        with self._lock:
            # Check memory cache first
            if content_hash in self._memory_cache:
                entry = self._memory_cache[content_hash]
                if not self._is_expired(entry):
                    return entry

            # Check disk cache
            cache_file = self.cache_dir / f"{content_hash}.json"
            if cache_file.exists():
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                    entry = CacheEntry(**data)
                    if not self._is_expired(entry):
                        self._memory_cache[content_hash] = entry
                        return entry
                except (json.JSONDecodeError, KeyError):
                    pass

        return None

    def set(
        self,
        content: str,
        result: Any,
        config: Any,
        file_path: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """Cache a validation result."""
        if not self.enabled:
            return

        config_hash = self.compute_config_hash(config)
        content_hash = self.compute_hash(content, config_hash)

        entry = CacheEntry(
            file_hash=content_hash,
            trust_score=result.trust_score,
            issues_count=len(result.all_issues),
            critical_count=len(result.critical_issues),
            timestamp=datetime.utcnow().isoformat(),
            config_hash=config_hash,
            result_data=self._serialize_result(result),
            file_path=file_path,
            analysis_duration_ms=duration_ms
        )

        with self._lock:
            self._memory_cache[content_hash] = entry

            cache_file = self.cache_dir / f"{content_hash}.json"
            with open(cache_file, "w") as f:
                json.dump(asdict(entry), f, indent=2)

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        try:
            timestamp = datetime.fromisoformat(entry.timestamp)
            return datetime.utcnow() - timestamp > timedelta(days=self.ttl_days)
        except (ValueError, TypeError):
            return True

    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        """Serialize validation result for caching."""
        return {
            "trust_score": result.trust_score,
            "passed": result.passed,
            "categories": {
                name: {
                    "score": cat.score,
                    "weight": cat.weight,
                }
                for name, cat in result.categories.items()
            },
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "line": i.line,
                    "suggestion": i.suggestion,
                }
                for i in result.all_issues
            ]
        }

    def clear(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._memory_cache.clear()
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()

    def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count of removed entries."""
        removed = 0
        with self._lock:
            # Memory cache
            expired_keys = [
                k for k, v in self._memory_cache.items()
                if self._is_expired(v)
            ]
            for key in expired_keys:
                del self._memory_cache[key]
                removed += 1

            # Disk cache
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                    entry = CacheEntry(**data)
                    if self._is_expired(entry):
                        cache_file.unlink()
                        removed += 1
                except (json.JSONDecodeError, KeyError):
                    cache_file.unlink()
                    removed += 1

        return removed

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            disk_entries = len(list(self.cache_dir.glob("*.json")))
            total_size = sum(
                f.stat().st_size
                for f in self.cache_dir.glob("*.json")
            ) if disk_entries > 0 else 0

            return {
                "memory_entries": len(self._memory_cache),
                "disk_entries": disk_entries,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": str(self.cache_dir),
                "enabled": self.enabled,
                "ttl_days": self.ttl_days,
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from cached results."""
        metrics = {
            "total_validations": 0,
            "avg_trust_score": 0,
            "avg_analysis_time_ms": 0,
            "files_analyzed": set(),
            "total_issues_found": 0,
            "score_distribution": {"excellent": 0, "good": 0, "fair": 0, "poor": 0},
        }

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                entry = CacheEntry(**data)

                metrics["total_validations"] += 1
                metrics["total_issues_found"] += entry.issues_count

                if entry.file_path:
                    metrics["files_analyzed"].add(entry.file_path)

                if entry.trust_score >= 80:
                    metrics["score_distribution"]["excellent"] += 1
                elif entry.trust_score >= 60:
                    metrics["score_distribution"]["good"] += 1
                elif entry.trust_score >= 40:
                    metrics["score_distribution"]["fair"] += 1
                else:
                    metrics["score_distribution"]["poor"] += 1

                if entry.analysis_duration_ms:
                    metrics["avg_analysis_time_ms"] += entry.analysis_duration_ms

            except (json.JSONDecodeError, KeyError):
                continue

        if metrics["total_validations"] > 0:
            metrics["avg_trust_score"] = sum(
                self._memory_cache.get(h, CacheEntry(file_hash="", trust_score=0, issues_count=0, critical_count=0, timestamp="", config_hash="", result_data={})).trust_score
                for h in self._memory_cache
            ) / max(len(self._memory_cache), 1)
            metrics["files_analyzed"] = len(metrics["files_analyzed"])

        return metrics
