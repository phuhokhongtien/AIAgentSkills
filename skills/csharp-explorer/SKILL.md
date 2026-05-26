---
name: csharp-explorer
description: >
  ALWAYS invoke this skill when working in a C# project (.cs files present)
  and the user asks ANY question about a class, method, interface, or how
  code works — even vague questions like "explain this", "what does X do",
  "how does this work", "where is X defined", "what calls this", "who uses X".
  Also invoke when the AI is actively reading .cs files and the user asks
  about code structure, dependencies, or architecture.
  Explicit trigger phrases: "explain this class", "who calls this method",
  "trace the call graph", "find all callers of X", "what does Y depend on",
  "show the call tree for Z", "what implements IOrderService",
  "how is OrderService registered", "understand this async flow",
  "explore this C# codebase", "hiểu class này", "trace caller",
  "show diagram", "csharp-explorer show", "visualize call graph",
  "what calls X", "who uses X", "where is X", "explain X", "how does X work",
  "what is X", "show me X", "analyze X", "understand X".
  This skill loads prior knowledge from a persistent store — invoke it even
  for repeat questions to benefit from cached call graph data.
version: 0.1.1
tools: Read, Glob, Grep, Write, AskUserQuestion
---

## Invocation Modes

Detect from user's message — first match wins:

| Mode | Trigger phrases | Phases |
|---|---|---|
| **init** | "csharp-explorer init", "setup hook", "install hook", "setup csharp-explorer" | Phase I only |
| **show** | "show diagram", "csharp-explorer show", "visualize", "show call graph" | Phase S only |
| **clear** | "csharp-explorer clear", "clear store", "reset csharp-explorer" | Phase C only |
| **analyze** (default) | any class/method question, reading .cs files | Phases 0–7 |

---

## Phase 0 — Context Hydration *(always runs first)*

Resolve `project_slug`:
- Take the current working directory's base name
- Lowercase, replace spaces and dots with `-`
- Example: `MyApp.Api` → `myapp-api`

Store dir = `~/.claude/csharp-explorer/<project_slug>/`  
On Windows: `%USERPROFILE%\.claude\csharp-explorer\<project_slug>\`

Steps:
1. Check if the store dir exists and contains any `.json` files
2. If **files found**:
   - Read each JSON file (sorted by filename = by timestamp)
   - Build `prior_knowledge.nodes_by_id`: keyed by `"<namespace>::<class_name>::<method_name>"`, value = most recent snapshot
   - Record `prior_knowledge.runs_count` and `prior_knowledge.last_run_timestamp`
   - Print: `Found <N> previous run(s) for <project_slug>. Loading prior knowledge as hints...`
3. If **no files**: set `prior_knowledge = null`, proceed silently

**Rule**: prior knowledge is hints only. Source code is always truth. Never skip verification.

Record:
```
prior_knowledge = {
  nodes_by_id: { "<ns>::<class>::<method>": { file, definition_line, namespace, ... } },
  runs_count,
  last_run_timestamp
} | null
```

---

## Phase 1 — Intake

Parse the user's message to extract:

| Field | Default | Notes |
|---|---|---|
| `target_name` | (required) | `OrderService` or `OrderService.CreateOrder` |
| `target_kind` | `unknown` | `class` \| `method` \| `interface` \| `unknown` |
| `direction` | `both` | `callers` \| `callees` \| `both` |
| `depth` | `2` | Integer 1–4; depth >3 only if user explicitly requests |
| `namespace_filter` | `null` | Partial namespace string to scope disambiguation |
| `file_hint` | `null` | Optional partial/full path from user |

If `target_name` contains a `.` (e.g. `OrderService.CreateOrder`): split into `class_part` + `method_part`; set `target_kind = method`.

**Proceed immediately** if `target_name` is unambiguous. Use `AskUserQuestion` only when the user's message genuinely cannot yield a target name (e.g. "explore the codebase" with no specific target).

Record:
```
intake = { target_name, target_kind, direction, depth, namespace_filter, file_hint }
```

---

## Phase 2 — Locate Target

Goal: find the exact file and line number of the target's definition.

### Step 1 — Cache lookup (fast path)

If `prior_knowledge` is not null, search `nodes_by_id` for a key matching `target_name` (case-insensitive partial match on class or method name).

For each candidate found:
- Read `offset: cached_line - 1, limit: 3` from the cached file
- Check if any of those 3 lines contains both a definition keyword (`class`, `interface`, `void`, `Task`, `async`, or similar) AND the target name
- **Cache hit**: use `cached_file` and `cached_definition_line` directly; set `cache_hit = true`; skip Step 2
- **Cache miss**: print `Cache miss for <target_name> — re-scanning source`; fall through to Step 2

### Step 2 — Grep scan (fallback)

Glob `**/*.cs` excluding: `**/bin/**`, `**/obj/**`, `**/Migrations/**`, `**/*.g.cs`, `**/*.Designer.cs`, `**/*.AssemblyInfo.cs`, `**/*GlobalUsings.cs`

If `file_hint` is set: also Glob `**/*{file_hint}*.cs` and check those files first.

Run definition patterns from `references/csharp-patterns.md` § Definition Patterns — use the pattern matching `target_kind`. Stop collecting after 10 matches.

### Step 3 — Disambiguation

If 1 match: use it directly.

If 0 matches: try the `unknown` patterns (all three: class, interface, method). If still 0: report "Target not found" and stop.

If ≥2 matches:
1. Filter by `namespace_filter` if set: Grep `^namespace.*<filter>` in each candidate file (Read `offset:0, limit:15`)
2. If still ≥2: extract namespace from each file (Read `offset:0, limit:15`, find `^namespace`)
3. Use `AskUserQuestion` showing each candidate as: `ClassName — <file> (namespace: <ns>)`

Record:
```
target = {
  name, kind, file, definition_line, namespace,
  cache_hit   // true | false
}
```

---

## Phase 3 — Extract Definition

Use the chunking algorithm from `references/chunking-guide.md`.

### Step 1 — Read opening region

Read `offset: definition_line - 1, limit: 60`.

For a **method**: scan for the closing `}` that brings brace depth to 0. If found within 60 lines → body is complete; record `line_end`.

For a **class** or **interface**: read the header (up to first `{`) and first 30 lines of body as a preview. Then do brace-depth counting in 100-line windows until depth returns to 0 or 500-line cap reached.

### Step 2 — Extract metadata

From the definition header line:
- `modifiers[]`: scan for `public`, `private`, `protected`, `internal`, `static`, `async`, `abstract`, `virtual`, `override`, `sealed`, `partial`
- `return_type`: text between last modifier and method name (for methods)
- `parameters[]`: parse `(type name, type name)` pairs from the signature line
- `attributes[]`: scan lines above the definition for `[Attribute]` patterns

### Step 3 — DI dependencies (class only)

Grep within the same file for `public\s+{class_name}\s*\(` to find the constructor.
Read constructor body (offset/limit).
Extract all `I[A-Z]\w+` parameter types → these are the injected dependencies.

Record:
```
definition = {
  header_lines,       // signature line(s) including attributes
  body_preview,       // first 60 lines of body (always populated)
  body_full,          // full body if ≤ 500 lines; null if truncated
  line_start, line_end,
  truncated,          // true if body exceeded 500 lines
  modifiers[], return_type, parameters[], attributes[],
  di_dependencies[]   // [{ interface_type, param_name }]
}
```

---

## Phase 4 — Map Callees

Only runs when `intake.direction` is `callees` or `both`.

### Step 1 — Extract call sites from body

Use patterns from `references/csharp-patterns.md` § Callee Patterns on `definition.body_full` (or `body_preview` if truncated).

For each unique call site extract: `receiver`, `method_name`, `raw_line`.

### Step 2 — Resolve receiver types

For each `receiver`:
1. Check `definition.di_dependencies` — if receiver name matches a constructor parameter, its type is that parameter's declared type
2. Grep within the same file for `private\s+(readonly\s+)?(\w[\w<>]+)\s+{receiver}\b` to find field declarations
3. If receiver starts with capital letter and no `_` prefix → likely static class; mark `is_static = true`

### Step 3 — Classify callees

For each resolved callee:
- `is_external_io`: check receiver_type against IO patterns in `references/csharp-patterns.md` § IO Patterns
- `is_async`: call preceded by `await` in source line
- `is_internal`: Grep `(class|interface)\s+{receiver_type}\b` → found in codebase → true

Record:
```
callees[] = {
  receiver, receiver_type, method_name,
  file,              // resolved or null
  definition_line,   // resolved or null
  is_external_io, io_category,
  is_async, is_internal, is_static,
  raw_line
}
```

---

## Phase 5 — Map Callers (BFS)

Only runs when `intake.direction` is `callers` or `both`.

### BFS Algorithm

```
queue = [{ node_id: target_id, name: target.name, kind: target.kind, depth: 0 }]
visited = Set()     // "file:line_number" strings
nodes = []
edges = []
test_callers = []
MAX_NODES = 50
```

For each item dequeued:
1. If `item.depth >= intake.depth` → skip expansion, record node only
2. Run caller patterns from `references/csharp-patterns.md` § Caller Patterns
3. Filter each match:
   - Skip if `visited.has("file:line")` (cycle / dedup)
   - Skip if `match.file == target.file && abs(match.line - target.definition_line) <= 2` (definition itself)
   - Skip if line is a comment (starts with `//` after trim, or within `/* */` block)
   - If file path matches test pattern (`/Test`, `/Tests`, `/Spec`, `Test.cs`, `Tests.cs`, `Spec.cs`): add to `test_callers[]`, do NOT enqueue
4. For each surviving match: Read `offset: line - 8, limit: 25` to extract enclosing class + method
5. Add node + edge; enqueue with `depth + 1`
6. If `nodes.length >= MAX_NODES`: set `truncated = true`, stop

See `references/traversal-strategy.md` for full BFS pseudo-code and cycle detection rules.

Record:
```
caller_tree = {
  nodes[], edges[],
  depth_reached, truncated,
  test_callers[],
  total_caller_count,
  test_caller_count
}
```

---

## Phase 6 — Synthesize

Pure reasoning — no further tool calls unless DI registration lookup is needed.

### Layer classification

Apply rules from `references/csharp-patterns.md` § Layer Classification to `target.file` path and `target.name`.

### Async analysis

From `definition.modifiers` and `callees[]`:
- Flag `async_void`: method is `async void` (not in event handlers — fire-and-forget anti-pattern)
- Flag `async_no_await`: method is `async` but no `await` found in body_preview
- Flag `task_not_awaited`: method returns `Task` but callers call it without `await`

### DI lifetime analysis

Grep `Program.cs`, `Startup.cs`, and `**/*ServiceCollectionExtensions.cs` for:
```
Add(Scoped|Transient|Singleton)<.*{target.name}
```
Record each match's lifetime. Then for each `di_dependency`:
```
Add(Scoped|Transient|Singleton)<.*{dependency.interface_type}
```
Flag if target is `Singleton` but depends on a `Scoped` service → critical lifetime mismatch.

### Boundary classification

| Condition | boundary_type |
|---|---|
| Layer is `controller` or `middleware`, no callers from controller layer | `entry-point` |
| Layer is `domain` and has no external IO callees | `domain-core` |
| Layer is `repository` or has external IO callees | `adapter` |
| Used by many callers (>5), has no external IO | `shared-utility` |
| Has callees but no callers in codebase | `leaf` |
| Otherwise | `unknown` |

### Interface / partial

- Grep `:\s*{target.name}\b` and `implements.*{target.name}` for implementations
- Grep `partial\s+class\s+{target.name}\b` for partial parts

Compose:
```
synthesis = {
  target_summary,    // 2–3 sentence description of what this does
  layer,
  boundary_type,
  async_issues[],    // [{issue_type, description, offending_line, recommendation}]
  di_issues[],       // [{type, description}]
  interface_implementations[],
  partial_parts[],
  concerns[],        // merged list of all issues with severity
  key_insight        // 1-sentence headline
}
```

---

## Phase 7 — Save & Chat Summary

### Save run data

1. Resolve store dir: `~/.claude/csharp-explorer/<project_slug>/` (create if missing)
2. Build `report` object per schema in `references/report-format.md`
3. Write to `<store_dir>/YYYYMMDD-HHmmss-<sanitized_target_name>.json`
   - `sanitized_target_name`: lowercase, replace `.` and spaces with `-`

### Chat summary

Print to chat (not a file):

```
C# Explorer — <target.name> (<target.kind>)
File:      <target.file>  line <target.definition_line>  [cache: hit/miss]
Layer:     <layer>  │  Boundary: <boundary_type>
Namespace: <target.namespace>

Callers:   <N> direct  │  <M> total (depth <depth_reached>)  │  <K> in tests
Callees:   <J> methods  │  <L> external I/O  │  <async_count> async

DI: <di_summary one-liner or "No DI detected">

⚠  <concern 1>
⚠  <concern 2>        (omit section if no concerns)
✅ No concerns detected  (only if concerns is empty)

Data saved → <path>
Run `/csharp-explorer show` to visualize all accumulated data.
```

---

## Phase S — Show Diagram *(triggered by "show", "diagram", "csharp-explorer show")*

### Step 1 — Locate store

Check `~/.claude/csharp-explorer/` for project dirs. If multiple exist, use `AskUserQuestion` to pick one (or all). If the current project's slug dir exists, use it by default.

### Step 2 — Load and validate all JSON files

For each `.json` file (sorted by filename = timestamp):
- Parse the report object
- For each node that has `file` + `definition_line`: Read `offset: line-1, limit: 2` to check if still valid
- Mark stale nodes (file missing or definition no longer at that line) with `stale: true`

### Step 3 — Merge call graphs

Merge algorithm (see `references/traversal-strategy.md` § Merge Algorithm):
- **Node dedup key**: `"<namespace>::<class_name>::<method_name>"`
- Keep most-recent metadata per node; add `first_seen`, `last_seen`, `run_count` fields
- **Edge dedup**: `"<from_id>→<to_id>"`; add `observation_count` (how many runs saw this edge)
- **Concerns**: dedup by `"<target_name>::<issue_type>"`; keep most recent
- Mark stale nodes visually in the merged graph

Build: `merged = { runs[], nodes[], edges[], concerns[], di_map[], timeline_stats }`

### Step 4 — Generate HTML report

1. Read `assets/report-template.html`
2. Replace all `{{PLACEHOLDER}}` tokens (HTML-escape all strings)
3. Inject: `const reportData = <JSON.stringify(merged)>;`
4. Write to current dir: `csharp-explorer-diagram-YYYYMMDD-HHmmss.html`
5. Auto-open:
   - Windows: `cmd.exe /c start "" "<path>"`
   - macOS: `open "<path>"`
   - Linux: `xdg-open "<path>"`
6. Print: `Diagram saved → <path>`

---

## Phase I — Init *(triggered by "init", "setup hook", "csharp-explorer init")*

One-time setup for a new machine. Installs the PostToolUse hook so the skill
auto-notifies when `.cs` files are read in any future session.

### Step 1 — Write `hook.py`

Write the canonical hook script (from `references/hook-setup.md`) to:
- **macOS/Linux**: `~/.claude/csharp-explorer/hook.py`
- **Windows**: `%USERPROFILE%\.claude\csharp-explorer\hook.py`

Use the `Write` tool. Create the `~/.claude/csharp-explorer/` directory first if it doesn't exist (the Write tool creates parent dirs automatically).

The exact content to write is the `hook.py` block in `references/hook-setup.md`.

### Step 2 — Update `~/.claude/settings.json`

1. Read `~/.claude/settings.json`
2. Parse JSON
3. **Idempotency check**: scan `hooks.PostToolUse[]` for any entry whose `command` contains `csharp-explorer/hook.py` — if found, print "Hook already installed." and skip to Step 4
4. If `hooks` key missing → add `"hooks": {}`
5. If `hooks.PostToolUse` missing → add `"PostToolUse": []`
6. Append this entry to `hooks.PostToolUse`:
```json
{
  "matcher": "Read|Grep",
  "hooks": [
    {
      "type": "command",
      "command": "python ~/.claude/csharp-explorer/hook.py"
    }
  ]
}
```
7. Write the updated JSON back to `~/.claude/settings.json`

### Step 3 — Verify

- Confirm `~/.claude/csharp-explorer/hook.py` exists (Read the first 3 lines)
- Confirm `~/.claude/settings.json` contains `csharp-explorer/hook.py` (Grep)

### Step 4 — Print summary

```
csharp-explorer — Init complete

Hook script:  ~/.claude/csharp-explorer/hook.py
Settings:     ~/.claude/settings.json  [hook added]

How it works:
  • Fires after any Read or Grep on a .cs file
  • Checks ~/.claude/csharp-explorer/<project>/ for prior runs
  • Prints a one-time reminder per session when data exists

Next steps:
  • Open any C# project and ask about a class to start building your store
  • /csharp-explorer <ClassName>   — analyze a class or method
  • /csharp-explorer show          — visualize all accumulated data
```

---

## Phase C — Clear Store *(triggered by "clear", "csharp-explorer clear")*

1. Resolve store dir for current project slug
2. List all `.json` files found
3. Use `AskUserQuestion` to confirm: "Delete <N> run files for <project_slug>? This cannot be undone."
4. If confirmed: delete all `.json` files in the store dir
5. Print: `Store cleared for <project_slug>. <N> files deleted.`
