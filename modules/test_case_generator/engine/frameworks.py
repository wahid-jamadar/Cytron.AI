# modules/test_case_generator/engine/frameworks.py

FRAMEWORKS_REGISTRY = {
    "PyTest (Python)": {
        "language": "Python",
        "extension": ".py",
        "guidelines": (
            "Write pytest tests. Use standard snake_case for test function names starting with `test_`.\n"
            "Use standard `assert` statements. Implement reusable setups using `pytest.fixture` with appropriate scopes.\n"
            "Use `pytest-mock` or `unittest.mock` for mocking dependencies. Structure test files with clear comments."
        )
    },
    "Jest (JavaScript/TypeScript)": {
        "language": "TypeScript",
        "extension": ".test.ts",
        "guidelines": (
            "Write Jest tests. Use `describe` blocks to group test suites and `it` or `test` for individual cases.\n"
            "Use Jest's built-in assertions (`expect().toBe()`, `expect().toEqual()`, etc.).\n"
            "Use `jest.mock()` and `jest.fn()` for spying and mocking modules, APIs, or database connections.\n"
            "Ensure proper async handling with `async/await`."
        )
    },
    "JUnit (Java)": {
        "language": "Java",
        "extension": "Test.java",
        "guidelines": (
            "Write JUnit 5 tests. Use standard Java camelCase and `@Test` annotations.\n"
            "Use `org.junit.jupiter.api.Assertions` (`assertEquals`, `assertTrue`, etc.).\n"
            "Use `@BeforeEach`, `@AfterEach`, `@BeforeAll`, `@AfterAll` for lifecycle hooks.\n"
            "Use Mockito (`@Mock`, `@InjectMocks`, `Mockito.when()`) for mock objects."
        )
    },
    "Go Test": {
        "language": "Go",
        "extension": "_test.go",
        "guidelines": (
            "Write standard Go testing code. Test functions must start with `Test` and take `t *testing.T`.\n"
            "Use Go's idiomatic assertions (e.g., `if got != want { t.Errorf(...) }`).\n"
            "Organize tests inside table-driven tests (struct slices with inputs and expected outputs).\n"
            "Use interfaces and custom mocks/stubs for dependency injection."
        )
    },
    "RSpec (Ruby)": {
        "language": "Ruby",
        "extension": "_spec.rb",
        "guidelines": (
            "Write RSpec specifications. Use `describe` and `context` blocks for structure, and `it` for assertions.\n"
            "Use RSpec expectations (`expect().to eq()`, etc.).\n"
            "Use `let` and `let!` for lazy and eager evaluation. Mock with `double` and `allow().to receive().and_return()`."
        )
    },
    "Mocha/Chai": {
        "language": "JavaScript",
        "extension": ".spec.js",
        "guidelines": (
            "Write Mocha tests with Chai assertions. Use `describe`, `it`, `beforeEach`, and `afterEach` functions.\n"
            "Use Chai's `expect` or `should` styles. Use Sinon.js for stubs, spies, and mocks."
        )
    },
    "NUnit (.NET)": {
        "language": "C#",
        "extension": "Tests.cs",
        "guidelines": (
            "Write NUnit tests. Use `[TestFixture]` and `[Test]` attributes.\n"
            "Use `Assert.That(..., Is.EqualTo(...))` or classic Assert statements.\n"
            "Use `[SetUp]` and `[TearDown]` methods. Mock using Moq (`new Mock<T>()`, `.Setup()`)."
        )
    },
    "MSTest (.NET)": {
        "language": "C#",
        "extension": "Tests.cs",
        "guidelines": (
            "Write MSTest tests. Use `[TestClass]` and `[TestMethod]` attributes.\n"
            "Use Microsoft.VisualStudio.TestTools.UnitTesting assertions. Mock using Moq or NSubstitute."
        )
    },
    "xUnit (.NET)": {
        "language": "C#",
        "extension": "Tests.cs",
        "guidelines": (
            "Write xUnit tests. Use `[Fact]` and `[Theory]` attributes. Inject dependencies via constructor injection.\n"
            "Use xUnit assertions. Mock with Moq or NSubstitute."
        )
    },
    "PHPUnit (PHP)": {
        "language": "PHP",
        "extension": "Test.php",
        "guidelines": (
            "Write PHPUnit tests extending `PHPUnit\\Framework\\TestCase`.\n"
            "Use PHPUnit assertion methods (`$this->assertEquals`, etc.).\n"
            "Use `setUp()` and `tearDown()` lifecycle methods. Mock using `$this->createMock()` or Mockery."
        )
    },
    "Pest (PHP)": {
        "language": "PHP",
        "extension": "Test.php",
        "guidelines": (
            "Write Pest functional test cases. Use functions like `test()`, `it()`, `beforeEach()`, and `expect()`.\n"
            "Use Pest's chainable expectation API. Use PHPUnit/Mockery mock styles behind the scenes."
        )
    },
    "TestNG (Java)": {
        "language": "Java",
        "extension": "Test.java",
        "guidelines": (
            "Write TestNG tests. Use `@Test`, `@BeforeMethod`, `@AfterMethod`, `@DataProvider` annotations.\n"
            "Use `org.testng.Assert` classes. Mock using Mockito or PowerMock."
        )
    },
    "Spock (Groovy)": {
        "language": "Groovy",
        "extension": "Spec.groovy",
        "guidelines": (
            "Write Spock specifications extending `spock.lang.Specification`.\n"
            "Structure tests using Spock's semantic blocks: `given:`, `when:`, `then:`, `expect:`, `where:`.\n"
            "Use Spock's built-in mocking (`Mock()`, `Stub()`, `Spy()`) and interaction assertions."
        )
    },
    "Vitest": {
        "language": "TypeScript",
        "extension": ".test.ts",
        "guidelines": (
            "Write Vitest tests. Use standard ES module syntax.\n"
            "Use Jest-compatible describe/test syntax and `expect()` assertions.\n"
            "Utilize Vitest's optimized mocking utility (`vi.mock()`, `vi.fn()`, `vi.spyOn()`)."
        )
    },
    "Jasmine": {
        "language": "JavaScript",
        "extension": "Spec.js",
        "guidelines": (
            "Write Jasmine specs using `describe`, `it`, `expect()`, `beforeEach`, `afterEach`.\n"
            "Use Jasmine spies (`spyOn()`, `createSpy()`) for mocking and checking call interactions."
        )
    },
    "Cypress": {
        "language": "JavaScript",
        "extension": ".cy.js",
        "guidelines": (
            "Write Cypress E2E tests. Use `cy.visit()`, `cy.get()`, `cy.click()`, and assertions via `.should()`.\n"
            "Mock network requests using `cy.intercept()`. Ensure tests run in a browser-like flow."
        )
    },
    "Playwright": {
        "language": "TypeScript",
        "extension": ".spec.ts",
        "guidelines": (
            "Write Playwright E2E/API tests. Use `test()` and `expect()` from `@playwright/test`.\n"
            "Leverage standard page fixtures (`page`, `request`). Use locators (`page.locator()`, `page.getByRole()`).\n"
            "Intercept/mock network calls via `page.route()`."
        )
    },
    "Selenium WebDriver": {
        "language": "Java",
        "extension": "IT.java",
        "guidelines": (
            "Write Selenium WebDriver tests. Initialize WebDriver (`ChromeDriver`, `FirefoxDriver`).\n"
            "Use Page Object Model (POM) pattern. Locate elements with `By.id`, `By.cssSelector`, `By.xpath`.\n"
            "Add explicit waits using `WebDriverWait` and `ExpectedConditions`."
        )
    },
    "Robot Framework": {
        "language": "Python",
        "extension": ".robot",
        "guidelines": (
            "Write Robot Framework tabular scripts. Include sections: `*** Settings ***`, `*** Variables ***`,\n"
            "`*** Test Cases ***`, and `*** Keywords ***`.\n"
            "Use readable keywords and built-in or SeleniumLibrary keywords (e.g., `Open Browser`, `Click Element`)."
        )
    },
    "Cucumber (BDD)": {
        "language": "Generic",
        "extension": ".feature",
        "guidelines": (
            "Write Gherkin feature files. Use `Feature`, `Scenario`, `Given`, `When`, `Then`, `And` keywords.\n"
            "Provide corresponding step definition stubs in a typical language like JavaScript or Java."
        )
    },
    "Karate DSL": {
        "language": "Generic",
        "extension": ".feature",
        "guidelines": (
            "Write Karate API test features. Use Gherkin syntax combined with Karate DSL.\n"
            "Define URL, path, request payloads, and assert status codes or JSON schemas (e.g., `status 200`, `match response == ...`)."
        )
    },
    "Appium": {
        "language": "Python",
        "extension": "test_mobile.py",
        "guidelines": (
            "Write Appium mobile automation tests. Define desired capabilities (`platformName`, `deviceName`, `app`).\n"
            "Locate mobile elements via accessibility IDs or XPath. Verify gestures and screen flows."
        )
    },
    "Espresso (Android)": {
        "language": "Kotlin",
        "extension": "Test.kt",
        "guidelines": (
            "Write Espresso Android instrumented tests. Use `onView()`, `withText()`, `withId()`, `perform()`, and `check()`.\n"
            "Implement assertions using `matches()` and ViewAssertions."
        )
    },
    "XCTest (iOS)": {
        "language": "Swift",
        "extension": "Tests.swift",
        "guidelines": (
            "Write XCTest unit/UI tests extending `XCTestCase`.\n"
            "Use `XCTAssertEqual`, `XCTAssertNotNil`, etc. Use `XCUIApplication` for UI interactions."
        )
    },
    "K6": {
        "language": "JavaScript",
        "extension": "load_test.js",
        "guidelines": (
            "Write k6 load tests using ES6 modules. Import `http` from 'k6/http' and `check`/`sleep` from 'k6'.\n"
            "Define virtual users (VUs), duration configuration options, and scenarios.\n"
            "Add thresholds for error rates and response times (p95, p99)."
        )
    },
    "JMeter": {
        "language": "XML",
        "extension": ".jmx",
        "guidelines": (
            "Write JMeter XML test plans (.jmx). Create elements for TestPlan, ThreadGroup, HTTPSamplerProxy,\n"
            "HeaderManager, and response assertions in correct JMeter-compliant XML format."
        )
    },
    "Locust": {
        "language": "Python",
        "extension": "locustfile.py",
        "guidelines": (
            "Write Locust performance tests. Define user classes inheriting from `HttpUser`.\n"
            "Create tasks annotated with `@task`. Use `self.client` to hit API endpoints and perform assertions."
        )
    },
    "Gatling": {
        "language": "Kotlin",
        "extension": "Simulation.kt",
        "guidelines": (
            "Write Gatling simulations. Extend `Simulation`. Configure protocols, scenarios, and feeder objects.\n"
            "Inject users using injection profiles (e.g., `atOnceUsers`, `rampUsers`)."
        )
    },
    "PyUnit (unittest)": {
        "language": "Python",
        "extension": ".py",
        "guidelines": (
            "Write Python unittest test cases. Extend `unittest.TestCase`.\n"
            "Use assertion methods like `self.assertEqual`, `self.assertRaises`. Use `unittest.mock` for mocks."
        )
    },
    "Behat": {
        "language": "PHP",
        "extension": "FeatureContext.php",
        "guidelines": (
            "Write Behat context classes for PHP BDD. Extend `BehatContext` or implement `Context`.\n"
            "Map Gherkin steps to PHP functions using docblock annotations like `@Given`, `@When`, `@Then`."
        )
    },
    "Capybara": {
        "language": "Ruby",
        "extension": "_spec.rb",
        "guidelines": (
            "Write Ruby specs with Capybara. Include Capybara DSL methods like `visit`, `fill_in`, `click_on`, `have_content`.\n"
            "Mock backend responses or test in browser drivers (Selenium/Webkit)."
        )
    },
    "SuperTest": {
        "language": "JavaScript",
        "extension": ".test.js",
        "guidelines": (
            "Write SuperTest API integration tests. Pass Express/Node app instance to `request`.\n"
            "Chain verbs: `.get('/path')`, `.send(data)`, `.expect(status)`, `.expect('Content-Type', /json/)."
        )
    },
    "REST Assured": {
        "language": "Java",
        "extension": "Test.java",
        "guidelines": (
            "Write REST Assured API tests. Use static imports for `given()`, `when()`, `then()`.\n"
            "Chain request payloads, headers, query params, assert response body structure using Hamcrest matchers."
        )
    },
    "Postman/Newman": {
        "language": "JSON",
        "extension": ".postman_collection.json",
        "guidelines": (
            "Write a valid Postman Collection JSON. Define items, request objects (method, URL, headers, body),\n"
            "and embed JS test scripts inside `event` arrays (e.g., `pm.test()`, `pm.response.to.have.status()`)."
        )
    },
    "Pact (Contract Testing)": {
        "language": "TypeScript",
        "extension": ".pact.spec.ts",
        "guidelines": (
            "Write Pact contract tests. Define interaction requirements between a provider and consumer.\n"
            "Use `PactV3` constructor. Set up mock services, state specifications, and request/response expectations."
        )
    }
}
