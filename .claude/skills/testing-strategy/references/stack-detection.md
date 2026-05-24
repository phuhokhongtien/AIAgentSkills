# Stack Detection Reference

## Test File Patterns

Glob patterns for detecting existing test files per language.

| Language | Glob patterns | Notes |
|---|---|---|
| TypeScript / JavaScript | `**/*.test.ts`, `**/*.spec.ts`, `**/*.test.js`, `**/*.spec.js`, `**/__tests__/**/*.ts`, `**/__tests__/**/*.js` | Exclude `node_modules` |
| Python | `**/test_*.py`, `**/*_test.py`, `**/tests/**/*.py` | `conftest.py` = pytest setup, not a test |
| C# / .NET | `**/*Tests.cs`, `**/*Test.cs`, `**/*Spec.cs`, `**/*.Tests.csproj`, `**/*.Test.csproj` | Project file suffix indicates test project |
| Go | `**/*_test.go` | Go convention — always `_test.go` suffix |
| Java / Kotlin | `**/src/test/**/*.java`, `**/src/test/**/*.kt`, `**/*Test.java`, `**/*Test.kt`, `**/*Spec.kt` | Maven/Gradle puts tests in `src/test/` |
| Ruby | `**/spec/**/*_spec.rb`, `**/test/**/*_test.rb` | RSpec = `spec/`, minitest = `test/` |
| PHP | `**/tests/**/*Test.php`, `**/*Test.php` | PSR-4 test naming |

---

## Tool Detection Table

Grep the content of manifest files for these strings to identify test tooling.

### Node.js (`package.json` devDependencies / dependencies)

| String to grep | Tool | Type |
|---|---|---|
| `"jest"` | Jest | Unit + Integration |
| `"vitest"` | Vitest | Unit + Integration |
| `"mocha"` | Mocha | Unit |
| `"jasmine"` | Jasmine | Unit |
| `"@testing-library/react"` | React Testing Library | Component/UI |
| `"@testing-library/vue"` | Vue Testing Library | Component/UI |
| `"@playwright/test"` | Playwright | E2E + Component |
| `"cypress"` | Cypress | E2E |
| `"supertest"` | Supertest | Integration/API |
| `"k6"` | k6 | Load |
| `"artillery"` | Artillery | Load |
| `"sinon"` | Sinon | Mocking |
| `"nock"` | nock | HTTP mocking |
| `"msw"` | Mock Service Worker | HTTP mocking (browser+node) |
| `"@cucumber/cucumber"` | Cucumber.js | BDD |
| `"chai"` | Chai | Assertion |

### Python (`pyproject.toml`, `requirements.txt`, `setup.py`)

| String to grep | Tool | Type |
|---|---|---|
| `pytest` | pytest | Unit + Integration |
| `unittest` | unittest | Unit |
| `httpx` | httpx | Integration (async HTTP client) |
| `requests-mock` | requests-mock | HTTP mocking |
| `responses` | responses | HTTP mocking |
| `locust` | Locust | Load |
| `pytest-benchmark` | pytest-benchmark | Performance |
| `behave` | Behave | BDD |
| `pytest-bdd` | pytest-bdd | BDD |
| `factory-boy` | factory-boy | Test data factory |
| `freezegun` | freezegun | Time mocking |
| `playwright` | Playwright | E2E |
| `selenium` | Selenium | E2E |

### .NET (`.csproj` PackageReference names)

| String to grep | Tool | Type |
|---|---|---|
| `xunit` | xUnit | Unit |
| `NUnit` | NUnit | Unit |
| `MSTest` | MSTest | Unit |
| `FluentAssertions` | FluentAssertions | Assertion |
| `Shouldly` | Shouldly | Assertion |
| `NSubstitute` | NSubstitute | Mocking |
| `Moq` | Moq | Mocking |
| `FakeItEasy` | FakeItEasy | Mocking |
| `Microsoft.AspNetCore.Mvc.Testing` | WebApplicationFactory | Integration |
| `Testcontainers` | Testcontainers | DB containers |
| `WireMock.Net` | WireMock.Net | HTTP mocking |
| `NBomber` | NBomber | Load |
| `BenchmarkDotNet` | BenchmarkDotNet | Performance |
| `Bogus` | Bogus | Test data generation |
| `AutoFixture` | AutoFixture | Auto test data |
| `SpecFlow` | SpecFlow | BDD |
| `coverlet` | Coverlet | Coverage |

### Go (`go.mod` require + source file imports)

| String to grep | Tool | Type |
|---|---|---|
| `testify` | testify | Assertion + mocking |
| `gomock` | gomock | Mocking (codegen) |
| `httptest` | httptest (stdlib) | Integration |
| `go-sqlmock` | go-sqlmock | DB mocking |
| `testcontainers-go` | testcontainers-go | DB containers |
| `gocheck` | gocheck | Assertion |

### Java/Kotlin (`pom.xml` / `build.gradle`)

| String to grep | Tool | Type |
|---|---|---|
| `junit` | JUnit | Unit |
| `mockito` | Mockito | Mocking |
| `mockk` | MockK | Mocking (Kotlin) |
| `assertj` | AssertJ | Assertion |
| `hamcrest` | Hamcrest | Assertion |
| `testcontainers` | Testcontainers | DB containers |
| `rest-assured` | REST Assured | API testing |
| `wiremock` | WireMock | HTTP mocking |
| `gatling` | Gatling | Load |
| `jmh` | JMH | Performance |
| `cucumber` | Cucumber-JVM | BDD |

---

## Project Shape Detection Rules

Apply in order — first match wins.

```
1. Glob **/package.json (not in node_modules) — count manifests at depth 1-2
   AND find *.csproj — count at depth 1-2
   Count > 2 distinct service directories → microservices

2. Read primary manifest (root package.json / Program.cs / main.py / etc.)
   Has both:
     - controllers/ or routes/ or handlers/
     - components/ or pages/ or views/ (React/Vue/Blazor)
   → fullstack

3. Has controllers/ or handlers/ or routes/
   AND no components/ or pages/ at root level
   → api

4. Has components/ or pages/ or app/ (frontend framework dirs)
   AND no controllers/ or routes/
   → web-app

5. No entry point (no main.py, Program.cs, index.ts exporting app)
   Has lib/ or src/ with exported symbols
   → library

6. Entry point reads process.argv / sys.argv / os.Args / Environment.GetCommandLineArgs
   → cli

7. None of the above → api (default for backend projects)
```

---

## CI Config Detection

Read the first found CI file and grep for test commands to determine existing
test stage configuration.

| File | CI system | Test stage patterns |
|---|---|---|
| `.github/workflows/*.yml` | GitHub Actions | `run: npm test`, `run: pytest`, `dotnet test` |
| `.gitlab-ci.yml` | GitLab CI | `script: npm test`, `test:` stage |
| `azure-pipelines.yml` | Azure Pipelines | `DotNetCoreCLI@2`, `script: pytest` |
| `Jenkinsfile` | Jenkins | `sh 'npm test'`, `sh 'mvn test'` |
| `.circleci/config.yml` | CircleCI | `run: npm test` |
| `bitbucket-pipelines.yml` | Bitbucket | `script: npm test` |

---

## Test Command Reference

| Stack | Tool | Discovery | Run all | Run specific | Coverage |
|---|---|---|---|---|---|
| Node.js | Jest | `npx jest --listTests` | `npx jest` | `npx jest <pattern>` | `npx jest --coverage` |
| Node.js | Vitest | `npx vitest list` | `npx vitest run` | `npx vitest run <pattern>` | `npx vitest run --coverage` |
| Python | pytest | `pytest --collect-only` | `pytest` | `pytest tests/unit/` | `pytest --cov=src` |
| .NET | dotnet test | `dotnet test --list-tests` | `dotnet test` | `dotnet test --filter "Name~X"` | `--collect:"XPlat Code Coverage"` |
| Go | go test | `go test ./... -list .` | `go test ./...` | `go test ./pkg/...` | `go test -cover ./...` |
| Java (Maven) | JUnit | — | `mvn test` | `mvn -Dtest=OrderTest test` | `mvn jacoco:report` |
| Java (Gradle) | JUnit | — | `./gradlew test` | `./gradlew test --tests "OrderTest"` | `./gradlew jacocoTestReport` |
| Ruby | RSpec | `rspec --dry-run` | `bundle exec rspec` | `bundle exec rspec spec/models/` | `bundle exec rspec --format documentation` |
