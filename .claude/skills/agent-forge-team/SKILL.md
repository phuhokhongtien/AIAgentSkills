---
name: agent-forge-team
description: This skill should be used when the user has a plan (a list of tasks or implementation steps) and wants a team of agents to EXECUTE it together — writing real code, running commands, and coordinating on shared files. Use when the user says "execute this plan with agents", "implement these steps with a team", "build this with a multi-agent crew", "run my implementation plan", "forge team", or "squad thực thi kế hoạch". Also use when the user provides a high-level goal (no plan yet) and wants agents to derive and execute a plan.
version: 0.2.0
tools: Read, Write, Edit, Glob, Grep, Bash, Agent, TodoWrite, AskUserQuestion
---

# Agent Forge Team

Assemble a crew of specialized agents that **executes** a plan — writing real code, running real
commands, and staying in sync through shared interface contracts and a structured impact system.
A Sentinel surfaces hidden risks before any code is written. An Interface Definer locks all
contracts upfront so implementers can work in parallel. A Wave Reviewer checks cross-agent
consistency after each wave. An Integration Verifier runs the build.

## Two non-negotiable constraints — read first

1. **The main Claude session running this skill IS the Leader.** Never delegate the
   orchestrator role to a subagent. Subagents spawned via the `Agent` tool cannot reliably
   spawn their own subagents, so a delegated leader cannot run the team. The Leader reasons
   directly in Phases 1, 2, 6, 7 and spawns team members via the `Agent` tool in Phases 3–5.
2. **Team members are stateless one-shot subagents.** Each `Agent` call has zero memory of
   prior calls. All continuity lives on disk. Every prompt must be self-contained — never
   assume an agent remembers anything not explicitly in its prompt.

See `references/orchestration.md` for the full model-tiering policy, parallel-spawning rules,
Implementation Brief format, and lazy-escalation protocol.

---

## Phase 1 — Intake & Configuration

### 1a — Capture the plan

Detect which of three input forms the user provided — check in this order:

- **Ticket URL or ticket ID** — a GitHub Issue / PR URL, Linear issue URL, Jira URL,
  Azure DevOps work item URL, or a plain ticket ID like `ENG-123` / `PROJ-456` →
  **Ticket Ingestion Mode** (see below).
- **Structured plan** — a numbered task list → use as-is, assign T-IDs if missing.
- **High-level goal** (no task list, no ticket URL) → **Plan Derivation Mode**: Leader
  reasons directly and produces a numbered task list, then shows it to the user for
  confirmation via `AskUserQuestion` before continuing. Do not proceed until confirmed.

#### Ticket Ingestion Mode

See `references/ticket-ingestion.md` for URL detection patterns, MCP tool names, field
mapping, subtask recursion, wave mapping rules, real-time status update hooks, and fallback
procedures.

Steps:
1. **Detect** — match the input against URL/ID patterns in the reference file. If a
   plain-ID (`PROJ-123`) is ambiguous between Jira and Linear, ask the user to confirm
   the system via `AskUserQuestion` before fetching.
2. **Load MCP schema** — all ticket-system tools are deferred; call `ToolSearch` before
   invoking any of them (e.g. `ToolSearch({ query: "select:mcp__github__get_issue" })`).
   Also pre-load the update tool for the detected system — it will be needed in Phase 5.
3. **Fetch ticket** — title, description, acceptance criteria, labels/components/tags,
   last 5 comments, and all subtasks recursively to depth 2. If deeper children exist,
   note them in `plan.md` assumptions and skip.
4. **Map fields** (full table in reference file):
   - title → plan name + slug
   - description + acceptance criteria → Goal + Success Criteria in `plan.md`
   - labels/components/tags → tech stack hints (keyword-matched)
   - subtasks → T-IDs with `[source: <ticket-ID>]` annotations
   - priority Critical/P0 → Hard Constraints entry
   - milestone/sprint → Hard Constraints deadline
5. **Present `TICKET INGESTION SUMMARY`** via `AskUserQuestion`:
   ```
   TICKET INGESTION SUMMARY
   Source: <system> — <URL>
   Title:  <title>
   Status: <open | closed | in-progress>   ← warn if already closed

   Goal derived: <2-3 sentence condensed description + acceptance criteria>
   Tech stack hints: <detected keywords or "none detected — will ask">
   Subtasks found: <N total>
     [T1] <title> (<source-ID>)
       [T1.1] <title> (<source-ID>)
     [T2] <title> (<source-ID>)
     ...
   Success criteria: <from acceptance criteria>
   Assumptions: <anything absent or truncated>

   Proceed with this plan, or edit the task list first?
   ```
   Wait for user confirmation or edits before continuing to 1b.
6. **Snapshot ticket states** — before Phase 5 Wave 1, read current states of the parent
   ticket and all child tickets; write to `.agent-forge/<slug>/ticket-states.md`. Used to
   revert states on rollback.
7. **Real-time status updates** (during Phase 5 execution):
   - When a wave starts → set all child tickets assigned to that wave to "In Progress";
     set parent to "In Progress" on the first wave.
   - When a T-ID is marked `done` → set the corresponding child ticket to "Done"/"Closed".
   - When all T-IDs across all waves are `done` → set parent ticket to "Done"/"Closed".
   - On rollback → revert affected tickets to their pre-execution states from the snapshot.
   - All updates are best-effort: log failures in `decisions.md` and continue. Never halt
     execution because a status sync failed.
8. **If MCP unavailable** — `AskUserQuestion`: "I cannot fetch <system> tickets
   automatically. Paste the ticket content here, or switch to Plan Derivation Mode."

Also capture (from ticket if available, otherwise ask):
- **Tech stack** — required for Sentinel and Interface Definer
- **Hard constraints** — must-not-break files, compliance requirements, deadline
- **Success criteria** — what "done" means: tests pass, CI green, manual smoke-test, etc.
- **Verification commands** — exact commands to run (`npm test`, `dotnet test`, `npx playwright test`)

### 1b — Configuration (AskUserQuestion)

Ask the user three questions (can be batched into one `AskUserQuestion` call):

| Question | Options | Default |
|---|---|---|
| Execution mode | `parallel` — Interface Definer unlocks max parallelism; `sequential` — one wave at a time for risky/unknown codebases | `parallel` |
| Gate style | `auto` — Leader gates between waves autonomously; `manual` — user approves each wave before it runs | `auto` |
| Rollback policy | `git-stash` — stash before each wave; `branch` — new branch per wave; `none` — user manages | `git-stash` |

### 1c — Create session directory and seed files

```bash
SLUG=$(echo "<short-plan-name>" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
SESSION=".agent-forge/$SLUG"
mkdir -p "$SESSION/interfaces" "$SESSION/briefs" "$SESSION/roles" \
         "$SESSION/waves" "$SESSION/impacts" "$SESSION/snapshots"
```

Seed `plan.md`, `config.md`, `impact-registry.md` (empty), `progress.md`.
Start a `TodoWrite` checklist: one item per phase, one per planned wave.

See `references/state-management.md` for exact file schemas.

---

## Phase 2 — Lead Designs Team & Dependency Graph

Reason directly (no subagent). Steps:

1. **Parse tasks** into a dependency graph. Detect:
   - *File-write*: Task B reads a file Task A creates/modifies → B depends on A
   - *Type/interface*: Task B imports a type/class Task A defines → B depends on A (resolved by Interface Definer in `parallel` mode)
   - *Data*: Task B processes data Task A seeds/migrates → B depends on A
   - *Explicit ordering cues* in the plan text
   - *Ticket ordering links*: if the plan came from Ticket Ingestion Mode and the ticket
     system provided explicit predecessor/dependency links (fetched in Phase 1a), treat
     these as hard ordering edges — they override heuristic classification.

2. **Separate runtime dependencies from code-level dependencies.**
   - *Runtime sequential* (must stay in Wave 1): DB migrations, infra setup, library installs
   - *Code-level* (resolved by Interface Definer in `parallel` mode): service imports entity type, component uses API response shape

3. **Design the wave structure** (default for `parallel` mode — 3 waves):
   - **Wave 1** — data/infra foundation (schema, migrations, scaffold — true runtime deps)
   - **Wave 2** — all application-layer implementers in parallel (services, API, frontend, tests)
   - **Wave 3** — E2E / integration tests (require running app)

   **Ticket-derived plans**: apply the wave mapping from
   `references/ticket-ingestion.md §Subtask → Wave Mapping` before the default.
   Infra/foundation subtasks → Wave 1; E2E subtasks → last wave; explicit ordering
   links → sequence; everything else → Wave 2 parallel. The 3-wave target still holds —
   ticket classification determines placement, not additional waves.
   Cap: maximum 8 Implementer roles per wave; merge smallest domain groups first if exceeded.

4. **Group Wave 2 tasks by domain** → assign one Implementer role per domain group.
   Domains: `data-layer`, `backend-services`, `backend-api`, `frontend-core`,
   `frontend-admin`, `tests`, `infra`. Merge small groups rather than create single-task roles.

5. **Assign file ownership explicitly** in each charter. Two agents writing the same file
   in the same wave is FORBIDDEN. Split ownership by specific filename if needed.

6. Write each `roles/<role>.md` charter (template in `references/roles.md`).

7. Write `dependency-graph.md` — task registry, wave assignments, file ownership map.

8. Print team roster + wave structure to the conversation.
   If `gate_style = manual`, ask user confirmation before Phase 3.

---

## Phase 3 — Sentinel Pass

**Sentinel runs BEFORE Interface Definer.** This is the value chain:
Sentinel makes the plan complete → Interface Definer makes contracts complete → Implementers don't get stuck.

Spawn ONE Sentinel agent. Prompt includes: plan, tech stack, dependency graph, codebase entry
points (glob the project root if a codebase exists). See `references/roles.md` for the
Sentinel charter and the exact output contract.

### Processing the Sentinel report

- **Blocker questions** → `AskUserQuestion` before any code is written
- **Critical / High risks** → insert mitigation tasks into `plan.md`, update dependency graph
- **File conflict predictions** → assign explicit file ownership in the affected role charters
- **Missing plan items** → insert into `plan.md` with a new T-ID (e.g. T3.5), re-run Phase 2 for affected waves

Forward all Sentinel findings to the Interface Definer prompt as "Sentinel requirements" so
NFRs and security concerns shape the contracts.

Print a Sentinel digest to the user before proceeding.

---

## Phase 4 — Interface Definer Pass

Spawn ONE Interface Definer agent. Prompt includes: complete post-Sentinel plan, tech stack,
dependency graph, full Sentinel report. See `references/roles.md` for the charter and output contract.

The Interface Definer produces:
- `interfaces/api-contracts.md` — REST/GraphQL endpoint shapes with auth, pagination, error codes
- `interfaces/service-interfaces.md` — TypeScript interfaces for all services (signatures + jsdoc, no implementation)
- `interfaces/db-schema.md` — DDL / entity definitions / migration specs
- `interfaces/component-contracts.md` — component prop types, emits, slots (if frontend tasks exist)

Leader writes the Interface Definer's output to the `interfaces/` directory. These files are
the **single source of truth** for all Implementers. No Implementer may invent an interface —
it must code to what is in `interfaces/`.

If no codebase or no frontend/backend split exists, produce only the relevant interface files.

---

## Phase 5 — Wave Execution Loop

Repeat for each wave W in sequence:

### 5a — Snapshot

```bash
# git-stash policy (default)
git stash push -m "agent-forge-${SLUG}-pre-wave-${W}" --include-untracked
git stash list | head -1 > ".agent-forge/${SLUG}/snapshots/wave-${W}.md"

# branch policy
git checkout -b "agent-forge-${SLUG}-wave-${W}"
echo "branch: agent-forge-${SLUG}-wave-${W}" > ".agent-forge/${SLUG}/snapshots/wave-${W}.md"
```

### 5b — Leader writes Implementation Briefs

Before spawning ANY Implementer, the Leader reads:
- Relevant `interfaces/` files for each role
- Analogous existing files in the codebase (to include as pattern references)
- `impacts/impact-registry.md` and `impacts/wave-(W-1)-ripple.md`

Then writes `briefs/<role>-brief.md` for each Implementer. Brief format and model-assignment
rules are in `references/orchestration.md`. Key principle: **the richer the brief, the cheaper
the model**. A haiku agent with a detailed brief outperforms a sonnet agent with a vague task.

### 5c — Spawn Implementers in parallel

Spawn all wave-W Implementers in a **single message** (multiple `Agent` calls). Each agent's
prompt = role charter + Implementation Brief + execution output contract. Agents have all tools:
Read, Write, Edit, Glob, Grep, Bash.

**Implementer output contract** (agents must return exactly these sections):

```
TASK COMPLETION REPORT — <role name> — Wave <W>

TASKS COMPLETED:
  T<N>: done | partial | blocked
    Files modified: <list>
    What was done: <one paragraph>
    Blockers (if partial/blocked): <description and what is needed>

FILES WRITTEN/MODIFIED:
  <path>: <one-line description of change>

IMPACT DECLARATIONS (routine cross-agent changes other roles must know about):
  <file or interface>: <what changed + what callers must do differently>
  Downstream tasks affected: <T-IDs>

CRITICAL ISSUES FOUND (unexpected problems that affect other agents or the plan):
  [SEVERITY: Critical|High] <issue description>
  Affects: <role / task / file>
  Recommendation: patch-on-main-thread | re-run-affected-tasks | ask-user
  (omit this section entirely if none found)

ASSUMPTIONS MADE: <any assumption about absent context>

VERIFICATION STEPS RUN:
  <command> → exit <code> | <summary of output>
```

### 5d — Critical Issue Scan

After ALL wave-W agents return, Leader reads every `CRITICAL ISSUES FOUND` section **first**,
before writing summaries or advancing:

- **No critical issues** → proceed to 5e.
- **`patch-on-main-thread`**: Leader applies the fix directly (main thread has all tools).
  Log in `decisions.md`. If the fix changes an interface → update `interfaces/<file>.md`.
- **`re-run-affected-tasks`**: Leader identifies conflicting agent outputs, applies fix or
  re-spawns only those tasks as a "correction sub-wave" (same wave number, suffix `-fix`).
  Updates `interfaces/` if a contract changed.
- **`ask-user`**: `AskUserQuestion` — surface the issue, present options, wait.

Real-time cross-agent notification during a wave is architecturally impossible (agents run
concurrently with zero shared memory). The four-layer defence is:
(1) Interface Definer contracts minimise need for mid-wave communication;
(2) `CRITICAL ISSUES FOUND` field surfaces issues in the return;
(3) Critical Issue Scan + Wave Reviewer resolve them before the next wave;
(4) Impact Ripple briefs future waves.

### 5e — Lazy Escalation

For each `partial` or `blocked` task:

| Blocker type | Leader action | Ask user? |
|---|---|---|
| Missing technical setup (library, config, scaffold) | Leader creates it on main thread, re-queues task | No |
| Reasoning gap (agent couldn't implement) | Re-spawn with `sonnet` + enriched brief | No |
| Missing runtime dependency | Leader runs the command | No |
| Interface ambiguity | Leader picks conservative interpretation, logs in `decisions.md` | No |
| Product / business decision | `AskUserQuestion` | Yes |
| Missing requirement changing user-visible behaviour | `AskUserQuestion` | Yes |

### 5f — Collect outputs + Update Impact Registry

Leader reads all Implementer outputs. For every Impact Declaration:
- Append to `impacts/impact-registry.md`
- Identify future-wave tasks affected
- Write `impacts/wave-W-ripple.md` (injected into Wave W+1 Implementation Briefs)
- If impact changes an interface → update `interfaces/<file>.md`

### 5g — Wave Reviewer

Spawn ONE Wave Reviewer (`sonnet`). Inject: all `waves/wave-W/<role>-output.md` files,
the `interfaces/` contracts, dependency graph, Sentinel report.
The Reviewer does NOT run commands — it reads and reasons.

**Wave Reviewer output contract:**

```
WAVE REVIEW — Wave <W>

CROSS-AGENT CONSISTENCY:
  PASS | FAIL
  - <role A> vs <role B>: consistent | conflict on <what>
    If conflict: <which is correct per interface contracts, and why>

INTERFACE CONTRACT CONFORMANCE:
  - <role>: conforms | deviates on <specific method/field/endpoint>
    Deviation: <what the agent did vs. what interfaces/ specifies>
    Severity: Breaking | Non-breaking | Style

UNDECLARED CASCADING IMPACTS:
  - <file or pattern changed without a declaration>
    Risk: <who is affected downstream>

INTERFACE UPDATE NEEDED:
  yes | no — if yes: <which interfaces/<file>.md + exact change>

RECOMMENDATION: PROCEED | CORRECT-AND-PROCEED (<specific fixes>) | HALT (<reason>)
```

Leader processes Wave Reviewer output:
- **`PROCEED`** → continue to 5h.
- **`CORRECT-AND-PROCEED`** → Leader applies corrections on main thread. Updates `interfaces/`
  if a contract deviation is found. Logs all changes in `decisions.md`. Then continues.
- **`HALT`** → surface to user via `AskUserQuestion`.
- **Interface Update Needed** → Leader updates `interfaces/<file>.md` before Wave W+1.

### 5h — Integration Verifier

Spawn ONE Integration Verifier (`haiku`). Inject: verification commands from `config.md`,
list of files changed in this wave, current working directory. Agent runs commands only.

**Integration Verifier output contract:**

```
INTEGRATION REPORT — Wave <W>

BUILD:  PASS | FAIL  → <command>  exit <code>
                        <first error line if failed>
TESTS:  PASS | FAIL | SKIPPED  → <N> passed, <M> failed, <K> skipped
        Failed: <test name — file:line>
LINT:   PASS | FAIL | N/A
REGRESSION RISK: <files changed that are touched by currently-failing tests>

RECOMMENDATION: PROCEED | ROLLBACK | PARTIAL-ROLLBACK (<task IDs>)
```

### 5i — Gate Decision

| Verifier recommendation | Leader action |
|---|---|
| `PROCEED` | Write `waves/wave-W/wave-summary.md`; continue to wave W+1 |
| `ROLLBACK` | Execute rollback (see below); surface to user; stop or retry |
| `PARTIAL-ROLLBACK` | Restore only failing-task files from snapshot; re-queue those tasks as sub-wave |

**Rollback execution:**
```bash
# stash policy
STASH=$(cat ".agent-forge/${SLUG}/snapshots/wave-${W}.md")
git stash pop  # or git checkout stash@{N} -- <specific files>

# branch policy
git checkout <base-branch>
git branch -D "agent-forge-${SLUG}-wave-${W}"
```

If `gate_style = manual`: print the **Wave Transparency Digest** and use `AskUserQuestion`
to ask user approval before wave W+1.

### Wave Transparency Digest (print after every wave)

Print to the conversation after every wave completes:
- Tasks completed / partial / blocked; escalations triggered
- Files changed (list)
- Critical issues found and how they were resolved
- Impact declarations + which future tasks were briefed
- Wave Reviewer verdict (PROCEED / corrections applied / halted)
- Integration: build ✓/✗, tests N passed M failed, lint ✓/✗
- Gate decision + rationale
- Rollback available at: `<stash ID or branch name>`

---

## Phase 6 — Lead Synthesis & Delivery

Reason directly (no subagent):

1. Verify all tasks in `plan.md` are marked done (or document partial/blocked with reasons).
2. Run the final verification suite once more, or instruct the user if commands are unavailable.
3. Write `DELIVERY.md`: what was built, what was deferred, residual risks, manual steps, rollback map.
4. Spawn **Archaeology Agent** (`sonnet`) — reads `git diff HEAD~<n>`, all
   `waves/wave-*/wave-summary.md`, and `impacts/impact-registry.md`. Produces a
   human-readable narrative:
   - What architectural decisions were made and why (from Implementer assumption logs)
   - Where the plan drifted from the original and why
   - What a future maintainer needs to know to work in this code safely
   - Open risks that were not resolved
5. Write `DELIVERY-NARRATIVE.md`.

---

## Phase 7 — Generate HTML Report & Auto-Open

Read `assets/report-template.html`, replace every `{{PLACEHOLDER}}` with report data
(JSON-encode complex objects, HTML-escape strings). Save as:

```
agent-forge-report-YYYYMMDD-HHmmss.html
```

in the current working directory. Auto-open by OS:

```bash
uname -s 2>/dev/null | grep Darwin && open "agent-forge-report-"*.html
uname -s 2>/dev/null | grep Linux  && xdg-open "agent-forge-report-"*.html
cmd.exe /c start "" "agent-forge-report-YYYYMMDD-HHmmss.html" 2>/dev/null
```

Print the report path to the user. Confirm it opened.

---

## Phase 8 — Cleanup

Confirm the wave summaries and `DELIVERY.md` captured everything important.
Then **ask the user** before pruning. Default keep list:
- `DELIVERY.md`, `DELIVERY-NARRATIVE.md`
- `impacts/impact-registry.md`
- `interfaces/` directory
- The HTML report

Offer to delete: `waves/`, `impacts/wave-*/`, `snapshots/`, `roles/`, `briefs/`.
**Never auto-delete** without explicit user confirmation.

---

## References

- `references/orchestration.md` — Leader=main-thread rule, parallel spawning,
  `subagent_type` matrix, model-tiering table, Implementation Brief format,
  lazy-escalation protocol, per-wave prompt template.
- `references/roles.md` — role catalog, charter template, fixed-role charters
  (Sentinel, Interface Definer, Wave Reviewer, Integration Verifier, Archaeology Agent),
  Implementer charter guide.
- `references/execution-protocol.md` — dependency graph format, interface-first
  parallelism rationale, Impact Ripple System schema, plan-drift rule table, rollback
  procedures.
- `references/state-management.md` — session directory schema, all file schemas,
  rolling-wave-summary rule, resource lifecycle.
- `assets/report-template.html` — HTML report template with `{{PLACEHOLDER}}`s.
- `references/ticket-ingestion.md` — URL/ID detection patterns (GitHub, Linear, Jira, Azure DevOps);
  MCP tool names and load-via-ToolSearch instructions per system; field mapping table; subtask
  recursion algorithm (depth 2, deduplication); domain keyword table; wave mapping rules for
  ticket-derived subtasks; real-time status update hooks + pre-execution state snapshot; fallback
  procedures when MCP is unavailable.
