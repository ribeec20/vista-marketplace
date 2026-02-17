---
name: vista
description: Open the Vista dashboard and register a project. Use when starting the planning UI or opening the web dashboard.
---

# Vista — Dashboard

The server is launched automatically via MCP on session start and `/vista` invocation.

## Invocation

```
/vista [project-path]
```

## Workflow

### Step 0: Discover Dashboard URL

Call the `ralph_providers` MCP tool. The response contains `dashboard_url` — use this as the server URL for all subsequent requests. Do NOT hardcode port 3456; the port is dynamically assigned.

### Step 1: Register Project

Determine the project path:
- If `$ARGUMENTS` contains a path, use that
- Otherwise use the current working directory

Check if the project is already registered:

```bash
curl -s <dashboard_url>/api/projects
```

If the project path is NOT already in the response list, register it:

```bash
curl -s -X POST <dashboard_url>/api/projects -H "Content-Type: application/json" -d '{"path": "<project-path>"}'
```

If it is already registered, skip registration.

If the server is unreachable, tell the user the MCP server may not be running and to check their `.mcp.json` configuration.

### Step 2: Report Status

Report to the user:
- Server URL: the `dashboard_url` from Step 0
- Whether the project was already registered or just registered
- Available sub-skills:
  - `/vista:plan <feature-name>` — Plan a feature through interactive questioning, producing domain requirements and architecture diagrams
  - `/vista:tdd <feature-name>` — Generate TDD diagrams for heavy-logic components
  - `/vista:specs <feature-name>` — Generate topic specifications from planning artifacts
  - `/vista:add <feature-name>` — Expand an existing feature with new requirements
  - `/vista:legacy <feature-name>` — Reverse-engineer an existing codebase into Vista planning artifacts
