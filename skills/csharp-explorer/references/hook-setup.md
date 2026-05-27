# Hook Setup Reference

Canonical content for the PostToolUse hook installed by Phase I.

---

## hook.py — destination: `~/.claude/csharp-explorer/hook.py`

```python
"""
csharp-explorer PostToolUse hook.
Installed by: /csharp-explorer init
Fires after ANY Read or Grep (any file type).
When prior run data exists for the current project:
  - Notifies on the 1st read of a new count window
  - Re-notifies every NOTIFY_INTERVAL reads (default: 15)
  - No .cs file filter — fires whenever AI reads any file in the project

v0.1.3 changes vs v0.1.1:
  - Removed .cs file-type filter (was only firing for .cs reads)
  - Lock file now stores JSON read-count instead of empty file
  - Re-notification every NOTIFY_INTERVAL reads handles long context sessions
"""
import os, json, sys

NOTIFY_INTERVAL = 15

try:
    tool_input = json.loads(os.environ.get("TOOL_INPUT", "{}"))
except Exception:
    sys.exit(0)

tool_name = os.environ.get("TOOL_NAME", "")

# Only handle Read and Grep tool calls
if tool_name not in ("Read", "Grep"):
    sys.exit(0)

# Resolve project slug from cwd
raw = os.path.basename(os.getcwd())
project = raw.lower().replace(" ", "-").replace(".", "-")

# Check store for prior runs FIRST — no file-type filter
store_parent = os.path.join(os.path.expanduser("~"), ".claude", "csharp-explorer")
store = os.path.join(store_parent, project)
if not os.path.isdir(store):
    sys.exit(0)

runs = [f for f in os.listdir(store) if f.endswith(".json")]
if not runs:
    sys.exit(0)

# Read-count based notification (lock file persists, stores JSON state)
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

# Save updated count
try:
    with open(lock, "w") as f:
        json.dump(state, f)
except Exception:
    pass

# Notify on first read OR every NOTIFY_INTERVAL reads
should_notify = (count == 1) or (count % NOTIFY_INTERVAL == 0)
if not should_notify:
    sys.exit(0)

# Extract recent target names from filenames (YYYYMMDD-HHmmss-<name>.json)
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

Phase I injects this into the `hooks.PostToolUse` array:

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

**Idempotency check**: before injecting, search existing `hooks.PostToolUse` entries for any command containing `csharp-explorer/hook.py`. Skip if already present.

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
            "command": "python ~/.claude/csharp-explorer/hook.py"
          }
        ]
      }
    ]
  }
  // ... rest of existing settings ...
}
```

If `hooks` key does not exist: create it. If `hooks.PostToolUse` does not exist: create it as an empty array, then append the entry.

---

## Removing the hook (uninstall)

To remove:
1. Delete `~/.claude/csharp-explorer/hook.py`
2. Remove the matching entry from `hooks.PostToolUse` in `~/.claude/settings.json`
3. (Optional) delete `~/.claude/csharp-explorer/.notified-*` lock files
