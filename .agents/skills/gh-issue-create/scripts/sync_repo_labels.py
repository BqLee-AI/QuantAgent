#!/usr/bin/env python3
"""Sync the QuantAgent issue labels to GitHub with gh CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys


DEFAULT_LABELS: list[dict[str, str]] = [
    {"name": "type:feature", "color": "1D76DB", "description": "Product or capability work"},
    {"name": "type:bug", "color": "D73A4A", "description": "Existing behavior is wrong"},
    {"name": "type:docs", "color": "0075CA", "description": "Documentation only"},
    {"name": "type:test", "color": "0E8A16", "description": "Test or validation work"},
    {"name": "type:chore", "color": "C5DEF5", "description": "Repository or tooling maintenance"},
    {"name": "type:refactor", "color": "5319E7", "description": "Internal change without behavior change"},
    {"name": "type:discussion", "color": "D4C5F9", "description": "Needs design or product discussion"},
    {"name": "priority:high", "color": "B60205", "description": "Blocks current work or follow-ups"},
    {"name": "priority:medium", "color": "FBCA04", "description": "Default priority"},
    {"name": "priority:low", "color": "C2E0C6", "description": "Useful but not on the critical path"},
    {"name": "status:needs-review", "color": "FBCA04", "description": "Needs maintainer review"},
    {"name": "status:ready", "color": "0E8A16", "description": "Ready to pick up"},
    {"name": "status:blocked", "color": "D73A4A", "description": "Blocked by dependency or decision"},
    {"name": "status:in-progress", "color": "1D76DB", "description": "Currently being worked on"},
    {"name": "area:api", "color": "C5DEF5", "description": "FastAPI service boundary"},
    {"name": "area:web", "color": "C5DEF5", "description": "React Vite web app"},
    {"name": "area:core", "color": "C5DEF5", "description": "Shared core package"},
    {"name": "area:agent", "color": "C5DEF5", "description": "Agent and workflow package"},
    {"name": "area:plugin", "color": "C5DEF5", "description": "Plugin runtime or SDK"},
    {"name": "area:contracts", "color": "C5DEF5", "description": "Cross-boundary contracts"},
    {"name": "area:worker", "color": "C5DEF5", "description": "Background worker boundary"},
    {"name": "area:scheduler", "color": "C5DEF5", "description": "Scheduled job boundary"},
    {"name": "area:docs", "color": "C5DEF5", "description": "Docs or PRD/design assets"},
    {"name": "area:infra", "color": "C5DEF5", "description": "Build, Docker, deployment, tooling"},
    {"name": "area:openspec", "color": "C5DEF5", "description": "OpenSpec artifacts"},
    {"name": "complexity:small", "color": "C2E0C6", "description": "Small, focused change"},
    {"name": "complexity:medium", "color": "FBCA04", "description": "Moderate coordination"},
    {"name": "complexity:large", "color": "D93F0B", "description": "Large or multi-area work"},
]


def sync_labels(repo: str, dry_run: bool) -> None:
    for label in DEFAULT_LABELS:
        cmd = [
            "gh",
            "label",
            "create",
            label["name"],
            "--repo",
            repo,
            "--color",
            label["color"],
            "--description",
            label["description"],
            "--force",
        ]
        if dry_run:
            print(" ".join(cmd))
            continue

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            sys.stderr.write(result.stderr or result.stdout)
            raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="BqLee-AI/QuantAgent", help="GitHub repo in OWNER/REPO form")
    parser.add_argument("--dry-run", action="store_true", help="Print gh commands without running them")
    args = parser.parse_args()

    sync_labels(args.repo, args.dry_run)
    print(f"{'would sync' if args.dry_run else 'synced'} {len(DEFAULT_LABELS)} labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
