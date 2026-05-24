# Testing Mindset

## Core Purpose of Tests

Tests are **executable specifications** — they describe what the system should do,
not just verify it doesn't crash. A test that passes but communicates nothing about
correctness is noise. A test that fails loudly with a clear message about *what*
broke and *why* is the goal.

The most important question before writing a test: **"If this test fails, will I
immediately know what broke and why?"** If no, the test design is wrong.

---

## Testing Models

### Test Pyramid (Mike Cohn / Martin Fowler)
```
         /\
        /E2E\        ← few, slow, expensive
       /------\
      / Integ  \     ← moderate
     /----------\
    /   Unit     \   ← many, fast, cheap
   /--------------\
```
**Use when:** project has thick domain logic, rich business rules, algorithms,
complex state machines. Unit tests catch regressions fast and cheaply.

**Avoid when:** the codebase is mostly thin CRUD — you end up unit testing
pass-through methods with no real value.

---

### Test Trophy (Kent C. Dodds)
```
       /\
      /E2E\
     /------\
    / Static \       ← type checking, linting
   /----------\
  / Integration\     ← largest layer
 /--------------\
  \    Unit     /    ← smaller than pyramid
   \-----------/
```
**Use when:** framework provides excellent integration test support
(React Testing Library, ASP.NET `WebApplicationFactory`, pytest `AsyncClient`).
The integration layer is cheap enough to be the primary layer.

**Core insight:** most bugs live at the boundaries between components, not inside
pure functions. Integration tests catch boundary bugs that unit tests miss.

---

### Honeycomb (Spotify microservices pattern)
```
  [Service A]──────[Service B]──────[Service C]
       ↕                 ↕                ↕
  [Integration    [Integration    [Integration
    tests own        tests own       tests own
    this service]    this service]   this service]
```
Each service is tested end-to-end within its own process (real DB, real queues
in test containers). Services mock *other services* at the HTTP boundary.
Unit tests only for algorithms/pure functions.

**Use when:** microservices architecture, each service is independently deployable,
service boundaries are well-defined.

---

### Decision Table

| Project type | Dominant characteristic | Recommended model |
|---|---|---|
| Domain-rich backend (DDD, CQRS) | Thick business logic, many domain objects | Pyramid |
| REST/GraphQL API (CRUD-heavy) | Thin services, repository pattern | Trophy |
| React/Vue/Angular SPA | Component-driven, hooks | Trophy |
| Microservices / event-driven | Many services, message passing | Honeycomb |
| Library / SDK | Pure functions, public API surface | Pyramid |
| CLI tool | Input → processing → output | Pyramid (integration = "run the CLI") |
| Fullstack monolith | Both API and UI in one repo | Trophy for frontend, Pyramid for domain |

---

## London vs Detroit/Chicago Schools

### Detroit/Chicago School (Classicist)
- Only mock **external I/O**: databases, HTTP clients, file systems, clocks, queues
- Test groups of real collaborators together
- Domain objects use real implementations or hand-rolled fakes (e.g., `InMemoryOrderRepository`)
- Tests survive refactoring because they test observable behavior, not call graphs
- Slower test setup for complex graphs, but far more resilient

**Use when:** domain objects are independently constructable, thick business logic,
DDD-style architecture.

**Red flag that you've gone too far:** mocking `IOrderService` inside a test of
`IOrderService` — you're mocking what you're testing.

### London School (Mockist)
- Mock every collaborator. The SUT has exactly one path through it.
- Verify interaction protocols: "was `SendEmail` called with the right args?"
- Fast setup. Brittle to refactoring — changing internal structure breaks tests
  even when behavior is unchanged.
- Good for complex dependency graphs, event-driven systems, adapters/anti-corruption layers

**Use when:** collaborators have expensive real implementations, event-driven
architecture where side-effect sequencing matters.

### Decision Rule
> "If refactoring your implementation breaks your tests without changing observable
> behavior, you have too many mocks." — move toward Detroit.

> "If constructing the real collaborator graph requires 40 lines of wiring code,
> you need London-style mocking." — mock the collaborators.

**Mixed/Pragmatic (most common in practice):**
- Detroit school for domain logic (business rules, calculations, state machines)
- London school for infrastructure adapters (email senders, payment gateways, external HTTP)

---

## FIRST Principles (Unit Tests)

| Letter | Principle | What it means in practice |
|---|---|---|
| **F** | Fast | < 50ms per test. No I/O, no network, no file system, no sleep. |
| **I** | Isolated | No shared state between tests. Each test arranges its own data. |
| **R** | Repeatable | Same result regardless of execution order, environment, time, locale. |
| **S** | Self-validating | Pass or fail is explicit — never "check the log to see if it worked." |
| **T** | Timely | Written alongside (or before) the code. Not months later. |

Any test that violates one of these is either slow, flaky, or hard to maintain.

---

## AAA Pattern

Every test should follow this structure:

```
// Arrange — set up preconditions and inputs
const order = new Order({ items: [{ sku: 'CTR-20', qty: 1 }] });

// Act — perform the single action under test
const total = order.calculateTotal({ taxRate: 0.1 });

// Assert — verify the outcome
expect(total).toBe(110);
```

**Rules:**
- One logical concept per test (can have multiple `expect` calls for the same concept)
- The test name describes the scenario: `calculateTotal_withTaxRate_appliesTax`
- Arrange block should be readable in < 10 lines. If longer, use a factory/builder.

---

## What NOT to Test

| Category | Reason |
|---|---|
| Third-party library internals (ORM, HTTP client) | They have their own test suites |
| Framework wiring (DI registration, route registration, middleware order) | Test it with an integration test, not unit |
| Generated code (migrations, OpenAPI clients) | Generated from a spec — test the spec |
| Trivial getters/setters with no logic | Zero business value; maintains itself |
| Language / runtime itself | `expect(1 + 1).toBe(2)` is noise |
| `console.log` calls | Side effect with no observable behavior contract |

---

## Coverage Metrics ≠ Test Quality

100% line coverage is achievable with tests that have **no assertions** — they
execute code but verify nothing.

What actually matters:
- **Branch coverage**: every `if/else` branch exercised
- **Mutation testing** (Stryker, Pitest, mutmut): change a line of code; the test must fail
- **Behavioral coverage**: every business rule described by at least one test

A project with 60% line coverage and meaningful assertions is better tested than
a project with 100% coverage and tests full of `expect(true).toBe(true)`.
