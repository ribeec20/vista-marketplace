# Model Configuration

This document explains how models are configured and read for use with the Ralph Loop Runner.

## Quick Start

The portable scripts use **Claude CLI** directly with the `--model` flag:

```bash
claude -p --model opus    # Use Claude Opus
claude -p --model sonnet  # Use Claude Sonnet
claude -p --model haiku   # Use Claude Haiku
```

## Available Models in Script

When you run `./ralph.sh` or `.\ralph.ps1`, you can select from:

| Model | Best For |
|-------|----------|
| `sonnet` | General tasks, fast execution |
| `opus` | Complex reasoning, architectural decisions |
| `haiku` | Simple tasks, fastest execution |

## Using OpenCode CLI (Alternative)

If you prefer to use **OpenCode CLI** instead of Claude CLI, the system can read models from OpenCode's configuration.

### OpenCode Config File Locations

| OS | Config Path |
|----|-------------|
| Linux/macOS | `~/.config/opencode/opencode.json` |
| Linux/macOS (alt) | `~/.local/share/opencode/opencode.json` |
| Windows | `%APPDATA%\opencode\opencode.json` |
| Windows (alt) | `%LOCALAPPDATA%\opencode\opencode.json` |

You can also set a custom path via environment variable:
```bash
export OPENCODE_CONFIG_FILE=/path/to/opencode.json
```

### Reading Models from OpenCode

OpenCode provides models via CLI commands:

```bash
# List available models
opencode models

# Output example:
# anthropic/claude-opus-4
# anthropic/claude-sonnet-4
# openai/gpt-4
# google/gemini-pro
```

```bash
# Check configured providers
opencode auth list

# Output example:
# anthropic (configured)
# openai (configured)
# google (not configured)
```

### OpenCode Config JSON Structure

The `opencode.json` file typically contains:

```json
{
  "defaultModel": "anthropic/claude-sonnet-4",
  "providers": {
    "anthropic": {
      "enabled": true
    },
    "openai": {
      "enabled": true
    }
  }
}
```

**Note**: API keys are stored separately in `auth.json` and should NEVER be committed to version control.

## Model Selection Flow

```
┌─────────────────────────────────────────┐
│         User runs ralph.sh              │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│    Step 3: Select Model                 │
│    ─────────────────────────────────    │
│      1) sonnet                          │
│      2) opus                            │
│      3) haiku                           │
│                                         │
│    Enter choice [1-3]: _                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│    Claude CLI invoked with:             │
│    --model {selected_model}             │
└─────────────────────────────────────────┘
```

## Customizing Models

### Option 1: Edit the Script

Modify the `MODELS` array in `ralph.sh`:

```bash
# Available models
MODELS=("sonnet" "opus" "haiku" "claude-3-5-sonnet-latest")
```

Or in `ralph.ps1`:

```powershell
$Models = @("sonnet", "opus", "haiku", "claude-3-5-sonnet-latest")
```

### Option 2: Use OpenCode Model IDs

If using OpenCode CLI, modify the script to use full model IDs:

```bash
MODELS=("anthropic/claude-opus-4" "anthropic/claude-sonnet-4" "openai/gpt-4")
```

Then update the claude invocation to use opencode:

```bash
# Replace:
cat "$prompt_file" | claude -p --model "$model" ...

# With:
cat "$prompt_file" | opencode --model "$model" ...
```

## Agent Configuration (agents.yaml)

For more complex setups, you can define agent-specific models in a YAML config:

```yaml
# configs/agents.yaml

assigner:
  name: assigner
  model: anthropic/claude-opus-4
  description: "Inter-loop task assigner"

workers:
  - name: build_worker
    model: anthropic/claude-sonnet-4
    specialization: general

  - name: review_worker
    model: anthropic/claude-haiku-4
    specialization: testing

  - name: escalation_opus
    model: anthropic/claude-opus-4
    specialization: debugging
```

This allows different agents to use different models based on task complexity.

## Security Notes

- **Never commit API keys** to version control
- API keys are managed by Claude CLI or OpenCode CLI
- The portable scripts do NOT access or store API keys
- Use environment variables for sensitive configuration:
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  ```

## Troubleshooting

### "Model not found"

Ensure you're authenticated:
```bash
claude auth login
# or
opencode auth add anthropic
```

### "Invalid model"

Check available models:
```bash
# For Claude CLI, valid values are: sonnet, opus, haiku
# For OpenCode CLI:
opencode models
```

### Model not in selection list

Edit the `MODELS` array in the script to add your desired model.
