# .NET — discovery, run, re-run, TRX parsing

## Detect test projects

Glob `**/*.csproj`. A project is a test project if Grep finds any of:

- `<IsTestProject>true</IsTestProject>`
- `PackageReference Include="Microsoft.NET.Test.Sdk"`
- `PackageReference Include="xunit"` → framework **xUnit**
- `PackageReference Include="nunit"` → framework **NUnit**
- `PackageReference Include="MSTest.TestFramework"` → framework **MSTest**

## Discovery (no execution)

```bash
dotnet test "<proj>.csproj" --list-tests --nologo
```
Output contains a block:
```
The following Tests are available:
    Namespace.ClassName.MethodName
    Namespace.ClassName.MethodName(param: ...)
```
Take every indented line after that header as a fully-qualified test name
(FQN). Split on `.` to build `namespace/class → test`. Theory/parametrized
cases keep the `(...)` suffix as the leaf label; the FQN for filtering is the
part before `(`.

## Run with structured output

```bash
dotnet test "<proj>.csproj" --no-build --nologo \
  --logger "trx;LogFileName=results.trx"
```
TRX is written to `<proj-dir>/TestResults/results.trx`. `--no-build` assumes
Phase 3 already built; if it errors with "project not built", retry once
without `--no-build`.

Coverage flags are added by `coverage.md` (do not duplicate here).

## TRX parsing

TRX is XML (namespace `http://microsoft.com/schemas/VisualStudio/TeamTest/2010`).

- Per-test results: `<Results><UnitTestResult .../></Results>`
  - `testName` → display name (FQN-ish; includes `(params)` for theories)
  - `outcome` → `Passed` | `Failed` | `NotExecuted` (= skipped) | `Timeout`
  - `duration` → `HH:MM:SS.fffffff` → convert to ms
  - On failure: `<Output><ErrorInfo><Message>` and `<StackTrace>`
- Test definitions: `<TestDefinitions><UnitTest><TestMethod
  className= name= />` — use to recover namespace/class for the tree and to
  map a result back to its source class.
- Counters: `<ResultSummary><Counters total= passed= failed= ... />` —
  cross-check against the parsed list.

Map outcome → unified status: `Passed→passed`, `Failed→failed`,
`NotExecuted→skipped`, `Timeout→failed` (error_type `timeout`).

Source `file:line`: parse the first frame in `<StackTrace>` that points into
the user's test/source paths, pattern `in <path>:line <n>`.

## Re-run filter {#rerun-filter}

From the prior `report.failures`, take each `.name`, strip any `(...)` suffix
to get the bare FQN, then:
```bash
dotnet test "<proj>.csproj" --no-build --nologo \
  --logger "trx;LogFileName=results.trx" \
  --filter "FullyQualifiedName=Ns.Cls.M1|FullyQualifiedName=Ns.Cls.M2"
```
`|` is OR in the .NET test filter expression. If a single failure, no `|`.
Re-running a theory by its base FQN re-runs all its cases — acceptable; merge
results back by matching `testName`.

## Notes

- Multiple test projects: run each separately, tag every node with its
  `project` so the tree groups by project at the top level.
- `dotnet test` exit code is non-zero when any test fails — that is expected,
  do **not** treat it as a skill error; parse the TRX regardless.
- Windows paths in stack traces use `\`; normalize to `/` for display only.
