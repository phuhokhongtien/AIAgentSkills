# Cache Strategy

Describes how prior knowledge (stored run data) is loaded, validated, and used as hints to avoid redundant Grep scans.

---

## Core Rule

**Source code is always the truth source.**

Stored data reflects the codebase as it was at the time of the last run. After any code edit, rename, or refactor, stored locations may be stale. The cache is only a speedup hint — it must be verified before use.

---

## Store Layout

```
~/.claude/csharp-explorer/
└── <project_slug>/
    ├── 20260524-100000-orderservice-createorder.json
    ├── 20260524-143022-ordercontroller-post.json
    └── 20260526-093000-paymentservice.json
```

- One JSON file per analysis run
- Filename format: `YYYYMMDD-HHmmss-<sanitized_target_name>.json`
- `sanitized_target_name`: lowercase, dots and spaces replaced with `-`
- Never overwrite existing files — always append a new timestamped file
- `project_slug`: current working directory base name, lowercased, spaces/dots → `-`

---

## Loading Prior Knowledge (Phase 0)

1. Check if store dir exists and has `.json` files
2. Read each file, parse JSON, extract `report.target` and `report.caller_tree.nodes`
3. Build `prior_knowledge.nodes_by_id`:
   - Key: `"<namespace>::<class_name>::<method_name>"`
   - Value: `{ file, definition_line, namespace, kind, layer }` from most recent run for that key
4. Set `prior_knowledge.last_run_timestamp` = timestamp of the most recently written file

The `nodes_by_id` map covers the primary target AND all nodes found in `caller_tree.nodes` from past runs — so re-running for a caller seen before will also benefit from the cache.

---

## Cache Validation (Phase 2)

Before using any cached `{ file, definition_line }`:

```
cached_line = prior_knowledge.nodes_by_id[target_key].definition_line
cached_file = prior_knowledge.nodes_by_id[target_key].file

verification = Read(cached_file, offset: cached_line - 1, limit: 3)
```

**Cache HIT** if any of the 3 lines contains:
- A definition keyword (`class`, `interface`, `record`, `void`, `Task`, `async`, or a visibility modifier like `public`, `private`, `protected`, `internal`)
- AND the `target_name` (case-sensitive)

**Cache MISS** if:
- The file does not exist (deleted or renamed)
- The 3 lines don't contain the target name at a definition position
- The Read call errors

On cache miss: print `Cache miss for <target_name> — re-scanning source` and proceed with full Grep scan.

---

## Staleness Signals

| Signal | Action |
|---|---|
| File no longer exists | Cache miss; flag node as `stale: true` in merged report |
| Definition line content doesn't match | Cache miss; discard cached line for this target |
| Definition moved (method refactored to different file) | Grep will find new location; old JSON entry persists as historical record |
| Class renamed | Grep will not find old name; node becomes stale in merged graph |

Staleness is **detected at read time** (Phase 0/2 and Phase S), not at write time. The JSON files are never modified after creation.

---

## Append-Only Design

Each run always writes a NEW file — never modifies existing ones. This means:

- History is preserved: you can see how a class evolved over multiple analysis sessions
- Multiple stale entries may accumulate for the same target across files — Phase S deduplicates by key, keeping the most recent metadata
- Phase C (clear store) is the only way to remove old files

---

## Store Growth

The store has no automatic pruning. Files accumulate over time. This is intentional:
- Phase S uses the full history for the timeline visualization
- Stale nodes are visually marked but not deleted

If the store becomes unwieldy, the user can run `/csharp-explorer clear` (Phase C) to delete all JSON files for the current project.

Typical file size per run: 5–50 KB (small method with shallow BFS) to 200 KB (large class with depth=3 and many nodes). A store with 30 runs is usually under 3 MB — no concern.

---

## Windows Path Handling

On Windows, `~` resolves to `%USERPROFILE%` (e.g. `C:\Users\Admin`).

Store path: `C:\Users\Admin\.claude\csharp-explorer\<project_slug>\`

When writing the store dir path in messages and report output, use forward slashes for readability: `~/.claude/csharp-explorer/<slug>/`.

When executing filesystem operations (Write tool), use the fully resolved Windows path with backslashes or forward slashes (both work in Windows PowerShell).
