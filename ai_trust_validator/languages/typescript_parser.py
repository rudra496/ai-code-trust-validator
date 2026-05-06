"""TypeScript language parser for trust validation."""

from ai_trust_validator.languages.base import LanguageParser, ParseResult


class TypeScriptParser(LanguageParser):
    """Parse TypeScript/TSX files for analysis."""

    def parse(self, code: str) -> ParseResult:
        return ParseResult(language="typescript", code=code)
