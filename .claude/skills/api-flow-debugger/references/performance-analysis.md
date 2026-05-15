# Performance Analysis Guide

How to detect and classify performance issues from captured logs and timing data — without modifying source code.

---

## N+1 Query Detection

### What is N+1
A controller fetches a list of N items, then executes 1 additional query *per item* to load related data — resulting in N+1 total queries instead of 1-2 (a list query + one JOIN/include).

### How to detect from logs

**Step 1 — Count DB queries in the log window:**
```bash
# Generic SQL patterns
grep -c "SELECT\|INSERT\|UPDATE\|DELETE" /tmp/server-debug.log

# EF Core (.NET)
grep -c "Executed DbCommand" /tmp/server-debug.log

# TypeORM / Sequelize (Node.js)
grep -c "query:" /tmp/server-debug.log

# Django ORM
grep -c "\(0\.\|[0-9]\+\.[0-9]\+\) SELECT" /tmp/server-debug.log

# SQLAlchemy (Python)
grep -c "SELECT\|BEGIN\|COMMIT" /tmp/server-debug.log

# GORM (Go)
grep -c "\[rows:" /tmp/server-debug.log

# Hibernate (Java)
grep -c "Hibernate: select" /tmp/server-debug.log
```

**Step 2 — Detect the pattern:**

N+1 signature in logs:
```
SELECT * FROM users WHERE id = 1        ← initial list query
SELECT * FROM orders WHERE user_id = 1  ← per-item query #1
SELECT * FROM orders WHERE user_id = 2  ← per-item query #2
SELECT * FROM orders WHERE user_id = 3  ← per-item query #3
...                                      ← N more identical queries
```

Check with:
```bash
# Find repeated query patterns (same table, different parameter)
grep "SELECT.*FROM orders" /tmp/server-debug.log | sort | uniq -c | sort -rn | head -20
```

**Step 3 — Threshold:**

| Query count | Assessment |
|------------|------------|
| 1-3 | Normal |
| 4-10 | Possible N+1 for small lists |
| 10+ | Almost certainly N+1 |
| Query count ≈ response array length + 1 | Confirmed N+1 |

**Step 4 — Identify the fix:**

| Stack | N+1 Fix Pattern |
|-------|----------------|
| EF Core (.NET) | Add `.Include(u => u.Orders)` to LINQ query |
| TypeORM | Add `relations: ['orders']` or use `QueryBuilder` with `leftJoinAndSelect` |
| Sequelize | Add `include: [{ model: Order }]` |
| SQLAlchemy | Use `joinedload()` or `selectinload()` |
| Django ORM | Use `prefetch_related('orders')` or `select_related` |
| GORM | Use `Preload("Orders")` |
| Hibernate | Use `@OneToMany(fetch = FetchType.EAGER)` or JOIN FETCH |

---

## Structured Query List Extraction

Beyond counting, produce a structured `db_queries[]` array for the report's rich viewer. Each entry: `{ index, sql, sql_raw, params, duration_ms, timestamp, checkpoint_id, is_slow, shape_group }`.

**Prerequisite**: log has been cleaned per `references/log-parsing.md` (ANSI-stripped, CRLF-normalized) and is at `server-debug.clean.log`.

### Per-ORM extraction patterns

| ORM | Capture Pattern (POSIX ERE / PCRE2) | Captures |
|---|---|---|
| EF Core | `Executed DbCommand \(([0-9]+)ms\) \[Parameters=\[([^\]]*)\][^,]*,[^=]*=[^,]*\]\s*(.+?)(?=^(info\|dbug\|warn\|fail):)` (multiline) | duration_ms, params, sql |
| TypeORM | `^\[([^\]]+)\] query: (.+?)\s+--\s+PARAMETERS:\s+(\[.*?\])?$` | timestamp, sql, params |
| Prisma | `^prisma:query\s+(.+?)$` then look for next `prisma:query` with `params:` | sql, params |
| Hibernate | `^Hibernate:\s+(.+?)$` + parse binding from `org.hibernate.type` TRACE lines | sql, params |
| Django ORM | `^\(([0-9]+\.[0-9]+)\)\s+(.+?);\s+args=(\(.*?\))$` | duration_seconds, sql, params |
| SQLAlchemy | Two-line: `INFO sqlalchemy.engine.\w+\s+(SELECT\|INSERT\|UPDATE\|DELETE)\s+(.+)` then `INFO sqlalchemy.engine.\w+\s+(\{.+?\}\|\[.+?\])` | sql, params (next line) |
| GORM | `^\[(\d+\.\d+)ms\]\s+\[rows:(-?\d+)\]\s+(.+)$` | duration_ms, rows, sql |
| Rails AR | `^\s+\w+\s+(\w+)\s+\(([0-9.]+)ms\)\s+(.+)$` | model_op, duration_ms, sql |
| Laravel (with logging) | `^\[[^\]]+\]\s+local\.INFO:\s+(.+?)\s+\| bindings:\s+(.+)$` | sql, params |

### Bash extractor example — EF Core

```bash
# Produce one JSON object per query
rg -U --pcre2 \
  'Executed DbCommand \((\d+)ms\)[^$]*?(?=^(info|dbug|warn|fail):)' \
  /tmp/server-debug.clean.log \
  | awk 'BEGIN{i=0}
    /Executed DbCommand/ {
      match($0, /\(([0-9]+)ms\)/, m);
      dur=m[1];
      sql="";
      next;
    }
    { sql = sql " " $0 }
    /^$/ {
      printf "{\"index\":%d,\"duration_ms\":%d,\"sql_raw\":\"%s\"}\n", i++, dur, sql;
      sql="";
    }'
```

### Bash extractor example — TypeORM

```bash
rg --pcre2 -o '^\[([^\]]+)\] query: (.+)$' \
  /tmp/server-debug.clean.log \
  | jq -R 'capture("\\[(?<ts>[^\\]]+)\\] query: (?<sql>.+)") | {timestamp: .ts, sql_raw: .sql}'
```

### Bash extractor example — Django ORM

```bash
rg --pcre2 -o '^\(([0-9]+\.[0-9]+)\)\s+(.+?);\s+args=(\(.*?\))$' \
  /tmp/server-debug.clean.log \
  | jq -R 'capture("\\((?<dur>[0-9.]+)\\)\\s+(?<sql>.+?);\\s+args=(?<params>.+)") |
           {duration_ms: (.dur|tonumber * 1000), sql_raw: .sql, params: .params}'
```

---

## Query Normalization (Shape Grouping)

Two queries that differ only in literal values belong to the same "shape" — this is the signature used for N+1 detection.

### Normalization algorithm

```
1. Replace integer literals:  \b\d+\b     →  ?
2. Replace single-quoted:     '[^']*'     →  ?
3. Replace double-quoted:     "[^"]*"     →  ?
4. Collapse whitespace:       \s+         →  (single space)
5. Trim leading/trailing whitespace.
```

### Example

```
Input:   SELECT * FROM users WHERE id = 42 AND email = 'a@b.com'
Output:  SELECT * FROM users WHERE id = ? AND email = ?
```

### Bash one-liner

```bash
echo "$sql_raw" \
  | sed -E "s/'[^']*'/?/g; s/\"[^\"]*\"/?/g; s/\b[0-9]+\b/?/g; s/[[:space:]]+/ /g" \
  | sed 's/^ //; s/ $//'
```

### Computing shape_group

Hash the normalized SQL → first 8 chars of SHA-1 is enough for grouping.

```bash
shape_group=$(echo "$normalized_sql" | sha1sum | cut -c1-8)
```

---

## Checkpoint Correlation

Map each extracted query to the checkpoint that produced it, using log timestamp windowing.

### Algorithm

1. From Phase 2, you have `checkpoints[]` with their log evidence lines (and timestamps from Phase 4 evidence collection).
2. Sort checkpoints by their entry timestamp ascending.
3. For each query, find the latest checkpoint whose entry timestamp ≤ query timestamp. That's its `checkpoint_id`.
4. If no checkpoint precedes the query (rare — pre-routing queries), assign `checkpoint_id = null`.

### Pseudocode

```
for query in queries:
  query.checkpoint_id = null
  for cp in sorted(checkpoints, by=entry_timestamp):
    if cp.entry_timestamp <= query.timestamp:
      query.checkpoint_id = cp.id
    else:
      break
```

If query timestamps are unavailable (some ORM logs lack them), fall back to ORDER (assume queries appear in log in execution order — assign to the latest checkpoint seen before this query in the log line index).

---

## Per-Query Analysis Rules

Once `db_queries[]` is populated, apply these rules to compute `db_summary` and detect issues.

### N+1 detection (structured)

```
group queries by shape_group → groups[]
for g in groups where g.count >= 5 and g.count >= 0.5 * total_queries:
  flag n_plus_one with g as evidence
```

### Slow query tagging

```
for q in db_queries:
  q.is_slow = (q.duration_ms != null and q.duration_ms > 100)
```

### Per-checkpoint DB-time roll-up

```
checkpoint_db_ms = {}
for q in db_queries:
  if q.checkpoint_id != null:
    checkpoint_db_ms[q.checkpoint_id] += (q.duration_ms or 0)
```

Annotate each checkpoint with its DB time. A checkpoint whose `db_ms > 500` is a strong candidate for the bottleneck.

### DB-bound bottleneck ratio

```
server_processing_ms = (TIME_STARTTRANSFER - TIME_CONNECT) * 1000
db_total_ms = sum(q.duration_ms or 0 for q in db_queries)
ratio = db_total_ms / server_processing_ms

if ratio > 0.6:
  flag "DB-bound bottleneck": <ratio>% of server processing time spent in DB
```

### db_summary output

```json
{
  "total_queries": 23,
  "unique_shapes": 4,
  "total_db_ms": 1734,
  "slow_query_count": 2,
  "n_plus_one_detected": true,
  "n_plus_one_shape_group": "a3f9b2c1",
  "db_bound_ratio": 0.94
}
```

---

## Bottleneck Detection

### From curl timing data

Extract from curl `-w` output:
```
TIME_CONNECT:    0.004s   ← network TCP handshake
TIME_STARTTRANSFER: 1.843s ← TTFB (time to first byte = server processing time)
TIME_TOTAL:      1.847s   ← total including download
```

**Calculate server processing time:**
```
server_processing_ms = (TIME_STARTTRANSFER - TIME_CONNECT) × 1000
```

**Thresholds:**
| Time | Classification |
|------|---------------|
| < 50ms | Fast — acceptable |
| 50-200ms | Moderate — investigate if trending up |
| 200-1000ms | Slow — performance issue |
| > 1000ms | Critical bottleneck |

### From server logs — identify which checkpoint is slow

Match log timestamps to checkpoints:
```bash
# Extract timestamp of each log line
grep -n "controller\|service\|repository\|query" /tmp/server-debug.log | head -50
```

If timestamps are present (ISO 8601 format), calculate delta between consecutive checkpoints.

**Common bottleneck causes by location:**

| Slow checkpoint | Likely cause |
|----------------|-------------|
| Router → Handler | Middleware overhead (auth, rate limiting) |
| Handler → Service | Serialization, validation of large payloads |
| Service → DB | Slow query, missing index, N+1 |
| DB → Response | Large result set, no pagination |
| Total > individual sum | GC pause, thread pool exhaustion |

---

## Slow Query Detection

### Log patterns per framework

**EF Core (.NET) — shows execution time:**
```
Executed DbCommand (347ms) [Parameters=[@id='?'], CommandText=SELECT...
                   ^^^
```
```bash
grep "Executed DbCommand" /tmp/server-debug.log | grep -E "\([0-9]{3,}ms\)"
```

**Django ORM:**
```
(0.347) SELECT ... [1 query]
```
```bash
grep -E "\([0-9]\.[0-9]{3,}\)" /tmp/server-debug.log
```

**TypeORM:**
```
query: SELECT ... -- took 347ms
```
```bash
grep "took [0-9]*ms" /tmp/server-debug.log | awk '{print $NF}' | sort -rn
```

**GORM (Go):**
```
[347.521ms] [rows:100] SELECT ...
```
```bash
grep -E "\[[0-9]+\.[0-9]+ms\]" /tmp/server-debug.log | grep -E "\[([0-9]{3,})\."
```

**Hibernate:**
```
select ... took 347 milliseconds
```

**Thresholds:**
| Query time | Classification |
|-----------|---------------|
| < 10ms | Fast |
| 10-100ms | Acceptable |
| 100-500ms | Slow — add index or optimize |
| > 500ms | Critical — investigate query plan |

---

## Missing Pagination Detection

**Signal:** Response body is a JSON array with > 100 items AND no pagination metadata.

Check for:
```bash
# Count items in response body (approximate)
echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else len(d.get('data',d.get('items',d.get('results',[])))))"

# Or simpler: count occurrences of a likely key
echo "$RESPONSE_BODY" | grep -o '"id"' | wc -l
```

If count > 100 and no `page`, `limit`, `offset`, `cursor`, `totalPages` in response → flag missing pagination.

---

## Memory / CPU Issues (Advanced)

Use dotnet-counters (.NET) or equivalent:

**C# .NET:**
```bash
dotnet-counters monitor --process-id <PID> \
  --counters System.Runtime[gc-heap-size,threadpool-queue-length,active-timer-count]
```

**Node.js:**
```bash
node --max-old-space-size=512 --inspect app.js
# Then in Chrome DevTools → Memory → Take heap snapshot
```

**Python:**
```bash
pip install memory-profiler
python -m memory_profiler app.py
```

---

## Performance Report Section

When writing to the HTML report, include:

```json
{
  "performance_issues": [
    {
      "type": "n_plus_one",
      "severity": "high",
      "description": "20 SELECT queries on `orders` table (1 per user in list)",
      "evidence": "grep output showing repeated queries",
      "checkpoint": "Checkpoint 5 — UserRepository.GetAllWithOrders()",
      "fix": "Add .Include(u => u.Orders) to the LINQ query in UserRepository.cs:34"
    },
    {
      "type": "slow_query",
      "severity": "medium",
      "description": "SELECT on users table took 347ms",
      "evidence": "Executed DbCommand (347ms) SELECT * FROM Users WHERE...",
      "checkpoint": "Checkpoint 5 — DB query",
      "fix": "Add index on users.email column (used in WHERE clause)"
    },
    {
      "type": "bottleneck",
      "severity": "high",
      "description": "Server processing: 1843ms (TTFB). DB layer accounts for ~1800ms.",
      "evidence": "TIME_STARTTRANSFER: 1.843s from curl timing",
      "checkpoint": "Checkpoint 5 — Data layer",
      "fix": "See query optimizations above"
    }
  ]
}
```
