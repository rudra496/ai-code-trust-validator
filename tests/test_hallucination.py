"""Tests for Hallucination Analyzer."""

import pytest
from ai_trust_validator.analyzers.hallucination import HallucinationAnalyzer
from ai_trust_validator.config import Config


@pytest.fixture
def analyzer():
    return HallucinationAnalyzer(Config())


@pytest.fixture
def parse_code():
    import ast
    return lambda code: ast.parse(code)


class TestSuspiciousImports:
    def test_ai_prefixed_import(self, analyzer, parse_code):
        code = 'import ai_smart_utils'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("hallucinated" in i.message.lower() for i in issues)

    def test_quick_prefixed_import(self, analyzer, parse_code):
        code = 'import quick_sort_v2'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("hallucinated" in i.message.lower() for i in issues)

    def test_stdlib_import_is_safe(self, analyzer, parse_code):
        code = 'import json\nimport os\nfrom pathlib import Path'
        issues = analyzer.analyze(parse_code(code), code)
        hallucination_issues = [i for i in issues if "hallucinated" in i.message.lower()]
        assert len(hallucination_issues) == 0

    def test_popular_package_is_safe(self, analyzer, parse_code):
        code = 'import numpy\nimport pandas'
        issues = analyzer.analyze(parse_code(code), code)
        hallucination_issues = [i for i in issues if "hallucinated" in i.message.lower()]
        assert len(hallucination_issues) == 0

    def test_auto_prefixed_import(self, analyzer, parse_code):
        code = 'import auto_processor'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("hallucinated" in i.message.lower() for i in issues)


class TestUndefinedFunctions:
    def test_suspicious_function_call(self, analyzer, parse_code):
        code = 'result = fast_hash(data)'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("hallucinated" in i.message.lower() for i in issues)

    def test_defined_function_is_safe(self, analyzer, parse_code):
        code = '''
def fast_hash(data):
    return hash(data)

result = fast_hash(data)
'''
        issues = analyzer.analyze(parse_code(code), code)
        hallucination_issues = [i for i in issues if "hallucinated" in i.message.lower()]
        assert len(hallucination_issues) == 0

    def test_builtin_function_is_safe(self, analyzer, parse_code):
        code = 'result = sorted(items)\nlength = len(items)'
        issues = analyzer.analyze(parse_code(code), code)
        hallucination_issues = [i for i in issues if "hallucinated" in i.message.lower()]
        assert len(hallucination_issues) == 0


class TestPlaceholderPatterns:
    def test_todo_implement(self, analyzer, parse_code):
        code = 'def process():\n    # TODO: implement this\n    pass'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("TODO" in i.message or "incomplete" in i.message.lower() for i in issues)

    def test_not_implemented_error(self, analyzer, parse_code):
        code = 'def process():\n    raise NotImplementedError'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("Unimplemented" in i.message or "incomplete" in i.message.lower() for i in issues)
