Continue building the architecture-chat feature, update progress tracking, and sync the implementation plan with actual code state and git commits.

## Context

The architecture-chat feature has been partially implemented. A prior build loop (job 5d505475) completed iteration 1 which created the core files. You need to:

1. **Assess current state**: Read the git log and diff to understand what's been built so far
2. **Continue building**: Pick up any incomplete phases from the implementation plan
3. **Update progress**: Write accurate progress to `.vista/features/architecture-chat/progress.txt`
4. **Update implementation plan**: Sync `.vista/features/architecture-chat/IMPLEMENTATION_PLAN.md` with actual code state — mark completed phases, note any deviations from the plan, update with real file paths and line counts

## Key Files

### Implementation Plan (v2 — the authoritative plan)
- `.vista/ralph/architecture-chat-plan-86118b3b/IMPLEMENTATION_PLAN.md` — v2 plan with protocol corrections

### Feature Directory
- `.vista/features/architecture-chat/domain-requirements.md` — Requirements
- `.vista/features/architecture-chat/IMPLEMENTATION_PLAN.md` — Plan copy (update this)
- `.vista/features/architecture-chat/progress.txt` — Progress tracking (update this)
- `.vista/features/architecture-chat/specs/opencode-server-reference.md` — OpenCode API reference
- `.vista/features/architecture-chat/specs/companion-websocket-reference.md` — Companion WS reference

### Source Code (check what exists)
- `vista/server/services/service_lifecycle.py`
- `vista/server/services/provider_router.py`
- `vista/server/services/claude_ws_client.py`
- `vista/server/services/opencode_client.py`
- `vista/server/services/context_assembler.py`
- `vista/server/services/diagram_watcher.py` (should be rewritten to watchdog)
- `vista/server/routes/service_status.py`
- `vista/server/routes/chat_sessions.py` (should use ProviderRouter)
- `vista/server/services/chat_service.py` (should delegate to ProviderRouter)
- `vista/server/views/architecture.html` (service status bar, provider availability)
- `vista/server/app.py` (lifecycle integration)
- `vista/mcp_server.py` (cleanup)

### Companion Fork
- `vista/companion/` — Cloned WebSocket bridge (DO NOT modify)

### Tests
- Run with: `python -m pytest tests/ -q` (from vista/ dir)
- All tests must pass

## Workflow

1. `git log --oneline -20` to see recent commits
2. Read the v2 implementation plan
3. Check each phase's files — do they exist? Are they complete?
4. Continue building anything incomplete
5. Run tests, fix any failures
6. Update progress.txt with accurate status per phase
7. Update IMPLEMENTATION_PLAN.md marking completed steps
8. Commit and push