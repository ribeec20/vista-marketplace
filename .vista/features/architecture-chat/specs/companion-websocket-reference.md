# Companion WebSocket Bridge Reference

## Overview

The Companion project (forked at https://github.com/ribeec20/claude-websocket-companion) provides a WebSocket bridge between Claude Code CLI and web clients. Vista uses only the **backend** (Bun/Hono server) — not the React frontend.

## Architecture

```
Vista FastAPI ←→ (WebSocket JSON) ←→ Companion Server ←→ (WebSocket NDJSON) ←→ Claude CLI
```

The Companion server has two WebSocket endpoints:
- `/ws/cli/{sessionId}` — Claude CLI connects here (NDJSON protocol)
- `/ws/browser/{sessionId}` — Vista's backend connects here (JSON protocol)

## Launching Claude CLI

The Companion spawns Claude Code with:
```bash
claude --sdk-url ws://localhost:{PORT}/ws/cli/{SESSION_ID} \
       --print \
       --output-format stream-json \
       --input-format stream-json \
       --verbose \
       -p ""
```

**Critical flags:**
| Flag | Purpose |
|------|---------|
| `--sdk-url` | Hidden flag activating WebSocket mode |
| `--print` | Headless mode (no terminal UI) |
| `--output-format stream-json` | NDJSON output |
| `--input-format stream-json` | NDJSON input |
| `--verbose` | Enables `stream_event` messages for token streaming |
| `-p ""` | Placeholder prompt (actual prompts via WebSocket) |
| `--model {model}` | Model selection |
| `--resume {id}` | Resume previous CLI session |
| `--dangerously-skip-permissions` | Auto-approve all tool calls |

## WebSocket Protocol

### Browser → Companion (JSON)

**Send user message:**
```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "Your assembled prompt here"}]
  }
}
```

**Respond to permission request:**
```json
{
  "type": "permission_response",
  "request_id": "uuid-from-request",
  "approved": true,
  "original_input": {"command": "..."},
  "modified_input": {"command": "..."}
}
```

**Send control request (interrupt, model change):**
```json
{
  "type": "control_request",
  "request_id": "generated-uuid",
  "request": {
    "subtype": "interrupt"
  }
}
```

### Companion → Browser (JSON)

**Session initialization (on connect/reconnect):**
```json
{
  "type": "session_init",
  "state": {
    "model": "opus",
    "cwd": "/path/to/project",
    "tools": [...]
  }
}
```

**Assistant message (complete):**
```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "Full response text"}
    ]
  }
}
```

**Streaming token:**
```json
{
  "type": "stream_event",
  "event": {
    "type": "content_block_delta",
    "index": 0,
    "delta": {"type": "text_delta", "text": " token"}
  }
}
```

**Result (response complete):**
```json
{
  "type": "result",
  "cost": 0.0123,
  "session_id": "cli-internal-session-id"
}
```

**Permission request (tool approval):**
```json
{
  "type": "permission_request",
  "request_id": "uuid",
  "tool_name": "Bash",
  "input": {"command": "ls -la"}
}
```

**Session state update:**
```json
{
  "type": "session_update",
  "state": {"model": "opus", "cwd": "..."}
}
```

**Message history (on reconnect):**
```json
{
  "type": "message_history",
  "history": [
    {"type": "assistant", "message": {...}},
    {"type": "assistant", "message": {...}}
  ]
}
```

## Key Integration Points for Vista

### Auto-Approve All Tools
Since Vista uses `--dangerously-skip-permissions`, no `permission_request` events should arrive. If they do, auto-respond with `approved: true`.

### Session Lifecycle
1. Vista creates a Companion session (tells it to spawn Claude CLI)
2. CLI connects via WebSocket to `/ws/cli/{id}`
3. Vista connects via WebSocket to `/ws/browser/{id}`
4. Messages flow: Vista → Companion → CLI → Companion → Vista
5. On session end: Vista closes WebSocket, Companion kills CLI process

### Streaming Translation
Vista receives `stream_event` with `content_block_delta` from Companion and translates to its own SSE format:
```
Companion WS: {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"text": "tok"}}}
Vista SSE:    event: token\ndata: {"text": "tok"}\n\n
```

### Reconnection
- Companion buffers up to 1000 messages for replay
- On reconnect, Companion sends `session_init` + `message_history`
- Vista should handle reconnection gracefully if WebSocket drops

### Health Checking
Companion runs on a known port. Health can be checked via HTTP GET to the server root or a dedicated health endpoint. Monitor process PID for crash detection.

## Companion Server API (HTTP)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/new` | POST | Create new session + spawn CLI |
| `/api/sessions/:id` | DELETE | Delete session + kill CLI |
| `/ws/cli/:id` | WS | CLI WebSocket endpoint |
| `/ws/browser/:id` | WS | Browser/client WebSocket endpoint |

## Process Management

Companion's `CliLauncher` manages Claude CLI processes:
- One process per session
- Monitors process exit codes
- Supports `--resume` for session recovery
- Stores session data to `{tmpdir}/vibe-sessions/{id}.json`

Vista's `ServiceLifecycleManager` manages the Companion server process itself:
- Starts Companion on plugin load
- Monitors health
- Auto-restarts on crash with exponential backoff
