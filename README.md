# AIAgentSkills

A collection of custom skills for Claude Code — enabling AI agents to perform complex developer tasks autonomously.

---

## Skills

### `api-flow-debugger` — v0.2.0

Debug any API endpoint by tracing the full request flow — from curl to response — **without modifying a single line of source code**.

**When to use:**
- An endpoint returns an error (4xx, 5xx) and you don't know why
- The response returns unexpected or incorrect data
- The API is slow and you suspect N+1 queries or a bottleneck
- You want to understand exactly which middleware and services a request passes through
- You want a **build health check** before running the server

**Supported stacks:** Node.js (Express, Fastify, NestJS), Python (FastAPI, Django, Flask), Go (Gin, Fiber), **C# .NET** (ASP.NET Core), Java/Spring Boot, PHP/Laravel, Ruby/Rails

**What's new in v0.2.0:**
- **Phase 2.5 — Build Verification**: compile-checks the project before starting the server; prompts to abort or continue if the build fails
- **ORM SQL Logging — always-on**: appends the right env vars per ORM so every SQL query appears in the log (EF Core, SQLAlchemy, TypeORM, Prisma, Hibernate, Rails AR)
- **Precise log parsing**: ANSI-stripping pre-processor → canonical clean log; anchored per-framework patterns replace naive `grep SELECT|INSERT` (eliminates false positives from stack traces and JSON request bodies); ripgrep multiline for multi-line query blocks
- **Rich DB Queries dashboard**: interactive table with expandable rows, CSS-only SQL syntax highlight, filter (All / Slow / N+1), sort, search, copy-SQL button, timeline strip, N+1 shape-group color coding

### `testing-explorer` — v0.1.0

A **Test Explorer that lives inside Claude Code's Preview panel**. Discovers the test tree, runs tests, classifies failures with a root cause, and collects coverage automatically — solving the problem that test projects are otherwise invisible in Claude Code and can't be run/checked at a glance.

**When to use:**
- You want to *see* your test tree (project → suite → test) inside Claude Code
- Run all tests, or **re-run only the failed ones**
- Understand **why** a test failed (assertion / exception / timeout / setup / Playwright selector) with the exact `file:line`
- Get **code coverage** with zero setup

**Supported stacks:** **.NET** (xUnit / NUnit / MSTest via `dotnet test`) and **Playwright** (`npx playwright test`)

**Highlights:**
- **Renders in the Preview panel** via `.claude/launch.json` + the Claude Preview MCP — not an external browser
- **Modes**: discovery (list only, no execution), full run, re-run-failed
- **Automatic .NET coverage** — uses `coverlet.collector` if present, otherwise auto-provisions a repo-local `dotnet-coverage` tool (no prompt, never global); parses Cobertura into overall + per-file bars
- **Playwright coverage**: suggest-only — never modifies your project; shows N/A + how-to-enable when not configured
- **Failure root-cause analysis**: classifies each failure and extracts the first user-code `file:line`
- Interactive dashboard: collapsible tree (✅/❌/⏭/◌), filter All/Failed/Skipped, search, click-to-expand failure detail with expected/actual diff

### `agent-forge-team` — v0.2.0

Assemble a **crew of specialized agents** that **executes** a plan — writing real code, running
real commands, and staying in sync through shared interface contracts and a structured impact
system. Provide a plan, a goal, or a **ticket URL** and the team builds it.

**When to use:**
- You have a plan (or a high-level goal) spanning multiple files, layers, or domains
- You want agents to work in parallel, not one at a time
- You have a ticket (GitHub Issue, Linear, Jira, Azure DevOps) and want the team to execute it
- Non-functional requirements (security, pagination, auth) must not be forgotten before coding begins
- You need a full audit trail: what was built, what drifted, what changed across agents, and how to roll back

**Key properties:**
- **Ticket Ingestion Mode** — paste a ticket URL (GitHub, Linear, Jira, ADO) and the skill fetches the ticket, collects all subtasks recursively, maps them to the wave system, and updates ticket statuses live as agents complete work
- **Interface-first parallelism** — an Interface Definer locks all contracts (TypeScript interfaces, API shapes, DB schema, component props) upfront, collapsing what would be 7+ sequential waves into 3
- **Sentinel** (mandatory pre-execution) — surfaces security gaps, missing steps, file conflicts, and NFRs *before* any code is written; its findings shape the interface contracts
- **Wave Reviewer** — after each wave, a dedicated agent checks cross-agent consistency and interface conformance before the build runs
- **Critical Issue Gate** — agents surface unexpected problems via `CRITICAL ISSUES FOUND` in their output; Leader resolves them before the next wave
- **Impact Ripple System** — when one agent changes a contract at runtime, future-wave agents receive a structured briefing automatically
- **Lazy model escalation** — Leader writes detailed Implementation Briefs so implementers start at `haiku`; escalates to `sonnet` only on partial/blocked returns
- **Rollback snapshot** per wave (git-stash or branch) with partial-rollback support + automatic ticket-state revert
- **Archaeology Agent** — post-execution narrative of what was built, why, and what a future maintainer must know
- **Interactive HTML report** — wave timeline, impact registry, Sentinel findings, plan drift log, delivery summary

Invoke with `/agent-forge-team` or natural phrases like *"execute this plan with agents"*,
*"implement these steps with a team"*, *"build this with a multi-agent crew"*,
*"execute ticket ENG-123"*, *"run this GitHub issue with agents"*.

### `agent-debate-team` — v0.1.0

Assemble a **team of specialized agents** that independently propose, then
**debate**, then converge on the best solution to a hard or open-ended problem —
coordinated by a **Leader** (the main session) that keeps everyone on-goal,
resolves conflicts, and produces a written decision plus an interactive HTML
report.

**When to use:**
- A hard/ambiguous problem benefits from multiple competing perspectives
- You want structured argument (proposer vs. devil's-advocate vs. domain expert) instead of a single take
- You need a recorded decision with rationale, rejected alternatives, and dissent
- You want guaranteed termination — **no infinite debate** — with live visibility into each round

**Key properties:**
- **Leader = main session**, team members = stateless one-shot subagents (no nested orchestration)
- **Conceptual demos only** — design sketches / pseudo-code / trade-off analysis as evidence (no code execution)
- **Loop-prevention gate** — hard round cap + convergence + stagnation + force-decision
- **Live transparency** — per-round digest of candidate solutions, each agent's position, and cross-review
- **Blind-Spot Hunter** — a mandatory default agent that surfaces unstated open questions, NFRs, missing docs, and downstream impacts
- **Per-role model tiering** — `opus`/`sonnet`/`haiku` assigned by cognitive load, user-overridable
- User chooses debate intensity (Lean / Balanced / Deep) at invocation

Invoke with `/agent-debate-team` or natural phrases like *"build a team of
agents to debate the best approach for X"*.

### `skill-release` — v0.1.0

Automates the **full 7-step release checklist** for any skill in this project — so no step is ever skipped.

**When to use:**
- You've created or updated a skill and want to publish it in one shot
- You want to ensure `.skill` packaging, local deploy, README updates, commit, and push all happen without manual prompting

**What it does:**
- Packages `skills/<name>/` into `<name>.skill` (ZIP via Python — works on Windows where `Compress-Archive` rejects `.skill` extensions)
- Deploys to `.claude/skills/<name>/`
- Updates README: Skills section, Release Notes (prepends dated entry), Project Structure (adds directory tree)
- Commits with the standard `feat(<name>): v<X.Y.Z> — <summary>` pattern
- Pushes to `master`

Invoke with `/skill-release` or *"release skill \<name\>"*, *"package and publish \<name\>"*.

### `skill-to-local` — v0.1.0

Syncs one or all skills from this project's `skills/` directory into the **global `~/.claude/skills/`** — making them available in any Claude Code session on this machine.

**When to use:**
- After releasing a skill, you want it available globally (not just in this project)
- You want to install all skills at once after cloning this repo

**What it does:**
- Copies `skills/<name>/` → `~/.claude/skills/<name>/` (force-overwrites stale copies)
- Verifies `SKILL.md` exists at destination
- Supports single-skill or all-skills mode

Invoke with `/skill-to-local` or *"sync \<name\> globally"*, *"install all skills globally"*, *"cài skill vào global"*.

---

## Installation

Skills live in `.claude/skills/` — Claude Code auto-discovers them when you start a session in this directory.

```bash
cd /your/path/to/AIAgentSkills
claude
```

No additional setup required.

---

## Using `api-flow-debugger`

### Step 1 — Invoke the skill

In a Claude Code session, type:

```
/api-flow-debugger
```

Or just describe what you need in natural language — Claude will pick it up automatically:
> *"debug this endpoint for me"*
> *"why is this curl returning 500?"*
> *"trace the request flow for this API"*

### Step 2 — Provide a curl command

Paste the curl command for the endpoint you want to debug:

```bash
# Example 1 — endpoint returning 500
curl http://localhost:5000/api/users/abc

# Example 2 — POST with a request body
curl -X POST http://localhost:3000/api/orders \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"productId": 42, "quantity": 2}'

# Example 3 — a bare URL works too; the skill will fill in missing headers
curl http://localhost:8080/api/v1/users?active=true
```

> **The curl doesn't need to be complete.** The skill auto-detects missing parts (Content-Type, Accept header, port) and asks for clarification only when necessary (e.g. token placeholders like `<TOKEN>`).

### Step 3 — The skill runs automatically

The skill will:

1. **Parse & validate** the curl — add missing headers, prompt for any token placeholders
2. **Detect the tech stack** — reads `package.json`, `*.csproj`, `go.mod`, etc.
3. **Map the code flow** — locates route → middleware → handler → service → DB in order
4. **Phase 2.5 — Build verification** — compile-checks with a non-mutating command (`dotnet build --no-restore`, `npx tsc --noEmit`, `go build -o /dev/null`, …); prompts `[abort/continue]` on failure
5. **Start the dev server** in debug mode using environment variables only (no code changes); ORM SQL logging always enabled
6. **Execute the curl** with `-v` to capture full HTTP details and timing
7. **Analyze** — strips ANSI codes, applies anchored log patterns, extracts structured query list, detects N+1 / slow queries / DB-bound bottleneck
8. **Generate an HTML report** and **open it automatically in your browser**

### Step 4 — Review the HTML Report

The report is saved as `debug-report-YYYYMMDD-HHmmss.html` and opens automatically. It includes:

| Section | Contents |
|---------|----------|
| **Build Status** | Build command, duration, pass/fail badge, error summary, last-30-lines output tail |
| **Request** | Enhanced curl command, method, URL, headers, body |
| **Checkpoint Trace** | Visual ✅/❌ timeline per step with file:line |
| **HTTP Response** | Status code, response headers, formatted body |
| **Timing** | Bar chart: connect / server processing / download |
| **DB Queries** | Interactive table — filter All/Slow/N+1, sort, SQL search, timeline strip, expandable rows with syntax-highlighted SQL, copy button, N+1 shape-group color grouping |
| **Performance** | N+1 queries, DB-bound bottleneck ratio, slow queries with durations |
| **Root Cause** | Exact description of what went wrong and where |
| **Suggested Fix** | Concrete, actionable code fix |

---

## Quick Test with the Sample Project

A **C# .NET 8 + EF Core + SQLite** sample is included with intentional test scenarios covering all skill features:

```bash
cd samples/dotnet-web-api-sample
dotnet restore
ASPNETCORE_ENVIRONMENT=Development dotnet run
# Server listens at http://localhost:5000
```

| Scenario | Endpoint | Expected skill output |
|---|---|---|
| Healthy baseline | `GET /api/healthy-user/1` | 200, 1 query, no flags |
| N+1 detection | `GET /api/users-with-orders` | 200, 21 queries, N+1 flagged |
| N+1 fixed | `GET /api/users-with-orders-optimal` | 200, 2–3 queries (single JOIN) |
| Slow query | `GET /api/slow-search?q=User` | 200, slow query >100ms flagged |
| Runtime error | `GET /api/users/abc` | 500, InvalidCastException traced |
| Build fail | rename `BrokenEndpoint.cs.broken` → `.cs`, rerun | Phase 2.5 prompts abort/continue |

Paste any of the above curls into the skill to see a full debug report.

**Build-fail test:**
```bash
# Activate the broken file → forces Phase 2.5 to fail
mv samples/dotnet-web-api-sample/BuildFailDemo/BrokenEndpoint.cs.broken \
   samples/dotnet-web-api-sample/BuildFailDemo/BrokenEndpoint.cs

# Restore when done
mv samples/dotnet-web-api-sample/BuildFailDemo/BrokenEndpoint.cs \
   samples/dotnet-web-api-sample/BuildFailDemo/BrokenEndpoint.cs.broken
```

---

## Project Structure

```
AIAgentSkills/
├── .claude/
│   ├── settings.json
│   └── skills/
│       ├── api-flow-debugger/         ← deployed copy (auto-loaded by Claude Code)
│       │   ├── SKILL.md               ← main workflow (Phases 1–6 + 2.5)
│       │   ├── assets/
│       │   │   └── report-template.html
│       │   └── references/
│       │       ├── build-verification.md    ← per-stack build commands + error parsing
│       │       ├── debug-env-vars.md        ← debug start commands + ORM SQL logging
│       │       ├── flow-mapping-patterns.md ← grep patterns to find routes/handlers
│       │       ├── log-parsing.md           ← ANSI strip, anchored regex, multiline
│       │       ├── performance-analysis.md  ← N+1, structured extraction, bottlenecks
│       │       └── trace-report-format.md  ← text fallback + scenario examples
│       └── agent-debate-team/         ← deployed copy (auto-loaded by Claude Code)
│           ├── SKILL.md               ← Leader workflow (Phases 1–7 + loop-prevention gate)
│           ├── assets/
│           │   └── report-template.html
│           └── references/
│               ├── orchestration.md         ← Leader=main-thread, parallel spawn, model tiering
│               ├── debate-protocol.md       ← rounds, loop-prevention, decision rules, dissent
│               ├── roles.md                 ← role catalog + mandatory Blind-Spot Hunter
│               └── state-management.md      ← session dir schema + rolling-summary rule
│       ├── testing-explorer/           ← deployed copy (auto-loaded by Claude Code)
│       │   ├── SKILL.md                ← 7-phase workflow
│       │   ├── assets/
│       │   │   └── test-report-template.html  ← dashboard shown in Preview panel
│       │   └── references/
│       │       ├── dotnet-test.md       ← discovery/run/rerun + TRX parsing
│       │       ├── playwright-test.md   ← list/JSON reporter/--last-failed
│       │       ├── result-parsing.md    ← unified model + failure classification
│       │       ├── coverage.md          ← coverlet/dotnet-coverage auto-provision
│       │       └── preview-panel.md     ← launch.json + preview_* orchestration
│       └── agent-forge-team/           ← deployed copy (auto-loaded by Claude Code)
│           ├── SKILL.md                ← 8-phase execution workflow
│           ├── assets/
│           │   └── report-template.html ← dark-theme HTML report (10 sections)
│           └── references/
│               ├── orchestration.md     ← Leader=main-thread, Implementation Brief, lazy escalation
│               ├── roles.md             ← Sentinel, Interface Definer, Wave Reviewer, Verifier, Archaeology, Implementer
│               ├── execution-protocol.md ← dependency graph, interface-first parallelism, Impact Ripple, rollback
│               ├── state-management.md  ← session dir schema, all file formats, rolling-wave-summary rule
│               └── ticket-ingestion.md  ← URL detection, MCP tools per system, field mapping, wave mapping, real-time status updates
│       ├── skill-release/              ← deployed copy (auto-loaded by Claude Code)
│       │   └── SKILL.md               ← 6-phase release checklist automation
│       └── skill-to-local/            ← deployed copy (auto-loaded by Claude Code)
│           └── SKILL.md               ← 3-phase global skill sync
├── skills/                            ← source-of-truth mirror of .claude/skills/
│   ├── api-flow-debugger/
│   ├── agent-debate-team/
│   ├── testing-explorer/
│   ├── agent-forge-team/              ← includes references/ticket-ingestion.md (v0.2.0)
│   ├── skill-release/
│   └── skill-to-local/
├── samples/
│   ├── dotnet-web-api-sample/         ← .NET 8 + EF Core + SQLite test project
│   ├── dotnet-web-api-sample.Tests/   ← xUnit fixture for testing-explorer
│   └── playwright-sample/             ← offline Playwright fixture for testing-explorer
│       ├── Controllers/
│       │   └── DebugTestController.cs ← 4 test endpoints
│       ├── Services/DebugTestService.cs
│       ├── Data/
│       │   ├── AppDbContext.cs
│       │   └── DbSeeder.cs            ← seeds 20 users × 5 orders
│       ├── BuildFailDemo/
│       │   └── BrokenEndpoint.cs.broken  ← rename to .cs to trigger Phase 2.5 fail
│       └── README.md
├── api-flow-debugger.skill            ← distributable package (ZIP)
├── agent-debate-team.skill            ← distributable package (ZIP)
├── testing-explorer.skill             ← distributable package (ZIP)
├── agent-forge-team.skill             ← distributable package (ZIP)
├── skill-release.skill                ← distributable package (ZIP)
├── skill-to-local.skill               ← distributable package (ZIP)
├── CLAUDE.md                          ← release checklist + project conventions
└── README.md
```

---

## Adding a New Skill

1. Create the directory: `.claude/skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: skill-name
   description: This skill should be used when... (third-person, include specific trigger phrases)
   version: 0.1.0
   tools: Read, Glob, Grep, Bash
   ---
   ```
3. Restart your Claude Code session to load the new skill.
4. Mirror the skill into `skills/<skill-name>/` (source of truth for packaging).

---

## Release Notes

### 2026-05-19 — `agent-forge-team` v0.2.0

**New: Ticket Ingestion Mode — paste a ticket URL instead of writing a plan**

- **Three plan input modes**: structured task list (existing), high-level goal / Plan Derivation Mode (existing), or **ticket URL / ticket ID** (new)
- **Supported systems**: GitHub Issues / PRs, Linear issues, Jira (Atlassian Cloud + self-hosted), Azure DevOps work items
- **Recursive subtask collection**: fetches the ticket + all subtasks to depth 2, deduplicates cross-referenced children, presents a `TICKET INGESTION SUMMARY` for user confirmation before executing
- **Field mapping**: title → plan name, description + acceptance criteria → Goal + Success Criteria, labels/components → tech stack hints, subtasks → T-IDs with `[source: <ticket-ID>]` annotations, priority/milestone → Hard Constraints
- **Tech stack detection**: keyword scan of labels + description prefix against 30+ framework/library names
- **Ticket-derived wave mapping**: explicit ordering links → hard edges; infra/foundation subtasks → Wave 1; E2E subtasks → last wave; coarse subtasks with children → wave-group labels; everything else → Wave 2 parallel; max 8 Implementer roles per wave
- **Real-time ticket status updates**: as agents complete work, the Leader calls MCP update tools to push status changes live — child tickets → "In Progress" when wave starts, "Done" when T-ID completes; parent → "In Progress" at first wave, "Done" when all tasks finish; all updates are best-effort (failures logged, execution never halted)
- **Pre-execution state snapshot**: records current states of all tickets before Wave 1 starts; used to revert states on rollback
- **Graceful degradation**: MCP unavailable → ask user to paste content manually; Jira/Linear state IDs unresolvable → skip sync + log; update failures → log and continue
- New reference file: `references/ticket-ingestion.md` — URL detection patterns, MCP tool names and ToolSearch load commands per system, field mapping table, recursion algorithm, wave mapping classification, real-time update hooks, fallback procedures

### 2026-05-17 — `skill-release` + `skill-to-local` v0.1.0 (initial release)
- `skill-release`: automates the full 7-step release checklist (package → deploy → README × 3 → commit → push)
- `skill-release`: Python-based ZIP packaging avoids Windows `Compress-Archive` `.skill` extension rejection
- `skill-release`: updates all three README sections (Skills, Release Notes, Project Structure) in one pass
- `skill-to-local`: syncs one or all skills from `skills/` to global `~/.claude/skills/` in a single command
- `skill-to-local`: supports single-skill and all-skills modes; verifies destination after each copy
- Both skills are self-contained (single SKILL.md, no references/ or assets/)

### 2026-05-17 — `agent-forge-team` v0.1.0 (initial release)

**New skill: multi-agent plan execution with interface-first parallelism**

- **8-phase workflow**: intake & plan derivation → team design → Sentinel pass → Interface Definer → wave execution loop → synthesis → HTML report → cleanup
- **Interface-first parallelism**: Interface Definer agent defines all contracts (API shapes, TypeScript interfaces, DB schema, component props) before any implementation — collapses 7+ sequential dependency waves into 3 parallel waves
- **Sentinel** (mandatory, pre-Interface): surfaces non-functional risks (security, performance, compliance, observability), missing plan steps, file conflict predictions, and downstream blast radius; findings feed directly into Interface Definer so contracts are complete before coding starts
- **Wave Reviewer** (post-wave, pre-Verifier): semantic cross-check — cross-agent consistency, interface contract conformance, undeclared cascading impacts; outputs `PROCEED / CORRECT-AND-PROCEED / HALT`
- **Critical Issue Gate**: agents declare `CRITICAL ISSUES FOUND` in their output contract; Leader runs a scan after every wave and resolves via `patch-on-main-thread`, `re-run-affected-tasks`, or `ask-user` before advancing
- **Impact Ripple System**: append-only `impact-registry.md`; after each wave, Leader writes ripple briefings injected into the next wave's Implementation Briefs; three conflict tiers: Predicted (Sentinel) → Runtime deviation (ripple) → Integration failure (rollback)
- **Implementation Brief pattern**: Leader writes per-role briefs (interfaces, pattern reference, error handling, impact briefing) before spawning agents; richer brief → cheaper model (`haiku`)
- **Lazy model escalation**: Implementers start at `haiku`; escalate to `sonnet` on partial/blocked with a reasoning gap; Integration Verifier always `haiku`; Sentinel/Interface Definer/Wave Reviewer always `sonnet`
- **Plan Drift Rule**: decision table for partial/blocked tasks — 6 blocker types mapped to Leader action (autonomous fix vs. `AskUserQuestion`)
- **Plan Derivation Mode**: if user provides a goal instead of a structured plan, Leader derives a numbered task list and confirms with user before proceeding
- **Rollback snapshots**: `git stash` or branch per wave with partial-rollback (restore only failing-task files)
- **Archaeology Agent**: post-execution `sonnet` agent reads git diff + wave summaries → writes `DELIVERY-NARRATIVE.md` (decisions, drift, maintainer notes, open risks)
- **Interactive HTML report**: nav bar with 10 sections — task list with sentinel-insert tags, team roster with model badges, interface contracts, sentinel risk cards, collapsible wave timeline with critical issue blocks, sortable impact registry, plan drift log, narrative, delivery + rollback map
- **Session state**: `.agent-forge/<slug>/` with `interfaces/`, `briefs/`, `waves/`, `impacts/`, `snapshots/`, rolling wave summaries, append-only registries

Invoke with `/agent-forge-team` or *"execute this plan with agents"*, *"build this with a multi-agent crew"*.

---

### 2026-05-16 — `testing-explorer` v0.1.0 (initial release)

- New skill: a Test Explorer rendered **inside Claude Code's Preview panel** (via `.claude/launch.json` + Claude Preview MCP), not an external browser
- 7-phase workflow: detect stacks → discovery → build verify → run → parse/classify → render panel → re-run-failed
- Stacks: **.NET** (`dotnet test`, TRX parsing) and **Playwright** (`--reporter=json`, `--last-failed`)
- Modes: `discovery` (no execution), `full`, `rerun-failed` (merges results, live-reloads the panel)
- **Automatic .NET coverage**: `coverlet.collector` if referenced, else repo-local `dotnet-coverage` auto-provision (no prompt, never `--global`); Cobertura parsed into overall + per-file bars
- **Playwright coverage**: suggest-only; never edits the project — shows N/A + `how_to_enable`
- Failure classification: assertion / exception / timeout / setup / selector / navigation, with first user-code `file:line` and a one-line likely cause
- Interactive dashboard (dark theme matching `api-flow-debugger`): collapsible test tree, All/Failed/Skipped filter, search, expandable failure cards with expected/actual diff, coverage bars
- References: `dotnet-test.md`, `playwright-test.md`, `result-parsing.md`, `coverage.md`, `preview-panel.md`
- Sample fixtures: `samples/dotnet-web-api-sample.Tests` (xUnit — pass/fail/skip/theory, no coverlet to exercise auto-provision) and `samples/playwright-sample` (offline `setContent` specs with a passing + failing test)

---

### 2026-05-16 — `agent-debate-team` v0.1.0 (initial release)

**New skill: multi-agent structured debate with guaranteed termination**

- **7-phase workflow**: intake & config → team design → Round 0 (parallel, independent proposals) → debate rounds → leader synthesis → HTML report → cleanup
- **Leader = main session**: the orchestrating Claude session coordinates all agents; team members are stateless one-shot subagents with no nested delegation
- **Blind-Spot Hunter** (mandatory default): surfaces unstated requirements, NFRs, missing docs, and downstream impacts before debate begins — outputs a ranked gap list, not a solution
- **Loop-Prevention Gate**: hard round cap + convergence + stagnation + irreconcilable-conflict force-decision — guarantees termination on every run
- **Per-role model tiering**: `opus` for Architect/Proposer and Devil's-Advocate; `sonnet` for Domain Expert, Pragmatist, Evaluator, Blind-Spot Hunter; `haiku` for mechanical formatting
- **Evidence-weighted decision rules**: `evidence-weighted` / `criteria-weighted` / `leader-call` — user-selectable at invocation
- **Live transparency digest**: per-round output of candidate solutions, each agent's position, cross-review results, and gate decision
- **Debate presets**: Lean (2–3 agents, 2 rounds), Balanced (3–5, 3 rounds), Deep (4–6, 5 rounds)
- **On-disk session state**: rolling summaries prevent context bloat; raw round returns persisted for audit
- **Interactive HTML report**: GitHub Dark theme dashboard with team roster, gap list, debate timeline, conflict map, decision log, dissent log, and final solution — self-contained, re-openable at any time
- **`agent-debate-report-*.html`** and **`.agent-team/`** added to `.gitignore` (runtime artifacts, not committed)

Invoke with `/agent-debate-team <problem statement>` or natural phrases like *"build a team of agents to debate the best approach for X"*.

---

### 2026-05-15 — `api-flow-debugger` v0.2.0

**New: Phase 2.5 — Build Verification**
- Compile-checks the project before starting the server using a non-mutating build command per stack (`dotnet build --no-restore`, `npx tsc --noEmit`, `go build -o /dev/null`, `mvn -q compile`, …)
- Dependency presence check per stack before building
- On failure: prints the first error line + last 30 build output lines, then prompts `[abort/continue]`
- `abort` → generates a partial HTML report with the Build Status section populated; Phases 3–5 skipped
- `continue` → proceeds with a warning that the running binary may not reflect current source
- New reference: `references/build-verification.md` — commands, error regexes, Win/Unix equivalents, report object schema

**New: ORM SQL Logging — always-on**
- Phase 3 now appends ORM-level SQL logging env vars to the server start command automatically
- Covered: EF Core, SQLAlchemy, TypeORM, Prisma, Hibernate, Rails ActiveRecord
- Documented limitations for stacks that require code changes (GORM, Django, Sequelize, Laravel default, Mongoose) with per-stack workarounds
- Updated reference: `references/debug-env-vars.md` — new `## ORM SQL Logging` section

**New: Precise Log Parsing**
- Pre-processing pipeline: ANSI escape code stripping → CRLF normalization → canonical `server-debug.clean.log`
- All pattern matching now runs on the clean log, not the raw file
- Anchored per-framework patterns replace naive `grep "SELECT\|INSERT"` — eliminates false positives from stack traces, JSON request bodies, SQL comments, CLI echo lines
- Tool preference: `rg` (ripgrep, multiline + PCRE2) → `grep -E` (Unix) → `Select-String` (PowerShell) → `findstr` (last resort)
- Multi-line query handling: `rg -U --pcre2` with lookahead, plus `awk` fallback
- Cross-platform wrappers: `parse_log()` (bash) and `Parse-Log` (PowerShell)
- New reference: `references/log-parsing.md`

**New: Structured DB Query Extraction**
- Phase 4 now produces a `db_queries[]` array: `{ index, sql, sql_raw, params, duration_ms, timestamp, checkpoint_id, is_slow, shape_group }`
- SQL normalization (literals → `?`, whitespace collapse) → SHA-1 prefix as `shape_group` for N+1 grouping
- Checkpoint correlation via timestamp windowing (or log-line order fallback)
- `db_summary`: `{ total_queries, unique_shapes, total_db_ms, slow_query_count, n_plus_one_detected, db_bound_ratio }`
- Updated N+1 threshold: `same_shape_count >= 5 AND same_shape_count >= 0.5 × total_queries`
- DB-bound bottleneck ratio: `db_total_ms / server_processing_ms > 0.6`
- Updated reference: `references/performance-analysis.md` — new sections for extraction, normalization, checkpoint correlation, per-query rules

**New: Rich DB Queries Dashboard (HTML report)**
- Summary mini-cards: total queries / unique shapes / total DB time / slow count / N+1 status
- Filter buttons: All | Slow only (>100ms) | N+1 group only
- Sort dropdown: by order / by duration desc / by checkpoint
- SQL text search input (live filter)
- Timeline strip: one proportional bar per query (gray/yellow/red by severity); click bar → scroll + highlight row
- Expandable query rows: full SQL with CSS-only syntax highlighting (keywords, strings, numbers, functions), params, copy-SQL button
- N+1 shape groups: shared pastel left-border color for repeated-shape queries (6-color cycle)
- Build Status collapsible section: command, duration, pass/fail badge, error banner, output tail
- New placeholders: `{{BUILD_STATUS_BADGE}}`, `{{BUILD_JSON}}`, `{{DB_QUERIES_JSON}}`, `{{DB_TIME_MS}}`, `{{DB_UNIQUE_SHAPES}}`, `{{DB_SLOW_COUNT}}`

**Sample project: `dotnet-web-api-sample` expanded**
- Added EF Core 8 + SQLite (`Microsoft.EntityFrameworkCore.Sqlite`)
- New entities: `Order` with `UserId` FK → `User`; seeded with 20 users × 5 orders
- 4 new test endpoints covering every skill scenario (see Quick Test table above)
- `BuildFailDemo/BrokenEndpoint.cs.broken` — rename to `.cs` to trigger Phase 2.5 fail path
- Updated `.gitignore` — excludes SQLite runtime files, build logs, generated reports

---

### 2026-05-14 — `api-flow-debugger` v0.1.0 (initial release)

- 6-phase workflow: parse curl → detect stack → map flow → start server → execute curl → analyze → HTML report
- Checkpoint tracing: Router → Middleware → Handler → Service → Data layer
- Per-framework debug start commands via env vars (no source code modification)
- N+1 detection from log grep counts + response array size heuristic
- Slow query detection by log regex per ORM
- HTML report with checkpoint timeline, HTTP details, timing bar chart, performance flags, root cause, suggested fix
- Text fallback report format for non-browser environments
- `.NET` sample project with `InvalidCastException` and basic N+1 scenario
