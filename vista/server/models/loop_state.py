"""Per-project loop state tracking."""
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


@dataclass
class LoopInstance:
    project_id: str = ""
    feature_name: str = ""
    mode: str = ""                     # "plan" or "build"
    model: str = ""                    # "opus", "sonnet", "haiku", or provider-specific
    provider: str = ""                 # "claude", "opencode"
    provider_display_name: str = ""    # "Claude Code", "OpenCode"
    status: str = "idle"               # "idle", "starting", "running", "stopped", "completed", "failed"
    pid: Optional[int] = None          # OS process ID
    iteration: int = 0                 # Current iteration number
    max_iterations: int = 0            # 0 = unlimited
    start_time: Optional[str] = None   # ISO datetime
    end_time: Optional[str] = None     # ISO datetime
    error: Optional[str] = None
    output_lines: deque = field(default_factory=lambda: deque(maxlen=2000))
    last_ralph_control: Optional[dict] = None   # {"status": "done", "files_changed": "3"}
    progress_summary: Optional[str] = None      # Last contents of progress.txt
    recent_actions: deque = field(default_factory=lambda: deque(maxlen=20))

    def to_dict(self) -> dict:
        """Serialize for JSON/API response."""
        return {
            "project_id": self.project_id,
            "feature_name": self.feature_name,
            "mode": self.mode,
            "model": self.model,
            "provider": self.provider,
            "provider_display_name": self.provider_display_name,
            "status": self.status,
            "pid": self.pid,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
            "output_line_count": len(self.output_lines),
            "last_ralph_control": self.last_ralph_control,
            "progress_summary": self.progress_summary,
            "recent_actions": list(self.recent_actions),
        }
