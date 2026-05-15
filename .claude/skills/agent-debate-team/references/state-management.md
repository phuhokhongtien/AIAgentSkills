# State Management

The on-disk session is the team's only shared memory. It must be complete
enough that the debate survives context limits and a re-read by the Leader.

## Session directory

Created in the current working directory (gitignored):

```
.agent-team/<slug>/
├── problem.md                  problem, goal, constraints, success criteria, assumptions
├── config.md                   team size, roles, max rounds, decision rule, per-role model
├── roles/<role>.md             one charter per agent (template in references/roles.md)
├── rounds/
│   ├── round-0/<role>.md       raw return per agent
│   ├── round-0/summary.md      Leader roll-up
│   ├── round-1/...
│   └── ...
├── decisions.md                append-only Leader ruling log
├── progress.md                 live status board
└── SOLUTION.md                 final solution + evidence + dissent
```

`<slug>` = kebab-cased short problem name.

## File schemas

### `problem.md`
```
# Problem
<verbatim problem statement>

## Goal
<what a good solution achieves>

## Hard constraints
- ...

## Success / decision criteria
1. <criterion> [weight if criteria-weighted]
...

## Assumptions (resolved or deferred open questions)
- <assumption> — source: Blind-Spot round 0 / user answer <date>
```

### `config.md`
```
preset: lean | balanced | deep | custom
team_size: <n>            # excludes Blind-Spot Hunter
max_rounds: <n>
decision_rule: evidence-weighted | criteria-weighted | leader-call
roles:
  - name: <role>   subagent_type: <...>   model: <opus|sonnet|haiku>
  - ...
  - name: Blind-Spot Hunter   subagent_type: <...>   model: sonnet
```

### `rounds/round-N/summary.md` (the rolling summary — most important file)
```
# Round N Summary
## Candidate solutions on the table
- S1: <one line> (championed by: <roles>)
- S2: ...

## Positions by role
- <role>: <1-2 lines> | change vs N-1: <new / revised / conceded / none>

## Cross-review results
- <role A> → <role B>: <the critique in one line>

## Agreements (frozen — do not reopen)
- ...

## Open conflicts (carried into round N+1)
- C1: <conflict> | bears on criteria: <which> | assigned to: <roles>

## Leader ruling this round (if any)
- <ruling + decision-rule rationale>  (also appended to decisions.md)

## Loop-Prevention Gate result
- cap: <hit/no> | convergence: <...> | stagnation: <...> | irreconcilable: <...>
- decision: continue to round N+1 | STOP → synthesis (reason: <...>)

## What changed this round (the anti-stagnation record)
- <the materially new info, or "NONE — stagnation">
```

The summary must be self-sufficient: a reader with only the latest `summary.md`
(plus `problem.md`/`config.md`) can continue the debate. This is what prevents
information loss as rounds accumulate — older raw `round-*/` files are never fed
forward, only superseded by the latest summary.

### `decisions.md` (append-only)
```
## <ISO timestamp> — round <N> — rule: <decision_rule>
Ruling: <what was decided>
Winner: <position> | Rejected: <positions>
Rationale: <why, against criteria/evidence>
Dissent: <role + revisit-if, or "none">
```

### `progress.md` (overwritten each update — live status board)
```
# Progress
Phase: <n/7> | Round: <N>/<MAX> | Updated: <ISO ts>
| Role | Model | Status (proposed/debating/conceded/done) | Last change |
|------|-------|------------------------------------------|-------------|
Convergence signal: <none | partial | converging | converged>
Next action: <one line>
```

## Rolling-summary rule (prevents info loss AND context bloat)

1. After collecting a round, write raw returns to `rounds/round-N/<role>.md`.
2. Distill into `rounds/round-N/summary.md` capturing every decision-relevant
   point, all open conflicts, all frozen agreements, and all dissent.
3. Feed ONLY the latest summary forward to the next round (per
   `references/orchestration.md`).
4. Before writing the summary, the Leader self-checks: "Could the debate
   continue correctly from this summary alone?" If not, add the missing point.
   Nothing decision-relevant may exist only in a raw round file.

## Resource lifecycle

- **Create** — Phase 1 (`mkdir -p` the dirs, seed `problem.md`/`config.md`).
- **Grow** — one `rounds/round-N/` per round; `decisions.md`/`progress.md`
  updated in place.
- **Prune (confirm first)** — Phase 7: by default KEEP `SOLUTION.md`,
  `decisions.md`, and the HTML report. Only after explicit user confirmation
  delete `rounds/` and other scratch. Suggested:
  `rm -rf .agent-team/<slug>/rounds` (only on confirmation).
- **Never** auto-delete the whole session or any deliverable without the user
  saying yes.
