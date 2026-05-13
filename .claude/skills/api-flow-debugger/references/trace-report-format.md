# Trace Report Format

Text-based fallback report when the HTML report cannot be opened. Also used as the data model for generating the HTML report.

---

## Full Text Report Template

```
╔══════════════════════════════════════════════════════════════════╗
║                    API FLOW DEBUG REPORT                         ║
╚══════════════════════════════════════════════════════════════════╝
Generated: 2024-01-15 14:32:05
Duration:  1843ms total

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Method:  POST
URL:     http://localhost:5000/api/users/123
Headers:
  Authorization: Bearer eyJhbGc...  [truncated]
  Content-Type: application/json    [auto-added]
  Accept: application/json          [auto-added]
Body:
  {"name": "John"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 STACK DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Framework:  ASP.NET Core Web API
Runtime:    .NET 8.0.1
Entry:      Program.cs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CHECKPOINT TRACE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ [1]  Router matched
        POST /api/users/{id} → UsersController.cs:12
        Evidence: info: Microsoft.AspNetCore.Routing[1] Request matched

✅ [2]  Middleware: AuthenticationMiddleware
        JwtBearerHandler validated token
        File: AuthMiddleware.cs:28  (~2ms)
        Evidence: info: Authentication successful, user=admin@example.com

✅ [3]  Middleware: RequestLoggingMiddleware
        File: LoggingMiddleware.cs:15  (~1ms)

✅ [4]  Handler: UsersController.UpdateUser()
        File: Controllers/UsersController.cs:67  (~5ms)
        Evidence: dbug: Executing action method UsersController.UpdateUser

❌ [5]  Service: UserService.UpdateAsync()
        File: Services/UserService.cs:89
        EXCEPTION THROWN HERE
        Evidence: fail: System.InvalidCastException: Specified cast is not valid
                    at UserService.UpdateAsync() in UserService.cs:line 89

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HTTP RESPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:  500 Internal Server Error
Headers:
  Content-Type: application/problem+json; charset=utf-8
Body:
  {
    "type": "https://tools.ietf.org/html/rfc7231#section-6.6.1",
    "title": "An error occurred while processing your request.",
    "status": 500,
    "traceId": "00-abc123..."
  }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TIMING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TCP Connect:    4ms
TTFB:           1843ms   ← server processing time
Total:          1847ms
Download size:  312 bytes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PERFORMANCE ISSUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  HIGH  N+1 Queries detected
    20 SELECT queries on 'orders' table (1 per user)
    Fix: Add .Include(u => u.Orders) in UserRepository.cs:34

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ROOT CAUSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
InvalidCastException in UserService.UpdateAsync() at Services/UserService.cs:89

The method attempts to cast the incoming `id` parameter (string "123abc") to `int`,
but the value contains non-numeric characters. The route accepts any string as `{id}`
but the service expects a valid integer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EVIDENCE (Server Logs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[14:32:05 INF] Request starting HTTP/1.1 POST http://localhost:5000/api/users/123abc
[14:32:05 INF] Executing action method UsersController.UpdateUser (id=123abc)
[14:32:05 ERR] An unhandled exception occurred
  System.InvalidCastException: Specified cast is not valid.
     at SampleApi.Services.UserService.UpdateAsync(String id) in UserService.cs:line 89
     at SampleApi.Controllers.UsersController.UpdateUser(String id) in UsersController.cs:line 72

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SUGGESTED FIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: Services/UserService.cs, line 89

Current:
  int userId = (int)id;   // ← throws InvalidCastException

Fix option 1 — parse with validation:
  if (!int.TryParse(id, out int userId))
      throw new ArgumentException($"Invalid user ID: {id}");

Fix option 2 — change route constraint to enforce int at routing level:
  // In Program.cs or UsersController:
  app.MapPut("/api/users/{id:int}", ...)
  // This returns 404 for non-integer IDs before reaching the handler
```

---

## Scenario Examples

### 401 Unauthorized

```
❌ [2]  Middleware: AuthenticationMiddleware
        JWT token validation failed
        Evidence: warn: Bearer was not authenticated. Failure: IDX10223: Lifetime validation failed. The token is expired.

ROOT CAUSE: JWT token expired. Token issued at 2024-01-14, expired after 1 hour.
FIX: Request a new token. Check token TTL configuration in appsettings.json → JwtSettings:ExpirationMinutes
```

### 404 Not Found

```
❌ [1]  Router — No route matched
        Request: GET /api/user/123  (missing 's')
        Available routes: GET /api/users/{id}, POST /api/users, ...

ROOT CAUSE: URL typo. Endpoint is /api/users/{id} (plural), not /api/user/{id}.
FIX: Correct the URL in the curl command.
```

### 400 Bad Request / Validation Error

```
✅ [1]  Router matched
❌ [2]  Middleware: ValidationMiddleware / ModelBinding
        Request body failed validation
        Evidence: warn: Model validation failed: The 'email' field is required.

ROOT CAUSE: Request body missing required field 'email'.
FIX: Add "email": "user@example.com" to the request body.
```

### Logic Bug — Wrong Response (200 but incorrect data)

```
✅ [1-5]  All checkpoints reached
HTTP: 200 OK

Expected: {"active": true}
Actual:   {"active": false}

Analysis: UserService.GetUser() at line 45 returns cached data.
          Cache TTL is 5 minutes. User was activated 2 minutes ago.
FIX: Invalidate cache on user update, or reduce cache TTL for user status.
```

### Timeout

```
✅ [1-4]  Router, Auth, Handler, Service reached
⏳ [5]   Data layer — no response after 30s
          Evidence: No log output after "Executing GetAllUsers query"

ROOT CAUSE: Database query timed out. Possible causes:
  - Full table scan on users table (no WHERE clause index)
  - Database server under heavy load
  - Deadlock

FIX: Check slow query log. Add index on queried column. Consider query timeout config.
```

---

## Severity Levels for Issues

| Severity | Color | Criteria |
|----------|-------|----------|
| `critical` | Red | Request fails (5xx), timeout, exception |
| `high` | Orange | N+1 queries, bottleneck > 1000ms |
| `medium` | Yellow | Slow query 100-500ms, missing pagination |
| `low` | Blue | Minor inefficiency, cosmetic |
| `info` | Gray | Informational, no action needed |
