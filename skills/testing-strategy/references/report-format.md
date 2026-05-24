# Report Format Reference

## Full JSON Schema

The `strategy` object injected as `reportData` in the HTML template.

```jsonc
{
  "timestamp": "2026-05-24T14:30:22Z",          // ISO 8601
  "project_name": "econtainer-shop",             // from manifest name or dir name
  "project_shape": "api|web-app|library|microservices|cli|fullstack",
  "intake": {
    "mode": "new-strategy|audit|focused",
    "scope": "whole-project|sub-project|class|function",
    "scope_target": null,                         // null for whole-project; e.g. "OrderService" or "createOrder"
    "scope_path": null,                           // resolved file path, e.g. "src/services/order.service.ts"
    "focus_type": null                            // or "unit|integration|api|ui|load|mocking|bdd"
  },
  "scope_analysis": null,                         // null unless scope is "class" or "function"
  // When populated, scope_analysis shape:
  // {
  //   "target": {
  //     "name": "OrderService.createOrder",
  //     "file": "src/services/order.service.ts",
  //     "layer": "service",                       // "controller"|"service"|"use-case"|"repository"|"utility"|"domain-model"|"cli"|"unknown"
  //     "signature": "async createOrder(dto: CreateOrderDto): Promise<Order>",
  //     "boundary_classification": "domain-core", // "entry-point"|"domain-core"|"adapter"|"shared-utility"|"leaf-node"
  //     "blast_radius": "medium",                 // "low" (≤2 callers)|"medium" (3–7)|"high" (≥8)
  //     "key_insight": "OrderService.createOrder is a domain-core method with 2 external I/O callees..."
  //   },
  //   "callers": [
  //     {
  //       "name": "OrderController.create",
  //       "file": "src/controllers/order.controller.ts",
  //       "layer": "controller",
  //       "call_type": "direct-call",             // "direct-call"|"constructor-injection"|"event-trigger"|"queue-consumer"
  //       "distance": 1                           // 1=direct caller, 2=caller's caller
  //     }
  //   ],
  //   "callees": [
  //     {
  //       "name": "OrderRepository.save",
  //       "file": "src/repositories/order.repository.ts",
  //       "layer": "repository",
  //       "is_external_io": true,
  //       "mock_needed": true,
  //       "mock_strategy": "fake"                 // "stub"|"fake"|"spy"|"mock"|"real"
  //     }
  //   ],
  //   "caller_count": 3,
  //   "callee_count": 4,
  //   "external_io_count": 2,
  //   "mock_needed_count": 2,
  //   "recommended_test_entry_point": "Unit test createOrder() directly, mocking OrderRepository and StripeClient"
  // }
  "stack": {
    "language": "TypeScript",
    "framework": "Express",
    "test_tools": ["Jest", "Supertest"],
    "ci_tool": "GitHub Actions",
    "test_file_count": 14,
    "has_existing_tests": true
  },
  "testing_model": "pyramid|trophy|honeycomb",
  "testing_model_rationale": "One-sentence explanation tied to code analysis",
  "test_types": [
    {
      "type": "unit|integration|api|ui-e2e|load|performance|automation|bdd",
      "label": "Unit Tests",                      // display label
      "recommendation": "essential|recommended|optional|skip",
      "rationale": "Project-specific reason referencing actual files/layers",
      "current_state": "none|minimal|adequate|good",
      "current_state_issues": ["issue 1", "issue 2"],
      "recommended_tools": ["Jest", "Vitest"],
      "example_snippet": "// language-specific code example string",
      "coverage_target": "70% line coverage",
      "bdd_scenario": null                        // only for BDD type — Gherkin string
    }
  ],
  "mocking": {
    "school": "london|detroit|mixed",
    "school_rationale": "One-sentence reason",
    "per_type": [
      {
        "test_type": "unit",
        "mock": ["DB/ORM (mongoose)", "HTTP clients (axios)", "System clock"],
        "dont_mock": ["PricingService (real)", "value objects"],
        "key_reason": "Isolate behavior without coupling to implementation"
      }
    ],
    "recommended_tools": ["jest.fn()", "jest.useFakeTimers()", "msw"],
    "anti_patterns": [
      "Mocking internal domain services",
      "Using any() matchers everywhere"
    ]
  },
  "overlap_analysis": {
    "has_overlaps": true,
    "cross_layer_count": 2,                   // number of cross-layer overlap candidates
    "intra_type_count": 3,                    // number of within-type duplicate groups
    "candidates": [                           // cross-layer overlaps
      {
        "behavior": "Order creation validation",
        "covered_by": {
          "unit": true,
          "integration": true,
          "api": false,
          "ui": false,
          "automation": false
        },
        "recommended_owner": "integration",
        "reason": "Logic is a pass-through service — integration test covers end-to-end without needing isolated unit"
      }
    ],
    "intra_type_overlaps": [                  // within-type duplicates
      {
        "test_type": "unit",                  // "unit"|"integration"|"api"|"e2e"|"automation"|"bdd"
        "behavior": "validateOrder() happy path",
        "test_files": ["tests/order.test.ts", "tests/checkout.test.ts"],
        "duplication_type": "identical",      // "identical"|"near-identical"|"subset"
        "recommendation": "Consolidate into order.test.ts — delete duplicate in checkout.test.ts"
      },
      {
        "test_type": "e2e",
        "behavior": "User login journey",
        "test_files": ["e2e/auth.spec.ts", "e2e/checkout.spec.ts", "e2e/profile.spec.ts"],
        "duplication_type": "near-identical",
        "recommendation": "Extract login to a shared beforeEach fixture — only test it explicitly in auth.spec.ts"
      }
    ]
  },
  "coverage": {
    "overall_estimate": "0-20%|20-40%|40-60%|60-80%|80%+",
    "targets": {
      "unit": "70% line",
      "integration": "All endpoints covered",
      "overall": "60-70%"
    },
    "gaps": [
      { "area": "PaymentService", "file": "src/services/payment.ts", "has_test": false }
    ]
  },
  "ci_plan": {
    "current_ci": "GitHub Actions",
    "current_has_tests": true,
    "stages": [
      { "name": "Fast Unit", "trigger": "every commit", "duration": "< 30s", "color": "green" },
      { "name": "Integration", "trigger": "every PR", "duration": "< 3 min", "color": "blue" },
      { "name": "E2E", "trigger": "merge to main", "duration": "< 10 min", "color": "yellow" },
      { "name": "Deploy", "trigger": "after E2E", "duration": "varies", "color": "purple" }
    ],
    "parallelism_tip": "Run unit tests in parallel workers; isolate integration tests per worker with separate DB schemas"
  },
  "priority_matrix": [
    {
      "rank": 1,
      "title": "Add integration tests for OrderService",
      "description": "OrderService has 12 branches and no integration coverage.",
      "example": "// code example",
      "effort": "medium",
      "impact": "high",
      "quadrant": "quick-win",
      "priority": "P0"
    }
  ],
  "action_items": [
    {
      "priority": "P0|P1|P2",
      "title": "Short title",
      "description": "What to do and why",
      "example": "// code snippet or config example"
    }
  ],
  "existing_quality": {
    "rating": "good|fair|poor",
    "issues": ["Heavy mock setup in order.test.js", "test1, test2 naming"],
    "positives": ["Good AAA structure in product.test.js"]
  }
}
```

---

## Placeholder Tokens

| Token | Type | Source |
|---|---|---|
| `{{PROJECT_NAME}}` | string | `strategy.project_name` |
| `{{TIMESTAMP}}` | string | `strategy.timestamp` (formatted) |
| `{{MODE_LABEL}}` | string | "New Strategy" / "Audit" / "Focused" |
| `{{PROJECT_SHAPE}}` | string | `strategy.project_shape` |
| `{{SCOPE_TARGET}}` | string | `strategy.intake.scope_target` or "" (whole-project) |
| `{{TESTING_MODEL}}` | string | `strategy.testing_model` |
| `{{STACK_LANGUAGE}}` | string | `strategy.stack.language` |
| `{{STACK_FRAMEWORK}}` | string | `strategy.stack.framework` |
| `{{TEST_FILE_COUNT}}` | number | `strategy.stack.test_file_count` |
| `{{OVERLAP_COUNT}}` | number | `strategy.overlap_analysis.cross_layer_count + strategy.overlap_analysis.intra_type_count` |
| `{{REPORT_JSON}}` | JSON | Full `strategy` object — injected into `<script>` block |

All string tokens must be HTML-escaped before injection to prevent XSS.

---

## Testing Model SVG Spec

Draw inline SVG for each model. All use dark theme colors.

### Pyramid
```
Layer proportions (height %): Unit=50%, Integration=30%, E2E=20%
Colors: Unit=#3fb950 (green), Integration=#58a6ff (blue), E2E=#d29922 (yellow)
Labels: Unit Tests | Integration Tests | E2E Tests
Active layer (thickest) highlighted with 1px solid border glow
```

### Trophy
```
Layer order (top→bottom): E2E | Integration (widest) | Static | Unit
Proportions: E2E=15%, Integration=50%, Static=20%, Unit=15%
Colors: E2E=#d29922, Integration=#58a6ff, Static=#bc8cff, Unit=#3fb950
```

### Honeycomb
```
Instead of pyramid: show 3 hexagons side by side (Service A, B, C)
Each hexagon contains: 70% integration, 20% unit, 10% E2E label
Connected by dotted lines representing service contracts
```

---

## Recommendation Badge Colors

| Value | Color | CSS class |
|---|---|---|
| Essential | `#3fb950` (green) | `badge-essential` |
| Recommended | `#58a6ff` (blue) | `badge-recommended` |
| Optional | `#d29922` (yellow) | `badge-optional` |
| Skip | `#8b949e` (muted) | `badge-skip` |

---

## Priority Matrix Layout

2×2 grid — x-axis = effort (Low→High), y-axis = impact (Low→High).

| Quadrant | Position | Label | Priority |
|---|---|---|---|
| Upper-left | High impact, Low effort | Quick Wins ⚡ | P0 |
| Upper-right | High impact, High effort | Strategic 🎯 | P1 |
| Lower-left | Low impact, Low effort | Fill-in 📋 | P2 |
| Lower-right | Low impact, High effort | Avoid ❌ | — |

Each action item is a dot plotted on the grid. Click dot → shows title + description popover.

---

## CI Pipeline Visualization

Horizontal flex row, left to right:
```
[Fast Unit] ──▶ [Integration] ──▶ [E2E] ──▶ [Deploy]
  green            blue            yellow     purple
  < 30s            < 3 min         < 10 min   varies
  every commit     every PR        on merge
```

Each box: stage name, trigger, estimated duration.
Arrow between boxes: right-pointing arrow `▶`.
Color matches stage color from `ci_plan.stages[].color`.

---

## Section Collapsed/Open Defaults

| Section | Default state |
|---|---|
| Summary Cards | Always visible (not collapsible) |
| Scope Impact Map | Open — only rendered when `scope_analysis != null` |
| Testing Model | Open |
| Test Types | Open (individual cards collapsible) |
| Mocking per Test Type | Open — never auto-collapsed |
| Mocking Deep-Dive | Open |
| Test Overlap Analysis | Open (only rendered if `has_existing_tests`) |
| Coverage Analysis | Open |
| CI/CD Integration | Collapsed |
| Priority Matrix | Open |
| Action Items | Open |
