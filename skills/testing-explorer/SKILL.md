---
name: testing-explorer
description: This skill should be used when the user wants to see, run, or inspect a project's tests inside Claude Code — discover the test tree, run .NET (dotnet test) or Playwright suites, view pass/fail/skip status in an interactive panel, re-run only failed tests, analyze why a test failed, or see code coverage. Also use when the user says "show my tests", "run the tests", "test explorer", "why did this test fail", "re-run failed tests", or "what's my coverage".
version: 0.1.0
tools: Read, Glob, Grep, Bash
---

# Testing Explorer

A Test Explorer that lives **inside Claude Code's Preview panel**. Discovers
the test tree, runs .NET (`dotnet test`) and Playwright suites, classifies
failures with a root cause, collects coverage automatically for .NET, and
renders an interactive dashboard in the Preview panel — no external browser.

Solves: test projects are otherwise invisible in Claude Code and there is no
way to run them and see status at a glance.

## Modes

| User intent | Mode |
|---|---|
| "show / list my tests", "test explorer" (no run) | `discovery` |
| "run the tests", "run all tests" | `full` |
| "re-run failed", "run failed tests again" | `rerun-failed` |
| "why did test X fail" | `full` (or reuse last results) then focus failure |

Pick the mode from the request. `discovery` never executes tests.

---

## Phase 1 — Detect Test Stacks

```bash
# .NET test projects
ls **/*.csproj 2>/dev/null
```
Use Glob `**/*.csproj`, then Grep each for a test marker:
`<IsTestProject>true</IsTestProject>` OR a PackageReference to
`Microsoft.NET.Test.Sdk`, `xunit`, `nunit`, or `MSTest.TestFramework`.
Record `{ project_path, framework }` (xUnit / NUnit / MSTest).

Playwright: Glob `**/playwright.config.{ts,js,mjs,cts}`; confirm
`@playwright/test` in the nearest `package.json`. Record the project dir.

If **no** test stack is found, stop and tell the user plainly (no panel).
Report which stacks were detected before proceeding.

See `references/dotnet-test.md` and `references/playwright-test.md`.

---

## Phase 2 — Discovery (no execution)

Build the tree without running anything:

- .NET: `dotnet test <proj> --list-tests` (parse the
  "The following Tests are available:" block into FQNs).
- Playwright: `npx playwright test --list --reporter=json` (or plain
  `--list`) → file → describe → test.

Produce `tree[]` (see `references/result-parsing.md`):
`project → suite/file → test`, every node `status:"unknown"` in discovery.

If mode is `discovery`: go straight to Phase 6 with `mode:"discovery"` and
stop after rendering.

---

## Phase 3 — Build Verification

Compile before running so a build break is reported clearly instead of as a
confusing test-runner error. Reuse the patterns in
`../api-flow-debugger/references/build-verification.md`.

| Stack | Command |
|---|---|
| .NET | `dotnet build <proj> --no-restore` (fallback `dotnet build <proj>`) |
| Playwright (TS) | `npx tsc --noEmit` if a `tsconfig.json` exists (skip if none) |

Capture stdout+stderr and duration. Ensure Playwright browsers are present:
if `npx playwright test` later errors with a missing-browser message, tell the
user to run `npx playwright install` (do **not** run it without approval —
it downloads browser binaries).

On build failure: print the parsed first error + last 30 lines, then ask
`Build failed. Abort and show partial panel, or continue anyway? [abort/continue]`.
Record:
```
build = { status, command, duration_ms, output_tail, error_summary, user_choice }
```
`abort` → skip Phases 4/5, render partial panel (Phase 6) with the build
error as the root cause.

---

## Phase 4 — Run Tests

Run in the background, capture artifacts. Pre-process any console output with
the ANSI-strip / line-ending normalization from
`../api-flow-debugger/references/log-parsing.md` before parsing.

**.NET** (`references/dotnet-test.md`):
```bash
dotnet test <proj> --no-build --logger "trx;LogFileName=results.trx"
```
The TRX is written under `<proj-dir>/TestResults/`.

**Coverage is automatic for .NET** (`references/coverage.md`):
- If the test project references `coverlet.collector` → append
  `--collect:"XPlat Code Coverage"` (Cobertura at
  `TestResults/<guid>/coverage.cobertura.xml`).
- Else, auto-provision a **repo-local** tool (no prompt, never `--global`):
  ```bash
  ls .config/dotnet-tools.json dotnet-tools.json 2>/dev/null | grep -q . \
    || dotnet new tool-manifest
  dotnet tool install dotnet-coverage 2>/dev/null || dotnet tool update dotnet-coverage
  dotnet tool run dotnet-coverage collect -f cobertura -o coverage.cobertura.xml \
    "dotnet test <proj> --no-build --logger trx;LogFileName=results.trx"
  ```
  If the tool cannot be installed (offline), warn once and continue with
  coverage marked unavailable — tests still run.

**Playwright** (`references/playwright-test.md`):
```bash
PLAYWRIGHT_JSON_OUTPUT_NAME=pw-results.json npx playwright test --reporter=json
```
Playwright source coverage is **not** auto-enabled — never inject hooks or
edit the project. Parse a monocart/V8 coverage report only if the project
already produces one.

---

## Phase 5 — Parse, Correlate, Classify

Parse TRX XML (`.NET`) and `pw-results.json` (Playwright) into one unified
model — full schema and parsing rules in `references/result-parsing.md`:

```
report = {
  timestamp, duration_ms, mode,            // "full" | "discovery" | "rerun-failed"
  stacks:   [ { type, project, framework } ],
  summary:  { total, passed, failed, skipped, flaky, pass_rate, duration_ms },
  tree:     [ { id, type, label, status, duration_ms, file, line, children:[] } ],
  failures: [ { test_id, name, file, line, error_type, message, stack,
                expected, actual, likely_cause } ],
  coverage: {
    dotnet:     { available, line_pct, branch_pct, by_file:[], source } ,
    playwright: { available:false, reason, how_to_enable }
  },
  build: { status, command, duration_ms, output_tail, error_summary, user_choice }
}
```

Classify every failure (`references/result-parsing.md#failure-classification`):
assertion mismatch · unhandled exception · timeout · setup/fixture error ·
Playwright selector/navigation. Extract `file:line` from the stack and write
a one-line `likely_cause`. For assertion failures, fill `expected`/`actual`.

---

## Phase 6 — Render Dashboard in the Preview Panel

This is the core of the skill — the panel must show **inside Claude Code**,
not an OS browser. Full orchestration in `references/preview-panel.md`.

1. Fill `assets/test-report-template.html`: replace `{{PLACEHOLDER}}` scalars
   (HTML-escape strings) and inject JSON for `TREE`, `FAILURES`, `COVERAGE`,
   `SUMMARY`, `BUILD`.
2. Write to the served path (create dir if missing):
   `.claude/skills/testing-explorer/.report/index.html`
   and an archive copy `.report/test-report-YYYYMMDD-HHmmss.html`.
3. Ensure a config named `testing-explorer-report` exists in
   `.claude/launch.json` (merge, don't clobber other configs) — schema in
   `references/preview-panel.md`.
4. `preview_start("testing-explorer-report")` → panel opens. On a refresh /
   re-run, instead call `preview_eval(serverId, "location.reload()")`.
5. `preview_screenshot(serverId)` to self-verify it rendered; if blank, check
   the server with `preview_list` and the fallback in `references/preview-panel.md`.
6. Also print a concise text summary in chat:
   `✅ 12 passed · ❌ 2 failed · ⏭ 1 skipped · ⏱ 4.3s · 📊 .NET line 78%`,
   then list each failure as `name — likely_cause (file:line)`.

Dashboard features (client-side, dark theme matching api-flow-debugger):
collapsible test tree with ✅/❌/⏭/◌ markers, All/Failed/Skipped filter,
search, click a test → failure detail (message + stack + file:line +
expected/actual), coverage bars (overall + per-file), summary cards.

---

## Phase 7 — Re-run Failed Only

Triggered by "re-run failed". Requires a prior `report` (run Phase 4 first if
none).

- .NET: build `--filter` from the failed FQNs:
  `dotnet test <proj> --no-build --logger trx \
   --filter "FullyQualifiedName=A|FullyQualifiedName=B"` (see
  `references/dotnet-test.md#rerun-filter`).
- Playwright: `npx playwright test --last-failed --reporter=json`.

Merge the new statuses into the previous `report` (only re-run tests change),
set `mode:"rerun-failed"`, regenerate `index.html`, and
`preview_eval(serverId,"location.reload()")` so the panel live-updates.

---

## Cleanup

Leave the preview server running so the panel stays usable; tell the user
they can ask to stop it (`preview_stop`). Remove temp logs
(`pw-results.json`, normalized log temp files). Do not delete `.report/`.

---

## References

- `references/dotnet-test.md` — discovery / run / rerun filter / TRX parsing
- `references/playwright-test.md` — list / JSON reporter / `--last-failed`
- `references/result-parsing.md` — unified model + failure classification
- `references/coverage.md` — coverlet vs dotnet-coverage auto-provision; Cobertura parsing
- `references/preview-panel.md` — launch.json schema + preview_* orchestration + fallbacks
- `assets/test-report-template.html` — dashboard template with placeholders
