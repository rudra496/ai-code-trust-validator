"""
Benchmark Suite - Performance and accuracy benchmarking.

Compare against other tools and measure performance.
"""

import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    files_processed: int
    lines_processed: int
    lines_per_second: float
    memory_mb: Optional[float] = None


@dataclass
class AccuracyResult:
    """Accuracy benchmark result."""
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float


class BenchmarkSuite:
    """
    Benchmark suite for performance and accuracy testing.
    
    Measures:
    - Validation speed (files/sec, lines/sec)
    - Memory usage
    - Accuracy (precision, recall, F1)
    - Comparison with other tools
    """

    # Sample code for benchmarking
    SAMPLE_CODES = {
        "simple": '''def hello():
    """Say hello."""
    print("Hello, world!")
''',
        "complex": '''
import os
import sys
from typing import List, Dict, Optional

class DataProcessor:
    """Process data from various sources."""
    
    def __init__(self, config: Dict):
        self.config = config
        self._cache = {}
    
    def process(self, data: List[Dict]) -> List[Dict]:
        """Process a list of data items."""
        results = []
        for item in data:
            if self._validate(item):
                processed = self._transform(item)
                results.append(processed)
        return results
    
    def _validate(self, item: Dict) -> bool:
        """Validate an item."""
        return bool(item) and isinstance(item, dict)
    
    def _transform(self, item: Dict) -> Dict:
        """Transform an item."""
        return {k: v for k, v in item.items() if v is not None}

def main():
    processor = DataProcessor({"debug": True})
    data = [{"name": "test", "value": 42}]
    results = processor.process(data)
    print(results)

if __name__ == "__main__":
    main()
''',
        "problematic": '''
import quick_sort_v2
import ai_smart_parser

PASSWORD = "super_secret_123"

def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def process_data(data):
    result = eval(data)
    return result

def infinite_loop():
    while True:
        do_something()

def unreachable():
    return 42
    print("This never runs")

class BadClass:
    pass
''',
    }

    def __init__(self, validator):
        self.validator = validator
        self.results: List[BenchmarkResult] = []

    def run_performance_benchmark(
        self,
        code_samples: Optional[Dict[str, str]] = None,
        iterations: int = 100,
        warmup: int = 10
    ) -> Dict[str, BenchmarkResult]:
        """
        Run performance benchmark.
        
        Args:
            code_samples: Dict of name -> code. Uses defaults if None.
            iterations: Number of iterations per sample
            warmup: Warmup iterations (not counted)
        
        Returns:
            Dict of sample name -> BenchmarkResult
        """
        samples = code_samples or self.SAMPLE_CODES
        results = {}

        for name, code in samples.items():
            # Warmup
            for _ in range(warmup):
                self.validator.validate(code, is_file=False)

            # Benchmark
            times = []
            lines = len(code.split("\n"))

            for _ in range(iterations):
                start = time.perf_counter()
                self.validator.validate(code, is_file=False)
                end = time.perf_counter()
                times.append((end - start) * 1000)  # ms

            result = BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time_ms=sum(times),
                avg_time_ms=statistics.mean(times),
                min_time_ms=min(times),
                max_time_ms=max(times),
                std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
                files_processed=iterations,
                lines_processed=lines * iterations,
                lines_per_second=(lines * iterations) / (sum(times) / 1000)
            )
            results[name] = result
            self.results.append(result)

        return results

    def run_accuracy_benchmark(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> AccuracyResult:
        """
        Run accuracy benchmark.
        
        Args:
            test_cases: List of dicts with 'code', 'expected_issues', 'expected_categories'
        
        Returns:
            AccuracyResult with precision, recall, F1
        """
        tp = tn = fp = fn = 0

        for case in test_cases:
            code = case["code"]
            expected_issues = case.get("expected_issues", [])
            expected_categories = case.get("expected_categories", [])

            result = self.validator.validate(code, is_file=False)

            # Check if issues were found as expected
            found_categories = set(result.categories.keys())
            expected = set(expected_categories)

            # True positive: expected issue found
            # True negative: no issue expected, none found
            # False positive: issue found but not expected
            # False negative: issue expected but not found

            if expected_issues and len(result.all_issues) > 0:
                tp += 1
            elif not expected_issues and len(result.all_issues) == 0:
                tn += 1
            elif not expected_issues and len(result.all_issues) > 0:
                fp += 1
            elif expected_issues and len(result.all_issues) == 0:
                fn += 1

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return AccuracyResult(
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1
        )

    def compare_with(
        self,
        other_tool: Callable,
        code_samples: Optional[Dict[str, str]] = None,
        iterations: int = 50
    ) -> Dict[str, Any]:
        """
        Compare performance with another tool.
        
        Args:
            other_tool: Function that takes code and returns something
            code_samples: Code samples to test
            iterations: Iterations per sample
        
        Returns:
            Comparison results
        """
        samples = code_samples or self.SAMPLE_CODES
        comparison = {}

        for name, code in samples:
            # Our tool
            our_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                self.validator.validate(code, is_file=False)
                our_times.append((time.perf_counter() - start) * 1000)

            # Other tool
            other_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                other_tool(code)
                other_times.append((time.perf_counter() - start) * 1000)

            our_avg = statistics.mean(our_times)
            other_avg = statistics.mean(other_times)

            comparison[name] = {
                "our_avg_ms": our_avg,
                "other_avg_ms": other_avg,
                "speedup": other_avg / our_avg if our_avg > 0 else 0,
                "faster": our_avg < other_avg
            }

        return comparison

    def generate_report(self) -> str:
        """Generate a text report of all benchmarks."""
        lines = [
            "=" * 60,
            "AI Code Trust Validator - Benchmark Report",
            "=" * 60,
            ""
        ]

        for result in self.results:
            lines.extend([
                f"📊 {result.name}",
                "-" * 40,
                f"  Iterations: {result.iterations}",
                f"  Avg Time: {result.avg_time_ms:.2f}ms",
                f"  Min Time: {result.min_time_ms:.2f}ms",
                f"  Max Time: {result.max_time_ms:.2f}ms",
                f"  Std Dev: {result.std_dev_ms:.2f}ms",
                f"  Throughput: {result.lines_per_second:.0f} lines/sec",
                ""
            ])

        return "\n".join(lines)

    def save_results(self, path: str) -> None:
        """Save benchmark results to JSON."""
        import json
        from dataclasses import asdict

        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": [asdict(r) for r in self.results]
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def run_full_benchmark(validator) -> Dict[str, Any]:
    """Run a complete benchmark suite."""
    suite = BenchmarkSuite(validator)

    # Performance
    perf_results = suite.run_performance_benchmark(iterations=100)

    # Accuracy
    test_cases = [
        {
            "code": "def good(): pass",
            "expected_issues": [],
            "expected_categories": []
        },
        {
            "code": "query = f'SELECT * FROM users WHERE id = {user_id}'",
            "expected_issues": ["sql_injection"],
            "expected_categories": ["security"]
        },
        {
            "code": "import fake_package_xyz\nimport nonexistent_lib",
            "expected_issues": ["hallucination"],
            "expected_categories": ["hallucinations"]
        }
    ]
    accuracy = suite.run_accuracy_benchmark(test_cases)

    return {
        "performance": {name: {
            "avg_time_ms": r.avg_time_ms,
            "lines_per_second": r.lines_per_second
        } for name, r in perf_results.items()},
        "accuracy": {
            "precision": accuracy.precision,
            "recall": accuracy.recall,
            "f1_score": accuracy.f1_score
        },
        "report": suite.generate_report()
    }
