"""
CLI interface for AI Code Trust Validator.

Commands:
    aitrust validate <path>     - Validate code and show trust score
    aitrust report <path>       - Generate detailed report
    aitrust suggest-fixes <path>- Show fix suggestions
    aitrust generate-tests <path>- Generate pytest tests
    aitrust serve               - Start REST API server
    aitrust watch <path>        - Watch files for changes
    aitrust benchmark           - Run performance benchmarks
    aitrust analyze-deps <path> - Multi-file dependency analysis
    aitrust cache               - Manage cache
"""

import sys
from pathlib import Path
from typing import Optional
import time

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from ai_trust_validator import (
    Validator, Config, ValidationResult, Issue,
    FixSuggester, TestGenerator, CacheManager,
    PluginManager, Watcher, watch_with_dashboard,
    BenchmarkSuite, run_full_benchmark,
    MultiFileAnalyzer, MultiFileResult,
    JSONReporter, HTMLReporter, SARIFReporter
)
from ai_trust_validator.api_server import run_server


console = Console()


@click.group()
@click.version_option(version="0.4.0", prog_name="ai-trust-validator")
def main():
    """
    🛡️ AI Code Trust Validator - Trust your AI-generated code.
    
    Validate AI-generated code for security, hallucinations, and logic errors.
    
    Examples:
        aitrust validate src/ --min-score 75
        aitrust report src/ --format html --output report.html
        aitrust serve --port 8080
        aitrust watch src/
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=False), required=False)
@click.option("--stdin", is_flag=True, help="Read code from stdin")
@click.option("--min-score", default=70, help="Minimum trust score to pass")
@click.option("--strict", is_flag=True, help="Fail on any critical issues")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--cache/--no-cache", default=True, help="Use caching")
@click.option("--git-diff", type=click.Choice(["staged", "working", "committed"]), help="Only validate changed files in git diff")
def validate(
    path: Optional[str],
    stdin: bool,
    min_score: int,
    strict: bool,
    json_output: bool,
    config: Optional[str],
    cache: bool,
    git_diff: Optional[str]
):
    """
    Validate AI-generated code and produce a trust score.
    
    PATH can be a file or directory. Use --stdin to read from stdin.
    """
    # Load config
    if config:
        cfg = Config.from_file(config)
    else:
        cfg = Config.find_and_load()

    cfg.min_score = min_score
    cfg.strict_mode = strict or cfg.strict_mode

    if git_diff and not path:
        path = "."

    # Initialize cache
    cache_mgr = CacheManager(enabled=cache)
    validator = Validator(cfg)

    # Get source
    if stdin:
        code = sys.stdin.read()
        result = validator.validate(code, is_file=False)
        results = [result]
    elif path:
        path_obj = Path(path)
        if path_obj.is_file():
            result = validator.validate(path_obj)
            results = [result]
        elif path_obj.is_dir():
            results = validator.validate_directory(path_obj)
        else:
            console.print(f"[red]Error: {path} does not exist[/red]")
            sys.exit(1)
    else:
        console.print("[red]Error: Provide a PATH or use --stdin[/red]")
        sys.exit(1)

    # Output results
    if json_output:
        _output_json(results)
    else:
        _output_rich(results, cfg)

    # Exit code
    all_passed = all(
        r.trust_score >= cfg.min_score and len(r.critical_issues) == 0
        for r in results
    )
    if not all_passed:
        sys.exit(1)


@main.command("report")
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "report_format", type=click.Choice(["json", "html", "sarif"]), default="html", help="Report format")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--min-score", default=70, help="Minimum trust score to pass")
def report(path: str, report_format: str, output: Optional[str], min_score: int):
    """Generate a detailed report in JSON, HTML, or SARIF format."""
    path_obj = Path(path)
    cfg = Config.find_and_load()
    cfg.min_score = min_score
    validator = Validator(cfg)

    if path_obj.is_file():
        results = [validator.validate(path_obj)]
    else:
        results = validator.validate_directory(path_obj)

    # Generate report
    if report_format == "json":
        reporter = JSONReporter()
        content = reporter.generate(results)
        default_output = "trust-report.json"
    elif report_format == "html":
        reporter = HTMLReporter()
        content = reporter.generate(results)
        default_output = "trust-report.html"
    elif report_format == "sarif":
        reporter = SARIFReporter()
        content = reporter.generate(results)
        default_output = "trust-report.sarif.json"

    # Write output
    output_path = output or default_output
    Path(output_path).write_text(content, encoding="utf-8")
    console.print(f"[green]✓ Report saved to {output_path}[/green]")


@main.command("suggest-fixes")
@click.argument("path", type=click.Path(exists=True))
@click.option("--apply", is_flag=True, help="Show diff of suggested fixes")
def suggest_fixes(path: str, apply: bool):
    """Generate fix suggestions for detected issues."""
    path_obj = Path(path)
    code = path_obj.read_text(encoding="utf-8")
    
    cfg = Config.find_and_load()
    validator = Validator(cfg)
    result = validator.validate(path_obj)

    if not result.all_issues:
        console.print("[green]✓ No issues found - nothing to fix![/green]")
        return

    suggester = FixSuggester()
    fixes = suggester.suggest_fixes(result, code)

    if not fixes:
        console.print("[yellow]No automatic fixes available for the detected issues.[/yellow]")
        return

    console.print(f"\n💡 [bold]Fix Suggestions for {path}[/bold]\n")

    for fix in fixes:
        severity = fix.issue.severity.upper()
        color = _severity_color(fix.issue.severity)
        
        console.print(f"[{color}]{severity}[/{color}] {fix.issue.message}")
        if fix.issue.line:
            console.print(f"  [dim]Line {fix.issue.line}[/dim]")
        
        console.print(f"\n  [dim]Original:[/dim]")
        console.print(f"  {fix.original_code}")
        
        console.print(f"\n  [green]Suggested:[/green]")
        for line in fix.suggested_fix.split("\n"):
            console.print(f"  {line}")
        
        console.print(f"\n  [dim]Confidence: {fix.confidence:.0%} | Auto-applicable: {'Yes' if fix.auto_applicable else 'No'}[/dim]")
        console.print()


@main.command("generate-tests")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--module", "-m", default="module", help="Module name for imports")
def generate_tests(path: str, output: Optional[str], module: str):
    """Generate pytest tests for a Python file."""
    path_obj = Path(path)
    code = path_obj.read_text(encoding="utf-8")

    generator = TestGenerator()
    test_code = generator.generate_tests(code, module)

    if output:
        output_path = Path(output)
        output_path.write_text(test_code, encoding="utf-8")
        console.print(f"[green]✓ Tests saved to {output_path}[/green]")
    else:
        console.print(test_code)


@main.command("serve")
@click.option("--port", "-p", default=8080, help="Server port")
@click.option("--host", "-h", default="0.0.0.0", help="Server host")
def serve(port: int, host: str):
    """Start the REST API server."""
    run_server(port=port, host=host)


@main.command("watch")
@click.argument("path", type=click.Path(exists=True))
@click.option("--refresh", "-r", default=2.0, help="Refresh rate in seconds")
@click.option("--dashboard", is_flag=True, help="Show live dashboard")
def watch(path: str, refresh: float, dashboard: bool):
    """Watch files for changes and re-validate."""
    validator = Validator()
    
    if dashboard:
        watch_with_dashboard(path, validator, refresh_rate=refresh)
    else:
        watcher = Watcher(validator)
        
        def on_change(result, file_path):
            score = result.trust_score
            icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            console.print(f"{icon} {file_path}: Score {score}/100")
            if result.critical_issues:
                for issue in result.critical_issues[:3]:
                    console.print(f"   [red]• {issue.message}[/red]")
        
        watcher.watch(path, on_change=on_change)


@main.command("benchmark")
@click.option("--iterations", "-i", default=100, help="Number of iterations")
@click.option("--output", "-o", type=click.Path(), help="Output file for results")
def benchmark(iterations: int, output: Optional[str]):
    """Run performance benchmarks."""
    from ai_trust_validator import Validator
    
    console.print("[bold]🏃 Running benchmarks...[/bold]\n")
    
    validator = Validator()
    suite = BenchmarkSuite(validator)
    
    # Run performance benchmark
    results = suite.run_performance_benchmark(iterations=iterations)
    
    # Display results
    table = Table(title="📊 Benchmark Results")
    table.add_column("Sample", style="cyan")
    table.add_column("Avg (ms)", justify="right")
    table.add_column("Min (ms)", justify="right")
    table.add_column("Max (ms)", justify="right")
    table.add_column("Lines/sec", justify="right")
    
    for name, result in results.items():
        table.add_row(
            name,
            f"{result.avg_time_ms:.2f}",
            f"{result.min_time_ms:.2f}",
            f"{result.max_time_ms:.2f}",
            f"{result.lines_per_second:.0f}"
        )
    
    console.print(table)
    
    # Save if requested
    if output:
        suite.save_results(output)
        console.print(f"\n[green]✓ Results saved to {output}[/green]")


@main.command("analyze-deps")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file for report")
def analyze_deps(path: str, output: Optional[str]):
    """Analyze multi-file dependencies."""
    from ai_trust_validator import MultiFileAnalyzer, Validator
    
    console.print(f"[bold]🔍 Analyzing dependencies in {path}...[/bold]\n")
    
    analyzer = MultiFileAnalyzer(validator=Validator())
    result = analyzer.analyze_directory(path)
    
    # Summary
    console.print(Panel(
        f"Modules: {len(result.modules)} | "
        f"Overall Score: {result.overall_score}/100",
        title="📊 Summary"
    ))
    
    # Circular dependencies
    if result.circular_dependencies:
        console.print("\n[red]⚠️ Circular Dependencies:[/red]")
        for a, b in result.circular_dependencies:
            console.print(f"  • {a} ↔ {b}")
    else:
        console.print("\n[green]✓ No circular dependencies[/green]")
    
    # Unused modules
    if result.unused_modules:
        console.print(f"\n[yellow]📦 Unused Modules ({len(result.unused_modules)}):[/yellow]")
        for m in result.unused_modules[:10]:
            console.print(f"  • {m}")
    
    # Import issues
    if result.import_issues:
        console.print(f"\n[yellow]⚠️ Import Issues ({len(result.import_issues)}):[/yellow]")
        for issue in result.import_issues[:5]:
            console.print(f"  • {issue['message']}")
    
    # Generate report
    if output:
        report = analyzer.generate_dependency_report()
        Path(output).write_text(report, encoding="utf-8")
        console.print(f"\n[green]✓ Report saved to {output}[/green]")


@main.command("cache")
@click.argument("action", type=click.Choice(["stats", "clear", "cleanup"]))
def cache(action: str):
    """Manage the validation cache."""
    cache_mgr = CacheManager()
    
    if action == "stats":
        stats = cache_mgr.stats()
        console.print("[bold]📦 Cache Statistics[/bold]\n")
        console.print(f"Memory entries: {stats['memory_entries']}")
        console.print(f"Disk entries: {stats['disk_entries']}")
        console.print(f"Total size: {stats['total_size_mb']} MB")
        console.print(f"Cache dir: {stats['cache_dir']}")
    
    elif action == "clear":
        cache_mgr.clear()
        console.print("[green]✓ Cache cleared[/green]")
    
    elif action == "cleanup":
        removed = cache_mgr.cleanup_expired()
        console.print(f"[green]✓ Removed {removed} expired entries[/green]")


def _output_rich(results: list[ValidationResult], cfg: Config):
    """Pretty print results using Rich."""
    for result in results:
        # Header
        if result.file_path:
            console.print(f"\n🔍 Analyzing: {result.file_path}")
        console.print("━" * 60)

        # Trust score with color
        score = result.trust_score
        if score >= 80:
            score_color = "green"
            score_icon = "✅"
        elif score >= 60:
            score_color = "yellow"
            score_icon = "⚠️"
        else:
            score_color = "red"
            score_icon = "❌"

        console.print(f"\n📊 TRUST SCORE: [{score_color}]{score}/100[/{score_color}] {score_icon}\n")

        # Category table
        if result.categories:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Category", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Issues", justify="left")

            for name, cat in result.categories.items():
                issue_count = len(cat.issues)
                critical = len([i for i in cat.issues if i.severity == "critical"])
                issue_str = f"{issue_count} issues"
                if critical > 0:
                    issue_str += f" ({critical} critical)"

                table.add_row(
                    name.replace("_", " ").title(),
                    str(cat.score),
                    issue_str
                )

            console.print(table)
            console.print()

        # Critical issues
        if result.critical_issues or result.high_issues:
            console.print("🚨 Critical Issues:\n")
            for issue in result.critical_issues[:5] + result.high_issues[:5]:
                line_info = f"Line {issue.line}: " if issue.line else ""
                console.print(f"  [{_severity_color(issue.severity)}]{issue.severity.upper()}[/{_severity_color(issue.severity)}] {line_info}{issue.message}")
                if issue.suggestion:
                    console.print(f"    💡 {issue.suggestion}")
            console.print()

        # Pass/fail
        if result.trust_score >= cfg.min_score and len(result.critical_issues) == 0:
            console.print(Panel("[green]✓ PASSED[/green]", expand=False))
        else:
            console.print(Panel("[red]✗ FAILED[/red]\n"
                              f"Score below {cfg.min_score} or critical issues found", 
                              expand=False))


def _severity_color(severity: str) -> str:
    """Get color for severity level."""
    colors = {
        "critical": "red",
        "high": "orange1",
        "medium": "yellow",
        "low": "dim",
        "info": "blue"
    }
    return colors.get(severity, "white")


def _output_json(results: list[ValidationResult]):
    """Output results as JSON."""
    reporter = JSONReporter()
    print(reporter.generate(results))


@main.command("analytics")
@click.option("--days", "-d", default=30, help="Number of days to analyze")
@click.option("--project", "-p", help="Filter by project")
@click.option("--output", "-o", type=click.Path(), help="Export data to JSON")
@click.option("--leaderboard", is_flag=True, help="Show leaderboard")
def analytics(days: int, project: Optional[str], output: Optional[str], leaderboard: bool):
    """View team analytics and statistics."""
    from ai_trust_validator import AnalyticsDB, generate_analytics_report
    
    db = AnalyticsDB()
    
    if leaderboard:
        console.print("[bold]🏆 Team Leaderboard[/bold]\n")
        board = db.get_leaderboard(days=days)
        
        table = Table(show_header=True)
        table.add_column("Rank", justify="right")
        table.add_column("User")
        table.add_column("Validations", justify="right")
        table.add_column("Avg Score", justify="right")
        table.add_column("Pass Rate", justify="right")
        
        for entry in board:
            table.add_row(
                str(entry["rank"]),
                entry["user"],
                str(entry["validations"]),
                str(entry["avg_score"]),
                f"{entry['pass_rate']}%"
            )
        
        console.print(table)
        return
    
    stats = db.get_stats(days=days, project=project)
    
    # Summary panel
    console.print(Panel(
        f"Validations: {stats.total_validations} | "
        f"Avg Score: {stats.average_score} | "
        f"Pass Rate: {stats.pass_rate}% | "
        f"Critical Issues: {stats.critical_issues}",
        title="📊 Analytics Summary"
    ))
    
    # Category averages
    if stats.category_averages:
        console.print("\n[bold]Category Averages[/bold]")
        table = Table(show_header=True)
        table.add_column("Category")
        table.add_column("Avg Score", justify="right")
        
        for cat, score in stats.category_averages.items():
            table.add_row(cat.replace("_", " ").title(), str(score))
        
        console.print(table)
    
    # Project breakdown
    if stats.project_breakdown:
        console.print("\n[bold]📁 Projects[/bold]")
        table = Table(show_header=True)
        table.add_column("Project")
        table.add_column("Validations", justify="right")
        table.add_column("Avg Score", justify="right")
        table.add_column("Critical", justify="right")
        
        for p in stats.project_breakdown[:10]:
            table.add_row(
                p["project"],
                str(p["validations"]),
                str(p["avg_score"]),
                str(p["critical_issues"])
            )
        
        console.print(table)
    
    # Export if requested
    if output:
        db.export_data(output, days=days)
        console.print(f"\n[green]✓ Data exported to {output}[/green]")


@main.command("lsp")
def lsp():
    """Start the LSP server for IDE integration."""
    console.print("[bold]🚀 Starting LSP Server...[/bold]")
    console.print("[dim]Connect your IDE to use AI Trust Validator in real-time.[/dim]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    from ai_trust_validator.lsp_server import run_lsp_server
    run_lsp_server()


@main.command("languages")
def languages():
    """Show supported languages and file extensions."""
    from ai_trust_validator.languages import LANGUAGE_MAP

    table = Table(title="🌐 Supported Languages")
    table.add_column("Language", style="cyan")
    table.add_column("Extensions", style="green")
    table.add_column("Status")

    for lang, info in sorted(LANGUAGE_MAP.items()):
        exts = ", ".join(f".{e}" for e in info["extensions"])
        table.add_row(lang.title(), exts, "✅ Supported")

    console.print(table)


if __name__ == "__main__":
    main()
