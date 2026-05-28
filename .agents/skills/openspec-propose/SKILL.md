---
name: openspec-propose
description: Propose a new change with all artifacts generated in one step. Use when the user wants to quickly describe what they want to build and get a complete proposal with design, specs, and tasks ready for implementation.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.3.1"
---

Propose a new change - create the change and generate all artifacts in one step.

I'll create a change with artifacts:
- proposal.md (what & why)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, run /opsx:apply

---

**Input**: The user's request should include a change name (kebab-case) OR a description of what they want to build.

**QuantAgent quality gate**: Before generating artifacts, read the relevant project truth sources:
- `AGENTS.md` and the nearest `AGENTS.md` under affected paths.
- Related `docs/design/*.md`, `docs/prd/*.md`, existing `openspec/changes/*`, issue comments, and PR discussion when referenced.
- `.agents/skills/references/engineering-quality-gate.md`.
- For `apps/web/**` changes, `.agents/skills/references/web-architecture-gate.md`.

Generated artifacts must be specific enough for implementation. Do not produce generic proposal/design/tasks text. If the change affects architecture, behavior, contracts, frontend UI, backend services, persistence, permissions, or auditability, the artifacts must record directory/file planning, layered architecture, responsibilities, core models, API/DTO/schema/event/config/database field drafts, reuse points, data flow, failure paths, and validation entrypoints.

For Web changes, artifacts must explicitly apply `web-architecture-gate.md`: route boundaries, app runtime ownership, `apiClient -> BaseApi -> FeatureApi`, TanStack Query hooks, business hooks, view components, README / usage notes, Chinese comments, and directory grouping. Do not leave these choices for implementation.

**Steps**

1. **If no clear input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **IMPORTANT**: Do NOT proceed without understanding what the user wants to build.

2. **Read QuantAgent context**

   Read the quality gate and only the directly relevant project truth sources. At minimum:
   - Root `AGENTS.md`
   - The nearest `AGENTS.md` for affected app/package/plugin paths
   - `.agents/skills/references/engineering-quality-gate.md`
   - `.agents/skills/references/web-architecture-gate.md` when affected paths or requested scope involve `apps/web/**`
   - Related design/PRD/OpenSpec/issue/PR context named by the user or required by the affected boundary

   If context conflicts, capture the conflict in the artifacts instead of silently choosing.

3. **Create the change directory**
   ```bash
   openspec new change "<name>"
   ```
   This creates a scaffolded change at `openspec/changes/<name>/` with `.openspec.yaml`.

4. **Get the artifact build order**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to get:
   - `applyRequires`: array of artifact IDs needed before implementation (e.g., `["tasks"]`)
   - `artifacts`: list of all artifacts with their status and dependencies

5. **Create artifacts in sequence until apply-ready**

   Use the **TodoWrite tool** to track progress through the artifacts.

   Loop through artifacts in dependency order (artifacts with no pending dependencies first):

   a. **For each artifact that is `ready` (dependencies satisfied)**:
      - Get instructions:
        ```bash
        openspec instructions <artifact-id> --change "<name>" --json
        ```
      - The instructions JSON includes:
        - `context`: Project background (constraints for you - do NOT include in output)
        - `rules`: Artifact-specific rules (constraints for you - do NOT include in output)
        - `template`: The structure to use for your output file
        - `instruction`: Schema-specific guidance for this artifact type
        - `outputPath`: Where to write the artifact
        - `dependencies`: Completed artifacts to read for context
      - Read any completed dependency files for context
      - Create the artifact file using `template` as the structure
      - Apply `.agents/skills/references/engineering-quality-gate.md`:
        - `proposal.md` must cover why now, current gap, non-goals, and risk boundary.
        - `design.md` must be an implementation blueprint covering directory/file planning, layered architecture, module responsibilities, core models, DTO/schema/API/event/config/database field drafts, data flow, failure paths, reuse decisions, and validation strategy.
        - `specs/**/spec.md` must describe verifiable requirements and scenarios, not implementation chores.
        - `tasks.md` must show dependencies, parallel boundaries, write scopes, review gates, and validation actions.
      - For Web changes, apply `.agents/skills/references/web-architecture-gate.md` so `design.md` and `tasks.md` name the route, runtime/API, query/mutation, business hook, component, README, comment, and validation boundaries.
      - Apply `context` and `rules` as constraints - but do NOT copy them into the file
      - Show brief progress: "Created <artifact-id>"

   b. **Continue until all `applyRequires` artifacts are complete**
      - After creating each artifact, re-run `openspec status --change "<name>" --json`
      - Check if every artifact ID in `applyRequires` has `status: "done"` in the artifacts array
      - Stop when all `applyRequires` artifacts are done

   c. **If an artifact requires user input** (unclear context):
      - Use **AskUserQuestion tool** to clarify
      - Then continue with creation

6. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for implementation."
- Prompt: "Run `/opsx:apply` or ask me to implement to start working on the tasks."

**Artifact Creation Guidelines**

- Follow the `instruction` field from `openspec instructions` for each artifact type
- The schema defines what each artifact should contain - follow it
- Read dependency artifacts for context before creating new ones
- Use `template` as the structure for your output file - fill in its sections
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output

**Guardrails**
- Create ALL artifacts needed for implementation (as defined by schema's `apply.requires`)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable decisions to keep momentum
- If a change with that name already exists, ask if user wants to continue it or create a new one
- Verify each artifact file exists after writing before proceeding to next
