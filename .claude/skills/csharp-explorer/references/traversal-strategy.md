# Call Graph Traversal Strategy

---

## BFS Algorithm (file-tool-only)

Full pseudo-code for Phase 5. All state lives in working memory — no scratch files needed.

```
function buildCallerTree(target, intake):
  queue = [{ node: target, depth: 0 }]
  visited = Set()              // "file:line_number" strings
  nodes = []
  edges = []
  test_callers = []
  MAX_NODES = 50

  while queue not empty:
    current = queue.dequeue()

    // Depth gate: still record the node, just don't expand further
    node_id = nodeId(current.node)
    if visited.has(node_id): continue
    visited.add(node_id)
    nodes.push(current.node)

    if current.depth >= intake.depth: continue

    // Run caller Grep patterns
    patterns = callerPatternsFor(current.node.name, current.node.kind)
    for pattern in patterns:
      matches = Grep(pattern, glob="**/*.cs", exclude=[...])
      for match in matches:
        match_id = match.file + ":" + match.line_number
        if visited.has(match_id): continue                  // dedup / cycle
        if isDefinitionLine(match, current.node): continue  // skip own definition
        if isCommentLine(match.matched_line): continue       // skip comments

        if isTestFile(match.file):
          test_callers.push(extractCallerNode(match))
          continue                                           // do NOT enqueue

        if nodes.length >= MAX_NODES:
          return { nodes, edges, test_callers, truncated: true, depth_reached: current.depth }

        caller_context = readCallerContext(match)
        caller_node = extractCallerNode(match, caller_context)

        // Dedup by enclosing method identity, not raw line number
        caller_id = caller_node.namespace + "::" + caller_node.class_name + "::" + caller_node.method_name
        if visited.has(caller_id): continue
        visited.add(caller_id)

        nodes.push(caller_node)
        edges.push({ from: caller_node.id, to: current.node.id })
        queue.enqueue({ node: caller_node, depth: current.depth + 1 })

  return { nodes, edges, test_callers, truncated: false, depth_reached: actual_max_depth_reached }
```

---

## Helper Functions

### `nodeId(node)`
```
return node.namespace + "::" + node.class_name + "::" + node.method_name
```
Using `(namespace, class_name, method_name)` as identity rather than `file:line` ensures partial class parts of the same class are treated as ONE node.

### `readCallerContext(match)`
Read `offset: match.line_number - 8, limit: 25`

### `extractCallerNode(match, context)`
From the 25-line context window, scan upward from the match line to find:
1. **Enclosing method**: nearest line matching `(public|private|protected|internal).*\w+\s*\(` that appears before the match line in the window
2. **Enclosing class**: nearest line matching `class\s+(\w+)` that appears before the enclosing method line
3. **Namespace**: if not found in context window, do a separate Read `offset:0, limit:15` to get the file's namespace declaration

Return:
```
{
  id: nodeId(this),
  class_name, method_name, namespace,
  file, line_number,
  layer,           // from Layer Classification rules
  call_expression  // the matched_line trimmed
}
```

### `isDefinitionLine(match, node)`
```
return match.file == node.file && abs(match.line_number - node.definition_line) <= 2
```

### `isCommentLine(line)`
```
trimmed = line.trim()
return trimmed.startsWith("//") || trimmed.startsWith("*") || trimmed.startsWith("/*")
```

### `isTestFile(file_path)`
```
return file_path matches any of:
  /[/\\]Tests?[/\\]/
  /[/\\]Specs?[/\\]/
  /Test\.cs$/
  /Tests\.cs$/
  /Spec\.cs$/
  /Fixture\.cs$/
  /_tests?\./i
```

---

## Depth Control

| Depth | Use case | Typical node count |
|---|---|---|
| 1 | Quick "who directly calls this?" | 1–10 nodes |
| 2 (default) | Understand the feature flow from entry to target | 5–30 nodes |
| 3 | Trace from HTTP endpoint all the way down | 20–50 nodes |
| 4 | Full system traversal (rarely needed; almost always hits 50-node cap) | likely truncated |

**Test callers are never expanded**: tests calling your service don't reveal architectural dependencies; they reveal test coverage. Record them in `test_callers[]` but don't BFS through them.

---

## Cycle Detection

Three cycle types in C# codebases:

### 1. Recursive methods
When `match.file == target.file && match.enclosing_method == target.method_name`:
- Flag the target as `is_recursive: true`
- Add a self-edge in the report but do NOT enqueue (would loop forever)

### 2. Circular dependencies
When node A is being expanded and we find a caller that is already in `nodes[]`:
- The `visited.has(caller_id)` check catches this
- The edge is NOT added (would create a cycle in the visualization)
- Log as `circular_dependency_detected: true` on the later node

### 3. Partial class parts
Multiple files can contain `partial class OrderService`. These are the SAME class — treat as one node:
- Node identity = `(namespace, class_name, method_name)`, NOT `(file, line_number)`
- When a second partial part is found, add the file to `node.partial_files[]` instead of creating a new node

---

## Merge Algorithm (Phase S)

When merging multiple run JSON files into a unified graph:

```
function mergeRuns(run_reports[]):
  node_map = {}     // nodeId -> merged_node
  edge_map = {}     // "from->to" -> observation_count
  concern_map = {}  // "target::issue_type" -> concern

  for run in run_reports (sorted by timestamp ascending):
    for node in run.caller_tree.nodes + [run.target]:
      id = nodeId(node)
      if id not in node_map:
        node_map[id] = { ...node, first_seen: run.timestamp, last_seen: run.timestamp, run_count: 1 }
      else:
        node_map[id].last_seen = run.timestamp
        node_map[id].run_count += 1
        // Update metadata with most recent values (name, file, line may have changed)
        node_map[id] = { ...node_map[id], ...node, first_seen: node_map[id].first_seen, run_count: node_map[id].run_count }

    for edge in run.caller_tree.edges:
      key = edge.from + "→" + edge.to
      edge_map[key] = (edge_map[key] || 0) + 1

    for concern in run.synthesis.concerns:
      key = run.target.name + "::" + concern.issue_type
      concern_map[key] = { ...concern, target_name: run.target.name, last_seen: run.timestamp }

  merged_nodes = Object.values(node_map)
  merged_edges = Object.entries(edge_map).map(([key, count]) => ({
    from: key.split("→")[0], to: key.split("→")[1], observation_count: count
  }))
  merged_concerns = Object.values(concern_map)

  return { merged_nodes, merged_edges, merged_concerns, runs: run_reports.length }
```

### Staleness in merged graph

After merging, for any node where `stale: true` was flagged during Phase S validation:
- Keep the node in the graph (removing it would lose history)
- Set `node.stale = true` so the HTML report renders it with a visual "stale" indicator
- Do NOT use its `definition_line` for any cache-hit purposes

---

## Method Overload Handling

When multiple Grep matches have the same `method_name` but different line numbers (overloads):
- Create separate nodes for each overload: use `method_name + "_overload_" + i` as the suffix
- Set `node.overload_of = base_method_name` and `node.overload_index = i`
- In the HTML report: display overloads as a grouped node with an expand button
- In BFS: if `intake` specified a generic method name (no parameter signature), expand ALL overloads
