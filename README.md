# AIAgentSkills

A collection of custom skills for Claude Code — enabling AI agents to perform complex developer tasks autonomously.

---

## Skills

### `api-flow-debugger`

Debug any API endpoint by tracing the full request flow — from curl to response — **without modifying a single line of source code**.

**When to use:**
- An endpoint returns an error (4xx, 5xx) and you don't know why
- The response returns unexpected or incorrect data
- The API is slow and you suspect N+1 queries or a bottleneck
- You want to understand exactly which middleware and services a request passes through

**Supported stacks:** Node.js (Express, Fastify, NestJS), Python (FastAPI, Django, Flask), Go (Gin, Fiber), **C# .NET** (ASP.NET Core), Java/Spring Boot, PHP/Laravel, Ruby/Rails

---

## Installation

Skills live in `.claude/skills/` — Claude Code auto-discovers them when you start a session in this directory.

```bash
cd /your/path/to/AIAgentSkills
claude
```

No additional setup required.

---

## Using `api-flow-debugger`

### Step 1 — Invoke the skill

In a Claude Code session, type:

```
/api-flow-debugger
```

Or just describe what you need in natural language — Claude will pick it up automatically:
> *"debug this endpoint for me"*
> *"why is this curl returning 500?"*
> *"trace the request flow for this API"*

### Step 2 — Provide a curl command

Paste the curl command for the endpoint you want to debug:

```bash
# Example 1 — endpoint returning 500
curl http://localhost:5000/api/users/abc

# Example 2 — POST with a request body
curl -X POST http://localhost:3000/api/orders \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"productId": 42, "quantity": 2}'

# Example 3 — a bare URL works too; the skill will fill in missing headers
curl http://localhost:8080/api/v1/users?active=true
```

> **The curl doesn't need to be complete.** The skill auto-detects missing parts (Content-Type, Accept header, port) and asks for clarification only when necessary (e.g. token placeholders like `<TOKEN>`).

### Step 3 — The skill runs automatically

The skill will:

1. **Parse & validate** the curl — add missing headers, prompt for any token placeholders
2. **Detect the tech stack** — reads `package.json`, `*.csproj`, `go.mod`, etc.
3. **Map the code flow** — locates route → middleware → handler → service → DB in order
4. **Start the dev server** in debug mode using environment variables only (no code changes)
5. **Execute the curl** with `-v` to capture full HTTP details and timing
6. **Analyze** — correlates server logs with the checkpoint map, detects N+1 and bottlenecks
7. **Generate an HTML report** and **open it automatically in your browser**

### Step 4 — Review the HTML Report

The report is saved as `debug-report-YYYYMMDD-HHmmss.html` in the working directory and opens automatically. It includes:

| Section | Contents |
|---------|----------|
| **Request** | Enhanced curl command, method, URL, headers, body |
| **Checkpoint Trace** | Visual ✅/❌ timeline per step with file:line |
| **HTTP Response** | Status code, response headers, formatted body |
| **Timing** | Bar chart: connect / server processing / download |
| **Performance** | N+1 queries, bottleneck, slow queries (if detected) |
| **Root Cause** | Exact description of what went wrong and where |
| **Suggested Fix** | Concrete, actionable code fix |

---

## Quick Test with the Sample Project

A `.NET` sample project is included with two intentional bugs for testing:

```bash
# Terminal 1 — start the server
cd samples/dotnet-web-api-sample
ASPNETCORE_ENVIRONMENT=Development dotnet run
# Server runs at http://localhost:5000
```

```bash
# Test case 1: InvalidCastException → triggers a 500 error
curl http://localhost:5000/api/users/abc

# Test case 2: N+1 queries → returns 200 but hits the DB once per user
curl http://localhost:5000/api/users

# Test case 3: Happy path — works correctly
curl http://localhost:5000/api/users/1
```

Paste any of the above curls into the skill to see a full debug report.

---

## Project Structure

```
AIAgentSkills/
├── .claude/
│   ├── settings.json
│   └── skills/
│       └── api-flow-debugger/
│           ├── SKILL.md                     ← main workflow (7 phases)
│           ├── assets/
│           │   └── report-template.html     ← self-contained HTML report template
│           └── references/
│               ├── debug-env-vars.md        ← debug start commands per framework
│               ├── flow-mapping-patterns.md ← grep patterns to find routes/handlers
│               ├── performance-analysis.md  ← N+1 and bottleneck detection guide
│               └── trace-report-format.md  ← text fallback + scenario examples
├── skills/                                  ← source mirror of .claude/skills/
│   └── api-flow-debugger/
├── samples/
│   └── dotnet-web-api-sample/               ← .NET test project with intentional bugs
├── api-flow-debugger.skill                  ← packaged distributable
└── README.md
```

---

## Adding a New Skill

1. Create the directory: `.claude/skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: skill-name
   description: This skill should be used when... (third-person, include specific trigger phrases)
   version: 0.1.0
   tools: Read, Glob, Grep, Bash
   ---
   ```
3. Restart your Claude Code session to load the new skill.
