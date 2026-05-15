# Coverage — automatic for .NET, suggest-only for Playwright

## .NET — fully automatic, zero-touch

### Decision

1. Grep the test `.csproj` (and a `Directory.Build.props` if present) for
   `coverlet.collector`.
2. **If referenced** → coverage via the built-in collector:
   ```bash
   dotnet test "<proj>.csproj" --no-build --nologo \
     --logger "trx;LogFileName=results.trx" \
     --collect:"XPlat Code Coverage"
   ```
   Output: `<proj-dir>/TestResults/<guid>/coverage.cobertura.xml`.
   Set `coverage.dotnet.source = "coverlet"`.
3. **If NOT referenced** → provision a **repo-local** tool (never `--global`,
   never prompt — the user already opted into automatic coverage):
   ```bash
   # Manifest may be at .config/dotnet-tools.json OR ./dotnet-tools.json
   # depending on SDK version — only create if neither exists.
   ls .config/dotnet-tools.json dotnet-tools.json 2>/dev/null | grep -q . \
     || dotnet new tool-manifest
   dotnet tool install dotnet-coverage 2>/dev/null \
     || dotnet tool update dotnet-coverage
   dotnet tool run dotnet-coverage collect -f cobertura \
     -o coverage.cobertura.xml \
     "dotnet test \"<proj>.csproj\" --no-build --nologo --logger trx;LogFileName=results.trx"
   ```
   Set `coverage.dotnet.source = "dotnet-coverage"`. Run these from the test
   project directory (the manifest is per-directory). Verified: produces a
   Cobertura file with `line-rate` / `branch-rate` even when the run has
   failing tests (exit code non-zero is expected — parse anyway).
4. If provisioning fails (offline / no NuGet): warn **once**, set
   `coverage.dotnet = { available:false, reason:"dotnet-coverage unavailable (offline?)" }`,
   and continue — tests must still run and the panel must still render.

`.config/dotnet-tools.json` is a normal repo-local manifest; creating it is
expected and safe. The skill creating it counts as a normal build action,
not a destructive one.

### Cobertura parsing

Cobertura XML root `<coverage line-rate="0.784" branch-rate="0.61" ...>`.

- Overall: `line_pct = round(line-rate * 100, 1)`,
  `branch_pct = round(branch-rate * 100, 1)`.
- Per file: walk `<packages><package><classes><class filename= line-rate=
  branch-rate=>`. Multiple `<class>` can share a `filename` (partial classes)
  — aggregate by `filename`: recompute pct from summed
  `<lines><line hits=>` (covered = hits>0) rather than averaging rates, so
  large/small files weight correctly.
- Skip generated/framework files: paths containing `obj/`, `*.g.cs`,
  `*.Designer.cs`, `Migrations/`.
- Sort `by_file` ascending by `line_pct` (worst first — most actionable).

Populate:
```
coverage.dotnet = {
  available: true, source: "coverlet" | "dotnet-coverage",
  line_pct, branch_pct,
  by_file: [ { file, line_pct, branch_pct } ]   // relative path, '/' separators
}
```

## Playwright — suggest only, never modify the project

Do not add fixtures, reporters, or config. Only consume an existing
monocart / V8 report if the project already produces one (look for
`coverage/index.json`, `coverage/cobertura.xml`, or a monocart output dir
configured by the project). If found, parse like Cobertura above or
monocart's JSON summary and fill `coverage.playwright`.

Otherwise:
```
coverage.playwright = {
  available: false,
  reason: "Playwright source coverage not configured",
  how_to_enable: "Add 'monocart-coverage-reports' as a Playwright reporter in playwright.config — testing-explorer does not modify your project."
}
```

The dashboard renders `.NET` coverage bars and a Playwright "N/A" card with
`how_to_enable` as a tooltip/note.
