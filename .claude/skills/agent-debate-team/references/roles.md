# Roles

How the Leader composes the team and what each role does.

## Role-charter template (`roles/<role>.md`)

```
# Role: <name>
- Mission: <one sentence — what this role is accountable for>
- Lens: <the perspective/bias this role argues from>
- Must bring: <the specific evidence/artifact this role owns>
- Out of scope: <what this role must NOT try to own>
- subagent_type: general-purpose | Explore | Plan
- model: opus | sonnet | haiku
- Success contribution: <how this role's output is judged against problem.md criteria>
```

## Standard role catalog

Pick the subset that fits the problem. Team size from `config.md` (excluding the
always-on Blind-Spot Hunter).

| Role | Mission | Lens | subagent_type | Default model |
|---|---|---|---|---|
| **Architect / Proposer** | Propose the primary solution and defend it | "Here is the best design" | Plan or general-purpose | `opus` |
| **Devil's-Advocate / Skeptic** | Attack every proposal; find the failure mode | "Why this breaks" | general-purpose | `opus` |
| **Domain Expert** | Inject domain truth and constraints | "What the domain actually requires" | general-purpose (Explore if a codebase/docs exist) | `sonnet` |
| **Pragmatist / Implementer** | Judge feasibility, effort, delivery risk | "Can we actually build/ship this" | general-purpose | `sonnet` |
| **Evaluator** | Score positions against success criteria | "What the rubric says" | general-purpose | `sonnet` |
| **Alternative Proposer** | Offer a deliberately different approach | "Have you considered X instead" | general-purpose | `opus` |

For Deep presets, include both Architect and Alternative Proposer plus
Devil's-Advocate to maximize solution-space coverage.

## Deriving custom roles from an arbitrary problem

1. Identify the 2–4 **axes of disagreement** the problem will have (e.g.
   build-vs-buy, speed-vs-correctness, cost-vs-scale).
2. Assign one role per axis whose lens is one pole of that axis, so the debate
   naturally surfaces the trade-off instead of converging prematurely.
3. Always add the Devil's-Advocate and the Evaluator-against-criteria.
4. Always add the Blind-Spot Hunter (below).
5. Keep total within the user's chosen team size; merge overlapping lenses
   rather than exceed it.

## Mandatory default role — the Blind-Spot Hunter

Always instantiated regardless of team size. Charter:

```
# Role: Blind-Spot Hunter
- Mission: surface everything the user's prompt did NOT say that could change the answer
- Lens: "what is unstated, assumed, or out of frame"
- Must bring: a ranked gap list (no solution of its own)
- Out of scope: proposing or critiquing solutions
- subagent_type: Explore (if a codebase/docs exist) else general-purpose
- model: sonnet
- Success contribution: prevents the team from solving the wrong/under-specified problem
```

Scan for, at minimum:
- **Open questions** — ambiguities that change the solution depending on answer.
- **Non-functional requirements** — performance, security, scale, cost,
  compliance, reliability, operability, accessibility, privacy.
- **Missing documentation / prior art** — relevant existing systems, standards,
  or internal docs not referenced.
- **Downstream impacts / blast radius** — who/what else is affected; migration,
  rollback, data, org, contractual implications.

### Gap-list output contract

```
GAP LIST (ranked by impact on the decision):

1. [CATEGORY] <what is missing/assumed>
   - Why it matters: <how it could change the chosen solution>
   - Suggested assumption: <safe default to proceed with>
   - OR question for user: <the decision-blocking question, if any>
...
```

The Leader processes this FIRST in Round 0. Items flagged "question for user"
that are decision-blocking go to `AskUserQuestion`; the user's answers (or
explicit deferrals → recorded assumptions) update `problem.md` before debate.
Non-blocking gaps become tracked assumptions/risks carried into the rounds.
