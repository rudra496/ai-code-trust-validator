# Screenshots & Demos

This folder contains screenshots and demo assets for the AI Code Trust Validator.

## What to add here

- `cli-demo.png` — CLI validation output showing trust score and issues
- `dashboard-demo.png` — Web dashboard with analytics and treemap
- `vscode-demo.png` — VS Code extension showing inline diagnostics
- `jetbrains-demo.png` — JetBrains plugin in action
- `ai-fix-demo.png` — AI auto-fix in terminal
- `html-report-demo.png` — Generated HTML report

## How to capture

### CLI Demo
```bash
aitrust validate example_code.py
# Screenshot the terminal output
```

### Dashboard Demo
```bash
aitrust watch src/ --dashboard
# Open browser to http://localhost:8080
# Screenshot the dashboard
```

### VS Code Demo
1. Open a Python/JS file with known issues
2. The extension will show inline diagnostics
3. Screenshot with the Problems panel visible

### JetBrains Demo
1. Open IntelliJ or PyCharm with the plugin installed
2. Open a file with trust issues
3. Screenshot the inline annotations and tool window

## Tips
- Use a dark terminal theme for consistency
- Keep window size reasonable (1200px width recommended)
- Highlight the trust score prominently
- Show both the problem and the fix suggestion
