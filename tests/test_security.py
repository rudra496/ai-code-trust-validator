"""Tests for Security Analyzer."""

import pytest
from ai_trust_validator.analyzers.security import SecurityAnalyzer
from ai_trust_validator.config import Config


@pytest.fixture
def analyzer():
    return SecurityAnalyzer(Config())


@pytest.fixture
def parse_code():
    import ast
    return lambda code: ast.parse(code)


class TestSQLInjection:
    def test_f_string_in_execute(self, analyzer, parse_code):
        code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("SQL injection" in i.message for i in issues)

    def test_percent_format_in_execute(self, analyzer, parse_code):
        code = 'cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("SQL injection" in i.message for i in issues)

    def test_safe_parameterized_query(self, analyzer, parse_code):
        code = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
        issues = analyzer.analyze(parse_code(code), code)
        sql_issues = [i for i in issues if "SQL" in i.message]
        assert len(sql_issues) == 0


class TestHardcodedSecrets:
    def test_hardcoded_password(self, analyzer, parse_code):
        code = 'password = "super_secret_123"'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("password" in i.message.lower() for i in issues)

    def test_hardcoded_api_key(self, analyzer, parse_code):
        code = 'api_key = "sk-abc123xyz"'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("api key" in i.message.lower() for i in issues)

    def test_hardcoded_aws_creds(self, analyzer, parse_code):
        code = 'aws_access_key = "AKIAIOSFODNN7EXAMPLE"'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("aws" in i.message.lower() for i in issues)

    def test_env_var_password_is_safe(self, analyzer, parse_code):
        code = 'password = os.environ.get("DB_PASSWORD")'
        issues = analyzer.analyze(parse_code(code), code)
        secret_issues = [i for i in issues if "password" in i.message.lower()]
        assert len(secret_issues) == 0


class TestDangerousFunctions:
    def test_eval_detection(self, analyzer, parse_code):
        code = 'result = eval(user_input)'
        issues = analyzer.analyze(parse_code(code), code)
        eval_issues = [i for i in issues if "eval" in i.message]
        assert len(eval_issues) > 0
        assert eval_issues[0].severity == "critical"

    def test_exec_detection(self, analyzer, parse_code):
        code = 'exec(compiled_code)'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("exec" in i.message for i in issues)

    def test_compile_detection(self, analyzer, parse_code):
        code = 'compiled = compile(source, "<string>", "exec")'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("Compiling" in i.message for i in issues)


class TestSubprocess:
    def test_shell_true(self, analyzer, parse_code):
        code = 'subprocess.run(cmd, shell=True)'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("shell=True" in i.message for i in issues)

    def test_shell_false_is_safe(self, analyzer, parse_code):
        code = 'subprocess.run(["ls", "-la"], shell=False)'
        issues = analyzer.analyze(parse_code(code), code)
        shell_issues = [i for i in issues if "shell" in i.message]
        assert len(shell_issues) == 0


class TestPathTraversal:
    def test_fstring_in_open(self, analyzer, parse_code):
        code = 'f = open(f"/uploads/{filename}")'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("path traversal" in i.message.lower() for i in issues)

    def test_dot_dot_in_path(self, analyzer, parse_code):
        code = 'f = open("/var/data/../../etc/passwd")'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("path traversal" in i.message.lower() for i in issues)


class TestSSRF:
    def test_requests_fstring_url(self, analyzer, parse_code):
        code = 'requests.get(f"https://{host}/api/data")'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("SSRF" in i.message for i in issues)

    def test_urlopen_fstring(self, analyzer, parse_code):
        code = 'urllib.request.urlopen(f"http://{user_input}/endpoint")'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("SSRF" in i.message for i in issues)


class TestYAMLDeserialization:
    def test_yaml_load_unsafe(self, analyzer, parse_code):
        code = 'data = yaml.load(f.read())'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("yaml.load" in i.message for i in issues)
        assert any(i.severity == "critical" for i in issues)

    def test_yaml_safe_load_is_safe(self, analyzer, parse_code):
        code = 'data = yaml.safe_load(f.read())'
        issues = analyzer.analyze(parse_code(code), code)
        yaml_issues = [i for i in issues if "yaml" in i.message]
        assert len(yaml_issues) == 0

    def test_pickle_load(self, analyzer, parse_code):
        code = 'obj = pickle.load(f)'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("pickle" in i.message for i in issues)
        assert any(i.severity == "critical" for i in issues)


class TestHardcodedInternalURL:
    def test_localhost_url(self, analyzer, parse_code):
        code = 'url = "http://localhost:8080/api"'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("internal URL" in i.message for i in issues)

    def test_private_ip_url(self, analyzer, parse_code):
        code = 'url = "http://192.168.1.100/admin"'
        issues = analyzer.analyze(parse_code(code), code)
        assert any("internal URL" in i.message for i in issues)
