# Ticket Ingestion

How the Leader detects ticket input, fetches ticket data from external systems, maps fields
to plan fields, collects subtasks recursively, maps subtasks to the wave system, and updates
ticket statuses in real-time as agents complete work.

---

## URL and ID Detection Patterns

Apply in order — first match wins.

### Full URL patterns

| System | URL regex | Fields to parse |
|---|---|---|
| GitHub Issue | `github\.com/([^/]+)/([^/]+)/issues/(\d+)` | owner, repo, issue_number |
| GitHub PR | `github\.com/([^/]+)/([^/]+)/pull/(\d+)` | owner, repo, pull_number |
| Linear | `linear\.app/([^/]+)/issue/([A-Z]+-\d+)` | org_slug, issue_id |
| Jira (Atlassian Cloud) | `([^/]+)\.atlassian\.net/browse/([A-Z]+-\d+)` | org, issue_key |
| Jira (self-hosted) | `jira\.[^/]+/browse/([A-Z]+-\d+)` | issue_key |
| Azure DevOps | `dev\.azure\.com/([^/]+)/([^/]+)/_workitems/edit/(\d+)` | org, project, id |
| Azure DevOps (legacy) | `([^/]+)\.visualstudio\.com/([^/]+)/_workitems/edit/(\d+)` | org, project, id |

### Plain-ID patterns (only when no URL and no task list present)

| Pattern | Candidate system(s) | Ambiguity action |
|---|---|---|
| `[A-Z]{2,10}-[0-9]+` (e.g. `ENG-123`, `ACME-456`) | Jira or Linear | Ask user to confirm system via `AskUserQuestion` before fetching |
| `#[0-9]+` with explicit "work item" or "ADO" mention | Azure DevOps | Confirm org + project with user |
| Linear ID with known team prefix (from prior session context) | Linear | Proceed directly |

---

## MCP Tool Usage by System

All ticket-system MCP tools are **deferred** — schemas must be loaded via `ToolSearch` before
any tool call. Never assume a ticket tool is callable without first loading its schema.

### GitHub

```
ToolSearch({ query: "select:mcp__github__get_issue", max_results: 1 })
```

Call signature (after schema load):
```
mcp__github__get_issue({
  owner: string,        // repo owner or org
  repo:  string,        // repository name
  issue_number: number
})
```

Returns: `title`, `body`, `labels` (array of `{name}`), `assignees`, `milestone`, `state`,
`number`, `html_url`.

**Subtask detection from body:** scan for `- [ ]` or `- [x]` lines that contain
`github.com/<owner>/<repo>/issues/<N>` links. For each match, call `mcp__github__get_issue`
recursively (max depth 2). Also scan for a "Tasks" or "Checklist" heading followed by
checkbox lists with issue references.

**Comments:** GitHub does not return comments inline from `get_issue`. Load:
```
ToolSearch({ query: "mcp__github", max_results: 15 })
```
If a `list_issue_comments` or `get_issue_comments` tool is available, fetch last 5 comments.
If unavailable, skip and add to `plan.md` assumptions: "GitHub comments not fetched —
no list_issue_comments tool available."

**Fallback if `mcp__github__get_issue` is unavailable:**
```
ToolSearch({ query: "mcp__plugin_engineering_github", max_results: 20 })
```
Authenticate if needed, then use equivalent tool.

**Real-time update tool:**
```
ToolSearch({ query: "select:mcp__github__update_issue", max_results: 1 })
// mcp__github__update_issue({ owner, repo, issue_number, state?, labels? })
// To mark In Progress: add label "in-progress"
// To mark Done: set state: "closed"
```

---

### Linear

```
ToolSearch({ query: "mcp__plugin_engineering_linear", max_results: 20 })
```

If an `authenticate` tool is found, call it first. Then look for tools named like
`get_issue`, `list_issues`, `get_issue_children`, `update_issue`.

**Expected fields on a Linear issue:**
- `id`, `identifier` (e.g. "ENG-123"), `title`, `description` (Markdown)
- `state` (object with `id` and `name`), `priority`, `labels` (array)
- `parent` (object), `children` (array of sub-issues — key field for recursion)
- `comments` (array or paginated), `attachments`

**Subtask fetch:** if `children` is present and non-empty, iterate and fetch each child
by identifier using the same get_issue tool. Depth limit: 2.

**Real-time update:** look for `update_issue` in the discovered tool list. Set the
`stateId` field to the matching state ID:
- Before fetching issues, discover available states via a `list_states` or `get_team` tool
  if available, so you know the correct state IDs for "In Progress" and "Done".
- If state IDs cannot be resolved, skip update and log in `decisions.md`.

**If Linear tools are unavailable:** fall back to `AskUserQuestion` asking user to paste
ticket content, or switch to Plan Derivation Mode. Note in assumptions.

---

### Jira / Atlassian

```
ToolSearch({ query: "mcp__plugin_engineering_atlassian", max_results: 20 })
```

Authenticate if needed. Look for tools like `get_issue`, `search_issues`,
`get_issue_subtasks`, `transition_issue`.

**Expected fields on a Jira issue:**
- `key` (e.g. "ACME-123"), `summary` (= title), `description` (Atlassian Document Format
  or plain text), `issuetype` (Epic | Story | Task | Sub-task | Bug)
- `priority`, `status` (object with `name`), `labels`, `components` (array of `{name}`)
- `subtasks` (array of `{key, summary}`) — direct children; fetch each recursively
- `customfield_10014` (Epic Link) — if this issue is a Story linked to an Epic
- `comment.comments` (array)

**Subtask recursion:** fetch each `subtasks[i].key` via get_issue. Depth limit: 2.
If issue is an Epic: also fetch Stories via search_issues with JQL:
`"Epic Link" = <issue-key> ORDER BY created ASC` (if search tool available).

**Real-time update:** Jira uses workflow **transitions** — you cannot directly write a
state name. Process:
1. Call a `get_transitions` or `list_transitions` tool for the issue (if available).
2. Find the transition ID matching "In Progress" and "Done" by name.
3. Call `transition_issue({ issue_key, transition_id })`.
If transitions cannot be resolved automatically, skip update and note in `decisions.md`:
"Could not auto-transition <ticket-ID> — Jira workflow state not resolvable. Update manually."

**If Atlassian tools are unavailable:** fall back to manual paste or Plan Derivation Mode.

---

### Azure DevOps

```
ToolSearch({
  query: "select:mcp__azure-devops__wit_get_work_item,mcp__azure-devops__wit_get_work_items_batch_by_ids,mcp__azure-devops__wit_update_work_item",
  max_results: 3
})
```

These tools are in the known deferred list — always load via ToolSearch before calling.

**Fetch:**
```
mcp__azure-devops__wit_get_work_item({ id: number })
```

Returns a work item with fields:
- `fields["System.Title"]` — title
- `fields["System.Description"]` — HTML description → strip tags before using
- `fields["Microsoft.VSTS.Common.AcceptanceCriteria"]` — HTML → strip tags
- `fields["System.Tags"]` — semicolon-delimited tags
- `fields["System.State"]` — current state (e.g. "New", "Active", "Resolved", "Closed")
- `relations` — array of relation objects with `rel` and `url`

**Child work items:** find relations where `rel == "System.LinkTypes.Hierarchy-Forward"`.
Extract the work item ID from the URL's last path segment. Batch-fetch:
```
mcp__azure-devops__wit_get_work_items_batch_by_ids({ ids: number[] })
```

**Ordering links:** find relations where `rel == "System.LinkTypes.Dependency-Forward"`.
These are explicit "blocked by" edges — treat as hard ordering in the dependency graph.

**HTML stripping:** replace `<[^>]+>` with space, then decode `&amp;` → `&`,
`&lt;` → `<`, `&gt;` → `>`, `&nbsp;` → ` ` before inserting into plan.md.

**Real-time update:**
```
mcp__azure-devops__wit_update_work_item({
  id: number,
  patch: [{ op: "replace", path: "/fields/System.State", value: "Active" }]
})
```
State values: `"New"` (To Do), `"Active"` (In Progress), `"Resolved"` or `"Closed"` (Done).
Use `"Active"` for In Progress and `"Resolved"` for Done (adjust to the project's process template).

---

## Field Mapping Table

| Source field | Where it lands in `plan.md` | Transformation |
|---|---|---|
| title / summary | `# Plan: <title>` heading + slug | Slugify: lowercase, replace spaces with `-`, strip special chars |
| description | `## Goal` section | Paste verbatim (trimmed). If >500 chars, truncate to first 500 and note "truncated" |
| acceptance criteria | `## Success Criteria` section | Split by newline/bullet, number as `1.`, `2.`, ... |
| labels / components / tags | `## Tech Stack` hints | Filter for known framework keywords (see §Tech Stack Keywords below) |
| priority = Critical/P0 | `## Hard Constraints` | Append: "Priority: Critical — escalate all blockers to user immediately" |
| milestone / sprint / fix-version | `## Hard Constraints` | Append: "Target: <milestone name>" |
| comments (last 5, if fetched) | `## Context from Comments` section | Paste as block quotes with author + date |
| attachments (text/linked docs) | `## Assumptions` | Note: "Referenced attachment: <name> — not fetched" |
| source URL | `## Source Ticket` | Paste full URL for traceability |
| state (closed/done) | Warning via `AskUserQuestion` before proceeding | "This ticket is already marked <state>. Proceed anyway?" |

---

## Tech Stack Keyword Detection

Scan labels, components, tags, and the first 200 chars of description for (case-insensitive):

```
react, next.js, nextjs, vue, angular, svelte,
node, nodejs, express, nestjs, fastify, hapi,
python, django, flask, fastapi,
java, spring, springboot,
go, golang,
rust,
postgresql, postgres, mysql, mariadb, mongodb, redis, dynamodb, sqlite,
docker, kubernetes, k8s, helm, terraform,
graphql, rest, grpc,
typescript, javascript,
aws, azure, gcp,
playwright, cypress, jest, vitest, pytest
```

If ≥1 keywords found: set Tech Stack to the matched keywords joined with ` + `.
If 0 keywords found: mark as "not detected — ask user in Phase 1b".

---

## Subtask Recursion Algorithm

```
FETCH_SUBTASKS(system, root_id, depth=0, max_depth=2, seen_ids={}):
  if root_id in seen_ids: return null   // deduplication
  seen_ids.add(root_id)
  ticket = call_system_mcp(system, root_id)
  children = get_children(system, ticket)   // varies by system (see MCP sections above)
  result = []
  for each child in children:
    child_data = {
      id:           child.id,
      title:        child.title,
      description:  child.description,
      explicit_deps: child.predecessor_ids,  // from ordering links
      source_id:    child.id,
      depth:        depth + 1
    }
    if depth + 1 < max_depth:
      child_data.children = FETCH_SUBTASKS(system, child.id, depth+1, max_depth, seen_ids)
    result.append(child_data)
  return result
```

**Depth limit handling:** if `depth == max_depth` and a fetched item still has children,
do NOT fetch deeper. Append to `plan.md` assumptions:
"Ticket hierarchy truncated at depth 2; <N> deeper items under <child-ID> not fetched. Review manually."

**Deduplication:** if a child ID appears in `seen_ids` (cross-referenced by multiple parents),
skip the duplicate fetch and note in the plan: "T<N> also referenced by T<M>."

---

## Subtask → Wave Mapping

Apply this classification in Phase 2 when the plan came from Ticket Ingestion Mode.
Rules are checked in order — first match wins.

### Classification table

| Class | Signal | Wave treatment |
|---|---|---|
| **Explicit ordering link** | Ticket system predecessor/dependency edge | Place after predecessor's wave (hard edge, overrides all other rules) |
| **Infra / foundation** | Title or body contains: `schema`, `migration`, `install`, `scaffold`, `setup`, `init`, `provision`, `database`, `infra` | Wave 1 |
| **E2E / integration test** | Title contains: `E2E`, `end-to-end`, `integration test`, `smoke test`, `playwright`, `cypress` | Last wave (Wave 3 in default 3-wave structure) |
| **Coarse multi-domain** | Has children at depth+1, OR description spans >1 domain | Promote children to T-IDs; this subtask becomes a wave-group label in `plan.md`. Apply classification rules recursively to children. |
| **Fine-grained single-file** | Title references a specific filename/component/function, OR description is clearly a single-file change | Group by domain into Implementer roles; merge up to 5 fine-grained tasks per role |
| **Independent application layer** | None of the above | Wave 2 parallel |

### Domain keyword table (for grouping Wave 2 tasks into Implementer roles)

| Domain | Keywords in title/description |
|---|---|
| `data-layer` | schema, migration, entity, model, table, ORM, seed, DDL, database, repository |
| `backend-services` | service, business logic, use case, handler, processor, queue, worker |
| `backend-api` | controller, router, endpoint, REST, GraphQL, middleware, guard, DTO, validator |
| `frontend-core` | page, component, UI, React, Next.js, Vue, Angular, layout, hook, store, view |
| `tests` | test, spec, unit test, mock, fixture, stub |
| `infra` | Docker, CI, CD, pipeline, Terraform, Helm, config, env, secret, deploy |

### Parallelism cap

Maximum **8 Implementer roles per wave**. If >8 domain groups would be created, merge the
smallest groups first (fewest tasks). Log each merge in `decisions.md` with rationale.

---

## Source Annotation

Every T-ID derived from a ticket subtask carries a `[source: <ticket-ID>]` annotation in:
- `plan.md` task list
- `dependency-graph.md` task registry
- HTML report (traceability column)
- `DELIVERY-NARRATIVE.md` Plan Drift section (read by Archaeology Agent)

Example:
```
T3. Implement UserService [source: ENG-45]
```

---

## Real-time Ticket Status Updates

When the plan came from Ticket Ingestion Mode, update ticket statuses live as agents
complete work. Load the appropriate update tool via ToolSearch before the first wave starts.

### Pre-execution state snapshot

Before Wave 1 starts, read and record current states of the parent ticket and all
child tickets into `.agent-forge/<slug>/ticket-states.md`:

```
# Ticket State Snapshot — pre-execution
parent: <ticket-ID> — state: <state>
T1 → <child-ticket-ID> — state: <state>
T2 → <child-ticket-ID> — state: <state>
T2.1 → <grandchild-ticket-ID> — state: <state>
...
```

This snapshot is used to revert states on rollback.

### Update trigger points

| Plan event | Child ticket action | Parent ticket action |
|---|---|---|
| Wave W starts | Set all child tickets assigned to wave W → "In Progress" | Set parent → "In Progress" (first wave only) |
| T-ID marked `done` | Set child ticket → "Done" / "Closed" | No change yet |
| T-ID marked `partial` or `blocked` | Leave as "In Progress" | No change |
| All T-IDs across all waves marked `done` | (already updated) | Set parent → "Done" / "Closed" |
| Rollback executed for T-ID | Revert child ticket to pre-execution state from snapshot | Revert parent if all tasks rolled back |

### Update tool per system

| System | Tool | Load command | State values |
|---|---|---|---|
| GitHub | `mcp__github__update_issue` | `ToolSearch({ query: "select:mcp__github__update_issue" })` | In Progress: add label `"in-progress"`; Done: `state: "closed"` |
| Linear | discovered via ToolSearch | `ToolSearch({ query: "mcp__plugin_engineering_linear", max_results: 20 })` — find `update_issue` | Set `stateId` — resolve IDs via list_states before first wave |
| Jira | transition tool via ToolSearch | `ToolSearch({ query: "mcp__plugin_engineering_atlassian", max_results: 20 })` — find `transition_issue` | Resolve transition IDs for "In Progress" and "Done" before first wave |
| Azure DevOps | `mcp__azure-devops__wit_update_work_item` | `ToolSearch({ query: "select:mcp__azure-devops__wit_update_work_item" })` | `System.State`: `"Active"` (In Progress), `"Resolved"` (Done) |

### Graceful degradation

Status sync is **best-effort** — a failed update must never halt execution.

- If an update MCP call fails → log in `decisions.md`: "Status sync failed for <ticket-ID>:
  <error>. Continuing execution." Do NOT stop or roll back.
- If Jira transition IDs cannot be resolved automatically → skip all Jira state updates
  for this session and note in `decisions.md`: "Jira workflow transitions not resolvable —
  update ticket states manually after execution."
- If Linear state IDs cannot be resolved → same skip + log pattern.
- If the ticket system is not connected at update time (tool unavailable) → log and continue.

---

## Fallback Procedures

| Situation | Leader action |
|---|---|
| ToolSearch returns no matching tools for the detected system | `AskUserQuestion`: "I cannot fetch <system> tickets automatically. Please paste the ticket title, description, and subtask list here, or switch to Plan Derivation Mode." |
| Authentication fails | `AskUserQuestion`: "Authentication to <system> failed. Please reconnect in the plugin settings and retry, or paste the ticket content manually." |
| Fetch succeeds but returns empty description | Use title only as goal; enter Plan Derivation Mode with title as the seed prompt. Note in assumptions: "Ticket description empty — goal derived from title only." |
| Child/subtask fetch fails | Skip that child. Note in `plan.md` assumptions: "Child <ID> could not be fetched (<error>)." Continue with partial data. |
| Ticket is already closed / done | Warn via `AskUserQuestion`: "This ticket is already marked <state>. Are you sure you want to execute a plan against it?" Wait for confirmation before continuing. |
| Ticket hierarchy depth > 2 | Truncate; note in assumptions: "Hierarchy truncated at depth 2; <N> deeper items under <ID> not fetched." |
| Deduplication hit (child referenced by multiple parents) | Skip duplicate fetch; note in plan: "T<N> also referenced by T<M>." |
| >8 domain groups in Wave 2 | Merge smallest groups; log each merge in `decisions.md` with rationale. |
| Status update fails at runtime | Log in `decisions.md`, continue execution. Do not halt. |
