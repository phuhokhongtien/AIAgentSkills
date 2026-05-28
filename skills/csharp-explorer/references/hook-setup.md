# Hook Setup Reference

Canonical content for the PostToolUse hook installed by Phase I.

---

## hook.py — destination: `~/.claude/csharp-explorer/hook.py`

```python
"""
csharp-explorer PostToolUse hook.
Installed by: /csharp-explorer init
v0.1.6

Two-mode behavior:
  MODE A — Auto-analyze (unanalyzed .cs file read):
    When AI reads a .cs file that has NOT been analyzed yet for this project,
    prints an INSTRUCTION telling Claude to run /csharp-explorer <ClassName>
    immediately. This passively builds the store as Claude explores the codebase.
    Skips: generated files, boilerplate, test files.

  MODE B — Read-count re-notification (everything else):
    For already-analyzed .cs files and all other file types:
    notifies on read #1, re-notifies every NOTIFY_INTERVAL reads.
    Handles long context sessions with periodic reminders.

v0.1.6 changes vs v0.1.5:
  - STRONGER INSTRUCTION: Mode A output now tells Claude exactly which
    tool to call (Skill) and with what parameters (skill, args). The old
    "INSTRUCTION: Run /csharp-explorer ClassName" was too passive — Claude
    agents mid-task would see it and keep going without acting. The new
    output uses ⚠️ MANDATORY INTERRUPT language and gives explicit Skill
    tool call syntax so agentic Claude treats it as a hard stop.

v0.1.5 changes vs v0.1.4:
  - CRITICAL FIX: Read hook input from stdin JSON (not env vars).
  - Use cwd from stdin JSON for accurate project slug (not os.getcwd()).
  - Bootstrap fix: Mode A now fires even with an empty store directory.
"""
import os, json, sys

# Force UTF-8 stdout so emoji/unicode in hook output works on Windows (cp1252 default)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

NOTIFY_INTERVAL = 15

# Files to skip for auto-analyze (generated, boilerplate, entry points)
AUTO_ANALYZE_SKIP = [
    "globalusings", "assemblyinfo", ".g", ".designer",
    "program", "startup", "migration",
]
# Test file name patterns — skip auto-analyze, don't pollute store with test classes
TEST_PATTERNS = ["tests", "test", "spec", "mock", "fake", "stub"]

try:
    data = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Only handle Read and Grep tool calls
if tool_name not in ("Read", "Grep"):
    sys.exit(0)

# Resolve project slug from cwd in hook data (more reliable than os.getcwd())
raw_cwd = data.get("cwd", os.getcwd())
raw = os.path.basename(raw_cwd)
project = raw.lower().replace(" ", "-").replace(".", "-")

# store_parent must exist — created by Phase I init, signals hook is active
store_parent = os.path.join(os.path.expanduser("~"), ".claude", "csharp-explorer")
if not os.path.isdir(store_parent):
    sys.exit(0)

# store is project-specific — created by Phase I init for this project
store = os.path.join(store_parent, project)
if not os.path.isdir(store):
    sys.exit(0)

# runs may be empty on a fresh init (Mode A still fires; Mode B requires runs)
runs = [f for f in os.listdir(store) if f.endswith(".json")]

# ── MODE A: Auto-analyze — unanalyzed .cs file ───────────────────────────────
if tool_name == "Read":
    file_path = tool_input.get("file_path", "")
    if file_path.endswith(".cs"):
        class_name = os.path.splitext(os.path.basename(file_path))[0]
        name_lower = class_name.lower()

        # Skip generated / boilerplate / entry-point / migration files
        # Check both class name AND full path (catches Migrations/ directory)
        file_lower = file_path.lower().replace("\\", "/")
        if any(s in name_lower or s in file_lower for s in AUTO_ANALYZE_SKIP):
            sys.exit(0)

        # Skip test files
        if any(p in name_lower for p in TEST_PATTERNS):
            sys.exit(0)

        # Exact match: stored filename part must equal class name
        # Format: YYYYMMDD-HHmmss-<sanitized_name>.json
        # "orderservice" matches OrderService.cs; "orderservice-createorder" also matches
        class_key = class_name.lower()
        analyzed = False
        for f in runs:
            parts = f.replace(".json", "").split("-", 2)
            if len(parts) != 3:
                continue
            stored = parts[2].lower()
            if stored == class_key or stored.startswith(class_key + "-"):
                analyzed = True
                break
        if not analyzed:
            print(
                f"\n⚠️  [csharp-explorer] MANDATORY INTERRUPT — stop your current task.\n"
                f"\n"
                f"  {class_name}.cs was just read and has NOT been analyzed for \"{project}\".\n"
                f"\n"
                f"  Call the Skill tool RIGHT NOW with:\n"
                f"    skill = \"csharp-explorer\"\n"
                f"    args  = \"{class_name}\"\n"
                f"\n"
                f"  After the skill completes, resume your previous task immediately.\n"
                f"  Skipping this leaves {class_name} unindexed for this session.\n"
            )
            sys.exit(0)
        # Already analyzed → fall through to Mode B (read-count notification)

# ── MODE B: Read-count re-notification ───────────────────────────────────────
# Requires prior runs — no point notifying if there is no accumulated data yet
if not runs:
    sys.exit(0)

lock = os.path.join(store_parent, ".notified-" + project)
state = {"read_count": 0}
if os.path.exists(lock):
    try:
        with open(lock) as f:
            state = json.load(f)
    except Exception:
        state = {"read_count": 0}

state["read_count"] = state.get("read_count", 0) + 1
count = state["read_count"]

try:
    with open(lock, "w") as f:
        json.dump(state, f)
except Exception:
    pass

should_notify = (count == 1) or (count % NOTIFY_INTERVAL == 0)
if not should_notify:
    sys.exit(0)

recent = []
for f in sorted(runs)[-3:]:
    parts = f.replace(".json", "").split("-", 2)
    if len(parts) == 3:
        recent.append(parts[2])

hint = ", ".join(recent) if recent else "prior targets"
read_note = f" [read #{count}]" if count > 1 else ""
print(
    f"\n[csharp-explorer] {len(runs)} prior run(s) for \"{project}\" "
    f"({hint}){read_note}.\n"
    f"  Analyze:   /csharp-explorer <ClassName>\n"
    f"  Diagram:   /csharp-explorer show\n"
    f"  Setup:     /csharp-explorer init\n"
)
```

---

## Hook entry for `~/.claude/settings.json`

Phase I injects this into the `hooks.PostToolUse` array.

**IMPORTANT — use the absolute path with forward slashes**, not `~`.

Two reasons:
1. Tilde is not expanded for native executables by PowerShell/cmd.exe on Windows
2. Backslashes are stripped by bash as escape characters (`\U` → `U`, `\A` → `A`, etc.)

During Phase I, compute the path with forward slashes:

```python
import os
p = os.path.join(os.path.expanduser("~"), ".claude", "csharp-explorer", "hook.py")
hook_path = p.replace("\\", "/")
# → C:/Users/Admin/.claude/csharp-explorer/hook.py  (Windows)
# → /home/user/.claude/csharp-explorer/hook.py      (macOS/Linux)
```

Then write that path into the command field:

```json
{
  "matcher": "Read|Grep",
  "hooks": [
    {
      "type": "command",
      "command": "python C:/Users/Admin/.claude/csharp-explorer/hook.py"
    }
  ]
}
```

**Idempotency check**: before injecting, search existing `hooks.PostToolUse` entries for any command containing `csharp-explorer`. Skip if already present.

---

## Settings.json structure after init

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/Admin/.claude/csharp-explorer/hook.py"
          }
        ]
      }
    ]
  }
}
```

If `hooks` key does not exist: create it. If `hooks.PostToolUse` does not exist: create it as an empty array, then append the entry.

---

## Removing the hook (uninstall)

To remove:
1. Delete `~/.claude/csharp-explorer/hook.py`
2. Remove the matching entry from `hooks.PostToolUse` in `~/.claude/settings.json`
3. (Optional) delete `~/.claude/csharp-explorer/.notified-*` lock files
