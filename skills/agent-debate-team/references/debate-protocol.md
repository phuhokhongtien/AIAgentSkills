# Debate Protocol

The rules that make the debate converge and terminate.

## Round structure

- **Round 0 — Independent proposals.** All roles spawned in parallel with no
  shared context. Produces the initial position set + the Blind-Spot gap list.
  No critique yet (nobody has seen others' work).
- **Rounds 1..MAX — Debate.** Each round, every agent sees the Leader's summary
  of the previous round (positions + the conflicts the Leader wants resolved)
  and must advance the argument or concede.
- After each round the Leader writes the summary, prints the transparency
  digest, runs the Loop-Prevention Gate, and resolves conflicts.

## Output contract (enforced by the Leader)

Every debate agent must return: POSITION, CONCEPTUAL DEMO, EVIDENCE & REASONING,
CRITIQUE OF OTHERS, ASSUMPTIONS & RISKS, CHANGE FROM LAST ROUND. The Leader
rejects (and does not count toward progress) any return whose "CHANGE FROM LAST
ROUND" is a restatement with no new option, evidence, or trade-off.

## Loop-Prevention Gate

Evaluate after EVERY round, in order. Stop on the first hit.

1. **Hard cap** — `current_round >= MAX_ROUNDS` from `config.md` → stop, go to
   synthesis. This alone guarantees termination regardless of agent behavior.
2. **Convergence** — every agent's POSITION reduces to the same solution, OR all
   remaining differences are immaterial to the success criteria in
   `problem.md` → stop.
3. **Stagnation** — apply the checklist below to the just-finished round vs. the
   prior `summary.md`. If ALL boxes are "no", the round added nothing → stop.
4. **Irreconcilable conflict** — agents repeat opposing positions across two
   consecutive rounds with no new support on the contested point → the Leader
   invokes the decision rule, decides, records dissent, stops.

The Leader always force-decides at the cap. Never start round MAX+1.

### Stagnation checklist (round N vs. round N-1 summary)

- [ ] A new candidate solution or material variant appeared?
- [ ] New evidence or reasoning supporting/refuting a position appeared?
- [ ] A new trade-off, constraint, or risk was surfaced?
- [ ] At least one agent meaningfully revised its position or conceded?

All "no" → stagnation → stop.

## Conflict-resolution decision rules

The user picks one in Phase 1; stored in `config.md`.

- **`evidence-weighted`** — the Leader scores each surviving position by the
  strength and specificity of its evidence/critique. Strongest evidence wins;
  ties broken by fewest unmitigated risks.
- **`criteria-weighted`** — the Leader scores each position against the explicit
  success criteria in `problem.md` (optionally weighted). Highest total wins.
  Use when the user gave clear, rankable criteria.
- **`leader-call`** — the Leader decides using judgement, stating the rationale.
  Use for ambiguous problems with no clean scoring rubric.

In all three the Leader MUST: name the winner, name the rejected alternatives,
state the rationale, and record any dissent. Append to `decisions.md`.

## Dissent recording format

When the chosen solution overrides a strongly-held opposing position, record it
so it is not lost:

```
### Dissent — round <N>
- Dissenting role: <role>
- Position overruled: <one line>
- Their strongest argument: <one line>
- Why overruled: <decision-rule rationale>
- Revisit-if: <condition under which this decision should be reconsidered>
```

Dissent appears in `SOLUTION.md` and the HTML report — a recorded minority view,
not an erased one.

## Conflict triage between rounds

The Leader need not relitigate everything each round. Each round, target the
1–3 conflicts with the highest impact on the success criteria; ask only the
agents whose lens bears on those conflicts the specific CONFLICT QUESTIONS.
Settled points are frozen in the summary and not reopened unless new evidence
directly contradicts them.
