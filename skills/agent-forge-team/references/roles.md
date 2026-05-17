# Roles

Role catalog, charter templates, and output contracts for every agent in the forge team.

## Role charter template (`roles/<role>.md`)

```
# Role: <name>
- Mission: <one sentence — what this role is accountable for>
- Lens: <the perspective/priority this role applies>
- Owns: <which files or domains this role writes to — must not overlap with other Wave-N roles>
- Out of scope: <what this role must NOT do>
- subagent_type: general-purpose | Explore
- model: opus | sonnet | haiku
- Wave: <wave number>
```

---

## Fixed roles (always present, always in this order)

### Sentinel

```
# Role: Sentinel
- Mission: surface every non-functional risk, missing step, security gap,
  file conflict, and downstream blast radius before any code is written
- Lens: "what could go wrong, what was not said, who else is affected"
- Owns: sentinel-report.md (read-only on all other files)
- Out of scope: proposing implementations, writing code
- subagent_type: Explore (if a codebase exists) | general-purpose (no codebase)
- model: sonnet
- Wave: Phase 3 (before Interface Definer)
```

**Sentinel output contract** — return exactly these sections:

```
SENTINEL REPORT

NON-FUNCTIONAL RISKS (ranked by severity):
1. [CATEGORY] <risk description>
   - Affected tasks: T<IDs>
   - Severity: Critical | High | Medium | Low
   - Mitigation: <specific actionable guard>
   OR Blocker question: <decision-blocking question for the user>

CROSS-CUTTING CONCERNS:
- <concerns not tied to a single task — transaction boundaries, auth context
  propagation, shared mutable state, rate limiting, audit logging, etc.>

FILE CONFLICT PREDICTIONS:
- <file path> — written by <role A> and <role B> in the same wave
  → Resolution: split ownership: <role A owns X, role B owns Y>

DOWNSTREAM BLAST RADIUS:
- <existing functionality that may break beyond the plan's explicit scope>

MISSING PLAN ITEMS:
- <step the plan assumes but does not include>
  → Insert as: T<N>.5 — <description>
  → Wave: <suggested wave placement>
```

Categories for NFR risks (use in brackets):
`SECURITY`, `PERFORMANCE`, `SCALABILITY`, `RELIABILITY`, `COMPLIANCE`,
`ACCESSIBILITY`, `OBSERVABILITY`, `DATA-INTEGRITY`, `COST`, `OPERABILITY`

---

### Interface Definer

```
# Role: Interface Definer
- Mission: define ALL cross-component contracts before any implementation begins,
  so implementers can work in parallel without waiting for each other's code
- Lens: "what must every consumer know to code against this component correctly"
- Owns: interfaces/ directory (all four contract files)
- Out of scope: implementing logic, writing migration SQL that actually runs
- subagent_type: general-purpose
- model: sonnet
- Wave: Phase 4 (after Sentinel, before Implementers)
```

**Interface Definer output contract** — produce these files (Leader writes them to `interfaces/`):

```
## interfaces/api-contracts.md

### <METHOD> <path>
Description: <one sentence>
Auth: required (Bearer JWT, permission: <name>) | none
Request:
  Body: { <field>: <type> — <constraint> }
  Query: { <param>: <type> — <default> }
Response 200:
  { <field>: <type> }
Errors:
  400: <condition>
  401: <condition>
  404: <condition>
Pagination: cursor | offset — params: page, limit (default 20, max 100)

---

## interfaces/service-interfaces.md

interface I<ServiceName> {
  /**
   * <what this method does>
   * @throws NotFoundException when <condition>
   * @throws ConflictException when <condition>
   */
  <methodName>(<param>: <Type>): Promise<<ReturnType>>
}

---

## interfaces/db-schema.md

### Table: <name>
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK, DEFAULT gen_random_uuid() | |
| <col> | <type> | <constraints> | <notes> |

### Relations
- <table A> has many <table B> via <join_table>

### Indexes
- CREATE INDEX ON <table>(<col>) WHERE <condition>

---

## interfaces/component-contracts.md (omit if no frontend tasks)

interface <ComponentName>Props {
  /** <description> */
  <prop>: <type>
}

// Data fetching: <component owns its own fetch | receives data via props>
// Events emitted: <event name> → <payload type>
```

**Coverage rule:** every task in the plan that crosses a component boundary must have its
interface defined here. If a task is purely internal (no other task reads its output), no
interface entry is needed for it.

---

### Wave Reviewer

```
# Role: Wave Reviewer
- Mission: verify semantic consistency across all agent outputs in a wave —
  cross-agent agreement, interface contract conformance, and undeclared impacts
- Lens: "do the outputs fit together and conform to the agreed contracts"
- Owns: nothing (read-only)
- Out of scope: running commands, writing code, calling tools other than Read
- subagent_type: general-purpose
- model: sonnet
- Wave: Phase 5g (after Implementers return, before Integration Verifier)
```

See SKILL.md §5g for the full Wave Reviewer output contract.

---

### Integration Verifier

```
# Role: Integration Verifier
- Mission: run the configured build, test, and lint commands; report pass/fail
  with exact exit codes; recommend proceed, rollback, or partial-rollback
- Lens: "does it still compile and do the tests still pass"
- Owns: nothing (read-only + Bash only)
- Out of scope: reading or modifying source files, reasoning about design
- subagent_type: general-purpose
- model: haiku
- Wave: Phase 5h (after Wave Reviewer)
```

See SKILL.md §5h for the full Integration Verifier output contract.

---

### Archaeology Agent

```
# Role: Archaeology Agent
- Mission: read the full git diff and wave summaries; produce a human-readable
  narrative of what the team built, why, and what a future maintainer must know
- Lens: "tell the story of the build for someone who wasn't in the room"
- Owns: DELIVERY-NARRATIVE.md
- Out of scope: running commands, modifying code
- subagent_type: general-purpose
- model: sonnet
- Wave: Phase 6 (after all waves complete)
```

**Archaeology Agent output contract:**

```
DELIVERY NARRATIVE

## What Was Built
<2-3 paragraph summary of what the team implemented, the key design decisions,
and how the components fit together. Written for a future maintainer.>

## Architectural Decisions & Why
- <decision>: <rationale — drawn from Implementer assumption logs and decisions.md>
- ...

## Plan Drift
<where the plan changed during execution, what triggered each change, and why
the deviation was the right call (or a known risk)>

## What a Future Maintainer Must Know
- <non-obvious constraint or invariant that would surprise a new developer>
- <file or pattern that is load-bearing and must not be changed naively>
- ...

## Open Risks
- <risk that was identified but not resolved — what could go wrong and when>
- ...
```

---

## Derived roles — Implementers

One Implementer per domain group. The Leader assigns domain groups in Phase 2.

### Implementer charter template

```
# Role: <domain>-implementer
- Mission: implement all assigned tasks for the <domain> domain, writing
  real code and running verification commands after each task
- Lens: "build what the interfaces specify, in the files I own, correctly"
- Owns: <explicit list of files — no other wave-W agent may touch these>
- Out of scope: tasks not in the assigned list, modifying files owned by other roles,
  inventing interfaces not in interfaces/
- subagent_type: general-purpose
- model: <haiku | sonnet — set by Leader based on brief completeness>
- Wave: <wave number>
```

### Domain groups (common examples — derive from the actual plan)

| Domain | Typical files | Default model |
|--------|---------------|---------------|
| `data-layer` | entities, migrations, ORM config | `haiku` (brief covers schema from interfaces/db-schema.md) |
| `backend-services` | service classes, business logic | `haiku` (brief covers IService from interfaces/) |
| `backend-api` | controllers, routers, middleware | `haiku` (brief covers API contracts from interfaces/) |
| `frontend-core` | pages, layout, shared components | `haiku` (brief covers component contracts) |
| `frontend-admin` | admin-specific pages and components | `haiku` |
| `tests` | unit tests, integration tests | `sonnet` (requires reasoning about edge cases) |
| `infra` | CI/CD, Docker, env config | `sonnet` (often novel setup, no interface to follow) |

Upgrade a domain to `sonnet` when:
- The task requires novel algorithm or architecture design
- The task is security-critical and the brief cannot pre-specify all decisions
- Previous `haiku` attempt on this domain returned partial/blocked (lazy escalation)

---

## Optional helper roles

### Contract-Stub Agent (pre-wave, optional)

Spawned by Leader when Wave W has Implementers on both sides of an interface boundary
(producer and consumer in the same wave). Runs before 5b (Implementation Briefs).

```
# Role: Contract-Stub Agent
- Mission: generate minimal compilable stub files for interface boundaries so
  both the producer and consumer can import and reference the types immediately
- model: haiku
- subagent_type: general-purpose
```

Output: one stub file per boundary (e.g. `src/users/user.interface.ts` with the
TypeScript interface body). Leader writes the stub files before spawning Implementers.

### Clarification Agent (pre-wave, optional)

Spawned for low-confidence tasks (plan description is vague, e.g. "add caching").
Runs before 5b. Reads the current codebase state and produces a concrete sub-plan
that the Leader uses to write a complete Implementation Brief.

```
# Role: Clarification Agent
- Mission: read the existing codebase for a vague task and produce a specific,
  actionable sub-plan that the Leader can use to write a complete brief
- model: sonnet
- subagent_type: Explore
```

Output: specific file paths, concrete implementation approach, suggested error handling,
and any assumptions that need user confirmation. Leader uses this output to fill in the
Implementation Brief for that task; only escalates to `AskUserQuestion` if the Clarification
Agent identifies a genuine product decision.
