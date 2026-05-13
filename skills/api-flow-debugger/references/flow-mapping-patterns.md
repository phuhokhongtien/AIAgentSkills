# Flow Mapping Patterns

Grep patterns and file conventions for finding routes, middleware, handlers, and services per tech stack. Use these during Phase 2 to build the Checkpoint Map.

---

## Node.js / Express

### Find route registrations
```bash
# Direct route definitions
grep -rn "app\.\(get\|post\|put\|delete\|patch\)\|router\.\(get\|post\|put\|delete\|patch\)" \
  --include="*.js" --include="*.ts" .

# Router files
find . -name "*.routes.js" -o -name "*.routes.ts" -o -name "router.js" -o -name "routes.js" 2>/dev/null

# Express Router usage
grep -rn "express\.Router\(\)" --include="*.js" --include="*.ts" .
```

### Find middleware registration order
```bash
# app.use() calls (order matters in Express)
grep -n "app\.use(" app.js server.js index.js src/app.js 2>/dev/null

# Middleware files
find . -name "*.middleware.js" -o -name "*.middleware.ts" \
       -o -name "middleware.js" -o -name "middlewares/" 2>/dev/null
```

### Find controller/handler
```bash
# Controller files
find . -name "*.controller.js" -o -name "*.controller.ts" 2>/dev/null

# Handler functions referenced in routes
grep -rn "require\|import" --include="*.js" --include="*.ts" . | grep -i "controller\|handler"
```

### Find service layer
```bash
find . -name "*.service.js" -o -name "*.service.ts" -o -name "*Service.js" -o -name "*Service.ts" 2>/dev/null
```

---

## Node.js / NestJS

### Find controllers and routes
```bash
# Controllers
find . -name "*.controller.ts" 2>/dev/null

# Route decorators inside controllers
grep -rn "@Get\|@Post\|@Put\|@Delete\|@Patch\|@Controller" --include="*.ts" .
```

### Find guards (auth middleware equivalent)
```bash
grep -rn "@UseGuards\|implements CanActivate" --include="*.ts" .
find . -name "*.guard.ts" 2>/dev/null
```

### Find interceptors and pipes
```bash
find . -name "*.interceptor.ts" -o -name "*.pipe.ts" 2>/dev/null
grep -rn "@UseInterceptors\|@UsePipes" --include="*.ts" .
```

---

## Python / FastAPI

### Find route definitions
```bash
grep -rn "@app\.\(get\|post\|put\|delete\|patch\)\|@router\.\(get\|post\|put\|delete\|patch\)" \
  --include="*.py" .

# Router files
find . -name "router.py" -o -name "routers.py" -o -name "*_router.py" 2>/dev/null
find . -path "*/routers/*.py" 2>/dev/null
```

### Find middleware (FastAPI / Starlette)
```bash
grep -rn "@app\.middleware\|app\.add_middleware\|BaseHTTPMiddleware" --include="*.py" .
find . -name "middleware.py" -o -name "*_middleware.py" 2>/dev/null
```

### Find dependencies (FastAPI's Depends)
```bash
grep -rn "Depends(" --include="*.py" .
find . -name "dependencies.py" -o -name "deps.py" 2>/dev/null
```

### Find service layer
```bash
find . -name "*service*.py" -o -name "*_service.py" 2>/dev/null
grep -rn "class.*Service" --include="*.py" .
```

---

## Python / Django

### Find URL patterns
```bash
find . -name "urls.py" 2>/dev/null
grep -rn "path(\|re_path(\|url(" --include="*.py" .
```

### Find views
```bash
find . -name "views.py" -o -name "viewsets.py" 2>/dev/null
grep -rn "class.*View\|def.*view" --include="*.py" .
```

### Find middleware
```bash
grep -rn "MIDDLEWARE" settings.py settings/*.py 2>/dev/null
find . -name "middleware.py" 2>/dev/null
```

---

## Go

### Find route registrations

#### Gin
```bash
grep -rn "\.GET\|\.POST\|\.PUT\|\.DELETE\|\.PATCH\|\.Group\|\.Use" \
  --include="*.go" .
```

#### Fiber
```bash
grep -rn "app\.Get\|app\.Post\|app\.Put\|app\.Delete\|app\.Use\|\.Group(" \
  --include="*.go" .
```

#### Echo
```bash
grep -rn "e\.GET\|e\.POST\|e\.PUT\|e\.DELETE\|e\.Group\|e\.Use" \
  --include="*.go" .
```

#### Chi
```bash
grep -rn "r\.Get\|r\.Post\|r\.Put\|r\.Delete\|r\.Route\|r\.Use\|r\.With" \
  --include="*.go" .
```

### Find middleware
```bash
grep -rn "func.*Middleware\|func.*Handler" --include="*.go" .
find . -name "middleware.go" -o -name "*_middleware.go" 2>/dev/null
```

### Find handlers / controllers
```bash
find . -name "*_handler.go" -o -name "handler.go" -o -name "*_controller.go" 2>/dev/null
grep -rn "func.*Handler\b" --include="*.go" .
```

---

## C# / ASP.NET Core

### Find route registrations — Minimal API
```bash
grep -rn "app\.Map\(Get\|Post\|Put\|Delete\|app\.MapGet\|app\.MapPost\|app\.MapPut\|app\.MapDelete\|app\.MapControllers" \
  --include="*.cs" .

# MapGroup usage
grep -rn "MapGroup\|RouteGroupBuilder" --include="*.cs" .
```

### Find route registrations — Controller-based
```bash
# Find controller files
find . -name "*Controller.cs" 2>/dev/null

# Route attributes on controllers and actions
grep -rn "\[Route\|\[HttpGet\|\[HttpPost\|\[HttpPut\|\[HttpDelete\|\[HttpPatch" \
  --include="*.cs" .

# Conventional routing in Program.cs / Startup.cs
grep -rn "MapControllerRoute\|MapDefaultControllerRoute\|UseEndpoints" --include="*.cs" .
```

### Find middleware registration order
```bash
# Middleware pipeline in Program.cs (order is critical in ASP.NET Core)
grep -n "app\.Use\|app\.Run\|app\.Map" Program.cs Startup.cs 2>/dev/null

# Custom middleware files
find . -name "*Middleware.cs" 2>/dev/null

# Middleware classes
grep -rn "class.*Middleware\|IMiddleware\|InvokeAsync" --include="*.cs" .
```

### Find dependency injection registrations
```bash
grep -rn "services\.Add\|builder\.Services\.Add\|AddScoped\|AddTransient\|AddSingleton" \
  --include="*.cs" Program.cs Startup.cs 2>/dev/null
```

### Find service layer
```bash
find . -name "*Service.cs" -o -name "I*Service.cs" 2>/dev/null
grep -rn "class.*Service\b\|interface I.*Service" --include="*.cs" .
```

### Find repository layer
```bash
find . -name "*Repository.cs" -o -name "I*Repository.cs" 2>/dev/null
grep -rn "DbContext\|DbSet\|FromSqlRaw\|ExecuteSqlRaw" --include="*.cs" .
```

### Find filters (action/exception filters)
```bash
find . -name "*Filter.cs" 2>/dev/null
grep -rn "IActionFilter\|IExceptionFilter\|IResultFilter\|\[ServiceFilter\|\[TypeFilter" \
  --include="*.cs" .
```

### .NET — Read launchSettings.json for port
```bash
cat Properties/launchSettings.json 2>/dev/null
# Look for: "applicationUrl": "https://localhost:7xxx;http://localhost:5xxx"
```

---

## Java / Spring Boot

### Find route registrations
```bash
grep -rn "@GetMapping\|@PostMapping\|@PutMapping\|@DeleteMapping\|@RequestMapping" \
  --include="*.java" --include="*.kt" .

find . -name "*Controller.java" -o -name "*Controller.kt" 2>/dev/null
```

### Find filters and interceptors
```bash
grep -rn "OncePerRequestFilter\|HandlerInterceptor\|Filter\b" --include="*.java" --include="*.kt" .
find . -name "*Filter.java" -o -name "*Interceptor.java" 2>/dev/null
```

### Find service layer
```bash
find . -name "*Service.java" -o -name "*Service.kt" 2>/dev/null
grep -rn "@Service\b" --include="*.java" --include="*.kt" .
```

### Find repository layer
```bash
grep -rn "@Repository\|JpaRepository\|CrudRepository" --include="*.java" --include="*.kt" .
find . -name "*Repository.java" -o -name "*Repository.kt" 2>/dev/null
```

---

## Tracing the Route Match

Once route files are found, match the curl URL against registered patterns:

| URL | Pattern to look for |
|-----|-------------------|
| `/api/users/123` | `/api/users/:id`, `/api/users/{id}`, `"/api/users/<int:id>"` |
| `/api/users?active=true` | `/api/users` (query params are not in route pattern) |
| `/api/v2/orders` | Check both `/api/v2/orders` and group prefix `/api/v2` + sub-route `/orders` |

For C# .NET specifically — controller route resolution:
1. Check `[Route("api/[controller]")]` on class → controller name (without "Controller" suffix) = segment
2. Check `[HttpGet("{id}")]` on action → combine with class route
3. Example: `UsersController` + `[Route("api/[controller]")]` + `[HttpGet("{id}")]` → `GET /api/users/{id}`
