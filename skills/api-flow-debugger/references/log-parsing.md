# Log Parsing — Precise Patterns

Reference for parsing server debug logs accurately. Replaces naive `grep "SELECT\|INSERT..."` patterns that produce false positives (matches in stack traces, JSON bodies, comments, CLI echo) and false negatives (multi-line queries counted as multiple rows, ANSI color codes breaking regex).

Apply this pipeline before any analysis in Phase 4 and Phase 5 of the skill.

---

## Pre-processing Pipeline

Always normalize the raw server log into a canonical clean file before pattern matching.

### Step 1 — Strip ANSI escape codes

Dev loggers (Express morgan, NestJS, Spring Boot, Rails) inject color codes like `\x1b[32m` that break regex matching and corrupt extracted text.

```bash
# Unix
sed -E 's/\x1b\[[0-9;]*[mGKHF]//g' /tmp/server-debug.log > /tmp/server-debug.clean.log
```

```powershell
# Windows PowerShell
(Get-Content "$env:TEMP\server-debug.log" -Raw) `
  -replace '\x1b\[[0-9;]*[mGKHF]','' `
  | Set-Content "$env:TEMP\server-debug.clean.log" -Encoding utf8
```

### Step 2 — Normalize line endings

CRLF on Windows logs breaks `$` anchors in regex.

```bash
# Unix
tr -d '\r' < /tmp/server-debug.clean.log > /tmp/server-debug.clean.log.tmp \
  && mv /tmp/server-debug.clean.log.tmp /tmp/server-debug.clean.log
```

```powershell
# Windows — already handled by Set-Content above; if needed:
(Get-Content "$env:TEMP\server-debug.clean.log" -Raw) `
  -replace "`r","" `
  | Set-Content "$env:TEMP\server-debug.clean.log" -Encoding utf8
```

### Step 3 — Canonical clean file

All subsequent patterns in Phase 4 and Phase 5 run against `server-debug.clean.log` (NOT the raw `server-debug.log`).

---

## Tool Preference Order

Pick the highest-priority tool available on the host.

| Priority | Tool | Strengths | Caveats |
|---|---|---|---|
| 1 | `rg` (ripgrep) | Multiline native (`-U`), PCRE2 (`-P` or `--pcre2`), no ANSI confusion, cross-platform single binary | Must be installed (not default on Windows) |
| 2 | `grep -E` | POSIX ERE, available everywhere on Unix | No PCRE lookahead, line-oriented only |
| 3 | `Select-String` (PowerShell) | Native Windows, regex via `-Pattern`, context via `-Context` | Different regex flavor (.NET) |
| 4 | `findstr` (Windows) | Last resort — literal substring, no alternation, no anchors | Very limited; use only if all above unavailable |

### Detect available tool

```bash
# Unix
if command -v rg >/dev/null 2>&1; then PARSER=rg; else PARSER="grep -E"; fi
```

```powershell
# Windows PowerShell
$Parser = if (Get-Command rg -ErrorAction SilentlyContinue) { 'rg' } else { 'Select-String' }
```

---

## Anchored Patterns per Framework

Replacement for the naive `grep -c "SELECT\|INSERT\|UPDATE\|DELETE"` — these patterns are anchored to the log-line prefix that the framework emits, so they cannot match SQL keywords inside stack traces, JSON request bodies, or comments.

### EF Core (.NET)

```
^(info|dbug|warn|fail|trce|crit):\s+Microsoft\.EntityFrameworkCore\.Database\.Command.*Executed DbCommand \((\d+)ms\)
```

Captures: `$1` = log level, `$2` = duration_ms.

```bash
rg --pcre2 '^(info|dbug):\s+Microsoft\.EntityFrameworkCore\.Database\.Command' /tmp/server-debug.clean.log
```

### TypeORM (Node.js)

```
^\[.*?\] query: (.+)$
```

Captures: `$1` = SQL text. Anchored on bracket timestamp prefix.

### Sequelize (Node.js)

```
^Executing \(default\): (.+)$
```

### Prisma (Node.js)

```
^prisma:query\s+(.+)$
```

### Hibernate (Java)

```
^Hibernate:\s+(select|insert|update|delete)\s+
```

Case-sensitive — the `Hibernate:` prefix is uppercase, the SQL keyword is lowercase by Hibernate convention.

### Django ORM (Python)

```
^\(([0-9]+\.[0-9]+)\)\s+(SELECT|INSERT|UPDATE|DELETE)
```

Captures: `$1` = duration_seconds, `$2` = operation. Parenthesized duration is the Django signature.

### SQLAlchemy (Python, echo=True mode)

```
^[0-9-]+\s[0-9:,]+\s+INFO\s+sqlalchemy\.engine\.\w+\s+(SELECT|INSERT|UPDATE|DELETE)
```

### GORM (Go)

```
^\[(\d+\.\d+)ms\]\s+\[rows:(\d+)\]\s+(.+)$
```

Captures: `$1` = duration_ms, `$2` = row count, `$3` = SQL.

### Rails ActiveRecord (Ruby)

```
^\s+\w+\s+Load\s+\(([0-9.]+)ms\)\s+(.+)$
```

Captures: `$1` = duration_ms, `$2` = SQL.

### Laravel (PHP, with query log enabled)

```
^\[[0-9-]+\s[0-9:]+\]\s+local\.INFO:\s+(SELECT|INSERT|UPDATE|DELETE)
```

---

## Multi-line Query Handling

ORMs that pretty-print SQL emit queries spanning multiple lines. Without multi-line awareness, line-counting under-reports and SQL extraction is truncated.

### Example — EF Core multi-line block

```
info: Microsoft.EntityFrameworkCore.Database.Command[20101]
      Executed DbCommand (15ms) [Parameters=[@p0='?'], CommandType='Text', CommandTimeout='30']
      SELECT u.Id, u.Name, u.Email
      FROM Users AS u
      WHERE u.Email = @p0
```

This is ONE query, not five.

### Pattern with ripgrep multiline

```bash
rg -U --pcre2 -o \
  'Executed DbCommand \((\d+)ms\)[\s\S]+?(?=^(info|dbug|warn|fail|trce|crit):)' \
  /tmp/server-debug.clean.log
```

`-U` enables multiline mode; the lookahead `(?=^(info|...):)` stops the match at the next log-line prefix.

### Pattern with awk (no ripgrep)

```bash
awk '
  /Executed DbCommand/ { in_query=1; print; next }
  in_query && /^(info|dbug|warn|fail|trce|crit):/ { in_query=0 }
  in_query { print }
' /tmp/server-debug.clean.log
```

---

## False Positive Filters

Always exclude these line types before counting queries. SQL keywords often appear inside them.

### Stack traces

```
at SomeClass.SomeMethod()              # .NET
  File "/path/to/file.py", line 42     # Python
\tat com.example.Class.method(File:42) # Java
    at /node_modules/.../file.js:42    # Node.js
```

Exclude pattern (rg):

```bash
rg -v '^\s*(at\s|File\s+"|\tat\s|>\s|\$\s)' /tmp/server-debug.clean.log
```

### CLI echo lines

Lines starting with `> ` or `$ ` are shell prompt echoes — not server log content.

### SQL inside JSON request body

If a request body contains `{"query": "SELECT * FROM ..."}`, the SQL keyword is data, not a query execution. Exclude by checking line context — these lines typically appear inside a request-log block bracketed by `{` and `}` and contain `"body":` or similar JSON markers.

### SQL comments

Lines containing `--` before a SQL keyword (`-- SELECT all active users`) are comments inside scripts.

```bash
rg -v '^\s*--' /tmp/server-debug.clean.log
```

---

## Structured (JSON) Log Parsing

Modern frameworks (Winston, Serilog with JSON formatter, Python structlog, NestJS with pino) emit one-JSON-per-line logs. Regex on these is fragile — prefer `jq`.

### Detect JSON log mode

The first non-empty line matches `^\{.*\}$` and parses as JSON.

```bash
head -1 /tmp/server-debug.clean.log | jq . > /dev/null 2>&1 && echo "JSON mode" || echo "Text mode"
```

### Extract SQL commands from JSON log

```bash
# EF Core via Serilog JSON
jq -r 'select(.Properties.SourceContext // "" | test("EntityFrameworkCore")) | .RenderedMessage' \
  /tmp/server-debug.clean.log
```

```bash
# Generic — extract message field
jq -r 'select(.message // "" | test("(?i)SELECT|INSERT|UPDATE|DELETE")) | .message' \
  /tmp/server-debug.clean.log
```

### Fallback without `jq`

```bash
rg -o '"message":\s*"([^"]+)"' --pcre2 /tmp/server-debug.clean.log
```

---

## Cross-platform Wrappers

Reusable shell function. Pick by host OS.

### Unix bash

```bash
parse_log() {
  local pattern="$1"
  local file="${2:-/tmp/server-debug.clean.log}"
  if command -v rg >/dev/null 2>&1; then
    rg --pcre2 "$pattern" "$file"
  else
    grep -E "$pattern" "$file"
  fi
}

# Usage
parse_log '^(info|dbug):\s+Microsoft\.EntityFrameworkCore'
```

### Windows PowerShell

```powershell
function Parse-Log {
  param([string]$Pattern, [string]$File = "$env:TEMP\server-debug.clean.log")
  if (Get-Command rg -ErrorAction SilentlyContinue) {
    rg --pcre2 $Pattern $File
  } else {
    Select-String -Path $File -Pattern $Pattern
  }
}

# Usage
Parse-Log '^(info|dbug):\s+Microsoft\.EntityFrameworkCore'
```

---

## Quick Sanity Check

After applying the pipeline, verify the clean log is usable:

```bash
# Should be > 0 if server is logging anything
wc -l /tmp/server-debug.clean.log

# Should be 0 — no ANSI codes remaining
rg -c $'\x1b' /tmp/server-debug.clean.log || echo "Clean"

# Spot-check first 5 lines
head -5 /tmp/server-debug.clean.log
```

If the clean log is empty after pre-processing, the server isn't emitting logs at the expected verbosity — check Phase 3 env vars and `references/debug-env-vars.md` for the right `LOG_LEVEL`.
