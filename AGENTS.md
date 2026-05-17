# AGENTS.md

## OpenSpec Location

- This repository uses rooted OpenSpec at `openspec/`.
- Do not create or update `docs/openspec`.

## OpenSpec Workflow

- For changes that affect behavior, architecture, or cross-file contracts, start from an OpenSpec change under `openspec/changes/<change-id>/`.
- Keep each PR scoped to its own change. Do not mix artifacts from unrelated OpenSpec changes in one branch or PR.
- Before implementation, read the change's `proposal.md`, `tasks.md`, and affected spec files.
- After updating a change, validate it with `openspec validate <change-id> --type change --strict --json`.

## Agent Usage

- OpenSpec skills for agents are installed under `.agents/skills/openspec-*`.
- Use those skills when the task is proposal generation, implementation from tasks, exploration, or archiving.
- Prefer the repository's existing rooted OpenSpec structure and current change IDs over creating parallel documentation trees.

## Repo Conventions

- Keep OpenSpec changes under `openspec/changes/`.
- Keep stable specifications under `openspec/specs/`.
- When a change is complete and accepted, archive it through the OpenSpec workflow instead of manually moving files.
