## Build & Run

Project: plugin_1
Feature: mvp
Feature Directory: C:/Users/Grove/OneDrive/Documents/AI Agents/claude code/plugin_1/.claude/features/mvp

### Run

- Install deps: `pip install -r requirements.txt`
- Start server: `cd "C:/Users/Grove/OneDrive/Documents/AI Agents/claude code/plugin_1" && python -m uvicorn server.app:app --host 127.0.0.1 --port 3456`
- Open: http://localhost:3456
- Windows script: `scripts/start-server.ps1`

### Validation

- Run tests: `cd "C:/Users/Grove/OneDrive/Documents/AI Agents/claude code/plugin_1" && python -m pytest tests/ -v`

## Notes

- Working directory must be plugin_1 root for `server.app:app` module resolution
- Tests use `unittest.mock.patch` to isolate config paths to tmp directories
- sse-starlette is required for SSE streaming endpoint
