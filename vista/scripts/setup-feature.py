"""Setup a new Vista feature directory with scaffolding files."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Setup a new Vista feature")
    parser.add_argument("--name", required=True, help="Feature name")
    parser.add_argument(
        "--parent", default=None, help="Parent feature name (for sub-features)"
    )
    args = parser.parse_args()

    name = args.name
    base = Path(".vista/features")

    if args.parent:
        parent_dir = base / args.parent
        if not parent_dir.exists():
            print(f"Error: Parent feature '{args.parent}' not found at {parent_dir}")
            sys.exit(1)
        feature_dir = parent_dir / name
    else:
        feature_dir = base / name

    if feature_dir.exists():
        print(f"Warning: Feature '{name}' already exists at {feature_dir}. Exiting.")
        sys.exit(0)

    # Create feature directory and specs subdirectory
    specs_dir = feature_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created: {specs_dir}")

    # Create arch/ subdirectory for architecture diagrams
    arch_dir = feature_dir / "arch"
    arch_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created: {arch_dir}")

    # _arch.json - architecture manifest
    arch_manifest = arch_dir / "_arch.json"
    arch_manifest.write_text(
        json.dumps({"feature": name, "diagrams": []}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Created: {arch_manifest}")

    # domain-requirements.md
    domain_req = feature_dir / "domain-requirements.md"
    domain_req.write_text(
        f"# Domain Requirements: {name}\n"
        "\n"
        "## Jobs to Be Done\n"
        "- \n"
        "\n"
        "## User Stories\n"
        "- \n"
        "\n"
        "## Acceptance Criteria\n"
        "- \n"
        "\n"
        "## Constraints\n"
        "- \n",
        encoding="utf-8",
    )
    print(f"Created: {domain_req}")

    # progress.txt
    progress = feature_dir / "progress.txt"
    progress.write_text(
        f"Feature: {name}\nStatus: Not Started\n\n--- Progress Log ---\n",
        encoding="utf-8",
    )
    print(f"Created: {progress}")

    # IMPLEMENTATION_PLAN.md
    impl_plan = feature_dir / "IMPLEMENTATION_PLAN.md"
    impl_plan.write_text(
        f"# Implementation Plan: {name}\n"
        "\n"
        "**Status:** Not Started\n"
        "\n"
        "---\n"
        "\n"
        "This file is populated by Ralph's planning loop.\n"
        "Run `/vista:plan` to generate domain requirements and architecture diagrams,\n"
        "then use Ralph plan mode to build this implementation plan from specs.\n",
        encoding="utf-8",
    )
    print(f"Created: {impl_plan}")

    print(f"\nFeature '{name}' setup complete at {feature_dir.resolve()}")


if __name__ == "__main__":
    main()
