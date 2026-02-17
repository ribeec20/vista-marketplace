Build the architecture-chat feature following the implementation plan.

## Implementation Plan

The full plan is at: `.vista/ralph/architecture-chat-plan-86118b3b/IMPLEMENTATION_PLAN.md`
Also available at: `.vista/features/architecture-chat/IMPLEMENTATION_PLAN.md`

READ THE FULL PLAN BEFORE STARTING. It has 8 phases with detailed code, file locations, and dependencies.

## Reference Documents

- `.vista/features/architecture-chat/domain-requirements.md` — Full requirements
- `.vista/features/architecture-chat/specs/opencode-server-reference.md` — OpenCode REST API + SSE reference
- `.vista/features/architecture-chat/specs/companion-websocket-reference.md` — Companion WebSocket protocol reference
- `.vista/features/architecture-chat/arch/*.mmd` — Architecture diagrams

## Companion Fork

The Companion WebSocket bridge is already cloned at `vista/companion/`. Read its source code for integration:
- `vista/companion/web/server/index.ts` — Server entry
- `vista/companion/web/server/cli-launcher.ts` — CLI process management
- `vista/companion/web/server/routes.ts` — API routes
- `vista/companion/web/server/ws-bridge.ts` — WebSocket bridge
- `vista/companion/web/server/session-types.ts` — Protocol types

## Build Order (from plan)

Follow the implementation order in the plan:
1. Phase 1: `service_lifecycle.py` + `service_status.py` route + `app.py` lifespan
2. Phase 3: `diagram_watcher.py` rewrite (polling → watchdog)
3. Phase 4: `context_assembler.py` extraction
4. Phase 2: `claude_ws_client.py`, `opencode_client.py`, `provider_router.py`, then `chat_service.py` + `chat_sessions.py` rewrite
5. Phase 5: `provider_service.py` model discovery
6. Phase 6: `architecture.html` frontend changes
7. Phase 7: Companion fork verification
8. Phase 8: Final integration + `mcp_server.py` cleanup

## Key Constraints

- All code goes in `vista/server/` (Python) — NOT in the companion directory
- Windows-first: use CREATE_NO_WINDOW, taskkill /T /F /PID
- New Python deps: watchdog, websockets, httpx
- Keep existing tests passing
- Run tests with: `python -m pytest tests/ -q` (from vista/ dir)