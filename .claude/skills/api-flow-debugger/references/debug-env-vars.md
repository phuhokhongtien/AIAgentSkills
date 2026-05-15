# Debug Environment Variables & Start Commands

Reference for starting dev servers with maximum logging enabled — without modifying source code.

---

## Node.js

### Express
```bash
DEBUG=express:* node app.js
# Or with Morgan HTTP logging:
DEBUG=express:* NODE_ENV=development node app.js
```
What it shows: route matching, middleware calls, response dispatch.

### Fastify
```bash
LOG_LEVEL=trace node server.js
# Or in code-less mode using env:
FASTIFY_LOG_LEVEL=trace node server.js
```
What it shows: request lifecycle hooks, plugin loading, route resolution.

### Koa
```bash
DEBUG=koa:* node app.js
```

### Hapi
```bash
NODE_DEBUG=http node server.js
# Hapi has built-in debug config — check for options.debug in server init
```

### NestJS
```bash
LOG_LEVEL=verbose node dist/main.js
# Or with ts-node:
LOG_LEVEL=verbose npx ts-node src/main.ts
```
What it shows: dependency injection, route registration, guard/interceptor lifecycle.

### General Node.js
```bash
NODE_DEBUG=http,net,stream node app.js    # Low-level HTTP/network
NODE_ENV=development node app.js          # Enables dev middleware in many frameworks
```

---

## Python

### FastAPI / Uvicorn
```bash
LOG_LEVEL=debug uvicorn main:app --reload
# Or with explicit host/port:
LOG_LEVEL=debug uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
What it shows: request/response lifecycle, exception details, middleware timing.

### Django
```bash
DEBUG=True python manage.py runserver
# For SQL query logging, set in settings: LOGGING with 'django.db.backends' at DEBUG level
# Can pass via env without code change if settings reads os.environ:
DJANGO_DEBUG=True LOG_LEVEL=DEBUG python manage.py runserver
```

### Flask
```bash
FLASK_DEBUG=1 FLASK_ENV=development flask run
# Or:
FLASK_DEBUG=1 python app.py
```
What it shows: full traceback in response, auto-reload, interactive debugger.

### aiohttp
```bash
AIOHTTP_NO_EXTENSIONS=1 python -m aiohttp.web app:create_app --verbose
```

### Generic Python logging
```bash
PYTHONVERBOSE=1 python app.py   # Very verbose interpreter output
LOGLEVEL=DEBUG python app.py    # If app reads LOGLEVEL env
```

---

## Go

### Gin
```bash
GIN_MODE=debug go run .
# Or:
GIN_MODE=debug go run main.go
```
What it shows: route table on startup, request path + handler name per call.

### Fiber
```bash
go run .   # Fiber prints routes in debug mode by default when app.Config.EnablePrintRoutes=true
```
Check `app.go` for `EnablePrintRoutes` config option.

### Echo
```bash
# Echo uses a logger middleware — enable DEBUG level via env if app reads it:
LOG_LEVEL=debug go run .
```

### Chi
```bash
# Chi logs via standard log package — enable verbose with:
LOG_LEVEL=debug go run .
```

### General Go
```bash
GODEBUG=http2debug=2 go run .       # HTTP/2 debug
GODEBUG=netdns=go go run .          # DNS debug
```

---

## C# / .NET (ASP.NET Core)

### Minimal API & Web API — Full Debug Mode
```bash
ASPNETCORE_ENVIRONMENT=Development dotnet run
```
This activates:
- `appsettings.Development.json` overrides
- Developer exception page (full stack trace in HTML response)
- Detailed error messages

### Maximum Log Verbosity (without changing appsettings.json)
```bash
ASPNETCORE_ENVIRONMENT=Development \
ASPNETCORE_LOGGING__LOGLEVEL__DEFAULT=Debug \
ASPNETCORE_LOGGING__LOGLEVEL__MICROSOFT=Debug \
ASPNETCORE_LOGGING__LOGLEVEL__MICROSOFT_ASPNETCORE=Trace \
dotnet run
```

### EF Core SQL Query Logging
```bash
ASPNETCORE_ENVIRONMENT=Development \
ASPNETCORE_LOGGING__LOGLEVEL__MICROSOFT_ENTITYFRAMEWORKCORE_DATABASE_COMMAND=Information \
dotnet run
```
What it shows: every SQL query, parameters, execution time.

### Hot Reload (watch mode)
```bash
ASPNETCORE_ENVIRONMENT=Development dotnet watch run
```

### Port override (if launchSettings conflict)
```bash
ASPNETCORE_URLS="http://localhost:5000" dotnet run
```

### dotnet-trace — Performance tracing without code changes
```bash
# Install once:
dotnet tool install --global dotnet-trace

# Collect trace for running process:
dotnet-trace collect --process-id <PID> \
  --providers "Microsoft-Extensions-Logging:5:5,Microsoft-AspNetCore-Hosting:5:5"

# View trace:
dotnet-trace report trace.nettrace
```

### dotnet-counters — Live metrics
```bash
dotnet tool install --global dotnet-counters
dotnet-counters monitor --process-id <PID> \
  --counters System.Runtime,Microsoft.AspNetCore.Hosting
```
What it shows: requests/sec, active requests, GC pressure, thread pool.

---

## Java / Kotlin

### Spring Boot
```bash
LOGGING_LEVEL_ROOT=DEBUG ./mvnw spring-boot:run
# Or:
java -jar app.jar --debug --logging.level.root=DEBUG
# SQL queries:
java -jar app.jar --logging.level.org.hibernate.SQL=DEBUG \
  --logging.level.org.hibernate.type.descriptor.sql=TRACE
```

### Gradle
```bash
LOGGING_LEVEL_ROOT=DEBUG ./gradlew bootRun --args='--debug'
```

---

## PHP / Laravel
```bash
APP_DEBUG=true APP_ENV=local php artisan serve
# Or set in .env:
APP_DEBUG=true
php artisan serve
```
What it shows: exception details, Whoops error page, query log if enabled.

Enable query log in tinker (no code change):
```bash
php artisan tinker
DB::enableQueryLog(); # then make the request and check DB::getQueryLog()
```

---

## Ruby on Rails
```bash
RAILS_LOG_LEVEL=debug rails server
# Or:
LOG_LEVEL=debug bundle exec rails server
```
What it shows: SQL queries, params (filtered), render times, response codes.

---

## ORM SQL Logging

Skill always enables ORM-level SQL logging in Phase 3 when starting the server. Append these env vars to the start command in addition to the framework-level debug flags above.

### EF Core (.NET)

```bash
ASPNETCORE_LOGGING__LOGLEVEL__MICROSOFT_ENTITYFRAMEWORKCORE_DATABASE_COMMAND=Information dotnet run
```

Emits every SQL command, parameters, and execution time. Compose with the ASP.NET Core debug vars above for full coverage.

### SQLAlchemy (Python — FastAPI / Flask)

```bash
SQLALCHEMY_ECHO=true uvicorn main:app
```

Most app templates read `SQLALCHEMY_ECHO` and pass to `create_engine(echo=...)`. If the app does NOT read this env var (custom config loader), fall back to `PYTHONASYNCIODEBUG=1` for async info or attach a debugger.

### TypeORM (Node.js)

```bash
TYPEORM_LOGGING=all TYPEORM_LOGGER=advanced-console node dist/main.js
```

Works when the app uses `new DataSource(...)` with config from environment. Pre-NestJS-9 setups may ignore these.

### Prisma (Node.js)

```bash
DEBUG=prisma:query node dist/main.js
```

Emits each query with bind parameters and duration.

### Hibernate (Java / Spring Boot)

```bash
java -jar app.jar \
  --logging.level.org.hibernate.SQL=DEBUG \
  --logging.level.org.hibernate.type.descriptor.sql=TRACE
```

`SQL=DEBUG` logs the statement; `descriptor.sql=TRACE` adds bind parameter values.

### Mongoose (MongoDB, Node.js)

No env-var-only switch — see Limitations below.

### Rails ActiveRecord (Ruby)

```bash
RAILS_LOG_LEVEL=debug rails server
```

Already verbose at DEBUG — no extra var needed. SQL appears as `User Load (0.5ms) SELECT ...`.

---

### Limitations — Stacks Requiring Source-Code Changes

Some ORMs cannot enable SQL logging via env vars alone. The skill respects "no source code modification" and documents the limitation rather than silently editing project files.

| ORM / Stack | Why env-var-only fails | Workaround (no code change) |
|---|---|---|
| GORM (Go) | Logging is configured per-DB-connection via `db.Debug()` or `Logger.LogMode(logger.Info)` in code | (a) Use `dlv debug` and set breakpoints on query methods; (b) Enable DB-side logging — Postgres: `ALTER SYSTEM SET log_statement = 'all'; SELECT pg_reload_conf();`; MySQL: `SET GLOBAL general_log = 'ON'; SET GLOBAL general_log_file = '/tmp/mysql.log';` |
| Django ORM | Requires a `LOGGING` dict entry in `settings.py` configuring the `django.db.backends` logger at `DEBUG` | (a) Set `DJANGO_SETTINGS_MODULE` to a separate settings file with logging enabled (out of scope for this skill); (b) DB-side logging as above |
| Sequelize (Node.js, no env-driven config) | The `logging` option must be a function passed to `new Sequelize(...)`. Most templates hard-code `logging: false` | (a) Check if app reads `SEQUELIZE_LOGGING` (project-specific convention); (b) DB-side logging |
| Laravel (default) | `DB::enableQueryLog()` must be called in code or middleware. Most apps don't | (a) Use Laravel Telescope if installed (`php artisan telescope:install`); (b) DB-side logging |
| Mongoose | `mongoose.set('debug', true)` is a code call | (a) MongoDB profiler: `db.setProfilingLevel(2)` inside `mongosh`; (b) Attach `node --inspect` and break on `Model.prototype.exec` |
| Knex.js (no event listener) | Logging requires `knex.on('query', ...)` listener in code | DB-side logging |

When the skill detects one of these stacks, it should:
1. Print a one-line warning: `SQL logging cannot be enabled via env vars for <stack>. DB query trace will be empty unless DB-side logging is active.`
2. Suggest the appropriate workaround from the table.
3. Continue execution — the trace will still capture HTTP and checkpoint data, just without per-query analysis.

---

## Framework Version Detection

```bash
# Node.js
cat package.json | grep -E '"express"|"fastify"|"koa"|"nestjs"' | head -5

# Python
pip show fastapi django flask 2>/dev/null | grep -E "Name|Version"

# Go
cat go.mod | grep -E "gin|fiber|echo|chi"

# .NET
cat *.csproj | grep -E "PackageReference.*AspNetCore"
dotnet --version

# Java
cat pom.xml | grep -E "spring-boot" | head -3
```
