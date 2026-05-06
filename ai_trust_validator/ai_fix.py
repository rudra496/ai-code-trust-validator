"""AI-Powered Auto-Fix Module with LLM integration."""
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

from ai_trust_validator.models import Issue


@dataclass
class FixResult:
    success: bool
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float
    issues_addressed: List[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""

@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.3
    timeout: int = 30

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        if os.environ.get("OPENAI_API_KEY"):
            return cls(provider="openai", model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ.get("OPENAI_BASE_URL"))
        if os.environ.get("ANTHROPIC_API_KEY"):
            return cls(provider="anthropic", model=os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"), api_key=os.environ["ANTHROPIC_API_KEY"])
        if os.environ.get("USE_OLLAMA"):
            return cls(provider="ollama", model=os.environ.get("OLLAMA_MODEL", "llama3"), base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
        if os.environ.get("LLM_BASE_URL"):
            return cls(provider="custom", model=os.environ.get("LLM_MODEL", "default"), api_key=os.environ.get("LLM_API_KEY"), base_url=os.environ["LLM_BASE_URL"])
        return cls(provider="none")

class AIAutoFixer:
    FIX_PROMPT = """Fix the following code issues:

ISSUES:
{issues}

ORIGINAL CODE:
```{language}
{code}
```

Return the fixed code followed by a brief explanation. Format:
```{language}
[fixed code]
```

EXPLANATION:
[brief explanation]"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()

    def is_available(self) -> bool:
        return bool(self.config.api_key) or self.config.provider == "ollama"

    def fix(self, code: str, issues: List[Issue], language: str = "python", fix_type: str = "general") -> FixResult:
        if not self.is_available():
            return FixResult(success=False, original_code=code, fixed_code=code, explanation="AI fixing not available. Configure OPENAI_API_KEY, ANTHROPIC_API_KEY, or Ollama.", confidence=0.0, provider="none")
        if not issues:
            return FixResult(success=True, original_code=code, fixed_code=code, explanation="No issues to fix.", confidence=1.0, provider=self.config.provider, model=self.config.model)

        issues_text = "\n".join(f"{i}. [{iss.severity.upper()}] Line {iss.line}: {iss.message}" + (f"\n   Suggestion: {iss.suggestion}" if iss.suggestion else "") for i, iss in enumerate(issues, 1))
        prompt = self.FIX_PROMPT.format(issues=issues_text, code=code, language=language)

        try:
            response = self._call_llm(prompt)
            fixed_code, explanation = self._parse_response(response, language)
            confidence = min(1.0, sum(1 for iss in issues if str(iss.line) in fixed_code or iss.message[:20].lower() in fixed_code.lower()) / len(issues)) if issues else 1.0
            return FixResult(success=True, original_code=code, fixed_code=fixed_code, explanation=explanation, confidence=confidence, provider=self.config.provider, model=self.config.model)
        except Exception as e:
            return FixResult(success=False, original_code=code, fixed_code=code, explanation=f"AI fix failed: {str(e)}", confidence=0.0)

    def _call_llm(self, prompt: str) -> str:
        if self.config.provider == "openai":
            url = self.config.base_url or "https://api.openai.com/v1/chat/completions"
            data = {"model": self.config.model, "messages": [{"role": "system", "content": "You are an expert code fixer. Return only the fixed code with brief explanation."}, {"role": "user", "content": prompt}], "max_tokens": self.config.max_tokens, "temperature": self.config.temperature}
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.config.api_key}"})
        elif self.config.provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            data = {"model": self.config.model, "max_tokens": self.config.max_tokens, "messages": [{"role": "user", "content": prompt}]}
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json", "x-api-key": self.config.api_key, "anthropic-version": "2023-06-01"})
        elif self.config.provider == "ollama":
            url = f"{self.config.base_url or 'http://localhost:11434'}/api/generate"
            data = {"model": self.config.model, "prompt": prompt, "stream": False}
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")

        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
            result = json.loads(resp.read().decode())
            if self.config.provider == "anthropic":
                return result['content'][0]['text']
            elif self.config.provider == "ollama":
                return result['response']
            return result['choices'][0]['message']['content']

    def _parse_response(self, response: str, language: str) -> tuple:
        match = re.compile(rf'```(?:{language})?\s*\n(.*?)\n```', re.DOTALL).search(response)
        if match:
            return match.group(1), response[match.end():].strip() or "Fixed by AI"
        return response, "Fixed by AI"

def ai_fix_code(code: str, issues: List[Issue], language: str = "python", api_key: str = None, model: str = None) -> FixResult:
    config = LLMConfig.from_env()
    if api_key: config.api_key = api_key
    if model: config.model = model
    return AIAutoFixer(config).fix(code, issues, language)
