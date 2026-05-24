# Test Types Reference

Each section covers: what to test, what NOT to test, boundaries, tools by stack,
patterns, and red flags.

---

## Unit Tests

**What:** Pure functions, business rules, domain logic, algorithms, transformations,
validators, state machines, data calculations.

**Not what:**
- Methods that only call `repository.save(entity)` — no logic
- Framework initialization code
- DTO/model constructors with no validation
- Methods that are pure delegation chains

**Boundaries:** No I/O allowed. No network, no database, no file system, no real clock.
Replace all external dependencies with fakes or stubs.

**Tools by stack:**

| Stack | Primary | Assertion | Mocking |
|---|---|---|---|
| Node.js / TypeScript | Jest, Vitest | jest/expect, chai | jest.fn(), sinon |
| Python | pytest, unittest | pytest assert, unittest.TestCase | unittest.mock, pytest-mock |
| .NET | xUnit, NUnit, MSTest | FluentAssertions, Shouldly | NSubstitute, Moq |
| Go | testing package | testify/assert | gomock, testify/mock |
| Java / Kotlin | JUnit 5, TestNG | AssertJ, Hamcrest | Mockito, MockK |
| Ruby | RSpec, minitest | RSpec matchers | RSpec mocks |
| PHP | PHPUnit | PHPUnit assertions | Mockery |

**Pattern (AAA):**
```typescript
// TypeScript example — PricingService
describe('PricingService', () => {
  it('applyDiscount_withVolumeOver10_applies15PctDiscount', () => {
    // Arrange
    const pricing = new PricingService();
    const order = { unitPrice: 100, quantity: 12 };

    // Act
    const total = pricing.calculateTotal(order);

    // Assert
    expect(total).toBe(1020); // 100 * 12 * 0.85
  });
});
```

**Red flags:**
- Setup block is longer than the test body
- Mocking internal domain services (e.g., mocking `OrderService` when testing `OrderService`)
- Tests that pass even when the assertion is removed
- Single test file with 200+ tests covering unrelated things

---

## Integration Tests

**What:** Multiple real components wired together. Test that the layers work
correctly when connected — HTTP handler → service → repository → real database.

**Not what:**
- End-to-end user journeys (that's E2E)
- Testing a single pure function (that's unit)

**Boundaries:** Real database (via TestContainers or in-memory where semantically
equivalent), real DI wiring, real middleware. Mock only **out-of-process external services**
(third-party HTTP APIs, email senders, payment gateways).

**Never use in-memory SQLite as a stand-in for PostgreSQL/MySQL** — different
query planner, different constraint behavior, different RETURNING syntax.
Use the real engine in a Docker container.

**Tools by stack:**

| Stack | HTTP testing | DB test container | Factory |
|---|---|---|---|
| Node.js | Supertest | @testcontainers/postgresql | factory-bot |
| Python | pytest + httpx AsyncClient | testcontainers-python | factory-boy |
| .NET | WebApplicationFactory<Program> | Testcontainers.PostgreSql | AutoFixture |
| Go | httptest.NewRecorder | testcontainers-go | go-factory |
| Java | MockMvc / RestAssured | Testcontainers | fixtures |

**Pattern (.NET WebApplicationFactory):**
```csharp
public class OrdersIntegrationTest : IClassFixture<WebApplicationFactory<Program>> {
    private readonly HttpClient _client;

    public OrdersIntegrationTest(WebApplicationFactory<Program> factory) {
        _client = factory.WithWebHostBuilder(builder => {
            builder.ConfigureServices(services => {
                // Replace real Stripe with a fake
                services.AddSingleton<IPaymentGateway, FakePaymentGateway>();
            });
        }).CreateClient();
    }

    [Fact]
    public async Task PostOrder_ValidRequest_Returns201AndPersists() {
        var response = await _client.PostAsJsonAsync("/orders", new { /* ... */ });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    }
}
```

**Red flags:**
- Integration tests that mock the database (defeats the purpose)
- Using SQLite when prod uses PostgreSQL
- Sharing database state between tests (causes flakiness — use transactions or separate schemas)
- Integration test that takes > 30 seconds (design problem, not a testing problem)

---

## API Tests

**What:** The HTTP contract of your API — correct status codes, response body shape,
authentication behavior, error responses, header values.

**Not what:** Business logic (unit test), database persistence (integration test).
API tests verify the *surface* of your API.

**Status code matrix to always cover:**

| Status | Scenario |
|---|---|
| 200 / 201 | Happy path |
| 400 | Malformed request body |
| 401 | Missing or invalid auth token |
| 403 | Valid token but wrong role/scope |
| 404 | Resource not found |
| 409 | Conflict (duplicate creation) |
| 422 | Validation error (well-formed but semantically invalid) |
| 500 | Unhandled error returns structured error body (not HTML stack trace) |

**Auth flow tests:**
- No token → 401
- Expired token → 401
- Valid token, wrong scope → 403
- Valid token, correct scope → 200

**Schema validation:** use JSON Schema or OpenAPI spec to validate the response
shape, not just spot-check one field.

**Pattern (Node.js Supertest):**
```typescript
describe('POST /orders', () => {
  it('returns 422 when quantity is negative', async () => {
    const res = await request(app)
      .post('/orders')
      .set('Authorization', `Bearer ${validToken}`)
      .send({ items: [{ sku: 'CTR-20', quantity: -1 }] });

    expect(res.status).toBe(422);
    expect(res.body).toMatchObject({
      error: 'VALIDATION_ERROR',
      fields: [{ path: 'items[0].quantity', message: expect.any(String) }]
    });
  });
});
```

**Red flags:**
- Testing only the happy path
- Not testing auth/authorization paths
- Using real third-party APIs in API tests (slow, flaky, costs money)
- No schema assertion — only checking `status === 200`

---

## UI / E2E Tests

**What:** Critical user journeys end-to-end through the real UI.
Use sparingly — cover the *most important* flows, not every page.

**Recommended journeys to cover (pick 3–5):**
1. Authentication: sign up, log in, log out
2. Core transaction: the action the user pays for
3. Error recovery: what happens when something fails
4. Role-based access: admin vs regular user sees different UI

**Not what:**
- Testing every UI component (use component tests for that)
- Duplicating logic already covered by unit/integration tests
- Testing third-party widgets

**Page Object Model — always use:**
```typescript
// ✅ Good — behavior-named methods hide selectors
class CartPage {
  async addItem(sku: string) { await this.page.click(`[data-sku="${sku}"] .add-btn`); }
  async getItemCount() { return this.page.locator('.cart-count').textContent(); }
}

// ❌ Bad — raw selectors in tests break on every UI refactor
await page.click('#add-to-cart-btn');
```

**Flakiness root causes and fixes:**

| Cause | Fix |
|---|---|
| Timing — waiting for animation | `waitForSelector`, not `sleep` |
| Test pollution — shared login session | Create fresh user per test |
| Network dependency | Mock 3rd-party APIs at HTTP boundary (WireMock, MSW) |
| Hard-coded test data | Use test-specific seed data, not shared fixtures |
| Selector changes | Page Object Model + `data-testid` attributes |

**Tools:** Playwright (preferred — auto-waiting, trace viewer, component testing),
Cypress (good DX, browser-only), Selenium (legacy).

**Red flags:**
- `await page.waitForTimeout(3000)` — always a smell
- E2E tests covering the same journey as 3 other test files
- E2E tests for every page in the app
- Tests that depend on production data

---

## Load Tests

**What:** Find the throughput ceiling and latency behavior under concurrent load.
Not "does it work?" — that's functional testing. Load tests answer:
"How many users can it handle before latency degrades?"

**Key metrics to collect:**
- **p50 / p95 / p99 latency** — median and tail behavior
- **RPS** — requests per second (throughput ceiling)
- **Error rate** — % of requests returning 5xx under load
- **Time to first byte (TTFB)** — for user-facing endpoints

**Realistic load script (k6):**
```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // ramp up
    { duration: '2m',  target: 50 },   // sustained load
    { duration: '30s', target: 0  },   // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests under 500ms
    http_req_failed:   ['rate<0.01'],   // < 1% error rate
  },
};

export default function () {
  const res = http.get('http://api:3000/products?page=1');
  check(res, { 'status is 200': (r) => r.status === 200 });
}
```

**Baseline first:** run load test before and after changes to detect regressions.
Store baseline results in the repo.

**Where to run:** NOT in the main CI pipeline. Use a separate scheduled job
(weekly or nightly) or a pre-release gate.

**Tools comparison:**

| Tool | Scripting | Best for | CI integration |
|---|---|---|---|
| k6 | JavaScript-like | Developer-friendly, CI pipelines | Excellent |
| Locust | Python | Programmable scenarios, real HTTP | Good |
| Artillery | YAML / JS | Quick setup, serverless | Good |
| JMeter | GUI / XML | Legacy teams, complex scenarios | Moderate |
| Gatling | Scala / Java | High-throughput simulation | Good |

---

## Performance Tests

**What:** Measure the latency and throughput of a *specific operation* — not the
full system under load. Use benchmarks to detect regression in hot code paths.

**Different from load testing:** Load = many users hitting the system.
Performance = one operation, measured precisely.

**Profile before optimizing.** Never write a performance test for code you
haven't profiled. You need data, not guesses.

**Benchmark tools:**

| Stack | Tool | Example |
|---|---|---|
| .NET | BenchmarkDotNet | `[Benchmark] public string Serialize() { ... }` |
| Go | testing package | `go test -bench=. -benchmem ./...` |
| Python | pytest-benchmark | `def test_sort(benchmark): benchmark(my_sort, data)` |
| Java | JMH | `@Benchmark public void measureSort() { ... }` |
| Node.js | tinybench, benchmark.js | `suite.add('fn', () => { ... })` |
| Browser | performance.mark / PerformanceObserver | Web Vitals API |

**p99 matters:** if p99 is 5s and p50 is 20ms, you have a tail latency problem.
Averages hide it entirely.

---

## Automation & CI Integration

**What:** How to organize tests in the CI pipeline to maximize feedback speed
without sacrificing coverage.

**Pipeline structure (speed-optimized):**

```
On every commit:
  └── Fast unit tests (< 30s)
         ↓ pass
On every PR:
  └── Integration + API tests (< 3 min)
         ↓ pass
On merge to main:
  └── E2E / automation (< 10 min)
         ↓ pass
  └── Deploy to staging
Scheduled (nightly or weekly):
  └── Load tests
  └── Visual regression snapshots
```

**Parallelism:**
- Unit tests: always run in parallel (no shared state)
- Integration tests: isolate per worker (separate DB schema per worker process, or
  use transactions that roll back after each test)
- E2E tests: shard across browsers or test files using Playwright `--shard`

**Flaky test quarantine:** track flaky tests in a separate `@flaky` tag/suite.
Do not fail CI for known-flaky tests — fix them or delete them.
A flaky test that occasionally passes is worse than no test: it builds false confidence.

**Coverage gate:** enforce that coverage must not *decrease* by more than 2% per PR.
Don't enforce a hard minimum — that breeds meaningless tests written just to hit
the number.

**Test reporting:** output JUnit XML format — supported universally across GitHub
Actions, GitLab CI, Azure Pipelines, CircleCI for test results visualization.

---

## BDD (Behavior-Driven Development)

**What:** A collaboration technique where tests are written in natural language
(Gherkin: `Given / When / Then`) so non-technical stakeholders — PMs, QA, BAs —
can read, write, and verify acceptance criteria.

**BDD is NOT a test level.** It's a style that can drive any layer:
unit tests, integration tests, or API tests. The Gherkin scenario is the
outer shell; underneath it runs whatever test code is appropriate.

**When to use BDD:**
- Product has business-readable acceptance criteria that stakeholders own
- Domain-rich workflows where the "why" of the behavior matters more than the "how"
- QA team writes scenarios before developers write code (Specification by Example)
- Regulatory/compliance contexts where human-readable test evidence is required

**When NOT to use BDD:**
- Internal libraries with no external stakeholders
- Pure technical services where no non-dev reads the tests
- Small teams where the collaboration overhead exceeds the benefit
- Projects where Gherkin would be written by developers only (just use unit tests)

**Gherkin example (ecommerce checkout):**
```gherkin
Feature: Container order checkout
  As a buyer
  I want to complete checkout for a container order
  So that my order is confirmed and I receive a receipt

  Scenario: Successful checkout with valid payment
    Given I have 1 x "20ft Standard Container" in my cart
    And I am logged in as "buyer@example.com"
    When I complete checkout with a valid credit card
    Then my order status should be "confirmed"
    And I should receive a confirmation email

  Scenario: Checkout fails when cart is empty
    Given my cart is empty
    When I attempt to checkout
    Then I should see "Your cart is empty"
    And no order should be created
```

**Tools by stack:**

| Stack | Tool | Notes |
|---|---|---|
| .NET | SpecFlow | Integrates with xUnit/NUnit, VS extension |
| Node.js | Cucumber.js | Steps in JS/TS, integrates with Playwright |
| Python | Behave, pytest-bdd | pytest-bdd is lighter-weight |
| Java | Cucumber-JVM | Works with JUnit 5, Spring Boot test |
| Ruby | RSpec + Turnip, Cucumber | RSpec native `feature/scenario` syntax |
| Any | Gauge | Markdown-based, language-agnostic |

**BDD + Layer pairing:**
- Business rule scenario → drives a unit test (fastest feedback)
- API contract scenario → drives an integration/API test
- User journey scenario → drives a Playwright E2E test
- Mocking in BDD follows the same rules as the underlying test type
