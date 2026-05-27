# Report Format

JSON schema for the per-run `report` object written by Phase 7.

---

## Full Schema

```jsonc
{
  // Meta
  "schema_version": "1.0",
  "timestamp": "2026-05-26T14:30:22Z",       // ISO 8601 UTC
  "project_name": "MyApp",                    // base name of working directory
  "project_slug": "myapp",                    // lowercase, hyphens

  // Target
  "target": {
    "name": "OrderService.CreateOrder",
    "class_name": "OrderService",
    "method_name": "CreateOrder",             // null if target is a class
    "kind": "method",                         // "class" | "method" | "interface"
    "file": "src/Services/OrderService.cs",
    "definition_line": 47,
    "namespace": "MyApp.Services",
    "layer": "service",
    "boundary_type": "domain-core",
    "modifiers": ["public", "async"],
    "return_type": "Task<Order>",
    "parameters": [
      { "type": "CreateOrderDto", "name": "dto" }
    ],
    "attributes": ["[Authorize]"],
    "di_dependencies": [
      { "interface_type": "IOrderRepository", "param_name": "_orderRepository", "lifetime": "scoped" },
      { "interface_type": "IPaymentGateway",  "param_name": "_paymentGateway",  "lifetime": "transient" }
    ],
    "cache_hit": false
  },

  // Intake parameters that produced this run
  "intake": {
    "direction": "both",          // "callers" | "callees" | "both"
    "depth": 2,
    "namespace_filter": null
  },

  // Definition body
  "definition": {
    "body_preview": "...",        // first 60 lines as a single string
    "body_full": "...",           // full body or null if truncated
    "line_start": 47,
    "line_end": 89,               // null if truncated
    "truncated": false
  },

  // Callees (outgoing calls from the target)
  "callees": [
    {
      "receiver": "_orderRepository",
      "receiver_type": "IOrderRepository",
      "method_name": "SaveAsync",
      "file": "src/Repositories/OrderRepository.cs",
      "definition_line": 23,
      "is_external_io": true,
      "io_category": "database",    // "database"|"http"|"messaging"|"cache"|"storage"|"email"|"logging"|"external-sdk"
      "is_async": true,
      "is_internal": true,
      "is_static": false,
      "raw_line": "    await _orderRepository.SaveAsync(order);"
    }
  ],

  // Caller tree (BFS result)
  "caller_tree": {
    "nodes": [
      {
        "id": "MyApp.Api.Controllers::OrderController::Post",
        "class_name": "OrderController",
        "method_name": "Post",
        "namespace": "MyApp.Api.Controllers",
        "file": "src/Controllers/OrderController.cs",
        "line_number": 34,
        "layer": "controller",
        "depth": 1,
        "call_expression": "await _orderService.CreateOrder(dto);",
        "overload_of": null,
        "overload_index": null
      }
    ],
    "edges": [
      {
        "from": "MyApp.Api.Controllers::OrderController::Post",
        "to": "MyApp.Services::OrderService::CreateOrder"
      }
    ],
    "depth_reached": 2,
    "truncated": false,
    "total_caller_count": 4,
    "test_callers": [
      {
        "class_name": "OrderServiceTests",
        "method_name": "CreateOrder_ValidDto_ReturnsOrder",
        "file": "tests/Services/OrderServiceTests.cs",
        "line_number": 58
      }
    ],
    "test_caller_count": 2
  },

  // Synthesis
  "synthesis": {
    "target_summary": "Creates a new order from a DTO, persists it via the repository, and initiates payment via the payment gateway. Returns the created Order entity.",
    "layer": "service",
    "boundary_type": "domain-core",
    "key_insight": "Core business logic node with 4 callers and 2 external I/O dependencies",
    "async_issues": [
      {
        "issue_type": "async_void",
        "description": "Method is declared async void — exceptions will not propagate to callers",
        "offending_line": "public async void ProcessBackground()",
        "recommendation": "Change return type to async Task",
        "severity": "warning"
      }
    ],
    "di_issues": [
      {
        "issue_type": "lifetime_mismatch",
        "description": "OrderService is registered as Singleton but depends on IOrderRepository which is Scoped",
        "severity": "error"
      }
    ],
    "interface_implementations": [
      { "class_name": "OrderService", "file": "src/Services/OrderService.cs", "line": 12 }
    ],
    "partial_parts": [],
    "concerns": [
      {
        "issue_type": "lifetime_mismatch",
        "description": "...",
        "severity": "error"
      }
    ]
  },

  // Aggregated stats
  "stats": {
    "caller_count": 4,
    "test_caller_count": 2,
    "callee_count": 3,
    "external_io_count": 2,
    "async_callee_count": 2,
    "partial_class_parts": 0,
    "interface_implementations": 1,
    "cache_hit": false
  }
}
```

---

## Placeholder Token Table

Used in `assets/report-template.html`. All tokens use `{{TOKEN}}` syntax.

| Token | Source path |
|---|---|
| `{{PROJECT_NAME}}` | `report.project_name` |
| `{{TARGET_NAME}}` | `report.target.name` |
| `{{TARGET_KIND}}` | `report.target.kind` |
| `{{TARGET_FILE}}` | `report.target.file` |
| `{{TARGET_LINE}}` | `report.target.definition_line` |
| `{{NAMESPACE}}` | `report.target.namespace` |
| `{{LAYER}}` | `report.target.layer` |
| `{{BOUNDARY_TYPE}}` | `report.target.boundary_type` |
| `{{CALLER_COUNT}}` | `report.stats.caller_count` |
| `{{CALLEE_COUNT}}` | `report.stats.callee_count` |
| `{{EXTERNAL_IO_COUNT}}` | `report.stats.external_io_count` |
| `{{CONCERN_COUNT}}` | `report.synthesis.concerns.length` |
| `{{KEY_INSIGHT}}` | `report.synthesis.key_insight` |
| `{{TIMESTAMP}}` | `report.timestamp` formatted as `YYYY-MM-DD HH:mm UTC` |
| `{{REPORT_JSON}}` | Full serialized `report` object — injected into `<script>` block, must NOT be HTML-escaped |

**v0.1.2 note**: The template no longer uses `{{PLACEHOLDER}}` token injection. All placeholders above are now read dynamically from `data.json` via `fetch()`. Phase S writes `data.json` and copies the template as-is — no substitution step required.

---

**Strip rule (applied when building data.json for the report server)**:
- Per node: `body_full` deleted; `body_preview` truncated to 400 chars
- Per callee: `raw_line` deleted
- Original per-run `.json` store files are never modified — full data always available there

---

## Merged Report Schema (Phase S output)

When Phase S merges multiple run files, it builds a `merged` object:

```jsonc
{
  "schema_version": "1.0-merged",
  "generated_at": "2026-05-26T15:00:00Z",
  "project_name": "MyApp",
  "project_slug": "myapp",

  "runs": [
    {
      "timestamp": "2026-05-24T10:00:00Z",
      "target_name": "OrderService.CreateOrder",
      "file": "20260524-100000-orderservice-createorder.json"
    }
  ],

  "nodes": [
    {
      "id": "MyApp.Services::OrderService::CreateOrder",
      "class_name": "OrderService",
      "method_name": "CreateOrder",
      "namespace": "MyApp.Services",
      "file": "src/Services/OrderService.cs",
      "layer": "service",
      "first_seen": "2026-05-24T10:00:00Z",
      "last_seen": "2026-05-26T14:30:00Z",
      "run_count": 3,
      "stale": false
    }
  ],

  "edges": [
    {
      "from": "MyApp.Api.Controllers::OrderController::Post",
      "to": "MyApp.Services::OrderService::CreateOrder",
      "observation_count": 2
    }
  ],

  "concerns": [
    {
      "target_name": "OrderService.CreateOrder",
      "issue_type": "lifetime_mismatch",
      "description": "...",
      "severity": "error",
      "last_seen": "2026-05-26T14:30:00Z"
    }
  ],

  "di_map": [
    {
      "interface_type": "IOrderRepository",
      "implementation": "OrderRepository",
      "lifetime": "scoped",
      "registration_file": "Program.cs",
      "registration_line": 14
    }
  ],

  "timeline_stats": {
    "run_count": 3,
    "date_range_start": "2026-05-24T10:00:00Z",
    "date_range_end": "2026-05-26T14:30:00Z",
    "total_unique_nodes": 12,
    "total_unique_edges": 15,
    "total_concerns": 1,
    "stale_nodes": 0
  }
}
```
