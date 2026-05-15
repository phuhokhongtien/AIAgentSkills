# Playwright — list, run, re-run, JSON parsing

## Detect

Glob `**/playwright.config.{ts,js,mjs,cts}`. Confirm `@playwright/test` is in
the nearest `package.json` (`dependencies` or `devDependencies`). The project
dir is the directory containing the config; run all commands from there.

## Discovery (no execution)

```bash
npx playwright test --list --reporter=json
```
The JSON `suites[]` tree describes files → describe blocks → tests without
running them. If `--reporter=json` with `--list` is noisy on the installed
version, fall back to plain `npx playwright test --list` and parse lines of
the form `  <file>:<line>:<col> › <describe> › <title>`.

## Run with structured output

```bash
PLAYWRIGHT_JSON_OUTPUT_NAME=pw-results.json npx playwright test --reporter=json
```
Some setups send JSON to stdout instead of a file — capture stdout too and
prefer the file if both exist. Set `--reporter=json` even if the config
defines other reporters (CLI flag overrides config).

## JSON parsing

Top level: `{ config, suites:[], stats:{} }`.

Walk `suites[]` recursively. Each `suite` has `title`, `file`, nested
`suites[]`, and `specs[]`. Each `spec` has `title`, `line`, `column`,
`tests[]`. Each `test` has `results[]` (one per attempt/retry) with:

- `status`: `passed` | `failed` | `timedOut` | `skipped` | `interrupted`
- `duration` (ms)
- `error` / `errors[]`: `{ message, stack }` (also `snippet`, `location`)
- `retry`: index — if a later retry passes after a failure, mark the test
  `flaky` (status `passed`, `flaky:true`).

Map status → unified: `passed→passed`, `skipped→skipped`,
`failed|timedOut|interrupted→failed` (`timedOut` sets `error_type:"timeout"`).

`file:line`: prefer `error.location` `{file,line,column}`; else the `spec`'s
`file` + `line`. Strip ANSI from `error.message` (Playwright colorizes diffs)
using the helper in `../../api-flow-debugger/references/log-parsing.md`.

For assertion errors, Playwright messages contain `Expected:` / `Received:`
blocks — extract them into `expected` / `actual`.

## Re-run failed only

```bash
PLAYWRIGHT_JSON_OUTPUT_NAME=pw-results.json npx playwright test --last-failed --reporter=json
```
`--last-failed` uses Playwright's own `.last-run.json` cache, so it works
even across skill invocations as long as the project dir is unchanged. Merge
results back by `file + spec title`.

## Coverage — do NOT auto-enable

Playwright has no built-in application-source coverage flag. Only parse
coverage if the project **already** emits a monocart / V8 report (e.g.
`coverage/index.json` or a `monocart-coverage-reports` output configured by
the project). Never add a fixture, reporter, or config entry to enable it.
When absent, set:
```
coverage.playwright = {
  available: false,
  reason: "Playwright source coverage not configured",
  how_to_enable: "Add monocart-coverage-reports as a Playwright reporter (see its README) — testing-explorer does not modify your project."
}
```

## Notes

- Missing browsers → error like `browserType.launch: Executable doesn't
  exist`. Surface this and tell the user to run `npx playwright install`;
  do not run it automatically (downloads ~hundreds of MB).
- `npx playwright test` exits non-zero on failures — expected; parse JSON
  regardless.
