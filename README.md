# AIAgentSkills

Tập hợp các custom skills cho Claude Code — giúp AI agent thực hiện các tác vụ phức tạp như một developer thực sự.

---

## Skills

### `api-flow-debugger`

Debug một API endpoint bằng cách trace toàn bộ request flow — từ curl đến response — **mà không cần sửa bất kỳ dòng code nào**.

**Khi nào dùng:**
- Endpoint trả về lỗi (4xx, 5xx) và không biết lỗi ở đâu
- Response trả về data sai, không như kỳ vọng
- API chạy chậm, nghi có N+1 hoặc bottleneck
- Muốn hiểu luồng xử lý request đi qua những middleware/service nào

**Hỗ trợ:** Node.js (Express, Fastify, NestJS), Python (FastAPI, Django, Flask), Go (Gin, Fiber), **C# .NET** (ASP.NET Core), Java/Spring Boot, PHP/Laravel, Ruby/Rails

---

## Cài đặt

Skills được đặt trong `.claude/skills/` — Claude Code tự discover khi khởi động session trong thư mục này.

```bash
cd D:\PROJECTS\AIAgentSkills
claude   # mở Claude Code trong thư mục này
```

Không cần cài đặt thêm gì.

---

## Cách dùng `api-flow-debugger`

### Bước 1 — Invoke skill

Trong session Claude Code, gõ:

```
/api-flow-debugger
```

Hoặc mô tả tự nhiên, Claude sẽ tự nhận:
> *"debug endpoint này cho mình"*
> *"tại sao curl này bị 500?"*
> *"trace request flow của API này"*

### Bước 2 — Cung cấp curl command

Paste curl command của endpoint cần debug:

```bash
# Ví dụ 1 — endpoint trả 500
curl http://localhost:5000/api/users/abc

# Ví dụ 2 — POST với body
curl -X POST http://localhost:3000/api/orders \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"productId": 42, "quantity": 2}'

# Ví dụ 3 — chỉ có URL cũng được, skill sẽ tự bổ sung headers
curl http://localhost:8080/api/v1/users?active=true
```

> **Không cần curl hoàn chỉnh.** Skill sẽ tự detect những gì còn thiếu (Content-Type, Accept header, port) và hỏi bổ sung nếu cần.

### Bước 3 — Skill tự chạy

Skill sẽ tự động:

1. **Parse & validate** curl — tự thêm headers còn thiếu, hỏi nếu có placeholder `<TOKEN>`
2. **Detect tech stack** — đọc `package.json` / `*.csproj` / `go.mod` / ... để nhận diện framework
3. **Map code flow** — tìm route → middleware → handler → service → DB theo thứ tự
4. **Start dev server** với debug mode (không sửa code, chỉ dùng env vars)
5. **Execute curl** — chạy với `-v` để capture full HTTP detail + timing
6. **Phân tích** — correlate logs với checkpoint map, detect N+1 / bottleneck
7. **Tạo HTML report** và **tự mở trên browser**

### Bước 4 — Đọc HTML Report

Report được lưu tại working directory với tên `debug-report-YYYYMMDD-HHmmss.html` và tự mở. Bao gồm:

| Section | Nội dung |
|---------|----------|
| **Request** | curl đã enhance, method, URL, headers, body |
| **Checkpoint Trace** | Timeline ✅/❌ per step với file:line |
| **HTTP Response** | Status code, response headers, body (formatted) |
| **Timing** | Connect / Server processing / Download bar chart |
| **Performance** | N+1 queries, bottleneck, slow queries nếu có |
| **Root Cause** | Mô tả chính xác lỗi ở đâu |
| **Suggested Fix** | Code fix cụ thể |

---

## Test nhanh với sample project

Có sẵn `.NET` sample project với 2 intentional bugs:

```bash
# Terminal 1 — start server
cd D:\PROJECTS\AIAgentSkills\samples\dotnet-web-api-sample
ASPNETCORE_ENVIRONMENT=Development dotnet run
# Server chạy tại http://localhost:5000
```

```bash
# Test case 1: InvalidCastException (500)
curl http://localhost:5000/api/users/abc

# Test case 2: N+1 queries (200 nhưng slow)
curl http://localhost:5000/api/users

# Test case 3: Works fine (baseline)
curl http://localhost:5000/api/users/1
```

Paste bất kỳ curl nào trên vào skill để xem full debug report.

---

## Cấu trúc project

```
AIAgentSkills/
├── .claude/
│   ├── settings.json
│   └── skills/
│       └── api-flow-debugger/
│           ├── SKILL.md                    ← workflow chính (7 phases)
│           ├── assets/
│           │   └── report-template.html    ← HTML report template
│           └── references/
│               ├── debug-env-vars.md       ← debug start commands per framework
│               ├── flow-mapping-patterns.md ← grep patterns tìm route/handler
│               ├── performance-analysis.md  ← N+1, bottleneck detection
│               └── trace-report-format.md  ← text fallback + scenario examples
├── skills/                                 ← source (mirror của .claude/skills)
│   └── api-flow-debugger/
├── samples/
│   └── dotnet-web-api-sample/              ← .NET test project có sẵn bugs
└── README.md
```

---

## Thêm skill mới

1. Tạo thư mục: `.claude/skills/<tên-skill>/`
2. Tạo `SKILL.md` với frontmatter:
   ```yaml
   ---
   name: tên-skill
   description: This skill should be used when... (third-person, specific triggers)
   version: 0.1.0
   tools: Read, Glob, Grep, Bash
   ---
   ```
3. Restart session Claude Code để load skill mới
