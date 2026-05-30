---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change. Use when the user wants to start implementing, continue implementation, or work through tasks.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.3.1"
---

Implement tasks from an OpenSpec change.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**QuantAgent quality gate**: Before implementation, read `.agents/skills/references/engineering-quality-gate.md` and verify the selected change artifacts are implementation-ready. If affected paths include `apps/web/**`, also read `.agents/skills/references/web-architecture-gate.md`. For complex Web features, routes, shared capabilities, or file splitting, read `.agents/skills/references/web-file-responsibility-and-feature-structure.md`. If affected paths include `apps/api/**`, also read `.agents/skills/references/api-architecture-gate.md`. If affected paths include `packages/core/**`, `packages/plugin-sdk/**`, or `plugins/**`, also read `.agents/skills/references/core-and-plugin-architecture-gate.md`. If the artifacts do not describe directory/file planning, responsibilities, core models, interface fields, reuse points, data flow, failure paths, and validation entrypoints, pause and propose artifact updates instead of writing code.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx:apply <other>`).

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - Which artifact contains the tasks (typically "tasks" for spec-driven, check status for others)

3. **Get apply instructions**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This returns:
   - `contextFiles`: artifact ID -> array of concrete file paths (varies by schema - could be proposal/specs/design/tasks or spec/tests/implementation/docs)
   - Progress (total, complete, remaining)
   - Task list with status
   - Dynamic instruction based on current state

   **Handle states:**
   - If `state: "blocked"` (missing artifacts): show message, suggest using openspec-continue-change
   - If `state: "all_done"`: congratulate, suggest archive
   - Otherwise: proceed to implementation

4. **Read context files**

   Read every file path listed under `contextFiles` from the apply instructions output.
   The files depend on the schema being used:
   - **spec-driven**: proposal, specs, design, tasks
   - Other schemas: follow the contextFiles from CLI output

   Also read `.agents/skills/references/engineering-quality-gate.md`, root `AGENTS.md`, and the nearest `AGENTS.md` files for the paths the tasks will touch. For Web tasks, read `.agents/skills/references/web-architecture-gate.md`; for complex Web feature structure or file splitting, read `.agents/skills/references/web-file-responsibility-and-feature-structure.md`. For API tasks, read `.agents/skills/references/api-architecture-gate.md`. For Core/Plugin tasks, read `.agents/skills/references/core-and-plugin-architecture-gate.md`. For SDK tasks, read `.agents/skills/references/core-and-plugin-architecture-gate.md`.

5. **Run engineering quality gate**

   Before changing files, check whether the artifacts and local rules answer:
   - Which module owns each responsibility?
   - Which directories and files will be created or modified, and what does each own?
   - What core models, DTO/schema/API/event/config/database fields are expected?
   - What existing code or shared capability should be reused?
   - What is the data flow, state source, error path, and recovery path?
   - What frontend component/state boundaries or backend service/repository/port boundaries are required?
   - What validation must be run after each meaningful slice?
   - For Web tasks, whether artifacts specify route, app runtime, API/BaseApi/FeatureApi, query/mutation, business hook, component, README, Chinese comment, and directory grouping boundaries.
   - For complex Web tasks, whether artifacts name concrete route, api, contracts, query keys, queries, mutations, hooks, components, types, utils, and README files.

   Pause if the answer is missing or contradictory. Suggest updating proposal/design/tasks/specs in the same change rather than guessing in implementation.

6. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Dynamic instruction from CLI

7. **Implement tasks (loop until done or blocked)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Mark task complete in the tasks file: `- [ ]` → `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

8. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest archive
   - If paused: explain why and wait for guidance

**Output During Implementation**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...implementation happening...]
✓ Task complete

Working on task 4/7: <task description>
[...implementation happening...]
✓ Task complete
```

**Output On Completion**

```
## Implementation Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete ✓

### Completed This Session
- [x] Task 1
- [x] Task 2
...

All tasks complete! Ready to archive this change.
```

**Output On Pause (Issue Encountered)**

```
## Implementation Paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>
3. Other approach

What would you like to do?
```

**Guardrails**
- Keep going through tasks until done or blocked
- Always read context files before starting (from the apply instructions output)
- Always run the engineering quality gate before implementation
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements - don't guess
- Use contextFiles from CLI output, don't assume specific file names

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
