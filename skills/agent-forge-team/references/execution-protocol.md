# Execution Protocol

Dependency graph format, interface-first parallelism, Impact Ripple System, plan-drift rule,
and rollback procedures.

---

## Interface-First Parallelism

### The problem with dependency-driven waves

A naive dependency graph creates many sequential waves. Each wave must wait for the previous:

```
Schema → Entities → Services → Guards → Controllers → Frontend → Tests
  W0       W1         W2         W3         W4           W5        W6
```

This forces 7 sequential steps even though most code-level dependencies are just type imports —
not runtime execution dependencies.

### The interface-first insight

A service implementer does not need the entity *implementation* — it needs the entity *type*.
A frontend component does not need the real API — it needs the API *contract*. Tests can be
written against interfaces before the implementations exist.

By defining all contracts upfront (Interface Definer, Phase 4), code-level dependencies
disappear. Only *runtime execution dependencies* remain sequential.

**Result (default parallel mode — 3 waves):**

```
Sentinel → Interface Definer → [db-layer | services | api | frontend | tests] → Verifier
  Ph3         Ph4                          Wave 2 (all parallel)                   Ph5h
```

### What remains sequential (true runtime dependencies)

| Dependency type | Why it's real | Placement |
|---|---|---|
| DB migrations must run before any service | App crashes without the table | Wave 1 |
| Library/package installs | Code doesn't compile without them | Wave 1 |
| Infra scaffold (Docker network, secrets) | Services can't start | Wave 1 |
| E2E tests that require a running server | Can't simulate the full stack | Wave 3 |

Everything else: code to the interface, run in parallel.

### File ownership — enforced, not suggested

Two agents writing the same file in the same wave WILL produce conflicting outputs (one agent's
edit overwrites the other's). The Leader must assign specific filenames to each role charter
before spawning Wave W. Ownership is set in Phase 2 when writing charters.

**Conflict resolution (in order of preference):**
1. Split file ownership (preferred) — each agent owns distinct files
2. Serialize (add a dependency edge) — if the file cannot be split
3. Merge via Leader on main thread after both agents return — only as a last resort

---

## Dependency Graph Format

File: `.agent-forge/<slug>/dependency-graph.md`

```markdown
# Dependency Graph — <slug>

## Task Registry
| ID  | Description | Wave | Role | Depends on | File ownership |
|-----|-------------|------|------|------------|----------------|
| T1  | Create DB schema DDL | 1 | data-layer | — | migrations/001_init.sql |
| T2  | User entity + TypeORM | 1 | data-layer | T1 | src/users/user.entity.ts |
| T3  | Role + Permission entities | 1 | data-layer | T1 | src/roles/role.entity.ts, src/roles/permission.entity.ts |
| T4  | UserService | 2 | backend-services | T1* | src/users/users.service.ts |
| T5  | RoleService | 2 | backend-services | T1* | src/roles/roles.service.ts |
| T6  | UsersController | 2 | backend-api | — | src/users/users.controller.ts |
| T7  | Frontend UsersTable | 2 | frontend-core | — | src/components/users/UsersTable.tsx |
| T8  | Unit tests: UserService | 2 | tests | — | src/users/users.service.spec.ts |

*code-level dependency resolved by Interface Definer (IUserEntity type is in interfaces/)

## Waves
Wave 1: T1, T2, T3  (data-layer — runtime sequential)
Wave 2: T4, T5, T6, T7, T8  (all parallel — code to interfaces/)
Wave 3: T9 (E2E — requires running server)

## File Ownership Map (Wave 2)
backend-services: src/users/users.service.ts, src/roles/roles.service.ts
backend-api:      src/users/users.controller.ts, src/roles/roles.controller.ts
frontend-core:    src/components/users/UsersTable.tsx, src/components/users/UserFormModal.tsx
tests:            src/**/*.spec.ts

## Impact Briefings Required
(populated during execution — Leader appends after each wave)
Wave 1 → T4, T5: User entity has deletedAt (soft delete) — use WithDeleted() or filter deleted_at IS NULL
```

### Dependency detection heuristics (Leader applies in Phase 2)

| Heuristic | Dependency type | Example |
|---|---|---|
| Task B reads a file Task A creates | file-write | migration file created in T1, read by entity in T2 |
| Task B imports a type/class Task A defines | type (resolved by Interface Definer) | Service imports Entity type |
| Task B processes data Task A seeds | data | seed task before data-dependent test |
| Explicit "after X" or "once Y is done" in plan text | explicit ordering | plan says "after migrations run, create services" |
| Task B's tests exercise Task A's code | test dependency | unit test depends on service implementation |

---

## Impact Ripple System

### Purpose

Implementers change things other agents' code depends on. Without notification, the next wave
agents code against stale assumptions. The Impact Ripple System is the structured mechanism
for propagating these changes forward.

### Registry entry schema

File: `.agent-forge/<slug>/impacts/impact-registry.md` (append-only)

```markdown
## Impact IMP-<NNN> — Wave <W> — <ISO-8601 timestamp>
- Declared by: <role name>
- File affected: <path>
- Change type: signature-changed | interface-added | interface-removed |
               schema-changed | behavior-changed | config-changed | file-deleted
- Summary: <one sentence — what changed and what callers must do differently>
- Downstream tasks briefed: T<IDs>
- Interface contract updated: yes (<interfaces/file.md>) | no
```

### Ripple propagation process (Leader runs in step 5f)

1. Read every `IMPACT DECLARATIONS` section from wave W outputs.
2. For each declared impact:
   a. Append a new `IMP-NNN` entry to `impact-registry.md`.
   b. Consult `dependency-graph.md` to find which future tasks touch the affected file.
   c. If the impact changes an interface (not just an internal implementation detail) →
      update `interfaces/<file>.md` to reflect the actual produced contract.
3. Write `impacts/wave-W-ripple.md` — one entry per impact, formatted as an injected briefing:

```markdown
# Wave W Impact Ripple — injected into Wave W+1 Implementation Briefs

## IMP-<NNN> (from <role>, Wave W)
File: <path>
Change: <what changed>
Action required: <what the receiving agent must do differently>
Affects tasks: T<IDs>
```

4. When writing Wave W+1 Implementation Briefs, filter `wave-W-ripple.md` to include
   only the entries that affect files the target Implementer will touch.

### Three conflict tiers

| Tier | When | How handled |
|---|---|---|
| **Predicted** | Sentinel Phase 3 finds two agents writing the same file | Leader splits file ownership in charters before any code is written; no ripple needed |
| **Runtime deviation** | Implementer declares an impact that changes an interface | Leader updates `interfaces/` + adds ripple briefing for next wave; no stop |
| **Integration failure** | Integration Verifier reports FAIL | Gate in §5i → rollback or partial-rollback |

---

## Plan Drift Rule

When an Implementer returns `partial` or `blocked`, the Leader applies this decision table:

| Blocker type | Leader action | Escalate to user? |
|---|---|---|
| Missing technical setup (library not installed, config file absent, scaffold needed) | Leader creates the gap-fill directly on main thread using its own tools | No |
| Reasoning gap (agent couldn't figure out how to implement despite full brief) | Re-spawn with `sonnet` + enriched brief (add more pattern reference, clearer error handling) | No |
| Missing runtime dependency (migration not run, service not started) | Leader runs the required command | No |
| Interface ambiguity (two equally valid interpretations of a contract) | Leader picks the conservative / backwards-compatible interpretation; logs in `decisions.md` | No |
| Product / business decision (changes API semantics, data model meaning, auth behaviour) | `AskUserQuestion` — surface the decision, present options | Yes |
| Missing requirement that changes user-visible behaviour | `AskUserQuestion` | Yes |
| Interface is genuinely wrong (Interface Definer made an error) | Leader corrects `interfaces/<file>.md`, re-spawns affected tasks as correction sub-wave | No (unless product decision implied) |

**Correction sub-waves:** when tasks need re-running after a fix, the Leader spawns them as
wave `W-fix` (same wave number, `-fix` suffix) so the wave summary captures the correction.
The correction sub-wave still takes a snapshot and runs Wave Reviewer + Integration Verifier.

---

## Rollback Procedures

### Pre-wave snapshot (always taken before spawning any Implementer)

```bash
# git-stash policy (default)
git stash push -m "agent-forge-${SLUG}-pre-wave-${W}" --include-untracked
STASH_ID=$(git stash list | head -1 | grep -oE 'stash@\{[0-9]+\}')
echo "stash: $STASH_ID" > ".agent-forge/${SLUG}/snapshots/wave-${W}.md"

# branch policy
git checkout -b "agent-forge-${SLUG}-wave-${W}"
BRANCH="agent-forge-${SLUG}-wave-${W}"
echo "branch: $BRANCH" > ".agent-forge/${SLUG}/snapshots/wave-${W}.md"
```

### Full rollback

```bash
# stash policy
STASH=$(grep "^stash:" ".agent-forge/${SLUG}/snapshots/wave-${W}.md" | cut -d' ' -f2)
git stash apply "$STASH"    # or pop if this is the top stash
git stash drop "$STASH"     # clean up after apply

# branch policy
git checkout "$(git rev-parse --abbrev-ref HEAD~0)"  # go back to base
git branch -D "agent-forge-${SLUG}-wave-${W}"
```

### Partial rollback (PARTIAL-ROLLBACK from Integration Verifier)

1. Identify which tasks failed (from Integration Verifier's `Failed:` list and `REGRESSION RISK`).
2. Map failing tasks to their file ownership (from `dependency-graph.md`).
3. Restore only those files from the snapshot:

```bash
# stash policy — restore specific files only
git checkout "$STASH_ID" -- src/users/users.controller.ts src/users/users.service.ts

# branch policy — restore from base branch
git checkout <base-branch> -- src/users/users.controller.ts
```

4. Re-queue the failing tasks as a correction sub-wave (wave `W-fix`).
5. Do NOT roll back the passing tasks — their work is kept.

### No-rollback-policy warning

If `rollback_policy = none`, the Leader prints before every wave:
> "No snapshot configured. Proceeding without rollback safety for Wave W.
> Current git state: <output of git status --short>"

Never silently lose work.

---

## Loop prevention for wave execution

The execution loop must terminate even if something goes wrong. Termination conditions (check after every wave):

1. **All tasks done** — all T-IDs in `plan.md` are marked `done` → proceed to Phase 6.
2. **Hard cap** — wave count exceeds `MAX_WAVES` (default: 10) → Leader stops, writes
   `DELIVERY.md` with current state, notifies user.
3. **Stagnation** — two consecutive waves produced zero new completed tasks (only
   partial/blocked) → Leader stops and uses `AskUserQuestion` to decide: abort, re-plan,
   or continue manually.
4. **User abort** — user responds to any `AskUserQuestion` with a stop signal.
