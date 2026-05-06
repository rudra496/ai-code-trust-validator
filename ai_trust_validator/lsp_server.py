"""
LSP Server - Language Server Protocol implementation.

Provides real-time validation in IDEs that support LSP.
"""

import json
import queue
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class MessageType(Enum):
    ERROR = 1
    WARNING = 2
    INFO = 3
    LOG = 4


@dataclass
class Position:
    line: int
    character: int


@dataclass
class Range:
    start: Position
    end: Position


@dataclass
class Diagnostic:
    range: Range
    severity: int  # 1=Error, 2=Warning, 3=Information, 4=Hint
    message: str
    source: str = "ai-trust-validator"
    code: Optional[str] = None


class LSPServer:
    """
    Language Server Protocol implementation for AI Code Trust Validator.
    
    Provides:
    - Real-time diagnostics
    - Code actions (fix suggestions)
    - Hover information
    - Document validation
    
    Usage with VS Code / Neovim / other LSP clients:
        aitrust lsp
    """

    # Severity mapping
    SEVERITY_MAP = {
        "critical": 1,  # Error
        "high": 1,      # Error
        "medium": 2,    # Warning
        "low": 3,       # Information
        "info": 4,      # Hint
    }

    def __init__(self):
        self.validator = None
        self._documents: Dict[str, str] = {}
        self._running = False
        self._message_queue = queue.Queue()
        self._content_length = 0

    def start(self):
        """Start the LSP server."""
        from ai_trust_validator import Validator
        self.validator = Validator()
        self._running = True

        # Send initialization
        self._send_response({
            "jsonrpc": "2.0",
            "method": "setTrace",
            "params": {"value": "off"}
        })

        # Process messages
        while self._running:
            try:
                message = self._read_message()
                if message:
                    self._handle_message(message)
            except Exception as e:
                self._log(f"Error: {e}")

    def _read_message(self) -> Optional[Dict]:
        """Read a JSON-RPC message from stdin."""
        try:
            # Read headers
            headers = {}
            while True:
                line = sys.stdin.readline()
                if not line or line == "\r\n":
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            # Read content
            content_length = int(headers.get("content-length", 0))
            if content_length > 0:
                content = sys.stdin.read(content_length)
                return json.loads(content)
        except Exception:
            pass
        return None

    def _send_response(self, response: Dict):
        """Send a JSON-RPC message to stdout."""
        content = json.dumps(response)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"
        sys.stdout.write(message)
        sys.stdout.flush()

    def _log(self, message: str):
        """Log a message to the client."""
        self._send_response({
            "jsonrpc": "2.0",
            "method": "window/logMessage",
            "params": {
                "type": MessageType.LOG.value,
                "message": message
            }
        })

    def _handle_message(self, message: Dict):
        """Handle an incoming JSON-RPC message."""
        method = message.get("method", "")
        params = message.get("params", {})
        msg_id = message.get("id")

        handlers = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "shutdown": self._handle_shutdown,
            "exit": self._handle_exit,
            "textDocument/didOpen": self._handle_did_open,
            "textDocument/didChange": self._handle_did_change,
            "textDocument/didClose": self._handle_did_close,
            "textDocument/hover": self._handle_hover,
            "textDocument/codeAction": self._handle_code_action,
        }

        handler = handlers.get(method)
        if handler:
            result = handler(params)
            if msg_id is not None:
                self._send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                })

    def _handle_initialize(self, params: Dict) -> Dict:
        """Handle initialize request."""
        return {
            "capabilities": {
                "textDocumentSync": {
                    "openClose": True,
                    "change": 1,  # Full sync
                    "save": True
                },
                "diagnostics": {
                    "interFileDependencies": False,
                    "dynamicRegistration": False
                },
                "hoverProvider": True,
                "codeActionProvider": {
                    "codeActionKinds": ["quickfix", "refactor"]
                },
                "executeCommandProvider": {
                    "commands": ["aitrust.fix", "aitrust.validate"]
                }
            },
            "serverInfo": {
                "name": "AI Code Trust Validator",
                "version": "0.2.0"
            }
        }

    def _handle_initialized(self, params: Dict) -> None:
        """Handle initialized notification."""
        self._log("🛡️ AI Code Trust Validator initialized")

    def _handle_shutdown(self, params: Dict) -> None:
        """Handle shutdown request."""
        self._running = False
        return None

    def _handle_exit(self, params: Dict) -> None:
        """Handle exit notification."""
        self._running = False
        sys.exit(0)

    def _handle_did_open(self, params: Dict) -> None:
        """Handle document open."""
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        text = doc.get("text", "")
        self._documents[uri] = text
        self._validate_document(uri)

    def _handle_did_change(self, params: Dict) -> None:
        """Handle document change."""
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        changes = params.get("contentChanges", [])
        if changes:
            self._documents[uri] = changes[0].get("text", "")
            self._validate_document(uri)

    def _handle_did_close(self, params: Dict) -> None:
        """Handle document close."""
        doc = params.get("textDocument", {})
        uri = doc.get("uri", "")
        self._documents.pop(uri, None)

    def _handle_hover(self, params: Dict) -> Optional[Dict]:
        """Handle hover request."""
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})
        text = self._documents.get(uri, "")

        if not text:
            return None

        # Get trust score
        result = self.validator.validate(text, is_file=False)

        return {
            "contents": {
                "kind": "markdown",
                "value": f"""**🛡️ AI Trust Score: {result.trust_score}/100**

- Security: {result.categories.get('security', {}).get('score', 'N/A') if hasattr(result.categories.get('security', {}), 'get') else result.categories.get('security', 0)}
- Hallucinations: {result.categories.get('hallucinations', 0)}
- Logic: {result.categories.get('logic', 0)}
- Best Practices: {result.categories.get('best_practices', 0)}

Issues: {len(result.all_issues)} ({len(result.critical_issues)} critical)"""
            }
        }

    def _handle_code_action(self, params: Dict) -> List[Dict]:
        """Handle code action request."""
        uri = params.get("textDocument", {}).get("uri", "")
        range_info = params.get("range", {})
        context = params.get("context", {})
        diagnostics = context.get("diagnostics", [])

        actions = []
        text = self._documents.get(uri, "")

        if not text:
            return actions

        # Get fix suggestions
        from ai_trust_validator import FixSuggester
        result = self.validator.validate(text, is_file=False)
        suggester = FixSuggester()
        fixes = suggester.suggest_fixes(result, text)

        for fix in fixes[:5]:  # Limit to 5 fixes
            actions.append({
                "title": f"Fix: {fix.issue.message[:50]}...",
                "kind": "quickfix",
                "diagnostics": [{
                    "range": {
                        "start": {"line": fix.issue.line - 1, "character": 0},
                        "end": {"line": fix.issue.line - 1, "character": 1000}
                    },
                    "message": fix.issue.message,
                    "severity": self.SEVERITY_MAP.get(fix.issue.severity, 2)
                }],
                "edit": {
                    "changes": {
                        uri: [{
                            "range": {
                                "start": {"line": fix.issue.line - 1, "character": 0},
                                "end": {"line": fix.issue.line, "character": 0}
                            },
                            "newText": fix.suggested_fix + "\n"
                        }]
                    }
                }
            })

        return actions

    def _validate_document(self, uri: str):
        """Validate a document and send diagnostics."""
        text = self._documents.get(uri, "")
        if not text:
            return

        result = self.validator.validate(text, is_file=False)
        diagnostics = []

        for issue in result.all_issues:
            diagnostics.append({
                "range": {
                    "start": {"line": (issue.line or 1) - 1, "character": 0},
                    "end": {"line": (issue.line or 1) - 1, "character": 1000}
                },
                "severity": self.SEVERITY_MAP.get(issue.severity, 2),
                "message": issue.message,
                "source": "ai-trust-validator",
                "code": issue.category,
                "relatedInformation": [{
                    "location": {
                        "uri": uri,
                        "range": {
                            "start": {"line": (issue.line or 1) - 1, "character": 0},
                            "end": {"line": (issue.line or 1) - 1, "character": 1000}
                        }
                    },
                    "message": issue.suggestion or ""
                }] if issue.suggestion else None
            })

        self._send_response({
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": uri,
                "diagnostics": diagnostics
            }
        })


def run_lsp_server():
    """Run the LSP server."""
    server = LSPServer()
    server.start()
