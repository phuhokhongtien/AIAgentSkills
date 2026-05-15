# Orchestration

How the Leader spawns and coordinates team-member agents.

## Leader = main thread (never delegate)

The Claude session running this skill is the Leader. Do NOT spawn a "leader
agent". Reason for the hard rule: a subagent created via the `Agent` tool cannot
reliably spawn its own subagents — `Explore` and `Plan` have no `Agent` tool at
all, and nesting `general-purpose` agents is unsupported in practice. A delegated
leader therefore cannot run the team. The Leader does Phases 1, 2, 5, 6, 7
directly and only spawns team members in Phases 3 and 4.

## Stateless subagents — pass state explicitly

Every `Agent` call is one-shot with zero memory of prior calls or rounds. An
agent knows only what is in its prompt. Therefore each round's prompt must carry
everything the agent needs:

- the problem statement (from `problem.md`),
- the agent's role charter (from `roles/<role>.md`),
- the agent's own prior-round position (from `rounds/round-(N-1)/<role>.md`),
- the Leader's latest `summary.md` ONLY — not the full transcript,
- the specific conflict question(s) assigned this round,
- the explicit output contract.

Never write "as we discussed" or assume continuity. The Leader is the only
component with memory; that memory lives on disk.

## Parallel spawning

Spawn all members of a round in ONE message containing multiple `Agent` tool
calls. They run concurrently and independently — no cross-talk within a round
(cross-examination happens via the Leader's summary in the next round). This is
what makes Round 0 unbiased and each debate round bounded.

## subagent_type selection matrix

| Role intent | `subagent_type` | Why |
|---|---|---|
| Propose / argue / critique / synthesize a position | `general-purpose` | Full reasoning + tools, returns a written argument |
| Research prior art, survey existing code/docs, gather facts | `Explore` | Fast read-only investigation |
| Produce a detailed design / implementation strategy | `Plan` | Architect-style step-by-step design |
| Mechanical formatting / extraction / summarization helper | `general-purpose` (model `haiku`) | Cheap deterministic transform |

Most debate roles are `general-purpose`. Use `Explore` for the Blind-Spot
Hunter when it must scan a real codebase/docs for unstated impacts.

## Per-role model assignment

Pass `model` on every `Agent` call. Do not inherit the user's session model.

| Role type | Default `model` | Rationale |
|---|---|---|
| Architect/Proposer, Devil's-Advocate | `opus` | Hardest reasoning; sets or breaks the solution |
| Domain Expert, Pragmatist, Evaluator, Blind-Spot Hunter | `sonnet` | Strong analysis, ~5× cheaper/faster than Opus |
| Formatting / extraction / mechanical summary | `haiku` | Trivial transforms; no deep reasoning |

Leader synthesis (Phase 5) runs on the main thread = the user's session model.

Override guidance:
- Upgrade a role to `opus` when its lens is decisive for THIS problem
  (e.g. safety/security-critical → Domain Expert to `opus`).
- Downgrade to `haiku` only for roles doing no argumentation.
- Record the final per-role model in `config.md`; echo it in the Round 0 digest
  and the HTML report roster so the user can tune the cost/quality trade-off.

## Per-round prompt template

```
ROLE: <role name>
MISSION: <one line from the role charter>

PROBLEM:
<contents of problem.md>

YOUR PRIOR POSITION (round N-1):
<contents of rounds/round-(N-1)/<role>.md, or "none — this is Round 0">

LEADER SUMMARY OF LAST ROUND (the only shared state — others' raw output is NOT included):
<contents of latest summary.md, or omitted for Round 0>

CONFLICT QUESTIONS TO ADDRESS THIS ROUND:
<specific questions the Leader assigns; omit for Round 0>

OUTPUT CONTRACT — return exactly these sections:
1. POSITION: your recommended solution (or, for Blind-Spot Hunter, "N/A — gap list only")
2. CONCEPTUAL DEMO: design sketch / pseudo-code / trade-off table — NO real code, NO execution
3. EVIDENCE & REASONING: why this beats alternatives, against the success criteria
4. CRITIQUE OF OTHERS: concrete weaknesses in the other positions from the Leader summary
5. ASSUMPTIONS & RISKS
6. CHANGE FROM LAST ROUND: what is NEW vs. your prior position, or "CONCEDE: <to whom/what>"
   — restating a prior point with no new support is not a change
```

For the Blind-Spot Hunter, replace the contract with the gap-list contract from
`references/roles.md`.

## After collecting a round

The Leader writes each raw return to `rounds/round-N/<role>.md`, then distills a
single `rounds/round-N/summary.md` (see `references/state-management.md` for the
summary schema). Only the summary is fed forward — this caps prompt growth and
is the mechanism that prevents both context bloat and information loss.
