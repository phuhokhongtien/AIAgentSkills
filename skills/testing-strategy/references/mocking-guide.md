# Mocking Guide

## Test Doubles Taxonomy (Gerard Meszaros)

Understanding which double to use prevents over-mocking and brittle tests.

| Double | Description | When to use |
|---|---|---|
| **Dummy** | Passed but never used. Fills a parameter slot. | When a collaborator is required by signature but irrelevant to the test |
| **Stub** | Returns canned answers to calls. No behavior verification. | When you need to control what a dependency returns |
| **Spy** | A stub that also records calls made. Can assert "was called N times." | When a side-effect must have occurred, but you don't need strict ordering |
| **Mock** | Pre-programmed with expectations — test FAILS if expected calls aren't made. | When interaction protocol (order, frequency, exact args) matters |
| **Fake** | A working implementation that takes shortcuts unsuitable for production. | When you need realistic behavior without real infrastructure |

**Practical guide:**
- **Use Fake** when: collaborator needs to behave realistically (e.g., `InMemoryRepository` for domain tests)
- **Use Stub** when: you need controlled return values, don't care about call verification
- **Use Spy** when: you need to verify a side-effect happened (email sent, event published), but not exact order
- **Use Mock** when: the sequence of interactions is part of the contract (e.g., begin-transaction → insert → commit-transaction)
- **Avoid Mock** when: the protocol is an internal implementation detail — prefer Spy + Stub

---

## Mock Boundaries — The Cardinal Rule

> **Mock at the system boundary, not at internal interfaces.**

**Mock these (external I/O):**
- HTTP calls to third-party services (Stripe, SendGrid, Twilio, external APIs)
- Databases (in unit tests only — use real DB in integration tests)
- File system operations
- System clock (`Date.now()`, `DateTime.Now`, `time.Now()`)
- Random number generators
- Message queues (in unit tests — use real in integration/E2E)
- Email / SMS senders

**Do NOT mock these:**
- Your own domain services (use real implementations or Fakes)
- Value objects and data containers
- Repositories in domain tests → use an `InMemoryRepository` Fake instead
- In-process method calls between your own classes
- The framework itself (routing, DI, serialization)

---

## Mocking Best Practices per Test Type

| Test Type | What to Mock | What NOT to Mock | Key Reason |
|---|---|---|---|
| **Unit** | DB/ORM, HTTP clients, file system, clock/time, queues, 3rd-party SDKs | Your own domain services, value objects, DTOs, pure functions | Isolate the behavior under test without coupling to implementation details |
| **Integration** | 3rd-party external HTTP APIs (WireMock/nock/VCR), email/SMS senders, payment gateways | Your own database (use real TestContainers), your own services, your own middleware | Test real wiring; mocking the DB defeats the purpose of integration tests |
| **API Tests** | 3rd-party downstream services, email, external payment processor | Your own DB (use real), your own services, authentication middleware | API tests should prove the full stack up to the HTTP boundary works |
| **UI Component** | Backend API calls (use MSW or jest-fetch-mock at HTTP boundary) | Browser/DOM itself, React/Vue internals, CSS, router | Component tests should verify UI behavior; API responses are the boundary |
| **UI/E2E (true E2E)** | Nothing for core journeys; 3rd-party APIs only (payment sandbox, email service) | Your own services, DB, frontend code | E2E tests the full stack — mocking your own code defeats their purpose |
| **Automation** | Clock/time (non-deterministic), external 3rd-party APIs, email/SMS/payment (use sandboxes) | Internal business logic, DB, your own services | Automation tests should run real flows; only isolate what is unsafe in CI |
| **Load Tests** | Nothing — test against a dedicated staging env | — | Load tests must reflect real behavior; mocking distorts the numbers |
| **BDD** | Follow the rules of the underlying test layer being driven | The Gherkin step definitions themselves | BDD is a style, not a test level — mock rules come from the layer |

---

## London vs Detroit Applied

### Detroit/Chicago Examples

```typescript
// ✅ Detroit — real PricingService, only mock Stripe (external I/O)
describe('OrderService', () => {
  it('createOrder_withDiscount_appliesCorrectTotal', async () => {
    const pricingService = new PricingService();               // real
    const orderRepo = new InMemoryOrderRepository();           // fake
    const stripe = createFakeStripe({ chargeResult: 'ok' });  // fake external
    const sut = new OrderService(pricingService, orderRepo, stripe);

    const order = await sut.createOrder({ items: [...], coupon: 'SAVE10' });

    expect(order.total).toBe(90);
    expect(orderRepo.findById(order.id)).toBeDefined();
  });
});
```

### London School Examples

```typescript
// ✅ London — mock every collaborator, verify interaction protocol
describe('OrderService', () => {
  it('createOrder_chargesStripeWithCorrectAmount', async () => {
    const pricingService = jest.fn().mockReturnValue({ total: 90 });
    const orderRepo = { save: jest.fn() };
    const stripe = { charge: jest.fn().mockResolvedValue({ id: 'ch_123' }) };
    const sut = new OrderService(pricingService, orderRepo, stripe);

    await sut.createOrder({ items: [...], coupon: 'SAVE10' });

    expect(stripe.charge).toHaveBeenCalledWith({ amount: 90, currency: 'usd' });
  });
});
```

### When London Gets Brittle

```typescript
// ❌ Brittle London — test breaks when you rename internal method,
//    even though behavior is unchanged
expect(pricingService.computeLineItemPrice).toHaveBeenCalledTimes(3);
// renaming 'computeLineItemPrice' → 'calculatePrice' breaks this test
// even though the order total is still correct

// ✅ Instead: assert on outcome, not implementation
expect(order.total).toBe(270);
```

---

## Tools by Stack

| Stack | Mock/Stub/Spy | Fake HTTP | Fake Time |
|---|---|---|---|
| .NET | NSubstitute, Moq, FakeItEasy | WireMock.Net | `TimeProvider` (.NET 8), NSubstitute |
| Node.js / TS | jest.fn(), jest.spyOn(), sinon | msw, nock, jest-fetch-mock | jest.useFakeTimers() |
| Python | unittest.mock, pytest-mock | responses, respx, httpretty | freezegun, time-machine |
| Go | gomock (codegen), testify/mock | httptest.NewServer | clock package |
| Java | Mockito, MockK (Kotlin) | WireMock, MockServer | Mockito clock, @MockBean |
| Ruby | RSpec mocks, flexmock | WebMock, VCR | timecop |
| PHP | Mockery, PHPUnit mocks | php-vcr, guzzle mock | Carbon::setTestNow() |

---

## Anti-Patterns

### 1. Mocking the System Under Test
```typescript
// ❌ You're testing OrderService by mocking OrderService
const sut = mock(OrderService);
when(sut.createOrder(anything())).thenReturn(fakeOrder);
```
You learn nothing from this test. It always passes.

### 2. Mocking Value Objects
```typescript
// ❌ Money is a value object — just construct it
const money = mock(Money);
when(money.amount).thenReturn(100);

// ✅
const money = new Money(100, 'USD');
```

### 3. `any()` Matchers Everywhere
```typescript
// ❌ Hides incorrect arguments passed to dependencies
expect(stripe.charge).toHaveBeenCalledWith(anything(), anything());

// ✅ Verify meaningful parts of the contract
expect(stripe.charge).toHaveBeenCalledWith(
  expect.objectContaining({ amount: 9000, currency: 'usd' })
);
```

### 4. 50-Line Mock Setup per Test
```typescript
// ❌ If your Arrange block is 50 lines of mock wiring, it's a design smell
// Usually means: too many dependencies, wrong abstraction level, or wrong school

// ✅ Fix: introduce a Fake (real lightweight implementation), or restructure
//    the code to reduce the dependency count
```

### 5. Asserting on Mock Calls Instead of Outcomes
```typescript
// ❌ Testing implementation, not behavior
expect(orderRepo.save).toHaveBeenCalledWith(expect.objectContaining({ id: expect.any(String) }));

// ✅ Testing observable outcome
const saved = await orderRepo.findByCustomerId(customerId);
expect(saved).toHaveLength(1);
expect(saved[0].total).toBe(90);
```

### 6. Shared Mock Setup Across All Tests in a Class
```typescript
// ❌ beforeAll mock setup that 20 tests silently depend on
beforeAll(() => {
  jest.mock('../stripe', () => ({ charge: jest.fn().mockResolvedValue({}) }));
});
// Test N assumes charge returns {} — but what if test N+1 needs a failure response?

// ✅ Each test sets up its own mock state in the Arrange block
```

---

## Fake vs Mock Decision Tree

```
Does the collaborator have real business logic you want to exercise?
  YES → Use a Fake (InMemoryRepository, FakeEmailSender)
  NO  → Does it cross a process boundary (DB, HTTP, file, clock)?
          YES → Stub or Mock it
          NO  → Consider not mocking at all (use the real object)
```
