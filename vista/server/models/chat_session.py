"""Data models for persistent chat sessions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class ChatMessage:
    """A single message in a chat session."""

    role: str  # "user" | "assistant"
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> "ChatMessage":
        return cls(role=d["role"], content=d["content"], timestamp=d.get("timestamp", ""))


@dataclass
class ChatSession:
    """A persistent chat session tied to a project feature."""

    id: str
    project_id: str
    feature_name: str
    name: str
    provider: str
    model: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    team_name: Optional[str] = None
    backend_session_id: Optional[str] = None

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "feature_name": self.feature_name,
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "team_name": self.team_name,
            "backend_session_id": self.backend_session_id,
        }

    def to_summary_dict(self) -> dict:
        """Lightweight dict without message bodies for session listing."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "feature_name": self.feature_name,
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "team_name": self.team_name,
            "backend_session_id": self.backend_session_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChatSession":
        messages = [ChatMessage.from_dict(m) for m in d.get("messages", [])]
        return cls(
            id=d["id"],
            project_id=d["project_id"],
            feature_name=d["feature_name"],
            name=d["name"],
            provider=d["provider"],
            model=d["model"],
            messages=messages,
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            team_name=d.get("team_name"),
            backend_session_id=d.get("backend_session_id"),
        )

    @staticmethod
    def generate_id() -> str:
        return uuid.uuid4().hex[:8]

    @staticmethod
    def auto_name(first_message: str) -> str:
        """Generate a session name from the first user message."""
        name = first_message.strip().replace("\n", " ")
        if len(name) > 50:
            name = name[:47] + "..."
        return name or "New Chat"
