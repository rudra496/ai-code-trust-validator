"""
Plugin System - Extensible architecture for custom analyzers.

Create custom analyzers by implementing the AnalyzerPlugin interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
import importlib
import inspect
from pathlib import Path

from ai_trust_validator.models import Issue


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    author: str
    description: str
    priority: int = 100  # Lower = runs first


class AnalyzerPlugin(ABC):
    """
    Base class for custom analyzer plugins.
    
    To create a custom analyzer:
    
    1. Create a class inheriting from AnalyzerPlugin
    2. Implement metadata and analyze methods
    3. Register with PluginManager
    """
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
    
    @abstractmethod
    def analyze(self, tree: Any, code: str, context: Dict[str, Any]) -> List[Issue]:
        """
        Analyze code and return issues.
        
        Args:
            tree: Parsed AST of the code
            code: Original source code as string
            context: Additional context (file path, config, etc.)
            
        Returns:
            List of Issue objects found
        """
        pass
    
    def should_run(self, file_path: Optional[str], context: Dict[str, Any]) -> bool:
        """Override to conditionally skip this analyzer."""
        return True
    
    def priority(self) -> int:
        """Execution priority (lower = runs first)."""
        return self.metadata.priority


class PluginManager:
    """
    Manages loading and running analyzer plugins.
    
    Built-in plugins:
    - SecurityAnalyzer
    - HallucinationAnalyzer
    - LogicAnalyzer
    - BestPracticesAnalyzer
    
    Custom plugins can be:
    - Registered programmatically
    - Loaded from Python files
    - Loaded from entry points
    """
    
    def __init__(self):
        self._plugins: Dict[str, AnalyzerPlugin] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_analyze": [],
            "post_analyze": [],
            "on_issue_found": [],
        }
    
    def register(self, plugin: AnalyzerPlugin) -> None:
        """Register a plugin instance."""
        name = plugin.metadata.name
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered")
        self._plugins[name] = plugin
    
    def unregister(self, name: str) -> None:
        """Unregister a plugin by name."""
        self._plugins.pop(name, None)
    
    def get_plugin(self, name: str) -> Optional[AnalyzerPlugin]:
        """Get a registered plugin by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugin names."""
        return list(self._plugins.keys())
    
    def run_all(
        self,
        tree: Any,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Issue]:
        """Run all registered plugins and collect issues."""
        context = context or {}
        all_issues: List[Issue] = []
        
        # Run pre-analyze hooks
        for hook in self._hooks["pre_analyze"]:
            hook(tree, code, context)
        
        # Run plugins in priority order
        sorted_plugins = sorted(
            self._plugins.values(),
            key=lambda p: p.priority()
        )
        
        for plugin in sorted_plugins:
            if plugin.should_run(context.get("file_path"), context):
                try:
                    issues = plugin.analyze(tree, code, context)
                    for issue in issues:
                        # Run on_issue_found hooks
                        for hook in self._hooks["on_issue_found"]:
                            hook(issue, plugin)
                        all_issues.append(issue)
                except Exception as e:
                    # Log but don't fail
                    import warnings
                    warnings.warn(f"Plugin {plugin.metadata.name} failed: {e}")
        
        # Run post-analyze hooks
        for hook in self._hooks["post_analyze"]:
            hook(all_issues, tree, code, context)
        
        return all_issues
    
    def add_hook(self, hook_type: str, callback: Callable) -> None:
        """Add a hook callback for specific events."""
        if hook_type in self._hooks:
            self._hooks[hook_type].append(callback)
    
    def remove_hook(self, hook_type: str, callback: Callable) -> None:
        """Remove a hook callback."""
        if hook_type in self._hooks and callback in self._hooks[hook_type]:
            self._hooks[hook_type].remove(callback)
    
    def load_from_file(self, file_path: str) -> List[str]:
        """
        Load plugins from a Python file.
        
        The file should define one or more AnalyzerPlugin subclasses.
        """
        loaded = []
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Plugin file not found: {file_path}")
        
        # Dynamic import
        spec = importlib.util.spec_from_file_location("custom_plugin", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find all AnalyzerPlugin subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, AnalyzerPlugin) and
                    obj is not AnalyzerPlugin and
                    obj.__module__ == "custom_plugin"
                ):
                    try:
                        plugin = obj()
                        self.register(plugin)
                        loaded.append(plugin.metadata.name)
                    except Exception as e:
                        import warnings
                        warnings.warn(f"Failed to instantiate plugin {name}: {e}")
        
        return loaded
    
    def load_from_entry_points(self) -> List[str]:
        """
        Load plugins from setuptools entry points.
        
        Entry point group: ai_trust_validator.plugins
        """
        loaded = []
        try:
            import importlib.metadata
            entry_points = importlib.metadata.entry_points()
            
            # Handle both old and new importlib.metadata APIs
            if hasattr(entry_points, 'select'):
                eps = entry_points.select(group="ai_trust_validator.plugins")
            else:
                eps = entry_points.get("ai_trust_validator.plugins", [])
            
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    plugin = plugin_class()
                    self.register(plugin)
                    loaded.append(plugin.metadata.name)
                except Exception as e:
                    import warnings
                    warnings.warn(f"Failed to load entry point {ep.name}: {e}")
        except ImportError:
            pass
        
        return loaded


# Example custom plugin
class ExampleCustomPlugin(AnalyzerPlugin):
    """Example custom analyzer plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="example_custom",
            version="0.1.0",
            author="Your Name",
            description="Example custom analyzer plugin",
            priority=200
        )
    
    def analyze(self, tree: Any, code: str, context: Dict[str, Any]) -> List[Issue]:
        issues = []
        # Your custom analysis logic here
        return issues


# Decorator for simple plugins
def analyzer_plugin(
    name: str,
    version: str = "0.1.0",
    author: str = "Unknown",
    description: str = "",
    priority: int = 100
):
    """
    Decorator to create a simple plugin from a function.
    
    Usage:
        @analyzer_plugin("my_checker", description="Checks for X")
        def check_x(tree, code, context):
            issues = []
            # ...
            return issues
    """
    def decorator(func: Callable):
        class FunctionPlugin(AnalyzerPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name=name,
                    version=version,
                    author=author,
                    description=description,
                    priority=priority
                )
            
            def analyze(self, tree, code, context):
                return func(tree, code, context)
        
        return FunctionPlugin()
    
    return decorator
