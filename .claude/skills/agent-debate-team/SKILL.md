---
name: agent-debate-team
description: This skill should be used when the user wants to "build a team of agents to solve" a problem, "have agents debate a solution", "assemble an agent team", run a "multi-agent debate", "get agents to argue the best approach", or "tranh luận giữa các agent" to converge on the best solution. Use when a hard or open-ended problem benefits from multiple specialized perspectives, structured argument, and a coordinated leader making the final call — with guaranteed termination (no infinite debate), live transparency to the user, and a written decision record.
version: 0.1.0
tools: Read, Write, Glob, Grep, Bash, Agent, TodoWrite, AskUserQuestion
---

# Agent Debate Team

Assemble a team of specialized agents that independently propose, then debate,
then converge on the best solution to a problem — coordinated by a Leader that
keeps everyone on-goal, resolves conflicts, and produces a written decision plus
an interactive HTML report.

## Two non-negotiable constraints — read first

1. **The main Claude session running this skill IS the Leader.** Never delegate
   the Leader/orchestrator role to a subagent. Subagents spawned via the `Agent`
   tool cannot reliably spawn their own subagents, so a delegated leader cannot
   run the team. The Leader reasons directly (Phases 2, 5) and spawns team
   members via the `Agent` tool (Phases 3, 4).
2. **Team members are stateless one-shot subagents.** Each `Agent` call has no
   memory of prior rounds. Debate continuity exists ONLY in the on-disk session
   state the Leader writes and feeds back into each agent's prompt every round.
   Never assume an agent remembers anything not in its prompt.

Conceptual demos only — agents produce design sketches, pseudo-code, and
reasoned trade-off analysis as evidence. They do NOT write or execute code.

---

## Phase 1 — Intake & Configuration

Capture the problem from the user. Then ask (use `AskUserQuestion`):

- **Goal** — what a good solution must achieve.
- **Hard constraints** — non-negotiables (tech, budget, deadline, compliance).
- **Success / decision criteria** — how the Leader will judge the winner.
- **Debate configuration** — offer presets, let the user override every field:

| Preset | Team size | Max rounds |
|---|---|---|
| Lean | 2–3 | 2 |
| Balanced (default) | 3–5 | 3 |
| Deep | 4–6 | 5 |

Also confirm with the user: role set (auto-derive vs. user-specified),
**decision rule** (`evidence-weighted` / `criteria-weighted` / `leader-call` —
see `references/debate-protocol.md`), and the **per-role model tier** (defaulted
by the policy table in Phase 2, user may override).

Create the session directory and seed files (see
`references/state-management.md` for exact schemas):

```bash
SLUG=$(echo "<short-problem-slug>" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
SESSION=".agent-team/$SLUG"
mkdir -p "$SESSION/roles" "$SESSION/rounds"
```

Write `problem.md` and `config.md`. Start a `TodoWrite` plan: one item per phase
plus one per planned round.

---

## Phase 2 — Leader Designs the Team

Reason directly (no subagent). Derive concrete roles from the problem using
`references/roles.md` (e.g. Architect/Proposer, Devil's-Advocate/Skeptic,
Domain Expert, Pragmatist/Implementer, Evaluator-against-criteria). Write each
`roles/<role>.md` charter and initialize `progress.md`.

### Per-agent model assignment (cost/latency tiering)

The user's session may run on Opus, but the team must NOT default every member
to Opus. Assign a model per role via the `Agent` tool's `model` parameter,
matched to the role's cognitive load — not the user's session model:

| Role type | Default model | Rationale |
|---|---|---|
| Architect/Proposer, Devil's-Advocate, Leader synthesis (main thread) | `opus` | Hardest reasoning; sets or breaks the solution |
| Domain Expert, Pragmatist, Evaluator, Blind-Spot Hunter | `sonnet` | Solid analysis at much lower cost/latency |
| Formatting / extraction / mechanical summarization helpers | `haiku` | Cheap, deterministic, no deep reasoning |

Upgrade a role when the problem warrants (e.g. safety-critical domain → its
Domain Expert to `opus`). Record the chosen model per role in `config.md`; it
appears in the Round 0 digest and the HTML report roster. Full guidance in
`references/orchestration.md`.

### Always-present default role — the Blind-Spot Hunter

Independent of the chosen team size, ALWAYS instantiate one Blind-Spot Hunter.
Its sole mission: surface what the user's prompt did **not** say — unstated
open questions, non-functional requirements (performance, security, scale, cost,
compliance, operability, accessibility), missing/relevant documentation or prior
art, and downstream impacts / blast radius. It proposes **no solution** — it
outputs a ranked **gap list** (each item: what's missing, why it matters,
suggested assumption OR a question for the user). Charter in
`references/roles.md`.

---

## Phase 3 — Round 0: Independent Proposals

Spawn all role agents **in parallel** — a single message with multiple `Agent`
tool calls. Pick `subagent_type` per `references/orchestration.md`
(`general-purpose` default; `Explore` for research-heavy; `Plan` for
design-heavy) and pass the `model` from `config.md`.

Each prompt = problem + that role's charter + the output contract (position +
conceptual demo: design sketch / pseudo-code / trade-off table + stated
assumptions + risks). Independent first pass — no cross-talk, no anchoring. The
Blind-Spot Hunter is in this same batch.

Process the **Blind-Spot Hunter's gap list first**. Surface it to the user in
the Round 0 digest. If it contains decision-blocking open questions, use
`AskUserQuestion` to let the user resolve or explicitly defer them (record
deferrals as assumptions in `problem.md`) **before** the debate proceeds.

Write each return to `rounds/round-0/<role>.md`, then write
`rounds/round-0/summary.md` (clustered positions, overlaps, explicit conflict
list, gap list). Update `progress.md`. Print the Round 0 transparency digest
(see below) before Phase 4.

---

## Phase 4 — Debate Rounds (1..MAX)

Per round, spawn agents in parallel. Each prompt =

- the problem,
- that agent's **own prior position**,
- the Leader's **latest `summary.md` only** (never the full transcript — this
  prevents context bloat and information loss),
- the **specific conflict question(s)** the Leader assigns this agent.

Output contract: defend or revise **with NEW reasoning/evidence, or explicitly
concede**. Restating a prior point without new support does not extend debate.

Then the Leader, in order:

1. Write `rounds/round-N/<role>.md` for each agent + `rounds/round-N/summary.md`.
2. **Print the live transparency digest to the user** (see below).
3. Run the **Loop-Prevention Gate** (next section).
4. Resolve conflicts per the configured decision rule
   (`references/debate-protocol.md`); append rulings to `decisions.md`.
5. Update `progress.md` and `TodoWrite`. Continue or stop.

### Live transparency digest (every round, including Round 0)

Print to the conversation, concisely:

- **Candidate solution(s)** currently on the table.
- **Each agent's position** — 1–2 lines per role.
- **Cross-review results** — what each agent critiqued in others' proposals.
- **Open conflicts** + the Leader's direction for the next round, OR the stop
  reason if the debate is ending.

The user may interject between rounds.

---

## Loop-Prevention Gate (mandatory)

After **every** round, evaluate in order — the debate MUST stop on the first hit:

1. **Hard cap** — `current_round >= MAX_ROUNDS` → stop.
2. **Convergence** — all agents agree on one solution, or all remaining
   disagreements are immaterial to the success criteria → stop.
3. **Stagnation** — the round added no new option, no new evidence, no new
   trade-off (only restatements), per the checklist in
   `references/debate-protocol.md` → stop.
4. **Irreconcilable conflict** — agents repeat opposing positions with no new
   support → Leader invokes the decision rule and decides; dissent recorded;
   debate ends.

The Leader **always force-decides at the cap**. A round never extends the
debate unless it introduced materially new information.

---

## Phase 5 — Leader Synthesis & Decision

Reason directly (no subagent). Synthesize the winning solution from the evidence
against the success criteria. Record rejected alternatives and any dissent.
Write `SOLUTION.md` and the final `decisions.md` entry.

---

## Phase 6 — Generate HTML Report & Auto-Open

Read `assets/report-template.html`, replace every `{{PLACEHOLDER}}` with report
data (JSON-encode complex objects, escape HTML in strings): problem, config,
role roster (with per-role model), per-round positions, conflict map, decision
log, final solution, dissent, rounds/budget used.

Save `agent-debate-report-YYYYMMDD-HHmmss.html` in the current working
directory. Auto-open by OS:

```bash
uname -s 2>/dev/null | grep Darwin && open "agent-debate-report-"*.html
uname -s 2>/dev/null | grep Linux  && xdg-open "agent-debate-report-"*.html
cmd.exe /c start "" "agent-debate-report-YYYYMMDD-HHmmss.html" 2>/dev/null
```

Print the report path and confirm it opened.

---

## Phase 7 — Cleanup

Confirm the rolling summaries captured everything important. Then **ask the
user** before pruning. By default keep `SOLUTION.md`, `decisions.md`, and the
HTML report. Offer to delete intermediate `rounds/` and the session scratch.
Never auto-delete without explicit confirmation.

---

## References

- `references/orchestration.md` — Leader=main-thread rule, parallel spawning,
  `subagent_type` matrix, per-role model policy, per-round prompt template,
  stateless-subagent state passing.
- `references/debate-protocol.md` — round structure, output contract,
  loop-prevention gate + stagnation checklist, decision rules, dissent format.
- `references/roles.md` — role catalog, deriving custom roles, charter template,
  the mandatory Blind-Spot Hunter charter + gap-list contract.
- `references/state-management.md` — session dir schema, file formats, the
  rolling-summary rule (prevents info loss), resource lifecycle, confirm-before-
  delete.
- `assets/report-template.html` — HTML report template with `{{PLACEHOLDER}}`s.
