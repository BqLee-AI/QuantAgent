## Status

Implementation is blocked until this OpenSpec change is reviewed and approved. The current scope is API dotenv precedence, API environment-specific dotenv files, Compose boundary alignment, templates, and validation only.

## Graph Overview

Critical path: `B0 -> B1 -> B2 -> R1 -> P1/P2/P3 -> M1 -> V1/V2/V3 -> R2`. `B1` stabilizes the API settings contract before tests, docs, and Compose changes consume it. `P1`、`P2`、`P3` can run in parallel after `R1` because their write boundaries are disjoint, then converge through `M1`.

## Blocking Serial Path

- [x] `B0` Review current baseline.
  - Inputs: `proposal.md`、`design.md`、`specs/api-env-file-precedence/spec.md`、`apps/api/AGENTS.md`、`apps/api/src/quantagent/api/config/settings.py`、`docker-compose.yml`、`.gitignore`。
  - Outputs: Confirmed current `_build_env_files()` behavior, Compose hard-injected variables, template ignore constraints, and affected test locations.
  - Write boundary: none.
  - Dependencies: none.
  - Parallel eligibility: no; this establishes facts used by all later nodes.
  - Validation: record findings in implementation notes or PR description.

- [x] `B1` Implement API dotenv candidate helper.
  - Inputs: `B0` findings and design decisions 1-2.
  - Outputs: API settings loads root `.env` first, `apps/api/.env` next, fixed `apps/api/.env.local` next, selected `apps/api/.env.<APP_ENV>` next, selected `.local` last; real process environment remains highest priority.
  - Write boundary: `apps/api/src/quantagent/api/config/settings.py` only unless a small API-private helper file is justified.
  - Dependencies: `B0`.
  - Parallel eligibility: no; later tests and docs depend on this exact contract.
  - Validation: focused unit checks for helper ordering if available before full test suite.

- [x] `B2` Preserve API settings safety behavior.
  - Inputs: `B1` implementation and existing auth validation rules.
  - Outputs: Existing `Settings` validation still rejects missing/weak staging and production auth secrets, and global `settings = Settings()` does not read unrelated developer paths.
  - Write boundary: `apps/api/src/quantagent/api/config/settings.py` and existing API settings tests if needed.
  - Dependencies: `B1`.
  - Parallel eligibility: no; this is the safety gate before downstream slices.
  - Validation: targeted tests for production/staging secret validation.

## Parallel Work After `R1`

- [x] `P1` Add configuration precedence tests.
  - Inputs: `B1`、`B2`、spec requirements.
  - Outputs: Tests covering duplicate root/API variables, `APP_ENV=test` and `APP_ENV=staging` selection, unrelated environment files not loading, process environment override, and staging/production secret validation.
  - Write boundary: `apps/api/src/tests/` only.
  - Dependencies: `R1`.
  - Parallel eligibility: yes; tests can be authored against the stabilized helper without touching docs or Compose.
  - Validation: `cd apps/api && uv run python -m unittest discover -s src` at `V1`.

- [x] `P2` Update API docs and dotenv templates.
  - Inputs: `design.md` decisions 1-3 and `B1` contract.
  - Outputs: `apps/api/README.md` explains precedence, duplicates, true environment variable override, local/test/staging/production usage, and secret handling; API `.env.example` no longer says API dotenv is only for private variables; API `.env.*.example` templates are non-sensitive and commit-eligible.
  - Write boundary: `apps/api/README.md`、`apps/api/.env.example`、`apps/api/.env.local.example`、`apps/api/.env.test.example`、`apps/api/.env.staging.example`、`apps/api/.env.production.example`、`.gitignore`。
  - Dependencies: `R1`.
  - Parallel eligibility: yes; docs/templates do not overlap with settings implementation or Compose file except through `M1` consistency.
  - Validation: manual secret scan of templates and `git status --short` to confirm templates are not ignored.

- [x] `P3` Align Docker Compose boundary.
  - Inputs: `design.md` decision 4 and current `docker-compose.yml`.
  - Outputs: Compose overrides the image default command with explicit Uvicorn host/port arguments and does not define `api.environment`; API application settings are no longer hard-injected from root `.env`; container-reachable database URL has a documented dotenv or external environment path.
  - Write boundary: `Dockerfile`, `docker-compose.yml` and root `.env.example` only.
  - Dependencies: `R1`.
  - Parallel eligibility: yes; Compose changes are isolated from API Python code but must merge through `M1`.
  - Validation: `docker compose config` at `V2`, plus manual check that `api.environment` does not include `APP_ENV`、`DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL`、`AUTH_*`、`API_*` hard injections.

## Merge / Integration Nodes

- [x] `M1` Reconcile docs, examples, Compose, and tests.
  - Inputs: `P1`、`P2`、`P3`.
  - Outputs: README, examples, tests, and Compose describe the same precedence order and Compose escape hatch; no artifact claims root `.env` is the final API source of truth.
  - Write boundary: changed files from `P1`、`P2`、`P3` only.
  - Dependencies: `P1`、`P2`、`P3`.
  - Parallel eligibility: no; this resolves cross-artifact drift.
  - Validation: review changed snippets for contradictory precedence language.

## Review Checkpoints

- [x] `R1` Design checkpoint after `B2`.
  - Inputs: implemented helper shape and existing safety validation behavior.
  - Outputs: Confirm no change to API routes, auth semantics, database schema, Alembic migration, front-end env contract, plugin config truth source, or `packages/core` default settings behavior.
  - Dependencies: `B2`.
  - Validation: compare implementation scope to `Non-Goals` and `Deferred / Out of Phase`.

- [x] `R2` PR readiness checkpoint.
  - Inputs: `M1` and validation results.
  - Outputs: PR notes include change id, evidence chain, validation commands, whether Docker services were actually started, remaining unverified risks, and secret safety boundary.
  - Dependencies: `V1`、`V2`、`V3`.
  - Validation: PR description review.

## Validation Nodes

- [x] `V0` Validate OpenSpec artifacts after documentation edits.
  - Inputs: this change directory.
  - Outputs: strict OpenSpec validation result.
  - Dependencies: OpenSpec artifact edits.
  - Command: `openspec validate api-env-file-precedence --type change --strict --json` or repository equivalent.

- [x] `V1` Run API unit tests.
  - Inputs: `M1`.
  - Outputs: API unittest result.
  - Dependencies: `M1`.
  - Command: `cd apps/api && uv run python -m unittest discover -s src`.

- [x] `V2` Validate Compose config parsing.
  - Inputs: `P3` and `M1`.
  - Outputs: Compose config parses; PR notes whether services were started.
  - Dependencies: `M1`.
  - Command: `docker compose config`.

- [x] `V3` Verify Git ignore and secret safety.
  - Inputs: `P2` templates and `.gitignore`.
  - Outputs: `.env.*.example` files are visible to Git; no real secret or production database URL is present in templates.
  - Dependencies: `M1`.
  - Command: `git status --short` plus manual review of template values.

## Multi-Agent Plan

Safe parallelism exists only after `R1`. `P1`、`P2`、`P3` can be assigned separately because they write tests, docs/templates, and Compose/example files respectively. `B1`/`B2` should stay single-owner because they define the shared API settings contract consumed by every other slice. `M1` should also stay single-owner to prevent cross-artifact precedence drift.
