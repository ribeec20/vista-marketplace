"""Context assembler for architecture chat prompts.

Extracts prompt assembly from ChatService into a clean, testable module.
Assembles system prompt, diagram context, conversation history, and user message.
"""

from pathlib import Path
from typing import Optional


class ContextAssembler:
    """Assembles the full prompt from diagram context, history, and user message."""

    @staticmethod
    def build_system_prompt(
        arch_dir: str,
        specs_dir: str,
        project_root: str,
    ) -> str:
        """Build system prompt scoping AI to arch/ and specs/ directories."""
        return (
            "You are an architecture documentation assistant.\n"
            f"You can read files anywhere in the project for context: {project_root}\n"
            f"You can read specification files in: {specs_dir}\n"
            f"You ONLY edit .mmd diagram files in the arch directory: {arch_dir}\n"
            "Do NOT edit source code or any files outside the arch directory.\n"
            "When asked to modify diagrams, edit the .mmd files directly.\n"
            "Provide clear, concise feedback on the provided diagrams.\n"
            "When discussing diagrams, be specific and reference node names and connections."
        )

    @staticmethod
    def build_full_prompt(
        message: str,
        context: Optional[str] = None,
        history: Optional[list[dict]] = None,
        system_prompt: str = "",
    ) -> str:
        """Assemble the complete prompt for a chat API message.

        Both Claude (via Companion) and OpenCode maintain native conversation
        history, so we do NOT re-send prior turns.  The prompt structure is:

        1. System prompt (role + file access instructions)
        2. Diagram context (attached files + selected elements)
        3. Current user message

        History is accepted for backwards compatibility but ignored — the
        provider session already has the conversation context.
        """
        parts = []
        if system_prompt:
            parts.append(system_prompt)
            parts.append("")

        if context:
            parts.append("--- DIAGRAM CONTEXT ---")
            parts.append(context)
            parts.append("--- END CONTEXT ---")
            parts.append("")

        parts.append(message)

        return "\n".join(parts)

    @staticmethod
    def get_diagram_context(
        arch_dir: str,
        attached_files: list[str],
        selected_elements: Optional[list[dict]] = None,
    ) -> str:
        """Read attached diagram files and format as context block."""
        parts = []
        for filename in attached_files:
            filepath = Path(arch_dir) / filename
            if filepath.is_file():
                content = filepath.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n```mermaid\n{content}\n```")

        if selected_elements:
            parts.append("\n## Selected Elements")
            for elem in selected_elements:
                parts.append(f"- {elem.get('id', 'unknown')}: {elem.get('label', '')}")

        return "\n\n".join(parts)
