Plan the implementation of the architecture-chat feature for the Vista plugin.

## Context

All domain requirements, architecture diagrams, and reference specs are in:
- `.vista/features/architecture-chat/domain-requirements.md` — Full requirements (8 FRs, TDD candidates)
- `.vista/features/architecture-chat/arch/` — 6 Mermaid architecture diagrams (system architecture, user flow, data model, Claude sequence, OpenCode sequence, service lifecycle state machine)
- `.vista/features/architecture-chat/specs/opencode-server-reference.md` — OpenCode REST API + SSE + Python SDK reference
- `.vista/features/architecture-chat/specs/companion-websocket-reference.md` — Companion WebSocket protocol + NDJSON reference

The Companion fork (Claude web UI WebSocket bridge) is cloned at `vista/companion/` — read its source code to understand the implementation.

## Key Architecture Decisions

- **Vista FastAPI is the hub server** — single entry point for all chat communication
- **Claude provider**: via Companion fork's WebSocket bridge (`--sdk-url` flag), cloned at `vista/companion/`
- **OpenCode provider**: via `opencode serve` HTTP REST API + SSE streaming
- **Frontend**: Keep existing Vista Jinja2/vanilla JS chat UI (not Companion's React UI)
- **One active chat session at a time**, provider locked per session
- **Auto-approve all AI tool calls** — no tool approval UI
- **AI file access**: scoped to `arch/` and `specs/` directories
- **Diagram operations**: create + edit + delete, `_arch.json` manifest auto-updated via `watchdog` filesystem watcher
- **All 3 services** (Vista FastAPI, Companion, OpenCode) auto-started and managed by plugin lifecycle
- **Windows-first** platform

## Existing Code to Understand

- `vista/server/app.py` — FastAPI app
- `vista/server/routes/chat_sessions.py` — Existing chat session routes
- `vista/server/services/chat_service.py` — Existing chat service (subprocess-based, to be replaced)
- `vista/server/services/chat_session_service.py` — Session persistence (keep)
- `vista/server/services/diagram_watcher.py` — Polling-based watcher (upgrade to watchdog)
- `vista/server/services/provider_service.py` — Provider abstraction (extend)
- `vista/server/views/architecture.html` — Frontend with chat panel (adapt)
- `vista/mcp_server.py` — MCP server entry point and lifecycle management
- `vista/companion/` — Companion fork source code (Bun/Hono WebSocket bridge)

## Deliverable

Create a detailed IMPLEMENTATION_PLAN.md at `.vista/features/architecture-chat/IMPLEMENTATION_PLAN.md` that covers:
1. What existing files need modification and what changes
2. What new files/modules need to be created
3. Step-by-step implementation order with dependencies
4. Integration points between Vista, Companion, and OpenCode
5. How the Companion fork should be modified (minimal changes) to work as a backend-only service
6. Service lifecycle management (auto-start, health checks, auto-restart)
7. How to upgrade diagram watcher from polling to watchdog
8. Frontend changes needed in architecture.html for the new WebSocket-based streaming