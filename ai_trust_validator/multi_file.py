"""
Multi-File Analyzer - Cross-file dependency analysis.

Analyzes imports, dependencies, and relationships across multiple files.
"""

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ModuleInfo:
    """Information about a Python module."""
    path: str
    name: str
    imports: List[str]
    exports: List[str]  # Functions/classes defined
    classes: List[str]
    functions: List[str]
    dependencies: Set[str] = field(default_factory=set)
    trust_score: Optional[int] = None


@dataclass
class DependencyEdge:
    """A dependency relationship between modules."""
    from_module: str
    to_module: str
    imports: List[str]
    is_circular: bool = False


@dataclass
class MultiFileResult:
    """Result of multi-file analysis."""
    modules: Dict[str, ModuleInfo]
    dependencies: List[DependencyEdge]
    circular_dependencies: List[Tuple[str, str]]
    unused_modules: List[str]
    import_issues: List[dict]
    dependency_graph: Dict[str, List[str]]
    trust_scores: Dict[str, int]
    overall_score: int


class MultiFileAnalyzer:
    """
    Analyze multiple files for cross-file issues.
    
    Detects:
    - Circular dependencies
    - Unused imports across files
    - Missing modules
    - Dependency clusters
    - Import inconsistencies
    """

    def __init__(self, validator=None):
        self.validator = validator
        self._modules: Dict[str, ModuleInfo] = {}

    def analyze_directory(self, directory: str) -> MultiFileResult:
        """Analyze all Python files in a directory."""
        dir_path = Path(directory)

        # Collect all modules
        for file_path in dir_path.glob("**/*.py"):
            if "__pycache__" in str(file_path):
                continue
            self._analyze_module(file_path, dir_path)

        # Build dependency graph
        dependencies = self._build_dependencies()

        # Find circular dependencies
        circular = self._find_circular_dependencies()

        # Find unused modules
        unused = self._find_unused_modules()

        # Check import issues
        import_issues = self._check_import_issues()

        # Calculate trust scores if validator available
        trust_scores = {}
        if self.validator:
            for name, module in self._modules.items():
                result = self.validator.validate(module.path)
                trust_scores[name] = result.trust_score
                module.trust_score = result.trust_score

        overall = (
            sum(trust_scores.values()) / len(trust_scores)
            if trust_scores else 50
        )

        return MultiFileResult(
            modules=self._modules,
            dependencies=dependencies,
            circular_dependencies=circular,
            unused_modules=unused,
            import_issues=import_issues,
            dependency_graph=self._build_graph(),
            trust_scores=trust_scores,
            overall_score=int(overall)
        )

    def _analyze_module(self, file_path: Path, root: Path) -> ModuleInfo:
        """Analyze a single module."""
        code = file_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return ModuleInfo(
                path=str(file_path),
                name=self._path_to_module(file_path, root),
                imports=[],
                exports=[],
                classes=[],
                functions=[]
            )

        imports = []
        exports = []
        classes = []
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                exports.append(node.name)

            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith("_"):
                    functions.append(node.name)
                    exports.append(node.name)

        module_name = self._path_to_module(file_path, root)

        info = ModuleInfo(
            path=str(file_path),
            name=module_name,
            imports=imports,
            exports=exports,
            classes=classes,
            functions=functions,
            dependencies=set(imports)
        )

        self._modules[module_name] = info
        return info

    def _path_to_module(self, file_path: Path, root: Path) -> str:
        """Convert file path to module name."""
        relative = file_path.relative_to(root)
        parts = list(relative.parts)

        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")

        return ".".join(parts)

    def _build_dependencies(self) -> List[DependencyEdge]:
        """Build dependency edges between modules."""
        edges = []
        module_names = set(self._modules.keys())

        for name, module in self._modules.items():
            for imp in module.imports:
                # Check if import is a local module
                base_module = imp.split(".")[0]
                if base_module in module_names or any(
                    m.startswith(imp) for m in module_names
                ):
                    # Find matching module
                    for other_name in module_names:
                        if other_name == name:
                            continue
                        if other_name == imp or other_name.startswith(imp + "."):
                            edges.append(DependencyEdge(
                                from_module=name,
                                to_module=other_name,
                                imports=[imp]
                            ))

        return edges

    def _find_circular_dependencies(self) -> List[Tuple[str, str]]:
        """Find circular dependencies."""
        circular = []
        visited = set()
        rec_stack = set()

        def dfs(module: str, path: List[str]) -> Optional[List[str]]:
            visited.add(module)
            rec_stack.add(module)
            path.append(module)

            for dep in self._modules.get(module, ModuleInfo("", "", [], [], [], [])).dependencies:
                dep_base = dep.split(".")[0]
                if dep_base in self._modules:
                    if dep_base not in visited:
                        result = dfs(dep_base, path)
                        if result:
                            return result
                    elif dep_base in rec_stack:
                        # Found cycle
                        return path + [dep_base]

            path.pop()
            rec_stack.remove(module)
            return None

        for module in self._modules:
            if module not in visited:
                cycle = dfs(module, [])
                if cycle and len(cycle) >= 2:
                    circular.append((cycle[0], cycle[-1]))

        return circular

    def _find_unused_modules(self) -> List[str]:
        """Find modules that are never imported."""
        all_imports = set()
        for module in self._modules.values():
            for imp in module.imports:
                all_imports.add(imp.split(".")[0])

        unused = []
        for name in self._modules:
            base = name.split(".")[0]
            if base not in all_imports and not name.endswith("__init__"):
                unused.append(name)

        return unused

    def _check_import_issues(self) -> List[dict]:
        """Check for import-related issues."""
        issues = []
        module_names = set(self._modules.keys())

        for name, module in self._modules.items():
            for imp in module.imports:
                base = imp.split(".")[0]

                # Check if importing non-existent local module
                if base not in module_names and self._is_local_import(imp):
                    issues.append({
                        "type": "missing_module",
                        "module": name,
                        "import": imp,
                        "message": f"Module '{name}' imports non-existent module '{imp}'"
                    })

        return issues

    def _is_local_import(self, imp: str) -> bool:
        """Check if import looks like a local module."""
        # Skip stdlib and known packages
        stdlib = {"os", "sys", "json", "re", "datetime", "typing", "collections", "pathlib"}
        return imp.split(".")[0] not in stdlib

    def _build_graph(self) -> Dict[str, List[str]]:
        """Build adjacency list graph."""
        graph = defaultdict(list)

        for name in self._modules:
            module = self._modules[name]
            for imp in module.imports:
                base = imp.split(".")[0]
                if base in self._modules:
                    graph[name].append(base)

        return dict(graph)

    def generate_dependency_report(self) -> str:
        """Generate a text dependency report."""
        lines = [
            "=" * 60,
            "Dependency Analysis Report",
            "=" * 60,
            ""
        ]

        # Summary
        lines.extend([
            f"Modules analyzed: {len(self._modules)}",
            ""
        ])

        # Dependency graph
        lines.append("Dependency Graph:")
        lines.append("-" * 40)
        graph = self._build_graph()
        for module, deps in sorted(graph.items()):
            if deps:
                lines.append(f"  {module}")
                for dep in deps:
                    lines.append(f"    → {dep}")
        lines.append("")

        # Circular dependencies
        circular = self._find_circular_dependencies()
        if circular:
            lines.append("⚠️ Circular Dependencies:")
            lines.append("-" * 40)
            for a, b in circular:
                lines.append(f"  {a} ↔ {b}")
            lines.append("")

        # Unused modules
        unused = self._find_unused_modules()
        if unused:
            lines.append("📦 Unused Modules (never imported):")
            lines.append("-" * 40)
            for m in unused:
                lines.append(f"  • {m}")

        return "\n".join(lines)
