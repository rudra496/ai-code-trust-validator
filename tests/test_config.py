"""Tests for Config module."""

from ai_trust_validator.config import Config


class TestConfigDefaults:
    def test_default_min_score(self):
        config = Config()
        assert config.min_score == 70

    def test_default_strict_mode(self):
        config = Config()
        assert config.strict_mode is False

    def test_default_ignore(self):
        config = Config()
        assert config.ignore == []

    def test_default_security_weight(self):
        config = Config()
        assert config.checks.security.weight == 2.0

    def test_default_hallucinations_weight(self):
        config = Config()
        assert config.checks.hallucinations.weight == 2.5

    def test_default_logic_weight(self):
        config = Config()
        assert config.checks.logic.weight == 1.0

    def test_default_best_practices_weight(self):
        config = Config()
        assert config.checks.best_practices.weight == 0.5

    def test_all_checks_enabled(self):
        config = Config()
        assert config.checks.security.enabled is True
        assert config.checks.hallucinations.enabled is True
        assert config.checks.logic.enabled is True
        assert config.checks.best_practices.enabled is True


class TestConfigFromFile:
    def test_missing_file_returns_defaults(self, tmp_path):
        config = Config.from_file(tmp_path / "nonexistent.yaml")
        assert config.min_score == 70

    def test_custom_min_score(self, tmp_path):
        config_file = tmp_path / ".aitrust.yaml"
        config_file.write_text("min_score: 90\n")
        config = Config.from_file(config_file)
        assert config.min_score == 90

    def test_strict_mode(self, tmp_path):
        config_file = tmp_path / ".aitrust.yaml"
        config_file.write_text("strict_mode: true\n")
        config = Config.from_file(config_file)
        assert config.strict_mode is True

    def test_ignore_patterns(self, tmp_path):
        config_file = tmp_path / ".aitrust.yaml"
        config_file.write_text("ignore:\n  - tests/\n  - venv/\n")
        config = Config.from_file(config_file)
        assert "tests/" in config.ignore
        assert "venv/" in config.ignore

    def test_custom_weights(self, tmp_path):
        config_file = tmp_path / ".aitrust.yaml"
        config_file.write_text("""
checks:
  security:
    weight: 3.0
  hallucinations:
    weight: 2.0
""")
        config = Config.from_file(config_file)
        assert config.checks.security.weight == 3.0
        assert config.checks.hallucinations.weight == 2.0

    def test_disabled_check(self, tmp_path):
        config_file = tmp_path / ".aitrust.yaml"
        config_file.write_text("""
checks:
  best_practices:
    enabled: false
""")
        config = Config.from_file(config_file)
        assert config.checks.best_practices.enabled is False
