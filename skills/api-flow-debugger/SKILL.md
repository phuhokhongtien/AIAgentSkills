---
name: api-flow-debugger
description: This skill should be used when the user wants to debug an API endpoint by tracing the request flow step by step, providing a curl command to test, investigating why an endpoint returns an error or unexpected response, needs to understand what happens inside the code as a request travels through middleware, handlers, and services — without modifying any source code. Also use when the user says "trace this request", "debug this curl", "why does this endpoint fail", or needs to detect performance issues like N+1 queries and bottlenecks.
version: 0.1.0
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

**DB query count**: grep server log for ORM query patterns:
```bash
grep -c "SELECT\|INSERT\|UPDATE\|DELETE\|Executing\|Executed DbCommand\|query" /tmp/server-debug.log
```

Store all raw data for Phase 5 and Phase 6.

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

**Step 3 — Performance analysis** (see `references/performance-analysis.md`):

- **N+1**: DB query count >> expected → flag with query pattern from logs
- **Bottleneck**: TIME_STARTTRANSFER / TIME_TOTAL > 0.7 → identify slow checkpoint
- **Slow query**: Any single query log entry showing > 100ms
- **Missing pagination**: Response array size > 100 items with no limit

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
  checkpoints: [ { id, label, file, line, status, log_evidence, timing_ms } ],
  http: { status_code, response_headers, response_body },
  timing: { connect_ms, ttfb_ms, total_ms },
  performance_issues: [ { type, description, evidence } ],
  root_cause: "...",
  evidence_lines: [...],
  suggested_fix: "..."
}
```

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

- `references/debug-env-vars.md` — Full debug start commands per framework
- `references/flow-mapping-patterns.md` — Grep patterns to find routes/handlers per stack
- `references/performance-analysis.md` — N+1 detection, bottleneck thresholds
- `references/trace-report-format.md` — Text fallback report format
- `assets/report-template.html` — HTML report template with placeholders
