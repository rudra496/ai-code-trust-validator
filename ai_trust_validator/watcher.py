"""
Watch Mode - Continuous file monitoring and validation.

Automatically re-validates when files change.
"""

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional


@dataclass
class FileState:
    """Tracked state of a file."""
    path: str
    last_modified: float
    content_hash: str
    last_score: int
    last_issues_count: int


class Watcher:
    """
    Watch files/directories for changes and re-validate.
    
    Usage:
        watcher = Watcher(validator)
        watcher.watch("src/", on_change=print_results)
    """

    POLL_INTERVAL = 1.0  # seconds

    def __init__(self, validator, config=None):
        self.validator = validator
        self.config = config
        self._tracked: Dict[str, FileState] = {}
        self._running = False
        self._callbacks: List[Callable] = []

    def watch(
        self,
        path: str,
        on_change: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        poll_interval: float = POLL_INTERVAL
    ) -> None:
        """
        Watch a file or directory for changes.
        
        Args:
            path: File or directory to watch
            on_change: Callback(result, file_path) on validation
            on_error: Callback(error, file_path) on error
            poll_interval: How often to check for changes
        """
        path_obj = Path(path)

        if not path_obj.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Register callback
        if on_change:
            self._callbacks.append(on_change)

        self._running = True

        print(f"👀 Watching: {path}")
        print("   Press Ctrl+C to stop\n")

        try:
            while self._running:
                if path_obj.is_file():
                    self._check_file(path_obj, on_error)
                else:
                    self._check_directory(path_obj, on_error)

                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n\n👋 Watch stopped.")

    def stop(self) -> None:
        """Stop watching."""
        self._running = False

    def _check_file(self, file_path: Path, on_error: Optional[Callable]) -> bool:
        """Check a single file for changes."""
        path_str = str(file_path)
        stat = file_path.stat()

        current_modified = stat.st_mtime
        content = file_path.read_text(encoding="utf-8")
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if changed
        if path_str in self._tracked:
            tracked = self._tracked[path_str]
            if (tracked.last_modified == current_modified and
                tracked.content_hash == content_hash):
                return False  # No change

        # File changed or new - validate
        try:
            result = self.validator.validate(file_path)

            # Update tracked state
            self._tracked[path_str] = FileState(
                path=path_str,
                last_modified=current_modified,
                content_hash=content_hash,
                last_score=result.trust_score,
                last_issues_count=len(result.all_issues)
            )

            # Notify callbacks
            for callback in self._callbacks:
                callback(result, path_str)

            return True

        except Exception as e:
            if on_error:
                on_error(e, path_str)
            return False

    def _check_directory(self, dir_path: Path, on_error: Optional[Callable]) -> int:
        """Check all Python files in directory for changes."""
        changed_count = 0

        for file_path in dir_path.glob("**/*.py"):
            # Skip common non-source directories
            if any(part in file_path.parts for part in ["__pycache__", ".git", "venv", "node_modules"]):
                continue

            if self._check_file(file_path, on_error):
                changed_count += 1

        return changed_count

    def get_summary(self) -> Dict:
        """Get summary of all tracked files."""
        if not self._tracked:
            return {"total_files": 0}

        scores = [t.last_score for t in self._tracked.values()]
        issues = [t.last_issues_count for t in self._tracked.values()]

        return {
            "total_files": len(self._tracked),
            "average_score": sum(scores) / len(scores),
            "total_issues": sum(issues),
            "excellent": len([s for s in scores if s >= 80]),
            "good": len([s for s in scores if 60 <= s < 80]),
            "poor": len([s for s in scores if s < 60]),
            "files": [
                {"path": t.path, "score": t.last_score}
                for t in sorted(self._tracked.values(), key=lambda x: x.last_score)
            ]
        }


def watch_with_dashboard(
    path: str,
    validator,
    config=None,
    refresh_rate: float = 2.0
):
    """
    Watch with a live terminal dashboard.
    
    Shows real-time trust scores and issues.
    """
    import time

    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    watcher = Watcher(validator, config)

    # Initial scan
    path_obj = Path(path)
    if path_obj.is_file():
        watcher._check_file(path_obj, None)
    else:
        watcher._check_directory(path_obj, None)

    def generate_display():
        summary = watcher.get_summary()

        # Create table
        table = Table(title="🔍 AI Code Trust Monitor", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Issues", justify="right")
        table.add_column("Status", justify="center")

        for file_info in summary.get("files", [])[:20]:  # Limit to 20
            score = file_info["score"]
            if score >= 80:
                status = "[green]✓ PASS[/green]"
                score_style = "green"
            elif score >= 60:
                status = "[yellow]⚠ WARN[/yellow]"
                score_style = "yellow"
            else:
                status = "[red]✗ FAIL[/red]"
                score_style = "red"

            # Shorten path
            file_display = file_info["path"]
            if len(file_display) > 50:
                file_display = "..." + file_display[-47:]

            table.add_row(
                file_display,
                f"[{score_style}]{score}[/{score_style}]",
                str(file_info.get("issues", 0)),
                status
            )

        # Summary panel
        summary_panel = Panel(
            f"Files: {summary['total_files']} | "
            f"Avg Score: {summary['average_score']:.1f} | "
            f"✓ {summary['excellent']} | "
            f"⚠ {summary['good']} | "
            f"✗ {summary['poor']}",
            title="Summary"
        )

        return f"{table}\n{summary_panel}"

    console.print("[bold]Starting watch mode...[/bold]")
    console.print(f"[dim]Watching: {path}[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        with Live(generate_display(), refresh_per_second=1/refresh_rate) as live:
            while True:
                # Check for changes
                path_obj = Path(path)
                if path_obj.is_file():
                    watcher._check_file(path_obj, None)
                else:
                    watcher._check_directory(path_obj, None)

                # Update display
                live.update(generate_display())
                time.sleep(refresh_rate)

    except KeyboardInterrupt:
        console.print("\n[bold]Watch stopped.[/bold]")
