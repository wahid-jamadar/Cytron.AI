# modules/test_case_generator/engine/coverages.py

COVERAGES_REGISTRY = {
    "Standard (80%)": "Aim for ~80% test coverage covering standard code paths, primary conditionals, and standard inputs.",
    "High (90%+)": "Aim for high coverage (>90%) covering happy paths, common error paths, and nested conditional branches.",
    "Critical (100%)": "Aim for 100% critical coverage. Cover all happy paths, error paths, boundaries, edge cases, and exception scenarios.",
    "Basic (Happy Path Only)": "Provide minimal coverage focusing solely on the standard happy path with valid inputs and normal execution flows.",
    "Smoke Testing Coverage": "Focus on validating the most critical core business capabilities and basic integration flows to ensure structural stability.",
    "Sanity Testing Coverage": "Focus on validating specific newly introduced changes, bug fixes, or isolated functionality, verifying they work as intended without detailed regression checking.",
    "Functional Coverage": "Ensure all specified requirements, business logic, functional rules, and user workflows are thoroughly validated.",
    "Regression Coverage": "Validate comprehensive regression paths, verifying that existing system functionality, side-effects, and integrations remain fully intact.",
    "Boundary Value Coverage": "Focus heavily on boundary conditions (e.g. min, max, just-below, just-above, empty values, overflow thresholds).",
    "Equivalence Partition Coverage": "Group inputs into equivalence classes (valid, invalid, boundary cases) and ensure at least one test case covers each partition class.",
    "Decision Coverage": "Ensure every boolean decision outcome (True and False outcomes for decision nodes) is exercised at least once.",
    "Branch Coverage": "Ensure every control flow branch (e.g., if/else paths, switch cases, exception handlers) is fully exercised.",
    "Statement Coverage": "Ensure that every individual executable statement/line in the target code or module is executed by at least one test.",
    "Condition Coverage": "Ensure that each boolean sub-expression in every conditional statement is evaluated to both True and False.",
    "Path Coverage": "Ensure all linearly independent paths of execution through the code or user flow are mapped and tested.",
    "Risk-Based Coverage": "Identify high-risk modules, complex features, or security-sensitive paths and focus testing depth and scenarios on those components.",
    "Security Coverage": "Focus on security aspects such as validation logic, auth checks, data leaks, SQL injections, sanitization, permissions, and cryptographic boundaries.",
    "Performance Coverage": "Focus on performance thresholds, timing limits, resource usage, concurrent operations, latency rules, and resource release.",
    "API Coverage": "Ensure comprehensive API contract testing including all status codes (2xx, 3xx, 4xx, 5xx), request headers, body structures, query params, and validation errors.",
    "Database Coverage": "Focus on database consistency, state changes, transaction rollbacks, constraints, indexes, joins, and data integrity checks.",
    "UI Coverage": "Focus on visual flows, user interactions (clicks, inputs, focus), state rendering, UI layouts, styling anomalies, and DOM state.",
    "Accessibility Coverage": "Focus on accessibility standards (WCAG guidelines, ARIA attributes, color contrast, keyboard navigation, and screen-reader friendliness).",
    "Cross-Browser Coverage": "Design tests to run and validate behaviors across multiple web browsers (Chrome, Firefox, Safari, Edge) or rendering engines.",
    "Mobile Coverage": "Focus on mobile-specific viewport sizes, touch gestures, orientations, network interruptions, offline behaviors, and OS platform differences.",
    "Maximum Coverage (All Test Scenarios)": "Generate the absolute maximum possible coverage, merging all strategies. Validate statements, branches, boundaries, security aspects, performance risks, and robust integrations."
}
