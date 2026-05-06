"""Tests for Logic Analyzer."""

import pytest
from ai_trust_validator.analyzers.logic import LogicAnalyzer
from ai_trust_validator.config import Config


@pytest.fixture
def analyzer():
    return LogicAnalyzer(Config())


@pytest.fixture
def parse_code():
    import ast
    return lambda code: ast.parse(code)


class TestUnreachableCode:
    def test_unreachable_after_return(self, analyzer, parse_code):
        code = '''
def example():
    return 42
    print("unreachable")
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("unreachable" in i.message.lower() for i in issues)

    def test_unreachable_after_raise(self, analyzer, parse_code):
        code = '''
def example():
    raise ValueError("error")
    print("unreachable")
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("unreachable" in i.message.lower() for i in issues)

    def test_no_false_positive(self, analyzer, parse_code):
        code = '''
def example():
    if condition:
        return 1
    return 2
'''
        issues = analyzer.analyze(parse_code(code), code)
        unreachable = [i for i in issues if "unreachable" in i.message.lower()]
        assert len(unreachable) == 0


class TestInfiniteLoops:
    def test_while_true_no_break(self, analyzer, parse_code):
        code = '''
def process():
    while True:
        do_something()
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("infinite" in i.message.lower() for i in issues)

    def test_while_true_with_break(self, analyzer, parse_code):
        code = '''
def process():
    while True:
        result = do_something()
        if result:
            break
'''
        issues = analyzer.analyze(parse_code(code), code)
        infinite = [i for i in issues if "infinite" in i.message.lower()]
        assert len(infinite) == 0

    def test_while_true_with_return(self, analyzer, parse_code):
        code = '''
def process():
    while True:
        if done:
            return result
'''
        issues = analyzer.analyze(parse_code(code), code)
        infinite = [i for i in issues if "infinite" in i.message.lower()]
        assert len(infinite) == 0


class TestUnusedVariables:
    def test_unused_variable(self, analyzer, parse_code):
        code = '''
def example():
    result = compute()
    return 42
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("unused" in i.message.lower() for i in issues)

    def test_underscore_prefix_is_ignored(self, analyzer, parse_code):
        code = '''
def example():
    _ = compute()
    return 42
'''
        issues = analyzer.analyze(parse_code(code), code)
        unused = [i for i in issues if "unused" in i.message.lower()]
        assert len(unused) == 0

    def test_used_variable_is_safe(self, analyzer, parse_code):
        code = '''
def example():
    result = compute()
    return result
'''
        issues = analyzer.analyze(parse_code(code), code)
        unused = [i for i in issues if "unused" in i.message.lower()]
        assert len(unused) == 0


class TestConstantConditions:
    def test_always_true(self, analyzer, parse_code):
        code = '''
if True:
    do_something()
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("always True" in i.message for i in issues)

    def test_always_false_while(self, analyzer, parse_code):
        code = '''
while False:
    do_something()
'''
        issues = analyzer.analyze(parse_code(code), code)
        assert any("always False" in i.message for i in issues)


class TestEmptyBlocks:
    def test_empty_function(self, analyzer, parse_code):
        code = 'def placeholder():\n    pass'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("empty" in i.message.lower() for i in issues)

    def test_ellipsis_function(self, analyzer, parse_code):
        code = 'def placeholder():\n    ...'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("ellipsis" in i.message.lower() for i in issues)


class TestRedundantComparisons:
    def test_x_equals_x(self, analyzer, parse_code):
        code = 'if x == x:\n    pass'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("Redundant" in i.message for i in issues)

    def test_x_not_equals_x(self, analyzer, parse_code):
        code = 'if x != x:\n    pass'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("Redundant" in i.message for i in issues)
