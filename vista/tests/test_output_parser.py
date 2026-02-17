"""Tests for the output parser - validates regex patterns against actual script output."""
from server.services.output_parser import OutputParser


class TestOutputParser:
    def setup_method(self):
        self.parser = OutputParser()

    def test_iteration_start(self):
        """Should detect iteration start markers from loop scripts."""
        events = self.parser.parse_line("======================== ITERATION 1 ========================")
        assert len(events) == 1
        assert events[0].event_type == "iteration_start"
        assert events[0].data["iteration"] == 1

    def test_iteration_start_double_digit(self):
        """Should handle multi-digit iteration numbers."""
        events = self.parser.parse_line("======================== ITERATION 42 ========================")
        assert len(events) == 1
        assert events[0].data["iteration"] == 42

    def test_timestamp(self):
        """Should detect Started timestamps from loop scripts."""
        events = self.parser.parse_line("Started: 2025-03-15 14:30")
        assert len(events) == 1
        assert events[0].event_type == "timestamp"
        assert events[0].data["time"] == "2025-03-15 14:30"

    def test_iteration_complete(self):
        """Should detect iteration completion markers."""
        events = self.parser.parse_line("[2025-03-15 14:35] ITERATION 1 complete")
        assert len(events) == 1
        assert events[0].event_type == "iteration_complete"
        assert events[0].data["iteration"] == 1

    def test_loop_finished(self):
        """Should detect loop finish messages."""
        events = self.parser.parse_line("Loop finished after 5 iteration(s)")
        assert len(events) == 1
        assert events[0].event_type == "loop_finished"
        assert events[0].data["total_iterations"] == 5

    def test_max_iterations_reached(self):
        """Should detect max iterations reached messages."""
        events = self.parser.parse_line("Reached max iterations: 10")
        assert len(events) == 1
        assert events[0].event_type == "max_reached"
        assert events[0].data["max"] == 10

    def test_all_phases_complete(self):
        """Should detect all phases complete messages."""
        events = self.parser.parse_line("All phases complete! Stopping loop.")
        assert len(events) == 1
        assert events[0].event_type == "all_phases_complete"

    def test_ralph_control_block(self):
        """Should parse multi-line RALPH_CONTROL blocks."""
        # Header
        events = self.parser.parse_line("# RALPH_CONTROL")
        assert len(events) == 0  # Header starts collection, no event yet

        # Key-value pairs
        events = self.parser.parse_line("status: done")
        assert len(events) == 0  # Still collecting

        events = self.parser.parse_line("files_changed: 3")
        assert len(events) == 0  # Still collecting

        # Empty line ends block
        events = self.parser.parse_line("")
        assert len(events) == 1
        assert events[0].event_type == "ralph_control"
        assert events[0].data["status"] == "done"
        assert events[0].data["files_changed"] == "3"

    def test_ralph_control_block_with_backticks(self):
        """Should end RALPH_CONTROL block on code fence."""
        self.parser.parse_line("# RALPH_CONTROL")
        self.parser.parse_line("status: done")
        events = self.parser.parse_line("```")
        assert len(events) == 1
        assert events[0].data["status"] == "done"

    def test_regular_lines_produce_no_events(self):
        """Normal output lines should produce no events."""
        events = self.parser.parse_line("Building feature...")
        assert len(events) == 0

        events = self.parser.parse_line("git push origin main")
        assert len(events) == 0

    def test_parser_is_stateful(self):
        """Parser should maintain state between parse_line() calls for RALPH_CONTROL."""
        p = OutputParser()

        # First RALPH_CONTROL block
        p.parse_line("# RALPH_CONTROL")
        p.parse_line("status: done")
        events = p.parse_line("")
        assert len(events) == 1
        assert events[0].data["status"] == "done"

        # Second RALPH_CONTROL block should also work
        p.parse_line("# RALPH_CONTROL")
        p.parse_line("status: failed")
        p.parse_line("files_changed: 0")
        events = p.parse_line("")
        assert len(events) == 1
        assert events[0].data["status"] == "failed"
        assert events[0].data["files_changed"] == "0"
