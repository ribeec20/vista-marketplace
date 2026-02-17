# Spec: Dashboard Integration

## Problem Statement

Ralph MCP jobs run as background subprocesses initiated by tool calls. Users need visual monitoring beyond what the LLM can report via text. The Vista dashboard should show ralph jobs alongside other project information, providing real-time status, progress streaming, and access to artifacts.

## Proposed Solution

Add a ralph jobs section to the Vista dashboard with a job list view and job detail view. The backend exposes REST API endpoints that the dashboard frontend calls. The UI integrates with the existing dashboard template structure.

### API Endpoints

Add to `vista/server/routes/` (new file `ralph.py` or extend existing):

```
GET  /api/ralph/jobs                    # List all ralph jobs
GET  /api/ralph/jobs/{job_id}           # Get job detail
GET  /api/ralph/jobs/{job_id}/progress  # Stream progress.txt (SSE or polling)
GET  /api/ralph/jobs/{job_id}/output    # Get output.log contents
GET  /api/ralph/jobs/{job_id}/artifacts # List artifact files in job directory
GET  /api/ralph/jobs/{job_id}/artifacts/{filename} # Read specific artifact
POST /api/ralph/jobs/{job_id}/stop      # Stop a running job (same as MCP ralph_stop)
```

### Job List View

On the project page or a dedicated ralph tab:

```
┌─────────────────────────────────────────────────────────────┐
│  Ralph Jobs                                                  │
├──────────┬────────┬──────────┬───────┬──────────┬───────────┤
│ Slug     │ Mode   │ Provider │ Model │ Status   │ Started   │
├──────────┼────────┼──────────┼───────┼──────────┼───────────┤
│ refactor │ plan   │ claude   │ opus  │ ● running│ 2m ago    │
│ fix-auth │ build  │ claude   │ sonnet│ ✓ done   │ 1h ago    │
│ add-tests│ plan   │ opencode │ gpt-4 │ ✗ failed │ 3h ago    │
└──────────┴────────┴──────────┴───────┴──────────┴───────────┘
```

- Status indicators: ● running (blue), ✓ completed (green), ✗ failed (red), ⬚ stopped (gray)
- Click a row to open job detail
- Auto-refresh every 5 seconds for running jobs

### Job Detail View

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Jobs                                              │
│                                                              │
│  refactor-api-handlers                          [Stop]       │
│  Mode: plan  │  Provider: claude  │  Model: opus             │
│  Status: ● Running (iteration 2/3)  │  Started: 2m ago      │
│                                                              │
│  ┌─── Progress ─────────────────────────────────────────┐   │
│  │ Phase: planning, iteration 2                          │   │
│  │ Analyzed src/api/handlers.py - found 12 endpoints     │   │
│  │ Identified 3 middleware integration points            │   │
│  │ Updating IMPLEMENTATION_PLAN.md...                    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  Artifacts:                                                  │
│  📄 task.md                                                  │
│  📄 IMPLEMENTATION_PLAN.md                                   │
│  📄 progress.txt                                             │
│  📄 output.log                                               │
└─────────────────────────────────────────────────────────────┘
```

- Progress section auto-scrolls (polls progress.txt)
- Artifacts are clickable to view contents
- Stop button visible only for running jobs

### Frontend Integration

Integrate with existing dashboard patterns:
- Use the same base template (`_base.html`)
- Same CSS framework and styling (`style.css`)
- Same JavaScript patterns (`app.js`)
- Add ralph-specific routes/views or integrate into existing project view

### Backend Integration

The `RalphService` from [job-management](job-management.md) is shared between MCP tools and dashboard API endpoints. The dashboard routes call the same service methods as the MCP tools.

## Data Requirements

- Job list: read all `job.json` files from `.vista/ralph/*/`
- Progress streaming: read and tail `progress.txt`
- Output log: read `output.log`
- Artifacts: list and read files from job directory

## UI/UX Considerations

- Dashboard is supplementary - the primary interface is the LLM conversation
- Progress should auto-update without manual refresh
- Job detail should be accessible via direct URL for bookmarking
- Responsive layout (works on various screen sizes)
- No authentication required (localhost only)

## Edge Cases

- **No jobs exist**: Show empty state with message ("No ralph jobs yet")
- **Job directory deleted**: Handle missing files gracefully
- **Very large output.log**: Paginate or show last N lines with "show more"
- **Progress.txt mid-write**: May read partial line - acceptable for dashboard display
- **MCP server restart**: Dashboard re-reads from disk, maintains correct state

## Dependencies

- `vista/server/app.py` (existing) - FastAPI app, register new routes
- `vista/server/views/` (existing) - HTML templates
- `vista/server/views/static/` (existing) - CSS/JS
- Spec: [job-management](job-management.md) - RalphService for data access

## Testing Strategy

- API endpoint tests for each route (GET/POST, valid/invalid job_id)
- Frontend: manual testing in browser (no automated UI tests for v1)
- Integration test: create job via MCP tool, verify it appears in dashboard API
