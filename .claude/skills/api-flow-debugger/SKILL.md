---
name: api-flow-debugger
description: This skill should be used when the user wants to debug an API endpoint by tracing the request flow step by step, providing a curl command to test, investigating why an endpoint returns an error or unexpected response, needs to understand what happens inside the code as a request travels through middleware, handlers, and services — without modifying any source code. Also use when the user says "trace this request", "debug this curl", "why does this endpoint fail", or needs to detect performance issues like N+1 queries and bottlenecks.
version: 0.2.0
tools: Read, Glob, Grep, Bash
---

# API Flow Debugger

Trace a full API request lifecycle from curl command to response — without modifying source code. Maps routes, middleware, handlers, and services. Generates an HTML debug report with timeline, HTTP details, and performance analysis (N+1, bottlenecks).

## Input

Accepts a curl command from the user. Example:
```bash
curl -X POST http://localhost:3000/api/users/123 \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"name": "John"}'
```

---

## Phase 1 — Parse & Validate Curl Command

Extract from the curl string:
- **Method**: `-X GET/POST/PUT/DELETE` (default GET if absent)
- **URL**: full URL including path and query params
- **Headers**: all `-H` flags
- **Body**: `-d`, `--data`, `--data-raw`, `--data-binary`
- **Port**: from URL (default 80/443, or custom)

Auto-enhance before executing — do NOT silently change, show the enhanced version first:

| Missing | Auto-add |
|---------|----------|
| No `Content-Type` but has body | `Content-Type: application/json` |
| No `Accept` header | `Accept: application/json` |
| Token placeholder `<TOKEN>`, `YOUR_TOKEN`, `{token}` | Ask user for real value |
| `localhost` but port unclear | Detect from config (see Phase 3) |

Print the final curl to be used and ask user to confirm if any changes were made.

---

## Phase 2 — Detect Stack & Map Code Flow

**Step 1 — Detect tech stack:**

```bash
# Check for project config files
ls package.json pyproject.toml go.mod *.csproj *.sln pom.xml Cargo.toml composer.json Gemfile 2>/dev/null
```

| File found | Stack |
|-----------|-------|
| `package.json` | Node.js (check `dependencies` for express/fastify/koa/nestjs) |
| `pyproject.toml` / `requirements.txt` | Python (check for fastapi/django/flask) |
| `go.mod` | Go (check imports for gin/fiber/echo/chi) |
| `*.csproj` / `*.sln` / `Program.cs` | C# .NET (check for `Microsoft.AspNetCore`) |
| `pom.xml` / `build.gradle` | Java/Kotlin (check for spring-boot) |
| `composer.json` | PHP/Laravel |
| `Gemfile` | Ruby on Rails |

**Step 2 — Find entry point:**

```bash
# Node.js
ls src/main.ts src/index.ts app.js server.js index.js 2>/dev/null

# Python
ls main.py app.py wsgi.py asgi.py 2>/dev/null

# Go
ls main.go cmd/*/main.go 2>/dev/null

# C# .NET
ls Program.cs Startup.cs 2>/dev/null
```

**Step 3 — Build Checkpoint Map** for the endpoint from the curl:

Trace in this order (adapt grep patterns from `references/flow-mapping-patterns.md`):

```
Checkpoint 1: Router — file:line where route is registered
Checkpoint 2: Middleware[N] — each middleware in order (auth, validation, logging...)
Checkpoint 3: Handler/Controller — function handling the request
Checkpoint 4: Service — business logic call(s)
Checkpoint 5: Data layer — DB query / external HTTP call
```

For each checkpoint record: `{ id, label, file, line, type, estimated_db_calls }`.

---

## Phase 2.5 — Verify Build & Dependencies

Compile-check the project BEFORE starting the server. Catches errors and missing dependencies early instead of letting Phase 3 fail with a confusing server-start error or running a stale cached binary.

See `references/build-verification.md` for per-stack commands and error parsing.

**Step 1 — Check dependencies are installed:**

| Stack | Check |
|-------|-------|
| Node.js | `test -d node_modules` |
| Python | `python -m pip check` (exit 0) |
| Go | `go mod verify` |
| .NET | `test -f obj/project.assets.json` |
| Java (Maven) | `test -d ~/.m2/repository` |
| Java (Gradle) | `./gradlew dependencies --offline` (exit 0) |
| PHP | `composer validate --no-check-publish` |
| Ruby | `bundle check` |

If missing → attempt the non-destructive install fallback from `build-verification.md` once.

**Step 2 — Run the non-mutating build command:**

| Stack | Command |
|-------|---------|
| Node.js (TS) | `npx tsc --noEmit` (or `npm run build` if script exists) |
| Python | `python -m py_compile <entry>` + `python -c "import <main_module>"` |
| Go | `go build -o /dev/null ./...` (Windows: `NUL`) |
| .NET | `dotnet build --no-restore` (fallback `dotnet build`) |
| Java (Maven) | `mvn -q compile` |
| Java (Gradle) | `./gradlew compileJava -q` |
| PHP | `php -l <entry>` |
| Ruby | `ruby -c <entry>` |

Capture stdout+stderr and timing:

```bash
START=$(date +%s%3N)
<build_command> > /tmp/build-output.log 2>&1
BUILD_EXIT=$?
BUILD_DURATION_MS=$(( $(date +%s%3N) - START ))
```

**Step 3 — On failure, prompt the user:**

If `BUILD_EXIT != 0`:

1. Parse first error line using stack-specific regex (see `build-verification.md`).
2. Print error summary + last 30 lines of `build-output.log`.
3. **Ask the user**: `Build failed. Abort and generate partial report, or continue anyway? [abort/continue]`.
4. If `abort`: skip Phases 3/4/5, jump to Phase 6 with `build.status = "failed"` and `user_choice = "abort"` → partial HTML report.
5. If `continue`: proceed to Phase 3 with `build.status = "failed_user_continued"` → report will warn that traced binary may not reflect current source.

**Step 4 — Record to report object:**

```
build = {
  status: "passed" | "failed" | "skipped" | "failed_user_continued",
  command: "<build_command>",
  duration_ms: <BUILD_DURATION_MS>,
  output_tail: "<last 30 lines>",
  error_summary: "<first parsed error or null>",
  user_choice: "abort" | "continue" | null
}
```

---

## Phase 3 — Start Server in Debug Mode

**Step 1 — Check if server is already running:**

```bash
# Detect port from URL, then check
netstat -an | grep ":PORT" | grep LISTEN   # Unix
netstat -an | findstr ":PORT"              # Windows
```

If already listening → skip to Phase 4.

**Step 2 — Detect config port (if URL says localhost without explicit port):**

```bash
# Node.js
grep -r "port\|PORT\|listen" --include="*.json" --include="*.env" --include="*.js" --include="*.ts" -l | head -5

# C# .NET
cat Properties/launchSettings.json 2>/dev/null | grep -i "applicationUrl\|port"

# Python
grep -r "port\|uvicorn\|runserver" --include="*.py" --include="*.env" -l | head -5
```

**Step 3 — Start with maximum debug logging** (no code changes, env vars only):

See `references/debug-env-vars.md` for full list. Key commands:

| Stack | Debug start command |
|-------|-------------------|
| Express | `DEBUG=express:* node <entry>` |
| Fastify | `LOG_LEVEL=trace node <entry>` |
| NestJS | `LOG_LEVEL=verbose node dist/main` |
| FastAPI | `LOG_LEVEL=debug uvicorn <module>:app --reload` |
| Django | `DEBUG=True python manage.py runserver` |
| Flask | `FLASK_DEBUG=1 flask run` |
| Gin | `GIN_MODE=debug go run .` |
| Fiber | `go run .` |
| **ASP.NET Core** | `ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_LOGGING__LOGLEVEL__DEFAULT=Debug dotnet run` |
| Spring Boot | `LOGGING_LEVEL_ROOT=DEBUG ./mvnw spring-boot:run` |
| Laravel | `APP_DEBUG=true php artisan serve` |
| Rails | `RAILS_LOG_LEVEL=debug rails server` |

**ORM SQL logging is always enabled.** Append the ORM-specific env vars from `references/debug-env-vars.md#orm-sql-logging` to the start command. Example for .NET + EF Core:

```bash
ASPNETCORE_ENVIRONMENT=Development \
ASPNETCORE_LOGGING__LOGLEVEL__DEFAULT=Debug \
ASPNETCORE_LOGGING__LOGLEVEL__MICROSOFT_ENTITYFRAMEWORKCORE_DATABASE_COMMAND=Information \
dotnet run
```

For stacks where SQL logging cannot be enabled via env vars (GORM, Django default, Sequelize default, Laravel default, Mongoose), print a one-line warning and suggest the workaround from the Limitations subsection. The trace will still capture HTTP and checkpoint data — only per-query analysis will be empty.

Start in background, capture output:
```bash
<debug-command> > /tmp/server-debug.log 2>&1 &
SERVER_PID=$!
# Wait up to 10s for port to open
for i in {1..10}; do netstat -an | grep ":PORT" | grep LISTEN && break; sleep 1; done
echo "Server PID: $SERVER_PID"
```

If server fails to start → print last 30 lines of log, stop, report error.

---

## Phase 4 — Execute Curl & Capture

Build the enhanced curl with verbose output and timing:

```bash
curl -v \
  -w "\n---TIMING---\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}\nTIME_CONNECT:%{time_connect}\nTIME_STARTTRANSFER:%{time_starttransfer}\nSIZE_DOWNLOAD:%{size_download}\n" \
  [original curl flags and URL] \
  2>&1
```

Capture simultaneously:
- Full curl output (headers + body + timing block)
- Server log since request started: `tail -f /tmp/server-debug.log`

Parse from output:
- `HTTP_CODE` → status code
- Response headers (lines after `< ` in verbose output)
- Response body (after blank line)
- `TIME_TOTAL`, `TIME_CONNECT`, `TIME_STARTTRANSFER` (TTFB)
- From server log: stack traces, DB query logs, warning/error lines

**Pre-process log** (required before any pattern matching — see `references/log-parsing.md`):

```bash
# Strip ANSI codes + normalize line endings → clean canonical log
sed -E 's/\x1b\[[0-9;]*[mGKHF]//g' /tmp/server-debug.log \
  | tr -d '\r' > /tmp/server-debug.clean.log
```

All subsequent pattern matching runs on `server-debug.clean.log`, NOT the raw file.

**DB query count** — use anchored per-framework pattern (NOT raw `SELECT|INSERT` keywords, which match stack traces and JSON bodies):

```bash
# Example — EF Core (.NET)
rg --pcre2 -c '^(info|dbug):\s+Microsoft\.EntityFrameworkCore\.Database\.Command' \
  /tmp/server-debug.clean.log

# Fallback if rg unavailable
grep -E -c '^(info|dbug):[[:space:]]+Microsoft\.EntityFrameworkCore\.Database\.Command' \
  /tmp/server-debug.clean.log
```

Pick the pattern matching the detected stack from `references/log-parsing.md#anchored-patterns-per-framework`.

**Step — DB Query Log Extraction** (structured):

Produce a `db_queries[]` array — one object per query with `{ index, sql, sql_raw, params, duration_ms, timestamp, checkpoint_id, is_slow, shape_group }`.

1. Apply the per-ORM extraction pattern from `references/performance-analysis.md#structured-query-list-extraction` to `server-debug.clean.log`.
2. Normalize each SQL (literals → `?`, collapse whitespace) and compute `shape_group` as SHA-1 prefix of normalized SQL.
3. Tag `is_slow = duration_ms > 100`.
4. Correlate to checkpoints using timestamp windowing (assign latest checkpoint whose entry timestamp ≤ query timestamp).
5. Compute `db_summary` (total/unique_shapes/total_ms/slow_count/n_plus_one_detected/db_bound_ratio).

Store `db_queries[]` and `db_summary` for Phase 5 and Phase 6.

---

## Phase 5 — Correlate, Analyze & Detect Issues

**Step 1 — Map logs to checkpoints:**

For each checkpoint from Phase 2, search the server log for evidence it was reached (function name, file name, log message pattern). Mark each checkpoint ✅ (reached) or ❌ (not reached / errored).

**Step 2 — Classify the issue:**

| HTTP Code | Analysis focus |
|-----------|---------------|
| 401 / 403 | Auth middleware — check token validation, permissions |
| 404 | Router — route not matched, check path and method |
| 400 / 422 | Request validation — check body schema, required fields |
| 500 | Runtime error — find stack trace in logs, identify file:line |
| 200 but wrong body | Logic bug — trace service return value |
| Timeout / very slow | Performance — identify slow checkpoint |

**Step 3 — Performance analysis** (uses structured `db_queries[]` from Phase 4 — see `references/performance-analysis.md#per-query-analysis-rules`):

- **N+1 (confirmed)**: group queries by `shape_group`; flag when `same_shape_count >= 5 AND same_shape_count >= 0.5 * total_queries`. Include the offending shape's normalized SQL and group count as evidence.
- **Slow queries**: filter `db_queries[]` where `is_slow == true`. Report each with `sql`, `duration_ms`, and the checkpoint that triggered it.
- **Per-checkpoint DB roll-up**: sum `duration_ms` per `checkpoint_id`. A checkpoint with `db_ms > 500` is a strong bottleneck candidate.
- **DB-bound bottleneck**: `ratio = db_total_ms / server_processing_ms`. If `ratio > 0.6`, flag with the ratio value (e.g., "94% of server processing time spent in DB").
- **HTTP-level bottleneck**: TIME_STARTTRANSFER / TIME_TOTAL > 0.7 → server-side processing, not network.
- **Missing pagination**: Response array size > 100 items with no `page` / `limit` / `cursor` / `totalPages` metadata.

**Step 4 — Debugger attachment (if logs insufficient):**

If root cause still unclear, suggest (do not execute without user approval):

| Stack | Command |
|-------|---------|
| Node.js | `node --inspect <entry>` then open `chrome://inspect` |
| Python | `python -m debugpy --listen 5678 -m uvicorn main:app` |
| Go | `dlv debug .` |
| **C# .NET** | Attach VS/Rider debugger to PID, or: `dotnet-trace collect --process-id <pid> --providers Microsoft-Extensions-Logging` |

---

## Phase 6 — Generate HTML Report & Auto-Open

Collect all data into a structured object:

```
report = {
  timestamp, duration,
  request: { method, url, headers, body, curl_enhanced },
  stack: { framework, version, entry_point },
  build: {
    status,              // "passed" | "failed" | "skipped" | "failed_user_continued"
    command,
    duration_ms,
    output_tail,         // last 30 lines
    error_summary,       // first parsed error line or null
    user_choice          // "abort" | "continue" | null
  },
  checkpoints: [ { id, label, file, line, status, log_evidence, timing_ms, db_ms } ],
  http: { status_code, response_headers, response_body },
  timing: { connect_ms, ttfb_ms, total_ms },
  db_queries: [ {
    index, sql, sql_raw, params,
    duration_ms,         // null if ORM didn't report
    timestamp,           // ISO 8601 or null
    checkpoint_id,       // mapped via timestamp window
    is_slow,             // duration_ms > 100
    shape_group          // SHA-1 prefix of normalized SQL
  } ],
  db_summary: {
    total_queries, unique_shapes, total_db_ms,
    slow_query_count, n_plus_one_detected,
    n_plus_one_shape_group, db_bound_ratio
  },
  performance_issues: [ { type, description, evidence } ],
  root_cause: "...",
  evidence_lines: [...],
  suggested_fix: "..."
}
```

**Build-failed case**: if `build.status` is `"failed"` and `build.user_choice == "abort"`, render a *partial* report — fill `build` section, skip checkpoints/http/timing/db_queries (leave as defaults), set `root_cause` from `build.error_summary` and `suggested_fix` to point at the failing file:line from the build output.

Read `assets/report-template.html` and replace all `{{PLACEHOLDER}}` values with report data (JSON-encode complex objects, escape HTML in strings).

Save as `debug-report-YYYYMMDD-HHmmss.html` in the current working directory.

Auto-open by OS:
```bash
# Detect OS and open
uname -s 2>/dev/null | grep Darwin && open "debug-report-*.html"    # macOS
uname -s 2>/dev/null | grep Linux  && xdg-open "debug-report-*.html" # Linux
cmd.exe /c start "" "debug-report-YYYYMMDD-HHmmss.html" 2>/dev/null  # Windows
```

Print the path to the report and tell the user it's been opened.

---

## Cleanup

After session ends or on user request:
```bash
kill $SERVER_PID 2>/dev/null  # Stop debug server if we started it
rm /tmp/server-debug.log 2>/dev/null
```

---

## References

- `references/build-verification.md` — Per-stack build verification commands (Phase 2.5)
- `references/debug-env-vars.md` — Full debug start commands + ORM SQL logging per framework
- `references/flow-mapping-patterns.md` — Grep patterns to find routes/handlers per stack
- `references/log-parsing.md` — Precise log parsing (ANSI strip, anchored regex, multiline, cross-platform)
- `references/performance-analysis.md` — N+1 detection, structured query extraction, bottleneck thresholds
- `references/trace-report-format.md` — Text fallback report format
- `assets/report-template.html` — HTML report template with placeholders
