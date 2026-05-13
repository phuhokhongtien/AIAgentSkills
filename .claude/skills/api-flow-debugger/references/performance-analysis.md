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
