# C# Grep Patterns

All patterns are ripgrep-compatible regex. Use with `Grep` tool, glob `**/*.cs`, always exclude `**/bin/**`, `**/obj/**`, `**/Migrations/**`, `**/*.g.cs`, `**/*.Designer.cs`.

---

## Definition Patterns

Replace `{Name}` with the actual target name before running.

### Class definitions
```
class\s+{Name}\b
abstract\s+class\s+{Name}\b
sealed\s+class\s+{Name}\b
partial\s+class\s+{Name}\b
```

### Interface definitions
```
interface\s+{Name}\b
```

### Record types (C# 9+)
```
record\s+{Name}\b
record\s+struct\s+{Name}\b
```

### Method definitions (any visibility)
```
(public|private|protected|internal)(\s+static)?(\s+async)?\s+[\w<>\[\]?,\s]+\s+{Name}\s*[<(]
```

### Constructor
```
public\s+{ClassName}\s*\(
```

### Property with body
```
(public|private|protected|internal)\s+[\w<>\[\]?]+\s+{Name}\s*\{
```

### Route / action attributes (controllers)
```
\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|Route)\b
```

---

## Callee Patterns

Apply to a method body string (in-memory, not Grep). Use as regex against each line.

### Private field call (DI-injected dependency)
```
_(\w+)\.([\w]+)\s*\(
```
Groups: (1) field_name, (2) method_name

### Awaited call on field
```
await\s+_(\w+)\.([\w]+)\s*\(
```

### Awaited call on any expression
```
await\s+(\w+)\.([\w]+)\s*\(
```

### Static or class-level call
```
\b([A-Z]\w+)\.([\w]+)\s*\(
```

### Object instantiation
```
new\s+([A-Z]\w+)\s*[<(]
```

### EF Core / LINQ async operations
```
\.(ToListAsync|FirstOrDefaultAsync|SingleOrDefaultAsync|FindAsync|AnyAsync|CountAsync|SaveChangesAsync|AddAsync|AddRangeAsync|UpdateAsync|RemoveAsync|ExecuteDeleteAsync|ExecuteUpdateAsync)\s*\(
```

### HttpClient calls
```
\.(GetAsync|PostAsync|PutAsync|DeleteAsync|PatchAsync|SendAsync|GetStringAsync|GetFromJsonAsync|PostAsJsonAsync)\s*\(
```

### MediatR
```
\.(Send|Publish|PublishAsync)\s*\(
```

### This-qualified calls
```
this\.([\w]+)\s*\(
```

---

## Caller Patterns

Replace `{Name}` with the target class or method name.

### Direct instantiation
```
new\s+{ClassName}\s*[(<]
```

### Method call on any receiver
```
\.\s*{MethodName}\s*\(
```

### Awaited method call
```
await\s+\w+\.\s*{MethodName}\s*\(
```

### Interface type usage (variable declaration, parameter)
```
I{ClassName}\s+\w+
```

### Generic type argument (DI registration, factory, typed client)
```
<\s*I?{ClassName}\s*[,>]
```

### Reflection
```
typeof\s*\(\s*{ClassName}\s*\)
```

### Constructor injection parameter (incoming side)
```
(I{ClassName}|{ClassName})\s+\w+\s*[,)]
```

---

## DI Registration Patterns

Run against `Program.cs`, `Startup.cs`, and `**/*Extensions.cs` files.

### Standard registrations
```
services\.(AddScoped|AddTransient|AddSingleton)\s*<\s*I?(\w+)\s*,?\s*(\w+)?\s*>
```
Groups: (1) lifetime, (2) interface_or_class, (3) implementation (may be empty)

### Generic non-typed registrations
```
services\.(AddScoped|AddTransient|AddSingleton)\s*\(\s*typeof\s*\((\w+)\)
```

### EF Core DbContext
```
\.(AddDbContext|AddDbContextPool)\s*<\s*(\w+)\s*>
```

### Typed HttpClient
```
\.AddHttpClient\s*<\s*(\w+)\s*>
```

### MediatR (blanket registration — no individual type)
```
\.AddMediatR\b
```

### builder.Services form (ASP.NET Core 6+)
```
builder\.Services\.(AddScoped|AddTransient|AddSingleton)\s*<
```

---

## IO Patterns

Maps receiver type names to `io_category`. Check `receiver_type` (string contains):

| Pattern (substring match) | io_category |
|---|---|
| `DbContext`, `DbSet`, `IRepository`, `SqlConnection`, `IDbConnection`, `NpgsqlConnection` | `database` |
| `HttpClient`, `IHttpClientFactory`, `RestClient`, `WebClient`, `IHttpService` | `http` |
| `ILogger`, `ILogger<` | `logging` (not external IO — flag separately as low-severity) |
| `IMessageBus`, `IBusControl`, `IEventBus`, `IServiceBus`, `IQueue`, `IPublisher`, `ISender` | `messaging` |
| `BlobClient`, `CloudStorageAccount`, `IStorageService`, `IBlobService`, `IFileService` | `storage` |
| `SmtpClient`, `IEmailSender`, `IMailService` | `email` |
| `IDistributedCache`, `IMemoryCache`, `StackExchange.Redis`, `IConnectionMultiplexer` | `cache` |

If `receiver_type` starts with `I` and no `.cs` file for it was found via Glob: mark as `external-sdk` (third-party dependency).

---

## Layer Classification

Apply rules in order — first match wins.

| Condition | layer |
|---|---|
| File path contains `/Controllers/` OR class name ends `Controller` OR has `[ApiController]` | `controller` |
| File path contains `/Handlers/` OR class name ends `Handler` (MediatR) | `handler` |
| File path contains `/Services/` OR class name ends `Service` | `service` |
| File path contains `/Repositories/` OR class name ends `Repository` OR base class is `DbContext` | `repository` |
| File path contains `/Domain/`, `/Entities/`, `/Aggregates/`, `/ValueObjects/` | `domain` |
| File path contains `/Middleware/` OR class name ends `Middleware` | `middleware` |
| File path contains `/Validators/` OR class name ends `Validator` | `validator` |
| File path contains `/Queries/` OR `/Commands/` (CQRS pattern) | `cqrs-handler` |
| Class name ends `Factory` | `factory` |
| File path contains `/Jobs/` OR class name ends `Job` OR `BackgroundService` in base | `background-job` |
| None of the above | `utility` |
