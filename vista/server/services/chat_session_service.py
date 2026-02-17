"""CRUD service for persistent chat sessions.

Sessions are stored as JSON files under server/data/sessions/{project_id}/.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from server import config
from server.models.chat_session import ChatMessage, ChatSession

SESSIONS_DIR = config.DATA_DIR / "sessions"


class ChatSessionService:
    """Manages chat session persistence on disk."""

    @staticmethod
    def _session_dir(project_id: str) -> Path:
        return SESSIONS_DIR / project_id

    @staticmethod
    def _session_file(project_id: str, session_id: str) -> Path:
        return SESSIONS_DIR / project_id / f"{session_id}.json"

    @classmethod
    def create(
        cls,
        project_id: str,
        feature_name: str,
        provider: str,
        model: str,
        name: str = "",
    ) -> ChatSession:
        session = ChatSession(
            id=ChatSession.generate_id(),
            project_id=project_id,
            feature_name=feature_name,
            name=name or "New Chat",
            provider=provider,
            model=model,
        )
        cls._save(session)
        return session

    @classmethod
    def list_sessions(
        cls, project_id: str, feature_name: Optional[str] = None
    ) -> list[dict]:
        """Return summary dicts for sessions, optionally filtered by feature."""
        d = cls._session_dir(project_id)
        if not d.exists():
            return []
        sessions = []
        for f in sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                session = cls._load(f)
                if feature_name and session.feature_name != feature_name:
                    continue
                sessions.append(session.to_summary_dict())
            except Exception:
                continue
        return sessions

    @classmethod
    def get(cls, project_id: str, session_id: str) -> Optional[ChatSession]:
        f = cls._session_file(project_id, session_id)
        if not f.exists():
            return None
        return cls._load(f)

    @classmethod
    def delete(cls, project_id: str, session_id: str) -> bool:
        f = cls._session_file(project_id, session_id)
        if not f.exists():
            return False
        f.unlink()
        return True

    @classmethod
    def add_message(
        cls, project_id: str, session_id: str, role: str, content: str
    ) -> Optional[ChatSession]:
        session = cls.get(project_id, session_id)
        if session is None:
            return None
        msg = ChatMessage(role=role, content=content)
        session.messages.append(msg)
        session.updated_at = datetime.now(timezone.utc).isoformat()
        # Auto-name from first user message if still default
        if session.name == "New Chat" and role == "user" and len(session.messages) == 1:
            session.name = ChatSession.auto_name(content)
        cls._save(session)
        return session

    @classmethod
    def update_name(cls, project_id: str, session_id: str, name: str) -> Optional[ChatSession]:
        session = cls.get(project_id, session_id)
        if session is None:
            return None
        session.name = name
        session.updated_at = datetime.now(timezone.utc).isoformat()
        cls._save(session)
        return session

    @classmethod
    def save(cls, session: ChatSession) -> None:
        """Public save — persist a session to disk."""
        cls._save(session)

    @classmethod
    def _save(cls, session: ChatSession) -> None:
        d = cls._session_dir(session.project_id)
        d.mkdir(parents=True, exist_ok=True)
        f = cls._session_file(session.project_id, session.id)
        f.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def _load(path: Path) -> ChatSession:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ChatSession.from_dict(data)
