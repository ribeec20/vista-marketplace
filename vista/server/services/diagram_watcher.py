"""Diagram file watcher using watchdog filesystem events.

Uses watchdog's Observer for instant filesystem event detection on Windows
(ReadDirectoryChangesW) with 100ms debounce to coalesce rapid file saves.
Broadcasts change events via async queues (same pub-sub pattern as loop_service).

Auto-updates the _arch.json manifest when diagrams are added or removed.
"""

import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger(__name__)


class _DiagramEventHandler(FileSystemEventHandler):
    """Handles filesystem events for diagram and markdown files."""

    WATCH_EXTENSIONS = {".mmd", ".drawio", ".puml", ".d2", ".dot", ".md"}

    def __init__(self, key: str, arch_dir: Path, watcher: "DiagramWatcher"):
        super().__init__()
        self.key = key
        self.arch_dir = arch_dir
        self.watcher = watcher
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[str, str]] = {}  # path -> (event_type, filename)
        self._timer: Optional[threading.Timer] = None

    def _is_diagram(self, path: str) -> bool:
        return Path(path).suffix in self.WATCH_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_diagram(event.src_path):
            self._debounced_notify(event.src_path, "diagram_added")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_diagram(event.src_path):
            self._debounced_notify(event.src_path, "diagram_changed")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_diagram(event.src_path):
            self._debounced_notify(event.src_path, "diagram_removed")

    def _debounced_notify(self, path: str, event_type: str, delay: float = 0.1):
        """Debounce rapid events (100ms) to coalesce file saves."""
        filename = Path(path).name
        with self._lock:
            self._pending[path] = (event_type, filename)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(delay, self._flush)
            self._timer.start()

    def _flush(self) -> None:
        """Flush all pending events."""
        with self._lock:
            pending = dict(self._pending)
            self._pending.clear()
            self._timer = None

        manifest_changed = False
        for path, (event_type, filename) in pending.items():
            if event_type == "diagram_removed":
                data = {"file": filename}
                manifest_changed = True
            else:
                content = _read_file(Path(path))
                data = {"file": filename, "content": content}
                if event_type == "diagram_added":
                    manifest_changed = True

            self.watcher._schedule_broadcast(
                self.key, {"event": event_type, "data": data}
            )

        if manifest_changed:
            self.watcher._schedule_manifest_update(self.key, self.arch_dir)

    def cancel_timer(self) -> None:
        """Cancel any pending debounce timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _detect_diagram_type(path: Path) -> str:
    """Detect Mermaid diagram type from file content."""
    try:
        content = path.read_text(encoding="utf-8").strip()
        first_line = content.split("\n")[0].strip().lower() if content else ""
        for dtype in (
            "graph", "flowchart", "sequencediagram", "sequence",
            "classdiagram", "class", "statediagram", "state",
            "erdiagram", "er", "gantt", "pie", "gitgraph",
            "c4context", "c4container", "c4component", "c4deployment",
            "mindmap", "timeline",
        ):
            if dtype in first_line.replace(" ", "").replace("-", ""):
                return dtype
        return "flowchart"
    except Exception:
        return "flowchart"


EXT_TO_TYPE = {
    ".mmd": "mermaid",
    ".drawio": "drawio",
    ".puml": "plantuml",
    ".d2": "d2",
    ".dot": "graphviz",
    ".md": "markdown",
}


def _detect_file_type(path: Path) -> str:
    """Detect diagram type from file extension."""
    return EXT_TO_TYPE.get(path.suffix.lower(), "mermaid")


class DiagramWatcher:
    """Watches arch/ directories for file changes using watchdog and notifies subscribers."""

    WATCH_EXTENSIONS = {".mmd", ".drawio", ".puml", ".d2", ".dot", ".md"}

    def __init__(self):
        # Key: "{project_id}:{feature_name}" -> list of subscriber queues
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        # Key: same -> Observer instance
        self._observers: dict[str, Observer] = {}
        # Key: same -> event handler
        self._handlers: dict[str, _DiagramEventHandler] = {}
        # Key: same -> arch dir Path
        self._watch_dirs: dict[str, Path] = {}
        # Event loop reference for cross-thread scheduling
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @staticmethod
    def _key(project_id: str, feature_name: str) -> str:
        return f"{project_id}:{feature_name}"

    def subscribe(
        self, project_id: str, feature_name: str, arch_dir: Path
    ) -> asyncio.Queue:
        """Register a subscriber for diagram changes. Starts watching if not already."""
        key = self._key(project_id, feature_name)

        # Capture the event loop for cross-thread scheduling
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if key not in self._subscribers:
            self._subscribers[key] = []
            self._watch_dirs[key] = arch_dir
            self._start_observer(key, arch_dir)

        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers[key].append(queue)
        return queue

    def unsubscribe(
        self, project_id: str, feature_name: str, queue: asyncio.Queue
    ) -> None:
        key = self._key(project_id, feature_name)
        if key in self._subscribers:
            self._subscribers[key] = [
                q for q in self._subscribers[key] if q is not queue
            ]
            if not self._subscribers[key]:
                del self._subscribers[key]
                self._watch_dirs.pop(key, None)
                self._stop_observer(key)

    def _start_observer(self, key: str, arch_dir: Path) -> None:
        """Start a watchdog Observer for the given arch directory."""
        if not arch_dir.is_dir():
            log.warning("Diagram watch dir does not exist: %s", arch_dir)
            return

        handler = _DiagramEventHandler(key, arch_dir, self)
        observer = Observer()
        observer.schedule(handler, str(arch_dir), recursive=False)
        observer.daemon = True
        observer.start()

        self._observers[key] = observer
        self._handlers[key] = handler
        log.info("Started watching diagrams: %s", arch_dir)

    def _stop_observer(self, key: str) -> None:
        """Stop the watchdog Observer for the given key."""
        handler = self._handlers.pop(key, None)
        if handler:
            handler.cancel_timer()

        observer = self._observers.pop(key, None)
        if observer:
            observer.stop()
            observer.join(timeout=2)
            log.info("Stopped watching diagrams for key: %s", key)

    def _schedule_broadcast(self, key: str, message: dict) -> None:
        """Thread-safe: schedule a broadcast onto the asyncio event loop."""
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                asyncio.ensure_future,
                self._broadcast(key, message),
            )

    def _schedule_manifest_update(self, key: str, arch_dir: Path) -> None:
        """Thread-safe: schedule a manifest update onto the asyncio event loop."""
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                self._update_manifest_sync, arch_dir,
            )

    async def _broadcast(self, key: str, message: dict) -> None:
        if key not in self._subscribers:
            return
        dead_queues = []
        for queue in self._subscribers[key]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for q in dead_queues:
            if key in self._subscribers:
                self._subscribers[key].remove(q)

    @staticmethod
    def _update_manifest_sync(arch_dir: Path) -> None:
        """Scan arch dir for diagram files and regenerate _arch.json manifest."""
        if not arch_dir.is_dir():
            return
        entries = []
        for f in sorted(arch_dir.iterdir()):
            if f.is_file() and f.suffix in EXT_TO_TYPE and not f.name.startswith("_"):
                file_type = _detect_file_type(f)
                diagram_type = _detect_diagram_type(f) if file_type == "mermaid" else "custom"
                name = f.stem.replace("-", " ").replace("_", " ").title()
                entries.append({
                    "name": name,
                    "file": f.name,
                    "type": file_type,
                    "diagramType": diagram_type,
                    "description": f"Auto-detected {file_type} diagram",
                })
        manifest_path = arch_dir / "_arch.json"
        feature_name = arch_dir.parent.name
        manifest = {"feature": feature_name, "diagrams": entries}
        try:
            manifest_path.write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
        except OSError as e:
            log.warning("Failed to update manifest: %s", e)

    async def stop(self) -> None:
        """Stop all observers and clear all state."""
        for key in list(self._observers.keys()):
            self._stop_observer(key)
        self._subscribers.clear()
        self._watch_dirs.clear()


# Singleton instance
diagram_watcher = DiagramWatcher()
