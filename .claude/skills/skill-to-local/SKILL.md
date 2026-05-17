---
name: skill-to-local
description: Use this skill when the user wants to "sync skill to global", "install skill globally", "copy skill to local", "deploy skill globally", "skill to local", or "cài skill vào global". Copies one or all skills from this project's skills/ directory into the global ~/.claude/skills/ so they are available in any Claude Code session on this machine.
version: 0.1.0
tools: Read, Glob, Bash, TodoWrite
---

# Skill to Local (Global Install)

Copy one or all skills from `skills/` in this project into the global `~/.claude/skills/` directory, making them available in any Claude Code session regardless of working directory.

---

## Phase 1 — Intake

1. **Determine scope:**
   - **Single skill** — user named it (e.g. "sync agent-forge-team globally"). Validate `skills/<name>/SKILL.md` exists.
   - **All skills** — user says "sync all skills" or "install all globally". Enumerate all directories under `skills/` that contain a `SKILL.md` file.
   - **Ambiguous** — use `AskUserQuestion`, listing the available skills found under `skills/`.

2. **Resolve global path** (Windows):
   ```bash
   echo "$env:USERPROFILE\.claude\skills"
   ```
   Global skills directory: `$env:USERPROFILE\.claude\skills\` (i.e. `~/.claude/skills/`).

---

## Phase 2 — Sync

For each target skill:

```bash
# Remove stale copy first to ensure clean sync, then copy
rm -rf "$HOME/.claude/skills/<name>"
cp -r "skills/<name>" "$HOME/.claude/skills/<name>"
```

After each copy, verify:
```bash
ls "$HOME/.claude/skills/<name>/SKILL.md"
```

If the destination parent directory does not exist, create it first:
```bash
mkdir -p "$HOME/.claude/skills"
```

---

## Phase 3 — Summary

Print a summary for each synced skill:

```
Synced <N> skill(s) to global:

  agent-forge-team   skills/agent-forge-team  →  ~/.claude/skills/agent-forge-team
  skill-release      skills/skill-release     →  ~/.claude/skills/skill-release

Global skills directory: C:\Users\<user>\.claude\skills\
Skills are now available in any Claude Code session on this machine.
```
