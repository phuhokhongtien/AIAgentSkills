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
version: 0.1.1
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

---

## Phase 1 — Intake

Determine mode and scope. If the user's message clearly states all of these,
skip the question and proceed immediately.

Otherwise, use `AskUserQuestion`:
1. **Mode**: new-strategy / audit / focused
2. **Scope**: whole project, a specific service, or a specific layer

Record `intake = { mode, scope }` and proceed.

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

**1. Pick the testing model** (see `references/testing-mindset.md#testing-models`):

| Project characteristics | Model |
|---|---|
| Thick domain logic, rich business rules, many services | **Pyramid** |
| Framework-heavy, CRUD-dominant, thin services | **Trophy** |
| Microservices / event-driven, each service is independently deployable | **Honeycomb** |
| React/Vue/Angular frontend dominant | **Trophy** (integration via component tests) |

Write a 1–2 sentence rationale explaining the choice.

**2. Per test type recommendation** (see `references/test-types.md`):
For each type, decide: `Essential | Recommended | Optional | Skip`.
Use the per-file complexity signals and project shape to justify each decision.
Generic reasoning is not acceptable — reference actual files or patterns found.

**3. Mocking school** (see `references/mocking-guide.md#schools`):
- **Detroit/Chicago**: domain logic is testable with fakes; only mock external I/O
- **London**: complex dependency graph, event-driven, hard to construct real objects
- **Mixed**: Detroit for domain, London for infrastructure adapters (most common)

Decision rule: if the services in Phase 3 had >3 collaborators each that would
need real setup → lean London. If domain objects are pure / easily constructable
with fakes → lean Detroit.

**4. Overlap elimination** — for each `overlap_candidate`:
- State which layer **owns** the test
- State what should be removed from the other layers
- Give a concrete example of what the slimmed-down test looks like

**5. Coverage targets** — realistic for this project type:
- Library: 80–90% line + branch
- API backend: 60–70% overall (unit + integration covering all endpoints)
- Web app: critical flows via E2E; component coverage 50–60%
- Microservices: contract tests for all service boundaries + per-service 60%

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
3. **Testing Model** — SVG pyramid/trophy/honeycomb with layer labels and rationale
4. **Test Types** — collapsible cards per type (recommendation badge, rationale, tools, code snippet, coverage target); BDD card includes Gherkin example
5. **Mocking per Test Type** — always-visible table (never collapsed); what to mock / what NOT to mock per test type; anti-patterns
6. **Mocking Deep-Dive** — London/Detroit indicator, what-to-mock list, tools by stack
7. **Test Overlap Analysis** — table of detected overlaps (only rendered if `has_existing_tests`); red rows = redundancy, green = clean ownership
8. **Coverage Analysis** — overall estimate gauge, gaps table
9. **CI/CD Integration** — horizontal pipeline stage visualization
10. **Priority Matrix** — 2×2 impact/effort scatter plot; hover for action details
11. **Action Items** — P0/P1/P2 expandable list with code examples

---

## Phase 6 — Chat Summary

After writing the report, print a concise text summary directly in chat:

```
Testing Strategy — <project_name>
Shape: <project_shape>  │  Model: <testing_model>

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
