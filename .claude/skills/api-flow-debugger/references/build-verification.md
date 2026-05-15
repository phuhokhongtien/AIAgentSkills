# Build Verification — Pre-flight Check

Reference for verifying a project compiles and dependencies are installed BEFORE starting the server in debug mode. Used by Phase 2.5 of the skill.

Goal: catch compile errors and missing dependencies early — with helpful output — rather than letting Phase 3 fail with a confusing server-start error, or worse, run an outdated cached binary that doesn't reflect current source code.

All commands here are **non-mutating** (no source code modification, no destructive side effects). Restore commands only fetch/install dependencies which is expected setup behavior.

---

## Dependency Presence Check

Run before the build command. If dependencies are missing, the build will fail anyway — better to report it clearly.

| Stack | Check Command | Pass Criteria |
|---|---|---|
| Node.js | `test -d node_modules && test -f node_modules/.package-lock.json` | Directory exists with lockfile metadata |
| Python (venv) | `python -c "import sys; print(sys.prefix != sys.base_prefix)"` | Output is `True` (virtualenv active) |
| Python (deps) | `python -m pip check` | Exit 0 (no broken requirements) |
| Go | `go mod verify` | Output `all modules verified` |
| .NET | `test -d obj && test -f obj/project.assets.json` | NuGet restore artifacts present |
| Java (Maven) | `test -d ~/.m2/repository` | Local Maven repo populated |
| Java (Gradle) | `./gradlew dependencies --offline` | Exit 0 |
| PHP | `composer validate --no-check-publish` | Exit 0 + `vendor/` exists |
| Ruby | `bundle check` | Output `The Gemfile's dependencies are satisfied` |

### Auto-install fallback

If dependency check fails, attempt non-destructive install once before failing the phase:

| Stack | Install Command |
|---|---|
| Node.js | `npm ci` (preferred, uses lockfile) or `npm install` |
| Python | `pip install -r requirements.txt` or `pip install -e .` |
| Go | `go mod download` |
| .NET | `dotnet restore` |
| Maven | `mvn dependency:resolve -q` |
| Gradle | `./gradlew dependencies` |
| PHP | `composer install --no-interaction` |
| Ruby | `bundle install` |

Capture stdout+stderr to `build-output.log` for the report.

---

## Non-mutating Build Commands

Each command compiles/type-checks WITHOUT running tests, generating release binaries, or modifying source.

| Stack | Build Command | What It Does |
|---|---|---|
| Node.js (TS) | `npx tsc --noEmit` | Type-check only, no JS output |
| Node.js (build script) | `npm run build` (if `build` script exists in package.json) | Run project's build pipeline |
| Python | `python -m py_compile <entry.py>` + `python -c "import <main_module>"` | Syntax check + import check |
| Go | `go build -o /dev/null ./...` (Unix) / `go build -o NUL ./...` (Windows) | Compile all packages, discard binary |
| .NET | `dotnet build --no-restore` → fallback `dotnet build` if restore needed | Compile assembly |
| Java (Maven) | `mvn -q compile` | Compile main sources only (no test) |
| Java (Gradle) | `./gradlew compileJava -q` | Compile main sources |
| PHP | `php -l <entry.php>` (syntax check) + `composer validate` | Lint + manifest validation |
| Ruby | `ruby -c <entry.rb>` (syntax check) + `bundle check` | Lint + bundle integrity |
| Rust | `cargo check` | Type-check without producing binary |

### Detect entry file per stack

```bash
# Node.js — look for build script first, else main entry
node -e "console.log(require('./package.json').main || 'index.js')"

# Python
ls main.py app.py wsgi.py asgi.py manage.py 2>/dev/null | head -1

# .NET — find the csproj
ls *.csproj **/*.csproj 2>/dev/null | head -1

# Go — main package
go list -f '{{.Dir}}' ./... 2>/dev/null | grep -v vendor | head -1
```

---

## Exit Code & Output Capture

Convention used throughout Phase 2.5:

### Capture stdout + stderr to a single file

```bash
# Unix
<build_command> > /tmp/build-output.log 2>&1
BUILD_EXIT=$?
```

```powershell
# Windows PowerShell
& <build_command> *> "$env:TEMP\build-output.log"
$BuildExit = $LASTEXITCODE
```

### Tail last 30 lines for the report

```bash
# Unix
tail -30 /tmp/build-output.log
```

```powershell
# Windows
Get-Content "$env:TEMP\build-output.log" -Tail 30
```

### Parse first error line

| Stack | Error Regex (POSIX ERE) |
|---|---|
| .NET (C#) | `error CS[0-9]+: ` |
| TypeScript | `error TS[0-9]+: ` |
| Go | `^[^:]+:[0-9]+:[0-9]+: ` |
| Python | `^(SyntaxError|ImportError|ModuleNotFoundError|IndentationError): ` |
| Java | `^\[ERROR\] ` |
| PHP | `Parse error: |PHP Fatal error: ` |
| Ruby | `^.*:[0-9]+:.*syntax error|undefined method` |
| Rust | `^error\[E[0-9]+\]: ` |

### Sample one-liner

```bash
grep -m1 -E 'error CS[0-9]+: ' /tmp/build-output.log
```

---

## Build Duration Capture

Wrap the build command to measure wall time:

```bash
# Unix
START=$(date +%s%3N)
<build_command> > /tmp/build-output.log 2>&1
BUILD_EXIT=$?
END=$(date +%s%3N)
BUILD_DURATION_MS=$((END - START))
```

```powershell
# Windows PowerShell
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& <build_command> *> "$env:TEMP\build-output.log"
$BuildExit = $LASTEXITCODE
$sw.Stop()
$BuildDurationMs = [int]$sw.ElapsedMilliseconds
```

---

## Decision Logic on Failure

If `BUILD_EXIT != 0`:

1. Print the parsed first-error line + last 30 lines of build-output.log.
2. **Prompt the user**: `Build failed. Abort and generate partial report, or continue anyway? [abort/continue]`.
3. Record `build.user_choice` in the report object.
4. If `abort`: skip Phase 3/4/5, jump to Phase 6 with `build.status = "failed"`, generate partial HTML report highlighting the build failure.
5. If `continue`: proceed to Phase 3 with `build.status = "failed_user_continued"` — the report will warn that traced binary may not reflect current source.

---

## Windows vs Unix Equivalents

| Concept | Unix | Windows (PowerShell) |
|---|---|---|
| Discard output | `> /dev/null` | `> $null` or `*> $null` |
| Discard binary | `-o /dev/null` | `-o NUL` |
| Tail file | `tail -30 file` | `Get-Content file -Tail 30` |
| Capture exit code | `$?` (boolean) / `$?` after `echo $?` | `$LASTEXITCODE` (integer for native exe) |
| Combine stdout+stderr | `2>&1` | `*>` (PowerShell 5.1+) |
| Path separator | `/` | `\` (but `/` often works in .NET tools) |
| Temp directory | `/tmp/` | `$env:TEMP\` |
| Command exists check | `command -v <name>` | `Get-Command <name> -ErrorAction SilentlyContinue` |

---

## Report Object Fields Produced

After Phase 2.5 runs, populate the report object:

```json
{
  "build": {
    "status": "passed | failed | skipped | failed_user_continued",
    "command": "dotnet build --no-restore",
    "duration_ms": 4823,
    "output_tail": "...(last 30 lines)...",
    "error_summary": "error CS0103: The name 'foo' does not exist...",
    "user_choice": "abort | continue | null"
  }
}
```

- `status = "skipped"` when stack detection failed or no recognized build command applies (e.g. a plain Python script with no entry detected).
- `error_summary = null` when build passed.
- `user_choice = null` when build passed (no prompt shown).
