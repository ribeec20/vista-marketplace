# Operational Guide: ralph-mcp-tool

## Running Tests

### Unit Tests

Run all unit tests:
```bash
pytest vista/tests/test_ralph_settings.py
pytest vista/tests/test_ralph_service.py
pytest vista/tests/test_summarizer_service.py
```

Run specific test:
```bash
pytest vista/tests/test_ralph_settings.py::test_live_model_discovery
```

### Integration Tests

Run integration tests (requires real subprocess):
```bash
pytest vista/tests/integration/test_ralph_lifecycle.py
pytest vista/tests/integration/test_mcp_tools.py
```

### Platform-Specific Tests

On Windows:
```powershell
pytest vista/tests/test_ralph_service.py::test_windows_pid_check
pytest vista/tests/test_ralph_service.py::test_windows_process_termination
```

On Unix/Mac:
```bash
pytest vista/tests/test_ralph_service.py::test_unix_pid_check
pytest vista/tests/test_ralph_service.py::test_unix_process_termination
```

## Development Workflow

### Setting Up Development Environment

1. Install dependencies:
   ```bash
   pip install -e .
   pip install pytest pytest-asyncio
   ```

2. Verify MCP server registration:
   ```bash
   cat vista/.mcp.json
   ```

3. Start Vista server (optional, for dashboard testing):
   ```bash
   python -m vista.mcp_server
   ```

### Testing MCP Tools Locally

Use the FastMCP CLI to test tools:

```bash
# Test provider discovery
mcp dev vista/mcp_server.py
# In the REPL:
> call ralph_providers

# Test job creation
> call ralph_start slug="test-job" mode="plan" task_description="Test task"

# Test status check
> call ralph_status job_id="<job-id-from-start>"

# Test job stop
> call ralph_stop job_id="<job-id>"
```

### Debugging Subprocesses

1. Check if job subprocess is running:
   ```powershell
   # Windows
   tasklist | findstr <PID>

   # Unix/Mac
   ps -p <PID>
   ```

2. Read job artifacts:
   ```bash
   # Job metadata
   cat .vista/ralph/{slug}/job.json

   # Progress
   cat .vista/ralph/{slug}/progress.txt

   # Full output
   cat .vista/ralph/{slug}/output.log
   ```

3. Manually run loop script (for debugging):
   ```powershell
   # Windows
   cd <project-root>
   powershell -ExecutionPolicy Bypass -File .vista/ralph/{slug}/loop.ps1

   # Unix/Mac
   cd <project-root>
   bash .vista/ralph/{slug}/loop.sh
   ```

### Testing Settings Changes

1. Edit settings manually:
   ```bash
   code vista/settings.json
   ```

2. Verify settings load:
   ```python
   from vista.server.config import get_ralph_settings
   print(get_ralph_settings())
   ```

3. Test provider filtering:
   ```python
   from vista.server.services.provider_service import get_ralph_providers
   print(get_ralph_providers())
   ```

## Dashboard Testing

### Access Dashboard

1. Start MCP server (auto-starts dashboard):
   ```bash
   python -m vista.mcp_server
   ```

2. Open browser:
   ```
   http://127.0.0.1:3456
   ```

3. Navigate to ralph jobs:
   ```
   http://127.0.0.1:3456/ralph/jobs
   ```

### Manual Testing Checklist

- [ ] Job list displays all jobs with correct status
- [ ] Status indicators show correct colors (blue/green/red/gray)
- [ ] Job detail page shows progress updates (auto-refresh)
- [ ] Stop button terminates job (visible only for running jobs)
- [ ] Artifact links work (task.md, progress.txt, output.log)
- [ ] Settings page loads with live-discovered models
- [ ] Settings save correctly (preserves other sections)
- [ ] Refresh Models button updates model lists

## Common Issues & Solutions

### Issue: Provider CLI not found

**Symptom:** `ralph_providers` returns empty model list for a provider.

**Solution:**
1. Verify CLI is installed:
   ```bash
   claude --version
   opencode --version
   ```

2. Check provider is enabled in settings:
   ```json
   {
     "providers": {
       "claude": { "enabled": true }
     }
   }
   ```

3. Check ralph section:
   ```json
   {
     "ralph": {
       "providers": {
         "claude": { "enabled": true }
       }
     }
   }
   ```

### Issue: Job status shows "failed" but subprocess is running

**Symptom:** PID check fails even though process is alive.

**Solution:**
1. Check PID from job.json:
   ```bash
   cat .vista/ralph/{slug}/job.json | grep pid
   ```

2. Verify process exists:
   ```powershell
   # Windows
   tasklist | findstr <PID>

   # Unix/Mac
   ps -p <PID>
   ```

3. Check platform-specific PID verification code:
   - Windows: `_is_process_running` uses OpenProcess
   - Unix: `_is_process_running` uses os.kill(pid, 0)

### Issue: Subprocess creates visible console window

**Symptom:** PowerShell window appears when ralph_start is called.

**Solution:**
1. Verify CREATE_NO_WINDOW flag is set:
   ```python
   # In ralph_service.py
   if platform.system() == "Windows":
       kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
   ```

2. Restart MCP server for changes to take effect.

### Issue: MCP tool timeout (> 60s)

**Symptom:** `ralph_summary` times out before returning.

**Solution:**
1. Check summarizer timeout:
   ```python
   # Should be 55s (5s buffer)
   proc.communicate(input=prompt, timeout=55)
   ```

2. Use faster model for summarizer:
   ```json
   {
     "ralph": {
       "summarizer": {
         "model": "haiku"  // Fast model
       }
     }
   }
   ```

3. Verify artifact truncation (prevent large inputs):
   - progress.txt: last 100 lines
   - IMPLEMENTATION_PLAN.md: first 500 lines

### Issue: Settings changes not reflected

**Symptom:** Changed settings.json but `ralph_providers` shows old data.

**Solution:**
1. Settings are read on each tool call (no caching for v1).
2. Verify file was saved correctly:
   ```bash
   cat vista/settings.json | grep ralph
   ```

3. Check for JSON syntax errors:
   ```bash
   python -c "import json; json.load(open('vista/settings.json'))"
   ```

4. Restart MCP server if needed (should not be necessary).

## Performance Monitoring

### Tool Call Times

Monitor tool call durations:

- `ralph_providers`: Target < 15s (depends on provider CLI speed)
- `ralph_start`: Target < 5s (fire-and-forget)
- `ralph_status`: Target < 1s (fast PID check)
- `ralph_summary`: Target < 60s (MCP limit)
- `ralph_stop`: Target < 5s (termination + state update)

### Subprocess Resource Usage

Check running ralph jobs:

```powershell
# Windows
tasklist /FI "IMAGENAME eq powershell.exe" /FI "STATUS eq running"

# Unix/Mac
ps aux | grep bash | grep loop.sh
```

Check disk usage:
```bash
du -sh .vista/ralph/*
```

## Logs & Debugging

### MCP Server Logs

MCP server runs via stdio transport. Logs go to Claude Code's log panel.

To see detailed logs:
1. Open Claude Code
2. View → Command Palette → "Claude: Show Logs"
3. Filter by "vista" or "mcp"

### Job Logs

Each job has an output.log file:
```bash
tail -f .vista/ralph/{slug}/output.log
```

View progress:
```bash
tail -f .vista/ralph/{slug}/progress.txt
```

### Dashboard Logs

Dashboard logs appear in MCP server stdout (if running standalone):
```bash
python -m vista.mcp_server
# Watch for FastAPI logs
```

## Release Checklist

Before merging to main:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Platform tests pass (Windows and Unix)
- [ ] Manual dashboard testing complete
- [ ] Settings UI tested (live discovery, save, refresh)
- [ ] MCP tools tested via FastMCP CLI
- [ ] Documentation complete (README, AGENTS.md)
- [ ] No regression in standalone ralph.py
- [ ] Performance metrics within targets

## Architecture Diagrams

No architecture diagrams exist yet for this feature. They will be created during implementation planning.

## Additional Resources

- FastMCP documentation: https://github.com/jlowin/fastmcp
- MCP protocol: https://modelcontextprotocol.io
- Vista project structure: See `vista/README.md`
- Provider abstraction: See `vista/server/services/provider_service.py`
- Loop service patterns: See `vista/server/services/loop_service.py`
