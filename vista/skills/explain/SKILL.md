---
name: explain
description: Provide a simple, clear explanation of a concept, feature, or piece of code. Include diagrams (Mermaid) when they help clarify. Use when the user asks to explain something.
disable-model-invocation: true
argument-hint: <topic>
---

# Explain

Provide a clear, concise explanation of the given topic.

## Rules

- Keep explanations simple and jargon-free
- Include simple ASCII/text diagrams in chat when they help illustrate relationships, flows, or architecture
- Prefer visual over verbose — a good diagram replaces paragraphs of text
- Use **AskUserQuestion** if the topic is ambiguous
- Tailor depth to what the user actually needs, not an exhaustive deep-dive
