#!/bin/bash
# Ralph Loop Runner - Portable Edition
# Usage: ./ralph.sh
# Interactive menu to select feature, mode, and model

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FEATURES_DIR="$PROJECT_ROOT/.vista/features"
TEMPLATES_DIR="$SCRIPT_DIR/templates"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Available models
MODELS=("sonnet" "opus" "haiku")

print_header() {
    echo -e "${CYAN}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "           RALPH LOOP RUNNER - PORTABLE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${NC}"
}

print_menu_header() {
    echo -e "${YELLOW}$1${NC}"
    echo "─────────────────────────────────────────────────────"
}

# Get list of feature directories under .vista/features/
get_features() {
    local features=()
    if [ ! -d "$FEATURES_DIR" ]; then
        echo ""
        return
    fi
    for dir in "$FEATURES_DIR"/*/; do
        [ -d "$dir" ] || continue
        dir_name=$(basename "$dir")
        features+=("$dir_name")
    done
    echo "${features[@]}"
}

# Select from numbered menu
select_option() {
    local prompt="$1"
    shift
    local options=("$@")

    if [ ${#options[@]} -eq 0 ]; then
        echo -e "${RED}No options available!${NC}"
        return 1
    fi

    print_menu_header "$prompt"
    for i in "${!options[@]}"; do
        echo -e "  ${GREEN}$((i+1))${NC}) ${options[$i]}"
    done
    echo ""

    while true; do
        read -p "Enter choice [1-${#options[@]}]: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#options[@]} ]; then
            SELECTED="${options[$((choice-1))]}"
            return 0
        fi
        echo -e "${RED}Invalid choice. Please enter a number between 1 and ${#options[@]}${NC}"
    done
}

# Create new feature from templates
create_feature() {
    echo ""
    read -p "Enter feature name (e.g., my_feature): " feature_name

    if [ -z "$feature_name" ]; then
        echo -e "${RED}Feature name cannot be empty${NC}"
        return 1
    fi

    # Sanitize feature name
    feature_name=$(echo "$feature_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    # Create under .vista/features/
    mkdir -p "$FEATURES_DIR"
    local feature_dir="$FEATURES_DIR/$feature_name"

    if [ -d "$feature_dir" ]; then
        echo -e "${RED}Feature '$feature_name' already exists!${NC}"
        return 1
    fi

    echo -e "${BLUE}Creating feature: $feature_name${NC}"

    # Create directory structure
    mkdir -p "$feature_dir/specs"

    # Get current date
    current_date=$(date +"%Y-%m-%d")

    # Get project name from project root
    project_name=$(basename "$PROJECT_ROOT")

    # Copy and process templates
    for template in "$TEMPLATES_DIR"/*.md "$TEMPLATES_DIR"/*.txt; do
        if [ -f "$template" ]; then
            filename=$(basename "$template")
            # Process template variables
            sed -e "s|{{FEATURE_NAME}}|$feature_name|g" \
                -e "s|{{FEATURE_DIR}}|$feature_dir|g" \
                -e "s|{{PROJECT_NAME}}|$project_name|g" \
                -e "s|{{DATE}}|$current_date|g" \
                "$template" > "$feature_dir/$filename"
        fi
    done

    # Rename progress_template.txt to progress.txt
    if [ -f "$feature_dir/progress_template.txt" ]; then
        mv "$feature_dir/progress_template.txt" "$feature_dir/progress.txt"
    fi

    # Create empty specs placeholder
    echo "# Feature Specification: $feature_name" > "$feature_dir/specs/README.md"
    echo "" >> "$feature_dir/specs/README.md"
    echo "Add your specification files here." >> "$feature_dir/specs/README.md"

    echo -e "${GREEN}Feature '$feature_name' created successfully!${NC}"
    echo -e "  Directory: $feature_dir"
    echo -e "  Next steps:"
    echo -e "    1. Add specification files to $feature_dir/specs/"
    echo -e "    2. Run ./ralph.sh and select '$feature_name'"
    echo ""
}

# Run the loop
run_loop() {
    local feature_dir="$1"
    local mode="$2"
    local model="$3"
    local max_iterations="${4:-0}"

    local prompt_file
    if [ "$mode" = "plan" ]; then
        prompt_file="$feature_dir/PROMPT_plan.md"
    else
        prompt_file="$feature_dir/PROMPT_build.md"
    fi

    # Verify prompt file exists
    if [ ! -f "$prompt_file" ]; then
        echo -e "${RED}Error: $prompt_file not found${NC}"
        exit 1
    fi

    local current_branch
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        current_branch=$(git branch --show-current)
    else
        current_branch="(not a git repo)"
    fi

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  Feature: ${GREEN}$(basename "$feature_dir")${NC}"
    echo -e "  Mode:    ${GREEN}$mode${NC}"
    echo -e "  Model:   ${GREEN}$model${NC}"
    echo -e "  Prompt:  ${GREEN}$(basename "$prompt_file")${NC}"
    echo -e "  Branch:  ${GREEN}$current_branch${NC}"
    echo -e "  Project: ${GREEN}$PROJECT_ROOT${NC}"
    [ "$max_iterations" -gt 0 ] && echo -e "  Max:     ${GREEN}$max_iterations iterations${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Agent must be initialized at project root
    cd "$PROJECT_ROOT"

    local iteration=0

    while true; do
        if [ "$max_iterations" -gt 0 ] && [ "$iteration" -ge "$max_iterations" ]; then
            echo -e "${YELLOW}Reached max iterations: $max_iterations${NC}"
            break
        fi

        # Run Claude with the prompt (cwd is project root, prompt has feature path)
        cat "$prompt_file" | claude -p \
            --dangerously-skip-permissions \
            --output-format=stream-json \
            --model "$model" \
            --verbose

        # Try to push if in a git repo
        if git rev-parse --is-inside-work-tree &>/dev/null; then
            git push origin "$current_branch" 2>/dev/null || {
                echo -e "${YELLOW}Creating remote branch...${NC}"
                git push -u origin "$current_branch" 2>/dev/null || true
            }
        fi

        iteration=$((iteration + 1))
        echo -e "\n\n${CYAN}======================== LOOP $iteration ========================${NC}\n"
    done
}

# Single iteration mode
run_single() {
    local feature_dir="$1"
    local mode="$2"
    local model="$3"

    local prompt_file
    if [ "$mode" = "plan" ]; then
        prompt_file="$feature_dir/PROMPT_plan.md"
    else
        prompt_file="$feature_dir/PROMPT_build.md"
    fi

    if [ ! -f "$prompt_file" ]; then
        echo -e "${RED}Error: $prompt_file not found${NC}"
        exit 1
    fi

    local current_branch
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        current_branch=$(git branch --show-current)
    else
        current_branch="(not a git repo)"
    fi

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  Feature: ${GREEN}$(basename "$feature_dir")${NC}"
    echo -e "  Mode:    ${GREEN}$mode (single iteration)${NC}"
    echo -e "  Model:   ${GREEN}$model${NC}"
    echo -e "  Branch:  ${GREEN}$current_branch${NC}"
    echo -e "  Project: ${GREEN}$PROJECT_ROOT${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Agent must be initialized at project root
    cd "$PROJECT_ROOT"

    cat "$prompt_file" | claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model "$model" \
        --verbose

    if git rev-parse --is-inside-work-tree &>/dev/null; then
        git push origin "$current_branch" 2>/dev/null || {
            git push -u origin "$current_branch" 2>/dev/null || true
        }
    fi

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ Single iteration complete${NC}"
    echo -e "  Review output, make edits, then run again"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Main menu
main() {
    print_header

    # Step 1: Select or create feature
    features=($(get_features))
    features+=("[Create New Feature]")

    select_option "Step 1: Select Feature" "${features[@]}"

    if [ "$SELECTED" = "[Create New Feature]" ]; then
        create_feature
        # Refresh features list
        features=($(get_features))
        if [ ${#features[@]} -eq 0 ]; then
            echo -e "${RED}No features found. Please create a feature first.${NC}"
            exit 1
        fi
        select_option "Select the new feature" "${features[@]}"
    fi

    FEATURE_NAME="$SELECTED"
    FEATURE_DIR="$FEATURES_DIR/$FEATURE_NAME"

    echo -e "${GREEN}Selected: $FEATURE_NAME${NC}"
    echo ""

    # Step 2: Select mode
    modes=("plan" "build")
    select_option "Step 2: Select Mode" "${modes[@]}"
    MODE="$SELECTED"
    echo -e "${GREEN}Selected: $MODE${NC}"
    echo ""

    # Step 3: Select model
    select_option "Step 3: Select Model" "${MODELS[@]}"
    MODEL="$SELECTED"
    echo -e "${GREEN}Selected: $MODEL${NC}"
    echo ""

    # Step 4: Select run type
    run_types=("Single Iteration" "Continuous Loop" "Limited Loop (set max)")
    select_option "Step 4: Run Type" "${run_types[@]}"
    RUN_TYPE="$SELECTED"

    case "$RUN_TYPE" in
        "Single Iteration")
            run_single "$FEATURE_DIR" "$MODE" "$MODEL"
            ;;
        "Continuous Loop")
            run_loop "$FEATURE_DIR" "$MODE" "$MODEL" 0
            ;;
        "Limited Loop (set max)")
            read -p "Enter max iterations: " max_iter
            if ! [[ "$max_iter" =~ ^[0-9]+$ ]]; then
                max_iter=5
            fi
            run_loop "$FEATURE_DIR" "$MODE" "$MODEL" "$max_iter"
            ;;
    esac
}

# Run main
main "$@"
