# CLAUDE.md — AIAgentSkills

## Release checklist (run for every new or updated skill)

Before committing a skill release, always do ALL of the following:

1. **Package** — `Compress-Archive -Path "skills/<skill-name>" -DestinationPath "<skill-name>.skill" -Force`
2. **Deploy** — `cp -r skills/<skill-name> .claude/skills/<skill-name>`
3. **README — Skills section** — add or update the skill entry under `## Skills` (name, version, when-to-use, highlights)
4. **README — Release Notes** — prepend a new dated entry under `## Release Notes` with a bullet-point changelog
5. **README — Project Structure** — add the new skill's directory tree under both `.claude/skills/` and `skills/`
6. **Commit message** — follow the pattern: `feat(<skill-name>): v<X.Y.Z> — <one-line summary>`
7. **Push to main**

> This file exists so Claude always runs the full checklist without being asked. If any step is missing, complete it before pushing.

## Project conventions

- Skills live in `skills/<name>/` (source of truth) and are mirrored to `.claude/skills/<name>/` (deployed)
- `.skill` files are ZIP archives of `skills/<name>/` — created with `Compress-Archive` on Windows
- Every skill has: `SKILL.md` (frontmatter + phases), `references/*.md`, `assets/report-template.html`
- Report templates use embedded JSON + vanilla JS — no external dependencies
- Dark theme CSS variables must be consistent across all skill reports
- Session scratch dirs (`.agent-team/`, `.agent-forge/`) and generated reports (`*-report-*.html`) are gitignored
