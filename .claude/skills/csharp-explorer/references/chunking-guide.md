# Chunking Guide — Reading Large C# Files Efficiently

The golden rule: **Grep first, Read second.** Never open a file from line 1 to find something you can locate with a pattern search.

---

## Core Principle

```
1. Grep(pattern, file)  →  get line_number
2. Read(file, offset: line_number - 1, limit: N)  →  get exactly what you need
```

The `Read` tool uses 0-based `offset` and line-count `limit`. A line at position L (1-based) maps to `offset = L - 1`.

---

## Offset / Limit Reference Table

| Goal | offset | limit | Notes |
|---|---|---|---|
| Confirm a definition keyword | `line - 3` | `8` | ±3 lines around the match |
| Cache validation (Phase 0/2) | `line - 1` | `3` | Just enough to verify the line |
| Read a small method (< 30 lines) | `line - 1` | `50` | Covers signature + body + closing `}` |
| Read a medium method (30–80 lines) | `line - 1` | `100` | Buffer for verbose C# patterns |
| Read a large method body | `line - 1` | `200` | Use brace-depth counting to find true end |
| Read caller context | `line - 8` | `25` | Get enclosing method signature + call site |
| Read class header + fields | `line - 1` | `40` | Signature, base types, ctor, field declarations |
| Namespace declaration | `0` | `15` | Always at the top of the file |
| Using directives scan | `0` | `30` | Imports appear before namespace in some styles |
| DI registration scan (Program.cs) | `0` | `200` | Usually small files; read most of it |

---

## Brace-Depth Body Extraction

Use when method/class size is unknown.

```
function extractBodyRange(file, start_line):
  depth = 0
  body_started = false
  current_line = start_line
  total_read = 0
  MAX_LINES = 600

  while total_read < MAX_LINES:
    window = Read(file, offset: current_line - 1, limit: 100)
    for each line in window:
      clean = stripCommentsAndStrings(line)
      opens = count('{', clean)
      closes = count('}', clean)

      if not body_started and opens > 0:
        body_started = true

      if body_started:
        depth += opens - closes
        if depth <= 0:
          return { end_line: current_line + window.indexOf(line), truncated: false }

      current_line += 1
      total_read += 1

  return { end_line: start_line + MAX_LINES, truncated: true }
```

### String and Comment Exclusion for Brace Counting

Before counting braces in a line:

1. Remove `//` line comments: strip everything from `//` to end of line
2. Remove `/* */` block comments: track a `in_block_comment` toggle across lines
3. Remove string literals: replace `"..."` content with empty (handle `\"` escapes and `@"..."` verbatim strings)
4. Remove character literals: replace `'{'` and `'}'` with empty

Simple approximation sufficient for 99% of C# code:
```
line = regex_replace(line, /\/\/.*$/, "")           // line comments
line = regex_replace(line, /"(?:[^"\\]|\\.)*"/, "") // string literals
line = regex_replace(line, /'[^']*'/, "")           // char literals
```

Note: verbatim strings `@"..."` spanning multiple lines will confuse simple brace counting. If the target file uses them heavily (API response literals, SQL strings), treat truncation conservatively and accept `truncated: true` at 600 lines.

---

## Large File Strategy (> 1000 lines)

For files over 1000 lines, build an in-memory "table of contents" before reading any body:

```
1. Grep(pattern="(public|private|protected|internal).*\(", file=target_file)
   → collect all (line_number, matched_line) pairs

2. Build method_toc[] from these matches
   → sorted by line_number
   → filter out noise: lines inside string literals or comments (heuristic: if line contains `"` before the keyword, skip)

3. For any specific method needed:
   → look up line_number in method_toc
   → Read(offset: line - 1, limit: 120) for that method
```

This avoids reading the entire file. The ToC Grep is a single fast call.

---

## File Type Size Guide

| File type | Typical lines | Read strategy |
|---|---|---|
| Controller action | 10–40 | Single Read `limit: 60` |
| Controller class | 50–200 | Read constructor + target method only |
| Service method | 20–80 | Single Read `limit: 100` |
| Service class | 100–500 | Read constructor for DI + target method only |
| Repository method | 10–50 | Single Read `limit: 80` |
| Repository class | 100–400 | Read target method only |
| Domain entity | 50–300 | Full Read if ≤ 300 lines; otherwise ToC approach |
| DbContext | 200–1000 | Grep for `DbSet<` and `OnModelCreating` line numbers; read those sections only |
| MediatR Handler | 20–60 | Single Read `limit: 80` (Handle method is usually short) |
| Generated migration | 50–5000 | **Skip entirely** — exclude via Glob pattern |
| Auto-generated (`*.g.cs`) | any | **Skip entirely** |
| `Program.cs` (minimal API) | 20–150 | Full Read |
| `Startup.cs` (classic) | 80–300 | Read `ConfigureServices` section only |

---

## Partial Class Strategy

When target is a partial class spread across multiple files:

```
1. Glob("**/<ClassName>.*.cs")  → may find OrderService.Queries.cs, OrderService.Commands.cs
2. Also Grep("partial\s+class\s+<ClassName>", glob="**/*.cs")
   → collect all file paths
3. For each partial file:
   → Read offset:0, limit:40 to get that part's namespace + field declarations
   → Run method ToC Grep to catalog methods in that part
4. Merge all parts into one logical class view:
   → combined di_dependencies[] (from all constructors found)
   → combined method list (for callee resolution)
```

---

## Common Pitfalls

**Property bodies vs. method bodies**: Properties with `{ get; set; }` on one line have depth 0 after parsing — don't mistake the property `{` for the start of a method body. The brace-depth counter only triggers after a method signature is confirmed.

**Expression-bodied members**: `public string Name => _name;` has no braces. Line_end == definition_line for these.

**Lambda closures**: Bodies of lambdas inside a method contain their own `{` and `}`. The brace-depth algorithm handles these correctly as they add then subtract from depth.

**`switch` expressions** (C# 8+): `switch { ... }` uses `{` `}` — these are counted but correctly balanced.
