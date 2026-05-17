---
name: skill-release
description: Use this skill when the user wants to "release a skill", "package and publish a skill", "run the release checklist", "publish skill to main", or "package skill". Automates the full 7-step release workflow for any skill in this AIAgentSkills project — packaging, local deploy, README updates, commit, and push — so no step is ever forgotten.
version: 0.1.0
tools: Read, Write, Edit, Glob, Grep, Bash, TodoWrite
---

# Skill Release

Run the complete release checklist for a skill in this project. Covers every step from packaging through push — no manual steps required.

## Non-negotiable constraint

**Never skip or reorder steps.** The checklist exists because partial releases break consistency. If any step fails, stop and surface the error rather than continuing.

---

## Phase 1 — Intake

1. **Identify the skill name:**
   - If the user named it (e.g. "release agent-forge-team"), use that name.
   - If ambiguous, list available skills: `ls skills/` and ask via `AskUserQuestion`.
   - Validate: `skills/<name>/SKILL.md` must exist.

2. **Read version** from `skills/<name>/SKILL.md` frontmatter (`version:` field).

3. **Determine release type:**
   - **New** — no entry for `<name>` in `README.md` Skills section yet.
   - **Update** — entry already exists; update version + changelog.

4. **Ask for changelog bullets** if not provided by the user. These go into the README Release Notes entry and the commit message summary.

5. Initialize `TodoWrite` with all remaining phases as tasks.

---

## Phase 2 — Package

Create `<name>.skill` (a ZIP archive of `skills/<name>/`).

`Compress-Archive` rejects `.skill` extensions on Windows. Use Python:

```bash
python -c "
import zipfile, pathlib
src = pathlib.Path('skills/<name>')
out = pathlib.Path('<name>.skill')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in src.rglob('*'):
        if f.is_file():
            zf.write(f, f.relative_to(src.parent))
print('Packaged:', out, '—', sum(1 for _ in src.rglob('*') if _.is_file()), 'files')
"
```

Verify: `<name>.skill` exists in the repo root.

Mark Phase 2 done in TodoWrite.

---

## Phase 3 — Deploy to Local .claude/skills/

Copy the skill into this project's `.claude/skills/` so it is available in this session:

```bash
cp -r "skills/<name>" ".claude/skills/<name>"
```

Verify: `.claude/skills/<name>/SKILL.md` exists.

Mark Phase 3 done in TodoWrite.

---

## Phase 4 — Update README (3 sections)

Read `README.md` in full, then apply three edits:

### 4a — Skills section (`## Skills`)

**New skill:** Add a new `### \`<name>\` — v<X.Y.Z>` entry following the format of existing entries (tagline, **When to use:** bullets, **Highlights:** or **Key properties:** bullets). Insert before the `---` separator that follows the last skill entry.

**Update:** Find the existing `### \`<name>\`` heading, update the version in the heading, add changelog items.

### 4b — Release Notes section (`## Release Notes`)

Prepend a new entry at the top of the section (after the `## Release Notes` heading):

```markdown
### <YYYY-MM-DD> — `<name>` v<X.Y.Z> (<new release|update>)
- <changelog bullet 1>
- <changelog bullet 2>
```

Use today's date (available in the session as `currentDate`).

### 4c — Project Structure section (`## Project Structure`)

Add the new skill's directory tree in both the `.claude/skills/` subsection and the `skills/` subsection. Match the indentation and tree style of existing entries.

Mark Phase 4 done in TodoWrite.

---

## Phase 5 — Commit & Push

Stage all changed files and commit:

```bash
git add "skills/<name>" ".claude/skills/<name>" "<name>.skill" README.md
git commit -m "feat(<name>): v<X.Y.Z> — <one-line summary>"
git push origin master
```

If `CLAUDE.md` was also modified, include it in the staged files.

Verify push succeeded (no error output).

Mark Phase 5 done in TodoWrite.

---

## Phase 6 — Summary

Print a concise release summary:

```
Released: <name> v<X.Y.Z>
Package:  <name>.skill  (<N> files)
Deployed: .claude/skills/<name>/
Commit:   <short SHA> — feat(<name>): v<X.Y.Z> — <summary>
Pushed:   master
```

Mark Phase 6 done in TodoWrite.
