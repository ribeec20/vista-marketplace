# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Vista is a Claude Code plugin (Python + FastMCP 3.0) that provides visual feature planning, architecture diagramming, and autonomous development loops ("Ralph"). It includes an embedded web UI ("The Companion") for browser-based Claude Code interaction.

## Development Commands

### Vista Plugin (Python)

```bash
# MCP server is auto-started by Claude Code via .mcp.json — no manual startup needed
# Manual test run:
python vista/mcp_server.py

# Run all tests
pytest vista/tests/

# Run a single test file
pytest vista/tests/test_ralph_service.py

# Run a specific test
pytest vista/tests/test_ralph_service.py::test_function_name
```

### The Companion (Web UI)

```bash
# Dev server (Hono backend on :3457, Vite HMR on :5174)
cd vista/companion/web && bun install && bun run dev

# Type checking
cd vista/companion/web && bun run typecheck

# Production build + serve (port 3456)
cd vista/companion/web && bun run build && bun run start

# Tests
cd vista/companion/web && bun run test
cd vista/companion/web && bun run test:watch

# Landing page — always use the script, never run bun/vite manually in landing/
./vista/companion/scripts/landing-start.sh          # start
./vista/companion/scripts/landing-start.sh --stop   # stop
```

## Architecture

### Two-Component System

1. **Vista Plugin** (`vista/`) — Python MCP server + FastAPI dashboard
2. **The Companion** (`vista/companion/`) — Bun/React web UI for Claude Code sessions

### Vista Plugin Layers

```
MCP Server (mcp_server.py, stdio transport)
  ├── FastMCP 3.0 tools: spawn_teammate, send_message, ralph_*, team_*
  ├── Launches FastAPI dashboard as daemon thread on port 3456
  └── Detects client type (Claude Code vs OpenCode)

FastAPI Dashboard (server/app.py)
  ├── Routes (server/routes/) — 14 route files for projects, loops, ralph, chat, export
  ├── Services (server/services/) — 17 service files for business logic
  ├── Models (server/models/) — Pydantic models: project, loop_state, chat_session, sandbox
  └── Views (server/views/) — Jinja2 templates + static assets
```

### The Companion Data Flow

```
Browser (React) ←→ WebSocket ←→ Hono Server (Bun) ←→ WebSocket (NDJSON) ←→ Claude Code CLI
     :5174              /ws/browser/:id        :3456        /ws/cli/:id         (--sdk-url)
```

Key files: `ws-bridge.ts` (message router), `cli-launcher.ts` (process management), `session-store.ts` (JSON persistence to `$TMPDIR/vibe-sessions/`).

### Key Patterns

- **Multi-provider abstraction**: `provider_router.py` routes to Claude Code or OpenCode
- **Service lifecycle**: `service_lifecycle.py` manages startup/shutdown orchestration
- **Skill system**: Skills in `vista/skills/*/SKILL.md` with YAML frontmatter define Claude Code workflows (planning, diagrams, ralph, tdd, specs)
- **Vendored dependencies**: `vista/vendor/claude_teams/` provides team coordination (spawning, messaging, tasks)
- **Feature data**: Stored in project-local `.vista/features/` directories; global data in `~/.vista/data/`
- **Settings**: Persistent at `~/.vista/settings.json`, legacy fallback at `vista/settings.json`

### Import Path Setup

The MCP server adds `vista/` and `vista/vendor/` to `sys.path` so imports use `from server.*` and `from claude_teams.*` (not `from vista.server.*`).

## Testing

- **Python**: pytest + pytest-asyncio. Tests use `tmp_path` fixtures and `patched_config` to isolate from real data. FastAPI TestClient for API tests.
- **Companion**: Vitest + Testing Library. Tests co-located with source. Husky pre-commit hook runs typecheck + tests.
- Never remove existing tests without explicit approval. Fix the code or the test instead.

## Conventions

- Conventional commits: `feat()`, `fix()`, `plan()`, `build()`
- The Companion uses commitizen-formatted commit messages and PR titles
- Python 3.14, Bun runtime for Companion
- FastMCP 3.0 beta (`fastmcp==3.0.0b1`) for MCP tools
- Dashboard port 3456 is the default but dynamically discovers a free port if occupied
