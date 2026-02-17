# OpenCode Server API Reference

## Overview

OpenCode provides a headless HTTP server mode (`opencode serve`) that exposes a REST API with SSE streaming for real-time events. This is the integration point for Vista's OpenCode provider.

## Starting the Server

```bash
opencode serve [--port <number>] [--hostname <string>] [--cors <origin>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | 4096 | HTTP port |
| `--hostname` | 127.0.0.1 | Bind address |
| `--cors` | none | CORS origin (repeatable) |

**Authentication** (optional):
```bash
OPENCODE_SERVER_PASSWORD=secret opencode serve
OPENCODE_SERVER_USERNAME=custom-user  # default: "opencode"
```
When set, all endpoints require HTTP Basic Auth: `Authorization: Basic <base64(user:pass)>`

## Core Endpoints

### Health
```
GET /global/health → {status, version}
```

### Sessions

**Create session:**
```
POST /session
Content-Type: application/json

{
  "title": "Architecture Chat - docker-sandbox",
  "permission": ["read", "write"]
}
→ {id, title, ...}
```

**List sessions:**
```
GET /session → [{id, title, ...}]
```

**Get session:**
```
GET /session/:id → {id, title, messages, ...}
```

**Delete session:**
```
DELETE /session/:id
```

### Messages

**Send message (blocking):**
```
POST /session/:id/message
Content-Type: application/json

{
  "parts": [
    {"type": "text", "text": "Your message here"}
  ],
  "model": {
    "providerID": "anthropic",
    "modelID": "claude-3-5-sonnet-20241022"
  }
}
→ {info, parts}
```

**Send message (async, non-blocking):**
```
POST /session/:id/prompt_async
Content-Type: application/json

{
  "parts": [{"type": "text", "text": "..."}],
  "model": {"providerID": "anthropic", "modelID": "..."}
}
```

**Abort running session:**
```
POST /session/:id/abort
```

**List messages:**
```
GET /session/:id/message → [{id, role, parts, ...}]
```

### Streaming (SSE)

**Global event stream:**
```
GET /global/event
Accept: text/event-stream
```

**Session-scoped event stream:**
```
GET /event
Accept: text/event-stream
```

**Event format:**
```
event: message.part.updated
data: {"type":"message.part.updated","properties":{...}}
```

### Event Types

| Event | Description |
|-------|-------------|
| `server.connected` | Sent immediately on SSE connect |
| `session.created` | New session created |
| `session.updated` | Session metadata changed |
| `session.deleted` | Session removed |
| `session.idle` | Session finished processing (response complete) |
| `session.error` | Session encountered error |
| `message.updated` | Message metadata changed |
| `message.part.updated` | **Streaming text delta** — incremental token updates |
| `message.part.removed` | Message part deleted |
| `message.deleted` | Full message removed |
| `permission.asked` | Tool permission request |
| `permission.response` | Tool permission response |
| `file.changed` | File modified on disk |
| `file.watcher.updated` | File watcher state change |
| `lsp.diagnostics` | LSP diagnostic update |

**Key for streaming:** `message.part.updated` events contain incremental text deltas that should be appended to the current message to display real-time token streaming.

### Configuration

**Get config:**
```
GET /config → {providers, models, ...}
```

**Get available providers/models:**
```
GET /config/providers → [{id, models: [...]}]
```

### Model Selection

Models are specified per-message, not per-session:
```json
{
  "model": {
    "providerID": "anthropic",
    "modelID": "claude-3-5-sonnet-20241022"
  }
}
```

Common provider IDs: `anthropic`, `openai`, `google`, `ollama`

**Note:** There are known issues where per-message model selection may be ignored in favor of server defaults (GitHub issue #3517). Test thoroughly.

## Python SDK

```bash
pip install --pre opencode-ai
```

### Synchronous Usage
```python
from opencode_ai import Opencode

client = Opencode(base_url="http://localhost:4096")

# List sessions
sessions = client.session.list()

# Create session
session = client.session.create(title="Arch Chat", permission=["read", "write"])

# Send message
response = client.session.prompt(
    id=session.id,
    parts=[{"type": "text", "text": "Hello"}],
    model={"providerID": "anthropic", "modelID": "claude-3-5-sonnet-20241022"}
)

# Stream events
stream = client.event.list()
for events in stream:
    for event in events:
        if event.type == "message.part.updated":
            print(event.properties.text, end="", flush=True)
```

### Async Usage
```python
from opencode_ai import AsyncOpencode

client = AsyncOpencode(base_url="http://localhost:4096")
sessions = await client.session.list()
```

## Integration Notes for Vista

### Session Mapping
Vista maintains a mapping between its own `ChatSession.id` and OpenCode's session IDs. When creating a Vista chat session with provider "opencode", Vista also creates an OpenCode session and stores the mapping.

### Context Assembly
Vista assembles the full prompt (system instructions + diagram context + history + user message) into a single text part before sending to OpenCode. OpenCode does not know about Vista's context structure.

### Streaming Bridge
Vista subscribes to OpenCode's SSE `GET /event` endpoint and translates `message.part.updated` events into Vista's own SSE format (`event: token`) for the browser frontend.

### Health Checking
Use `GET /global/health` for service health monitoring. Expected response includes server status and version info.

### Lifecycle Management
Vista starts OpenCode via:
```python
proc = await asyncio.create_subprocess_exec(
    "opencode", "serve", "--port", str(port),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```
Monitor process health with periodic `GET /global/health` checks.
