"""Project model - JSON-serializable dataclass for project registry."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""           # Derived from directory name
    path: str = ""           # Absolute path to project root
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
