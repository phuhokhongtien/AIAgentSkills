# Orchestration

How the Leader spawns, briefs, and coordinates the forge team.

## Leader = main thread (never delegate)

The Claude session running this skill IS the Leader. Do NOT spawn a "leader agent" or an
"orchestrator agent". A subagent created via the `Agent` tool cannot reliably spawn its own
subagents — `Explore` and `Plan` types have no `Agent` tool at all, and nesting
`general-purpose` agents is unsupported in practice. A delegated leader breaks the team.

The Leader acts directly in Phases 1, 2, 6, 7 (reasoning, file writing, synthesis) and spawns
team members via the `Agent` tool only in Phases 3–5.

## Stateless subagents — pass everything explicitly

Every `Agent` call is one-shot with zero memory. An agent knows only what is in its prompt.
Therefore each agent's prompt must carry:

- Its role charter (from `roles/<role>.md`)
- Its Implementation Brief (from `briefs/<role>-brief.md`) — for Implementers
- The interface contracts relevant to its tasks (from `interfaces/`)
- The impact briefing from prior waves (from `impacts/wave-(W-1)-ripple.md`, filtered)
- The explicit output contract

Never write "as we discussed" or assume any continuity. The Leader is the only component with
memory; that memory lives on disk.

## Parallel spawning

Spawn all Implementers in a wave in **ONE message** containing multiple `Agent` tool calls.
They run concurrently and independently — no cross-talk within a wave. Cross-wave communication
happens via the Leader's ripple briefings.

Fixed agents (Sentinel, Interface Definer, Wave Reviewer, Integration Verifier, Archaeology Agent)
are always spawned individually — one at a time, in sequence.

## subagent_type selection

| Role intent | `subagent_type` | Why |
|---|---|---|
| Sentinel scanning a codebase for risks | `Explore` | Fast read-only investigation across many files |
| Sentinel with no existing codebase | `general-purpose` | Reasoning only |
| Interface Definer | `general-purpose` | Reasoning + structured output |
| Implementer (writes code, runs commands) | `general-purpose` | Needs all tools: Read, Write, Edit, Bash |
| Wave Reviewer | `general-purpose` | Reasoning across multiple outputs |
| Integration Verifier | `general-purpose` | Runs commands via Bash |
| Archaeology Agent | `general-purpose` | Reads git diff + summaries, writes narrative |

## Model tiering

Pass `model` on every `Agent` call. Do not inherit the user's session model.

| Role | Default model | Rationale |
|---|---|---|
| Leader (main thread) | user's session model | Full orchestration + synthesis |
| Sentinel | `sonnet` | Risk reasoning across the entire plan |
| Interface Definer | `sonnet` | Cross-system contract design |
| Wave Reviewer | `sonnet` | Semantic cross-checking |
| Implementer — detailed brief + CRUD/mechanical task | `haiku` | Mechanical execution; brief supplies the reasoning |
| Implementer — complex, security-critical, or multi-file design | `sonnet` | Needs reasoning beyond a brief |
| Integration Verifier | `haiku` | Runs commands and parses output — no reasoning |
| Archaeology Agent | `sonnet` | Synthesis narrative |
| Contract-stub helper (optional pre-wave) | `haiku` | Mechanical stub generation |

**Escalation rule:** if a `haiku` Implementer returns `partial` or `blocked` with a reasoning
gap, the Leader re-spawns the same task with `sonnet` and an enriched brief. Log the escalation
in `waves/wave-W/wave-summary.md` and surface it in the HTML report. Never over-provision
upfront; lazy escalation keeps costs proportional to actual complexity.

## Implementation Brief format

The Implementation Brief is the Leader's primary lever for cost control. The richer the brief,
the cheaper the model that can execute it. A haiku agent with a complete brief outperforms a
sonnet agent with a vague task description.

Leader writes `briefs/<role>-brief.md` before spawning each wave. The brief must include:

```
IMPLEMENTATION BRIEF — <role name> — Wave <W>

ASSIGNED TASKS: T<N>, T<M>, ...

FILES TO CREATE/MODIFY:
  - CREATE: <absolute path> — <purpose>
  - MODIFY: <absolute path> — <what section to add/change and why>

INTERFACES TO IMPLEMENT (verbatim from interfaces/):
  [paste the exact TypeScript interface, API contract, or schema section
   that this agent must implement — do not paraphrase]

PATTERN REFERENCE:
  [Leader reads an analogous existing file in the codebase and includes a
   short representative snippet so the agent matches project conventions]
  Example: "Follow src/products/products.service.ts — inject via
  @InjectRepository(Product), use QueryBuilder for paginated queries"

ERROR HANDLING:
  - <specific condition> → throw <ExceptionClass>
  - <specific condition> → return <value / status>

IMPACT BRIEFING FROM PRIOR WAVES:
  [Paste the relevant section of impacts/wave-(W-1)-ripple.md filtered to
   files this agent will touch. Omit for Wave 1.]

VERIFICATION:
  Run after your changes: <command>
  Expected: <exit code / output summary>
```

**Model assignment decision** (Leader makes this per-role before writing the brief):

```
if task is: single-file | pure CRUD | mechanical scaffold | clear interface provided
   AND brief is: complete (all fields filled, pattern reference included)
→ assign haiku

if task is: multi-file | security-critical | requires design reasoning | novel algorithm
   OR brief is: incomplete (pattern reference missing, error handling complex)
→ assign sonnet

if in doubt → assign haiku; lazy escalation handles failures
```

## Per-agent prompt template

```
ROLE: <role name>
MISSION: <one line from the role charter>

ROLE CHARTER:
<contents of roles/<role>.md>

IMPLEMENTATION BRIEF:
<contents of briefs/<role>-brief.md>

INTERFACE CONTRACTS (read-only reference — do not invent interfaces):
<relevant sections of interfaces/api-contracts.md, service-interfaces.md,
 db-schema.md, or component-contracts.md>

IMPACT BRIEFING FROM PRIOR WAVES:
<filtered contents of impacts/wave-(W-1)-ripple.md — only entries relevant to
 the files this agent will touch>

OUTPUT CONTRACT — return exactly these sections:
[paste the Implementer output contract from SKILL.md §5c]
```

## After collecting a wave

The Leader, in order:
1. Runs the Critical Issue Scan (§5d) — no summaries written yet.
2. Handles lazy escalation (§5e) for partial/blocked tasks.
3. Reads all Impact Declarations → writes `impacts/impact-registry.md` and `impacts/wave-W-ripple.md`.
4. Spawns Wave Reviewer → processes its output (updates `interfaces/` if needed).
5. Spawns Integration Verifier → applies gate decision.
6. Writes `waves/wave-W/wave-summary.md` (the rolling summary — see state-management.md).
7. Updates `progress.md` and `TodoWrite`.
8. Prints the Wave Transparency Digest to the user.
