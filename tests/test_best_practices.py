"""Tests for Best Practices Analyzer."""

import pytest

from ai_trust_validator.analyzers.best_practices import BestPracticesAnalyzer
from ai_trust_validator.config import Config


@pytest.fixture
def analyzer():
    return BestPracticesAnalyzer(Config())


@pytest.fixture
def parse_code():
    import ast
    return lambda code: ast.parse(code)


class TestBareExcept:
    def test_bare_except(self, analyzer, parse_code):
        code = '''
try:
    risky()
except:
    pass
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("bare" in i.message.lower() for i in issues)

    def test_specific_except_is_safe(self, analyzer, parse_code):
        code = '''
try:
    risky()
except ValueError:
    pass
'''
        issues = analyzer.analyze(parse_code(code), code)
        bare = [i for i in issues if "bare" in i.message.lower()]
        assert len(bare) == 0


class TestMutableDefaults:
    def test_list_default(self, analyzer, parse_code):
        code = 'def add_item(item, items=[]):\n    items.append(item)\n    return items'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("mutable" in i.message.lower() for i in issues)

    def test_dict_default(self, analyzer, parse_code):
        code = 'def process(data, cache={}):\n    return cache'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("mutable" in i.message.lower() for i in issues)

    def test_none_default_is_safe(self, analyzer, parse_code):
        code = 'def add_item(item, items=None):\n    if items is None:\n        items = []\n    return items'
        issues = analyzer.analyze(parse_code(code), code)
        mutable = [i for i in issues if "mutable" in i.message.lower()]
        assert len(mutable) == 0


class TestNamingConventions:
    def test_snake_case_function(self, analyzer, parse_code):
        code = 'def myFunction():\n    pass'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("snake_case" in i.message for i in issues)

    def test_pascal_case_class(self, analyzer, parse_code):
        code = 'class my_class:\n    pass'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("PascalCase" in i.message for i in issues)

    def test_snake_case_variable(self, analyzer, parse_code):
        code = 'myVariable = 42'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("snake_case" in i.message for i in issues)


class TestDocstrings:
    def test_missing_module_docstring(self, analyzer, parse_code):
        code = 'x = 42'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("Module" in i.message and "docstring" in i.message for i in issues)

    def test_module_with_docstring(self, analyzer, parse_code):
        code = '"""Module doc."""\nx = 42'
        issues = analyzer.analyze(parse_code(code), code)
        module_doc = [i for i in issues if "Module" in i.message]
        assert len(module_doc) == 0


class TestFunctionLength:
    def test_long_function(self, analyzer, parse_code):
        lines = "\n".join(f"    x = {i}" for i in range(55))
        code = f"def long_function():\n{lines}"
        issues = analyzer.analyze(parse_code(code), code)
        assert any("too long" in i.message for i in issues)
