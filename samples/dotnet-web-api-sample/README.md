# SampleApi — Debug Test Project

ASP.NET Core Web API với intentional bugs để test skill `api-flow-debugger`.

## Run

```bash
ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_LOGGING__LOGLEVEL__DEFAULT=Debug dotnet run
# Server starts at http://localhost:5000
```

## Intentional Bugs

### Bug 1: InvalidCastException (500 error)
Endpoint: `GET /api/users/{id}` và `PUT /api/users/{id}`

**Breaks** khi id không phải số nguyên:
```bash
# Triggers InvalidCastException in UserService.cs:44
curl http://localhost:5000/api/users/abc
curl -X PUT http://localhost:5000/api/users/abc \
  -H "Content-Type: application/json" \
  -d '{"name":"Test"}'
```

**Works** với id hợp lệ:
```bash
curl http://localhost:5000/api/users/1
curl -X PUT http://localhost:5000/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Updated"}'
```

Root cause: `UserService.cs:44` — `(int)Convert.ChangeType(id, typeof(int))` throws for "abc".

Fix: Replace with `int.TryParse(id, out int userId)`.

---

### Bug 2: N+1 Queries
Endpoint: `GET /api/users`

```bash
curl http://localhost:5000/api/users
```

Returns 200 OK but performs 1 query per user to load orders (3 users = 4 total queries instead of 1).
Root cause: `UserService.cs:27-32` — `foreach` loop with individual order lookup per user.
Fix: Load all orders in one query and group by UserId.

---

## Checkpoint Map (for skill verification)

```
[1] Router      → UsersController.cs:12   (@Route("api/[controller]"))
[2] Middleware  → Program.cs middleware pipeline (none custom in this sample)
[3] Handler     → UsersController.GetById()  :38
[4] Service     → UserService.GetByIdAsync() :37
[5] Data layer  → in-memory lookup + cast    :44  ← BUG HERE
```
