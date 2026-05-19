# CLAUDE.md — AIAgentSkills

## Branch & PR workflow (required for every change)

**Never commit directly to `master`.** All work goes through a feature branch and a pull request.

### Branch naming
| Change type | Branch name |
|---|---|
| New or updated skill | `feat/<skill-name>` or `feat/<skill-name>-v<X.Y.Z>` |
| Bug fix | `fix/<short-description>` |
| Docs / README only | `docs/<short-description>` |
| Config / tooling | `chore/<short-description>` |

### Workflow (every session)
1. **Branch first** — before any edits: `git checkout -b feat/<skill-name>`
2. **Do the work** — follow the release checklist below
3. **Push the branch** — `git push -u origin feat/<skill-name>`
4. **Open a PR** — `gh pr create --title "feat(<skill>): v<X.Y.Z> — <summary>" --body "..."`
5. **Never force-push to master** — PRs only

> If you find yourself on `master` with uncommitted changes, stash them, branch, and pop: `git stash && git checkout -b feat/... && git stash pop`

---

## Release checklist (run for every new or updated skill)

Before committing a skill release, always do ALL of the following:

1. **Package** — use Python zipfile (Compress-Archive rejects `.skill` on Windows):
   ```bash
   python -c "
   import zipfile, pathlib
   src = pathlib.Path('skills/<skill-name>')
   out = pathlib.Path('<skill-name>.skill')
   with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
       for f in src.rglob('*'):
           if f.is_file():
               zf.write(f, f.relative_to(src.parent))
   print('Packaged:', out)
   "
   ```
2. **Deploy** — `cp -r skills/<skill-name>/. .claude/skills/<skill-name>/`
3. **README — Skills section** — add or update the skill entry under `## Skills` (name, version, when-to-use, highlights)
4. **README — Release Notes** — prepend a new dated entry under `## Release Notes` with a bullet-point changelog
5. **README — Project Structure** — add the new skill's directory tree under both `.claude/skills/` and `skills/`
6. **Commit message** — follow the pattern: `feat(<skill-name>): v<X.Y.Z> — <one-line summary>`
7. **Push branch + open PR** — never push directly to master

> This file exists so Claude always runs the full checklist without being asked. If any step is missing, complete it before opening the PR.

## Project conventions

- Skills live in `skills/<name>/` (source of truth) and are mirrored to `.claude/skills/<name>/` (deployed)
- `.skill` files are ZIP archives of `skills/<name>/` — created with Python `zipfile` (not `Compress-Archive`, which rejects `.skill` extensions)
- Every skill has: `SKILL.md` (frontmatter + phases), `references/*.md`, `assets/report-template.html`
- Report templates use embedded JSON + vanilla JS — no external dependencies
- Dark theme CSS variables must be consistent across all skill reports
- Session scratch dirs (`.agent-team/`, `.agent-forge/`) and generated reports (`*-report-*.html`) are gitignored
