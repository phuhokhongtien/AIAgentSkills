---
name: testing-strategy
description: >
  Use this skill when the user wants a testing strategy for their project,
  wants to audit existing tests, needs advice on what types of tests to write
  (unit, integration, API, UI/E2E, load, performance, automation, BDD),
  wants a mocking strategy, wants to understand the test pyramid vs trophy for
  their project, needs help integrating tests into CI/CD, wants to detect
  overlapping/redundant tests, or asks:
  "what should I test?", "how do I test this?", "is my testing good?",
  "what test types do I need?", "should I use mocks?", "how do I structure my tests?",
  "testing strategy", "test approach", "test plan", "test coverage gaps",
  "audit my tests", "testing advice", "best practices for testing",
  "how do I use mocks in unit tests?", "should I mock the database?",
  "BDD for my project", "given when then tests", "non-technical test specs",
  "overlap between tests", "redundant tests",
  "chiến lược test", "nên test gì", "mock như thế nào", "tránh overlap test".
version: 0.1.2
tools: Read, Write, Glob, Grep, Bash, AskUserQuestion
---

# Testing Strategy

A **Testing Strategist** that analyzes your project's codebase and produces a
project-specific testing strategy — covering unit, integration, API, UI/E2E,
load, performance, automation, and BDD. It detects test overlaps, maps external
dependencies to the right mock boundaries, and generates an interactive
dark-theme HTML report with a priority action list.

Distinct from `testing-explorer` (which **runs** tests). This skill **advises**
on what to write, how to structure it, and what to fix.

---

## Modes

| User intent | Mode |
|---|---|
| No/few tests, greenfield | `new-strategy` |
| Has tests, wants gap/quality assessment | `audit` |
| One specific concern ("how should I mock?", "BDD?") | `focused` |

**Scope granularity** (orthogonal to mode):

| Scope | Examples |
|---|---|
| `whole-project` | default when no target specified |
| `sub-project` | "auth service", "payment module", specific subdirectory |
| `class` | "OrderService", "UserRepository" — a single class/interface |
| `function` | "createOrder()", "validatePayload()" — a single method or function |

When scope is `class` or `function`, **Phase 2.5 (Call Graph Analysis)** is activated before
the rest of Phase 3. This produces a full impact map: who calls the target, what the target
calls, and where the natural test boundaries sit.

---

## Phase 1 — Intake

Determine mode and scope. If the user's message clearly states all of these,
skip the question and proceed immediately.

Otherwise, use `AskUserQuestion`:
1. **Mode**: new-strategy / audit / focused
2. **Scope**: whole project, a specific service, or a specific layer/class/function

If scope is a class or function, also ask (or infer from the user's message):
- The **target name** (e.g., "OrderService", "createOrder")
- The **file path** if known, otherwise the skill will locate it via Grep

Record:
```
intake = {
  mode,
  scope,             // "whole-project" | "sub-project" | "class" | "function"
  scope_target,      // null for whole-project; name or path for narrower scopes
  scope_path         // resolved file path (filled in Phase 2.5 if scope is class/function)
}
```

---

## Phase 2 — Stack Detection

Detect language, frameworks, test tooling, and CI config using Glob + Grep only.
Never run commands in this phase. Full detection patterns in
`references/stack-detection.md`.

**Step 1 — Language & framework manifests:**
Glob in order:
- `**/package.json` (not inside node_modules) — Node.js / TypeScript
- `**/pyproject.toml`, `**/requirements*.txt`, `**/setup.py` — Python
- `**/*.csproj`, `**/*.sln` — .NET
- `**/go.mod` — Go
- `**/pom.xml`, `**/build.gradle`, `**/build.gradle.kts` — Java/Kotlin
- `**/Gemfile` — Ruby
- `**/composer.json` — PHP

Read the detected manifest(s) and Grep for known test tool strings
(see `references/stack-detection.md#tool-detection-table`).

**Step 2 — Test file count:**
Glob for test file patterns per detected language
(see `references/stack-detection.md#test-file-patterns`).
Count total test files, record up to 20 paths for later analysis.

**Step 3 — CI config:**
Glob for:
`.github/workflows/*.yml`, `.github/workflows/*.yaml`,
`.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`,
`.circleci/config.yml`, `bitbucket-pipelines.yml`
Read the first found and extract existing test commands.

**Step 4 — Project shape:**
Apply rules from `references/stack-detection.md#project-shape-detection`:
- Has `controllers/` or `handlers/` or `routes/` but no `pages/` or `components/` → `api`
- Has `src/app/`, `pages/`, or `components/` (React/Vue/Angular/Blazor) → `web-app`
- Has no entry point file but has `lib/` or `src/` exports → `library`
- Multiple manifests at depth 2 in different subdirectories → `microservices`
- Entry point parses `argv` and returns exit code → `cli`
- Has both API controllers AND frontend components → `fullstack`

Record:
```
stack = {
  language, framework, test_tools[], ci_tool,
  project_shape, test_file_count, has_existing_tests,
  test_file_paths[]
}
```

Report detected stack to user before proceeding to Phase 3.

---

## Phase 2.5 — Focused Scope Analysis *(skip if scope = whole-project or sub-project)*

Activated when `intake.scope` is `class` or `function`. Read-only; never modify files.

Goal: map the **call graph** around the target so Phase 4 can plan tests at the right layer,
know what to mock, and understand the blast radius of a change.

**Step 1 — Locate the target:**
If `intake.scope_path` is not yet known, use Grep to find it:
- Grep for `class <TargetName>`, `function <TargetName>`, `def <TargetName>`, `func <TargetName>`,
  `<TargetName>(`  across all source files (exclude `node_modules`, `dist`, `bin`, `obj`)
- Read the identified file to confirm the target and understand its signature, parameters, and return type
- Record `scope_path` and the target's **layer** (controller / service / repository / utility / domain model)

**Step 2 — Caller analysis (upstream / "who calls this?"):**
Grep across all source files for references to the target:
- Function calls: `<targetName>(`, `.<targetName>(`, `this.<targetName>(`
- Class instantiation: `new <TargetClass>(`, `<TargetClass>.`
- Imports/injections: `import.*<TargetClass>`, `@Inject.*<TargetClass>`, `DI.get<TargetClass>`
- Event/queue triggers: if target is an event handler, grep for the event name

For each caller found, record:
```
caller = {
  name,           // function or class name of the caller
  file,           // source file path
  layer,          // "controller" | "service" | "use-case" | "repository" | "cli" | "test" | "external" | "unknown"
  call_type,      // "direct-call" | "constructor-injection" | "event-trigger" | "queue-consumer"
  distance        // 1 = direct caller; 2 = caller's caller (only go 2 levels deep)
}
```
Cap at depth 2 — going deeper adds noise without signal.

**Step 3 — Callee analysis (downstream / "what does this call?"):**
Read the target's source file. Scan the body of the target function/class for:
- Method calls on injected dependencies: `this.repo.`, `this.client.`, `this.service.`
- Direct function calls to other modules: `import`-ed names being called
- External I/O markers: DB queries, HTTP fetches, file reads, queue publishes, time/clock access
- Calls to other internal classes/functions

For each callee found, record:
```
callee = {
  name,           // what is being called
  file,           // resolved file if internal; null if external
  layer,          // same layer taxonomy as callers
  is_external_io, // true if DB/HTTP/file/queue/clock/email/payment
  mock_needed,    // true if is_external_io OR is a 3rd-party SDK
  mock_strategy   // "stub" | "fake" | "spy" | "mock" | "real" — from mocking-guide.md rules
}
```

**Step 4 — Boundary classification:**
Based on callers + callees, classify the target's position:
- **Entry point**: callers include a controller, route handler, CLI command, or queue consumer
  → API test or integration test can drive it from the top
- **Domain core**: callers and callees are all internal; no external I/O in callees
  → Unit tests are the primary layer; minimal mocking needed (Detroit school)
- **Adapter / infrastructure**: callees include DB, HTTP client, queue, file, or external SDK
  → Mock the callees in unit tests; use real infra in integration tests
- **Shared utility**: called from many places (≥5 callers at different layers)
  → Unit tests essential; changes here have wide blast radius — note this in report
- **Leaf node**: no callees (pure function, no I/O)
  → Simple unit tests, no mocking needed at all

**Step 5 — Test entry point recommendation:**
Based on boundary classification, recommend the most effective test entry point:

| Classification | Recommended test entry point | Why |
|---|---|---|
| Entry point | Test via HTTP (API test) or integration test from controller | Proves the full wiring works |
| Domain core | Unit test the target directly | Isolate domain logic cleanly |
| Adapter / infra | Unit test with mocked callees + integration test with real infra | Both layers needed |
| Shared utility | Unit test with representative callers as context | Wide blast radius → high priority |
| Leaf node | Unit test with inputs/outputs only | Pure function, easiest to test |

Record:
```
scope_analysis = {
  target: { name, file, layer, signature },
  boundary_classification,        // "entry-point" | "domain-core" | "adapter" | "shared-utility" | "leaf-node"
  callers[],                      // upstream callers (depth ≤ 2)
  callees[],                      // downstream dependencies
  caller_count,
  callee_count,
  external_io_count,              // how many callees are external I/O
  mock_needed_count,
  blast_radius,                   // "low" (≤2 callers) | "medium" (3–7) | "high" (≥8)
  recommended_test_entry_point,   // as per table above
  key_insight                     // 1-sentence summary for the report header
}
```

---

## Phase 3 — Deep Project Analysis

Read-only. Never modify source files. Use Read, Glob, Grep, Bash (read-only only).

**Step 1 — Architectural layer mapping:**
Glob for common layer directory names: `controllers/`, `handlers/`, `routes/`,
`services/`, `use-cases/`, `usecases/`, `repositories/`, `adapters/`,
`infrastructure/`, `domain/`, `models/`.
Read up to 3 source files from each detected layer. Classify each:
- **Thin** (pass-through CRUD, no branching) → integration tests are more valuable than unit
- **Thick** (domain logic, >3 branches, business rules) → unit tests shine here

**Step 2 — Complexity profiling:**
Use Grep to count per source file (sample up to 10 key files):
- Branch keywords: `if`, `else`, `switch`, `case`, `?`, `||`, `&&`
- Loops: `for`, `while`, `forEach`, `map`, `filter`, `reduce`
- Public methods / exported functions

Classify each file:
- `branch_count >= 5` → unit test candidate
- `branch_count < 3` → skip unit, cover at integration level
- `method_count >= 6` → worth dedicated test file

Output per-file signal:
```
{ file, layer, is_thick, branch_count, method_count }
```

**Step 3 — Existing test quality (if `has_existing_tests`):**
Read up to 5 test files (pick variety across types if possible).
For each, assess:
- AAA pattern (Arrange/Act/Assert sections visible?)
- Mock usage: applied at system boundary (DB, HTTP) or overused on internal classes?
- Test naming: `it('should do X when Y')` vs `it('test1')`
- Assertion density: multiple distinct assertions vs one assertion per test

Record `existing_test_quality = { rating: "good|fair|poor", issues[], positives[] }`.

**Step 4 — Overlap detection (cross-layer AND intra-type):**

For each test file, determine which behaviors it exercises:
- Does it call a service method directly? (`covers_service_method`)
- Does it call an HTTP endpoint? (`covers_endpoint`)
- Does it click UI elements? (`covers_ui_action`)
- Does it use the same assertion as another test file at a different layer?

**4a — Cross-layer overlaps** (behavior tested redundantly at multiple test types):
- Unit + Integration covering identical logic → overlap, integration should own it
- Integration + API test with same endpoint + same assertions → overlap, API test owns it
- API + Automation test covering same user action → overlap, API test owns it
- Multiple E2E tests covering same full journey → overlap, one E2E owns it

Record `overlap_candidates[] = { behavior, covered_by: {unit,integration,api,ui,automation}, recommended_owner, reason }`.

**4b — Intra-type overlaps** (duplicate tests within the same test type):
For each test type separately, scan all test files of that type and detect:
- **Unit**: Multiple test files asserting the same function/method with identical or near-identical inputs/outputs
  - Signal: same function name called in `describe`/`it` blocks across different test files
- **Integration**: Multiple integration test files hitting the same endpoint with the same expected status code + response shape
  - Signal: same route string (e.g., `POST /orders`) with same assertion pattern in 2+ files
- **API**: Same endpoint + HTTP method tested with the same status code in 2+ API test suites
- **E2E / Automation**: Same user journey sequence (login → action → assert outcome) repeated in multiple test files
  - Signal: same sequence of UI selectors or page actions across 2+ test files
- **BDD**: Duplicate Gherkin scenarios (same Given/When clause with same Then outcome) in different feature files

Classify each intra-type overlap:
- `identical` — same function/endpoint/journey, same assertions, effectively copy-paste
- `near-identical` — same target, minor variation (different user role, minor input diff) that could be table-driven
- `subset` — one test covers a superset of what another test covers (smaller test is redundant)

Record:
```
intra_type_overlaps[] = {
  test_type,          // "unit" | "integration" | "api" | "e2e" | "automation" | "bdd"
  behavior,           // human-readable description, e.g. "validateOrder() happy path"
  test_files[],       // list of files containing the duplication
  duplication_type,   // "identical" | "near-identical" | "subset"
  recommendation      // e.g. "Consolidate into order.test.ts — delete duplicate in checkout.test.ts"
                      // or "Parameterize into a data-driven test table"
}
```

Combined output:
```
overlap_analysis = {
  has_overlaps: bool,
  cross_layer_count: int,
  intra_type_count: int,
  candidates[],         // cross-layer overlaps
  intra_type_overlaps[] // within-type duplicates
}
```

**Step 5 — External dependency map:**
Grep source files for external I/O that needs mocking:
- DB/ORM: `DbContext`, `mongoose`, `Repository`, `session.query`, `prisma`, `sequelize`
- HTTP clients: `HttpClient`, `axios`, `requests.get`, `fetch`, `urllib`, `got`, `grpc`
- File I/O: `File.`, `fs.`, `open(`, `os.path`, `path.join`
- Message queues: `ServiceBus`, `RabbitMQ`, `kafka`, `SQS`, `Bull`, `BullMQ`
- Time: `DateTime.Now`, `new Date()`, `time.Now()`, `datetime.now()`, `Date.now()`
- Email/SMS: `sendgrid`, `nodemailer`, `twilio`, `ses`
- Payment: `stripe`, `paypal`, `braintree`

Record `external_deps[] = { name, type, files_using_it[], mock_at_layer[] }`.

Output at end of Phase 3:
```
analysis = {
  layers[],
  complexity_signals[],
  existing_test_quality,
  coverage_gaps[],
  overlap_candidates[],
  external_deps[]
}
```

---

## Phase 4 — Strategy Synthesis

Pure reasoning phase. No tool calls except one optional `AskUserQuestion` if a
genuine ambiguity would change the recommendation materially.

**0. Scope-aware adjustments** *(only when `scope_analysis` exists from Phase 2.5)*:

Before synthesizing strategy, apply these scope-driven constraints:

| scope_analysis.boundary_classification | Primary test type to recommend Essential | Secondary |
|---|---|---|
| `entry-point` | API test (tests the full path from controller down) | Integration |
| `domain-core` | Unit test (isolates business logic cleanly) | — |
| `adapter` | Unit (mocked callees) + Integration (real infra) | both Essential |
| `shared-utility` | Unit (high priority — wide blast radius) | Integration |
| `leaf-node` | Unit only (pure function, no infra needed) | — |

Mocking decisions for the target:
- Each callee with `mock_needed: true` → must be mocked in unit tests of the target
- Each callee with `mock_needed: false` and internal → use real implementation (Detroit school)
- If `external_io_count >= 2` → lean London school for this target's tests
- If `external_io_count == 0` and all callees internal → lean Detroit

Priority matrix adjustment:
- If `blast_radius = "high"` → automatically bump the target's test action item to P0
- If `caller_count == 0` → note "no callers found — may be dead code or newly added; verify before investing heavily"

**1. Pick the testing model** (see `references/testing-mindset.md#testing-models`):

| Project characteristics | Model |
|---|---|
| Thick domain logic, rich business rules, many services | **Pyramid** |
| Framework-heavy, CRUD-dominant, thin services | **Trophy** |
| Microservices / event-driven, each service is independently deployable | **Honeycomb** |
| React/Vue/Angular frontend dominant | **Trophy** (integration via component tests) |

When scope is `class` or `function`: still pick a model, but narrow the rationale to
reflect the target's position in the architecture (e.g., "target is a domain service with no
external I/O — Pyramid applies; unit tests are the primary layer").

Write a 1–2 sentence rationale explaining the choice.

**2. Per test type recommendation** (see `references/test-types.md`):
For each type, decide: `Essential | Recommended | Optional | Skip`.
Use the per-file complexity signals and project shape to justify each decision.
Generic reasoning is not acceptable — reference actual files or patterns found.

When scope is `class` or `function`: skip types that the call graph shows are irrelevant
(e.g., skip UI/E2E if no caller chain reaches a frontend controller).

**3. Mocking school** (see `references/mocking-guide.md#schools`):
- **Detroit/Chicago**: domain logic is testable with fakes; only mock external I/O
- **London**: complex dependency graph, event-driven, hard to construct real objects
- **Mixed**: Detroit for domain, London for infrastructure adapters (most common)

Decision rule: if the services in Phase 3 had >3 collaborators each that would
need real setup → lean London. If domain objects are pure / easily constructable
with fakes → lean Detroit.

When `scope_analysis` exists: apply mocking school specifically to the target's
callee list from Phase 2.5 Step 3, not the entire project.

**4. Overlap elimination** — for each `overlap_candidate`:
- State which layer **owns** the test
- State what should be removed from the other layers
- Give a concrete example of what the slimmed-down test looks like

**5. Coverage targets** — realistic for this project type:
- Library: 80–90% line + branch
- API backend: 60–70% overall (unit + integration covering all endpoints)
- Web app: critical flows via E2E; component coverage 50–60%
- Microservices: contract tests for all service boundaries + per-service 60%
- Single class/function scope: aim for 100% branch coverage of the target itself

**6. Priority matrix** — rank 5–8 action items by ROI:
- `impact`: high / medium / low (how much test confidence it adds)
- `effort`: high / medium / low (lines of code / infrastructure needed)
- `quadrant`: quick-win (high-impact, low-effort) | strategic | fill-in | avoid

**7. CI plan** — recommended pipeline stages:
- Fast unit (< 30s): run on every commit
- Integration (< 3 min): run on every PR
- E2E / automation (< 10 min): run on merge to main or nightly
- Load tests: scheduled weekly or as a pre-release gate

Produce `strategy` object matching schema in `references/report-format.md`.

---

## Phase 5 — Generate HTML Report

1. Read `assets/report-template.html`
2. Replace scalar `{{PLACEHOLDER}}` tokens (HTML-escape all strings)
3. Serialize the full `strategy` JSON and inject as `const reportData = {{REPORT_JSON}};`
4. Write the filled template to `testing-strategy-report-YYYYMMDD-HHmmss.html`
   in the **current working directory** (where the user ran the skill)
5. Print the file path to the user

The template renders all sections client-side via vanilla JS from `reportData`.
See `references/report-format.md` for the full placeholder list and section spec.

Report sections (in order):
1. **Header** — project name, timestamp, mode badge, shape badge
2. **Summary cards** — 6 metric cards (model, shape, test types, overlap issues, coverage estimate, CI status)
3. **Scope Impact Map** *(only rendered when `scope_analysis` exists)* — call graph visualization:
   - Target info card (name, file, layer, boundary classification, blast radius badge)
   - **Callers table**: who calls this target — name, file, layer, call type, depth; entry-point callers highlighted
   - **Callees table**: what this target calls — name, file, layer, external I/O flag, mock recommendation
   - **Key insight** banner explaining the recommended test entry point and why
4. **Testing Model** — SVG pyramid/trophy/honeycomb with layer labels and rationale
5. **Test Types** — collapsible cards per type (recommendation badge, rationale, tools, code snippet, coverage target); BDD card includes Gherkin example
6. **Mocking per Test Type** — always-visible table (never collapsed); what to mock / what NOT to mock per test type; anti-patterns
7. **Mocking Deep-Dive** — London/Detroit indicator, what-to-mock list, tools by stack
8. **Test Overlap Analysis** — two-tab table (cross-layer / within-type); only rendered if `has_existing_tests`
9. **Coverage Analysis** — overall estimate gauge, gaps table
10. **CI/CD Integration** — horizontal pipeline stage visualization
11. **Priority Matrix** — 2×2 impact/effort scatter plot; hover for action details
12. **Action Items** — P0/P1/P2 expandable list with code examples

---

## Phase 6 — Chat Summary

After writing the report, print a concise text summary directly in chat:

```
Testing Strategy — <project_name>
Shape: <project_shape>  │  Model: <testing_model>

[When scope is class or function — print the impact map summary first:]
  Scope:    <TargetName> (<boundary_classification>)  │  Blast radius: <low|medium|high>
  Callers:  <N> callers  │  Callees: <M> dependencies (<K> external I/O)
  Best entry point: <recommended_test_entry_point>
  💡 <key_insight>

  ✅ UNIT TESTS        <recommendation>  │ <coverage_target>  │ <tools>
  ✅ INTEGRATION       <recommendation>  │ —                  │ <tools>
  ~  API TESTS         <recommendation>  │ —                  │ <tools>
  ~  UI/E2E            <recommendation>  │ <N> critical journeys
  ~  BDD               <recommendation>  │ <when applicable>
  ○  LOAD TESTS        <recommendation>  │ <reason if Skip>
  ○  PERFORMANCE       <recommendation>  │ <reason if Skip>

Mocking: <school> school — <one-line rule>

⚠️  <N> cross-layer overlaps  │  <M> intra-type duplicates
    (or ✅ No overlaps detected)

Top actions:
  [P0] <title>
  [P0] <title>
  [P1] <title>

Report: testing-strategy-report-YYYYMMDD-HHmmss.html
```

---

## References

- `references/testing-mindset.md` — testing philosophy, models, FIRST, AAA, what NOT to test
- `references/test-types.md` — per test type: what to test, tools, patterns, BDD guide
- `references/mocking-guide.md` — test doubles taxonomy, London vs Detroit, per-type mock rules
- `references/stack-detection.md` — file patterns, tool detection, project shape rules
- `references/report-format.md` — full JSON schema, placeholder list, SVG specs
- `assets/report-template.html` — dark-theme HTML report template
