# State Management

The on-disk session is the team's only shared memory. It must be complete enough that
execution can survive context limits and a re-read by the Leader.

## Session directory

Created in the current working directory:

```
.agent-forge/<slug>/
├── plan.md                     verbatim plan + task list with T-IDs + constraints + success criteria + tech stack
├── config.md                   execution mode, gate style, rollback policy, roles, models, verification commands
├── dependency-graph.md         task registry, wave assignments, file ownership map, impact briefings
├── sentinel-report.md          full Sentinel output (pre-execution risk report)
├── interfaces/
│   ├── api-contracts.md        REST/GraphQL endpoint shapes
│   ├── service-interfaces.md   TypeScript interfaces for all services
│   ├── db-schema.md            DDL / entity definitions / migration specs
│   └── component-contracts.md  component prop types, emits, slots (frontend only)
├── briefs/
│   └── <role>-brief.md         Implementation Brief per Implementer (written by Leader pre-wave)
├── roles/
│   └── <role>.md               role charter per agent
├── waves/
│   └── wave-N/
│       ├── <role>-output.md    raw Implementer return (one file per agent)
│       ├── reviewer-report.md  Wave Reviewer output
│       ├── verifier-report.md  Integration Verifier output
│       └── wave-summary.md     Leader roll-up (the rolling summary fed forward)
├── impacts/
│   ├── impact-registry.md      append-only global impact log (all waves)
│   └── wave-N-ripple.md        briefings extracted from wave N, injected into wave N+1 briefs
├── snapshots/
│   └── wave-N.md               stash ID or branch name (rollback reference)
├── decisions.md                append-only Leader ruling log
├── progress.md                 live status board (overwritten on every update)
├── DELIVERY.md                 final delivery summary (written in Phase 6)
└── DELIVERY-NARRATIVE.md       Archaeology Agent narrative (written in Phase 6)
```

`<slug>` = kebab-cased short plan name, e.g. `admin-dashboard`.

---

## File schemas

### `plan.md`

```markdown
# Plan: <name>

## Tech Stack
<framework, language, database, etc.>

## Tasks
T1. <description>
T2. <description>
T3. <description> [status: done | partial | blocked — filled in during execution]
...

## Hard Constraints
- <non-negotiable constraint>

## Success Criteria
1. <criterion>
...

## Verification Commands
- build: <command>
- test:  <command>
- lint:  <command>

## Assumptions
- <assumption> — source: Sentinel round / user answer <date>
```

### `config.md`

```yaml
slug: <slug>
execution_mode: parallel | sequential
gate_style: auto | manual
rollback_policy: git-stash | branch | none
max_waves: 10
verification_commands:
  build: <command>
  test:  <command>
  lint:  <command>
roles:
  - name: data-layer
    wave: 1
    model: haiku
    subagent_type: general-purpose
  - name: backend-services
    wave: 2
    model: haiku
    subagent_type: general-purpose
  - name: sentinel
    wave: phase-3
    model: sonnet
    subagent_type: explore
  - name: interface-definer
    wave: phase-4
    model: sonnet
    subagent_type: general-purpose
  - name: wave-reviewer
    wave: post-wave
    model: sonnet
    subagent_type: general-purpose
  - name: integration-verifier
    wave: post-wave
    model: haiku
    subagent_type: general-purpose
  - name: archaeology-agent
    wave: phase-6
    model: sonnet
    subagent_type: general-purpose
```

### `waves/wave-N/wave-summary.md` (the rolling summary — most important file)

```markdown
# Wave N Summary
Generated: <ISO-8601 timestamp>

## Tasks completed
- T<N>: done — <one-line description of what was produced>

## Tasks partial / blocked
- T<N>: partial — <reason> — <what was and wasn't done>
- T<N>: blocked — <reason> — <what is needed to unblock>

## Files changed
- <path>: <one-line description of change>

## Critical issues found
- [SEVERITY] <issue> — Resolution: <how Leader resolved it>
OR: none

## Escalations
- T<N>: escalated haiku → sonnet — Reason: <reasoning gap description>
OR: none

## Impact declarations (normalized)
- IMP-<NNN>: <file> — <change type> — <what callers must know>

## Ripple briefings issued to Wave N+1
- IMP-<NNN> → affects: T<IDs> — <summary of what those agents must do>
OR: none

## Wave Reviewer verdict
- PROCEED | CORRECT-AND-PROCEED (<corrections applied>) | HALT

## Integration results
- Build: PASS | FAIL (<command>, exit <code>)
- Tests: <N> passed, <M> failed, <K> skipped
- Lint:  PASS | FAIL | N/A

## Plan drift
- <deviation from original plan — what changed and why>
OR: none

## Gate decision
- PROCEED to Wave N+1 | ROLLBACK (<reason>) | PARTIAL-ROLLBACK (<tasks>)
- Rollback available: <stash ID or branch name>
```

The wave summary must be self-sufficient: a reader with only the latest `wave-summary.md`
(plus `plan.md`, `config.md`, and `interfaces/`) can continue execution. This is the rolling-
wave-summary rule — it prevents both information loss and context bloat. Older raw `<role>-output.md`
files are never fed forward; only the wave summary is.

**Self-check before writing:** "Could execution continue correctly from this summary alone?"
If not, add the missing point. Nothing decision-relevant may exist only in a raw agent output.

### `decisions.md` (append-only)

```markdown
## <ISO-8601 timestamp> — Wave <N> — <decision type>
Decision: <what was decided>
Rationale: <why — reference to interface, plan, Sentinel finding, or user answer>
Impact: <files changed, interfaces updated>
Alternatives considered: <if any>
```

### `progress.md` (overwritten on every update — live status board)

```markdown
# Progress
Phase: <n/8> | Wave: <W>/<total estimated> | Updated: <ISO-8601>

## Task Status
| ID | Description | Wave | Role | Status | Files changed |
|----|-------------|------|------|--------|---------------|
| T1 | ... | 1 | data-layer | done | migration.sql |
| T4 | ... | 2 | backend-services | pending | — |

## Escalations in progress
- T<N>: haiku → sonnet (reasoning gap)
OR: none

## Current action
<one-line description of what the Leader is doing right now>

## Convergence signal
all-done | in-progress | stagnation-risk (N waves without completion) | halted
```

### `impact-registry.md` (append-only — never truncate or overwrite)

```markdown
# Impact Registry — <slug>

## Impact IMP-001 — Wave 1 — 2026-05-17T10:00:00Z
- Declared by: data-layer
- File affected: src/users/user.entity.ts
- Change type: schema-changed
- Summary: User entity added deletedAt field for soft delete — all queries filtering
  active users must add WHERE deleted_at IS NULL or use @SoftDelete() decorator
- Downstream tasks briefed: T4, T5
- Interface contract updated: yes (interfaces/db-schema.md)

## Impact IMP-002 — Wave 2 — 2026-05-17T10:15:00Z
...
```

---

## Rolling-wave-summary rule (prevents info loss AND context bloat)

1. After collecting all wave-N agent outputs, write raw returns to `waves/wave-N/<role>-output.md`.
2. Run Critical Issue Scan, Lazy Escalation, Impact Registry update, Wave Reviewer, Integration Verifier.
3. Distill ALL decision-relevant information into `waves/wave-N/wave-summary.md`.
4. Feed ONLY the latest `wave-summary.md` forward to Wave N+1 (injected into Implementation Briefs as "prior wave context"). Never re-read or feed forward raw `<role>-output.md` files from prior waves.
5. Before writing the summary, self-check: "Could execution continue correctly from this summary alone?" If not, add the missing point.

---

## Resource lifecycle

- **Create** — Phase 1 (`mkdir -p` the dirs, seed `plan.md` / `config.md`).
- **Grow** — one `waves/wave-N/` per wave; `impact-registry.md` and `decisions.md` append-only; `progress.md` overwritten each update.
- **Prune (confirm first)** — Phase 8: by default KEEP `DELIVERY.md`, `DELIVERY-NARRATIVE.md`, `impact-registry.md`, `interfaces/`, and the HTML report. Only after explicit user confirmation delete `waves/`, `impacts/wave-*/`, `snapshots/`, `roles/`, `briefs/`.
- **Never** auto-delete the whole session or any deliverable without user confirmation.
