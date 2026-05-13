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
