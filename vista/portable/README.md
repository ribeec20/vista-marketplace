# Ralph Loop Runner - Portable Edition

A self-contained, portable version of the Ralph Loop system for running autonomous AI development loops.

## Prerequisites

- **Claude CLI** installed and authenticated (`claude` command available)
- **Git** (optional, for version control features)
- **Bash** (Linux/macOS/WSL) or **PowerShell** (Windows)

## Quick Start

### Linux/macOS/WSL

```bash
# 1. Copy the portable folder to your project root
cp -r portable/ /path/to/your/project/ralph/

# 2. Navigate to the folder
cd /path/to/your/project/ralph/

# 3. Make script executable
chmod +x ralph.sh

# 4. Run the interactive menu
./ralph.sh
```

### Windows (PowerShell)

```powershell
# 1. Copy the portable folder to your project root
Copy-Item -Recurse portable\ C:\path\to\your\project\ralph\

# 2. Navigate to the folder
cd C:\path\to\your\project\ralph\

# 3. Run the interactive menu
.\ralph.ps1
```

## Usage Flow

When you run the script, you'll be guided through:

1. **Select Feature** - Choose an existing feature or create a new one
2. **Select Mode** - Choose between:
   - `plan` - Research and planning only (no code changes)
   - `build` - Implementation mode (writes code)
3. **Select Model** - Choose the AI model:
   - `sonnet` - Fast, good for straightforward tasks
   - `opus` - Most capable, for complex reasoning
   - `haiku` - Fastest, for simple tasks
4. **Run Type** - Choose execution style:
   - Single Iteration - Run once and stop
   - Continuous Loop - Run until manually stopped
   - Limited Loop - Run up to N iterations

## Directory Structure

```
portable/
├── ralph.sh          # Main runner script (bash)
├── ralph.ps1         # Main runner script (PowerShell)
├── README.md         # This file
└── templates/        # Template files for new features
    ├── AGENTS.md
    ├── IMPLEMENTATION_PLAN.md
    ├── PROMPT_build.md
    ├── PROMPT_plan.md
    └── progress_template.txt

After creating a feature:
portable/
├── my_feature/
│   ├── AGENTS.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── PROMPT_build.md
│   ├── PROMPT_plan.md
│   ├── progress.txt
│   └── specs/
│       └── README.md
```

## Creating a Feature

1. Run `./ralph.sh` (or `.\ralph.ps1`)
2. Select `[Create New Feature]`
3. Enter a feature name (e.g., `user_auth`)
4. Add your specifications to `my_feature/specs/`

## Specification Files

Place your feature specifications in the `specs/` directory:

- `specs/README.md` - Overview of the feature
- `specs/api.md` - API specifications
- `specs/ui.md` - UI requirements
- `specs/prd.json` - Product requirements (optional)

## Workflow

### Planning Phase

1. Run with `plan` mode first
2. The agent will analyze specs and create an implementation plan
3. Review `IMPLEMENTATION_PLAN.md` after each iteration
4. Iterate until the plan is complete

### Build Phase

1. Run with `build` mode
2. The agent will implement tasks from `IMPLEMENTATION_PLAN.md`
3. Progress is tracked in `progress.txt`
4. Changes are committed and pushed (if git repo)

## Tips

- **Start with planning** - Always run a few `plan` iterations first
- **Review between iterations** - Use "Single Iteration" mode to review progress
- **Keep specs updated** - The agent works from your specs
- **Check progress.txt** - See what's been completed
- **Use opus for complex work** - Plan mode benefits from opus reasoning

## Troubleshooting

### "claude command not found"

Install the Claude CLI:
```bash
npm install -g @anthropic-ai/claude-cli
claude auth login
```

### "Permission denied"

Make the script executable:
```bash
chmod +x ralph.sh
```

### "No features found"

Create a feature first by selecting `[Create New Feature]` in the menu.
