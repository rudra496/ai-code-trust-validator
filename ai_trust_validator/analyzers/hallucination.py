"""
Hallucination Analyzer

Detects AI hallucinations in code:
- Non-existent imports
- Invented function calls
- Fake attributes/methods
- Imaginary modules
"""

import ast
import re
from typing import Dict, List, Optional, Set

from ai_trust_validator.analyzers import BaseAnalyzer
from ai_trust_validator.models import Issue

# Known standard library modules (Python 3.8+)
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
    "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "imaplib", "imghdr", "imp",
    "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers", "operator", "optparse", "os", "ossaudiodev", "pathlib",
    "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
    "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue",
    "quopri", "random", "re", "readline", "reprlib", "resource",
    "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib",
    "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "ssl",
    "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
    "types", "typing", "unicodedata", "unittest", "urllib", "uu",
    "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib", "_thread",
}

# Popular third-party packages
POPULAR_PACKAGES = {
    "numpy", "pandas", "matplotlib", "scipy", "sklearn", "tensorflow",
    "torch", "keras", "requests", "flask", "django", "fastapi", "pydantic",
    "pytest", "selenium", "beautifulsoup4", "bs4", "pillow", "PIL",
    "sqlalchemy", "celery", "redis", "pymongo", "boto3", "click",
    "rich", "tqdm", "polars", "pyarrow",
    "opencv", "cv2", "scikit-learn", "xgboost", "lightgbm",
    "transformers", "huggingface_hub", "langchain", "openai", "anthropic",
}


class HallucinationAnalyzer(BaseAnalyzer):
    """Detects AI hallucinations in imports and function calls."""

    base_score = 100

    def __init__(self, config):
        super().__init__(config)
        self._known_modules: Optional[Set[str]] = None
        self._installed_packages: Optional[Set[str]] = None

    def analyze(self, tree: ast.AST, code: str) -> List[Issue]:
        """Analyze code for hallucinations."""
        issues: List[Issue] = []

        # Collect imports
        imports = self._collect_imports(tree)

        # Check for suspicious imports
        issues.extend(self._check_imports(imports))

        # Check for undefined function calls
        issues.extend(self._check_undefined_calls(tree, imports))

        # Check for suspicious naming patterns
        issues.extend(self._check_suspicious_patterns(tree, code))

        return issues

    def _collect_imports(self, tree: ast.AST) -> Dict[str, str]:
        """Collect all imports and their aliases."""
        imports: Dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports[name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports[name] = f"{module}.{alias.name}" if module else alias.name

        return imports

    def _check_imports(self, imports: Dict[str, str]) -> List[Issue]:
        """Check for potentially hallucinated imports."""
        issues: List[Issue] = []

        for alias, full_name in imports.items():
            base_module = full_name.split(".")[0]

            # Check if it's a known module
            if base_module in STDLIB_MODULES:
                continue
            if base_module in POPULAR_PACKAGES:
                continue
            if base_module in self._get_installed_packages():
                continue

            # Suspicious patterns that suggest hallucination
            suspicious_patterns = [
                r"^ai_",  # AI-prefixed fake modules
                r"^smart_",  # Smart-prefixed
                r"^auto_",  # Auto-prefixed
                r"^quick_",  # Quick-prefixed
                r"^easy_",  # Easy-prefixed
                r"_v\d+$",  # Versioned fake modules
                r"^lib\d+",  # Numbered libraries
                r".*_utils_.*",  # Generic utils
            ]

            for pattern in suspicious_patterns:
                if re.search(pattern, base_module.lower()):
                    issues.append(Issue(
                        severity="critical",
                        category="hallucination",
                        message=f"Import '{full_name}' appears to be hallucinated",
                        suggestion=f"Verify '{base_module}' exists or find a real alternative"
                    ))
                    break

            # If not in any known list, flag as warning
            else:
                if not self._is_likely_real(base_module):
                    issues.append(Issue(
                        severity="medium",
                        category="hallucination",
                        message=f"Import '{full_name}' is not in standard/popular packages",
                        suggestion=f"Verify '{base_module}' is installed: pip install {base_module}"
                    ))

        return issues

    def _check_undefined_calls(self, tree: ast.AST, imports: Dict[str, str]) -> List[Issue]:
        """Check for calls to undefined functions."""
        issues: List[Issue] = []

        # Collect all defined functions and classes
        defined_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)

        # Built-in functions
        builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))

        # Check calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name not in defined_names and func_name not in imports and func_name not in builtins:
                        # Check for hallucinated function patterns
                        if self._is_suspicious_function_name(func_name):
                            issues.append(Issue(
                                severity="critical",
                                category="hallucination",
                                message=f"Function '{func_name}' appears hallucinated (not defined or imported)",
                                line=self._get_line(node),
                                suggestion=f"Define '{func_name}' or import it from a real module"
                            ))

        return issues

    def _check_suspicious_patterns(self, tree: ast.AST, code: str) -> List[Issue]:
        """Check for other hallucination patterns."""
        issues: List[Issue] = []

        # AI-generated code often has these patterns
        suspicious = [
            (r"# TODO: implement", "Unimplemented TODO suggests incomplete AI code"),
            (r"# Your code here", "Placeholder comment suggests incomplete AI code"),
            (r"pass\s*# placeholder", "Placeholder code"),
            (r"raise NotImplementedError", "Unimplemented method"),
            (r"# ...", "Ellipsis comment suggests incomplete code"),
        ]

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern, message in suspicious:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(Issue(
                        severity="low",
                        category="hallucination",
                        message=message,
                        line=i,
                        suggestion="Complete the implementation or remove placeholder"
                    ))

        return issues

    def _is_suspicious_function_name(self, name: str) -> bool:
        """Check if function name looks hallucinated."""
        patterns = [
            r"^quick\w+",  # quickSort, quickProcess
            r"^fast\w+",   # fastHash, fastProcess
            r"^smart\w+",  # smartParse, smartHandle
            r"^auto\w+",   # autoProcess, autoHandle
            r"^easy\w+",   # easyConvert
            r"^simple\w+", # simpleHash
            r"_v\d+$",     # function_v1, function_v2
            r"\d+$",       # function2, process1
        ]
        name_lower = name.lower()
        return any(re.search(p, name_lower) for p in patterns)

    def _is_likely_real(self, module: str) -> bool:
        """Check if module name looks like a real package."""
        # Common real package patterns
        real_patterns = [
            r"^django", r"^flask", r"^fastapi", r"^py", r"^python",
            r"^google", r"^aws", r"^azure", r"^boto", r"^kubernetes",
        ]
        return any(re.search(p, module.lower()) for p in real_patterns)

    def _get_installed_packages(self) -> Set[str]:
        """Get set of installed packages (cached)."""
        if self._installed_packages is None:
            self._installed_packages = set()
            try:
                import pkg_resources
                self._installed_packages = {pkg.key for pkg in pkg_resources.working_set}
            except ImportError:
                pass
        return self._installed_packages
