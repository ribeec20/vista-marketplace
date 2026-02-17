# Spec: AI Chat Review Panel

> Updated: 2026-02-15 — Aligned with protocol-native streaming implementation

## Overview

Side-by-side AI chat interface for reviewing and discussing architecture diagrams with protocol-native streaming to Claude (via Companion WebSocket) and OpenCode (via HTTP SSE).

## Parent JTBD

As a developer, I want to discuss my architecture diagrams with an AI model so I can get feedback, identify issues, and iterate on the design interactively.

## Scope

**In Scope:**
- Chat panel UI (Notion-style slide-out from bottom-right button)
- Side-by-side layout (diagrams left, chat right) when open
- Provider/model dropdown selection
- Diagram click-to-inject-context
- Message send/receive with streaming responses via SSE
- Protocol-native streaming via ProviderRouter (Claude WebSocket, OpenCode SSE)
- Persistent chat sessions with CRUD operations
- ContextAssembler for prompt construction with diagram/spec context
- Diagram file watcher for live diagram change notifications

**Out of Scope:**
- Diagram rendering (see rendering-pipeline spec)
- Multi-user chat / collaboration
- AI-suggested "Apply" button for writing back diagram edits

## Requirements

### Functional

1. Bottom-right floating button opens/closes the chat panel
2. Panel slides out and page reflows to side-by-side layout (diagrams left ~60%, chat right ~40%)
3. Chat header has two dropdowns: provider selector and model selector
4. Provider dropdown populated from `GET /api/providers` (existing endpoint)
5. Model dropdown populated from `GET /api/providers/{name}/models` (existing endpoint) when provider changes
6. User clicks a rendered diagram to "attach" it - the diagram's .mmd content gets injected into the next message as context
7. Attached diagram shows as a chip/tag in the message input area (removable)
8. User types a message and sends it. Server routes the prompt to the selected provider via protocol-native streaming
9. Response streams back via SSE (token events) and renders in the chat as markdown
10. Chat messages display in a scrollable thread (user messages right-aligned, AI left-aligned)
11. Chat sessions persist to disk as JSON files and can be listed, created, renamed, and deleted
12. Multiple sessions per feature, with automatic naming from first user message

### Non-Functional

- **Performance:** First token of AI response visible within 2s of sending
- **Platform:** Web only, modern browsers
- **Streaming:** Responses stream token-by-token via SSE from a merged event stream (chat tokens + diagram change notifications)

## Architecture

### Protocol-Native Streaming (ProviderRouter)

The chat does NOT invoke CLI subprocesses. Instead, it uses protocol-native connections:

- **Claude**: Vista connects to the Companion server's WebSocket API. The Companion manages a Claude Code CLI process. Vista creates a session via HTTP, then streams messages over WebSocket (`ClaudeWSClient`).
- **OpenCode**: Vista connects directly to OpenCode's HTTP API. Sessions are created via REST, and messages stream via SSE (`OpenCodeClient`).

The `ProviderRouter` singleton manages backend session lifecycle and routes `send_message()` calls to the correct client, yielding `{type: "token"|"done"|"error", ...}` events.

### History Handling

History is NOT re-sent with each message. Both Claude (via Companion) and OpenCode maintain native conversation context within their backend sessions. The `ContextAssembler.build_full_prompt()` method accepts a `history` parameter for backwards compatibility but ignores it. Only the system prompt, diagram context, and current user message are sent.

### Session Persistence

Sessions are fully persisted as JSON files in `server/data/sessions/{project_id}/`. The `ChatSessionService` provides CRUD operations:
- `create()` - New session with feature, provider, model
- `list_sessions()` - List sessions optionally filtered by feature
- `get()` / `delete()` - Standard CRUD
- `add_message()` - Append a message and auto-save
- `update_name()` - Rename a session

Each session file contains the full message history, provider/model config, feature association, and backend session ID mapping.

### Context Assembly

`ContextAssembler` builds prompts with:
1. System prompt scoping the AI to arch/ and specs/ directories
2. Diagram context (attached .mmd files + selected elements)
3. Current user message

The system prompt grants read access to the entire project for context but restricts edits to .mmd files in the arch directory only.

## User Workflows

### Workflow 1: Review a Diagram with AI

**Actor:** Developer
**Trigger:** User wants feedback on an architecture diagram

**Steps:**
1. User views rendered diagrams on the architecture page
2. User clicks the chat button (bottom-right)
3. Chat panel slides out, diagrams shift to left column
4. User selects provider (e.g., "Claude") from dropdown
5. Model dropdown populates (e.g., "opus", "sonnet", "haiku")
6. User selects model (e.g., "sonnet")
7. User clicks a sequence diagram - it attaches as context chip
8. User types "Does this sequence handle the error case where the API returns a 429?"
9. Message + diagram context sent to server via POST
10. Server routes prompt to provider via ProviderRouter (WebSocket for Claude, SSE for OpenCode)
11. AI response streams token-by-token via SSE to the browser
12. User continues conversation with follow-up questions (provider maintains conversation context)

**Error Cases:**
- Provider not available: Returns 503 with "Provider '{name}' is not available"
- Backend session creation fails: Returns 502 with error detail
- SSE connection drops: Client can reconnect to the SSE stream endpoint

### Workflow 2: Multi-Diagram Context

**Actor:** Developer
**Trigger:** User wants AI to compare or relate multiple diagrams

**Steps:**
1. Chat is already open
2. User clicks first diagram (e.g., system-arch.mmd) - appears as chip
3. User clicks second diagram (e.g., data-model.mmd) - appears as second chip
4. User types "Are the entities in the data model consistent with the services in the architecture?"
5. Both diagram contents sent as context with the message

### Workflow 3: Session Management

**Actor:** Developer
**Trigger:** User wants to organize chat conversations

**Steps:**
1. User creates a new session for a feature
2. Session auto-names from the first user message
3. User can rename sessions via the UI
4. User can switch between sessions, each preserving full history
5. User can delete sessions (backend session is cleaned up)

## Data Model

**Entities:**
- ChatSession: `{ id, project_id, feature_name, name, provider, model, messages: ChatMessage[], backend_session_id, created_at, updated_at }`
- ChatMessage: `{ role: "user"|"assistant", content: string, timestamp: ISO-8601 }`
- ProviderRouter session map: `{ session_id -> { provider, backend_session_id, model, cwd } }`

**Relationships:**
- ChatSession contains N ChatMessages
- ChatSession maps 1:1 to a ProviderRouter backend session (lazy-created on first message)
- ChatSession stored as JSON file in `server/data/sessions/{project_id}/{session_id}.json`

## Integration Points

**Dependencies:**
- Provider service: `GET /api/providers`, `GET /api/providers/{name}/models` (existing)
- Service lifecycle: Checks if Companion/OpenCode backends are available
- Companion server: WebSocket API for Claude sessions
- OpenCode server: HTTP REST + SSE API for OpenCode sessions
- Rendering pipeline: Clickable diagrams for context injection
- Arch directory: Diagram file contents for context
- Diagram watcher: File system watcher for live diagram change notifications on SSE stream

**Provides to:**
- None (terminal consumer)

## Technical Considerations

### Server-side Routes (`chat_sessions.py`)

- `GET /api/projects/{id}/chat/sessions` - List sessions (filterable by feature)
- `POST /api/projects/{id}/chat/sessions` - Create session
- `GET /api/projects/{id}/chat/sessions/{sid}` - Get session with messages
- `DELETE /api/projects/{id}/chat/sessions/{sid}` - Delete session + cleanup backend
- `PATCH /api/projects/{id}/chat/sessions/{sid}` - Rename session
- `POST /api/projects/{id}/chat/sessions/{sid}/messages` - Send message (triggers async streaming)
- `POST /api/projects/{id}/chat/sessions/{sid}/cancel` - Cancel/cleanup backend session
- `GET /api/projects/{id}/chat/sessions/{sid}/stream` - SSE endpoint (chat tokens + diagram changes)

### Key Services

- `ProviderRouter` (`provider_router.py`): Routes messages to Claude WebSocket or OpenCode SSE backends
- `ChatSessionService` (`chat_session_service.py`): CRUD for persistent sessions on disk
- `ContextAssembler` (`context_assembler.py`): Builds prompts with system instructions + diagram context
- `DiagramWatcher` (`diagram_watcher.py`): Watches arch/ for file changes, pushes events to SSE stream
- `ChatService` (`chat_service.py`): **Deprecated placeholder** - retained only for backwards compatibility

### Client-side

- Chat panel component with state management (open/closed, provider, model, messages, attachments)
- EventSource for SSE streaming (chat tokens + diagram change events)
- Markdown rendering for AI responses

### Patterns

- Protocol-native streaming: POST triggers async background task, SSE delivers events
- Merged event stream: Chat tokens and diagram file changes delivered through single SSE endpoint
- Lazy backend session: Backend session created on first message, not on session creation
- Session pub/sub: Multiple SSE subscribers per session via in-memory queue broadcast

## Acceptance Criteria

- [x] Chat button visible on architecture page (bottom-right)
- [x] Panel slides out to side-by-side layout on click
- [x] Provider dropdown loads from existing API
- [x] Model dropdown loads when provider selected
- [x] Clicking a diagram attaches it as context chip
- [x] Multiple diagrams can be attached
- [x] Sending a message routes to selected provider via protocol-native streaming
- [x] Response streams back token-by-token via SSE
- [x] Chat thread displays message history for the session
- [x] Connection errors shown as system messages in chat
- [x] Chat sessions persist to JSON files on disk
- [x] Sessions can be listed, created, renamed, and deleted
- [x] History is NOT re-sent; providers maintain native conversation context
- [x] ContextAssembler builds prompts with system prompt + diagram context + user message

## Resolved Questions

- Chat sessions persist as JSON files in `server/data/sessions/{project_id}/` (not session-only).
- AI responses that suggest diagram edits do not yet have an "Apply" button (deferred to future work).
- ChatService is a deprecated placeholder; ProviderRouter handles all chat routing.
