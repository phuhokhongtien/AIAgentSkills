# Hook Setup Reference

Canonical content for the PostToolUse hook installed by Phase I.

---

## hook.py — destination: `~/.claude/csharp-explorer/hook.py`

```python
"""
csharp-explorer PostToolUse hook.
Installed by: /csharp-explorer init
Fires after Read or Grep. When a .cs file is accessed and prior run data
exists for the current project, prints a one-time reminder per session.
"""
import os, json, sys

try:
    tool_input = json.loads(os.environ.get("TOOL_INPUT", "{}"))
except Exception:
    sys.exit(0)

tool_name = os.environ.get("TOOL_NAME", "")

# Detect .cs file access
is_cs = False
if tool_name == "Read":
    fp = tool_input.get("file_path", "")
    is_cs = fp.endswith(".cs")
elif tool_name == "Grep":
    glob = tool_input.get("glob", "")
    path = tool_input.get("path", "")
    is_cs = ".cs" in glob or path.endswith(".cs")

if not is_cs:
    sys.exit(0)

# Resolve project slug from cwd
raw = os.path.basename(os.getcwd())
project = raw.lower().replace(" ", "-").replace(".", "-")

# Check store for prior runs
store = os.path.join(os.path.expanduser("~"), ".claude", "csharp-explorer", project)
if not os.path.isdir(store):
    sys.exit(0)

runs = [f for f in os.listdir(store) if f.endswith(".json")]
if not runs:
    sys.exit(0)

# One-time notification per session (lock file per project)
lock = os.path.join(
    os.path.expanduser("~"), ".claude", "csharp-explorer", ".notified-" + project
)
if os.path.exists(lock):
    sys.exit(0)

try:
    open(lock, "w").close()
except Exception:
    pass

# Extract recent target names from filenames (YYYYMMDD-HHmmss-<name>.json)
recent = []
for f in sorted(runs)[-3:]:
    parts = f.replace(".json", "").split("-", 2)
    if len(parts) == 3:
        recent.append(parts[2])

hint = ", ".join(recent) if recent else "prior targets"
print(
    f"\n[csharp-explorer] {len(runs)} prior run(s) stored for \"{project}\" "
    f"({hint}).\n"
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
