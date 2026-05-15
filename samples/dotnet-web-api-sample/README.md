# SampleApi — Debug Test Project

ASP.NET Core 8 Web API with EF Core + SQLite, designed as a test fixture for the `api-flow-debugger` skill. Contains intentional bugs across multiple categories: runtime errors, N+1 query patterns, slow queries, and a build-fail scenario.

## Run

```bash
cd samples/dotnet-web-api-sample
dotnet restore
ASPNETCORE_ENVIRONMENT=Development dotnet run
# Server listens at http://localhost:5000 (see Properties/launchSettings.json)
```

On first run a `sample.db` SQLite file is created and seeded with 20 users × 5 orders.

EF Core SQL logging is enabled by default via `appsettings.Development.json` → `Microsoft.EntityFrameworkCore.Database.Command=Information`.

---

## Test Endpoints (for api-flow-debugger)

### 1. Healthy baseline — single query

```bash
curl http://localhost:5000/api/healthy-user/1
```

Returns 200 with a single user. ONE `SELECT` against `Users`. No issues — used as the green-path baseline.

### 2. N+1 detection demo

```bash
curl http://localhost:5000/api/users-with-orders
```

Returns 200 with users + orders. INTENTIONALLY runs **21 queries**: 1 for users + 1 per user for orders. The skill should detect `n_plus_one_detected = true` with `shape_group` repetition ≥ 20.

Source: [Services/DebugTestService.cs:25](Services/DebugTestService.cs)

### 3. Optimal counterpart — N+1 fixed

```bash
curl http://localhost:5000/api/users-with-orders-optimal
```

Returns same data as endpoint #2 but uses `.Include(u => u.Orders)` — single JOIN, **2-3 queries total**. No N+1 flag.

### 4. Slow query detection

```bash
curl "http://localhost:5000/api/slow-search?q=User"
```

Returns 200 but the service does `await Task.Delay(150)` + `LIKE %q%` query. The skill should flag the endpoint with `is_slow` on the query and `db_bound_ratio` showing DB time dominates.

### 5. Existing runtime-error endpoints (from original sample)

```bash
# Works — 200
curl http://localhost:5000/api/users/1

# Breaks — 500 InvalidCastException
curl http://localhost:5000/api/users/abc
```

These use the original in-memory `UserService` with `(int)Convert.ChangeType(...)` cast that throws for non-integer IDs. Useful for testing checkpoint failure mapping.

---

## Build-Fail Test (Phase 2.5)

Verify that `api-flow-debugger` Phase 2.5 catches compile errors before attempting to start the server.

### Activate the fixture

```bash
mv BuildFailDemo/BrokenEndpoint.cs.broken BuildFailDemo/BrokenEndpoint.cs
```

Now `dotnet build --no-restore` will fail with `CS1002`, `CS1003`, `CS0103` errors.

### Run the skill

Trigger the skill against any endpoint. Expected behavior:

1. Phase 2.5 runs `dotnet build --no-restore`, exits non-zero.
2. Last 30 lines of build output are shown.
3. Skill prompts: `Build failed. Abort and generate partial report, or continue anyway? [abort/continue]`.
4. `abort` → partial HTML report with `Build & Dependencies` section showing failure + error summary; Phases 3–5 skipped.
5. `continue` → proceeds with a warning that the running binary may not reflect current source.

### Restore

```bash
mv BuildFailDemo/BrokenEndpoint.cs BuildFailDemo/BrokenEndpoint.cs.broken
```

---

## Checkpoint Map (reference for skill verification)

```
[1] Router      → Controllers/DebugTestController.cs:8   ([Route("api")])
[2] Middleware  → Program.cs middleware pipeline (none custom)
[3] Handler     → DebugTestController.<endpoint>()
[4] Service     → DebugTestService.<method>Async()
[5] Data layer  → AppDbContext via EF Core → SQLite
```

The DB query trace from Phase 4 should populate Checkpoint 5 with all SQL commands.

---

## Test Matrix Summary

| Scenario | Endpoint | Expected skill output |
|---|---|---|
| Healthy baseline | `GET /api/healthy-user/1` | 200, 1 query, no flags |
| N+1 | `GET /api/users-with-orders` | 200, 21 queries, n_plus_one_detected=true |
| N+1 fixed | `GET /api/users-with-orders-optimal` | 200, 2-3 queries, no N+1 |
| Slow query | `GET /api/slow-search?q=User` | 200, slow query flagged (>100ms) |
| Runtime error | `GET /api/users/abc` | 500, checkpoint [5] ❌, root_cause = InvalidCastException |
| Build fail | (any, after renaming broken file) | Phase 2.5 prompt, partial report with build error |
