"""Tests for the watchdog-based diagram watcher."""

import asyncio
import json
from pathlib import Path

import pytest

from server.services.diagram_watcher import (
    DiagramWatcher,
    EXT_TO_TYPE,
    _detect_diagram_type,
    _detect_file_type,
    _read_file,
)


class TestDetectDiagramType:
    def test_flowchart(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("flowchart LR\n  A --> B", encoding="utf-8")
        assert _detect_diagram_type(f) == "flowchart"

    def test_sequence_diagram(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("sequenceDiagram\n  Alice->>Bob: Hello", encoding="utf-8")
        assert _detect_diagram_type(f) == "sequencediagram"

    def test_class_diagram(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("classDiagram\n  class Animal", encoding="utf-8")
        assert _detect_diagram_type(f) == "classdiagram"

    def test_state_diagram(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("stateDiagram-v2\n  [*] --> Idle", encoding="utf-8")
        assert _detect_diagram_type(f) == "statediagram"

    def test_gantt(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("gantt\n  title Project", encoding="utf-8")
        assert _detect_diagram_type(f) == "gantt"

    def test_unknown_defaults_to_flowchart(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("unknown content", encoding="utf-8")
        assert _detect_diagram_type(f) == "flowchart"

    def test_empty_file(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("", encoding="utf-8")
        assert _detect_diagram_type(f) == "flowchart"

    def test_missing_file(self, tmp_path):
        f = tmp_path / "nonexistent.mmd"
        assert _detect_diagram_type(f) == "flowchart"


class TestReadFile:
    def test_reads_utf8(self, tmp_path):
        f = tmp_path / "test.mmd"
        f.write_text("flowchart LR", encoding="utf-8")
        assert _read_file(f) == "flowchart LR"

    def test_missing_file_returns_empty(self, tmp_path):
        assert _read_file(tmp_path / "nope.mmd") == ""


class TestDiagramWatcher:
    def test_key_generation(self):
        assert DiagramWatcher._key("proj1", "feat1") == "proj1:feat1"

    def test_subscribe_creates_queue(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        queue = watcher.subscribe("p1", "f1", arch_dir)
        assert isinstance(queue, asyncio.Queue)
        assert "p1:f1" in watcher._subscribers
        assert len(watcher._subscribers["p1:f1"]) == 1

    def test_subscribe_starts_observer(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        watcher.subscribe("p1", "f1", arch_dir)
        assert "p1:f1" in watcher._observers
        assert watcher._observers["p1:f1"].is_alive()

        # Cleanup
        for key in list(watcher._observers.keys()):
            watcher._stop_observer(key)

    def test_subscribe_no_dir(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "nonexistent"

        queue = watcher.subscribe("p1", "f1", arch_dir)
        assert isinstance(queue, asyncio.Queue)
        # Observer not started for nonexistent dir
        assert "p1:f1" not in watcher._observers

    def test_multiple_subscribers(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        q1 = watcher.subscribe("p1", "f1", arch_dir)
        q2 = watcher.subscribe("p1", "f1", arch_dir)
        assert len(watcher._subscribers["p1:f1"]) == 2

        for key in list(watcher._observers.keys()):
            watcher._stop_observer(key)

    def test_unsubscribe_removes_queue(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        q1 = watcher.subscribe("p1", "f1", arch_dir)
        q2 = watcher.subscribe("p1", "f1", arch_dir)

        watcher.unsubscribe("p1", "f1", q1)
        assert len(watcher._subscribers["p1:f1"]) == 1

        for key in list(watcher._observers.keys()):
            watcher._stop_observer(key)

    def test_unsubscribe_last_stops_observer(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        q = watcher.subscribe("p1", "f1", arch_dir)
        assert "p1:f1" in watcher._observers

        watcher.unsubscribe("p1", "f1", q)
        assert "p1:f1" not in watcher._observers
        assert "p1:f1" not in watcher._subscribers

    def test_unsubscribe_unknown_key(self):
        watcher = DiagramWatcher()
        q = asyncio.Queue()
        # Should not raise
        watcher.unsubscribe("unknown", "unknown", q)


class TestManifestUpdate:
    def test_updates_arch_json(self, tmp_path):
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "flow-diagram.mmd").write_text("flowchart LR\n  A-->B", encoding="utf-8")
        (arch_dir / "seq-diagram.mmd").write_text("sequenceDiagram\n  A->>B: Hi", encoding="utf-8")
        (arch_dir / "readme.txt").write_text("ignore me", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert "diagrams" in manifest
        assert len(manifest["diagrams"]) == 2
        names = {e["name"] for e in manifest["diagrams"]}
        assert "Flow Diagram" in names
        assert "Seq Diagram" in names
        for entry in manifest["diagrams"]:
            assert entry["type"] == "mermaid"
            assert "diagramType" in entry

    def test_no_dir_does_nothing(self, tmp_path):
        arch_dir = tmp_path / "nonexistent"
        # Should not raise
        DiagramWatcher._update_manifest_sync(arch_dir)

    def test_empty_dir(self, tmp_path):
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert manifest["diagrams"] == []

    def test_drawio_type(self, tmp_path):
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "my-diagram.drawio").write_text("<xml>drawio</xml>", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert len(manifest["diagrams"]) == 1
        assert manifest["diagrams"][0]["type"] == "drawio"
        assert manifest["diagrams"][0]["diagramType"] == "custom"


@pytest.mark.asyncio
class TestBroadcast:
    async def test_broadcast_delivers_to_subscribers(self):
        watcher = DiagramWatcher()
        q1: asyncio.Queue = asyncio.Queue(maxsize=10)
        q2: asyncio.Queue = asyncio.Queue(maxsize=10)
        watcher._subscribers["test:key"] = [q1, q2]

        msg = {"event": "diagram_changed", "data": {"file": "test.mmd"}}
        await watcher._broadcast("test:key", msg)

        assert q1.qsize() == 1
        assert q2.qsize() == 1
        assert await q1.get() == msg
        assert await q2.get() == msg

    async def test_broadcast_drops_full_queues(self):
        watcher = DiagramWatcher()
        q_ok: asyncio.Queue = asyncio.Queue(maxsize=10)
        q_full: asyncio.Queue = asyncio.Queue(maxsize=1)
        q_full.put_nowait({"dummy": True})  # fill it

        watcher._subscribers["test:key"] = [q_ok, q_full]

        msg = {"event": "diagram_changed", "data": {"file": "test.mmd"}}
        await watcher._broadcast("test:key", msg)

        assert q_ok.qsize() == 1
        # Full queue should be removed
        assert len(watcher._subscribers["test:key"]) == 1

    async def test_broadcast_unknown_key(self):
        watcher = DiagramWatcher()
        # Should not raise
        await watcher._broadcast("nonexistent", {"event": "test", "data": {}})


@pytest.mark.asyncio
class TestStopAll:
    async def test_stop_clears_state(self, tmp_path):
        watcher = DiagramWatcher()
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()

        watcher.subscribe("p1", "f1", arch_dir)
        assert len(watcher._observers) > 0

        await watcher.stop()

        assert len(watcher._observers) == 0
        assert len(watcher._subscribers) == 0
        assert len(watcher._watch_dirs) == 0


class TestExtendedFileTypes:
    """Tests for extended file type support in diagram watcher."""

    def test_watches_puml_files(self):
        """WATCH_EXTENSIONS includes .puml."""
        assert ".puml" in DiagramWatcher.WATCH_EXTENSIONS

    def test_watches_d2_files(self):
        """WATCH_EXTENSIONS includes .d2."""
        assert ".d2" in DiagramWatcher.WATCH_EXTENSIONS

    def test_watches_dot_files(self):
        """WATCH_EXTENSIONS includes .dot."""
        assert ".dot" in DiagramWatcher.WATCH_EXTENSIONS

    def test_watches_md_files(self):
        """WATCH_EXTENSIONS includes .md."""
        assert ".md" in DiagramWatcher.WATCH_EXTENSIONS

    def test_detect_file_type_plantuml(self, tmp_path):
        """_detect_file_type() returns 'plantuml' for .puml."""
        f = tmp_path / "class.puml"
        f.write_text("@startuml", encoding="utf-8")
        assert _detect_file_type(f) == "plantuml"

    def test_detect_file_type_d2(self, tmp_path):
        """_detect_file_type() returns 'd2' for .d2."""
        f = tmp_path / "arch.d2"
        f.write_text("a -> b", encoding="utf-8")
        assert _detect_file_type(f) == "d2"

    def test_detect_file_type_graphviz(self, tmp_path):
        """_detect_file_type() returns 'graphviz' for .dot."""
        f = tmp_path / "graph.dot"
        f.write_text("digraph G {}", encoding="utf-8")
        assert _detect_file_type(f) == "graphviz"

    def test_detect_file_type_markdown(self, tmp_path):
        """_detect_file_type() returns 'markdown' for .md."""
        f = tmp_path / "notes.md"
        f.write_text("# Hello", encoding="utf-8")
        assert _detect_file_type(f) == "markdown"

    def test_detect_file_type_mermaid(self, tmp_path):
        """_detect_file_type() returns 'mermaid' for .mmd."""
        f = tmp_path / "flow.mmd"
        f.write_text("flowchart LR", encoding="utf-8")
        assert _detect_file_type(f) == "mermaid"

    def test_detect_file_type_unknown_defaults_to_mermaid(self, tmp_path):
        """_detect_file_type() returns 'mermaid' for unknown extensions."""
        f = tmp_path / "unknown.xyz"
        f.write_text("content", encoding="utf-8")
        assert _detect_file_type(f) == "mermaid"

    def test_manifest_update_assigns_correct_type_plantuml(self, tmp_path):
        """Manifest update sets type='plantuml' for .puml files."""
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "class-diagram.puml").write_text("@startuml\nclass Foo\n@enduml", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert len(manifest["diagrams"]) == 1
        assert manifest["diagrams"][0]["type"] == "plantuml"
        assert manifest["diagrams"][0]["diagramType"] == "custom"

    def test_manifest_update_assigns_correct_type_markdown(self, tmp_path):
        """Manifest update sets type='markdown' for .md files."""
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "notes.md").write_text("# Architecture Notes", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert len(manifest["diagrams"]) == 1
        assert manifest["diagrams"][0]["type"] == "markdown"
        assert manifest["diagrams"][0]["diagramType"] == "custom"

    def test_manifest_update_assigns_correct_type_d2(self, tmp_path):
        """Manifest update sets type='d2' for .d2 files."""
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "architecture.d2").write_text("a -> b", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert len(manifest["diagrams"]) == 1
        assert manifest["diagrams"][0]["type"] == "d2"

    def test_manifest_update_assigns_correct_type_graphviz(self, tmp_path):
        """Manifest update sets type='graphviz' for .dot files."""
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "deps.dot").write_text("digraph G { a -> b; }", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert len(manifest["diagrams"]) == 1
        assert manifest["diagrams"][0]["type"] == "graphviz"

    def test_manifest_update_skips_underscore_files(self, tmp_path):
        """Manifest update skips files starting with underscore."""
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "_arch.json").write_text("{}", encoding="utf-8")
        (arch_dir / "real.mmd").write_text("flowchart LR", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        assert len(manifest["diagrams"]) == 1
        assert manifest["diagrams"][0]["file"] == "real.mmd"

    def test_manifest_update_mixed_types(self, tmp_path):
        """Manifest update handles a mix of different file types correctly."""
        arch_dir = tmp_path / "arch"
        arch_dir.mkdir()
        (arch_dir / "flow.mmd").write_text("flowchart LR\n  A-->B", encoding="utf-8")
        (arch_dir / "class.puml").write_text("@startuml\nclass Foo\n@enduml", encoding="utf-8")
        (arch_dir / "notes.md").write_text("# Notes", encoding="utf-8")
        (arch_dir / "readme.txt").write_text("ignore me", encoding="utf-8")

        DiagramWatcher._update_manifest_sync(arch_dir)

        manifest = json.loads((arch_dir / "_arch.json").read_text(encoding="utf-8"))
        types = {e["file"]: e["type"] for e in manifest["diagrams"]}
        assert types == {
            "class.puml": "plantuml",
            "flow.mmd": "mermaid",
            "notes.md": "markdown",
        }
        assert len(manifest["diagrams"]) == 3
