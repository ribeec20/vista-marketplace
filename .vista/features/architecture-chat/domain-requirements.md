# Domain Requirements: Architecture Chat

> **Status (2026-02-15):** All 8 phases complete. Protocol-native streaming via ProviderRouter (Claude WebSocket + OpenCode SSE), diagram watcher with watchdog, context assembler, service lifecycle manager, model discovery, frontend updates, and integration all delivered. 390 tests passing. Remaining gaps: no dedicated test file for chat session routes/service, watchdog dependency missing from test environment (blocks 28 tests).

## Problem Statement
The current architecture chat implementation uses subprocess-based CLI invocation for AI providers, which limits streaming fidelity, lacks proper tool approval flows, and treats OpenCode as a second-class citizen. The feature needs a redesign to provide multi-provider parity with real-time diagram editing capabilities, using the Companion project's WebSocket bridge for Claude and the OpenCode HTTP server API for OpenCode — both as first-class providers with equivalent streaming, context, and diagram editing capabilities.

## Users & Personas
- **Solo developer** using Vista to plan features visually, chatting with AI about architecture diagrams while seeing edits rendered in real-time
- **Primary platform:** Windows 11 (Windows-first, other platforms nice-to-have)

## Business Objectives
- Replace subprocess-based Claude chat with Companion's `--sdk-url` WebSocket bridge for proper bidirectional streaming
- Add OpenCode server (`opencode serve`) as a first-class provider with HTTP REST + SSE streaming
- Enable real-time diagram editing by AI during chat with instant visual feedback
- Maintain the existing robust context assembly (diagram attachment, node selection) and model selection capabilities
- Single server instance architecture — one active chat session at a time

## Success Metrics
- Token-by-token streaming from both Claude and OpenCode providers
- Diagram changes visible in the web UI within 1 second of AI editing a file
- Zero manual steps to start chatting — all backend services auto-start on plugin load
- Existing context assembly (attached diagrams, selected elements) preserved and working with new backends

## Functional Requirements

### Core Functionality

#### FR-1: Multi-Provider Chat Backend
- Vista's FastAPI server is the single hub for all chat communication
- Claude provider: communicates via WebSocket bridge to Companion fork (cloned at `vista/companion/`)
- OpenCode provider: communicates via HTTP REST API + SSE streaming to `opencode serve`
- Both providers support token-by-token streaming to the frontend
- Provider is locked per session (chosen at session creation, cannot switch mid-session)
- One active chat session at a time across the entire server

#### FR-2: Companion Fork Integration
- Clone https://github.com/ribeec20/claude-websocket-companion into `vista/companion/`
- Use Companion as a **backend-only** service — Vista's frontend connects through Vista's FastAPI, which proxies to Companion's WebSocket endpoints
- Companion auto-starts on plugin load alongside Vista's FastAPI dashboard
- Claude CLI launched with `--sdk-url` flag pointing to Companion's WebSocket endpoint
- Auto-approve all tool calls (no tool approval UI needed — AI operates freely within arch/ and specs/ directories)
- Companion's React frontend is NOT used; Vista's existing Jinja2/vanilla JS chat UI is the interface

#### FR-3: OpenCode Server Integration
- Auto-start `opencode serve` on a free port when plugin loads (if binary detected)
- Communicate via OpenCode's REST API: `POST /session/:id/message` for sending, `GET /event` SSE for streaming
- Use the official OpenCode Python SDK (`opencode-ai` package) where beneficial
- Support per-message model selection via `{providerID, modelID}` in request body
- Handle HTTP Basic Auth if `OPENCODE_SERVER_PASSWORD` is set

#### FR-4: Real-Time Diagram Editing
- AI can read, edit, create, and delete `.mmd` diagram files in `arch/` directory during chat
- AI can also read and edit files in `specs/` directory
- Diagram changes detected by filesystem watcher (Python `watchdog` library, replacing current 2s polling)
- Changes broadcast to frontend via existing SSE event system
- Frontend re-renders affected Mermaid diagrams instantly on change events
- `_arch.json` manifest auto-updated when files are added/removed from arch/ directory

#### FR-5: Context Assembly (Preserved from Existing)
- User attaches diagrams to chat context by clicking diagram cards
- User selects specific diagram nodes to focus conversation
- Attached diagram file contents + selected element connection info assembled into prompt context
- Context assembly happens in Vista's Python backend (not frontend)
- System prompt includes instructions for the AI's role as architecture documentation assistant
- Conversation history included in context for continuity

#### FR-6: Model Selection (Preserved from Existing)
- Provider dropdown in chat panel (Claude / OpenCode)
- Model dropdown populated dynamically from each provider's available models
- Claude models: discovered via Companion or CLI
- OpenCode models: discovered via `GET /config/providers` endpoint
- Selected model persisted per session

#### FR-7: Service Status Dashboard
- Dashboard displays health status for three services:
  1. Vista Dashboard (FastAPI) — name, port, health status, uptime
  2. Claude Bridge (Companion) — name, port, health status, uptime
  3. OpenCode Server — name, port, health status, uptime
- Detailed display: service name, port number, health indicator, uptime
- Auto-restart crashed services with exponential backoff
- Toast notification in UI when a service goes down or recovers
- Graceful degradation: disable unavailable providers in chat UI, allow chat with remaining providers

#### FR-8: Session Management
- One active chat session at a time
- Switching features (e.g., docker-sandbox → architecture-chat) ends the current session, starts fresh
- Previous sessions saved to disk and loadable from history
- Session picker in chat panel for loading previous sessions
- Session auto-named from first user message

### User Workflows

1. **Start Architecture Chat**: User navigates to architecture page for a feature → chat panel available → selects provider and model → attaches diagrams → starts chatting → AI responds with streaming text → AI edits diagrams → changes appear live in the diagram viewer

2. **Switch Feature Context**: User navigates to a different feature's architecture page → current session ends and is saved → fresh session starts → new feature's diagrams shown → user can load previous sessions for this feature

3. **Provider Selection**: User opens chat panel → selects Claude or OpenCode from provider dropdown → model dropdown updates with available models for that provider → user picks model → session created with that provider/model locked in

### Business Rules
- Auto-approve all AI tool calls — no approval UI needed
- AI file access is scoped to `arch/` and `specs/` directories within the feature
- Companion fork lives at `vista/companion/` inside the plugin directory
- All three services (Vista, Companion, OpenCode) managed by the plugin's lifecycle
- Single active session enforced — starting a new session terminates any existing one

## Non-Functional Requirements
- **Performance:** Token streaming latency < 100ms from provider to browser. Diagram re-render < 1s after file change.
- **Platform:** Windows 11 primary. Bun runtime required for Companion fork.
- **Security:** All services bound to localhost only. No external network exposure. Auto-approve scoped to feature directories.
- **Reliability:** Auto-restart crashed services with exponential backoff. Graceful degradation when providers unavailable.

## Constraints & Dependencies
- **Technical:**
  - Bun runtime required for Companion fork (must be installed)
  - Claude Code CLI must be installed for Claude provider
  - OpenCode binary must be installed for OpenCode provider
  - Python `watchdog` package needed for filesystem watching
  - Python `opencode-ai` SDK for OpenCode integration
- **Dependencies:**
  - Companion fork: https://github.com/ribeec20/claude-websocket-companion
  - Existing Vista architecture page and chat UI
  - Existing provider service abstraction
  - Existing diagram watcher service (to be upgraded to watchdog)
- **Integration:**
  - Companion WebSocket protocol (NDJSON, `--sdk-url` flag)
  - OpenCode REST API + SSE (port 4096 default)

## User Experience Requirements
- **Discovery:** Chat panel accessible from architecture page via existing FAB button
- **Layout:** Keep existing right-side sliding chat panel over diagram grid
- **Feedback:** Streaming tokens shown in real-time, diagram changes animate in, service status visible in dashboard
- **Error handling:** Toast notifications for service failures, provider dropdown disables unavailable options, "reconnecting..." states for WebSocket drops

## TDD Candidates

- **ProviderRouter**: Complex routing logic dispatching messages to Claude (WebSocket) vs OpenCode (REST/SSE) with different protocols, error handling, and streaming mechanisms
- **ServiceLifecycleManager**: State machine managing three services (Vista, Companion, OpenCode) with auto-start, health checks, auto-restart with backoff, and graceful shutdown
- **ManifestAutoUpdater**: File watcher triggering _arch.json updates on diagram create/delete with debouncing and validation
- **ContextAssembler**: Complex prompt assembly with diagram contents, selected elements, connection info, history, and system instructions — already has logic that must be preserved through refactor
