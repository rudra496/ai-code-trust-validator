"""Tests for AI Trust Validator."""

import pytest
from ai_trust_validator import Validator, Config
from ai_trust_validator.models import Issue


def test_validator_basic():
    """Test basic validation."""
    code = '''
def hello():
    """Say hello."""
    print("Hello, world!")
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    assert result.trust_score > 0
    assert len(result.critical_issues) == 0


def test_security_sql_injection():
    """Test detection of SQL injection."""
    code = '''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    # Should detect SQL injection
    security_issues = [i for i in result.all_issues if i.category == "security"]
    assert len(security_issues) > 0
    assert any("SQL injection" in i.message for i in security_issues)


def test_security_hardcoded_password():
    """Test detection of hardcoded passwords."""
    code = '''
DATABASE_PASSWORD = "super_secret_123"

def connect():
    pass
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    security_issues = [i for i in result.all_issues if i.category == "security"]
    assert any("password" in i.message.lower() for i in security_issues)


def test_hallucination_suspicious_import():
    """Test detection of suspicious imports."""
    code = '''
import quick_sort_v2
import ai_smart_utils

def process():
    pass
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    hallucination_issues = [i for i in result.all_issues if i.category == "hallucination"]
    assert len(hallucination_issues) > 0


def test_logic_unreachable_code():
    """Test detection of unreachable code."""
    code = '''
def example():
    return 42
    print("This is unreachable")
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    logic_issues = [i for i in result.all_issues if i.category == "logic"]
    assert any("unreachable" in i.message.lower() for i in logic_issues)


def test_logic_infinite_loop():
    """Test detection of infinite loops."""
    code = '''
def process():
    while True:
        do_something()
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    logic_issues = [i for i in result.all_issues if i.category == "logic"]
    assert any("infinite" in i.message.lower() for i in logic_issues)


def test_best_practices_bare_except():
    """Test detection of bare except."""
    code = '''
def risky_operation():
    try:
        do_something()
    except:
        pass
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    bp_issues = [i for i in result.all_issues if i.category == "best_practices"]
    assert any("bare" in i.message.lower() for i in bp_issues)


def test_best_practices_mutable_default():
    """Test detection of mutable default arguments."""
    code = '''
def add_item(item, items=[]):
    items.append(item)
    return items
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    bp_issues = [i for i in result.all_issues if i.category == "best_practices"]
    assert any("mutable" in i.message.lower() for i in bp_issues)


def test_syntax_error():
    """Test handling of syntax errors."""
    code = '''
def broken(:
    pass
'''
    validator = Validator()
    result = validator.validate(code, is_file=False)

    assert result.trust_score == 0
    assert len(result.critical_issues) > 0


def test_config_loading():
    """Test configuration loading."""
    config = Config()
    assert config.min_score == 70
    assert config.checks.security.weight == 2.0
    assert config.checks.hallucinations.weight == 2.5
