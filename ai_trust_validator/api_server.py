"""
REST API Server - HTTP interface for validation.

Run with: aitrust serve --port 8080
API docs at: http://localhost:8080/docs
"""

import json
import time
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse


@dataclass
class APIResponse:
    """Standard API response format."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str = ""
    duration_ms: float = 0.0


class ValidationAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for validation API."""

    validator = None
    config = None

    def log_message(self, format, *args):
        """Override to use custom logging."""
        pass  # Suppress default logging

    def _send_json(self, status: int, response: APIResponse):
        """Send JSON response."""
        response.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(asdict(response)).encode())

    def _read_body(self) -> bytes:
        """Read request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        start_time = time.time()

        if path == "/":
            # Root - API info
            response = APIResponse(
                success=True,
                data={
                    "name": "AI Code Trust Validator API",
                    "version": "0.1.0",
                    "endpoints": {
                        "/": "API information",
                        "/health": "Health check",
                        "/validate": "Validate code (POST)",
                        "/stats": "Validation statistics",
                        "/docs": "API documentation",
                    }
                }
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(200, response)

        elif path == "/health":
            # Health check
            response = APIResponse(
                success=True,
                data={"status": "healthy", "validator": "ready"}
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(200, response)

        elif path == "/stats":
            # Get statistics
            stats = self._get_stats()
            response = APIResponse(success=True, data=stats)
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(200, response)

        elif path == "/docs":
            # API documentation
            docs = self._generate_docs()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(docs.encode())

        else:
            response = APIResponse(
                success=False,
                error=f"Unknown endpoint: {path}"
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(404, response)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        start_time = time.time()

        if path == "/validate":
            self._handle_validate(start_time)
        elif path == "/validate/batch":
            self._handle_batch_validate(start_time)
        else:
            response = APIResponse(
                success=False,
                error=f"Unknown endpoint: {path}"
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(404, response)

    def _handle_validate(self, start_time: float):
        """Handle single validation request."""
        try:
            body = self._read_body().decode("utf-8")
            data = json.loads(body)

            code = data.get("code")
            if not code:
                response = APIResponse(
                    success=False,
                    error="Missing 'code' in request body"
                )
                response.duration_ms = (time.time() - start_time) * 1000
                self._send_json(400, response)
                return

            # Optional parameters
            min_score = data.get("min_score", 70)
            strict = data.get("strict", False)

            # Validate
            from ai_trust_validator import Config, Validator
            config = Config(min_score=min_score, strict_mode=strict)
            validator = Validator(config)
            result = validator.validate(code, is_file=False)

            response = APIResponse(
                success=True,
                data={
                    "trust_score": result.trust_score,
                    "passed": result.passed,
                    "categories": {
                        name: {
                            "score": cat.score,
                            "weight": cat.weight,
                            "issue_count": len(cat.issues)
                        }
                        for name, cat in result.categories.items()
                    },
                    "issues": [
                        {
                            "severity": i.severity,
                            "category": i.category,
                            "message": i.message,
                            "line": i.line,
                            "suggestion": i.suggestion
                        }
                        for i in result.all_issues
                    ],
                    "critical_count": len(result.critical_issues),
                    "summary": self._generate_summary(result)
                }
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(200, response)

        except json.JSONDecodeError:
            response = APIResponse(
                success=False,
                error="Invalid JSON in request body"
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(400, response)

        except Exception as e:
            response = APIResponse(
                success=False,
                error=f"Validation error: {str(e)}"
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(500, response)

    def _handle_batch_validate(self, start_time: float):
        """Handle batch validation request."""
        try:
            body = self._read_body().decode("utf-8")
            data = json.loads(body)

            files = data.get("files", [])
            if not files:
                response = APIResponse(
                    success=False,
                    error="Missing 'files' array in request body"
                )
                response.duration_ms = (time.time() - start_time) * 1000
                self._send_json(400, response)
                return

            # Validate all files
            from ai_trust_validator import Config, Validator
            config = Config(
                min_score=data.get("min_score", 70),
                strict_mode=data.get("strict", False)
            )
            validator = Validator(config)

            results = []
            for file_data in files:
                result = validator.validate(file_data.get("code", ""), is_file=False)
                results.append({
                    "file": file_data.get("name", "unnamed"),
                    "trust_score": result.trust_score,
                    "passed": result.passed,
                    "critical_count": len(result.critical_issues)
                })

            response = APIResponse(
                success=True,
                data={
                    "results": results,
                    "total": len(results),
                    "passed": sum(1 for r in results if r["passed"]),
                    "failed": sum(1 for r in results if not r["passed"])
                }
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(200, response)

        except Exception as e:
            response = APIResponse(
                success=False,
                error=f"Batch validation error: {str(e)}"
            )
            response.duration_ms = (time.time() - start_time) * 1000
            self._send_json(500, response)

    def _get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "version": "0.1.0",
            "analyzer_count": 4,
            "supported_languages": ["Python"],
            "features": [
                "security_analysis",
                "hallucination_detection",
                "logic_validation",
                "best_practices_check"
            ]
        }

    def _generate_summary(self, result) -> str:
        """Generate a text summary."""
        if result.trust_score >= 80:
            return f"Code is trustworthy (score: {result.trust_score}/100)"
        elif result.trust_score >= 60:
            return f"Code needs attention (score: {result.trust_score}/100)"
        else:
            return f"Code has significant issues (score: {result.trust_score}/100)"

    def _generate_docs(self) -> str:
        """Generate API documentation HTML."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>AI Code Trust Validator API</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background: #1a1a2e; color: #e4e4e4; }
        h1 { color: #00d9ff; }
        h2 { color: #00ff88; border-bottom: 1px solid #333; padding-bottom: 10px; }
        code { background: #2a2a4e; padding: 2px 6px; border-radius: 4px; }
        pre { background: #2a2a4e; padding: 16px; border-radius: 8px; overflow-x: auto; }
        .endpoint { margin: 20px 0; padding: 16px; background: rgba(255,255,255,0.03); border-radius: 8px; }
        .method { color: #00ff88; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🛡️ AI Code Trust Validator API</h1>
    
    <h2>Endpoints</h2>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> /</h3>
        <p>API information and available endpoints.</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> /health</h3>
        <p>Health check endpoint.</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">POST</span> /validate</h3>
        <p>Validate a single code snippet.</p>
        <h4>Request Body:</h4>
        <pre>{
  "code": "def hello():\\n    print('world')",
  "min_score": 70,
  "strict": false
}</pre>
        <h4>Response:</h4>
        <pre>{
  "success": true,
  "data": {
    "trust_score": 85,
    "passed": true,
    "issues": [...]
  }
}</pre>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">POST</span> /validate/batch</h3>
        <p>Validate multiple code files.</p>
        <h4>Request Body:</h4>
        <pre>{
  "files": [
    {"name": "file1.py", "code": "..."},
    {"name": "file2.py", "code": "..."}
  ],
  "min_score": 70
}</pre>
    </div>
    
    <footer style="margin-top: 40px; color: #666;">
        <p>Created by <a href="https://rudra496.github.io/site" style="color: #00d9ff;">Rudra Sarker</a></p>
    </footer>
</body>
</html>"""


def run_server(port: int = 8080, host: str = "0.0.0.0"):
    """Run the API server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, ValidationAPIHandler)

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  🛡️  AI Code Trust Validator API Server                  ║
╠══════════════════════════════════════════════════════════╣
║  Running on: http://{host}:{port}                        ║
║  API Docs:    http://localhost:{port}/docs               ║
║  Health:      http://localhost:{port}/health             ║
╠══════════════════════════════════════════════════════════╣
║  Press Ctrl+C to stop                                    ║
╚══════════════════════════════════════════════════════════╝
""")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped.")
        httpd.shutdown()
