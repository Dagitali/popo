// GreetingTests.swift
// popo/examples/swift/Tests/GuardrailExampleTests
//
// Copyright © 2026 Dagitali LLC. All rights reserved.
//
// Verify the Swift package independently of Popo's repository checks.

import XCTest
@testable import GuardrailExample

final class GreetingTests: XCTestCase {
    func testMessage() {
        XCTAssertEqual(Greeting.message, "Hello, guardrails!")
    }
}
