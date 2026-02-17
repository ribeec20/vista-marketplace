"""Summarizer service for generating AI summaries of ralph job artifacts."""

import json
import subprocess
from pathlib import Path
from typing import Any

from server.config import get_summarizer_config
from server.services.provider_service import get_provider_by_name


def build_summarizer_prompt(job_dir: Path, job_meta: dict) -> str:
    """Build summarizer prompt from job artifacts.

    Args:
        job_dir: Path to the job directory (.vista/ralph/{slug}/)
        job_meta: Job metadata dict from job.json

    Returns:
        Markdown prompt string requesting structured JSON output
    """
    # Read task description
    task_md = job_dir / "task.md"
    task_content = task_md.read_text(encoding="utf-8") if task_md.exists() else "No task description available."

    # Read progress (last 100 lines)
    progress_file = job_dir / "progress.txt"
    progress_lines = []
    if progress_file.exists():
        all_lines = progress_file.read_text(encoding="utf-8").splitlines()
        progress_lines = all_lines[-100:]
    progress_content = "\n".join(progress_lines) if progress_lines else "No progress yet."

    # Read implementation plan (first 500 lines)
    plan_file = job_dir / "IMPLEMENTATION_PLAN.md"
    plan_lines = []
    if plan_file.exists():
        all_lines = plan_file.read_text(encoding="utf-8").splitlines()
        plan_lines = all_lines[:500]
    plan_content = "\n".join(plan_lines) if plan_lines else "No implementation plan yet."

    # Get git log from project root (infer from job_dir structure)
    project_root = job_dir.parent.parent.parent  # .vista/ralph/{slug}/ -> project root
    git_log = ""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_log = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        git_log = "Git log unavailable."

    # Build prompt
    prompt = f"""# Ralph Loop Job Summary

You are analyzing a ralph loop job and must provide a concise, structured summary.

## Job Metadata
- **Slug**: {job_meta.get('slug', 'unknown')}
- **Mode**: {job_meta.get('mode', 'unknown')}
- **Status**: {job_meta.get('status', 'unknown')}
- **Provider**: {job_meta.get('provider', 'unknown')}
- **Model**: {job_meta.get('model', 'unknown')}
- **Iterations**: {job_meta.get('current_iteration', 0)}/{job_meta.get('iterations', 0)}

## Task Description
```
{task_content}
```

## Recent Progress (last 100 lines)
```
{progress_content}
```

## Implementation Plan (first 500 lines)
```
{plan_content}
```

## Recent Git Commits (last 20)
```
{git_log}
```

---

**Your task**: Analyze the above artifacts and provide a structured JSON summary with the following schema:

```json
{{
  "status_summary": "One sentence describing the current state of the job",
  "completed_work": ["List of accomplishments", "..."],
  "in_progress": ["What is currently being worked on", "..."],
  "issues": ["Problems or blockers encountered", "..."],
  "recommendations": ["Suggested next steps", "..."],
  "key_files_changed": ["file/path.py", "..."]
}}
```

**IMPORTANT**:
- Return ONLY valid JSON (no markdown code fences, no extra text)
- If a field has no items, use an empty array []
- Be concise but specific (include file names, function names, error messages where relevant)
- Extract information from progress.txt and git log to identify changed files
"""

    return prompt


class SummarizerService:
    """Service for running summarizer agent on ralph job artifacts."""

    def run_summarizer(self, project_root: Path, job_id: str) -> dict[str, Any]:
        """Run summarizer agent and return structured summary.

        Args:
            project_root: Project root directory
            job_id: UUID of the job to summarize

        Returns:
            Dict with summary data (status_summary, completed_work, in_progress, issues, recommendations, key_files_changed)

        Raises:
            ValueError: If job not found or summarizer CLI not available
            subprocess.TimeoutExpired: If summarizer exceeds 55-second timeout
        """
        # Find job directory
        ralph_dir = project_root / ".vista" / "ralph"
        job_dir = None

        if ralph_dir.exists():
            for slug_dir in ralph_dir.iterdir():
                if not slug_dir.is_dir():
                    continue
                job_json = slug_dir / "job.json"
                if job_json.exists():
                    try:
                        job_meta = json.loads(job_json.read_text(encoding="utf-8"))
                        if job_meta.get("job_id") == job_id:
                            job_dir = slug_dir
                            break
                    except (json.JSONDecodeError, OSError):
                        continue

        if not job_dir:
            raise ValueError(f"Job not found: {job_id}")

        # Load job metadata
        job_json = job_dir / "job.json"
        job_meta = json.loads(job_json.read_text(encoding="utf-8"))

        # Get summarizer config
        config = get_summarizer_config()
        provider_name = config.get("provider", "claude")
        model = config.get("model", "haiku")

        # Get provider and command
        provider = get_provider_by_name(provider_name)
        if not provider:
            raise ValueError(f"Summarizer provider not found: {provider_name}")

        cmd = provider.get_summarizer_command(model)
        if not cmd:
            raise ValueError(f"Summarizer CLI not available for provider: {provider_name}")

        # Build prompt
        prompt = build_summarizer_prompt(job_dir, job_meta)

        # Run summarizer subprocess
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_root,
            )

            stdout, stderr = proc.communicate(input=prompt, timeout=55)

            if proc.returncode != 0:
                raise ValueError(f"Summarizer exited with code {proc.returncode}: {stderr}")

            # Try to parse JSON output
            try:
                summary = json.loads(stdout.strip())
                # Validate required fields
                required = ["status_summary", "completed_work", "in_progress", "issues", "recommendations", "key_files_changed"]
                for field in required:
                    if field not in summary:
                        summary[field] = [] if field != "status_summary" else "Summary unavailable"
                return summary
            except json.JSONDecodeError:
                # Fallback: return raw text in a structured format
                return {
                    "status_summary": "Summary generated but not in expected JSON format",
                    "completed_work": [],
                    "in_progress": [],
                    "issues": ["Failed to parse JSON output from summarizer"],
                    "recommendations": [],
                    "key_files_changed": [],
                    "raw_output": stdout.strip()[:1000],  # First 1000 chars
                }

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise ValueError("Summarizer timed out after 55 seconds")


# Singleton instance
summarizer_service = SummarizerService()
