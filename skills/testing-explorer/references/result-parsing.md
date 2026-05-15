# Unified result model + failure classification

## Unified model

```jsonc
report = {
  timestamp: "2026-05-16T10:22:03Z",
  duration_ms: 4310,
  mode: "full",                       // "full" | "discovery" | "rerun-failed"
  stacks: [
    { type: "dotnet",     project: "samples/Sample.Tests", framework: "xUnit" },
    { type: "playwright", project: "samples/playwright-sample", framework: "Playwright" }
  ],
  summary: {
    total: 15, passed: 12, failed: 2, skipped: 1, flaky: 0,
    pass_rate: 0.80,                  // passed / (total - skipped), 0..1
    duration_ms: 4310
  },
  tree: [
    { id:"p:dotnet",  type:"project", label:"Sample.Tests", status:"failed",
      duration_ms:1200, children:[
        { id:"s:Calc", type:"suite", label:"CalculatorTests", status:"failed",
          children:[
            { id:"t:1", type:"test", label:"Add_Works", status:"passed",
              duration_ms:3, file:"CalculatorTests.cs", line:10 },
            { id:"t:2", type:"test", label:"Divide_ByZero", status:"failed",
              duration_ms:5, file:"CalculatorTests.cs", line:22 }
          ] } ] }
  ],
  failures: [
    { test_id:"t:2", name:"Sample.Tests.CalculatorTests.Divide_ByZero",
      file:"CalculatorTests.cs", line:22,
      error_type:"assertion",                 // see classification below
      message:"Assert.Equal() Failure\nExpected: 2\nActual:   0",
      stack:"   at Sample.Tests.CalculatorTests.Divide_ByZero() in ...:line 22",
      expected:"2", actual:"0",
      likely_cause:"Calculator.Divide returns 0 instead of the quotient — check the Divide implementation at the call site." }
  ],
  coverage: {
    dotnet:     { available:true,  line_pct:78.4, branch_pct:61.0,
                  source:"dotnet-coverage",     // or "coverlet"
                  by_file:[ { file:"Calculator.cs", line_pct:55.0, branch_pct:40.0 } ] },
    playwright: { available:false, reason:"...", how_to_enable:"..." }
  },
  build: { status:"passed", command:"dotnet build ...", duration_ms:820,
           output_tail:"", error_summary:null, user_choice:null }
}
```

### Status values

`passed` · `failed` · `skipped` · `unknown` (discovery only).
A suite/project node's status is the worst of its children:
`failed` > `skipped`-mixed > `passed` > `unknown`. (Any failed child →
`failed`; else any passed → `passed`; else `skipped`/`unknown`.)

### Node ids

Stable, prefixed: `p:` project, `s:` suite, `t:` test. Build deterministically
(e.g. hash of FQN / `file::title`) so re-run merges by id.

### Merge rule (rerun-failed)

Keep the previous `report`. For each re-run test, replace its node `status`,
`duration_ms`, and its `failures[]` entry (remove if it now passes).
Recompute every ancestor node status and the `summary` counters. Set
`mode:"rerun-failed"`.

## Failure classification {#failure-classification}

Set `error_type` by inspecting the message/stack (first match wins):

| error_type | Signal |
|---|---|
| `timeout` | TRX outcome `Timeout`; Playwright `timedOut`; message has `Timeout` / `exceeded` / `Timed out NNNN ms` |
| `assertion` | xUnit `Assert.*() Failure`; NUnit `Expected:`/`But was:`; MSTest `Assert.*` ; Playwright `expect(...)` / `Expected:`+`Received:` |
| `selector` | Playwright `locator(...)` / `waiting for selector` / `strict mode violation` / `element is not visible` |
| `navigation` | Playwright `page.goto` / `net::ERR` / `ERR_CONNECTION` |
| `setup` | Stack mentions ctor / `IClassFixture` / `[SetUp]` / `OneTimeSetUp` / `beforeAll` / `beforeEach`; or test never started |
| `exception` | Fallback — any unhandled exception (`System.*Exception`, `TypeError`, etc.) not matched above |

`expected` / `actual`: for `assertion`, parse the runner's diff block
(xUnit `Expected:` / `Actual:`; NUnit `Expected:` / `But was:`; Playwright
`Expected:` / `Received:`). Leave null if not an assertion.

`likely_cause`: one sentence, concrete, pointing at the probable source —
name the asserted method/symbol and the `file:line` from the first user-code
stack frame. Do not restate the message verbatim.

`file:line`: first stack frame inside the user's source (skip framework
frames: `Microsoft.*`, `xunit.*`, `NUnit.*`, `node_modules`,
`@playwright/test`). .NET frames: `in <path>:line <n>`. Playwright: prefer
`error.location`.

## Cross-platform parsing

Reuse `../../api-flow-debugger/references/log-parsing.md`:
- Strip ANSI before regex (Playwright + .NET colorize output).
- Tool order: `rg` → `grep -E` → PowerShell `Select-String` → `findstr`.
- Normalize CRLF → LF on captured logs.
TRX/JSON are structured — parse as XML/JSON, not by line regex, except for
extracting `file:line` out of free-text stack strings.
